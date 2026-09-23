# TeamMetallurgy/Aquaculture 源码分析报告

> 注：本地为瘦检出（`git ls-files` 958 / 磁盘 105），JSON 数据用 `git show HEAD:<path>` 补读。该分支为 **MC 26.1 新版本**（代码里已用 `Identifier` 新命名），与 1.21.1 版差异较大。

## 1. 基本信息

Aquaculture 2 / mod_id `aquaculture` / 作者 Shadowclaimer, Girafi（TeamMetallurgy）/ 许可证 **All Rights Reserved**（`neoforge.mods.toml`）。`gradle.properties`：minecraft `26.1.1`（range [26.1,26.2)）、NeoForge `26.1.1.2-beta`、Java **25**、`mod_version=2.9.2`、pack_format 18。**仅 NeoForge 单模块**（`src/main`），构建插件 `net.neoforged.moddev 2.0.141`，使用 **AccessTransformer**（`src/main/resources/META-INF/accesstransformer.cfg`）。依赖仅 JEI `29.4.0.23`（compileOnly+runtimeOnly）；CraftTweaker / EMI 依赖已注释但集成代码仍在。无 Mixin。

## 2. 规模与包结构

98 个 `.java`、6942 行。包：`api{,.bait,.fish,.fishing}`、`block{,.blockentity}`、`client{gui.screen,model,renderer{entity.model,entity.state,blockentity,special}}`、`entity{,.ai.goal}`、`init`（12 个文件，最多）、`integration{crafttweaker.actions,emi,jei.recipes}`、`inventory{container,.slot}`、`item{,.crafting,.neptunium}`、`loot`、`misc`。最大文件：`entity/AquaFishingHookEntity` 510、`entity/FishMountEntity` 308、`client/renderer/entity/FishMountRenderer` 244、`block/TackleBoxBlock` 242、`block/WormFarmBlock` 216、`api/fishing/Hook` 187、`loot/BiomeTagPredicate` 176、`item/AquaFishingRodItem` 161。

## 3. 入口与注册

`Aquaculture.java:30` `@Mod(MOD_ID)`，构造注入 `(ModContainer, IEventBus)`：`modContainer.registerConfig(ModConfig.Type.COMMON, AquaConfig.spec)`；`registerDeferredRegistries()` 统一注册 **11 个 DeferredRegister**（BLOCK/ITEM/DATA_COMPONENT_TYPE/CREATIVE_MODE_TAB/BLOCK_ENTITY/ENTITY/SOUND_EVENT/MENU/IRECIPE_SERIALIZERS/BIOME_MODIFIER_SERIALIZERS/CONDITION_CODECS）；`RegisterCapabilitiesEvent` 只给 `TACKLE_BOX` 挂 `Capabilities.Item.BLOCK`；`FMLCommonSetupEvent` 里 `event.enqueueWork` 调 `Hooks::load` 与 `FishWeightHandler::registerFishData`（确保注册表已就绪再写内存表）。`init/FishRegistry.java:43` 提供一站式注册：一次调用同时注册 `AquaFishEntity` 实体、`<name>_bucket` 桶物品与鱼物品，并把实体加进 `fishEntities` 列表。

## 4. 核心系统

**A. 鱼钩（Hook）参数化系统** —— `api/fishing/Hook.java`：不可变值对象 + `HookBuilder`，字段 `minCatchable/maxCatchable`（咬钩窗口，覆盖 vanilla 20~40）、`Vec3 weight`（抛投轨迹阻尼，构造时 `setDeltaMovement(...multiply(weight))`）、`durabilityChance`（免耐久概率）、`luckModifier`、`doubleCatchChance`（双倍掉落）、`catchSound`、`List<TagKey<Fluid>> fluids`（决定能否在岩浆里钓）。`Hooks.java` 内置 10 种，含联动写法 `setOptionalFluid(FluidTags.LAVA, IS_AQ2LAVA_LOADED)`。竿的 4 个附件（hook/bait/line/bobber）存在 `AquaDataComponents.ROD_INVENTORY`（`ItemContainerContents`）里，按槽位序号读取（`AquaFishingRodItem.getHookType/getBait/getFishingLine/getBobber`）。

**B. 自定义鱼钩实体** —— `AquaFishingHookEntity extends FishingHook implements IEntityWithComplexSpawn`：`tick()` 按 hook 是否含 LAVA 分流到 `lavaFishingTick()`（**完整复刻** vanilla 物理与状态机 FLYING/BOBBING/HOOKED_IN_ENTITY）；`catchingFish()` 复制原版但把 `BlockState` 检查改为 `FluidState` 并加水/岩浆两套粒子与音效（`:404-435`）；`nibble = Mth.nextInt(random, hook.getMinCatchable(), hook.getMaxCatchable())`；`retrieve()` 内含双倍掉落重掷、空掉落兜底（末地→`FISH_BONES`、水→COD）、饵耐久损坏后按槽 1 写回 `ROD_INVENTORY`。跨端同步用 `writeSpawnData/readSpawnData` 只传 luck、hook **名字字符串**与 3 个 ItemStack，客户端用 `Hook.HOOKS.get(name)` 反查——绕过自定义类型同步的经典手法。

**C. 数据驱动战利品（生物群系过滤）** —— 注册自定义 loot condition：`FishRegistry.registerFishies` 在 `RegisterEvent` 的 `LOOT_CONDITION_TYPE` 上注册 `aquaculture:biome_tag_check`；实现 `loot/BiomeTagCheck.java` + `BiomeTagPredicate.java`（record：`position/include/exclude/and`，命中结果按 `CheckType` 缓存 `Set<Holder<Biome>>`，带 `INVALID_TYPES` 黑名单）。`init/AquaLootTables.java` 用 `LootTableLoadEvent` + 反射改 `LootPool.entries`（AT 已放开 `entries`）向原版 `minecraft:gameplay/fishing` 注入 fish(85)/junk(10)/neptunium(可配置权重, 仅 openWater) 三个池；35 种鱼写在同一张 `data/aquaculture/loot_table/gameplay/fishing/fish.json`，每条 entry 用 `any_of(biome_tag_check)` 限定群系，另有 lava/nether 独立表。

**D. 重量与切鱼片** —— `api/fish/FishData`（三张 `ConcurrentHashMap`：min/max 重量与 fillet 数量，`getFilletAmountFromWeight` 按重量分 16 档）由 `loot/FishWeightHandler` 消费：监听 `ItemFishedEvent` 掷重量并写数据组件 `FISH_WEIGHT/FISH_SIZE`（juvenile/small/large/massive 按最大重量百分比分档），未登记但属于 `#minecraft:fishes` 的也给 0.1~100。`item/crafting/FishFilletRecipe extends CustomRecipe`（`MapCodec.unit` 单例）用 `#c:tools/knife` 标签切鱼片。

**E. 群系生成注入** —— `loot/AquaBiomeModifiers` 注册 `mob_spawn`/`fish_spawn` 两个 BiomeModifier MapCodec，由 `data/aquaculture/neoforge/biome_modifier/*.json` 驱动；`FishSpawnBiomeModifier` 支持 `List<HolderSet<Biome>>` 多组 include/exclude + `and` 逻辑 + `WeightedList<SpawnerData>` 生成权重。

## 5. 网络 / 数据驱动 / 配置 / datagen

无自定义网络包（用 `IEntityWithComplexSpawn` + 数据组件 + AT）。数据驱动：loot_table JSON（含自定义 condition）、`neoforge/biome_modifier` JSON、recipe JSON、c/tags 标签；`item/crafting/ConditionFactory.java` 注册 2 个 NeoForge `ICondition`（`neptunium_items_enabled`、`neptunium_armor_enabled`），让配方/战利品随配置开关。配置：`misc/AquaConfig.java` 用 `ModConfigSpec`（COMMON，两组 `BASIC_OPTIONS`/`NEPTUNIUM_OPTIONS`，如 `randomWeight`、`fishSpawnLevelModifier`、`neptuniumLootRarity`）。datagen：仅 `clientData` run 输出 `src/generated/resources`（blockstate/model），物品与配方 JSON 手写。

## 6. Mixin

**无 Mixin**。全部原版改动走 AccessTransformer（`src/main/resources/META-INF/accesstransformer.cfg`）：`FishingHook.nibble/currentState/life/timeUntilLured/timeUntilHooked/fishAngle/lureSpeed/biting/openWater/DATA_BITING`、`shouldStopFishing`、`catchingFish`、`setHookedEntity`；`LootPool.entries`（注入战利品池）、`BuiltInLootTables.register`（注册自定义钓鱼表）、`AbstractSchoolingFish.leader`、`LivingEntity.jumping`、`AttributeInstance.removeModifier`。

## 7. 值得学的 5 条做法

1. 把"配件"做成**纯参数对象 + Builder**（`Hook`/`HookBuilder`），行为全部由字段驱动，附属 mod 只需 `AquacultureAPI.registerHook(Hook)` 即可加新钩（`api/fishing/Hook.java:101`）——适合"配件改变机器/工具行为"的设计。
2. 复刻原版 AI/物理时**整体拷贝方法再局部替换**（`catchingFish()`、`lavaFishingTick()`），并把注释写在改动行上，便于跟随版本升级（`entity/AquaFishingHookEntity.java:372`）。
3. 自定义实体跨端同步用 `IEntityWithComplexSpawn` 只传**键名**，客户端回查静态注册表（`readSpawnData` → `Hook.HOOKS.get(name)`），避免同步复杂对象（`:498`）。
4. 用**自定义 LootItemCondition + 单张大表**表达"按群系/位置出不同战利品"，可被数据包完全改写（`loot/BiomeTagCheck.java`、`BiomeTagPredicate.java`）。
5. 用反射之外的**受控注入**扩展原版战利品：`LootTableLoadEvent` + AT 放开 `LootPool.entries`，直接按权重插入 `NestedLootTable`（`init/AquaLootTables.java:44`）——比 mixin 更稳的原版内容扩展。

## 8. 公开 API

- `api/AquacultureAPI.java`：静态门面 `MATS`（材料）、`FISH_DATA`（鱼重量/鱼片注册）、`Tags`（公开 Item/Biome 标签，如 `c:tools/knife`、`aquaculture:fishing_line`）、`createBait(...)`、`registerHook(Hook)`。
- `api/fishing/Hook` + `Hook.HookBuilder`（`setCatchableWindow/setWeight/setDurabilityChance/setLuckModifier/setDoubleCatchChance/setCatchSound/setFluid`）、`Hooks`（内置实例）、`api/fish/FishData`、`api/bait/IBaitItem`（自定义鱼饵只需实现该接口给 `getLureSpeedModifier`）。
- 外部接入方式：1) 注册自定义 Hook 与粘竿附件；2) `FISH_DATA.add(item, min, max, filletAmount)` 让新鱼参与重量/鱼片系统；3) 通过 JEI/EMI 插件类与 CraftTweaker 动作（`integration/crafttweaker/actions/AddFishDataAction|RemoveFishDataAction`）在脚本层增删鱼数据；4) 数据包改写 loot_table / biome_modifier。
