# Qelifern/IronFurnaces 源码分析报告

## 1. 基本信息

- Mod 名：Iron Furnaces；mod_id：`ironfurnaces`；作者 Qelifern (pizzaatime)、XenoMustache、BOLT_M4G1C
- 目标版本：MC `1.20.1`，**Forge** `47.2.0`（`gradle.properties:11-17`），Java 17，mappings 用 `official`（1.20.1）
- Gradle 插件：`net.minecraftforge.gradle [6.0,6.2)` + eclipse/idea/maven-publish（`build.gradle:1-6`）
- 许可证：GPLv3（`gradle.properties:24`，`mods.toml` 内 `${mod_license}`）
- 版本号 `4.1.8`，archivesName `${mod_id}-${mcversion}`
- 编译依赖：Forge（`forge_version_range=[46,)`）、Minecraft（`minecraft_version_range=[1.20, 1.21)`）、**JEI 15.20.0.112**（`gradle.properties:35-38`，`mods.toml` 中 `modId="jei"` 为可选依赖）；无前置库，是其他整合包 mod 的依赖对象

## 2. 源码规模与包结构

- 144 个 `.java`，10848 行（`find . -name '*.java' -exec cat {} + | wc -l`）
- 包结构（`src/main/java/ironfurnaces/`）：
  - `blocks/furnaces/`(12) + `blocks/furnaces/other/`(3)、`tileentity/furnaces/`(12) + `other/`(3)、`container/furnaces/`(12) + `other/`(3)、`gui/furnaces/`(12) + `other/`(3) —— **四个"三层镜像包"**，每个熔炉变体在四层各有一个类
  - `init/`(3：Registration / ModSetup / ClientSetup)、`network/`(3)、`recipes/`(2)、`capability/`(9)、`energy/`、`items/`(顶层 9) + `items/augments/`(6) + `items/upgrades/`(14)
  - `container/slots/`(5)、`util/`(6) + `util/container/`(1) + `util/gui/`(2)、`jei/`(1 + 若干分类类)、`update/`(2)、`blocks/`(1)、`IronFurnaces.java`、`Config.java`(489)
- 最大文件：`tileentity/furnaces/BlockIronFurnaceTileBase.java`(2222)、`container/furnaces/BlockIronFurnaceContainerBase.java`(817)、`gui/furnaces/BlockIronFurnaceScreenBase.java`(600)、`Config.java`(489)、`blocks/furnaces/BlockIronFurnaceBase.java`(431)、`init/Registration.java`(346)
- **仓库内只有 1 个非 Java 文件**：`src/main/resources/META-INF/mods.toml`。全仓库无任何 `.json`（无 data/ 无 assets/），配方与贴图不在此仓库（来源未确认）

## 3. 入口与注册

主类 `src/main/java/ironfurnaces/IronFurnaces.java`：`@Mod(IronFurnaces.MOD_ID)` + `@Mod.EventBusSubscriber(bus = MOD)`，构造函数里按顺序做四件事——注册网络、取 mod 事件总线、注册 CLIENT/SERVER 两个配置、`MOD_EVENT_BUS.register(Registration.class)` 后调 `Registration.init()`，最后按 `Config.checkUpdates` 决定是否起更新检查线程。

注册框架是**原生 DeferredRegister，7 个实例集中在 `init/Registration.java`**：

```java
private static final DeferredRegister<Block> BLOCKS = DeferredRegister.create(ForgeRegistries.BLOCKS, MOD_ID);
private static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID);
private static final DeferredRegister<BlockEntityType<?>> TILES = ...;
private static final DeferredRegister<MenuType<?>> CONTAINERS = ...;
public static final DeferredRegister<RecipeSerializer<?>> RECIPE_SERIALIZERS = ...;
public static final DeferredRegister<RecipeType<?>> RECIPE_TYPES = ...;
public static final DeferredRegister<CreativeModeTab> CREATIVE_MODE_TABS = ...;
```
（`Registration.java:56-62`；`init()` 在 `:65-74` 一次性 `register(modEventBus)`）

每个变体固定 4~5 条注册语句成组出现：BLOCK → ITEM(new ItemFurnace(block, props, speed)) → TILE(BlockEntityType.Builder.of) → CONTAINER(`IForgeMenuType.create` 并从 `data.readBlockPos()` 还原菜单)，例如铁、金、钻石……共 10 个 tier 熔炉 + Heater + 熔炉工厂/发电机/百万熔炉。创造标签页在 `:291-346` 用 `displayItems` 逐个 `output.accept`，**联动物品（ATM/Vibranium/Unobtainium）用 `if (ModList.get().isLoaded("allthemodium"))` 包住**。

## 4. 核心系统

**(1) 抽象基类 + 极薄变体子类（本 mod 的核心工程手法）**
- `BlockIronFurnaceBase`（abstract, 431 行）承担全部逻辑：方块状态只 4 个属性 `HORIZONTAL_FACING / LIT / TYPE(0..2) / JOVIAL(0..2)`（`BlockIronFurnaceBase.java:56-57,417-419`）；`use()` 按手持物分派到 `interactAugment / interactJovial / interactCopy / interactWith`（:108-128）；红石信号按 `furnaceSettings.get(8)` 模式与 `getComparatorInputOverride` 的槽位集合计算（:295-353）
- 具体变体类如 `BlockGoldFurnace` 只有 33 行：定义 `public static final String GOLD_FURNACE = "gold_furnace"`，override `newBlockEntity` 与 `getTicker`（后者调基类的 `createFurnaceTicker(level, type, Registration.GOLD_FURNACE_TILE.get())`）（`BlockGoldFurnace.java:14-32`）
- Tile 层同理：`BlockIronFurnaceTileBase`(2222 行, abstract) → `BlockGoldFurnaceTile` 只 override 4 个方法：`getCookTimeConfig()`（返回 `Config.goldFurnaceSpeed`）、`IgetName()`、`IcreateMenu()`、`getTier()`（返回 `Config.goldFurnaceTier.get()`）（`BlockGoldFurnaceTile.java:13-37`）——**"变体差异"被压缩成 4 个返回值**

**(2) 以 Config 为单一数据源的"分级"**
`Config.java` 为每个 tier 生成 3 组 `ForgeConfigSpec.IntValue`：`xxxFurnaceSpeed`(47-57)、`xxxFurnaceGeneration`(60-69)、`xxxFurnaceTier`(76-85)，另有全局 `furnaceEnergyCapacityTier0/1/2` 与 `recipeMaxXPLevel`。速度既影响 ItemFurnace 提示信息（`Registration.java:95`）也影响 tick 逻辑，改配置即改平衡性。

**(3) 槽位与能力（TIER 之上的三种"模式"）**
Slot 常量集中定义：`INPUT 0 / FUEL 1 / OUTPUT 2 / AUGMENT_RED 3 / AUGMENT_GREEN 4 / AUGMENT_BLUE 5 / GENERATOR_FUEL 6 / FACTORY_INPUT = {7..12}`（`BlockIronFurnaceTileBase.java:82-90`）。同一台机器通过 augment 切换 `Furnace/Generator/Factory` 三种形态，工厂模式再按 `getTier()` 递增输入槽数（`BlockIronFurnaceBase.java:301-328` 与 tick 内 `factoryCookTime[6] / factoryTotalCookTime[6] / usedRF[6]`）。
性能优化：**5 组 `LRUCache<Item, Optional<Recipe>>`**（普通 / blasting / smoking / generator / factory 各 6 槽一份），容量取 `Config.cache_capacity`（`:116-146`）。能量用 `FEnergyStorage extends Forge EnergyStorage` + `onEnergyChanged()` 回调，经 `LazyOptional` 暴露 `IEnergyStorage`（`:147-168`）。

**(4) 设置持久化与同步**
`util/FurnaceSettings.java` 把 **12 个虚拟索引**映射到 3 个 int 数组（`settings[6] / autoIO[2] / redstoneSettings[2] + augmentGUI + autoSplit`），`get/set(int index)` 用 switch 转换并统一触发 `onChanged()`；NBT 存 5 个键（`FurnaceSettings.java:74-86`）。客户端按钮 → `PacketSettingsButton(x,y,z,index,set)` → 服务端 `te.furnaceSettings.set(...)` + `setChanged()` + `markAndNotifyBlock`（`network/PacketSettingsButton.java:34-46`）。

**(5) 变体升级物品**
`items/upgrades/ItemUpgrade` 持 `Block from / Block to`，`useOn` 时若方块匹配 `from`：先把旧 tile 的 12 个字段（energyStorage、factoryCookTime、usedRF、cookTime、furnaceSettings、inventory…）逐个取出，`removeBlockEntity` + setBlock 换成 `to`，再**逐字段回填新 tile** 并 `placeConfig()`（`ItemUpgrade.java`）。共 14 个 upgrade 物品 + `ItemFurnaceCopy`（复制设置到 NBT `"settings"` 数组）。

**(6) 玩家能力**
两个 Forge Capability：`IPlayerFurnacesList`（记录玩家放置过的熔炉坐标，`PlayerFurnacesList` 用简单 List + 逐项坐标比对去重）与 `IPlayerShowConfig`，通过 `RegisterCapabilitiesEvent` + `CapabilityManager.get(new CapabilityToken<>(){})` 注册（`capability/CapabilityPlayerFurnacesList.java`、`ModSetup.java:33-38`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：Forge 老式 `SimpleChannel`（`network/Messages.java`），`NetworkRegistry.newSimpleChannel(id, () -> "1.0", s -> true, s -> true)`，`nextID()` 自增分配 id，注册 2 个包（`PacketSettingsButton`、`PacketShowConfigButton`）。序列化直接用 `ByteBuf.writeInt` / `buf.readInt`（非 FriendlyByteBuf codec），handle 内 `ctx.get().enqueueWork(...)` + `setPacketHandled(true)`。
- 配置：两个 spec —— `Config.CLIENT_CONFIG` 与 `Config.COMMON_CONFIG`（注册为 SERVER 类型，`IronFurnaces.java`），并额外调 `Config.loadConfig(spec, path)` 手动从 `config/ironfurnaces.toml` / `ironfurnaces-client.toml` 加载。分类常量 `general/furnaces/modded_furnaces/jei/updates/misc`（`Config.java:37-42`）。
- 数据驱动：仅 1 个自定义配方类型 `GeneratorRecipe implements Recipe<Container>` + 内部 `Serializer`，并注册 `RecipeType`（`recipes/GeneratorRecipe.java:18,86,95`）；无 datapack 注册表、无 datagen（`src/main/resources` 只有 mods.toml，无 `GatherDataEvent`）。
- 联动的条件包装：`util/RainbowEnabledCondition` 注册为 `CraftingHelper.register(...)` 的自定义配方条件（`ModSetup.java:29-31`），id 为 `ironfurnaces:rainbow`。
- 更新检查：`update/UpdateChecker` + `ThreadUpdateChecker extends Thread` 从 `raw.githubusercontent.com/Qelifern/IronFurnaces/<branch>/update/updateVersions.properties` 抓取版本并对比 changelog（借自 Ellpeck 的 Actually Additions）。

## 6. Mixin

**无**。全仓库无 `@Mixin`、无 mixin 配置、无 accessTransformer（`build.gradle:33` 处 accessTransformer 被注释掉）。所有扩展均通过 Forge 官方事件/能力/注册 API 完成。

## 7. 值得学的 5 条具体做法

1. **三层镜像包 + 极薄子类表达"方块变体"**：`blocks/tileentity/container/gui` 各一层，变体类只 override 个性方法（方块 2 个、Tile 4 个）。适用：需要 10+ 个只差数值/贴图的方块时，比 switch 一坨要清晰。文件：`src/main/java/ironfurnaces/blocks/furnaces/BlockGoldFurnace.java`
2. **每个 tier 的差异全部外置到 Config**：`Config.goldFurnaceSpeed / goldFurnaceTier / goldFurnaceGeneration` 三件套，Tile 用 `getCookTimeConfig()` 拉取。适用：整合包需要按包调平衡的机器 mod。文件：`src/main/java/ironfurnaces/tileentity/furnaces/BlockGoldFurnaceTile.java:18-36`
3. **把散字段打包成"虚拟索引设置表"**：`FurnaceSettings.get/set(int index)` 用 12 个索引统一读写 3 个数组，配 GUI 按钮与一个 `PacketSettingsButton(index, set)` 就能扩展任意开关，无需新增包。文件：`src/main/java/ironfurnaces/util/FurnaceSettings.java`
4. **LRUCache 缓存配方查询**：按 RecipeType × 6 个工厂槽各建一个缓存，容量来自 config，避免每 tick 遍历 recipeManager。适用：任何高频 tick 的机器。文件：`src/main/java/ironfurnaces/tileentity/furnaces/BlockIronFurnaceTileBase.java:116-146`
5. **升级物品"搬运"整个 BlockEntity 状态**：取出旧实例字段 → 换 block → 回填新实例，而不是序列化到 NBT；顺带 `placeConfig()` 重算派生值。适用：方块之间的原地升级/降级。文件：`src/main/java/ironfurnaces/items/upgrades/ItemUpgrade.java`

补充可学点：JEI 分类与催化剂全部用 `Config.enableJeiPlugin / enableJeiCatalysts` 开关包住（`jei/IronFurnacesJEIPlugin.java:93-94`），联动物品只在创造标签页显示处用 `ModList.get().isLoaded(...)` 判定（`Registration.java:338-345`）。

## 8. 公开 API（库/前置/API 类 mod）

不适用：Iron Furnaces 是内容型 mod，未提供公开 API 包或插件接口；第三方只能通过 Forge 的 Capability（`ironfurnaces:player_furnaces_list`、`show_config`）与自定义 RecipeType（`ironfurnaces:generator_blasting`）间接交互。
