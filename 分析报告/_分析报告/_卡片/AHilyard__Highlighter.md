# Item Highlighter — 速览卡片

- 仓库: https://github.com/AHilyard/Highlighter
- 出现在整合包: 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 16642517
- 本地源码: `源码库\_参考仓库\_bulk\AHilyard__Highlighter`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=architectury，工程结构=multiloader；mod_id: ?
- 源码规模: 12 个 .java，543 行
- 目录特征: Client, Config, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/anthonyhilyard/highlighter` | 12 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/com/anthonyhilyard/highlighter/Highlighter.java` | 202 |
| `common/src/main/java/com/anthonyhilyard/highlighter/config/HighlighterConfig.java` | 72 |
| `fabric/src/main/java/com/anthonyhilyard/highlighter/fabric/mixin/AbstractContainerScreenMixin.java` | 37 |
| `forge/src/main/java/com/anthonyhilyard/highlighter/forge/mixin/AbstractContainerScreenMixin.java` | 37 |
| `common/src/main/java/com/anthonyhilyard/highlighter/mixin/GuiMixin.java` | 36 |
| `neoforge/src/main/java/com/anthonyhilyard/highlighter/neoforge/mixin/AbstractContainerScreenMixin.java` | 36 |
| `common/src/main/java/com/anthonyhilyard/highlighter/mixin/InventoryScreenMixin.java` | 31 |
| `common/src/main/java/com/anthonyhilyard/highlighter/mixin/AbstractContainerMenuMixin.java` | 24 |
| `forge/src/main/java/com/anthonyhilyard/highlighter/forge/client/HighlighterForgeClient.java` | 19 |
| `forge/src/main/java/com/anthonyhilyard/highlighter/forge/HighlighterForge.java` | 17 |
| `neoforge/src/main/java/com/anthonyhilyard/highlighter/neoforge/client/HighlighterNeoForgeClient.java` | 17 |
| `fabric/src/main/java/com/anthonyhilyard/highlighter/fabric/HighlighterFabric.java` | 15 |