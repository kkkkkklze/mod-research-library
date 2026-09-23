# WitherRedstone/Kaleidoscope-DimensionsWine 源码分析

## 1. 基本信息
- Mod 名：森罗物语：次元酒窖 / Kaleidoscope Dimensions wine；mod_id `kaleidoscope_dim_wine`；作者 ChinaEX123、Fvue233（`src/main/templates/META-INF/neoforge.mods.toml` authors）；group `com.chinaex123.kaleidoscope_dim_wine`；版本 1.5.3-mc1.21.1-neoforge
- 目标：NeoForge 1.21.1（`gradle.properties`：neo_version=21.1.220、parchment 2024.11.17、moddev 2.0.141、Java 21）；许可证 MIT；源码包名根 `com.chinaex123.kaleidoscope_dim_wine`
- 依赖：必需 `kaleidoscope_tavern`（森罗物语：酒馆）`[1.0.1,)`，gradle 里写作 `curse.maven:kaleidoscope-tavern-1475175:8350856` 并注释"前置"；可选 twilightforest `[4.8.3345,)`、the_bumblezone `[7.13.0,)`、aether `[1.5.10,)`；localRuntime eternal-starlight/owo-lib/JEI/Jade/Accessories
- mods.toml 走 `src/main/templates` + `generateModMetadata` 占位符展开，输出 `src/generated/resources`

## 2. 源码规模与包结构
- 102 个 .java / 11667 行（含 datagen 与 compat）
- 包：`effect` 15、`init` 10、`data` 6、`util` 5、`data/advancements` 5、`block/crop/vanilla/WarpedGrape` 5、`block/crop/vanilla/CrimsonGrape` 5、`event` 4、`loot` 3、`item/crop` 3、`data/recipe` 3、`data/lootTable` 3、`init/compat/{Twilightforest,EternalStarlight,Aether}` 各 3、`block/crop/vanilla/Dreamfruit` 2、`init/compat/TheBumblezone` 2、`mixin` 2、`client/render` 2、`block/crop/vanilla/Hop` 2、`block/crop/compat/Twilightforest/FrostheartFruit` 2、`block/entity` 1、`fluid` 1、`config` 1、`item` 2
- 最大文件：`util/ColorCalculator.java` 1253 行、`block/crop/vanilla/Dreamfruit/DreamfruitCropWildVineHead.java` 411、`data/ModItemTagsProvider.java` 375、`data/recipe/ModRecipesProvider.java` 279、`DreamfruitCropWildVinePlant.java` 266、`WarpedGrapevineTrellisBlock.java` 261、`util/GradientTextHelper.java` 260、`fluid/DragonBlood.java` 257

## 3. 入口与注册
- 主类 `src/main/java/com/chinaex123/kaleidoscope_dim_wine/KaleidoscopeDimensionsWine.java:28-76`：注册 KDWBlocks / KDWItems / KDWFluids(FLUID_TYPES + FLUIDS) / KDWEffects / KDWCreativeTabs、`DrinkBlockEntityTypeEventHandler::onBlockEntityTypeAddBlocks`、`KDWConfig.SPEC`(COMMON)、`ModRecipes.RECIPE_SERIALIZERS`
- 4 个可选前置各用一个 `if (ModList.get().isLoaded("xxx"))` 块按需注册（twilightforest / the_bumblezone / aether / eternal_starlight，行 47-75），对应注册类集中在 `init/compat/<ModName>/`（Blocks/Items/Fluids 三件套）
- 注册框架：`DeferredRegister.create(...)` + `DeferredHolder`（`init/KDWEffects.java:14-40`、`init/KDWFluids.java:19-20`），流体用 `NeoForgeRegistries.FLUID_TYPES` + `BuiltInRegistries.FLUID`，每酒两个 ID（源/流动）

## 4. 核心系统
1. 复用前置方块实体：`block/entity/DrinkBlockEntityTypeEventHandler.java:26-30` 监听 NeoForge `BlockEntityTypeAddBlocksEvent`，取 `ResourceLocation.tryBuild("kaleidoscope_tavern","drink")` 的 BE 类型，把本 mod（含 4 个维度 compat）的全部酒方块批量加入 → 不新增 BE 类型即可复用酒馆的酒逻辑。
2. 维度作物系统：`block/crop/vanilla/{CrimsonGrape,WarpedGrape,Dreamfruit,Hop}/` 每种 4 件套（CropBlock / WildVineHead / WildVinePlant / TrellisBlock）+ `item/crop/*Item`；compat 侧 `block/crop/compat/Twilightforest/FrostheartFruit/`。
3. 自定义效果：`init/KDWEffects.java:14-40` 注册 15 个 MobEffect（枯萎斩/狂怒/火焰攻击/后发制人/嗜血/悖论/硬化/自然祝福/霜寒/霜降/巨大化/迷你化/高兴/苍穹之赐/无界之赐），实现在 `effect/` 各自类中，`event/EffectAttributeRemoveHandler.java` 统一处理属性修饰符移除。
4. 龙血机制：`fluid/DragonBlood.java`（`@EventBusSubscriber`），NBT 键 `DragonBloodData`/`TimeInFluid`/`HasReward`，`REWARD_TIME_TICKS = 20*60*3`、`CLEAR_SIZE = 3`，`PlayerEvent.Clone` 中按 `isWasDeath()` 复制奖励状态并给永久生命加成。
5. 文本工具：`util/GradientTextHelper.java:17-` 14 个 `createXxxGradientText(text, leftToRight, speed, bold, italic, underlined, strikethrough, obfuscated)`；算法全在 `util/ColorCalculator.java`（1253 行，入参 `GradientTextHelper.ColorParams` 的纯函数），用于酒名等渐变/呼吸文字。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：未发现自定义 payload（无 network 包），同步依赖前置与 NeoForge 默认机制。
- 数据驱动：`data/DataMaps.java:20-40` extends `DataMapProvider`，用 `builtInRegistryHolder()` 往 `NeoForgeDataMaps.COMPOSTABLES` / `FURNACE_FUEL` 写条目（并按 `ModList.isLoaded` 分区加 compat 条目）；`data/loot/Injector` 风格见 `loot/{BlockLootInjector,ChestLootInjector,EntityLootInjector}.java`。
- 配置：`config/KDWConfig.java` 注册为 COMMON。
- datagen：`data/ModDataGenerator.java:22-38` 监听 `GatherDataEvent` 注册 8 个 provider（ModItemModelsProvider、LootTableGenerator、ModItemTagsProvider、ModFluidTagsProvider、ModBlockTagsProvider、ModRecipesProvider、DataMaps、ModAdvancements），build.gradle 已把 `src/generated/resources` 纳入 sourceset。

## 6. Mixin
- 配置 `src/main/resources/kaleidoscope_dim_wine.mixins.json`：JAVA_21、`overwrites.requireAnnotations=true`、`injectors.defaultRequire=1`，仅 2 个 mixin
- `mixin/StringLightsBlockMixin.java:27-36`：`@Mixin(StringLightsBlock.class)` + `@Inject(method="useItemOn", at=@At("HEAD"), cancellable=true)`
- `mixin/EntityMixin.java:10`：`@Mixin(Entity.class)`（具体注入点未逐行确认）

## 7. 值得学的 5 条
1. 用 `BlockEntityTypeAddBlocksEvent` 把新方块挂进依赖 mod 已有的 BE 类型（`block/entity/DrinkBlockEntityTypeEventHandler.java:26-30`）→ 做前置模组的"新增方块"扩展时零重复逻辑。
2. DataMaps provider 化堆肥/燃料（`data/DataMaps.java:20-40`）→ 1.21 取代 `ComposterBlock.COMPOSTABLES` 硬编码的现代写法。
3. 兼容代码按 `init/compat/<ModName>/{Blocks,Items,Fluids}` 分包，主类按 `ModList.isLoaded` 分块注册（`KaleidoscopeDimensionsWine.java:47-75`）→ 多可选前置时便于增删。
4. 掉落注入拆成 Block/Chest/Entity 三个 Injector（`loot/` 包）→ 不改原版战利品表就追加内容。
5. 渐变文字拆成"纯算法 ColorCalculator + Component 组装 GradientTextHelper"（`util/ColorCalculator.java:17-`、`util/GradientTextHelper.java:17-`）→ 十几个配色变体仍可维护、可单测。

## 8. 公开 API
不适用（内容型扩展模组，未导出 API 包）。其对外接入方式是反向的：通过前置注册名 `kaleidoscope_tavern:drink` 复用酒馆的 BlockEntityType，并用 `KDWFluids.id()`/主类 MOD_ID 生成自身注册名。
