# matejhozlar/Create-Aeronautics-Climbable-Ropes 源码分析报告

## 1. 基本信息
- Mod 名：Climbable Ropes for Create Aeronautics；mod_id：`climbable_ropes`；版本 2.1.3；`neoforge.mods.toml` 模板 authors="saunhardy"（仓库 owner 为 matejhozlar）；许可证 **MIT**（`gradle.properties`）。
- 目标：MC 1.21.1 + **NeoForge 21.1.228**（单平台）；Java 21；Parchment 2024.11.17；Gradle 插件 `net.neoforged.gradle.userdev`（`build.gradle`）；`src/main/templates/META-INF/neoforge.mods.toml` 由 `generateModMetadata`（ProcessResources，property 展开）生成，`[[mixins]] config="${mod_id}.mixins.json"`。
- 依赖（谁提供 API）：**Simulated**（Create: Aeronautics 内置物理模块）`simulated_version_range=[1.3.0,1.4.0)`，**Sable** `[2.0.0,3.0.0)`，Create `6.0.10`，`playeranimator 2.0.4`（**jarJar 打进产物**，NeoForge 按版本去重）、`foundry.veil:veil-neoforge 4.0.1`（网络层）、Flywheel 1.0.6、Ponder 1.0.81、可选 EMF 3.2.4 / ETF 7.1（仅在 toml 里声明，代码里用 `EmfCompat` 反射/隔离）。
- 构建技巧：`extractSimulated` 任务把 Modrinth 下载的 `create-aeronautics` bundle 内 `META-INF/jarjar/*simulated*.jar` 解出为 `build/extracted-simulated/simulated.jar` 当 compileOnly，并在 `doLast` 里校验存在，否则抛 `GradleException("No Simulated jar-in-jar found ...")`（`build.gradle:89-113`）。

## 2. 源码规模与包结构
- 23 个 `.java`，1953 行，**全部为客户端/配置/网络，无方块或物品注册**。包：`client/ride` 10、`client` 6、`network` 3、`mixin` 2、根 2（`ClimbableRopes`、`ClimbableRopesConfig`）。
- 最大文件：`client/ride/StrandClimbController.java` 288、`client/ClimbAnimationController.java` 209、`client/ride/PlungerZiplineController.java` 156、`client/RemoteClimbAnimations.java` 148、`client/ride/PlungerClimbController.java` 136、`ClimbableRopesConfig.java` 118。
- 资源仅 `src/main/resources/climbable_ropes.mixins.json`（assets/lang/动画 json 未包含在仓库）。

## 3. 入口与注册
`ClimbableRopes.java` 极小：`container.registerConfig(ModConfig.Type.SERVER, ClimbableRopesConfig.SERVER_SPEC)` + `ClimbableRopesNetwork.init()`（构造函数注入 `IEventBus, ModContainer`）。无 DeferredRegister、无物品/方块/实体注册 —— 玩法全靠客户端控制器 + 复用 Simulated 的实体与包。客户端侧由 `client/ClimbableRopesClient.java:21` 单独 `registerConfig(ModConfig.Type.CLIENT, ClimbableRopesConfig.CLIENT_SPEC)`（与 SERVER_SPEC 分文件注册，保证 dedicated server 不加载客户端配置）。

## 4. 核心系统
1. **模式分发器**：`client/ride/RopeRideDispatcher.java`（`@EventBusSubscriber(modid, Dist.CLIENT)`）。`ClientTickEvent.Post`（`EventPriority.LOWEST`）里用 `keyUse` 边沿检测（`justPressed = useDown && !prevUseDown`）分流三种模式；`MovementInputUpdateEvent` 里把 `forwardImpulse/leftImpulse/up/down/left/right` 全部清零，防止原版走路输入让玩家"走出绳子"（注释明说 zip 模式例外，它故意骑原版 WASD）。
2. **共享瞄准几何**：`client/ride/HoverRay.java` —— 一个 record 式"摄像机射线 vs 线段的最近距离"求解（`(dotLD*rSeg - rLook)/denom`），返回 `lateralSqr` 与 `depthSqr`，并用 `Sable.HELPER.projectOutOfSubLevel(...)` 把准星命中点投影出子世界，使"准星后面的绳子"不会被选中，`maxRange = BLOCK_INTERACTION_RANGE + 1`。
3. **三种载具控制器**：`StrandClimbController`（悬挂绳股：`ClientRopeStrand`/`ClientRopePoint` 逐段找最近点 `findClosestSegment`，`totalArcLength` 做弧长上下限，`END_OVERSHOOT_LIMIT`）、`PlungerClimbController`、`PlungerZiplineController`（镜像 Simulated 的 `ZiplineClientManager.ridingTick`：阻尼 `v*0.6` 减去沿绳分量、助力 `dir * v.dot(dir) * 0.04`、弹簧拉向线段最近点）。`PlungerRope.java` 遍历 `mc.level.entitiesForRendering()` 找成对 `LaunchedPlungerEntity` 并用 `Sable.HELPER.getContainingClient(...)` 处理挂在子世界上的绳端。
4. **共享攀爬物理**：`client/ride/ClimbPhysics.java` —— `anchorHeight`/`anchor` 定义玩家锚点，`snapToRope` 先试带侧偏 0.3 的位置再退回正位，两次都用 `mc.level.noCollision(player, aabb)` 校验后 `setPos`；`applyClimbVelocity` 把 `carry + climbVel + snap` 合成 `setDeltaMovement` 并 `player.fallDistance = 0`，弹簧加速度上限 `SNAP_VELOCITY_CAP`。
5. **随船运动补偿**：`client/ride/RopeMotion.java` —— `carry()` 先丢弃 >3.0 格/tick 的跳变（resync），再减去 Sable 已经通过 `LivingEntityMovementExtension.sable$getInheritedVelocity()` 施加给玩家的速度，避免"弹簧追绳子"双重位移。
6. **动画与姿态**：`client/ClimbAnimationController.java`（KosmX playerAnimator `ModifierLayer`，`LAYER_PRIORITY=40`、`FADE_TICKS=4`、`SYNC_REFRESH_INTERVAL=10`，按 `ClimbState{IDLE,CLIMB_UP,DESCEND,SLIDE}` 与切线选动画）+ `client/RemoteClimbAnimations.java`（`STALE_TICKS=30` 超时清理）+ `mixin/PlayerSkyhookRendererMixin` 取消 Create 的 skyhook 姿态；`client/compat/EmfCompat.java` 在爬绳时暂停 EMF 自定义玩家动画。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**不用 NeoForge payload 注册**，而用 Veil 的 `foundry.veil.api.network.VeilPacketManager.create(MODID, "1")`（`network/ClimbableRopesNetwork.java`），`registerServerbound(ClimbAnimUpdatePacket)` + `registerClientbound(ClimbAnimSyncPacket)`；包为 record + `StreamCodec.of(...)` 手写编解码。服务端中继前做**输入消毒**：仅当 `packet.animation()` 命名空间等于本 mod，且 tangent 三分量 `Double.isFinite` 才用 `VeilPacketManager.tracking(sender).sendPacket(...)` 广播（注释指出 Infinity tangent 会破坏其他客户端的姿态旋转）。
- 配置：`ClimbableRopesConfig` 用 `ModConfigSpec` 分四组 —— climbing/features/advanced（SERVER_SPEC）与 animation（CLIENT_SPEC）；`advanced` 组把 `snapPull/snapVelocityCap/maxLeashDistance/bottomDismountOffset/bottomGroundedDismountTicks/ropeHoverRadius` 全部暴露，默认值即调优值。
- datagen：无。数据驱动：无（玩法参数走 config，绳索数据来自 Simulated）。

## 6. Mixin
- 配置：`src/main/resources/climbable_ropes.mixins.json`，`required: true`，`compatibilityLevel: JAVA_21`，`injectors.defaultRequire: 1`，仅 `client` 两个类。
- `mixin/PlayerSkyhookRendererMixin.java`：`@Mixin(PlayerSkyhookRenderer.class)`，`@Inject(method="beforeSetupAnim", at=@At("HEAD"), cancellable=true, remap=false)`（把 head/hat/body/双臂/双腿 `resetPose()` 后 `ci.cancel()`）与 `@Inject(method="afterSetupAnim", HEAD, cancellable=true, remap=false)`（自定义姿态激活时取消）。
- `mixin/PlayerSkyhookRendererAccessor.java`：接口式 `@Accessor(value="hangingPlayers", remap=false) static Set<UUID> getHangingPlayers()`，读取 Create 的悬挂玩家集合。

## 7. 值得学的 5 条具体做法
1. **射线-线段最近距离做"悬停抓取"**：`client/ride/HoverRay.java` 用 `dotLD/denom` 闭式解算 + `blockDistSqr` 遮挡比较，所有三种模式共用同一判定 —— 适用：绳索/电线/铁链类交互瞄准。
2. **输入清零而非取消事件**：攀爬时在 `MovementInputUpdateEvent` 里把 Input 各分量置零（`RopeRideDispatcher.onMovementInput`）—— 适用：想让玩家脱离原版移动但保留其它输入语义。
3. **随动补偿要减去"已继承速度"**：`RopeMotion.carry()` 从绳速里扣掉 Sable 已给玩家的位移，并丢弃 >3 格/tick 的 resync —— 适用：任何"附着在运动平台/子世界上的实体"随动。
4. **服务端中继客户端动画前做字段消毒**：仅放行本 mod namespace + 有限浮点（`network/ClimbableRopesNetwork.handleUpdate`）—— 适用：所有 C2S→S2C 转发型视觉同步。
5. **构建期从 JiJ 里抽前置 jar 并断言**：`build.gradle:89-113` 的 `extractSimulated` + 缺失即 `GradleException` —— 适用：上游只以 jar-in-jar 分发、没有 maven 的 API（Simulated 是典型）。

## 8. 库/API 类 mod 的公开 API
不适用（非库 mod）。其对外契约体现在 `neoforge.mods.toml` 的依赖区间与 `reason` 字段：明确写出"依赖 Simulated 的 `ZiplineClientManager`/`RopeRidingPacket` 内部 API，跨小版本可能变，故把范围钉死在 `[1.3.0,1.4.0)`"——这是附属 mod 应对上游内部 API 漂移的可复制做法。
