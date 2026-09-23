# Embeddium — 速览卡片

- 仓库: https://github.com/FiniteReality/embeddium
- 出现在整合包: FIDR暗涌；Modrinth 下载量(参考): 34553725
- 本地源码: `源码库\_参考仓库\_bulk\FiniteReality__embeddium`
- 目标版本: MC 1.21.4 / NeoForge - / Forge 21.4.5-beta / Fabric 0.16.9；mod 版本 1.0.11
- 构建: 插件=?，工程结构=single；mod_id: embeddium, neoforge, sodium
- 源码规模: 552 个 .java，36,788 行
- 主类候选: `src/fabric/java/net/neoforged/fml/common/Mod.java` (13 行)
- 目录特征: API, Client, Config, Data, Entity, Mixin, Network, Worldgen
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `org/embeddedt/embeddium` | 503 |
| `net/neoforged/neoforge` | 29 |
| `net/neoforged/fml` | 17 |
| `net/neoforged/neoforgespi` | 1 |
| `me/jellysquid/mods` | 1 |
| `org/embeddedt/embeddium_integrity` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/org/embeddedt/embeddium/impl/render/chunk/RenderSectionManager.java` | 812 |
| `src/main/java/org/embeddedt/embeddium/impl/render/EmbeddiumWorldRenderer.java` | 651 |
| `src/main/java/org/embeddedt/embeddium/impl/render/chunk/compile/pipeline/FluidRenderer.java` | 568 |
| `src/main/java/org/embeddedt/embeddium/impl/render/immediate/CloudRenderer.java` | 504 |
| `src/main/java/org/embeddedt/embeddium/impl/gui/EmbeddiumGameOptionPages.java` | 467 |
| `src/main/java/org/embeddedt/embeddium/impl/world/WorldSlice.java` | 466 |
| `src/main/java/org/embeddedt/embeddium/impl/gui/EmbeddiumVideoOptionsScreen.java` | 451 |
| `src/main/java/org/embeddedt/embeddium/impl/gl/arena/GlBufferArena.java` | 399 |
| `src/main/java/org/embeddedt/embeddium/impl/render/chunk/RenderSection.java` | 396 |
| `src/main/java/org/embeddedt/embeddium/impl/render/chunk/compile/pipeline/BlockRenderer.java` | 366 |
| `src/main/java/org/embeddedt/embeddium/impl/render/chunk/occlusion/OcclusionCuller.java` | 331 |
| `src/main/java/org/embeddedt/embeddium/impl/mixin/MixinConfig.java` | 308 |
| `src/main/java/org/embeddedt/embeddium/impl/model/light/smooth/SmoothLightPipeline.java` | 298 |
| `src/main/java/org/embeddedt/embeddium/impl/gl/device/GLRenderDevice.java` | 295 |
| `src/main/java/org/embeddedt/embeddium/impl/render/chunk/DefaultChunkRenderer.java` | 291 |