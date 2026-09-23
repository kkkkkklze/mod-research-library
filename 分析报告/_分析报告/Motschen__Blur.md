# Motschen/Blur 源码分析报告

## 1. 基本信息

- Mod 名 **Blur+** / mod_id `blur` / 作者 Motschen, amiralimollaei, tterrag1098, Pyrofab, backryun, byquanton（`src/main/resources/META-INF/neoforge.mods.toml`）
- 版本 **6.3.1**，`mod.group=eu.midnightdust`
- 目标 MC：**多版本**，1.21.1 / 1.21.5 / 1.21.8 / 1.21.10 / 1.21.11 / 26.1 / 26.2 × **fabric + neoforge**（`versions/` 目录 + `stonecutter.gradle.kts`，当前 active 为 `26.2-neoforge`）；无 Forge
- Gradle：**Stonecutter**（`dev.kikugie.stonecutter`）多版本预处理器 + architectury-loom + `me.modmuss50.mod-publish-plugin`；`build-obfuscated.gradle.kts` / `build-unobfuscated-fabric|neoforge.gradle.kts` 三套构建脚本
- 许可证 **MIT**（neoforge.mods.toml:4）
- 关键依赖 **MidnightLib 1.9.3+**（required，`side=CLIENT`；`build-obfuscated.gradle.kts` 里 `include(midnightlib)` 直接打进 jar）：配置系统用 `eu.midnightdust.lib.config.MidnightConfig`，颜色工具用 `eu.midnightdust.lib.util.MidnightColorUtil`。编译期另引 modmenu（fabric）与 Mixinextras（`com.llamalad7.mixinextras`，用于 `@WrapOperation` / `@WrapMethod` / `@ModifyReturnValue`）

## 2. 源码规模与包结构

实测 **27 个 .java / 1343 行**（单 source set，`versions/` 只放 gradle.properties，靠注释预处理切换代码）。

- `eu.midnightdust.blur`：`Blur.java`(265) —— 全局状态与渲染/动画调度
- `eu.midnightdust.blur.mixin`：**13 个类**（MixinScreen 125、MixinGui 73、MixinDeathScreen 60、MixinBookSignScreen 43、GuiRenderStateMixin 40、MixinAbstractContainerScreen 39、MixinBookViewScreen 36、MixinBookEditScreen 36、MixinTitleScreen 34、MixinOptions 32、MixinAbstractSignEditScreen 30、MixinAbstractCommandBlockEditScreen 29、GuiRenderStateAccessor 20、GuiGraphicsAccessor 19）
- `eu.midnightdust.blur.animations`：`AbstractAnimationHandler`(81)、`IAnimationHandler`(12)、`IEnumAnimationTarget`、`AnimationState`(record)
- `eu.midnightdust.blur.animations.impl`：`GradientAnimationHandler`(59)、`BlurRadiusAnimationHandler`(19)、`BackgroundAlphaAnimationHandler`、三个枚举 Target
- `eu.midnightdust.blur.config`：`BlurConfig`(152，含 `Easing` 枚举与 `RadiusSliderWidget` 内部类)
- `eu.midnightdust.blur.util`：`DebugHudRenderer`(34)

## 3. 入口与注册

无 DeferredRegister、无内容注册，纯客户端渲染 mod。入口是静态 `Blur.init()`（`Blur.java:36-44`），NeoForge 内部类 `Blur.BlurNeoForge`（`@Mod(value = MOD_ID, dist = Dist.CLIENT)`，Blur.java:258-263）调用；Fabric 侧入口 `BlurFabric implements ModInitializer, ClientModInitializer`，整段被 Stonecutter 注释包裹，仅在 fabric 变体生效（Blur.java:245-256）。

```java
// Blur.java:36-44
public static void init() {
    BlurConfig.init(MOD_ID, BlurConfig.class);      // MidnightLib 配置
    if (BlurConfig.configVersion < 3) {             // 配置迁移：老版本补默认值
        BlurConfig.forceEnabledScreens.add("mezz.jei.gui.recipes.RecipesGui");
        ...
        BlurConfig.configVersion = 3;
        BlurConfig.write(MOD_ID);
    }
}
```

全局单例：`blurRadiusAnimation` / `backgroundAlphaAnimation` / `gradientAnimation` 三个静态动画器 + 一个"本帧是否已处理"的 `isProcessingRenderPass` 布尔位（Blur.java:48-54）——没有事件总线，靠 mixin 直接驱动。

## 4. 核心系统

**A. 双动画器 + 缓动曲线**（`animations/AbstractAnimationHandler.java`）
- `AnimationState<E>` 是不可变 record `(timeState, startValue, currentValue, target)`，`stepAnimation()` 用 `Math.lerp(startValue, target.getAnimationTarget(), easing.apply(t))` 求值，`timeState` 钳在 0..1
- 目标切换不立即生效：`setTarget()` 只写 `newTarget`，下一帧 `updateAnimation()` 里 `resetTarget()` 把 `startValue=currentValue`（保证从当前值平滑过渡，不跳变）
- 枚举实现 `IEnumAnimationTarget` 自带 `getAnimationTarget()` 与 `getAnimationTimeMillis()`；`BlurConfig.Easing` 是带 lambda 的枚举（FLAT/SINE/…/ELASTIC，`BlurConfig.java`）

**B. "屏幕有没有背景"探测**（`mixin/MixinScreen.java`）
- 在 `Screen#renderBlurredBackground` 的 `@At("HEAD")` 设 `blurRadiusAnimation → FadeIn`；在 `renderTransparentBackground` / `renderMenuBackground` 的 HEAD 设 `backgroundAlphaAnimation → FadeIn`（:37-88）
- `MixinGui` 在 `Gui#render/extractRenderState` 的 HEAD/TAIL 调 `Blur.onRender()` / `onRenderEnd()`：onRender 先假设"无背景"把两类动画目标设为 FadeOut，onRenderEnd 再根据本帧探测结果与 `forceEnabledScreens` / `forceDisabledScreens`（存类全限定名字符串列表）覆盖目标，避免重复渲染时闪烁（`Blur.java:89-243`）
- 探测采用"调用即证明"思路，不需要读取屏幕类型白名单

**C. 多版本抽象层**
- `Blur.getCurrentScreen()`、`getRealtimeDeltaTicks()`、`canBlur(graphics)` 三个静态方法是唯一的版本差异出口（`//? if >= 1.21.5` 等注释预处理，Blur.java:56-87）
- `canBlur` 走 accessor mixin：`((GuiRenderStateAccessor)((GuiGraphicsAccessor)graphics).getGuiRenderState()).getFirstStratumAfterBlur() == Integer.MAX_VALUE`——用渲染分层状态判断当前能否再插一次 blur

**D. 崩溃修复型 mixin**（`mixin/GuiRenderStateMixin.java`）
- `@WrapMethod(blurBeforeThisStratum)` 先把 `firstStratumAfterBlur` 重置为 `Integer.MAX_VALUE` 再 `original.call()`，使 MC "一帧只能 blur 一次"的崩溃变成"只保留最后一层 blur"

**E. 渐变背景替换**（`MixinScreen.java:90-125`）
- `@WrapOperation` 包住 `Screen#renderMenuBackgroundTexture` 与 `GuiGraphics#fillGradient`：配置开启 `useGradient` 时改画自己的旋转渐变（`Blur.renderRotatedGradient`），否则 `original.call(...)` 走原版——典型的"可选替换、默认透传"

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络、数据驱动、datagen：**无**（无 assets 数据包、无 codec 数据加载）
- 配置：基于 **MidnightLib** 的注解式静态字段配置（`BlurConfig extends MidnightConfig`，`@Entry @Condition @Comment`，分 animations/style/screens 三个 tab），文件 `config/blur.json`（由 MidnightLib 决定，未在本仓库确认）；含 `configVersion` 字段做迁移
- 配置还能插入自定义控件：重写 `onTabInit()` 往配置界面塞自定义 `RadiusSliderWidget`（直接改 `options.menuBackgroundBlurriness`，上限由 `MixinOptions` 的 `@ModifyArg` 提到 20）

## 6. Mixin

配置：`src/main/resources/blur.mixins.json`（`eu.midnightdust.blur.mixin`，client 列表 15 项，含内部类 `MixinDeathScreen$MixinTitleConfirmScreen`）。

代表性 hook：
- `MixinScreen#blur$onRenderBlurredBackground`：`Screen#renderBlurredBackground` HEAD
- `MixinScreen#blur$replaceMenuBackground`：`@WrapOperation` → `Screen#renderMenuBackgroundTexture`
- `MixinGui#blur$beforeRenderScreen1`：`@ModifyVariable`，锚点 `FIELD Minecraft.screen` + `opcode=GETFIELD`，在"即将渲染屏幕"前插入背景绘制
- `MixinOptions#blur$applyMenuBackgroundBlurCoefficient`：`@ModifyReturnValue` → `Options#getMenuBackgroundBlurriness`
- 各屏幕 mixin 统一在 `extractBackground`/`renderBackground` 的 HEAD 补一次 `extractBlurredBackground`（TitleScreen、DeathScreen、书、告示牌、命令方块）

## 7. 值得学的 5 条具体做法

1. **一次渲染 pass 的幂等保护**：静态 `isProcessingRenderPass` + `forceRenderedBackground` 两个布尔位，把"同一帧被调用多次"降级为日志而非重复绘制 —— `Blur.java:101-142`
2. **动画目标延迟提交**：`setTarget` 只存 `newTarget`，帧末统一 `resetTarget` 并把 `startValue=currentValue`，避免动画中途跳变 —— `animations/AbstractAnimationHandler.java:58-80`
3. **能力探测代替类型判断**：`canBlur()` 用 `firstStratumAfterBlur` 判断能否插 blur，而不是维护"哪些屏幕能 blur"的硬编码 —— `Blur.java:81-87`
4. **第三方屏幕软兼容靠配置字符串清单**：`forceEnabledScreens` / `forceDisabledScreens` 存类全限定名，默认内置 JEI/REI/EMI/Iris，无需编译期依赖 —— `BlurConfig.java`
5. **多版本一号构建用 Stonecutter 注释预处理 + 字符串替换**：`//? if > 1.21.5 {}` 注释块 + `stonecutter.gradle.kts` 里 `replace("ResourceLocation","Identifier")` 等全局改写，13 个 mixin 一份源码吃 7 个 MC 版本 —— `stonecutter.gradle.kts`

## 8. 公开 API

非库 mod，无对外 API 包。可被外部 mod 引用的只有 `Blur` 的静态状态（`reducedBlur`、`forceRenderedBackground`）与配置类字段，未做稳定化封装。
