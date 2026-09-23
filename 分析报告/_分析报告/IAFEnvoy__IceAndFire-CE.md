# IAFEnvoy/IceAndFire-CE 源码分析报告

## 1. 基本信息

- Mod 名：Ice And Fire Community Edition（冰火传说社区版，原版 Ice and Fire 的非官方 fork）；`mod_id=iceandfire`；作者：IAFEnvoy、xiaowu、uoay（credits 标 Alexthe666）；`mod_version=2.2-alpha.3`
- 目标版本：`gradle.properties` `minecraft_version=26.1.2`、`neo_version=26.1.2.97`；Java 25（`build.gradle` java.toolchain 25）；许可证 LGPL-3.0；构建 `net.neoforged.moddev` 2.0.144 单模块
- 编译依赖（`build.gradle:139-149`）：`jarJar(com.github.IAFEnvoy.Integration:integration-neoforge:0.2)`（自家跨 mod 集成调度库，运行时代码用 `IntegrationExecutor.runWhenLoad("curios", ...)` 调用）、curse.maven `uranus-1010827`（自家前置库：Tabula 模型/动画、`DynamicItemRenderer`、`IArmorRendererBase`）、curse.maven `jupiter-1072905`（自家配置库）、`implementation curse.maven:jade`、`compileOnly` JEI 29.29.0.77 / curios 15.0.0+26.1.2；EMI/Ponder/ArsNouveau 兼容代码在 26.1.2 下被 `sourceSets.main.java.exclude` 排除（`:36-40`）
- `neoforge.mods.toml` 放在 `src/main/templates/`，由 `processResources { expand replaceProperties }` 展开生成（软编码 mod_id/version/license）；声明 `[[mixins]] config = "${mod_id}.mixins.json"` 与 `[[accessTransformers]]`

## 2. 源码规模与包结构

- 605 个 `.java`，60131 行（单模块）
- 主要包（`com.iafenvoy.iceandfire`，括号内文件数）：`entity/ai`(68)、`entity`(56)、`render/entity`(44)、`registry`(37)、`render/model`(36)、`item/block`(35)、`item`(29)、`entity/util`(21)、`item/tool`(18)、`render/entity/feature`(17)、`world/structure`(16)、`item/ability`(16)、`render/model/armor`(12)、`particle`(12)、`mixin`(12)、`item/block/entity`(10)、`data`(9)、`entity/util/dragon`(8)、`network/payload`(7)、`screen`(13)、`world/feature`(6)、`compat`
- 最大文件：`entity/DragonBaseEntity.java`(2899)、`entity/AmphithereEntity.java`(1091)、`HippogryphEntity.java`(997)、`HippocampusEntity.java`(887)、`SeaSerpentEntity.java`(869)、`screen/gui/bestiary/BestiaryScreen.java`(825)、`DeathWormEntity.java`(811)、`render/model/HippogryphModel.java`(767)、`GorgonModel.java`(729)、`CockatriceEntity.java`(723)
- 资源极薄：`src/main/resources` 只有 `assets/iceandfire/lang` 与 `META-INF`（json 共 1 个、nbt 0 个），模型为 `.bbmodel`/Tabula 格式且被 exclude，datagen 输出目录 `src/generated/resources` 未包含在仓库中

## 3. 入口与注册

`src/main/java/com/iafenvoy/iceandfire/IceAndFire.java:46`（`@Mod(MOD_ID)` + `@EventBusSubscriber`）构造器内：

```java
IafBestiaryPages.init(); IafDragonColors.init(); IafDragonTypes.init();
IafHippogryphTypes.init(); IafSeaSerpentTypes.init(); IafTrollTypes.init();
DragonColor.initArmors(); SeaSerpentType.initArmors(); IafSkullType.initItems(); TrollType.initArmors();
IafAttachments.REGISTRY.register(bus); ... // 21 个 DeferredRegister 依次 register(bus)
IafTrades.POI_REGISTRY.register(bus); IafTrades.PROFESSION_REGISTRY.register(bus);
```

`FMLCommonSetupEvent` 里 `IafTrades.registerPoiStates()`、`IafRecipes.init()`、`IafTiers.init()`。注册类统一放 `registry/`（37 个 `Iaf*`），全部是 `DeferredRegister` + `DeferredHolder` 静态字段模式，实体用私有 `build(name, factory, category, ...)` 封装 `EntityType.Builder`（`registry/IafEntities.java:27`），并把 `EntityAttributeCreationEvent`/`RegisterSpawnPlacementsEvent` 一起写在同一个类里。`registry/IafRegistrationContext.java` 是个有意思的兼容层：用 `ThreadLocal<ResourceKey<Block/Item>>` 在 `createBlock/createItem` 期间提供 ID，因为 MC 26.1.2 的 Block/Item 构造器开始需要 `ResourceKey`。配置注册用 Jupiter：`ConfigManager.getInstance().registerConfigHandler(IafCommonConfig.INSTANCE)` + `ServerConfigManager.registerServerConfig(..., PermissionChecker.IS_OPERATOR)`（可由 OP 在线改）。

## 4. 核心系统

1. **巨龙实体栈（本 mod 最有学习价值的部分）**：`entity/DragonBaseEntity.java:113` 一个抽象基类实现 12 个接口（`IFlyingMount`、`IMultipartEntity`、`IAnimatedEntity`、`IDragonFlute`、`IDeadMob`、`IVillagerFear`、`IHasCustomizableAttributes`、`ICustomSizeNavigator`、`ICustomMoveController`…），内部组合两个专用子系统：`IafDragonLogic`（攻击/繁殖/吼叫等状态机）与 `IafDragonFlightManager`（`entity/util/dragon/`，自研飞行：`approach`/`approachDegrees`/`degreesDifferenceAbs` 角度插值 + 自定义 `MoveControl`/`PathNavigation`/`NodeEvaluator`）；靠 `flyProgress`/`hoverProgress`/`fireBreathProgress`/`diveProgress` 等一整族 float 进度字段驱动动画插值。具体龙只需继承（`FireDragonEntity`/`IceDragonEntity`/`LightningDragonEntity`）
2. **变体描述用 record + Supplier 表**：`data/DragonType.java`（`record DragonType(String name, List<DragonColor> colors, Function<Level, DragonBaseEntity> hatchEntityCreator, Supplier<Item> skullItem, Supplier<Item> crystalItem, boolean piscivore)`）、`DragonColor`（含 `initArmors()`）、`SeaSerpentType`、`TrollType`、`IafSkullType`——颜色/装备/头颅/水晶全部由数据表驱动 `init()` 批量注册物品，避免给每个变体写类
3. **AI 按生物前缀分文件**：`entity/ai/` 68 个 Goal（`DragonAI*`、`CockatriceAI*`、`DeathWormAI*`、`DreadAI*`、`AquaticAI*`、`EntityAI*`），多为基础 Goal 的复制改写（如 `EntityAIAttackMeleeNoCooldownGoal`）
4. **物品能力（ability）系统**：`item/ability/` 16 个类 + `Ability`/`BuiltinAbilities`/`PostHitAbility`/`SwingHandAbility` 等接口，把"命中后点燃/冰冻/多段雷击/召唤闪电"做成可组合能力，挂在 `item/tool` 的龙钢工具上
5. **世界生成**：`world/structure/` 16 个结构（`DragonCave`/`DragonRoost` 各 3 属性 + `GorgonTemple`、`Graveyard`、`Mausoleum`、`PixieVillage`、`SirenIsland`、`HydraCave`、`CyclopsCave`），共用一个抽象基类 `IafJigsawStructure`（暴露 `start_pool`/`startJigsawName`/`size`/`start_height`/`project_start_to_heightmap`/`maxDistanceFromCenter`）；`world/DragonPosWorldData.java` 是 `SavedData`（`SavedDataType` + Codec，记录每只龙的 UUID→坐标），`world/DangerousGeneration.java` 是 default 方法接口，用配置的 `dangerousDistanceLimit` 保证危险结构离出生点足够远
6. **渲染与模型**：`render/` 共约 130 个类，模型走 Uranus 的 Tabula（`IafRenderers` 集中注册 `EntityRenderersEvent`/`RegisterParticleProvidersEvent`，模型 ID 如 `iceandfire:firedragon/firedragon_ground`，注释提示 Uranus 会给每个 Tabula 查找加 `models/tabula/` 前缀），动画器在 `render/model/animator/`（三属性各一个）

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/NetworkManager.java`（`@EventBusSubscriber`）`event.registrar("1")` 后集中注册 7 个 payload（5 个 playToClient、1 个 playToServer、1 个 bidirectional），每个 payload 自带 `ID` + `CODEC`；handler 分离到 `ServerNetworkHandlers`/`ClientNetworkHandlers`（`StartRidingMobPayload` 骑乘自定义飞行生物、`DragonControlC2SPayload` 玩家操控龙）
- 配置：两个 Jupiter 容器——`config/IafCommonConfig.java`（`extends AutoInitConfigContainer`，`super(Identifier.fromNamespaceAndPath(MOD_ID,"common"), "screen.iceandfire.common.title", "./config/iceandfire/iaf-common.json")`；字段按生物分内部类，每项用 `DoubleEntry.builder(...).min(1).key("maxHealth").build()` 声明）与 `IafClientConfig`，重复劳动极少
- 数据驱动：`registry/tag/` 7 个 Tag 类（`IafBlockTags`/`IafEntityTags`/`CommonBlockTags`/`CommonItemTags` 等做跨 mod 通用 tag）；`data/` 里的 `DragonType` 等表不是 datapack registry 而是硬编码静态表（未使用 datapack registry）
- datagen：`build.gradle` 有 `data` run config（`--output src/generated/resources/ --existing src/main/resources/`）且 `sourceSets.main.resources.srcDir('src/generated/resources')`，但**仓库内未包含 datagen 包**（未确认是否在其它分支/CI 生成）

## 6. Mixin

- 配置：`src/main/resources/iceandfire.mixins.json`——`package: com.iafenvoy.iceandfire.mixin`、`compatibilityLevel: JAVA_21`（注意与 26.1.2/Java 25 目标不一致，可能是未更新）、`mixins` 9 个 + `client` 3 个、`injectors.defaultRequire: 1`
- 代表类与注入点：
  - `mixin/MobMixin.java` → `Mob#dropFromLootTable(ServerLevel, DamageSource, boolean, CallbackInfo)` HEAD，给凋灵骷髅额外掉 `IafItems.WITHERBONE`（源码注释标 `//FIXME::Loot table modifiers`，说明作者知道正规做法是 GLM）
  - `mixin/WorldGenRegionMixin.java` → `WorldGenRegion#ensureCanWrite` 中 `Util.logAndPauseIfInIde` 调用点 cancel，抑制龙穴生成超范围方块时的日志刷屏（结构类 mod 常见痛点）
  - 访问器/钩子：`EntityIdAccessor`、`LivingEntityAccessor`、`ServerLevelMultipartAccessor`（配合自研多部件实体）、`LivingEntityMixin`、`BlockPropertiesMixin`、`ItemPropertiesMixin`
  - client：`client/EntityHitboxDebugRendererMixin`、`PanoramaRendererMixin`、`TitleScreenMixin`

## 7. 值得学的 5 条具体做法

1. **超大类拆"基类 + 专用子系统对象"**：`DragonBaseEntity`(2899 行) 只保留状态与字段，把飞行交给 `IafDragonFlightManager`、攻击交给 `IafDragonLogic`。文件：`entity/DragonBaseEntity.java`、`entity/util/dragon/`。适用：复杂飞行/多阶段 Boss 实体。
2. **"飞行姿态"用一族进度 float + `approach` 插值**：`flyProgress`/`hoverProgress`/`diveProgress`/`swimProgress` 与静态工具 `approach/approachDegrees`（`entity/util/dragon/IafDragonFlightManager.java:36-45`）。适用：任何需要在客户端平滑插值的飞行动物动画。
3. **变体用 record + `Supplier<Item>` 数据表**：`data/DragonType.java` 一行描述"龙的类型"，`DragonColor.initArmors()` 批量产出盔甲变体。适用：颜色/材质矩阵型内容（龙、马铠、宝石）。
4. **配置用 Jupiter 的 `AutoInitConfigContainer` + 反射式 Entry**：`config/IafCommonConfig.java`，每项 `DoubleEntry.builder(...).key(...).build()` 自带范围校验、i18n key、分组，且能 `ServerConfigManager` 注册成 OP 可改。适用：不想手写 TOML 读写的 mod。
5. **`ThreadLocal` 形式的注册上下文**：`registry/IafRegistrationContext.java` 在 `createBlock/createItem` 内部临时暴露 `ResourceKey` 给需要它的构造器（`with()` 里 try/finally 还原）。适用：上游/原版构造签名变更、不便改所有子类时。

## 8. 公开 API

非库 mod，无 API 包。对外兼容方式：`compat/` 下按 mod 分文件（jade/jei/emi/ponder/curios/ArsNouveau），用 `ModList.get().isLoaded(...)` 与 `IntegrationExecutor.runWhenLoad(...)`（来自 jarJar 内嵌的 `com.iafenvoy.integration`）延迟加载，避免硬依赖；`registry/tag/Common*Tags` 提供与通用 tag 的互通。
