# fxmorin/memoryLeakFix 源码分析报告

## 1. 基本信息
- Mod 名 Memory Leak Fix；mod_id `memoryleakfix`；作者 FX - PR0CESS（fxmorin）
- 目标：MC **1.20.4**（Fabric + Forge，Quilt 兼容）；加 `-Dbuild16=true` 用同一套源码再产 1.15.2~1.16.5 版本（`gradle.properties:11-16`、`build.gradle:16,43`、`.github/workflows/publish.yml`）
- Gradle：`architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 0.12.0-SNAPSHOT`，模块 `common/fabric/forge`，Java 8（`options.release=8`）、Mojang 官方映射、shadow 7.1.2；许可 LGPL-2.1-only
- 依赖：`fabric-loader 0.15.3`（common 只取 `@Environment` 注解，见 `common/build.gradle:15-16` 注释）、**MixinExtras 0.3.2**（forge 侧 shadow 并 `relocate("com.llamalad7.mixinextras","ca.fxco.memoryleakfix.mixinextras")` + `mergeServiceFiles()`，`forge/build.gradle:74-75`）；architectury API 被注释掉，只沿用其 `@ExpectPlatform` 约定

## 2. 规模与包结构
28 个 `.java`，共 **1165** 行。最大文件：`common/src/main/java/ca/fxco/memoryleakfix/config/MemoryLeakFixMixinConfigPlugin.java`(392)、`utils/MixinInternals.java`(83)、`mixin/readResourcesLeak/TextureUtil_freeBufferMixin.java`(68)、`forge/.../MemoryLeakFixExpectPlatformImpl.java`(62)。
包（第 3 层）：`ca.fxco.memoryleakfix`(3 个类)、`.config`(8，含 `mixinExtension`)、`.extensions`(2 个访问接口)、`.mixin.<泄漏名>`(9 个 mixin，一个泄漏一个包)、`.utils`(1)；另有 fabric/forge 两个平台包。

## 3. 入口与注册
无任何游戏对象注册。真正入口是 mixin 配置插件的 `onLoad`（`config/MemoryLeakFixMixinConfigPlugin.java:35-40`）：
```java
public void onLoad(String mixinPackage) {
    MemoryLeakFixBootstrap.init();                      // 幂等注册 UnMixinExtension
    if (ArchitecturyTarget.getCurrentTarget().contains("forge")) MixinExtrasBootstrap.init();
}
```
Forge 的 `@Mod` 类仅调 `MemoryLeakFix.init()`；Fabric `fabric.mod.json` entrypoint 指向 12 行的 `MemoryLeakFixFabric`。平台差异全部收在 `MemoryLeakFixExpectPlatform` 的 4 个 `@ExpectPlatform` 静态方法（`isModLoaded / compareMinecraftToVersion / getMappingType / isDevEnvironment`），两侧各有一个 `*ExpectPlatformImpl` 实现（`forge/...:38-62`、`fabric/...:14-38`）。

## 4. 核心系统
1. **按版本启停 mixin**：自定义 `@MinecraftRequirement(@VersionRange(minVersion,maxVersion))` 注解 + `shouldApplyMixin()` 用 `compareMinecraftToVersion` 判定；命中的修复名收集到 `APPLIED_MEMORY_LEAK_FIXES`，在 `acceptTargets()` 一次性打印"将启用 N 个修复"（plugin:48-58、76-86）。
2. **多映射名兼容**：`@Remap(fabric/forge/mcp, excludeDev, mcVersions)` / `@Remaps` 在运行时直接改写 mixin 注解的 `method=` 与 `At.target=`（`executeRemapAnnotation`、`remapMixinAnnotation`、`alterAtTarget`，plugin:249-390）；映射类型来自 `getMappingType()` 返回 `"fabric"/"forge"/"mcp"`。
3. **改 mixin 自身字节码**：`utils/MixinInternals.java:28-72` 反射取 `TargetClassContext.mixins`、`MixinInfo.getState().classNode`、`Extensions.extensions/activeExtensions`，把 `UnMixinExtension` 挂进 activeExtensions，在其 `preApply` 中调用 `runCustomMixinClassNodeAnnotations` 删除不符合版本条件的注入方法/字段（`config/mixinExtension/UnMixinExtension.java:22-26`）。
4. **逐条泄漏的注入手法**（每个类都很短）：`Biome` 用 `@WrapOperation` 把 `ThreadLocal.withInitial` 结果换成**静态** ThreadLocal（`mixin/biomeTemperatureLeak/Biome_threadLocalMixin.java:29-41`）；`TagKey` 用 `@Redirect` 把 `Interners.newStrongInterner()` 换成 `newWeakInterner()`（MC-248621）；`ServerLevel.onEntityRemoved` TAIL 从 `Set<PathNavigation> navigations` 移除溺水者导航（MC-202246，仅 1.16.3~1.16.5）；`Entity.remove` TAIL 清空 `Brain.memories`（MC-260605，≤1.19.3）；`Minecraft.grabHugeScreenshot` 用 `ModifyExpressionValue` + MixinExtras `@Share LocalRef` 捕获 `GlUtil.allocateMemory` 的 ByteBuffer，在 `"screenshot.failure"` 常量处 `GlUtil.freeMemory`；`TextureUtil.readResource` 用 `@WrapOperation` 包住 `FileChannel/ReadableByteChannel.read`，异常时 `MemoryUtil.memFree(byteBuf)`（MC-226729）。
5. **软目标兼容**：`@Pseudo` + 多 `targets` 类名 + 自定义 `@SilentClassNotFound`，目标类不存在时静默跳过（plugin:60-73、`TextureUtil_freeBufferMixin.java:20-29`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
无网络、无配置文件、无 datagen；mixin 应用情况仅打日志。

## 6. Mixin
- `common/src/main/resources/memoryleakfix.mixins.json`：client = hugeScreenshotLeak、targetEntityLeak；mixins = biomeTemperatureLeak、entityMemoriesLeak×3、tagKeyLeak
- `memoryleakfix-16.mixins.json`：client = readResourcesLeak、targetEntityLeak；mixins = biomeTemperatureLeak、drownedNavigationLeak×2、entityMemoriesLeak×3
- `fabric/src/main/resources/memoryleakfix-fabric.mixins.json`：client 为空数组，只为在 Fabric 侧也加载同一个 `plugin`
- 三者 `defaultRequire:1`、`plugin: ca.fxco.memoryleakfix.config.MemoryLeakFixMixinConfigPlugin`；fabric.mod.json 用 `${commonMixinId}` 占位注入配置名，forge 侧由 `forge/build.gradle` 的 `loom.forge.mixinConfig` 声明

## 7. 值得学的 5 条
1. 用自定义版本注解 + mixin 配置插件做"每个修复按 MC 版本独立启停"：`config/MemoryLeakFixMixinConfigPlugin.java:48-58`，适合长生命周期兼容 mod。
2. 用 `@Remap` 注解在运行时改写 mixin 注解里的方法名与 `At.target`，一套源码吃 fabric/forge/mcp 三种映射：`config/Remap.java`、plugin:249-320。
3. `@Pseudo` + 多 `targets` + `@SilentClassNotFound`，让跨版本/跨加载器目标缺失不报错：plugin:60-73。
4. MixinExtras `@Share LocalRef` 把"分配点捕获的局部对象"传到另一个注入点，用于失败分支释放原生内存：`mixin/hugeScreenshotLeak/Minecraft_screenshotMixin.java:25-48`。
5. 需要动 mixin 自身（删注入点/改字段名）时，用 `IExtension` + 反射 internals 挂 activeExtensions，是最"轻"的官方未暴露入口：`utils/MixinInternals.java:61-73`。

## 8. 库/API
非前置库 mod，不对外提供 API（仅自带 `extensions/` 访问接口供自己的 mixin 互调）。
