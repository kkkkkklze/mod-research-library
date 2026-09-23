# Paragliders — 速览卡片

- 仓库: https://github.com/Tictim/Paraglider
- 出现在整合包: FIDR暗涌；Modrinth 下载量(参考): 2711875
- 本地源码: `源码库\_参考仓库\_bulk\Tictim__Paraglider`
- 目标版本: MC 1.20.1 / NeoForge - / Forge 1.20.1-47.1.3 / Fabric 0.14.22；mod 版本 20.1.4
- 构建: 插件=architectury，工程结构=single；mod_id: ?
- 源码规模: 207 个 .java，15,996 行
- 主类候选: `fabric/src/main/java/tictim/paraglider/fabric/FabricParagliderMod.java` (198 行)
- 目录特征: API, Client, Command, Config, Datagen, Mixin, Network, Worldgen

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `tictim/paraglider/api` | 30 |
| `tictim/paraglider/fabric` | 29 |
| `tictim/paraglider/forge` | 23 |
| `tictim/paraglider/contents` | 22 |
| `tictim/paraglider/impl` | 19 |
| `tictim/paraglider/network` | 19 |
| `datagen` | 17 |
| `tictim/paraglider/client` | 12 |
| `tictim/paraglider/bargain` | 11 |
| `tictim/paraglider/config` | 7 |
| `tictim/paraglider/mixin` | 4 |
| `tictim/paraglider/wind` | 4 |
| `datagen/builder` | 4 |
| `tictim/paraglider/plugin` | 3 |
| `tictim/paraglider` | 2 |
| `tictim/paraglider/command` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/tictim/paraglider/client/screen/BargainScreen.java` | 512 |
| `common/src/main/java/tictim/paraglider/impl/movement/PlayerStateMapLoader.java` | 441 |
| `common/src/main/java/tictim/paraglider/ParagliderUtils.java` | 375 |
| `common/src/main/java/tictim/paraglider/command/ParagliderCommands.java` | 305 |
| `common/src/main/java/tictim/paraglider/impl/movement/ServerPlayerMovement.java` | 275 |
| `common/src/main/java/tictim/paraglider/api/movement/MovementPlugin.java` | 266 |
| `common/src/main/java/tictim/paraglider/contents/recipe/SimpleBargain.java` | 260 |
| `common/src/main/java/tictim/paraglider/client/render/StaminaWheelRenderer.java` | 247 |
| `common/src/main/java/tictim/paraglider/contents/recipe/SimpleBargainSerializer.java` | 242 |
| `forge/src/main/java/tictim/paraglider/forge/contents/ForgeContents.java` | 231 |
| `common/src/main/java/tictim/paraglider/wind/Wind.java` | 230 |
| `common/src/main/java/tictim/paraglider/client/screen/ParagliderSettingScreen.java` | 217 |
| `common/src/main/java/tictim/paraglider/client/screen/StaminaWheelSettingScreen.java` | 213 |
| `fabric/src/main/java/tictim/paraglider/fabric/FabricParagliderMod.java` | 198 |
| `common/src/main/java/tictim/paraglider/config/Cfg.java` | 197 |