# Create: Cosmonautics 源码分析报告

## 1. 基本信息

- Mod 名：Create: Cosmonautics / `mod_id=rocketnautics` / 版本 1.4.0.rc1；**同一个 jar 内还打包了第二个 mod `dimensional_sable`（version 1.0.5，"Dimensional Support for Sable"）**，见 `src/main/resources/META-INF/neoforge.mods.toml:11-23`。
- 作者：webyep-art, M_W_K；许可证 **GNU GPL v3**。
- 目标：MC 1.21.1 + NeoForge `[21.1.1,)`。
- Gradle 插件：`net.neoforged.moddev 2.0.141` + `com.gradleup.shadow 9.4.3`（`build.gradle:1-4`），自定义 `shade` 配置与 `jarExtraction`。
- 编译依赖（`build.gradle:146-188`）：Create `6.0.11-300`（implementation, transitive=false）、Ponder、Flywheel API+impl、Registrate（`jarJar(api(...))`）、**Sable `2.0.3`（compileOnly）+ sable-companion（implementation）——子世界/物理引擎前置**、**offroad / simulated / aeronautics 各 1.2.1（Create Aeronautics 生态）**、Veil `4.1.1`、Jade、CC:Tweaked、JEI、Iris（compileOnly）；`compileOnly fileTree(buildDir/extracted-jars)` 解包取 API。

## 2. 源码规模与包结构

369 个 `.java`，52732 行。

主要包：`content/blocks` 77、`mixin` 33、`client` 26、`content/orbit` 24、`network` 22、`client/render` 22、`registry` 16、`content/sputnik` 13、`data/worldgen` 11、`content/world` 9、`api/orbit` 9、`dev/ryanhcode/sable/api/physics` 8（对 Sable 物理 API 的镜像/适配）、`ponder/scenes` 8、`data/recipe` 8、`content/physics` 6、`compat/computercraft` 6、`api/peripherals` 3、`api/radio` 2。

最大文件：`client/SkyHandler.java` **2586**、`client/ui/imgui/SputnikNodeGraphPanel.java` 1595、`client/DeepSpaceHandler.java` 1171、`content/commands/CosmonauticsCommand.java` 1026、`client/RocketSettingsScreen.java` 987、`MFDCartridgeEditorScreen.java` 734、`registry/RocketBlocks.java` 722、`sputnik/node/SputnikNodeRegistry.java` 719、`RocketNauticsClient.java` 701、`SputnikBlockEntity.java` 698。

## 3. 入口与注册

主类 `src/main/java/dev/devce/rocketnautics/RocketNautics.java:44`。注册走 **Registrate（经 Simulated 二次封装）**，17 个注册类集中在 `registry/`：

```java
private static final NonNullSupplier<RocketRegistrate> REGISTRATE = NonNullSupplier.lazy(() ->
        (RocketRegistrate) new RocketRegistrate(path(MODID), MODID).defaultCreativeTab((ResourceKey<CreativeModeTab>) null));
```

构造器（:58-120）：注册 SERVER/CLIENT 配置 → 世界生成注册（`RocketDensityFunctions / SurfaceRules / FloatProviders / WorldCarvers / Features`）→ `RocketDatagen::gatherData` → Registrate 各注册（Items/Blocks/Tabs/BlockEntities/Particles/Sounds/DataComponents）→ **手动 `modEventBus.register(NetworkHandler.class)`（规避 deprecated bus() 参数）** → 客户端分支（Flywheel 兼容、`SableSkyLightShadows.setIsEnabled(true)`、Veil `onVeilAddShaderProcessors` / `onVeilRenderLevelStage`）→ `GlobalSpacePhysicsHandler.init()` / `AsteroidSpawner.init()` / `SpaceTransitionHandler.init()`。
`RocketRegistrate`（`registry/RocketRegistrate.java`）重写 `accept()`，把物品从父级（Simulated/Aeronautics）创造标签里"抢"回来（`ITEM_TO_SECTION.remove(res.getId())`），并在 `onData` 用自写 `LimitedRegistrateDataProvider` 并 `disableProvider(ProviderType.LANG)`。

## 4. 核心系统

**4.1 宇宙/行星数据驱动加载**（`content/orbit/universe/`）
`UniverseLoader` 继承 `SimpleJsonResourceReloadListener`（GSON，目录 `universe_planets`），`INSTANCE` 单例并注册进 `AddReloadListenerEvent`（`RocketNautics.java:160`）。两阶段加载：阶段一按名字收集 `PlanetDefinitionBuilder` 并按 `priority` 排序，同优先级用 `subsume(read)` 合并（**包 zip 覆盖式数据包**）；阶段二坍缩成依赖树，维护 `dependents / unsatisfiedDependencies / disabled` 集合，循环依赖/失败依赖会被标记禁用。加载失败时回退 `FALLBACK = StandardUniverseProvider.createSolarSystem()`（内置太阳系）。builder 目录提供 `PlanetDefinitionBuilder / UniverseDefinitionBuilder / Serializable*`（全部 record，DFU codec）。

**4.2 6DOF 自由运动与太空物理**（`content/physics/`、`api/FreeMotionEntity.java`）
`FreeMotionEntity` 是公开接口：`is6DOFEnabled/set6DOFEnabled`、`isAmbulant`、`getOrientation/setOrientation(Quaternionf)`、`getMovementAcceleration`、`getDampenerForce`——外部 mod 的生物/载具实现它即获得太空运动能力。物理侧 `GlobalSpacePhysicsHandler` + `content/blocks/RocketThrusterActorBehaviour`（把推力接进 Create 的 contraption actor 体系），`MergedMassTracker` 用于合并质量/惯性。

**4.3 Sputnik 可视化逻辑节点系统**（`content/sputnik/`）
`node/SputnikNodeRegistry.java` 用静态 `LinkedHashMap` 注册 `INodeHandler` 并分 `BY_CATEGORY`，内置常量/数学/逻辑/传感器（高度、速度、姿态）/显示/引擎（点火、推力、矢量）/陀螺仪控制等节点；执行上下文是 `NodeExecutionContext`。UI 是 **imgui**（`client/ui/imgui/SputnikNodeGraphPanel.java` 1595 行）——在 MC 里嵌即时模式 GUI，资源同步用 `SputnikNodeSyncPayload`。

**4.4 火箭方块组 + MFD**（`content/blocks/` 77 文件）
抽象 `AbstractRocketThrusterBlock(Entity)` + `ThrustBehaviour` + `IThruster`，派生 Rocket/Booster/RCS/Vector/Creative 五种推进器（各自 BlockEntity + Renderer）；配套 `EngineNozzle / EnginePipes / ThrusterMount / drain_valve / energy_tank / gyrodyne / hose / Separator*`。MFD（多功能显示器）方块 + 弹夹式卡带编辑器 `MFDCartridgeEditorScreen`（734 行）。

**4.5 客户端太空渲染**：`client/SkyHandler.java`（2586 行，最大文件）、`client/DeepSpaceHandler.java`（1171 行，深空位置/过渡）、`client/render/spaceRenderer/`、`client/render/shadow/DirectionalShadowRenderer`（自建方向光阴影贴图渲染阶段）。自定义 `SunDirectionalShadingPreProcessor` 经 Veil 注册为 shader 预处理器。

**4.6 外设/无线电 API**：`api/peripherals/{IPeripheral, PeripheralRegistry, EngineIdManager}` + `compat/computercraft/ComputerCraftCompat`（仅在 `ModList.isLoaded("computercraft")` 时初始化）；`api/radio/{RadioNetworkManager, VirtualRadioNode}`（服务器级无线电网，`setServer` 于 ServerStarting 注入）；`server/telemetry/TelemetryServer` 遥测。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：21 个 payload 类于 `network/`，`NetworkHandler.register` 用 NeoForge 原生 `PayloadRegistrar registrar = event.registrar(MODID).versioned("1.0")`，逐条 `playToClient/playToServer` + `context.enqueueWork(...)`。含 `FreeMotion*`（运动状态 C2S/S2C）、`JetpackTogglePayload / DampenersTogglePayload`（按键开关）、`UniverseDefinitionPayload / UniverseTimeSyncPayload`（宇宙数据同步）、`DeepSpacePositionPayload / PlanetMapPayload / PlanetRenderPayload`、`PlayAudioPayload`、`ReentryHeatPayload / SolarBurnPayload`、`SeamlessTransitionPayload`。
- 配置：`RocketConfig` 用 `Pair<Server, ModConfigSpec>` 双 spec（SERVER_SPEC/CLIENT_SPEC），于主类构造器 `modContainer.registerConfig`。
- datagen：`data/RocketDatagen.java` —— Registrate 的 `ProviderType.BLOCK_TAGS / FLUID_TAGS`，Create 风格配方生成器 8 个（Crushing/Milling/Mixing/Pressing/Washing/ItemApplication/MechanicalCrafting/Standard），并用 `RegistrySetBuilder` + `event.createDatapackRegistryObjects` 一次性生成 DIMENSION_TYPE / LEVEL_STEM / BIOME / BIOME_MODIFIERS / PLACED_FEATURE / CONFIGURED_FEATURE / NOISE_SETTINGS / NOISE / DENSITY_FUNCTION / CONFIGURED_CARVER；`RocketUniverseProvider` 生成宇宙 JSON。

## 6. Mixin

两个配置：`src/main/resources/rocketnautics.mixins.json`（`package=dev.devce.rocketnautics.mixin`，`plugin=RocketMixinPlugin`，23 common + 9 client）与 `dimensional_sable.mixins.json`（`package=dev.egg.mixin`，仅 `LevelPlotAccessor` / `ServerLevelPlotAccessor`）。

- 插件门控：`mixin/RocketMixinPlugin.java:24-28` 仅对 `compat.C2MEDensityFunctionFixer` 检查 `FMLLoader.getLoadingModList().getModFileById("c2me") != null`。
- 代表性 hook：**Sable/Rapier 物理**——`RapierGenericConstraintHandleMixin / RapierRotaryConstraintHandleMixin / RapierFixedConstraintHandleMixin / RapierFreeConstraintHandleMixin / PhysicsPipelineMixin`（改约束求解）、`SubLevelPhysicsSystemMixin`、`MergedMassTrackerMixin`；**子世界**——`SubLevelWarperMixin`、`HoldingSubLevelMixin` + `SubLevelHoldingChunkMapAccessor`；**Create 集成**——`BacktankUtilMixin`、`DivingHelmetItemMixin`、`FluidTankBlockEntityMixin`；**原版**——`EntityMixin`、`LivingEntityMixin`、`RemainingAirOverlayMixin`（真空呼吸/氧气）、`LevelTimeAccessMixin`、client 侧 `LevelRendererMixin / CameraMixin / MinecraftMixin / MouseHandlerMixin / PlayerModelMixin / PlayerRendererMixin`（6DOF 视角与姿态）。

## 7. 值得学的 5 条具体做法

1. **数据包式宇宙定义 + priority/subsume 覆盖**：`content/orbit/universe/UniverseLoader.java:48-72`，第三方数据包可只写差分字段覆盖内置行星，且用 `Lazy` 内置回退——做"数据驱动内容 + 内置默认值"的通用范式。
2. **一个 jar 出两个 mod、两套 mixin 配置**：`neoforge.mods.toml:6-23`，把强耦合的引擎适配层（dimensional_sable）拆成独立 modId 便于被其它 mod 单独依赖。
3. **公开 `FreeMotionEntity` 接口做能力注入**：`api/FreeMotionEntity.java`，任何实体实现 6 个方法即可接入太空运动，是标准的"接口型扩展点"写法。
4. **自定义 Registrate 子类改写 `accept()`**：`registry/RocketRegistrate.java`，用于把物品强制移出父/前置 mod 的创造标签分组——写依赖 Aeronautics/Simulated 那类框架的附属时直接可复用。
5. **自建方向光阴影渲染阶段 + Veil shader 预处理器**：`RocketNautics.java:100-107`，展示了在 Create 生态里做自定义渲染管线的正确注册时机（必须在 mod 构造期注册）。

注：`api/orbit`（`FrameTree / PaletteAccess / CompoundPaletteAccess / ColorFlags / AtmosphereFlags / AllowedTransfer`）与 `api/packager` 式的对外扩展点已存在，但本仓库未见独立发布 API 制品，接入方式为直接依赖 `rocketnautics`。
