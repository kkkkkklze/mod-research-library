# FDLib 源码分析报告

> 仓库：`源码库/_参考仓库/_bulk/FINDERFEED__FDLib`。下文所有路径均相对仓库根，行号取自本检出实测。
> 定位：作者 FINDERFEED 自用的**表现层前置库**（动画/模型/屏幕/HUD/过场/配置），不是内容 mod。

## 1. 基本信息

- mod_id `fdlib`；显示名 FDLib；作者 FINDERFEED；mod 版本 `1.0.9`（`gradle.properties:13,14,16,19`）；描述自嘲："A library with some cool features. Idk what other things to write here."（`gradle.properties:20`）。
- 目标平台：**MC 1.21.1 + NeoForge 21.1.211**，`minecraft_version_range=[1.21.1,1.22)`、`neo_version_range=[21.1.0,)`、`loader_version_range=[4,)`（`gradle.properties:5,7,8,9,10`）。**没有 Forge、没有 Fabric 分支**，多加载器支持为零。
- 许可证：All Rights Reserved（`gradle.properties:15`），且 `LICENSE.txt:5` 明文 **"Embedding this library into your mod jar is prohibited."**；`:9,:11,:13,:15` 允许把代码当教材/私有使用，禁止再分发源码、禁止拆用、禁止盈利。也就是说：**只能"读形状"，不能引依赖，也不能 jar-in-jar**。
- Gradle：`java-library` + `maven-publish` + `net.neoforged.gradle.userdev 7.0.165`（`build.gradle:2,5,6`），单模块工程（`settings.gradle` 无 include），`base.archivesName = mod_id`（`build.gradle:25`），AT 走 `minecraft.accessTransformers.file`（`build.gradle:32`），`sourceSets.main.resources { srcDir 'src/generated/resources' }`（`build.gradle:65`）。
- Java 版本：**21**（`build.gradle:28` `JavaLanguageVersion.of(21)`；`fdlib.mixins.json:4` `compatibilityLevel: JAVA_21`）。
- 编译依赖：`implementation "net.neoforged:neoforge:${neo_version}"`（`build.gradle:73`）、`fileTree(dir:'jarmods')`（`:75`，本检出无该目录）、以及 **Sodium 与 Iris 以 cursemaven 直连版本号编译**（`:77,78`）——库需要在 mixin 里避开/optimize 它们的行为。
- 发布坐标：`com.finderfeed.fdlib:fdlib:1.0.9-1.21.1`，`mavenJava` publication `from components.java`（`build.gradle:14,15,25,108,109`），**仓库地址是本地目录** `file://${projectDir}/repo`（`build.gradle:114`）——没有公共 maven，下游只能本地 file repo 接入。
- mods.toml：`modLoader=javafml`，声明 `[[mixins]]` 与 `[[accessTransformers]]`，对 neoforge 与 minecraft 各一条 required 依赖（`src/main/resources/META-INF/neoforge.mods.toml:7,50,55,61,80`）。

## 2. 源码规模与包结构

实测（`find src -name '*.java' | wc -l` 与 `find src -name '*.java' -exec cat {} \; | wc -l`）：**443 个 .java、28,360 行**。速览卡片写的 443/28,803 文件数一致、行数略高；另外用 `xargs wc -l` / `wc -l {} +` 求和会因参数分批只打印尾批的 `14559 total`，这是命令陷阱不是仓库差异，复核时要用 `cat | wc -l`。

主要包（`src/main/java/com/finderfeed/fdlib/` 下，含子包累计文件数）：

| 包 | 文件数 | 内容 |
|---|---|---|
| `systems/bedrock` | 113 | 基岩版模型/动画系统（库最大子系统） |
| `systems/screen` | 54 | 注解驱动的容器界面框架 + 屏幕效果 |
| `shunting_yard` | 35 | 中缀表达式→RPN 求值器（动画关键帧用） |
| `systems/simple_screen` | 33 | 第二代简化界面 widget 框架 |
| `util` | 31 | 渲染/数学/codec/粒子工具 |
| `init` | 19 | 注册与生命周期订阅者 |
| `systems/cutscenes` | 17 | 过场相机 |
| `systems/music` | 15 | 音乐分区与淡入淡出 |
| `mixin` | 13 | 13 个客户端 mixin |
| `systems/hud` | 11 | GUI layer 注册 + bossbar 子系统（577 行） |
| `systems/particle` | 19 | 粒子发射器 |
| `systems/config` | 9 | 反射式 JSON 配置 |
| `systems/shake` / `impact_frames` / `post_shaders` / `render_types` / `entity` | 8/3/5/9/8 | 屏幕震动、打击帧、后处理、渲染类型、招式链 |
| 根包 + `network` + `nbt` + `data_structures` + `commands` + `test` | 8/5/6/4/2/2 | 入口、网络层、NBT 反射、数据结构、命令、测试 |

最大源文件（前 12）：`util/rendering/FDRenderUtil.java` 627、`systems/screen/default_components/text/FDTextBox.java` 604、`util/rendering/renderers/ShapeOnCurveRenderer.java` 528、`util/math/FDMathUtil.java` 472、`systems/simple_screen/FDWidget.java` 422、`util/FDByteBufCodecs.java` 404、`systems/bedrock/animations/Animation.java` 306、`systems/screen/FDScreen.java` 291、`systems/bedrock/animations/animation_system/AnimationTicker.java` 275、`shunting_yard/ShuntingYard.java` 267、`systems/entity/action_chain/AttackChain.java` 261、`systems/bedrock/models/FDCube.java` 257。

**源码树不完整（重要）**：`src/main/resources` 只有 3 个文件（`fdlib.mixins.json`、`META-INF/accesstransformer.cfg`、`META-INF/neoforge.mods.toml`），**无 assets、无 lang、无 shader，且无 `src/generated/resources` 目录**；而代码运行期明确要读 `assets/<ns>/bedrock/models/*.geo.json` 与 `bedrock/animations/*.json`（`init/FDModEvents.java:61,65,81,84`）、`textures/gui/effects/broken_screen_*.png`（`systems/broken_screen_effect/ShatteredScreenSettings.java:24-28`）、`shaders/post/impact_frame.json`（`systems/impact_frames/ImpactFramesHandler.java:35`）。本检出**无法运行**，只能读结构。

## 3. 入口与注册

入口 `FDLib.java:16-43` 只做两件事：存 MOD_ID + 把 13 个 `DeferredRegister` 挂到 mod 总线（`FDSounds.SOUNDS.register(bus)` 那一行被注释掉了，`:32`），业务逻辑全在静态订阅者里。

```java
@Mod(FDLib.MOD_ID)
public class FDLib {
    public static final String MOD_ID = "fdlib";
    public static ResourceLocation location(String loc){
        return ResourceLocation.fromNamespaceAndPath(MOD_ID,loc);
    }
    public FDLib(IEventBus bus, ModContainer modContainer) {
        FDItems.ITEMS.register(bus);  FDBlocks.BLOCKS.register(bus);
        FDConfigs.CONFIGS.register(bus);  FDRenderTypes.RENDER_TYPES.register(bus);
        FDScreenEffects.SCREEN_EFFECT_TYPES.register(bus);  /* ...共 13 行... */
    }
```

- 自定义注册表：`systems/FDRegistries.java:23-41` 声明 7 个 `ResourceKey<Registry<T>>` + `RegistryBuilder<>(key).sync(true).create()`，`:43-52` 在 `NewRegistryEvent` 里逐个 `event.register(...)`。`boss_bars` 就是其中之一（`:26,38`）。
- 事件订阅点清单（全部走 `@EventBusSubscriber` 静态类，不是构造器里手写）：`RegisterGuiLayersEvent`（`systems/hud/FDHuds.java:21`）、`NewRegistryEvent`（`systems/FDRegistries.java:44`）、`RegisterPayloadHandlersEvent`（`network/PacketHandler.java:25`）、`FMLCommonSetupEvent`（`init/FDModEvents.java:35`）、`ServerStartedEvent`/`PlayerLoggedInEvent`（`init/FDGameEvents.java:35,46`）、`ClientTickEvent.Pre/Post`（`systems/hud/bossbars/FDBossbars.java:23`、`systems/screen/screen_effect/ScreenEffectOverlay.java:34`、`ClientMixinHandler.java:43`）、`ClientPlayerNetworkEvent.LoggingOut`（`FDBossbars.java:39`）、`RegisterCommandsEvent`（`commands/FDCommandsRegistry.java:40`）、以及 `@SubscribeEvent` 订阅**库自己定义的 event**（`FDPostShaderInitializeEvent`、`FDRenderPostShaderEvent.Level/Screen`，见 `systems/impact_frames/ImpactFramesHandler.java:32,48`）。
- 一处不一致值得注意：`FDHuds.java:14`、`FDRegistries.java:20`、`PacketHandler.java:21`、`FDModEvents.java:30` 显式写 `bus = EventBusSubscriber.Bus.MOD`；而 `init/FDClientModEvents.java:38` 订阅的全是 mod 总线事件（`RegisterKeyMappingsEvent`/`RegisterClientReloadListenersEvent`/`RegisterParticleProvidersEvent`/`EntityRenderersEvent`）却没写 `bus`，`ScreenEffectOverlay.java:18` 则显式写 `Bus.GAME`。注解默认落到哪条总线属 NeoForge 侧行为（本仓库外，**未验证**），至少写法不统一。

## 4. 核心系统

### 4.1 Bossbar：一条 bar 怎么脱离实体存在（回答问题①）

`systems/hud/` 共 577 行（其中 `bossbars/` 546 行），数据表示只有三层：

- **客户端对象**：`systems/hud/bossbars/FDBossBar.java:12-35` 是抽象类，字段仅 `UUID uuid`、`int entityId`、`float percentage`；抽象方法四个：`render(GuiGraphics,float)`、`tick(float topOffset)`、`height()`、`hanldeBarEvent(int eventId,int data)`（作者拼错了 handle，`:35`）。实体只是**可选上下文**：`getEntityId()` 注释"May return -1 which means no entity is bound"（`:50-55`），`getEntity()` 每次渲染现场用 `FDClientHelpers.getClientLevel().getEntity(this.entityId)` 查（`:57-65`），查不到返回 null——bar 不依赖实体存活。
- **生命周期与 ID**：ID 由服务端决定并一次定终身——`FDServerBossBar.java:27-37` 两个构造器：绑实体时 `uuid = entity.getUUID()`，不绑时 `uuid = UUID.randomUUID()`。注册即"把这个玩家加进 bar"：`addPlayer` 发 `AddPlayerToBossBarPacket`（`:46-49`），客户端用注册表里的工厂 new 出 bar 并 `setPercentage` 后入表（`packets/AddPlayerToBossBarPacket.java:51-56`）；销毁只有 `removePlayer`→`RemovePlayerFromBossBarPacket`→`FDBossbars.removeBossBar(uuid)`（`FDServerBossBar.java:51-54`、`packets/RemovePlayerFromBossBarPacket.java:32-34`）。**可见性动态开关完全交给宿主**：库不做距离/维度/战斗判定，也没有 bar 过期 TTL；兜底只有断线清空（`FDBossbars.java:39-41`）与 `level == null` 清空（`:24-27`）。服务端若忘记 `removePlayer`（比如 BOSS 直接死掉），客户端这条 bar 会一直挂到退服——**这是给 Colossus 的第一个坑位**。
- **容器与排序**：`FDBossbars.java:19` 一个 `LinkedHashMap<UUID,FDBossBar>`（声明类型写成 `HashMap`，靠运行时类型保序）。排序 = 插入顺序，垂直堆叠。布局在两处各算一遍同样的累加：tick 里 `offs = calculateBossBarsOffset(); for(bar) { bar.tick(offs); offs += bar.height(); }`（`:29-34`），渲染里 `matrices.translate(width/2, baseOffset, 0)` 然后每条 `translate(0, height, 0)`（`FDBossBarsOverlay.java:29-37`）。没有优先级/分组/左右分栏，也没有条数上限。
- **和原版血条共存**：`FDBossBarsOverlay.java:42-49` 用 AT 读原版 `BossHealthOverlay.events.size()`（`accesstransformer.cfg:21`），算 `3 + size*25` 作为自己的顶部偏移，把自己的 bar 堆在原版血条之下；layer 用 `event.registerAboveAll(fdlib:boss_bars, new FDBossBarsOverlay())` 注册（`systems/hud/FDHuds.java:23`）。
- **动画/lerp 位置**：只在客户端，`FDBossBarInterpolated.java`。`setPercentage` 变化时把 `currentInterpolationTime = interpolationTime`（`:46-56`），每 tick 递减 1（`:40-42`），渲染时 `p = FDEasings.easeIn(clamp(currentInterpolationTime - partialTicks,0,N)/N)` 再 `interpolatedPercentage = FDMathUtil.lerp(new, old, p)`（`:26-35`），`lerp` 就是 `v1+(v2-v1)*p`（`util/math/FDMathUtil.java:27-29`），`easeIn(p)=p*p`（`util/rendering/FDEasings.java:49-51`）。**关键性质：倒计时按客户端 tick 计，不用 wall-clock**，所以暂停即冻结、掉帧不失真——与调研里 Draconic Evolution 的"客户端 100ms 真实时间 lerp"是两条路线。中途再次掉血时 `oldPercentage` 从当前插值位置续接（`:48-52`），不会跳回旧值。
- **服务端→客户端的旁路通道**：`broadcastEvent(int eventId,int data)`（`FDServerBossBar.java:56-60`）→ `BossBarEventPacket` → `bar.hanldeBarEvent(event,data)`（`packets/BossBarEventPacket.java:43-48`）。这是一个**语义完全留给宿主的两个 int**，多阶段切换、护盾破、点名提示都能用它，且不用新增包类型——本仓库最省事也最值得抄的一处解耦。
- **样式/贴图数据化：没有**。库内 `FDBossBar` 零子类、零贴图、零 JSON/Codec；`FDRegistries.BOSS_BARS`（`:38`）在本仓库里没有任何条目被注册（grep 只见声明与 `event.register`），外观 100% 由宿主的 `render()` 硬编码。横向综述把它归为"裸 bar 库"是准确的。

### 4.2 一个"系统"在 FDLib 里是什么单位（回答问题②）

`systems/` 下**没有共同骨架类、没有系统注册表、没有 FDSystem 接口**（该目录唯一文件是 `systems/FDRegistries.java`）。但反复出现三种可命名的骨架：

- **骨架 A：一次性效果（事件式）**——`systems/screen/screen_effect/` 六文件最规整：注册表条目 `ScreenEffectType<D extends ScreenEffectData, S extends ScreenEffect<D>>` 只装两样东西：`StreamCodec dataCodec` 与 `ScreenEffectFactory factory`（`ScreenEffectType.java:6-18`）；一个包把 type 的注册表 key 与 data 一起发（`SendScreenEffectPacket.java:29-55`）；客户端 `type.factory.create(...)` 后 `ScreenEffectOverlay.addScreenEffect(effect)` 塞进静态 list（`:58-61`）；overlay 同时是 `LayeredDraw.Layer` 渲染者 + `ClientTickEvent.Post` 回收者（`ScreenEffectOverlay.java:19,24-31,34-47`）。生命周期是 `inTime/stayTime/outTime` 三段，并直接给出 `getInTimePercent/getStayTimePercent/getOutTimePercent` 三个 0..1 缓动进度（`ScreenEffect.java:31-72`）。**这套"in/stay/out + percent"正是 bossbar 缺的入场/退场动画形状**——两者在同一个库里，可以合体。
- **骨架 B：每对象常驻 system（侧别分裂）**——`AnimationSystem.java:14-18` 持 `Map<String,AnimationTicker>` + `Map<String,Float> variables`，`:24` tick，`:104-126` startAnimation、`:128-150` stopAnimation、`:153-156` setVariable，四个 `onXxx` 抽象钩子（`:181-184`）；`EntityAnimationSystem.create(entity)` 按 `level().isClientSide` new 出 Clientside/Serverside 子类（`EntityAnimationSystem.java:23-29`），服务端子类的钩子就是发包（`ServersideEntityAnimationSystem.java:17-36` 全用 `PacketDistributor.sendToPlayersTrackingEntity`），客户端子类钩子全空实现（`ClientsideEntityAnimationSystem.java:12-31`）。`ModelSystem` 同构（`EntityModelSystem.java:30-36` 的 `create` + `:26-28` 的 `asServerside()` 强转）。
- **骨架 C：服务端聚合管理器 + 轮询差分**——`systems/music/music_areas/FDMusicArea.java`：服务端持 `List<UUID> playersInside`，每 `playerDetectionFrequency`(默认 5) tick 做一次集合差分，进入/离开才发包（`:21-71`），另有"没人就倒计时自毁"的 `autoDeletionTicker`（`:30,83-98`）。
- 搬给 Colossus 的可行性：**骨架 A + C 可以直接搬**（各约 60~100 行，几乎不碰 FDLib 其它代码，只依赖 `FDPacket` 与一个自定义注册表）；**骨架 B 不建议整搬**，它假设"每对象一个 model system"，Colossus 血条层用不上双层侧别强转，用 A 的 type+data+codec 形状即可。宿主接入方式在 A/B/C 三种里都是同一句话：**往 FDLib 声明的自定义注册表里注册条目，然后按 UUID 建立服务端句柄 ↔ 客户端实例的映射**。

### 4.3 网络层（回答问题③）

`network/` 只有 5 文件、约 200 行：

- `FDPacket` 抽象类 `implements CustomPacketPayload`，声明 `write(RegistryFriendlyByteBuf)` + `clientAction(IPayloadContext)` + `serverAction(IPayloadContext)`，`type()` 首次调用时反射读自己类上的 `@RegisterFDPacket` 注解值并把 `Type` 缓存进静态 `REGISTERED_TYPES`（`network/FDPacket.java:12-45`，注解定义 `network/RegisterFDPacket.java:11-14`）。
- 注册：`PacketHandler.java:25-29` 拿 `event.registrar(FDLib.MOD_ID).versioned("1").optional()`，`:30` 用 `FDHelpers.getAnnotatedClasses(RegisterFDPacket.class)` **扫全部 mod 的 ModFileScanData**（`FDHelpers.java:133-151`）找出所有带注解的类，`:40-44` 反射找 `(FriendlyByteBuf)` 或 `(RegistryFriendlyByteBuf)` 构造器，`:47-59` 用它拼一个 `StreamCodec.of(write, decode-反射)`，`:62-70` `registrar.playBidirectional(type, codec, (p,c)-> c.enqueueWork(侧别分发))`。
- 与 NeoForge 原生 `PayloadRegistrar` 的差异：**注册通道、版本化、`enqueueWork` 都还是原生的**（它没有另造网络层，只是把"每个 payload 要写一次 type+StreamCodec+handler"三件事压成一个注解 + 一对方法）。代价是：读侧走反射 `newInstance`（编译期不检查构造器存在）；写侧 `write(buf)` 与读构造器必须人工配对，`StreamCodec` 不再是声明式组合子；全部包一律 `playBidirectional`（客户端专用包也注册了服务端分支，见各 `serverAction` 空方法，如 `packets/BossBarEventPacket.java:50-53`）；`REGISTERED_TYPES` 以注解字符串为 key 复用 `Type`（`FDPacket.java:35-45`），两个 mod 撞名会在原生 registrar 处炸；命名空间靠约定手写 `"fdlib:xxx"`（如 `packets/AddPlayerToBossBarPacket.java:18`），宿主用自己的前缀即可，这也意味着**下游 mod 的包能被 FDLib 一并自动注册**。本仓库共 39 个 `@RegisterFDPacket`（grep 实测）。
- 另有一层客户端集中分发：包只负责解码，动作全转调 `FDClientPacketExecutables` 的静态方法（`FDClientPacketExecutables.java:30-70`），便于宿主复用同一套动作。

### 4.4 配置系统（反射式 JSON config）

`JsonConfig.java:45-78` 负责读盘/建文件/只在有变化时回写（`changesWereMade` 一路从 `parseJson` 返回）；`ReflectiveJsonConfig.java:30-42` 在 `FMLCommonSetupEvent` 阶段递归"记住默认值"（`init/FDModEvents.java:37-42`），`:64-72` 把 `@Comment` 注解读成 JSON 里的 `_comment_<字段>` 键（玩家手改文件能看到说明），`:92-125`/`:127-228` 对 int/float/double/String/boolean/enum/嵌套对象分别处理，坏值 catch 后回退默认并把 `changesWereMade=true`。同步：`FDGameEvents.java:34-43` 服务器启动加载全部，`:45-51` 玩家登录时发 `JsonConfigSyncPacket`（非客户端配置全量 JSON 字符串）+ `TriggerClientsideConfigReloadPacket`；`commands/FDCommandsRegistry.java:75-99,148-155` 提供 `/fdlib reload configs|clientsideConfigs|models|animations`（后两者仅开发环境，见 `:130,142` 的 sendFailure）。宿主示例：`FDClientConfig.java:10-16` 一个 `@ConfigValue boolean impactFramesEnabled`，被 HUD 用来开关特效（`systems/impact_frames/ImpactFramesHandler.java:90`）；`systems/config/test/TestConfig.java:15-52` 演示 `ManualSerializeable` 手写 `Item` 字段。

### 4.5 AttackChain：BOSS 招式序列机（`systems/entity/action_chain/`，本库对 Colossus 最值钱的一块）

`AttackChain.java:16-26` 持 `Map<String,AttackExecutor>`、`List<Pair<Integer优先级, AttackOptions>>`、`alwaysTryCast` 列表、`Queue<String> chain`、`currentAttack`。`tick()`（`:83-102`）：链空且无当前招式就 `buildQueue()`，否则执行 `currentAttack.attack.execute(inst)`，返回 false 时"stage 未变才 +1 tick"（`:94-96`，配合 `AttackInstance.nextStage()` 重置 tick 并 stage++，`AttackInstance.java:18-21`）——**招式自己用 stage 表达阶段，链负责计时**，这是多阶段 BOSS 的现成形状。`buildQueue()`（`:160-190`）按优先级分组、组内**洗牌逐个入队**，`addOptionsToQueue`（`:192-214`）递归展开 pre/next 与嵌套 `AttackOptions`，权重抽取直接用原版 `WeightedRandomList`（`AttackOptions.java:53-66`）。打断：`attackListener` 是 `Function<String,AttackAction>`，每poll一个招式先问宿主 PROCEED/SKIP/WAIT（`:121-135`，枚举 `AttackAction.java:3-7`）。注册：`registerInClassAttacks(entityClass)` 反射实体类上的 `@Attack("名字")` 方法（`:34-51`，注解 `Attack/Attack.java:10-12`）。**持久化**：`save/load(CompoundTag)` 把整条 `chain` 和 `currentAttack{name,tick,stage}` 写进 NBT（`:228-260`），BOSS 区块卸载/重启能续招。本库内**没有任何使用者**（grep `AttackChain` 除自身目录外 0 命中），也没有示例。

### 4.6 HUD 全家桶（血条之外）

`FDHuds.java:21-26` 一次注册三个 layer（`boss_bars` aboveAll、`screen_effect` aboveAll、`shattered_screen` below boss_bars）。`impact_frames` 是黑白闪打击帧：静态 `Queue<ImpactFrame>` + 当前帧倒计时轮转（`ImpactFramesHandler.java:25-27,59-87`），shader 通过自定义 `FDPostShaderInitializeEvent` 注册（`:32-40`），由 `FDRenderPostShaderEvent.Level` 驱动 `PostChain.process`（`:48-57`）。后处理总管家 `FDPostShadersHandler.java:27-47` 每 tick 检查窗口尺寸变化并 resize 所有 `PostChain`；`GameRendererMixin.java:36-44` 在 `RenderTarget.bindWrite` 前与 `render` TAIL 分别 post Level/Screen 两个自定义事件；`FDPostShadersReloadableResourceListener.java:38-67` 在资源重载时 close+clear+重 post 初始化事件，**并把每个 shader 的加载异常收集起来一次性抛出**。屏幕震动更简单：`ClientMixinHandler.java:40-55,72-86` 静态 list + 注入 `bobHurt@HEAD`，用 `renderShake` 布尔位保证只作用于世界不影响手持物。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 自定义包：39 个 `@RegisterFDPacket`，每个约 40~65 行（write + buf 构造器 + clientAction + 空 serverAction）。跨端形态分两类：**寻址 UUID**（bossbar 全家，`BossBarEventPacket.java:36-40`）与**寻址 int entityId**（bedrock 动画/附件，`packets/SyncEntityAnimationsPacket.java:53-61`，实体 id 靠 `level.getEntity(id)` 解析，见 `FDClientPacketExecutables.java:68-70`）。带注册表对象的包（`SendScreenEffectPacket.java:46-55`、`AddPlayerToBossBarPacket.java:41-46`）只发 **registry key 的 ResourceLocation**，客户端查表还原——这是它们共同的"数据化"手法。
- 序列化：`util/FDByteBufCodecs.java` 自建 `RESOURCE_LOCATION/UUID/VEC3/BLOCK_POS/COLOR` 常量（`:22,26,38,56,74`）与 **7~12 元的 `composite` 重载**（`:86,129,176,227,282,341`），补上原版 `ByteBufCodecs` 只有到 6 元的缺口；`ShatteredScreenSettings.java:30-40` 用 8 元 composite 一行做完一个 HUD 设置对象的 codec。Codec（`com.mojang.serialization`）只出现在 `ReflectiveJsonConfig.java:6-8` 的 import 与粒子 `MapCodec`（`init/FDParticles.java:24,36,49`）；**没有 RecordCodecBuilder 驱动的数据类型**，Bedrock 模型/动画走 Gson + 手写解析（`init/FDModEvents.java:65-70,84-85`）。
- 配置：见 4.4。数据驱动面：床岩 `.geo.json`/`.animation.json`（运行期反射加载 + `/fdlib reload models|animations` 热重载）、`@ConfigValue`+`@Comment` 反射式 JSON、注册表键寻址的 payload。
- datagen：**无**。全仓 grep `GatherDataEvent`/`DataGenerator` 只命中 `systems/trails/FDTrailDataGenerator.java`，那是拖尾网格顶点生成器（`:12-28` 的 `positionExtractor`/`maxPointsInTrail`），与 FML datagen 无关。`build.gradle` 也没有 datagen 专属配置块，只留了 `runData` 风格的 `runs.data` programArguments。
- **带宽纪律（回答问题④）**：做对的——`FDMusicArea.java:42` 每 5 tick 才做一次玩家检测（`playerDetectionFrequency`）、`:48-54` 只在"之前不在集合里"时发包（边沿触发）、`:59-62` 用集合差分算离开者，这是全库唯一的增量同步范式。做坏/没做的——(1) `FDServerBossBar.java:39-44` `setPercentage` **无脏检查、无节流**：每次调用都遍历 `players` 逐人 `sendToPlayer`，BOSS 每 tick 掉血就是 N 人 N 包，且不用 `sendToPlayersNear`；(2) `JsonConfigSyncPacket.java:22-31` 构造时把**所有非客户端配置的完整 JSON 字符串**装进列表，登录全量重发，无 hash/版本比对；(3) `FDMusicArea.java:25,34-39` 的 `uuid` 字段在构造器里从未赋值，`getUUID()`（`:104-106`）恒为 null——说明这条链没被真正跑通过；(4) `ImpactFramesHandler.java:101-103` 的 `beforePostEffect()` 第一行就是 `if (true) return;`，后面 40 行 `glReadPixels` 九点采样（`:105-144`）是**永久死代码**；(5) `EntityStartAnimationPacket.java:48-49` 的 `serverAction` 里留着 `System.out.println("Wtf?")`；(6) `init/FDClientModEvents.java:69-164` 把一段带几十个注释行的 demo 渲染代码提交进库，`FDImpl.java:3-13` 是一个纯彩蛋嵌套类（Rickroll 命名），`systems/config/test/TestConfig.java:27` 字段名叫 `sausage`——库的工程纪律偏个人项目。

## 6. Mixin

13 个，全部在 `mixin/`，配置 `src/main/resources/fdlib.mixins.json`：common 只有 `KeyboardInputMixin`（`:6-8`），client 12 个（`:10-23`）。目的是把"渲染时机"和"声音/网络内部状态"抠出来，而不是改逻辑：

| mixin | 注入点 | 目的 |
|---|---|---|
| `GameRendererMixin.java:21,26,31,36,41` | `bobHurt@HEAD`、`renderItemInHand@HEAD`、`renderLevel@HEAD`、`render` 的 `RenderTarget.bindWrite@BEFORE`、`render@TAIL` | 屏幕震动作用域开关 + post 库自己的 `FDRenderPostShaderEvent.Level/Screen` |
| `ClientMixinHandler`（非 mixin，被上表调用） | — | 震动实例表与 tick 回收 |
| `AbstractContainerScreenMixin.java:19,27` | `renderSlot` 的 `renderSlotContents` 前/后 | 槽位装饰/覆盖渲染（screen 框架） |
| `ItemInHandLayerMixin.java:22,31` / `ItemInHandRendererMixin.java:20,28` / `ItemEntityRendererMixin.java:20,28` | `renderItem` 前后成对注入 | 手持/掉落物上挂基岩动画模型 |
| `SoundEngineMixin.java:17,26` / `ChannelAccessMixin.java:19` / `ChannelMixin.java:20,25` | `play`、`stopAll`、`release`、`removeProcessedBuffers`、`stop` | 跟踪 OpenAL channel，实现"耳边音"与音乐淡入淡出 |
| `ParticleEngineMixin.java:22` | `render` 中 `BufferUploader.drawWithShader` BY 2 | 按粒子类型插入自绘批次 |
| `LocalPlayerMixin.java:15` / `MouseHandlerMixin.java:13` / `KeyboardInputMixin.java:14` | `isControlledCamera@HEAD`、`turnPlayer@HEAD`、`tick@TAIL`（cancellable） | 过场期间接管玩家输入与镜头 |
| `MinecraftMixin.java:17` | `onResourceLoadFinished@TAIL` | 加载完成后触发库初始化 |

配套 AT（`accesstransformer.cfg`）里与本报告主题最相关的一条是 `:21 public net.minecraft.client.gui.components.BossHealthOverlay events`——4.1 的堆叠偏移靠它；另有 `:20 DeltaTracker$Timer deltaTickResidual`、`:16,17 GameRenderer postEffect/effectActive`、`:22,23 SoundManager soundEngine 与 SoundEngine instanceToChannel`、`:26 PostChain passes`。

## 7. 值得学的 5 条

1. **两 int 旁路通道**：`systems/hud/bossbars/FDServerBossBar.java:56-60` + `packets/BossBarEventPacket.java:36-48` —— 服务端 `broadcastEvent(id,data)`、客户端 `hanldeBarEvent(id,data)`，宿主用枚举自行解释（阶段号、破盾、点名目标 slot）。值得抄是因为它让血条子系统**不必为每种新表现加一个新包类**，Colossus 的多阶段血条、护盾条、机制提示能共用一条协议。
2. **tick 倒计时的补血条插值**：`systems/hud/bossbars/FDBossBarInterpolated.java:40-56` —— 变化时 `currentInterpolationTime=N`、每 tick -1、渲染时 `lerp(new, old, easeIn(remaining/N))`，中途再次变化从当前插值点续起。值得抄：不用 wall-clock，暂停/掉帧/慢速服务器下表现一致，比真实时间 lerp 更省事也更不容易出错。
3. **in/stay/out 三段生命周期 + 三个 percent 助手**：`systems/screen/screen_effect/ScreenEffect.java:31-72` 配 `ScreenEffectInstance.tick()`（`ScreenEffectInstance.java:14-20`）与 overlay 的迭代器回收（`ScreenEffectOverlay.java:34-47`）。值得抄：把它套到 bar/护盾条/参战标记上，正好补上 FDLib bossbar 没有入场退场动画的缺口，而且是同一库内已经跑通过的形状。
4. **注册即差分的可见性管理**：`systems/music/music_areas/FDMusicArea.java:41-71` —— 服务端持 `List<UUID> playersInside`，每 5 tick 算一次进/出集合并只对差分发包，配 `:83-98` 的空集合倒计时自毁。值得抄：Colossus 的"参战者标记/距离内才显示血条"就应该是这个形状，且自毁计时器正好治 4.1 的"服务端忘了 remove 导致 bar 永挂"。
5. **招式链的可持久化状态机**：`systems/entity/action_chain/AttackChain.java:83-102`（execute 返回 false + `stage` 未变才 `tick++`）、`:160-190`（同优先级组洗牌）、`:228-260`（NBT 存 queue + currentAttack{name,tick,stage}）。值得抄：BOSS 引擎最难的两件事——"招式跨 tick 推进"和"重启续招"——它用不到 30 行给出了答案，且不依赖 FDLib 其它部分，可整包搬（只需把 `Pair` 换掉：它用的是 `com.finderfeed.fdlib.data_structures.Pair`，`AttackChain.java:3`）。

结论——给 Colossus 的 bossbar/HUD 层 3 条直接可抄的形状（问题⑥）：

- **多阶段血条**：抄 `FDBossBarInterpolated.java:40-56` 的"tick 倒计时 + `lerp(new, old, easeIn(remaining/N))`"做主血条的延迟段，阶段切换不要新建 bar，用 `FDServerBossBar.java:56-60` 的 `broadcastEvent(阶段号, 0)` 走 `BossBarEventPacket.java:43-48` 通知客户端改样式；再补 `ScreenEffect.java:31-72` 的 in/stay/out 三段，让阶段换条有淡入淡出（FDLib 自己没做这一步）。
- **护盾/副资源条**：抄 `FDBossBar.java:26-35` 的四方法契约——`height()` 决定堆叠占位（`FDBossbars.java:29-34` 与 `FDBossBarsOverlay.java:29-37` 各累加一次），主血条与护盾条就是同一个 `LinkedHashMap` 里相邻的两条 bar（插入顺序即视觉层级），差别只在 `percentage` 的语义（剩余护盾/满盾）。若要把两者画进同一条视觉条里，就只注册 1 个工厂、把护盾值改用 `hanldeBarEvent(护盾事件号, 百分比*100)` 喂进来——载荷只有 uuid + 两个 int（`packets/BossBarEventPacket.java:36-40`），够用。
- **参战者标记/可见性**：抄 `FDMusicArea.java:41-71` 的"每 5 tick 检测 + 集合差分 + 只对变化者发包"，服务端把 `playersInside` 换成"参战集合"，`addPlayer/removePlayer`（`FDServerBossBar.java:46-54`）正好是它的落点；再抄 `:83-98` 的空集合倒计时自毁，避免 FDLib 自身的"服务端忘 remove → bar 挂到退服"缺陷（`FDBossbars.java:39-41` 只在断线时清空）。

## 8. 公开 API（作为被依赖库）

- **接入前置事实**：许可证禁止把库嵌进别人的 jar（`LICENSE.txt:5,:13`），且没有公共 maven（`build.gradle:114` 只发到项目内 `repo/` 目录）。所以现实中只能像璇穹之歌那样**把 FDLib 作为独立 mod 与自己的 mod 一起分发**，开发期用本地 file repo 或 flatDir：

```groovy
// 宿主 build.gradle（推断写法；仓库里没有宿主示例，未在 CI 验证）
repositories { maven { url = uri("file:///<FDLib 检出目录>/repo") } }
dependencies { implementation "com.finderfeed.fdlib:fdlib:1.0.9-1.21.1" }
// neoforge.mods.toml 里加 [[dependencies.<myMod>]] modId="fdlib" type="required" versionRange="[1.0.9,)" ordering="NONE" side="BOTH"
```

- 入口/门面包：`com.finderfeed.fdlib.FDLibCalls`（表现层动作总入口：过场、粒子发射器、打击帧、屏幕效果、玩家位移，`FDLibCalls.java:40-137`）、`FDLib.location()`、`FDClientHelpers`/`FDHelpers`、`util.math.FDMathUtil`、`util.rendering.FDRenderUtil`/`FDEasings`、`util.FDByteBufCodecs`。
- 扩展点（宿主该实现/注册的接口与抽象类）：

| 扩展点 | 位置 | 宿主要做的事 |
|---|---|---|
| `FDBossBarFactory<T>` / `FDBossBar` / `FDBossBarInterpolated` | `systems/hud/bossbars/FDBossBarFactory.java:5-8`、`FDBossBar.java:12-35`、`FDBossBarInterpolated.java:11-23` | 子类写 `render/tick/height/hanldeBarEvent`，工厂注册进 `FDRegistries.BOSS_BARS` |
| 自定义注册表 `fdlib:boss_bars` | `systems/FDRegistries.java:26,38,47` | `DeferredRegister.create(FDRegistries.BOSS_BARS, 宿主 modid)`（照 `init/FDModels.java:12` 与 `init/FDScreenEffects.java:16` 的写法） |
| `FDPacket` + `@RegisterFDPacket` | `network/FDPacket.java:12-33`、`RegisterFDPacket.java:11-14` | 宿主的包**会被 FDLib 自动扫描注册**（`FDHelpers.java:133-151` 扫全部 mod 的 scan data），只需带注解 |
| `ScreenEffectType` / `ScreenEffect` / `ScreenEffectData` / `ScreenEffectFactory` | `systems/screen/screen_effect/ScreenEffectType.java:16`、`ScreenEffect.java:21` | 注册 type（factory + data StreamCodec）后进而能用 `FDLibCalls.sendScreenEffect` |
| `JsonConfig` / `ReflectiveJsonConfig` + `@ConfigValue` / `@Comment` / `ManualSerializeable` | `systems/config/JsonConfig.java:84-86`、`ReflectiveJsonConfig.java:21` | 注册进 `fdlib:configs` 即自动读盘/同步/热重载 |
| `FDEntity` / `FDMob` / `AnimatedObject` / `AnimationSystem` 钩子 | `systems/bedrock/.../entity/FDEntity.java:12-19`、`AnimationSystem.java:181-184` | 实体继承 `FDMob`/`FDEntity`，或实现 `AnimatedObject` 自挂 model system |
| 库自定义 event：`FDPostShaderInitializeEvent`、`FDRenderPostShaderEvent.Level/Screen` | `systems/post_shaders/FDPostShaderInitializeEvent.java:19`、`FDRenderPostShaderEvent.java:19,25,31` | 宿主 `@SubscribeEvent` 即可注册自己的 PostChain 与渲染时机 |
| `@Attack` + `AttackChain` | `systems/entity/action_chain/Attack.java:10-12`、`AttackChain.java:34-51` | 招式写成实体方法，`registerInClassAttacks` 自动收集 |

- **bossbar 最小接入示例（三步；仓库内无可运行示例——`FDRegistries.BOSS_BARS` 在本库零条目，以下按 `FDBossbars.java` / `FDServerBossBar.java` / `packets/AddPlayerToBossBarPacket.java:51-56` 的调用形状推出，未在运行期验证）**：

```java
public class MyBar extends FDBossBarInterpolated {                       // 形状源自 FDBossBarInterpolated.java:11-23
    public MyBar(UUID u, int entityId){ super(u, entityId, 20); }        // 20 tick 补血条动画
    @Override public float height(){ return 22f; }                       // 参与 FDBossbars.java:29-34 的堆叠
    @Override public void renderInterpolatedBossBar(GuiGraphics g, float pt, float pct){ /* 自绘 */ }
    @Override public void hanldeBarEvent(int id, int data){ /* 阶段/护盾语义 */ }
}
public static final DeferredRegister<FDBossBarFactory<?>> BARS =
    DeferredRegister.create(FDRegistries.BOSS_BARS, "colossus");          // 注册方式同 init/FDModels.java:12
public static final DeferredHolder<FDBossBarFactory<?>, FDBossBarFactory<MyBar>> MY =
    BARS.register("my_bar", () -> (uuid, entityId) -> new MyBar(uuid, entityId));  // FDBossBarFactory.java:5-8 是单方法接口
// 服务端：var bar = new FDServerBossBar(MY, bossEntity);                  // FDServerBossBar.java:27-31
// bar.addPlayer(p);  bar.setPercentage(hp/max);  bar.broadcastEvent(1, phase);  bar.removePlayer(p);
```

- 版本耦合（回答问题⑤）：真实目标是 **NeoForge 21.1.211 / MC 1.21.1 / Java 21**（`gradle.properties:5,8`、`build.gradle:28`）。以下为 Forge 1.20.1 借用时的逐条改写清单。
- 必须换掉的（HUD 侧）：`LayeredDraw.Layer` + `DeltaTracker` + `RegisterGuiLayersEvent`（`FDBossBarsOverlay.java:5,8,10,15`、`FDHuds.java:12,21-26`）在 Forge 1.20.1 全不存在，要改成叠加层/`RenderGuiOverlayEvent` 系的等价时机（1.20.1 样本走 `CustomizeGuiOverlayEvent.BossEventProgress`，见横向综述第 26 行）。原版 `BossHealthOverlay` 的字段在 1.20.1 是否仍名为 `events` **未验证**，别照抄 `accesstransformer.cfg:21`——能用 Forge 侧事件计数替代就不要 AT。
- 必须换掉的（网络侧）：`CustomPacketPayload`/`Type`/`IPayloadContext`/`RegisterPayloadHandlersEvent`/`registrar().versioned().optional()`/`PacketDistributor.sendToPlayer(player,payload)`（`PacketHandler.java:12-14,25-29,62`、`FDPacket.java:6,20-21`）在 Forge 1.20.1 全部换成 `EventNetworkRegistry` + `SimpleChannel.registerMessage` + `IMessage`。好消息：`FDPacket` 的 `write(buf)` + `(Buf)` 构造器形状几乎 1:1 映射到 `toBytes/fromBytes`，而注解扫描用的 `ModList.getAllScanData()`（`FDHelpers.java:133-151`）Forge 侧也有——**"一个注解自动注册全部包"这一层是能搬的**。
- 必须换掉的（杂项）：`net.neoforged.*` import 与 `@EventBusSubscriber(bus=...)`（`FDRegistries.java:14-17,20`）→ `net.minecraftforge.*` 与 `Mod.EventBusSubscriber.Bus.MOD`；`ResourceLocation.tryBuild/parse/fromNamespaceAndPath`（`FDRegistries.java:32`、`SendScreenEffectPacket.java:34`、`FDLib.java:25`）→ 1.20.1 的 `new ResourceLocation(ns,path)`；Java 21 API `List.getFirst()/getLast()`（`FDLibCalls.java:83,85`）在 Java 17 编译不过，需退回 `get(0)`/`get(size()-1)`。
- 可以原样搬的：`FDServerBossBar`↔`FDBossBar` 的 UUID + `int entityId` 双寻址（`FDBossBar.java:57-65` 靠 `level.getEntity(id)`，1.20.1 同样成立）、tick 倒计时插值（只依赖 `Mth.clamp` 与浮点 lerp）、`AttackChain` 全套（含 NBT save/load）、`FDMusicArea` 的差分形状、以及 `ScreenEffect` 的 in/stay/out 生命周期。
