# Monad-Modding/BrewinAndChewin（饮酒作乐）源码分析

## 1. 基本信息

- Mod 名：Brewin' And Chewin'（饮酒作乐）；mod_id `brewinandchewin`；作者 Probleyes、Umpaz、MerchantCalico（`buildSrc/src/main/kotlin/umpaz/brewinandchewin/gradle/Properties.kt`）；版本 5.0.0
- 目标：**多加载器**，MC 1.21.1 / Fabric Loader 0.19.2 + Fabric API 0.116.2 / NeoForge 21.1.219，Java 21（`buildSrc/.../Versions.kt` 单一版本清单）
- Gradle：`settings.gradle.kts` 只有 `include("common")`、`include("fabric")`、`include("neoforge")`；根 `build.gradle.kts` 声明 `fabric-loom 1.16-SNAPSHOT`、`net.neoforged.moddev 2.0.141`、`mod-publish-plugin 2.0.0`；自写 `buildSrc` 约定插件 `conventions.common.gradle.kts` / `conventions.loader.gradle.kts`
- 许可证：MIT
- 编译依赖（`common/build.gradle.kts`，全部 `compileOnly`）：**Farmer's Delight**（父 mod，必装）、`greenhouseconfig` + `greenhouseconfig_toml`（Greenhouse 的配置库，必装，neoforge.mods.toml 里 mandatory=true）、`mixinextras-common`、`jei-common-api`、`emi-xplat-mojmap:api`、`appleskin`、`create-1.21.1` + `Registrate`（Create 联动仅在 neoforge 侧）；可选 `nomansland`(AFTER)

## 2. 源码规模与包结构

- `common` 192 个 java / `fabric` 40 / `neoforge` 60，合计 **292 个 `.java`、25557 行**（`find . -name '*.java' -exec cat {} + | wc -l`）；仓库受版本控制文件 1804 个（1028 json + 449 png + 292 java），本地为 sparse checkout
- 主要包：`umpaz.brewinandchewin.common.block`(20)、`common.mixin`(18)、`common.registry`(16)、`common.utility`(12)、`common.item`(10)、`common.mixin.client`(9)、`common.block.entity`(9)、`client.utility`(8)、`integration.jei`(6)、`common.network.clientbound`(5)、`client.renderer.texture`(5)、`client.gui`(5)、`integration.emi.*`、`common.compat.nomansland`、`common.utility.dfu`
- 最大文件：`common/block/entity/KegBlockEntity.java`(815)、`integration/jei/transfer/FermentingTransfer.java`(578)、`FermentingTransferServer.java`(526)、`common/block/RopeGrapeBlock.java`(490)、`integration/emi/handler/BnCEMIRecipeFiller.java`(457)、`KegEmiRecipeHandler.java`(402)、`fabric/platform/BnCPlatformHelperFabric.java`(339)、`neoforge/platform/BnCPlatformHelperNeoForge.java`(331)、`AgingCaskBlockEntity.java`(310)、`TrellisGrapeBlock.java`(297)

## 3. 入口与注册

- common 侧的"主类"是 `common/src/main/java/umpaz/brewinandchewin/BrewinAndChewin.java:10`，只持有 `BnCPlatformHelper` 单例：

```java
public static void init(BnCPlatformHelper helper) {
    BrewinAndChewin.helper = helper;
    BnCConfiguration.init();
}
```

- Fabric 入口 `fabric/.../BrewinAndChewinFabric.java:50`（`ModInitializer`）：`BrewinAndChewin.init(new BnCPlatformHelperFabric())` → `registerContents()`（逐个 `BnC*.registerAll()`）→ `registerNetwork()` → `registerCompostables()` → `registerWorldGeneration()`（`BiomeModifications.addFeature`）→ `registerFluidAttributeHandlers()`
- NeoForge 入口 `neoforge/.../BrewinAndChewinNeoForge.java`，`@Mod` 构造注入 `IEventBus`，用内部类 `RegistryEvents` + `@EventBusSubscriber(bus = MOD)`，在 `RegisterEvent` 里按注册表分派 `register(event, Registries.BLOCK, BnCBlocks::registerAll)` 等
- **注册框架**：不用 DeferredRegister/Registrate，而是 common 里写静态字段 + `registerAll()`（`common/registry/BnCItems.java:24` 里 `Registry.register(BuiltInRegistries.ITEM, BrewinAndChewin.asResource(name), item)`），把"注册时机"交给各加载器的入口调用 —— 这是本仓库最值得抄的多加载器骨架
- 客户端：`client/BrewinAndChewinClient.java` + Fabric `BrewinAndChewinFabricClient`

## 4. 核心系统

**A. 多加载器平台抽象**（`common/src/main/java/umpaz/brewinandchewin/platform/BnCPlatformHelper.java`）。接口定义全部差异点：`getPlatform()`、`isModLoaded`、网络发送（`sendClientbound`/`sendClientboundTracking`/`sendServerbound`）、`getFluidDisplayName(AbstractedFluidStack)`、`openKegMenu`、`supplyBlockEntity()` 等；两个实现分别 339/331 行。配套的"中间抽象类型"：`AbstractedFluidStack`、`AbstractedFluidTank`、`AbstractedItemHandler`、`AbstractedFluidIngredient`、`KegRecipeWrapper`，把 Fabric Transfer API 与 NeoForge Capability 收敛到同一套接口（`fabric/container/KegFluidTankFabric` vs `neoforge/container/KegFluidTankNeoForge`）。

**B. 酒桶发酵**（`common/block/entity/KegBlockEntity.java:65`）。`FLUID_CAPACITY = 4000L`、`INPUT_SLOTS=4`、`CONTAINER_SLOT=4`、`OUTPUT_SLOT=5`；核心状态 `fermentTime/fermentTimeTotal/fermentFluid/fermentBatches`，配 `ContainerData kegData` 走菜单同步、`writeUpdateTag` 只推变更数据（见 `:179`）；配方匹配缓存 `lastRecipeID` + `checkNewRecipe`，`usedRecipeTracker`(Object2IntOpenHashMap) 记录已用配方；`snapshotFermenting/clearFermenting/fermentingWasDisturbed` 保证发酵中途被扰动即回滚；`ejectIngredientRemainder`、`splitAndSpawnExperience` 处理副产物与经验。

**C. 陈酿桶**（`common/block/entity/AgingCaskBlockEntity.java:37`）。`WINE_SLOT=0`、`FIRST_DISTILLATE_SLOT=1`、`DISTILLATE_SLOTS=8`、`OUTPUT_SLOT=9`、`AGING_TIME_TOTAL=6000`、`DATA_COUNT=2`，用 `lastInputs` 数组记住上一 tick 输入以判定"是否换了酒"。

**D. 数据驱动的配方与抽象流体单位**（`common/crafting/`）。`KegFermentingRecipe`（`INPUT_SLOTS=4`、`FERMENTING_TIME_PER_BUCKET=18000`、`BUCKET=1000L`）字段 `Optional<FluidIngredientWithAmount> fluidIngredient` + `Optional<FluidUnit> unit` + `Either<AbstractedFluidStack, ItemStack> result`（结果是流体或物品二选一，`unit` 存在时把结果归一化到统一单位）；另有 `KegPouringRecipe`、`CreatePotionPouringRecipe`（Create 联动）、`FluidIngredientWithAmount`。

**E. 附件（Attachment）与效果状态同步**（`common/attachment/`、`common/network/`）。`RagingAttachment`/`TipsyHeartsAttachment` 各自带 `Codec` 与 `ID`（`BrewinAndChewin.asResource("raging")`），效果类 `effect/{Intoxication,Raging,SweetHeart,Tipsy}Effect.java`；同步时机在 Fabric 入口 `BrewinAndChewinFabric.java:68-91`：`EntityTrackingEvents.START_TRACKING`（新玩家开始追踪实体时补发）+ `ServerEntityEvents.ENTITY_LOAD` —— 状态型数据的标准补同步写法。

**F. 自定义 DataFixer**（`common/utility/dfu/BnCDataFixer.java`）。自建 `DataFixerBuilder`，`CURRENT_VERSION = 100`（注释：「每个 MC 版本 +100」），配 `schema/BnCSchemaV1` + `DataFixTypesAccessor`/`NbtUtilsMixin`，用于老存档 NBT/物品迁移。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：common 定义 9 个 `CustomPacketPayload`（clientbound 5：`SyncRagingStacks`、`SyncNumbedHearts`、`SendRecipeBookValues`、`MakeNextPlayerChatTipsy`、`ClearKegFluidContainerComponents`；serverbound 4：JEI/EMI 灌装配方的 `JEITransferKegRecipe`、`EMIFillFermentingRecipe`、`EMIFillPouringRecipe`、`SetLabelContents`），每个自带 `StreamCodec`/`TYPE`；Fabric 侧 `PayloadTypeRegistry.playS2C/playC2S().register(...)` + `ServerPlayNetworking.registerGlobalReceiver(TYPE, (p,ctx)->p.handle(ctx.player()))`（`BrewinAndChewinFabric.java:120-136`），NeoForge 侧走 `RegisterPayloadHandlersEvent`
- **数据驱动**：1028 个 json（`common/src/generated/resources/`：recipes/advancement/tags/loot），配方走 `KegFermentingRecipe` 自定义 RecipeType/Serializer；世界生成有 `BnCFeatures` + `BnCBiomeFeatures`（Fabric 用 `BiomeModifications`，NeoForge 用 `BIOME_MODIFIERS` datagen）
- **配置**：第三方库 **GreenhouseConfig**（`common/BnCConfiguration.java:22`）`GreenhouseConfigHolder.common("brewinandchewin-common", Common.CODEC, Common.DEFAULT, TomlLang.INSTANCE).networkSynchronized(...)` —— record + Codec + StreamCodec + TOML，common 侧全同步，client 侧独立
- **datagen**：只放在 neoforge 模块（`neoforge/src/main/java/umpaz/brewinandchewin/data/`）：`BnCDataGenerators.java` 汇总 `BnCBlocks*Tags`、`BnCBuiltInEntries`（RegistrySetBuilder：DAMAGE_TYPE/CONFIGURED_FEATURE/PLACED_FEATURE/BIOME_MODIFIERS）、`BnCRecipes`、`data/recipe/*`（含 `BnCCookingPotRecipes`、`KegFermentingRecipes`）、`data/loot/BnCBlockLoot`、`data/world/BnCWildCropGeneration`

## 6. Mixin

三份配置：`common/src/main/resources/brewinandchewin.mixins.json`（19 个 common + 10 个 client，含 `DataFixTypesMixin`、`IntoxicationCancelSaturationMixin`、`KegStackedContentsRecipePickerMixin`、`StoreLootParamsMixin$LootParamsBuilderMixin`、`client.TipsyDrunkRendererMixin`）、`fabric/.../brewinandchewin.fabric.mixins.json`（8+7）、`neoforge/.../brewinandchewin.neoforge.mixins.json`（2+2）。common 配置挂了 `plugin: umpaz.brewinandchewin.BnCMixinConfigPlugin`（`fabric/.../BnCMixinConfigPlugin.java:24`）：

```java
public boolean shouldApplyMixin(String targetClassName, String mixinClassName) {
    if (mixinClassName.contains(".integration."))
        return FabricLoader.getInstance().isModLoaded(mixinClassName.split(".integration.", 2)[1].split("\\.", 2)[0]);
    return true;
}
```

即"mixin 类放在 `.integration.<modid>.` 包下就按该 mod 是否加载自动启用/跳过"，一份 jar 兼容有无前置。注入点以 `@ModifyVariable`/`@ModifyExpressionValue`/`@ModifyArg`（MixinExtras 风格）为主，如 `TipsyDrunkRendererMixin` 改 `renderLevel` 的矩阵与 `prepareCullFrustum` 参数（醉酒视角摇晃）。另配有 `common/src/main/resources/brewinandchewin.cfg`（NeoForge AT）与 `fabric/src/main/resources/brewinandchewin.classtweaker`（`classTweaker v2 named`）。

## 7. 值得学的 5 条具体做法

1. **common/fabric/neoforge 三模块 + `conventions.loader` 用 `commonJava`/`commonResources` configuration 把 common 源码直接编译进加载器 jar**（`buildSrc/src/main/kotlin/conventions.loader.gradle.kts`）—— 多加载器共享一份源码而不发中间产物，是当前最省心的组织方式。
2. **用 `record + Codec + StreamCodec` 同时定义配置与网络包**（`BnCConfiguration.java`、`common/network/*`）—— 一处结构定义同时给 toml 序列化、客户端显示、网络同步用。
3. **`MixinConfigPlugin.shouldApplyMixin` 按包名判断前置 mod**（`fabric/.../BnCMixinConfigPlugin.java:24`）—— 一份 jar 支援可选联动，避免为每个联动出单独构建。
4. **状态型附件的三重补同步**（`BrewinAndChewinFabric.java:61-91`）：登录/加载/开始被追踪各发一次 —— 写"玩家身上有自定义数值"的系统时照抄。
5. **自建 DataFixer 并给自家 schema 预留版本段**（`common/utility/dfu/BnCDataFixer.java`，`CURRENT_VERSION = 100`、按版本 +100）—— 长期更新、经常改 NBT 结构的 mod 的存档兼容保险。

## 8. 库/API 类 mod 扩展点

非库 mod，但对外提供了可复用契约：`platform/BnCPlatformHelper`（加载器适配接口，可仿写）、`common/utility/Abstracted*`（流体/物品/配方的跨加载器抽象）、`integration/jei`+`integration/emi`（`JEIPlugin` / `EMIPlugin` 作为 entrypoint 注册在 fabric.mod.json 的 `jei_mod_plugin` / `emi` 字段）、以及 Maven 发布（Greenhouse Maven，坐标 `umpaz.brewinandchewin:BrewinAndChewin-common/-fabric/-neoforge`，见 README）。
