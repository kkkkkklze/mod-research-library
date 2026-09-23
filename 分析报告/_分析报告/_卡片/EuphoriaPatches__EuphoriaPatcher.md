# Euphoria Patches — 速览卡片

- 仓库: https://github.com/EuphoriaPatches/EuphoriaPatcher
- 出现在整合包: ATM10, 星轨重铸；Modrinth 下载量(参考): 26879080
- 本地源码: `源码库\_参考仓库\_bulk\EuphoriaPatches__EuphoriaPatcher`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=?，工程结构=multiloader；mod_id: euphoria_patcher
- 源码规模: 196 个 .java，28,433 行
- 主类候选: `common/src/main/java/com/euphoriapatches/euphoria_patcher/config/ConfigEntry.java` (109 行)
- 目录特征: Config, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/euphoriapatches/euphoria_patcher` | 196 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/services/ShaderDetector.java` | 1059 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/features/shader_settings/UpdateShaderConfig.java` | 760 |
| `forge/src/main/java/com/euphoriapatches/euphoria_patcher/forge/mixin/IrisHeaderEntryMixin.java` | 737 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/integration/ShaderLoader.java` | 731 |
| `fabric/src/main/java/com/euphoriapatches/euphoria_patcher/fabric/mixin/IrisHeaderEntryMixinYarn.java` | 625 |
| `fabric/src/main/java/com/euphoriapatches/euphoria_patcher/fabric/mixin/IrisHeaderEntryMixin.java` | 611 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/monitoring/ShaderpacksWatcher.java` | 608 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/DevPatchGenerator.java` | 573 |
| `neoforge/src/main/java/com/euphoriapatches/euphoria_patcher/neoforge/mixin/IrisHeaderEntryMixin.java` | 562 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/util/UserPersistentData.java` | 554 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/features/properties/PropertiesWatcher.java` | 500 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/config/Config.java` | 480 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/util/UpdateChecker.java` | 468 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/monitoring/PotatoFileMonitor.java` | 427 |
| `common/src/main/java/com/euphoriapatches/euphoria_patcher/features/steganography/ShaderSteganography.java` | 409 |