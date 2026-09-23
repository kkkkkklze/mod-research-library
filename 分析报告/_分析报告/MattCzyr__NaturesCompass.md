# MattCzyr/NaturesCompass 源码分析报告

## 1. 基本信息
- Mod 名：Nature's Compass；mod_id `naturescompass`；作者 ChaosTheDude（仓库 MattCzyr）
- 目标版本：`gradle.properties` → `minecraft_version=26.2`、`neo_version=26.2.0.1-beta`、`mod_version=26.2-3.3.0-neoforge`、Java toolchain **25**；加载器仅 NeoForge
- Gradle 插件：`net.neoforged.moddev` 2.0.141（无 mixin/loom 插件）
- 许可证：CC BY-NC-SA 4.0（`LICENSE.md`、`neoforge.mods.toml` license 字段）
- 编译依赖：**无任何第三方 mod 依赖**（`build.gradle` 的 dependencies 块全是注释示例）；`src/main/resources/META-INF/accesstransformer.cfg` 存在（`public net.minecraft.client.gui.components.EditBox bordered`），但 `build.gradle` 里 `accessTransformers` 一行被注释，是否生效未确认

## 2. 源码规模与包结构
`find . -name '*.java' | wc -l` → **34 个文件 / 2540 行**（单一 sourceSet）。
包分布（到第 3 层）：`sorting` 8、`gui` 6、`util` 5、`client` 5、`network` 4、`worker` 2、`registry` 1、`item` 1、`config` 1、根 1。
最大文件：`util/BiomeUtils.java` 283、`worker/BiomeSearchWorker.java` 273、`item/NaturesCompassItem.java` 222、`gui/NaturesCompassScreen.java` 208、`NaturesCompass.java` 127、`gui/BiomeSearchEntry.java` 120、`gui/BiomeSearchList.java` 111、`config/ConfigHandler.java` 97、`network/TeleportPacket.java` 93。

## 3. 入口与注册
主类 `src/main/java/com/chaosthedude/naturescompass/NaturesCompass.java:43` `@Mod`，构造器（:74-85）里注册 FMLCommonSetupEvent、BuildCreativeModeTabContentsEvent、RegisterPayloadHandlersEvent、两套 ModConfig，并挂 `NeoForge.EVENT_BUS`。
注册**不用 DeferredRegister**，而是事件总线 + `RegisterEvent` 内联 lambda：
```java
// registry/NaturesCompassRegistry.java:15
@SubscribeEvent
public static void register(RegisterEvent event) {
    event.register(BuiltInRegistries.ITEM.key(), registry -> {
        NaturesCompass.naturesCompass = new NaturesCompassItem();
        registry.register(Identifier.fromNamespaceAndPath(MODID, NaturesCompassItem.NAME), NaturesCompass.naturesCompass);
    });
```
物品实例与 9 个 `DataComponentType` 全部是主类的 `public static` 字段（`NaturesCompass.java:52-62`），注册类只做 `registry.register` 绑定。

## 4. 核心系统
**① 协作式分片搜索（worker 包）**：`WorldWorkerManager.java:11-37` 由 `ServerTickEvent.Pre/Post` 夹住一个 tick 的时间片（预算 = 50ms − 已耗时，最低 10ms），`IWorker.doWork()` 的返回值语义是"本 tick 是否还能再调我"（:57-65）。`BiomeSearchWorker.java:107-112` 用螺旋扩展采样（UP→NORTH→EAST→SOUTH→WEST，`nextLength` 逐圈加长），取点走 `QuartPos.fromBlock` + `biomeSource.getNoiseBiome(..., randomState().sampler())`，**不加载区块**；进度写回 ItemStack 组件 `SEARCH_RADIUS`（:232-237）。上限 `maxSamples`/`maxRadius` 来自配置 × `BiomeUtils.getBiomeSize`。
**② 连通性校验**：命中候选点后不立即成功，先沿"上一个结果→候选点"直线采样，连续非匹配段达到 `clamp(distance/sampleSpace/4, 1, 10)` 即判定不连通、放弃该点（`BiomeSearchWorker.java:143-214`），避免把隔海的同群系当成最近结果。
**③ 物品状态用 DataComponentType + 状态机**：`compass_state/biome_id/found_x/found_z/search_radius/samples/display_coords/prev_pos/damage`，均为 `persistent(...).networkSynchronized(...)`（`NaturesCompass.java:54-62`）；`CompassState{INACTIVE,SEARCHING,FOUND,NOT_FOUND}` + `shouldCauseReequipAnimation` 按状态抑制换手动画（`NaturesCompassItem.java:110-115`）；自绘耐久条 `isBarVisible/getBarWidth/getBarColor`，不占用原版 damage（:82-107）。
**④ sorting 策略链**：`sorting/ISorting.java` 继承 `Comparator<Identifier>` 并带 `next()`/`getLocalizedName()`，7 个实现（Name/Dimension/Tags/Temperature/Rainfall/XpLevels/Source）可循环切换。
**⑤ 配置与黑白名单**：`config/ConfigHandler.java` 两套 `ModConfigSpec`（COMMON/CLIENT，:18-19）；`biomeBlacklist`、`perBiomeXpLevels` 支持 `*` `?` 通配符，`BiomeUtils.java:65-102` 把通配符转成正则逐条匹配，XP 上限硬编码为 3。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：4 个 `record ... implements CustomPacketPayload`，手写 `StreamCodec.ofMember(read, write)`；服务端 `handle` 内先判 `context.flow()` 再 `context.enqueueWork`（`network/SyncPacket.java:22,71-83`）。`SyncPacket` 在玩家使用指南针时一次性下发全部群系/维度/XP 配置快照（`NaturesCompassItem.java:60-66`）；`TeleportPacket.java:62-86` 自实现 `findValidTeleportHeight`（从海平面上下同时探测可站立点）。权限用 NeoForge `PermissionNode<Boolean> TELEPORT_PERMISSION`（`NaturesCompass.java:48`）。
- 数据驱动：无（无 worldgen/tags JSON）。
- 配置：NeoForge `ModConfigSpec`（COMMON + CLIENT）。
- datagen：`build.gradle` 声明了 `src/generated/resources` 与 data run config，但仓库内**不存在**该目录与任何 DataProvider → 实际未使用。

## 6. Mixin
**无**。`grep -ril mixin src` 无结果，无 `*.mixins.json`，AT 是唯一字节码层手段。

## 7. 值得学的 5 条
1. **每 tick 时间片 + IWorker 接口**，把 5 万次采样的长任务拆成不卡服的协作式工作：`worker/WorldWorkerManager.java:11-37`；适用任何跨 tick 的大范围世界扫描（找结构、扫群系、批量替换）。
2. **物品状态放 DataComponentType 而非 NBT**，persistent + networkSynchronized 双声明即可自动同步给客户端：`NaturesCompass.java:54-62`；适用一切"有状态的工具/仪器"。
3. **命中后加连通性/合理性校验**再返回结果：`worker/BiomeSearchWorker.java:143-214`；适用寻路、结构定位类功能。
4. **枚举状态机 + 覆盖 `shouldCauseReequipAnimation`** 抑制无意义的手部动画：`item/NaturesCompassItem.java:110-115`。
5. **配置项用通配符字符串列表匹配资源路径**（`*`/`?` 转正则），比写 id 清单友好：`util/BiomeUtils.java:65-102`。

## 8. 公开 API
无（非库/前置 mod）。
