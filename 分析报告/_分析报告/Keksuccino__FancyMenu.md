# FancyMenu 源码分析报告

仓库根：`源码库\_参考仓库\_bulk\Keksuccino__FancyMenu`（`master` 分支只有 README/LICENSE/changelog，**源码在各版本分支**；本次分析检出分支 `1.21.1`，即 FancyMenu 3.9.12。1.20.1 对应 `v2-1.20.1-forge` 分支的 2.x 代码）

## 1. 基本信息

- Mod 名 FancyMenu / mod_id `fancymenu` / group `de.keksuccino.fancymenu` / 作者 Keksuccino / 版本 3.9.12（`gradle.properties`）。
- 目标：MC 1.21.1，Java 21；Fabric（Loom 1.9-SNAPSHOT、fabric-api 0.110.0+1.21.1、loader 0.16.10）与 NeoForge（neogradle 7.0.178、NeoForge 21.1.47、loader 2）双平台，`settings.gradle` 分 `common` / `fabric` / `neoforge` 三模块。
- 许可证：DSMSLv3.1（"DON'T SNATCH MA STUFF LICENSE"，源码可见但禁止搬运/再分发），`LICENSE.md`。
- 关键依赖（= 它的 API 边界）：`konkrete`（>=1.9.4，required，实为本 mod 的公共库：`de.keksuccino.konkrete.*` 被直接 import）、`melody`（required，客户端）、`watermedia`（视频）、`rinku`（>=3.0.4，内嵌浏览器）、`fancy_entity_renderer`（建议项）；`breaks` 里明确屏蔽 `fmextension_audio/video`、`drippyloadingscreen<3.0.0`、`rrls<4.0.1`（`fabric/src/main/resources/fabric.mod.json`）。构建侧：MixinExtras 0.4.1、`japng 0.5.3` 与 `animated-gif-lib` 通过 `include(implementation(...))` 内嵌（`fabric/build.gradle`）。所有描述符文件用 `${mod_id}` 等占位符，由根 `build.gradle:150-180` 的 `processResources expandProps` 展开。

## 2. 源码规模与包结构

- 1609 个 `.java` / 276,068 行（`git ls-files '*.java' | xargs wc -l`）；其中 `common` 1410、`fabric` 187（**约 189 个 JUnit5 单元测试在 `fabric/src/test/java`**）、`neoforge` 12。资源文件仅 245 个（字体 Noto Sans 多语、`assets/fancymenu/lang/*.json`）。
- 全部代码在单一命名空间 `de.keksuccino.fancymenu` 下（271 个目录）。二级主要包：`customization`（24 子包）、`util`（24 子包）、`mixin`、`networking`、`events`、`platform`、`commands`。
- 最大文件：`util/resource/resources/texture/afma/creator/AfmaEncodePlanner.java` 6681、`.../afma/creator/AfmaV2PlannerCore.java` 5212、`util/rendering/ui/icon/MaterialIcons.java` 4239、`customization/action/ui/ActionScriptEditorWindowBody.java` 3819、`util/rendering/ui/contextmenu/v2/ContextMenu.java` 3614、`util/properties/Property.java` 3371、`util/rendering/ui/pipwindow/PiPWindow.java` 2244。

## 3. 入口与注册

- 公共入口 `FancyMenu.java`：`init()` 按 `Services.PLATFORM.isOnClient()` 分客户端/服务端初始化（`FileTypes.registerAll()`、`TextColorFormatters.registerAll()`、浏览器与视频、`WebUtils.init()`），另有 `lateClientInit()`（`UIThemes.registerAll()`、自定义窗口图标/全屏、`CursorHandler.init()`、`CustomLocalsHandler.init()`、`ServerCache.init()`，`FancyMenu.java:47-101`）。
- Fabric：`fabric/.../FancyMenuFabric.java`（`implements ModInitializer`）→ `FancyMenu.init(); PacketsFabric.init();` + 客户端/服务端事件注册；NeoForge：`neoforge/.../FancyMenuNeoForge.java`（`@Mod(FancyMenu.MOD_ID)`）同构，只多传 `IEventBus` 给 `PacketsNeoForge.init(eventBus)`。
- 不使用 DeferredRegister/Registrate，全部是自建静态注册表：`ElementRegistry`、`ActionRegistry`、`PlaceholderRegistry`、`RequirementRegistry`、`PacketRegistry`、`MenuBackgroundRegistry`、`DecorationOverlayRegistry`。平台抽象用 `platform/Services.java` 的 ServiceLoader，描述文件在各模块 `META-INF/services/de.keksuccino.fancymenu.platform.services.IPlatformHelper`（内容分别为 `...platform.FabricPlatformHelper` / `...NeoForgePlatformHelper`），接口见 `platform/services/IPlatformHelper.java:15-90`。

## 4. 核心系统

1. **布局 DSL**：`customization/layout/Layout.java`（继承 `LayoutBase.java`）。`serialize()`（`Layout.java:109`）把布局写成 `PropertyContainerSet`（type=`fancymenu_layout`）+ 多个 `PropertyContainer`，段落类型有 `layout-meta` / `element` / `vanilla_button` / `menu_background` / `layer_group` / `scroll_list_customization` / `layout_action_executable_blocks`；`deserialize()`（`:261`）逐段解析并大量做旧格式兼容（`@Legacy` 标注的 `convertLegacyElements`、`convertLegacyVanillaButtonCustomizations`、`convertLegacyMenuBackground`）。生命周期由 `LayoutHandler.java` 管：`LAYOUT_DIR = config/fancymenu/customization`、`ASSETS_DIR = config/fancymenu/assets`（`:32-33`），递归读取 `*.txt`（`:88-90`）→ `PropertiesParser.deserializeSetFromFile`。
2. **文件格式**：`util/properties/PropertiesParser.java`——文本语法 `type = <类型>` + `容器名 {` / `  key = value` / `}`（`:122-139` 序列化、`:39-93` 解析，解析时去空格、`}` 缺失会告警并"泄漏式"收尾）；`stringifyFancyString`/`unstringify` 用 `$prop_line_break$` 等占位符把多行值压成一行。这是"人工可编辑 + 版本可迁移"的 DSL 基座。
3. **元素体系**：`customization/element/ElementRegistry.java`（`LinkedHashMap<String, ElementBuilder>`，重复注册仅告警并覆盖），构建器集中声明在 `customization/element/elements/Elements.java:33-58`（button / input_field / slider_v2 / checkbox / text_v2 / tooltip / ticker / player_entity / image / glsl_shader / json_model / splash_text / slideshow / rectangle_shape / circle_shape / cursor / progress_bar / audio_v2 / music_controller / dragger / browser / item / animation_controller / video / rinku_video 等 27 个）。扩展点是 `ElementBuilder<E extends AbstractElement, L extends AbstractEditorElement>`（`ElementBuilder.java:27-56`）：子类只实现 `buildDefaultInstance()` 与 `deserializeElement()`，通用字段（`instance_identifier`、`appearance_delay`、`fade_in`、`auto_sizing`…）由模板方法 `deserializeElementInternal()` 统一处理，并顺手把旧键名（`delayappearance`、`fadein`）迁移到新键。**运行元素与编辑器元素成对设计**，编辑器 UI 因此与运行时解耦。
4. **动作 / 可执行块 / 需求**：`customization/action/ActionRegistry.java`（identifier 禁止含 `:`，否则抛异常；`customization/action/actions` 下 64 个动作类），`ActionInstance` + `blocks/`（语句、条件、`GenericExecutableBlock`、`ExecutableBlockDeserializer`）组合成脚本化动作，`Layout` 里用 `layout_action_executable_blocks` 段存"打开/关闭界面时执行"；`customization/requirement/RequirementRegistry` + `RequirementContainer` 控制元素/布局是否生效（带 `requirementCachingDurationMs` 缓存开关）。
5. **占位符与资源加载**：`customization/placeholder/PlaceholderRegistry`（identifier + `getAlternativeIdentifiers()`）+ `PlaceholderParser.replacePlaceholders`。`util/resource/ResourceSupplier.java:102-131` 是核心：资源源是字符串（URL / 本地路径 / `namespace:path`），每次 `get()` 先解析占位符，与 `lastGetterSource` 不同就丢弃旧资源并回调 `onUpdateCurrent`（音频/视频会自动 stop），再按 `FileMediaType` 交给 `ResourceHandlers`；`getSourceWithPrefix()/getSourceWithoutPrefix()` 用 `ResourceSourceType` 前缀区分来源；`ResourceSource.isDispatchable()` 防御空占位符结果误注册成贴图导致整次资源重载失败（`:116-119` 注释）；`ClientResourceIndex` 维护资源包内 ResourceLocation 索引，`util/resource/preload` 做预加载。
6. **屏幕接管**：`customization/ScreenCustomization.java`（442 行）负责屏幕标识符（`ScreenIdentifierHandler`）、`config/fancymenu/customizablemenus.txt` 开关、黑名单规则 `ScreenBlacklistRule`、`reInitCurrentScreen()`；`customization/global`、`customization/layer`、`customization/panorama`、`customization/slideshow`、`customization/gameintro`、`customization/decorationoverlay`、`customization/widget`（vanilla 控件识别）等各自独立子系统。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：自研轻量协议，`networking/Packet.java` + `PacketCodec` + `PacketRegistry`（**注册阶段可冻结**：`PacketRegistry.endRegistrationPhase()`，之后注册直接抛异常，`PacketRegistry.java:20-25,51`），平台侧 `PacketsFabric` / `PacketsNeoForge` 落地；包按 `packets/{handshake, commands(closegui/opengui/layout/suggestions), entities, fmdata, placeholders, structure}` 分类；`networking/bridge/`（`BridgeChunkEncoder` / `BridgeChunkReassembler` / `BridgeProtocol` / `BridgeWireCodec` / `BridgeMessageSender`）做大数据分块传输；`ServerHandshakeNegotiationTracker` + `NetworkCapabilityLifecycle` + `OptionalPayloadSender` 处理能力协商与"对端不支持则不发送"。
- 数据驱动：布局/幻灯片/全景等全部是磁盘上的 `.txt` 属性文件；`customization/remote/`（`RemoteServerConnectionManager`、`JdkRemoteWebSocketTransport`、`InboundMessageBuffer` 等）支持从 FancyMenu 定制服务器（WebSocket）下发定向内容；`Options.java:122-123` 还内置了可选 **MCP server**（`mcp_server_enabled` / `mcp_server_port=48561`）供外部工具驱动。`customization/customlocals` 支持自定义本地化。
- 配置：`Options.java` 继承 `util/AbstractOptions`，用 Konkrete 的 `Config` 写 `config/fancymenu/options.txt`，每项是 `new Option<>(config, "key", 默认值, "分组")`（分组仅用于配置界面归类），构造器末尾 `syncConfig()` + `clearUnusedValues()`。
- datagen：未见（未确认，未见 `*DataProvider` 类）。

## 6. Mixin

- 配置：`common/src/main/resources/fancymenu.mixins.json`（`required:false`、`package: de.keksuccino.fancymenu.mixin.mixins.common`、`compatibilityLevel: JAVA_17`，client 列表含几十个 `IMixin*` 接口式 mixin 与 `Mixin*`）+ 平台各自 `fancymenu.fabric.mixins.json` / `fancymenu.neoforge.mixins.json`；`accessWidener: fancymenu.accesswidener`（common）。
- 插件：`mixin/FMMixinPlugin.java` 实现 `IMixinConfigPlugin`，`shouldApplyMixin()` 只有 `isKonkreteLoaded()`（反射 `Class.forName("de.keksuccino.konkrete.Konkrete")`）为真才应用，实现"缺失 Konkrete 时整体不注入"。
- 代表 hook：`mixin/mixins/common/client/MixinScreen.java`——`@WrapOperation` 包 `Screen.renderWithTooltip` 内的 `render`/`renderTooltip` 调用（`:61,68`）、`renderPanorama`、`renderBackground`、`renderMenuBackground`（`:102-156`），`@Inject(HEAD, cancellable)` 接管 `renderBlurredBackground` / `renderMenuBackgroundTexture`（`:85,148`），另有 `keyPressed` / `setInitialFocus` / `children` 的注入（`:179-209`）与 `IMixinScreen` 接口 mixin 暴露 getter 给 common 代码。

## 7. 值得学的 5 条做法

1. **多加载器骨架**：`platform/Services.java` 用 `ServiceLoader` + `META-INF/services/<接口全限定名>` 文本文件切换实现，common 只依赖接口（本仓库 fabric/neoforge 各一份 services 文件；Dynamic FPS 同款做法），适用任何双加载器模组。
2. **文本段落 DSL**：`PropertiesParser`（`type = x` + `名 { k = v }`）配 `PropertyContainerSet`/`PropertyContainer` 存复杂嵌套数据；代价是自研解析器，收益是玩家能手改、版本迁移只加 `upgrade/legacy` 分支（`Layout.java` 里成打的 `@Legacy` 方法）。
3. **注册表 + 冻结**：`ElementRegistry` / `ActionRegistry` / `PacketRegistry` 都是静态 `LinkedHashMap` + `register/getBuilder/hasBuilder`，网络表在启动后 `endRegistrationPhase()` 关闭写入（`PacketRegistry.java:51`）；适合需要被其它 mod 扩展的模组。
4. **模板方法 + 旧键名迁移**：`ElementBuilder.deserializeElementInternal()` 只让子类实现"自定义字段"，公共字段与历史字段兼容集中在一处（`ElementBuilder.java:56-140`），新元素类型接入成本很低。
5. **"字符串源 + 取用时解析"的资源模型**：`ResourceSupplier.get()` 每次比对 `lastGetterSource`，占位符变化即换资源并回调清理旧资源（`ResourceSupplier.java:102-131`），同一套代码支持 URL / 本地文件 / 资源包路径——很适合做数据驱动 UI/皮肤。
6. **测试放在 fabric 模块**：约 189 个 JUnit5 用例集中在 `fabric/src/test/java`，覆盖序列化、缓存、生命周期、并发（如 `PropertiesParserTest`、`LayoutLifecycleTest`、`BoundedWebResourceClientTest`），这是大型模组保持可改动的关键。

## 8. 扩展点（供外部接入）

`ElementRegistry.register(ElementBuilder)`、`ActionRegistry.register(Action)`、`PlaceholderRegistry.register(Placeholder)`、`RequirementRegistry`、`MenuBackgroundRegistry` / `DecorationOverlayRegistry`（背景与装饰覆盖层）、`PacketRegistry.register(PacketCodec)`（须在早期注册）；Mod 侧的共享库是独立的 Konkrete（`de.keksuccino.konkrete.*`），FancyMenu 硬依赖它并使用其 Config/MathUtils/StringUtils 等工具。
