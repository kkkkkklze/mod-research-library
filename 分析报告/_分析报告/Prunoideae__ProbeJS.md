# Prunoideae/ProbeJS 源码分析报告

## 1. 基本信息

- Mod 名 ProbeJS；mod_id `probejs`；作者 Prunoideae；GPLv3（`src/main/resources/META-INF/neoforge.mods.toml:4`）
- MC 1.21.1 / NeoForge 21.1.199，Java 21，Parchment 2024.07.28；插件 `net.neoforged.moddev` 2.0.75；版本 8.0.3（`gradle.properties`）
- 依赖（`build.gradle`）：`kubejs-neoforge:2101.7.2-build.365`（api + `interfaceInjectionData`）、`rhino`、`tiny-java-server`（内置 HTTP）、`architectury`（compileOnly）、`javaparser`（jarJar 内置）
- 是 KubeJS 插件式前置：`src/main/resources/kubejs.plugins.txt` → `moe.wolfgirl.probejs.plugin.ProbeJSKJSPlugin`

## 2. 源码规模与包结构

135 个 `.java` / 10847 行。包（`moe.wolfgirl.probejs`）：`typescript`+`typescript/document/{base,members,types,types/special}`+`transpiler`（约 40 文件）、`plugin`+`builtins/{alias 9,events 5,extras 6,discovery 2}`、`java`+`java/members`、`misc/{gui 5,javadoc 4,llm 2,codegen 3,endpoints 1}`、`snippet`(9)、`dumps`(3)、`mixins`(5)、`utils`(4)

最大文件：`misc/javadoc/JavadocSanitizer.java`(531)、`java/members/ClassInfo.java`(374)、`java/ClassRegistry.java`(290)、`misc/gui/DumpScreen.java`(289)、`plugin/builtins/alias/RegistryTypes.java`(269)、`misc/javadoc/SourceJarParser.java`(250)

## 3. 入口与注册

主类 `ProbeJS.java:14` `@Mod(value = MOD_ID, dist = Dist.CLIENT)`，只存 `GSON`（含 `Path` 适配器）与 `MOD_CONTAINER`。三处注册：
- `plugin/ProbeJSKJSPlugin.java`：`registerBindings` 注入脚本全局 `require`；`registerLocalWebServer(WithAuth)` 挂 `/api/probejs/*`
- `GameEvents.java:22` `@EventBusSubscriber(Dist.CLIENT)`；`:61` 注册客户端命令 `/probejs`（`hasPermission(2)`）→ `DumpScreen.open()`
- `src/main/resources/probejs.mixins.json`

无 DeferredRegister（不注册游戏对象）。

## 4. 核心系统

**A. 类发现** `java/ClassRegistry.java`
- `fetchInitialClasses()` 遍历 `ModList.get().getModFiles()`：目录用 `Files.walk`、jar 用 `ZipFile.entries` 枚举 `.class`，`Class.forName(name,false,loader)` + `ClassInfo.resolve`
- `discover()` 按 `ProbeConfig.recursionDepth`（默认 5）BFS 扩散被引用类，`ClassRecord(info, recursionDepth)` 支持 `writeTo/readFrom` 落盘缓存
- 跑在 `RenderSystem.recordRenderCall(...)` 内 + `CountDownLatch.await()` 强制主线程（`:86`）；`shouldSkipClass` 过滤 `mixin(s)` 包、`package-info`、`architectury_inject` 前缀（`:226`）

**B. TS 文档生成** `typescript/Documents.java:55`
- `transpile()`：`Transpiler`+`TypeConverter` 把 `ClassRegistry` 全部类转 `ClassDecl`，再回调插件 `modifyClasses(ClassAccessor)`（可增删文档）
- `getInputAlias` 生成 `X_` 联合类型（`classPath.withSuffix("_")`），解决 KubeJS 松入参无法补全；`addGlobal` 故意抛异常，全局声明交给 `SpecialDocuments`

**C. 插件扩展点** `plugin/ProbeJSPlugin.java`
- 11 个回调：`initialize`/`transformClass`/`modifyClasses`/`addTypeAlias`/`addSpecialDocuments`/`addSidedDocuments`/`provideClassForDiscovery`/`allowClassInDiscovery`/`addSnippets`/`addUsageHintsForAgents`
- `forEachWithPriority(methodName, consumer)`（`:97`）：反射读方法上的 `@Priority` 排序，合并内置插件与 `KubeJSPlugins.forEachPlugin` 收集的第三方插件，单个插件异常只记日志不中断
- `ProbeConfig.findFullScanMods()` 以"jar 内是否存在 `kubejs.plugins.txt`"识别 KubeJS 插件 mod

**D. Javadoc 注入** `misc/javadoc/SourceJarDownloader.java`（按 `ProbeConfig.modSources` 下载 sources jar）→ `SourceJarParser` → `JavadocSanitizer` → 写入 TS 注释

**E. 进度/GUI**：`GameStates.DUMP_STATE`（`DumpState`）+ `misc/gui/DumpScreen`，逐阶段 `setStatus/incrementProgress`

## 5. 网络 / 数据驱动 / 配置 / datagen

- 无自定义网络包；对外用本地 HTTP：`misc/endpoints/ProbeJSWeb.java` 注册 `/api/probejs/list-commands`、`/run-command`
- 配置不用 `ModConfigSpec`：自建 `ProbeConfig.ConfigEntry<T>`（`ProbeConfig.java:64`）读写 `.vscode/settings.json` 与 `config/probe-settings.json`；键：`recursionDepth`、`forceIncluded`、`generateBeans`、`hintsForLLM`、`fullScanMods`、`modSources`
- 产物（`dumps/ProjectDump.java`）：`.vscode/probejs.code-snippets`、`kubejs/{client,server,startup}_scripts/jsconfig.json`、`package.json`；`hintsForLLM` 开启时额外输出 `assets/probejs/dumps/kubejs-{planner,explore,survey}.agent.md`
- 无 datagen

## 6. Mixin

`src/main/resources/probejs.mixins.json`（`defaultRequire: 1`）：
- client：`JavaWrapperMixin`（`@Mixin(JavaWrapper, remap=false)`，`loadClass`/`tryLoadClass` at RETURN，记录脚本加载的 Java 类）、`LootTableMixin`（`@Mixin(LootDataType)` `deserialize` RETURN）、`RecipeManagerMixin`（`@Mixin(value=RecipeManager.class, priority=900)`，`@Inject(method="apply*", at=HEAD)` 收集非 `kjs_` 配方 id）、`TranslatableMixin`（`TranslatableContents.<init>` RETURN + `@Shadow @Final key/fallback`）
- main：`GiveCommandMixin`（`@Mixin(GiveCommand)` `register` HEAD + cancellable，重写 `/give` 支持 tag）
- 另有 `META-INF/accesstransformer.cfg`

## 7. 值得学的 5 条做法

1. **反射全量扫描 mod jar 构类型图**：`ModList.getModFiles()` + `ZipFile` 枚举 entry，不依赖 classpath；`java/ClassRegistry.java:193`。
2. **BFS 引用扩散 + 深度上限**：从种子类按引用递归，`recursionDepth` 可配；`ClassRegistry.java:76`。
3. **主线程 + 闭锁调度重活**：`recordRenderCall` 内扫描、主线程 `await`，规避并发类加载；`ClassRegistry.java:86`。
4. **`@Priority` 注解 + 反射排序的插件回调**：无需新注册表即实现"内置+第三方统一有序、异常隔离"；`plugin/ProbeJSPlugin.java:97`。
5. **插件清单自动发现 + `interfaceInjectionData`**：靠 jar 内 `kubejs.plugins.txt` 被宿主加载；`build.gradle` dependencies、`ProbeConfig.java:36`。

## 8. 公开 API

- 扩展入口：`moe.wolfgirl.probejs.plugin.ProbeJSPlugin`（实现后注册为 KubeJS 插件）
- 模型/注册：`typescript/base/{DocumentRegistrar,DocumentRegistry}`、`typescript/ClassPath`（含 `ClassPath.sided`）、`typescript/{SpecialDocuments,SidedDocuments}`、`snippet/SnippetRegisterer`
- 元数据：`java/members/{ClassInfo,FieldInfo,MethodInfo,ConstructorInfo}`、`java/PackageTree`；`plugin/builtins/*` 本身就是用该接口写的别名/事件文档范例
