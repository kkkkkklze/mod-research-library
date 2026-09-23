# glisco03/owo-lib 源码分析报告

> 快照说明：本快照 **未包含** `src/main/resources/fabric.mod.json` 与 `LICENSE`（`build.gradle:33` 的 `processResources` 会对 `fabric.mod.json` 做 version 展开，说明原仓库中存在该文件）。入口点信息由 `Owo.java` / `client/OwoClient.java` 推断。

## 1. 基本信息

- Mod 名：oωo（owo-lib），mod_id = `owo`（`src/main/java/io/wispforest/owo/Owo.java:24`）；sentinel 中以 `owo-impl` 作为"实现已存在"判定（`owo-sentinel/.../OwoSentinel.java:35`）
- 作者/组织：glisco（glisco03），wisp-forest
- 目标版本：**Minecraft 1.21.11 + Fabric**（`gradle.properties`：loader 0.18.2、fabric-api 0.141.2+1.21.11）；mod_version 0.13.0，group `io.wispforest`
- Gradle：`net.fabricmc.fabric-loom-remap` 1.15-SNAPSHOT + java + maven-publish；Java 21；`accessWidenerPath = src/main/resources/owo.accesswidener`（v2 named）；多工程 `include 'owo-sentinel'`，另有独立 Kotlin DSL 工程 `braid-reload-agent`
- 编译依赖（`build.gradle`）：Fabric API；**自带并 Jar-in-Jar 打包** `io.wispforest:endec:0.1.12` + endec 的 netty/gson/jankson 格式模块 + `blue.endless:jankson:1.2.2` + `com.github.kdl-org:kdl4j:1.0.1`；compileOnly 接 REI 21.9.812、EMI 1.1.18、ModMenu 17.0.0-alpha.1、`server-translations-api`。**endec 是它自己的序列化底座**，也是它对外 API 的一部分

## 2. 源码规模与包结构

实测：仓库共 **718 个 .java**；`src/main/java` **646 个文件 / 55865 行**；testmod 3383 行。

顶级包（`io/wispforest/owo/`）文件数：braid 294、ui 103、mixin 101、config 30、util 28、serialization 16、registration 10、client 10、itemgroup 9、text 7、network 7、compat 7、command 6、particles 4、ops 4、renderdoc 3、moddata 2、ext 2、blockentity 2。

三级细分：`ui/component` 21、`ui/core` 19、`ui/event` 12、`ui/util` 11、`ui/renderstate` 10、`ui/container` 9、`ui/base` 8、`ui/parsing` 6、`ui/hud` 3、`ui/layers` 2、`ui/inject` 2；`braid/widgets` 187、`braid/core` 41、`braid/framework` 38、`braid/util` 16、`braid/animation` 9、`braid/display` 3。

最大文件：`serialization/CodecUtils.java` 740、`braid/core/AppState.java` 684、`ui/core/UIComponent.java` 657、`network/OwoNetChannel.java` 605、`braid/widgets/textinput/TextInput.java` 559、`RangeSlider.java` 508、`config/ui/ConfigScreen.java` 484、`itemgroup/OwoItemGroup.java` 464。

## 3. 入口与注册

`Owo implements ModInitializer`（`Owo.java:22`）：注册 LootOps、`CustomTextRegistry.register("index", InsertingTextContent.CODEC)`、`MenuNetworkingInternals.init()`、缓存 Server 实例；`DEBUG` 由 `-Dowo.debug` 覆盖开发环境默认值（`:39-48`）。
`OwoClient implements ClientModInitializer`（`client/OwoClient.java:26`）：`ModDataLoader.load(OwoItemGroupLoader.INSTANCE)`、把 `UIModelLoader` / `NinePatchTexture.MetadataLoader` 挂成客户端资源重载监听、`OwoUIPipelines.register()`、`RenderPipelines.register(BraidDisplay.PIPELINE)`、`OwoConfigCommand::register`。

**不使用 DeferredRegister/Registrate**，而是自研反射注册树：`registration/reflect/AutoRegistryContainer`（接口）→ `FieldProcessingSubject` / `SimpleFieldProcessingSubject` → `FieldRegistrationHandler.register(Class, namespace, recurseIntoInnerClasses)`（`FieldRegistrationHandler.java:65`）扫描 public static 字段并递归内部类，配套 `@AssignedName` / `@RegistryNamespace` / `@IterationIgnored`。跨表延迟逻辑由 `registration/RegistryHelper.java:19` 提供：`runWhenPresent(Identifier, Consumer<T>)` 基于 Fabric `RegistryEntryAddedCallback` 在目标条目出现后执行；`ComplexRegistryAction.Builder.create(Runnable).entry(id)` 表达"多个前置条目齐备才执行"。

## 4. 核心系统

**① 网络（`network/OwoNetChannel.java` 605 行 + `OwoHandshake.java` 315 行）**
- 数据包就是一个 `record`；`registerClientbound/registerServerbound(Class<R extends Record>, ChannelHandler)` 默认用 `RecordEndec.create(builder, messageClass)` 反射生成编解码器（`:198-226`），可用 `registerClientboundDeferred` 先占位后补 endec。
- 一个通道注册 **两个 payload type**（`PayloadTypeRegistry.playC2S/playS2C`，`:153-154`），消息用 `Endec.dispatched(...)` 以 `VAR_INT` 做索引分派：clientbound 存负索引、serverbound 存正索引（`:139-151`），同一 record 可双向注册。
- handler 索引存在 `Int2ObjectMap<IndexedEndec>` + `Reference2IntMap<Class<?>>`，运行时按消息 class 反查，避免反射查找。
- `OwoHandshake` 在 configuration 阶段交换通道哈希：required 通道必须双方一致，optional 只做交集过滤（`:177-266`），因此**注册必须两端都做，否则握手直接断连**。

**② 配置（`config/`，30 文件）**
- `config/ConfigAP.java:24` 是编译期注解处理器，用文本模板（`:26-73`）从 `@Config(name, wrapperName)` 模型类生成 `XxxConfig extends ConfigWrapper<Model>`，含字段访问器、`Keys` 常量类与 `subscribeToXxx`。
- `ConfigWrapper<C>`（398 行）以 Jankson + `ReflectiveEndecBuilder` 为核心，要求模型类有 0 参构造（`ReflectionUtils.requireZeroArgsConstructor`），选项展开成 `LinkedHashMap<Option.Key, Option>`，`Option.Key` 是 `String[] path` 因此天然支持 `@Nest` 嵌套。
- `Option.SyncMode` 三档 `NONE / INFORM_SERVER / OVERRIDE_CLIENT`（`config/Option.java:285-300`）；只要有任一 option 非 NONE，构造时即 `ConfigSynchronizer.register(this)`。
- `config/ConfigSynchronizer.java` 用 `owo:config_sync` 通道，`toPacket` 只打包 ordinal ≥ 目标模式的 option（`:76-95`），每个 option 写进 `FriendlyByteBuf`；客户端值按 `Connection` 存进 `WeakHashMap`，服务端 `getClientOptions(player, config)` 取回（`:59-74`）。
- `@Modmenu(modId, uiModelId)` 会在客户端自动注册 `ConfigScreenProviders` → `ConfigScreen.createWithCustomModel(UIModel)`（`ConfigWrapper.java:104-110`）；约束注解丰富：`@RangeConstraint/@RegexConstraint/@PredicateConstraint/@WithAlpha/@RestartRequired/@ExcludeFromScreen/@Hook/@Expanded/@SectionHeader`。

**③ owo-ui 声明式 UI（`ui/`，103 文件）**
- 入口 `OwoUIAdapter.create(Screen, BiFunction<Sizing, Sizing, R>)`：自己 `addRenderableWidget` 进 Screen 并接管焦点（`OwoUIAdapter.java:76-84`）；`inflateAndMount()` 先 `inflate(Size)` 再 `mount(null, x, y)`（`:109-112`）。
- `ui/core/UIComponent.java` 定义 width/height/x/y/**baseX/baseY**（DraggableContainer 等需要独立布局基准点）、`margins/positioning/cursorStyle/tooltip` 等可动画属性（`AnimatableProperty`），并统一实现 `parseProperties(UIModel, Element, Map)`（`:478-493`）解析 XML。
- XML 模型：`ui/parsing/UIModelLoader.java:29` 是资源重载监听，模型缓存于 `LOADED_MODELS`；`get(id)` 在 DEBUG 下读 `config/owo_ui_hot_reload_locations.json5` 做**热重载**（`:53-64`）。`UIModel` 分 `<components>` 与 `<templates>`，模板支持跨模型引用 `name@namespace:model`（`UIModel.java:251-258`）。
- 容器：StackLayout / FlowLayout / GridLayout / ScrollContainer / CollapsibleContainer / OverlayContainer / DraggableContainer（`ui/container/`）；给外部用的基类：`BaseOwoScreen` / `BaseUIModelScreen` / `BaseOwoContainerScreen` / `BaseParentUIComponent`（`ui/base/`）。
- 注入原版界面：`Layers.add(rootMaker, instanceInitializer, screenClasses...)`（`ui/layers/Layers.java:52`）与 `Hud.add(Identifier, Supplier<UIComponent>)`（`ui/hud/Hud.java:44`）。

**④ owo-braid（`braid/`，294 文件，0.13 新体系）**
- 三层对象模型：`Widget`（framework/widget）→ `WidgetProxy`（framework/proxy：Stateless/Stateful/Composed/Inherited + Multi/Single/OptionalChild）→ `WidgetInstance`（framework/instance），即 React 式 element/component/instance 分离，靠 diff 复用实例。
- 运行时根 `braid/core/AppState.java:42`（684 行）持有 root BuildScope、动画与调度回调队列、hover/drag/scroll 状态、`BraidEventStream` 键鼠流与 `BraidInspector`。
- `braid/core/BraidScreen.java:17` 由 AppState 驱动，提供 `maybeOf(BuildContext)` 静态查找；widgets 覆盖 flex/grid/slider/textinput/scroll/splitpane/window/inspector/recipeviewer。
- 与 owo-ui 互操作：`braid/widgets/owoui/OwoUIWidget(+Wrapper)`、`braid/widgets/vanilla/VanillaWidget(+Wrapper)`。

**⑤ 序列化桥（`serialization/`，16 文件）**
`serialization/CodecUtils.java`（740 行）以 endec 为中枢，在 endec ↔ DFU `Codec`/`StreamCodec`/`NbtOps`/Gson/Jankson/EDM/ByteBuf 之间互转，配套 `mixin/serialization/*` 一组 accessor/invoker（`DelegatingOpsAccessor`、`RegistryOpsAccessor`、`FriendlyByteBufMixin`、`TagValueInput/OutputMixin`）打通原版管线 —— 这是 owo 全部数据类能与原版交互的基础。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 ①；JSON5 与 NBT 全走 endec。
- 数据驱动：`moddata/ModDataLoader.java:36` 从 `gameDir/moddata` 加载 json5（客户端用于 `OwoItemGroupLoader`）；item group 支持 `data/<ns>/item_group_tabs/*.json5` 扩展（testmod 有 4 个样例）。
- 配置：`.json5` 文件（Jankson，`JsonGrammar.JANKSON`）+ 可选的 C/S 同步（见 ②）。
- 关键数据格式决策：**全仓库资源统一用 `.json5`**（testmod 的 assets/data 全是 json5），靠 `mixin/extension/json5/*`（`LanguageReaderMixin`、`MultiPackResourceManagerMixin`、`FallbackResourceManagerMixin`、`FileToIdConverterMixin`）让原版资源管线接受 json5 与注释。
- datagen：**无**（未发现 datagen 相关包或类）。

## 6. Mixin

配置：`src/main/resources/owo.mixins.json`（package `io.wispforest.owo.mixin`，`compatibilityLevel JAVA_16`，`injectors.defaultRequire=1`），分 `mixins` 55 条 / `client` 47 条 / `server` 1 条（`MainMixin`）。

- `mixin/braid/ScreenMixin.java:14`：`@Mixin(value = Screen.class, priority = 1100)`，`@Inject(method = "renderWithTooltipAndSubtitles", at = @At(value = "INVOKE", target = "Screen;render(...)", shift = AFTER))` 之后渲染 braid 层，并在 Screen 上挂 `OwoScreenExtension` 存 `braidLayersState`。
- `mixin/Copenhagen.java:28`：`@Mixin(OreFeature.class)`，`@Inject` 到 `doPlace` 的 `LevelChunkSection.setBlockState` INVOKE 点（`locals = CAPTURE_FAILHARD`）与 TAIL。
- `mixin/ConnectionMixin.java:11`：`@Mixin(Connection.class)`。`mixin/serialization/FriendlyByteBufMixin.java:12`：`@Mixin(FriendlyByteBuf.class)`。
- 其余成组的：`serialization/**`（accessor/invoker 为主）、`itemgroup.CreativeModeInventoryScreen{Mixin,Accessor}`、`text.TranslatableContentsMixin`（富文本翻译）、`ui.layers.*`、`ui.access.*`（13 个 accessor）。
- `owo.accesswidener` 对外开放：`Screen.addRenderableWidget`、`CreativeModeTab` 构造及 `$Output/$ItemDisplayBuilder`、`GuiGraphics$ScissorStack` 与 `setTooltipForNextFrameInternal`、`AbstractContainerScreen.renderSlotHighlight{Back,Front}` 与 `renderFloatingItem`（可被下游 mod 直接 override，见 AW 的 `extendable`）。

## 7. 值得学的 5 条具体做法

1. **编译期生成配置包装类**：`@Config` 模型类 → `ConfigAP` 文本模板生成 wrapper + `Keys` + 订阅方法，把反射开销挪到编译期。适用：任何"注解模型 + 类型安全访问器"的场景。`config/ConfigAP.java:26-73`
2. **反射式泛用注册器**：`FieldRegistrationHandler.register` 扫 public static 字段并递归内部类，配 `@RegistryNamespace/@AssignedName`，不为每张注册表写样板。`registration/reflect/FieldRegistrationHandler.java:65`
3. **record 即包 + 索引分派**：一个通道用 `Endec.dispatched` 按 VAR_INT 索引复用 payload type，clientbound 用负索引，同一 record 双向注册。`network/OwoNetChannel.java:139-175`
4. **配置握手分级校验**：`OwoHandshake` 在 configuration 阶段比对 required/optional 通道哈希，缺包时给出可读断连原因而不是崩栈。`network/OwoHandshake.java:177-266`
5. **把 json5 变成一等数据格式**：用一组资源管线 mixin 让原版 loader 直接读 `.json5`，全仓库数据/资源/语言文件都保留注释。`mixin/extension/json5/`

## 8. 公开 API（库/前置类）

- 包路径：`io.wispforest.owo.{ui, braid, config, network, registration, serialization, util, itemgroup, client.screens}`；发布到 `maven.wispforest.io`。
- 接入方式（README）：`modImplementation "io.wispforest:owo-lib:<ver>"`；用 owo-config 时额外 `annotationProcessor "io.wispforest:owo-lib:<ver>"`；`include "io.wispforest:owo-sentinel:<ver>"` 用于缺库时提示下载（`owo-sentinel/.../OwoSentinel.java:34-52`，有 GUI 与 headless 两套降级路径）。
- UI 扩展点：实现 `UIComponent` / `ParentUIComponent` 自定义组件（`UIComponents` 工厂给出内置实现）；`OwoUIAdapter.create` / `OwoUIAdapter.createWithoutScreen` 嵌入任意上下文；`UIParsing` 的 factory 注册让自定义组件能写进 XML（`UIModel.java:203` 用 `UIParsing.getFactory`）；`Layers.add` / `Hud.add` 注入原版界面。
- 网络扩展点：`OwoNetChannel.create(Identifier)`（required）/ `createOptional` + `ChannelHandler<R, ClientAccess|ServerAccess>` + `addEndecs` 注册自定义类型。
- 注册扩展点：`AutoRegistryContainer` / `SimpleFieldProcessingSubject` 接口、`RegistryHelper.runWhenPresent`、`ComplexRegistryAction.Builder`。
- 配置扩展点：`@Config` + 13 个约束注解（`config/annotation/`）、`@Modmenu` 一键接 ModMenu 配置按钮、`Option` / `ConfigWrapper#options` 编程式访问。
