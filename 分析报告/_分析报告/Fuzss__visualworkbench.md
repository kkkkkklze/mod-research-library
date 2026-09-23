# Fuzss/visualworkbench 源码分析报告

> 重要：默认分支 `main` 只有 README/LICENSE/versions.json，**源码在版本分支**（26.2.x / 26.1.x / 1.21.11 / … / 1.21.1）。本地为 partial clone（`blob:none` + sparse-checkout），本次执行 `git fetch --depth 1 origin 1.21.1 && git checkout FETCH_HEAD` 后分析 **1.21.1 分支**。

## 1. 基本信息
- Mod 名：Visual Workbench；mod_id `visualworkbench`；作者 Fuzs；`modVersion=21.1.2`
- 目标版本/加载器（`gradle.properties`）：仅声明 `modId/modVersion` 等，MC 与加载器版本来自外部脚本；`settings.gradle` 中 `include "Common" "Fabric" "NeoForge"`，**`//include "Forge"` 被注释**（该分支不构建 Forge）；mixins.json 里 `compatibilityLevel=JAVA_17`，另含 `visualworkbench.accesswidener` → 1.21.1 + Fabric/NeoForge
- Gradle：`apply from: "https://raw.githubusercontent.com/Fuzss/modresources/main/gradle/v2/settings.gradle"` 等**外链共享脚本**（仓库内几乎无构建逻辑）
- 许可证：MPL-2.0（`modLicense=MPL-2.0`）
- 编译依赖（`NeoForge/build.gradle`）：`modApi libs.puzzleslib.neoforge`（**PuzzleLib 是作者自维护的 API 前置库，必需，`>=21.1.58`**）；JEI `compileOnly libs.jeiapi.common` + `modLocalRuntime`，EMI 同；Fabric 端另需 `fabric-api`、`forge-config-api-port`

## 2. 源码规模与包结构
`find . -name '*.java' | wc -l` → **21 个 / 1102 行**（极小，靠 PuzzleLib 承担跨加载器差异）。
包（`fuzs.visualworkbench`）：根 1、`client` 1 + `client.renderer.blockentity` 1、`config` 2、`data.client` 1 + `data.tags` 1、`handler` 1、`init` 1、`integration.jei` 1 + `integration.emi` 1、`world.inventory` 1、`world.level.block` 1、`world.level.block.entity` 3；NeoForge 3 个、Fabric 2 个。
最大文件：`handler/BlockConversionHandler.java` 184、`world/level/block/entity/CraftingTableBlockEntity.java` 162、`CraftingTableAnimationController.java` 116、`client/renderer/blockentity/CraftingTableBlockEntityRenderer.java` 95、`world/level/block/CraftingTableWithInventoryBlock.java` 90。

## 3. 入口与注册
NeoForge 入口只有 16 行，把一切委托给 PuzzleLib 的跨加载器引导：
```java
// NeoForge/src/main/java/fuzs/visualworkbench/neoforge/VisualWorkbenchNeoForge.java:12
public VisualWorkbenchNeoForge() {
    ModConstructor.construct(VisualWorkbench.MOD_ID, VisualWorkbench::new);
    DataProviderHelper.registerDataProviders(VisualWorkbench.MOD_ID, ModBlockTagsProvider::new);
}
```
Fabric 端 `VisualWorkbenchFabric implements ModInitializer` 做同一件事。真正的逻辑在 Common 的 `VisualWorkbench implements ModConstructor`，`onConstructMod()`（`VisualWorkbench.java:36-53`）里 `ModRegistry.bootstrap()` + `registerEventHandlers()`。
注册用 PuzzleLib 的 `RegistryManager.from(MOD_ID).registerBlockEntityType/registerMenuType`、`TagFactory.make(MOD_ID).registerBlockTag`（`init/ModRegistry.java:16-25`），**没有 DeferredRegister**；注册项都是 `Holder.Reference`。

## 4. 核心系统
**① 方块"替换/转换"系统（本仓库最有价值的部分）**：`BlockConversionHandler.java:41-59` 维护 `BiMap<Block, Block> BLOCK_CONVERSIONS`（原方块 → 自己的 `CraftingTableWithInventoryBlock`）。它挂在 `RegistryEntryAddedCallback.registryEntryAdded(Registries.BLOCK)` 上，**每当任意方块被注册**就用谓词过滤、并以 `<namespace>/<path>` 追加注册同 id 的替代方块。谓词定义在 `VisualWorkbench.java:32-34`：`block instanceof CraftingTableBlock && !(block instanceof CraftingTableWithInventoryBlock)` —— 因此任何 mod 添加的工作台都会被自动接管，无需知道对方存在。
**② 状态转换缓存与属性搬运**：`BlockState → BlockState` 的结果放 `new MapMaker().weakKeys().weakValues().makeMap()` 缓存，防止 BlockState 长期驻留（:43-45、:156-175）；`copyAllProperties` 用 `trySetValue` 逐项搬属性（:177-183）。
**③ 物品与标签双向修正**：`onTagsUpdated`（FIRST 阶段）遍历 `BuiltInRegistries.ITEM` 找 BlockItem，用 PuzzleLib `BlockConversionHelper.setItemForBlock/setBlockForItem` 把物品指向替代方块，并 `copyBoundTags` 复制标签绑定；`unaltered_workbenches` 标签作为豁免名单（:103-142）。
**④ 方块实体即容器 + 原版菜单复用**：`CraftingTableBlockEntity extends RandomizableContainerBlockEntity`（自带战利品表，`loadAdditional` 用 `tryLoadLootTable` 分支，:41-58），额外持有一格 `resultItems`（TAG `visualworkbench:result`）用于渲染配方结果；`canPlaceItem` 照抄原版 Crafter 的 `smallerStackExist` 逻辑，禁止把大堆拆散（:72-95）。`VisualCraftingMenu extends CraftingMenu` 直接把原版菜单字段重指到方块实体自己的列表：
```java
((TransientCraftingContainer) this.craftSlots).items = blockEntity.getItems();   // VisualCraftingMenu.java:24
this.resultSlots.itemStacks = blockEntity.getResultItems();
```
这些字段靠 `Common/src/main/resources/visualworkbench.accesswidener` 打开并标 `mutable`；`removed()` 时临时把 `this.access` 换成 `ContainerLevelAccess.NULL` 以防关界面时物品被清空（:48-54）。
**⑤ 客户端动画**：`CraftingTableAnimationController` 在 BE 客户端 tick，算最近玩家方位角 → 按 π/2 分扇区 → 扇区变化时启动 20 tick 的 easeOutQuad 旋转插值（:36-115）；由 `ClientConfig.rotateIngredients`（CLOSEST_PLAYER / CRAFTING_PLAYER / NEVER）决定跟谁转。
**⑥ 无模型的方块模型解析**：`VisualWorkbenchClient.onRegisterBlockStateResolver`（:26-44）不为替代方块写 JSON 模型，而是运行时把**原方块的 BlockState 模型**指派给替代方块，缺失时用 `ModelLoadingHelper.missingModel()` 并打 warn；`onRegisterBlockRenderTypes` 也从原方块抄 render type（:58-63）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无自定义包**。同步靠 `CraftingTableBlockEntity.getUpdatePacket/getUpdateTag`（`ClientboundBlockEntityDataPacket`）加原版菜单同步（`CraftingTableBlockEntity.java:62-69`）。
- 配置：PuzzleLib `ConfigHolder.builder(MOD_ID).client(ClientConfig.class).server(ServerConfig.class)`（`VisualWorkbench.java:29-31`），字段加 `@Config(description=...)`；ServerConfig 只有 `convertVanillaWorkbenchWhenInteracting`。
- datagen：`data/tags/ModBlockTagsProvider`（23 行）、`data/client/ModLanguageProvider`（24 行），NeoForge 端由 `DataProviderHelper.registerDataProviders` 挂上。
- 软依赖集成：`integration/jei/VisualWorkbenchJEIPlugin`（29 行）、`integration/emi/VisualWorkbenchEMIPlugin`（15 行），JEI/EMI 仅 compileOnly + 本地运行时。

## 6. Mixin
- `Common/src/main/resources/common.mixins.json`、`Fabric/src/main/resources/fabric.mixins.json` 都是**空列表壳**（仅 required/minVersion/injectors 与 `${modGroup}` 占位）；`neoforge.mixins.json` 的 `client` 里只有一个类。
- `NeoForge/.../neoforge/mixin/client/BlockStateModelLoaderNeoForgeMixin.java:14` `@Mixin(BlockStateModelLoader.class)`，用 **mixinextras** `@WrapWithCondition` 包住 `lambda$loadBlockStateDefinitions$10` 里的 `Logger.warn(String, Object, Object)` 调用，并用 `@Slice(to = @At(value="FIELD", target="...BlockStateModelLoader;missingModel:...", opcode=GETFIELD))` 精确定位；条件体 `return !BlockConversionHandler.getBlockConversions().containsValue(blockState.getBlock())` —— 只为屏蔽"替代方块缺模型"的自造警告，不影响其它警告。

## 7. 值得学的 5 条
1. **"注册期谓词过滤 + 同名替代方块"的无侵入替换模式**：`handler/BlockConversionHandler.java:47-59` + `VisualWorkbench.java:32-34`；可用于给任意（含未安装的）mod 的方块/工作台附加自己的行为，天然兼容他人新增内容。
2. **用 accesswidener 打开原版菜单字段并标 mutable，直接把槽位数组换成自己的容器**，省掉整套菜单复制：`Common/src/main/resources/visualworkbench.accesswidener` + `VisualCraftingMenu.java:22-30`。
3. **BlockState→BlockState 转换结果放 `MapMaker().weakKeys().weakValues()` 弱缓存**：`BlockConversionHandler.java:43-45`；适用任何"高频查表但键值都是游戏对象"的转换/映射。
4. **用 `@WrapWithCondition` + `@Slice` 只屏蔽自己造成的日志**，而非降低日志等级或改写实现：`BlockStateModelLoaderNeoForgeMixin.java:17-25`。
5. **替代方块不写模型文件，运行时从原方块的 BlockState 定义复制 `UnbakedModel`，渲染层与 render type 一并照抄**：`client/VisualWorkbenchClient.java:26-63`；把自己的方块伪装成系统内所有同类方块的最省力做法。

## 8. 公开 API
非库 mod。对外暴露的是运行时行为（方块转换表 `BlockConversionHandler.getBlockConversions()` 为 public static，理论上供兼容代码读取）与数据包标签 `#visualworkbench:unaltered_workbenches`（豁免转换）。其多加载器骨架完全依赖前置 **PuzzleLib**（`fuzs.puzzleslib.api.*`：ModConstructor / ClientModConstructor / ConfigHolder / RegistryManager / TagFactory / BlockConversionHelper / 各事件回调），是研究"轻量多加载器 mod 架构"的现成样本。
