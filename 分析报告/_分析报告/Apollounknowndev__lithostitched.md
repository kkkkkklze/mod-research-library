# Lithostitched 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Lithostitched / `lithostitched` |
| 作者 | Apollo（build.gradle.kts 的 `author("Apollo")`；部分文件署名 SmellyModder） |
| 版本 / 目标 | `1.8.0+beta1`；**多目标同源构建**：`fabric:21.1` = MC 1.21.1 + Fabric Loader 0.18.4，`fabric:26.1` = MC 26.1.2，`fabric:26.2` = MC 26.2；neoforge 同样 21.1 / 26.1 / 26.2 三档（`build.gradle.kts:50-140`） |
| Gradle | Kotlin DSL + `kotlin("jvm") 2.1.0` + **`earth.terrarium.cloche` 0.18.11**（Cloche 多版本构建插件）；`src/{common,shared/<ver>,fabric/<ver>,neoforge/<ver>}` 分层 source set，含 accessWidener、mixins 逐 target 注册 |
| 许可证 / 定位 | MIT；README 自述"library mod with new configurability and compatibility enhancements for worldgen"——**世界生成库/前置** |
| 编译依赖 | Fabric 侧 `fabricApi("0.116.1")`（21.1）/`0.148.0`（26.x）；`compileOnly("org.spongepowered:mixin:0.8.3")`；TerraBlender 兼容代码被注释（`// modImplementation(...TerraBlender-fabric:1.21.1-4.1.0.8)`），但 `mixin/common/compat/terrablender/` 仍在 |

## 2. 源码规模与包结构

- 共 **517 个 `.java`、约 25.8k 行**：`src/common` 243 文件/13705 行，`src/shared` 196/9457，`src/neoforge` 54/1879，`src/fabric` 24/751。
- `common` 顶层包：`api/`（公开 API）、`impl/`（实现）、`mixin/`、`worldgen/`（具体功能）、`config/`、`duck/`（跨 mixin 的访问接口）、`util/`、`registry/`。
- `api/worldgen/` 子包：`biomeinjector`、`modifier`、`bandlands`、`blockentitymodifier`、`blockpredicate`、`densityfunction/fastnoise`、`feature`、`placementcondition`、`placementmodifier`、`poolelement`、`processor`(+`enums`)、`processorcondition`、`stateprovider`、`structure`、`util`。
- 最大文件：`api/worldgen/densityfunction/fastnoise/FNL.java` 2621、`shared/21.1/.../structure/AlternateJigsawGenerator.java` 436（21.1 与 26.x 分版本各一份）、`api/worldgen/modifier/WorldgenModifier.java` 278、`impl/.../biomeinjector/internal/InjectorBiomeSource.java` 253、`api/registry/LithostitchedBuiltInRegistries.java` 208。

## 3. 入口与注册

- 公共入口/常量类 `src/common/main/java/dev/worldgen/lithostitched/Lithostitched.java`：`MOD_ID`、`LOGGER`、`id(String)`、`vanillaToLithostitched(Identifier)`，以及 **`@Expect` 方法**（`registry(RegistryAccess, ResourceKey)`、`scheduleTick(...)`、`getInitialDensity(NoiseRouter)` 等），注解来自 `net.msrandom.multiplatform.annotations.Expect`。
- 各 MC 版本实现放 `src/shared/<ver>/.../LithostitchedActual.java`，用 `@Actual` 标注同名同签名方法返回版本相关实现（如 `router.initialDensityWithoutJaggedness()`）。
- 平台入口：`LithostitchedNeoforge`（`@Mod(MOD_ID)`，构造注入 `IEventBus`，依次 `ConfigHandler.load()` → `LithostitchedBuiltInRegistries.init()` → `LithostitchedRegistrations.init(bus)`）；`LithostitchedFabric implements ModInitializer`，`onInitialize` 里 `ResourceConditions.register(BreaksSeedParityCondition.TYPE)`。
- 注册抽象：`impl/registry/LithostitchedRegistrar`（`@Expect registerRegistry(key, codec)` / `register(key, Map<String,T>)`）→ NeoForge `LithostitchedRegistrarActual` 把动态注册包装成 `DataPackRegistryEvent.NewRegistry` 监听器，静态项用 `REGISTER_CACHE`（`Map<ResourceKey<?>, DeferredRegister<?>>`）+ `bus` 统一注册；Fabric 版用 `DynamicRegistries.register` 与 `Registry.register`。

## 4. 核心系统

1. **WorldgenModifier：数据驱动的世界生成补丁管线** `api/worldgen/modifier/WorldgenModifier.java:53`：接口方法 `Optional<LoadPredicate> predicate() / int priority() / void apply(RegistryAccess) / MapCodec<? extends WorldgenModifier> codec()`；`CODEC = LithostitchedBuiltInRegistries.MODIFIER_TYPE.byNameCodec().dispatch(WorldgenModifier::codec, Function.identity())`；常量 `DEFAULT_PRIORITY=1000`、`REMOVAL_PRIORITY=2000` 及配对 codec `PRIORITY_DEFAULT_CODEC / PRIORITY_REMOVE_CODEC`；内置 `ModifierBuilder` 提供 ~30 个链式方法（`addFeatures`、`removeBiomeSpawns`、`setPoolElementProcessors`、`wrapNoiseRouter`、`stackFeatures`…）。
2. **ModifierManager：注册表与代码事件双通道合并 + 优先级排序执行** `impl/worldgen/modifier/ModifierManager.java:22`：`getAllModifiers` 先读 `LithostitchedRegistries.WORLDGEN_MODIFIER` 数据包注册表，再经 `AddWorldgenModifiersEvent.EVENT.invoker().addModifiers(registries, (id, modifier) -> ...)` 合并（已存在 ID 不覆盖）；`sortByPriority` 用 `Comparator.comparingInt(priority)`；若任一 modifier `shouldRecompileSortedFeatures()` 则用 `ChunkGeneratorAccessor` 重建 `FeatureSorter.buildFeaturesPerStep`，并 `LithostitchedPlatform.memoize(...)` 懒重算（仅 Fabric 分支执行）。
3. **无加载器依赖的自建事件总线** `impl/event/LithostitchedEvent.java`：`register(T)` + `invoker()`（`Function<List<T>, T>` 聚合），公开事件 `api/event/AddWorldgenModifiersEvent`、`AddBiomeInjectorsEvent`、`AddRegionsEvent` 均以 `EVENT` 常量暴露。
4. **BiomeInjector 体系：改生物群系布局** `api/worldgen/biomeinjector/BiomeInjector.java:33`：`dimension() / possibleBiomes() / mapAll(DensityFunctionWrapper)` + `ClimateParameter` 枚举（continentalness/erosion/weirdness/humidity/temperature/depth）；实现类 `impl/worldgen/biomeinjector/{AddPoints,DispatchAlternateLayout,ForcePlacement,ReplaceFully,ReplacePartially}.java`，管理器 `BiomeInjectorManager` + `RegionManager`（`REGION` 动态注册表），并用 `InjectorBiomeSource`/`ParameterMap` 替换原 `MultiNoiseBiomeSource`。
5. **服务端启动统一注入点** `impl/LithostitchedInternalHooks.java:17` `onServerAboutToStart(MinecraftServer)` 按序执行 `ModifierManager.applyModifiers` → `SurfaceRuleManager.applySurfaceRules` → `BiomeInjectorManager.applyBiomeInjectors(..., seed)` → 给所有 `fast_noise_config` `bind(seed)`；由 `mixin/client/IntegratedServerMixin`、`mixin/server/DedicatedServerMixin`、`mixin/common/GameTestServerMixin`（NeoForge 另有 `ServerLifecycleHooksMixin`）在服务器启动时调用。
6. **FastNoise 密度函数注入** `api/worldgen/densityfunction/fastnoise/`（`FNL.java` 2621 行）+ `impl/worldgen/fastnoise/{PerlinNoiseType,SimplexNoiseType,CellularNoiseType}`：把 FastNoise 噪声作为数据驱动 `DensityFunction` 暴露给世界生成。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无（纯服务端/世界生成，无自定义 payload）。
- **数据驱动（核心）**：7 个动态（数据包）注册表 + 7 个静态 codec 注册表，声明集中在一个接口 `api/registry/LithostitchedRegistries.java`：动态 `worldgen_modifier / surface_rule / bandlands / template_list / biome_injector / fast_noise_config / region`；静态 `modifier_type / placement_condition_type / processor_condition_type / bandlands_band_type / biome_injector_type / fast_noise_config_type / load_predicate_type`。`LithostitchedBuiltInRegistries` 用 `@Expect` 的 `create(key)` 桥到平台实际注册对象。`LoadPredicate`（`api/predicate/LoadPredicate.java`）给每条 modifier/injector 挂在配置/环境下是否启用。另注册 `BreaksSeedParityCondition`（NeoForge `ICondition` / Fabric `ResourceConditions`）作为数据包加载条件。
- **配置**：`config/ConfigHandler.java`，自写 codec（`ConfigCodec.CODEC` + `JsonOps.INSTANCE`）读写 `<config>/lithostitched.json`，解析失败回退默认并重写文件；写入时用 `JsonWriter.setIndent("  ")` + `GsonHelper.writeValue(jsonWriter, element, Comparator.naturalOrder())` 排序键，再经 `commentHack` 注入注释。
- **datagen**：仓库内未见独立 datagen 入口（`LithostitchedBuiltInRegistries` 注释写"public only for usage in datagen"，未确认是否由外部模块生成）。

## 6. Mixin

分三层配置，均为 `JAVA_17`、`injectors.defaultRequire=1`：

- `src/common/main/lithostitched.mixins.json`（49 项）：含大量 `*Accessor`/`*Invoker`（`MappedRegistryAccessor`、`ChunkGeneratorAccessor`、`MultiNoiseBiomeSourceAccessor`、`BiomeSourceInvoker`、`RandomStateAccessor`…）、功能 mixin（`common.mnbs.MNBSMixin` / `MNBSPLMixin` 改多噪声群系源、`common.bandlands.SurfaceSystemMixin`、`common.processor.StructureStartMixin`、`common.template.mansion.PiecePlacerMixin` 等）、`mixinextras.minVersion: 0.5.0`，客户端/服务端各 `client.IntegratedServerMixin` / `server.DedicatedServerMixin`。
- `src/shared/21.1/main/lithostitched.21.1.mixins.json`：`DensityFunctionsMapAllMixin`、`RegistryDataLoaderMixin`、`RuinedPortalPieceMixin`、`VillagerTypeMixin`、`SurfaceRulesContextMixin2` + `lithostitched.21.1.accesswidener`（每版本一份 AW）。
- 平台侧 `src/neoforge/21.1/main/lithostitched.neoforge.mixins.json`（`BeardifierMixin`、`ServerLifecycleHooksMixin`）/ `src/fabric/21.1/...`（仅 `BeardifierMixin`）。

## 7. 值得学的 5 条具体做法

1. **用 Cloche + `@Expect/@Actual` 做真正的多版本同源**（而不是 architectury 运行时抽象）：`impl/LithostitchedPlatform.java`、`impl/registry/LithostitchedRegistrar.java` 只写声明，实现落在 `src/shared/<ver>/...LithostitchedActual.java`、`src/neoforge|fabric/<ver>/...PlatformActual.java`；适用"库模组要同时供 1.21.1 与 26.x"。
2. **自定义 tiny mapping 统一跨版本类名**：`build.gradle.kts:71-75` 对 `fabric:21.1` 使用 `mappings { official(); custom(files("mappings/$minecraftVersion.tiny")) }`，使 1.21.1 与 26.x 源码共用 `Identifier`、`LevelStem` 等新命名；适用不想维护两套命名的团队（本副本无 `mappings/` 目录，内容未确认）。
3. **`priority` + 成对 codec 表达"增/删"两类语义**：`WorldgenModifier.DEFAULT_PRIORITY=1000` / `REMOVAL_PRIORITY=2000` 配合 `PRIORITY_DEFAULT_CODEC` / `PRIORITY_REMOVE_CODEC`，让删除型补丁默认排在添加型之后 → `api/worldgen/modifier/WorldgenModifier.java:55-59`。
4. **数据包注册表 + 代码事件双通道合并同一种数据**，且以 ID 去重、`sortByPriority` 统一执行 → `impl/worldgen/modifier/ModifierManager.java:29-62`；适用"既要 JSON 可配又要 API 可注册"的系统。
5. **改动原版缓存后主动失效**：修改生物群系特征后，用 accessor 调 `setFeaturesPerStep(Platform.memoize(() -> FeatureSorter.buildFeaturesPerStep(...)))` 重算并懒求值 → `impl/worldgen/modifier/ModifierManager.java:39-47`；适用任何需要 patch 原版世界生成缓存的模组。

## 8. 公开 API 包路径与接入方式

- **API 包**：`dev.worldgen.lithostitched.api.*`（`event` / `predicate` / `registry` / `tag` / `util` / `worldgen/**`），核心入口类 `Lithostitched`（文档明确"Undocumented methods can be considered not API"）。
- **扩展点**：① 注册自定义数据包类型——实现 `WorldgenModifier` / `BiomeInjector` / `PlacementCondition` / `ProcessorCondition` / `Band` / `FastNoiseConfig` / `LoadPredicate` 接口并用 `LithostitchedRegistrar`/`LithostitchedBuiltInRegistries` 注册其 `MapCodec`；② 代码侧注入——监听 `AddWorldgenModifiersEvent.EVENT` / `AddBiomeInjectorsEvent.EVENT` / `AddRegionsEvent.EVENT`，用 `WorldgenModifier.builder()`、`BiomeInjector.builder(Level.OVERWORLD)` 构造对象并以 `Identifier` 提交（Javadoc 内即含示例）。
- **数据包侧接入**：往 `data/<ns>/lithostitched/{worldgen_modifier,biome_injector,region,...}/` 写 JSON，或写 `surface_rule`、`template_list`（`TemplateList` 提供 `raw` 模板再经 `CompileRawTemplatesModifier` 编译）。
- 兼容层：`mixin/common/compat/terrablender/NoiseBasedChunkGeneratorMixin` 处理 TerraBlender 共存；`config` 中 `breaksSeedParity()` 说明其改动默认破坏原版种子一致性（可由配置/数据包条件关闭）。
