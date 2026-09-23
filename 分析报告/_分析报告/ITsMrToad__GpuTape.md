# ITsMrToad/GpuTape（GPUBooster）源码分析报告

## 1. 基本信息
- Mod 名：GPUBooster（仓库名 GpuTape；README 说明 1.21.10 起 GpuTape 被 GPUBooster 取代）；`archives_base_name=GPUBooster`；mod_id：`gpu_booster`（`client/GPUBooster.java:26`）；作者：Mr.Toad（ITsMrToad）
- 目标 MC 与加载器：Minecraft 1.21.1 + Fabric（`gradle.properties`: `minecraft_version=1.21.1`、`yarn_mappings=1.21.1+build.3`、`loader_version=0.16.2`、`fabric_version=0.102.1+1.21.1`）；Java 21（`build.gradle: tasks.withType(JavaCompile).options.release = 21`）
- Gradle 插件：`fabric-loom` 1.8-SNAPSHOT（`build.gradle:2`）；`loom { mixin.defaultRefmapName = "gb.refmap.json" }`
- 许可证：**未在仓库快照中发现 LICENSE 文件**（`build.gradle` 的 `jar { from("LICENSE") }` 引用了它，来源未确认）
- 编译依赖：`fabric-api` 0.102.1、`modmenu` 11.0.3、`maven.modrinth:vulkanmod:${project.vulkan}`（**`gradle.properties` 中不存在 `vulkan` 键，该行按现状无法解析，未确认**）、`maven.modrinth:toadlib:1.3.7-1.21-1.21.1-fabric`（modApi；配置系统 `ToadConfigs`/`ToadConfig`/`BoolEntry`/`EnumEntry`/`ShortEntry`/`DeprecationRule`/`PerformanceImpact` 全部来自它）
- 版本：`mod_version=1.1.0`；资源只有 `gb.mixins.json`、`gb.tgl.mixins.json`（**无 `fabric.mod.json`，未见 datagen/资产目录**）

## 2. 源码规模与包结构
- `.java` 29 个，共 1958 行
- 包（第 3 层）：`com.mr_toad.gpu_booster.api`（GBGL、IntArrayDeque、VertexFormatCacheAPI，3 个）、`.client`（GPUBooster，1）、`.client.config`（GBConfig、DSAMode，2）、`.client.mixin.dsa`（4）、`.client.mixin.math`（5）、`.client.mixin.random`（4）、`.client.mixin.tgl`（2）、`.client.rendering.gl`（VAOInstance、VertexFormatCache，2）、`.client.rendering.math`（GBFMath、GBFMatrix3f/4f、TableGaussianGenerator，4）、`.client.resource`（1）、`.modmenu`（1）
- 最大文件：`client/rendering/math/GBFMatrix4f.java` 230、`client/mixin/dsa/FramebufferMixin.java` 177、`api/GBGL.java` 167、`client/mixin/dsa/WindowFramebufferMixin.java` 133、`client/mixin/math/ShaderProgramMixin.java` 104、`client/mixin/dsa/VertexBufferMixin.java` 100、`client/rendering/math/GBFMatrix3f.java` 97、`client/rendering/math/GBFMath.java` 83、`client/rendering/gl/VertexFormatCache.java` 81
- **快照不完整（事实性观察）**：`api/GBGL.java:14`、`api/VertexFormatCacheAPI.java:5`、`client/resource/UnregisteredIdsResourceSupplier.java:4` 均 `import com.mr_toad.gpu_booster.client.rendering.gl.VertexBufferCache`，但仓库中不存在该文件；两个 mixin json 的 `package` 为 `com.mr_toad.gpu_booster.core.mixin(.tgl)`，而源码实际包为 `com.mr_toad.gpu_booster.client.mixin(.tgl)`——快照与可编译状态不一致

## 3. 入口与注册
- 入口 `src/main/java/com/mr_toad/gpu_booster/client/GPUBooster.java:29`：`public class GPUBooster implements ClientModInitializer`（fabric.mod.json 缺失，entrypoint 声明未确认）
- `onInitializeClient()`（`:37-53`）在 `RenderSystem.recordRenderCall` 内查询 `GL.getCapabilities()`，写入三个静态能力标志 `GL45`、`DSA = caps.GL_ARB_direct_state_access || GL45`、`BUFFER_STORAGE = caps.GL_ARB_buffer_storage || GL45`；随后 `ToadConfigs.create(MODID, CONFIG)`、`System.setProperty("joml.fastmath", CONFIG.fastMath.get().toString())`、`ResourceManagerHelper.get(ResourceType.CLIENT_RESOURCES).registerReloadListener(UNREGISTERED_IDS)`、按开关 `VertexFormatCacheAPI.addCacheableFormats(POSITION_COLOR_TEXTURE_LIGHT_NORMAL, POSITION_COLOR_TEXTURE_OVERLAY_LIGHT_NORMAL)`
- 无 DeferredRegister/Registrate（Fabric 纯客户端性能 mod，无游戏对象注册）

## 4. 核心系统
1. **DSA（direct-state access）兼容层**（`api/GBGL.java`）：把 GL4.5 DSA 调用集中成静态工具（`createVAO→GL45.glCreateVertexArrays`、`addVAO2VBO→glVertexArrayVertexBuffer`、`vaoFormat→glVertexArrayAttribFormat/AttribIFormat`、`makeFBO→glCreateFramebuffers`、`textureStorage`、`createRBO/storageNamedRBO/framebufferNamedRBO`），每个方法前 `RenderSystem.assertOnRenderThread()`；`ThreadLocal<VertexFormat> CURRENT` 让"当前 BufferBuilder 的格式"在 UI/渲染线程上下文中传递（`GBGL.java:29,32-38`）
2. **VBO/EBO 池 + VAO↔VertexFormat 缓存**（`client/rendering/gl/VertexFormatCache.java`）：`Object2ObjectOpenHashMap<VertexFormat, VAOInstance> VAOS` + 两个 `IntArrayDeque` 池（容量取 `CONFIG.renderCyclePoolSize`，默认 256，范围 128–432）+ `IntArrayList UNREGISTERED_IDS`；`getVBO/getEBO` 池空时新建并登记，`clean(vao, vbo, ebo)` 解绑后归还池；`preGen()` 在初始化阶段预热池。`api/IntArrayDeque.java` 是自写 int 环形队列（`pool()` 返回 `OptionalInt`、`ensureCapacity` 扩容），避免 `ArrayDeque<Integer>` 装箱
3. **RBO depth 替代 depth texture**（`client/mixin/dsa/FramebufferMixin.java:45`）：`@Inject(method="initFbo", at=HEAD, cancellable=true)` 整段重写 FBO 初始化；`CONFIG.canCreateRenderbuffer()`（需 `GL45` 且未装 iris）时走 `createRBO/storageNamedRBO`（DSA）或 `genRBO/bindRBO/storageRBO`，否则退回 `GL_DEPTH_COMPONENT24` 纹理；同文件 `@Shadow` 了 `fbo/viewportWidth/depthAttachment/colorAttachment/texFilter` 等字段。`WindowFramebufferMixin` 另注入 `init(HEAD,cancellable)` 与两处 `@Redirect(findSuitableSize)` 改写 `TextureUtil.generateTextureId()`
4. **VBO/EBO 走 DSA 的顶点缓冲替换**（`client/mixin/dsa/VertexBufferMixin.java:37-...`）：构造 TAIL 里把 `vertexBufferId/indexBufferId/vertexArrayId` 换成 `VertexBufferCache.getVBO/getEBO` + `GBGL.getVAO()`；再用两个 `@Redirect` 把 `VertexBuffer.uploadVertexBuffer/uploadIndexBuffer` 换成 named 版本 `uploadNamedVBO/uploadNamedEBO`；`BufferBuilderMixin` 在构造 TAIL 设置 `GBGL.CURRENT.set(format)`
5. **fast math 体系**（`client/rendering/math/`）：`GBFMath` 含 Quake 魔数快速平方根倒数（`MAGIC = 0x5F3759DF` + 两次牛顿迭代，`GBFMath.java:11,26-31`）与 `EXP_LUT`（2048 项、scale 256 的 exp 查表）；`GBFMatrix4f/GBFMatrix3f` 继承 JOML 矩阵，用 `MathHelper.cos/sin` + `applyRotation` 覆写 `rotateX/Y/Z`；`TableGaussianGenerator` 是 Ziggurat 表法 `GaussianGenerator`（`TABLE_SIZE=256`、`R=3.442619855899F`，静态初始化 X[]/Y[]）
6. **fast random**：4 个 mixin 用同一手法在构造 TAIL 替换高斯生成器——`@Mutable @Shadow @Final private GaussianGenerator gaussianGenerator;`（`mixin/random/CheckedRandomMixin.java:19-21` 等），`Xoroshiro128PlusPlusRandomMixin` 覆盖其 4 个构造签名
7. **配置与配置界面**：`GBConfig extends ToadConfig`（`client/config/GBConfig.java:24`）注册 `renderbuffer_depth`/`fast_math`/`fast_random`/`dsa`(枚举)/`vertex_format_cache`/`render_cycle_pool_size`，每项带 `withPerformanceImpact(PerformanceImpact.*)`、`withWarning(HighlightWarning.WORLD_RELOAD|GAME_RELOAD)`、`addDeprecationRule(...)`；`DeprecationRule` 用 lambda 实时判定（如 `!GPUBooster.BUFFER_STORAGE`、`isModLoaded("iris")`、`MinecraftClient.getInstance().world != null`）并附 tooltip；`hasDSA(DSAMode)` 额外要求图形模式低于 `FABULOUS`。ModMenu 入口 `modmenu/GPUBoosterModMenu.java` 返回 `ToadConfigScreen`

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无（纯客户端；无 payload/包注册）
- 数据驱动：无内置数据文件；只用了一个恒为空的 `SinglePreparationResourceReloader<Void>`（`client/resource/UnregisteredIdsResourceSupplier.java`，`getFabricId = gpu_booster:unregistered_ids`）在 `apply` 里调 `VertexBufferCache.deleteUnregistered()`，借资源重载时机回收脱离池的 GL buffer id
- 配置：ToadLib 的 `ToadConfig` 框架（`ToadConfigs.create(MODID, CONFIG)`），开关由 `System.setProperty("joml.fastmath", …)` 影响 JOML 全局行为；`DSAMode` 用 `StringIdentifiable.createCodec` 提供 Codec
- datagen：无

## 6. Mixin
- 配置：`src/main/resources/gb.mixins.json`（`package: com.mr_toad.gpu_booster.core.mixin`，`compatibilityLevel: JAVA_21`，`refmap: gb.refmap.json`，`defaultRequire: 1`；mixins 6 个 math/random，client 7 个 dsa/math）；`src/main/resources/gb.tgl.mixins.json` 带 `plugin: com.mr_toad.gpu_booster.client.mixin.tgl.TGLMixinPlugin`
- `TGLMixinPlugin implements IMixinConfigPlugin` 的 `shouldApplyMixin` 用 `Class.forName("lol.richy.threatengl.ThreatenGL")` 判断：装了 ThreatenGL 就**不**应用 `WindowMixin`（`mixin/tgl/TGLMixinPlugin.java:19-27`）
- 代表 hook 目标：`Framebuffer#initFbo`(HEAD cancellable)、`WindowFramebuffer#init/findSuitableSize/supportsColor/supportsDepth`、`VertexBuffer#<init>/upload`(两个 @Redirect)、`BufferBuilder#<init>`、`BufferRenderer#drawWithGlobalProgramInternal`（@Redirect `RenderSystem.getModelViewMatrix/getProjectionMatrix`）、`ShaderProgram`（`@Shadow @Final GlUniform modelViewMat/projectionMat/...`）、`MatrixStack$Entry#<init>(Matrix4f,Matrix3f)`、`MathHelper#floorMod(II|FF|DD)/ceilLog2/floorLog2`、`GivensPair#normalize/fromAngle`、`Window#<init>`（`@Redirect GLFW.glfwWindowHint`，`priority=1001`）

## 7. 值得学的 5 条具体做法
1. **把 capability 检测做成静态三标志 + 配置前置守卫**：`GL45/DSA/BUFFER_STORAGE` 在 `RenderSystem.recordRenderCall` 里初始化，`GBConfig.hasDSA(target)` 再叠加图形模式条件（`GPUBooster.java:39-46`、`GBConfig.java:57-59`），适用于任何"按硬件能力分级启用优化路径"的 mod
2. **自写 int 环形队列代替装箱集合**：`api/IntArrayDeque.java` 只支持 int 且 `pool()` 返回 `OptionalInt`，适合高频分配的 GL/VBO id 池
3. **"VAO ↔ 顶点格式"缓存复用**：`VertexFormatCache.VAOS` + `VAOInstance.setupFormat()` 用 `format.getElements()/getOffset()` 反射式绑定属性（`VertexFormatCache.java:49-63`、`VAOInstance.java:14-26`）
4. **用 IMixinConfigPlugin 做运行期软兼容判定**：不依赖注解条件，用 `Class.forName` 探测冲突 mod 并返回 `!loaded`（`mixin/tgl/TGLMixinPlugin.java:19-27`）
5. **把 GL 资源回收挂在原版资源重载上**：一个空 `SinglePreparationResourceReloader` 的 `apply` 里回收未登记 buffer id（`client/resource/UnregisteredIdsResourceSupplier.java`），避免自己排程清理

## 8. 公开 API 包与接入方式
- `com.mr_toad.gpu_booster.api`：`GBGL`（DSA/GL 封装，静态方法全部可用但注释自称 "Compat bridge for GL 4.5 with Minecraft and GL <=3"）、`IntArrayDeque`、`VertexFormatCacheAPI`
- 扩展点：`VertexFormatCacheAPI.addCacheableFormat(s)(VertexFormat...)` 允许其他 mod 把自定义 `VertexFormat` 纳入 VAO 缓存（`api/VertexFormatCacheAPI.java:16-22`）；`canBeCached` 要求 `CONFIG.vertexFormatCache` 已开启
- 已知限制（README 声明）：OpenGL < 4.5 时部分功能不可用；RBO 与光影包不兼容；1.21.10 起由 GPUBooster 取代
