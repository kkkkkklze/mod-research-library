# Asek3/Oculus 源码分析

## 1. 基本信息
- Mod 名：Oculus；`mod_id=oculus`（`src/main/java/net/coderbot/iris/Iris.java:69`，`MODNAME="Oculus"` 同文件 76 行）；作者 coderbot, IMS212, Justsnoopy30, FoundationGames（`src/main/resources/META-INF/mods.toml`）；维护者 Asek3。
- 目标：MC 1.16.5 + **Forge 36.2.29**（`gradle.properties`），`modLoader="javafml"`, `loaderVersion="[36,)"`；Java 8。
- Gradle：`dev.architectury.loom` 0.10.0-SNAPSHOT（`loom.platform=forge`）+ shadow 7.1.2，`loom.officialMojangMappings()`；子工程 `glsl-relocated`（`settings.gradle`）。
- 许可证：LGPL-3.0-only。
- 编译依赖：`modCompileOnly maven.modrinth:rubidium:0.2.13`（即 Sodium 的 Forge 分支）、`curse.maven:epic-fight-mod`；shadow 内嵌 `org.anarres:jcpp`、`org.slf4j`，并 relocate 为 `oculus.*`（`build.gradle:74-83`）。

## 2. 规模与包结构
- 613 个 `.java`、184766 行（含 69 个 vendored JOML）；剔除 vendored 后约 21735 行。
- 包（文件数）：`net/coderbot/iris` 523、`net/coderbot/batchedentityrendering` 36、`de/odysseus/ithaka` 22（贴图拼合）、`kroppeb/stareval` 28（表达式求值器）、`net/irisshaders/iris` 4（对外 API）。
- iris 内部：`vendored/joml` 69、`compat/sodium` 58、`shaderpack/option` 26、`gl/uniform` 20、`mixin` 90。
- 最大文件（非 vendored）：`pipeline/DeferredWorldRenderingPipeline.java` 1309、`Iris.java` 706、`pipeline/ShadowRenderer.java` 678、`shaderpack/ShaderProperties.java` 629、`shaderpack/ShaderPack.java` 509。

## 3. 入口与注册
主类 `net.coderbot.iris.Iris`（`@Mod(Iris.MODID)`）。**没有 DeferredRegister/Registrate**（纯客户端渲染 mod，无内容注册）：
```java
FMLJavaModLoadingContext.get().getModEventBus().addListener(this::onInitializeClient);
MinecraftForge.EVENT_BUS.addListener(this::onKeyInput);
ModLoadingContext.get().registerExtensionPoint(ExtensionPoint.DISPLAYTEST,
    () -> Pair.of(() -> FMLNetworkConstants.IGNORESERVERONLY, (a, b) -> true)); // Iris.java:105-112
```
按键在 `onEarlyInitialize()` 构造、`FMLClientSetupEvent` 里 `ClientRegistry.registerKeyBinding` 注册（`Iris.java:142-154`）。

## 4. 核心系统
1. **Shaderpack 加载**：`shaderpack/ShaderPack.java`、`ProgramSet.java`、`shaderpack/loading/*`；zip 包用 `FileSystems.newFileSystem` 挂载并缓存 `zipFileSystem`（`Iris.java:373-398`、`582-599`），重载时必须 close 否则报 FileSystemAlreadyExists。
2. **渲染管线**：`pipeline/PipelineManager.java` 用 `Map<NamespacedId, WorldRenderingPipeline>` 按维度缓存，工厂函数由主类注入（`Iris.java:638`）；`destroyPipeline()` 后必须立刻重建，并 `resetTextureState()` 解绑 16 个纹理单元（`PipelineManager.java:87-116`）。创建失败回退到 `FixedFunctionWorldRenderingPipeline`（`Iris.java:616-633`）。
3. **GL 状态跟踪**：`gl/IrisRenderSystem.java`(534 行) + `gl/blending`、`gl/state` + `mixin/state_tracking`、`mixin/statelisteners`，通过 mixin 拦截 `GlStateManager` 记录混合/深度状态。
4. **顶点格式扩展**：`vertices/*` + `api/v0/IrisTextVertexSink`；Sodium 侧在 `compat/sodium/impl/vertex_format/{terrain_xhfp,entity_xhfp}`、`IrisChunkMeshAttributes`。
5. **Rubidium(Sodium) 兼容层**：`compat/sodium` 58 文件，分 `impl/`（实现）与 `mixin/`（注入）两半；`IrisSodiumCompatMixinPlugin.shouldApplyMixin()` 直接返回 `isRubidiumLoaded`，一处开关全部 sodium mixin（同文件 22-34 行）。
6. **PBR 贴图**：`texture/pbr` 12 文件，`PBRTextureManager.INSTANCE.init()`（`Iris.java:172`）。

## 5. 网络 / 数据驱动 / 配置
- 网络：无自建包（无 SimpleChannel/PacketHandler）。
- 配置：`config/IrisConfig.java` 用 `Properties` 写 `config/oculus.properties`（`shaderPack`/`enableShaders`/`enableDebugOptions`/`maxShadowRenderDistance`/`colorSpace`）。
- Shaderpack 选项：靠解析 shader 源码注释（`shaderpack/option/OptionAnnotatedSource.java`）+ stareval 表达式生成 UI 项，结果存到 `shaderpacks/<pack>.txt`（`Iris.java:335-357`）。
- datagen：无。

## 6. Mixin
- 9 个 config 在 `build.gradle:11-21` 的 `loom.forge.mixinConfigs` 声明（loom 写进 manifest，替代 fabric.mod.json）；`mixin.defaultRefmapName="oculus-mixins-refmap.json"`。
- 注意：本仓库快照中 `src/main/resources/mixins.oculus*.json` 与 `assets/` 未落盘（只有 `oculus-batched-entity-rendering.mixins.json`），可用 `git show HEAD:src/main/resources/mixins.oculus.json` 取。
- `mixins.oculus.json`：package `net.coderbot.iris.mixin`，约 66 个 client mixin，按功能分子包（texture/rendertype/shadows/sky/fabulous/state_tracking/gui/math/…），`injectors.maxShiftBy=2`。
- `mixins.oculus.compat.sodium.json`：带 `plugin` 与 `overwrites.conformVisibility=true`；`mixins.oculus.compat.json` 用 `CompatMixinPlugin` 条件加载 epicfight/pixelmon 兼容。
- AT：`src/main/resources/META-INF/accesstransformer.cfg` 22 行，用 **SRG 名**（如 `WorldRenderer field_228415_m_`）开放私有字段，无需 mixin accessor 的场景优先走 AT。

## 7. 值得学的做法
1. **移植只碰边界**：613 个文件里只有 10 个 `import net.minecraftforge.*`（实测 grep），Forge 接入集中主类 + AT + mixin config，其余业务代码平台中立——移植成本最低的形态。
2. **用 mixin config plugin 做条件兼容**：`IrisSodiumCompatMixinPlugin`（`compat/sodium/mixin/IrisSodiumCompatMixinPlugin.java:19-34`）在 `onLoad` 判断 `rubidium` 是否存在，`shouldApplyMixin` 统一开关；适用于"可选前置 mod"场景。
3. **子工程产出 bundledJar 配置**：`glsl-relocated/build.gradle` 定义 `bundledJar` configuration，主工程 `implementation(shadow(project(path:":glsl-relocated", configuration:"bundledJar")))`，把 glsl-transformer+antlr 单独隔离再整体内嵌 relocation。
4. **失败可降级**：shaderpack 加载失败/管线创建异常都回退到固定管线并置 `fallback`，配合玩家聊天栏提示（`Iris.java:204-225`、`267-271`）。
5. **防误用主类**：shadowJar 的 `Main-Class = LaunchWarn`，用户把 mod jar 当 Forge 安装器运行时弹窗引导到官网（`Iris.java` 同包的 `LaunchWarn.java:12-43`）。

## 8. 对外 API
`net.irisshaders.iris.api.v0`：`IrisApi`（静态 `getInstance()`）、`IrisApiConfig`、`IrisTextVertexSink`、`item/IrisItemLightProvider`；实现 `net.coderbot.iris.apiimpl.IrisApiV0Impl`（`getMinorApiRevision()=1`，`isShaderPackInUse()` 用"管线不是 FixedFunction 实例"判断）。外部 mod 用反射/方法句柄调用（例：Embeddium 的 `impl/render/ShaderModBridge.java` 即如此），属"零编译依赖"接入风格。
