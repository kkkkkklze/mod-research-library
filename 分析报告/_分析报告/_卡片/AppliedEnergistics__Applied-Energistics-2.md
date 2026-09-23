# Applied Energistics 2 — 速览卡片

- 仓库: https://github.com/AppliedEnergistics/Applied-Energistics-2
- 出现在整合包: ATM10, FIDR暗涌, 星轨重铸；Modrinth 下载量(参考): 5850461
- 本地源码: `源码库\_参考仓库\_bulk\AppliedEnergistics__Applied-Energistics-2`
- 目标版本: MC 26.1.2 / NeoForge 26.1.2.21-beta / Forge 26.1.2.21-beta / Fabric -；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: ?
- 源码规模: 1453 个 .java，167,250 行
- 主类候选: `src/main/java/appeng/menu/me/crafting/CraftingStatusEntry.java` (115 行)
- 目录特征: API, Client, Config, Datagen, Entity, Mixin, Network, Worldgen
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `appeng/client/gui` | 132 |
| `appeng/api/networking` | 61 |
| `appeng/client/render` | 39 |
| `appeng/core/network` | 37 |
| `appeng/integration/modules` | 37 |
| `appeng/datagen/providers` | 36 |
| `appeng/util` | 35 |
| `appeng/client/integrations` | 32 |
| `appeng/client/renderer` | 31 |
| `appeng/api/config` | 30 |
| `appeng/items/tools` | 29 |
| `appeng/server/testplots` | 28 |
| `appeng/parts/automation` | 27 |
| `appeng/menu/implementations` | 26 |
| `appeng/api/implementations` | 24 |
| `appeng/menu/me` | 24 |
| `appeng/server/testworld` | 23 |
| `appeng/api/stacks` | 20 |
| `appeng/api/storage` | 20 |
| `appeng/menu/slot` | 20 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/client/java/appeng/datagen/providers/recipes/CraftingRecipes.java` | 1512 |
| `src/main/java/appeng/parts/CableBusContainer.java` | 1102 |
| `src/client/java/appeng/client/gui/AEBaseScreen.java` | 1101 |
| `src/main/java/appeng/menu/AEBaseMenu.java` | 1050 |
| `src/main/java/appeng/server/testplots/TestPlots.java` | 1023 |
| `src/client/java/appeng/client/gui/me/common/MEStorageScreen.java` | 872 |
| `src/main/java/appeng/helpers/patternprovider/PatternProviderLogic.java` | 819 |
| `src/main/java/appeng/me/GridNode.java` | 788 |
| `src/main/java/appeng/core/AEConfig.java` | 778 |
| `src/main/java/appeng/menu/me/common/MEStorageMenu.java` | 750 |
| `src/main/java/appeng/blockentity/storage/MEChestBlockEntity.java` | 735 |
| `src/main/java/appeng/menu/me/items/PatternEncodingTermMenu.java` | 704 |
| `src/main/java/appeng/crafting/pattern/AECraftingPattern.java` | 691 |
| `src/client/java/appeng/client/AppEngClient.java` | 670 |
| `src/client/java/appeng/client/render/cablebus/CableBuilder.java` | 670 |