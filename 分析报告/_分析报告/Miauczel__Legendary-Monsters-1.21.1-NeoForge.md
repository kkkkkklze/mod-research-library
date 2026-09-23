# Legendary Monsters 源码分析报告

## 1. 基本信息

- Mod 名：Legendary Monsters；mod_id：`legendary_monsters`；作者：Miauczel（`gradle.properties`）
- 目标：**MC 1.21.1 / NeoForge 21.1.219**（同你的目标版本，可直接抄）；Java 21；ModDevGradle `2.0.140`（`build.gradle`）
- 许可证：All Rights Reserved（`mod_license=All Rights Reserved`，仓库根另有 `TEMPLATE_LICENSE.txt`，说明基于 MDK 模板起步）
- 依赖：仅 JEI `19.27.0.340`（`jei_version`，仓库内未实际 compileOnly 引用，未确认用途）；无前置库、无 GeckoLib（**动画自己实现**）
- 资源情况：`src/main/resources` 只有 `META-INF/neoforge.mods.toml` + 5 个占位 `.txt`（tags/worldgen 示例），**assets（模型/贴图/动画/sounds.json/lang）不在本仓库**，是纯代码仓库
- 注意 `META-INF/neoforge.mods.toml` 里 `version="1.21.1"` 硬编码（未用 `${mod_version}`）、neoforge 依赖写 `versionRange="1.20.1,1.21.1"`；`LegendaryMonsters.prefix()` 用的是 `"legendarymonsters"` 而不是 `MOD_ID="legendary_monsters"`（命名空间不一致，属事实性隐患）

## 2. 源码规模与包结构

- 736 个 `.java`，**244,318 行**（实测 `find -print0 | xargs -0 cat | wc -l`），是本次三仓库中最大的
- 主要包（第 3 层）：`entity/client/Render` 65、`item/custom` 54、`entity/AnimatedMonster/Projectile` 50、`entity/client/Model` 49、`Particle/custom` 47、`entity/animations` 40、`entity/ProjectileEntityRenderer` 34、`effect/custom` 20、`entity/AnimatedMonster/IAnimatedBoss/TheObliterator/goals` 29
- 最大文件：`.../IAnimatedBoss/TheObliterator/TheObliteratorEntity.java` **6363 行**、`entity/animations/PosessedPaladinAnimations.java` 4023、`PossessedPaladinEntity.java` 3607、`CloudGolemAnimations.java` 3563、`Cloud_GolemEntity.java` 3436，另有 14 个 TheObliterator 动画类各 3000+ 行（`Animations/TheObliterator/*`）
- 主观评价：代码量集中在"每个 Boss 一个巨型实体类 + 每个动作一条硬编码关键帧"，可读性差但功能完整

## 3. 入口与注册

`src/main/java/net/miauczel/legendary_monsters/LegendaryMonsters.java`：`@Mod(MOD_ID)`，构造器拿到 `(IEventBus, ModContainer)`：

```java
proxy = FMLLoader.getDist().isClient() ? new ClientProxy() : new CommonProxy();
proxy.init(modEventBus);
NeoForge.EVENT_BUS.register(this);
ModArmorMaterials.ARMOR_MATERIALS.register(modEventBus);
modEventBus.addListener(LegendaryMonsters::setupMessages);
ModEntities.register(modEventBus); ModItems.register(...); ModEffects/ModSounds/ModBlocks/ModParticles/ModProcessors/ModBlockEntity/ModStructures.register(...);
modContainer.registerConfig(ModConfig.Type.COMMON, ModConfig.MOB_CONFIG_SPEC);
```

- 注册风格：每个 `ModXxx` 类持有 `DeferredRegister.create(BuiltInRegistries/Registries.X, MOD_ID)` 并暴露静态 `register(IEventBus)`（老式 Forge 习惯，非 `DeferredRegister.Blocks/Items` 新 API）。
- 侧隔离用 `CommonProxy / ClientProxy` 继承 + `FMLLoader.getDist()` 判断（`CommonProxy.getClientSidePlayer()` 返回 null 兜底），并有 `ClientModEvents` 静态内部类用 `@EventBusSubscriber(Dist.CLIENT)` 做客户端注册（约 90 个 `EntityRenderers.register`、4 个 `BlockEntityRenderers.register`、`ItemBlockRenderTypes.setRenderLayer`）。
- 客户端渲染注册集中在主类里（`LegendaryMonsters.ClientModEvents.onClientSetup`），极易冲突，不建议模仿组织方式。

## 4. 核心系统

1. **Boss 继承栈**（`entity/AnimatedMonster/OriginClasses/`，注意这些名字叫 `Ixxx` 的其实是**类**）：`IAnimatedMonster extends Monster` → `IAnimatedBoss extends IAnimatedMonster` → 具体 Boss（`TheObliteratorEntity`、`Cloud_GolemEntity`、`PossessedPaladinEntity`）；同级还有 `IAnimatedMob/IAnimatedMiniBoss/IAnimatedPathfinderMob/IAnimatedTamableMob/IHurtingPathfinderMob/INoRendererEntity/ModPowerableMob/AmbientEntity/AbstractFlameborn/AbstractChorusling`。
2. **战斗状态机（本仓库最值得学的部分）**：`OriginClasses/IAnimatedMonster.java:86-98, 429-459` 用同步数据 `ATTACK_STATE`（INT）+ `attackTicks/attackDelayTicks/attackCooldown` 表示"当前招式"；`setAttackState(int)` 里 `broadcastEntityEvent(this, (byte) -input)`，`handleEntityEvent(byte id)` 据 id 重置 `attackTicks/attackDelayTicks` 实现客户端同步。每个招式一个 Goal 类，构造函数统一传 7 个参数`(getattackstate, attackstate, attackendstate, attackMaxTick, attackSeeTick, attackrange, attackrangeMin)`——见 `IAnimatedBoss/TheObliterator/goals/ParryGoal.java:22-64`，`canUse()` 判 `getAttackState()==getattackstate && distance<range && >rangemin && getAttackDelayTicks()<=0`，`start()` 切状态，`canContinueToUse()` 判 `attackTicks < attackMaxTick`，`stop()` 切下一状态（`setAttackState(entity.gambitParry ? 59 : 57)`）。29 个 TheObliterator goal 全按此模板写。
3. **Boss 血量/伤害自定义**（`OriginClasses/IAnimatedBoss.java`）：不直接用 `LivingEntity.health`，而用 `float totalDamageTaken` + `getHealth() = max(0, getMaxHealth() - totalDamageTaken)`（行 302-307），从而支持单次伤害上限 `damageCap()`、受伤冷却 `hurtCD = HURT_COOLDOWN(30)`、伤害适应 `damageTimeFactor -= adaptationFactor()`、反作弊距离 `antiCheeseDistance()`（超距免伤，行 343-345）、`breakCheeseBlocks()` 拆玩家搭的方块；`totalDamageTaken` 用 `Float.floatToIntBits ^ 0x5F3759DF` 写进 NBT 的 `_td`（行 73-91）——防玩家改存档的加密式存法（作者自述语义未确认）。
4. **Boss 音乐/血条网络同步**：`IAnimatedBoss.tick()` 每 tick 在服务端 `LegendaryMonsters.sendMSGToAll(new PlayBossMusicMessage(this.getId(), true/false))`（行 146-153）；本地血条走 `util/LMBossInfoServer` + `CommonProxy.bossBarRenderTypes`（`Map<UUID,Integer>`），客户端渲染类型由 `MessageUpdateBossBar` 同步。
5. **"Java 硬编码关键帧"动画系统**：`entity/animations/*.java`（40 个文件）每个都手写原版 `AnimationDefinition.Builder.withLength(x).looping().addAnimation("part", new AnimationChannel(Targets.ROTATION, new Keyframe(0f, KeyframeAnimations.degreeVec(...), AnimationChannel.Interpolations.LINEAR), ...))`（`SkeletosaurusAnimations.java:11-30`），无 Blockbench 的 `.animation.json`；`entity/animations/replacer/` 放替换版本，`entity/client/ControlledAnim` 控制播放。
6. **特效实体（相机类）**：`entity/AnimatedMonster/Effect/CameraShakeEntity`、`DynamicCameraZoomEntity` 做成实体，配合 `mixin/CameraInvoker`（Accessor）直接改相机，是"用实体驱动镜头特效"的做法。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：NeoForge `RegisterPayloadHandlersEvent` + `registrar("1")`（`LegendaryMonsters.setupMessages`），6 个包：`MessageArmorKey`、`PlayBossMusicMessage`、`MessageUpdateBossBar`、`SkeloraptorRoarKeyMessage`、`SkeloraptorTailAttackMessage`、`AnnihilatorHelmetAbilityMessage`。payload 为 `record ... implements CustomPacketPayload` + `Type<>` + `StreamCodec.composite(...)`（`Message/MessageUpdateBossBar.java:19-26`，用 `UUIDUtil.STREAM_CODEC` 与 `ByteBufCodecs.INT`），handler 放 `Network/LMClientPayLoadHandler`、`LMServerPayLoadHandler`。发送封装为 `LegendaryMonsters.sendMSGToAll / sendNonLocal / sendMSGToServer`（内部 `PacketDistributor`）；另有 `queueServerWork(tick, Runnable)` + `ServerTickEvent.Post` 倒计时队列（`LegendaryMonsters.tick`）做延迟任务。
  - 事实性缺陷：`LMClientPayLoadHandler.handleUpdateBossBar` 在 `renderType == -1` 时调用 `proxy.removeBossBarRender(data.renderType())`（应传 uuid，`CommonProxy` 的 `removeBossBarRender` 参数类型也对不上）；大量 `context.handle(data)` 是手写错误用法——不要照抄该文件。
- 配置：`config/ModConfig.java` 两个 `ModConfigSpec`（`CommonConfig` + `MobConfig`，均注册为 `ModConfig.Type.COMMON`），键名直白（`AllowOvergrownColosussStun`、`DamageMultiplier`、`HealthMultiplier`、`canBossesTeleportBackToSpawn`），实体里直接读 `ModConfig.MOB_CONFIG.xxx.get()`。
- datagen：`datagen/DataGenerators.java` 注册 5 个 provider（`ModBlockTagGenerator`、`ModItemTagGenerator`、`ModBlockStatesProvider`、`ModModelProvider`、`ModWorldGenProvider`），输出到 `src/generated/resources`。
- 数据驱动（JSON）：无自定义 codec/数据包类型；`worldgen` 用 datagen + 少量手写 JSON。

## 6. Mixin

- 配置：`src/main/resources/legendary_monsters.mixins.json`，`package: net.miauczel.legendary_monsters.mixin`，`compatibilityLevel: JAVA_21`，**全部放在 `mixins`（无 `client` 段）**，7 个：`PlayerRespawnMixin`、`LivingEntityMixin`、`StructureTemplateMixin`、`StructureProcessorAccessor`、`IForgeItemMixin`、`CameraInvoker`、`PlayerMixin`。
- 代表性 hook：
  - `mixin/PlayerMixin.java`：`Player#hurt(DamageSource,F)Z` HEAD cancellable，带 `ModEffects.UNBREAKABLE` 时 `cir.setReturnValue(false)`。
  - `mixin/LivingEntityMixin.java`：同款效果拦截。
  - `mixin/CameraInvoker`：`@Invoker`/Accessor 直取 `Camera` 私有方法（配合相机特效实体）。
  - `mixin/StructureTemplateMixin` + `StructureProcessorAccessor`：改结构生成流程（自定义结构处理器）。
  - `IForgeItemMixin` 命名残留 1.20.1 Forge 迁移痕迹。

## 7. 值得学的 5 条具体做法

1. **"同步 int 状态 + 参数化 Goal" 写 Boss 招式机**：`IAnimatedMonster.setAttackState/getAttackState`（含 `broadcastEntityEvent`）+ `goals/ParryGoal.java` 的 7 参数构造模板。适用：任何多阶段 Boss/精英怪；比一个大 `tick()` 里 if 状态好扩展。
2. **把血量改为"累计伤害"而不是 LivingEntity.health**：`IAnimatedBoss.getHealth()/setHealth/addDamage`（行 280-317），天然支持单hit上限、破防期、伤害适应、Boss 返回出生点。适用：需要精细控制战斗节奏的 Boss。
3. **每 tick 只发一条布尔音乐包 + 客户端本地管理**：`IAnimatedBoss.tick()` 中 `sendMSGToAll(new PlayBossMusicMessage(id, canPlayMusic()))`。适用：Boss 音乐/演出同步（避免复杂状态同步）。
4. **延迟任务队列**：`LegendaryMonsters.queueServerWork(int ticks, Runnable)` + `ServerTickEvent.Post` 里倒计时执行（`workQueue` 用 `ConcurrentLinkedQueue` + `SimpleEntry<Runnable,Integer>`）。适用：招式起手→伤害判定之间隔 N tick 的"预告打击"。
5. **反向参考（不要学）**：单实体类 6000+ 行（`TheObliteratorEntity`）、30 个 goal 全塞在一个 `goals` 包、`ClientProxy/CommonProxy` 在 1.21.1 已被 `Dist` 隔离取代、`context.handle(data)` 误用——可作为"代码质量反例"留存。

## 8. 公开 API

无（闭源 ARR 内容模组，无对外 API 包，无插件/事件扩展点）。
