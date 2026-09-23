# Cheaterpaul/fallingleaves 源码分析

## 1. 基本信息

- Mod 名：FallingLeaves / mod_id：`fallingleaves` / 作者：Cheaterpaul（原 Fabric 版作者为 Fourmisain、BrekiTomasson、RandomMcSomethin，见 `gradle.properties` credits）
- 目标：NeoForge `26.1.2.71`、MC `26.1.2`、Java 25（`build.gradle` 中 `JavaLanguageVersion.of(25)`）、Parchment 未显式配置
- Gradle 插件：`net.neoforged.moddev` 2.0.141，`java-library` + `maven-publish`；curse.maven 仓库仅用于可选的 SereneSeasons/GlitchCore（依赖被注释，`build.gradle:89-92`）
- 许可证：LGPL-3.0。纯客户端（`@Mod(dist = Dist.CLIENT)`，`FallingLeavesMod.java:21`）
- 依赖：仅 NeoForge/MC，无硬性前置（SereneSeasons 集成源码存在但被 `sourceSets.main.java.exclude("**/serene/*")` 与注释屏蔽）

## 2. 源码规模与包结构

- 48 个 `.java`，共 2410 行
- 包（`de/cheaterpaul/fallingleaves/`）：`mixin`（含 `decay`/`leaves`/`snow`/`wind` 子包共 8 文件）、`data`（`generator`/`provider` 5）、`leaves/mod`（`types`/`util` 6）、`wind`（`math` 5）、`seasons`（`serene` 3）、`config`（4）、`event`（`attack`/`leaves`/`wind` 4）
- 最大文件：`leaves/mod/FallingLeafParticle.java` 260、`wind/Wind.java` 144、`leaves/mod/util/LeafHelper.java` 133、`data/generator/LeafSettingGenerator.java` 109、`wind/WindState.java` 101、`leaves/mod/util/TextureCache.java` 99

## 3. 入口与注册

主类 `src/main/java/de/cheaterpaul/fallingleaves/FallingLeavesMod.java:25-28`：仅两行——注册 CLIENT 配置与 `IConfigScreenFactory`（NeoForge 自动配置界面）。所有实际初始化用 `@EventBusSubscriber(modid, value = Dist.CLIENT)` + 静态 `@SubscribeEvent`：`data/LeafLoader.java:24-26` 注册 `LeafProvider` 重载监听、48-51 注册两个 datagen provider；`config/Config.java:31-34` 在 `ModConfigEvent` 时同步配置对象。

## 4. 核心系统

1. **数据驱动的树叶配置**（`data/provider/LeafProvider.java:44-88`，单一 `PreparableReloadListener` 串联三方加载）：并行加载 `LeafSettingProvider`（`fallingleaves/settings/<block>.json`）+ `LeafTypeProvider`（`fallingleaves/types/*.json`）+ 自建贴图图集 `RenderSettings.LEAVES_ATLAS`，最后在 `SpriteLoader.Preparations` 上把贴图解析成 `ColoredSpriteProvider.TextureSprite`，缺失贴图优雅降级到 `preparations.missing()`。运行时查询入口是 `LeafLoader.getOrDefault(block)`（`data/LeafLoader.java:37-45`，未知方块回落到 `minecraft:oak_leaves`）。
2. **Codec 定义的类型系统**（`leaves/mod/types/LeafType.java:13-94`）：`LeafType(textures, spawnModifier, sizeModifier, lifeSpanModifier, seasonModifier)`；`Texture` 与 `Season` 都用 `NeoForgeExtraCodecs.withAlternative` 支持「简写形式（字符串/单浮点）」与「完整对象」双写法。
3. **风力系统**（`wind/Wind.java`，`wind/WindState.java`）：三层 `SmoothNoise`（风速 2s、风向趋势 30min、风向抖动 10s）叠加，5 tick 更新一次（`WIND_UPDATE_INTERVAL`，`Wind.java:31-48`）；阵风用 `gustStrength/gustDuration/gustFadeTime` 做淡入淡出；`WindState` 按天气在 `StateGroup` 之间随机切换，每 6 分钟换一次状态，雷暴强制 STORM。
4. **树叶生成与配色**（`leaves/mod/ModLeavesSpawner.java`）：`leafChance` 由 `leafType.spawnModifier * setting.spawnRate * 配置叶子速率 * 季节 modifier` 连乘（83-90）；生成前用 AABB + `getBlockCollisions` 检查下方 `minimumFreeSpaceBelow` 是否留有空隙（71-81）。
5. **运行时贴图取色**（`leaves/mod/util/LeafHelper.java:26-87`）：取方块模型 DOWN 面的 `materialInfo().sprite()`，读取 `NativeImage` 像素（经 `mixin/NativeImageAccessor` 拿裸指针 + `MemoryUtil.memGetInt` 累加非透明像素算均值），再乘 `level.getBlockTint(..., BiomeColors.FOLIAGE_COLOR_RESOLVER)`；纹理色与「纹理+群系染色」双层缓存（`TextureCache`）。
6. **季节扩展点**：`seasons/ISeasonProvider.java`（`getCurrentSeason`/`getSeasonModifier`，`DEFAULT` 实现返回 1f），`seasons/serene/SereneSeasonProvider.java` 为 SereneSeasons 适配（当前被注释停用），`Leaves.checkSpawner` 在 vanilla/mod 两套 spawner 间切换（`leaves/Leaves.java:31-38`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包，纯客户端表现。
- 数据驱动：资源包路径 `fallingleaves/settings/*.json`（`LeafSetting` = leafType + spawnRate）与 `fallingleaves/types/*.json`（`LeafType`）；由 `LeafProvider` 统一加载。
- 配置：NeoForge `ModConfigSpec`（CLIENT），`config/Config.java:27-46` 用 `new ModConfigSpec.Builder().configure(Config::new)` 把 leaves/wind/snow 三段拆成独立类（`Leaves`/`Wind`/`Snow`），每段带 `translation` 键。
- datagen：有。`LeafSettingGenerator.java:55-108` 直接硬编码原版 + BYG/Terrestria/Traverse/BOP 等十几个模组的树叶设置；`LeafTypeGenerator` 生成类型定义；均在 `@EventBusSubscriber` 里挂 `GatherDataEvent.Client`。

## 6. Mixin

配置 `src/main/resources/fallingleaves.mixins.json`（含 refmap，common 两项 + client 六项），`compatibilityLevel: JAVA_8`：

- `mixin/leaves/LeavesBlockMixin.java:36` — `LeavesBlock.animateTick` 的 `@WrapOperation` 改写 `makeFallingLeavesParticles` 调用（这是 NeoForge 1.21.5+ 新加的原版方法，直接换实现而非覆盖）
- `mixin/decay/ClientLevelMixin.java:28` — `ClientLevel.addDestroyBlockEffect` HEAD：叶子被破坏时补发粒子
- `mixin/wind/FallingLeavesParticleMixin.java:28,33` — 原版落叶粒子 `<init>`/`tick` 注入风速
- `mixin/wind/ClientLevelMixin.java:25`、`mixin/leaves/ClientLevelMixin.java`、`mixin/snow/ClientLevelMixin.java` — 给 `ClientLevel` 挂 `IWindLevel`/`ILeavesLevel`/`ISnowLevel` 接口（`mixinhelpers` 式接口注入）
- `mixin/NativeImageAccessor.java` — `@Accessor` 取 `NativeImage.pixels`

## 7. 值得学的 5 条做法

1. 一个 `PreparableReloadListener` 里用 `CompletableFuture.allOf(...).thenCompose(barrier::wait)` 并行加载多份数据 + 贴图图集，最后统一构建不可变映射（`data/provider/LeafProvider.java:44-88`）。
2. 用 `withAlternative(简写codec, 完整codec)` 让手写/生成的数据文件既简洁又表达完整（`leaves/mod/types/LeafType.java:45-55,80-89`）。
3. 未知值回落默认：`getOrDefault` 让任何未配置的模组树叶都能工作（`data/LeafLoader.java:37-45`）。
4. 贴图取色用裸内存遍历（`MemoryUtil.memGetInt`）替代 `getPixelColor`，并加两层缓存（`leaves/mod/util/LeafHelper.java:89-132`）。
5. 把「生成策略」抽象成 `ILeavesSpawner`（vanilla 版 / mod 版），用配置一键切换实现（`leaves/Leaves.java:31-38`、`leaves/vanilla/VanillaLeavesSpawner.java`）。

## 8. 库/API 说明

非库 Mod。可扩展点：资源包 JSON（`fallingleaves/settings`、`fallingleaves/types`）与 `ISeasonProvider` 接口（`seasons/ISeasonProvider.java`）供季节模组接入。
