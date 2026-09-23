# AppliedEnergistics/GuideME 源码分析报告

## 1. 基本信息

- Mod 名：GuideME；mod_id：`guideme`；作者：shartte（`src/main/neoforge.mods.toml`）
- 目标版本/加载器：**Minecraft 26.1.2 + NeoForge 26.1.2.10-beta，仅 NeoForge**（`gradle.properties`：`java_version=25`、`neoforge_version_range=[26.1.2.10-beta,26.2-)`）
- Gradle：ModDevGradle `net.neoforged.moddev` 2.0.134 + **`com.gradleup.shadow` 9.3.0**（`settings.gradle`）；根工程 `guideme` **include 子工程 `markdown`**（`settings.gradle` 末行）
- 许可证：LGPL-3.0（`LICENSE.md`，mods.toml 写 `license="See GitHub repository for details"`）
- 编译依赖（`build.gradle`）：`shaded "com.google.flatbuffers:flatbuffers-java"`；`shaded(localImplementation("org.apache.lucene:lucene-*"))` 共 8 个 Lucene 模块（core / analysis-common / queryparser / facet / queries / highlighter / memory）；`shadow { relocate "com.google.flatbuffers", "guideme.internal.shaded.flatbuffers"; relocate "org.apache.lucene", "guideme.internal.shaded.lucene" }`（`:243-244`）。另有 snakeyaml、directory-watcher、ffmpeg、junit/assertj 用于测试
- 定位：**纯库/前置 mod**（AE2 的硬依赖，`guideme` 在 AE2 的 mods.toml 中为 REQUIRED）

## 2. 源码规模与包结构

实测：**521 个 .java，58309 行**（含 `markdown` 子工程 151 类、`src/main/flatbuffers/generated` 下的 FlatBuffers 生成类、`src/test` 14 类）。

根包 `src/main/java/guideme` 286 个类，分布：`internal` 94、`document` 52、`scene` 43、`compiler` 30、`render` 13、`layout` 10、`siteexport` 9、根目录直接放公开 API 9 个类（`Guide`/`GuideBuilder`/`Guides`/`GuidePage`/`PageAnchor`/`GuideItemSettings`…）、`color` 8、`style` 6、`indices` 5、`extensions` 3、`navigation` 2、`ui` 2。`internal` 下再分：`siteexport` 20、`web` 14、`screen` 12、`search` 8、`util` 9、`command` 5、`item`/`data` 3、`scene` 2、`network`/`hotkey`/`datadriven` 各 1。

`markdown` 子工程是自研 Markdown 解析器：`guideme/libs/{micromark,mdast,mdx,unist}`（micromark 是 JS 库的 Java 移植，含 `commonmark`/`factory`/`symbol`/`html`/`extensions`）。

最大文件：`markdown/.../micromark/NamedCharacterEntities.java` 2151、`MdastCompiler.java` 1027、`internal/web/WebPageCompiler.java` 947、`HtmlCompiler.java` 871、`mdx/FactoryTag.java` 746、`scene/element/FakeForwardingServerLevel.java` 742、`internal/siteexport/SiteExporter.java` 707、`internal/screen/DocumentScreen.java` 628。

## 3. 入口与注册

两个 `@Mod` + 代理模式：`guideme.internal.GuideME`（`@Mod(value = GuideME.MOD_ID)`，公共侧）与 `guideme.internal.GuideMEClient`（`dist = Dist.CLIENT`）；通过 `GuideME.PROXY` 静态字段切换 `GuideMEServerProxy`/`GuideMEClientProxy`（`GuideME.java:27`，`GuideMEClient.java:78`）。

`GuideME.java:31-57` 用新版 NeoForge 注册 API 的简写形式，全部注册即用即弃（无独立 registries 类）：

```java
private static final DeferredRegister.Items DR_ITEMS = DeferredRegister.createItems(MOD_ID);
private static final DeferredRegister<ArgumentTypeInfo<?, ?>> DR_ARGUMENT_TYPE_INFOS =
        DeferredRegister.create(Registries.COMMAND_ARGUMENT_TYPE, MOD_ID);
public static final Supplier<GuideItem> GUIDE_ITEM = DR_ITEMS.registerItem("guide", GuideItem::new);
public static final DataComponentType<Identifier> GUIDE_ID_COMPONENT = DataComponentType.<Identifier>builder()
        .networkSynchronized(Identifier.STREAM_CODEC).persistent(Identifier.CODEC).build();
...
DR_ARGUMENT_TYPE_INFOS.register(modBus); DR_ITEMS.register(modBus); drDataComponents.register(modBus);
```

注册内容极少：1 个通用指南物品 `guideme:guide`、1 个数据组件 `guideme:guide_id`、2 个命令参数类型（`GuideIdArgument`/`PageAnchorArgument`）、1 个网络包、1 条命令、1 个配方同步（`OnDatapackSyncEvent.sendRecipes(CRAFTING, BLASTING, SMELTING, SMITHING)`，`GuideME.java:87-93`，用于内嵌配方渲染）。客户端额外挂：配置（`registerConfig(CLIENT, ..., "guideme.toml")`）、配置界面扩展点、快捷键、物品模型、渲染管线、PiP 渲染器（`GuideMEClient.java:80-136`）。

## 4. 核心系统

**(1) 指南构建 API（对外主入口）** — `src/main/java/guideme/GuideBuilder.java`
- `Guide.builder(id)` → `GuideBuilder`，字段驱动：`folder` 默认 `guides/<ns>/<path>`（`:49`、`:104`）、`startPage` 默认同命名空间的 `index.md`（`:50`）、默认索引自动加入 `ItemIndex`+`CategoryIndex`（`:63-64`）
- 开发期热重载靠系统属性注入源目录：`System.getProperty(getSystemPropertyName(id, "sources"))`（`:53-60`），交给 `internal/GuideSourceWatcher.java`（directory-watcher 库）监听变更
- 全局注册表 `Guides`（`Guides.java`）只暴露 `getAll()/getById()/createGuideItem(id)`，真实存储在 `internal/GuideRegistry`；`GuideBuilder.register(false)` 可关掉自动注册（文档注释列出会失去的能力：启动自动展示、快捷键、资源重载）

**(2) Markdown 编译管线** — `src/main/java/guideme/compiler/`
- `PageCompiler` + `ParsedGuidePage` + `Frontmatter`（front-matter 元数据）+ `LinkParser` + `MdAstNodeAdapter`（把 markdown 子工程的 mdast 树适配成自己的节点）+ `IndexingSink`/`IndexingContext`
- `compiler/tags/` 19 个内建标签编译器：`ATagCompiler`（基类）→ `FlowTagCompiler`/`BlockTagCompiler`，实现 `BoxTagCompiler`、`ItemLinkCompiler`、`ItemGridCompiler`、`RecipeCompiler`、`SubPagesCompiler`、`CommandLinkCompiler`、`ColorTagCompiler`、`KeyBindTagCompiler`、`FloatingImageCompiler`、`BreakCompiler` 等；`MdxAttrs` 统一属性读取，`parent.appendError(compiler, msg, el)` 会把错误定位回源文件行

**(3) 3D 场景系统** — `src/main/java/guideme/scene/`
- `GuidebookScene` + `GuidebookLevel`，用虚拟世界 `scene/element/FakeForwardingServerLevel.java`（742 行，转发式 ServerLevel）承载从结构文件加载的建筑；提供 `worldToScreen`/`documentToScreen`/`screenToDocument` 坐标互转与 `pickAnnotation`/`pickBlock`
- 标注分 `InWorldAnnotation`（世界内，可被方块遮挡，用 `OCCLUDED_PIPELINE`）与 `OverlayAnnotation`；`scene/annotation/`、`scene/element/` 下 7 个元素编译器（`ImportStructureElementCompiler`、`SceneBlockElementCompiler`、`EntityElementCompiler`、`IsometricCameraElementCompiler` 等）
- `scene/export/` 把场景烘成 `Mesh` 并写出 FlatBuffers（`ExpScene`/`ExpMesh`/`ExpMaterial`/`ExpCameraSettings` 等，`src/main/flatbuffers/generated/guideme/flatbuffers/scene/`），供网页版使用

**(4) 全文搜索（Lucene）** — `src/main/java/guideme/internal/search/`
- `GuideSearch` + `PageIndexer` + `IndexSchema` + `GuideQueryParser` + `QueryStringSplitter`；`Analyzers`/`EnglishAnalyzer`/`LanguageSpecificAnalyzerWrapper` 做按语言选分词器（`GuideBuilder` 里可用 `defaultLanguage` 指定索引语言）

**(5) 静态站点导出** — `src/main/java/guideme/internal/siteexport/` + `guideme/siteexport/`
- `SiteExporter`→`SiteExportWriter`，`internal/web/WebPageCompiler.java`（947 行）把编译后的页面转成 HTML，配 `WebPExporter`/`TextureDownloader`/`CacheBusting`/`OffScreenRenderer`/`RawProjectionMatrixBuffer` 导出图片与资源；`mdastpostprocess/` 做 AST 后处理。对外的 `guideme.siteexport` 包给出 9 个可扩展类

**(6) 扩展点机制** — `src/main/java/guideme/extensions/`
- `ExtensionPoint<T>(Class<T>)` + `Extension` + `ExtensionCollection`（构造时用 `IdentityHashMap` 校验并冻结，注册错类型直接抛 `IllegalArgumentException`）
- 8 个公开扩展点：`TagCompiler.EXTENSION_POINT`、`RecipeTypeMappingSupplier`、`SymbolicColorResolver`、`ImplicitAnnotationStrategy`、`SceneElementTagCompiler`、`RecipeExporter`、`ExportPostProcessor`、`AdditionalResourceExporter`；`GuideBuilder` 支持按扩展点关闭内建默认实现（`disableDefaultsForExtensionPoints`，`:41-42`）

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：仅 1 个包 `internal/network/OpenGuideRequest.java`（playToClient），在 `GuideME.java:70-80` 注册，用于命令/快捷键触发客户端打开指定指南与锚点
- **数据驱动（重点）**：指南本身可由**资源包**完整定义（`docs/docs/20-data-driven-guides.md`）——`assets/<ns>/guideme_guides/<path>.json` 定义 guide（`item_settings.display_name`/`tooltip_lines`/`model`），页面为 `assets/<ns>/guides/<ns>/<path>/*.md`；仓库自带 `src/testmod/resources/assets/testmod/guides/testmod/guide/` 示例（含 `subpage.md`、`markdown.md`、`japanese.md` 等）
- **配置**：客户端 `ModConfigSpec`（`guideme.toml`），并注册 `IConfigScreenFactory` 提供游戏内配置界面（`GuideMEClient.java:80/110`）
- **datagen**：**无**（无 datagen 源集，也不产出数据包文件）
- **测试**：`src/test` 14 个 JUnit 类（覆盖 `layout/flow`、`internal/search`、`compiler/tags`、`extensions`、`color`）+ 游戏内测试 mod `src/test/java/guideme/guidebook/TestMod.java` + `src/testmod` 资源包

## 6. Mixin

两份配置：`src/main/resources/guideme.mixins.json`（`required: true`，包 `guideme.internal.hooks.mixins`，**数组为空**——为将来预留的必需配置）与 `guideme.optional.mixins.json`（**`required: false` + `defaultRequire: 0`**，客户端列表只有 `LuceneVectorizationMixin`）。

`Guideme.optional` 的 `internal/hooks/mixins/LuceneVectorizationMixin.java`：`@Mixin(targets = "guideme.internal.shaded.lucene.internal.vectorization.VectorizationProvider", remap = false)`，`@Inject(method = "lookup", cancellable = true, at = @At("HEAD"))` 反射构造 `DefaultVectorizationProvider` 并直接返回返回值——阻止 Lucene 探测 incubator Vector 模块（会打印启动报错，用户真开了该模块时还会崩）。两个 `[[mixins]]` 均在 mods.toml 声明。

## 7. 值得学的 5 条具体做法

1. **把第三方解析器整体移植为独立 Gradle 子工程，并声明为库**：`markdown/build.gradle` 的 `jar { manifest { attributes('FMLModType': 'LIBRARY') } }` —— 适用想在 mod 内复用大型 JS/Python 库逻辑的场景。
2. **shadow + relocate 内嵌重依赖**：`build.gradle:243-244` 把 Lucene/FlatBuffers 重定位到 `guideme.internal.shaded.*` —— 适用库 mod 需要重量级依赖又不想与别人冲突。
3. **开发期目录监听热重载**：`GuideBuilder.java:53-60`（系统属性 `-Dguideme.<id>.sources=<path>`）+ `internal/GuideSourceWatcher.java` —— 适用"内容在资源文件里、作者需要即时预览"的 mod。
4. **一个扩展点一个 `static ExtensionPoint<T>` 字段 + 注册时类型校验**：`extensions/ExtensionPoint.java`、`ExtensionCollection.java:27-38`、`compiler/TagCompiler.java:16` —— 适用需要给第三方提供多种扩展位且要求失败即报错的库。
5. **用 NeoForge Picture-in-Picture 渲染器在 GUI 里嵌 3D**：`GuideMEClient.java:132-133`（`registerPipRenderers(ScenePictureInPictureRenderer::new)`）+ `internal/scene/ScenePictureInPictureRenderer.java` —— 适用指南/图鉴类 mod 展示多方块或实体预览。

## 8. 公开 API（库 mod）

- API 包：根包 `guideme`（`Guide`/`GuideBuilder`/`Guides`/`GuidePage`/`PageAnchor`/`PageCollection`/`GuidesCommon`/`GuideItemSettings`/`GuidePageChange`）、`guideme.extensions`、`guideme.compiler` + `guideme.compiler.tags`（`ATagCompiler`/`FlowTagCompiler`/`BlockTagCompiler`/`RecipeTypeMappingSupplier`）、`guideme.scene`（含 `SceneElementTagCompiler`、`ImplicitAnnotationStrategy`、`CameraSettings`）、`guideme.color`（`SymbolicColorResolver`）、`guideme.indices`（`ItemIndex`/`CategoryIndex`/`PageIndex`/`UniqueIndex`/`MultiValuedIndex`）、`guideme.siteexport`、`guideme.document`（`LytRect`/`LytSize` 等布局原语）、`guideme.style`、`guideme.render`、`guideme.ui`、`guideme.layout`
- 接入方式（`docs/docs/20-integration/index.md`）：Gradle 里 `compileOnly "org.appliedenergistics:guideme:${guideme_version}:api"` + `runtimeOnly "org.appliedenergistics:guideme:${guideme_version}"`（**提供独立 `:api` 分类器 jar**）；代码里在 mod 构造器内 `Guide.builder(Identifier.parse("mymod:guide")).extension(TagCompiler.EXTENSION_POINT, new MyTagCompiler()).build()`
- 可选依赖兜底：外部 mod 不想自定义指南物品时，可只调用 `Guides.createGuideItem(guideId)` 复用 `guideme:guide` 通用物品；自定义标签须加 mod-id 前缀避免命名冲突
