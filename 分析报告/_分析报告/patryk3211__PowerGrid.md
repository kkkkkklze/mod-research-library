# Create: Power Grid 源码分析

## 1. 基本信息
- Mod 名 / mod_id：Create: Power Grid / `powergrid`（mod_version 0.6.1）；作者 patryk3211, Da-Negy, rvndm, casvara
- MC 1.20.1，**Architectury 多加载器**（`settings.gradle`: `include("native","fabric","forge")`，`enabled_platforms=forge,fabric`）；Forge 47.4.6 / Fabric Loader 0.17.3
- 构建：Gradle (Groovy) + architectury plugin（`architectury_api_version=9.2.14`）、MixinExtras 0.3.5、parchment 2023.09.03
- 许可证：Apache-2.0（`LICENSE`、mods.toml）
- 依赖：Create `6.0.7-281`(forge) / `6.0.8.1+build.1744`(fabric)（**Create 附属**，且深度使用 Create API）、Ponder 1.0.91、Flywheel 1.0.5、Registrate `MC1.20-1.3.3`、energy-api 3.0.0（Team Reborn）、可选 CC:Tweaked 1.120.0（`forge/src/.../compat/cc`）、Cold Sweat、FarmersDelight、JEI 15.20 / REI 12.0

## 2. 源码规模与包结构
817 个 `.java`（实测）：`src`（common）722 文件 / **93432 行**，`fabric` 33 文件 / 2710 行，`forge` 62 文件 / 4174 行，`native` 无 java（C++）。
`src/main/java/org/patryk3211/powergrid` 下按包（文件数）：`electricity` 334、`circuits` 97、`kinetics` 61、`equipment` 32、`utility` 25、`collections` 21、`network` 21、`mixin` 20、`ponder` 20、`config` 16、`compat` 15、`data` 14、`general` 12、`base` 4、`commands` 4、`advancements` 2。
最大文件：`ponder/scenes/DeviceScenes.java`(1757)、`electricity/WorldNetworks.java`(1377)、`ponder/scenes/CircuitScenes.java`(1047)、`collections/ModdedBlocks.java`(1026)、`electricity/sim/ElectricalNetwork.java`(787)、`kinetics/generator/winding/WindingBlockEntity.java`(765)、`circuits/circuitboard/CircuitBoardBlockEntity.java`(661)、`forge/.../DataProviderUtilityImpl.java`(627) 与 `fabric/.../DataProviderUtilityImpl.java`(623)。

## 3. 入口与注册
主类 `src/main/java/org/patryk3211/powergrid/PowerGrid.java`：
```java
public static void init() {
    ElectricalNetwork.LOGGER = LOGGER;
    NativeMNA.tryLoad();            // 加载本地加速求解器
    ModdedSoundEvents.prepare();
    REGISTRATE = createRegistrate();     // @ExpectPlatform，平台各实现一份
    register();                          // Modded* 集合类注册
    registerArchitecturyEvents();        // 全用 architectury 事件总线
    ModdedPackets.registerPackets();
}
```
- 注册框架：Create 的 **CreateRegistrate**，并被扩展为 `AbstractPowerGridRegistrate`（自定义 `.component(...)` 构建电路元件、自定义 data provider 与 Flywheel 视觉注册）。
- 平台差异用 architectury `@ExpectPlatform`：`createRegistrate()`、`finalizeRegistrate()`、`ComponentRegistry.entries()`、`ModdedConfigs.registerPlatform()`，实现分别在 `fabric/src/.../fabric/` 与 `forge/src/.../forge/` 包（同路径同名的 `DataProviderUtilityImpl` 等）。
- 事件全走 architectury：`TickEvent.ServerLevelTick.SERVER_LEVEL_PRE/POST` → `GlobalElectricNetworks.preTick/postTick`、`LifecycleEvent.SERVER_LEVEL_UNLOAD`、`InteractionEvent.RIGHT_CLICK_BLOCK/ITEM` → `WireItem::useOn/use`（`:94-107`）。
- 创造标签/物品/方块等集中在 `collections/Modded*.java`（Blocks/Items/Fluids/BlockEntities/Entities/Menus/Packets/Configs/Tags/Contraptions/DisplaySources/PartialModels/Particles/RenderLayers/SoundEvents/Keys/DamageTypes/Advancements/Commands/Icons）。

## 4. 核心系统
1. **电路求解器 / 电网仿真**（`electricity/sim/`）
   职责：把方块/电线抽象成节点+导线，用改进节点法（MNA）每 tick 求解电压/电流。核心 `ElectricalNetwork`（787 行）+ `sim/node/`（`ElectricNode`、`FloatingNode`、`CurrentSourceNode`、`CouplingNode`…）+ `sim/special/`（27 种非线性/动态元件：`BJTWire`、`InductorWire`、`CapacitorWire`、`TransmissionLine`、`NeonBulbWire`、`PNJunctionWire`…）。
   - `IMNA` 抽象后端，两种实现：`JavaMNA`（可移植）与 `NativeMNA`（JNI，`private native` 方法 + `ByteBuffer` 命令批处理：`jacobianAdd` 写满 256 条命令才 `processJacobianBuffer` 一次性下发，`:186-198`）；版本化库名 `powergridNative7`，找不到就从 jar 内 `native/<platform>/` 解压到 `.pg-native/` 再 `System.load`（`NativeMNA.tryLoad`）。
   - 矩阵增量维护：`updateConductance` 只把变化量 stamp 进雅可比，累积 `conductanceUpdates >= nodes*40 || conductanceDelta > 1000` 才整表重建（`ElectricalNetwork.java:672-679`）。
   - 支持 `merge/clear`、叶子节点消除（`makeLeaf`，非仿真节点映射到被跟踪节点）、`float` 节点自动加 1000S 对地锚定避免奇点（`:469-497`）、`multiTicks` 多子步、`warmUp` 预热迭代。
   - `native/` = CMake + SuperLU + OpenBLAS 子模块编译 C++ 求解器；`CSolver.SolverBackend` 枚举用 `BooleanSupplier checkSupport` + `Supplier<Function<ElectricalNetwork,IMNA>> constructor` 切换后端（`config/CSolver.java:52-68`）。
2. **世界电网管理**（`electricity/GlobalElectricNetworks.java` + `WorldNetworks.java` 1377 行 + `ClientWorldNetworks`/`ClientElectricNetwork`）：`ConcurrentHashMap<Level, WorldNetworks>`，网络合并/拆分（transformer、transmission line 可作分岛边界，见 `CSolver` 的 `splittingTransmissionLines/splittingTransformers`）、每 tick pre/post、玩家维度切换时 `dropTrackers`。
3. **电路板 / 元件系统**（`circuits/` 97 文件）：`circuitboard/CircuitBoardBlockEntity`(661) 承载可放置的"PCB"，元件是**数据驱动注册表**——`ComponentRegistry.REGISTRY_KEY = powergrid:components`、`ITEM_REGISTRY_KEY = powergrid:component_items`（`RecordCodecBuilder` 带 `item` + 可选 `tag`），生成物落在 `data/powergrid/powergrid/component_items/*.json`（如 `resistor.json` = `{"item":"powergrid:resistor"}`）。`circuits/components/Components.java` 用扩展后的 Registrate 声明式注册 40+ 元件（`REGISTRATE.component("triode", ElectronTubeComponent::new).footprint(3,3, b -> b.addPadSharedText(...)).item(...).register()`），每个元件是 `Component` 子类并实现 `IRenderedComponent`/`IInteractableComponent`/`IRedstoneComponent` 等小接口。
4. **电线/线缆实体**（`electricity/wire/`）：`BaseWireEntity`→`WireEntity`/`BlockWireEntity`/`HangingWireEntity`，端点抽象 `IWireEndpoint`（`BlockWireEndpoint`、`JunctionWireEndpoint`、`CircuitBoardEndpoint`、`DeferredJunctionWireEndpoint`、`ImaginaryWireEndpoint`），`WireRegistry.KEY = powergrid:wire_types` 数据驱动线材参数（`copper_cord.json`：`resistancePerItem/maximumCurrent/thermalMass/verticalCoefficient/insulated/colorable`）；`WireItem.useOn/use` 通过 architectury 交互事件进入。
5. **动力学/发电**（`kinetics/` 61 文件：`generator`、`motor`、`winding`（765 行绕组 BE）、`variac`、`rheostat`、`servo`、`punchcard`、`plotter`）——电能与 Create 转速/应力互转；`config/CStress` 通过 `BlockStressValues.IMPACTS/CAPACITIES.registerProvider(stress::getImpact/… )` 把应力并入 Create 体系（`collections/ModdedConfigs.java:76-78`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：architectury `NetworkChannel.create(powergrid:main)`，`SimplePacket` 接口（`encode(FriendlyByteBuf)` + `handle(Supplier<NetworkManager.PacketContext>)`，默认方法提供 `clientBoundPacket()/serverBoundPacket()`）；`collections/ModdedPackets.java` 是**枚举即注册表**，21 个包（`StateS2CPacket`、`EntityDataS2CPacket`、`MultimeterDataC2SPacket`、`NegotiateSyncC2SPacket`、`UpdateComponentBiPacket`…）统一在 `registerPackets()` 里逐个 `channel.register(type, encoder, decoder, handler)`；发送封装 `sendToClientsTracking(be/entity)`、`sendToClientsAround(pos, radius)`（`utility/PlayerLookup`）。`NegotiateSyncC2SPacket` 做客户端能力协商（`SYNC_TYPES` 按玩家记录）。
- 数据驱动：自定义注册表 `powergrid:components`、`powergrid:component_items`、`powergrid:wire_types` + 常规 tags/loot/recipes，datagen 落在 `fabric/src/main/generated/…`（含 `data/powergrid/powergrid/*`）。
- 配置：`collections/ModdedConfigs`（照 Create `AllConfigs`）用 `EnumMap<ModConfig.Type, ConfigBase>` + `ForgeConfigSpec.Builder().configure(...)`，16 个配置类分组：`CServer/CCommon/CClient/CCircuit/CElectricity/CGenerator/CKinetics/CResistance/CSolver/CStress/CThermal/CEquipment/CRecipes/CColdSweat`；`ResistanceValues/ThermalValues` 把数值也做成可配置；`server().isUpToDate()` + 进服提示 `/powergrid reset_configs`。
- datagen：`data/` 提供 `BlockTagProvider`、`ItemTagProvider`、`data/recipes/*`（标准/切削/压印/序列装配/磁化配方）：共 11 个 Recipe 类。

## 6. Mixin
三套配置：`src/main/resources/powergrid.mixins.json`（15 个 common：`AirCurrentMixin`、`ArmBlockEntityMixin`、`BeltDeployerMixin`、`BlockStateBaseMixin`、`ChuteBlockEntityMixin`、`EntityMixin`、`FanProcessingMixin`、`FluidPropagatorMixin`、`KineticBlockEntityAccessor`、`LevelEntitiesAccessor`、`LightningAccessor`、`PlayerMixin`、`RecipeApplierMixin`、`SheepMixin`、`SoundEntryBuilderMixin`）、`powergrid.client.mixins.json`（`BlueprintOverlayMixin`、`ComplexEntityRaycastMixin`、`ValueSettingsScreenMixin`、`RenderBuffersAccessor`、`BlueprintOverlayRendererAccessor`）、平台各一份（`powergrid-fabric.mixins.json` 4 个 / `powergrid-forge.mixins.json` 8 个，如 `ArmInteractionPointMixin`、`ChunkMapMixin`、`ThreadedAnvilChunkStorageAccessor`）。代表性 hook：
- `Flywheel/Create 集成`：`BeltDeployerMixin` → `BeltDeployerCallbacks.activate`；`ArmBlockEntityMixin` → `ArmBlockEntity.tick`；`FanProcessingMixin` → `FanProcessing`；`SoundEntryBuilderMixin`(remap=false) → `AllSoundEvents.SoundEntryBuilder.build`
- `Accessor` 风格：`KineticBlockEntityAccessor`(`@Accessor("flickerTally")`)、`LevelEntitiesAccessor`(`@Invoker("getEntities")`)、`LightningAccessor`(`@Invoker("findLightningTargetAround")` on `ServerLevel`)
- 交互/世界：`BlockStateBaseMixin` → `BlockStateBase.use`；`PlayerMixin`；`EntityMixin`；`SheepMixin` → `mobInteract`（HEAD, cancellable）；`FluidPropagatorMixin`(priority=1100) → `propagateChangedPipe`；`ChuteBlockEntityMixin` → `calculatePull/calculatePush`（order=1100, remap=false）

## 7. 值得学的 5 条做法
1. **把"性能关键"的数学解耦成可替换后端**：`IMNA` 接口 + `JavaMNA`/`NativeMNA` 双实现 + `SolverBackend` 枚举（`checkSupport`+`constructor`），Java 版永远可用的兜底路径，配合 `.pg-native/` 运行时解压 JNI 库（`NativeMNA.java:76-121`）——任何重计算子系统都可照抄这一结构。
2. **命令缓冲区减少 JNI 调用**：`jacobianAdd` 攒满 256 条命令再 native 调用（`NativeMNA.java:186-209`），跨语言边界只传 `ByteBuffer`。
3. **增量矩阵维护 + 阈值整表重建**：只 stamp 变化量，`conductanceUpdates >= nodes*40 || conductanceDelta > 1000` 才重建，避免浮点漂移（`ElectricalNetwork.java:336-353, 672-679`）。
4. **枚举即包注册表**：`ModdedPackets` 每个包一行枚举 + 统一 `register()`/`sendTo...` 辅助方法，网络部分（21 包）零散乱代码。
5. **数据驱动的元件/线材注册表**：`powergrid:components` / `component_items` / `wire_types` 用原始 `RegistryKey` + Codec + datagen（`ComponentRegistry.java:36-47`、`WireRegistry.java`），加一个新元件/线材 = 加 Java 类 + json，不动加载逻辑。
6. 补充：`@ExpectPlatform` 只暴露极少数方法（注册表工厂、配置注册、entries()），平台代码集中在 `fabric|forge/src/main/java/.../<pkg>/<platform>/` 同路径同名文件里，便于对照阅读。

## 8. 是否库/前置
非通用库，但它有对外可用的扩展点：`IMNA`（可插自己求解后端）、`ComponentRegistry`/`WireRegistry` 自定义注册表、`AbstractPowerGridRegistrate.component(…)` 构建器（供附属注册新电路元件）。外部 mod 接入靠 architectury 的注册表与 Create 的 `BlockStressValues`/`FanProcessingType`/`CreateRegistries` 等 API。
