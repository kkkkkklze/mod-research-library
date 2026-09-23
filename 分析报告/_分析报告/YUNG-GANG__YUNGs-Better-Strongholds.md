# YUNG-GANG/YUNGs-Better-Strongholds 源码分析

## 1. 基本信息

- YUNG's Better Strongholds；mod_id `betterstrongholds`；YUNGNICKYOUNG, Acarii；v6.1.1；LGPLv3（`gradle.properties`）
- MC `26.1.2`（NeoForge `26.1.2.75`，Fabric loader `0.18.6` + Fabric API `0.150.0`）；`java_version=25`；Gradle 9.2.0
- 多加载器 `Common`/`Fabric`/`NeoForge`；fabric-loom 1.15.5 + moddev 2.0.141；公共约定 `buildSrc/src/main/groovy/multiloader-{common,loader}.gradle`
- 依赖即 API：**YungsApi 6.1.3**（必需；`@AutoRegister`、`LocateReplacer`、`ItemRandomizer`/`BlockStateRandomizer`、`ISafeWorldModifier`、`yungsapi:yung_jigsaw` 结构类型、`yungsapi.io.JSON`）、Cloth Config（Fabric 必需）、ModMenu 可选、MixinExtras 0.5.3、reflections（Fabric include）
- **工作树是 sparse-checkout**（只签出 `**/*.java`、`*.gradle`、`*.toml`、`*.mixins.json`）：磁盘上 `src/main/resources` 只剩 `betterstrongholds.mixins.json` 与 `neoforge.mods.toml`，`data/**`(97 个 NBT、12 个 template_pool、10 个 loot_table)、`fabric.mod.json`、`META-INF/services/*` 必须 `git show HEAD:<path>` 读

## 2. 源码规模与包结构

41 个 `.java` / 2243 行（git 跟踪共 208 个文件）。包（`Common/.../betterstrongholds/`）：`world/processor`(9)、`world`(4 个概率单例)、`world/placement`(1)、`module`(3)、`mixin`(1)、`services`(4)；Fabric/NeoForge 各约 10 个（入口、Config、`ArmorStandProcessor`/`ItemFrameProcessor`）。

最大文件：`NeoForge/.../module/ConfigModuleNeoForge.java` 302、`Fabric/.../module/ConfigModuleFabric.java` 285、`world/processor/LegProcessor.java` 146、`world/ArmorStandChances.java` 110、`processor/ArmorStandProcessor.java` 106/105、`processor/BannerProcessor.java` 100、`world/placement/BetterStrongholdsPlacement.java` 98。

## 3. 入口与注册

`Common/.../BetterStrongholdsCommon.java:17-24`：`init()` → `YungAutoRegister.scanPackageForAnnotations("...module")` + `Services.MODULES.loadModules()` + `LocateReplacer.register(BuiltinStructures.STRONGHOLD, ResourceKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath(MOD_ID,"stronghold")), () -> true)`（`/locate` 无条件改指新要塞）。

注册用 YungsApi `@AutoRegister` + 包扫描（非 DeferredRegister）：`module/StructureProcessorTypeModule.java:16-37` 注册 9 个 processor 类型（`ruin/banner/ore/rare_block/redstone/leg/end_portal_frame` 7 个纯 common，`armorstand`/`itemframe` 走 `Services.PROCESSORS.*Codec()` 转发到各 loader）；`StructurePlacementTypeModule` 注册 `stronghold` placement。ServiceLoader 载 `IPlatformHelper`/`IModulesLoader`/`IProcessorProvider`，绑定文件在各 loader 的 `META-INF/services/`；`FabricModulesLoader.loadModules()` 追加 `ConfigModuleFabric.init()`。

## 4. 核心系统

**A. 环形分布 `BetterStrongholdsPlacement`（98 行，最有学习价值）**：CODEC 在 `RandomSpreadStructurePlacement` 之上加 `chunk_distance_to_first_ring` / `ring_chunk_thickness` / `max_ring_section`(Optional)；`isPlacementChunk` 算 `(int)Math.sqrt(chunkX²+chunkZ²)`，再 `shifted = chunkDistance + (ringChunkThickness - chunkDistanceToFirstRing)` 把首环拉近原点，`ringSection = shifted / ringChunkThickness`，**只允许奇数环生成**，`maxRingSection` 可限制总环数（`:56-88`）——原版"三环要塞"的可数据化重写。

**B. JSON 概率单例族**：`ArmorStandChances`/`OreChances`/`RareBlockChances`/`ItemFrameChances`，全部 `private` 构造 + `public static X instance` + `get()`；字段是 YungsApi 的 `ItemRandomizer`/`BlockStateRandomizer` 并带默认权重（如 commonHelmets：chainmail .3 / leather .1 / iron .3 / carved_pumpkin .01）。注释明确写"单例是为了与 JSON 保持单一数据源，JSON 不存在则由默认值生成"（`world/ArmorStandChances.java:9-12`）。

**C. 处理器链 + 标记方块**：`LegProcessor.java:48` 用 `YELLOW/ORANGE_STAINED_GLASS` 做腿部标记，换成石砖并向下补柱（实现 `ISafeWorldModifier` 安全写世界）；`RuinProcessor.java:44-51` 受 `CONFIG.general.enableStructureRuin` 控制，非 `safe_blocks` 且世界位置为空气时置 AIR（"被洞穴侵蚀"）；`EndPortalFrameProcessor.java:30-32` 用 `nextFloat() < filledPortalFrameChance` 决定末地门是否带眼；`BannerProcessor.java:33-60` 用 `Banner.Builder` 造末影人/凋灵/传送门三款墙旗；`OreProcessor`（`NETHER_GOLD_ORE` 为标记）/`RareBlockProcessor`（`PURPUR_BLOCK` 为标记）转概率单例。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无。
- 数据驱动（`Common/src/main/resources/data/betterstrongholds/`）：`structure/stronghold.json` 为 `"type": "yungsapi:yung_jigsaw"`，`start_pool: ...:starts`、`start_jigsaw_name: ...:stronghold_anchor`、`size: 15`、`step: strongholds`、`start_height` 绝对 -30~11、`max_y: 60`、`enhanced_terrain_adaptation` 为 `yungsapi:custom`（kernel_size/distance 24，top/bottom 均 bury）；`structure_set/stronghold.json` 用自定义 placement（spacing 85 / separation 50 / `chunk_distance_to_first_ring` 80 / `ring_chunk_thickness` 96 / salt）；`processor_list/main.json` 按顺序列 8 个自定义 processor 后接原版 `minecraft:rule`（`red_stained_glass`→tnt、`stone_bricks` 30% mossy/20% cracked/5% infested、cobweb/tripwire/torch/lantern 随机消除），另有 `rooms/*.json`、`statues.json`、`terminators.json`；97 个 NBT、12 个 template_pool、10 个 loot_table；并覆盖 `data/minecraft/tags/worldgen/structure/eye_of_ender_located.json` 与 `data/minecraft/advancement/story/follow_ender_eye.json`（让末影之眼指向新要塞）。
- 配置（双轨，本 mod 重点）：① common `module/ConfigModule.java` 仅 2 个字段（`enableStructureRuin=false`、`filledPortalFrameChance=0.1f`）；NeoForge `ModConfigSpec`（`config/BSConfigNeoForge.java`，全 `worldRestart()`，文件 `betterstrongholds-neoforge-1_21.toml`——`VERSION_PATH` 字符串仍写死 `neoforge-1_21`），Fabric Cloth `AutoConfig`+Toml4j。② **自定义 JSON**：`ConfigModuleNeoForge.initCustomFiles()` 建 `config/betterstrongholds/neoforge-1_21/`、写 `README.txt`（内含各文件格式说明），再 `loadOresJSON/loadRareBlocksJSON/loadArmorStandsJSON/loadItemFramesJSON`：文件缺失则 `JSON.createJsonFileFromObject(path, X.get())` 由默认对象生成，存在则 `JSON.loadObjectFromJsonFile(path, X.class)` 覆盖单例（`:175-280`）；两边都在 `LevelEvent.Load`/`ModConfigEvent` 调 `bakeConfig()` 写入 POJO。
- datagen：无。

## 6. Mixin

`Common/src/main/resources/betterstrongholds.mixins.json`（required、JAVA_17、defaultRequire 1）仅 1 个：`mixin/DisableVanillaStrongholdsMixin.java` → `@Mixin(ChunkGenerator.class)`，`@Inject(method = "tryGenerateStructure", at = @At("HEAD"), cancellable = true)`，参数完整枚举（`StructureSet.StructureSelectionEntry`/`StructureManager`/`RegistryAccess`/`RandomState`/seed/`ChunkAccess`/`ChunkPos`/`SectionPos`/`ResourceKey<Level>`），命中 `StructureType.STRONGHOLD` 即 `cir.setReturnValue(false)`。**无配置开关**（与 Jungle Temples 不同，无条件禁用原版）。

## 7. 值得学的 5 条做法

1. **环形 placement 数据化**：把"要塞分环、只落奇数环"做成 CODEC 字段（`chunk_distance_to_first_ring`/`ring_chunk_thickness`/`max_ring_section`），datapack 可调（`world/placement/BetterStrongholdsPlacement.java:56-88`）。
2. **单例 + JSON 双向同步的调参文件**：概率表=普通 POJO 单例，缺失时由默认对象生成 JSON、存在时反序列化覆盖（`ArmorStandChances.java` + `ConfigModuleNeoForge.loadArmorStandsJSON()`）——比塞进 ModConfigSpec 更适合权重嵌套结构。
3. **标记方块 + `ISafeWorldModifier`**：`LegProcessor`、`OreProcessor`、`RareBlockProcessor` 只在命中自身标记时动手，写世界走 YungsApi 安全接口防越界崩溃。
4. **首次运行自动铺 README + 默认 JSON**：`createBaseReadMe()`/`createJsonReadMe()` 用文本块把格式说明写进 config 目录（`ConfigModuleNeoForge.java:81-170`）。
5. **覆盖原版 tag 与进度**：`eye_of_ender_located.json` + `follow_ender_eye.json` 让"末影之眼/进度"体系无缝指向新结构（`data/minecraft/...`）——替换原版结构时的必备收尾。
