# Immersive Engineering — 速览卡片

- 仓库: https://github.com/BluSunrize/ImmersiveEngineering
- 出现在整合包: ATM10, FIDR暗涌, 星轨重铸；Modrinth 下载量(参考): 3472261
- 本地源码: `源码库\_参考仓库\_bulk\BluSunrize__ImmersiveEngineering`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: immersiveengineering, minecraft, neoforge
- 源码规模: 1305 个 .java，162,223 行
- 主类候选: `src/manual/java/blusunrize/lib/manual/ManualEntry.java` (478 行)
- 目录特征: API, Client, Config, Data, Datagen, Entity, Mixin, Network, Worldgen

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `blusunrize/immersiveengineering/common` | 678 |
| `blusunrize/immersiveengineering/client` | 223 |
| `blusunrize/immersiveengineering/api` | 220 |
| `blusunrize/immersiveengineering/data` | 85 |
| `blusunrize/immersiveengineering/mixin` | 46 |
| `blusunrize/lib/manual` | 25 |
| `src/main/oldjava` | 22 |
| `blusunrize/immersiveengineering/gametest` | 4 |
| `blusunrize/immersiveengineering` | 1 |
| `invtweaks/api/container` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/blusunrize/immersiveengineering/common/register/IEBlocks.java` | 1051 |
| `src/datagen/java/blusunrize/immersiveengineering/data/blockstates/BlockStates.java` | 1018 |
| `src/datagen/java/blusunrize/immersiveengineering/data/recipes/MiscRecipes.java` | 867 |
| `src/datagen/java/blusunrize/immersiveengineering/data/recipes/DecorationRecipes.java` | 831 |
| `src/main/java/blusunrize/immersiveengineering/common/blocks/metal/FluidPipeBlockEntity.java` | 827 |
| `src/main/java/blusunrize/immersiveengineering/common/util/Utils.java` | 809 |
| `src/api/java/blusunrize/immersiveengineering/api/shader/ShaderRegistry.java` | 779 |
| `src/datagen/java/blusunrize/immersiveengineering/data/recipes/DeviceRecipes.java` | 771 |
| `src/main/java/blusunrize/immersiveengineering/common/gui/IESlot.java` | 769 |
| `src/datagen/java/blusunrize/immersiveengineering/data/tags/IEBlockTags.java` | 746 |
| `src/main/java/blusunrize/immersiveengineering/client/ClientEventHandler.java` | 739 |
| `src/datagen/java/blusunrize/immersiveengineering/data/recipes/MultiblockRecipes.java` | 738 |
| `src/main/java/blusunrize/immersiveengineering/common/items/RevolverItem.java` | 706 |
| `src/datagen/java/blusunrize/immersiveengineering/data/blockstates/ExtendedBlockstateProvider.java` | 705 |
| `src/main/java/blusunrize/immersiveengineering/common/config/IEServerConfig.java` | 675 |