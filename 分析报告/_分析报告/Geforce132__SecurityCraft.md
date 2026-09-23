# SecurityCraft 源码分析报告

> 仓库：`源码库/_参考仓库/_bulk/Geforce132__SecurityCraft`。正文相对路径均以 `src/main/java/net/geforcemods/securitycraft/` 为基址；配置/资源文件给出完整相对路径。本报告写作时该仓库为浅检出，仅 Java 源码 + 3 个资源文件可读（见第 2 节）。

## 1. 基本信息

- mod_id：`securitycraft`（`gradle.properties` 第 3 行 `mod_id=securitycraft`）
- 作者：Geforce、bl4ckscor3、Redstone_Dubstep、ChainmailPickaxe（`gradle.properties` 第 4 行）
- 许可证：MIT（`src/main/resources/META-INF/neoforge.mods.toml:1` 声明 `license="MIT ..."`；LICENSE 文件本体不在浅检出内，未验证）
- 目标 MC / 加载器：`mc_version=26.2`、`neoforge_version=26.2.0.57`（`gradle.properties` 第 10、13 行）。这是极新的 Minecraft/NeoForge 版本线，源码里已用 `net.minecraft.resources.Identifier`、`ValueInput/ValueOutput`、`ExtractLevelRenderStateEvent` 等新版 API，很多 1.20.1 经验不能直接平移
- Gradle 插件与工程结构：`net.neoforged.moddev` 2.0.141（`build.gradle` 第 6 行 + `gradle.properties` 的 `mdg_version`），单工程非 multiloader；`run/client2` 配了第二个离线账号 Dev2（`build.gradle` client2 块），方便双端联调相机联动
- Java 版本：25（`gradle.properties` `java_version=25`；`src/main/resources/securitycraft.mixins.json` 的 `compatibilityLevel: "JAVA_25"` 互证）
- 发布坐标：group `net.geforcemods.securitycraft`、archivesName `securitycraft`、版本 `1.10.2.1`（`build.gradle` 的 `version/group/base` 块 + `gradle.properties` 第 8 行）

## 2. 源码规模与包结构

实测（`py` 逐文件行数统计）：**616 个 .java，共 72,876 行**。速览卡片写 73,432 行、SCContent 3220 行，实测为 3219 行——卡片计数含尾部差异，以本报告实测为准；卡片"目标版本 Forge 26.2.0.57"一项有误，本工程只有 NeoForge 依赖。

主要包文件数分布：

| 包 | 文件数 | 包 | 文件数 |
|---|---|---|---|
| blocks | 128 | api | 26 |
| blockentities | 65 | util | 25 |
| screen | 58 | misc | 24 |
| network | 47 | compat | 19 |
| renderers | 40 | entity | 17（camera 7 / sentry 等） |
| mixin | 39 | datagen | 14 |
| items | 32 | models | 12 |
| inventory | 30 | components | 11 |
| commands/recipe/particle/fluids | 6/6/4/2 | 根包 | 11 |

最大 12 个源文件（行数）：`SCContent.java` 3219、`datagen/RecipeGenerator.java` 2010、`datagen/BlockTagGenerator.java` 1007、`datagen/BlockModelAndStateGenerator.java` 888、`blockentities/BlockPocketManagerBlockEntity.java` 853、`ClientHandler.java` 805、`entity/sentry/Sentry.java` 802、`screen/SCManualScreen.java` 763、`SCEventHandler.java` 637、`blockentities/SecureRedstoneInterfaceBlockEntity.java` 544、`blockentities/SecurityCameraBlockEntity.java` 526、`entity/AbstractSecuritySeaBoat.java` 521。

**源码树不完整**：`src/main/resources/` 只剩 `META-INF/accesstransformer.cfg`、`META-INF/neoforge.mods.toml`、`securitycraft.mixins.json` 三个文件，assets/lang/方块模型 JSON 全部缺失；`build.gradle` 引用的 `src/generated/resources`（datagen 输出）也不在检出里。下文只分析 Java 可读事实，不推断任何缺失 JSON 的内容。

## 3. 入口与注册

- 主入口 `SecurityCraft.java:68-105`：`@Mod(MODID)` + 类级 `@EventBusSubscriber`。构造器内一次性挂 14 个 `DeferredRegister`：

```java
container.registerConfig(ModConfig.Type.SERVER, ConfigHandler.SERVER_SPEC);   // :90
SCContent.BLOCKS.register(modEventBus);                                        // :91
SCContent.ITEMS.register(modEventBus);                                         // :99
NeoForge.EVENT_BUS.addListener(this::registerCommands);                        // :86
```

- 客户端入口 `SecurityCraftClient.java:11-15`：`@Mod(dist = Dist.CLIENT)`，注册客户端配置与配置屏扩展点。
- 网络注册 `RegistrationHandler.java:179-181`：`event.registrar(MODID).versioned(getVersion())`，随后逐项 `playToClient/playToServer`（约 :183-215）。
- 跨 mod 接口注册走 IMC：`SecurityCraft.java:107-130` 在 `InterModEnqueueEvent` 里广播自己的 extraction block / passcode convertible / sentry attack target / door activator 实现，并顺带探测 TOP、Distant Horizons。
- 服务端事件集中在 `SCEventHandler.java`（24 个 `@SubscribeEvent`，如 `BreakBlockEvent:444`、`EntityPlaceEvent:491`、`EntityTeleportEvent:554`、`OwnershipEvent:510`）；渲染侧订阅在 `ClientHandler.java` 与 `entity/camera/FrameFeedHandler.java:210-234`。
- 一个易忽视的注册点：`SecurityCraft.java:74-83` 定义 `CAMERA_TICKET_CONTROLLER`（区块加载票据控制器），在 `RegisterTicketControllersEvent:140-143` 注册，负责回收"画面框正在观看的相机"周围的强加载票据。

## 4. 核心系统

### 4.1 归属与访问控制（问题②）

归属以 `api/Owner.java:26-67` 这个不可变值对象表达（name + UUID 字符串 + validated 标志），带 Codec 与 StreamCodec（:28-36）。记录点在 `api/OwnableBlockEntity.java:20,31-43`：owner 随 BE NBT 存盘；`setOwner(:71-75)` 即转移。比较逻辑在 `Owner.isTreatedTheSameAs(:110-124)`：先查同队（`util/TeamUtils.java:25-33`，支持 FTB Teams，插件在 `compat/ftbteams/`），再 UUID、最后回退按名字——为旧档没存 UUID 的数据留了迁移路径。

拦截点**不在 menu、也不在统一事件**，而是分散在服务端权威位置：自定义包 handler 里逐一复查（如 `network/server/MountCamera.java:39-46` 校验 `be.isOwnedBy(player) || be.isAllowed(player)` 才允许上车；13 处 `notOwned` 提示分布在 `items/Universal*Item` 与包 handler）；`api/ILockable.java:30-42` 把"被声呐系统锁住"实现为按 `BlockEntityTracker` 范围查询而非每 tick 扫区块。menu 只兜底 `stillValid`（如 `inventory/BlockChangeDetectorMenu.java:86-88`）。防伪报的关键在密码链路：客户端永远拿不到盐与哈希（`api/OwnableBlockEntity.java:57-59` 的 `getUpdateTag` 用 `PasscodeUtils.filterPasscodeAndSaltFromTag` 过滤后才同步），改密用 PBKDF2（65536 次迭代，`util/PasscodeUtils.java:154-156`）且哈希在独立线程队列里做（:62-64，避免卡主线程）；校验在 `network/server/CheckPasscode.java:78-95`——先查玩家级/方块级双重冷却（:78-89），再服务端重算哈希 `Arrays.equals`（:91-94）。盐表存 `SavedData`（`misc/SaltData.java:20-38`）。`network/server/CheckPasscode.java:53-63` 的构造器注释表明客户端连明文密码都不发——发包前已做无盐哈希。

### 4.2 相机与离屏取景（问题①，本报告重点）

**申请**：每路"画框↔相机"画面按相机坐标 `GlobalPos` 建一个 feed（`entity/camera/FrameFeedHandler.java:57` 的 `ConcurrentHashMap<GlobalPos, CameraFeed>`，:263-267 惰性 computeIfAbsent）。`entity/camera/CameraFeed.java:47-56` 构造时 `new TextureTarget("securitycraft:frame", resolution, resolution, true, RGBA8)`（:50），分辨率取自 client 配置 `frame_feed_resolution`（默认 512，范围 1~16384，`ConfigHandler.java:77-79`）；同时为每路 feed 申请独立的雾 uniform 环形缓冲（:51），避免离屏渲染污染主画面的雾参数缓冲。

**怎么"不显示到主屏幕地取画面"——它根本不读像素**：渲染时机是 `mixin/camera/GameRendererMixin.java:32-36` 注入 `GameRenderer.render`，恰在主世界渲染完、GUI 渲染前调 `captureFrameFeeds`。该函数（`FrameFeedHandler.java:62-208`）复用**整套 vanilla 关卡渲染管线**：造一个隐形 `Marker` 实体当摄影机位（:102，注释说明用独立实体而非搬玩家，是为了让玩家画框里能看到自己），把窗口临时改 100×100 且强制 1:1 比例（:109-110），逐 feed 换入 `gameRenderer.mainRenderTarget`（:143）、skyRenderer 的 target（:138）、camera 的 `attributeProbe`（:139，防止离屏位置的大气属性写回主 probe），再把 `levelRenderer.visibleSections` 换成该 feed 自己算出的可见 section 列表（:135，进入前 :86 先克隆原列表、退出后 :198-199 恢复），然后调 `extract + renderLevel` 渲进 feed 自己的 RenderTarget。产物纹理以 `getColorTextureView()` 直接交给画框的 BER 采样显示（`renderers/FrameBlockEntityRenderer.java:240-245`），全程无 GPU→CPU 回读。

**能否看别的位置/别的玩家**：能看任意已加载位置的"该处画面"——feed 的视角完全由相机方块决定（`FrameFeedHandler.java:126-128` 取相机 BE 存储的俯仰/旋转/玩家云台转向），与该玩家在哪无关；另一玩家骑上相机则是另一套机制（`SecurityCamera` 实体 + `CameraController.java:58-115`，头部旋转经 `ServerboundMovePlayerPacket.Rot` 同步给旁人看，:99-104）。跨维度寻址用 `GlobalPos`（画框存的相机列表 `blockentities/FrameBlockEntity.java:40-42`），但**捕获时要求观察者与相机同维度**（`FrameFeedHandler.java:116`），画面本身不跨维度传输。

**每帧成本与降频/降分辨率策略**：(a) 全局帧预算轮转——`getFeedsToRender:236-261` 把 `frame_feed_fps_limit`（默认 30，`ConfigHandler.java:81-83`）摊到所有 feed 上，每个 feed 记录 `AtomicDouble lastActiveTime`，单 tick 只渲"到期的前 ceil(fps×feed数/当前FPS) 路"，多画框时自动降单路帧率而非卡顿；(b) 视锥门控——只有当某个画框在玩家自己的视锥里可见（`CameraFeed.updateHasFrameInFrustum:140-156` + `FrameFeedHandler.doFeedFrustumCheck:305-309`，由 `onExtractLevelRenderState:226-234` 每帧驱动）才捕获该 feed（:123-124 `continue`），没人看的画面零成本；(c) 渲染距离四重取小——`getFrameFeedViewDistance:335-339` = min(画框本地设置, client 配置, server 配置, 玩家视距)；(d) section 级增量发现——`CameraFeed.discoverVisibleSections:66-107` 从起点 section 做 BFS，只有编译完成的 mesh 报告 `facesCanSeeEachother`（:109-116）才扩邻居，未编译的留在重试队列（:80-83），配合 `updateVisibleSections:118-129` 的视锥过滤得到 `visibleSections`。

**释放**：`CameraFeed.close:170-174` 清画框链接并 close 雾缓冲；`isClosed` 在没有任何画框观看时自动为 true（:176-178），`FrameFeedHandler.onClientTickPost:210-224` 客户端 tick 回收，断链/换维度走 `removeAllFrameLinks:281-286`。注意：**RenderTarget 纹理本体没有任何显式 close/destroy**（全库 grep `renderTarget` 仅见换绑与取视图，无释放调用），512² RGBA8（约 1MB/路）依赖 vanilla 的 GPU 对象追踪器随 GC 回收——是否可靠未验证，见第 7 节第 5 条的警示。渲染抛异常时 feed 被永久关闭并提示玩家（:151-156），故障隔离干净。

换绑-渲染-还原的核心几行（`FrameFeedHandler.java:135-149` 摘录）：

```java
feed.applyVisibleSections(mc.levelRenderer.visibleSections);   // :135 塞入该 feed 自己的可见 section 集
mc.levelRenderer.skyRenderer().renderTarget = newRenderTarget; // :138 天空渲染器也换靶
camera.attributeProbe = feed.attributeProbe();                 // :139 每 feed 独立大气/雾探针
mc.gameRenderer.mainRenderTarget = newRenderTarget;            // :143 主渲染靶切换
mc.gameRenderer.extract(DeltaTracker.ONE, true);               // :147 用相机视角提取渲染状态
mc.gameRenderer.renderLevel(DeltaTracker.ONE);                 // :149 渲进离屏靶
```

若"AI 看画面"需要的是 CPU 可读像素而非纹理视图，SecurityCraft 没有现成代码可抄——它从未回读；最短路径是在 :149 之后对 `feed.renderTarget()` 调 `copyTextureIntoBuffer`/blit 到 staging buffer（新版 RenderTarget 自带缓冲拷贝能力，具体 API 名未验证），并务必放在同一 save/restore 区内，否则会读到未完成 GPU 提交的帧。

### 4.3 检测类方块与限频（问题③）

仓库里没有"移动探测器"这个名字，检测职责由激光场、用户名记录器、inventory 扫描仪、方块变化探测器分担。共同点：**不做任何周期性全量扫区块，全部事件驱动 + 冷却节流**。各设备的做法：

- 激光束：实体碰触 `LaserFieldBlock.entityInside` 才触发（`blocks/LaserFieldBlock.java:73-77` 先精确复核碰撞箱形状，防擦边误报），再沿反方向找发射端；找到后 500ms 内不重复翻转红石（`timeSinceLastToggle()<500`，`blocks/LaserFieldBlock.java:88-92` 与 `blockentities/LaserBlockBlockEntity.java:204-217` 同一套节流）。
- inventory 扫描仪：`blockentities/InventoryScannerBlockEntity.java:75-83` 每 tick 只做两个 cooldown 递减，红石输出到期才翻转——把"检测"外包给容器变更事件（`containerChanged`，`LaserBlockBlockEntity.java:265-293` 同理），tick 里零扫描。
- 用户名记录器：`blockentities/UsernameLoggerBlockEntity.java:50-58` 是检测类方块里少见的每 tick 半径 `getEntitiesOfClass`，但过滤谓词里带 `wasPlayerRecentlyAdded` 超时去重（:119-123），同一玩家不会反复触发记录与联动。
- 警报器：`blockentities/AlarmBlockEntity.java:48-75` 声音按玩家距离平方算音量、逐人定向发 `ToggleAlarmSound` 包而非全世界播放，冷却 `soundLength*20` tick；停音时同样只发给范围内玩家（:50-56）。
- 声呐安保系统（SSS）：`blockentities/SonicSecuritySystemBlockEntity.java:83-145` 非激活直接 `return`，`pingCooldown/powerCooldown/listeningTimer` 三级计时器构成休眠-唤醒状态机。
- 基础设施：`misc/BlockEntityTracker.java:31-37` 六个全局追踪器（各自带 range 函数，如 `SECURE_REDSTONE_INTERFACE_RECEIVER` 用 `Integer.MAX_VALUE` 表示全维可达）以空间索引替代扫描，`SCEventHandler.onEntityTeleport:554-562` 这类全服事件只查 tracker 半径内的 BE。

近似手段也有一处：`ILockable.isLockedBySSS`（`api/ILockable.java:30-42`）判断"是否被锁"不遍历链接表，而是按距离反查附近 SSS——牺牲精确性（同坐标跨维度会误判，见第 8 节末）换取每次交互 O(附近SSS数) 的成本。

### 4.4 联动与告警链路（问题④）

链路用**坐标绑定的图**表达：`api/LinkableBlockEntity.java:74-115` 双向 link 存 `api/LinkedBlock.java:10-14`（`blockName + BlockPos`，Codec 加 LEGACY_CODEC 兼容旧档 :16-22），`propagate(:158-180)` 以 sealed `ILinkedAction`（record 模式匹配见 `LaserBlockBlockEntity.java:184-221`）做 BFS 传播，`excludedBEs` 列表防环。因为是 `BlockPos`，**方块-方块联动只支持同维度**；SSS 例外——`SonicSecuritySystemBlockEntity.java:59` 存 `List<GlobalPos>`（寻址含维度，但校验有 bug，见"做坏了"）。告警的物化形式统一是：翻转方块 `POWERED` 属性 + `BlockUtils.updateIndirectNeighbors` + `level.scheduleTick(pos, block, signalLength)` 自卸载脉冲（`LaserFieldBlock.java:89-103`），即告警链路最终都落回原版红石，Alarm 再吃红石信号发声。探测端与执行端之间没有线，只有"链接列表 + 红石"两级。

### 4.5 模块与选项系统

安全方块的"可玩性参数"不走配置文件，而是物品化模块 + 类型化选项：`api/CustomizableBlockEntity.java`（配合 `IModuleInventory`）管理插入的 `ModuleType`（红石输出、智能、伪装、伤害、白名单等，见 `LaserBlockBlockEntity.acceptedModules:341-345`），模块开关经 `toggleModuleState`（`api/CustomizableBlockEntity.java:61`）触发 `onModuleInserted/Removed` 回调；每块方块的 GUI 选项统一建模为 `api/Option.java:23` 的泛型 `Option<T>`，子类如 `DisabledOption(:195)`、`IgnoreOwnerOption(:206)`、`SignalLengthOption(:296)`，选项列表由 `customOptions()` 声明（`LaserBlockBlockEntity.java:347-352`）、自动存 NBT 并自动出现在通用定制界面（`screen/CustomizeBlockScreen.java`）。这套"选项即对象、模块即物品"让 65 个 BE 共享同一条配置 UI 与同步链路，是该 mod 内容量膨胀却不再堆代码的主因。

### 4.6 强化方块与内容聚合

`SCContent.java`（3219 行，内含 141 处 `DeferredHolder` 声明并经循环批量生成变体）集中注册全部内容；`SecurityCraft.collectSCContentData:149-211` 用注解（`@Reinforced`/`@HasManualPage`）反射扫描 SCContent 字段，构建 `IReinforcedBlock.VANILLA_TO_SECURITYCRAFT` 双向映射并自动生成游戏内手册页——注册表与文档同源，加一个方块自动进手册。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 自定义包 46 个（`network/client` 9 个 + `network/server` 37 个），每个 payload 自带 `Type + STREAM_CODEC + handle(IPayloadContext)`，在 `RegistrationHandler.java:179+` 统一注册且通道 `versioned(模组版本)`——版本不匹配直接断连，省去包兼容包袱。命名即语义：C2S 全部是祈使意图（Check/Set/Sync/Toggle/Remove），S2C 全是状态推送。
- 数据驱动程度中等：配方/战利品/标签/tag/模型全有 datagen（`datagen/` 14 个生成器，`build.gradle` data run 输出到 `src/generated/resources` 并打进 main resources）；但联动关系、权限、选项不是数据包驱动，而是 BE NBT + `DataComponentType`（`components/` 11 个，如 `SSS_LINKED_BLOCKS` 直接把链接列表存进物品组件，`items/SonicSecuritySystemItem.java:57-64`）。
- 配置三档：
  - SERVER 主 spec（`registerConfig`，`SecurityCraft.java:90`）：`laserBlockRange`、`inventoryScannerRange`、`maxAlarmRange`、`enableTeamOwnership`、`vanillaToolBlockBreaking`、`frameFeedViewingEnabled/frameFeedViewDistance`（`ConfigHandler.java:110-116,217-243`）等防作弊与总开关；
  - CLIENT（`SecurityCraftClient.java:14`）：取景三键 `frame_feed_render_distance` 默认 16（2~32，`ConfigHandler.java:73-75`）、`frame_feed_resolution` 默认 512（1~16384，:77-79）、`frame_feed_fps_limit` 默认 30（10~260，:81-83）；
  - 编译期互操作开关若干（FTB/JEI/Jade 等仅作 compileOnly 依赖，见 `gradle.properties` 依赖区）。

## 6. Mixin / ASM / 接口注入

无 ASM，纯 NeoForge Mixin（内嵌 mixinextras，`securitycraft.mixins.json` 声明 39 个 mixin，相机相关者统一 `priority=1100`，如 `GameRendererMixin.java:16`）。按目的分组：
- `mixin/camera/`（15 个，核心）：`GameRendererMixin` 捕获钩子 + 离屏去畸变（:20-27）；`LevelRendererMixin:44-82` 接管 `compileSections` 的 section 来源（接 `CameraViewAreaExtension`）、跳过离屏期的遮挡图更新与相机重定位；`ClientChunkCacheMixin:48-111` 让客户端保留相机视距内的额外区块（`shouldAddChunk` 判据，`FrameFeedHandler.java:296-303`）；`ChunkMapMixin:48-114` 服务端为被观看的相机强推区块；`PlayerListMixin:24-37` 把音效坐标换算到相机位（听声辨位跟着画面走）；`ServerPlayerMixin` 阻止服务器把骑相机的玩家拽回相机坐标；`FogRendererMixin/CloudRendererMixin/LevelExtractorMixin/GuiMixin/LocalPlayerMixin/MinecraftMixin/TrackedEntityMixin/SectionUpdateTrackerMixin/CameraMixin` 收尾细节（雾色、云、GUI 屏蔽、拾取取消等）。
- 其余：`mixin/mines`（刷怪蛋/矿车行为）、`mixin/reinforced`（漏斗抽料、传送门、工具材质等拦截，配合 `IExtractionBlock`）、`mixin/passcode/ServerGamePacketListenerImplMixin`、`mixin/datafix`（8 个存档升格修复——这解释了 `Owner` 里"名字回退"的历史包袱）、`mixin/f3`（BetterF3 适配）、`mixin/taser`。
- 接口注入：`mixin/camera/ClientChunkCacheMixin.java:37` 让 `ClientChunkCache` implement mod 自己的 `IChunkStorageProvider`（`misc/IChunkStorageProvider.java`）——标准的"给原版类加能力"模式。另有 `accesstransformer.cfg`（`src/main/resources/META-INF/`）。

**与现代优化 mod 的兼容（问题⑤）**：
- Sodium/Embeddium（二者统称 IUM）：抽象接口 `compat/ium/IumCompat.java:26-33` 按 `ModList` 选择实现，`compat/ium/Sodium.java:9-15` 直接调 Sodium 的 `ChunkTrackerHolder.onChunkStatusAdded/Removed`——因为相机视距外额外区块是 SecurityCraft 自己塞进客户端的，不通知 Sodium 自己的区块图就会花屏；消费点在 `entity/camera/CameraClientChunkCacheExtension.java:249,289`。`mixin/camera/LevelExtractorMixin.java:39` 在离屏捕获期且无 IUM 时跳过原版提取路径。
- Iris：`mixin/camera/GameRendererMixin.java:29-31` 的原话注释——把捕获钩子放在"主世界渲染后、GUI 渲染前"正是为了修 Iris 共存时的屏幕闪烁；即它把 Iris 当作必须共存的一等公民。
- Distant Horizons：`compat/distanthorizons/DistantHorizonsCompat.java:12-27`，注册 DH 的 beforeRender 事件，`isCapturingCamera()` 期间直接取消 LOD 渲染（离屏靶里没有 DH 的上下文）。
- Lithium/EntityCulling：全源码 grep 无任何专项处理（未发现引用）；批量实体剔除兼容交给 mixin 时机而非代码配合。
- 自建批渲染：**没有**。`renderers/` 40 个文件都是常规 BER/GUI 绘制；离屏画面成本靠复用 vanilla 的 section 网格批渲染（4.2 节）摊薄，唯一的渲染减负开关是配置 `more_performant_sri_rendering`（`ConfigHandler.java:60-62`，关掉红石接口的旋转圆盘动画）。

## 7. 值得学的 5 条

1. **全局帧预算 + 视锥门控的离屏渲染调度**——`entity/camera/FrameFeedHandler.java:236-261`（fps 摊薄轮转）与 :123-124 + `CameraFeed.java:140-156`（画框不可见则整路 feed 零成本）。为什么值得抄："AI 看画面游玩"往往要多路视角（主视角/俯视图/目标特写），这两段代码给出了"N 路相机共享固定 GPU 预算、且没人看就不渲"的完整答案，且与帧率解耦（用 `glfwGetTime` 而非 tick 计数）。
2. **换绑全局渲染状态 → 复用 vanilla 渲染器 → 精确还原**的一进一出结构——`FrameFeedHandler.java:82-110`（保存相机/窗口/可见集/渲染靶/雾探针等二十余项状态）与 :176-207（逐项还原 + 重跑 `gui.extractRenderState` 修正 GUI）。离屏渲染最易犯的错就是"忘还原某个全局态"导致主画面花屏；这份 save/restore 清单可直接当 checklist 抄。第二摄影机用一次性 `Marker`（:102）而不搬玩家，避免了位置包反馈环。
3. **增量 section 发现代替球状扫描**——`CameraFeed.java:66-107`：从相机所在 section BFS，靠已编译 mesh 的 `facesCanSeeEachother`（:109-116）决定是否扩边，未编译节点留在重试队列（:80-83）。给"渲染另一位置的景象"提供了免全视距扫描的可见集算法，成本与真实可见体积成正比。
4. **密码学的工程化落地**——`util/PasscodeUtils.java:62-64,154-156`（PBKDF2 65536 次迭代 + 专职哈希线程队列）+ `api/OwnableBlockEntity.java:57-59`（同步前过滤盐/哈希）+ `network/server/CheckPasscode.java:53-63,78-95`（客户端预哈希防明文过网、双重冷却防爆破、服务端重算比对）。任何"玩家设访问口令"的功能（护山大阵阵眼、洞府禁制）该照这套走，而不是把口令明文进 NBT。
5. **故障隔离：渲染异常只熔断单路 feed**——`FrameFeedHandler.java:145-156` catch 后 `feed.close()` + 给玩家可追溯的聊天栏报错，坏画面不会带崩整个客户端。多视角 AI 采样同理：某路视角构造失败（资源缺失/模组冲突）时应降级为黑帧并记录，而非拖垮主渲染循环。警示配套：它**没有**显式 close RenderTarget（`CameraFeed.java:170-174` 只关雾缓冲），做 AI 取景器时请把 `renderTarget.close()` 补进 close()。

## 8. 公开 API

`api/SecurityCraftAPI.java` + IMC 是官方扩展面（`SecurityCraft.java:109-123` 展示全部入站消息类型）：第三方可注册"可被破坏者挖掘的方块"（`IExtractionBlock`）、"可被密码器转换的方块"（`IPasscodeConvertible`，如把原版箱子转成 keypad 箱子）、"哨兵攻击目标判定"（`IAttackTargetCheck`）、"开门器"（`IDoorActivator`）。对外的还有 `ILinkedAction` 联动协议与 `ILockable`/`IOwnable` 接口（自己的方块实现后可直接加入激光/SSS/归属生态）。HUD mod 兼容面在 `compat/hudmods/`（TOP/Jade/WTHIT 三家 Provider）。

### 结论：对读者三个项目的落点（问题⑥）

- **AI 看画面游玩**，可搬两条：(1) `FrameFeedHandler.captureFrameFeeds`（`entity/camera/FrameFeedHandler.java:62-208`）的"save/restore 全局渲染态 + Marker 摄影机 + 独立 RenderTarget"骨架，AI 侧把 :143 的 `mainRenderTarget` 换成自建 `TextureTarget` 后加一次 `copyTextureIntoBuffer` 回读即得 CPU 像素，配 :236-261 的帧预算器以 2~5 FPS 采样即可把成本压到无感；(2) `CameraFeed.java:48-56 + 140-156` 的按需申请/视锥休眠——AI 观察器只在对应区块进入某个真实玩家视野（或调试窗打开）时才激活，其余时间 close，避免服务器端隐形渲染负担。
- **「求仙问道」护山大阵**，可搬一条：4.4 节的"归属 + 告警"组合——阵眼节点用 `Owner` 值对象（含队伍语义，`api/Owner.java:110-124`）记录归属，入侵检测用 `LaserFieldBlock.entityInside`（`blocks/LaserFieldBlock.java:73-103`）式的"事件驱动 + 500ms 翻转节流 + scheduleTick 自卸载脉冲"，联动走 `LinkableBlockEntity.propagate` 的坐标图，天然复用红石做执行层。
- **做坏了的一处**：SSS 的跨维度寻址名存实亡——`blockentities/SonicSecuritySystemBlockEntity.java:59` 用 `List<GlobalPos>` 保存链接（维度信息在场），但每 tick 的失效校验（:123-136）只拿 `globalPos.pos()` 查**自己所在维度**的 BE，`isLinkedToBlock(:234)` 与 `api/ILockable.java:35` 的比较也只看坐标不看维度：一旦物品组件（`items/SonicSecuritySystemItem.java:57-64` 允许存任意 GlobalPos）里带了异维度链接，tick 要么误删本维度恰好同坐标的无辜链接、要么永远校验不到真目标。教训：选了 `GlobalPos` 就要一路带到所有查询点，或者干脆一开始就用 `BlockPos` 并在 UI 禁跨维度。它自己的设计意图是支持跨维度（存了 GlobalPos），所以这是缺陷而非取舍。
