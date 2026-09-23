# Iris Veil Compat — 速览卡片

- 仓库: https://github.com/leon-o/iris-veil-compat
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 92206
- 本地源码: `源码库\_参考仓库\_bulk\leon-o__iris-veil-compat`
- 目标版本: MC 1.21.1 / NeoForge 21.1.219 / Forge 1.0.6 / Fabric -；mod 版本 0.3.0
- 构建: 插件=moddev，工程结构=single；mod_id: irisveil
- 源码规模: 61 个 .java，4,606 行
- 目录特征: API, Client, Entity, Network, Worldgen

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `top/leonx/irisveil` | 42 |
| `dev/ryanhcode/sable` | 5 |
| `net/minecraft/client` | 3 |
| `com/mojang/blaze3d` | 2 |
| `it/unimi/dsi` | 2 |
| `net/irisshaders/iris` | 2 |
| `com/mojang/logging` | 1 |
| `net/minecraft/resources` | 1 |
| `net/minecraft/server` | 1 |
| `net/minecraft/world` | 1 |
| `org/slf4j` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/top/leonx/irisveil/compat/veil/IrisVeilProgramLinker.java` | 571 |
| `src/main/java/top/leonx/irisveil/compat/veil/GlslTransformerVeilPatcher.java` | 447 |
| `src/main/java/top/leonx/irisveil/compat/veil/GlslTransformerVeilFragmentPatcher.java` | 346 |
| `src/main/java/top/leonx/irisveil/compat/veil/IrisVeilShaderCache.java` | 212 |
| `src/test/java/top/leonx/irisveil/compat/veil/GlslTransformerVeilPatcherTest.java` | 198 |
| `src/main/java/top/leonx/irisveil/compat/veil/VeilDitheringPatcher.java` | 193 |
| `src/main/java/top/leonx/irisveil/compat/veil/VeilCompatRegistry.java` | 164 |
| `src/test/java/top/leonx/irisveil/compat/sable/SableShadowCompatTest.java` | 150 |
| `src/main/java/top/leonx/irisveil/compat/veil/mixin/MixinShaderProgramShard.java` | 129 |
| `src/main/java/top/leonx/irisveil/compat/sable/SableShadowBridge.java` | 126 |
| `src/test/java/top/leonx/irisveil/compat/veil/IrisVeilProgramLinkerTest.java` | 116 |
| `src/main/java/top/leonx/irisveil/compat/simulated/SimulatedEndSeaCompat.java` | 111 |
| `src/test/java/top/leonx/irisveil/compat/simulated/SimulatedFirstPersonProjectionTest.java` | 105 |
| `src/main/java/top/leonx/irisveil/mixin/iris/MixinShadowRenderer.java` | 103 |
| `src/test/java/dev/ryanhcode/sable/sublevel/render/dispatcher/SubLevelRenderDispatcher.java` | 99 |