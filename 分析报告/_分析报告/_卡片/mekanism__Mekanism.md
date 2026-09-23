# Refined Storage - Mekanism Integration — 速览卡片

- 仓库: https://github.com/mekanism/Mekanism
- 出现在整合包: ATM10, FIDR暗涌, 星轨重铸；Modrinth 下载量(参考): 3609437
- 本地源码: `源码库\_参考仓库\_bulk\mekanism__Mekanism`
- 目标版本: MC 1.21.1 / NeoForge 21.1.200 / Forge - / Fabric -；mod 版本 10.7.19
- 构建: 插件=moddev，工程结构=single；mod_id: 5579007
- 源码规模: 2455 个 .java，259,854 行
- 主类候选: `src/main/java/mekanism/client/gui/robit/GuiRobitMain.java` (117 行)
- 目录特征: API, Client, Command, Config, Data, Datagen, Entity, Network, Worldgen
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `mekanism/client/gui` | 232 |
| `mekanism/common/integration` | 204 |
| `mekanism/common/tile` | 142 |
| `mekanism/common/content` | 122 |
| `mekanism/common/lib` | 122 |
| `mekanism/client/recipe_viewer` | 106 |
| `mekanism/common/recipe` | 103 |
| `mekanism/api/recipes` | 101 |
| `mekanism/common/inventory` | 92 |
| `mekanism/common/capabilities` | 91 |
| `mekanism/generators/common` | 86 |
| `mekanism/client/render` | 82 |
| `mekanism/common/item` | 76 |
| `mekanism/common/network` | 75 |
| `mekanism/additions/common` | 60 |
| `mekanism/common/block` | 55 |
| `mekanism/common/attachments` | 50 |
| `mekanism/generators/client` | 49 |
| `mekanism/tools/common` | 49 |
| `mekanism/common/registration` | 37 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/datagen/main/java/mekanism/client/lang/MekanismLangProvider.java` | 1833 |
| `src/main/java/mekanism/common/tile/base/TileEntityMekanism.java` | 1713 |
| `src/datagen/main/java/mekanism/common/recipe/impl/MekanismRecipeProvider.java` | 1675 |
| `src/main/java/mekanism/common/tile/machine/TileEntityDigitalMiner.java` | 1488 |
| `src/main/java/mekanism/common/registries/MekanismBlocks.java` | 1132 |
| `src/main/java/mekanism/common/registries/MekanismBlockTypes.java` | 964 |
| `src/main/java/mekanism/common/inventory/container/QIOItemViewerContainer.java` | 931 |
| `src/main/java/mekanism/common/content/qio/QIOCraftingWindow.java` | 928 |
| `src/main/java/mekanism/common/util/WorldUtils.java` | 927 |
| `src/main/java/mekanism/common/util/MekanismUtils.java` | 921 |
| `src/main/java/mekanism/common/MekanismLang.java` | 889 |
| `src/main/java/mekanism/common/tile/machine/TileEntityFormulaicAssemblicator.java` | 879 |
| `src/main/java/mekanism/common/content/blocktype/BlockShapes.java` | 865 |
| `src/main/java/mekanism/common/entity/EntityRobit.java` | 839 |
| `src/api/java/mekanism/api/chemical/BasicChemicalTank.java` | 829 |