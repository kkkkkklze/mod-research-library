# ViScriptRecipe — 速览卡片

- 仓库: https://github.com/zhenshiz/ViScriptRecipe
- 出现在整合包: 璇穹之歌；Modrinth 下载量(参考): 未知
- 本地源码: `源码库\_参考仓库\_bulk\zhenshiz__ViScriptRecipe`
- 目标版本: MC 1.21.1 / NeoForge 21.1.228 / Forge - / Fabric -；mod 版本 1.0.8 beta
- 构建: 插件=moddev，工程结构=single；mod_id: viscript_recipe
- 源码规模: 262 个 .java，39,961 行
- 主类候选: `src/main/java/com/viscript_recipe/data/RecipeEntry.java` (192 行)
- 目录特征: Client, Command, Data, Mixin, Network
- 含 accesstransformer.cfg

## 包结构（前 20，按文件数）

| 包 | 文件数 |
|---|---|
| `com/viscript_recipe/data` | 130 |
| `com/viscript_recipe/gui` | 53 |
| `com/viscript_recipe/compat` | 48 |
| `com/viscript_recipe/recipe` | 14 |
| `com/viscript_recipe/network` | 7 |
| `com/viscript_recipe/mixin` | 5 |
| `com/viscript_recipe` | 2 |
| `com/viscript_recipe/client` | 2 |
| `com/viscript_recipe/command` | 1 |

## 最大的 15 个源文件

| 文件 | 行数 |
|---|---|
| `src/main/java/com/viscript_recipe/gui/editor/RecipeEditorController.java` | 7122 |
| `src/main/java/com/viscript_recipe/gui/editor/CraftingWorkbenchView.java` | 4357 |
| `src/main/java/com/viscript_recipe/gui/editor/MekanismCanvasFactory.java` | 1047 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipePropertiesSections.java` | 1028 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipePropertiesView.java` | 961 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipeDefaultDataInitializer.java` | 704 |
| `src/main/java/com/viscript_recipe/recipe/RecipeOverrideManager.java` | 579 |
| `src/main/java/com/viscript_recipe/gui/editor/CreateProcessingCanvasFactory.java` | 567 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipeNavigationView.java` | 549 |
| `src/main/java/com/viscript_recipe/gui/editor/IndustrialForegoingPropertiesSections.java` | 482 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipeSearchComponents.java` | 473 |
| `src/main/java/com/viscript_recipe/compat/create/CreateRecipeFactory.java` | 399 |
| `src/main/java/com/viscript_recipe/recipe/importer/RecipeImporter.java` | 395 |
| `src/main/java/com/viscript_recipe/compat/jei/RecipeDeltaJeiSynchronizer.java` | 351 |
| `src/main/java/com/viscript_recipe/gui/editor/MekanismPropertiesSections.java` | 348 |