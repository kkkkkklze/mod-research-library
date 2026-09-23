# Waystones: Sable (Create Aeronautics Addon) — 速览卡片

- 仓库: https://github.com/SShakusora/WaystonesSable
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 181575
- 本地源码: `源码库\_参考仓库\_bulk\SShakusora__WaystonesSable`
- 目标版本: MC 1.21.1 / NeoForge 21.1.228 / Forge - / Fabric -；mod 版本 1.0.8-SNAPSHOT
- 构建: 插件=moddev，工程结构=single；mod_id: waystonessable
- 源码规模: 29 个 .java，4,098 行
- 目录特征: Client, Command, Mixin, Network

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/sshakusora/waystonessable` | 29 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/com/sshakusora/waystonessable/compat/SableWaystoneCompat.java` | 990 |
| `src/main/java/com/sshakusora/waystonessable/gametest/SubLevelWaystoneUnloadTest.java` | 762 |
| `src/main/java/com/sshakusora/waystonessable/compat/SableWaystoneEventHandler.java` | 289 |
| `src/main/java/com/sshakusora/waystonessable/mixin/WaystonesSableMixinPlugin.java` | 283 |
| `src/main/java/com/sshakusora/waystonessable/gametest/SubLevelClassificationBenchmark.java` | 207 |
| `src/main/java/com/sshakusora/waystonessable/gametest/SubLevelWaystoneTestSupport.java` | 207 |
| `src/main/java/com/sshakusora/waystonessable/gametest/WaystoneApiCompatibilityTest.java` | 184 |
| `src/main/java/com/sshakusora/waystonessable/compat/WaystonePositionSnapshotSavedData.java` | 154 |
| `src/main/java/com/sshakusora/waystonessable/gametest/SubLevelWaystonePlacementTest.java` | 103 |
| `src/main/java/com/sshakusora/waystonessable/gametest/SubLevelWaystoneAssemblyTest.java` | 85 |
| `src/main/java/com/sshakusora/waystonessable/compat/SableTrackingPointerSync.java` | 83 |
| `src/main/java/com/sshakusora/waystonessable/command/ActivateAllWaystonesCommand.java` | 73 |
| `src/main/java/com/sshakusora/waystonessable/network/SableTeleportPayload.java` | 68 |
| `src/main/java/com/sshakusora/waystonessable/mixin/SubLevelAssemblyHelperMixin.java` | 62 |
| `src/main/java/com/sshakusora/waystonessable/mixin/client/ClientPacketListenerMixin.java` | 61 |