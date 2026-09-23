# Architectury API — 速览卡片

- 仓库: https://github.com/architectury/architectury
- 出现在整合包: ATM10, FIDR暗涌, 星轨重铸, 璇穹之歌；Modrinth 下载量(参考): 98546473
- 本地源码: `源码库\_参考仓库\_bulk\architectury__architectury`
- 目标版本: MC 1.19.2 / NeoForge - / Forge 43.2.0 / Fabric 0.14.19；mod 版本 ?
- 构建: 插件=architectury，工程结构=single；mod_id: ?
- 许可证: GNU Lesser General Public License ==========================
- 源码规模: 332 个 .java，25,313 行
- 主类候选: `common/src/main/java/dev/architectury/platform/Mod.java` (93 行)
- 目录特征: Client, Entity, Mixin, Network, Worldgen

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `dev/architectury/mixin` | 71 |
| `dev/architectury/registry` | 63 |
| `dev/architectury/hooks` | 54 |
| `dev/architectury/event` | 40 |
| `dev/architectury/test` | 23 |
| `dev/architectury/networking` | 17 |
| `dev/architectury/core` | 16 |
| `dev/architectury/utils` | 14 |
| `dev/architectury/extensions` | 11 |
| `dev/architectury/impl` | 7 |
| `dev/architectury/platform` | 5 |
| `dev/architectury/fluid` | 3 |
| `dev/architectury/annotations` | 2 |
| `dev/architectury/init` | 2 |
| `dev/architectury/plugin` | 2 |
| `dev/architectury/compat` | 1 |
| `dev/architectury/forge` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `forge/src/main/java/dev/architectury/registry/registries/forge/RegistriesImpl.java` | 787 |
| `common/src/main/java/dev/architectury/core/fluid/ArchitecturyFluidAttributes.java` | 639 |
| `forge/src/main/java/dev/architectury/registry/level/biome/forge/BiomeModificationsImpl.java` | 557 |
| `forge/src/main/java/dev/architectury/event/forge/EventHandlerImplCommon.java` | 447 |
| `common/src/main/java/dev/architectury/hooks/level/biome/BiomeHooks.java` | 397 |
| `common/src/main/java/dev/architectury/core/fluid/SimpleArchitecturyFluidAttributes.java` | 381 |
| `testmod-common/src/main/java/dev/architectury/test/events/DebugEvents.java` | 367 |
| `forge/src/main/java/dev/architectury/event/forge/EventHandlerImplClient.java` | 357 |
| `fabric/src/main/java/dev/architectury/registry/level/biome/fabric/BiomeModificationsImpl.java` | 325 |
| `fabric/src/main/java/dev/architectury/registry/registries/fabric/RegistriesImpl.java` | 292 |
| `common/src/main/java/dev/architectury/event/events/common/PlayerEvent.java` | 289 |
| `forge/src/main/java/dev/architectury/core/fluid/forge/imitator/ArchitecturyFluidAttributesForge.java` | 266 |
| `common/src/main/java/dev/architectury/fluid/FluidStack.java` | 254 |
| `common/src/main/java/dev/architectury/event/EventFactory.java` | 249 |
| `common/src/main/java/dev/architectury/hooks/fluid/FluidStackHooks.java` | 235 |