# ModernFix — 速览卡片

- 仓库: https://github.com/embeddedt/ModernFix
- 出现在整合包: ATM10, FIDR暗涌, 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 76865964
- 本地源码: `源码库\_参考仓库\_bulk\embeddedt__ModernFix`
- 目标版本: MC 1.20.1 / NeoForge - / Forge 1.20.1-47.4.0 / Fabric 0.16.10；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: modernfix
- 源码规模: 337 个 .java，20,489 行
- 主类候选: `annotations/src/main/java/org/embeddedt/modernfix/annotation/RequiresMod.java` (13 行)
- 目录特征: API, Command, Config, Entity, Worldgen
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `org/embeddedt/modernfix` | 333 |
| `org/fury_phoenix/mixinAp` | 4 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/org/embeddedt/modernfix/forge/capability/analysis/CapabilityAnalyzer.java` | 713 |
| `src/main/java/org/embeddedt/modernfix/core/config/ModernFixEarlyConfig.java` | 630 |
| `src/main/java/org/embeddedt/modernfix/forge/capability/CapabilityProviderDispatcherGenerator.java` | 550 |
| `src/main/java/org/embeddedt/modernfix/common/mixin/perf/dynamic_resources/ModelBakeryMixin.java` | 413 |
| `src/main/java/org/embeddedt/modernfix/resources/ZipPackIndex.java` | 394 |
| `src/main/java/org/embeddedt/modernfix/core/ModernFixMixinPlugin.java` | 329 |
| `src/main/java/org/embeddedt/modernfix/forge/dynresources/ModelBakeEventHelper.java` | 325 |
| `src/main/java/org/embeddedt/modernfix/dynamicresources/DynamicBakedModelProvider.java` | 297 |
| `src/main/java/org/embeddedt/modernfix/world/gen/ChunkBiomeLookup.java` | 267 |
| `src/main/java/org/embeddedt/modernfix/screen/OptionList.java` | 243 |
| `src/main/java/org/embeddedt/modernfix/textures/StbStitcher.java` | 238 |
| `src/main/java/org/embeddedt/modernfix/resources/PackResourcesCacheEngine.java` | 235 |
| `src/main/java/org/embeddedt/modernfix/spark/SparkLaunchProfiler.java` | 220 |
| `src/main/java/org/embeddedt/modernfix/common/mixin/perf/cache_strongholds/ChunkGeneratorMixin.java` | 204 |
| `src/main/java/org/embeddedt/modernfix/platform/forge/ModernFixPlatformHooksImpl.java` | 195 |