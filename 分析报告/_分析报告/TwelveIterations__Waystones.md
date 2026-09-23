# TwelveIterations/Waystones 源码分析报告

## 1. 基本信息

| 项 | 值 | 来源 |
|---|---|---|
| Mod 名 / mod_id | Waystones / `waystones` | `gradle.properties:2-3` |
| 作者 | BlayTheNinth（TwelveIterations） | `gradle.properties:4` |
| 版本 | 26.2.0.12 | `gradle.properties:7` |
| 目标 MC / 加载器 | **Minecraft 26.2**、Java 25；fabric(loom)、neoforge(modDevGradle) 启用，forge 关闭 | `gradle/libs.versions.toml:1-22`、`gradle.properties:22-30` |
| Gradle 插件 | fabric-loom 1.14-SNAPSHOT、moddev 2.0.141、forge gradle `[6.0.25,6.2)`、curseforgegradle、minotaur | `gradle/libs.versions.toml:51-57` |
| 许可证 | All Rights Reserved（非开源许可，源码可读不可复用） | `gradle.properties:13` |
| 编译依赖 | **balm 26.2.0.7**（作者自研跨加载器平台层，做注册/网络/配置/事件/渲染抽象）、**shogi 26.2.0.5**（规则 DSL 引擎）、journeymap-api、BlueMapAPI v2.5.1、DynmapCoreAPI、unbreakables；mixin 0.8.7 compileOnly | `common/dependencies.gradle`、`gradle/libs.versions.toml:24-48` |

注意：仓库快照不是 1.21.1，是 MC 26.2 时代（`Identifier` 已取代 `ResourceLocation`）。加载器矩阵由 `settings.gradle:36-45` 的 `include_fabric/include_neoforge/include_forge` 开关控制。

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **354 个文件**，合计 **22977 行**（common 325 文件 / 21851 行；fabric 19/997；neoforge 7/75；forge 3/54）。

包结构（第 3 层，文件数）：`api 28`（+`api/client 3`、`api/event 15`、`api/trait 5`、`api/error 2`）、`client 9`（`client/gui/widget 28`、`client/requirement 15`、`client/gui/screen 13`、`client/config 5`、`client/render 5`）、`block 13`+`block/entity 9`、`core 19`、`item 17`、`worldgen 5`+`worldgen/namegen 12`、`config 6`+`config/rules 10`、`network 2`+`network/message 20`、`store 8`、`menu 7`、`compat 6`、`handler 9`、`component 8`、`requirement 6`、`comparator 6`、`migration 3`、`mixin 7`、`command 5`、`tag 4`。

最大文件：`core/WaystoneTeleportManager.java` 556、`client/gui/screen/WaystoneSelectionScreenBase.java` 448、`block/entity/WarpPlateBlockEntity.java` 436、`block/entity/WaystoneBlockEntityBase.java` 429、`store/PersistentWaystonesPlayerStore.java` 408、`command/ModCommands.java` 340、`core/PlayerWaystoneManager.java` 338、`config/WaystonesRules.java` 290、`InternalMethodsImpl.java` 273。

## 3. 入口与注册

common 侧主类 `net/blay09/mods/waystones/Waystones.java` 不写注解，实现 Balm 的 `BalmModule`，由平台层回调分发：

```java
public class Waystones implements BalmModule {                 // Waystones.java:52
    public static final String MOD_ID = "waystones";
    @Override public void registerBlocks(BalmBlockRegistrar blocks) { ModBlocks.initialize(blocks); }      // :97
    @Override public void registerNetworking(BalmNetworking n) { ModNetworking.initialize(n); }            // :92
    @Override public void registerConfig(BalmConfig config) { config.registerConfig(WaystonesConfig.class); } // :76
    @Override public void initialize() { /* 事件、HUD、compat 反射加载 */ }                                  // :153
}
```

- fabric：`fabric/.../fabric/FabricWaystones.java`（`ModInitializer`）→ `Balm.initializeMod(MOD_ID, FabricLoadContext.INSTANCE, new Waystones())`；neoforge：`neoforge/.../neoforge/NeoForgeWaystones.java`（`@Mod` 构造器注入 `IEventBus`/`ModContainer`）；forge：`forge/.../ForgeWaystones.java`。
- 注册框架是 **Balm 的 Registrar 体系**（`BalmBlockRegistrar`/`BalmItemRegistrar`/`BalmMenuTypeRegistrar`/`BalmDataComponentTypeRegistrar`/`BalmPoiTypeRegistrar`…），本仓库用「静态 Holder 字段 + initialize(registrar)」模式，而非 DeferredRegister 直接暴露。
- 变体批量注册：`block/ModBlocks.java:35-50` 用 Balm `DiscriminatedBlocks` 按类型集合注册 16 种 waystone / 15 种 sharestone / portstone，一次生成方块+物品+tooltip 组件。
- 可选的第三方兼容用字符串反射类名延迟加载：`Balm.initializeIfLoaded("bluemap", "net.blay09.mods.waystones.compat.BlueMapIntegration")`（`Waystones.java:165-167`）。

## 4. 核心系统

### (1) 传送点数据存储（store 包，8 文件）
- 职责：全局传送点库 + 每玩家个性化数据。
- 全局：`store/SavedDataWaystonesStore.java` 继承 `SavedData` 并实现 `WaystonesStore`，`RecordCodecBuilder` Codec 只序列化 `"Waystones"` 一个列表（`SavedDataWaystonesStore.java:21-31`），写操作后 `setDirty()`；`get(server)` 用 `server.getDataStorage().computeIfAbsent(TYPE)`（:88-90）。
- 装饰器链：`SavedDataWaystonesStore` 内部 = `EventfulWaystonesStore(new InMemoryWaystonesStore(...))`（:36）；`EventfulWaystonesStore` 是 record 形式的纯转发装饰器，只在 `updateWaystone/removeWaystone` 时触发 `WaystoneUpdatedEvent/WaystoneRemovedEvent`（`store/EventfulWaystonesStore.java:22-31`）。这是"存储与事件解耦"的干净做法。
- 玩家侧：接口 `WaystonesPlayerStore` 两实现——`PersistentWaystonesPlayerStore`（服务端，NBT 挂在玩家 persistent data 的 `"WaystonesData"` 下，含 `Waystones/SortingIndex/Aliases/Groups/HiddenWaystones/GroupRegistry` 六个子标签，`PersistentWaystonesPlayerStore.java:20-33`）与 `InMemoryWaystonesPlayerStore`（客户端）。`core/PlayerWaystoneManager.java:197-203` 按 `Level.isClientSide()` 单点切换实现，业务代码无需判断端。
- 自愈：读取已激活列表时对每个 UUID 建 `WaystoneProxy`，`isValid()` 为 false 就 `iterator.remove()` 顺手清理脏数据（`PersistentWaystonesPlayerStore.java:58-68`）；`core/WaystoneProxy.java:40-41` 的 `isValid()` 直接查 SavedData 存在性。

### (2) 网络与同步（network 22 文件 + `core/WaystoneSyncManager.java`）
- 19 个包全部是 `CustomPacketPayload` + `StreamCodec.composite` 记录类，注册集中在 `network/ModNetworking.java:8-29`（serverbound 12 / clientbound 7）。
- 全量推送在登录时一次完成：`handler/LoginHandler.java` 顺序 push sortingIndex → 默认组 → 动态组 → 组注册表 → 已激活传送点 → warp plate → 各色 sharestone。
- 增量同步：`WaystoneSyncManager.sendWaystoneUpdate(sendWaystoneUpdate:92-100)` 只对"已激活该传送点"的玩家发；`sendWaystoneRemovalToAll` 用 `getWaystoneAwareOnlinePlayers` 按 kind 过滤（`PlayerWaystoneManager.java:248-265`：fleeting memorial 只发拥有者、waystone 只发已激活者、其余全服）。
- 每人不同的数据（别名/分组/隐藏）由服务端"装饰"为 `PersonalizedWaystoneImpl` 再下发（`PlayerWaystoneManager.getPlayerDecoratedWaystone:179-189`、`ClientboundUpdateWaystonePacket.java`）；`PersonalizedWaystoneImpl.DOWNGRADED_STREAM_CODEC` 用于客户端不需要全部字段时降级编码（`PersonalizedWaystoneImpl.java:36-39`）。
- 安全：`ServerboundSelectWaystonePacket.java:26-46` 先校验所选 UUID 确实在服务端菜单列表里，再 `PlayerWaystoneManager.findWaystone` 重新解析，防伪造。

### (3) GUI 列表（menu 7 + client/gui 41 文件）
- 服务端菜单 `menu/WaystoneSelectionMenu.java` 携带 `Data(Optional fromWaystone, List<MutablePersonalizedWaystone> waystones, Map<UUID, Either<List<Object>,List<Object>>> warpRequirements)`，并自定义 `STREAM_CODEC` 一次过传输列表+需求（:29-47）；列表由 `menu/WaystoneSelectionListBuilder.java` 以流式 API 拼装（`withTargetsForItem`/`withInventoryButtonTargets`/`sorted`/`buildMenuProvider`，:46-172），`build()` 里抛 `BuildWaystoneSelectionMenuEvent` 供扩展。
- 客户端 `client/gui/screen/WaystoneSelectionScreenBase.java`：按传送点数量**动态计算界面高度**（`getLayoutImageHeight:134-155`），搜索框、排序按钮、分组过滤按钮均按需布局；`client/gui/widget/AbstractWaystoneList.java` 继承原版 `ContainerObjectSelectionList`，定义 `ENTRY_WIDTH=220/ENTRY_HEIGHT=22` 并让 Entry 复用 widget 列表渲染（:14-79）。
- 管理界面（分组、拖动排序、隐藏）复用同一基类：`ManageWaystonesScreen`/`ManageWaystoneGroupsScreen` + `ListDragController`/`DragHandleButton` 手写拖拽。

### (4) 权限与规则（config 16 文件 + Shogi 规则引擎）
- 配置类 `config/WaystonesConfig.java` 是 Balm 反射式 `@Config`，字段用 `@Synced`（下发客户端）/`@Comment`/`@NestedType` 注解（:19-136），`getActive()` 静态取当前配置。
- 细粒度规则外包给 **Shogi DSL**：`config/WaystonesRules.java:40-144` 用 `Shogi.scope(id("rules"), ...)` 注册 `is_waystone/is_owner/is_interdimensional/is_with_pets` 等一批"效果"，默认 warps 需求本身就是字符串规则（`WaystonesConfig.java:30-37`：`"$xp_points_cost = $distance * $xp_per_block"`、`"is_warp_stone -> damage_item(80)"`）。规则经 `CachedShogiRule` 缓存，配置重载时失效（`WaystonesRules.java:267-279`）。
- 把关函数返回"错误提示"而非布尔：`core/WaystonePermissionManager.mayEditWaystone` → `Optional<Component>`（:19-30），UI 直接显示；`isEntityDeniedTeleports` 读配置黑名单。

### (5) 传送执行（`core/WaystoneTeleportManager.java` 556 行）
- 全异步：`prepareTeleport = loadDestinationChunksAsync → validatePendingTeleport → resolveDestination`（:88-99），`tryTeleportAsync/forceTeleportAsync` 返回 `CompletableFuture`；校验包括实体是否仍有效、离开源石碑是否超范围、源物品是否还在（:111-130）。
- API 层保留废弃同步方法并注明原因（`api/WaystonesAPI.java:37-43`：新方法 `createUnchecked*` 避免同步加载目标区块），异步失败走 `crashOnUnexpectedAsyncFailure`。
- 生命周期事件 `WaystoneTeleportEvent`（Pre/Post/Complete + `WaystoneTeleportEntityEvent`）可被外部拦截。

### (6) 团队/全局可见性索引（`core/WaystoneIndexManager.java`）
用 Guava `SetMultimap<String teamName, UUID>` + `LinkedHashSet<UUID> globalWaystones` 建内存倒排索引，`ServerLifecycleCallback.Started` 时重建（`handler/ModEventHandlers.java:14`），队伍变动通过 `mixin/ServerScoreboardMixin.java:22-29` 在 `addPlayerToTeam/removePlayerFromTeam` 后刷新；查询时 `getTargets(player)` 合并全局+本队（:23-55）。避免每次开 GUI 全表扫描。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：见 4(2)。统一 `CustomPacketPayload.Type<>(id("xxx"))` + `StreamCodec.composite`，无自定义 channel 管理代码。
- **数据驱动**：common 内**无 data/ 资源文件**（仓库快照 assets/data 为空，资源不在本仓库或未纳入快照）。结构注入是运行时行为——`mixin/SinglePoolElementMixin.java`（`place` HEAD cancellable 注入传送石碑结构元素）、`mixin/JigsawPlacementPlacerMixin.java`（`@ModifyArg` 改 `tryPlacingChildren` 的 `Registry.get`）、`mixin/StructureTemplatePoolAccessor.java`，配合 `worldgen/ModWorldGen.java` 动态改村庄模板池。世界生成风格/名字生成由 `worldgen/namegen/` 12 个生成器（MrPork/Biome/Template/Custom/Mixed）实现，配置驱动。
- **数据包条件**：`resources/ForceSpawnInVillagesCondition.java`（BalmResourceCondition，Codec unit），在 `Waystones.java:148-150` 注册为 `"force_spawn_in_villages"`。
- **配置**：`config/WaystonesConfig.java`（反射式 @Config，@Synced 项 = 服务端权威 + 下发）；迁移逻辑 `config/ConfigMigration.java` + `migration/MigrationUtils.java`（旧配色 sharestone→新材质、旧 visibility 字符串→枚举、`blocks.addAlias` 处理方块/物品 ID 重命名，:16-148），并在 `Waystones.java:78-83` 于配置可用时自动迁移。
- **datagen**：只在 fabric 模块，`fabric/src/main/java/net/blay09/mods/waystones/datagen/` 7 个 provider（BlockTag/ItemTag/BiomeTag/LootTable/Model/Recipe/主类），输出目录 `common/src/generated/resources`（`fabric/build.gradle` 的 `-Dfabric-api.datagen.output-dir`），再经 `multiloader-loader.gradle` 的 `commonGeneratedResources` 配置打进所有加载器 jar。

## 6. Mixin

配置：`common/src/main/resources/waystones.mixins.json`（package `net.blay09.mods.waystones.mixin`，required，6 个 mixin）；加载器级空配置 `waystones.fabric.mixins.json`、`waystones.neoforge.mixins.json`、`waystones.forge.mixins.json`；jar manifest 里 `MixinConfigs` 统一声明（`multiloader-common.gradle`）。

| 类 | 目标 | 注入点 |
|---|---|---|
| `mixin/EntityMixin.java` | `Entity`（并 `implements WaystoneTeleportedEntity`） | `saveWithoutId` HEAD / `load` HEAD 存读 `WaystonesTicksOnWarpPlate` 等 NBT，`tick` TAIL 委托 `WarpPlateBlockEntity.tickEntityWarpPlateState`（:60-76）|
| `mixin/ServerScoreboardMixin.java` | `ServerScoreboard` | `addPlayerToTeam`、`removePlayerFromTeam(String, PlayerTeam)` RETURN → 刷新团队索引 |
| `mixin/SinglePoolElementMixin.java` | `SinglePoolElement` | `place(...)` HEAD cancellable → 村庄结构插入传送石碑 |
| `mixin/JigsawPlacementPlacerMixin.java` | `JigsawPlacement$Placer` | `@ModifyArg` on `tryPlacingChildren` 内 `Registry.get` |
| `mixin/StructureTemplatePoolAccessor.java` | `StructureTemplatePool` | `@Accessor` |
| `mixin/DimensionStorageFileFixMixin.java` | `DimensionStorageFileFix` | `makeFixer` RETURN（存档数据修复） |

## 7. 值得学的 5 条具体做法

1. **存储接口 + 装饰器分层**：`WaystonesStore` 接口下 `InMemory`（数据）→`Eventful`（事件）→`SavedData`（持久化）三层组合，同一接口在客户端用 InMemory 实现（`store/EventfulWaystonesStore.java`、`WaystonesClient.java:23`）。适用：任何"服务端持久化 + 客户端镜像"的数据系统。
2. **单点分端**：`PlayerWaystoneManager.getPlayerWaystoneData(level)` 用 `isClientSide()`/`BalmEnvironment` 二选一返回 store（:197-203），业务层完全不写 `if (client)` 分支。
3. **每人一份的"装饰视图"**：原始 `Waystone` 不动，把别名/分组/隐藏包成 `PersonalizedWaystoneImpl` 随包下发（`PlayerWaystoneManager.getPlayerDecoratedWaystone:179-189`），多人数据天然隔离、也不用在客户端拼权限判断。
4. **广播按需裁剪**：`getWaystoneAwareOnlinePlayers` 依据 waystone 种类决定发给谁（`PlayerWaystoneManager.java:248-265`），避免全服广播敏感位置。
5. **把"代价/门槛"外置为可编辑规则字符串 + 缓存**：`warpRequirements` 是玩家可改的字符串列表（`WaystonesConfig.java:30-37`），运行时编译为 Shogi 规则并用 `CachedShogiRule` 缓存、仅配置重载时失效（`config/WaystonesRules.java:146-147,267-279`），同时用 `migration/MigrationUtils.java:18,74-148` 的 `Codec.withAlternative` + `registrar.addAlias` 保证旧存档/旧配置平滑升级。

## 8. 公开 API（本 mod 有稳定 API 包）

- 包路径：`net.blay09.mods.waystones.api`（28 文件）+ `api/client`、`api/event`（15）、`api/trait`（5）、`api/error`。
- 门面：`api/WaystonesAPI.java` 全静态方法（`createUncheckedDefaultTeleportContext`/`tryTeleportAsync`/`placeWaystone`/`createBoundScroll`/`getDynamicWaystoneGroups` …），实现**通过反射桥接**到根包的 `InternalMethodsImpl`（:27-35 `Class.forName("net.blay09.mods.waystones.InternalMethodsImpl")`），使内部实现类不出现在 API 包里。
- 数据模型：接口 `Waystone`/`MutableWaystone`/`PersonalizedWaystone`/`WaystoneGroup`/`WaystoneTeleportContext`/`WaystoneVisibility`/`WaystoneKinds`（+ 类型注册器 `WaystoneTypes`/`SharestoneTypes`/`PortstoneTypes`/`WarpStoneTypes`），错误用 `Either<结果, WaystoneTeleportError>` 而非异常。
- 扩展点：14 个事件（`api/event/`：`WaystoneActivatedEvent`、`WaystoneTeleportEvent`、`BuildWaystoneSelectionMenuEvent`、`CollectDefaultWaystoneGroupsEvent`、`GenerateWaystoneNameEvent`、`WaystonesLoadedEvent`…）；`api/trait/`（`WaystoneKindScoped`、`IAttunementItem`、`IFOVOnUse`、`IResetUseOnDamage`）供物品实现；`api/client/WaystonesClientAPI` 给客户端模组。
- 第三方接入范式：另加载器模块仅写 `Compat` 类 + `Balm.initializeIfLoaded("modid", "包名.类名")` 反射懒加载（`Waystones.java:165-167`，compat 包 6 个集成：JourneyMap/BlueMap/Dynmap/Unbreakables/RepurposedStructures/hudinfo）。
