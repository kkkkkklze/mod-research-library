# SophisticatedStorage 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Sophisticated Storage / `sophisticatedstorage`（v1.5.91）
- 作者：P3pp3rF1y（代码）、Ridanisaurus（美术）；许可证：All Rights Reserved（`gradle.properties` `mod_license`）
- 目标：Minecraft 1.21.1、NeoForge 21.1.229（`neo_version_range=[21.1.229,)`）、`modLoader="javafml"`、`loaderVersion=[4,)`（`src/main/templates/META-INF/neoforge.mods.toml:1-2`）
- Gradle：`java-library` + `net.neoforged.moddev` 1.0.14 + curseforgegradle 1.1.15 + minotaur + spotless 7.0.4 + openrewrite（`build.gradle:1-9`）
- 依赖（`build.gradle:186-231`）：**`implementation net.p3pp3rf1y:sophisticatedcore:${sc_version}`（`sc_version=[1.21.1-1.4.88,1.21.2)`，且有 `findProject(':SophisticatedCore')` 分支）**，mods.toml 中把它声明为 required 依赖；另 `implementation` SophisticatedBackpacks（`sb_version=[1.21.1-3.25.74,1.21.2)`）。可选 `compileOnly/localRuntime`：JEI、EMI、REI、Embeddium、Jade、Chipped、Athena、ResourcefulLib、Sawmill、MoonlightLib、Tom's Storage、Quark/Zeta。
- 发布：CurseForge 619320 / Modrinth `hMlaZH8f`

## 2. 源码规模与包结构

实测：`.java` 238 个、共 32717 行。`src/main` 各包（递归文件数/行数）：

| 包 | 文件/行 | 包 | 文件/行 |
|---|---|---|---|
| block | 47 / 8027 | client | 56 / 7858 |
| compat | 35 / 2085 | item | 16 / 2999 |
| upgrades | 15 / 2002 | crafting | 13 / 1002 |
| common | 11 / 1109 | init | 9 / 1290 |
| network | 8 / 273 | data | 7 / 1268 |
| entity | 6 / 1628 | settings | 2 / 85 |
| util | 4 / 535 | | |

最大文件：`item/StorageTierUpgradeItem.java`(1063)、`client/render/BarrelBakedModelBase.java`(988)、`data/StorageRecipeProvider.java`(953)、`client/gui/DecorationTableScreen.java`(875)、`block/DecorationTableBlockEntity.java`(839)、`upgrades/compression/CompressionInventoryPart.java`(808)、`block/StorageBlockEntity.java`(683)、`entity/StorageHolderBase.java`(586)、`entity/MovingStorageWrapper.java`(580)、`block/ChestBlock.java`(544)。

## 3. 入口与注册

`src/main/java/net/p3pp3rf1y/sophisticatedstorage/SophisticatedStorage.java:23` 为 `@Mod` 主类：

```java
container.registerConfig(ModConfig.Type.SERVER, Config.SERVER_SPEC);   // :31-33 SERVER/CLIENT/COMMON 三份
ModBlocks.registerHandlers(modBus);
ModItems.registerHandlers(modBus);
modBus.addListener(ModPayloads::registerPayloads);
modBus.addListener(DataGenerators::gatherData);
ModParticles.registerParticles(modBus);
```

`FMLCommonSetupEvent` 里 `event.enqueueWork(ModBlocks::registerDispenseBehavior)`、`registerCauldronInteractions`（发射器与炼药锅交互）。注册框架为 NeoForge `DeferredRegister`，集中在 `init/ModBlocks.java:58-62,350,372` 的 6 个注册器（`BLOCKS`、`ITEMS`、`BLOCK_ENTITY_TYPES`、`MENU_TYPES`、`RECIPE_SERIALIZERS`、`INGREDIENT_TYPES`），由 `registerHandlers`（:377-388）统一 `register(modBus)` 并追加 `ModBlocks::registerCapabilities`（如 `Capabilities.ItemHandler.BLOCK` → `ControllerBlockEntity::getExternalItemHandler`）；`init/ModItems.java:91` 另有 `ITEMS`；`init/ModPayloads`、`init/ModDataComponents`、`init/ModParticles` 同构。客户端注册走 `ModBlocksClient.init` / `ModItemsClient`。

## 4. 核心系统

**(a) 存储方块 + 内嵌 StorageWrapper**（`block/StorageBlockBase.java`、`block/WoodStorageBlockBase.java`、`block/StorageBlockEntity.java`）
- `StorageBlockEntity` 内部类 `StorageWrapper implements IStorageWrapper`（:98-172）覆写 `getContentsUuid()`、`getWrappedStorageStack()`、`getDefaultNumberOfInventorySlots()`、`getBaseStackSizeMultiplier()`、`getStorageType()`、`isAllowedInStorage()` 等，把 SC 的库存/升级/设置框架直接架在方块实体上；NBT 键 `STORAGE_WRAPPER_TAG="storageWrapper"`、`UPDATE_BLOCK_RENDER_TAG="updateBlockRender"`。
- 打开状态用 `SophisticatedOpenersCounter`（非原版 `ContainerOpenersCounter`）统计；`ICountDisplay`/`IFillLevelDisplay`/`ILockable`/`ITierDisplay`/`IUpgradeDisplay` 一组接口把「外观显示」抽出来供渲染层查询。
- 方块族：`ChestBlock`、`BarrelBlock`、`ShulkerBoxBlock`、`LimitedBarrelBlock`、`WoodStorageBlockBase` + 对应 BlockEntity；`item/` 侧 `ChestBlockItem`/`BarrelBlockItem`/`ShulkerBoxItem`/`SimpleMaterialBlockItem`/`WoodStorageBlockItem` 处理物品形态（含方块化反向迁移 `LegacyStorageBlockDataMigration`）。

**(b) 材质与装饰（油漆笔/装饰台）**（`block/BarrelMaterial.java`、`util/DecorationHelper.java`、`util/SimpleMaterialHelper.java`、`item/PaintbrushItem.java`、`block/DecorationTableBlockEntity.java`）
- 材质用 `BarrelMaterial` 枚举 + `IMaterialHolder`/`ISimpleMaterialHolder`/`SimpleMaterialBlockData` 承载，`GenericWoodStorageHelper`/`SimpleMaterialHelper.getSingleMaterial(...)` 做「一个方块材质」的识别。
- `DecorationHelper`：`BLOCK_TOTAL_PARTS = 24`（:22）—— 每个存储方块拆成 24 个部件，改材质/改色时按部件逐个消耗染料或装饰方块，`getDyePartsNeeded(...)`/`getMaterialPartsNeeded(...)` 计算需求，`consumeDyePartsNeeded(...)`/`consumeMaterialPartsNeeded(...)` 返回 `record ConsumptionResult(boolean hasEnough, Map<ResourceLocation, Integer> missingParts)`，装饰台 GUI 逐件展示缺什么。

**(c) 升级物品与压缩升级**（`item/StorageTierUpgradeItem.java`、`upgrades/compression/CompressionInventoryPart.java`、`upgrades/hopper`）
- `StorageTierUpgradeItem`（1063 行）持有 `TierUpgrade` 枚举，`useOn` 时把原版箱子/木桶/潜影盒（处理 `ChestType`、`WoodType`、`ShulkerBoxBlock`、`RandomizableContainerBlockEntity` 内容搬运）升级为 SC 存储方块，并保留内容物。
- `CompressionInventoryPart`（808 行，`upgrades/compression`）实现 SC 的 `IInventoryPartHandler`，把压缩升级的槽位嵌入存储库存分区，`IOMode`/`INeighborChangeListenerUpgrade` 定义存储 IO 与邻居更新回调。

**(d) 控制器 / 多方块连通**（`block/ControllerBlock.java`、`block/StorageConnectorBlock.java`、`block/StorageLinkBlock.java`、`block/StorageIOBlock.java` + 各 BlockEntity）
控制器逻辑几乎全在 SC 的 `controller/ControllerBlockEntityBase`（1112 行），本仓库只做方块/菜单/能力绑定（`ModBlocks.registerCapabilities`）。

**(e) 实体携带存储**（`entity/`）
`StorageHolderBase`(586)、`MovingStorageWrapper`(544)：把存储挂到实体（如随方块移动/掉落时的内容物包装），复用 `IStorageWrapper` 而非自定义容器。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：8 个 payload（`network/`），`init/ModPayloads.java` 用 `event.registrar(MOD_ID).versioned(getNetworkProtocolVersion())` 注册：`OpenStorageInventoryPayload`、`RequestStorageContentsPayload`/`StorageContentsPayload`、`ScrolledToolPayload`、`RequestPlayerSettingsPayload`、`StorageOpennessPayload`、`RequestControllerTargetHighlightsPayload`。
- 数据驱动：本仓库注册 `RecipeSerializer` 与 NeoForge `IngredientType`（`ModBlocks.java:350,372`）；设置模板走 SC 的 `sophisticated_settingstemplates` 数据包（本仓库仅 `settings/StorageSettingsHandler.java` 一个定制）。
- 配置：SERVER/CLIENT/COMMON 三份 Spec，`Config.SERVER.initListeners(modBus)`。
- datagen：`data/DataGenerators` → `StorageRecipeProvider`(953)、`BlockTagProvider`、`ItemTagProvider`、`StorageBlockLootProvider`、`CopyStorageDataFunction`（数据组件复制/迁移函数）。资源目录本身只有 `META-INF`（资源由 datagen 生成）。

## 6. Mixin

无。`src/main` 下不存在 `*.mixins.json`，也没有 `mixin` 包；所有 mixin 由前置 SophisticatedCore 提供（`sophisticatedcore.mixins.json` 与 `sophisticatedcore.create.mixins.json`）。

## 7. 值得学的 5 条具体做法

1. **BlockEntity 内部类直接 `implements IStorageWrapper`**：方块存储与物品存储共用同一套库存/升级/设置/网络代码，`block/StorageBlockEntity.java:98-172`，适合「同一套容器逻辑要同时给方块和物品用」的场景。
2. **把「外观材质」做成枚举 + 部件计数消耗**：`DecorationHelper.java:22`（24 部件）+ `ConsumptionResult` 记录缺少量，改色/改材质可精确告诉玩家缺几个染料/方块。适合任何外观自定义系统。
3. **方块↔物品同构 + 显式迁移类**：`LegacyStorageBlockDataMigration`、`CopyStorageDataFunction`、`init/ModDataComponents` 把旧 NBT 数据迁到 DataComponent，升级存档格式时风险可控。
4. **分级升级用枚举驱动**（`StorageTierUpgradeItem` 的 `TierUpgrade`）：把「原版方块 → 本模组方块」的映射与搬运逻辑集中在一处，新增等级只加枚举项。
5. **能力注册集中在一个 `registerCapabilities`**：`ModBlocks.java:390` 起，用 `RegisterCapabilitiesEvent` 明确声明 `Capabilities.ItemHandler.BLOCK` 等，避免各处散落 `capability` 注册。

## 8. 公开 API

非库 mod，无独立 API 包；对外可复用的是它对 SC 扩展点的实现示例（`IInventoryPartHandler` 的 `CompressionInventoryPart`、`IStorageWrapper` 的方块实现 `StorageBlockEntity.StorageWrapper`），以及 `upgrades/INeighborChangeListenerUpgrade`、`upgrades/IOMode` 这类可被同生态引用的接口。
