# KubeJS-Mods/KubeJS 源码分析报告

本地路径：`...\_bulk\KubeJS-Mods__KubeJS`（下文路径相对仓库根）

## 1. 基本信息

KubeJS / `kubejs` / latvian.dev（group `dev.latvian.mods`）/ v8.0.6（`gradle.properties:5-7`）；MC `26.1.2` + NeoForge `26.1.2.84`，Java 25，仅 NeoForge；LGPLv3（`src/main/resources/META-INF/neoforge.mods.toml:3`）。
Gradle：`net.neoforged.moddev` 2.0.138 + `com.almostreliable.almostgradle` 2.1.1（`build.gradle.kts:3-6`，用其配置 JEI/REI 运行环境）。
依赖：`rhino`（JS 引擎，api、非传递）、`better-advanced-tooltips`；jarJar 内置 `tiny-java-server` 与 `animated-gif-lib-for-java`；可选 JEI/REI/EMI/architectury。它本身即"脚本 API 提供者"，NeoForge 只提供注册/事件。

## 2. 规模与包结构

913 个 `.java` / 64301 行（`find . -name '*.java' | wc -l` 与 `cat | wc -l`）。
包（第 2 层）：`recipe` 158、`core` 152、`block` 76、`util` 63、`client` 48、`plugin` 45、`item` 45、`integration` 37、`script` 36、`net` 21、`web` 19、`registry` 17。
最大文件：`plugin/builtin/BuiltinKubeJSPlugin.java` 843、`block/BlockBuilder.java` 831、`recipe/KubeRecipe.java` 682、`script/ConsoleJS.java` 680、`recipe/RecipesKubeEvent.java` 668、`core/EntityKJS.java` 574、`component/DataComponentWrapper.java` 557、`block/state/BlockStatePredicate.java` 554。

## 3. 入口与注册

主类 `src/main/java/dev/latvian/mods/kubejs/KubeJS.java`，构造器 `(IEventBus, Dist, ModContainer)`：

```java
var allMods = new ArrayList<>(ModList.get().getMods().stream()...toList());
allMods.remove(thisModFile); allMods.addFirst(thisModFile);   // 自己优先
KubeJSPlugins.load(allMods, dist == Dist.CLIENT);
startupScriptManager = new StartupScriptManager();
KubeJSPlugins.forEachPlugin(KubeJSPlugin::init);
if (!datagen) startupScriptManager.reload();
KubeJSRecipeSerializers.REGISTRY.register(bus); KubeJSMenus.REGISTRY.register(bus);
```

注册框架非 DeferredRegister：`registry/RegistryType`（`ResourceKey→TypeInfo` 三张静态 Map + `Scanner.init()`）+ `registry/BuilderTypeRegistry`（注册 `BuilderBase` 类型，如 item 的 `sword`）；实际填充在 `registry/RegistryEventHandler`（`@EventBusSubscriber` 监听 NeoForge `RegisterEvent`，`EventPriority.LOW`）：先 `StartupEvents.REGISTRY.post(...)` 跑脚本，再从 `RegistryObjectStorage` 逐个 build。

## 4. 核心系统

1. **插件 API**：`plugin/KubeJSPlugin.java`，约 40 个 default 钩子（`registerBuilderTypes/registerEvents/registerRecipeSchemas/registerTypeWrappers/attachPlayerData/generateData` 等）；`plugin/KubeJSPlugins.java` 扫描每个 mod jar 根的 `kubejs.plugins.txt`（一行 = `FQCN [client|必需modId...]`）、`kubejs.classfilter.txt`、bindings。
2. **脚本运行时**：`script/ScriptManager.java`（注释即流程：`unload()` → `loadFromDirectory()` → `load(long)` 建 `KubeJSContextFactory`、注册 type wrapper、按优先级求值）；`ScriptType.STARTUP/SERVER/CLIENT`、`KubeJSBackgroundThread`、`KubeJSFileWatcherThread`（热重载）、`ConsoleJS` 错误上报。
3. **注入式 API**：152 个 `core/*KJS` 接口（`ItemStackKJS`、`EntityKJS`…）由 `core/mixin` 82 个 Mixin 以 `@Mixin(原版类) @RemapPrefixForJS("kjs$") class X implements XKJS` 实现；接口注入清单走 `build.gradle.kts` 的 `interfaceInjectionData.from("interfaces.json")`（本副本缺该文件）。
4. **自研事件总线**：`event/KubeEvent|EventGroup|EventHandler|TargetedEventHandler|EventGroupRegistry`，脚本侧 `StartupEvents.REGISTRY`、`event.recipes.*`。
5. **配方系统**：`recipe/KubeRecipe` + `recipe/schema`（`RecipeSchema/RecipeSchemaRegistry/KubeRecipeFactory`）+ `recipe/component`（`RecipeComponent`）+ `filter/`、`viewer/`、`ingredientaction/`；钩子 `beforeRecipeLoading(RecipesKubeEvent, Map<Identifier, JsonElement>)` 可直接改原始配方 JSON。
6. **本地 Web 服务**：`web/LocalWebServer.java`（tiny-java-server）、`LocalWebServerRegistry/APIRegistry`、`KJSHTTPRequest/KJSWSSession`，脚本重载经 `KubeJSWeb.broadcastUpdate` 推送。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络：`net/KubeJSNet.java`（接口 + `@EventBusSubscriber`），`RegisterPayloadHandlersEvent` 的 `event.registrar("1").optional()` 注册 19 个 `CustomPacketPayload`（`STREAM_CODEC`）双向收发；`safeSendToPlayer` 在 `CommonProperties.serverOnly` 时直接 return。数据驱动：`KubeJSPaths.DATA/ASSETS` 当 datapack/resourcepack（`KubeFileResourcePack`），`generator/KubeDataGenerator`、`generator/KubeAssetGenerator` 供插件 datagen，`server/DataExport` 导出 `local/kubejs/export/`。配置为五个 JSON（common/client/dev/web_server）。脚本安全靠 `kubejs.classfilter.txt`（`+`/`-` 行）与 `plugin/ClassFilter`。

## 6. Mixin

`src/main/resources/kubejs.mixins.json`：package `dev.latvian.mods.kubejs.core.mixin`、plugin `KubeJSMixinPlugin`、JAVA_25、约 72 common + 14 client、`defaultRequire=1`。代表：`core/mixin/ItemStackMixin`（`@Mixin(ItemStack.class)`，shadow `components`，`@HideFromJS` 屏蔽原版方法）、`RecipeManagerMixin`、`SimpleJsonResourceReloadListenerMixin`（接管数据包加载）、client `mod.REITooltipMixin`。`KubeJSMixinPlugin.shouldApplyMixin` 用 `FMLLoader...getModFileById` 判断 `modnametooltip`/`roughlyenoughitems` 是否加载后再决定应用。

## 7. 值得学的 5 条做法

1. jar 内 txt 做插件发现（`plugin/KubeJSPlugins.loadFromFile`）：无服务加载器、无注解扫描，行内可写 `client` 与必需 modId 过滤，加载失败只记日志。
2. mixin 实现接口 + `@RemapPrefixForJS`（`core/mixin/ItemStackMixin.java`）：API 方法统一 `kjs$` 前缀，避免与原版方法撞名。
3. 自定义事件总线（`event/EventGroup`）：KubeEvent 携带脚本上下文、可 `EventExit` 提前退出，同一事件同时服务脚本与 Java。
4. 在 `RegisterEvent` 内先跑脚本再 build（`registry/RegistryEventHandler.handleRegistryEvent`），把脚本内容并入原版注册流程。
5. 可选兼容只落在 mixin 配置插件 + payload `.optional()`（`KubeJSMixinPlugin`、`net/KubeJSNet.java`），缺依赖即跳过，不硬崩。

## 8. 公开 API（库模组）

扩展点：`dev.latvian.mods.kubejs.plugin.KubeJSPlugin`（唯一入口）、`plugin.ClassFilter`、`recipe.component.RecipeComponent`、`recipe.schema.RecipeSchema`/`KubeRecipeFactory`、`script.BindingRegistry/TypeWrapperRegistry/TypeDescriptionRegistry/RecordDefaultsRegistry`、`registry.BuilderTypeRegistry`、`registry.ServerRegistryRegistry`、`event.EventGroupRegistry`。
外部接入：在自己 mod 的 `resources/kubejs.plugins.txt` 写实现类 FQCN（可加 `client`/modId 后缀），可选 `kubejs.classfilter.txt` 与 bindings 资源。
