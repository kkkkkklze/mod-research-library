# FTB Quests 源码分析报告

分析对象：`源码库\_参考仓库\_bulk\FTBTeam__FTB-Quests`（GitHub FTBTeam/FTB-Quests，main 分支快照，git ff6cd47）。
所有 `路径:行号` 为仓库根相对路径，均经逐文件回读核实。

## 1. 基本信息

- **mod_id**：`ftbquests`（`gradle.properties:5`）；显示名 "FTB Quests"，作者 FTB Team（`neoforge/src/main/resources/META-INF/neoforge.mods.toml` 的 `[[mods]]` 段，约 :9-13 行）。
- **许可证**：All Rights Reserved（`neoforge/src/main/resources/META-INF/neoforge.mods.toml:4`）。
- **目标 MC 与加载器**：minecraft_version=26.1.2、NeoForge 26.1.2.76、fabric-loader 0.18.6 + fabric-api（`gradle.properties:15,21,25`）。
- 注意：这是 Mojang 新日期版本号时代的 main 分支，**不是** 1.20.1/1.21.1 经典分支；迁移到 1.21.1 时类名映射有差（如 `ResourceLocation` 已改名 `net.minecraft.resources.Identifier`，见 `TaskTypes.java:9`）。
- **Gradle 插件与工程结构**：multiloader 三模块 `include "common", "fabric", "neoforge"`（`settings.gradle:10`）；fabric-loom 1.15.2 与 net.neoforged.moddev 2.0.140 双插件（`build.gradle:3-4`），mod-publish-plugin 负责发布；common 源码被子模块 `api project(":common")` + jar 合入复用。
- **Java 版本**：`options.release = 25`（`build.gradle:31`）。
- **发布坐标**：`dev.ftb.mods:ftb-quests(-neoforge|-fabric)`，mod 主版本 7（`gradle.properties:8,11,12`），依赖 ftb-library / ftb-teams 同版本线（`gradle.properties:29-30`）。

## 2. 源码规模与包结构

实测：403 个 `.java`，总行数 37,380（`find -exec cat + | wc -l`）。

- 速览卡片写 37,783，恰差 403——是"每文件缺行尾换行各计 +1"的统计口径差，真实 wc 口径为 37,380。
- 按模块：common 346 文件/34,439 行；fabric 21/828；neoforge 36/2,113（含 `neoforge/src/test` 下 14 个 gametest 文件）。
- 卡片中的 "Forge" 目录特征在本快照不存在（无 forge/ 模块，只有 fabric+neoforge）。
- resources 基本完整：common 有 assets/ 与 mixin 配置、accesswidener；neoforge 侧仅 mods.toml；未发现源码树缺口的目录特征（无 API/Client/Command 之外的幽灵包）。

主要包（common 侧，按文件数）：`net` 67、`quest/task` 25、`client/gui/quests` 25、`quest` 22、`client/gui` 22、`client` 20、`quest/reward` 19、`command` 15、`theme/selector` 11、`block/entity` 11、`util` 10、`quest/history*` 15、`api*` 18、`quest/loot` 5。近三分之一代码是客户端 GUI。

最大源文件（实测行数）：

| 文件 | 行数 |
|---|---|
| `common/.../quest/BaseQuestFile.java` | 1659 |
| `common/.../quest/Quest.java` | 1225 |
| `common/.../client/gui/quests/ViewQuestPanel.java` | 1127 |
| `common/.../client/gui/quests/QuestScreen.java` | 1009 |
| `common/.../client/gui/quests/QuestPanel.java` | 880 |
| `common/.../quest/TeamData.java` | 854 |
| `common/.../client/gui/MultilineTextEditorScreen.java` | 750 |
| `common/.../quest/Chapter.java` | 554 |
| `common/.../client/gui/quests/QuestButton.java` | 547 |
| `common/.../quest/loot/RewardTable.java` | 495 |
| `common/.../quest/QuestObjectBase.java` | 495 |

## 3. 入口与注册

公共入口 `FTBQuests` 构造函数完成全部"注册"（`common/src/main/java/dev/ftb/mods/ftbquests/FTBQuests.java:39-59`）：

```java
public FTBQuests() {
    FTBQuestsAPI._init(FTBQuestsAPIImpl.INSTANCE);
    eventHandler = new FTBQuestsEventHandler();
    TaskTypes.init();  RewardTypes.init();  FTBQuestsNetHandler.init();
    ModDataComponents.register(); ModBlocks.register(); ModItems.register(); ModBlockEntityTypes.register();
    Platform.get().addDataPackReloadListener(..., new TagReloadListener());
```

- 任务/奖励类型注册表是静态 `LinkedHashMap<Identifier,TaskType>`（`quest/task/TaskTypes.java:18-23`）；奖励侧 `quest/reward/RewardTypes.java:17-37`。
- 67 个网络包在 `net/FTBQuestsNetHandler.java:6-73` 逐条 `registerC2S/registerS2C`（该文件即全部报文清单）。
- 注册表对象（物品/方块/BEE/数据组件）走 `registry/` 包，平台无关。
- 加载器侧：NeoForge `@Mod` 入口构造 `FTBQuests` 后把平台事件桥接给 `NeoEventHandler`（`neoforge/.../neoforge/FTBQuestsNeoForge.java:29-56`，并向总线注册能力与事件海报）；Fabric 由 `FTBQuestsFabric implements ModInitializer` 做同构桥接（`fabric/.../fabric/FTBQuestsFabric.java:32-56`）。
- 游戏事件订阅点集中在 `FTBQuestsEventHandler`：击杀（:97-117）、玩家 tick（:119-140）、合成/熔炼（:142-152）、进维度（:172-186）、开容器（:188-192）、登录/建队/换队（:85-95）；两个加载器只是喂事件的适配器不同。

## 4. 核心系统

### 4.1 数据模型与对象图（问题①）

树形拥有 + 全局 id 索引：`BaseQuestFile`（id=1）→ ChapterGroup → Chapter → Quest → Task/Reward，另有平级的 RewardTable、QuestLink、ChapterImage；所有对象注册进一张 `Long2ObjectOpenHashMap<QuestObjectBase> questObjectMap`（`quest/BaseQuestFile.java:93,344-365`）。

- id 是随机 long（`readID`，`BaseQuestFile.java:1230-1241`），序列化为 16 位十六进制 `"%016X"`（`QuestObjectBase.java:78-80`），另支持 `#tag` 反查（`BaseQuestFile.java:1275-1284`）。
- **跨对象引用一律用 id 存盘、装载时解析成对象引用**：依赖存 id 列表再逐个 `get(id)` 还原（`Quest.java:289,953-957`）；RandomReward 只存 `table_id`（`RandomReward.java:107-124`）。
- 装载是**两遍式**：第一遍扫 `chapters/*.json5`、`reward_tables/*.json5` 只建骨架（对象 new 出来进 id 图，原始 JSON 暂存 `dataCache`），第二遍才逐对象 `readData`（`BaseQuestFile.java:576,590-651`）——前向/交叉引用因此永远解析到已存在对象。
- 文件布局：`data.json5` + `chapter_groups.json5`（`BaseQuestFile.java:482-563`）+ `chapters/<文件名>.json5`（`Chapter.java:398`）+ `reward_tables/*.json5`（`RewardTable.java:391`）+ `lang/` 翻译目录（`BaseQuestFile.java:586`）。
- **编辑期与运行期是同一份对象**：ServerQuestFile 装载出的活对象树就是判定/发奖用的树；编辑器改的就是这些对象（客户端改完经 `EditObjectMessage` 在服务器端活对象上重放并标脏回写文件，`EditObjectMessage.java:52-57`、`ServerQuestFile.java:177-194`）。
- 缺失引用兜底：装载后 `removeInvalidDependencies()` 剔除失效依赖（`BaseQuestFile.java:653-661`、`Quest.java:974-985`）；未知 task type 时 `createTask` 返回 null 静默跳过该任务（`BaseQuestFile.java:751-756`、`TaskType.java:49-53`）；但**网络同步**遇未知 type 直接抛异常——client/server mod 集不匹配属致命错（`BaseQuestFile.java:1044-1049`）。
- 循环引用：`verifyDependenciesInternal` DFS，环抛 `DependencyLoopException`、深度≥1000 抛 `DependencyDepthException`（`Quest.java:819-839`）；加载时可选校验（`verify_on_load`，`BaseQuestFile.java:668-670`），编辑时校验失败则**清空该任务全部依赖**并在 GUI 报错（`Quest.java:777-789`）。
- 奖励表的子奖励挂在一张 `fakeQuest`（id=-1 的哨兵 Quest）上并整体内联存进表文件（`RewardTable.java:60-90,165-185`），其子奖励也注册进全局 id 图（`refreshRewardTableRewardIDs`，`BaseQuestFile.java:367-369`）。

### 4.2 任务检测器体系（问题②）

离散类型 = 注册表：每个 Task 子类声明 `TaskType`；注册表按 Identifier 索引并分配 `internalId` 供网络编码（`TaskTypes.java:18-23`）；内置 14 种类型（item/kill/stat/checkmark/advancement/custom…，`TaskTypes.java:25-54`）；addon 注册实例见 NeoForge 能量任务（`FTBQuestsNeoForge.java:31-33`）。

匹配策略是**按事件类型预筛任务清单、再遍历小清单**——不是倒排索引，也不是全量遍历任务：

- `FTBQuestsEventHandler` 持三张 `Lazy<List<…>>` 缓存：killTasks、dimensionTasks、autoSubmitTasks（`FTBQuestsEventHandler.java:38-43`），文件热重载时统一失效（`67-77`）。
- 击杀事件只遍历 killTasks 且先查"未完成+可开始"（`:104-116`）；玩家 tick 只遍历 autoSubmit 任务并按 `gameTime % interval == 0` 门控（`:119-140`）。
- 背包变化的物品检测遍历 `file.getSubmitTasks()` / `getCraftingTasks()` 两条预过滤缓存清单（`util/FTBQuestsInventoryListener.java:22-41`；构建与缓存在 `BaseQuestFile.java:1343-1363,1210-1224`）。
- 真正近似倒排的是背包侧：`PlayerInventorySummary` 每次检测前把玩家背包做成 `Map<Item,List<ItemStack>>`，ItemTask 按 item 键取候选（`util/PlayerInventorySummary.java:15-35`、`ItemTask.java:288-298`）。

限流与缓存：

- 槽位变化不立即检测，按 `detection_delay`（0..200 tick，默认 20，`BaseQuestFile.java:78,464`）经 `DeferredInventoryDetection.scheduleInventoryCheck` 做**每玩家合并去重**（`putIfAbsent` 截止时间，窗口内多次变动只排一次，`util/DeferredInventoryDetection.java:35-37`），服务器 tick 尾部统一触发（`FTBQuestsEventHandler.java:79-83`、`FTBQuestsInventoryListener.java:48-62`）。
- 假玩家一律跳过（`FTBQuestsInventoryListener.java:18-20`）；`setProgress` 只在值真变化时广播/推事件并 clamp 到 maxProgress（`TeamData.java:593-633`）。

### 4.3 奖励发放链路（问题③）

- 加权表 `RewardTable`：每条 `WeightedReward(reward, float weight)`；掷取为线性累加扫描 `generateWeightedRandomRewards`（`RewardTable.java:128-154`），`getTotalWeight` 单一真相（`:123-126`）。
- 语义细节：weight=0 的条目**无条件全额发放**（`:133-135`）；`empty_weight` 是"空手"槽（`:141-143`）；`nAttempts *= lootSize` 实现一抽多落（`:137`）。同一条目**可以被多次掷中**（多次独立抽，`RandomReward.claim` 对每个抽中结果各发一次，`RandomReward.java:171-179`）——这是设计而非重复发放。
- 关键防重放闸门：**先记账后发货**。`claimReward = markRewardAsClaimed(...)` 仅当 `claimedRewards`（键 `QuestKey(playerUUID, objectId)`）发生"从无到有"迁移时才执行 `reward.claim`（`TeamData.java:281-309,528-532`）。重复领取包、断线重发、`/ftbquests change progress` 强制补发都不会把同一倍率/同一计数乘两次——"只生效一次"由 map 迁移保证。
- 重复计数同样只加一次：`completionCount.merge(+1)` 只在 `resetProgressIfRepeatable` 返回 true 时执行，而它要求"该任务**全部**奖励已被该玩家领完"这一条件首次成立（`TeamData.java:297-303`；`Quest.java:868-874` 的 `allMatch(isRewardClaimed)`）。
- 可重复与上限机制：repeat 冷却写绝对毫秒时间戳 `questRepeatableTime`（幂等读回，`TeamData.java:261-268,300-302`）；全局 `rewardsBlocked`（`:227-248`）；逐奖励 `exclude_from_claim_all` / `ignore_reward_blocking`（`Reward.java:85-86,99-100`）；`suppress_all_autoclaiming` 一刀切（`BaseQuestFile.java:470`）。
- **保底：全源未见任何 pity/计数器兜底**（检索 RewardTable、RandomReward、loot 包均无；只能标记为"确认此快照不存在"）。ChoiceReward 是"随机表+玩家重选"变体（`ChoiceReward.java` 整文件，claim 交给 `ClaimChoiceRewardMessage`）。

### 4.4 进度持久化与同步（问题④）

- 进度键是**团队**（单人 = 玩家个人"队"，依赖 FTB Teams），存 `world/ftbquests/<teamUUID>.json5`，与任务定义（config 目录）物理分离（`ServerQuestFile.java:38,81,100-118`）；落盘走 `saveIfChanged` 标脏制，随世界保存与停服触发（`TeamData.java:142-152`、`FTBQuestsEventHandler.java:57-65`）。
- 内存核心是 6 张 fastutil 稀疏 map：taskProgress/started/completed/completionCount/questRepeatableTime/claimedRewards（`TeamData.java:73-79`），落盘用 `Json5Ops.COMPRESSED`（id 压缩，`TeamData.java:348-363`、`util/FTBQCodecs.java:27-33`）。
- 重启一致性：加载即整体反序列化；任务文件 `fileVersion != VERSION` 时标脏强制重写升级（`BaseQuestFile.java:678-680`）；进度文件同理（`TeamData.java:365-368`）。
- 跨端同步是"**登录全量 + 之后增量**"：登录先发整本书 `SyncQuestsMessage`（手写 buf 全量序列化 `writeNetDataFull`，含类型 internalId 字典，`BaseQuestFile.java:898-988`），客户端建好 ClientQuestFile 后回 `RequestTeamDataMessage`，服务器才发本队 `SyncTeamDataMessage`——两步握手防客户端未就绪（`ServerQuestFile.java:215-227`、`net/SyncQuestsMessage.java:25-31`）。
- 此后一切变化走小粒度包：任务进度 `UpdateTaskProgressMessage`（`TeamData.java:617`）、开始/完成/重置四个对象级包（`:177-208`）、领取回执 `ClaimRewardResponseMessage`（`:294`）、锁定/发奖屏蔽/翻译各一条专线。时间戳同步用 `now - value` varlong 差值压缩（`TeamData.java:395-419,436-451`）。
- 换团语义：入队把个人进度 `mergeData` 进大队（进度取 max、集合类并集保旧值，`TeamData.java:682-691`；触发 `ServerQuestFile.java:303-316`）；离队拿回旧个人进度**但已领奖励保持已领**——只并回 `claimedRewards`（`ServerQuestFile.java:317-321`、`TeamData.java:693-700`）。
- 离线补发：登录时 `checkQuestBookOnLogin` 对全部任务重演判定——"进度已满但未判完成"补判、"任务被删光但已满足"补触发 `onCompleted`、跑 `checkAutoCompletion`、按 `Task.checkOnLogin()` 重扫（`ServerQuestFile.java:246-278`）。自动发奖在无人在线时**不入队**，留待下次登录由该扫描补发（`TeamData.java:555-568`）。

### 4.5 编辑工作流（问题⑤）

**本仓库没有内嵌 Web 编辑器**：全源检索 httpserver/sparkjava/websocket/upload 均无命中。任务书中"自带 web UI"的说法在此 main 快照不成立（未找到，疑为旧版印象或外部工具）。实际工作流三层：

- 游戏内编辑模式：op 或 `ftbquests.editor` 权限节点开启（`integration/PermissionsHelper.java:13-22`；`/ftbquests editmode`，`command/FTBQuestsCommands.java:24-36`），每玩家 isEditMode 存服务端 TeamData（`TeamData.java:738-751`），失权时登录自动踢出编辑态（`ServerQuestFile.java:238-241`）；编辑动作以 Create/Edit/Delete/Move 报文发回服务端在活对象树重放，进 `HistoryStack` 支持 undo/redo（`EditObjectMessage.java:52-57`、`quest/history/` 包、`UndoRedoRequestMessage`）。
- 直接改 JSON5 文本 + `/ftbquests reload`（ReloadCommand）：稳定十六进制 id、写盘键序确定（版本控制友好，`BaseQuestFile.java:477-485` 注释），外部编辑器/生成器有完整生存空间。
- 奖励表导出/导入命令（Export/ImportRewardTableCommand，`FTBQuestsCommands.java:29-30`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **序列化三通道同构**：每类对象实现 `writeData/readData`（JSON5 磁盘格式：缺省值不写、读取全部 `orElse(默认)` 容错）、`writeNetData/readNetData`（手写 RegistryFriendlyByteBuf，布尔集合打包成 flag bits，见 `ItemTask.java:107-138`）、`fillConfigGroup`（游戏内编辑表单，同一批字段的第三份映射，`BaseQuestFile.java:1177-1207`）。
- ItemStack 走 Mojang `ItemStack.CODEC × Json5Ops`；解析失败降级为 `MissingItem` 占位而非炸档（`QuestObjectBase.java:94-105`）。
- **为什么是 JSON5 文件而非 datapack**：任务书是**服务端实例可变状态**——存 `<config>/ftbquests/quests`（`ServerQuestFile.java:81`），运行期编辑器会把对象树原样写回同一批文件（`writeDataFull`，`BaseQuestFile.java:477-493`）；datapack 管线只读、需打包分发，承载不了"边玩边改、热重载"。文件头 `VERSION=13` 驱动迁移（`BaseQuestFile.java:80,678-680`）。
- 与 datapack 的接触面只有两处：物品 tag 重载时清显示缓存（`FTBQuests.java:53,89-94`）；RewardTable 可挂原版 `loot_table_id`（`RewardTable.java:249`；编辑器侧 TODO 未实装，`:330`）。无 datagen。
- **配置项**（data.json5 顶层，读写对 `BaseQuestFile.java:409-475`）：`progression_mode`(LINEAR/FLEXIBLE)、`detection_delay`、`emergency_items`+冷却、`loot_crate_no_drop` 权重、`suppress_all_autoclaiming`、`verify_on_load`、`fallback_locale`、`grid_scale`、视觉主题 `presets` 与 defaults 子组。
- 包大小：无压缩分包/分帧机制，整本书一次性 UTF/二进制流（靠 varint、flag bits、时间戳差值、internalId 字典压体积）；`Write {} bytes` 日志直接打字节数（`BaseQuestFile.java:987,1112`）。

## 6. Mixin

common 2 个（清单见 `common/src/main/resources/ftbquests-common.mixins.json`）+ fabric 专用 5 个；**NeoForge 侧零 mixin**（全走总线事件），mixin 只为补齐 Fabric 缺失事件：

- `mixin/ServerGamePacketListenerImplMixin.java`：注入 `handleClientInformation`，玩家语言变化即推送对应语种的任务翻译整表（多语言任务书同步）。
- `mixin/GuiGraphicsMixin.java`：`@Accessor GuiRenderState`，纯取值。
- `fabric/mixin/ResultSlotMixin.java` / `FurnaceResultSlotMixin.java`：注入 `checkTakeAchievements`，桥接"合成完成/熔炼取出"两个检测事件。
- `fabric/mixin/ServerLevelMixin.java`（addEntity→进维度检测）、`ServerPlayerMixin.java`（openMenu→给容器挂槽位监听）、`TextureAtlasMixin.java`（贴图 upload 后触发图标重 stitch，客户端）。
- 另有 accesswidener 4 条（`common/src/main/resources/ftbquests.accesswidener`：BlockEntityType 构造器、ItemTintSources.ID_MAPPER、CompoundTag 可继承）。

## 7. 值得学的 5 条

1. **先记账后发货的幂等领取**（`quest/TeamData.java:281-309` + `528-532`）：claim 是 claimedRewards put-if-absent 成功迁移的唯一副作用，重复请求/重连/命令补发都被 map 挡住——"同一倍率/同一计数只生效一次"由数据结构保证，而非散点 if。
2. **两遍式装载解引用**（`quest/BaseQuestFile.java:576,641-651`）：第一遍建全对象骨架并缓存原始 JSON，第二遍统一填属性，前向/交叉引用零成本成立；缺引用静默降级 + 统一清理，比"解析失败即崩"稳健。
3. **事件合并限流**（`util/DeferredInventoryDetection.java:35-37` + `quest/BaseQuestFile.java:464`）：`putIfAbsent(uuid, now+delay)` 把背包风暴合并成每玩家每窗口一次全量检测，delay 钳制在 0..200 tick；配 `Lazy` 类型清单在热重载时统一失效（`FTBQuestsEventHandler.java:38-43,67-77`）。
4. **类型注册表 + 网络 internalId 协商**（`quest/task/TaskTypes.java:18-23`；`BaseQuestFile.java:901-911,990-1011`）：全量同步先传 `Identifier↔internalId` 字典再传对象，客户端遇未知 type fail-fast，addon 加新类型零协议改动。
5. **登录对账扫描**（`quest/ServerQuestFile.java:246-278`）：任务定义在玩家离线时被改，登录后把结算重演成"对当前定义的纯函数重算"，专治"增量事件丢发/定义漂移后进度卡死"。

### 结论（问题⑥：给 nextCard / 新星殖民地 / 反例）

- **给 nextCard 第 1 条（保底与幂等）**：FTBQ 无保底，但 `completionCount`/`questRepeatableTime` 展示了计数的正确形态——存在玩家维度的 `Object2LongMap<QuestKey>`、随进度文件落盘、且只在"记账迁移成功"时 +1（`TeamData.java:297-303`）。抽卡 pity 照搬：计数器与本次抽卡结果在同一次状态迁移里一起更新，重试/断线恢复时因迁移不再成立而天然不双计。
- **给 nextCard 第 2 条（权重表单一真相）**：`getTotalWeight` 单源 + 线性累加掷取 + weight=0 恒发（`RewardTable.java:123-154`），公示概率走同一个 total 的 `chanceString`（`WeightedReward.java:28-45`）。几十到几百项的卡池线性扫描完全够用，别过早上 alias method；"必出且只进一次"的条目用 weight=0 语义，"抽空"用 empty_weight 槽。
- **给新星殖民地每日任务 1 条**：把每日/到港结算写成登录对账式的可重放全量重算（`ServerQuestFile.java:246-278`），配差值时间戳同步（`TeamData.java:395-419`）——结算正确性不依赖"当时记得发"，正好根治读者踩过的"去重把收入算减半"方向性问题。
- **做坏的一处**：`quest/loot/RewardTable.java:196-197`——`hide_tooltip`/`use_title` 读取默认 `orElse(true)`，但 `writeData` 只在值为 true 时写字段（`:162-163`）、构造默认 false（`:74-75`）：拨到 false 永不落盘，重载后翻回 true，保存/加载往返不对称；同函数 `:195` 的 `lootSize = ...orElse(0)` 与构造默认 1 相反，手写 JSON 漏字段时整表静默抽不出任何奖励。教训：磁盘/网络/表单三通道共享的字段，默认值必须只写一处。

## 8. 公开 API

定位是给整合包作者与 addon 用的库，稳定面收敛在 `dev.ftb.mods.ftbquests.api` 包（Javadoc 明言包外不承诺稳定，`api/FTBQuestsAPI.java:8-14`）。

- **入口**：`FTBQuestsAPI.api()` 单例（`api/FTBQuestsAPI.java:26-28`）；`API.getQuestFile(isClient)` 拿全对象树、`API.registerFilterAdapter(ItemFilterAdapter)` 注册自定义物品过滤器（`:53-56`）。
- **扩展点**：`TaskTypes.register(id, provider, icon)` / `RewardTypes.register(...)` 新增任务/奖励类型（`TaskTypes.java:21-23`；内置例 `FTBQuestsNeoForge.java:31-33`）；`CustomTask` + `CustomTaskEvent` 让 addon 不改注册表即可给单条任务挂 `Check(data, player)` 回调（`quest/task/CustomTask.java:99-131`；事件在装载与创建时广播，`BaseQuestFile.java:672-676`、`Task.java:174-176`）；奖励侧有对称的 CustomReward。任务编辑器 GUI 可替换：`TaskType.setGuiProvider`（`TaskType.java:82-85`）。
- **事件**：`api/event/progress/` 的 File/Chapter/Quest/TaskProgressEvent 与 CustomTaskEvent、ClearFileCacheEvent 等经 `NativeEventPosting` 平台抽象发出，NeoForge 侧贴到总线（`FTBQuestsNeoForge.java:44-56`），Fabric 侧暴露 `FTBQuestsEvents` 回调接口（`FTBQuestsFabric.java:55-56`）；`CustomFilterDisplayItemsEvent` 供 JEI/REI 生态注入。
- **接入方式**：Gradle 依赖 `dev.ftb.mods:ftb-quests-neoforge`（或 -fabric）即可；`RecipeModHelper.setRecipeModHelper` 是 FTB XMod Compat 注入 JEI 联动的后门（`FTBQuests.java:62-72`，二次调用即抛的单例守卫）。任务书数据本身经 JSON5 文件即完整可编程接口（见 4.5），进度数据则是 `world/ftbquests/*.json5`（见 4.4）——外部工具链（批量生成任务、迁移脚本）都走这两处文件契约。
