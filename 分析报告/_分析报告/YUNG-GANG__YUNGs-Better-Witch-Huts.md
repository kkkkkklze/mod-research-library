# YUNG-GANG/YUNGs-Better-Witch-Huts 源码分析

## 1. 基本信息

- YUNG's Better Witch Huts；mod_id `betterwitchhuts`；YUNGNICKYOUNG, Acarii（`neoforge.mods.toml` / `fabric.mod.json`）；v5.1.1；LGPLv3
- MC `26.1.2`（NeoForge `26.1.2.75`，Fabric loader `0.18.6` + Fabric API `0.150.0`）；`java_version=25`；Gradle 9.2.0
- 多加载器 `Common`/`Fabric`/`NeoForge`；fabric-loom 1.15.5 + moddev 2.0.141；公共约定 `buildSrc/src/main/groovy/multiloader-{common,loader}.gradle`（`commonJava`/`commonResources`）
- 依赖即 API：**YungsApi 6.1.3**（必需；`@AutoRegister`、`LocateReplacer`、`BlockStateRandomizer`、`yungsapi:yung_jigsaw` 结构类型）、Cloth Config（Fabric 必需 `cloth-config2`）、ModMenu 可选（entrypoint `modmenu` → `config/gui/BWHModMenu`）
- **工作树是 sparse-checkout**（只签出 `**/*.java`、`*.gradle`、`*.toml`、`*.mixins.json`）：磁盘上 `Common/src/main/resources` 只剩 `betterwitchhuts.mixins.json`；`data/**`（6 个 NBT、3 个 template_pool、worldgen JSON）、`fabric.mod.json`、`META-INF/services/*` 必须 `git show HEAD:<path>` 读

## 2. 源码规模与包结构

25 个 `.java` / 692 行（git 跟踪共 76 个文件）。包（`Common/.../betterwitchhuts/`）：
- `world/processor`(5，全部逻辑)：`BrewingStandProcessor` 87、`WitchCircleProcessor` 75、`LegProcessor` 54、`FenceLegProcessor` 53、`PottedMushroomProcessor` 46
- `module`(2)：`StructureProcessorTypeModule`、`ConfigModule`；`services`(3)：`Services`/`IPlatformHelper`/`IModulesLoader`（**无** `IProcessorProvider`）；`mixin`(1)：`DisableVanillaWitchHutsMixin`；主类 `BetterWitchHutsCommon` 27 行
- 与另两个 YUNG 结构 mod 不同：**没有 `world/placement` 包，也没有 `StructurePlacementTypeModule`**（不使用自定义 placement）

## 3. 入口与注册

`Common/.../BetterWitchHutsCommon.java:16-23`：`init()` → `YungAutoRegister.scanPackageForAnnotations("...module")` + `Services.MODULES.loadModules()` + `LocateReplacer.register(BuiltinStructures.SWAMP_HUT, ResourceKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath(MOD_ID,"witch_hut")), () -> CONFIG.general.disableVanillaWitchHuts)`。

注册用 `@AutoRegister` 注解 + 包扫描（`module/StructureProcessorTypeModule.java` 5 条：`leg_processor`、`fence_leg_processor`、`witch_circle_processor`、`brewing_stand_processor`、`potted_mushroom_processor`）。loader 入口：NeoForge `@Mod`（存 `IEventBus`，调 common `init()` + `ConfigModuleNeoForge.init()`），Fabric `ModInitializer`。ServiceLoader（`services/Services.java:9-10`）只载 `IPlatformHelper`/`IModulesLoader`，绑定文件在各 loader 的 `META-INF/services/`；`FabricModulesLoader.loadModules()` 追加 `ConfigModuleFabric.init()`。

## 4. 核心系统

**A. "腿延伸"（`LegProcessor`/`FenceLegProcessor`）**：标记方块 → 柱体 → 向下填。`LegProcessor.java:32-37` 命中 `BROWN_STAINED_GLASS` 换成 `OAK_LOG`(`AXIS=Y`)；`FenceLegProcessor.java:31-36` 命中 `CRIMSON_FENCE` 换成 `OAK_FENCE.withPropertiesOf(原状态)`；随后 while 循环在 `getMinY()/getMaxY()` 之间，遇到空气或流体就 `levelReader.getChunk(mutable).setBlockState(...)` 继续向下补，把建筑"腿"接到地面（`:40-46`）——沼泽起伏地形适配的核心。

**B. `WitchCircleProcessor`**：三张静态 `BlockStateRandomizer`（`BRICKS_RANDOMIZER`=stone_bricks+mossy .6+cracked .1、`STONE_RANDOMIZER`=cobblestone+mossy .6+coarse_dirt .1、`STAIRS_RANDOMIZER`），按输入方块分派（stone_bricks / mossy_cobblestone / stone_brick_stairs / `GRAY_STAINED_GLASS`）；玻璃分支同样向下补柱把法阵"沉"到地面。**关键防御**：每分支先 `if (levelReader instanceof WorldGenRegion w && !w.getCenter().equals(ChunkPos.containing(pos))) return blockInfoGlobal;`（`:33`/`:53`）只处理当前生成区块，避免级联生成。

**C. `BrewingStandProcessor`（87 行）**：命中 `Blocks.BREWING_STAND` 后读 `nbt()` 的 `Items` ListTag，`populateItemsList` 用 `nextInt(5)` 从 5 组配方里选（glistering_melon_slice→healing、sugar→swiftness、pufferfish→water_breathing、golden_carrot→night_vision、phantom_membrane→slow_falling）；`addBrewingRecipe` 写输入料（`Slot 3`，count `nextInt(4)+2`）、必给输出药水（`Slot 1`）、50% 再补一瓶（Slot 0 或 2）；药水用 1.21+ 组件式 NBT `components → minecraft:potion_contents → potion`（`:56-86`）。`PottedMushroomProcessor` 以 `POTTED_RED_MUSHROOM` 为标记，随机换成 7 种花盆（brown .2，cornflower/cactus/dead_bush/fern/azalea 各 .1）。

**D. 两结构 + 原版 placement**：`worldgen/structure/witch_hut.json`、`witch_circle.json` 均为 `"type": "yungsapi:yung_jigsaw"`，`project_start_to_heightmap: WORLD_SURFACE_WG`、`start_height` 绝对 1 / 0、`size: 20`、`max_distance_from_center: 80`、`liquid_settings: ignore_waterlogging`；`spawn_overrides` 里直接写死 witch（monster）与 cat（creature）各 1——这是"小屋必有女巫和猫"的实现。`structure_set/*.json` 用**原版 `minecraft:random_spread`**（witch_hut spacing 30/separation 8；witch_circle spacing 40/separation 10）。`template_pool/starts.json` 在 `witch_hut_sm/lg/double` 三个权重 1 单体元素间随机，全部挂 `betterwitchhuts:main` processor list；法阵用 `template_pool/circles.json`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无。
- 数据驱动（`Common/src/main/resources/data/betterwitchhuts/`）：6 个 NBT（`cat`、`witch`、`witch_circle`、`witch_hut_sm/lg/double`）、3 个 template_pool（`starts`/`circles`/`mobs`）、`processor_list/main.json`（5 个自定义 processor 全列）、1 个 loot_table（`chests/hut_0`）、2 个 biome tag（`has_structure/better_witch_hut` 用 `replace:false` 列 `swamp`/`mangrove_swamp` 并可选 `#forge:is_swamp`、`#c:swamp`；`has_structure/witch_circle`）；覆盖原版 `data/minecraft/tags/worldgen/structure/cats_spawn_in.json`、`cats_spawn_as_black.json`（沼泽猫变黑），兼容 `morevillagers` 的 `on_swamp_hut_explorer_maps`。
- 配置：common `module/ConfigModule.java` 仅 `General.disableVanillaWitchHuts=true`；NeoForge `config/BWHConfigNeoForge.java`+`ConfigGeneralNeoForge.java`（`ModConfigSpec`，`worldRestart()`），文件 `betterwitchhuts-neoforge-26_1.toml`；Fabric `BWHConfigFabric`（`@Config(name="betterwitchhuts-fabric-26_1")`，`@ConfigEntry.Category` + `Gui.TransitiveObject`）走 Cloth `AutoConfig` + Toml4j；两侧都 `bakeConfig()` 写入 common POJO（触发点：`LevelEvent.Load`/`ModConfigEvent`/Cloth save+load 监听）。
- datagen：无。

## 6. Mixin

`Common/src/main/resources/betterwitchhuts.mixins.json`（required、JAVA_17、defaultRequire 1，数组末项后多一个逗号——严格 JSON 不合法，靠 Mixin 的 Gson 宽松解析容忍）仅列 `DisableVanillaWitchHutsMixin`：`@Mixin(ChunkGenerator.class)`，`@Inject(method = "tryGenerateStructure", at = @At("HEAD"), cancellable = true)`，判断 `CONFIG.general.disableVanillaWitchHuts && type() == StructureType.SWAMP_HUT` 时 `cir.setReturnValue(false)`。

## 7. 值得学的 5 条做法

1. **"腿延伸"通用写法**：标记方块 → 柱体 → 向下 while 填空气/流体到 `getMinY()/getMaxY()`（`world/processor/LegProcessor.java:40-46`）——起伏/沼泽地形上生成建筑的现成方案。
2. **`WorldGenRegion.getCenter()` 守卫**：写世界前确认目标坐标属于当前生成区块，否则原样返回（`WitchCircleProcessor.java:33`/`:53`）——防级联生成与卡顿。
3. **实体生成写进结构 JSON**：用 `spawn_overrides` 声明 witch/cat，代替 Java 刷怪（`worldgen/structure/witch_hut.json`），玩家可被 datapack 覆盖。
4. **标记方块语义分层**：同一 mod 给每个 processor 分配专用标记（brown_stained_glass=原木腿、crimson_fence=栅栏腿、gray_stained_glass=法阵砖、potted_red_mushroom=花盆），链式挂接时互不干扰（`processor_list/main.json` 并列 5 条）。
5. **组件式物品 NBT**：药水效果写 `components → minecraft:potion_contents → potion`（`BrewingStandProcessor.java:78-86`），可直接照抄到任何 1.21+ 结构战利品/容器生成代码。
