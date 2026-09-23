# Elytra Slot — 速览卡片

- 仓库: https://github.com/illusivesoulworks/elytraslot
- 出现在整合包: 星轨重铸；Modrinth 下载量(参考): 13540453
- 本地源码: `源码库\_参考仓库\_bulk\illusivesoulworks__elytraslot`
- 目标版本: MC 1.21.4 / NeoForge 21.4.136 / Forge 21.4.136 / Fabric 0.16.9；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: elytraslot
- 源码规模: 23 个 .java，949 行
- 主类候选: `neoforge/src/main/java/com/illusivesoulworks/elytraslot/ElytraSlotNeoForgeClientMod.java` (122 行)
- 目录特征: Client, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/illusivesoulworks/elytraslot` | 23 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `neoforge/src/main/java/com/illusivesoulworks/elytraslot/ElytraSlotNeoForgeClientMod.java` | 122 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/client/ElytraSlotLayer.java` | 108 |
| `neoforge/src/main/java/com/illusivesoulworks/elytraslot/ElytraSlotNeoForgeMod.java` | 95 |
| `fabric/src/main/java/com/illusivesoulworks/elytraslot/ElytraSlotFabricMod.java` | 91 |
| `fabric/src/main/java/com/illusivesoulworks/elytraslot/ElytraSlotFabricClientMod.java` | 75 |
| `neoforge/src/main/java/com/illusivesoulworks/elytraslot/common/CurioElytra.java` | 64 |
| `fabric/src/main/java/com/illusivesoulworks/elytraslot/platform/FabricClientPlatform.java` | 61 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/mixin/IntegrationMixinPlugin.java` | 58 |
| `neoforge/src/main/java/com/illusivesoulworks/elytraslot/platform/NeoForgeClientPlatform.java` | 33 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/ElytraSlotConstants.java` | 28 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/mixin/integration/waveycapes/CustomCapeRenderLayerMixin.java` | 27 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/platform/services/IClientPlatform.java` | 27 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/integration/minecraftcapes/MinecraftCapesPlugin.java` | 23 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/platform/Services.java` | 22 |
| `common/src/main/java/com/illusivesoulworks/elytraslot/platform/ClientServices.java` | 20 |