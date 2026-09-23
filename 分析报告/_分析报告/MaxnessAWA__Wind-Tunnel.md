# MaxnessAWA / Wind-Tunnel 源码分析

## 1. 基本信息
- Mod 名：Wind Tunnel；mod_id `windtunnel`；作者 MaxnessAWA；许可证 **MIT**；`io.github.windtunnel`
- 目标：MC **1.21.1** + **NeoForge 21.1.219**（loader range `[4,)`），Java **21**（`gradle.properties`）
- Gradle：**NeoForge ModDev 插件 `net.neoforged.moddev` 2.0.140**（非 ForgeGradle/Architectury），parchment `2024.11.10`
- 依赖（`build.gradle`）：`compileOnly` Create `6.0.10-280`、Sable `1.0.6`、Sable Companion `1.5.0`、Ponder `1.0.82`、Veil `3.6.2`、Simulated `1.0.3`；`implementation` **LDLib2 `2.2.6`** 与 `yoga 1.0.0`。`neoforge.mods.toml` 声明 Create/Sable/Simulated/Create Aeronautics/LDLib2 为必装
- runs：client/server/data；data run 带 `--existing-mod create`、`--existing-mod aeronautics`，输出到 `src/generated/resources`（已加入 `sourceSets.main.resources`）

## 2. 源码规模与包结构
实测 **96 个 .java / 17309 行**。
- `io.github.windtunnel.content`（**54**）：方块/方块实体/菜单/渲染器/服务全在此层
- `.network`（11）、`.item`（7）、`.registry`（5）、`.data`（4）、根包（4）、`.mixin`（3）、`.compat`（3）、`.client`（3）、`.config`（1）、`.mixin.compat.synaxis`（1）
- 最大文件：`content/WindTunnelMountService.java` 1308 > `content/WindTunnelLdlib2DiagramElement.java` 1269 > `content/WindTunnelMountBlockEntity.java` 758 > `content/HologramProjectorRenderer.java` 656 > `content/WindTunnelControllerScreen.java` 583 > `content/WindTunnelWindProvider.java` 514

## 3. 入口与注册
`WindTunnelMod.java:52-113`（`@Mod`，构造器注入 `IEventBus modBus, ModContainer modContainer`）按四阶段集中初始化：
1. `WindTunnelBlocks.BLOCKS / WindTunnelItems.ITEMS / WindTunnelBlockEntities.BLOCK_ENTITY_TYPES / WindTunnelCreativeTabs.CREATIVE_MODE_TABS / WindTunnelMenus.MENUS` 各自 `DeferredRegister.createBlocks/create(Registries.X, MOD_ID)` 并 `.register(bus)`；注册类集中在 `registry/` 包（如 `WindTunnelBlocks.java:31` 起，含按 `DyeColor` 循环注册的 16 色 airfoil 用 `EnumMap` + `Collections.unmodifiableMap`）。
2. `modBus.addListener(NetworkHooks::registerPayloads)` + `WindTunnelDataGenerators::gatherData`。
3. 客户端注册全部包在 `if (FMLEnvironment.dist.isClient())` 里（屏幕/渲染器/额外模型/着色器 + `NeoForge.EVENT_BUS` 渲染与登出监听）。
4. Sable 物理集成用 `windProviderRegistered` / `mountHooksRegistered` 静态布尔防重复注册，随后 `modContainer.registerConfig(ModConfig.Type.SERVER, WindTunnelConfig.SPEC)`。

## 4. 核心系统
1. **风洞集群网络**（`content/WindTunnelNetwork.java`）：对 controller/tunnel 面相邻方块做泛洪填充（`ArrayDeque` frontier + `visited`），合并规则"任一 controller 使能则整簇激活、长度/风速取 max、风向取或"；仅在放置/移除/红石/GUI 改动时重扫，不每 tick 轮询；状态变化经 `applyTunnelState` 写回并 `level.setBlock(..., Block.UPDATE_CLIENTS)`；`PacketDistributor.sendToPlayersTrackingChunk` 只同步 chunk 追踪者。
2. **Sable 风场桥接**（`content/WindTunnelWindProvider.java`）：`Map<ResourceKey<Level>, DimensionTracking> ACTIVE_TUNNELS = new ConcurrentHashMap<>()` 按维度索引活跃风洞，写入时原子重建不可变 `DimensionSnapshot` 让热路径无锁查询；`ThreadLocal<QueryScratch> QUERY_SCRATCH` 复用查询状态避免分配（类头注释明确说明这套"总览"）。
3. **测量台服务**（`content/WindTunnelMountService.java`，1308 行）：挂 `SableEventPlatform.INSTANCE.onPhysicsTick/onPostPhysicsTick` 前后窗口，前锁姿态、后读累积升力/阻力/力矩。
4. **LDLib2 + Yoga 界面**：`content/WindTunnelLdlib2*.java`（DiagramElement 1269 行、控制器/注入器屏幕、`WindTunnelResizableUi` 534 行）用 LDLib2 组件 + Yoga 弹性布局手搓可缩放力矢量图。
5. **可选兼容 Synaxis**：`compat/SynaxisWindCompat.java` 以 `ClassValue<Optional<Method>>` 缓存反射得到的对方方法（`flapCenterLocal`/`modelToWorldPosition`/`positionWorld` 等），完全不编译依赖 Synaxis。
6. **着色器/全息投影**：`client/HologramProjectorWorldRenderer`、`content/HologramProjectorRenderer` + `HologramProjectorService`（每物理 tick 采样点力生成世界空间箭头）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- **网络**：NeoForge 现代 `CustomPacketPayload` + `StreamCodec` record 风格。`NetworkHooks.registerPayloads(RegisterPayloadHandlersEvent)` 用 `event.registrar("1")` 一次性注册 10 个 payload：5 个 `playToServer`（`UpdateWindTunnelController/Mount/AirflowInjector`、`Request*Diagram`）+ 5 个 `playToClient`（`Sync*`），全部自带 `TYPE`/`STREAM_CODEC`（如 `network/SyncGogglesForceVectorsPayload.java`），`handle` 内 `context.enqueueWork(...)`；公共序列化（`Vec3Payload`、`ForcePointPayload`）抽到 `network/DiagramPayloadHelper.java`。
- **配置**：`config/WindTunnelConfig.java` 用 `ModConfigSpec` 服务端配置，逐项 `comment(...).defineInRange("maxRange", 256, 1, 256)`，外部只暴露静态 getter（`maxRange()` 等）。
- **datagen**：`data/WindTunnelDataGenerators.gatherData(GatherDataEvent)` 先判 `event.getMods().contains(MOD_ID)`，client 走 `WindTunnelAirfoilAssetProvider`（用 Gson 手写 blockstate/block model/item model），server 走 `WindTunnelAirfoilDataProvider`（`loot_table/blocks`、**`physics_block_properties`**、`recipe`）；两者按 `WindTunnelAirfoilData.COLORS × AirfoilKind` 生成 32 套，全部 `PackOutput.PathProvider` + `CompletableFuture.allOf` 并行落盘。

## 6. Mixin
两份配置：
- `src/main/resources/windtunnel.mixins.json`（`required:true`，JAVA_21）：`ServerSubLevelAirfoilMixin`（`@Mixin(ServerSubLevel.class)`，`@Inject(method="prePhysicsTick", at=HEAD/RETURN)` + `@Redirect`）、`BlockSubLevelLiftProviderMixin`（`@Mixin(BlockSubLevelLiftProvider.class)`，`@Inject` 锚点 `INVOKE .../Pose3d;transformNormalInverse`，另有 3 处 `@ModifyVariable(method="sable$contributeLiftAndDrag")`）。
- `src/main/resources/windtunnel-synaxis.mixins.json`（**`required:false`**，`injectors.defaultRequire=0`，`plugin: WindTunnelCompatMixinPlugin`）：`SynaxisFlapControlMixin` 用 `@Mixin(targets="com.verr1.synaxis...FlapControl", remap=false)` + `@Redirect(method="tick(Lcom/verr1/synaxis/foundation/physics/PhysicsStepContext;)V")`。
- `mixin/WindTunnelCompatMixinPlugin.java` 实现 `IMixinConfigPlugin`，`shouldApplyMixin` 里按包名判断：`io.github.windtunnel.mixin.compat.synaxis.` 前缀的 mixin 仅当 synaxis 已加载才应用；检测用反射 `LoadingModList.getModFileById` / `ModList.isLoaded`（兼容加载早期阶段）。

## 7. 值得学的 5 条做法
1. **主类分阶段初始化 + 客户端守卫**：内容注册→网络/datagen→`FMLEnvironment.dist.isClient()` 包裹的客户端监听→物理/事件钩子→配置；每个可选钩子配布尔守卫（`WindTunnelMod.java:39-40, 62-95`）。
2. **可选 mod 兼容的三件套**：`required:false` 的独立 mixin json + `IMixinConfigPlugin.shouldApplyMixin` 按包名开关 + 反射 `ClassValue<Optional<Method>>` 缓存对方方法（`mixin/WindTunnelCompatMixinPlugin.java`、`compat/SynaxisWindCompat.java`）——零编译期依赖做兼容。
3. **热路径无锁设计**：`ConcurrentHashMap` 按维度索引 + 不可变快照 `DimensionSnapshot` + `ThreadLocal<QueryScratch>`（`content/WindTunnelWindProvider.java:47-53`），适合任何每 tick 被外部 mod 高频查询的 API。
4. **集群逻辑用泛洪填充 + 变更驱动重扫**，并用 max/OR 明确合并语义，避免多控制器冲突（`content/WindTunnelNetwork.java`）。
5. **datagen 覆盖非原版命名空间的数据包**：除常规 loot/recipe/model 外还生成 Sable 的 `physics_block_properties` JSON（`data/WindTunnelAirfoilDataProvider.java:16-18`），说明"第三方数据驱动格式也能纳入 datagen"。

## 8. 公开 API
无对外 API 包（内容型附属 mod）；对 Sable 只做**消费方**集成（`SubLevelHelper.registerWindProvider`、`SableEventPlatform.INSTANCE.onPhysicsTick`）。
