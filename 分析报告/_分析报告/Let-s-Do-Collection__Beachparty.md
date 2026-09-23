# Let-s-Do-Collection/Beachparty 源码分析报告

## 1. 基本信息

- Mod 名：[Let's Do] Beachparty / mod_id：`beachparty` / 作者：Satisfy、Jason13（credits: MissLilitu）
- 目标：MC 1.21.1，**Architectury 多平台（Fabric + NeoForge）**，三模块 `common` / `fabric` / `neoforge`（`settings.gradle`）
- 版本：mod_version 2.1.4；fabric_loader 0.16.14、fabric_api 0.116.3+1.21.1、neoforge 21.1.192、architectury 13.0.8（`gradle.properties`）
- Gradle 插件：根 `build.gradle` = architectury-plugin 3.4-SNAPSHOT + dev.architectury.loom 1.9-SNAPSHOT；fabric 侧额外 shadow 8.0.0 / minotaur / cursegradle
- 许可证：`neoforge.mods.toml:5` = "All Rights Reserved"，`fabric.mod.json` = "Custom"
- 编译依赖（谁是 API）：architectury（必需，`neoforge.mods.toml:38-43` required）；cloth-config（fabric 配置）、trinkets(fabric)/curios(neoforge) 饰品、REI 16.0.799 / JEI 19.22.0.315 / modmenu（仅客户端兼容，`fabric/build.gradle:39-51`）

## 2. 源码规模与包结构

- **166 个 `.java`，13202 行**（`find ... -name '*.java' | wc -l` / `cat {} + | wc -l`）；git 跟踪 964 文件，其中 resources/data 244、resources/assets 530
- 主要包（第 3 层，均在 `common/src/main/java/net/satisfy/beachparty/`）：`core/block`（+`core/block/entity`）最大、`core/registry`、`core/entity`(+goals)、`core/item`、`core/recipe`、`core/mixin`、`core/world/placers`、`core/compat/{jei,rei}`、`core/event`、`client/{gui,model,renderer}`、`platform`；平台侧 `fabric/.../fabric`、`neoforge/.../neoforge`
- 最大文件：`core/block/HoodedBeachChair.java`(341)、`SandBucketBlock.java`(340)、`BeachGoalBlock.java`(294)、`BeachSunLounger.java`(284)、`block/entity/PalmBarBlockEntity.java`(265)、`fabric/core/compat/BeachpartyTrinket.java`(245)、`CuriosWearableTrinket.java`(229)、`client/renderer/block/PalmSignRenderer.java`(226)、`core/util/BeachpartyUtil.java`(221)、`MiniFridgeBlockEntity.java`(213)

## 3. 入口与注册

common 无 `@Mod`：`Beachparty.MOD_ID="beachparty"`，`Beachparty.init()` 手工按序调用各注册表（common/src/main/java/net/satisfy/beachparty/Beachparty.java:8-18）：

```java
public static void init() {
    ObjectRegistry.init(); EntityTypeRegistry.init(); TabRegistry.init();
    PlacerTypeRegistry.init(); MobEffectRegistry.init(); SoundEventRegistry.init();
    ScreenHandlerTypeRegistry.init(); CommonEvents.init(); RecipeTypeRegistry.init();
}
```

- NeoForge：`@Mod(Beachparty.MOD_ID)` + 构造注入 `(IEventBus, ModContainer)`（neoforge/.../BeachpartyNeoForge.java:32-42），平台专用 `DeferredRegister<EntityType<?>> ENTITY_TYPES` 在此 register
- Fabric：`ModInitializer` `BeachpartyFabric`（fabric.mod.json entrypoints.main/client/rei_client/jei_mod_plugin/modmenu 五个入口）
- 注册框架：**Architectury 的 `dev.architectury.registry.registries.DeferredRegister/Registrar/RegistrySupplier`**（common/ObjectRegistry.java:42-45），物品/方块同一 id 用 `BeachpartyUtil.registerWithItem(...)`（BeachpartyUtil.java:49-62）
- 平台差异：`@ExpectPlatform` 的 `PlatformHelper`（platform/PlatformHelper.java:15-38）+ `platform.{fabric,neoforge}.PlatformHelperImpl`

## 4. 核心系统

1. **统一注册辅助层**：`core/util/BeachpartyUtil.java` 提供 registerWithItem / registerWithoutItem / registerItem（同一 ResourceLocation 同时建 Block 与 BlockItem）、`registerColorArmor/Weapon` 颜色、`onUse/onStateReplaced` 方块交互复用；`ObjectRegistry` 只用一行声明式登记 ~100 个对象。
2. **坐具系统**：伪实体 `core/entity/ChairEntity.java` + `BeachpartyUtil.java:105-151`（`addChairEntity/removeChairEntity/getChairEntity/isOccupied/getPreviousPlayerPosition/isPlayerSitting`）；座块（`HoodedBeachChair`、`BeachSunLounger`、`BeachTowelBlock`）统一 `pushReaction(PushReaction.IGNORE)`、`instabreak()`，并与「睡床设重生点」交互（`BeachpartyNeoForge.playerSetSpawn` / fabric `EntitySleepEvents.ALLOW_SETTING_SPAWN`）。
3. **自定义配方 + 容器**：`core/recipe/PalmBarRecipe.java`（`matches` → `BeachpartyUtil.matchesRecipe(input, 1, 4)`，`assemble` 返回 EMPTY 表示产出由方块实体负责）、`MiniFridgeRecipe`（1→1 + `craftingTime`）；`PalmBarBlockEntity`(265 行) 实现 `WorldlyContainer, MenuProvider`，常量 `CAPACITY=5 / SLOTS_FOR_UP={1} / SLOTS_FOR_DOWN={0} / OUTPUT_SLOT=0`，`shakingTime/totalShakingTime` + `ContainerData` 同步进度，`getAllRecipesFor(RecipeTypeRegistry.PALM_BAR_RECIPE_TYPE.get())` 每 tick 查配方。
4. **生物 AI 与方块互动**：`core/entity/goals/ApproachSandCastleGoal.java` — 60tick 冷却 `canUse`、200tick 重算 `SandCastleManager.getNearestSandCastle`、`distanceToSqr<=16` 维持、抵达 2.25 停止；通过 `ZombieMixin`(注入 `registerGoals` TAIL) + `MobAccessor`(`@Accessor("goalSelector")`) 动态加目标。
5. **跨平台事件层**：`core/event/CommonEvents.java` 全用 Architectury 事件（`LootEvent.MODIFY_LOOT_TABLE`→`LoottableInjector.InjectLoot` 改战利品表；`PlayerEvent.ATTACK_ENTITY` 泳池浮条击退；`EntityEvent.LIVING_HURT` 遮阳伞下火焰伤害 ×0.96）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无自研包**（grep 仅命中原版 `ChairEntity/PalmBoatEntity` 同步与 recipe 的 `StreamCodec`），同步依赖原版容器/BE 机制
- 数据驱动：原生 JSON recipes / loot table / 树形 placer（data 244 文件）；JEI 分类 `core/compat/jei`、REI `core/compat/rei`
- 配置：Fabric 用 cloth-config `AutoConfig + GsonConfigSerializer`（ConfigFabric + 自定义 `ModMenu`），NeoForge 用 `ModConfigSpec`（BeachpartyNeoForgeConfig），common 侧经 `PlatformHelper.allowBottleSpawning()/getBottleMaxCount()/getBottleSpawnInterval()` 读到同一组语义
- datagen：**无**（无 `GatherDataEvent` 命中）

## 6. Mixin

- 配置：`common/src/main/resources/beachparty-common.mixins.json`（fabric 用）+ `neoforge/src/main/resources/beachparty.mixins.json`；`beachparty.accesswidener` 提供 AW
- 同一个类在 common 与 neoforge 各存在一份（Architectury 双份 mixin 的典型写法）：`ZombieMixin`(@Mixin(Zombie) `@Inject registerGoals TAIL`)、`ServerLevelTickMixin`(@Mixin(ServerLevel) `tick` TAIL → `MessageInABottleSpawner.tick`)、`PotionItemMixin`(`useOn` HEAD cancellable)、`HayBaleBlockMixin`(@Mixin(Block) `setPlacedBy` HEAD)、`MobAccessor`(`@Accessor("goalSelector")`)

## 7. 值得学的 5 条具体做法

1. 「注册 = 一行」：`BLOCKS/ITEMS` 两个 DeferredRegister + `registerWithItem(name, supplier)` 一次生成 Block+BlockItem — `common/.../core/registry/ObjectRegistry.java:42-45,184-194`；适用于任何装饰/食物类 mod。
2. 平台差异只做「值 + 实体类型注册」两件事，其余全在 common：`PlatformHelper`(@ExpectPlatform) 暴露配置读值与 `registerBoatType` — `common/.../platform/PlatformHelper.java:26-38`；适用于双加载器库化。
3. 配方「匹配逻辑共享、产出交给方块实体」：`BeachpartyUtil.matchesRecipe(input, start, end)` 复用于两个自定义配方（PalmBarRecipe/MiniFridgeRecipe）。
4. AI 目标用 mixin 按条件挂载而不是全量替换：`ZombieMixin` 注入 `registerGoals` TAIL + `@Accessor goalSelector` — 见 `core/mixin/*`；适用于给原版怪加自定义行为。
5. 世界级「定时投放」用 `ServerLevel.tick` TAIL 注入 + 配置项限流（`MessageInABottleSpawner.tick` + `PlatformHelper.getBottleSpawnInterval/MaxCount`）；替代每 tick 扫描实体。
