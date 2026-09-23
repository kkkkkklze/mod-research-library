# Create FluidLogistics 源码分析报告

## 1. 基本信息

- Mod 名：Create FluidLogistics / `mod_id=fluidlogistics` / 版本 1.2.9
- 作者：Yision（`gradle.properties:16`）
- 许可证：**All rights reserved**（`gradle.properties`；仓库内 `LICENSE.txt` 仅 48 字节，另有 `TEMPLATE_LICENSE.txt`）
- 目标：MC 1.21.1 + NeoForge `21.1.219`（`loader_version_range=[1,)`），Parchment 2024.11.17
- Gradle 插件：`net.neoforged.moddev 2.0.116`、`java-library`、`com.hypherionmc.modutils.modpublisher 2.2.2`（`build.gradle:1-6`）；Gradle 属性关闭 daemon（`org.gradle.daemon=false`）
- 编译依赖（`build.gradle:95-110`）：Create `6.0.10-280`（`create_version_range=[6.0.10,)`）、Registrate `MC1.21-1.3.0+67`、Ponder `1.0.82`、Flywheel API、Vanillin `1.1.3-41`、CC:Tweaked、JEI/EMI/Jade（compileOnly）、可选兼容 `create-enchantment-industry`、`create-dragons-plus`、`kaleidoscope-tavern`。

## 2. 源码规模与包结构

433 个 `.java`，54500 行。

主要包：`content/logistics` 79、`content/fluids` 77、`content/equipment` 54、`mixin/client` 20、`content/schematics` 19、`content/processing` 19、`registry` 18、`ponder` 17、**`api/packager` 16**、`mixin/logistics` 12、`util` 9、`mixin/kinetics` 7、`compat/jei` 7、`compat/jade` 7、`render` 6、`config` 6、`foundation/fluid` 5、`filter/attribute` 5、**`api/handpointer` 5 / `api/factorygauge` 5**、`mixin/accessor` 4、`compat/emi` 4、`network/factoryPanel` 2。

最大文件：`ResourceFactoryGaugeScreen.java` 863、`MultiFluidAccessPortBlockEntity.java` 732、`ResourceFactoryPanelBehaviour.java` 710、`HandPointerInteractionHandler.java` 663、**`PackageResourceRegistry.java` 658**、`StockKeeperRequestScreenMixin.java` 642、`FluidPumpBlock.java` 611、`LogisticsSelectionHandler.java` 594、`FaucetBlockEntity.java` 585、`MechanicalFluidGunState.java` 576。

## 3. 入口与注册

主类 `src/main/java/com/yision/fluidlogistics/FluidLogistics.java:98`。双轨注册：**Registrate（`CreateRegistrate` 子类 `FluidLogisticsRegistrate`）负责方块/物品/标签，NeoForge `DeferredRegister` 负责创造标签与全局掉落修饰器**：

```java
public static final CreateRegistrate REGISTRATE = FluidLogisticsRegistrate.create(MODID)
        .setTooltipModifierFactory(item -> ... new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)
                .andThen(TooltipModifier.mapNull(KineticStats.create(item))))
        .defaultCreativeTab(FLUID_LOGISTICS_TAB);
```

构造器（:126-169）注册 `AllConditionCodecs / AllDataComponents / AllFluidAttributeTypes / AllFluidLogisticsFluid(s|Particle|FanProcessing|Recipe)Types / FluidLogisticsPackagePortTargetTypes / AllBlocks / AllBlockEntities / AllItems / AllMenuTypes / FluidLogisticsArmInteractionPointTypes`。**第三方 API 启动在这个阶段"喂"数据**：`PackagerAddresses.register(Create 的 PACKAGER)`、`HandPointerCrafterAdapters.register(...)`、`FactoryGauges.register(new FactoryGaugeType(...))`。`modEventBus.addListener(AllItems::registerAliases)`。

真正的一次性初始化放在 `commonSetup` 的 `event.enqueueWork`（:171-183）：`PackageResources.bootstrap()`、`FactoryGauges.bootstrap()`、`FluidLogisticsPackets.register()`、`ArmInteractionPointType.init()`、`AllMountedStorageTypes.register()`、`FluidLogisticsUnpackingHandlers.registerDefaults()`，以及向 Create 注册应力影响 `BlockStressValues.IMPACTS.register(AllBlocks.FLUID_PUMP.get(), () -> 8.0)`。能力注册集中在 `registerCapabilities(RegisterCapabilitiesEvent)`（:185-218）：14 个方块实体 + 物品能力（压缩储罐、铜桶用 `FluidHandlerItemStack(AllDataComponents.COPPER_BUCKET_CONTENT, ...)`、四种氧化状态流体包裹、原版雪球桶）。

## 4. 核心系统

**4.1 PackageResource —— 让 Create 包裹系统承载流体（最重要的可复用设计）**
`api/packager/` 16 个类构成完整扩展 API：`PackageResourceType`（`@ApiStatus.Experimental` 接口，定义 `carrierItem / isValidCarrier / normalizeKey / matches / amountOf / createCarrier / maxPerPackage / createPackage`，内嵌 `SawAction{DEFAULT, DESTROY_WITHOUT_DROPS}` 与 `DropAction{PASS, CONSUME_CARRIERS}`），`PackageResources` 为静态门面，`PackageResourceRegistry`（658 行）实现**生命周期状态机 `OPEN → BOOTSTRAPPING → FROZEN`**：注册期用 `LinkedHashMap pendingTypes`，`bootstrap()` 后转成 `Map.of()` 不可变快照 + `IdentityHashMap<Item, PackageResourceType> typesByCarrier` 加速按载体物品查找，冻结后拒绝新注册并抛错。配套 `ResourcePackager / ResourcePackagers / PackageInspection / PackageUnpackContext / PackageDestroyContext / PackageResourceCrafting`。

**4.2 FactoryGauge 资源化工厂仪表盘**
`api/factorygauge/`：`FactoryGauges` 与 4.1 同构（`Lifecycle OPEN/BOOTSTRAPPING/FROZEN` + 双重索引 `BY_ID`/`BY_ITEM`），提供 `createItem(ResourceLocation typeId, Item.Properties)` 让外部 mod 直接产出可被 Create 工厂面板识别的仪表物品；`FactoryGaugeType(id, PackageResourceType, item, probe)`；`FactoryGaugeFilterResolver`、client 侧 `FactoryGaugeClient / FactoryGaugeModelSet`。行为实现 `content/logistics/factoryGauge/ResourceFactoryPanelBehaviour.java`（710 行）+ UI `ResourceFactoryGaugeScreen.java`（863 行）。

**4.3 多流体储罐与流体网络**（`content/fluids` 77 文件）：`MultiFluidTank / HorizontalMultiFluidTank / MultiFluidAccessPort / FluidInventoryAccessPort`（`MultiFluidAccessPortBlockEntity` 732 行）、`FluidPumpBlock`（611 行）+ `FluidPumpNetworkUpdater`（每 tick 统计已加载泵数，ServerStopped 时 `clearLoadedFluidPumpCounts()`）、`FaucetBlockEntity`、`InfiniteFluidTank`、`CopperBucket`、`WaterContainingCopperCasingFluidHandler`（单例假流体处理器，`:198-200`）。

**4.4 HandPointer 手持指针工具**（`content/equipment/handPointer` + `api/handpointer`）：`HandPointerInteractionHandler` 663 行 + `LogisticsSelectionHandler` 594 行做选取交互；`PackagerAddress`/`PackagerAddresses` 是可注册的"包地址"映射（默认注册 Create 的 PACKAGER 与自家 FLUID_PACKAGER）；`HandPointerCrafterAdapter(s)` 提供合成器适配器扩展点（内置 `CreateMechanicalCrafterAdapter`）；`AddressEditFeedback` 做客户端反馈。**10 个 C2S 包**支撑该工具的全部交互。

**4.5 蓝图/原理图与后处理**：`content/schematics` 19 文件 + `mixin/schematics/{SchematicTableInputSlotMixin, ServerSchematicLoaderMixin}` + `accessor.SchematicannonBlockEntityAccessor`（读私有字段），实现"蓝图中含流体也能量化建造"。`content/processing/{copperBasin, blazeCooler}`，`BlazeCoolerFuelManager` 作为 `AddReloadListenerEvent` 监听器做数据驱动燃料表。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**CatnipPacketRegistry**（`net.createmod.catnip.net.base`），`network/FluidLogisticsPackets.java` 实现 `BasePacketPayload.PacketTypeProvider`，约 21 个负载（Clipboard、CopperFrogport、FactoryPanel×2、HandPointer×10、Faucet 粒子、MechanicalFluidGun×4、流体蓝图×2），包名=枚举名小写，`register()` 在 commonSetup 的 enqueueWork 内执行；按功能分子包（`handPointer/network`、`mechanicalFluidGun/network`、`schematics/network`…）。
- 配置 + 数据驱动特性开关：`config/FeatureToggle.java` 定义约 30 个 `ResourceLocation` 特性 ID（`fluid_pump`、`multi_fluid_tank`…）与 `isEnabled(id)`；`config/FeatureEnabledCondition.java` 是 `ICondition` record（字段 `feature`），在 `AllConditionCodecs` 注册后可直接写进数据包 JSON 条件里——**被关掉的特性的配方/战利品表加载即被跳过**；另有 `FluidHatchAdvertisedCondition` 做"仅广告位隐藏"的特例。UI 层用 `BuildCreativeModeTabContentsEvent` + `FEATURE_ITEMS[]` 表（`FluidLogistics.java:261-284`）从创造标签里移除被禁用物品。
- 数据组件：`datacomponent/FluidTankContent.java` + `registry/AllDataComponents`；`registry/AllMountedStorageTypes` 接入 Create 的挂载存储（装置上搬运流体）。
- datagen：`infrastructure/data/FluidLogisticsDatagen.java` 采用**"手写 JSON 模板 + 原样搬运"**策略——自写 `StaticDataProvider` 用 `Files.walk(src/datagen/resources/data)` 遍历，`JsonParser` 解析后 `DataProvider.saveStable` 输出到 `PackOutput.Target.DATA_PACK`；路径由 `FMLPaths.GAMEDIR.getParent().resolve("src/datagen/resources/data")` 推算（脱离标准 src/main/resources，便于用纯 JSON 维护大量数据包内容）。

## 6. Mixin

配置 `src/main/resources/fluidlogistics.mixins.json`：`package=com.yision.fluidlogistics.mixin`，`plugin=FluidLogisticsMixinPlugin`，`required=true`，`injectors.defaultRequire=1`；约 26 common + 22 client mixin，按域分子包（accessor / logistics / kinetics / schematics / processing / fluids / client）。

- 插件门控：`mixin/FluidLogisticsMixinPlugin.java` 在 `onLoad` 用 `Class.forName(..., false, loader)` 探测 `mezz.jei.api.runtime.IJeiRuntime`，只对 `StockKeeperTransferHandlerMixin` 与 `BasinCategoryMixin` 两个 JEI 专用 mixin 返回 false——**用"类是否存在"而非 modId 判断可选依赖**。
- 代表 hook（全部针对 Create）：`logistics.PackagerBlockEntityMixin` / `PackagerBlockMixin` 让打包机认识流体、`LogisticsManagerMixin` / `InventorySummaryMixin` / `RequestPromiseQueueMixin` / `StockTickerBlockEntityMixin`（把流体纳入物流网络与库存摘要）、`FactoryPanelConfigurationPacketMixin`（扩包字段）、`fluids.FluidPropagatorMixin`、`kinetics.ChainConveyorBlockEntityMixin`（链式传送带运流体）、client 侧 `StockKeeperRequestScreenMixin`（642 行，改请求界面）、`FactoryPanelScreenMixin`、`GoggleOverlayRendererMixin`（护目镜 HUD 加流体信息）、`PackagePortTargetSelectionHandlerMixin`。
- Accessor：`ArmBlockEntityAccessor`、`LogisticallyLinkedBehaviourAccessor`、`SchematicannonBlockEntityAccessor`、`CreativeModeInventoryScreenAccessor`。

## 7. 值得学的 5 条具体做法

1. **`OPEN → BOOTSTRAPPING → FROZEN` 注册表状态机**：`content/logistics/packageResource/PackageResourceRegistry.java:38-56`，在 `FMLCommonSetupEvent` 的 `enqueueWork` 里 bootstrap 后冻结为不可变 Map + `IdentityHashMap` 索引——既允许第三方在构造期注册，又保证运行期查找无锁且廉价。做 API/前置模组应直接照搬。
2. **接口 + 静态门面的 API 分层**：对外只暴露 `api/<domain>`（`PackageResources` / `FactoryGauges` / `PackagerAddresses` / `HandPointerCrafterAdapters`），实现类全部标 `@ApiStatus.Internal`（`PackageResourceRegistry`），扩展点用 `@ApiStatus.Experimental` 标明稳定性。
3. **特性开关即数据包条件**：`config/FeatureToggle.java` + `config/FeatureEnabledCondition.java`，配置里关掉一个特性时数据包条目直接不加载，比在代码里处处判空干净。
4. **可选依赖用类探测而非 modId**：`mixin/FluidLogisticsMixinPlugin.java` 的 `isClassPresent("mezz.jei.api.runtime.IJeiRuntime")`——支持 JEI 被其它方式加载/替换的场景。
5. **手写 JSON 模板 + `DataProvider.saveStable` 搬运**：`infrastructure/data/FluidLogisticsDatagen.java`，当数据文件量大且不适合代码生成时（本例：流体工厂仪表盘配方、筛选器属性），把 JSON 放 `src/datagen/resources/data` 由固定路径读取并输出，避免手抄进 `src/main/resources`。

**公开 API 概要**（本 mod 具备前置/API 性质）：公开包为 `com.yision.fluidlogistics.api.packager`（`PackageResourceType` / `PackageResources` / `ResourcePackager` / `PackageInspection` …）、`api.factorygauge`（`FactoryGauges.createItem` / `FactoryGaugeType` / `FactoryGaugeFilterResolver`）、`api.handpointer`（`PackagerAddresses.register`、`HandPointerCrafterAdapter`）、`api.creativetab`；接入方式为 `compileOnly` 依赖 `fluidlogistics` 后在 mod 构造期调用上述静态注册方法（须在 bootstrap 冻结之前），客户端扩展点另有 `api/*/client` 子包。
