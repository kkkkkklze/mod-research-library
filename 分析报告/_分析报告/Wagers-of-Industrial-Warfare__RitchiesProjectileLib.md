# Wagers-of-Industrial-Warfare/RitchiesProjectileLib 源码分析

## 1. 基本信息

- Mod 名 / mod_id：Ritchie's Projectile Lib / `ritchiesprojectilelib`；作者 rbasamoyai；版本 `2.1.2`（`gradle.properties`）
- 目标版本/加载器：**多加载器**——1.20.1 Forge 47.4.12 + Fabric 0.16.10，1.21.1 NeoForge 21.1.206 + Fabric（`versions/1.20.1/gradle.properties`、`versions/1.21.1/gradle.properties`）
- Gradle：**Stonecutter 0.7-alpha.10 + Architectury Loom 1.13 + architectury-plugin 3.4 + com.gradleup.shadow 8.3.5**（`stonecutter.gradle.kts`、`settings.gradle.kts`）；版本切换靠 `//? if >=1.21 { ... } //?} else { //?}` 源码预处理（如 `RitchiesProjectileLib.java:27`、`ChunkManager.java:12-21`）
- 许可证 MIT（forge/neoforge 的 mods.toml）
- 依赖：MixingExtras 0.4.1（`mixin_extras`）、Fabric 侧 Fabric API + **Porting-Lib（networking,utility,base）+ ForgeConfigApiPort**（均 `include` 内嵌）、Parchment mappings。它自身就是被依赖方（README 提供 `com.rbasamoyai:ritchiesprojectilelib:...-common/forge/fabric` 三种 artifact）

## 2. 源码规模与包结构

- 44 个 `.java`，1910 行（含三平台各 6-7 个 impl 类）
- 最大文件：`projectile_burst/ProjectileBurst.java`(174)、`chunkloading/ChunkManager.java`(149)、`effects/screen_shake/ModScreenShakeHandler.java`(109)、`RitchiesProjectileLib.java`(91)、`RPLScreenShakeHandlerClient.java`(73)、`config/RPLConfigs.java`(70)、`network/RPLNetwork.java`(63)
- common 包：`projectile_burst`、`chunkloading`、`effects.screen_shake`、`network`、`config`、`mixin`；平台包：`...forge` / `...neoforge` / `...fabric` 各含 EnvExecuteImpl、CameraModifier、*Client、主类与 `network.<platform>`

## 3. 入口与注册

common 侧 `RitchiesProjectileLib.java:15` 只是静态 facade（`MOD_ID`、`LOGGER`、`init()` 调 `RPLNetwork.init()`、`queueForceLoad`、`shakePlayerScreen`）。平台入口：

- NeoForge：`neoforge/.../RitchiesProjectileLibNeoForge.java:15` `@Mod(MOD_ID)`，构造注入 `IEventBus modBus`，`RPLConfigs.registerConfigs(mlContext.getActiveContainer()::registerConfig)`，`NeoForge.EVENT_BUS.addListener(this::onServerLevelTick)` → `LevelTickEvent.Post`
- Forge：`forge/.../RitchiesProjectileLibForge.java`
- Fabric：`fabric/.../RitchiesProjectileLibFabric.java:17` `ModInitializer`，用 `ServerPlayConnectionEvents.JOIN`、`ServerTickEvents.END_WORLD_TICK`、`ForgeConfigRegistry.INSTANCE.register`
- **无 DeferredRegister**（不添加内容），注册只有网络通道/配置/事件。数据存储走 `SavedData`：`RitchiesProjectileLib.java:37` 用 `level.getDataStorage().computeIfAbsent(ChunkManager.factory(), CHUNK_MANAGER_ID)`（1.20.1 分支为 `ChunkManager::load, ChunkManager::new` 两个方法引用）

## 4. 核心系统

**(a) 精确动作同步（tag 驱动）**：`src/main/java/rbasamoyai/ritchiesprojectilelib/RPLTags.java` 定义 `#ritchiesprojectilelib:precise_motion`（EntityType TagKey）。命中该 tag 的实体由 mixin 每 tick 额外发包。

**(b) ProjectileBurst 虚拟子弹**：`projectile_burst/ProjectileBurst.java`——一个实体用 `List<SubProjectile>`（record，double[3] displacement/velocity）表示上百颗子弹，`tick()` 内逐个 `clipAndDamage`（`level().clip` + `ProjectileUtil.getEntityHitResult`）并累加位移，命中即 `onSubProjectileHit` 后从链表移除；`getLifetime()`/`applyForces()`/`getSubProjectileWidth|Height()` 为抽象扩展点。渲染侧 `ProjectileBurstRenderer.java:16` 直接遍历子子弹并按 `partialTick` 插值平移。**用 1 个实体代替 N 个实体解决霰弹/破片性能问题**。

**(c) 分帧强制加载 ChunkManager**：`chunkloading/ChunkManager.java extends SavedData`，内部 `LongOpenHashSet chunks` + `LongArrayFIFOQueue queue` + `Long2IntOpenHashMap loaded`（fastutil）。每 tick 至少推进 `maxChunksLoadedEachTick` 个、总上限 `maxChunksForceLoaded`，用 `loadChunkNoGenerate()`（`:136`，`getChunkNow` → `ChunkStatus.EMPTY` → 若为 ProtoChunk 则移除 `TicketType.UNKNOWN` 票再取 FULL）避免触发地形生成；老化计数 -1/<0 表示"等待实体加载"，`isPositionEntityTicking` 后重置为 `DEFAULT_AGE`。

**(d) 屏幕震动**：`effects/screen_shake/ModScreenShakeHandler.java` 是**可扩展接口 + Impl 默认实现**（`delayedShakes` LinkedHashSet、`tick/applyEffects/clearEffects`），用 10 次子步的弹簧-阻尼积分（restitution 0.1/drag 0.2）算 yaw/pitch/roll 位移；`RPLScreenShakeHandlerClient.registerModScreenShakeHandler(ResourceLocation, handler)` 允许其它 mod 注册具名 handler（重复注册抛 IllegalStateException），默认 id 为 `ritchiesprojectilelib:shake_handler`。

**(e) 双通道网络抽象**：`network/RPLNetwork.java` 用 `Int2ObjectMap<Function<FriendlyByteBuf,? extends RootPacket>> ID_TO_CONSTRUCTOR` + `Object2IntMap<Class,...> TYPE_TO_ID` 手写包 id 映射，5 个方法用 architectury `@ExpectPlatform`（`sidedInit/sendToServer/sendToClientPlayer/sendToClientTracking/sendToClientAll`）委派给平台实现；`forge/.../network/forge/RPLNetworkImpl.java:23` 只用两个 Forge 包载体（`ForgeServerboundPacket` / `ForgeClientboundPacket`）包裹所有 `RootPacket`，`networkProtocolVersion(VERSION="3.0.0")` 做版本校验。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：见 4(e)。包类为 record（如 `ClientboundPreciseMotionSyncPacket.java:10`，手写 `FriendlyByteBuf` 构造与 `rootEncode`），`handle()` 内用 `EnvExecute.executeOnClient(() -> () -> RPLClientHandlers.syncPreciseMotion(this))` 做**安全侧判定**（避免 common 代码引用客户端类）。加入服务器时下发 `ClientboundCheckChannelVersionPacket(VERSION)`。
- **数据驱动**：唯一数据入口是实体类型 tag `precise_motion`；无 datapack 自定义内容。
- **配置**：`config/RPLConfigs.java` 静态单例 + `ModConfigSpec`（<1.21.1 由 stonecutter 替换成 `ForgeConfigSpec`，`:8-14`），4 项 server 配置（maxChunksForceLoaded=64、maxChunksLoadedEachTick=32、projectileChunkAge=3、entityLoadTimeout=10），Fabric 侧经 ForgeConfigApiPort 注册。
- **datagen**：无（build 脚本仅声明 `src/generated/resources` 源目录）。

## 6. Mixin

- 配置：`src/main/resources/ritchiesprojectilelib.mixins.json`（package `rbasamoyai.ritchiesprojectilelib.mixin`，mixins=[ServerEntityMixin]）；三个平台各有空 mixin 配置 `ritchiesprojectilelib-{fabric,forge}.mixins.json` 备用
- `src/main/java/rbasamoyai/ritchiesprojectilelib/mixin/ServerEntityMixin.java`：`@Mixin(ServerEntity.class)`，`@Shadow @Final private Entity entity`
  - `@Inject(method="sendChanges", at=@At("HEAD"))`：实体类型 match `RPLTags.PRECISE_MOTION` 时发 `ClientboundPreciseMotionSyncPacket`（含精确 vel/rot/onGround/lerpSteps=3）并把 `entity.hasImpulse = false`
  - 两个 `@WrapOperation(method="sendChanges", target="Ljava/util/function/Consumer;accept(Ljava/lang/Object;)V", ordinal=2/3)`（MixinExtras）：命中 tag 的实体**取消原版位置/速度包的发送**，避免双份同步
- `src/main/resources/ritchiesprojectilelib.accesswidener`（v2 named）：仅开放 `Projectile.<init>(EntityType, Level)` 供 `ProjectileBurst` 继承
- 无任何 @Redirect/Overwrite；平台 mixin 包为空

## 7. 值得学的 5 条具体做法

1. **Tag 驱动 + 取消原版包**：`RPLTags.PRECISE_MOTION` + `@WrapOperation` 拦截 `ServerEntity.sendChanges` 的两个 Consumer，实现"选择性替换同步协议"；`mixin/ServerEntityMixin.java:37-48`；适用于需要自定义网络同步节奏的实体。
2. **虚拟子弹幕（1 实体 N 子弹）**：`List<SubProjectile>` + 手动 clip/位移积分 + 独立 renderer 遍历；`projectile_burst/ProjectileBurst.java`；适用于霰弹、集束、破片等高频实体场景。
3. **分帧 chunk 加载队列 + SavedData 持久化**：FIFO 队列 + 每 tick 配额 + 老化淘汰，且 `loadChunkNoGenerate` 规避地形生成；`chunkloading/ChunkManager.java`；适用于远程炮击/导弹的区块需求。
4. **`@ExpectPlatform` + 单一 `RootPacket` 双载体**：平台只注册 2 个包，业务包用 id 表映射；`network/RPLNetwork.java` + 各平台 `RPLNetworkImpl`；适用于多加载器库的网络层，新增包无需改平台代码。
5. **Stonecutter 版本/平台条件源码**：`//? if >=1.21 {` 与 build.gradle.kts 里的 `stonecutter { replacements { ... ModConfigSpec → ForgeConfigSpec ... } }`（`build.gradle.kts:29`）；适用于 1.20.1↔1.21.1 双版本维护。

## 8. 公开 API

- 门面：`rbasamoyai.ritchiesprojectilelib.RitchiesProjectileLib`（`queueForceLoad(ServerLevel,int,int)`、`shakePlayerScreen(ServerPlayer[,ResourceLocation],ScreenShakeEffect)`、`onServerLevelTickEnd`、`resource(path)`、`CHUNK_MANAGER_ID`）
- 扩展基类：`projectile_burst.ProjectileBurst`（抽象：`getLifetime`、`applyForces`、`getSubProjectileWidth/Height`、`onSubProjectileHitEntity/Block`）与 `projectile_burst.ProjectileBurstRenderer`（`renderSubProjectile`）
- 客户端扩展：`effects.screen_shake.RPLScreenShakeHandlerClient.registerModScreenShakeHandler(id, handler)`，接口 `ModScreenShakeHandler`（`tick/addEffect/clearEffects/applyEffects`，`Impl` 的 `modifyScreenShake/getRestitution/getDrag/applyConstraints` 可覆写）
- 数据扩展点：EntityType tag `#ritchiesprojectilelib:precise_motion`
- 接入方式：Maven `https://maven.realrobotix.me/master/`（group `com.rbasamoyai`），依赖 `ritchiesprojectilelib-<ver>+mc.<mc>-<common|forge|fabric>-build.<n>`，`include` 内嵌 Porting-Lib/ForgeConfigApiPort 于 Fabric 产物（README "Depending on RPL"）
- 注：仓库快照缺 `fabric/src/main/resources/fabric.mod.json` 源文件（`fabric/build.gradle.kts:119` 对 `fabric.mod.json` 做占位符替换，源模板未包含在快照中），因此 fabric 侧 entrypoint 声明未能确认。
