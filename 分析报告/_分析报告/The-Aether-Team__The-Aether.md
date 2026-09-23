# The Aether 源码分析报告

## 1. 基本信息

- mod_id：`aether`（`gradle.properties:9`）；mod 版本 1.5.10（`gradle.properties:12`）
- 作者：AlphaMode、bconlon、Drullkus、reetam 等（`gradle.properties:18` 的 mod_authors）
- 许可证：代码 LGPL-3.0、素材 All Rights Reserved（`gradle.properties:13`；`LICENSE.txt` 第 1-2 行为 LGPL v3 头）
- 目标平台：MC 1.21.1 / NeoForge 21.1.72、loader `[4,)`（`gradle.properties:21,26,29`）。无 Forge/Fabric 分支
- 构建：`net.neoforged.moddev` 2.0.63-beta 单插件（`build.gradle:6`），非 multiloader，单一 source set（只有 `src/main`，客户端代码在 main 内以 `client/` 包与 `@OnlyIn` 隔离）；Java 21 工具链（`build.gradle:22`）
- 发布坐标：group `com.aetherteam.aether`、artifact `aether`、版本 `1.21.1-1.5.10-neoforge`（`build.gradle:15-19`）；CurseForge 255308 / Modrinth YhmgMVyu（`gradle.properties` 尾部 Publishing 段）
- 关键外部件：自研库 Nitrogen、Cumulus（菜单），前置 Accessories（wisp-forest 饰品库）（`gradle.properties:32-34`）

## 2. 源码规模与包结构

实测：`src/main/java` 下 797 个 `.java`、共 69,999 行（`find … -exec cat {} + | wc -l`）。速览卡片记 70,796 行，差异应为计数口径（行尾换行归属）不同，文件数一致。

顶层包文件数（`com/aetherteam/aether/` 下）：

| 包 | 文件数 | 包 | 文件数 |
|---|---|---|---|
| client | 168 | integration | 32 |
| item | 106 | recipe | 28 |
| entity | 71 | event | 27 |
| world | 70 | loot | 15 |
| block | 63 | inventory | 13 |
| mixin | 62 | blockentity | 13 |
| data | 55 | perk | 12 |
| network | 34 | attachment | 7 |

侧别分布（单 source set 内）：`client/` 包 168 文件 + `mixin/mixins/client/` 26 文件为纯客户端，其余 common；`network/packet` 34 文件按 clientbound(19)/serverbound(12)/双向同步(3) 分目录。

最大源文件（wc -l 实测）：`data/generators/AetherLanguageData.java` 1401、`entity/monster/dungeon/boss/SunSpirit.java` 987、`entity/passive/Moa.java` 980、`attachment/AetherPlayerAttachment.java` 969、`entity/monster/dungeon/boss/Slider.java` 954、`data/generators/AetherRecipeData.java` 890、`entity/monster/Swet.java` 885、`entity/monster/dungeon/boss/ValkyrieQueen.java` 873、`data/generators/AetherSoundData.java` 800、`client/gui/screen/perks/MoaSkinsScreen.java` 642、`Aether.java` 632、`event/hooks/EntityHooks.java` 624。

**稀疏检出的缺口**：`src/main/resources` 本地只剩 `aether.mixins.json` 与 `META-INF/accesstransformer.cfg`，`src/generated/resources`（datagen 产物：维度/群系/配方/战利品 JSON、语言文件）与 `assets` 整体缺失；`neoforge.mods.toml` 以模板形式在 `src/main/templates/META-INF/`。本报告一切关于 JSON 的结论均由 datagen 的 Java 代码反推，不臆造 JSON 文本。

## 3. 入口与注册

入口 `Aether.java:131` 构造器（`@Mod(Aether.MODID)`，注入 `ModContainer/IEventBus/Dist`）：

```java
public Aether(ModContainer mod, IEventBus bus, Dist dist) {
    bus.addListener(AetherData::dataSetup);          // datagen
    bus.addListener(this::commonSetup);
    bus.addListener(this::registerPackets);          // NeoForge payload 注册
    bus.addListener(DataPackRegistryEvent.NewRegistry.class,
        event -> event.dataPackRegistry(AetherMoaTypes.MOA_TYPE_REGISTRY_KEY, MoaType.CODEC, MoaType.CODEC));
    ...
    for (DeferredRegister<?> register : registers) register.register(bus);  // 32 个 DR，Aether.java:141-176
    this.eventSetup(bus);
    mod.registerConfig(ModConfig.Type.SERVER, AetherConfig.SERVER_SPEC);    // 四组配置 :183-186
```

`eventSetup`（`Aether.java:552-577`）把 11 个静态 Listener 类挂上 `NeoForge.EVENT_BUS`（如 `DimensionListener.listen(bus)`），每个 Listener 内部再逐个 `bus.addListener(...)`（`event/listeners/DimensionListener.java:37-49`）——"hooks 类写逻辑、listeners 类只做订阅"是本仓库的统一分层。`packSetup`（`Aether.java:310-325`）注册 10 个内置资源/数据包（复古材质、色盲、Immersive Portals 兼容、废化传送门等），全部走 `AddPackFindersEvent`。

主要事件订阅点清单（按用途）：

| 通道 | 事件 | 用途出处 |
|---|---|---|
| mod 总线 | `GatherDataEvent` | datagen 入口，`Aether.java:132` |
| mod 总线 | `RegisterPayloadHandlersEvent` | 44 个 payload，`Aether.java:216` |
| mod 总线 | `AddPackFindersEvent` | 10 个内置包，`Aether.java:310` |
| mod 总线 | `DataPackRegistryEvent.NewRegistry` / `NewRegistryEvent` | MoaType / 进度音效表，`Aether.java:138-139` |
| 游戏总线 | `PlayerTickEvent.Post` / `EntityTickEvent.Post` | 反踢计时与附件 tick，`DimensionListener.java:121`、`AetherPlayerListener.java:58` |
| 游戏总线 | `EntityTravelToDimensionEvent` / `PlayerChangedDimensionEvent` | 进出维度交接，`DimensionListener.java:103-116` |
| 游戏总线 | `LevelTickEvent.Post` / `LevelEvent.Load` | 维度时间驱动与 LevelData 替换，`DimensionListener.java:91-132` |
| 游戏总线 | `RegisterCapabilitiesEvent` / `RegisterDataMapTypesEvent` | 桶流体/宝箱物品能力、燃料数据映射，`Aether.java:270-308` |

## 4. 核心系统

### 4.1 维度注册与进入（问题①）

维度三元组 key 在 `data/resources/registries/AetherDimensions.java:23-30`（DimensionType / Level / LevelStem 同用 `aether:the_aether`）；`bootstrapDimensionType`（:32-49）逐参构造 `DimensionType`：`fixedTime` 留空（日夜由 4.4 的系统自管）、高度区间 0~256、infiniburn 复用主世界 tag、`effectsLocation = aether:the_aether`、天光底色 `0.0F`（各参数字面量即 :33-48 所示，位置语义未逐一对表原版签名）；`bootstrapLevelStem`（:51-58）组装 `NoiseBasedChunkGenerator(MultiNoiseBiomeSource, SKYLANDS 噪声)`。注册通道只有一条：`AetherRegistrySets.BUILDER`（`data/generators/AetherRegistrySets.java:15-30`）把这些 bootstrap 交给 `DatapackBuiltinEntriesProvider` 生成 JSON 随 jar 分发——运行时代码不做任何维度注册（全库 grep 无运行期 RegistrySetBuilder）。

传送门是**实现原版 `Portal` 接口的方块**，不用自定义 Teleporter：`AetherPortalBlock implements Portal`（`block/portal/AetherPortalBlock.java:42`），`entityInside` 走原版 `setAsInsidePortal`（:58-62），`getPortalDestination`（:75-86）按当前维度反查目标（目标/回程维度可由配置改写，`world/LevelUtil.java:18-32` + `AetherConfig.java:55-56`），坐标经 `DimensionType.getTeleportationScale` 换算并被世界边界裁剪（:82-83）。落点由 `AetherPortalForcer`（原版 PortalForcer 的翻版，:43-57）找最近门或现造门；玩家状态交接在 `createDimensionTransition`（:139-155）：按门矩形换算相对偏移、旋转 yaw+90°、速度向量随门轴向旋转，最后 `AetherPortalShape.findCollisionFreePosition` 防卡墙，返回 `DimensionTransition`。

**竞态处理**三件套：(a) 目标区块加载用传送门工单——复用 `DimensionTransition.PLACE_PORTAL_TICKET` 且命中已有门时 `placePortalTicket(blockpos)`（:105,115），保证目的区块在交接时不被卸载；(b) 冷却交给原版 `setPortalCooldown`（坠落路径 `mixin/mixins/common/EntityMixin.java:75`）；(c) 掉出世界反坠回主世界的路径直接 `entity.changeDimension(transition)`（EntityMixin.java:80-81），乘客/坐骑由原版 `changeDimension` 一并搬运，另用 **静态 `teleportationTimer = 500`**（:85）标记"刚传送过"，在 `DimensionHooks.travelling`（`event/hooks/DimensionHooks.java:285-297`）里持续把 `ServerGamePacketListenerImpl.aboveGroundTickCount` 归零（accessor mixin），防止反飞行踢。骑行中的 Aerbunny 在跨维度前显式移除、到场后重装（`DimensionHooks.java:265-277` + `RemountAerbunnyPacket`）。

### 4.2 玩家附件与"键名字符串"同步协议（问题③前半）

NeoForge Attachment 注册于 `attachment/AetherDataAttachments.java:13-18`（`serialize(CODEC).copyOnDeath()`）。`AetherPlayerAttachment` 实现 Nitrogen 的 `INBTSynchable`：持久字段进 `RecordCodecBuilder` CODEC（`AetherPlayerAttachment.java:145-156`，如 life_shard_count、seen_sun_spirit），瞬时字段不进 CODEC；可同步字段登记在 `Map<String, Triple<Type, Consumer<Object>, Supplier<Object>>>`（:126-141），例如 `"setJumping"`。同步包 `AetherPlayerSyncPacket` 继承 Nitrogen `SyncEntityPacket`，只携带 `(entityId, key, type, value)` 四元组（`network/packet/AetherPlayerSyncPacket.java:21-52`）。权威方向：客户端把输入标志推给服务器（`client/event/hooks/CapabilityClientHooks.java:23-32` 检测 `input.jumping` 变化后 `setSynched(..., Direction.SERVER, "setJumping", ...)`），服务器权威跑逻辑、向客户端回灌；换维度/登录时 `forceSync` 全量重放（`event/hooks/CapabilityHooks.java:67-71`、`AetherPlayerAttachment.onLogin` :189-197）。这套"注册式反射表"避免了每加一个字段手写一个包。

### 4.3 装备驱动能力（问题③后半）

飞行不是 attribute 也不是 mayfly，而是**每 tick 改速度向量**：`item/combat/abilities/armor/ValkyrieArmor.handleFlight`（:19-55）由 `ArmorAbilityListener.onEntityUpdate`（`event/listeners/abilities/ArmorAbilityListener.java:38`）在 `EntityTickEvent.Post` 调用。判定 `EquipmentUtil.hasFullValkyrieSet`（手套件受 `require_gloves` 配置影响），空中按住跳跃时 flightModifier 递增、上限 15×、52 tick 封顶（`AetherPlayerAttachment.java:103-106`），防止连点变无限飞（:37-39 注释明确"松键冻结计时器防无限飞"）；服务端权威靠 :49-52 用 accessor 清 `aboveGroundTickCount` 防踢。免疫类（坠落免疫、火焰免疫）集中在 `event/hooks/AbilityHooks.java`（如 :205-212 坠落免疫按套装判定），全部由装备状态即时求值，无持久标记。饰品能力走 Accessories 库 + `AccessoryAbilityListener`。

跨端流转要点：这套"预测"其实是反向的——客户端只上报输入布尔（isJumping/isMoving，见 4.2），抬升量完全由服务端用附件里的 flightTimer/flightModifier 计算并 `setDeltaMovement`（`ValkyrieArmor.java:46-48`），timer/modifier 本身不在 synchable 表里、纯服务端私有，客户端看到的效果全靠原版位置同步。对"灵力值"这类不想暴露给客户端的计量资源，这是一个现成的权威模板。

### 4.4 独立时间系统

天穹维度有自己的 dayTime：`AetherTimeAttachment`（挂在 Level 上，注册于 `AetherDataAttachments.java:18`）持有 `eternalDay`、自定义 `ticksPerDay` 倍率与追时逻辑（`attachment/AetherTimeAttachment.java:66-76`：把当前时刻以 3/4 天为界向目标相位每次最多 ±10 tick 缓动，避免跳变）。数据怎么表示：attachment CODEC（存盘）+ 静态缓存 `ticksPerDayMultiplier`（:26，供 mixin 在渲染/换算热路径零查表读取）。

什么时候算：`DimensionHooks.tickTime`（:201-211）每 tick 对 `effectsLocation == aether:the_aether` 的维度经 `LevelAccessor`/`ServerLevelAccessor` 两个 accessor mixin 直接改 `ServerLevelData` 的时间；`mixin/mixins/common/DimensionTypeMixin.java:18-33` 用 `ModifyVariable`/`Inject` 改写 `timeOfDay`/`moonPhase` 的 24000 常量为 `getTicksPerDay()`，客户端天空渲染同样按该值折算日月不透明度（`client/renderer/level/AetherSkyRenderEffects.java:380-394`）。

跨端如何流转：`AetherTimeSyncPacket`（bidirectional，`Aether.java:266`）在登录/换维度/重生三个节点由 `CapabilityHooks.AetherTimeHooks`（:81-101）向玩家单独同步；睡觉对齐主世界时间走 `SleepFinishedTimeEvent`（`DimensionHooks.finishSleep` :324-336），并顺手清掉该维度的雨雪循环。

### 4.5 地牢结构与 Boss（问题④的"区域"）

4 个自定义 `Structure` 子类：大型气云、青铜/白银/黄金地牢（`data/resources/registries/AetherStructures.java:59-94`），各自 `AetherStructureTypes` 注册类型、生成参数（间隔、高度带、processor 列表）全在 bootstrap Java 里，datagen 落成 structure JSON；群系准入用 tag（`AetherTags.Biomes.HAS_GOLD_DUNGEON` 等），即"往群系 tag 里加成员"就能开放/关闭某地牢分布。`SilverDungeonStructure.findGenerationPoint`（`world/structure/SilverDungeonStructure.java:63-89`）做地上/地下双高度策略，`afterPlace`（:227-234）生成后扫描本区块已存在的 Boss 实体并写入 dungeonBounds——Boss 的 AI 活动范围由结构生成期反注入，而不是实体自己找房子。Boss 触发为常规 AI/方块驱动（Slider 由地牢刷怪笼、ValkyrieQueen 由 `TriggerTrapEvent`/`ValkyrieTeleportEvent`，`event/` 包内自定义总线事件）。

### 4.6 进度闭环（问题④）

三个通道合成闭环：(1) 原版 advancement + 两个自定义 `SimpleCriterionTrigger`——`IncubationTrigger`（按物品谓词判孵化完成，`advancement/IncubationTrigger.java:18-38`）、`LoreTrigger`；JSON 侧全部由 `data/generators/AetherAdvancementData.java` datagen。(2) 非奖励型状态记在 attachment CODEC：`seen_sun_spirit`（对话解锁，`entity/monster/dungeon/boss/SunSpirit.java:277,318` 读取/置位）、`life_shard_count`（属性加成用固定 id 的 `AttributeModifier` 幂等重设，`AetherPlayerAttachment.java:938-940`，应用点 :495,508）。(3) 多人区域限制不用进度而用配置+白名单文件：Sun Altar（全服改时间）受 `sun_altar_dimensions` 列表（`AetherConfig.java:141-144`）与独立 `sun_altar_whitelist.json`（`command/SunAltarWhitelist.java:14-48`，直接复用原版 `UserWhiteList` 存储）双重门控。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`network/packet` 实测 34 个源文件（根 3 + clientbound 19 + serverbound 12），在 `Aether.java:216-268` 一处注册共 44 个 payload 类型（下行 26、上行 15、双向 3；一个文件常含 Apply/Remove/Sync 多个 TYPE，如 `ClientHaloPacket`）。registrar 声明为 `"1.0.0").optional()`（:217）——版本不匹配时静默降级不阻断连接。大头是附件同步与 perk 展示（Halo/MoaSkin/DevGlow 三件套）；区块加载不用自定义包，靠原版 portal ticket（见 4.1）。
- **数据驱动程度**：维度/群系/噪声/密度函数/配置化与放置特征/结构/structure set/processor list/damage type/唱片/数据映射 15 类 registry 全走 `RegistrySetBuilder`（`AetherRegistrySets.java:15-30`）→ 生成 JSON → 随 jar 内置 datapack；这意味着**用户可用 datapack 覆盖秘境的一切生成参数**。真正进 Java 的只有：自定义 Feature 4 个（气云层、湖、水晶岛、快速沙 shelf，`world/feature/`）、自定义 Structure 逻辑 5 个、自定义密度函数 `aether:base_3d_noise_aether` + 手写 island slide（`data/resources/builders/AetherNoiseBuilders.java:48-56`：基噪声 -0.13、`slide(0,128,72,0,-0.2,8,40,-0.1)`、squeeze）。配方走 Nitrogen 的 RecipeBuilder 家族 + `AetherRecipeData`（891 行）；战利品表 datagen 于 `data/generators/loot/`；另有 NeoForge DataMap 三个燃料表（`Aether.java:304-308`）和 MoaType 自定义 datapack registry（`Aether.java:139`）。**限流**：生成开销控制只有常规手段——放置特征里的 `RarityFilter.onAverageOnceEvery(64)`（`AetherStructures.java:90`）、地牢 structure set 间隔参数；未见额外的生成期预算/节流代码。
- **配置**：`AetherConfig.java`（437 行）四组 Spec：STARTUP/SERVER/COMMON/CLIENT。值得注意的 SERVER 项：`portal_destination/return_dimension_ID`（把传送门两端改成任意维度，:172-174）、`spawn_in_aether`（登录直接出生在秘境，`DimensionHooks.startInAether` :64-85 用安全落点搜索 :87-120）、`disable_falling_to_overworld`、`maximum_life_shards`、`require_gloves`。CLIENT 项直接驱动渲染分支：`colder_lightmap`（`AetherSkyRenderEffects.java:52`）、`green_sunset`（:91）、`disable_clouds`（:137）。COMMON 项负责兼容开关（`enable_immersive_portals_compatibility`、`use_default_accessories_menu`，`Aether.java:459,479`）。
- **datagen**：`data/AetherData.java:24-63` 一个 GatherData 入口挂 17 类 provider（语言 1401 行、材质模型、配方、战利品、进度、tag 8 类），产物提交到 `src/generated/resources`（本地缺失，见第 2 节）。

## 6. Mixin / ASM / 接口注入

`src/main/resources/aether.mixins.json`：common 34 条（含 24 个 accessor）+ client 26 条（含 15 个 accessor），另有 `AetherMixinPlugin` 条件门与 Optifine 兼容子包（`mixin/mixins/client/optifine/`）。插件本体（`mixin/AetherMixinPlugin.java:13-34`）只做一件事：`Class.forName("optifine.Installer")` 探测 OptiFine，装了就用 `optifine/BossHealthOverlayMixin` 替换原版那条同名 mixin——同一注入点的"双版本二选一"是处理渲染 mod 冲突的最小方案。代表性注入点：
- `common/DimensionTypeMixin.java:18-33`：改写 `timeOfDay/moonPhase`，把"维度一天多长"注入原版静态换算；
- `common/EntityMixin.java:36-59`：`Entity.tick` TAIL 检测掉出天穹、:68-92 完成坠落转维（见 4.1）；
- `common/PlayerMixin.java:29-37,52-65`：横扫攻击手套耐久只扣一次、骑乘时蹲下按键回放；`ServerPlayerMixin.java:15-20`：断连时清理坐骑引用；
- accessor 群：`ServerGamePacketListenerImplAccessor`（反踢保护）、`LevelAccessor`/`ServerLevelAccessor`（替换 LevelData，4.4 的根基）、`LevelRendererAccessor` + `callBuildClouds`（客户端自绘云复用原版 VBO，`AetherSkyRenderEffects.java:136-198`）。
另有 `META-INF/accesstransformer.cfg`。接口注入侧：Ability 全部是"marker interface + 事件监听里 instanceof 分派"（`item/combat/abilities/armor/*` × `ArmorAbilityListener`），不 ASM 改类。

**环境表现的接法与代价（问题⑤）**：天空/雾/云不改 `LevelRenderer`，而是注册 `DimensionSpecialEffects` 子类（`client/renderer/level/AetherRenderEffects.java:15-17` 按 `effectsLocation` 挂到维度）。代价写在脸上：`AetherSkyRenderEffects` 433 行里约 60% 是 `[CODE COPY]` 标注的原版复制（renderSky :240、renderClouds :136、LightTexture 调色 :51），原版每改一次这些私有渲染段就要人工跟随一次；且云端复用 `LevelRenderer` 的私有 VBO 字段，靠 accessor 续命。音乐不占渲染：`Musics.createGameMusic(MUSIC_AETHER)` 直接写进群系定义（`AetherBiomeBuilders.java:49`），雾色/天色同理（:41-47）。

## 7. 值得学的 5 条

1. **原版 `Portal` 接口 + `DimensionTransition` 做维度接入，零自定义 Teleporter** — `src/main/java/com/aetherteam/aether/block/portal/AetherPortalBlock.java:42,75-118`：坐标换算、速度旋转、乘客搬运、portal ticket 加载目的区块全部骑在原版实现上，进出交接只剩一个返回值。秘境做"入口任意、出口自愈"时这是最省维护的骨架。
2. **传送后反飞行踢的时间窗** — `event/hooks/DimensionHooks.java:285-297` + `item/combat/abilities/armor/ValkyrieArmor.java:49-52`：跨维度/悬浮能力必然触发原版 `aboveGroundTickCount` 踢人，用 accessor 清零 + 倒计数窗口，是 1.20.1 上同样成立的通用解。
3. **附件"方法名字符串→同步通道"注册表** — `attachment/AetherPlayerAttachment.java:126-141` 与 `client/event/hooks/CapabilityClientHooks.java:23-32`：一个 Map 声明哪些字段可跨端、什么类型，加字段不再加包；持久/瞬时字段用"进不进 CODEC"一刀切开，方向由 `Direction.SERVER/CLIENT` 表达。
4. **维度全套世界生成 = 一个 `RegistrySetBuilder` + datagen 产物** — `data/generators/AetherRegistrySets.java:15-30`：Java 里以 bootstrap 函数为唯一真源，JSON 是编译产物，玩家可用 datapack 覆写；洞天参数想做成"配置即玩法"的 mod 应照抄这个分层。
5. **DimensionSpecialEffects 覆写而非渲染 mixin 做天空盒** — `client/renderer/level/AetherSkyRenderEffects.java:240,331` + `AetherRenderEffects.java:15-17`：以"复制原版渲染段 + 微调"换取不 mixin `LevelRenderer`；配合 effectsLocation 身份判定（`DimensionHooks.java:202`），维度外观与逻辑彻底解耦。代价与收益一并见第 6 节。

## 8. 公开 API

- `api/` 包：`AetherMenus`（供外部打开其菜单）、`AetherAdvancementSoundOverrides`——自建 NeoForge registry 允许其他 mod 覆写进度音效（`Aether.java:138,168` 注册）。
- `api/registers/MoaType`：datapack registry 类型（`Aether.java:139`），第三方加 Moa 皮肤只需 JSON。
- `integration/`：Jade/REI/JEI 只读兼容；内置 Immersive Portals 兼容 datapack（`Aether.java:458-472`）是"按 `ModList.isLoaded` + 配置开关注入覆写包"的干净范例。
- 自定义事件面：`event/` 包内 `BossFightEvent`、`PlacementBanEvent`、`ItemUseConvertEvent` 等经 `AetherEventDispatch` 派发，可供第三方监听。

---

### 给「求仙问道」秘境/洞天福地的 3 条可搬做法

1. **入口方块实现原版传送门框架、出口坐标带"世界边界裁剪 + 安全落点搜索"**：搬 `AetherPortalBlock.getPortalDestination`（:75-86）与 `DimensionHooks.checkPositionsForInitialSpawn`（:87-120）。**版本耦合点**：`DimensionTransition`/`Portal#getPortalDestination` 是 1.20.2+ 才有；1.20.1 Forge 需退回 `Block.getTeleporter` 时代——自己实现 `Teleporter` 接口并借 Forge `PlacePortalUtil` 事件造出口，portal ticket 用 `TicketType.PORTAL` 手动加，速度/旋转换算那段数学可以直接照搬（它与 API 形态无关）。
2. **秘境维度所有生成参数进一个 RegistrySetBuilder、由 datagen 落成内置 datapack**（做法 4 的 :15-30 模式）。1.20.1 Forge 上对应物是 `DataPackRegistryEvent.NewRegistry` + 手放 `data/<mod>/dimension|worldgen/**` JSON；注意 1.20.1 的 `dimension_type` JSON 无 `gravity`/`temperature` 之外的新字段差异不大，但 `minecraft_version` 的 pack format 与 1.21 的 `RegistrySetBuilder` 依赖的 `BootstrapContext` API 不同，datagen 代码不可直接复制，只能复制"单一真源"的分层。
3. **授予飞行/灵力：服务端权威 + "每 tick 增量式能力" + 反踢时间窗**：`ValkyrieArmor.handleFlight`（:19-55）证明不需要碰 `Abilities.mayfly` 就能做"灵力滑翔"，且天然防白嫖（落地重置、按键冻结）。1.20.1 Forge 对应存储用 `IAttachmentType`（47.x 后期版本已引入，需按所用 Forge 构建核实；若缺失则退回 capability + 手写 sync）；`aboveGroundTickCount` 清零那手（值得学第 2 条）在 1.20.1 同样可行，字段名未变。

**做坏了的 1 处**：`src/main/java/com/aetherteam/aether/data/resources/builders/AetherBiomeBuilders.java:155` — 多噪声群系表的最后一个条目写的是 `temps5`（温度 0.93-0.94），而它已被 :148 的 `temps5 ×湿度(-0.3..1.0)→SKYROOT_FOREST` 完整遮蔽，从上下文（:153 的 temps6 行）看本应是 `temps6 ×(0.8..1.0)`。结果是这条 WOODLAND/FOREST 边界规则永不生效、高温高湿角落靠 MultiNoise 的最近邻兜底——一行复制粘贴错误直接改变群系分布，且纯看 JSON 几乎不可能发现；数据驱动程度越高，越要给这类参数表配"条目可达性"单测。另一处小气味：`event/hooks/DimensionHooks.java:54` 的 `teleportationTimer` 是服务器级静态量，两名玩家先后坠落时窗口互相吞占（只影响反踢宽限，不致错传送）。

### 交付说明

- 做了什么：通读入口/维度/传送门/附件/能力/结构/datagen/mixin 共约 20 个源文件并逐条给出行号；实测 .java 797 个、69,999 行（卡片 70,796 为口径差）。
- 遗留：本地检出缺 `assets` 与 `src/generated/resources`，故进度 JSON、配方 JSON、维度 JSON 的实际文本未能回读（报告已声明只依据 datagen Java 反推）。
- 设计偏差：无——按 8 节结构完成，第 8 节因确存在跨 mod 接口而未省略。
