# NightEpiphany/KaleidoscopeHodgepodge 源码分析

## 1. 基本信息
- Mod 名：森罗物语：杂烩 / Kaleidoscope: Hodgepodge；mod_id `kaleidoscope_hodgepodge`；作者 NightEpiphany；maven_group `com.moigferdsrte.kaleidoscopehodgepodge`；版本 1.1.0-fabric+mc26.2
- 目标：**Fabric**，MC 26.2（`gradle.properties`：minecraft_version=26.2、loader_version=0.19.5、loom_version=1.17-SNAPSHOT），Java 25（`build.gradle.kts` options.release=25、mixin compatibilityLevel JAVA_25）
- 许可证 MIT（README badge）；README badge 标注支持 MC 1.21.1 | 26.1.2 | 26.2 与 Fabric|Neoforge
- 编译依赖：`kaleidoscope-cookery-refabricated` 1.4.1.5（maven.modrinth，必需前置）、`fabric-api` 0.160.0+26.2、`forgeconfigapiport-fabric` 26.2.1（Kaleidoscope Cookery 声明的必需运行依赖）、JEI 30.16.0.134；测试 JUnit 5.12.2
- 注：仓库未包含 `fabric.mod.json` 与 assets（`src/main/resources` 下只有 mixins.json），完整元数据未确认

## 2. 源码规模与包结构
- 123 个 .java / 12374 行（含 src/test）；主源码 + 11 个 JUnit 测试文件（807 行）
- 包（main）：`core` 24、`init` 9、`gametest` 8、`block` 8、`mixin` 7、`client/render` 7、`item` 5、`mixin/accessor` 4、`inventory/tooltip` 4、`client/tooltip` 4、`network` 3、`client/model` 3、`client/animation` 3、`api` 3、`mixin/client` 2、`interaction` 2、`config` 2、`blockentity` 2、根包 2、`util` 2；另有 `crafting`、`compat`、`client/screen` 各 1
- 最大文件：`gametest/HodgepodgeGameTests.java` 671 行、`gametest/MultiBlockPlateGameTests.java` 489、`block/AbstractHodgepodgeFeastBlock.java` 481、`blockentity/HodgepodgeFeastBlockEntity.java` 449、`block/AbstractMultiBlockPlateBlock.java` 410、`inventory/LunchBoxMenu.java` 365

## 3. 入口与注册
- 通用入口 `KaleidoscopeHodgepodge.java:22-42`（ModInitializer）：`CrashDiagnostics.install()` → KHDataComponents/KHBlocks/KHBlockEntities/KHItems/KHRecipes/KHMenus/KHCreativeModeTabs/KHCommands 顺序 init → PackingBagRotationHandler/LunchBoxSelectionHandler.init → `ConfigManager.start()`；`id()` 静态工厂（行 44-46）
- 客户端 `KaleidoscopeHodgepodgeClient.java:37-60`（ClientModInitializer）：写 `ItemModels.ID_MAPPER`（ingredient_display、wrapping_bag_gui、lunchbox）、`SpecialModelRenderers.ID_MAPPER`（custom_feast、custom_feast_asymmetry）、BlockEntityRenderers、MenuScreens、`ClientTooltipComponentCallback`
- 注册框架：不用 DeferredRegister，直接用 Fabric `Registry.register(BuiltInRegistries.X, id, value)`（`init/KHDataComponents.java:20-97`、`init/KHRecipes.java:12-21`）；`init/KHDataComponents` 注册 14 个 `DataComponentType`（DISH_NAME、HODGEPODGE_RECIPE、PACKING_BAG_*、LUNCH_BOX_*、CUSTOM_FEAST 等），是 mod 的状态载体

## 4. 核心系统
1. 自定义菜品摆放（feast）：`block/AbstractHodgepodgeFeastBlock.java` + `blockentity/HodgepodgeFeastBlockEntity.java` + `core/PlacedIngredient`、`core/PlacementSpace`、`core/IngredientPlacementTarget`、`core/IngredientHitTest`、`core/IngredientCollisionHeightMap`（把食材模型当实体体积处理，粗粒度 1/4 高度图，对应 GameTest `ingredientCollisionUsesCoarseQuarterHeightMap`）。
2. 菜品序列化 `core/FeastCodec.java:12-238`：`MAGIC="KHP"`、`VERSION=1`、`MAX_INGREDIENTS=360`，`encode(containerPath, CustomFeastData)` / `decode(String)` + 内嵌 `FormatException.asComponent()`，把整盘菜编码成可放进物品组件的短字符串（仓库根 `example_code.txt` 即该格式的实例）。
3. 打包袋 / 午餐盒：`core/PackingBagService`、`PackingBagContents/Mode`、`core/LunchBoxService`、`LunchBoxContents`、`inventory/LunchBoxMenu`（365 行）+ `client/screen/LunchBoxScreen`
4. API 层 `api/`：`IHodgepodge` 用 default 方法定义容器方块语义（placementBounds、allowsBoundaryPlacementProjection、recipeControllerPos、recipePlacementPos、placementIngredients、recipePlacementTarget、containerOutlineShape）、`@Service`（`UsedFor{BLOCK,ITEM,ENTITY,BLOCK_ENTITY}` + `EnvType`）、`ICustomAnimation`（@Environment(CLIENT)）
5. Mixin + @Accessor：`mixin/accessor/{PlateBlockAccessor(@Accessor("servings")), PotBlockEntityAccessor, StockpotBlockEntityAccessor, FoodBiteBlockAccessor}`；`mixin/PlateBlockMixin` `@Inject(method="useItemOn", at=HEAD, cancellable)`、`StockpotBlockEntityMixin` `@Inject(method="takeOutProduct", HEAD, cancellable)`、`AnvilMenuMixin` `@Inject(method="createResult", at=RETURN)`

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：3 个 payload record 实现 `CustomPacketPayload`，`StreamCodec.composite(...)` 组合（`network/RotatePackingBagPayload.java:11-23` 用 `BlockPos.STREAM_CODEC` + `InteractionHand.STREAM_CODEC`）；BulkPlacePackingBagPayload、SelectLunchBoxIngredientPayload 同类写法。
- 数据驱动：无 JSON 配方/数据包驱动，数据以 `Registry.register` + 命令（`init/KHCommands.java` 313 行）暴露；配方只有一个 `HodgepodgeRecipeResetRecipe`（`init/KHRecipes.java`）。
- 配置 `config/ConfigManager.java:5-20`：走 forgeconfigapiport 的 `ConfigRegistry.INSTANCE.register` + `ModConfigEvents.loading/reloading`，common 与 client 两个 toml，`GeneralConfig.Snapshot` 提供不可变快照与 `describe()`。
- datagen：无（未见 DataGenerator）。测试替代：`gametest/`（fabric-api gametest v1 `@GameTest`，`build.gradle.kts` 注册 gametest run 并输出 gametest-results.xml）+ `src/test` 11 个 JUnit 纯逻辑测试（FeastCodecTest、PlacementSpaceTest、IngredientHitTestTest、ConfigManagerTest 等）。

## 6. Mixin
- 配置 `src/main/resources/kaleidoscope_hodgepodge.mixins.json`：required=true、JAVA_25、主段 11 个（AnvilMenuMixin、CakeBlockMixin、FoodBiteBlockMixin、PlateBlockMixin、NormalRecipeRecordTransferMixin、PotBlockEntityMixin、StockpotBlockEntityMixin + 4 个 accessor）+ client 段 2 个（client.GuiGraphicsExtractorMixin、client.HumanoidModelMixin），`overwrites.requireAnnotations=true`
- 目标是 Kaleidoscope Cookery 的 Plates/Pot/Stockpot 与原版 AnvilMenu/CakeBlock，用 @Accessor 直读私有字段而非 AT 或反射

## 7. 值得学的 5 条
1. 把复杂摆放状态编码成带 MAGIC/VERSION 上限校验的短字符串（`core/FeastCodec.java:12-238`）→ 复杂数据塞进物品组件、可复制可分享。
2. 动态食材的碰撞用粗粒度高度图代替逐模型 AABB（`core/IngredientCollisionHeightMap.java`）→ 大量可变模型的性能与手感折中。
3. 用 mixin `@Accessor` 读取前置私有字段（`mixin/accessor/PlateBlockAccessor.java:8-11`）→ 不改前置源码就能扩展其数据。
4. Fabric GameTest + JUnit 双层测试（`gametest/HodgepodgeGameTests.java`、`src/test/.../FeastCodecTest.java`）→ 纯逻辑（codec/几何）先用 JUnit 跑，需要世界的用 gametest。
5. 配置用不可变 snapshot record 对外暴露（`config/ConfigManager.java:5-20`、`GeneralConfig.Snapshot`）→ 游戏线程与渲染线程安全读配置。

## 8. 公开 API（扩展型模组）
`com.moigferdsrte.kaleidoscopehodgepodge.api`：`IHodgepodge`（实现该接口即可让自定义容器方块复用杂烩的摆放/碰撞/轮廓语义）、`ICustomAnimation`（客户端自定义动画标记）、`@Service`（标注服务实现的用途与侧别）。此外 `init/KHDataComponents` 的 14 个 DataComponentType 均为 public 静态字段，外部可用 `KaleidoscopeHodgepodge.id(path)` 拼接键访问菜品数据。
