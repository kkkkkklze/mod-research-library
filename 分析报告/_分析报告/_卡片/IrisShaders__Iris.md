# Iris Shaders — 速览卡片

- 仓库: https://github.com/IrisShaders/Iris
- 出现在整合包: ATM10, 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 174203494
- 本地源码: `源码库\_参考仓库\_bulk\IrisShaders__Iris`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=loom，工程结构=single；mod_id: ?
- 源码规模: 744 个 .java，63,291 行
- 主类候选: `common/src/main/java/net/irisshaders/iris/shaderpack/materialmap/BlockEntry.java` (131 行)
- 目录特征: API, Config, Network

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `net/irisshaders/iris` | 655 |
| `kroppeb/stareval/function` | 23 |
| `de/odysseus/ithaka` | 22 |
| `kroppeb/stareval/element` | 16 |
| `kroppeb/stareval/parser` | 9 |
| `kroppeb/stareval/exception` | 5 |
| `kroppeb/stareval/expression` | 5 |
| `com/seibel/distanthorizons` | 4 |
| `com/terraformersmc/modmenu` | 3 |
| `kroppeb/stareval` | 1 |
| `kroppeb/stareval/resolver` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/net/irisshaders/iris/pipeline/IrisRenderingPipeline.java` | 1395 |
| `common/src/main/java/net/irisshaders/iris/parsing/IrisFunctions.java` | 1213 |
| `common/src/main/java/net/irisshaders/iris/shaderpack/properties/ShaderProperties.java` | 998 |
| `common/src/main/java/net/irisshaders/iris/gl/IrisRenderSystem.java` | 863 |
| `common/src/main/java/net/irisshaders/iris/Iris.java` | 815 |
| `common/src/main/java/net/irisshaders/iris/shadows/ShadowRenderer.java` | 807 |
| `common/src/main/java/net/irisshaders/iris/pipeline/transform/transformer/CompatibilityTransformer.java` | 752 |
| `common/src/main/java/net/irisshaders/iris/gui/screen/ShaderPackScreen.java` | 690 |
| `common/src/main/java/net/irisshaders/iris/shaderpack/ShaderPack.java` | 632 |
| `common/src/main/java/net/irisshaders/iris/shaderpack/option/OptionAnnotatedSource.java` | 567 |
| `common/src/main/java/net/irisshaders/iris/gui/element/ShaderPackSelectionList.java` | 545 |
| `common/src/main/java/net/irisshaders/iris/pipeline/CompositeRenderer.java` | 532 |
| `common/src/main/java/net/irisshaders/iris/vertices/NormalHelper.java` | 523 |
| `common/src/main/java/net/irisshaders/iris/shadows/frustum/advanced/AdvancedShadowCullingFrustum.java` | 509 |
| `common/src/main/java/net/irisshaders/iris/pipeline/transform/transformer/CommonTransformer.java` | 502 |