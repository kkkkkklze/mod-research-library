# decce6/Gnetum 源码分析报告

## 1. 基本信息
- Mod 名：Gnetum；mod_id：`gnetum`；作者：decce；许可证：**LGPL-3.0-only**；mod_version `4.5.4`
- 定位（README）：把一次完整 HUD 更新拆成多个 "pass" 分摊到多帧、用双帧缓冲交换的方式降低 HUD 渲染开销，并提供 HUD FPS 上限
- 目标版本/加载器：**Stonecutter 多版本多加载器**，`versions/` 下存在 `1.20.1-fabric`、`1.20.4-fabric`、`1.21.1-fabric`、`1.21.4-fabric`、`1.21.11-fabric`、`1.21.11-neoforge`、`26.1-fabric/neoforge`、`26.2-fabric/neoforge`；`stonecutter.gradle.kts:5` 当前 `stonecutter active "1.21.11-fabric"`（**本仓库快照未包含 1.21.1-neoforge 目标**）
- Gradle：Stonecutter `dev.kikugie.stonecutter 0.9.7` + Fabric Loom `net.fabricmc.fabric-loom-remap 1.17-SNAPSHOT`（`build.loom.gradle.kts`）或 ModDevGradle `net.neoforged.moddev 2.0.141`（`build.mdg.gradle.kts`）+ `com.gradleup.shadow` + mod-publish-plugin；`buildSrc` 提供 `gnetum-common-conventions`
- 源码为 **Stonecutter 预处理格式**：`//? >=1.21.10 { ... }`、`/*...*///?` 注释块 + `//$ swap` 常量替换（`Gnetum.java:13-25`、`stonecutter.gradle.kts:12-50`），同一份 `src/` 编译出所有版本
- 编译依赖（按版本条件注入）：Fabric API、NeoForge、Sodium（新旧两套：`deps.sodium` / `deps.sodium_legacy`）、Jade、Xaero's Minimap、JourneyMap、ImmediatelyFast；`neoforge.mods.toml` 里以 `[modproperties.gnetum] "sodium:config_api_user" = "me.decce.gnetum.compat.sodium.SodiumEntrypoint"` 挂 Sodium 配置 API

## 2. 源码规模与包结构
- 75 个 `.java`，合计 **4720 行**
- 包（第 3 层）：`me.decce.gnetum`（根 11 个类）、`hud`(4)、`mixins`(17)+`mixins/compat/{bossbar,effects,jade,journeymap,sodium,xaerominimap}`+`mixins/{fabric,neoforge}`、`platform`+`platform/{fabric,neoforge}`、`time`(2)、`util`(5)、`versioned`(3)、`compat/{sodium,jade,journeymap,xaerominimap,immediatelyfast,legacy_fapi,neoforge}`
- 最大文件：`hud/VanillaHuds.java`(438)、`mixins/GameRendererMixin.java`(324)、`mixins/HudMixin.java`(265)、`Framebuffers.java`(181)、`Gnetum.java`(179)、`compat/sodium/SodiumEntrypoint.java`(157)、`FramebufferBlitter.java`(157)、`mixins/GuiRenderStateMixin.java`(151)、`hud/Hud.java`(127)、`GnetumConfig.java`(120)

## 3. 入口与注册
双加载器入口都只做一件事（`platform/fabric/FabricEntrypoint.java`、`platform/neoforge/NeoforgeEntrypoint.java`，后者 `@Mod(value = "gnetum", dist = Dist.CLIENT)`）：
```java
public class FabricEntrypoint implements ClientModInitializer {
    @Override public void onInitializeClient() { Gnetum.init(); }   // → GnetumConfig.reload(); config.save();
}
```
- 无内容注册表；`Gnetum` 用 `Platform` 接口 + `createPlatformInstance()` 的 Stonecutter 条件编译实现加载器分派（`Gnetum.java:160-172`）。
- 元素（HUD 组件）收集走 `platform/ElementGatherer`（抽象类，`gather()` 用 `LinkedHashMap<String,CachedElement>` 去重并迁移用户开关）→ `ElementGathererFabricImpl`（反射 `HudElementRegistryImplAccessor` 拿 first/last/vanillaElementIds）/ `ElementGathererNeoForgeImpl`（走 `GuiLayerManager` accessor）。

## 4. 核心系统
1. **Pass 调度**：`Gnetum.pass` + `nextPass()`（`Gnetum.java:53-70`）——只有 `FPS_COUNTER.belowMax()` 时才推进/收尾；`finishAllPasses()` = `Distributor.resolve()` + `framebuffers().swapFramebuffers()` + `HudDeltaTracker.reset()`（`:72-76`）。
2. **双帧缓冲**：`Framebuffers` 持有 `back/front` 两个 `TextureTarget`（名称 `gnetum_back/front`，清屏色透明、`GL_NEAREST`），每帧只把 `front` blit 到屏幕；支持 `downscale`、`markForCatchUp()`、`dropCurrentFrame()`；`Gnetum.checkForPoseCatchUp()` 比较 `GuiGraphics` 的矩阵（`Matrix3x2f`/`Matrix4f`，容差 0.01F），姿态变化时触发 catch-up（`Gnetum.java:78-91`、`Framebuffers.java`）。
3. **按耗时自动分配 pass**：`Distributor.resolve()` 累计所有元素的 5 次采样耗时总和，`target = totalTime / passCount`，再顺序累加、超过 target 就 `pass++`（`Distributor.java:12-43`）；`CachedElement` 保存 `TriStateBoolean enabled`（AUTO/ON/OFF）+ `time[5]` 环形采样 + `begin()/end()` 用 `TimeSource`（GLFW 时间）计时，`shouldRender()` 只在"自身 pass == 当前 pass"时渲染（`CachedElement.java:24-45`）。
4. **原版 HUD 拆分**：`hud/VanillaHuds.java` 把 `Gui` 的私有渲染方法用 accessor 拆成带 id 的 `Hud`（`camera_overlays`、`crosshair`、`hotbar`、`experience_level`、`effects`、`boss_overlay` …），每个 `Hud` 声明 blend/depth 状态并 `HudManager.register(this)`（`hud/Hud.java:24-50`）。
5. **HUD 时间与 FPS 上限**：`FpsCounter` + `GnetumConfig`（`numberOfPasses` clamp 2-10、`maxFps` 1-125=无限、`screenMaxFps` 1-65）；`HudDeltaTracker` 按 pass 分槽累计 `DeltaTracker` 的 realtime/gameTime，保证 HUD 动画速度与真实时间一致（`HudDeltaTracker.java`）。
6. **兼容层**：`compat/` 下 Sodium（含 legacy sodium 页面 `LegacySodiumPage`）、Jade、JourneyMap、Xaero、ImmediatelyFast、legacy Fabric API（`ArrayBackedEventAccessor`）、NeoForge 事件总线（`EventBusAccessor`），并各自配 `mixins/compat/**` 注入。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无**（纯客户端渲染 mod）。
- 配置：自定义 `config/gnetum.json`（Gson，`GnetumConfig.load/save`），字段 `enabled`、`showHudFps`、`downscale`、`fastFboBlit`（均 `TwoStateBoolean`）、`numberOfPasses`、`maxFps`、`screenMaxFps`，以及 **`LinkedHashMap<String,CachedElement> map`（每个 HUD 元素的 AUTO/ON/OFF 开关，随元素收集动态生成并持久化）**；`validate()` 做 clamp（`GnetumConfig.java:29-119`）。
- 数据驱动：只有 assets（`assets/gnetum/gnetum.png` 等）；无数据包/codec 注册。
- datagen：**无**（`createMinecraftArtifacts` 依赖 `stonecutterGenerate`，属预处理而非 datagen）。

## 6. Mixin
- 配置：`src/main/resources/gnetum.mixins.json`（24 个 client mixin）、`gnetum.neoforge.mixins.json`（`neoforge.HudAccessor`、`neoforge.GuiLayerManagerAccessor`、`neoforge.GuiLayerManagerMixin`）、`gnetum.fabric.mixins.json`
- 代表 1：`mixins/HudMixin.java` → `@Mixin(value = Gui.class, priority = 5000)` + MixinExtras `@WrapMethod(method = "render")`（`>26` 时 `extractRenderState`），在 `Gnetum.config.isEnabled()` 为真时接管整个 HUD 渲染并按 pass 决定哪些元素渲染；含 `@Shadow leftHeight/rightHeight` 与 `gnetum$lastLeftHeight` 状态保持，另用 `@WrapWithCondition` 过滤 `HudRenderCallback`。
- 代表 2：`mixins/GameRendererMixin.java` → `@Inject` 到 `GameRenderer#render` 调用 `Gui#render(GuiGraphics,DeltaTracker)` 的 INVOKE 点（版本不同目标不同，`>=1.21.1` / `>26` / `>=26.2` 各有 Stonecutter 分支），做 delta tracker 采样与 pose catch-up，并处理"界面打开/隐藏 HUD"的状态切换。
- 其他：`GuiRenderStateMixin`、`GlStateManagerMixin`、`GpuBufferPoolMixin`、`MappableRingBufferMixin`（缓冲/状态相关）、`MinecraftMixin`、`DeltaTrackerMixin`、`DebugEntryFpsMixin`（F3 显示 `HUD: x fps T: y (n passes)`）。

## 7. 值得学的 5 条具体做法
1. **"按实测耗时切帧"的思想**：`CachedElement.time[5]` 环形采样 + `Distributor.resolve()` 按累计耗时切 pass（`Distributor.java:12-43`），比固定 N 等分更均衡；也示范了"用采样替代配置估算"的性能设计。
2. **双帧缓冲 + 帧尾 blit** 把昂贵的 HUD 绘制摊薄到多帧，并对 `GuiGraphics` 姿态做容差比较触发 catch-up，避免动画/缩放时错位（`Framebuffers.java`、`Gnetum.checkForPoseCatchUp`）。
3. **Stonecutter 单源多版本**：`//? >=1.21.10 { ... } /*...*///?` 注释块 + `//$` 常量替换 + `swaps`（如 `ResourceLocation`→`Identifier`、`GuiGraphics`→`GuiGraphicsExtractor`），一份 `src/` 覆盖 Fabric/NeoForge × 1.20.1~26.2（`stonecutter.gradle.kts:12-60`、`Gnetum.java:13-25`）。
4. **加载器差异集中在一个 `Platform` 接口 + abstract `ElementGatherer`**，其余代码完全平台无关；对第三方 HUD（Jade/Xaero/JourneyMap）用"每个 mod 一个 compat 类 + 独立 mixin 子包 + 条件常量"管理（`platform/Platform.java`、`compat/**`）。
5. **AUTO 开关的降级策略**：元素默认 `AnyBooleanValue.AUTO`，检测到不兼容时 `Gnetum.disableCachingForElement(element, reason)` 打印原因并永久禁用缓存 + `framebuffers().dropCurrentFrame()`（`Gnetum.java:104-119`），可自动兜底。
6. **配置里直接序列化"元素开关表"**（`LinkedHashMap<String,CachedElement>`），且 `ElementGatherer` 重新收集时按名字迁移用户已有开关（`ElementGatherer.gather()`），配置与代码演进解耦。

## 关键词
HUD 分帧渲染、双 Framebuffer 交换、按耗时分配 pass、Stonecutter 多版本、MixinExtras WrapMethod
