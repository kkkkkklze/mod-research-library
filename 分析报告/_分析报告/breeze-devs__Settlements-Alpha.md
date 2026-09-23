# Settlements (Alpha) 源码分析报告

> 仓库：`源码库/_参考仓库/_bulk/breeze-devs__Settlements-Alpha`。1448 个 .java 的中大型工程，本报告按取舍细读了三块：定居点边界与世界索引（`domain/settlement`、`infrastructure/minecraft/query`、`application/ai/sensors`）、日程与计划执行（`application/ai/planning`、`infrastructure/minecraft/behavior/planning`、`di/modules/server`）、跨端 UI 同步（`application/ui`、`infrastructure/network`）；`domain/animation`、`infrastructure/rendering`、`presentation/ui/stats` 与 `application/ai/inference`（LLM 推理）按包略读，理由见第 2 节末。

## 1. 基本信息

- mod_id `settlements`、显示名 Settlements、作者 "Breeze et al."、许可证 `GPL-3.0-only`、mod 版本 `1.0.0-beta.2`（以上均在 `gradle.properties:31,35,37,41,43`）。
- 目标平台：MC `1.21.1`（`gradle.properties:15`），加载器 NeoForge `21.1.73`（`gradle.properties:21`），版本区间 `[1.21.1,1.21.2)` / `[21.1.0,)`、FML loader `[4,)`（`gradle.properties:18,23,26`）。无 Fabric/Forge 分支，单加载器。
- Gradle 插件：`net.neoforged.moddev` 1.0.21 + `java-library` + `maven-publish`（`build.gradle:3-7`），Parchment 映射 1.21/2024.07.28（`gradle.properties:9-10`）。工程结构 single（`settings.gradle` 只含 pluginManagement 与 foojay resolver，无子项目），但有一个 `buildSrc` 模块放 `dev.breezes.gradle.EnsureJarManifest`（`buildSrc/src/main/java/dev/breezes/gradle/EnsureJarManifest.java`），用来给缺 MANIFEST.MF 的 jarJar 产物做 Gradle artifact transform 修补（`build.gradle:9-34`）——这是 ModDevGradle 1.0.21 的坑位绕行，值得记住。
- Java 版本：toolchain 21（`build.gradle:57`）。
- 编译依赖：Lombok 1.18.34（compileOnly + annotationProcessor）、Dagger 2.60.1 + `jakarta.inject` + `javax.inject` 以 `jarJar` 内嵌发布（`build.gradle:169-206`，注释明确说明两个 inject 包是运行时链接必需，缺一个就是 NoClassDefFoundError）；测试 JUnit 5 + Mockito（`build.gradle:211-215`）。
- Maven 发布坐标 `dev.breezes.settlements:settlements:1.0.0-beta.2`，发布到本地 `file://$projectDir/repo`（`build.gradle:45-46,249-260`）。元数据由 `src/main/templates/META-INF/neoforge.mods.toml` 经 ProcessResources 展开生成（`build.gradle:223-246`）。

## 2. 源码规模与包结构

实测（`find src -name '*.java' -print0 | xargs -0 cat | wc -l`）：全仓 1448 个 .java（其中 `src/main` 1235 个、`src/test` 212 个、`buildSrc` 1 个），总行数 123,723；`src/main` 单独 94,613 行。卡片给的 125,260 行与实测差约 1.5k 行，量级正确但数字要自己复核。

`src/main` 按二级包的文件数（降序）：

| 包 | 文件数 | 包 | 文件数 |
|---|---|---|---|
| `application/ai` | 323 | `presentation/ui` | 38 |
| `infrastructure/minecraft` | 156 | `bootstrap/event` | 36 |
| `domain/ai` | 102 | `di/modules` | 34 |
| `domain/generation` | 78 | `application/ui` | 32 |
| `domain/animation` | 66 | `infrastructure/config` | 28 |
| `infrastructure/rendering` | 52 | `shared/util` | 25 |
| `infrastructure/network` | 50 | `bootstrap/registry` | 16 |
| 其余（economy/world/personality/…） | 约 130 | `infrastructure/datagen` | 3 |

最大的源文件（`src/main`）：`di/modules/server/BehaviorCatalogModule.java` 1478、`infrastructure/minecraft/entities/villager/BaseVillager.java` 1278、`application/ai/planning/PlanRunner.java` 952、`presentation/ui/stats/VillagerStatsScreen.java` 926、`domain/animation/FishingAnimations.java` 721、`application/ai/planning/DayPlanComposer.java` 607、`presentation/ui/framework/Elements.java` 571、`application/ai/behavior/usecases/villager/fishing/FishingBehavior.java` 492、`.../trading/TradeInitiateBehavior.java` 490、`di/modules/server/SocialCueCatalogModule.java` 481、`.../leatherworking/dyeleather/DyeLeatherBehavior.java` 464、`domain/world/location/Location.java` 397。测试侧另有 5 个 530+ 行的规划器/感知单测（`src/test/.../planning/HeuristicPlanGeneratorTest.java` 等）。

源码树不完整（重要）：`src/main/resources` 只有 `settlements.mixins.json`，`src/main/templates` 只有 `neoforge.mods.toml`——`src/` 树里非 .java 文件总共只有 2 个；`src/generated/resources` 目录不存在。也就是说所有 datapack JSON（建筑定义 `settlements/buildings/definitions/…`，见 `infrastructure/minecraft/data/building/BuildingDefinitionDataManager.java:22`）、NBT 建筑模板、lang、贴图、动画资源都不在本地树里。本报告关于"有哪些 JSON/模板文件"的描述全部来自代码里的目录常量与 Codec，不来自实测文件清单；涉及资源内容的判断标为未验证。取舍说明：动画/渲染/UI 皮肤层与 `application/ai/inference`（LLM 覆写计划，依赖外部推理服务）对本次两位读者的蜂群/新星目标帮助低，只确认其接入形状，不逐文件读。

## 3. 入口与注册

入口 `src/main/java/dev/breezes/settlements/SettlementsMod.java:25-59`：`@Mod` 构造函数只做两件事——把 14 个 `DeferredRegister` 包装类挂到 mod 总线，然后跑注解式配置与网络注册。

```java
ItemRegistry.register(modEventBus);
BlockRegistry.register(modEventBus);
...
StructureRegistry.register(modEventBus);
ActivityRegistry.register(modEventBus);
ScheduleRegistry.register(modEventBus);
processAnnotations(modEventBus);
...
ConfigAnnotationProcessor.process();                       // 扫注解生成 ModConfigSpec
modEventBus.addListener(PacketRegistry::bindPacketHandlers);
```

注册方式要点：`bootstrap/registry/` 下 14 个注册子包（16 个文件）各持有一个 `DeferredRegister`（例 `bootstrap/registry/attachments/AttachmentRegistry.java:34-35`、`bootstrap/registry/structures/StructureRegistry.java:16-29`）。事件总线订阅点分三层：
- MOD 总线：`@EventBusSubscriber(bus = Bus.MOD)` 的 `bootstrap/event/CommonModEvents.java:30-51`（属性、生成规则）与 `:53-73` 的 `FMLLoadCompleteEvent`——load-complete 时才 `DaggerSettlementsComponent.create()` 建根图，并把 `Set<PreparableReloadListener>` 的多绑定注入 `AddReloadListenerEvent`（`CommonModEvents.java:75-86`）。
- GAME 总线（每服务端会话）：`bootstrap/event/ServerLifecycleEvents.java:23-54` 在 `ServerAboutToStartEvent` 建 server 子组件并逐个 `NeoForge.EVENT_BUS.register(serverComponent.xxx())`，`ServerStoppedEvent` 里对称 unregister（`:57-90`）。因为事件类都是 `@ServerScope`，Dagger 返回同一实例，注册/注销成对可核对。
- 客户端：`bootstrap/event/ClientModEvents.java`、`*ClientEvents.java` 若干。
- `bootstrap/event/CommonModEvents.java:35` 有一个静态 `LOAD_COMPLETE_TASKS: List<Runnable>`（自带 `// TODO: refactor this!!! ugly`），是配置工厂的启动补丁通道——反面样本，别学。

## 4. 核心系统

### 4.1 定居点边界：结构（Structure）当身份，SavedData 当属性表

定居点不是方块实体也不是自定义 chunk，而是一个注册过的世界结构：`bootstrap/registry/structures/StructureRegistry.java:22-23` 注册 `StructureType<SettlementStructure>`，piece 类型两个（`settlement_building_piece`、`settlement_road_piece`）。生成时在 `infrastructure/minecraft/worldgen/structures/SettlementStructure.java:52-103` 里跑完整布局管线，把每个建筑落成一个 `SettlementBuildingPiece`（带 `settlementId` + `buildingDefinitionId`，`SettlementBuildingPiece.java:18-19,48-53` 把它写进 piece 的 NBT）。

关键设计：`SettlementStructure.java:132-136` 的 `settlementIdFor(ChunkPos)` 把起始 chunk 的 (x,z) 打包成一个 long 再转无符号十进制串——定居点 ID 是纯坐标派生的确定性值，重放同一个 chunk 必然得到同一个 ID（幂等锚点）。

查询侧 `infrastructure/minecraft/query/StructureManagerSettlementQueryService.java:36-54`：`locate` 用 `level.structureManager().getStructureAt(pos, structure)`（`SettlementStructureLocator.java:23-37`）拿到 `StructureStart`，再 `extractSettlementId(pieces)` 取任一 piece 上的 id（`SettlementPieceIdentityResolver.java:20-29`），然后拿 `SettlementSavedData` 里的元数据并用 `metadata.containsPosition(x,z)` 二次校验（`SettlementMetadata.java:23`）。同一 Start 里多个 piece 重叠时按最小包围盒体积选最具体建筑（`StructureManagerSettlementQueryService.java:87-94,130-133`）。

区块卸载如何存活：边界信息天然存在 `StructureManager` 的 starts（随 level 存档，不随 chunk 卸载丢失），建筑身份存在 piece NBT；属性（名字/特质/规模/中心/包围盒/人口/财富）存在 `infrastructure/minecraft/persistence/SettlementSavedData.java:17-119`（`getDataStorage().computeIfAbsent`，key `settlements_settlement_metadata`，`:44-53`）。NPC 侧状态全部走 NeoForge attachment（`AttachmentRegistry.java`：hunger `:37`、emeralds、inventory、brain、genetics、`VILLAGER_PERSONALITY :110`、`CHEST_WAXED :153`），因此实体 chunk 卸载/重载后由实体 NBT + attachment 复原，不需要外部索引。

写入路径的线程边界值得抄：worldgen 在 worker 线程上产出元数据，只能投队列 `application/settlement/persistence/SettlementMetadataQueueService.java:20-36`（`ConcurrentLinkedQueue`），由主线程 `bootstrap/event/SettlementMetadataPersistenceServerEvents.java:23-37` 在 `ServerTickEvent.Post` drain 进 SavedData，注释直说 "Worldgen runs off-thread, so persistence must cross the thread boundary here"。落盘脏标记靠值比较：`SettlementSavedData.java:84-89` 只有 `!metadata.equals(previous)` 才 `setDirty()`。

### 4.2 行为分层：原版 Brain 当宿主，自研 DayPlan 当调度器

分层不止一层，而且不是"自研 Goal 替换原版"：

1. 原版 Brain/Activity 保留：`BaseVillager.java:942-986` 的 `registerBrainGoals` 用 `VanillaBehaviorPackages.getCorePackage`（`application/ai/brain/VanillaBehaviorPackages.java:96-120`，含 `AcquirePoi` 找 JOB_SITE/HOME/MEETING、`AssignProfessionFromJobSite`、`SleepInBed`、`PoiCompetitorScan`）+ `VanillaAmbientBehaviorPackages` 的 WORK/MEET/IDLE/REST 环境包。也就是说床、钟、工作站 POI 的占用/竞争/ profession 授予仍是原版机制（`VanillaAmbientBehaviorPackages.java:79,102` 继续校验 HOME/MEETING）。日程则被换掉：`brain.setSchedule(ScheduleRegistry.SETTLEMENTS_SCHEDULE.get())`（`BaseVillager.java:982`），而 `bootstrap/registry/schedules/ScheduleRegistry.java:19-23` 只有一个 12:00→IDLE 的切换点——原版日程被刻意掏空。
2. 桥接层是两个 CORE behavior：`BaseVillager.java:948-956` 只在成年村民上注入 `PlanRunnerBehavior`（优先级 20）与 `PlanContextSwitcher`（优先级 98）。`infrastructure/minecraft/behavior/planning/PlanRunnerBehavior.java:47-56` 覆写 `timedOut`/`canStillUse` 让它永不自超时，`:59-87` 每 tick 先做 panic 判定、再 `tickOverride`、再看当前非核心 Activity 是否属于 {WORK, MEET, IDLE}（`:29`），否则 `suspendIfActive + ensureValidPlan`。`PlanContextSwitcher.java:55-72` 以 1 秒冷却把 DayPlan 推导出的 Activity 写回 Brain，并用 `lastDerivedActivity` 记住上次结果，避免每 tick 让 Brain 重复断言同一 Activity（注释在 `:69`）；`:98-115` 让"当前 ACTIVE 槽位的类别"（WORK→Activity.WORK、SOCIAL→MEET）优先于日程块，保证工作/社交行为拿到匹配的原版上下文。
3. 计划层：`domain/ai/planning` 的 `DayPlan` = 有序 `PlanSlot` 列表 + `DayPlanSchedule`（wake/bedtime + activity 块）。生成一次一天，由 `application/ai/planning/DayPlanComposer.java:83-107` 的三段式流水线产出：`computeFrame`（wake/sleep/work 边界，无 RNG）→ `computeAnchors`（餐点表 + 钉住的 pin，`:267-334`）→ 逐 band `fillBand`（`:432-478`，把 band 减掉锚点后交给 `WindowPacker.pack` 做带冷却的贪心装箱）。band 派生见 `:169-223`：MORNING/AFTERNOON/EVENING 是有序无重叠划分，宽度小于 `WindowPacker.MINIMUM_SLOT_SPACING_TICKS`（10 游戏分钟，`application/ai/planning/WindowPacker.java:31`；band 过滤在 `DayPlanComposer.java:217-221`）的 band 直接丢掉。基因与人格进入计划：WIL 决定下班时间（`:572-580`），chronotype 决定起床/就寝/吃饭偏移（`:126-145`），休息日权重另算（`:175-179`）。
4. 执行层：`PlanRunner.java:246-333` 是个小型状态机——槽位 PENDING 时从 catalog 用工厂新建 behavior 实例（`:281-291`，注释说明"每次新建所以 cooldown 需要 forceComplete，节奏改由计划生成期保证"），前置条件不满足则 flexible 槽跳过、rigid 槽 0.5 秒后重试（`:271-313`，常量 `SLOT_START_RETRY_INTERVAL_TICKS` 在 `:80`）；ACTIVE 时累计 ticks，超过 `DEFAULT_MAX_BEHAVIOR_RUN_TICKS`（`:75`，120s）或 override 超 `MAX_OVERRIDE_DURATION_TICKS`（`:67`，同为 120s）就强制停机并把槽位重新排队（`:53-65` 注释）。具体 behavior 是 `application/ai/behavior` 下的 staged workflow（`workflow/steps/` 有 Sequenced/Conditional/TimeBased step，`usecases/villager/**` 每职业一个 behavior），例：`usecases/villager/farming/CultivatePlotBehavior.java:78-120` 用 `Stage{PICK_CELL, APPROACH_CELL, CULTIVATE, LOOP, AWARD, END}` + `BlockMemoryTargetResolver` 从记忆里取候选地块。
5. 目录与职业池：`di/modules/server/BehaviorCatalogModule.java` 1478 行，每个行为一个 `@Provides @IntoSet BehaviorCatalogEntry`，descriptor 里写 category/intensity/requiredChannel/estimatedDuration/maxRunDuration/cooldown/interruptible（样本 `:159-183` 的 manage_chests）。头注释（`:150-153`）就是"加一个行为要改哪两处"的操作说明。职业→行为权重池在 `di/modules/server/PoolModule.java:29-87`。这就是这个 mod 的"Goal 表"，只不过它是 Dagger multibinding + 元数据，而不是 JSON。
6. 与工作站的对接方式： mod 自己的生产行为不走 POI，走"感知记忆"——`domain/ai/memory/MemoryTypeRegistry.java:58-94` 声明十几个 `DecayingSpatialMemoryType`（RIPE_CROP_SITES、ORE_SITES、ANVIL_SITES、FULL_HIVE_SITES…），由 `application/ai/sensors/BlockResourceSensor` 定期灌入（`BlockResource.java:28-60` 把查询结果写成 presence + "确认缺失区域"），执行时再用 `domain/world/blocks/BlockMemorySiteConfirmer` 逐点复核活方块（`CultivatePlotBehavior.java:108-119` 把 `confirmBox`/`maxConfirms` 装进前置条件，`DEFAULT_MAX_CONFIRMS` 取自 `:109`）。POI 只用于 HOME/MEETING 与 `ReleaseHomePoiObligation.java:30` 的床释放。
7. 响应式旁路：`PlanRunner.tickOverride`（`:110-120`）+ `Set<OverridePolicy>`（`di/modules/server/OverridePolicyModule.java:24-29` 用 `@Binds @IntoSet`，优先级比较器在 `PlanRunner.java:82-84`）在计划槽之外跑一个单槽 override（`PlanRuntimeState.java:26-46`，注释说明这里将来可以变成小优先级栈），用来抢"着火了/有需求物品在地上/被攻击"这类即时反应。

### 4.3 世界资源索引：一次 section 扫描服务全体村民

`application/ai/sensors/WorldResourceIndex.java` 是 server 级共享缓存：`Long2ObjectOpenHashMap<SectionPos packed long → SectionResourceScan>`（`:191`）+ FIFO 去重脏队列 `LongLinkedOpenHashSet`（`:195`）。`queryAll(:38-87)` 只做一件事：把查询框涉及的 section 枚举一次（`sectionsIntersecting :147-170`），对每个 section 判新鲜度（`nowTick - scannedAtTick < ttl`，`:61`），过期就 enqueue 并整次标记 incomplete，然后把该 section 的各资源命中数组扇进 per-resource 桶，最后统一做 box 过滤 + 最近 K 截断（`NearestKSelector`）。缺失/过期不返回错误，只是"结果不完整 + 排一次异步补扫"——自愈缓存。

补扫在 `ResourceIndexRefresher.java`：`refresh(level)`（`:72-88`）每 level-tick 主线程跑，先 drain worker 回来的 arrivals（`:116-145`，newest-wins、chunk 已卸载就丢），再 drain 至多 `scan_budget_sections_per_tick` 个脏 section；每个 section 有两级快速路径（空 section 直接写空扫描 `:175-178`；palette `maybeHas` 预过滤，全部资源都不可能出现就写空 `:183-187`），需要真扫时才在主线程取 `PalettedContainer.copy()` 快照（目标 section + 6 面邻居，`:292-345`）并把 16³ 的逐块匹配丢到 `@WorldScanExecutor` 线程池（`:201-216`），worker 完全不碰活世界（`matchSnapshot :224-281`）。线程池是有名 daemon + 未捕获异常日志的固定池（`di/modules/server/ConcurrencyModule.java:61-73`），server stop 时统一 shutdown（`ServerLifecycleEvents.java:64-72`）。
清理：chunk 卸载同时清 index 与 in-flight（`ResourceIndexRefresherServerEvents.java:31-39` → `WorldResourceIndex.evictChunk :125-134`、`ResourceIndexRefresher.evictChunk :94-106`），level 卸载清整表（`:41-47`）。

### 4.4 行为副作用账本（teardown ledger）

`application/ai/behavior/teardown/` 下 12 个文件构成"占用→必须归还"的显式账本：`TeardownObligation`（`stillValid`/`discharge`/`describe`）+ 具体义务 `RestoreBlockObligation`、`ResetBlockStateObligation`、`DiscardEntityObligation`、`DropLeashObligation`、`ReleaseHomePoiObligation`，作用域 `TeardownScope`。账本随实体持久化（`AttachmentRegistry.java:73-78` VILLAGER_TEARDOWN_LEDGER + `attachments/TeardownLedgerAttachmentState.java:13-21`），崩溃/存档遗留条目由 `BaseVillager.java:748-799` 每 5 秒（`RECONCILER_COOLDOWN_TICKS :142`）reconcile：目标 chunk 未加载就"顺延但不计失败次数"（`:765-768`），有活跃 behavior 重新持有就跳过（`:770-773`），最多 10 次失败后放弃并 error log（`:791-796`）。停止链路是有序的：`BaseVillager.remove(:813-838)` 先 `brain.stopAll` 再走 `PlanRunner.forceStop → behavior.stop → teardownAll`，注释（`:816-819`）把这条链写死在代码里。

### 4.5 社交/事件总线与语音气泡

`domain/ai/worldevent/WorldEventBus.java` 是一个 append-only `List<WorldEvent>` + 单调 seq（`currentSeq :127`、TTL 驱逐 `evict :139-155`），每村民持一个瞬时游标（`SocialCueRuntimeState`），因此"事件对谁广播"由游标差决定而不是广播写。驱逐 1 Hz（`bootstrap/event/WorldEventBusReaperServerEvents.java:23-28`，`tickCount % 20`）。感知管线整体 1 秒一次（`BaseVillager.java:146,729-738`），注释解释"总线是追赶游标，所以批量消费只放大 delta 不丢事件"。气泡 `application/ui/bubble/VillagerBubbleService` 走独立 payload 快照（见第 5 节）。

### 4.6 经济：需求信号与版本计数

`application/economy/demand/DemandSignalService.java` 维护 per-villager 的 `DemandSignalState`（attachment `demand_signals`，`AttachmentRegistry.java:49-53`），并对外暴露 `getVersion(villager)` 整型版本号；`domain/economy/catalog/` 15 个文件是交易目录（ItemMatch/OfferFacet/StockPolicy/RestockFacet 全部有 Codec）。玩家交易的每日补货完全交给原版（`BaseVillager.java:634-643` 只在 `restock()` 上挂了个装饰动画，注释明说"mod 的绿宝石经济与原版补货是两件事"）。

### 4.7 tick 成本盘点（每 tick 在跑什么 / 什么被限频 / 哪里做坏了）

每 tick 真的在跑：`BaseVillager.customServerAiStep(:679-700)` 每 tick 调 `settlementsBrain.tick(1)`，它逐个 sensor 过一遍（`VillagerBrain.java:53-58`）——但 sensor 内部由 `AbstractSensor.tick(:28-45)` 的冷却门挡住，所以每 tick 成本 = N 个布尔减法；`PlanRunnerBehavior.tick`（CORE 优先级 20，每 tick，`BaseVillager.java:952`）与 `PlanContextSwitcher.tick`（1s 冷却 + 结果缓存，`PlanContextSwitcher.java:30,59-71`）；`WorldResourceIndex` 补扫在主线程预算内（`ResourceIndexRefresher.java:79`，默认 8 section/tick，重活已丢线程池）。

限频/脏标记清单：`PERCEPTION_COOLDOWN 1s`、`RECONCILER_COOLDOWN 5s`、`NAME_SYNC 1min`、`RAIN_EXPOSURE 1s + 2 次观测去抖`（`BaseVillager.java:142-152,216,656-663`）；hunger 按配置秒数间隔（`:1162-1176`）；玩家区域轮询 5s 且有"位移 <1 格就跳过"的守卫（`PlayerSettlementTracker.java:39,67-70`）；`VillageAnimalSpawnerServerEvents` 只在 overworld + 生成规则开启时按间隔跑（`:62-77`）；persona sweep/drain 分频 1Hz（`PersonaSweepServerEvents.java:30-58`）；世界事件总线驱逐 1Hz（`WorldEventBusReaperServerEvents.java:23-28`）；`tickReconciler` 无孤儿时提前返回（`BaseVillager.java:753-756`）；UI 快照分段限频（`VillagerStatsSnapshotPublisher.java:31-33`、`DayPlanSnapshotPublisher.java:21`）。

判断做坏/可疑的四处：
- `BlockResourceSensor.java:32` 用 `ClockTicks.seconds(config.scanIntervalSeconds()).asTickable()`，没有像另两个 sensor 那样按 UUID 错峰（对比 `EntityPerceptionSensor.java:50-58`）。同一批生成/加载的村民扫描同相，会把 30 秒一次的整框枚举压到同一 tick。单次成本不大（默认 32/8 半径约 5×2×5 个 section，`WorldResourceIndex.java:147-170`），但它是全系统唯一"人人每 30 秒同步醒来"的循环。
- `WorldResourceIndex.queryAll` 每次调用 `new IdentityHashMap` + 每资源一个 `ArrayList` + `sectionsIntersecting` 的 `long[count]`（`:48-51,58,157-158`），`matchSnapshot` 每 section 再建 `HashMap`/`LongArrayList`（`:233,262-264`）。热路径短命对象在 50+ 村民规模会形成规律 GC 压力；作者知道这点（`:47` 注释"pre-allocate to avoid repeated map lookups"）但没走到复用缓冲。
- `ResourceIndexRefresherServerEvents.java:24-29` 留着 `// TODO:CONFIRM should this be throttled??`：`LevelTickEvent.Post` 每个 level 每 tick 调 `refresh`，下界/末地也照跑（无维度过滤）。成本被预算与空脏队列早退压住（`ResourceIndexRefresher.java:80-82`），所以是"作者自己不确定"而非确证的坏，仍记作风险点。
- `UiSyncServerEvents.java:43-63` 每 tick 遍历所有 UI 会话，实体丢失时发 `ClientBoundUiUnavailablePacket`——同一次调用里就 close 会话（`:59`），不会连发，可接受。

跨端同步的"全量重发"问题确实存在，集中在日程面板：`application/ui/dayplan/DayPlanSnapshotPublisher.java:21,35-58` 每 2 秒把整份 `DayPlan` 组装成快照整包发（无版本比较、无增量），而 stats 通道已经做了分段版本号脏检查（`VillagerStatsSnapshotPublisher.java:78-100,148-152`）——同一框架下两种成熟度并存（`UiChannel.java:5-7`：BEHAVIOR_CONTROLLER / VILLAGER_STATS / DAY_PLAN）。定居点本身没有列表面板：客户端看到的领地信息只有进入区域时的 subtitle（`RegionSubtitleHandler.java:31-50` 直接发 `ClientboundSetSubtitleTextPacket`）和 debug 包 `ClientBoundSettlementDebugPacket`；`presentation/ui` 下只有 `VillagerStatsScreen` 与 `DayPlanScreen`。"定居点面板数据从哪来"在本仓库无对应实现，能借鉴的是"版本化快照 + 会话心跳 + 通道定义表"这套骨架。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`infrastructure/network/core/`。`SettlementsPacket extends CustomPacketPayload`（`core/SettlementsPacket.java:5`），每个包自带 `ID` + `StreamCodec<FriendlyByteBuf, T>`；`core/PacketRegistry.java:29-56` 一次注册 16 个 payload（4 个通用/环境 + UiSync 生命周期 6 个 + 4 个 stats 快照 + dayplan + debug），`:62-76` 把 handler 写成 lambda 延迟解析 Dagger 组件，因为注册发生在客户端子组件构建之前。收端统一 fan-out 到 `ClientSidePacketReceiver` / `ServerSidePacketReceiver`。UI 会话有心跳包（`ServerBoundHeartbeatUiPacket` / `ClientBoundHeartbeatAckUiPacket`），服务端按心跳清理失效会话（`bootstrap/event/UiSyncServerEvents.java:39-41`）。
- 数据驱动：`infrastructure/minecraft/data/` 下 20 多个 DataManager 全部继承 `framework/CodecJsonDataManager.java:26-79`——目录常量 + `Codec<T>` 两样东西，基类负责 prepare/apply 线程切分、按 ResourceLocation 排序解析（`:55`）、单文件失败隔离、`onReloaded` 里构建不可变快照。`ReloadListenerModule.java:36-52` 用 `@Binds @IntoSet PreparableReloadListener` 注册（注释：新增 loader 只加一个 @Binds，忘记注册变得不可能）。建筑定义目录 `settlements/buildings/definitions`（`BuildingDefinitionDataManager.java:22`），`onReloaded` 里做 later-file-wins 去重并按 id/constrained/trait-affinity 建索引（`:42-89`）。`BuildingDefinition`（`domain/generation/model/building/BuildingDefinition.java:16-30`）字段是 footprint、trait affinities、zone tier、road frontage、requires/forbidden resource tags、proximity/global affinity、`npcProfession` + `npcCount`。重要发现：`npcProfession`/`npcCount` 只有 Codec 读取（`BuildingDefinitionCodec.java:52`）和 getter，全仓找不到消费点（grep `npcProfession()|npcCount()` 只命中定义文件）——建筑→NPC 派工在这一版还没接上；建筑的容量/产出计算同样不存在，建筑目前只是"生成期布局 + 查询期身份/显示名"两件事。
- 配置：自研注解式（`infrastructure/config/annotations/`）。`ConfigAnnotationProcessor.process()`（`:31-76`）用 `ModFileScanData.getAnnotatedBy` 扫 `@BehaviorConfig`/`@GeneralConfig` 记录类，`RecordConfigProcessor` 把 record 组件上的 `@IntegerConfig/@FloatConfig/@MapConfig/@BooleanConfig/@StringConfig` 变成 `ModConfigSpec`。一个例子就把"性能参数=配置项"表达清楚了：`application/ai/sensors/BlockResourceSensorConfig.java:7-44` 四条（水平半径默认 32、垂直 8、扫描间隔默认 30 秒、每 level-tick 扫描预算默认 8 个 section，min/max 都写死在注解里）。
- datagen：基本没有。`infrastructure/datagen/DataGenerators.java:14` 类注释写着 "This class is unused for now."，只挂了 `ModItemModelProvider`（20 行）和一个 item tag provider（25 行）。`build.gradle:95-103` 配了 `runData` 输出到 `src/generated/resources`，但该目录不存在。也就是说建筑模板、lang、blockstates 全为手写资源（且不在本地树里）。

## 6. Mixin

`src/main/resources/settlements.mixins.json` 声明 9 个 mixin，包 `infrastructure/minecraft/mixins`，无 client/server 分区，`defaultRequire: 1`。全部是 `interface` + `@Accessor`/`@Invoker` 的纯访问器，没有任何 `@Inject/@Redirect` 字节码注入：
- `EntityMixin.java:8-10` `@Invoker("isInRain")`，被 `BaseVillager.java:661` 用来采样淋雨。
- `LevelMixin.java:12-14` `@Invoker("getEntities")` 拿 `LevelEntityGetter`。
- `VillagerMixin.java:11-14` `@Accessor` 补货升级方法与 `updateMerchantTimer`（配合 `BaseVillager.java:1131`）。
- `WolfMixin.java:17`（isWet）、`CatMixin`、`DisplayEntityMixin.java:14`、`BlockDisplayMixin`、`ItemDisplayMixin`、`ArmorStandMixin`：为动画/渲染层开原版私有字段。
结论：这个 mod 不用 mixin 改行为，只用 mixin 当"受控反射"，注入面几乎为零——对研究"要不要写 mixin"是个很好的参照。

## 7. 值得学的 5 条

1. `application/ai/sensors/EntityPerceptionSensor.java:50-58`（同款 `DemandedGroundItemSensor.java:109-117`）：周期型热路径的初始延迟用 `Math.floorMod(villager.getUUID().hashCode(), intervalTicks)` 错开，注释明写"防止大村庄把全体 section 扫描压到同一个 tick"。这是零成本消除 tick 尖峰的做法，比 `tickCount % N` 强（后者让所有村民同 tick 对齐），蜂群的分层行为 tick 与新星到港结算的批处理都可以直接抄这层错峰。
2. `infrastructure/minecraft/data/framework/CodecJsonDataManager.java:26-79` + `di/modules/ReloadListenerModule.java:36-52`：datapack loader 收敛成"一个目录常量 + 一个 Codec + 一行 @Binds @IntoSet"，基类统一负责线程切分、id 排序（later-file-wins 可复现）、单文件失败隔离、快照不可变。两个 mod 的建筑/职业/配方 JSON 迟早会写出 5 份重复 reload listener，这套骨架是正解。
3. `application/ui/stats/VillagerStatsSnapshotPublisher.java:78-100,148-152`：同步粒度做成分段 + 版本号脏检查——inventory 用 `getInventoryVersion()`、demand 用 `Objects.hash(inventoryVersion, demandService.getVersion(villager))`，与上次已发版本相同就不发包（检查周期 3s，主 stats 面板 0.5s）。"给每个可同步数据段配一个单调版本号 + 已发版本号基线"正是幂等推送的最小形态，新星殖民地每日结算该照这个形状给结算结果记账。
4. `PlanRunner.java:813-819` + `:847-860` + `:758-776`：每日推进的三重去重——`runtime.getPendingNextPlan()!=null || getPendingFuture()!=null` 直接 return（不重复提交）；`markPlanExhausted()` 先测再提交（同一天只提交一次后继）；到达的计划用 `arbitrate(旧, 新, currentCalendarDay)` 按"targetDay 小于今天丢弃、同日按 author 定序"仲裁，`adoptPendingIfReady(:779-801)` 再要求 `dayTime >= wakeAtAbsoluteTick` 且"当前槽位不 ACTIVE 才换"。这套"计划以 targetDay 为键 + 单一 pending 槽 + 到点才采纳"可以直接搬到每日结算的可重入推进上。
5. `infrastructure/minecraft/worldgen/structures/SettlementStructure.java:132-136` + `persistence/SettlementMetadataQueueService.java:20-36` + `SettlementMetadataPersistenceServerEvents.java:23-37`：领地身份用坐标派生的确定性 ID（重生成必得同 ID），生成线程只投递队列、主线程 tick 才写 SavedData，`put` 里再靠 `equals` 比较决定 `setDirty()`。三者合起来就是"跨线程 + 可重放 + 只在真变了才落盘"的领地登记形状，正是蜂群领地建筑登记要避免的坑位组合。

### 结论落到两个目标工程

蜂群（领地建筑 + 分层行为）三条：
1. 边界用"结构/坐标派生 ID"登记，属性另存 SavedData，查询接口做成一个 domain port（照 `SettlementQueryService.java` + `StructureManagerSettlementQueryService.java:36-54` 的分工）：`getContextAt(level,pos)` 一次返回 settlement+building 两层上下文，重叠时按最小包围盒取最具体（`:130-133`）。领地建筑用蓝图 NBT + piece 携带定义 ID（`SettlementBuildingPiece.java:48-53`），比"每 tick 扫方块判断我是什么建筑"便宜得多，也天然跨 chunk 卸载存活。
2. 行为分层的切法照抄它的四层：原版 Brain/Activity（跑环境动作与床/钟/POI）→ 一个永不自超时的 CORE 桥接 behavior（`PlanRunnerBehavior.java:47-56`）→ 计划槽位状态机（`PlanRunner.java:246-333`，含 rigid/flexible 与重试节流）→ 具体 staged workflow。外加一个 override 槽处理"着火/被打断"类反应，别把反应式逻辑塞进主循环。
3. 建筑的"能力"用元数据目录而不是方块扫描：`BehaviorCatalogModule.java:159-183` 的 descriptor 形式（category、intensity、所需 channel、estimatedDuration、maxRunDuration、cooldown、interruptible）是给调度器的全部信息，配合 4.4 的 teardown ledger 做资源借还。反例提醒：本仓库有 `npcProfession/npcCount` 字段却无人消费（第 5 节），别在字段落地前把建筑定义当成已有功能。

新星殖民地（每日结算去重/幂等）一条：
4. 它并没有做"每日结算"，但它的"每日推进"就是同构问题，可抄的是四件套：ID/键为 `calendarDay`（`WorldCalendar.calendarDayOf` 把日界对齐到午夜，`WorldCalendar.java:27-29`，`WeekCycleProvider.java:21-25` 用 `floorMod(day,3)` 派生日类型，纯函数无副作用）；推进前用 `equals` 比较再置脏（`SettlementSavedData.java:84-89`）；单 pending 槽 + 到点才采纳 + 同日按来源优先级仲裁（`PlanRunner.java:813-819,779-801,758-776`）；推送侧带版本号基线（`VillagerStatsSnapshotPublisher.java:83-99,151`）。把"已结算到第 N 天"当成一个 `lastSettledCalendarDay` 基线 + 结果快照版本，结算函数写成 (calendarDay → 结果) 的纯映射，就同时拿到重放安全与"改了也别双发"。

## 8. 公开 API 与扩展点

没有面向第三方 mod 的 API 包（全仓无 `api/` 目录，无 `@Api`/服务加载器出口，`build.gradle:249-260` 的 maven 发布只是把自身坐标发到本地 `repo/`）。实际存在的扩展点是三类，全部"对内不对外"：

- 数据扩展：datapack JSON 目录 + Codec，即第 5 节那张清单（建筑定义、trait 定义、scorer、biome survey、history event、交易目录、作物、蜂箱产出、矿再生、烧炼/锻造目录等），任何资源包可覆盖，同 id 后加载者胜（`BuildingDefinitionDataManager.java:43-47`、`CodecJsonDataManager.java:55`）。这是唯一无需编译期依赖的扩展面。
- 代码扩展（同仓内）：Dagger multibinding 集合——`@IntoSet BehaviorCatalogEntry`（`di/modules/server/BehaviorCatalogModule.java:150-153` 头注释即操作说明）、`@IntoSet VillagerSensorFactory` + `@IntoSet BlockResource`（`di/modules/server/SensorCatalogModule.java:48-118`）、`@IntoSet OverridePolicy`、`@Binds @IntoSet PreparableReloadListener`（`di/modules/ReloadListenerModule.java:36-52`）。加东西要改这个 mod 的源码并重建，外部 mod 挂不进去。
- 域端口（读写世界的抽象）：`domain/settlement/query/SettlementQueryService`、`domain/generation/building/BuildingRegistry`、`domain/ai/schedule/IWeekCycleProvider`、`domain/ai/planning/IPlanGenerator` / `IAsyncPlanGenerator`。实现由 Dagger 绑定：`SettlementQueryModule.java:11-12`（→ `StructureManagerSettlementQueryService`）、`WorldGenerationModule.java:28`（→ `BuildingDefinitionDataManager`）、`di/modules/server/PlanningModule.java:38-41`（→ 启发式生成器，含异步壳）。理论上可替换，但入口只有 `SettlementsDagger` 静态访问（`di/SettlementsDagger.java`，用于 `CommonModEvents.java:60-68`、`ServerLifecycleEvents.java:25`），没有对外注册通道。

结论：可抄的是形状与实现手法，不是接口——上面三类扩展面全部要求把代码写进本仓库（或只做资源包），既没有面向第三方的注册入口，也没有为扩展预留的自定义事件。

遗留：`src/main/resources` 与生成资源不在本地树（第 2 节），因此建筑 JSON 字段实际取值、模板尺寸、lang key 覆盖度均未验证；`application/ai/inference/**`（LLM 计划覆写、monologue、persona 生成）与 `domain/animation`/`infrastructure/rendering` 未逐文件读，只做接入点确认。
