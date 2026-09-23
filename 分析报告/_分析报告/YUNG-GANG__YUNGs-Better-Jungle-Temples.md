# YUNG-GANG/YUNGs-Better-Jungle-Temples 源码分析

## 1. 基本信息

- YUNG's Better Jungle Temples；mod_id `betterjungletemples`；YUNGNICKYOUNG, Tera；v4.1.1；LGPLv3（`gradle.properties`）
- MC `26.1.2`（NeoForge `26.1.2.75`，Fabric loader `0.18.6` + Fabric API `0.150.0`）；`java_version=25`；Gradle 9.2.0
- 多加载器 `Common`/`Fabric`/`NeoForge`；插件 fabric-loom 1.15.5 + moddev 2.0.141；公共约定 `buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle`（`commonJava`/`commonResources` configuration + `io.github.mcgradleconventions.loader` 属性）
- 依赖即 API：**YungsApi 6.1.3**（必需；`@AutoRegister`/`YungAutoRegister`/`LocateReplacer`/`BlockStateRandomizer`/`EnhancedExclusionZone`/`StructureEntityProcessor` 全来自它）、Cloth Config（Fabric 必需）、ModMenu（可选）、MixinExtras 0.5.3、reflections（Fabric include）

## 2. 源码规模与包结构

- 40 个 `.java` / 1234 行；git 共跟踪 229 个文件（结构 NBT 127、template_pool 17、loot_table 3、lang en_us/ru_ru/uk_ua）
- **工作树是 sparse-checkout**（`.git/info/sparse-checkout` 只签出 `**/*.java`、`*.gradle`、`*.toml`、`*.mixins.json`）：`data/**`、`fabric.mod.json`、`META-INF/services/*` 磁盘上不存在，须 `git show HEAD:<path>` 读，不要据此判定"无数据资源"
- 公共逻辑全在 `Common/.../betterjungletemples/`：`world/processor`(8)、`world/placement`、`world/util`、`module`(6)、`mixin`(2)、`services`(4)；Fabric/NeoForge 各约 10 个文件（入口/Config/平台实现）
- 最大文件：`BlockReplaceProcessor` 148、`BetterJungleTemplePlacement` 93、`PillarProcessor` 86、`EmptyDispenserProcessor` 65、`CaveVineDecorationProcessor` 62

## 3. 入口与注册

`Common/.../BetterJungleTemplesCommon.java:16-23`：

```java
public static void init() {
    YungAutoRegister.scanPackageForAnnotations("...betterjungletemples.module");
    Services.MODULES.loadModules();
    LocateReplacer.register(BuiltinStructures.JUNGLE_TEMPLE,
        ResourceKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath(MOD_ID, "jungle_temple")),
        () -> CONFIG.general.disableVanillaJungleTemples);
}
```

注册框架不是 DeferredRegister：类上 `@AutoRegister(MOD_ID)` + 字段 `@AutoRegister("pillar_processor")`，由 YungsApi 包扫描完成（`module/StructureProcessorTypeModule.java:16-38` 8 个 processor 类型、`StructurePlacementTypeModule` 1 个）。平台差异用 ServiceLoader：`services/Services.java:9-11` 载 `IPlatformHelper`/`IModulesLoader`/`IProcessorProvider`，绑定文件在各 loader 的 `src/main/resources/META-INF/services/...`。loader 入口：NeoForge `@Mod`（存 `IEventBus` 后调 common `init()` + `ConfigModuleNeoForge.init()`），Fabric `ModInitializer`。

## 4. 核心系统

**A. 处理器链 + 标记方块约定**：8 种 `StructureProcessor`，NBT 里放不可能自然出现的方块做占位，运行时替换——`FireballDispenserProcessor.java:35`（`ORANGE_CONCRETE`→朝上 dispenser，第 4 格必给 fire_charge、其余 9 格各 10%）、`BlastFurnaceProcessor.java:27`（`BlockStateRandomizer` 权重 dispenser/dropper/observer）、`TorchProcessor`、`CaveVineDecorationProcessor`。随机一律 `structurePlacementData.getRandom(blockInfoGlobal.pos())`（按坐标定随机，保证一致）。

**B. `BlockReplaceProcessor`（148 行）**：`target_block` + `output: BlockStateRandomizer`，开关 `copy_input_properties` / `randomize_facing` / `randomize_half` / `preserve_waterlog`；开启复制时把源楼梯/台阶/墙的 `FACING/HALF/SHAPE/TYPE/NORTH..UP` 属性搬到输出（`:79-101`）。

**C. `BetterJungleTemplePlacement`**：继承 `RandomSpreadStructurePlacement`，CODEC 追加 `enhanced_exclusion_zone`，自校验 `spacing > separation`；`isPlacementChunk` 借 accessor 拿 `BiomeSource`，用 `findBiomeHorizontal(..., 48, 2, ...)` 判"48 格内有河流/海洋就不放"（`:66-84`）；`isStructureChunk` 再叠 exclusion zone。

**D. 禁用原版 + `/locate` 重定向**：mixin 在 `ChunkGenerator#tryGenerateStructure` HEAD 取消 `StructureType.JUNGLE_TEMPLE`；`LocateReplacer` 把 `minecraft:jungle_temple` 指向本 mod 结构（受同一配置开关控制）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无。
- 数据驱动（`Common/src/main/resources/data/betterjungletemples/worldgen/`）：`structure/jungle_temple.json` 用 `"type": "yungsapi:yung_jigsaw"`，字段 `start_pool: betterjungletemples:starts`、`start_jigsaw_name: ...:anchor`、`size: 10`、`project_start_to_heightmap: WORLD_SURFACE_WG`、`start_height` 绝对 -30~-25、`enhanced_terrain_adaptation: yungsapi:none`、`liquid_settings: ignore_waterlogging`、清空 spawn_overrides；`structure_set/jungle_temples.json` 用自定义 placement（spacing 24 / separation 8 / salt、`enhanced_exclusion_zone: {other_set: #betterjungletemples:jungle_temple_avoid, chunk_count: 4}`）；`processor_list/main.json`（+`main_waterlog.json`）23 条配置把标记映射写死（`blue_concrete`→water/cobblestone、`pink_concrete`→infested_cobblestone、`orange_stained_glass`→pillar、`granite`→cobblestone 系、`smooth_red_sandstone*`→stone_brick 系带 `copy_input_properties`、`red_sandstone`→`randomize_facing`、`dead_tube_coral_block`→water），末尾混用原版 `minecraft:rule`；另有 17 个 template_pool、127 个 NBT（含 `challenge_room_serpent*`、`challenge_statue_*`）、3 个 loot_table、`morevillagers`/`yungsapi` 兼容 tag。
- 配置：common 为普通 POJO `module/ConfigModule.java`（仅 `disableVanillaJungleTemples=true`）；NeoForge 注册 `ModConfig.Type.COMMON`，文件 `betterjungletemples-neoforge-26_1.toml`，在 `LevelEvent.Load`/`ModConfigEvent` 调 `bakeConfig()`；Fabric 用 Cloth `AutoConfig`+Toml4j，save/load 监听器烘焙。
- datagen：无。

## 6. Mixin

`Common/src/main/resources/betterjungletemples.mixins.json`（required、JAVA_17、defaultRequire 1）：
- `mixin/DisableVanillaJungleTempleMixin.java` → `ChunkGenerator#tryGenerateStructure`，`@Inject(at = HEAD, cancellable = true)`，`CallbackInfoReturnable<Boolean>` 返回 false
- `mixin/accessor/ChunkGeneratorStructureStateAccessor.java` → `@Accessor` 暴露 `ChunkGeneratorStructureState#getBiomeSource()`

## 7. 值得学的 5 条做法

1. **注解注册**：`@AutoRegister(MOD_ID)` + 字段级 `@AutoRegister("name")` + 包扫描，注册代码一行一个（`module/StructureProcessorTypeModule.java`）——多 loader 共享代码时比 DeferredRegister 更省心。
2. **标记方块占位**：datapack 用 `orange_concrete` 等做占位，processor 按上下文换成带 NBT/朝向的真实方块（`FireballDispenserProcessor.java:35`）——结构随机化不必为每种变体导 NBT。
3. **随机绑定坐标**：`structurePlacementData.getRandom(pos)` 而非全局 random（`BlockReplaceProcessor.java:74`），保证多人/重载一致。
4. **ServiceLoader 平台隔离**：签名不一致的类（如两侧 `ItemFrameProcessor` 继承不同基类）下沉到 loader 子项目，common 只依赖接口（`services/Services.java`）。
5. **配置烘焙**：common 只存 POJO，各 loader 在加载/变更/进世界时写入（`ConfigModuleNeoForge.java:bakeConfig`），共享代码零配置库依赖且可热重载。
