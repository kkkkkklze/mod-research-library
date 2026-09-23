# DragonsPlusMinecraft/CreateEnchantmentIndustry 源码分析报告

> 注意：本地 bulk 导出不完整，工作区只有 `src/integration/apotheosis`；本报告其余内容通过 `git show HEAD:<path>` 读取 git 对象完成（HEAD=`9a523a3`）。

## 1. 基本信息
- Mod 名 Create: Enchantment Industry（CEI）；`mod_id=create_enchantment_industry`；作者 DragonsPlus；版本 2.5.3b。
- MC 1.21.1 + NeoForge 21.1.248（`neo_version_range=[21.1.228,)`），Java 21，Parchment `2024.11.13`。
- Gradle：`net.neoforged.moddev` 2.0.141 + `mod-publish-plugin` + spotless；`generateModMetadata` 用模板生成 `neoforge.mods.toml`（`src/main/templates/META-INF/neoforge.mods.toml`）。
- 许可证 LGPL-3.0-or-later。
- 编译依赖：Create `[6.0.10,)`、**CreateDragonsPlus 1.11.3+（其 API 库）**、`jarJar` 内嵌 `me.fallenbreath:conditional-mixin-neoforge` 0.6.4；compileOnly JEI 19.21 / Curios 9.2.2；可选集成 Apotheosis 8.7.0、ApothicEnchanting 1.6.1、ApothicSpawners、Sable、TouhouLittleMaid。

## 2. 源码规模与包结构
- git HEAD 共 351 个 `.java`；`src/main` 179 个，`src/integration` 172 个。总行数实测 24806（超长路径文件因 Windows 限制未计入，实际略高）。
- 主包 `plus.dragons.createenchantmentindustry`：`common/{registry(16),processing/{enchanter,classic_enchanter,forger},fluids/{experience,printer,lantern},kinetics/{grindstone,crusher,deployer}}`、`client/ponder/scene`、`config(10)`、`data(5)`、`mixin(12)`、`api/registry`、`util`、`integration/{apotheosis,apothic_enchanting,sable,sable_apotheosis,touhou_little_maid,jei}`。
- 最大文件：`common/processing/forger/BlazeForgerInventory.java`(747)、`BlazeForgerBlockEntity`(543)、`client/ponder/scene/ExperienceScene`(524)、`common/kinetics/grindstone/GrindstoneDrainBlockEntity`(464)、`common/processing/enchanter/BlazeEnchanterBlockEntity`(366)、`common/registry/CEIAdvancements`(332)。

## 3. 入口与注册
`common/CEICommon.java:39` 是 `@Mod`；注册器来自 CDP：
```java
public static final CDPRegistrate REGISTRATE = new CDPRegistrate(ID)
    .setTooltipModifier(item -> new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)...);
public CEICommon(IEventBus modBus, ModContainer modContainer) {
    REGISTRATE.registerEventListeners(modBus);
    CEIFluids.register(modBus); ... CEIBlocks/CEIBlockEntities/CEIItems/CEICreativeModeTabs/CEIRecipes/
    CEIEnchantments/CEIArmInterationPoints/CEIDataMaps/CEIStats/CEIMountedStorageTypes/CEIItemAttributes/
    CEIPrintingBehaviours.register(modBus);
```
注册全部委托给 `common/registry/CEI*` 静态类，多数自带 `register(IEventBus)` 供主类调用（如 `CEIFluids.java:68`）。另有两个 `@Mod` 入口：`client/CEIClient` 与 `data/CEIData`（后者仅在 `DatagenModLoader.isRunningDataGen()` 时挂监听）。

## 4. 核心系统
1. **烈焰三件套机械**：`common/processing/{enchanter,classic_enchanter,forger}`。`BlazeEnchanterBlockEntity`/`BlazeForgerBlockEntity` 继承 Create 的 SmartBlockEntity 风格，`EnchanterBehaviour`/`TemplateEnchantingBehaviour`/`BlazeForgerModeBehaviour` 做"模式 → 行为"分派；机械臂交互点 `CEIArmInterationPoints`。
2. **经验流体**：`fluids/experience`。`ExperienceFluidType` 定义物性（不推动实体、不能游泳），`ExperienceEffectHandler` 实现 Create `OpenPipeEffectHandler`（开放管道滴灌注经验），`ExperienceHatchBlockEntity`、`ExperienceLightningCharger`（避雷针）、`ExperienceLanternMountedStorage`（灯笼作为移动流体容器）。
3. **打印机 + 数据驱动行为注册表**：`fluids/printer`。核心是自定义注册表 `api/registry/CEIRegistries.PRINTING_BEHAVIOUR_PROVIDER`，见 `fluids/printer/behaviour/PrintingBehaviourRegistry.java`：`DeferredRegister.create(CEIRegistries.PRINTING_BEHAVIOUR_PROVIDER, ID)` + `builder.sync(false).onBake(this::bake)`，`PrintingBehaviourProvider(int priority, Provider)` 用 `DEFAULT_PRIORITY=0 / BUILTIN_PRIORITY=1000` 排序；内置行为覆盖附魔书、成书、命名、旗帜图案、包裹地址、打包配方等 9 个类。
4. **数据包规则**：`common/processing/EnchantmentProcessingRule.java` 用 record + `RecordCodecBuilder` 表达 `level_extension`（blaze_enchanter/blaze_forger 等级上限）与 `cost_multiplier`；通过 `CEIDataMaps`（NeoForge `DataMapType`，`EXPERIENCE_FUEL` 声明 `.synced(FULL_CODEC, true)`）下发；`EnchantmentProcessingRules.warnLegacyDataMaps()` 检测旧 map 并给出迁移警告。
5. **磨石/动力砂轮**：`kinetics/grindstone/{MechanicalGrindstoneBlock,GrindingRecipe,GrindstoneDrainBlockEntity}`；`util/CEICodecs`、`util/CEIStreamCodecs` 提供自定义序列化工具。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：主源集未见自建网络注册类（同步走 Create SmartBlockEntity/Registrate）；集成内有 `integration/apothic_enchanting/.../ContraptionEnderWovenBagPocketChangePacket` 等自定义包（未确认是否存在统一注册器）。
- 数据驱动：自定义 Registry（printing_behaviour）、NeoForge DataMap、Codec 化加工规则、`data/CEIRecipeProvider`。
- 配置：`config/CEIConfig.java` 用 `ModConfigSpec.Builder` 注册 COMMON/CLIENT/SERVER 三份，委托 `CEICommonConfig/CEIClientConfig/CEIServerConfig`，对外用静态访问器 `CEIConfig.server()/kinetics()/stress()/fluids()` 暴露嵌套分组。
- datagen：`data/CEIData.java` 监听 `GatherDataEvent`，注册 `CEIGenerateEntriesProvider`（自带 `getRegistryProvider()` 供后续 provider 复用 lookups）+ `CEIRecipeProvider` + `CEIAdvancements`；Registrate 侧再挂 `registerBuiltinLocalization/registerForeignLocalization/registerPonderLocalization`；产物流向 `src/generated/resources`。
- 集成隔离：Gradle 为每个集成建独立 sourceSet（`src/integration/<name>/{java,resources}`，`enable_xxx_integration` 开关），构建时把对应 mixin 配置拼进 mods.toml 的 `${integration_mixin_blocks}`。

## 6. Mixin
- 配置 `src/main/resources/create_enchantment_industry.mixins.json`：`priority=1100`、`plugin=plus.dragons.createdragonsplus.mixin.CDPMixinConfigPlugin`（由 CDP 提供的 conditional-mixin 插件，可按条件启用）。
- 代表类：`mixin/DeployerHandlerMixin.java`（`@Redirect` 到 `BlockState.spawnAfterBreak`，让机械臂挖掘也触发 `CommonHooks.handleBlockDrops`，用 `@Local(argsOnly=true)` 取 `ServerPlayer`）、`mixin/EnchantmentHelperMixin.java`（`@ModifyExpressionValue` 拦 `getComponentType` 让附魔模板被当作附魔书）、`mixin/PlayerMixin.java`（`@ModifyArg` 拦 `CommonHooks.fireSweepAttack`，机械臂可横扫）；其余：`ConnectivityHandlerMixin`、`SmartBlockEntityMixin`、`LightningBoltMixin`、`FishingHookMixin`、`CrushingWheelControllerBlockEntityMixin`、`CreateNBTProcessorsMixin`、`FillingBySpoutMixin`、`DeployerFakePlayerMixin`、`accessor.CreateRecipeCategoryAccessor`。
- 集成 mixin 单独 config：`src/integration/apotheosis/resources/create_enchantment_industry.apotheosis.mixins.json`（AffixHelperMixin、create.BeltInventoryMixin、create.DepotBehaviourMixin）。

## 7. 值得学的 5 条
1. 入口三分：`CEICommon`/`CEIClient`/`CEIData` 各为一个 `@Mod` 类，datagen 类先判 `DatagenModLoader.isRunningDataGen()` 再注册监听 —— 运行时零开销（`data/CEIData.java:32`）。
2. 数据包 + 迁移警告：新规则走 Codec/DataMap，同时 `warnLegacyDataMaps` 扫描旧 DataMap 并提示 —— 存量整合包不炸（`common/processing/EnchantmentProcessingRules.java:24`）。
3. 第三方可插拔：`PrintingBehaviourProvider(priority, provider)` + Registry `onBake` 排序缓存，附属 mod 只要注册高/低优先级 provider 就能覆盖默认做书行为（`api/registry/CEIRegistries.java`）。
4. MixinExtras 的组合用法：`@Local(argsOnly=true)` 补参数、`@ModifyArg` 伪造布尔让假玩家享受真实玩家逻辑 —— 修第三方 mod 回调缺参的标准手法（`mixin/DeployerHandlerMixin.java`）。
5. 集成/构建工程化：`enable_xxx_integration` 独立 sourceSet、mixin config 由模板变量注入 mods.toml、`jarJar` 内嵌 conditional-mixin；配套的零耦合开关是 mods.toml 的 `[modproperties.create_enchantment_industry] "create_dragons_plus:fluid/dye"=true`，由 CDP 读取决定是否注册染料流体（`build.gradle:33-95,244-287`、`src/main/templates/META-INF/neoforge.mods.toml`）。

## 8. 对外 API（非纯库 mod，但提供扩展点）
- `plus.dragons.createenchantmentindustry.api.registry.CEIRegistries`：`PRINTING_BEHAVIOUR_PROVIDER` 注册表键；配合 `common/fluids/printer/behaviour/PrintingBehaviour.Provider`、`PrintingBehaviourProvider` 接入自定打印行为。
- 数据包侧扩展：`EnchantmentProcessingRule`（附魔等级扩展/费用倍率）、`CEIDataMaps.EXPERIENCE_FUEL`（item → 经验燃料）。
- 依赖 CDP 库暴露的 `CDPRegistrate`、`CDPMixinConfigPlugin` 等公共设施（见 CDP 报告）。
