# Cristelknight999/Cristel-Lib 源码分析报告

## 1. 基本信息
- Mod 名：Cristel Lib；mod_id `cristellib`；作者 Cristelknight；版本 3.1.11（`gradle.properties:6`）
- 目标 MC / 加载器：**MC 26.1.2**（`minecraft_version=26.1.2`，`minecraft_versions=26.1, 26.1.1, 26.1.2`），Java 25；Fabric（fabric_api 0.151.0+26.1.2，loader 0.19.3，quilt_loader 0.30.0-beta.8）+ NeoForge（26.1.2.76，`neo_forge_version=26.1.2-1`）
- Gradle：`net.neoforged.moddev` + 自带 `buildSrc/src/main/groovy/multiloader-common.gradle` / `multiloader-loader.gradle`（common 产物以 `commonJava`/`commonResources` configuration 暴露给 loader 子项目）；无 fabric-loom
- 许可证：**CC-BY-NC-ND-4.0**（`gradle.properties:44`；注意文件里注释指向 by-nc-sa 链接，字段值才是准的）
- 编译依赖（`common/build.gradle`）：`mixinextras-common 0.5.4`、`jankson 1.2.3`（JSON5）、cloth-config 26.1.154（可选 UI）、modmenu 18.0.0-beta.1；均为 `compileOnly`（不打包，运行期软依赖）
- 定位：**结构（structure set）配置 + 运行时数据包的前置库**；`neoforge.mods.toml` 用 `displayTest="IGNORE_ALL_VERSION"`

## 2. 源码规模与包结构
- 84 个 `.java`，共 5737 行
- 主要包（文件数）：`builtinpacks`(6)、根包 `de.cristelknight.cristellib`(6)、`util`(5)、`util/jankson`(4)、`data/condition{,/conditions}`(3+4)、`data/codec`(3)、`config/structure/toggle`(3)、`config/simple{,/custom}`(3+2)、`config/client/structure`(3)、`config`(3)、`autoconfig`(3)、`api`(3)、`platform/services`(2)、`config/client/extension/*`(2+2)、`data`(2)、`util/runtimepack`(2)
- 最大文件：`util/jankson/JanksonOps.java`(452)、`builtinpacks/RuntimePack.java`(379)、`config/client/extension/extensions/StructureConfigExtension.java`(293)、`StructureConfig.java`(216)、`builtinpacks/BuiltInPackLoader.java`(181)、`neoforge/.../NeoForgePlatformHelper.java`(175)、`client/simple/custom/SimpleScreenTypes.java`(149)、`config/FileWriter.java`(147)、`data/ReadData.java`(135)

## 3. 入口与注册
- `CristelLib.java` 两阶段初始化：`preInit()`(Stage 1，`:42`) 做 `DataFixer.registerFixer()`、`ConditionRegistry.init()`、把 API 收集的配置快照成 `ImmutableMap`（`CristelLibRegistry.configs = ImmutableMap.copyOf(getConfigs())`）、`BuiltInPackLoader.freeze()`、`BuiltInPackConfig.update()`、并逐个 `c.writeConfig(false)`；`init()`(Stage 2，`:37`) 只做 `StructureConfig.addSetsToRuntimePack(CristelLibRegistry.getConfigs())`
- 平台壳：NeoForge `neoforge/.../CristelLibNeoForge.java` `@Mod` 构造里 `preInit(); init();`，并监听 `AddPackFindersEvent` 调 `BuiltInPackLoader.registerEachPackAsSource(event.getPackType(), event::addRepositorySource)`（注释明说"一个 pack 一个 source，避免 NeoForge 按 source 字母序排序"）；Fabric `fabric/.../CristelLibFabric.java` 的 `onInitialize()` 只调 `init()`，`preInit()` 由 `fabric/.../mixin/BootstrapMixin.java` 注入 `Bootstrap.bootStrap@TAIL` 提前触发（需在 mod 初始化前就绪），并在开发环境注册 `/dump_runtime_pack` 命令
- 客户端：`neoforge/.../client/CristelLibNeoForgeClient.java` 用 `ModLoadingContext.registerExtensionPoint(IConfigScreenFactory.class, ...)` 挂 `ScreenBuilder`，并在 `FMLLoadCompleteEvent` 里为其它 mod 补挂配置屏
- 注册框架：**无 DeferredRegister**；用 *ServiceLoader*（`platform/Services.java` 的 `Services.load(IPlatformHelper.class)`，实现类由 `META-INF/services` 声明）+ 自有注册表 `ConfigRegistry`、`ConditionRegistry`、`ExtensionRegistry`

## 4. 核心系统
1. **StructureConfig（结构集配置）**：`StructureConfig.java:20` 用 `RecordCodecBuilder` 描述（`name/path/header/config_type/comments/structure_sets`），按 `config_type` 反序列化成 `StructureConfigToggle` 或 `StructureConfigPlacement`；核心流程 `addSetsToRuntimePack`→`applyToRuntimePack`→`addChanges(modId, setLocation)`，只有"与默认不同"的 set 才写进运行时包，其余 `CristelLib.CONFIG_PACK.removeStructureSet(...)`（`:72-85`）；`setDefaultNamespace()` 按出现次数最多的 namespace 自动补全 ID（`:183`）；容错 `checkForError()` 把坏配置改名 `xxx-had-error` 后重建（`:98-118`）
2. **RuntimePack（运行时数据包）**：`builtinpacks/RuntimePack.java` 是内存实现 `PackResources`，内部 `Map<Identifier, Supplier<byte[]>> data/assets` + `Map<List<String>, Supplier<byte[]>> root` + `ReentrantLock`（`:36-40`），支持 `dumpToFolder` 导出；`BuiltInPackLoader` 负责 freeze 与打包成 source
3. **API 与插件发现（跨平台差异最大处）**：接口 `api/CristelLibAPI.java`（`registerConfigs(Set<StructureConfig>)`、`registerStructureSets(CristelLibRegistry)`、`registerBuiltInPacks()`）+ 标记注解 `api/CristelPlugin.java`；Fabric 走 entrypoint：`FabricPlatformHelper.getApis()` 用 `FabricLoader.getInstance().getEntrypointContainers("cristellib", CristelLibAPI.class)`（`FabricPlatformHelper.java:106`）；NeoForge 走 ASM 扫描：`extraapiutil/APIFinder.scanForAPIs(CristelPlugin.class, CristelLibAPI.class)`，遍历 `ModList.get().getAllScanData()` 的注解并按 `Type.getType(annotationClazz)` 过滤后反射 `getDeclaredConstructor().newInstance()`；`CristelLib.readAPI` 对每个 API 用 try/catch 隔离坏实现（`CristelLib.java:66-77`）
4. **simple 配置体系**：`config/simple/ConfigRegistry.register(Class<T>, ConfigSettings<T>)`（`ConcurrentHashMap<Class<?>, ConfigHolder<?>>`）+ `registerWithScreen(...)`（仅当 `Services.PLATFORM.isClient() && Util.isClothConfigLoaded()` 才注册 Cloth 屏）；配套 `config/client/simple/custom/{ConfigFieldFactory,SimpleScreenTypes}`、颜色控件 `ColorField/AlphaColorField`、版本迁移 `config/simple/datafixer/DataFixer`；JSON5 读写靠 `util/jankson/{JanksonOps,Comments,CommentsMap,CommentArray}` 保留注释
5. **数据条件（数据驱动开关）**：`data/condition/ICondition` + `ConditionRegistry`（`ConcurrentMap<String, Codec<? extends ICondition<?>>>`，注释明确说明"本可用 Registry，但要处理 NeoForge 的麻烦事"）；内置条件 `mod_loaded`/`or`/`not`/`config_value`（`ConditionRegistry.init()`）；开关链路 `StructureConfigToggle`→`config/structure/toggle/{ToggleConfig,NestedToggleConfig,ToggleConfigTransformer}`、放置链路 `config/structure/placement/PlacementConfig`
6. **自动配置生成（autoconfig）**：`autoconfig/{ModFinder,ACConfig,ACInfoData}` + `data/ReadData` + `data/PathFinder` + `util/Util.readData(...)`，扫描所有已加载 mod 的 data 文件，为没写 API 的 mod 自动生成结构配置文件（`Util.java:43-60`，`ACConfig.update()`）
7. **客户端配置界面**：`config/client/ScreenBuilder` + `config/client/extension/{ConfigScreenExtension,ExtensionRegistry}` + `extensions/{SimpleConfigExtension,StructureConfigExtension}` + `config/client/structure/{ClientStructureConfig,ClientPlacementConfig,ClientEDConfig}`

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无**（未见任何网络包/包注册类）
- 数据驱动：核心卖点。① 运行时数据包 `RuntimePack` 动态生成/覆盖 `structure_set` JSON（`StructureConfig.getStructureSet`）；② 内置包 `BuiltInPackConfig`/`OverlayPack`/`BuiltinResourcePackSource` 注入资源包选择界面；③ `cristellib` 自己的 JSON5 配置（`config/cristellib/`，`ConfigManager.CONFIG_DIR.resolve("cristellib")`）；④ 条件系统 `ICondition`/`ConditionRegistry`
- 配置：`config/FileWriter`（写带注释 JSON5）、`config/ConfigManager`（`createToggleConfig/readToggleConfig/createPlacementConfig/readPlacementConfig`，全部基于 Codec + Jankson）；目录迁移逻辑在 `Util.updateOldFiles()`（把旧 `config/cristellib/data/` 改名 `~OUTDATED DIRECTORY~ data`）
- datagen：无（配置全部运行期生成，另提供 `/dump_runtime_pack` 便于开发环境导出）

## 6. Mixin
- 配置：`common/src/main/resources/cristellib.mixins.json`（client：`PackSelectionScreenMixin`）、`fabric/src/main/resources/cristellib.fabric.mixins.json`（`BootstrapMixin`、`ResourceLoaderImplMixin`）、`neoforge/src/main/resources/cristellib.neoforge.mixins.json`（`JarContentsPackResourcesAccessor`）；全部用 `"compatibilityLevel": "${java}"` 由 Gradle `processResources` 展开（`multiloader-common.gradle` 的 `filesMatching(['*.mixins.json'])`）
- 代表性 hook：
  - `common/.../mixin/PackSelectionScreenMixin.java`：`@Mixin(PackSelectionModel.class)`，`@Shadow @Final List<Pack> selected/unselected`，`findNewPacks@TAIL` 中按 `pack.location().source() instanceof BuiltinResourcePackSource` 移除（受 `ConfigRegistry.get(BuiltInPackConfig.class).hideAllPacksInScreen()` 控制）
  - `fabric/.../mixin/BootstrapMixin.java`：`Bootstrap.bootStrap@TAIL` 触发 `CristelLib.preInit()`
  - `fabric/.../mixin/ResourceLoaderImplMixin.java`：`ResourceLoaderImpl.registerBuiltinResourcePacks@TAIL` 里补注册 `BuiltInPackLoader.getPacks(consumer, type)`
  - `neoforge/.../mixin/JarContentsPackResourcesAccessor.java`：纯 `@Accessor("prefix"/"contents")` 拿 NeoForge 内部 `JarContents`

## 7. 值得学的 5 条具体做法
1. 双阶段初始化（Stage1 收集/冻结 + Stage2 应用，`CristelLib.preInit()`/`init()`）—— 需要"一定要早于其它 mod 初始化"的库必备；Fabric 侧用 `Bootstrap.bootStrap@TAIL` mixin 抢到最早期（`fabric/.../mixin/BootstrapMixin.java`）。
2. 用 ServiceLoader + 平台 helper 接口把 loader 差异做成一个文件一个实现（`common/.../platform/Services.java`，`META-INF/services` 声明 `IPlatformHelper`/`IModLoadingUtil`）—— 多 loader 库通用骨架。
3. 同一扩展接口按平台用不同发现机制：Fabric 用 entrypoint，NeoForge 用 ASM 注解扫描（`extraapiutil/APIFinder.java` 过滤 `ModFileScanData` 注解 + 反射实例化）—— 想给下游提供"零注册"插件入口时直接照抄。
4. 运行时内存 pack 实现 `PackResources`（`builtinpacks/RuntimePack.java`）来动态覆盖原版 `structure_set` JSON，而不是用 mixin 改结构生成 —— 数据驱动 + 兼容性最好的组合。
5. 所有动态配置都给"自愈"通道：`StructureConfig.checkForError()` 发现配置缺 key 就重命名 `-had-error`、重置并重写（`StructureConfig.java:98-118`），加 `config/simple/datafixer/DataFixer` 做老版本迁移 —— 面向玩家手改文件的 config 必须做的容错。

## 8. 公开 API / 扩展点（库/前置 mod）
- API 包：`de.cristelknight.cristellib.api`（3 个文件：`CristelLibAPI`、`CristelPlugin`、`BuiltInAPI`）
- 扩展点接口 `CristelLibAPI`（`api/CristelLibAPI.java`）：三个 default 方法 —— `registerConfigs(Set<StructureConfig>)`（提供自己的配置对象）、`registerStructureSets(CristelLibRegistry)`（把 structure set 绑到配置）、`registerBuiltInPacks()`；`BuiltInAPI`（`@CristelPlugin`）是官方自用示例，注册了 `vanilla_structures` 的 toggle/placement 两个配置（`BuiltInAPI.java:16-17`）
- 注册辅助：`CristelLibRegistry.registerSetToConfig(modId, namespace, List<String> sets, StructureConfig...)` / `(modId, Identifier set, ...)`；`StructureConfig.createWithDefaultConfigPath(name, ConfigType)`（`StructureConfig.java:130-147`）；`config/ConfigType`（TOGGLE/PLACEMENT）
- 外部 mod 接入方式（两种，按加载器）：
  - Fabric：在 `fabric.mod.json` 里声明 `"entrypoints": { "cristellib": ["your.YourAPI"] }`
  - NeoForge：给实现类加 `@CristelPlugin`（`api/CristelPlugin.java`，`@Retention(RUNTIME) @Target(TYPE)`），由 `APIFinder` 扫描发现
  - 简单配置（非结构类）：`config/simple/ConfigRegistry.register(YourConfig.class, ConfigSettings)`，需要 UI 时 `registerWithScreen(clazz, spec, modId, screenName[, onScreenSave])`（依赖 Cloth Config，仅客户端生效）
  - 自定义数据条件：`data/condition/ConditionRegistry.registerCondition(Identifier, Codec<? extends ICondition<?>>)`
