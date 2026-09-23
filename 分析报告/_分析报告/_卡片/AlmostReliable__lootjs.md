# LootJS: KubeJS Addon — 速览卡片

- 仓库: https://github.com/AlmostReliable/lootjs
- 出现在整合包: 璇穹之歌；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\AlmostReliable__lootjs`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: ${modId}, minecraft, neoforge
- 源码规模: 151 个 .java，8,398 行
- 主类候选: `src/main/java/com/almostreliable/lootjs/core/entry/LootEntry.java` (251 行)
- 目录特征: Mixin
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/almostreliable/lootjs` | 130 |
| `testmod/gametest` | 7 |
| `testmod/gametest/conditions` | 7 |
| `testmod` | 2 |
| `testmod/event` | 2 |
| `testmod/gametest/tables` | 2 |
| `testmod/mixin` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/com/almostreliable/lootjs/core/filters/ItemFilterImpl.java` | 277 |
| `src/main/java/com/almostreliable/lootjs/core/entry/LootEntry.java` | 251 |
| `src/main/java/com/almostreliable/lootjs/loot/LootConditionsContainer.java` | 250 |
| `src/main/java/com/almostreliable/lootjs/loot/LootEntryList.java` | 218 |
| `src/main/java/com/almostreliable/lootjs/loot/table/MutableLootTable.java` | 212 |
| `src/main/java/com/almostreliable/lootjs/loot/modifier/GroupedLootAction.java` | 205 |
| `src/main/java/com/almostreliable/lootjs/kube/wrappers/BasicWrapper.java` | 182 |
| `src/main/java/com/almostreliable/lootjs/core/LootBucket.java` | 171 |
| `src/test/java/testmod/gametest/ItemFilterTests.java` | 170 |
| `src/main/java/com/almostreliable/lootjs/loot/AddAttributesFunction.java` | 169 |
| `src/main/java/com/almostreliable/lootjs/loot/LootFunctionsContainer.java` | 163 |
| `src/main/java/com/almostreliable/lootjs/loot/LootTableEvent.java` | 154 |
| `src/main/java/com/almostreliable/lootjs/mixin/LootTableMixin.java` | 138 |
| `src/main/java/com/almostreliable/lootjs/loot/LootModificationEvent.java` | 128 |
| `src/main/java/com/almostreliable/lootjs/core/filters/ItemFilter.java` | 125 |