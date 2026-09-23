# Farmer's Delight 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Farmer's Delight / `farmersdelight` |
| 作者 | vectorwing |
| 目标 MC / 加载器 | 1.21.1 / NeoForge（`neo_version=21.1.219`，`gradle.properties`） |
| Gradle 插件 | `net.neoforged.moddev` 1.0.0（`build.gradle:6`），Java toolchain 21，Parchment `1.21/2024.07.28` |
| 许可证 | MIT |
| 编译依赖 | 仅 NeoForge + Minecraft（`neoforge.mods.toml` 中 `crafttweaker` 为 optional）；JEI / EMI / CraftTweaker / AppleSkin 仅作**软集成**，不进运行时依赖 |
| mods.toml 额外项 | `enumExtensions="META-INF/enumextensions.json"`（NeoForge 枚举扩展，把自己注册进创造模式标签等原版枚举） |

## 2. 源码规模与包结构

- 主源码 246 个 `.java`，**22563 行**（`find src/main/java -name '*.java' -exec wc -l {} +`）。
- 包分布（前 3 层，文件数）：`common/block` 43、`common/registry` 25、`common/block/entity` 21、`common/item` 19、`data` 14、`common/mixin` 11、`common/utility` 8、`client/renderer` 7、`common/crafting` 6、`client/gui` 6，其余（event/loot/network/world/effect/data-component）各 1-4。
- 顶层分包严格按 `client` / `common` / `data` / `integration` 四方划分，`integration` 下再分 `jei` `emi` `crafttweaker`，**第三方兼容代码零散落在主逻辑里**。
- 最大文件：`data/recipe/CraftingRecipes.java` 918、`common/block/entity/CookingPotBlockEntity.java` 569、`data/BlockStates.java` 526、`common/registry/ModItems.java` 508、`data/BlockTags.java` 408。

## 3. 入口与注册

主类 `src/main/java/vectorwing/farmersdelight/FarmersDelight.java:20`，`@Mod(MODID)`，构造注入 `(IEventBus modEventBus, ModContainer modContainer)`：

```java
modEventBus.addListener(CommonSetup::init);
if (FMLEnvironment.dist.isClient()) {
    modEventBus.addListener(ClientSetupEvents::init);
    modContainer.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new);
}
modContainer.registerConfig(ModConfig.Type.COMMON, Configuration.COMMON_CONFIG);
modContainer.registerConfig(ModConfig.Type.CLIENT, Configuration.CLIENT_CONFIG);
ModBlocks.BLOCKS.register(modEventBus); ModItems.ITEMS.register(modEventBus); ...
```

- **全量 DeferredRegister**，25 个 `Mod*` 注册类集中在 `common/registry/`，每个类自持一个 `DeferredRegister`，静态字段暴露为 `Supplier<T>`（如 `ModBlocks.STOVE`），注册在构造器里一次性 `.register(modEventBus)`。客户端配置 GUI 直接用 NeoForge 的 `ConfigurationScreen` 扩展点，不写自定义 Screen。
- `RegistryAliases.addRegistryAliases()`（`common/registry/RegistryAliases.java:16`）用 `DeferredRegister.addAlias` 保留 `basket → bamboo_basket` 的旧 ID 兼容。

## 4. 核心系统

1. **烹饪锅（多方块烹饪配方执行）** `common/block/entity/CookingPotBlockEntity.java:62`：实现 `MenuProvider, HeatableBlockEntity, Nameable, RecipeCraftingHolder`；`MEAL_DISPLAY_SLOT=6 / CONTAINER_SLOT=7 / OUTPUT_SLOT=8`；`RecipeManager.CachedCheck<RecipeWrapper, CookingPotRecipe> quickCheck` 做配方缓存；`Object2IntOpenHashMap<ResourceLocation> usedRecipeTracker` 统计配方使用次数用于发放进度；`cookingTick` 为 `BlockEntityTicker` 静态方法。
2. **砧板切割（带概率与工具匹配的配方）** `common/crafting/CuttingBoardRecipe.java:34`：字段 `Ingredient input / Ingredient tool / NonNullList<ChanceResult> results / Optional<SoundEvent> soundEvent`；`rollResults(RandomSource, fortuneLevel, inventory)` 按附魔幸运等级滚动产出；`MAX_RESULTS=4`；`Serializer` 里用 `Ingredient.LIST_CODEC_NONEMPTY.fieldOf("ingredients").flatXmap(...)` 把 JSON 数组折叠成单个 input，兼容 1.20 格式。
3. **数据组件驱动的物品状态** `common/registry/ModDataComponents.java:20`：`meal` / `container` 用自建 `ItemStackWrapper`（`CODEC` + `STREAM_CODEC`）并 `.cacheEncoding()`；锅里的菜能"整锅打包成物品"，靠 BE 的 `applyImplicitComponents / collectImplicitComponents`（`CookingPotBlockEntity.java:494/502`）双向搬运。
4. **BE 网络同步基类** `common/block/entity/SyncedBlockEntity.java:17`：`getUpdatePacket` + `getUpdateTag = saveWithoutMetadata`，`inventoryChanged()` 内部 `setChanged()` + `level.sendBlockUpdated(..., Block.UPDATE_CLIENTS)`，所有机器方块统一继承，避免重复样板。
5. **世界生成：过滤器式 BiomeModifier** `common/world/modifier/AddFeaturesByFilterBiomeModifier.java:16`（`record ... implements BiomeModifier`）+ `common/world/filter/BiomeTagFilter.java:16`（`extends PlacementFilter`），把"按生物群系标签注入野生作物"做成数据驱动的 JSON（`data/farmersdelight/neoforge/biome_modifier/`），自定义 `WildCropConfiguration` + `WildCropFeature`。
6. **食物效果** `common/effect/NourishmentEffect.java` / `ComfortEffect.java`：Nourishment 通过 mixin 实现"饱食度满也能继续吃"。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`common/network/ModNetworking.java:18`，`@EventBusSubscriber` 监听 `RegisterPayloadHandlersEvent`，`event.registrar("1")` 版本号 + `playToClient` / `playToServer`；两个 payload 均为 `record implements CustomPacketPayload`，`StreamCodec.unit(INSTANCE)` 用于无参包（`payload/FlipSkilletPayload.java`），处理器以静态内部类 `ClientPayloadHandler` / `ServerPayloadHandler` 分侧。
- **数据驱动**：自定义 `RecipeType` + `RecipeSerializer`（cooking / cutting / food_serving / dough）；`ModLootModifiers` 注册 4 个 `MapCodec<? extends IGlobalLootModifier>`（add_item / replace_item / add_loot_table / pastry_slicing）；`ModConditionCodecs` 注册自定义 `ICondition`；`ModIngredientTypes` 注册 `item_ability`（`ItemAbilityIngredient`，按"物品能力"而非物品匹配）；产物写入 `src/generated/resources/data/`。
- **配置**：`common/Configuration.java`，纯 `ModConfigSpec.Builder`，按 `settings/farming/crafting/overrides/world/debug` 分 push 段，客户端项单独一份 CLIENT_CONFIG。
- **datagen**：`data/DataGenerators.java:42` 监听 `GatherDataEvent`，一次性 addProvider 服务端 13 个（tags / recipes / loot / data_maps / advancements / `StructureUpdater`）+ 客户端 3 个（blockstates / item models / sounds），配方生成器拆成 `data/recipe/{Crafting,Cooking,Cutting}Recipes.java`。

## 6. Mixin

配置 `src/main/resources/farmersdelight.mixins.json`，`JAVA_21`，`injectors.defaultRequire=1`，`mixins` 12 个 + `client` 2 个（`CanvasSignEditScreenMixin`、`HideBlockBreakProgressMixin`），另有 `datafix/` 3 个（`ItemStackComponentizationFixMixin`、`V1460Mixin`、`V3818_3Mixin`）做旧存档数据升级。代表 hook：

- `NourishmentAlwaysEatMixin.java:15` → `Player#canEat` @At("HEAD") cancellable，有 NOURISHMENT 效果时强行返回 true。
- `KeepRichSoilUntrampledMixin.java:14` → `FarmBlock#turnToDirt` HEAD 取消，保护富土耕地不被踩坏。
- `RopeFenceConnectionMixin.java:15` → `FenceBlock#connectsTo` / `#isSameFence` HEAD 返回 false，阻止绳子栅栏与原版栅栏相连。

## 7. 值得学的 5 条做法

1. **注册类按注册表 1:1 拆分 + `Mod*` 前缀**，主类只做 21 行 `.register(modEventBus)` 编排 → `FarmersDelight.java:36-56`；适用任何中型 mod 起步。
2. **`SyncedBlockEntity` 基类封装 BE 同步样板**（updateTag / updatePacket / inventoryChanged）→ `common/block/entity/SyncedBlockEntity.java`；所有带库存机器直接继承。
3. **用 DataComponent 把"方块内容物"变成可搬运的物品数据**（`meal`/`container` + `applyImplicitComponents`/`collectImplicitComponents`）→ `common/registry/ModDataComponents.java`、`CookingPotBlockEntity.java:494`；适用"机器内容物可掉落/可装箱"。
4. **概率产出 + 工具匹配的配方用 `flatXmap` 兼容旧 JSON 形状** → `common/crafting/CuttingBoardRecipe.java:163-190`；适用自定义配方需要向后兼容数据包。
5. **兼容代码独立 `integration/<mod>` 包 + `neoforge.mods.toml` 里声明 optional 依赖**，JEI/EMI/CraftTweaker 各自 Plugin 入口 → `integration/jei/JEIPlugin.java`、`integration/emi/EMIPlugin.java`、`integration/crafttweaker/FarmersDelightCrTPlugin.java`；适用任何要接 JEI/EMI/脚本语言的 mod。

## 8. 公开 API / 扩展点

非库模组，无独立 API 包。外部接入方式为：① 数据包层（`farmersdelight:cooking` / `:cutting` 配方、`farmersdelight` 标签、`data/neoforge/loot_modifiers`）；② 注册别名与数据组件可被其他 mod 读取（`ModDataComponents.MEAL/CONTAINER`）；③ `ModBlocks.ROPE_FENCE` 等方块允许被 mixin/标签扩展。JEI/EMI 分类通过 `integration/*` 注册，不对外暴露 Java API。
