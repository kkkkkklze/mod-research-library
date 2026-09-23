# Glitchfiend/BiomesOPlenty 源码分析报告

## 1. 基本信息

| 项 | 值 |
| --- | --- |
| Mod 名 / mod_id | Biomes O' Plenty / `biomesoplenty` |
| 作者 | Adubbz, Forstride（Glitchfiend Team） |
| 目标 MC / 加载器 | `minecraft_version=26.2`（快照式大版本号；代码用 `net.minecraft.resources.Identifier`、`EntityTypes`、`WeightedList` 等新 Mappings 名称，属面向未来版本的分支，非 1.20.1/1.21.1） |
| 加载器版本 | Forge `65.0.1`；NeoForge `26.2.0.7-beta`；Fabric loader `0.19.3` + fabric-api `0.153.0+26.2` |
| Gradle 插件 | 根 `net.minecraftforge.gitversion` + `net.minecraftforge.changelog`；common/neoforge `net.neoforged.moddev 2.0.141`；forge `net.minecraftforge.gradle [7.0.17,8)`；fabric `net.fabricmc.fabric-loom 1.15-SNAPSHOT`；均含 `de.maxhenkel.cursegradle`、`com.modrinth.minotaur`（`build.gradle:1-40,143`） |
| Java | toolchain 25（`build.gradle:47-50`） |
| 许可证 | All Rights Reserved（`gradle.properties:mod_license`；`README.md` © 2026 Glitchfiend） |
| 编译依赖（谁是它的 API） | `GlitchCore`（`glitchcore_version=26.2.0.0.0`）提供 `config.Config`、`util.RegistryHelper`、`util.Environment`、`event.EventManager`、`util.Remapper`、`util.BlockHelper`；`TerraBlender`（`26.2.0.0.1`）提供 `Region`/`Regions`/`EndBiomeRegistry`/`SurfaceRuleManager`。common 中两者均 `compileOnly`（`common/build.gradle:17-23`），mods.toml 声明为 required + AFTER |

## 2. 源码规模与包结构

实测：共 **275 个 .java，34701 行**（common 248 / worldgen 占 118 个文件 17020 行；neoforge 18；fabric 5；forge 4）。资源文件极少：`common/src/main/resources` 仅 4 个文件（mixins.json、accesswidener、accesstransformer.cfg、shaders/block.properties），`common/src/generated/resources` 在本次快照中**不存在**（datagen 产物未提交）。

按包（common，第 3 层）：`worldgen`(118/17020)、`block`(70/5154)、`init`(19/3402)、`api`(12/1501)、`biome`(6/3220)、`particle`(11/976)、`util`(7/316)、`config`(2/58)、`client`(1/81)、`worldgen/feature/misc`(69 个一事一文件的 Feature)、`worldgen/feature/tree`(15)、`worldgen/feature/configurations`(12)、`worldgen/placement`(6)。

最大文件：`biome/BOPOverworldBiomes.java`(2041)、`worldgen/feature/misc/HugeFlowerFeature.java`(1002)、`biome/BOPOverworldBiomeBuilder.java`(666)、`init/ModBlocks.java`(638)、`neoforge/datagen/BOPBlockLoot.java`(637)、`init/ModItems.java`(635)、`api/item/BOPItems.java`(551)、`worldgen/placement/BOPVegetationPlacements.java`(550)。

## 3. 入口与注册

common 主类 `common/src/main/java/biomesoplenty/core/BiomesOPlenty.java:23`：

```java
public static void init() {
    ModConfig.setup();                 // 先建配置目录，其他逻辑依赖它
    ModBiomes.setup(); ModTags.setup();
    addRegistrars(); addHandlers();
    ModLegacy.setupBiomes();           // 旧 ID 迁移
}
private static void addRegistrars() {
    var regHelper = RegistryHelper.create();
    regHelper.addRegistrar(Registries.BLOCK, ModBlocks::setup);
    regHelper.addRegistrar(Registries.ITEM, ModItems::setup);
    regHelper.addRegistrar(Registries.FEATURE, BOPBaseFeatures::registerFeatures);
    regHelper.addRegistrar(Registries.CARVER, BOPWorldCarvers::registerCarvers);
    ... // BLOCK_ENTITY_TYPE/FLUID/ENTITY_TYPE/CREATIVE_MODE_TAB/PARTICLE_TYPE/SOUND_EVENT
}
```

**不用 DeferredRegister 作为主框架**：注册回调统一签名 `BiConsumer<Identifier, T>`，由 GlitchCore `RegistryHelper` 在各 loader 落地；仅 NeoForge 为自身专属注册表 New 建了 `DeferredRegister<FluidType> FORGE_FLUID_REGISTER`（`neoforge/.../core/BiomesOPlentyNeoForge.java:27`）。平台入口：NeoForge `@Mod` 构造器注入 `IEventBus`，`commonSetup` 里 `event.enqueueWork(BiomesOPlenty::setupTerraBlender)`；Fabric 类实现 `GlitchCoreInitializer, TerraBlenderApi`（`onInitialize`/`onInitializeClient`/`onTerraBlenderInitialized`，`fabric/.../core/BiomesOPlentyFabric.java:13-32`）；Forge 同理。

## 4. 核心系统

**(a) 与 TerraBlender 的分工**：BOP 只提供生物群系定义与地表/地物，**地区(Region)权重与注入点全交 TerraBlender**。`init/ModBiomes.java:32-45` 注册 5 个 Region（`BOPOverworldRegionPrimary/Secondary/Rare`、`BOPNetherRegionCommon/Rare`），权重全部读配置；`BOPOverworldRegionPrimary` 仅 3 行有效逻辑：`super(LOCATION, RegionType.OVERWORLD, weight)` + `addBiomes` 委托 `BOPOverworldBiomeBuilder`。End 生物群系走 `EndBiomeRegistry.registerHighlandsBiome(key, weight)`。**地表规则写在 `init/ModItems.java:109-111`**：`SurfaceRuleManager.addSurfaceRules(RuleCategory.OVERWORLD/NETHER/END, MOD_ID, BOPSurfaceRuleData::overworld)`（`BOPSurfaceRuleData` 372 行全是 `SurfaceRules.sequence/ifTrue` 组合）。

**(b) 气候参数驱动的群系表**：`biome/BOPOverworldBiomeBuilder.java` 定义 5×5×7 的 temperature/humidity/erosion `Climate.Parameter` 数组 + 数十个二维表（`MIDDLE_BIOMES_BOP`、`PLATEAU_BIOMES_BOP`、`BEACH/RIVER/ISLAND/SLOPE/PEAK_BIOMES_BOP`…），每个 `pickXxxBiomeBOP` 都调 `BiomeUtil.biomeOrFallback(registry, bop, vanilla)`，实现"BOP 优先、被禁用/不存在则回退原版"。三个 builder（Primary/Secondary/Rare）复刻同一套骨架，仅替换表内容，Rare 用 `RARE_RARENESS_RANGE` 缩小生成区。

**(c) 地物体系（代码 bootstrap，非 JSON）**：`worldgen/feature/BOPBaseFeatures.java` 用普通静态字段声明全部 Feature 实例（`public static Feature<NoneFeatureConfiguration> HIGH_GRASS;` 等），按环境分 6 个文件（Cave/MiscOverworld/Nether/End/Tree/Vegetation）；`util/worldgen/BOPFeatureUtils.bootstrap` 依次调用 6 个类的 `bootstrap(context)`，`BOPPlacementUtils` 同理。树用泛型基类：`BOPTreeFeature<T extends FeatureConfiguration>` + `BasicTreeFeature/PineTreeFeature/RedwoodTreeFeature/BayouTreeFeature/EmpyrealTreeFeature` 等 15 个实现 + 12 个 configuration 类。

**(d) 生物群系开关配置（JSON）**：`init/ModConfig.java` 手写 `config/biomesoplenty/biome_toggles.json`，键名 `getBiomeConfigOptionName(key) = key.identifier().getPath() + "_enabled"`；读到不存在的键就**自动补写**（`addBiomeToggle` → `updateConfigFile`）；static 块用 `BOPBiomes.getAllBiomes()` 生成默认值并放进 `TreeMap` 保证输出顺序稳定。TOML 侧走 GlitchCore `Config` 子类（`config/GenerationConfig.java`：5 个 Region 权重，范围 0~MAX，注释即文档）。

**(e) 旧存档兼容**：`init/ModLegacy.java` 用 `glitchcore.util.Remapper` 把历史 ID 映射到新方块或原版方块（`remap("white_cherry_sapling", BOPBlocks.SNOWBLOSSOM_SAPLING)`、`remap("cherry_planks", Blocks.CHERRY_PLANKS)`）；`init/ModVanillaCompat.java` 负责发射器行为、可燃性 `registerFlammable(block,30,60)`、堆肥表。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无。全仓 grep `CustomPacketPayload|PayloadRegistrar|SimpleChannel` 零命中。
- **数据驱动**：ConfiguredFeature / PlacedFeature / Biome / Carver / DamageType / JukeboxSong / VillagerTrade / TrimMaterial 全部代码 bootstrap（`neoforge/.../datagen/DataGenerationHandler.java:29-37` 的 `RegistrySetBuilder` 逐表 `.add(...)`），再经 `DatapackBuiltinEntriesProvider` 输出 JSON 到 `common/src/generated/resources`。datagen provider：`BOPLootTableProvider`、`BOPRecipeProvider`、`BOPBlockLoot`(637 行)、`BOPModelProvider`(模型生成器/纹理映射/模板三件套)、`BOPDamageTypeTagsProvider`、`BOPDataMapProvider`。
- **配置**：两类——GlitchCore TOML（generation/gameplay）+ 自写 Gson JSON（biome_toggles.json，`util/config/JsonUtil.getOrCreateConfigFile`：文件不存在则写默认值再读回）。

## 6. Mixin

4 个 mixin 配置：`common/src/main/resources/biomesoplenty.mixins.json`（**空列表**，仅占位）、`neoforge|forge|fabric` 各一份 `biomesoplenty.*.mixins.json`。共 7 个 mixin 类，其中 `MixinBloodFluid`、`MixinLiquidNullFluid` 三个加载器各写一份（目标为流体类，未读实现细节），Fabric 多一个 `MixinScreenEffectRenderer`。另用 `common/src/main/resources/META-INF/accesstransformer.cfg` + `biomesoplenty.accesswidener` 打开原版私有成员（`WoodType.register`、`BlockSetType.register`、`StairBlock` 构造器、`Blocks.log`、`FireBlock.setFlammable`）。

## 7. 值得学的 5 条具体做法

1. **注册回调用平台无关签名**：全部注册方法写成 `Consumer`/`BiConsumer<Identifier, T>`，common 不 import 任何 loader 类，loader 差异集中在 `RegistryHelper` 实现里（`core/BiomesOPlenty.java:36-49`）；适用于多加载器共用源码。
2. **"静态字段即 API"的持有类**：`api/block/BOPBlocks`、`api/item/BOPItems`、`api/entity/BOPEntities` 只有 `public static Block X;` 声明，赋值在 `init/ModBlocks` 内 `import static biomesoplenty.api.block.BOPBlocks.*;` 后完成 → 外部 mod 可 `compileOnly` 依赖 api 包，内部实现类不对外暴露（`api/` 12 个文件 1501 行）。
3. **禁用即回退的 fallback 链**：`BiomeUtil.biomeOrFallback(registry, bopBiome, vanillaBiome)` 让配置关闭生物群系时自动落到原版同类群系，而不是留空洞（`util/biome/BiomeUtil.java:13-27`）；任何"可关闭内容 + 气候参数表"的场景都适用。
4. **配置缺项自动补写**：`ModConfig.getBiomeToggles()` 发现键缺失就 `put` 并立刻回写 JSON，配合 static 块预置默认值 → 升级 mod 加新群系时老配置不用手改（`init/ModConfig.java:43-79`）。
5. **文档化的"配置即开关"**：Region 权重直接由 `GenerationConfig` 提供（`addNumber("overworld.bop_primary_overworld_region_weight", 10, 0, Integer.MAX_VALUE, "...")`），权重=0 即关闭整套 BOP 群系注入，无需额外代码分支（`config/GenerationConfig.java:28-33` + `init/ModBiomes.java:34-38`）。

## 8. 公开 API 与外部接入

- 入口常量：`biomesoplenty.api.BOPAPI.MOD_ID`。
- 内容清单：`biomesoplenty.api.biome.BOPBiomes`（`getAllBiomes()`/`getOverworldBiomes()` 返回 `ImmutableList.copyOf`，且在 `register*` 中登记，供配置与遍历用）、`api.block.BOPBlocks/BOPBlockEntities/BOPFluids/BOPWoodTypes/BOPBlockSetTypes`、`api.item.BOPItems`、`api.entity.BOPEntities/BOPVillagerTrades`、`api.sound.BOPSounds`、`api.damagesource.BOPDamageTypes`。
- 外部接入方式：非"BOP 提供扩展点接口"，而是**依赖 TerraBlender 的公共机制**——第三方 mod 通过 TerraBlender 注册自己的 `Region`/地表规则即可与 BOP 共存（`Regions.register`、`SurfaceRuleManager.addSurfaceRules`、`EndBiomeRegistry.registerHighlandsBiome`），BOP 自身就是这套 API 的第一个用户。
- 未确认项：本快照中 `fabric/src/main/resources/fabric.mod.json` 缺失（根 `build.gradle:143` 会对该文件做变量 expand），无法核对 Fabric 侧 entrypoint 声明文本。

## 附：分析备注

- `forge/src/main/java/biomesoplenty/forge/` 仅 4 个文件（主类、FluidTypes、2 个 mixin），Forge 侧复用 common + GlitchCore/Forge 适配，是最薄的一层；Fabric 5 个、NeoForge 18 个（NeoForge 独有完整 datagen 管线，Forge/Fabric 侧未发现 datagen 包）。
