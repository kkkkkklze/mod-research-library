# Sinytra/Connector 源码分析报告

> 说明：本报告基于本地克隆的分支 `26.1.x`（最后提交 2026-09-01，`67b3cc5`），目标 MC 26.1.2 / NeoForge 26.1.2，**不是** 1.20.1/1.21.1 版本；架构分层在旧版本（如 1.20.1 的 1.x 线）基本一致，但类名与 SPI 名称会随 NeoForge API 变化。

## 1. 基本信息

- Mod 名：Sinytra Connector；mod_id：`connector`；作者：Su5eD / Sinytra；许可证 MIT（`src/mod/resources/META-INF/neoforge.mods.toml`）。
- 版本：`versionConnector=3.0.0-beta.6`（`gradle.properties`），最终 `version = "$versionConnector+$versionMc"`，非发布构建追加 `dev-<git hash>`（`build.gradle.kts:37`）。
- 目标：MC `26.1.2`、NeoForge `26.1.2.100`（`gradle/libs.versions.toml`）；mods.toml 依赖 `neoforge [26.1,26.2)`、`launchpad [1.9.0,)` 必选，`connectorextras` 可选；Java 25。
- Gradle 插件：`net.neoforged.moddev` 2.0.141、`com.gradleup.shadow` 9.4.2、`me.modmuss50.mod-publish-plugin`、`net.neoforged.gradleutils`、`org.moddedmc.wiki.toolkit`；根项目 `include("transformer")`。
- 关键依赖（谁是它的 API）：`org.sinytra.adapter:core` 2.0.54（Mixin 补丁引擎，Connector 的核心算法来自 Adapter）、`org.sinytra.launchpad:launchpad` 1.9.1（把 Fabric mod 包装成 `IModFile`，`FabricModFactory`）、`org.sinytra:AutoRenamingTool` 2.0.23、`net.fabricmc:class-tweaker` 0.3.0-beta.2、`org.sinytra:forgified-fabric-loader` 2.5.85；jarJar 内嵌 `adapter:runtime` 与 shadow 后的 `:transformer`。
- 定位：前置/兼容层（不是普通内容 mod），全部工作在**启动早期**完成。

## 2. 源码规模与包结构

实测：89 个 `.java`，6598 行。三个 source root：

- `src/main/java/org/sinytra/connector`（18 文件）：`locator`(4) `locator/filter`(2) `service`(3) `service/coremod`(3) `util`(4) `api`(1) — 启动期发现/装配逻辑。
- `src/mod/java/org/sinytra/connector/mod`（25 文件）：`mixin/registries`(6) `mixin/client`(5) `mixin`(4) `mixin/network`(2) `mixin/item`(2) `compat`(3) — 真正的 `@Mod` 与 mixin。
- `transformer/`（46 文件）：`transform`(9) `patch`(7) `jar`(7) `api`(6) `plugin`(5) `runner/*`(9，独立 CLI 入口) — 可单独运行的字节码转换器。

最大文件：`ConnectorLocator.java` 357、`ConnectorModFileReader.java` 246、`TransformerUtil.java` 235、`SplitPackageMerger.java` 225、`ModuleLayerMigrator.java` 205、`MixinPatchTransformer.java` 195、`JarTransformer.java` 193、`MetadataReader.java` 167。

## 3. 入口与注册

没有单一主类，而是**用 NeoForge 的启动 SPI 多点接入**（`git ls-files` 可见 `src/main/resources/META-INF/services/` 下 5 个服务文件：`IModLanguageLoader`、`IDependencyLocator`、`IModFileCandidateLocator`、`IModFileReader`、`ClassProcessor`；这些文件在本次克隆的工作区被裁剪，仅有索引记录）：

- `ConnectorLocator`（`IDependencyLocator`，priority `LOWEST_SYSTEM_PRIORITY`）：`scanMods` 里 `PluginManager.initialize()` → 收集 Fabric mod → `JarTransformer.transform` → `pipeline.addModFile`，异常统一包装成 `ModLoadingException`。
- `ConnectorModFileReader`（`IModFileReader`，priority 500，早于 Launchpad）：构造器里做 `injectLogMarkers()` / `CrashReportHeader` / `ConnectorForkJoinThreadFactory.install()` / `new MixinFacade()`，并 `FabricLoaderImpl.INSTANCE.ignoreMods(hiddenMods)`、`aliasMods(globalModAliases)`。
- `ModuleLayerMigrator`（`IModFileCandidateLocator`）：把 brigadier、authlib 从 JDK 类加载器里"搬"进模块层。
- `ConnectorPrelaunch`（`IModLanguageLoader`）：用 `version()` 只在加载器取版本时触发 `MixinTransformSafeguard.trigger()` 与 `finalizeCache()`（懒触发技巧）。
- 内容侧 `ConnectorMod`（`src/mod/.../ConnectorMod.java`）：空构造器，只提供被字节码注入的静态方法 `getModResourceAsStream` / `useModConfigResource`。

## 4. 核心系统

1. **Jar 转换流水线**（`transformer/.../jar/JarTransformer.java`）：缓存优先（`jar.cacheFile().isUpToDate()`），只对改动过的 jar 走 `transformJars`；`Executors.newFixedThreadPool(paths.size())` 多线程 + `awaitTermination(1, HOURS)`；类查找用 `TransformerBytecodeProvider` 包一层 `ClassProvider`。
2. **Mixin 补丁引擎**（`transformer/.../transform/MixinPatchTransformer.java`）：构造函数里构造两套东西 —— 对所有类生效的 `classTransforms = [EnvironmentStripperTransformer(envType), FieldTypeUsageTransformer]`，以及只对 mixin 生效的 `Patcher.builder(...).classTransformers(DynamicPatches.CLASS_PATCHES).methodTransformers(DynamicPatches.methodTransformers(patches))`；`finalize` 阶段还会把运行时生成的 mixin 类注册进 mixin config 的 `package`。
3. **split package 合并**（`locator/filter/SplitPackageMerger.java`）：用 `JarModuleInfo.scanModulePackages(jar)` 扫包，`Map<String, List<Pair<JarContents, SplitInputPath>>> pkgSources` 找冲突，`BASE_FILTER = path -> !path.startsWith("META-INF/versions")` 排除版本化目录，再把冲突 jar 合并/挑选归属。
4. **插件 SPI**（`transformer/.../api/*` + `plugin/PluginManager.java`）：`TransformerPlugin`（`name/registerPatches/registerJarTransformers`）通过 `ServiceLoader` 发现；`TransformerRegistrar` 支持 `EARLY/DEFAULT/LATE` 排序提示与 `runsBefore/runsAfter` 依赖；`PatchRegistrar` 提供 `HIGHEST_SYSTEM_PRIORITY=1000 … LOWEST_SYSTEM_PRIORITY=-1000` 五档优先级。
5. **自定义配置**（`util/ConnectorConfig.java`）：`connector.json` 用 Mojang DFU `Codec` + `RecordCodecBuilder` 解析，字段 `version/hiddenMods/globalModAliases/enableMixinSafeguard`；`version` 用 `comapFlatMap` 只接受 1；单值/列表兼容用 `Codec.either`。
6. **失败保护**（`locator/MixinTransformSafeguard.java`）：把 `AuditTrail.getFailingMixins()` 收集成一次性的启动错误弹窗（`prepare`/`trigger` 两阶段，靠 `ConnectorPrelaunch.version()` 触发），可用配置关闭。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自研网络包；`mixin/network/BundlerInfoMixin`、`StreamCodecMixin` 是修原版网络编解码兼容性。
- 配置：`connector.json`（见上），`TransformerUtil.getCachedPath(input, output, cacheVersion)` 做转换缓存；`ConnectorUtil.JAR_CACHE_VERSION` 生产环境用 jar `Implementation-Version` + dist，开发环境返回 `"__dev__"` 永远过期。
- 数据驱动：无；`ConnectorLocator` 只读 `fabric.mod.json`（`FabricModFileMetadata` / `MetadataReader`）。

## 6. Mixin

- 配置：`src/mod/resources/connector.mixins.json`（package `org.sinytra.connector.mod.mixin`，`compatibilityLevel: JAVA_25`，`injectors.defaultRequire: 1`，15 个 common + 5 个 client）。transformer 侧还有自己的 runner mixin 服务。
- 代表：
  - `registries/RegistryDataLoaderMixin`：`@Mixin(value = RegistryDataLoader.class, priority = 9999)`，注入 `<clinit>` 的 `TAIL`。
  - `registries/NetworkRegistryMixin`：`@Redirect(method = "register", at = @At(INVOKE, target = "Ljava/lang/String;equals(...)"))` 改 modid 匹配。
  - `CommonHooksMixin`：`@Inject(method = "onPlaceItemIntoWorld", at = @At(INVOKE, target = "Lnet/minecraft/world/item/ItemStack;copy()..."), cancellable = true)`。
  - `network/BundlerInfoMixin`：`@Mixin(targets = "net/minecraft/network/protocol/BundlerInfo$1")`（匿名内部类）。
  - `client/FullFaceCalculatorAccessor`：`@Mixin(targets = "net.neoforged.neoforge.client.model.ao.FullFaceCalculator")`。

## 7. 值得学的 5 条具体做法

1. **转换结果磁盘缓存 + 版本键**：`ConnectorUtil.JAR_CACHE_VERSION`（`util/ConnectorUtil.java:41`）+ `TransformerUtil.getCachedPath`，适合任何"启动期做重活"的 mod。
2. **把"能不能用"做成运行时探测而非硬依赖**：`ConnectorUtil.SHOULD_ENABLE` 用 `Class.forName(...)` + 调一次 `FabricModFactory.createModFile` 判可用性（`util/ConnectorUtil.java:56`），库模组做软兼容可照搬。
3. **懒触发的启动检查**：`ConnectorPrelaunch.version()` 里做事（`service/ConnectorPrelaunch.java:16`），把代价推迟到加载器真正需要该语言加载器时。
4. **共用父类做 mixin 冲突降级**：`MixinTransformSafeguard` 把审计结果汇总成一条可关闭的启动错误，而不是直接崩（`locator/MixinTransformSafeguard.java`）。
5. **把转换器拆成独立可运行子项目**：`transformer/` 有 `runner/src/.../runner/cli/Main.java`（picocli）与 `main-Class` 清单，脱离游戏也能跑转换与 `JarInspector` 探针，便于复现问题。

## 8. 对外扩展点（Connector 作为前置）

- SPI 接口包：`org.sinytra.connector.transformer.api`（`TransformerPlugin`、`TransformerRegistrar`、`PatchRegistrar`、`TransformerContext`、`TransformerIds`）；第三方通过 `META-INF/services/org.sinytra.connector.transformer.api.TransformerPlugin` 注册。
- 内建转换器 ID 常量：`TransformerIds.SIGNATURE_STRIPPER / MOD_METADATA / CLASS_ANALYSIS / METHOD_PATCHES / ACCESS_REDIRECT`。
- 运行时查询：`ConnectorEarlyLoader.isConnectorMod(modid)` / `isConnectorModClass(Class)`，供其它 mod 判断"这个 mod 是 Fabric 转过来的"。
