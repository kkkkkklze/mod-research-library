# Paraglider 源码分析报告

## 1. 基本信息

- mod_id：`paraglider`（出处：`forge/src/main/resources/META-INF/mods.toml` 中 `modId="paraglider"`；`common/src/main/java/tictim/paraglider/api/ParagliderAPI.java:19`）
- 作者：Tictim；许可证：GPLv3（`mods.toml` 头部 `license="GNU General Public License version 3 (GPLv3)"`）
- 目标 MC 与加载器：`gradle.properties` 钉死 `minecraft_version=1.20.1`、`forge_version=1.20.1-47.1.3`、`fabric_loader_version=0.14.22`、`fabric_api_version=0.87.0+1.20.1`，mod 版本 `20.1.4`。上游仓库对多条 MC 版本线各开分支发布，**本检出是 1.20.1 这条线**（Architectury 双平台同发 Fabric + Forge）。
- Gradle 插件与工程结构：根 `build.gradle` 使用 `architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.1-SNAPSHOT`，Moja­ng mappings + Parchment `2023.08.20`；`settings.gradle` 含 `common / fabric / forge` 三子模块（速览卡片写 "single" 不准确，实为多模块）。Java 版本 17（根 `build.gradle` `options.release = 17`）。
- 依赖 Forge 侧配置走 `forgeconfigapiport`（`common/build.gradle`），使 common 层能共用一套 ForgeConfigSpec 定义。

## 2. 源码规模与包结构

实测（`find -name "*.java" | wc -l` 与逐文件 `wc -l` 求和）：**207 个 .java、15,789 行**（卡片记 15,996，为计数口径差异，含末尾无换行文件的统计差）。模块分布：common 134、fabric 39、forge 34。

common 主要包及文件数：`api` 30（对外接口/插件契约）、`contents` 22（物品/配方/村民/世界生成）、`impl` 19（movement 12 + stamina 5 + vessel 2 + …）、`network` 19（message 子包 12）、`client` 12、`bargain` 11、`config` 7、`mixin` 4、`wind` 4、`plugin` 3、`command` 1、顶层 2（`ParagliderMod.java`、`ParagliderUtils.java`）。

Mixin 总量：common 4 + fabric 7 = 11 个（forge 0，全部走事件），详见第 6 节。

最大 12 个源文件（行数为本次 `wc -l` 实测）：

| 文件 | 行 |
|---|---|
| `common/.../client/screen/BargainScreen.java` | 511 |
| `common/.../impl/movement/PlayerStateMapLoader.java` | 440 |
| `common/.../ParagliderUtils.java` | 374 |
| `common/.../command/ParagliderCommands.java` | 304 |
| `common/.../impl/movement/ServerPlayerMovement.java` | 274 |
| `common/.../api/movement/MovementPlugin.java` | 265 |
| `common/.../contents/recipe/SimpleBargain.java` | 259 |
| `common/.../client/render/StaminaWheelRenderer.java` | 246 |
| `common/.../contents/recipe/SimpleBargainSerializer.java` | 241 |
| `forge/.../contents/ForgeContents.java` | 230 |
| `common/.../wind/Wind.java` | 229 |
| `common/.../client/screen/ParagliderSettingScreen.java` | 216 |

**稀疏检出提示**：本检出缺全部 assets 与绝大部分 resources JSON——common 的 `src/main/resources` 只有 `paraglider.mixins.json` 与 `paraglider.accesswidener`，fabric 侧缺 `fabric.mod.json`，配方/战利品/ advancement JSON 均不在树中（datagen 源码在，产物不在）。下文所有断言只依据 Java 源码，未引用任何缺失 JSON。

## 3. 入口与注册

双平台各一个入口，公共逻辑收敛到抽象类 `ParagliderMod`（单例自检，`ParagliderMod.java:32-35`）。Forge 入口用 `DistExecutor.unsafeRunForDist` 分 CLIENT/COMMON 代理（`forge/.../ForgeParagliderMod.java:35-38`）；Fabric 入口在 `onInitialize` 里集中登记内容、事件与命令：

```java
// fabric/.../FabricParagliderMod.java:100-110（节选）
AttackBlockCallback.EVENT.register((p, l, h, b, d) -> ParagliderEventHandler.beforeInteraction(p));
UseItemCallback.EVENT.register((p, l, h) -> ParagliderEventHandler.beforeUseItem(p, h));
ServerPlayerEvents.COPY_FROM.register(ParagliderEventHandler::onPlayerCopy);
EntityTrackingEvents.START_TRACKING.register(ParagliderEventHandler::onStartTracking);
ServerPlayConnectionEvents.JOIN.register((l, p, s) -> ParagliderEventHandler.onLogin(l));
```

注册方式差异：Forge 侧 `@Mod.EventBusSubscriber` 静态订阅（`forge/.../event/ParagliderEventHandler.java:28`）+ `AttachCapabilitiesEvent` 挂能力（同文件 :73-77）+ `TickEvent.PlayerTickEvent` END 相位驱动 `PlayerMovement.update()`（:79-84）；Fabric 侧因无事件总线，改为 `MixinPlayer.tick()` RETURN 处直接调 `update()` 并用 `@Unique` 字段存能力对象。第三方扩展点用注解发现：`@ParagliderPlugin` 标注的类经 `ModList.get().getAllScanData()` 的 ASM 扫描数据加载（`forge/.../ForgeParagliderPluginLoader.java:58-68`）。

跨平台抽象机制：common 对平台差异函数用 Architectury `@ExpectPlatform`（`ParagliderUtils.java:321-366`，共 9 个：水下呼吸判定、BlockMatcher 的 tag 查询、KeyMapping 取键等），fabric/forge 各提供 `ParagliderUtilsImpl`；能力存取则整层分叉——Forge 走真 capability，Fabric 走 mixin `@Unique` 字段（见第 6 节）。命令 `paraglider` 含 `reloadPlayerStates`（`ParagliderCommands.java:126-129,167`）。

## 4. 核心系统

1. **玩家状态机（movement）**。
   - 数据表示：`PlayerState` = 不可变记录（id + flags 集合 + staminaDelta + recoveryDelay，`api/movement/PlayerState.java:20-60`）；状态间转移边存成 `PlayerStateConnectionMap`（每个 parent 一条按 priority 降序排好的分支表 + fallback，`impl/movement/PlayerStateConnectionMap.java:19-61`）。
   - 计算时机：**只在服务端**、每 tick 在 `ServerPlayerMovement.update()` 里从 IDLE 根节点重走一遍决策树（:108-113）。
   - 跨端流转：算出的新状态若与上 tick 不同则打 `movementChanged` 脏标（:121），随 SyncMovementMsg 把**状态 id（ResourceLocation）**发给客户端；客户端 `RemotePlayerMovement.syncMovement` 用本地缓存的 stateMap 把 id 解析回对象（`impl/movement/RemotePlayerMovement.java:29-40`）。
2. **能力承载（PlayerMovement）**。
   - 每个玩家一个 `PlayerMovement`（抽象基类，持 Stamina + VesselContainer + 当前 state + recoveryDelay，`impl/movement/PlayerMovement.java:21-66`），三个子类：`ServerPlayerMovement`（权威计算+持久化+发包）、`ClientPlayerMovement`（本地玩家，执行运动学副作用）、`RemotePlayerMovement`（其他玩家，只接收状态）。
   - 默认状态集与转移条件由 `ParagliderDefaultPlugin` 以代码注册（`plugin/ParagliderDefaultPlugin.java:22-61`）：IDLE→PARAGLIDING 的条件是 `有体力 && !onGround && !isFallFlying && 主手是完好的 Paraglider`（:45-51）——注意**没有按键检查**，空中持伞即开伞。
   - 退出/panic 边界用自维护的 `accumulatedFallDistance ≥ 1.45`（`PlayerMovementValues.java:10`；`ServerPlayerMovement.java:105-106` 注释明说原版 fallDistance 会被其它 mod 覆写所以自己记）。入水/进载具/创造飞行等边界由更高优先级分支抢占：FLYING(7)→ON_VEHICLE(6)→SWIMMING(5)→UNDERWATER(4)→PARAGLIDING(3)（`ParagliderDefaultPlugin.java:37-40`）。
3. **体力与容器（stamina/vessel）**。
   - `BotWStamina.update()` 每 tick 在服务端按 `state.staminaDelta()`（经 staminaReductionLogic 修正，`ServerPlayerMovement.java:115-119`）增减体力；负 delta 后进入 recoveryDelay 冷却（`impl/stamina/BotWStamina.java:42-56`）。
   - "升级等级"即容器数：`SimpleVesselContainer` 存 heartContainer/staminaVessel/essence 三个 int（`impl/vessel/SimpleVesselContainer.java:21-23,159-171`），心容器数换算成 MAX_HEALTH 的 AttributeModifier（`ServerPlayerMovement.java:83-99`，UUID 常量在 `PlayerMovementValues.java:9`）。体力工厂可被 StaminaPlugin 整体替换（`api/ParagliderAPI.java` 的 `staminaFactory`）。
4. **风（wind，上升气流）**。
   - 服务端按区块维护 `WindChunk` 节点链，仅对"主手持伞玩家"每 4 个 gametime 放置一次风（`wind/WindUtils.java:29-37`），脏区块才广播（:41-51）；客户端按 `windParticleFrequency` 撒烟花粒子（:63-93）。
   - 持伞进入风区触发 PARAGLIDING→ASCENDING 分支（`ParagliderDefaultPlugin.java:54-56`），ASCENDING 带 FLAG_ASCENDING，由 `PlayerMovement.applyMovement` 把 y 速度抬到 +0.25（:96-98）。
5. **持久化与死亡/换维保全**。
   - 数据全部内聚在 ServerPlayerMovement 的一个 CompoundTag（stamina 子 tag + vessels 子 tag + recoveryDelay + panic 状态，`ServerPlayerMovement.java:261-273`），并带旧档兼容读取（:233-252）。
   - Forge：能力实现 `ICapabilitySerializable` 随玩家存档落盘（`forge/.../capability/PlayerMovementProvider.java:47-62`）；死亡走 `PlayerEvent.Clone`——先 `original.reviveCaps()` 取旧数据 `copyFrom`，死亡时体力回满、容器保留（`forge/.../event/ParagliderEventHandler.java:55-69`）。
   - 换维度：`PlayerChangedDimensionEvent`（Forge）/ `triggerDimensionChangeTriggers`（Fabric mixin）只打 `markForSync` 脏标，下一 tick 由 update 尾部全量重发（`forge/.../event/ParagliderEventHandler.java:92-97`；`fabric/.../mixin/MixinServerPlayer.java:22-27`；消费点 `ServerPlayerMovement.java:79-80,132-153`）。
   - Fabric 存档：`addAdditionalSaveData/readAdditionalSaveData` mixin 读写 `paraglider_player_movement` 键（`fabric/.../mixin/MixinPlayer.java:22,38-50`）。
6. **bargain（以物易物 NPC）系统**：自定义序列化器 `SimpleBargainSerializer` 作为 JSON 配方加载、目录/对话/结算共 5 种包（见第 5 节），与移动系统正交，此处不展开。

输入与状态机小结（对应第 3 问）：本 mod **没有滑翔按键**——全树唯一的 KeyMapping 是设置界面键（`ParagliderMod.java:56`，其触发见 `fabric/.../mixin/MixinMinecraft.java:24-41` 对 CTRL+P 碰撞的绕行）。"输入"实际是持续事实集合：主手持伞（物品栏）、`!onGround`、体力是否够（`canDoParagliding` 形参，`ServerPlayerMovement.java:109-113`），服务端每 tick 重放决策树得出状态，因此进入无事件、退出也无事件——边界情况全部表达为转移边（入水→SWIMMING/UNDERWATER、上载具→ON_VEHICLE、体力耗尽→PANIC_PARAGLIDING，`ParagliderDefaultPlugin.java:37-57`）；落地靠 `accumulatedFallDistance` 归零（`ServerPlayerMovement.java:105`）自然掉回 IDLE。

## 5. 网络 / 数据驱动 / 配置 / datagen

自定义包：单 channel `paraglider:master`，协议版本串握手 `"2.0"`（`forge/.../ForgeParagliderNetwork.java:35,44-45`），11 个消息（`common/.../network/message/`）：移动相关 4 个（SyncPlayerStateMap/SyncMovement/SyncRemoteMovement/SyncVessel）、bargain 5 个、wind 1 个。

节流与同步粒度（对应第 5 问）：
- `SyncMovementMsg` 载荷只有 5 个字段（state id + int + bool + varint + double，`SyncMovementMsg.java:7-13`），约 30 字节；发送全走脏标——稳态 0 包，见 `ServerPlayerMovement.java:132-140`。
- 其他玩家的状态只在开始追踪时发一次 `SyncRemoteMovementMsg`（`forge/.../event/ParagliderEventHandler.java:86-90`），之后仅当该玩家服务端状态变化时经 `syncRemoteMovement` 广播给追踪者。
- 状态表 `PlayerStateMap` 整体可序列化下发（`impl/movement/PlayerStateMap.java:22-25,67-71`），只在登录和热重载时发（`forge/.../event/ParagliderEventHandler.java:104-108`；fabric 端 `syncStateMapToAll` 挂在 reload 回调 `FabricParagliderMod.java:88-92`）。
- 风数据：每区块只在"变脏"时广播（`wind/WindUtils.java:41-51`），加玩家进区块时补发一次（Forge `ChunkWatchEvent.Watch`，`forge/.../event/WindEventHandler.java:50-58`；Fabric `MixinChunkMap.playerLoadedChunk`，`fabric/.../mixin/MixinChunkMap.java:24-33`）。
- 方向性：移动/风 5 包全部 PLAY_TO_CLIENT，客户端唯一的 C2S 是 bargain 交互两包（`ForgeParagliderNetwork.java:48-126` 的 NetworkDirection 声明）——移动系统对客户端是只读广播，这本身就是反作弊面收敛。

数据驱动程度**中等偏低**：状态、转移条件、优先级全是 Java lambda（`ParagliderDefaultPlugin.java:36-61`），配置只允许调每个状态的 `staminaDelta` 与 `recoveryDelay` 两个数——但做法漂亮：把注册后状态表反射成 `paraglider-player-states.toml` 每状态一节，改完 `/paraglider reloadPlayerStates` 在 `Util.ioPool()` 异步读回、主线程应用并广播（`config/PlayerStateMapConfig.java:38-81,110-143`）。bargain 配方是全 JSON 自定义 RecipeSerializer；风的火源方块用配置字符串（block id / `#tag` / `prop=value`）解析成 BlockMatcher（`config/Cfg.java:29-35`）。

配置粒度：三份 spec——
- `Cfg`：可玩性数值，COMMON 类型随服同步（`forge/.../config/ForgeCommonConfig.java:8-10`），覆盖滑翔速度倍率、耐久（默认 0=关，`LocalConfig.java:60-61`）、心容器/体力上限、跑步/滑翔是否耗体力、TotW 兼容枚举等约 17 项（`config/Cfg.java:11-160`）。
- `FeatureCfg`/`DebugCfg`：功能开关与调试（`common/.../config/`）。
- `ParagliderClientSettings`：纯客户端——体力轮位置、风粒子频率、设置界面键位。

datagen：两平台各一套 `src/dataGen/java`（fabric 8 文件 + builder、forge 9 文件），生成配方/战利品/标签/进度/bargain 类型（如 `forge/src/dataGen/java/datagen/LootModifierProvider.java:30-36` 写 TotW 箱子注入）；产物 JSON 未包含在本检出。

## 6. Mixin / ASM / 接口注入

**没有字节码级 ASM 变换**（Forge 侧的 ASM 只用于读取其它 mod 的 `@ParagliderPlugin` 注解扫描结果）。Mixin 共 **11 个**，按目的归类：

- 接管玩家移动（1 个，common）：`mixin/MixinPlayer.java:16-37`——注入 `Player#getFlyingSpeed()F`，定位在方法体内**第 2 处** `isSprinting()` 调用之前（`@At(value="INVOKE", target="…Player.isSprinting()Z", ordinal=1, shift=BY, by=-1)`），当状态含 FLAG_PARAGLIDING 时以 `cancellable=true` 直接返回 `0.025999999F × paraglidingSpeed`，把原版为"冲刺时空中/飞行加速"供的常数改写成滑翔速度系数。关键事实：**本 mod 完全不 mixin `travel`/`move`/`travelInAir`**（全树 grep 无此类目标，`Player#abilities.flying` 从不被置位，grep 仅 `ParagliderDefaultPlugin.java:37` 读到它），滑翔运动学靠三个"薄"注入点合成：① 本 mixin 改水平加速度常数；② tick 尾 `applyMovement` 每 tick 把 y 速度钳到 -0.05（下落限速）/抬到 +0.25（上升气流），并把 `fallDistance` 清零防摔落伤害（`impl/movement/PlayerMovement.java:90-101`）；③ 客户端把 `setSprinting(paragliding)` 置真蹭原版空中冲刺控制（`ClientPlayerMovement.java:38-40`）。体力耗尽时反向钳制：关冲刺、关游泳（:35-37）。
- 能力/存档承载（仅 Fabric，1 个）：`fabric/mixin/MixinPlayer.java`——tick 驱动 update + 存档读写（无 Fabric capability 系统的兜底）。换维重同步（1 个）：`MixinServerPlayer.java`。
- 防误判（配合移动，2 处代码 + 1 个 AW）：服务端滑翔每 tick 把 `ServerPlayer.connection.aboveGroundTickCount = 0`，防原版"飞行时间过长"踢人（`ServerPlayerMovement.java:166-175`）；该字段在 `paraglider.accesswidener` 里被 accessible（AW 另两处开放 `StructureTemplatePool` 私有字段用于村庄交易站结构注入）。
- 表现层（5 个）：`MixinPlayerModel.java:23-45`（读主手物品 `Paragliding` NBT 摆双臂/并腿姿势——注意它读的是 `ServerPlayerMovement.java:158-163` 每 tick 回写到 ItemStack 上的标记，靠原版物品同步自然流转，零额外包）；fabric `MixinItemInHandRenderer.java:18`（滑翔时不渲染手）、`MixinGui.java:15`（准星）、`MixinDebugScreenOverlay.java:20-21`（F3 调试行）、`MixinMinecraft.java:24-52`（设置键绕过与 Wind level 注册）。
- 奖励注入（2 个）：`MixinDragonFightManager.java:29` 与 `MixinRaid.java:31-36`——精确卡在 `EndDragonFight#setDragonKilled` 的 `dragonKilled` PUTFIELD 后与 `Raid#tick` 写 status 字段后的 `@Slice` 区间，掉落心容器/体力容器。

对第 4 问（与其他 mod 兼容）的直接回答：
- 仓库内**没有**针对 Sodium/Iris 的任何处理（全树 grep 无命中）——正因为不 mixin 渲染管线、不动 travel，才敢这么躺平；唯一渲染侧定制是玩家模型/手持这两处低风险注入。
- 首人称手臂/手持：取消 Forge `RenderHandEvent`（副手整只手，`forge/.../event/ParagliderClientEventHandler.java:28-35`）与 Fabric `MixinItemInHandRenderer.evaluateWhichHandsToRender` 双实现；方块高亮与点击也在滑翔时禁掉（同文件 :63-83）。
- 与其他移动 mod 的冲突点：双方都改 `getFlyingSpeed`/冲刺标志时优先级不明（本 mod 的 mixin 用 `ordinal=1` 这种脆弱定位，上游重构即崩）；fallDistance 被覆写问题的防御是服务端自记 `accumulatedFallDistance`（`ServerPlayerMovement.java:49-53`）。
- 对其它 mod 改状态表开放了 `ConflictResolver`：默认插件在"修改/连接"类动作上返回 ABORT，把解释权让给后来者（`ParagliderDefaultPlugin.java:63-70`）。
- 交互打断：滑翔中取消一切使用/攻击（Forge `ParagliderEventHandler.java:32-52`；Fabric 五个回调 `FabricParagliderMod.java:104-108`），这同时是"入水/被击"等边界外唯一的状态保持手段。

## 7. 值得学的 5 条

1. **服务端每 tick 从 IDLE 根重走状态树，客户端只收状态 id**。`common/.../impl/movement/PlayerStateConnectionMap.java:30-61` + `ServerPlayerMovement.java:108-113`。
   值得抄：转移条件（离地、主手物品、体力）全部用服务端可见事实评估，作弊客户端没有"申请进入滑翔"的通道，跨端同步从"同步意图"降级成"同步结论"，一个 ResourceLocation 就够。
2. **三面脏标合并发包**。`ServerPlayerMovement.java:29-31,117-121,132-153,208-231`：`movementChanged/heartContainerChanged/staminaVesselChanged` + 事件触发的 `markForSync()`（换维、登录）在 update 尾部统一消费，稳态 0 包、状态变更 1 个 ~30 字节包、容器变更才发 vessel 包。
   值得抄：把"什么值得同步"做成显式脏位而不是每 tick 广播。
3. **不接管 travel，用"加速度常数 + 速度钳 + 原版 sprint"合成飞行手感**。`mixin/MixinPlayer.java:16-37`、`PlayerMovement.java:90-101`、`ClientPlayerMovement.java:30-45`。
   值得抄：与渲染引擎/服务端版本解耦（这也是它不需要 Sodium 适配的原因），御剑飞行只需要把 -0.05 钳换成沿剑矢量的推进。
4. **注册期数据 + 运行期配置的两段式**。`PlayerStateMapLoader.java:39-91`（收集→冲突消解→priority 排序→回环检测，:393-419 三态着色法查 fallback 环）+ `PlayerStateMapConfig.java:38-81`（把加载完的状态表反射成 TOML 每状态一节）。
   值得抄：数值可配置但条件留在代码，配置面小而全，重载走 `/paraglider reloadPlayerStates` + `Util.ioPool()` 异步回主线程（:138-143）。
5. **旧档兼容的读取分支**。`ServerPlayerMovement.java:233-252`：检测字段类型决定按 v1 平铺字段还是 v2 子 tag 解析（还顺手修了 `essence`→`essences` 的历史拼写）。
   值得抄：能力数据格式演进必带这一手，别赌"没人从旧版本直升"。

## 8. Public API

以下先列扩展面，末尾的"结论"段是给「求仙问道」的落地形状（含做坏了的一处）。

`common/src/main/java/tictim/paraglider/api/` 是正式的对外扩展面（速览卡片目录特征里的 "API"）：

- 静态访问器：`Movement.get(player)` / `Stamina.get` / `VesselContainer.get`（`api/movement/Movement.java:18-20`，供应商函数由 mod 自身在 `ParagliderAPI.java:26-30` 注入），第三方在任何事件里可读写玩家状态与容器。
- `MovementPlugin`（`api/movement/MovementPlugin.java:20-265`）：注册新状态/合成状态、改 staminaDelta 与 flags、增删转移分支与 fallback、注册体力衰减逻辑，配 `ConflictResolver`（`api/plugin/ConflictResolver.java:1-89`）显式仲裁双改冲突；发现机制为 `@ParagliderPlugin` 注解 + 加载器（Forge 走 mod 扫描数据，`ForgeParagliderPluginLoader.java:58-76`）。
- `StaminaPlugin`/`StaminaFactory`：可整体替换体力系统实现（默认 `BotWStamina`）。
- `api/item/Paraglider.java`：第三方伞具物品只需实现该接口（耐久判定/状态标记回写），默认插件条件里的 `mainHand instanceof Paraglider` 即接口判定（`ParagliderDefaultPlugin.java:49-50`）。
- `api/bargain/`：`Bargain`/`BargainResult`/预览接口，允许别的 mod 注册自定义以物易物类型。

### 结论：给「求仙问道」御剑飞行/凌空行走的形状（Forge 1.20.1）

1. **照搬状态机骨架**：一个服务端权威 `PlayerSwordFlightState`（枚举或 id 集合均可）+ 转移表（ground→takeoff→cruising→landing，被打断=受击/入水/进载具各占一条高优先级出边）+ 每 tick 服务端重估、C→S 只回传状态 id。抄 `PlayerStateConnectionMap.java:30-61` 与三脏标发包（`ServerPlayerMovement.java:132-153`）。1.20.1 差异注意：Forge 47 用 `TickEvent.PlayerTickEvent` END 相位即可，不需要 Neo 的 `PlayerTickEvent` 新命名。
2. **照搬"薄接管"运动学**：不 mixin `travel`；tick 尾钳 deltaMovement（巡航=水平加速上限 + 垂直限速/抬升，一个 `applyMovement` 搞定，`PlayerMovement.java:90-101`），配合一个 `getFlyingSpeed` 式加速度常数注入；同时预置 `aboveGroundTickCount=0` 防踢（`ServerPlayerMovement.java:170`）与自记 fallDistance（:105-106）——凌空行走落地伤害判定直接用后者，别信 `fallDistance`。1.20.1 差异：`aboveGroundTickCount` 需 AT/access transformer（Forge 侧 `AccessTransformer` 对应它的 AW 用法）；mixin ordinal 定位脆弱，1.20.1 官方映射里 `getFlyingSpeed` 结构可钉死。
3. **照搬持久化容器**：单一 per-player 对象聚合 能力等级/灵力值/冷却，Forge 1.20.1 用 `AttachCapabilitiesEvent<Entity>` + `ICapabilitySerializable`（`PlayerMovementProvider.java:47-62`），死亡保全用 `PlayerEvent.Clone` + `reviveCaps()/invalidateCaps()`（`forge/.../ParagliderEventHandler.java:55-69`）——注意这套在 NeoForge 1.21（新星殖民地/Colossus 侧）已整体换成 Data Attachments + `PlayerCloneEvent`，两平台要写两份胶水，状态机本身放 common 不动。

**做坏了的一处**：`common/src/main/java/tictim/paraglider/config/LocalConfig.java:66-67`——`witherDropsVessel` 的配置键被复制粘贴成了 `"enderDragonDropsVessel"`，两个开关读写同一键：改任一值都会连带改变另一行为（wither 掉落实际由龙掉落键控制）。同文件旁证还有 `Cfg.java:174` 的 `if(maxStaminaVessels<=staminaVessels) maxStamina();`——调用结果被丢弃的无意义语句。教训：配置键与状态分支要有"定义处即断言"的防复制粘贴纪律（例如键名由字段名派生）。

（交付说明：三问中"getFlyingSpeed 在原版 1.20.1 travel 链路里的确切调用方"未在本检出内验证——外部源码拉取失败，报告仅陈述 mixin 自身的定位与效果，不引申原版行号。）
