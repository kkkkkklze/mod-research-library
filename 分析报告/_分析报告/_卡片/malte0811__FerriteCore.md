# FerriteCore — 速览卡片

- 仓库: https://github.com/malte0811/FerriteCore
- 出现在整合包: FIDR暗涌, 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 149414054
- 本地源码: `源码库\_参考仓库\FerriteCore`
- 目标版本: MC 1.21.1 / NeoForge 21.1.218 / Forge - / Fabric 0.18.4；mod 版本 7.0.3
- 构建: 插件=moddev，工程结构=single；mod_id: ferritecore
- 许可证: MIT License Copyright (c) 2020 malte0811 Permission is hereb
- 源码规模: 69 个 .java，3,858 行
- 主类候选: `NeoForge/src/main/java/malte0811/ferritecore/ModMainForge.java` (11 行)
- 目录特征: Config, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `malte0811/ferritecore/mixin` | 35 |
| `malte0811/ferritecore/fastmap` | 10 |
| `malte0811/ferritecore/impl` | 6 |
| `malte0811/ferritecore` | 5 |
| `malte0811/ferritecore/hash` | 5 |
| `malte0811/ferritecore/util` | 5 |
| `malte0811/ferritecore/ducks` | 3 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `Common/src/main/java/malte0811/ferritecore/fastmap/table/FastmapNeighborTable.java` | 218 |
| `Common/src/main/java/malte0811/ferritecore/fastmap/PropertyIndexer.java` | 209 |
| `Common/src/main/java/malte0811/ferritecore/mixin/config/FerriteConfig.java` | 177 |
| `Common/src/main/java/malte0811/ferritecore/impl/BlockStateCacheImpl.java` | 170 |
| `Common/src/main/java/malte0811/ferritecore/util/SmallThreadingDetector.java` | 169 |
| `Common/src/main/java/malte0811/ferritecore/fastmap/FastMap.java` | 167 |
| `Common/src/test/java/malte0811/ferritecore/fastmap/FastMapTest.java` | 159 |
| `Common/src/main/java/malte0811/ferritecore/mixin/config/FerriteMixinConfig.java` | 154 |
| `Common/src/test/java/malte0811/ferritecore/util/SmallThreadingDetectorTest.java` | 124 |
| `Common/src/main/java/malte0811/ferritecore/impl/KeyValueConditionImpl.java` | 111 |
| `Common/src/main/java/malte0811/ferritecore/fastmap/table/CrashNeighborTable.java` | 107 |
| `Common/src/main/java/malte0811/ferritecore/impl/FastMapEntryMap.java` | 98 |
| `Common/src/main/java/malte0811/ferritecore/mixin/fastmap/FastMapStateHolderMixin.java` | 97 |
| `Common/src/main/java/malte0811/ferritecore/impl/Deduplicator.java` | 96 |
| `Common/src/main/java/malte0811/ferritecore/hash/DiscreteVSHash.java` | 85 |