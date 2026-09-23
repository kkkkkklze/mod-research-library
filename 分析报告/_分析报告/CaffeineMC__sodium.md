# CaffeineMC/sodium 源码分析报告

> 分析对象：`_参考仓库/_bulk/CaffeineMC__sodium`，HEAD = `73fe292`。仓库为多模块 Gradle 工程，本文所有结论均来自实际文件读取。

## 1. 基本信息

| 项 | 值 | 来源 |
| --- | --- | --- |
| Mod 名 / mod_id | Sodium / `sodium` | `neoforge/src/mod/resources/META-INF/neoforge.mods.toml`、`fabric/src/main/resources/fabric.mod.json` |
| 作者 | JellySquid (jellysquid3)、IMS212（credits 含 PepperCode1、embeddedt、douira 等 30 余人） | 同上 |
| 目标 MC 版本 | `26.3-rc-1`（`BuildConfig.MINECRAFT_VERSION`） | `buildSrc/src/main/kotlin/BuildConfig.kt:4` |
| 加载器 | Fabric（Loader 0.19.3，Fabric API 0.160.3+26.3）+ NeoForge（26.2.0.0-beta） | `BuildConfig.kt:5-7` |
| Mod 版本 / 发布渠道 | `0.9.2-beta.1`；CurseForge `394468`、Modrinth `AANobbMI` | `BuildConfig.kt:9,21-22` |
| Gradle 插件 | `net.fabricmc.fabric-loom 1.17.20`、`net.neoforged.moddev 2.0.141`、`me.modmuss50.mod-publish-plugin 1.1.0` | `fabric/build.gradle.kts:4`、`neoforge/build.gradle.kts:4`、`build.gradle.kts:7` |
| Java | toolchain / `options.release` = 25 | `buildSrc/src/main/kotlin/multiloader-base.gradle.kts:9,12` |
| 许可证 | Polyform-Shield-1.0.0 | `LICENSE.md`、mods.toml `license` |
| 编译依赖 | `minecraft 26.3-rc-1`；`io.github.llamalad7:mixinextras-common:0.5.0`；`net.fabricmc:sponge-mixin:0.13.2+mixin.0.8.5`；`fabric-loader`；boot 源集还有 lwjgl 3.4.3（含 -opengl/-sdl）、jna 5.14.0、jna-platform、slf4j-api 2.0.9、jspecify 1.0.0 | `common/build.gradle.kts:57-78` |
| 内嵌 Fabric 模块 | `fabric-api-base`、`block-getter-api-v2`、`rendering-v1`、`renderer-api-v1`、`lifecycle-events-v1`、`rendering-fluids-v1`、`resource-loader-v0/v1`、`transitive-access-wideners-v1` | `fabric/build.gradle.kts:68-86` |

它是"被依赖方"而不是依赖方：`neoforge.mods.toml` 声明 `"fabric-renderer-api-v1:contains_renderer" = true` 与 `"fabric:provides" = ["indium"]`，即 Sodium 自身充当 FRAPI 的 renderer 实现，取代 Indium。

## 2. 源码规模与包结构

实测：`.java` 文件 **648 个**，总行数 **55,703**（`find . -name '*.java' -not -path './.git/*' -exec cat {} + | wc -l`）。模块分布：`common` 588、`neoforge` 23、`frapi` 20、`fabric` 17。`common` 内部再分 4 个 source set：`main` 487、`api` 52、`boot` 45、`desktop` 4。

主要包（第 3 层，文件数）：

- `client/render/chunk` 162 —— 地形渲染全部子系统（async / compile / data / lists / occlusion / region / storage / terrain / translucent_sorting / tree / vertex）
- `mixin/core/render` 19、`mixin/features/render` 15、`mixin/features/textures` 12
- `client/util` 19、`client/services` 16、`client/config/structure` 16、`client/config/builder` 14
- `client/gpu/arena` 14（GPU 缓冲区分配 + staging buffer）、`client/gpu/device` 10（GL/VK 后端）
- `client/model/light` 13（光照/AO 管线）、`client/gui` + `client/gui/options` + `client/gui/widgets` 约 35
- `client/render/model`、`client/render/vertex`、`client/world`（LevelSlice/克隆区块）

最大的 10 个文件（`wc -l` 实测）：

| 行数 | 文件 |
| --- | --- |
| 1210 | `common/src/main/java/net/caffeinemc/mods/sodium/client/render/chunk/RenderSectionManager.java` |
| 1084 | `common/src/main/java/net/caffeinemc/mods/sodium/client/render/chunk/translucent_sorting/bsp_tree/InnerPartitionBSPNode.java` |
| 878 | `common/src/main/java/net/caffeinemc/mods/sodium/client/render/chunk/compile/pipeline/DefaultFluidRenderer.java` |
| 702 | `common/src/main/java/net/caffeinemc/mods/sodium/client/gui/SodiumConfigBuilder.java` |
| 650 | `common/src/main/java/net/caffeinemc/mods/sodium/client/render/chunk/occlusion/OcclusionCuller.java` |
| 644 | `common/src/main/java/net/caffeinemc/mods/sodium/client/util/interval_tree/Interval.java` |
| 600 | `common/src/main/java/net/caffeinemc/mods/sodium/client/render/chunk/RenderSection.java` |
| 581 | `common/src/main/java/net/caffeinemc/mods/sodium/client/gpu/arena/ArenaAggregator.java` |
| 569 | `common/src/main/java/net/caffeinemc/mods/sodium/client/gui/VideoSettingsScreen.java` |
| 539 | `common/src/main/java/net/caffeinemc/mods/sodium/client/render/SodiumWorldRenderer.java` |

## 3. 入口与注册

**没有内容注册表**（本 mod 不注册方块/物品/实体），没有 `DeferredRegister` / `Registrate`。它的"注册"是三条线：

1. 平台入口：
   - NeoForge：`neoforge/src/mod/java/net/caffeinemc/mods/sodium/neoforge/SodiumForgeMod.java:17` `@Mod(value = "sodium", dist = Dist.CLIENT)`，构造参数 `(IEventBus bus, ModContainer modContainer)`，内部只做 `modContainer.registerExtensionPoint(IConfigScreenFactory.class, ...VideoSettingsScreen.createScreen(...))`、遍历 mod property `frex:flawless_frames_handler` 反射调用、`FRAPIRegistrar.getInstance().register()`。
   - NeoForge 预启动（窗口创建前）：`neoforge/src/main/java/net/caffeinemc/mods/sodium/service/SodiumWorkarounds.java` 实现 `GraphicsBootstrapper`，经 `neoforge/src/main/resources/META-INF/services/net.neoforged.neoforgespi.earlywindow.GraphicsBootstrapper` 注册；该 jar 的 manifest 被设为 `FMLModType = LIBRARY`（`neoforge/build.gradle.kts` 的 `tasks.jar`），与主 mod 分属 `service` / `mod` 两个 source set。
   - Fabric：`fabric/src/main/java/net/caffeinemc/mods/sodium/fabric/SodiumFabricMod.java`（`ClientModInitializer`）与 `SodiumPreLaunch.java`（`PreLaunchEntrypoint`），在 `fabric.mod.json` 的 `entrypoints.client` / `entrypoints.preLaunch` 声明。
2. 公共初始化收敛到一处：`common/src/main/java/net/caffeinemc/mods/sodium/client/SodiumClientMod.java:31` `onInitialization(String version)` —— 注册 4 个 F3 调试条目（`SODIUM_DEBUG_ENTRY_FULL` 等 `Identifier`）、`loadConfig()`、`updateFingerprint()`。
3. 平台抽象用 **`java.util.ServiceLoader` 自建服务层**：`common/.../client/services/Services.java:14-44` 提供 `load` / `loadOr` / `loadConditionalOr(Class<? extends ServiceProvider<U>>, Supplier<U>)`；实现类由各平台 `META-INF/services/` 文件绑定（如 `fabric/src/main/resources/META-INF/services/net.caffeinemc.mods.sodium.client.services.PlatformRuntimeInformation` → `net.caffeinemc.mods.sodium.fabric.FabricRuntimeInformation`）。共 7 个平台服务接口（RuntimeInformation / BlockAccess / LevelAccess / LevelRenderHooks / ModelAccess / MixinOverrides / FluidRendererFactory）+ frapi 的 2 个（FRAPIRegistrarProvider / ModelModelEmitterProvider）。

## 4. 核心系统

### 4.1 地形渲染调度：RenderSectionManager（1210 行）

- 文件：`common/src/main/java/net/caffeinemc/mods/sodium/client/render/chunk/RenderSectionManager.java`
- 职责：全帧的地形 graph / 渲染列表 / 异步剔除 / 网格任务派发 / GPU 上传节流。
- 关键设计点：
  - **帧预算制**：`FRAME_DURATION_UPLOAD_FRACTION = 0.3f`、`MIN_UPLOAD_DURATION_BUDGET = 10_000_000L`（:64-65）——每帧只花固定比例的帧时长上传网格，避免掉帧。
  - **估计器驱动调度**：字段 `JobDurationEstimator` / `MeshTaskSizeEstimator` / `UploadDurationEstimator`（:75-77），估计值来自 `render/chunk/compile/estimation/` 下的 `ExpDecayLinear2DEstimator`、`Average1DEstimator`、`LimitedResourceBudget`，用于填满但不超发工作。
  - **剔除与渲染列表分离**：单个 `asyncCullExecutor`（单线程，:115）+ `pendingTask`，结果存 `EnumMap<CullType, SectionTree> cullResults`（:121），相机稳定帧复用 `findBestTree()`（:272）。
  - 列表输出 `SortedRenderLists` / `DeferredTaskList`，`importantTasks` 用 `ReferenceLinkedOpenHashSet` 按 `DeferMode` 分类（:100）。

### 4.2 异步网格构建（快照 + 线程池 + 结果上传）

- 文件：`common/.../render/chunk/compile/executor/ChunkBuilder.java`、`compile/tasks/ChunkBuilderMeshingTask.java`、`world/LevelSlice.java`、`world/cloned/ClonedChunkSection.java`
- 关键设计点：
  - **离线快照**：`LevelSlice` 类注释明确写"copies the data for use in off-thread operations… see a consistent snapshot"；`ClonedChunkSection` 复制 `PalettedContainerRO<BlockState>`、biome、`DataLayer[]` 光照数组、方块实体 map、`SodiumAuxiliaryLightManager`。worker 永不触碰活动世界。
  - **自建线程池而非 ForkJoin**：`ChunkBuilder` 构造时起 N 个 `"Chunk Render Task Executor #i"` 线程（`thread.setPriority(NORM_PRIORITY - 2)`，:36-45），配 `ChunkJobQueue` / `ChunkJobCollector`。
  - **背压**：`getTotalRemainingDuration(durationPerThread)`（:52-54）返回"本帧还应派发多少工作"，派发超过预算会阻塞。
  - 输出 `BuilderTaskOutput.getResultSize()` 惰性计算（`compile/BuilderTaskOutput.java`），配合 `MeshResultSize` 做上传排队。

### 4.3 半透明排序：BSP + 拓扑 + 相机移动触发

- 文件：`render/chunk/translucent_sorting/`（`SortBehavior.java`、`bsp_tree/InnerPartitionBSPNode.java`、`data/DynamicBSPData.java`、`trigger/SortTriggering.java`）
- 关键设计点：
  - **排序策略是可组合枚举**：`SortBehavior` 把 `SortMode(NONE/STATIC/DYNAMIC)` × `PriorityMode(NONE/NEARBY/ALL)` × `DeferMode(ZERO_FRAMES/ONE_FRAME/ALWAYS)` 组合成 7 档（`OFF`、`S`、`DF`、`N1`、`N0`、`A1`、`A0`），用户可在配置里选延迟与优先级。
  - **对齐 BSP 分区**：`InnerPartitionBSPNode` 做 block 对齐的 BSP 划分，类注释记录了被否定的方案（预排序 bucket、fastutil radix 排序更慢、惰性写 index 无收益）——很值得读的工程笔记；无法对齐但有交点时退化为拓扑排序近似（`TopoGraphSorting`）。
  - **触发式重排**：`trigger/` 下 `CameraMovement` + `GFNITriggers`/`GeometryPlanes`/`NormalPlanes`，只在相机跨越平面时才对相关区段重排。

### 4.4 遮挡剔除（图 + 树 + 位掩码）

- 文件：`render/chunk/occlusion/OcclusionCuller.java`、`DirectionalVisGraph.java`、`VisibilityEncoding.java`、`SectionTree.java`、`render/chunk/tree/TraversableForest.java`
- 关键设计点：
  - **可见性是 long 位掩码**：`VisibilityEncoding.bit(from, to)`；`UP_DOWN_OCCLUDED` 等常量把"沿某轴必然不可见"预编码（`OcclusionCuller.java:53-55`）。
  - 分档剔除 `CullType`（frustum / regular / wide / local）各有 BFS 宽度（`bfsWidth`，宽档检查邻区块），`getAngleVisibilityMaskLocal` 用相机相对偏移快速砍掉轴向（:57-78）。
  - 惰性树化：`SectionTree` 持有 `TraversableForest<TraversableTree>`，可以 `markGraphDirty()` 增量重建而不是全量重算。

### 4.5 GPU 显存管理：Region + Arena + 堆外元数据

- 文件：`render/chunk/region/RenderRegion.java`、`render/chunk/data/SectionRenderDataStorage.java`、`gpu/arena/BufferArena.java`、`gpu/arena/ArenaAggregator.java`、`gpu/arena/staging/MappedStagingBuffer.java`
- 关键设计点：
  - `RenderRegion` 固定 8×4×8 = 256 段（`REGION_SIZE`），容量按 `SECTION_VERTEX_COUNT_ESTIMATE = 756` 顶点 + index 估算（`RenderRegion.java:30-33`）；同区块内共享 index buffer（`SHARED_INDEX_DATA_INDEX = -1`）。
  - `SectionRenderDataStorage` 把每段顶点/索引的偏移、`sliceMask`、`facingList` 写进 **堆外内存**（`pMeshDataArray` + `SectionRenderDataUnsafe`），GC 压力为零，buffer 扩容时 `onBufferResized()` 回写全部偏移。
  - `BufferArena` = 段链表分配器 + 容量增长系数（`EXPECTED_SIZE_TARGET_FACTOR = 1.5f`）；`ArenaAggregator` 负责跨 arena 的复用、碎片整理限速（`DEFRAG_BYTES_PER_FRAME`）、分配速率过高时暂停释放（`PAUSE_DEALLOCATION_ABOVE_FRACTION`）。
  - 上传经 staging buffer 抽象（`StagingBuffer` / `MappedStagingBuffer` / `MojangStagingBuffer`），`getUploadSizeLimit(frameDuration)` 是帧时长到字节预算的换算点。

### 4.6 渲染后端抽象 + 配置 UI（对外 API）

- 后端：`render/chunk/ChunkRenderer.java` 接口（prepare / render / rotate / delete），实现 `DefaultChunkRenderer`、`ShaderChunkRenderer`；`gpu/device/backend/DrawBackend.java` 在启动时探测 `GpuDevice`（`GpuDeviceAccessor` mixin）选择 `OPENGL` / `VK_MULTIDRAW` / `VK_INDIRECT`，分别对应 `GLDrawBatch`、`VKMultiDrawBatch`、`VKIndirectDrawBatch`。
- 配置：早期/晚期两阶段注册（`api/config/ConfigEntryPoint.java` 的 `registerConfigEarly` / `registerConfigLate`），结构 `Config → ModOptions → Page → OptionGroup → Option`，全部经 Builder（`client/config/builder/*BuilderImpl.java`）构建，支持 overlay 别人已有选项、动态值依赖（`config/value/DependentValue.java`）、状态化选项（`StatefulOptionBuilder`）。详见第 8 节。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无。** 在 `common/src`、`fabric/src`、`neoforge/src`、`frapi/src` 全量 grep `CustomPacketPayload|ClientboundCustomPayload|StreamCodec|PayloadRegistrar|ServerPlayer` 零命中；mods.toml 只有客户端依赖（`dist = Dist.CLIENT`），是纯客户端渲染 mod。
- **数据驱动（方法级）**：
  - Mixin 开关外置：`client/data/config/MixinConfig.java` 从 `./config/sodium-mixins.properties` 读用户规则，并接受**其他 mod 声明的覆盖**——Fabric 读 `fabric.mod.json` 自定义字段 `sodium:options`（`fabric/.../FabricMixinOverrides.java:22-50`，键为 mixin 包路径、值为 boolean），NeoForge 读 mods.toml `modproperties`（`neoforge/.../ForgeMixinOverrides.java`），结果汇总为 `List<MixinOverride>` 交给 mixin 插件。非法类型会打印警告并忽略。
  - 资源侧：`common/src/main/resources/assets/minecraft/models/block/*.json` 只手写覆盖原版方块模型（beacon、hopper、cauldron、pitcher_crop 等），README 说明目的是"减少顶点数、UV 与原版一致"；`assets/sodium/lang/en_us.json`（107 行）。
- **配置**：`SodiumOptions`（Gson + `FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES`，落盘 `sodium-options.json`，`common/.../gui/SodiumOptions.java`）保存用户值；`gson` 排除 private 字段，加载失败则只读模式 + 控制台警告（`SodiumClientMod.loadConfig()`）。另有 `data/fingerprint/`（FingerprintMeasure → HashedFingerprint 落盘）用于检测硬件/配置变更后重置提示状态。
- **datagen：无。** grep `DataGenerator|FabricDatagen|DataProvider|runDatagen` 零命中；模型与 lang 为手写提交。

## 6. Mixin

- 配置文件：`common/src/main/resources/sodium-common.mixins.json`（84 条 client 条目，`"plugin": "net.caffeinemc.mods.sodium.mixin.SodiumMixinPlugin"`，`compatibilityLevel: JAVA_17`，`injectors.defaultRequire = 1`，`overwrites: {conformVisibility: true, requireAnnotations: true}`，`mixinextras.minVersion = 0.5.2`）、`fabric/src/main/resources/sodium-fabric.mixins.json`（4 条）、`neoforge/src/mod/resources/sodium-neoforge.mixins.json`（11 条，含 `platform.neoforge.*`）、`frapi/src/main/resources/sodium-frapi.mixins.json`（4 条，package `...mixin.frapi`）。
- 规模：92 个 mixin 类；注入注解统计 `@Mixin` 89、`@Inject` 63、`@Overwrite` 19、`@Redirect` 12、`@WrapOperation` 6、`@Accessor` 5、`@Invoker` 4、`@ModifyExpressionValue` 1。
- 代表性 mixin 与 hook 目标：
  - `mixin/core/render/world/LevelRendererMixin.java`（`@Mixin(LevelRenderer.class)`，`@Unique` 静态 `EnumMap<ChunkSectionLayer, Int2ObjectOpenHashMap<List<RenderPass.Draw<GpuBufferSlice[]>>>>`）——接管地形提交路径，替换为 Sodium 的 `ChunkSectionsToRender` 批量提交。
  - `mixin/core/render/world/LevelExtractorMixin.java` —— `@Inject(method = "extract", at = @At("HEAD"))` 取 `((LevelRendererExtension) Minecraft.getInstance().levelRenderer).sodium$getWorldRenderer()`；`extractVisibleBlockEntities` 处 `cancellable = true` 用 Sodium 自己的可见方块实体列表替换原版。
  - `mixin/core/render/VertexFormatMixin.java` —— `@Mixin(VertexFormat.class) implements VertexFormatExtensions`，`@Inject(method = "<init>", at = @At("RETURN"))` 里 `VertexFormatRegistry.instance().allocateGlobalId(...)`，用 `@Unique int sodium$globalId` 扩展原版类。
  - `mixin/features/render/entity/cull/EntityRendererMixin.java` —— 注入 `shouldRender`，改由 `SodiumWorldRenderer.isEntityVisible` 判定（实体视锥剔除）。
  - `mixin/core/GpuDeviceAccessor.java`（`sodium$getBackend()`）、`mixin/core/render/world/ViewAreaMixin.java`（`lambda$new$0` HEAD 注入防 NPE）、`mixin/workarounds/context_creation/{WindowMixin,GlSurfaceMixin}.java`（驱动兼容）、`mixin/platform/neoforge/*`（NeoForge 侧专用，如 `ClientHooksMixin`、`ModelDataMixin`、`LevelSliceMixin`）。
- 插件逻辑：`mixin/SodiumMixinPlugin.java:47-84` `shouldApplyMixin` 先按包名前缀校验（非本包直接禁用并报错），再查 `MixinConfig.getEffectiveOptionForMixin`，未匹配到规则的 mixin 会被当作外来 mixin 禁用；被用户/mod 强制改写的会在日志中打印规则名与来源。另有保护：检测到 `embeddium` 在加载列表时全部 mixin 不应用（:37-41）。
- 放宽可见性：三份 access widener（`accessWidener v1 official`，即官方（Mojang）命名）：`common/src/main/resources/sodium-common.accesswidener`（26 条）、`fabric/.../sodium-fabric.accesswidener`（27 条）、`frapi/.../sodium-frapi.accesswidener`（29 条）；NeoForge 等价物是 `neoforge/src/mod/resources/META-INF/accesstransformer.cfg`（并开启 `validateAccessTransformers = true`）。

## 7. 值得学的 5 条具体做法

1. **用 ServiceLoader + `ServiceProvider` 做多平台抽象，通用代码零平台分支**
   做法：接口放 common（如 `client/services/PlatformLevelAccess.java`），加载器实现由 `META-INF/services/<接口全名>` 文件绑定，`Services.loadConditionalOr` 支持"没装就退化为 no-op"。
   文件：`common/src/main/java/net/caffeinemc/mods/sodium/client/services/Services.java:14-44`、`common/.../client/services/FRAPIRegistrar.java:3`。
   适用：NeoForge + Fabric 双平台 mod 的平台差异层，比 `if (FabricLoader...)` 更干净。
2. **把 mixin 开关做成数据驱动的"冲突仲裁"**
   做法：每个 mixin 包有规则名与默认开关，用户 `config/sodium-mixins.properties` 和其他 mod 的元数据（`sodium:options` 对象）都能覆盖，插件在 `shouldApplyMixin` 里仲裁并打印来源。
   文件：`common/src/main/java/net/caffeinemc/mods/sodium/mixin/SodiumMixinPlugin.java:47`、`common/.../client/data/config/MixinConfig.java:26-90`、`fabric/.../FabricMixinOverrides.java:22`。
   适用：与同类优化 mod（OptiFine/Embeddium/Indium）共存时避免硬冲突；也可借鉴"未登记的 mixin 一律禁用"这一安全默认。
3. **duck 接口 + `@Unique` 字段扩展原版类，而不是 Overwrite**
   做法：`@Mixin(X.class) implements XExtensions` 加 `@Unique` 字段/方法，其他 mod 通过接口调用。
   文件：`common/src/main/java/net/caffeinemc/mods/sodium/mixin/core/render/VertexFormatMixin.java:19-37`、`common/.../world/LevelRendererExtension.java`。
   适用：需要给原版对象挂状态并暴露给第三方；`@Overwrite` 仅 19 处且集中在 workaround。
4. **离线快照 + 帧时长预算 + 估计器，三件套治卡顿**
   做法：worker 线程只读 `LevelSlice`/`ClonedChunkSection` 的复制数据；派发前用 `getTotalRemainingDuration()` 做背压；上传只允许消耗 `0.3f` 帧时长，并用 `ExpDecayLinear2DEstimator` 自适应估计任务耗时。
   文件：`common/.../render/chunk/compile/executor/ChunkBuilder.java:52`、`common/.../render/chunk/RenderSectionManager.java:64-77`、`common/.../client/world/LevelSlice.java:39-45`。
   适用：任何需要后台线程处理世界数据的 mod（实体 AI 预计算、结构扫描、Create 的机械网络求解）。
5. **分离"数据/结构"与"渲染值"的配置 API：两阶段注册 + Builder + overlay**
   做法：`ConfigEntryPoint.registerConfigEarly/Late` 覆盖"窗口创建前就要读到"与"常规"两种时机；`ConfigBuilder` 产出 `ModOptions → Page → OptionGroup → Option`，允许 overlay 只改他人选项的少数字段；所有用户可见字符串走 translation key。
   文件：`common/src/api/java/net/caffeinemc/mods/sodium/api/config/ConfigEntryPoint.java`、`common/.../client/config/ConfigManager.java:64-120`、`common/src/api/java/net/caffeinemc/mods/sodium/api/config/USAGE.md`。
   适用：想让别的 mod 往自己界面加配置、又不想被 mixin 的库/前置 mod。

（附）**入口分流技巧**：NeoForge 侧把 pre-launch workaround 放进独立 jar，用 `FMLModType = LIBRARY` + `jarJar(project(":neoforge", "mod"))`，使"早期加载的 service"与"常规 mod 代码"物理隔离，避免 pre-launch 阶段触碰未变换的 Minecraft 类（`common/build.gradle.kts:73-74` 注释、`neoforge/build.gradle.kts` 的 `tasks.jar`）。

## 8. 对外 API（Sodium 非前置库，但提供 API 包）

- API 独立 source set `common/src/api`，产出独立 `apiJar` / `api-sourcesJar`（`fabric/build.gradle.kts:113-125`、`neoforge/build.gradle.kts:107-125`），Maven 坐标 `net.caffeinemc:sodium-<platform>-api`。
- 包与入口：
  - `net.caffeinemc.mods.sodium.api.blockentity.BlockEntityRenderHandler`（`addRenderPredicate` / `removeRenderPredicate`，`@ApiStatus.Experimental AvailableSince("0.6.0")`）
  - `net.caffeinemc.mods.sodium.api.config.*`：`ConfigEntryPoint`、`ConfigEntryPointForge`（NeoForge 注解，值 = modId）、`ConfigState`、`StorageEventHandler`、`option.{OptionBinding,OptionFlag,FlagHook,Range,Validator,SteppedValidator,ControlValueFormatter,NameProvider,OptionImpact}`、`structure.{ConfigBuilder,ModOptionsBuilder,PageBuilder,OptionPageBuilder,ExternalPageBuilder,OptionGroupBuilder,OptionBuilder,BooleanOptionBuilder,IntegerOptionBuilder,EnumOptionBuilder,StatefulOptionBuilder,ExternalButtonOptionBuilder,ColorThemeBuilder}`
  - `api.vertex.buffer.VertexBufferWriter`（第三方 `VertexConsumer` 必须实现此接口并回答 `canUseIntrinsics()`，否则 Sodium 会抛出带 issue 链接的 `IllegalArgumentException`，`VertexBufferWriter.java:34-40`）
  - `api.vertex.format.{VertexFormatRegistry,VertexFormatExtensions,common.*}`、`api.vertex.serializer.{VertexSerializer,VertexSerializerRegistry}`
  - 低层工具：`api.memory.MemoryIntrinsics`、`api.math.MatrixHelper`、`api.texture.SpriteUtil`、`api.util.{ColorABGR,ColorARGB,ColorMixer,ColorU8,NormI8}`
- 内部桥接方式：API 接口用 `DependencyInjection.load(apiClass, "impl 全类名")` 反射绑定实现（`common/src/api/java/net/caffeinemc/mods/sodium/api/internal/DependencyInjection.java`），失败即抛运行时异常（非静默降级）。
- 外部 mod 接入方式（三选一，取决于要做什么）：
  1. 加视频配置页 → 注册 `ConfigEntryPoint`：Fabric 用 entrypoint key `sodium:config_api_user`（`ConfigManager.CONFIG_ENTRY_POINT_KEY`）；NeoForge 用 mods.toml `modproperties["sodium:config_api_user"] = "类名"`，或在类上标 `@ConfigEntryPointForge("modid")`（`neoforge/.../config/ConfigLoaderForge.java:27-70`）。
  2. 依赖 Sodium 的 renderer → FRAPI（`fabric-renderer-api-v1`），Sodium 声明 `fabric:provides = ["indium"]`。
  3. 关掉某个 Sodium mixin → mod 元数据里写 `sodium:options` 覆盖（见第 5 节）。

## 未确认项

- `fabric/src/main/resources/fabric.mod.json` 与 `assets/sodium/lang/en_us.json` 在当前工作区物理缺失（仅存在于 git 对象中，本次用 `git show HEAD:<path>` 读取内容），因此它们的完整内容未逐行核对。
- 版本号 `26.3-rc-1` / `26.2.0.0-beta` / `com.mojang.renderpearl.*` 命名体系为本仓库自述事实，未与外部版本表比对。
