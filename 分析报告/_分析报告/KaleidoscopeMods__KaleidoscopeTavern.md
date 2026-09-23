# KaleidoscopeMods/KaleidoscopeTavern 源码分析报告

## 1. 基本信息

- Mod 名：Kaleidoscope Tavern（森罗物语：酒馆）；mod_id `kaleidoscope_tavern`
- 作者：ysbbbbbb, tartaric_acid；版本 `1.2.0-forge+mc1.20.1`，`mod_description` 仍为 `To be added...`
- **平台为 Minecraft Forge 47.3.0 / MC 1.20.1，Java 17**（`gradle.properties`、`src/main/resources/META-INF/mods.toml`），与厨房同架构（同一团队的姊妹工程）
- Gradle 插件：`net.minecraftforge.gradle [6.0.16,6.2)`、`parchmentmc.librarian.forgegradle`、`spongepowered.mixin 0.7.+`
- 许可证：BSD-3-Clause + CC BY-NC-SA 4.0；`archivesBaseName = kaleidoscopetavern`
- 依赖：compileOnly JEI 15.20.0.105 / REI 12.1.785 / EMI 1.1.22 / Curios 5.9.1 API / Flywheel API；implementation Ponder 1.0.80、Jade、Architectury+ClothConfig（REI 前置）；**KubeJS 相关依赖已整段注释掉**（build.gradle），runtimeOnly Create 6.0.6、Curios、CarryOn、nbtedit-reborn、kiwi；无 Farmer's Delight/Create 编译期依赖

## 2. 源码规模与包结构

- `.java` **255 个，23434 行**（`find src -name '*.java' | wc -l` / `wc -l` 汇总）
- 根包 `com.github.ysbbbbbb.kaleidoscopetavern`，主要子包（深度 2，文件数）：`client/render` 21（含 `block` 14 个 BER）、`block/deco` 17、`blockentity/deco` 11、`compat/ponder` 10、`block/brew` 10、`game/tap` 8、`blockentity/brew` 8、`block/plant` 8、`datagen/recipe` 7、`block/mixology` 6、`compat/rei|jei` 各 5、`compat/emi` 4、`crafting/{recipe,serializer}` 各 4、`api/blockentity` 4、`network/message` 4、`init/register` 3
- 最大文件：`blockentity/brew/BarrelBlockEntity.java` 696 行、`init/ModBlocks.java` 630、`compat/ponder/scene/PressingTubScenes.java` 570、`datagen/datamap/DrinkEffectDataProvider.java` 445、`datagen/model/BlockStateGenerator.java` 444、`blockentity/brew/PressingTubBlockEntity.java` 431、`block/deco/ChalkboardBlock.java` 379、`item/ShakerItem.java` 305

## 3. 入口与注册

主类 `src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/KaleidoscopeTavern.java:14`，构造器统一注册 10 个 DeferredRegister，并提供 `modLoc(path)` 工具方法：

```java
ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, GeneralConfig.init());
ModBlocks.BLOCKS.register(modEventBus);
ModBlocks.BLOCK_ENTITIES.register(modEventBus);
ModItems.ITEMS.register(modEventBus);
ModRecipes.RECIPE_SERIALIZERS.register(modEventBus);
ModTreeDecoratorTypes.TREE_DECORATOR_TYPES.register(modEventBus);
ModFluids / ModParticles / ModEffects / ModSounds ...
```

- `init/register/CommonRegistry.java`（`@Mod.EventBusSubscriber(bus = MOD)`）集中做 `FMLCommonSetupEvent` 的 `event.enqueueWork(...)`：`NetworkHandler::init`、堆肥表 `ComposterBlock.COMPOSTABLES.put`、`TapBehaviorManager.register(...)` 8 条行为、**遍历 `ForgeRegistries.BLOCKS.getValues()` 找出所有 `BottleBlock` 并注册 `DispenserBlock.registerBehavior`**、`CuriosCompat::commonSetup`
- `init/register/CompatRegistry.java` 用 `InterModEnqueueEvent` + `ModList.get().isLoaded("carryon")` 惰性接 CarryOn 黑名单
- `init/register/DatapackReloadListenerEvent.java` 注册 `DrinkEffectDataReloadListener`
- RecipeType 同厨房做法：`RegisterEvent` 内 `RecipeType.simple(modLoc(...))`（`init/ModRecipes.java:32-39`），共 pressing_tub / barrel / shaker 三种

## 4. 核心系统

**A. 酒桶发酵（多阶段等级 + 错峰定时检查）** `blockentity/brew/BarrelBlockEntity.java:42`
- 常量集中在 API 接口：`api/blockentity/IBarrel.java` 定义 `MAX_ITEM_SLOTS=4`、`MAX_FLUID_AMOUNT=4000`、`BREWING_NOT_STARTED/STARTED/FINISHED(6)`
- **性能技巧**：`CHECK_INTERVAL = 97`（“选取最接近的质数，避免与其他周期性事件同时发生”），且 `int offset = this.hashCode() % CHECK_INTERVAL + CHECK_INTERVAL; tick = level.getGameTime() + offset;` 让每个酒桶错峰检查（`:50,106-107`）
- 字段：`ItemStackHandler ingredient`（`getSlotLimit` 覆写为 16“防止玩家浪费”）、`output`（仅计数显示）、`FluidTank fluid`、`open`、`brewLevel`、`brewTime`、`recipeId`；盖子未关不 tick
- 流体接口走 Forge Capability（`FluidTank` / `ItemStackHandler`）

**B. 龙头（Tap）行为注册表——非常干净的方块行为扩展点** `game/tap/TapBehaviorManager.java:13`
- `Map<Block, ITapBehavior> BEHAVIOR_MAP` + `register(Block, ITapBehavior)`；特例 `WaterloggedBehavior` 不进表，由 `hasWaterlogged(state)` 兜底（`:18,41-44`）
- 接口 `api/blockentity/ITapBehavior.java`：`isMatch(level, player, tapPos, tapState, sourceState, destinationState)` / `onStartExtract(...)` 返回 `ParticleOptions`（返回 null 无粒子）/ `onEndExtract(...)`，`player` 可为 null 以支持红石自动化；接口内提供 `sendParticles` 静态工具
- 内置实现 7 个：`BarrelTapBehavior/WaterCauldronTapBehavior/LavaCauldronTapBehavior/BeehiveTapBehavior/DragonHeadTapBehavior/WatermelonTapBehavior/WaterloggedBehavior`（`game/tap/impl/`），全部在 `CommonRegistry.addTapBehavior()` 里一行注册

**C. 压榨盆（Pressing Tub，踩踏式榨汁）** `blockentity/brew/PressingTubBlockEntity.java:46`
- `press(LivingEntity target, float fallDistance)`：先判 `MIN_FALL_DISTANCE`，用 `RecipeManager.CachedCheck<PressingTubRecipeContainer, PressingTubRecipe>` 命中配方（`:139-200`）；按“流体类型冲突 / 液体已满 / 产物为空 / 无配方”分别播放不同音效粒子并走 `dropContents()`
- 物品与流体走 Capability：`ItemStackHandler getItems()`、`FluidTank getFluid()`、`getCapability(...)`、`invalidateCaps()`（`:363-420`）

**D. 摇酒壶（Shaker，物品内储物的手持配方）** `item/ShakerItem.java:48`
- 用 NBT 键 `Storage` / `Result` 在 ItemStack 里存 `ItemStackHandler`（`getStorage/setStorage/hasStorage/getResult/removeAll`），`useOn` 倒出、`use` 摇动、`onUseTick/releaseUsing` 蓄力后调 `handRecipe(level, stack)` 用 `RecipeManager.getRecipeFor(ModRecipes.SHAKER_RECIPE, ...)`，配 `network/message/ClearShakerC2SMessage` 清空

**E. 黑板：多人共享文本方块** `block/deco/ChalkboardBlock.java:40` + `blockentity/deco/TextBlockEntity`
- 自定义属性 `POSITION = EnumProperty.create("position", PositionType.class)` + `HALF/HACING/WATERLOGGED`，实现多格拼合（`setPlacedBy` 里检查 left1/left2/right1/right2 邻格并逐个 `newBlockEntity` 补建，`:192-268`）
- 文本编辑走网络双向：`TextUpdateC2SMessage`（服务端写 NBT）+ `TextOpenS2CMessage`（服务端开输入界面），并有 `onBlockExploded` / `handleRemove` 统一回收文本

**F. 数据驱动的饮料效果（datamap）** `datamap/data/DrinkEffectData.java:21` + `datamap/resources/DrinkEffectDataReloadListener.java:22` + `datagen/datamap/DrinkEffectDataProvider.java`
- `record DrinkEffectData(Item item, List<List<Entry>> effects)`，第一层 list = **brew level → 效果组**，第二层 = 组内条目；`record Entry(MobEffect effect, int duration, int amplifier, float probability)`（概率触发）
- 用 `SimpleJsonResourceReloadListener(GSON, "datamap/drink_effect")` + `Codec`/`JsonOps` 解析，解析失败只 `LOGGER.error` 不崩溃；结果存在静态 `Map<Item, DrinkEffectData> INSTANCE`
- 消费点在 item 层：`item/DrinkBlockItem.java:128,187`、`item/BottleBlockItem.java:101`、`item/CocktailBlockItem.java:81,109`；另有 `datagen` Provider 生成 JSON

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/NetworkHandler.java:20` `SimpleChannel`（version "1.0.0"），4 个包：`TextUpdateC2SMessage(0)`、`TextOpenS2CMessage(1)`、`ClearShakerC2SMessage(2)`、`DrinkEffectSyncS2CMessage(3)`；附 `sendToClient(Player, Object)`（内部 `PacketDistributor.PLAYER`）/`sendToServer`
- **整表同步模式**：`DrinkEffectSyncS2CMessage.fromServer()` 把 `INSTANCE` 全量 `CODEC.encodeStart(NbtOps.INSTANCE, data)` → `ListTag` 塞进一个 `CompoundTag`，`buf.writeNbt` 一次发完，客户端解码后重建（`network/message/DrinkEffectSyncS2CMessage.java:32-55`）；触发点是 `DatapackReloadListenerEvent`（数据包重载时重发）
- 配置：`config/GeneralConfig.java` 仅 COMMON，分组 `push("tavern")`（`PressingTubDropContentsOnNonJuiceable`、`InfiniteLavaFromTap`）与 `push("vanilla bottle placement")`（水/蜂蜜/药水/龙息/经验瓶是否可放置）
- datagen：`datagen/DataGenerators.java:21-44`，client 出 BlockModel/BlockState/ItemModel/ParticleDescription，server 出 ModRecipe/LootTable/**DrinkEffectData**/SoundDefinitions，`vanillaPack.addProvider` 出 TagBlock/TagItem/TagEntityType
- 数据驱动资源：`src/main/resources` 只有 `META-INF` 与 mixins.json；`src/generated/resources` 由 datagen 生成

## 6. Mixin

`src/main/resources/kaleidoscope_tavern.mixins.json` 存在且 `required: true`、`compatibilityLevel: JAVA_17`、refmap `kaleidoscope_tavern.refmap.json`，但 **`mixins` 与 `client` 列表均为空**，仓库内无任何 `@Mixin` 类（`find -ipath '*mixin*'` 无 Java 结果）。需要改原版行为的场景全部改用 Forge 事件/能力/自定义属性实现；`build.gradle` 里仍配置了 `accessTransformer`（`src/main/resources/META-INF/accesstransformer.cfg`）与 mixin 插件（hotSwap/verbose/export）。

## 7. 值得学的 5 条具体做法

1. **周期性方块实体“错峰 + 质数间隔”轮询**：`CHECK_INTERVAL = 97` + `hashCode() % CHECK_INTERVAL` 偏移，`blockentity/brew/BarrelBlockEntity.java:50,106-107`；适用：发酵桶、磨盘等大量存在的慢速机器。
2. **方块行为外置为 Map 注册表 + 接口，并留“特殊兜底”分支**：`game/tap/TapBehaviorManager.java` + `api/blockentity/ITapBehavior.java`；适用：想让第三方或整合包给任意方块加交互（本例龙头对接原版炼药锅/蜂巢/西瓜）。
3. **纯数据效果表 + 重载监听 + 整表 NBT 同步**：`datamap/` 三件套 + `DrinkEffectSyncS2CMessage`；适用：整合包常改的效果/掉落数据，避免写死在代码里。
4. **一次扫描注册表批量挂原版行为**：`CommonRegistry.addDispenserBehavior()` 遍历 `ForgeRegistries.BLOCKS.getValues()`，命中 `BottleBlock` 即 `DispenserBlock.registerBehavior`；适用：有大量同族方块要挂发射器/交互行为。
5. **API 里放常量而非实现**：`api/blockentity/IBarrel.java`（容量/等级）、`api/blockentity/ITapBehavior.java`（`sendParticles` 静态工具）；适用：给第三方 mod 提供稳定的数值契约。

## 8. 公开 API（有独立 api 包）

- `api/blockentity/`：`IBarrel`、`IPressingTub`、`IShaker`、`ITapBehavior`（配套注册器 `game/tap/TapBehaviorManager#register`）
- `api/event/PlantGrapeEvent`（`@Cancelable`，玩家种植葡萄时触发，用于不同品种的种植逻辑）
- 外部接入方式：注册 `ITapBehavior`、监听 `PlantGrapeEvent`、JSON 数据（`datamap/drink_effect`、`recipes`）、Curios 饰品（`compat/curios/CuriosCompat`）、CarryOn 黑名单（`compat/carryon/BlackList`）、Create Ponder 教学场景（`compat/ponder`）、JEI/REI/EMI 三套插件（`compat/{jei,rei,emi}`）
