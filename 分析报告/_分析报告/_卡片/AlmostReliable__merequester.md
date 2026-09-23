# ME Requester — 速览卡片

- 仓库: https://github.com/AlmostReliable/merequester
- 出现在整合包: ATM10, 星轨重铸；Modrinth 下载量(参考): 1641811
- 本地源码: `源码库\_参考仓库\_bulk\AlmostReliable__merequester`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: ${modId}, minecraft, neoforge
- 源码规模: 65 个 .java，4,155 行
- 目录特征: Client, Mixin, Network
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/almostreliable/merequester` | 65 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/com/almostreliable/merequester/client/abstraction/AbstractRequesterScreen.java` | 326 |
| `src/main/java/com/almostreliable/merequester/requester/RequesterBlockEntity.java` | 285 |
| `src/main/java/com/almostreliable/merequester/requester/Request.java` | 232 |
| `src/main/java/com/almostreliable/merequester/client/RequesterTerminalScreen.java` | 197 |
| `src/main/java/com/almostreliable/merequester/requester/StorageManager.java` | 192 |
| `src/main/java/com/almostreliable/merequester/client/widgets/NumberField.java` | 187 |
| `src/main/java/com/almostreliable/merequester/requester/abstraction/AbstractRequesterMenu.java` | 171 |
| `src/main/java/com/almostreliable/merequester/core/ModRegistration.java` | 169 |
| `src/main/java/com/almostreliable/merequester/client/widgets/RequestWidget.java` | 144 |
| `src/main/java/com/almostreliable/merequester/terminal/RequesterTerminalMenu.java` | 142 |
| `src/main/java/com/almostreliable/merequester/compat/wtlib/WirelessTerminalCompat.java` | 131 |
| `src/main/java/com/almostreliable/merequester/client/widgets/StatusDisplay.java` | 111 |
| `src/main/java/com/almostreliable/merequester/requester/RequestManager.java` | 108 |
| `src/main/java/com/almostreliable/merequester/client/RequestSlot.java` | 93 |
| `src/main/java/com/almostreliable/merequester/client/RequesterScreen.java` | 83 |