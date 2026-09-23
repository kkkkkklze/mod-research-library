# MidnightLib 源码分析报告

仓库根：`源码库\_参考仓库\_bulk\TeamMidnightDust__MidnightLib`（以下路径均相对仓库根；工作副本中 `fabric.mod.json`、`assets/*`（贴图/lang）在磁盘上缺失，内容取自 git 对象 HEAD）

## 1. 基本信息

- Mod 名 / ID：MidnightLib / `midnightlib`，group `eu.midnightdust`，版本 1.9.3（`gradle.properties:15-18`）
- 作者：TeamMidnightDust、Motschen；贡献者 maloryware、Jaffe2718（`versions/1.21.1-fabric/src/main/resources/fabric.mod.json`）
- 许可证：MIT（`LICENSE`、`versions/1.21.1-neoforge/src/main/resources/META-INF/neoforge.mods.toml`）
- 定位：库/前置，`"badges": ["library"]`
- 目标版本：Fabric + Forge 1.20.1；Fabric + NeoForge 1.21.1 / 1.21.5 / 1.21.8 / 1.21.10 / 1.21.11 / 26.1 / 26.2（`settings.gradle.kts:29-31`）
- 构建：**Stonecutter 0.9** 多版本工程（`settings.gradle.kts`、`stonecutter.gradle.kts`），三套构建脚本按版本切换：`build-obfuscated.gradle.kts`（Architectury Loom 1.13-SNAPSHOT，≤1.21.11）、`build-unobfuscated-fabric.gradle.kts`（fabric-loom 1.15-SNAPSHOT，≥26.1）、`build-unobfuscated-neoforge.gradle.kts`（neoforged moddev 2.0.141）；Java 目标随版本自动取 17/21/25（`build-obfuscated.gradle.kts` 的 `requiredJava`）。映射为官方 Mojang mappings。发布用 `me.modmuss50.mod-publish-plugin`，产物发布到 `maven.midnightdust.eu`。
- 编译依赖：fabric-loader 0.18.4、fabric-api、**ModMenu 11.0.3（仅 Fabric，`modImplementation`，非运行必需）**、neoforge 21.1.66、forge 47.3.0（`versions/*/gradle.properties`）。**无任何第三方运行时库依赖**，只用 Gson（MC 自带）+ 反射 + Swing（JColorChooser/JFileChooser）。

## 2. 源码规模与包结构

16 个 `.java` 文件、1846 行（`find . -name '*.java' | xargs wc -l`）；其中 main 13 个文件 1554 行，test 3 个文件 292 行。

- `eu.midnightdust.lib.config`（7 文件，**公开 API 包**）：MidnightConfig / MidnightConfigScreen / MidnightConfigListWidget / MidnightSliderWidget / ButtonEntry / EntryInfo / AutoCommand
- `eu.midnightdust.lib.util`（2）：PlatformFunctions、MidnightColorUtil
- `eu.midnightdust.core`（1：MidnightLib 入口）、`core.config`（MidnightLibConfig）、`core.mixin`（MixinOptionsScreen）、`core.screen`（MidnightConfigOverviewScreen）

最大文件：`lib/config/MidnightConfig.java` 418 行、`lib/config/MidnightConfigScreen.java` 343、`test/.../MidnightConfigExample.java` 177、`core/MidnightLib.java` 165、`EntryInfo.java` 104、`AutoCommand.java` 104。

## 3. 入口与注册

无 DeferredRegister、无注册表内容（纯库）。Fabric 入口（`fabric.mod.json`）：client `eu.midnightdust.core.MidnightLib`、server `eu.midnightdust.lib.config.AutoCommand`、modmenu `MidnightLib$ModMenuInit`；依赖仅 `fabric-resource-loader-v0` + minecraft。NeoForge/Forge 用 `@Mod("midnightlib")` 的 `MidnightLib` 构造函数 + `@EventBusSubscriber` 静态内部类（`core/MidnightLib.java:97-164`）。

```java
public void onInitializeClient() {          // MidnightLib.java:68-76
    if (Util.getPlatform() != Util.OS.OSX) { System.setProperty("java.awt.headless","false"); UIManager.setLookAndFeel(...); }
    MidnightLibConfig.init(MOD_ID, MidnightLibConfig.class);
}
```

## 4. 核心系统

1. **注解驱动配置内核** `lib/config/MidnightConfig.java`：`init(modid, class)` 用 `config.getFields()` 反射扫描，`@Entry/@Comment` 才建 `EntryInfo`，`@Server/@Hidden` 跳过、非客户端环境跳过（94-105）；Gson 用 `ExclusionStrategy` 只序列化带 `@Entry` 的字段（48-63），`Identifier` 注册 TypeAdapter；静态 `LinkedHashMap<String,EntryInfo> entries`（键 `modid:fieldName`）+ `configInstances`（65-67）。`getUnderlyingType()` 解析 `List` 泛型并用 `.TYPE` 字段把 `Boolean` 归一成 `boolean`（146-152，所以非原始类型也支持）。
2. **自动生成界面** `lib/config/MidnightConfigScreen.java`：按 `@Entry(category)`/`@Comment(category)` 自动建 Tab（`GridLayoutTab` + `TabManager`，54-70）；控件类型按 `dataType` 分派：枚举/布尔→循环 Button、`isSlider()`→`MidnightSliderWidget`、其余→`EditBox` 且 `setMaxLength(e.width())` + `setResponder(校验谓词)`（201-226）；重置按钮/取色器/文件选择器按需动态插入并把 `widget.setWidth(-22)` 让位（284-297）。
3. **校验与实时同步**：`textField()` 用三条正则（整数/小数/十六进制色）构造 `Predicate<String>`，越界时写 `info.error` + 变红字色，并用 `b.active = entries.values().allMatch(e -> e.inLimits)` 联动 Done 按钮（157-193）；`tick()` 每帧 `info.updateFieldValue()` 回写静态字段，`updateButtons()` 在值==默认值时禁用重置（74-104）；`loadValuesFromJson()` 把 `updateConditions` 丢给 `Minecraft.getInstance().submit(...)` 在渲染线程执行以避免跨线程静态字段访问异常（229-233）。
4. **条件显示** `@Condition(requiredModId/requiredOption/requiredValue/visibleButLocked)`（可重复，跨 mod 用 `"othermod:field"`），由 `EntryInfo.updateConditions()` 求值，状态变化时置 `instance.reloadScreen = true` 触发重建列表（`EntryInfo.java:78-90`、`MidnightConfigScreen.java:85-88`）。
5. **Swing 原生对话框**：取色 `JColorChooser`、文件/目录 `JFileChooser`（含扩展名过滤器）都在临时 `new Thread(...).start()` 里弹，macOS 上按钮 `active=false`（`MidnightConfigScreen.java:239-287`）；入口处把 `java.awt.headless` 置 false。
6. **配置总览屏与指令**：`core/screen/MidnightConfigOverviewScreen.java` 遍历 `configInstances` 列出所有接入 mod 的配置页（`hiddenMods` 可屏蔽）；`lib/config/AutoCommand.java` 反射生成 `/midnightconfig <modid> <field> [value|add|remove]`，参数类型/范围直接取 `@Entry.min/max`，权限等级 2（47-58），列表字段自动带 add/remove 子命令。
7. **平台抽象** `lib/util/PlatformFunctions.java`：`getConfigDirectory/isClientEnv/isModLoaded/registerCommand` 四件事分平台实现；Forge/NeoForge 侧把命令塞进 `MidnightLib.commands` 静态列表，等 `RegisterCommandsEvent` 再注册。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（无包、无同步通道）。配置为客户端本地 JSON，服务器侧靠指令写 `<config>/<modid>.json`。
- 配置：Gson pretty printing，路径 `PlatformFunctions.getConfigDirectory().resolve(modid + ".json")`，可覆盖 `getJsonFilePath()`/`writeChanges()`/`getScreen(parent)`/`onTabInit(tab, list, screen)`（`MidnightConfig.java:258-317`）。
- datagen：无。语言文件为手写 `assets/midnightlib/lang/*.json`（12 种语言）。

## 6. Mixin

配置 `src/main/resources/midnightlib.mixins.json`（`required:true`、`minVersion 0.8`、`compatibilityLevel JAVA_17`、`package eu.midnightdust.core.mixin`、仅 client 一项）。唯一 mixin `core/mixin/MixinOptionsScreen.java`：目标 `net.minecraft.client.gui.screens.options.OptionsScreen`（1.20.x 为 `screens.OptionsScreen`），`@Inject(at=HEAD, method="init")` 在选项屏加一个 20×20 的 `SpriteIconButton`（贴图 `midnightlib:icon/midnightlib`）打开总览屏，`@Inject(at=TAIL, method="repositionElements")` 在窗口尺寸变化时重定位；坐标来自 `@Shadow @Final HeaderAndFooterLayout layout`（`layout.getWidth()/2+158`、`layout.getY()+layout.getFooterHeight()-4`，54-56）；是否显示由 `MidnightLibConfig.shouldShowButton()` 决定。

## 7. 与 ModMenu 集成（两条路径）

- Fabric：`fabric.mod.json` 的 `modmenu` entrypoint 指向 `MidnightLib.ModMenuInit implements ModMenuApi`。除了返回自身配置页，还实现 `getProvidedConfigScreenFactories()` 遍历 `MidnightConfig.configInstances`，**替所有使用本库的 mod 向 ModMenu 注册配置页**，并跳过 `MidnightLib.hiddenMods`（`MidnightLib.java:78-95`）。
- NeoForge/Forge：在 `FMLClientSetupEvent` 里 `ModList.get().forEachModContainer(...)`，凡是已 `init` 过的 modid 就注册 `IConfigScreenFactory` / `ConfigScreenHandler.ConfigScreenFactory`（`MidnightLib.java:109-119`、141-152）。
- 自身展示策略用 `MidnightLibConfig` 的 `ConfigButton{TRUE,FALSE,MODMENU}` 与 `HAS_MODMENU`（`PlatformFunctions.isModLoaded("modmenu")` 或平台为 neoforge）决定是否显示选项屏按钮（`core/config/MidnightLibConfig.java`）。

## 8. 值得学的 5+ 条做法

1. **反射 + 注解 + Gson `ExclusionStrategy`** 三件套实现"零依赖、零样板"配置：只序列化 `@Entry` 字段，未标注解的公开字段自动忽略（`lib/config/MidnightConfig.java:48-63, 94-105`）——适合自定义配置系统或需要"配置类即界面"的场景。
2. **跨线程静态字段回写走渲染线程**：`Minecraft.getInstance().submit(info::updateConditions)` 规避 `IllegalAccessException`（同文件 229-233）——任何"主线程之外改静态状态"的库都该抄。
3. **用平台扩展点批量接管依赖方的配置界面**：`getProvidedConfigScreenFactories()` / `IConfigScreenFactory` 循环注册（`MidnightLib.java:86-93, 112-116`）——前置库让下游 mod "零代码获得配置页"的通用手法。
4. **屏幕关闭时清空静态缓存字段**（value/tempValue/tab/actionButton 全置 null，`MidnightConfigScreen.java:118-128`）——避免静态 `entries` 永久持有 widget/screen 造成内存泄漏。
5. **校验逻辑即输入过滤器 + 联动按钮可用性**：`b.active = entries.values().allMatch(e -> e.inLimits)`，一个表达式让"任一输入非法则 Done 不可点"（`MidnightConfig.java:177`）。
6. **列表字段用"索引游标 + 循环按钮"编辑**：`listIndex`、`writeList(index,value)`、越界时 add（`MidnightConfigScreen.java:230-238`、`EntryInfo.java:92-98`）——比嵌套界面便宜得多。
7. **Stonecutter 注释替换而非多份代码**：整仓 16 个文件同时支持 1.20.1→26.2，靠 `//? if >= 1.21 {` 与 `replace("GuiGraphics","GuiGraphicsExtractor")` 等规则（`stonecutter.gradle.kts:8-45`）。
8. **`src/test` 当活文档**：`MidnightConfigExample.java`（177 行）覆盖每个注解/类型/条件组合，`MidnightLibExtras.KeybindButton` 演示 `onTabInit` 扩展点插入自定义 KeyMapping 行（`src/test/java/eu/midnightdust/test/`）。

## 9. （库/前置类）公开 API 与接入方式

- API 包：`eu.midnightdust.lib.config`（对外）、`eu.midnightdust.lib.util`；内部实现放 `eu.midnightdust.core.*`。
- 接入三步：1) 依赖 `eu.midnightdust:midnightlib:<ver>-<loader>`；2) 配置类 `extends MidnightConfig`，字段用 `public static` + `@Entry/@Comment`；3) 入口调 `MidnightConfig.init("yourmodid", YourConfig.class)`（客户端入口即可，见 `src/test/java/eu/midnightdust/test/MidnightLibTest.java:10-12`）。
- 扩展点：覆写 `getJsonFilePath()`、`writeChanges()`、`getScreen(Screen)`、`onTabInit(tabName, list, screen)`；静态工具 `MidnightConfig.write(modid)`、`getDefaultValue(modid, entry)`、`getScreen(parent, modid)`；屏蔽自身配置页用 `MidnightLib.hiddenMods.add(modid)`。
- 翻译键约定：`<modid>.midnightconfig.title`、`...category.<tab>`、`<modid>.midnightconfig.<field>`、`...<field>.tooltip`、枚举 `%s.midnightconfig.enum.<Enum>.<VALUE>`（`MidnightConfig.java:200-208`）。
