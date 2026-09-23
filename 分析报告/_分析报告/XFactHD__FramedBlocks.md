# FramedBlocks 源码分析报告

> 分析对象：`源码库/_参考仓库/_bulk/XFactHD__FramedBlocks`（分支 26.1，稀疏检出 `**/*.java` 等白名单）。
> 阅读取舍：1.7k 文件不通读。细读了「模型包裹 / camo / 方块实体 / StateCache / 配方 / datagen」六条线，其余按包略读；
> 所有非 java 资源（assets、`src/generated`、`framedblocks.mixin.json`、`injected_interfaces.json`、LICENSE）不在检出内，均通过 `git show HEAD:<path>` 读取，下文引用时会标注。

## 1. 基本信息

- mod_id：`framedblocks`（`src/main/resources/META-INF/neoforge.mods.toml:5`），license 字段 `LGPL v3`（同文件 `:2`，仓库根 `LICENSE` 正文为 LGPL-3.0 头，经 git 读取）。
- 作者：XFactHD（GitHub `XFactHD/FramedBlocks`）。
- 目标版本：MC `26.1.2`、NeoForge `26.1.2.102`、mod 版本 `11.4.0`（`gradle.properties:10,12,14`；版本区间 `:11,13`）。**注意：这是新版日期式 MC 版本号 + NeoForge 单一加载器**，不是 1.20.1/1.21.1，很多结论落在 NeoForge 新模型管线（`BlockStateModel`/`Material`/`BlockStateModelPart`）之上。
- 构建插件：`net.neoforged.moddev` 2.0.144（`build.gradle:4`），Java 工具链 **25**（`build.gradle:14`），mixin compatibilityLevel `JAVA_25`。
- 工程结构：**单模块 Gradle 工程 + 4 个 sourceSet**（`build.gradle:16-43`）：`main`、`datagen`（`src/datagen/java`，跑 `--all` 输出到 `src/generated/resources`，`build.gradle:77-89`）、`test`（被"挪用"放 in-game 调试命令，`build.gradle:279-282` 注释与 `src/test/java/.../cmdtests/`）、`codegen`（`src/codegen/java`，离线代码生成器，不在 jar 里）。生成资源通过 `main.resources.srcDir 'src/generated/resources'` 并入（`build.gradle:17-19`）。
- 编译依赖：全部是 `compileOnly` + 自定义 `localRuntime` 配置（`build.gradle:203-244`），涵盖 diagonalblocks、JEI、Create/Ponder、Amendments、AE2、Jade、AtlasViewer、Searchables、AdditionalPlacement。多仓库均用 `exclusiveContent + includeGroup` 精确路由（`build.gradle:110-195`）——避免 Cursemaven 污染解析。
- maven 发布：`maven-publish`，group `xfacthd.framedblocks`、artifact `FramedBlocks`（`build.gradle:8,11`），publication `mavenJava` 取 `components.java`（`:284-295`），本地 `file://./mcmodsrepo` 仓库——即它把自身作为**依赖库对外发布**（addon 作者可 `implementation`）。

## 2. 源码规模与包结构

实测（`find -name '*.java' | wc -l` / `wc -l`，与本仓库检出一致）：

| sourceSet | .java | 行数 |
|---|---|---|
| `src/main/java` | 1706 | 143,187 |
| `src/datagen/java` | 19 | 5,768 |
| `src/codegen/java` | 6 | 2,087 |
| `src/test/java` | 33 | 2,325 |
| 合计 | 1764 | **153,367** |

速览卡片记的 155,131 行比实测多 1,764（正好等于文件数，疑为计数脚本每文件多加了一个换行）；卡片里"最大的 15 个文件"数值同样各偏 1 行，且"主类候选"挑中的是 `GeometryTemplateSpecEntry.java`，那只是 API 里的一个抽象类，**不是入口**（入口见第 3 节）。

主包文件数（`src/main/java/io/github/xfacthd/framedblocks/` 下二级包，含子包递归）：`common/data` 621、`common/block` 229、`client/model` 181、`api/model` 63、`common/blockentity` 65、`common/compat` 64、`api/block` 56、`client/render` 44、`api/camo` 39、`api/util` 38、`client/screen` 36、`api/datagen` 23、`api/predicate` 20、`common/crafting` 13、`common/net` 13、`mixin` 11+4。

最大的 12 个 java 文件：

| 文件 | 行 |
|---|---|
| `src/datagen/.../providers/FramedRecipeProvider.java` | 1722 |
| `src/codegen/.../skippreds/SkipPredicateGeneratorData.java` | 1216 |
| `src/datagen/.../providers/FramedBlockModelProvider.java` | 1203 |
| `src/main/.../api/block/blockentity/FramedBlockEntity.java` | 1112 |
| `src/datagen/.../providers/FramingSawRecipeProvider.java` | 976 |
| `src/main/.../common/FBContent.java` | 965 |
| `src/datagen/.../providers/FramedLanguageProvider.java` | 827 |
| `src/codegen/.../skippreds/SkipPredicateGeneratorImpl.java` | 729 |
| `src/main/.../api/model/quad/Modifiers.java` | 718 |
| `src/main/.../common/data/skippreds/stairs/StairsSkipPredicate.java` | 702 |
| `src/main/.../common/data/skippreds/slopeedge/InnerCornerSlopeEdgeSkipPredicate.java` | 691 |
| `src/main/.../api/block/IFramedBlock.java` | 662 |

规模结构的关键事实：`common/data/skippreds/` 一个目录 **142 个文件 / 32,611 行**，占 main 的 23%，且文件头写着「This class is machine-generated, any manual changes will be overwritten」——它们由 `src/codegen` 的离线生成器产出（见 4.4）。真正手写的核心逻辑体量比表面小得多。

## 3. 入口与注册

三个 `@Mod` 类，靠 dist 与 datagen 判定分裂：

1. `src/main/java/io/github/xfacthd/framedblocks/FramedBlocks.java:40-42` — `@Mod(FramedConstants.MOD_ID) public final class FramedBlocks`，构造器 `:42-86` 是总装配清单：
```java
FBContent.init(modBus);
ClientConfig.init(modBus, modContainer); ServerConfig.init(...); DevToolsConfig.init(...);
modBus.addListener(CapabilitySetup::onRegisterCapabilities);
modBus.addListener(NetworkHandler::onRegisterPayloads);
modBus.addListener(DataMapsSetup::onRegisterDataMapTypes);
modBus.addListener(DynamicRegistrySetup::onCreateDatapackRegistries);
FullFacePredicates.PREDICATES.initialize();  SideSkipPredicates.PREDICATES.initialize();
```
`onCommonSetup`（`:88-95`）里 `StateCacheBuilder.initializeStateCaches()` + `CamoContainerFactories.registerCamoFactories()`；`:69-71` 用 `Utils.PRODUCTION` 开关只在非正式版挂调试 reload listener；`:81-85` 注册了一条**带开关的崩溃报告附加信息**（`allowBlockEntities` 开启时提示用户先加黑名单 tag）。
2. `src/main/java/io/github/xfacthd/framedblocks/client/FBClient.java:122-153` — `@Mod(value=MOD_ID, dist=Dist.CLIENT)`，一次挂 28 个 mod-bus 监听，其中 `:137` `onBlockStateModelRegister` 与 `:511` 是本项目最关键的一行：
```java
event.registerDefinition(Utils.id("wrapper"), FramedBlockModelDefinition.CODEC);
```
`:534-541`（`onInitClientRegistries`）里 `ModelWrappingManager.fireRegistration()`，把 `RegisterModelWrappersEvent`（handler 在 `:247-508`，逐块调 `WrapHelper.wrap(...)`）在客户端注册阶段触发。
3. `src/datagen/java/.../datagen/GeneratorHandler.java:13-38` — 第三个 `@Mod(dist=CLIENT)`，只在 `DatagenModLoader.isRunningDataGen()` 时挂 `GatherDataEvent.Client`，注册 11 个 provider + 一个 datapack registry。

注册方式：全部 `DeferredRegister` 家族，集中在 `common/FBContent.java:122-138`（BLOCKS / ITEMS / DATA_COMPONENTS / BE_TYPES / MENU_TYPES / RECIPE_TYPES / RECIPE_SERIALIZERS / INGREDIENT_TYPES / CREATIVE_TABS / PARTICLE_TYPES / ATTACHMENT_TYPES / 自定义 CAMO_CONTAINER_FACTORIES），`:145+` 每个方块一行 `registerBlock(FramedCubeBlock::new, BlockType.FRAMED_CUBE)`。没有 ServiceLoader；addon 扩展点走**自研事件**（`RegisterModelWrappersEvent`、`RegisterBlockItemModelProvidersEvent`、`RegisterItemModelDataProvidersEvent`、`CamoContainerFactories`）。

## 4. 核心系统

### 4.1 形状空间：253 个 BlockType，1 个方块 = 1 个 blockstate 文件

- 形状枚举 `common/data/BlockType.java:43`，实测枚举常量 **253** 个；每个常量在构造参数里就声明了这块形状的全部行为契约（`:44` 起）：`canOccludeWithSolidCamo / isDoubleBlock / hasSpecialOutline / ... / ConTexMode / Outline / ShapeGenerator`，并各自绑定 5 个谓词（FullFace / SideSkip / Connection / BlockOverlay / NullCull，见 `api/block/IBlockType.java:23-80` 的一组契约方法）。
- `FBContent` 里 `public static final Holder<Block> BLOCK_*` 共 **255** 个，42 个 BlockEntityType。
- 反爆炸的第一层：**camo 不进 blockstate**。材质是数据组件 + 方块实体字段（4.3），所以形状×材质是 253 × N 的**运行时组合**，文件上不乘。
- 实测生成产物（`git ls-tree -r src/generated`，非检出内容）：`assets/framedblocks` 616 个文件 = blockstates **255** + models **82** + items 231 + framed_templates 45 + specialstates 2 + lang 1；`data/framedblocks` 1019 个 = recipe **474** + advancement 256 + loot_table 255 + block_overlay 25 + tags 8 + data_maps 1。也就是 **blockstate 与注册方块严格 1:1**，模型 json 只有 82 个（多数是"占位/无 camo 时"的通用 `framed_cube`、`framed_underlay`、`framed_reinforcement`）。作为对照：同样规模的"每形状×每材质一套 json"路线在 253 形状下不可行。
- 每个 blockstate 文件写的是**自定义 definition**，例如 `src/generated/resources/assets/framedblocks/blockstates/framed_slope.json`（经 git 读取）全部内容只有：`{"neoforge:definition_type":"framedblocks:wrapper","base_model":{"model":"framedblocks:block/framed_cube"}}`。`framed_cube.json` 则在同一 definition 里带 `multipart`+`when`（`solid_bg`/`alt` 条件）。承载它的类是 `client/model/unbaked/FramedBlockModelDefinition.java:26-40`（`baseModel` 是 `Either<BlockStateModelDispatcher, SingleVariant.Unbaked>`，外加 `aux_models` map 与可选 `wrapper_key`），`instantiate()`（`:42-54`）先按常规方式展开全部状态模型，再交给 wrapping handler 逐个替换。

### 4.2 形状 = 对 camo 已烘焙 quad 的运行时几何变换（不是 baked model，也不是 json 模型）

- 抽象基类 `api/model/geometry/Geometry.java:23`，唯一抽象方法 `transformQuad(QuadMapBuilder, BakedQuad, FramedBlockData, Object)`（`:31`）——"给一条 camo 模型的 quad，产出形状化后的 quad"。
- 最小组件实例：`client/model/geometry/slope/FramedSlopeGeometry.java:29-58`。45° 坡的**全部实现**是按 quad 朝向分流：正面 `Modifiers.makeHorizontalSlope(false, 45)`（`api/model/quad/Modifiers.java:406`），顶/底面 `Modifiers.cut(dir.getOpposite(), 1, 0)`，vertical 型走 `makeVerticalSlope`（`Modifiers.java:440,460`）。62 行覆盖一个形状族。
- 绑定玩家贴图发生在 `client/model/baked/FramedBlockStateModel.java:101` `collectParts(...)`：从 `level.getModelData(pos)` 取 `AbstractFramedBlockData.PROPERTY`（`api/model/data/AbstractFramedBlockData.java:17`），无 camo 时用预建的 `NO_CAMO_MODELS`（`:394 collectCubeBaseModels` 在 `ModelEvent.BakingCompleted` 后填充，见 `client/FBClient.java:523-528`）；有 camo 时 `CamoContainerHelper.Client.getOrCreateModel(camoContent)` 拿到**源方块自己的已烘焙 `BlockStateModel`**，逐 part 喂给 Geometry。
- 计算时机与缓存：`:158-176` 用 `createCacheKey(partData, camoContent, ctCtx, userKeyData, 三个 tintOffset)` 做 key（key 组装在 `:169`，查表 `:170`），miss 才 `buildPartCache`（`:251`），命中直接把缓存 part 包一层 `CullableBlockStateModelPart` 输出。也就是说**每个 (形状状态, camo, 连接上下文) 组合的几何只算一次**，之后是查表。`ctCtx` 来自源模型的 `createGeometryKey`（`:162`），所以随机变体/cam 的随机模型也进 key；ConTex 关闭时 key 退化为 null 上下文。
- 简单形状进一步**数据驱动**：`client/model/geometry/templated/TemplateSpecs.java:34-36` 一行一个形状（如 `SLAB_EDGE = TemplateUtils.createTopBottomHorFacingSpec(BLOCK_FRAMED_SLAB_EDGE, SourceType.TEMPLATE, TemplateIds.SLAB_EDGE)`），几何来自 45 个 `assets/framedblocks/framed_templates/*.json`（元素 = cuboid `from/to` + 每面 bool，如 `half_board.json`），由 `client/model/template/GeometryTemplateManager.java:31,88-100` 以 Gson+`GeometryTemplate.CODEC` 在 reload 时加载。运行时可注册的 sprite 源另有 `framedblocks:anim_splitter` / `area_mask`（`FBClient.java:543-546`）。
- 结论：**墙/板/斜角/楼梯都是运行时生成**；楼梯/栅栏门这类"由若干 cuboid 组成"的形状走 json 模板，斜面/角面这类需要斜切 UV 的走 Java Geometry。代价是几何正确性依赖每面 quad 的人工分流规则，所以必须有 4.4 那套 culling 谓词兜底。

### 4.3 状态与同步：BlockState(形状) + BE(camo/修饰符) + StateCache(派生位掩码)

- 三层数据。① **形状与朝向**在 BlockState：`api/block/FramedProperties.java:11-40`（`FACING_HOR/FACING_NE/TOP/OFFSET/X_AXIS/Y_AXIS/Z_AXIS/SOLID/PROPAGATES_SKYLIGHT/GLOWING/STATE_LOCKED/ALT_SLOPE/COPYCAT_STYLE`）+ `common/data/PropertyHolder`。**注意：六向连接不是 property**。② **材质与修饰符**在 BE：`api/block/blockentity/FramedBlockEntity.java:96-103`（`camoContainer`、`Holder<BlockOverlay>`、glowing/intangible/reinforced/emissive 四个 flag）。③ **派生元数据**在 `StateCache`。
- 存档/网络/物品三条路径各自最省：NBT `saveAdditionalInternal`（`:1064-1073`）把 camo 存成**单个 int**（`api/camo/block/SimpleBlockCamoContainerFactory.java:65` `valueOutput.putInt("state", Block.getId(state))`，`:70` `Block.stateById(...)` 读回）；网络包 `writeToDataPacket`（`:860-864`）只写 camo + overlay + 一个 **byte 打包四个 flag**（`writeFlags` `:907-913`）；`getUpdateTag/getUpdatePacket` 直接复用 vanilla BE 包（`:832-846`）；`readFromDataPacket`（`:869-905`）逐字段 diff，只对真正变化的位发 `requestRenderUpdate/requestCullingUpdate/requestLightUpdate`。物品侧走 **data component**：`collectImplicitComponents`（`:1010-1019`）→ `DC_TYPE_CAMO_LIST`（`FBContent.java:406`）、`FrameConfig`（`api/component/FrameConfig.java:19-37` 四 bool 的 RecordCodec + StreamCodec + DEFAULT，`:43-48` 只在非默认时写组件）。
- camo 的类型分发是**注册表 codec**：`api/camo/CamoContainerHelper.java:38-44` `REGISTRY.byNameCodec().dispatch(...)`，注册表本身由 `common/data/FramedRegistries.java:13-17` 建（`builder.sync(true)`），工厂类型有 block / fluid 等（`common/data/camo/`）。camo 内容 `api/camo/block/BlockCamoContent.java:34-35` 就存 `BlockState state`，`:146 getAppearanceState()` 供渲染取"外观状态"。
- 加载即校验：`loadAndValidateCamo`（`FramedBlockEntity.java:1092-1104`）camo 不合法就丢 camo 并打 warn（含方块/坐标/被丢弃的 camo id），并把 `getLightEmission()>0` 折进 `forceLightUpdate`；`onLoadInternal`（`:785-795`）在服务端 load 时无条件重算 SOLID/GLOWING 等派生 flag，注释写明是为了绕开"工具只复制 BlockState 不复制 BE 数据"的问题。
- **六向连接（ConTex）与遮挡的表示**：`api/block/cache/StateCache.java:32-38` 五个字段——`byte fullFace`、`byte mayConnect`、`long conFullEdge`、`long conDetailed`、`byte solidOverlay` + `EdgeOverlayMask`。构造时（`:39-96`）对 6 面 × 4 边枚举调 `IBlockType` 的谓词，把结果压成位掩码（`getSideEdgeNullableMask` `:212`、`getSideEdgeMask` `:221`）。查询全是位运算：`isFullFace` `:117`、`mayConnect` `:129`、`canConnectFullEdge` `:139`、`canConnectDetailed` `:149`。
- 这个 cache 挂在 BlockState 对象上，靠 **接口注入 + mixin**：`src/main/resources/injected_interfaces.json`（git 读取）把 `StateCacheAccessor` 注到 `BlockBehaviour$BlockStateBase`，`mixin/MixinBlockStateBase.java:16-38` 加 `@Unique StateCache framedblocks$cache` 字段；`common/data/StateCacheBuilder.java:24-44` 在 commonSetup 遍历 `BuiltInRegistries.BLOCK` 中所有 `IFramedBlock` 的全部状态，`new StateCache(...)` 后用 `ObjectOpenHashSet.addOrGet` 去重再 `state.framedblocks$initCache(cache)`，日志打印"unique caches / states / 耗时"。BE 侧 `FramedBlockEntity.java:108` 与 `setBlockState`（`:811`）直接 `state.framedblocks$getCache()`，零查表成本。
- 客户端**遮挡位**（哪几面被邻块挡住）不靠网络：`api/block/blockentity/ClientData.java:36`（sealed 基类）每个 BE 持一个 `CullState`（单块 `:227-228`，双块两份 `:246-247`）与 `sectionNeighborMask`（字段 `:42`，按 block 是否贴 section 边界算出的 6 bit，计算在 `:204-225`），`updateCulling`（`:77-125`）逐面调 `CullingHelper.isSideHidden` 并把变化扩散到相邻 framed BE（对端 `updateCulling(dir.getOpposite(), true)`），随后 `ClientAccess.setSectionsDirty(...)` 精确标脏 section（`markSectionRangeDirty` `:69-72`）；`:154-173 getModelData()` 在依赖 chunk 未就绪（`CullingUpdateResult.PARTIAL`）时**保留上一次的 ModelData 并自我 re-request**，避免跨区块加载顺序导致的遮挡抖动；模型实际消费的是 `makeBlockData`（`:190-197`）打包的 `FramedBlockData(state, camo, cullMask, ...)`。服务端只在需要时发一个 26 行的 `ClientboundCullingUpdatePayload`（chunk + pos 数组，`common/net/payload/clientbound/ClientboundCullingUpdatePayload.java`），由 `common/data/cullupdate/CullingUpdateTracker.java:24-42` 在 `LevelTickEvent.Pre` 按 (维度,chunk) 聚合后 `sendToPlayersTrackingChunk`——**先聚合再发**，注释说明是为了排在 block update 包之后到达。

### 4.4 遮挡谓词的规模问题：用离线代码生成替代人肉

`api/predicate/cull/SideSkipPredicate` 决定"这个形状的这条边能不能被邻面挡住"。它是纯组合爆炸的：形状 × 状态属性 × 6 面 × 邻块属性。手写产物是 142 个类 / 32,611 行（如 `common/data/skippreds/stairs/StairsSkipPredicate.java` 702 行），而这些类**由 `src/codegen` 生成**：`codegen/skippreds/SkipPredicateGeneratorData.java:30-60` 用 DSL 描述每个 BlockType 用到的属性（`Property.api("Direction","dir","FACING_HOR",PRIMITIVE)` / `Property.internal("SlopeType","type","SLOPE_TYPE",CUSTOM)`）和测试方向（`TestDir("TriangleDir","Tri",...)`），`SkipPredicateGeneratorImpl.java:30` 写死输出目录 `src/main/java/.../common/data/skippreds/`，`:50-58` 是类模板（带 `@CullTest(...)` 注解和"machine-generated"注释）。入口 `codegen/SkipPredicateGenerator.java:6-13` 是个 `static void main()`，手改 `sourceType` 后单跑，`generateAndExportClasses` 只重生成一个类型或全部。生成类与手写实现的一致性由 `src/test/java/.../cmdtests/tests/SkipPredicateConsistency.java`/`SkipPredicateErrors.java`/`SkipPredicateRedundancy.java` 在游戏内命令里回归检查（`build.gradle:279-282` 明确"test sourceSet 被挪用"）。

### 4.5 蓝图数据与兼容层（略读，未展开）

`api/blueprint/BlueprintData.java`（record，含 `CamoList`、overlay、四个 flag、`BlockItemStateProperties`、可选 custom TypedDataComponent），BE 侧写入/读回见 `api/block/blockentity/FramedBlockEntity.java:947-994`，每种子类可覆写 `appendCustomBlueprintData`。`common/compat/` 64 文件按 mod 分子包（jei/create/ae2/jade/atlasviewer/searchables/diagonalblocks/amendments/additionalplacements/buildinggadgets），`common/compat/CompatHandler.java:15-23` 在 mod 构造期逐个调用各子兼容的 `init()`（每个子兼容自己判断目标 mod 在否）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络极简**：`common/net` 13 文件 368 行。`NetworkHandler.java`（62 行）在 `RegisterPayloadHandlersEvent` 注册 7 个 serverbound（`payload/serverbound/`：状态循环、锯床选配方/编码图案、涂抹器三件套）+ 2 个 clientbound（遮挡更新、打开告示牌界面）。**方块状态/材质同步完全不用自定义包**，走 BE update tag + data component stream codec。
- **自定义配方类型 4 个**（`FBContent.java:725-740`）：`framedblocks:frame`（锯床，唯一注册了 `RecipeType` 的）、`apply_camo`、`jei_camo`（仅 JEI 展示用的假配方）、`rotate_shape`（把"旋转形状"表达成一条合成）。另有 `RecipeDisplay.Type framing_saw`（`:749-751`）和 `IngredientType jei_camo_dummy`（`:756-758`）。Codec 例子：`common/crafting/saw/FramingSawRecipe.java:35-40` = `material: intRange(0,MAX)` + `additives: sizeLimitedList(MAX_ADDITIVE_COUNT)` + `result: ItemStackTemplate.CODEC` + `disabled: bool`，`:41-50` 对偶的 `StreamCodec`；`disabled` 字段是**给整合包作者用的配方关闭开关**（`FramingSawRecipeCache.java:57-60` 先取 materialValue 再 `removeIf`）。锯床不是 vanilla 匹配语义：`matches` 走材质值/LCM/输出堆叠三重判定（`FramingSawRecipe.java:71-96`，返回带原因的 `FramingSawRecipeMatchResult`，界面据此提示"差哪样"；serializer/type 在 `:192,197` 接回 `FBContent` 注册项）。
- **配方与数据的加载路径**：`FramingSawRecipeCache.java:32-72` 维护 SERVER/CLIENT 两份单例，`onAddReloadListener`（服务端 `RecipeMap`）与 `onRecipesReceived`（客户端）同一 `update()`；`OnDatapackSyncEvent` 主动把配方重发给玩家（`:64`），因为配方要在锯床界面打开时可用而不依赖 vanilla 的配方同步时机。
- **datapack 驱动程度**：自定义 `DataPackRegistry` 1 个——`framedblocks:block_overlay`（`common/data/dynreg/DynamicRegistrySetup.java:11-13`，`event.dataPackRegistry(KEY, BlockOverlay.DIRECT_CODEC, ...)`），生成 25 条（地毯/苔藓/雪/菌丝等"贴面覆盖层"）。DataMap 2 个：`block_camo_rotators`（Block→旋转器原型）与 `sound_event_groups`（SoundEvent→组），都 `.synced(CODEC, true)`（`common/data/DataMapsSetup.java:15-25`），`:29-37` 处理"data map 晚于默认组件绑定到达"的时序、CLIENT_SYNC 时 `BlockCamoRotators.reload()`。形状模板 45 个 json（4.2）。camo 白/黑名单走 **tag**（`common/data/camo/block/BlockCamoContainerFactory.java:18-31` 读 `BLOCK_BLACKLIST` / `BE_WHITELIST` / `FRAMEABLE`）。
- **配置**：3 个 `ModConfigSpec` 文件（`common/config/ClientConfig.java` 461 行、`ServerConfig.java` 188、`DevToolsConfig.java` 169），API 侧只暴露 `ConfigView`/`ExtConfigView` 视图（`api/util/ConfigView` + `ClientConfig.VIEW`），因此服务端配置值能安全地被 BE/模型代码读取而不成对加载器耦合。DevTools 里甚至有"打印每个 wrapper 用到哪些属性、哪些被 StateMerger 吃掉"的调试开关（`DevToolsConfig.java:78`）。
- **datagen**：19 文件 5,768 行，`GeneratorHandler.java:22-38` 注册 11 个 provider（sprite source / block model / item model / lang / template / loot / recipe / saw recipe / block tag / item tag / data map / overlay tag）+ 一个 `RegistrySetBuilder` 产 datapack 注册表对象。手写 API 面在 `api/datagen/`（23 文件）：`AbstractFramedBlockModelProvider`（含 `framedVariant/framedStandalone*/simpleFramedBlockWithItem` 和 `FramedBlockModelDefinitionGenerator`，`:119-121`、`:448-461` 收集 standalone definition 并写文件）、`recipes/builders/FramingSawRecipeBuilder`、`loot/objects/RetainCamoLootCondition`+`SplitCamoLootFunction`（战利品表能把 camo 拆出来掉，255 个 loot_table 全生成）。配方实测分布（474 个 json，`git grep` 统计）：`framedblocks:frame` 217、`minecraft:crafting_shaped` 181、`framedblocks:rotate_shape` 42、`crafting_shapeless` 33、`framedblocks:apply_camo` 1。
- 稀疏检出的影响：`src/main/resources/assets` 与 `src/generated/resources` **未落盘**（只有 `META-INF/` 两个文件在），本报告所有 json 相关数字来自 git 对象树，复现需 `git ls-tree -r --name-only HEAD src/generated`。

## 6. Mixin

`src/main/resources/framedblocks.mixin.json`（未落盘，git 读取）：`package = io.github.xfacthd.framedblocks.mixin`，`compatibilityLevel JAVA_25`，`mixinextras.minVersion 0.5.0`，`defaultRequire 1`。分段：`mixins`（common）6 个、`client` 3 个，共 **10 个 mixin 类**（`src/main/java/.../mixin/`，15 文件含 package-info）。另有 `src/main/resources/META-INF/accesstransformer.cfg`（32 行，`build.gradle:48 validateAccessTransformers = true`）和 `injected_interfaces.json`（4 个接口注入，见 `build.gradle:50`）。

| 类 | 目标 | 注入点（@At） | 目的 |
|---|---|---|---|
| `mixin/InvokerBlock.java:8-11` | `Block` | `@Invoker("registerDefaultState")` | 子类调 protected 的默认状态注册 |
| `mixin/InvokerBlockItem.java:10-13` | `BlockItem` | `@Invoker("getPlacementState")` | 复用 vanilla 放置态计算 |
| `mixin/MixinBlockStateBase.java:16-38` | `BlockBehaviour$BlockStateBase` | `@Unique` 字段 + `@Shadow asState()` | 给每个状态挂 `StateCache`（4.3 的核心）；`initCache` 里 `Preconditions` 限定只对 `IFramedBlock` 调用 |
| `mixin/MixinStateDefinitionBuilder.java:12-27` | `StateDefinition$Builder` | `@Shadow @Final Map properties` | `hasProperty` / `removeProperty`——从 builder 里摘属性，配合 `BlockUtils.addStandardProperties`（`api/block/BlockUtils.java:49,137,145`）动态增减属性 |
| `mixin/MixinStairBlock.java:13-45` | `StairBlock` | MixinExtras `@WrapOperation`，`method="<init>"` 和 `"updateShape"` 上的 `BlockState#setValue`/`getValue` | 让 `FramedDoubleStairsBlock` 复用 `StairBlock` 逻辑但不带 `WATERLOGGED` 属性（构造期跳过默认值、`updateShape` 缺属性时返回 FALSE） |
| `mixin/MixinMapItemSavedData.java:47-127` | `MapItemSavedData` | MixinExtras `@Definition+@Expression` 两处 `@ModifyExpressionValue`（`tickCarriedBy` 局部变量 `placedInFrame` 的 `!=null`/`==null`，`:55-70`）、`@Inject`（`:72`）、**`method="<clinit>"` 的 `@ModifyExpressionValue` 包住 `RecordCodecBuilder.create`（`:82-101`）** | ①让"装了 Framed Item Frame 的地图"也走 tracking 分支；②把 `framedblocks:frames` 列表**加进 vanilla 地图数据的 CODEC**，失败时打 error 且非正式版抛异常（`:99-101`） |
| `mixin/client/AccessorModelManager.java:8-11` | `ModelManager` | `@Accessor("missingModels")` | 取"缺失模型"占位（`client/model/ResourceCubeModel.java:64` 用它兜底加载失败的贴图/模型） |
| `mixin/client/AccessorMultiPlayerGameMode.java:7-10` | `MultiPlayerGameMode` | `@Accessor("destroyDelay")` | 把破坏进度写回 vanilla 默认值（`client/util/ClientAccess.java:18`，用于破坏被取消/客户端预测后的重置） |
| `mixin/client/MixinLevelRenderer.java:19-49` | `LevelRenderer` | `@Inject("<init>", at=@At("RETURN"))`、`@Inject("allChanged", at=@At("HEAD"))` | 监听 vanilla 的 `cutoutLeaves` 选项变化 → `CacheCleaner.clearModelCaches(SETTINGS_CHANGED)`，因为模型缓存的结果依赖该设置 |

值得注意的两点：`required=1` + `defaultRequire=1`（没静默失败余地）；`<clinit>` 改 CODEC 与 `@WrapOperation` 属于"知道自己在改 vanilla 语义"的高风险用法，都配了降级日志。

## 7. 值得学的 5 条

1. **把"看起来必须爆炸"的组合挪到运行时，用 1:1 的 blockstate + 自定义 definition 类型收口**。`client/model/unbaked/FramedBlockModelDefinition.java:26-54` 配 `client/FBClient.java:511` 的 `event.registerDefinition(id("wrapper"), CODEC)`，让 255 个方块只要 255 个 definition 文件、82 个模型文件。为什么值得抄：卡牌/殖民地的"皮肤 × 部件"如果每组合出一个 json，资源包大小与 datagen 时间线性相乘；把组合搬进 `instantiate()` 之后，文件数只随**形状**增长。
2. **派生元数据缓存到 BlockState 对象上，并用 `addOrGet` 去重**。`api/block/cache/StateCache.java:32-38`（6 面×4 边压成 2 个 long）+ `common/data/StateCacheBuilder.java:36-38`（`ObjectOpenHashSet.addOrGet` 后 `state.framedblocks$initCache`），配合 `mixin/MixinBlockStateBase.java:16-38`。为什么值得抄：热路径（每帧每面的判断）退化成位运算与对象相等，且"有多少种真正不同的状态"会被自动收敛到日志里，成本可观测。
3. **同步包按字段 diff、把 flag 压进一个 byte，并且只在聚合 tick 边界发一次**。`api/block/blockentity/FramedBlockEntity.java:860-905`（`writeToDataPacket` 三行、`readFromDataPacket` 逐位比较后只请求必要的 render/light/culling 更新）+ `common/data/cullupdate/CullingUpdateTracker.java:24-42`（`Map<维度, Long2ObjectMap<LongSet<ChunkPos, pos>>>`，`LevelTickEvent.Pre` 批量 `sendToPlayersTrackingChunk`）。为什么值得抄：比"每次 setChanged 就 sync"少一到两个数量级的包，且注释写明了发送时机是为了排在区块 block update 之后。
4. **组合爆炸的纯函数用离线 codegen 写成 java 源码，而不是写解释器**。`src/codegen/java/.../SkipPredicateGeneratorData.java:30-60`（属性/方向 DSL）→ `SkipPredicateGeneratorImpl.java:30,50-58`（模板直写 `src/main/java/.../skippreds/`），并配 `src/test/java/.../cmdtests/tests/SkipPredicateConsistency.java` 做一致性回归。为什么值得抄：生成物是普通 java，能被编译器检查、能被 profiler 看到、能内联；跑一次生成器比维护一个运行时 DSL 便宜，而且 diff 可读。
5. **可选 mod 依赖一律 `compileOnly`，配一个不进 POM 的 `localRuntime` 配置**。`build.gradle:197-244`（注释直接写明"用 localRuntime 代替 runtimeOnly，因为它是 local 的、classpath 必须来自 run config 而不是其父配置"）+ 每个 repo 用 `exclusiveContent` 圈住 group（`:110-195`）。为什么值得抄：兼容层（`common/compat/` 64 文件）照常编译，发布产物零传染，Cursemaven 之类慢仓库不会被拿去解析别人的坐标。

（第 6 条顺手记下，非凑数：`api/model/quad/QuadModifierPool.java:12-43` 的对象池 + `-Dframedblocks.quad_modifier.check_leaks=true` 时用 `java.lang.ref.Cleaner` + `StackWalker` 打印未 release 的调用栈——在 `build.gradle:67` 以注释形式留了开关。写渲染热路径的池化对象时这套"泄漏即报栈"的做法很值。）

## 8. 公开 API

FramedBlocks 是内容 mod 兼 **addon 平台**（发布 `xfacthd.framedblocks:FramedBlocks`，`build.gradle:8,284-295`），API 面全部在 `io.github.xfacthd.framedblocks.api`（303 文件），内部实现只在 `common`/`client`，`api/internal/`（7 文件）与 `api/*/package-info.java` 用 `@ApiStatus.Internal/NonExtendable` 标界。

- 入口与注册：`api/FramedBlocksAPI.java`（`getCamoContainerFactoryRegistry()` 等，被 `FramedRegistries.java:38` 反查）、`api/FramedBlocksClientAPI.java`；自定义注册表 `framedblocks:camo_container`（key 在 `api/util/FramedConstants.java:30`，建表在 `common/data/FramedRegistries.java:13-17`，`sync(true)`）由 `common/data/camo/CamoContainerFactories.registerCamoFactories()`（`FramedBlocks.java:92`）填内置项；addon 用同样的 `DeferredRegister.create(CamoContainerFactory.class, MOD_ID, "camo_container")` 往同一注册表追加（内置项写法见 `FBContent.java:138`）。数据驱动形状模板则放 `assets/<ns>/framed_templates/*.json`（4.2），overlay 放 `data/<ns>/framedblocks/block_overlay/*.json`（4.1）。
- 扩展点接口：`api/camo/CamoContainerFactory`（+ `CamoContainer`/`CamoContent` 两级抽象，`api/camo/block/AbstractBlockCamoContainerFactory.java:21-112` 给方块类 camo 的骨架，子类只需 `getStateFromItemStack/createContainer/isValidBlock`）、`api/model/wrapping/GeometryFactory`/`ModelFactory`/`AuxModelProvider`/`statemerger/StateMerger`、`api/model/geometry/Geometry`（`transformQuad` 是唯一必需覆写）、`api/block/IBlockType`（一组形状行为契约）、`api/predicate/{cull,contex,fullface,overlay}` 四套谓词、`api/shapes/ShapeGenerator`、`api/model/item/block/BlockItemModelProvider`、`api/ghost/GhostRenderBehaviour`、`api/render/outline/OutlineRenderer`、`api/datagen/*`（自定义配方 builder + 模型 provider 基类）。
- 接入方式：mod bus 事件。`RegisterModelWrappersEvent`（官方用法示例在 `FBClient.java:247-508`，全部形如 `WrapHelper.wrap(FBContent.BLOCK_X, TemplateSpecs.X, WrapHelper.DEFAULT_MERGER)`，见 `api/model/wrapping/WrapHelper.java:50-120,235`）、`RegisterBlockItemModelProvidersEvent`、`RegisterItemModelDataProvidersEvent`、`DataPackRegistryEvent.NewRegistry`、`RegisterDataMapTypesEvent`。`WrapHelper.IGNORED_PROPS`/`DEFAULT_MERGER`/`POWERED_MERGER`（`:29-39`）把"哪些状态属性不影响外观"抽成显式策略对象，避免为每个属性组合重复烘焙模型。
- 另两条材质拼接路线的对照（与 `深挖__Domum-Ornamentum__方块版材质拼接.md` 比）：

| 维度 | Domum 路线 | 本仓库路线 | 对照：CTM 类贴图拼接路线（非本仓库实现，未在此验证） |
|---|---|---|---|
| 存什么 | 部件 id → 源 `Block` 映射（物品 data component） | 单个 `BlockState`（BE 里存 int，`api/camo/block/SimpleBlockCamoContainerFactory.java:65`） | 贴图名/布局表 |
| 命中部件的方式 | **占位 sprite 名 == 部件 id**（隐式契约） | **不需要命中**：整条已烘焙 quad 按朝向交给 Geometry 规则（`client/model/geometry/slope/FramedSlopeGeometry.java:29-58`） | 按邻块位掩码选 baked 变体 |
| 加材质的成本 | 写一条 tag，零代码 | 零成本（任意 mod 方块皆可 camo，只要过 `isValidBlock`） | 需美术出图 |
| 加形状的成本 | 一个方块 json + 部件表 | **一个 Geometry 类或一个 template json**（45 个 json 覆盖简单形状） | 一组 baked model + blockstate |
| 代价 | sprite 名占命名空间、改贴图名静默失效 | 每形状的 quad 分流规则要人写人验（→ 32k 行 skippreds）+ 运行时几何缓存内存 | 文件与贴图数量随形状×邻接组合增长 |
| 能吃到什么 | 源方块的染色/渲染类型/粒子/行为委托 | 源方块**整个已烘焙模型的所有 part 与 tint**（`FramedBlockStateModel.java:101-135` 逐 part 收集），并额外得到形状变换 | 只得到贴图 |

一句话定位：本仓库属于"存源方块引用"这一类，但**匹配点在几何层（quad 朝向 + UV 重算）而不是 sprite 名层**——所以它不需要 Domum 那种"部件 id 即贴图名"的隐式契约，代价是每加一种形状都要写或生成一份"这条 quad 该切/该斜/该丢"的规则，并且必须自备第 4.4 节那套遮挡谓词来解释切完之后谁能挡谁。
