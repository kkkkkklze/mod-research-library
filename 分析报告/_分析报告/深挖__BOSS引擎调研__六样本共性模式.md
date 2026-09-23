# 深挖：BOSS 引擎调研——六个真实工程的共性模式

> 服务于 Forge 1.20.1 BOSS 框架 MOD（Colossus）的设计输入。2026-09-23，五路并行源码分析蒸馏。
> 样本：[首领崛起] block_factorys_bosses + unusualend（同作者两代）、L_Ender's Cataclysm、Twilight Forest(1.20.1 移植)、Eternal Starlight、Iron's Spells、外加五个周边系统（Draconic Evolution 护盾条 / FDLib bossbar 库 / dumbcatmod 人数缩放 / Confluence 召唤与进度 / Alex's Caves ACBossEvent）。

## 一、共性结论（跨样本反复出现的结构）

### 1. 阶段 = 同步 int + 一次性血量闸门，切换本身是一个"不可打断的技能"
所有样本的 boss phase 都是 `SynchedEntityData` 里的 int（`DATA_BOSS_PHASE` / `BOSS_PHASE` / `PHASE`），阈值检测写在 tick 头部，用 `phase < N` 做一次性闸门（BR 的 `hpGate75/50/25`、Cataclysm Ignis 的 `getBossPhase()<1`、ES 的 `getPhase()==0 && hp<50%`）。切换动画期间**完全免伤**（Ignis `hurt()` 直接 return false）+ 阈值区间减伤，改阶段数发生在动画关键帧（`animationTick==34 → setBossPhase(1)`）而不是检测瞬间。**阶段对技能做门控**：技能入场条件里带 `phase>=N` / `phase in (0,2)` 谓词。

### 2. 技能调度收敛为「状态机 + 声明式招式表」，中间形态是 招式 Phase 类
三代演进清晰可见：
- Cataclysm：`tick()` if-else 优先级瀑布 + 每个动画一个 `AnimationGoal`（`canUse = goal.test(currentAnimation)`）——"动画即状态机"。
- ES：`BehaviorManager` + 每招一个 `BehaviorPhase(id, priority, duration, cooldown, turnsInto)` 类（≤40 行），tick 驱动。
- BR(新)：`BR/state/` 独立状态机包——`State.onStart/onTick→Result.CONTINUE|END/onEnd` + `StateController` **状态栈**（push/replaceActive/replaceAll，`ActiveState` 自带 timer）+ `StateRegistry` 名字注册 + `DataState(Codec)` 可序列化 + `StateGoal` 挂进原版 AI + 整栈 NBT 存读。这是全库最成熟的引擎层，纯 MC 无关代码，1.20.1 可直接移植。

**判定帧**全部是"动画 tick 计数器上的魔数"（`animationTick==24 → AreaAttack(...)`、`frame==21`），IS 把它结构化成了 `AttackAnimationData = animationId + lengthInTicks + Int2ObjectMap<AttackKeyframe>`——keyframe 前的 tick 即前摇、keyframe 当帧判定、剩余即后摇。**没有任何样本做 JSON 数据驱动**（全库 grep 无 attack 池的 datapack 加载），招式表全是硬编码 static final——这是框架最大的差异化空间。

### 3. 伤害判定不碰动画库，服务端自己算
无一例外用服务端 AABB+几何过滤（`getEntityLivingBaseNearby` → 距离/扇形 `atan2 vs yBodyRot`/高度带），伤害走 `hurt(damageSources().mobAttack(boss), dmg)`，并显式重置 `invulnerableTime=0` 允许一套连招多帧命中。高级形态：BR 的 `ServerAnimationPlayer` + `positionPartsFromBones`——**服务端每 tick 采样动画骨骼位置**，让子实体碰撞盒真实跟随动画（GeckoLib 3 on 1.20.1 没有这个 API，框架要留 AnchorSampler 抽象口）。

### 4. 死亡被统一延迟：动画先播、结算后到
两套实现殊途同归：Cataclysm `onDeathUpdate(deathDuration)` 在 `tickDeath` 里数帧；BR 更狠——`maybeCancelDeath()` 把血量钉回 0.1f，播完死亡动画后 `simulatePlayerKill()` 重新打一次真死。**掉落、成就、进度记录全部挂在延迟后的结算点**。TF 的 `IBossLootBuffer` 再加一层：loot 结果先缓冲进实体 NBT（防区块卸载/满包丢物），最后放进 home 点下方宝箱——"开箱仪式感"。

### 5. BossBar：都基于 ServerBossEvent，都只补一条"样式旁路"
最干净的协议（ACBossEvent / Cataclysm CMBossInfoServer，同为 Forge 1.20.1）：`extends ServerBossEvent` 只加 `int renderType`，`addPlayer` 时旁路补发 `{barId, renderType}` 包；客户端 `CustomizeGuiOverlayEvent.BossEventProgress` 命中则 `setCanceled(true)` 换自绘。复杂需求（护盾/晶体/多资源条，DE）：setter 脏检查 + 进世界快照全包（op0）+ 客户端 100ms wall-clock lerp。完全脱离实体的裸 bar（IS ExtendedServerBossEvent / FDLib）在"多实体共一条 bar、可见性动态开关"时才需要——KnightPhantom 队长聚合全场血量、Kraken bar=触手血量均值，都属此类。

### 6. 参战者管理是所有工程的公共痛点，收敛为 hurt 收集名单
ES/Cataclysm/BR 都在 `hurt()` 里把玩家加进 `fightParticipants`，tick 剔除死亡/远距玩家；胜利时**对名单全体**触发击杀成就（解决"最后一击不是我"），ES 还维护 Map 型"挑战次数"并进 Data Attachment → 供 loot condition `boss_challenge_count{min,max}` 读取做保底。原生 bar 的 players 集合是"**可见**"不是"**参战**"，两者的差集就是框架 EngagementTracker 的价值空间（dmg+lastAggroTime+TTL）。

### 7. 多人缩放：没有一个是认真的
Cataclysm 只有全局配置乘区 + 半成品 LIFE 计数（64 格内存活玩家数→归零触发 Retry）；BR 两个工程**完全没有**缩放；唯一实现的是 MCreator 生成的 dumbcatmod：`sqrt(n)-1` 曲线、AABB inflate 40 计数、10 tick 轮询、变更时 `addTransientModifier` 且**按血量百分比回填**（`setHealth(frac*newMax)`）。框架该提供策略接口。

### 8. 召唤与进度：一次性召唤石 + 全局击杀板
共同形状：`BossSpawnerBlock(Entity)` = 刷 Boss 后自毁（TF/BR），BR 的箱子变体以"玩家在指定结构里开了指定容器"为触发；Cataclysm 反转为闭环——**Boss 死亡在尸体下放置 Respawn Spawner + 把召唤物塞进它物品栏**，玩家拾回再右键重召。进度状态：TF 用 advancement 树当 DAG（结构内嵌 `advancements_required`，事件拦截执行锁：破坏/交互/伤害三处取消 + 提示书掉率），Confluence 用全局 `SavedData KillBoard{defeatedBosses: Map<EntityType,Boolean>}` 供交易锁查询。**TF 1.20.1 移植版已删掉旧 DeferredScript/Arena**——竞技场强制传送在成熟工程里是空白，是框架可补的点。

### 9. 网络：战斗状态零自定义包
全部状态走 `SynchedEntityData`；自定义包只管四件事：bar 样式、音乐开关、粒子/音效事件（`ParticleEventMessage(entityId,name)`）、玩家附件同步。音乐是**服务端幂等布尔 + 客户端单例播放器**（`canPlayMusic()` 每 tick 发 `MessageMusic(id,true/false)`，客户端持有 boss 引用、setBoss(null) 淡出）。

### 10. 每写一个新 Boss 的样板税（框架要吃的重复劳动）
bossEvent 装配+startSeen/stopSeen 挂钩、BehaviorManager 构造、每招一个类+ID 常量+同名 AnimationState+`onSyncedDataUpdated` 巨型 switch、phase 键 save/load、aiStep 里 bar.update()+manager.tick()、tickDeath 定长移除、finalizeSpawn 缩放、hurt 收集参战、die 结算 40 行、召唤物/进度挂钩。ES 一个 Boss 拆 15 个文件里 12 个是纯样板。

## 二、分歧点（框架必须做选择的地方）

| 维度 | A 派 | B 派 | 框架裁决 |
|---|---|---|---|
| 调度内核 | vanilla Goal 表（IS/Cataclysm） | 自有 StateController 栈（BR） | **两者桥接**：内核是状态栈，`StateGoal` 一个 goal 占位（BR 已验证） |
| 招式建模 | Phase 类（tick 常量判帧） | 数据表（duration+cooldown+权重；IS keyframe） | **代码 builder 生成 keyframe 表**，为 JSON 化预留 Codec；权重按上下文（距离/阶段）可给函数 |
| 动画后端 | vanilla AnimationState+数据包事件 | GeckoLib | **后端适配器接口**，核心不依赖 GeckoLib（1.20.1 有 GeckoLib 3 可作官方适配） |
| 进度存储 | advancement（per-player，原版 UI） | SavedData（全局，查询简单） | **双轨**：KillBoard(SavedData) 为权威，advancement trigger 联动桥 |
| 打断语义 | `isInterruptable()=idle 才可断` | 免伤过场不可断 | 状态自带 interruption 策略 + 转段窗口用负 timer 表达 |

## 三、不该进框架的东西
具体 tick 魔法数与招式语义（碎盾/弹反/翻滚）、黑屏运镜、船体缓存竞技场、MCreator procedures、Cataclysm 双框架历史包袱、BR `@Deprecated` 双基类（框架只留一个基类+组合式 controller）、YetiState 式"把动画/音效/移动锁塞进枚举"的私有写法、CC BY-NC-ND 许可的 Cataclysm——只取思想不搬代码。

## 四、样本路径索引
- BR 状态机包：`_pack_decompiled/璇穹之歌/[首领崛起] block_factorys_bosses-2.1.2-neo-1.21.1/net/unusual/block_factorys_bosses/state/`（12 文件）
- BR 基类：`.../entity/boss/AbstractStateBossEntity.java`、`AbstractBossEntity.java`(deprecated)
- Cataclysm：`_bulk/lender544__new1.20.1/.../entity/etc/CMBossInfoServer.java`、`entity/AnimationMonster/AI/AnimationGoal.java`、`BossMonsters/Ignis_Entity.java`（判定帧:824）
- TF：`_bulk/marlester-dev__twilightforest-unofficial/.../entity/boss/PlateauBoss.java`、`events/ProgressionEvents.java`、`entity/KnightPhantom.java`(队长聚合)、`enums/BossVariant.java`
- ES：`_bulk/LeoMinecraftModding__eternal-starlight/common/.../entity/living/boss/ESBoss.java`、`entity/living/phase/BehaviorManager.java`、`item/loot/BossChallengeCountCondition.java`
- IS：`_bulk/Iron431__irons-spells-n-spellbooks/.../entity/mobs/goals/melee/AttackAnimationData.java`、`wizards/GenericAnimatedWarlockAttackGoal.java`、`fire_boss/ExtendedServerBossEvent.java`
- 周边：DE `ShieldedServerBossInfo.java`；FDLib `systems/hud/bossbars/`；dumbcatmod `custom/boss/BossScaling.java`；Confluence `KillBoard`/`BossDelaySpawner`/`AnyBossDefeatedLock`；AC `server/entity/util/ACBossEvent.java`（唯一原生 1.20.1 样本）
