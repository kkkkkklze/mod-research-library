# KubeJS-Mods/KubeJS-Create 源码分析报告

> 快照 `_参考仓库/_bulk/KubeJS-Mods__KubeJS-Create`，commit `b1f7084`（2025-11-12，"Fix modrinth publishing by shortening version number"）。
> 本仓库是典型的"附属集成 mod"：自身代码极少（455 行），价值全在"如何给 KubeJS 写集成"。

## 1. 基本信息

- Mod 名 / id：KubeJS Create / `kubejs_create`；作者 `latvian.dev`（LatvianModder）；版本 `2101.3.1`（`gradle.properties:11-13`）
- 目标环境：MC **1.21.1** / **NeoForge 21.1.200**，Parchment 2024.11.17（`gradle.properties:15-18`）
- Gradle 插件：`net.neoforged.moddev` **2.0.107** + `me.shedaniel.unified-publishing` + `foojay-resolver-convention`（`build.gradle:1-12`）
- 许可证 **MIT**（`src/main/resources/META-INF/neoforge.mods.toml:4`；仓库根目录无 LICENSE 文件）
- 编译依赖（`build.gradle` 的 `dependencies`）：`api kubejs-neoforge:2101.7.2-build.285` + `interfaceInjectionData("...kubejs-neoforge")`；`implementation create-1.21.1:6.0.7-159 (slim, transitive=false)`、`Ponder-NeoForge-1.21.1:1.0.63`、`Registrate MC1.21-1.3.0+62`；`compileOnly flywheel-neoforge-api-1.21.1:1.0.2`；`runtimeOnly jei-1.21.1-neoforge:19.25.0.322`
- 依赖关系：**KubeJS 是它唯一的 API**（本体只写 KubeJS 插件回调）；它把 Create 暴露给脚本，自己不再对外提供 API

## 2. 源码规模与包结构

实测 `find src -name '*.java' | wc -l` = **13** 个文件，**455** 行；全部位于 `src/main`，无 client/server 拆分、无 datagen sourceSet。

| 包（`dev.latvian.mods.kubejs.create.*`） | 文件数 | 关键文件（行数） |
|---|---|---|
| `create` | 2 | `KubeJSCreatePlugin`(105)、`KubeJSCreate`(6) |
| `create.events` | 4 | `SpecialFluidHandlerEvent`(73)、`SpecialSpoutHandlerEvent`(33)、`BoilerHeaterHandlerEvent`(25)、`CreateEvents`(12) |
| `create.recipe` | 2 | `ProcessingOutputRecipeComponent`(68)、`CreateRecipeComponents`(18) |
| `create.wrapper` | 1 | `KubeCreateOutput`(52) |
| `create.item` | 2 | `SandpaperItemBuilder`(23)、`SequencedAssemblyItemBuilder`(17) |
| `create.core.mixin` | 2 | `FluidIngredientStacksInvoker`(14)、`ProcessingOutputMixin`(9) |

## 3. 入口与注册

- 加载器入口几乎是空类：`src/main/java/dev/latvian/mods/kubejs/create/KubeJSCreate.java:6` —— `@Mod("kubejs_create") public class KubeJSCreate {}`，**没有 DeferredRegister**（依赖里引了 Registrate，但源码未使用）
- 注册全在 KubeJS 插件回调里：`src/main/resources/kubejs.plugins.txt` 只有一行 `dev.latvian.mods.kubejs.create.KubeJSCreatePlugin create`，KubeJS 据此实例化 `KubeJSPlugin` 并回调：
  - `registerBuilderTypes(BuilderTypeRegistry)`：向 `Registries.ITEM` 添加 `create:sequenced_assembly`、`create:sandpaper` 两种 Builder（`KubeJSCreatePlugin.java:38-45`）
  - `registerRecipeSchemas/registerRecipeComponents/registerEvents/registerBindings/registerTypeWrappers/registerDataComponentTypeDescriptions`（同文件 `:47-92`）
  - `afterInit()` 内以 `ScriptType.STARTUP` 触发 3 个自定义事件（`:31-36`）
- 值得注意：`registerRecipeSchemas()` 目前**只有注释**（列出 conversion/crushing/cutting/milling/basin/mixing/compacting/pressing/… 待做项），Create 配方 schema 尚未实现；`META-INF/accesstransformer.cfg` 为空文件

## 4. 核心系统

1) **脚本事件桥**（`create/events/CreateEvents.java:8-12`）：`EventGroup.of("CreateEvents")` 下 3 个 startup 事件 `pipeFluidEffect`/`spoutHandler`/`boilerHeatHandler`，把 Create 的注册入口整体转给脚本。
   - `BoilerHeaterHandlerEvent.add(Block, cb)` → `BoilerHeater.REGISTRY.register(...)`；`addAdvanced(BlockStatePredicate, cb)` → `registerProvider(block -> block.testBlock(blockIn) ? handler : null)`（`BoilerHeaterHandlerEvent.java:19-30`）
   - `SpecialSpoutHandlerEvent.add(...)` 返回 `SimpleRegistry.Provider<Block, BlockSpoutingBehaviour>`，`block.test(world.getBlockState(pos))` 为假时返回 0（`SpecialSpoutHandlerEvent.java:26-36`）
2) **惰性集合缓存 + 注册表失效回调**（`SpecialFluidHandlerEvent.java:29-73`）：自定义 `SimpleRegistry.Provider` 借 `@Invoker` mixin 调 `FluidIngredient.generateStacks()` 算出 `Set<Fluid> validFluids`；`onRegister(Runnable invalidate)` 中监听 `TagsUpdatedEvent`，仅在 `shouldUpdateStaticData()` 时 `invalidate.run()` + 置空缓存重算
3) **JS 值 → `ProcessingOutput` 包装**（`wrapper/KubeCreateOutput.java:35-51`）：`switch` 模式匹配 null / `ProcessingOutput` / `ItemStack` / `ItemLike` / `JsonObject{chance,output}` / `Map`，`chance` 一律 `Mth.clamp(c,0,1)`，空栈与空气统一为 `ProcessingOutput.EMPTY`
4) **配方组件**（`recipe/ProcessingOutputRecipeComponent.java:24-67`、`recipe/CreateRecipeComponents.java`）：实现 `hasPriority/matches/replace/isEmpty/buildUniqueId`，替换时保留原 `getChance()`；`HEAT_CONDITION` = `EnumComponent.of(Create.asResource("heat_condition"), HeatCondition.class, HeatCondition.CODEC)`，`SIZED_FLUID_INGREDIENT` 复用 `CreateCodecs.FLAT_SIZED_FLUID_INGREDIENT_WITH_TYPE`
5) **反射式数据组件注册**（`KubeJSCreatePlugin.java:76-92`）：遍历 `AllDataComponents` 的 public static `DataComponentType` 字段，用泛型实参 `TypeInfo.of(t.getActualTypeArguments()[0])` 自动注册类型信息——Create 新增组件时本 mod 无需改动
6) **两个物品 Builder**：`SandpaperItemBuilder` 默认打 `AllTags.AllItemTags.SANDPAPER` 标签并用 `ItemDescription.referKey(item, AllItems.SAND_PAPER)` 复用 Create 的 tooltip；`SequencedAssemblyItemBuilder` 产出 `SequencedAssemblyItem`

## 5. 网络 / 数据驱动 / 配置 / datagen

**均为"无"**。没有自定义网络包、没有 Config 类、没有 NeoForge datagen、没有数据包资源。`src/main/resources` 仅有：`kubejs.plugins.txt`、`kubejs.classfilter.txt`（内容一行 `+ com.simibubi.create.`，放开脚本对 Create 类的引用）、`kubejs_create.mixins.json`、空的 `accesstransformer.cfg`、`neoforge.mods.toml`（`processResources` 用 `expand` 注入 `version/kubejs_version/create_version`，见 `build.gradle` 的 processResources 段）。

## 6. Mixin

配置：`src/main/resources/kubejs_create.mixins.json`（`required:true`、`package dev.latvian.mods.kubejs.create.core.mixin`、`compatibilityLevel JAVA_21`、`injectors.defaultRequire=1`、`maxShiftBy=2`；`client` 为空）。

- `core/mixin/ProcessingOutputMixin.java:7-9`：`@Mixin(ProcessingOutput.class) public class ProcessingOutputMixin implements KubeCreateOutput` —— **空 mixin，仅做接口注入**（源码注释自称 "mildly cursed"）
- `core/mixin/FluidIngredientStacksInvoker.java:11-14`：`@Mixin(FluidIngredient.class)`，`@Invoker Stream<FluidStack> callGenerateStacks()`

## 7. 值得学的 5 条

1. 附属 mod 不自建注册/配置体系，只用 KubeJS 的 `KubeJSPlugin` 回调 + jar 内 `kubejs.plugins.txt`（`KubeJSCreatePlugin.java`）——任何"某 mod 的 KubeJS 集成"都可照抄这套骨架
2. **空 mixin + `implements`** 给第三方类补接口，避免遍地包装类（`ProcessingOutputMixin.java` + `wrapper/KubeCreateOutput.java`），配合 `TypeWrapperRegistry.register(ProcessingOutput.class, ...)` 让脚本直接传 `ItemStack`/`{chance:0.5,output:...}`
3. 访问第三方 protected 成员时单独写 `@Invoker` mixin 收口（`FluidIngredientStacksInvoker.java`）；缓存集合时用 Provider 的 `onRegister(invalidate)` + `TagsUpdatedEvent` 失效（`SpecialFluidHandlerEvent.java:53-73`）
4. 用反射枚举对方的"常量注册表"字段自动生成类型信息，对方更新时零维护（`KubeJSCreatePlugin.registerDataComponentTypeDescriptions`）
5. 序列化一律复用对方 Codec 而不是自己重写（`CreateRecipeComponents.java` 的 `HeatCondition.CODEC` 与 `CreateCodecs.FLAT_SIZED_FLUID_INGREDIENT_WITH_TYPE`）

## 8. 外部 mod 接入方式（集成/附属 mod 补充）

本仓库不对外暴露 API 包。它自己的"接入方式"就是教科书样例：实现 `dev.latvian.mods.kubejs.plugin.KubeJSPlugin` 的 `register*` 回调，在 `src/main/resources/kubejs.plugins.txt` 写 `<插件类全名> <id>`，并用 `kubejs.classfilter.txt` 一行 `+ com.simibubi.create.` 把对方包名加入脚本可见白名单。
