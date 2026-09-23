# Occultism 源码分析报告

## 1. 基本信息

- mod_id `occultism`，作者 Kli Kli，许可证 MIT（`gradle.properties:19-24`）；发布 POM 里写成 `MIT AND CC-BY-4.0`（代码 MIT、美术 CC-BY，`build.gradle:333-336`）。
- 目标 MC `26.1.2`、版本区间 `[26.1,26.2)`、NeoForge `26.1.2.76`（`gradle.properties:11-14`）。加载器只有 NeoForge，无 Forge/Fabric 分支。mod 版本 `1.251.0`（`gradle.properties:22`）。
- Gradle 插件 `net.neoforged.moddev` 2.0.141（`build.gradle:5`、`gradle.properties:15`），工程结构 single：`settings.gradle` 只有一个 rootProject、无 include（`settings.gradle:11`，另有一段被注释掉的 `includeBuild('../code-defined-gui')` 复合构建开关，`settings.gradle:13-21`）。
- Java 工具链 25（`build.gradle:42`），mixin `compatibilityLevel` 仍是 `JAVA_21`（`src/main/templates/occultism.mixins.json:6`）。
- 编译依赖与发布：`implementation` modonomicon（必需前置）、geckolib、codedefinedgui 与 magicparticleslib（后两者 `jarJar` 内嵌），`compileOnly` jei/jade/curios/theurgy/apothic-enchanting；发布到 cloudsmith `klikli-dev/mods`，artifactId = `occultism-26.1.2-neoforge`（`build.gradle:21`、`186-267`、`321-357`）。前置 mod 列表与版本区间在 `src/main/templates/META-INF/neoforge.mods.toml:36-106`。
- 构建期有一个 `ProcessResources` 任务把 `src/main/templates` 里的 `${var}` 展开成 `neoforge.mods.toml` / `occultism.mixins.json`（`build.gradle:271-302`）——模板目录放元数据、resources 只放静态资产，这个布局值得抄。
- 速览卡片勘误：MC/NeoForge 版本与 mod_id 正确；但「主类候选 `datagen/book/getting_started/PotionEffectsEntry.java`」是错的（真正的 `@Mod` 类是 `Occultism.java`），卡片行数普遍比实测多 1 行（见下节）。

## 2. 源码规模与包结构

实测（`find src -name '*.java' | xargs wc -l` 汇总）：**992 个 .java、119,443 行**，全部在 `src/main/java`；本检出无 `src/test`。卡片写 120,435 行，与实测差 992 行——正好等于文件数，应是按「每文件至少 1 行」口径统计。

下文路径简写：`J/` = `src/main/java/com/klikli_dev/occultism/`。

| 顶层包 | 文件数 | 说明 |
|---|---|---|
| `J/common/` | 319 | 游戏逻辑：entity 138、item 61、block 40、container 24、ritual 15、blockentity 11、misc 11、level 8、effect 3、data 3、advancement 2、command 1、capability 1、根 1（`DebugHelper`） |
| `J/datagen/` | 283 | book 251（Modonomicon 手册页）、recipe 10（含 `builders/` 6）、tags 5、worldgen 4、loot 4、model 3、lang 1、根 5 |
| `J/client/` | 169 | render 67、gui 59、model 26、itemproperties 6、particle 3、keybindings 3、divination 3 |
| `J/integration/` | 54 | modonomicon 15、jei 15、emi 15、jade 4、almostunified 3、apothicenchanting 1 |
| `J/crafting/` | 42 | 6 种 RecipeType + result/display/conditionextension |
| `J/network/` | 34 | 3 框架类 + 31 条 payload |
| `J/registry/` | 32 | DeferredRegister 汇总 |
| `J/util/` | 20 · `J/api/` 18 · `J/handlers/` 10 · `J/config/` 4 · `J/mixin/` 3 · `J/loot/` 1 | 根目录 3 个文件：`Occultism.java`、`OccultismConstants.java`、`TranslationKeys.java` |

最大的 12 个源文件（实测行 / 卡片行，普遍差 1）：

1. `J/datagen/recipe/RitualRecipes.java` 3083 · 2. `J/datagen/lang/ENUSProvider.java` 2187 · 3. `J/datagen/recipe/OccultismRecipeProvider.java` 1444 · 4. `J/client/gui/storage/StorageControllerGuiBase.java` 1134 · 5. `J/registry/OccultismItems.java` 1002 · 6. `J/datagen/tags/OccultismItemTagProvider.java` 971 · 7. `J/registry/OccultismBlocks.java` 912 · 8. `J/common/blockentity/GoldenSacrificialBowlBlockEntity.java` 897 · 9. `J/datagen/model/OccultismItemModelSubProvider.java` 846 · 10. `J/datagen/model/OccultismBlockModelSubProvider.java` 844 · 11. `J/datagen/loot/OccultismEntityLoot.java` 826 · 12. `J/common/ritual/Ritual.java` 762。

源码树不完整（重要）：`src/main/resources` 实测只有 **5 个文件**——3 个 `00_readme.md`（loot_table / recipe/crushing / recipe/ritual）、`META-INF/accesstransformer.cfg`、`assets/occultism/textures/about_isabella.txt`；`src/generated/resources` 整个缺失（`build.gradle:37-40` 声明它是资源目录）。因此本检出的 **所有 datapack JSON、lang、模型都不在树里**，仪式配方/ pentacle 的真实 JSON 形状只能从 datagen 类与 `src/main/resources/data/occultism/recipe/ritual/00_readme.md`（含一份完整示例配方，`:35-93`）复核。第 5、6 节据此取证，凡未能直接看到 JSON 的地方我都会指向生成器行号。

取舍：细读 ritual 包（1,927 行全覆盖）、`GoldenSacrificialBowlBlockEntity`、`RitualRecipe`、`StorageControllerBlockEntity` + `MapItemResourceHandler`、`DimensionalMineshaftBlockEntity`、`ManageMachineJob`/`ManageMachineGoal`、`PentacleProvider`、network/config/datagen 骨架；`client/render`、`common/entity/familiar`（138 文件里的绝大部分 AI/familiar 行为）、`common/item` 只按包略读，未逐个核实。

## 3. 入口与注册

入口 `J/Occultism.java:76` 的 `@Mod(Occultism.MODID)` 类，构造器签名直接吃 `IEventBus modEventBus, ModContainer modContainer`（`:89`）：

```java
modContainer.registerConfig(Type.SERVER, SERVER_CONFIG.spec);      // :91
OccultismBlocks.BLOCKS.register(modEventBus);                      // :99
OccultismSpiritJobs.JOBS.register(modEventBus);                     // :120  自定义注册表
OccultismRituals.RITUAL_FACTORIES.register(modEventBus);             // :121  自定义注册表
modEventBus.addListener(Networking::register);                       // :129
NeoForge.EVENT_BUS.addListener(OccultismRecipeManager.get()::onDatapackSync); // :133
if (FMLEnvironment.getDist() == Dist.CLIENT) { /* 4 个 mod bus + 2 个 game bus 监听 */ } // :135-144
```

- 注册方式：23 个 `DeferredRegister.register(modEventBus)`（`Occultism.java:95-117`：effects/potions/recipe types/recipe serializers/blocks/items/creative tabs/block entities/containers/entities/sounds/particles/features/loot modifiers/sensors/memory types/data attachments/advancement triggers/data components/recipe results/condition codecs/recipe displays/foods），加 2 个自定义注册表（`spirit_job_factories`、`ritual_factories`，见 `J/registry/OccultismRituals.java:35-40`、`J/registry/OccultismSpiritJobs.java:36-40`）。第 3 个自定义注册表 `recipe_result_type` 用 `new RegistryBuilder<>(...).sync(true)` 显式开了跨端同步（`J/registry/OccultismRegistries.java:17`），在 `NewRegistryEvent` 里注册（`:20`，由 `Occultism.java:124` 挂上）。
- 事件总线订阅点：mod 总线 `RegisterCapabilitiesEvent`（`EventPriority.HIGHEST`，`Occultism.java:125`）、`EntityAttributeCreationEvent`（`:127`，`:197-268` 手写 60+ 实体属性）、`FMLCommonSetupEvent#enqueueWork`（`:148-190`，往 `BlockEntityType.CAMPFIRE/SHELF.validBlocks` 里塞自家方块、注册发射器行为）、`RegisterPayloadHandlersEvent`（`J/network/Networking.java:37`）。游戏总线只挂 3 个全局监听（数据附件克隆/加入世界/配方同步）+ 客户端 2 个。
- 仪式方块不用全局 tick 事件：`GoldenSacrificialBowlBlock.java:121` 的 `getTicker` 返回 `bowl::tick`，仪式推进完全靠 BE ticker。
- datagen 入口另起一个 `@EventBusSubscriber` 类 `J/datagen/DataGenerators.java:56-60`，与主入口隔离。

## 4. 核心系统

### 4.1 仪式引擎：数据形状与时间线

仪式定义是 **datapack 配方**（`RecipeType` = `occultism:ritual`，`J/registry/OccultismRecipes.java:45,58`），`RitualRecipe.CODEC` 由四段 record 拼成（`J/crafting/recipe/RitualRecipe.java:74-85`）：

- `ritual_type`（Identifier，指向 ritual 工厂注册表的一行，决定行为）；
- `RitualRequirementSettings`：`pentacle_id` + `ingredients` + `activation_item` + `duration`（`:444-457`），`durationPerIngredient` 不在 JSON 里，构造时按 `duration / (ingredients.size()+1)` 推导（`:473-479`）；
- `RitualStartSettings`：`entity_to_sacrifice{tag,display_name}`、`item_to_use`、`condition`（`:408-442`）；
- `EntityToSummonSettings`：`entity_to_summon` / `entity_tag_to_summon`（随机取 tag 内一个）/ `entity_nbt` / `spirit_job_type` / `spirit_max_age` / `summon_number`（`:373-406`）；
- 外加 `ritual_dummy`（占位物品）、`result`、`command`（`:79-81`）。

时间线**只有一个标量** `currentTime`。驱动在 `J/common/blockentity/GoldenSacrificialBowlBlockEntity.java:389-510` 的 `tick()`：先 `restoreCastingPlayer()` → 若 `!isValid(...)` 立即 `stopRitual(false)`（`:403-408`）→ 若祭品/用物未满足就只发等待粒子并 return（`:411-439`）→ 按碗的阶级推进时间：tier1 金碗每 `20 * ritualDurationMultiplier` tick 加 1 秒，tier2 iesnium 碗每 `5 * multiplier`（4 倍速），tier3 圣杯直接把 `currentTime = duration` 瞬间完成（`:479-491`）→ 调 `ritual.update(...)` → `consumeAdditionalIngredients` 失败即打断（`:498-505`）→ `currentTime >= duration` 时 `stopRitual(true)`（`:507`）。

额外材料是**随时间分批消耗**而非起手全收：`Ritual.consumeAdditionalIngredients` 用 `floor(time / durationPerIngredient)` 算「到现在应该吃掉几份」，再从 8 格半径内的祭品碗里逐个 `extract`，找不到就返回 false 触发打断（`J/common/ritual/Ritual.java:369-397`）。

关键结论：**本版本没有任何仪式子类覆盖 `update()`**。全仓 `common/ritual/*.java` 里只有 `Ritual.java:296,311` 定义 `update`，15 个 Ritual 子类清一色只覆盖 `finish()`（`SummonRitual.java:128`、`SummonWildRitual.java:49`、`CraftRitual.java:42`、`UpgradeRitual.java:49`、`CommandRitual.java:53`…）。所以"多阶段仪式"在 Occultism 里不存在——它是「单一计时器 + 两道输入门 + 完成回调」的形状。

### 4.2 Pentacle（法阵）：多块结构的数据化

法阵不在本 mod 里实现，而是复用自家 Modonomicon 的 multiblock 系统：`RitualRecipe.getPentacle()` 返回 `ModonomiconAPI.get().getMultiblock(pentacleId)`（`J/crafting/recipe/RitualRecipe.java:163-165`），校验就是 `pentacle.validate(level, goldenBowlPosition) != null`（`J/common/ritual/Ritual.java:216-218`）。

法阵 JSON 由 datagen 从 ASCII 图案生成：`J/datagen/PentacleProvider.java:65-410` 用字符矩阵声明 19 个法阵（含 1 个 `debug`；最大的 `summon_marid` / `craft_marid` 是 21×21，`:155-178`、`:321-344`），`MappingBuilder` 把字符映射成 `modonomicon:block` / `modonomicon:tag` / `modonomicon:display` 三种元素（`:496-532`），`addPentacle` 再把「图案层 + 棋盘地基层」两层拼成 `type: modonomicon:dense` 的 JSON 写到 `data/occultism/<MultiblockDataManager.FOLDER>/<name>.json`（`:420-457`、`:468`）。符石/蜡烛/水晶用的是 **tag 而非具体方块**（`OccultismTags.Blocks.GLYPHS_*`、`CANDLES`，`:534-608`），因此整合包可以用任意 mod 的方块补位。

失败诊断做得很足（这块是「求仙问道」最缺的）：法阵差一点点时，`helpWithPentacle` 对四个旋转做 `simulate`、取差异最小的法阵，把「缺哪块、在哪格」拼成消息发给玩家（`GoldenSacrificialBowlBlockEntity.java:176-210`、`:303-325`）；材料差一点点时 `helpWithRitual` 按差异比例 < 0.5 猜玩家想做什么仪式（`:226-285`）；碗全空时发 `empty_bowls`；没碗时给周围空气格发 `BLACK_MARKER` 粒子提示摆碗位（`:583-608`）。

### 4.3 参与者：招募、校验、回滚

三类参与者，机制各不相同：

1. **施法者**：起手时把 `castingPlayer` UUID 写进 BE（`startRitual` `:647`），引用不持久化；每 30 秒尝试按 UUID 全维度找回在线玩家（`restoreCastingPlayer` `:512-520` → `J/util/EntityUtil.java:58-65` 遍历 `server.getAllLevels()`）。找不到也不打断仪式，只是少发提示。
2. **祭品/用物**：靠两个**运行时挂到全局总线**的监听器。`startRitual` 里 `NeoForge.EVENT_BUS.addListener(this.livingDeathEventListener / rightClickItemListener)`（`:660-661`），`stopRitual` 与 `preRemoveSideEffects` 成对 `unregister`（`:747-748`、`:691-699`，注释明确说是防 BE 被卸载时漏解绑）。判定条件：玩家击杀 + 半径 8 内 + 实体类型在 `entity_to_sacrifice` tag 内（`onLivingDeath` `:797-809`），或半径 16 内右键使用指定物品（`onPlayerRightClickItem` `:785-795`）。满足只置一个布尔位并 `markNetworkDirty()`（`:771-783`）。
3. **工人（自动合成 spirit）**：见 4.5。

**回滚**在 `stopRitual(finished=false)`：返还激活物品到世界（`:720-730`）、把 `consumedIngredients` 里已吃掉的每一份材料 `Containers.dropItemStack` 逐个吐回（`:731-734`），再清空 `currentTime / sacrificeProvided / itemUseProvided / remainingAdditionalIngredients / consumedIngredients`（`:737-745`）。

**跨端与断线**：BE 存盘字段只有 `currentRitual`（配方 ID 字符串）、`castingPlayerId`、`currentTime`、`ritualActive`、`consumedIngredients`（List<ItemStack> via `ItemStack.OPTIONAL_CODEC`）、`sacrificeProvided`、`requiredItemUsed`（`saveAdditional` `:846-867`）；`remainingAdditionalIngredients` **不存盘**，由「全部材料 − 已消耗」重算（`restoreRemainingAdditionalIngredients` `:811-824`，其中 level 为 null 时留 null 让 `tick()` 下一 tick 再试，`:394-401`）。`saveNetwork/loadNetwork` 是同一字段的子集（`:869-896`），配方 ID 在客户端到 BE 加载时才惰性解析成 `RitualRecipe` 对象（`getCurrentRitualRecipe` `:339-355`）。仪式状态还有第二个出口：红石信号 `getSignal()` 用 0/1/2/8 表示「无仪式/缺祭品/缺用物/进行中」（`:357-369`），配合 `level.updateNeighborsAt` 让比较器能读出仪式阶段（`:412-413`、`:666`、`:753`）。

结果落地也做了自动化：`Ritual.dropResult` 优先把产物塞进金碗上方 1~3 格、面朝下的祭品碗，否则丢地上（`J/common/ritual/Ritual.java:682-714`）；`dropResultAndFlame` 则先找 8+2 半径内最近的 `RitualCatcherBlockEntity` 收产物，并塞一个 `flame_of_automation`（把 ritual_dummy 的物品 id 尾段当作品灵名写进物品，`Ritual.java:747-748`）（`:725-760`）。`RitualCatcherBlockEntity` 的槽位 `isValid` 只允许 FLAME_AUTOMATION（`J/common/blockentity/RitualCatcherBlockEntity.java:48-49`）。注：本版本未见「火焰自动重施仪式」的代码路径，它只是产物/凭证容器（未验证是否有其它消费方）。

### 4.4 存储网络：图结构、寻址、同步

不是 AE 式的 cell 网络，而是**单一控制器的 Map 存储 + 周边方块直连**：

- 存储本体 `J/common/misc/MapItemResourceHandler.java:34-69`：`Object2IntOpenHashMap<ItemResource> resourceToCountMap`（一个物品变体一条记录，不占槽）+ `resourceToSlot/slotToResource/emptySlots/nextSlotIndex` 的虚拟槽索引 + `itemToVariantsCache`（`Multimap<Item,ItemResource>` 加速按物品查），双限额 `maxItemTypes` / `maxTotalItemCount`，整体用 `Codec` 序列化（`:37-59`），并继承 `SnapshotJournal` 以支持 NeoForge 新 `Transaction` 体系。
- 容量增长靠**物理结构**：控制器首次 tick 时对六个方向做射线扫描（最远 5 格、要求稳定器朝向对着控制器）统计稳定器，按 tier1~5 叠加限额（`StorageControllerBlockEntity.java:92`、`:159-233`），`setStorageLimits` 会清缓存消息并 `markNetworkDirty` 强制重同步（`:345-354`）。
- 寻址统一用 `J/api/common/data/GlobalBlockPos.java:42-48`（`BlockPos` + `ResourceKey<Level>`），带 Codec 与 StreamCodec。跨维度访问在 `J/util/BlockEntityUtil.java:43-80`：同维度直接查；跨维度时**客户端一律返回 false/null**，服务端用 `ServerLifecycleHooks.getCurrentServer().getLevel(dimKey)`，目标维度不存在或未加载同样返回 null。远程终端就是这么打开远端控制器的：`StorageRemoteItem.java:103-116` 先 `hasChunkAt` 检查，不加载就发 `.message.not_loaded` 给玩家。
- 同步：控制器内容不走容器槽位同步。`getStacks()` 每次从 map 重算并顺带刷新 usedItemTypes/usedTotalItemCount（`StorageControllerBlockEntity.java:317-328`），消息对象缓存到 `cachedMessageUpdateStacks`，任何内容变化在 `onContentsChanged` 里置 null（`:545-549`）。实际发送点在容器交互后（`J/common/container/storage/StorageControllerContainerBase.java:167`、`:444`）。`MessageUpdateStacks` 自带 deflate/inflate，把 stacks 与四个限额编进压缩 `ByteBuf` payload（`J/network/messages/MessageUpdateStacks.java:52-54` 声明、`:114-135` 解压）。
- 控制器还能被**装进物品/BE**：`applyImplicitComponents/collectImplicitComponents` 把排序方向、合成矩阵、orderStack、整份存储内容写进 DataComponent（`StorageControllerBlockEntity.java:612-648`，对应 `OccultismDataComponents.STORAGE_CONTROLLER_CONTENTS` `J/registry/OccultismDataComponents.java:264-266`），`removeComponentsFromTag` 负责避免 NBT 双写。`RitualCatcherBlockEntity.java:107-125` 里有一段专门处理「控制器被放进碗时先剥掉内容组件」的补丁，注释说明是规避深层 NBT 崩溃——这是个真实踩过的坑。

### 4.5 工人与自动合成（跨维度只读，不跨维搬运）

自动合成链是「控制器记账 → spirit 自己跑腿」：

- 玩家在终端点某个配方的 order → 客户端发 `MessageRequestOrder`（`J/client/gui/storage/logic/StorageScreenActions.java:60`）→ 控制器 `addDepositOrder` 先模拟抽取确认可用（`StorageControllerBlockEntity.java:377-399`）→ 按 `linkedMachinePosition → spiritUUID` 查出登记的工人（`depositOrderSpirits`，`:101`）→ 若该 spirit 的 job 确实是 `ManageMachineJob` 就 `addDepsitOrder` 入队，否则**当场注销这条登记**（`:388-397`）。
- 工人侧：`J/common/entity/job/ManageMachineJob.java` 存 `storageControllerPosition` + `managedMachine(MachineReference)` + `currentDepositOrder` + `depositOrderQueue`，全部手写进实体 NBT（`:169-209`）；`onInit` 往 `goalSelector` 塞 4 个 goal，`cleanup` 逐个 `removeGoal` 并注销（`:129-151`）。登记/注销都是幂等的：`setManagedMachine` / `setStorageControllerPosition` 先 unregister 再 register（`:75-98`）。
- **失联自愈**：`resolveCurrentStorageController`（`:247-264`）每 tick 重解析（chunk 未加载 → 置 null 而不是崩），`refreshStorageControllerRegistration`（`:239-245`）在「换了一个控制器实例」时重新登记；`validateLinkedMachines`（`:235-238`）用 `MachineReference.isValidFor(level)` 剔除失效机器。
- 搬运本身不跨维度：`J/common/entity/ai/goal/ManageMachineGoal.java:124-140` 让 spirit 走到目标方块 2.2 格内（`accessDistance = 2.2f`，`:110`）、把控制器抽出的物品插进**自己身上的 `Capabilities.Item.ENTITY`**，然后设 `depositPosition`（一个普通 `BlockPos`，取自 `machineReference.insertGlobalPos.getPos()`，`:139`——维度信息在这里被丢弃）交给 `DepositItemsGoal` 投递。`SpiritEntity` 的工作区/存取位全是 `EntityDataAccessor<BlockPos>`（`J/common/entity/spirit/SpiritEntity.java:90-104`），即工人只在本维度活动。
- 「矿工」在本版本已不是实体：`J/common/item/spirit/MinerSpiritItem.java:41-63` 只是一个把配置里的 `maxMiningTime / rollsPerOperation / outputMultiplier` 在 `onCraftedBy` 时写进 DataComponent 的物品（`:78-86` 还负责补齐缺失组件），真正干活的是 `DimensionalMineshaftBlockEntity`（它在 `:133-135` 用 `FakePlayer` 主动调 `onCraftedBy` 触发这套初始化）。机器用 `MinerRecipe`（`ingredient` → `WeightedRecipeResult`，`J/crafting/recipe/MinerRecipe.java:39-51`）做加权抽取：`mine()` 缓存 `possibleResults`、按 `rollsPerOperation + fortune` 次 `WeightedRandom` 掷取、silk/fortune 用 `min(rand(0,lvl)...)` 做递减收益、结果批量合并后写进输出 handler，耐久 `hurtAndBreak(1)`，并可在下一次伤害会碎之前把工具本体吐回（`DimensionalMineshaftBlockEntity.java:285-366`）。进度同步刻意做**节流**：只在「maxMiningTime 变化 / 活跃态 0↔非0 翻转 / 进度漂移 ≥10 tick」时 `markNetworkDirty`（`:245-265`）。输出目标可被下方的 `Dimensional Extractor` 劫持：缓存 `below(2)` 的 capability，方块状态变了才刷新（`:393-412`）。
- 结论：跨维度取物在本 mod 只有两种——**只读远端 BE**（存储远程、机器引用）和**真传送**（`EntityWormholeBlock.java:182-257`、`TeleportTabletItem.java:91-161`，都用 `TeleportTransition` + `PLACE_PORTAL_TICKET`）。没有任何「工人跑到别的维度挖矿再回来」的实现。

### 4.6 进度与时限类系统（对应问题⑤）

本版本**没有**熟练度/等级/"time lock" 系统：全仓 grep `proficiency|affinity|skillLevel|progression|timeLock` 无实现命中（只在 `J/datagen/book/getting_started/ChalksEntry.java:31` 的书籍文案里出现 "progression" 一词）。实际存在的三个"时间/进度"机制是：

1. **灵魂寿命**：`spirit_max_age` 由配方写入（`SummonRitual.java:182`），`SpiritEntity.aiStep` 每 20 tick 增 1 秒、超龄直接 `die + remove(DISCARDED)`（`J/common/entity/spirit/SpiritEntity.java:426-433`），`DEFAULT_MAX_AGE = -1` 表示不限（`:84`，`canDieFromAge()` `:662`）；年龄走 `EntityDataAccessor` 所以客户端可读、GUI 显示成百分比（`J/client/gui/spirit/SpiritGui.java:135`）。
2. **仪式时长倍率**：`ritualDurationMultiplier`（`J/config/OccultismServerConfig.java:363,389-391`，注释专门警告 NightConfig 会把 `.05` 吃成 1.0），配合碗的 tier 决定推进速度（见 4.1）。
3. **进度解锁**：只有 2 个自定义 advancement 触发器（`J/common/advancement/RitualTrigger.java`、`FamiliarTrigger.java`），仪式完成时在 `Ritual.finish` 里 `OccultismAdvancements.RITUAL.get().trigger(player, this)`（`J/common/ritual/Ritual.java:265`），配方本身靠 Modonomicon 的 research 树门控（`J/datagen/OccultismResearch.java` 373 行）。

对「求仙问道」的映射（问题⑥）：

- **现成形状，直接照搬**：(a) `配方 ID + 法阵 ID + 行为工厂 ID` 的三段式仪式配方 + Codec/StreamCodec 双份（`RitualRecipe.java:74-106`）；(b) 单计时器 + 分批吃材料 + 两道输入门（祭品/用物）的时间线；(c) `isValid` 每 tick 复检 → 不满足即打断 → `stopRitual(false)` 的材料吐回；(d) 只存 ID/时间/已消耗清单、派生态重算的 BE 存档策略；(e) `getSignal()` 把仪式阶段变红石信号；(f) ASCII 图案 → 多块结构 JSON 的 datagen；(g) 差一点就失败的三类玩家提示；(h) 「自登记 + 每 tick 重解析 + 失联即注销」的工人-控制器关联。境界突破仪式基本能把 (a)-(e) 直接换成「灵石/丹药 + 法阵 + 天象条件」。
- **必须自己造的**：本 mod 的仪式**没有多阶段时间线**（4.1 结论：无人覆盖 `update`），也没有阶段间回退/部分惩罚，要「九转」式分段就得自己在 `update(level,...,time)` 里加阶段表并让它数据化；`condition` 只有维度/生物群系四种（`J/crafting/recipe/conditionextension/condition/*.java`），天时/境界/因果条件要自己扩 `ICondition`（`J/registry/OccultismConditionCodecs.java` 给了注册范式）。
- **明确的坑**：① **区块卸载**——全仓 java 无 `forceLoad`/`TicketType`/`persistenceRequired`（grep 为空），仪式只靠 BE ticker 推进，玩家走远就原地冻结；`markNextIngredient`/`consumeAdditionalIngredients` 依赖 `getSacrificialBowls` 的 17×(h)×17 三重扫格 + `level.getBlockEntity` 每 tick 全量调用（`Ritual.java:563-589`），仪式一多就是每 tick 几百次 BE 查询，`isValid` 还会顺带 `pentacle.validate`；求仙问道若要「长时间闭关」，必须自建 forceload 或改成「离线补算」。② **事件监听器泄漏**——`startRitual` 往全局总线加 lambda 监听器（`GoldenSacrificialBowlBlockEntity.java:660-661`），漏 `unregister` 就永久持有 BE（它在 `:691-699` 里对 `preRemoveSideEffects` 做了兜底，注释写明了原因）。③ **跨维度**——工人实体只在本维度（`SpiritEntity` 的 deposit/extract 是裸 `BlockPos`），`MachineReference` 虽有 `GlobalBlockPos` 但搬运 goal 会丢维度；真要跨维度采集，得自己写传送 + 回程 + 容量约束（现成可参考的只有 `DimensionalMineshaftBlockEntity` 的「输出目标可被下游劫持 + 进度节流同步」）。④ **中断**——`stopRitual(false)` 一律吐回全部已消耗材料，不扣进度；如果突破失败要「反噬」，得自己在 `interrupt()` 里加惩罚钩子。⑤ `remainingAdditionalIngredients` 在 level 为 null 时以 null 作为「待重试」哨兵（`:394-401`），这类哨兵容易在后续改动里被当成空集合误用。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：31 条自定义 payload，全部在 `J/network/Networking.java:37-74` 一个 `registrar(MODID)` 里成对登记（22 条 toServer、9 条 toClient），handler 统一走 `MessageHandler::handle` 分派到 `IMessage#onServerReceived/onClientReceived`。每条消息自带 `Type` + `StreamCodec`（如 `MessageUpdateStacks.java:52-54`），没有用 `ConfigurationUtils` 之外的框架。发送工具只有 4 个：`sendTo(player)`、`sendToTracking(chunkPos)`、`sendToTracking(entity)`、`sendToServer`（`:76-90`）。
- **数据驱动程度**：6 种 `RecipeType`（spirit_trade / spirit_fire / crushing / crystallize / miner / ritual，`J/registry/OccultismRecipes.java:40-45`）+ 2 种原版特殊配方序列化器（`:60-62`），每种都写 `MapCodec`（磁盘/网络）与 `StreamCodec`（同步）双份；仪式的 `condition` 字段直接复用 NeoForge 的 `ICondition.CODEC`，并在 StreamCodec 里用 `ByteBufCodecs.fromCodecWithRegistries(ICondition.CODEC)` 过 NBT 以绕开流式 codec 对条件多态的麻烦（`RitualRecipe.java:420-429` 带注释解释）。扩展条件通过 `DeferredRegister<MapCodec<? extends ICondition>>` 注册（`J/registry/OccultismConditionCodecs.java:15-20`），4 个自家条件在 `J/crafting/recipe/conditionextension/condition/`，另有 visitor 模式把失败原因渲染成可读消息（`J/crafting/recipe/conditionextension/RitualRecipeConditionFailureInformationVisitor.java` 138 行、同目录 `RitualRecipeConditionDescriptionVisitor.java` 122 行）——同一棵树两用（判定 + 说明），设计干净。
- **配方显示解耦**：走原版 26.1 的 `RecipeDisplay` API，自家 `RitualRecipeDisplay`（`J/crafting/recipe/display/RitualRecipeDisplay.java:44-68`）注册进 `RECIPE_DISPLAYS`（`J/registry/OccultismRecipeDisplays.java:38-44`），JEI/EMI 只消费 display；`RitualRecipe.display()` 甚至从实体的 loot table id 反推一个 `TagSlotDisplay`（`RitualRecipe.java:269-289`），把「祭品会掉什么」也做成数据。
- **配置**：4 个 `ModConfigSpec`，全部静态 `get()` + 构造器里 `registerConfig`（`Occultism.java:91-93`）：server 461 行（`itemSettings` / `spiritJobs` 每 tier 一组 time/output multiplier / `rituals` / `storage` 稳定器 tier1~5 限额）、startup 135 行（`RitualSettings` 的灵名池 + `DimensionalMineshaftSettings.miner*` 的 `maxMiningTime/rollsPerOperation/outputMultiplier/durability`；之所以放 STARTUP，是因为这些值在物品注册期就要读——`MinerSpiritItem` 构造器直接收 `Supplier<Integer>`，`J/common/item/spirit/MinerSpiritItem.java:43-55`）、client 219 行、common 41 行。
- **datagen**：`J/datagen/DataGenerators.java:59-121` 一次注册 13 类 provider：registry 数据（`DatapackBuiltinEntriesProvider` + `OccultismRegistries.BUILDER`，输出句柄被后续 tag provider 复用 `:72`）、loot（block/entity 两个 subprovider）、**PentacleProvider**、advancements、4 个 tag provider + enchantment tag、model、loot modifiers、`RecipeProvider.Runner`（`:100-110`，26.1 新写法）、Modonomicon 的 `NeoBookProvider` + `NeoResearchProvider` + 最后才挂 `ENUSProvider`（`:119` 注释说明顺序依赖：要先把书里的文本攒进 `LanguageProviderCache`）。ritual 配方本体按类型分文件（`J/datagen/recipe/RitualRecipes.java` 3083 行，配 `J/datagen/recipe/builders/RitualRecipeBuilder.java`），法阵图案硬编码在 Java（`PentacleProvider.java:65-410`）。
- 无 KubeJS 兼容层（卡片标题「Occultism KubeJS」不实）；`build.gradle:25-35` 明确把 `**/emi/**` 和 `AlmostUnifiedIntegrationImpl.java` 从 sourceSets 里排除——即这两个 integration 目前**不参与编译**，`integration/emi/` 的 15 个文件是待启用死代码，仓库自带的 `AGENTS.md` 也写了「Several integrations are intentionally excluded, do not re-enable」。

## 6. Mixin

配置在 `src/main/templates/occultism.mixins.json`（构建期展开到 `build/generated/sources/modMetadata`，`build.gradle:295-296`）：`package com.klikli_dev.occultism.mixin`，`mixins`（通用）两项、`client` 一项、`server` 空数组，`injectors.defaultRequire = 1`（`:7-18`）。全 mod 只有 3 个 mixin 类：

- `J/mixin/MixinLivingEntity.java`（通用段）：`@Inject` 进 `canGlide` 的 `@At("RETURN")`、cancellable，原版返回 false 时用 `MovementUtil.allowCustomGlide(entity)` 兜底放行（自家斗翼/法术）；`@ModifyVariable` 进 `updateFallFlying` 的 `@At("STORE")` `ordinal = 1`，持有 `FIRE_WING` 效果时把 free-fall 间隔改成 1（提高坠落检测频率，让火翼判定更跟手）。
- `J/mixin/MixinServerGamePacketListenerImpl.java`（通用段）：`@Redirect` 进 `tryPickItem` 内对 `Inventory.findSlotMatchingItem` 的调用（`@At INVOKE`），若原逻辑返回 -1 且目标物品是 `ChalkItem`，则退化为 `isSameItem`（忽略组件）再扫一遍背包——修「粉笔带组件后双击取色拿不到同一支」。
- `J/mixin/MixinItemStack.java`（client 段，`@Mixin(value = ItemStack.class, priority = 10, remap = false)`）：`@Inject(method = "getHoverName", at = @At("RETURN"), cancellable = true)`，带 `UNBREAKABLE` 组件的栈在悬停名两侧插乱码 `nice` 彩蛋；若当前界面是铁砧则直接放行。

另有 49 行 `src/main/resources/META-INF/accesstransformer.cfg`（`build.gradle:48-50` 挂入），典型用途：`public-f BlockEntityType validBlocks`（入口 `Occultism.java:152-159` 靠它扩展营火/架子合法方块）、`public-f Ingredient EMPTY`、一批 datagen 内部字段/方法（`BlockModelGenerators` 的 output 与 `condition/variant/plainVariant`）、以及一条注明「otherwise jei causes a startup crash」的 `ClientCommonPacketListenerImpl connection`。整体策略是：**能 AT 就不 mixin，只有需要 redirect/modify-variable 时才写 mixin**。

## 7. 值得学的 5 条

1. **仪式 = 三段 ID + 一份时间线，行为靠注册表工厂**——`J/crafting/recipe/RitualRecipe.java:128`（`this.ritual = () -> OccultismRituals.REGISTRY.get(this.ritualType).orElseThrow().value().create(this)`）配 `J/registry/OccultismRituals.java:43-92`。值得抄：新增一种仪式=加一个工厂 + 一堆 JSON，引擎与存档格式零改动，且配方在数据包里可被整合包直接改写。
2. **仪式状态只存「配方 ID + 已消耗清单」，派生态一律重算**——`J/common/blockentity/GoldenSacrificialBowlBlockEntity.java:846-867`（存）+ `:339-355`（惰性把 ID 解析回对象并补挂监听器）+ `:811-824`（`remaining = all - consumed`）。值得抄：这是区块卸载/重启/热重载后仪式不腐坏的根本原因，比把对象图整个塞 NBT 安全一个量级。
3. **一个 BE 基类同时喂磁盘与同步包**——`J/common/blockentity/NetworkedBlockEntity.java:44-56`（`loadAdditional` 内调 `loadNetwork`）与 `:62-79`（`getUpdateTag`/`handleUpdateTag`/`onDataPacket` 复用同一对 `save/loadNetwork`），外加 `markNetworkDirty()`。值得抄：47 种内容类型 × N 个 BE 时，"哪些字段要同步"只声明一次，客户端渲染态与服务端存盘态天然不会分叉。
4. **失败诊断比成功路径更值得工程化**——`J/common/blockentity/GoldenSacrificialBowlBlockEntity.java:176-210`（四旋转 diff 取最小、报「缺哪块在哪格」）+ `:226-285`（按差异比例猜玩家想做的仪式）+ `J/crafting/recipe/conditionextension/RitualRecipeConditionFailureInformationVisitor.java`（把 `ICondition` 树渲染成「需要下界 / 当前在平原」）配调用点 `GoldenSacrificialBowlBlockEntity` 侧的 `Ritual.java:187-194`。值得抄：仪式类玩法 90% 的工单是「我摆对了怎么不触发」，把 visitor + 最小差异两件套先建起来，后面加内容不用重做。
5. **工人↔控制器的关系靠「自登记 + 每 tick 重解析 + 查到就顺手清理」**——`J/common/entity/job/ManageMachineJob.java:239-272`（`resolveCurrentStorageController` 未加载即置 null、`registerWithStorageController` 幂等）+ `J/common/blockentity/StorageControllerBlockEntity.java:377-399`（下单时反查工人，查不到就 `removeDepositOrderSpirit`）+ `:235-238`（`isValidFor` 剔除死引用）。值得抄：不引入任何网络/GUI 就自愈了「工人死亡、控制器被拆、区块没加载」三类断链，比"存一张全局网络图"少一整个 bug 面。

次选：`DimensionalMineshaftBlockEntity.java:245-265` 的进度同步节流（阈值 10 tick + 状态翻转才发包）；`PentacleProvider.java:65-114` 的 ASCII→结构 JSON；`MessageUpdateStacks` 的自带 deflate 压缩。

## 8. 公开 API

扩展点集中在 `J/api/`（18 文件），分三块：

- **入口**：`J/api/OccultismAPI.java:34-64`，单例 `OccultismAPI.get()`，目前只有两个方法——`getItemsToPickUp(Entity)`、`canPickupItem(Entity, ItemEntity)`，都是「若实体是本 mod 灵魂且有 job 则委托给 job」的开放钩子，供别的 mod 的 AI/掉落逻辑复用。接口极小，说明外部集成主要走能力与注册表，而不是这个门面。
- **能力接口**（真正的扩展点）：`J/api/common/blockentity/IStorageController.java`（159 行：`getStacks/getMessageUpdateStacks/getMaxItemTypes/setStorageLimits/getLinkedMachines/addDepositOrder/addDepositOrderSpirit/removeDepositOrderSpirit/insertStack/getItemStack/getOneOfMostCommonItem/getAvailableAmount/isBlacklisted` 等）、`IStorageAccessor`、`IStorageControllerProxy`。三者任一实现类即可挂进存储网络：`ManageMachineGoal.java:124` 就是按 `blockEntity instanceof IStorageControllerProxy` 决定能否从该方块抽料，`StorageControllerBlockEntity.java:90` 自己三个全实现。客户端侧另有 `api/client/gui/IStorageControllerGui(+Container)`，供别的 mod 复用终端界面。
- **数据/枚举型注册表**：`ritual_factories`（`OccultismRituals.java:35-40`）与 `spirit_job_factories`（`OccultismSpiritJobs.java:36-40`）都是 NeoForge 自定义注册表——addon 可用 `NewRegistryEvent` 前后往这两个 key 注册自己的 `RitualFactory` / `SpiritJobFactory`（`SpiritJobFactory` 只是 `entity -> job` 加一个客户端外观，`J/common/entity/job/SpiritJobFactory.java` 51 行），再写 `ritual_type: yourmod:xxx` 的配方即可拿到整套仪式引擎。`recipe_result_type`（`J/registry/OccultismRegistries.java:17`）是唯一 `sync(true)` 的注册表，配套 `crafting/recipe/result/` 下的 `RecipeResult`/`WeightedRecipeResult`/`TagRecipeResult` 家族可被 miner/crushing 配方引用。`ItemStack` 侧的扩展点是 DataComponent（`OccultismDataComponents.java`，含 `LINKED_STORAGE_CONTROLLER` `:79`、`STORAGE_CONTROLLER_CONTENTS` `:264`、`MAX_MINING_TIME` `:38`、`SORT_DIRECTION/SORT_TYPE/CRAFTING_MATRIX/ORDER_STACK`），`applyImplicitComponents/collectImplicitComponents` 的写法（`StorageControllerBlockEntity.java:612-648`）就是让第三方方块也能被塞进控制器物品形态的模板。
- **无 addon 框架**：没有事件式扩展 API、无 `RegisterRitualEvent` 之类的开放总线、也没有文档化的 compat 契约（未验证是否有 wiki 之外文档）。`integration/` 的依赖方向是**主→接口的单向**：主包只引 `integration` 的接口/dummy（8 个文件：`KnowledgeTabletItem`、`IesniumAnvilMenu`、`StorageControllerGuiBase`、`StorageTooltipOverlay`、`GoldenSacrificialBowlHUD`、`RitualRecipe`、`ClientSetupEventHandler`、`TagUtil`），反向有 40 个 integration 文件引主包。加载用「接口 + `Class.forName("...impl.XxxImpl")` + 反射失败落回 dummy」模式（`J/integration/jei/OccultismJeiIntegration.java:14-31`），JEI 插件本体只靠 `@mezz.jei.api.JeiPlugin` 发现（`J/integration/jei/impl/JeiPlugin.java:59-60`），因此 JEI 缺席时零崩溃。唯一的分层瑕疵：`RitualRecipe.java:32` 从 integration 里取书籍 i18n 常量，`StorageControllerGuiBase` 直接依赖 JEI 的搜索文本接口——属可接受的便利耦合。Patchouli 在本版本不存在，书籍体系整体换成 Modonomicon（`integration/modonomicon/` 15 文件，页面类型在 `OccultismModonomiconPageTypeRegistry.bootstrap()`（`Occultism.java:149`）注册，每类页面三件套 page/model/renderer）。
