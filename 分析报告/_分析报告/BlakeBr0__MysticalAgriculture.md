# BlakeBr0/MysticalAgriculture 源码分析报告

## 1. 基本信息

- Mod 名/ID：Mystical Agriculture / `mysticalagriculture`；作者 BlakeBr0（credits Mark719、xun468、Cavemanrockx）；version `26.1.2-9.0.9`
- 目标版本：**MC 26.1.2 + NeoForge 26.1.2.71**（Java 25，ModDevGradle 2.0.141）——此检出是新分支，不是 1.21.1/1.20.1 布线
- 许可证 MIT（`src/main/resources/META-INF/neoforge.mods.toml`）
- 依赖：`cucumber`（BlakeBr0 自家前置库，required）；JEI 29.5.0.28、Jade、TOP、Patchouli `26.1-94`、CraftTweaker `1.21:20.0.21`（均来自 `gradle.properties`）；有 `META-INF/accesstransformer.cfg`，**无 mixin**

## 2. 源码规模与包结构

- 284 个 `.java`，**24099 行**。主要包：`api/*`(60)、`augment`(26)、`block`(19)、`item`(16)、`tileentity`(13)、`item/tool`(13)、`init`(12)、`crafting/recipe`(9)、`lib`(8)、`container`(8)、`compat/jei/category`(8)、`client/tesr`(16)、`client/screen`(8)、`registry`(4)、`network/payloads`(4)
- 最大文件：`api/crop/Crop.java`(577)、`tileentity/SouliumSpawnerTileEntity.java`(516)、`lib/ModCrops.java`(398)、`tileentity/HarvesterTileEntity.java`(345)、`init/ModCreativeModeTabs.java`(326)、`api/tinkering/Augment.java`(301)

## 3. 入口与注册

`MysticalAgriculture.java:58` `@Mod`，构造注入 `IEventBus`/`ModContainer`：`bus.register(new ModBlocks()/ModItems()/ModDataGenerators())` + 10 个 `DeferredRegister`（CreativeModeTabs/TileEntities/DataComponentTypes/MenuTypes/IngredientTypes/ConditionSerializers/RecipeTypes/RecipeSerializers/WorldFeatures/BiomeModifiers），`registerConfig(STARTUP, "mysticalagriculture-common.toml")`，最后 `initAPI()` + `PluginRegistry.getInstance().loadPlugins()`。`initAPI()`（`:133-158`）用反射把 `CropRegistry/AugmentRegistry/MobSoulTypeRegistry` 单例写进 `MysticalAgricultureAPI` 的私有静态字段，避免 API 类直接引用实现。

## 4. 核心系统

- **Crop 抽象**（`api/crop/Crop.java`）：一个 Crop = id + CropTier + CropType + 三套颜色 + `CropModels`（贴图模板）+ 延迟 `Supplier<CropBlock>/<Item> essence/<Item> seeds/<Block> crux` + `LazyIngredient craftingMaterial` + `CropRecipes` 开关 + `requiredBiomes`；`ModCrops.java` 用静态字段表列出全部内置作物，`withRequiredMods(crop,"ae2")` 在非 DEBUG 下按 `ModList.isLoaded` 自动 `setEnabled(false)`
- **注册期"用户没给就代建"**：`registry/CropRegistry.java:114-160` 在 `RegisterEvent` 里遍历 crops，`shouldRegisterCropBlock/EssenceItem/SeedsItem` 为真且用户未提供实现时 new 默认 `MysticalCropBlock/MysticalEssenceItem/MysticalSeedsItem` 并以 `名称+suffix` 注册；末尾 `getSortedCropsMap` 按 tier 排序，保证注册顺序稳定
- **插件 API**：`api/IMysticalAgriculturePlugin.java` 定义 configure + `onRegisterCrops/onPostRegisterCrops`（augments、mobSoulTypes 同构）；`registry/PluginRegistry.java:18-49` 先放内置 `ModCorePlugin`，再扫 `ModList.getAllScanData()` 里带 `@MysticalAgriculturePlugin` 注解的类，反射实例化后"全部 register → 全部 postRegister"，配置用 `api/lib/PluginConfig.java`
- **LazyIngredient**（`api/lib/LazyIngredient.java`）：只存字符串 id/tag + `DataComponentMap`，首次 `getIngredient(registries)` 时才解析（tag 走 `HolderLookup`，带组件时用 `DataComponentIngredient`），天然规避注册顺序
- **Augment / Tinkering**（`api/tinkering/Augment.java`）：`DeferredHolder.create(ITEM, id+"_augment")` 自动建物品；`EnumSet<AugmentType> types` 分类，事件回调 `onItemUse/onRightClick/onBlockDestroyed/onInventoryTick/onPlayerTick/onPlayerFall` + `getAttributeModifiers()` + `hasSetBonus()`；配套 `ITinkerable/AugmentComponent/AugmentUtils/AbilityCache` 与 `AugmentType/AOEAugment`
- **机器**：`tileentity/*` 13 个（灌注祭坛 248、觉醒祭坛 306、再处理器 319、灵魂刷怪笼 516、收割机 345、注矿机 320…）统一实现 `api/machine/IUpgradeableMachine` + `MachineUpgradeTier/MachineUpgradeItemStackHandler`

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/NetworkHandler.java` 用 `RegisterPayloadHandlersEvent` + `registrar("1")`；3 个 playToClient（ExperienceCapsulePickup、ReloadIngredientCache、SyncEssenceVesselColors）、1 个 playToServer（UpdateAOEAugmentOffset），各 payload 自带 `TYPE/STREAM_CODEC/handle*`
- datagen：`data/ModDataGenerators.java` 挂 `GatherDataEvent.Client`，注册 ItemModel/BlockModel/Recipe/ItemTags/BlockTags 5 个自定义 JsonGenerator（从 CropRegistry 反推生成），`build.gradle` 有 data run + `src/generated/resources`、`syncTestDatapacks/syncTestScripts`
- 动态数据：`DynamicRecipeManager`、`ModRecipeTypes.onDatapackSync`、`crafting/recipe` 9 个配方类 + `crafting/condition` 4 个条件、`RecipeIngredientCache`；CraftTweaker 兼容层 6 个类（Awakening/Enchanter/Infusion/Reprocessor/SoulExtractor/SouliumSpawner）

## 6. Mixin

无 Mixin（`grep spongepowered` 无命中），仅 `accesstransformer.cfg`。

## 7. 值得学的 5 条做法

1. API 与实现分离：`api/*` 只暴露接口/数据类，实现对单例 + 反射注入（`MysticalAgriculture.java:133`）。
2. 插件生命周期"register/postRegister 两段式"，post 阶段专门留给别人改自己的内容（`PluginRegistry.java:39-46`）。
3. 注册时用户未提供实现则自动生成默认方块/物品，扩展 mod 只需准备贴图（`CropRegistry.java:123-134`）。
4. `LazyIngredient` 把跨 mod 引用延迟到使用时刻解析，避免前置未加载（`api/lib/LazyIngredient.java:57`）。
5. datagen 从自家注册表反推模型/配方 JSON，几百个作物不用手写资源（`data/generator/*`）。
6. `@MysticalAgriculturePlugin` + `getAllScanData` 扫描实现"零配置接入"（`PluginRegistry.java:22-37`）。

## 8. 公开 API

包路径 `com.blakebr0.mysticalagriculture.api.*`：入口 `MysticalAgricultureAPI`（registry getter + `resource()`）、插件接口 `IMysticalAgriculturePlugin` + 注解 `MysticalAgriculturePlugin`、注册表接口 `ICropRegistry/IAugmentRegistry/IMobSoulTypeRegistry`、可继承数据类 `Crop/CropTier/CropType/CropModels/Augment/AugmentType/AOEAugment/MobSoulType`、配方接口 `crafting/I{Awakening,Infusion,Enchanter,OreInfusion,Reprocessor,SoulExtraction,SouliumSpawner}Recipe`、`MysticalAgricultureTags/ToolMaterials/DataComponentTypes/MysticalAgricultureConfigValues`。外部 mod 接入方式：依赖 `cucumber` 前置 + 在类上标 `@MysticalAgriculturePlugin` 并实现接口。
