# playerAnimator — 速览卡片

- 仓库: https://github.com/KosmX/fabricPlayerAnimation
- 出现在整合包: ATM10, 璇穹之歌；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\KosmX__fabricPlayerAnimation`
- 目标版本: MC 1.21.1 / NeoForge - / Forge 21.1.89 / Fabric 0.16.9；mod 版本 2.0.4
- 构建: 插件=architectury，工程结构=single；mod_id: ?
- 源码规模: 108 个 .java，8,241 行
- 目录特征: API, Client, Data, Mixin, Network

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `dev/kosmx/playerAnim` | 105 |
| `dev/kosmx/animatorTestmod` | 3 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/KeyframeAnimation.java` | 939 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/api/layered/KeyframeAnimationPlayer.java` | 395 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/AnimationBinary.java` | 330 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/gson/GeckoLibSerializer.java` | 319 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/gson/AnimationJson.java` | 299 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/api/layered/ModifierLayer.java` | 228 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/api/layered/modifier/AdjustmentModifier.java` | 206 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/opennbs/network/NBSPacket.java` | 184 |
| `minecraft/common/src/main/java/dev/kosmx/playerAnim/mixin/PlayerModelMixin.java` | 162 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/quarktool/Section.java` | 160 |
| `minecraft/common/src/main/java/dev/kosmx/playerAnim/minecraftApi/PlayerAnimationRegistry.java` | 154 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/opennbs/format/Layer.java` | 151 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/util/Ease.java` | 134 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/util/Easing.java` | 132 |
| `coreLib/src/main/java/dev/kosmx/playerAnim/core/data/opennbs/NBSFileUtils.java` | 124 |