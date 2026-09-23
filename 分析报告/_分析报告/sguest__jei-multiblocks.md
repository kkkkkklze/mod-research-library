# sguest/jei-multiblocks 源码分析报告

## 1. 基本信息
Just Enough Immersive Multiblocks / `jeimultiblocks` / sguest / 1.0.6 / MIT / group `sguest.jeimultiblocks`。MC 1.21.1，NeoForge 21.1.93（loader `[4,)`），单模块，Java 21。插件：`java-library` + `net.neoforged.gradle.userdev 7.0.170`（`build.gradle:1-7`）。依赖：`blusunrize.immersiveengineering:1.21.1-12.0.0-182.88`（被接入 API）、JEI `19.21.0.247` 与 EMI `1.1.22` 仅 compileOnly（`localRuntime` 按 `recipe_viewer` 属性二选一）。`neoforge.mods.toml` 中 IE 为 required 且 `ordering="BEFORE"`，jei/emi 为 optional。

## 2. 规模与包结构
`.java` 9 个 / 414 行（tracked 文件 28 个）。包：`sguest.jeimultiblocks`（JeiMultiblocks、MultiblockUtils、ContentHelper、JeiMultiblocksEventHandler）、`.jei`（JeiModPlugin、MultiblockRecipeCategory）、`.emi`（EmiModPlugin、EmiMultiblockRecipe、MultiblockWidget）。最大：`MultiblockRecipeCategory.java` 96、`EmiMultiblockRecipe.java` 98、`JeiModPlugin.java` 60。

## 3. 入口与注册
`JeiMultiblocks.java:5-8` 只有 `@Mod` + MODID，本 mod 不注册任何方块/物品。三个插件入口代替注册系统：`@JeiPlugin JeiModPlugin`、`@EmiEntrypoint EmiModPlugin`、`@EventBusSubscriber(bus=GAME, value=CLIENT) JeiMultiblocksEventHandler`。

## 4. 核心系统
1. **只读 IE 注册表当数据源**（`MultiblockUtils.java:12-26`）：`MultiblockHandler.getMultiblocks()` 过滤 `instanceof TemplateMultiblock`，分别输出 `List<IMultiblock>`（配方）与 `new ItemStack(item.getBlock())`（搜索条目）。
2. **JEI 分类复用 IE 手册渲染**（`MultiblockRecipeCategory.java:44-53`）：`IRecipeCategory<IMultiblock>`，`draw()` 里构造 `{"name": multiblock.getUniqueName()}` 交给 `manual.getElementFactory(IE "multiblock").apply(json)` 得到 `SpecialManualElement`，`render(guiGraphics, screen, 30, 20, 0, 0)`——**鼠标坐标传 0,0 以屏蔽手册 tooltip**。材料槽来自 `ClientMultiblocks.get(multiblock).getTotalMaterials()`，`x=154` 起每 20px 一列、`y>100` 换列（`:76-95`）。
3. **生命周期延迟注册**（`JeiModPlugin.java:33-58`）：`registerExtraIngredients` 用 `addExtraItemStacks` 让多方块物品可被搜索；因 `onRuntimeAvailable` 时 IE 的 `ClientMultiblocks` 未就绪，不当场 `addRecipes`，而是把调用包成 `Callable<Boolean>` 交给 `JeiMultiblocksEventHandler.registerCallback`，由 `ClientTickEvent.Pre` 首帧执行一次后置 null（`JeiMultiblocksEventHandler.java:19-28`）。
4. **EMI 一等插件**（`EmiModPlugin.java:19-40`、`EmiMultiblockRecipe.java`、`MultiblockWidget.java`）：`EmiRecipeCategory` 图标/工作站均为 IE 锤子（`ContentHelper.java:9-12` 从 `BuiltInRegistries.ITEM` 取 `immersiveengineering:hammer`）；`MultiblockWidget.getBounds()` 返回 `Bounds.EMPTY` 不拦截点击，内部复用同一手册元素渲染，与 JEI 侧共用逻辑。

## 5. 网络 / 数据驱动 / 配置 / datagen
全部无。内容来自 IE 运行时注册表与 IE 手册 JSON（`immersiveengineering:multiblock` 元素工厂）。

## 6. Mixin
无。

## 7. 值得学的 5 条
1. 做查看器附属先找目标的运行时注册表 API（`MultiblockHandler.getMultiblocks()`），不解析 JSON/不硬编码。
2. 预览复杂结构时复用目标模组的 GUI 组件，并传 `(0,0)` 鼠标坐标屏蔽其 tooltip（`MultiblockRecipeCategory.java:49-52`）。
3. "客户端 tick 一次性回调"破解插件注册期数据未就绪的竞态（`JeiMultiblocksEventHandler.java`）。
4. 同 mod 支持 JEI+EMI：两套插件平行目录（`jei/`、`emi/`）只共享数据/渲染工具类，不引兼容库；JEI 用 `localRuntime` 而非 `runtimeOnly` 避免污染下游（`build.gradle:113-121`）。
5. `gradle.properties` 的 `recipe_viewer` 属性切换开发环境加载的查看器。

## 8. 库/API 视角
不提供 API，是纯消费者：消费 `blusunrize.immersiveengineering.api.*`（`MultiblockHandler`、`TemplateMultiblock`、`ClientMultiblocks`、`ManualHelper`、`Lib`）与 `mezz.jei.api`/`dev.emi.emi.api`。可作为 JEI/EMI 双端插件的最小模板（414 行）。
