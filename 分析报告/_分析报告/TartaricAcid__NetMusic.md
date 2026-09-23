# TartaricAcid/NetMusic 源码分析报告

## 1. 基本信息
- Mod 名：Net Music Mod；mod_id：`netmusic`；作者：TartaricAcid、IMG、郝南村、琥珀酸、帕金伊、SQwatermark（`src/main/resources/META-INF/mods.toml`）
- 目标：Minecraft 1.20.1 + **Forge 47.1.0**（`mods.toml` loaderVersion `[46,)`，Minecraft `[1.20,1.20.2)`），Java 17，Parchment `2023.08.20-1.20.1`
- Gradle：ForgeGradle `[6.0.16,6.2)` + Parchment librarian + `com.github.johnrengelman.shadow`（`build.gradle:1-16`）
- 许可证：MIT
- 编译依赖（重点是**可选前置**）：Cloth Config（`implementation`，配置界面）、Sophisticated Core/Backpacks（精妙背包音乐播放器）、Touhou Little Maid（女仆 AI 播放音乐，`touhou_little_maid` 为 optional 依赖）、JEI（compileOnly）、Inventory Profiles Next；音频解码用 `minecraftLibrary`：mp3spi、javasound-aac、jflac，并在 `shadowJar` 中 `relocate` 到 `com.github.tartaricacid.netmusic.soundlibs.*` + `mergeServiceFiles()`。**本 mod 不对外提供 API 依赖，纯内容 mod**（但内部有扩展点，见 §8）。

## 2. 源码规模与包结构
- 110 个 `.java`，合计 **8711 行**（`find . -name '*.java' -exec wc -l {} +`）
- 主要包（第 3 层，括号为文件数）：`api`(5)+`api/lyric`(2)+`api/pojo`(3)+`api/resolver`(3)+`api/search`(2)；`client/audio`(7)+`client/audio/provider`(2)+`client/audio/reader`(3)；`client/api`(2)+`client/api/implement`(5)；`init`(7)；`network/message`(6)；`block`(5)；`item`(3)；`inventory`(3)；`config`(2)；`event`(1)；`util`(2)；`tileentity`(2)；`compat/sbackpack`(6)、`compat/tlm/*`（20+，含 `ai`/`backpack`/`client/audio`/`message`）
- 最大文件：`client/model/ModelMusicPlayer.java`(396)、`client/audio/BigMegaphoneClientManager.java`(269)、`client/gui/BigMegaphoneScreen.java`(257)、`client/gui/ComputerMenuScreen.java`(254)、`tileentity/TileEntityBigMegaphone.java`(234)、`item/ItemMusicCD.java`(221)、`client/audio/NetMusicAudioStream.java`(174)、`api/pojo/NetEaseMusicList.java`(174)

## 3. 入口与注册
`src/main/java/com/github/tartaricacid/netmusic/NetMusic.java`：
```java
@Mod(NetMusic.MOD_ID)
public class NetMusic {
    public static WebApi NET_EASE_WEB_API;
    public NetMusic() {
        NET_EASE_WEB_API = new NetEaseMusic().getApi();
        InitBlocks.BLOCKS.register(FMLJavaModLoadingContext.get().getModEventBus());
        InitBlocks.TILE_ENTITIES.register(...); InitItems.ITEMS/TABS.register(...);
        InitSounds.SOUND_EVENTS.register(...); InitContainer.CONTAINER_TYPE.register(...);
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, GeneralConfig.init());
        SBackpackCompat.register();   // 尽早注册兼容
    }
}
```
全部用 Forge `DeferredRegister`+`RegistryObject`（`init/InitBlocks.java:17-28`、`InitItems.java:20-30`、`InitContainer.java:12-15`），无 Registrate。`init/CommonRegistry.java` 用 `@Mod.EventBusSubscriber(Bus.MOD)` 在 `FMLCommonSetupEvent` 里 `enqueueWork(NetworkHandler::init)`，在 `FMLLoadCompleteEvent` 里初始化 `MusicPlayResolverManager`（冻结扩展点列表）。

## 4. 核心系统
1. **音频流子系统**（`client/audio/`）：`NetMusicAudioStream` 实现 `net.minecraft.client.sounds.AudioStream`，把任意来源流统一转成 `PCM_SIGNED 16bit`（`NetMusicAudioStream.java:100-109`，mp3 无位深时默认 16），用 4 线程固定池 `NetMusic-AudioStream-Downloader`（daemon）+ `ConcurrentLinkedQueue<ByteBuffer>` 做**分块预载**：构造时 `pumpBuffers(4)`，`read()` 前若队列 <4 再异步 `pumpBuffers(2)`（`:25-32, :116-126`），队列不足直接返回 `null` 交给 MC 音频线程重试。
2. **URL 处理器扩展点**：`client/api/IAudioStreamHandler`（`canHandle/handle/getPriority`）+ `AudioStreamHandlerManager`，内置 `CnrM3u8Handler/M3u8Handler/NetEaseHttpHandler/LocalFileHandler/DirectHttpHandler`（`implement/`），支持 m3u8/TS 分段流（`M3u8Handler.java`，超时 5s/10s）。
3. **HTTP 与异步**：`api/NetWorker.java` 单例 `java.net.http.HttpClient`（5s 连接超时、`Redirect.ALWAYS`、可配置代理 `NetWorker.ConfigProxySelector`）；`api/NetEaseMusic.java` 只负责拼 Origin/Referer/UA/Cookie 头，返回 `WebApi`。
4. **歌曲 URL 解析链**：`api/resolver/IAsyncSongUrlResolver` + `MusicPlayResolverManager`，`CompletableFuture<SongInfo>` 异步解析，按 priority 倒序匹配，异常时回落到原 `SongInfo`（`MusicPlayResolverManager.java:41-54`），默认 `DefaultVipResolver` 当前被注释掉（`:16`）。
5. **大喇叭（空间广播）**：`client/audio/BigMegaphoneClientManager` 用 `Long2ObjectOpenHashMap<TrackedBroadcast>` 按方块坐标管理长连接广播，用 `sessionId` 防 stop/start 乱序误停（`:35-58`），带重试间隔（40 tick、最多 2 次）与客户端并发上限；`MusicPlayManager` 负责 404 提示与 `Minecraft.getInstance().submitAsync` 异步播放。
6. **物品数据与持久化**：`ItemMusicCD.SongInfo` 支持 `CompoundTag` 序列化（`ItemMusicCD.java:163-190`）；`config/MusicListManage` 读写 `config/net_music/music.json`（上限 100 首，`MAX_NUM`），同时可从数据包 `ResourceManager` 加载。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`network/NetworkHandler` 单一 `SimpleChannel("netmusic:network")`，协议版本常量 `"1.5.1"`，注册 6 个包（id 0-5：`MusicToClient`/`GetMusicList`/`SetMusicID`/`BigMegaphoneStart|Stop|Control`），并把 `CompatRegistry.initNetwork(CHANNEL)`、`SBackpackCompat.initNetwork(CHANNEL)` 交给兼容模块**复用同一频道注册**（`NetworkHandler.java:27-42`）。范围广播用 `chunkMap.getPlayers(ChunkPos)` + `distanceToSqr < 96*96` 过滤（`:44-52`）。
- 配置：`config/GeneralConfig`（Forge COMMON spec）含立体声开关、代理类型/地址、歌词颜色、大喇叭最大范围 96（1-256）/扫描间隔 200 tick/客户端并发 3、CD 生成开关。
- 数据驱动：音乐列表 `music.json` + 数据包资源；无 codec 化数据驱动注册。
- datagen：仅声明 `sourceSets.main.resources { srcDir 'src/generated/resources' }`，目录为空，**实际无 datagen**。
- 注：本快照 `src/main/resources` 下只有 `META-INF/`（assets/lang 未包含）。

## 6. Mixin
**无**（全仓库无 `spongepowered` 引用、无 mixins.json）。

## 7. 值得学的 5 条具体做法
1. **音频"队列 + 后台线程池"预载**，让 `read()` 永不阻塞游戏线程：`client/audio/NetMusicAudioStream.java:116-168`；适用任何流式下载播放（音频/视频/大文件）。
2. **可冻结的优先级扩展点**：`registerHandler/registerResolver` 在列表被 `ImmutableList.copyOf` 后调用会打印明确错误并拒绝（`AudioStreamHandlerManager.java:31-39`），既保证加载顺序可控又对第三方友好。
3. **包装输入流把 IOException 转成 RuntimeException**，避免第三方解码库吞掉超时异常导致 `read` 死循环阻塞主线程：`client/audio/MusicBufferedInputStream.java:12-30`（真实踩坑注释）。
4. **HTTP Range 分块下载流**：`client/audio/ChunkedAudioStream` 用 `Function<Long,HttpRequest>` 按 offset 续传（接受 200/206），对不支持 seek 的远端也能顺序读。
5. **sessionId 幂等防乱序**：长连接广播的 start/stop 用递增 sessionId + 去重比较，防网络乱序把新会话停掉（`BigMegaphoneClientManager.java:35-46`）。
6. 兼容模块"按外部 mod 分包 + 统一 initNetwork/initContainerScreen 钩子"的组织方式：`compat/`（cloth/sbackpack/tlm），入口显式调用，避免硬依赖崩溃。

## 8. 扩展点（非库 mod，但内部开放）
- 服务端/通用：`api/resolver/MusicPlayResolverManager#registerResolver`、`api/WebApi`、`api/NetWorker`
- 客户端：`client/api/AudioStreamHandlerManager#registerHandler` + `IAudioStreamHandler`
- 兼容层：`compat/tlm` 用 TLM 的 `ITool`（LLM function tool）实现 `PlayMusicTool`/`StopMusicTool`，通过 `compat/tlm/init/CompatRegistry` 统一注册

## 关键词
音频流分块预载、SimpleChannel 多模块复用、优先级扩展点冻结、sessionId 防乱序、shadowJar relocate 解码库
