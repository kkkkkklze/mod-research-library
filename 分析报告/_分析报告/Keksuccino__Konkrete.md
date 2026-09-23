# Konkrete 源码分析报告

> 分析对象：`Keksuccino/Konkrete` 分支 `1.21.1`（commit 6db382f）。**重要前提**：本地 `_bulk/Keksuccino__Konkrete` 的默认分支 `main`（114c3b8）只有 README/changelog/.github，**不含源码**；源码在 `1.21.1`、`1.20.1`、`legacy-*` 等分支上。本报告取自 `1.21.1` 分支快照。

## 1. 基本信息

- Mod 名：Konkrete / mod_id：`konkrete` / 作者：Keksuccino / 许可证：Apache-2.0 / 定位：`mod_description=Library for Keksuccino's mods`（FancyMenu 的库）
- 版本：`mod_version=1.9.9`，`group=de.keksuccino.konkrete`，`minecraft_version=1.21`
- 目标平台 **四个**（`gradle.properties` + 子工程）：`common` + `fabric`（fabric-loom 1.6-SNAPSHOT，loader 0.15.11，fabric-api 0.100.1+1.21）+ `forge`（ForgeGradle `[6.0.24,6.2)`，forge 51.0.5，sponge mixin 0.7-SNAPSHOT）+ `neoforge`（NeoGradle userdev 7.0.145，neoforge 21.0.20-beta）
- 编译依赖：`common/build.gradle:18-21` = `compileOnly mixinextras-common:0.3.2` + `compileOnly mixin:0.8.5`、`implementation jsr305:3.0.1`、`asm-tree:9.3`；fabric 侧额外 `modImplementation maven.modrinth:modmenu:11.0.0-beta.1`（仅开发环境）；forge 侧 `jarJar("mixinextras-forge")`（`forge/build.gradle:81`）
- 下游/关联：`fabric.mod.json` 的 `breaks` 写 `drippyloadingscreen<3.0.1`、`fancymenu<3.1.0`；`mods.toml` 声明 fancymenu `[3.1.0,)` optional

## 2. 源码规模与包结构（实测）

- 246 个 `.java` / **30477 行**；`common` 233、`fabric` 5、`forge` 4、`neoforge` 4
- **内置（vendored）第三方库占了 64%**：`konkrete/json/jsonpath` 87（Jayway JsonPath）、`konkrete/json/minidev` 52（json-smart，含 ASM bean 映射）、`konkrete/objecthunter/exp4j` 19（数学表达式求值）
- Konkrete 自身功能包：`konkrete/gui/content` 15、`konkrete/gui/screens` 7、`konkrete/mixin/mixins` 11、`konkrete/input` 6、`konkrete/resources` 5、`konkrete/rendering/animation` 4、`konkrete/properties` 3、`konkrete/localization` 3、`konkrete/config` 2、`konkrete/command` 2，以及根包 3
- 最大文件：`config/Config.java` 817、`json/minidev/.../JSONParserBase.java` 811、`JSONNavi.java` 767、`jsonpath/JsonPath.java` 757、`ValueNodes.java` 712、`rendering/GifDecoder.java` 703（Open Imaging 库）、`gui/screens/ConfigScreen.java` 642、`gui/content/AdvancedButton.java` 493

## 3. 入口与注册

- **没有任何内容注册**（无 DeferredRegister/无 Registry 注册）——它是纯客户端工具库
- common 侧只有 `de/keksuccino/konkrete/Konkrete.java`：`MOD_ID/MOD_VERSION(1.9.9)/MOD_LOADER = Services.PLATFORM.getPlatformName()`（:17-19）、`init()`（:24，打印内置库许可 + 探测 Optifine）、`onGameInitCompleted()`（:63：`SoundHandler.init()` → `initLocals()` → `PostClientInitTaskExecutor.executeAll()`）
- 三个加载器入口都只有一行 `Konkrete.init()`：`fabric/.../KonkreteFabric.java`（`fabric.mod.json` 的 `entrypoints.main`）、`neoforge/.../KonkreteNeoForge.java:9-12`（`@Mod(Konkrete.MOD_ID)` 构造器注入 `IEventBus`）、`forge/.../KonkreteForge.java`
- 平台抽象：`platform/Services.java:16-17` 用 `ServiceLoader.load(...).findFirst().orElseThrow()` 加载 `IPlatformHelper`（isModLoaded/getModVersion/isOnClient/isDevelopmentEnvironment/getKeyMappingKey…）与 `IPlatformCompatibilityLayer`；三个平台各自提供 `fabric/forge/neoforge` 下的 `*PlatformHelper`/`*CompatibilityLayer` + `META-INF/services` 文本文件
- 对外挂载点：`Konkrete.addPostClientInitTask(modId, Runnable)`（:92，内部 `PostClientInitTaskExecutor`）——下游 mod 用它把初始化推迟到游戏完全加载后

## 4. 核心系统

**(a) 高级 GUI 控件**（`gui/content/`）：`AdvancedButton`(493)、`AdvancedImageButton`、`AdvancedTextField`、`ExtendedEditBox`、`ContextMenu`、`DropdownMenu`、`HorizontalSwitcher`、`IMenu`；配套 `handling/{AdvancedWidgetsHandler, IAdvancedWidgetBase}`（键盘/字符事件回调）。设计点：**不用原版事件系统**，鼠标状态来自静态 `input/MouseInput`（getMouseX/isLeftMouseDown），滚动条 `scrollarea/ScrollArea.java:44-65` 自己算 grabber 位置并用 `RenderSystem.enableScissor((int)(x*scale),(int)(win.getHeight()-sciBottom*scale),…)` 做 GUI scale 换算后裁剪

**(b) 弹窗系统**（`gui/screens/popup/`）：`Popup`/`PopupHandler` 统一管理，预置 `YesNoPopup`、`TextInputPopup`、`NotificationPopup`、`FilePickerPopup`（自带文件选择器，配 `assets/konkrete/filechooser/*.png` 图标）

**(c) 外部贴图/动态纹理管线**（`resources/`）：接口 `ITextureResourceLocation` + `ExternalTextureResourceLocation.java:51 loadTexture()`——从磁盘文件或 `InputStream` 用 `NativeImage.read` 构造动态纹理并注册进 `TextureManager`；JPEG 走 `convertJpegToPng` 且强制 warn（:67）；另有 `WebTextureResourceLocation`（网络图片）、`SelfcleaningDynamicTexture`、`TextureHandler`。这是 FancyMenu"用户自定义背景图/自定义图片"的底层

**(d) 动画渲染**（`rendering/`）：`GifDecoder`(703，内置 GIF 解码，来自 Open Imaging) + `animation/{IAnimationRenderer, AnimationRenderer, ExternalTextureAnimationRenderer, ExternalGifAnimationRenderer}` + `RenderUtils`。注意 `AnimationRenderer` 已 `@Deprecated(forRemoval = true)` 且 `render()` 是空实现（:45-50），由 External* 子类接管

**(e) 自定义配置 / 本地化 / 属性数据**：`config/{Config(817), ConfigEntry}` 是自研文本配置系统（`EntryType`：String/Boolean/数字），配 `gui/screens/ConfigScreen.java`(642) 自动生成配置界面；`localization/{Locals, LocalizationPackage, LocaleUtils}` 使用自定义 `.local` 文本格式（`key = value`、`{}` 顺序占位符、缺 key 递归回退 `en_us`，`Locals.java:104-136`），首次运行把 jar 内 `konkrete:locals/{en_us,de_de,pl_pl,pt_br}.local` 复制到 `config/konkrete/locals`（`Konkrete.java:77-87`）；`properties/{PropertiesSerializer, PropertiesSection, PropertiesSet}` 是 FancyMenu 的 `.properties`/section 数据格式

**(f) Vendored JSON/表达式栈**：`json/JsonUtils` + jsonpath/json-smart/exp4j 三个完整内置库（json-smart 用 ASM 动态生成 bean 存取器 `BeansAccessBuilder`），让下游无需额外前置即可做 `$.a.b[?(@.x>1)]` 式查询与数学表达式求值

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无**（全文无 CustomPacketPayload/网络注册类）
- **数据驱动**：`.local`（本地化）、`.properties`（`PropertiesSet`/`PropertiesSerializer`）、JSON（内置 jsonpath/json-smart）；运行时从 `config/konkrete/locals` 目录加载用户可改的本地化文件
- **配置**：自研 `Config` + `ConfigEntry`（非 NeoForge/Forge ConfigSpec），并有自动生成的 `ConfigScreen`
- **datagen：无**；`fabric.mod.json` 用 `${mod_id}` 等占位符，构建时由 root `build.gradle` 的 expandProps 替换（`gradle.properties` 头部注释要求所有字段同步到 expandProps）

## 6. Mixin

- 配置：`common/src/main/resources/konkrete.mixins.json`（`package de.keksuccino.konkrete.mixin.mixins`，`client` 11 个，`injectors.defaultRequire=1`，`refmap konkrete.refmap.json`，`plugin de.keksuccino.konkrete.mixin.KonkreteMixinPlugin`）；加载器各有一份 `konkrete.{fabric,forge}.mixins.json`，内容均为 `mixin/mixins/<loader>/client/MixinGameRenderer`；另有 `konkrete.accesswidener`（`accessible field AbstractWidget x/y`、`extendable method render`）与 forge 侧 `META-INF/accesstransformer.cfg`（NeoForge 侧自动读取同名文件，见 `neoforge/build.gradle` 注释）
- 代表性 hook（`grep @Mixin/@Inject` 实测）：
  - `client/MixinMinecraft.java:15-52` → `Minecraft#<init>`@RETURN、`tick`@HEAD、`setScreen`（`@At INVOKE Screen#added` 与 HEAD 两处）、`resizeDisplay`@HEAD
  - `client/MixinKeyboardHandler.java:13,24` → `keyPress`/`charTyped`，注入点均为 `@At INVOKE Screen#wrapScreenError`（+ `shift AFTER`）——把按键转发给 Konkrete 控件
  - `client/MixinMouseHandler.java:18,30` → `onScroll`@HEAD、`onPress`@HEAD
  - 接口式 mixin（`IMixin*`）：`AbstractWidget`、`Screen`、`EditBox`、`DynamicTexture`、`ClientLanguage`、`LocalPlayer`、`ClientPacketListener`、`MouseHandler`——用接口混入暴露字段/方法给下游调用
- `KonkreteMixinPlugin` 本身是**空实现**（`shouldApplyMixin` 恒 true），只作为未来条件开关的预留点

## 7. 值得学的 5 条做法

1. **ServiceLoader 平台抽象三件套**：接口放 common、实现放各平台、`META-INF/services` 三份文本文件挂接（`common/.../platform/Services.java:16-25`）→ 条件编译以外的多加载器方案，不需要 architectury
2. **外部图片 → 动态纹理管线**：`NativeImage.read(InputStream)` + `TextureManager` 注册，把磁盘/网络图片变成 `ResourceLocation`（`common/.../resources/ExternalTextureResourceLocation.java:51-70`）→ 做"用户自定义资源/图包"类 mod 必读
3. **accesswidener + 接口 mixin 替代到处 @Shadow**：`konkrete.accesswidener` 直接开放 `AbstractWidget.x/y` 与 `render`，再用 `IMixinAbstractWidget` 提供访问入口（`common/.../mixin/mixins/client/IMixinAbstractWidget.java`）→ 下游依赖该接口而非反射
4. **老 API 只废弃不删除**：`Locals`、`ScrollArea`、`AnimationRenderer`、`IAdvancedWidgetBase` 全部标 `@Deprecated(forRemoval = true)` 并保留行为占位（如 `AnimationRenderer.render()` 空实现）→ 给 FancyMenu 等下游留升级窗口
5. **Forge 侧 jarJar 内嵌 MixinExtras**（`forge/build.gradle:81-82`，`jarJar.ranged(it,"[0.3.2,)")`）→ 用高级 Mixin 注解而不强制用户装前置
6. **自研 GUI 控件绕过原版事件**：`input/MouseInput`/`KeyboardHandler` 静态缓存 + mixin 把 `onPress/onScroll/keyPress` 转成全局回调（`MixinMouseHandler.java:18-30`）→ 便于做"非 Screen 环境"的 HUD/覆盖层交互

## 8. 公开 API 与外部接入方式（库模组）

- **没有 api/impl 分层**：所有 `de.keksuccino.konkrete.*` 类都是事实公开 API（下游 FancyMenu / Drippy Loading Screen 直接 import 具体类，如 `de.keksuccino.konkrete.input.StringUtils`、`gui.content.AdvancedButton`、`properties.PropertiesSerializer`）
- 正式扩展点接口仅 3 个：`platform.services.IPlatformHelper`、`IPlatformCompatibilityLayer`（平台能力/兼容层，如 Optifine 检测，`annotations/OptifineFix`）、`resources.ITextureResourceLocation`、`rendering.animation.IAnimationRenderer`
- 接入方式：在 `fabric.mod.json`/`mods.toml` 声明依赖 → 调用 `Konkrete.addPostClientInitTask(modId, task)` 做延迟初始化（`Konkrete.java:92`）→ 使用 `gui.content.*` 控件与 `ConfigScreen`、`Config`、`Locals`、`ExternalTextureResourceLocation`/`TextureHandler` 等静态工具；无事件总线、无注册 API、无对外网络 API
- 注意 API 稳定性风险：类名/方法大量静态与直接字段访问，且 `@Deprecated(forRemoval=true)` 标记密集，下游需按版本对齐（`fabric.mod.json` 的 breaks 段即为此机制）
