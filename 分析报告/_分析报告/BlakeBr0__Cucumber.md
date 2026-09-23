# Cucumber 源码分析报告

## 1. 基本信息
- Mod 名 Cucumber Library / mod_id `cucumber` / 作者 BlakeBr0 / 版本 26.1.2-9.0.6 / 许可证 MIT（`build.gradle:9`、`src/main/resources/META-INF/neoforge.mods.toml`）
- 目标：NeoForge-only 单模块，MC **26.1.2**（`versionRange="[26.1.2,26.2)"`，依赖 neoforge `[26.1.2.41-beta,)`），Java 25 toolchain（`build.gradle:15`）。注意：该快照比 1.21.1 更新，类名已变（`Identifier` 取代 `ResourceLocation`、输出用 `ItemStackTemplate`、存档用 `ValueInput`），移植到 1.21.1 需自行降级 API
- Gradle 插件：仅 `net.neoforged.moddev 2.0.141`（`build.gradle:1-6`）；`-Dmixin.debug.export=true`
- 编译依赖：JEI `compileOnly`（common-api + neoforge-api，`jei_version=29.5.0.28`）、`almostunified_version=1.21.1-1.0.0`、maven blamejared（`build.gradle`）。它是纯前置库，被 BlakeBr0 全家桶（Mystical Agriculture 等）依赖

## 2. 源码规模与包结构
实测 118 个 `.java`、5806 行，包根 `src/main/java/com/blakebr0/cucumber/`。文件数分布：`item/tool` 13、`client/screen` 6、`client/handler` 5、`crafting/recipe` 4、`inventory/slot` 3、`compat/jei` 2、`client/properties` 2；其余 `block`(8)、`helper`(10)、`iface`(6)、`util`(13)、`crafting`(5)、`event`(5)、`init`(4)、`client/extensions`、`client/sound`、`command`、`config`、`container`、`energy`、`lib`、`mixin`、`tileentity` 各 1-3 个。
最大文件：`item/BaseWateringCanItem.java` 252、`inventory/CItemStacksHandler.java` 237、`crafting/TagMapper.java` 207、`item/tool/BaseScytheItem.java` 177、`helper/ColorHelper.java` 148、`item/tool/BasePaxelItem.java` 137、`crafting/recipe/ShapedTransferDamageRecipe.java` 132、`crafting/recipe/ShapelessTagRecipe.java` 128。

## 3. 入口与注册
`src/main/java/com/blakebr0/cucumber/Cucumber.java:29` `@Mod(Cucumber.MOD_ID)`，构造器内容：

```java
bus.register(this);
ModDataComponentTypes.REGISTRY.register(bus);
ModSounds.REGISTRY.register(bus);
ModConditionSerializers.REGISTRY.register(bus);
ModRecipeSerializers.REGISTRY.register(bus);
if (FMLEnvironment.getDist() == Dist.CLIENT) { bus.register(new ItemModelPropertyHandler()); ... }
FeatureFlagInitializer.init();
mod.registerConfig(ModConfig.Type.CLIENT, ModConfigs.CLIENT);
mod.registerConfig(ModConfig.Type.COMMON, ModConfigs.COMMON);
```

注册框架是标准 `DeferredRegister`，集中在 `init/` 四个类：`ModDataComponentTypes`（`watering_can_filled`，`persistent(Codec.BOOL).networkSynchronized(ByteBufCodecs.BOOL)`）、`ModConditionSerializers`（`feature_flag` → `FeatureFlagCondition.CODEC`，注册到 `NeoForgeRegistries.CONDITION_SERIALIZERS`）、`ModRecipeSerializers`（`shaped_transfer_damage`/`shaped_transfer_components`/`shaped_tag`/`shapeless_tag`，`DeferredRegister.create(BuiltInRegistries.RECIPE_SERIALIZER, MOD_ID)`）、`ModSounds`。游戏事件在 `FMLCommonSetupEvent` 里注册到 `NeoForge.EVENT_BUS`（`ModCommands`、`TagMapper`），客户端在 `FMLClientSetupEvent` 里注册三个 handler。

## 4. 核心系统
1. **标签配方体系**（`crafting/`）：`TagMapper`（207 行）把 `cucumber-tags.json` 里的 tag→物品映射解析出来，`TagsUpdatedEvent` 触发 `reloadTagMappings()`，`getItemForTag(String)`/`getItemStackForTag(String,int)` 供配方使用；配合 `OutputResolver`（`interface OutputResolver` + 内部 `class Tag`/`class Item`，各自 `MapCodec` + `resolve() → ItemStackTemplate`）和 `ShapedRecipePatternCodecs`（自定义 `MAP_CODEC`/`SYMBOL_CODEC`，让 shaped pattern 的 key 可以是 tag）；四个配方序列化器 `ShapedTagRecipe`/`ShapelessTagRecipe`/`ShapedTransferDamageRecipe`/`ShapedTransferComponentsRecipe`（合成时把耐久/组件从输入传递到输出）。
2. **配方生命周期事件**（`event/RecipeManagerLoadingEvent.java`、`RecipeManagerLoadedEvent.java`）：前者暴露 `getRecipeManager()`/`getRegistries()`/`addRecipe(RecipeHolder<?>)`，让下游在配方加载中途注入；后者只读。由两个 mixin 触发（见第 6 节）。
3. **FeatureFlag 开关系统**（`util/FeatureFlag.java:8`、`FeatureFlagInitializer`、`config/ModFeatureFlags.java`）：`FeatureFlag.create(Identifier, Supplier<Boolean>)` 存进静态 `HashMap<Identifier, FeatureFlag> REGISTRY`，`ModFeatureFlags` 用 `@FeatureFlags` 注解标记后由 `FeatureFlagInitializer.init()` 扫描注册；数据包侧通过 `FeatureFlagCondition`（NeoForge `ICondition`）让 JSON 按开关加载，`FeatureFlagDisplayItemGenerator` 控制创造标签显示。
4. **通用基类工具箱**：`block/BaseBlock/BaseSlabBlock/BaseStairsBlock/BaseOreBlock/BaseLiquidBlock/BaseGlassBlock/BaseWallBlock/BaseTileEntityBlock`、`item/BaseItem/BaseBlockItem/BaseArmorItem/BaseBucketItem/BaseReusableItem/BaseShinyItem/BaseWateringCanItem`、`item/tool/`(BaseScytheItem/BasePaxelItem/BaseSickleItem/BaseCrossbowItem 等 13 个)、`tileentity/BaseInventoryTileEntity`、`container/ExtendedContainerMenu`/`BaseContainerMenu`、`inventory/CItemStacksHandler`+`SidedInventoryWrapper`+`RecipeInventory`、`energy/CEnergyStorage`、`helper/`(ColorHelper/BlockHelper/CropHelper/FluidHelper/ItemResourceHelper/RecipeHelper/TileEntityHelper/VecHelper/ParsingHelper)。
5. **客户端表现层**（`client/handler/`）：`BowFOVHandler`（拉弓 FOV）、`TagTooltipHandler` + `DataComponentTooltipHandler`（Ctrl/Alt 显示 tag/组件，配套 `lib/Tooltips.java` 常量与 `ModConfigs` 两个开关）、`TintSourceHandler`、`ItemModelPropertyHandler`，另 `client/extensions/WateringCanClientItemExtensions`、`client/sound/WateringCanSound`、`client/ModRenderTypes`、`client/screen/`(6 个) + `screen/button`、`screen/widget`。
6. **兼容与命令**：`compat/jei/JeiCompat` + `ShapedTagRecipeCategoryExtension`（把 tag 配方显示进 JEI）、`compat/almostunified/AlmostUnifiedAdapter`（统一化模组联动）、`command/ModCommands`（注册在 NeoForge 事件总线）。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络：无自定义包（无 `network` 包、无 `RegisterPayloadHandlersEvent`）。数据驱动：配方序列化器 + `ICondition` 条件（`feature_flag`）+ `TagMapper` 读取 `cucumber-tags.json`（`ModConfigs.MOD_TAG_PRIORITIES` 决定优先用哪个 mod 的物品，`AUTO_REFRESH_TAG_ENTRIES` 自动刷新失效条目）。配置：`config/ModConfigs.java` 用 `ModConfigSpec.Builder` 分 `CLIENT`/`COMMON` 两段（`tagTooltips`/`dataComponentTooltips`、`modTagPriorities`/`autoRefreshTagOptions`）。datagen：无 `GatherDataEvent`/`DataGenerator`。

## 6. Mixin
`src/main/resources/cucumber.mixins.json`（`compatibilityLevel: JAVA_25`，`refmap: cucumber.refmap.json`）：
- `mixin/RecipeManagerMixin`：`@Inject(at = @At(value="INVOKE", shift=AFTER, target="Ljava/util/SortedMap;forEach(...)V"), method="prepare(...)")`，用 mixinextras `@Local(name="recipeHolders")` 取列表后 `RecipeHelper.fireRecipeManagerLoadingEvent(...)`。
- `mixin/ReloadableServerResourcesMixin`：`@Inject(at=RETURN, method="updateComponentsAndStaticRegistryTags()V")` 触发 Loaded 事件（注释：此时配方已是可用终态）。
- `mixin/ItemStackMixin`：构造器 `RETURN` 处对实现 `IComponentInitializer` 的物品调用 `initialize(stack)`；`applyDamage` 内 `shrink(I)V` ordinal 0 处 `NeoForge.EVENT_BUS.post(new ItemBreakEvent(...))`。
- client：`mixin/ModelBakeryMixin`。

## 7. 值得学的 5 条具体做法
1. 用 mixin + `@Local` 从原版 `RecipeManager#prepare` 内部抓 `recipeHolders` 并发自定义事件，从而给出"配方加载中"可写扩展点（`mixin/RecipeManagerMixin.java:26-43`）。
2. 让 JSON 配方/数据按开关加载：把自定义 `ICondition` 注册进 `NeoForgeRegistries.CONDITION_SERIALIZERS`，用 `@FeatureFlags` + `FeatureFlagInitializer` 从配置生成开关（`init/ModConditionSerializers.java`、`util/FeatureFlag.java:20`）。
3. 自定义 `ShapedRecipePattern` codec 使 shaped 配方的 key 支持 tag（`crafting/ShapedRecipePatternCodecs.java:36-52`），并用 `OutputResolver` 把"输出是 tag"抽象成接口 + 双实现。
4. `ItemStackMixin` 在构造器 RETURN 处调用 `IComponentInitializer`，等于给物品加了"构造后初始化"钩子（`mixin/ItemStackMixin.java:36-40`），无需覆盖每个 `Item` 子类。
5. 库的每个功能开关都挂 `ModConfigSpec` 并由 `lib/Tooltips` 统一管理文案，客户端 handler 只读配置（`client/handler/TagTooltipHandler` + `config/ModConfigs.java`）。

## 8. 公开 API（库/前置类）
扩展点：`iface/`（`IComponentInitializer`、`IColored`、`IFluidHolder`、`IToggleableSlot`、`IHoverTextProvider`、`ICustomBow`）、`lib/`（`ModTags.MINEABLE_WITH_PAXEL`/`MINEABLE_WITH_SICKLE`、`Tooltips` 常量）、`event/`（`RecipeManagerLoadingEvent`/`RecipeManagerLoadedEvent`/`ItemBreakEvent`/`RegisterClientItemsEvent`/`ScytheHarvestCropEvent`）、`crafting/`（`OutputResolver`、`ShapedRecipePatternCodecs`、四个配方序列化器）、`util/FeatureFlag`+`FeatureFlags` 注解、`tileentity/BaseInventoryTileEntity` 与全部 `Base*` 基类。下游 mod 通过 `Cucumber.MOD_ID` 依赖并直接使用这些公开类（无独立的 api 包命名约定）。
