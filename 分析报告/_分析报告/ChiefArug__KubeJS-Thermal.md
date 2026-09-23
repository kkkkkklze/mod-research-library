# ChiefArug/KubeJS-Thermal 源码分析报告

> 快照路径按任务给定为 `_参考仓库/_bulk/ChiefArug__KubeJS-Thermal`（原先不存在，本次据 GitHub 实际仓库 clone 后放入）。
> **仓库位置更正**：GitHub 上不存在 `ChiefArug/KubeJS-Thermal`；实际仓库为 **`KubeJS-Mods/KubeJS-Thermal`**（分支 `1605/1802/1902/2001/workflows`），本次分析 clone 的是分支 **`2001`**（1.20.1），HEAD `f555642`（"remove old changelog script"）。CurseForge/Modrinth 页面与 KubeJS 官方 wiki 的该集成文档常被记到 ChiefArug 名下（未在源码中确认）。

## 1. 基本信息

- Mod 名 / id：KubeJS Thermal / `kubejs_thermal`；`mod_name=kubejs-thermal`；作者 `LatvianModder`（`gradle.properties` 的 `mod_author`、`mods.toml` 的 `authors`）；描述 "KubeJS Thermal Expansion integration"
- 版本：`mod_version=2001.1.10`；CurseForge `421694`、Modrinth `taN3HInZ`（`gradle.properties`）
- 目标环境：MC **1.20.1** / **Forge 47.2.19**；`loom.platform=forge`（**Architectury Loom**，`build.gradle:62-65` 用 `minecraft/forge/mappings loom.officialMojangMappings()`）
- 许可证：**GNU LGPL v3**（仓库根 `LICENSE.txt` 为 LGPLv3 全文；`mods.toml:4` 亦写 "GNU LGPLv3"）
- 编译依赖（`build.gradle:61-80`）：`kubejs-forge:2001.6.4-build.114`（硬前置，`mods.toml` 里 kubejs `versionRange=[1902.6.1-build.300,)`，`thermal_expansion [1.3.0,)`）；其余 Thermal/CoFH 全部用 **cursemaven 文件号** 硬编码：`cofh-core / thermal-foundation / thermal-expansion / thermal-cultivation / thermal-locomotion / thermal-innovation / thermal-dynamics`，另加 `com.teamcofh:thermal_core:1.20.1-11.+`；`jei`
- 依赖关系：**KubeJS 提供 API**，CoFH 系列提供被集成的配方体系

## 2. 源码规模与包结构

实测 `find src -name '*.java' | wc -l` = **16**，总 **535** 行；全部在 `dev.latvian.mods.kubejs.thermal`（含 `mixin` 子包 1 个文件），无 client/server 拆分、无 datagen。

最大文件：`ThermalRecipeJS`(97)、`mixin/FluidIngredientMixin`(59)、`KubeJSThermalPlugin`(57)、`ThermalAugmentItemBuilder`(54)、`BasicRecipeSchema`(53)、`FuelRecipeSchema`(44)、`InsolatorRecipeSchema`(25)；其余 9 个 `*RecipeSchema` 均为 4-21 行的纯声明接口。

## 3. 入口与注册

- 加载器入口 `KubeJSThermal.java`：`@Mod(KubeJSThermal.MOD_ID)` 且只有 `MOD_ID = "kubejs_thermal"`，无 DeferredRegister、无 Registrate——物品注册交给 KubeJS
- 真正入口：`src/main/resources/kubejs.plugins.txt` → `dev.latvian.mods.kubejs.thermal.KubeJSThermalPlugin`（`extends KubeJSPlugin`），体现 KubeJS **1.20.1 时代 API**（与 1.21 的 `RecipeSchemaRegistry/BuilderTypeRegistry` 回调不同）：
  - `init()`：`RegistryInfo.ITEM.addType("thermal_augment", ThermalAugmentItemBuilder.class, ThermalAugmentItemBuilder::new)`（`KubeJSThermalPlugin.java:16-19`）
  - `registerRecipeSchemas(RegisterRecipeSchemasEvent)`：`event.namespace(ModIds.ID_THERMAL).register(...)` 链式一口气挂上 **30+ 个** Thermal 配方类型（`:22-57`）——furnace/sawmill/pulverizer(+recycle)/smelter(+recycle)/centrifuge/press/crucible/chiller/refinery/pyrolyzer/bottler/brewer/crystallizer → `BasicRecipeSchema.SCHEMA`；insolator 单列；pulverizer/smelter/insolator 催化剂 → `CatalystRecipeSchema.SCHEMA`；stirling/numismatic/lapidary/disenchantment/gourmand（物品燃料）与 compression/magmatic（流体燃料）→ `FuelRecipeSchema.ITEM_FUEL / FLUID_FUEL`；hive-extractor/tree-extractor mapping、tree-extractor boost、fisher boost、rock-gen mapping、potion-diffuser boost → 各自的 schema

## 4. 核心系统

1) **声明式 RecipeSchema**（`BasicRecipeSchema.java`、`FuelRecipeSchema.java`、`CatalystRecipeSchema.java` 及各 Mapping/Boost schema）：每个接口只有若干 `RecipeKey<T>` 常量 + 一行 `new RecipeSchema(ThermalRecipeJS.class, ThermalRecipeJS::new, ...)`。键的特性用得齐全：`.key(RecipeJsonUtils.X)`（复用 CoFH 常量名）、`.alt(其它别名)`（兼容 Thermal 历史字段名 output/result/inputs 等）、`.optional(...)`、`.preferred("energyMod")`（JS 侧更友好的名字）、`.exclude()`；`ENERGY` 的默认值写成 **按配方类型分发** 的 lambda：`type -> switch (type.id.getPath()) { case TCoreRecipeTypes.ID_FURNACE_RECIPE -> FurnaceRecipeManager.instance().getDefaultEnergy(); ... default -> 0; }`（`BasicRecipeSchema.java:34-47`）
2) **第三方 JSON 方言适配层**（`ThermalRecipeJS.java:19-96`）：覆写 `readInputItem/writeInputItem` 支持 Thermal 的 `{value:<ingredient>, count|amount:n}`（仅在 `count>1` 时写回对象）；覆写 `inputFluidHasPriority/readInputFluid/writeInputFluid` 识别 `{fluid,fluid_tag}`，内部用 `cofh.lib.common.fluid.FluidIngredient` 与 `RecipeJsonUtils.parseFluidIngredient`，并通过 architectury 的 `FluidStackHooksForge` 在 KubeJS 的 `FluidStackJS` 与 Forge `FluidStack` 间转换
3) **接口注入 mixin**（`mixin/FluidIngredientMixin.java:17-59`）：`@Mixin(cofh.lib.common.fluid.FluidIngredient.class) implements InputFluid`，`@Shadow` 取 `amount` 与 `@Final IFluidList[] values`，实现 `kjs$getAmount/kjs$isEmpty/kjs$copy(amount)/matches(FluidLike)`；`kjs$copy` 用 `FluidIngredient.fromValues(Arrays.stream(values))` + `setAmount` 复制，使 CoFH 的流体原料可被 KubeJS 当 `InputFluid` 使用
4) **自定义物品类型 = Augment**（`ThermalAugmentItemBuilder.java`）：`LinkedHashMap<String,Float> thermalMods` + `augmentType` 两个 `transient` 字段，`createObject()` 里 `AugmentDataHelper.builder().type(augmentType).mod(k,v)...build()` 生成 `AugmentItem`；`baseMod(float)` 是 `TAG_AUGMENT_BASE_MOD` 的便捷别名；三个外来方法均带 KubeJS 的 `@Info("...")` 注解（会进入类型提示文档）
5) 轻量配置化：所有被集成类型都取自 `TCoreRecipeTypes` 常量（而非硬编码字符串），默认值取自 Thermal 自己的 Manager（`getDefaultEnergy()/getDefaultWater()`），保证与游戏内实际配方管理器一致

## 5. 网络 / 数据驱动 / 配置 / datagen

前四项中：**无网络包、无 Config、无 datagen**。"数据驱动"体现在把 Thermal 的 datapack 配方体系（机器、燃料、催化剂、生物/环境类 mapping 与 boost）整体暴露为 KubeJS schema。`src/main/resources` 仅 `kubejs.plugins.txt`、`kubejs.classfilter.txt`（`+ cofh.`）、`kubejs-thermal.mixins.json`、`META-INF/mods.toml`、`pack.mcmeta`。

## 6. Mixin

`src/main/resources/kubejs-thermal.mixins.json`（`required:true`、`package dev.latvian.mods.kubejs.thermal.mixin`、`compatibilityLevel JAVA_17`、`injectors.defaultRequire=1`、`maxShiftBy=2`）——**仅 1 个**：`FluidIngredientMixin`（目标 `cofh.lib.common.fluid.FluidIngredient`，无 `@Inject`，纯 `@Shadow` + 接口实现）。

## 7. 值得学的 5 条

1. 一组 `RecipeKey` 覆盖一批配方类型：`BasicRecipeSchema` 同一 schema 服务 13 个 machine/`_recycle` 类型，用 `optional(type -> switch(type.id.getPath()))` 按类型给默认值（`BasicRecipeSchema.java:36-47`）——写机器 mod 的 KubeJS 集成时可照抄
2. 第三方原料类型通过 `mixin implements <KubeJS 接口>` 融入体系（`FluidIngredientMixin` → `InputFluid`），比写适配器少一半代码
3. 在 `RecipeJS` 子类里集中消化对方的 JSON 方言（`{value,count|amount}`、`{fluid,fluid_tag}`），而不是在每个 schema 上打补丁（`ThermalRecipeJS.java`）
4. 给脚本可用方法加 `@Info` 注解即得文档（`ThermalAugmentItemBuilder.java:26-42`）
5. 依赖用 `gradle.properties` + `curse.maven:<slug>:<fileId>` 集中管理（`build.gradle:61-80`）；反例是 `mods.toml` 里的 `kubejs versionRange` 仍写着 `1902.6.1-build.300`、`issueTrackerURL` 还带 `mc=1902`，说明这类手写版本区间容易随分支漂移，升级时要同步

## 8. 外部接入方式（附属 mod 补充）

不对外暴露 API 包。接入方式与 KubeJS Create 同构：实现 KubeJS 的 `KubeJSPlugin`（注册在 `kubejs.plugins.txt`），在 `init()` 里 `RegistryInfo.ITEM.addType(...)` 扩展脚本物品类型，在 `registerRecipeSchemas(RegisterRecipeSchemasEvent)` 里 `event.namespace("<modid>").register("<recipe_type_id>", schema)` 把对方配方类型交给脚本。
