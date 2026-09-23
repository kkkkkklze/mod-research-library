# Preloading Tricks — 速览卡片

- 仓库: https://github.com/SettingDust/preloading-tricks
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 377475
- 本地源码: `源码库\_参考仓库\_bulk\SettingDust__preloading-tricks`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=?，工程结构=single；mod_id: ?
- 源码规模: 92 个 .java，5,649 行
- 目录特征: API, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `settingdust/preloading_tricks/neoforge` | 24 |
| `settingdust/preloading_tricks/modlauncher` | 18 |
| `settingdust/preloading_tricks/forge` | 14 |
| `settingdust/preloading_tricks/fabric` | 12 |
| `settingdust/preloading_tricks/forgelike` | 11 |
| `settingdust/preloading_tricks/api` | 6 |
| `settingdust/preloading_tricks/util` | 6 |
| `settingdust/preloading_tricks` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/shared/modlauncher/main/java/settingdust/preloading_tricks/modlauncher/module_injector/ModuleReplacer.java` | 249 |
| `src/shared/modlauncher/main/java/settingdust/preloading_tricks/modlauncher/module_injector/ModuleOperationHelper.java` | 228 |
| `src/platform/fabric/main/java/settingdust/preloading_tricks/fabric/mod_candidate/ExtraModsLoader.java` | 222 |
| `src/shared/modlauncher/main/java/settingdust/preloading_tricks/modlauncher/module_injector/ModuleInjector.java` | 176 |
| `src/platform/forge/modlauncher/main/java/settingdust/preloading_tricks/forge/modlauncher/virtual_mod/VirtualJar.java` | 173 |
| `src/platform/fabric/main/java/settingdust/preloading_tricks/fabric/virtual_mod/VirtualModMetadata.java` | 167 |
| `src/platform/neoforge/modlauncher/main/java/settingdust/preloading_tricks/neoforge/modlauncher/virtual_mod/VirtualJar.java` | 163 |
| `src/shared/forgelike/main/java/settingdust/preloading_tricks/forgelike/UcpClassLoaderInjector.java` | 133 |
| `src/shared/modlauncher/main/java/settingdust/preloading_tricks/modlauncher/module_injector/ModuleMover.java` | 126 |
| `src/api/main/java/settingdust/preloading_tricks/api/PreloadingTricksCallbacks.java` | 125 |
| `src/shared/modlauncher/main/java/settingdust/preloading_tricks/modlauncher/module_injector/ModuleCopier.java` | 125 |
| `src/shared/modlauncher/main/java/settingdust/preloading_tricks/modlauncher/PreloadingTricksTransformationService.java` | 124 |
| `src/shared/modlauncher/main/java/settingdust/preloading_tricks/modlauncher/module_injector/ModuleConfigurationCreator.java` | 118 |
| `src/platform/fabric/main/java/settingdust/preloading_tricks/fabric/FabricModManager.java` | 117 |
| `src/core/main/java/settingdust/preloading_tricks/util/ServiceLoaderUtil.java` | 116 |