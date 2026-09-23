# VazkiiMods/Patchouli 源码分析报告

> 分析对象：`_参考仓库/_bulk/VazkiiMods__Patchouli`（分支 `26.1`，HEAD `4f94b07`，2026-07-10）。
> 注意：本仓库是 sparse-checkout（只检出 `*.java/*.gradle/*.properties/*.toml/*.mixins.json/*.md`），资源与数据文件仍在 git 中但未落盘（可用 `git show HEAD:<path>` 查看）。

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Patchouli / `patchouli` |
| 作者 | Vazkii, williewillus |
| 目标版本 | `mc_version=26.1`（`gradle.properties`），`java_version=25`；`neoforge_version=26.1.0.1-beta`（moddev 2.0.141），`fabric_loader=0.18.4`、`fabric_api=0.144.0`、loom 1.15-SNAPSHOT |
| 许可证 | CC BY-NC-SA 3.0（`NeoForge/src/main/resources/META-INF/neoforge.mods.toml`、`fabric.mod.json`） |
| Gradle 结构 | 3 子模块：`Xplat`（公共代码，用 neoForm 反重映射编译，`Xplat/build.gradle`）、`Fabric`（loom）、`NeoForge`（moddev）；Fabric/NeoForge 通过 `source xplat.sourceSets.main.allSource` 复用 Xplat 源（`build.gradle`） |
| 编译依赖 | `compileOnly mezz.jei:jei-26.1-common-api:29.2.0.17`（JEI 为唯一硬 API 依赖，`build.gradle`）；Fabric 侧 `implementation+include me.zeroeightsix:fiber:0.23.0-2`（配置文件库）；REI / Cloth Config 依赖已注释 |
| 公开 API 产物 | `NeoForge/build.gradle` 的 `apiJar` 任务只打包 `vazkii/patchouli/api/**`（`archiveClassifier='api'`） |

**版本提示（对 1.21.1/1.20.1 目标读者）**：本快照已使用 MC 26.1 的 API——`ResourceLocation` 全面改名为 `net.minecraft.resources.Identifier`、创意栏条目用 `ItemStackTemplate`、渲染用 `GuiGraphicsExtractor`。对照 Forge 1.20.1 / NeoForge 1.21.1 分支时，类名与网络注册 API 需自行回退，但整体架构（下文）未变。

## 2. 源码规模与包结构

实测：**190 个 `.java`，15057 行**（`find . -name '*.java' -exec wc -l {} +`）。分布：`Xplat` 164 文件 / 13780 行；`Fabric` 16 / 685；`NeoForge` 10 / 592。核心逻辑几乎全在 Xplat。

```
api            15 文件  1008 行   ← 唯一对外承诺的稳定包
client/book    15       1591      ← BookContents/Entry/Category 模型
client/book/page    17  1108      ← 17 种内置页（text/crafting/multiblock/quest…）
client/book/gui     10  1839      ← GuiBook/GuiBookEntry/GuiBookLanding
client/book/template 5+9+7  658+  ← 模板、组件、变量系统
client/base     7        435      ← PersistentData/ClientAdvancements/ClientRecipes
client/handler  4        584      ← 崩溃报告/右键/多方块可视化/工具提示
client/multiblock 5      330
common/book     3        431      ← Book/BookRegistry/BookFolderLoader
common/base     3        420      ← PatchouliConfig/PatchouliAPIImpl/Sounds
common/multiblock 8      884      ← DenseMultiblock/SparseMultiblock/StateMatcher
common/util     4        371      ← ItemStackUtil/SerializationUtil/RotationUtil
network         2        50
xplat           3        136      ← IXplatAbstractions 等
mixin/client   7(Xplat)+4(Fabric)
```

最大文件：`client/book/gui/GuiBook.java` 587、`client/book/text/BookTextParser.java` 401、`client/book/gui/GuiBookEntry.java` 342、`client/handler/MultiblockVisualizationHandler.java` 324、`client/book/BookEntry.java` 322、`common/base/PatchouliAPIImpl.java` 302、`api/PatchouliAPI.java` 301、`client/book/page/PageMultiblock.java` 290、`common/book/Book.java` 285。

## 3. 入口与注册

- **NeoForge 主类** `NeoForge/src/main/java/vazkii/patchouli/neoforge/common/NeoForgeModInitializer.java:35-80`（`@EventBusSubscriber` + `@Mod`）；客户端 `neoforge/client/NeoForgeClientInitializer.java:32-92`（`@Mod(dist=CLIENT)`，注册 reload listener、GUI 层、PiP 渲染器、物品模型属性）。
- **Fabric** `fabric/common/FabricModInitializer.java:30-66`、`fabric/client/FabricClientInitializer.java`；`fabric.mod.json` entrypoints = `main/client/fabric-gametest`。

注册内容（以 NeoForge 为例，全部走事件回调）：

```java
NeoForgePatchouliConfig.setup(container);          // 配置
modBus.addListener(NeoForgeNetworkHandler::setupPackets);
NeoForgeXplatImpl.ITEMS.register(modBus);           // DeferredRegister.Items
PatchouliItems.init();
modBus.addListener((RegisterEvent evt) -> {         // 声音 / 数据组件 / 触发器
    evt.register(Registries.SOUND_EVENT, rh -> PatchouliSounds.submitRegistrations(rh::register));
    evt.register(Registries.DATA_COMPONENT_TYPE, rh -> PatchouliDataComponents.submitDataComponentRegistrations(rh::register));
    evt.register(Registries.TRIGGER_TYPE, rh -> PatchouliCriteriaTriggers.submitTriggerRegistrations(rh::register));
});
modBus.addListener((FMLCommonSetupEvent evt) -> BookRegistry.INSTANCE.init());
```

**注册框架是"自研抽象 + 手工注册"而非 DeferredRegister 全家桶**：只有一个 `DeferredRegister.Items ITEMS`（`neoforge/xplat/NeoForgeXplatImpl.java:39`），通过 `IXplatAbstractions.registerItem(name, factory, propsOp)`（`xplat/IXplatAbstractions.java:68`）暴露给公共代码，`PatchouliItems.BOOK` 因此能在 Xplat 里静态初始化（`common/item/PatchouliItems.java:9`）。其他注册项用 `submitXxxRegistrations(BiConsumer<Identifier, T>)` 的函数式提交，让同一份公共代码既能走 NeoForge `RegisterEvent`、也能走 Fabric 的 `Registry.register`（`FabricModInitializer.java:33-36`）。**跨平台抽象用 `ServiceLoader`**：`IXplatAbstractions.INSTANCE = find()` 要求 classpath 上恰好一个实现（`IXplatAbstractions.java:50-62`），实现类名写在 `META-INF/services/vazkii.patchouli.xplat.IXplatAbstractions`。

## 4. 核心系统

### 4.1 BookRegistry + Book：书籍元数据注册表

`common/book/BookRegistry.java:28`（`BOOKS_LOCATION = "patchouli_books"`）。`init()`（:37-71）遍历 `IXplatAbstractions.getAllMods()` 的每个 mod，用 `mod.visit("data/<ns>/patchouli_books")` 找 `book.json`，由路径反推 `bookId`，再调 `loadBook(...)`。同一份 JSON 构造的 `Book` 对象（`common/book/Book.java:122-195`）把 book.json 的每个键读成 final 字段（`text_color`/`book_texture`/`i18n`/`pamphlet`/`dont_generate_book`，以及 `macros` 宏表），并把物品栈用 `Suppliers.memoize` 延迟解析，避免加载顺序问题（:178-189）。外部书籍（`.minecraft/patchouli_books/<name>/`）由 `BookFolderLoader.findBooks()`（`common/book/BookFolderLoader.java:26-55`）加载，标记 `isExternal=true` 走另一套 loader。

另外两个设计点：book.json 中若缺 `use_resource_pack` 或出现已废弃的 `extend`，直接抛 `IllegalArgumentException` 并附带迁移指引（`Book.java:156-172`）——用异常做版本迁移提示；`reloadContents()` 失败时降级为 `BookContents.empty(book, e)` 而不是崩溃（:217-224）。

### 4.2 BookContentLoader：三种内容来源的统一接口

`client/book/BookContentLoader.java:21-33`：只两个方法 `findFiles(book, dir, out)` / `loadJson(book, file)`，返回 `LoadResult(JsonElement json, @Nullable String addedBy)`（`addedBy` 用于在书里显示"由某资源包补充"）。三个实现：
- `BookContentResourceListenerLoader`（:27-109）：继承 `SimpleJsonResourceReloadListener<JsonElement>`，注册为 `patchouli:resource_pack_books` 客户端 reload listener，在**资源重载时**就把 `patchouli_books/<book>/<lang>/<folder>/<id>.json` 全部预读进内存（用正则 `ID_READER` 拆分路径，:31-35），避免每次打开书都做 I/O。
- `BookContentResourceDirectLoader`：需要时直查 ResourceManager，负责用 `sourcePackId` 计算 `addedBy`。
- `BookContentExternalLoader`：从磁盘目录递归爬取。

### 4.3 BookContentsBuilder：两阶段（load → build）内容装配

`client/book/BookContentsBuilder.java`。**阶段一** `loadFiles()`（:79-86）依次加载 `categories`/`entries`/`templates` 三类文件，文件名即 id；`load()`（:123-136）把逻辑 id 还原成 `patchouli_books/<book>/en_us/<type>/<id>.json` 再交给 loader，并支持"本地化优先"：先找 `currentLang` 版本，找不到回落 `en_us`（:186-199）。**阶段二** `build(level)`（:88-121）才做交叉引用解析（`entry.initCategory` 会把 entry 挂到 category 上），全部结果封成 `ImmutableMap` 塞进 `BookContents`。异常策略是"带 id 的 RuntimeException"（:92、:101），由上层统一转成可显示的错误书。

关键细节：`getContentLoader()`（:138-146）决定用哪种 loader——`isExternal` 走磁盘；用户手动点"重载本书"（`singleBookReload`）时才绕过缓存直查资源包，注释明确写了"quick reload 不应复用陈旧数据"。

### 4.4 ClientBookRegistry：页类型注册表 + Gson 多态反序列化

`client/book/ClientBookRegistry.java:27-60` 维护 `Map<Identifier, Class<? extends BookPage>> pageTypes`（17 种内置页），`gson` 用 `registerTypeHierarchyAdapter(BookPage.class, LexiconPageAdapter)` 实现数据驱动的多态：JSON 的 `type` 字段查表拿类，**省略 `type` 的纯字符串页直接当成 `PageText`**（:101-106），**未知 type 回落 `PageTemplate`**（:115-117）——即"任何自定义 type 都是一次模板页调用"，这是模板系统能当扩展点的原因。`TemplateComponentAdapter` 同理由 `BookTemplate.componentTypes`（`template/BookTemplate.java:30-42`）解析组件类型。反序列化时把原始 `JsonObject` 存进 `sourceObject`，供变量系统二次求值。

### 4.5 模板 / 变量系统（Patchouli 最有价值的子系统）

`BookTemplate`（180 行）是"JSON 里的小 UI 框架"：`include` 声明嵌套模板（`TemplateInclusion` 负责重命名与外层变量封装 `wrapProvider`）、`processor` 字段是**类名字符串**，靠 `Class.forName(...).newInstance()` 反射实例化为 `IComponentProcessor`（:165-178）；`compile()` 递归展开所有 include 后逐个 `component.compile()`。变量侧由 `api/IVariable`（内部就是 `JsonElement` 的包装，提供 `as(Class)`）、`api/IVariableProvider`、`api/IVariableSerializer`、`template/VariableAssigner.java`（:33 注册一批变量函数）与 `template/variable/*VariableSerializer`（ItemStack / Ingredient / TextComponent / 数组）组成，实现了"JSON 值 → 运行时对象"的可插拔转换。文本内联语法由 `client/book/text/BookTextParser.java:32-33` 的 `COMMANDS`/`FUNCTIONS` 两张表驱动，`PatchouliAPI.registerCommand/registerFunction` 就是往这里塞。

### 4.6 进度 / 锁定体系（数据驱动的软依赖门控）

`AbstractReadStateHolder` + `EntryDisplayState` 组成状态机（UNREAD/PENDING/COMPLETED/NEUTRAL），`BookEntry.updateLockStatus()`（`client/book/BookEntry.java:150-167`）根据 `ClientAdvancements.hasDone(advancement)` 决定锁定，`compareTo`（:211-230）按"锁定 → 阅读状态 → priority → sortnum → 名称"排序。门控不看代码而看字符串：`canAdd()` 检查 `flag`（:192-194），`PatchouliConfig.getConfigFlag`（`common/base/PatchouliConfig.java:42-65`）支持 `!flag`、`&a,b`（AND）、`|a,b`（OR）表达式，并自动为每个已加载 mod 生成 `mod:<id>` 标志位（:27-40）——于是"某 mod 装了才显示这页"是纯 JSON 配置。阅读进度存在客户端文件 `patchouli_data.json`（`client/base/PersistentData.java:26`）。

### 4.7 多方块可视化

`common/multiblock/`（8 文件 884 行）：`DenseMultiblock` 从 `String[][] pattern` + 字符→方块映射构建（`DenseMultiblock.java:26-90`），`SparseMultiblock` 存坐标→matcher；匹配走 `IStateMatcher`/`StringStateMatcher`（支持 `minecraft:oak_stairs[facing=north]` 与 tag）。客户端 `client/handler/MultiblockVisualizationHandler.java:47` 单例负责世界内渲染、HUD 进度条与"锚定到结构"（:126-151）。

## 5. 网络 / 数据驱动 / 配置 / datagen

**网络**：两个 `CustomPacketPayload` record —— `MessageOpenBookGui(book, entry, page)`（`network/MessageOpenBookGui.java:13-31`，用 `StreamCodec.composite` 拼 codec，`entry` 用 `STRING_UTF8.map` 兼容空值）与 `MessageReloadBookContents`。NeoForge 侧 `RegisterPayloadHandlersEvent` + `PayloadRegistrar.playToClient`（`neoforge/network/NeoForgeNetworkHandler.java:19-23`），Fabric 侧 `PayloadTypeRegistry.clientboundPlay()` + `ClientPlayNetworking.registerGlobalReceiver`。**同步策略**：服务端只发"打开书/重载内容"两个指令型包，书内容本身永不过网。

**数据驱动**：目录约定为
`data/<ns>/patchouli_books/<book>/book.json`（书定义）、
`assets/<ns>/patchouli_books/<book>/<lang>/{categories,entries,templates}/<id>.json`（内容，1.20 起强制放客户端资源）。
重载链路有三条：客户端资源包 reload → `BookReloadHook`（`client/book/BookReloadHook.java`）/`BookContentResourceListenerLoader` 监听 → `ClientBookRegistry.reload()`（:62-65）；服务端 `/reload` → `ServerStartedEvent`(NeoForge) / `END_DATA_PACK_RELOAD`(Fabric) → `ReloadContentsHandler.dataReloaded` → 广播 `MessageReloadBookContents`；打开书时按需构建。

**配置**：平台各自实现，接口统一为 `api/PatchouliConfigAccess`。NeoForge 用 `ModConfigSpec`（`neoforge/common/NeoForgePatchouliConfig.java:23-58`，注释里直接标注对应的 config flag 名），Fabric 用 fiber（`fabric/common/FiberPatchouliConfig.java`）。配置项只有 7 个（禁用成就锁定、测试模式、快捷查找键、文本溢出策略等），真正的"开关"全部走 config flag。

**datagen**：无。所有内容 JSON 手写，`Xplat/src/test/resources/assets/patchouli/patchouli_books/comprehensive_test_book/` 是一本覆盖所有页型/组件/边界的"活文档测试书"，配 `Xplat/src/test/java/vazkii/patchouli/test/APITest.java` 用反射校验 API 方法名字符串仍准确。

## 6. Mixin

配置：`Xplat/src/main/resources/patchouli_xplat.mixins.json`（`package: vazkii.patchouli.mixin`, compatibilityLevel JAVA_21, 7 个 client 条目）与 `Fabric/src/main/resources/patchouli_fabric.mixins.json`（4 个 client 条目）；NeoForge 无自己的 mixin，但 `neoforge.mods.toml` 里声明了 `[[mixins]] config="patchouli_xplat.mixins.json"`。

| 类 | 目标 | 注入点 |
|---|---|---|
| `AccessorScreen` | `Screen` | `@Accessor("renderables")`、`("narratables")` |
| `AccessorMultiBufferSource` | `MultiBufferSource.BufferSource` | `@Accessor("sharedBuffer")`、`("fixedBuffers")` |
| `AccessorKeyMapping` | `KeyMapping` | `@Accessor("ALL")`（JEI 插件取按键） |
| `AccessorClientAdvancements` | `ClientAdvancements` | `@Accessor("progress")` |
| `MixinClientAdvancements` | 同上 | `@Inject(method="update", at=RETURN)` → 重算锁定 |
| `MixinInventoryScreen` | `InventoryScreen` | `@Inject(method="init()V", at=RETURN)` → 注入"打开书"按钮 |
| `MixinSystemReport` | `SystemReport` | `@Inject(method="<init>", at=RETURN)` → `BookCrashHandler` 把 Patchouli 状态写进崩溃报告 |
| Fabric `MixinGameRenderer` | `GameRenderer` | `render(DeltaTracker,Z)` HEAD/RETURN |
| Fabric `MixinMinecraft` | `Minecraft` | `disconnect(Screen,ZZ)` HEAD → 保存 `PersistentData` |
| Fabric `MixinAbstractContainerScreen` / `MixinGuiGraphicsExtractor` | 同名 | `extractTooltip` / `setTooltipForNextFrame`，用于接管书内物品的 tooltip |

特点：**几乎全是 Accessor 与"低侵入的 HEAD/RETURN 钩子"**，唯一算侵入的是 Fabric 侧把书按钮塞进容器界面（NeoForge 用官方 GUI 事件替代）。

## 7. 值得学的 5 条具体做法

1. **Xplat 单源 + ServiceLoader 抽象，平台模块只写胶水**：公共代码只依赖 `IXplatAbstractions` 接口，实现由 `META-INF/services/...IXplatAbstractions` 声明、`ServiceLoader` 在静态初始化时校验"恰好一个"（`Xplat/src/main/java/vazkii/patchouli/xplat/IXplatAbstractions.java:50-62`）；Fabric/NeoForge 各 16/10 个文件即可。适用：任何想同时支持 NeoForge + Fabric 的库。
2. **可选依赖用"反射加载 + stub 实现"**：`PatchouliAPI.get()` 用 `Class.forName("...PatchouliAPIImpl")` 找不到实现时返回 `api/stub/StubPatchouliAPI.INSTANCE`（`api/PatchouliAPI.java:35-42`、`api/stub/StubPatchouliAPI.java`），别的 mod 可以无条件 `compileOnly` 调用；配套 `apiJar` 只发布 `vazkii/patchouli/api/**`（`NeoForge/build.gradle` `include 'vazkii/patchouli/api/**'`）。适用：你写前置库模组时。
3. **JSON 里做"软依赖门控"**：`flag` 字段 + 布尔表达式（`!`、`&a,b`、`|a,b`）+ 自动 `mod:<id>` 标志位（`common/base/PatchouliConfig.java:27-65`），让内容作者零代码实现"装了某 mod 才出现"。适用：Create 附属/数据包友好型内容。
4. **预读缓存 + 双 loader 策略解决"大量 JSON 每次打开都要读盘"**：默认用 `SimpleJsonResourceReloadListener` 在资源重载时一次性缓存（`client/book/BookContentResourceListenerLoader.java:44-63`），仅在用户显式重载时退回直查（`client/book/BookContentsBuilder.java:138-146`）。适用：任何"资源包里有几百个 JSON 要频繁访问"的系统。
5. **加载失败降级而非崩溃 + 崩溃报告带上下文**：单本书装配异常 → `BookContents.empty(book, e)` 并在 GUI 显示（`common/book/Book.java:217-224`）；`MixinSystemReport` 把当前打开的书的栈信息写进 `SystemReport`（`mixin/client/MixinSystemReport.java:12-18`）。适用：数据驱动内容易被用户写错，必须"报错不崩"。

（附加）用一本覆盖所有特性的"测试书"当回归测试集（`Xplat/src/test/resources/.../comprehensive_test_book/`），并用单元测试反射校验 API 名（`Xplat/src/test/java/vazkii/patchouli/test/APITest.java:11-15`）——对 API 稳定性要求高的库模组很实用。

## 8. 公开 API 与外部 mod 接入方式

- **API 包**：`Xplat/src/main/java/vazkii/patchouli/api/`（15 文件），对外稳定承诺全在这里。
- **入口**：`PatchouliAPI.get()` 返回 `PatchouliAPI.IPatchouliAPI`（`api/PatchouliAPI.java:57-299`，接口内附完整 javadoc），实现类 `common/base/PatchouliAPIImpl.java` 在实现里对客户端专用方法统一 `assertPhysicalClient()` 双端保护（:61-66）。
- **扩展点接口**：`IComponentProcessor`（自定义 processor，需无参构造，靠类名反射实例化）、`ICustomComponent`、`IComponentRenderContext`、`IVariable`/`IVariableSerializer`/`IVariableProvider`/`IVariablesAvailableCallback`、`IMultiblock`/`IStateMatcher`、`IStyleStack`、`TriPredicate`、`PatchouliConfigAccess`、`VariableHelper`。
- **注册类扩展点**：`registerTemplateAsBuiltin(res, Supplier<InputStream>)`（注册内置模板，重复注册抛异常，:170-187）、`registerCommand`/`registerFunction`（往 `BookTextParser` 注册 `$(...)` 语法）、`registerMultiblock`、`makeMultiblock/makeSparseMultiblock` + 一系列 matcher 工厂；纯客户端扩展还有 `BookTemplate.registerComponent(Identifier, Class)` 与 `ClientBookRegistry.pageTypes`（页型/组件型注册表）。
- **平台事件**：NeoForge `api/BookContentsReloadEvent`、`api/BookDrawScreenEvent`（在 `NeoForge/.../api/`，经 `IXplatAbstractions.fireBookReload/fireDrawBookScreen` 派发）；Fabric 对应 `BookContentsReloadCallback`、`BookDrawScreenCallback`。
- **接入方式**：Maven 依赖 apiJar（`group=vazkii.patchouli`，artifactId `patchouli-neoforge`），或在 `build.gradle` 声明 `compileOnly`；内容侧只需把 JSON 放进上文目录结构，book.json 的 `dont_generate_book` + `custom_book_item` 可让 mod 用自己的物品当书。文档位于仓库 `web/docs/`（`reference/book-json.md`、`entry-json.md`、`category-json.md` 是完整字段表）。
