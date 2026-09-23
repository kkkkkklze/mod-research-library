# blackd / libIPN 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | libIPN / `libipn`（`libIPN/neoforge-1.21/src/main/resources/META-INF/neoforge.mods.toml`） |
| 作者 | blackd(mirinimi)；credits: Selah (AspieGamer13), ThirtyTwelveNor |
| 版本 | 6.5.0（`build.gradle.kts:33` `Version("6","5","0", preRelease = IPNEXT_RELEASE==null)`，非发布构建自动加 `-SNAPSHOT`） |
| 许可证 | AGPL-3（`gradle.properties` `mod.license=AGPL-3`） |
| 目标 MC / 加载器 | 10 个模块：`fabric/forge/neoforge × 1.21 / 1.21.4 / 1.21.5` + `fabric-1.21.6`（`settings.gradle.kts:29-38`）。磁盘上还有 `1.21.3` 三模块但**未 include**。`neoforge-1.21` 构建对 MC **1.21.1**（`neoforge 21.1.85`、`kotlinforforge 5.4.0`），mods.toml `versionRange="[1.21.1, 1.21.2)"`、`side="CLIENT"`、`modLoader="kotlinforforge"` |
| Gradle 插件 | 自研 `buildSrc`（`CommonConfig/CompilationConfig/DependencyConfig/DistributionConfig/FilteringSourceSet/ModInfoGeneratorTask/VersionProperties`）；外部：`fabric-loom 1.10-SNAPSHOT`、`net.neoforged.gradle.userdev 7+`、`io.github.goooler.shadow 8+`、`kotlin 2.0.21 + plugin.serialization`、JVM target 21 |
| 发布链 | `com.matthewprenger.cursegradle` + `com.modrinth.minotaur` 自动发布；ProGuard（`proguard.txt` + 自研 `minimizeJar` task）压缩；产物发到 `maven.ipn-mod.org` |
| 依赖 | shadedApi：`com.yevdo:jwildcard`、`ca.solo-studios:kt-fuzzy-jvm`；运行时要求 `fabric-api`+`fabric-language-kotlin`（Fabric）或 `kotlin-for-forge`（Forge/NeoForge）。**注意 README 首行声明：项目已迁移到 Codeberg，本仓库已归档** |

## 2. 源码规模与包结构

实测：`.java` **36** 个 / **3641** 行；`.kt` **1159** 个 / **91612** 行（合计约 9.5 万行）。

- 1159 个 Kotlin 文件中 **807 个在 `org/anti_ad/mc/alias/**`**（每平台×每版本各一份 typealias），真正的业务代码只有 352 个 kt。
- 目录结构：每平台模块 = `src/main/java/org/anti_ad/mc/{common/{forge,gui,mixin,vanilla},libipn}` + `src/main/kotlin/org/anti_ad/mc/alias/**`；共享代码在 `libIPN/shared/{java,kotlin}/...`（81 个 kt），由各模块 build 脚本 `sourceSets.main.java.srcDirs("./src/shared/java")` 引入（注意本地 checkout 中该目录位于 `libIPN/shared` 而非各模块下的 `src/shared`，疑似符号链接未展开，**未确认**）。

主要包（`libIPN/shared`，第三层）：

| 包 | 文件数 | 内容 |
|---|---|---|
| `common/gui/widgets` | 15 | 自研 Widget 框架（Widget/RootWidget/Page/Scrollable/Config*） |
| `common/extensions` | 8 | Kotlin 扩展（PropertyDelegates、kt_collection、json、string） |
| `common/gui/screen` | 6 | ConfigScreenBase、BaseDialog、ColorPicker、HotkeyDialog |
| `common/input` | 5 | GlobalInputHandler、GlobalScreenEventListener、Keybinds |
| `common/config{,/builder,/options}` | 8 | 配置 DSL 与序列化 |
| `common/vanilla/{render,glue}` | 12 | 跨版本渲染 glue（Screen/Text/Texture/Rect/Color） |
| `common/moreinfo` | 3 | InfoManager、SemVer |

最大文件：`alias/block/BlockAlias.kt` **857** 行（9 个平台/版本模块各一份）、`shared/.../input/KeyCodes.kt` **664** 行。

## 3. 入口与注册

无任何原版注册表注册（纯客户端库）。NeoForge 入口（`libIPN/neoforge-1.21/src/main/java/org/anti_ad/mc/libipn/LibIPNModEntry.kt:36`）：

```kotlin
@Mod(ModInfo.MOD_ID)
object LibIPNModEntry {
    private val toInit: Runnable =
        if (FMLEnvironment.dist === Dist.CLIENT) LibIPNClientInit() else LibIPNServerInit()
    init {
        runForDist(
            clientTarget = { MOD_BUS.addListener(::onClientSetup) },
            serverTarget = { MOD_BUS.addListener(::onServerSetup); "test" })
    }
    private fun onClientSetup(event: FMLClientSetupEvent) { toInit.run() }
}
```

- `ModInfo` 由 `buildSrc` 的 `ModInfoGeneratorTask`（`ModInfoGeneratorTask.kt:78-102`）在编译期生成 `object ModInfo { MOD_ID/MOD_NAME/MOD_VERSION/MOD_LOADER/CURSEFORGE_URL/MODRINTH_URL }` 到 `build/generated`，业务代码零硬编码字符串。
- `LibIPNClientInit.kt:37`：注册 `CommonForgeEventHandler`、`NeoForgeTicksSource` 到 `NeoForge.EVENT_BUS`，并用 `ModLoadingContext.registerExtensionPoint(IConfigScreenFactory::class.java)` 把 `ConfigScreenBase(ConfigScreenSettings)` 挂成 mod 列表里的配置按钮。
- 公共初始化 `org.anti_ad.mc.common.init()`（`shared/java/org/anti_ad/mc/common/LibIPN.kt:33`）= `ConfigScreenSettings.initMainConfig()` + `OnetimeDelayedInit.init()`。
- Fabric 侧入口在 `fabric-1.21/src/main/java/org/anti_ad/mc/libipn/`（本检查未逐一读取）。

## 4. 核心系统

**(1) 跨版本 alias 层（本库最大特色）**。`org/anti_ad/mc/alias/**` 为每个用到的 MC 类写一个 `typealias`，如 `MinecraftAlias.kt:24 typealias SharedConstants = SharedConstants`、`screen/ScreenAlias.kt:22-50` 把全部 `world.inventory.*Menu` 归类别名。业务代码只 `import org.anti_ad.mc.alias.*`，1.21 → 1.21.6 的包名/类名差异全部收敛在这 807 个文件里（每模块自持一份，同名不同内容）。

**(2) 配置系统（Kotlin DSL + kotlinx.serialization）**。`ConfigDeclaration` + `createBuilder().CATEGORY("...")` 链式声明，字段用委托 `by bool(false)` / `by int(v,min,max)` / `by hotkey("")` / `by color(...)` / `by enum(...)`（`ConfigDeclarationBuilder.kt:41-94`）。`ConfigOptionNumericBase` 在 setter 里做 `coerceIn(min,max)`（`IConfigElements.kt:31-40`），另有 `Importance`、`hidden`、`isModified/resetToDefault`、`enumForMinMCVersion(min,cur,dv)` 之类"按 MC 版本决定是否真注册该字段"的写法（不满足则 `fakeAddTo`，保证老版本配置文件兼容）。落盘：`ConfigSaveLoadManager(modId, fileName) { configs.toMultiConfig() }`（`ConfigSaveLoadManager.kt:38-74`），路径 `VanillaUtil.configDirectory(modId)/fileName`，`Json { prettyPrint=true; prettyPrintIndent="    " }`。

**(3) 自研 GUI 框架**。`Widget`（`widgets/Widget.kt:46`）是响应式基类：`location`/`size` 用 `by detectable(...)` 委托（`extensions/PropertyDelegates.kt`）在变更时触发 `locationChanged/sizeChanged/screenLocationChanged` 事件；支持 `anchor = AnchorStyles.*`、`overflow`、`zIndex`、`visible` 依据父容器裁剪自动计算。`RootWidget`（`widgets/RootWidget.kt:56`）用 `RoutedEvent<T>` 把 `MouseEvent/KeyEvent/CharTypedEvent` 按 z 序路由分发。配套 `Page`、`ScrollableContainerWidget`、`ConfigListWidget`、`layout/Flex.kt`、`glue/VanillaWidgetsGlue.kt`。`ConfigScreenBase` 直接由配置声明生成整个设置界面（含 `dumpWidgetTree()` 调试）。

**(4) 渲染/屏幕抽象**。`common/gui/NativeContextBase.kt` + 各平台 `NativeContext.kt` 提供与版本无关的画布 API；`common/vanilla/render/glue/{Screen,Text,Texture,Rect}.kt` 是接口，平台侧 `render/{GL,Screen,Text,Texture}.kt` 实现；`IVanillaScreenUtil` 统一屏幕工具。

**(5) Tick/事件总线与输入**。`TicksDispatcher`（`shared/kotlin/.../events/TicksDispatcher.kt:7`，`ReentrantReadWriteLock` 保护 pre/post 两个 `MutableList<()->Unit>`，分发前 `toList()` 快照）+ 平台 tick 源：NeoForge 用 `NeoForgeTicksSource`（事件），Fabric 用 `MixinMinecraftClient`。`OnetimeDelayedInit`（同目录）让下游注册 `register(priority, action)`，在首个 tick 时排序后执行一次并自摘钩子——用于"MC 完全初始化后才能做"的延迟初始化。输入侧 `GlobalInputHandler` + `GlobalScreenEventListener` 配合 `MixinKeyboard` 的 `onKey` HEAD 取消注入。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无（mods.toml `side="CLIENT"`，未发现任何包注册/收发代码）。
- **数据驱动**：无资源包 JSON 数据；每个平台模块的 `resources` 只有 `ipn.accesswidener`（Fabric）/ `META-INF/accesstransformer.cfg`（Forge/NeoForge）与 `META-INF/*.toml`。
- **配置**：见第 4 节 (2)，JSON 格式，文件 `libipn-demo-config.json`（`ConfigScreenSettings.kt:36,47`）。
- **datagen**：无。
- **访问扩宽**：Fabric `ipn.accesswidener` 开放 `SoundEvent.of`、`MerchantScreen` 的 `offers/indexStartOffset/selectedIndex/syncRecipeIndex`、`NbtString.value`、`AnvilScreen.nameField`、`RecipeBookWidget.searchField`、`ItemStack` 构造等；Forge/NeoForge 用 `accesstransformer.cfg` 表达同一批（带 SRG 注释如 `# f_99118_`）。

## 6. Mixin

只有 **Fabric 侧有 mixin（3 个，且仓库内无 `*.mixins.json`**；loom 侧只配了 `mixin.defaultRefmapName.set("libIPN-refmap.json")`，json 配置文件本检查中未找到，**未确认**是否由构建生成）：

| 类 | 目标 | 注入点 |
|---|---|---|
| `fabric-1.21/.../common/mixin/MixinMinecraftClient.java:32` | `MinecraftClient` | `tick()V` 的 `HEAD`/`RETURN` → `TicksDispatcher.INSTANCE.dispatchPre()/dispatchPost()` |
| `fabric-1.21/.../common/mixin/MixinKeyboard.java:39` | `Keyboard`（`priority = 0`） | `onKey` 的 `HEAD`、`cancellable = true`；带 `@Unique pressedCount/releasedCount`，先校验 `mc().isOnThread() && handle == window().getHandle()` |
| `fabric-1.21/.../common/mixin/MixinMouse.java` | 鼠标 | 未读取 |

NeoForge/Forge 侧 **0 个 mixin**——tick 钩子改走 `NeoForgeTicksSource` 事件，屏幕字段访问改走 AT，体现了"平台原生能力优先、mixin 只做 Fabric 补齐"的策略。

## 7. 值得学的 5 条具体做法

1. **用 typealias 层收敛跨版本差异**：写 807 个 `typealias` 而不是到处 `//? if` 注释或预处理器，业务代码只 import `org.anti_ad.mc.alias.*`（`alias/screen/ScreenAlias.kt:22`）。适用：一个 mod 同时支持 5 个 MC 小版本、又不愿上 Stonecutter/预处理器的场景。
2. **`object + 委托` 让配置声明即界面**：`val FOO by bool(true)`、`val BAR by hotkey("")`，配置项、默认值、UI 控件、序列化一次声明（`config/builder/ConfigDeclarationBuilder.kt:41-94` + `ConfigScreenBase`）。适用：任何需要设置屏的 mod。
3. **`OnetimeDelayedInit` 化解"过早初始化"**：把需要 MC 起来后的动作 `register(priority){}` 排队到首个 tick 执行，按优先级排序后自摘钩子（`events/OnetimeDelayedInit.kt:31-43`）。适用：库模组需要在客户端 ready 后做一次性注册/迁移。
4. **构建期生成 `ModInfo`**：`ModInfoGeneratorTask` 从 Gradle 输出 `object ModInfo { const val MOD_ID/MOD_VERSION/... }`，代码里引用常量而非字符串，版本号编译期内联（`buildSrc/.../ModInfoGeneratorTask.kt:78-102`）。适用：所有 mod，规避 mods.toml 与代码版本不同步。
5. **`FilteringSourceSet` 与 `minimizeJar`**：前者通过过滤 classpath 中含指定字符串的 jar 来隔离同名多版本依赖，后者用 ProGuard 对产物做 `-optimizationpasses 100` 压缩（`proguard.txt`、`buildSrc/.../DistributionConfig.kt`）。适用：多平台/多版本矩阵构建、想减小 jar 体积。

## 8. 公开 API / 外部 mod 接入方式

对外以 Maven 制品发布（`maven.ipn-mod.org` releases/snapshots，artifact `libIPN-<platform>-<mcversion>`，另有 `sources`、`dev` classifier，见各模块 `publishing` 块），README 建议以 `compileOnly` 依赖接入。可复用的扩展点集中在：

- 配置 DSL：`org.anti_ad.mc.common.config.builder.ConfigDeclaration` + `createBuilder()` + `by bool/int/string/enum/hotkey/color/keyToggleBool`（下游可声明自己的配置组并复用同一设置屏）。
- GUI：`common/gui/widgets/{Widget,RootWidget,Page,...}`、`common/gui/screen/{ConfigScreenBase,BaseDialog}`、`gui/layout/Flex.kt`。
- 输入/事件：`common/Interfaces.kt` 的 `ScreenEventListener`（可覆写 `mouseClicked/Release/Dragged/Scrolled`、`keyPressed` 等）、`IInputHandler`、`Savable`；`TicksDispatcher`/`OnetimeDelayedInit`。
- 信息/工具：`common/moreinfo/InfoManager`、`SemVer.kt`、`common/util/LogicalStringComparator.kt`、`algoritms/WeightedRandomizingList.kt`、`extensions/*`（Kotlin 扩展）。
- 本库**没有**独立的 `api` 包或 `@ApiStatus` 白名单，公开面即上述 `org.anti_ad.mc.common.*` 包（README 中提到的 `@IPNIgnore`/`@IPNGuiHint` 属旧版 Inventory-Profiles 文档，本仓库未逐一确认对应注解类是否仍存在）。
