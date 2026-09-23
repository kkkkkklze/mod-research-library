# TwistedGate/ImmersivePetroleum 源码分析报告

## 1. 基本信息

- Mod 名：Immersive Petroleum（沉浸原油，IE 官方附属）；mod_id `immersivepetroleum`；作者 Flaxbeard，现由 TwistedGate 维护。
- 版本/加载器：MC 1.21.1 + NeoForge 21.1.164（`gradle.properties:18-22`），Java 21，mod 版本 4.5.0-39。
- 构建：NeoForge ModDevGradle `net.neoforged.moddev` 2.0.30-beta（`build.gradle:1-7`）；无 mixin 插件。许可证在 `src/main/resources/META-INF/neoforge.mods.toml:4` 写为 `All rights reserved`（未使用开源协议）。
- 依赖：强依赖 `blusunrize.immersiveengineering:ImmersiveEngineering:1.21.1-12.4.2-194`（`build.gradle:113`，`implementation` + `datagenImplementation`），IE 既是前置也是它的 API 来源；JEI 19.10.0.126 仅 compileOnly api + localRuntime；`malte0811:DualCodecs:0.1.2` 为 implementation。gradle.properties 里的 CrT 14.0.38 / CC:Tweaked 1.110.2 代码已移除到 `removed_src/`。

## 2. 源码规模与包结构

- 272 个 `.java`，共 32680 行（`find . -name '*.java' | wc -l` / `cat | wc -l`）。
- 主要包：`common`(13)、`datagen common.data`(12)、`common.items`(10)、`common.util`(9)、`common.gui`(8)、`common.blocks.multiblocks`(8)、`client.render.multiblock`(8)、`client.gui.displays`(8)、`api.crafting`(8)、`common.network`(7)、`common.blocks.tileentities`(7)、`api.reservoir`(6)、`common.reservoir.util`(4)、`client.gui.machines`(5)。
- 最大文件：`common/entity/MotorboatEntity.java`(1013)、`common/items/ProjectorItem.java`(799)、datagen `common/data/IPRecipes.java`(724)、`blocks/multiblocks/logic/DerrickLogic.java`(648)、`common/items/DebugItem.java`(473)、`client/ClientProxy.java`(467)、`common/fluids/IPFluid.java`(396)。

## 3. 入口与注册

主类 `src/main/java/flaxbeard/immersivepetroleum/ImmersivePetroleum.java:47`，`@Mod(MODID)`，构造器签名 `(ModContainer, Dist, IEventBus)`：注册 SERVER/CLIENT 配置、`IPRegisters.addRegistersToEventBus(eBus)`、`IPContent.modConstruction(eBus)`、`IPRegisters.runCallbacks(eBus)`、`IPLootFunctions/IPRecipeTypes.modConstruction`；监听 `RegisterPayloadHandlersEvent`→`IPPacketHandler.init(event.registrar(MODID))`（`:135-137`），`AddReloadListenerEvent`→`RecipeReloadListener`，`LevelEvent.Load`→在 Overworld 的 DimensionDataStorage 上初始化 `ReservoirRegionDataStorage`（`:122-129`）。
注册体系是"DeferredRegister 集中池 + 静态内嵌类懒加载"：`IPRegisters.java:60-68` 用 `private static List<DeferredRegister<?>> REGISTERS` 收集所有 `DeferredRegister.create(registry, MODID)`，统一 `register(eBus)`；内容分在 `IPContent` 的 `Blocks/Items/Fluids/BoatUpgrades/Multiblock` 等静态类，每个类一个空 `forceClassLoad()` 由 `modConstruction` 强制触达，避免静态初始化时机问题。多方块不走原版注册，而是 IE 的新 API：`IPRegisters.registerMultiblock` 用 `MultiblockBuilder extends MultiblockRegistrationBuilder`（`IPRegisters.java:145-158`），`IPContent.setup` 里再 `MultiblockHandler.registerMultiblock(...)` 注册 6 个结构。

## 4. 核心系统

1. **油藏（Reservoir）系统** `api/reservoir/`：`ReservoirHandler`（`ReservoirHandler.java`）用 `Map<Pair<ResourceKey<Level>, ColumnPos>, Reservoir> CACHE` + `synchronized` 做列坐标缓存；油藏分布由 `PerlinSimplexNoise` 噪声生成（`scale=0.015625`，阈值 2/3，`:129-140`），`getTotalWeight` 按维度/生物群系缓存权重和。`ReservoirType extends IESerializableRecipe`（`ReservoirType.java:30`）把油藏做成**配方/数据包驱动**：`static Map<ResourceLocation, RecipeHolder<ReservoirType>> map`，字段 `weight/minSize/maxSize/residual/equilibrium`，用 `BWListBiome/BWListDimension`（`common/reservoir/util/`）做黑白名单校验，`IValidator` 抽象。持久化在 `common/datastorage/reservoir/ReservoirRegionDataStorage` + `RegionData`（按 `RegionPos` 分区的 SavedData）。
2. **IE 新多方块逻辑** `common/blocks/multiblocks/logic/`：`DerrickLogic implements IMultiblockLogic<State>, IServerTickableComponent, IClientTickableComponent`（`DerrickLogic.java:69`），`State implements IMultiblockState` 持有 `AveragingEnergyStorage`、`RedstoneControl.RSState`、`FluidTankFiltered`、`PipeConfig.Grid`；面级交互用 `CapabilityPosition(2,0,4, RelativeBlockFace.BACK)` 声明流体/能量口（`:85-94`）。学习点：状态类与逻辑类分离、`registerCapabilities(CapabilityRegistrar)` 注入能力。
3. **勘探/投影仪** `common/util/survey/`(SurveyScan/ReservoirInfo) + `items/ProjectorItem.java`：物品内嵌 `ClientRenderHandler.renderProjection/renderPhantom` 渲染多方块虚影，`ClientInputHandler` 处理滚轮旋转；结果通过 `MessageSurveyResultDetails`（双向）与 `MessageProjectorSync` 同步。
4. **配方与润滑** `api/crafting/`：`IPMultiblockRecipe extends MultiblockRecipe`，用内部 `TimeAndEnergy`+`Lazy<Integer>` 支持运行期 `modifyTimeAndEnergy(DoubleSupplier, DoubleSupplier)`（`IPMultiblockRecipe.java:30-80`）；`IPRecipeTypes` 复用 IE 的 `IERecipeTypes.TypeWithClass`；`LubricantHandler`/`LubricatedHandler`/`FlarestackHandler` 是给外部 mod 的注册入口。
5. **载具**：`MotorboatEntity`(1013 行) + `IPUpgradeItem`（reinforced_hull / icebreaker / tank / rudders / paddles，`IPContent.BoatUpgrades`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`common/network/IPPacketHandler.java:12-20` 统一在 `PayloadRegistrar` 上注册 `commonToServer/commonToClient`，每个包实现 `CustomPacketPayload` 且 `StreamCodec` 多用 `ByteBufCodecs.COMPOUND_TAG.map(MessageDerrick::new, MessageDerrick::toTag)`（`MessageDerrick.java:25`）——即"整包走 NBT"的省事写法；`process` 内 `context.enqueueWork` 并用 `getDirection().getReceptionSide()` 判端，另有 `sendToPlayer/sendToServer/sendToDimension/sendAll` 静态工具。协议共 6 个包（船燃料消耗、调试同步、投影仪同步、井架网格、勘探结果双向）。
- 数据驱动：油藏类型 = datapack recipe（`ReservoirSerializer` 注册名 `reservoirs`，`common/crafting/Serializers.java:22-24`），`RecipeReloadListener` 处理重载；`IPTags` 集中标签。
- 配置：`IPServerConfig.ALL` / `IPClientConfig.ALL` 经 `container.registerConfig` 注册。
- datagen：独立 `sourceSets.datagen`，入口 `common/data/IPDataGenerator.java`，run 配置 `data()` 输出 `src/generated/resources`（该目录未提交）并带 `--existing-mod immersiveengineering`，即**复用 IE 已有资源做兜底**；含 `IPRecipes/IPBlockStates/IPItemModels/IPBlockLoot/IPWorldGen/IPMultiblockTexturesAttach` 与配方 builder（Coker/Distillation/HydroTreater/Reservoir）。

## 6. Mixin

`src/main/resources/immersivepetroleum.mixins.json`（`required: true`，`package flaxbeard.immersivepetroleum.mixin`，`compatibilityLevel: JAVA_17`——与 Java 21 不一致，未确认是否必要），在 `neoforge.mods.toml` 末尾用 `[[mixins]] config=` 声明。全 mod 只有两个 mixin，且都是 accessor：`mixin/accessors/BoatAccess.java`、`mixin/accessors/DataStorageTestAccess.java`（用于访问原版私有成员），无 `@Inject`/`@Redirect` 逻辑注入。

## 7. 值得学的 5 条

1. 用 record `Loader(Function<String, ResourceLocation>)` + `DeferredHolder.create(BuiltInRegistries.X.key(), loc)` 引用别的 mod 的方块/物品/流体，避免硬依赖与 `ItemStack` 硬编码（`common/ExternalModContent.java:125-137`）——适用于任何可选前置兼容层。
2. 注册集中池化：`List<DeferredRegister<?>>` + `forceClassLoad()` 空方法模式，一处 `register(eBus)` 全注册（`common/IPRegisters.java` / `IPContent.modConstruction`）——适用于注册项上千的大型 mod。
3. 把"世界资源分布"做成配方类型（`ReservoirType extends IESerializableRecipe` + `RecipeHolder` map + 权重表缓存），从而天然获得数据包可配置与 KubeJS/JSON 覆盖（`api/reservoir/ReservoirType.java`、`ReservoirHandler.getTotalWeight`）——适用于任何"随机分布/权重抽取"设计。
4. 多方块逻辑用 IE 的 `IMultiblockLogic<State>` + 组件接口（`IServerTickableComponent`/`IClientTickableComponent`）而非 BlockEntity，逻辑/状态/能力三层分离（`blocks/multiblocks/logic/DerrickLogic.java`）——适用于搭建大型机器。
5. `TimeAndEnergy` + `Lazy<Integer>` 让配方产物数值在运行期被外部 handler 倍率化，而不是烘焙进 JSON（`api/crafting/IPMultiblockRecipe.java:53-80`）——适用于想给其他 mod 留数值钩子的机器配方。

## 8. 公开 API（附属/前置类）

API 包 `flaxbeard.immersivepetroleum.api`：`crafting`（`CokerUnitRecipe`/`DistillationTowerRecipe`/`HighPressureRefineryRecipe`/`IPMultiblockRecipe`/`IPRecipeTypes`，注册型 handler：`FlarestackHandler.register(TagKey<Fluid>)`、`LubricantHandler.register(TagKey<Fluid>, int)`、`LubricatedHandler.register(MultiblockRegistration, Function<IFluidHandler>??)`——签名见 `IPContent.setup` 中 `LubricatedHandler.register(Multiblock.PUMPJACK, PumpjackLubricationHandler::new)`）、`energy/FuelHandler`、`event/ProjectorEvent`、`reservoir`（`ReservoirHandler`/`ReservoirType`/`IReservoir`/`ReservoirBoundingBox`/`ReservoirPolygon`）、`IPTags`。外部 mod 通过 `ReservoirHandler.addReservoir(id, RecipeHolder<ReservoirType>)`、注册配方序列化器和上述 handler 接入；JEI/CrT/CC 兼容代码在当前版本已移除（`removed_src/`）。
