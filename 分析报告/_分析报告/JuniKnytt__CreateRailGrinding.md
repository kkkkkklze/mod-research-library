# JuniKnytt/CreateRailGrinding 源码分析

## 1. 基本信息
- Mod 名：Create: Rail Grinding；mod_id `createrailgrinding`；作者 Juni Knytt；mod 版本 1.2.2；MIT 许可
- 目标：MC 1.21.1 + NeoForge（neo_version 21.1.219，loader `[4,)`）；Parchment 2024.11.17；mods.toml 由 `src/main/templates` 经 ProcessResources 展开生成（`build.gradle:96-114`）
- 编译依赖：Create 6.0.11-286、Ponder 1.0.82+mc1.21.1、Flywheel 1.0.6（api 为 compileOnly + 完整版 runtimeOnly）、Registrate MC1.21-1.3.0+67（声明但源码中未检索到使用）；EMF 3.2.4 / ETF 7.1 仅 compileOnly，运行时用 `compat/Mods` 判定
- 仓库含 `ai_disclosure.md`（声明 AI 辅助编码，资产与测试为人工）

## 2. 源码规模与包结构
75 个 `.java`，合计 6845 行。包分布：`rail` 1、`client` 18、`client/particle` 1、`network` 16、`ponder` 7、`advancement` 5、`mixin` 5、`mixin/client` 6、`compat` 2、`compat/emf` 2、`cosmetic` 2、`effect` 2、`event` 2、`sound` 2、`particle` 1、`enchantment` 1、根 2。
最大文件：RailGrindHandler 2003、ClientInputHandler 546、GrindSoundController 222、RailGrindScenes 200、RailGrindClientMotion 184、Networking 174、ModEvents 174、RailGrindDebugHud 170。

## 3. 入口与注册
`src/main/java/net/juniknytt/createrailgrinding/RailGrind.java:74-88`：`@Mod` 构造注入 `IEventBus modBus, ModContainer container`，注册四个 DeferredRegister（ModSounds/ModEffects/ModParticles/ModTriggers）并 `container.registerConfig` 两份配置（CLIENT 的 `Config.SPEC`、SERVER 的 `Config.SERVER_SPEC`）。网络注册在独立类 `network/ModNetworking.java:14-46`（`@EventBusSubscriber(Bus.MOD)` + `RegisterPayloadHandlersEvent` + `PayloadRegistrar registrar = event.registrar("1")`）。

## 4. 核心系统
1. RailGrindHandler（2003 行，核心状态机）：`rail/RailGrindHandler.java:69-78` 用 `ConcurrentHashMap<UUID, GrindState>` 等 6 张表保存逐玩家状态，配 `record PendingRegrind/GrindFrame/GrindDebugInfo/RailHit`（:184、:833、:1228、:1245）避免对象分配。`railgrinding(Player, TrackGraphLocation, ...,SubLevelHandle)`（:391）做冷却/乘客/旁观/轨道材质过滤，按朝向切边、由 `edge.getPosition`+`sampleTangent` 求世界坐标，并按轨道规格（Create 标准轨与 railways 窄轨/宽轨/单轨常量 :117-127）设 `lateralOffset/yOffset`，支持 Sable 子世界坐标变换。
2. 速度与物理：`tick`（:1336）+`computeTargetSpeed`/`computeAcceleration`/`computeFluidMultiplier`/`computeDynamicMaxDrift`（:1497-1570），参数集中在类头常量（SPEED_EASE_RATE 0.08、CURVE_* 系列、WATER_FLUID_FACTOR 0.5 等 :85-140）；`applyTickMotion` 落地位移，`sendTargetToPlayer`（:1687）下发目标点与速度。
3. 客户端预测：`client/RailGrindClientMotion.java:18-140`，`setTargetAndVelocity(..., authoritative)` + CORRECTION_RATE 0.3 平滑逼近，另含 `runBlockedDetection` 前瞻障碍探测；`client/ClientInputHandler.java:58-325` 处理点击/跳跃蓄力/踏板输入并发 `StartGrindFromNearestPayload`、`StopGrindPayload`、`SteerInputPayload` 等。
4. 网络：见 5。
5. 兼容层：`compat/Mods.java:9-49` 用 `LoadingModList.get().getModFileById(id) != null` 判定，并提供 `Supplier<Supplier<T>>` 延迟类加载；`compat/SableSubLevels.java:14-52` 纯反射缓存 `Class.forName("dev.ryanhcode.sable...")` 的方法句柄，实现可选的子世界支持，`SubLevelHandle` 为轻量记录。
6. 表现层：`client/` 下 tilt/lean/roll/camera 系列（RailGrindModelTilt、RailGrindLeanTracker、RailGrindCameraRoll、BalancingPoseTracker）、HUD 覆盖层（GrindSpeedometerOverlay、JumpChargeOverlay、RailGrindDebugHud）、`sound/GrindSoundController.java`（222 行，按速度切换循环音）；`ponder/RailGrindScenes.java`（200 行）+ `RailGrindPonderPlugin` 注册 Ponder 场景。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`network/ModNetworking.java:16-45` 注册 6 个 playToClient payload（Sync/DebugSync/Target/LeanSync/AccelSync/ParticleBurst），全部是 `record implements CustomPacketPayload` + `StreamCodec.composite`（如 `RailGrindSyncPayload.java:13-21`），客户端处理集中在 `ClientPayloadHandler`（86 行）；C2S 侧用 `PacketDistributor.sendToServer(...)`，另有 `Networking.java`（174 行，含 `TeleportToRailPacket`）。
- 配置：`Config.java:9-57`，CLIENT（debugMode、soundVolume、cameraRollOnLean）与 SERVER（topGrindSpeed、crouchGrindSpeed、crouchAcceleration、downwardMomentumGain、railJumpCharge、railJumpMomentum、autoDeployElytra、syncDebugToClients）；取值时用 `SERVER_SPEC.isLoaded()` 兜底（RailGrindHandler:80-84）。
- 数据驱动：全部走数据包 JSON——`data/createrailgrinding/enchantment/railgrind_enchantment.json`（feet 槽、`primary_items: #createrailgrinding:railgrind_enchantable`）、`tags/item/is_diving_boots.json`（create:copper_diving_boots / netherite_diving_boots）、4 个 advancement、recipe 与 3 个 minecraft 附魔 tag；附魔本体不注册，直接用 `ResourceKey<Enchantment>` 查原版注册表（`enchantment/ModEnchantments.java:17-33`）。
- datagen：无。注意：本地镜像工作区 `src/main/resources` 只落盘了 `createrailgrinding.mixins.json`，assets/data 的 31 个文件存在于 git 索引（需 `git show` 或完整 checkout 才能看到贴图/音效/ponder nbt）。
- 进度触发：`advancement/ModTriggers.java:11-29` 注册 4 个 `CriterionTrigger`，由 `event/ModEvents.java:52-65` 周期性 trigger。

## 6. Mixin
`src/main/resources/createrailgrinding.mixins.json`（JAVA_21，required，defaultRequire 1）：
- 通用 5 个：`Player.tryToStartFallFlying` HEAD 取消（`mixin/LivingEntityFallFlyingMixin.java:14`）、`Player.maybeBackOffFromEdge`（`PlayerEdgeMixin.java:14`）、`Player.tick` 在 `INVOKE updateIsUnderwater` 处再置 `noPhysics`（`PlayerNoPhysicsTickMixin.java:16-22`）、`PortalProcessor.processPortalTeleportation` HEAD cancellable（`PortalProcessorInstantMixin.java:16`）、`ServerGamePacketListenerImpl.handleMovePlayer` HEAD（`ServerMovePacketMixin.java:17`）
- 客户端 6 个：`PlayerModel.setupAnim`（`client/PlayerModelMixin.java:36`）、`PlayerRenderer.renderHand`、`Camera.setup(...)` 与 `Camera.tick()`（@Redirect）、`HumanoidArmorLayer.renderArmorPiece`（@Redirect）、`LivingEntityRenderer.setupRotations`

## 7. 值得学的 5 条
1. 把"每玩家长驻状态"集中成一个静态状态机类，用 ConcurrentHashMap + record 组合，零额外分配且天然线程安全：`rail/RailGrindHandler.java:69-226`。
2. 服务端权威 + 客户端插值：服务端只下发 target/velocity（`sendTargetToPlayer` :1687），客户端以固定修正率 0.3 逼近并做前瞻障碍检测（`client/RailGrindClientMotion.java:53-140`），适合高速移动的实体控制。
3. 可选兼容用"枚举 isLoaded + 反射缓存方法句柄"双保险，绝不硬依赖第三方 mod：`compat/Mods.java:16-49`、`compat/SableSubLevels.java:34-52`。
4. 新内容尽量复用原版数据系统：自定义 tag + 自定义 CriterionTrigger + datapack 附魔 JSON，而不是新增注册对象（`CustomBootSkin.java:16-18`、`advancement/ModTriggers.java:11-24`）。
5. mods.toml 用 processResources 展开 `src/main/templates` 占位符生成，避免版本号在多处硬编码：`build.gradle:96-114`。

## 8. 库/API 扩展点
不适用（非库/前置模组）。
