# KilaGraph 源码分析报告

- 仓库：`源码库/_参考仓库/_bulk/Low-Drag-MC__KilaGraph`（分支 `26.1`，HEAD `920e44e`）
- 定位：README.md:5 自称 "A programmable node graph and shader graph toolkit for Minecraft mod developers"——它给**别的 mod** 提供"图 → 可执行逻辑"的地基，自己不注册任何游戏内容。
- 阅读取舍：全仓 668 个 `.java`、83,277 行，其中 34% 行数是仓库自带 GameTest。按"构建脚本 → 入口类 → `graph/core` → `graph/exec` → `rendertype`(编译+运行时) → `blueprint/nodes` 抽样"细读了约 20 个文件，节点族按包统计略读。LDLib2 是外部 jar（`build.gradle:142`），`nodegraphtookit` 的 `Graph/Node/GraphModel/GraphNodeRegistry` 基类源码不在本地，凡涉及基类行为的推断一律标"未验证"。

## 1. 基本信息

| 项 | 值 | 出处 |
|---|---|---|
| mod_id | `kilagraph` | `gradle.properties:19` |
| 作者 / 版本 / 许可证 | KilaBash / `26.1.0.14` / `MIT-LICENSE`（README 与 `LICENSE` 均称 MIT） | `gradle.properties:22,21,24` |
| 目标 MC / 加载器 | Minecraft `26.1.2`，NeoForge `26.1.2.59-beta`，FML `[4,)` | `gradle.properties:8,11,15` |
| Java | toolchain `25`（`build.gradle:45`）；mixin `compatibilityLevel` 写 `JAVA_21`（`src/main/resources/kilagraph.mixins.json:5`） | 同上 |
| Gradle 插件 | `net.neoforged.moddev` 2.0.141（`:5`）、`io.freefair.lombok` 9.2.0（`:6`）——全仓只有 2 个文件 `import lombok`（`rendertype/gui/RenderTypeGraphView.java:23`、`GradientColorSelector.java:18`），插件近乎闲置 | `build.gradle` |
| 工程结构 | 单模块；`mods.toml` 由 `ProcessResources` 从 `src/main/templates` 展开生成（`:156-179`）；`src/generated/resources` 挂进 resources（`:138`）但该目录不存在 | 同上 |
| 关键依赖 | **LDLib2** `26.1.2.39`（`build.gradle:142`，版本范围 `gradle.properties:29-30`）：编辑器、节点画布、`@Configurable`/Accessor 序列化体系全部来自它 | — |
| 图/求值是否自研 | **是**，无外部图/脚本/表达式库。`GraphExecutor`/`PreparedGraph`/`ShaderGraphCompiler` 均为本仓库手写；依赖表里没有 gremlin/jgrapht/antlr/任何脚本引擎坐标（`build.gradle:140-150` 全文只有 LDLib2、Sodium/Iris、JUnit） | — |
| Iris / Sodium | `localImplementation`（`build.gradle:145-146`，配置见 `:49-56`）：编译期可见、不打包，只在装了 Iris 时通过 mixin 生效 | — |

## 2. 源码规模与包结构

实测（`find`/`wc -l`，行数按换行符计）：

- `.java` 总数 **668**，总行数 **83,277**；`src/main/java` 656 文件 / 81,368 行，`src/test/java` 12 文件 / 1,909 行（纯 JVM JUnit，无游戏）。
- `src/main/java/.../kilagraph/test/`（GameTest，随主源码编译）**84 文件 / 27,936 行**——去掉它，产品代码是 572 文件 / 53,432 行。这是本仓库最重要的结构事实：三分之一的体量是"给节点系统写黄金测试与微基准"。
- 节点数量：`@NodeAttribute` 出现 681 次（非测试），其中 blueprint 495、rendertype 186。它们大量以**静态嵌套类**形式集中在族文件里（例 `blueprint/nodes/mc/action/BlockActionNodes.java:22,38,80,119,183` 一个文件四个节点）。

主要包（文件数 | 行数）：

| 包 | 文件 | 行 | 角色 |
|---|---|---|---|
| `graph/exec` | 19 | 5,999 | 求值引擎（心脏） |
| `graph/core` | 10 | 585 | 注解→端口/选项的节点定义层 |
| `graph/type` + `graph/ui` + `graph/util` | 20 | 2,429 | 类型句柄、编辑器 UI 扩展、节点文档（另有 `graph/mc/McConvert.java` 51 行） |
| `blueprint/**` | 221 | 21,387 | 逻辑节点族（math/list/map/string/bitwise/convert/vector/mc_*/ldlib2_ui_*/exec） |
| `rendertype/**` 合计 | 287 | 22,074 | 着色器图侧，拆解见下 |
| — `rendertype/nodes/**` | 199 | 9,737 | 着色器节点族（math/uv/fragment/input/procedural…） |
| — `rendertype/compiler` | 32 | 4,468 | 图→GLSL 编译器 |
| — `rendertype/runtime` | 13 | 1,794 | 编译产物接进 vanilla 渲染管线 |
| — `rendertype/{gui,preview,iris,format}` | 37 | 4,858 | 编辑器界面、实时预览、Iris 兼容、顶点格式 |
| `editor` | 7 | 506 | 三种图资源的编辑器接线 |
| `mixin` | 6 | 330 | 5 个 mixin + 1 个插件 |
| `test`（GameTest） | 84 | 27,936 | blueprint 侧 75 文件、rendertype 侧 3 文件、公共 harness 6 文件 |

最大源文件（去掉测试）：`rendertype/compiler/ShaderGraphCompiler.java` 2,280、`graph/exec/GraphExecutor.java` 2,181、`graph/exec/PreparedGraph.java` 1,030、`rendertype/RenderTypeGraph.java` 568、`rendertype/compiler/ShaderCompileContext.java` 562、`blueprint/nodes/ui/doc/UIDocNodes.java` 536、`rendertype/iris/IrisShaderInjector.java` 504、`graph/exec/EvalContext.java` 504、`graph/exec/ExecContext.java` 483、`rendertype/gui/CurveSelector.java` 459。含测试则有 `test/gametest/rendertypegraph/ShaderCompilerGameTest.java` 3,068 与 `RenderTypeGraphGameTest.java` 879。（速览卡片的行数普遍比实测大 1，是末行无换行符的统计口径差，卡片的其他数字与实测一致。）

**检出完整性**：本目录是 partial clone + sparse-checkout（`.git/info/sparse-checkout` 含 `**/*.java`、`**/*.mixins.json`、`**/*.md`，**不含** `**/*.json`/`*.glsl`/`*.nbt`/`*.png`）。因此工作区里 `src/main/resources` 只剩两个 mixins json，而 git 树（693 个文件）另有 `assets/kilagraph/lang/{en_us,zh_cn}.json`、`assets/kilagraph/shaders/include/kg_scene.glsl`、`data/kilagraph/structure/test_area.nbt`、`icon.png` 未落盘。后果：(a) 代码里大量 `kg.node.<name>.tooltip` 语言键（`graph/core/AnnotatedNode.java:45-48`）无法核对文案；(b) **本地看不到任何"一张具体图"的样例文件**——而且 git 树里本来也没有 blueprint/rendertype 图的样例 json/nbt，图实例只存在于 LDLib2 编辑器工程里，不随仓库分发；(c) `graph/type/KGTypeHandles.java:81` 引用的 `docs/CONVENTIONS.md` 在此提交树中不存在。凡涉及图定义文件格式，本报告只描述代码里的 NBT 读写，不猜字段布局。

## 3. 入口与注册

入口 `com/lowdragmc/kilagraph/Kilagraph.java:20-71`，一个 `@Mod` 构造器，做四件事（节选）：

```java
KGTypeHandles.init();                       // :28  自定义 TypeHandle 必须先于任何节点类被扫描
KGUITypeHandles.init();                     // :31
AccessorRegistries.registerAccessor(        // :34-58 给自定义值类型补 codec，否则图 NBT 里静默丢值
    CustomDirectAccessor.builder(RenderTypeGraphTypes.Sampler2DValue.class)
        .codec(SAMPLER2D_CODEC).streamCodec(SAMPLER2D_STREAM_CODEC).copyMark(v -> v).build(), 1000);
LOGGER.info("... nodes loaded: {}", BlueprintGraph.NODE_REGISTRY.getNodeClasses().size()); // :61
```

`:26-27` 的注释是理解注册成本的钥匙：**注册表在扫描时会实例化每个节点类来采集端口类型**，所以自定义类型句柄和 accessor 必须先就位。`KGTypeHandles.java:46-115` 声明了 `LIST/MAP/NODE_REF/VEC2-4/VECTOR/BLOCK_POS/LEVEL/ENTITY/CONTAINER(...)` 等句柄；`BlueprintGraph.java:44-89` 区分 `getSupportTypes()`（线能承载的类型，含 Level/Entity 这类"只可连线不可写字面量"的）与 `getLibrarySupportTypes()`（能拖出常量节点的），并注释说明为何排除前者四个（`:92-104`）。

- 节点注册：每个图类型持有一个 `GraphNodeRegistry`，节点类用 `@NodeAttribute(name=..., group=..., graphTypes=BlueprintGraph.class)` 绑定；类路径扫描与 `graphTypes` 过滤发生在 LDLib2 侧（本仓库无扫描代码，`Kilagraph.java:59-60` 只"摸一下注册表触发扫描"）。同一节点类可绑多个图：`rendertype/nodes/logic/ExpressionNode.java:48` 的 `graphTypes = {RenderTypeGraph.class, ShaderFunctionGraph.class}`。分组 `group` 是纯字符串路径，编辑器按它摆树（`blueprint/nodes/ui/sync/UIBindingNodes.java:64` 的 `GROUP = "ui/sync"`）。
- 图类型注册：`BlueprintGraph.java:25-27`、`rendertype/RenderTypeGraph.java:53`、`rendertype/ShaderFunctionGraph.java:26-28` 各建一个 registry，靠 `:30-37` 的 `getSupportNodes()/createGraphModel()` 接上。
- 注册表事件：无 FML `DeferredRegister`（全仓 grep 无），也**没有任何自定义网络 payload**（grep `CustomPacketPayload|PayloadRegistrar` 零命中）。节点里出现的 `BuiltInRegistries.*`（如 `blueprint/nodes/mc/action/WorldEffectNodes.java:75`）是**读** vanilla 注册表，不是注册自己的东西。

## 4. 核心系统

### 4.1 图的表示与序列化：权威形态是对象图，持久化是 NBT 投影

图不是 JSON、不是 Codec、也不是自定义数据类——它**就是** LDLib2 的 `Graph` 对象图（`nodeModels` + `wireModels` + `graphVariableModels`）。KilaGraph 只加了两个子类：`BlueprintGraph`/`RenderTypeGraph`（`blueprint/BlueprintGraph.java:23`、`rendertype/RenderTypeGraph.java:52`）与模型子类 `graph/type/KGGraphModel.java:28`。

序列化见 `editor/RenderTypeGraphResource.java:51-58`：`graphModel.serialize(TagValueOutput)` → `CompoundTag`，外层再包 `{graph, settings}` 两段；读回在 `:72-88`（`TagValueInput.create(..., Platform.getFrozenRegistry(), tag)`）。用的是 1.21.x 起的 ValueInput/ValueOutput + registry ops 通道，因此注册表对象（Block/Item/ComponentType…）序列化时带 registry snapshot 语义。`settings`（顶点格式元素、blend、depth、cull、outputTarget）是手写 tag，不是节点（`:90-119`），并带一个"旧存档枚举→新 key 列表"的升级分支（`:125-144`）。`blueprint` 资源不覆写序列化（`editor/BlueprintGraphResource.java:16-41`），直接吃基类默认（基类实现未验证）。

**一张图存在哪里**：KilaGraph 里没有方块实体、没有物品组件、没有存档级 attachment 承载图。图是 LDLib2 编辑器工程里的**资源**（`editor/KilaGraphEditor.java:23-30` 注册三类 `GraphResource`；打开方式见 `editor/KilaGraphEditorScreenTest.java:17-28`，`@LDLRegisterClient(... registry = "ldlib2:screen_test")`，dev-only）。运行时宿主由消费方 mod 自己承担——`RenderTypeGraphMaterial.java:72-75` 的注释提到外部宿主（SlideShow 的解码纹理、EntityStudio，另见 `graph/type/KGTypeHandles.java:56-60`）。跨图引用（把别的图当子图）通过 `IGraphReferenceResolver` 注入 deserialize（`RenderTypeGraphResource.java:42-44,78-82`），解析器由 LDLib2 提供。

**编辑全在游戏内，撤销 = 整个模型的 NBT 往返**：画布、资源面板、节点库、inspector 都来自 LDLib2 的 `Editor` 基类（`editor/KilaGraphEditor.java:10-13` 的注释直说 "All editing UI ... comes from the LDLib2 base class"，本仓库只做资源装配与关掉左窗口），另有节点缩略图与整图预览（4.5）。撤销不是记录 diff 的命令对象，而是 `UndoableGraphCommand` 把整个 graph model 序列化再反序列化（`rendertype/RenderTypeGraphModel.java:38-44` 注释）。这条决定两个后果，都是可直接借用的教训：(a) 反序列化会重建所有 NodeModel 实例，所以任何被缓存的"节点引用"必须在一个统一钩子里重解析——`:47-51` 的 `afterDeserialize()` 专门复原固定的 vertex/fragment stage 引用，注释写明不这么做的症状是"删掉一个节点再撤销，编译出全透明的 shader"；(b) 可变参数值必须深拷贝，否则撤销/实例化会让两份图共享同一个 Gradient/Curve 被就地拖改——`Kilagraph.java:45-58` 的 `copyMark(RenderTypeGraphTypes.GradientValue::copy)` 就是为这个（注释："the editor drags points in place"）。与之配套：预览选的几何形状存在 **model 的附加 NBT**（`RenderTypeGraphModel.java:56-57,78,102-122` 的 `serializeAdditionalNBT/deserializeAdditionalNBT`，且反序列化先 clear 再装，"replace, never merge"），而不是存在 UI 上，理由同样是"要同时活过重开与撤销"。

### 4.2 节点定义与参数化：注解字段 → 端口/选项，一次反射终身缓存

`graph/core/AnnotatedNode.java:30` 是所有逻辑节点的基类，声明五个字段注解：`InputPort / OutputPort / ExecInputPort / ExecOutputPort / Option`（同目录）。机制：`NodeMetadata.scan(Class)`（`graph/core/NodeMetadata.java:53-63`）沿父类链扫非静态字段，`scanField`（`:65-105`）把字段 Java 类型经 `KGTypeHandles.handleFor(genericType)` 映射成端口类型，exec 端口固定为 `TypeHandles.EXECUTION_FLOW` + `PortCapacity.SINGLE/MULTIPLE`（`:91-100`）；结果按类缓存在 `CACHE`（`:47`，`AnnotatedNode.java:34-37` 懒取）。

参数声明 = 一个带初始值的字段。`applyOptions`（`NodeMetadata.java:107-122`）读字段值当默认值，并 `withFieldContext(field, node)` 把字段交给 LDLib2 的 `@Configurable` 生态生成编辑器控件；**若该类型没有注册 accessor，就退到 `withoutConfigurator()`**（`:112-120`，探测在 `:161-168`）——即"能编辑/能序列化的参数"与"只能连线的参数"由同一个 accessor 表决定，且降级是自动的。变长/依赖参数的口子是 `onDefineDynamicPorts`（`AnnotatedNode.java:79`），例 `blueprint/nodes/math/AddNode.java:26-32` 按 `inputs` 选项生成 `in1..inN`；`AnnotatedNode.java:106-120` 的 `optionValue()` 提醒作者"读选项当前值，不要读 Java 字段（那是声明期默认值）"。端口排序也做了工程处理：exec 端口先发射，保证 `trigger/next` 永远在节点顶部（`NodeMetadata.java:124-134`）。

类型兼容规则集中在 `graph/type/KGGraphModel.java:54-84`：EXEC 严格同型、UNKNOWN 通吃、Number↔Number、任意→String；配套的运行时降级在 `EvalContext.coerce`（`graph/exec/EvalContext.java:482`）。

### 4.3 求值模型 A：数据流 = 惰性 pull + 代际 memo + 双 lane 槽表

`GraphExecutor`（`graph/exec/GraphExecutor.java:37-76` 自述）是**按需拉取**的求值器，不是拓扑排序预算，也不是每 tick 传播。三个入口：`evaluate(PortModel, Class)`（`:437`）、`runOutputs()`（`:458`，把所有 OUTPUT 图变量拉一遍）、`executeFrom(NodeModel)`（`:481`）。拉取递归上游，`ensureComputed`（`:1178-1194`）用 `stamps[slot] == generation` 判命中，因此"缓存了 null"与"未缓存"可区分（`:66-70` 注释）。

值的存放是**扁平整数槽**而非 map：每个端口一个 slot，`Object[] slots` + `long[] nums` + `byte[] kinds`（`KIND_FLOAT/DOUBLE/INT/LONG/OBJECT`，`:97-113`）。数值走 raw-bits lane 是为了不装箱——`:91-98` 明确写着"`Float.valueOf` 无缓存，旧单 lane 下每条数值边都分配"。`clearCache()` 靠 `written[]` 只清"本次真写过的槽"（`:114-122`），且强调必须清空引用以免长生命周期执行器钉死死掉的 `Entity/ItemStack`。

**环**：prepare 期做一次三色 DFS（`graph/exec/PreparedGraph.java:553-598`）得出 `mayCycle`（`:502` 赋值），无环则运行时完全跳过栈登记（`GraphExecutor.java:1181-1186`、`:315-316`）；有环则每次进入节点走 `enterNode/exitNode` 的 `boolean[] + visitStack`，撞见在栈上的节点就抛 `CycleException`（`:1318-1332`，`graph/exec/CycleException.java:8-12`，消息是 UID 链）。注意 `detectCycle` 的两处"看不见边"的例外——wire-portal exit 与 context block 会沿 `inputSourceOwners` 之外的边递归，所以只要图里有这两类节点就直接保守地保留运行时检查（`:554-568`）。exec 侧的"环"靠 `WhileController.maxIterations` 兜底（`graph/exec/LoopController.java:96-116`），不做静态检测。

求值层的性能预算是**带实测数字写进注释**的，这是本仓库对"⑤ 成本在哪"的正面回答：`PreparedGraph.java:676-684` 记录 `PortModel.getEmbeddedValue()` 是一次按端口唯一名 key 的 HashMap 查、约 8ns，在 `Remap`（一根线 + 四个常量）这种节点上占到整个节点步的 **59%**，于是把 `Constant` 引用预解析进 `inputConstants[]`，但**值仍通过该引用活读**以便编辑器改常量立刻可见；`:685-694` 同理解释 `inputTypes[]` 只为让 `isFresh()` 察觉换掉常量的 retype。多张图同时跑的边际成本因此是"每图一份 PreparedGraph（`synchronizedMap(WeakHashMap)` 共享，`:144-159`，注释说明 value 必须是 WeakReference 否则永远不逐出）+ 每执行器一组数组"，而不是每 tick 重建解析结构。

### 4.4 求值模型 B：执行流 = 显式帧栈 VM，可单步

exec 流不是同步递归，而是 `ExecSession`（`graph/exec/ExecSession.java:16-38`）持 `Deque<ExecFrame>` 的虚拟机：loop / sequence / subgraph 各推自己的帧（`LoopFrame/SequenceFrame/SubgraphFrame`），`Break/Continue` 是 `Signal` 由 `applySignal()` 路由到最近的 `LoopFrame`（`:44-45`）。于是 `step()`（`:102-117`）能"跑一个 exec 节点就返回"，`runToBreakpoint()`（`:174`）+ `currentNode()`（`:224`）+ `stepCount()`（`:244`）构成一个 blueprint 调试器；`executeFrom` 只是 `begin + runToCompletion`（`GraphExecutor.java:481-494`）。`runToCompletion`（`:142-166`）有一条"同帧未换就不重复 settle"的融合驱动快路，并用 `Opt.FUSED_EXEC_DRIVER` 保留慢路用于对比。

节点侧 API 是 `ctx.flow(id)`（`graph/exec/ExecContext.java:367`）、`pushSequence`（`:395`）、`pushLoop(controller, body, completed)`（`:412`）、`signalBreak/Continue`（`:436+`）、`state()`（`:470`）。控制流节点因此只写声明式一行：`blueprint/nodes/exec/ForNode.java:33-40`。**关键约束**：它跑在调用线程上，不另起工作线程（`ExecSession.java:23-26`），为的是 Minecraft 线程亲和（图能碰 `Level/Entity`）。

状态分三层，这是它能被反复运行的原因：(1) 节点实例**零运行态**（`AnnotatedNode.java:26-29`）；(2) 每次求值 memo 在执行器槽表，`clearCache()` 清；(3) 跨运行持久态在 `nodeState`（按节点 UID 的 map，`GraphExecutor.java:178-186`，公开于 `:927`）。`blueprint/nodes/exec/CacheNode.java:33-42` 就是靠"loop 的 clearCache 不清 nodeState"实现永久 memo，并用 `NODE_REF` 输出让 `CacheClear` 指名清它。`retainExecOutputs(boolean)`（`:409`）另提供一种"exec 发布的槽跨 clear 存活"的语义。

### 4.5 第二种"图 → 可执行"：编译成 GLSL 并挂进 vanilla 管线

`rendertype/compiler/ShaderGraphCompiler.java:41-51`：编译器同样**需求驱动、反向拉取**，从 fragment 的语义 block 往上游走，把每个非常量输出提升成临时变量按依赖顺序发出；维护 vertex/fragment 两个 `StageScope`（各带 body/temp 计数/memo 缓存，`:57-80`），碰到 varying 即认作阶段边界。与 4.3 是**同构的两台机器**——一台解释执行，一台编译到 GLSL。

产物 `CompiledShaderGraph` 带一个稳定 `contentHash`（`rendertype/compiler/CompiledShaderGraph.java:17-83`，注释逐项说明哪些元数据**故意不**进 hash：逐实例 uniform/纹理、缺 attribute 的降级、stage 错误）。`rendertype/runtime/RenderTypeFactory.java:44-70` 用 hash 作缓存键持有 `RenderPipeline`，并**引用计数**：`createMaterial` acquire、`RenderTypeGraphMaterial.close()` release（`rendertype/runtime/RenderTypeGraphMaterial.java:387`），归零才逐出 pipeline + GLSL 源——注释点名这是为"每次编辑都换新 hash 的实时预览"兜内存。`:96-120` 还会 GPU 校验失败就把该 hash 永久记入 `FAILED`，避免每帧重试。

生成 shader 的注入点是 `mixin/client/ShaderManagerMixin.java:21-29`（劫持 `ShaderManager.getShader`，源从 `DynamicShaderSourceRegistry` 取，见 `rendertype/runtime/DynamicShaderSourceRegistry.java:11-33`，注释说明这让产物**跨资源重载存活**）；`rendertype/runtime/GlslImportProcessor.java:29-59` 用 vanilla `GlslPreprocessor` 展平 `#moj_import`（因为设备直接编译拿到的源）。

我认为**做坏了的一层在这里**（仅编辑器，不影响游戏运行时）：脏标记粒度是"整张图"。`rendertype/RenderTypeGraph.java:464-468` 每次改动都 `changeVersion++` 并调 `validateGraph(logger)`，而后者在 logger 非空时会**整图再编译一次**只为读出被降级的 attribute 默认值（`:377-382`）；每个带缩略图的节点在提交绘制时（`submit`）调 `updateMaterial()`（`rendertype/preview/NodeShaderPreview.java:131-133,143`），内部各跑一次 `compilePreview(port)`（`:157`），其注释自陈"Graph-wide, so any edit re-checks every thumbnail — conservative but correct"（`:144-146`）。结果是拖一个滑条 = 1 次校验编译 + N 个缩略图编译（外加预览面板那次）。缓解手段（contentHash 相同就只 `refreshDefaults`，`:168-172`）只压掉了 pipeline 重建，没压掉 GLSL 生成与哈希。缺的是"以该端口的上游子图为单位"的局部脏标记——`compilePreview` 本来就是子图编译，天然可缓存。另一处值得警惕的运行时成本：`PreparedGraph.isFresh()` 每次顶层入口都要走一遍 `getWireModels()/getNodeModels()/getInputsById()/getOutputsByDisplayOrder()`（`graph/exec/PreparedGraph.java:222-252`），这几个 LDLib2 访问器是否返回缓存视图本仓库无法核实（未验证），宿主若"每实体每 tick 跑一张图"必须显式 `setGraphFrozen(true)`（`graph/exec/GraphExecutor.java:2148`），而它是默认关的。

### 4.6 世界怎么进图：值，不是环境字段

`graph/exec/EvaluationEnvironment.java:20-97` 只带 `VariableStore` 与 RNG 种子——**没有 Level**。世界对象是图的输入值：`blueprint/nodes/mc/action/McActions.java:42-45` 从 `level` 输入端口取 `Level`，只有 `ServerLevel` 才允许写；`:14-28` 的规则值得整段抄（客户端 level 是近似物 → 拒写、报 `ok=false`、但**继续 flow 而不抛异常**，因为同一张图可能被服务端跑也可能被客户端预览跑）。`:64-70` 把 NeoForge 26.1 的事务模型翻译成节点的 `simulate` 输入：开根事务 → 干活 → 不 commit 即回滚。

`graph/ui/UICallbacks.java:13-55` 解决"图只跑一次、事件几分钟后才发生"的延迟回调：同一节点被**两阶段重入**——注册阶段订阅并给回调留一个 Trampoline；派发阶段由回调把 phase 标志与 payload 写进 `nodeState` 后**再调一次 `executeFrom(同一节点)`**（`:201` 处实际调用），节点看到标志就发布 payload 并 fire `onEvent` 而不是 `then`。它显式依赖"每次派发前 `clearCache()`"，否则处理器会读到建树时 memo 下来的旧值（`:43-48`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **图定义能否来自 datapack/JSON：不能。** 图的唯一载体是 NBT（4.1），仓库里没有 `Graph` 的 `Codec`，也没有 JSON→图 的加载器。有 Codec 的只是**值类型**：`rendertype/RenderTypeGraphTypes.java:195-206`（Sampler2D）、`:250-268`（Gradient）、`:360-367`（Curve）、`graph/type/Vectors.java:50`，它们服务 accessor 的 NBT 往返（`Kilagraph.java:34-58` 注册）。要做"图作为 datapack 内容"，缺的正是这一层 Codec + 一个 reload listener，本仓库没有。
- **确实走资源系统的两处**：UI XML 由 `graph/ui/UIXml.java:66-76` 经 `ResourceManager` 读，注释明确"客户端查 assets、服务端查 datapack，单机能跑的东西专用服可能缺文件"；GLSL include 走 `assets/<ns>/shaders/include/`（4.5）。此外 `rendertype/nodes/logic/ExpressionNode.java:31-49` 用一段 JSON 文本塞进 STRING 选项来声明自定义节点的端口与 GLSL 体（Gson 解析，见 `:3-5` 的 import），这是仓库里唯一"文本 → 节点结构"的通道。
- **网络：零自定义包**（grep 无 payload）。blueprint 的跨端一致性走"两端各自跑同一张图"的路子：`graph/ui/UICallbacks.java:49-55` 与 `blueprint/nodes/ui/sync/UIBindingNodes.java:58-61` 都强调"两侧必须建同一棵树，同步值按注册顺序识别"，值搬运委托给 LDLib2 的 sync/binding 层。rendertype 纯客户端。
- **配置：无**（grep `ConfigSpec|ModConfig` 零命中）。可配置的东西都是图/资源自带的 `Settings`（`editor/RenderTypeGraphResource.java:90-119`）。
- **datagen：只有脚手架，无产物**。`build.gradle:95-103` 配了 `data { clientData() ... --output src/generated/resources }` 且 `:138` 把它挂进 resources，但 `src/generated` 目录不存在，仓库也不生成 lang/模型（语言键由 `graph/util/NodeDescriptions.java`、`NodeTooltipHelper.java` 消费，文件本身在检出的 git 树里但未落盘，见第 2 节）。测试基建有 `gameTestServer` run（`:90-93`）与 JUnit unitTest（`:131-133`），`neoforge.enabledGameTestNamespaces=kilagraph`。

## 6. Mixin

只有客户端渲染相关，blueprint/求值层**不碰任何 vanilla 私有状态**——这是本仓库最重要的架构边界之一。

- `src/main/resources/kilagraph.mixins.json`（required=true）：`mixin/client/ShaderManagerMixin.java:18-29`（`@Inject HEAD` 于 `ShaderManager.getShader`，cancellable，把 `kilagraph:generated/*` 的 id 路由到动态 shader 源）；`mixin/client/RenderTypeMixin.java:29-88`（三处注入 `RenderType.draw`：`HEAD` 上传材质 UBO + Iris 阴影 pass 安全跳过并 `ci.cancel()`；`drawIndexed` 前绑定自定义 UBO/纹理并设 `kg_surface_id`；之后清 discriminator）。之所以需要它，注释写在 `:15-21`——vanilla `draw` 只绑默认 uniform + `DynamicTransforms` + RenderSetup 纹理。
- `src/main/resources/kilagraph.iris.mixins.json`（required=false，`defaultRequire:0`，带 plugin）：`mixin/iris/IrisMixinPlugin.java:12-58` 用 FML mod list + `Class.forName` 双探测决定是否应用，注释解释"目标类改名时静默不生效而非崩启动"，并用 `wasApplied` + 行为学 `seamDead` 闩把"require=0 但零注入"这种情况在运行时**大声**报告；`mixin/iris/MixinShaderCreator.java:18-30`（`@ModifyVariable` 改 shaderpack 程序的 GLSL 源，`remap=false`，targets 字符串引用 Iris 类）；另两个打 Sodium 的 `GlCommandEncoder`。
- 没有 AT/accesstransformer（`src/main/templates/META-INF/neoforge.mods.toml` 末段该块被注释掉）。

## 7. 值得学的 5 条

1. **把"寻址"从求值里剥出来做一次预解析**：`graph/exec/PreparedGraph.java:38-59`（旧实现每步都在编辑器 model 上做 hash 查端口、`new ArrayList`+`new PortKey` 找连线、`instanceof` 链判类型；预解析后运行期只碰整数索引数组，第二次运行起零分配）＋ `:656-740`（每节点一个快照：`inputIds/inputSlots/inputSourceSlots/inputSourceOwners/flowTargets/outputSlots`）。最狠的一句是 `:61-64`：**不预计算"何时、跑几次"**，因为节点惰性拉输入是可观察语义（And/Or 短路、Select 只拉被取分支）。为什么值得抄：这是"图跑得快"与"图语义不变"之间唯一干净的分界线。
2. **每个优化都留一条可开关的旧路径，并配差分测试**：`GraphExecutor.java:200-277`（`enum Opt` 十项，注释逐项写清省了什么、关掉后恢复的是什么；`NUMERIC_PROMOTION` 甚至自陈"这不是优化，关掉会算错答案"，只为满足基准对比规则），入口 `:310-313`，配套的差分工具在 `test/gametest/KGDifferential.java`、优化旁路例如 `:621-625`。为什么值得抄：性能改动的可证伪性只能靠这个结构获得，而它同时是回归测试。
3. **分配量当断言、不拿挂钟当断言**：`test/gametest/KGBench.java:10-26`（"绝不断言 wall-clock"，报 ns/node-step 与 `ThreadMXBean.getThreadAllocatedBytes` 的 bytes/run）＋ `test/gametest/blueprint/ExecutorBenchGameTest.java:143-149`（同一条 16 节 lerp 链"改造前 13,176 B/run"，断言预算 64 B/run）。为什么值得抄：求仙问道以后要解释"为什么每秒几千次回路求值不卡"，只有这种数字能解释。
4. **新鲜度检测自己实现，别指望上游有 dirty 位**：`PreparedGraph.java:66-79` 明确列出 LDLib2 为什么没得挂（`GraphModel` 无版本计数、`setGraphObjectDirty()` 是空桩、`PortWireIndex.isDirty` 私有、`GraphChangeDescription` 是 accumulate-and-flush 且编辑器每帧抽干），于是 `:222-252` 用"wire 数组 + 两端端口引用 + 每节点端口计数 + 每输入 TypeHandle"的结构快照做引用比较；`GraphExecutor.java:544-546` 把这次 O(图规模) 校验限制在顶层入口。为什么值得抄：任何"把编辑器模型接进运行时"的系统都会撞上这个坑，这份代码把代价与降级（同数改名查不到 → 退回活模型，慢但不答错）都写清了。
5. **世界写操作的统一收口**：`blueprint/nodes/mc/action/McActions.java:14-29`（客户端 level 一律拒写、报 `ok=false`、**继续 flow 不抛**，理由是同一张图可能在两侧跑）＋ `:64-70`（`simulate` = 开事务不 commit）。为什么值得抄：修仙 mod 的"施法/布阵/改方块"迟早要面对"客户端也调了一次这张图"，把策略写成一个 `McActions` 式的公共壳，胜过在 47 种内容里各写一遍。

另记一条（没挤进前五）：`rendertype/runtime/RenderTypeFactory.java:44-70,96-120` 的"内容哈希当缓存键 + 引用计数逐出 + 失败哈希永久记黑"，是任何"图 → 昂贵编译产物"的通用形状，值得整套搬走。

## 8. 公开 API（本仓库是 toolkit，这节按框架对待）

对宿主 mod 暴露的稳定面（都在 `com.lowdragmc.kilagraph` 包内；本仓以 maven 库形式分发，`publishing` 块 `build.gradle:183-195` 用 `artifactId = archives_name`（= `kilagraph-neoforge-26.1`，`gradle.properties:27`）、group `com.lowdragmc.kilagraph`、发布到 `maven.firstdark.dev/snapshots`（`build.gradle:192`），并且 `java.withSourcesJar()`（`:46`）；LDLib2 以 `implementation` 传递，见 `build.gradle:142`）：

1. **新增一个 blueprint 节点 = 1 个类**。三样东西：`@NodeAttribute(name/group/graphTypes)`、用五个注解声明的字段（参数就是带初始值的字段）、覆写 `evaluate(EvalContext)` 或 `execute(ExecContext)`。不需要写任何网络/序列化代码——只要端口类型在 `AccessorRegistries` 里有 accessor，编辑器控件与 NBT 往返自动来（`graph/core/NodeMetadata.java:112-120`），否则自动降级成"只能连线"。最小实例：`blueprint/nodes/exec/ForNode.java:24-48`（25 行：5 个字段 + `execute` 一行 `ctx.pushLoop(...)` + `evaluate` 一行 `ctx.setOutput`）；带变长端口的实例 `blueprint/nodes/math/AddNode.java:19-55`。校验没有声明式 DSL，靠约定：类型不符时 `EvalContext.coerce` 返回默认而不抛（`graph/exec/EvalContext.java:482`，规则表在 `:22-33`），静态自检只有 shader 侧有 `INodeValidator`（`rendertype/compiler/INodeValidator.java:14-16`，由 `rendertype/RenderTypeGraph.java:359-371` 收集并进编辑器错误面板）。
2. **新增一个 shader 节点 = 1 个类 + 一个 `compile(ctx)`**。实例 `rendertype/nodes/math/basic/AddNode.java:9-15`——15 行、只覆写 `emit(a,b)`，因为宽度推导/端口声明在 `rendertype/nodes/math/DynamicBinaryNode.java:18-59`；基类面在 `rendertype/compiler/ShaderNode.java:30-87`（`compile` 抽象、`stageAffinity()`、`choice()/flag()` 读选项）。不写类也行：`rt_expression` 节点允许直接把 GLSL 体和端口表写在 STRING 选项里（`rendertype/nodes/logic/ExpressionNode.java:31-49`）。
3. **新增一种图 = 1 个 `Graph` 子类 + 1 个 registry + 1 个 `GraphResource`**。模板 `blueprint/BlueprintGraph.java:23-37`（registry 建在 `:25-27`，模型覆写在 `:35-37`，类型白名单在 `:44-120`）＋ 编辑器接线 `editor/BlueprintGraphResource.java:16-41`、`editor/KilaGraphEditor.java:23-30`。图之间的复用/嵌套规则是 `acceptsSubgraphGraph`（`rendertype/ShaderFunctionGraph.java:56-60`，RenderTypeGraph 只收 ShaderFunctionGraph），子图界面完全由 blackboard 变量决定（`GraphExecutor.java:53-56`、`LoopController` 同级）。
4. **求值 API**：`new GraphExecutor(graph[, EvaluationEnvironment])`（`GraphExecutor.java:337-344`）→ `evaluate(port, type)` / `runOutputs()` / `executeFrom(entry)`；宿主上下文（被驱动的实体、本 tick 的 delta）挂在 `EvaluationEnvironment` 子类上，并且必须覆写 `createChild` 才能传进子图（`graph/exec/EvaluationEnvironment.java:56-67` 的注释专门警告"不覆写就会在下一层静默变 null/0"）；单节点粒度调试用 `ExecSession`（`graph/exec/ExecSession.java:68-73,102-128,174`，含断点）；静态图每运行前 `setGraphFrozen(true)` + 多线程共享前 `PreparedGraph.seal()`（`GraphExecutor.java:2148`、`PreparedGraph.java:81-127` 的四步纪律：先单线程预热跑一遍 → seal → fork → join 后查 `sealBreached()`）。
5. **材质 API**：`RenderTypeFactory.createMaterial(graphOrCompiled)` → `RenderTypeGraphMaterial`，用 `setUniform(name,...)/setTexture(name,...)` 按**变量显示名**改 uniform/纹理而不重建 RenderType（`rendertype/runtime/RenderTypeGraphMaterial.java:24-43`），`renderType()` 交给宿主自己 submit；宿主不需要 mixin 即可用，因为 `BY_RENDER_TYPE` 侧表负责让 vanilla `draw` 找到材质（`:41-42,46-47,110-112`）。
6. **无头/程序化建图**：`test/gametest/KGGraphBuilder.java:18-42`（`wire("sqrt.in","sumSq")` 式命名引用，歧义直接抛）——文件头明说"Not a production API"，但它是本仓库唯一给出的"不靠编辑器批量造图"的完整形状，宿主可照抄语义。

## 附：结论 —— 对应重点问题 ⑥，「求仙问道」能借哪一层

（对应重点问题 ①–⑥，前面各节已给证据，这里只给结论。）

- **可借的形状 1：定义层与运行层彻底分离**（4.2、4.4 的三层状态模型）。修仙的"功法回路"若照此实现，节点类只声明端口/参数与语义，运行态一律在执行器/`VariableStore`/`nodeState` 三处，就能池化上下文、能把同一份定义同时用于编辑器预览、服务端结算、客户端表现。这条与"内容删空地基照跑"完全同向。
- **可借的形状 2：预解析 + 整数槽 + 代际 stamp**（4.3、7.1、7.4）。阵图/回路天然是"同一张图被成千上万个实例反复求值"——正是 `PreparedGraph` 的设计目标；照搬时要一并搬它的**脏检测自实现**（LDLib2/NeoForge 都不会给你 dirty 位）和"不预计算执行次数"的纪律，否则短路语义会在优化中丢失。
- **可借的形状 3：内容哈希缓存昂贵产物**（4.5、7 另记条）。若"阵图"最终编译成某种昂贵产物（shader、模型、结算表），`RenderTypeFactory` 的 hash+引用计数+失败黑名单一整套可复用。
- **不适合 47 类型数据化的部分：节点语义仍是 Java 类。** 数据化只到"实例参数"这一层：`@NodeAttribute` 的 name/group 是编译期字符串（`blueprint/nodes/mc/action/BlockActionNodes.java:38`），端口表来自 `NodeMetadata.scan` 的**反射字段扫描**（`graph/core/NodeMetadata.java:53-63`），行为是 `evaluate/execute` 的虚方法覆写（`graph/core/AnnotatedNode.java:95-105`）。新增一种节点必须写 Java 并重新编译发版；仓库里唯一的"数据定义节点"是 `rt_expression` 那种"整段 GLSL 塞进一个 STRING 选项"的逃生口（`rendertype/nodes/logic/ExpressionNode.java:31-49`），粒度是"一个万能自定义节点"，不是"每种内容类型一个数据描述"。
- **第二个不适合：图没有游戏内宿主。** 没有方块实体/物品组件/存档级 attachment 承载图（4.1、5），也没有 `Graph` 的 `Codec`/datapack 加载路径，图定义不进世界、不进版本控制、不能由 pack 作者提供。求仙问道若要求"功法回路可被 datapack 覆盖/热重载"，需要自建 KilaGraph 根本没有的那一层：`Codec<GraphDefinition>` + reload 监听 + 宿主（BE/data attachment）——**但注意它的 NBT 通道已经是 registry-ops 的 `TagValueOutput`（`editor/RenderTypeGraphResource.java:51-58`），换成 JSON 只需把同一对 `serialize/deserialize` 换成 JSON ops，改动量比想象小。**
- **可以照抄的一个观念**：MC 语义作为**端口值**流入、而不是作为**环境字段**流入（4.6，`EvaluationEnvironment` 里没有 `Level`，`McActions.java:42-45` 从端口取 level）。这让同一张图能被喂给不同世界/不同宿主，也让"这张图会在客户端被跑"成为显式设计约束而不是 bug。对 47 种内容类型共用一套求值器，这个决定值回票价。
- **不建议抄的部分**：4.2 的反射-注解定义层依赖外部库（LDLib2）的 `Node/NodeModel/GraphNodeRegistry` 与其 accessor 系统，搬走等于把半个 LDLib2 一起搬；求仙问道在 Forge 1.20.1 上没有这套底座，应该抄它的**注解语义**（五个字段注解 + 一个缓存的元数据扫描器），而不是抄它的基类层次。
