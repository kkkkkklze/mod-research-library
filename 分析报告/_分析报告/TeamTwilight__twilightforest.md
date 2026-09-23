# TeamTwilight/twilightforest 源码分析报告

## 1. 基本信息

- Mod 名：The Twilight Forest（暮色森林）；`mod_id=twilightforest`；作者：Benimatic 等 10 余人，现维护者 GizmoTheMoonPig 等；`mod_version=4.8`
- 目标版本：`gradle.properties` `minecraft_version=26.1.2`、`neoforge_version=26.1.2.102`、`mdg_version=2.0.141`；Java 25；许可证 LGPL-2.1（`neoforge.mods.toml`）
- 构建：MDG 单模块 + 三个 source set（`src/main` 1614 文件 / `src/data` 78 / `src/asm` 30，见 `build.gradle:145` `'asm' { it.sourceSet project(":asm")... }`），`jarJar implementation(project(":asm"))` 把 ASM 处理器内嵌进主 jar；用 shadowJar 9.4.1 把 `tamaized.*` 重定位成 `twilightforest.*`（`build.gradle:52-56`）
- 编译依赖（`build.gradle:139` 附近）：`com.github.IAFEnvoy.Integration`（jarJar）、`tamaized:beanification:1.9.130`（gradle 插件 + 运行时 DI 容器）、curse.maven `uranus`/`jupiter`；`compileOnly` JEI/REI/EMI、curios 15.0.0-beta.1、TOP。**它是"依赖别人 API"的一方，不对第三方提供 API mod**

## 2. 源码规模与包结构

- 1736 个 `.java`，162788 行（`src/main` 1614、`src/data` 78、`src/asm` 30）
- 主要包（`src/main/java/twilightforest`，括号内文件数）：`block`(119)、`client/renderer/entity`(72)、`client/model/entity`(61)、`item`(56)、`init`(54)、`entity/ai/goal`(44)、`entity/monster`(43)、`client/state/entity`(35)、`world/components/structures/finalcastle`(32)、`util`(32)、`network`(30)、`block/entity`(26)、`world/components/structures/stronghold`(26)、`entity/boss`(20)、`world/components/structures/*`（darktower/lichtower/courtyard/icetower 等共约 250 个）、`world/components/feature`(21)、`command`(17)
- 最大文件：`world/components/structures/lichtower/TowerWingComponent.java`(1887)、`darktower/DarkTowerMainComponent.java`(1457)、`entity/boss/Lich.java`(1096)、`darktower/DarkTowerWingComponent.java`(1067)、`entity/boss/HydraHeadContainer.java`(982)、datagen 侧 `assets/LangGenerator.java`(1318)、`data/loot/ChestLootTables.java`(1136)、`data/recipes/CraftingGenerator.java`(1052)
- 仓库内几乎没有成品资源文件：`src/main/resources` 只有 `META-INF/accesstransformer.cfg`、`META-INF/neoforge.mods.toml`，0 个 json/nbt（`src/generated/` 仅 README.txt），全部数据与素材由 datagen 产出

## 3. 入口与注册

`src/main/java/twilightforest/TwilightForestMod.java:32` `@Mod(TwilightForestMod.ID)` 构造器里一次性注册约 50 个 `DeferredRegister`（`TFItems.ITEMS.register(bus)` 到 `TemplateMarkerHandlers.TEMPLATE_MARKER_HANDLER_TYPES.register(bus)`），并 `TFRemapper.addRegistryAliases()` 做旧 ID 别名迁移；静态块执行 `BeanContext.init(ID)`（Beanification 依赖注入容器，全仓 `@Component`/`@Autowired` 约 111 处，如 `command/ClearDisplayCommand.java:14`）。注册类集中在 `init/` 54 个 `TF*` 类，命名规整：`TFItems`/`TFBlocks`/`TFEntities`/`TFDataComponents`/`TFDataAttachments`/`TFStructureTypes`…；`init/custom/` 放"需要额外编码的数据包注册表初始内容"（`Restrictions`、`Enforcements`、`BiomeLayerStack`、`TravellersModifierTypes`）。自定义注册表走 `TFRegistries.java`：`new RegistryBuilder<>(Keys.ENFORCEMENT).sync(true).create()`（6 个自建 registry，其中 3 个 `sync(true)`），另有 14 个纯 datapack registry key（`restrictions`、`biome_layer_stack`、`biome_terrain_data`、`wood_palettes`、`magic_paintings`、`template_marker_handler`、`structure_speleothem_settings` 等）；`mods.toml` 声明 `enumExtensions="META-INF/enumextensions.json"`，配合 `TFEnumExtensions.java` 给 `DamageEffects`/`Rarity` 等原版枚举扩展成员（NeoForge 枚举扩展机制，仓库内不含该 json 产物）

## 4. 核心系统

1. **进度门禁（progression lock）**：`util/Restriction.java`（record：`hintStructureKey`/`enforcement`/`multiplier`/`lockedBiomeToast`/`advancements`，带 CODEC，走 datapack registry `twilightforest:restrictions`）+ `util/Enforcement.java:14` `enforceBiomeProgression(player, level)`（按生物群系查 Restriction，再从 `TFRegistries.ENFORCEMENT` 取出 `TriConsumer<Player,ServerLevel,Restriction>` 执行），触发点 `events/ProgressionEvents.java:210`；`EnforceProgressionStatusPacket` 同步到客户端。改整合包只需改 JSON。
2. **结构体系**：`init/TFStructures.java` + `TFStructureSets.java` 用 `BootstrapContext` 生成 25 个结构；自定义摆放器 `world/components/structures/placements/LandmarkGridPlacement.java`、`AvoidLandmarkGridPlacement.java`（按"地标网格"排布，保证 BOSS 结构间距），`structures/start/TFStructureStart.java` 额外持久化 `conquered` 布尔（`createTag`/`loadFromTag`/`setConquered`），配合 ASM transformer `conquered/StructureStartLoadStaticTransformer` 在反序列化时注入；`structures/util/` 下用一堆能力接口组合结构（`ConquerableStructure`、`ProgressionStructure`、`AdvancementLockedStructure`、`LandmarkStructure`、`StructureHints`、`ControlledSpawningStructure`）
3. **数据包化的模板标记处理**：`world/components/structures/markerhandler/` + registry `template_marker_handler` / `template_marker_handler_list`，让结构 NBT 里的 marker 行为由数据包配置（`TFStructureHelper`、`util/jigsaw`），替代硬编码；`world/components/chunkblanketing/` 的 `ChunkBlanketProcessor`（数据包注册）用于"整片区域铺方块"的地形改造
4. **实体与多部件生物**：`entity/boss/`（`Lich.java` 1096 行、`HydraHeadContainer.java` 982 行的多头实现）、`entity/ai/goal/` 44 个专用 Goal、`entity/util/multiparts` + `entity/TFPart.java` 自研多部件（不走原版 `EnderDragonPart`），配 `network/UpdateTFMultipartPacket` + `mixin` 之外的服务端访问器与客户端 `MultipartRenderDispatcher`
5. **网络层**：`events/RegistrationEvents.java:214` `setupPackets` 一处集中注册约 30 个 payload（`registrar(TwilightForestMod.ID).versioned("1.0.0").optional()`，playToClient/playToServer/playBidirectional 三分），每个包自带 `TYPE`+`STREAM_CODEC`+handle
6. **世界生成与维度**：`init/TFDimensionData.java`（`LevelStem`、自定义 `TFBiomeProvider`/`BiomeDensitySource`、`BiomeLayerStack` 数据包化群系层，见 `world/components/layer/vanillalegacy/`）、`world/components/chunkgenerators/`（自研 `NoiseDensityRouter`/`TerrainDensityRouter`/`CustomTerrainBeardifier` 等 density function，并在 `TFDensityFunctions` 注册类型）；`init/TFDataAttachments.java` 用约 20+ 个 `AttachmentType`（`sync(...)` 决定同步，`BANISHED_TO_TWILIGHT_FOREST` 带 `copyOnDeath()`）替代 Capability

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 4.5；`events/` 下按功能分文件（`RegistrationEvents`、`ProgressionEvents`、`ClientRegistrationEvents` 等），统一 `@Component` 由 Beanification 实例化后挂事件
- 数据驱动：14 个 datapack registry + 5 个 `DataMapType`（`init/TFDataMaps.java`：`TRANSFORMATION_POWDER`、`OMINOUS_FIRE`、`CRUMBLE_HORN`、`MAGIC_MAP_BIOME_COLOR`、`ORE_MAP_ORE_COLOR`，全部 `.synced(..., false)`），在 `RegistrationEvents.createDataMaps` 注册
- 配置：`config/ConfigSetup` + `ModLoadingContext.registerExtensionPoint(IConfigScreenFactory, ConfigurationScreen::new)`（NeoForge 自带配置界面）
- datagen：独立 `data` source set（`src/data/java/twilightforest/datagen/`），`datagen/DataGenerators.java` 用 Beanification `@Autowired` 注入 `AssetsGenerator`/`DataGenerator`，挂在 `GatherDataEvent.Client`；含 `data/TFStructureUpdater.java`（结构 NBT 自动升级，同 ImmersiveEngineering 思路）和 `generator/`、`helpers/models/BlockModelBuilders.java`(1030 行) 等

## 6. Mixin

**该仓库完全不用 Mixin**：全仓 `grep -rl "org.spongepowered" src/main/java` 命中 0 个文件，也没有 `*.mixins.json` 与 `mixin` 包。替代方案是 NeoForge 的类处理器（新式 coremod）：

- `src/asm/java/twilightforest/asm/TFCoreMod.java:33` `public class TFCoreMod implements ClassProcessorProvider`，`createProcessors(Context, Collector)` 里逐个 `collector.add(new XxxTransformer())` 注册约 30 个 ASM transformer
- 按功能分包：`transformers/armor`（盔甲/披风/鞘翅渲染可见性）、`entity`（`WaterWalkTransformer`、`PathFinderUnrestrainedByLeashTransformer`）、`chunk`（`ChunkStatusTaskTransformer`）、`conquered`（`StructureStartLoadStaticTransformer`）、`map`、`multipart`（`SendDirtyEntityDataTransformer`）、`render`、`player`、`cloud`、`snow` 等
- 主 jar 侧留有 `twilightforest/asmhooks/` 与 `EntityAccessor` 风格访问器供 transformer 注入的代码调用；`mods.toml` 无 `[[mixins]]` 段

## 7. 值得学的 5 条具体做法

1. **把"进度锁"做成数据包**：`Restriction`(CODEC) + 自建 registry `TFRegistries.ENFORCEMENT` + `Enforcement.enforceBiomeProgression`。文件：`util/Restriction.java`、`util/Enforcement.java:14`。适用：想让整合包作者改"哪些区域何时解锁"。
2. **用 ASM `ClassProcessorProvider` 做不能靠 Mixin 的改动**（如给原版 `WaterWalk`、`StructureStart.loadStatic`、渲染管线插桩）：`src/asm/java/twilightforest/asm/TFCoreMod.java`。适用：需要改 final 静态方法/条件极苛刻处。
3. **source set 隔离 + jarJar 内嵌 coremod**：`build.gradle:145,250`（asm 单独编译、`jarJar` 打包、shadowJar relocate `tamaized`→`twilightforest`）。适用：需要内嵌自带 ASM/依赖而不与整合包冲突。
4. **`TFStructureStart` 扩展原版 StructureStart 存附加状态**：`world/components/structures/start/TFStructureStart.java` 的 `createTag`/`loadFromTag` + `ASM` 在 `loadStatic` 注入。适用：结构需要持久化自定义状态（是否通关、是否已掠夺）。
5. **一个类集中注册整包网络**：`events/RegistrationEvents.java:214`。适用：NeoForge 1.20.5+ `PayloadRegistrar` 时代想让网络清单一眼可查。

## 8. 公开 API

非库 mod。对外扩展点是数据包：`twilightforest:restrictions`、`biome_layer_stack`、`biome_terrain_data`、`wood_palettes`、`magic_paintings`、`template_marker_handler(_list)`、`structure_speleothem_settings`、`travellers_modifiers` 以及 data maps（`twilightforest:transformation_powder`、`ominous_fire`、`crumble_horn`、`magic_map_color`、`ore_map_color`）。代码侧只有 `TwilightForestMod.prefix()` 等工具方法与 `TFDimension.isTwilightPortalDestination(Level)` 这类判定入口（`init/TFDimension.java:19`）。与 curios 的兼容在 `compat/curios/CuriosCompat.java` 用 `ModList.isLoaded` 条件加载，不使用 Mixin。
