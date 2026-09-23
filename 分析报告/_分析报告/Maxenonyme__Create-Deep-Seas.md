# Maxenonyme/Create-Deep-Seas 源码分析报告

## 1. 基本信息

- **Mod 名 / mod_id**：Create Deep Seas / `create_submarine`（主）；同一 JAR 内还打包了 **`create_abyss`（Create Abyss）** 与 **`create_high_seas`（Create High Seas）** 两个内部子 mod（`gradle.properties:20-30`）
- **作者**：Maxenonyme；包名 `com.maxenonyme.createsubmarine` / `com.maxenonyme.AbyssDimension` / `com.maxenonyme.highseas`
- **目标 MC / 加载器**：Minecraft 1.21.1 + NeoForge `21.1.227`（`gradle.properties:11,13`），Java 21，Parchment `2024.11.17`
- **Gradle 插件**：`net.neoforged.moddev` 2.0.141（ModDevGradle）+ `java-library`、`idea`（`build.gradle:2-4`）
- **许可证**：All Rights Reserved（闭源）
- **编译依赖**（`build.gradle:108-128`）：
  - `curse.maven:create-328085:${create_file_id}`（Create，**非 slim**）
  - `net.createmod.ponder:ponder-neoforge:1.0.82+mc1.21.1`、`flywheel-neoforge-1.21.1:1.0.6`
  - **`foundry.veil:veil-neoforge-1.21.1:3.6.2`**（着色器/雾效，implementation）
  - `dev.ryanhcode.sable:sable-neoforge-1.21.1:1.2.2`：**同时**以 `compileOnly`（modrinth）和 `implementation files("libs/sable-neoforge-1.21.1-1.2.2.jar")` 引入 —— 核心物理 API
  - `jarJar(api("dev.ryanhcode.sable-companion:sable-companion-common:[1.5.0,)"))` —— 把自己依赖的 Sable Companion **内嵌**分发给下游
  - `compileOnly(name: 'aeronautics-...jar')`、`compileOnly(name: 'simulated-...jar')`（`libs/` 下同时放了 1.1.3 与 1.3.0 两版 jar）
  - `compileOnly "maven.modrinth:sodium:mc1.21.1-0.6.13-neoforge"`
  - 运行时辅助：`lithostitched`（深海洋世界生成）、`fusion-connected-textures`
- **mods.toml 依赖策略**（`src/main/templates/META-INF/neoforge.mods.toml`）：`sable`、`aeronautics`、`ponder`、`create` 均为 `required`；`sodium 0.6.13` 被声明为 **`type="incompatible"`**（`side="CLIENT"`），`fusion` / `lithostitched` 为 `optional`
- **AccessTransformer**：`src/main/resources/META-INF/accesstransformer.cfg` 仅 1 行，放宽 `FallingBlockEntity` 的构造器

## 2. 源码规模与包结构

实测：**174 个 java 文件，19496 行**。三个包根：

| 包（第 3 层） | 文件数 | 内容 |
|---|---|---|
| `createsubmarine/submarine/mixin`（+compat） | 21 + 11 | 主 mixin 与兼容 mixin |
| `createsubmarine/submarine/block`（+entity） | 21 + 13 | 23 种机器方块与方块实体 |
| `createsubmarine/submarine/system` | 16 | 压力/沉没/电缆/交互等 tick 系统 |
| `createsubmarine/submarine/client`（+renderer） | 9 + 5 | 雾效、裂纹渲染、欢迎屏 |
| `createsubmarine/submarine/util` | 6 | `SubLevelRegistry`、`SablePhysicsHelper` 等 |
| `createsubmarine/submarine/network` | 6 | 6 个 payload |
| `createsubmarine/submarine/config` | 4 | `SubmarineConfig`、`HullStrengthConfig` 等 |
| `createsubmarine/submarine/compartment` | 2 | **闭舱体检测算法核心** |
| `AbyssDimension/*` | ~19 | 深渊维度、实体、BOSS 般的水母/鲨鱼 |
| `highseas` | 4 | 船体水剔除 |
| `createsubmarine/worldgen` | 1 | 自定义 `DensityFunction` |

最大文件：`block/entity/DecompressionChamberBlockEntity.java` 719 行、`ponder/SubmarinePonderScenes.java` 653、主类 `CreateSubmarine.java` 554、`AbyssDimension/block/entity/SubmarineLianaBlockEntity.java` 530、`block/entity/BallastTankBlockEntity.java` 516、`compartment/CompartmentTracker.java` 500、`AbyssDimension/system/SubmarineLianaCommand.java` 484、`system/SubmarineInfoCommand.java` 475、`block/entity/UnderwaterMineBlockEntity.java` 468、`block/entity/PulleyBlockEntity.java` 462。

## 3. 入口与注册

主类 `src/main/java/com/maxenonyme/createsubmarine/CreateSubmarine.java:39-372`，**纯原生 `DeferredRegister`**（无 Registrate），且几乎全部注册项塞在同一个类里：`BLOCKS/ITEMS/BLOCK_ENTITIES/SOUNDS/MENUS/MOB_EFFECTS/FLUIDS/FLUID_TYPES/CONDITION_CODECS/DENSITY_FUNCTIONS` 共 10 个 DeferredRegister（`:60-131`）。构造器（`:330-372`）除逐个 `register(modEventBus)` 外，把 **16 个 `NeoForge.EVENT_BUS` 监听器**集中注册（压力、沉没、交互、钢缆物理、电缆通电、命令、扳手修复、生命周期），并使用 `modEventBus.addListener(EventPriority.HIGH, WrenchRepairHandler::onRightClickBlock)` 指定优先级（`:357-358`）。三处值得注意：

```java
// Create API 接入（:486-497）
com.simibubi.create.api.stress.BlockStressValues.IMPACTS.register(SUBMARINE_PROPELLER.get(), () -> 4.0);
TooltipModifier.REGISTRY.register(SUBMARINE_PROPELLER_ITEM.get(),
        TooltipModifier.mapNull(KineticStats.create(SUBMARINE_PROPELLER_ITEM.get())));
DisplaySource.BY_BLOCK_ENTITY.register(BAROMETER_BE.get(), List.of(SubmarineDisplaySources.BAROMETER.get()));
// 可选 mod（Simulated）的 Tab 注入用纯反射，避免硬依赖（:501-553）
Class<?> regClass = Class.forName("dev.simulated_team.simulated.registrate.SimulatedRegistrate");
List<Supplier<Item>> tabItems = (List<Supplier<Item>>) regClass.getField("TAB_ITEMS").get(null);
```
另注册了非标准注册表 `ForceGroups.REGISTRY_KEY` 上的 `ForceGroup`（`:42-57`，Sable 的力组 API，用于压舱/浮子），以及一个自定义 `ICondition`（`ConfigCondition`，`:72-76`）用于按配置开关数据加载。子 mod 入口 `AbyssDimension/CreateAbyss.java:43-63` 有特别处理：**`FMLEnvironment.production` 为真时直接 `return`，内容不在正式版启用**。

## 4. 核心系统

### 4.1 舱室检测与"水下假空气"（CompartmentTracker / CompartmentDetector）
本 mod 最核心的子系统，共 739 行。`CompartmentDetector.java:19-22` 定义 `record Component(Set<BlockPos> internal, Set<BlockPos> hull, boolean sealed, BlockPos anchor)`。算法为**体素游标 + 增量 BFS**：`IncrementalScanState`（`:25-95`）持有 `curX/curY/curZ` 三轴游标、`visited`、`total`、`ChunkCache`，`advanceCursor()` 按 Z→Y→X 推进（`:83-94`）；遇到可渗透方块就 `startBfs(start)` 扩展成连通分量，BFS 触达边界则 `activeSealed=false`（即判断"是否闭舱"），`stepScan(st, budget)`（`:106-）按预算分帧执行，配合 `SubmarineConfig.OXYGEN_MAX_FILL_BLOCKS` 上限（默认 50 万方块）防止卡服。`CompartmentTracker.java` 是它的状态缓存层：11 个 `ConcurrentHashMap<UUID, ...>` 静态表（`:29-40`），`update()`（`:67-86`）写回并算世界包围盒（半径 = 最大边长 × 0.75，`:81-83`）。关键设计点：
- **`sealedSnapshot` 数组 + `volatile`**（`:41,48,51-65`）：热路径查询用不可变快照 + `ThreadLocal<Vector3d>` 复用向量，避免并发遍历 HashMap 与 GC 压力。
- **快速排除链**（`findContainingSub`，`:384-409`）：全局 AABB → 维度 → 单艇 AABB → `pose().transformPositionInverse` 转局部坐标 → `LongOpenHashSet` 查 cell，逐级短路。
- **位姿变化量阈值**（`poseMovedEnough`，`:197-208`）：用四元数点积 `|dot| < 1.0 - rotEps` 判断旋转是否超阈值，配合 `recordPose` 决定是否需要重扫——避免每 tick 全量重算。
- **`onPlotBlockChanged`**（`:224-237`）把方块变更标脏 `STRUCTURE_DIRTY`，空闲才 `beginScanIfIdle` 增量扫描。
- **`isInSealedExact` 额外检查局部流体**（`:341`）：即使坐标落在闭舱 cell 内，若该处是水（`plotFluidAt`，`:346-354`）则判为不在空气中。
- `getLiedBlockState` 对闭舱内返回 `Blocks.AIR`（`:412-417`）—— 即向第三方"撒谎"，让舱内行为等同陆地。

### 4.2 深海压力与船体强度（SubmarinePressureSystem + HullStrengthConfig）
`system/SubmarinePressureSystem.java` 每 20 tick 跑一次（`:32,117-126`）。流程：`measureSurfaceY` 从潜艇中心向上最多 `MAX_WATER_SCAN = 400` 格找水柱顶（`:178-206`）→ 缓存深度 → 在包围盒内**随机采样** `samples = clamp(volume/150, 15, 250)` 个点（`:155-157`）而非全区遍历。单点判定 `applyPressure`（`:208-285`）依次排除：不属于任何未失效闭舱、不在 `comp.hull()` 内、六个面都不朝外（`facesExterior`）、深度未超该方块 `maxWaterDepth`，然后按 `depthMultiplier = depth / maxWaterDepth` 放大 `implosionChance`。**裂纹是 4 级状态机**（`:252-278`）：`CRACK_LEVELS` 累加，每级同步 `SubCrackPayload` 给玩家（`:301-308`）并喷 `DRIPPING_WATER` 粒子，到 4 级才 `plotLevel.destroyBlock` 并进 `BREACHED_PLOT` + 触发 `SubmarineSinkingSystem.onCrashed`。性能保护：单次 tick 的 `breakBudget = {4}` 限制最多爆 4 块（`:154,260-269`）。

`config/HullStrengthConfig.java` 是**独立的 JSON 配置体系（不走 ModConfigSpec）**：`config/submarine_hull.json`，带 `_version`（当前 2）与 `_README` 自描述键（`:217-232`）。`load()`（`:36-75`）遍历 `BuiltInRegistries.BLOCK` 为每个方块补全条目，未知方块由 `autoCompute` 按 `hardness * 11.2 + resistance * 5.6` 再乘音效类型系数（METAL×1.8、STONE×1.1、WOOD×0.6、GLASS×0.3）推导，`implosionChance = clamp(1 - score/168, 0.05, 0.85)`（`:167-197`）；跨 mod 方块被 `GLOBAL_MAX_DEPTH_CAP` 夹紧（`:191-193`），本 mod 方块豁免并硬编码（`:199-215`）。版本不匹配或解析失败时 `backupBadFile()` 备份成 `.bak.<epoch>`（`:154-161,130-133`），配置损坏不崩游戏。

### 4.3 兼容子系统（compat）
`mixin/compat/` 下 11 个类按目标 mod 分目录：`sable/`（7）、`sodium/`（4，文件名含 CrashFix 的就有 Aeronautics 3 个 + Sodium 4 个 + Veil 1 个）。命名规律 `XxxCrashFixMixin` 说明作者把**每个已知崩溃点固化成独立 mixin**。同时 `SubmarineConfig` 里把出问题的 Sodium 版本直接声明为 hard incompatible（见 1. 节）。`util/SablePhysicsHelper`、`system/SableSnapshotQueue` 承担与 Sable 的对接。

### 4.4 客户端雾/水剔除与 Veil 着色器
`client/SubmarineFogHandler`、`client/renderer/SubmarineWaterCullBuffer`，加 6 个 Sable 侧 mixin（`SableSubLevelPocketFogMixin`、`SableSubLevelBEFogMixin`、`SableWaterOcclusionPreProcessorMixin`、`VanillaSubLevelRenderDispatcherMixin` 等）与 Veil 的 `FluidRenderHelperMixin`/`FogRendererMixin`/`LevelRendererMixin`。资源目录里还有 `assets/veil/pinwheel/shader_modifiers/minecraft/shaders/core` 与 `sodium/shaders/blocks` 下的着色器补丁——即**通过 Veil 的 Pinwheel 着色器修改器给原版与 Sodium 的 shader 打补丁**，而非整体替换着色器包。`Const` 常量 `DISABLE_WATER_OCCLUSION = false`（`CreateSubmarine.java:59`）作为总开关。

### 4.5 多 mod 打包与版本差异化
`sable.mixins.json`（10KB，`package: dev.ryanhcode.sable.mixin`）**放在仓库根目录并纳入版本控制**（`git ls-files` 可见），它不是本 mod 的 mixin 配置（mods.toml 只声明了 `create_submarine.mixins.json` 和 `create_abyss.mixins.json`），推测用于查阅/比对 Sable 自身的注入点（**未确认**）。`libs/` 下同时存放 Aeronautics/Simulated 的 1.1.3 与 1.3.0 两个版本 jar，配合 `UpdateChecker`/`DeepSeasUpdateScreen`/`LithostitchedMissingScreen`（缺 Lithostitched 时弹屏提示），是"面向玩家的依赖诊断"做法。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`CreateSubmarine` 内 `registerPayloads`（`:382-408`）注册 6 个 payload：S→C 的 `SubLevelBoundsPayload`、`SubCrackPayload`、`HullConfigSyncPayload`、`CameraShakePayload`；C→S 的 `ElectrolyzerTogglePayload`、`HullConfigEditPayload`。`CreateAbyss` 另有 1 个 C→S `StruggleSharkPayload`（`:65-71`）。协议版本用 `event.registrar(MOD_ID)`（以 modid 作版本号）。`SubCrackPayload.java:16-31` 用 `CustomPacketPayload.codec(write, ctor(FriendlyByteBuf))` 简写形式，比手写 StreamCodec 更短；handler 里再判 `FMLEnvironment.dist == CLIENT` 后进内部 `ClientHandler` 类（`:36-45`）——**把客户端类引用隔离在嵌套类里**，避免专用服务器加载客户端类。
- **配置**：两个层次。(a) `config/SubmarineConfig.java:28-133` 单个大 `ModConfigSpec`，按 `gameplay` / `hullStrength` / `mechanics` / `experimental` / `client` 五个 `builder.push(...)` 分组，注册为 `Type.COMMON`（`CreateSubmarine.java:331`）；dev 环境才定义 `WELCOME_SCREEN_SEEN`、`IGNORED_UPDATE_VERSION`（`:117-129`，生产环境置 null）。(b) `HullStrengthConfig` 的 GSON JSON + `HullConfigSyncPayload`/`HullConfigEditPayload` **服务端→客户端同步 + 客户端可编辑回传**，`applySynced()`/`update()`/`save()`（`:242-259`）三件套，配合 `client/HullStrengthConfigScreen`。另有 `config/FloaterTuning`、`config/SubmarineClientState`。
- **数据驱动**：注册了自定义 `DensityFunction` `OceanDepthOffset`（`CreateSubmarine.java:83-88`，`worldgen/`）用于加深海洋，由 `enableDeeperOceans`/`deeperOceansDepth` 配置驱动并通过 `OceanDepthOffset.refreshConfig()` 在 `ModConfigEvent` 时刷新（`:476-480`）；以及 `ConfigCondition`（自定义 `ICondition`）让数据包内容可按配置开关（`:72-76`）。`DEEPER_OCEANS_DEPTH` 注释里明确警告性能代价，并要求 Lithostitched。
- **datagen**：未发现 `GatherDataEvent`/`DataGenerator` 相关类（**未确认**：未做全仓库 grep，但 `@Mod` 类中无 datagen 监听器注册）。

## 6. Mixin

- `src/main/resources/create_submarine.mixins.json`：`required: true`、`JAVA_21`、`defaultRequire: 1`。**`mixins`（14 个）**：`LevelChunkMixin`、`RopeStrandHolderBehaviorMixin`、`ServerRopeStrandMixin`、`RapierVoxelColliderBakeryMixin`、`RopeWinchBlockEntityMixin`、`RopeConnectorBlockEntityMixin`、`SmartBlockEntityMixin`、`EntityWaterPhysicsMixin`、`FlowingFluidMixin`、`LargeWaterWheelPropulsionMixin`、`WaterWheelBlockEntityMixin` + compat 3 个。**`client`（26 个）**：绳索渲染（`ClientRopeStrandMixin`/`RopeStrandRendererMixin`/`RopeWinchRendererMixin`/`RopeConnectorRendererMixin`）、雾（`EntityPocketFogMixin`/`FogRendererMixin`）、水剔除（`WaterOcclusionRendererMixin`+`WaterOcclusionRendererAccessor`）、`LevelRendererMixin`、compat/`sable` 7 个、compat/`simulated` 1 个、Sodium 4 个、Aeronautics 3 个、Veil 2 个、Flywheel 1 个。
- `src/main/resources/create_abyss.mixins.json`：`mixins: []`，`client: ["AbyssSpecialEffectsMixin", "LightTextureMixin"]`。
- 代表 hook：
  - `mixin/EntityWaterPhysicsMixin.java:11-153`（`@Mixin(Entity.class)`）：**最值得读的一个**。11 处 `@Inject(HEAD, cancellable)` 覆盖 `isInWater` / `getFluidHeight(TagKey)` / `updateInWaterStateAndDoFluidPushing` / `isEyeInFluid` / `doWaterSplashEffect` / `isUnderWater` / `updateFluidOnEyes` / `getEyeInFluidType` / `updateSwimming` / `isSwimming`，统一由 `@Unique createsubmarine$isInsideAirtightSub()` 驱动；该方法做了**手写 tick+坐标缓存**（`:92-110`，`cacheTick/cacheX/...` 全字段比对，tick 内同位置直接返回），并在 `updateFluidOnEyes` 处直接 `ci.cancel()` 后清空 `wasTouchingWater`、`fluidHeight`、`forgeFluidTypeHeight`（`:32-40`）——一次性让实体在闭舱内完全"忘记"水。`@Shadow` 同时用了 `remap = false`（NeoForge 的 `forgeFluidTypeHeight`）与默认 remap（`wasTouchingWater`）。
  - `mixin/SmartBlockEntityMixin.java:15-41`（`@Mixin(value = SmartBlockEntity.class, remap = false)`）：对 Create 的 `SmartBlockEntity.write/read` `@At("TAIL")` 注入，用 `tag.putInt("createsubmarine$Energy", ...)` 把额外能量存进 **Simulated** 的绳索方块实体；方法名与 NBT key 都带 `createsubmarine$` 前缀防冲突，内部用 `instanceof` 而非类型参数限定。
  - `mixin/compat/sable/ServerSubLevelMixin.java:11-18`：`@Mixin(ServerSubLevel.class)` 对 `setSplitFrom` `HEAD` 注入，让子艇继承水雷所有权（`MineOwnershipRegistry.onSplit`）——最小的"一行式"兼容 hook。

## 7. 值得学的 5 条具体做法

1. **可序列化物理形体的增量/分帧检测算法**：`compartment/CompartmentDetector.java:25-104`（游标 + BFS + `stepScan(budget)`）+ `CompartmentTracker.beginScanIfIdle/stepScan/abortScan`（`:239-274`）+ 上限配置 `OXYGEN_MAX_FILL_BLOCKS`。适用：任何需要在大体积结构上做连通性/封闭性判断的 mod（飞船、密封舱、房间检测）。
2. **热路径查询用"不可变快照 + volatile + 多级 AABB 短路 + ThreadLocal 复用向量"**：`CompartmentTracker.java:41-65,285-311`。让"某坐标是否在船内"这种每帧可能被问上万次的问题保持 O(1)+低 GC。
3. **畸变输入不崩游戏：版本号 + 自动备份 + 逐级降级**：`config/HullStrengthConfig.java:102-165`（`_version` 检查、`backupBadFile()` 生成 `.bak.<epoch>`、旧字段 `maxDepthY` 迁移到 `maxWaterDepth`）。适用：所有给玩家手改的 JSON/TOML 配置。
4. **每帧/每 tick 的高频判定结果缓存到"tick + 坐标"键**：`mixin/EntityWaterPhysicsMixin.java:91-110`。一个 `@Unique` 方法被 11 个 hook 共用，内部先比对 5 个 double + tick 再计算，避免重复的坐标系变换。
5. **对可选/不稳定的第三方 mod，用反射做入口、用独立 mixin 文件做崩溃点**：`CreateSubmarine.java:501-553`（`Class.forName` 读 Simulated 的静态 `TAB_ITEMS`/`ITEM_TO_SECTION` 并 try/catch 吞异常）+ `mixin/compat/` 下按 `XxxCrashFixMixin` 命名的 11 个类 + mods.toml 里把特定 Sodium 版本标 `incompatible`。适用：想兼容大量 mod 又不想被单个版本拖崩的场合。

（补充：`CreateSubmarine.java:410-474` 的 `RegisterCapabilitiesEvent` 是"用注册事件给别人的方块实体补能力"的范例——读取 `BuiltInRegistries.BLOCK_ENTITY_TYPE.get(ResourceLocation.fromNamespaceAndPath("simulated", "rope_winch"))` 后若无条件地 `event.registerBlockEntity(Capabilities.EnergyStorage.BLOCK, ropeWinchType, ...)`，对可选 mod 零编译依赖。）

## 8. 公开 API

非库模组（All Rights Reserved，且明确 `incompatible` 声明），无对外开放 API 包。对内暴露的扩展/接入点为：`compartment/CompartmentDetector`（`beginScan/stepScan/finishScan/detect` 静态 API，可被复用做通用闭舱检测）、`util/SubLevelRegistry`、`util/SablePhysicsHelper`、`config/HullStrengthConfig`（含网络同步的 `applySynced/update/save`）。跨 mod 方向它走的是**消费**而非提供：把 `sable-companion` 用 `jarJar(api(...))` 内嵌分发，并 `implementation files("libs/sable-neoforge-1.21.1-1.2.2.jar")` 直接依赖本地 jar。
