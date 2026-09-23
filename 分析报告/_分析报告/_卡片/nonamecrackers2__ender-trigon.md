# Ender Trigon — 速览卡片

- 仓库: https://github.com/nonamecrackers2/ender-trigon
- 出现在整合包: FIDR暗涌；Modrinth 下载量(参考): 533676
- 本地源码: `源码库\_参考仓库\_bulk\nonamecrackers2__ender-trigon`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=forgegradle，工程结构=single；mod_id: endertrigon, forge, minecraft
- 源码规模: 40 个 .java，3,402 行
- 主类候选: `src/main/java/nonamecrackers2/endertrigon/EnderTrigonMod.java` (77 行)
- 目录特征: Client, Entity, Mixin
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `nonamecrackers2/endertrigon/common` | 22 |
| `nonamecrackers2/endertrigon/mixin` | 12 |
| `nonamecrackers2/endertrigon/client` | 5 |
| `nonamecrackers2/endertrigon` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/nonamecrackers2/endertrigon/common/entity/BabyEnderDragon.java` | 320 |
| `src/main/java/nonamecrackers2/endertrigon/client/renderer/entity/model/BabyEnderDragonModel.java` | 264 |
| `src/main/java/nonamecrackers2/endertrigon/mixin/MixinEnderDragon.java` | 167 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/boss/enderdragon/phase/DragonChargeUpPhase.java` | 139 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/DragonFlame.java` | 129 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/boss/enderdragon/phase/DragonCrashPlayerPhase.java` | 120 |
| `src/main/java/nonamecrackers2/endertrigon/mixin/MixinDragonHoldingPatternPhase.java` | 112 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/goal/BabyEnderDragonMoveAnchorGoal.java` | 101 |
| `src/main/java/nonamecrackers2/endertrigon/common/util/EnderDragonHelper.java` | 101 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/boss/enderdragon/phase/DragonDiveBombPlayerPhase.java` | 95 |
| `src/main/java/nonamecrackers2/endertrigon/common/block/BabyDragonEgg.java` | 93 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/goal/BabyEnderDragonSweepGoal.java` | 93 |
| `src/main/java/nonamecrackers2/endertrigon/mixin/MixinDragonStrafePlayerPhase.java` | 92 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/boss/enderdragon/EnderDragonHead.java` | 88 |
| `src/main/java/nonamecrackers2/endertrigon/common/entity/boss/enderdragon/phase/DragonSnatchPlayerPhase.java` | 87 |