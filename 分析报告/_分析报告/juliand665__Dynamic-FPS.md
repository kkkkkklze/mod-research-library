# Dynamic FPS 源码分析报告

仓库根：`源码库\_参考仓库\_bulk\juliand665__Dynamic-FPS`（分支 `main`，HEAD `b2a7c3b`，mod_version 3.11.9）

## 1. 基本信息

- Mod 名 Dynamic FPS / mod_id `dynamic_fps` / 命名空间 `net.lostluma`；作者 "juliand665 & LostLuma"（`platforms/neoforge/src/main/resources/META-INF/neoforge.mods.toml:8`、`:11`）。
- 目标 MC 与加载器：**本快照面向 MC 26.2**（`gradle.properties` `minecraft_version = 26.2.0`；`gradle/libs.versions.toml` `minecraft="26.2"`、`fabric_loader=0.19.3`、`fabric_api=0.152.1+26.2`、`neoforge=26.2.0.0-beta`）。**1.21.1 / 1.20.1 的代码不在本分支**，需切历史 tag/提交后再看。
- Gradle：Fabric Loom 1.17.11 + NeoForge ModDevGradle 2.0.141 + mod-publish-plugin 2.0.0；Java 工具链 25（`build-logic/src/main/kotlin/dynamic_fps.java.gradle.kts`）；3 个平台子工程 `platforms/{common,fabric,neoforge}` + `build-logic` 复合构建集中 `base/java/common` 约定。
- 许可证 MIT（`neoforge.mods.toml:2`；仓库根无 LICENSE 文件）。
- 编译依赖（= 它的 API 来源）：`net.lostluma:battery 2.1.0`（电池 API，`jarJar`/`include` 内嵌）、`me.shedaniel.cloth:cloth-config 26.1.154`（`platforms/common/build.gradle.kts`，`isTransitive=false`，仅编译，用于配置界面）、Fabric 侧 `modmenu`；3 个平台产物都通过 `include(project(":platforms:common"))`（fabric）/`jarJar`（neoforge）打包同一份 common 代码。

## 2. 源码规模与包结构

- 59 个 `.java` / 3916 行（`git ls-files '*.java'`；`platforms/common` 50 个、fabric 5、neoforge 3）。
- 主要包与文件数：`dynamic_fps.impl`（核心 2：`DynamicFPSMod`、`PowerState`）、`.impl.config` 5 + `.config.option` 6、`.impl.feature.state` 4 / `.feature.battery` 4 / `.feature.volume` 1、`.impl.compat` 2、`.impl.mixin` 9 + `.mixin.bugfix` 1、`.impl.service` 3、`.impl.util` 13 + `.util.duck` 2；平台 `net.lostluma.dynamic_fps.impl.fabric(.service/.compat/.mixin)`、`.neoforge(.service)`。
- 最大文件：`compat/ClothConfig.java` 450、`DynamicFPSMod.java` 358、`config/Serialization.java` 236、`feature/battery/BatteryTracker.java` 201、`mixin/SoundEngineMixin.java` 151、`util/Version.java` 127、`feature/state/IdleHandler.java` 114、`config/Config.java` 108。

## 3. 入口与注册

不注册任何游戏对象（无 DeferredRegister / Registrate）。
- NeoForge：`platforms/neoforge/src/main/java/net/lostluma/dynamic_fps/impl/neoforge/DynamicFPSNeoForgeMod.java`，`@Mod(Constants.MOD_ID)`，构造器内 `ModLoadingContext.get().registerExtensionPoint(IConfigScreenFactory.class, ...)`、`modEventBus.addListener(this::registerKeyMappings)`、`NeoForge.EVENT_BUS.addListener(this::renderGuiOverlay)`。
- Fabric：同包 `impl/fabric/...`（入口 + `FabricPlatform`/`FabricModCompat`/`ModMenu`/`FREX` 兼容类，共 5 个）。
- 真正初始化点写在 Mixin 里：`mixin/MinecraftMixin.java:35` `@Inject(method="<init>", at=@At("TAIL"))` → `DynamicFPSMod.init(); DynamicFPSMod.setWindow(this.window.handle());`。
- 平台抽象：`service/Platform.java`、`service/ModCompat.java` 为接口，`service/Services.java:7-8` 用 `ServiceLoader` 加载；各平台提交 `META-INF/services/dynamic_fps.impl.service.Platform`（fabric 指向 `...fabric.service.FabricPlatform`，neoforge 指向 `...neoforge.service.NeoForgePlatform`）。注意：这些资源文件只在 git 索引中，当前工作区是部分检出，本地目录里看不到。
- 双 `fabric.mod.json`：`platforms/common/src/main/resources/fabric.mod.json`（id `dynamic_fps_common`，`custom.modmenu.parent=dynamic_fps`）与 `platforms/fabric/src/main/resources/fabric.mod.json`（id `dynamic_fps`，声明 mixins + accessWidener）。

## 4. 核心系统

1. **电源状态机**（`PowerState.java` + `DynamicFPSMod.java:302-332`）：枚举 `FOCUSED / HOVERED / UNFOCUSED / INVISIBLE / UNPLUGGED / ABANDONED`，每个状态带 `ConfigurabilityLevel(NONE/SOME/FULL)`；`checkForStateChanges0()` 按固定优先级（用户禁用 → 强制低帧 → 焦点/空闲/电池 → hover → 最小化）算出唯一 state，变化时 `handleStateChange(previous, current)` 一次性套用 `DynamicFPSConfig.INSTANCE.get(state)`。
2. **帧率控制**：`mixin/FramerateLimitTrackerMixin.java:32` 注入 `getFramerateLimit` HEAD（cancellable）返回 `max(target, MIN_FRAME_RATE_LIMIT=15)`；`:65` 再用 `@At(value="CONSTANT", args="intValue=60")` 只替换主菜单那个 60 常量，实现 "不破坏 vanilla idle 逻辑地解/限主菜单帧率"。整帧跳过在 `MinecraftMixin.java:41` `@WrapMethod(method="renderFrame")`：`DynamicFPSMod.checkForRender()` 返回 false 时不调用原方法，只 `pauseIfInactive()` + `FramerateLimiter.limitDisplayFPS(15)`；`Constants` 定义 `MIN_FRAME_RATE_LIMIT=15 / NO_FRAME_RATE_LIMIT=260 / TITLE_FRAME_RATE_LIMIT=60`。
3. **窗口与空闲探测**：`feature/state/WindowObserver.java` 用 GLFW 直接读 `GLFW_FOCUSED/HOVERED/ICONIFIED` 并注册 focus/cursor-enter/iconify 回调，回调内先更新自身状态再 **链式调用保存下来的 previous callback**（避免吞掉 vanilha/其它 mod 的回调）；`feature/state/IdleHandler.java` 叠加 cursor-pos 回调 + 每 tick 比对玩家 `position()`/`getLookAngle()`（`checkPlayerActivity`）判断空闲，条件支持 `VANILLA` 与 `ON_BATTERY`。
4. **音量平滑过渡**：`feature/volume/SmoothVolumeHandler.java` 用 `registerStartTickEvent` 每 tick 以 `config.getUp()/20`、`getDown()/20` 步长插值 `Map<SoundSource,Float>`，再经 `util/duck/DuckSoundEngine.java`（接口 mixin，`SoundEngineMixin implements DuckSoundEngine`）调用 `dynamic_fps$updateVolume(source)` 更新正在播放的音源。
5. **图形选项暂存/还原**：`feature/state/OptionHolder.java` `copyOptions(Options)` 把 11 个 vanilla 图形选项存到静态字段，`applyOptions(options, GraphicsState)` 按 `GraphicsState.DEFAULT/REDUCED/MINIMAL` 覆盖（REDUCED 只改不重载世界的项：云、粒子、实体阴影、天气半径）；`DynamicFPSMod.handleStateChange` 里在 `before.graphicsState()==DEFAULT` 时先 copy 再 apply。
6. **配置体系**：`config/Config.java`（每状态的帧率/vsync/音量乘数/图形态/toast/GC 开关，`frameRateTarget==-1` 代表不限帧）、`config/DynamicFPSConfig.java`（`Map<PowerState, Config> configs` + `get(PowerState)`，FOCUSED 直接返回 `Config.ACTIVE`）、`config/Serialization.java`（Gson 读写 `config/dynamic_fps.json`，写前 `removeUnchangedFields` 删掉与默认值相同的字段，写入用临时文件 + `ATOMIC_MOVE` 回退 `REPLACE_EXISTING`，读取时 `upgradeConfig` → `upgradeVolumeMultiplier/upgradeIdleConfig/addMissingFields` 做版本迁移，并对 "Windows 上出现全 0 字节的坏配置" 做降级）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（无 packet 注册）。
- 数据驱动：仅默认配置文件 `platforms/common/src/main/resources/assets/dynamic_fps/data/default_config.json`（`Serialization.loadDefault()` 从 classpath 读，运行期再用它补齐用户配置缺项）；另有大量 `assets/dynamic_fps/lang/*.json` 语言文件。
- datagen：无。
- 平台适配资源：`dynamic_fps.accesswidener`（fabric，1 行）、`META-INF/accesstransformer.cfg`（neoforge，1 行 `public net.minecraft.client.sounds.SoundManager soundEngine`）——同一需求在两个加载器各写一份的最简做法。

## 6. Mixin

- 配置：`platforms/common/src/main/resources/dynamic_fps.common.mixins.json`（`required:true`，`package: dynamic_fps.impl.mixin`，client 10 个：DebugEntryFps / FramerateLimitTracker / Gui / Hud / LoadingOverlay / Minecraft / Options / SoundEngine / ToastManager / bugfix.BlockableEventLoop），平台各有 `dynamic_fps.fabric.mixins.json`、`dynamic_fps.neoforge.mixins.json`（后者当前为空列表）。`overwrites.conformVisibility/requireAnnotations = true`。
- 代表 hook：`MinecraftMixin`（`renderFrame` 用 MixinExtras `@WrapMethod` + `@WrapOperation` 拦截 `OptionInstance.get()` 第 0 次调用以覆盖 vsync；`close` HEAD 关电池追踪）；`OptionsMixin`（`save` HEAD/RETURN 包住，避免保存时把被覆盖的图形选项写回）；`GuiMixin.setScreen` HEAD；`HudMixin.extractCrosshair` RETURN；`SoundEngineMixin.play/playDelayed` HEAD cancellable；`bugfix.BlockableEventLoopMixin` 用 `@Overwrite` 修 vanilla 后台 CPU 占用问题（README 提到的那个 bug）。

## 7. 值得学的 5 条做法

1. `ServiceLoader` + `META-INF/services/<接口全限定名>` 做平台抽象：common 代码只调 `Services.PLATFORM`，平台实现类写在各自模块（`service/Services.java:10`、`platforms/*/src/main/resources/META-INF/services/dynamic_fps.impl.service.Platform`）；适用：任何多加载器库代码。
2. GLFW 回调"包装而不是替换"：保存并透传 previous callback（`feature/state/WindowObserver.java:24-48`、`IdleHandler.onMove`）；适用：给窗口/输入加自己的监听又不想和别的 mod 打架。
3. 用"单一状态字段 + 集中优先级判定"控制全局行为（`PowerState` + `checkForStateChanges0`），所有副作用只在状态切换时执行一次（`handleStateChange`）；适用：AI/实体行为档位、性能调节类模组。
4. 配置序列化三件套：与默认值相同的字段不写盘 + 临时文件原子替换 + `upgradeXxx` 迁移老格式（`config/Serialization.java:26-146`）；适用：任何自管 JSON 配置。
5. 优先用 MixinExtras `@WrapMethod`/`@WrapOperation` 而不是 `@Redirect`/`@Overwrite`：`MinecraftMixin.java:41-68` 只包裹 `renderFrame` 和一处 `OptionInstance.get()` 调用，改动面最小、兼容性最好。

## 8. 公开 API / 扩展点

无对外 API 包。对外可用的仅内部静态入口 `DynamicFPSMod.isDisabled() / powerState() / targetFrameRate() / volumeMultiplier(SoundSource) / shouldShowLevels()`（`DynamicFPSMod.java:65-187`）与 `util/duck/DuckSoundEngine`、`util/duck/DuckLoadingOverlay` 两个 duck 接口（供其它 mixin 判断/驱动），以及 `compat/GLFW.applyWorkaround()`。
