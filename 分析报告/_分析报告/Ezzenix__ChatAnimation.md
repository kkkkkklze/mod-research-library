# ChatAnimation 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Chat Animation / `chatanimation`（`gradle.properties:5-6`）
- 作者：Ezzenix；版本 1.3.2
- 许可证：`src/main/resources/META-INF/mods.toml` 与 `neoforge.mods.toml` 内写 `license = "MIT"`，但**仓库根目录没有 LICENSE 文件**
- 目标版本：**单代码多版本 + 多加载器**，由 `settings.gradle.kts:24-45` 声明 12 个版本节点：`1.20.1(fabric,forge)`、`1.20.6/1.21.0/1.21.3/1.21.5(三加载器)`、`1.21.2/1.21.6/1.21.9/1.21.11/26.1/26.2(fabric,neoforge)`；当前激活节点 `26.2-fabric`（`stonecutter.gradle.kts:6`）
- 构建插件：`dev.kikugie.stonecutter 0.9.6`（多版本预处理）+ `gg.meza.stonecraft 1.12.2`（加载器/发布/运行配置一站式）+ 作者自研 `com.ezzenix.mcverify 0.1.0`（`build.gradle.kts:6-7`）；Fabric 侧用 loom（`build.gradle.kts:100-106` 对 Forge 调 `forge.mixinConfig(...)`）
- 依赖：`com.ezzenix:emlib`（作者自己的库，`include` 打进 jar）、`io.github.llamalad7:mixinextras-common:0.5.4`（compileOnly + annotationProcessor，注释说明 fabric/emlib 里已有）、Fabric 端可选 `com.terraformersmc:modmenu`
- 各版本依赖集中在 `versions/dependencies/<mc>.properties`（如 `versions/dependencies/26.2.properties`：`minecraft_version/loader_version/fabric_version/neoforge_version/deps.modmenu/deps.emlib`），1.21.11 还带 `yarn_mappings_neoforge_patch`

## 2. 源码规模与包结构

实测：`.java` 文件 **7 个**、共 **397 行**（极小仓库）。包结构 `src/main/java/com/ezzenix/chatanimation/`：

| 包 | 文件（行数） | 说明 |
|---|---|---|
| （根） | `ChatAnimation.java`(81) | 入口 + 动画/透明度工具静态方法 |
| `config/` | `ModConfig.java`(26)、`EasingStyle.java`(27) | 配置声明 + 缓动函数表 |
| `mixin/` | `ChatComponentMixin.java`(128)、`ChatScreenMixin.java`(79)、`GuiMessageLineMixin.java`(40) | 全部逻辑所在 |
| `util/` | `TimestampedMessageLine.java`(16) | 行时间戳接口 |

资源仅 3 个文件：`src/main/resources/chatanimation.mixins.json`、`META-INF/mods.toml`、`META-INF/neoforge.mods.toml`（**无 `fabric.mod.json`、无 lang/贴图**；1.3.2 changelog 称"加入本地化支持"，但仓库内未见 lang 文件 —— 可能由 stonecraft/emlib 生成，未确认）。

## 3. 入口与注册

`src/main/java/com/ezzenix/chatanimation/ChatAnimation.java:9-80`：**同一个文件里用 Stonecutter 注释同时声明三个加载器的入口**：

```java
//? if neoforge {
/*import net.neoforged.fml.ModContainer;
@Mod(value = ChatAnimation.MOD_ID, dist = Dist.CLIENT)
public class ChatAnimation {
*///? }
//? if fabric {
import net.fabricmc.api.ModInitializer;
public class ChatAnimation implements ModInitializer {
//? }
    private static void initialize() { EmConfig.init(MOD_ID, ModConfig.class); }
```

Forge 版用 `FMLJavaModLoadingContext` 构造器、NeoForge 版用 `ModContainer` 构造器、Fabric 版 `onInitialize()`，三者都只调 `initialize()`（初始化 emlib 配置）。**无任何内容注册**（客户端渲染类 mod），也没有 DeferredRegister。

## 4. 核心系统

**(a) 聊天消息整体位移动画**
`mixin/ChatComponentMixin.java:31-46` `calculateDisplacement()`：`System.currentTimeMillis() - lastMessageTime` 算出存活时间 → 与 `ModConfig.fadeTimeMessage` 相除得 `alpha`，`maxDisplacement = lineHeight * 0.8f`，返回 `maxDisplacement - alpha*maxDisplacement`；条件 `chatScrollbarPos != 0` 时返回 0（用户上滚查看历史时不动画）。时间戳在 `addMessage` 的 `@Inject(at = TAIL)` 里写入 `@Unique long lastMessageTime`（行 52-60，用 `//? >=26.1` 分版本给不同方法签名）。
位移实现放在 `ChatAnimation.wrap(GuiGraphics graphics, float displacement, Runnable)`（`ChatAnimation.java:40-52`）：非 0 时 `graphics.pose().pushMatrix()/translate(0, displacement)/popMatrix()`，再执行传入的 `Runnable`。**注入点用 mixinextras `@WrapOperation` 包住具体渲染调用**（而不是 Wrap 整个方法），例如 26.1+ 的 `ChatComponent.extractRenderState` 里包住 `ChatComponent.extractRenderState(ChatGraphicsAccess,int,int,DisplayMode)`（行 94-103），并用 `@Local(argsOnly = true) GuiGraphics graphics` 拿到图形上下文。

**(b) 消息行时间戳（跨类传递状态）**
`mixin/GuiMessageLineMixin.java:13-26`：`@Mixin(GuiMessage.Line.class)` **implements `TimestampedMessageLine`**，加 `@Unique long chatAnimation$addedTime`（`chatAnimation$` 前缀避免与其他 mixin 冲突），在 `<init>` TAIL 打时间戳；`util/TimestampedMessageLine.java:8-15` 提供 `of(GuiMessage.Line)` 强转 + `static float age(line)` 读存活时长。这是"给 vanilla 对象挂自定义字段"的教科书写法。

**(c) 透明度淡入 + 缓动**
`ChatComponentMixin.java:119-126`：`@ModifyVariable(method = "forEachLine", at = @At("STORE"), ordinal = 0)` 改写每行 alpha —— `original * getOpacityFactor(age)`，再过 `EasingStyle.SINE.apply(...)`。`ChatAnimation.getOpacityFactor(float age)`（`ChatAnimation.java:54-61`）返回 `min(age/fadeTime, 1)`，开关关闭或 `fadeTime<=0` 时返回 1。`config/EasingStyle.java` 用枚举 + `Function<Double,Number>` 内置 SINE/QUAD/CUBIC/EXPO/CIRC/BACK/ELASTIC 等 10 种缓动。

**(d) 聊天输入框弹出动画**
`mixin/ChatScreenMixin.java:17-54`：`wasOpenedLastFrame`/`lastOpenTime` 两个 `@Unique` 字段在渲染时惰性判定"刚打开"，`@Inject(method = "removed", at = HEAD)` 重置；位移量乘 `client.getWindow().getHeight()/1080f` 做屏幕尺寸自适应（1080p 基准），再包住 `GuiGraphicsExtractor.fill(...)` 与 `Screen.extractRenderState(...)` 两个调用点做位移（行 60-75）。

**(e) 配置**：`config/ModConfig.java` 继承 `com.ezzenix.emlib.config.EmConfig`，用库提供的注解声明：`@EmConfig.Config(title=...)` 标类、`@Entry(min=10, max=800, isSlider=true, suffix="ms")` 标字段、`@Comment` + 名字带下划线的 `Comment _messages` 字段当分组标题。字段是 `public static`，业务代码直接读（零 getter 开销），配置界面由 emlib 统一提供。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（无 `CustomPacketPayload`、无 channel，纯客户端 mod，`fabric.mod.json`/mods.toml 中 `side = "CLIENT"`、`clientSideOnly=true`）。
- 数据驱动：无。
- 配置：见 4(e)，序列化与 UI 全部委托 `emlib`（`com.ezzenix.emlib.config.EmConfig`），本仓库不负责 IO。
- datagen：**无**（无 `GatherDataEvent`、无 `src/generated`）。

## 6. Mixin

配置：`src/main/resources/chatanimation.mixins.json` —— `required: true`、`minVersion: 0.8`、`package: com.ezzenix.chatanimation.mixin`、`refmap: "${id}.refmap.json"`（占位符由构建期展开）、`compatibilityLevel: JAVA_17`、**`mixins: []` / `server: []`，全部放在 `client` 段**、`injectors.defaultRequire: 1`。neoforge.mods.toml 有 `[[mixins]] config = "${id}.mixins.json"`。

| Mixin | 目标类 | Hook |
|---|---|---|
| `ChatComponentMixin` | `ChatComponent` | `addMessage` @Inject TAIL；`extractRenderState` `@WrapOperation`（1.20.4- 用 `@WrapMethod` 整方法包装，1.21.11 / 26.1+ 用 `@WrapOperation` 包内层调用）；`forEachLine` `@ModifyVariable` STORE ordinal 0（1.21.5- 时改为 `extractRenderState` STORE ordinal 3） |
| `ChatScreenMixin` | `ChatScreen` | `removed` @Inject HEAD；`extractRenderState` 两个 `@WrapOperation`（`GuiGraphicsExtractor.fill(IIIII)V`、`Screen.extractRenderState`），1.21.5- 另有 `EditBox.extractRenderState` |
| `GuiMessageLineMixin` | `GuiMessage.Line` | `<init>` @Inject TAIL 打时间戳；`tag` @Inject HEAD cancellable（`removeMessageIndicator` 时返回 null 去掉消息指示条） |

**多版本差异全靠 Stonecutter 预处理器**：`stonecutter.gradle.kts:8-25` 定义字符串级全局替换表 —— `>=1.21.11`：`ResourceLocation`→`Identifier`；`>=26.1`：`GuiGraphics`→`GuiGraphicsExtractor`、`renderContent`→`extractContent`、`render`→`extractRenderState`、`graphics.drawString(`→`graphics.text(`；`>=26.2`：`minecraft.setScreen(`→`minecraft.gui.setScreen(`、`Minecraft.getInstance().gui.`→`...gui.hud.`。源码内再用 `//? >=26.1 {` … `//? } else { /*…*/ }` 分支、`//~ if >=1.21.6 'pushPose' -> 'pushMatrix'` 行内替换（`ChatAnimation.java:42-51`）。

## 7. 值得学的 5 条具体做法

1. **`@WrapOperation` 包住单个渲染调用做变换**：不改方法整体，只在目标调用前后 push/translate/pop pose —— 见 `mixin/ChatScreenMixin.java:60-75`、`mixin/ChatComponentMixin.java:94-103`。适用：给任意 vanilla UI 局部加位移/缩放动画。
2. **给 vanilla 类挂自定义字段**：`@Mixin(GuiMessage.Line.class) implements TimestampedMessageLine` + `@Unique` 字段，外部通过 `of()` 强转读取 —— `mixin/GuiMessageLineMixin.java:14-18`、`util/TimestampedMessageLine.java:8`。适用：需要按对象记录额外状态（出生时间、动画进度）。
3. **动画"时间戳 + 惰性计算"而非每 tick 更新**：`System.currentTimeMillis()` 差值算 alpha，帧率无关 —— `ChatComponentMixin.java:42-45`、`ChatScreenMixin.java:44-50`。适用：UI 淡入淡出、避免 20fps 限制。
4. **缓动函数做成枚举常量表**：`config/EasingStyle.java:8-19`，`Function<Double,Number>` + `static import java.lang.Math.*`，想加曲线只加一行。适用：任何插值/动画工具类。
5. **Stonecutter + Stonecraft 的多版本工程化**：一个 `src/main` 支撑 12 个 MC 版本 × 3 加载器；入口类在同一文件内用 `//? if fabric/forge/neoforge` 切块；版本依赖放 `versions/dependencies/<mc>.properties`；`build.gradle.kts` 里按 `mod.isFabric`/`mod.isForge` 分支配置发布（Modrinth `DnNYdJsx` / CurseForge `892086`，`environment = CLIENT_ONLY`）与 `modSettings.clientOptions`（固定 GUI 缩放便于截图）。适用：想低成本维护多版本客户端 mod 的开发者。

## 8. 公开 API

非库/前置型 mod，**没有对外 API 包**。但可借鉴其"通用能力下沉到自有库"的做法：配置系统（注解式声明 + 自动配置界面 + 多加载器适配）已抽到独立库 `com.ezzenix:emlib`（本仓库通过 `include(emlib)` 内嵌），业务仓库只留 `ModConfig` 声明（`config/ModConfig.java:5-6`）。多版本依赖坐标 `deps.emlib` 也随 MC 版本在 `versions/dependencies/*.properties` 中切换。
