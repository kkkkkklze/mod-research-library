# Flux Networks — 速览卡片

- 仓库: https://github.com/McJty/XNet
- 出现在整合包: ATM10；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\McJty__XNet`
- 目标版本: MC 1.16.5 / NeoForge - / Forge 36.2.19 / Fabric -；mod 版本 ?
- 构建: 插件=forgegradle，工程结构=single；mod_id: forge, mcjtylib, xnet
- 源码规模: 125 个 .java，15,716 行
- 目录特征: API, Client, Datagen, Network
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `mcjty/xnet/modules` | 49 |
| `mcjty/rftoolscontrol/api` | 18 |
| `mcjty/xnet/apiimpl` | 16 |
| `mcjty/xnet/multiblock` | 11 |
| `mcjty/xnet/compat` | 6 |
| `mcjty/xnet/datagen` | 6 |
| `mcjty/xnet/client` | 5 |
| `mcjty/xnet/setup` | 5 |
| `mcjty/xnet/commands` | 4 |
| `mcjty/xnet/logic` | 3 |
| `crazypants/enderio/api` | 1 |
| `mcjty/xnet` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/mcjty/xnet/modules/controller/blocks/TileEntityController.java` | 1091 |
| `src/main/java/mcjty/xnet/modules/controller/client/GuiController.java` | 729 |
| `src/main/java/mcjty/xnet/apiimpl/items/ItemChannelSettings.java` | 579 |
| `src/main/java/mcjty/xnet/multiblock/ChunkBlob.java` | 537 |
| `src/main/java/mcjty/xnet/apiimpl/items/ItemConnectorSettings.java` | 420 |
| `src/main/java/mcjty/xnet/modules/cables/blocks/ConnectorBlock.java` | 388 |
| `src/main/java/mcjty/xnet/multiblock/WorldBlob.java` | 385 |
| `src/main/java/mcjty/xnet/modules/wireless/blocks/TileEntityWirelessRouter.java` | 382 |
| `src/main/java/mcjty/xnet/modules/router/blocks/TileEntityRouter.java` | 373 |
| `src/main/java/mcjty/xnet/modules/cables/blocks/ConnectorTileEntity.java` | 369 |
| `src/main/java/mcjty/xnet/modules/cables/blocks/GenericCableBlock.java` | 368 |
| `src/main/java/mcjty/xnet/apiimpl/fluids/FluidChannelSettings.java` | 362 |
| `src/main/java/mcjty/xnet/modules/cables/client/GenericCableBakedModel.java` | 361 |
| `src/main/java/mcjty/xnet/modules/controller/client/AbstractEditorPanel.java` | 339 |
| `src/main/java/mcjty/xnet/apiimpl/logic/Sensor.java` | 319 |