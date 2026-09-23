# CustomSkinLoader (MCCustomSkinLoader) 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | CustomSkinLoader / `customskinloader` |
| 作者 | xfl03、JLChnToZ、ZekerZhayard |
| 目标 MC / 加载器 | **跨版本通用**：`Common/src/main/resources/META-INF/mods.toml` 声明 `minecraft [1.13.2,)` side=CLIENT、forge `[25,)` optional；`neoforge.mods.toml` 声明 neoforge `[20.5,)`；README 列出 1.8–1.21。一个 bootstrap jar 适配 Forge legacy / Forge ModLauncher / NeoForge / Fabric |
| Gradle | 自研 `buildSrc` 插件（`buildSrc/src/main/java/customskinloader/gradle/ManifestLibrariesPlugin.java`，apply 了 `customskinloader.manifest-libraries`）；Java 8 目标（`build.gradle:81`），`Common` 额外有 java21 sourceSet 覆盖 |
| 许可证 | GPL-3.0-only（`mods.toml`） |
| 编译依赖 | 无 Minecraft / 加载器依赖。`Dummy/` 模块只是**编译期桩类**（`Dummy/Common/src/main/java/net/minecraft/...`、`Dummy/Bootstrap/.../cpw/mods/modlauncher/api/TargetType.java`），真实类运行期由 bootstrap 从运行时 jar 中取 |

## 2. 源码规模与包结构

- 共 **113 个 `.java`，8906 行**（`find . -name '*.java' -not -path '*/build/*' -exec wc -l {} +`）。
- Gradle 多模块（`settings.gradle`）：`Bootstrap:{Core,FabricV1,ForgeV1,ForgeV2,NeoForgeV1,NeoForgeV2}`、`Common`、`Dummy:{Bootstrap,Common}`，另有 `buildSrc`。
- 文件数分布：`Bootstrap/Core` 24、`Common` 47（+`src/main/java21` 1）、`Dummy/Common` 23、各加载器 bootstrap 1-4、`buildSrc` 3。
- `Common` 内包：`customskinloader`（主类 236 行）、`config`(2)、`fake`+`fake/itf`+`fake/texture`(13)、`loader`+`loader/jsonapi`(9)、`log`(2)、`mod/{forge,neoforge}`(2)、`plugin`(2)、`profile`(3)、`utils`(11)。
- 最大文件：`Bootstrap/Core/.../transformer/patch/SkinManagerPatch.java` 523、`.../installer/BytecodeRemapper.java` 411、`buildSrc/.../ManifestLibrariesExtension.java` 295、`Common/.../utils/HttpRequestUtil.java` 284、`.../mapping/Mappings.java` 262、`Common/.../config/Config.java` 258。

## 3. 入口与注册

架构是"**bootstrap 先跑 → 运行期生成并加载 Common jar**"（README 明确说明），没有传统 `@Mod` 主类注册表：

- 主类 `Common/src/main/java/customskinloader/CustomSkinLoader.java:33`，全部静态初始化：`DATA_DIR = <mc>/CustomSkinLoader`、`GSON`、`logger`、`config`、`THREAD_POOL` / `PROFILE_THREAD_POOL`（线程池大小由 `config.threadPoolSize * loadlist.size()` 决定）。
- 加载器侧入口（各自独立子模块，互不依赖）：
  - Fabric：`Bootstrap/FabricV1/.../MixinConfigPlugin.java` 实现 `IMixinConfigPlugin`，在 `onLoad` 调 `TransformerBootstrap.initialize()`，在 **`postApply`** 中调 `TransformerBootstrap.transformTargetClass(...)` 拿到 Mixin 处理后的 `ClassNode` 再二次改写；mixin 配置用空 `DummyMixin` 占位（`customskinloader.bootstrap.fabric.v1.mixins.json`）。
  - Forge legacy：`Bootstrap/ForgeV1/.../LoadingPlugin.java:10` 实现 `IFMLLoadingPlugin`，`getASMTransformerClass()` 返回 `ClassTransformerAdapter`。
  - Forge ModLauncher：`Bootstrap/ForgeV2/.../TransformationService.java`。
  - NeoForge 新版：`Bootstrap/NeoForgeV2/.../ClassProcessorProviderImpl.java` 实现 `net.neoforged.neoforgespi.transformation.ClassProcessorProvider`，`createProcessors` 里 `collector.add(TransformerBootstrap.createProcessor())`。
  - 加载器名/版本通过系统属性回传给 Common：`Bootstrap/Core/.../ModLoaderInfo.java` 写入 `customskinloader.modLoader.name/version`，`Common/utils/MinecraftUtil.java:64` 读取。
- 无 DeferredRegister；插件注册走 `ServiceLoader` + 目录扫描（见第 8 节）。

## 4. 核心系统

1. **运行期字节码转换引擎** `Bootstrap/Core/src/main/java/customskinloader/bootstrap/transformer/`：`TransformerBootstrapSupport.ensureTransformersLoaded()` 用 `ServiceLoader<TargetedClassTransformer>`（锚点 `serviceLoaderAnchor.getClassLoader()`）懒加载平台提供的 transformer 并注册进 `ClassTransformerRegistry`；`transformClassNode(internalClassName, ClassNode)` 构造 `ClassTransformationContext` 后交给 `RuntimeClassTransformerEngine`。ASM 用 `ClassNode` 树 API（`toClassNode` / `toByteArray(COMPUTE_MAXS)` / `copyClassNode` 反射复制全部非静态字段）。
2. **原始/目标双命名空间映射** `Bootstrap/Core/.../mapping/Mappings.java:14`：同时维护 `classMappingsBySourceName` / `ByTargetName`、`fieldMappingsBySourceKey` / `ByTargetKey`、`methodMappingsBySourceKey` / `ByTargetKey`，方法描述符里的类名用 `Pattern CLASS_NAME_IN_DESCRIPTOR = "L([^;]+);"` 重映射；`Loader.load(classLoader, mappingType)` 从 jar 内 `/customskinloader/mapping.xml` 读映射，`Parser` 解析。transformer 目标类名先经 `remapClassName` 再匹配，因此同一份 patch 可跨 MCP/SRG/Mojmap。
3. **版本区间限定的补丁集合** `transformer/patch/SkinManagerPatch.java:20`：每个 target 带版本表达式 `"[764,800],[804,0x40000000],[0x40000090,]"`（含 1.20.2/快照编码），`applyIfMatches(versionExpr, patchName, action)` + `requireModified(...)` 保证补丁"要么成功要么报错"，不静默失效。同目录另有 `InterfacePatch` / `RenderPatch` / `SkinTexturePatch`。
4. **跨版本接口适配层（fake 包）** `Common/src/main/java/customskinloader/fake/`：`FakeSkinManager`（27 行起）静态方法把不同版本 `SkinManager` 的调用统一成 `getUserProfile/loadSkinFromCache`，内部类 `FakeCacheKey extends SkinManager$CacheKey` 直接继承被 patch 成 public 的原版内部类（配合 `makeInnerClassPublicNonFinal`）；`fake/itf/` + `FakeInterfaceManager` 用接口强转代替反射（`NativeImage` vs `BufferedImage` 双实现），`fake/texture/` 是纹理下载/裁剪抽象。
5. **多源并发档案加载与合并** `CustomSkinLoader.loadProfile0(GameProfile, boolean)`（`CustomSkinLoader.java:90`）：遍历 `config.loadlist` 中每个 `SkinSiteProfile`，用 `CompletableFuture.supplyAsync(..., PROFILE_THREAD_POOL)` 并行请求各皮肤站，再按顺序 `join()` 并 `profile0.mix(profile)` 逐字段合并（`forceLoadAllTextures=false` 时首个非空即停）；结果写 `ProfileCache`。
6. **可插拔站点加载器** `Common/.../loader/ProfileLoader.java`：`LOADERS` 由 `PluginLoader.PLUGINS` 初始化成 `Map<String lowercaseName, IProfileLoader>`；`IProfileLoader` 四个方法 `loadProfile / compare / getName / init`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无自定义包（客户端 mod）。HTTP 自建：`utils/HttpRequestUtil.java`（284 行，含本地/网络缓存）、`HttpTextureUtil`、`UserAgentUtil`、`utils/ThreadPoolFactory`（java21 版直接 `Executors.newVirtualThreadPerTaskExecutor()`，Java 8 版用传统池，靠 `Common/build.gradle:6` 的 `sourceSets.java21` + 条件 include 实现按版本替换）。
- **数据驱动**：配置驱动。`config/Config.java` 是 Gson 直反序列化的普通 POJO（`version/buildNumber/loadlist/enableTransparentSkin/forceLoadAllTextures/enableCape/threadPoolSize/cacheExpiry/forceUpdateSkull/enableLocalProfileCache/enableCacheAutoClean/forceDisableCache`），配置文件 `<mc>/CustomSkinLoader/CustomSkinLoader.json`；站点模型 `config/SkinSiteProfile.java`；每个加载器可通过 `ICustomSkinLoaderPlugin.IDefaultProfile.updateSkinSiteProfile(ssp)` 把默认站点**回写进配置文件**。
- **datagen**：无。资源只有两个 mods.toml 和一个 fabric mixins.json；版本号通过 Gradle `ReplaceTokens` 在编译期替换 `@MOD_VERSION@` / `${modFullVersion}`（`build.gradle:56` 的 `generateJavaMacros` 任务，把 `src/main/java` 过滤输出到 `build/generated/sources/java-macros/`）。
- `Dummy/*` 只参与编译，不打进产物（真实类运行期才存在）。

## 6. Mixin

- 唯一配置 `Bootstrap/FabricV1/src/main/resources/customskinloader.bootstrap.fabric.v1.mixins.json`：`"plugin": "customskinloader.bootstrap.fabric.v1.MixinConfigPlugin"`、`compatibilityLevel: JAVA_8`、仅一个空 mixin `DummyMixin`，`getMixins()` 返回空列表——**用 Mixin 当"最早可插入的加载钩子"**，真正改字节码发生在 `postApply(String targetClassName, ClassNode targetClass, IMixinInfo)` 里调 `TransformerBootstrap.transformTargetClass`（`MixinConfigPlugin.java:38`），`acceptTargets` 时调 `applyPendingMixinTargets(this)` 反射补目标类。
- Forge/NeoForge 侧走各加载器原生 `IClassTransformer` / `ClassProcessor`，不用 Mixin。

## 7. 值得学的 5 条具体做法

1. **用 Mixin 的 `IMixinConfigPlugin.postApply` 拿 ClassNode 做自有 ASM 改写**，从而不写具体 mixin 方法也能改原版类 → `Bootstrap/FabricV1/.../MixinConfigPlugin.java:38`；适用"目标类随版本变动大、必须按映射自适配"的 mod。
2. **双命名空间 Mappings 索引 + 描述符内类名重映射**，让 patch 代码写源命名空间、运行期自动转目标命名空间 → `Bootstrap/Core/.../mapping/Mappings.java`；适用跨映射命名空间分发。
3. **给每个补丁标注适用版本区间（含快照编码），并用 `requireModified` 强校验**，避免版本升级后补丁静默失效 → `Bootstrap/Core/.../transformer/patch/SkinManagerPatch.java:20`。
4. **`Dummy/` 编译桩模块**：把 Minecraft/ModLauncher 等 API 写成空壳源码只用于编译，产物不含它们，从而一个工程同时支持 1.8–1.21 → `Dummy/Common/src/main/java/net/minecraft/`；适用"不想跟每个版本各开分支"的库类 mod。
5. **构建期 token 替换注入版本号 + `buildSrc` 里下载 Minecraft version json 拿 libraries 依赖集**（`build.gradle:42` 的 `manifestLibraries { add("https://raw.githubusercontent.com/PrismLauncher/meta-launcher/.../${minecraft_version}.json") }`、`buildSrc/.../ManifestLibrariesExtension.java`）；适用需要手工拼装运行时依赖集的特殊构建。

## 8. 公开 API 包路径 / 扩展点

- **扩展接口** `customskinloader.plugin.ICustomSkinLoaderPlugin`（`Common/src/main/java/customskinloader/plugin/ICustomSkinLoaderPlugin.java`）：实现 `getProfileLoader()` 返回自定义 `ProfileLoader.IProfileLoader`（`loadProfile(SkinSiteProfile, GameProfile)` / `compare` / `getName` / `init`），并可用内部接口 `IDefaultProfile`（`getName` / `getPriority` / `updateSkinSiteProfile`）提供默认站点。
- **接入方式**：把 jar/zip 丢进 `<mc>/CustomSkinLoader/Plugins/`，`PluginLoader.loadPlugins()` 用 `new URLClassLoader(urls, PluginLoader.class.getClassLoader())` + `ServiceLoader<ICustomSkinLoaderPlugin>` 发现（需自带 `META-INF/services`）；内置 9 个加载器（`GameProfileLoader`、`MojangAPILoader`、`LegacyLoader` 及 6 个 `JsonAPILoader` 子类型：CustomSkinAPI/CustomSkinAPIPlus/UniSkinAPI/ElyByAPI/MinecraftCapesAPI/WynntilsAPI）。
- 无对外 Java API 稳定性承诺（GPL-3.0-only）。
