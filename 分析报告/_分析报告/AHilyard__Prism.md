# Prism 源码分析

## 1. 基本信息
- Mod 名 / mod_id：Prism / `prism`（`Prism.java:8` `MODID = "prism"`），版本 `1.0.8`（`gradle.properties` `modVersion`），group `com.anthonyhilyard.prism`
- 作者：anthonyhilyard（`mods.toml` 署名 `Grend`，displayURL https://anthonyhilyard.com/）；定位是库：`mods.toml` 描述 "A library all about color! Provides lots of color-related functionality for dependent mods."
- 分支/版本：git 分支 `1.21-multi`，最新提交 `6d8493c Fixed neoforge loading error.`；**MC 1.21**（`minecraftVersion=1.21`）、Java 21、Mojang 官方映射（`loom.officialMojangMappings()`）
- Gradle 插件：`dev.architectury.loom 1.6-SNAPSHOT` + `architectury-plugin 3.4-SNAPSHOT` + `com.github.johnrengelman.shadow 8.1.1`；`enabledPlatforms=fabric,forge,neoforge`，`settings.gradle` include `common/fabric/forge/neoforge` 四模块
- 许可证：**CC BY-NC-ND 4.0**（`forge/src/main/resources/META-INF/mods.toml`、`neoforge.mods.toml`；与仓库其他 Apache/MIT 生态不同）
- 编译依赖：**无任何 mod 依赖**（根 `build.gradle` 只声明 CurseMaven 仓库，各平台无 dependency 块）；`common` 仅 `modImplementation net.fabricmc:fabric-loader`（注释说明只为了 `@Environment` 注解）。反向依赖方（Iceberg / Legendary Tooltips 等 tooltip 系 mod）的接入代码**不在本仓库，未确认**；本仓库内没有 `iceberg`/`legendary` 字样，只有 `item/ItemColors` 与 tooltip 取值相关

## 2. 源码规模与包结构
- **18 个 `.java`，合计 1527 行**：`common` 16 个（全部逻辑）、`forge` 1、`neoforge` 1；**`fabric/` 目录只有 `build.gradle` 与空的 `gradle.properties`，无 `src/`**（此快照里 Fabric 平台未落地，尽管 `fabric/build.gradle` 有 `processResources` 处理 `fabric.mod.json`）；`common/src/main/resources` 仅 2 个文件：`prism.accesswidener`、`prism.mixins.json`
- 包结构（`common/src/main/java/com/anthonyhilyard/prism/`）：
  - 根：`Prism.java`（仅 MODID + Logger）
  - `events/`：`Event`、`EventFactory`、`ToggleableEvent`（3）；`events/client/`：`RenderTickEvent`（1）
  - `item/`：`ItemColors`（1）
  - `mixin/`：`TextColorMixin`、`MinecraftMixin`（2）
  - `text/`：`DynamicColor`、`TextColors`（2）
  - `util/`：`ConfigHelper`、`ColorUtil`、`IColor`、`ImageAnalysis`、`MinecraftColors`、`WebColors`（6）
- 最大文件：`util/ConfigHelper.java`(404)、`text/DynamicColor.java`(227)、`util/ColorUtil.java`(168)、`util/ImageAnalysis.java`(125)、`item/ItemColors.java`(121)、`mixin/TextColorMixin.java`(80)
- 注意：`util/WebColors.java` 从 classpath 读 `webcolors.csv`（`getResourceAsStream("webcolors.csv")`），**该文件不在本快照的 resources 里，未确认其最终放置位置**

## 3. 入口与注册
Prism **不注册任何方块/物品/实体**，没有任何 `DeferredRegister`，是纯客户端 API 库。入口拆成三层：
- common `com/anthonyhilyard/prism/Prism.java:6-12`：`public static final String MODID = "prism"; public static final Logger LOGGER = ...`，构造函数空（无 `@Mod`）
- Forge `forge/.../PrismForge.java:9-15`：`@Mod(Prism.MODID)`，构造器里只 `ModLoadingContext.get().registerExtensionPoint(IExtensionPoint.DisplayTest.class, ..."ANY"...)`（声明服务端可不同版本）
- NeoForge `neoforge/.../PrismNeoForge.java:6-12`：`@Mod(Prism.MODID)`，构造器为空
- 真正的"注册"发生在类加载与 mixin：`prism.mixins.json`（`required:true`、`client:[TextColorMixin, MinecraftMixin]`、`injectors.defaultRequire=1`、minVersion 0.8.5）+ `prism.accesswidener`（`extendable class net/minecraft/network/chat/TextColor`、两个构造器 extendable、`accessible field ... name`）

## 4. 核心系统
1. **IColor 抽象 + 给原版 TextColor 注入接口**（`util/IColor.java:5-11`：`getName() / getIntValue() / isAnimated()`）。`mixin/TextColorMixin.java:18-37` 让 `TextColor implements IColor`（`@Shadow @Final private String name; @Shadow @Final @Mutable private int value;` 直接暴露），配合 accesswidener 的 `extendable` 使自家 `DynamicColor extends TextColor implements IColor`（`text/DynamicColor.java:14`）能作为**原版颜色**塞进 `Style`，同时被识别为 IColor —— 这是整个库的地基
2. **动态（动画）颜色**（`text/DynamicColor.java`）：字段 `List<IColor> values / float duration / int currentIndex / float timer`；`getIntValue()` **每次调用现算**相邻两色的 A/R/G/B `Mth.lerp`（`:162-186`），不缓存；构造器或 `setDuration` 里 `RenderTickEvent.START.register(this::onRenderTick)`（`:45,152`），`onRenderTick` 用 `tracker.getRealtimeDeltaTicks() / 50.0f` 推进 `timer` 并循环换色（`:212-220`）。工厂方法 `fromRGB/fromARGB/fromHSV/fromAHSV/fromColor` 同时接受 int 与 float；`fromRgb(int)` 用 `Integer.compareUnsigned(value, 0xFFFFFF) >= 0` 启发式判断入参是 AARRGGBB 还是 RRGGBB（`:49-59`）；`isAnimated()` 定义为"多色且 duration>0"
3. **物品名颜色推导**（`item/ItemColors.java:43-120`）：`getColorForItem(ItemStack, TextColor defaultColor)` 是一条 7 级降级链 —— `item.getDisplayName().getStyle().getColor()`（稀有度色）→ `item.getItem().getName(item)` 的 Style 色（绕过改写过 getName 的 mod）→ `item.getHoverName()` 的 Style 色（NBT 里存的颜色）→ `TextColors.findFirstColorCode(hoverName)`（`text/TextColors.java` 手写扫描 `\u00a7` 颜色代码，跳过非颜色格式码）→ `ColorCollector implements FormattedCharSink` 逐字符取第一个带色 Style（`:25-41`）→ **取 tooltip 第一行颜色**（`:87`，注释明确"This is slow, so it better get cached externally!"）→ `defaultColor` → `WebColors.getColor("transparent")`；返回值统一包成 `new DynamicColor((IColor)result)`，使调用方拿到的颜色天然支持动画
4. **配置颜色解析器**（`util/ConfigHelper.java`，库对外最大的 API）：`colorFormatDocumentation(boolean forKey)` 生成配置注释文档（hex/decimal/MC 颜色名/Web 颜色名/修饰符五类，`:21-40`）；`parseColor(Object value, boolean allowAlpha)` 支持 `#F4C`、`0xFEE0`、`#40FF2E`、`#CC00E2EE`、十进制、`"red"`、`"chartreuse"` 以及动画串 **`"<duration>_<color>_<color>..."`**（下划线分隔，首段是 duration 秒，也接受 List 形式，`:156-315`）；`applyModifiers` 表驱动实现 `+/-/= <h|s|v|r|g|b|a><amount>` 修饰符（`Map<Character, BiFunction<Integer,Integer,Integer>>`，`:79-100`）；`validateColor` 用长度白名单（3/4/6/8 或 <=10）做校验（`:321`）
5. **自建跨平台事件总线**（`events/`）：`Event<T>`（`volatile T invoker` + `synchronized` 注册 + `Arrays.copyOf` 扩容 + `listenerCount()`，`:15-71`）、`EventFactory`（`MapMaker().weakKeys()` 登记全部事件，`invalidate()` 重算 invoker，`:6-24`）、`ToggleableEvent`（`disable()/enable()` 切换时返回预生成的 `dummyInvoker`，避免判空）、`events/client/RenderTickEvent.START`（`@FunctionalInterface Start { void onStart(DeltaTracker) }`）。写法与 Fabric Loader 的事件 API 同构，目的是让 common 代码在 Forge/NeoForge 上也能注册客户端 tick 回调
6. **图片主色提取**（`util/ImageAnalysis.java`）：`getDominantColor(ResourceLocation, Rect2i)` 走 `ResourceManager.getResource(...).open()` + `ImageIO.read`（可按区域 `getSubimage`）；算法 = 每像素按 `degrade 0/2/4/6` 右移量化为 4 档分组计数，权重函数**排除近黑(r,g,b<=0.06)与 alpha<0.3** 并偏好亮/不透明色（`:54-75`），最后取 `count * weight` 最大者 `TextColor.fromRgb(...)`。`util/ColorUtil.java` 提供 `combineARGB`（带 clamp）、`AHSVtoARGB`/`ARGBtoAHSV`（手写 HSV 换算，0-255/0-360 与 float 两种重载）

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无**（无 `SimpleChannel`/`PayloadRegistrar`/自定义包；纯客户端库）
- 数据驱动：**无**（`WebColors` 从 classpath 读 `webcolors.csv` 属于静态资源，不是 `ResourceManager` 数据包 loader）
- 配置：Prism 自己**没有 config 文件**；"配置"角色由 `ConfigHelper` 承担 —— 它是给**依赖 mod** 用的：依赖方把用户配置项当 `Object` 丢进 `parseColor`，再用 `colorFormatDocumentation()` 生成注释，靠 `webcolors.csv`/`MinecraftColors` 支持名字写法
- datagen：**无**（无 `GatherDataEvent`、无 provider）
- 平台资源：`forge/src/main/resources/META-INF/mods.toml`（`modLoader="javafml"`、`loaderVersion="[51,)"`、`[[modDependency]]` 经 `build.gradle` 的 `filter` 动态替换成 `[[dependencies.prism]]`、`updateJSONURL=https://mc-update-check.anthonyhilyard.com/638111`），neoforge 版同构（`type="required"`、neoforge `[21,)`）

## 6. Mixin
- 配置：`common/src/main/resources/prism.mixins.json`（`required: true`、`package com.anthonyhilyard.prism.mixin`、`compatibilityLevel JAVA_17`、`target "@env(DEFAULT)"`）
- `mixin/TextColorMixin.java`：
  - `@Inject(method = "<init>(ILjava/lang/String;)V", at = @At("TAIL"))` 与 `@Inject(method = "<init>(I)V", at = TAIL)` —— 都做 `this.value = originalValue & 0xFFFFFFFF`，注释说明是**修原版只支持 alpha <= 0x7F 的问题**（`:39-52`）
  - `@Inject(method = "parseColor", at = HEAD, cancellable = true)` —— 拦截 `#` 开头字符串，`Integer.parseUnsignedInt(substring(1), 16)` 后用 `Integer.compareUnsigned` 校验范围，支持 8 位 AARRGGBB / 4 位 ARGB（`:55-79`）
- `mixin/MinecraftMixin.java`：`@Inject(method = "runTick", at = @At(value = "INVOKE_STRING", target = "Lnet/minecraft/util/profiling/ProfilerFiller;popPush(Ljava/lang/String;)V", args = {"ldc=gameRenderer"}))` —— 用**性能分析器字符串常量**精确定位到"开始渲染"位置，然后 `RenderTickEvent.START.invoker().onStart(instance.getTimer())`（`:15-22`）

## 7. 值得学的 5 条具体做法
1. **用 mixin 给原版类注入接口 + accesswidener 打开字段**：`TextColorMixin implements IColor` 让所有原版颜色对象都能被当作自家颜色；同时 AW 把 `TextColor` 声明为 `extendable`，自家 `DynamicColor extends TextColor` 才能合法存在并被塞回 `Style`（`prism.accesswidener`、`DynamicColor.java:14`）—— 扩展原版类型时"注入接口 + 打开继承"的组合是标准解法。
2. **INVOKE_STRING + `ldc=gameRenderer` 作为注入锚点**：不依赖易改的方法名/序数，直接锁定 `ProfilerFiller.popPush` 的这个字符串常量，用于做"渲染帧开始的 tick 事件"（`MinecraftMixin.java:16-17`）；跨版本/跨加载器做客户端 tick 事件时非常实用。
3. **颜色对象惰性求值 + 渲染 tick 驱动动画**：`DynamicColor.getIntValue()` 每次现算插值、只维护 `currentIndex/timer`，动画订阅 `RenderTickEvent.START`（`DynamicColor.java:162-220`），消费方无需关心动画，只要每次渲染取一次颜色。
4. **把"用户配置字符串 → 颜色"做成可复用工具与文档生成器**：`ConfigHelper.parseColor` 支持 hex/decimal/颜色名/动画串四种写法，`colorFormatDocumentation(boolean)` 直接给依赖 mod 生成配置备注，`applyModifiers` 用 `Map<Character, BiFunction>` 表驱动 `+/-/=` 修饰符（`ConfigHelper.java:79-100`）——任何"让玩家自定义颜色"的 mod 都可直接抄这套格式与实现。
5. **`FormattedCharSink` 抓取首个带色字符**：`ItemColors.ColorCollector.accept()` 返回 false 提前终止遍历（`ItemColors.java:29-41`），是低成本从 `Component` 里提取"实际渲染颜色"的技巧；配套的 7 级降级链顺序（名字 → Item.getName → hoverName → 颜色代码 → 逐字符 → tooltip 首行 → 默认 → transparent）本身就能当"物品显示色优先级"的参考实现。
6. 补充（构建侧）：Architectury 多平台用 `common(project(path: ':common', configuration: 'namedElements'))` 编译 + `shadowBundle project(path: ':common', configuration: 'transformProductionForge/NeoForge/...')` 打包进各平台产物；Forge 侧因 architectury 的 bug 手动把 access widener 转 access transformer（`forge/build.gradle` 的 `ModBuildExtensions.convertAwToAt` + 反射取 `RemapJarTask.serviceManagerProvider`、`remapJar.atAccessWideners.add('prism.accesswidener')`）。

## 8. 公开 API 与外部接入
- 公开 API 包（依赖方直接静态调用，无 ServiceLoader/注解式注册）：
  - `com.anthonyhilyard.prism.util`：`IColor`（最小颜色接口：`getName/getIntValue/isAnimated`）、`ColorUtil`（ARGB/HSV 互转）、`ConfigHelper`（`parseColor`/`applyModifiers`/`colorFormatDocumentation`/`validateColor`）、`MinecraftColors`（16 个原版颜色名，静态块遍历 `ChatFormatting.values()` 建表）、`WebColors`（140 个 HTML 颜色名 + `transparent`，键经 `ConfigHelper.formatColorName` 归一化：小写去空格下划线）、`ImageAnalysis`
  - `com.anthonyhilyard.prism.text`：`DynamicColor`（动画颜色，可直接放进 `Style`）、`TextColors`
  - `com.anthonyhilyard.prism.item`：`ItemColors.getColorForItem(ItemStack, TextColor)`（注释要求调用方自行缓存）
  - `com.anthonyhilyard.prism.events(.client)`：`Event`/`EventFactory`/`ToggleableEvent`/`RenderTickEvent`
- 扩展点：依赖方在配置里写颜色/动画串 → `ConfigHelper.parseColor`；给方块/物品贴图自动配色 → `ImageAnalysis.getDominantColor`；自定义动画色 → `new DynamicColor(list, duration)` 或 `addColor/setDuration`；客户端每帧回调 → `RenderTickEvent.START.register(...)`。发布形态依赖 Architectury，消费方需按平台引入对应 `prism-<mcversion>-<platform>` 产物。
