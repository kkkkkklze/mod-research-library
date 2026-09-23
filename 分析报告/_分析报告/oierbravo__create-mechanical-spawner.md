# Create: Mechanical Spawner 源码分析报告

## 1. 基本信息

- Mod 名：Create: Mechanical spawner；mod_id：`create_mechanical_spawner`；作者：oierbravo；版本 `1.3.2-6.0.10`
- 目标：Minecraft `1.21.1` / **NeoForge** `21.1.219`（`gradle.properties:16-22`）；许可证 LGPL3
- Gradle 插件：`net.neoforged.moddev 2.0.74`、`dev.ithundxr.silk 0.11.15`、`me.modmuss50.mod-publish-plugin 0.8.3`（`build.gradle:1-6`），另用 `gradle/property_loader.gradle` 载入属性，Parchment `2024.11.17`
- 编译依赖（谁是它的 API）：**Create 6.0.10-280**（`slim`、`transitive=false`）、Ponder `1.0.82`、Flywheel `1.0.6`（compileOnly API）、Registrate `MC1.21-1.3.0+67`、`mixinextras-common`；**关键：`com.oierbravo.mechanicals:Mechanicals:1.21.1-1.1.5` 是作者自研的前置库**，本 mod 的配方基类/行为类/语言生成器全部来自它；软兼容 JEI 19.25、Jade、KubeJS 2101、Curios（compileOnly api）、Enchantment Industry（开关式）

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **43 个文件，3230 行**（含 datagen）。主要包：

- `content/components`（10）+ `content/components/collector`（4）+ `content/components/recipe`（5）— 机器本体与配方
- `compat/jei`（4，含 `animations`）、`compat/jade`（1）、`compat/kubejs`（3）— 三方兼容
- `registrate`（6）— CreateRegistrate 注册
- `infrastructure/config`（4）、`infrastructure/data`（5）— 配置与 datagen
- `foundation/utility`（1）、`ponders`（2）

最大文件：`content/components/SpawnerBlockEntity.java`(336)、`infrastructure/data/SpawnerRecipeGen.java`(212)、`CreateMixingRecipeGen.java`(204)、`SpawnerPointDisplay.java`(188)、`registrate/ModBlocks.java`(176)、`recipe/SpawnerRecipe.java`(153)。

## 3. 入口与注册

主类 `CreateMechanicalSpawner.java:32`，构造器 `:47-70`：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MODID)
        .defaultCreativeTab(ModCreativeTabs.MAIN_TAB.getKey());
public CreateMechanicalSpawner(IEventBus modEventBus, ModContainer modContainer){
    REGISTRATE.registerEventListeners(modEventBus);
    ModCreativeTabs.register(modEventBus);
    ModBlocks.register(); ModBlockEntities.register(); ModFluids.register();
    MConfigs.register(modLoadingContext, modContainer);
    ModRecipes.register(modEventBus);
    modEventBus.addListener(this::doClientStuff);
    modEventBus.addListener(this::registerCapabilities);
    modEventBus.addListener(ModDataGen::gatherData);
    generateLangEntries();
}
```

- **Registrate**：方块/流体/方块实体/创造栏走 `CreateRegistrate`（`registrate/ModBlocks.java:55` 起，链式 `.initialProperties(SharedProperties::stone)` `.transform(pickaxeOnly())` `.transform(ModStress.setImpact(16.0))` `.simpleItem()`），方块实体用 `BlockEntityEntry` + `.visual(() -> QuarterShaftVisual::bottom)`（`registrate/ModBlockEntities.java`）。
- **DeferredRegister**：仅配方类型/序列化器用它（`registrate/ModRecipes.java:22-30`）。
- **能力注册**走 NeoForge `RegisterCapabilitiesEvent`（`SpawnerBlockEntity.java:178-183` 注册 `Capabilities.FluidHandler.BLOCK`）。

## 4. 核心系统

**4.1 动力刷怪机（KineticBlockEntity + 行为树）** `content/components/SpawnerBlockEntity.java`
- 继承 `KineticBlockEntity`，`addBehaviours`（`:82-99`）挂 4 个行为：`SmartFluidTankBehaviour.single`、`ScrollValueBehaviour.between(1, maxRange)`（生成高度，`:88-92`）、Mechanicals 的 `DynamicCycleBehavior`（进度）、`RecipeRequirementsBehaviour<SpawnerRecipe>`（配方需求校验）。
- 实现 `DynamicCycleBehaviorSpecifics/RecipeRequirementsSpecifics/IHavePercent` 三个接口来接管 `tryProcess(simulate)`（`:279-312`）、`getProcessingTime()`、`matchesIngredients()`。
- 生成点定位用 `getSpawnPos() = 方块位置沿 Y 相对偏移`（`:136-137`），`isSpawnPosBlockLootCollector()` 判断该位置是否为空或采集器（`:146-163`），含"任意容器/原版物品保险库/Create 物品保险库"三级配置开关。
- 渲染定位用内部类 `SpawnPointValuePositioning extends ValueBoxTransform.Sided`（`:324-335`），仅水平面激活。

**4.2 配方系统** `content/components/recipe/`
- `SpawnerRecipe extends AbstractMechanicalRecipe`（Mechanicals 提供）；输入是 `SizedFluidIngredient`，输出是 `SpawnerRecipeOutput`（`ResourceKey<EntityType<?>>`，为空表示"随机"），另有 `customLoot: NonNullList<ProcessingOutput>`。
- 序列化（`SpawnerRecipeSerializer.java`）：`MapCodec` 用 `RecordCodecBuilder`，字段 `input/output/customLoot/processingTime/requirements/conditions`，全部 `optionalFieldOf` 带默认值；`StreamCodec` 手写 `toNetwork/fromNetwork`，复用 `CatnipStreamCodecBuilders.nonNullList`。
- 查找：`ModRecipes.findSpawner()` 用 `level.getRecipeManager().getAllRecipesFor(...).stream().filter(r -> r.matches(fluidStack)).findAny()`（`ModRecipes.java:39-47`），前提 `!level.isClientSide()`。

**4.3 战利品采集** `content/components/collector/` + `foundation/utility/LivingEntityHelper.java`
- 采集点有方块时**不生成实体**，直接把掉落塞进容器：`fillCollector`（`SpawnerBlockEntity.java:211-233`）→ 自定义掉落或 `fillCollectorWithMobLoot`。
- `LivingEntityHelper.getLootFromMob`（`:116-144`）：用 `DeployerFakePlayer` 造一个假玩家 + 附魔 `LOOTING` 的钻石剑，构造 `LootParams`（`withLuck(3)`、`TOOL/DAMAGE_SOURCE/LAST_DAMAGE_PLAYER`）后 `reloadableRegistries().getLootTable(...).getRandomItems(params)`——无需真的杀死生物即可产出战利品表结果。
- 随机模式 `spawnRandomLivingEntity` 从 `level.getBiome(pos).value().getMobSettings().getMobs(MobCategory.MONSTER).getRandom(random)` 取生态生成表。

**4.4 配置与应力** `infrastructure/config/`
- `MConfigs` 完全照抄 Create 的 `AllConfigs`（注释中标注来源）：`EnumMap<ModConfig.Type, ConfigBase>` + `ModConfigSpec.Builder.configure`，`onLoad/onReload` 事件派发（`MConfigs.java:23-74`），并把 `ModStress` 的 impact 注册进 `BlockStressValues.IMPACTS.registerProvider(stress::getImpact)`。
- 服务端配置 `ModConfigServer` 嵌套 `SpawnerConfigs`（`fluidCapacity/maxRange/allowAnyContainerForLootCollector/lootCollectorCapacity/customLootPerSpawnRecipeEnabled`，`SpawnerConfigs.java:10-16`）与 `ModStress`。

**4.5 数据生成** `infrastructure/data/ModDataGen.java:12-25`
- `GatherDataEvent` 中注册 `SpawnerRecipeGen`（`AbstractMechanicalRecipeGenerator<SpawnerRecipeBuilder>` 子类，构造器只传 namespace/typeId/builder Supplier/显示名）、`CreateMixingRecipeGen`、`SpawnerCompatRecipeGen`、`CreateItemApplicationRecipeGen`——即用 Create 的混合/物品应用配方生成"刷怪液"的获取途径。

**4.6 语言与兼容层**
- `generateLangEntries()`（`CreateMechanicalSpawner.java:78-97`）用 Mechanicals 的 `RegistrateLangBuilder` 一句话生成 tooltip/ponder/JEI 文案，不手写 en_us.json。
- JEI 分类 `compat/jei/SpawnerCategory.java`（150 行，含 `animations/AnimatedSpawner.java` 做动画）；Jade `compat/jade/MechanicalSpawnerPlugin.java`；KubeJS 通过 `src/main/resources/kubejs.plugins.txt` + `KubeJSCreateMechanicalSpawnerPlugin` 注册 `SpawnerRecipeSchema`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**未发现自定义网络包注册类**（无 `RegisterPayloadHandlersEvent`/`PacketDistributor` 使用），同步依赖原版配方同步 + 方块实体 `sendData()`（`tryProcess` 中被注释掉，`SpawnerBlockEntity.java:309-310`）。
- 数据驱动：配方即数据（`data/<ns>/recipe/spawner/*.json`），支持 `ICondition` 条件字段；状态显示 `SpawnerPointDisplay`/`SpawnerRenderer` 属客户端渲染。
- 配置：NeoForge `ModConfig`（SERVER/CLIENT）+ Create 风格 `ConfigBase` 嵌套，支持热重载事件。
- datagen：仅 server 端配方（`ModDataGen.java` 只用 `event.includeServer()`），无模型/语言 datagen。

## 6. Mixin

`src/main/resources/create_mechanical_spawner.mixins.json` 存在（`priority: 1100`、`refmap`、`injectors.defaultRequire: 1`），但 **`mixins` 与 `client` 数组均为空**，且源码树中不存在 `com/oierbravo/mechanical_spawner/mixin` 包（包名与主包 `create_mechanical_spawner` 不一致）。结论：**实际无 mixin**，配置文件是模板残留。`build.gradle` 中另开启了 `mixin.debug.export/verbose`。

## 7. 值得学的 5 条具体做法

1. **把注册表收敛到一个静态 `CreateRegistrate` 并绑定 tooltip 工厂**（`CreateMechanicalSpawner.java:38-44`，用 `ItemDescription.Modifier(...).andThen(TooltipModifier.mapNull(KineticStats.create(item)))`）；适用：所有 Create 附属，一次配置全局 tooltip/KineticStats。
2. **用 ScrollValueBehaviour + 自定义 ValueBoxTransform 做"无 GUI 参数化"**（`SpawnerBlockEntity.java:88-92`、`:324-335`）；适用：机器需要一个滚轮可调数值（高度/范围/速度）而不想写 Screen。
3. **用 `DeployerFakePlayer` + `LootParams` 直接算掉落表**（`LivingEntityHelper.java:116-144`）；适用：需要"模拟击杀/采集"产出（自动农场、战利品展示、JEI 预览）。
4. **把可复用机器逻辑抽到独立前置库 Mechanicals**（`build.gradle:140` + `AbstractMechanicalRecipe/DynamicCycleBehavior/RecipeRequirementsBehaviour/RegistrateLangBuilder`）；适用：作者多开 mod 时共享配方基类与行为，避免每个 mod 复制 Create 内部类。
5. **build 脚本按属性条件排除兼容代码**（`build.gradle:83-88`，`kubejs_enabled` 为 false 时 `exclude 'com/oierbravo/<mod>/compat/kubejs/**'`）；适用：可选兼容模块不引入依赖也能编译。
6. （附带）**配方 codec 用 `optionalFieldOf` 给每个字段兜底 + 复用 `ICondition.LIST_CODEC`**（`SpawnerRecipeSerializer.java:59-84`）；适用：数据驱动配方允许最小 JSON（只写 input/output）。

## 8. 公开 API / 库化程度

本 mod 不是库，但**强依赖作者自己的 API 库**：外部接入点全部在 `com.oierbravo.mechanicals.*`（`foundation/recipe/AbstractMechanicalRecipe`、`foundation/blockEntity/behaviour/{DynamicCycleBehavior,RecipeRequirementsBehaviour}`、`utility/RegistrateLangBuilder`、`compat/jade/IHavePercent`、`foundation/visual/QuarterShaftVisual`）。对第三方扩展者而言，新增刷怪配方只需提供 `spawner` 类型 JSON（`input/output/customLoot/processingTime/requirements/conditions`），KubeJS 侧通过 `SpawnerRecipeSchema` 注册。
