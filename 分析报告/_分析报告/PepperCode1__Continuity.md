# Continuity 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / id | Continuity / `continuity` |
| 作者 | PepperCode1 |
| MC / 加载器 | 1.20.1 / Fabric（loader 0.17.3，yarn 1.20.1+build.10） |
| 版本 / 许可证 | 3.0.1 / LGPL-3.0-only |
| Gradle | fabric-loom 1.12.7，Java 17，`maven_group = me.pepperbell`，`archives_base_name = continuity` |
| 编译依赖 | fabric-api 0.89.0+1.20.1（必需，也是渲染 API 提供者）；modmenu 7.2.2（modImplementation，TerraformersMC maven）；canvas 20.0.2625（`modCompileOnly`，maven.modrinth） |
| environment | `client`（纯客户端，无服务端类） |

数据来源：`gradle.properties`、`build.gradle`、`settings.gradle`。**注意**：本 bulk 副本工作区缺少 `src/main/resources/fabric.mod.json` 与 `assets/`（仅有 `continuity.mixins.json` 与 resourcepacks），metadata 需用 `git show HEAD:src/main/resources/fabric.mod.json` 读取：entrypoints `client → me.pepperbell.continuity.client.ContinuityClient`、`modmenu → ...client.config.ModMenuApiImpl`，depends `minecraft 1.20.1 / fabricloader >=0.15.0 / fabric-api >=0.89.0`。

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **102 个 java 文件，8231 行**；`resourcepacks/` 目录 git 跟踪 1779 个文件（内置两个资源包）。按包（第 3 层）文件数：

`client/processor` 12、`client/mixin` 12、`client/resource` 11、`client/processor/simple` 10、`api/client` 10、`client/properties` 9、`client/util` 7、`impl/client` 6、`client/properties/overlay` 6、`client/model` 4、`client/config` 4、`client/util/biome` 4、`client/processor/overlay` 3、`client/mixinterface` 3、`client/`（根，仅 ContinuityClient）1。

最大的 9 个文件：`client/properties/BaseCtmProperties.java`(737)、`client/processor/CompactCtmQuadProcessor.java`(687)、`client/processor/overlay/StandardOverlayQuadProcessor.java`(403)、`client/properties/PropertiesParsingHelper.java`(310)、`client/ContinuityClient.java`(273)、`client/model/EmissiveBakedModel.java`(240)、`client/model/CtmBakedModel.java`(197)、`client/model/QuadProcessors.java`(175)、`client/util/QuadUtil.java`(174)。

## 3. 入口与注册

入口 `src/main/java/me/pepperbell/continuity/client/ContinuityClient.java:56`。没有物品/方块注册（纯客户端），其"注册"是**字符串 method → CTM 加载器**的表：

```java
ProcessingDataKeyRegistryImpl.INSTANCE.init();
BiomeHolderManager.init(); ProcessingDataKeys.init();
ModelWrappingHandler.init(); RenderUtil.ReloadListener.init();
CustomBlockLayers.ReloadListener.init();
// 内置资源包（Fabric API）
ResourceManagerHelper.registerBuiltinResourcePack(asId("default"), container, ..., NORMAL);
ResourceManagerHelper.registerBuiltinResourcePack(asId("glass_pane_culling_fix"), container, ..., NORMAL);
// method 注册：ctm/glass/ctm_compact/horizontal/bookshelf/vertical/horizontal+vertical/
// vertical+horizontal/top/random/repeat/fixed + overlay 系列（overlay_ctm/overlay_random/...）共 21 个
registry.registerLoader("ctm", createLoader(OrientedConnectingCtmProperties::new,
        new TileAmountValidator.AtLeast<>(47), new SimpleQuadProcessor.Factory<>(new CtmSpriteProvider.Factory())));
```

`createLoader(propertiesFactory, validator, processorFactory, isValidForMultipass)`（同文件 :218-259）把四件套组合成 `CtmLoader`：`CtmProperties.Factory`（解析 properties）+ `TileAmountValidator`（tiles 数量校验）+ `QuadProcessor.Factory`（生成处理器）+ `CachingPredicates.Factory`（多 pass 有效性）。`wrapWithOptifineOnlyCheck` 让带 `optifineOnly=true` 的包在非 OptiFine 场景下跳过。

## 4. 核心系统

**A. 资源包驱动的 CTM 定义加载** `client/resource/CtmPropertiesLoader.java`
- 遍历 `resourceManager.streamResourcePacks()`，`packPriority` 递增记录包顺序（:58-73），再用 `containers.sort(Comparator.reverseOrder())` 让高优先级包覆盖低优先级（`BaseCtmProperties.compareTo` :104 比较优先级与 resourceId）。
- 用 `pack.findResources(CLIENT_RESOURCES, namespace, "optifine/ctm", ...)` 递归抓取所有 `.properties`，`properties.getProperty("method", "ctm")` 查 `CtmLoaderRegistry`，未知 method 打 error（:91-99）。
- 关键设计：加载时顺带收集**纹理依赖表** `Map<atlasId, Set<textureId>>`（:106-109），供图集在 stitch 前预加载 sprite。

**B. 精灵图集(sprite atlas)集成 / 任意纹理重定向** `client/resource/ResourceRedirectHandler.java` + 4 个 ThreadLocal context
- 保留路径前缀 `textures/continuity_reserved/<8位hex>.png`：`getSourceSpritePath` 把任意绝对路径登记进 `ObjectList<RedirectInfo>` 并返回 hex 索引 id；`redirect()`（:64）解析 hex 后还原真实路径（支持扩展名后缀追加）。配套 `IdentifierMixin`（hook `Identifier.isPathValid`）+ `InvalidIdentifierStateHolder` 临时放行非法路径。
- `AtlasLoaderMixin` 在 `AtlasLoader.<init>` 用 `@ModifyVariable` 把 `SingleAtlasSource(extraId)` 插到 sources 头部（:33-54），从而把 CTM 用的额外贴图 stitch 进方块图集；`SpriteLoaderMixin` 用 `@ModifyArg` 包裹 `SpriteLoader.load` 内部的 `supplyAsync`/`thenApply` lambda（:36、:62），把 ThreadLocal 上下文带进 vanilla 的异步图集线程。

**C. 发光(emissive)纹理** `client/resource/EmissiveSuffixLoader.java` + `client/model/EmissiveBakedModel.java`
- 图集阶段：遍历所有 sprite id，找同图集内 `<id>_e` 纹理（默认后缀），命中则追加 sprite 供应器并记录 `emissiveIdMap`；`SpriteLoaderMixin` 在 `stitch` RETURN 处把两个 Sprite 关联（`((SpriteExtension) sprite).continuity$setEmissiveSprite(...)`，`SpriteMixin` 只加一个 `@Unique` 字段，零注入）。
- 渲染阶段：`EmissiveBakedModel` 用 Fabric Renderer API `MaterialFinder.emissive(true).disableDiffuse(true).ambientOcclusion(TriState.FALSE)` 造材质（:38），quad transform 中把基础 sprite 换成 emissiveSprite 并以 `QuadUtil.interpolate` 换算 UV；对外由 `EmissiveSpriteApi.get().getEmissiveSprite(sprite)` 暴露。

**D. 模型包装（Fabric ModelLoadingPlugin）** `client/resource/ModelWrappingHandler.java`
- `ModelLoadingPlugin.register(ctx -> ctx.modifyModelAfterBake().register(WRAP_LAST_PHASE, ...))`（:70-81），在最后一个包裹阶段套 `CtmBakedModel` / `EmissiveBakedModel`；是否能包 CTM 取决于 `ModelIdentifier → BlockState` 映射（`createBlockStateModelIdMap` 复制 `BakedModelManager#bake` 的遍历逻辑，:40-51）。
- 包装器只持有 handler（`ModelLoaderMixin` 注入 `@Unique` 字段 + `ModelLoaderExtension` 接口传递，:11-27）。

**E. 四边处理管线** `client/model/CtmBakedModel.java`
- 自定义 `RenderContext.QuadTransform`（`CtmQuadTransform`），`emitBlockQuads` 里 `context.pushTransform(...)` → 让原模型吐 quad → `popTransform` → 把额外 quad `outputTo(context.getEmitter())`（:68-76）。
- 每个 quad 最多迭代 `PASSES = 4` 个 pass（pass 0 = 普通处理器，之后 = multipass 处理器），返回枚举 `ProcessingResult{NEXT_PROCESSOR, NEXT_PASS, STOP, DISCARD}` 控制流向（:132-162）。`useManualCulling` 走 `renderContext.isFaceCulled(quad.cullFace())` 自行剔除面。外观状态用 `state.getAppearance(blockView, pos, Direction.DOWN, state, pos)`（:66，代码注释解释了为何不能用相邻方块做 source）。

**F. 处理器选择缓存** `client/model/QuadProcessors.java`
- 两级 `Reference2ReferenceOpenHashMap`（BlockState → Sprite → `Slice`），全部用 `StampedLock.tryOptimisticRead()` 乐观读 + 失败回落读锁/写锁的模式（:64-103、:125-164），热路径无锁。
- `computeSlice` 用 `CachingPredicates.affectsBlockStates/affectsBlockState/affectsSprites/affectsSprite/isValidForMultipass` 过滤，产出 `processors` 与 `multipassProcessors` 两个数组（:23-47）。

**G. 自定义方块层（custom block layers）** `client/resource/CustomBlockLayers.java`
- 读取 `optifine/block.properties` 的 `layer.solid|cutout|cutout_mipped|translucent`（值为方块状态谓词）+ `disableSolidCheck`，由 `RenderLayersMixin` 在 `RenderLayers.getBlockLayer` / `getMovingBlockLayer` 的 `@At("HEAD")` cancellable 注入直接改返回层（:14、:26）。这是 OptiFine 独有的"资源包换渲染层"能力实现路径。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无**（纯客户端，无 `ClientPlayNetworking`、无 payload 注册）。
- **数据驱动**：`assets/<ns>/optifine/ctm/**.properties`（属性键实测含 `method/matchBlocks/matchTiles/tiles/connect/faces/biomes/tintIndex/tintBlock/layer/innerSeams/linked/prioritize/randomLoops/weights/width/height/heights/minHeight/maxHeight/optifineOnly/resourceCondition/name`）与 `optifine/block.properties`。另有两个内置资源包：`resourcepacks/default`（玻璃/砂岩/书架连接纹理）+ glass pane culling fix。
- **配置**：`client/config/ContinuityConfig.java` 单例，落盘 `config/continuity.json`，`Option.BooleanOption` 4 项 `connected_textures / emissive_textures / custom_block_layers / use_manual_culling`（:38-41）；`ContinuityConfigScreen` + `ModMenuApiImpl` 提供 GUI。
- **datagen：无**（仓库无 `src/main/generated` 与 datagen 入口）。
- **运行时开关 API**：`api/client/ContinuityFeatureStates` + `impl/client/ContinuityFeatureStatesImpl`，第三方 mod 可在运行时 `enable()/disable()` 连接纹理与发光纹理（`CtmBakedModel:40` 每帧查询）。

## 6. Mixin

配置 `src/main/resources/continuity.mixins.json`（`required: true`、`compatibilityLevel JAVA_17`、`defaultRequire: 1`、`package me.pepperbell.continuity.client.mixin`，共 12 个 client mixin）。代表目标：

| 类 | 目标 / 注入 |
|---|---|
| `SpriteLoaderMixin` | `SpriteLoader.load(ResourceManager,Identifier,int,Executor)` 的 `supplyAsync`/`thenApply`（`@ModifyArg` index=0）+ `stitch(...)` `@At("RETURN")` |
| `AtlasLoaderMixin` | `AtlasLoader.<init>(List)` `@ModifyVariable`(LOAD, argsOnly)；`loadSources(ResourceManager)` `@At(INVOKE ImmutableList.builder, locals=CAPTURE_FAILHARD)` |
| `BakedModelManagerMixin` | `reload(...)` HEAD/RETURN + `@ModifyReturnValue`；`bake(Profiler,Map,ModelLoader)` HEAD；`upload(...)` RETURN |
| `LifecycledResourceManagerImplMixin` | 构造器 TAIL + `getResource`/`getAllResources` 入参 `@ModifyVariable`（重定向查询）|
| `NamespaceResourceManagerMixin` | `getMetadataPath(Identifier)` HEAD/TAIL |
| `IdentifierMixin` | `Identifier.isPathValid(String)` HEAD cancellable（放行 `continuity_reserved/`）|
| `RenderLayersMixin` | `getBlockLayer` / `getMovingBlockLayer` HEAD cancellable |
| `ModelLoaderMixin` | 纯 `@Unique` 字段 + `ModelLoaderExtension` 接口 |
| `SpriteMixin` | 纯 `@Unique` emissiveSprite 字段 |
| `FallingBlockEntityRendererMixin` / `PistonBlockEntityRendererMixin` | 在 `BlockModelRenderer.render(...)` 调用边界启/停亮度缓存 |
| `ReloadableResourceManagerImplAccessor` | `@Accessor("activeManager")` |

## 7. 值得学的 5 条具体做法

1. **用保留路径 + hex 索引做"任意路径贴图"重定向**：`ResourceRedirectHandler.getSourceSpritePath/redirect`（`client/resource/ResourceRedirectHandler.java:53-95`）+ `IdentifierMixin`，把不符合 identifier 规则的文件塞进方块图集。适用：需要从非标准目录/非法命名空间加载贴图的 mod。
2. **ThreadLocal 上下文 + `@ModifyArg` 包裹 lambda**：`SpriteLoaderMixin:36,62` 把上下文注入 vanilla 异步图集线程，`AtlasLoaderInitContext/AtlasLoaderLoadContext/SpriteLoaderStitchContext` 分离"新增 source / 收集 id / stitch 后关联"三阶段。适用：任何要在 vanilla 异步重载流程中插数据的场景。
3. **乐观读无锁缓存**：`QuadProcessors` 与 `SpriteCalculator` 都用 `StampedLock.tryOptimisticRead()` + 失败回落的双检写法，热路径（渲染线程）零锁开销且注释说明了为何 map 并发读安全。适用：渲染/实体 AI 热路径缓存。
4. **面向第三方扩展的字符串注册表 + 四件套抽象**：`api/client/CtmLoaderRegistry` + `CtmLoader/CtmProperties.Factory/QuadProcessor.Factory/CachingPredicates.Factory`，`ContinuityClient:75-215` 自带 21 个 method 也走同一注册路径。适用：库模组开放"数据格式/处理器"扩展点。
5. **配置项自注册到有序 map**：`ContinuityConfig.addOption`（`client/config/ContinuityConfig.java:96`，`Object2ObjectLinkedOpenHashMap` + 重复 key 告警），读写与 GUI 都遍历同一 `optionMapView`。适用：任何需要 JSON 配置 + GUI 的 NeoForge/Forge 或 Fabric 模组。

## 8. 公开 API（前置/库能力）

包路径 `me.pepperbell.continuity.api.client`（实现全部放在 `me.pepperbell.continuity.impl.client`，`@ApiStatus.NonExtendable` + `static get()` 单例，典型 facade 模式）：

- `CtmLoaderRegistry`：`registerLoader(String method, CtmLoader<?>)` / `getLoader(String)` —— 第三方可注册自定义 CTM method（资源包 `method=` 直接对接）。
- `CtmLoader<T extends CtmProperties>`、`CtmProperties`（`.Factory<T>.createProperties(Properties, Identifier, ResourcePack, int, ResourceManager, String)`）、`CachingPredicates`（`.Factory<T>`，含 `isValidForMultipass`）。
- `QuadProcessor`：`processQuad(MutableQuadView, Sprite, BlockRenderView, appearanceState, state, BlockPos, Supplier<Random>, pass, ProcessingContext)` + `ProcessingResult` 枚举；`ProcessingContext extends ProcessingDataProvider`（`addEmitterConsumer`/`addMesh`/`getExtraQuadEmitter`/`markHasExtraQuads`）——这是基于 Fabric Renderer API（`QuadEmitter`/`Mesh`）的自定义几何输出口。
- `ProcessingDataKeyRegistry`：`registerKey(Identifier, Supplier<T>, Consumer<T> resetAction)` + `getKey/getRegisteredAmount`，与 `ProcessingDataKey`/`ProcessingDataProvider` 组成"每个处理上下文的自定义附加数据"机制（内置键在 `client/processor/ProcessingDataKeys.java`，如 `MUTABLE_POS`）。
- `ContinuityFeatureStates`：运行时开关 connected/emissive 渲染；`EmissiveSpriteApi.getEmissiveSprite(Sprite)`：读发光贴图关联。
