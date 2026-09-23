# way2muchnoise/JustEnoughResources 源码分析报告

## 1. 基本信息

- Mod 名：Just Enough Resources（JER）；mod_id：`jeresources`；作者 way2muchnoise
- 目标版本（本地快照为最新分支）：MC `26.2`、Java 25、Fabric Loader 0.19.3 / Fabric API 0.155.2、NeoForge `26.2.0.35-beta`（`gradle.properties:15-30`）。**注意：不是 1.20.1/1.21.1 版本**，此分支已用 `Identifier` 取代 `ResourceLocation`、用 `IRecipeType.create(...)` 取代旧 JEI API
- 依赖 JEI `30.15.0.98`（`gradle.properties:33`）；Fabric 侧可选 Cloth Config 26.2.155 + ModMenu 20.0.1
- 构建：Architectury `3.5-SNAPSHOT` + `dev.architectury.loom-no-remap 1.17-SNAPSHOT` + `com.gradleup.shadow 9.4.1`，多模块 `CommonApi / Common / Fabric / NeoForge`（`settings.gradle.kts`、`build.gradle.kts:4-9`）；Parchment 映射 `2025.12.20`
- 许可证：“Don't Be a Jerk” non-commercial care-free license（`NeoForge/src/main/resources/META-INF/neoforge.mods.toml:5`）
- 编译依赖：Common 只 `api(project(":CommonApi"))` + `compileOnly` JEI common-api（`Common/build.gradle.kts:14-17`）

## 2. 源码规模与包结构

- 122 个 `.java`，7462 行（`find . -name '*.java' | wc -l`）。模块分布：Common 76、CommonApi 31、Fabric 8、NeoForge 7
- `Common/src/main/java/jeresources/` 下：`jei/`(20，含 dungeon/enchantment/mob/plant/villager/worldgen 六个子包)、`registry/`(6)、`util/`(17)、`entry/`(8)、`compatibility/`(4)+`api`(5)+`minecraft`(4)、`platform/`(5)、`json/`(2)、`proxy/`(2)、`reference/`(3)、`config/`(1)、`collection/`(1)
- `CommonApi/src/main/java/jeresources/api/`：31 个文件，`distributions/`(6)、`drop/`(2)、`render/`(4)、`restrictions/`(3)、`util/`(4)、`conditionals/`(4)，另有 9 个顶层接口
- 最大文件：`api/distributions/DistributionHelpers.java`(271)、`api/drop/LootDrop.java`(258)、`compatibility/api/PlantRegistryImpl.java`(220)、`entry/WorldGenEntry.java`(216)、`compatibility/api/MobRegistryImpl.java`(207)、`collection/TradeList.java`(179)、`util/LootTableHelper.java`(171)、`entry/MobEntry.java`(151)、`json/WorldGenAdapter.java`(144)

## 3. 入口与注册

- NeoForge 入口 `NeoForge/src/main/java/jeresources/neoforge/JEResources.java`：`@Mod(Reference.ID)`，构造函数按 `Dist` 选 `ClientProxy`/`CommonProxy`，注册 COMMON 配置并挂 `LevelEvent.Unload` 监听清空 MobRegistry/VillagerRegistry 的实体缓存（该文件:21-35）
- Fabric 入口 `Fabric/src/main/java/jeresources/fabric/JEResources.java`（同构）
- **没有方块/物品注册**——JER 是纯 JEI 展示型 mod：内容全部是“运行时收集的数据”，通过 `jeresources.jei.JEIConfig`（`@JeiPlugin implements IModPlugin`）注册进 JEI。`JEIConfig` 里声明 6 个 `IRecipeType`（mob/dungeon/worldgen/plant/enchantment/villager）并存进 `Map<Identifier, IRecipeType<?>> TYPES` 供后续 hide/unhide 分类（`Common/src/main/java/jeresources/jei/JEIConfig.java:33-53`）
- 数据装载链：`JEIConfig.registerCategories` → `Services.PLATFORM.getProxy().initCompatibility()`（:90）→ `CommonProxy.initCompatibility()` 依次 clear 五个 registry 再调 `Compatibility.init()`

## 4. 核心系统

**(1) 平台抽象 + 自研插件注入（本仓库最有价值的一段）**
- 用 `ServiceLoader` 做 loader 无关的平台层：`platform/Services.java` 用 `ServiceLoader.load(IPlatformHelper.class).findFirst()` 取 `IPlatformHelper`（`Common/src/main/java/jeresources/platform/Services.java`）
- 第三方 mod 通过 `IJERPlugin` + `@JERPlugin`（NeoForge）或 Fabric entrypoint `jer_mod_plugin` 接入，拿到 `IJERAPI`（`CommonApi/src/main/java/jeresources/api/IJERPlugin.java:10-14`、`JERPlugin.java`）
- 两端实现完全不同：Fabric 用 `FabricLoader.getEntrypoints(IJERPlugin.entry_point, IJERPlugin.class).forEach(p -> p.receive(instance))`（`Fabric/src/main/java/jeresources/fabric/FabricPlatformHelper.java:44-45`）；NeoForge **遍历 `ModList.getAllScanData()` 的注解扫描结果**，匹配 `Type.getType(JERPlugin.class)`，再 `Class.forName` + 反射 `newInstance()` 执行 `receive`（`NeoForge/src/main/java/jeresources/neoforge/NeoForgePlatformHelper.java:51-69`）
- 关键时序：`JERAPI.init()` 被 `pluginsInjected` 布尔量保证每会话只注入一次，注册结果**先缓冲再 `commit(boolean)` 重放**，因此数据包重载不需要重新询问插件（`Common/src/main/java/jeresources/compatibility/api/JERAPI.java:22-49`）；注释明确写了 MC 26.1+ ItemStack 必须在资源加载后才能构造，所以插件注入点刻意放在 `Compatibility.init()` 而非 mod setup

**(2) 六大 Registry + Impl 分离**
- 抽象侧 `CommonApi`/`registry/`（有独立 `jeresources.api.*Registry` 接口），实现侧 `Common/compatibility/api/*RegistryImpl`，`commit()` 时把缓冲数据灌进单例 `registry/*Registry.getInstance()`
- `MobRegistryImpl` 用**四张静态表**分职：`rawRegisters`（只给 LootTable → 稍后 `LootTableHelper.toDrops` 反查）、`preppedRegisters`（直接给 LootDrop）、`renderHooks`、`scissorHooks`（`MobRegistryImpl.java:24-27`）。`register(...)` 有 **7 个重载**做参数可选化，全部包在 try/catch 里，坏注册只打 `LogHelper.debug` 不打断（:34-160）
- 亮点：`applyScissorHooks` 用 `Thread.currentThread().getStackTrace()` 反查调用方类名来匹配 hook（最多上溯 10 层，:188-200）——避免 hook 注册需要传调用者

**(3) 世界生成数据模型 `WorldGenEntry`**
- 一份矿物：`block` + `deepSlateBlock` + `DistributionBase` + `Restriction` + `LootDrop[]`，6 个构造重载把 restriction/silktouch/deepslate 都变成可选参数（`entry/WorldGenEntry.java:29-69`）
- `calcChances()` 用 `float[256+64]` 分布数组（64 = 负 Y 空间）算出 minY/maxY 并量化到区块段（`:97-125`），`getAverageBlockCountPerChunk()` 直接对 320 长度数组求和（`:181-187`）
- `merge(WorldGenEntry)` 允许把多个来源的同种矿物合并（`DistributionHelpers.addDistribution`，:198-202）——处理"同矿物由多个 mod 的矿脉生成"

**(4) DI Y 数据（JSON 覆盖）**：`json/WorldGenAdapter.java`(144) + `ProfilingAdapter.java`(116)，当 `Settings.useDIYdata` 为 true 且包里有 DIY 数据时读入并**跳过原版世界生成收集**（`Compatibility.java:19-30`），即用户可手写 JSON 覆盖 JER 的挖矿数据。

**(5) JEI 展示层**：每个分类一套 `XxxCategory + XxxWrapper + XxxTooltip`（mob/plant/worldgen/dungeon/villager/enchantment 六个包），`reference/Resources.java` 用嵌套类集中管理 `BackgroundDrawable` 背景贴图常量与尺寸（`reference/Resources.java:7-23`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义 payload（纯客户端展示 mod）。
- 配置：平台分离——`config/Settings.java` 是 loader 无关的静态字段集合（`useDIYdata`、`excludedEnchants`、`hiddenCategories`、`excludedDimensions`、`ITEMS_PER_ROW/COLUMN`）；Fabric 用 Cloth Config（`Fabric/.../fabric/config/Config.java` + `ConfigFileHandler` + `JEResourcesModMenu`），NeoForge 用 `ModConfig.Type.COMMON`（`NeoForge/.../neoforge/config/Config.java`），两侧各自把值写回 `Settings`。
- datagen：**无**（无 `GatherDataEvent`、无 `src/generated`）。整个仓库 `src/main/resources` 只有 4 个文件（`jeresources.accesswidener`、`jeresources.mixins.json`、`accesstransformer.cfg`、`neoforge.mods.toml`）——贴图/语言文件不在本仓库内。
- 混入：仅 `Fabric/src/main/resources/jeresources.mixins.json`，且 `mixins` / `client` 数组**均为空**（`compatibilityLevel: JAVA_16`，未随 Java 25 更新）；全仓库 `grep -rn "@Mixin"` 无结果。改用 accesswidener / accesstransformer 访问原版成员。

## 6. Mixin

`Fabric/src/main/resources/jeresources.mixins.json` 为**空壳配置**（package `jeresources.fabric.mixin`，无实际类）；NeoForge 侧无 mixin 配置，只用 `NeoForge/src/main/resources/META-INF/accesstransformer.cfg`；Common 用 `Common/src/main/resources/jeresources.accesswidener`。**本分支实际不含 mixin 实现**。

## 7. 值得学的 5 条具体做法

1. **ServiceLoader 平台抽象**：Common 代码只认 `IPlatformHelper`，用 `ServiceLoader.load(...).findFirst()` 在运行期取实现，Common 成为真正的第三方无关模块。文件：`Common/src/main/java/jeresources/platform/Services.java`
2. **双 loader 插件发现**：同一 `IJERPlugin` 接口，Fabric 走 entrypoint、NeoForge 走 `ModFileScanData` 注解扫描 + 反射实例化。文件：`Fabric/src/main/java/jeresources/fabric/FabricPlatformHelper.java:40-46`、`NeoForge/src/main/java/jeresources/neoforge/NeoForgePlatformHelper.java:51-69`
3. **“先缓冲、后 commit”处理重载**：API 接收的注册进静态 List/Map，`commit()` 时才灌入真实 registry，配合 `pluginsInjected` 保证插件只调用一次。适用：数据包可重载的收集型 mod。文件：`Common/src/main/java/jeresources/compatibility/api/MobRegistryImpl.java:202-206`、`JERAPI.java:36-47`
4. **用调用栈反查调用方做 hook 匹配**：`registerScissorHook(Class caller, ...)` 存类名，渲染时 `getStackTrace()` 匹配并限制上溯 10 层。适用：需要知道"谁在调用我"而又不想污染 API 签名。文件：`Common/src/main/java/jeresources/compatibility/api/MobRegistryImpl.java:188-200`
5. **重载构造器把可选参数组合展开**：`WorldGenEntry` 用 6 个委托构造器把 `deepSlateBlock / restriction / silktouch` 变成可选，`MobRegistryImpl.register` 7 个重载同理。适用：给第三方写“零负担”API 时的取舍参考。文件：`Common/src/main/java/jeresources/entry/WorldGenEntry.java:29-69`

## 8. 公开 API（库模组）

- 根包：`jeresources.api`（独立 Gradle 模块 `CommonApi`，Common 以 `api(project(":CommonApi"))` 暴露）
- 核心入口：`IJERAPI`（提供 `getMobRegistry / getWorldGenRegistry / getPlantRegistry / getDungeonRegistry / getLevel`）与 `IJERPlugin`；NeoForge 用 `@JERPlugin` 注解标记实现类，Fabric 在 `fabric.mod.json` 声明 `jer_mod_plugin` entrypoint
- 扩展点接口：`IMobRegistry`、`IWorldGenRegistry`、`IPlantRegistry`、`IDungeonRegistry`
- 数据构造辅助：`api/drop/LootDrop`(258)、`api/drop/PlantDrop`、`api/distributions/`（`DistributionBase` 及 `DistributionSquare/Triangular/Custom/UnderWater` + `DistributionHelpers` 合并工具）、`api/restrictions/`（`Restriction`、`BiomeRestriction`、`DimensionRestriction`）
- 渲染扩展：`api/render/IMobRenderHook`（自定义怪物预览变换）、`IScissorHook`（裁剪区变换）、`ColorHelper`、`TextModifier`
- 条件/战利品辅助：`api/conditionals/`（`LightLevel`、`Conditional`、`ExtendedConditional`、`ICustomLootFunction`）、`api/util/`（`ItemHelper`、`BiomeHelper`、`LootConditionHelper`、`LootFunctionHelper`）
- 内部包 `jeresources.compatibility.*`、`jeresources.registry.*`、`jeresources.entry.*` 为 Common 内部实现，第三方应只依赖 `CommonApi`
