# Citadel 源码分析报告

> 分析对象：`源码库\_参考仓库\_bulk\Raguto__Citadel-1.21.1`（Raguto 的非官方 1.21.1 移植；本地是浅克隆，`git log` 只有 1 条 `cb24a15 Merge pull request #6 from Starior/master`，无版本 tag）。
> 路径缩写：下文 `J/` = `src/main/java/com/github/alexthe666/citadel/`。

## 1. 基本信息

| 项 | 值 | 出处 |
| --- | --- | --- |
| mod_id / 名称 | `citadel` / Citadel | `gradle.properties:6,8` |
| 版本 | `2.7.5`（有 `BUILD_NUMBER` 环境变量时追加 `.N`） | `gradle.properties:2`、`build.gradle:8-10` |
| 作者 | Alexthe666（credits: Gegy1000） | `gradle.properties:7,10` |
| 许可证 | GNU LGPL | `gradle.properties:9` |
| 目标 MC | `minecraft_version=1.21.1`，范围 `[1.21, 1.22)` | `gradle.properties:5,12` |
| 加载器 | **仅 NeoForge**，`neoforge_version=21.1.203`，loader 范围 `[4,)` | `gradle.properties:14,15` |
| 仓库名的含义 | `Citadel-1.21.1` 是上游仓库名（版本线），不是 multiloader 分支后缀 | — |
| Gradle 插件 | `net.neoforged.moddev` 2.0.111 + `java-library` + `maven-publish`；无 Architectury/Loom | `build.gradle:2-6` |
| 工程结构 | **single**（一个 source set，无 common/loader 模块） | `settings.gradle`（无 `include`）、`build.gradle:151-153` |
| Java | toolchain 21；mixin `compatibilityLevel` 仍写 `JAVA_17` | `build.gradle:12-16`、`citadel.mixins.json:5` |
| 映射 | Parchment `1.21` / `2024.07.28` | `gradle.properties:16-17` |
| 编译依赖 | `net.neoforged:neoforge:21.1.203`；shade 内嵌 `com.github.AlexModGuy:JAADec:master-SNAPSHOT` + `org.jcodec:jcodec:0.2.5`（MP4 视频贴图用） | `build.gradle:172-187` |
| maven 坐标 | group `com.github.alexthe666.citadel`，artifactId `citadel-1.21.1`，version `2.7.5` | `gradle.properties:3`、`build.gradle:72-74,218-230` |
| 发布仓库 | `file://$local_maven`（本地目录，无公网 maven） | `build.gradle:225-229` |
| AT | `src/main/resources/META-INF/accesstransformer.cfg`，11 条 | `build.gradle:95`、`neoforge.mods.toml:29-31` |

结论性一句：它不是可发布库，是「Alex's Mobs / Alex's Caves 在 1.21.1 的共用引擎层 + 私人本地构建」（`build.gradle:265-302` 有个把 jar 直接拷进 `D:/instances/.../mods` 的 `deploy` 任务并被 `build` 尾随执行）。

## 2. 源码规模与包结构

实测：`find src -name '*.java' | wc -l` = **182**，`xargs wc -l` 合计 **21252** 行（卡片里的 21,434 与实测差 182，卡片数偏高，以本报告为准）。

| 包（`J/` 下） | 文件 | 行数 | 包 | 文件 | 行数 |
| --- | --- | --- | --- | --- | --- |
| `client/`（合计） | 68 | 9680 | `server/`（合计） | 66 | 7972 |
| ├ `client/model` | 21 | 3268 | ├ `server/entity` | 32 | 5800 |
| ├ `client/gui` | 18 | 2195 | │ └ `entity/pathfinding/raycoms` | 16+5 | 5171 |
| ├ `client/render` | 7 | 2372 | ├ `server/message` | 7 | 539 |
| ├ `client/event` | 6 | 328 | ├ `server/tick` | 9 | 512 |
| ├ `client/{texture,shader,rewards}` | 3×3 | 610 | ├ `server/{world,generation}` | 5+5 | 545 |
| └ `client/{game,tick,video}` | 2+1+1 | 719 | └ `server/{block,event,item}` | 3+2+2 | 487 |
| `mixin/` | 16 | 717 | `math/` | 5 | 1458 |
| `animation/` | 7 | 332 | `config/` | 6 | 233 |
| `item/` | 8 | 209 | 根包（`Citadel`/`ClientProxy`/`ServerProxy`/`CitadelConstants`） | 4 | 603 |

最大 12 个源文件（行）：`server/entity/pathfinding/raycoms/pathjobs/AbstractPathJob.java` 1502、`client/render/pathfinding/WorldRenderMacros.java` 1085、`server/entity/pathfinding/raycoms/AdvancedPathNavigate.java` 908、`client/gui/GuiBasicBook.java` 710、`client/render/pathfinding/UiRenderMacros.java` 598、`server/entity/pathfinding/raycoms/PathingStuckHandler.java` 587、`math/Tuple2f.java` 504、`client/model/container/JsonUtils.java` 484、`math/Tuple2i.java` 444、`server/entity/pathfinding/raycoms/MNode.java` 433、`client/model/AdvancedModelBox.java` 394、`math/CitadelSimplexNoise.java` 356。

**源码树不完整（重要）**：`.git/info/sparse-checkout` 只放行 `*.java/*.gradle/*.properties/*.toml/*mixins.json/*.md/*.cfg/*.txt` 等，未放行 `*.json`（`*.json5` 除外）。实际非 java 文件仅 8 个（mixin 配置、AT、mods.toml 模板、3 个 book `.txt`、`backup_text.txt`、`patreon.txt`）。因此**看不到任何 `.tbl` 模型、动画 json、lang、贴图、blockmodel json**；第 5 节关于资源路径的结论只能从 java 侧的加载代码反推，标注为「代码要求如此，资源未验证」。`src/generated/resources`（`build.gradle:157` 引用）也不存在。

## 3. 入口与注册

唯一入口 `J/Citadel.java`，`@Mod("citadel")` + 类级 `@EventBusSubscriber`（`Citadel.java:54-55`），构造器签名 `(ModContainer, IEventBus)`（NeoForge 特有，`:76`）。构造器里做的事：

```java
public static ServerProxy PROXY = unsafeRunForDist(() -> ClientProxy::new, () -> ServerProxy::new); // :60
ITEMS.register(bus); BLOCKS.register(bus); BLOCK_ENTITIES.register(bus);                  // :77-79
CitadelDataComponents.DATA_COMPONENTS.register(bus);                                        // :80
if (FMLEnvironment.dist.isClient()) { NeoForge.EVENT_BUS.register(PROXY); }                 // :85-87
modContainer.registerConfig(ModConfig.Type.COMMON, ConfigHolder.SERVER_SPEC);               // :88
NeoForge.EVENT_BUS.register(new CitadelEvents());                                          // :89
```

注册方式：全部 `DeferredRegister` + `BuiltInRegistries`/`Registries` 常量（`Citadel.java:62-74`、`item/CitadelDataComponents.java:13-24`），无 Registrate、无自建注册框架。注册内容极少：5 个 Item、1 个 Block（`citadel:lectern`）、1 个 BlockEntityType、2 个 DataComponent、1 个 BiomeModifier serializer（`Citadel.java:81-83`）。

代理分流是它的关键手法：`Citadel.PROXY` 静态字段 + `unsafeRunForDist`（`Citadel.java:148-153`），`ClientProxy extends ServerProxy`（`ClientProxy.java:57`），跨端调用一律 `Citadel.PROXY.xxx()`，服务端版本是空实现（`ServerProxy.java:22-49`）。这等于用「继承 + 运行时实例化」替代了 FML 的 `DistExecutor`/平台服务，代价是客户端类被服务端加载时靠 `FMLEnvironment.dist` 判断。

事件总线订阅点：mod 总线事件 `FMLCommonSetupEvent`/`FMLClientSetupEvent`/`ModConfigEvent.Reloading`/`ServerAboutToStartEvent`/`RegisterPayloadHandlersEvent`（`Citadel.java:92-146`）；游戏总线由 `ClientProxy` 上 9 个 `@SubscribeEvent`（`ScreenEvent.Init.Post:87`、`RenderLevelStageEvent:142,333`、`ClientTickEvent.Pre:198`、`RenderTooltipEvent.Color:245` 等）和 `CitadelEvents` 4 个（`EntityTickEvent.Post`、`PlayerInteractEvent.RightClickBlock`、`PlayerEvent.Clone`、`ServerTickEvent.Pre`）承担；`client/ClientEvents.java:13-21` 是 `@EventBusSubscriber(Dist.CLIENT)` 注册 GLSL。

## 4. 核心系统

### 4.1 动画模型管线（Tabula 形状，不是 GeckoLib 形状）

数据表示三层：
1. **磁盘格式**：`.tbl` 是 **zip**，内含唯一条目 `model.json`（`client/model/TabulaModelHandler.java:181-190`：`new ZipInputStream(file)` 循环找名为 `model.json` 的 entry，找不到抛 `RuntimeException("No model.json present in " + name)`）。所以是「二进制容器 + JSON 载荷」，不是纯 JSON 数据包。
2. **反序列化容器**：Gson 直接映射到 POJO —— `TabulaModelContainer.java:12-26`（`modelName/authorName/projVersion/scale[3]/textureWidth/textureHeight/cubeGroups/cubes/anims/cubeCount`）、`TabulaCubeContainer.java:11-28`（`name/identifier/parentIdentifier/dimensions[3]/position[3]/offset[3]/rotation[3]/scale[3]/txOffset[2]/txMirror/opacity/mcScale/hidden/children`）、`TabulaAnimationContainer.java:11-17` 与 `TabulaAnimationComponentContainer.java:11-29`（`startKey/length/posChange/rotChange/scaleChange/opacityChange/*Offset/progressionCoords/hidden`）。
3. **运行时模型**：`client/model/TabulaModel.java:27-38` 构造时递归 `parseCube` 把 cube 树建成 `AdvancedModelBox` 树，同时填两张索引：`cubes`（按名）与 `identifierMap`（按 Tabula UUID），`rootBoxes` 作为 `parts()` 输出（`:103-105`）。

关键结论（对应问题①）：**模型是数据驱动的，动画不是。** `TabulaModelContainer.getAnimations()`（`:79-81`）在整个仓库里**没有任何调用点**（grep 仅命中定义与 `IAnimatedEntity.getAnimations()` 的同名方法）——Tabula 导出的动画轨被解析后直接丢弃。运行时唯一的动画执行器是 `client/model/ModelAnimator.java`，一个 190 行的手写关键帧插值器：`update(entity)` 清状态（`:49-55`）、`setAnimation(Animation)` 用引用相等决定这一帧是否应用（`:63-67`）、`startKeyframe(duration)` 累加时间轴游标（`:74-80`）、`rotate/move` 把增量记进 `HashMap<AdvancedModelBox, Transform>`（`:110-134`）、`endKeyframe` 才真正写回 box（`:143-189`）。插值用 `Mth.sin(tick*PI/2)` 做 ease-out，并且**同时叠加上一段与当前段**（`:164-181`），`Transform` 只有 rot+offset 六个 float、没有 scale/opacity（`container/Transform.java:9-16`）。帧时间取自 `Minecraft.getInstance().getTimer().getGameTimeDeltaTicks()`（`:161`）——这是 1.21 的 `DeltaTracker` API。

缓存与烘焙：**没有烘焙层，也没有全局缓存**。`.tbl` 走 `TabulaModelHandler.class.getResourceAsStream(path)`（`:52`）——**classpath 直读，不经过 `ResourceManager`**，所以不吃资源包/datapack、不参与 reload、无热重载。旧版的 `IModelLoader.accepts/loadModel` 整段被注释掉了（`:144-179`），`container/TabulaModelBlock.java`(310 行) 与 `container/BakedTabulaModel.java`(68 行，实现 1.21 `BakedModel`、`getQuads` 只返回预先塞好的 immutable list) 因此是**孤儿类**。唯一的缓存是各调用方的 `Map`：`client/gui/GuiBasicBook.java:68` 的 `renderedTabulaModels` + `:402-410` 的「查不到就 new 一个再 put」；`ClientProxy.java:71-84` 在 `onClientInit` 里 load 一个静态 `CITADEL_MODEL`。即：**每实例一份模型对象，每帧原地改 box**（与 GeckoLib 的「baked 模型 + 每帧读 keyframe」不同，见 4.2 对照）。

模型侧的通用能力在 `client/model/AdvancedEntityModel.java`：`faceTarget(yaw,pitch,divisor,boxes...)` 多头瞄准（`:53-61`）、`chainSwing/chainWave/chainFlap` 用相位偏移做蛇/尾/触须的波浪链（`:73-120`）、`walk/flap/swing/bob`（`:150-198`）、`progressRotation/progressPosition`（`:231-253`）。`client/model/AdvancedModelBox.java` 是渲染单元：`updateDefaultPose`/`resetToDefaultPose`（`:147-181`）存默认姿势，`translateAndRotate`（`:232-247`）压 PoseStack，`render`（`:250-268`）递归子节点并在非 `scaleChildren` 时反向 `scale(1/max(s,1e-4))` 抵消父缩放，`doRender`（`:270-296`）把 6 面 quad × 4 顶点逐顶点提交给 `VertexConsumer`。

### 4.2 动画状态与实体同步（对应问题②）

Citadel **没有 variant / 皮肤 / 形态系统**：`grep -rni "variant"` 在 182 个 java 里 0 命中。所谓「外观差异」只有两条路：(a) 模型实例本身不同（每个实体一个 `TabulaModel`，缩放走 `IScaleable.getScaleForLegSolver()`，`animation/IScaleable.java:8-10`）；(b) `server/entity/CitadelEntityData` 那个 CompoundTag（见下）。所以「variant 在两侧各扮演什么角色」的答案是：**不扮演任何角色，这是 GeckoLib/Alex's Mobs 自己实现的部分**。

动画的服务器侧状态只有三个字段大小的东西：`IAnimatedEntity`（`animation/IAnimatedEntity.java:11,16-40`）要求实现 `getAnimationTick/setAnimationTick/getAnimation/setAnimation/getAnimations()`，`Animation` 只是 `{int id(废弃), int duration}`（`animation/Animation.java:7-52`）。`animation/AnimationHandler.java` 一个枚举单例承载全部逻辑：

```java
public <T extends Entity & IAnimatedEntity> void sendAnimationMessage(T entity, Animation animation) {
    if (entity.level().isClientSide) return;                      // :24
    entity.setAnimation(animation);
    PacketDistributor.sendToAllPlayers(new AnimationMessage(entity.getId(),
        ArrayUtils.indexOf(entity.getAnimations(), animation)));   // :28
}
```

同步粒度是**「实体 id + 动画在数组里的下标」两个 int**（`server/message/AnimationMessage.java:15-30`，`write` 就是 `writeInt × 2`）。tick 推进在 `updateAnimations`（`AnimationHandler.java:37-58`）：tick==0 时先发可取消的 `AnimationEvent.Start` 再广播；tick<duration 时自增并每 tick post 一个 `AnimationEvent.Tick`；tick==duration 时归零并回到 `NO_ANIMATION`。客户端收包后按下标还原（`ClientProxy.java:267-279`，`index == -1` 表示清空）。

两个必须知道的代价：`sendAnimationMessage` 用 `PacketDistributor.sendToAllPlayers`（**全服广播，不是 sendToPlayersTrackingEntity**），且 `ArrayUtils.indexOf` 对 `getAnimations()` 返回的**新建数组**做线性查找——Alex's Mobs 侧 `EntityBison.java:395-396` 就是 `return new Animation[]{...}`。动画不持久化：它只活到 duration 结束，`ICitadelDataEntity` 的 tag 里也没有它。

通用实体数据的载体是**唯一一个注册生效的实体 mixin**：`mixin/LivingEntityMixin.java:22` 用 `SynchedEntityData.defineId(LivingEntity.class, EntityDataSerializers.COMPOUND_TAG)` 给**所有** LivingEntity 加一条同步 `CITADEL_DATA`，`defineSynchedData` TAIL 里 define（`:28-31`），并在 `addAdditionalSaveData/readAdditionalSaveData` 读写 `CitadelData` 键（`:33-46`），同时给 LivingEntity 实现 `ICitadelDataEntity`。API 面是 `CitadelEntityData.getOrCreateCitadelTag/get/set`（`server/entity/CitadelEntityData.java:15-28`）。跨端「额外」推送只有 `PropertiesMessage`（`server/message/PropertiesMessage.java:14-54`：`String propertyID + CompoundTag + int entityID`），且 handler 只认两个字面量 `"CitadelPatreonConfig"` 和 `"CitadelTagUpdate"`（`:48`）——**这不是通用属性同步框架，是 Patreon 特权专用的硬编码**。

一个反直觉的坑（对应问题②）：CompoundTag 参与 `SynchedEntityData` 意味着**原版LivingEntity（含玩家）每次该 tag 变化都会向所有 tracking client 重发整份 NBT**；`setCitadelTag` 没有脏标记/裁剪，Alex's Mobs 用它存 AI 中间状态。这条对「求仙问道」直接决定要不要接：想学「给所有实体挂一个免费同步 NBT 袋」的形状可以，照抄实现会踩性能。

### 4.3 异步寻路（MineColonies 血统，仓库最大的单体系统）

`server/entity/pathfinding/raycoms/` 共 21 文件 5171 行，文件头统一注明「used with permission from Raycoms」（`AdvancedPathNavigate.java:2-4`）。分层：
- **线程池**：`Pathfinding.java:19-41` 一个静态 `ThreadPoolExecutor(1, PathfindingConstants.pathfindingThreads, 10s, LinkedBlockingDeque)`；`pathfindingThreads` 与 `maxPathingNodes=5000`、`isDebugMode` 都是**可写字段但没有配置文件**（`PathfindingConstants.java:50-54`）。线程工厂 `CitadelThreadFactory`（`Pathfinding.java:46-74`）做两件很「库模」的事：从 `LogicalSidedProvider.WORKQUEUE.get(SERVER)` 借 `MinecraftServer.getRunningThread()` 的 ContextClassLoader 装到新线程（否则 mixin/AT 后的游戏类在别的线程上加载不到），并 `setDaemon(true)` + `MAX_PRIORITY` + `setUncaughtExceptionHandler` 记日志。
- **工作单元**：`AbstractPathJob implements Callable<Path>`（`:46`），A* 主循环 `search()` 每轮检查 `Thread.currentThread().isInterrupted()`（`:573-575`）。世界读取走 `ChunkCache implements LevelReader`（`ChunkCache.java:40`），构造时一次性抓 `ChunkHolder.getFullChunkFuture().getNow(...)` 快照（`:67-79`，靠 AT 放开 `ChunkMap.getVisibleChunkIfPresent`），因此 worker 线程不碰 `ServerLevel`。
- **导航器**：`AdvancedPathNavigate extends AbstractAdvancedPathNavigate extends GroundPathNavigation`（`AbstractAdvancedPathNavigate.java:14`），对外是 `moveToXYZ/moveAwayFromXYZ/moveToRandomPos/moveToLivingEntity` 全套 `PathResult` API（`:63-131`）。`PathResult.startJob(executor)` 提交（`PathResult.java:165-174`，`submit` 的 NPE 被吞成「Mod tried to move an entity from non server thread」日志 `:171`）。
- **每 tick 做什么**：`AdvancedPathNavigate.tick()`（`:249-330`）先用 `nodeEvaluator.entityWidth/Height/Depth` 覆写为实体 BB（`:250-257`，靠 AT 放开这三个 protected 字段），再判 `pathResult.isFinished()`，未完成就 **直接 return（不阻塞、不重复计算）**；完成后 `processCompletedCalculationResult()`；然后**整段重写并替代原版 `PathNavigation.tick()`**（`:289-318` 有注释说明为什么要替换：原版 `moveControl` 在空 BB 方块前不肯上台阶），最后 `stuckHandler.checkStuck(this)`（`PathingStuckHandler.java` 587 行：抖动/超时/卡死计数后决定重试或放弃）。
- **可视化**：worker 的 visited/notVisited/path 三个 `Set<MNode>` 通过 `SyncePathMessage` 发到客户端（`server/message/SyncePathMessage.java:48-85` 手写 `size + 逐个 serializeToBuf`，**只在 `Pathfinding.isDebug()` 下发出**），客户端 `PathfindingDebugRenderer`（`client/render/pathfinding/PathfindingDebugRenderer.java:21-58`）用自建的 `RenderBuffers` 画线。这是全仓库唯一的「服务端算 → 客户端画」调试通路，值得抄形状。

### 4.4 自定义碰撞与实体移动

`server/entity/collision/`（6 文件）把原版 `Entity#getAllowedMovement` 私有链复制出来：`ICustomCollisions.getAllowedMovementForEntity`（`:21-43`）+ 复制的 `collideBoundingBox2/collideWithShapes2`（`:50-100`，注释自称 1.18 逻辑），扩展点只有一个 `boolean canPassThrough(BlockPos, BlockState, VoxelShape)`（`:46`）。`MovementControllerCustomCollisions` / `CustomCollisionsNavigator` / `CustomCollisionsBlockCollisions` / `CitadelVoxelShapeSpliterator` 配套。价值：想让妖兽穿过荆棘/藤蔓/法阵而不改方块本身，这是可借鉴的最小切口；代价是它 fork 了原版碰撞解算，MC 一升级就要重对（`:49` 注释已经和当前版本脱节）。

### 4.5 全局/局部 tick 速率（Citadel 独有的性能系统）

`server/tick/TickRateTracker.java`（`:12-110`）持有一组 `TickRateModifier`（7 个文件，`GLOBAL`/`CELESTIAL`/`LOCAL` 三类，`TickRateModifierType.isLocal()`）。`getEntityTickLengthModifier` 把所有 appliesTo 当前坐标的乘子连乘（`:79-87`），`hasNormalTickRate` 即乘子 == 1。被降速的实体进入 `specialTickRateEntities`，由 `masterTick()`（`:19-31`）每 master tick 手动 `tickEntityAtCustomRate`（服务端实现是 `((ServerLevel)level).tickNonPassenger(entity)`，`ServerTickRateTracker.java:36-40`）。日/月推进也被乘子改写（`getDayTimeIncrement`，`:65-77`，分数速率用「每 1/f 个 tick 走一次」的整数化近似）。状态持久化在 `SavedData`（`server/world/CitadelServerData.java:13-40`，OVERWORLD 的 `citadel_world_data`，按 `MinecraftServer` 做 static map 缓存），改动通过 `SyncClientTickRateMessage` 全量下发（`ServerTickRateTracker.java:44`）。
但**触发它的 mixin 没注册**（见第 6 节）：`LevelMixin#guardEntityTick` 取消原版 tick 的入口当前失效，只有 `CitadelEvents.onServerTick`（`server/CitadelEvents.java:72-88`）还在设 `setGlobalTickLengthMs`。也就是说 1.21.1 这份移植的实体降速是**半瘫**状态，别照抄「能用」这个假设。

### 4.6 渲染层如何接入（对应问题④）

明确事实：**Citadel 完全不使用 1.21 的 `RenderPipeline`**（`grep -rn "RenderPipeline"` 0 命中），也不引用 Sodium/Iris/OptiFine（0 命中）。它的接法是「沿用 1.17–1.20 时代的 `RenderType` + `MultiBufferSource` + `PoseStack`」三件套：
- 实体侧：`client/model/basic/BasicEntityModel.java:17-27` 用 `RenderType::entityCutoutNoCull` 构造 `EntityModel`，`renderToBuffer` 遍历 `parts()`；取顶点缓冲靠 `bufferSource.getBuffer(RenderType.entityCutoutNoCull(tex))`（例子 `client/render/CitadelLecternRenderer.java:39-41`、`client/gui/GuiBasicBook.java:120-122`）。因为 shader/状态全走原版 `entityCutoutNoCull`，**Sodium/Iris 天然不冲突**（它们只重写 terrain/sky/lighting pipeline），但也没有任何自定义 shader 实体的批处理收益。
- 自定义 RenderType：`client/shader/CitadelShaderRenderTypes.java:13-38` 用「`extends RenderType` + `RenderType.CompositeState.builder().setShaderState(...).setOutputState(RAINBOW_AURA_OUTPUT)`」拼一个写到离屏 target 的透明 pass；`client/render/pathfinding/WorldRenderMacros.java:940-1000` 更极端——private 构造里 `super(...)` 之后直接 `throw new IllegalStateException()`，只为拿到 `RenderType.create` 的 protected 入口，并**手工枚举全部 13 个 StateShard**。
- GLSL：`client/ClientEvents.java:16-18` 在 `RegisterShadersEvent` 注册 `citadel:rendertype_rainbow_aura`。后处理链自己管：`client/shader/PostEffectRegistry.java:20-45` 用 `new PostChain(...)` 手动构造并 `resize(window)`，在 `LevelRenderer.initOutline` 时机重建（该 mixin 未注册，故此路亦瘫）。
- **批处理**：没有实体合批、没有 instancing、没有 per-model 顶点缓存。`AdvancedModelBox.doRender`（`:270-296`）每帧每 box 每面每顶点都新建 `Vector3f`/`Vector4f` 并 `mul` 矩阵——**每帧垃圾分配**，100 只 × 30 box 时是明显的 young-gen 压力。唯一的「批」是原版 `BufferBuilder` 按 RenderType 的分段。

与 GeckoLib 的分工差异（对应问题③）：GeckoLib 5 走「`GeoRenderState` 数据袋 + DataTicket + baked cache + Molang 表达式 + 事件化 layer」，Citadel 走「实体上 4 个 getter + 每实例可变 box 树 + Java 手写关键帧」。前者把渲染状态从实体里抽走了，后者没有——`ModelAnimator.endKeyframe` 直接读 `Minecraft.getInstance().getTimer()`（`ModelAnimator.java:161`），等于假定「渲染线程 == 有 Minecraft 单例的线程」，在 1.21.5+ 的 render-state 化与潜在多线程里会失效。动画实体一个 tick 的分工：服务端 = `Mob.tick()` 里显式调 `AnimationHandler.INSTANCE.updateAnimations(this)`（Alex's Mobs 有 30+ 处这样调，如 `entity/EntityBison.java:274`），AI/命中判定**自己写在 `customServerAiStep`/goal 里靠 `getAnimationTick()` 卡点**（`EntityBison.java:238` 用 `getAnimationTick() > 8 && dist < getBbWidth()+1 && hasLineOfSight` 决定真命中；`:212` 用 `== 30` 触发吃草特效）；Citadel 不提供命中窗口、不提供动画事件回调、不提供 sound/particle keyframe 指令帧——这些全靠宿主 mod 手写 if。客户端 = 每帧 `setupAnim` → `resetToDefaultPose()` → `animator.update/setAnimation/startKeyframe...` → 原版 `renderToBuffer`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：6 个 payload，全部在 `Citadel.registerPayloads`（`Citadel.java:130-138`）一处注册，registrar 是 `event.registrar("citadel").versioned("2.7.0").optional()`。清单：`PropertiesMessage`(playToServer，但 handler 里判 `flow().isClientbound()` — 语义与注册方向不自洽，`PropertiesMessage.java:42-52`)、`AnimationMessage`(toClient, 2 int)、`DanceJukeboxMessage`(bidirectional, int+bool+BlockPos)、`SyncePathMessage`(toClient, 3×Set<MNode>)、`SyncPathReachedMessage`(toClient)、`SyncClientTickRateMessage`(toClient, CompoundTag)。`PacketBufferUtils.java`(181 行) 是手写的 `readTag/writeTag/writeUTF8String` 工具——在 `StreamCodec` 时代属于重复造轮，且 UTF8 长度手工编码。**所有 payload 都是 optional()**：连不上就不连，没有协议握手校验。
- **动画资源格式与加载路径**：`.tbl`（zip+`model.json`）；路径由调用方拼字符串，例如 `ClientProxy.java:73` 的 `"/assets/citadel/models/citadel_model"`（handler 自动补 `/` 与 `.tbl`，`TabulaModelHandler.java:46-51`），GuiBasicBook 从书页数据里取 `"modid:path"` 再拼成 `"/assets/<mod>/<path>"`（`:406`）。**注意这是 classpath 资源名而不是 ResourceLocation**：材质包/数据包覆盖不了它，非 jar 环境（开发时 `src/main/resources` 也在 classpath，能跑）与生产一致但不可热重载。仓库内**看不到任何 `.tbl`**（sparse checkout 未放行）。
- **配置**：一个 COMMON 类型 `ModConfigSpec`（`config/ConfigHolder.java:8-16`），4 项：`Track Entities`、`Skip Datapack Warnings`、`chunkGenSpawnModifier`(0..100000)、`April Fools Content`（`config/ServerConfig.java:17-21`）。写法是「`ModConfigSpec` 实例字段 + 同名 static 可变字段」，靠 `Citadel.onModConfigEvent` 在 Reloading 时手动 rebake 到 static（`Citadel.java:112-122`）。没有 CLIENT 配置。
- **datagen**：**完全没有**。`grep -rni "datagen|DataProvider|GatherDataEvent|LanguageProvider|RecipeProvider"` 0 命中，`src/generated/resources` 不存在（`build.gradle:157` 引用了但目录缺失）。唯一像 datagen 的是 `generateModMetadata`（`ProcessResources` 把 `src/main/templates` 的 `neoforge.mods.toml` 展开变量，`build.gradle:191-215`）。世界相关内容是**运行时**改的：`VillageHouseManager.addToPool` 直接改 `StructureTemplatePool.templates/rawTemplates`（靠 AT，`server/generation/VillageHouseManager.java:33-41`），`SurfaceRulesManager` 按维度类别合并 surface rule（`mixin/NoiseGeneratorSettingsMixin.java:28-35`），`SpawnProbabilityModifier` 是注册的 BiomeModifier codec。**没有 JSON 配方/语言文件可依赖**：这些都得宿主 mod 自己带。

## 6. Mixin

配置：`src/main/resources/citadel.mixins.json`（`required: true`、`package: ....citadel.mixin`、`refmap: citadel.refmap.json`、`injectors.defaultRequire: 1`）。`neoforge.mods.toml:15-16` 只声明这一个。**关键事实：源码里有 16 个 mixin 类（root 8 + `client/` 8，共 717 行），但 json 只注册 3 个**（`mixins.json:7-11`），且 `"client": []` 是空数组。也就是 13 个 mixin 是移植后遗留的死代码，它们提供的事件桥（`client/event/` 6 个事件类）**在本版本里永远不会被 post**。

已注册（3）：
| 类 | 目标 | 注入点 | 目的 |
| --- | --- | --- | --- |
| `mixin/LivingEntityMixin.java:28,33,41` | `LivingEntity` | `defineSynchedData` / `addAdditionalSaveData` / `readAdditionalSaveData` 各 `@At("TAIL")` | 加一条全实体共享的同步 `EntityDataSerializers.COMPOUND_TAG`，并让它随 NBT 存读（4.2 的地基） |
| `mixin/NoiseGeneratorSettingsMixin.java:28` | `NoiseGeneratorSettings`（priority 500） | `surfaceRule` `@At("HEAD")` + cancellable | 把 `SurfaceRulesManager` 按 `RuleCategory` 注册的规则与原规则合并（原版在前，保证 WorldWeaver/Blueprint 优先，见文件注释 `:14-18`） |
| `mixin/BlockBehaviourAccessor.java:10-11` | `BlockBehaviour` | interface mixin（accessor） | 放开方块行为字段给 `server/block` |

未注册（13），按用途归类（这些正是「Citadel 在 1.20.1 原版里本来干什么」的地图）：
- **tick 速率/降速**（3）：`LevelMixin:23` `guardEntityTick` `@At("HEAD")` cancellable → 取消原版实体 tick 以接管；`MinecraftServerMixin:19-42` `runServer` 在 `startMetricsRecordingTick` 前 `@At(INVOKE)` + `@ModifyConstant(50L, expect=4)` → 改全局 ms/tick；`ServerLevelMixin:19` / `client/ClientLevelMixin:42` `tickTime` `@ModifyConstant(1L, expect=2)` → 改昼夜推进步长。
- **渲染钩子桥**（4）：`client/LivingEntityRendererMixin:23-69` 四处（`setupRotations` RETURN、`render` 中 `EntityModel.setupAnim` 前后各一、`render` RETURN）→ post `EventLivingRenderer.{SetupRotations,PreSetupAnimations,PostSetupAnimations,PostRenderModel}`；`client/LevelRendererMixin.java:34-93` 七处（`initOutline`/`resize` TAIL、`renderLevel` 三个 `@At(INVOKE)`、`getTeamColor` `@Redirect`→`EventGetOutlineColor`、`renderSky` 中 `getTimeOfDay` `@Redirect`）→ 后处理与描边；`client/ItemBlockRenderTypesMixin:19` `getRenderLayer` TAIL→`EventGetFluidRenderType`；`client/HumanoidModelMixin:26,36` `poseRightArm/poseLeftArm` HEAD→`EventPosePlayerHand`。
- **客户端表现**（2）：`client/AbstractClientPlayerMixin:22` `getSkin` `@ModifyReturnValue`（换玩家皮肤纹理实现 cape）、`client/SoundEngineMixin:15` `calculatePitch` RETURN（按客户端 tick 速率改音高）。
- **其他**（4）：`client/ClientLevelMixin:33` `getStarBrightness`、`client/SplashRendererMixin:31-66`（标题界面标语替换，April Fools）、`ChunkGeneratorMixin:22` `getMobsAt` RETURN→`EventMergeStructureSpawns`（结构生物合并）、`SmithingMenuMixin:19` `createResult` 的 `getRecipesFor` `@ModifyExpressionValue`（追加自定义锻造配方）。

所有注入点都写 `remap = CitadelConstants.REMAPREFS`，而 `CitadelConstants.java:9` 是 `true`——注意这在 Mojang-mapped 的 NeoForge 上语义与旧 SRG 时代不同，属遗留写法。

## 7. 值得学的 5 条

1. **一个 mixin 换「所有 LivingEntity 的同步 NBT 袋」，把跨端状态成本压到零样板**：`mixin/LivingEntityMixin.java:22-46`。宿主 mod 想给妖兽挂「结冰/石化/被驯服标记/技能冷却」时不需要每家定义 `EntityDataAccessor`，直接 `CitadelEntityData.getOrCreateCitadelTag(e).putInt(...)` 就自动同步 + 自动存档（`:33-46`）。值得抄的是这个**契约形状**（一个接口 `ICitadelDataEntity` + 一个静态工具类 + 一条合成数据），实现细节要改：按 key 拆 accessor 或换 NeoForge `AttachmentType`，避开整份 NBT 重发（4.2 末尾的性能提醒）。
2. **动画同步只发「实体 id + 动画下标」两个 int**：`animation/AnimationHandler.java:28` + `server/message/AnimationMessage.java:15-30`。前提是 `IAnimatedEntity.getAnimations()` 约定「枚举数组下标即协议号」，宿主在 AI 里写 `setAnimation(ANIMATION_EAT)` 完全不需要关心网络。抄它的收益是**带宽与实现复杂度都是 O(1)**；抄的时候必须补两点：改成 `sendToPlayersTrackingEntityAndSelf`，并把 `getAnimations()` 换成静态常量数组（`EntityBison.java:395` 每次 new 数组 + `ArrayUtils.indexOf` 线性查找是反面教材）。
3. **关键帧不写 JSON、写 Java：`ModelAnimator` 的 `startKeyframe/endKeyframe/resetKeyframe` 三段式**：`client/model/ModelAnimator.java:74-100,143-189`。好处是动画直接引用模型字段（`animator.rotate(head, rad(-20), 0, 0)`，见 Alex's Mobs `client/model/ModelBison.java:114-135`），编译期校验、能调方法复用姿势（`eatPose()` 被反复调用）、每段自动 ease-out 并与上一段交叉叠加。**对「求仙问道」的结印/御剑/妖兽扑咬这类少量但要求精确手感的关键帧，这套比 GeckoLib 的 animation json 更好控**。它的边界也很清楚：一次只能服务一段动画、没有 `AnimationController`/过渡/混合/速度控制，所以只抄形状不要抄成主引擎（见第 8 节结论）。
4. **异步寻路的「世界快照 + 借 server 线程的 ClassLoader」组合**：`ChunkCache.java:62-79`（`implements LevelReader`，构造时抓 `ChunkHolder.getFullChunkFuture().getNow(UNLOADED)`）+ `Pathfinding.java:52-74`（worker 线程 setContextClassLoader 为 `MinecraftServer.getRunningThread()` 的 CCL，`setDaemon(true)` + uncaught handler）+ `AbstractPathJob.java:573`（每轮检查 interrupt）。这是让大型妖兽在寻路时不阻塞主线程、又不崩 mixin/AT 加载的**完整最小配方**，三处缺一都会踩坑（不借 CCL 会在 worker 上抛 NoClassDefFound；不做快照会 CME；不检查中断则卡住队列）。
5. **给自定义渲染留「原版 `entityCutoutNoCull` 优先、必要时才拼 RenderType」的克制策略**：`client/model/basic/BasicEntityModel.java:17-20` 默认就是原版 cutout；真正需要离屏 target 时才 `extends RenderType` 拼 CompositeState（`client/shader/CitadelShaderRenderTypes.java:19-38`）。结果是全仓库 0 处 `RenderPipeline`、0 处 Sodium 特判却能和 Sodium/Iris 共存（因为它根本没碰被接管的管线）。**这是与 GeckoLib 最不一样的工程取舍，也是它「不需要为各渲染 mod 写兼容层」的原因**；反面是 `WorldRenderMacros.java:940-950` 用 `throw new IllegalStateException()` 的 private 构造当 `create` 入口，属于能用但别学的脏法。

## 8. 公开 API 与接入方式（它是被依赖的引擎层）

- **gradle 坐标**：group `com.github.alexthe666.citadel`、artifactId `citadel-1.21.1`、version `2.7.5`（`gradle.properties:2-3`、`build.gradle:72-74`）。但 `publishing` 只发到 `file://$local_maven`（`build.gradle:225-229`），**没有公网 maven**；Raguto 这份移植的实际用法是宿主 mod 与它一起本地构建。宿主依赖时它作为普通 runtime jar 存在（非 jar-in-jar），并且**因为 AT/mixin 只作用于它自己，宿主拿不到被放开原版成员的权限**——所以宿主必须自带 AT（Alex's Mobs 的 `entityWidth` 等就是靠 Citadel 自己的 AT，见 `accesstransformer.cfg:4-6`）。
- **入口包**：`com.github.alexthe666.citadel`（`Citadel.PROXY`、`CitadelConstants`）、`...citadel.animation`（`Animation`/`IAnimatedEntity`/`AnimationHandler`/`AnimationEvent`/`IScaleable`/`LegSolver`/`LegSolverQuadruped`）、`...citadel.client.model`（`TabulaModel`/`AdvancedModelBox`/`AdvancedEntityModel`/`ModelAnimator`/`LegArticulator`/`ITabulaModelAnimator`/`TabulaModelHandler`）、`...citadel.client.render`、`...citadel.server.entity`（`CitadelEntityData`/`ICitadelDataEntity`/`IDancesToJukebox`/`IComandableMob`/`IModifiesTime`）、`...citadel.server.entity.pathfinding.raycoms`、`...citadel.server.entity.collision`、`...citadel.client.rewards`（`CitadelCapes`/`CitadelPatreonRenderer`）、`...citadel.item`（`ItemCitadelBook`/`ItemWithHoverAnimation`）。
- **生物接入一个动画要写的四样**（全部有实例，取自宿主 Alex's Mobs 1.21.1）：
  1. 实体 `implements IAnimatedEntity`，声明 `public static final Animation ANIMATION_X = Animation.create(duration)`，`getAnimations()` 返回数组，`customServerAiStep`/`tick` 里调 `AnimationHandler.INSTANCE.updateAnimations(this)`（`Raguto__AlexsMobs-1.21.1/src/main/java/com/github/alexthe666/alexsmobs/entity/EntityBison.java:59-69,274,375-396`）。
  2. 渲染器 `render` 前调 `model.animate(entity, ...)`，模型里 `resetToDefaultPose()` + `animator.update(entity)`（`.../client/model/ModelBison.java:111-118`）。
  3. 模型类：`extends TabulaModel`（读 `.tbl`）或 `extends AdvancedEntityModel` + 手工 `new AdvancedModelBox(this, "head")` 建树（`ModelBison.java:105-110`），然后在 `animate` 里用 `ModelAnimator` 写关键帧。
  4. 触发点在 AI：`setAnimation(ANIMATION_X)` + `getAnimationTick()` 卡命中/特效窗口（`EntityBison.java:207-212,238,251-257`）。
- **最小示例**（本报告作者按上述四步归纳）：
  ```java
  public static final Animation ROAR = Animation.create(30);
  private Animation animation = NO_ANIMATION; private int animationTick;
  // tick(): AnimationHandler.INSTANCE.updateAnimations(this);
  // AI: if (this.animation == NO_ANIMATION) this.setAnimation(ROAR);
  //     if (this.animation == ROAR && this.animationTick == 18) spawnParticles();
  ```

### 附：可移植性与结论（对应问题⑤⑥）

**与 MC 版本强耦合（要改才能回 1.20.1）**，按耦合密度排序：
1. `mixin/`（16 文件）——耦合最深：`guardEntityTick`（1.19+ 才有）、`Level#tickTime`、`MinecraftServer#runServer` 的 `50L` 常量、`PlayerSkin` record（1.20.5+）、`RecipeManager.getRecipesFor(RecipeType, RecipeInput, Level)`（1.20.5+，`SmithingMenuMixin.java:21`）、`EntityModel.setupAnim(Entity,...)` 签名。不过 13/16 本来就没注册，等于**耦合最深的部分不用搬**。
2. `client/model/container/`（11 文件）——`BakedTabulaModel implements BakedModel`（1.21 的 `getQuads`/`ItemDisplayContext`/`Transformation`）、`TabulaModelBlock`（`ItemTransforms.Deserializer` 在 1.20.1 存在但 `PerspectiveWrapper` 命名不同）、`JsonUtils`。这一包全是块模型管线，且 4.1 已证明**运行时没人用**，直接不要。
3. `Citadel.java:130-138` + `server/message/`——1.20.5+ 的 `StreamCodec`/`CustomPacketPayload`/`RegisterPayloadHandlersEvent`；Forge 1.20.1 要退回 `IMessageConsumer`/`EventPacket`。
4. `item/CitadelDataComponents.java`——DataComponent 是 1.20.5+；1.20.1 用 Forge `ATTACHMENT_TYPES` 或 NBT。
5. 单点耦合：`ModelAnimator.java:161`（`getTimer().getGameTimeDeltaTicks()` → 1.20.1 是 `Minecraft.getFrameTime()`/`partialTicks`）、`accesstransformer.cfg:9`（`DeltaTracker$Timer`）、`AdvancedModelBox.java:292`（它调的是**不带矩阵**的 `addVertex(x,y,z,color,u,v,overlay,light,nx,ny,nz)`；1.20.1 的 `VertexConsumer` 对应方法要额外传 `Matrix4f`/`PoseStack.Pose`，所以这里要补一个参数，其余顶点语义一致）、`PathfindingDebugRenderer.java:21`（`new RenderBuffers(int)` 构造在 1.20.1 是无参）。`ChunkCache.java:101`（`getTileEntity(pos, EntityCreationType)` 这个参数 1.20.1 没有）。
**纯 Java 可直接搬**：`math/`（5 文件 1458 行，`Tuple2f/Tuple2i/Point2f/Point2i/CitadelSimplexNoise`，只依赖 JOML 与 `Mth`）、`animation/` 的 `Animation`+`IAnimatedEntity`（换 `PacketDistributor` 一行）、`client/model/{ModelAnimator,AdvancedModelBox,AdvancedEntityModel,LegArticulator}` + `client/model/basic/`（PoseStack/VertexConsumer 跨版本稳定）、`TabulaModel` + `TabulaModelHandler` + `container/{Tabula*Container,Transform,TextureOffset}`（Gson+zip）、`pathfinding/raycoms/{AbstractPathJob,MNode,PathingOptions,PathingStuckHandler,SurfaceType,PathResult}`（只依赖 `LevelReader`/`BlockPos`）、`tick/modifier/`、`config/`。

**结论：求仙问道妖兽动画层怎么组合。**
- **该抄 Citadel 的形状**：①「一个实体接口 + 一个枚举单例 handler + 两个 int 的包」这套动画状态机（第 7 节 1、2 条），它比 GeckoLib 的 `GeoAnimatable.registerControllers` 轻一个数量级，适合几百个只有 2–4 段动作的妖兽；②`ICustomCollisions.canPassThrough`（4.4）——妖兽穿林/穿法阵的最小切口；③`AdvancedEntityModel.chainWave/faceTarget`（`client/model/AdvancedEntityModel.java:53-120`）——多首蛇妖、群眼妖物的程序化姿势，GeckoLib 里没有等价物（要在 GeckoLib 里做等价效果需自己写 bone 遍历）；④`LegSolver`/`LegArticulator`（`animation/LegSolver.java:60-82`、`client/model/LegArticulator.java:15-38`）——贴地四肢 IK，GeckoLib 也不带；⑤异步寻路整包（4.3），这是 Citadel 最有价值、和动画完全正交的一块，MineColonies 血统的代码在 1.20.1 Forge 上同样可用（只需改 `ChunkCache` 的一个方法签名）。
- **该直接用 GeckoLib**：需要逐帧混合、过渡时间、Molang 条件、动画事件（sound/particle 指令帧）、多控制器并发、baked 缓存与热重载的 Boss/召唤兽大战斗。Citadel 在这些问题上**没有实现**（4.1：动画轨解析后丢弃；`Transform` 无 scale/opacity；无 controller）——不要指望补出来。
- **明确不要抄**：`mixin/` 的 13 个未注册类与 `client/event/` 的 6 个事件（死桥）、`client/model/container/TabulaModelBlock` + `BakedTabulaModel`（无调用方）、`.tbl` 走 classpath 的加载方式（不可热重载、不吃资源包，GeckoLib 的 `PreparableReloadListener` 方案明显更好）、`PropertiesMessage` 的硬编码 propertyID 分派、`client/video` + jcodec/JAADec 全家（`build.gradle:175-186`，与目标无关且 `master-SNAPSHOT` 不可复现）、`TickRateTracker`（依赖未注册的 `LevelMixin`/`MinecraftServerMixin`，当前半成品）、以及 `doRender` 里每顶点新建 `Vector3f/Vector4f` 的写法（`AdvancedModelBox.java:279-292`，抄了就把 GC 压力一起抄过来）。
- **一句话总判**：Citadel 不是「动画引擎」，是「**给原版盒模型加一层 Java 关键帧插值 + 给实体加一条同步 NBT 袋 + 一套 MineColonies 寻路**」的胶水层；它自己已经放弃了 mixin 驱动的那半边（13/16 未注册）。所以「自研动画/实体框架值不值得抄一套」的答案是：**动画主线抄 GeckoLib，但把 Citadel 的同步契约、IK/链条姿势工具与异步寻路当作可搬的零件库；不要把它当框架整体接管。**
