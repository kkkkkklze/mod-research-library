# kltyton/LightSpeedRe 源码分析报告

## 1. 基本信息
- Mod 名 Lightspeed / `mod_id=lightspeed` / 作者 CCr4ft3r, kltyton（fork）/ 版本 `1.20.1-1.2.3`
- 目标：MC 1.20.1 + **Forge 47.4.20**（`loader_version_range=[47,)`），官方映射
- 许可证：All Rights Reserved（`gradle.properties:8`）
- 构建：`net.minecraftforge.gradle [6.0.16,6.2)` + `org.spongepowered.mixin`（mixingradle 0.7-SNAPSHOT），Java 17
- 依赖：仅 forge + mixin AP；`compileOnly+jarJar io.github.llamalad7:mixinextras-forge:0.3.5`（build.gradle）。**无 API、无前置**

## 2. 源码规模与包结构
- 33 个 `.java`，2487 行（`find src -name '*.java' -exec wc -l {} +`）。全在 `src/main/java/com/ccr4ft3r/lightspeed/`
- 包：`mixin/resources` 9、`mixin/misc` 6、`interfaces` 3、`mixin/model` 3、`mixin/renderer` 2、`compat` 2、`util` 2、`cache` 1、`config` 1、`events` 1、根 2
- 最大文件：`mixin/resources/PathResourcePackMixin.java`(494)、`cache/GlobalCache.java`(323)、`compat/ResourceReloadFailureGuard.java`(224)、`mixin/resources/FallbackResourceManagerMixin.java`(186)、`mixin/resources/FilePackResourcesMixin.java`(124)

## 3. 入口与注册
`src/main/java/com/ccr4ft3r/lightspeed/Main.java:17` `@Mod(ModConstants.MOD_ID)`。**不注册任何方块/物品**，只在构造中挂配置与刷新开关：
```java
modEventBus.addListener(this::onConfigEvent);
ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, LightspeedConfig.SPEC);
updateCacheFlags();
```
`updateCacheFlags()`（Main.java:35-77）把 config 值写入 `GlobalCache` 的 volatile 静态开关，并做 mod 存在性兼容判断（`ModConstants.java` 声明 `connectormod/sophisticatedstorage/jsonthings/multiblocked` 常量）。

## 4. 核心系统
1. **全局缓存与线程池**（`cache/GlobalCache.java`）：`EXECUTOR`/`CACHE_EXECUTOR` 为固定线程池，`RESOURCE_RELOAD_EXECUTOR` 是自定义 `ForkJoinPool`（`newReloadWorker:244` 手动设 `setContextClassLoader` 与线程名，避免 ModLauncher 类加载问题）。线程数按 CPU 通过系统属性 `lightspeed.workers/cacheWorkers/reloadWorkers` 覆盖（:220-242）。
2. **资源包路径/命名空间缓存**（`mixin/resources/PathResourcePackMixin.java`）：`@Unique` 字段 `lightspeed$resolvedPathByResource`、`lightspeed$namespacesByPackType`、`lightspeed$relativeFilePathsByPackType`；`@Inject(method="resolve", at=HEAD, cancellable=true)` 直接返回缓存 Path（:75-98），`getNamespaces` 命中缓存即 `cir.setReturnValue`（:110-117）。
3. **并行查找 + 安全白名单**：`GlobalCache.findFirstResource:164` 仅在包数 ≥ `parallelLookupMinPacks` 时并发；`isSafeForParallelLookup:317` 只放行 `PathPackResources`（含 `ResourcePackLoader$` 内部类）与 `FilePackResources` 且 `FusionPackCompat.hasOverrides(pack)==false`，否则顺序回退。
4. **持久化缓存**（`util/CacheUtil.java`）：缓存目录 `gamedir/lightspeed-cache/<MC版本>/{hasResource,namespaces,resourceLists}`，用 Java 原生 `ObjectOutputStream` 写 `.ser`；接口 `ICache.lightspeed$persistAndClearCache()` 由 `GlobalCache.disablePersistAndClear:198-218` 统一 flush、清目录、清 Map。
5. **重载失败隔离**（`compat/ResourceReloadFailureGuard.java:25`）：`guard(listener, reload)` 捕获第三方 `PreparableReloadListener` 的异常并返回 `null` 完成 future，`shouldIsolate:50` 用配置的类名前缀模式（默认 `*`）判定，避免单个 mod 崩溃整个加载界面。

## 5. 网络 / 数据驱动 / 配置
- **网络**：无。
- **数据驱动 / datagen**：无（build.gradle 保留 data run config，`src/generated` 未使用）。
- **配置**：`config/LightspeedConfig.java` 用 `ForgeConfigSpec`，分 `startup`（asyncPreloadPacks、dedicatedResourceReloadExecutor、parallelResourceLookup、parallelLookupMinPacks、cacheResourceExistence）与 `compatibility`（isolateModdedResourceReloadFailures、isolatedResourceReloadListenerPatterns、connectorCompatibilityMode）共 8 项；监听 `ModConfigEvent` 热重载。

## 6. Mixin
配置 `src/main/resources/lightspeed.mixins.json`：client 10 个、mixins 11 个，含另一个 accessor（`FallbackResourceManagerPackEntryAccessor`）。
代表 hook：`PathPackResources#resolve / getNamespaces`（缓存）、`VanillaPackResourcesMixin`、`FilePackResourcesMixin`、`SimpleReloadInstanceMixin`、`MinecraftReloadExecutorMixin`、`MinecraftMainMixin`、`misc/SelectorMixin`+`misc/MaterialMixin`+`misc/StateDefinitonMixin`（方块状态/材质去重）、`renderer/EntityRenderersMixin`、`renderer/ForgeHooksClientMixin`。

## 7. 值得学的 5 条做法
1. **兼容性开关集中管理**：所有优化开关收在一个 `GlobalCache` 静态字段 + config → 一处判断关闭，便于针对 Sinytra Connector 等直接禁用（`cache/GlobalCache.java:46-57`、`Main.java:57-69`）——适用于任何"性能优化型 mod"。
2. **并行前先做安全白名单**：只对确定线程安全的原版包类并行读，并检测第三方包装类（`FusionPackCompat.hasOverrides`）——适用于并发加速资源加载。
3. **缓存分模块落盘 + 版本隔离目录**：`.ser` 文件按功能分目录、按 MC 版本号再分层，避免跨版本脏缓存（`util/CacheUtil.java:19-23`）。
4. **自定义 ForkJoinPool 手动设 contextClassLoader**（`GlobalCache.java:244-250`）——Forge 上自建线程池加载资源时避免 ClassLoader 归属错误。
5. **统一"失败即降级"的兜底**：缓存任务全部走 `executeCacheLogged` 捕获异常并记录任务名（`GlobalCache.java:129-140`），单点失败不影响启动——适用于任何异步加载逻辑。

## 8. （库/前置类）
非库 mod，无对外 API 包。
