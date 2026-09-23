# Fuzss/pickupnotifier（Pick Up Notifier）源码分析报告

> 前提：本地 `_bulk/Fuzss__pickupnotifier` 的默认分支 `main`（a945b49）是**元数据仓库**，只有 README/LICENSE/.github，`find . -name '*.java' | wc -l` = **0**。源码按 MC 版本分散在分支上（1.20.1 / 1.21.1 / 26.x）。本报告内容取自 `1.21.1` 分支（commit 420357d，modVersion 21.1.1），与作者目标版本一致。

## 1. 基本信息

- Mod 名 / mod_id：Pick Up Notifier / `pickupnotifier`；作者 Fuzs；许可证 MPL-2.0（`LICENSE.md`）；素材单独授权"All Rights Reserved"（`LICENSE-ASSETS.md`）
- 目标：MC 1.21.1，多加载器 Common+Fabric+NeoForge（`gradle.properties:8-42`）；`modForgeDisplayTest=IGNORE_ALL_VERSION` 即**纯客户端 mod**（不参与 mod 列表校验）
- Gradle：架构为 Architectury 风格但**不依赖 architectury**，而是共享远程脚本 `build.gradle:9` → `apply from: "https://raw.githubusercontent.com/Fuzss/modresources/main/gradle/${libs.versions.minecraft.get()}/main.gradle"`，插件为 architecturyloom/architecturyplugin/shadow/cursegradle/minotaur；版本目录 `dependenciesVersionCatalog=1.21.1-SNAPSHOT`
- 编译依赖：**Puzzles Lib 是它的 API 与运行时**（`neoforge.mods.toml` 声明 `puzzleslib [${minPuzzlesVersion},)` mandatory）；Fabric 侧另需 fabric-api、forge-config-api-port。注意 `Common` 源码直接 import `net.neoforged.neoforge.common.ModConfigSpec`（`config/ClientConfig.java:8`），Fabric 上靠 ForgeConfigAPIPort 供类

## 2. 源码规模与包结构（实测）

- `common/src` 25 个 `.java`，总 **1585 行**（`find … -exec wc -l {} +`）。分布：Common 19、Fabric 3、NeoForge 3
- 包根 `fuzs.pickupnotifier`：`client`(2) `client/commands`(1) `client/gui`(1) `client/gui/entry`(3) `client/handler`(3) `client/util`(3) `config`(2) `mixin/client`(2) `network`(2)
- 最大文件：`client/gui/entry/DisplayEntry.java` 190、`client/handler/AddEntriesHandler.java` 135、`client/handler/DrawEntriesHandler.java` 117、`config/ClientConfig.java` 111、`client/gui/entry/ExperienceDisplayEntry.java` 110、`client/util/TransparencyBuffer.java` 104

## 3. 入口与注册

Common 侧**没有 `@Mod`**，只有一个继承 Puzzles Lib `ModConstructor` 的常量类 `PickUpNotifier.java`，注册全部写为静态字段初始化：

```java
public static final NetworkHandler NETWORK = NetworkHandler.builder(MOD_ID).optional().registerLegacyClientbound(
        S2CTakeItemMessage.class, S2CTakeItemMessage::new).registerLegacyClientbound(S2CTakeItemStackMessage.class, …);
public static final ConfigHolder CONFIG = ConfigHolder.builder(MOD_ID).client(ClientConfig.class).server(ServerConfig.class)
        .setFileName(ClientConfig.class, ConfigHolder.getDirectoryNameFactory("client", MOD_ID)) …;
```

（`Common/src/main/java/fuzs/pickupnotifier/PickUpNotifier.java:18-26`）

平台入口只做构造转发：`NeoForge/.../PickUpNotifierNeoForge.java` = `@Mod(MOD_ID)` + `ModConstructor.construct(MOD_ID, PickUpNotifier::new)`；客户端 `@Mod(value = MOD_ID, dist = Dist.CLIENT) PickUpNotifierNeoForgeClient` → `ClientModConstructor.construct(...)`。**无 DeferredRegister / Registrate**——本 mod 不注册任何游戏内容，只注册网络与配置。

## 4. 核心系统

1. **服务端拾取采集**：`NeoForge/.../handler/NeoForgeItemPickupHandler.java` 刻意用原生 `ItemEntityPickupEvent.Pre/Post` 而非 Puzzles Lib 抽象（注释"use native Forge events to be able to receive cancelled"），以 `EventPriority.HIGH` 先快照 `currentStack`、`EventPriority.LOW + receiveCancelled=true` 再比对剩余数量，算出"部分拾取"并手工模拟 `Inventory.getFreeSlot()/getSlotWithRemainingSpace()` 判断能否装下（`getSpaceAtIndex`）；Fabric 侧等价实现见 `Fabric/.../FabricItemPickupHandler.java`（返回 `EventResult.PASS`）
2. **客户端采集与去重**：`client/handler/AddEntriesHandler.java` 有两个入口——原版包 `ClientPacketListenerMixin` 注入 `handleTakeItemEntity`，以及服务端包 `addPickUpEntry`；后者把 entityId 写入 `DrawEntriesHandler.handledEntities`（`Int2ObjectArrayMap<MutableInt>`，80 tick 过期）以**防止同一次拾取被客户端与服务端各记一遍**
3. **条目模型与合并**：`client/gui/entry/DisplayEntry.java`（抽象，`ENTRY_HEIGHT = 18`，text 组件惰性缓存 + 稀有度配色）与子类 `ItemDisplayEntry`/`ExperienceDisplayEntry`；容器 `client/util/PickUpCollector.java extends ArrayList<DisplayEntry>`，提供 `refresh()`（先 remove 再 add 到末尾=重新计时）、`findDuplicate/mayMergeWith`（`CombineEntries.ALWAYS/NEVER/EXCLUDE_NAMED` 三态）、`getTotalFade()`（计算整体位移动画）
4. **HUD 渲染**：`client/handler/DrawEntriesHandler.java:58` 订阅 Puzzles Lib `RenderGuiCallback`；按 `PositionPreset`（`mirrored()/bottom()/getX/getY`）与 `move/fadeAway` 配置做 alpha+位移；`client/util/TransparencyBuffer.java` 自建第二个 `TextureTarget` 双 framebuffer 实现**半透明物品精灵**（类注释注明抄自 samolego/ClientStorage，LGPL-3.0），配合 `MinecraftMixin.resizeDisplay`
5. **数据驱动的物品黑名单**：`client/handler/ItemBlacklistManager.java` 扫描 config/pickupnotifier 目录下所有 json（字段 `inverted` / `dimension` / `items`），用 Puzzles Lib `ConfigDataSet.from(Registries.ITEM, …)` 解析（支持标签），按 `ResourceKey<Level>` 分维度建表，`inverted` 冲突直接抛 `IllegalStateException`；`client/commands/ModReloadCommand.java` 提供客户端 `/pickupnotifier reload` 热重载

## 5. 网络 / 数据驱动 / 配置

- **网络**：Puzzles Lib `NetworkHandler` v3 + v2 的 `WritableMessage` 接口（`write(FriendlyByteBuf)` / `makeHandler().handle(packet, player, gameInstance)`）。只有 2 个 S2C 包：`S2CTakeItemMessage(int entityId, int amount)` 与 `S2CTakeItemStackMessage(ItemStack)`（1.21.1 用 `ItemStack.OPTIONAL_STREAM_CODEC.encode((RegistryFriendlyByteBuf) buf, …)`）；服务端 `NETWORK.sendTo((ServerPlayer) player, msg.toClientboundMessage())`
- **数据驱动**：仅上述 json 黑名单；**无 datagen**（仓库无 `data/` 生成器目录）
- **配置**：Puzzles Lib `ConfigHolder` v3。`ClientConfig` 是三层嵌套 `ConfigCore`（General/Behavior/Display）+ 4 个枚举；`@Config` 注解只用于描述，**实际注册一律手写** `addToBuilder(ModConfigSpec.Builder builder, ValueCallback callback)`（`config/ClientConfig.java:32-87` 用 `define/defineEnum/defineInRange`）。`ServerConfig.addToBuilder` 里用 `ModLoaderEnvironment.INSTANCE.getModLoader().isForgeLike()` 做**平台差异化配置项**（`backpack_integration` 只在 Forge 系出现）

## 6. Mixin

- `Common/src/main/resources/common.mixins.json`：`package: ${modGroup}.mixin`，client 两条；`NeoForge/.../neoforge.mixins.json` 为空占位（Fabric 侧另有 `fabric.mixins.json`、accesswidener `pickupnotifier.accesswidener` + `architectury.common.json`）
- `mixin/client/ClientPacketListenerMixin.java`：`@Inject(method="handleTakeItemEntity", at=@At(value="INVOKE", target="…PacketUtils;ensureRunningOnSameThread…", shift=Shift.AFTER))`，在包体真正执行后抓取 (itemId, playerId, amount)
- `mixin/client/MinecraftMixin.java`：`@Inject(method="resizeDisplay", at=@At("RETURN"))` → `TransparencyBuffer.resizeDisplay()`

## 7. 值得学的具体做法

1. **事件双通道**：同一逻辑在 NeoForge 用 `EventPriority.HIGH` + `receiveCancelled=true` 的原生事件精确算"实际拾取量"，Fabric 用抽象事件回退（`NeoForgeItemPickupHandler.java`）——适用于跨加载器的拾取/交互类逻辑
2. **一包一路径去重**：服务端先算并广播，客户端维护 `handledEntities` 过期表忽略重复（`AddEntriesHandler.java:29-41`）——适用于 serv/client 都会触发的事件
3. **配置描述与注册分离**：字段 + `addToBuilder` 手写 `define*`，可按加载器分支配置项（`ServerConfig.java:14-19`）
4. **双 framebuffer 做 GUI 半透明**：`TransparencyBuffer` + `resizeDisplay` mixin，是 1.21.1 上给物品/文本做真实 alpha 的少见现成方案（含出处与许可证）
5. **客户端 `/modid reload` + JSON 数据驱动**：让整合包可替换黑名单而不改 jar（`ModReloadCommand.java`、`ItemBlacklistManager.java`）

## 8. 无

本 mod 不是库/前置，不提供对外 API；其"API"实际由 Puzzles Lib 提供（`fuzs.puzzleslib.api.core.v1.ModConstructor`、`api.network.v3.NetworkHandler`、`api.config.v3.ConfigHolder`）。
