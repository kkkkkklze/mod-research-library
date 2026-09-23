# Confluence 源码分析报告

> 样本：`源码库\_参考仓库\_bulk\MagicHarp__confluence`（terra 系内容整合包 mod，泰拉瑞亚式流程移植进 MC）。
> 重要前提：这是**稀疏/部分检出**。settings.gradle:14-23 声明了 6 个子项目（ConfluenceOtherworld + git submodule：Confluence-Magic-Lib、TerraEntity、TerraCurio、TerraGuns、TerraFurniture），本地**只有 ConfluenceOtherworld 主模块**；Boss 实体本体（`org.confluence.terraentity.entity.boss.*`，含 AbstractTerraBossBase、各 Boss 的招式/阶段/BossBar）与被引用的 `org.confluence.lib.*` 均不在盘上。本仓库是"调度与进度胶水层"，Boss 战斗内核全部在缺失的 TerraEntity 子模块里——凡涉及实体内部招式/阶段/血条的判断，本报告一律给胶水层证据并标注"未验证"。
> 与六样本综述的关系：综述只点名了 KillBoard/BossDelaySpawner/AnyBossDefeatedLock 三个词；本报告把这三者连同 GameEvent 入侵系统、GamePhase 属性 DataMap、TradeLock 注册表一起展开到行号级。

## 1. 基本信息

- mod_id `confluence`，mod 版本 `1.3.0`，许可证 `GNU LGPL 3.0`，作者 Magic Harp 等十人（`ConfluenceOtherworld/gradle.properties:1-6`）。
- 目标平台：MC 1.21.1 / NeoForge 21.1.219，loader [4,)，parchment 1.21（根 `gradle.properties:7-9`；`ConfluenceOtherworld/build.gradle:24-31`）。GeckoLib 4.8.4、Curios 9.5.1、TerraBlender、JEI、Create、Ars Nouveau、Iron's Spells、KubeJS 等为编译/运行期依赖（根 `gradle.properties` 12-33 行区间；`ConfluenceOtherworld/build.gradle` 依赖段）。
- Gradle 插件：`net.neoforged.moddev` 2.0.140（根 `build.gradle:6`），多模块工程（根 `settings.gradle:22-23` 循环 include 全部子项目），foojay toolchain 解析；Java 21（根 `build.gradle:9`）。
- 编译产物发布坐标：group `org.confluence.mod`，artifact `ConfluenceOtherworld`，version `1.3.0-beta-yyMMdd`（`ConfluenceOtherworld/build.gradle:16-18`、`base.archivesName` 行 20-22）；`maven-publish` 推到自建 `maven.confluence.ink/releases|snapshots`（`ConfluenceOtherworld/build.gradle:537-556`）。其余五个子项目以 `implementation jarJar(project(":名称"))` 内嵌进最终 jar（同文件 207 行），ParticleStorm/TheTrackers 等外围同理 jarJar（210-212 行）——是"库内置"而非 relocate 重定位。
- 工程卫生细节：run 配置里预置 `client1/client2` 双开账号（`ConfluenceOtherworld/build.gradle:36-46`）、IDEA 热重载 JVM 参数（`-XX:+AllowEnhancedClassRedefinition`，63-68 行）、`genVoilaRun` 任务自动生成 IDEA 运行配置（567 行起）。

## 2. 源码规模与包结构（实测）

- `ConfluenceOtherworld/src/main/java` 下 **1736 个 .java、183,113 行**（`find | xargs cat | wc -l` 复核，与卡片 184,849 的差异是换行统计口径；卡片把 `src/generated/resources` 缺席也算进去了——本检出确实**没有** generated 资源目录，`src/` 下仅 `main/`）。
- 资源侧在盘：`src/main/resources/META-INF/neoforge.mods.toml`、`accesstransformer.cfg`、三个 mixin 配置 json、`assets/`；**datapack 生成产物不在盘**。
- 主要包（`org/confluence/mod/` 下，文件数实测）：

| 包 | 文件数 | 内容 |
|---|---|---|
| `common` | 953 | 游戏逻辑主体：data/saved（全局进度）、gameevent（入侵事件）、event（总线订阅）、init（注册）、loot、recipe、block、item、worldgen、attachment |
| `client` | 326 | 界面/渲染/手册（Bestiary）屏 |
| `mixin` | 188 | 注入（含 40+ 个 integration.* 针对第三方 mod 的注入） |
| `integration` | 102 | 对 TerraEntity/TerraCurio/Create/ARS/JEI 等的适配，其中 `terra_entity/` 49 文件是最厚的胶水 |
| `network` | 56 | 33 个 S2C + 若干 C2S payload |
| `api` | 58 | 对外事件（25 个 *Event）+ 农历/干支历法库（lunar/，纯计算） |
| `mixed` | 33 | 接口型"影子字段"（Immunity、IMinecraftServer 等） |
| `util` | 18 | ModUtils/PlayerUtils/AchievementUtils 等 |

- 最大源文件 Top 12 基本全是 datagen 与静态表（4817 行 `ModChineseProvider`、3073 行 `Lunar`、2275 行 `ModDataProvider`、2176 行 `ValueSubProvider`、2092 行 `ModBlockTagsProvider`、2017 行 `ModTabs` 等）——**没有一个是 Boss 实体类**，佐证"战斗内核不在此模块"。
- `integration/terra_entity/` 的典型手法：`TEEvents.modifyAttributes`（`TEEvents.java:31-112`）用 `AttributeRegistration` builder 链（`.set(属性).register(EntityType, 值)`）给缺失子模块的几十个 Boss/怪物批量补挂穿甲/护甲等自定义属性——跨模块属性注入集中在一个文件里，而不是散进各实体类。

## 3. 入口与注册

入口 `org/confluence/mod/Confluence.java`（32-110 行）。构造器只做三件事：注册配置 → 把约 25 个 `DeferredRegister` 挂上 mod 总线 → 若干非注册表初始化：

```java
// Confluence.java:39-49
public Confluence(IEventBus eventBus, ModContainer container) {
    StartupConfigs.register(container);
    CommonConfigs.register(container);
    if (LibUtils.isPhysicalClient()) { ClientConfigs.register(container); ... }
    TEEvents.register(eventBus);
    ModBlocks.register(eventBus);
    ModItems.register(eventBus);
    ...
```

- 游戏事件总线订阅点全部走 `@EventBusSubscriber` 静态类：`common/event/game/TickEvents.java:34`（LevelTick/PlayerTick/EntityTick/ServerTick 各一个 Post 事件）、`common/event/game/entity/LivingEntityEvents.java:104`（死亡/受伤/装备/物品使用等）、`common/event/NetworkEvents.java:15-17`（`RegisterPayloadHandlersEvent`，单个 `event.registrar("1")` 链式注册 33 个 playToClient + 约 10 个 playToServer）。
- 全局状态不用 Attachment 而用 **enum 单例 + 自定 IGlobalData 序列化契约**（`KillBoard.INSTANCE`、`GameEventSystem.INSTANCE`、`BossDelaySpawner.INSTANCE`…，驱动代码在缺失的 lib 模块，未验证其 SavedData 宿主；`ConfluenceData.java:58-62` 展示同仓库手写 SavedData 的对照面：`getDataStorage().computeIfAbsent(new Factory<>(...), MODID)` 按主世界维度存）。
- mod 总线上还广播自定义注册事件供 addon 注入：`GameEventSystem.java:48` 在枚举初始化时 `ModLoader.postEvent(new CustomGameEventRegisterEvent(map))`，第三方 mod 可往 map 里加自己的 GameEvent。
- 另有两处懒注册：gamerule `confluenceSpreadableChance` 在首次需要时才 `GameRules.register`（`Confluence.java:81-85`），payload Type 统一走 `Confluence.createType(id)` 工厂（107-109 行），保证包 id 命名空间不散落。

## 4. 核心系统

细读取舍：18 万行不可能通读。按"对 Colossus 的七个问题清单"的贡献度，细读了 `common/data/saved/`（KillBoard/GamePhase/BossDelaySpawner/MeteoriteTracker/ConfluenceData/HardmodeConvertor）、`common/gameevent/`（GameEvent/GameEventSystem/BloodMoon/LanternNight/SlimeRain 的 checkEnd）、`common/event/`（TickEvents/LivingEntityEvents/EntityEvents/NetworkEvents）、`integration/terra_entity/`（召唤/交易锁/属性注册胶水）与 `mixin/` 中 Boss 相关注入；略读了 client/（326 文件界面层）、api/lunar/（纯历法计算）、worldgen/、recipe/ 与 40+ 三方 integration mixin。

### 4.1 进度内核：KillBoard（全局击杀板，SavedData 语义）

- 数据表示：两张 fastutil `Object2BooleanMap`——`defeatedBosses: Map<EntityType,Boolean>` 与 `defeatedEvents: Map<ResourceKey<GameEvent>,Boolean>`，外加一个 `gamePhase` 枚举字段（`KillBoard.java:39-41`）。两张 map 都有 Codec（NBT 存档用）与 StreamCodec（网络用）双份定义（`KillBoard.java:34-37`），存档 key `confluence:kill_board`（167 行）。
- **写入点只有两处**：① Boss 死亡——`LivingEntityEvents.livingDeath`（127-129 行，门是 `victim instanceof Boss && boss.shouldShowMessage()`）→ `ModUtils.bossDeath`（`ModUtils.java:156-160`）→ `KillBoard.defeat(type)`；② 入侵事件结束——`GameEventSystem.tick`（92 行）`defeat(event.key())`。
- `defeat(EntityType)` 内部**硬编码推进全局阶段**：骷髅王→AFTER_SKELETRON，血肉墙/血墙山→WALL_OF_FLESH，其他一律触发灯笼夜排程（`KillBoard.java:89-100`）。`setGamePhase`（115-125 行）是副作用闸门：进入 MOON_LORD 写 GRADUATED 秘密旗标；进入 WALL_OF_FLESH 调 `onUnlockHardmode`（127-133 行）——翻转世界旗标、用 GlobalCloakData 揭示氯化绿矿脉、并启动 `HardmodeConvertor.INSTANCE.start(server,false)` 的分块渐进地表改造（`HardmodeConvertor.java` 336 行，tick 驱动的方块置换）。MECHANICAL_BOSSES 之后的阶段推进不在此仓库（本盘仅 `/confluence gamePhase set` 命令 与秘密种子可写，`ModCommands.java:109-115`、`TooEasy.java:38`），推断在 TerraEntity 的死亡处理里——未验证。
- 读取点遍布全模：`isAnyMechBossDefeated()/countDefeated(...)`（58-79 行）供新三王条件；`getGamePhase()` 供掉落条件（4.4 节）、实体混变（`EntityMixin.java:174-181`）、命令、经济倍率（`ModUtils.java:193-195`）。
- 跨端流转：任何 defeat/阶段变更都 `KillBoardSyncPacketS2C.sendToAll()`（99/108/118 行）。该包**没有字段**——StreamCodec 的 encode/decode 直接读写 KillBoard 单例本体（`KillBoardSyncPacketS2C.java:16-27`），即"全表快照、改包即改内存"，配合 `GamePhase` 的 `@NetworkedEnum(BIDIRECTIONAL)`（`GamePhase.java:25`）保证网络 id 映射安全。客户端交易锁、手册、HUD 因此始终有权威镜像。
- advancement 与 KillBoard 的联动方式：不走进度触发器，而是**服务端程序化直发**——`AchievementUtils.awardAchievement`（`util/AchievementUtils.java:182-192`）拿 `confluence:<path>` 成就、用假判据 `"never"` 调 `player.getAdvancements().award(...)`，并用玩家持久化数据做幂等守卫（防重复弹 toast）。全仓库只注册了一个真触发器 `ShimmerTransmutationTrigger`（`common/init/ModAdvancements.java:19-23`）。击杀宝袋/成就发放点即 4.5 节的 bossDeath 循环。

### 4.2 召唤调度：BossDelaySpawner（延迟召唤队列）

- 数据表示：内存 `ArrayList<Delayed<AbstractTerraBossBase>>`，每项 = (剩余 tick, EntityType, `ToIntFunction<ServerPlayer> predicate`)（`BossDelaySpawner.java:37,149-159`）。
- 语义是**四值返回码**：predicate 对每个在线玩家跑一次，`SUCCESS(0)` 就地以该玩家坐标召唤（`ModUtils.summonBoss` 把 Boss 抛到玩家 30~50 格外随机点，`ModUtils.java:127-138`）；`CANCEL(-2)` 作废；`CONTINUE(-1)` 跳过该玩家；**返回正数 n 表示"n tick 后再查"**（`BossDelaySpawner.java:39-61` 及 63 行的中文注释契约）。这就是它的"等待窗口"——例如克苏鲁之眼排程 1350 tick（约 67 秒）后，每 20 tick 复查"玩家在地表高度以上 + 夜晚 + 装备门槛"（90-94 行）。
- 防重复：入队前查 `KillBoard.isDefeated(type)` 和 `hasSameTypeInQueue(type)`（83 行）；队列容量写死 8，满则 `removeFirst()` 静默丢最老项（65 行）。多人竞态处理=**谁先满足谓词谁召唤、单条目只成功一次**（45-50 行 break-labeled）。
- 触发源是时钟而非玩家：`TickEvents.levelTick$Post` 每天 19:30 调 `spawnEyeOfCthulhu`、00:00 调 `spawnDeerClops`（`TickEvents.java:46-54`），且只在自定义主世界维度跑（38 行）。自然召唤的前置互斥：事件进行中不刷（80-81 行）、`Boss.noBossInWorld(level)`（109/146 行，方法在缺失 lib，按名推断为全场扫 Boss——未验证实现）。
- 玩家主动召唤走另一路：`BossSummoningItem.use`（`BossSummoningItem.java:33-53`）——condition 谓词 + factory 造实体 + **全维度实体扫描判重**（37 行），成功则扣道具、传送到玩家 ±50 格、并强制结束灯笼夜（50 行）。服装商人之死这种"剧情召唤"直接在死亡事件里 new Boss + finalizeSpawn(EVENT) + summonBoss（`LivingEntityEvents.java:143-151`）。地牢守卫者是巡逻型：玩家未杀骷髅王且在结构 BB 内滞留，每 100 tick 检查、警告 3 次后瞬刷（`DungeonStructure.checkSkeletronDefeated:556-576`）。
- Boss 还会反向改写全局规则：玩家复活等待时间按"周边是否存在任何 Boss 实体"二选一取配置区间（`util/PlayerUtils.java:394-406`，AABB inflate `Short.MAX_VALUE` 粗筛 + `BOSS_RESPAWN_TIME_MIN/MAX` 配置）——"Boss 战期间惩罚复活"这种体验参数被做进了通用复活管线而不是 Boss 类里。

### 4.3 入侵事件系统：GameEvent（与 Boss 平行的第二调度轴）

- 接口 `GameEvent.java:15-56`：`open/close/tick/canStart/canEnd/onStart/onEnd/started/forceStart/forceEnd/encode/decode/countKilled` + `ResourceKey` 身份（自带注册表 key `confluence:game_event` 的 KEY_CODEC/KEY_STREAM_CODEC，16-18 行）。9 个内置事件全部 enum 单例，集中登记在 `GameEventSystem.events` IdentityHashMap（38-49 行），addon 通过 `CustomGameEventRegisterEvent` 追加。
- 驱动：`GameEventSystem.tick()`（80-104 行）每 tick 遍历——`canEnd` 成立则结算并写 KillBoard；`canStart` 成立则开启并全量广播 `GameEventSyncPacketS2C`。事件计数（含"非环境事件"分类）缓存为 transient 字段供他处 O(1) 查询（135-151 行）。
- 互斥/竞态约定散在 canStart 里：灯笼夜要求"血月没开 + 全场无 Boss"（`LanternNightGameEvent.java:83`）；血月要求"克眼不在召唤队列里"（`BloodMoonGameEvent.java:81`）；克眼自然刷要求"没有任何进行中事件"（`BossDelaySpawner.java:80-81`）。排程用 `schedule()` 置脏位、下个 19:30 兑现（LanternNight 62-64、72-77 行）——与 4.1 的 defeat 联动。
- 刷怪实现：每个入侵事件持有一个 vanilla `CustomSpawner` lambda，注册进维度（`BloodMoonGameEvent.java:42-49`）；核心 `GameEventSystem.customSpawner`（207-258 行）：存活集合按"区块已加载且未移除"修剪（197-205 行），上限 = `base + 在线人数*perPlayer`（配置驱动，225 行），按玩家所在区块的刷怪速度倍率折算间隔（231 行），在玩家 24~32 格外投点、`MobSpawnType.EVENT` 生成、贴事件专属 tag、可选锁定玩家为目标（239-253 行）。怪物名单在 open 时 post `GameEventSpawnerDataModificationEvent` 允许外部加权改写（`BloodMoonGameEvent.java:55-58`）。
- 跨端：事件开/关广播 key 列表；哥布林军团另有 `GoblinArmyProgressPacketS2C` 进度条包。事件状态持久化在 `confluence:game_event_system`（serializeKey 171 行），但**存活实体集合 spawned 是 transient**，重启后由 tag 与 discard 逻辑收敛（未验证是否有重扫）。
- 事件↔Boss 双向耦合的样本：击杀国王史莱姆会强制结束 slime rain 并给全服发 "sticky_situation" 成就（`SlimeRainGameEvent.checkEnd:261-268`，挂点 `LivingEntityEvents.java:129`）；反向地，slime rain 进行中 WoF 死亡走特殊成就要分支（`ModUtils.java:170,178-179`）。对 Colossus 的启示：Boss 死亡回调要能触达事件调度器，Confluence 用"死亡事件里逐个调 `event.checkEnd(victim)`"这种 O(1) 硬接线，事件数量多了会退化。

### 4.4 全局缩放：GamePhase 属性 DataMap（本仓库最接近"多人/进度缩放"的东西）

- `GamePhase2AttributeModifiers.java:39-48`：NeoForge **数据映射**（挂在 EntityType 注册表上，`ModDataMaps.java:38-43` 注册，带 Codec + 自定义 Merger + 自定义 Remover），值为 `Map<GamePhase, AttributeModifiersValue>`；取某阶段值时向低位回退（44-48 行 `get`）。
- 应用时机：`FinalizeSpawnEvent` 末尾统一 `applyModifiers(mob)`（`LivingEntityEvents.java:455-457`）；对玩家和（默认）原版生物跳过（52-57 行），和平/简单难度跳过（59 行）；改完属性直接 `setHealth(getMaxHealth())`（70 行）——**阶段推进瞬间全图怪物数值换代**，数据包可覆盖/删改（Remover/Merger 各一套编解码）。这是"内容随进度变强"的数据驱动样板，但**不是**按人头缩放：本仓库内没有玩家数→Boss 属性的通道（`LibUtils.isAtLeastExpert/isMaster(level,pos)` 提供专家/大师难度判定并广泛影响掉落/减益，如 `ModUtils.java:213-216`、`TreasureBagItems.java:51,65`，判定实现依赖区块内玩家数与否在缺失 lib——未验证）。

### 4.5 伤害结算与免伤窗口（胶水层可见部分）

- 原版 10 tick invulnerableTime 被替换为**按伤害来源逐一记名无敌帧**：`mixed/Immunity.java`——武器/弹幕实现 Immunity 接口，命中时 `calculateInvTicks` 往受害者身上的 `Object2IntMap<Immunity>` 写帧数（55-64 行），`EntityTickEvent.Post` 全实体递减（66-87 行，挂点 `TickEvents.java:92-95`），`LivingIncomingDamageEvent` 里若该 cause 仍在表中即 `setInvulnerable(true)`（`EntityEvents.java:107-110`）。帧数默认按攻速折算 `(int)(20/speed)-1`（`Immunity.java:96-103`）。
- 关键设计是 `Type.STATIC/LOCAL` 二枚举（107-115 行）：STATIC 以"类"为敌（多支同源弹幕不叠伤不骗伤），LOCAL 以"实例"为敌（多个召唤物各算各的）。无敌帧 map 与 `extraInvulnerableTicks` 由 `LivingEntityMixin.java:60-92,140-147` 注入实体并随 NBT 存读。
- Boss 侧免伤窗口只见到一例跨模块修补：`mixin/integration/terraentity/SkeletronMixin.java:14-26`——用 MixinExtras `@WrapOperation` 包住 `Skeletron.hurt`，按存活手数量改写伤害（>2 手封顶 1~2 点，1~2 手各 -45%），且**豁免 BYPASSES_INVULNERABILITY 伤害源**。骨架本体减伤这种"阶段性规则"是打在实体模块外的注入，不侵入 Boss 基类。
- 死亡延迟结算一派的归属：本模块的 KillBoard 写入发生在 vanilla `LivingDeathEvent`（即 die() 当帧），掉落靠原版 loot + **每位维度内玩家一个绑定归属的宝袋实体**（`ModUtils.java:173-181`；`TreasureBagItem.java:95-100`；`TreasureBagItemEntity.java:22-40`：`DATA_OWNER` 同步 UUID、isOwner 校验拾取、lifespan 12000、免疫爆炸、不可合并）。若 TerraEntity 内部另有"播完死亡动画再掉落"的机制，本盘无法验证——就胶水层证据看，Confluence 属于**死亡当帧结算 + 掉落物生命周期延长**一派，与 BR 的"血量钉回 0.1 再补刀"派不同。
- "参战者"概念极薄：没有 hurt 收集名单。奖励判定用的是**同维度在场即参战**（`ModUtils.java:173` 按 `player.level().dimension()==living.dimension` 过滤），成就同样发维度内全员（`BloodMoonGameEvent.onEnd:108-119` 甚至发给全服）。
- 死亡经济结算也在同函数附近：普通敌人掉落钱币由 `getLivingBaseMoneyDrops` 公式化（`ModUtils.java:200-210`：maxHealth×0.15 + 攻击×0.25 + 护甲×0.1 + 击退抗×10 倍率，乘本地难度系数，封顶 10 万），困难模式 ×1.6、世花后 ×1.5（184-195 行）——"按实体面板算钱"是无损可移植的小公式表。

### 4.6 BossBar / HUD

- 本检出**零引用** `ServerBossEvent`/BossEvent/BossBar（全树 grep 无匹配）；血条与 Boss 音乐全部在缺失的 TerraEntity/lib。本仓库能看到的相关痕迹只有 `Boss` 接口（`org.confluence.lib.api.entity.Boss`，含 `shouldShowMessage()`、`noBossInWorld()`，`LivingEntityEvents.java:127`、`BossDelaySpawner.java:109` 调用）与 README 提到的外围子项目 TheTrackers（"提供 Boss 实体实时位置提示"，README-EN_US.md 工程表）。综述第 5 条说的"ServerBossEvent+一条样式旁路"在 Confluence 上**不可复核**，标未验证。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：56 个文件、约 45 个 payload，全部在 `NetworkEvents.java:17-70` 一处注册（版本化 registrar("1")）。战斗相关只有四类：KillBoard 全表同步、GameEvent 开/关、哥布林进度、流星/风向/星相环境包。无招式/无伤害同步包——与综述第 9 条一致。**特色手法**是"无字段枚举包 + StreamCodec 直接反序列化进单例"（`KillBoardSyncPacketS2C.java:16-27`），同步语义=整库快照覆盖，永远收敛。
- 数据驱动程度：`GamePhaseLootItemCondition.java:15-35`——loot condition 带 `[from,to]` 区间谓词 Codec，运行时查 KillBoard 的 GamePhase，掉落随全局进度换表（datapack 可写）；12 种 NPC 交易锁全走注册表 `TradeLockProvider(MapCodec, drawer)`（`ModTradeLockProviderTypes.java:13-32`），其中 `ConditionsLock.java:14-27` 直接吃 `ICondition.LIST_CODEC`——**把 datapack 条件系统当交易谓词 DSL 复用**；另有每把武器/实体的无敌帧归类（代码接口）。配方（Transmutation、HeavyWorkBench 等）、DataMap、世界生成注册均在 `ModDataProvider.DATA_BUILDER`（经 datagen 落地）。
- 进度查询的第三轨：秘密旗标位掩码。`IMinecraftServer.confluence$updateSecretFlag` 把 HARDMODE/GRADUATED 等 bit 写进存档 WorldOptions（`mixed/IMinecraftServer.java:11-29`，mixin 见第 6 节），供 `SecretFlagLock` 交易锁与 `TooEasy` 种子逻辑查询；`Bestiary`（`common/data/saved/Bestiary.java:36`）是又一张 IGlobalData 表（`Map<String,BestiaryEntry>`，死亡事件 `LivingEntityEvents.java:122` 更新），并有 `BestiaryUnlockedCountLock` 把"图鉴解锁数"也变成交易门谓词——同一份全局状态被 loot 条件、交易锁、命令、mixin 四个方向复用，这是它区别于"advancement 一把梭"样本（TF）的根本形状。
- 配置：三层 ModConfigSpec——STARTUP（`StartupConfigs.java:16-27`）、COMMON（`CommonConfigs.java` 全 302 行；事件强度如 `BLOOD_MOON_EVENT_MAX_ENEMIES_BASE/PER_PLAYER/INTERVAL_FACTOR`（BloodMoonGameEvent.java:45-47 消费）、`EYE_OF_CTHULHU_NATURE_SPAWNING`、宝袋/重生时长等）、CLIENT（`ClientConfigs.java`），另有 `DragonChargePlayerConfigPacketS2C` 做服务端配置到客户端的按需下发。
- datagen：`ModDataGenerator.gatherData`（36-84 行）组织得相当工整——`DatapackBuiltinEntriesProvider` 先跑并回传 lookup 给语言/标签提供方；`CollectRecipeProvider` 把一批子 provider 聚合成一个输出任务（NPC 商店、合成、重工作台、炼药、切石、锯木、困难模式铁砧……）；中英文案各自是 codegen 大类（`ModChineseProvider` 4817 行）。产物目录 `src/generated/resources` 在 build 里接线（`ConfluenceOtherworld/build.gradle:84`）但不在盘。

## 6. Mixin

- 三个配置：`confluence.mixins.json`（主，JAVA_21，refmap）分 `mixins` 111 / `client` 75 / `server` 3 三段；`confluence.integration.citadel.mixins.json` 与 `confluence.integration.lithium.mixins.json` 各含 1 个注入且**带 MixinPlugin 条件开关**（CitadelIntegrationMixinPlugin / LithiumIntegrationMixinPlugin），另有 `@EventBusSubscriber` 无关的 40+ 个 `mixin/integration/*` 条目直接写在主配置——对 Curios/Create/Sodium/IRonsSpells/ArsNouveau 等第三方类的补丁与对缺失子模块（terraentity/terracurio）的回打。
- 与本题相关的注入点逐个说：
  - `mixin/server/MinecraftServerMixin.java:22-36`：`@Inject("<init>", TAIL)` 从世界选项恢复 `confluence$secretFlag`；`confluence$updateSecretFlag` 写回 WorldOptions——**把秘密种子/困难模式/毕业旗标存进存档生成选项**，KillBoard 进阶时调用（KillBoard.java:120,128）。
  - `mixin/world/entity/EntityMixin.java:160-188`：`confluence$initTarget` 读 KillBoard 阶段做"混变实体替换"（把源实体按 GamePhase 表转生成目标实体并移植血量比例）——进度系统直接改写实体行为。
  - `mixin/world/entity/LivingEntityMixin.java:60-92,140-147`：给 LivingEntity 塞无敌帧 map + extraInvulnerableTicks 字段并接 save/load——4.5 节免伤体系的宿主。
  - `mixin/integration/terraentity/SkeletronMixin.java:13-26`：`@WrapOperation` 拦截跨模块 Boss 的 hurt 做手数减伤（4.5 节）。
  - `mixin/server/PlayerAdvancementsMixin` / `ServerAdvancementManagerMixin` / `client...ClientAdvancementsMixin`：成就（achievement 化 advancement）展示与偏移量（`ModAchievementOffsetProvider` datagen）改造——与 Boss 进度仅弱相关。
- `mixin/world/entity/boss/enderdragon/EnderDragonMixin.java` 是本仓库唯一原版 Boss 注入（改末影龙行为以适配阶段系统，细节未逐行核对）。
- 注入密度与写法：主配置 `injectors.defaultRequire=1`（任何注入失败即崩，不留静默）；@At 最多的单文件是 `mixin/world/entity/projectile/FishingHookMixin.java`（13 个注入点）与 `LivingEntityMixin.java`（10 个）；大量使用 MixinExtras（`@WrapOperation/@ModifyExpressionValue/@WrapWithCondition`），跨模块修补（如 SkeletronMixin）全靠它。

## 7. 值得学的 5 条

1. **全局击杀板 = enum 单例 + 双 Codec(NBT/Stream) + 无字段快照包**：`common/data/saved/KillBoard.java:34-37,135-145` + `network/s2c/KillBoardSyncPacketS2C.java:16-27`。写入端每次变更 sendToAll 全表，客户端永远持有权威镜像，交易锁/掉落条件/HUD 全部本地 O(1) 查询、零增量同步 bug 面——Colossus 的 KillBoard 轨可直接抄这个"快照即协议"的形状。
2. **四值返回码的延迟召唤队列**：`common/data/saved/BossDelaySpawner.java:34-67`。`(delay, EntityType, ToIntFunction<ServerPlayer>)` 三元组，SUCCESS/CONTINUE/CANCEL/n>0=再等 n tick 把"条件未成熟→继续等"表达成数据而不是重排队代码；配合 `hasSameTypeInQueue`（69-72 行）与 KillBoard 双闸防重（83 行）。Colossus 的 BossDelaySpawner 骨架可以只换掉它的存储位置（持久化问题见结论"不该抄"第 2 条）。
3. **GamePhase→属性修饰符的数据映射 + finalizeSpawn 单点应用**：`common/data/map/GamePhase2AttributeModifiers.java:39-71`、`common/init/ModDataMaps.java:38-43`、`common/event/game/entity/LivingEntityEvents.java:455-457`。带 Codec/Merger/Remover 的注册表数据映射让"进度换代增强"完全 datapack 可编辑，应用点收敛在一个生成钩子上；Forge 1.20.1 无 DataMap，同形状可用"JSON 表 + 自己的 holder 缓存"移植。
4. **按伤害来源记名的无敌帧，且区分 STATIC/LOCAL 两类**：`mixed/Immunity.java:55-64,66-87,107-115` + `common/event/game/entity/EntityEvents.java:107-110`。原版全局 invulnerableTime 无法表达"多召唤物各自计帧、同源弹幕不许叠伤"，这套 per-cause 帧表是 BOSS 战连招判定的地基，且整套只依赖一个 mixin 字段注入。
5. **TradeLock 注册表（MapCodec + RecipeDrawer）与 ConditionsLock 复用 ICondition**：`integration/terra_entity/init/ModTradeLockProviderTypes.java:13-32`、`npc_trade_lock/ConditionsLock.java:14-27`、`AnyBossDefeatedLock.java:11-26`。进度门（"杀过任意 Boss 才卖 this"）做成可序列化、可 JEI 展示、可被数据包组合的小谓词对象——Colossus 若做 NPC/奖励门，注册"谓词类型"而不是写死 if 是正解。

## 8. 公开 API / 扩展点

`org.confluence.mod.api` 包本身即扩展点：25 个 mod 总线事件（`api/event/`——`CustomGameEventRegisterEvent`、`GameEventSpawnerDataModificationEvent`、`GameEventSyncCallbackRegisterEvent`、`ShimmerEntityTransmutationEvent`、`EnterHardmodeEvent`、bestiary 注册三件套等）+ `ITerraArrowProjectileWeaponItem` 接口 + 与游戏无关的 `lunar/` 历法库；对缺失子模块又消费其 `terraentity.api.event.*`（NPCEvent/SummonEvent/YoyosThrowingEvent，见 `TEGameEvents.java:34-60`）。扩展范式=事件化注册表注入，无注解扫描。

---

## 结论：对 Colossus 设计的输入

**可以直接借用的三条形状**（证据在上）：
1. KillBoard 的"enum 单例 + Codec/StreamCodec 成对 + 变更即全表快照包"（`KillBoard.java:34-37` 与 `KillBoardSyncPacketS2C.java:16-27`）——进度轨的同步成本被压到一行 sendToAll；
2. BossDelaySpawner 的四值谓词返回码与双闸防重（`BossDelaySpawner.java:34-72,83`）——"延迟召唤+条件复查+取消"一个函数签名讲完；
3. GamePhase2AttributeModifiers 的"阶段→属性表、finalizeSpawn 单点应用、Remover/Merger 全编解码"（`GamePhase2AttributeModifiers.java:39-71`）——进度换代的声明式做法，胜过 Cataclysm 式配置乘区。

**不该抄的三条**：
1. **把 Boss 特异性流程硬编码进全局状态突变器**：`KillBoard.defeat()` 94-98 行用 `entityType == SKELETRON/WALL_OF_FLESH` 逐 Boss 分支推阶段并顺手启动全图改造（115-133 行），而新三王/世花/月总阶段的推进又散落在缺失模块——阶段机的知识被打碎在"全局单例的 if-else + 子模块暗改"两处，addon 无法插拔新 Boss 的阶段效果。Colossus 应当是进度监听器/阶段规则表，而不是写在 setter 里。
2. **调度状态不落地 + 静默丢弃**：召唤队列是 enum 里的普通 `ArrayList`（BossDelaySpawner.java:37），无 encode/decode——服务器重启全部预约召唤蒸发；容量满时 `size()==8 → removeFirst()`（65 行）直接吃掉最早那位玩家的召唤，且谓词全员 CONTINUE 时条目在第 59 行被无条件移除（"再等等"和"作废"共用一个 int 通道，误用即丢）；`TickEvents.java:38` 又把它锁死在单一维度。Colossus 的延迟刷怪必须持久化、满队列要报错而不是换人。
3. **竞态与规模的敷衍**：自然召唤对玩家列表按序掷 `nextFloat()>=0.3333`（BossDelaySpawner.java:86-89）——先遍历到的玩家系统性吃掉概率；NPC 邻近检测用抛异常当 return（137-145 行 `ReturnException`）；主动召唤每件道具都做一次 `getAllEntities()` 全维度扫描（BossSummoningItem.java:37）。多人缩放到此为止：没有参战者名单，宝袋与成就以"同维度在场"论功（ModUtils.java:173-181）——挂机/路过即得分。这三处正是综述第 6、7 条痛点的又一实证，Colossus 的 EngagementTracker + 概率按人份独立结算 + 空间索引查重都是净差异化。

**遗留与偏差声明**：本报告无法覆盖 Boss 实体内部（招式表、阶段类、判定帧、BossBar、死亡动画延迟），因 TerraEntity/Confluence-Magic-Lib 子模块不在检出内——问题①③及②的动画派归属均标"未验证"；已交付的是该样本在"调度/进度/缩放/免伤/召唤"五个外围系统上的全部可复核事实。速览卡片的行数口径已实测修正为 183,113 行/1736 文件；卡片"主类候选"（ClientBestiaryEntry）并非入口，真实入口是 `Confluence.java`。
