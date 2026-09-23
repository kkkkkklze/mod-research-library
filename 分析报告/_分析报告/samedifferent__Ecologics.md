# samedifferent/Ecologics 源码分析

## 1. 基本信息

- Mod 名：Ecologics / mod_id：`ecologics` / 作者：SameButDifferent, Zero_DSRS_VX, Drigonis, Crispytwig, Irishjevil, Foquito Azul（`forge/src/main/resources/META-INF/mods.toml`）
- 目标：MC `1.19.3`、Fabric + Forge 双平台（`enabled_platforms=fabric,forge`），Java 17；`forge_version=1.19.3-44.1.0`，`fabric_api_version=0.75.1+1.19.3`
- Gradle 插件：`architectury-plugin` 3.4-SNAPSHOT + `dev.architectury.loom` 0.12.0-SNAPSHOT（`build.gradle:2-3`），三层工程 `common`/`fabric`/`forge`
- 许可证：MIT。编译依赖：Cloth Config（`cloth_fabric_version=9.0.94`，Fabric 侧用 `me.shedaniel.autoconfig`）、ModMenu（`modmenu_version=5.0.2`）用于可选整合
- 它是纯内容 Mod（生物/方块/世界生成），不对外提供 API

## 2. 源码规模与包结构

- 96 个 `.java`，共 6876 行；common/fabric/forge 三段
- common 包（`samebutdifferent/ecologics/`）：`entity`（+`ai/navigation`）、`block`（+`entity`/`grower`/`properties`）、`client`（`model`/`renderer`）、`item`、`effect`、`registry`、`worldgen`（`feature`/`foliageplacers`/`trunkplacers`）、`platform`、`mixin`
- 最大文件：`entity/Penguin.java` 533、`entity/Squirrel.java` 377、`fabric/EcologicsFabric.java` 302、`entity/CoconutCrab.java` 280、`forge/EcologicsForge.java` 269、`entity/Camel.java` 269、`entity/ModChestBoat.java` 191

## 3. 入口与注册

- Fabric：`fabric/.../fabric/EcologicsFabric.java:52-63`（`ModInitializer`）注册 AutoConfig、`Ecologics.init()`、属性、事件、群系特性注入、刷怪、创造模式标签页。
- Forge：`forge/.../forge/EcologicsForge.java:55-76`（`@Mod`），把每个 `DeferredRegister` 逐个 `register(bus)`，`FMLCommonSetupEvent` 里 `enqueueWork(Ecologics::commonSetup)`。
- 共享初始化与内容声明分离：`common/.../Ecologics.java:32-43` 的 `init()` 只调各 `Mod*` 注册类的 `init()`；`commonSetup()`（45-52）集中做跨平台后置注册。

**注册框架是自建的平台抽象**（`common/.../platform/CommonPlatformHelper.java`）：全部方法标 `@ExpectPlatform` 并抛 `AssertionError`，由 `fabric/.../platform/fabric/CommonPlatformHelperImpl.java`(129 行) 与 `forge/.../platform/forge/CommonPlatformHelperImpl.java`(132 行) 提供实现。所以 `registry/ModEntityTypes.java:13-18` 这类注册表写法与加载器无关：

```java
public static final Supplier<EntityType<Penguin>> PENGUIN =
    CommonPlatformHelper.registerEntityType("penguin", Penguin::new,
        MobCategory.CREATURE, 0.7F, 0.9F, 10);
```

## 4. 核心系统

1. **平台抽象层**：`CommonPlatformHelper`（141 行）声明 20+ 个 `@ExpectPlatform` 方法（注册方块/物品/实体/音效/药水/树干与树冠类型、`setFlammable`、`registerSpawnPlacement`、`registerCompostable`、`registerStrippables`、`registerWoodType`、`registerBrewingRecipe`）。Forge 侧用 `DeferredRegister` 汇总注册，Fabric 侧用 `Registry.register` + `FabricDefaultAttributeRegistry`。
2. **实体与 AI**：`entity/Penguin.java` 是范本——`registerGoals`（84-98）组合原版 Goal 与自定义 Goal（`PenguinSearchForItemsGoal`/`PenguinMeleeAttackGoal`/`PenguinRandomSwimmingGoal`，478-532），自建 `PenguinPathNavigation extends WaterBoundPathNavigation`（391-409，用 `AmphibiousNodeEvaluator`）与 `PenguinLookControl`（411-440，限制头部偏转并身体跟随）。「怀孕—延迟生子」状态用 `SynchedEntityData` 同步 + `addAdditionalSaveData` 持久化（61、154-170），`aiStep` 里随机 3000 tick 后生成幼体（204-217）。
3. **世界生成**：`worldgen/feature/`（`CoastalFeature`、`DesertRuinFeature`、`ThinIceFeature`）+ 自定义 `CoconutFoliagePlacer`、trunk placer，注册类为 `ModFeatures`/`ModFoliagePlacerTypes`/`ModTrunkPlacerTypes`；平台侧通过 `BiomeModifications.addFeature/addSpawn`（Fabric，`EcologicsFabric.java:207-298`）或 Forge 的 biome modifier 注入。
4. **方块/物品**：`block/PotBlock`（可凿刻状态，`state.cycle(PotBlock.CHISEL)`）、`HangingCoconutBlock`、`SandcastleBlock`、`ThinIceBlock`、`SurfaceMossBlock`、自定义 `ModWoodType`（在 Forge/Fabric 各需不同 `WoodType.register`）。
5. **兼容与迁移**：Forge 侧 `MissingMappingsEvent` 把旧 ID（`coconut_husk`→`coconut_seedling`）自动重映射（`EcologicsForge.java:249-269`），这是给老存档升级用的实用手法。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包，实体同步用原版 `SynchedEntityData`。
- 配置：Fabric 用 Cloth Config AutoConfig（`ModConfigFabric`），Forge 用 `ModConfigForge.COMMON_CONFIG`（`ModConfigSpec`）；同一份配置语义在两端各写一次（`registry/fabric`、`registry/forge` 包）。
- datagen：`fabric/src/generated/resources` 存在（Fabric 侧生成），common 内未见统一 `DataProvider`（未确认其完整覆盖面）。
- Mixin 配置三份：`common/src/main/resources/ecologics-common.mixins.json`（4 项：`AzaleaTreeGrowerMixin`、`CamelMixin`、`CarpetBlockMixin`、`LivingEntityMixin`）、`fabric/.../ecologics.mixins.json`（8 项，含 `PotionBrewingAccessor`、`SpawnPlacementsAccessor`、`WoodTypeAccessor` 等 `@Accessor`）、`forge/.../ecologics.mixins.json`（`FireBlockAccessor`、`AxeItemAccessor`）。

## 6. Mixin

见上；代表性：`common/.../mixin/AzaleaTreeGrowerMixin.java`（改杜鹃树生长）、`common/.../mixin/CamelMixin.java`（骑乘/冲刺）、`fabric/.../mixin/fabric/WoodTypeAccessor.java` 与 `SpawnPlacementsAccessor`（用 `@Accessor` 访问私有 Map/集合以绕开平台差异）——**用 Mixin 补齐平台 API 缺失**是这套 architectury 工程的核心思路。

## 7. 值得学的 5 条做法

1. `@ExpectPlatform` 静态方法 + 两侧 Impl：注册与平台专有逻辑全部走同一入口，业务代码零平台判断（`common/.../platform/CommonPlatformHelper.java`）。
2. 把注册集中成一个 `Registry` 聚合类，`init()` 与 `commonSetup()` 分离，避免跨平台初始化顺序问题（`common/.../Ecologics.java:32-52`）。
3. 实体用「内部静态 Goal 类 + 构造器注入宿主」组织 AI，避免为每个 Goal 建独立文件（`entity/Penguin.java:442-532`）。
4. 存档 ID 迁移用 `MissingMappingsEvent.remap`（`forge/.../EcologicsForge.java:249-269`）。
5. 双平台资源/配置类分目录（`registry/fabric`、`registry/forge`）但仍共享 `common` 的字段名，保证配置语义一致。

## 8. 库/API 说明

非库 Mod；无对外 API 包。仅提供原版世界生成的注入点（`ModFeatures`/`ModFoliagePlacerTypes`/`ModTrunkPlacerTypes`）供数据包使用。
