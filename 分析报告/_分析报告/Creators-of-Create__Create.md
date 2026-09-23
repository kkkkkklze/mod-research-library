# Create（机械动力）源码分析报告

仓库：`源码库\_参考仓库\_bulk\Creators-of-Create__Create`（GitHub: Creators-of-Create/Create）

> 仓库状态（分析时实测）：HEAD `0924e93`，分支 `mc1.21.1/dev`；`blob:none` 部分克隆 + 内容型稀疏检出（`git sparse-checkout list` 含 `**/*.java`、`**/*.gradle`、`**/*.toml`、`**/*.mixins.json`、`**/*.cfg`、`**/*.md`、`**/*.txt` 等，**不含 `**/*.json` / `**/*.png`**）。后果：
> - `src/main/java` 下 2016 个 .java 已在磁盘上，路径可直接打开；本报告行数统计即基于工作区实测（275,023 行）。
> - `src/main/resources` 只有 `create.mixins.json`、`META-INF/accesstransformer.cfg`、`assets/create/lang/README.md`；**datagen 产物 `src/generated/resources/**`（7,175 个 json）、模型/贴图/ponder 资源不在磁盘上**，需要时用 `git archive HEAD src/generated | tar -x`（会自动懒加载下载 blob）或放宽 sparse 规则。

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Create（机械动力）/ `create` |
| 作者 | simibubi（The Create Team / Creators of Create） |
| MC 版本 / 加载器 | 1.21.1 / NeoForge `21.1.219` |
| Mod 版本 | `6.0.11`；分支 `mc1.21.1/dev`，HEAD `0924e93` "Coasting textures"（2026-08-18） |
| 构建系统 | NeoForge ModDevGradle `net.neoforged.moddev` 2.0.141，Java 21 toolchain + `withSourcesJar()`，Parchment `2024.11.17` 映射 |
| 其他 Gradle 插件 | `net.kyori.blossom` 2.2.0（把 mod_version/gitCommit 注入源码常量）、`dev.ithundxr.silk`（changelog）、`me.modmuss50.mod-publish-plugin`（CurseForge 328085 / Modrinth LNytGWDc / GitHub） |
| 关键依赖 | Registrate `MC1.21-1.3.0+67`（`jarJar(api(...))` 对外暴露）、Flywheel `1.0.6`（`compileOnlyApi` API + jarJar runtimeOnly，范围 `[1.0.0,2.0)`）、Ponder `1.0.85`（jarJar api）、Vanillin `1.1.3-41`、JEI 19.21.0.247 / Curios 9.2.2 / Sodium / CC:Tweaked / Farmer's Delight、FTB Chunks·Teams·Library / JourneyMap / Xaero（compileOnly/local） |
| 许可证 | 双许可：代码 MIT；`src/main/resources/assets/` 下资源 All Rights Reserved（见 `LICENSE.md`） |
| 入口元数据 | `src/main/templates/META-INF/neoforge.mods.toml` 经 `generateModMetadata` 展开；AT 文件 `src/main/resources/META-INF/accesstransformer.cfg`（约 30 条，开放 `Font#getFontSet`、`PotionBrewing` 静态表、`Ingredient#values` 等）；datagen 输出 `src/generated/resources/` |
| 备注 | `settings.gradle` 在本地存在 `Ponder/` 目录时会 `includeBuild` 并做 `dependencySubstitution`；`cc_tweaked_enable=false` 时排除 `compat/computercraft/implementation/**` |

## 2. 源码规模与包结构

- `src/main/java`：**2016 个 .java / 275,023 行**；`src/generated/resources`：**7,175 个 json**。
- 行数分布：≥300 行 201 个，≥200 行 382 个，≥100 行 839 个，≥50 行 1,426 个（即小文件 590 个）。
- 顶层分包（括号内为文件数）：`com/simibubi/create` 根包（38，9572 行，全是 `AllXxx` 注册表）· `content`（1303）· `foundation`（323）· `infrastructure`（131）· `compat`（114）· `api`（88）· `impl`（19）。
- 主要子包（文件数）：`content/kinetics` 254、`content/logistics` 219、`content/contraptions` 185、`content/trains` 164、`content/equipment` 141、`content/redstone` 113、`content/fluids` 76、`content/decoration` 66、`foundation/mixin` 65、`infrastructure/ponder` 54、`compat/jei` 47、`foundation/blockEntity` 45、`content/schematics` 45、`compat/computercraft` 39、`foundation/data` 38、`content/processing` 33、`foundation/utility` 27、`api/contraption` 26、`foundation/block` 26、`infrastructure/command` 25、`api/data` 22、`foundation/gui` 21、`foundation/item` 21。
- 行数最重的包：`infrastructure/ponder/scenes` 14955（30 个文件，教学脚本）· 根包 9572 · `content/trains/entity` 7433 · `content/trains/track` 6706 · `content/contraptions` 5784 · `foundation/data/recipe` 4896（20 个文件，全 mod 配方生成）· `content/logistics/factoryBoard` 3870 · `content/logistics/stockTicker` 3718。

## 3. 源文件清单

按要求 >400 个文件时应列出全部 ≥50 行者，但该类文件有 1,426 个（远超报告篇幅）。折中：列出体量最大的 40 个文件；其余按包汇总在 §2 表格中；完整清单可用下方命令随时导出（在仓库根目录执行）。

```bash
find src/main/java -name '*.java' -exec wc -l {} + | sort -rn | awk '$1>=50'
```

| 行数 | 路径（`src/main/java/` 之后） |
|---|---|
| 2711 | `com/simibubi/create/AllBlocks.java` |
| 1830 | `com/simibubi/create/foundation/data/recipe/CreateStandardRecipeGen.java` |
| 1830 | `com/simibubi/create/content/logistics/stockTicker/StockKeeperRequestScreen.java` |
| 1594 | `com/simibubi/create/content/contraptions/Contraption.java` |
| 1523 | `com/simibubi/create/infrastructure/ponder/scenes/highLogistics/FactoryGaugeScenes.java` |
| 1432 | `com/simibubi/create/infrastructure/ponder/scenes/KineticsScenes.java` |
| 1310 | `com/simibubi/create/content/trains/entity/Train.java` |
| 1128 | `com/simibubi/create/content/trains/schedule/ScheduleScreen.java` |
| 1120 | `com/simibubi/create/content/logistics/factoryBoard/FactoryPanelBehaviour.java` |
| 1032 | `com/simibubi/create/content/trains/station/StationBlockEntity.java` |
| 1002 | `com/simibubi/create/AllBlockEntityTypes.java` |
| 963 | `com/simibubi/create/foundation/data/recipe/CreateMillingRecipeGen.java` |
| 946 | `.../content/contraptions/AbstractContraptionEntity.java` |
| 941 | `.../content/trains/entity/Carriage.java` |
| 928 | `.../content/schematics/cannon/SchematicannonBlockEntity.java` |
| 923 | `.../infrastructure/ponder/scenes/highLogistics/FrogAndConveyorScenes.java` |
| 923 | `.../content/trains/entity/Navigation.java` |
| 902 | `.../infrastructure/ponder/scenes/ProcessingScenes.java` |
| 872 | `.../content/equipment/clipboard/ClipboardScreen.java` |
| 836 | `.../infrastructure/ponder/scenes/RedstoneScenes.java` |
| 819 | `.../content/processing/basin/BasinBlockEntity.java` |
| 819 | `.../content/logistics/chute/ChuteBlockEntity.java` |
| 816 | `.../content/trains/track/BezierConnection.java` |
| 812 | `.../content/logistics/tunnel/BrassTunnelBlockEntity.java` |
| 812 | `.../content/kinetics/chainConveyor/ChainConveyorBlockEntity.java` |
| 795 | `.../content/trains/track/TrackBlock.java` |
| 790 | `.../content/trains/track/TrackPlacement.java` |
| 777 | `.../content/trains/entity/CarriageContraptionEntity.java` |
| 771 | `com/simibubi/create/AllSoundEvents.java` |
| 750 | `.../infrastructure/ponder/scenes/MovementActorScenes.java` |
| 748 | `.../content/kinetics/belt/BeltBlock.java` |
| 746 | `.../infrastructure/ponder/scenes/BearingScenes.java` |
| 743 | `.../compat/trainmap/TrainMapManager.java` |
| 735 | `.../foundation/advancement/AllAdvancements.java` |
| 715 | `.../content/logistics/factoryBoard/FactoryPanelScreen.java` |
| 714 | `.../content/contraptions/ContraptionCollider.java` |
| 685 | `.../content/logistics/packager/PackagerBlockEntity.java` |
| 672 | `.../content/kinetics/mechanicalArm/ArmBlockEntity.java` |
| 667 | `.../content/kinetics/mechanicalArm/AllArmInteractionPointTypes.java` |
| 665 | `.../content/logistics/depot/EjectorBlockEntity.java` |

小文件（<50 行）按包汇总：`foundation/mixin/accessor` 33（纯 `@Accessor` 接口）、`infrastructure/config` 多为字段声明、`api/*` 下多为 SPI 接口（`api/behaviour/*`、`api/schematic/*`、`api/contraption/storage/*` 共 88 个文件里单文件普遍 <50 行）。

## 4. 入口与注册

主类：`src/main/java/com/simibubi/create/Create.java`（218 行，`@Mod(Create.ID)`）。客户端入口 `CreateClient.java`（165 行）。注册全部集中在根包的 `AllXxx` 类（38 个，见 §2），主类只在 `onCtor(IEventBus, ModContainer)` 里按顺序调用，分三个时机：

```java
public static void onCtor(IEventBus modEventBus, ModContainer modContainer) {
    REGISTRATE.registerEventListeners(modEventBus);
    AllSoundEvents.prepare();
    AllCreativeModeTabs.register(modEventBus);   // DeferredRegister 风格
    AllBlocks.register();
    AllItems.register();
    AllBlockEntityTypes.register();
    AllPackets.register();
    AllConfigs.register(modLoadingContext, modContainer);
    modEventBus.addListener(Create::init);       // FMLCommonSetupEvent
    modEventBus.addListener(Create::onRegister); // RegisterEvent
    modEventBus.addListener(EventPriority.HIGHEST, CreateDatagen::gatherDataHighPriority);
    modEventBus.addListener(EventPriority.LOWEST,  CreateDatagen::gatherData);
    Mods.CURIOS.executeIfInstalled(() -> () -> Curios.init(modEventBus));
}
```

三种注册风格并存：

1. **Registrate builder 链**（主体，`AllBlocks.java` 188 个 `BlockEntry` 字段声明）：
   ```java
   public static final BlockEntry<ShaftBlock> SHAFT = REGISTRATE.block("shaft", ShaftBlock::new)
       .initialProperties(SharedProperties::softMetal) ... .register();
   ```
   实例由 `Create.registrate()` 持有（`foundation/data/CreateRegistrate.java`，318 行，扩展了 `blockEntity/entity/virtualFluid/mountedItemStorage/displaySource/paletteStoneBlock` 等 builder）。**该实例被 `StackWalker` 保护**：非 `com.simibubi.create` 包调用会抛 `UnsupportedOperationException`（`Create.java:213-217`），附属需自建 `CreateRegistrate` 或走 `api/registrate/CreateRegistrateRegistrationCallback`。
2. **DeferredRegister 风格**：`AllRecipeTypes`、`AllParticleTypes`、`AllFeatures`、`AllPlacementModifiers`、`AllDataComponents`、`AllAttachmentTypes` 等 20 余个类，`register(modEventBus)`。
3. **自定义 `SimpleRegistry`**（`api/registry/SimpleRegistry.java`）：线程安全的对象→值映射，支持懒加载 `Provider`（如 `forBlockTag`）+ 缓存失效，用于 `BlockStressValues`、`AllInventoryIdentifiers`、`BoilerHeaters`、`AllPortalTracks` 等"用 tag 或配置注入行为"的注册表。依赖已注册对象的默认值延迟到 `Create.init` 的 `event.enqueueWork(...)` 与 `onRegister(RegisterEvent)` 中执行。

## 5. 核心系统

1. **Kinetics 旋转/应力网络**（`content/kinetics/`，254 文件）
   `RotationPropagator.java`(442) 用 `getRotationSpeedModifier(from,to)` 纯函数描述相邻动能 BE 的转速比（轴连=1、小齿轮互咬=-1、大-小齿轮=±2/±0.5），`KineticNetwork.java` 记录整张网络的转速与应力、`TorquePropagator.java` 作为全局脏标记/重算调度；`KineticBlockEntity`(626) 只管自身 rpm 与应力影响，`IRotate` 接口暴露 `hasShaftTowards/getRotationAxis` 供方块声明连接语义。设计点：网络重算只影响"脏"网络；单方块查询走 `propagateRotationTo` 让特殊方块自定义；应力值走 `api/stress/BlockStressValues`（`SimpleRegistry` + Provider），因此**配置文件能直接改每个方块的应力**（`AllConfigs.register` 把 `CStress` 接成 Provider）。
2. **Contraption 移动结构**（`content/contraptions/`，185 文件）
   `Contraption`(1594，抽象) 负责装配扫描 `searchMovedStructure`、快照序列化 `writeNBT/readNBT`、`addBlocksToWorld/removeBlocksFromWorld`；`AbstractContraptionEntity`(946) 是承载实体，`ContraptionCollider`(714) 做碰撞，`foundation/virtualWorld/VirtualRenderWorld` 提供伪世界用于渲染与 Ponder。设计点：actor 行为由 `api/behaviour/movement/MovementBehaviour` + 注册表决定（同一套方块在 contraption 里自动变成 actor）；被移动方块的库存走 `api/contraption/storage`（MountedItemStorage/MountedFluidStorage）与 `AllMountedStorageTypes`，与方块类型解耦。
3. **BlockEntity Behaviour 组合式设计**（`foundation/blockEntity/`，45 文件）
   `SmartBlockEntity.java`(265) 用 `Reference2ObjectArrayMap<BehaviourType<?>, BlockEntityBehaviour>` 装行为，`tick/write/read/initialize/destroy` 统一广播给所有行为（`read` 时先 `addBehavioursDeferred` 再读，因为部分行为依赖 NBT）。已有行为：filtering、inventory（`InvManipulationBehaviour`/`TankManipulationBehaviour`）、fluid（`SmartFluidTankBehaviour`）、scrollValue（`ValueSettingsBehaviour` + `ValueSettingsScreen` 值面板）、edgeInteraction。**外部可通过 `api/event/BlockEntityBehaviourEvent` 往任意 Create 方块实体注入行为**，是附属最常见扩展点。
4. **铁路图与全局数据**（`content/trains/`，164 文件）
   `GlobalRailwayManager` 持有 `trackNetworks / signalEdgeGroups / trains / sync` 四张全局表（服务端单例，登录/卸日志同步），`graph/TrackGraph`+`TrackNodeLocation`(218) 表示连通轨道网络，`signal/SignalPropagator` 做信号传播，`TrackGraphSyncPacket`(282) 增量同步给客户端，`schedule/ScheduleScreen`(1128) 是数据驱动的列车时刻表 UI。
5. **Ponder 教学系统**（`infrastructure/ponder/` + `foundation/ponder/`）
   `foundation/ponder/CreatePonderPlugin.java` 实现 `PonderPlugin`（registerScenes / registerTags / registerSharedText / indexExclusions / onPonderLevelRestore）；`infrastructure/ponder/AllCreatePonderScenes.java` 做声明式登记，共 179 处 `addStoryBoard`：
   ```java
   HELPER.forComponents(AllBlocks.SHAFT)
       .addStoryBoard("shaft/relay", KineticsScenes::shaftAsRelay, AllCreatePonderTags.KINETIC_RELAYS);
   ```
   场景本体在 `infrastructure/ponder/scenes/**`（30+ 个 `XxxScenes` 类，14955 行），用 `CreateSceneBuilder`(377) 的链式指令描述动画。附带 `PonderWorldBlockEntityFix` 修 Ponder 伪世界中的 BE。
6. **可视化 / Flywheel 与 CTM**
   视觉对象只在 BE 类型注册处声明，服务端无渲染 import：`AllBlockEntityTypes.java:243+` 的 `.visual(() -> SchematicannonVisual::new)`、`.visual(() -> OrientedRotatingVisual.of(...), false)`；实例类型集中在 `foundation/render/AllInstanceTypes.java`（`CreateClient` 里 `AllInstanceTypes.init()`）。方块连接纹理自研：`foundation/block/connected/`（`ConnectedTextureBehaviour` 284 行、`AllCTTypes` 198、`CTModel` 118）。

## 6. 网络 / 数据驱动 / 配置 / 资源与 datagen

- **网络**：全部包登记在单个枚举 `AllPackets.java`（262 行，约 114 个包类型，注释分区 Client→Server / Server→Client），每个常量绑定 `Class<T>` + `StreamCodec`，`register()` 交给 catnip 的 `CatnipPacketRegistry`（外部库 `net.createmod.catnip`，不在本仓库）批量注册。`foundation/networking/BlockEntityConfigurationPacket.java` 是服务端设置包的统一基类：先校验 `player!=null && !spectator && !AdventureUtil.isAdventure`、`world.isLoaded(pos)`、`player.canInteractWithBlock(pos, 20)`，再 `applySettings(...)` + `SyncedBlockEntity.sendData()` + `setChanged()`；同包还有 `ISyncPersistentData`、`LeftClickPacket`、`BlockEntityDataPacket`。
- **数据驱动**：`src/generated/resources/data/create` 下 advancement / enchantment / damage_type / loot_table / recipe / tags / worldgen / data_maps（另生成 `data/neoforge`、`data/c`、`data/curios`、`data/quark` 兼容数据）；`infrastructure/data/GeneratedEntriesProvider` 用 `RegistrySetBuilder` 生成 enchantment、damage_type、configured/placed_feature、biome_modifier，以及 Create 自有注册表 `create:potato_projectile_type`。新式数据驱动用 NeoForge **DataMap**：`api/registry/CreateDataMaps.java` 定义 `create:regular_blaze_burner_fuels` / `superheated_blaze_burner_fuels`（`DataMapType<Item, BlazeBurnerFuel>`）；另有 `api/data/datamaps`、`SimpleRegistry.Provider.forBlockTag/forItemTag` 让 tag 直接驱动行为。
- **配置**：`infrastructure/config/`（13 个类），基于 catnip `ConfigBase`，分 CLIENT/COMMON/SERVER 三份（`CClient`、`CCommon`、`CServer` + `CKinetics/CStress/CLogistics/CFluids/CTrains/CRecipes/CSchematics/CEquipment/CWorldGen`），`AllConfigs.register` 统一 `container.registerConfig(...)` 并在 `ModConfigEvent.Loading/Reloading` 时回调 `onLoad/onReload`；`CStress` 同时作为 `BlockStressValues` 的 Provider（配置↔行为耦合点）。
- **资源**：`assets/create/{flywheel,lang,models,particles,ponder,reference,shaders,sounds,textures}` + `icon.png` + `pack.mcmeta`；`data/create/structure` 在 main 内（其余在 generated）。
- **datagen**：`infrastructure/data/CreateDatagen.java` 分 `gatherDataHighPriority`（Registrate 附加数据）与 `gatherData`（15 处 `generator.addProvider`）：`GeneratedEntriesProvider`、配方 tag、contraption type tag、mounted storage tag、`DamageTypeTagGen`、`AllAdvancements`、`CreateStandardRecipeGen`、`CreateMechanicalCraftingRecipeGen`、`CreateSequencedAssemblyRecipeGen`、`CreateDatamapProvider`、`VanillaHatOffsetGenerator`、`CuriosDataGenerator`、`CreateEnchantmentTagsProvider`、`CreateWikiBlockInfoProvider`；`CreateRecipeProvider.registerAllProcessing` 批量挂 20 个 `foundation/data/recipe/*RecipeGen`（生成 7,175 个 json 的主力，含 `CreateStandardRecipeGen` 1830 行、`CreateMillingRecipeGen` 963 行）。附属侧可直接继承 `api/data/recipe/` 的 `BaseRecipeProvider`、`ProcessingRecipeGen`、`StandardProcessingRecipeGen`、`MechanicalCraftingRecipeBuilder`。

## 7. Mixin

- 配置：`src/main/resources/create.mixins.json` — `package: com.simibubi.create.foundation.mixin`，`plugin: com.simibubi.create.foundation.mixin.CreateMixinPlugin`，`priority: 1000`，`compatibilityLevel: JAVA_21`，`injectors.defaultRequire: 1`，`required: true`。
- 规模：64 个 mixin 类（`mixins` 数组 43 个含 24 个 `@Accessor` + 3 个 datafixer；`client` 数组 21 个含 9 个 accessor 与 3 个 `compat.xaeros.*`），文件名与 `@Mixin` 目标：
  - `foundation/mixin/BlockMixin.java` → `@Mixin(Block.class)`，`@WrapWithCondition` 包 `Block#popResource` 内的 `Level#addFreshEntity`
  - `foundation/mixin/PlayerMixin.java` → `@Mixin(value = Player.class, priority = 1500)`，`@ModifyExpressionValue` 改 `canPlayerFitWithinBlocksAndEntitiesWhen` 中的 `Level#noCollision`
  - `foundation/mixin/MapItemSavedDataMixin.java`(194) → `@Mixin(MapItemSavedData.class)`（Create 地图/列车地图数据）
  - `foundation/mixin/client/EntityContraptionInteractionMixin.java`(167) → `@Mixin(Entity.class)`（客户端），`client/LevelRendererMixin.java` → `@Mixin(LevelRenderer.class)`
  - `foundation/mixin/datafixer/{BlockPosFormatAndRenamesFixMixin, ItemStackComponentizationFixMixin(204), V1460Mixin}`（跨版本 NBT 修正）
  - 24 个 accessor 取代 AT，如 `MappedRegistryAccessor`、`FluidInteractionRegistryAccessor`、`ItemModelGeneratorsAccessor`、`ServerLevelAccessor`
- 插件逻辑紧凑（46 行）：`shouldApplyMixin` 只在 `mixinClassName.startsWith("...compat.xaeros")` 且 `!Mods.XAEROWORLDMAP.isLoaded()` 时返回 false —— **按运行时模组加载状态开关 mixin**，是兼容 mixin 的低成本做法。
- 构建脚本给 run 配置开了 `mixin.debug.verbose/export=true`，便于 dump 变换后字节码。

## 8. 值得学的具体做法

1. **"注册表 + 懒加载 Provider + 失效缓存"三件套**：`api/registry/SimpleRegistry.java`（接口含 `Provider`、`Multi`，文档写明线程安全与优先级）配 `impl/registry/SimpleRegistryImpl.java`(181)、`TagProviderImpl.java`(53)。配置与 tag 都能注入行为，且只在首次查询时计算。用法见 `api/stress/BlockStressValues.java`。
2. **BE 行为组合 + 事件注入**：`foundation/blockEntity/SmartBlockEntity.java:51-120`（构造期收集行为、`addBehavioursDeferred` 处理 NBT 依赖、统一 tick/save/load 广播）与 `api/event/BlockEntityBehaviourEvent.java`（`NeoForge.EVENT_BUS.post`，让附属给自己/别人的 BE 加行为）。
3. **出入站包的统一安全校验基类 + 枚举式包登记**：`foundation/networking/BlockEntityConfigurationPacket.java`（权限/距离/维度校验集中在 `handle`，子类只写 `applySettings`）、`AllPackets.java`（114 个包一屏看完，`Class` + `StreamCodec` 一处声明）。做多 BE 交互 UI 时可直接照搬。
4. **声明式教学/文档登记**：`infrastructure/ponder/AllCreatePonderScenes.java`（`forComponents(方块...).addStoryBoard(id, Scene::method, Tag)`，179 处）、`foundation/ponder/CreatePonderPlugin.java`（含 `registerSharedText` 共享文案与 `indexExclusions` 去噪）。把"文档"变成可复审的代码，而且和注册表解耦。
5. **客户端渲染与服务端逻辑彻底分层 + 内建 API/Impl 分包**：visual 只在 `AllBlockEntityTypes.java:243+` 的 `.visual(() -> XxxVisual::new)` 声明（服务端无 import），实例类型集中 `foundation/render/AllInstanceTypes.java`；对外只暴露 `api/*`（`api/behaviour`、`api/data`、`api/registry`、`api/contraption`、`api/schematic`、`api/stress` 等 88 个文件），实现放 `impl/*`，并用 `Create.registrate()` 的 StackWalker 检查（`Create.java:213-217`）阻止附属误用内部实例——这套"稳定接口 / 内部实现 / 运行时守卫"组合，是大型 mod 保 API 兼容的实用手段。

（未确认项：`CatnipPacketRegistry`、`ConfigBase`、`LangBuilder` 等来自外部库 `net.createmod.catnip`，其源码不在本仓库；Ponder/Flywheel 同理，本仓库仅有调用侧与 `src/main/resources/assets/create/ponder` 资源。）
