# decce6/Ixeris 源码分析报告

## 1. 基本信息
- Mod 名：Ixeris；modid `ixeris`；`maven_group=me.decce.ixeris`；作者 decce（credits: LitnhJacuzzi）；版本 `4.6.5`；描述 "Buffered raw input and threaded event polling"
- 许可证：`mod_license = LGPL-3.0-only`（`gradle.properties`）；**API 部分单独声明为 0BSD**（`src/api/java/me/decce/ixeris/api/IxerisApi.java:3` SPDX 头，`API_DOCS.md` 明确说明"API 是 BSD-0 授权"，便于其他 mod 集成）
- 目标 MC 与加载器：stonecutter 默认版本 `1.21.11-fabric`（`stonecutter.gradle.kts:5`），构建矩阵覆盖 `versions/` 下 25 个目标：1.16.5/1.18.2/1.19.2/1.20.1/1.20.4/1.21.1/1.21.8/1.21.11 × fabric/forge/neoforge，以及 26.1/26.2/26.3 × fabric(无混淆 loom)/neoforge；Java 版本按 MC 版本自动推导（`buildSrc/.../ixeris-common-conventions.gradle.kts`: `>=26 → 25`、`>=1.20.5 → 21`、否则 17）
- Gradle：`dev.kikugie.stonecutter` 0.9.7 + `net.fabricmc.fabric-loom-remap` 1.17-SNAPSHOT + `com.gradleup.shadow` + `me.modmuss50.mod-publish-plugin`；多模块：根工程 + `includeBuild("core")` + `service-neoforge`/`service-neoforge-v2`，公共约定在 `buildSrc/src/main/kotlin/me/decce/ixeris/gradle/ixeris-common-conventions.gradle.kts`
- 编译依赖：`net.fabricmc:fabric-loader:0.19.3`（loom 侧）；shadow 打进并 relocate 的 `com.electronwill.night-config:core/toml:3.8.2`（→ `me.decce.ixeris.core.shadow.nightconfig`）；`core` 模块 compileOnly：`classtransform 1.14.1` + `mixinstranslator 1.14.1` + `sponge mixin 0.8.5` + `lwjgl(-glfw/-sdl) 3.4.1` + `modlauncher 10.0.9` + `securemodules 2.2.21` + fastutil/gson/guava/log4j；`gradle.properties` 中 `deps.classtransform=1.15.0-SNAPSHOT`、`deps.reflect=1.6.1`

## 2. 源码规模与包结构
- `.java` 168 个，共 16465 行
- `core/` 为核心库（不含 MC 依赖，105 个文件）：`core`（11）、`core.glfw.callback_dispatcher`（22 + `_334` 5）、`core.glfw.state_caching`（3，含 `window` 11/`global` 4/`util` 3）、`core.sdl`（4）与 `core.sdl.state_caching`（7）、`core.mixins.glfw`（8：plain/callback_dispatcher(+_334)/flexible_threading/glfw_state_caching/glfw_threading(+_330/_334)）、`core.mixins.sdl`（+threading 共 8）、`core.natives.win32`（8）、`core.input(.win32)`（3+3）、`core.threading`（2）、`core.transform`（2）、`core.util`（7）、`core.java8`（2）
- `src/ixeris`（客户端实现）：`me.decce.ixeris`（IxerisMod、RenderThreadStarter、VersionCompatUtils 等 4）、`mixins`（11）、`forge` + `forge.transformers.*`（13 个 Transformer，与 core 的 mixin 一一对应）、`workarounds`（2）、`neoforge`（1）；`src/java8`（3+2：MixinPlugin 与各加载器入口，Java 8 编译）；`service-neoforge`/`service-neoforge-v2`（各 3-4 个 Bootstrap 类）
- 最大文件：`src/ixeris/.../transformers/sdl/threading/SDLVideoTransformer.java` 788、`core/.../mixins/sdl/threading/SDLVideoMixin.java` 779、`core/.../input/win32/RawInputHandlerGlfwWin32.java` 573、`src/ixeris/.../transformers/glfw/glfw_threading/GLFWTransformer.java` 493、`core/.../mixins/glfw/glfw_threading/GLFWMixin.java` 484、`GLFWTransformer`(callback_dispatcher) 405、`GLFWMixin`(callback_dispatcher) 396、`core/natives/win32/RAWMOUSE.java` 392、`IxerisConfig.java` 318、`src/api/.../IxerisApi.java` 203

## 3. 入口与注册
- Fabric：`src/java8/java/me/decce/ixeris/fabric/IxerisModFabric.java`（`ClientModInitializer`，Java 8 编译以便低 Java 版本时能安全禁用）→ `IxerisMod.init()`
- Forge/NeoForge：走**早期 service 而非普通 mod 入口**——`service-neoforge/src/main/java/me/decce/ixeris/neoforge/core/IxerisBootstrapper.java` 实现 `net.neoforged.neoforgespi.earlywindow.GraphicsBootstrapper`，在 GLFW/SDL 类被加载前做字节码改写（注释写明 "Must run before GLFW/SDL classes are loaded"）；另有 `IxerisModLocator`、`NeoForgeClassLoaderHandler`；`service-neoforge-v2` 是面向更新 NeoForge 的同名重写
- Mixin 配置两份：`core/src/main/resources/ixeris.core.mixins.json`（plugin `IxerisCoreMixinPlugin`，`client`/`mixins` 都为空，**混入列表由 `getMixins()` 动态返回**）与 `src/ixeris/resources/ixeris.mixins.json`（plugin `IxerisMixinPlugin`，`client` 列出 MainMixin/MinecraftMixin/MouseHandler(Mixin/Accessor)/RenderSystemMixin/TitleScreenMixin/WindowMixin/enhanced_fps_limiter.RenderSystemMixin/macos.*/workarounds.WindowAccessor）
- 仓库快照中**没有 `fabric.mod.json`**（`buildSrc` 约定脚本里有 `filesMatching("**/fabric.mod.json")` 与 `exclude("**/fabric.mod.json")`，说明文件由构建提供，快照缺失，未确认）；元数据模板为 `src/main/resources/META-INF/neoforge.mods.toml`（`modId = "${modid}_dummy"`，注释说明只给启动器显示用）与 `src/ixeris/resources/META-INF/{mods.toml,neoforge.mods.toml}`（`clientSideOnly=true`）
- 无 DeferredRegister/物品注册；`service-neoforge` 用 ServiceLoader 机制（resources 由构建生成）

## 4. 核心系统
1. **主线程/渲染线程倒置的线程模型**（`src/ixeris/java/me/decce/ixeris/RenderThreadStarter.java`）：`MainMixin` 在 `Main#main` 的 `Thread.setName` 之后注入（`mixins/MainMixin.java:33`，`cancellable=true`），把 `Minecraft` 实例的创建与主循环搬到渲染线程（`RenderSystem.initRenderThread()` → `new Minecraft(gameConfig)` → `minecraft.run()`），原主线程改名 "Ixeris Event Polling Thread"（`core/.../Ixeris.java:11`）专职轮询事件；`IxerisMod.renderThread`/`isOnRenderThread()` 提供双线程判定
2. **跨线程调度与阻塞桥接**（`core/.../threading/MainThreadDispatcher.java`）：`ConcurrentLinkedQueue` + `mainThreadLock` 对象锁；`runLater` 投递、`runNow/query(Supplier<T>)` 用 `Query`/`ImmediateRunnable` + `Thread.onSpinWait()` 自旋等结果；`findNextTask()` 注释 "Prioritize blocking tasks to reduce render thread waiting time"，队列空时才 `pollEvents`；跨线程调用前 `Ixeris.accessor.unlockContext()`、返回后 `lockContext()` 释放 GL 上下文；`RenderThreadDispatcher` 用 `recordingQueue` + `errorRecordingQueue` 把 GLFW 回调顺序回放到渲染线程（`replayErrorQueue`），并在 LWJGL ≥3.4 时用 `UpcallExceptionHelper` 捕获 upcall 异常
3. **GLFW/SDL 状态缓存**（`core/.../glfw/state_caching/`、`core/.../sdl/state_caching/`）：`GlfwCache/GlfwCacheManager/GlfwGlobalCacheManager/GlfwWindowCacheManager` 分层，窗口级 11 个缓存（`GlfwInputModeCache`、`GlfwWindowSizeCache`、`GlfwKeyNameCache`…）使"必须主线程执行"的查询变成任意线程可读的缓存；SDL 侧为 `SdlDisplayCache/SdlGlobalCache/SdlWindowCache` + `BasicSdlInt2ObjectCache` 等基类
4. **GLFW/SDL 回调分发体系**（`core/.../glfw/callback_dispatcher/`）：每种回调一个 Dispatcher（`KeyCallbackDispatcher`、`CursorPosCallbackDispatcher`…共 22 个）+ `UpcallRunnable` 接口 + `CommonCallbacks` 汇总；`_334` 包为 LWJGL 3.3.4+ 新增回调（IMEStatus/Preedit/PreeditCandidate）
5. **Windows 缓冲原始输入**（`core/.../input/win32/RawInputHandlerGlfwWin32.java`）：用 `natives/win32/User32Ex.java:65,93-99` 经 LWJGL `apiGetFunctionAddress` 直接 downcall `GetRawInputBuffer`，自管 `RAWINPUT.calloc(size)` 缓冲并按需增长（默认 32~1024），实现 `grab/release/pollEvents`，用 `MessageOptimizationStrategy`（DEFAULT/UNOPTIMIZED/THROTTLED/NOLEGACY）分档处理 legacy 消息，并有 `FIND_MESSAGE_MAXIMUM_RECURSION = 15` 防递归；`natives/win32` 下 8 个类是 Win32 结构体映射（RAWMOUSE/RAWKEYBOARD/RAWHID 等）
6. **"同一 mixin 的多实现 + 运行期筛选"与 Forge/NeoForge 字节码路线**：`core/src/java8/java/me/decce/ixeris/core/Constants.java` 集中列出 16 个 mixin 名（如 `glfw.glfw_threading_330.GLFWMixin`、`sdl.threading.SDLVideoMixin`）；`IxerisCoreMixinPlugin.getMixins()` 用 `MixinHelper.shouldApply` 过滤——类名含 `glfw`/`sdl` 时按 `RuntimeBackend.HAS_GLFW/HAS_SDL`（用 `MixinEnvironment` 类加载器 `getResource("...class")` 探测）决定，含 `_330`/`_334` 时按 `LWJGLVersionHelper` 判定，`flexible_threading` 看配置，`macos` 看平台。Forge/NeoForge 上 GLFW/SDL 属 bootstrap 层、mixin 打不到，于是 `Constants.getForgeTransformerClasses` 把同一批 mixin 名做 `Mixin → Transformer` 替换映射到 `src/ixeris/.../forge/transformers/**`（Netty 生态外的 `net.lenni0451.classtransform` + mixinstranslator，即"mixin 源码编译成 ClassTransform transformer"），再由 `IxerisBootstrapper`/`IxerisTransformer` 执行 `expandGlfwModuleReads()` → `doTransformation` → `ClassLoaderHandler.defineClass(bootstrapClassLoader, …)`（NeoForge）或 `Agents`/`Instrumentation.redefineClasses`（Forge）
7. **配置**：`core/.../IxerisConfig.java` 用自定义注解（`@Comment`/`@Key`）+ 反射 + night-config TOML 读写；含 `enabledOnWindows/MacOS/Linux/OtherPlatforms` + `BooleanHolder enabledOnCurrentPlatform`（惰性平台判定）、`flexibleThreading`、`fullyBlockingMode`、`eventPollingThreadPriority`、`bufferedRawInput.*`（mouse/keyboard/min/max/messageOptimizationStrategy）、`aggressiveCaching`、三个 debug 日志开关

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无（纯客户端，无自定义 payload）
- 数据驱动：无；`generator/meta/callback_list.txt` 是一份回调清单（用于对照/生成 Dispatcher，未确认是否为脚本生成）
- 配置：自研注解式 TOML 配置（night-config 被 shade + relocate，避免与其他 mod 冲突），带 `@Comment` 自动写入注释与平台开关
- datagen：无

## 6. Mixin
- 配置：`core/src/main/resources/ixeris.core.mixins.json` + `src/ixeris/resources/ixeris.mixins.json`（均带 `IMixinConfigPlugin`，`required: true`，`injectors.defaultRequire: 1`；ixeris 那份 `refmap: ixeris.mixins.refmap.json`，由 loom `mixin.add(ixerisSourceSet, ...)` 生成）
- 代表 hook：`@Mixin(GLFW.class, remap=false, priority=500)` 在 `core/.../mixins/glfw/glfw_threading/GLFWMixin.java:24-…` 对 `glfwCreateWindow`/`glfwDefaultWindowHints`/`glfwFocusWindow`/`glfwGetClipboardString`/`glfwGetJoystick*` 等几十个方法 `@Inject(at=HEAD, cancellable=true)` 短路（改走主线程/缓存）；`MinecraftMixin` 在 `Minecraft#runTick` 的 `Window.updateDisplay(...)` 调用点与 `Thread.yield()` 之后注入、`destroy` 的 `System.exit` 处注入（`mixins/MinecraftMixin.java:31,60,71`）；`RenderSystemMixin` 用 MixinExtras `@WrapMethod(method="pollEvents")`；`MouseHandlerMixin` `@WrapMethod` 包 `grabMouse/releaseMouse`；两类 `IMixinConfigPlugin`（`IxerisMixinPlugin` 含 `PlatformHelper.isAndroid()/isX64()`、`JavaHelper.JAVA_SUPPORTED` 守卫）

## 7. 值得学的 5 条具体做法
1. **把"必须指定线程执行"的系统调用全部收拢到 Dispatcher 并加自旋等待**：`MainThreadDispatcher.runNow/query`（`core/.../threading/MainThreadDispatcher.java:41-83`），适用于任何需要跨线程调用线程受限 API 的场景
2. **用类名字段做"编译期多实现、运行期自动筛选"**：`Constants.MIXINS` + `MixinHelper.shouldApply` 按 `glfw/sdl/_330/_334/macos/flexible_threading` 子串决定启用（`core/.../MixinHelper.java:7-20`），避免为每个平台写多份 mixin 配置
3. **Mixin 与 ClassTransformer 双形态复用同一套源码/命名**：`Constants.getForgeTransformerClasses` 用 `replace("Mixin","Transformer")` 在 bootstrap 类上复刻 mixin 逻辑（`core/src/java8/.../Constants.java:52-58`），适用于需要改 bootstrap/模块层类（GLFW、SDL）的 mod
4. **把"入口/插件/低版本兼容代码"单独用 Java 8 编译**：`java8` sourceSet + `compileJava8Java` 设 1.8（`buildSrc/.../ixeris-common-conventions.gradle.kts:49-57`），运行时用 `JavaHelper.JAVA_SUPPORTED` 决定是否启用，保证高版本 Java 特性代码在旧 JVM 上不会崩
5. **资源重载/注入路径上的状态缓存代替重复查询**：`GlfwWindowCacheManager` + 11 个窗口缓存类把 GLFW 状态读变成本地字段（`core/.../glfw/state_caching/window/`），适用于高频查询唯一状态源（窗口尺寸、输入模式、键名）的场景

## 8. 公开 API 与接入方式
- API 包：`me.decce.ixeris.api`（仅 2 个类：`IxerisApi`、`IxerisFuture`），0BSD 许可
- 获取方式：`modImplementation "maven.modrinth:ixeris:$version:api"`（`API_DOCS.md`）；构建侧通过 `apiJar`/`apiSourcesJar` 任务（`ixeris-common-conventions.gradle.kts:132-138,227-228`）作为 Modrinth 附加文件发布
- 扩展点：`IxerisApi.getInstance()` 后可用 `getMainThreadName()`、`isEnabled()`、`isInitialized()`、`isOnMainThread(OrInit)()`、`runOnMainThread(Runnable)`（按 `fullyBlockingMode` 自动选择阻塞/延迟）、`runNowOnMainThread`/`runLaterOnMainThread`，以及基于 `Future` 的变体（`IxerisFuture`）；未启用 Ixeris 时 `runOnMainThread` 直接原地执行，保证无 mod 也能工作
- 内部扩展面（非 API，但可参考）：`core` 模块被 shade 进所有平台 jar，`MixinHelper`/`Constants`/`RuntimeBackend` 是平台适配中枢
