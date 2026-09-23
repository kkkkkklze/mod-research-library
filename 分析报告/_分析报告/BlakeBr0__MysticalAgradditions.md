# BlakeBr0/MysticalAgradditions 源码分析报告

## 1. 基本信息

- Mod 名 Mystical Agradditions；mod_id `mysticalagradditions`；作者 BlakeBr0（credits Mark719, xun468）；MIT（`src/main/resources/META-INF/neoforge.mods.toml:1`）
- 目标 MC `26.1.2`（依赖区间 `[26.1.2,26.2)`）/ NeoForge `26.1.2.71`，Java 25，插件 `net.neoforged.moddev` 2.0.141，版本 `26.1.2-9.0.3`（`gradle.properties`、`build.gradle`）
- 依赖：**Cucumber**（BlakeBr0 通用库）、**MysticalAgriculture**（宿主，提供作物 API）、Jade（implementation）、Patchouli/JEI（runtimeOnly/compileOnly）
- 代码使用 `net.minecraft.resources.Identifier`、`ValueInput/ValueOutput`、`GameRules` 新签名，属较新 MC 分支快照

## 2. 源码规模与包结构

35 个 `.java` / 1652 行。`src/main/resources` 仅有 `META-INF/{neoforge.mods.toml,accesstransformer.cfg}`——**本 checkout 无 assets/data（无 lang/模型/配方 json）**。

包（`com.blakebr0.mysticalagradditions`）：`init`(7)、`item`(6)、`world/modifiers`(4)、`lib`(4)、`compat/tconstruct/modifier`(3)、`config`(2)、`handler`(2)、`client/handler`(2)、`util`(2)、`block`(1)

最大文件：`item/EssencePaxelItem.java`(153)、`init/ModFluids.java`(146)、`init/ModCreativeModeTabs.java`(99)、`util/EssenceAppleTier.java`(77)、`init/ModBlocks.java`(73)、`block/InfusedFarmlandBlock.java`(72)

## 3. 入口与注册

主类 `MysticalAgradditions.java`：

```java
@Mod(MysticalAgradditions.MOD_ID)
public final class MysticalAgradditions {
    public MysticalAgradditions(IEventBus bus, ModContainer mod) {
        bus.register(this); bus.register(new ModFluids()); bus.register(new RegisterCapabilityHandler());
        ModBlocks.REGISTRY.register(bus); ModItems.REGISTRY.register(bus); ModCreativeModeTabs.REGISTRY.register(bus);
        ModBiomeModifiers.REGISTRY.register(bus); ModFluidTypes.REGISTRY.register(bus);
        if (FMLEnvironment.getDist() == Dist.CLIENT) { bus.register(new FluidModelHandler()); bus.register(new TintSourceHandler()); }
        mod.registerConfig(ModConfig.Type.STARTUP, ModConfigs.COMMON, "mysticalagradditions-common.toml");
    }
    @SubscribeEvent public void onCommonSetup(FMLCommonSetupEvent e) { NeoForge.EVENT_BUS.register(new MobDropHandler()); }
    public static Identifier resource(String path) { return Identifier.fromNamespaceAndPath(MOD_ID, path); }
}
```

全用 NeoForge `DeferredRegister`（无 Registrate）。顺序技巧：`init/ModItems.java:19` 静态块 `ModBlocks.BLOCK_ITEMS.forEach(REGISTRY::register)`，注释"for class load order purposes"。

## 4. 核心系统

**A. 宿主内容注册（对外接入点）** `lib/ModCorePlugin.java`
- `@MysticalAgriculturePlugin implements IMysticalAgriculturePlugin`：`configure(PluginConfig)` 里 `setModId` + `disableDynamicSeedCraftingRecipes/InfusionRecipes/ReprocessingRecipes()`
- 两段式注册：`onRegisterCrops(ICropRegistry)` 注册作物/等级，`onPostRegisterCrops` 再注入交叉引用（`Crop.setCruxBlock`）

**B. 作物与等级** `lib/ModCrops.java`、`lib/ModCropTiers.java`
- 一行声明一个作物：`new Crop(resource("nether_star"), ModCropTiers.SIX, CropType.RESOURCE, LazyIngredient.item("minecraft:nether_star"))`；跨 mod 材料用 `LazyIngredient.tag(...)`
- `withRequiredMods(crop, "botania", ...)`：`ModList.get()::isLoaded` 判断，`DEBUG = !FMLEnvironment.isProduction()` 时强制全开（`:60`）
- `ModCropTiers.SIX` 在 post 阶段链式 `setFarmlandBlock/setEssenceItem/setFertilizable/setSecondarySeedDrop`

**C. 生物掉落** `handler/MobDropHandler.java`
- 在 `FMLCommonSetupEvent` 注册到 `NeoForge.EVENT_BUS`；`LivingDropsEvent` 中先查 `level.getGameRules().get(GameRules.MOB_DROPS)`，凋灵按 `WITHERING_SOUL_DROP_CHANCE` 概率、末影龙按 `DRAGON_SCALES_AMOUNT` 数量

**D. 生物群系矿物（数据驱动）** `init/ModBiomeModifiers.java` + `world/modifiers/*`
- 4 个 `record XxxOreModifier(HolderSet<Biome> biomes, Holder<PlacedFeature> feature) implements BiomeModifier`，各自 `RecordCodecBuilder.mapCodec`；`codec()` 返回注册在 `NeoForgeRegistries.BIOME_MODIFIER_SERIALIZERS` 的 DeferredHolder
- `modify()` 中 `phase == Phase.ADD && ModConfigs.GENERATE_XXX.get() && biomes.contains(biome)` 才 `addFeature(GenerationStep.Decoration.UNDERGROUND_ORES, feature)`——**用 codec 把配置开关绑进世界生成**

**E. 客户端与兼容** `client/handler/{FluidModelHandler,TintSourceHandler}.java`、`compat/JadeCompat.java`、`compat/tconstruct/modifier/*`
- Jade：`@WailaPlugin` + `IWailaPlugin.registerClient` 注册匿名 `IBlockComponentProvider`（UID `resource("infused_farmland")`），仅作用于 `InfusedFarmlandBlock.class`

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**
- 数据驱动：`world/modifiers` 的 BiomeModifier codec（数据文件缺失，未确认）；AT 仅一行 `public FarmlandBlock isNearWater`
- 配置：`config/ModConfigs.java` 单例 `ModConfigSpec COMMON`，分组 General/World，键 `witheringSoulChance(0.35)`、`dragonScalesAmount(8)`、`fertilizableTier6Crops(false)`、`essenceAppleDuration(180)`、`generateNether/End{Prosperity,Inferium}Ore(true)`；`config/ModFeatureFlags.java` 为特性开关
- datagen：`build.gradle` 无 data run，仓库无 generated 目录 → **未确认/无**

## 6. Mixin

**无**（只有 `META-INF/accesstransformer.cfg`）

## 7. 值得学的 5 条做法

1. **用宿主提供的插件注解接入，而不是 mixin/hack**：`@MysticalAgriculturePlugin` + `IMysticalAgriculturePlugin`；`lib/ModCorePlugin.java`。
2. **注册两段式（先建对象、post 阶段补交叉引用）**：`onRegisterCrops`/`onPostRegisterCrops`；同上 `:24`。
3. **`LazyIngredient` 声明式输入**：一行描述种子/副产物来源，避免注册期解析物品；`lib/ModCrops.java:20`。
4. **开发环境全开跨 mod 内容**：`if (DEBUG) return crop;`（非生产环境跳过 `isLoaded` 过滤）；`lib/ModCrops.java:60`。
5. **BiomeModifier 内直接读配置决定是否加矿**：`world/modifiers/NetherProsperityOreModifier.java:27`。

## 8. 公开 API / 对外接入

本 mod 无 `api` 包，是 MysticalAgriculture 的**内容扩展包**；它示范了外部接入路径：`IMysticalAgriculturePlugin`（`configure(PluginConfig)`、`onRegisterCrops/onPostRegisterCrops(ICropRegistry)`）+ `ICropRegistry.register/registerTier` + `LazyIngredient`。可作为"为他人 mod 编写内容附属"的模板。
