# DragonsPlusMinecraft/CreateDragonsPlus 源码分析报告

## 1. 基本信息
- Mod 名 Create: Dragons Plus（CDP）；`mod_id=create_dragons_plus`；作者 DragonsPlus；版本 1.11.8b；自我定位 "Library mod for DragonsPlusMinecraft Create-addons" —— **库/前置 mod**（CEI、CreateIntegratedFarming 等均依赖它）。
- MC 1.21.1 + NeoForge 21.1.228（`[21.1.0,)`）；Java 21；Parchment `2024.11.17`。
- Gradle：`net.neoforged.moddev` 2.0.141 + `mod-publish-plugin` + spotless；`generateModMetadata` 生成 `neoforge.mods.toml`；带 accesstransformer。
- 许可证 LGPL-3.0-or-later（`LICENSE-CREATE.txt` 标注含来自 Create 的 MIT 代码）。
- 编译依赖：`api` 暴露 Registrate `MC1.21-1.3.0+67`、Ponder `1.0.82`、Create `6.0.10`(transitive false)、Flywheel `compileOnlyApi`；`jarJar` 内嵌 `me.fallenbreath:conditional-mixin-neoforge` 0.6.4（下游无条件复用）；compileOnly JEI/Curios。集成（独立 sourceSet）：sable/aeronautics、ars_nouveau、dye_depot、dyenamics、arts_and_crafts、create_garnished、create_dnd、aether、quicksand、immersive_engineering。

## 2. 源码规模与包结构
- 285 个 `.java`，共 20192 行（`src/main` 14959 行，其余为 8 个集成 sourceSet）。
- 包（`plus.dragons.createdragonsplus`）：`common/{registry(16),fluids/{dye,hatch,tank,pipe,dragonBreath},kinetics/fan/{coloring,sanding,freezing,ending},processing/blaze,advancements,recipe,behaviours,registrate/builder}`、`config(11)`、`data/{recipe,tag,lang,internal,runtime}`、`client/{ponder/scenes,model,color,texture}`、`mixin/{create,minecraft,neoforge,util}`、`integration/{jei,CDPCompatFix}`、`util(10)`。
- 最大文件：`common/kinetics/fan/coloring/ColoringFanProcessingType.java`(527)、`common/fluids/hatch/FluidHatchBlock.java`(416)、`common/CDPRegistrate.java`(385)、`common/registry/CDPFluids.java`(323)、`common/processing/blaze/BlazeBlockVisual.java`(286)、`common/fluids/tank/FluidTankBehaviour.java`(263)、`common/advancements/CDPAdvancement.java`(263)。

## 3. 入口与注册
三个 `@Mod` 类：`common/CDPCommon.java:62`、`client/CDPClient.java`、`data/CDPData.java`。库总线在 **FMLConstructModEvent（priority=LOWEST）** 阶段注册（不是构造器里），以保证染料变体先 bootstrap：
```java
@SubscribeEvent(priority = EventPriority.LOWEST)
public void construct(final FMLConstructModEvent event) {
    bootstrapDyeVariants();                      // DyeVariantRegistry.freeze(builder.build())
    CDPCauldrons.register(modBus); CDPFluids.register(modBus); CDPBlocks.register(modBus);
    ... CDPBlockEntities / CDPItems / CDPCreativeModeTabs / CDPCriterions / CDPRecipes /
    CDPConditions / CDPFanProcessingTypes / CDPItemAttributes / CDPDataMaps.register(modBus);
}
```
注册框架是 **Registrate 的派生类** `common/CDPRegistrate.java`（`AbstractRegistrate<CDPRegistrate>`）：覆写 `accept()` 自动挂 tooltip/创造模式标签页登记，另提供 `asResource`、`registerTags`、`registerBuiltinLocalization`、`registerForeignLocalization`、`registerPonderLocalization`、`setCreativeModeTab`、`armInteractionPoint`/`customStat`（`common/registrate/builder/`）等封装；类上有 `@CodeReference(value = CreateRegistrate.class, source = "create", license = "mit")`。

## 4. 核心系统
1. **染料流体变体系统** `common/fluids/dye`：`DyeVariant`（id+颜色+纹理+名称）、`DyeVariantRegistry`（`AtomicBoolean FROZEN` + `freeze(Collection)` 后 `all()/get()/creativeModeTabIndex()` 全不可变）、事件 `RegisterDyeVariantsEvent`。`CDPCommon.bootstrapDyeVariants()` 在 CONSTRUCT 期收集 `DyeColors.registerVanilla` 与所有 mod 的贡献后冻结；`CDPFanProcessingTypes` 随即为每个变体生成一个 `ColoringFanProcessingType` 并注册进 `CreateRegistries.FAN_PROCESSING_TYPE`（`COLORING: Map<ResourceLocation, Supplier<...>>`）。
2. **风扇处理类型四件套** `common/kinetics/fan/{coloring,sanding,freezing,ending}`：每种 = FanProcessingType + 对应 `StandardProcessingRecipe` 子类（`ColoringRecipe/SandingRecipe/FreezingRecipe/EndingRecipe`）+ `DynamicParticleFanProcessingType` 粒子；`SandingCatalysts` 管催化剂物品/tag。
3. **共用烈焰机械** `common/processing/blaze`：`BlazeBlock`/`BlazeBlockEntity`/`BlazeBlockVisual`/`BlazeMovementBehaviour` —— 供 CEI 的 BlazeEnchanter/BlazeForger 等附属直接继承的基础装置。
4. **流体容器组件**：`common/fluids/tank/FluidTankBehaviour`（Create `SmartFluidTank` 的多罐 BlockEntityBehaviour，`TankFactory`/`TankSegment`/`getPrimaryHandler()`/`sendDataLazily()`）+ `ConfigurableFluidTank`；`common/fluids/hatch/{FluidHatchBlock,FluidHatchItemFilling,FluidHatchItemFluidTransfer,FluidHatchFillingRecipeTransfer}`（物品→流体互转的"流体仓"）。
5. **特性开关 = 数据包条件** `config/{FeaturesConfig,CDPFeaturesConfig}.java`：`ConfigFeature extends ConfigBool implements ICondition`，附 `MapCodec<ConfigFeature>`（用 ResourceLocation 查已注册特性），可作为配方/数据的 condition；`getFeatureOverride()` 遍历 `ModList.get().getMods()` 读**其他 mod 的 mods.toml `[modproperties]`** 来覆盖开关（CEI 里写 `create_dragons_plus:fluid/dye=true` 即为此机制）。
6. **运行时数据包** `data/runtime/RuntimePackResources.java`：一个类同时实现 `PackResources, RepositorySource, ResourcesSupplier, CachedOutput`，在 `AddPackFindersEvent` 中往 `PackType.SERVER_DATA` 加 `Position.TOP` 的自生成包，配 `data/internal/CDPRuntimeRecipeProvider` 在运行时产出配方。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：主源集未见自建 payload 注册（同步依赖 Create SmartBlockEntity/SmartFluidTank 体系）→ 未确认。
- 数据驱动：`DeferredRegister<FanProcessingType>` 进 Create 的 `CreateRegistries.FAN_PROCESSING_TYPE`；配方全部走 Create `StandardProcessingRecipe` 子类 + `data/internal/CDPRegistrateDataMaps` 生成 DataMap；`data/recipe/integration/{IntegrationIngredient,IntegrationResult,IntegrationResultRecipe}` 做"按 mod 加载状态切换配方";`data/tag/` 有 `TagRegistry`/`IntrinsicTagRegistry`（intrinsic tag 用 `Supplier<T>` 直接写值，不需要 label）、`ItemTagRegistry`。
- 配置：`config/CDPConfig` + `CDPCommonConfig/CDPServerConfig/CDPClientConfig/CDPFeaturesConfig/CDPDyeFluidConfig/CDPDragonBreathConfig`，全部基于 Create 的 `ConfigBase`（非 NeoForge ModConfigSpec）。
- datagen：`data/CDPData.java`(`@Mod`) + `data/{internal,tag,recipe,lang}`；`ForeignLanguageProvider` 处理外部语言文件；`CDPRegistrate` 内建本地化/ponder 本地化注册。

## 6. Mixin
- `src/main/resources/create_dragons_plus.mixins.json`：`plugin=CDPMixinConfigPlugin`（`extends me.fallenbreath.conditionalmixin.api.mixin.RestrictiveMixinConfigPlugin`），`compatibilityLevel=JAVA_21`。
- 16 个主 mixin：`create.AirCurrentMixin`(+`$AirCurrentSegmentMixin`)、`AirFlowParticleMixin`(client)、`BlockEntityBehaviourMixin`、`ContraptionMixin`、`FluidFillingBehaviourMixin`、`MechanicalMixerBlockEntityMixin`、`OpenEndedPipeMixin`、`OpenEndFluidHandlerMixin`、`PotionMixingRecipesMixin`、`VanillaFluidTargetsMixin`、`minecraft.BottleItemMixin`、`ConcretePowderBlockMixin`、`IngredientValueMixin`、`RecipeManagerAccessor`、`ReloadableServerResourcesMixin`、`neoforge.ExistingFileHelperAccessor`。
- `mixin/util/RunDataMixinCondition.java`：通过 ModLauncher `IEnvironment.Keys.LAUNCHTARGET` 判断当前是否 datagen（`CommonLaunchHandler.isData()`），让某些 mixin 只在 datagen 生效。
- 集成各有独立 config：`create_dragons_plus.{sable,aether,create_dnd,create_garnished}.mixins.json`。

## 7. 值得学的 5 条
1. 变体"收集→冻结→派生注册"：`DyeVariantRegistry.freeze` + `RegisterDyeVariantsEvent`，一次声明染料变体，自动派生流体、风扇类型、创造模式标签页顺序（`common/fluids/dye/DyeVariantRegistry.java:20`、`common/CDPCommon.java:110`）。
2. 跨 mod 零代码开关：读其他 mod 的 `modproperties` 决定本库特性是否启用（`config/FeaturesConfig.java:54`）——比事件/接口更轻的软依赖协商方式。
3. `ConfigFeature implements ICondition` + `MapCodec`：把配置开关直接当数据包/配方条件用（`config/FeaturesConfig.java:57`）。
4. `RuntimePackResources` 把"运行时生成的资源"做成标准 Mod 内建资源包，插到 `Position.TOP`（`data/runtime/RuntimePackResources.java`、`common/CDPCommon.java:126`）。
5. `@CodeReference(value=..., source=..., license=...)` 注解 + `LICENSE-CREATE.txt`：把抄自 Create 的代码逐类标注来源与许可证（`common/CDPRegistrate.java:86`）——多来源代码的合规工程做法；同理 `mixin/util/FieldsNullabilityUnknownByDefault` 等注解用于抑制/标注 null 分析。构建层另有集成 sourceSet + `integrationSourceSetDependencies` 依赖图 + `${integration_mixin_blocks}` 注入 mods.toml 的范式（`build.gradle`）。

## 8. 公开 API / 外部接入方式（库 mod）
- 无独立 `api` 包，API 即 jar 顶层：注册器 `common/CDPRegistrate.java`；事件/收集器 `common/fluids/dye/RegisterDyeVariantsEvent` + `integration/CDPIntegrationContributions`（`registerDyeVariants/registerDataMaps/registerColoringCompat/registerSandingCompat/registerCatalyst...`，全部 `CopyOnWriteArrayList` 收集后统一 gather）。
- 可继承装置：`common/processing/blaze/BlazeBlock(+BlockEntity/Visual/MovementBehaviour)`、`common/fluids/tank/FluidTankBehaviour`/`ConfigurableFluidTank`、`common/behaviours/{BehaviourProvider,SmartBlockEntityBehaviourProvider}`。
- 数据/配方工具：`common/recipe/{BaseRecipeBuilder,RecipeConverter,RecipeTypeInfo,UpdateRecipesEvent}`、`data/recipe/*RecipeBuilder`、`data/tag/{TagRegistry,IntrinsicTagRegistry,ItemTagRegistry}`、`util/{Pairs,ItemStackKey,PersistentDataHelper,CDPCodecs,CodeReference}`。
- Mixin 接入：附属在自己的 mixin config 里指定 `"plugin": "plus.dragons.createdragonsplus.mixin.CDPMMixinConfigPlugin"`（CEI 就是这么做的），并借 `jarJar` 内嵌的 conditional-mixin 做条件开关。
