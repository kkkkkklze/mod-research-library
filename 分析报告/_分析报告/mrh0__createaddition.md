# mrh0/createaddition — Create Crafts & Additions

## 1. 基本信息

- Mod 名：Create Crafts & Additions；mod_id `createaddition`；作者 MRH0
- 目标：MC 1.21.1 / NeoForge 21.1.248（`gradle.properties`：`minecraft_version=1.21.1`、`neo_version=21.1.248`、`loader_version_range=[1,)`）；Java 21
- Gradle：ModDevGradle `net.neoforged.moddev 2.0.141`（`build.gradle:4`），Parchment `2024.11.17`；mixins 用 `mixingradle` 变量但实为 ModDev 内建
- 许可证：MIT（`LICENSE`、`gradle.properties:mod_license=MIT License, Copyright 2025 MRH0`）
- mod 元数据不在 resources 里，而在 `src/main/templates/META-INF/neoforge.mods.toml`，由 `generateModMetadata` 任务做 `${}` 变量展开后加入 sourceSet（`build.gradle` 尾部）
- 依赖：编译期依赖 Create `6.0.10-280`、Ponder `1.0.82`、Flywheel `1.0.6`、Registrate `MC1.21-1.3.0+67`、JEI `19.25.0.323`；可选运行时 compat：CC:Tweaked `1.115.1`、Mekanism、IE、`sable`/`sablecompanion`、`aeronautics`、`simulated`、`ae2`。即：它是 Create 的**下游附属**，自己不是 API

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` → 230；`wc -l` 合计 20359 行（全部在 `src/main/java`）。

主要包（第 3 层，括号=文件数）：`index`(16)、`energy`(11)、`datagen/RecipeProvider`(11)、`network`(9)、`item`(9)、`blocks/*`（`portable_energy_interface` 9、`modular_accumulator` 9、`connector` 8+`connector/base` 6、`liquid_blaze_burner` 6、`electric_motor`/`alternator`/`rolling_mill`/`servo_motor` 各 4-5）、`mixin`(8)、`compat/jei`(8)、`compat/computercraft`(8)、`config`(3)。

最大文件：`energy/IWireNode.java`(623)、`ponder/PonderScenes.java`(573)、`blocks/modular_accumulator/ModularAccumulatorBlockEntity.java`(551)、`blocks/servo_motor/ServoMotorBlockEntity.java`(497)、`blocks/liquid_blaze_burner/LiquidBlazeBurnerBlockEntity.java`(485)、`blocks/connector/base/AbstractConnectorBlockEntity.java`(426)、`config/CommonConfig.java`(317)、`index/CABlocks.java`(299)。

## 3. 入口与注册

主类 `src/main/java/com/mrh0/createaddition/CreateAddition.java:54`（`@Mod(CreateAddition.MODID)`）。采用 **CreateRegistrate + DeferredRegister 混用**：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MODID)
        .defaultCreativeTab((ResourceKey<CreativeModeTab>) null)
        .setTooltipModifierFactory(item -> new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)
                .andThen(TooltipModifier.mapNull(KineticStats.create(item))));
```
（`CreateAddition.java:66-71`）

构造器里统一收集入口：`CABlocks.register()`、`CABlockEntities`、`CAItems`、`CAFluids`、`CAEffects`、`CARecipes`、`CASounds`、`CADamageTypes`、`CADisplaySources`（`CreateAddition.java:129-141`），再挂 `RegisterCapabilitiesEvent -> CACapabilities::register`、`RegisterPayloadHandlersEvent -> registerPackets`（`:106-107`）。`index` 包 16 个类按注册域拆分（`CABlocks/CABlockEntities/CAItems/CARecipes/CACapabilities/CADataComponents` 等）；`CARecipes` 用 `DeferredRegister.create(...)` 注册 `RecipeSerializer`、`RecipeType`、以及 NeoForge 的 `ICondition` codec（`index/CARecipes.java:22-27`）。

## 4. 核心系统

**a) 电网（能量线缆网络）** `energy/`。`IWireNode`（623 行，全接口 + default 方法）定义节点的读写/连接语义，`LocalNode` 用非装箱字段存 `index/otherIndex/type/relativePos` 并内联序列化常量（`LocalNode.java:14-22`）；`WireType` 是枚举表（铜/金/银金/节日线，含 `ID, TRANSFER, CR/CG/CB, DROP, SOURCE_DROP`，`WireType.java:8-13`），用 `fromIndex` 反查。网络聚合在 `energy/network/EnergyNetwork.java`：按 tick 交换 `inBuff/outBuff` 双缓冲，`getMaxBuff()` 由节点数与需求动态算出并被配置封顶（`EnergyNetwork.java:30-46`）；`EnergyNetworkManager` 用 `WeakHashMap<LevelAccessor, Manager>` 按维度持有网络并在无效时剔除（`EnergyNetworkManager.java:10-38`）。

**b) 连接器 BlockEntity** `blocks/connector/base/AbstractConnectorBlockEntity.java:44` 同时实现 `IWireNode, IObserveBlockEntity, IHaveGoggleInformation, IEnergyProvider`，内部 `LocalNode[] localNodes` + `IWireNode[] nodeCache` 双数组缓存节点，外部能量用 `BlockCapabilityCache<IEnergyStorage, Direction> external` 缓存相邻方块能力（避免每 tick 重查 capability）。

**c) 动能↔电能转换**：电机/泵/伺服/交流发电机。注册时即把数值接进 Create 的应力表：`.onRegister(BlockStressValues.setGeneratorSpeed(256, true))` 与 `BlockStressValues.CAPACITIES.register(block, () -> CommonConfig.MAX_STRESS.get()/256f)`（`index/CABlocks.java:73-74`）。数值全部来源于配置，便于调平衡。

**d) 模块化蓄能器（多方块）** `blocks/modular_accumulator/`：`CAConnectivityHandler`(383) 复用 Create 的 connectivity 思路做多方块合并，`ModularAccumulatorBlockEntity` 用 `CREATE_CONNECTIVITY` 式接口暴露 `IMultiTileEnergyContainer`，并有 `ModularAccumulatorMovement` 作为 contraption 移动行为。

**e) 配方与条件**：`recipe/charging`、`recipe/liquid_burning`、`recipe/rolling` 复用 Create 的 `StandardProcessingRecipe`（`index/CARecipes.java:8` 导入），并自建 `MapCodec<ICondition>` 条件 `HasFluidTagCondition`（数据驱动配方条件）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`CreateAddition.registerPackets`（`:189-218`）用 `event.registrar("1").executesOn(HandlerThread.MAIN)`，三个 payload 全 `playBidirectional` + `DirectionalPayloadHandler<>(client, server)`：`ObservePacketPayload`（观察方块实体 goggle 数据）、`EnergyNetworkPacketPayload`（电网状态同步）、`TimeRemainingPacketPayload`。每个 payload 自带 `TYPE` 与 `STREAM_CODEC`，handler 分离到 `network/ClientPayloadHandler` 与 `ServerPayloadHandler`。
- 配置：`config/CommonConfig.java` 单一 `ModConfigSpec`，用 `@EventBusSubscriber(bus = MOD)` + `ModConfigEvent` 触发，构造器里 `container.registerConfig(ModConfig.Type.COMMON, CommonConfig.COMMON_CONFIG)`（`CreateAddition.java:115`）。按功能分 12 个 category（`CATAGORY_WIRES`、`CATEGORY_TESLA_COIL` 等）。
- datagen：`datagen/CreateAdditionsDataGen.java` 监听 `GatherDataEvent`，一次性挂 14+ provider：方块/流体/物品 Tag provider、vanilla 风格 `CACraftingRecipeProvider`，以及 Create 的 `RecipeGen` 子类（`CACrushingRecipeGen`、`CAMixingRecipeGen`、`CAPressingRecipeGen`、`CAMechanicalCrafterRecipeGen`…），并附加 `DatapackBuiltinEntriesProvider` 注册 damage type 等。

## 6. Mixin

配置：`src/main/resources/createaddition.mixins.json`（`required:true`、`priority:1000`、`compatibilityLevel:JAVA_17`、`package: com.mrh0.createaddition.mixin`），共 8 个类：`BaseFireBlockMixin`、`FireBlockMixin`、`FireBlockInvoker`、`BlockMovementChecksMixin`、`ContraptionMixin`、`FlowingFluidMixin`、`DockingConnectorBEMixin`、`VanillaSubLevelBERenderMixin`。

代表：`mixin/FireBlockMixin.java:19-24` 用 MixinExtras 的 `@WrapOperation` 包裹 `FireBlock.canCatchFire` 内对 `BlockState.isFlammable` 的调用（`target = Lnet/minecraft/world/level/block/state/BlockState;isFlammable(...)`），使可燃液体也能引燃；同类里另一个注入点用 `@ModifyExpressionValue` + `@Local`。注意 `ContraptionMixin` 实际主体被注释掉（空 mixin 保留占位，`mixin/ContraptionMixin.java:8-30`）。

## 7. 值得学的 5 条做法

1. **用接口 + default 方法承载跨 BE 的共用逻辑**：`energy/IWireNode.java` 把"取节点/掉线缆/迭代连接"全做成 default 方法，`AbstractConnectorBlockEntity` 只存状态；适用于自己写多方块/网络类共享行为。
2. **能力查询缓存**：`AbstractConnectorBlockEntity` 中 `BlockCapabilityCache<IEnergyStorage, Direction> external` + `nodeCache[]`，避免每 tick 重新 `level.getCapability`；适用于高频交互的机器 BE。
3. **数值全部配置化并反向注入 Create 应力表**：`index/CABlocks.java:73-74`、`config/CommonConfig.java`；适用于 Create 附属调平衡，无需改代码。
4. **网络协议三件套分离**（payload 类 + `TYPE`/`STREAM_CODEC` + Client/Server handler 分文件 + `DirectionalPayloadHandler`），见 `network/` 与 `CreateAddition.java:189`；适用于 NeoForge 1.21.1 自定义包规范写法。
5. **mod 元数据模板化**：`src/main/templates/META-INF/neoforge.mods.toml` + `generateModMetadata`（`build.gradle` 尾部）把版本/作者/依赖范围集中到 `gradle.properties`，CI 可注入版本号；适用于任何 NeoForge 项目。

## 8. 公开 API

非库模组，无独立 API 包。可被外部复用的"半公开面"是 `energy/IWireNode`（接口，任何 BE 可实现以接入其电网）与 `energy/network/EnergyNetwork*`；未见对外发布的 maven 坐标声明（`publishing` 指向本地 `repo` 目录，`build.gradle`）。
