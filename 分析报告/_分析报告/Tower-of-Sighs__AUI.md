# ApricityUI (AUI) 源码分析报告

## 1. 基本信息

- mod_id `apricityui`，名称 ApricityUI，作者 Tower of Sighs，许可证 LGPL-2.1，版本 1.2.4-hotfix，group `com.sighs`（均出自根 `gradle.properties:4-10`；仓库根无 LICENSE 文件，许可证仅由该处声明）。
- 定位：一句话是"在游戏里跑一个精简浏览器"——UI 页面就是 HTML/CSS/JS（README.md:1 "Design UI with HTML, CSS, and maybe JavaScript"），JS 由 Rhino 执行（`targets/forge-1.20.1/src/main/java/com/sighs/apricityui/script/ApricityJS.java:28`，未装 KubeJS 时直接跳过脚本）。
- 目标加载器/版本（各自 `targets/<id>/gradle.properties`）：forge-1.20.1（MC 1.20.1 / Forge 47.3.0）、fabric-1.20.1、fabric-1.21.1（loader 0.16.14 / FAPI 0.116.15+1.21.1）、neoforge-1.21.1、neoforge-26.1（MC 26.1 / NeoForge 26.1.2.84，`targets/neoforge-26.1/gradle.properties:1-2`）。共 5 个发行目标。
- 工程结构：不是常见 multiloader 插件，而是"每个 target 独立 Gradle 工程 + common 共享源码树"。根 `build.gradle:1-23` 只做转发（`gradlew -p targets/<id> build`，用 `-Ptarget` 选择）；target 通过 `sourceSets.java.srcDir` + `prepareCommonSources` Sync 任务把 `common/src/main/java` 编进自己（`targets/forge-1.20.1/build.gradle:32-49`，并排除 `network/chunk/**` 用 target 自己的实现）。构建插件：Forge/legacy 用 `net.neoforged.moddev.legacyforge 2.0.91`（build.gradle:10），Fabric 用 fabric-loom 1.10.5（`targets/fabric-1.21.1/build.gradle:8`），发布用 `me.modmuss50.mod-publish-plugin 2.1.1`。
- Java 版本：forge/fabric/common 侧 toolchain 17（`targets/forge-1.20.1/build.gradle:23-26`）；neoforge-26.1 用 Java 25（`targets/neoforge-26.1/build.gradle:20`）。mixin compatibilityLevel 为 JAVA_8（`common/src/main/resources/apricityui.mixins.json:5`）。
- 编译依赖：KubeJS / Rhino / Architectury 仅 modCompileOnly（`common/build.gradle:48-50`），即软依赖；maven 发布坐标 `com.sighs:ApricityUI-forge-1.20.1:<ver>` 至 `https://maven.sighs.cc/repository/maven-releases/`（`gradle/target-conventions/publish.gradle:98-119`）。

## 2. 源码规模与包结构

实测（`find -name '*.java'` + 逐文件行数合计）：全仓 795 个 .java、149,580 行（卡片写 150,375，本次复核为 149,580，差异或来自统计口径）。分模块：

| 模块 | .java | 行数 | 说明 |
|---|---|---|---|
| common/src/main | 290 | 74,346 | 引擎主体（加载器无关的 UI 内核） |
| common/src/test | 113 | 21,401 | headless 测试（含 WPT 派生测试） |
| targets/forge-1.20.1 | 74 | 11,908 | Forge 侧适配 + 容器/物品元素 |
| targets/fabric-1.20.1 / 1.21.1 | 61 / 68 | 7,723 / 8,364 | Fabric 侧 |
| targets/neoforge-1.21.1 / 26.1 | 92 / 97 | 12,368 / 13,470 | NeoForge 侧（含 26.1 前瞻移植） |

common main 主要包（文件数）：render 31、dev 29（DevTools/热重载/外部调试）、network 26、element 24（DOM 内置元素）、canvas 22、style 18、spi 18（加载器服务接口）、util 16、behavior 15（滚动/选区/动效）、resource 12、dom 11、parser 10（HTML/CSS/Selector/JS）、layout 9、media 8（音频）、ui 7（Toast/对话框等成品组件）、task 5、init 4（Document/Element/Node/Window）、event 4、form/world/registry/container 各 3~4。

最大源文件（main，行号实测）：`init/Element.java` 3279、`render/FontDrawer.java` 2102、`dev/devtools/DevToolsController.java` 1723、`init/Document.java` 1652、`layout/Flex.java` 1631、`style/Text.java` 1291、`layout/Size.java` 1258、`canvas/CanvasRenderingContext2D.java` 1080、`parser/Selector.java` 1037；测试侧最大 `common/src/test/.../webapi/LayoutPositionTest.java` 1935。

forge target 内部再按职责分包：`forge/`（13 个 SPI 实现/引导类）、`network/`（handler、chunk、forge 网络适配 10 类）、`screen/`（ApricityScreen/ApricityContainerScreen/ApricityContainerMenu/SlotDataBinder 四件套）、`element/`（CONTAINER/SLOT/ITEM/RECIPE/INGREDIENT 等 MC 元素 6 类）、`container/`（datasource 9 类 + filter + SlotLayout）、`dom/`（expander 与槽位内容规则）、`client/`（事件路由、重载监视、自测）、`script/`、`registry/`、`world/`、`mixin/`。即 target 层只做四类事：SPI 实现、MC 事件接线、容器语义元素、mixin——这是它能在 5 个加载器间复制的结构性原因。

稀疏检出的不完整处：`common/src/main/resources` 只剩 `apricityui.mixins.json`、`kubejs.plugins.txt` 和 `assets/apricityui/apricity/apricityui/theme/` 下的 license/readme/theme-spec 三个文档——主题核心 `ore.css`、`example.html`、`global.css` 均不在本地（docs/getting-started.md:183-187 引用了它们，内容未验证）；各 target 的 src 下除 java 仅见 `META-INF/mods.toml` 与 `accesstransformer.cfg`（forge）。因此本报告的资源层结论只依据 java 代码与 docs。阅读取舍：细读 init/render/loader/network/forge 适配与 mixin；canvas、media、form、world 仅按包略读。

## 3. 入口与注册

Forge 入口 `targets/forge-1.20.1/src/main/java/com/sighs/apricityui/forge/ApricityUIForge.java:28-49`：

```java
@Mod(ApricityUI.MODID)
public class ApricityUIForge {
    public ApricityUIForge() {
        AuiLogging.installFileAppender();
        AuiServicesBootstrap.init();                       // 注册 SPI 实现（网络/配置/脚本/expander）
        if (FMLEnvironment.dist == Dist.CLIENT) ClientServicesBootstrap.init(modEventBus);
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, ApricityUIConfig.CLIENT_SPEC);
        ApricityUIRegistry.scanPackages("com.sighs.apricityui.element", "com.sighs.apricityui.element");
        ApricityMenus.register(modEventBus);               // DeferredRegister 注册容器菜单类型
        NetworkManagerImpl.installAutoRegistrationHook();
        NetworkAutoRegistration.findAllAnnotatedPackets(); // 扫描 @NetworkPacket 注解自动注册包
```

加载器无关的公共门面是 `common/src/main/java/com/sighs/apricityui/ApricityUI.java:24-177`（createDocument/screen/menu/createWorldWindow）。SPI 实现通过 `spi/AuiServices.java:31-45` 的静态 holder 注入，未注入时落到安全 Defaults，且首次访问会懒触发 `AuiServicesBootstrap` 的 static 块（`forge/AuiServicesBootstrap.java:14-22`），headless 测试因此可跑。自定义 DOM 元素注册是注解式：`@ElementRegister("CONTAINER")` + 包扫描反射实例化（`registry/ApricityUIRegistry.java:24-41`、forge 侧 `element/Container.java:17-22`）。

事件总线订阅点集中在 forge `client/Client.java`：`ScreenEvent.Render.Post`（195）、`RenderGuiEvent.Post` 画 overlay 文档（218-232）、`InputEvent.MouseButton.Pre`（301）、`InputEvent.Key`（341）、`ScreenEvent.CharacterTyped.Pre`（294）、`TickEvent.ClientTickEvent` 驱动 `FrameScheduler.tick()`（449-456）、`RenderTickEvent` 每渲染帧派发 mousemove（332-335）。键位在 `registry/Keybindings.java:15-60` 注册（RELOAD/DEV_TOOLS/RESOURCE_MANAGER 默认 UNKNOWN，RELEASE_MOUSE 默认左 Alt）；文档宣传的 F10/F12/END 是作者约定的键位绑定（docs/getting-started.md:34），代码内无硬编码 F 键（未验证到反例）。

## 4. 核心系统

### 4.1 UI 描述与解析：真·HTML/CSS/JS，非 XML/JSON/builder

页面就是普通 HTML 文件。解析层手写：

- HTML：`parser/HTML.java:300-337` 是 Token + HtmlTokenizer 词法器；`parser/CSS.java:179` 的 `CSS.Extractor` 抽取 `<style>`/外链 CSS 并缓存进 `Document.CSSCache`（Document.java:79）；`@keyframes` 用正则抽取解析（CSS.java:282-343）。
- 选择器带 CSS 规范级 specificity：`parser/Selector.java:109`（"three selector-specificity columns"）、`:210-213`（:is/:not 继承内部 specificity）、`:331` 起 `Selector.Index` 按文档建规则索引，匹配结果按 specificity 排序、important 同属性再压一层（`:472-479`）。
- 布局表达：盒模型（`layout/Box.java` 947 行）+ flexbox 全套（`layout/Flex.java:45-56` direction/wrap/align-content/justify-content/align-items，`:83-84` wrap-reverse，`:115` computeChildPosition，`:133` computeContentSize）+ 绝对定位（Size/Position 体系）+ 关键字值缓存避免重解析（Flex.java:59-70 `Flex.of` 命中即复用）。
- 动画：CSS transition/animation 完整支持，时间基是渲染帧而非 MC 的 20Hz tick（`render/Base.java:266-268` 注释），采样在 `behavior/MotionTrack.java:25`，连"继承色的 transition 要后合成否则文字冻在白帧"这种边角都有处理（:162-165）。
- 附加能力：`<canvas>` 2D 上下文（fillRect/beginPath/drawImage，`canvas/CanvasRenderingContext2D.java:254-731`）、SVG 类元素（`element/Svg.java`、`Path.java`、`Sprite.java`）、音频（`media/`，AudioEngine 每帧推进，FrameScheduler.java:28）。
- MC 语义扩展标签 `CONTAINER/SLOT/ITEM/RECIPE/INGREDIENT` 不在 common，而是编译在各加载器 target 内、用同一注解机制注册（forge `element/Container.java:17-22`）——通用引擎与 MC 语义的切分线非常清楚。

### 4.2 渲染管线：旁路 GuiGraphics，自建绘制列表 + SPI 抽象的顶点层

Screen 只把 GuiGraphics 当 pose 容器与 flush 点：`forge/screen/ApricityScreen.java:114-130` 推 pose、按视口 scale、调 `Base.drawScreenDocument(poseStack, doc)`，随后 `bufferSource().endBatch()` 与两次 `guiGraphics.flush()`。

- 两趟式绘制：先在逻辑侧把带 z-index/stacking context 的 DOM 烘焙成线性绘制列表（`render/Drawer.java:27 flushUpdates → :96 updatePaintList → :148 processStackingContext`，负 z 子树提升 `:338 hoistPaintedDescendants`；出口 `Document.getPaintList()` Document.java:563），渲染帧只顺序遍历 `node.render(poseStack)`（`render/Base.java:307-344`），配子树整体裁剔（节点不可见或几何与当前裁剪区不相交即跳过整棵子树，`shouldSkipSubtree` Base.java:433-447）与逐帧缓存表（Rect/Transform/Style/Measure 四个 cache begin，:243-247）。
- 帧内叠放顺序是一张具名 z 常量表：物品模型 150、装饰 200、前景 200.125、漂浮物更高，每张"平面文档"占一个 `FLAT_DOCUMENT_LAYER_STEP` 台阶（`render/GuiItemDepths.java:5-11`，`Base.java:36-42,186-202`）；top-layer 弹屏作为独立浏览器表面隔离深度栈（`Base.java:324-335,385-399`）。
- 绘制原子操作不直接用 MC 的 RenderType/GuiGraphics，而是走 `spi/AuiRenderService.java:41-47` 的 beginMesh/submitMesh/beginTextureBatch，由各 target 实现：forge `RenderService.java:77-98` 用 Tesselator BufferBuilder + BufferUploader.drawWithShader，贴图批用 `MultiBufferSource.BufferSource` 配自造 `RenderType`（`forge/render/SmoothRenderType.java:16-22`，linear 过滤 + 可选 blur/深度变体）；RenderSystem 全局状态（投影、深度、混合）也被抽象进 SPI（`RenderService.java:47-74`），这正是它能平移移植到 neoforge-26.1 的原因。
- 字体自绘：FontDrawer 后台把字形光栅成动态纹理限量上传，完成前用原版字体回退（`Base.java:241-242`）。
- 节奏控制：20Hz tick 提交布局（`common/task/FrameScheduler.java:35-39` 遍历 `document.tickFrame()`），渲染帧入口再强制补交 pending 样式/布局——注释直接写明了动因：布局提交 20Hz 而绘制每帧，不补交则光标 caret 读到旧几何画在 (0,0)（`Base.java:251-265`）；滚动只平移子树走快速路径，避免每帧全量 Rect 重建（:274-286，注释标注了 JFR 归因）。

### 4.3 组件生命周期与事件系统

`Document.refresh()`（`init/Document.java:343-438`）是完整的重挂载流水线，逐阶段计时打日志（慢刷新自动分段上报，:440-465）：

- 顺序：清缓存/清树 → HTML/CSS/JS 抽取重建 DOM → 初次样式计算 → 调 `AuiServices.expander().apply(this)`（:384，加载器注入的文档扩展器，forge 侧 `dom/ForgeDocumentExpander` 挂 ContainerExpander/RecipeExpander）→ 最终样式 + 烘焙绘制列表 + 图片预取 → 跑全局/页面 JS → 依序触发 `DOMContentLoaded`→interactive→`load`（:410-412，状态机 :516-526）。
- 代次与失效：每次 refresh 递增 `refreshGeneration`（:507-514），异步回调须用 `isCurrentGeneration(gen)` 验尸再写（:917；二次开发文档把它列为第一纪律，docs/guide/secondary-development.md:22-31）。卸载走 `disposeLifecycle`（:528-532，清 MutationObserver、停音频）。
- 增量更新：`Element.setTextContent/setAttribute` 等只把 `RELAYOUT|REPAINT|REORDER|HITTEST` 位掩码标到最近布局根（`init/Element.java:350,1591-1619`；`render/DirtyFlags.java`），不触发全文档重建；MutationObserver 有独立 queue/flush（`dom/MutationObserverManager.java:33-43`）。
- 事件是浏览器语义：capture → AT_TARGET → bubble 三阶段（`event/Event.java:148-199`），单个 listener 抛异常被捕获记录、不中断派发（:304-307）。

### 4.4 输入绑定与容器/跨端流转

输入从 MC 事件转成"可信" DOM 事件（命中测试 `Document.hitTest` Document.java:572）：

- `render/Operation.java:41-53` 鼠标按下先给 DevTools 拾取模式让位，再构造 `MouseEvent.setTrusted(true)` 派发；mousemove 按坐标缓存去重（:97-108），keydown 有 5ms 同源去抖（:584-599）；文本输入、富文本编辑（方向键选区/undo/redo/内部 HTML 剪贴板）、select/button 键盘激活全在 `Operation.onKeyPressed`（:167-423）；"游戏内没有 Screen 也要收字符"靠第 6 节的 KeyboardHandler mixin。
- 服务端开容器屏：`ApricityUI.menu(player, path).bind(b -> b.blockEntity(pos).player())`（`ApricityUI.java:79-81` → forge `PendingMenu.java:28-41` → `BindingBuilder.java:54-99` 生成 ContainerDeclaration + 按 CSS 选择器的槽位过滤 :108-111），`ApricityScreenNetworkHandler.openScreenFromServer` 用 `NetworkHooks.openScreen` 把 `SlotLayout` 序列化进 `ApricityContainerMenu`（handler :273-285；menu :26-43，客户端反序列化构造 :39-43）。
- 客户端页面加载后：`SlotDataBinder` 扫描 DOM 里的 `<slot>/<item>` 与菜单槽位绑定同步（forge `screen/SlotDataBinder.java:50-80`，`<ingredient>` 只作展示不覆盖真实槽位）；`ContainerExpander` 在 refresh 期把 `repeat`/`size`/`bind=player` 属性展开成真实槽位节点（forge `dom/expander/ContainerExpander.java:23-49`）；纯客户端页面也能反向发 `OpenScreenRequestPacket`（容器声明随 DOM 解析上云，`common/network/packet/OpenScreenRequestPacket.java:13-27`）；过滤器可解析性由客户端回发 `ResolveSlotFiltersPacket` 在服务端补全（handler :231-269）。
- 原版容器屏渲染被 mixin 整体接管（取消 renderSlot/highlight/floatingItem，见第 6 节），物品由 `ItemRenderService` 以原版 PoseStack 模型管线重绘、并复刻 Forge 装饰器接口（forge `ItemRenderService.java:21-40` 引用 `ItemDecoratorHandler`/`IClientItemExtensions`）。

### 4.5 资源分层与热重载

逻辑路径系统：所有页面按 `<游戏目录>/apricity/**` 寻址，文件系统覆盖资源包 `apricity/`，再回退 jar 内 `assets/apricityui/apricity/`（`loader/Loader.java:63-71`、`loader/ClientLoader.java:161-174,208-223`）——mod 作者写页面不需要打包。

- END 全量重载 `ClientLoader.reload()` 刻意延后 2 帧、显示 Toast、并合并期间的重复请求（:41-65）；重载序列是一份"缓存失效清单"：脚本引擎 → 异步任务代次 → CSS 编译表/Selector 编译表 → 图片 RenderType 缓存/字体缓存 → 预热模板样式 → `Document.refreshAll()`（:72-119）。
- 分级热重载：CSS 单独改动走 `refreshStyles()` 只重挂样式不重建 DOM、页面状态全保留（`Document.java:334-341`）；开发期 `autoReload` 用 500ms 轮询 + 1s 节流监控文件修改时间（forge `client/DebugReloadWatcher.java:23-49`）。
- 外围工具链：游戏内 DevTools（DOM 树/样式检视/写回源文件，`dev/devtools/` 12 类）、WebSocket 外部调试服务（`dev/debug/ExternalDebugServer.java`，配置 `remoteDebug` 门控）、每秒自动截图供 AI 自查（`client/DebugAIScreenshotTicker.java`，配置项见第 5 节）。布局正确性用 Web Platform Tests 语料做回归基准（`wpt/README.md:3-11`，语料刻意不进 git）。
- 异步资源是独立一档管线：图片/样式/音频各有 async handler，解码在后台、提交统一在 `FrameScheduler.tick` 开头限量入队应用（`common/task/FrameScheduler.java:25-29`；页面加载时 `ImageAsyncHandler.prefetchImages`，`Document.java:395`），纹理上传是 fenced task、在渲染边界 drain（`Base.java:237-242`）。

### 4.6 视口模型与四种宿主

页面通过 `<meta name="aui-viewport">` 声明逻辑视口：`window/native`（浏览器式、随窗口变宽）、`browser/css`（固定逻辑宽缩放适配）、`fixed`（显式尺寸），外加 zoom/min-zoom/max-zoom/user-scalable 参数（`viewport/ApricityViewport.java:27-38,67-73`）。Screen 在 render 里对 pose 整体 `scale(renderScale)` 并推送 scissor 比例（forge `ApricityScreen.java:117-118`），布局坐标从此与 MC 像素密度解耦——这是"同一页面在任意分辨率下版式不崩"的机制；Ctrl+滚轮/Ctrl+±/0 缩放被 Screen 拦截后转发给文档（:138-163）。

- Overlay 宿主不建 Screen：注册为"常驻屏幕文档"，由 forge 的 `RenderGuiEvent.Post` 在原版 HUD 之上逐文档调 `Base.drawOverlayDocument`（`client/Client.java:218-232,246-256`；`render/Base.java:88`），HUD 页面不需要容器也不需要 Screen。
- WorldWindow 宿主由 target 的世界渲染钩子驱动：forge 订阅 `RenderLevelStageEvent`，仅在 `AFTER_TRANSLUCENT_BLOCKS` 阶段对每个窗口调 `window.render(pose, projection, partialTick)`（forge `world/WorldWindowRenderer.java:22-28`），"用哪个事件、传哪些矩阵"留在 target、渲染逻辑在 common（该文件 :10-15 注释）；common 侧 WorldWindow 自带深度台阶、准星遮挡射线测试与超距缓冲带（`world/WorldWindow.java:29-45`，配合配置 worldWindow* 项）。
- 成品组件层 `ui/`：Tooltip/Toast/对话框/右键菜单/取色器本身就是 AUI 页面——`ui/Tooltip.java:85` 持有一个 Document、固定 `Z_INDEX = 11000`（:18），框架自己吃自己的 dogfood。卡牌 mod 的悬停详情/抽卡横幅可直接借"组件=独立小文档+固定 z 段"的做法，而不必在宿主 Screen 里手写 render。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 自研网络抽象而非 vanilla CustomPacketPayload：包用 `@NetworkPacket(modId, id, side)` 注解声明 record（`network/api/NetworkPacket.java`），Forge 侧经 `ModFileScanData` 自动注册（`network/forgeutil/ForgeAnnotationScanner.java`）。已知包：`open_screen`、`close_container`、`resolve_slot_filters`、`generic_chunk`（UUID 会话分片 + GenericChunkAssembler 组包，forge `network/chunk/GenericChunkPacket.java:14-24`，common 版被 forge 构建排除改用 target 实现）。序列化是注解驱动 record codec（`network/serialization/NetworkRecordCodecBuilder.java`、`JsonCodec.java`）。
- UI 描述完全数据驱动但走资源包/文件系统而非 datapack：HTML/CSS/JS/图片全在 `apricity/` 命名空间；配方展示由 `RecipeExpander` 读原版 RecipeManager 展开（forge `dom/expander/RecipeExpander.java`）。主题（Ore）也只是一组 CSS 资源，可用变量覆写（docs/getting-started.md:79-93）。
- 页面级配置只有三个 `aui-*` meta（viewport、mouse-events 拦截、charset），其余全在 CSS/JS——"配置即 HTML 头"让同一文件在四种宿主下通用（getting-started.md:67-69、Document.java:347）。表单侧带迷你实现：`form/` 包有 FormData/FormDataEntry/ConstraintValidator/ValidityState（HTML 表单校验与提交数据收集，`form/FormDataEntry.java:4-11`），规模小但结构完整。
- 配置：Forge 仅 CLIENT 节 TOML（`config/apricityui-client.toml`）：debugAutoReload、aiAutoScreenshot（每秒截图给 AI 自查）、frameTimingHud、remoteDebug、worldWindow 深度/LOD 参数等（forge `config/ApricityUIConfig.java:19-43`），改配置经 `ModConfigEvent.Reloading` 标脏（`ApricityUIForge.java:51-54`）。
- datagen：无。全仓找不到 GatherDataEvent/DataGenerator 挂点；forge 构建里的 `data` run 只是模板残留（`targets/forge-1.20.1/build.gradle:133-137`）。
- 构建期验证工程（对写多加载器 mod 的人参考价值高，全在 `targets/forge-1.20.1/build.gradle`）：`verifyReobfuscatedJar` 用手写 class 常量池解析器检查产物 jar 里 `ClientMenuScreens.class` 是否仍调用 dev 映射名 `MenuScreens.register`、必须存在 SRG 名 `m_96206_`（:244-351）——reobf 泄漏在 CI 直接失败；`clientTest` 把真实 MC 客户端当测试运行器，靠系统属性让 `ClientRuntimeSelfTest` 写出 PASS 文件再由 Gradle 验收（:476-512）；headless 测试维护一份"client-only 用例清单"，skip 集合与清单不一致即报错（:445-474）。

## 6. Mixin

单一配置 `common/src/main/resources/apricityui.mixins.json`：无服务端段（`mixins` 数组为空），`client` 两个（:7-12），compatibilityLevel JAVA_8，refmap `apricityui.refmap.json`（forge 构建经 `mixin{}` 块与 jar manifest `MixinConfigs` 双重挂接，`targets/forge-1.20.1/build.gradle:152-161`）。

1. `CommonKeyboardHandlerMixin`（common，注入 `KeyboardHandler`）：`@Inject charTyped @At("HEAD")` 可取消——在没有 MC Screen 时把 Unicode 字符也派发给 AUI 文本控件，注释解释了为何自带版本中立的合法字符谓词而非 shadow SharedConstants/StringUtil（`CommonKeyboardHandlerMixin.java:13-29`）。
2. `AbstractContainerScreenMixin`（forge target，注入 `AbstractContainerScreen`，同包不同源树）：`@Invoker recalculateQuickCraftRemaining` 复用原版快移状态机；四个 `@At("HEAD")` 可取消注入点——`renderSlot`（Apricity 容器屏内取消原版槽位绘制并修剪无效快移槽）、`renderSlotHighlight`（Forge 补丁方法无 SRG 名，显式 `remap=false`）、`renderFloatingItem`（把拖拽漂浮物捕获给 AUI 重绘）、`isHovering(Slot,DD)`（命中判定改由 AUI 几何接管），各见 `:29-70`。注释里"refmap 只有方法映射、shadow 字段会在生产环境崩"是实打实的 1.20.1 踩坑记录（:19-24）。
3. 其余 target 各带自己的 mixin 集：fabric-1.21.1 有 `AbstractContainerScreenMixin`、`KeyboardHandlerMixin`、`MouseHandlerMixin`、`RenderTargetAccessor`、`RenderTargetStencilMixin`（目录实测；Stencil 在 fabric 用 mixin 补，forge 侧走 RenderSystem/AT），其对应的 mixins json 未随稀疏检出提供（未验证）；neoforge-26.1 自带 `AbstractContainerScreenMixin` 与 `CommonKeyboardHandlerMixin` 的适配副本，其 `prepareCommonSources` 显式排除 common 版 mixin（`targets/neoforge-26.1/build.gradle:40-45`）。共同模式：mixin 只用来"接管原版 GUI 输入与绘制边界"，不做任何数据注入。

另有 `accesstransformer.cfg` 且 `validateAccessTransformers = true`（`targets/forge-1.20.1/build.gradle:54-57`）。

## 7. 值得学的 5 条

1. 两趟式帧管线 + "绘制前强制补交布局"：20Hz 只提交脏子树，渲染帧入口再补 pending 样式并区分 layout/scroll/geometry 三档重建成本（`common/src/main/java/com/sighs/apricityui/render/Base.java:251-300`）。卡牌悬停动画、拖影、tooltip 全都会踩"状态改了半帧旧几何"这个坑，这段是最直接的解法范本。
2. 帧内 z 层用一张具名常量表管死：物品 150/200/200.125、漂浮物更高、每层平面文档一个 `FLAT_DOCUMENT_LAYER_STEP` 台阶（`common/.../render/GuiItemDepths.java:5-11` + `Base.java:186-202`）。多卡格 GUI 里"卡面/角标/悬浮卡/弹层"的叠放顺序从此不需要在每个 render 里手算，抄表即可。
3. 代次守卫（generation guard）的异步→DOM 纪律：refresh 换树后旧引用静默作废，所有异步回调用 `isCurrentGeneration` 验尸再写（`common/.../init/Document.java:507-514,917`；成文规范见 `docs/guide/secondary-development.md:22-31`）。卡牌翻面/抽卡表演大量依赖异步资源就绪回调，这条零成本可移植。
4. 热重载的"分级失效清单"：CSS-only 改动只重挂样式保状态、HTML 改动重建文档、全量重载按 ClientLoader.reloadResourcesInternal 的固定清单逐个清缓存（`common/.../loader/ClientLoader.java:72-119`、`Document.java:334-341`）。这份清单本身就是 GUI 框架"哪些缓存必须成对失效"的活文档，比任何工具本身值得抄。
5. 加载器中立 SPI + 源码树共享的多加载器方案：`spi/AuiServices.java:31-45` 的静态 holder 带安全默认值和懒引导，同一份 common 源码经 srcDir 编进 5 个 target（`targets/forge-1.20.1/build.gradle:32-49`），没有 multiloader/architectury 插件。对同时维护 Forge 1.20.1 与 NeoForge 1.21.1 的作者是眼下最省事的跨加载器路线。

不该学的 1 条：浏览器兼容面本身。`Operation.onKeyPressed`（`render/Operation.java:167-423`）一个方法 250 余行 if 链，为 Input/TextArea/RichText/Select 实现了光标选区、undo/redo、内部 HTML 剪贴板等完整文本编辑栈，加上 MutationObserver、:is() specificity、WPT 语料回归——这是"做浏览器"的目标函数，卡牌 GUI 不需要 contenteditable；照搬会把维护成本烧在用户永远写不出来的能力上。学它的管线分层，别学它的兼容面。

## 8. 公开 API

- 入口包 `com.sighs.apricityui`：门面类 `ApricityUI.java`（`getWindow/createDocument/screen/menu/closeScreen/createWorldWindow`，:31-139）；`init.Document`/`init.Element`/`init.Window` 即面向脚本与 Java 的 DOM API。
- 扩展点：`registry/annotation/ElementRegister.java` + 自定义 Element 子类（覆写 `onInitFromDom`/`drawPhase`，示例 docs/guide/secondary-development.md:33-52）；`dom/DocumentExpander`（refresh 期注入 MC 语义，`Document.java:384`）；`spi/` 18 个服务接口（render/network/script/resource/key/item/audio/config/client）是加载器作者的移植面；KubeJS 绑定注解 `@KJSBindings`（secondary-development.md:77-80）；宿主四种：Screen / Overlay / 容器 Screen / WorldWindow（getting-started.md:98-104）。
- 接入方式（作为依赖使用，非 fork 合入）：

```groovy
repositories { maven { url "https://maven.sighs.cc/repository/maven-public/" } }
dependencies { implementation 'com.sighs:ApricityUI-forge-1.20.1:1.2.0' }  // getting-started.md:12-22
```

最小接入：把页面放进资源包 `assets/<你的ns>/apricity/screens/hello.html`（或开发期直接 `<游戏目录>/apricity/`），页面就是标准 HTML——头部 `<meta name="aui-viewport" content="mode=browser">` 与 `<meta name="aui-mouse-events" content="intercept">` 两个声明，脚本里 `document.getElementById("btn").addEventListener("click", ...)`（完整可运行示例见 docs/getting-started.md:40-64）。客户端纯展示 `ApricityUI.screen("screens/hello.html")`；带背包容器则服务端一行：

```java
ApricityUI.menu(player, "screens/hello.html").bind(b -> b.blockEntity(pos).player());
// PendingMenu.java:12-14 的文档示例；绑定步骤链见 BindingBuilder.java:25-41
```

页面内与外部代码共享同一套 DOM API（`getElementById/querySelector/setTextContent/setAttribute/addEventListener`，getting-started.md:107-131）。注意两点：JS 段落依赖运行时装有 KubeJS 才会执行（ApricityJS.java:28）；`getDocument(path)` 返回实例列表且刷新即失效，外部持有要存代次。
