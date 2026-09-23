# ryanhcode/sable 源码分析

## 1. 基本信息

- Mod 名：Sable / mod_id：`sable` / 作者：RyanHCode（credits：Ocelot, Eriksonn, Cyvack, Bee, Kyan, Cake, Rhyguy1）
- 目标：MC `1.21.1`、NeoForge `21.1.228` + Fabric `0.110.0` 双平台、Java 21、Parchment `2024.11.10`
- Gradle：自建多加载器插件 `buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle` + `net.neoforged.moddev`；`settings.gradle` 含 `common`/`fabric`/`neoforge`/`sable_rapier` 四工程，`sable_rapier` 通过 Docker 交叉编译 Rust 原生库（gradle 任务 `buildImages`/`buildRustNatives`，pinned rust `nightly-2026-01-29`）
- 许可证：PolyForm Shield License 1.0.0。定位明确：**intrusive library mod**（README）
- 编译依赖（`gradle.properties`）：`create_version=6.0.10-280`、`flywheel 1.0.6`、`registrate MC1.21-1.3.0+67`、`veil 4.3.2`、`sable_companion_version=1.6.0`（外部库 github.com/ryanhcode/sable-companion，即对外 API）、`forgeconfigapiport`、`imguimc`；兼容性适配：CC:Tweaked、Exposure、Jade、Moonlight、PMWeather、Sodium、Iris、Distant Horizons 等

## 2. 源码规模与包结构

- 780 个 `.java`（不含 build），共 **58320** 行。模块分布：`common` 534 文件、`neoforge` 207、`fabric` 25、`sable_rapier` 14
- 顶层包（`dev/ryanhcode/sable/`）：`api`（62 文件，核心公开面）、`mixin`（common 277 + neoforge 182 + fabric 10 个 mixin 类）、`sublevel`（60）、`network`、`render`、`physics`、`platform`、`mixinterface`（接口注入）、`config`、`command`、`debug`、`index`
- 最大文件：`sable_rapier/.../RapierPhysicsPipeline.java` 729、`Rapier3D.java` 691、`sublevel/plot/ServerLevelPlot.java` 687、`sublevel/storage/holding/SubLevelHoldingChunkMap.java` 657、`sublevel/system/SubLevelPhysicsSystem.java` 631、`sublevel/entity_collision/SubLevelEntityCollision.java` 618、`api/SubLevelAssemblyHelper.java` 593

## 3. 入口与注册

`common/.../Sable.java:38-45` 只有极简 `init()`：TCP 包、标签、物理方块属性类型、力组注册。

```java
public static void init() {
    SableTCPPackets.init();
    SableTags.register();
    PhysicsBlockPropertyTypes.register();
    ForceGroups.register();
}
```

同一文件 `defaultSubLevelContainerInitializer`（60-81）是全局装配点：每个 level 的 `ServerSubLevelContainer` 被装上 `SubLevelPhysicsSystem` + `SubLevelTrackingSystem`，并 `addObserver` 追加 `SubLevelTrackingPointObserver`、`SubLevelTicketLoadingSystem`。

NeoForge 侧 `neoforge/.../SableNeoForge.java:29-49`：注册 COMMON/SERVER 两份 `ModConfigSpec`、`registerReloadListeners`（物理方块属性、维度物理、浮块材质三份数据包加载器）、命令、`OnDatapackSyncEvent` 同步、`DeferredRegister<Attribute>`（拳击强度/冷却）、`CrashReportCallables.registerHeader(Sable::getCrashHeader)`（崩溃头加自嘲注释，`Sable.java:83-114`）。

## 4. 核心系统

1. **Sub-level（可动方块结构）容器**：`api/sublevel/SubLevelContainer.java` 用「plot 网格」实现——`SubLevel[] subLevels` + `BitSet occupancy`，`DEFAULT_ORIGIN = 10000`、`DEFAULT_LOG_SIZE_LENGTH/LOG_PLOT_SIZE = 7`（约 30M 方块外存放 plotyard，2-44 行）；`tick()` 里先 tick 所有 sub-level 再通知 observers（143-148）。服务端 `ServerSubLevel`/`ServerLevelPlot`（687 行）+ 客户端 `ClientSubLevel`。
2. **物理管线抽象**：`api/physics/PhysicsPipeline.java` 是纯接口（`init/prePhysicsTicks/physicsTick(timeStep)/postPhysicsTicks/readPose/add/remove/handleChunkSectionAddition|Removal`）；实现由 `api/physics/PhysicsPipelineProvider.java` 通过 `ServiceLoader` 选 `@LoadPriority` 最高者（默认 Rapier 实现 `sable_rapier/.../RapierPhysicsPipelineProvider.java`）。`SubLevelPhysicsSystem.java:59-129` 持有 pipeline + `PhysicsConfigData` + `PhysicsChunkTicketManager` + `IN_PHYSICS_STEP`/`currentlySteppingSystem` 静态态；`initialize()` 从 `DimensionPhysicsData` 取重力与全局阻力注入管线。
3. **物理对象/约束/受力**：`api/physics/object/`（`BoxPhysicsObject`/`RopePhysicsObject`/`ArbitraryPhysicsObject`）、`api/physics/constraint/`（Fixed/Free/Rotary/Generic 各配 `*Handle`）、`api/physics/force/`（`ForceGroup`/`ForceGroups`/`QueuedForceGroup`/`ForceTotal`）、`api/physics/mass/`（`MassTracker`/`MergedMassTracker`）；方块侧扩展点在 `physics/floating_block/`（`FloatingBlockCluster`/`FloatingBlockController`）与 `physics/ReactionWheelManager.java`。
4. **Voxel 碰撞体烘焙**：`sable_rapier/.../collider/RapierVoxelColliderBakery.java` + `RapierVoxelColliderData` + `PhysicsColliderBlockGetter`，把方块截面转成物理引擎用的体素数据；`api/physics/collider/VoxelColliderData`、`SableCollisionContext` 是对外抽象。
5. **Rust 原生桥**：`Rapier3D.java` 加载 `sable_rapier_binaries.zip.l4z`（LZ4 压缩的按平台解压 DLL/dylib/so），JNI 调 Rapier；本地库解压到临时目录（`resolveNativeDir`）。构建脚本按 triple（mac/linux/windows × x86_64/aarch64）用 Docker 产多平台产物。
6. **渲染/兼容子系统**：`render/`（`region/SimpleCulledRenderRegionBuilder`、`dynamic_biome`、`dynamic_shade`、`sky_light_shadow`、`water_occlusion`）、`sublevel/entity_collision/SubLevelEntityCollision.java`（618 行，实体与 sub-level 碰撞）、`compatibility/SableIrisCompat.java`、`neoforge/.../compatibility/flywheel/SableFlywheelLightStorage.java`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络双通道**：TCP 走自研 `network/tcp/SableTCPPackets.java`（自建 `PACKET_MANAGER.registerClientbound/registerServerbound(TYPE, CODEC, handler)` 模式，15 个包，含 `ClientboundSableSnapshotDualPacket`、`ClientboundSableSnapshotInfoDualPacket`、`ServerboundPunchSubLevelPacket` 等）；另有**可选的 UDP 通道**（`network/udp/`：`SableUDPServer`、`SableUDPPacketEncoder/Decoder`、`SableUDPAuthenticationState`、`AddressedSableUDPPacket` + client/server ChannelHandler），由 `ClientboundSableUDPActivationPacket` 激活，用于高频快照。
- **数据驱动**：datapack 加载器三个（`PhysicsBlockPropertiesDefinitionLoader`、`DimensionPhysicsData.ReloadListener`、`FloatingBlockMaterialDataHandler.ReloadListener`），注册于 `SableNeoForge.java:51-55`；`network/packets/PacketReceiveMode` 控制同步策略。wiki 目录带 4 篇开发文档（`wiki/Home.md`、`Block Physics Properties.md`、`Dimension Physics Data.md`、`Working with Entities.md`）。
- **配置**：`SableConfig`（COMMON）+ `SableServerConfig`（SERVER），`config/SubLevelSettingsScreen.java` 提供 GUI；No datagen provider（未见 `GatherDataEvent`）。

## 6. Mixin

三份配置：`common/src/main/resources/sable.mixins.json`（237 行条目，package `dev.ryanhcode.sable.mixin`，`"plugin": "dev.ryanhcode.sable.plugin.SableMixinPlugin"`）、`fabric/src/main/resources/sable-fabric.mixins.json`、`neoforge/src/main/resources/sable-neoforge.mixins.json`（大量 `compatibility.create.*` 条目，如 `ContraptionVisualMixin`、`BeltRendererMixin`）。`SableMixinPlugin extends AbstractSableMixinPlugin` 在 `preApply/postApply` 做条件过滤。

Mixin 按功能分小包（`mixin/entity/`、`mixin/particle/`、`mixin/camera/`、`mixin/chunk_container_replacement/`、`mixin/clip_overwrite/`、`mixin/plot/`…）。代表：`mixin/particle/ParticleMixin.java`（574 行，最大 mixin）、`mixin/particle/ParticleEngineMixin.java`、`mixin/clip_overwrite/*`、`mixin/entity/entity_sublevel_collision/*`、`mixin/mixinterface/plot/SubLevelContainerHolder`（配合 `mixinterface/` 里 20+ 个接口做接口注入，如 `EntityExtension`、`LevelPoseProviderExtension`）。

## 7. 值得学的 5 条做法

1. 「管线接口 + ServiceLoader + `@LoadPriority`」替换物理引擎实现，不做平台硬绑定（`api/physics/PhysicsPipeline.java`、`PhysicsPipelineProvider.java`）。
2. 用 BitSet + 定长数组管理巨型 plot 网格（`SubLevelContainer.java:130-138`），避免 Map 开销。
3. 用 mixin 包 `mixinterface/` 统一管理接口注入：`SubLevelContainerHolder#sable$getPlotContainer()` 这类带前缀的注入方法，可读且防冲突（`api/sublevel/SubLevelContainer.java:92-119`）。
4. 高频物理快照走独立 UDP 通道 + 认证状态机，TCP 只做低频语义包（`network/udp/SableUDPAuthenticationState.java`、`ClientboundSableUDPActivationPacket`）。
5. 极重的原生加速（Rust/Rapier）用「lz4 压缩的多平台二进制 zip + 运行时解压 + 独立 gradle 子工程」交付，Java 侧只留一层薄 JNI（`sable_rapier/build.gradle`、`Rapier3D.java`）。
6. 兼容层按模组名建包（`mixin/compatibility/create|iris|jade|exposure|...`），并配套 `sable-companion` 外部库让第三方只写轻量适配。

## 8. 库/API 说明（本仓为库/前置型）

- 公开 API 包：`dev.ryanhcode.sable.api.*`（62 文件）——`api/sublevel/`（`SubLevelContainer`/`ServerSubLevelContainer`/`ClientSubLevelContainer`/`SubLevelObserver`/`KinematicContraption`/`SubLevelTrackingPlugin`/`ticket`）、`api/block/`（`BlockSubLevelAssemblyListener`、`BlockSubLevelCollisionShape`、`BlockSubLevelCustomCenterOfMass`、`BlockSubLevelDynamicCollider`、`BlockSubLevelLiftProvider`、`BlockEntitySubLevelActor`、`BlockEntityPropeller`…）、`api/entity/EntitySubLevelUtil`、`api/event/`（`SablePrePhysicsTickEvent`/`SablePostPhysicsTickEvent`/`SableSubLevelContainerReadyEvent`）、`api/math/`（`OrientedBoundingBox3d`、`LevelReusedVectors`）、`api/particle/ParticleSubLevelKickable`、`api/schematic/`、`api/command/SubLevelArgumentType`。
- 扩展方式：实现上述接口（多由 block/block-entity 承载），物理量通过 `api/physics/`（约束/受力/质量/Handle）操作；跨 mod 的轻量兼容改走外部库 **Sable Companion**（`Sable.HELPER = (ActiveSableCompanion) SableCompanion.INSTANCE`，`ActiveSableCompanion.java` 实现 `getAllIntersecting`/`getContaining` 等查询），避免直接依赖 Sable 内部实现。
