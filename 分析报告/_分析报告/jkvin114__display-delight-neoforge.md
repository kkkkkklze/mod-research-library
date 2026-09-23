# jkvin114/display-delight-neoforge 源码分析报告

## 1. 基本信息

- Mod 名/ID：Display Delight / `displaydelight`；作者 jkvin114；version 1.7.0
- 目标版本与加载器：**MC 1.21.1 + NeoForge 21.1.73**（`minecraft_version_range=[1.21.1,1.22)`，`loader_version_range=[4,)`），ModDevGradle `1.0.21`，Parchment `1.21 / 2024.07.28`，Java 21
- 许可证：LGPL（`gradle.properties` 的 `mod_license`）
- 编译依赖：JEI `19.8.2.99`（`compileOnly` + `runtimeOnly`，仓库 `maven.blamejared.com`）；`src/main/templates/META-INF/neoforge.mods.toml` 里声明 `farmersdelight` 为 **optional** 依赖；无其他前置。注意：本快照只含 36 个 java + mixins.json + mods.toml 模板，**assets/data 资源不在快照内**

## 2. 源码规模与包结构

- 36 个 `.java`，**3607 行**（`find . -name '*.java' -exec wc -l {} +`）
- 包结构：`init`(9：DisplayItems 592、DisplayBlocks 409、BlockAssociations 300、PlatedBlocks 236、SmallPlatedBlocks 116、DisplayConfig 56、DisplayTags 33、DisplayTabs 26、DisplayProperties 10)、`block`(16，含 `block/fiery` 4)、`events`(3：InterationManager 296、DisplayEvents 95、DisplayVillagerEvents 46)、`client/renderer`(3，PlateHidingBakedModel 100)、`trades`(1：DisplayItemListing 122)、`item`(1)、`mixin`(1)、`integration/jei`(1)、根 `DisplayDelight`(170)

## 3. 入口与注册

`DisplayDelight.java:37` `@Mod(DisplayDelight.MODID)`，构造参数 `(IEventBus, ModContainer)`：注册 4 个 `DeferredRegister` —— `DisplayBlocks.REGISTRY`、`DisplayItems.REGISTRY`、`PlatedBlocks.REGISTRY`、`SmallPlatedBlocks.REGISTRY` —— 加 `CREATIVE_TABS`，`modContainer.registerConfig(COMMON, DisplayConfig.CONFIG, "displaydelight-common.toml")`（`:128`），`NeoForge.EVENT_BUS.register(this)`，`BuildCreativeModeTabContentsEvent` 往 FOOD_AND_DRINKS 塞盘子。`DisplayItems` 用静态工厂集中注册：`block()/drinkblock()` 建 `FoodBlockItem`、`plateblock()` 建 `BlockItem`，每个都把 `DeferredHolder` 加进 `items` 列表，`GetAll()`（tail）供创造栏 / JEI / 关联表初始化复用。

## 4. 核心系统

- **命名约定自动建"物品↔方块"关联**（`init/BlockAssociations.java:179-269`，由 `DisplayEvents.onWorldLoad` 在 `LevelEvent.Load` 触发）：遍历 `DisplayItems.GetAll()`，只处理 `FoodBlockItem`；用 `COMPAT_NAMESPACES`（cd_/ed_/df_/nd_… 21 个前缀）+ `TypePrefixes`（`plated_`/`small_plated_`/空）做 `removeFirstPrefix` 推断原食物 id 与所属 mod（无前缀且命中 `VanilaFoods` → minecraft，否则 farmersdelight），再查 tag（`DISPLAYABLE`/`PLATE_DISPLAYABLE`/`SMALL_PLATE_DISPLAYABLE`）写进 `blockMap/itemMap/plateBlockMap/smallplateBlockMap`
- **缺前置降级**：`ModList.get().isLoaded(fullNamespace)` 为假时 `FoodBlockItem.setRequiredModName(name)` 并在 tooltip 提示，同时把物品塞进 `TRADEABLE_FOODS/DRINKS/PLATES/SMALL_PLATES`（`NO_WANDERING_TRADER` 排除 nethersdelight）
- **方块基类**：`block/AbstractItemBlock.java`（继承 `HorizontalDirectionalBlock`，状态 `FACING`+`SUPPORT`）；`getStateForPlacement/updateShape` 用 `BlockHelper.needSupport` 计算是否需要支撑（下方非实心/他 mod 方块 → SUPPORT=true，tag `SUPPORT_EXCEPTIONS` 或打开的活板门例外）；`getDrops` 自己算精准采集与叠盘数量、`getCloneItemStack` 中键取原食物
- **交互**：`events/InterationManager.java`（`tryTakePlateWithAxe` 斧头取盘 → `PLATE_HIDDEN=true` + 掉盘子；`testInsertPlate/tryInsertSmallPlate` 放盘；`tryPlaceItem/tryPlaceItemOnPlate` 摆放），由 `events/DisplayEvents.java:36` 的 `PlayerInteractEvent.RightClickBlock` 按顺序 try 各分支，命中即 `setCanceled(true) + InteractionResult.PASS`，每个交互都能被 `DisplayConfig` 单独关掉
- **客户端模型治理**：`client/renderer/PlateHidingBakedModel.java:21` 继承 `BakedModelWrapper`，按 `PLATE_HIDDEN` 过滤盘子 quad（`isFromElement(1,0,1,15,2,15)` 等）并整体下移 dy；`ClientEvents.onModifyBakingResult`（`:29-42`）在 `ModelEvent.ModifyBakingResult` 里对该 mod 命名空间的全部模型 `replaceAll` 包一层
- **流浪商人交易**：`trades/DisplayItemListing.java`（抽象 `DisplayFoodItemListing implements VillagerTrades.ItemListing`，`getOffer` 里用 `ItemCost + MerchantOffer`）由 `DisplayVillagerEvents.onWandererTrades` 注入 generic trades

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包
- 配置：`init/DisplayConfig.java` 用 `ModConfigSpec.Builder().push("Features")` 定义 12 个 `BooleanValue`（是否精准采集掉方块物品、流浪商人售卖、tooltip、消息、4 个交互开关等）
- 数据驱动：`init/DisplayTags.java` 声明 `displayable/plate_displayable/small_plate_displayable/support_exceptions` 及 `c:food_display_plate` 等公共 tag；datagen 未在仓库中（build.gradle 有 `data` runConfig 与 `src/generated/resources` srcDir，但无生成类）

## 6. Mixin

`src/main/resources/displaydelight.mixins.json`（`package com.jkvin114.displaydelight.mixin`，`refmap: display.refmap.json`，仅 `client`，`defaultRequire:1`）。唯一 mixin `mixin/ItemMixin.java:18` — `@Inject(method = "appendHoverText", at = @At("TAIL"))` 注入 `net.minecraft.world.item.Item`，按 tag 决定加"可摆放/可放盘上"提示，受 `DisplayConfig.TOOLTIP` 控制。

## 7. 值得学的 5 条做法

1. 用"ID 前缀 + 命名约定"从已注册物品自动推导跨 mod 兼容映射，兼容 mod 列表写成 `Map` 前缀表（`BlockAssociations.java:49-70`），新增联动只加一行。
2. 前置缺失不报错而是降级：给物品打"需要 XX"tooltip + 进流浪商人交易池（`BlockAssociations.java:203-228`、`trades/DisplayItemListing.java`）。
3. 用 tag 当玩家可配置的"能不能摆放"开关，并复用 NeoForge 公共 `c:` 命名空间（`DisplayTags.java:12-24`）。
4. 组件级模型隐藏：`BakedModelWrapper` + `ModifyBakingResult` 动态剔除/位移 quad，而不是做两套方块状态模型（`PlateHidingBakedModel`、`ClientEvents.java:29-42`）。
5. 把所有右键交互收敛到一个事件 + 一串 `if (!placed)` 分支，命中即取消事件，并让每个交互都有独立配置开关（`DisplayEvents.java:36-86`、`InterationManager`）。

## 8. 公开 API

非库模组，无对外 API 包；联动靠 tag、`FoodBlockItem` 与命名约定自动发现。
