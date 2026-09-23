# fzzyhmstrs/fconfig（Fzzy Config）源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Fzzy Config / `fzzy_config`（`src/main/kotlin/me/fzzyhmstrs/fzzy_config/fzzy_config.kt:48`）
- 作者：fzzyhmstrs（Timefall Development）；homepage/issues 见 fabric.mod.json
- 许可证：Timefall Development Licence - Modified 1.3（TDL-M），源码每个文件头部带版权注释
- 版本与平台：`modVersion=0.7.6`、`minecraftVersion=26.2`、`loaderVersion=0.19.3`（fabric-loader）、`fabricVersion=0.152.1+26.2`、`mcVersions=26.2`（`gradle.properties`）；fabric.mod.json 声明 `minecraft >=26.1`、`java >=25`、`fabric-language-kotlin`
- 加载器/构建：本快照仅 Fabric 一侧——`net.fabricmc.fabric-loom`（1.16-SNAPSHOT）+ `kotlin("jvm") 2.3.21` + `kotlin("plugin.serialization")` + minotaur/cursegradle/dokka/moddedmc-wiki/maven-publish；Java 25 target，编译参数 `-Xjvm-default=all -jvm-default=enable`（`build.gradle.kts:139-142`）。README:55 说明同版本号另有 `+neoforge`/`+forge` 构建，即存在 Forge/NeoForge 分支，本仓库不包含
- 编译依赖：`tomlkt 0.3.7`（TOML 读写，JiJ）、`jankson 1.2.3`（JSON5，JiJ）、`me.lucko:fabric-permissions-api 0.7.0`（JiJ）、`kotlinx-serialization-json 1.6.3`、`compileOnly/runtimeOnly modmenu 20.0.0-alpha.1`
- 定位：库/前置 mod。外部接入方式为 maven `https://maven.fzzyhmstrs.me/`（README）

## 2. 源码规模与包结构

实测：`.kt` 270 个 / 50020 行（`src/main` 251 个 / 48270 行）；`.java` 仅 2 个（`src/testmod`，124 行，用于验证 Java 侧 API）。工作树中 `src/main/resources` 被快照剔除（`git ls-files` 中仍有 fabric.mod.json 与 assets/lang、textures）。

包（第 3 层，文件数）：`screen` 71（widget 21、context 12、internal 8、entry 7、decoration 6、widget/custom、widget/internal）、`util` 43（pos 10、function 6、platform 3+impl 5）、`validation` 35（misc 13、collection 8、number 7、minecraft 4）、`entry` 19、`networking` 16（api 7、impl 1）、`impl` 12、`event` 10（api 8、api/v2）、`config` 6、`api` 5、`updates` 5、`result` 9、`registry` 2、`annotations` 2、`examples` 15（构建时默认排除）。

最大文件：`util/Expression.kt` 2227（类 Brigadier 表达式的数值/条件表达式解析器）、`impl/ConfigApiImpl.kt` 1725、`screen/widget/DynamicListWidget.kt` 1540、`util/ValidationResult.kt` 1488、`screen/widget/LayoutWidget.kt` 1461、`validation/minecraft/ValidatedIdentifier.kt` 1256、`screen/widget/PopupWidget.kt` 1200、`validation/misc/ValidatedColor.kt` 1185、`validation/ValidatedField.kt` 990、`api/ConfigApi.kt` 772。

## 3. 入口与注册

```kotlin
// fzzy_config.kt:47
object FC: ModInitializer {
    internal const val MOD_ID = "fzzy_config"
    override fun onInitialize() { NetworkEvents.registerServer(); PlatformUtils.registerCommands() }
}
object FCC: ClientModInitializer { override fun onInitializeClient() { NetworkEventsClient.registerClient() } }  // :60
```
fabric.mod.json（从 git 读取，工作树缺失）：entrypoints `main→…FC`、`client→…FCC`、`modmenu→impl.ConfigModMenuCompat`；`custom.catalogue.configFactory`；`environment:"*"`。

本库不使用 DeferredRegister/Registrate（自身不注册游戏内容）。配置的"注册"= `ConfigApi.registerConfig / registerAndLoadConfig`（`api/ConfigApi.kt:76/120`）→ `impl/ConfigApiImpl.kt:157/181`，按 `RegisterType`（`api/RegisterType.kt:20`）分流到 `registry/SyncedConfigRegistry.kt:55` 与 `registry/ClientConfigRegistry.kt:50`。`util/platform/Registrar.kt:26` + `RegistryBuilder/RegistrySupplier` 提供了仿 NeoForge 的注册器抽象，供接入方跨平台使用。

## 4. 核心系统

1. 注解驱动配置 + 反射序列化（`impl/ConfigApiImpl.kt`）：`serializeToToml`（:449）以 `clazz.memberProperties.filter { it is KMutableProperty<*> && !isNonSync(it) && !isTransient(javaField) }` 收集字段，属性名即 TOML 键；行为由 **位掩码 flags** 控制（:100-113）：`IGNORE_NON_SYNC=1`、`CHECK_ACTIONS=2`、`IGNORE_VISIBILITY=4`、`RECORD_RESTARTS=8`、`FLAT_WALK=16`、`CRITICAL_ERRORS_ONLY=32`、`PROVIDE_UPDATE_TOML=64`。`deserializeFromToml`（:592）按"EntryDeserializer → 基础类型自动包装 → 原始字段"三分支回填，缺失键与文件里多余键都写成 `ValidationResult.Errors`（:685）。
2. 校验/纠正容器（`util/ValidationResult.kt`、`validation/ValidatedField.kt:79`）：不用异常，而是"值 + 错误树"单子（`Errors.*`、`attachTo/map/bimap/outmap`、`ErrorEntry.Mutable`）；`validateAndSet/validateEntry/correctEntry`（:247-360）实现越界自动纠正与 revert/skip 策略；35 个包装类（ValidatedDouble/Boolean/Identifier/List/Map/Choice/Expression/Keybind…）既是校验器又是 GUI 描述。
3. 客户端-服务端同步（`networking/`、`registry/SyncedConfigRegistry.kt`）：payload 均为"整份序列化字符串"，如 `ConfigSyncS2CCustomPayload`（:20，`buf.writeUtf(id)` + `writeUtf(config)`）；`NetworkEvents.registerServer()`（:58）挂在 Fabric 事件上——`ServerConfigurationConnectionEvents.CONFIGURE`（:71，非单人游戏时同步所有 SYNC 配置）、`ServerPlayConnectionEvents.JOIN`（:79，发 `ConfigPermissionsS2CCustomPayload` 权限报告）、`END_DATA_PACK_RELOAD`（:88，重发全部配置并 `invalidateLookup()`）、`SERVER_STARTED/STOPPING`（:97/102 线程池启停）。客户端改动经 `ConfigUpdateC2S`（`receiveUpdate` :34，带 `playerPerm` 与 `changeHistory`）与 `SettingForwardCustomPayload`（:46，玩家间转发）回传；`SyncedConfigRegistry` 用 `Object2ObjectLinkedOpenHashMap` 存放隔离更新 `QuarantinedUpdate`（:381）。
4. 权限（`impl/PermResult.kt`、`util/platform/impl/PlatformUtils.kt:67`）：默认 `Config.defaultPermLevel()=2`（`config/Config.kt:118`），注解 `@WithPerms(opLevel=3)`/`@WithCustomPerms`/`@AdminAccess`（`annotations/ConfigAnnotations.kt:94/121/139`）逐字段覆盖，底层走 fabric-permissions-api 的 `Permissions`。
5. 界面自动生成（`screen/`）：`ConfigScreenManager`（`screen/internal/ConfigScreenManager.kt:56`）以 scope 为单位构建屏幕，持有 `sidebar`、`screenCaches`、权限缓存（`cachedPerms/cachedPermKey`）、`screenLock: AtomicBoolean` 防重入，`provideScreen(scope)`（:95）支持 `scope.subscope` 下钻与 rootScope；布局由自研 `LayoutWidget`（1461 行）+ `DynamicListWidget`（1540 行）+ `PopupWidget` 承担；每行由 `screen/entry/ConfigEntry.kt:67` 组合 layout/decoration/action/context/search；`ConfigScreenProvider`（`api/ConfigApi.kt:298`）允许 mod 替换某 namespace 的整个屏幕。
6. 版本迁移与预设（`updates/`、`impl/`）：`@Version(n)` + `Config.update(deserializedVersion)`（`config/Config.kt:143`）做旧数据修正；`updates/UpdateManager.kt:17`（`companion object Base: BaseUpdateManager()`）记录 changeHistory/revert/restore，`BasicValidationProvider` 让普通字段也能被增量更新；`impl/ConfigPresetsLoader.kt:25` 是 `SinglePreparationResourceReloader` + `IdentifiableResourceReloadListener`，从资源包加载 ConfigPreset。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：7 个自建 payload（配置同步、权限、C2S 更新、S2C 更新、设置转发、动态 ID）；注册统一走 `ConfigApi.network()`（`networking/api/NetworkApi.kt`），其中 `registerLenientS2C/C2S`（:74/:83）为"对端未装 Fzzy Config 时不报错"的宽松注册——这是库模组的必要设计。
- 文件格式：`Config.fileType()` 默认 `FileType.TOML`（`config/Config.kt:128`、`api/FileType.kt:24`），编码分支见 `ConfigApiImpl.kt:359-424`（Toml/Json/Json5/Nbt）；`SaveType` 至少含 `OVERWRITE` 与 `SEPARATE`（`api/SaveType.kt:20`、`config/Config.kt:133`）。
- TOML 呈现：`annotations/JvmTomlAnnotations.kt` 的 `@Comment/@Inline/@BlockArray/@MultilineString/@LiteralString/@Integer` 控制输出样式；`@ConvertFrom`（`ConfigAnnotations.kt:343`）可把旧文件迁移为新配置。
- datagen：`ConfigApi.buildTranslations(kClass, id, lang, builder)`（`api/ConfigApi.kt:723`，实现 `ConfigApiImpl.kt:1108`，按声明顺序遍历字段）把 `@Translatable.Name/Desc/Prefix`（`util/Translatable.kt:453/473/477`）与 TOML 注释导出为 lang 条目；`serializeToToml/serializeConfig/deserializeConfig` 全部公开（`api/ConfigApi.kt:331-643`），可离线复用。
- Java 支持：`api/ConfigApiJava.kt:47` 提供 Supplier/Consumer/BiConsumer 版本，`src/testmod/java/...JavaTestConfig.java` 为验证样例。

## 6. Mixin

无。全仓库无 mixin 配置文件与 `@Mixin` 代码（`grep -rl "mixin" src/main/kotlin` 无命中），同步/事件全部依赖 Fabric API 事件与自定义 payload。

## 7. 值得学的 5 条做法

1. 用位掩码 flags 统一驱动序列化/反序列化/更新三种场景（`impl/ConfigApiImpl.kt:100-113`），避免多套遍历代码——适用于任何"同一数据多用途导出"的库。
2. 用 `ValidationResult<T>` 代替异常做输入校验，把"值 + 错误树 + 是否被纠正"一起返回（`util/ValidationResult.kt:1488` 行；`validation/ValidatedField.kt:247`）——配置/命令/网络参数校验通用。
3. 让"校验器"兼任"GUI 描述符"（`entry/Entry.kt:16` 继承 `EntryWidget/EntryHandler/EntryFlag/Consumer/Supplier`，`EntryCreator` 懒构建），界面生成因此零额外注册——写自带配置界面的模组可直接抄。
4. 反射按 `KMutableProperty` + `javaField` transient 过滤并保留声明顺序（`ConfigApiImpl.kt:607`、`:1117` 的 `orderById`），字段名即存储键，缺失键与遗留键都进错误报告并回写修复文件（`:685`、`readOrCreateAndValidate` :250）。
5. 同步放在 CONFIGURATION 阶段 + 数据包重载时重发（`networking/NetworkEvents.kt:71/88`），并用 lenient payload 注册兼容未安装本库的客户端（`NetworkApi.kt:74`）；跨端 UI 意图用 `@Volatile` 字段 + `withScope{ }` 消费而非全局单例（`fzzy_config.kt:62-86`）。
6. 文档随码：包内保留 `narration_map.md`（无障碍朗读映射）与 `screen/context/context_map.md`（屏幕上下文说明），大改 UI 时先读这两份材料。

## 8. 公开 API（库模组）

- 主入口：`api/ConfigApi.kt`（object，@JvmStatic/@JvmOverloads）、`api/ConfigApiJava.kt`；子 API 聚合方法 `ConfigApi.network()/platform()/event()/result()`（`api/ConfigApi.kt:734/746/758/770`）
- 扩展点接口：`screen/ConfigScreenProvider`（自定义屏幕）、`entry/Entry` 及其 19 个 `Entry*` 接口（EntryWidget/EntryDeserializer/EntryValidator/EntryKeyed…）、`updates/UpdateManager`、`event/api/EventApi`（onSyncClient/onSyncServer/onUpdateClient/onUpdateServer(v2)/onRegistered*）、`result/api/ResultApi`（ResultProvider 动态注册表 ID）、`networking/api/NetworkApi`、`util/platform/Registrar`+`RegistryBuilder`+`RegistrySupplier`（仿 NeoForge 注册器）、`screen/decoration` 与 `screen/widget/custom`（自定义控件/装饰）
- 外部接入：`class MyConfig: Config(Identifier.fromNamespaceAndPath(MODID,"my_config"))` + 公开 `var` 字段（裸字段或 Validated ×），启动处 `ConfigApi.registerAndLoadConfig { MyConfig() }`（样例 `examples/MyConfig.kt:26-39`、`examples/ConfigRegistration.kt`）
- 未确认：本快照资源目录缺失，`assets/fzzy_config/lang/*.json` 与贴图未做内容核对；Forge/NeoForge 分支的实现方式未在本次范围内。
