# JustEnoughItems 源码分析报告

## 1. 基本信息
- Mod 名：Just Enough Items；mod_id：`jei`；group `mezz.jei`；作者 mezz；MIT（`LICENSE.txt`）。
- 目标：Minecraft 26.2（neoform `26.2-2`）+ Java 25；NeoForge 26.2.0.69（loader `[4,)`，版本范围 `[26.2.0.67,)`）；Fabric Loader 0.19.4 + Fabric API 0.158.0+26.2（另有 AMECS 1.0.2 仅 Fabric，用于带修饰键的快捷键）。API 规范版本 `specificationVersion=30.32.0`（`gradle.properties`）。
- Gradle：Kotlin DSL，模块 `Changelog/Common/Fabric/NeoForge/Library/Debug/Gui`；插件 fabric-loom 1.17.20、moddevgradle 2.0.144、net.mezzdev.modshade 0.6.0（打包装依赖）、jarcompatibilitychecker 0.1.19、mod-publish-plugin 2.2.0；`buildSrc` 提供 `mezz.jei.project` 约定插件（`settings.gradle.kts` 中 `gradle.lifecycle.beforeProject` 自动应用）。
- 依赖：`net.mezzdev:baked-substring-index 0.1.0`、`net.mezzdev:suffixtree 1.1.0`（搜索索引）、JUnit 6.1.3。

## 2. 源码规模与包结构
实测 1149 个 `.java` / 99054 行。模块分布：`Common` 434（其中 `Common/src/api` 181、`Common/src/main` 221）、`Library` 256、`Gui` 232（main 210）、`NeoForge` 117、`Fabric` 84、`Debug` 26。
主要包：
- `mezz.jei.api.*`（公开 API，见 §8）
- `mezz.jei.common.*`：`config`(+`config/file` 自研 INI 框架) 21、`network`(+`network/packets`,`codecs`) 6、`platform` 15、`util` 33、`transfer` 9、`search` 12、`gui` 10、`input`、`ingredients`、`recipes`、`codecs`、`chat`、`collect`
- `mezz.jei.library.*`：`load`(+`load/registration`) 、`plugins/vanilla/{crafting,cooking,anvil,brewing,stonecutting,grindstone,compostable,ingredients}`、`gui/{recipes,ingredients,widgets,elements}`、`ingredients/subtypes`、`recipes`、`render/batch`、`transfer`、`runtime`、`startup`、`config/serializers`
- `mezz.jei.gui.*`：`overlay/{ingredients,bookmarks,elements}`、`recipes`、`config`、`search`、`ghost`、`filter`、`input`、`events`、`network`、`startup`
- `mezz.jei.neoforge.*` / `mezz.jei.fabric.*`：`platform`、`network`、`events`、`input`、`plugins`、`startup`、`mixin`
最大文件：`Gui/.../recipes/RecipesGui.java` 855、`Library/.../gui/recipes/RecipeLayout.java` 589、`Library/.../color/MMCQ.java` 536、`Library/.../gui/ingredients/RecipeSlot.java` 520、`Gui/.../config/InternalKeyMappings.java` 514、`Gui/.../overlay/bookmarks/BookmarkOverlay.java` 500；测试量也很大（`NeoForge/src/gameTest/.../RecipeTransferGameTests.java` 3139 行）。

## 3. 入口与注册
NeoForge：`@Mod(ModIds.JEI_ID) JustEnoughItems`（`NeoForge/src/main/java/mezz/jei/neoforge/JustEnoughItems.java:18-46`）注入 `IEventBus/Dist`，注册 `ServerConfig`、`NetworkHandler("3")`，并监听 `OnDatapackSyncEvent` 主动 `sendRecipes(CRAFTING, STONECUTTING, …)`；`dist.isClient()` 时走 `JustEnoughItemsClientSafeRunner.registerClient()`→`JustEnoughItemsClient`（同目录，:59 `ForgePluginFinder.getModPlugins()` → `StartData` → `JeiStarter`，`StartEventObserver` 控制启动/停止）。
Fabric：`Fabric/src/main/java/mezz/jei/fabric/startup/ClientLifecycleHandler.java:40` 用 `FabricPluginFinder.getModPlugins()`，由 `JeiLifecycleEvents.AFTER_RECIPES_UPDATED`/`GAME_STOP` 驱动启停。
注册形态：**无 DeferredRegister 主体**，唯一一处是 NeoForge 侧 `DeferredRegister<RecipeSerializer<?>>` 注册 `jei_shaped`/`jei_smelting`（`JustEnoughItemsClient.java:89-94`）；其余全部是"插件接口 + 分阶段回调"。

## 4. 核心系统
**(a) 插件发现与容错加载**
- NeoForge 用 `ModFileScanData` 扫 `@JeiPlugin` 注解再反射无参构造（`ForgePluginFinder.java:30-59`）；Fabric 用 entrypoint key `jei_mod_plugin`（`FabricPluginFinder.java:27-44`）。两者对单个插件异常只 error 记录（含 `LinkageError`），不拖垮整体。
- `library/load/PluginCaller.java:16-38`：`callOnPlugins(title, plugins, func)` 统一 Stopwatch 计时 + `PluginCallerTimer`，逐插件 try/catch，唯独 `VanillaPlugin` 出错立即抛出（"后面会崩在更难懂的地方"）。
- `library/startup/JeiStarter.java:82-87`：`PluginHelper.removePluginsWithCrashingUids` + `sortPlugins(vanillaPlugin, jeiInternalPlugin)` 保证加载顺序。

**(b) 分阶段注册流水线 `library/load/PluginLoader.java`**
顺序：subtypes → ingredients/extra/aliases/slotDisplays → modAliases → jeiHelpers → categories（含原版类别扩展）→ catalysts → `RecipeManagerInternal`（收集）→ advanced（装饰器/按钮工厂）→ recipes → transfer → runtime。每个 `I*Registration` 接口都由 `library/load/registration/*Registration` 实现，注册时即时校验（`RecipeCategoryRegistration.java:32-44`：recipeType 非空、UID 不重复、宽高 >0）。

**(c) 配方与原料类型系统**
- `api/recipe/category/IRecipeCategory.java`：`getRecipeType/getTitle/getWidth/getHeight/setRecipe(IRecipeLayoutBuilder, …)`，可选 `Codec`；`IRecipeType<T>` + `ITypedIngredient`/`IIngredientType` + 每类型一份 `IIngredientHelper`/`IIngredientRenderer`（`VanillaTypes.ITEM_STACK`），`IIngredientAcceptor` 让布局代码对物品/流体统一；渲染按类型批量（`library/render/batch/`）。

**(d) 配方转移（展示亮点）**
- 客户端只发结构化操作：`common/network/packets/PacketRecipeTransferWithResult.java:22-35` 用 `StreamCodec.composite` 编码 `TransferOperation` 列表 + crafting/inventory slot 索引 + maxTransfer/requireCompleteSets + transferId；服务端 `common/transfer/BasicRecipeTransferHandlerServer.java` 执行后回 `PacketRecipeTransferResult`，服务端没装 JEI 时降级 `packets/legacy/`。
- 扩展点：`api/recipe/transfer/{IRecipeTransferHandler,IUniversalRecipeTransferHandler,IRecipeTransferInfo}` + `IRecipeTransferRegistration`。

**(e) 跨加载器抽象**
- `common/platform/Services.java:11-19` 用 Java `ServiceLoader` 取 `IPlatformHelper`，13 个 `IPlatform*Helper`（World/Screen/Render/Recipe/Ingredient/Config/Mod/Fluid/Input/ItemStack/Brewing）由 Fabric、NeoForge 各实现一份；网络同样抽成 `IConnectionToServer`/`IConnectionToClient` + `PlayToServerPacket`/`PlayToClientPacket` 基类。

**(f) 自研 INI 配置框架 `common/config/file/`**
`IConfigSchemaBuilder.addCategory()/build()` → `ConfigSchema`/`ConfigValue`，`FileWatcher`+`FileWatcherThread` 监听磁盘改动经 `ConfigManager` 广播给 `IConfigListener`；序列化器可插拔（`ConfigSerializer`、`Library/config/serializers/{ChatFormattingSerializer,ColorNameSerializer}`）；对外只暴露 `IJeiConfigManager`/`IJeiConfigFile` 只读视图。实际文件：`jei-client.ini`、`jei-debug.ini`、`jei-mod-id-format.ini`、`jei-colors.ini`（`JeiStarter.java:93-106`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：全部基于原版 `CustomPacketPayload` + `StreamCodec`，NeoForge `NetworkHandler("3")`（协议版本号显式写在构造里）、Fabric `ClientNetworkHandler`；`neoforge.mods.toml` 用 `displayTest="IGNORE_SERVER_VERSION"` 允许进无 JEI 服务器。
- 数据驱动：配方由服务端同步（`OnDatapackSyncEvent.sendRecipes` / Fabric `AFTER_RECIPES_UPDATED` → `ClientLifecycleHandler.onRecipesSynchronized`），槽位解析走 `SlotDisplay`/Codec；未发现自建 datapack 格式。
- datagen：仓库中未见 datagen sourceSet（未确认）。
- 测试：`src/test`、`src/gameTest`（NeoForge）、`src/keyMappingGametest`（Fabric）三套，GUI 逻辑有单测（`Gui/src/test/.../IngredientGridConfigTest.java` 2009 行）。

## 6. Mixin
- Fabric：`Fabric/src/main/resources/jei.mixins.json`（package `mezz.jei.fabric.mixin`，compatibilityLevel `JAVA_25`；`mixins`: AmecsKeyModifiersEarlyInitMixin；`client`: `ClientPacketListenerRecipeUpdateMixin`、`EffectsInInventoryMixin`、`GuiGraphicsExtractorMixin`、`KeyboardHandlerMixin`、`MinecraftMixin`、`ScreenMixin`）。
- NeoForge：未见 mixin 配置，改用 `NeoForge/src/main/resources/META-INF/accesstransformer.cfg`（AT 代替 mixin 的方案对比）。

## 7. 值得学的 5 条具体做法
1. 插件体系"双通道发现 + 单插件隔离"：注解扫描（`ForgePluginFinder.java:46-60`）/entrypoint（`FabricPluginFinder.java:27-44`），每个插件单独捕获 `RuntimeException|LinkageError`，坏插件不影响宿主启动。
2. 每个注册阶段独立计时与日志标题：`PluginLoader` 全程 `PluginCaller.callOnPlugins("Registering xxx")`，可直接定位是哪个 mod 的哪个阶段慢。
3. 注册入口即时校验（UID 唯一、尺寸 >0）：`RecipeCategoryRegistration.java:32-44`，把错误抛在插件作者能看懂的位置。
4. API 与实现分目录独立打包：`Common/src/api` → 独立 `jei-<mc>-common-api` jar（`Common/build.gradle.kts:38-50` 的 `apiSourceSet` + `apiClassesElements` capability），配 `checkApiCompatibility`/jarcompatibilitychecker + `@ApiStatus.NonExtendable` 锁扩展面。
5. 客户端只发"操作清单"、服务端执行回执：`PacketRecipeTransferWithResult` + `BasicRecipeTransferHandlerServer`，避免把预览逻辑写进服务端。

## 8. 公开 API（JEI 是典型 API/前置模组）
- 包路径：`Common/src/api/java/mezz/jei/api`（181 文件），另有 `Fabric/src/api/java/mezz/jei/api/fabric`、`NeoForge/src/api/java/mezz/jei/api/neoforge`。子包：`registration/`、`runtime/`(+`runtime/config`)、`recipe/{category,transfer,types,vanilla,advanced,extensions}`、`gui/{builder,ingredients,widgets,inputs,drawable,placement,buttons,handlers}`、`ingredients/`(+`rendering`,`subtypes`)、`helpers/`、`search/`、`constants/`。
- 接入方式：实现 `IModPlugin` 并标注 `@JeiPlugin`（必须有公共无参构造，Fabric 还需在 fabric.mod.json 声明 entrypoint `jei_mod_plugin`）；早期特性开关用 `configureJei(IJeiFeatures)`。
- 主要扩展点：`IRecipeCategory`/`IRecipeType`（配方类型与 GUI）、`IIngredientType`+`IIngredientHelper`+`IIngredientRenderer`/`ISubtypeRegistration`（自定义原料与子类型）、`IGuiHandlerRegistration`（GUI 交互区域）、`IRecipeTransferHandler`/`IUniversalRecipeTransferHandler`（转移）、`IAdvancedRegistration`（`IRecipeManagerPlugin`、类别装饰器、配方按钮工厂）、`IRuntimeRegistration`/`IJeiRuntime`（运行时替换与查询）、`IJeiConfigManager`。
- 版本与稳定性约定：`getPluginUid()` 必须以 modId 作命名空间；API 方法大量标注 `@since`、`@ApiStatus.NonExtendable`，并在构建期用 `checkApiCompatibility` 比较同大版本已发布 API jar。
