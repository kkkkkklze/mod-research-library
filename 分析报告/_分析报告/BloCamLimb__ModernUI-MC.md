# BloCamLimb / ModernUI-MC 源码分析报告

## 1. 基本信息

- Mod 名：Modern UI；mod_id `modernui`（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）；作者 BloCamLimb；许可证 **LGPL-3.0-or-later**。
- 目标版本：`gradle.properties` → `minecraft_version=26.1.2`、`neoforge_version=26.1.2.59-beta`、`forge_version=64.0.8`、`mod_version=3.13.0.7-SNAPSHOT`、`core_version=3.13.0`（引擎 modernui-core）、`arc3d_version=2026.2.0`。注意：**不是 1.21.1 分支**（本机 NeoForge 1.21.1 若要参考需比对旧 tag，未确认）。
- 多加载器结构：`settings.gradle` include `common / forge(ModernUI-Forge) / neoforge(ModernUI-NeoForge) / fabric(ModernUI-Fabric)`；构建插件 `org.relativitymc.neo-loom 1.16-SNAPSHOT` + `com.gradleup.shadow 9.3.0`（root `build.gradle`），Java toolchain 25、`options.release=25`（root `build.gradle` subprojects 块）。
- 依赖（`common/build.gradle`、`neoforge/build.gradle`）：`dev.icyllis:modernui-core:3.13.0`（引擎，shadow 重定位打包）、`icyllis.modernui:ModernUI-Markflow:3.12.0`（Markdown）、`dev.icyllis:arc3d-*`（core/engine/granite/opengl/vulkan/sketch/compiler）、`compileOnly org.spongepowered:mixin:0.8.7`（common/build.gradle:21）、`asm-tree:9.8`、`org.lwjgl:lwjgl-vulkan:3.4.1`、Modrinth 上的 VulkanMod API（`api("maven.modrinth:JYQhtZtO:PNODQNIn")`）；access widener 为 `common/src/main/resources/modernui.classtweaker`。mods.toml 声明 required：neoforge `[26.1.0.1-beta,)`、minecraft `[26.1, 26.2)`；`tipthescales` 为 `discouraged`。

## 2. 源码规模与包结构

- 实测：**186** 个 `.java`，**47567** 行。
- 包（文件数）：`common .../modernui/mc` 34、`common .../mc/text` 28、`common .../mc/mixin` 25、`neoforge .../mc/neoforge` 17、`forge .../mc/forge` 16、`common .../mc/text/mixin` 16、`common .../mc/ui` 11、`fabric .../mc/fabric` 10、forge 测试 7、`common .../mc/b3d` 1。
- 最大文件：`text/TextLayoutEngine.java` 2689、`ui/PreferencesFragment.java` 1938、`FontResourceManager.java` 1788、`text/TextLayoutProcessor.java` 1785、`UIManager.java` 1544、`text/GlyphManagerForge.java` 1188、`text/TextLayout.java` 1055、`StillAlive.java` 1034、`text/GlyphManager.java` 1002、`forge/ConfigImpl.java` 与 `fabric/ConfigImpl.java` 各 913。

## 3. 入口与注册

- common 侧抽象基类 `common/src/main/java/icyllis/modernui/mc/ModernUIMod.java:30`；NeoForge 入口 `neoforge/.../mc/neoforge/ModernUIForge.java:45 @Mod(ModernUI.ID)`，构造器注入 `(IEventBus modEventBus, ModContainer modContainer)`（:56）；客户端是**嵌套的第二个 @Mod**：`:110 @Mod(value = ModernUI.ID, dist = {Dist.CLIENT}) class Client extends ModernUIClient`。Forge 侧同构：`forge/.../forge/ModernUIForge.java:47`。
- 注册内容（`ModernUIForge.java`）：`:80` `modContainer.registerConfig(COMMON, ConfigImpl.COMMON_SPEC, name + "/common.toml")` + `:82-84` 监听 `ModConfigEvent` 热重载；Client 内 `:120-123` 再注册 CLIENT/TEXT 两个 spec，`:125` `FontResourceManager.getInstance()`，`:126` `ModernUIText.init(modEventBus)`。
- 无 DeferredRegister：物品/方块注册走各加载器版 `Registration.java` / `MuiRegistries.java`（neoforge、forge 各一份）。加载期警告用 `:98-99 ModLoader.addLoadingIssue(ModLoadingIssue.warning(...))`，并在 `:65-78` 主动检测 `tipthescales`/`reblured`/`vulkanmod`/`legendarytooltips` 等冲突 mod。

## 4. 核心系统

1. **UI 线程与视图桥接**：`common/.../mc/UIManager.java:104`（`abstract class UIManager implements LifecycleOwner`），单例 `sInstance`（:116）、容器 id `fragment_container`（:118）；配套 `MenuScreen/MuiScreen/SimpleScreen/ScreenCallback/ContainerMenuView/MinecraftSurfaceView`。
2. **Unicode 文本排版引擎（最大子系统）**：`text` 包 28 个主类 + 16 个 mixin；`TextLayoutEngine.java` 2689 行、`TextLayoutProcessor.java` 1785、`TextLayout.java` 1055、`GlyphManager(.Forge)` + `ModernFontAtlas/StandardFontSet/SpaceFont/BitmapFont`、`FontResourceManager.java` 1788（字体资源与 atlas 重载）、`ModernTextRenderer/ModernPreparedText/ModernStringSplitter/ReorderTextHandler`（双向文字）。
3. **跨加载器 API/平台抽象**：`MuiModApi.java:77`（abstract，:212 `ServiceLoader.load(MuiModApi.class)`，:230 `get()`）暴露监听器接口 `OnScrollListener:80 / OnScreenChangeListener:92 / OnWindowResizeListener:105 / OnDebugDumpListener:120 / OnPreKeyInputListener:131 / OnUpdateLoaderListener:143 / OnRenderFrameListener:188`，渲染阶段常量 `RENDER_STAGE_UPDATE/EXTRACT/RENDER/PRESENT`（:173-185）；界面入口 `openScreen(Fragment)`（:254）、`createScreen(fragment[, ...])`（:263/272/282/315）、容器界面 :332。平台能力抽象在 `MuiPlatform.java:38 get()`、`:42-48`（bootstrap 路径、isClient、配置读写）；加载器实现 `MuiForgeApi.java` 补 `getRealGpuDevice/getRealGpuTexture/submitGuiElementRenderState`（`MuiModApi.java:463-477`）。
4. **渲染/GuiGraphics 集成**：`ExtendedGuiGraphics`、`MinecraftDrawHandler`、`GuiRenderType`、`TextRenderType`、`GradientRectangleRenderState`、`TooltipRenderer`；第三方兼容被隔离成单文件 `IrisApiIntegration.java`、`OptiFineIntegration.java`、`VulkanModIntegration.java`。
5. **配置与设置界面**：common `Config.java` / `ConfigItem.java`，各加载器 `ConfigImpl.java`（forge/fabric 各 913 行，neoforge 另有 `ForgeConfigItem.java`），界面为 `ui/PreferencesFragment.java`(1938) 等 11 个 Fragment（另有 `AdvancedOptionsFragment/DashboardFragment/ThemeControl/MarkdownFragment`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：未发现自建网络通道（未见 SimpleChannel/Payload 注册；**未确认**）。
- 配置：使用加载器原生 `ModConfig`，三个 spec：COMMON/CLIENT/TEXT（`ModernUIForge.java:80,120-123`）。
- datagen：通过 loom 的 `clientData` / `serverData` run config（`neoforge/build.gradle` runs 块）；代码侧有 `EmojiDataGen.java`。
- 数据驱动资源：`assets/modernui/emoji_data.json`、`lang/{en_us,ru_ru,uk_ua,zh_cn,zh_tw}.json`、`post_effect/{gaussian_blur,grayscale,radial_blur}.json`、大量 `shaders/*.frag`（含 `_330` 变体）。

## 6. Mixin

- 配置文件（git 已跟踪，本地工作区未检出，可用 `git show HEAD:<path>` 读取）：`neoforge/src/main/resources/mixins.modernui-neoforge.json`（`plugin: icyllis.modernui.mc.MixinConfigPlugin`、`package: icyllis.modernui.mc.mixin`、`required: true`、`mixinPriority: 1`）、`mixins.modernui-textmc.json`（`plugin: icyllis.modernui.mc.text.MixinConfigPlugin`、`package: ...mc.text.mixin`、`mixinPriority: 3`）、forge 侧 `mixins.modernui-forge.json` + `META-INF/coremods.json` + `MixinConnector.java`（`IMixinConnector.connect()` 里 `Mixins.addConfiguration("mixins.modernui-forge.json")`）。
- 条件化插件：`common/.../mc/MixinConfigPlugin.java:28`，`:36-42` 从 bootstrap 系统属性读开关（`ModernUIMod.BOOTSTRAP_DISABLE_SMOOTH_SCROLLING` / `..._ENHANCED_TEXT_FIELD`），`:51-68` 在 `shouldApplyMixin` 里逐类禁用以关闭对应功能，`:69-71` 统一禁用类名以 `DBG` 结尾的调试 mixin。
- 代表性 hook：`mixin/MixinMinecraft.java:51 @Inject(setScreen, FIELD)`、`:58/:75 onGameLoadFinished HEAD/TAIL`、`:85 allowsTelemetry HEAD cancellable`、`:92-110 renderFrame (INVOKE)`、`:137 close`；`mixin/MixinScreen.java:30 @Mixin(Screen.class)`、`:75 @Inject(renderTooltipInternal, TAIL)`；`mixin/MixinGuiRenderer.java:40 @Inject(executeDrawRange)`；文本侧 `text/mixin/MixinFontRenderer.java:35 @Mixin(Font.class)`、`:42 @Redirect(method="<init>", NEW ...)`；另有 6 个 `Access*` accessor mixin。

## 7. 值得学的 5 条具体做法

1. **用 `IMixinConfigPlugin` 做 mixin 级开关 + 发布前剔除调试 mixin**（`MixinConfigPlugin.java:36,51,69`）：把无配置界面的高危注入留给系统属性应急关闭，并以类名后缀 `DBG` 统一禁用调试注入。
2. **common 写抽象基类 + `ServiceLoader` 桥到各加载器实现**（`MuiModApi.java:212,230`、`MuiPlatform.java:38`）：同一份 API 由 forge/neoforge/fabric 各自的 `MuiForgeApi/MuiPlatformForge` 落实现，避免 common 出现平台 if。
3. **把大子系统（文本引擎）整体可插拔**：`text` 包独立 + 独立 mixin 配置 + `BOOTSTRAP_DISABLE_TEXT_ENGINE` 开关（`ModernUIMod.java:36,112`），出问题时能整块关掉。
4. **第三方兼容隔离成单文件 Integration**（`IrisApiIntegration.java`/`OptiFineIntegration.java`/`VulkanModIntegration.java`）：主流程只做"加载了什么 mod"的探测（`ModernUIForge.java:65-78`）。
5. **多加载器共享 common，但依赖版本集中声明**：root `build.gradle` subprojects 统一 toolchain/注解依赖，模块各自 `shadow`/`include` 打包 arc3d 与 core；common 用 `accessWidenerPath = file("src/main/resources/modernui.classtweaker")`（`common/build.gradle`）统一访问权。

## 8. 公开 API 与外部接入

- API 包：`icyllis.modernui.mc`（`MuiModApi`、`MuiPlatform`、`MuiScreen`、`MenuScreen`、`ScreenCallback`、`IModernEditBox`、`ConfigItem`、`ContainerMenuView`）；文本 API 在 `icyllis.modernui.mc.text`（`ModernTextRenderer`、`ModernPreparedText`、`GlyphRender`、`TextRenderType`）；示例界面与组件在 `icyllis.modernui.mc.ui`（Fragment 子类，`ui/CenterFragment2.java` 作为打开界面的示例）。
- 外部 mod 接入方式：调用 `MuiModApi.get().openScreen(Fragment)` 或 `createScreen(fragment[, ContainerMenu])` 打开 ModernUI 界面；注册 `OnScrollListener` / `OnScreenChangeListener` / `OnRenderFrameListener` 等回调；平台与配置通过 `MuiPlatform.get()`；文字渲染接管由 `mixins.modernui-textmc.json` 自动生效，可按 `modernui_mc_disableTextEngine` 属性关闭（`ModernUIMod.java:36,112`）。
