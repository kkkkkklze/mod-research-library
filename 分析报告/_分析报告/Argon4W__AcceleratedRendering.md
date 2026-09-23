# Accelerated Rendering 源码分析报告

> 仓库：`源码库\_参考仓库\_bulk\Argon4W__AcceleratedRendering`（浅克隆 + 稀疏检出）。
> 本报告内引用路径：`build.gradle`、`gradle.properties` 等以仓库根为基准；Java 源码以
> `src/main/java/com/github/argon4w/acceleratedrendering/` 为基准（下文简写 `…/`）。
> 上一位执行者读完了源码但未落盘，本文为重跑产物，全部断言基于本次实测工具输出。

## 1. 基本信息

- **mod_id**：`acceleratedrendering`（`gradle.properties` `mod_id` 行）
- **作者**：Argon4W（`gradle.properties` `mod_authors`）；**许可证**：MIT（`gradle.properties` `mod_license`）
- **目标平台**：MC 1.21.1 / NeoForge 21.1.238 / 加载器 javafml（`gradle.properties` `minecraft_version`、`neo_version`；`src/main/resources/META-INF/neoforge.mods.toml:9` `modLoader="javafml"`）。mod 版本 `1.0.15-1.21.1-alpha`（`gradle.properties` `mod_version`）。注意：速览卡片记录的 jar 名是 `…1.0.14-1.20.1-alpha.jar`，与本快照 gradle.properties 的 1.0.15/1.21.1 不一致——卡片采集自旧 release，本仓库源码树只有 1.21.1 一支（本地无 1.20.1 分支，未验证其是否存在）。
- **Gradle 插件与工程结构**：`net.neoforged.gradle.userdev 7.0.189`（`build.gradle:6`），单模块工程（`settings.gradle` 无子项目）；Parchment 映射 1.21.1（`gradle.properties`）；AT 文件经 `minecraft.accessTransformers.file` 挂接（`build.gradle:58`）。
- **Java 版本**：21（`build.gradle:56`；mixin 配置 `compatibilityLevel: JAVA_21`）。
- **定位**：纯客户端实体/方块实体/GUI/文字渲染优化 mod，一句话见 `gradle.properties` mod_description："Fast vertex transform and caching using compute shader."

## 2. 源码规模与包结构

实测（工具：`find`+`wc`）：**355 个 .java、合计 26,255 行**（`find src -name "*.java" -print0 | xargs -0 cat | wc -l`）。速览卡片写 26,610 行，为统计口径差异（卡片按逐文件 `wc -l` 求和，行尾无换行的文件会多计），以本实测为准。

**源码树不完整的证据（稀疏检出）**：`.git/info/sparse-checkout` 白名单只含 `**/*.java`、`*.json`、`*.toml`、`*.md`、`*.cfg` 等，**不含 `*.compute`（GLSL 计算着色器）与 `assets/`**。代码中大量引用的着色器资源（如 `core/programs/ComputeShaderPrograms.java:42` 起的 `shaders/core/transform/block_vertex_transform_shader.compute`，及 `compat/iris/programs/IrisPrograms.java:37-131` 的 15 个 iris 变体）在本检出中全部缺失——第 4 节凡涉及 GLSL 内部逻辑的描述均只依据 Java 侧调度代码，GLSL 本体标注为"未验证"。

主要包及文件数（`src/main/java/…/acceleratedrendering/` 下两级聚合）：

| 包 | 文件数 | 职责速记 |
|---|---|---|
| `core/buffers` | 61 | 加速缓冲源、环形缓冲、buffer builder |
| `features/items` | 47 | 物品/BakedModel 加速 + GUI 合批 |
| `features/text` | 32 | BakedGlyph 文字加速 |
| `core/backends` | 32 | 裸 GL4.6 封装（SSBO、compute program、绑定状态） |
| `compat/iris` | 31 | Iris 光影兼容层 |
| `core/programs` | 30 | 计算着色器加载与 dispatch |
| `core/utils` | 23 | 工具（矩阵/顶点/能力检测） |
| `core/mixins` | 17 | 对原版的注入 |
| `core/meshes` | 16 | 网格缓存/收集器/数据键 |
| `features/modernui` | 11 | ModernUI 文字兼容 |
| `features/filter` | 9 | 黑/白名单过滤 |
| 其余（emf/entities/culling/compat.vanilla/…） | 各 1~7 | |

最大源文件（`wc -l`）：`configs/FeatureConfig.java` 670、`features/items/gui/GuiBatchingController.java` 648、`features/text/mixins/FontMixin.java` 494、`core/buffers/accelerated/builders/AcceleratedBufferBuilder.java` 472、`features/text/cache/ComponentMesh.java` 419、`features/items/mixins/gui/GuiGraphicsMixin.java` 413、`features/text/mixins/StringRenderOutputMixin.java` 409、`features/modernui/mixins/TextLayoutMixin.java` 361、`core/programs/dispatchers/meshes/MeshUploadingProgramDispatcher.java` 332、`features/text/renderers/AcceleratedStyledSequenceRenderer.java` 323、`core/CoreFeature.java` 321、`compat/iris/…` 若干 200+。

## 3. 入口与注册

`@Mod` 入口极其薄，只挂配置（`AcceleratedRenderingModEntry.java:24-28`）：

```java
@Mod(value = AcceleratedRenderingModEntry.MOD_ID, dist = Dist.CLIENT)
public AcceleratedRenderingModEntry(IEventBus modEventBus, ModContainer modContainer) {
    modContainer.registerConfig(ModConfig.Type.CLIENT, FeatureConfig.SPEC);
    modContainer.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new);
}
```

其余初始化分散在：17 个 mixin config 由 `neoforge.mods.toml` 的 `[[mixins]]` 块声明（`src/main/resources/META-INF/neoforge.mods.toml:57` 起逐块注释）；reload 监听经 `core/CoreModEvents.java:20-23` 注册 `CoreReloads`；GL 能力不足时登录后聊天栏报警告（`core/CoreGameEvents.java:21-26`）。

**接入原版渲染的时机点**（三个）：
1. `MultiBufferSource.BufferSource.getBuffer` 返回值替换——每个 vanilla VertexConsumer 出生时被装上加速外壳（`core/mixins/buffers/BufferSourceMixin.java:42-48`）；
2. `LevelRenderer.renderLevel` 中 `BufferSource.endLastBatch()` 被 WrapOperation——在世界实体批次 flush 的那一刻提交并 draw 全部加速缓冲（`core/mixins/LevelRendererMixin.java:96-134`）；
3. `GameRenderer.renderItemInHand` 调用前后夹取（first-person 手模独立提交一次，`core/mixins/GameRendererMixin.java:19-26,36-81`）。区块轮廓线则钩在 `OutlineBufferSource.endOutlineBatch()`（`LevelRendererMixin.java:66-93`）。

## 4. 核心系统

它合并的**不是区块网格**——整个工程没有一处触碰 chunk rebuild / LevelRenderer 区块合成（与 Sodium 的"合并区块"路线正交）。它合并的是"**每帧 CPU 逐顶点变换**"这件 vanilla 一直在重复做的事，分四层：

**4.1 几何去重层（mesh 缓存）**：模型部件第一次渲染时被收集为 `MeshData`（vertex layout + 全部顶点内容的 `@EqualsAndHashCode` 值对象，`core/meshes/data/MeshData.java:10-14`），以内容为键查 `MeshDataCaches.SERVER/CLIENT`（`core/meshes/ServerMesh.java:82`、`core/meshes/ClientMesh.java:63`），命中即丢弃刚收集的副本、**返回同一个共享 mesh 对象**。也就是说"几何完全相同"的所有 ModelPart/BakedQuad/字形/EMF 部件（含不同实体实例上的同名部件）全库只存一份顶点。每个注入点还额外持有 `Map<IBufferGraph, IMesh> meshes` 与 `Map<MeshData, IMesh> merges` 两级本地缓存（如 `features/modelparts/mixins/ModelPartMixin.java:38-39`），key 里的 `IBufferGraph` 是"消费者装饰链身份"（`core/buffers/accelerated/builders/IAcceleratedVertexConsumer.java:16`），保证同一部件在不同 sheet/decorator 链下不串缓存。烘焙时还能用 `CulledMeshCollector` 下载贴图为 `NativeImage` 做 CPU 背面剔除，把完全不可见的多边形直接从 mesh 里删掉（`core/meshes/collectors/CulledMeshCollector.java:22-40`）。

**4.2 每帧提交层（CPU 只写"实例记录"）**：`ModelPart.render/compile` 被 cancellable 注入后不再逐顶点提交，而是走 `AcceleratedBufferBuilder`。若几何命中 ServerMesh（GPU 常驻池），每帧每实例只调用 `addServerMesh`（`core/buffers/accelerated/builders/AcceleratedBufferBuilder.java:378-404`）——写一条 (color, light, overlay, 矩阵引用) 几十字节的上传记录；动态几何走 `addClientMesh`（`:339-375`），也只是 memcpy 一份 CPU 顶点。变换矩阵经 `beginTransform` 存入**共享区**（`:324-331`，`SHARING_SIZE = 矩阵4x4+法线3x3`，`:36-38`）：同一 PoseStack 层下的多个实例引用同一 sharing 索引，矩阵只写一次。这就是它版的"实例化共享"——不靠 GL instancing，而是把共享粒度做在 buffer 记录层。

**4.3 GPU 展开与变换层（compute shader）**：帧提交时 `AcceleratedBufferSource.prepareBuffers`（`core/buffers/accelerated/AcceleratedBufferSource.java:127-181`）先跑 MeshUploadingProgramDispatcher，把 GPU 常驻 mesh **展开**进本帧顶点缓冲：按 `(MeshBuffer, builder)` 分组后，同一 mesh 的上传记录数 ≥ `sparse_threshold`（默认 64，`configs/FeatureConfig.java:126`；判定在 `core/meshes/ServerMesh.java:42-44`）走 **dense 组**（同 mesh 多实例合并成一次 dispatch，`core/programs/dispatchers/meshes/MeshUploadingProgramDispatcher.java:82-98`），否则走 sparse；随后 TransformProgramDispatcher 派发变换程序，CPU 端只 `glMemoryBarrier`（`AcceleratedBufferSource.java:144`）。顶点常驻在 persistently-mapped SSBO 环形缓冲里（`core/buffers/accelerated/AcceleratedRingBuffers.java` + `core/backends/buffers/MappedBuffer.java`），绕开 `glBufferSubData`；环取空时 `waitSync` 等 GPU fence 回收旧帧（`AcceleratedRingBuffers.java` `fail()`/`Sync.java`）。

**4.4 绘制回接层**：`drawBuffers`（`AcceleratedBufferSource.java:183-233`）在 `glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY|ELEMENT_ARRAY|COMMAND)`（`:188-190`）之后，对每个 (RenderType, layer) 记录执行 `renderType.setupRenderState(); shader.setDefaultUniforms(...); shader.apply(); drawElements(...)`（`:210-225`）——**用的仍是原版 shader 与 RenderType 状态**，这是它能与 Iris 兼容的根本原因：它只改变了顶点从哪来、在哪变换，不改变最终 draw 的管线。

**4.5 状态卫生子系统**：自定义 compute 会占用 SSBO/atomic counter 绑定点，vanilla 及其它光影的 block buffer 会被踩脏，因此每帧提交前后做 `CoreStates.recordBuffers()/restoreBuffers()` 保存并恢复这些绑定（`core/CoreStates.java:7-22`），粒度由配置 `shader_storage_type`/`atomic_counter_type` = IGNORED/RESTORED 控制（`configs/FeatureConfig.java:251-258`，注释直言"IGNORED 提升 FPS 但降低与使用 SSBO 的 mod/shader 的兼容性"）。

**4.6 特性子系统**：GUI 合批（`features/items/gui/GuiBatchingController.java:76-296`：把 GuiGraphics 的 blit/fill/gradient/item/highlight/string 按 depth 归并进 Layer 再统一 flush，对应 `features/items/mixins/gui/GuiGraphicsMixin.java`）；文字加速（`features/text/`：BakedGlyph effect 与整段字符串 `SimpleSequenceKey` 缓存为 mesh，`features/text/key/SimpleSequenceKey.java:15`）；实体阴影 GPU 化（`features/entities/mixins/EntityRenderDispatcherMixin.java:35-80` 取消 `renderBlockShadow` 改走加速渲染器）；过滤（`features/filter/`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **无网络包、无 datagen、无服务端逻辑**（全工程 `dist = Dist.CLIENT`，未见任何 `CustomPacketPayload`/`FMLEnvironment` 通道注册）。
- **配置**是唯一的数据面：`configs/FeatureConfig.java` 670 行、约 60 项，落盘 `acceleratedrendering-client.toml`。粒度设计值得抄——三层：
  1. **特性总开关**：entity/item/text/culling/filter/mods 各一个 `feature_status`（`:236,288,321,378,405,431,541,573,612`）；
  2. **特性内档位**：每特性独立 `default_pipeline`（VANILLA/ACCELERATED，`:294`）、`mesh_type`（CLIENT/SERVER，`:301`）、GUI/hand 加速单独开关（`:307,346,352`）、半透明强制加速 `force_translucent_acceleration`（`:179`）；
  3. **按来源 mod 的开关**：vanilla/EMF/GeckoLib/TLM/SimpleBedrockModel/FTB/Sophisticated/ModernUI 各一（`:618-666`）。
- **性能↔兼容旋钮**：`mesh_collector_type` CULLED/SIMPLE（`:166`）、`draw_method_type` INDIRECT/BASEVERTEX（`:159`）、`sparse_threshold`、`pooled_ring_buffer_size`、`cached_image_size`、`mesh_merge_type`（`:201`）、SSBO/atomic 恢复策略（`:251-258`）、shader storage range（`:265`）。
- **过滤器**：menu/entity/block_entity/item/stage 五类各自的 ENABLED + WHITELIST/BLACKLIST + 正则列表（`:437-527`）。默认菜单白名单 `minecraft:.*`、实体过滤默认关闭——上线姿态保守（先只加速确认安全的部分）。
- **运行时栈式开关**：每个特性类暴露 `forceXxx()/resetXxx()` 的 Deque 栈（如 `features/entities/AcceleratedEntityRenderingFeature.java:13,32-33`；`core/CoreFeature.java:35-39` 的五个栈），第三方 mod 可在自己一段渲染前后压入 VANILLA 档位临时退出加速。

## 6. Mixin / ASM / 接口注入

无自写 ASM，全部是 Mixin（17 个 config json）+ 少量 AT。关键注入点及"为什么必须改它"：

- `LevelRenderer.renderLevel` 的 `MultiBufferSource$BufferSource;endLastBatch()V`（`core/mixins/LevelRendererMixin.java:96-134`，WrapOperation）：这是世界实体/BE 批次最终 flush 的唯一收口点，加速缓冲必须赶在这里 draw 完，否则顶点时序错乱；`renderLevel` HEAD/RETURN 另设"正在渲染世界"标志（`:36-63`）供各特性判定作用域。`renderLevel` close 时统一删除 GL 对象（`:137-157`）。
- `MultiBufferSource.BufferSource.getBuffer`（`core/mixins/buffers/BufferSourceMixin.java:42-48`，ModifyReturnValue）+ `@Mixin(MultiBufferSource.class) interface MultiBufferSourceMixin`（接口注入挂 `IAcceleratableBufferSource` default 方法，`MultiBufferSourceMixin.java:13-28`）：不改这里就没有任何位置能把 vanilla consumer 换成加速 consumer。
- `BufferBuilder`（`core/mixins/buffers/BufferBuilderMixin.java:20-90`）：实例化时懒绑 `AcceleratedBufferBuilder`，`isOutdated()` 驱动每帧换 ring buffer（`:70-90`）；`VertexConsumer`/`VertexDoubleConsumer`/`VertexMultipleConsumer`/`SpriteCoordinateExpander`/`SheetedDecalTextureGenerator`/`OutlineBufferSource`/`EntityOutlineGenerator` 各 mixin 是为了让 vanilla 的**装饰链**把加速身份透传下去——漏一个环节链上就退化为原版路径。
- `ModelPart.render/compile`（`features/modelparts/mixins/ModelPartMixin.java:41-76`，HEAD cancellable）：绕开 vanilla 逐帧 CPU 变换的入口；同理 EMF `EMFModelPartMixin`、GeckoLib `GeoBoneMixin`、SimpleBedrockModel `BedrockPartMixin`、TLM `IGeoRendererMixin`（其 target 直指 TLM 的 sodium 兼容方法 `features/touhoulittlemaid/mixins/IGeoRendererMixin.java:83`）。物品侧钩 `BakedQuad`/`SimpleBakedModel`（`features/items/mixins/models/`）。
- `RenderType.energySwirl/breezeWind` 缓存（`core/mixins/compatibility/RenderTypeMixin.java:31-56`，WrapMethod）：这两个工厂每帧产生新 RenderType 实例，会把"RenderType 作 map 键"的合批全部打碎，故量化 UV 后缓存——不改它，半透明特效层直接失效。
- 兼容 mixin 的开关闸门：`compat/AbstractCompatMixinPlugin.java:14-33` —— 用 `LoadingModList.getModFileById` 判定目标 mod 是否在场，`shouldApplyMixin` 返回 false 时整组 compat mixin 一条不落。**这是它与 Iris/ImmediatelyFast/Curios/Sophisticated 的兼容策略：不检测即不注入，在场才注入**（iris 31 个文件、immediatelyfast 3 个）。对 ImmediatelyFast 是"共栈"：给 IF 的 `BatchableBufferSource` 也实现 `IAcceleratableBufferSource`（`compat/immediatelyfast/mixins/BatchableBufferSourceMixin.java:16-17`），让双方识别对方接管的 buffer。对 Iris 是"改写格式假设"：提供按 Iris ENTITY/GLYPH 顶点格式编译的专用 compute 变体（`compat/iris/programs/IrisPrograms.java:37-131`）+ `IrisBufferEnvironment` 选择覆盖（`compat/iris/environments/IrisBufferEnvironment.java:26-71`）。
- **对 Sodium 的态度**：全仓库仅 2 处提及 sodium，且都是 Iris 内部类/TLM 兼容方法（第 5 点 grep 结果）；没有任何针对 Sodium/Embeddium 实体管线本身的注入——Sodium 会替换 BE/实体合批路径（`EmbeddiumCachingLayerSorter` 一类），**双方同开时的冲突既未处理也未验证**，README 也只承诺兼容 Iris（`README.md` "currently support Iris Shaders"）。可视为"对 Sodium 系区块 mod：放弃协调"。
- `ClientHooksMixin`（`features/filter/mixins/ClientHooksMixin.java:17-24`）注入 NeoForge `dispatchRenderStage`，按 stage 白名单决定 RenderLevelStageEvent 期间是否允许加速——耦合的是 NeoForge 类而非原版。
- AT（`src/main/resources/META-INF/accesstransformer.cfg`）仅 5 条：`ModelPart.cubes/children`、`ModelPart$Cube.polygons`、`RenderType$CompositeState.texturingState`、`OutlineBufferSource$EntityOutlineGenerator`。

## 7. 值得学的 5 条

1. **内容哈希级几何去重**——`core/meshes/data/MeshData.java:10-14` + `core/meshes/ServerMesh.java:82`：以 (layout, 顶点全量) 为 equals 键缓存网格，相同几何天然共享。值得抄：不需要任何 GL 改动就能让"47 种内容里大量复制粘贴出来的法阵部件/砖块模型"在烘焙层归一，直接砍内存和每帧提交量。
2. **每帧只提交实例记录，几何不动**——`core/buffers/accelerated/builders/AcceleratedBufferBuilder.java:324-404`（beginTransform 矩阵入共享区、addServerMesh 只写 color/light/overlay/矩阵引用）。值得抄：CPU 成本从 O(顶点×实例) 降到 O(实例)，且这个"引用共享"思路即使不上 compute shader（比如只喂给 vanilla 的 pose 缓存）也成立。
3. **借绑定点必配恢复闸门**——`core/CoreStates.java:10-22` + `configs/FeatureConfig.java:247-258`：占用 SSBO/atomic counter 前后 record/restore，并把"要不要恢复"做成玩家可选的档位。值得抄：任何往 Minecraft 渲染循环里塞自定义 GL 状态的 mod（自绘特效最典型）都在借全局绑定点，这是唯一正确的姿势。
4. **栈式运行时降级 API**——`features/entities/AcceleratedEntityRenderingFeature.java:32-47` + `core/CoreFeature.java:35-39`：特性开关不是布尔而是 Deque 栈，允许"本段渲染临时回落 vanilla"。值得抄：特效 mod 里"某个实体/某块 GUI 不想被加速"的需求，用栈压弹解决，不用 if 树。
5. **兼容 mixin 以"目标 mod 在场"为闸门**——`compat/AbstractCompatMixinPlugin.java:14-33`：一组 json 一个 plugin，缺席即零注入。值得抄：多 mod 共存库的标准做法，比"启动期反射 + try/catch NoClassDefFound"干净且可审计。

## 8. 公开 API

没有独立 api 包，但留了三类接入点：
1. **IMC 黑名单通道**——`features/filter/FilterIMC.java:42-46`：其它 mod 可通过 InterModComms 发送 `entity_type_blacklist` / `block_entity_type_blacklist` / `item_blacklist` / `menu_type_blacklist` / `stage_blacklist` 消息把自己内容排除在加速外。这是对 mod 作者最正式的"别动我的实体"接口。
2. **ModBus 扩展事件**——`LoadComputeShaderEvent`（`core/programs/ComputeShaderProgramLoader.java:30` 收集注册）、`LoadPolygonProcessorEvent`、`LoadShaderProgramOverridesEvent`：允许第三方注册自己的 compute shader、自定义逐边形处理器（vanilla 顶点管线拿不到的多边形级剔除/加工，`core/programs/processing/`、`core/programs/overrides/`）。
3. **运行时控制器**——第 7 条 4 栈式 `useVanillaPipeline()/forceAccelerateInGui()` 等公开静态方法（各特性类同构），配合 mixin 内一律先查 `isEnabled()` 的模式，构成事实上的编程接口。

---

## 附：六个重点问题的回答

**① 合并对象与机制**：合并的是"实例×顶点"的重复提交。落在三处——内容哈希网格缓存（`core/meshes/`，烘焙层）、帧内上传记录合并 dense/sparse 分组（`core/programs/dispatchers/meshes/MeshUploadingProgramDispatcher.java:82-98`，buffer 层）、矩阵 sharing 去重（`AcceleratedBufferBuilder.java:324-331`）。buffer 层是 persistently-mapped SSBO 环形池（`AcceleratedRingBuffers.java`）。**不做区块网格合并、不做 BE 跨区块合批**（那是 Sodium 的地盘）。

**② 兼容策略**：Iris＝真支持（专用格式着色器 + 环境覆盖，31 文件）；ImmediatelyFast＝共栈共存（给其 buffer source 挂接口）；Sodium/Embeddium＝**未处理**（见第 6 节）；其它渲染 mod＝靠"目标在场才注入"+ IMC 黑名单 + 玩家逐 mod 开关兜底。冲突面：SSBO/atomic 绑定点（有恢复闸门）、GUI 深度与 vanilla flush 时序、`endLastBatch` 被别家 wrap 的顺序竞争。

**③ 失效与重建**：资源重载触发 `CoreReloads.onResourceManagerReload`（`core/CoreReloads.java:13-19`）——只清 `reloadSensitive` 标记的那批 mesh builder 与两级 MeshDataCaches，非 reload 敏感的网格跨重载存活，避免"改一个材质全站重建"。帧级失效靠 `AcceleratedBufferBuilder.setOutdated()`（每帧上传派发时标记，`AcceleratedBufferSource.java:159`）+ `BufferBuilderMixin` 的 `isOutdated` 换 ring buffer。代价在内存：ServerMesh 顶点按 layout 分块存入 GPU `MeshBuffer`（`GL_DYNAMIC_STORAGE_BIT` 可变缓冲，首块 64 字节、溢出即 `resize` 并挂新块，`core/meshes/MeshBuffer.java:13-16,34-38`、`core/meshes/ServerMesh.java:110-124`）、环形缓冲按 `pooled_ring_buffer_size` 预留并逐帧轮转；**不做光照/AO 重算**——light/overlay 是逐实例传入的 uniform 级数据，不走原版光照管线，故无连锁重建，但这也是它必须 force_translucent/半透明档位的原因之一。

**④ 性能主张的依据**：仓库内**没有可复核的 benchmark 代码或计数器**——无 FPS/耗时统计类，`images/benchmark.jpg`（`README.md:8`）是唯一的"数据"，为作者自制截图。可复核的只有能力检测（`core/utils/AvailabilityUtils.java:22-36` 检查 shader image load store/compute/buffer storage 等 6 项 ARB）与 GL debug context 开关（`core/mixins/compatibility/MinecraftMixin.java:18-31`、`backends/DebugOutput.java`）。结论：README 描述 + 公开可关特性，数字本身不可复核。

**⑤ 版本耦合**：依赖 1.21.1 深水区——`renderLevel(DeltaTracker,…)` 签名、`BufferSource.endLastBatch`、`ModelPart.compile`、`RenderType.breezeWind`、NeoForge `ClientHooks.dispatchRenderStage`、Java 21 语法。在 Forge 1.20.1 上**这套 mixin 一行都编译不过/落不了点**；可复用的是设计：MeshData 内容键、sharing 矩阵、栈式开关、AbstractCompatMixinPlugin 闸门、SSBO 恢复闸门（1.20.1 需自建 GL 封装）。卡片里的 `1.20.1-alpha` jar 名提示作者可能有 1.20.1 旧线，本检出无证据（未验证）。

**⑥ 给「求仙问道」的落地建议**（Forge 1.20.1，大量同类方块 + 法阵特效）：
1. **先抄烘焙层去重，不碰渲染管线**：把 47 种内容里几何相同的法阵件/同类方块模型在 BakedModel/ModelPart 产物上做内容哈希共享（学 `MeshData.java:10-14` 的思路，用 Java 侧 equals 键即可），收益是内存与区块重烘焙量，零管线风险。
2. **特效走"引用共享"而非新建 GL 路径**：法阵几十个实例共用一套顶点、每实例只存 pose+颜色+亮度引用（学 `AcceleratedBufferBuilder.java:324-331` 的 sharing 语义），在 1.20.1 的 RenderType 内用普通 buffer 提交也成立，不必上 compute shader。
3. **不该走这条路的判据**：同屏实例×顶点积在数千以内（几十个法阵属于此量级）、或需要与 Sodium/Embeddium/Oculus 同包共存、或团队没有能维护 GL4.6 + 三家兼容矩阵的人——满足任一条就停在建议 1/2 的层面。ARR 自己 355 文件 2.6 万行、17 个 mixin config、31 个 iris 兼容文件就是这条路的账单。
4. **风险最大的设计**：`core/mixins/LevelRendererMixin.java:96-134` 的全局 `endLastBatch` WrapOperation——它是全部加速内容的唯一提交闸口，任何 mod 重排/替换该方法（Sodium 系实体批次管理、其它 wrap 同点的优化 mod）都会导致整条加速链静默失效或时序错乱；它是收益点也是单点故障，读者若模仿必须自带"闸口失效即全量回落 vanilla"的检测。

## 遗留与偏差说明

- 未挖：GLSL 计算着色器本体（稀疏检出不含 `*.compute`），4.3 节展开/变换细节按 Java 调度侧推断，程序内部写法未验证。
- 卡片勘误：行数 26,610 → 实测 26,255；jar 名版本（1.0.14/1.20.1）与仓库（1.0.15/1.21.1）不一致，系采集时点差异，卡片未改动（任务规定只允许写报告文件）。
- 本报告为唯一新建/落盘文件；未创建、修改或删除其它任何文件，未执行 git 写操作。
