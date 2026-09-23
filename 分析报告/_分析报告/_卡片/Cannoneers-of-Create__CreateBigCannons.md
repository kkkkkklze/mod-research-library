# Create Big Cannons — 速览卡片

- 仓库: https://github.com/Cannoneers-of-Create/CreateBigCannons
- 出现在整合包: 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 7396939
- 本地源码: `源码库\_参考仓库\_bulk\Cannoneers-of-Create__CreateBigCannons`
- 目标版本: MC 1.21.1 / NeoForge 21.1.228 / Forge 21.1.228 / Fabric -；mod 版本 5.11.7
- 构建: 插件=moddev，工程结构=single；mod_id: createbigcannons
- 许可证: Copyright (c) 2022- Cannoneers of Create This project is fre
- 源码规模: 668 个 .java，62,021 行
- 主类候选: `src/main/java/rbasamoyai/createbigcannons/connected_textures/CBCCTSpriteShiftEntry.java` (30 行)
- 目录特征: Client, Config, Datagen, Mixin, Network
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `rbasamoyai/createbigcannons/munitions` | 168 |
| `rbasamoyai/createbigcannons/effects` | 70 |
| `rbasamoyai/createbigcannons/crafting` | 69 |
| `rbasamoyai/createbigcannons/cannons` | 62 |
| `rbasamoyai/createbigcannons/mixin` | 49 |
| `rbasamoyai/createbigcannons/cannon_control` | 39 |
| `rbasamoyai/createbigcannons/compat` | 37 |
| `rbasamoyai/createbigcannons/index` | 26 |
| `rbasamoyai/createbigcannons/network` | 22 |
| `rbasamoyai/createbigcannons/base` | 21 |
| `rbasamoyai/createbigcannons/datagen` | 18 |
| `rbasamoyai/createbigcannons/config` | 12 |
| `rbasamoyai/createbigcannons/remix` | 12 |
| `rbasamoyai/createbigcannons` | 11 |
| `rbasamoyai/createbigcannons/block_armor_properties` | 9 |
| `rbasamoyai/createbigcannons/block_hit_effects` | 9 |
| `rbasamoyai/createbigcannons/cannon_loading` | 8 |
| `rbasamoyai/createbigcannons/ponder` | 8 |
| `rbasamoyai/createbigcannons/equipment` | 6 |
| `rbasamoyai/createbigcannons/multiloader` | 6 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/rbasamoyai/createbigcannons/index/CBCBlocks.java` | 1352 |
| `src/main/java/rbasamoyai/createbigcannons/ponder/CannonLoadingScenes.java` | 1241 |
| `src/main/java/rbasamoyai/createbigcannons/ponder/CannonCraftingScenes.java` | 1044 |
| `src/main/java/rbasamoyai/createbigcannons/cannon_control/contraption/MountedBigCannonContraption.java` | 791 |
| `src/main/java/rbasamoyai/createbigcannons/remix/ContraptionRemix.java` | 763 |
| `src/main/java/rbasamoyai/createbigcannons/datagen/assets/CBCBuilderTransformers.java` | 751 |
| `src/main/java/rbasamoyai/createbigcannons/munitions/AbstractCannonProjectile.java` | 665 |
| `src/main/java/rbasamoyai/createbigcannons/crafting/casting/AbstractCannonCastBlockEntity.java` | 664 |
| `src/main/java/rbasamoyai/createbigcannons/cannon_control/cannon_mount/CannonMountBlockEntity.java` | 592 |
| `src/main/java/rbasamoyai/createbigcannons/cannon_control/contraption/MountedAutocannonContraption.java` | 588 |
| `src/main/java/rbasamoyai/createbigcannons/ponder/CannonMountScenes.java` | 587 |
| `src/main/java/rbasamoyai/createbigcannons/cannon_control/carriage/CannonCarriageEntity.java` | 564 |
| `src/main/java/rbasamoyai/createbigcannons/datagen/CBCCraftingRecipeProvider.java` | 558 |
| `src/main/java/rbasamoyai/createbigcannons/crafting/boring/AbstractCannonDrillBlockEntity.java` | 520 |
| `src/main/java/rbasamoyai/createbigcannons/crafting/builtup/CannonBuildingContraption.java` | 471 |