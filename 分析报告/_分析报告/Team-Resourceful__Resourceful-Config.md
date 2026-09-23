# Team-Resourceful/Resourceful-Config 源码分析报告

> 本报告基于本地克隆分支 `26.x`（最后提交 2026-09-04，`62c0f6c`），目标 MC 26.2 / NeoForge 26.2.0.0-beta / Fabric API 0.152.1+26.2，Java 25。它是**库/前置类** mod（配置库），第 8 节按模板要求展开。

## 1. 基本信息

- Mod 名：ResourcefulConfig；mod_id：`resourcefulconfig`；作者：Team Resourceful；许可证 MIT（`build.gradle.kts` 的 `GitHubPom(..., "MIT", ...)`、`neoforge.mods.toml` 的 `license = "MIT"`）。
- 版本：`version.properties` → `version=5.0.0`（构建脚本用 `libs.versions.mod.version`，由 `com.teamresourceful.resourcefulsettings` 插件从该文件注入）；`version.properties` 里还有 `initialMCVersion=1.19.1`，而 `currentMCVersion=1.23` 与 `gradle/libs.versions.toml` 的 `minecraft = "26.2"` 不一致（遗留字段，实际编译版本以 toml 为准）。
- 目标与构建：`gradle/libs.versions.toml` 中 `minecraft = "26.2"`、`neoforge = "26.2.0.0-beta"`、`fabric-api = "0.152.1+26.2"`、`modmenu = "20.0.0-beta.2"`（仅 Fabric 侧 compileOnly）；`settings.gradle.kts` 里 `com.teamresourceful.resourcefulsettings` 0.0.6，root 用 `com.teamresourceful.resourcefulgradle` + `com.teamresourceful.plugins.minecraft` 2.0.0；子项目按 `getPlatform()` 分派 COMMON/FABRIC/NEOFORGE 预设。
- 编译期特殊机制：非 COMMON 平台加 `-Xplugin:ServicePlugin --service-plugin-platform=<platform> --service-plugin-platform-class=...common.utils.Platform`，注解处理器 `com.teamresourceful:resourceful-service-plugin` 1.0.0（用于生成/改写平台服务实现）。
- 模块：`common`（主体）、`fabric`（含 `demo` 示例）、`neoforge`。

## 2. 源码规模与包结构

实测：186 个 `.java`，12402 行。主体在 `common/src/main/java/com/teamresourceful/resourcefulconfig`：

- `api`：`annotations`(8) `types/info`(9) `types/options`(7) `types/entries`(7) `types/elements`(4) `client`(6) `loader`(2) `patching`(1) —— 对外 API 面。
- `client`：`components/options`(37) `components/base`(6) `screens/base`(3) `components/header`(3) `components/configs`(3) `components/categories`(2) `utils`(4) `UIConstants/ConfigScreen/ConfigsScreen/ListScreen`。
- `common`：`loader`(6 + `elements` 5 + `entries` 6) `compat/minecraft`(3) `jsonc`(4) `info`(5) `config`(2) `utils`(4)。
- `web`：`server`(1) + `server/paths`(4) `config/validators`(8) `info`(1) `utils`(2)。
- `mixins`：`client`(2) + `common`(2)。
- 最大文件：`client/components/options/text/TextBox.java` 377、`common/loader/JavaConfigParser.java` 292、`api/types/entries/ResourcefulConfigFieldBackedValueEntry.java` 254、`client/components/options/Options.java` 248、`common/loader/entries/ParsedObservableEntry.java` 226、`common/compat/minecraft/DedicatedServerConfigEntry.java` 215、`fabric/.../demo/DemoConfig.java` 210、`MultilineTextState` 204。

## 3. 入口与注册

- NeoForge：`neoforge/src/main/java/com/teamresourceful/resourcefulconfig/neoforge/ResourcefulConfigNeoForge.java`（37 行）——`@Mod("resourcefulconfig")` 构造器里 `WebServer.start()`，按 `FMLLoader.getCurrent().getDist()` 分派 `CompatabilityLayers.initServer()` / `ResourcefulConfigNeoForgeClient.onClientInit(container)`；`NeoForge.EVENT_BUS.addListener(ResourcefulConfigNeoForge::onServerStarted)` 里 `DedicatedServerInfo.setServer(event.getServer())`。
- Fabric：`fabric/.../common/fabric/ResourcefulConfigFabric.java`（`ModInitializer`，仅注册 `ServerLifecycleEvents.SERVER_STARTED`）。
- 没有 DeferredRegister/Registrate：**注册模型是"每 mod 一个 Configurator"**，`Configurator.register(Class<?> | ResourcefulConfig, Consumer<ConfigPatchEvent>)` 解析后写入全局 `Configurations.INSTANCE`（`common/config/Configurations.java`，两个 `ConcurrentHashMap`：`modToConfigs`、`configs`，`@ApiStatus.Internal`）。`Configurator` 构造时用 `ModUtils.isModLoaded(modid)` 校验 modid 并打印友好警告（`api/loader/Configurator.java:31`）。

## 4. 核心系统

1. **注解驱动的配置定义**：`@Config(value, version, categories)`、`@Category`、`@ConfigEntry(id, translation)`、`@ConfigObject`、`@ConfigInfo.Provider`，以及 `@ConfigOption.{Range,Slider,Multiline,Color,Regex,Separator,Hidden,Select,Draggable,Keybind,SearchTerm,Renderer}`（`api/annotations/*`）。真实用法见 `fabric/.../demo/DemoConfig.java`（`public static int demoSlider` + `@ConfigOption.Slider @ConfigOption.Range(min=0,max=10)`）。
2. **反射解析器链**：`ConfigParser` 是 `ServiceLoader` 扩展点（`PARSERS` 用 `Suppliers.memoize` 缓存并按 `priority()` 降序），`tryParse` 逐个尝试、全失败抛 `IllegalArgumentException`（`api/loader/ConfigParser.java`）；内建 `JavaConfigParser` 的 `priority()` 返回 `Integer.MIN_VALUE`（兜底）。它遍历 `clazz.getDeclaredFields()`，按 `EntryType` 分派到 `ParsedObjectEntry/ParsedListEntry/ParsedObservableEntry/ParsedInstanceEntry`，并递归处理 `@Config.categories()`。
3. **类型系统**：`EntryType` 枚举（BYTE/SHORT/INTEGER/LONG/FLOAT/DOUBLE/BOOLEAN/STRING/ENUM/OBJECT/LIST），每个常量持有一个 `Predicate<Class<?>>`；`isAllowedInArrays()`（LIST/OBJECT 不可）、`mustBeFinal()`（OBJECT/LIST 必须 final）（`api/types/options/EntryType.java`）。
4. **读写与 JSONC**：`Loader.loadConfig(config, JsonObject)` 递归把 JSON 灌进 entry（`convert()` 按 `EntryType` 把 `JsonPrimitive` 转 byte/short/int/…，数字统一经 `Number#xxxValue`；ENUM 走 `ParsingUtils.parseEnum`），`Writer.save(config)` 反向生成带注释的 `JsoncObject`，首行固定 `VERSION_KEY = "rconfig:version"`，注释文案来自 `@Comment`；`common/jsonc/{JsoncObject,JsoncArray,JsoncPrimitive,JsoncElement}` 是自研的"可带注释 JSON"树。
5. **版本迁移**：`ConfigPatchEvent.register(int version, UnaryOperator<JsonObject>)` 注册按版本的重写回调，另有便捷 `move(version, from, to)` 用点路径（`api/patching/ConfigPatchEvent.java`，内部专用 `getParent(json, path, create)`）。
6. **内嵌 Web 配置面板**：`web/server/WebServer.java` 用 JDK `com.sun.net.httpserver.HttpServer`（默认关闭），context 为 `/configs`、`/config`、`/save`（`web/server/paths/*`）；`WebServerConfig` 是 `RecordCodecBuilder` codec（`enabled`、`intRange(0,65535)` 的 `port`（默认 7903）、可选 `config_site`、`validator`），默认 `IfValidator + PasswordValidator(UUID)`；请求处理统一走 `BasePath.handle` → `WebServerUtils.handleCors` → `verifier().getInfo(exchange)`（JWT，`web/info/UserJwtPayload.java`），失败回 401/400。
7. **平台抽象（服务插件）**：`ModLoaderService` 接口（`getConfigPath/isDev/isModLoaded`）标注 `@PlatformService`，工厂 `static ModLoaderService create()` 源码里直接 `throw new AssertionError("Platform service not implemented")`，由编译期插件按 `--service-plugin-platform` 生成实现；Fabric/NeoForge 侧分别有 `ModLoaderServiceFabricImpl`、`ModLoaderServiceNeoForgeImpl`（命名约定，生成源码不在本仓库，**未确认**具体改写方式）。`Platform` 枚举用 `Class.forName("net.neoforged.fml.loading.FMLLoader")` 探测加载器。
8. **数据驱动附加层**：`common/compat/minecraft/DedicatedServerConfigEntry` + `DedicatedServerInfo` 让专用服务器把配置暴露给 Web 面板；`common/compat/CompatabilityLayers.initServer()` 在 NeoForge 专用服务端启用。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无自研网络包**（Web 面板走 HTTP/JWT，不走 Minecraft 网络栈）。
- 配置：本 mod 自身配置为 `config/resourceful-config-web.json`（`WebServer.loadConfig()`，手写 `Jsonc`/Codec 读写，不存在时写默认值）。
- 数据驱动：无 datapack/registry 加载；datagen：无（示例配置写在 `fabric` 的 `demo` 包）。

## 6. Mixin

配置：`common/src/main/resources/resourcefulconfig.mixins.json`（`required: true`、`compatibilityLevel: JAVA_17`、`injectors.defaultRequire: 1`）。

- 目标：`client.GuiMixin`（`@Mixin(Gui.class)` + `@Inject`）、`client.GuiGraphicsExtractorAccessor`（`@Accessor("guiRenderState")`）、`common.DedicatedServerAccessor`（`@Mixin(DedicatedServer.class)` + `@Accessor`）。
- 注意：同目录还有 `common/SettingsAccessor.java`（`@Mixin(Settings.class)`）但**未列在 mixins.json 的 mixins 数组中**（疑似遗漏或按需手工启用）。

## 7. 值得学的 5 条具体做法

1. **用 `ServiceLoader` 做解析器扩展点**：`ConfigParser.PARSERS` + `priority()` + `Suppliers.memoize`（`api/loader/ConfigParser.java:13`），第三方可替换/优先接管解析。
2. **带注释 JSON 的自研序列化树**：`common/jsonc/*` 与 `Writer` 分离"值结构"和"注释元数据"，生成的配置文件自带 `@Comment` 文案（适合做用户友好配置）。
3. **类型枚举自带判定谓词**：`EntryType` 把"Java 类型 → 配置类型"的映射写成 `Predicate`，`isAllowedInArrays()/mustBeFinal()` 把校验规则数据化，新增类型只改枚举。
4. **配置版本迁移 API 化**：`ConfigPatchEvent.register(version, UnaryOperator<JsonObject>)` + 点路径 `move`，让"改字段路径"无需手写迁移代码。
5. **平台差异放编译期**：`@PlatformService` + 注解处理器（`build.gradle.kts` 的 `-Xplugin:ServicePlugin`）避免运行期反射分支；仓库侧只留 impl 类。

## 8. 公开 API 与接入方式（库/前置）

- API 根包：`com.teamresourceful.resourcefulconfig.api.*`
  - 定义：`api.annotations.*`（`Config/Category/ConfigEntry/ConfigObject/ConfigInfo/ConfigButton/Comment/ConfigOption.*`）
  - 注册：`api.loader.Configurator`（`new Configurator(modid).register(MyConfig.class, patchHandler)`）、`api.loader.ConfigParser`（SPI）
  - 模型：`api.types.ResourcefulConfig`（`id()/version()/elements()/categories()/info()/save()/load(handler)`）、`ResourcefulConfigElement/Category/Button`、`api.types.entries.*`（含 `Observable<T>`、`SerializableObject`）、`api.types.options.EntryType/EntryData/Option`
  - 迁移：`api.patching.ConfigPatchEvent`
  - 客户端扩展：`api.client.{ResourcefulConfigScreen, ResourcefulConfigScreenBuilder, ResourcefulConfigUI, ResourcefulConfigElementRenderer, ModalWidgetConstructor, GenericModalOverlay}`、`api.client.options.ResourcefulConfigOptionUI`
  - 信息/展示：`api.types.info.{ResourcefulConfigInfo, ListEntryInfoProvider, TooltipProvider, ResourcefulConfigColor*, ResourcefulConfigLink, ResourcefulConfigInfoButton}`
- 外部模组接入流程：`@Config` 注解静态字段类 → 在 mod 初始化时 `Configurator.register()` → 文件读写/UI 由库负责；服务器端可通过 Web 面板（`config/resourceful-config-web.json` 开启）远程编辑。
