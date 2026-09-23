# Flan 源码分析报告

- 仓库：`源码库\_参考仓库\_bulk\Flemmli97__Flan`（https://github.com/Flemmli97/Flan）
- 分析日期：2026-09-23；全部行号以本地检出为准（`wc -l` 实测口径）

## 1. 基本信息

**这个 mod 到底做什么（自判，非卡片转述）**：Flan 是一个**纯服务端领地保护（land claiming）mod**，GriefPrevention 的 Fabric/NeoForge 复刻与扩展。核心是给世界划分 2D/3D 领地区块、用数据包定义的"权限"逐交互拦截，并提供完全服务端的 GUI。README.md:7 自述 "Server side land claiming mod"；neoforge.mods.toml:14 自述 "A serverside claiming mod"。**它与妖兽/玩家动作、技能、BOSS 战无关**——仓库中没有动画系统、没有技能系统、没有实体 AI 改写（详见第 4、8 节的逐条回应），本报告按"服务端交互仲裁 + 数据驱动权限 + 零自定义协议"的样本价值来分析。

- mod_id：`flan`（gradle.properties:13；neoforge.mods.toml:8）
- 作者：flemmli97（gradle.properties:14）
- 许可证：**All rights reserved**（neoforge/src/main/resources/META-INF/neoforge.mods.toml:1；检出内无 LICENSE 文件）——只可学结构，不可搬代码
- 目标平台：MC 26.2（新编号方案），NeoForge 26.2.0.63 + Fabric loader 0.19.3 / Fabric API 0.158.0+26.2（gradle.properties:3-8,17）。**卡片写"Forge 26.2.0.63"有误：工程只有 neoforge 模块，无 Forge 模块**
- mod 版本：1.12.8（gradle.properties:11）
- Gradle 插件与工程结构：三模块多加载器（settings.gradle:41-43 `common/fabric/neoforge`），但用的是 flemmli97 自家的 blazing-coop multiloader 插件族而非标准 MLO：根 build.gradle:2-5 声明 `fabric-loom 1.15-SNAPSHOT`、`net.neoforged.moddev 2.0.141`、`mod-publish 2.2.0`、`io.github.flemmli97.multiloader.discord_hook`；common/build.gradle:2-3 用 `platform-common`+`tiny-remapper`，平台模块各自 `platform-fabric`/`platform-neoforge`
- Java 版本：gradle.properties:2 `jvm=25`（curseforge_versions 亦标 Java 25，gradle.properties:45），由 multiloader 插件消费（仓库内无直接引用，未验证具体接线）；mixin `compatibilityLevel: JAVA_21`（三个 mixins.json 均为 5）

## 2. 源码规模与包结构

实测：**210 个 .java、共 16,598 行**（卡片写 16,808，偏高；Claim.java 实测 1,043 行，卡片 1,044）。分布：

- common：161 个（业务全在这里，含 41 个通用 mixin）
- fabric：30 个（入口 + 16 mixin + 平台桥 + `api/fabric` 公开事件）
- neoforge：19 个（入口 + 5 事件桥 + 5 datagen + 平台桥）

主要包（common，按文件数）：

| 包（`io.github.flemmli97.flan.` 下） | 文件数 | 职责 |
|---|---|---|
| `mixin` | 41 | 通用拦截 mixin |
| `commands.sub` | 26 | 子命令 |
| `gui` | 19+3(inv) | 纯服务端 GUI |
| `claim` | 7+3(attachment) | 领地实体与存储 |
| `event` | 5 | 三端共享交互事件 |
| `api.permission` | 5+3+2 | 数据驱动权限层 |
| `player`(+display) | 6+4 | 玩家数据与表现 |
| `config` | 4 | 手写 Gson 配置 |
| `platform.integration.*` | ~15 | 地图/经济/权限 mod 桥 |

最大源文件（`wc -l`）：Claim.java 1043、PlayerClaimData.java 679、ClaimStorage.java 667、Config.java 496、ENLangGen.java(neoforge) 330、BuySellHandler.java 328、ItemInteractEvents.java 325、EntityInteractEvents.java 322、PlayerEvents.java 308、ClaimDisplay.java 300、BlockInteractEvents.java 278、ClaimPermission.java 198。

**稀疏检出说明**：`common/src/main/resources` 只有 `META-INF/accesstransformer.cfg`（实测 0 字节，空文件）和 `flan.mixins.json`；README:13-14 引用的 `common/src/main/resources/data/flan/lang` 与 `common/src/generated/resources`（datagen 产物）**均不在本地检出内**；fabric 模块亦无 fabric.mod.json（推断由 multiloader 插件生成，未验证）。语言文件、datagen JSON 内容无法核对，凡引用处均标注。

## 3. 入口与注册

common 层没有入口类，`Flan.java` 只是常量 + 日志 + 反射平台工厂（见下）。真入口分平台两个：

NeoForge 入口 `neoforge/.../FlanNeoForge.java:27-74`：构造器内检测可选 mod、把交互回调逐个挂到 NeoForge 总线，**破坏/放置/交互一律 `EventPriority.HIGHEST`**（45-52 行），再挂生命周期（59-66），最后注册计分板_criteria_（73）：

```java
bus.addListener(EventPriority.HIGHEST, BlockInteractEventsNeoForge::startBreakBlocks);
bus.addListener(EventPriority.HIGHEST, BlockInteractEventsNeoForge::breakBlocks);
bus.addListener(EventPriority.HIGHEST, EntityInteractEventsNeoForge::preventDamage);
bus.addListener(ServerEvents::commands);
...
ClaimCriterias.init();
```

Fabric 入口 `fabric/.../FlanFabric.java:56-117`：注册原生 player 事件与生命周期事件，并统一插一个自定义事件相位，保证跑在其他 mod 默认相位之前（119-122）：

```java
private static <T> void applyPriorityListener(Event<T> event, T listener) {
    event.addPhaseOrdering(EVENT_PHASE, Event.DEFAULT_PHASE);
    event.register(EVENT_PHASE, listener);
}
```

数据重载注册是两端对称的：`PermissionManager` 与 `InteractionOverrideManager` 作为 reload listener 挂入（FlanNeoForge.java:76-79、FlanFabric.java:80-81）。可选 mod 集成（Impactor/DiamondCurrency/OctoEconomy/BEconomy/动态地图/FTB…）全部以 `isModLoaded` 守卫后调用各自 `register()`。两端入口末尾都会 `ClaimCriterias.init()` 注册自定义计分板 criteria（FlanNeoForge.java:73、FlanFabric.java:116）。

**事件订阅点的取向**：所有"拦截型"回调（破坏开始/进行中、放置、方块右击、实体右击/攻击、投射物命中、伤害否决）一律最高优先级/最早相位；所有"表现型"回调（经验吸收、掉落、mob griefing、闪电）用默认相位。命令注册两端共用同一 `CommandClaim.register`，仅以 `env == DEDICATED` 区分（FlanFabric.java:78）。**没有任何客户端入口**——两个平台类都只在 dedicated 侧初始化，本 mod 客户端零代码。

跨平台实例获取用反射：`common/.../Flan.java:43-68` `getPlatformInstance(Class, String... implFqns)`，按类名探测哪个平台实现存在并反射建实例——整个 common 层的 SPI（`ClaimEvents.INSTANCE`、`CrossPlatformStuff.INSTANCE` 等）都靠它接线（platform/ClaimEvents.java:12-15）。

## 4. 核心系统

### 4.1 领地存储与空间索引（claim/ClaimStorage.java）

数据表示：每维度一个 `ClaimStorage`，`Long2ObjectOpenHashMap<List<Claim>> claims` 以 packed ChunkPos 为键做粗索引（69 行），另有 `claimUUIDMap`、`playerClaimMap` 两个反查表和 `Set<UUID> dirty` 脏标记（70-72）。`Claim` 本体是 min/maxX/Z + minY + 可空 maxY（null=到世界底/顶，即 3D 领地用 `Integer maxY` 表达开放高度，Claim.java:71-72），权限按"组名→(权限id→bool)"两层 map 存（77-79），子领地挂在 `subClaims` 上并回指 `parentClaim`（83-87）。查询：`getForPermissionCheck(pos)` 命中返回 Claim，否则返回 `GlobalClaim`（301-306）；半径查询 `getNearbyClaims` 按 chunk 遍历再 AABB 过滤（309-330）。新建/改界时 `conflicts()` 只扫覆盖到的 chunk 桶、逐条 intersects，且会把冲突检查**外包给其他圈地 mod**（`OtherClaimingModCheck.findConflicts`，179-197）——与 FTB Chunks/GOML/MineColonies 互不打架的关键在这。持久化：**不进 NBT/region，独立 JSON 文件**写到维度存档目录 `data/claims`（ConfigHandler.java:34-36；save 按 owner 分文件、dirty 才重写，445-486）。生命周期靠 mixin 绑定：`ServerWorldMixin` 让 ServerLevel `implements IClaimStorage` 并在构造注入、`saveLevelData` 时落盘（ServerWorldMixin.java:12-24），`ClaimStorage.get(level)` 即一次强转（76-78）。还内置 GriefPrevention 的 YAML 迁移器（ClaimStorage.java:489 起）。

### 4.2 权限模型与判定瀑布（api/permission + claim/Claim.java）

数据表示：权限不是枚举而是**数据包条目**——`PermissionManager extends SimpleJsonResourceReloadListener<ClaimPermission.Builder>`，注册在自定义 registry key `flan:claim_permission` 下（PermissionManager.java:22-34）；`ClaimPermission.Builder.CODEC` 声明 gui 图标、default/global/require_explicit/order/required_mod（ClaimPermission.java:104-113），`requiredMod` 缺失时 `verify()` 直接丢弃该条目（167-169）。内置 60+ 权限在 BuiltinPermission 以 static final Identifier 登记，且**注册行为随 datagen 分支**（BuiltinPermission.java:126-133：仅 `isDataGen()` 时塞进 `DATAGEN_DATA`），并保留旧字符串键→新 id 的迁移表（32、135-144）。判定发生在交互事件线程（服务端），`Claim.canInteract(player, perm, pos, message)` 是一条固定优先级的瀑布（Claim.java:315-400）：假玩家改判 FAKEPLAYER → 第三方 mod 钩子 `ClaimEvents.claimCheck` → 全局配置锁死项 → 离线保护 → global 权限递归子领地 → owner/admin 绕过（受 `requireExplicitSet` 反制，402-410）→ 玩家分组表 → claim 默认值。跨端流转：**没有跨端**——判定纯服务端，客户端只收到"操作失败"的副作用（见 4.5）。

### 4.3 交互→权限的重映射层（api/permission/InteractionOverrideManager.java）

第二个数据管道：`flan:claim_interactions_override`，允许数据包把"某个方块/物品/实体的某种交互"改指到任意权限 id。7 个上下文用 static `InteractionType` 声明（46-52），条目 codec 是按 type id 的 `Identifier.CODEC.dispatch`（185-190）。解析是惰性的：tag/holder-set（`ResolvableHolderSet.codec` = `RegistryCodecs.homogeneousList`，天然支持 `#tag` 与 `[单元素列表]`，ResolvableHolderSet.java:13-17）先进 `unresolvedTags`，首次查询时排序展开成 direct map（InteractionOverrideManager.java:159-182），数据包条目**优先于**代码内 `ObjectToPermissionMap` 的 predicate 默认值（130-145；默认映射表见 ObjectToPermissionMap.java:99-135，第三方 mod 可再注入自己的 predicate，65-97）。

### 4.4 玩家数据与经济（player/PlayerClaimData.java、config/BuySellHandler.java）

`PlayerClaimData` 由 `ServerPlayerMixin` 在构造器注入字段、经 `IPlayerClaimImpl` 能力接口取回（ServerPlayerMixin.java:22-38；PlayerClaimData.java:106-108）。存的东西：剩余 claim 块数、编辑模式/首个角点、进行中确认命令、显示集合、假玩家通知 map（70-102）。读盘/写盘的挂点两端不同但语义一致：fabric 用 `PlayerList` 的 mixin（placeNewPlayer HEAD / save RETURN，WorldSaveHandlerMixin.java:16-23），neoforge 用 `PlayerEvent.SaveToFile/LoadFromFile`（ServerEvents.java:35-42）。**冷却与"资源再生"全在服务端 tick**：在线每满 `ticksForNextBlock`（默认 600）加 1 块（322、339-342），另有 `confirmTick/actionCooldown` 节流；持久化为 playerdata 目录下 `claimData` 的 JSON（ConfigHandler.java:38-40；PlayerClaimData.java:569 起 read）。可 claim 上限可被权限节点封顶/加成（74-80 行经 `PermissionNodeHandler` 桥 FTB Ranks 之类）。买地/卖地的货币是 SPI：`api/economy` 定义接口，`platform/integration/currency` 按加载的 mod 提供 Impactor/DE/OctoEconomy/BEconomy 实现，BuySellHandler（328 行）做汇率曲线。领地光环用**原版 MobEffect 注册表里的效果**（`Holder<MobEffect>` 映射到等级/时长，Claim.java:96），驻留时每 20 tick 补挂 ambient、无图标、-amplifier-1 的实例（Claim.java:644-653，调用点 PlayerEvents.java:277）——它没有自有 status/effect 层，光环就是用 `addEffect` 反复续挂原版 MobEffectInstance（ambient=true、不显示粒子，Claim.java:649），并在剩余时长≤20 tick 时才补（夜视特判≤220，648 行）。

### 4.5 纯服务端 GUI 与零包表现（gui/、player/display/、player/ClientBlockDisplayTracker.java）

全部界面（领地菜单、权限页、分组、药水编辑、白名单、文本输入、确认页）都是 `ServerOnlyScreenHandler`：借用原版 `MenuType.GENERIC_9xN` 开箱子菜单，**把"按钮"实现为不可拾取的 ItemStack**，在 `clicked()`（94-109）和 `quickMoveStack()`（110-118）里拦原版容器包，点击反馈用直接单发 `ClientboundSoundPacket`（ServerScreenHelper.java:144-149）；文本输入复用铁砧菜单（StringResultScreenHandler.java:23-41），禁翻讲台用 `clickMenuButton` 拦截 id==3（LockedLecternScreenHandler.java:39-44）。领地边界表现：服务端算顶点/棱插值点阵（ClaimDisplay.java:49-120），每 tick 直接向在场玩家发 `ClientboundLevelParticlesPacket`（187-190）；选区角点用**发原版 `ClientboundBlockUpdatePacket` 的"假方块"**表现，`ClientBlockDisplayTracker` 维护 per-UUID 显示集与 pos→UUID 反向表以正确还原重叠假块（ClientBlockDisplayTracker.java:23-80）。进出领地的标题/副标题同样是服务端单发包：`player.connection.send(new ClientboundSetTitleTextPacket(title))`（Claim.java:692-694）。GUI 打开后需要刷新的页面实现 `TickingGui` 接口（TickingGui.java:3-11，默认 20 tick 一次），由玩家 tick 驱动回 `fillInventoryWith`。

### 4.6 命令、确认流与离线保护（commands/、player/LogoutTracker.java、scoreboard/）

26 个子命令挂在 `/claim` 下（commands/CommandClaim.java + `sub/` 包）。破坏性操作走**延迟确认流**：命令把自身包装成 `PendingCommand`（PendingCommand.java:10-29，持 CommandContext 与 `Supplier<Integer>`）存进 `PlayerClaimData.deferCommand`，同时置 `confirmTick = 400`（PlayerClaimData.java:270-272）；玩家须再执行 `/claim confirm confirm|deny`（ConfirmCommand.java:20-34，带建议补全），超时后 tick 里自动作废（PlayerClaimData.java:361-363）。同文件还有 10 tick 的 `actionCooldown`（184、384 行）节流高频命令。离线保护：`LogoutTracker` 由 MinecraftServer 经 mixin 能力接口取实例（LogoutTracker.java:16-18），玩家登出后按配置时长内领地仍视同主人在场（Claim.java:350-352 的检查分支引用它）。经济/配额对外暴露 4 个自定义计分板 criteria（ClaimCriterias.java:7-10：total/used/free_claimblocks、claim_number），每次 `setClaimBlocks` 同步回写（PlayerClaimData.java:115-119），让服主用原版计分板就能做权限门槛。边界跨越同样双向下发：`ServerPlayerMixin.java:46` 检测当前 claim 变化后调 `ClaimEvents.INSTANCE.borderCross`，fabric 侧再转成 `ClaimBorderCrossEvent` 公开事件（api/fabric/ClaimBorderCrossEvent.java）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **自定义网络包：零。** 全仓库 grep `registerReceiver|PayloadRegistrar|CustomPacketPayload|addNetworkMessage|PacketDistributor.sendToPlayer` 无命中；对外只**直接构造原版协议包**（§4.5）。这是它作为"无客户端 mod 的服务端插件"的立身之本。
- **数据驱动程度：高（权限层），且只用 Codec。** 两套 JSON 管道（`flan:claim_permission`、`flan:claim_interactions_override`）都是 `SimpleJsonResourceReloadListener` + DFU Codec + 自定义 registry key，支持 `required_mod` 条件裁剪、tag 引用、legacy 键迁移（BuiltinPermission.java:131、ClaimHandler.java:59-66）。
- **非数据驱动的一半：** 领地/玩家/分组数据本体是 Gson JSON 文件（第 4 节），无 Codec、无 NBT——因为消费方只有服务端自己，不需要进原版序列化管线。
- **配置：** 手写 Gson 的 `Config.java`（496 行，约 60+ 顶层项：起始/上限块数、产出速率、3D 开关、维度级权限覆盖、黑名单等，39-80 行），`ConfigHandler` 集中加载（33-43 行还有 claim 工具的"部分 DataComponent 匹配"），`ConfigUpdater` 做版本迁移。无 Forge/Fabric 配置库依赖。
- **datagen：** 有，且只挂 neoforge：`DataEvent.java:13-20` 在 `GatherDataEvent.Server` 注册 `PermissionGen`（把 `BuiltinPermission.DATAGEN_DATA` 落成 JSON，含 Create 兼容条目，PermissionGen.java:24-33）、`InteractionOverrideGen`、`ENLangGen`（330 行，从代码里的描述串生成英文 lang）。产物目录 `common/src/generated/resources` 不在本次检出内（§2）。

## 6. Mixin / ASM / 接口注入

无 ASM，全靠 Mixin；三份配置：common 41 个（flan.mixins.json）、fabric 16 个、neoforge 1 个（NeoForgeFireMixin）。三个目的族：

1. **能力注入（给原版类挂"接口实现"）**：`ServerWorldMixin` 使 ServerLevel 实现 `IClaimStorage`、`ServerPlayerMixin` 使 ServerPlayer 实现 `IPlayerClaimImpl`+飞行/掉落跟踪接口并注入字段（ServerPlayerMixin.java:22-38）；fabric 侧 `ItemUseBlockFlags` 暴露 `flan$stopCanUseBlocks` 等 setter，让交互事件能反向控制 Fabric 事件后续行为（FlanFabric.java:134-146）；`WorldSaveHandlerMixin` 给 PlayerList 挂读盘/写盘钩子（16-23）。所有注入字段/方法一律 `@Unique` + `flan$` 前缀。
2. **事件缺失补洞**：`PistonMixin` 注入 `isPushable` HEAD——注释明说 Forge 活塞事件位置不合适、要算全部受影响方块才在 mixin 层解决（PistonMixin.java:16-25）；同理 EndermanPickup/Place、Allay、SculkSensor/Shrieker、RaidManager、FireBlock、Fluid、TurtleEgg、ItemEntity（拾取/掉落）、DragonEgg、Moss、SulfurCube 等，把原版"没有事件的动作者"逐个钉住。fabric 专属 16 个 mixin（ExplosionMixin、PlayerDropMixin、WitherMixin、Patrol/PhantomSpawner、XpEntity 等）的存在本身就是证据：**同一拦截语义在两个加载器上事件覆盖面对不齐**，neoforge 侧同类逻辑走 `EntityInteractEventsNeoForge` 事件即可。`accesstransformer.cfg` 存在但实测为 0 字节——作者宁可写 mixin/accessor 也不开 AT。
3. **细粒度体验**：`ServerPlayerGameModeMixin` 见 §7-1；`ChunkGeneratorMixin`/`StructureManagerAccessor` 服务结构自动圈地（WorldEvents.java:114-127）；`PlayerMixin` 用 `@ModifyVariable` 在刺击(鞘翅冲刺)伤害计算点把被保护区挡下的攻击的击退标记改成 false（PlayerMixin.java:16-22），`LivingEntityMixin` 在掉落物生成点给 ItemEntity 打"来源玩家"标记（`createItemStackToDrop` 处调 `flan$setOriginPlayer`，LivingEntityMixin.java:14-18 → PlayerEvents.java:219-221，接口 `IOwnedItem`），供死亡掉落锁定（LOCKITEMS/PICKUP 权限）过滤；accessor 类（`ILecternBlockValues`、`BonemealableBlockAccess`、`IHungerAccessor`、`IPersistentProjectileVars`）纯读私有字段供 GUI/事件层用。

## 7. 值得学的 5 条

1. **失败挖矿的"无包反馈"**：`common/.../mixin/ServerPlayerGameModeMixin.java:31-52`——玩家在保护区开始破坏时给 `BLOCK_BREAK_SPEED` 挂 -100% transient modifier（进度条冻住、纯原版渲染），收到 ABORT 包再摘掉。为什么抄：零自定义包做出"啃不动"的手感，求仙问道的禁制护盾/阵法反弹反馈可同款实现。
2. **服务器端 GUI 全家桶**：`common/.../gui/ServerOnlyScreenHandler.java:94-118` + `ClaimMenuScreenHandler.java:42-102`——原版箱菜单 + 不可拾取 ItemStack 当按钮 + `clicked/quickMoveStack` 拦截 + `ContainerListener.slotChanged` 回刷。为什么抄：任何"客户端不装 mod 也要能配置"的系统（境界丹参数、妖兽白名单）都可直接套这套骨架，连文本输入都有铁砧方案（StringResultScreenHandler.java:23-41）。
3. **权限即数据包的完整闭环**：`ClaimPermission.java:104-113`（Builder.CODEC）+ `InteractionOverrideManager.java:185-190`（dispatch codec）+ `BuiltinPermission.java:126-133`（同一份定义驱动 datagen 与运行时）+ `ClaimHandler.java:59-66`（旧键迁移）。为什么抄：技能/能力系统若把这四层一次设计到位，就能"加一个技能=丢一个 JSON"，且天然支持 `required_mod` 条件与 tag 批量绑定——这正是六样本综述指出的"全库无人做 JSON 数据驱动招式表"的现成答案。
4. **惰解析 + 三级覆盖的 holder 解析器**：`InteractionOverrideManager.java:153-182`——数据包条目、代码 predicate 默认值都先进 unresolved 队列，首次查询按 key 排序展开、先声明者优先、`direct` 已含则跳过。为什么抄：妖兽/配方白名单这类"注册表巨大但每条交互只查一点"的映射应该照抄这套延迟展开，避免 reload 时全表实例化（对比它在 96-112 行的反面教材，见 §8）。
5. **假方块表现层**：`common/.../player/ClientBlockDisplayTracker.java:40-80`——per-UUID 显示集 + pos→UUID 反查表，重叠假块撤销时能还原成"上一个占用者"的状态而非直接还原真方块。为什么抄：技能预警圈/ Colossus 前摇的"临时地形改变"（光墙、符文方块）需要这个 diff+还原簿记，原版 `LevelChunk#setBlockState` 直发会互相踩。

## 8. 公开 API 与遗留问题

**扩展点（它是有意的公开 API，README:19-44 附 maven 接入文档，产物带 `:api` classifier）**：

- `api/ClaimHandler.java:27-66`：`canInteract` / `getPermissionStorage` / `getPlayerData` / `registerMapping` 四个静态门面，第三方 mod 在自己的交互点主动问"这里能不能干"。
- `ObjectToPermissionMap.register*PredicateMap`（65-97）：给方块/物品/投射物挂自定义权限 predicate。
- `ClaimAllowListKey` 构造即注册（56-61）：可为任意 registry 新增一个"白名单维度"，GUI 页自动出现。
- `platform/ClaimEvents.java:16-18`：`claimCheck`（否决/放行任意检查）与 `borderCross`（进出领地），fabric 侧转成公开 `ClaimBorderCrossEvent` 事件。
- `api/economy` SPI + datagen 基类 `ClaimPermissionProvider`/`InteractionOverrideProvider`（api/permission/provider/），第三方可复用它们发布自己的权限 JSON。
- 跨 mod 兼容层（FTB Chunks/GOML/MineColonies/common-protection-api 只读查询）在 `platform/integration/claiming`。

**重点问题的逐条回应**：

- ① 动作/动画系统：**本仓库无此系统**——无 GeckoLib、无动画层、无命中帧回调；与 Colossus"判定帧"最接近的东西是纯服务端 tick 计数（PlayerClaimData.java:339 的产出计时、confirmTick/actionCooldown 节流），表现全部单向推送、客户端不回流。
- ② 技能/能力系统：**无**；最接近的是"权限"这一交互能力层（§4.2/4.3），冷却与消耗对应 `confirmTick/actionCooldown` 与 claim 块数（PlayerClaimData.java:68、184），全部存服务端 JSON、无跨端表现。
- ③ 状态效果：**无自有 effect 层**，领地光环直接用原版 `MobEffect`/`MobEffectInstance`（Claim.java:96、644-653），与原版 MobEffect 是"使用"而非"扩展"关系。
- ④ AI 与实体：**不改 Goal**——对实体行为（末影人搬方块、监守者尖叫、袭击、闪电）全部用 mixin/事件在动作执行点否决（§6），目标选择逻辑零触碰。
- ⑤ 渲染与表现耦合点：粒子边界、假方块、标题消息三类原版包直发（§4.5），无模型替换、无拖尾。

**给「求仙问道」技能/动作层的 2 条可搬做法**：(a) 把"妖兽交互白名单/功法可用域"照 `ClaimAllowListKey`+`AllowedRegistryList` 做成 registry+tag 双形态数据清单（§8 第 3 条，AllowedRegistryList.java:38-61 的 `Either<T, TagKey<T>>` + GUI 自动摊开），白名单页与 tag 支持白送；(b) 技能可用性做成 §7-3 的四层闭环（Builder.CODEC 定义→DATAGEN_DATA 驱动 datagen→reload listener 生效→LEGACY_MIGRATION 迁移旧键），技能本体即可 JSON 化，"加一个技能=丢一个 JSON"。

**给 Colossus 判定帧的对照结论**：对照 `深挖__BOSS引擎调研__六样本共性模式.md` §2"没有任何样本做 JSON 数据驱动招式表"——Flan **多做了**这缺失的一半：它证明"能力/交互表用自定义 registry key + SimpleJsonResourceReloadListener + dispatch codec + required_mod 条件裁剪"在 MC 工程里长期可维护（六样本的招式表全是硬编码 static final，Flan 是全库少数把"可交互对象→语义"整层数据化的样本）。但它**少做了**另一半且结构性做不到：Flan 零 C→S 通道、纯服务端仲裁，没有任何"动画回传逻辑"的形态——判定帧仍必须走"服务端自驱计时 + 表现单向广播"（与 GeckoLib 无服务端时钟的既有结论一致），不能指望 Flan 给出动画耦合方案。

**做坏了的一处**：`common/.../api/permission/InteractionOverrideManager.java:96-112`（`getProjectileEntityInteract`）——首个投射物命中实体时，它对**全注册表每个 EntityType 创建一次 dummy 实体**并与每条 predicate 做笛卡尔匹配（`entrySet().stream().filter(... type.create(level, TRIGGERED) ...)`），异常路径里每失败一种实体就打一次 error 日志（106）；且第 99-100 行循环内重复取同一个 holder、外层已判 `unresolved()` 内层又逐条再判。这段自带注释"Prob overengineered"（29 行），复杂度 O(实体类型数×predicate 数) 且发生在游戏进行时首次命中帧——§7-4 的惰解析做对了，这里却又重又晚。次要不严谨：`Claim.java:354` 直接 `PermissionManager.getInstance().isGlobalPermission(perm)`，而 getInstance 文档自述"数据包未加载完前为 null"（PermissionManager.java:41-46），启动早期路径靠调用顺序侥幸。

---

**核对卡片差异汇总**：总行数 16,598（卡片 16,808）；Claim.java 1,043 行（卡片 1,044）；目标加载器仅 NeoForge+Fabric 两平台（卡片误列 Forge）；卡片"主类候选"挑中的是 7 行接口 ResolvableEntry，实际入口为 FlanFabric/FlanNeoForge；`generated/resources` 与 lang 文件缺失系稀疏检出所致。
