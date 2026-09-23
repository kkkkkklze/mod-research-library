# Simple Voice Chat 源码分析报告

分析仓库快照：`源码库\_参考仓库\_bulk\henkelmax__simple-voice-chat`（下文路径均相对该根目录）

## 1. 基本信息

- Mod 名 / mod_id：Simple Voice Chat / `voicechat`；作者 Max Henkel（henkelmax）
- 目标版本（本次快照：`gradle.properties`）：`minecraft_version=26.2`、`mod_version=2.6.24+26.2`、`java_version=25`、`voicechat_compatibility_version=20`；同一代码库通过模块组合同时出品 1.20.1/1.21.x 等版本
- 加载器：Fabric、Quilt、NeoForge、Forge，外加 4 个服务端平台 Bukkit(Spigot/Folia)、Paper、Velocity、BungeeCord（`settings.gradle:15`）
- 关键 Gradle 插件：fabric-loom、quilt-loom、moddevgradle(NeoForge)、forgegradle、paperweight(userdev)、shadow、cursegradle/modrinth/minotaur、hangar-publish；`build.gradle:14` 远程 `apply from` henkelmax 私有 mod-gradle-scripts（因此快照里没有 `fabric.mod.json`，它由该脚本生成）
- 许可证：`All rights reserved`（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）
- 依赖关系：**API 独立发行为 `voicechat_api`**（`neoforge.mods.toml` 声明两个 modId，`ForgeVoiceChatAPIDummyMod` @Mod("voicechat_api")），其他 mod 依赖的是它；运行时依赖 `de.maxhenkel.configbuilder`（自研配置库）、cloth-config、Concentus（纯 Java Opus）、自有 native 音频库 opus4j/rnnoise4j/lame4j/speex4j、fabric-permissions-api、commodore、PlaceholderAPI、ViaVersion（全部 shadowJar + relocate）

## 2. 规模与包结构

647 个 `.java`，43 565 行（`find`/`wc -l` 实测）。按模块：common 138 文件/9 665 行、common-client 153/12 266、bukkit 147/11 423、api 91/2 953、fabric 30/1 291、quilt 30/1 289、common-proxy 17/1 518、neoforge 15/979、forge 9/840、paper 12/788、bungeecord 3/291、velocity 2/262。

顶层包（第 3 层）：`api/.../api/{events(38), audiochannel(10), packets(8)}`；`common/.../voice/{common(19), server(9), rtc(5)}`、`common/.../{net(18), plugins/impl(38), config, command, permission, natives}`；`common-client/.../{voice/client(30+speaker/microphone), gui(50+), plugins/impl(19)}`。

最大文件：`bukkit/.../util/FriendlyByteBuf.java`(1043)、`common/.../voice/server/Server.java`(624)、`bukkit/.../voice/server/Server.java`(558)、`common-client/.../voice/client/AudioRecorder.java`(362)、`api/.../api/VoicechatServerApi.java`(343)、`common-client/.../AudioChannel.java`(314)、`common/.../plugins/impl/VoicechatServerApiImpl.java`(312)、`common-client/.../SoundManager.java`(309)。

## 3. 入口与注册

平台无关抽象主类 `common/src/main/java/de/maxhenkel/voicechat/Voicechat.java:37` `initialize()` —— 配置 → NetManager.init() → `ServerVoiceEvents` → `ServerPlayerManager.init()` → 插件 → 命令；各加载器只写 3 行子类（如 `fabric/.../FabricVoicechatMod.java` 继承 Voicechat 并实现 ModInitializer；`neoforge/.../NeoForgeVoicechatMod.java` FMLCommonSetupEvent 中调 `initialize()` 并把 `NeoForgeNetManager` 注册进 mod 事件总线）。

**本 mod 没有方块/物品/实体，故完全不用 DeferredRegister/Registrate**；"注册"只有两件事：自定义网络通道（见 §5）与命令 `VoicechatCommands.register`（经 `CommonCompatibilityManager.onRegisterServerCommands` 回调注入平台命令分发器）。

## 4. 核心系统

**(1) 双网协议栈（最大亮点）**
- MC 侧 TCP：`common/.../net/NetManager.java:12` 用 14 个强类型 `Channel<T>` 字段声明全部 MC 包（updateState/playerState(s)/removePlayerState/secret/requestSecret/add-/remove-/join-/create-/leave-/joinedGroup、add/removeCategory）；`Channel.onServerPacket` 先过 `PacketRateLimiter`，超限直接 `player.connection.disconnect(...)`，再 `execute(server, ...)` 切回主线程。
- 语音侧 UDP：`common/.../voice/common/NetworkMessage.java:44` 用 `MAGIC_BYTE=0xFF + UUID + byte[] 密文` 的自定义帧；`packetRegistry`（byte 0x1–0xA）映射 Mic/Sound/Auth/KeepAlive 等 10 类；`Secret`（`voice/common/Secret.java:24`）为 `AES/GCM/NoPadding`，16 字节密钥 + 12 字节 IV + 128bit tag，每包随机 IV 前置拼装。

**(2) 握手与连接生命周期**：客户端收到 `SecretPacket`（含 port/codec/mtu/distance/keepAlive/voiceHost）后建 `InitializationData` → UDP `AuthenticatePacket` → `AuthenticateAckPacket` → `ConnectionCheckPacket/Ack`（以地址反向查连接，完成 NAT/地址校验并升格为正式连接）→ 双向 KeepAlive（超时阈值 `keepAlive*10`）。服务端状态机在 `voice/server/Server.java` 的 `ProcessThread`（见下）。

**(3) 语音服务器线程模型**：`voice/server/Server.java:26` 继承 `Thread`，主 loop 只做 `packetQueue.add(socket.read())`（阻塞收包→队列）；内部 `ProcessThread` 每 10 ms `poll` 一个包，按 `TTL` 丢弃过期包（`MicPacket.getTTL()=500ms`），并周期发 KeepAlive、清理超时连接。全部集合为 `ConcurrentHashMap`，MC 对象只在 `CommonCompatibilityManager.execute(server,...)` 回主线程时访问。

**(4) 空间音频与三种路由**：`Server.processMicPacket` → 有组则 `processGroupPacket`（`GroupSoundPacket` 只发同组），否则 `processProximityPacket`（`PlayerSoundPacket` + `ServerPlayerManager.getPlayersInRange(level,pos,broadcastRange)`，`broadcastRange<0` 时取 `voiceChatDistance+1`）；旁观者走 `LocationSoundPacket`；组可 `isOpen()/isIsolated()` 决定是否叠加邻近语音。权限 `PermissionManager.INSTANCE.SPEAK/LISTEN/GROUPS_PERMISSION`。

**(5) 状态同步**：数据载体 `voice/common/PlayerState`（uuid/name/disabled/disconnected/group），由 `PlayerStateManager`+`ServerPlayerManager` 维护，变更时发 `PlayerStatePacket`（单个）、`PlayerStatesPacket`（批量，登录时全量）、`RemovePlayerStatePacket`；客户端据此渲染头顶图标与音量列表。

**(6) 平台抽象层**：`common/.../intercompatibility/CommonCompatibilityManager.java` 是"事件回调总线"（每个平台子类持有 `CopyOnWriteArrayList<Consumer<X>>`，把 Forge 的 `@SubscribeEvent` 转成平台无关的 `onPlayerLoggedIn/onServerStarting/...`），`CrossSideManager` 决定单人存档是否启动语音服务端；`Voicechat.Loader` 枚举标识 5 种平台。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络注册（NeoForge 例，`neoforge/.../net/NeoForgeNetManager.java:33`）：`RegisterPayloadHandlersEvent` → `PayloadRegistrar.optional()` + `playToServer/playToClient/playBidirectional`，用匿名 `StreamCodec` 把 `packet.toBytes/fromBytes` 接进 NeoForge 的 `CustomPacketPayload` 体系（`net/Packet.java` 直接继承 `CustomPacketPayload`，自带 `Type<T>`）。未鉴权玩家除 `RequestSecretPacket` 外一律丢弃；Bukkit 平台同结构但用 plugin messaging channel 承载（`bukkit/.../net/NetManager.java`），为此**把 MC 的 `FriendlyByteBuf` 整个重写**（`bukkit/.../util/FriendlyByteBuf.java`，`extends ByteBuf`，1043 行，复刻 VarInt/ByteArray/UUID/Utf）。
- 配置：`de.maxhenkel.configbuilder.ConfigBuilder`（作者自研，properties 文件 + `ConfigEntry<T>` 带上下界与多行注释），`ServerConfig`(19 项)/`ClientConfig`/`Translations`/`ProxyConfig`；配置快照随 `SecretPacket` 下发，客户端"配置由服务端决定"。
- datagen：**无**（无 DataGenerator；资源为静态文件。注意本次快照未包含 `common/src/main/resources`，但 `bukkit/build.gradle` 的 `generateFallbackTranslations` 会读 `common/src/main/resources/assets/voicechat/lang/en_us.json` 生成 `FallbackTranslations.java`——不属于 datagen）。版本兼容用 `voicechat_compatibility_version` 常量 + `BuildConstants` 模板文件（`src/template/java` 经 Gradle `expand` 生成）。

## 6. Mixin

配置：`fabric/src/main/resources/voicechat.mixins.json`（package `de.maxhenkel.voicechat.mixin`，required，`JAVA_17`；quilt 同构）。代表类：
- `PlayerManagerMixin`：`@Inject(method="placeNewPlayer", at=@At("RETURN"))` 与 `method="remove", at=@At("HEAD")` → 触发 `PlayerEvents.PLAYER_LOGGED_IN/OUT`（Fabric 无登录事件，只能 mixin）
- `IntegratedServerMixin`：`publishServer(...)Z` RETURN 处发 `SERVER_PUBLISHED(port)`，用于单人开局域网后拿到真实语音端口
- `ConnectionAccessor`：`@Accessor("channel")` 取 `Connection.channel`，拿客户端真实远端 IP（通过 MC 连接拿到 UDP 目标）
- 其余为 UI/音效类（GameRenderer、Minecraft、Keyboard、Mouse、PlayerEntry、AvatarRenderer、PackRepository）。**NeoForge/Forge 模块不写 mixin**，全部走事件总线。

## 7. 值得学的 5 条

1. **用"回调总线"隔离加载器**：`intercompatibility/CommonCompatibilityManager.java` + 平台子类，业务代码零 `@SubscribeEvent`；新平台只需实现抽象方法。
2. **自己刻一条 UDP 协议而不是塞进 MC 包**：`voice/common/NetworkMessage.java` 的 magic byte + 注册表 + 每包 AES-GCM，语音不受 MC 主线程/TCP 影响，可独立端口/插件替换。
3. **收包与处理分离的双线程模型**：`voice/server/Server.java` 主 loop 只入队，`ProcessThread` 带 TTL 丢弃 + KeepAlive，避免单包处理阻塞收包（可迁移到任何高频包场景）。
4. **数据包做成"强类型 Channel 字段"**：`net/NetManager.java` 把每个包声明为字段，注册/发送/监听都在同一处，比字符串 id 表好维护。
5. **为了跨平台把 MC 工具类整体重写**：`bukkit/.../util/FriendlyByteBuf.java` 让同一套 Packet 序列化代码跑在没有任何 MC 类的 Bukkit 上——同思路可用于"同一套网络 codec 同时服务 NeoForge/Forge"。

## 8. 公开 API（本 mod 属前置/库类）

- 包路径：`de.maxhenkel.voicechat.api`（独立模块 `api/`，`publishApi` 任务发到 Maven；Fabric 有 `fabric:api-stub` 让依赖方可编译）
- 接入方式：实现 `VoicechatPlugin`（`getPluginId` + `initialize(VoicechatApi)` + `registerEvents(EventRegistration)`）；Fabric 用 entrypoint `voicechat`（`FabricCommonCompatibilityManager.java:147`），Forge/NeoForge 用 `@ForgeVoicechatPlugin` 注解扫描
- 扩展点：`events/` 38 个事件（`MicrophonePacketEvent`/`SoundPacketEvent`/`VoiceDistanceEvent`/`VoiceHostEvent`/`PlayerConnectedEvent`/`RegisterVolumeCategoryEvent`…）；`VoicechatServerStartingEvent#setSocketImplementation(VoicechatSocket)` 可整套替换 UDP 传输（作者自己的 WebRTC 实验实现即在 `common/.../voice/rtc/`）；`audiochannel`（Entity/Locational/Static 频道）+ `audiosender` + `audiolistener` 让第三方 mod 播放/监听音频；`api/opus` 暴露编解码器
- 另有可见的"坏味道/注意点"：`Voicechat` 主类大量 `public static` 可变字段（`SERVER`/`SERVER_CONFIG`/`TRANSLATIONS`），以及 `Bukkit`/`Paper` 模块与 common 大段复制粘贴（`Server.java` 624 vs 558 行），说明其跨平台复用靠"复制+按平台改"，非共享抽象到底。
