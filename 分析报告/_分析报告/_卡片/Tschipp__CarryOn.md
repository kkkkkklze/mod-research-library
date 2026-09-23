# Carry On — 速览卡片

- 仓库: https://github.com/Tschipp/CarryOn
- 出现在整合包: 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 25254327
- 本地源码: `源码库\_参考仓库\_bulk\Tschipp__CarryOn`
- 目标版本: MC 26.2 / NeoForge 26.2.0.41-beta / Forge 26.2.0.41-beta / Fabric 0.19.3；mod 版本 ?
- 构建: 插件=moddev，工程结构=single；mod_id: carryon
- 源码规模: 96 个 .java，8,993 行
- 主类候选: `Fabric/src/main/java/tschipp/carryon/CarryOnFabricMod.java` (75 行)
- 目录特征: Client, Command, Config, Mixin

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `tschipp/carryon/common` | 14 |
| `tschipp/carryon/mixin` | 14 |
| `tschipp/carryon/config` | 12 |
| `tschipp/carryon/events` | 12 |
| `tschipp/carryon/platform` | 9 |
| `tschipp/carryon` | 8 |
| `tschipp/carryon/client` | 7 |
| `tschipp/carryon/compat` | 7 |
| `tschipp/carryon/networking` | 6 |
| `tschipp/carryon/carry` | 4 |
| `tschipp/carryon/utils` | 2 |
| `tschipp/carryon/scripting` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `Common/src/main/java/tschipp/carryon/client/render/CarryRenderHelper.java` | 416 |
| `Common/src/main/java/tschipp/carryon/common/config/CarryConfig.java` | 393 |
| `Common/src/main/java/tschipp/carryon/common/carry/PlacementHandler.java` | 390 |
| `Common/src/main/java/tschipp/carryon/common/scripting/Matchables.java` | 355 |
| `Common/src/main/java/tschipp/carryon/common/carry/PickupHandler.java` | 323 |
| `Common/src/main/java/tschipp/carryon/common/carry/CarryOnData.java` | 282 |
| `Forge/src/main/java/tschipp/carryon/events/CommonEvents.java` | 254 |
| `Common/src/main/java/tschipp/carryon/common/config/ListHandler.java` | 237 |
| `NeoForge/src/main/java/tschipp/carryon/events/CommonEvents.java` | 233 |
| `Common/src/main/java/tschipp/carryon/CarryOnCommon.java` | 213 |
| `Common/src/main/java/tschipp/carryon/common/scripting/CarryOnScript.java` | 206 |
| `Fabric/src/main/java/tschipp/carryon/config/fabric/ConfigLoaderImpl.java` | 197 |
| `Common/src/main/java/tschipp/carryon/common/command/CommandCarryOn.java` | 178 |
| `Fabric/src/main/java/tschipp/carryon/events/CommonEvents.java` | 178 |
| `Common/src/main/java/tschipp/carryon/client/render/CarriedObjectRender.java` | 152 |