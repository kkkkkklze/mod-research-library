# Octo-Studios/octo-lib 源码分析报告

## 1. 基本信息
- Mod 名：OctoLib；mod_id `octolib`；作者 OctoStudios；版本 0.6.2（`gradle.properties:7`）
- 目标 MC / 加载器：MC 1.21（`gradle.properties:16`），三平台 Fabric + NeoForge + Quilt（`enabled_platforms = fabric,neoforge,quilt`），跨平台层用 Architectury API 13.0.6（fabric_loader 0.15.11 / fabric_api 0.100.8+1.21 / neoforge 21.0.148 / quilt 0.20.2）
- Gradle：`dev.architectury.loom`（`build.gradle:1`），多模块 common/fabric/neoforge/quilt；Lombok 1.18.32；发布到自建 maven.octo-studios.com
- 许可证：All Rights Reserved（`gradle.properties:11`）
- 编译依赖：Architectury API（neoforge.mods.toml 中 `[[dependencies.octolib]] modId="architectury"` required）、Minecraft、Loader；本仓库快照内**未见 fabric.mod.json**（architectury 工程中缺失，疑为快照/构建生成，未确认）
- 它是其它 mod 的**前置库**：immersive-ui 依赖 `octolib 0.6.0.3+1.21`

## 2. 源码规模与包结构
- 134 个 `.java`，共 7795 行（`find . -name '*.java' -exec wc -l {} +`）
- 主要包（第 3 层，文件数）：`module/config/cfgbuilder`(11)、`module/particle/trail`(10)、`mixin`(9)、`util`(7)、`module/config/{cfgbuilder/scalar,util}`(7+7)、`client/animation`(7)、`module/config/annotation*`(6+5)、`module/config/impl`(5)、`client/particle`(5)、`client/screen/widget`(4)
- 最大文件：`TrailProvider.java`(362)、`module/config/util/ConstructorExt.java`(301)、`cfgbuilder/CompoundEntry.java`(279)、`RepresenterExt.java`(268)、`module/chromatic_aberration/ChromaticAberration.java`(261)、`client/animation/Tween.java`(256)、`util/OctoColor.java`(212)、`module/config/ConfigManager.java`(211)

## 3. 入口与注册
- 公共入口 `common/.../OctoLib.java:16` `OctoLib.init()`：注册命令（`CommandRegistrationEvent.EVENT.register(OctolibCommand::register)`）、事件（`PlayerEvent.PLAYER_JOIN.register(ConfigManager::syncConfigs)` 玩家进服自动同步服务端配置）、`OctolibNetwork.init()`
- 平台壳：`fabric/.../OctoLibFabric.java`（ModInitializer）、`neoforge/.../OctoLibNeoForge.java`（`@Mod(OctoLib.MODID)`，构造中判 `FMLEnvironment.dist == Dist.CLIENT` 再起客户端）、`quilt/.../OctoLibQuilt.java`
- 客户端 `OctoLibClient.init()`：注册 `ClientTickEvent.CLIENT_LEVEL_PRE -> OctoRenderManager::clientTick`、`CLIENT_PLAYER_QUIT -> worldExit`，`OctoLibPostEffects.register(ChromaticAberrationPostEffect::new)`，`TweenSystem.init()`
- **无 DeferredRegister / Registrate**：库不注册方块物品，注册全部是"自建静态注册表 + Architectury 事件"（`OctolibNetwork`、`OctoLibPostEffects`、`EntityTrailRegistry`、`ParticleTrailRegistry`）

## 4. 核心系统
1. **注解式配置系统**（`module/config/`，最大子系统，约 40 文件）
   - 职责：用 Java 字段定义配置并读写 JSON5/多文件，服务端向客户端同步
   - `ConfigManager.java:35` `Map<String, OctoConfig> CONFIG_MAP = new ConcurrentHashMap<>()`；`ConfigManager.java:37` `IdentityHashMap<Class<? extends Annotation>, Pair<AnnotationConfigFactory<?>, ConfigNameGetter<?>>> ANNOTATION_CONFIG_FACTORIES`（注解→工厂可扩展）；`registerConfigFactory/registerConfigPackage/registerConfig`；`ConfigUtils.registerFieldConfig` 反射读静态字段注解并注册
   - 配置树抽象成 `cfgbuilder`（`ConfigEntry`/`CompoundEntry`/`ObjectEntry`/`ListEntry`/`scalar/*`），序列化靠 `JanksonOps`+`RepresenterExt`/`ConstructorExt` 二次注入；`IConfigFileLoader.SOLID`/`FileSpread` 两种落盘策略；`OctoConfig.getSide()` 返回 `ConfigSide.SERVER|CLIENT`
   - 同步策略：`ConfigManager.syncConfig(ServerPlayer,path)` → `SyncConfigPacket`（整个配置文件字符串 + path，`SyncConfigPacket.java:27` 构造时 `ConfigManager.saveAsString`），客户端 `reloadStringConfig` 就地重载
2. **网络层**（`module/network/`）
   - `OctolibNetwork.java:25` `registerS2C` 按 `Platform.getEnv()==EnvType.SERVER` 分流：服务端只 `registerS2CPayloadType`，客户端才 `registerReceiver`（Architectury `NetworkManager`）
   - `Packet.java` 抽象基类：`handle(context)` 按 env 分派 `handleClient/handleServer`（`@Environment(EnvType.CLIENT)`），`createType/createCodec` 静态工厂；走 1.21 `CustomPacketPayload`+`StreamCodec`
3. **补间动画**（`client/animation/`）
   - `Tween.java` 链式 API：`Tween.create().tweenProperty(target,"x",to,duration).setEase(...).setTransitionType(...)`；`tweenInterval/tweenRunnable/tweenMethod` 四类 `Tweener`
   - `TweenSystem.java:12` `List<Tween> TWEENS`+`ConcurrentLinkedQueue<Tween> PENDING`（跨线程安全入队），内置 `RenderThreadExecutor`/`ServerThreadExecutor` 各自 Runnable 队列；时间源 `OctoLibClient.DELTA_NANOS/getDeltaTime()`
4. **UI 粒子**（`client/particle/`）
   - `UIParticle` 支持 `Layer`、`Texture2D`（图集偏移）、颜色渐变 `setColors(OctoColor...)`、混合模式 `enableBlend/setBlendFunc`
   - `ParticleSystem.java:14` `GUI_PARTICLES` + `SCREEN_PARTICLES = new WeakHashMap<Screen, List<UIParticle>>`（按屏分流，弱引用防泄漏）；渲染挂点靠 mixin：`GuiMixin.render@RETURN`、`ScreenMixin.render@RETURN`（跳过 `AbstractContainerScreen`）、世界粒子靠 `ParticleEngineMixin.createParticle@RETURN`
5. **拖尾系统**（`module/particle/trail/`，配合 `module/particle/RenderProvider`）
   - 泛型自引用接口 `RenderProvider<P extends RenderProvider<P,B>, B extends RenderBuffer<P,B>>`
   - `TrailProvider` 是"模板方法"教科书：20+ 个可覆写 getter（`getTrailMaxLength/getTrailFadeInColor/getTrailFadeOutColor/getTrailScale/getTrailSamplesPerTick/getTrailFaces/getTrailInterpolationPoints/getTrailMaxAgeTicks...`），注册表 `EntityTrailRegistry.registerProvider(EntityType, Supplier)` / `ParticleTrailRegistry.registerProvider(ParticleType, ...)`
6. **后处理与画面效果**
   - `module/post_effect/PostEffect.java`（`getPath()` 指向 shader json、`getStage()`=`RenderStage.SCREEN`）；`OctoLibPostEffects` 用 `Map<ResourceLocation, Supplier<PostEffect>>` 延迟实例化
   - `mixin/post_effect/GameRendererMixin.java:36` 在 `render` 的 `RenderTarget.bindWrite` 前注入、`:41` TAIL、`:46` `resize(II)V` TAIL（重建后需重载后处理）
   - 色差：`ChromaticAberrationManager.CHROMATIC_ABERRATIONS Map<UUID, ChromaticAberration>`、`add/addForPlayer`，配套 `S2CChromaticAberrationPacket`；屏幕抖动：`ShakeSystem.ACTIVE_SHAKES ConcurrentHashMap<Shakeable,ShakeData>`

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：见 4.2；S2C 为主（config_sync、test_screen、chromatic_aberration），`registerC2S` 已预留
- 配置：见 4.1，是仓库最重的数据驱动子系统；自定义注解可通过 `ConfigManager.registerConfigFactory` 与 `registerConfigProvider(location, ConfigProvider)` 扩展
- 数据驱动：无（不读 datapack JSON）
- datagen：无（无 data 生成器类/datagen 包）

## 6. Mixin
- 配置：`common/src/main/resources/octolib-common.mixins.json`（client 全量）、`fabric/src/main/resources/octolib-fabric.mixins.json`、`quilt/.../octolib-quilt.mixins.json`（注意 quilt 的 `compatibilityLevel` 仍写 `JAVA_17`，与另两个 JAVA_21 不一致）
- 代表性 hook：`ScreenMixin`→`Screen.render@RETURN`；`GuiMixin`→`Gui.render@RETURN`；`AbstractWidgetMixin`→`clicked@RETURN(cancellable)`、`render` 中 `PUTFIELD isHovered` 用 `@Redirect` 拦截、`getX/getY@HEAD(cancellable)`；`AbstractWidgetAccessor`→`@Accessor("x"/"y")`；`ClientLevelMixin`→`ClientLevel.addEntity@TAIL`；`GameRendererMixin`→`render` 中 `INVOKE Minecraft.isGameLoadFinished`；`MinecraftMixin`→`runTick@HEAD/@TAIL`、`tick` 中 `INVOKE Gui.tick`；`ParticleEngineMixin`→`createParticle@RETURN`

## 7. 值得学的 5 条具体做法
1. 用"注解→工厂"注册表把配置类型做成可扩展：`IdentityHashMap<Annotation, Pair<Factory, NameGetter>>`（`module/config/ConfigManager.java:37,84`），外部 mod 可加自己的注解语义 —— 适合做前置库给下游扩展点。
2. 配置同步直接传"序列化后的配置文件字符串"而不是逐字段同步（`SyncConfigPacket.java:27`），客户端 `reloadStringConfig` 复用同一套加载管线，省掉两套 DTO —— 适合字段多、结构会变的配置。
3. 平台差异收敛在一处：`OctolibNetwork.registerS2C` 内用 `Platform.getEnv()` 分支决定"注册 payload 还是注册 receiver"（`module/network/OctolibNetwork.java:30`）—— 三平台共用一套网络代码的省事写法。
4. 按 Screen 分桶 + WeakHashMap 存 UI 粒子（`client/particle/ParticleSystem.java:15`），并让 mixin 跳过 `AbstractContainerScreen`（`mixin/ScreenMixin.java:22`）避免与容器屏渲染重复 —— UI 特效类 mod 直接可抄。
5. 用"泛型自引用 + 纯 getter 模板"设计拖尾（`module/particle/trail/TrailProvider.java:21`）：所有参数都做成可覆写方法而非构造参数，子类只改自己关心的几项 —— 想把一套渲染效果开放给一堆实体/粒子类型时非常合适。

## 8. 公开 API 与接入方式（库/前置 mod）
- 公共 API 包根：`it.hurts.octostudios.octolib`（核心）+ `it.hurts.octostudios.octolib.module.*` + `it.hurts.octostudios.octolib.client.*`（无独立 `api` 包，公共类即 API）
- 扩展点接口：
  - 配置：`module/config/impl/OctoConfig`（`prepareData/onLoadObject/getLoader/getSide`）、注解 `module/config/annotation/{Config,ObjectConfig,Prop,TypeProp,CfgConstructor,IgnoreProp}`、`module/config/provider/ConfigProvider`、`module/config/loader/IConfigFileLoader`、`ConfigManager.registerConfig(location, config)`
  - 配置工厂/命名：`annotation/registration/AnnotationConfigFactory`、`ConfigNameGetter`
  - 网络：`module/network/Packet`（继承后 `createType/createCodec`，`handleClient/handleServer`）
  - 渲染：`module/particle/RenderProvider`+`RenderBuffer`、`module/post_effect/PostEffect`、`client/particle/UIParticle`
- 外部 mod 接入示例（实测自 immersive-ui）：自己实现 `OctoConfig` 的类 + `@Prop` 字段，然后 Fabric `ModInitializer.onInitialize` 或 NeoForge `FMLCommonSetupEvent` 里 `ConfigManager.registerConfig("modid", CONFIG)`；库入口 `OctoLib.init()` 由本库自身加载，下游无需调用
