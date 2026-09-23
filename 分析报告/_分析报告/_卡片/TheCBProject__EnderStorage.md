# Ender Storage — 速览卡片

- 仓库: https://github.com/TheCBProject/EnderStorage
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 641347
- 本地源码: `源码库\_参考仓库\_bulk\TheCBProject__EnderStorage`
- 目标版本: MC ? / NeoForge - / Forge 21.11.42 / Fabric -；mod 版本 2.14.0
- 构建: 插件=moddev，工程结构=single；mod_id: enderstorage, minecraft, neoforge
- 许可证: The MIT License (MIT) Copyright (c) 2020 covers1624, Chicken
- 源码规模: 67 个 .java，4,471 行
- 目录特征: API, Client, Config, Entity, Network
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `codechicken/enderstorage/client` | 19 |
| `codechicken/enderstorage/manager` | 7 |
| `codechicken/enderstorage/api` | 5 |
| `codechicken/enderstorage/plugin` | 5 |
| `codechicken/enderstorage/block` | 4 |
| `codechicken/enderstorage/init` | 4 |
| `codechicken/enderstorage/tile` | 4 |
| `codechicken/enderstorage/item` | 3 |
| `codechicken/enderstorage/recipe` | 3 |
| `codechicken/enderstorage/storage` | 3 |
| `codechicken/enderstorage` | 2 |
| `codechicken/enderstorage/config` | 2 |
| `codechicken/enderstorage/container` | 2 |
| `codechicken/enderstorage/misc` | 2 |
| `codechicken/enderstorage/network` | 2 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/codechicken/enderstorage/tile/TileEnderTank.java` | 258 |
| `src/main/java/codechicken/enderstorage/manager/EnderStorageManager.java` | 250 |
| `src/main/java/codechicken/enderstorage/storage/EnderItemStorage.java` | 215 |
| `src/main/java/codechicken/enderstorage/block/BlockEnderStorage.java` | 201 |
| `src/main/java/codechicken/enderstorage/init/DataGenerators.java` | 200 |
| `src/main/java/codechicken/enderstorage/client/render/RenderCustomEndPortal.java` | 179 |
| `src/main/java/codechicken/enderstorage/recipe/ReColourRecipe.java` | 176 |
| `src/main/java/codechicken/enderstorage/client/render/tile/RenderTileEnderTank.java` | 173 |
| `src/main/java/codechicken/enderstorage/client/render/tile/RenderTileEnderChest.java` | 147 |
| `src/main/java/codechicken/enderstorage/tile/TileFrequencyOwner.java` | 132 |
| `src/main/java/codechicken/enderstorage/tile/TileEnderChest.java` | 127 |
| `src/main/java/codechicken/enderstorage/init/EnderStorageModContent.java` | 125 |
| `src/main/java/codechicken/enderstorage/api/Frequency.java` | 123 |
| `src/main/java/codechicken/enderstorage/plugin/jei/ESCraftingRecipeWrapper.java` | 110 |
| `src/main/java/codechicken/enderstorage/container/ContainerEnderItemStorage.java` | 107 |