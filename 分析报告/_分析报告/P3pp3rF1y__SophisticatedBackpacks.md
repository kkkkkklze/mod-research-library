# SophisticatedBackpacks 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Sophisticated Backpacks / `sophisticatedbackpacks`（v3.26.3）
- 作者：P3pp3rF1y（代码）、Ridanisaurus（美术）；许可证：All Rights Reserved（`gradle.properties` `mod_license`）
- 目标：Minecraft 1.21.1、NeoForge 21.1.229（`neo_version_range=[21.1.229,)`）、`modLoader="javafml"`、`loaderVersion=[4,)`（`src/main/templates/META-INF/neoforge.mods.toml:1-2`，其中 `sophisticatedcore` 为 required 依赖）
- Gradle：`java-library` + `net.neoforged.moddev` 1.0.14 + curseforgegradle 1.1.15 + minotaur + spotless 7.0.4 + openrewrite（`build.gradle:1-9`）
- 依赖（`build.gradle:176-216`）：**`implementation net.p3pp3rf1y:sophisticatedcore:${sc_version}`（`sc_version=[1.21.1-1.5.1,1.21.2)`，含 `findProject(':SophisticatedCore')` 分支）**；`compileOnly/localRuntime`：JEI、EMI、REI、Curios、Accessories、Balm、CraftingTweaks、Chipped、Athena、ResourcefulLib、Sawmill、MoonlightLib。
- 发布：CurseForge 422301 / Modrinth `TyCTlI4b`

## 2. 源码规模与包结构

实测：`.java` 253 个、共 25225 行。`src/main` 各包（递归文件数/行数）：

| 包 | 文件/行 | 包 | 文件/行 |
|---|---|---|---|
| upgrades | 58 / 5374 | backpack | 32 / 5482 |
| compat | 35 / 1758 | client | 24 / 2713 |
| network | 17 / 796 | command | 11 / 862 |
| registry | 14 / 969 | api | 10 / 159 |
| data | 10 / 774 | common | 8 / 2063 |
| init | 7 / 875 | crafting | 6 / 315 |
| settings | 6 / 191 | util | 4 / 258 |
| mixin | 2 / 21 | | |

`upgrades` 下 16 个子包：`anvil`、`deposit`、`everlasting`、`inception`、`mobcatcher`、`refill`、`restock`、`smithing`、`toolswapper` 等。
最大文件：`client/render/BackpackDynamicModel.java`(1145)、`backpack/wrapper/BackpackWrapper.java`(878)、`common/gui/BackpackContext.java`(817)、`Config.java`(610)、`init/ModItems.java`(552)、`common/EntityBackpackAdditionHandler.java`(537)、`upgrades/refill/RefillUpgradeWrapper.java`(514)、`backpack/BackpackBlockEntity.java`(505)、`backpack/BackpackItem.java`(503)。

## 3. 入口与注册

`src/main/java/net/p3pp3rf1y/sophisticatedbackpacks/SophisticatedBackpacks.java:39` 为 `@Mod` 主类：

```java
container.registerConfig(ModConfig.Type.SERVER, Config.SERVER_SPEC);   // :53-54 SERVER/COMMON
LinkedStorageEndpointAdapters.register(new BackpackLinkedStorageEndpointAdapter()); // :62
modBus.addListener(SophisticatedBackpacks::setup);      // FMLCommonSetupEvent
SBPCommand.init(modBus);
eventBus.addListener(this::onAddReloadListener);        // NeoForge 总线
```

- `onAddReloadListener`（:113-117）注册三个数据包监听器：`RegistryLoader`、`DatapackBackpackTemplateManager.Loader.INSTANCE`、`BackpackShapeReloadListener.INSTANCE`。
- `setup`（:86-90）做 `ModItems::registerDispenseBehavior`、`ModItems::registerCauldronInteractions`、`LinkedStorageHostFactories.register(BackpackLinkedStorageHostWrapper.FACTORY_ID, ...)`。
- 客户端额外注册 `KeybindHandler::registerKeyMappings` 与三个 tooltip 组件工厂（`BackpackContentsTooltip`/`LinkedStorageTooltip`/`MobCatcherHealthTooltip`）。
- 注册框架为 `DeferredRegister`：`init/ModItems.java:136-141`（`ITEMS`、`CREATIVE_MODE_TABS`、`LOOT_FUNCTION_TYPES`、`LOOT_CONDITION_TYPES`）、`init/ModBlocks.java:19-20`、`init/ModDataComponents.java:19`、`command/SBPCommand.java:21`（`COMMAND_ARGUMENT_TYPES`）。

## 4. 核心系统

**(a) 背包包装层**（`backpack/wrapper/` 17 文件）
- `BackpackWrapper implements IBackpackWrapper`（878 行）：`fromStack(ItemStack)` / `fromExistingData(ItemStack)` 两个静态工厂决定「新建还是复用 NBT 数据」；`DEFAULT_MAIN_COLOR=0xFF_CC613A`、`DEFAULT_ACCENT_COLOR=0xFF_622E1A`；对外暴露 `getInventoryHandler`、`getUpgradeHandler`、`getSettingsHandler`、`getFluidHandler`、`getEnergyStorage`、`getContentsUuid`、`copyDataTo`、`replaceBackpackStack`。
- 同包 `BackpackFluidHandler`、`BackpackRenderInfo`、`BackpackSettingsHandler`、`LegacyBackpackDataMigration`、`InventoryModificationHandler`、`EmptyEnergyStorage`，以及 linked storage 三件套 `BackpackLinkedStorageEndpointAdapter`/`HostWrapper`/`Resolver`（接入 SC 1.5 的 linkedstorage 扩展点）。

**(b) 背包形态与打开上下文**（`backpack/BackpackItem`、`BackpackBlockEntity`、`common/gui/BackpackContext`）
- `BackpackContext`（817 行）统一处理「物品/方块/实体/Accessories/Curios 里装的背包」几种位置的打开、内容定位与网络请求，避免每种上下文各写一套。
- `BackpackBlock`/`BackpackBlockEntity` 提供方块形态（可放置），`BackpackStorage`/`StackStorageWrapper` 处理物品内存储。
- 访问控制：`BackpackAccessLogger` + `AccessLogRecord`（记录访问日志）、`UUIDDeduplicator`（防同一背包被重复挂载）。

**(c) 数据驱动：工具/剑注册 与 背包模板/形状**（`registry/` 14 文件）
- `RegistryLoader extends SimpleJsonResourceReloadListener`，目录 `"registry"`，内部 `static { registerParser(...) }` 注册 `ToolRegistry.BlockToolsLoader`、`EntityToolsLoader`、`SwordRegistry.SwordsLoader` 三个解析器；`IRegistryDataLoader` 抽象 `parse(JsonObject, modId)`，`IMatcherFactory`/`ItemTagMatcher`/`ModMatcher`/`Matchers` 让 JSON 里既能写物品 id、tag，也能写 `Predicate<ItemStack>`；查询入口 `ToolRegistry.isToolForBlock(stack, block, level, state, pos)` / `isToolForEntity(stack, entity)`。
- 背包模板与形状：`DatapackBackpackTemplateManager`、`BackpackTemplates`、`BackpackTemplateStorage`、`BackpackShapeHelper`、`BackpackShapes`、`BackpackShapeReloadListener`（数据包定义可生成的模板背包与方块形状）。

**(d) 动态模型渲染**（`client/render/BackpackDynamicModel.java` 1145 行 + `BackpackItemClient`）
按背包物品/升级内容动态 bake 模型（含 tank/颜色/升级贴图层），是本仓库最大单文件；`client/gui` 提供 GUI。

**(e) 实体 AI：怪物自动装备背包**（`common/EntityBackpackAdditionHandler.java` 537 行）
- 常量与权重表：`MAX_DIFFICULTY=3`、`MAX_LOCAL_DIFFICULTY=6.75f`、`BACKPACK_CHANCES`、`DIFFICULTY_BACKPACK_CHANCES`（按难度分档），复用 SC 的 `WeightedElement<T>`。
- 实体持久标记写在实体 data：`ENTITY_DATA_SPAWNED_WITH_BACKPACK="spawnedWithBackpack"`、`spawnedWithJukeboxUpgrade`、`pendingBackpackAddition`、`converting`；装备方式 `monster.setItemSlot(EquipmentSlot.CHEST, backpack)` + `setDropChance(EquipmentSlot.CHEST, 0)`（默认不掉落），头盔/护腿/靴子按 `HELMET_CHANCES`/`LEGGINGS_CHANCES`/`BOOTS_CHANCES` 概率补装（:151-153）；另有 `backpack_bearer_health_bonus` 属性修饰符。

**(f) 升级生态与外部回调 API**（`upgrades/` 58 文件 + `api/`）
- `api/` 10 个近乎纯接口的文件是「给其他 mod 的钩子」：`IAttackEntityResponseUpgrade`、`IBlockClickResponseUpgrade`、`IBlockPickResponseUpgrade`、`IBlockToolSwapUpgrade`、`IEntityToolSwapUpgrade`、`IItemHandlerInteractionUpgrade`、`IEnergyStorageUpgradeWrapper`、`IFluidHandlerWrapperUpgrade`、`IInventoryWrapperUpgrade`——其他 mod 实现这些接口即可让背包升级响应自己的交互。
- 内置升级：`refill`、`restock`、`everlasting`、`inception`、`mobcatcher`（含 `MobCatcherCaptureEffectPayload`/`ReleasePayload`）、`anvil`、`smithing`、`deposit`、`toolswapper` 等。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/` 17 个 payload + `init/ModPayloads`，`PayloadRegistrar.versioned(getNetworkProtocolVersion())` 后逐个 `playToServer/playToClient`：`BackpackOpenPayload`、`AnotherPlayerBackpackOpenPayload`（打开他人背包）、`UpgradeTogglePayload`、`InventoryInteractionPayload`、`BlockToolSwapPayload`/`EntityToolSwapPayload`、`RequestBackpackInventoryContentsPayload`/`BackpackContentsPayload`、`LinkedStorageBackpackContentsPayload`、`SyncClientInfoPayload`、`MobCatcherCaptureEffectPayload`/`ReleasePayload`、`BlockPickPayload` 等。
- 数据驱动：`registry/*.json`（工具/剑匹配，兼容任意 mod 的工具集）；`DatapackBackpackTemplateManager`、`BackpackShapeReloadListener`；`data/SBLootEnabledCondition` 作为战利品注入开关条件。
- 配置：`Config.SERVER_SPEC` / `Config.COMMON_SPEC`（`Config.java` 610 行，含生成概率等），`Config.SERVER.initListeners(modBus)`。
- datagen：`data/DataGenerators` → `SBPRecipeProvider`、`SBLootTableProvider`/`PBlockLootSubProvider`/`SBInjectLootSubProvider` + `SBLootModifierProvider`（Global Loot Modifier 注入）、`CopyBackpackDataFunction`、`ItemTagProvider`。
- 命令：`command/SBPCommand`（11 文件，注册自定义 `ArgumentTypeInfo`）。

## 6. Mixin

- 配置：`src/main/resources/sophisticatedbackpacks.mixins.json`（`required: true`，`package net.p3pp3rf1y.sophisticatedbackpacks.mixin`，`JAVA_17`），`mixins` 仅 `MobAccessor`，`client` 为空。
- 代表类 `mixin/MobAccessor.java`：`@Mixin(Mob.class)` 接口式 `@Invoker("getAmbientSound")`，方法名 `sophisticatedbackpacks$getAmbientSound()` —— 用 accessor/invoker mixin 取原版 protected 方法（供 mobcatcher 捕获生物时复用声音），不注入逻辑。

## 7. 值得学的 5 条具体做法

1. **物品内数据用「工厂方法 + 已有数据探测」两分支**：`BackpackWrapper.fromStack` / `fromExistingData`（`backpack/wrapper/BackpackWrapper.java:106,138`），避免重复初始化并兼容旧存档。
2. **统一「打开上下文」抽象**：`common/gui/BackpackContext.java` 一个类处理物品/方块/实体/饰品模组的打开路径，新增载体只加分支，适合任何「可放在多处的容器」。
3. **JSON 化的工具/剑注册表**：`registry/RegistryLoader.java`（`SimpleJsonResourceReloadListener` + `IRegistryDataLoader` 静态注册解析器）+ `ToolRegistry.isToolForBlock/isToolForEntity`，让 toolswapper 升级自动识别任意 mod 的工具，无需硬编码。
4. **给怪物装配装备的权重表抽取**：`common/EntityBackpackAdditionHandler.java:59-103` 的 `MAX_DIFFICULTY`/`WeightedElement`/`DIFFICULTY_BACKPACK_CHANCES` 结构，可整段借用做「按难度给怪物配装备」的 AI 增强（对实体/AI 方向很实用）。
5. **外部 mod 通过极简 api 包挂钩交互**：`api/` 下全是单方法接口（如 `IBlockPickResponseUpgrade`），其他 mod 实现接口即可让升级响应自己的方块点击/工具交换，接口数量 = 扩展点清晰度。

## 8. 公开 API

非库 mod，但 `net.p3pp3rf1y.sophisticatedbackpacks.api` 是其对外扩展面（10 个交互响应接口，见 4(f)），实际接入需以 `net.p3pp3rf1y:sophisticatedcore` 为前置（官方发布渠道为 GitHub Packages maven）。此外 `backpack/wrapper/IBackpackWrapper` 与 `IBackpackContentsSource`、`ClientLinkedStorageBackpackContents` 是跨包可用的包装接口。
