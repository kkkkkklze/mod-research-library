# lender544/Lionfish-API 源码分析报告

## 1. 基本信息
- Mod 名：LionfishAPI；mod_id：`lionfishapi`；作者：L_Ender（lender544，即 Cataclysm 灾变的作者）；version `2.6`
- 目标：**Minecraft 1.20.1 + Forge**（`mods.toml` loaderVersion `[47,)`，forge 依赖 `[47.0.34,)`），mappings `official`，Java 17
- Gradle：ModDevGradle `net.neoforged.gradle [6.0.18,6.2)` + `org.spongepowered.mixin 0.7.+`（`build.gradle:1-20`，`minecraft 'net.neoforged:forge:1.20.1-47.1.84'`）；`mixin { add sourceSets.main, "lionfishapi.refmap.json" }`，manifest 写 `MixinConfigs`
- 许可证：`mods.toml` 写 **"All rights reserved"**（仓库根为 MDK 的 `TEMPLATE_LICENSE.txt`，即未开源授权，仅可作参考）
- 编译依赖：JEI（compileOnly，`jei_version=15.2.0.22`）；运行时仅 neat。**它是别人的前置（灾变 Cataclysm），自身几乎不依赖别人**

## 2. 源码规模与包结构
- 41 个 `.java`，合计 **6248 行**；其中单文件 `client/model/render/Kobolediator_Animation.java` 就占 2138 行（一段示例动画数据，非框架代码）
- 包（第 3 层）：`com.github.L_Ender.lionfishapi`（根 3 个类）、`client/model`(2)+`client/model/AdvancedAnimations`(4)+`client/model/Animations`(4)+`client/model/tools`(7)+`client/model/container`(1)+`client/model/render`(1)、`client/{event,screen,util}`、`config/biome`(3)、`mixin`(1)+`mixin/client`(1)、`server/animation`(7)、`server/{entity,event,network}`(各 1-2)
- 除示例动画外最大文件：`client/model/tools/AdvancedModelBox.java`(513)、`Animations/IntermittentAnimation.java`(321)、`tools/AdvancedEntityModel.java`(310)、`tools/BasicModelPart.java`(305)、`Animations/ControlledAnimation.java`(275)、`Animations/ModelAnimator.java`(193)

## 3. 入口与注册
`src/main/java/com/github/L_Ender/lionfishapi/LionfishAPI.java`：无 DeferredRegister（纯 API/框架，不注册内容），核心是**静态频道 + 一个包**：
```java
static {
    NetworkRegistry.ChannelBuilder channel = NetworkRegistry.ChannelBuilder.named(new ResourceLocation(MODID, "main_channel"));
    channel = channel.clientAcceptedVersions(version::equals);      // PROTOCOL_VERSION = "1"
    NETWORK_WRAPPER = channel.serverAcceptedVersions(version::equals)
                             .networkProtocolVersion(() -> PROTOCOL_VERSION).simpleChannel();
}
private void setup(final FMLCommonSetupEvent event) {
    NETWORK_WRAPPER.registerMessage(packetsRegistered++, AnimationMessage.class,
            AnimationMessage::write, AnimationMessage::read, AnimationMessage.Handler::handle);
}
```
`PROXY = DistExecutor.runForDist(ClientProxy::new, CommonProxy::new)`（`:33`），并暴露 `sendMSGToServer/sendMSGToAll/sendNonLocal`（用 `player.connection.connection` 直发）。

## 4. 核心系统
1. **实体动画状态机（服务端）** `server/animation/`：`IAnimatedEntity`（`getAnimationTick/setAnimationTick/getAnimation/getAnimations()` + `NO_ANIMATION`）是外部 mod 唯一必须实现的接口；`Animation.create(duration)` + `setLooping`，`AnimationHandler.INSTANCE.updateAnimations(entity)` 每 tick 推进：tick==0 时 post `AnimationEvent.Start`（可取消）、未达 duration 时 `setAnimationTick(+1)` 并 post `AnimationEvent.Tick`、到点后非 loop 则重置为 `NO_ANIMATION`（`AnimationHandler.java:39-62`）。`AnimationAI` 为基类。
2. **动画网络的"索引同步"** `server/network/AnimationMessage`：只发 `(entityId, index)`，index = `ArrayUtils.indexOf(entity.getAnimations(), animation)`；客户端收到后用 `entity.getAnimations()[index]` 还原（`AnimationMessage.java:45-50`），**避免序列化 Animation 对象**，`index == -1` 表示停止。发送用 `PacketDistributor.TRACKING_ENTITY_AND_SELF`（`AnimationHandler.java:30`）。
3. **客户端模型框架** `client/model/tools/`：`AdvancedEntityModel<T>`（gegy1000 血统）在 `BasicEntityModel` 上加 `resetToDefaultPose/updateDefaultPose/faceTarget/chainSwing|chainWave|chainFlap/walk|flap|swing|bob/progressRotation(Prev)/progressPosition(Prev)` 与 `getAnyDescendantWithName(String)`（按 `boxName` 反射式查找骨骼，给关键帧动画用）；`AdvancedModelBox`(513 行) 保存 `defaultRotationX/Y/Z`、`defaultPositionX/Y/Z` 以支持"相对默认姿态"的叠加。
4. **双动画驱动**：(a) `Animations/ModelAnimator.java` 关键帧插值器——`startKeyframe(duration)/endKeyframe()` 用 `prevTransformMap`+`transformMap` 做 `inc = sin(tick*π/2)`、`dec = 1-inc` 的缓入缓出，并用 `Minecraft.getInstance().getFrameTime()` 做部分刻插值；(b) `AdvancedAnimations/AdvancedKeyframeAnimations.java` 复刻 1.19+ 原版 `KeyframeAnimations`，但骨骼用字符串名映射 `AdvancedModelBox`、关键帧数据是 `AdvancedAnimationDefinition`（便于 JSON/代码生成）。
5. **骨骼/腿 IK 与链式物理**：`server/animation/LegSolver.java`（来自 JurassiCraft 授权代码）按 yaw 计算 side/forward 偏移，对每只脚做 `VoxelShape.closestPointTo` 的地面高度采样 + `clamp(±range*scale)`，落地速度 0.25/格（`:61-98`），另带 `LegSolverQuadruped`；`client/model/tools/DynamicChain` + `ChainBuffer` 做尾巴/链节的物理跟随。
6. **Forge 事件扩展** `server/event/`：`StandOnFluidEvent`（可取消 → 水面站立/行走）、`EventGetFluidRenderType`（`Result.ALLOW` 覆盖流体 RenderType）、`AnimationEvent.Start/Tick`。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：仅 `NetworkHandler`-style 的 `main_channel` + `AnimationMessage`（entityId/index 两个 VarInt），`context.enqueueWork` 后 `setPacketHandled(true)`；无其他包。
- 数据驱动：无 codec/数据包驱动（动画定义在 Java 侧）。
- 配置：`config/biome/SpawnBiomeConfig` + `SpawnBiomeData` + `BiomeEntryType`，用 Gson（`registerTypeAdapter` 自定义 Deserializer）在 config 目录按 `ResourceLocation` 生成/读取每个生物的刷怪群系 JSON（`SpawnBiomeConfig.java:24-42`），供灾变等 mod 复用。
- datagen：仅 `data` run 配置与 `src/generated/resources` 声明，**实际未使用**。

## 6. Mixin
- 配置：`src/main/resources/lionfishapi.mixins.json`（`refmap: lionfishapi.refmap.json`，`mixins: [EntityMixin]`，`client: [client.ItemBlockRenderTypesMixin]`）
- `mixin/EntityMixin.java`：`@Mixin(Entity.class)`，`@ModifyVariable(method = "move", ordinal = 1, index = 3, name = "vec32", at = @At(value = "INVOKE_ASSIGN", target = "...Entity;collide(Lnet/minecraft/world/phys/Vec3;)Lnet/minecraft/world/phys/Vec3;"))`——在碰撞结算后检测 12 个采样点附近最高流体面（`Shapes.block().move(...)` + `Shapes.joinIsNotEmpty`），post `StandOnFluidEvent`，若被取消则 `fallDistance=0`、`setOnGround(true)` 并返回抬高后的 y（**这是"水上行走"的实现方式**）。
- `mixin/client/ItemBlockRenderTypesMixin.java`：`@Inject(at = TAIL, cancellable = true)` 到 `ItemBlockRenderTypes#getRenderLayer(FluidState)`，post `EventGetFluidRenderType`，`Result.ALLOW` 时 `cir.setReturnValue`。

## 7. 值得学的 5 条具体做法
1. **动画只同步索引不同步对象**：`AnimationMessage(entityId, index)` + `getAnimations()[index]` 还原，包体极小、天然对齐（`AnimationMessage.java:24-51`）。
2. **接口化的实体动画状态机**：`IAnimatedEntity` + `AnimationHandler.INSTANCE.updateAnimations(entity)` 一行接入，且提供 `AnimationEvent.Start` 可被外部取消（`AnimationHandler.java:39-62`）。
3. **关键帧插值器用 prev/current 双 Map 表达"上一帧姿态"**，inc/dec 用 `sin(tick*π/2)` 平滑，并以 `getFrameTime()` 做部分刻（`ModelAnimator.java:147-193`）。
4. **按名字查骨骼**（`getAnyDescendantWithName`）+ `AdvancedAnimationDefinition` 让动画数据与模型实现解耦（`AdvancedEntityModel.java:282-308`）。
5. **用 Mixin 打开一个可取消的 Forge 事件**（`StandOnFluidEvent`/`EventGetFluidRenderType`），把原版硬编码行为变成"事件 + `Result.ALLOW`"，是给其他 mod 提供能力的低成本做法（`mixin/EntityMixin.java`、`mixin/client/ItemBlockRenderTypesMixin.java`）。
6. **AT 而非 Mixin 来拿包私有成员**：`accesstransformer.cfg` 里把 `Item.renderProperties`、`StructureTemplatePool.templates/rawTemplates`、`Minecraft.timer`、`Timer.msPerTick`、`BiomeSource *`、`NoiseBasedChunkGenerator.settings`、`NodeEvaluator.entityWidth/Height/Depth`、`ChunkMap.getVisibleChunkIfPresent` 全部 public 化，比每个都写 Mixin 更省事。

## 8. 公开 API（本 mod 是前置库）
- 公共 API 包：`com.github.L_Ender.lionfishapi`（`LionfishAPI.NETWORK_WRAPPER/PROXY/sendMSGTo*`）、`server.animation`（`IAnimatedEntity`、`Animation`、`AnimationHandler`、`AnimationAI`、`LegSolver`、`LegSolverQuadruped`）、`server.event`（`AnimationEvent`、`StandOnFluidEvent`）、`client.model.tools`（`AdvancedEntityModel`、`AdvancedModelBox`、`BasicEntityModel`、`DynamicChain`、`LionfishModelRenderUtils`）、`client.model.Animations`（`ModelAnimator`、`IntermittentAnimation`、`ControlledAnimation`）、`client.model.AdvancedAnimations`（`AdvancedAnimationDefinition/Channel/Keyframe/KeyframeAnimations`）、`config.biome`（`SpawnBiomeConfig/SpawnBiomeData`）
- 扩展点接口：`IAnimatedEntity`（实体动画）、`IIntermittentEntity#getOffsetEntityState`（间歇性实体同步偏移）、`StandOnFluidEvent`（流体行走裁决）、`EventGetFluidRenderType`（流体渲染层裁决）
- 外部 mod 接入方式：把 LionfishAPI 作为依赖；实体 `implements IAnimatedEntity` 并在 `tick` 调 `AnimationHandler.INSTANCE.updateAnimations(this)`，服务端用 `AnimationHandler#sendAnimationMessage` 切换动画；客户端让模型继承 `AdvancedEntityModel`，在 `setupAnim` 中按 `entity.getAnimation()/getAnimationTick()` 驱动 `ModelAnimator` 或 `animate(...)`
- 消费方：仓库内未包含消费方代码，仅 `LionfishAPI.java:24` 留有被注释的 `com.github.L_Ender.cataclysm.init.ModStructures` 引用，可推断与灾变（Cataclysm）同作者配套使用；README 为 MDK 模板原文

## 关键词
实体动画状态机、索引式动画同步、ModelAnimator 关键帧、StandOnFluidEvent 水上行走、AdvancedModelBox 骨骼
