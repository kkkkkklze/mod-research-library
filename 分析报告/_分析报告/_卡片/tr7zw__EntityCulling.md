# Entity Culling — 速览卡片

- 仓库: https://github.com/tr7zw/EntityCulling
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 164860754
- 本地源码: `源码库\_参考仓库\EntityCulling`
- 目标版本: MC ? / NeoForge - / Forge - / Fabric -；mod 版本 ?
- 构建: 插件=?，工程结构=single；mod_id: ?
- 源码规模: 31 个 .java，2,351 行
- 主类候选: `src/main/java/dev/tr7zw/entityculling/EntityCullingMod.java` (82 行)
- 目录特征: Config, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `dev/tr7zw/entityculling` | 30 |
| `dev/tr7zw/tests` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/dev/tr7zw/entityculling/EntityCullingModBase.java` | 249 |
| `src/main/java/dev/tr7zw/entityculling/mixin/WorldRendererMixin.java` | 242 |
| `src/main/java/dev/tr7zw/entityculling/config/ConfigScreenProvider.java` | 221 |
| `src/main/java/dev/tr7zw/entityculling/CullTask.java` | 177 |
| `src/main/java/dev/tr7zw/entityculling/mixin/BlockEntityRenderDispatcherMixin.java` | 127 |
| `src/main/java/dev/tr7zw/entityculling/mixin/ClientWorldMixin.java` | 115 |
| `src/main/java/dev/tr7zw/entityculling/mixin/EntityRendererMixin.java` | 108 |
| `src/main/java/dev/tr7zw/entityculling/DebugCollector.java` | 102 |
| `EntityCulling-Versionless/src/main/java/dev/tr7zw/entityculling/versionless/Config.java` | 93 |
| `src/main/java/dev/tr7zw/entityculling/EntityCullingMod.java` | 82 |
| `EntityCulling-Versionless/src/main/java/dev/tr7zw/entityculling/versionless/EntityCullingVersionlessBase.java` | 70 |
| `src/main/java/dev/tr7zw/entityculling/mixin/CullableMixin.java` | 66 |
| `src/main/java/dev/tr7zw/entityculling/NMSCullingHelper.java` | 64 |
| `EntityCulling-Versionless/src/main/java/dev/tr7zw/entityculling/versionless/ConfigUpgrader.java` | 59 |
| `src/main/java/dev/tr7zw/entityculling/mixin/DebugHudMixin.java` | 59 |