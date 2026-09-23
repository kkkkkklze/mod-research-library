# IrisShaders/Iris 源码分析报告

> 分析对象：`_参考仓库/_bulk/IrisShaders__Iris`（分支 trunk，MOD_VERSION 1.11.4）
> 注：本次下载的工作副本被过滤掉了所有 `*.json` / `*.lang` / shader 源文件（磁盘上 `find -name '*.json'` 为 0 个，git 索引中有 42 个），因此 mixin 配置、`fabric.mod.json` 等内容通过 `git show HEAD:<path>` 读取，已在正文标注。

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / modId | Iris / `iris`（`Iris.java:78` `MODID`，`Iris.java:85` `MODNAME`） |
| 作者 | coderbot、IMS212（`neoforge.mods.toml`）；`fabric.mod.json` 另列 Justsnoopy30、FoundationGames |
| 目标 MC / 加载器 | 本分支：Minecraft `26.1.2`、NeoForge `26.1.2.10-beta`、Fabric Loader `0.19.3`、Fabric API `0.154.2+26.1.2`（`build.gradle.kts:12-16`）。注意 `neoforge.mods.toml` 里的 `versionRange` 仍是 `[1.21.3,)` / `[21.3.9-beta,)`，未随版本更新 |
| Java | toolchain 25（`build.gradle.kts:47`、`neoforge/build.gradle.kts` 末行） |
| Gradle 插件 | Fabric Loom `1.15.4`（common+fabric）、`net.neoforged.moddev 2.0.140`（neoforge）、`com.github.gmazzo.buildconfig 5.3.5`（common，生成 `BuildConfig`） |
| 许可证 | LGPL-3.0-only |
| 模块结构 | `include("common","fabric","neoforge")`（`settings.gradle.kts`） |
| 编译依赖（重点） | **Sodium 是硬依赖**：fabric `net.caffeinemc:sodium-fabric:0.9.2+mc26.1.2` / neo `sodium-neoforge-mod`；声明 embeddium 为 incompatible。`compileOnly("io.github.douira:glsl-transformer:3.0.0-pre3")`、`org.anarres:jcpp:1.4.14`、`org.antlr:antlr4-runtime:4.13.1`（fabric 端 `include` 内嵌这三个库）、`compileOnly(files("DHApi.jar"))`（Distant Horizons）。common 还用 fabric-api 的 `fabric-resource-loader/block-getter/renderer-api` 作为 compileOnly |

## 2. 源码规模与包结构

实测（`find -name '*.java'` + `wc -l`）：

- 总计 **744 个 .java / 62,547 行**；common 723 文件 61,918 行、fabric 4 文件 151 行、neoforge 17 文件 478 行。
- 额外 source set：`common/src/api`（8 文件，对外开放 API）、`common/src/headers`（7 文件，ModMenu / Distant Horizons 编译期 stub）、`common/src/vendored`（kroppeb `stareval` 表达式引擎 + `de/odysseus/ithaka` 有向图库）、`common/src/desktop`（1 文件 `LaunchWarn`）、`common/src/disabledTest`（11 文件，集成测试，默认不编译）。
- 第 3 层包文件数：`mixin` 142、`shaderpack` 86、`gl` 84、`pipeline` 52、`compat` 37、`uniforms` 36、`gui` 30、`vertices` 29、`pbr` 28、`shadows` 16、`mixinterface` 16、`targets` 13、`layer` 10、`pathways` 9、`parsing` 9。第 4 层热点：`mixin/entity_render_context` 24、`compat/sodium/mixin` 22、`gl/uniform` 21、`pipeline/programs` 15、`shaderpack/option` 14、`pipeline/transform/transformer` 14、`gl/texture` 14、`uniforms/custom/cached` 12。
- 最大文件：`pipeline/IrisRenderingPipeline.java` 1394、`parsing/IrisFunctions.java` 1212、`shaderpack/properties/ShaderProperties.java` 997、`gl/IrisRenderSystem.java` 862、`Iris.java` 814、`shadows/ShadowRenderer.java` 806、`pipeline/transform/transformer/CompatibilityTransformer.java` 751、`gui/screen/ShaderPackScreen.java` 689、`shaderpack/ShaderPack.java` 631、`shaderpack/option/OptionAnnotatedSource.java` 566。

## 3. 入口与注册

common 模块**没有任何 @Mod/@ModInitializer**，生命周期全靠 mixin 钩原生类（这也是它能同时支持两加载器且 fabric 端只写 4 个类的原因）：

- `mixin/MixinOptions_Entrypoint.java:24` → `new Iris().onEarlyInitialize()`（读版本、注册按键、`DHCompat.run()`、初始化配置与 UpdateChecker，`Iris.java:780-813`）
- `mixin/MixinRenderSystem.java:27-31` → `RenderSystem.initRenderer` RETURN 里依次 `Iris.duringRenderSystemInit()` / `GLDebug.reloadDebugState()` / `IrisRenderSystem.initRenderer()` / `IrisSamplers.initRenderer()` / `Iris.onRenderSystemInit()`
- `mixin/MixinTitleScreen.java:25` → `Iris.onLoadingComplete()`；`mixin/MixinMinecraft_Keybinds.java:22,26` → `tick()V` RETURN 里 `Iris.handleKeybinds()`

加载器侧极薄：`neoforge/.../platform/IrisForgeMod.java:18-33` 用 `@Mod(value="iris", dist=Dist.CLIENT)` 构造注入 `IEventBus`/`ModContainer`，做三件事——注册按键（延迟到 `RegisterKeyMappingsEvent`，先在 `IrisForgeMod.KEYLIST` 攒着）、`registerExtensionPoint(IConfigScreenFactory.class, ...)` 挂配置界面、调 `IrisApi.getInstance().assignPipeline(...)`。fabric 端只有 4 个类：`ModMenuIntegration`、两个 mixin、`IrisFabricHelpers`。

**没有 DeferredRegister / Registrate**：这是纯客户端渲染 mod，不注册方块物品。"注册"体现为两条表：

1. `pipeline/IrisPipelines.java:19-24` 两个静态 `Map<RenderPipeline, Function<IrisRenderingPipeline, ShaderKey>>`（coreShaderMap / coreShaderMapShadow），把 60+ 个原版 `RenderPipelines.SOLID_BLOCK`… 映到 Iris 的 `ShaderKey`；
2. `pipeline/programs/ShaderKey.java:18+` 枚举，每项携带 `(ProgramId, AlphaTest, VertexFormat, FogMode, LightingModel)` 五元组，例如 `TERRAIN_CUTOUT(ProgramId.TerrainCutout, AlphaTests.HALF_ALPHA, IrisVertexFormats.TERRAIN, FogMode.PER_VERTEX, LightingModel.LIGHTMAP)`。

平台差异收敛到一个接口：`platform/IrisPlatformHelpers.java:14-40`（`INSTANCE = ServiceLoader.load(...)`），neoforge/fabric 各在 `META-INF/services/net.irisshaders.iris.platform.IrisPlatformHelpers` 声明实现类。

## 4. 核心系统

**(1) 光影包加载（`shaderpack/`）** — 职责：把 zip/目录形式的 OptiFine 光影包解析成 `ProgramSet`。
- `include/IncludeGraph.java:22+` 用**有向图**建模：节点=文件，边=`#include`；好处是一次性读盘、正确处理循环 include、支持增量变换。
- `option/ShaderPackOptions.java:23-52` 按 `graph.computeWeaklyConnectedComponents()` 分组做选项发现与合并（`OptionAnnotatedSource` 从源码注释里提取 `#define` 选项注解）。
- 预处理链：`preprocessor/JcppProcessor.java:12+` 用 jcpp 做 GLSL 预处理，为兼容 Mesa 会把 `#version`/`#extension` 先替换成 marker 再统一 hoist；`IrisDefines.java:25+` 注入 `MC_VERSION`、`BIOME_*`、`CAT_*`、`PPT_*` 等标准宏。
- `ShaderPack.java:120-` 构造函数一次读完所有磁盘 IO（注释明确"退出构造函数后无需再持有路径"）。

**(2) 着色器变换（`pipeline/transform/`，注释称 "triforce 2"）** — 职责：把光影包 GLSL 改写成 MC 现代渲染管线能吃的形式。
- `TransformPatcher.java:60-85` 基于 `glsl-transformer` 的 ASTTransformer；`useCache=true` + `LRUCache<>(400)`，缓存 key = 源码字符串 + 参数对象，**要求 Parameters 全部实现 equals 且使用后不可变**。
- `Patch` 枚举 6 种（`VANILLA/DH_TERRAIN/DH_GENERIC/SODIUM/COMPOSITE/COMPUTE`），`transformer/` 下 14 个 Transformer 按 Patch 分发；`parseTokenFilter` 会对残留的未解析预处理指令直接抛异常（快速失败）。

**(3) 渲染管线（`pipeline/` + `targets/`）** — `WorldRenderingPipeline` 接口（大量 `shouldRenderXxx()` 开关）由 `IrisRenderingPipeline`（`:128-179` 字段：renderTargets / shaderMap / customUniforms / shadowRenderer / 多个 `flipped...` 集合）实现，`VanillaRenderingPipeline` 作为关闭光影时的实现。`PipelineManager.java:18-30` 按维度缓存 pipeline，切换维度才重建，重建会 reset `SystemTimeUniforms.COUNTER`。

**(4) 阴影（`shadows/`）** — `ShadowRenderer.ACTIVE` 静态标志 + `ShadowRenderingState.areShadowsCurrentlyBeingRendered()`；剔除策略可插拔：`frustum/advanced/AdvancedShadowCullingFrustum`、`SafeZoneCullingFrustum`、`frustum/fallback/BoxCullingFrustum`、`NonCullingFrustum`，由 `FrustumHolder` 选择；`ShadowRenderTargets` 管理多张深度图（硬件过滤 / mipmap / `DepthCopyStrategy`）。

**(5) Uniform 体系（`uniforms/`）** — 硬编码 uniform 按主题拆成 `CommonUniforms`/`MatrixUniforms`/`BiomeUniforms`/`SystemTimeUniforms`/`FrameUpdateNotifier` 等 19 个类；**自定义 uniform（shader 内 `uniform.xxx = 表达式`）** 是最有学习价值的部分：`parsing/IrisFunctions.java:74-78` 自建函数解析器（sin/clamp/smooth/if/between…），`uniforms/custom/CustomUniforms.java:43-51` 用 vendored 的 stareval `ExpressionResolver` 编译表达式，`:92-174` 做依赖图拓扑排序，**任何解析失败或依赖损坏的 uniform 会被打成 broken 并沿依赖边传播**，最后只把可用的按序注册，绝不因单个表达式崩掉整个包。

**(6) 顶点格式扩展与 Sodium 兼容（`vertices/` + `compat/`）** — `IrisVertexFormats` 定义 TERRAIN/ENTITY/GLYPH/CLOUDS 扩展格式，`Iris.java:141-144` 向 Sodium 的 `VertexSerializerRegistry` 注册 4 个序列化器做格式互转；`compat/sodium/mixin` 22 个 mixin 改 Sodium 的区块构建/区块渲染，`compat/dh` 7 个类接 Distant Horizons。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自定义包**。`grep Packet` 只命中 `mixin/MixinClientPacketListener.java`（`handleLogin` TAIL 里发聊天栏提示更新与光影编译错误）；`UpdateChecker` 用 `java.net.URL` 拉远端 JSON 做更新检查。**未见任何自定义 payload/通道**。
- **数据驱动（这是 Iris 的重头）**：光影包侧全部是 OptiFine 格式数据文件——`shaders.properties`（`ShaderProperties.java:57-108`：profiles、subScreenOptions、alphaTest/viewport/textureScale/blendMode 覆盖、customTextures、bufferObjects、几十个 `OptionalBoolean` 显隐开关）、`block.properties`/`item.properties`/`entities.properties`（`IdMap.java:43+`，含 tag 与 legacy id 映射）、`lang/*.lang`（`LanguageMap.java:20+`，含 en_US→en_us 文件名兼容）；Iris 侧 `iris.properties`（`java.util.Properties`，ISO-8859-1）+ `iris-excluded.json`（`IrisConfig.java:143-212`），每个光影包一个同名 `.txt` 存被改过的选项（`Iris.java:329-351`，空则删文件）。
- **配置集成**：`compat/sodium/config/IrisConfig.java` 实现 Sodium 的 `ConfigEntryPoint`，用 builder 风格链式注册自己的配置页，并用 `registerOptionOverlay` 覆盖 Sodium 原有选项（开光影时禁用 RGSS/改进透明）；fabric 端用 `ModMenuIntegration` 提供 ModMenu 入口。
- **datagen：无**（无 `runData`/`DataGenerator` 相关代码）。

## 6. Mixin

配置集中在 `common/src/main/resources/`（本机副本缺失，路径来自 git）：`mixins.iris.json`（约 140 个条目，package `net.irisshaders.iris.mixin`，`plugin: net.irisshaders.iris.mixin.IrisMixinPlugin`，`refmap: iris.refmap.json`，`injectors.maxShiftBy=2`）、`mixins.iris.vertexformat.json`、`mixins.iris.compat.sodium.json`、`mixins.iris.compat.dh.json`、`mixins.iris.bettermipmaps.json`（空列表占位）、`mixins.iris.fantastic/devenvironment/integrationtest/fixes.maxfpscrash.json`；另有 `fabric/src/main/resources/mixins.iris.fabric.json`、`neoforge/src/main/resources/mixins.iris.forge.json`。neoforge 在 `neoforge.mods.toml` 用 `[[mixins]] config=` 列出 5 个；fabric 在 `fabric.mod.json` 的 `mixins` 数组列 7 个。

规模：**180 个类带 `@Mixin`，286 处注入注解**。代表性 hook：

- `mixin/MixinLevelRenderer.java:121` `renderLevel` HEAD 初始化管线；`:153` 注入 `FramePass.executes` 之后 `iris$beginLevelRender`；`:192` `@WrapOperation` 包 `cullTerrain` 以插入阴影渲染；`:237` 包 `ChunkSectionsToRender.renderGroup` 做层级切换
- `mixin/MixinGameRenderer.java:50/58/66/75`：`render` HEAD、`<init>` TAIL、`@ModifyArgs` 改 `GlobalSettingsUniform.update` 参数、`@Redirect` 改 `renderHandsWithItems`
- `mixin/MixinGlStateManager.java:11` `@ModifyConstant(method="<clinit>", constant=@Constant(intValue=12))`
- `mixin/MixinRenderSystem.java:26` `initRenderer` RETURN（`remap=false`）
- Accessor 与接口注入并用：`LevelRendererAccessor`/`GameRendererAccessor`/`GlStateManagerAccessor` 等 16 个 `mixinterface` 接口，通过 fabric `loom:injected_interfaces` 与 neoforge `interface_injections.json`（6 个目标：RenderTarget/GpuTexture/RenderPass/RenderType/ItemInHandRenderer）注入，避免到处 cast。`iris.accesswidener`（34 条条目）打开 `GlStateManager$BooleanState.enabled`、`PoseStack$Pose.trustedNormals`、`GlProgram.uniformsByName` 等内部字段。

## 7. 值得学的 5 条具体做法

1. **用 `ServiceLoader` 抽象加载器差异**：common 只依赖接口 `IrisPlatformHelpers`（`platform/IrisPlatformHelpers.java:15`），两个加载器各写一个实现 + `META-INF/services` 文件，common 代码零加载器 API 引用——多加载器库/附属的标准做法。
2. **把昂贵变换做成带 equals 缓存的纯函数**：`pipeline/transform/TransformPatcher.java:84` `useCache=true` + `LRUCache<>(400)`，key 是"源码字符串 + 参数对象"，并要求参数不可变；换到 NeoForge 上处理资源/模型/配方加载时同样适用。
3. **用图结构做资源加载与选项合并**：`shaderpack/include/IncludeGraph.java` + `option/ShaderPackOptions.java:23-52` 按弱连通分量分组——一次 IO、天然处理循环 include，比递归 include 稳得多。
4. **失败隔离而非全局崩溃**：`uniforms/custom/CustomUniforms.java:92-174` 的 broken-uniform 集合 + 依赖传播；`Iris.java:643-664` `createPipeline` 捕获异常后回退 `VanillaRenderingPipeline`（渲染类 mod 必须保证"最差也能进游戏"）。
5. **GL 状态与生命周期收敛到少数切面**：`gl/state` + `statelisteners` + `MixinGlStateManager_{BlendOverride,DepthColorOverride,FramebufferBinding}` 几个专用 mixin 分别负责一类状态覆盖，避免散落各处的状态读写。
6. **补充：仓库自带的工程规范文档**（`docs/development/recommendations.md`、`release-checklist.md`）与 `common/src/disabledTest` 下 11 个真实光影包集成测试，说明它把"回归测试素材"也纳入仓库。

## 8. 公开 API 与外部接入（Iris 是加载器/前置型 mod）

- **API 包路径**：`net.irisshaders.iris.api.v0`，物理位置在独立 source set `common/src/api/java/`，由 `common/build.gradle.kts` 打成 `apiJar`（classifier `api`），另有 `headersJar`（编译期 stub 依赖）、`vendoredJar`。
- **入口**：`IrisApi.getInstance()`；接口本身不引用实现——`api/v0/IrisApiInternal.java:8` 用 `Class.forName("net.irisshaders.iris.apiimpl.IrisApiV0Impl").getField("INSTANCE")` 反射绑定，实现见 `apiimpl/IrisApiV0Impl.java`（`getMinorApiRevision()` 返回 4）。
- **扩展点接口**：`IrisApi`（`isShaderPackInUse()`、`isRenderingShadowPass()`、`openMainIrisScreenObj()`、`createTextVertexSink()`、`getSunPathRotation()`、`assignPipeline(RenderPipeline, IrisProgram)`、`assignPipelineShadow(RenderPipeline, IrisShadowProgram)`、`registerShadowRenderCallback(IrisShadowRenderCallback)`）、`IrisApiConfig`、`IrisProgram`/`IrisShadowProgram`（程序键枚举）、`IrisTextVertexSink`、`item/IrisItemLightProvider`（方块/物品自定义光源，泛型接 `@Nullable Object` 以免引 MC 类）。
- **接入方式**：外部 mod 编译期依赖 apiJar（jitpack 发布 `publishToMavenLocal`，见 `jitpack.yml`），运行时 `IrisApi.getInstance()`；Sodium 用 `ConfigEntryPoint`、ModMenu 用 `ModMenuApi`（`common/src/headers` 里放了这些接口的编译期 stub，避免硬依赖）；Distant Horizons 通过 `headers` 里的 `IDhApiShadowCullingFrustum` 等接口对接；渲染管线级接入是 `assignPipeline`（Iris 自己在 `IrisForgeMod.java:25-27` 就这么用）。

### 未确认项

- common 与 neoforge 的 `@Mixin` 目标方法名大量使用 `MojLambdas`/`NeoLambdas` 常量类混合，未逐一核对全部 286 处注入点的目标方法。
- 工作副本缺失全部 json/lang/shaderpack 资源，无法核对 `fabric.mod.json` 之外的资源清单与 `mixins.iris.devenvironment/fantastic` 的完整内容（仅确认文件存在于 git 索引）。
