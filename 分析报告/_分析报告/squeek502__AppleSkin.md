# AppleSkin 源码分析报告

## 1. 基本信息
- Mod 名 AppleSkin；mod_id `appleskin`（`resources/fabric.mod.json`）；作者 squeek502。
- 目标版本（`gradle.properties`）：MC `1.21`、yarn `1.21+build.2`、Fabric Loader `0.15.11`、Fabric API `0.100.8+1.21`、Java 21；`build.gradle` 用 `fabric-loom 1.8-SNAPSHOT`，版本号 `mc1.21-3.0.6`，`archives_base_name = appleskin-fabric`。
- 许可证：Unlicense（fabric.mod.json `"license": "Unlicense"`；根 `LICENSE`）。
- 源码布局非标准：`build.gradle:15-16` 把 `java`、`resources` 加进 `sourceSets.main`。
- 编译依赖：`fabric-api`、`modmenu 11.0.0-beta.1`、`cloth-config-fabric 15.0.127`（`modApi` + `include`，jar-in-jar）、`RoughlyEnoughItems-fabric 15.0.728` 与 `jei 19.5.3.67`（仅 compileOnly）。`fabric.mod.json` 声明 `fabricloader>=0.15.10`、依赖 `fabric-api`、`breaks roughlyenoughitems<6.0.306-alpha`。
- 独立发布 API jar：`build.gradle` 的 `apiJar` 任务只打包 `squeek/appleskin/api/**`（classifier `api`），随 `mavenJava` 发布。

## 2. 规模与包结构
29 个 `.java`、2043 行（`find/java wc -l`）。包（`java/squeek/appleskin/`）：`client`(5)、`mixin`(8)、`api/event`(3)+`api/handler`(1)+`api`(1)、`network`(4)、`helpers`(4)、`gui`(1)、`util`(1)、根(2)。最大文件：`client/HUDOverlayHandler.java` 578、`client/TooltipOverlayHandler.java` 382、`helpers/FoodHelper.java` 179、`api/event/HUDOverlayEvent.java` 94、`ModConfig.java` 65、`helpers/TextureHelper.java` 59、`network/SyncHandler.java` 51。资源：18 种语言 lang、`icons.png`、`appleskin.png`、两个 mixin json。

## 3. 入口与注册
`fabric.mod.json` entrypoints：client=`squeek.appleskin.AppleSkin`、main=`AppleSkinCommon`、modmenu=`gui.ModMenuIntegration`、rei_client=`client.REITooltipPlugin`。
`AppleSkin.onInitializeClient`（`AppleSkin.java:18-35`）顺序调用 5 个 `init()`：`ClientSyncHandler`、`ModConfig`、`HUDOverlayHandler`、`TooltipOverlayHandler`、`DebugInfoHandler`，随后遍历第三方入口点：`FabricLoader.getInstance().getEntrypointContainers("appleskin", AppleSkinApi.class)` 并 `registerEvents()`，逐个 try/catch 隔离错误。`AppleSkinCommon` 只在服务端调 `SyncHandler.init()`（payload 注册：`PayloadTypeRegistry.playS2C().register(ID, CODEC)`，`SyncHandler.java:14-18`）。无 DeferredRegister（Fabric 侧无此概念）。

## 4. 核心系统
1) HUD 叠加（主系统）：`client/HUDOverlayHandler.java` 单例 `INSTANCE`（:28，由 `init()` 创建，mixin 里判空后转发）。`onPreRenderFood` 画耗尽度（exhaustion）底条、`onRenderFood` 画饱和度与手持食物预测、`onRenderHealth` 画预估回血；每处先构造 `HUDOverlayEvent.X` 并 `EVENT.invoker().interact(...)`，`isCanceled` 同时承载“配置关闭”和“其他 mod 取消”（:79-91）。闪烁动画在 `onClientTick`（:355-367）用 `unclampedFlashAlpha`/`alphaDir` 推进，最终乘 `ModConfig.maxHudOverlayFlashAlpha`。
2) 原版图标抖动对齐：内部类 `OffsetsCache`（:409-537）用 `random.setSeed(guiTicks * 312871)` 复刻原版 PRNG，**食物与生命偏移必须同批生成**（:418-422 注释：生命抖动的 PRNG 消耗会影响食物），结果按 `lastGuiTick` 缓存、复用 `IntPoint` 对象；`healthBars>1000` 时直接置 0 关闭绘制（:436-439）。
3) 手持食物缓存：`HeldFoodCache`（:539-577）同 tick 只查询一次，主手不可食用时按 `showFoodValuesHudOverlayWhenOffhand` 回退副手，`result==null` 表示不绘制。
4) 数值计算：`helpers/FoodHelper.java`；`getDefaultFoodValues` 用 `DataComponentTypes.FOOD` + `EMPTY_FOOD_COMPONENT` 兜底（:28-36）；`query()` 发出 `FoodValuesEvent` 允许改 default/modified 两个 `FoodComponent`；`getEstimatedHealthIncrement`（:117-178）模拟自然回血循环，用 `Float.compare(saturationLevel, Float.MIN_NORMAL)` 防浮点卡死（:134-137），并把“快回血”分支的百万次迭代用乘加一次性推算（:162-167）。
5) 工具提示：`client/TooltipOverlayHandler.java` 由 `ItemStackMixin` 注入 `ItemStack.getTooltip` 的 RETURN，向原版 list 里塞自定义 `FoodOverlay`（实现 `TooltipComponent`+`TooltipData`），绘制时用 `FoodOutline` 叠轮廓；`shouldShowTooltip` 依据 `TooltipType` 与配置决定 shift/常显。
6) 饥饿/耗尽度同步：`network/SyncHandler.java` 每 tick 采样，仅当饱和度变化、或耗尽度变化 ≥0.01f 才发 `SaturationSyncPayload`/`ExhaustionSyncPayload`（record + `CustomPayload`，float 单字段）；`onPlayerLoggedIn` 清缓存（`PlayerManagerMixin` 注入 `onPlayerConnect`）；客户端 `ClientSyncHandler` 直接在客户端线程写 `HungerManager.setSaturationLevel/setExhaustion`。

## 5. 网络 / 配置 / datagen
网络：2 个 S2C payload（`squeek.appleskin:saturation`、`:exhaustion`），服务端 mixin 触发同步，无自定义包体逻辑。配置：Cloth `AutoConfig` + Jankson（`ModConfig.java`，`@Config(name="appleskin")`，10 个布尔/浮点字段带 `@Comment` 与 `@ConfigEntry.Gui.Tooltip`），ModMenu 屏 `AutoConfig.getConfigScreen`。无 datagen。

## 6. Mixin
主配置 `resources/appleskin.mixins.json`（`required: true`、`package squeek.appleskin.mixin`、`JAVA_21`、`defaultRequire: 1`、`maxShiftBy: 2`）：服务端 `ServerPlayerEntityMixin`（`tick` HEAD）、`PlayerManagerMixin`（`onPlayerConnect` TAIL）；客户端 `InGameHudMixin`（`renderFood` HEAD/RETURN、`renderHealthBar` RETURN）、`MinecraftClientMixin`（`tick` HEAD）、`ItemStackMixin`（`getTooltip` RETURN）、`TooltipComponentMixin`、`DebugHudMixin`（`getLeftText` RETURN）。
副配置 `resources/appleskin.jei.mixins.json`（`required: false`，仅 `JEIRenderHelperMixin`），在 fabric.mod.json 里以 `"environment": "client"` 声明，属可选兼容 mixin 的正确写法。

## 7. 值得学的做法
- mixin 只做“薄转发”：所有逻辑在 client handler 单例里，`InGameHudMixin.java:16-35` 三处注入合计不到 15 行，游戏版本升级时只改注入点。
- 复刻原版随机抖动时不能只算自己那一条：`OffsetsCache.generate` 明确注释必须与生命条同批推进 PRNG（`HUDOverlayHandler.java:418`）。
- 模拟循环要防死循环与浮点退化：`Float.compare(..., Float.MIN_NORMAL)`（`FoodHelper.java:134`），并用数学等价推导替代百万次迭代（:145-167）。
- 事件对象自带 `isCanceled`，让“配置关闭”和“外部 mod 取消”共用一条短路路径（`HUDOverlayHandler.java:82-91`）。
- 零硬依赖的集成协议：`api.AppleSkinApi` + entrypoint 名 `appleskin`，另出 `api` classifier jar 供第三方编译期依赖（`build.gradle` 的 `apiJar`）。
- 同步脏检查 + 阈值 + 登录清缓存（`SyncHandler.java:37-50`），避免每 tick 发包。

## 8. 公开 API
- 包路径 `squeek.appleskin.api`：入口 `AppleSkinApi`（entrypoint `"appleskin"`，`registerEvents()`）。
- 事件：`api/event/FoodValuesEvent`（改 default/modified 食物数值）、`HUDOverlayEvent.{Exhaustion,Saturation,HungerRestored,HealthRestored}`、`TooltipOverlayEvent.{Pre,Render}`；统一通过 `api/handler/EventHandler.createArrayBacked()`（Fabric `EventFactory` 数组后端）注册。
- 接入方式：第三方 mod 的 `fabric.mod.json` 声明 `"appleskin"` entrypoint 实现 `AppleSkinApi`，编译期依赖 `appleskin-fabric:…:api`，运行期无需 AppleSkin 存在（内部遍历入口点时已 try/catch）。
