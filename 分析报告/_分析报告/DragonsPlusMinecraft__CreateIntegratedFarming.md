# DragonsPlusMinecraft/CreateIntegratedFarming 源码分析报告

> 本地 bulk 导出不含 `src`（工作区只有根文件）；本报告全部数据通过 `git show HEAD:<path>` 读取 git 对象（HEAD=`44838f0`）。

## 1. 基本信息
- Mod 名 Create: Integrated Farming（CIF）；`mod_id=create_integrated_farming`；作者 DragonsPlus；版本 1.4.1c。
- MC 1.21.1 + NeoForge 21.1.248（`neo_version_range=[21.1.0,)`）；Java 21；Parchment `2024.11.17`。
- Gradle：`net.neoforged.moddev` 2.0.141 + `me.modmuss50.mod-publish-plugin` + spotless；`src/main/templates/META-INF/neoforge.mods.toml` 模板生成元数据；带 accesstransformer。许可证 LGPL-3.0-or-later。
- 编译依赖：Create `[6.0.10,)`、**CreateDragonsPlus `[1.11.1,)`（必需前置，提供 `CDPRegistrate`）**、`jarJar` 内嵌 conditional-mixin 0.6.4；compileOnly JEI 19.21 / Curios 9.5.1。
- 可选集成（21 个）：farmersdelight、netherdepthsupgrade、mynethersdelight、corndelight、crabberdelight、culturaldelights、hearthandharvest、festivedelight、delightoflight、twilightdelight、untitledduck、environmental、autumnity、windswept、nethersexoticism、vanillabackport、tide、starcatcher、confluence、sable(+aeronautics)、createenchantablemachinery。

## 2. 源码规模与包结构
- git HEAD 共 254 个 `.java`，17482 行；`src/main` 99 个文件，其余 155 个分布在 21 个集成 sourceSet（untitledduck 37、farmersdelight 18、vanillabackport 16、sable/confluence 各 15）。
- 主包 `plus.dragons.createintegratedfarming`：`common/fishing/net(15)`、`common/registry(10)`、`common/ranching/roost/display(8)`、`common/ranching/roost(8)`、`mixin/create(7)`、`common/ranching/roost/chicken(7)`、`common/farming/vacuum(6)`、`client/ponder(5)`、`client/ponder/scene(4)`、`data(4)`、`config(3)`、`common/network(3)`、`client/renderer(3)`、`api/harvester(3)`、`common/farming/harvest`。
- 最大文件：`integration/sable/.../SableFishingNetController.java`(616)、`client/compat/jei/RoostingCategory.java`(346)、`common/ranching/roost/display/RoostingLootTableParser.java`(340)、`common/farming/vacuum/VacuumHarvesterBlockEntity.java`(279)、`client/ponder/scene/VacuumHarvesterScene.java`(278)、`common/ranching/roost/AnimalRoostBlockEntity.java`(276)、`api/harvester/CustomHarvestBehaviour.java`(190)。

## 3. 入口与注册
`common/CIFCommon.java:43` 为 `@Mod`，注册器同样是 CDP 的 `CDPRegistrate`：
```java
public CIFCommon(IEventBus modBus, ModContainer modContainer) {
    REGISTRATE.addRawLang(...);                       // 大量 addRawLang 内联文案
    REGISTRATE.registerEventListeners(modBus);
    CIFCreativeModeTabs/CIFBlocks/CIFBlockEntities/CIFArmInteractionPoints/CIFDataMaps.register(modBus);
    CIFPackets.register(modBus); RoostingDisplaySync.register();
    FishingNetCatchProviders.register(asResource("vanilla"), FishingNetMedium.WATER,
        context -> context.level().getServer().reloadableRegistries()
            .getLootTable(BuiltInLootTables.FISHING).getRandomItems(context.lootParams()));
}
@SubscribeEvent public void onCommonSetup(FMLCommonSetupEvent e) {
    e.enqueueWork(CIFBlockSpoutingBehaviours::register); ...CIFRoostCapturables/CIFRoostingDisplayProfiles... }
```
另有 `client/CIFClient`、`data/CIFData`（先判 `DatagenModLoader.isRunningDataGen()`）两个 `@Mod` 入口。

## 4. 核心系统
1. **真空收割机** `common/farming/vacuum`：`VacuumHarvesterBlockEntity extends KineticBlockEntity`，18 格 `ItemStackHandler` + `ItemHandlerWrapper{insertItem→返回原 stack}` 做"只出不进"输出；`chargeProgress/releaseTicks/headOffset` 动画状态；收割逻辑拆到 `VacuumHarvesterCycle`/`VacuumHarvesterHarvesting`/`VacuumHarvesterEffects`/`VacuumHarvesterMovementBehaviour`（可装到装置上）。
2. **动力渔网** `common/fishing/net`：`FishingNetMedium{WATER, LAVA}` 介质枚举；`FishingNetCatchProviders` 用 `EnumMap<Medium, LinkedHashMap<ResourceLocation, Provider>>` + `synchronized register` + `putIfAbsent` 重复校验，捕获时按介质随机挑一个 provider；`FishingNetBlock`/`LavaFishingNetBlock`、`FishingNetMovementBehaviour`（装置化）、`FishingNetFakePlayer`、`FishingNetEntityCaptures`。
3. **栖架/养鸡** `common/ranching/roost`：`RoostBlock`/`ChickenRoostBlock`/`BirdRoostBlock`/`AnimalRoostBlockEntity`/`TaggedAnimalRoostBlockEntity`；`RoostCapturable`（`SimpleRegistry<EntityType<?>, RoostCapturable>` + `RoostCapturableProvider`）让任意实体注册自己的栖架；食物来源走 `CIFDataMaps.CHICKEN_FOOD_ITEMS/CHICKEN_FOOD_FLUIDS`（同名 `create_integrated_farming:chicken_food`，分别注册在 ITEM/FLUID 两个 registry，`synced(CODEC, true)`）。
4. **产出预览同步** `common/ranching/roost/display`：`RoostingLootTableParser`(340 行) 静态解析战利品表 → `OutputDisplay` + `LootDisplayStatus{EXACT, COMPLEX}` + `IntRange`；`RoostingDisplaySnapshotBuilder` 汇总成 `RoostingDisplayRecipe`(record，带 CODEC/STREAM_CODEC)；`RoostingDisplaySync` 监听 `OnDatapackSyncEvent`，按 `revision` 缓存快照并只重建一次，广播 `RoostingDisplayPayload` 给客户端 `RoostingDisplayClientCache`（供 JEI `RoostingCategory` 与护目镜显示）。
5. **可插拔作物 API** `api/harvester`：`CustomHarvestBehaviour`（`@FunctionalInterface` + `SimpleRegistry<Block, CustomHarvestBehaviour> REGISTRY`）、`AreaHarvestContext`、`StandardAreaHarvests`；用 Guava `LoadingCache<Dynamic<Tag>, ItemEnchantments>`（上限 64）缓存掉落物附魔解析。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`common/network/CIFPackets.java` 用 NeoForge `RegisterPayloadHandlersEvent`（`PROTOCOL_VERSION="1"`，仅 `playToClient`）；`RoostingDisplayPayload implements CustomPacketPayload` 手写 `StreamCodec.ofMember(encode, decode)`，客户端只做缓存写入。
- 数据驱动：NeoForge `DataMapType`（chicken_food）、`RoostingDisplayRecipe` 数据配方、`FishingNetCatchProviders` 运行时注册表、Create `SimpleRegistry` 若干。
- 配置：`config/CIFConfig` + `CIFServerConfig extends ConfigBase`（Create 配置体系），分组 `farming/fishing/ranching` + `StressConfig`，键如 `vacuumHarvesterRange=10`、`fishingNetCooldownMultiplier=8`、`roostingInventorySlotCount=9`。
- datagen：`data/CIFData.java` 用 Registrate `ProviderType.LOOT/LANG`（`CIFLootTables::generate`、`registerBuiltinLocalization("tooltips")`、`registerPonderLocalization`、`registerForeignLocalization`）+ `CIFRecipeProvider`，产物落 `src/generated`。

## 6. Mixin
- 主配置 `src/main/resources/create_integrated_farming.mixins.json`（`priority=1000`、`compatibilityLevel=JAVA_21`、无 plugin），6 个类全部针对 Create：`HarvesterMovementBehaviourMixin`（`@Inject(method="visitNewPosition", at=@At(INVOKE, target=HarvesterMovementBehaviour;isValidCrop...), cancellable=true)`）、`TreeCutterMixin`（`@ModifyReturnValue isVerticalPlant @TAIL`）、`SawBlockEntityMixin`（`@ModifyReturnValue isSawable`）、`SeatBlockMixin`（`@ModifyExpressionValue canBePickedUp`）、`BlockBreakingMovementBehaviourMixin`、`SawMovementBehaviourMixin`。
- 集成 mixin config 4 个：`create_integrated_farming.{sable,tide,delightoflight,createenchantablemachinery}.mixins.json`，其中 sable 配置带 `"plugin": "...mixin.UniversalConditionalMixinPlugin"`（`extends RestrictiveMixinConfigPlugin`，来自 conditional-mixin）。

## 7. 值得学的 5 条
1. "第三方判定 = 注册表 + mixin 兜底"：`CustomHarvestBehaviour.REGISTRY`(Create `SimpleRegistry<Block, …>`) 提供扩展点，mixin 只在 Create 的 `isValidCrop` 处插桩（`api/harvester/CustomHarvestBehaviour.java:52`、`mixin/create/HarvesterMovementBehaviourMixin.java:34`）。
2. 静态解析战利品表并在 UI 里诚实标注不确定性：`LootDisplayStatus.EXACT/COMPLEX` + `IntRange`，并在 lang 里说明"全局 loot modifier 可能改变实际产出"（`display/RoostingLootTableParser.java`、`CIFCommon` 内 `roosting.loot_modifier_note`）。
3. 数据同步只构建一次：`RoostingDisplaySync` 用 `cachedServer/cachedSnapshot/revision`，仅整包重载时才重建快照，然后按玩家广播（`display/RoostingDisplaySync.java:34`）。
4. 介质化可插拔产出：`FishingNetCatchProviders` 以 `EnumMap<FishingNetMedium, LinkedHashMap<ResourceLocation, Provider>>` 组织，原版钓鱼表零硬编码接入（`FishingNetCatchProviders.java:20`）。
5. 同一 DataMap 名跨两个 registry（item/fluid）统一"喂食"抽象 + `synced(x, true)` 让客户端也知道（`common/registry/CIFDataMaps.java:37`）；同时只用 `ItemHandlerWrapper` 覆写 `insertItem` 返回原 stack 做"只产出"容器、`getItemHandler(side)` 屏蔽底面（`VacuumHarvesterBlockEntity.java:67`）。

## 8. 对外 API
- `plus.dragons.createintegratedfarming.api.harvester`：`CustomHarvestBehaviour`、`AreaHarvestContext`（作物自定义收割判定）、`api/saw/SawableBlockTags`（可锯方块 tag）。
- 运行时注册点：`RoostCapturable.REGISTRY`/`RoostCapturableProvider.REGISTRY`（实体→栖架）、`FishingNetCatchProviders.register(id, medium, provider)`（渔网产出）、`RoostingDisplayProfiles`（产出预览）。
- 数据包侧：`create_integrated_farming:chicken_food` DataMap（item/fluid）、`RoostingDisplayRecipe` 配方 JSON。
- 生态依赖：`CDPRegistrate` 与 CDP 生态（mixin plugin 由 CDP 内嵌的 conditional-mixin 支撑）。
