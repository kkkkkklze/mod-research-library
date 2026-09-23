# Ritchie's Projectile Library — 速览卡片

- 仓库: https://github.com/Wagers-of-Industrial-Warfare/RitchiesProjectileLib
- 出现在整合包: 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 3226551
- 本地源码: `源码库\_参考仓库\_bulk\Wagers-of-Industrial-Warfare__RitchiesProjectileLib`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=architectury，工程结构=single；mod_id: ?
- 源码规模: 44 个 .java，1,954 行
- 目录特征: Config, Mixin, Network

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `rbasamoyai/ritchiesprojectilelib/network` | 16 |
| `rbasamoyai/ritchiesprojectilelib/effects` | 5 |
| `rbasamoyai/ritchiesprojectilelib/fabric` | 4 |
| `rbasamoyai/ritchiesprojectilelib/forge` | 4 |
| `rbasamoyai/ritchiesprojectilelib/neoforge` | 4 |
| `rbasamoyai/ritchiesprojectilelib` | 4 |
| `rbasamoyai/ritchiesprojectilelib/projectile_burst` | 4 |
| `rbasamoyai/ritchiesprojectilelib/chunkloading` | 1 |
| `rbasamoyai/ritchiesprojectilelib/config` | 1 |
| `rbasamoyai/ritchiesprojectilelib/mixin` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/rbasamoyai/ritchiesprojectilelib/projectile_burst/ProjectileBurst.java` | 175 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/chunkloading/ChunkManager.java` | 150 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/effects/screen_shake/ModScreenShakeHandler.java` | 110 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/RitchiesProjectileLib.java` | 92 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/effects/screen_shake/RPLScreenShakeHandlerClient.java` | 74 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/config/RPLConfigs.java` | 71 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/network/RPLNetwork.java` | 64 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/effects/screen_shake/ScreenShakeEffect.java` | 56 |
| `forge/src/main/java/rbasamoyai/ritchiesprojectilelib/network/forge/RPLNetworkImpl.java` | 55 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/network/RPLClientHandlers.java` | 55 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/network/ClientboundSyncBurstSubProjectilesPacket.java` | 54 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/mixin/ServerEntityMixin.java` | 51 |
| `fabric/src/main/java/rbasamoyai/ritchiesprojectilelib/fabric/RitchiesProjectileLibFabric.java` | 49 |
| `forge/src/main/java/rbasamoyai/ritchiesprojectilelib/forge/RitchiesProjectileLibForge.java` | 49 |
| `src/main/java/rbasamoyai/ritchiesprojectilelib/network/ClientboundPreciseMotionSyncPacket.java` | 48 |