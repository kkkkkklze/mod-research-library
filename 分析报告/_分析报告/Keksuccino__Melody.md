# Melody（Keksuccino/Melody）源码分析

> 说明：本地 `_bulk/Keksuccino__Melody` 是 sparse checkout，`main` 分支只有 README/changelog 与 issue 模板（`git ls-tree -r main | grep .java` = 0）。本报告基于其 **1.21.1 分支**（clone 到 `_bulk/_tmp_melody`）分析，共 23 个 java 文件。

## 1. 基本信息

- Mod 名 Melody / `mod_id=melody` / 作者 Keksuccino / 版本 1.0.10（`gradle.properties:8-14`）
- 目标：**MC 1.21.1、Java 21**；Fabric Loader 0.16.10 + Fabric API 0.110.0+1.21.1；NeoForge 21.1.47（`gradle.properties:20-30`）
- 构建：三模块多加载器 `common / fabric / neoforge`（`settings.gradle:19-21`）；common 与 fabric 用 **Fabric Loom 1.9-SNAPSHOT**，neoforge 用 **NeoGradle userdev 7.0.178**；映射 officialMojangMappings + Parchment 2024.11.17
- 许可证 MIT（`LICENSE:1`、`mod_license`）
- 编译依赖：jsr305 3.0.2、asm-tree 9.7、mixin 0.8.5（compileOnly）、mixin-extras 0.4.1（Fabric 侧 `include(...)` 打包）、fabric-loader（compileOnly，仅用 @Environment）。**无 GUI/前置硬依赖，自身就是别人（如 FancyMenu）的前置库**

## 2. 源码规模与包结构

23 个 `.java` / 1289 行（`find -name '*.java' -exec wc -l {} +`）。

| 包 | 内容 |
|---|---|
| `de.keksuccino.melody` | `Melody.java`（主类，25 行） |
| `.platform` / `.platform.services` | `Services`、`IPlatformHelper`、`IPlatformCompatibilityLayer`；平台实现分别在 fabric/neoforge 源码集 |
| `.resources.audio` | `AudioClip`（接口）、`SimpleAudioFactory`、`MinecraftSoundSettingsObserver`、`MelodyAudioException` |
| `.resources.audio.openal` | `ALAudioClip`、`ALAudioBuffer`、`ALUtils`、`ALErrorHandler`、`ALException` |
| `.mixin` / `.mixin.mixins.common.client` | `MelodyMixinPlugin` + 3 个 mixin |

最大文件：`SimpleAudioFactory.java` 301、`ALAudioClip.java` 252、`NeoForgePlatformHelper.java` 75、`FabricPlatformHelper.java` 74、`ALAudioBuffer.java` 70。

## 3. 入口与注册

**没有任何游戏对象注册**（无 DeferredRegister / Registrate / 事件总线），主类只做平台探测与日志：

```java
// common/.../Melody.java:15-23
public static void init() {
    if (Services.PLATFORM.isOnClient()) {
        LOGGER.info("[MELODY] Loading v" + VERSION + " on " + MOD_LOADER.toUpperCase() + "...");
    } else {
        LOGGER.warn("[MELODY] Disabling Melody since it's loaded server-side.");
    }
}
```

- Fabric：`fabric.mod.json` entrypoint `main` → `MelodyFabric implements ModInitializer`（`fabric/.../MelodyFabric.java:8-12`），服务端也会加载并打警告
- NeoForge：`@Mod(Melody.MOD_ID) MelodyNeoForge` 构造器调用 `Melody.init()`（`neoforge/.../MelodyNeoForge.java:5-12`）
- 平台差异通过 `Services` 的 `ServiceLoader.load(clazz).findFirst()` + 各平台 `META-INF/services/<接口全名>` 文件实现（`Services.java:16-25`）

## 4. 核心系统

**(1) 音频工厂**（`resources/audio/SimpleAudioFactory.java`）：入口 `ogg(String source, SourceType)` / `wav(...)` → `CompletableFuture<ALAudioClip>`；`SourceType = RESOURCE_LOCATION / LOCAL_FILE / WEB_FILE`（:290-294）。OGG 用 MC 自带 `JOrbisAudioStream`（:249），WAV 用 `javax.sound.sampled.AudioSystem`（:269，先 readAllBytes 规避 mark/reset 问题，:267 注释）；WEB 用 `HttpURLConnection` + `User-Agent: Mozilla/4.0`（:283-288）。创建前强制 `RenderSystem.assertOnRenderThread()` + `ALUtils.isOpenAlReady()`（:46-50），失败一律 `clip.closeQuietly()` 防泄漏。

**(2) OpenAL 生命周期**（`openal/ALAudioClip.java`、`ALAudioBuffer.java`）：直接用 LWJGL `AL10`（`alGenSources/alSourcePlay/alSourcePause/alSourceStop/alSourcei(AL_LOOPING)/alSourcef(AL_GAIN)`），每次调用后 `ALErrorHandler.checkOpenAlError()`。`ALAudioBuffer.prepare()` 懒加载 `alGenBuffers + alBufferData`，成功后把 `dataBuffer` 置 null 释放内存（:28-47）。关键约束：**clip 在资源重载/音频设置变更后会失效**，用 `isValidOpenAlSource()`（`alIsSource`，:248-250）判定。

**(3) 音量与重载同步**（`MinecraftSoundSettingsObserver.java` + `mixin/.../MixinSoundEngine.java`）：静态注册表存 `Map<Long, BiConsumer<SoundSource,Float>>` 与 `Map<Long, Runnable>`（:12-13），mixin 在 `SoundEngine.updateCategoryVolume` 的 RETURN 与 `SoundEngine.reload` 的 RETURN 分发（`MixinSoundEngine.java:25-37`）。`ALAudioClip` 构造器注册监听（:69-71），`setVolume()` 把 `Minecraft.options.getSoundSourceVolume(channel)` 乘进去（:158-171）。

**(4) 就绪检测**：`ALUtils.isOpenAlReady()` 经两个 `@Accessor` 接口读 MC 私有字段——`IMixinSoundManager.getSoundEngineMelody()`（`@Accessor("soundEngine")`）→ `IMixinSoundEngine.getLoadedMelody()`（`@Accessor("loaded")`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

**均为无**：无网络包、无配置文件（只读 Minecraft 的 SoundSource 音量）、无 datagen、无 languages。仅 `pack.mcmeta`、logo、`META-INF/services/*`。

## 6. Mixin

- `common/src/main/resources/melody.mixins.json`：`package de.keksuccino.melody.mixin.mixins.common`，client 3 条，plugin `MelodyMixinPlugin`，refmap `melody.refmap.json`；`compatibilityLevel` 写死 `JAVA_17`（实际编译 Java 21）
- `fabric/src/main/resources/melody.fabric.mixins.json` 与 `melody.neoforge.mixins.json` 为空数组，仅预留平台专属 mixin 目录
- hook 目标：`SoundEngine.updateCategoryVolume(SoundSource,float)` @RETURN、`SoundEngine.reload()` @RETURN；两个 `@Mixin + @Accessor` 接口取私有字段
- `MelodyMixinPlugin.shouldApplyMixin` 恒返回 true，未做条件启用

## 7. 值得学的 5 条做法

1. **common 用 Loom 编译、平台模块直接吃 common 源码**：`neoforge/build.gradle` 用 `tasks.withType(JavaCompile).matching(notNeoTask).configureEach { source(project(":common").sourceSets.main.allSource) }`，同时在 `runtimeClasspath` 排除 `net.fabricmc:fabric-loader` —— 一份源码双平台真编译，不依赖 jar 内嵌。
2. **平台差异用 Java 原生 ServiceLoader**（`Services.java:16`）+ `META-INF/services` 文本文件，避免反射与静态单例。
3. **`@Accessor` mixin 接口只暴露一个字段**（`IMixinSoundEngine.java:10`），比在逻辑类里 `@Shadow` 干净，且可被任意代码 `(IMixinX) obj` 强转访问。
4. **把 MC 内部事件转成自己的监听器 API**：静态 ID→回调 映射 + mixin 在 RETURN 注入分发（`MinecraftSoundSettingsObserver`），监听器可反注册，避免长期持有引用。
5. **工厂方法入口即做前置校验并统一清理**：`assertOnRenderThread()` → `isOpenAlReady()` → `create()` 失败即 `closeQuietly()`，异常信息带音频来源字符串，便于定位。

## 8. 库 API（前置/API 类 mod）

- 公开 API 包：`de.keksuccino.melody.resources.audio`（`AudioClip` 接口：play/pause/resume/stop/setVolume/setSoundChannel/isClosed）、`...audio.openal`（`ALAudioClip.create()/of(ALAudioBuffer)`、`ALAudioBuffer`、`ALUtils`、`ALErrorHandler`/`ALException`）、`...platform.services.IPlatformHelper`
- 扩展点：`AudioClip` 是接口（可自写实现）；`SimpleAudioFactory` 是格式工厂样板（README 明确指路）；要支持新格式需自行仿写 factory + `ALAudioBuffer`
- 接入方式：依赖 Melody jar，调 `SimpleAudioFactory.ogg(url, SourceType.WEB_FILE)` 拿 `CompletableFuture<ALAudioClip>`，用前查 `ALUtils.isOpenAlReady()`、资源重载后重建 clip（`isValidOpenAlSource()` 检查）；`SourceType` 覆盖资源包/本地文件/网络三种来源
- 发布/坐标：仓库内有 `mod_upload.py` + `mod_upload_config.json` 发布脚本，具体 maven 坐标与 jarJar 接入方式**未确认**
