# Colony Pathing Edition (MineColonies 分支) 源码分析报告

> 仓库: `源码库\_参考仓库\_bulk\ARxyt__ColonyPathingEdition`。本仓库是 MineColonies 1.20.1 的**玩法覆写分支**：不 fork 上游源码，而是以约 127 个 Mixin 覆写 MineColonies/structurize/原版的内部类，重做寻路与市民工作 AI。
> 本报告路径约定：`SRC/` = `src/main/java/com/arxyt/colonypathingedition/`，其余路径相对仓库根。

## 1. 基本信息

- mod_id: `colonypathingedition`（`gradle.properties:25`），作者 arxyt（`gradle.properties:29`），mod 版本 1.0.5-ALPHA-13（`gradle.properties:28`）。
- 许可证: `mod_license=GPL-3.0`（`gradle.properties:27`）。注意它是对 MineColonies 内部类的衍生（`@Overwrite` 直接替换上游方法体），上游仓库的 LICENSE 文件本检出缺失（未验证），但 MineColonies 系是带网络条款 copyleft 的开源协议——**结论：本 fork 的算法思想可自由重实现，源码不可直接搬进闭源/宽松许可工程**，复制即触发 GPL-3.0（及上游协议）传染。
- 目标版本: MC 1.20.1（`gradle.properties:4`）/ Forge 47.3.20（`gradle.properties:7`）；依赖 MineColonies `1.20.1-1.1.1197`，版本区间钉死到 `[1197-snapshot, 1259-snapshot]`（`gradle.properties:10-12`）——`@Overwrite` 式分支必须钉上游快照。
- 依赖面（`build.gradle:104-121`）: MineColonies + structurize/multipiston/domum_ornamentum/blockui 全家桶走 `implementation fg.deobf`（`:108-115`，structurize 再 exclude 掉嵌套的 blockui/domum 防重复类 `:109-112`）；联动 mod（Ecliptic Seasons 走 cursemaven `:119`，MineColonies Tweaks/Compatibility 走 `libs/` flatDir `:93-95,120-121`）全部 compileOnly——发布需手动改回（`:117-118` 有作者自注）。
- 工程结构: 单 Gradle 模块，无 api/sourceSet 分离（`settings.gradle` 仅 rootProject）；`api` 只是包名（见第 8 节）。插件: `net.minecraftforge.gradle` 6.0.x + Parchment 映射（`build.gradle:15,33`；`gradle.properties:23-24`）+ spongepowered mixingradle（`build.gradle:1-10,19,79-83`）。注解处理器只有 Mixin refmap processor（`build.gradle:122`），无自研 AP。
- Java 17（`build.gradle:28-30`）。含 `src/main/resources/META-INF/accesstransformer.cfg` 但为空文件（0 行），实际全靠 Mixin。

## 2. 源码规模与包结构

实测（`find + wc -l`）：**220 个 .java，26,921 行**（速览卡片写 27,141，偏高 ~220 行，以本报告复核值为准）。

| 顶层包 | 文件数 | 职责 |
|---|---|---|
| `SRC/mixins` | 127 | 对 MineColonies/structurize/原版的覆写；注册于 mixins.json 主列表 110 项（其中 104 项 `minecolonies.*`、6 项 `minecraft.*`），`minecolonies/accessor` 9 个纯 accessor |
| `SRC/core` | 71 | 重写的 worker AI(11)、job(1)、网络(2 通道+12 消息)、配置、window、easycolony、data |
| `SRC/api` | 21 | Mixin 织入契约接口（Extra/网络消息基类），非对外 API |
| `SRC/ColonyPathingEdition.java` | 1 | 入口 |

`core` 71 个文件的内部配比（实测）：`ai` 19（worker 11 / actions 5 / minimal 2 / pathfinding 1）、`message` 12（+compatible 2）、`window` 6、`easycolony` 6、`colony` 4、`util` 4、`event` 3、`data` 3、`network` 2、`config` 2、`minecolonies` 2（建筑模块插桩）、`manager` 2、`job` 1、`update` 1，其余为 costants/initializer 等杂项。`mixins/minecolonies` 一级 11 个散件 + 按职业分包（job 11、farm 7、healer 6、building 6、pathfinding 13（含 heuristic 5、navigator 3）、herder 5…）。可见结构：**一半以上体量在"替换上游 AI 实现"，真正的算法增量集中在 pathfinding 一个子包。**

行实测三分布：`mixins` 13,271 行、`core` 13,233 行、其余（api+入口）约 2,400 行——"侵入补丁"与"平行重实现"各占一半，这个 1:1 比例本身就是此类宿主覆写工程的形态特征。

最大源文件（实测行数）：`core/ai/worker/NewEntityAIWorkFarmer.java` 1415；`mixins/minecolonies/pathfinding/AbstractPathJobMixin.java` 1087；`mixins/minecolonies/farm/EntityAIWorkFarmerMixin.java` 939；`core/ai/worker/NewEntityAIWorkNetherWorker.java` 925；`core/ai/worker/NewAbstractEntityRequestSmelter.java` 908；`core/ai/worker/NewEntityAIWorkDeliveryman.java` 893；`core/job/NewJobDeliveryman.java` 816；`core/ai/minimal/NewEntityAIEatTask.java` 676；`mixins/minecolonies/pathfinding/navigator/MinecoloniesAdvancedPathNavigateMixin.java` 648；`core/ai/worker/NewEntityAIWorkPlanter.java` 497；`core/config/PathingConfig.java` 487；`mixins/minecolonies/healer/EntityAIWorkHealerMixin.java` 465。

**资源缺失声明**：`src/main/resources` 只有 3 个文件（mods.toml、mixins.json、空 AT），无 lang、无窗口 XML、无蓝图 JSON，`src/generated/` 不存在——本检出的 resources 层不完整，勿据此判断其数据资产。窗口全部用 BlockUI 代码硬建（`core/window/WindowCropRotation.java:11-16`），datagen 实际为零（见第 5 节）。

## 3. 入口与注册

入口 `SRC/ColonyPathingEdition.java:22-56`，`@Mod` 构造器做两件事——注册 COMMON 配置、注册自有频道消息：

```java
ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON,
        PathingConfig.init(new ForgeConfigSpec.Builder()));      // :30-33
CPENetwork.register(SpecialSeedSyncMessage.class, SpecialSeedSyncMessage::new); // :35
```

- 无 DeferredRegister、无 ForgeRegistries 注册（本 mod 不加任何注册表对象）。对 MineColonies 注册表的"接入"全靠事件与 Mixin：`RegisterEvent` 命中上游建筑注册表 key 时触发 `BuildingModules.init()`（空壳，`:45-50`）；`FMLCommonSetupEvent.enqueueWork(ModBuildingInitializer::init)` 把自建 ModuleProducer **插进上游 BuildingEntry 的模块生产者列表**（`:52-55`；`core/minecolonies/module/ModBuildingInitializer.java:9-50,52-63`——`entry.getModuleProducers().add(index, ele)`，反射级列表手术）。
- 事件订阅点：`ModConfigEvent` 触发配置快照与交互验证器重注册（`:39-43`；`core/initializer/InteractionInitializer.java:13-53`）；FORGE bus 上 `@Mod.EventBusSubscriber` 类有 `core/event/CitizenTrackingHandler.java:11-27`（StartTracking 补发实体传送包修 citizens 首次同步位置）、`core/event/FMLCommonSetupSubscriber.java:22-27`（联动 mod 探测）、`core/data/farmlandmap/SpecialSeedManager.java:26-51`、`core/update/UpdateManager.java:28-40`（客户端登录拉更新公告）。

## 4. 核心系统

### 4.1 A* 搜索层重写（"为什么单独开分支"的答案主体）

覆写 `com.minecolonies.core.entity.pathfinding.pathjobs.AbstractPathJob`（`SRC/mixins/minecolonies/pathfinding/AbstractPathJobMixin.java`，1087 行，8 个 `@Overwrite`）。**它改的不是原版 PathNavigation/NodeEvaluator，而是 MineColonies 自己的异步 A* 内核**（上游把寻路放线程池执行，fork 未动调度层）。与上游的可核对差异：

- **删上游随机扰动与启发缓存**：`computeCost` 注释"删除随机因子，因为会影响后续寻路"（`:162`）；`reevaluteHeuristic` 整个置 false（`:888-892`）；注释"上游 heuristic 有 bug，放弃它"（`:774`）。
- **双优先队列 + 每步展开最便宜 N 个节点**：`search()` 维护 `nodesToVisit`（f 序）与 `pathNodesToVisit`（道路/铁路节点的 h 序）两条队列，每轮取 1 个 f 最优再补 `NODE_EXTEND_COUNT-1`（默认 4）个"最便宜"节点（`:278-359`，取值 `:110-111`）——近似 beam 的多样扩展，缓解 A* 在道路低 cost 下漏走复杂地形的最优解。
- **动态节点上限**：`totalNodesVisited > Math.min(MAX_NODES, maxNodes + node.getHeuristic()*2)` 才判停（`:327`），离目标越远配额越大；到达后再用 `extraNodes` 在目标邻域按 h 序二次扩点找更好落点（`:362-411`）。
- **回扣节点（callback node）**：道路/铁路上的启发减免不允许"越减越优"造成回头路振荡——超出减免的部分改写为 `lastHeuristic + cost*回调乘子` 并打标记（`modifyHeuristic :950-982`），回扣节点最多被重扩展 `visitedLevel*CALLBACK_TIMES_TOLERANCE` 次（`updateNode :990`）。配套节点状态 `onFarmland/onSlab/isStation/isCallback` 通过 `@Implements` 把 `api/IMNodeExtras.java` 四个标志位织进上游 `MNode`（`MNodeMixin.java:14-60`），零内存布局开销（4 个 boolean）。
- **落点/地形判定细修**：半砖 0.5 格高度偏移（`:187-189`）、楼梯上下面判 cost（`:193,207-208`）、台阶处 corner 碰撞复检（`recheckGroundHeight :481-494`、`checkPossiblyPassing :502-532`——楼梯缝用 `rawDY>1.8` 粗判，作者自注待精细化的 TODO `:530`）、铁轨 shape 连通性判断（`checkConnection :534-560`）、掉落检测改探测铁轨为可停点（`checkDrop :586-590`）。
- **各 pathjob 启发式分派重写**：`PathJobMoveToLocationMixin.java:18-23`（h² 拉距：`(h*h+99h)/100`，越远增长越快）、`PathJobMoveTowardsMixin.java:24-35,63-69`（欧氏+罚因子）、`PathJobFindTreeMixin.java:16-23`（限制盒 Y 向 ±3）。
- **cost 常量的两处注入口**：`PathingOptionsMixin.java:28-43` 在 `PathingOptions` 构造器 RETURN 处把游泳/道路/铁路/跳跃/掉落等 10 个 cost 字段整体换成配置值（每个 job 新建 options 时生效，不改热循环）；`PathingOptions.java` 字段本身是 public 可再被 AI 逐 job 微调（如 Sentry 建造 `dropCost=1.5`，见 4.6）。
- **起点定位与危险块**：`PathfindingUtilsMixin.java:38-155` 重写 `prepareStart`（碰撞盒内可站判定、跨 BB 占地扫描 `:64-85`、围栏/模组建筑方块侧推 `:130-152`）——上游大量"市民起手卡进栅栏"类 bug 的修法；`isDangerous` 追加岩浆锅/岩浆块等（`:161-172`）。
- **演进史以 changelog 为准绳**：`changelog.md:2-15`（1.0：铁路 cost 定值化、探测铁轨=站点免下车 cost）、`changelog.md:16-27`（1.0.1：距离全部改 Y 权 1/5 曼哈顿、非紧急寻路改欧氏、入侵者改切比雪夫；corner 节点降级为纯存储）、`changelog.md:29-38`（1.0.2：绕行罚函数、卡住上限 4 次）。这份"上游哪里不对→怎么改"的对照清单比代码注释更系统，值得研究分支项目时优先读。
- **限流/成本**：寻路仍在 MineColonies 的异步线程跑，Block 读取走上游 `CachingBlockLookup`（`:67` shadow）；最大寻路距离由配置改写硬编码 900：`MinecoloniesAdvancedPathNavigateMixin.java:88-96` 用 `@ModifyConstant` 把 `900*900` 换成 `MAX_PATHING_DISTANCE²`（默认 1000，`PathingConfig.java:455-457`）。**路径缓存与失效本身未改**——跟随上游（结果对象状态机在 fork 的 tick 里消费：`MinecoloniesAdvancedPathNavigateMixin.java:332-343`，卡住后 `recalc()` 触发重算 `UnstuckMixin.java:81`）。

### 4.2 全殖民地路径覆盖层（蓝图 tag 数据驱动）

每个路径 job 构造时抓市政厅 BlockEntity 的 structurize `IBlueprintDataProviderBE.getPositionedTags()`（`AbstractPathJobMixin.java:1029-1054`），节点扩展时把世界坐标换算为相对市政厅坐标查三类 tag：`blocked` 直接不可入（`:740-742`）、`path`/`not_path` 参与"道路"判定（`:760`）。即玩家可用蓝图标记给全殖民地画"必走/禁走"走廊，不需要放道路方块。道路判定本身还叠加上游 `WorkerUtil.isPathBlock` 与梯子（"梯子及其上方可行走位置视为路径方块"，`:760`；`changelog.md:37`）。

代价：每节点扩展做 2~6 次 `Map<BlockPos,List<String>>` 查询且每次 `BlockPos.subtract` 分配新对象（`:1056-1084`），无任何区块级预过滤——见第 7 节的批评。

### 4.3 移动执行层（navigator + unstuck）

`MinecoloniesAdvancedPathNavigateMixin.java`（648 行）覆写 `followThePath`（`:166-278`，多前瞻点最近跳格，Y 权 0.5 的曼哈顿距离，`core/util/DistanceUtils.java` 108 行）、`tick()`（`:318-462`，替换原版 `super.tick()` 修 moveHelper 上不去空碰撞盒方块的陈年 bug，注释自述 "Because it's broken" `:404`）、梯子专用跟路（`handleLadders/doLadderMovement :464-602`，入梯对中、换梯限速）、矿道下车纠偏（`:98-159`，下车即传送到下一路径点、脱轨按速度补偿前跳）。`UnstuckMixin.java:53-171` 重写卡住处理：有路径先向前 5 节点小传送+重算（`:69-86`）；stuckLevel≤4 用"垂直于目标方向偏 20×level 格"的绕行罚函数重寻路（`:92-126`）；放梯/搭叶/破坏方块保留给袭击者（作者自评"非常蠢" `:128`）；≥5 级直接传送到终点，可被 `CANCEL_TELEPORT` 关掉（`:157-170`）。最底层的 `MovementHandler`（原版 MoveControl 子类）也被 `@Overwrite tick()`：stepHeight/speed 改为每 20 tick 缓存一次而非每 tick 查属性（`MovementHandlerMixin.java:41-46`），加 `jumpCoolDown` + `FORCE_JUMP_LIMIT=10` 强制起跳计数（`:27-28`）——这是全仓库唯一直接碰实体移动控制层的地方，NodeEvaluator/PathNavigation 本体未覆写。

### 4.4 worker / job / site 三元与岗位分派

三层关系照 MineColonies 骨架：`JobEntry(注册表) → produceJob → Job → createAI → WorkAI(状态机)`；site 是 `BuildingExtension`（农田 FarmField 等）挂在建筑的 `BuildingExtensionsModule` 上。fork 的介入点：

- **整体换 AI/换 Job**：`JobFarmerMixin.java:19-29` 覆写 `createAI()`，模块开关开时 `new NewEntityAIWorkFarmer(job)` 塞进 `citizenJobHandler.setWorkAI(...)`；快递员更狠——`JobEntryMixin.java:28-54` 直接 `@Overwrite` 注册表的 `produceJob`，按 `key.getPath()=="deliveryman"` 换整个 `NewJobDeliveryman`。
- **领取/释放沿用上游状态机**：农夫 `prepareForFarming` 里 `module.getExtensionToWorkOn()` 领一块田（`NewEntityAIWorkFarmer.java:219`），干完 `setFieldStage(EMPTY)` + `changeField` 换场（`:291-296`）；AI 构造器注册 AITarget 状态表（`:137-147`），`decide()` 把 IDLE 改道到新的 PREPARING 阶段（`:149-159`）。
- **物料经上游 request system 异步下单**：堆肥 StackList 请求（`NewEntityAIWorkFarmer.java:226-232`，需求数按田面积 `a*b-1` 现算 `:236-241`）、种子补货 `checkIfRequestForItemExistOrCreateAsync`（`:282`）——工人不自己找货，投递一律交给快递员体系。
- **快递员任务队列**：`NewJobDeliveryman.java:51` 实现 `JobWithEatingLimit/JobWithAdditionalHireCheck/JobWithWaitingQueue` 三个本 fork 契约接口；任务令牌队列存在殖民地 RequestSystem 的 DataStore 里（`:83-94` 持 `rsDataStoreToken`，`:116-125` NBT 序列化，`:597-614` `onTaskDeletion/getTaskQueue`）——队列跟着存档走而不是跟实体走。执行侧 `NewEntityAIWorkDeliveryman.java:61-120` 维护 `PRIORITY_FORCING_DUMP=10`（高优请求完成即强制返仓清包，`:69-71`）、`wareHouseIndex`（本轮投递目标仓库游标 `:102`）、`waitingTimer`（低等级快递员在途等待节流 `:112`）。`DeliverymenRequestResolverMixin.java:33-55` 在上游取消请求时找回持有该 token 的 citizen（新旧两种 Job 都认）。
- **跨建筑再雇佣**：`CourierAssignmentModuleMixin.java:29-54` 覆写仓库Courier模块的 `onColonyTick`：未满员时遍历全体市民找实现了 `JobWithAdditionalHireCheck` 的快递员挂进本仓库；`:56-62` 把上限从平级改为 `ceil(level*(level+1)*mult)`（对应配置注释"仓库 x 级雇 x(x+1) 人"，`PathingConfig.java:397-402`）。
- **跨区块 site 的唤醒/休眠**：fork 未做改动（全仓库无相关 Mixin，`CitizenManagerMixin.java:29-50` 只是重写"全员入睡"判定的消息触发）。**殖民地侧逻辑**（site 是存档内 Colony 数据、区块未加载时由 Colony tick 代持）完整继承上游——本报告只描述现状，不代上游取证。

### 4.5 数据驱动内容与同步

- 专属耕地映射：`core/data/farmlandmap/FarmlandMapLoader.java:18-67` 是 `SimpleJsonResourceReloadListener`，读 datapack 的 `farmland_map/*.json`（seed→farmland），`apply` 里 clear+重建并推给 `SpecialSeedManager.rebuildFromMappings`；服务端在玩家登录与 `/reload` 后用自有包把整表推给客户端（`SpecialSeedManager.java:29-51`；包实现 `core/network/message/SpecialSeedSyncMessage.java:13-50`）。
- 农夫侧消费点：专属耕地缺失时按 `isMissingFarmland` 状态位下单补方块（`NewEntityAIWorkFarmer.java:247-267`）——数据表→请求系统→工人搬运的闭环。
- 作物轮作日历：`RegisteredStructureManagerMixin.java:20-45` 挂进上游 `onColonyTick`，**只在日历天变化时**（`trueDate` 脏标记）遍历 farmField 扩展 `advanceDay()`，并把 `trueDate` 写进殖民地 NBT（read/write TAIL 注入）；`FarmFieldExtra` 由 farm 包 mixin 织入。
- 跨 mod 联动（Ecliptic Seasons 节气）在 `core/window/WindowCropRotation.java:28-29` 直接 import 其 API，compileOnly 软依赖 + `core/manager/LinkageManager` 运行期探测（`core/event/FMLCommonSetupSubscriber.java:22-27`）。

### 4.6 市民生活系统（进食/休闲/医疗/建造模式）

- 进食：`NewEntityAIEatTask.java`（676 行）+ `CitizenFoodHandlerMixin`，需求阈值改为"住宅等级 × 配置系数"，经 `InteractionValidatorRegistry.registerStandardPredicate` 注册成上游交互惩罚（`InteractionInitializer.java:14-53`），禁食清单是配置列表→启动期解析成 `Set<ItemStorage>` 快照（`PathingConfig.java:465-487`——注意 onLoad 只 add 不 clear，重载会残留）。
- 休闲：`CitizenDataMixinForLeisure.java:53-90` 覆写 `CitizenData.update` 的自务段，把工作空闲折算成 leisureTime 蓄水池 + `coolDownTime` 冷却，替代上游每 tick 概率判定。
- 建造：`EntityAIStructureBuilderMixin.java:60-120` 给建筑工/矿工/采石工五种作业模式（NORMAL/FORMALIST 边走边干/SENTRY 定点/GOD 无视距离/GIBBON 大半径，配置枚举 `PathingConfig.java:357-383`），SENTRY 用 `PathJobMoveCloseToXNearY` 预寻位 + `repathCounter≥3` 止损（`:78-118`）。material 消耗与工单 UI 未改，沿用上游 work order；建造侧唯一的防御性补丁是 `BuildingBuilderMixin.java:19-24`（citizen 为 null 时跳过请求取消，修一个上游 NPE 路径）。蓝图识别/工单/材料清单本身（上游+structurize）fork 全未触碰，只改"工人怎么在工地上站位与移动"。
- changelog 末尾 TODO 自曝进度（`changelog.md:578-580`）：脆弱 AI 重构完成 8 个、技能/幸福度系统"暂时搁置"、任务系统（运送顺序）已优化——与本报告 worker 清单互相印证。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **双网络层**：(a) 自有 `SimpleChannel`（`core/network/CPENetwork.java:14-42`，自增 id + `<T extends ICPEMessage<T>>` 泛型注册；`api/network/ICPEMessage.java:12-40` 接口自带 encode/handle 和 `syncToAll/syncToPlayer/syncToTracking/syncToServer` 四个 default 分发器）——只走了 1 条包（SpecialSeedSync）。(b) 主通道是 **Mixin 挤进 MineColonies 自己的 NetworkChannel**：`NetworkChannelMixin.java:21-36` 在 `registerCommonMessages` TAIL 用 `++idx` 连注册 12 条 `IMessage`。`idx` 来自 locals capture——上游消息数一变就全线错位，这是分支最脆的接缝之一。殖民地服侧包形状见 `FarmFieldResizeMessage.java:18-91`（`AbstractColonyServerMessage`，`toBytesOverride/fromBytesOverride` 手写序列化，`onExecute` 拿到已解析的 IColony）。
- **实体数据同步**：无任何 capability/Attachment 注册（全仓库 grep `AttachCapabilities|RegisterCapabilities` 零命中）——市民/建筑/MNode 上的扩展数据全部走 Mixin 字段织入 + 上游 Colony NBT + 上游 building sync 消息，自定义持久化只在 `RegisteredStructureManagerMixin.java:34-45` 这类 read/write 注入点。**对 1.20.1 读者：这是"零 capability"路线的形状参考，不是推荐照抄。**
- **配置**：单 COMMON `ForgeConfigSpec`（`core/config/PathingConfig.java:119-463`），约 90 项、七大分区，全部中英双语 comment；寻路常数（回扣乘子/展开数/信赖度）和每条 cost 都开放（`:223-311`，分区自注"警告：慎重修改"）。`ModConfigEvent` 重载时 `onLoad()` 重解析黑名单（`:467-487`）。
- **更新公告**：客户端登录时异步 HTTP 拉取 changelog JSON，GitHub Pages 与 gitee raw 双镜像轮询、5s 超时（`core/update/UpdateManager.java:29-31,43-51,64-72`；mods.toml 的 `updateJSONURL` 在 `src/main/resources/META-INF/mods.toml:24`）——国内分发 mod 的典型兜底形状。
- **datagen**：没有。无 `src/generated`、无 `GatherDataEvent` 处理、无 provider；配方/蓝图/窗口 XML/lang 均不产生也不存在于检出。

## 6. Mixin / ASM / 注解处理器

- Mixin 是唯一改写手段：127 文件、`compatibilityLevel JAVA_17`、`priority: 999`（压在所有常规 mod 之后，`colonypathingedition.mixins.json`）；注册计数：主 mixins 列表 110 项、client 列表 15 项、server 列表 1 项。原版只有 6 个轻量注入（`BeaconBlockEntityMixin.java:23-49` 让信标惠及市民——在原版 `applyEffects` 里再查一次 AABB 实体表；`DoorBlockMixin/FenceGateBlockMixin/FurnaceBlockEntityMixin/AbstractMinecartMixin/DamageSourcesAccessor`）。
- 值得记录的三种手法：`@Implements + prefix` 织接口（`MNodeMixin.java:15`）；`@Overwrite(remap=false)` 整法替换 + 配置常量快照进 `@Unique` 字段避免热路径反复读配置（`AbstractPathJobMixin.java:110-124`）；`@ModifyConstant` 干掉魔法数（navigator `:88-96`）。accessor 子包 9 个纯 `@Invoker/@Shadow` 接口供别的类调用私有成员。
- **没有** MineColonies 自家的注解驱动注册（`@ColonyEventHandler/@EventAnnotation` 全仓库零命中——它直接走 Forge bus 注解），也没有自研注解处理器；AP 只有 mixin refmap 生成（`build.gradle:122`），代价是编译期产物 `refmap.json` + 运行期对上游方法签名的完全绑定（版本区间钉死 `[1197,1259]` 即其自供状）。
- 死代码：`core/ai/pathfinding/SpecialInfoNode.java`（149 行）无任何引用（grep 全库仅自引用），应为早期路径点方案残留。
- 生态耦合面：`mixins/minecolonies/compatible` 4 个类对接第三方生态 mod（Tweaks/Compatibility，见 §1 依赖），view 三件套分别注册进主/client/server 列表——"分支的分支"，也是它把上游区间钉到 ±60 号快照的原因之一。

## 7. 值得学的 5 条

1. **回扣节点：启发减免必须带"回头税"** — `SRC/mixins/minecolonies/pathfinding/AbstractPathJobMixin.java:950-990`。给偏好通道（道路/铁轨/传送带）降启发值必然产生振荡；它把"减免后再变优"的节点改写为可有限重扩展（tolerance 次数）的 callback 节点而非直接接受。任何有"首选走廊"的分层寻路都会撞上这个问题，这套限次复检是可直接照搬的算法骨架。
2. **蓝图 tag 覆盖层做领地寻路走廊** — `AbstractPathJobMixin.java:1029-1084`。借市政厅结构扫描的 position→tag 字典当全殖民地空间索引，玩家"画"禁行/必行区零新方块。**抄思路要修性能**：原版每节点 `BlockPos.subtract` 分配 + 最多 6 次 map 查询（`:740,760`），应改为区块粒度的 tag 位图预过滤后再查细表。
3. **配置门控整类换 AI/Job，而非逐方法补丁** — `mixins/minecolonies/job/JobFarmerMixin.java:19-29` + `JobEntryMixin.java:28-44`。开新行为=构造新实现塞进 handler，关开关即回到上游原类，回归可二分、diff 不污染旧路径。对"重做 NPC 行为层"的工程，这是比到处 `@Redirect` 干净得多的扩展形态。
4. **日历天脏标记 + 单次遍历的殖民地块推进** — `mixins/minecolonies/workersetting/RegisteredStructureManagerMixin.java:20-45`。tick 里只比较 `dayTime/TICKS_PER_DAY != trueDate`，变了才 stream 遍历 farm 扩展并 `advanceDay`，且 trueDate 随殖民地 NBT 持久化防重放。所有"每天结算"类逻辑的范本（新星殖民地的日结算去重可直接对照）。
5. **消息接口自带分发器 + 借宿主频道** — `api/network/ICPEMessage.java:12-40`（default `syncToAll/Player/Tracking/Server` 包掉 PacketDistributor）与 `NetworkChannelMixin.java:21-36`（寄生注册省一条频道握手）。前者是纯 1.20.1 Forge 惯用法可直接抄；后者只在"深度依附某宿主 mod"时可用，并要像它一样把 id 冲突当作版本钉死的理由。

反面取证（第④问的"做坏了"清单）：

- `AbstractPathJobMixin.java:629-630`：每节点扩展 `new ArrayList<>(Direction.values()) + new Random()` 洗牌——热路径双分配，方向顺序本可查表轮转。
- 同文件 `:295-307,998-1024`：对第二条队列用 `PriorityQueue.remove(Object)`（O(n) 线性扫）做增删，量大时比 A* 本体还贵。
- `BeaconBlockEntityMixin.java:31-36`：每信标每 tick 在原版 `getEntitiesOfClass` 之外**再查一遍**同 AABB 的实体表，本可在注入点复用那次查询只放宽类型。
- `PathingConfig.java:465-487`：食物黑名单 `onLoad()` 只 add 不清空，配置重载后旧条目残留。
- `EntityAIWorkFarmerMixin`（939 行）与 `NewEntityAIWorkFarmer`（1415 行）是同一农夫的两套并行实现（开关内/外），无测试兜底，行为漂移只能人肉同步；healer 包 465 行的 `EntityAIWorkHealerMixin` 是同类双轨。
- `core/ai/pathfinding/SpecialInfoNode.java`（149 行）全仓库零引用，死代码。

正面样板（限频/脏标记确实做了的地方）：navigator 地面增速判定 15~20 tick 随机节流并自注"不知道会不会更卡所以维持原样"（`MinecoloniesAdvancedPathNavigateMixin.java:373-385`）；`MovementHandler` 把 stepHeight/速度属性刷新降为 20 tick 周期（`MovementHandlerMixin.java:41-46`）；市民实体不在场时 HEAD 直接 cancel `CitizenData.update`（`CitizenDataMixinForLeisure.java:54-59`）；休闲改 cooldown 蓄水池（`:60-80`）；日历天脏标记扫描（`RegisteredStructureManagerMixin.java:25-27`）。

## 8. 公开 API

本 mod 对外**没有**可依赖的 API 模块（无独立 sourceSet、mods.toml 无 dependencies 暴露、`api` 包是其 Mixin 织入契约的内脏）。对"殖民 mod 的 worker/job 扩展点"这一问题，本仓库的价值在于反推出 MineColonies 1.20.1 的扩展形态并示范如何从外部撬动它：

- **job 侧**：`JobEntry.produceJob`（被 `JobEntryMixin.java:28-44` 撬开）——注册表条目持有 `Function<ICitizenData,IJob<?>>`；job 的 `createAI()` 决定挂哪个 WorkAI；job 可 NBT 持久化自己的令牌/队列（`NewJobDeliveryman.java:116-140`）。
- **site 侧**：建筑模块体系 `BuildingEntry.ModuleProducer`——可后处理插入（`ModBuildingInitializer.java:52-63`）、可覆写 `IAssignsJob` 模块的 `onColonyTick` 做自动雇佣（`CourierAssignmentModuleMixin.java:29-62`）；site 实体是 BuildingExtension，由 `BuildingExtensionsModule.getExtensionToWorkOn()` 派发给工人。
- **请求侧**：RequestSystem resolver（`DeliverymenRequestResolverMixin.java`）+ `InteractionValidatorRegistry`（`InteractionInitializer.java`）。
- 接入方式即：依赖 MineColonies → 写 Mixin/accessor + `enqueueWork` 期列表插入；或正经点走其 `IMinecoloniesAPI` 注册表（本 fork 只在 `ColonyPathingEdition.java:45-50` 窥了一眼 key）。
- `SRC/api` 21 个接口的三种角色（全部是"织入契约"，不是对外 API）：
  - *Extra 状态契约*（16 个）：`IMNodeExtras`、`FarmFieldExtra`、`AbstractEntityAIBasicExtra`、`BedHandlingModuleExtra`、`SkillDataExtra`、`PatientExtras`、`api/workersetting/Building*Extra` ×4 等——mixin 给上游类挂字段/方法后，其余代码统一按接口访问，避免到处 cast + 反射式 accessor；
  - *行为标记契约*（3 个 + 1 个 accessor）：`JobWithWaitingQueue`、`JobWithAdditionalHireCheck`、`JobWithEatingLimit`——跨新旧 Job 实现的鸭子类型（`CourierAssignmentModuleMixin.java:39` 用 `instanceof` 接口分派；`DeliverymenRequestResolverMixin.java:44-53` 因新旧 Job 无共同接口只能类别双写——这正是没把接口铺到底的代价）；
  - *网络契约*（1 个）：`ICPEMessage`。

**结论（给两个读者的可搬做法）**：
- 蜂群(hivecolony)：① 把 4.1 的"双队列+回扣节点"搬进它的分层行为调度——NPC 沿既定层级通道移动时给通道启发折扣，但折扣产生的"回头更优"节点一律打 callback 标记限次复检（`AbstractPathJobMixin.java:950-990` 的判据可原样翻译）；② 岗位分派学它的契约接口形态（`JobWithAdditionalHireCheck/JobWithWaitingQueue`）：工人实现标记接口，建筑模块 tick 时按接口匹配招募，任务队列存在"领地存档"而非实体上（`NewJobDeliveryman.java:83-94`），断线/换区块不丢单。
- 新星殖民地(newstar)：③ `RegisteredStructureManagerMixin.java:20-45` 的日历天脏标记推进 + NBT 持久化 trueDate，适合它的殖民地块统一由 colony tick 驱动（农田轮作/产出周期），而不逐区块挂 tileentity。
- **许可边界**：以上只能拿走"判定结构与数据流向"；本 fork 的方法体大量 `@Overwrite`、派生自上游 MineColonies 代码（其 LICENSE 文件不在本检出，协议名以"带网络条款 copyleft 系"待验证为准），自身又声明 GPL-3.0——任何一行（含 cost 常数表的 comment 文本）复制进非兼容许可工程都构成衍生；重写时请从行为规格出发重新实现。
- 本报告未取证项：`core/ai/actions/netherworker`（5 文件）与 `NewAbstractEntityRequestSmelter` 的冶炼分工细节、`mixins/minecolonies/event/ClientEventHandlerMixin` 具体注入点——均只点名未逐行读，引用时请以文件路径自行复核。
