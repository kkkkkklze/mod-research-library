# reserveword/IMBlocker（输入法冲突修复）源码分析

> 本地为 **master 分支最新提交**（`e7d463a`，2026-09-12 "Update changelog"，mod_version 5.6.1）。

## 1. 基本信息

- Mod 名 / mod_id：IMBlocker / `imblocker`；作者 reserveword, LitnhJacuzzi；许可证 `GPL3 or higher`（`gradle.properties:license`）
- 目标版本：构建基线 `minecraft_version=1.19.4`，但产物一份 jar 覆盖 **1.17~1.21.8**（`fabric/build.gradle` archivesName `IMBlocker-5.6.1-fabric+1.17-1.21.8`；`fabric.mod.json` depends `minecraft: ">=1.17 <=1.21.8"`, `java: ">=17"`）
- 加载器：Fabric（`fabric-loom 1.8.+` + yarn）、Forge（45.3.7 + official mappings）、forge-legacy、NeoForge（`compatibilityLevel: JAVA_21`）。多模块工程：`common` / `fabric` / `forge` / `forge-legacy` / `neoforge`（`settings.gradle:8`）
- 关键依赖：`net.java.dev.jna:jna(-platform):5.12.1`（Windows IMM32 调用）、`ca.weblite:java-objc-bridge:1.1`（macOS）、`org.spongepowered:mixin:0.8.5`、`asm-tree:9.6`、lwjgl+lwjgl-glfw 3.3.4、joml、log4j；`compileOnlyApi cloth-config-forge`（软依赖，做配置界面）
- 可选兼容编译依赖（全部 compileOnly）：REI、EMI、Axiom、supermartijn642 core lib、FTB Library、LibGui、Ixeris、Armourers Workshop、ModernUI、ReplayMod、Notebook、sodium/reeses-sodium-options、blockui、ldlib2、essential 等

## 2. 源码规模与包结构

181 个 `.java` / 9639 行（`find . -name '*.java' -exec wc -l {} +`）。按模块：`common` 84、`forge` 37、`fabric` 34、`forge-legacy` 17、`neoforge` 9。common 侧包结构（到第 3 层）：`io.github.reserveword.imblocker.common`（IMManager 族、配置、核心）、`.common.gui`（焦点与渲染层，28 个类）、`.common.accessor`（4 个跨加载器接口）、`io.github.reserveword.imblocker.mixin[.compat]`。

最大文件：`IMManagerWindows.java` 411、`IMManagerMac.java` 362、`gui/GenericAxiomTextField.java` 221、`IMBlockerAutoConfig.java` 198、`IMBlockerMixinPlugin.java` 174、`gui/FocusContainer.java` 172、`gui/MinecraftFocusContext.java` 171、`IMManager.java` 171、`gui/UniversalIMEPreeditOverlay.java` 158、`IMManagerX11.java` 154（`forge/*/mixin/TextFieldLegacyMixin.java` 各 132）。

## 3. 入口与注册

每个加载器一个薄 `IMBlocker`（`@Mod(IMBlockerCore.MODID)`），逻辑集中在 `IMBlockerCore`：

```java
public static void invokeOnMainThread(Runnable r) {           // common/IMBlockerCore.java:26
    if (IS_IXERIS_LOADED) IxerisApi.getInstance().runLaterOnMainThread(r);
    else MinecraftClientAccessor.INSTANCE.execute(r);
}
```

`IMBlockerCore` 静态块用 `Class.forName("io.github.reserveword.imblocker.ModLoaderAccessorImpl")` + `ReflectionUtil.newInstance` 拿到各加载器实现（`IMBlockerCore.java:83-93`），**common 不直接引用任何加载器 API**；只有 `registerClientTickEvent`、`hasMod`、`isGameVersionReached`、`getMapping` 四个方法（`accessor/ModLoaderAccessor.java`）。无方块/物品注册。

## 4. 核心系统

**① 平台输入法抽象 + Windows IMM32 实现**
`IMManager`（`common/IMManager.java:20-33`）定义 `PlatformIMManager` 接口（`setState/setEnglishState/updateCompositionWindowPos/setPreeditCursorRectangle/updateCompositionFontSize/initializeIngameIME`），静态块按 `Platform.isWindows/isMac/isLinux` 选实现（`IMManager.java:140-170`），Linux 优先反射加载第三方增强实现 `xyz.rrtt217.HDRMod.compat.imblocker.IMManagerLinuxEnhanced`，失败再试 X11（`GLFWNativeX11.glfwGetX11Window`），否则退化 `IMManagerStub`。`IMManagerWindows` 用 `Native.register("imm32")` 直连原生函数：开输入法 = `ImmAssociateContext(hwnd, ImmCreateContext())`，关 = `ImmAssociateContext(hwnd, null)`（`IMManagerWindows.java:112-125`）；切中英文 = `ImmSetConversionStatus(himc, english?0:1, 0)`，并受一个 60ms `getConversionStatusCooldown()` 限制（切换输入法后立即设转换状态会失效），用常驻 `SetConversionStateThread` 排队执行（`IMManagerWindows.java:303-335`）。

**② 游戏内自绘 IME（候选词/预编辑显示）**
`initializeIngameIME` 用 `SetWindowLongPtr(hwnd, GWL_WNDPROC, CallbackReference.getFunctionPointer(imeListener))` 替换 GLFW 窗口过程，拦截 `WM_IME_SETCONTEXT`（去掉 `ISC_SHOWUICANDIDATEWINDOW`，屏蔽系统候选窗）、`WM_IME_STARTCOMPOSITION`（直接返回空 LRESULT 吃掉）、`WM_IME_COMPOSITION`、`WM_IME_ENDCOMPOSITION`、`WM_IME_NOTIFY/IMN_SETCONVERSIONMODE|IMN_CHANGECANDIDATE`，末尾统一 `CallWindowProc(originalProc, ...)` 链回原处理（`IMManagerWindows.java:187-229`）。取数据用 `ImmGetCompositionStringW(GCS_COMPSTR/GCS_CURSORPOS)` 与手工解析 `ImmGetCandidateListW` 返回的内存块（`getInt(12/16/20)` = selectedIndex/pageStart/pageSize，候选串偏移 `24 + i*4`），转成 `UniversalIMEPreeditOverlay` / `UniversalIMECandidateOverlay` 的自绘内容（`IMManagerWindows.java:262-301`）。

**③ FocusManager 焦点传输链（本 mod 的理论核心）**
类文档明确写出设计（`gui/FocusManager.java:10-44`）：路径 `Operating System -> [Game Window -> FocusContainer -> FocusableWidget]`，方括号内由 IMBlocker 管理。全局变量只有 `focusOwner`、`focusedContainer`（默认 `FocusContainer.MINECRAFT`）、`isWindowFocused`、`isWindowInitialized`、`windowPixelDensity`；`requestFocus(container)` / `setWindowFocused(boolean)`（由 GLFW 窗口回调调用）→ `deliverFocus()` / `lostFocus()` 逐级下发；`FocusContainer` 抽象出 `MINECRAFT`（`MinecraftFocusContext`）与 `IMGUI`（`ImGuiFocusContext`）两个上下文，提供 `switchFocus/clearFocus/checkFocusCandidatesVisibility/getBoundsAbs/getCaretPos/getGuiScale`。之所以造这套系统，注释给了三条理由：原生焦点状态不可靠、GUI 架构各异、部分 mod GUI 实现质量差。

**④ IMBlockerMixinPlugin：条件化 mixin 总开关**
`getMixins()` 返回的列表在**静态块**里拼好（`IMBlockerMixinPlugin.java:19-161`）：
- 按 mapping 二选一：`isOfficialMapping ? "AbstractWidgetMixin" : "ClickableWidgetMixin"`、`KeyboardHandlerAccessor` vs `KeyboardAccessor`、1.19.1+ 的 `AbstractScrollWidgetMixin/StringViewAccessor/MultilineTextFieldMixin` vs `ScrollableWidgetMixin/SubstringAccessor/EditBoxMixin`
- 按协议版本门控：`isGameVersionReached(771/*1.21.6*/)` → `IMEOverlayRendererV3`，763 → V2，755 → V1；`isGameVersionReached(762/*1.19.4*/)` → `TextFieldMixin`，否则 `TextFieldLegacyMixin`
- 按平台：Windows 加 `WindowsFullScreenPatch`/`WindowsIngameIMEInitializer`，Linux 加 `LinuxKeyboardPatch`
- 按第三方 mod 存在性（`IMBlockerCore.hasMod`）：`axiom`/`ftblibrary`/`libgui`/`emi`/`roughlyenoughitems`/`replaymod`/`meteor-client`/`reeses-sodium-options`/`blockui`/`supermartijncorelib`/`notes`/`essential`/`sfm`/`armourers_workshop`/`modernui`/`ldlib2` 各自点亮 `compat.*` mixin；`generalfeedback` 一行被注释掉并注明 "Unstable Internal Implementation"

**⑤ `src/shadow` 源码集：给"不存在的依赖"写桩类**
每个模块都有 `src/shadow/java`，`sourceSets.shadow` 先编译，再 `main { compileClasspath += files(sourceSets.shadow.output) }`（`common/build.gradle:27-40`）。里面的"类"是手写空桩：`net/minecraft/client/gui/GuiGraphics.java`（方法名直接用 SRG `m_280168_()`、`m_286007_()`、`m_280509_()`，带 `/**pose*/` 注释说明映射含义）、`neoforge/src/shadow/.../DeltaTracker.java`（空接口）、fabric 侧 `net/minecraft/class_332.java`（yarn 名）、`com/lowdragmc/lowdraglib2/gui/ui/elements/TextField.java`、`gg/essential/gui/common/input/AbstractTextInput.java`、`kotlin/Pair.java`。这样能在**不引入真实 mod 依赖、也不依赖具体 MC 版本**的前提下编译兼容 mixin。

**⑥ 兼容 mixin 复用主 mixin（含双映射名）**
`fabric/.../mixin/compat/EmiSearchWidgetMixin` 直接 `extends TextFieldMixin` 并复用其注入方法，且 method 数组同时给两套名字：

```java
@Inject(method = {"isFocused", "method_25370"}, at = @At("TAIL"))
public void updateLastRenderTime(CallbackInfoReturnable<Boolean> ci) { super.updateLastRenderTime(ci); }
```

主 mixin `forge/.../TextFieldMixin`（`@Mixin(EditBox.class)`，`extends AbstractWidgetMixin implements MinecraftTextFieldWidget`）注入 `setFocused`/`setVisible`（TAIL）、`charTyped`（HEAD,cancellable）、`onValueChange`（TAIL），并 `@Overwrite setEditable`；用 `@Unique isRenderable/lastRenderTime` + `checkVisibility(lastGameRenderTime)`（比较 `lastRenderTime`）过滤"不可见但仍有焦点"的控件（`TextFieldMixin.java:87-127`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端，`FMLEnvironment.dist != Dist.CLIENT` 时只打 fatal 警告）。
- 配置：`IMBlockerConfig`（纯 Java 默认值）+ 有 `cloth_config` 时 `IMBlockerAutoConfig extends IMBlockerConfig implements ConfigData`（`@Config(name=MODID)`，`GsonConfigSerializer`），`@ConfigEntry.Gui.CollapsibleObject` 分组：Basic/Advance/ModCompatibility/WindowsCompatibility/LinuxCompatibility。Forge 侧注册界面是**反射适配三代 API**：`ConfigScreenHandler$ConfigScreenFactory`(1.19+) → `ConfigGuiHandler$ConfigGuiFactory`(1.18) → `fmlclient.ConfigGuiHandler$ConfigGuiFactory`(1.17)（`forge/IMBlocker.java:40-72`）。无 cloth_config 则 `IMBlockerConfig.INSTANCE.reloadConfig()`。
- 白名单机制：`defaultScreenWhitelist` 预置 Create 剪贴板、Supplementaries/Simulated/Aeronautics/PneumaticCraft 等屏幕类名，`bakeList()` 用 `Class.forName(s, false, classLoader)` 惰性解析并忽略缺失类（`IMBlockerConfig.java:44-64`）；`commandPrefixRegexMatcher`(默认 `^/`) 判断聊天内容是否命令，用于自动切英文。
- 数据驱动/datagen：无；资源只有 `assets/imblocker/lang/{en_us,zh_cn,zh_tw}.json`、`pack.mcmeta`、图标；所有 `mods.toml`/`fabric.mod.json` 都是 `${占位符}` 模板，由根 `build.gradle:92-93` 的 `expand all_properties` 展开。

## 6. Mixin

4 个配置：`fabric/src/client/resources/imblocker.mixins.json`、`forge`/`forge-legacy/src/main/resources/imblocker-forge.mixins.json`、`neoforge/src/main/resources/imblocker-neoforge.mixins.json`。四者结构一致（`package: io.github.reserveword.imblocker.mixin`、`compatibilityLevel` JAVA_17/JAVA_21、`injectors.defaultRequire=1`、`overwrite.strict=false`、`plugin: io.github.reserveword.imblocker.common.IMBlockerMixinPlugin`），**类列表全部由 plugin 动态提供**，json 里不写 `mixins` 数组。代表性注入点见 §4⑤/⑥。

## 7. 值得学的 5 条具体做法

1. **用"手写桩类 + 独立 shadow sourceSet"解耦编译期依赖**：src/shadow 里放 MC/第三方类的空壳（含 SRG/yarn 双套方法名），`main.compileClasspath += shadow.output`（`common/build.gradle:27-40`）。适用：单 jar 兼容多 MC 版本 + 编译期兼容十几个可选 mod 且不引入依赖。
2. **mixin 配置只留 plugin，用 `getMixins()` 静态表和 `isGameVersionReached(协议号)`/`hasMod(id)` 门控**（`IMBlockerMixinPlugin.java:19-161`）。适用：一份源码同时供 1.17~1.21.8 与四种映射。
3. **兼容 mixin `extends` 自家 mixin 并复用 `@Inject` 数组中的双映射方法名**（`@Inject(method = {"isFocused", "method_25370"})`）。适用：Fabric(yarn/intermediary) 与 Forge(official/SRG) 共用一套注入代码。
4. **自建焦点管理系统而不是信任原版/GUI 库的 `isFocused`**：`FocusManager` 全局链 + `FocusContainer.MINECRAFT/IMGUI` 抽象 + `isRenderable`/`lastRenderTime` 过滤假焦点（`gui/FocusManager.java`、`forge/.../TextFieldMixin.java:105-127`）。适用：需要"当前到底谁在接收键盘"的输入类 mod。
5. **替换窗口过程实现游戏内 IME 自绘**：`SetWindowLongPtr(GWL_WNDPROC)` + 处理 `WM_IME_*` 并 `CallWindowProc` 链回原过程，配合 `ImmGetCompositionStringW`/`ImmGetCandidateListW` 取候选词（`IMManagerWindows.java:187-301`）。适用：需要把任意系统的候选框画进 MC 渲染管线的场景（想抄时注意 Windows 全屏需同时处理 `WindowsFullScreenPatch`）。

## 8. 公开 API / 外部接入

非库 mod，无对外 API。但 common 模块里四个接口就是它的"内部扩展点"，外部 fork 只需为每个加载器实现一份：`accessor/ModLoaderAccessor`（hasMod/isGameVersionReached/getMapping/registerClientTickEvent）、`accessor/MinecraftClientAccessor`（execute/getWindowHandle）、`common/IMManager.PlatformIMManager`（新增平台输入法后端，如 HDRMod 用 `xyz.rrtt217.HDRMod.compat.imblocker.IMManagerLinuxEnhanced` 反射接入）、`gui/FocusableObject + FocusContainer`（接入新 GUI 框架的焦点体系）。
