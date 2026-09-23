# Roots 源码分析报告

> 仓库根：`源码库/_参考仓库/_bulk/MysticMods__Roots`（MysticMods/Roots，v4.0.0.31-alpha）。除第 1、2 节外，下文 Java 路径一律省略 `src/main/java/mysticmods/roots/` 前缀；`仪式` = ritual，`灵木/林域` = Grove（下文保留英文 Grove，因它是专有名词）。本报告只覆盖本仓库实际读到的代码；本版本是 Roots 的 1.21.1 NeoForge 重写版（4.x），与老版 3.x（Forge 1.16/1.18）行为不同，凡未直接读到的一律标"未验证"。

## 1. 基本信息

- mod_id `roots`，显示名 Roots，作者 Noobanidus，版本 `4.0.0.31-alpha`，group `mysticmods.roots`（以上均出自 `gradle.properties:20-26`）
- 目标平台：MC 1.21.1 / NeoForge 21.1.249；区间 `minecraft_version_range=[1.21.1, 1.22)`、`neo_version_range=[21.1.200)`、`loader_version_range=[2,)`（`gradle.properties:10-14`）；无 Forge/Fabric 侧
- 许可证：MIT（`gradle.properties:22` 的 `mod_license=MIT`；`LICENSE.md:1-3` 为 MIT 正文，版权 2025 Noobanidus）。美术资源另有 `ASSET_LICENSE.md`（52 字节）与 `CREDITS.md`
- Java 21（`build.gradle:37` `java.toolchain.languageVersion = 21`，且 mixin 配置 `compatibilityLevel: JAVA_21`，`gradle.properties:35` 另有 `java_21=true`）
- Gradle 插件三个：`net.neoforged.moddev 2.0.107`（官方 NeoForge dev 插件，非 ForgeGradle/loom）、`org.moddedmc.wiki.toolkit 0.2.7`（发布 javadoc/wiki 站点，配置见 `build.gradle:300-304`，`docs/` 目录在本次检出中缺失）、`me.modmuss50.mod-publish-plugin 2.1.1`（CurseForge/Modrinth 发布，`curseforge.gradle` 9.9KB + `build.gradle:320-330` 用 `git log` 自动生成 changelog）
- 工程结构：单模块（`sourceSets { template {} }` 之外只有一个 main sourceSet，`build.gradle:115-120`）。`src/generated/resources` 作为 main 的资源目录参与编译；`src/template/java` 是**代码生成骨架**（见 §5）
- 编译依赖（都很轻）：JEI api（compileOnly + `localRuntime` 全量，故意不发布依赖，`build.gradle:164-167`）、Curios api（compileOnly）+ 全量（runtimeOnly）、Jade（compileOnly+implementation）、`auto-service-annotations` 1.0.1（annotationProcessor，仅 `test/decompose` 用到）、MixinExtras 0.3.6（`gradle.properties:28`）。**没有依赖任何自研前置库**
- 发布坐标：`publishing` 只写到本地 `file://$projectDir/repo`（`build.gradle:275-284`），版本 4.0.0.31-alpha、group `mysticmods.roots`、artifactId 即 `roots`（`base.archivesName = mod_id`，`build.gradle:33`）——addon 依赖它得自行取 jar

## 2. 源码规模与包结构

实测：`find src -name '*.java' | wc -l` = **957**（其中 `src/main/java` 955 个、`src/template/java` 2 个）；`find src -name '*.java' -print0 | xargs -0 cat | wc -l` = **85,552** 行，`src/main/java` 单独为 85,415 行。速览卡片写 86,509，差异应是统计口径（卡片按 `wc -l` 逐文件求和、含末行无换行的偏差）。

主要包（`src/main/java/mysticmods/roots/` 下，实测文件数）：

| 包 | 数 | 包 | 数 |
|---|---|---|---|
| api | 176 | recipe | 31 |
| client | 170 | item | 31 |
| network | 71 | init | 31 |
| mixin | 66 | gen | 30 |
| integration | 59 | spell | 29 |
| block | 31 | growth | 26 |
| util | 25 | action | 24 |
| inventory | 22 | ritual | 21 |
| blockentity / entity | 各 17 | event | 12 |

api 之下再分层（文件数）：`api/recipe` 23、`api/registry` 14、`api/attachment` 14、`api/modifier` 13、`api/herb` 12、`api/blockentity` 10、`api/test` 9、`api/grove` 8、`api/datamap` 8、`api/spell` 7、`api/condition` 7、`api/action` 6、`api/ritual` 4、`api/property` 4、`api/growth` 4——**约 1/5 的代码住在 `api` 包里**，这不是"接口层"而是"框架层"（注册表对象、Codec 数据结构、可被子类化的抽象基类全在里面）。

最大的 13 个文件：`gen/recipe/RootsRecipeProvider.java` 2560、`gen/loot/RootsLootTableProvider.java` 1243、`gen/lang/RootsLangProvider.java` 1132、`client/network/ClientFXHandlers.java` 1114、`api/RootsTags.java` 842、`client/gui/layer/HudOverlay.java` 718、`api/spell/Spell.java` 698、`blockentity/PyreBlockEntity.java` 683、`gen/neoforge/RootsDataMapProvider.java` 667、`client/RenderUtil.java` 633、`event/neoforge/EntityEventHandler.java` 584、`blockentity/FungalTransmuterBlockEntity.java` 571、`item/CastingItem.java` 568。**datagen 占据前三**，说明内容量主要靠代码生成而非 JSON 手写。

稀疏检出情况（重要）：`src/main/resources` 只剩 4 个文件（`roots.mixins.json`、`dev.mixins.json`、`META-INF/accesstransformer.cfg` 10 行、`META-INF/old_neoforge.mods.toml`），`src/generated/resources`（全部 datagen 产物：recipes/loot_tables/tags/data_maps/lang）**整目录缺失**；仓库根的 `data/modifiers.json`、`buildscripts/GenerateModifiers.groovy`、`docs/`、`gradlew`、`settings.gradle` 也不在检出内。因此本报告涉及的**所有 JSON 形状均从 Java 侧的 Codec 反推**，未见到成品文件的地方一律不猜格式。另有 `unused/items/groves/brief.txt` 一个占位文件。

## 3. 入口与注册

入口 `Roots.java:26-62`：`@Mod(RootsAPI.MODID)` 构造器把 25 个 `Mod*` 注册表类逐个 register 到 mod 总线，最后建 `PacketHandler` 并初始化 mod 兼容层。

```java
@Mod(RootsAPI.MODID)
public class Roots {
  public Roots(ModContainer container, IEventBus bus) {
    container.registerConfig(ModConfig.Type.COMMON, ConfigManager.COMMON_CONFIG);
    container.registerConfig(ModConfig.Type.CLIENT, ConfigManager.CLIENT_CONFIG);
    ModBlocks.register(bus); ModBlockEntities.register(bus); ModItems.register(bus);
    ModEffects.register(bus); ModHerbs.register(bus); ModConditions.register(bus);
    ModRituals.register(bus); ModSpells.register(bus); /* …音效/序列化器/配方/世界生成/战利品… */
    ModAttachments.register(bus); ModGroves.register(bus); ModActions.register(bus);
    packetHandler = new PacketHandler(bus);
    IntegrationUtil.init(bus);
} }
```

- 注册框架是**原生 NeoForge `DeferredRegister`**，无 Registrate/Lib 封装；`init/` 31 个文件即 25 个注册表类 + `ModTypes`/`P`/`ResolvedRecipes` 等辅助。
- 自定义注册表 18 个（`api/registry/RootsRegistries.java:24-46`，键声明在 `:50-68`），全部用 `new RegistryBuilder<>(Keys.X).sync(true).create()`——**注册表内容整体同步到客户端**，所以 ritual/spell/herb/grove 的 id 可以在客户端渲染 tooltip 与 JEI 时直接解析。
- 关键取舍：**"是什么"进注册表（Ritual/Spell/Herb/Grove/GroveAction/各种 Function 类型），"数值多大"进 Data Map（§5）**。例如 ritual 的类是 Java，duration/interval/radius 却从 `DataMaps.RITUAL_PROPERTY_DATA` 读回（`api/ritual/Ritual.java:123-140`）。
- 事件总线订阅点：25 个 `@EventBusSubscriber` 类，分三组——`event/neoforge/`（游戏总线：`EntityEventHandler` 584 行、`BlockEventHandler`、`ServerTickHandler`、`ActionEventsHandler`、`DataEventHandler`、`CommandsHandler`、`TooltipHandler`）、`event/mod/`+`event/setup/`（mod 总线：`RootsModEvents` 创造标签排序/实体属性、`CommonSetup`/`ClientSetup`）、`client/`（渲染/键位/HUD）。跨端 tick 收口在 `event/neoforge/ServerTickHandler.java:80-102`。
- 客户端入口独立：`RootsClient.java:11-15`（`@Mod(value=MODID, dist=CLIENT)`）只注册了配置界面扩展点，其余客户端逻辑靠 `@EventBusSubscriber(value=Dist.CLIENT)`。

## 4. 核心系统

### 4.1 Grove Power：可再生自然力的表示与限频（问题①）

表示：**没有全局资源池，也没有 SavedData**——全仓库 `SavedData` 只出现在 `api/IRootsAPI.java:83`（`readAdditionalSavedData(Entity, CompoundTag)`，是实体 NBT 的透传，不是世界数据）与 `api/recipe/ComplexEntityType.java:116`。自然力是**每个 Grove Stone 方块实体自己每 tick 重算出来的瞬时值**：

- `blockentity/GroveStoneBlockEntity.java:35-39` 四个 int 字段：`generatedLastTick/generatedThisTick/consumedLastTick/consumedThisTick`；`:312-327` 存 NBT 的就是这四个值——**没有跨 tick 累计的能量**，它是"功率"不是"电量"。
- 生成：`GroveStoneBlockEntity.java:200-247` 每 tick 遍历以方块为中心的长方体（半径按 stone 的 `RANK` blockstate 取配置：`:122-153`），对每个非空方块读 `state.getBlockHolder().getData(DataMaps.GROVE_POWER_GENERATORS)`（`:228`），累加 `generator.generate(...)`。
- 消耗：`:250-284` 从 `level.getData(ModAttachments.GROVE_CONSUMERS)`（一个 `util/SpatialMap.java:13-62` 的 section 哈希索引，消费者 BE 在 `onLoad()` 自增登记，如 `EnchantedTurfBlockEntity.java:89`）拿到半径内的消费者，逐个 `consumer.getTicketForTick(gameTime)` 并把本 tick 剩余功率塞进 ticket。
- 多 grove 分账：一张 ticket 里每个 `Consumer(tag,value)` 独立记账（`api/grove/PowerTicket.java:15,23-40`），`wasFullfilled()`（`:46-56`）要求**每一项都吃满**，否则该消费者这一 tick 视为未供电。这就是"一个方块同时需要 3 灵域之力才生效"的表达方式。
- 缓冲侧在消费者：`blockentity/FungalTransmuterBlockEntity.java:484-506` 把 ticket 已供应量累进 `storedPower`，并 `Math.min(storedPower, getMaxPower())` 截顶——**上限是硬顶，多余功率直接浪费**，配方启动时 `storedPower < recipe.getPower()` 就拒绝并 `displayClientMessage`（`:158-164`）。

限频防刷（三条正交闸门，全在数据侧）：
1. **同类方块计数上限**：`GrovePowerGenerator.java:84-108` 的 `BlockTracker` 对每种 block 只数到 `maxCount`，`:238-241` 超限的方块不产力。datagen 里给值极小——`gen/neoforge/RootsDataMapProvider.java:563-585`：FAIRY 生成器 2 个、FAIRY 小径 30 个、ELEMENTAL 2 个、FUNGAL 蘑菇 5/土 5/其它 8、PRIMAL 2、TWILIGHT 1。**围一圈 200 个花不涨功率，只按有效数量的前 N 个结算**，这是防刷的主闸门且它是纯 datapack 字段。
2. **对称性要求**：`GrovePowerGenerator.java:118-202` 的 `Symmetry` 枚举（NONE / RADIAL_SAME_BLOCK / RADIAL_SAME_BLOCK_OR_TAG / RADIAL_DIFFERENT_SAME_TAG / RADIAL_NOT_MATCHING）+ `getPairedPosition`（`:130-140` 关于中心点镜像）：`:234` 要求 `pos` 与其对径点同时满足 tag 条件才计数（例：ELEMENTAL 要"对径同 tag 不同方块"，TWILIGHT 要"对径**不**在同 tag"）。摆盘形状即配方。
3. **等级倍率**：`api/grove/GrovePowerGenerator.java:61-71` `generate()` 返回 `value * grove.getRank()`，而 rank 来自 stone 的 blockstate（`GroveStoneBlockEntity.java:291-294`），rank 又只能由声望决定：`tryActivating`（`:329-360`）里 `ReputationHelper.getRank(player, grove) > getRank()` 才把 ACTIVE/RANK 写进方块状态（`activate` `:362-374` 连写三格）。
- 供给是 tick 瞬时的，所以整体形如：**功率 = f(周围方块布局, 玩家等级)，需求 = 每 tick 各消费者的 ticket**，双方在同一 tick 内撮合，撮不上的自然不生效——没有"充值/提现"路径，也就没有可被刷的存量。

### 4.2 仪式：Ritual 注册表 + Pyre 方块实体 + Property Data Map（问题②）

数据结构：`api/ritual/Ritual.java:39-51` 抽象类，字段只有 `boundingBox/aabb/duration/radiusXZ/radiusY/interval`，`CODEC = RootsRegistries.RITUALS.byNameCodec()`（`:40`）——**序列化为一个 ResourceLocation**，注册表对象本身是 Java 单例。`ritual/` 21 个类，`init/ModRituals.java` 注册 22 项（含 `empty`/`crafting` 两个伪仪式）。

时间线怎么表达（对照 Occultism 的"单标量 currentTime"）：
- 状态存在 `blockentity/PyreBlockEntity.java:97-98`：`currentRitual`（注册表对象）+ `int lifetime`，存盘为 ritual 的注册表 key 字符串和 `lifetime` 整数（`:357-387`，读盘 `:392-435`）。
- 方向相反：Occultism 从 0 往上数到 duration；Roots 的 `lifetime` **初值 = duration 并每 tick 递减**（`PyreBlockEntity.java:255`、`:561`），再在 `Ritual.tick` 里换算成"剩余量"`dur = getDuration() - blockEntity.getLifetime()`（`api/ritual/Ritual.java:85-88`）传给 `functionalTick`。语义上等价，但注意 `functionalTick` 收到的 `duration` 实参是**剩余 tick**，而各仪式实现里却按"已过 tick"用（`ritual/OvergrowthRitual.java:63` `if (duration % interval == 0)`、`api/ritual/SingleTickRitual.java:15` 同样取模）——alpha 版本此处语义可疑，不作结论。
- **每仪式一个类，但数值全部数据化**：子类必须实现 5 个 `*Property()` getter（`Ritual.java:199-214`）返回 `ModRituals.X_DURATION` 等 `PropertyHolder`，`init()` 时用 holder 上的 `RITUAL_PROPERTY_DATA` data map 覆盖默认值（`Ritual.java:123-149`，随后 `rebuildBounds()`）。`init/ModRituals.java` 共声明 **117 个** `PropertyHolder`（`grep -c recordProperty`），每个自带中文可读的 comment 字符串，例如 `ModRituals.java:33-38` 给 animal_harvest 连 `looting_chance/stack_limit/glow_duration` 都开成可调项。
- 多阶段：**没有阶段概念**。一个仪式 = 一个 `functionalTick(level, pos, state, cache, be, remaining, random)`，靠 `interval` 取模分段执行；`SingleTickRitual`（`api/ritual/SingleTickRitual.java:13-20`）只是"到点执行一次"的糖。前置条件不是阶段而是**启动时一次性门**：`PyreBlockEntity.light()` 里 `checkConditions(...)`（`:210-215`，条件来自配方的 `level_conditions`/`player_conditions`，见 §5）与 `checkUnlocks(...)`（`:216-222`）任一失败即 `InteractionResult.FAIL`、不消耗任何东西。
- 生命周期钩子四个：`starts/stops/ends/removed`（`Ritual.java:69-83`），注释明确 `stops` 只在"不是立即重启"时调、`ends` 总是调、`removed` 只在 pyre 被破坏时调；实际调用点在 `PyreBlockEntity.stopRitual(boolean doLight)`（`:524-537`）与 `removed()`（`:608-615`）。
- 中断：浇水。手持含水容器右键正在进行的仪式 → `stopRitual(true)` 并扣掉水（`PyreBlockEntity.java:133-151`）；投掷水瓶熄祭坛是 `mixin/MixinThrownPotion$ExtinguishPyre.java`；配置 `ENABLE_EXTINGUISH_PYRE`（`config/ConfigManager.java:50`，注释里写明"右键铲子/喷溅水瓶"两种浇法）。
- 自动续期：`PyreBlockEntity.java:564-572`——`lifetime` 归零时若 `cachedRecipe == lastRecipe && matches(...)` 则 `stopRitual(false)`（不发 stops 钩子）后立刻 `light(lastPlayer)`，即"材料够就续一轮"。
- 仪式间冲突（Occultism 没有的维度）：`api/attachment/RitualInformation.java` 在**玩家 attachment** 上记两个 bool（`heavy_storms_active`/`protection_active`），并用配置项 `RITUAL_RESOLUTION_TYPE`（STORM_PRIORITY / PROTECTION_PRIORITY / AGE_PRIORITY）决定谁抢占天气（`:40-51`）。
- 未完成的部分要看清：`api/ritual/IRitualInstance.java:12` 顶着一句 `// TODO: Actually use this`；ritual modifier 有注册表、有成本 data map、有 tag、有 `RITUAL_MODIFIER_ICONS/RESTRICTED`，但**祭坛流程里没有任何地方读取 ritual modifier**（grep `RitualModifier` 在 `ritual/`、`blockentity/` 无命中）。此外 `gen/tags/RootsRitualTagsProvider.java:24-27` 把 GERMINATION 与 SPREADING_FOREST 标进 `roots:nyi`（Not Yet Implemented）、11 个仪式标进 `wip`——`ritual/GerminationRitual.java:19-22` 的 `functionalTick` 是**空方法**，`TooltipHandler.java:40-44` 会给这些仪式的名字加"未完成"提示。所以"数据驱动程度"评估要打折：形状完整，内容半空。

### 4.3 生长/催熟：GrowthRecord + randomTick 转发（问题③）

表示：两条 data map 挂在**方块注册表**上，键可以是具体方块也可以是 tag（`gen/neoforge/RootsDataMapProvider.java:252` 对 `RootsTags.Blocks.SPREADING_MUSHROOMS`、`:269` 对 `BlockTags.SAPLINGS` 生效）：
- `api/datamap/DataMaps.java:75` `GROWTH_RECORDS: Block -> GrowthRecord`，结构 `growth/GrowthRecord.java:24-28` = `(cropBlock, Optional<IntegerProperty> ageProperty, maximumAge, ticks, CanGrowFunction, LightFunction)`，完整 MapCodec 在 `:30-46`。`ticks` 是"每 N 次机会才长一次"的分母，`canGrowFunction`/`lightFunction` 是注册表里的函数类型（`api/registry/RootsRegistries.java:38-41` 四个 `CAN_GROW/LIGHT/CAN_HARVEST/HARVEST_FUNCTIONS` 注册表，24 个实现文件住在 `growth/growable|harvest|harvestable`，`growth/` 另 2 个文件是 record 本体）。
- 关键技巧在构造期解析 age 属性：`GrowthRecord.of(block, "age", ...)` 遍历 `cropBlock.defaultBlockState().getProperties()` 按名字找 IntegerProperty（`:50-68`），对原版 `CropBlock` 则用 accessor mixin 直接拿受保护的 `getAge()`（`:51-52`，`mixin/accessor/AccessorMixinCropBlock`）。于是**给任意 mod 的作物补一条生长规则=写一段 JSON**，只要那个方块有整数 age 属性。
- `growth/HarvestRecord.java:48-52` 同构（+ `Optional<Item> seedItem`），`:65-73` 会自动从 `CropBlock#getBaseSeedId()` 回补种子。文件头 `:33-47` 有一大段设计注释，列出"收获必须知道的六件事"，并说明掉落如何与战利品表/时运/精准采集共存。

求值时机：**事件/施法点求值，没有 tick 轮询器**。原版作物照样走原版随机 tick，Roots 的催熟只是"替玩家多 tick 几下"：
- 入口 `util/GrowthUtil.java:28-46` `growthTicks(level,pos,state,player)`：先查黑名单 tag `RootsTags.Blocks.GROWTH_BLACKLIST`（`:34-36`），再取 GrowthRecord，`record.canGrow(...)`（`growth/GrowthRecord.java:90-98`：光照函数 + 生长函数）通过则返回 `record.ticks()`，否则 -1。
- `spell/GrowthInfusionSpell.java:180-192`：咏唱每 `growthInterval` tick 一次，命中方块后 `if (pLevel.random.nextInt(doTicks) == 0) at.randomTick((ServerLevel) pLevel, pos, pLevel.random)`——**把催熟退化成"多给一次原版 randomTick"**，因此完全复用原版作物的生长条件/粒子/音效/掉落；副作用是"能催的作物"零适配。AOE 分支（`:95-161`）则是遍历包围盒挑 `count` 个可长方块做同样事，且按 `AOEGrowthMode` + `RAMPANT_GROWTH_EXCLUDE_MODE` tag + 副手作物 tag 过滤（`:121-127`）。
- 骨粉分支最省事：`:169-178` 命中 `GROWTH_INFUSION_FERTILIZER` modifier 时直接 `GrowthUtil.applyBoneMeal(boneMealCount, ...)`（`util/GrowthUtil.java:48-58`，内部就是循环 `BoneMealItem.applyBonemeal`），连语义都不重新实现。
- 保墒 modifier `tryMoisturizeGround`（`GrowthInfusionSpell.java:208-224`）向下最多找 3 格寻找带 `FarmBlock.MOISTURE` 的方块并 +1——把"生长加速的代价/前置"接回原版耕地湿度机制。
- 自定义植物走同一条路：mod 自己的作物（`block/crop/ThreeStageCropBlock`、`FourStageCropBlock` 等）也在 datagen 里注册 GrowthRecord/HarvestRecord，法术与仪式不区分原版/自定义。
- 收获侧 `util/HarvestUtil.java` 用一个 `@EventBusSubscriber` 的 `BlockDropsEvent`（`priority = HIGHEST`，`:84-85`）配合显式 `beginCapture()/endCapture()`（`:48-61`，重复开始直接抛 `IllegalStateException`）来截获掉落，再按 HarvestRecord 扣掉种子（`adjustOrCapture` `:67-73`）。**"改掉落"不靠覆写方块，靠一次性捕获窗口**，作用域清晰、不会串台。

### 4.4 GroveAction / Reputation：进度的数据化与防刷（问题①的"限频"侧面）

- 行为定义在 Java：`action/` 24 个 `GroveAction` 子类 + `init/ModActions.java` 注册 25 项。抽象基类 `api/action/GroveAction.java:19-40` 是 `Consumer<GroveContext>`，模板方法 `accept = validate → test → reward`；子类只写 `test(context)`（例：`action/CropGrowthAction.java:30-57` 判"age 变化且到达 maximumAge"）。
- 上下文是 record + 参数校验：`api/action/GroveContext.java:25-48` 声明 24 个 `Parameter`（`LEVEL/PLAYER/BLOCK_STATE/OLD_BLOCK_STATE/TARGET_ENTITY/RECIPE/DAMAGE/…`），`GroveAction.validate`（`:100-109`）缺参数直接抛 `NoSuchElementException`——**新行为接入忘传上下文会在开发期立刻炸**，不是静默失效。
- 奖励全在数据：`api/action/GroveAction.java:82-98` 遍历 `builtInRegistryHolder().getData(DataMaps.GROVE_ACTION_REPUTATIONS)`（`api/datamap/DataMaps.java:81`），每条 `GroveReputationEntry`（`api/action/GroveReputationEntry.java:19-25`）含 `(grove, name, reputation, unique, entries[])`，`SubEntry.type` 是 19 值枚举（`BLOCK/ITEM/EXACT_ITEM/TARGET_ENTITY/EXACT_RITUAL/SPELL/RECIPE/DAMAGE/DIMENSION/TOOL/ALWAYS…`，`:31-52`），运行期用 `context.is(type, name)` 反查（如 `CropGrowthAction.Context.is` `:84-91`）。datagen 侧 80 条 `GroveReputationEntry(...)`（`gen/neoforge/RootsDataMapProvider.java:341-487`，如 `:341` 的 cultivation_crop_growth 给 `(2,2,1,0,0)` 五档）。
- 三层限频防刷：
  1. `unique=true` 的一次性奖励——`api/attachment/ReputationStorage.java:72-81` 用 `UniqueReputation(groveId, name)` 集合去重，命中返回 0，不再涨。
  2. **按当前等级给不同额度**——`api/action/GroveReputation.java:9-15` 每条奖励是 `(gain1..gain5)` 五元组，`ReputationStorage.adjust` 调 `byIndex(rank)`（`:84-87`、`GroveReputation.byIndex` `:39-47`）：同一件重复行为在低等级给得多、高等级给得少（多数条目后面几档写 0）。
  3. 冷却在别处（法术侧）：`api/attachment/CooldownStorage.java:30-31` 两张 `Spell→int` 表（剩余 + 最大值，用于画条），`tick(entity)` 每 tick 自减并在归零时同时清两张表（`:97-105`）。
- 等级门槛是纯函数：`api/grove/ReputationRanks.java:23-101`（`threshold1..4` 四阈值 + `getProgress` 返回 `(rank, progress, nextRank, total)` 供 HUD 画进度条），阈值本身也可被 datapack 换掉（`DataMaps.java:85` `GROVE_RANKS`，默认 `(1000,5000,15000,30000)` 写在 `api/grove/Grove.java:26`）。
- 反刷还有一条硬规则：`GroveAction.getReputationEntries()` 找不到 data 时把 `skipped=true` 并 `LOG.error`（`:82-95`），此后该 action 整体短路——**数据缺失时选择"不给奖励 + 大声报错"，不是"给默认值"**。

### 4.5 法术 / SpellModifier 树 / SpellInstance：功法可数据化的部分（问题⑥素材）

- 法术也是注册表单例（25 个，`init/ModSpells.java`，113 个 `PropertyHolder`），但注册方式更工程化：`REGISTER.register(path, () -> new AquaBubbleSpell(new Spell.Properties(...)  .type(Cast.INSTANT).charge(Charge.INSTANCE).cost(() -> ModHerbs.DEWGONIA, SpellCosts.BASE_0250).cooldown(PROP).radius(...).properties(P1,P2,...).build()))`（`init/ModSpells.java:55-75`）。`Properties` 收 5 类信息：表现（cast/charge 类型、两档颜色）、成本（`CostInstance` 惰性 supplier）、属性键（`properties(...)` 声明"本法术拥有哪些可调数值"）。
- 成本是**带类型的加乘链**：`api/herb/Cost.java:14-19` = `(CostType, Holder<Herb>, double)`，`CostType` 有 `ADDITIVE / MULTIPLICATIVE_BASE / MULTIPLICATIVE_TOTAL / NEGATE_BASE_COST`，并有 `Cost.negate(cost)`（`:60-67`）用来"抵消基础消耗"。可叠加成本由 `AdvancedDataMapType` 的自定义 merger 完成：`api/datamap/DataMaps.java:47-53` + `:175-181`（`costMerger()` 把两份 `CostInstance` 的 list 拼接）。于是"给某法术加一项消耗/删一项消耗/整体打折"都是 datapack 动作，`CostRemover`（`api/datamap/CostRemover.java`）就是删除侧的 record。
- 玩家"学会的构筑"存在**物品数据组件**里：`api/datacomponent/SpellInstance.java:28-47` = `(UUID spellId, int slot, Spell spell, SpellModifierSet enabledModifiers, PatchedDataComponentMap data)`——最后一项是**每份法术实例自己的组件补丁包**，用 `PatchedDataComponentMap.fromPatch(spell.getComponents(), patch)` 叠加在法术模板默认组件之上（`:53-62`）。法杖持有 `SpellStorage(currentSlot, maxSlot, List<SpellInstance>)`（`api/datacomponent/SpellStorage.java:20-35`，5 格），两者都有 CODEC+STREAM_CODEC，注册在 `init/ModAttachments.java:86-89` 的 `COMPONENTS`。
- 构筑合法性靠**修饰符树**：`api/modifier/ModifierTree.java:20-38` 为每个 spell/ritual 建一棵节点树（parent/conflict/group/depth），`ModifierTrees.java:7-49` 静态缓存 + `initialize()`；重建时机是注册表 bake 回调：`event/neoforge/DataEventHandler.java:40-44` `modifyRegistries` 给 `SPELL_MODIFIERS` 注册 registry 挂 `BakeCallback → ModifierTrees.initialize()`——**依赖注册表已冻结并同步，再一次性构图**，不用 lazy 遍历。
- 求值时不复制数据：`Spell` 自己只按 modifier 集合现算属性（`api/spell/Spell.java` 的 `layeredProperties`，`getCooldown/getReach/getMaxUse` 接受 `ISpellInstance`），描述文案也是运行期把数值格式化进 lang（`spell/GrowthInfusionSpell.java:270-326` 的 `getOrCreateDescriptionComponents`/`createModifierDescriptionComponents` 返回 `Component[]` 填空 `%s`）。
- 施法消耗结算在 `api/herb/Costing.java`：构造时把 `Charge.Condition.ALWAYS` 的 modifier 无条件记账（`:53-62`），`canAfford` 先 `calculateCosts(...)` 再用 `HerbStorage.drain(herb, value, simulate=true)` 试扣（`:105-127`），不够时回落到扫描真实背包/腰包（`api/herb/HerbMap.java:26-75`，遍历主背包 + 每个 item 的 `Capabilities.ItemHandler.ITEM` + Curios 腰带，记录 `HerbEntryType.INVENTORY/CAPABILITY/CURIOS_CAPABILITY` 与槽位），最后由 `Costing` 精确扣除对应槽位的物品。`Costing.noCharge()`/`operations(n)`（`:71-89`）是法术体交给框架的"这一 tick 我干了什么"信号，`CastResult.tickFromCosting(...)`（`spell/GrowthInfusionSpell.java:205`）据此算冷却——**"是否计费/计几次"由效果自己声明，不由框架猜**。

### 4.6 状态存放与跨端流转总表

| 状态 | 存在哪 | 序列化 | 到客户端的方式 |
|---|---|---|---|
| Grove 功率 | `GroveStoneBlockEntity` 4 个 int | `saveAdditional`（`blockentity/GroveStoneBlockEntity.java:312-327`） | `updateViaState()` → `ClientboundBlockEntityDataPacket` 广播半径 64（`blockentity/template/BaseBlockEntity.java:35-44`），每 tick 都发（`:97-101` 的变化检测被注释掉了） |
| Grove 消费者索引 | 世界 attachment `ModAttachments.GROVE_CONSUMERS`（`init/ModAttachments.java:62-63`，无 serialize） | 不存盘 | 不需要——BE `onLoad()` 自己登记 |
| 祭坛/仪式 | `PyreBlockEntity`（ritual key + lifetime + inventory + storedItems + last_player UUID，`:357-435`） | NBT；配方只存 id 字符串、加载时惰性解析（`cachedRecipeId` `:389-390`、`init/ResolvedRecipes.java`） | 同上 BE 包 |
| 玩家进度 | attachment：`REPUTATION_STORAGE`/`HERB_STORAGE`/`GRANT_STORAGE`/`COOLDOWN_STORAGE`/`RITUAL_INFORMATION`（`init/ModAttachments.java:45-61`，均 `.serialize(CODEC)`，多数 `.copyOnDeath()`） | Codec | `ServerTickHandler.java:80-102` 每 tick 末 `AttachmentUtil.monitorAndSync(...)`：dirty 才发包（`api/attachment/AttachmentUtil.java:20-50`），实体/BE 版另有半径 64 广播（`:53-63`） |
| 法术构筑 | 物品数据组件 `SPELL_STORAGE`/`SPELL_SLOT` | CODEC + STREAM_CODEC | 随 ItemStack 组件天然同步 |
| 表现（粒子/音效/屏幕） | 不存 | — | 40+ 个 `*FXPacket`（`network/PacketHandler.java:70-119`），纯单向 |

`ICleanable` + `isDirty()` 是这套 attachment 同步的支点：`ReputationStorage.setDirty`（`api/attachment/ReputationStorage.java:128-133`）、`CooldownStorage.tick` 每 tick 置 dirty（`:97-105`）；`monitorForChange` 检测 dirty 后**回写一份 `copy()`** 再清标志，从而把"服务端 mutation → 精准增量同步"收敛成一个 30 行工具方法。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/` 71 文件，`network/PacketHandler.java:37-42` 在 `RegisterPayloadHandlersEvent` 里拿 `event.registrar("4.0.0.0").executesOn(HandlerThread.MAIN)`，再分 `registerClientToServer`（16 个 `Serverbound*Packet`）/`registerServerToClient`（53 个，其中 `network/client/fx/` 的 34 个文件是纯表现包），两者共用一个 `PacketRegistrar` 包装（`:121-130`，按方向把 handler 统一指到 `IRootsPacket::handle`）。每个 payload 是 `TYPE + CODEC`（`StreamCodec<RegistryFriendlyByteBuf, ?>`）成对，包体本身多为 record。attachment 同步专用一族在 `network/client/attachment/`（Herb/Grant/Reputation/Cooldown/DiscardEntity/DiscardBlockEntity）——**discard 包**用于 attachment 清空时通知客户端删数据（`api/IRootsAPI.java:67-69` 暴露构造口）。
- 数据驱动分三层，覆盖面从大到小：
  1. **配方**：8 种自定义 `RecipeType`（`init/ModRecipes.java:22-29`），每种 `MapCodec`+`StreamCodec`+`Serializer` 三件套。公共骨架 `api/recipe/BaseRecipeData.java:34-56`：`ingredients / level_conditions / player_conditions / result / chance_outputs / unlocks / power_requirements / priority`，全部 `optionalFieldOf(..., 空)`，所以 JSON 可以只写用到的字段。`recipe/pyre/PyreRecipe.java:27-35` = `BaseRecipeData` + 可选 `ritual`（注册表 byNameCodec），因此"新仪式配方"完全可以是 JSON——前提是那个 Ritual 已在 Java 里注册。配方匹配的排序与缓存自研：`api/recipe/type/ResolvingRecipeType.java:19-49`（按 `namespace` 再按 `getPriority()` 排序、`getRecipes` 缓存），`init/ResolvedRecipes.java:31-41` 声明 8 个实例并带一个"解析器"函数（Pyre 用 `PyreRecipe::getRitual`、Mortar 用首条 `SpellUnlock`），reload 时 `apply()` 只 `reset()`（`:68-74`）。它继承 `SimpleJsonResourceReloadListener` 但不读文件，纯粹借用 reload 生命周期当失效钩子。
  2. **Data Map**：30 个（`api/datamap/DataMaps.java:39-165`，逐个在 `event/neoforge/DataEventHandler.java:46-77` 注册），覆盖 Block/Item/EntityType/Attribute/Grove/GroveAction/Spell/SpellModifier/Ritual/RitualModifier/Level 十来个注册表；多数 `.synced(CODEC, true)`，需要并集的用 `AdvancedDataMapType + DataMapValueMerger.listMerger()` 或自定义 `costMerger()`。这是本项目最主要的"整合包可改面"。
  3. **注册表对象本体**（Ritual/Spell/Herb/Grove/各种 Function）：**必须写 Java**，JSON 只能改其 data map 与 tag。
- 条件系统：`ILevelCondition`/`IPlayerCondition` 各有注册表（`api/registry/RootsRegistries.java:33-34`），实现 6 个（`condition/GroveStoneCondition`（要求某系 grove stone 处于 ACTIVE）、`PillarCondition`（要求 N 根符文柱）、`BlockStatePropertyCondition`、`FluidSourcePropertyCondition`、`OvergrowthCondition`、`GroveRankReputation`），全部 `Type::new` 注册（`init/ModConditions.java:26-30` 与 `:80`）。方块状态匹配复用 `api/test/world/`（`BlockMatchWorldTest`/`TagMatchWorldTest`/`PartialBlockStateMatchWorldTest`，注册见 `init/ModTests.java:17-28`）——**同一套 world-test 结构既给配方条件用，也给战利品函数用**，`api/test` 9 个文件 + `loot/` 11 个文件。
- 配置：`config/ConfigManager.java` 307 行，单个 COMMON + 单个 CLIENT 的 `ModConfigSpec`（`Roots.java:31-32`），约 61 项（`grep -c 'public static final ModConfigSpec'`），全是"边界与开关"而非数值平衡：三轴范围 `GROVE_STONE_POWER_RANGE_X/Y/Z`（`:66-68`）、四档 grove bounds（`:54-65`）、`PYRE_BOUNDS_*`（`:44-46`）、`ENCHANTED_TURF_TICKS`（`:52`）、`UNDERWATER_BONE_MEAL_WILD_ROOTS_CHANCE`（`:77`）、`RITUAL_RESOLUTION_TYPE`（枚举型配置，`:88`）、一堆 `DEBUG_*`。分工明确：**能进 datapack 的不进 config，config 只放 datapack 放不下的东西（包围盒大小、调试开关、冲突仲裁策略）**。
- datagen：`gen/RootsDataGenerators.java` 一个 `@EventBusSubscriber` 的 `GatherDataEvent` 处理器，跑 29 个 provider 类（`gen/` 共 30 文件：recipe/loot/lang/tags×17/client×5/advancement/nbt/neoforge×2）。运行配置在 `build.gradle:78-86` 的 `runs.data`，输出到 `src/generated/resources`、`--existing src/main/resources`，产物**作为 main 的资源目录参与构建**（`build.gradle:120`）。
  - 最有价值的一点：datagen **把 Java 里的默认值原样导出成 data map JSON**，让 datapack 成为唯一的事实来源。`gen/neoforge/RootsDataMapProvider.java:49-95` 遍历注册表流，对每个 Spell/Ritual/SpellModifier 写 `new PropertyDataMap(x.getProperties())`、对每个 spell 写 `x.getDefaultCosts()`；`PropertyDataMap.CODEC` 用的是 `PropertyHolder.FULL_CODEC`（`api/datamap/PropertyDataMap.java:17`），而 `FULL_CODEC` 会把 `default_value + comment + value` 三个字段都写全（如 `api/property/Property.java:115-122` IntegerProperty 的 `FULL_CODEC`），所以产出的 JSON 自带中文可读注释，作者改数即改 `value`。
  - `PropertyDataMap` 构造器校验重复 id 抛 `IllegalArgumentException`（`api/datamap/PropertyDataMap.java:20-29`），`get(holder)` 在缺键时抛 `IllegalStateException`（`:31-44`）——**配漏一项会炸，不会静默用默认值**。
  - `init/P.java` 是反向校验：所有 `recordProperty(...)` 登记进静态集合，`P.unclaimed()`（`:53-79`）用 `SPELLS/RITUALS` 的 `getProperties()` 做集合差，`event/setup/CommonSetup.java:24-27` 在 `FMLCommonSetupEvent` 里对差集逐条 `LOG.error("Unclaimed property: {}")`。**"声明了却没人用的数值"在启动日志里可见**。
  - 图鉴/文档自动化程度（问题④）：**没有 Patchouli/Jade 书页/KubeJS/CraftTweaker**（全仓 grep `patchouli|kubejs|crafttweaker` 零命中；Jade 仅在依赖里出现，代码侧未见）。`integration/` 59 个文件里 54 个是 JEI（余 5 个：`IntegrationUtil`/`ClientIntegrationUtil` + `curios/` 3 个）：`integration/jei/RootsJEIPlugin.java` + `categories/` 15 个文件（Pyre/Grove/GrovePower/Mortar/Knife/RunicBlock/RunicEntity/AnimalHarvest/FungalTransmuter/SproutGift/SummonCreatures/GroveWithReputation/EntityInteraction + 基类 `RootsRecipeBaseCategory` + `WorldRecipeUtil`）+ `ingredient/` 7 类自定义 ingredient 类型（block/entity/grove/damage/dimension/ritual/spell，每类 helper+renderer 成对，grove 一类就有 8 个文件）+ `widget/` 8 个（`GrovePowerWidget`/`SymmetryWidget`/`LevelConditionWidget`/`PlayerConditionWidget`/`CooldownWidget`/`DurabilityWidget`/`WorldTestWidget`/`InfoWidget`）。这些页面**直接读注册表与 data map**，因此不需要第二套文档源：`GrovePowerRecipe`（`recipe/fake/GrovePowerRecipe.java:28-36`）是一个只给 JEI 显示的"假配方"record（block_tag + grove + power + symmetry + amount），由数据 map 聚合出来；`recipe/fake/` 共 5 个这种投影型 record（另 4 个是 `GroveWithReputation`/`SproutGiftRecipe`/`EntityInteractionRecipe`/`DyeRecipeGenerator`）。
  - 语言文件同理：`gen/lang/RootsLangProvider.java` 1132 行，前段是手写的界面/消息文案，后段用注册表自动生成键名——`RootsRegistries.GROVE_ACTIONS/SPELLS/RITUALS/HERBS/SPELL_MODIFIERS.entrySet().forEach(o -> add(o.getDescriptionId(), toEnglishName(path)))`（`:215-241`），键由 registry path 反推英文（`roots.spell.growth_infusion` → "Growth Infusion"）；手写部分只补描述模板，如 `:925-1004` 的 `spellDescription(...)`/`spellExtendedDescription(...)`，其中的 `%s` 占位由 §4.5 的 `createExtendedDescriptionComponents()` 在运行期填入实际数值。**即：数值只有一份真值（data map），文案里的数字是格式化出来的，不会写死两遍。**

## 6. Mixin

配置两份：`src/main/resources/roots.mixins.json`（主，`mixins` 44 项 + `client` 19 项）与 `dev.mixins.json`（开发期专用，`requiredMods=["noobanidusdev"]`，只 2 项，见 `src/template/resources/META-INF/neoforge.mods.toml` 的两个 `[[mixins]]` 段）。`compatibilityLevel JAVA_21`、`mixinextras.minVersion 0.5.0`（用了 MixinExtras 的 `@WrapOperation`/`@Local` sugar）。66 个 mixin 文件 / 955 个 java ≈ 7%，比例克制。

三类用途：
- **`mixin/action/Mixin*` 11 个：把原版行为翻成 GroveAction**。统一形状是 `@WrapOperation` 原版方法内的某个副作用调用，先 `original.call(...)` 再构造 Context 交给 action（`mixin/action/MixinBoneMealItem$GrowAction.java:23-42`：包 `BonemealableBlock.performBonemeal`，用 `@Local(argsOnly=true)` 取 stack/level/pos/player、`@Local` 取原始 BlockState，事后按 `MushroomBlock` 追发 `GROW_HUGE_MUSHROOM`）；`mixin/action/MixinComposterBlock$CompostAction.java:18-32` 包 `ItemStack.consume`，在 `original.call` **之前**发 `FILL_COMPOST`。命名约定 `Mixin宿主$具体用途` 让一个宿主类被多个小 mixin 分片复用。
- **行为补丁**：`MixinBoneMealItem.java:20-38`（`@WrapOperation method="growWaterPlant"` 包 `BlockState.canSurvive`，按配置概率在清水里种 mossy wild roots）、`MixinThrownPotion$ExtinguishPyre`（摔水瓶浇祭坛）、`MixinBeehiveBlock$RunicShears`、`MixinBrewingStandBlockEntity`+`MixinBrewingStandMenu$FuelSlot`（ brewing 燃料）、`MixinServerPlayerGameMode`、`MixinWitherBoss$Geas`、`MixinAbstractArrow`/`MixinProjectileWeaponItem$WildwoodQuiver`（箭袋）、`MixinMerchantMenu$FairyHutTemporary`、`MixinPlayer$LightDrifter/IncreaseItemBoundingBox`、client 侧 `MixinLocalPlayer$StaffChannel`（咏唱）、`MixinGui$Tome`、`MixinMouseHandler/MixinPlayerRenderer/MixinCapeLayer/MixinAbstractClientPlayer$LightDrifter`（"出神"移动接管）。
- **accessor 30 个**（`mixin/accessor/` 20 + `mixin/client/accessor/` 10）：`accessor/AccessorMixinCropBlock`（`roots$CallGetAgeProperty`/`roots$CallGetBaseSeedId`，被 `growth/GrowthRecord.java:51`、`growth/HarvestRecord.java:65-72` 用来给原版作物建 record）、`AccessorMixinGrowingPlantBlock`、`AccessorMixinZombieVillager`（Purity 仪式减转化时间）、`AccessorMixinGoat`、`AccessorMixinMob`、`AccessorMixinEntity`（`roots$ReadAdditionalSaveData`，被 `impl/RootsAPIImpl.java:184-186` 暴露成 API）、以及一整套 loot 结构 accessor（`LootTable/LootPool/LootItem/CompositeEntryBase/NestedLootTable/BlockLootSubProvider/TagEntry`）——它们服务于 `test/decompose/` 的战利品表分解比对（`@AutoService` 注册 decomposer），配合 datagen 校验生成物是否偏离预期。
- AT 只有 10 行且全是 client 粒子/渲染字段（`src/main/resources/META-INF/accesstransformer.cfg:1-10`）——能 mixin 就不 AT，能 accessor 不 public。

## 7. 值得学的 5 条

1. **"功率不是电量"的可再生资源模型**（`blockentity/GroveStoneBlockEntity.java:200-284` + `api/grove/GrovePowerGenerator.java:61-108`）：每 tick 从世界现算供给、当 tick 撮合需求，消费者各自带一个截顶缓冲（`blockentity/FungalTransmuterBlockEntity.java:484-506`）。值得抄的原因：**没有可累积的存量，就没有可被刷的存量**；防刷靠 `maxCount`（同类方块只数前 N 个）与 `Symmetry`（对径形状匹配）两个 datapack 字段，调平衡不碰代码。求仙问道的"灵力循环"直接可以套这个形状：灵脉/洞天每 tick 由周围灵气方块现算，弟子洞府各自带容量上限。
2. **`PropertyHolder` + data map 的"Java 声明数值、datapack 拥有数值"**（`api/property/PropertyHolder.java:12-25`、`api/datamap/PropertyDataMap.java:17-44`、`gen/neoforge/RootsDataMapProvider.java:82-95`）：每个可调项是一个带 comment 的 `(id, default)` record，默认值由 datagen 导出成 JSON（FULL_CODEC 把 default/comment/value 都写出来），运行期 `Ritual.init` 从 data map 读回（`api/ritual/Ritual.java:123-149`）；缺键抛异常、重复键抛异常、声明未使用启动日志报错（`init/P.java:53-79` + `event/setup/CommonSetup.java:24-27`）。值得抄的原因：这解决了 Ars Nouveau 路线的短板（数值在 TOML、内容在 Java，两边都不能纯数据改），且**三道校验把"漏配"变成编译期/启动期错误**。
3. **催熟 = 转发一次原版 `randomTick`，概率分母来自数据**（`spell/GrowthInfusionSpell.java:180-192` + `util/GrowthUtil.java:28-46` + `growth/GrowthRecord.java:50-68`）：不自己实现长.age()、不长成就、不掉落的三条路径，只按 `GrowthRecord.ticks` 做 `random.nextInt(doTicks)==0` 的门并调 `state.randomTick(serverLevel, pos, random)`；同时有 `GROWTH_BLACKLIST` tag 兜底、有 `applyBoneMeal` 直连原版骨粉分支（`util/GrowthUtil.java:48-58`）、有把副作用写回原版耕地湿度的 modifier（`spell/GrowthInfusionSpell.java:208-224`）。值得抄的原因：**与任意 mod 的作物零适配兼容**，且"某作物吃不吃催熟"变成一个 JSON 字段。
4. **`GroveAction` 的"参数缺失即炸 + 数据缺失即停并报错"**（`api/action/GroveAction.java:100-109`、`:82-98`）：`GroveContext.Parameter` 常量表（`api/action/GroveContext.java:25-48`）声明每个行为需要哪些上下文，`validate` 用 `NoSuchElementException` 把关；`accept` 模板方法把 `test/reward/log` 固定成统一流程，子类只剩 `test`。值得抄的原因：修仙 mod 的"善缘/功德/因果"类进度系统最大的坑就是"接了新行为忘了传上下文"和"配了行为没配奖励"，这两处都被显式化。
5. **注册表 bake 回调构图 + dirty 驱动的 attachment 增量同步**（`event/neoforge/DataEventHandler.java:40-44` 的 `ModifyRegistriesEvent` + `BakeCallback → ModifierTrees.initialize()`；`event/neoforge/ServerTickHandler.java:80-102` + `api/attachment/AttachmentUtil.java:20-50` 的 `monitorAndSync`）：值得抄的原因——前者把"依赖全量注册表的派生结构（树/索引/图）"放在注册表冻结点建一次，避免 lazy 构建期的空引用；后者用一个 `ICleanable.isDirty()` 约定替代每个 storage 自己写发包逻辑，服务端 tick 末尾统一扫一遍，且 `copy()` 快照防客户端看到中途态。这两条与加载器无关，Forge 1.20.1 侧对应 `RegistryEvent.Freeze`/手动 sync。

## 8. 公开 API（Roots 有 addon/KubeJS 面向，若有扩展点就写）

- 入口包 `mysticmods.roots.api`（176 文件）。门面 `api/RootsAPI.java:70-81`：`getInstance()` 用 `ServiceLoader.load(IRootsAPI.class, Roots.class.getClassLoader()).findFirst()` 拿实现，拿不到直接 `IllegalStateException`——**接口与实现分离，实现（`impl/RootsAPIImpl.java`）在 `api` 包外**，`api` 包因此可以单独作为 compileOnly 依赖分发（不过 `publishing` 未拆 API jar，见 §1）。
- 契约接口 `api/IRootsAPI.java:37-89`：`unlock/canUnlock`（法术/修饰符学习）、`grant(player, grove, id, GroveReputation, unique)`（外部给声望，附带的 `syncHerbs`）、`getCurios/getPouches/getTome`（跨容器取物品）、`getCostReduction/getCooldownReduction`（读自有 Attribute）、`getEntityDiscardPacket/getBlockEntityDiscardPacket`（外部自定义 attachment 也能复用 discard 协议）、`getCooldownStorageType/getGrantStorageType/getAugmentationInfoType/getDeletableType/getModifiableType`（**把私有 attachment/data component 类型作为值暴露出去**，addon 不必反射）、`readAdditionalSavedData(Entity, tag)`（用 accessor mixin 帮 addon 重放实体 NBT 读取）、`getRestrictedTagFor/getRequiresUnlockTagFor`（把"哪些修饰符被禁用/需要解锁"的 tag 命名约定开放为查询）。
- 注册表访问 `api/registry/RootsRegistries.java:24-68`：18 个注册表及其 `Keys`，全 `.sync(true)`。扩展方式=在 mod 构造器用 `DeferredRegister.create(RootsRegistries.Keys.RITUALS/SPELLS/HERBS/GROVES/GROVE_ACTIONS/… , MODID)` 注册自己的对象——与主模组自注册完全同一入口（`init/ModRituals.java:17-18` 就是这么写的）。
- 可子类化的扩展点：`Ritual`（`api/ritual/Ritual.java:39`，5 个抽象 getter + `functionalTick`/`initialize` + 可选 `starts/stops/ends/removed/getPredicates/providesLight`）、`Spell`（`api/spell/Spell.java:49`）、`GroveAction`（`api/action/GroveAction.java:19`）、四个生长函数接口（`api/growth/CanGrowFunction|LightFunction|CanHarvestFunction|HarvestFunction`，每个都是 `@FunctionalInterface`，例 `api/growth/CanGrowFunction.java:11-13`）、`ILevelCondition/IPlayerCondition` + 其 `*Type`、`WorldTestType/EntityTestType`、`PropertySerializer/PropertyType`（新数值类型也能开放）、`SnapshotType`、`GrovePowerGenerator`（`api/grove/GrovePowerGenerator.java:34-41`，允许自定义"生成器/消耗器"实现——但注意目前只有 `Congen` 两种 record 被 data map 消费）。
- 数据侧扩展（不需要 Java）：任何 addon 的方块都可以通过 datapack 的 `roots:growth_records`/`roots:harvest_records`/`roots:grove_power_generator`/`roots:herb_item_data`/`roots:spell_property_data`/`roots:ritual_property_data`/`roots:grove_action_reputations` 被 Roots 的机制接管——**这是比"注册新内容"更强的扩展面**：一个第三方农业 mod 不加一行代码就能被 Roots 的催熟/收获/灵域系统识别。
- 未发现的东西（据实记录）：无 KubeJS/CraftTweaker/ProbeJS 集成、无 in-game 书本（`Roots.java:16` 有一条 TODO 指向外部 wiki mod "Oracle Index"）、无 GameTest 类（`gradle.properties`/`build.gradle` 有 `gameTestServer` run 与 `neoforge.enabledGameTestNamespaces`，但 `src/main/java` 内未见 gametest 注解，`test/` 包是 loot-table 分解比对工具而非游戏内测试）、无 `META-INF/services/...IRootsAPI` 文件（该服务声明文件应随 `src/generated`/resources 一起被裁掉了——**未验证**其生成方式）。

## 附：对「求仙问道」的结论（问题⑤⑥）

数据化程度评估（问题⑤）：
- **加一个新仪式** = Java 侧 3 处：①`ritual/` 一个子类（最薄的壳子 46-48 行，`ritual/SpreadingForestRitual.java`、`ritual/GerminationRitual.java`；真正有逻辑的 80-138 行，`ritual/OvergrowthRitual.java` 138 行）；②`init/ModRituals.java` 加 1 行 register + N 行 `P.recordProperty`（现在 22 个仪式对应 117 条属性）；③一个 ritual token item 在 `init/ModItems.java`（`RITUAL_GERMINATION` 之类，一行）。**配方可以纯 datapack**（`recipe/pyre/PyreRecipe` 的 `ritual` 字段就是注册表 id + `BaseRecipeData`），**数值可以纯 datapack**（`ritual_property_data`），**分类/提示可以纯 tag**（`roots:rituals/cultivation`）。所以"新增一门已存在语义的功法变体"= 零 Java；"新增一种从未有过的功法效果"= 一个类。
- **加一个新效果（法术侧）**：同形状，`spell/` 一个 `Spell` 子类（最薄 37-56 行）+ `init/ModSpells.java` 一行 register 与若干 `recordProperty`（25 个法术 / 113 条属性）。但**表现层与描述是代码**：`createExtendedDescriptionComponents()` 返回 `Component[]`（`spell/GrowthInfusionSpell.java:320-326`）、Lang 里的描述模板手写（`gen/lang/RootsLangProvider.java:925-1004`）、粒子/音效要写 handler（`client/network/ClientFXHandlers.java` 1114 行）。这两处是 Roots 数据化的真实天花板。
- 结论：Roots 的数据化是**"数值+条件+分类+成本"全数据、"语义+表现"全代码**，且它比 Ars Nouveau 路线多做了一件关键的事——**用 data map 把数值从 Java 里搬进 JSON，再用 datagen 把 JSON 和 Java 默认值保持同源**。
- 与 Occultism 的对照收口（问题②）：Occultism 的时间线是 `currentTime` 单标量 + 15 个子类无一覆盖 `update()`；Roots 是 `lifetime` 单标量 + 21 个子类**全都**只覆盖 `functionalTick`。所以两者在"多阶段"上同样贫瘠——Roots 也没有阶段机，它靠 `interval` 取模 + `PositionCache`（`util/PositionCache.java:88-106` 每 tick 重建 predicate→命中索引的映射）+ 启动前一次性 conditions/unlocks 把复杂度推到数据和外部机制上。真正的差异在别处：**Occultism 仪式失败靠"回滚已吞材料"，Roots 仪式失败根本不发生**（`PyreBlockEntity.java:210-222` 条件不过就 FAIL、材料不动），并且 Roots 把"仪式之间互相冲突"上升成显式仲裁配置（`api/attachment/RitualInformation.java:40-51`）。求仙问道若打算做"多阶段大阵/需要维护的持续法阵"，可抄 Roots 的续期与中断语义（`:564-572` 自动续 + `:133-151` 浇水打断），阶段机得自己补——这条路上库里目前三个样本（Occultism / Roots / Ars 的 ritual）都没给出形状。

可搬的两条（问题⑥）：
1. **灵力循环 = Grove Power 的形状**：每 tick 由"周围方块 + 玩家境界(rank) + 布局对称性"现算供给，不做全局池、不做存量；消耗方各自声明 `TicketDefinition(requests[(tag→amount)…])`，全满足才算"供电成功"（`api/grove/PowerTicket.java:23-56`），并把剩余塞进带硬上限的个人缓冲。限频三闸门照抄（`maxCount` 同类计数上限 / 对称性 / rank 倍率），配一条黑名单 tag（`util/GrowthUtil.java:34-36`）作为逃生门。这套东西不需要 SavedData、不需要世界属性，跨维度天然分账（attachment 挂在 Level 上，`init/ModAttachments.java:62`）。
2. **功法可再生 = PropertyHolder + data map + 三校验**：每门功法在 Java 里是"语义类"，其全部数值是 `(id, default, comment)` 列表；datagen 把默认值导出为 JSON，datapack 改 JSON；缺键/重复键/未使用键三种错误分别用异常、异常、启动日志暴露（`api/datamap/PropertyDataMap.java:20-44`、`init/P.java:53-79`）。配合 §4.4 的"同一行为在不同境界给不同额度"（`api/action/GroveReputation.java:9-15` 的五档数组）与 `unique` 一次性奖励，正好覆盖"重复修炼收益递减但仍可积累"的需求。
- 与 Ars Nouveau 路线的取舍（一句话）：**给整合包作者改数值，Roots 明显更合适**——Ars 的数值在 per-glyph 的 SERVER TOML（改的人要懂 config 目录、且服务端要重启同步），Roots 的数值在 `data_maps/*.json`（datapack 生态通用、能被 CraftTweaker/datapack 工具链与 JEI 页面直接读，且 comment 字段自带文档），代价是 Roots 的语义层（Ritual/Spell 类）与 TOML 路线同样不可数据化，而 Ars 靠"法术=符文序列"在**组合层**换来了另一维度自由度（作者可拼出作者没写过的法术，Roots 拼不出来）。求仙问道如果功法是"预先设计好的固定条目"，抄 Roots；如果功法要"玩家/作者自由组装"，抄 Ars 的组合层 + Roots 的数值层。
