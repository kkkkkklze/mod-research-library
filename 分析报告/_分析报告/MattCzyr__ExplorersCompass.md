# MattCzyr/ExplorersCompass 源码分析报告

## 1. 基本信息

- Mod 名：Explorer's Compass（`displayName` 见 `src/main/resources/META-INF/neoforge.mods.toml`）
- mod_id：`explorerscompass`；作者：ChaosTheDude（仓库 owner 为 MattCzyr）；group：`com.chaosthedude.explorerscompass`
- 目标版本与加载器（`gradle.properties`）：`minecraft_version=26.2`、`neo_version=26.2.0.1-beta`、`mod_version=26.2-3.3.0-neoforge`，纯 NeoForge（无 Fabric 分支）
- Gradle 插件：`net.neoforged.moddev` 2.0.141，Java toolchain 25（`build.gradle`），无 mixin 插件
- 许可证：CC BY-NC-SA 4.0（`neoforge.mods.toml` 的 `license` 字段 + `LICENSE.md`）
- 编译依赖：只有 `neoforge` + `minecraft` 两条 required；`build.gradle` 的 `dependencies {}` 全为注释，**无任何第三方 API 依赖**

## 2. 源码规模与包结构

- 36 个 `.java`，共 2697 行（`find . -name '*.java' | wc -l` / `-exec wc -l {} +`）
- `worker`(6)、`sorting`(6)、`gui`(6)、`util`(5)、`client`(5)、`network`(4)、`registry`(1)、`item`(1)、`config`(1)、根包(1)
- 最大文件：`util/StructureUtils.java` 257、`item/ExplorersCompassItem.java` 257、`gui/ExplorersCompassScreen.java` 211、`worker/StructureSearchWorker.java` 148、`worker/RandomSpreadSearchWorker.java` 120、`ExplorersCompass.java` 115、`worker/ConcentricRingsSearchWorker.java` 111
- 资源目录仅 `META-INF/{neoforge.mods.toml,accesstransformer.cfg}`（贴图/语言文件未纳入本地副本）

## 3. 入口与注册

主类 `src/main/java/com/chaosthedude/explorerscompass/ExplorersCompass.java:40` 用 `@Mod(MODID)`，构造器注入 `ModContainer`，走 `modContainer.getEventBus().addListener(this::...)` 注册 FML 事件（`:69-78`），同时 `registerConfig(COMMON/CLIENT)` 与 `NeoForge.EVENT_BUS.register(this)`：

```java
public ExplorersCompass(ModContainer modContainer) {
    modContainer.getEventBus().addListener(this::commonSetup);
    modContainer.getEventBus().addListener(this::buildCreativeTabContents);
    modContainer.getEventBus().addListener(this::registerPayloads);
    modContainer.registerConfig(ModConfig.Type.COMMON, ConfigHandler.GENERAL_SPEC);
```

不使用 DeferredRegister：物品与组件用经典 `RegisterEvent`（`registry/ExplorersCompassRegistry.java:16-33`）

```java
e.register(BuiltInRegistries.ITEM.key(), helper -> {
    ExplorersCompass.explorersCompass = new ExplorersCompassItem();
    helper.register(Identifier.fromNamespaceAndPath(MODID, ExplorersCompassItem.NAME), ExplorersCompass.explorersCompass);
});
```

物品自身用 `new Properties().setId(KEY).stacksTo(1)`（`item/ExplorersCompassItem.java:43`）声明 ResourceKey。10 个 `DataComponentType` 定义在主类静态字段（`ExplorersCompass.java:49-58`），全部 `persistent(...).networkSynchronized(...)`，是物品状态唯一载体。

## 4. 核心系统

**a. 搜索 worker 体系**（`worker/`）：抽象基类 `StructureSearchWorker<T extends StructurePlacement>` 实现自定义接口 `WorldWorkerManager.IWorker{hasWork(); doWork();}`；熔断条件集中在 `worker/StructureSearchWorker.java:73`（`maxNextSearches` / `maxRadius` / `maxSamples` 三配置）。`worker/SearchWorkerManager.java:46-57` 按 placement 子类分派三种 worker：

```java
if (placement instanceof ConcentricRingsStructurePlacement) { workers.add(new ConcentricRingsSearchWorker(...)); }
else if (placement instanceof RandomSpreadStructurePlacement) { workers.add(new RandomSpreadSearchWorker(...)); }
else { workers.add(new GenericSearchWorker(...)); }
```
workers 是队列，`start()/pop()` 配合 `fail()` 实现"一个 placement 找不到就试下一个"。

**b. 服务端时间片调度**：`worker/WorldWorkerManager.java:11-37` 由 `ServerTickEvent.Pre` 记 `startTime`、`Post` 执行，预算 50ms（tick 落后时保底 10ms），`doWork()` 返回 true 可连续调用；挂点在 `ExplorersCompass.java:101-109`，`ServerStoppingEvent` 清空。

**c. 结构定位算法**：`StructureSearchWorker.getStructureGeneratingAt(ChunkPos)`（`:88-105`）先用 `level.structureManager().checkStructurePresence(chunkPos, structure, placement, false)`，命中 `START_PRESENT` 直接返回 `placement.getLocatePos(chunkPos)`，否则取 `ChunkStatus.STRUCTURE_STARTS` 的 `StructureStart` 再校准。`RandomSpreadSearchWorker.doWork()`（`:40-71`）只采样 `x==±length || z==±length` 的环边界点、按 length 逐环外扩（近到远）；`ConcentricRingsSearchWorker` 用 `getRingPositionsFor(placement)` 预取候选环点并记录 `minDistance`。

**d. 服务端权威 + 单次同步**：`item.use()` 在服务端算好可搜索结构、XP 消耗、可生成维度、结构→组映射后一次性下发；客户端读 `ExplorersCompass` 静态缓存渲染（`item/ExplorersCompassItem.java:58-66`，`network/SyncPacket.java:73-85`）。

**e. 客户端渲染**：`client/ExplorersCompassClient.java`（`@EventBusSubscriber(Dist.CLIENT)`）注册 `RegisterRangeSelectItemModelPropertyEvent` 的 `angle` 属性（`:17`）与 `RegisterGuiLayersEvent` 的 HUD 层（`:22`）；`client/ExplorersCompassAngleState` 继承 `NeedleDirectionHelper` 复用原版指南针指针动画（wobbler 抖动 + `getRotationTowardsCompassTarget`）。

**f. 排序策略**：`sorting/ISorting`（`getValue/next/getLocalizedName`，`extends Comparator<Identifier>`），5 个实现（维度/组/名称/来源/XP）；`gui/ExplorersCompassScreen.java:187-189` 点击按钮 `sortingCategory = sortingCategory.next()`，`:158-161` 先按 NameSorting 再按当前策略两次稳定排序。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：4 个 `CustomPacketPayload`（`SearchPacket`、`SearchForNextPacket`、`TeleportPacket` 为 `playToServer`，`SyncPacket` 为 `playToClient`），在 `ExplorersCompass.registerPayloads`（`:93-99`）用 `PayloadRegistrar` 注册；编解码为手写 `FriendlyByteBuf` read/write + `StreamCodec.ofMember`；`handle` 内统一 `context.enqueueWork(...)` 且用 `context.flow().isServerbound()/isClientbound()` 双保险。
- 配置：`config/ConfigHandler.java` 用 `ModConfigSpec` 分 COMMON/CLIENT 两份；含 glob 通配黑名单 `structureBlacklist`、逗号串列表 `perStructureXpLevels`，由 `StructureUtils.convertToRegex`（`:240-256`）把 `*`/`?` 转正则匹配。
- 数据驱动：结构/结构组均来自 `Registries.STRUCTURE` 与 `Registries.STRUCTURE_SET`，黑名单还支持 `c:hidden_from_locator_selection` 标签（`util/StructureUtils.java:106-109`）。
- datagen：无（`build.gradle` 仅配置了 `src/generated/resources` 与 data run，无 `data` 包）。

## 6. Mixin

无 mixin（仓库内无 mixin 配置与 `@Mixin`）。仅有 1 处访问转换器：`src/main/resources/META-INF/accesstransformer.cfg` → `public net.minecraft.client.gui.components.EditBox bordered`。

## 7. 值得学的 5 条具体做法

1. **用 DataComponentType 承载全部物品状态**：10 个组件（state/x/z/radius/samples/prevPos/damage…）全部 `persistent + networkSynchronized`，读写即 `stack.getOrDefault(...)`，彻底免掉 NBT 样板与手动同步 —— `ExplorersCompass.java:49-58`；适用于任何"有状态道具"。
2. **服务端 tick 时间片 worker**：`System.currentTimeMillis()` 记账 + 每次最多 50ms 的 `doWork()` 循环 —— `worker/WorldWorkerManager.java:11-37`；适用耗时搜索/遍历，避免单 tick 卡服。
3. **按 placement 子类分派算法 + worker 队列**：新结构类型只需加一个分支和构造参数 —— `worker/SearchWorkerManager.java:46-57`；适合需要针对不同生成机制做不同优化的场景。
4. **一次 SyncPacket 下发全部服务端算好的数据**（可搜索结构 + XP + 维度 + 组映射），客户端只读缓存，配置/权限判断仍在服务端复核（`TeleportPacket.handle` 二次校验 `allowTeleport` 与 `canTeleport`）—— `network/SyncPacket.java`、`network/TeleportPacket.java:36-58`。
5. **配置用 glob 而非精确 ID**：`convertToRegex` 将 `*`/`?` 转正则，黑名单与 XP 覆写共用同一套匹配 —— `util/StructureUtils.java:96-104,240-256`；适合给整合包作者留配置自由度。另可借鉴 `ISorting.next()` 的"排序策略循环"（`gui/ExplorersCompassScreen.java:187`）。

## 8. 公开 API

不适用（非库/前置 mod，无对外 API 包）。
