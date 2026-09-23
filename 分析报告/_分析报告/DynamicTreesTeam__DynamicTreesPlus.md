# DynamicTreesTeam/DynamicTreesPlus 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Dynamic Trees Plus / `dynamictreesplus`（`gradle.properties`：`mod_version=1.3.2`、`group=com.dtteam.dynamictreesplus`、`versionType=stable`）
- 作者 / 许可证：Ferreusveritas、Max Hyper、Harley O'Connor；**MIT**（`TEMPLATE_LICENSE.txt`、`license=MIT`）
- 目标版本：Minecraft **1.21.1**（`minecraft_version_range=[1.21.1, 1.22)`）、Java 21、Parchment `2024.11.10`、neoform `1.21.1-20240808.144430`
- 加载器（三模块 `common / fabric / neoforge`）：Fabric `fabric_version=0.109.0+1.21.1`、loader `0.16.9`；NeoForge `21.1.80`（`neoforge_loader_version_range=[4,)`）；还留有 Forge `52.0.28` 配置项。Fabric 端额外用 **`forge_config_api_port` `21.1.6`** 复用 NeoForge 的 `ModConfigSpec`（`fabric/.../DynamicTreesPlusFabric.java:6,14`）
- Gradle：multiloader 模板（`buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle`），fabric 用 `fabric-loom`，neoforge 用 NeoGradle/ModDevGradle（未细则确认）
- 编译依赖（重点）：**唯一硬依赖是 Dynamic Trees 本体** —— fabric `modImplementation "com.dtteam.dynamictrees:dynamictrees-fabric-1.21.1:1.7.1-BETA2.001"`（`fabric/build.gradle:65`），neoforge `neoforge_dynamic_trees_version=1.7.1`；`neoforge.mods.toml` 声明 `modId="dynamictrees" versionRange="[1.7.0,)" ordering="AFTER" mandatory=true`；common 侧 `common_dynamic_trees_version=1.7.1`。dev-only：`curse.maven:jade-324717`、`jei-238222`、`glitchcore-955399`、`serene-seasons-291874`
- 定位：**上游 DynamicTrees 的官方 addon**（`README` 自述 "Vanilla addon for Dynamic Trees"），只使用 `com.dtteam.dynamictrees.api.*` 公开包 + 数据包

## 2. 源码规模与包结构

实测 **62 个 `.java` / 5821 行**（common 42 / fabric 6 / neoforge 14）。

包（`com.dtteam.dynamictreesplus`）：
- common：`systems`（`featuregen` 3 + `growthlogic` 4 + `mushroomlogic`（含 `context`/`shapekits`）9 + `nodemapper` 1 + `thicknesslogic` 2 = 18 个，最大块）、`block`(+`block/mushroom` 5) 8、`resources` 3、`tree` 4、`worldgen`（`canceller` 2 + `structure` 1）、`data` 1、`init` 1、`items` 1、根类 1 + 3 个 `package-info`
- fabric：`DynamicTreesPlusFabric`（ModInitializer）+ `event` 5（`DTPAddonEntrypoint`、`DTPCommonEventHandler`、`DTPRegistryHandler`、`JsonRegistriesEntrypointHandler`、`ModRegistryEntrypointHandler`）
- neoforge：`model`（`baked` 1 + `geometry` 1 + `loader` 1）、`event` 5、`data` 3（datagen）、入口 1

最大文件：`neoforge/model/baked/CactusBranchBlockBakedModel.java` **743**、`block/mushroom/CapProperties` 515、`tree/HugeMushroomSpecies` 498、`block/CactusBranchBlock` 406、`block/mushroom/DynamicCapCenterBlock` 347、`DynamicCapBlock` 263、`tree/CactusSpecies` 212、`MushroomBranchBlock` 184、`systems/nodemapper/MushroomInflatorNode` 136、`systems/mushroomlogic/shapekits/BellShape` 136。

资源侧：`common/src/main/resources/trees/dynamictreesplus/jo_codes/*.txt` 7 个（brown_mushroom、red_mushroom、mega_brown/red_mushroom、pillar_cactus、pipe_cactus、saguaro_cactus）——DT 的 ASCII 树形描述语言（JoCode）；**无 mixins.json、无 accesswidener**，json 资源被 sparse checkout 排除。

## 3. 入口与注册

common 无入口类，根类 `DynamicTreesPlus.java` 只放 `MOD_ID` 与一组资源名常量（`CACTUS`/`MUSHROOM`/`PILLAR`/`PIPE`/`SAGUARO`/`MEGA`，:8-14）。

Fabric 侧通过上游提供的 addon 入口点接入，`fabric/.../event/DTPAddonEntrypoint.java:12-42`：

```java
public class DTPAddonEntrypoint implements DynamicTreesAddonEntrypoint {
  public void onDynamicTreesPreSetup() {
    FabricRegistryHandler.setup(DynamicTreesPlus.MOD_ID);
    ModRegistryEntrypointHandler.registerGrowthLogic();  /* + CactusThicknessLogic / GenFeature /
        FruitType / FamilyType / SpeciesType / FeatureCanceller / MushroomShapeKit */
    DTPJsonDeserializers.register();
  }
  public void onAddResourceLoaders(TreeResourceManager rm) { rm.addLoader(CapPropertiesResourceLoader.CAP_PROPERTIES_LOADER); ... }
  public <O,I> void onRegisterStagedApplier(StagedApplierResourceLoader.ApplierStage stage, PropertyAppliers<O,I> appliers, String id) { ... }
}
```

NeoForge 侧是标准 `@Mod`，`neoforge/.../DynamicTreesPlusNeoForge.java:24-57`：注册 `DTPConfigs.SERVER_CONFIG`/`COMMON_CONFIG`、`DTPShapes.setup()`、`DTPDataGenerators.register()`、`NeoForgeRegistryHandler.setup(MOD_ID, modBus)`，并在 `GatherDataEvent` 里注册 `BranchLoaderBuilder`、跑 `Resources.MANAGER.gatherData()` 与 `GatherDataHelper.gatherAllData(modid, event, SoilProperties/Family/Species/LeavesProperties/CapProperties 五个 REGISTRY)`。

Fabric 入口 `fabric/.../DynamicTreesPlusFabric.java:12-22`：用 `NeoForgeConfigRegistry.INSTANCE.register(... SERVER/COMMON, DTPConfigs.*_CONFIG)` 注册配置，`DTPShapes.setup()`、`DTPCommonEventHandler.RegisterEvents()`、`DTPRegistryHandler.LockRegistries()`。

注册框架：**没有 DeferredRegister**，全走上游 `TypedRegistry<T>` + JSON。每个可扩展类型自己持 `TypedRegistry`（如 `CapProperties.REGISTRY`、`MushroomShapeKit.REGISTRY`、`CactusThicknessLogic.REGISTRY`），并注册 `TypedRegistry.EntryType`（例：`CactusSpecies.TYPE = createDefaultType(CactusSpecies::new)`，`tree/CactusSpecies.java:43`）。

## 4. 核心系统

1. **蘑菇帽数据对象 `block/mushroom/CapProperties.java`（515 行）**：把"巨型蘑菇的伞帽"抽象为 json 驱动的注册项；字段含 `primitiveCap`、`generateFaceModels`、`textureOverrides`/`modelOverrides`、`mushroomItem`、`family`、`fireSpreadSpeed`/`flammability`、`ageZeroShape`、`blockRegistryName`/`centerBlockRegistryName`；`generateDynamicCapBlocks(BlockBehaviour.Properties)` 可**从 json 自动生成方块**（`DynamicCapBlock` / `DynamicCapCenterBlock`）；`blockStateGenerators` 表供 datagen 挂生成器。
2. **三阶段属性 applier 体系（上游 `StagedApplierResourceLoader`）**：`CapPropertiesResourceLoader.registerAppliers()` 分三段注册（`CapPropertiesResourceLoader.java:38-66`）：`gatherDataAppliers`（必须最先，如 `primitive_cap`、`mushroom_item`）、`setupAppliers`（客户端也要，如 `family` 用 `Family.REGISTRY.runOnNextLock(...)` 延迟到注册表锁定后解析，避免加载顺序问题）、`reloadAppliers`（重载可改：fire_spread/flammability/age_zero_shape）。附带 `registerMapApplier` 处理 map 型字段。
3. **仙人掌生长体系**：`block/CactusBranchBlock`（内含 enum `CactusThickness`）+ `systems/thicknesslogic/*`（`CactusThicknessLogic` + `CactusThicknessLogicKits`）+ `systems/growthlogic/*`（`StraightLogic` 直杆、`SaguaroCactusLogic`、`MegaCactusLogic`、`DTPGrowthLogicKits`）+ `tree/CactusSpecies`（默认 ARID 气候、Wool 音效、`setGrowthLogicKit(STRAIGHT_LOGIC)`、`FoodSeed` 可食种子）；果实侧 `block/CactusFruit`/`CactusFruitBlock` + `systems/featuregen/CactusFruitGenFeature`、`CactusClonesGenFeature`。
4. **巨型蘑菇体系**：`systems/mushroomlogic/*`（`MushroomShapeKit.REGISTRY`、`MushroomShapeConfiguration` + `TEMPLATES` 模板表、`MushroomShapeClusters`、`MushroomCapDisc`、`context/MushroomCapContext`、`shapekits/BellShape`/`MushroomShapeKits`）+ `tree/HugeMushroomSpecies`(498) + `systems/nodemapper/MushroomInflatorNode`（把 DT 生长的树节点膨胀/映射为蘑菇伞形）。
5. **世界生成接管**：`worldgen/canceller/CactusFeatureCanceller`、`MushroomFeatureCanceller`（取消原版 cactus/大蘑菇 feature，改由 DT 的 tree 接管）、`worldgen/structure/VillageCactusReplacement`（村庄仙人掌替换；NeoForge 中调用处被注释 `DynamicTreesPlusNeoForge.java:41`）。
6. **自研模型管线（neoforge 独有）**：`model/baked/CactusBranchBlockBakedModel`(743) + `model/geometry/CactusBranchBlockModelGeometry` + `model/loader/CactusBlockModelLoader` + `event/BakedModelEventHandler`，配套 datagen `CapStateGenerator`/`CapCenterStateGenerator`（登记进 `CapProperties.blockStateGenerators`，`data/DTPDataGenerators.java:8-11`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（仓库内无 packet 类）。
- 数据驱动（本项目的主体）：`resources/CapPropertiesResourceLoader extends JsonRegistryResourceLoader<CapProperties>`（读 `cap_properties` json）；`ConfigurationTemplateResourceLoader<MushroomShapeConfiguration, MushroomShapeKit>`（读 `mushroom_shape_kits/configurations`，模板 + 配置写法）；`resources/DTPJsonDeserializers.register()` 为自定义类型挂 json 反序列化器——`CactusThickness`(enum)、`CactusThicknessLogic`/`MushroomShapeKit`/`CapProperties`（`RegistryEntryDeserializer`）、`ConfiguredDeserializer("Mushroom Shape Kit", … MushroomShapeConfiguration.TEMPLATES)`（`DTPJsonDeserializers.java:20-40`）；`resources/DTPShapes` 把 3 个仙人掌树苗 `VoxelShape` 注册进上游 `CommonVoxelShapes.SHAPES`。新树/新蘑菇 = jo_code 文本 + json + 代码里的 `EntryType`/deserializer。
- 配置：`init/DTPConfigs` 用 NeoForge `ModConfigSpec`（SERVER：`canBoneMealCactus`/`cactusPrickleOnMoveOnly`/`cactusKillItems`；COMMON：`replaceMushroomSaplingOnPlacement`/`replaceMushroomSaplingOnGrowth`），Fabric 端经 forge_config_api_port 复用同一 spec。
- datagen：neoforge `GatherDataEvent` → `Resources.MANAGER.gatherData()` + `GatherDataHelper.gatherAllData(...)`（5 个上游 registry）+ 自研状态生成器（见 4-(6)）。
- **Mixin：无**（`grep -rn "@Mixin"` 全仓库 0 命中；无 mixins.json、无 accesswidener，`neoforge.mods.toml` 里的 `[[mixins]]` 段是注释状态）。

## 6. Mixin

无。全仓库 62 个类、零 mixin、零 accesswidener——扩展完全通过上游 `DynamicTreesAddonEntrypoint` + TypedRegistry + JSON 反序列化器完成，这是本仓库最值得注意的工程信号（做大型 mod 的官方附属时首选路线）。

## 7. 值得学的 5 条具体做法

1. **addon 只依赖上游 API + 数据包，零 mixin**：接入点是上游定义的 `DynamicTreesAddonEntrypoint`（三个回调：preSetup / addResourceLoaders / registerStagedApplier），见 `fabric/.../event/DTPAddonEntrypoint.java:12-42`。附属 mod 与本体版本解耦。
2. **属性赋值分阶段 + `runOnNextLock` 延迟解析**：需要其它注册表先就绪的字段（如 `family`）留到 `setupAppliers` 并用 `Family.REGISTRY.runOnNextLock(generateIfValidRunnable(...))`，失败时 `logWarning` 而不是崩溃（`resources/CapPropertiesResourceLoader.java:50-59`）。适合任何"注册项互相引用"的场景。
3. **主动注册 JSON 反序列化器**（`JsonDeserializers.register`、`RegistryEntryDeserializer`、`ConfiguredDeserializer` 模板机制）让数据包能引用自定义 Java 类型（`resources/DTPJsonDeserializers.java:20-40`）——比维护 `Codec` 更省事的"数据驱动反射式"方案。
4. **用上游 Injector 完成平台注册**：Fabric 走 `FabricRegistryHandler.setup(modid)`、NeoForge 走 `NeoForgeRegistryHandler.setup(modid, modBus)`，业务代码两边共用（`DTPAddonEntrypoint.java:16`、`DynamicTreesPlusNeoForge.java:37`）。
5. **世界生成"先取消再接管"**：`CactusFeatureCanceller`/`MushroomFeatureCanceller` 取消原版 feature，再由自己的 Species/GrowthLogic/GenFeature 重新生成（`worldgen/canceller/*`）——替换原版地物而不改原版 class 的干净做法。
6. （附）Fabric 端用 `forge_config_api_port` 直接复用 NeoForge `ModConfigSpec`，避免为 Fabric 另写配置层（`DynamicTreesPlusFabric.java:5-14`）。

## 8. 公开 API 与外部接入方式

非库模组（是上游 DynamicTrees 的 addon），不对外提供 API；自身即为"如何接入 DynamicTrees 生态"的官方范例：上游 API 包 `com.dtteam.dynamictrees.api.*`（`DynamicTreesAddonEntrypoint`、`registry.TypedRegistry/RegistryHandler`、`resource.TreeResourceManager`、`resource.loading.StagedApplierResourceLoader/JsonRegistryResourceLoader`、`deserialization.JsonDeserializers/PropertyAppliers`、`platform.Services`）与平台处理器 `FabricRegistryHandler`/`NeoForgeRegistryHandler`。
