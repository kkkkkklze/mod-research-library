# Creators-of-Aeronautics/Simulated-Project 源码分析报告

## 1. 基本信息

- 一体化多 mod 仓库（Create 航空学系列）：`aeronautics` = Create Aeronautics（`dev.eriksonn.aeronautics`）、`simulated` = Create Simulated（`dev.simulated_team.simulated`，物理核心）、`offroad` = Create Offroad（`dev.ryanhcode.offroad`）；`aeronautics-bundled` 是打包壳，其 `neoforge.mods.toml:1` 用 `modLoader = "lowcodefml"` 做 jar-in-jar 合并分发（依赖声明为空，仅 neoforge + minecraft）
- 目标版本：`gradle.properties` → `minecraft_version=1.21.1`、`neoforge_version=21.1.247`、`java_version=21`、Parchment `2024.11.10`；**仅 NeoForge**（`settings.gradle.kts` 只有 `*:neoforge` 子项目，无 fabric 模块，但构建脚本预留了 "Unify the run config names with fabric" 注释）
- Gradle 插件：`net.neoforged.moddev 2.0.140`（`build.gradle:3`）+ 自研 `buildSrc` 里的 `multiloader-loader` 约定插件
- 许可证：混合——`assets/` 目录 ARR（All Rights Reserved），其余代码 MIT（`LICENSE.md:1-24`）
- 编译依赖（`gradle.properties`）：Create `6.0.10-280`、Ponder `1.0.81`、Flywheel `1.0.6`、Registrate `MC1.21-1.3.0+67`、**Veil `4.3.2`（foundry.veil）**、**Sable `2.0.4-37` + sable_companion `1.6.0`（`dev.ryanhcode.sable`，物理引擎，是本项目真正的 API 前置）**；可选/集成：JEI、CC:Tweaked、Curios、Natures/Explorers Compass、Sodium/Iris
- 私有 maven 源 `maven.ryanhcode.dev/releases|snapshots|private`（`build.gradle:47-60`）

## 2. 源码规模与包结构

实测：**905 个 `.java`，90158 行**（`find -name '*.java' | xargs wc -l` 求和）。分模块：`simulated` 634 文件、`aeronautics` 202、`offroad` 69。

包结构（第 3 层文件数）：`dev/simulated_team/simulated/content` 247、`dev/eriksonn/aeronautics/content` 97、`simulated/mixin` 86、`simulated/ponder` 48、`simulated/network` 39、`simulated/index` 35、`simulated/neoforge` 31、`aeronautics/mixin` 29、`simulated/util` 25、`simulated/compat` 25、`aeronautics/index` 24、`offroad/content` 23、`simulated/multiloader` 16、`simulated/mixin_interface` 16、`simulated/data` 15、`simulated/service` 14、`simulated/config` 10、`simulated/api` 10。

最大的 5 个文件：`simulated/.../ponder/scenes/SensorScenes.java` 1464、`KineticScenes.java` 1284、`content/entities/diagram/screen/DiagramScreen.java` 1077、`RedstoneScenes.java` 1052、`aeronautics/.../ponder/scenes/PropellerScenes.java` 958；`index/SimBlocks.java` 939、`content/blocks/swivel_bearing/SwivelBearingBlockEntity.java` 921。

注意 `content/blocks/` 下每个方块一个子包（redstone 33 文件、rope 19、lasers 12、auger_shaft 10、docking_connector 9…），`aeronautics/content/blocks` 只有 4 个子包（hot_air / levitite / mounted_potato_cannon / propeller），但 hot_air 内部自成一个"气球图"子系统。

## 3. 入口与注册

**没有单一主类**：`common` 里的 `Simulated.java` / `Aeronautics.java` 只提供 `init()` + MOD_ID + 共享 Registrate，真正入口在 neoforge 侧 `@Mod` 类（6 个：每 mod 一个主类 + 一个 `dist = Dist.CLIENT` 客户端类）。

```java
// simulated/neoforge/.../SimulatedNeoForge.java:24-54
@Mod(Simulated.MOD_ID)
public final class SimulatedNeoForge {
  public SimulatedNeoForge(IEventBus modEventBus, ModContainer modContainer) {
    DeferredRegister<CreativeModeTab> tabRegister = DeferredRegister.create(BuiltInRegistries.CREATIVE_MODE_TAB, Simulated.MOD_ID);
    tabRegister.register("main_tab", () -> TAB); tabRegister.register(modEventBus);
    NeoForge.EVENT_BUS.register(SimNeoForgeCommonEvents.class);
    modEventBus.register(SimNeoForgeCommonEvents.ModBusEvents.class);
    SimParticleTypesImpl.register(modEventBus); SimNeoForgeRecipeTypes.register(modEventBus);
    Simulated.getRegistrate().registerEventListeners(modEventBus);
    if (ModList.get().isLoaded("computercraft")) modEventBus.register(NeoForgeSimPeripheralService.class);
    Simulated.init();
  }
}
```

- 注册框架：**Registrate**（`SimulatedRegistrate extends CreateRegistrate`，`simulated/.../registrate/SimulatedRegistrate.java:29`）。它魔改了 Create 的创意标签体系：静态共享 `MODS` / `TAB_ITEMS` / `ITEM_TO_SECTION`（第 30-32 行），配合 `inSection(ResourceLocation)` 把三个 mod 的物品塞进同一套分组标签，并用静态集合跨 mod 边界交换注册数据（`AeroRegistrate extends SimulatedRegistrate` 复用该逻辑）。
- 全部内容注册集中在一个 `init()` 序列里（`Simulated.java:33-60`）：`SimRegistries → SimTags → SimBlocks → SimItems → SimBlockEntityTypes → SimParticleTypes → SimSoundEvents → SimSpriteShifts → SimPacketManager → SimEntityTypes → SimMenuTypes → SimNavigationTargets → SimDataComponents`，顺序显式可见，便于排错。
- 少量必须延迟的注册（粒子 provider、配方类型、Stats、DataComponent 序列化器）走 NeoForge `DeferredRegister`（`SimParticleTypesImpl.register` 等）。
- 自定义数据驱动注册表用 **Veil 的 `RegistrationProvider`**：`simulated/.../index/SimRegistries.java:15-27` 定义 `navigation_target` 与 `property_tooltip` 两个 `Registry`，`provider.asVanillaRegistry()` 拿到裸 Registry 供 datapack 加载。

## 4. 核心系统

1. **物理体（SubLevel）接入**：全仓 167 个文件 import `dev.ryanhcode.sable.*`。核心类是外部库的 `sublevel.SubLevel` / `api.sublevel.SubLevelContainer` / `api.SubLevelHelper` / `api.block.BlockEntitySubLevelActor`，本项目只做适配：`SableEventPlatform.INSTANCE.onPhysicsTick(...)` / `onPostPhysicsTick(...)` / `onSubLevelContainerReady(...)`（`Simulated.java:58-59`、`Aeronautics.java:63-65`）。**学点：把物理引擎当第三方 API，本项目不实现物理，只注册 tick 回调 + Actor**。
2. **多加载器平台抽象（SPI）**：`simulated/common/.../service/` 下 14 个接口，统一模式是接口内自持单例：
   ```java
   public interface SimAssemblyService { SimAssemblyService INSTANCE = ServiceUtil.load(SimAssemblyService.class);
       boolean canStickTo(BlockState a, BlockState b); }
   ```
   （`service/SimAssemblyService.java`、`ServiceUtil.java:7-9` 用 `ServiceLoader` + `findFirst().orElseThrow`）；NeoForge 实现在 `simulated/neoforge/.../service/NeoForgeSim*Service.java`。**注意：本快照中未找到 `META-INF/services/*` 文件，注册方式未确认**。
3. **Create 动力系统改造（extra_kinetics）**：`mixin/extra_kinetics/` 一整套 mixin 改 Create 的 `RotationPropagator`、`KineticNetwork`、`GeneratingKineticBlockEntity`、`EncasedCogwheelBlock`，另有 `dynamic_stress.KineticStatsMixin`、`flicker_tally_removal.RotationPropagatorMixin`、`extra_kinetics.auto_orientation.FixAutoOrientation*`。学点：**通过 mixin 给第三方 mod 的动能网络加"动力学必须跨 SubLevel 传递"的新规则**，而不是替换系统。
4. **Ponder 教学场景**：`simulated/ponder/scenes/` + `aeronautics/.../content/ponder/scenes/`，单个场景文件上千行；注册入口 `index/SimPonderScenes.java` / `SimPonderTags.java`；配套 3 个 ponder mixin（`PonderSceneMixin` / `PonderSceneTransformMixin` / `WorldSectionElementImplMixin`）让 Ponder 场景支持物理变换与子世界渲染。
5. **蓝图式"机构图"（Diagram）**：`content/entities/diagram/` 11 文件 + `DiagramScreen.java` 1077 行，配套 4 个网络包（`RequestDiagramData` / `DiagramData` / `DiagramSaveConfig` / `DiagramOpen`），是"服务端算数据、客户端渲染大 UI"的完整范例（含分页数据请求）。
6. **Aeronautics 气球/热气球图**：`content/blocks/hot_air/balloon/` 自成一套（`BalloonLayerGraph` 图结构 + `BalloonLevelSavedData` 存档数据 + `ClientBalloon`/`ServerBalloon` 分侧 + `HeatedCulledRenderRegion` 自定义渲染剔除区域）；升力气体做成**数据驱动注册表** `AeroRegistries.Keys.LIFTING_GAS_TYPE`（`aeronautics/.../content/blocks/hot_air/lifting_gas/LiftingGasType.java`，`AeroRegistrate.liftingGasType()` 提供注册糖）。
7. **levitite 结晶协议（公开 API 范例）**：`aeronautics/.../api/levitite_blend_crystallization/` 7 个文件，含 `CrystalPropagationContext`、`LevititeCrystallizerManager`、`CrystallizationWorldSaveData`、`LevititeBlendTicker` —— 一个"可被其它 mod 扩展的结晶扩散"完整 API 包（含传播上下文接口与存档数据）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：不用原版 `SimpleChannel`，用 **Veil 的 `VeilPacketManager`**：`SimPacketManager.java:26` `VeilPacketManager.create(MOD_ID, "0.1")`（带协议版本号），每组包一个 `TYPE` + `CODEC`（Mojang Codec）+ `handle` 静态方法引用，分 `registerServerbound` / `registerClientbound` 注册（39 个包，见 `network/packets/`）。序列化统一走 Codec，便于复用。
- **数据驱动**：自定义 Registry（`SimRegistries` 2 个 + `AeroRegistries` 多个）、`SimResourceManagers`、`SimWorldPresets`（配套 `world_presets.CreateWorldScreenMixin` / `PrimaryLevelDataMixin` 把超平坦/世界预设注入创建界面）、`SimTags`。
- **配置**：`simulated/config/{client,server}`、`aeronautics/config/{client,server}`（`AeroPhysics` / `AeroStress` / `AeroKinetics` / `AeroBlockConfigs` 分类），通过 `SimConfigService` / `NeoForgeSimConfigService.register(ModLoadingContext, ModContainer)` 接入（`SimulatedNeoForge.java:53`）。
- **datagen**：有，走 Registrate 的 `addDataGenerator(ProviderType.LANG, SimLang::registrateLang)`（`Simulated.java:36`）+ 手写 `data/SimBlockStateGen.java`；neoforge 的 `data` run 配置显式 `--existing-mod create` 复用 Create 的生成资源（`simulated/neoforge/build.gradle:37-44`）。

## 6. Mixin

- 6 份配置：`simulated/common/src/main/resources/simulated.mixins.json`、`simulated/neoforge/.../simulated-neoforge.mixins.json`、`aeronautics.mixins.json` + `aeronautics.neoforge.mixins.json`、`offroad.mixins.json` + `offroad.neoforge.mixins.json`；`JAVA_21`、`required: true`、`injectors.defaultRequire: 1`、含 refmap。
- 组织方式值得抄：按**功能目录**分包（`accessor/`、`extra_kinetics/`、`ponder/`、`rope/`、`world_presets/`、`creative_tab_sections/`），client 与通用混入在 json 里显式分组（`simulated.mixins.json:7-50` 是 client，`51-96` 是通用，共 84 个 mixin）。
- 代表类与注入目标：`extra_kinetics.RotationPropagatorMixin` → Create `RotationPropagator`（动能传播）；`create_assembly.MechanicalBearingBlockEntityMixin` / `ClockworkBearingBlockEntityMixin` / `ElevatorPulleyBlockEntityMixin` / `LinearActuatorBlockEntityMixin` → Create 四个组装器方块实体（把原版 Create 组装改成物理 SubLevel 组装）；`torsion_spring.MechanicalBearingBlockEntityMixin`、`schematicannon_fix.SchematicPrinterMixin`、`aabb.AABBMixin`、一堆 `accessor.*`（`@Accessor` 取私有字段）。
- `mixin_interface/` 16 个文件是配套的 `interface` + 默认方法（`PlayerTypewriterExtension`、`SpriteContentsExtension`、`PrimaryLevelDataExtension` 等），mixin 里 `implements` 它们以便其他代码安全调用——**这是给 mixin 加"类型安全扩展面"的好模式**。

## 7. 值得学的 5 条具体做法

1. **把重型引擎（物理 Sable、网络 Veil、UI Flywheel、注册 Registrate）全部当外部 API，本项目只写适配层**：见 `gradle.properties` 依赖清单 + `Simulated.java` 只做 init 编排。
2. **单个 `init()` 显式串起全部注册调用**（`Simulated.java:33-60`），优于散落的静态初始化块；注册顺序即依赖顺序。
3. **mixin 必配 `mixin_interface` 接口**：`mixin_interface/` + `mixin/accessor/` 成对出现，把"类型转换"变成"接口实现"，避免 `(SomeAccessor)(Object)` 到处强转。
4. **自研注册服务 SPI 做多加载器解耦**：接口自持 `INSTANCE = ServiceUtil.load(...)`，common 代码零加载器引用（`service/Sim*Service.java`，14 个接口）。适合任何要长期双端维护的库。
5. **自定义数据驱动注册表用 `RegistrationProvider.asVanillaRegistry()`**（`SimRegistries.java:15-27`），配合 Registrate 的 `byNameCodecExpanded`（`SimulatedRegistrate.java:47+`，按名字从自己的注册集合解析 ID）——给 datapack 作者提供"写 JSON 就能加内容"的扩展点。

## 8. 公开 API / 扩展点

- **本项目不是库模组**，但 `simulated/api/`（10 文件：`BearingSlowdownController`、`ConditionalDisplayTarget`、`CustomStressImpactTooltipProvider`、`IDirectionalAnalogOutput`、`SimpleResourceManager`、`sound/`）与 `aeronautics/api/`（8 文件：`CustomSituationalMusic`、`levitite_blend_crystallization/*`）是明确的对外 API 包，风格是"接口 + Manager + SavedData"三件套。
- 上游前置才是真正的 API：**Sable（`dev.ryanhcode.sable`，物理 SubLevel）**、**Veil（`foundry.veil`，网络/注册/渲染平台）**、Create + Ponder + Flywheel + Registrate。做 Create 物理附属时应先摸清 `SubLevel` / `SubLevelContainer` / `SableEventPlatform` / `BlockEntitySubLevelActor` 四个入口。
