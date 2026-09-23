# KaleidoscopeMods/KaleidoscopeCookery 源码分析报告

## 1. 基本信息

- Mod 名：Kaleidoscope Cookery（森罗物语：厨房）；mod_id `kaleidoscope_cookery`
- 作者：ysbbbbbb, tartaric_acid, Azumic；版本 `1.4.1-forge+mc1.20.1`
- **目标平台实为 Minecraft Forge 47.3.0 / MC 1.20.1，Java 17**（`gradle.properties`；本地仓库无 NeoForge 分支，`src/main/resources/META-INF/mods.toml` 为 Forge 格式，`modLoader = "javafml"`）
- Gradle 插件：`net.minecraftforge.gradle [6.0.16,6.2)`、`org.parchmentmc.librarian.forgegradle`、`org.spongepowered.mixin 0.7.+`，Gradle Wrapper 8.14.3
- 许可证：BSD-3-Clause（代码）+ CC BY-NC-SA 4.0（资源），见 `LICENSE-CODE` / `LICENSE-ASSETS`
- 依赖（`build.gradle`）：compileOnly JEI(15.20.0.105)/REI(12.1.785)/EMI(1.1.22)；implementation KubeJS 2001.6.5、Rhino、FarmersDelight 1.20.1-1.2.6、Create 6.0.6 + Ponder 1.0.80、Tetra 6.12.0、mutil、Jade、HarvestWithEase；runtimeOnly 大量（Sophisticated Backpacks、Diet、东方小女仆 TouhouLittleMaid、FTB 系等）——即“自身是内容 mod，同时给 JEI/REI/EMI/KubeJS/Create 做适配”

## 2. 源码规模与包结构

- `src/main/java` 下 `.java` 共 **393 个，13568 行**（`find src -name '*.java' | wc -l` / `wc -l` 汇总）；资源还含 `src/generated/resources`
- 根包 `com.github.ysbbbbbb.kaleidoscopecookery`，主要子包（深度 2，文件数）：`client/render` 24、`datagen/recipe` 15、`compat/jade` 14、`crafting/recipe` 13、`block/kitchen` 13、`crafting/serializer` 11、`compat/ponder` 11、`datagen/builder` 10、`compat/rei|jei` 各 10、`compat/kubejs` 9、`compat/emi` 9、`blockentity/kitchen` 9、`api/blockentity` 8、`init/registry` 7
- 最大文件：`init/ModFoods.java` 844 行、`blockentity/kitchen/StockpotBlockEntity.java` 642、`blockentity/kitchen/PotBlockEntity.java` 610、`entity/ScarecrowEntity.java` 537、`blockentity/kitchen/MillstoneBlockEntity.java` 496、`blockentity/kitchen/TeapotBlockEntity.java` 464、`datagen/recipe/MillstoneRecipeProvider.java` 443、`blockentity/kitchen/SteamerBlockEntity.java` 440
- 顶层包：init / api / block / blockentity / crafting / compat / client / datagen / datamap / effect / entity / event / inventory / item / loot / mixin / network / config / util / advancements

## 3. 入口与注册

主类 `src/main/java/com/github/ysbbbbbb/kaleidoscopecookery/KaleidoscopeCookery.java:17`，构造器里显式注册全部 DeferredRegister：

```java
IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, GeneralConfig.init());
ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, ClientConfig.init());
FoodBiteRegistry.init(); TeacupRegistry.init(); PlateRegistry.init(); ModTrigger.init();
ModBlocks.BLOCKS.register(modEventBus); ModItems.ITEMS.register(modEventBus);
ModEntities.ENTITY_TYPES.register(modEventBus); ModRecipes.RECIPE_SERIALIZERS.register(modEventBus);
ModLootModifier.GLOBAL_LOOT_MODIFIER_SERIALIZER.register(modEventBus);
```

- 注册集中在 `init/`：`ModBlocks`（含 `BLOCKS` + `BLOCK_ENTITIES` 两个 DeferredRegister 同文件声明）、`ModItems`、`ModEntities`、`ModEffects`、`ModPoi`、`ModVillager`（`VILLAGER_PROFESSION`）、`ModParticles`、`ModSounds`、`ModCreativeTabs`、`ModFoods`（纯常量食物数据）、`ModSoupBases`
- RecipeType 因 Forge 无 DeferredRegister 支持，用 `RegisterEvent` 手工赋值（`init/ModRecipes.java:44-61`），同一事件里 `CraftingHelper.register(AnyIngredient.ID, AnyIngredient.Serializer.INSTANCE)` 注册自定义 Ingredient
- 用 **AccessTransformer** 代替大量 mixin：`src/main/resources/META-INF/accesstransformer.cfg` 开了 `RecipeManager.byType`、`StructureTemplatePool.rawTemplates`、`Block.stateDefinition`、`MobEffectInstance.duration`、`Gui.renderTextureOverlay` 等

## 4. 核心系统

**A. 锅/汤锅烹饪（状态机 + 配方匹配）**
`blockentity/kitchen/PotBlockEntity.java:52`（`implements IPot`，610 行）与 `StockpotBlockEntity.java:56`。要点：
- 状态常量定义在 **API 接口**里：`api/blockentity/IPot.java:11-23` 定义 `PUT_INGREDIENT/COOKING/FINISHED/BURNT`；`tick()` 按状态分派 `tickPutIngredient/tickCooking/tickFinished/tickBurnt`（`PotBlockEntity.java:92-131`）
- 每 5 tick 做一次重活（热源/配方检查），代码注释 “每 5tick 刷新一次”（`PotBlockEntity.java:99`）
- 汤锅把配方 id 落盘而非存 ItemStack：NBT 键 `Inputs/RecipeId/SoupBaseId/Result/Status/CurrentTick/TakeoutCount/LidItem`（`StockpotBlockEntity.java:59-66`），并用 `recipeId + 客户端按 id 反查 recipe 拿 visuals` 省同步（`:197-200`）
- 配方匹配可被外部取消/修改：`StockpotMatchRecipeEvent.Post`（`StockpotBlockEntity.java:287`、`api/event/StockpotMatchRecipeEvent.java`）

**B. 汤底的可扩展注册表（第三方扩展点，很值得学）**
`api/recipe/soupbase/ISoupBase.java` 定义 `getName/getBubbleColor/getDisplayStack/isSoupBase/getReturnContainer/isContainer/getReturnSoupBase/getRender`；`crafting/soupbase/SoupBaseManager.java:11-42` 用 `LinkedHashMap<ResourceLocation, ISoupBase>` 做运行时注册表并提供 `registerFluidSoupBase/registerMobSoupBase` 便捷方法，重复注册直接抛 `IllegalArgumentException`。实现类 `FluidSoupBase/MobSoupBase/SimpleSoupBase`，客户端渲染独立为 `api/client/render/ISoupBaseRender`（`@OnlyIn(Dist.CLIENT)`）。

**C. 多配方类型 + 序列化器分层**
`crafting/recipe/` 下 `PotRecipe/StockpotRecipe/FlexPotRecipe/FlexStockpotRecipe/ChoppingBoardRecipe/MillstoneRecipe/SteamerRecipe/TeapotRecipe/BambooTrayRecipe/RiceBowlRecipe`，配 `BaseRecipe` 抽象父类；每种配方一个 `*RecipeSerializer`（`crafting/serializer/`），并抽公共积木：自定义 Ingredient `crafting/ingredinet/AnyIngredient`、产物 `crafting/output/RandomOutput`、容器 `crafting/container/StockpotContainer`。`Flex*` 变体表示“材料顺序无关”的宽松匹配。

**D. 大量 compat 适配层**
`compat/jei|rei|emi` 各含 `ModXxxPlugin` + `category` 子包，三套物品栏查看器统一抽象；“Ponder” 场景 `compat/ponder/scenes`（Create 的教学动画）；`compat/create`（`MillstoneCompat`）、`compat/tetra`、`compat/farmersdelight`、`compat/harvest`、`compat/carryon`、`compat/kubejs`。KubeJS 侧提供 `kubejs.plugins.txt`、`kubejs.classfilter.txt` 让整合包脚本可注册汤底等。

**E. 事件驱动的行为补丁层**
`event/` 下 10+ 小事件类：`RightClickEvent/LeftClickEvent/HoeUseEvent/SickleHarvestNetherWartEvent/ScarecrowFarmlandTrampleEvent/ModTradesEvent/EntityJoinWorldEvent/ChangeTargetEvent/ArmorEffectEvent/AddVillageStructuresEvent`，都订阅 Forge 事件总线，把方块/物品交互逻辑从 Block 类里搬出来（便于单点复用与调试）。

**F. 数据驱动的小型 datamap**
`datamap/MillstoneBindableData.java:13-26` 用 `RecordCodecBuilder` + `Codec.unboundedMap(ENTITY_TYPE_CODEC, ...)` 描述“哪些实体能被绑到磨盘上、转速/抬升角/偏移”，并提供 `DEFAULT`。属于 Forge datamap 的轻量替代方案。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/NetworkHandler.java:15` 用 `NetworkRegistry.newSimpleChannel(..., "1.0.0")` + `SimpleChannel`；**只有一个包** `SimpleC2SModMessage`（`network/message/`），用 `int index` 复用多用途（`record SimpleC2SModMessage(int index)`，`:19`），`handle` 里 `context.enqueueWork`，服务端侧再校验 `player.getMainHandItem().is(ModItems.BAOZI.get())` 防作弊（`:61-76`）
- 数据驱动：配方全部 JSON（`data/kaleidoscope_cookery`），汤底走代码注册表；`init/registry/DatapackReloadListenerEvent.java` 处理数据包重载；`kubejs.plugins.txt` 供 KubeJS 扫描
- 配置：`config/GeneralConfig.java`（COMMON，`ForgeConfigSpec`，`push("cookery")` 分组，含“饱腹代偿”一整套可调伤害减免参数）+ `config/ClientConfig.java`（CLIENT）
- datagen：`datagen/DataGenerators.java:17-42` 一个 `@Mod.EventBusSubscriber` 收 `GatherDataEvent`，`vanillaPack.addProvider(...)` 出标签（block/item/poi/entity_type/damage），`ForgeAdvancementProvider` 出进度，另有 `LootTableGenerator/ModRecipeGenerator/GlobalLootModifier/SoundDefinitionsGenerator/ParticleDescriptionGenerator/BlockModelGenerator/BlockStateGenerator/ItemModelGenerator`，输出到 `src/generated/resources`

## 6. Mixin

配置 `src/main/resources/kaleidoscope_cookery.mixins.json`（`required: true`、`compatibilityLevel: JAVA_17`、`defaultRequire: 1`、refmap `kaleidoscope_cookery.refmap.json`），共 7 个类、260 行，无 client mixin：

- `mixin/BlockMixin.java:20` → `Block.getDrops(...)` `@At("RETURN")` cancellable，转交 `InstantSmeltingEffect.onGetDrops(state, level, entity, cir)`
- `mixin/VillagerMixin.java:21` → `Villager.wantsToPickUp(Lnet/minecraft/world/item/ItemStack;)Z` HEAD cancellable；用 `@Unique` 惰性缓存 Set，注释明确指出“避免过早初始化导致 Item 全为 null”
- `mixin/MobBucketItemMixin.java` + `MobBucketItemAccessor.java`（插件式 Accessor，避免开 AT）
- `mixin/LivingEntityMixin.java`、`PowderSnowBlockMixin.java`、`FallingBlockEntityMixin.java`（92 行，最大）

## 7. 值得学的 5 条具体做法

1. **把状态常量与交互方法定义在 `api/` 接口，实现类只做实现**：`api/blockentity/IPot.java:11`，第三方可直接 `instanceof IPot` 驱动锅；适用：任何要留扩展点的机器/容器方块。
2. **用“只存 recipeId + 客户端按 id 反查 visuals”代替同步整个配方/渲染数据**：`blockentity/kitchen/StockpotBlockEntity.java:57-66,197-200`；适用：带复杂客户端表现的机器。
3. **配方匹配抛出可取消事件让整合包改结果**：`api/event/StockpotMatchRecipeEvent.java` + 调用点 `StockpotBlockEntity.java:287`；适用：想被 KubeJS/整合包接管的系统。
4. **单一 C2S 包 + `int index` 复用**，并在服务端复检手持物：`network/message/SimpleC2SModMessage.java:19-46`；适用：按键触发的零散交互。
5. **AT + mixin 混合，能用访问器/getter 的一律进 `accesstransformer.cfg`**：`src/main/resources/META-INF/accesstransformer.cfg` 与 `mixin/MobBucketItemAccessor.java`；适用：1.20.1/1.21 兼容性维护成本控制。

## 8. 公开 API（非库 mod，但有明确 API 包）

- `api/blockentity/`：`IPot/ISteamer/IStockpot/ITeapot/IMillstone/IChoppingBoard/IShawarmaSpit/IKitchenwareRacks`
- `api/recipe/soupbase/ISoupBase`（＋`SoupBaseManager.registerSoupBase/registerFluidSoupBase/registerMobSoupBase` 接入）、`api/item/IHasContainer`、`api/client/render/ISoupBaseRender`
- `api/event/`：`RecipeItemEvent/SickleHarvestEvent/MillstoneMatchRecipeEvent/StockpotMatchRecipeEvent`（可取消/改写）
- 外部接入方式：代码调用 `SoupBaseManager`、监听上述事件、JSON 配方（`data/kaleidoscope_cookery/recipes`）、KubeJS 插件与 classfilter（`kubejs.plugins.txt` / `kubejs.classfilter.txt`）
