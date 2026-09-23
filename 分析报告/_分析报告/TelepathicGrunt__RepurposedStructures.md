# TelepathicGrunt/RepurposedStructures 源码分析报告

## 1. 基本信息

- Mod 名：Repurposed Structures；`mod_id=repurposed_structures`；作者：TelepathicGrunt（+2 位结构捐赠者），版本 7.7.6
- 目标版本：`gradle.properties` 中 `minecraft_version=26.1`、`neoforge_version=26.1.2.20-beta`、`fabric_api_version=0.144.0+26.1`、`fabric_loader_version=0.18.4`；Java 25（`build.gradle:12` `def javaVersion = 25`）
- 构建：MDG（`net.neoforged.moddev` 2.0.141）+ `net.fabricmc.fabric-loom` 1.15-SNAPSHOT 三模块多加载器结构（`settings.gradle` 末尾 `include 'common', 'fabric', 'neoforge'`），发布用 `me.modmuss50.mod-publish-plugin`
- 许可证：LGPL-3.0（`gradle.properties` `license=GNU Lesser General Public License v3.0`）
- 编译依赖：`common` 无 mod 依赖；运行/平台侧依赖 midnightlib 1.9.2、ModMenu 18.0.0-alpha.7（`gradle.properties` Libraries 段）。它本身不是库，但内部有可复用的注册抽象与结构生成器（见第 8 节）。注意：MC 26.1 已把 `ResourceLocation` 改名为 `net.minecraft.resources.Identifier`（全局可见）

## 2. 源码规模与包结构

- 194 个 `.java`，15876 行；`common` 160 个文件、`neoforge` 18、`fabric` 16
- 主包 `com.telepathicgrunt.repurposedstructures`（下按文件数）：`world/features` 32、`world/processors` 26、`world/features/configs` 13、`mixins/features` 11、`world/structures` 9、`modinit/registry` 9、`modinit` 9（注册清单类）、`mixins/structures` 8、`world/structures/pieces` 6、`events/lifecycle` 6、`services` 2、`misc/structurepiececounter` 2、`misc/mobspawners` 2、`misc/lootmanager` 2
- 最大文件：`common/.../world/structures/pieces/MansionPieces.java`(1187)、`MonumentPieces.java`(826)、`utils/OpenSimplex2F.java`(782)、`world/structures/pieces/PieceLimitedJigsawManager.java`(621)、`utils/GeneralUtils.java`(439)、`world/structures/GenericJigsawStructure.java`(412)、`world/features/NbtDungeon.java`(330)、`world/features/StructureBreakage.java`(274)
- 仓库资源极薄：全仓仅 3 个 json、0 个 nbt（`common/src/main/resources` 只有 mixins.json 与 `META-INF/accesstransformer.cfg`），结构 NBT/数据包 JSON 不在本仓库内（是否由外部仓库/datagen 产出：未确认）

## 3. 入口与注册

- 公共入口 `common/src/main/java/com/telepathicgrunt/repurposedstructures/RepurposedStructures.java:46` `init()`：按顺序 `RSTags.initTags()` → `StructureModdedLootImporter.createMap()` → 各注册表 `init()`（`RSFeatures`、`RSPredicates`、`RSStructures`、`RSPlacements`、`RSProcessors`、`RSStructurePieces`、`RSStructurePlacementType`、`RSConditionsRegistry`）→ 注册三个生命周期事件监听；平台入口 `neoforge/.../neoforge/RepurposedStructuresNeoforge.java:23`（`@Mod(RepurposedStructures.MODID)`）、`fabric/.../RepurposedStructuresFabric.java`（`ModInitializer`）
- 注册框架：自研 `ResourcefulRegistry<T>`（`modinit/registry/ResourcefulRegistry.java`）接口 = `register(String id, Supplier<I>)` 返回 `RegistryEntry<I>`（延迟绑定，可 `get()`/`getKey()`）；平台实现由 ServiceLoader 选择（`services/ResourcefulRegistriesService.java:12` `INSTANCE = GeneralUtils.loadService(...)`），`NeoForgeResourcefulRegistry` 包 `DeferredRegister`，Fabric 侧 `CustomResourcefulRegistry` 直接写 Registry
- 注册声明极短，例如 `modinit/RSStructures.java:24`：`STRUCTURE_TYPE.register("generic_jigsaw_structure", () -> () -> GenericJigsawStructure.CODEC)`（双重 Supplier 让 codec 延迟求值）

## 4. 核心系统

1. **带配额/必需件的拼图生成器**：`world/structures/pieces/PieceLimitedJigsawManager.java`（原版 `JigsawPlacement` 的分支重写）。`Assembler` 内部三个 map：`currentPieceCounts` / `maximumPieceCounts` / `requiredPieces`（:240-242），选件时先跳过超上限候选（:434-436），`processList` 用 `BoxOctree` 做整体包围盒约束（:174 `new BoxOctree(axisAlignedBB)`）；生成完再校验 `doesNotHaveAllRequiredPieces`（:211）。可精确控制"每个结构最多/最少刷多少个 NBT 房间"。
2. **数据包驱动的结构件配额**：`misc/structurepiececounter/StructurePieceCountsManager.java`（`SimpleJsonResourceReloadListener`，`FileToIdConverter.json("rs_pieces_spawn_counts")`），JSON 字段 `target_structure` / `pieces_spawn_counts` / `alwaysSpawnThisMany` / `neverSpawnMoreThanThisMany` / `condition`（条件走 `RSConditionsRegistry` 查找，:38-50）。带缓存 `cachedRequirePiecesMap` / `cachedMaxCountPiecesMap`（:25-26）；类里注释明确警告"复制此类必须换掉目录字符串"，否则两个 mod 会重复读同一文件。
3. **用 tag + mixin 抑制原版地物落进结构**：`mixins/features/` 下 11 个 mixin（`NoLakesInStructuresMixin`、`LessBambooInStructuresMixin`、`NoGeodesInStructuresMixin`、`SmarterSnowPlacingInStructuresMixin` 等）。统一模式：`@Inject(method="place(...)Z", at=HEAD, cancellable=true)` → 用 `GeneralUtils.inboundsValidStartsForAllStructure(worldGenRegion, origin, struct -> ...is(RSTags.NO_LAKES))`（`utils/GeneralUtils.java:389`）判断该位置是否落在指定结构内，是则 `cir.setReturnValue(false)`。tag 定义集中在 `modinit/RSTags.java`（`NO_LAKES`/`LESS_BAMBOO`/`NO_GEODES`…），第三方 mod 也能加 tag 生效。
4. **通用结构类型族**：`world/structures/GenericJigsawStructure.java:52` 的 `CODEC` 暴露 `start_pool`/`start_height`/`size`/`y_allowance`/`project_start_to_heightmap`/`cannotSpawnInLiquid`/`terrainHeightCheckRadius`/`allowedTerrainHeightRange`/`biomeRadius`/`pools_that_ignore_boundaries`/`maxDistanceFromCenter`/`burying_type` 等字段（:70-83），配合 `MansionStructure`、`MineshaftEndStructure`、`StrongholdEndStructure`、`CityNetherStructure` 等特殊实现；`extraSpawningChecks` 做半径内生物群系校验（:126-138）。
5. **跨平台事件抽象层**：自研 `events/lifecycle`（`SetupEvent`、`RegisterReloadListenerEvent`、`ServerGoingToStartEvent`、`ServerGoingToStopEvent`、`ServerGoingToStopEvent`）——每个事件是一个包装 `Consumer` 列表的 EVENT 对象；NeoForge 侧在 `RepurposedStructuresNeoforge` 把 `FMLCommonSetupEvent`/`AddServerReloadListenersEvent`/`ServerAboutToStartEvent` 转发进来（:52-67），Fabric 侧在 `RepurposedStructuresFabric.onInitialize` 转发（同样几行）。公共代码因此完全不引用平台 API。
6. **结构破坏/后处理特性组**：`world/features/StructureBreakage.java`（可破坏结构方块）、`StructurePostProcessConnectiveBlocks`、`MineshaftSupport`、`NbtDungeon`，以及 `world/processors` 下 26 个 `StructureProcessor`（结算结构生成时的方块替换/衰减）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包（未发现网络注册类）
- 数据驱动：三个 datapack reload listener 在 `RepurposedStructures.registerDatapackListener` 里注册——`rs_spawners`(MobSpawnerManager)、`rs_pieces_spawn_counts`(StructurePieceCountsManager)、`rs_pool_additions`(PoolAdditionMergerManager)；`misc/pooladditions` 支持把额外结构池合并进已有池
- 配置：`RSModdedLootConfig`（平台各一份）+ NeoForge `RSConfigHandler.setup` 注册 `ModConfig.Type.COMMON` 到 `repurposed_structures-neoforge/modded_loot.toml`，并在 `ModConfigEvent.Loading/Reloading` 时把值 `copyToCommon()` 同步进 common 静态字段（`configs/neoforge/RSConfigHandler.java:13-31`）——这是多加载器下共享配置的实用套路
- datagen：`neoforge/.../datagen/StructureNbtUpdater.java`（基于 ImmersiveEngineering 的 StructureUpdater 思路，用 DataFixer 批量升级结构 NBT）；另 NeoForge 侧有 `RSBiomeModifiers`、`RSGlobalLootModifier`

## 6. Mixin

- 配置：`common/src/main/resources/repurposed_structures-common.mixins.json`（`required:true`、`compatibilityLevel: JAVA_25`、`injectors.defaultRequire: 1`，23 个 mixin）、`repurposed_structures-neoforge.mixins.json`（空）、`repurposed_structures-fabric.mixins.json`；NeoForge 在 `neoforge.mods.toml` 用两个 `[[mixins]]` 条目同时挂载
- 代表类与目标：
  - `mixins/features/NoLakesInStructuresMixin.java` → `LakeFeature#place(FeaturePlaceContext)Z` 的 HEAD，`@Inject cancellable`
  - `mixins/structures/StructurePoolMixin.java` → `StructureTemplatePool` 静态 lambda 里的 `Codec.intRange(II)`，用 MixinExtras `@WrapOperation` 把权重上限从原版值改成 5000（注释指出是绕 MC-203131），并设 `priority=1200`、`require=0`
  - `mixins/structures/` 里还有大量 `@Accessor`（`StructurePoolAccessor`、`SinglePoolElementAccessor`、`TemplateAccessor`、`PoolElementStructurePieceAccessor`）供 `PieceLimitedJigsawManager` 读原版私有字段；`LocateCommandMixin` 改定位命令
  - `mixins/entities/ShulkerEntityInvoker`（`@Invoker`）、`StructureBlockScreenMixin`（client-only 结构方块界面）
- 另有 `accesstransformer.cfg`（common 内，本次读取显示为空文件）

## 7. 值得学的 5 条具体做法

1. **"tag 决定哪些结构不吃哪些原版地物"**：把抑制逻辑写成通用 `@Inject(HEAD, cancellable)` + `inboundsValidStartsForAllStructure()` 查询，新增结构只要打 tag 即可，无需改 mixin。文件：`mixins/features/NoLakesInStructuresMixin.java`、`utils/GeneralUtils.java:389`。适用：自建结构需要保证内部不被湖泊/峡谷/竹丛破坏。
2. **结构件数量配额数据包**：`StructurePieceCountsManager` + `PieceLimitedJigsawManager` 组合，让整合包作者用 JSON 控制"某结构必刷 N 个 Boss 房、最多 1 个藏宝室"。适用：地牢类结构想避免随机生成导致房间缺失/刷爆。
3. **ServiceLoader 平台抽象**：`services/*.java` 只定义接口 + `INSTANCE = GeneralUtils.loadService(...)`，实现放各平台模块并在 `META-INF/services` 声明；配合 `events/lifecycle` 包装事件，common 代码零平台 API。适用：任何想一份代码双加载器的 mod。
4. **配置在平台上注册、值回写 common 静态字段**：`RSConfigHandler.copyToCommon()` 于 Loading/Reloading 两个事件都执行。适用：多加载器共享同一份配置语义。
5. **自研 `ResourcefulRegistry` 包装注册**：`RegistryEntry` 延迟持有 + `stream()/boundStream()` 便于批量注册/tag 生成，NeoForge 下包 `DeferredRegister`、Fabric 下直连 `Registry`。文件：`modinit/registry/ResourcefulRegistry.java`。适用：需要同时支持 NeoForge 与 Fabric 的注册代码。

## 8. 可复用 API / 扩展点

- 不是前置库，但对外扩展点很明确：所有"结构件配额/刷怪/池合并"都读数据包（`rs_pieces_spawn_counts`、`rs_spawners`、`rs_pool_additions`，命名空间 `repurposed_structures`），第三方 mod 可用 `RSConditionsRegistry.RS_JSON_CONDITIONS_REGISTRY` 注册自定义 JSON 条件（`modinit/RSConditionsRegistry.java`），或往 `RSTags` 定义的 `repurposed_structures:no_lakes` 等结构 tag 里加入自己的结构
- `world/structures/codecs/` 提供自定义 codec（如 `YRangeAllowance`），`world/structures/placements/AdvancedRandomSpread.java` 是自定义 `StructurePlacement` 类型
