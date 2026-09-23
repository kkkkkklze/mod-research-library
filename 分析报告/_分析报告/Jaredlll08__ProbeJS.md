# Jaredlll08/ProbeJS 源码分析报告

> **仓库位置更正**：GitHub 上不存在 `Jaredlll08/ProbeJS`（`git ls-remote` 返回 not found）。本次分析基于本地快照 `_参考仓库/_bulk/Prunoideae__ProbeJS`，其 remote 为 **`https://github.com/Prunoideae/ProbeJS.git`**，分支 `1.21`，HEAD `7e231ab`（2026-08-02，"Fixing up events, also add addons to full scan mods"）。下游如需按目录名索引，请以 `Prunoideae/ProbeJS` 为准。

## 1. 基本信息

- Mod 名 / id：ProbeJS / `probejs`；作者 `Prunoideae`；`maven_group=moe.wolfgirl`；`mod_version=8.0.3`（`gradle.properties`、`src/main/resources/META-INF/neoforge.mods.toml`）
- 目标环境：MC **1.21.1** / **NeoForge 21.1.199**（`loom.platform=neoforge`，Parchment 1.21 / 2024.07.28）；**纯客户端**（`ProbeJS.java:15` `@Mod(value = ProbeJS.MOD_ID, dist = Dist.CLIENT)`）
- Gradle：Architectury Loom（`loom.platform`）+ 发布脚本；许可证 **GPLv3**（`neoforge.mods.toml:4`，仓库根无 LICENSE 文件）
- 编译依赖（`build.gradle` dependencies）：`api rhino:2101.2.7-build.80 (transitive=false)`、`api kubejs-neoforge:2101.7.2-build.365` + `interfaceInjectionData(kubejs)`、`implementation tiny-java-server:1.0.0-build.25`、`compileOnly architectury-neoforge:13.0.2`、`jarJar` 打包 `javaparser-core` 与 `javaparser-symbol-solver-core:3.24.8`
- 依赖关系：**KubeJS（+ Rhino）是它唯一的 API**；它自身对外提供 `ProbeJSPlugin` 扩展点（见 §8）

## 2. 源码规模与包结构

实测 **135** 个 `.java`，共 **10847** 行，包前缀统一 `moe.wolfgirl.probejs`。

| 包 | 文件数 | 包 | 文件数 |
|---|---|---|---|
| `typescript/document/types` | 14 | `typescript/transpiler/members` | 5 |
| `plugin/builtins/alias` | 9 | `plugin/builtins/events` | 5 |
| `plugin/builtins` | 7 | `mixins` | 5 |
| `typescript/document/base` | 6 | `misc/gui` | 5 |
| `typescript` | 6 | `utils` | 4 |
| `snippet/parts` | 6 | `typescript/document/members` | 4 |
| `plugin/builtins/extras` | 6 | `plugin` | 4 |
| `probejs`（根） | 6 | `misc/javadoc` | 4 |
| `java/members(+/other)` | 4+4 | `typescript/document/builders`、`typescript/base`、`snippet`、`misc/codegen` | 各 3 |

最大文件：`misc/javadoc/JavadocSanitizer`(531)、`java/members/ClassInfo`(374)、`java/ClassRegistry`(290)、`misc/gui/DumpScreen`(289)、`plugin/builtins/alias/RegistryTypes`(269)、`misc/javadoc/SourceJarParser`(250)、`plugin/builtins/events/RecipeEvents`(228)、`typescript/document/ClassDecl`(219)、`alias/WorldTypes`(200)、`misc/javadoc/ParchmentClass`(199)。

## 3. 入口与注册

- `ProbeJS.java`（33 行）只持有 `MOD_ID/LOGGER/GSON/GSON_WRITER/MOD_CONTAINER`；启动逻辑在 `@EventBusSubscriber(value = Dist.CLIENT)` 的 `GameEvents.java`：注册客户端命令 `/probejs`（`requires(source -> source.hasPermission(2))` 打开 `DumpScreen`，`:60-71`），并用 `PlayerInteractEvent.RightClickBlock/EntityInteract` 记录 `GameStates.LAST_RIGHTCLICKED/LAST_ENTITY` 供 dump 时推断上下文
- KubeJS 插件入口 `src/main/resources/kubejs.plugins.txt` → `moe.wolfgirl.probejs.plugin.ProbeJSKJSPlugin extends KubeJSPlugin`：`registerBindings` 注入脚本全局 `require`（`Require.Wrapper`，`misc/Require.java`，实为 `Java.loadClass` 的别名，仅接受 `@package/...` 路径）、`registerLocalWebServer/WithAuth` 注册 HTTP 端点、`registerEvents` 为空（TODO）
- dump 编排是一个 10 步状态机：`DumpState.TOTAL_STEPS = 10`，`startDump()` 顺序执行 initialize → addUsageHintsForAgents → `fetchInitialClasses()` → `discover()` → `PackageDump.dump()` → `OtherDump.dump()` → `ProjectDump.dump()`，结束时 clear 各文档注册表并 `System.gc()`（`DumpState.java:27-75`）

## 4. 核心系统

1) **类发现 `java/ClassRegistry.java`**：`fetchInitialClasses()`（`:146-192`）先取插件白名单（`provideClassForDiscovery` / `allowClassInDiscovery`），再遍历 `findModFiles()` 得到的每个 mod jar/目录、`findEntries()` 枚举 `*.class`、`shouldSkipClass()` 过滤（mixin 包等）、以 `Class.forName(name, false, loader)` **不初始化**加载，跳过匿名类；`discover()`（`:76-124`）在 `RenderSystem.recordRenderCall` 内做按 `ProbeConfig.recursionDepth`（默认 5）限深的 BFS，用 `ClassInfo.getReferredClasses()` 逐层扩展，`CountDownLatch` 与调用线程同步；`ClassRecord` 支持 `writeTo/readFrom` 落盘缓存
2) **Java→TS 转译管线**：`typescript/Documents.transpile()`（`Documents.java:99-116`）用 `TypeConverter`（`typescript/transpiler/TypeConverter.java:30-77`）把 Rhino 的 `TypeInfo` 映射为 document 树——`ClassTypeInfo`→`ClassType`（泛型参数填 `any`）、`ArrayTypeInfo`→数组、`ParameterizedTypeInfo` 特判 `RAW_OPTIONAL`→`Types.optional`、`ClassWrapper`→`Types.typeOf`、`JSOrTypeInfo`→联合类型、`JSNumber/JSStringConstantTypeInfo`→字面量类型；再经 `Transpiler` + `transpiler/members/{Field,Method,Constructor,Param}Converter` 生成 `ClassDecl/FieldDecl/MethodDecl/ConstructorDecl`；最后回调 `modifyClasses(ClassAccessor)` 允许插件增删文档
3) **三套文档注册表 + 包树输出**：`Documents`（类文档 + 输入别名 `addInputAlias`）、`SpecialDocuments`、`SidedDocuments` 均实现 `DocumentRegistry`（`getDocument/getInputAlias/getGlobal/resolveTree`）；`dumps/PackageDump.java`/`OtherDump.java` 遍历 `PackageTree`，每个包由 `typescript/IndexFile.java` 汇总类文档与 import、re-export 子包、写入 `index.d.ts`（根包写到 `@package`、`@special` 目录）；`getInputAlias` 会额外生成 `X_` 联合别名类型，注释明确说明是为规避 TS 结构化类型污染补全（`Documents.java:135-152`）
4) **插件扩展与优先级**：`plugin/ProbeJSPlugin.java` 定义 `initialize/transformClass/modifyClasses/addTypeAlias/addSpecialDocuments/addSidedDocuments/provideClassForDiscovery/allowClassInDiscovery/addSnippets/addUsageHintsForAgents`；`forEachWithPriority`（`:107-124`）把 `ProbeBuiltinDocs` 与所有实现该类的 KubeJS 插件合并，按方法上的 `@Priority`（`plugin/Priority.java`）**反射**排序后调用，且逐个 try/catch，单插件异常只记日志不影响整体 dump
5) **Javadoc/Parchment 注入**：`misc/javadoc/SourceJarDownloader` 按 `ProbeConfig.modSources`（默认 NeoForge 的 `neoforge-21.1.199-sources.jar`）下载源码 jar 到 `.probe/source_jars`，`SourceJarParser` + javaparser 解析、`JavadocSanitizer` 清洗 HTML 后由 `plugin/builtins/InjectParchment` 写进类型注释
6) **LLM/Agent 支持**：`misc/llm/NotesToLLM`（`ClassPath → List<String>`）由 `addUsageHintsForAgents` 收集，`plugin/builtins/InjectDocsForAgents`（`@Priority(-100)`）把它排在类声明下方写入 d.ts；另外 `RequireToLoadClass` 与 `DumpScreen` 的 Convert 按钮可把脚本里的 `require()` 自动改写为 `Java.loadClass()`

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无自定义包；改用 KubeJS 内建本地 Web 服务（`LocalWebServerRegistry`）——`GET /api/probejs/list-commands` 返回玩家名与全部命令的 `getSmartUsage` 列表，`POST /api/probejs/run-command`（需鉴权）由服务端以首个玩家的 `DelegatedSourceStack` 执行命令并回传消息（`misc/endpoints/ProbeJSWeb.java:26-42`）
- **配置**：`ProbeConfig`（单例 `INSTANCE`）以 `ConfigEntry<T>` 声明 `enabled/recursionDepth/reset/forceIncluded/generateBeans/hintsForLLM/excludedClassPaths/fullScanMods/explicitNames/newGame/modSources`，通过 KubeJS 配置 API 读写；文件路径常量 `ProbePaths.SETTINGS_JSON = kubejs/config/probe-settings.json`，另有游戏内 GUI（`misc/gui/DumpScreen` 289 行 + `DumpGuiComponents/TexturedCheckbox/TexturedProgressBar`）配置并显示 10 步进度
- **datagen**：无 Forge datagen；产物全部是运行时生成的 TS 工程文件——`kubejs/@package/**/index.d.ts`、`kubejs/@special`、`kubejs/@sided`、`kubejs/{client,server,startup}_scripts/jsconfig.json`、`kubejs/package.json`、`.vscode/probejs.code-snippets`、以及 `hintsForLLM=true` 时的 `.github/agents/kubejs-{planner,explore,survey}.agent.md`（模板位于 `src/main/resources/assets/probejs/dumps/`；本检出中只见 3 个 `.agent.md`，jsconfig/package.json 模板文件未见，**未确认**）
- 片段系统：`snippet/Snippet.java`(150) + `snippet/parts/{TabStop,Choice,Variable,Literal,Enumerable}` 构建 VSCode code-snippets JSON（`SnippetRegistry.writeTo`）

## 6. Mixin

配置 `src/main/resources/probejs.mixins.json`（`required:true`、`package moe.wolfgirl.probejs.mixins`、`JAVA_17`、`defaultRequire:1`）：

| Mixin | 目标 | 注入点 |
|---|---|---|
| `JavaWrapperMixin` (client) | `dev.latvian.mods.kubejs.plugin.builtin.wrapper.JavaWrapper` | `loadClass`、`tryLoadClass(...)`，均 `@At("RETURN")`，`remap=false`（记录脚本加载过的类） |
| `LootTableMixin` (client) | `LootDataType` | `deserialize` `@At("RETURN")`（配合 `GameStates.LOOT_TABLES`） |
| `RecipeManagerMixin` (client) | `RecipeManager`，`priority = 900` | `apply*` `@At("HEAD")`（收集配方 JSON → `GameStates.RECIPE_IDS`） |
| `TranslatableMixin` (client) | `TranslatableContents` | `<init>` `@At("RETURN")` + `@Shadow`（收集语言键） |
| `GiveCommandMixin` (mixins) | `GiveCommand` | `register` `@At("HEAD")`，`cancellable = true`（164 行） |

配套 `META-INF/accesstransformer.cfg` 打开 `ClientLanguage.storage`、`TextureAtlas.texturesByName`、`TextureManager.byPath`、`ModelManager.bakedRegistry`、`StateHolder.PROPERTY_ENTRY_TO_STRING_FUNCTION`、`CreativeModeTabs.CACHED_PARAMETERS`、`NativeImage.writeToChannel`，供 dump 读取贴图/语言键/创造标签页等内部数据。

## 7. 值得学的 5 条

1. 海量反射扫描放到渲染线程执行并用 `CountDownLatch` 交回结果（`java/ClassRegistry.java:91-121` "We run the discovery in the render thread"，`DumpState` 的 10 步进度同步刷新 GUI）
2. 类发现用 `Class.forName(name, false, loader)`（不触发静态初始化）+ 只遍历 mod jar 的 `.class` 条目 + 跳过 mixin 包与匿名类（`ClassRegistry.fetchInitialClasses`），把加载失败降级为"只丢一个类"的日志
3. 插件模型用「同名方法 + 反射读注解 `@Priority`」排序，且 `forEachWithPriority` 对每个插件 try/catch：任何一个附加 mod 抛异常都不会让整个 dump 失败（`plugin/ProbeJSPlugin.java:107-124`）
4. 把类型信息抽象成独立 document 树（`typescript/document/**` 的 `ClassDecl/MethodDecl/Types.*`）再统一解析符号与 import（`IndexFile.setResolvedSymbols`），因此同一套管线可同时输出 `@package/@special/@sided` 三个命名空间并支持 `jarJar` 内嵌 javaparser 解析 javadoc
5. 面向 AI 使用者的产品化设计：`NotesToLLM` + `addUsageHintsForAgents` 把用法提示写进 d.ts，`ProjectDump` 直接生成 `.github/agents/*.agent.md`，并提供 `require`→`Java.loadClass` 的兼容层与自动改写提示（`misc/Require.java`、`misc/RequireToLoadClass.java`、`GameEvents.playerJoined`）

## 8. 公开 API / 外部接入方式

- 扩展点：实现 `moe.wolfgirl.probejs.plugin.ProbeJSPlugin`（其本身 `implements dev.latvian.mods.kubejs.plugin.KubeJSPlugin`），在自己的 jar 里放 `kubejs.plugins.txt` 写类名即可被发现；可覆写方法：`initialize`、`transformClass(Documents.ClassDocument)`、`modifyClasses(Documents.ClassAccessor)`、`addTypeAlias(AliasRegistrar)`、`addSpecialDocuments(DocumentRegistrar)`、`addSidedDocuments(DocumentRegistrar)`、`provideClassForDiscovery()`、`allowClassInDiscovery(Class)`、`addSnippets(SnippetRegisterer)`、`addUsageHintsForAgents(NotesToLLM.Registry)`，并按方法标注 `@Priority(int)` 控制顺序（内建示例见 `plugin/builtins/Bindings.java`、`alias/*`、`events/*`）
- 脚本侧 API：全局 `require("@package/...")`（`ProbeJSKJSPlugin.registerBindings`）
- Web API：`GET /api/probejs/list-commands`、`POST /api/probejs/run-command`（VSCode 扩展/Agent 用，`ProbeJSWeb`）
