# 源码分析报告：KhloeLeclair/CreateAdditionalLogistics（Create: Additional Logistics）

## 1. 基本信息

- Mod 名：Create: Additional Logistics；mod_id：`createadditionallogistics`；作者：Khloe Leclair；版本 `1.4.5`
- 目标：Minecraft 1.21.1 / **仅 NeoForge**（`neo_version=21.1.209`，`loader_version_range=[1,)`）
- Gradle：`net.neoforged.moddev 2.0.107`；Java 21 toolchain；Parchment `2024.11.17`；`accessTransformers = files('src/main/resources/META-INF/accesstransformer.cfg')`
- 许可证：**MIT**（本仓库可参考实现思路，注意 Create 本身的许可）
- 关键依赖：Create `6.0.7-159`、Ponder `1.0.63`、Flywheel `1.0.5`、Registrate `MC1.21-1.3.0+62`；可选 **CC:Tweaked**（`cc_tweaked_enabled=true`、`cc_tweaked_version=1.116.1`，仓库 `maven.squiddev.cc`）
- 发布元数据走模板：`src/main/templates/META-INF/neoforge.mods.toml`（`processResources` 用 `expand` 替换），另有 `TEMPLATE_LICENSE.txt`

## 2. 源码规模与包结构

- `.java` 文件 **173** 个，总行数 **15 207**（实测）
- 最大文件：`common/registries/CALBlocks.java` 715、`common/utilities/CurrencyUtilities.java` 630、`common/RegexTokenizer.java` 585、`client/widgets/BlockPreviewWidget.java` 525、`common/content/logistics/packageEditor/PackageEditorBlockEntity.java` 451、`common/content/logistics/cashRegister/CashRegisterBlockEntity.java` 450、`common/datagen/CALBlockStateGen.java` 444、`common/content/kinetics/lazy/base/AbstractLowEntityKineticBlockEntity.java` 345、`common/registries/CALPackets.java` 323、`compat/computercraft/implementation/luaObjects/LuaTrainObject.java` 291
- 包结构：`api`(4)、`client/*`（约 20，含 `client/content/{kinetics/lazy,logistics/*,trains/networkMonitor}`、`client/widgets`、`client/registries/CALGuiTextures`）、`common/content/*`（`kinetics/lazy/{base,cog,flexible,shaft}`、`kinetics/verticalBelt`、`logistics/{cashRegister,packageAccelerator,packageEditor}`、`trains/networkMonitor`、`contraptions/actors/seats`）、`common/registries`(17)、`common/utilities`(8)、`common/datagen`(5)、`compat/computercraft`（约 25，`implementation/{luaObjects,peripherals}`）、`mixin`(12) + `mixin/client`(10)
- 风格特征：**几乎每个包都有 `package-info.java`** 并标注 `@MethodsReturnNonnullByDefault / @FieldsAreNonnullByDefault / @ParametersAreNonnullByDefault`

## 3. 入口与注册

主类 `src/main/java/dev/khloeleclair/create/additionallogistics/CreateAdditionalLogistics.java:37`。

```java
public static final NonNullSupplier<CreateRegistrate> REGISTRATE = NonNullSupplier.lazy(() ->
        CreateRegistrate.create(MODID).setTooltipModifierFactory(item ->               // :46
                new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)
                        .andThen(TooltipModifier.mapNull(KineticStats.create(item)))));

public CreateAdditionalLogistics(IEventBus modEventBus, ModContainer modContainer) {  // :63
    REGISTRATE.get().registerEventListeners(modEventBus);
    CurrencyUtilities.init();
    CALTags.init(); CALBlocks.register(); CALItems.register(); CALMenuTypes.register();
    CALEntityTypes.register(); CALBlockEntityTypes.register(); CALStress.register();
    CALPartialModels.register(); CALComputerCraftProxy.register();                    // :79
    CALDataComponents.register(modEventBus); CALDataMaps.register(modEventBus);
    modEventBus.addListener(CALPackets::register);                                     // :84
```

- 注册框架：**CreateRegistrate**（`common/registries/CALBlocks.java` 715 行，含 `EncasingRegistry`、`DyedBlockList`、`PackagerGenerator`、`SharedProperties`/`TagGen`/`ModelGen` 等 Create 数据生成工具）
- NeoForge 事件：`NeoForge.EVENT_BUS.addListener(...)` 注册 `CurrencyUtilities::onDataMapUpdated`、`RecipeHelper::onRecipesUpdated`、`AbstractLowEntityKineticBlockEntity::onTick`（`:89-91`）；自身用 `@SubscribeEvent` 处理 `ServerStartingEvent/ServerStoppedEvent/PlayerInteractEvent.RightClickBlock`
- 配置由 `common/Config.register(modContainer)` 注册 CLIENT/COMMON/SERVER 三份 spec

## 4. 核心系统

1. **"低实体"动力学（Lazy Kinetics）**（`common/content/kinetics/lazy/`）：`AbstractLowEntityKineticBlockEntity extends SplitShaftBlockEntity`（`:23`）用自维护的 `connections: List<BlockPos>` 代替邻居遍历，`write/read` 以 `long[] "Connected"` 存取（`:39-64`），读到旧键 `"Connections"` 时置 `lazyDirty` 触发重建；`checkInvalid / removeInvalidConnections() / notifyConnectedToValidate()`（`:88-114`）做延迟校验，客户端信息缓存由网络包 `ServerToClientEvent.CLEAR_INFORMATION` → `AbstractLazySimpleKineticBlock.clearInformationWalkCache()` 清理；衍生 `LazyShaftBlock`、`LazyCogWheelBlock`、`FlexibleShaftBlock`（可选连接的柔性传动，`FlexibleShaftBlockEntity` 285 行）。
2. **货币系统**（`api/` + `common/utilities/CurrencyUtilities.java`）：`ICurrency`（`getId/getItems/getValue/getStacksWithValue/extractValue/formatValue`）+ `ICurrencyBuilder` + `Currency` + `ICurrencyBackend`；`CurrencyUtilities` 维护 `CURRENCIES / API_CURRENCIES / FORMATTERS / BUILTIN_FORMATTERS` 静态表并提供内置格式化器（含 Numismatics 兼容）；价值来源是 NeoForge **DataMap**（见第 5 节），支持"压缩换算"（9 钻石 ↔ 钻石块，`Config.Common.currencyCompression`）。
3. **物流内容**：`PackageEditorBlockEntity`(451) + `PackageEditorBlock`（改包地址）、`PackageAcceleratorBlockEntity`（应力由 `CALStress` 的 provider 提供，config 可调）、`CashRegisterBlockEntity`(450) + `CashRegisterMenu` + `SalesHistoryData` + `SalesLedgerItem`（销售流水 UI，`client/.../SalesLedgerScreen`）。
4. **列车网络监视器**（`common/content/trains/networkMonitor/`）：`NetworkMonitor extends SingleBlockEntityEdgePoint`（`NetworkMonitor.java:10`），`EdgePointType.register(asResource("network_monitor"), NetworkMonitor::new)` 把自定义节点注册进 Create 的铁路图；`onTrainArrival/onTrainDeparture(graph, train, station)` 遍历 `graph.getPoints(NETWORK_MONITOR)` 广播事件给所有监视器。
5. **CC:Tweaked 集成**（`compat/computercraft/`）：`CALComputerCraftProxy` 条件注册；`AbstractEventfulComputerBehavior` + `FallbackEventfulComputerBehavior` 双实现（无 CC:T 时用空壳）；`implementation/luaObjects/` 用"只读基类 + `LuaWriteableXxx` 子类"分离读写权限（`LuaTrainObject`/`LuaWriteableTrainObject`、`LuaStationObject`/`LuaWriteableStationObject`、`LuaPostboxObject`）；`implementation/peripherals/{CashRegisterPeripheral,PackageEditorPeripheral,NetworkMonitorPeripheral,SyncedPeripheral}` 暴露外设，`PackageApi` 为 Lua 入口。
6. **地址匹配与正则**（`common/SafeRegex.java`、`RegexTokenizer.java` 585 行、`PatternReplacement.java` + `mixin/MixinGlob.java`）：`MixinGlob` 注入 catnip `Glob.toRegexPattern` 的 HEAD，识别 `"regex:"` 前缀（`Config.Common.globAllowRegex`）并调用 `SafeRegex.assertSafe(regex, maxStarHeight, maxRepetitions, allowBackrefs)`；`SafeRegex` 用 Guava Cache（1000 条 / 30 分钟）缓存 glob→regex 与替换串校验，`matchAddress()` 重写了 Create `PackageItem.matchAddress` 的双向匹配逻辑。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`common/registries/CALPackets.java:41` 用 **NeoForge 原生 API**（非 Catnip PacketSystem）：`event.registrar("3").executesOn(HandlerThread.MAIN)`，再 `registrar.playToServer/playToClient(TYPE, STREAM_CODEC, handler)`；6 个包 = 3 个 C2S（`UpdateGaugePromiseLimit`、`ConfigureFlexibleShaft`、`FinishedConfiguringFlexibleShaft`）+ 3 个 S2C（`OpenSalesLedgerScreen`、`OpenFlexibleShaftScreen`、通用 `ServerToClientEvent`）；编解码全用 `StreamCodec.composite(...)` + `ByteBufCodecs`。
- **数据驱动**：`CALDataMaps.java` 注册 `DataMapType<Item, CurrencyData>`（`createadditionallogistics:currency`，`RecordCodecBuilder` 编解码，`.synced(codec, false)` 同步给客户端），数据由 `datagen/CALDataMapProvider` 生成 JSON；`CALTags` 负责 tag 声明。
- **配置**：`common/Config.java` 手写 **NeoForge `ModConfigSpec`**（不用 Create ConfigBase）：`_Client/_Common/_Server` 三个内部类 + 静态 `configure` 三份 spec，分组 `currencyConversion / trainNetworkMonitor / addresses / regexSafety / kinetics.packageAccelerator`，带 `translation(CALLang.key("config."+path))` 便于本地化。
- **datagen**：`common/datagen/DataGen.java:19`，`addLanguageRegistrateData()` 通过 `REGISTRATE.addDataGenerator(ProviderType.LANG, ...)` 把 `config/interface/tooltip` 默认语言 JSON 写进 lang；`CALBlockStateGen`(444)、`CALRecipeProvider`、`CALWashingRecipeGen`；build.gradle 的 data run 会先 `cleanOldGeneratedResources` 清空 `src/generated/resources`，并带 `--existing-mod create`（CC:T 开启时再加 `--existing-mod computercraft`）。

## 6. Mixin

- 配置：`src/main/resources/createadditionallogistics.mixins.json`（`package dev.khloeleclair.create.additionallogistics.mixin`、`compatibilityLevel JAVA_21`、`overwrites.requireAnnotations=true`、`injectors.defaultRequire=1`；13 个通用 + 10 个 client）
- 通用：`MixinGlob`（`Glob.toRegexPattern` 的 `@At("HEAD")` 且 `cancellable=true`，注入正则地址支持）、`MixinFactoryPanelBehaviour`（工厂面板 promise limit / 额外库存）、`MixinStockTickerInteractionHandler`、`MixinPackageItem`、`MixinSmartBlockEntity`、`MixinTrain`、`MixinAbstractContraptionEntity`、`MixinBlazeBurnerBlockEntity`、`MixinTableClothBlockEntity`、`MixinSeatBlock`（阻止坐到拿着 Stock Keeper 的座椅）、`RotationPropagatorInvoker`（`@Invoker` 调 Create 私有旋转传播）、`IStockTickerBlockEntityAccessor` / `IStationPeripheralAccessor`（`@Accessor`）
- client：`MixinPackagerRenderer`、`MixinPackagePortScreen`、`MixinFactoryPanelScreen`、`MixinStockKeeperRequestScreen`、`MixinVisualizationManager`、`MixinAddressEditBox`、`MixinTableClothOverlayRenderer`、`MixinShoppingListItem`、`MixinTrackTargetingClient`、`IBlueprintOverlayRendererAccessor`
- 特点：不做 mixin 插件过滤（无 MixinPlugin），CC:T 相关分支靠 `CALComputerCraftProxy` 在 Java 侧条件加载而非 mixin 开关

## 7. 值得学的 5 条具体做法

1. **允许用户输入正则时的安全防护**：`common/SafeRegex.java:191` 用自写 `RegexTokenizer` 计算 star height / 重复次数 / 是否含反向引用，超限直接抛 `PatternSyntaxException`，并用 Guava Cache 缓存编译结果（`:17-30`）。任何暴露正则给玩家/服务器的 mod 都应照抄。
2. **用 `@Invoker`/`@Accessor` 取私有状态**：`mixin/RotationPropagatorInvoker.java`、`mixin/IStockTickerBlockEntityAccessor.java` 替代反射与 AccessTransformer，语义清晰且可被 IDE 校验。
3. **接入 Create 的图 API 添加自定义轨道节点**：`NetworkMonitor.java:15` `EdgePointType.register(...)` + `extends SingleBlockEntityEdgePoint`，再用 `graph.getPoints(type).forEach(...)` 广播事件——比自己扫描世界便宜得多。
4. **可选依赖的"代理 + 双实现"**：`compat/computercraft/CALComputerCraftProxy` 在加载时选择 `implementation` 类，`AbstractEventfulComputerBehavior` / `FallbackEventfulComputerBehavior` 保证无 CC:T 时不 NoClassDefFoundError。
5. **NeoForge 原生网络与 DataMap 的现代写法**：`CALPackets.java:41-53` 一文件收纳所有包（`registrar("3")` + `StreamCodec.composite`）；`CALDataMaps.java` 用 `DataMapType.builder(...).synced(codec, false)` + `RecordCodecBuilder` 把"物品→货币值"变成可被数据包/其它 mod 覆盖的数据，而不是硬编码表。
6. （补充）**每包 `package-info.java` 默认空值注解**，让 `@Nullable` 只标例外，减少样板（`api/package-info.java`）。

## 8. 对外 API（本仓库含公开 API 包）

- 包路径：`dev.khloeleclair.create.additionallogistics.api`（`ICurrency.java` / `Currency.java` / `ICurrencyBuilder.java`）
- 扩展点接口：`ICurrency`（`getId / getItems / getValue / getStacksWithValue / extractValue / formatValue` + 嵌套 `IAdvancedValueGetter / IAdvancedValueExtractor / IValueFormatter`）；后端接口 `ICurrency.ICurrencyBackend`（`registerCurrency / registerFormatter / newBuilder / get / getForItem`）
- 外部 mod 接入方式：运行时调用 `CurrencyUtilities` 的静态表（`CURRENCIES / API_CURRENCIES / FORMATTERS`）注册货币与格式化器（`CurrencyUtilities.init()` 在 mod 构造器中执行），或仅用数据包声明 `createadditionallogistics:currency` data map（`{ "id": ..., "value": ... }`，见 `CALDataMaps.CurrencyData`）。
- 其它可选混入接口（`common/utilities/`）：`IPromiseLimit`（工厂面板承诺上限）、`ISetLazyTickCounter`、`ICustomBlueprintOverlayRenderer`、`SidedCache`、`FlexiblePoleHelper`，供内部与兼容 mixin 判断方块实体能力时使用。
