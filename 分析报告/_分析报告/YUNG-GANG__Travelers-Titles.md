# YUNG-GANG/Travelers-Titles 源码分析报告

## 1. 基本信息

- Mod 名：Traveler's Titles；mod_id `travelerstitles`；作者 YUNGNICKYOUNG；group `com.yungnickyoung.minecraft.travelerstitles`
- 目标版本与加载器（`gradle.properties`）：`mc_version=26.1.2`（范围 `[26.1,)`）、`neoforge_version=26.1.2.75`、Fabric `fabric_version=0.150.0`/`fabric_loader_version=0.18.6`，project `version=6.1.0`，`java_version=25`；**多加载器（Common + Fabric + NeoForge 三子项目）**
- Gradle：根 `build.gradle` 声明 `net.fabricmc.fabric-loom` 1.15.5 + `net.neoforged.moddev` 2.0.141（apply false），发布用 curseforgegradle 1.1.24 / Minotaur；`buildSrc/src/main/groovy/multiloader-common.gradle` 与 `multiloader-loader.gradle` 是 YUNG 自研的多加载器公共脚本（`processResources` 用 `expand` 统一填充 mods.toml/mixins.json/pack.mcmeta）
- 许可证：LGPLv3
- 编译依赖（关键）：**YUNG's API（YungsApi）6.1.0**，Common 用 `compileOnly`、Fabric/NeoForge 用 `implementation`（`Common/build.gradle:20-22`）→ 它是运行前置。NeoForge 侧另有 Balm/Waystones 兼容（`waystones_version=26.1.2.5`、`balm_version=26.1.2.6`）；Fabric 侧 clothconfig/modmenu 为可选 GUI

## 2. 源码规模与包结构

- 43 个 `.java`，共 2079 行（实测 `find`+`wc -l`）
- Common：`travelerstitles`(1) / `command`(3) / `mixin`(3) / `module`(5) / `render`(2) / `services`(5)
- NeoForge：`travelerstitles`(1) / `config`(5) / `module`(2) / `services`(4)
- Fabric：`travelerstitles`(1) / `config`(4+gui) / `mixin`(1) / `module`(1) / `services`(4)
- 最大文件：`Common/.../render/TitleRenderManager.java` 240、`NeoForge/.../services/NeoForgeWaystonesCompatHelper.java` 179、`Common/.../render/TitleRenderer.java` 173、`NeoForge/.../config/ConfigWaystonesNeoForge.java` 146、`ConfigBiomesNeoForge.java` 138

## 3. 入口与注册

Common 入口 `Common/src/main/java/com/yungnickyoung/minecraft/travelerstitles/TravelersTitlesCommon.java:18-21`：

```java
public static void init() {
    YungAutoRegister.scanPackageForAnnotations("com.yungnickyoung.minecraft.travelerstitles.module");
    Services.MODULES.loadModules();
}
```

NeoForge 入口（`NeoForge/.../TravelersTitlesNeoForge.java:15-21`）`@Mod(value = MOD_ID, dist = Dist.CLIENT)`，注入 `IEventBus, ModContainer`，依次调 `TravelersTitlesCommon.init()` → `ConfigModuleNeoForge.init(container)` → `RenderGuiNeoForge.init(eventBus)`；Fabric 入口 `Fabric/.../TravelersTitlesFabric.java` 实现 `ClientModInitializer#onInitializeClient` 只调 `Common.init()`。

注册框架：**完全依赖 YUNG's API 的 AutoRegister 注解**，不用 DeferredRegister。`module/SoundModule.java:7-16`：类上 `@AutoRegister(MOD_ID)`，字段上 `@AutoRegister("biome")` + `AutoRegisterSoundEvent.create()`；命令同理 `module/CommandModule.java:52-62`（`@AutoRegister("biome_title")` + `AutoRegisterCommand.of(BiomeTitleCommand::register)` —— 注意寄存器是 `static` 字段，用注解注册才能避免类加载顺序问题）。

## 4. 核心系统

**a. 标题渲染器**（`Common/.../render/TitleRenderer.java`）：泛型 `TitleRenderer<T>`，状态为 `titleTimer/cooldownTimer/displayedTitle/recentEntries(LinkedList<T>)`；`renderText` 按 fadeIn/display/fadeOut 三段算 alpha（`:64-118`），`addRecentEntry` 用 `maxRecentListSize` 做滑动窗口，`matchesAnyRecentEntry(Predicate<T>)` 做"最近去过"判重。渲染走 `GuiGraphicsExtractor#text` + `pose().pushMatrix()/scale()`。

**b. 标题调度中心**（`Common/.../render/TitleRenderManager.java`）：持有 biome/dimension 两个 renderer 并在构造时从 config 取参（`:25-51`）；`playerTick(Player)`（`:79-99`）判断是否地下、更新维度标题→Waystone 标题→生物群系标题（Waystone 可覆盖群系标题，此时 `biomeTitleRenderer.clearTimer()`）；`clientTick()` 只在 `!Minecraft.isPaused()` 时递减计时器（`:57-63`）。

**c. 名称与颜色本地化约定**：`Util.makeDescriptionId("biome", id)` 取原版名，先用 `Util.makeDescriptionId(MOD_ID + ".biome", id)` 查玩家覆写名（`:174-188`）；颜色取同名 lang key + `.color`（如 `biome.minecraft.plains.color`）作为十六进制字符串，找不到就回落默认色（`TitleRenderer.setColor` 解析失败回落白色，`:143-151`）。维度同理，未知维度显示 `"???"`。

**d. 平台服务抽象**（`Common/.../services/`）：`Services.load(clazz)` 用 `java.util.ServiceLoader.findFirst()` 依次加载 `IPlatformHelper / IModulesLoader / IConfigReloader / IWaystonesCompatHelper`（`services/Services.java:62-75`），各加载器提供实现类；`IModulesLoader.loadModules()` 是 default 方法，子类 `super.loadModules()` 追加平台模块。→ 这是"common 代码不认识加载器 API"的关键技巧。

**e. Waystones 软兼容**（`module/CompatModule.java:35-41` + `NeoForge/.../services/NeoForgeWaystonesCompatHelper.java`）：`Services.PLATFORM.isModLoaded("waystones") && getPlatformName().equals("NeoForge")` 时才 `Services.WAYSTONES.init()`，内部复用同一个 `TitleRenderer<Waystone>` 并订阅 `WaystonesListReceivedEvent.EVENT`、`PlayerTickEvent.Post` 找最近石碑；`IWaystonesCompatHelper` 暴露 `init/updateWaystoneTitle/clientTick/renderText/reset/isRendering/updateRendererFromConfig` 七个方法，无兼容时是空实现，避免硬依赖。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包（纯客户端渲染，服务端不参与）。
- 配置：NeoForge 侧 `NeoForge/.../config/TTConfigNeoForge.java`（`ModConfigSpec.Builder` 静态块 + 4 个子配置类），注册为 **CLIENT 类型**并指定文件名 `travelerstitles-neoforge-26_1.toml`（`module/ConfigModuleNeoForge.java:18`）；Fabric 侧用 Cloth Config/AutoConfig（`config/TTConfigFabric`+`gui/TTModMenu`）。同步策略是"平台 config → common 可变 POJO"：`bakeConfig()` 把每个 `ModConfigSpec.ConfigValue#get()` 抄进 `ConfigModule` 的静态内部类 `Biomes/Dimensions/Sound/Waystones`（`ConfigModuleNeoForge.java:38-88`），再由 `ConfigModule.updateRenderersFromConfig()` 回写 renderer 字段；触发点是 `LevelEvent.Load` 与 `ModConfigEvent`（`:23-36`）。
- 数据驱动：`module/TagModule.java:26` 定义 `TagKey<Biome> IS_UNDERGROUND`（`travelerstitles:is_underground`），与 `Biomes.LUSH_CAVES/DRIPSTONE_CAVES` 一起用于"地下群系不显示标题"。
- datagen：无。

## 6. Mixin

- Common 配置 `Common/src/main/resources/travelerstitles.mixins.json`（`required:true`，`client` 段 3 个）：`MinecraftClientTickMixin`（`Minecraft.tick` HEAD → `titleManager.clientTick()`）、`LocalPlayerTickMixin`（`LocalPlayer.tick` TAIL → `playerTick(this)`，类上 `extends Player` 以便调用父类构造）、`EntityChangeDimensionMixin`（`Entity.teleportCrossDimension` TAIL → `playerChangedDimension`，用于切维度时清缓存）。
- Fabric 额外配置 `Fabric/src/main/resources/travelerstitles_fabric.mixins.json`：`RenderGuiTickMixinFabric`（Fabric 侧无 GuiLayer API，用 mixin 挂渲染）。
- NeoForge 侧**不 mixin 渲染**，改用 `RegisterGuiLayersEvent`（`NeoForge/.../module/RenderGuiNeoForge.java:38-44`，`event.registerAboveAll(id("overlay"), RenderGuiNeoForge::render)`）。

## 7. 值得学的 5 条具体做法

1. **ServiceLoader 做多加载器平台抽象**：`Services.load(clazz).findFirst().orElseThrow()`，common 只写接口，平台模块提供实现 —— `Common/.../services/Services.java:68-74`；任何多加载器项目直接可用。
2. **YUNG's API AutoRegister 注解注册**：`@AutoRegister("biome")` + `AutoRegisterSoundEvent.create()` 把寄存器字段声明与注册时机解耦 —— `Common/.../module/SoundModule.java:7-16`，配合 `YungAutoRegister.scanPackageForAnnotations("...module")` 一行扫包。
3. **"平台 config → common POJO → 渲染器"三段式烘焙**：`bakeConfig()` 抄值 + `updateRenderersFromConfig()` 回写，改配置立即生效（`LevelEvent.Load` + `ModConfigEvent` 双触发）—— `NeoForge/.../module/ConfigModuleNeoForge.java:23-36`。
4. **最近去过缓存 + 冷却计时防刷屏**：`recentEntries` 定长滑动列表 + `cooldownTimer` + `displayedTitle` 内容比对（内容相同直接 return）—— `Common/.../render/TitleRenderer.java:153-164`、`TitleRenderManager.java:203-210`；适用于任何"进入区域提示"。
5. **语言文件承载文案与颜色**：标题名走 `travelerstitles.biome.<id>` 覆写 key，颜色走 `<name key>.color`，未提供时不显示 —— `TitleRenderManager.java:174-200`；给整合包/汉化留了零代码定制点。软兼容用 `CompatModule.isWaystonesLoaded` 布尔 + 空实现接口（`CompatModule.java:32-41`）也值得照搬。

## 8. 公开 API

不适用（游戏内容 mod；对外只提供 lang key 覆写约定与 `travelerstitles:is_underground` 群系标签作为接入点）。
