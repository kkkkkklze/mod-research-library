# 深挖：BOSS 引擎调研 v3——全库通用技术清单（不限 Mod 类型）

> 第三轮：一个不限工程类型的自由挖掘任务（2026-09-23），按七个方向扫全库，为 Colossus 找可移植引擎技术。全部条目有路径实证；负结果照实记录。路径相对 `源码库/_参考仓库/`。

## 方向 1：判定/碰撞数学
- **1a 弹道扫掠分段+穿透排序**（P1）| TACZ `EntityKineticBullet.java:308-340` + `EntityUtil.java:21-40`：每 tick「线段起止 + AABB `expandTowards(delta).inflate(1)` 扫掠 + 逐实体 clip + 按 hitVec 距离升序」——高速挥击/吐息不漏帧的完整配方；Ars-Nouveau `EntityProjectileSpell.java:171`（Forge 1.20.1 原生）同构。挂载点：`move/` HitSolver。
- **1b 命中窗口+接触去重键**（P0）| DBE `gas/hitbox/HitboxWindowRuntime.java:88-257`、`HitboxContactKey.java`：`(ownerUUID, scopeId, windowId)` 接触键——同一窗口对同一目标只跳一次，多段伤害=换新 windowId。与 Colossus `between(a,b)` 同构，给"持续区/多段"预置身份。
- **1c 顿帧=播放速率标量**（P1）| DBE `ActionHitStopRuntime`：纯客户端动画时钟降速（≤1 速率 + WeakHashMap 到期自动回 1.0），不冻结服务端 tick——绕开 1.20.1 停服风险的正解。
- **1d 受击击退方向三分解**（P2）| DBE `AbilityCombatEffects.java:115-135`：显式方向 > 攻击者→目标 > 目标朝向 的回退链 + `hurtMarked=true`。
- **1e 连招 i-frame 改写**（P1）| ES `LivingEntityMixin:58-61`（打后无敌帧做成事件钩子）+ Apotheosis `SocketedGems:58-61`（`invulnerableTime` 存-零-打-还原的无损补刀套路）。挂载点：`MoveDef.postAttackInvuln`。
- （RaycastBuilder 链式形状参考：Iron's Spells `api/util/RaycastBuilder.java`。）

## 方向 2：无头/确定性测试
- **2a 纯 JVM 内核 + fixture 注入**（P1）| refinedstorage2 `NetworkTestExtension`：领域逻辑零 MC 依赖 + JUnit5 扩展注入假对象——Colossus 的 `state/`/`move/` 已同构（FrameRunner 已零依赖），升级路径=把 Level 依赖收进接口后换真 JUnit。
- **2b 声明式 GameTest DSL**（P1）| SuperFactoryManager `SFMDeclarativeTestBuilder`：spec/builder 声明「摆方块→给时间→断言」，纯单测与 GameTest 双层分离。Colossus 可做 `BossTestScenario`（spawn→tick N→断言状态栈/触发帧命中数）做招式回归。
- **2c 一次性空白 level**（P2）| sable `SableTestHelper:23-37`：`newEmptyChunk` 现场造微型 level，适合 ArenaBlockAccess/TelegraphZone 结算测试。
- 负结果：库内无 Forge 1.20.1 现成 headless-server harness；`minecraft-biology-dictionary` 的 testServer 是源码级不变量断言（思路可用于"每个 DATA_ 键必须注册"守卫）。

## 方向 3：序列化与数据驱动
- **3a Codec+StreamCodec 成对类型注册表**（P0）| Eternal Starlight `vfx/VfxType.java`+`ScreenShakeVfx.java:16-47`（原生 1.20.1 血统）：一种效果类型带 `MapCodec`(JSON)+`StreamCodec`(网络) 双编码，`VfxInstance.send(ServerLevel)` 一个通用包广播——TelegraphZone/演出 cue/血条样式共用管线，也是招式 JSON 化的最贴合样本。
- **3b JSON 重载监听器族：tag 为键**（P1）| Create Big Cannons `BlockArmorPropertiesHandler:57-88`：`SimpleJsonResourceReloadListener` + tag→属性表 + 自定义序列化器扩展 + 同步——破块伤害表照此。
- **3c 表达式解析**（P2）| GeckoLib5 `MathParser`、refinedstorage2 query-parser（Pratt 微型版够用，别引 Rhino）。
- **3d datapack 目录→运行时表整体装配**（P2）| AdventureRedefined `RMSongpackLoader`。

## 方向 4：同步技巧
- **4a 双端时钟漂移纠偏完整算法**（本轮最重要，P0）| DBE `ActionPlaybackClockSynchronizer.java:20-95`：`DEAD_ZONE=4ms / HARD_REBASE=80ms / SMOOTH_RECOVERY=0.12s`；|err|<4ms 不动、状态变化或 ≥80ms 硬快照、否则 `recoveryRatio=clamp(err/0.12)` 平滑收敛、`advanceScale=1-|err|/0.12` 减速追赶且**永不倒退**。→ `api.anim.SyncedAnimClock` 的定版常数。注：Colossus 的 ATTACK_TICK 走 entityData 每 tick 同步、本身无漂移；该模块服务的是 GeckoLib 适配层（本地动画时钟与逻辑 tick 的映射），随 GL3 落地。
- **4b 通用演出 cue 单包**（P1）| ES `VfxPacket`（type id+data）——避免每加一种粒子/震屏新写包。
- 负结果：未发现第三种独立插值库；TACZ 全程 entityData 扩展是"零包路线"又一旁证。

## 方向 5：HUD/演出
- **5a 世界空间径向震屏**（P1）| ES `client/visual/ScreenShake.java`：震屏=带位置/半径/双轴功率/easing 的世界空间实体，随距离衰减——巨型 Boss 落地砸击正配。
- **5b 伤害数字（Forge 1.20.1 原生现成）**（P2）| DamageIndicators：`RenderLevelStageEvent.AFTER_TRANSLUCENT_BLOCKS` 世界文字 + `RegisterGuiOverlaysEvent` 全屏受击闪屏 + 客户端缓冲队列 `DamageTextHandler`。
- 负结果：库内无独立可用的 timeline/cutscene 通用工程；编排长在 DBE 式 timeline+状态机上。

## 方向 6：音效同步
- **6a 客户端读 BossBar 反推战斗态**（P2）| AdventureRedefined `SongPicker`+`BossBarHudAccessor`：零协议、bar 可见=开打的兜底触发。
- **6b 音乐 ducking**（P2）| `PlayerThread:39,184`：`QUIET_VOLUME_PERCENTAGE=0.7 + lerpConstant 0.02/buffer`——音乐是持续闪避不是开关。
- **6c 抢占 vanilla BGM**（P2）| `MusicTrackerMixin` tick HEAD cancel 一行式闸门。

## 方向 7：其他
- **7a 招式派生与传送续播**（P1）| DBE `timeline/ActionSectionFlow/Redirect/Transition`（招式内段落跳转=变招/派生）+ `RootMotionVisualCatchUpKt:32-59`（位置回同步时以 beforePosition/beforeCycle 续播而非重放）。`MoveDef` 预留 `section` 概念。
- **7b 事件名 catalog 化**（P2）| DBE `StateTreeEventCatalog`：注册期校验可订阅事件名——Colossus 演出事件/visual id 值得同款守卫。
- **7c 库自带可编译示例源集**（P2）| Moonlight `src/example/java/`：每特性配编译期示例，`testboss/` 升级为受编译保证的 example 源集。

## Top 5（agent 原排序 + 我方落点）
1. 4a 漂移纠偏 → 随 GL3 适配落地（SyncedAnimClock）
2. 1b 窗口+ContactKey → FrameRunner 窗口实例化（持续区/多段时启用）
3. 3a/4b/5a cue 双编码注册表 → move JSON 化、TelegraphZone、震屏共用管线
4. 1a 扫掠 HitSolver → 近战挥击/落雷不漏帧
5. 2a/2b 双层测试 → StateSelfTest 升级招式回归
