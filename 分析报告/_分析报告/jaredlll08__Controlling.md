# jaredlll08/Controlling 源码分析报告

> 分析基于仓库快照 `_bulk/jaredlll08__Controlling`，commit `91ae721`（2026-06-17，"Fix fabric not working. Close #235"）。
> 注意：工作树快照缺 `fabric.mod.json`、`META-INF/services/*`、`assets/controlling/lang/*.json`，这些文件在 git 中存在（用 `git show HEAD:<path>` 读取），下文相关内容以 git 版本为准。

## 1. 基本信息

- Mod 名 / id：Controlling / `controlling`；作者 Jaredlll08；许可证 MIT（`neoforge.mods.toml`、`fabric.mod.json`）
- 目标环境：`gradle.properties` — `minecraft=26.2`、`java_version=25`、`neoforge=26.2.0.1-beta`、`fabric_loader=0.19.3`、`fabric=0.152.1+26.2`；**纯客户端 mod**（`@Mod(dist = Dist.CLIENT)`、fabric `"environment": "client"`）
- Gradle：NeoForge **ModDevGradle 2.0.141** + **Fabric Loom 1.16.3**（`net.fabricmc.fabric-loom`），发布用 `com.modrinth.minotaur` / `net.darkhax.curseforgegradle`；自定义 composite build `build-logic/`（`settings.gradle:includeBuild`）
- 编译依赖（关键）：common 侧 `com.blamejared.searchables:Searchables-common-<mc>`，各加载器侧 `Searchables-{fabric,neoforge}-<mc>:1.0.1`；**Searchables 是硬前置**（两个 mods.toml / fabric.mod.json 都声明 required）。mixin 0.8.5 + mixinextras-common 0.3.5
- 所以它的"API"有两层：作者自己的 Searchables（搜索框/补全/高亮）与自己暴露的 `api/` 包

## 2. 源码规模与包结构

实测 `find . -name '*.java' | wc -l` = **54**，总 **2658 行**（含 build-logic 4 个文件）。模块划分：

| 模块 | 文件数 | 说明 |
|---|---|---|
| `common/src/.../controlling` | 28 | `api/`(2) `api/entries`(3) `api/events`(8) `client`(5) `mixin`(5) `platform`(3) |
| `fabric/src/.../controlling` | 13 | `api/event`(10) `platform`(2) `mixin`(1) |
| `neoforge/src/.../controlling` | 9 | `api/events`(4) `platform`(2) `mixin`(1) `events`(1) + 主类 |
| `build-logic` | 4 | RootPlugin / LoaderPlugin / CommonPlugin / Util |

最大文件：`NewKeyBindsScreen.java`(353)、`NewKeyBindsList.java`(301)、`CommonPlugin.java`(183)、`FreeKeysList.java`(165)、`NeoForgePlatformHelper.java`(104)。

## 3. 入口与注册

**没有内容注册**（无 DeferredRegister / Registrate，零物品方块实体）。

- NeoForge：`neoforge/src/main/java/com/blamejared/controlling/Controlling.java:13` — `@Mod("controlling", dist = CLIENT)` 构造器仅 `modEventBus.addListener(this::init)`，`init` 里 `NeoForge.EVENT_BUS.register(new ClientEventHandler())`
- Fabric：`fabric.mod.json`（git 版）`"entrypoints": {}` **为空** —— Fabric 端完全靠 mixin + ServiceLoader 启动，无入口类
- 平台服务：`common/.../platform/Services.java:9-19` 用 `ServiceLoader.load(...).findFirst()` 加载 `IEventHelper` / `IPlatformHelper`；实现类由**手写的** `fabric|neoforge/src/main/resources/META-INF/services/com.blamejared.controlling.platform.{IPlatformHelper,IEventHelper}` 指定（build-logic 引入了 auto-service 依赖，但源码里未见 `@AutoService` 注解，属未使用/历史残留）；common 只 `compileOnly project(':common')` 时按 loader 属性区分

## 4. 核心系统

**(1) 屏幕接管（两种加载器两套做法）** — Fabric 用 `fabric/.../mixin/OpenGuiMixin.java:20` 的 `@ModifyVariable(method = "setScreen", at = @At("HEAD"), argsOnly = true)` 在 `Gui.setScreen` 入参处把 `KeyBindsScreen` 换成 `NewKeyBindsScreen`；NeoForge 用 `neoforge/.../events/ClientEventHandler.java:14` 监听 `ScreenEvent.Opening` 调 `event.setNewScreen(...)`，上一屏通过 `AccessOptionsSubScreen.controlling$getLastScreen()` 取。两处都做了 `instanceof NewKeyBindsScreen` 防重入。

**(2) 子类化而非注入原版界面** — `common/.../client/NewKeyBindsScreen.java:36` `extends KeyBindsScreen`，只覆写 `addTitle/addContents/addFooter/repositionElements/init/mouseClicked/keyPressed/extractRenderState`，并用原版 `layout.setHeaderHeight(48)/setFooterHeight(56)` + `LinearLayout`/`GridLayout`(`:72-131`) 重建头尾。私有字段访问靠 Accessor 接口 + 强制转型：`getAccess()`(`:273`) 返回 `(AccessKeyBindsScreen) this`。

**(3) 双列表 + 全量/显示分离** — `common/.../client/CustomList.java:11` `extends KeyBindsList`，新增 `allEntries` 保存全量行；覆写 `addEntry` 时同时进 `allEntries` 和真实列表，另开 `addEntryInternal`(`:46`) 供过滤时只进真实列表，避免过滤把全量数据冲掉。`NewKeyBindsList`（`KeyEntry implements IKeyEntry`，自带"改键/重置"按钮与冲突黄条 `:193-197`）与 `FreeKeysList`（借 `AccessInputConstantsKey.controlling$getNAME_MAP()` 反查所有未绑定按键）都继承它。

**(4) 搜索/过滤/排序** — 声明式 `ControllingConstants.java:27` 构造 `SearchableType<KeyBindsList.Entry>`，组件 `category` / `key` / `name`（用 `instanceof IKeyEntry` 等接口取字段）；输入框是 Searchables 的 `AutoCompletingEditBox`（`NewKeyBindsScreen.java:69`）。过滤统一走 `filterKeys(String)`(`:163`)：`clearEntries` → `SEARCHABLE_KEYBINDINGS.filterEntries(allEntries, term, extraPredicate)` → `addEntryInternal` → `postConsumer` 排序。`DisplayMode`（ALL/NONE/CONFLICTING，各带 `Predicate<IKeyEntry>`）与 `SortOrder`（5 档，`implements Comparator<KeyBindsList.Entry>`）都是自解释枚举，`cycle()` 轮换。

**(5) 跨加载器事件桥** — `common/.../platform/IEventHelper.java:19-25` 四个方法统一返回 `Either<I*Event, 默认值>`：NeoForge 实现投 `Either.left(EVENT_BUS.post(ev))`(可取消事件)，Fabric 实现投 `Either.right(回调返回值)`；调用点 `.map(I...Event::handled, UnaryOperator.identity())` 一行兼容两种语义（`NewKeyBindsList.java:202-230`）。common 因此**零引用**任一加载器类。

## 5. 网络 / 数据驱动 / 配置 / datagen

全部**无**。无网络包、无配置屏幕、无 datagen、无数据驱动内容（纯客户端 UI，状态即 `Options.keyMappings`）。资源仅 24 个语言文件 + `pack.mcmeta` + `icon.png`。

## 6. Mixin

三个配置：`common/src/main/resources/controlling.mixins.json`（5 个）、`controlling.fabric.mixins.json`（1 个）、`controlling.neoforge.mixins.json`（1 个），全部只在 `client` 段，`defaultRequire: 1`。

**只有两类 mixin，没有任何 `@Inject` / `@Redirect` / `@Overwrite`**：

- Accessor 接口（6 个）：`AccessKeyBindsScreen`(@Accessor `keyBindsList`/`resetButton`)、`AccessKeyBindsScreenNeoForge`(`lastPressedModifier`/`isLastKeyHeldDown`/`isLastModifierHeldDown`/`lastPressedKey`，仅 26.x 改键需要)、`AccessAbstractSelectionList`(`children`)、`AccessKeyMapping`(`key`)、`AccessInputConstantsKey`(静态 `NAME_MAP`)、`AccessOptionsSubScreen`(`lastScreen`)；命名统一加 `controlling$` 前缀防冲突
- 唯一的行为注入：`OpenGuiMixin` 的 `@ModifyVariable(setScreen, HEAD, argsOnly)`
- `controlling.accesswidener`（仅一行 header）与 `META-INF/accesstransformer.cfg`（空）都是**空占位**——因为代码走 Accessor mixin，不需要 AW/AT；保留文件让 Loom/ModDevGradle 的条件分支继续生效

## 7. 值得学的 5 条

1. **UI 增强用"子类化 + Accessor mixin"而不是注入原版界面方法**：`NewKeyBindsScreen.java:36` + `AccessKeyBindsScreen.java:11`（10 行拿到私有字段）。适用：想大改某个原版 Screen 布局但不想碰 30 个注入点。
2. **在"屏幕打开"这一时刻换实例，两种加载器各一个 hook**：`OpenGuiMixin.java:20` 的 `@ModifyVariable(argsOnly)` 与 `ClientEventHandler.java:14` 的 `ScreenEvent.Opening`。适用：让原版入口跳转到自己的界面，且不影响其他 mod 直接 new 原版界面的场景。
3. **平台 SPI 用 `ServiceLoader` + 接口 default 方法兜底**：`Services.java:12`、`IPlatformHelper.java:39`（default 实现就能跑，loader 只覆写差异部分）。适用：多加载器共享代码里隔离 loader 特有行为。
4. **用 `Either<事件对象, 默认值>` 抹平"可取消事件 vs 回调"两种事件模型**：`IEventHelper.java:19`。适用：common 层想抛事件又不想依赖 loader 事件类。
5. **把通用能力抽成独立库再硬依赖**：搜索/补全全在 `com.blamejared.searchables`，本仓只用 `SearchableType.Builder`（`ControllingConstants.java:27`）声明字段。适用：同一作者多 mod 共用 UI 组件时，比复制代码更省维护成本。

（附：构建侧值得借鉴的做法是 `build-logic/LoaderPlugin.java:46-72` —— 用自定义 `commonJava`/`commonResources` configuration 把 common 的源码与资源直接塞进各 loader 的 `compileJava`/`processResources`/`sourcesJar`，配合 Gradle `Attribute("io.github.mcgradleconventions.loader")` 做变体区分，避免 jar-in-jar；`CommonPlugin.java:95-129` 再把 `gradle.properties` 里的版本/作者/依赖版本号统一 expand 进 `fabric.mod.json`、`*.mixins.json`、`neoforge.mods.toml` 模板。）
