# Ping System — 速览卡片

- 仓库: https://github.com/sam-makes-stuff/ping_system
- 出现在整合包: FIDR暗涌；Modrinth 下载量(参考): 1623
- 本地源码: `源码库\_参考仓库\_bulk\sam-makes-stuff__ping_system`
- 目标版本: MC 1.20.1 / NeoForge - / Forge 47.3.0 / Fabric -；mod 版本 1.01-1.20.1
- 构建: 插件=forgegradle，工程结构=single；mod_id: ping_system
- 源码规模: 19 个 .java，1,749 行
- 目录特征: Client, Config, Network

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `net/sam/ping_system` | 19 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/net/sam/ping_system/client/overlay/PingHandler.java` | 401 |
| `src/main/java/net/sam/ping_system/render/CustomHudRenderer.java` | 285 |
| `src/main/java/net/sam/ping_system/networking/ClientPacketHandler.java` | 194 |
| `src/main/java/net/sam/ping_system/client/overlay/Ping.java` | 124 |
| `src/main/java/net/sam/ping_system/client/overlay/PingWheelOverlay.java` | 110 |
| `src/main/java/net/sam/ping_system/client/ClientInputHandler.java` | 77 |
| `src/main/java/net/sam/ping_system/networking/packets/S2CSendPingPacket.java` | 68 |
| `src/main/java/net/sam/ping_system/networking/ModPackets.java` | 66 |
| `src/main/java/net/sam/ping_system/networking/packets/C2SRequestToPingPacket.java` | 60 |
| `src/main/java/net/sam/ping_system/PingSystem.java` | 54 |
| `src/main/java/net/sam/ping_system/networking/ServerPacketHandler.java` | 54 |
| `src/main/java/net/sam/ping_system/client/overlay/PingGhost.java` | 49 |
| `src/main/java/net/sam/ping_system/util/ConfigUtils.java` | 43 |
| `src/main/java/net/sam/ping_system/config/ServerConfig.java` | 29 |
| `src/main/java/net/sam/ping_system/sound/ModSounds.java` | 29 |