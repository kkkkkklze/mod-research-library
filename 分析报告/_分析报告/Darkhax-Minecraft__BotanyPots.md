# Darkhax-Minecraft/BotanyPots 源码分析报告

> 注：本地为瘦检出（`git ls-files` 2280 文件 / 磁盘 115），数据包与资源未落盘，关键资源用 `git show HEAD:<path>` 补读。

## 1. 基本信息

BotanyPots / mod_id `botanypots` / 作者 Darkhax / LGPL v2.1（`gradle.properties`）。MC 1.21.1，**多加载器** `common`+`fabric`+`neoforge`（`settings.gradle:35-38`）；NeoForge 21.1.209（moddev 2.0.112）、Fabric API 0.116.6+1.21.1、NeoForm、Parchment 2024.07.28、Java 21。构建靠自研 buildSrc 脚本（`multiloader-common/loader/secret-loader` 等）。关键依赖：**Bookshelf**（注册框架/工具，required）与 **Prickle**（配置），JEI 仅 `compileOnly`，Mixin 0.8.5 + MixinExtras 0.4.0。

## 2. 规模与包结构

90 个 `.java`，7546 行（common 88/neoforge 1/fabric 1）。主要包：`common.api.data.recipes{,.crop,.soil,.fertilizer,.interaction}`、`common.api.data.{display(.types,.render,.math),itemdrops,growthamount,components}`、`common.api.{context,command.generator}`、`common.impl.{block(.entity,.menu),command(.generator),config,data.*}`、`common.mixin`、`common.impl.addons.jei`。最大文件：`BotanyPotFileGenerator` 323、`BotanyPotBlockEntity` 278、`BotanyPotsContent` 233、`BasicCrop` 230、`BotanyPotBlock` 226、`MissingCommand` 222。

## 3. 入口与注册

`BotanyPotsMod.java` 只有常量、`CachedSupplier<Config>`、`WeakReference<RegistryAccess>` 与 `init()`，**无注册代码**；`NeoForgeMod`（`@Mod`，仅注册 `Capabilities.ItemHandler.BLOCK`→`SidedInvWrapper`，只对 `Direction.DOWN` 暴露）与 `FabricMod` 都只调 `BotanyPotsMod.init()`。注册集中在 `BotanyPotsContent.java:63` 实现的 Bookshelf `ContentProvider`（`defineBlocks/defineBlockEntities/defineRecipeTypes/defineRecipeSerializers/defineMenuType/defineItemComponents/defineAttributes/defineCommands/...`），经 `META-INF/services` 装载。组件注册写法（`:201`）：

```java
registry.add(CropOverride.TYPE_ID.getPath(), new DataComponentType.Builder<CropOverride>()
    .persistent(CropOverride.CODEC).networkSynchronized(CropOverride.STREAM).build());
```

另有 3 个自建 HashMap 注册表 `DisplayType`/`ItemDropProviderType`/`GrowthAmountType`，接口统一为 `register(id, codec, stream)`（`api/data/display/types/DisplayType.java:70`），由 `BotanyPotsPlugin.PLUGINS`（ServiceLoader）在 `defineBlockEntities` 内初始化（`:123-125`）。

## 4. 核心系统

**A. 数据驱动配方**：4 个 RecipeType（`soil/crop/pot_interaction/fertilizer`）+ 6 个 serializer（含 `block_derived_*`）。抽象 `Crop.java` 定义扩展点 `onHarvest/isGrowthSustained/getRequiredGrowthTicks/getDisplayState/onTick/onGrowthTick/canHarvest/getBaseYield/getYieldScale`；数据字段集中在 `BasicCrop.Properties`（`impl/.../BasicCrop.java:177`）：`input/soil/grow_time/display/light_level/drops/function/pot_predicate/yield/yield_scale`，可选字段均带默认值。

**B. 块→作物自动适配**：`impl/.../crop/BlockDerivedCrop.java` 只需 `block` 即可推导种子（Bookshelf `AccessorCropBlock.getSeed()` → 退化 `block.asItem()`）、成熟态（`CropBlock.getMaxAge()` 或 `@Accessor("max")` 取 `IntegerProperty.max`，`:139`）、收获态（`berries=true`、`MultifaceBlock` 面）、展示（`HALF/DOUBLE_BLOCK_HALF`→两块，否则 `AgingDisplayState`）与掉落（`BlockStateDrops`）。

**C. RecipeCache 索引**：`api/data/recipes/RecipeCache.java:87` 遍历 `BuiltInRegistries.ITEM`×全配方，对 `CacheableRecipe.canBeCached()/isCacheKey()` 建 `Multimap<Item,RecipeHolder<T>>`，未命中线性扫 `uncached`；由 `SidedReloadableCache` 在重载时重建并打印耗时/命中率。

**D. 生长与自动化**：`BotanyPotBlockEntity.java:81 tickPot()` 用 `TickAccumulator`(float) 管 `growthTime/growCooldown/exportCooldown`；`PotType.WAXED` 把 `growthTime` 设 `Float.MAX_VALUE` 冻结；比较器输出 `Mth.ceil(14f*progress)`；HOPPER 成熟后多次掷 `Helpers.getLootRolls` 存入 `STORAGE_SLOTS(3..14)` 再向下方 `inventoryInsert`。数值集中在 `impl/Helpers.java:81-118`：`growTime / (配置+土壤+工具效率+盆栽)`，产出 `baseYield + yieldScale*(土壤+盆栽+工具属性)`。

**E. 展示系统**：`DisplayType` 以 `typeId→(MapCodec,StreamCodec)` 做 dispatch，5 种内置类型，客户端用 `DisplayRenderer.bind(type, renderer)` 绑定，序列化与渲染解耦。

**F. 缺数据批生成**：`impl/command/MissingCommand.java` 的 `botanypots missing seeds|soils [include_saplings] [generate]` 扫全物品注册表，交给 `CropGenerator`（`canGenerateCrop`+`generateData`）产出 JSON 落盘，内容含 `bookshelf:load_conditions` 与 `botanypots:block_derived_crop`；兜底 `MissingCropGenerator` 按 `CropBlock/BonemealableBlock/SaplingBlock/BushBlock/珊瑚` + 标签 `forge:seeds`/`c:seeds`/`minecraft:flowers` 判定并按方块特征选土壤。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自定义包**（grep `CustomPacketPayload|RegisterPayload|SimpleChannel` 无命中）；同步靠 `getUpdateTag`（`BotanyPotBlockEntity.java:257`，剔除 `comparator_level`，只同步 `slot<=TOOL_SLOT`）+ 数据组件 `networkSynchronized`。
- 数据驱动：作物/土壤/肥料/交互全为数据包配方 JSON，并用 Bookshelf `ILoadCondition`（`ConfigLoadCondition`）让条目绑定配置开关。
- 配置：Prickle `ConfigManager.load(MOD_ID, new Config())` + `CachedSupplier` 惰性单例（`BotanyPotsMod.java:19`），分 Gameplay/Recipes/Visuals。
- datagen：无 gradle datagen；`BotanyPotFileGenerator` 调用点已被注释（`BotanyPotsContent.java:70`），实际靠命令生成器。

## 6. Mixin

`common/src/main/resources/botanypots.mixins.json` 含 3 个（fabric/neoforge 两个 mixin json 为空）。`MixinRecipeManager` → `RecipeManager.apply(...)` `@At("HEAD")`，把 `registries` 取出存弱引用，使配方解析期可用注册表；`AccessorConfigurableRegistryLookup` → `@Accessor("registryAccess")` targeting `ReloadableServerResources$ConfigurableRegistryLookup`；`AccessorIntegerProperty` → `@Accessor("max")` targeting `IntegerProperty`。

## 7. 值得学的 5 条做法

1. 主类零注册、注册集中到一个 `ContentProvider` 实现，跨加载器共享（`impl/BotanyPotsContent.java`）——多加载器内容型 mod。
2. 行为类型用自带注册表 + dispatch codec（`DisplayType`），附属只需 `register(id, codec, stream)`——可扩展的行为系统。
3. 小 API 用 ServiceLoader 而非 `@Mod` 事件（`api/BotanyPotsPlugin.java`），多加载器零适配。
4. 为数据包作者配自动化：`CropGenerator` + `missing seeds generate` 扫全注册表产 JSON，并写 `load_conditions` 防缺失报错（`impl/command/MissingCommand.java`）。
5. "按物品匹配配方"做 item→recipe 预索引 + 分侧重载失效（`api/data/recipes/RecipeCache.java`）——机器类方块通用。

## 8. 公开 API

包 `net.darkhax.botanypots.common.api.*`。扩展点：`BotanyPotsPlugin`（ServiceLoader，6 个 default 方法：土壤/作物生成器、展示类型、掉落提供器、生长量类型、客户端渲染绑定）、`CropGenerator`/`SoilGenerator`、抽象 `Crop/Soil/Fertilizer/PotInteraction`、`ItemDropProvider`、`GrowthAmount`、`Display`、`DisplayType.register`。外部接入：1) 写 ServiceLoader 插件；2) 写 `botanypots:crop/soil` 配方 JSON；3) Maven `net.darkhax.botanypots:botanypots-{neoforge,fabric,common}-1.21.1`（maven.blamejared.com）；4) `CropOverride`/`SoilOverride` 数据组件单物品覆盖。
