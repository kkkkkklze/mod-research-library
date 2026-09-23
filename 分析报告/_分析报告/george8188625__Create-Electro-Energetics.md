# Create Electro Energetics 源码分析报告

## 1. 基本信息

- Mod 名：Create Electro Energetics；mod_id `electroenergetics`；作者 George VI；许可证 MIT；版本 `1.21.1-1.2.0`（`gradle.properties:11-15`）
- 目标：Minecraft `1.21.1` / NeoForge `21.1.228`（range `[21.1.174,)`），Java 21，Parchment `2024.11.17`
- Gradle 插件：`net.neoforged.moddev 2.0.89` + `java-library` + `maven-publish`（`build.gradle:1-6`）；`neoforge.mods.toml` 由 Groovy `expand` 从 `src/main/templates/` 生成，并在其中以 `[[mixins]] config="${mod_id}.mixins.json"` 声明 mixin
- 编译依赖：Create `6.0.10-280:slim`(transitive=false)、Ponder `1.0.82`、Flywheel `1.0.6`(api compileOnly)、Registrate `MC1.21-1.3.0+67`、JEI `19.53.0.425`(compileOnly api)；**生态强绑定：Sable 2.0.3、Aeronautics、Simulated、Offroad（物理/载具系）+ `jarJar(api(sable-companion-common))`**（`build.gradle:104-131`）；CC:Tweaked `1.116.1`（implementation）、Supplementaries/Selene（compileOnly）、Create Addition（runtimeOnly）

## 2. 源码规模与包结构

**513 个 `.java`、56,386 行**（`find`+`cat` 实测，全仓库最大的一批 Create 附属之一）。按顶层包统计（文件/行）：

- `content` **295 / 31,320**（36 个子包：connector、wire(+attachments/interaction)、pole、transformer、current_transformer、hv_capacitor、sf6_breaker、variac、resistor/inductor/capacitor/diode、fuse(+fuse_held)、energy_meter、frequency_meter、clamp_meter、synchroscope、gauge、bulb/indicator_bulb、electric_motor/pump/fan、rotor、accumulator、converter、creative_battery、potentiometer、relay、redstone_relay、cut_off_switch、ground_rod、linemans_stick、bundled_wire、voxel_wire、sign、electrical_panel(+attachments/link/special_interaction)、railway_electrification(catenary/pantograph/third_rail/gauges/sound_effects)）
- `simulation` 60 / 7,388；`foundation` 43 / 3,184；`ponder` 12 / 3,565；`client` 11 / 2,158；`mixins` 21 / 1,820；`events` 14 / 2,016；`config` 9 / 288；`devices` 7 / 421；`compat` 8（computercraft/strut_your_stuff）；`mixin_interfaces` 3 / 76；根目录 **29 个 `CEE*` 注册/定义类**
- 最大文件：`simulation/infrastructure/InfrastructureSavedData.java`(1131)、`CEEBlocks.java`(1031)、`events/datagen/CEERecipeGen.java`(806)、`ponder/ElectricityBasicsScenes.java`(771)、`TransformerScenes.java`(638)、`client/WireRenderer.java`(607)、`WireSimulationState.java`(463)、`switch/SwitchScenes.java`(436)、`NetworkOptimizer.java`(414)、`PantographMovementBehaviour.java`(394)、`Network.java`(385)、`foundation/nodes/InWorldNode.java`(381)

## 3. 入口与注册

主类 `CreateElectroEnergetics.java:23-70`：

```java
REGISTRATE = CreateRegistrate.create(ID).setTooltipModifierFactory(item ->
        new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)
                .andThen(TooltipModifier.mapNull(KineticStats.create(item)))
                .andThen(TooltipModifier.mapNull(new ElectricStatsTooltipModifier(item))));
CEEItems.register(); CEEBlocks.register(); CEEFluids.register(); CEEPackets.register();
CEEMenuTypes/CEEEntityTypes/CEEPartialModels/CEEDisplaySources/CEEBlockEntityTypes.register();
CEEWireTypes/CEEMobEffects/CEESoundEvents/CEECreativeTab/CEEDataComponents/CEEPantographTypes/
CEEWireAttachments/CEESimulatedDevices/CEEPanelAttachmentTypes/CEEElectricTrainSoundTypes/
CEEWireInteractionBehaviours/CEESimulatedDeviceFeatureTypes.register(modEventBus);
CEEConfigs.register(modLoadingContext, modContainer);
if (ModList.get().isLoaded("struts")) StrutYourStuffRegistryEntries.register();
```

风格：**一个类一个注册域**（29 个 `CEE*` 静态类）＋ `CreateRegistrate`（方块/物品/创造栏）＋ `DeferredRegister`（如 `DeferredRegister.create(CEERegistries.WIRE_TYPE, ID)`，`CEEWireTypes.java:12-41`）。

## 4. 核心系统

**4.1 电路求解器（MNA + 稀疏矩阵）** `simulation/simulator/Network.java`、`simulation/util/`
- `formMatrix()`（`:143-267`）组装节点导纳矩阵：每节点累加 `properties.conductance() + properties.gMin()`，互导纳填 `-conductance`，对角填 `totalConductance`；**电压源**通过额外行列（`:204-232`）加入并置 `matrixNonSPD = true`；**变压器、互感**用 `CoupledProperties` 追加两行实现 `Vp1-Vp2 = n*(Vs1-Vs2)` 与电流耦合（`:234-266`）。
- 接地处理：`GROUNDED/UNGROUNDED/FIXED` 三态，未接地连通域强制 `setGroundConductance(nodeID, 1)`（`:111-118`）。
- `runSolver()`（`:352-384`）：先用上次解算残差 `VectorHelpers.normSqr(res) < 1e-2` 判收敛，否则按 `matrixNonSPD` 选 `LUSolver` 或 `CholeskySolver`，最多 100 次迭代；`simulation/util` 另备 `SparseMatrix/SparseRow/BiCGStabSolver/CGSolver/ILUPreconditioner/SimulatorProfiler`。
- 多线程：`SimulationTicker` 用 `Executors.newSingleThreadExecutor`（线程名 `CEE-Electrical-Simulator`，daemon）异步跑，`microTicks`/`totalMicroTicks` 支持子步长；`SimulationStats`/`SimulatorProfiler` 统计性能。

**4.2 拓扑优化（最值得学）** `simulation/simulator/NetworkOptimizer.java`
- 三种化简，每步把被删除支路记入 `network.optimizations` 栈，解算后由 `Network.getResults()`（`:269-331`）**反向回填电压**（`SimpleTopologyOptimizationEntry`/`StarToDeltaEntry`/`SetVoltageOptimizationEntry`/`CoupledPropertiesOptimizationEntry`/`AdvancedCoupledPropertiesOptimizationEntry`）。
- `seriesOptimize()`：度=2 的节点与其串联链合并（`DissolvedProperties` / 非纯阻性用 `AdvancedDissolvedProperties`），还能处理"变压器被串联链夹住"的 `optimizeCoupledProperties`。
- `starToDeltaOptimize()`：Y-Δ 变换（`calculateRAB/RBC/RCA`），已有并联线用 `ParallelDissolvedProperties` 合并，等价性受 `isSimpleResistor()`/`canDissolve(pass)` 约束；`runOptimizationPass()` 返回 true 表示已无法继续。

**4.3 节点与线网基础设施** `foundation/nodes/` + `simulation/infrastructure/`
- 节点模型：`Node`→`InWorldNode`(381 行)→`AttachedNode`（线缆中段开断点）/`PositionedAttachedNode`，连接用 `InWorldNodeConnection`/`DirectionalInWorldNodeConnection`/`NodeConnectionPoint`。
- `InfrastructureSavedData extends SavedData` 是**全等级唯一电气状态**：节点 ID 用 `IntStack freeNodeIDs` 复用，连接存 `WireData`，支持 `getConnectionsInSection(long section, ...)`（按区块段索引）、`createCut/relocateCut/removeCut(WireCutHandle, ...)`（可在导线上"剪口"插节点）、`migrateFromLegacy` 旧数据迁移、`DYNAMIC_POSITION_NODES`（随载具移动的节点）。
- 模块化子系统字段：`wireSimulationState / wireAssemblerModule / wireLifetimeModule / wireCrossContactModule / catenaryModule / wireElectrocutionModule / wireSync`（电线寿命熔断、交叉短路、悬链线、触电、同步）。
- `WireSimulationState.createCircuitBuilder()`（`:87`）把世界线网编译成 `CircuitBuilder`；`WireSync` + `SendVoltageDataPacket/RequestVoltageDataPacket` 负责客户端同步。

**4.4 数据驱动的导线类型** `CEEWireTypes.java` + `simulation/WireType.java`
- 自定义注册表类型 `WireType`，`Builder` 链式：`resistance(config::get)`、`insulationResistance`、`maxInsulationVoltage`、`maxTemperature`、`maxLength`、`maxCurrent`、`droppedItem/spoolItem`、`dyeable(...)`、`replaceOnOverheat(COPPER)`（绝缘层烧毁后变裸铜）、`decorative()`；`DUPLEX/BUNDLE_CONDUCTOR` 用同一套机制做"多芯线"（自定义 `WireType` 而非新方块）。

**4.5 内容与网络层**
- `content/*` 覆盖发电-输电-配电-负载全链：`connector`（连接点）、`electrical_panel`(378 行 Block，含可插拔 `attachments`)、`transformer/current_transformer/voltage_regulator`、`fuse`(含 `fuse_held`)、`energy_meter/clamp_meter`、`railway_electrification`（`catenary` 悬链线、`pantograph` 受电弓 `PantographMovementBehaviour` 跟 Create 火车移动、`third_rail`、`sound_effects`）。
- 网络：`CEEPackets` 是 **enum + `BasePacketPayload.PacketTypeProvider`**，由 `CatnipPacketRegistry`（Create 的 catnip）统一注册 23 个包（`SEND_VOLTAGE_DATA`、`SEND_NODE_DATA`、`SEND_WIRE_CONNECTIONS`、`SEND_CATENARY`、`SEND_SPARK`、`INTERACT_WIRE`、`CHANGE_LENGTH`…）。
- `devices/device/*`（`SimulatedDevice`/`SimulatedDeviceFactory`/`SimulatedDeviceType`/`VirtualRedstoneDevice`/`DevicesSavedData`）把电气设备抽象成可挂到物理载具（Sable/Simulated）上的虚拟设备。
- 配置：`CEEConfigs`（Create `ConfigBase` 风格 + `ModConfigSpec`，`onLoad/onReload` 派发）拆成 `CClient/CServer/CRatings/CResistances/CVoltages/CSimulation/CTrains/CRotor`，`WireType` 直接引用配置 Supplier 实现热重载生效。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络见 4.5；数据驱动主要是导线类型（自定义注册表）与 datagen 配方。datagen 位于 `events/datagen/`：`CEERecipeGen`(806 行)、`CEEMixingRecipeGen`/`CEECompactingRecipeGen`/`CEEMechanicalCraftingRecipeGen`（继承 Create 的 `MixingRecipeGen` 等）、`CEEGeneratedEntriesProvider extends DatapackBuiltinEntriesProvider`、`CEEAdvancements` + 自研进度触发器 `CEECriterionTriggerBase`/`SimpleCEETrigger`。配置见 4.5。Ponder 教程 12 个场景类共 3,565 行。

## 6. Mixin

`src/main/resources/electroenergetics.mixins.json`（`priority 1234`、`JAVA_21`、`refmap`、`plugin: com.george_vi.electroenergetics.CEEMixinPlugin`）：

- client 7 个：`MouseHandlerMixin`、`MultiPlayerGameModeMixin`、`ItemInHandRendererMixin`、`HumanoidModelMixin`、`CarriageSoundsMixin`、`SchematicRendererMixin`、`LevelRendererAccessor`
- common 14 个：`LevelChunkMixin`（`setBlockState`/`postProcessGeneration` `@Inject TAIL`）、`ComparatorBlockMixin`（`@WrapOperation` 拦截 `getAnalogOutputSignal`）、`TrainMixin`（对 `write`/`read` 用 `@WrapMethod` 持久化电气属性）、`LivingEntityMixin`（`checkTotemDeathProtection` 注入点做触电免疫）、`BlockStateBaseMixin`、`FluidPropagatorMixin`、`MinecraftServerMixin`、`StructureTemplateMixin`/`Schematic*Mixin`、`SubLevelAssemblyHelperMixin`、`compat.ElectricFanBlockEntityMixin`
- **`CEEMixinPlugin.shouldApplyMixin` 做条件化兼容**：无 `sable` 时禁用 `SubLevelAssemblyHelperMixin` 与 `ElectricFanBlockEntityMixin`，装 `youer` 时禁用 `LivingEntityMixin`
- 另有 `mixin_interfaces/`（`ICEETrainExtension`、`IPantographList`、`ISchematicInfrastructureList`）供 mixin 侧实现、主代码侧按接口取值

## 7. 值得学的 5 条具体做法

1. **用 MNA + 稀疏矩阵真的算电路，并给节点/支路做拓扑化简**（`NetworkOptimizer.java` + `Network.getResults()` 回填）；适用：任何"网络必须真的收敛"的模拟系统（流体、热、物流）。
2. **化简结果全部入栈、求解后按栈反向回填派生量**（`optimizations` Deque + 5 种 `OptimizationEntry`）；适用：先化简再计算、但 UI 仍要显示原始每个元件数值的场景。
3. **自定义注册表承载"材料/类型"而不是新建方块**（`CEERegistries.WIRE_TYPE` + `WireType.Builder` 绑定配置 Supplier）；适用：同一方块要有 N 种物性变体（导线、管道、铆钉）。
4. **`InfrastructureSavedData extends SavedData` 做单点世界状态 + 模块字段拆分 + 数据迁移钩子**（`:53-92`、`migrateFromLegacy`、`getConnectionsInSection` 段索引）；适用：大世界范围内万级对象的增删改与索引。
5. **枚举 + CatnipPacketRegistry 集中声明所有包**（`CEEPackets.java`）；适用：包数量多时避免手写 23 处注册样板。
6. （附带）**IMixinConfigPlugin 按已加载 mod 动态禁用 mixin**（`CEEMixinPlugin.java`）；适用：兼容多个改同一类的附属 mod。

## 8. 公开 API / 扩展点

非库 mod，但扩展面明确：`events/AddToElectricGraphEvent`（携带 `CircuitBuilder`/`InfrastructureSavedData`，可往电路里注入自定义元件）与 `FinishElectricSimulationEvent` 走 NeoForge 事件总线；`simulation/electrical_properties/*`（`resistor/capacitor/inductor/diode/voltageSource/Norton/Nonlinear/Coupled/...`，含 `canDissolve`）是仿真层可扩展的元件抽象；`WireType` 是公开注册表类型，附属可注册新导线；`compat/computercraft/peripherals` 提供 CC:Tweaked 外设；`mixin_interfaces/*` + `CEEMixinPlugin` 展示了跨 mod 的 mixin 开关范式。
