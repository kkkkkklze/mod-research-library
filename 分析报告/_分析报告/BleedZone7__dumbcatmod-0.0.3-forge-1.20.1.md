# BleedZone7（dumbcatmod 0.0.3）反编译分析报告

> 分析对象：`~/Downloads\BleedZone7-0.0.3-forge-1.20.1.jar`（5.1 MB / 2226 条目 / 718 个 class）
> 反编译产物（已并入源码库）：`源码库\_参考仓库\BleedZone7__dumbcatmod-0.0.3\`（493 个 .java，已做 SRG→官方名还原）
> 方法：CFR 0.152 反编译 + 本地 NFRT `officialToSrg.tsrg` 反转重映射（12,453 个方法名 / 3,592 个字段名，389 个文件被改写）
> 说明：本报告所有 `文件:行` 引用均指向上述产物；本 mod 无公开源码仓库（`displayURL` 指向 mcreator.net），故为反编译分析。

---

## 1. 基本信息

| 项 | 值 |
|---|---|
| mod_id / 显示名 | `dumbcatmod` / **Bleed Zone 7**（中文语境：七号区，`key.categories.dumbcatmod = 七号区`） |
| 版本 | 0.0.3 |
| 目标 | Minecraft **1.20.1** / **Forge**（`loaderVersion="[47,)"`） |
| 作者工具链 | **MCreator 生成**（`credits="Created using mod maker MCreator"`，`displayURL="https://mcreator.net"`） |
| 许可证 | Academic Free License v3.0 |
| 硬依赖 | `geckolib [4.4,)`、`curios [5,)`、`patchouli [1.20.1-84,)`、`particlestorm [1.3,)`（ParticleStorm 数据包粒子） |
| 内嵌库 | `META-INF/jarjar/mixinextras-forge-0.5.0.jar`（jarJar 打包；**在可见代码中未见直接使用**，应为依赖链或预留） |
| 包结构 | 全部位于 `net.mcreator.dumbcatmod`（MCreator 惯例），含 `init/`(18) `procedures/`(23) `item/`(90) `block/`(38) `entity/`(24+ai 19) `network/`(7) + **手写模块 `custom/`(≈350 类) 与 `client/`(≈120 类)** |

**一句话定性**：这是一个"MCreator 打底 + 大量手写子系统"的**修仙/硬核生存整合向 mod**——修炼境界、武器品阶与技能、尸潮守卫战、抽卡、工业机器（拆解机/车床/矿机）、Boss（暴君熊/镜中蛇），并自研了**玩家动画引擎（dcanim）**与**特效引擎（dcvfx）**，内置**性能剖析器与 LOD**。

---

## 2. 内容规模（从 jar 资源与语言文件实测）

| 类别 | 数量 | 说明 |
|---|---|---|
| 语言词条 | **921** | 前缀分布：`msg`143 / `item`136 / `gui`118 / `tip`111 / `advancements`84 / **`zhanfa`(战法)75** / `block`49 / `dao`(道)30 / **`realm`(境界)29** / `book`28 / `xinshu`(心术)12 |
| 贴图 | 520 | — |
| 模型 | 239（+ blockstates 50） | — |
| GeckoLib 资源 | **geo 48 + animations 20** | 用于实体/方块动画（动画文件名如 `jzsshenti_1/2/3`、`xuemi`、`shizhui`） |
| 自研 dcanim 资源 | **geo 6 + animations 13** | 6 把武器 × (模型 + 一人称动画 + 三人称动画) + debug 组 |
| 帕秋莉手册 | **144 页 json + 3 本书** | 新手手册《七号区生存手册》 |
| 配方 / 进度 / 战利品表 | 69 / 64 / 55 | — |
| 世界生成 | 38（含 3 个 structure、18 个 biome_modifier） | — |
| Curios 槽位 | 6 类（`ring`/`necklace`/`belt`/`glow`/`jianxia`(剑匣)/`yuqi`(玉器)） | — |
| 自定义粒子 | 7 + 4 `particle_definitions`（ParticleStorm） | — |

修炼系统内容（`realm.dumbcatmod.*` 29 条）对应 **10 大境界**枚举：`始量 → 刻恨 → 灵海 → 玉海 → 玉界 → 起源 → 元始 → 真株 → 封神 → 创世`（`custom/xiulian/Realm.java:13-22`）。

---

## 3. 入口与注册

**主类** `net.mcreator.dumbcatmod.DumbcatmodMod`（典型的 MCreator 骨架 + 手写扩展）：

```java
@Mod("dumbcatmod")
public class DumbcatmodMod {
    public static final SimpleChannel PACKET_HANDLER = NetworkRegistry.newSimpleChannel(
        new ResourceLocation("dumbcatmod", "dumbcatmod"), () -> "1", "1"::equals, "1"::equals);  // Forge 旧式 SimpleChannel
    private static int messageID = 0;
    private static final Collection<AbstractMap.SimpleEntry<Runnable,Integer>> workQueue = new ConcurrentLinkedQueue<>();

    public DumbcatmodMod() {
        MinecraftForge.EVENT_BUS.register(this);
        IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
        DumbcatmodModBlocks.REGISTRY.register(bus);      // MCreator 生成：方块/方块实体/物品/实体/创造栏/菜单/粒子
        ...
        ModBlocks.register(bus);                          // 手写：custom.ModBlocks
        ModItems.register(bus);                           // 手写：custom.ModItems
        ModMenus.register(bus);                           // 手写：custom.kuangji.ModMenus
        ModWeapons.register(bus);                         // 手写：custom.weapon.ModWeapons
        ModEntities.register(bus);                        // 手写：custom.ModEntities
        WeaponSounds.register(bus);                       // 手写：音效
        ModStructures.register(bus);                      // 手写：worldgen
        JewelryMenus.register(bus);                       // 手写：饰品菜单
    }
```
（`DumbcatmodMod.java:52-70`）

值得注意的工程取舍：
- **两套注册并存**：MCreator 的 `init.*` 与手写的 `custom.*` 各自 `register(bus)`，互不干扰——这是"MCreator 生成 + 手写扩展"共存的干净做法。
- **网络是自己注册的**（`addNetworkMessage(...)` 递增 messageID + `queueServerWork(tick, action)` 在主线程延迟执行），说明作者没被 MCreator 的数据包机制限制住。
- 7 个手写注册模块本身就是一份"这个 mod 有哪些子系统"的地图。

---

## 4. 核心系统

### 4.1 修炼系统（`custom/xiulian`，约 77 类）

- **数据落点**：Forge **Capability** 标准三件套 —— `XiulianCapability`（`CapabilityManager.get(new CapabilityToken<XiulianData>(){})`）+ `Provider implements ICapabilitySerializable<CompoundTag>` + `@Mod.EventBusSubscriber(MOD bus)` 里 `RegisterCapabilitiesEvent` 注册（`XiulianCapability.java:25-52`）。
- **数据结构** `XiulianData`（`XiulianData.java:16-28`）：
  ```java
  private final int[] ring = new int[Dao.COUNT];   // 每条"道"的进度环
  private final int[] exp  = new int[Dao.COUNT];   // 每条"道"的经验
  private int realm;          // 境界索引（对应 Realm 枚举）
  private int yuansu, yuansuMax;   // 元气当前/上限
  private int currentDao;
  private CompoundTag extra;  // 扩展袋
  private boolean shenhenMode; // 神痕模式
  private boolean domainOn;    // 领域开启
  private int jiebiCharges;    // 劫壁充能
  private boolean tidalTaken;  // 潮汐（与守潮系统联动）
  private final XinshuData xinshu;   // 心术子系统
  private final ZhanfaData zhanfa;   // 战法子系统
  ```
  → **值得抄的点**：一个 Capability 里用"多条道并行（数组）+ 单值状态位 + 两个子系统容器"的方式组织，避免为每个子系统单独写 Capability。
- **配套**：`RealmPerks`（境界特权）、`RealmArmorGate`（按境界限制穿戴）、`XiulianEvents`（升级/消耗事件）、`XiulianConsume`、`XiulianModes`、`XiulianStats`、`XiulianConfig`、`XiulianCommand`（`RegisterCommandsEvent`）、`XiulianNetwork` + `ClientXiulianData`（NBT/ByteBuf 同步到客户端）、`custom/xiulian/client/XiulianScreen`（795 行自绘界面）。
- **子系统**：`xinshu`（心术 13 类：血魔·始量术、神匠·御界术…）、`zhanfa`（战法 19 类 + 10 客户端：云燕、电击术、烈焰术、风刃…，含 `PojunFxClient` 350 行特效）。

### 4.2 武器体系（`custom/weapon`，44 类）

- **品阶基类** `TieredWeaponItem` / `TieredToolWeaponItem`：同时实现 `Tier`（`getUses/getSpeed/getAttackDamageBonus/getLevel/getEnchantmentValue/getRepairIngredient`）并覆写 `damageItem`、`canApplyAtEnchantingTable`、`getUseAnimation/getUseDuration/use`——**"武器=材质档 + 使用动画 + 技能"的一体化基类**。
- **数据与成长**：`WeaponSpec`（规格）/ `WeaponData`（存档数据）/ `WeaponProgress` + `WeaponProgressEvents`（成长）/ `WeaponSkills`（技能）/ `WeaponEnchants`（专属附魔）/ **`WeaponCurse`（诅咒）** / **`WeaponLock`（绑定锁）** / `WeaponStackCompat`（与堆叠/NBT 兼容）。
- **实体与特效**：`DaoBladeEntity`（刀气飞行物）+ `DaoBladeFx/DaoBladeRenderer`（客户端）、`GrappleWeaponEntity`（钩爪，470 行）、`ThrownWeaponEntity`（投掷）+ **`JianqiFriendlyFire`（剑气对友方伤害豁免）**、`ShockwaveFx` + `ScreenShake`（屏幕震动）、`StuckAware`（卡住感知）、`PlayFpAnim`（触发一人称动画）。
- **设施**：`WeaponAnvil` / `WeaponBench`（方块）、`WeaponTooltip` / `WeaponTabEvents` / `WeaponClientSetup`（注册与 UI）。

### 4.3 守潮系统（`custom/shouchao`，21 类）——mod 的招牌玩法

`HordeManager`（`HordeManager.java:17-45`）：
```java
public static final int DAILY_CHANCE_PERCENT = 7;
public static void tick(ServerLevel level) {
    if (level.dimension() != Level.OVERWORLD) return;
    HordeData data = HordeData.get(level);            // SavedData 挂在 ServerLevel 上
    if (data.hasActive()) { if (data.active().tick(level)) data.setActive(null); else data.setDirty(); return; }
    rollDaily(level, data);                            // 每个游戏日 7% 概率起潮；打龙后切 blood 档
}
```
- 组件分工清晰：`HordeData`（持久化）→ `HordeInstance`（一次潮的运行时）→ `ShouchaoWave`（波次）→ `HordeTier`（强度档，`roll(random, blood)`）→ `HordeRoster`（名单）/ `HordeTargeting`（选目标）/ `HordeRewards` + `RewardGate`（奖励与门槛）/ `HordeGate` + `GateSummonItem` + `GateItemNetwork`（召唤门）/ `ShouchaoAnnounce`（全服公告）/ `ShouchaoCommand`（管理命令 `/…`）。
- **可复用模式**：`SavedData + 每日掷骰 + 实例状态机 + 波次表 + 奖励门`，是"周期性全服事件"的通用骨架。

### 4.4 自研**玩家动画引擎 dcanim**（`client/dcanim`，约 30 类）

**它没有用 GeckoLib 做玩家动画，而是自己写了一套**（GeckoLib 只用于实体/方块）：

| 层 | 类 | 职责 |
|---|---|---|
| 模型 | `model/DcGeoLoader` `DcGeoModel` `DcGeoBone` `DcGeoCube` `DcModelRenderer` | 解析 **Bedrock geometry 1.12**（`format_version: "1.12.0"`，bones/cubes/pivot/uv） |
| 动画 | `anim/DcAnimLoader` `DcClip` `DcInterp` `DcAnimPlayer` | 解析 **Bedrock animation 1.8**（`catmullrom` 插值、`post` 关键帧），播放/混音 |
| 应用 | `firstperson/DcFirstPersonClient`、`thirdperson/DcThirdPersonClient` | **按手持物品注册 Profile**：`register(Item, Profile)`；武器各有一套一人称/三人称动画文件（`chixiao.animation.json` / `chixiao_3rd.animation.json`） |
| 摄像机 | `camera/DcCameraClient` | 动画里带 **`camera` 骨骼**（关键帧驱动镜头） |
| API | `api/DcAnimApi` `DcFirstPersonRenderEvent` `DcThirdPersonPoseEvent` | 对外事件：其他 mod 可干预姿态 |
| 支撑 | `DcAssets` `DcNames` `DcAnimDebug` `DcAnimEngine` | 资源定位、调试绑定（`debugBind(item, profile)`） |

第三人称入口（`DcThirdPersonClient.java:31-60`）：按 `player.getMainHandItem()` 查 `REGISTRY`，`MinecraftForge.EVENT_BUS.post(new DcThirdPersonPoseEvent(player))` 可被取消——**"注册表 + 事件"**双扩展点。
接入原版渲染：`PlayerModelMixin` 注入 `PlayerModel.setupAnim(...)` 的 RETURN 后调用 `DcThirdPersonClient.afterSetupAnim(entity, model)`（`mixin/client/PlayerModelMixin.java:16-19`）。
`anim` 格式关键点：`loop`/`animation_length`/`bones.<name>.{position,rotation}.<time>.post[]`，位移单位是像素→由引擎换算。

### 4.5 自研**特效引擎 dcvfx**（`client/dcvfx`，55+ 类）

- **程序化网格生成器（11 种）** `mesh/`：`TubeMesh`(232)/`RibbonMesh`(220)/`FoamClusterMesh`(197)/`WaveSheetMesh`+`WaveProfile`/`BoltMesh`(闪电)/`LightningMesh`/`RippleMesh`/`DiscMesh`/`PointCloudMesh`/`BillboardMesh`/`WakeMesh`(尾迹)。
- **材质与层系统**：`VfxInstance`(316)/`VfxLayer`/`VfxMaterial`/`VfxFrame`/`VfxRenderer`(254)/`VfxRenderTypes`/`VertexSink`(自定义顶点写入)/`IMeshProvider`/`IColorRamp`/`ICurve`/`VfxNoise`/`VfxBlend`/`ShaderPackDetect`(光影包检测!)。
- **产品级实现**：`fx/FireTornado`（**1353 行、28 个层**：`circle_outer/inner、gather_arc/glow/spark、flash、shock、burst_ribbon/spark、scorch、pool、ripple、column、inner、cap、smoke、whip、wind、outer、orbit、core、sparks、top_embers、ash_ember、ash_dust、bolt、smoke_out、diss_ribbon`，每层独立材质+颜色常量+时间轴常量）；`TidalWaveFx`(390)；`FireStormRoarSound`；`ScreenShakeClient`。
- **服务端联动**：`custom/firestorm/{FireStormMessage, FireStormTiming}`——技能释放/时序由服务端发包驱动客户端特效，避免客户端各自为政。

### 4.6 内置性能剖析 + LOD（`custom/perf`）

- `DcPerf`：`enabled` 开关、`bucket(key)` → `Bucket{calls, nanos, cubes, entities}`、`begin()/end()` 打点、`endFrame()` 每帧清理 `SEEN`（**用 entityId 去重统计"不同实体数"**）、`serverMspt/serverModEntities/serverTotalEntities`。
- 采集入口：`EntityRenderTimingMixin` 在 `EntityRenderDispatcher.render` 的 **HEAD/RETURN** 成对打点（`mixin/client/EntityRenderTimingMixin.java`）；`DcPerfClient.pushTiming/popTiming`。
- 产出：`DcPerfCommand`（游戏内命令查看报告）、`DcPerfNetwork`（客户端↔服务端数据汇总）。
- `DcLod`：按相机距离三档（`highDistance=24`、`midDistance=40`）为实体贴图选档（`pick(ResourceLocation high, Entity)`，带 `NO_LOD` 白名单与缓存）；**当前 jar 内没有 `_lod` 变体贴图**，`variants[level] == null` 时回退高模——属于"框架已就绪、资源待补"的预留实现。

### 4.7 其它子系统（列表）

| 子系统 | 类 | 说明 |
|---|---|---|
| 抽卡 `custom/cards` | 13 | `CardItem`/`CardBoxItem`(卡包)/`CardOpening`(开包动画)/`CardRarity`(稀有度)/`CardDropEvents`(掉落)/`CardNetwork`+`CardClient` |
| 拆解机 `custom/chaijie` | 8 | `ChaijieLogic`/`ChaijieRecipes`(拆解配方)/`ChaijieMenu`/`ChaijieClientListener` |
| 车床 `custom/chechuang` | 2 | MCreator GUI 逻辑（`procedures/Chechuang…Procedure` **3001 行**生成代码） |
| 矿机 `custom/kuangji` | 8 | `KuangjiLogic`(8 类)/`DrillBitItem`(钻头)/`KuangjiMenu` |
| 饰品 `custom/jewelry` | 28 | `JianxiaItem`+`JianxiaStorage`+`JianxiaMenu`（**剑匣内存储 + GUI**）、`ShengjieItem`、`TiangangItem`(天罡)、`GlowRelicItem`、`RegenRingItem`、`MechanicalPotionItem`、`CombatClock`、`RingStorage` |
| Boss/实体 `entity` + `custom/boss` | 24+19+11 | `JingzhongsheEntity`(镜中蛇, 1513 行)、`GaizaobaojunxiongEntity`(改造暴君熊, 955)、`Xuemi1Entity`、`LiediSmashGroundEntity`；AI 目标 `SnakeSkillGoal`(695)/`SnakeStalkGoal`(368)；`BossScaling`(随玩家境界缩放)、`LabWeather`/`ClientLabWeather`(实验室天气)、`BearRoom` |
| 守潮外的世界 | `custom/worldgen` | 38 个 worldgen json（3 结构 + 18 biome_modifier） |
| JEI/Jade 兼容 | `compat/jei`(2) `compat/jade`(2) | 接 JEI 插件与 Jade Provider |
| 其它 | — | `custom/spawn`(刷怪)、`custom/repair`、`custom/xueyao`(血药 9)、`custom/zhiyao`(制药 11)、`custom/xiancao`(仙草 10)、`custom/gtgxiangzi`(箱子 7)、`custom/ClientSelfHarm`（自身伤害反馈抑制） |

---

## 5. 网络 / 数据 / 配置

- **网络**：Forge `SimpleChannel`（`NetworkRegistry.newSimpleChannel`，协议版本 "1"）+ 自写 `addNetworkMessage` 注册器。可见包：`network/DumbcatmodModVariables`（MCreator 变量同步）、`network/MenuStateUpdateMessage`（菜单状态）、`network/TeshuMessage`（自定义；`buffer()/handler()` 静态方法 + `context.enqueueWork`）。各子模块另有专用包：`XiulianNetwork`、`CardNetwork`、`JewelryNetwork`、`DcPerfNetwork`、`GateItemNetwork`、`FireStormMessage`。
- **数据**：`XiulianData` 走 Capability + `save()/read(CompoundTag)`；`HordeData` 走 `SavedData`；武器数据在 `WeaponData`（物品 NBT）。
- **配置**：`XiulianConfig`、`JewelryConfig`（模块级配置类）。
- **资源驱动**：帕秋莉 144 页手册（`data/dumbcatmod/patchouli_books`）、69 配方、64 进度（含叙事文本，如"把过往锁进箱子里 89 秒，听它讲完那个梦"）、ParticleStorm 的 4 个 `particle_definitions`。

---

## 6. Mixin（3 个，全部 client 侧）

配置文件 `dumbcatmod.mixins.json`：`package=net.mcreator.dumbcatmod.mixin`、`compatibilityLevel=JAVA_17`、`refmap=dumbcatmod.refmap.json`、`client` 三条、`defaultRequire=1`。

| Mixin | 目标 | 手法 |
|---|---|---|
| `client.PlayerModelMixin` | `PlayerModel#setupAnim(LivingEntity;FFFFF)V` | `@Inject(at=RETURN)` → 调用自研 dcanim 的三人称姿态覆盖 |
| `client.EntityRenderTimingMixin` | `EntityRenderDispatcher#render` | HEAD/RETURN 成对 `@Inject`，**`require=0`**（性能剖析功能失败不影响游戏） |
| `client.LocalPlayerHurtMixin` | `LocalPlayer#hurtTo(F)V` | RETURN 后若 `ClientSelfHarm.consume()` 则把 `hurtTime/hurtDuration` 归零——**"自伤时不抖屏"的精确实现** |

工程细节：注入方法统一 `dumbcatmod$` 前缀（防冲突）、只做 client 侧、refmap 正常生成、可失败项用 `require=0`。

---

## 7. 值得学的 6 条具体做法

1. **"MCreator 生成 + 手写模块"的双轨工程**：MCreator 管 `init/`、`procedures/`、资源；手写代码集中在 `custom/`、`client/`，由主类统一 `register(bus)`（`DumbcatmodMod.java:64-77`）。既吃到了可视化工具的产能，又保留了手写控件的自由度。→ 对任何"工具生成 + 手写扩展"的场景都适用。
2. **自研玩家动画引擎（dcanim）**：用 Bedrock 格式（geo 1.12 + animation 1.8）自建 `loader → clip → interp → player → 按物品注册 Profile` 管线，并按"一人称/三人称"分文件；渲染接入只用一个 5 行 mixin（`PlayerModelMixin`）。→ 当需要"武器专属手部动画 + 镜头骨骼"这类 GeckoLib 覆盖不好的能力时，这是一个完整可抄的骨架。
3. **自研 VFX 引擎（dcvfx）的"层+网格生成器"架构**：把"形状"（11 种程序化 mesh）与"表现"（材质/颜色渐变/噪声/曲线/混合）解耦，Boss 技能 `FireTornado` 只负责编排 28 个层（`FireTornado.java:45` 的 `LAYERS` 常量就是技能设计表）。→ 复杂特效可维护性的关键。
4. **内置性能剖析器**：`DcPerf` + 一个 `require=0` 的渲染 mixin + 命令/网络汇总（`custom/perf/*`）。→ 把"性能观测"做成产品内建能力，而不是靠外部 profiler。
5. **周期性全服事件骨架**：`SavedData + 每日掷骰(7%) + 实例状态机 + 波次/强度表 + 奖励门 + 全服公告`（`HordeManager.java:17-45`）。→ 任何"尸潮/天灾/入侵"玩法可直接套用。
6. **子系统级的"网络+配置+命令"三件套**：每个大模块（修炼/饰品/抽卡/守潮/性能）都有独立的 `XxxNetwork`/`XxxConfig`/`XxxCommand`，而不是堆在一个巨型类里。→ 与你现有工程的模块划分习惯一致，可对照检查。

---

## 8. 对我们（修仙方向 mod）的直接启示

- **境界系统**：`Realm` 枚举（10 境）+ `RealmPerks`/`RealmArmorGate` + Capability 存档，是一套可直接对标的"境界=枚举、进度=道×经验数组、状态=布尔位"的数据模型（`XiulianData.java:16-28`）。比"每个境界一个 Capability/一份 NBT 键"更省事。
- **心术 / 战法分家**：`xinshu`（被动/术法）+ `zhanfa`（主动战法，带独立客户端特效 `PojunFxClient`）两类内容分目录、分数据容器，适合做"功法体系"的扩展。
- **武器成长链**：品阶（Tier）→ 技能（Skills）→ 附魔（Enchants）→ 诅咒（Curse）→ 绑定（Lock）→ 进度（Progress），五层各有事件（`WeaponProgressEvents`），是一条成熟的"武器养成"流水线。
- **守潮事件**可以改造为"魔潮/天劫"：把 `HordeTier.roll(random, blood)` 换成按境界掷骰即可。
- **反例警示**：`procedures/ChechuangDangGaiGUIDaKaiShiMeiKeFaShengProcedure.java` 单文件 3001 行是 MCreator GUI 生成的典型产物——**手写逻辑不要塞进 procedure**，否则维护成本爆炸。

---

## 9. 反编译方法（可复现）

```bash
# 1) 反编译（本机已有 CFR：~/AppData\Local\Temp\cfr.jar）
java -jar cfr.jar BleedZone7-0.0.3-forge-1.20.1.jar --outputdir _bleedzone/src --silent true --caseinsensitivefs true
# 2) SRG→官方名还原（用本地 NFRT 映射，脚本在 Downloads/_bleedzone/remap.py）
python remap.py     # 解析 officialToSrg.tsrg 并反转；替换 m_/f_ 名
```
- 映射源：`~/.gradle\caches\neoformruntime\intermediate_results\createMappings_*_officialToSrg.tsrg`（本机装过 1.20.1 Forge MDG 工程即可复用，无需联网）
- 还原效果：12,453 个方法名 + 3,592 个字段名；`p_xxx_` 参数名因该映射文件不含参数行而保留（不影响阅读）
- 产物：`源码库\_参考仓库\BleedZone7__dumbcatmod-0.0.3\`（493 个 .java，3.7 MB）
