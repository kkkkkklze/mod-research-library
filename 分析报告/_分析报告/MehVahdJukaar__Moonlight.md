# Moonlight Lib 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 | Moonlight Lib（旧名 Selene），`mod_id = moonlight` |
| 作者 | MehVahdJukaar（Supplementaries Team） |
| 版本 | `1.21.1-3.6.4`（`gradle.properties:7`） |
| 目标 | MC 1.21.1；NeoForge 21.1.248 + Fabric Loader 0.19.3 / Fabric API 0.116.15 |
| 模块 | `common`(524 java) / `fabric`(98) / `neoforge`(71)，三模块多加载器 |
| Gradle 插件 | 自研套件 `com.possible-triangle.core/common/fabric/neoforge` + `net.mehvahdjukaar.candlelight`（`build.gradle.kts:2-7`） |
| 许可证 | Supplementaries Team License v.1.5（source-available，非 MIT，禁止竞争性项目整合） |
| 编译依赖 | `net.mehvahdjukaar:candlelight`（自己的注解处理器）、`codecui-{common,fabric,neoforge}`（配置 UI 库，neoforge 用 `jarJar`、fabric 用 `include` 内嵌）；modCompileOnly：ModernFix、Map Atlases、Quark/Zeta、Iris、Configured、YACL、Cloth Config、`dev.ryanhcode.sable-companion`。neoforge 的 `modRuntimeOnly` 里挂着 Supplementaries/Amendments 做自测 |
| 依赖关系 | 它是"上游库"：Supplementaries、Amendments 等全部依赖 Moonlight，Moonlight 自身不依赖任何内容 mod |

## 2. 源码规模与包结构

实测：**693 个 .java，70983 行**。集中在 `net.mehvahdjukaar.moonlight` 下的 `api`（对外公开）与 `core`（内部实现）两大块。

`api` 分包文件数：client 74、misc 50、util 47、resources 46、block 30、platform 17、item 15、map 13、fluids 12、set 11、events 8、entity 7、trades 6、worldgen 3、integration 3。
`core` 分包：mixins 52、client 31、misc 15、network 11、commands 10、worldgen 7、loot 5、integration 5、set 4、pack 3、fake_player 3。

最大文件：`Palette.java` 1070、`RegHelper.java` 951、`ConfigBuilder.java` 725、`neoforge/.../RegHelperImpl.java` 626、`MthUtils.java` 610、`Utils.java` 575、`SoftFluidStack.java` 561、`SoftFluidTank.java` 538、`FakeServerLevel.java` 534、`WoodType.java` 527。

## 3. 入口与注册

- common 逻辑入口：`common/.../core/Moonlight.java:73 commonInit()`（无 @Mod 注解，被两端调用），按固定顺序初始化：配置 → BlockSet 定义 → 两个数据注册表 → 网络 → 命令 → 动态资源 → 村民 AI → 地图标记 → SoftFluid；再用 `PlatHelper.addCommonSetup/addReloadableCommonSetup/addServerReloadListener` 注册生命周期回调。
- NeoForge：`neoforge/.../platform/MoonlightForge.java:59 @Mod(Moonlight.MOD_ID)`，构造器里 `RegHelperImpl.runTasksOnInit()` → `Moonlight.commonInit()` → 事件总线注册 → `ModLootModifiers/ModIngredientTypes/ResourceConditionsBridge`。
- Fabric：`fabric.mod.json` entrypoint `net.mehvahdjukaar.moonlight.platform.MoonlightFabric`（+ `MoonlightFabricClient`、modmenu 入口）。
- 注册框架**不用** DeferredRegister/Registrate，而是自研 `RegHelper`（`api/platform/RegHelper.java`）：100+ 个 `registerBlock / registerBlockWithItem / registerItem / registerBlockEntityType / registerPOI / registerMenuType / registerDataPackRegistry / registerWorldSavedData` 等静态重载，返回 `RegSupplier`/`OptRegSupplier` 包装。新增注册类型只需加一个静态方法 + 各加载器一份实现。

```java
// api/platform/RegHelper.java:101
@PlatformImpl
public static <T, E extends T> RegSupplier<E> register(
        ResourceLocation name, Supplier<E> supplier, ResourceKey<? extends Registry<T>> regKey) {
    throw new AssertionError();   // 实现由 candlelight 注解处理器生成到各加载器
}
```

## 4. 核心系统（按学习价值排序）

**4.1 多加载器平台抽象（`@PlatformImpl` 自动生成实现）**
`RegHelper/PlatHelper/NetworkHelper/MoonlightEventsHelper/ExtraModelData` 全部写成 `@PlatformImpl` 的"抛 AssertionError 的静态桩"，具体实现由自家 Gradle 插件 `net.mehvahdjukaar.candlelight` 在编译期生成/校验到 `fabric|neoforge` 的 `*Impl` 类（26 个文件带 `@PlatformImpl`）。`core/Moonlight.java:199 assertInitPhase()` / `205 isInitPhase()` 还主动做加载阶段校验：在 Forge 上误在 client/server 初始化器里调用注册就抛错。

**4.2 动态资源/数据包生成（`api/resources`, 46 文件）**
`DynamicResourcesProvider`（`api/resources/pack/DynamicResourcesProvider.java`）是新一代入口：构造时指定 `PackType` + `PackGenerationStrategy`，`packResources`（`IEditablePackResources`）承载内容，`createPack()` 用 `Pack.readMetaAndCreate` 挂到 `Pack.Position.TOP`。`reload()` 里 `needsToRegenerate()` 决定"清空重生成"还是"用磁盘缓存（`initializeIfValid()`）"；生成管线把任务切成 `ResourceGenTask`（`BiConsumer<ResourceManager, ResourceSink>`），用 `CompletableFuture` 并发跑后 `ResourceSink.acceptSinks()` 合并——并发开关是 `CommonConfigs.MULTI_THREADED_GENERATION`（`CommonConfigs.java`）。dev 环境自动 `dumpToDisk("debug/generated_resource_pack")`。旧的 `DynResourceGenerator`/`DynamicResourcePack` 已 `@Deprecated(forRemoval)`。配套工具极多：`StaticResource`、`ResType`、`LangBuilder`、`BoxedModelBuilder`、`TextureImage`/`Respriter`/`Palette`（含 `api/util/math/kmeans/KMeans` 做调色板量化）、`ParticleUtil`。

**4.3 BlockSetAPI：跨 mod 方块家族（`api/set`）**
`BlockType`（`api/set/BlockType.java:30`）用 `BiMap<String,Object> children` 存"planks/log/slab/boat…"等命名子对象，提供 `addChild/getChild/getChildKey/changeBlockType/changeItemType/getAppendableIdWith`；`BlockTypeRegistry` 支持 `addFinder/addRemover/finalizeAndFreeze/buildAll`，即第三方 mod 可"事后追加"一个新木材种类并让所有已注册的方块自动参与。`WoodType`/`LeavesType` 是内置实例，`BlockSetInternal` 在 `Moonlight.commonInit()` 里注册定义。这是 Moonlight 最具原创性的子系统。

**4.4 SoftFluid 虚拟流体（`api/fluids`）**
用数据包注册表 `moonlight:soft_fluid`（`SoftFluidRegistry.KEY`）描述"瓶/碗装的任意流体"，不占用真实 Fluid。`SoftFluid` 持 still/flowing 贴图、`FluidContainerList`（容器↔流体映射分类）、`equivalentFluids`、`FoodProvider`、tint 方法、`Capacity`（BOTTLE/BOWL/BUCKET 计数）。`SoftFluidStack`(561 行)/`SoftFluidTank`(538 行) 复刻 `ItemStack`/`FluidTank` 的 API，客户端用 `ClientBoundFinalizeFluidsMessage` 同步，另有 `FluidOffer`（类 ItemStack 的 offer/交易）与方块侧 `ISoftFluidProvider/ISoftFluidConsumer/ISoftFluidTankProvider` 接口。

**4.5 数据驱动村民交易（`api/trades`）**
`ItemListingManager`（`api/trades/ItemListingManager.java:35`）继承 `SimpleJsonResourceReloadListener`，注册在 `PlatHelper.addServerReloadListener(..., Moonlight.res("villager_trade"))`；交易类型进自定义注册表 `VILLAGER_TRADES_REGISTRY`，`ModItemListing` 是带 `MapCodec` 的接口，内置 `simple / remove_all_non_data / no_op / villager_type_variant` 四种编解码器。写入时通过 `addTrade/mergeArrays` 把数据包交易与硬编码交易按等级合并。

**4.6 数据驱动地图标记（`api/map`）**
`MapDataRegistry` + `MLMapMarker`/`MLMapDecoration`/`MLMapDecorationType`，在 `MapItemSavedData` 上挂自定义数据（靠 `core/mixins/MapDataMixin.java` 注入 `locked/scaled/tickCarriedBy` 并实现 copy-on-scale），方块/结构自动生成标记，支持 `addDynamicClientMarkersEvent/addDynamicServerMarkersEvent` 动态标记与 BiomeVariant。

**4.7 配置系统（`api/platform/configs`）**
`ConfigBuilder` 流式 DSL：`define/defineSlider/definePercentage/defineItem/defineBlock/defineRange/defineVec3/defineEnum/defineDropdown/defineRegex/defineColor/defineList/defineItemList/defineJson/defineBean/defineObject(SchemaCodec)`，配合 `comment/push/pop/pushFeature/icon/worldReload/gameRestart`。类型 `ConfigType.COMMON_SYNCED`，各加载器实现 `ModConfigHolder`（`ForgeConfigHolder`/`FabricConfigHolder`/`ForeignConfigHolder` 桥接 YACL、Cloth Config、Configured），同步走 `SyncConfigsMessage`。自带原生配置界面（`core/client/config/`30 个类）。

**4.8 模型数据扩展与假世界/假玩家**
`ExtraModelData`/`ModelDataKey`/`IExtraModelDataProvider`（BE 实现 `addExtraModelData`，数据变化调 `requestModelReload`）配合 `CustomBakedModel`/`CustomGeometry`/`NestedModelLoader`/`BakedQuadBuilder`/`BakedQuadsTransformer` 做动态烘焙模型。`api/misc/fake_level/FakeServerLevel.java:64`（继承 ServerLevel，534 行）用于在结构生成/逻辑里安全地 tick 实体；`core/fake_player/` 提供 `FakeGenericPlayer`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`NetworkHelper.addNetworkRegistration(Consumer<RegisterMessagesEvent>, int version)`；消息实现 `Message extends CustomPacketPayload` 并自定 `write(RegistryFriendlyByteBuf)` + `handle(Context)`，用 `Message.makeType(id, decoder)` 生成 `TypeAndCodec`。`ModNetworking.init()` 注册 11 个消息（`event.registerClientBound/ServerBound/Bidirectional`）。有 `markOptional(type)` + `canSendToPlayer/serverHasChannel` 做可选通道，发送侧提供 12 个 `sendToAllClientPlayers*`（范围/粒子范围/追踪实体/追踪区块）辅助方法。
- **数据驱动**：3 个数据包注册表（SoftFluid / 地图标记 / 村民交易）+ `RegHelper.registerDataPackRegistry(id, codec, networkCodec)` 供外部注册；`RegistryAccessJsonReloadListener` 统一跑 reload；`WorldSavedDataType` + `ClientBoundSyncWorldDataMessage` 做可同步的世界存档数据。
- **配置**：见 4.7。
- **datagen**：无标准 `DataGenerator` 用法；Moonlight 走"运行时动态生成资源包"（4.2）代替 datagen，并提供 `DynServerResourcesGenerator`/`IDebugDumpable` 把生成结果落盘到 `debug/` 目录。

## 6. Mixin

共 **98 个 mixin 类**。配置三份：`common/src/main/resources/moonlight-common.mixins.json`（包 `...core.mixins`）、`fabric/src/main/resources/moonlight.mixins.json`、`neoforge/src/main/resources/moonlight.mixins.json`（包 `...core.mixins.platform`）；NeoForge 的 `neoforge.mods.toml` 里显式声明两个 config。未配置 refmap 插件，用 `compatibilityLevel: JAVA_17`。

- 条件加载：`plugin = ...core.mixins.MixinPlugin`，继承 `api/misc/SimpleMixinPlugin.java:12`——用 ASM 直接读目标 mixin 类的 `ClassNode.invisibleAnnotations`，发现 `@OptionalMixin(clazz, needsClass)` 就判断该类是否存在，从而实现**"按依赖类是否存在决定是否应用 mixin"**，无需为每个可选 mod 建子 config。
- 代表性 hook：`MapDataMixin.java:200/210/232` → `@Inject(method="locked"/"scaled", at=@At("RETURN"))`、`tickCarriedBy` TAIL；`VillagerMixin.java:26` → `Villager#registerBrainGoals` RETURN（注入脑任务）；`PistonBlockEntityMixin.java:84/94/107` → `PistonMovingBlockEntity#tick/finalTick` 的 `INVOKE` 点（`Level#neighborChanged`、`Block#updateOrDestroy`）；`BlockStateBaseMixin.java:17` → `@ModifyReturnValue("hasBlockEntity")`；`ServerPlayerMixin.java:22` → `@WrapOperation("<init>")` 改 `adjustSpawnLocation`；`ItemInHandRendererMixin.java:21/37` → `renderArmWithItem` 接入第一/第三人称物品动画。另有 5 个 accessor/accesswidener（`moonlight.accesswidener`、`META-INF/accesstransformer1.cfg`）。

## 7. 值得学的 5 条具体做法

1. **接口桩 + 注解处理器生成平台实现**：`@PlatformImpl` 打在一行 `throw new AssertionError()` 的静态方法上，实现放到各加载器 `*Impl` 类，common 代码零 `if (loader == ...)`。文件：`api/platform/RegHelper.java:101`、`api/events/MoonlightEventsHelper.java`。适用：任何多加载器库模组。
2. **用 ASM 注解驱动 mixin 条件加载**：`@OptionalMixin` + `SimpleMixinPlugin` 按"依赖类是否存在"开关 mixin，比 `mod_loaded` 更精确、比多份 mixin config 更省事。文件：`api/misc/SimpleMixinPlugin.java:25`。适用：可选联动 mixin。
3. **动态资源生成带磁盘缓存与策略解耦**：`PackGenerationStrategy`（`GlobalCached*Strategy` 系列）决定"每次重生成 / 读缓存 / 缓存失效才生成"，并把 dev 生成结果 dump 到 `debug/generated_resource_pack` 便于肉眼核对。文件：`api/resources/pack/DynamicResourcesProvider.java`、`api/resources/pack/GlobalCachedFolderStrategy.java`。适用：运行时造贴图/模型/配方。
4. **"子物件 BiMap"表达方块家族**：`BlockType.children` 用 `BiMap<String,Object>` 把 `planks/slab/boat` 之类命名槽位与真实对象双向绑定，于是"把 A 木种的台阶换成 B 木种"只需 `changeBlockType(current, from, to)`（`api/set/BlockType.java:288-323`）。适用：木/叶/石等成套变体系统，也适合做 Create 风格的"材质套件"。
5. **注册表数据 + 合并语义**：`ItemListingManager` 把数据包定义与硬编码定义按等级 `mergeArrays`（支持 `add=false` 覆盖/删除），并给 `no_op`/`remove_all_non_data` 这类"占位+清空"编解码器（`api/trades/ItemListingManager.java:181-200`）。适用：任何"原版内容 + 数据包可改"的需求。

## 8. 公开 API / 外部 mod 接入方式

- 公开包：`net.mehvahdjukaar.moonlight.api.**`（`core.**` 标注 `@ApiStatus.Internal`）。常用入口：`api/platform/PlatHelper`、`api/platform/RegHelper`、`api/platform/network/NetworkHelper`、`api/set/BlockSetAPI`、`api/events/MoonlightEventsHelper`、`api/resources/pack/DynamicResourcesProvider`、`api/client/model/ExtraModelData`、`api/util/Utils`/`MthUtils`。
- 扩展点以 `I*` 接口形式散布：`IWashable/IRotatable/IRecolorable/ISoftFluidProvider/ILeftClickReact/IFirstPersonSpecialItemRenderer/IThirdPersonSpecialItemRenderer/IItemDecoratorRenderer/IExtraModelDataProvider/IExtraClientSpawnData/IControllableVehicle/IWaxable/IFlammable/IPistonMotionReact` 等（`api/block`、`api/item`、`api/entity`、`api/client`）。
- 事件：`SimpleEvent` + `MoonlightEventsHelper.addListener(consumer, IxxxEvent.class)`（Forge 上也可直接 `@SubscribeEvent` 订阅同名平台事件，平台实现类在 `*/api/events/platform/`）；另有 `api/misc/*` 的 DI 式工具 `SidedInstance`、`HolderRef`、`DynamicHolder`、`TField/TMethod`（反射缓存）。
- 联动检测：`core/CompatHandler.java`（静态布尔 + `classExists()` 反射探测 + 版本比较，含 `SABLE`），`core/integration/`（Iris/ModernFix/Polymer/MapAtlas/Sable）与 `api/integration/*`（YACL/Cloth/Configured/ModMenu）。
- 动态注册回调：`BlockSetAPI.addDynamicBlockRegistration(modId, event, Registry)` / `RegHelper.registerInBatch(registry, consumer<Registrator>)` / `RegHelper.addItemsToTabsRegistration` / `addBlocksToPOI` / `registerCompostable/registerItemBurnTime`，使依赖者无需知道加载器即可在注册窗口期插入内容。
- 已知限制：许可证非开源（禁止竞争性整合）；`gradle.properties` 未给 `common` 侧 mod 元数据，构建强依赖作者自研的 `possible-triangle` 与 `candlelight` 插件，外部无法直接复刻其构建流程。
