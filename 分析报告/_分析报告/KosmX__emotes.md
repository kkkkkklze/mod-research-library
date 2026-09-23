# KosmX/emotes（Emotecraft）源码分析报告

## 1. 基本信息

- Mod 名：Emotecraft；mod_id `emotecraft`；作者 KosmX、dima_dencep（credits: Kale Ko、ZigyTheBird、BoBkiNN）；`group = io.github.kosmx.emotes`。
- 目标版本（**注意：本地为最新 dev 分支，非 1.21.1**）：`gradle.properties` 里 `minecraft_version = 26.2`、`neoforge_version = 26.2.0.32-beta`、`fabric_loader_version = 0.19.3`、`java_version = 25`；许可证 **GPL3**（`minecraft/src/neoforge/resources/META-INF/neoforge.mods.toml` 的 `license="GPL3"`）。
- 构建：**已从 Architectury 迁移到 unimined**（`xyz.wagyourtail.unimined 1.4.2-SNAPSHOT`）+ `com.gradleup.shadow`（打薄依赖）+ `jvmdowngrader` + mod-publish-plugin。`minecraft/build.gradle.kts` 用 `unimined.minecraft(sourceSets.main)` 生成 fabric/neoforge 两个 sourceSet（`combineWith(main)`），并写了 `defaultRemapJar = false`。
- **多模块多目标**：`settings.gradle.kts` include 了 7 个模块：`emotesAPI` / `emotesServer` / `emotesAssets` / `emotesMc` / `minecraft`（Fabric+NeoForge mod）/ `paper`（Paper 服务端插件）/ `geyser`（GeyserMC 扩展，让基岩版玩家也能看表情）。依赖 `PlayerAnimationLibCore`（playeranimlib，动画运行时）、`NoteBlockLib`（NBS 音乐）、`org.redlance.emotecraftlibrary:game-sdk`（在线表情库）、Searchables（可选编译依赖）。
- access widener 用的是新格式 **classTweaker**（`minecraft/src/main/resources/emotes.classtweaker`），NeoForge 侧在构建脚本里把它**转换成 accessTransformer**（`aw2at`）并剔除 `inject-interface` 行。

## 2. 源码规模与包结构

`find . -name '*.java' -exec wc -l {} +` = **191 个文件，14978 行**。模块分布：`minecraft` 96、`emotesAPI` 34、`geyser` 28、`emotesServer` 19、`emotesMc` 7、`paper` 7（`emotesAssets`/`blender`/`buildSrc` 无 java）。

- `emotesAPI/src/main/java/io/github/kosmx/emotes/`
  - `api/events/client/`（`ClientEmoteAPI`、`ClientEmoteEvents`、`ClientNetworkEvents`）、`api/events/server/`（`ServerEmoteAPI`、`ServerEmoteEvents`）、`api/proxy/INetworkInstance` ← **对外 API 与扩展点全在这**
  - `common/network/`（`EmotePacket`、`CommonNetwork`、`PacketConfig`、`PacketBound`、`PacketTask` + `objects/` 10 个分包类）、`common/serializer/gson/AnimationTypeAdapter`、`common/tools/`（`UUIDMap`、`MathHelper`）、`common/nbsplayer/`
- `emotesServer/`：`network/AbstractServerEmotePlay`、`serializer/`（`UniversalEmoteSerializer`、`type/IReader|IWriter|ISerializer`、`type/impl/` 4 种格式）、`services/InstanceService`、`config/`
- `emotesMc/`：跨平台公共层（`ServerCommands`、`PermissionKeys`、`IPermissionService`、`services/impl/VanillaPermissionService`、`network/ConfigTask`）
- `minecraft/src/main/java/io/github/kosmx/emotes/`：`main/`（`EmoteHolder`、`EmotecraftMod`、`emotePlay/`、`network/`）、`arch/`（`screen/`、`screen/widget/preview/`、`gui/widgets/`、`library/`、`mixin/`、`network/`）、`fabric|neoforge/`
- `geyser/`：`EmotecraftExt`、`animator/GeyserAnimationController`、`utils/resourcepack/`

最大文件：`arch/gui/widgets/EmoteListWidget.java` 611、`arch/library/LibraryFolderEntry.java` 443、`main/EmoteHolder.java` 340、`arch/screen/EmoteMenu.java` 313、`arch/screen/components/EmoteSubScreen.java` 302、`common/network/EmotePacket.java` 272、`geyser/EmotecraftExt.java` 259。

## 3. 入口与注册

没有单一 `@Mod` 主类承担业务，而是**平台壳 + 服务定位器**。平台壳：`minecraft/src/fabric/.../EmotecraftFabricMod.java`、`EmotecraftClientFabricMod.java`、`EmotecraftFabricPlatform.java`（Fabric）与 `minecraft/src/neoforge/java/io/github/kosmx/emotes/neoforge/` 下的 `EmotecraftNeoMod.java`、`EmotecraftNeoPlatform.java`、`executor/ForgeEmotesMain.java`（NeoForge）；另有 `neoforge/mixins/NetworkRegistryMixin.java`（用 mixin 改 NeoForge 的网络注册，属于少见做法）。

**注册/服务发现框架**：`org.redlance.common.services.ServiceUtils` + 各模块的 `AdvancedService` 接口静态实例。例如 `ServerEmoteAPI.INSTANCE = ServiceUtils.loadService(ServerEmoteAPI.class)`（`ServerEmoteAPI.java:95`）、`InstanceService.INSTANCE = ServiceUtils.loadService(InstanceService.class, InstanceServiceImpl::new)`（`InstanceService.java:14`）、`UniversalEmoteSerializer.READERS = ServiceUtils.loadServicesSorted(IReader.class)`。即"接口 + SPI/服务加载 + 平台提供实现"的插件式结构，common 代码不 import 加载器类。（本地快照 `META-INF/services` 未被拉取，未确认其具体 SPI 文件内容。）

## 4. 核心系统

### 4.1 一个包塞所有内容的 EmotePacket（网络协议设计，最核心）
`emotesAPI/.../common/network/EmotePacket.java`。它不是"一条消息一个类"，而是**"一个容器包 + 一组可选子包"**：
- 包头：`int networkingVersion` + `byte purpose(PacketTask)` + `byte 子包数量`，每个子包再带 `byte id`、`byte 版本`、`int 长度`（`EmotePacket.java:101-133`）。
- 子包类 `AbstractNetworkPacket`（`objects/`）：`NewAnimPacket`、`EmoteDataPacket`、`PlayerDataPacket`、`DiscoveryPacket`、`StopPacket`、`SongPacket`、`EmoteHeaderPacket`、`EmoteIconPacket`、`RemoveEmotesPacket`，各自实现 `read/write/doWrite/isOptional/boundsTo()`，由 `NetHashMap`/`NetData` 聚合。`PacketBound`（CLIENT/SERVER/BOTH）决定子包只在某个方向编码。
- **双向协商**：`PacketConfig` 里定义 config key（`DISCOVERY_PACKET=8`、`SERVER_TRACK_EMOTE_PLAY=0x80`、`NBS_CONFIG=3`…），双方交换 `Map<Byte,Byte> versions`，`AbstractNetworkPacket.getVer(versions)` 取 `min(本地版本, 对端版本)`——**同一份代码兼容新旧客户端**，子包按对端能力裁剪。
- 健壮性：`size < 0 || size > readableBytes` 校验 + `byteBuf.slice(currentPos, size)` 限定读者边界（82 行），可选子包解析失败只 warn 不抛；`EMPTY` 哨兵包用于"解析失败必须丢弃而不是断开 netty 连接"（46-51 行）；发送时可选子包超 `sizeLimit` 会回滚 `writerIndex` 并记录 `skippedPackets`（134-141 行）。

### 4.2 服务端权威的播放状态跟踪
`emotesServer/.../network/AbstractServerEmotePlay.java`（泛型 `<P extends ServerNetworkInstance>`，同时被 mod 服务端、Paper 插件、Geyser 复用）：
- `receiveMessage` 按 `packet.data.purpose` 分派（STOP/CONFIG/STREAM），`streamEmote()` 记录 `player.setPlayedEmote(data.emoteData, isForced)` 后调用 `ServerEmoteEvents.EMOTE_PLAY` 事件再 `sendForTrackedBy(data, player)` 广播。
- `playerStartTracking(tracked, tracker)`：**新玩家进入视野时，服务端主动把被跟踪玩家当前表情+进度 tick 补发**（108-118 行）；若服务端不支持跟踪，则 `INetworkInstance.isTrackingPlayState()` 为 false，改由客户端重复发送（`ClientEmotePlay.clientRepeatLocalEmote`）。
- API 提供 `setPlayerPlayingEmote / forcePlayEmote / playEmote(UUID, Animation, tick, forced)` 与 `getPlayedEmote(UUID)`（`ServerEmoteAPI.java:19-91`），并有 `force` 标志：被强制的表情玩家自己停不掉，服务端发现玩家"不守规矩"会记录 warn 并拒绝覆盖（`AbstractServerEmotePlay.java:66-72`）。

### 4.3 表情注册表与 UUID 稳定标识
`minecraft/.../main/EmoteHolder.java`：`static UUIDMap<EmoteHolder> list`（`UUIDMap` 在 `emotesAPI/.../common/tools/UUIDMap.java`），`hashCode()` 取 `emote.hashCode()` 缓存进 `AtomicInteger` —— 注释写明"Emotes have stable hash function"，所以**表情用内容哈希生成的 UUID 作全局 id**，客户端不需要先把文件传完就能识别"是不是同一个表情"。配合 `EmoteDataPacket/EmoteHeaderPacket/EmoteIconPacket` 做"先发 id+图标，真需要时再传整段动画"的懒加载；`HIDDEN_SERVER_EMOTES`（`UniversalEmoteSerializer`）用于"服务端有但不外发"的表情。

### 4.4 多格式读写的表情序列化
`emotesServer/.../serializer/`：`IReader`/`IWriter`/`ISerializer` 三接口 + 4 个实现（`BinaryFormat`、`JsonEmoteWrapper`、`BlockyAnimWrapper`、`QuarkReaderWrapper`），`UniversalEmoteSerializer.findReader(fileName)` 按文件名挑选 reader，`findWriter` 用比较器 `onlyEmoteFile() → possibleDataLoss()` 排序取最优（`UniversalEmoteSerializer.java:73-79`）——**格式可扩展、可降级导出**。`AnimationTypeAdapter`（Gson）在 `emotesAPI` 里，测试目录有 `AnimationTypeAdapterTest`、`NetworkPacketTest`、`RandomEmoteData`（**有真单测，少见**）。

### 4.5 客户端渲染/交互层
`minecraft/.../arch/`：表情轮盘 `screen/widget/AbstractFastChooseWidget` + `FastChooseController` + `preview/elemets/PlayerChoose{Circle,Square}Element`；表情列表/在线库 `arch/library/`（`EmoteLibrary`、`LibraryFolderEntry` 443 行、`LibraryModals`、`LibraryNotifications`、`LibraryStatus`，含隐私协议/配额弹窗）。渲染侧 mixin 覆盖 `EntityRenderDispatcher`、`LivingEntityRenderer`、`AvatarAnimManager`、`SoundEngine`、`KeyEvent` 等。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 4.1；平台实现分别在 `minecraft/src/fabric/.../network/PayloadTypeRegistator.java`、`.../fabric/network/server/ServerNetworkStuff.java`、`minecraft/src/neoforge/.../network/ForgeNetwork.java`，业务侧 `main/network/ClientPacketManager`、`arch/network/EmotePacketPayload`。服务端入口用 mixin 挂到 `ConnectionHandler`/`ServerGamePacketListenerImpl`。Paper 侧用 `fuckery/EmotePayloadHandler` + `network/BukkitNetworkInstance` 自己解析同一套 ByteBuf 协议（**一份协议四种服务端实现**）。
- 数据驱动：表情来源有三类——内置 json/binary 资源（`emotesAssets` 模块只放资源）、玩家外部表情目录（`InstanceService.getExternalEmoteDir()` ← `Config.emotesDir`）、在线表情库（`game-sdk` + `arch/library/`）；服务端目录由 `Serializer.getConfig().emotesDir` 决定。
- 配置：服务端 `emotesServer/config/Serializer`（+ `CommonConfig`、`ConfigSerializer`）、客户端 `main/config/ClientConfig`（+ `CloseWheel`），配置路径支持系统属性 `emotecraftConfigDir` 覆盖，值为 `pluginDefault` 时落到 `plugins/emotecraft`（`InstanceService.java:26-44`）——同一份代码适配 mod 与插件环境。
- datagen：无（但有 JUnit 测试基础设施，`emotesAPI/build.gradle.kts` 里配了 `useJUnitPlatform()` 与 junit-bom 6.1.3）。

## 6. Mixin

- `minecraft/src/main/resources/emotecraft-arch.mixins.json`：`package: io.github.kosmx.emotes.arch.mixin`，`compatibilityLevel: JAVA_16`，`defaultRequire: 1`；通用 2 个 `network.ConnectionHandlerMixin`、`network.ServerGamePacketListenerImplMixin`；客户端 7 个 `AvatarAnimManagerMixin`、`EmoteAvatarMixin`、`EntityRenderDispatcherMixin`、`KeyEventMixin`、`LivingEntityRendererMixin`、`PlayerMixin`、`SoundEngineMixin`。
- NeoForge 额外配置 `minecraft/src/neoforge/resources/emotecraft-neo.mixins.json`（在 `neoforge.mods.toml` 里以两个 `[[mixins]]` 声明），含 `neoforge/mixins/NetworkRegistryMixin`。
- 代表 hook：`PlayerMixin` 与 `main/mixinFunctions/IPlayerEntity.java`（duck interface，给出 `emotecraft$playEmote / $getEmote / $isForcedEmote` 等扩展方法，客户端逻辑里到处用 `player.emotecraft$...` 调用）；`EntityRenderDispatcherMixin`/`LivingEntityRendererMixin` 注入实体渲染以驱动表情动画。

## 7. 值得学的 5 条具体做法

1. **单一容器包 + 版本协商子包**（`EmotePacket` + `AbstractNetworkPacket` + `PacketConfig`），新旧客户端互通且能按对端能力裁剪可选数据。适用：需要长期维护协议兼容的大型交互 mod。
2. **子包级容错**：长度区间校验 + `slice` 限界 + `isOptional()` 子包失败仅告警 + 超限回滚 `writerIndex`（`EmotePacket.java:75-92,134-141`）。适用：任何手写 ByteBuf 协议的场景。
3. **内容哈希作全局 UUID**（`EmoteHolder.hashCode()` + `UUIDMap`），表情/资源先传 id 与元数据、按需再传本体（`EmoteHeaderPacket`/`EmoteIconPacket`/`EmoteDataPacket` 分层）。适用：玩家可自定义内容（皮肤/蓝图/曲谱）的 mod。
4. **服务端跟踪播放状态 + 新观察者补发**（`AbstractServerEmotePlay.playerStartTracking`，`:108-118`），并用 `SERVER_TRACK_EMOTE_PLAY` 配置位让老服务端退化为客户端重发。适用：所有"持续状态"型同步（表情、姿势、载具表演）。
5. **一套业务代码、多服务端形态**：`emotesServer`/`emotesMc` 用泛型 + `ServiceUtils` 服务加载解耦，同一 `AbstractServerEmotePlay` 被 mod 服务端、Paper 插件（`paper/.../ServerSideEmotePlay`）、Geyser 扩展共用。适用：想同时支持 Fabric/Forge/插件端的库型 mod。

## 8. 公开 API / 扩展点

- 扩展点集中在 `emotesAPI` 模块（独立发布为 `emotesAPI` artifact，有 sourcesJar/javadocJar）：
  - 服务端：`io.github.kosmx.emotes.api.events.server.ServerEmoteAPI`（`setPlayerPlayingEmote`、`forcePlayEmote`、`playEmote`、`getPlayedEmote`、`isForcedEmote`，静态 `INSTANCE` 由服务加载）；`ServerEmoteEvents.EMOTE_VERIFICATION / EMOTE_PLAY / EMOTE_STOP_BY_USER` 三个事件（自定义 `Event<Listener>` 实现，返回 `EventResult.PASS/FAIL/SUCCESS`）。
  - 客户端：`api.events.client.ClientEmoteAPI` / `ClientEmoteEvents` / `ClientNetworkEvents`（本地表情播放/停止与网络事件回调）。
  - 网络接入：`api.proxy.INetworkInstance`（`getVersions/setVersions/sendMessage(EmotePacket.Builder, boolean)/isActive/isTrackingPlayState/maxDataSize/createConfigurationPacket`）——外部 mod 只要实现它就能把 Emotecraft 协议挂到自己的通道上。
  - 数据格式：`emotesServer` 的 `IReader`/`IWriter`/`ISerializer` 可被外部 mod 通过服务加载扩展新表情文件格式。
- 权限/命令扩展：`emotesMc/PermissionKeys.java`、`services/IPermissionService`（Vanilla/Fabric/NeoForge/Bukkit 四种实现），命令 `emotesMc/ServerCommands`、`EmoteArgumentProvider`。
