# DBE（dbe / dbe_npc，NeoForge 1.21.1）反编译分析报告

> 分析对象：`~/Downloads\DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar`（38.9 MB / 7766 条目 / **7149 个 class**）
> 反编译产物：`Mod源码研究汇总\源码库\_参考仓库\DBE-1.1.0-neoforge-1.21.1\`（3656 个 .java；其中 `cn/dbe` 本体 3304 个文件 / 879,544 行，其余为内嵌第三方库）
> 方法：CFR 0.152 全量反编译（Kotlin 项目 → Java，含 Intrinsics/Companion 噪声）+ 6 个子系统分头精读（本文第 4 章）
> 作者：曦月(SolarMoon)、甜粽子(Sweetzonzi)；许可证 MIT；credits 注明 Molang 部分来自 TartaricAcid & TomatoPuddin

## TL;DR

**DBE 不是普通 mod，而是"给 Minecraft 装一套游戏引擎"**：一个 jar 里塞进了两个 mod —— `dbe`（引擎）与 `dbe_npc`（NPC 模块，依赖引擎 + **LDLib2**），实现了一整套通常出现在商业引擎里的系统：

| 系统 | 规模（jar class） | 一句话 |
|---|---|---|
| **动画图 animation_graph** | 1448 | 节点图式动画状态机（双 pass 求值 + 分层并行 + 环检测 + RigPass 预算） |
| **UI 编辑器** | 1012 | 游戏内动画编辑器/蓝图编辑器/状态树编辑器（建在 LDLib2 上，15 个 `.lss` 样式表） |
| **NPC 模块** | 839 | 数据驱动 NPC + AI + 313 个网络类 + 编辑器工具链 |
| **工具链 tools** | 765 | 蓝图（可视化脚本）、存储（draft-commit 事务）、调试 |
| **动画核心 animation** | 629 | 自研基岩格式动画加载器 + 播放器 + **IK** + 根运动 + 相机动画 + 第一人称 |
| **action** | 498 | 动作运行时（受击反应表、动作路由、通知） |
| **effect** | 396 | 数据驱动粒子 + 拖尾（Iris 兼容）+ 自定义 shader + 音效钩子 |
| **GAS** | 252 | 类 UE 的 GameplayAbilitySystem：ability/effect/tag/target/**hitbox**/tasks |
| **state_tree** | 202 | 状态树（authoring + runtime） |
| **物理 physics** | 183 | **jMonkeyEngine Bullet 刚体物理**（独立物理线程 60Hz、每 tick 3 子步、只读查询快照） |

对外依赖极少（NeoForge + KotlinForForge +（NPC 模块）LDLib2），其余全靠 jarJar 内嵌 17 个库（jackson、kotlinx、byte-buddy、freemarker、**LuaJava**、**SCXML2**）与 natives（bulletjme / lua51）。

---

## 1. 基本信息

| 项 | 值 |
|---|---|
| mod id | **`dbe`**（显示名 DBE）+ **`dbe_npc`**（DBE NPC，同一 jar 内两个 mod） |
| 版本 | jar 文件名 `1.1.0-SNAPSHOT`；内嵌 `neoforge.mods.toml` 写 `1.0.1009-SNAPSHOT`（**两处不一致，注意**） |
| 加载器 | **Kotlin（`modLoader="kotlinforforge"`，loaderVersion `[5.10,)`）** → 必须装 KotlinForForge |
| 依赖 | required：neoforge `[21.1.0,)`、minecraft `[1.21,1.22)`、kotlinforforge `[5.10.0,)`；`dbe_npc` 额外 required **`ldlib2 [2.2.36.a,)`（side=CLIENT）**；`dbe` 可选 `mgmc [0.7.0,)` |
| 许可证 | MIT |
| 内嵌库（jarJar，17 个） | jackson-annotations/core/databind、yumi-mc-foundation、byte-buddy(+agent)、freemarker、kotlin-reflect/stdlib(-jdk7/-jdk8)、kotlinx-coroutines-core/jdk8、kotlinx-serialization-core/json(-jvm/protobuf)、**org.keplerproject:java（LuaJava）**、**org.apache.commons.scxml2** |
| natives | `natives/bullet/{bulletjme.dll,libbulletjme.so,libbulletjme.dylib}`、`natives/lua/{lua51.dll,luajava4Luajit.dll}` |
| Mixin | **8 个配置共 63 条**（animation 13 / model 18 / npc 24 / physics 2 / sound 2 / effect 2 / pack 1 / entity 1） |
| AccessTransformer | `META-INF/accesstransformer.cfg`，约 19 条（`Camera.detached`、`KeyboardInput.calculateImpulse`、`GameRenderer.getFov`、`LookControl.lookAtCooldown`、`ClientLevel.tickingEntities`、`Entity.firstTick`、`LivingEntity.jumping`、`BlockEntity$ComponentHelper` 等） |
| 资源 | 语言 **4723(en) / 4759(zh)** 条；15 个 `.lss`（LDLib2 样式表：animation_editor / input_editor / state_tree_editor / spark_* / combat_reaction …）；自定义 shader `distort`、`particle_glow_{blur,copy,fullscreen}`；模型（npc_creator / player_editor / iron_warhammer / model_switch …） |

## 2. 规模与包结构

- jar：**7149 个 class**；反编译 **3656 个 .java**（Kotlin 的 `$Companion`/`$WhenMappings`/lambda 合成类被 CFR 并入外层文件，故 java 数≈class 数一半）。
- `cn/dbe` 本体：**3304 个 .java / 879,544 行**；含第三方（jme3/bullet、vhacd、lua、jackson 等）共 3656 个文件 / 935,843 行。

| 一级包 | jar class | 反编译 java | 职责（要点） |
|---|---|---|---|
| animation_graph | 1448 | 800 | 节点图动画状态机（nodes/runtime/execution/integration/authoring/debug） |
| ui | 1012 | 412 | 游戏内编辑器界面（animation_editor、blueprint…，基于 LDLib2） |
| npc | 839 | 410 | dbe_npc：NPC 实体/AI/网络/编辑器/存储 |
| tools | 765 | 357 | blueprint（可视化脚本）、storage、debug |
| animation | 629 | 319 | 基岩动画加载/播放/IK/根运动/相机/第一人称 + animatable mixin |
| action | 498 | 261 | 动作运行时、受击反应、动作路由、通知 |
| effect | 396 | 211 | 粒子/音效/拖尾/着色器 |
| gas | 252 | 149 | GameplayAbilitySystem（ability/effect/target/hitbox/tasks/presets/tag/sync） |
| state_tree | 202 | 87 | 状态树 authoring + runtime |
| physics | 183 | 98 | Bullet 物理集成（level 桥、地形、查询、诊断） |
| model | 104 | 62 | 模型/骨骼渲染 |
| pack / tags / input_mapping / sheet / registry / entity / sync / item / event / api / network | 合计约 250 | 约 120 | 资源包、自定义 tag、输入映射三层、sheet、注册 DSL、同步框架、事件 |

## 3. 启动与模块布局（重要设计事实）

- `cn/dbe/DbeCore.java` 极简：只声明 `MOD_ID`、`LOGGER`，构造器不注册任何东西。
- **真正的组合根在 `cn/dbe/npc/DbeNpc.java`**（`dbe_npc` 的 `@Mod` 类）：其 import 段横跨 action、animation.camera、animation.registry、animation_graph.debug、effect（DbeEffects/DbeShaders/DbeParticleProviderRegister/AnimationNotifyParticleBridge）、event（DbeClientEventRegistrar/DbeCommonEventRegistrar）、gas.client.hitbox（HitboxWindowClientMirror）、input_mapping… 并在 `DbeNpc.java:109` 调用 **`DbeCodeRegistry.register(modEventBus)`** 统一注册。
- 注册侧是一套自研 **注册 DSL**（`cn/dbe/registry/`）：`RegistryBuilder` / `CommonRegistryBuilder` / `ItemBuilder` / `SoundEventBuilder` / `AttachmentBuilder` / `DbeRegistries` / `DbeCodeRegistry` / `RegistryObjectStore`。
- Mixin 按子系统拆 8 个配置（含两个 `IMixinConfigPlugin`：`cn/dbe/npc/mixin/DbeNpcMixinConfig` 用于按依赖门控），63 条注入主要落在：**动画（Player/LivingEntity/LookControl/BlankNpc 的 animatable 化）**、**第一人称渲染（5 条）**、**NPC 战斗相机（目标锁定/描边抑制/输入法遮挡）**、**物理（Level/ServerLevel）**、**音效（SoundEngine/SoundManager）**、**Iris 兼容（2 条）**。
- 架构风格：**引擎/内容分层**（`dbe` 引擎 + `dbe_npc` 内容与组合根）+ **子系统自治**（每个子系统自带 registry/network/runtime/client 子包）+ **编辑期/运行期分层**（authoring vs runtime，动画图/状态树/蓝图三套都是这个模式）。

## 4. 子系统详解（6 个子系统精读）


### 4.A 动画核心（animation + model）

# A. 动画核心（cn/dbe/animation 319 + cn/dbe/model 62）

## 1. 包结构与职责
- `animation/ik/` 105 个（virtual 28、foot_planning 50、solver/space/apply/runtime/target/debug 23）——反向动力学
- `animation/root_motion/` 52（warp 19、source 11、policy 10、runtime 8、sampling 2、collision 1）——根运动
- `animation/playback/` 52（notify 26、controller 14、sync 7、data 3、apply 2）——播放、通知、同步组
- `animation/camera/` 42（client 20、camera 10、shake 6、event 4、integration 2）
- `animation/rotation/` 18：转向系统（`RotationTurnSystem`/`RotationController`/`RotationTurnInPlaceController`/`RotationGaitCurve`）
- 其余：`mixin/` 14、`asset/` 10（AnimationClip/Bone/Keyframe/Loop…）、`vanilla/` 7（`VanillaBoneUpdateHandler` 头部与腿部跟随原版）、`sampling/` 3、`mesh_compensation/` 3、`registry|event|debug|config` 各 2
- `model/`：`mixin/` 18、`renderer/` 11、`equipment/` 9、`origin/` 8（ModelOrigin/Bone/Cube/Polygon/VertexSet/Vertex/Uv/Locator）、`vanilla/` 3、`pose/` 2、`registry/` 2、`sync|preview|event` 各 1，根目录 6（ModelIndex/ModelInstance/ModelController/ModelDefaultHumanoid/ModelCustomItem）

## 2. 基岩动画加载器（自研，非 GeckoLib）
不走 GeckoLib 的 `GeoModel`+`ResourceManager`，而是"包模块"（pack module）式：
- 模型：`pack/modules/PackModelModule.java:72` `read()` 解析 `minecraft:geometry[0].bones`，用 `ModelOriginBone.Companion.MAP_CODEC`（`model/origin/ModelOriginBone.java:45`）反序列化，坐标 ÷16 并翻转轴 `(-1,1,1)`（PackModelModule.java:129-136），最后写入 `ModelOrigin.ORIGINS`（:179）。模型 id 是 `(type, ResourceLocation)`（`model/ModelIndex.java:47`）。
- 动画：`pack/modules/PackAnimationModule.java:109` `read()`；文件名必须匹配 `AnimationAssetNaming.FILE_SUFFIX=".animation.json"`（`animation/asset/AnimationAssetNaming.java:18,23`），内容由 `AnimationClipSet.CODEC` 解码（PackAnimationModule.java:198）。`.animation.json.meta` 走 sidecar 元数据合并（:118、:300、:353）；`.bbmodel` 交给 `PackCameraTrackModule` 解析成相机轨道并合成空 clip（:402）。
- "烘焙"：关键帧不做预烘表，运行时按需插值（`animation/sampling/AnimationKeyframeSampler.java:42`，区间查找 :67-83，`interpolate`:95，LINEAR/CATMULLROM 见 `AnimationInterpolationType.java:38,44`）；唯一预烘的是图曲线 `DistanceCurveProvider/NextStepTimeCurveProvider.preBakeAll`（PackAnimationModule.java:734-736），且在 `animation_graph` 包内。
- 注册表：`AnimationClipSet.ORIGINS`（`animation/asset/AnimationClipSet.java:37`，ConcurrentHashMap）与 `ModelOrigin.ORIGINS`（`model/origin/ModelOrigin.java:45`）均为全局静态，reload 时 `onStart` 直接 clear（PackAnimationModule.java:97）。

## 3. 播放与状态
- 中枢接口 `AnimationAnimatable<T>`（`animation/AnimationAnimatable.java:25`）：`getAnimController()`、`getModelController()`、`getIkManager()`、`getWorldPositionMatrix()`、`applyRootMotion()`；`AnimationEntityAnimatable` 为实体特化（:52）。
- 挂到原版实体靠 mixin 直接 `implements`：`mixin/animatable/PlayerMixin.java:35`、`ZombieMixin.java:27`、`VindicatorMixin.java:25`、`BlankNpcMixin.java:27`，并在字段里 new 出 controller/modelController（PlayerMixin.java:37-38）。头部朝向有 `mixin/vanilla/LookControlMixin.java:36,44` 与 `LivingEntityMixin.java:35(tickHeadTurn),70(tick)`；`DbeAnimationMixinConfig.java:17` 按 `dbe_npc-common.toml` 决定 vanilla mob 的 mixin 是否注入。
- `AnimationPlaybackController`（9049 行）是总控：`tick()`:5056、root motion 缓冲/消费、IK 快照、sync group、notify 队列、mesh compensation、传送检测，字段近 200 个。时间与权重在 `AnimationPlaybackInstance`：状态机 `IDLE/ENTER/WORK/EXIT`，过渡用 `transitionTick/inTransitionTick` 线性淡出（`AnimationPlaybackInstance.java:668 stepWeight()`），`step()`:651 推进时间、`getProgress()`:640 供采样。混合仅 `OVERRIDE/ADDITIVE`（`AnimationPlaybackBlendMode.java:27-28`），播放模式仅 `PARALLEL_GRAPH`（`AnimationPlaybackMode.java:13`）——旧手写混合已被"交给图"取代。多动画对齐由 `AnimationSyncGroupLogic.alignGroup`:56 按 marker/长度推 leader 与各 follower 时间。
- 驱动器 `AnimationPlaybackApplier`：`entityTickPre`:106 消费根运动并改写 `setDeltaMovement`；`entityTick`:515 调 `controller.tick()`；`itemTick`:544；`onBoneUpdate`:558。

## 4. IK
目标：脚踩地、手扶物、多足步态。
- 求解器：自研 `ik/solver/IkCcdSolver.java:28`（CCD + 相邻关节限位 :125）；第三方 Caliko FABRIK（`ik/runtime/IkComponent.java:19` 持有 `FabrikChain3D`，`IkCalikoStructureBuilder.buildChainFromPath`:89 从 pose 或 bind pose 建链）；解析式 `ik/virtual/VirtualIkTwoBoneSolver.java:24` + `VirtualIkRigProfile/PoleResolver`。
- 空间：`ik/space/IkSpaceSolver.java` 做 local↔world：`computeGlobalTransform`:63、`solveLocalTransform`:126、`buildTargetMatrixFromPositionAndDirection`:198，需按父链重建矩阵。
- 回写：`ik/apply/IkApplier.java:55/111/144` 把解出的 pivot 差量写回 `PoseData`；`ik/target/IkFootTargetResolver.resolve`:47 决定脚目标来源。
- 预测足部规划 `ik/foot_planning/`：`PredictIkPlanner`、`PredictIkBipedGaitPolicy`/`QuadrupedTrot|Walk`/`HexapodRippleGaitPolicy`、`PredictIkSupportPolygonStabilityEvaluator`，结果经 `root_motion/source/PredictIkPathTakeoverSource` 接管位移。

## 5. 根运动
`RootMotionConfig.java:42-48` 约定 root/motion_root/rotation_root/rootMotion 四个根骨。采样 `RootMotionDeltaCalculator.computeDelta`:26（邻帧差 + loop seam 处理）；转换 `RootMotionAccumulator.transform/step`（:40,103）按 axisMask/blendWeight/rotationScale/bodyYaw 旋到世界并抽 yaw；落地在 `entityTickPre`，与 vanilla 速度按 `vanillaMovementRetention` 混合后写 `setDeltaMovement`；`RootMotionSweepSolver`:77/:141 自扫掠裁剪首碰，替代 vanilla 位移解算。网络权威：`RootMotionPlayerPacketAuthority.controlledAxes/preserveControlledAxes`:14,23 + `RootMotionLocomotionOwnershipPolicy.java:19`（planar/yaw/vertical 三 owner）定义"这一轴归谁写"；`warp/KRootMotionModifier`、`MotionWarpSkewModifier` 提供 UE 式 motion warping。

## 6. 相机
唯一挂点：`animation/mixin/camera/CameraMixin.java:117` 在 `Camera.setup` TAIL 注入，取 `CameraClientRuntime.resolveForCamera(partialTick)` 后 `applyCameraOutput` 覆写位置与 yaw/pitch/roll（:137-140）；在 `setPosition` 调用点后（:143）另做 detached/根运动相机平滑（弹簧 0.035s，水平滞后上限 0.02）。姿态由 `camera/client/CameraDirector`（enter/exit 过渡、`CameraChannelWeights` 通道权重、`CameraLagSolver`、`CameraCollisionSolver`）合成，抖动独立为 `camera/shake/CameraShaker`。数据源两路：`.animation.json` 相机轨道（`CameraAnimationJsonParser` 2631 行）与 `.bbmodel`（`CameraBlockbenchProjectParser`）。

## 7. 第一人称
实现思路是"临时劫持第三人称渲染"：`model/mixin/first_person/LevelRendererMixin.java:24-36` 在 `renderLevel` 里把 `camera.detached` 置 true，让原版渲染器照常画出玩家身体，渲染后立即还原；配套 `ItemInHandRendererMixin:19` 取消 `renderHandsWithItems`（否则手臂重复）、`EntityRenderDispatcherMixin:20` 取消影子、`FirstPersonLivingEntityRendererMixin:33-48` 只保留 `PlayerItemInHandLayer`、`FirstPersonPlayerRendererMixin:30-37` 先 `setAllVisible(false)` 再 `event.applyModifier()` 只开需要的骨。开关即事件 `VanillaPlayerAnimationEventsKt.postFirstPersonArmAnimationRenderEvent`:20 → `CameraFirstPersonAnimationRenderEvent`（`getShouldRender`=shouldRender&&isValid :50，`modify`:58、`applyModifier`:63），外部可接管手臂骨。`renderHand` 内再临时 `VanillaTransformModel.setShouldTransform(false)`（:39-46）防二次变换。

## 8. model/ 边界
model 只管"静态资源 + 位姿 + 渲染"，不含时间轴。`ModelOrigin`→`ModelOriginBone`（`getParent`:145、`applyTransformWithParents`:159 自行爬父链，等价但独立于 vanilla ModelPart）；`ModelOriginPolygon/VertexSet/Uv/Vertex` 支持基岩多边形与逐顶点 UV。`ModelInstance` 持 index+`ModelPose`+贴图+`RenderFrameCache`:151；`ModelBonePose.getLocalTransform(partialTicks)`:156 做渲染插值，`snapRenderStateToCurrent`:93 提交。渲染自写顶点：`model/renderer/core/ModelRenderingKt.render`:32/60/100 → `ModelOriginCubeRendererKt.renderVertices`:23（`fixFlatCubeNormal`:59）。对原版模型另有一套桥：`model/vanilla/VanillaModelBridge.applyTransform`:82 + `model/mixin/vanilla/model/ModelPartMixin` 在 `translateAndRotate` HEAD/TAIL（:24,:38）劫持，`VanillaTransformModel(Part)` 作鸭子类型。装备绑定/渲染见 `model/equipment/`（`ModelEquipmentRenderer.renderAll`:94）。

## 9. 扩展点/API
- 实体：自实现 `AnimationEntityAnimatable` 或照 `mixin/animatable/PlayerMixin` 写 mixin（4 个范例）。
- 事件（NeoForge EVENT_BUS）：`AnimationBoneUpdateEvent`（`animation/event/AnimationBoneUpdateEvent.java:28`，`setNewTransform`:64）改单骨结果；`ModelChangeEvent`（`model/event/ModelChangeEvent.java:15`，`setNewModel`:53）换模型；`CameraFirstPersonAnimationRenderEvent`、`CameraEntityTurnEvent`、`CameraFollowHeadEvent`、`CameraRootMotionSmoothingEvent`。
- 资源：实现 `PackModule`（`pack/modules/PackModule.java:18`，`read`:33、`collectOverlayEntries`:39）由 `PackLoader` 喂文件；`AnimationAssetNaming.qualify/innerName`（:49,61）决定"文件名.动画名"限定名。
- 物品：`AnimationCapabilities.ITEM_ANIMATABLE`（ItemCapability，`animation/registry/AnimationCapabilities.java:40`）+ `AnimationDataComponents.CUSTOM_ITEM_MODEL`（按 `ItemDisplayContext` 挂不同 animatable）+ `ModelItemInHandRegistrationEvent`。
- 网络：`model/sync/ModelIndexSyncPayload`（`dbe:sync_model_index`）；`AnimationClip.STREAM_CODEC`(:62) 与 `AnimationClipSet.ORIGIN_MAP_STREAM_CODEC`(:130) 同步整包动画。

## 10. 值得学的 5 条
1. 命名即契约：`.animation.json` 后缀 + `qualify(file,name)` 让动画与模型/文件关系完全可推导（AnimationAssetNaming.java:18,49）。
2. 双 Codec：每个资产同时给 `Codec` 与 `StreamCodec`，客户端免二次解析（AnimationClip.java:60-62、AnimationBone.java:288-290）。
3. 显式建模"谁写这一轴"：`RootMotionLocomotionOwnershipPolicy`(planar/yaw/vertical) + `RootMotionPlayerPacketAuthority`，比散落 if 干净（RootMotionLocomotionOwnershipPolicy.java:19）。
4. 渲染态与动画态分离 + 帧缓存：`ModelBonePose` 双路由 + `RenderFrameCache`(ModelInstance.java:151) 是插值/去抖的正确落点。
5. mixin 带开关：`DbeAnimationMixinConfig.shouldApplyMixin` 读 toml 决定 vanilla mob mixin 是否注入（:17），出问题可关。

## 3 个自研动画引擎的坑
1. 全局静态注册表：`AnimationClipSet.ORIGINS`/`ModelOrigin.ORIGINS` 是静态 map，reload 时 `onStart` 直接 clear（PackAnimationModule.java:97），渲染线程若同时在遍历就可能读到空集，跨端 key 还共用 `ModelIndex`。
2. 热路径逐帧分配：`AnimationKeyframeSampler.sample` 每帧把 keyframes 转 `List` 再线性扫（:50-83），IK 每解一次重建父链矩阵与缓存，virtual/virtual 大量 data class copy——`RenderFrameCache` 的存在正说明这里有性能债。
3. 机制层层叠加：legacy 播放实例 + graph + predict-IK + mesh compensation + root motion 都能写位移/朝向，`AnimationPlaybackController` 被撑到 9000 行、近 200 字段与成堆 `shouldFreeze*/shouldSuppress*` 开关（:725-800），"唯一权威"没有在早期收口。

未确认：`animation/playback` 与 `animation_graph` 的调用边界（graph 包不在本次范围），以及动画首次加载时 modelIndex 与 clip 的配对是否完全依赖约定目录结构。

### 4.B 动画图（animation_graph，1.4k class 的旗舰模块）

# B. 动画图子系统 `cn/dbe/animation_graph/`

源码根 `~/Downloads\_dbe\src\cn\dbe\animation_graph\`：800 个 java 文件，对应 jar 内 1448 个 class（反编译自 Kotlin）。是本 mod 最大模块。

## 1. 整体架构与分层

按 jar 内 class 数量：`nodes` 467、`integration` 115、`debug/server` 114、`runtime/transaction` 93、`execution` 72、`definition` 67、`data` 54、`debug`(含子包约 264)、`player` 40、`input` 40、`scheduling` 32、`instance` 26、`serialization` 20、`registry` 17、`catalog/command/dsl/validation/examples` 少量。

分层：

- **定义层（纯数据，可序列化）**：`definition/ParallelGraphDefinition.java:72` 是一张图的完整描述（id/version/skeletonId/nodes/connections/outputPort/parameters/editor/parallelism/blendProfiles/blendSpaces/rigPassEnabled/rigPassGraphId/rigPassBudget），配套 `NodeDefinition/PortDefinition/ConnectionDefinition/StateMachineDefinition/EditorMeta`。`data/` 是运行期值对象（`NodeOutput`、`PoseData`、`RootMotionData`、以及 `FootLockData`/`IkTargetData`/`GraphCommand…` 等"命令类"数据）。
- **运行时层**：`instance/`（`ParallelGraphInstance`=图实例、`NodeInstance`=节点实例、`NodeCapability`）、`execution/`（`GraphContext`/`UpdateContext`/`GraphCommand`/`GraphNodeMemoryStore` + `scheduler/`）、`scheduling/`（批次与降频）、`registry/`（节点与图注册表）、`serialization/`（JSON 编解码 + 校验 + 迁移）。
- **集成层**：`integration/GraphAnimationController.java`（20973 行）把图接到 `cn/dbe/animation` 的播放器；另有 `PoseApplicator`/`RootMotionBridge`/`GraphAnimationControllerBinding`。
- **调试/工具层**：`debug/{server,overlay,gizmo,profiler,sync,buffer}`、`catalog/`（节点规格目录）、`dsl/`、`examples/`、`validation/`。
- **编辑器态（authoring）不在本包内**：图编辑器在 `cn/dbe/ui/blueprint/`、`cn/dbe/tools/blueprint/`；本包通过 `catalog`（节点规格）、`serialization`（读写+校验）、`definition.EditorMeta`（画布坐标 `Rect/Vec2/GroupAnnotation`）为编辑态提供后端。二者共用同一份 JSON。

## 2. 节点系统

**基类** `instance/NodeInstance.java:52`：字段 `id/definition/graphInstance/parameterBindings/inputCache/cachedOutput/weight/isActive/wasActiveLastFrame/capabilities`；生命周期钩子 `onInitialize → onActivate → onUpdate → onEvaluate → onDeactivate → onPostUpdateInactive → onDestroy`（`folds`：`getInput/getParameter/getFloatParameter/emitCommand/readMemory/writeMemory`）。默认能力集只有 `PURE_EVALUATE`，其余为 `UPDATE_STATEFUL/UPDATE_WORLD_QUERY/UPDATE_COMMAND`（`instance/NodeCapability.java:14-17`），用来判定节点是否需要在 update pass 提前跑、是否有副作用。

**注册** `registry/NodeRegistry.java:30`：`implId(String) → KClass`，`createInstance` 走反射无参构造（`:49`）。内置清单一处集中在 `registry/ParallelGraphBuiltinNodes.java:229` `registerAll()`，共 **207 条 implId**（206 个 `sparkcore:` + 1 个 `dbe_npc:`），`registerIfAbsent` 允许外部先注册同名覆盖（`:445`）。与 266 个节点源文件相比，注册数少是因为不少文件是支撑类（`*Kt`、`*Support`、`Resolved*`、`*Plan`）。

**节点类别（按注册名）**：

- 动画播放源：`clip`、`action_slot`、`active_animation`、`action_blend`、`action_trigger`、`blend_space_player`、`damaged_animation_player`、`multi_way_blend`
- 混合：`blend_2`、`blend_1d`、`layered_blend`、`layer_mixer`、`blend_with_profile`、`select`、`select_higher`、`priority_select`
- 姿态/数学：`add/subtract/multiply/clamp/max/float_in_range`、`make_vec3/break_vec3/vec_*`、`quat_*`、`transform_*`、`space_convert_position|rotation`、`axis_mask_*`、`pose_space_convert`、`pose_cache`
- 状态机/逻辑：`state_machine`、`transition_pose_evaluator`、`and/or/not/greater`、`prev_value`、`edge_trigger`、`latch/hysteresis/debounce/cooldown/timer/expiry_window`
- 信号/滤波：`smooth_damp`、`ema_filter`、`rate_limit`、`integrator`、`phase_window`、`phase_play_rate`
- 世界查询：`raycast`、`shape_cast`、`ground_probe`、`walkable_surface_probe`、`clearance_test`、`headroom_test`、`stair_probe`、`predict_ik_*`（6 个）、`collision_mask_select`、`mesh_buffer_envelope`
- IK/脚部：`ik`、`fabrik_ik`、`leg_ik`、`two_bone_ik`、`foot_lock`、`foot_align_to_surface`、`ik_target_from_surface`、`foot_planted_detector`、`rigpass_ik_env`
- 路径/候选：`make_path`、`path_*`、`bezier_segment`、`make_candidate`/`score_candidate`/`filter_candidates`/`sort_candidates`/`select_candidate`
- 参数/存储：`read_*`（15+ 个只读源）、`write_runtime_state`、`graph_param_write`、`table_get/table_set`
- 输出节点：`final_pose`、`root_motion`、`movement_constraint_output`、`foot_lock_output`、`play_rate_output`、`stride_scale_output`、`ik_target_output`、`gameplay_event_output`、`debug_draw_output`、`telemetry_output`、`locomotion_state_output`、`rigpass_output`

**序列化方式**：节点本身不序列化（反射建实例），序列化的是 `NodeDefinition{id, implId, params}` 与连接；参数值支持 `"$path"` 形式的属性表达式——`NodeInstance.onInitialize` 里遇到 `$` 前缀就交给 `PropertyAccessorCache.getOrCompile()`（`NodeInstance.java:179-180`、`variable/PropertyAccessorCache.java:31`）编译成 `PropertyAccessor`，否则按字面量解析。

**声明式规格（editor 用）**：`catalog/NodeSpecDto.java:19`（implId/type/input_ports/output_ports/default_params/required_params/param_aliases/legacy/authoring_only），静态入口 `SparkNodeCatalog.getNodeSpec()`，未命中回落到 `PrimitiveNodeCatalog`。节点类型枚举只有 5 类：`SOURCE/BLEND/MODIFIER/OUTPUT/SUBGRAPH`（`GraphNodeType.java:24-28`），数据类型 30+ 种（`GraphDataType.java:24-54`，含 POSE/PATH/SURFACE_HIT/CAPSULE/CANDIDATE/各种 COMMAND）。

## 3. 运行时与执行器

**实例化** `ParallelGraphInstance` 构造（`instance/ParallelGraphInstance.java:226-309`）：遍历 `definition.nodes` → `NodeRegistry.createInstance` → 建 `incomingConnectionsByTarget`/`outgoingConnectionsBySource` → `new GraphLayerScheduler(...)` → `scheduler.validateNoCycles()` 环检测 → 逐节点 `onInitialize`（超过 10ms 记慢节点）。

**双 pass 模型**（核心设计）：

1. **Update pass**：`updateLocked/executeUpdatePass`（`:373/:757`）从输出节点自顶向下 `updateNode`（`:1080`）传播 weight/激活/重置/重启语义；跑完统一收集 `activeNodes` 与 `weight > 1e-4` 的节点进 `evaluateNodes`（`:565-580`）——即"只求值活跃子图"。
2. **Evaluate pass**：`evaluateSerialOutput`（`:2266`）/`evaluateParallelOutput`，用 `GraphLayerScheduler.buildLayers(evaluateNodes)`（`execution/scheduler/GraphLayerScheduler.java:119`，`int[][]` 邻接表 + `inDegree` + 复用数组，避免每帧分配）拓扑分层；每层先 `wireInputsForLayer`（`:2602`，把上游 `cachedOutput` 写进下游 `inputCache`）再执行本层节点，最后由输出节点出 `NodeOutput/PoseData`。
3. **层内并行**：`GraphTaskExecutor.executeLayer`（`execution/scheduler/GraphTaskExecutor.java:48`）——单节点层直接串行特快路径（`:52-56`），多节点层用 kotlinx.coroutines `supervisorScope + async` 并发。运行时开关 `GraphParallelismMode AUTO/FORCE_SERIAL/FORCE_PARALLEL`（`GraphParallelismMode.java:24-26`），定义里也可写死（`ParallelGraphDefinition.getParallelism()`）。
4. **生命周期锁**：`withLifecycleLock`（`ParallelGraphInstance.java:354`）用 ReentrantLock 串行 update/evaluate，等待 ≥20ms 打 `[GraphLockWaitDiag]`。
5. **缓存**：节点级 `cachedOutput` + `clearEvaluateCache`/`hasPreparedEvaluatePlan`（`:1622/:1636`，支持按 implId 级联失效）；帧内存 `GraphNodeMemoryStore.beginFrame`；`pose_cache` 节点可复用姿态。

**多阶段求值**：`execution/GraphExecutionPhase.java:8` 定义 `UPDATE/PRE_POSE/RIG_PASS/POST_IK`，同一张图会在不同阶段用不同 `GraphContext` 跑（`GraphAnimationController.java:9411/9460`），例如 `LegIkNode` 只在 `PRE_POSE` 写目标（`nodes/LegIkNode.java:699`）。

**RigPass（IK 环境预计算）**：`integration/GraphAnimationControllerRuntimeSupportKt.java:136` `executeRigPassCore` 读取 `definition.getRigPassGraphId()` 拿第二张图，在 pre-pose 上求 IK 环境，并受 `RigPassBudget{maxTracesPerTick, traceReuseDistance}` 限流（`definition/RigPassBudget.java:25`）——把"每个 IK 节点各自射线"合并成一次预算内查询。

**批次与降频**：`GraphAnimationController` 暴露五阶段 API `prepareFiveStageUpdate/updateFiveStage/finishFiveStageUpdate/evaluateFiveStage/commitFiveStage`（`:8779/8928/8955/8983/9139`），阶段枚举 `scheduling/AnimationBatchStage.java:14-18`（CAPTURE/UPDATE/FINISH_UPDATE/EVALUATE/COMMIT），支持跨实体批量 `AnimationPlaybackRequestScheduler`（`scheduling/AnimationPlaybackRequestScheduler.java:38`）与 NPC 按距离/战斗状态降频 `GraphCadencePolicyKt.selectNpcGraphCadenceTier`（`scheduling/GraphCadencePolicyKt.java:65`）、`GraphUpdateMode.ADVANCE/REUSE`。容错：`maxFailures=3`、`shouldFallbackToLegacy()`（`ParallelGraphInstance.java:245/:3133`）。

**未确认**：`runtime/transaction/`（93 class，`SparkAnimationAbiV1` SCHEMA=`spark_animation_abi_v1`、ABI_MAJOR=1、大量 `*Wire` 记录与 capability 位）只有常量与线格式定义，未见生产调用点，疑似为将来 host/原生运行时预留。

## 4. 与动画核心的接口

- `GraphContext` 直接持有 `AnimationAnimatable / AnimationPlaybackController / ModelController`（`execution/GraphContext.java:46-50`），节点通过它拿到播放器。
- **播放器实例由节点创建**：`ClipNode.ensureAnimationInstance`（`nodes/ClipNode.java:2029`）惰性 `new AnimationPlaybackInstance(animatable, new AnimationIndex(modelIndex, animationName))`（`:2161`），再向 `getAnimController()` 注册/注销 external sync group。`BlendSpacePlayerNode` 同理。
- **回写通道**：`publishServerAnimationNotifyPlayer`（`ClipNode.java:1880`）、`recordNotifyTriggered`（`:4734`）、`resolveRootMotionBoneName`（`:3742`）、`getOverallSpeed()`（`:307`）。
- **输出落地**：`PoseApplicator.applyPoseToModel`（`integration/PoseApplicator.java:42`，调用点 `GraphAnimationController.java:9174/17026`）；根运动经 `RootMotionBridge`；命令类输出由 controller 的 `typedFootLock/typedIkTarget/typedPlayRate/typedMovementConstraint` 等（`GraphAnimationController.java:1026-1106`）供动画核心查询。
- **绑定与入口**：`GraphAnimationControllerRegistry`（`:27`）登记所有控制器；`GraphAnimationControllerBinding`（`integration/GraphAnimationControllerBinding.java:52`）在 `EntityJoinLevelEvent` 按 `ModelIndex → GraphRegistry.findGraphFor()` 自动绑定，也支持 `bindExplicitGraph`；播放器侧通过 `AnimationPlaybackController.getGraphAnimationController()`（`cn/dbe/animation/playback/controller/AnimationPlaybackController.java:1589`）访问，每物理子步由 `AnimationPlaybackApplier.physTick → controller.physTick()`（`:489`）驱动。热重载：`GraphRuntimeReloader`、`GraphHotReloadWatcher`、`GraphAnimationController.switchGraph`（`:7881`）。

## 5. 编辑器集成与数据来源

**注意区分两套编辑器**：

- `cn/dbe/ui/animation_editor/`（236 文件，`AnimationEditor.java` 4132 行）是**动画/时间轴编辑器**（曲线、通知、骨骼、预览），与 animation_graph 几乎无耦合——目录内只有 `AnimationEditorDocument.java` 一处 import `animation_graph.variable.dictionary.AnimationClipDictionary`。
- **图编辑器**在 `cn/dbe/ui/blueprint/`（如 `AnimationGraphAssetSidebar.java` 22775 行、`SparkAuthoringCanvasHost/View`、`mgmc/*Popup`、`state_tree/`）+ `cn/dbe/tools/blueprint/animation_graph/NpcAnimationGraphAuthoringService.java`（7713 行）。authoring 的"业务后端"仍在 animation_graph（codec/catalog/validator）。

**数据来源（自定义格式，非原版 datapack 目录）**：走 mod 自己的 pack 读取器 `PackParallelGraphModule`（`cn/dbe/pack/modules/PackParallelGraphModule.java`，模块 id = `spark_graphs`）：`read()` 里对 JSON 调 `GraphDefinitionParser.parse`（`serialization/GraphDefinitionParser.java:132`，源文件名 `GraphResourceLoader.kt`，先做 keyAliases 归一化），`onFinish()` 走 `GraphRegistry.replacePackSnapshot` 替换整批包内图。资源路径形如 `spark_graphs/<ns>/animation_graphs/<name>.json`（见 `LocalResourcePackRuntimeBridge.java:374`、`GraphRegistry.java:435` 的路径约定）。另有本地文件路径 `cn/dbe/tools/storage/animation_graph/AnimationGraphFileStore.java`（含 save drafts/session/temp 文件）与 NPC 编辑器的网络包注册（`NpcAnimationGraphEditorPayloadsKt.java:227`）。

**格式与版本**：`SparkGraphAssetCodec`（`ASSET_TYPE="spark_graph"`、`DEFAULT_FORMAT_VERSION=5`，`:63-64`）与 `ForMcAnimationGraphAuthoringCodec`（authoring blueprint，可 `toLegacyEnvelope` 降级）/`ForMcBlueprintGraphCodec`；迁移链 `GraphMigration.migrate`（写 `spark_graph_version`）与 `LegacySparkGraphImport`；校验 `GraphValidator.validateWithModel`（骨架骨骼级校验）、`validation/GraphSkeletonValidator`。

## 6. 扩展点

1. **自定义节点**：`NodeRegistry.register(implId, KClass)`（全局单例，`registry/NodeRegistry.java:30`）；要求**无参构造**且继承 `NodeInstance`（推荐继承 `nodes/PrimitiveNode` 拿输入解析糖）。内置注册用 `registerIfAbsent`，外部先注册即可覆盖。
2. **自定义图来源**：实现 `PackModule`（`cn/dbe/pack/modules/PackModule.java:18`，`getId/read/onFinish`），在 `PackReaderRegistrationEvent.register`（`pack/event/PackReaderRegistrationEvent.java:26`）注册；再 `GraphRegistry.register/replace`。
3. **编辑器节点规格**：`NodeSpecDto` + `SparkNodeCatalog.getNodeSpec()`（可被 `PrimitiveNodeCatalog` 兜底），即"给编辑器看的端口/默认参数字典"。
4. **代码建图**：`dsl/GraphDsl`、`NodeBuilder`、`ParallelGraphBuilder`；样例 `examples/GraphExamples.java`。
5. **调试 API**：`debug/server/DebugApiProviderRegistry` + `BuiltinDebugApiProvider` + `NettyDebugServer`（5021 行，protobuf 帧推流），供外部工具挂载。
6. **参数体系**：`variable/PropertyRegistry` 可注册 `KotlinAnnotationProvider/ResourcePackProvider/StaticPropertyProvider` 等属性提供者，节点参数即可用 `$表达式` 绑定（`NodeInstance.java:179`）。
7. **未确认**：`runtime/transaction` 的 ABI、`debug/server` 的网络协议是否有对外文档。

## 7. 值得学的 5 条做法

1. **节点"执行 + 规格"双轨**：运行靠 `NodeInstance` 子类，编辑靠 `NodeSpecDto` 元数据字典（端口/默认参数/别名/legacy 标记），编辑器不必加载/实例化节点类，规格式 UX 与执行解耦。
2. **权重驱动的活跃子图求值**：update pass 决定谁 active、谁的 weight>1e-4，evaluate pass 只对这批节点做拓扑分层，天然省掉大量无效求值（`ParallelGraphInstance.java:565-580`）。
3. **分层 + 层内并行 + 单节点层特快路径**：`GraphLayerScheduler` 用扁平 `int[][]` + 复用缓冲区而非 Map/对象图；层内先集中 `wireInputs` 再并发跑，把数据竞争面压到"读上游 cachedOutput"这一点（`GraphLayerScheduler.java:119`、`GraphTaskExecutor.java:48`）。
4. **把昂贵的世界查询抽成独立预算的 RigPass 图**：`rigPassGraphId + RigPassBudget` 让 IK 环境一次算清，而不是每个 IK 节点各打一遍射线。
5. **可观测性当一等公民**：`DebugHook`/`DebugEventBus`、系统属性开关 `AnimationFlowTrace.enabled()`（`Boolean.getBoolean("dbe.anim_flow.trace")`）、`PlayerAnimationStallDiagnostics` 对 >50ms 阶段上报、慢节点/慢锁日志、`NettyDebugServer` 远程推帧、`catalog/SparkNodeCatalogExportTool` 导出规格——图系统能长期演进的前提。

## 8. 两个"自研图/可视化系统"的坑

1. **上帝类与巨型节点不可维护**：`GraphAnimationController` 20973 行、`ui/blueprint/AnimationGraphAssetSidebar` 22775 行、`StateMachineNode` 6190 行、`ClipNode` 5789 行。反编译后单文件几乎无法通读，改动靠全文搜索，多人协作冲突与回归风险极高（本包 `GraphAnimationControllerRuntimeSupportKt`/`GraphAnimationControllerSpecializationsKt` 这种"从大类里削函数出来"的痕迹，正是事后补救）。自研图系统应一开始就按职责切分（绑定/参数/根运动/IK/网络/诊断），单文件超过 ~2000 行即视为设计信号。
2. **字符串 implId + 反射是运行期约定，且 schema 必须从第 0 天版本化**：`NodeRegistry.createInstance` 只做 `getDeclaredConstructor().newInstance()`，写错/漏注册只能在运行时抛 `NodeImplMissingException`，且已出现同一个实现挂两个 implId 的重复（`ParallelGraphBuiltinNodes.java:283` 与 `:432` 都指向 `SyncGroupPhaseResetNode`）。同时代码里满是补丁式兼容：`keyAliases` 归一化、`normalizeActiveAnimationInputPorts` 老端口改名、`GraphMigration` 链、`LegacySparkGraphImport`——说明格式升级没在早期做版本闸门。对策：注册表 + 编译期/CI 清单校验（或注解处理器生成清单），资产 JSON 首版就写 `version` 并配一个强制 migrate + 校验器。

### 4.C GAS 能力系统 + action + 状态树 + sheet

# DBE 源码分析 C：gas / action / state_tree / sheet

分析根：`~/Downloads\_dbe\src\cn\dbe\`。行号以反编译后的 `*.java` 为准。

## 1. GAS 总览（149 java）

`gas/` 子包与职责：`ability/`(15) 核心容器与能力类型；`effect/`(9) GameplayEffect 与属性；`tag/`(6) 标签与查询；`target/`(3) 目标数据与查询；`hitbox/`(10) 物理判定窗口；`tasks/`(68) 异步能力任务；`presets/`(13) 内置能力与蓝图能力；`sync/`(9) 网络载荷；`event/`(11) 事件与生命周期阶段；`client/hitbox/`(3) 客户端镜像与调试渲染；`command/`(2) Brigadier 命令。

**是自研的「UE GAS 概念对齐版」，不是移植**。对照 UE：Ability≈`Ability`+`AbilitySpec`+`AbilityType`，Effect≈`GameplayEffectSpec`/`ActiveGameplayEffect`（`gas/effect/GameplayEffectSpec.java:21`），Attribute≈`AbilityAttributeId`+`AbilityAttributeStore`，Tag≈`GameplayTag`(点分层级，`gas/tag/GameplayTag.java:47` 前缀匹配)，Target≈`AbilityTargetData`（`gas/target/AbilityTargetData.java:18` 是 sealed interface），Task≈`AbilityTask`（`gas/tasks/AbilityTask.java:15`），Cue 缺失，改为 `action/notifications` 的表现层（粒子/音效/刀光/震屏）。ASC 不是挂在实体上的组件，而是 `AbilityHost` 接口经 mixin 注入实体（`entity/mixin/EntityMixin.java:82`），由 `EntityJoinLevelEvent` 创建（`gas/ability/AbilitySystemComponentApplier.java:31-40`），`EntityTickEvent.Pre` 驱动 `tick()`（`entity/EntityRuntimeEventHandler.java:42-49`）。

## 2. 能力生命周期

激活：`AbilitySystemComponent.tryActivateAbility`(`ability/AbilitySystemComponent.java:171`) → `AbilitySpec.tryActivate`(`ability/AbilitySpec.java:103`)。`tryActivate` 内依次检查：是否已 initialize、`instancingPolicy`(`ability/AbilityInstancingPolicy.java:14`，仅 INSTANCED_PER_ACTOR / INSTANCED_PER_EXECUTION 两种，前者复用已存在实例)、`isAbilityBlocked`(`AbilitySystemComponent.java:245`，标签双向 matches)、`canActivate`，再分配 `AbilityActivationId`、发 ACTIVATED/COMMITTED 生命周期事件、调 `Ability.activate`(`ability/Ability.java:36`)。取消/结束：`cancelAbility`/`endAbility`(:199/:210)→`AbilitySpec.cancelAll`/`endAll`(:196/:206)→`endAbility(spec,ability,wasCancelled)`(:163)，遍历 task `end(true)` 后移除实例并发 CANCELLED/ENDED。客户端预演走 `tryActivateAbilityLocal`(:185) + `endAbilityLocal`(:234)，随后 `TryActivateAbilityLocalPayload` 回传服务端（`gas/sync/TryActivateAbilityLocalPayload.java:89`）。

**参数与等级**：`AbilityType`(`ability/AbilityType.java:28-42`) 只有 instancingPolicy、tags、工厂；能力类型是数据驱动——`AbilityTypeDataProvider`(`ability/AbilityTypeDataProvider.java:64-96`) 导出 `spark_engine/<pack>/ability/<modid>/*.json`，`pack/modules/PackAbilityTypeModule.java:54` 装载；蓝图能力靠 `blueprint_ref/entry_event/cancel_event/auto_end_when_idle` 四个字段（`gas/presets/BlueprintAbilityTypeSerializer.java:153`），运行时反射加载 `MgmcBlueprintAbility`，mgmc 未安装则降级 `MissingMgmcBlueprintAbility`（`gas/presets/BlueprintAbilityRuntimeFactory.java:23-42`）。参数通道是 `ActivationContext`（`ability/ActivationContext.java:21-30`，自带 codec 并注册进 `registry/DbeRegistries.java:28`），可扩展，但仓库内唯一实现是 `Empty`(:64)。**没有等级/rank 概念，也没有冷却与消耗**（全 gas 目录 grep cooldown/cost 为空；UE 的 Cooldown/Cost/Level 三件套需自行补，冷却只以动画图节点形式存在 `animation_graph/nodes/CooldownNode.java:22`）——这点是「未确认是否有外部补齐」的空白。

## 3. 效果与标签

`GameplayEffectSpec` 支持 durationTicks/periodTicks/stackLimit/grantedTags/blockedByTags/modifiers/payload（`effect/GameplayEffectSpec.java:21-36`）。`applyGameplayEffect`(`AbilitySystemComponent.java:781`) 先做 `blockedByTags` 免疫判定并广播 BLOCKED_IMMUNITY，再按 spec.id 叠层（受 stackLimit 限制、重置剩余时间、叠加快照），instant 效果直接结算不入表，否则进 `activeEffects` 并 `addLooseTag` 授予标签。`tickActiveEffects`(:519) 处理周期结算与到期移除。**关键设计：改属性前先捕获 `GameplayEffectModifierSnapshot`，移除时逆序回滚**（:913 与 :869）。属性对接 MC：`AbilityAttributeStore`(`effect/AbilityAttributeStore.java:32/84`) 把 health/max_health/movement_speed/attack_damage/attack_speed 映射到原版 `Attributes`/`setHealth`（用 `setBaseValue`），其余路径落本地 transient Map——所以它读写的是原版 attribute，而非自定义属性系统。标签面：`GameplayTagContainer` 增删查（`gas/tag/GameplayTagContainer.java:46-56`）、`GameplayTagQuery`(all/any/none/exact，`gas/tag/GameplayTagQuery.java:62-80`)、ASC 侧 looseTag 计数与 blockedAbilityTags 计数表（:636/:664），`AbilityActionTags`(`gas/tag/AbilityActionTags.java:15-27`) 定义 `ability.action.started/commit/finished/cancelled`、`ability.attack.hit_window.*`、`ability.footstep`，与动画通知（AnimationNotifyKt:141 发 `AbilityEvent`）打通。

## 4. 目标与判定

`AbilityTargetQueries`(`gas/target/AbilityTargetQueries.java:38/109/188`) 提供球形/盒形重叠、扫掠重叠、前向 trace 三类查询，产 `AbilityTargetData.EntityList`（按距离排序、livingOnly/includeOwner/maxTargets 过滤）；`AbilityTargetDataPayloads`(35KB) 负责序列化。真正有特色的是 hitbox：`HitboxWindowRuntime`(单文件 289KB) 用**真物理**——jme3 `BoxCollisionShape`+`PhysicsRigidBody` 挂到 `sourceBone`/`sourceSocket` 上，`WindowConfig`(`gas/hitbox/HitboxWindowRuntime.java:3503`) 含 shape（半长）、offset、role（ATTACK/DEFENSE/COLLISION，:4130）、`detectedObjectTypes`（BODY/ATTACK_BOX/DEFENSE_BOX/COLLISION_BOX，:2331）、hitOnce/livingOnly/includeOwner/maxTargets/ignoreProjectiles/tumbleProjectiles。窗口 owner 用 UUID+scope 索引（WindowKey :4031），每 tick `tickOwner`(:572) 刷新位姿，`HitboxPoseSamplingKt.java:30` 在上一帧与当前帧位姿间插值采样，避免快动作穿透；命中来源区分物理接触/同步防御查询/攻击盒 vs 实体包围盒（TargetSource :3373），输出 `CollisionContact`(:2181)。受击方向另有 `HitboxAttackPreviewCache`（攻击预览缓存，供格挡/弹反预判）、`HitboxDamageFieldContext`(:114 组装伤害字段)、`HitboxDefenseDamagePolicy`。伤害落点是 `AbilityCombatEffects.applyDamage/applyKnockback`（`gas/effect/AbilityCombatEffects.java:38/93`），由 `ApplyDamageEffectTask`/`ApplyKnockbackTask` 调用。客户端有 `HitboxWindowClientMirror`(`gas/client/hitbox/HitboxWindowClientMirror.java:61/100/206`) 用同批 payload 自建 mirror body 做调试渲染与预测。

## 5. 任务与同步

tasks/ 68 个类几乎一一对应 UE 的 AbilityTask：`WaitDelayAbilityTask`、`WaitAbilityEndTask`、`WaitTagQueryTask`、`WaitGameplayEffectEventTask`、`WaitComboWindowTask`、`TraceHitTargetsTask`、`OpenHitboxWindowTask`、`RootMotionSourceTask`（含 JumpForce/MoveTo/RadialForce 三个 source）、`NetworkSyncPointTask`（`gas/tasks/NetworkSyncPointTask.java:33`，带 `activationId`+timeout，经 `AbilityNetworkSyncEvent` 做定点同步）等；`CombatAbilityTasksKt`/`EffectAbilityTasksKt`/`MovementAbilityTasksKt` 是 DSL 门面。**异步模型是「同 tick 单线程队列」**：`handleGameplayEvent/handleInputEvent/handleNetworkSyncPoint` 只往 `ConcurrentLinkedQueue` 塞（`AbilitySystemComponent.java:406-427`），`tick()`(:421) 顺序 drain 四类队列再 tick 所有 task，因此回调里不会重入，且天然按帧有序；结果用 `AbilityTaskResult`（completed/cancelled/timeout）+ `OneShotAbilityTask`/`RepeatTask` 收尾。同步层：`gas/sync/` 7 个 Entity 载荷（give/clear/activate/cancel/end/endAll）+ 2 个 Local 载荷，服务端权威 `onRep*`(`AbilitySystemComponent.java:994-1036`) 在客户端直接复放 `tryActivate/endAll`；注意 `giveAbility`(:148) 仅在 `!isClientSide` 写表，客户端表由 `onRepGiveAbility` 补——两侧状态靠重放收敛。

## 6. action/（261 java）

`action/` 是**动作（Action）资产的 authoring+runtime**，即「一段有段位/窗口/标记/根运动的动画序列」层，与 GAS 平行而非其运行时。资产模型 `ActionAsset`(`action/asset/ActionAsset.java:24-36`)：model/blend/rootMotion/headLook/camera/segments/windows/markers/slotId/tagRules；窗口与标记都是「时间区间/时间点 + typeId + JsonObject 参数 + notifyGraphRef」（`asset/ActionWindow.java:18`、`asset/ActionMarker.java:15`），typeId 注册在 `ActionWindowTypeRegistry`（攻击/防御/碰撞/粒子/原版粒子/音效/箭矢/刀光/震屏/输入路由/预输入/基础/攻击吸附/朝向对齐，:64 与 :310）。

运行时：`ActionPlaybackManager`(202KB，静态单例 :110) 负责 `prepareAction`/`beginActionRequest`(请求入口与去重)/`advanceAction`/`synchronizeActionVisualCursor`/`acceptMappedInput`(:2115)；`ActionPlaybackSession`(65KB) 是单实例状态机（play/pause/setPlayRate/advance/seek/jumpWithinAction/interrupt，全 `synchronized`)；`ActionSlotRuntime`/`ActionSlotGroupRuntime`/`ActionSlotPoseComposer` 做槽位权重与位姿混合；`ActionDispatchRequest` 描述「从哪个 source 段跳到 target 段」的请求（含 requestId/sequence/authoritative/tagRules）。`notifications/runtime` 是表现层：`ActionWindowTracker`(:33，begin/boundaries/advanceActive/apply/closeAll 管理窗口生命周期)、`ActionNotifyGraphRuntime`(:113 consume 事件)、`ActionMarkerIndex`/`ActionMarkerGraphRuntime`/`ActionMarkerPresetExecutor`(对 `AbilityHost` 适配)；`notifications/blueprint` 下 `ActionNotifyGraphBlueprintExecutor`(70KB) 是窗口/标记触发的蓝图子图执行器，`ActionHitboxCollisionRuntime`/`ActionHitboxScopeController` 把攻击窗口接到 `HitboxWindowRuntime`。`trigger/` 是输入与路由：`ActionInputBuffer`(:50/89，带 priority/expiresAtTick/directRoute 的输入缓冲)、`ActionInputRouter`(:127)、`ActionRouteDispatcher`(:68，支持 forceRetrigger/syncBeforePlayback)、`trigger/event` 处理伤害/死亡事件（`DeathActionRemovalRuntime` 移除亡者动作）。`tag/ActionTagRuntime`(:70 evaluate/:289 activate/:412 deactivate) 实现动作互斥与打断（规则在 `tags/rule/GameplayExecutionTagRules.java`）。`sync/`：播放时钟锚点同步（`ActionPlaybackClockSyncPayload.java:34`、`timeline/ActionPlaybackClockSynchronizer/Anchor/Correction`，客户端视觉追帧）、`C2SActionMappedInputPayload`+`S2CActionMappedInputResultPayload`（客户端输入预测、服务端裁决回执）、窗口关闭回执与 `timeline/ActionHitStopRuntime`（命中定格）。`graph/nodes/` 是动画图侧节点：`ActionSlotNode`(`action/graph/nodes/ActionSlotNode.java`) 继承 222KB 的 `ActionSlotPlaybackSampler`，每帧采样动作位姿并驱动 PlaybackManager；蓝图侧由 `BlueprintAnimationGraphNodes.java:398` 提交 `ActionSlotPlaybackRequests` 入队。`authoring/`+`editor/`+`storage/`(71KB/29KB/56KB) 负责分类、模板图生成与持久化。

## 7. state_tree/（87 java）

**是标准 SCXML 的 HFSM，不是 UE StateTree 的复刻**：`model/SCXML.java:36` 包装 `org.apache.commons.scxml2.model.SCXML`，另带 metadata/原始 XML/解析告警/节点元数据；`parser/StateTreeParser.java:137` 解析；`runtime/StateTreeExecutorFactory.java:33` 组装 `SCXMLExecutor`+`SimpleDispatcher`，向上下文注入 entity/level/definition/stateTreeId/executor。分层清晰：`authoring/`（`StateTreeAuthoringService.java:108 open/:139 save/:1841 createOrOpenBlueprint/:2045 createOrOpenSubGraph`，文档模型 `StateTreeAuthoringDocument`，映射器 `StateTreeScxmlAuthoringMapper`，绑定 `StateTreeBlueprintBinding` 用 engine/ref/event/phases 指向蓝图）→ `pack/`（`StateTreePackageManifest.java:41` 含 entryTree/defaultBindings/trees，`StateTreeDefinitionLoader.java:48` 按路径装载，`StateTreePackModule.java:131 tryStartFor` 接到实体）→ `runtime/`（`StateTreeInstance.java:137 start/:252 progress/:305 sendEvent/:556 startDelay`；`StateTreeTaskScheduler.java:44/143/196` 管生命周期任务与超时；另有 Delay/Input/InputCombo/VariableDefaults）→ `core/`（`StateTreeEntityManager.java:63 startStateTree/:340 progress/:373 reload/:856 getDebugInfo`，每实体一个管理器，`StateTreeManagerRegistry.java:152`，`StateTreeBridgeService.java:39/78` 对外 start/广播）→ `event/`（事件别名、表达式、成员目录）→ `mirror/`（`StateTreeMirrorPort`/`Snapshot`/`Log`，调试镜像，有 Noop 实现）。**驱动关系是「谁驱动谁」中较干净的一处：state_tree 不 import 业务包**（全目录仅 `runtime/StateTreeInstance.java:6` 引了 HitboxWindowRuntime 做清理），外部能力经 `StateTreeScriptExecutorRegistry`(engine id→executor) 与 `StateTreeEvaluatorRegistry` 反向注册（`evaluator/StateTreeScriptDispatch.java:210` 派发，`tools/blueprint/mgmc/state_tree/BlueprintStateTreeScriptExecutorBootstrap.java` 注册蓝图引擎）。事件由 NPC 侧桥接广播（如 `npc/integration/state_tree/NpcCommonStateTreeBridge.java:73` 发 `npc.init`/`game.entity.spawn`），每服 tick 由 `NpcStateTreeLifecycle.java:182` 调 `progressManagedEntity()`。即：**state_tree 决策 →（引擎=蓝图）→ 动作/能力；动画图与 GAS 反过来给 state_tree 喂事件**。

## 8. sheet/（16 java）

**不是贴图集，是「表格」——战斗受击反应表**（`sheet/reaction/`）。`CombatReactionTableAsset`（schemaVersion/id/displayName/columns/rules）是行-列数据表：列声明字段与类型（`CombatReactionColumn` + `CombatReactionValueType` TEXT/NUMBER/BOOLEAN），规则 `CombatReactionRule`（enabled + conditions + output），条件 `CombatReactionCondition`（field/operator/value/secondValue），输出 `CombatReactionOutput` 只带一个 `animationId`。标准字段是 `Type/Strength/AttackHand/IsDead`（`sheet/reaction/CombatReactionStandardFields.java`）。匹配器 `CombatReactionTableMatcher.match(asset, fields)`(:41) 取首个命中规则，配套 codec/validator/nameRules 与 `client/CombatReactionI18nKt` 本地化；存储 `tools/storage/sheet/CombatReactionTableStorage.java`。消费方在动作侧：`ActionReactionTableRuntime.resolve`(`action/runtime/playback/ActionReactionTableRuntime.java:53`)/`applyResolved`(:157) 对 `ActionAnimationSegment.getUsesReactionTable()/getReactionTableId()` 的段做运行期动画替换（上限 256 段），即**按打击类型/强度/左右手/死亡动态选取受击动画**，最终写回 `ActionSlotPlaybackRequest.resolvedSegmentAnimations`。

## 9. 值得学的 5 条

1. **零侵入的 ASC 挂载**：`AbilityHost` 接口 + mixin(`entity/mixin/EntityMixin.java:82`) + 两行事件(`AbilitySystemComponentApplier.java:31-40`)，不用改实体继承体系即可给任意实体加能力系统，且生命周期与 tick 都挂在 NeoForge 事件上。
2. **事件队列化 + 标签路由**：`handleGameplayEvent` 只入队、`tick()` 统一 drain(`AbilitySystemComponent.java:421-478`)，回调按 `GameplayTag` 前缀匹配分发，天然免重入、顺序确定，比直接回调好调。
3. **可回滚的属性结算**：`GameplayEffectModifierSnapshot` 快照 + 逆序还原(:913/:869)，配合 looseTag 引用计数，让 buff/debuff 叠加与到期都能精确复原。
4. **用物理 sensor 做判定并跨帧插值**：`HitboxWindowRuntime` 以骨骼挂点驱动 jme3 Box sensor，`HitboxPoseSamplingKt.java:30` 做位姿插值采样，另有攻击预览缓存供格挡预判——比纯 AABB 扫描更贴近格斗游戏判定，且客户端能用同一批载荷做镜像渲染。
5. **引擎/引用式解耦与可选依赖降级**：state_tree 仅通过 `StateTreeScriptExecutorRegistry` 调外部引擎（`StateTreeScriptDispatch.java:210`）；蓝图能力用 `ModList.get().isLoaded("mgmc")` + `Class.forName` 反射加载并降级(`BlueprintAbilityRuntimeFactory.java:23-42`)，库模组可独立运行。

## 10. 两个坑

1. **缺 UE GAS 的三根支柱，且参数无处落地**：全 `gas/` 无 Cooldown 无 Cost，`AbilityType`/`AbilitySpec` 无 level/rank，唯一参数通道 `ActivationContext` 只有 `Empty` 一个实现（`ability/ActivationContext.java:64`），冷却只能外挂到动画图节点 `CooldownNode`。按 UE 心智照搬会踩空；等级/参数是否有外部实现属**未确认**。
2. **巨型上帝文件 + 静态可变全局态，可读性与可测性差**：`gas/hitbox/HitboxWindowRuntime.java` 单文件 289KB、`action/runtime/playback/ActionPlaybackManager.java` 202KB、`action/graph/nodes/ActionSlotPlaybackSampler.java` 222KB、`AbilitySystemComponent.java` 62KB；`HitboxWindowRuntime` 用 `static ConcurrentHashMap windows` + `static AtomicLong windowGenerations`(:94-97)、PlaybackManager 是单例(:110)，测试隔离只能靠 `clearForTests$` 一类后门（`ActionPlaybackManager.java:2558`、`ActionTagRuntime.java:485`）。此外网络路径是两套并行（gas/sync 重放能力状态 + action/runtime/sync 同步播放时钟/输入/窗口关闭），一致性维护成本高。

### 4.D 物理（Bullet/V-HACD）+ 同步 + 注册 DSL

# D · 物理 / 同步 / 注册 子系统

## 1. 物理集成架构

**绑定 Level**：`cn/dbe/physics/mixin/level/PhysicsLevelMixin.java:32-44` 用 `@Mixin(Level.class)` 在 `<init>` 的 RETURN 注入，按 `isClientSide` 造 `PhysicsClientLevel` / `PhysicsServerLevel`，并顺带在 Level 上挂三张表：`collisionObjects`(name→PhysicsCollisionObject)、`tasks`(PhysicsTaskPhase→name→任务)、`imtasks`(立即队列)。对外接口是 `PhysicsLevelPatch extends PhysicsHost, PhysicsTaskQueue`（`physics/PhysicsLevelPatch.java`、`PhysicsHost.getPhysicsBody(name)`）。

**生命周期与每 tick 步进**：`physics/level/PhysicsLevelEventBridge.java` 是唯一入口——`LevelEvent.Load`→`PhysicsLevel.start()`，`Unload`→`close()`，`LevelTickEvent.Pre`→`processTasks(ALL/PRE)`+`requestStep()`，`Post`→`processTasks(ALL/POST)`，`ChunkEvent.Load/Unload`→地形管理器，`ChunkTicketLevelUpdatedEvent`(新票据 >33)→`unloadPhysicsTerrainChunk`。`requestStep()`（`physics/level/PhysicsLevel.java:744-911`）在主线程做准备工作：遍历 `pcoList` 触发 `PhysicsBodyEvent.Tick`、刷新 `PhysicsBodyState`、收集 **activation box / build box**（静态体、terrain section、非碰撞组、失活刚体跳过；动态体用 `PhysicsTerrainDemandPolicy.predictedDynamicBodyBox` 按速度前瞻）、取玩家盒、`updateDirtySections()`、`updateTerrain(demand)`；然后 `signalPhysicsStep()`（:913-922）把 `PhysicsLevelStepRequest` 投进 `Channel`。物理线程协程 `run()`（:577-725）**固定 dt=1/60、每 tick 3 个子步**（`fixedStep=0.016666668f`, `repeat=3`，:615-660），逐子步 `world.update(fixedStep,0,false,true,false)`，结束后回投 `stepCompletedChannel`。子步内 `prePhysicsTick`（:1300+）与 `physicsTick` 前后各发一次 `PhysicsLevelTickEvent.Pre/Post`，最后一个子步里 `querySnapshot.publish(pcoList, seq)`（:1411-1420）。

**原生库**：`npc/DbeNpc.java:101` 在 mod 构造器里 `PhysicsNativeLoader.load("bullet", PhysicsHelperKt.selectLib())`；`PhysicsHelperKt.selectLib()` 按 `JmeSystem.getPlatform().getOs()` 选 `bulletjme.dll`/`libbulletjme.so`/`libbulletjme.dylib`，`PhysicsNativeLoader:47-70` 从 mod 文件 `natives/bullet/...` 拷到临时目录再 `System.load`（`deleteOnExit`）。空间模式二选一：`PhysicsWorldSpaceMode.LEGACY_SOFT_SPACE` 与 `MULTITHREADED_PHYSICS_SPACE`（`PhysicsMultithreadedWorldSpace extends PhysicsSpace`，DBVT + threadCount 构造，`physics/level/PhysicsMultithreadedWorldSpace.java:27`），是否启用由 `PhysicsLevelNativeCapabilities.probe()` 校验 natives 版本（期望 `22.0.3`）、threadSafe、debug 后 `decideMultithreadedSpace` 决定（开关 `-Ddbe.physics_multithreaded_space`）。

**实体→刚体**：`physics/body/PhysicsCollisionObjectEntity.java`（抽象 Entity，`getBody()`）与 `PhysicsRigidBodyEntity`（质量/重力/速度/阻尼…）把所有物理参数塞进 `SynchedEntityData`（`defineSynchedData`:425-450，共 19 个 accessor）并写进 NBT（`physics_*` 键，`readAdditionalSaveData`/`addAdditionalSaveData`）；`onAddedToLevel` 里 `setOwner(body,this)`+`addPhysicsBody(level,body)`（:401-412），`onRemovedFromLevel` 反之。**模型碰撞**：`physics/model/PhysicsModelCollisionSpecCache.java:37-41,125-134` 把 `ModelOrigin` 的 cube 编译成每骨骼 `CompoundCollisionShape`（Box 子形状，上限 128 cube/32 body），`PhysicsModelCollisionBinder.java:554-566` 造 `name="omodel:<gen>:<bone>"`、kinematic、`contactResponse=false`、`collisionGroup=8`、`collideWithGroups=0` 的刚体，并按 64 格距离 + 750ms 宽限启停，`updateBinding`（:586-620）把骨骼世界矩阵写进 body 同时缓存 `renderTransform`。

**地形**：`physics/mixin/terrain/PhysicsServerLevelMixin.java:21-33` 注入 `ServerLevel.onBlockStateChange` 的 HEAD，**前后都是完整碰撞方块时直接 return**，否则 `terrainManager.onBlockUpdated(Set.of(pos))` + `enqueuePhysicsTerrainMutation(pos,gameTime)`。`PhysicsTerrainChunkSection.buildCollisionShape()`（:173-221）先做**同层贪心矩形合并**（`PhysicsTerrainPhysicsTerrainPhysicsTerrainBlockMerger.mergeLayer/findGreedyRect`，同 shapeType 的整格合并成一个大 Box），剩余的走 `PhysicsTerrainBlockShapeManagerKt.getBulletCollisionShape`→`...BlockShapeManager.convertVoxelToCollisionShape(...)`：全方块→共享 `FULL_BLOCK(0.5)`；`VoxelShape.toAabbs()` 数量 2..16→Compound；XZ 满格且 Y 为 0-0.5 / 0.5-1.0→共享上下半砖；否则退化取 bounds box；缓存键是 `BlockState`（ConcurrentHashMap `SHAPE_CACHE`）。

**V-HACD 结论**：`cn/dbe` 全库 grep 不到 `VHACD`/`Vhacd4`/`HullCollisionShape` 任何调用点；`jar/vhacd`、`jar/vhacd4` 是 bulletjme 依赖里的 **Java 包**（`VHACD.compute(positions,indices,params)`、`Vhacd4`），只有 jme3 的 `HullCollisionShape(Vhacd4Hull/VHACDHull)` 会消费它们；`jar/natives/` 只有 `bullet/` 与 `lua/`，**没有 vhacd native 目录**，DBE 也没加载过 vhacd native。即：V-HACD 是"随依赖打包但本 mod 未启用"的能力（是否存在运行期反射调用未确认，静态代码路径未发现）。

## 2. 性能设计

固定步长而非累加器：60Hz 定 dt，每 MC tick 恰好 3 子步（`PhysicsLevel.TPS = 60`，:249），时间与游戏时钟严格对齐；上一轮还 RUNNING 时不排队新步，只补发信号并每 40 tick 打一次 overloaded 告警（:795-815）。步骤合法性由 `PhysicsLevelStepSequencer`（epoch+请求/接受/完成序号，统计 coalesced/stale/rejected/failed）保证不重不丢。地形裁剪：`PhysicsTerrainDemandPolicy` 给 activation 盒（XZ±1.25、下 1.1、上 0.75，速度前瞻 0.25s/max1.75）与更大的 build 盒（XZ±2.0、下 1.25、上 1.0，前瞻 0.75s/max6.0），`buildRadius=activationRadius=2`、**每帧最多起 2 个 chunk 构建、最多 24 次 section 激活变更**（`PhysicsTerrainChunkManager.java:118-120`），地形构建跑在 `min(max(cpu/2,1),2)` 线程的独立协程作用域上（:92-120）。可观测性：`PhysicsStepDiagnostics`（physicsStep/preEvent/preTask/entityEvent/postEvent/postTask）+ `PhysicsPerformanceRecorder`（1200 tick 汇总）+ 资源日志（heap/body 数/terrain stats，1800 tick，:727-739）。

## 3. 视觉同步

三条路：(a) 实体位置仍走原版 `lerpTo/lerpPositionAndRotationStep`（`PhysicsCollisionObjectEntity.baseTick`：服务端 `update{}` 把 body→实体，客户端按 lerpSteps 插值），物理参数走 `SynchedEntityData`；(b) 骨骼刚体由 `PhysicsModelCollisionBinder.renderTransformOf(body)` 提供矩阵，渲染端直接取；(c) 查询走只读快照 `physics/query/PhysicsQuerySnapshot.java`（`enqueueAdd/Remove/ShapeReplacement` 收集 → 物理线程 `publish` 稳定 id+边界，`ReentrantReadWriteLock`），需要"新鲜"时用 `PhysicsLevel.freshAnimationQueryView(maxAgeTicks)`（:514-535，用 `gameTime-querySnapshotPublishedGameTick` 判龄）。地形改动只把 `Set<SectionPos>` 打成 `PhysicsTerrainUpdatePayload`（`physics/terrain/PhysicsTerrainUpdatePayload.java`，客户端 handler `enqueueWork{ markDirtySections }`）发给客户端自行重建，不同步几何。

## 4. sync/ 框架

`SyncData`（data + `MapCodec` + `StreamCodec<RegistryFriendlyByteBuf,?>`；Companion 用 `ByteBufCodecs.registry(...).dispatch` + `NeoForgeStreamCodecs.lazy` 做 **按注册表名 dispatch**），内置 `IntSyncData`（RecordCodec int + composite INT）。`SyncerType<T:Syncer>` 持 `(Level,SyncData)->T` provider，`getRegistryKey()` 未注册即抛"同步体类型尚未注册"；`Syncer` 只需 `syncerType`+`syncData` 两方法，`entity/mixin/EntityMixin.java:52-64` 把它实现给**所有 Entity**（`DbeSyncerTypeRegistry.ENTITY` + `IntSyncData(id)`）。注册三处：`register/DbeRegistries`（`syncer_type`/`sync_data_codec`/`sync_data_stream_codec` 三个 sync(true) 注册表）、`DbeCodeRegistry`（注册 int 的编解码器）、`DbeSyncerTypeRegistry`（`entity` 的 factory 用 `level.getEntity(data)` 反解）。**同步载体是 NeoForge payload 而非 attachment**：`AnimationGraphSyncPayload(syncerType,syncData,graphId,params)` 用 registries dispatch 编解码，客户端 `handleInClient` 里 `syncerType.getSyncer(level,syncData)` 找到目标实体，找不到就 warn"同步失败，动画体未实现 Syncer"；发送示例 `animation_graph/integration/GraphAnimationController.java:7764`。

## 5. registry/ DSL

门面是 `RegistryObjectStore`（`registry/RegistryObjectStore.java:53-290`）：`DbeNpc.REGISTER = RegistryObjectStore("dbe_npc")`，懒初始化 13 个 `DeferredRegister`（item/block/entityType/dataComponentType/mobEffect/particleType/recipeType/recipeSerializer/creativeModeTab/soundEvent/attachment/entityDataSerializer/syncerType），`register(bus)` 一次挂完；`registry(id){ it.sync(true).create() }` 可建自定义 Registry 并自动挂 `NewRegistryEvent`。`RegistryBuilder<R,C>`（deferredRegister + id + validate + build），`CommonRegistryBuilder` 加 `factory`，`ItemBuilder.capabilities{ with(cap,provider) }` 在 `RegisterCapabilitiesEvent` 注册，`SoundEventBuilder.build()` = `createVariableRangeEvent(ns:id)`，`AttachmentBuilder` = factory + `Codec`/`IAttachmentSerializer` + `shouldSerialize`。用法（现网实例）：

```kotlin
REGISTER.item { id = "iron_warhammer"; factory = { MaceItem(...) } }           // EquipmentItems.java:22
REGISTER.entityType { id = "blank_npc"; factory = { EntityType.Builder... } }   // NpcEntities.java:47
REGISTER.soundEvent { id = "custom_sound" }                                     // DbeEffects.java:37
REGISTER.attachment { id = "npc_data"; factory = { NpcData() }; serializer = ... } // NpcAttachments.java:71
REGISTER.syncerType { id = "entity"; factory = { SyncerType { lv, d -> lv.getEntity(d as Int) } } } // DbeSyncerTypeRegistry.java:24
REGISTER.registry("syncer_type") { it.sync(true).create() }                     // DbeRegistries.java:32
```

另有 `registry/mixin/MappedRegistryMixin.java`：取消 `registerIdMapping` 的负 id 写入（warn once），防止坏 id 污染注册表。

## 6. tags/ 与 event/

tags 是自研 GameplayTag 而非 MC TagKey：`asset/` 负责数据包加载与校验（`GameplayTagDefinition`/`GameplayTagLibraryAsset`/`Codec`/`NameRules`/`Redirect`/`Validator`）；`registry/GameplayTagRegistry`（单例 + CopyOnWriteArrayList 监听者，snapshot/all/contains/resolve/`reloadFromLocalPacks`，`RegisteredGameplayTag`=definition+`GameplayTagSource(packId,libraryId)`）；`runtime/GameplayTagRuntimeContainer`（synchronized 的 name→sources 计数集合，add/remove/`removeSource`/has(exact)/matches(query)/listen）+ `GameplayTagRuntimeService` 静态门面；`rule/GameplayExecutionTagRules`（identityTags、activation `GameplayTagCondition`、激活期授予、阻断/取消执行、可打断与被谁打断）。`event/` 只是集中注册清单：`DbeCommonEventRegistrar.register(modBus)` 把 `PhysicsLevelEventBridge`、`PhysicsCollisionFunctionApplier`、`PhysicsModelCollisionBinder`、`EntityHeightOverride`、`EntityRuntimeEventHandler` 等单例挂到 `NeoForge.EVENT_BUS`，`DbeClientEventRegistrar` 同理挂客户端侧。

## 7. 值得学的 5 条

1. **tick 边界准备、物理线程只步进**：主线程收集状态/需求盒/dirty，投 Channel；物理线程只 `space.update`，不碰 MC 世界对象。
2. **固定 60Hz + 每 tick 3 子步 + 序号化 StepSequencer**（accept/complete/fail + coalesced/stale 统计），比朴素 accumulator 更好定位"物理落后/丢步"。
3. **只读快照做跨线程查询**：稳定 id + 发布序号 + gameTime 年龄校验（`freshAnimationQueryView`），把"物理线程写、游戏线程读"变成安全操作。
4. **注册 DSL 化**：`RegistryObjectStore` 一处收口所有 DeferredRegister；`SyncData/SyncerType` 用注册表 dispatch 取代枚举 switch，新增同步类型只加一个 id。
5. **地形分级预算**：BlockState→共享 shape 缓存、同层贪心矩形合并、每帧 chunk/激活配额、只回传 SectionPos 让客户端自建。

## 在 MC 里嵌物理引擎的 3 个坑

1. **线程**：jme3 的 `PhysicsCollisionObject`/`PhysicsSpace` 不是线程安全的（DBE 因此用 `physicsOwnerThread`、`PhysicsTaskQueue.submitImmediateTask`、`SynchedEntityData` 代理写、快照读四道护栏；`PhysicsLevelNativeCapabilities` 还要 probe native 版本/treadSafe 才敢开多线程 space）。绕过护栏直接在主线程 `rayTest`/改 body，典型结果是随机 native crash 且无堆栈。
2. **存档与热重载**：刚体/空间不进存档，只有参数进 NBT；`Level` 卸载必须 `close()`（取消 scope、关 dispatcher、清 hostManager/任务表，:1220-1250），否则重进世界时旧线程仍持有 native 空间 → 崩服；作者另有 `PhysicsLevelCrashRecoveryTracker` + `restart(resetCrashCount)` 兜底。
3. **方块更新与多人同步**：`onBlockStateChange` 先过滤"碰撞形状真变了"的方块，改动入 mutation inbox 再在步进前按预算 wake 相关刚体（`enqueuePhysicsTerrainMutation`/`processPhysicsTerrainMutationWakes`）；网络只发 SectionPos，客户端用**本地** blockstate 重建碰撞——两端方块/资源包不一致就会各自算出不同碰撞，所以 DBE 还额外有 pack 同步通道（configurationToClient `PackSyncPayload`）。

### 4.E NPC 模块（dbe_npc）

# E — `cn/dbe/npc`（DBE NPC 模块）

反编译源：410 个 java / 94720 行（jar 内 839 class）。子包规模：`ai` 120、`network` 109、`control` 26、`mixin` 25、`entity` 24、`server` 16、`player` 15、`integration` 14、`camera` 14、`client` 12、`registry` 7、`event` 6、`compat` 6、`state_tree` 4、`animation` 4、`command` 3。入口 `DbeNpc.java:95-179`：注册 config、加载 Bullet 物理原生库、跑 `DbeRegistries/SyncerTypeRegistry/CodeRegistry`，挂附件、实体、菜单、命令、payload，并初始化本地文件默认数据（`ActionCategoryStorage`/`WeaponTypeMappingStorage`、`GameplayTagRegistry.reloadFromLocalPacks`）。

## 1. Blank NPC：数据驱动的空壳

`entity.dbe_npc.blank_npc` 是 `PathfinderMob` 子类 `BlankNpcEntity`（`entity/BlankNpcEntity.java:37`）。它刻意"什么都不做"：

- 属性只有 20 HP / 0.35 速度 / 2 伤害（:146-148），模型由引擎 ModelIndex 绑定，实体自带皮肤为零。
- 自建 7 个旋转同步字段 + 碰撞宽高（:39-47），碰撞尺寸可同步、写 persistentData 持久化（:175-187）。
- `LookControl`、`BodyRotationControl` 被替换成**全空实现**（:234-271），`tickHeadTurn` 可跳过（:126-131）——朝向完全由 DBE 自己的朝向系统接管。
- 行为只挂 5 个 Goal（:138-144），且带运行时开关 `goalEnabledMap`（:150-161）。
- 所有配置放 Attachment `NPC_DATA` 里：`NpcData`（`entity/data/NpcData.java:41-52`）聚合 pathfinding/search/combat/faction/stateTreeBinding/model/inventory 七个子配置，统一 NBT 存取（:113-140）。

结论：NPC = 空实体 + 附件数据 + 状态树/蓝图，扩展行为不需要改实体类。

## 2. AI 体系

**Goal 层很薄**：`NpcGoalIds` 仅 5 个 id（`ai/goal/NpcGoalIds.java:14-22`），全部实现 `IControllableGoal`。`NearestAttackableTargetGoal` 不自己扫世界，只问 `NpcTargetService`（`ai/goal/target/NearestAttackableTargetGoal.java:43-52`）。

**目标与感知**在 `ai/targeting` + `ai/searching`：`NpcTargetService`（getTarget/setTarget/clearTarget，`ai/targeting/NpcTargetService.java:30-99`）转发到 Checker/Writer/Clearer；`NpcSearchVision` 做多点采样（躯干上/中/下 + 内/外侧共若干射线，比例 0.3/0.75/0.82/0.52/0.22，距离上限 24，`ai/searching/vision/NpcSearchVision.java:28-34`）；`NpcSearchScore` 是分数制获取机制——阈值 + 近/中/远分档增益 + 被遮挡衰减 + 空闲按 tick 衰减（`ai/searching/score/NpcSearchScore.java:17-76`）。目标能否维持由分数说话（NearestAttackableTargetGoal.java:71-72）。

**战斗入口事件化**：`AttackPrepareEventGoal`（`ai/goal/combat/AttackPrepareEventGoal.java:37-115`）每 tick 核算 距离/攻击间隔/目标可用/分数/可见，产出 `Readiness` 结构，再由 `NpcCombatRuntimeEvent.AttackPrepare` → `state_tree/NpcCombatStateTreeBridge.java:65` 广播状态树事件 `"entity.attack_prepare"`。即"可以打了"交给状态树和动画演出，Goal 不直接造成伤害。

**状态树是行为主体**：`cn/dbe/state_tree`（SCXML，见 `diagnostics/DbeRuntimeDiagnostics.java:16-45` 主动压制 commons-scxml 日志）。实体入世时由 `integration/state_tree/NpcStateTreeLifecycle.java:80-130` 读绑定、`StateTreeBridgeService.start`（:127）启动，离世时 stop + 清理管理器（:169-179）。玩家对话面是蓝图节点库：`cn/dbe/tools/blueprint/mgmc/nodes/**` 里 **122 个** `NodeHelper.setup("dbe_npc", ...)`，对应 lang 的 `node.npc.*`（445 条）——移动/转向/寻路/战斗/命中盒/动画通知/阵营/感知/纹理替换等全暴露为节点。

**朝向（Rotation）自成一系统**：三轴（ROOT/BODY/HEAD）× 连续/一次性请求，按 `owner + TTL` 仲裁（`ai/rotation/runtime/NpcRotationRuntime.java:59-72`）；`submitRootBodyContinuous`（:93）转根+身体、`submitFullOneShot`（:133）三轴一次到位、`cancelContinuous`（:151）按 owner 撤销；连续注视 owner 固定为 `continuous_look_goal`、TTL 4 tick（:70-71），无需每帧续期太频繁。算完的帧经版本号写回 entityData（`BlankNpcEntity.java:193`）供客户端插值。

**寻路**：`PathService` 统一入口，支持同步 `planAndFollow`、异步分片 `planAndFollowAsync` + `tickAsyncSearches`（`ai/navigation/PathService.java:81/182/511/589`）；`SlicedPathPlanner.updateSliced(state, maxIterations)` 让 A* 分帧跑（`ai/navigation/planning/SlicedPathPlanner.java:59-190`），配 `NavFilter/NavModifier/NavAgentProfile` 可插拔。跟随层有平滑、`StuckDetector`、`PathCrowdManager`、`NpcLocomotionDriver`（root motion 驱动）。**阵营**：`ai/faction/**` 提供 friendly/hostile/neutral 关系（lang `faction_relation.dbe_npc.*`）与编辑器服务。

## 3. 战斗间距（CombatSpacing）

规则：取双方 requiredDistance 的较小值（`control/combat_spacing/CombatSpacingResolver.java:24-37`），默认容差 0.05（:18），三态 AT_DISTANCE/TOO_CLOSE/TOO_FAR（:51）；默认攻击距离 1.5（`CombatSpacingData.java:19`），存在附件 `COMBAT_SPACING`（`registry/NpcAttachments.java:74`）。
执行方式不是"让 AI 走慢点"，而是**几何硬校正**：`mixin/CombatSpacingLivingTravelMixin.java:31` 在 `LivingEntity.travel` HEAD 记起点/目标/需求距离，TAIL 里 `correctApproach` 把穿圈位移截回圆周、`limitApproach` 删掉速度中朝目标的分量（:69-100）；对玩家走网络包通道做同样校正（`mixin/CombatSpacingPlayerPacketMixin.java:43/63`，服务端权威回滚）。root motion 驱动时按 `ignoreRootMotionSpacing` 让位（:44-48）。客户端通过 `S2CCombatSpacingSnapshotPayload` → `CombatSpacingRemoteState` 只做镜像（`CombatSpacingService.java:57-81`）。

## 4. 网络（109 java / 313 class）

双注册点：引擎 `cn/dbe/network/DbePayloadRegister.java:58-101` 分 7 个域（animation/visual_effect/particle/physics/gas/entity/package），含 **configuration 阶段**包同步（`PackSendingTask`，:103-105）；NPC 侧 `NpcNetworkPayloads.java` 14 个域（:124 item、:126 editor、:154 preset、:161 rts_integration、:166 npc_ui、:172 camera、:177 movement、:179 combat_spacing、:181 state_tree_editor、:214 animation_editor、:218 action_runtime、:222 state_tree_runtime、:229 search_debug），共 95 条 payload（58 上行 / 37 下行；C2S 56、S2C 33）。

形态分两类：
- **编辑器 = RPC + 结果回包**：`C2SOpenNpcBasicEditor → S2COpenNpcBasicEditor`、`C2SUpdateNpcBasicSettings`、state_tree/animation_graph 的 create/copy/rename/save/rollback 全套。
- **运行期 = 小快照推送**：`S2CCombatSpacingSnapshot`、`CameraControlSyncPayload`、`S2CStartPrecisionMovement`、`S2CSetVanillaPlayerJumpSuppressed/LeftClickSuppressed/BlockOutlineSuppressed`、`S2CPerformCurrentPlayerJump`。

**权威性**：位置、朝向、间距、相机全部服务端算。相机在 `camera/CameraControlService.java:33/100/232` 维护 per-player `version + CameraControlState`（含 directionLocked/targetLocked/actionFacing/shoulderView/fov/offset）再 publish，客户端 `CameraController` 只渲染。**预测**很克制：`control/movement/PrecisionMovement.java` 的 `startClientMovement/updateClientMovements` + `S2CStartPrecisionMovementPayload` 做客户端插值，服务端 `applyMovement` 覆盖。注意 `cn/dbe/sync` 只有 4 个类（`SyncData/IntSyncData/Syncer/SyncerType`），是给 ModelIndex 这类类型化同步复用的轻框架（`integration/state_tree/NpcStateTreeLifecycle.java:256-258`），**不是**通用实体同步层，别按 UntrackedEntity 的思路去读。

## 5. 编辑器与数据

物品（`cn/dbe/item/npc|player`，lang 7 条）：NPC 创建魔杖 `NpcCreatorWandItem.java:44-67` → `BlankNpcSpawnService.create`（`entity/spawn/BlankNpcSpawnService.java:71-75`，自动绑默认状态树 :96-110）；NPC 复制魔杖 `NpcCopyWandItem.java:124` → `S2COpenNpcCopyWandScreenPayload` + 模板列表；玩家编辑魔杖、模型切换魔杖、铁战锤。

服务端 `server/editor/*`：`NpcBasicEditorService`（openEditor :73 / handle :220 / switchNpcModel / handleDelete）、`NpcUiEditorService`、`NpcBindingEditorService`、`NpcFactionEditorService`、`PlayerBasicEditorService`、`ModelEquipmentBindingAuthoringService`。权限统一 `DbeEditorPermissions.java:17-21`：单人未开放 **或** OP 2 级。

存储走引擎 `cn/dbe/tools/storage`：`NpcTemplateStorage`（`tools/storage/npc/NpcTemplateStorage.java:59-64`，`preset.json` + 实体 NBT）基于 `LocalBoardStorage` 做 **draft → commit/discard/stageDelete** 事务（:186/212/226/240），根目录来自 `LocalPackRoots` + `LocalPackArchiveBackend`，可同时落存档与整合包。业务层 `server/preset/NpcLocalFileService.java` 负责列表/存/读/复制/删除与"光标瞄准的 NPC"。

界面 = LDLib2 + `.lss`：13 个样式文件（`jar/assets/dbe_npc/lss/*.lss`），源码里以 `ResourceLocation("dbe_npc","lss/xxx.lss")` 引用（如 `ui/npc/NpcEditorViewsKt.java:22-24`），编辑器视图在 `cn/dbe/ui/**`（animation_editor 237 文件、blueprint 91、workspace 25、npc 18）。模块自身只有一个真容器界面：NPC 装备菜单（`entity/inventory/NpcEquipmentMenu.java:49-58`，9 段 slot 区间），其余编辑器都是"假屏幕 + 网络请求"。可编辑字段见 `network/ui/NpcEditableSettingsPayload.java:30-45`（名称/生命/视野 FOV 与范围/速度/碰撞宽高/攻击伤害-间隔-范围/阵营/状态树绑定/当前模型），并带 `validated()` 二次校验（:225）。

## 6. 能力/技能

模块对 `cn/dbe/gas` 的硬依赖极薄（只 `HitboxWindowClientMirror`、`HitboxDamageFieldContext`）——技能由状态树节点触发，实际执行在 gas/action 运行时：`play_action`、`attack_hitbox_check`、`defense_hitbox_check`、`damage_task_hitbox_targets`、`open/sample/close_task_hitbox_window`、`apply_direct_damage`、`apply_action_hit_stop`、`combat_try_melee_attack` 等。

命令面（注意别只看 lang）：`/dbe_npc save|load [id]`（`command/NpcLocalFileCommand.java:37/43`，权限 2）、`/state_tree editor <id>`（`command/StateTreeEditorCommand.java:27-33`）、`/spark ability play|give|activate`（`gas/command/AbilityCommandHandler.java:60-62`，挂在 `/spark` 根，`tools/command/DbeCommandRegister.java:36-63`）、`/spark client particle ...`。`command.dbe_npc.*` 的 18 条 lang 文案（ability.granted/activated/activation_rejected/invalid_parameter/type_missing、skill.play.success/no_target/unknown、local_file.loaded、particle.*）**由 `/spark` 下的处理器使用**，不能据此推断存在 `/dbe_npc ability`。

## 7. 外部集成

- **mgmc（可选，[0.7.0,) AFTER）**：节点库（122 个节点）+ 组节点编辑器改造。9 条 mgmc mixin 全部经 `mixin/DbeNpcMixinConfig.java:13-30` 做**类存在性守卫**；`MgmcBlueprintManagerMixin.java:22-50` 放行 `spark_graphs/` 蓝图路径并做 `..`/`//`/冒号/通配符校验。蓝图文件落 `<world>/mgmc_blueprints/spark_graphs/<ns>/*.json`。
- **LDLib2**：只做 UI/lss；额外补输入法兼容——`mixin/client/Ldlib2ImBlockerFocusMixin.java` 监听 `addClass/removeClass("__focused__")` 与 `setVisible/setActive` 通知 `ImBlockerCompat`，另有 `ScreenImBlockerFocusMixin`（中文输入法遮挡窗口的老问题）。
- **Molang**：mods.toml credits "TartaricAcid & TomatoPuddin for Molang support"；实现位于引擎粒子模块（`cn/dbe/effect/particle/client/ParticleMolangContext.java` 等约 20 个文件），与 NPC 行为脚本无关。
- **其他**：shouldersurfing（相机 mixin + Bridge/LockPlugin）、方块描边抑制（`S2CSetPlayerBlockOutlineSuppressedPayload` + `LevelRendererBlockOutlineSuppressionMixin`）、玩家 vanilla 跳跃/左键抑制、RTS 风格放置（`integration/rts`：客户端幽灵预览 + 拖拽/滚轮旋转，服务端 `RtsNpcPlacementService.place/manage` :45/116 做相机视野范围校验）。"Spark" 是 DBE 自家的节点图/编辑器品牌（`tools/editor/SparkEditor.java`、`spark_editor.lss`、`node.sparkcore.*`），非外部 mod。

## 8. 值得学的 5 条做法

1. **空实体 + 附件数据 + 状态树**三层分离：`BlankNpcEntity` 不写业务，行为配置全在 `NpcData` 的七个可序列化子配置里，改行为不动实体类。
2. **朝向请求仲裁器**：把"谁控制朝向"变成显式资源（owner + TTL + 三轴 + 连续/一次性），根治多个 AI 抢朝向的抖动；并用版本号 + 前后帧同步解决客户端插值。
3. **战斗间距做在运动学末端**：mixin 在 `LivingEntity.travel` 与玩家移动包两端做几何校正，对玩家/root motion/非 AI 移动一体生效，且服务端权威、客户端只镜像。
4. **可选依赖用 MixinConfigPlugin 守卫**（`DbeNpcMixinConfig.java:13-30`），类不在就不应用，不需要 try/catch 兜底。
5. **本地文件事务化**：`writeDraft → commit/discard/stageDelete` + `operations.jsonl` 日志（`NpcTemplateStorage`），编辑器随便改也不会写坏线上模板。

## 9. 两个坑

1. **同方法 HEAD 记录 + TAIL 校正的 mixin 很脆**：`CombatSpacingLivingTravelMixin` 用 `@Unique` 字段跨注入传状态，并在 TAIL 再调 `self.move()`/改 deltaMovement；任何别的 mod 也在 `travel` 里位移或改速度都会互相覆盖；对玩家在 `handleMovePlayer` 里改坐标还要自己设 epsilon 阈值避免与反作弊/其他校验打架（`CombatSpacingPlayerPacketMixin.java:88-96`）。
2. **反编译工程里"历史残留"极易误读**：`cn/dbe/npc/state_tree/*` 与 `cn/dbe/npc/integration/state_tree/*` 是同名双份（`NpcCommonStateTreeBridge` 分别 722/747 行），事件只注册 `integration` 版（`event/NpcEventListeners.java:12-20`），旧包仍被引用一次（:20）；同理 `state_tree`（4 个类）与 `integration/state_tree`（9 个类）并存，是两代实现。此外 lang 前缀 `command.dbe_npc.*` 被 `/spark` 命令使用——只看语言文件会把命令面推错。

### 4.F 特效 + UI 编辑器 + 工具链（blueprint/storage/debug）

# F — `cn/dbe/effect` / `ui` / `tools` / `input_mapping` / `pack`

反编译源规模：`effect` 211 java / 29927 行，`ui` 412 java / 172679 行，`tools` 357 java / 95842 行，`input_mapping` 20 java / 5550 行，`pack` 37 java / 7738 行。外部依赖（`META-INF/neoforge.mods.toml:108-110`）：`ldlib2[2.2.36.a,)`、`mgmc[0.7.0,)`、kotlinforforge——UI 与蓝图两块都是"站在别人框架上做业务"，本仓库基本没有自研控件库/节点编辑器内核。

## 1. effect/：粒子=数据驱动，其余是可视化调试

**粒子（366 class）是 Bedrock/Snowstorm 格式的再实现**，与 ParticleStorm 同一路数：组件键直接用贝德里克命名空间，`ParticleComponentRegistry.java:62-91` 静态注册 30 个 `minecraft:emitter_rate_instant` / `particle_appearance_billboard` / `emitter_shape_disc`… 反序列化函数；`ParticleEffectDefinition`（`common/data/ParticleEffectDefinition.java:15-22`）聚合 description + emitterPreset + particlePreset + `Map<String,ParticleCurve>` + `Map<String,List<EventNode>>`。表达式层不是自研：`molang/MochaEngine.java` 是 Mocha（Molang）引擎的移植/内嵌（69 个类，lexer/parser/AST/runtime/binding），有 `prepareEval`/`compile` 与反射绑定。
与 ParticleStorm 的差异在"运行时外壳"：(a) 实例化——`ParticleEmitterManager.java:29-32` 用 `UUID→emitter`、`UUID→group`、pendingAdd/pendingRemove 队列管理，`ParticleEffectGroupLayout.java:18-38` 从 groupId 派生确定性 member/child UUID 与偏移，可跨端复现；(b) 网络——`network/` 7 个 payload（play/stop/stopEmitting/transform…）让服务端也能 spawn；(c) 事件节点 `EventExecutor.java:108-197` 支持 PARTICLE_EFFECT / SOUND_EFFECT / EXPRESSION / SEQUENCE / RANDOMIZE / EMITTER_BOUND，可嵌套点火；(d) 发光/泛光管线 `ParticleGlowPipeline.java:85-107`（HalfFloatRenderTarget × bloom profile、最多 16 组 screen light，配 `particle_glow_{copy,blur,screen_light}` 三个 shader 做 mask→blur→深度重建补光）；(e) 与动画通知联动 `AnimationNotifyParticleBridge.java:61`（notify 事件里 spawn 粒子）。另有两个原生 `Particle` 子类（`SpaceWarpParticle`、`AnimatableShadowParticle`）走 `ParticleRenderTypeFactory.distort()`。

**自定义 shader** 共 5 个，注册在 `client/DbeShaders.java:102-117`：`distort`（球面波驱动的屏幕 UV 扭曲，被 `SpaceWarpParticle` 用作 RenderType）、`white_trail`（拖尾）、`particle_glow_*`（三段泛光）。

**拖尾与 Iris 兼容**是最有技术含量的一块：`TrailRenderer` 只维护 mesh 池并采集骨骼/刀刃轨迹，真正的绘制被搬到 `renderLevel` 的 RETURN 之后独立 pass（`mixin/LateTrailRendererMixin.java:32-59`：手动 bind 主 RT、重设 projection/modelview、`finally` 里还原）。配套两个小设计：`LateTrailPassContext.java:6` 用 ThreadLocal 计数表达"当前在 late pass 内"；`mixin/compat/iris/IrisShaderInstanceMixin.java` 对 `net.minecraft.client.renderer.ShaderInstance` 打 `@Pseudo + remap=false + priority=900`，注入 `iris$shouldSkipThis()` 强制白名单 + `apply` TAIL 处重绑主 RT，`require=0` 保证没装 Iris 时静默失效。

其余子包是"给上面三项做可视化"：`visual/{trail,ik,root_motion,shape,warp}` 全是 debug renderer（IK 求解、根运动轨迹、warp 目标），统一实现 `VisualEffectRenderer`（tick/physTick/render，构造即自注册，`visual/VisualEffectRenderer.java:20-30`）；`sound/` 做"会移动的音源"——`SoundEngineMixin.java:49/82/91` 在 `tickNonPaused`/`calculatePitch`/`calculateVolume` 注入，让 `SpreadingSoundInstance` 的位置/音量/音高每帧由 `ISoundSpreader` 供给，`OggVorbisFormatValidator.java` 则在 pack 侧预检 ogg 头（扫描上限 64KB），避免整个声音引擎因坏文件崩掉。

## 2. ui/（412）：LDLib2 组件 + DBE 的 "Typed Views" 壳

分工可以从 `lss` 注释和代码两头看出。样式表 13 个（`assets/dbe_npc/lss/*.lss`，共 4677 行），`animation_editor.lss:1` 第一行写明"Specialized stage/lane drawing remains coarse; ordinary chrome is LDLib2-owned"。

- **LDLib2 负责**：控件（`UIElement/Label/Button/TextField/ScrollerView/SplitView/Dialog`）、事件（`UIEvent`）、布局与样式引擎（`UI.of` + `StylesheetManager`）、窗口与编辑器骨架（`com.lowdragmc.lowdraglib2.editor.ui.Editor/View/ViewContainer/EditorWindow/EditorLayoutStore`）、以及测试框架（`uitest.UIScenario`）。引用计数：`lowdraglib2.*` 出现 666 次。
- **DBE 负责**：把每个编辑器装配成 `SparkEditor extends Editor`（`tools/editor/SparkEditor.java:33-34`），提供 `useFixedTwoPaneLayout/useFixedThreePaneLayout`（:39/:64，把面板钉死并把多余 tab 头隐藏）、只保留 scale 的外观设置（:100-101）；再用 `*ViewsKt` 里的 builder 手写控件树，例如 `ui/animation_editor/AnimationEditorTypedViewsKt.java:33-44`：`root.addLocalStylesheet(spark_editor.lss/animation_editor.lss/spark_dialog.lss)` + `UI.of(root, ldlib2:lss/modern.lss)`，并提供 `element/named/label/button` 等 helper 与 `addClass()` 语义化类名。即"LDLib2 出引擎，DBE 出 pipline + 主题"。

**打开方式**：6 个编辑器各持有一个 `WINDOW_ID`（`ui/animation_editor/AnimationEditor.java:201`、`ui/blueprint/state_tree/StateTreeEditor.java:77` 等），经 `EditorWindow.open(WINDOW_ID, supplier)` 复用窗口/布局持久化；入口是 `/spark …` 命令（`tools/command/DbeCommandRegister.java:37-65`，动画图另有 `/spark graph`）→ `*ClientDriver` 调 `mc.setScreen(…)`（如 `ui/animation_editor/AnimationEditorClientDriver.java:91`）。**Screen 是双轨的**：19 个新壳 `extends ModularUIScreen`（`AnimationEditorShellScreen.java:34-35`），另有 10 个老式 `extends Screen` 仍在用，`CaptureParentScreen` 在 4 个包各写一份——迁移做到一半的状态。

**组织**：`animation_editor` 237（最大，编辑器+文档模型 `AnimationEditorDocument.java` 12775 行）、`blueprint` 91、`workspace` 25（`DbeWorkspaceEditor` 统一导航/资产树外壳）、`npc` 18、`action` 11、`input_mapping` 11、`reaction` 5、`tags` 4。命名后缀极规整：View 37、Screen 32、State 23、Popup 18、Layout 14——"状态对象 + 渲染函数 + View 组装"的三段式。

## 3. tools/（357）

- **blueprint（149）**：`ltd.opens.mg.mc`（MaingraphforMC）的**扩展包**，不是自研图。证据：`tools/blueprint/mgmc/nodes/NpcDataNodes.java:69+` 用 `NodeHelper.setup("dbe_npc","get_npc_basic_data","node.npc.…").category().color().input()` + `execute(JsonObject,NodeContext)/getValue(JsonObject,portId,NodeContext)` 注册节点；`MgmcBlueprintNodeBootstrap.java:32-52` 按域批量 `register()`（npc/player/world/camera/combat/state_tree/animation/action）；`DbeBlueprintBootstrap.java:29-42` 更是 `Class.forName` 探测 MGMC，未装则整块降级。图数据是 MGMC 的 JSON。
- **和 animation_graph 的关系**：**两套图，不同内核**。`animation_graph`（800 java）是 DBE 自己的"动画并行图/状态机"引擎——`GraphNodeType.SOURCE/BLEND/MODIFIER/OUTPUT/SUBGRAPH`、`ParallelGraphDefinition`、`StateMachineDefinition/TransitionDefinition/BlendSpaceDefinition`、`GraphRegistry`、`execution/GraphCommand*`、`serialization/SparkGraphAssetCodec`；全仓只有 1 个文件里面出现 mgmc 引用（`animation_graph/command/AnimationGraphMgmcCommand.java:20-21`）。两者的接缝是"用蓝图节点当动画图的遥控器/入口"：`tools/blueprint/mgmc/nodes/animation/BlueprintAnimationGraphNodes.java`（set_animation_graph_parameter / play_animation / start_blade_trail）、`tools/blueprint/animation_graph/NpcAnimationGraphAuthoringService.java`（在蓝图里 createOrOpen 动画图，蓝图名前缀 `spark_graphs/`）、以及 `BlueprintStateTreeScriptExecutor`（状态机脚本节点回落蓝图运行时执行）。所以：**同构但不同框架，靠节点/命令做桥**（是否共享同一份节点渲染代码：未确认）。
- **storage（75）**：作者侧持久化层，解决"编辑器写哪里、怎么同步、怎么回滚"。`core/base` 定义 LocalStorageRef/FileSet/FileKind，`core/board` 是 Board 抽象（`LocalBoardStorage/Adapter/Backend/ActionTable`），`core/action` 是文件级 journal（`LocalFileStore`/`LocalFileJournalEntry`/`LocalFileOperation`），`core/save` 是保存决策流，`core/sync` 是变更上传。根目录可被 system property 覆盖（`root/DbeStorageRoots.java:23` 的 `dbe_npc.configRoot`，默认 `FMLPaths.CONFIGDIR`）。域适配器按业务铺开：pack(17)、state_tree(7)、animation_graph(4)、trigger(4)、weapon(3)…，还有 `PackLegacyAnimationOverlayMigrator` 这类"老格式迁移并自动备份"。
- **debug（68）** = `mcp`(22) + `taint`(45)：一个**跑在游戏进程里的 MCP server** + 一套**运行时探针**。`mcp/McpHandler.java:50-66` 手写 JSON-RPC（Initialize/Tools/Resources/Roots 全套 capability），宿主是 Netty（`animation_graph/debug/server/NettyDebugServer.java` 同时提供动画图 protobuf 帧数据与 MCP 入口）。taint 用 ByteBuddy attach 自身（`taint/TaintAgent.java:59-60,99`）对指定"类名/方法名通配 + 条件表达式"重定义已加载类，采样调用（`recordInvocation`），再由 `TaintAnalyzer.java:385-390` 做跨线程写、值震荡、高频变更三类异常检测，输出按 tick 的时间线与冲突报告（`AnomalyType.java:14-17`）。`taint/TaintMcpTools.java` 把 taintTrace/taintReport 等挂成 MCP 工具。

## 4. input_mapping/（20）：三层

- **asset**：`InputMappingAsset`（schemaVersion + bindings + combinations，`asset/InputMappingAsset.java:25-33`）；`InputMappingBinding` 是"设备(KEYBOARD/MOUSE_BUTTON/MOUSE_WHEEL)+keyCode+modifiers+trigger(PRESS/RELEASE/TAP/HOLD)+holdSeconds → outputTag"（:24-36）；`InputTagCombinationRule` 是连招/组合键（inputTags、ordered、maxIntervalSeconds、requirePreviousHeld、cancelTags、priority、outputTag，:30-42）；配套 `InputMappingCodec/Validator/TagReferenceScan`（扫描 tag 引用完整性，无 tag 系统则报错）。
- **client**：`InputMappingClientBridge.java:63-135` 订阅 `InputEvent.Key`/`MouseButton.Pre`/`MouseScrollingEvent`/`ClientTickEvent.Post`，把物理事件喂给引擎。
- **runtime**：`InputMappingRuntime` + `InputMappingTriggerEngine`（时序语义、hold 判定）+ `InputMappingTagCombinationEngine`（`record(rawTag,nanos)`→`tick(nanos)` 结算，带 cancel/priority/consume）。
- **用途**：把物理输入归一成 GameplayTag，作为状态树/动画图/动作系统的统一输入（上行经 `action/runtime/sync/C2SActionMappedInputPayload`）。美术/策划侧在 `ui/input_mapping`（编辑器 + `input_editor.lss`）里可视化配表。

## 5. pack/（37）

自研"资源包分发/加载"体系，不是 vanilla resource pack 包装。`PackLoader.java`（:99 initialize → :113 readPackageGraph → :204 readPackageContent）分两遍读：先建依赖图（`graph/PackGraph.java`，节点 `PackDefinition`，边按 `DependencyType` 分 HARD/SOFT/OVERRIDE/CONFLICT，`graph/DependencyType.java:36-39`），再按 `resolveLoadOrder` 拓扑序喂给各 `PackModule`。模块注册是事件式的（`pack/event/PackReaderRegistrationEvent` + `registry/PackModuleRegistry.java:56-70`，15 个模块：model/animation/texture/particle/sound/recipe/lang/dictionary/parallel_graph/variable/ik_constraint…），每个模块声明自己的读取模式（`PackReadMode`：SERVER_TO_CLIENT / LOCAL_ONLY / CLIENT_LOCAL_ONLY）与 `onStart/read/onFinish` 生命周期。副作用覆盖 vanilla 资源的地方靠 mixin：`mixin/PackClientLanguageMixin.java` 给 `ClientLanguage` 塞 `dbe$extraStorage/dbe$componentStorage`，劫持 `has/getOrDefault/getComponent`，使 pack 里的 lang 与 Component 不需要重载资源包即可生效。同步：`sync/PackSendingTask.java:31-37` 实现 NeoForge `ConfigurationTask`，在配置阶段把包定义推给客户端（`PackSyncPayload`），客户端 `PackRemoteSnapshot` 做本地/远端双源合并；`PackLoaderApplier.java:34-45` 把世界目录写进 `spark.level.root`、世界内 `spark_engine/` 写进 `spark.overlay.root`（编辑器只改 overlay，不动原始包）。

## 6. 值得学的 5 条

1. **样式外置 + 语义类名**：UI 结构用 Kotlin-style builder（`element/label/button(id, classes)`）搭，视觉全在 `.lss`（4677 行、可在资源包里热改），`modern.lss` 做基线、自家 lss 只覆盖差异。UI 迭代不必编译。
2. **UI 也能跑自动化用例**：借 LDLib2 的 `uitest`，10 个 `*GalleryScenario`（`ui/animation_editor/uitest/AnimationEditorShellGalleryScenario.java:96-100` 以 `@LDLRegisterClient(registry="ldlib2:ui_scenario", environment=DEV_ONLY)` 注册），用 `ScenarioBuilder` 注入 fixture（临时 pack root、伪造 documentHost）后脚本化点选断言——GUI 模块有了回归测试与"画廊"。
3. **把 AI/外部工具接进运行时**：in-game MCP server（`tools/debug/mcp`）+ Netty 远程调试 + `animation_graph/debug/{DebugEventBus,FrameDebugData}` 事件化采样点，AI 直接读动画图每帧状态，不需要读日志猜。
4. **ByteBuddy 自身 attach 做"按需探针"**：`TaintAgent.startTrace(类通配, 方法通配, 条件, 持续 tick)` 才注入，到期移除 transformer；把"日志/断点"变成可编排的短时观测，而不是常驻 instrumentation。
5. **模块化 pack reader + 依赖图 + 配置期同步**：一种资源一个 module、依赖语义分四档、世界目录/overlay 分离，且"本地可改"（editor 写 overlay）与"服务端权威"（ConfigurationTask 推送）并存；配套一个轻量格式校验（`OggVorbisFormatValidator`）把脏资产挡在加载前。

## 7. 两个坑

1. **依赖图只排序、不查环**：`PackGraph.resolveLoadOrder` 是普通 DFS 后序（`graph/PackGraph.java:69-77`，递归函数 :82-127），`visited.add` 在递归**之后**；HARD 缺失、CONFLICT 命中才抛异常，SOFT 缺失仅 warn。若两个包互相 HARD 依赖（或 OVERRIDE 自指），`visited` 拦不住，会**无限递归直至 StackOverflowError**，而不是一句"检测到依赖环 A↔B"。同时 `originNodes` 是 `LinkedHashSet`/`originNodes.values()`，加载顺序还隐含取决于遍历顺序。（未确认上游是否有环校验：`PackLoader` 与 `tools/storage/pack` 中未见。）
2. **"渲染管线 hack"要写进资产约定，否则后患**：`white_trail.fsh` 里为了绕开"图集是不透明灰度遮罩"写了 luminance→alpha 的降级分支，并把不透明度硬夹到 0.85，注释明说"independent of shader-pack entity rules"；`particle_glow_screen_light.fsh` 的光源上限 16 是硬编码在 shader 数组长度里的；`ParticleGlowPipeline` 又是一整套 static 状态（静态 target、`levelIdentity`、`fallbackReason`）。这类"暗约定"散在 shader/静态字段里而没有落到 pack 校验或组件 schema 上，换一批美术资产就会重现"整条拖尾变实心矩形"，且与光影/多世界/多实例同存时很难定位。编辑器侧同类问题：`AnimationGraphAssetSidebar.java` 22775 行、`AnimationEditorDocument.java` 12775 行、`AnimationStateMachineEditorScreen.java` 7071 行的 God class 与新老 Screen 双轨（19 个 `ModularUIScreen` + 10 个旧 `Screen`、4 份 `CaptureParentScreen`）并存，是当前最大的维护成本。 

（`tools/command`、`tools/util`、`ui/action`、`ui/reaction`、`ui/tags` 为纯支撑：命令聚合、颜色/渲染类型/NBT 序列化助手、动作与战斗反应表格编辑器，未展开。）


---

## 5. 值得学的做法（跨子系统汇总）

1. **组合根集中 bootstrap**：引擎本体（DbeCore）保持空壳，由内容模块（DbeNpc）按依赖顺序拉起全部子系统（`DbeNpc.java:108-`），依赖方向清晰、便于拆包。
2. **编辑期/运行期双态建模**：动画图、状态树、蓝图三套系统都严格区分 `authoring`（编辑器数据）与 `runtime/execution`（游戏内实例），并用 `EditorMeta` 之类的附加元数据承载编辑器信息——这是"可编辑系统"的标准分层。
3. **图求值工程化**：双 pass（Serial 输出 + Evaluate 输出）+ 拓扑分层（扁平 `int[][]` 邻接表 + 入度 + 复用缓冲，`GraphLayerScheduler.java:43,119`）+ 层内并行 + 单节点层特快路径 + 启动时环检测。
4. **动画关键帧 → 事件 → 外部系统的解耦**（与 ParticleStorm 同一思路，但这里是自研引擎内建）。
5. **物理与游戏线程分离**：主线程只做"收集与提交"（activation/build box、dirty sections、任务队列），物理线程固定 `dt=1/60`、每 tick 3 子步（`PhysicsLevel.java:249,615-616`），结果经只读查询快照（`PhysicsQuerySnapshot` + 读写锁 + 龄期判断）暴露给渲染/逻辑。
6. **步进序号化**：`PhysicsLevelStepSequencer`（epoch + request/accept/complete + coalesced/stale/rejected 统计）用于定位"物理落后/丢步"——比朴素 accumulator 可观测得多。
7. **地形需求盒分层**：activation box（小、速度前瞻 0.25s）与 build box（大、前瞻 0.75s）分离，每帧限流（最多起 2 个 chunk 构建 / 24 次 section 变更）。
8. **按依赖门控 mixin**：用 `IMixinConfigPlugin` 在 `mgmc` 等可选依赖存在时才应用对应 mixin。
9. **数据驱动的能力/效果/目标/判定**（GAS：ability + effect + tag + target + hitbox + tasks + presets）。
10. **资源/语言规模化管理**：4759 条中文词条 + `.lss` 样式表外置，编辑器 UI 的文本与样式都不进代码。

## 6. 坑与风险（给"要不要自己造"的参考）

- **规模成本**：7149 个 class、63 条 mixin、19 条 AT、17 个内嵌库、2 套 natives —— 这是一个团队级长期工程的体量；个人项目复刻其**架构思想**可行，复刻其**实现**不现实。
- **Kotlin + KFF 的连带成本**：使用者必须装 KotlinForForge；反编译/调试时全是 Intrinsics 噪声（本报告已尽量剥离）。
- **AT 与注入原版内部的耦合**：`Camera.detached`、`KeyboardInput.calculateImpulse`、`GameRenderer.getFov`、`ClientLevel.tickingEntities`、`Entity.firstTick` 等一旦版更即返工；`model` 的 5 条第一人称 mixin 同理。
- **双 mod id / 版本号不一致**（文件名 1.1.0-SNAPSHOT vs toml 1.0.1009-SNAPSHOT）在分发与依赖解析时容易踩坑。
- **内嵌 Lua + SCXML + FreeMarker + ByteBuddy**：能力强大但攻击面/体积/许可面都变大（LuaJava、SCXML2 的许可证需自行核对）。
- **物理引擎与存档/多人一致性**：物理状态不进存档（按需重建）、只同步地形变更标记而非几何，改动物理参数时要意识到"重登/换端可能不同步"。

## 7. 对你自己项目的启示（修仙 / NPC / 战斗方向）

1. **能力系统直接对标 `gas/`**：你若要"功法/技能/异常状态/命中判定"分家，`ability + effect + tag + target + hitbox + tasks` 这六个概念就是成熟切分；其中 **hitbox 独立成包**（与物理/动画联动）比把判定写进技能里可维护得多。
2. **动画图 vs 状态机**：DBE 三套（动画图/状态树/蓝图）说明"动作编排"和"逻辑编排"应当分开；你的守潮/战斗若复杂度上来，先上**状态树**（202 class 的量级，比动画图小得多），动画图最后再考虑。
3. **受击反应表**（action 的 `reaction` + `.lss` 里的 `combat_reaction`）是"战斗手感"的关键落点——比在每个技能里硬编码硬直/击退要清晰。
4. **物理的性价比**：整包物理（独立的 60Hz 线程）能带来真实感，但你现有玩法（蜂群/殖民地）用**局部物理**（少量刚体 + 查询 API）就够，可直接借鉴它的"主线程准备 / 物理线程步进 / 只读快照"三段式。
5. **编辑器不要自己写 UI 框架**：DBE 自己写引擎却把 UI 交给 **LDLib2**（自研只留 `.lss` 样式与编辑器逻辑），这个分工值得照抄。

## 8. 复现与源码位置

- 反编译：`java -jar cfr.jar DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar --outputdir src --silent true --caseinsensitivefs true`
- 源码（反编译产物）：`Mod源码研究汇总\源码库\_参考仓库\DBE-1.1.0-neoforge-1.21.1\`（附 `_反编译来源说明.md`）
- 子系统分头精读的原始草稿：`%TEMP%` 之外的 `~/Downloads\_dbe\parts\`（6 份，已全文并入本报告第 4 章）
- 注意：本目录为**反编译产物**，仅供学习分析，勿再分发。
