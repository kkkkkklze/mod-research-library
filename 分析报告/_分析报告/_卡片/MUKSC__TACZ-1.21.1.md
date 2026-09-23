# [UNOFFICIAL] TaCZ 1.21.1 NeoForge Port — 速览卡片

- 仓库: https://github.com/MUKSC/TACZ-1.21.1
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 930366
- 本地源码: `源码库\_参考仓库\_bulk\MUKSC__TACZ-1.21.1`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 1.1.8-hotfix-r6
- 构建: 插件=architectury，工程结构=single；mod_id: tacz
- 源码规模: 641 个 .java，59,087 行
- 主类候选: `src/main/java/com/tacz/guns/compat/jei/entry/AttachmentQueryEntry.java` (89 行)
- 目录特征: API, Client, Command, Config, Data, Entity, Mixin, Network
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/tacz/guns` | 641 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/com/tacz/guns/item/ModernKineticGunScriptAPI.java` | 900 |
| `src/main/java/com/tacz/guns/client/resource/GunDisplayInstance.java` | 769 |
| `src/main/java/com/tacz/guns/entity/EntityKineticBullet.java` | 762 |
| `src/main/java/com/tacz/guns/client/gui/GunSmithTableScreen.java` | 712 |
| `src/main/java/com/tacz/guns/api/client/animation/gltf/GltfConstants.java` | 688 |
| `src/main/java/com/tacz/guns/client/model/BedrockAttachmentModel.java` | 664 |
| `src/main/java/com/tacz/guns/item/ModernKineticGunItem.java` | 594 |
| `src/main/java/com/tacz/guns/api/client/animation/gltf/accessor/AccessorDatas.java` | 557 |
| `src/main/java/com/tacz/guns/client/model/BedrockGunModel.java` | 508 |
| `src/main/java/com/tacz/guns/util/math/MathUtil.java` | 493 |
| `src/main/java/com/tacz/guns/api/item/gun/AbstractGunItem.java` | 492 |
| `src/main/java/com/tacz/guns/api/item/nbt/GunItemDataAccessor.java` | 465 |
| `src/main/java/com/tacz/guns/client/animation/statemachine/GunAnimationStateContext.java` | 459 |
| `src/main/java/com/tacz/guns/api/client/animation/gltf/AnimationStructure.java` | 428 |
| `src/main/java/com/tacz/guns/api/client/animation/ObjectAnimationRunner.java` | 414 |