# FiniteReality/embeddium 源码分析

## 1. 基本信息
- Mod 名：Embeddium；`mod_id=embeddium`（`src/main/resources/META-INF/neoforge.mods.toml`，MODID 常量在 `api/EmbeddiumConstants.java`）；作者 embeddedt，credits "embeddedt, NanoLive, CaffeineMC"。
- 目标：`minecraft_version=1.21.4`、NeoForge `21.4.5-beta`（`gradle.properties`），Java 21、`options.release=21`；同树支持 Fabric（`embeddium.fabric_mode=false` 切换）。
- Gradle：Kotlin DSL；自研插件 `embeddium-platform-selector`（`buildSrc`）二选一加载 `fabric-userdev`(dev.architectury.loom) 或 `neoforge-userdev`(ModDevGradle)，`settings.gradle.kts` 从 prmaven 拉 PR 版 MDG。
- 许可证 LGPL-3.0-only（options 屏部分代码来自 RSO，MIT，见 `src/main/resources/licenses/rso.txt`）。
- 依赖：基于 Sodium 0.5.8 之前最后的 FOSS 代码；`implementation("io.github.llamalad7:mixinextras-neoforge")`；Fabric 模式下 `compileOnly net.fabricmc:fabric-loader` + `fabricCompileOnly` 各 `fabric-*` 模块；`neoforge.mods.toml` 里把 `sodium` 声明为 `incompatible`。

## 2. 规模与包结构
- 552 个 `.java`、总计约 19.7k 行（`xargs wc -l`）；四个 source set：`main` 451 文件、`fabric` 77（31 个 org.embeddedt + 46 个 net.neoforged 兼容层）、`compat` 2、`gametest` 10。
- `main` 分包：`impl/render/chunk` 75、`impl/mixin/features` 59、`impl/mixin/core` 25、`impl/gl/shader` 14、`api` **66**、`impl/gui/*`、`impl/platform/windows` 11。
- 最大文件：`impl/render/chunk/RenderSectionManager.java` 811、`impl/render/EmbeddiumWorldRenderer.java` 650、`impl/render/chunk/compile/pipeline/FluidRenderer.java` 567、`impl/render/immediate/CloudRenderer.java` 503、`impl/gui/EmbeddiumVideoOptionsScreen.java` 450、`impl/mixin/MixinConfig.java` 307。

## 3. 入口与注册
主类 `org.embeddedt.embeddium.impl.Embeddium`（`@Mod(value = MODID, dist = Dist.CLIENT)`，构造函数注入 `IEventBus`）：注册 `IConfigScreenFactory` 扩展点指向 `EmbeddiumVideoOptionsScreen`、静态加载 `EmbeddiumOptions`、`-Dembeddium.enableGameTest=true` 时反射注册 `impl.gametest.content.TestRegistry`（`Embeddium.java:31-51`）。
Fabric 侧入口 `fabric/.../init/EmbeddiumFabricInitializer.java` 实现 `ClientModInitializer`，反射 `new Embeddium(NeoForge.EVENT_BUS)`——**同一主类两平台复用**。无 DeferredRegister/内容注册（纯客户端渲染 mod）。

## 4. 核心系统
1. **移植工程组织（最值得看）**：Fabric 支持不是分支，而是补一套"假 NeoForge"：`src/fabric/java/net/neoforged/**` 手写 `ModLoadingContext`（返回单例）、`FMLJavaModLoadingContext`、`FMLLoader`、`ModList/LoadingModList`、`ModFileInfo`、`ClientHooks`、`ModelData`、`FluidType`、`IConfigScreenFactory`、neoforgespi earlywindow 等；NeoForge 的 `IBlockStateExtension` 之类行为接口改由 Fabric mixin 实现（`impl/mixin/fabric/*`：AABBMixin、RenderTypeMixin、LevelChunkMixin…）+ `fabric/injectors/*Injector` 接口。`main` 代码只依赖 NeoForge 形态的 API，两平台各自满足。
2. **Mixin 动态发现**：`embeddium.mixins.json` 的 `client` 数组是**空的**，`plugin=MixinPlugin`；`MixinPlugin.getMixins()`（`impl/mixin/MixinPlugin.java:141-181`）扫描 mod 文件里 `impl/mixin/{core,modcompat,fabric}` 下的 `.class`、经 `MixinClassValidator` 与配置规则过滤后返回列表；并靠 `System.getProperty("mixin.service")` 是否含 `MixinServiceKnot` 判定运行在 Fabric（同文件 40-56 行），Fabric 上屏蔽 `ChunkRenderTypeSetMixin`。
3. **Mixin 规则配置**：`impl/mixin/MixinConfig.java` 沿用 Sodium 的 `embeddium-mixins.properties`（`ConfigMigrator.handleConfigMigration` 迁移），按包名建规则（`features.render.model.block` …），并**为每个已加载 mod 自动建 `modcompat.<sanitized id>` 规则**（94-102 行），其它 mod 可在自己 mods.toml 用 `[mods."embeddium:options"]` 关 mixin（`JSON_KEY_SODIUM_OPTIONS="embeddium:options"`，24 行、170-204 行），禁用优先于启用。
4. **区块渲染核心**：`impl/render/chunk/RenderSectionManager.java`(811)、`RenderSection.java`、`compile/pipeline/{BlockRenderer,FluidRenderer}.java`、`occlusion/OcclusionCuller.java`、`impl/gl/arena/GlBufferArena.java`（vertex arena）。
5. **平台/环境检查**：`impl/util/PlatformUtil.java`（modPresent/isDevelopmentEnvironment）、`impl/compatibility/{checks,environment,workarounds}`、`EmbeddiumPreLaunch.onPreLaunch()`（由 mixin plugin `onLoad` 调用，做 `GraphicsAdapterProbe`/`EarlyDriverScanner`/`Workarounds.init`）。
6. **防篡改**：`org/embeddedt/embeddium_integrity/MixinTaintDetector.java` + `impl/asm/AnnotationProcessingEngine.java`（`MixinPlugin.postApply` 对 embeddium/sodium 目标类做自定义注解处理）；`MixinPlugin.onLoad` 检测到 `net.caffeinemc.caffeineconfig.AdvancedEmbeddiumHackery` 就报 `ModLoadingIssue`（75-78 行）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无自定义包（客户端 mod）。
- 配置：JSON `embeddium-options.json`，Gson 读写、写临时文件再落盘（`impl/gui/EmbeddiumOptions.java:24,101,118,163`）；旧 properties 由 `impl/config/ConfigMigrator.java` 迁移。
- 选项 UI 框架：`impl/gui/{frame,options,screen,theme,widgets,console}` 自建（基于 RSO），对外暴露构造事件。

## 6. Mixin（统计与代表）
- 配置：`src/main/resources/embeddium.mixins.json`（package `org.embeddedt.embeddium.impl.mixin`，refmap `embeddium-refmap.json`，`overwrites.conformVisibility=true`，plugin + 空 client 列表）。
- mixin 类约 110 个：features 59、core 25、fabric 19、workarounds 2、modcompat 1。代表：`impl/mixin/features/render/entity/cull/EntityRendererMixin`、`impl/mixin/core/model/quad/BakedQuadFactoryMixin`、`impl/mixin/features/textures/mipmaps/SpriteContentsMixin`、`fabric/.../impl/mixin/fabric/RenderTypeMixin`（Fabric 专属）。
- AT/AW：`src/main/resources/META-INF/accesstransformer.cfg`（主）；Fabric 侧由 `GenerateAWFromATTask` 生成 `src/main/resources/embeddium.accesswidener`。

## 7. 移植工程关键机制（buildSrc）
- `embeddium-platform-selector.gradle.kts`：按 `embeddium.fabric_mode` 决定 `fabric-userdev` 或 `neoforge-userdev`。
- `fabric-userdev.gradle.kts`：建 `fabric` source set 并把其 output/classpath 挂到 `main`+`compat`（于是 main 能编译通过 shim）；`useLegacyMixinAp=false`；注册 `AccessTransformerJarProcessor` 处理 AT；`loom.mods` 里登记 main/fabric/compat 三个 source set；任务 `convertTransformerToWidener` 用 loom `MappingTree` 把 AT 的 Mojang 名翻成 intermediary，写进 AW 的 `# embeddium {` … `# }` 包裹块（`GenerateAWFromATTask.java:57-204`）——**一份 AT 同时产出两平台访问扩展**。
- `RemapperPlugin.java`：为 Fabric 依赖引入自定义 attribute `isEmbeddiumDevCompatibleMod` 与 `RemapperTransform`，把 `fabricCompileOnly` 的 Fabric API/mod jar 从 intermediary+官方映射重映射到当前 dev 环境（含映射下载与 `embeddium_remap_cache` 缓存），Magic borrowed from MDG（33-53 行）。
- `neoforge-userdev.gradle.kts`：`main.java.srcDirs("src/gametest/java")` 复用 gametest；runs `client/gameTestClient/gameTestCiClient`（`embeddium.runAutomatedTests`）；`tasks.jar` 排除 `fabric.mod.json`/`embeddium.accesswidener`；排除 NeoForm 仓库的 LWJGL。
- 发布与兼容校验：`apiJar` 任务剔除 `impl/**` 与 `assets/**` 产出 api classifier；`VerifyAPICompat` 任务做二进制 API 兼容检查；`ProjectVersioner` 由 git 状态算版本；`publishMods` 标注 rubidium / textrues-embeddium-options 不兼容。
- `Constants.EXTRA_SOURCE_SETS = List.of("compat")`（`buildSrc/.../Constants.java`），`embeddium-common.gradle.kts` 据此统一建/打包额外 source set。

## 8. 对外 API（库式集成）
`org.embeddedt.embeddium.api` 66 文件：`BlockRendererRegistry`、`MeshAppender`、`ChunkMeshEvent`（静态 `BUS`，带 `Level`+`SectionPos`，文档明确"render 在工作线程，用 `EmbeddiumBlockAndTintGetter`"）、`ChunkDataBuiltEvent`、`OptionPageConstructionEvent`/`OptionGroupConstructionEvent`/`OptionGUIConstructionEvent`、`api/options/**`（Option/OptionStorage/`MinecraftOptionsStorage`/SliderControl/CyclingControl）、`api/eventbus/{EmbeddiumEvent,EventHandlerRegistrar}`（自建轻量事件总线）、`api/math`、`api/memory.MemoryIntrinsics`、`api/render/chunk/EmbeddiumBlockAndTintGetter`、`RenderSectionDistanceFilter(+Event)`、`api/service/**`。与光影 mod 的交互走反射：`impl/render/ShaderModBridge.java` 用 `MethodHandle` 绑定 `net.irisshaders.iris.api.v0.IrisApi#isShaderPackInUse/openMainIrisScreenObj`（即直接兼容 Oculus/Iris，`areShadersEnabled()` 参与顶点格式决策）。

## 9. 值得学的 5 条
1. **跨平台 = 依赖倒置**：主源码只写 NeoForge 形态 API，Fabric 侧补同名 shim + mixin（`src/fabric/java`），避免到处写 `if (platform)`。
2. **一条 AT 双端复用**：AT → AW 自动转换任务（`GenerateAWFromATTask.java`），保证两平台访问扩展不漂移。
3. **mixin 列表代码化发现 + 用户/mod 可配规则**（`MixinPlugin.getMixins()` + `MixinConfig`），可让第三方 mod 精确关掉某个 mixin。
4. **发布两个 jar 面**：`apiJar` 去 impl + `VerifyAPICompat` 卡二进制兼容，库式 mod 的稳定契约。
5. **反射桥接可选依赖**：`ShaderModBridge`、`PlatformUtil.modPresent`，避免硬依赖 Oculus/Nvidium 等。
