# CoFH Core — 速览卡片

- 仓库: https://github.com/CoFH/CoFHCore
- 出现在整合包: FIDR暗涌；Modrinth 下载量(参考): 2163573
- 本地源码: `源码库\_参考仓库\_bulk\CoFH__CoFHCore`
- 目标版本: MC ? / NeoForge 20.4.237 / Forge - / Fabric -；mod 版本 11.0.2
- 构建: 插件=userdev，工程结构=single；mod_id: cofh_core
- 源码规模: 525 个 .java，47,109 行
- 目录特征: API, Client, Command, Config, Data, Entity, Network, Worldgen
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `cofh/core/common` | 172 |
| `cofh/lib/common` | 99 |
| `cofh/core/client` | 85 |
| `cofh/core/util` | 47 |
| `cofh/lib/api` | 37 |
| `cofh/lib/util` | 31 |
| `cofh/core/init` | 19 |
| `cofh/lib/init` | 11 |
| `cofh/core/mixin` | 10 |
| `cofh/core/compat` | 7 |
| `cofh/lib/client` | 6 |
| `cofh/core` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/cofh/core/util/AreaUtils.java` | 986 |
| `src/main/java/cofh/core/util/helpers/RenderHelper.java` | 818 |
| `src/main/java/cofh/core/util/helpers/vfx/VFXHelper.java` | 745 |
| `src/main/java/cofh/lib/util/Utils.java` | 642 |
| `src/main/java/cofh/core/util/helpers/FluidHelper.java` | 537 |
| `src/main/java/cofh/lib/util/helpers/MathHelper.java` | 481 |
| `src/main/java/cofh/core/client/gui/ContainerScreenCoFH.java` | 475 |
| `src/main/java/cofh/core/util/helpers/GuiHelper.java` | 455 |
| `src/main/java/cofh/core/util/helpers/AreaEffectHelper.java` | 443 |
| `src/main/java/cofh/lib/init/data/RecipeProviderCoFH.java` | 441 |
| `src/main/java/cofh/lib/util/recipes/RecipeJsonUtils.java` | 393 |
| `src/main/java/cofh/core/client/gui/element/ElementListBox.java` | 364 |
| `src/main/java/cofh/core/client/gui/element/panel/PanelBase.java` | 358 |
| `src/main/java/cofh/lib/common/item/CrossbowItemCoFH.java` | 331 |
| `src/main/java/cofh/lib/util/crafting/ShapedRecipeInternal.java` | 326 |