# 源码分析报告：hlysine/create_connected（Create: Connected）

## 1. 基本信息

- Mod 名：Create: Connected；mod_id：`create_connected`；作者：Lysine；版本 `1.3.3-mc1.21.1`
- 目标：Minecraft 1.21.1 / **仅 NeoForge**（`neoforge_version=21.1.228`，`loader_version_range=[4,)`）
- Gradle：`net.neoforged.moddev 2.0.141`（ModDevGradle）+ `me.modmuss50.mod-publish-plugin 2.2.0`；Gradle 8.10.1；Java 21；Parchment `2024.11.17`；含 `accessTransformers`（`src/main/resources/META-INF/accesstransformer.cfg`，5 条）
- 许可证：**GNU AGPL-3.0**
- 关键依赖：Create `6.0.10-280`、Ponder `1.0.82`、Flywheel `1.0.6`、Registrate `MC1.21-1.3.0+67`、MixinExtras `0.4.1`、JEI `19.21.0.247`；兼容/编译期依赖 **Copycats+**（`com.copycatsplus:copycats:3.0.4+mc.1.21.1-neoforge`）、Create: Dragons Plus、Additional Placements、Dye Depot、Sable / Simulated / Create: Aeronautics（并用 `jarJar` 内嵌 `sable-companion`）；Conditional Mixin 仓库来源（maven.fallenbreath.me）
- 发布：Modrinth `Vg5TIO6d`、CurseForge `947914`、GitHub Release

## 2. 源码规模与包结构

- `.java` 文件 **315** 个，总行数 **29 562**（实测）
- 最大文件：`registries/CCBlocks.java` 1197、`datagen/recipes/CCStandardRecipes.java` 941、`content/fluidvessel/FluidVesselBlockEntity.java` 624、`content/fluidvessel/BoilerData.java` 499、`registries/CCSoundEvents.java` 445、`ponder/KineticBatteryScene.java` 440、`content/kineticbattery/KineticBatteryBlockEntity.java` 410、`content/inventorybridge/InventoryBridgeBlockEntity.java` 400
- 主要包（第 3 层）：`content/<feature>/*`（约 40 个功能包：sequencedpulsegenerator(+instructions 15)、linkedtransmitter、kineticbattery、fluidvessel、itemsilo、kineticbridge、copycat/* 等）、`registries`（26 个 `CC*` 注册类）、`mixin/*`（约 50 个，按功能分子包）、`config`（9，与 Copycats+ 同源）、`datagen/{recipes(10),advancements(7)}`、`ponder`（13 个场景）、`compat`(8)

## 3. 入口与注册

主类 `src/main/java/com/hlysine/create_connected/CreateConnected.java:33`。

```java
@Mod(CreateConnected.MODID)
public class CreateConnected {
    private static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MODID); // :40
    public CreateConnected(IEventBus eventBus, ModContainer modContainer) {
        modEventBus = eventBus;
        REGISTRATE.registerEventListeners(modEventBus);
        REGISTRATE.setCreativeTab(CCCreativeTabs.MAIN);            // :57
        CCBlocks.register(); CCItems.register(); CCBlockEntityTypes.register();
        CCCreativeTabs.register(modEventBus); CCPackets.register();  // :63-64
        CCConfigs.register(modContainer);
```

- 全部内容注册走 **Registrate**（`CCBlocks.java` 1197 行，链上大量 `.transform(FeatureToggle.register(FeatureCategory.KINETIC))`，见 `CCBlocks.java:148`）与 26 个 `registries/CC*.java` 静态注册类
- Create 的扩展点集中在 `FMLCommonSetupEvent#enqueueWork`（`:80-90`）：`CCInteractionBehaviours / CCMovementBehaviours / CCMountedStorageTypes / CCDisplaySources / CCDisplayTargets / CCUnpackingHandlers / CCInventoryIdentifiers`
- `RegisterEvent` 分派（`:92-99`）：按 `event.getRegistry()` 判断注册 `CCItemAttributes`（`CreateBuiltInRegistries.ITEM_ATTRIBUTE_TYPE`）与 `CCAdvancements/CCTriggers`

## 4. 核心系统

1. **功能开关体系**（`config/FeatureToggle.java`，用于"可选内容"）：四个静态表 `TOGGLEABLE_FEATURES / DEPENDENT_FEATURES / FEATURE_CATEGORIES / FEATURE_CONDITIONS`；提供 Registrate 变换 `register(FeatureCategory...)`、`registerDependent(dependency, ...)`、以及 `addCondition(key, Supplier<Boolean>)`（`:36-60`），配置项由 `config/CFeatures.java:24` 按 `TOGGLEABLE_FEATURES` 批量 `builder.define(r.getPath(), true)`；`refreshItemVisibility()` + `mixin/featuretoggle/CreativeModeTabsAccessor` 控制开关关闭时物品不进创造标签页。
2. **多方块蒸汽容器**（`content/fluidvessel/`）：`FluidVesselBlockEntity extends FluidTankBlockEntity implements IHaveGoggleInformation, IMultiBlockEntityContainer.Fluid`（`:40`），内部聚合 Create 的 `BoilerData`（`:49`，本仓库又扩写了 499 行）与 `updateBoilerState()/removeController()/setWindows()/toggleWindows()`（`:180-340`）；配合 `mixin/fluidvessel/{BlazeBurnerBlockEntity,FluidTankBlockEntity,SteamEngineBlockEntity,SteamEngineBlock,WhistleBlock}Mixin` 把自定义储罐接入 Create 锅炉/蒸汽机体系。
3. **动能电池**（`content/kineticbattery/`）：`KineticBatteryBlockEntity extends GeneratingKineticBlockEntity implements ISplitShaftBlockEntity, ThresholdSwitchObservable`（`:38`），字段 `consumedStress / applyMinStress / batteryLevel`；`updateConsumedStress()`（`:142`）遍历 `network.sources` 用 `KineticNetworkAccessor.getUnloadedStress()` 反推可储能，`updateMinStress()`（`:171`）按 `network.members` 决定最低转速；配套 `KineticBatteryGenerator/KineticBatteryOverrides/KineticBatteryDisplaySource`。
4. **可编程脉冲发生器**（`content/sequencedpulsegenerator/instructions/`）：`Instruction.java:19` 用 `static Map<String, Instruction> INSTRUCTION_MAP` + `register(Instruction)` 建指令注册表，每条指令带 `instructionId / CCGuiTextures background / ParameterConfig / hasSignal / terminal`；15 个子类（`LoopForInstruction`、`WaitForExactInstruction`、`LoopIfMaxInstruction`…）。这是"自建行为注册表"的干净范例。
5. **Copycats 兼容层**（`compat/CopycatsManager.java`）：`BLOCK_MAP/ITEM_MAP` 把本 mod 旧方块 id 映射到 Copycats+ 的 `BlockEntry/ItemEntry`（如 `com.copycatsplus.copycats.CCBlocks.COPYCAT_SLAB`），`convert(Block/Item)` 在注册名冲突时替换实现；`migrationQueue = Collections.synchronizedMap(new WeakHashMap<Level, Set<BlockPos>>())`（`:24`）配合 `NeoForge.EVENT_BUS.addListener(CopycatsManager::onLevelTick)` 分批迁移存档。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`registries/CCPackets.java`，枚举 + Catnip `CatnipPacketRegistry(CreateConnected.MODID, 1)`、`CustomPacketPayload.Type`、`StreamCodec`；两个包 `CONFIGURE_SEQUENCER(ConfigureSequencedPulseGeneratorPacket)`、`PLAY_CONTRAPTION_JUKEBOX(PlayContraptionJukeboxPacket)`。
- 配置：`config/CCConfigs + CCommon/CServer/CFeatures/CStress + SyncConfigBase`（与 Copycats+ 同源，服务端→客户端 NBT 同步）。
- 数据驱动：`CCTags`、`datagen/CCDataMapGen`（NeoForge DataMap）、`FeatureEnabledCondition / FeatureEnabledInCopycatsCondition`（实现配方的 `ICondition`，功能开关关闭时配方自动失效）；Ponder 场景插件 `registries/CCPonderPlugin.java`（`PonderPlugin#registerScenes/registerTags`）。
- datagen：`datagen/CCDatagen.java:26` `gatherDataHighPriority`（HIGHEST 优先级，加 Registrate 数据）+ `gatherData`（`:31` LOWEST，`event.includeServer()` 分支注册 `CCAdvancements / CCStandardRecipes / SequencedAssemblyGen / CCJukeboxSongs / CCSoundEvents.provider`）；`CreateConnectedProcessingRecipeGen` 继承 Create 的处理配方生成器；`build.gradle` 的 data run 带 `--existing-mod create/simulated/dye_depot`；语言文件走 `ConnectedLang` + `src/generated/resources`。

## 6. Mixin

- 配置：`src/main/resources/create_connected.mixins.json`（`package com.hlysine.create_connected.mixin`、`refmap create_connected.refmap.json`、`plugin com.hlysine.create_connected.mixin.MixinPlugin`、`overwrites` 未启用；共约 50 个 mixin）
- 插件 `mixin/MixinPlugin.java:34`：与 Copycats+ 同款机制——自定义 `@ModMixin(mods=..., applyIfPresent=...)`（`compat/ModMixin.java`）+ `FMLLoader.getLoadingModList()` 判定，用于 `compat.CopycatBlockMixin/CopycatBlockEntityMixin` 等条件兼容
- 代表性目标：`nestedschematics.{FilesHelper,ServerSchematicLoader,ClientSchematicLoader,SchematicExport}Mixin`（允许子目录原理图）、`sequencedgearshift.{SequencedGearshiftBlockEntity,Instruction,SequencerInstructions}Mixin` + `InstructionAccessor/AbstractSimiScreenAccessor`、`itemsilo.{Contraption,MountedStorageManager}Mixin`、`inventoryaccess.{PackagerBlock,PackagerBlockEntity}Mixin`、`redstonelinkwildcard.RedstoneLinkNetworkHandlerMixin`、`kineticbattery.KineticNetworkAccessor`（读 Create 私有网络字段）、`linkedtransmitter.{AnalogLeverBlock,ThrottleLeverBlock}Mixin`、client 侧 `sequencedgearshift.SequencedGearshiftScreenMixin`、`featuretoggle.SubMenuConfigScreenMixin`

## 7. 值得学的 5 条具体做法

1. **用 Registrate 变换实现"功能开关"**：`config/FeatureToggle.java:52` 的 `register(FeatureCategory...)` 返回 `NonNullUnaryOperator<S>`，一行 `.transform(...)` 同时接好配置项、创造标签页可见性与依赖关系。适用于任何"可选内容包"式 mod。
2. **枚举跨版本兼容读取**：`registries/CCSequencerInstructions.java` 不直接引用 Create 枚举常量，而是 `for (SequencerInstructions value : values()) if (value.name().equals("TURN_AWAIT")) ...`；上游改名/改序时只退化为不可用而非崩溃。
3. **Create 扩展点集中注册**：`CreateConnected.java:80-90` 把 `MovingInteractionBehaviour.REGISTRY.register(Blocks.NOTE_BLOCK, ...)`（`CCInteractionBehaviours.java`）、`REGISTRATE.displaySource("boiler_status", BoilerDisplaySource::new)`（`CCDisplaySources.java:19`）等统一放在 `enqueueWork` 里，并给出 Registrate 风格包装函数。
4. **配方随功能开关联动**：`datagen/recipes/FeatureEnabledCondition` + `FeatureEnabledInCopycatsCondition` 实现 `ICondition`，关闭功能时不生成/不加载配方。
5. **迁移队列避免卡顿**：`compat/CopycatsManager.java:24` 用 `WeakHashMap<Level, Set<BlockPos>>` 收集待迁移位置，在 `LevelTickEvent` 里持续处理（`convert()` 按 id 换方块），而不是一次性遍历区块。
6. （补充）**冲突让位**：`CCInteractionBehaviours.register()` 里 `if (!Mods.STEAM_N_RAILS.isLoaded())` 才注册合成台/切石机等交互行为，主动让第三方优先。

## 8. 对外接口（非库 mod，供依赖参考）

- `build.gradle` 已应用 `maven-publish`，但未见 `publishing {}` 目标仓库配置 → 是否发布可依赖坐标**未确认**。
- CHANGELOG 明确提示依赖者：1.2.0 起**注册类迁移到 `registries` 包**（`com.hlysine.create_connected.registries.*`），这是它对下游的实际"API 面"；`content/*` 的 Block/BlockEntity 类亦为公开。
- 兼容接入点：`compat/Mods.java` 枚举（`CopycatsManager`、`AdditionalPlacementsCompat`、`SimCompatRegistry`）演示了"软依赖 + 静态注册表替换"的接入方式；外部 mod 若要与本 mod 互操作，主要走方块 id 映射与 Create 官方注册表（DisplaySource/MovementBehaviour 等）。
