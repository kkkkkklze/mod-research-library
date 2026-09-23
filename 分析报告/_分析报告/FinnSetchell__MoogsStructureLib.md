# FinnSetchell/MoogsStructureLib 源码分析报告

## 1. 基本信息

- Mod 名：Moog's Structure Lib；mod_id：`moogs_structures`；作者：FinnDog（FinnSetchell）；mod_version 3.1.3。
- 目标版本（`gradle.properties`）：`minecraft_version=1.21.11`（`minecraft_version_range=1.21.11`）、`neo_form_version=1.21.11-20251209.172050`、Java 21、`forge_version=61.1.0`、`neoforge_version=21.11.12-beta`、`fabric_version=0.140.2+1.21.11`；四模块 `common/fabric/forge/neoforge`（settings.gradle）。
- Gradle：`fabric-loom 1.13-SNAPSHOT`、`net.neoforged.moddev 2.0.123` + 自建 `buildSrc` 插件 `multiloader-common`/`multiloader-loader`（含 mcgradleconventions loader attribute）。许可证 LGPL-3.0；CREDITS 与代码注释多次标注来自 TelepathicGrunt 的 structure mod template 与 YUNG's API。
- 依赖：`compileOnly` Cloth Config 21.11.153（软依赖，不打包；`gradle.properties` 注明 Forge 端自 1.21.3 后 Cloth 已停更、故 Forge 无游戏内配置界面）、mixinextras-common 0.3.5（`common/build.gradle`）、Fabric 侧 ModMenu 17.0.0；`runtimeOnly` 用 Curse maven 拉 5 个 Moog's 系结构 mod 做测试（neoforge/build.gradle:78-82）。
- 注意：本地目录是 git sparse-checkout（只落 `*.java/*.gradle/*.toml/*.mixins.json/*.md` 等），`fabric.mod.json`、`META-INF/services/*`、图标等经 `git ls-files` 确认存在但未下载到磁盘。

## 2. 规模与包结构

`find . -name '*.java' | wc -l` = **138**，总行数 **10681**。最大文件：`utils/OpenSimplex2F.java`(782)、`world/structures/pieces/PieceLimitedJigsawManager.java`(692)、`world/structures/GenericJigsawStructure.java`(417)、`utils/GeneralUtils.java`(297)、`config/MslConfig.java`(295)、`placements/AdvancedRandomSpread.java`(253)、`config/StructureListManager.java`(252)、`terrainadaptation/beardifier/EnhancedBeardifierHelper.java`(241)。

包分布：`world/processors`(16)、`mixins/structures`(12)、`modinit/registry`(10，含 `{fabric,forge,neoforge}` 各 3-4)、`utils`(7)、`modinit`(7)、`events/lifecycle`(6)、`client`(6)、`config`(5)、`world/structures/**`（pieces/placements/terrainadaptation/beardifier）、`misc/structurepiececounter`(3)、`datagen`/`gametest`/`platform`/`commands`。

## 3. 入口与注册

common 侧入口 `common/.../MoogsStructuresCommon.java`（`init()` 依次 `init()` 六个注册表 + `ReplaceVanillaManager.init()` + `StructureListManager.init()`，再把 4 个生命周期监听挂到自建事件类）。NeoForge 入口 `neoforge/.../MoogsStructuresNeoforge.java`：`@Mod(MODID)` 构造里注册 `ResourcefulRegistriesImpl::onRegisterForgeRegistries`，用**临时静态字段** `modEventBusTempHolder` 让 common 的注册能在 `init()` 期间拿到 eventBus，随后置 null；Fabric 入口 `MoogsStructuresFabric` 用 `FabricReloadListener` 包装把 Fabric 的 ServerLifecycle/Command/ResourceManager 事件桥接到自建的 `events/lifecycle/*`（`SetupEvent`/`ServerGoingToStartEvent`/`ServerGoingToStopEvent`/`RegisterReloadListenerEvent`，见 `events/base/EventHandler.java` 等）。

注册框架是自研 `ResourcefulRegistry`（`modinit/registry/`）：`ResourcefulRegistries.create(BuiltInRegistries.STRUCTURE_TYPE, MODID)` → `register("id", Supplier)` 返回 `RegistryEntry`；NeoForge 实现内部包 `DeferredRegister` 并在 `init()` 时 `register(modEventBusTempHolder)`（`NeoForgeResourcefulRegistry.java:26-38`）。结构类型注册值：`moogs_structures_generic_jigsaw_structure`、`moogs_structures_generic_nether_jigsaw_structure`，placement 类型 `advanced_random_spread`、`conditional_concentric_rings`。

## 4. 核心系统

- **数据驱动的 Jigsaw 结构**：`GenericJigsawStructure`（`CODEC` 用 `RecordCodecBuilder`）字段即 JSON schema：`start_pool/size/y_allowance/start_height/project_start_to_heightmap/cannot_spawn_in_liquid/terrain_height_radius_check/allowed_terrain_height_range/valid_biome_radius/pools_that_ignore_boundaries/max_distance_from_center/burying_type/use_bounding_box_hack/liquid_settings`；构造器对 `maxYAllowed < minYAllowed` 直接抛带指引文案的异常（:118-124）。
- **拼接与限流**：`PieceLimitedJigsawManager.assembleJigsawStructure(...)`（:51）记录 `Entry(piece, MutableObject<BoxOctree>, topYLimit, depth)`，用 `BoxOctree`（`utils/BoxOctree.java`）做快速包围盒重叠淘汰，配合 `misc/structurepiececounter/StructurePieceCountsManager`（datapack 数据 `msl_pieces_spawn_counts`）限制每块数量。
- **高级放置**：`AdvancedRandomSpread extends RandomSpreadStructurePlacement`：JSON 加 `exclusion_zone`/`super_exclusion_zone`/`spacing_key`/`structure_id`；构造时 `spacing = round(spacing*1.65)`；`owningSetId` 由服务器线程在 `serverAboutToStart` 里 stamp 成结构集 id（`MoogsStructuresCommon.stampOwningSetIds`），字段 volatile 供 worldgen 线程读；性能上把 (generation, spacing, separation) 压进一个不可变 `Memo` 存在单 volatile 字段，避免 C2ME 并发下读到撕裂值。
- **增强地形适应**：`EnhancedTerrainAdaptation` + `EnhancedBeardifierHelper/EnhancedJigsawJunction` + `mixins/terrainadaptation/BeardifierMixin`（3D 高斯核平滑地形，注明是 YUNG's API 的精简移植，缺 aquifer-override 部分）+ `PoolElementAdaptationOverride` 支持按 pool element 覆盖。
- **配置与"替换原版结构"**：`MslConfig`（`config/moogs_structures.json`，schema：`presets`/`spacing{universal_multiplier,per_mod,per_structure}`，单 `generation` 计数器 + volatile 不可变快照供多线程读）；`ReplaceVanillaManager`（datapack `data/<modid>/moogs_structures/replace_vanilla.json` 声明 preset 与替换绑定，`BY_VANILLA_STRUCTURE` 索引）；`StructureListManager` 自动扫描每个已加载 mod jar 内 `worldgen/structure_set/*.json` 生成配置界面列表，mod 无需额外声明。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自建 payload；跨端只靠配置/数据包与客户端配置界面。
- 数据驱动：`StructureManifestReloadListener extends SimplePreparableReloadListener`（注释说明用 prepare/apply 而非 reload 签名以便兼容）+ `StructurePieceCountsManager`、`TrialSpawnerConfigManager`，统一经 `RegisterReloadListenerEvent` 注册（`MoogsStructuresCommon.registerDatapackListener`）。
- 配置：文件（MslConfig）+ Cloth Config 界面（Fabric ModMenu 集成、NeoForge 配置屏 `MoogsStructuresConfigScreenNeoforge`）；`PlatformConfig` SPI 由各 loader 的 `config.<loader>.PlatformConfigImpl` 经 `META-INF/services` 提供（读 loader 元数据、枚举 mod id、直接读其他 mod jar 内的 json）。
- datagen：`neoforge/.../datagen/StructureNbtUpdater`（`DataProvider`，用 DataFixers 批量升级结构 NBT，来源标注 ImmersiveEngineering）。gametest：`EquipArmorStandProcessorTest`。

## 6. Mixin

四份配置：`common/.../moogs_structures-common.mixins.json`（16 个，`package com.finndog.moogs_structures.mixins`）、`-fabric`（structures.EntityProcessorMixin）、`-forge`/`-neoforge`（structures.StructureEntityProcessorMixin、StructurePoolMixin，包 `...mixins.{forge,neoforge}`）。

代表：
- `mixins/structures/DisableVanillaStructureMixin.java`：`@Inject(method="tryGenerateStructure", at=@At("HEAD"), cancellable=true)` 到 `ChunkGenerator`，据 `ReplaceVanillaManager.shouldCancelVanilla / MslConfig.isStructureDisabled` 直接 `setReturnValue(false)`；注释强调必须镜像目标完整签名（含尾部 `ResourceKey<Level>`）否则 apply 失败。
- `mixins/terrainadaptation/BeardifierMixin.java`：`@Inject` `Beardifier.forStructuresInChunk`(RETURN,cancellable) 与 `compute`(RETURN, cancellable) 两次返回点改写，`implements EnhancedBeardifierData` 并用 `@Unique` 前缀字段（`moogs_structures_enhancedPieceIterator`）承载状态。
- `fabric/.../EntityProcessorMixin.java`：`@Mixin(StructureTemplate.class)`，在 `placeInWorld` 调 `placeEntities` 的 INVOKE 点用 `ThreadLocal<StructureProcessingContext>` 捕获上下文，再在 `placeEntities` HEAD 自行生成实体并取消原版，实现 Fabric 上缺失的 `processEntity` 钩子；只在该结构真的用 `StructureEntityProcessor` 时生效。
- 另有资源侧 `NamespaceResourceManagerAccessor`/`BuiltInRegistriesMixin`，特征侧 `NoBasaltColumnsInStructuresMixin`/`NoDeltasInStructuresMixin`。AT 与 accesswidener 各一份，内容一致（`VillagerTrades$TreasureMapForEmeralds`、`FallbackResourceManager$PackEntry`）。

## 7. 值得学的 5 条做法

1. 结构类型/placement 全部做成 `RecordCodecBuilder` 的 `MapCodec`，JSON 字段即 API，无需 datagen（`GenericJigsawStructure.java:45-62`）。
2. 用 `ServiceLoader` + `META-INF/services/<FQN>` 做 loader 抽象（`Services.java:7`、`IRegistryPlatform`、`PlatformConfig`），比 if/else 判断 loader 更整洁。
3. 自研 `ResourcefulRegistry`/`RegistryEntry` 统一四 loader 注册 API，只让 loader 模块实现细节（`modinit/registry/`）。
4. 配置读路径全部"volatile 不可变快照 + generation 计数器"，让 worldgen 多线程可安全读取（`MslConfig.java:44-52`、`AdvancedRandomSpread.Memo`）。
5. 跨 mod 兼容 mixin 用 `@Accessor`/`@Invoker` 只取数据、行为注入一律 `cancellable` 且在 HEAD 快速返回（`mixins/structures/*`），并把"从其他 mod jar 里读结构集 JSON"做成自动发现，替整合包减负（`StructureListManager`）。

## 8. 公开 API（库模组）

- 扩展方式：**不写 Java**——在数据包里用它的结构类型 `moogs_structures:moogs_structures_generic_jigsaw_structure`、`..._generic_nether_jigsaw_structure` 与 placement 类型 `advanced_random_spread`/`conditional_concentric_rings` 写结构/结构集 JSON；可选 manifest `data/<modid>/moogs_structures/replace_vanilla.json`（含 `structures.mod_slug/mod_name/entries` 用于配置界面与在线预览链接）。
- Java 侧扩展点：`modinit/registry/*`（`ResourcefulRegistry`、`RegistryEntry`）、`platform/IRegistryPlatform`、`config/PlatformConfig`（均由各 loader 通过 `META-INF/services` 实现）、`world/processors/*`（16 个 `StructureProcessor`：`PillarProcessor`、`StructureEntityProcessor`、`EquipArmorStandProcessor`、`RemoveFloatingBlocksProcessor`、`VaultRandomizingProcessor` 等）、`world/placements/*` 与 `EnhancedTerrainAdaptation` 作为可复用构造块。
- 文档：`docs/wiki/*`（Getting-Started、Structure-Files、Template-Pools、Structure-Sets、Placement-Systems、NBT-Files、Advanced-Topics + 4 个完整示例），对外接入说明齐全。
