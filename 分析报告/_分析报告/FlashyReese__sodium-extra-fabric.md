# Sodium Extra 源码分析报告

## 1. 基本信息
- Mod 名：Sodium Extra；NeoForge mod_id `sodium_extra`（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）；仓库内 fabric 模块**没有** fabric.mod.json（未确认其 Fabric id）。
- 作者：FlashyReese。许可证：LGPLv3（`LICENSE.txt`、toml 的 `license = "LGPLv3"`）。
- 目标版本（`build.gradle.kts:6-13`）：MC `26.2`、NeoForge `26.2.0.1-beta`、Fabric Loader `0.19.3`、Fabric API `0.152.1+26.2`、Java 25。
- Gradle 插件：`net.fabricmc.fabric-loom 1.17.13`（common/fabric）、`net.neoforged.moddev 2.0.141`（neoforge）；三模块 `common`/`fabric`/`neoforge`（`settings.gradle.kts`）。
- 编译依赖（它是 Sodium 的附属，非前置库）：`net.caffeinemc:sodium-fabric|sodium-neoforge(-api|-mod):0.9.1+mc26.2`（其 `net.caffeinemc.mods.sodium.api.config.*` 即 Sodium 配置 API）；`me.flashyreese.mods:greenlight-api:0.1.0+mc26.2`（fabric `include`、neoforge `jarJar`，toml 中 optional）；`mixinextras-common 0.5.4`；`sponge-mixin 0.17.3`。

## 2. 规模与包结构
85 个 `.java`，6083 行（`find . -name '*.java' | wc -l`；`wc -l`）。包：`me.flashyreese.mods.sodiumextra.{client,common,compat,mixin}`、`net.caffeinemc.caffeineconfig`（内嵌）。最大文件：`client/config/SodiumExtraConfig.java` 1141、`client/config/SodiumExtraGameOptions.java` 571、`client/fog/FogDistanceHelper.java` 448、`net/caffeinemc/caffeineconfig/CaffeineConfig.java` 423、`client/fog/FogShaderTransformer.java` 170、`client/render/PaniniProjection.java` 141、`client/SodiumExtraClientMod.java` 134。mixin 子包按功能分：`mixin/fog`(13)、`mixin/particle`(4)、`mixin/render/entity`(3)、`mixin/render/block/entity`(3)、`mixin/panini_projection`(3)、`mixin/gui`(3)、`mixin/animation`(2)、`mixin/toasts`(2) 等。

## 3. 入口与注册
无 DeferredRegister：`common` 是被两边直接编译进 jar 的源码集（`fabric/build.gradle.kts` 的 `tasks.withType<JavaCompile>{ source(project(":common")...) }`；neoforge 侧用 `notNeoTask` 过滤），状态集中在静态单例 `client/SodiumExtraClientMod.java:28-133`（`options()`、`mixinConfig()` 懒加载）。
- Fabric：`SodiumExtraFabricClientModInitializer implements ClientModInitializer`（`onInitializeClient`→`initFabric()`，直接改 `DebugScreenEntries.PROFILES`）；`SodiumExtraFabricPreLaunch implements PreLaunchEntrypoint` → `WaylandFullscreenResolutionRecovery.recoverIfNeeded`。
- NeoForge：`@Mod(value="sodium_extra", dist=Dist.CLIENT)` 的 `SodiumExtraNeoForgeClientMod`，构造器内做恢复 + `bus.addListener(this::registerDebugEntries)`（`RegisterDebugEntriesEvent`）。
- 注册内容：4 个调试 HUD 条目（`registerAll(BiConsumer<Identifier,DebugScreenEntry>)`，`SodiumExtraClientMod.java:123-133`）+ Sodium 设置页。
- Sodium 设置页由 `client/config/SodiumExtraConfig.java:39` `implements ConfigEntryPoint` 提供，toml 里用 `[modproperties.sodium_extra] "sodium:config_api_user" = "...SodiumExtraConfig"` 声明。

## 4. 核心系统
1) 选项注册（Sodium Config API）：`SodiumExtraConfig.registerConfigLate(ConfigBuilder)`（:1130-1140）→ `registerOwnModOptions().setIcon(...).addPage(animations/particles/details/render/extra).registerOptionReplacement("sodium:general.fullscreen_resolution"|"…vsync")`；页内用 `builder.createOptionGroup()` 组织（约 35 处）。选项 ID 用 `Identifier.parse("sodium-extra:xxx")`；泛型 helper `fogOption()`（:168）统一设 `setName/setTooltip/setEnabledProvider(...,ConfigState.UPDATE_ON_REBUILD)/setStorageHandler`；粒子页按 namespace 动态生成（`compareParticleNamespace`:182）。
2) 配置存储：`SodiumExtraGameOptions implements StorageEventHandler`，Gson（`LOWER_CASE_WITH_UNDERSCORES` + `@SerializedName(常量)` + `IdentifierSerializer`）；`load()` 捕获 `IOException|JsonParseException|IllegalStateException` 后落默认值并把损坏文件 `moveCorruptConfig`；写盘走 `ConfigFileIO.writeStringAtomically`（临时文件 + `ATOMIC_MOVE` + `channel.force` + 目录 fsync，`ConfigFileIO.java:29-66`）；文件名在 `SodiumExtraConfigKeys.FILE_NAME`。
3) Mixin 开关体系（内嵌 `net.caffeinemc.caffeineconfig`，4 个类）：`CaffeineConfig.builder("Sodium Extra").addMixinOption("fog",true)…`（`SodiumExtraClientMod.java:50-86`）生成 `mixin.fog` 键；`AbstractCaffeineConfigMixinPlugin.shouldApplyMixin` 用 `getEffectiveOptionForMixin`（`CaffeineConfig.java:201`，按包路径逐级前缀匹配）决定是否应用，父项关闭连坐子项（:149-168）；用户 `.properties` 与其他 mod 元数据 JSON 键 `sodium-extra:options` 都可覆盖，且“禁用优先”（:184）；平台差异用 `ServiceLoader`（`CaffeineConfig.java:27`）→ `CaffeineConfigFabric`/`CaffeineConfigNeoForge`。
4) 雾系统：`FogDistanceHelper`(448) + `mixin/fog/*` + `FogShaderTransformer`；`MixinFogRenderer.java:25`（`priority=1300`、`@Unique` 字段）用 `@WrapOperation` 捕获是否 `AtmosphericFogEnvironment`，`@Inject(at FIELD PUTFIELD renderDistanceEnd ordinal=0)` 后改写 start/end，`@ModifyArgs` 改 `updateBuffer` 参数。
5) 其他：`PaniniProjection`（投影）、`reduce_resolution_on_mac`（5 个 mixin + `MacReducedResolution`）、`ToastFilter`、`FrameCounter`、`SodiumExtraHud`、`IrisCompat`。

## 5. 网络 / 数据驱动 / 配置 / datagen
无网络代码（纯客户端）。配置双轨：Sodium config API（内存态 + `StorageEventHandler`）+ JSON/`.properties` 文件；文档见 `docs/protected-gameplay-fog.md`、`docs/server-policies.md`；无 datagen。

## 6. Mixin
配置：`common/src/main/resources/sodium-extra.mixins.json`（`plugin = ...mixin.SodiumExtraMixinConfigPlugin`、`compatibilityLevel: JAVA_25`、49 个 client mixin、`injectors.defaultRequire: 1`）。AW：`common/src/main/resources/sodium-extra.accesswidener`（可写 `DebugScreenEntries.PROFILES`）；NeoForge 另有 `META-INF/accesstransformer.cfg`。代表：`mixin/fog/MixinFogRenderer`、`mixin/gui/MixinMinecraftClient`、`mixin/animation/MixinTextureAtlas`、`mixin/steady_debug_hud/MixinDebugScreenOverlay`。

## 7. 值得学的做法
- 单份 `common` 源码被两个 loader 模块直接 source 编译，不做跨平台抽象层（`fabric/build.gradle.kts` 的 `JavaCompile.source`）。
- 选项 UI 与存储解耦：选项只挂 `StorageEventHandler`，序列化键集中在 `SodiumExtraConfigKeys` 常量，避免改名漏改。
- 配置写入原子化 + 损坏文件另存 `.corrupt.N`（`ConfigFileIO.java:29`、`SodiumExtraGameOptions.moveCorruptConfig`）。
- 用包名＝选项名构建 mixin 开关树，天然支持“一键关掉整个子系统”（`CaffeineConfig.getEffectiveOptionForMixin`）。
- 平台差异只在 `ServiceLoader` 边界分叉（`CaffeineConfigPlatform`），入口在 common 暴露 `registerAll(...)`，两端各一行 lambda 适配。
- 泛型 builder helper（`fogOption()`）压缩上千行选项声明样板。

## 8. API
非前置库，但对外扩展点有两个：`sodium:config_api_user` 声明 OwnModOptions / `registerOptionReplacement`；其他 mod 通过自身元数据的 `sodium-extra:options` 布尔表覆盖 mixin 开关。
