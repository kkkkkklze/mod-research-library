# TerraBlender 源码分析报告

## 1. 基本信息

- Mod 名 / ID：TerraBlender / `terrablender`；作者 Adubbz（Glitchfiend）；许可证 LGPLv3（`gradle.properties:mod_license`，根目录无 LICENSE 文件）
- 定位：**库模组/前置 API**——"以简单且兼容的方式向 MC 新生物群系/地形系统添加群系"
- 目标版本（`gradle.properties`）：`minecraft_version=26.2`、Java toolchain 25（`build.gradle:subprojects`）。**注意：仓库当前分支已非 1.20.1/1.21.1**，代码使用 `net.minecraft.resources.Identifier`（而非 `ResourceLocation`），示例模块 Forge 侧仍用 `ResourceLocation`。
- 加载器与 Gradle 插件：`fabric` 用 `net.fabricmc.fabric-loom 1.16-SNAPSHOT`；`neoforge` 用 `net.neoforged.moddev 2.0.141`；`forge` 用 `net.minecraftforge.gradle [7.0.17,8)`；根 `build.gradle` 额外 apply `gradleutils`（版本号取自 git tag）、`Minotaur`（发布）、`idea-ext`。`settings.gradle` 把 `common/forge/neoforge/fabric` 四个子项目重命名为首字母大写（`Common/Forge/NeoForge/Fabric`）。
- 编译依赖：Fabric 侧 `fabric-loader 0.19.3` + `fabric-api 0.153.0+26.2`，并 `include` 了 night-config toml/core 3.6.7（配置用，Fabric 需内嵌）。无第三方 mod 依赖——**它是别人的前置，不是别人的附属**。
- Fabric 侧无手写 `fabric.mod.json`（`fabric/src/main/resources/` 只有 mixin json），推测由 loom/构建脚本生成，未确认。

## 2. 源码规模与包结构

实测：`find -name '*.java' | wc -l` = **81 个文件**，`wc -l` 合计 **5893 行**。属于小而精的库（平均 73 行/文件）。

包结构（`common/src/main/java/terrablender/`）：

- `api`（10 文件）：对外 API——`Region`、`Regions`、`RegionType`、`ParameterUtils`、`VanillaParameterOverlayBuilder`、`ModifiedVanillaOverworldBuilder`、`TerrablenderOverworldBiomeBuilder`、`SurfaceRuleManager`、`EndBiomeRegistry`
- `api.data` + `api.data.condition`（7 文件）：数据驱动 region（`RegionDefinition`、`BiomeMapping`、`DataDrivenRegion`、条件类型）
- `core`（3）：`TerraBlender`、`Registries`、`TerraBlenderRegistries`
- `mixin`（11）：全部 mixin
- `worldgen`（10）+ `worldgen.noise`（10）+ `worldgen.surface`（1）：核心算法
- `config`（2）、`util`（4）；加载器专属：`neoforge/core`、`neoforge/handler`、`fabric/core`、`fabric/api`、`forge/core`、`forge/handler`

最大文件：`worldgen/TBSurfaceRuleData.java` 670、`api/ParameterUtils.java` 401、`config/Config.java` 233、`api/VanillaParameterOverlayBuilder.java` 232、`api/SurfaceRuleManager.java` 189、`mixin/MixinParameterList.java` 169、`api/Region.java` 164、`api/Regions.java` 160、`mixin/MixinTheEndBiomeSource.java` 159、`util/LevelUtils.java` 130。

## 3. 入口与注册

Common 无 `@Mod`，只有常量与全局状态：`common/src/main/java/terrablender/core/TerraBlender.java:25-27` 定义 `MOD_ID/LOGGER/CONFIG`，配置由各加载器注入（`setConfig`）。

- NeoForge：`neoforge/src/main/java/terrablender/core/TerraBlenderNeoForge.java:29-38`，`@Mod(MOD_ID)` 构造函数收 `IEventBus`，挂 `NeoForge.EVENT_BUS` 的 `ServerAboutToStartEvent`（`EventPriority.LOWEST`）、`DataPackRegistryEvent.NewRegistry`、`NewRegistryEvent`。
- Forge：同构的 `forge/src/main/java/terrablender/core/TerraBlenderForge.java` + `handler/InitializationHandler.java`（68 行）。
- Fabric：`fabric/src/main/java/terrablender/core/TerraBlenderFabric.java:35-58`，`ModInitializer` 内建注册表、注册数据包注册表、并发派发自己的入口点：

```java
FabricLoader.getInstance().getEntrypointContainers("terrablender", TerraBlenderApi.class)
    .forEach(entrypoint -> entrypoint.getEntrypoint().onTerraBlenderInitialized());
```

**注册框架的抽象点**：TerraBlender 自己要注册的是自定义注册表（region / biome_mapping_condition），于是定义了加载器中立的回调接口 `core/TerraBlenderRegistries.java:21-24`：

```java
public interface RegistryBootstrap {
    <T> Supplier<Registry<T>> create(ResourceKey<Registry<T>> key, Consumer<BiConsumer<Identifier, T>> entryRegistrar);
}
```

NeoForge 用 `NewRegistryEvent` + `RegistryBuilder`（`neoforge/.../InitializationHandler.java:52-62`），Fabric 用 `FabricRegistryBuilder.create(key).buildAndRegister()`（`TerraBlenderFabric.java:46`），Common 代码完全不知道加载器差异。数据包注册表同样双实现：NeoForge `event.dataPackRegistry(Registries.REGION, RegionDefinition.CODEC)`，Fabric `DynamicRegistries.registerSynced(...)`。普通游戏对象（群系本身）**不由 TerraBlender 注册**，由接入方自己用各加载器的 DeferredRegister 注册。

## 4. 核心系统

### 4.1 Region 抽象 + 参数覆盖（不覆盖原版的关键）

`api/Region.java:39-164`：抽象类，持有 `Identifier name / RegionType type / int weight`，子类只需实现 `addBiomes(Registry<Biome>, Consumer<Pair<ParameterPoint, ResourceKey<Biome>>>)`。`api/Regions.java:39-159` 用 `Map<RegionType, LinkedHashMap<Identifier, Region>>` + 独立 `indices` 表管理顺序，**静态块先注册 `DefaultOverworldRegion` 与 `DefaultNetherRegion` 占住 index 0**，因此所有模组区域都排在原版之后。配套 API：`addBiomeSimilar(mapper, 原版群系Key, 自己的群系)` 直接复制原版 ParameterPoint（`Region.java:146-150`），`VanillaParameterOverlayBuilder` 让新群系只覆盖原版参数空间的一部分。

### 4.2 区域噪声（uniqueness）+ 按区域分树查找

- `worldgen/noise/LayeredNoiseUtil.java:32-63`：用 `AreaContext`/`ZoomLayer.FUZZY`/N 次 `ZoomLayer.NORMAL`（层数 = 配置 `overworldRegionSize`/`netherRegionSize`）生成一张"该点属于哪个 region index"的噪声图，即 uniqueness。
- `mixin/MixinParameterList.java:60-101` `initializeForTerraBlender`：为**每个** region 单独构建 `Climate.RTree`，存进 `SearchTreeEntry[] uniqueTrees`；index 0 直接复用原版 `this.values`（为数据包兼容）。
- `findValuePositional`（同文件 134-150）：先取该点 uniqueness，再查对应树；若命中的是 `Region.DEFERRED_PLACEHOLDER`（`Region.java:42`，`terrablender:deferred_placeholder`）则回退到 tree[0]（原版树）。这就是"注入而不覆盖"的核心：原版群系参数点未被删除，只是被同位置的模组群系优先命中。

### 4.3 世界生成注入时机与"不覆盖原版"

`util/LevelUtils.java:47-129` 是关键：在 `ServerAboutToStartEvent`（LOWEST 优先级）里遍历 `Registries.LEVEL_STEM`，仅对 `NoiseBasedChunkGenerator` + `MultiNoiseBiomeSource` 生效；用 `DimensionTypeTags.NETHER_REGIONS/OVERWORLD_REGIONS`（`DimensionTypeTags.java`）判断维度该用哪套 region；然后 `parametersEx.initializeForTerraBlender(...)` 并 `biomeSourceEx.appendDeferredBiomesList(builder.build())`。`mixin/MixinBiomeSource.java:46-57` 里 `appendDeferredBiomesList` 只做 `possibleBiomes` 的追加+去重（`ObjectLinkedOpenHashSet`），**从不移除原版群系**。查询侧由 `mixin/MixinMultiNoiseBiomeSource.java:47-51` 在 `getNoiseBiome` HEAD 处直接 `cir.setReturnValue(findValuePositional(...))` 接管。

### 4.4 表层规则 API

`api/SurfaceRuleManager.java`：以 `RuleCategory(OVERWORLD/NETHER/END)` × namespace 存 `RuleBuilder`（`Function<HolderGetter<Biome>, SurfaceRules.RuleSource>`），提供 `addSurfaceRules`、`addToDefaultSurfaceRulesAtStage(category, RuleStage, priority, builder)`、`removeSurfaceRules`、`repopulateRules`；`worldgen/surface/NamespacedSurfaceRuleSource.java` 做按命名空间分发；`worldgen/TBSurfaceRuleData.java`（670 行）是原版表层规则的复刻模板。注入点：`mixin/MixinNoiseGeneratorSettings.java:43` 在 `surfaceRule()` HEAD 可取消返回。

### 4.5 末地支持

`mixin/MixinTheEndBiomeSource.java`（159 行，7 个 `@Unique` 字段）+ `api/EndBiomeRegistry.java` + 配置里的 `endHighlandsBiomeSize` 等 8 个权重，把末地四类群系（highlands/midlands/edge/islands）也做成可加权的区域查找。

### 4.6 数据驱动 region

`api/data/RegionDefinition.java:29-41`：`record RegionDefinition(Identifier name, RegionType type, int weight, List<BiomeMapping> biomeMappings, BiomeMappingCondition condition)` + `RecordCodecBuilder`；`BiomeMapping` 用 `Climate.ParameterPoint.CODEC`；条件系统在 `api/data/condition/`（`BiomeMappingConditionType`、`BiomeMappingConditionTypes`、`AlwaysTrueCondition`）。数据包写好的定义在 `Regions.loadDataDrivenRegions(registryAccess)`（`Regions.java:42-50`）里转成 `DataDrivenRegion` 并注册。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自建包**。同步完全依赖原版/加载器的**数据包注册表同步**（NeoForge `dataPackRegistry` / Fabric `registerSynced`），region 定义随数据包同步到客户端。
- **数据驱动**：见 4.6，`terrablender:region` 与 `terrablender:biome_mapping_condition` 两个注册表；`MixinParameterList` 中 `recreateUniqueness()`（`IExtendedParameterList.java:35`）支持重新生成噪声。
- **配置**：`config/Config.java`(233) + `config/TerraBlenderConfig.java`，基于 night-config TOML，字段 `overworldRegionSize`/`netherRegionSize`/`vanillaOverworldRegionWeight`/`vanillaNetherRegionWeight`/`end*BiomeSize`/`vanillaEnd*Weight`；各加载器各自 new 一份（NeoForge `FMLPaths.CONFIGDIR`，Fabric `FabricLoader.getConfigDir()`），再 `TerraBlender.setConfig`。
- **datagen**：仅示例模块有 `example/Fabric/.../datagen/DataGen.java`，库本体无。

## 6. Mixin

配置文件：`common/src/main/resources/terrablender.mixins.json`（`package: terrablender.mixin`，10 个 common mixin + client 1 个，`defaultRequire: 1`、`minVersion 0.8.4`）、`terrablender.fabric.mixins.json`（`MixinMinecraftServer`）、`terrablender.forge/neoforge.mixins.json`（**列表为空**，仅占位挂 refmap）。另有 `common/src/main/resources/terrablender.accesswidener` 与 `META-INF/accesstransformer.cfg`。

代表性 hook：

| 类 | 目标 | 注入点 |
|---|---|---|
| `MixinParameterList` | `Climate.ParameterList` | `implements IExtendedParameterList`，无 @Inject，纯接口扩展 |
| `MixinMultiNoiseBiomeSource` | `getNoiseBiome(IIILClimate$Sampler;)` | HEAD + cancellable；另 `addDebugInfo` TAIL 输出 Region 名 |
| `MixinBiomeSource` | `BiomeSource.possibleBiomes` | `@Shadow` + `@Unique` 追加列表 |
| `MixinNoiseGeneratorSettings` | `surfaceRule` | HEAD cancellable |
| `MixinNoiseBasedChunkGenerator` | `doCreateBiomes` | `@ModifyArg` 改 `fillBiomesFromNoise` 的 BiomeResolver |
| `MixinChunkGenerator` | `validate` | HEAD cancellable |
| `MixinBuiltInRegistries` | `registerSimple` | HEAD cancellable |
| `MixinTheEndBiomeSource` | `collectPossibleBiomes`/`getNoiseBiome` | RETURN/HEAD cancellable |
| `MixinPrimaryLevelData` / `MixinWorldOpenFlows`(client) | `worldGenSettingsLifecycle` / `confirmWorldCreation` | HEAD cancellable，跳过"实验性世界"警告 |
| `MixinMinecraftServer`(fabric) | `<init>` | `@At("RETURN")`，`priority = 995` |
| `MultiNoiseBiomeSourceAccess` | `MultiNoiseBiomeSource` | 两个 `@Accessor` |

## 7. 值得学的 5 条做法

1. **在 server-about-to-start 做一次性后处理，而不是注册期**：`LevelUtils.initializeOnServerStart`（`util/LevelUtils.java:47`）遍历 LevelStem 并逐个 BiomeSource 打标；适用"必须等注册表/存档 seed 就绪"的注入类 mod。
2. **"占位符 + 回退"实现非破坏式覆盖**：`Region.DEFERRED_PLACEHOLDER` 命中时回退 tree[0]（`MixinParameterList.java:146`），比直接改原版参数表更兼容。
3. **index 0 留给原版**：`Regions` 静态块先注册 `DefaultOverworldRegion`/`DefaultNetherRegion`（`api/Regions.java:148-159`），第三方一律 append，天然避免"谁先加载谁赢"。
4. **把加载器差异压成一个函数式接口**：`TerraBlenderRegistries.RegistryBootstrap`（`core/TerraBlenderRegistries.java:16-24`），每个加载器 ~10 行实现，其余 95% 代码在 common。
5. **能力扩展用"自建接口 + 在 mixin 上 implements"**：`IExtendedParameterList`/`IExtendedBiomeSource` 定义接口，mixin 类实现（`MixinParameterList implements IExtendedParameterList`），调用侧只做一次 `(IExtendedBiomeSource) src` 强转（`LevelUtils.java:111-114`），比反射/Accessor 更类型安全。

## 8. 公开 API 与外部 mod 接入方式

- API 包：`terrablender.api`（主）、`terrablender.api.data` / `...data.condition`（数据驱动）。
- 主要扩展点：`Region`（覆写 `addBiomes`）、`Regions.register(name, weight, region)`、`SurfaceRuleManager.addSurfaceRules(category, namespace, builder)`、`EndBiomeRegistry`、`ParameterUtils`（`Temperature/Humidity/Continentalness/Erosion/Weirdness/Depth` span 枚举 + `ParameterPointListBuilder`）、`VanillaParameterOverlayBuilder`、`ModifiedVanillaOverworldBuilder`、`TerrablenderOverworldBiomeBuilder`。
- 接入时序（示例见 `example/{NeoForge,Forge,Fabric}/src/main/java/terrablender/example/TestMod.java`）：
  - NeoForge/Forge：在 mod 构造/FMLCommonSetup 阶段 `Regions.register(new TestRegion1(id("overworld_1"), 2))`（`example/NeoForge/.../TestMod.java:45-49`），随后 `SurfaceRuleManager.addSurfaceRules(RuleCategory.OVERWORLD, MOD_ID, TestSurfaceRuleData.makeRules())`。
  - Fabric：mod 主类同时 `implements ModInitializer, TerraBlenderApi`（`example/Fabric/.../TestMod.java:26`），在 `onTerraBlenderInitialized()` 里注册；入口点名固定为 `terrablender`（`fabric/core/TerraBlenderFabric.java:53`）。
- 关于 Biomes O' Plenty 等下游：本仓库内**未见任何 BOP 集成代码**（BOP 是消费方），未确认其具体接入代码位置。
