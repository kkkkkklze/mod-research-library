# MCEF (Minecraft Chromium Embedded Framework) — 速览卡片

- 仓库: https://github.com/CinemaMod/mcef
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 725967
- 本地源码: `源码库\_参考仓库\_bulk\CinemaMod__mcef`
- 目标版本: MC 1.21.4 / NeoForge - / Forge - / Fabric 0.16.9；mod 版本 ?
- 构建: 插件=loom，工程结构=single；mod_id: mcef
- 源码规模: 27 个 .java，2,987 行
- 主类候选: `neoforge/src/main/java/com/cinemamod/mcef/example/MCEFExampleMod.java` (53 行)
- 目录特征: Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/cinemamod/mcef` | 27 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/com/cinemamod/mcef/MCEFBrowser.java` | 517 |
| `common/src/main/java/com/cinemamod/mcef/MCEF.java` | 243 |
| `common/src/main/java/com/cinemamod/mcef/MCEFClient.java` | 197 |
| `common/src/main/java/com/cinemamod/mcef/MCEFDownloader.java` | 191 |
| `common/src/main/java/com/cinemamod/mcef/example/ExampleScreen.java` | 161 |
| `common/src/main/java/com/cinemamod/mcef/MCEFSettings.java` | 146 |
| `common/src/main/java/com/cinemamod/mcef/CefUtil.java` | 140 |
| `common/src/main/java/com/cinemamod/mcef/ModScheme.java` | 139 |
| `common/src/main/java/com/cinemamod/mcef/internal/MCEFDownloaderMenu.java` | 136 |
| `common/src/main/java/com/cinemamod/mcef/MCEFDragContext.java` | 129 |
| `common/src/main/java/com/cinemamod/mcef/mixins/CefDownloadMixin.java` | 128 |
| `common/src/main/java/com/cinemamod/mcef/mixins/CefInitMixin.java` | 112 |
| `common/src/main/java/com/cinemamod/mcef/MCEFPlatform.java` | 76 |
| `common/src/main/java/com/cinemamod/mcef/MCEFRenderer.java` | 76 |
| `common/src/main/java/com/cinemamod/mcef/MIMEUtil.java` | 74 |