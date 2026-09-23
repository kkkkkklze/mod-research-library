# YUNG-GANG/YUNGs-Better-Dungeons 源码分析报告

## 1. 基本信息

- Mod 名：YUNG's Better Dungeons；mod_id `betterdungeons`；作者 YUNGNICKYOUNG, Tera
- 目标版本：`gradle.properties:2` version=6.1.1，`mc_version=26.1.2`、`mc_version_range=[26.1,)`；`java_version=25`
- 加载器：NeoForge `26.1.2.75` + Fabric（loader `0.18.6`，fabric-api `0.150.0`）
- Gradle 插件：`net.fabricmc.fabric-loom 1.15.5`、`net.neoforged.moddev 2.0.141`、darkhax curseforgegradle 1.1.24、minotaur（`build.gradle:3-6`）；`settings.gradle:15` `include("Common","Fabric","NeoForge")`
- 许可证：LGPLv3
- 编译依赖：**YUNGs-API 6.1.3 为硬前置**（neoforge.mods.toml 中 required）。代码直接引用 `yungsapi.api.YungAutoRegister`、`api.YungJigsawManager`、`api.autoregister.AutoRegister`、`world.spawner.MobSpawnerData`、`world.banner.Banner`、`world.structure.processor.ISafeWorldModifier`。Fabric 侧 cloth-config `26.1.154`

## 2. 源码规模与包结构

实测：**69 个 `.java`，4503 行**。主要包（第 3 层）：

| 包 | 文件数 |
|---|---|
| `betterdungeons.world.processor.zombie_dungeon` | 8 |
| `betterdungeons.world.processor.small_dungeon` | 8 |
| `betterdungeons.world.processor.small_nether_dungeon` | 6 |
| `betterdungeons.world.structure.spider_dungeon.piece` | 5 |
| `betterdungeons.world.processor` / `.module` | 4 / 4 |

最大文件：`SpiderDungeonBigTunnelPiece.java` 340、`ZombieMainStairsProcessor.java` 329、`SpiderDungeonSmallTunnelPiece.java` 274、`SpiderDungeonNestPiece.java` 237、`SpiderDungeonEggRoomPiece.java` 228、`SmallNetherDungeonBannerProcessor.java` 171、`SmallDungeonBannerProcessor.java` 150、`module/StructureProcessorTypeModule.java` 129。

## 3. 入口与注册

NeoForge 入口 `NeoForge/.../BetterDungeonsNeoForge.java:12`；Fabric 入口 `Fabric/.../BetterDungeonsFabric.java:7`。共同初始化 `Common/.../BetterDungeonsCommon.java:23-31`：`YungAutoRegister.scanPackageForAnnotations("...betterdungeons.module")` + SPI `Services.MODULES.loadModules()`，再 `LocateReplacer.registerRemoval(small_nether_dungeon, ..., () -> !CONFIG.smallNetherDungeons.enabled)`。

`module` 包四个类全部用 YUNGs-API 注解注册（无 DeferredRegister）：
- `StructureProcessorTypeModule.java:36` `@AutoRegister(MOD_ID)`，注册 **27 个 StructureProcessorType**（mob_spawner / head / nether_block / candle，外加 small_dungeon、small_nether_dungeon、skeleton_dungeon、zombie_dungeon 四组专属 processor）
- `StructureTypeModule`：`spider_dungeon`、`small_nether_dungeon`
- `StructurePieceTypeModule:10-18`：4 个 `StructurePieceType.ContextlessType` 方法引用（`SpiderDungeonBigTunnelPiece::new` 等）

## 4. 核心系统

1. **DungeonContext：processor 跨方块的共享状态**。`world/DungeonContext.java` 用 `ThreadLocal<DungeonContext>` 保存 `bannerCount` / `chestCount`（`WeakReference<Integer>`），提供静态 `initialize() / peek() / pop()`。投放时机由 `mixin/DungeonContextMixin.java:20-23` 保证：注入 `StructureTemplate#placeInWorld` 的 HEAD 调用 `DungeonContext.initialize()`。使用者如 `world/processor/small_dungeon/SmallDungeonBannerProcessor.java:105-123`：`peek()` 拿上下文，`getBannerCount() >= CONFIG.smallDungeons.bannerMaxCount` 就跳过，否则放旗并 `incrementBannerCount()`。这是"全体积内全局限量"的通用解法。
2. **占位方块驱动的 processor 家族（27 个）**。统一签名 `processBlock(LevelReader, jigsawPiecePos, jigsawPieceBottomCenterPos, blockInfoLocal, blockInfoGlobal, StructurePlaceSettings)`。设计模式：①模板里放占位方块，processor 识别后按配置替换或删除——`world/processor/HeadProcessor.java:30-34` 依 `CONFIG.general.enableHeads` 决定是否换成 `Blocks.CAVE_AIR`；②带参数的 processor 用 `RecordCodecBuilder` 暴露字段——`MobSpawnerProcessor.java:32-43` 要求 `"spawner_mob"`，找不到实体时**回退 zombie 并打 error**（60-69 行），再用 `MobSpawnerData.builder().spawnPotentials(WeightedList.of(new SpawnData(nbt,...)))` 造 NBT 写成 `Blocks.SPAWNER`；③旗子图案硬编码在静态字段里（`SmallDungeonBannerProcessor.java:56-88`，`Banner.Builder().pattern(BannerPatterns.CURLY_BORDER, DyeColor.WHITE)...customName("betterdungeons.small_dungeon.banner.skeleton","Vengeful Banner")`）。
3. **两条并存的结构生成路径**。Jigsaw 路线：`world/structure/SmallNetherDungeonStructure.java:41-70`，CODEC 暴露 `start_pool / start_jigsaw_name / size / start_height / x_offset_in_chunk / z_offset_in_chunk / use_expansion_hack / project_start_to_heightmap / max_distance_from_center / max_y / min_y / dimension_padding / liquid_settings`，`findGenerationPoint` 先判 `CONFIG.smallNetherDungeons.enabled` 再调 `YungJigsawManager.assembleJigsawStructure(...)`。纯代码路线：`world/structure/spider_dungeon/SpiderDungeonStructure.java:31-47`，用 `StructurePiecesBuilder.addPiece(startPiece)` + `startPiece.addChildren(startPiece, builder, random)` 递归构建整条 spider mineshaft（注释明写 "no blocks are actually placed yet"，两阶段：先布房间后放方块），配套 `SpiderDungeonPiece` 提供 `placeSphereRandomized(...)`、`decorateCave(...)`、`getInitialBoundingBox(pos).inflatedBy(64)` 等工具。
4. **配置单一真源 + 平台烘焙**。`module/ConfigModule.java` 为 POJO（general / zombieDungeons / smallDungeons / smallNetherDungeons 四组）。NeoForge 走 `ModConfigSpec`（`ConfigModuleNeoForge.java:13-31`，在 `LevelEvent.Load` 与 `ModConfigEvent` 时 bake）；Fabric 走 cloth-autoconfig（`Fabric/.../module/ConfigModuleFabric.java`，`Toml4jConfigSerializer` + save/load 监听）。
5. **原版地牢移除的平台差异**。`Fabric/.../module/VanillaRemovalModuleFabric.java:17-27` 用 `BiomeModifications.create(...).add(ModificationPhase.REMOVALS, ctx -> ctx.hasPlacedFeature(CavePlacements.MONSTER_ROOM), ctx -> ctx.getGenerationSettings().removeFeature(CavePlacements.MONSTER_ROOM))`（MONSTER_ROOM 与 MONSTER_ROOM_DEEP 各一次）；类注释说明 1.19 起 Forge/NeoForge 可纯资源化，故只在 Fabric 用代码。
6. **SPI 平台抽象**：`services/Services.java:8-17` 加载 `IPlatformHelper`（getPlatformName/isModLoaded/isDevelopmentEnvironment）与 `IModulesLoader`（`FabricModulesLoader` 额外 init Config 与 VanillaRemoval 两个 Fabric-only 模块）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**。
- 数据驱动：结构模板 JSON/NBT 与 biome modifier 资源**不在本快照内**（`src/main/resources` 下仅 `betterdungeons.mixins.json` 与 `neoforge.mods.toml`，`find . -name '*.nbt'` = 0）。
- 配置：见 4.4；含 `removeVanillaDungeons`（注释标明仅 Fabric 用）。
- datagen：**无**。

## 6. Mixin

`Common/src/main/resources/betterdungeons.mixins.json`：`required:true`、`compatibilityLevel:"JAVA_17"`、`defaultRequire:1`。
- `DungeonContextMixin` → target `StructureTemplate#placeInWorld`，`@At("HEAD")` @Inject（只为初始化 ThreadLocal 上下文）
- `accessor.BoundingBoxAccessor` → target `BoundingBox`，6 个 `@Accessor("minX"/"minY"/"minZ"/"maxX"/"maxY"/"maxZ")` setter（用于生成中动态收缩/扩张包围盒）

## 7. 值得学的 5 条具体做法

1. **用 ThreadLocal 上下文给 StructureProcessor 传状态**：`DungeonContext` + mixin 在 `placeInWorld` HEAD 初始化，实现"整座结构内最多 2 面旗 / 1-2 个箱子"这类全局约束（`world/DungeonContext.java`、`mixin/DungeonContextMixin.java`）。
2. **占位方块 + 配置开关控制可选装饰**：关闭功能时把头颅换 `CAVE_AIR`，而不是改模板（`world/processor/HeadProcessor.java:31-33`）。
3. **processor 参数走 CODEC 而非硬编码**：`Identifier.CODEC.fieldOf("spawner_mob")`，使同一 processor 类可服务多个怪物类型，并带出错回退（`MobSpawnerProcessor.java:32-69`）。
4. **Jigsaw 与手写 piece 两条路线按需选**：规则房间用 `YungJigsawManager`，需要程序化隧道/球形空腔的蜘蛛地牢用 `StructurePiecesBuilder` + 递归 `addChildren`（`SpiderDungeonStructure.java:38-46`）。
5. **平台专属能力用 SPI 模块延迟注入**：`FabricModulesLoader.loadModules()` 里才 `ConfigModuleFabric.init()` 和 `VanillaRemovalModuleFabric.init()`，Common 不需要知道 Fabric 存在（`Fabric/.../services/FabricModulesLoader.java`）。

## 8. 库 / API 说明

非库模组；本身是 YUNGs-API 的消费者，可作为"如何用 YUNGs-API 写大型结构模组"的参考样板（注解注册 → SPI 平台服务 → Common 单例 CONFIG → LocateReplacer 联动）。
