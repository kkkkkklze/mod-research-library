# Luke100000/ImmersiveMelodies 源码分析报告

## 1. 基本信息

- Mod 名：Immersive Melodies；mod_id `immersive_melodies`；作者 Conczin（`group_id=net.conczin`）。
- 目标版本：MC **1.20.1**，加载器 **fabric + forge 双端**（`gradle.properties`: `enabled_platforms=fabric,forge`）；Fabric Loader 0.14.21 / API 0.83.1、Forge 47.0.3。
- Gradle：Architectury 三模块（`common` / `fabric` / `forge`），依赖 cloth-config 11.0.99、mod-menu 7.0.1；Fabric 侧用 `yarn_mappings=1.20.1+build.2`（但源码是 Mojang 名，靠 Architectury loom 统一）。
- `common/build.gradle` 只 `modImplementation fabric-loader`（借 @Environment 注解），并声明 `accessWidenerPath = immersive_melodies.accesswidener`（本地快照里该文件只有表头，内容被 partial clone 截断）。
- 许可证未在仓库内声明（未确认）；无外部 API 依赖，纯自包含。
- 本地为 partial clone：`common/src/main/resources` 只剩 accesswidener，`*.mixins.json` 与 `assets/` 未拉取。

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **89 个文件，5221 行**（`common` 79 / `fabric` 3 / `forge` 3 左右），属于"小而密"的范例。

包结构（`common/src/main/java/immersive_melodies/`）：
- 根包：`Common`（常量/`RegisterHelper`）、`Client`、`Config`、`JsonConfig`、`Items`、`ItemGroups`、`Sounds`、`MidiListener`
- `resources/`（Melody 数据模型：`Melody`、`Track`、`Note`、`MelodyDescriptor`、`MelodyLoader`、`ServerMelodyManager`、`ClientMelodyManager`）
- `network/`（`Network`、`ImmersivePayload`、`FragmentedMessage`、`PacketSplitter`）、`network/c2s`(6)、`network/s2c`(4)
- `client/animation/` + `accessors/`(3) + `animators/`(12 个乐器姿态)、`client/sound/`(4)、`client/gui/`(3 + `widget/`3)、`client/`（`MelodyProgress`、`MelodyProgressManager`、`CustomInventoryModels`）
- `util/`（`MidiParser`、`MidiConverter`、`MidiInstrumentMapping`、`EntityEquiper`、`Utils`）、`item/`（仅 `InstrumentItem`）、`mixin/`（15 个）

最大文件：`client/gui/ImmersiveMelodiesScreen.java` 354、`item/InstrumentItem.java` 272、`MelodyUploadScreen.java` 255、`ImmersiveMelodiesFreePlayingScreen.java` 223、`resources/ServerMelodyManager.java` 222、`util/MidiParser.java` 214、`client/MelodyProgress.java` 145。

## 3. 入口与注册

- 共用基类 `common/.../Common.java:9-21`：`MOD_ID`、`LOGGER`、`networkManager`、`soundManager`，以及关键的**平台无关注册回调**：

```java
public interface RegisterHelper<T> { void register(ResourceLocation name, T value); }
```

- Fabric：`fabric/src/main/java/immersive_melodies/fabric/CommonFabric.java:34-67`，`registerHelper(BuiltInRegistries.ITEM, Items::registerItems)` 直接把平台注册函数喂给 common 的 `Items`；sound 同理；`ResourceManagerHelper.get(PackType.SERVER_DATA).registerReloadListener(new FabricMelody())`；`Network.register(fabricRegistrar)`。
- Forge：`forge/src/main/java/immersive_melodies/forge/CommonForge.java:32-44`，用 `RegisterEvent` 适配同一个回调（`event.register(register.key(), registry -> consumer.accept(registry::register))`），只有创造模式物品栏用 `DeferredRegister`（46-54 行）。
- 即：**注册框架是"函数式回调 + 平台适配器"**，common 不 import 任何加载器注册类。

## 4. 核心系统

### 4.1 网络抽象层 + 分包（最有借鉴价值）
`network/Network.java` 定义三个函数式接口 `Registrar` / `Sender` / `ClientSender`，平台侧各注入一次实现：Forge 用 `SimpleChannel`（`CommonForge.java:57-85`），Fabric 用 `ServerPlayNetworking`/`ClientPlayNetworking` 并在 `onInitialize` 里注册 sender（`CommonFabric.java:56-66`）。消息统一是 `ImmersivePayload`（只有 `encode(FriendlyByteBuf)` + `handle(Player)`，与 ImmersiveAircraft 的 cobalt 同源）。
- Fabric 侧消息 id 由类名生成：`msg.getSimpleName().toLowerCase().substring(0, 8) + id++`（`CommonFabric.java:76`），**存在前 8 字符重名风险**（如 `MelodyListMessage`/`MelodyDeleteRequest` → 均以 `melody...` 开头，前 8 字符不同则侥幸，属潜在坑）。
- **大包分片**：`PacketSplitter.java`（`FRAGMENT_SIZE = 8192`）把 `Melody` 编码成 byte[] 后切片，逐片发 `UploadMelodyRequest`/`MelodyResponse`；接收端 `FragmentedMessage` 接口用静态 `Map<String, Queue<byte[]>>`（`ConcurrentHashMap` + `ConcurrentLinkedQueue`）按 `类名:UUID:melody名` 聚合，累计长度达标后重组并 `finish(e, name, new Melody(buffer))`。曲子上传/下发完全不走文件系统直传。

### 4.2 曲子数据模型与存储
`resources/` + `ServerMelodyManager.java`。`Melody` 用 `FriendlyByteBuf` 作**唯一序列化格式**（既用于网络也用于磁盘），服务端玩家上传的自定义曲子写 `<dimension>/data/melodies/<ns>/<id>.bin`（29-37、75-90 行）；索引走 `SavedData`（`CustomServerMelodiesIndex`，"immersive_melodies"）只存 `MelodyDescriptor` 轻量描述；另一份 `SavedData` `MelodyTrackSettings` 记录"每个玩家对哪首曲子启用了哪些音轨"，并以 `Set<Integer>` ↔ `int[]` 转换存 NBT（177-194 行）。数据包曲子与自定义曲子由同一 `getMelody()` 统一读取（108-122 行，读失败即删除）。

### 4.3 MIDI 解析（JDK 自带库，不需额外依赖）
`util/MidiParser.java`（214 行）用 `javax.sound.midi.MidiSystem.getSequence(InputStream)`：先全轨道收集 tempo 事件（MetaMessage type 0x51）作为共享事件，再按 tick 排序、逐事件把 tick 换算成 ms（`deltaMs = (tick-lastTick) * 60000 / (resolution * bpm)`，第 48 行）并支持中途变速。`MidiConverter` / `MidiInstrumentMapping` 把 MIDI 音色映射到本 mod 乐器。游戏内还内置 midi（`Config.loadInbuiltMidis`）。

### 4.4 演奏时间线与客户端音效
`client/MelodyProgress.java` + `item/InstrumentItem.java`。曲子进度不是服务端模拟，而是**存在物品 NBT**（`TAG_MELODY` / `TAG_START_TIME` / `TAG_PAUSED_TIME` / `TAG_TRACKS` / `TAG_PLAYING`），客户端按 `world.getGameTime()` 推时间线（`tick(stack, gameTime)`）。演奏在 `inventoryClientTick`（85-138 行）里逐轨扫描：`MAX_LATE_NOTE_TIME = 150L` 丢弃过期音符，`Config.humanizationTime` 做前瞻以获得"人性化"提前量；同一玩家双手乐器共享一条时间线并各自按 `enabled_tracks` 过滤音轨。音效侧 `client/sound/`（`NoteSoundInstance`、`CancelableSoundInstance`、`SoundManagerImpl`）配合 `MusicSuppression` 在演奏时静音原版音乐。

### 4.5 实体演奏动画（接口 + 访问器 + Mixin 三件套）
`client/animation/`。`Animator` 只有 `setAngles(ModelAccessor<T>, MelodyProgress, float)`（`animators/Animator.java:7-10`），12 个乐器各一个实现（Flute/Trumpet/Bagpipe…），`ItemAnimators` 用 `Map<ResourceLocation, Animator>` 且默认回落到 `FluteAnimator`。`ModelAccessor<T>` 是**不依赖 Biped 类型的通用手部/头部访问器**（`getFlippedLeftArm()`、`flipHands()`、`headYaw()` 等），另有 `BipedModelAccessor`、`ArmsAndHeadAccessor`。注入点见 `mixin/BipedEntityModelMixin.java:17`：`@Inject(method = "setupAnim*", at = @At("TAIL"))` → `EntityModelAnimator.setAngles(new BipedModelAccessor<>(...))`；同族 mixin 还覆盖 Zombie/Illager/Piglin 模型与 `ItemRenderer`（第一人称乐器模型）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 4.1；c2s 6 条（`ItemActionMessage`、`MelodyRequest`、`MelodyDeleteRequest`、`UploadMelodyRequest`、`TrackToggleMessage`、`NoteBroadcastRequest`）、s2c 4 条（`MelodyListMessage`、`MelodyResponse`、`NoteMessage`、`OpenGuiRequest`）。自由演奏走"客户端发 `NoteBroadcastRequest` → 服务端校验后向 64 格内其他玩家回 `NoteMessage(entityId, tone, velocity)`"（`c2s/NoteBroadcastRequest.java:22-31`）。
- 数据驱动：曲子来自**两个来源**——数据包与玩家上传。数据包扫描目录固定为 `melodies`（`MelodyLoader.java:24`），只认 `.mid` / `.midi` 文件：`manager.listResources("melodies", path -> path.endsWith(".midi") || path.endsWith(".mid"))`（`MelodyLoader.java:60`），即把游戏数据包当 MIDI 库用；解析结果包成 `LazyMelody`（内部 `Supplier` + 记忆化）以便**首次演奏时才解析**。玩家上传的曲子由 `ServerMelodyManager` 落盘为 `.bin`。客户端用 `ClientMelodyManager` 缓存。
- 配置：自研 `JsonConfig`（与 ImmersiveAircraft 同一套写法，public 字段 + 反射读默认值），`Config` 里有 `keycodeToMidi`（A/S/D/F… → MIDI 音高，自由演奏键盘映射）、`mobInstrumentFactors`（让僵尸/骷髅/劫掠者也能捡乐器演奏，配合 `mixin/MobEntityMixin`、`ParrotEntityMixin`、`AllayEntityMixin`）、`uploadPermissionLevel`、`maxAudibleDistance=48`、`bufferDelay` 等。
- 外部 MIDI 键盘：`MidiListener.java` 起一个**守护线程每 5 秒轮询 `MidiSystem.getMidiDeviceInfo()`**，自动连接所有可发送设备（`device.getMaxTransmitters() != 0`），把真实 MIDI 键盘接入游戏；含 sustain(CC64) 处理。
- datagen：无。

## 6. Mixin

配置文件应为 `common/src/main/resources/immersive_melodies.mixins.json`（本地快照缺失，见 1；文件清单已由 `mixin/` 包 15 个类证实）。
类清单与目标：`BipedEntityModelMixin`/`AbstractZombieModelMixin`/`IllagerEntityModelMixin`/`PiglinEntityModelMixin` → `setupAnim*` @TAIL 注入演奏姿态；`ItemRendererMixin` → 第一人称乐器模型；`ModelLoaderMixin` → 注册乐器模型部件；`MusicManagerMixin` + `MusicTrackerAccessor` → 演奏时压制原版背景音乐；`ClientWorldMixin`/`ServerWorldMixin`/`ClientWorldMixin` → 世界级演奏状态；`MobEntityMixin`/`ParrotEntityMixin`/`AllayEntityMixin`/`PillagerEntityMixin` → 生物拾取与演奏乐器；`ServerChunkManagerMixin` → 区块加载时恢复/停止演奏。

## 7. 值得学的 5 条具体做法

1. **网络层三接口注入**（`Registrar`/`Sender`/`ClientSender`，`network/Network.java:53-63`），Forge/Fabric 各 30 行适配即可，common 零平台依赖。
2. **大对象分片传输 + 接收端重组**（`PacketSplitter.java` 8192 字节切分、`FragmentedMessage` 用并发 Map+Queue 按 UUID 聚合）。适用：任何要传自定义文件/曲谱/蓝图的 mod。
3. **一份 `FriendlyByteBuf` 编解码同时用于网络与磁盘**（`ServerMelodyManager.registerMelody` 直接把 `melody.encode(buffer)` 的字节写 `.bin`），数据结构只维护一套。
4. **通用姿态动画用"访问器接口 + 模型 mixin"解耦**（`ModelAccessor` + `ItemAnimators` 注册表 + `default` 空实现），新增乐器只需加一个 `Animator` 类，不动 mixin。
5. **把"演奏状态 + 时间线"放物品 NBT 而非服务端实体状态**（`InstrumentItem` 的 `TAG_START_TIME` 与 `MelodyProgress`），客户端各自按 `gameTime` 推进，只同步音符事件（`NoteMessage`）——省掉逐 tick 同步。
