# hlysine/create_power_loader 源码分析报告

## 1. 基本信息

| 项 | 值（来源） |
|---|---|
| Mod 名 / mod_id | Create: Power Loader / `create_power_loader`（`gradle.properties`，`CreatePowerLoader.java:25`） |
| 作者 / 版本 | Lysine / `2.0.5-mc1.21.1` |
| 目标 MC / 加载器 | 1.21.1 `[1.21.1,1.22)` / NeoForge 21.1.228（`neoforge_version_range=[21.1.0,)`，loader `[4,)`） |
| Gradle | ModDevGradle，Java 21，Parchment 2024.11.17，`org.gradle.configuration-cache=false` |
| 许可证 | MIT（`neoforge.mods.toml` `license="${mod_license}"`） |

**依赖（重点是"它依赖谁"）**：Create `6.0.10-280`（`create_version_range=[6.0.0,)`，mandatory）、Ponder `1.0.82`、Flywheel `1.0.6`、**Registrate `MC1.21-1.3.0+67`**（注册框架）、**Sable `1.1.3` + sable-companion `1.5.0`（物理子世界 API）**、`simulated 1.1.0`（仅开发期）、JEI `19.21.0.247`（可选）。即：**Create 是它的 API，Registrate 是它的注册层，Sable 是它的坐标投影来源**。

## 2. 源码规模与包结构

实测 `find . -name '*.java' | wc -l` = **52**，总 **4225** 行。
- 顶层包 `com.hlysine.create_power_loader`：12 个 `CPL*` 类（Blocks/BlockEntityTypes/CreativeTabs/Tags/Recipes/Icons/PartialModels/Ponders/Datagen/Commands）+ 主类 + 客户端类。
- `content` 25 文件 2120 行，含子包 `andesitechunkloader`/`brasschunkloader`/`emptychunkloader`/`trains`。
- `mixin` 5、`ponder` 3、`config` 3、`compat` 2（Mods、SableCompat）、`command` 2（ListLoadersCommand、SummaryCommand）。

最大文件：`ChunkLoadManager.java` 308、`ponder/BrassChunkLoaderScenes.java` 279、`content/AbstractChunkLoaderBlockEntity.java` 264、`content/ChunkLoaderMovementBehaviour.java` 230、`command/ListLoadersCommand.java` 216、`command/SummaryCommand.java` 200、`content/trains/StationChunkLoader.java` 160、`CarriageChunkLoader.java` 158、`config/CPLConfigs.java` 145。

## 3. 入口与注册

主类 `src/main/java/com/hlysine/create_power_loader/CreatePowerLoader.java`，用 **Registrate** 而非 DeferredRegister：

```java
private static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MODID);
public CreatePowerLoader(IEventBus modBus, ModContainer container) {
    REGISTRATE.registerEventListeners(modBus);
    REGISTRATE.setCreativeTab(CPLCreativeTabs.MAIN);
    CPLTags.register(); CPLBlocks.register(); CPLBlockEntityTypes.register();
    CPLCreativeTabs.register(modEventBus);
    ChunkLoadManager.register(modEventBus);   // 注册 TicketController
    CPLConfigs.register(container);
    CPLDatagen.register();
    neoforgeBus.addListener(ChunkLoadManager::onServerWorldTick);
}
```

可学点：静态初始化块里 `REGISTRATE.setTooltipModifierFactory(ItemDescription.Modifier + TooltipModifier.mapNull(KineticStats.create(item)))`（`CreatePowerLoader.java:32-37`）一行接入 Create 风格 tooltip；方块/方块实体全部走 `.onRegister(movementBehaviour(new ChunkLoaderMovementBehaviour(...)))`、`.renderer(() -> XxxRenderer::new)`（`CPLBlocks.java:23-83`、`CPLBlockEntityTypes.java:15-37`）。客户端是独立入口：`@Mod(value = MODID, dist = Dist.CLIENT) CreatePowerLoaderClient` → `CPLPartialModels.register()` + `PonderIndex.addPlugin(new CPLPonders())`。

## 4. 核心系统

**① 区块票证管理 —— `content/ChunkLoadManager.java`**
- 用 NeoForge 的 `TicketController`：`new TicketController(asResource("chunk_load_manager"), ChunkLoadManager::validateTickets)`，在 `RegisterTicketControllersEvent` 注册（:28、:240）。
- 加载/卸载是**集合差分**：`updateForcedChunks` 对目标集合与已强制集合做 remove/force 双向 diff（:87-104）；所有 owner 统一用 `BlockPos` 或 `UUID` 传给 `forceChunk`（:139-147）。
- 存读回填：`validateTickets(helper)` 在存档加载时把 ticking ticket 交给方块实体 `reclaimChunks()`，实体 ticket 暂存 `savedForcedChunks` 并设 100 tick 倒计时后统一回收（:33-37、:153-206）。世界卸载时禁止卸载：`enqueueUnforceAll` 入队，避免在错误时机 unforce。
- 记录类型当 Map key：`record DimensionalBlockPos(ResourceLocation dimension, BlockPos pos)` + `record LoadedChunkPos(...)`，且额外提供 `chunkEquals`（:248-307）。

**② 加载器抽象 —— `content/ChunkLoader.java` + `LoaderType`/`LoaderMode` + `WeakCollection.java`**
- 一个接口 4 个方法（`getForcedChunks/getLoaderMode/getLoaderType/getLocation`）+ `addToManager/removeFromManager` 默认方法；`LoaderMode` 枚举区分 STATIC/CONTRAPTION/TRAIN/STATION，`allLoaders` 用 `Map<LoaderMode, WeakCollection<ChunkLoader>>` 存弱引用（:43-51）。

**③ 动力方块实体 —— `content/AbstractChunkLoaderBlockEntity.java`（extends `KineticBlockEntity`）**
- 只在 `needsUpdate()` 时改票（:127-133、:153-156）：比较 `getProjectedBlockPos()/canLoadChunks()/getLoadingRange()` 三个快照字段，避免每 tick 刷票。
- 卸载宽限：`chunkUnloadCooldown >= unloadGracePeriod` 才真卸载，否则按 `chunkUpdateInterval` 递增（:168-173）。
- 转速要求随范围指数上升：`minSpeed * 2^getLoadingRange() * speedMultiplier`（:198）。
- 挂车站用 blockstate `ATTACHED` 属性 + `updateAttachedStation`，并处理"GlobalStation 下一 tick 才创建"的延迟（:75-94）。

**④ 装置/列车集成**
- `ChunkLoaderMovementBehaviour`（implements `MovementBehaviour`）：在 `startMoving/visitNewPosition/tick/stopMoving` 里操作 `context.temporaryData` 中的 `SavedState`，并且**只有跨越 chunk 才更新**（:74）；`disableBlockEntityRendering() = true`；`CarriageContraption` 返回 false 交给列车专用逻辑（:176-182）。
- `content/trains/StationChunkLoader.java`：以 `station.id`(UUID) 为 owner，`attachments` 集合记录挂载点，`tick(graph, preTrains)` 时清洗非法 attachment（距车站 >1 格丢弃），并由 `write()/read()` 列表化 NBT 持久化（:123-159）。

**⑤ 配置与 GUI 控件 —— `config/CPLConfigs.java`、`brasschunkloader/BrassChunkLoaderBlockEntity.java`**
- 用 Create 的 `net.createmod.catnip.config.ConfigBase`：`new ModConfigSpec.Builder().configure(builder -> { T c = factory.get(); c.registerAll(builder); return c; })`，按 `ModConfig.Type` 存 `EnumMap`；同时把配置接入 `BlockStressValues.IMPACTS.registerProvider(stress::getImpact)`（:24-32）——**这是给动力方块声明应力系数的正确姿势**。
- 黄铜装载器用 `ScrollOptionBehaviour<LoadingRange>` + 自定义 `CenteredSideValueBoxTransform`（覆写 `getSouthLocation` 算出 15.5 格的贴面位置、`getLocalOffset` 沿 FACING 内缩 4px）+ `INamedIconOptions` 枚举（3 档 1x1/3x3/5x5）与自定义 `CPLIcons extends AllIcons`（自带 `ICON_ATLAS`）；`loadingRange.onlyActiveWhen(() -> !getValue(ATTACHED))`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自建包**。全仓库 grep 无 `RegisterPayloadHandlersEvent`/`CustomPacketPayload`/`PacketDistributor`；状态同步完全复用 Create `KineticBlockEntity` 的 `write/read(compound, registries, clientPacket)`（`AbstractChunkLoaderBlockEntity.java:222-232` 加一个 `CoreActive` 布尔）。
- **配置**：仅 SERVER 类型（`CPLConfigs.register(container)`），每个 LoaderType 一份 `getFor(type)` 子配置（chunkUpdateInterval / unloadGracePeriod / speedMultiplier / enableStatic / enableContraption / enableStation / rangeOnContraption / rangeOnStation）。文件里还留了一个手写 `TomlGroup` 用于旧配置转换（:89-144）。
- **datagen**：极简，只有实体标签：`REGISTRATE.addDataGenerator(ProviderType.ENTITY_TAGS, CPLDatagen::genEntityTags)`，产出 `CHUNK_LOADER_CAPTURABLE`（内含 Ghast）（`CPLDatagen.java`）。`CPLTags` 提供了 Create 风格的 `forgeTag/optionalTag` 与 `NameSpace` 枚举模板（1.21 用 `c:` 命名空间）。
- **JEI**：不写自己的 category，而是改 Create 的 `MysteriousItemConversionCategory.RECIPES` 添 `ConversionRecipe.create(空 → 运行)`（`CPLRecipes.java`），并用 `compat/Mods.java` 的 `executeIfInstalled(() -> ...)` 做软依赖。
- **Ponder**：`CPLPonders implements PonderPlugin`，`forComponents(CPLBlocks.BRASS_CHUNK_LOADER).addStoryBoard("brass_chunk_loader/basic_usage", BrassChunkLoaderScenes::basicUsage, AllCreatePonderTags.KINETIC_APPLIANCES)`，共 6 个 storyboard（`CPLPonders.java`）；场景内用 `CreateSceneBuilder` + `scene.effects().rotationSpeedIndicator()` 等。
- **命令**：`/powerloader summary|list`（权限 2）并注册 `/pl` 别名，别名用 Velocity 的 Brigadier `redirect` 实现类复制（`CPLCommands.java`）。

## 6. Mixin

配置：`src/main/resources/create_power_loader.mixins.json`（`required=true`、`compatibilityLevel=JAVA_21`、带 `refmap` 与自定义 `plugin: ...mixin.MixinPlugin`）。
- `GlobalRailwayManagerMixin` → `GlobalRailwayManager#removeTrain(UUID)`、`#tick(Level)`（两个注入点，把 `ChunkLoadManager.tickLevel` 设为当前 tick 的 level）
- `GlobalStationMixin`（implements `CPLGlobalStation`）→ `GlobalStation#read/write(CompoundTag...)` 与 `read/write(FriendlyByteBuf...)`，为 station 附加 chunk loader 数据
- `TrackEdgePointMixin` → `TrackEdgePoint#tick(TrackGraph,boolean)`、`#removeFromAllGraphs()`
- `TrainMixin`（implements `CPLTrain`）→ `Train#write/read(...,DimensionPalette)`、`#tick(Level)`
- `MixinPlugin implements IMixinConfigPlugin`：`onLoad` 里 `Class.forName("...CreatePowerLoader")` 探测主类，`shouldApplyMixin` 返回探测结果 —— 目的写在注释里：让 Forge 的 "mods not found" 界面正常弹出而不是崩在 mixin。

## 7. 值得学的 5 条做法

1. **用 `TicketController` + `validateTickets` 做"可持久化、可自愈"的区块加载**：加载存档时读回 ticket 并回填到方块实体，找不到实体就 `helper.removeAllTickets(pos)` 清理死票（`ChunkLoadManager.java:153-206`）——任何"强制区块/强制加载"类需求直接照搬。
2. **跨 tick 安全性靠"延迟卸载队列 + 倒计时"而不是立即卸载**：`unforceQueue` + `savedChunksDiscardCountdown = 100`，解决世界/结构卸载期的非法时机问题（`ChunkLoadManager.java:33-72`）。
3. **用 `context.temporaryData` + 自定义 `SavedState` 在移动装置里挂状态**（`ChunkLoaderMovementBehaviour.java:184-229`），`stopMoving` 时把 `dimension/blockPos` 置 null 以强制下次重新判定 —— 传送门往返场景的正确处理。
4. **`ConfigBase` + `EnumMap<ModConfig.Type, ConfigBase>` + `BlockStressValues.IMPACTS.registerProvider`**：Create addon 配置与应力系统的标准接法，一行把配置值变成应力系数（`CPLConfigs.java:24-32`）。
5. **`IMixinConfigPlugin` 探测主类再决定是否应用 mixin**，让缺依赖时表现为"缺 mod"而非崩溃（`mixin/MixinPlugin.java`）——所有强制 mixin 进 Create 的 addon 都该加。

## 8. 公开 API

非库/前置 mod，无对外 API 包。其 `content/ChunkLoader` 接口与 `compat/SableCompat.java`（`projectOutOfSubLevel` 把子世界坐标投影到主世界坐标）仅供本 mod 内部与 Sable 版本兼容使用。
