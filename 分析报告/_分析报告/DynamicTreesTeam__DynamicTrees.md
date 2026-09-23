# DynamicTreesTeam/DynamicTrees 源码分析报告

## 1. 基本信息

- Mod 名：Dynamic Trees（"Trees that grow, forests that spread..."）；mod_id `dynamictrees`；`mod_author=Ferreusveritas`，credits 注明当前开发者 MaxHyper、treepack 作者 Harley O'Connor（`gradle.properties:4-8`，`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）
- 版本：`1.7.2`（Fabric 产物加 `-BETA` 后缀，`fabricVersionAppend`）
- 目标 MC / 加载器：**1.21.1，范围 `[1.21.1, 1.22)`**；NeoForge `21.1.80`（loader range `[4,)`）、Fabric Loader `0.18.4` + Fabric API `0.116.8+1.21.1`；`forge_version=52.0.28` 标注 "// Unused"（已弃 Forge，仅保留参数）
- Java 21；映射 Parchment `1.21 / 2024.11.10`；`org.gradle.jvmargs=-Xmx3G`、`daemon=false`
- Gradle 插件：`multiloader-loader`（`buildSrc` 自定义约定插件，`neoforge/build.gradle` / `fabric/build.gradle` 首行）+ `net.neoforged.moddev`（NeoForge）+ `fabric-loom` + `me.modmuss50.mod-publish-plugin`；`settings.gradle` 用 `exclusiveContent` 分流 Fabric/Sponge/Forge 仓库
- 编译依赖：`fuzs.forgeconfigapiport:forgeconfigapiport-fabric:21.1.6`（Fabric 侧提供 NeoForge 式 `ModConfigSpec`）；JEI、Jade(Waila)、SereneSeasons 为软兼容（`neoforge/.../compat/`）
- 许可证：MIT

## 2. 源码规模与包结构

实测 **.java 633 个 / 58619 行**；模块：common 466、neoforge 114、fabric 53、buildSrc 0（Groovy/Kotlin 约定插件）。

`common/src/main/java/com/dtteam/dynamictrees/`：`api`（13 个子包：cell/configuration/function/lazyvalue/network/registry/resource(+loading/preparation)/season/substance/treedata/voxmap/worldgen）、`block`（branch/fruit/leaves/pod/sapling/soil）、`client`、`command`、`compat`、`config`、`data`、`deserialization`（applier/deserializer/math/result）、`entity`、`event`、`item`、`loot`、`platform`（+services）、`recipe`、`registry`、`systems`（cell/genfeature/growthlogic/nodemapper/poissondisc/season/substance）、`tree`（family/species）、`treepack`（+loader）、`utility`、`worldgen`（feature/featurecancellation/structure）。

最大文件：`tree/species/Species.java` 2602、`tree/family/Family.java` 1023、`block/leaves/DynamicLeavesBlock.java` 809、`block/branch/BranchBlock.java` 782、`block/leaves/LeavesProperties.java` 732、`block/branch/BasicRootsBlock.java` 688、`worldgen/BiomeDatabase.java` 593、`worldgen/JoCode.java` 572、`block/soil/SoilBlock.java` 552、`api/voxmap/SimpleVoxmap.java` 525、`deserialization/result/Result.java` 506、`entity/FallingTreeEntity.java` 496、`api/network/BranchDestructionData.java` 457。

## 3. 入口与注册

`neoforge/src/main/java/com/dtteam/dynamictrees/DynamicTreesNeoForge.java:25`：

```java
@Mod(DynamicTrees.MOD_ID)
public class DynamicTreesNeoForge {
    public DynamicTreesNeoForge(IEventBus eventBus, ModContainer container) {
        eventBus.addListener(this::clientSetup); eventBus.addListener(this::onCommonSetup); eventBus.addListener(this::gatherData);
        container.registerConfig(ModConfig.Type.SERVER, DTConfigs.SERVER_CONFIG); // COMMON / CLIENT 同理
        NeoForgeRegistryHandler.setup(DynamicTrees.MOD_ID, eventBus);
        DynamicTrees.init();                 // common 侧：注册内置季节管理器
        NeoForgeRegistryLoader.setup(eventBus);
        OptionalHandlers.registerHandlers();
        DataGenerators.register();
    }
}
```

平台无关逻辑在 `common/src/main/java/com/dtteam/dynamictrees/DynamicTrees.java`（`init()`、`commonSetup()`、`location(String)`、`runOnCommonSetup(Runnable)` 收集器）；Fabric 对应 `DynamicTreesFabric.java`。

**注册体系（本仓库最大亮点，双层抽象）**：
1. 面向使用方的 `common/.../registry/DTRegistries.java` 全用 `Services.REGISTRY.getRegistryLoader().registerBlock/registerItem/registerEntity/registerFeature/...` 同一套 API 注册方块、物品、实体、方块实体、DataComponent、Loot 类型、Worldgen Feature、结构池元素、配方序列化器（约 40 个注册项）。
2. 加载器实现 `neoforge/.../registry/NeoForgeRegistryLoader.java`（大量 `DeferredRegister`，`BLOCK_ENTITY_TYPES`/`FEATURES`/`DATA_COMPONENT_TYPES`…）与 `NeoForgeRegistryHandler.java`：**用反射拿到 `DeferredRegister#addEntries(RegisterEvent)` 并按 namespace 建独立 DeferredRegister**，从而在运行时把第三方（addon/tree pack）声明的方块物品注册进它们自己的命名空间：

```java
ADD_ENTRIES_METHOD = DeferredRegister.class.getDeclaredMethod("addEntries", RegisterEvent.class);
protected final DeferredRegister<Block> blocksDeferredRegister =
        DeferredRegister.create(BuiltInRegistries.BLOCK, this.getRegistryName().getNamespace());
```

配合 `RegistryHandler.correctRegistryName(...)`：没有注册 handler 的 namespace 会被强制改回 `dynamictrees`。`DynamicTrees.commonSetup()` 里再 `RegistryHandler.REGISTRY.clear()` 释放内存。

## 4. 核心系统

1. **树木生长（SoilBlock + TreeHelper，核心机制）**：`block/soil/SoilBlock.java:208 randomTick(...)` 读配置 `DTConfigs.SERVER.treeGrowthMultiplier`（>1 时 `Math.ceil` 多次尝试），调 `updateTree(state, level, pos, random, natural)`（:224）；`updateTree` 首先 `ChunkTreeHelper.isSurroundedByLoadedChunks(level, soilPos)` 防跨未加载区块生长，再取 `Species` 做环境适配判定。强制生长入口 `tree/TreeHelper.java:46 growPulse(Level, BlockPos)`（生长药水/肥料/树液）→ `dirt.updateTree(...)` + `ageVolume(level, pos, 8, 32, 1, false)`。
2. **Voxmap 体素洪泛（极有学习价值）**：`tree/TreeHelper.java:63 ageVolume(LevelAccessor, SimpleVoxmap, iterations, worldgen)` 用"权威 leafMap + 丢弃式 iterMap"双 map 迭代：只对变化过的体素重算邻居（`iterMap.setVoxel(iPos, 0)` 剪枝、变化时把 `Direction.values()` 邻居值从 leafMap 拷进 iterMap），把 O(N) 全量刷新降为增量刷新；`api/voxmap/SimpleVoxmap.java`（525 行）提供 byte 体素容器（`getAllNonZero()`）。
3. **JoCode（Base64 树木蓝图）**：`worldgen/JoCode.java`（572 行，注释自嘲"因为生成的 base64 几乎都以 JO 开头"），`instructions` 用 `FORK_CODE=6`/`RETURN_CODE=7` 编码分叉与回溯，`CoderNode`/`CollectorNode`/`FindEndsNode`（`systems/nodemapper/` 共 18 种 NodeInspector）以"节点访问者"遍历既有树结构：既能从世界采集树形，也能按码重建树形；`JoCodeResourceLoader` 让 `.joc` 文件可被数据包/附加包替换。
4. **数据驱动加载体系（tree pack）**：`treepack/Resources.java`（+`TreesResourceManager`、`ModFileContainer`、`TreePackResources`）注册 12 种 loader（Leaves/Soil/Family/Species/Fruit/Pod/JoCode/BiomePopulators/FeatureCancellation/GenFeature 与 GrowthLogicKit 的 `ConfigurationTemplateResourceLoader`），把 `trees/` 目录 JSON 映成 `Species`/`Family` 等对象；`ConfigurationTemplate` + `ConfigurationProperty` + `ConfigurationTemplateResourceLoader` 实现"JSON → 配置对象 → 立即实例化"的模板模式。
5. **反序列化框架（`deserialization/`）**：`Result<T,I>`（506 行）把成功/失败/警告统一为可链式对象（`ifSuccess(...)`/错误与警告分离收集），`JsonDeserializers` + 20 余个 `Deserializer` + `applier/JsonPropertyApplier`（`MultiPropertyApplier`/`MapPropertyApplier`/`IfTrueApplier` 等）做属性装配；`JsonPropertyApplierLists` 收敛可应用属性字典，配置错误不会抛栈而能聚合报告。
6. **生长逻辑与外延系统可插拔**：`systems/growthlogic/`（`GrowthLogicKit` + `GrowthLogicKits` 注册 DARK_OAK/CONIFER/JUNGLE/AZALEA/NETHER_FUNGUS/PALM/MANGROVE_ROOTS，另有 `DirectionSelectionContext`/`DirectionManipulationContext` 上下文）；`systems/genfeature/` 25 种 `GenFeature`（VinesGenFeature、RootsGenFeature、HugeMushroomGenFeature…）用 `GenFeatureContext`（PreGeneration/PostGrow/PostRot/PostGeneration/FullGeneration）区分生成时机。
7. **世界生成接管**：`worldgen/feature/DynamicTreeFeature.java` + `worldgen/featurecancellation/`（`TreeFeatureCanceller`/`FungusFeatureCanceller`/`MushroomFeatureCanceller`）+ `worldgen/structure/`（`DTCancelVanillaTreePoolElement` 取消村庄原版树池、`TreePoolElement` 用 DynamicTrees 树替换），经 BiomeModifier 注入（`NeoForgeRegistryLoader` 的 `ADD_DYNAMIC_TREES_BIOME_MODIFIER`/`RUN_FEATURE_CANCELLERS_BIOME_MODIFIER`）；`worldgen/BiomeDatabase.java`/`JoCodeRegistry` 存每生物群系的树形码。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：本分支**未发现自定义 payload/通道注册**（全仓库 grep `CustomPacketPayload|registerPayload|PayloadRegistrar|NetworkRegistry` 无命中），仅有 `api/network/` 下的数据结构（`BranchDestructionData`/`BranchConnectionData`/`RootConnections`/`NodeInspector`/`MapSignal`）用于服务端内部与方块破坏链路；完全未确认是否存在其它同步机制。
- 配置：`common/.../config/DTConfigs.java` 用 NeoForge `ModConfigSpec` 三分（SERVER/COMMON/CLIENT），Fabric 经 ForgeConfigApiPort 复用同一 spec；服务端项含 `treeGrowthMultiplier`、`leavesSeedDropRate`、`seasonalSeedDropChance` 等。
- 数据驱动：`trees/`（species/family/leaves_properties/soil_properties/fruit/pod/jo_codes/biome_populators）、`gen_features/configurations`、`growth_logic_kits/configurations` 等 JSON 资源包；`ModTreeResourcePack`/`ModFileContainer` 让**其它 mod 的 jar 充当树包**（数据驱动 + 跨 mod 资源注入）。
- datagen：完整（neoforge 侧 `data/` 目录）：`DataGenerators`/`GatherDataHelper`，19 个 `DataGenerator`（BranchStateGenerator、LeavesStateGenerator、RootsStateGenerator、PalmLeavesStateGenerator、各种 ItemModel/Lang Generator）由注册表条目驱动批量产出 blockstate/model/lang；`provider/` 下有 BlockTags/ItemTags/Loot/Recipe/DatapackBuiltinEntries/SpriteSource 等 Provider。

## 6. Mixin

三份配置：`common/src/main/resources/dynamictrees.mixins.json`（`mixins: []`，只留 refmap 占位，`compatibilityLevel=JAVA_18`）、`neoforge/src/main/resources/dynamictrees.neoforge.mixins.json`（JAVA_21，仅 `MixinBushBlock`）、`fabric/src/main/resources/dynamictrees.fabric.mixins.json`（JAVA_21，7 个：`MixinBushBlock`、`MixinSaplingBlock`、`MixinChunkSerializer`、`MixinMinecraftServer`、`MixinBrewingStandBlockEntity`、`MixinBrewingStandMenu`、`MixinPotionBrewing`）。mods.toml 用两条 `[[mixins]] config=` 同时加载主配置与加载器专有配置。`MixinBushBlock`/`MixinSaplingBlock` 用于把原版灌木/树苗行为重定向到 DynamicTrees；`MixinChunkSerializer` 处理区块存读时的树数据；`MixinPotionBrewing` 系列做药水（Dendro Potion）扩展。具体注入点（method/at）本次未逐行确认。

## 7. 值得学的 5 条具体做法

1. **"common 定义注册 API + 加载器实现 RegistryLoader"**：`registry/DTRegistries.java` 里 40 个注册项只写一次，Fabric/NeoForge 各实现一份 `RegisterXxx`；1.21.1 双语种 mod（NeoForge+Fabric）可直接照搬，见 `common/.../registry/RegistryLoader.java`（18 个 abstract 方法）。
2. **反射调 `DeferredRegister#addEntries` 实现"给别人的命名空间注册"**：`neoforge/.../registry/NeoForgeRegistryHandler.java:36-48`，让 addon 的方块物品注册进 addon 自己的 modid（配合 `RegistryHandler.correctRegistryName` 兜底）；注意这是内部 API，跨版本易碎，慎用于非必需场景。
3. **Voxmap 增量洪泛替代全量扫描**：`tree/TreeHelper.java:63` 的双 map + 变化点扩散，任何"体素/方块体积联动更新"（树叶衰减、光照数据、流体）都能套用。
4. **字符串蓝图（JoCode）作为树的存档格式**：`worldgen/JoCode.java` + `JoCodeResourceLoader` 把树形外置为可分享、可数据包覆盖的 base64 字符串，并把"采集/重建"写成同一套 NodeInspector 访问者；适用于任何"结构/形状需要跨存档搬运"的系统。
5. **数据驱动三层（ResourceLoader → Deserializer/Applier → Template）**：`treepack/loader/*` + `deserialization/` + `api/configuration/`，错误用 `Result<T,I>` 收集而不是抛异常，做大型数据包驱动 mod 时可直接参考其"JSON 属性字典 + 模板实例化"分工。

## 8. 公开 API / 扩展点（前置型 mod，DynamicTreesPlus 等依赖它）

- API 包：`com.dtteam.dynamictrees.api.*`（13 个子包），核心扩展点：`api/registry/`（`Registry`/`RegistryEntry`/`Registries`/`RegistryHandler`）、`api/resource/`（`TreeResourceManager`、`TreeResourcePack`、`ResourceLoader`、`StagedApplierResourceLoader`）、`api/configuration/`（`Configurable`/`ConfigurationTemplate`/`PropertyDefinition`）、`api/season/`（`SeasonProvider`/`SeasonManager`/`SeasonGrowthCalculator`）、`api/cell/`（`Cell`/`CellKit`/`CellSolver` 树形细胞自动机）、`api/voxmap/`、`api/network/`、`api/substance/`、`api/worldgen/`（`PoissonDiscProvider`、`GroundFinder`、`FeatureCanceller`、`LevelContext`）。
- 接入方式一（Fabric 官方入口）：实现 `com.dtteam.dynamictrees.api.DynamicTreesAddonEntrypoint`（`onDynamicTreesPreSetup()`、`onAddResourceLoaders(TreeResourceManager)`、`onRegisterStagedApplier(Stage, PropertyAppliers, String)`），通过 Fabric entrypoint 声明 `fabric/src/main/java/com/dtteam/dynamictrees/api/DynamicTreesAddonEntrypoint.java`。
- 接入方式二（纯数据包/树包）：往 jar 内放 `trees/` 资源目录即可被 `ModFileContainer` 识别为树包，无需写 Java（`treepack/Resources.java` + `ModTreeResourcePack`）。
- 平台服务定位器：`platform/Services.java` + `platform/services/I*.java`（`IRegistryHelper`/`IConfigHelper`/`ICompatHelper`/`IEventHelper`/`IInteractionHelper`/`IMiscHelper`/`IClientHelper`）是 common↔加载器的唯一桥，第三方要接加载器特有功能也走这里。
