# FionaTheMortal / better-biome-blend 源码分析

## 1. 基本信息
- Mod 名：Better Biome Blend；mod_id：`betterbiomeblend`（`src/main/resources/META-INF/mods.toml`）
- 作者：FionaTheMortal；版本 `1.3.5-forge`（`gradle.properties`）
- 目标：MC **1.18.2** + **Forge 40.0.1**，Java 17，mappings `official`；纯客户端 mod（`mods.toml` 依赖 minecraft `[1.18.1,1.19)`）
- Gradle：ForgeGradle 5.1.+，mixingradle 0.7.+，`jar.finalizedBy('reobfJar')`
- 许可证：`license="All rights reserved"`（闭源，仅可读不可抄）
- 依赖：无运行时依赖；唯一编译依赖是自制的 `compileOnly files("libs/better-biome-blend-sodium-api-0.4.1-dev.jar")`（`build.gradle`）——把 Sodium 内部类抽成独立 API jar 供 `compileOnly`
- `mods.toml` 的 `[[dependencies.examplemod]]` 段名未改名（模板残留）

## 2. 源码规模与包结构
实测：**24 个 .java，3382 行**（`find . -name '*.java' -exec wc -l {} +`）。
- `fionathemortal.betterbiomeblend`（2）：`BetterBiomeBlend`、`BetterBiomeBlendClient`
- `.common`（9）：`ColorBlending`、`ColorCaching`、`BlendCache`、`BlendChunk`、`Color`、`ColorBlendBuffer`、`BiomeColorType`、`CustomColorResolverCompatibility`、`Random`
- `.common.cache`（6）：`SliceCache`、`ColorCache`、`BiomeCache`、`Slice`、`ColorSlice`、`BiomeSlice`
- `.common.debug`（3）；`.mixin`（3）；`.sodium`（1）
- 最大文件：`ColorBlending.java` 865 > `SodiumColorBlending.java` 370 > `cache/SliceCache.java` 324 > `BlendCache.java` 308 > `BetterBiomeBlendClient.java` 294

## 3. 入口与注册
`BetterBiomeBlend.java:13-40`：`@Mod(MOD_ID)` + `DistExecutor.unsafeRunWhenOn(Dist.CLIENT, ...)` 注册 `BetterBiomeBlendClient` 到 `MinecraftForge.EVENT_BUS`，并用 `IExtensionPoint.DisplayTest` 声明 `"client-only"`。**无任何注册表内容（无 DeferredRegister、无物品/方块）**，mod 完全由 mixin 生效。

## 4. 核心系统
1. **原版颜色查询覆写**：`mixin/MixinClientWorld.java:104-192` 用 `@Overwrite` 替换 `ClientLevel#getBlockTint(BlockPos, ColorResolver)`。先把 resolver 映射为 `BiomeColorType`（GRASS/WATER/FOLIAGE/其它走 `CustomColorResolverCompatibility.getColorType`），再取对应的 4 个 `ThreadLocal<BlendChunk>`。
2. **三级分块缓存**：`BlendCache`(2048) / `ColorCache`(512) / `BiomeCache`(32) 皆继承式复用 `common/cache/SliceCache.java`，内部 `ReentrantLock + Long2ObjectLinkedOpenHashMap`（LRU）+ `Long2ObjectOpenHashMap invalidationHash` 双向链表；`BlendChunk` 带引用计数与 `freeStack` 池化（`BlendCache.java:49-72`）。
3. **缓存键位打包**：`ColorCaching.getChunkKey` 把 chunkZ/chunkX 各 26 位、chunkY 5 位、colorType 压进一个 `long`（`ColorCaching.java:14-22`）。
4. **失效策略**：`@Inject(method="clearTintCaches", at=HEAD)` 全清；`@Inject(method="onChunkLoaded", at=HEAD)` 按 ChunkPos `invalidateChunk` + `invalidateSmallNeighborhood`（`MixinClientWorld.java:104-127`）。
5. **混合算法**：`ColorBlending.java` 常量 `SECTION_SIZE_LOG2=2`、`BLEND_BUFFER_DIM=11`、固定 `byte[]` 缓冲与 `freeBlendBuffers` 栈复用；采样抖动用整数种子 `SAMPLE_SEED_X=1664525 / Y=214013 / Z=16807`（`ColorBlending.java:24-41`）——即"扩大半径但按种子抖动采样"以控成本。
6. **Sodium 兼容**：`mixin/MixinBlockColorCache.java:59` 以 `@Overwrite(remap = false)` 替换 sodium 的 `BlockColorCache#getColor`，生成 `byte[3*5*5*5]` 并按 `(4-offsetX/Y/Z)` 三线性权重、**long 打包 RGB 一次性乘加**避免 int 溢出（`MixinBlockColorCache.java:97-135`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无**（无 packet 类、无 SimpleChannel）。
- 配置：**无自有配置**，直接读改原版 `Options.biomeBlendRadius`（`BetterBiomeBlendClient.java:39-96` 自定义 `ProgressOption`）。
- 数据驱动：无。datagen：`build.gradle` 定义了 `data` run（`--mod betterbiomeblend`），但 `src` 下无任何 DataProvider 类，实际未使用。

## 6. Mixin
配置：`src/main/resources/betterbiomeblend.mixins.json`（`required:true`，`client` 列表 3 条，refmap `betterbiomeblend.refmap.json`）+ `META-INF/accesstransformer.cfg`（放开 `OptionsList$Entry`）。
- `AccessorOptionSlider`：`@Mixin(SliderButton.class)` + `@Accessor getOption()`，用于在视频设置界面里按 `Option.BIOME_BLEND_RADIUS` 找到原版滑条行并整体替换（`BetterBiomeBlendClient.java:184-233`）。
- `MixinClientWorld`：目标 `ClientLevel`，hook `clearTintCaches`、`onChunkLoaded`（HEAD 注入）+ `getBlockTint`（Overwrite）。
- `MixinBlockColorCache`：目标 `me.jellysquid.mods.sodium.client.world.biome.BlockColorCache`，`<init>` 的 TAIL 注入存 `slice.getOrigin()` 基准坐标，`getColor` 覆写。

## 7. 值得学的 5 条做法
1. **可选兼容用 compileOnly API jar**：把第三方内部类抽成 `libs/*-sodium-api-*.jar`，`build.gradle` 里 `compileOnly files(...)`，无该 mod 时不加载对应 mixin——做 Create/Sodium 兼容时同法。
2. **ThreadLocal 缓冲块 + 引用计数池**：渲染线程各持 `BlendChunk`，`BlendChunk.acquire/release` + `freeStack` 复用以零 GC（`BlendCache.java`、`ColorCaching.java:27-41`）。
3. **long 位打包做复合缓存键**：`ColorCaching.getChunkKey` 把 x/z/y/类型压进单 long，可直接作 fastutil 长哈希键（`ColorCaching.java:14`）。
4. **对第三方 mod 用 `@Overwrite(remap=false)`，对原版类只用 `@Inject` 做失效**：前者绕开混淆映射名（`MixinBlockColorCache.java:59`），后者风险最小（`MixinClientWorld.java:104`）。
5. **`@Unique` 字段统一前缀**：所有注入成员命名 `betterBiomeBlend$xxx`（`MixinClientWorld.java:41-51`），避免与其它 mixin 冲突。

## 8. 公开 API
无（客户端功能 mod，非库；`libs/` 内 sodium-api jar 是它自己的编译脚手架，不是对外 API）。
