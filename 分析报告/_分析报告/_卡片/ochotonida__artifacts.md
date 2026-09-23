# Artifacts — 速览卡片

- 仓库: https://github.com/ochotonida/artifacts
- 出现在整合包: ATM10, 星轨重铸；Modrinth 下载量(参考): 13087683
- 本地源码: `源码库\_参考仓库\_bulk\ochotonida__artifacts`
- 目标版本: MC 26.1.2 / NeoForge 26.1.2.103 / Forge 26.1.2.103 / Fabric 0.19.2；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: artifacts
- 源码规模: 290 个 .java，19,386 行
- 主类候选: `common/src/main/java/artifacts/config/screen/ItemSubCategoryListEntry.java` (75 行)
- 目录特征: Client, Config, Data, Entity, Mixin, Network, Worldgen

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `artifacts/component/ability` | 27 |
| `artifacts/mixin/ability` | 23 |
| `artifacts/client/item` | 22 |
| `artifacts/registry` | 18 |
| `artifacts/neoforge/data` | 17 |
| `artifacts/fabric/mixin` | 13 |
| `artifacts/component` | 9 |
| `artifacts/config/value` | 9 |
| `artifacts/mixin/attribute` | 7 |
| `artifacts/mixin/item` | 7 |
| `artifacts/component/itemdamage` | 6 |
| `artifacts/config` | 6 |
| `artifacts/world` | 6 |
| `artifacts/fabric/registry` | 6 |
| `artifacts/client/mimic` | 5 |
| `artifacts/network/payload` | 5 |
| `artifacts/world/placement` | 5 |
| `artifacts/client` | 4 |
| `artifacts/integration/accessories` | 4 |
| `artifacts/integration/trinkets` | 4 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `common/src/main/java/artifacts/config/ItemConfigs.java` | 1403 |
| `common/src/main/java/artifacts/registry/ModItems.java` | 690 |
| `common/src/main/java/artifacts/entity/MimicEntity.java` | 456 |
| `neoforge/src/main/java/artifacts/neoforge/data/LootModifiers.java` | 424 |
| `common/src/main/java/artifacts/config/ConfigManager.java` | 420 |
| `neoforge/src/main/java/artifacts/neoforge/data/LootTables.java` | 394 |
| `common/src/main/java/artifacts/util/TooltipHelper.java` | 354 |
| `common/src/main/java/artifacts/event/ArtifactHooks.java` | 347 |
| `neoforge/src/main/java/artifacts/neoforge/data/Language.java` | 309 |
| `common/src/main/java/artifacts/item/ArtifactProperties.java` | 300 |
| `common/src/main/java/artifacts/registry/ModDataComponents.java` | 266 |
| `common/src/main/java/artifacts/client/item/mesh/ArmsMeshDefinitions.java` | 208 |
| `neoforge/src/main/java/artifacts/neoforge/data/tags/ItemTags.java` | 207 |
| `common/src/main/java/artifacts/client/item/mesh/LegsMeshDefinitions.java` | 203 |
| `common/src/main/java/artifacts/client/item/mesh/BeltMeshDefinitions.java` | 175 |