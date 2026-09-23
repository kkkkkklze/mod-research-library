# DragonsPlusMinecraft/CreateCentralKitchen 源码分析报告

## 1. 基本信息

Mod 名 Create: Central Kitchen；mod_id `create_central_kitchen`；作者 DragonsPlus；MC 1.21.1 + NeoForge 21.1.248；版本 2.6.0；许可证 LGPL-3.0-or-later（`gradle.properties:14-28`）。Gradle 插件：`java-library`、`net.neoforged.moddev 2.0.143`、`me.modmuss50.mod-publish-plugin`、`com.diffplug.spotless`（`build.gradle:1-8`）。

**编译依赖（重点）**：`create [6.0.10,)`；`create_dragons_plus [1.11.4,)` —— 作者自研前置库，本项目直接用其 `CDPRegistrate`、`RuntimePackResources`、`FieldsNullabilityUnknownByDefault`；`me.fallenbreath:conditional-mixin-neoforge:0.6.4`（compileOnly）；`jei 19.43.0.394`、`curios 9.5.1`；13 个 Farmer's Delight 系 mod 按 integration 源集引入（`build.gradle:202-267`）。

**定位**：不注册任何方块/物品，只把 FD 系机器接进 Create 的机械手 / 打包机 / 配方三条扩展点。

## 2. 源码规模与包结构

实测 **199 个 `.java`、10783 行**。主源集 `src/main/java` 仅 42 文件 1997 行；13 个 integration 源集共 157 文件 8786 行。

主包 `plus.dragons.createcentralkitchen`：`mixin/create` + `mixin/create/client` 共 12（含 1 个 accessor）、`client/burner` 3、`client/registry` 3、`client/ponder` 2、`common/registry` 2、`common/mechanicalarm` 2、`common/packager` 2、`config` 4、`data` 3、`integration/jei` 2，其余为 package-info。

integration 规模：`farmersdelight` 36 文件/2466 行、`extradelight` 24/1581、`brewinandchewin` 15/995、`hearthandharvest` 14/952、`dungeonsdelight` 14/429；最少 2 文件/56 行。

最大文件：`farmersdelight/ponder/FDPonderScenes.java` 614、`extradelight/.../ExtraDelightPonderScenes.java` 296、`hearthandharvest/HearthAndHarvestGameTests.java` 250、仓库根 `com/simibubi/create/content/kinetics/mechanicalArm/ArmInteractionPointHandler.java` 229。

## 3. 入口与注册

主类 `src/main/java/plus/dragons/createcentralkitchen/common/CCKCommon.java:47`；客户端 `client/CCKClient.java:36`（`@Mod(value = ID, dist = Dist.CLIENT)`）。

```java
public static final CDPRegistrate REGISTRATE = new CDPRegistrate(ID)
        .setTooltipModifier(item -> new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE));
public CCKCommon(IEventBus modBus, ModContainer modContainer) {
    REGISTRATE.registerEventListeners(modBus);
    CCKArmInteractionPointTypes.register(modBus);
    modBus.register(this);
    modBus.register(new CCKConfig(modContainer));
}
```

注册框架是 Registrate 衍生版 `CDPRegistrate`，但只用于本地化/datagen；业务注册走原生 `DeferredRegister`：`common/registry/CCKArmInteractionPointTypes.java:30` 用 `DeferredRegister.create(CreateRegistries.ARM_INTERACTION_POINT_TYPE, ID)`，并暴露 `holder(name)` / `register(holder, supplier)` 供各 integration 用 enum 常量登记（如 `farmersdelight/registry/FDArmInteractionPointTypes.java:35-47` 的 5 个交互点类型）。

## 4. 核心系统

**(1) 机械手交互点** — `common/mechanicalarm/StatefulBlockArmInteractionPoint.java`。把取放建模为**方块状态原子跃迁**：`insert()`/`extract()` 均 final，先 `planInsertion(state, stack)` / `planExtraction(state)` 产出记录 `Insertion(remainder, nextState, sound)`，`simulate=true` 时只规划不改世界（第 47-72 行）；子类只实现两个 plan 方法。`copySharedProperties()`（第 94 行）换状态时保留公共属性；`apply()` 单点 `level.setBlock(..., 3)`，`nextState == null` 即 `removeBlock`。

**(2) 打包机解包扩展** — `common/packager/ShapelessUnpackingHandler.java:32` 实现 Create 的 `api.packager.unpacking.UnpackingHandler`：把无序物品逐个塞进 `[slotStart, slotStart+slotCount)`，逐槽判空后 `insertItem(slot, item.split(1), simulate)`，失败即整体回滚返回 false（第 46-56 行）；子类只实现 `getInventory()`。

**(3) 烈焰灶 BlazeChef 客户端扩展** — `client/burner/BlazeBurnerClientExtension.java`、`BlazeBurnerRenderOverride.java`（199 行）配合 `mixin/create/client/BlazeBurnerRendererMixin.java:39` 的 `@WrapOperation` 包住 `renderSafe` 中的 `renderShared(...)` 改走 override；再加 `BlazeBurnerVisualMixin`（`@ModifyVariable` + `@Inject` 命中 `animate`）、`BlazeBurnerBlockEntityMixin`（`@ModifyExpressionValue` 改 `isValidBlockAbove()`、`@ModifyArg` 改粒子）。整条链只换视觉不换逻辑。

**(4) 配方转换（运行时数据包）** — `farmersdelight/recipe/CuttingBoardRecipeConverters.java`、`brewinandchewin/recipe/KegPouringRecipeConverters.java` 把 FD 砧板、Keg 倒注配方转成 Create 的 Deployer / 混合注液配方，每个模块配 `XxxRecipeGameTests` 验证。

**(5) Ponder 教程** — `client/ponder/CCKPonderPlugin.java` + 各 integration 的 `XxxPonderScenes`，注册于 `CCKClient.java:49` 的 `PonderIndex.addPlugin(...)`。

**(6) 配置框架** — `config/CCKConfig.java:38-46`：Common/Client 两个 POJO 各自 `registerAll(builder)`，`ModConfigSpec.Builder().configure(...)` 产出 spec 后 `modContainer.registerConfig(Type.COMMON/CLIENT, spec)`，再监听 `ModConfigEvent.Loading/Reloading` 按 spec 身份分发到 `onLoad()/onReload()`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自定义 payload**，全部复用 Create 自带包（`AllPackets`）。
- **运行时数据包（本仓库最有特色）**：`CCKCommon.java:70-90` 在 `AddPackFindersEvent` 构造 `RuntimePackResources("runtime", modContainer, PackType.SERVER_DATA, Position.TOP, ...)`，挂上 `CCKBlockTags`/`CCKItemTags` 两个 DataProvider 后 `event.addRepositorySource(pack)` —— **标签运行时生成并以最高优先级当数据包加载**，用于给 FD 等第三方物品打标签而不怕模组缺失。integration 侧用 `RuntimeDataGeneratorMixin` 挂钩。该能力来自 `create_dragons_plus`。
- **集成判定**：`integration/ModIntegration.java:27-63` enum 包住 modid，提供 `enabled()`（`ModList.get().isLoaded`）、`condition()`（`ModLoadedCondition`）、`asResource()`。
- **配置**：common + client 两个 toml，另在 common 下挂 `CCKRecipesConfig`。
- **datagen**：`build.gradle:356-359` 把 `src/generated/resources` 与 `generateModMetadata` 加入主资源；本地化仅在 `DatagenModLoader.isRunningDataGen()` 时用 `REGISTRATE.registerBuiltinLocalization("interface")` + `registerForeignLocalization()` 生成（`CCKCommon.java:64-67`），译文实体存 `src/translations/`。

## 6. Mixin

- 主配置 `src/main/resources/create_central_kitchen.mixins.json`：`required: true`、`priority: 1000`、`JAVA_21`、`injectors.defaultRequire: 1`；mixins 为 `create.BeltHelperMixin`、`create.DeployerBlockEntityAccessor`，client 为 4 个 `create.client.*`。
- 插件 `mixin/UniversalConditionalMixinPlugin.java:26` 继承 `conditionalmixin.api.mixin.RestrictiveMixinConfigPlugin`，条件交给注解。
- 集成 mixin 各自成配置（`create_central_kitchen.<name>.mixins.json`，5 份），由 gradle 按开关注入 mods.toml（`build.gradle:271-285`）。
- 代表 hook：`mixin/create/BeltHelperMixin.java:29,31` — `@Mixin(value = BeltHelper.class, priority = 2000)` + `@WrapMethod(method = "lambda$isItemUpright$1")`（连 lambda 都精确命中并用更高 priority 压过他人）；`mixin/create/DeployerBlockEntityAccessor.java:26-28` 用 `@Accessor` 取私有字段代替 AT；`BlazeBurnerRendererMixin.java:39` 用完整长签名 `@WrapOperation`；条件写法 `@Restriction(require = @Condition(ModIntegration.Mods.FARMERSDELIGHT))`（`mixin/farmersdelight/BeltDeployerCallbacksMixin.java:33`）。

## 7. 值得学的 5 条具体做法

1. **主源集 + N 个条件 integration 源集**：`build.gradle:43-100` 用 `providers.gradleProperty("enable_${name}_integration")` 决定是否创建 `src/integration/<name>` 源集并在 runtimeClasspath 拼装，integration 间还可声明依赖。适用：一个附属要接十几个同类 mod。
2. **gradle 生成 mods.toml 与 mixin 清单**：`build.gradle:271-348` 把 `integration_mixin_blocks`、`integration_dependency_blocks` 注入 `src/main/templates/META-INF/neoforge.mods.toml`（`[[mixins]]` 块为 `${integration_mixin_blocks}`），配 `neoForge.ideSyncTask generateModMetadata`。
3. **条件 mixin 用 `@Restriction` + 自定义 `RestrictiveMixinConfigPlugin`**：目标 mod 缺失时静默跳过，无需写 if。
4. **`@Accessor` 替代 AccessTransformer**：`DeployerBlockEntityAccessor` 只取一个字段，改动面最小。
5. **运行时数据包代替静态 JSON**：`CCKCommon.java:70-90` 用 `RuntimePackResources` + `Position.TOP` 注册动态数据包。适用：给第三方既有物品动态打标签、动态生成配方转换结果。

## 8. 库 / API 视角

非前置库（其可复用产物是 `create_dragons_plus`）。对下游暴露的扩展点是 Create 官方 API：`CreateRegistries.ARM_INTERACTION_POINT_TYPE` 与 `com.simibubi.create.api.packager.unpacking.UnpackingHandler`。

**未确认**：仓库根目录 `com/simibubi/create/content/kinetics/mechanicalArm/ArmInteractionPointHandler.java`（229 行）为 Create 原类源码副本，未被 `build.gradle` 任何 sourceSet 引用，用途未确认（疑为改写参考）。
