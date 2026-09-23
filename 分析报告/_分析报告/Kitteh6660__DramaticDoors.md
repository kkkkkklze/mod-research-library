# Kitteh6660/DramaticDoors 源码分析报告

## 1. 基本信息

- Mod 名：Dramatic Doors；mod_id：`dramaticdoors`；作者：Fizzware / Kitteh6660；版本 `1.21.1-3.3.1`
- 目标：**MC 1.21.1**，双平台（`gradle.properties: enabled_platforms=fabric,neoforge`）
  - NeoForge `21.1.219`（`neoforge.mods.toml` 要求 `minecraft [1.21.1,1.22)`、`neoforge [21.1.0,)`）
  - Fabric：loader `0.16.10`、Fabric API `0.115.4+1.21.1`、ModMenu `11.0.3`
- Gradle（**不用 Architectury**）：根 `build.gradle:1-6` 用 `io.github.pacifistmc.forgix 1.2.9`（把 fabric/neoforge 两个 jar 合并成 `DramaticDoors-NeoQuiFab-*.jar`，并 `additionalRelocate` 把 common 包分别重定位到 `....fabric` / `....neoforge`）、`fabric-loom 1.9`、`org.spongepowered.gradle.vanilla`、`org.spongepowered.mixin 0.7`；Java 21 toolchain；mappings 用 **official**（`mapping_channel=official`, `mapping_version=1.21.1`）
- 许可证：MIT
- 编译依赖（重点）：**Create 6.0.10-280**（`maven.createmod.net`，`create-1.21.1:...:slim` + `transitive = false`，NeoForge 侧 `implementation`）、`ponder-neoforge 1.0.82`、`flywheel-neoforge-api 1.0.6`（compileOnly api + runtimeOnly）、`Registrate MC1.21-1.3.0+67`；Fabric 侧 `curse.maven:macaws-doors`（`neoforge/build.gradle:51-65`、`fabric/build.gradle:29-33`）。common 仅 `compileOnly org.spongepowered:mixin 0.8.6`

## 2. 源码规模与包结构

- `.java` **193 个文件，共 6381 行**（`find -name '*.java' -exec wc -l {} +`）
- 包结构（common 为主）：
  - `compat/registries/` **107 个文件**（每个兼容 mod 一个 `XxxCompat` 类，占总文件数一半以上）
  - `blocks/` 15 个（`TallDoorBlock`、`ShortDoorBlock` + 各种材质/风化/滑动门变体）
  - `mixin/` 11 个、`state/properties/` 4 个（`TripleBlockPart` 等）、`config/` 3 个、`entity/ai/goal/` 3 个、`registry/` 3 个（`DDNames` 全部字面量名）、`tags/` 2 个、`blockentities/` 2 个、`compat/` 4 个
  - 平台侧：`fabric/`（registry、datagen 2、mixin 4、addons/create 7）、`neoforge/`（registry、datagen 3、mixin 2、compat 3、addons/create 5）
- 最大文件：`registry/DDNames.java`(182KB，纯常量)、`compat/registries/MacawCompat.java`(133KB)、`ChippedCompat.java`(103KB)、`ManyIdeasCompat.java`(62KB)、`MoreDoorsCompat.java`(48KB)、`AbnormalsCompat.java`(34KB)、`BWGCompat.java`(26KB)、`blocks/TallDoorBlock.java`(24KB)、`fabric/.../DDModelProvider.java`(16KB)

## 3. 入口与注册

common 只有 `DramaticDoors.java`（`MOD_ID` + `LOGGER` 常量，`:6-11`）。平台入口：`fabric/.../DramaticDoorsFabric.java`（`ModInitializer.onInitialize`）与 `neoforge/.../DramaticDoorsNeoForge.java`（`@Mod` 构造注入 `IEventBus` + `ModContainer`）。

**注册体系不是 DeferredRegister**：common 侧 `registry/DDRegistry.java` 用工厂方法把方块/物品实例塞进静态列表，loader 侧再批量注册。

```java
// common/registry/DDRegistry.java:66-79
public static void registerDoorBlockAndItem(String tallname, @Nullable String shortname, Block block, BlockSetType blocksettype, boolean includeShort) {
    ...
    tempBlock = createDoorBlock(block, blocksettype, true);
    DOOR_BLOCKS.add(new Pair<String, Block>(tallname, tempBlock));
    DOOR_ITEMS.add(new Pair<String, Item>(tallname, tempItem));
}
// neoforge/DDNeoForgeRegistry.java:39-48
event.register(Registries.BLOCK, helper -> { for (Pair<String, Block> pair : DDRegistry.DOOR_BLOCKS) helper.register(ResourceLocation.fromNamespaceAndPath(MOD_ID, pair.getA()), pair.getB()); });
```

NeoForge 侧 `@SubscribeEvent registerBlocksItems(RegisterEvent)`（`DDNeoForgeRegistry.java:31-71`）在 **RegisterEvent 内部**先跑 `Compats.registerCompats(...)`、再按 `isModLoaded` 条件构造 `BlockEntityType`（`TALL_NETHERITE_DOOR`、Create 的 `TALL_SLIDING_DOOR`）与条件化的创造模式标签页。

## 4. 核心系统

**a) 兼容层：一个接口 + 一张巨型 if 表（`common/compat/Compats.java`）**
- `CompatChecker` 是 3 个 default 方法的接口（`isModLoaded` / `isDev` / `isQuarkModuleEnabled`），由 `NeoforgeUtils.INSTANCE`、`FabricUtils.INSTANCE` 分别实现。
- `Compats.registerCompats(checker)`（`:27-363`）里 100+ 条 `if (isModLoaded("xxx", checker)) XxxCompat.registerCompat();`，全部映射到 `compat/registries/XxxCompat`；`isDev()` 为真时**所有兼容都注册**（`:365-374`），便于开发环境一次编译全部分支。
- 状态既存"是否安装"布尔字段（`MACAWS_DOORS_INSTALLED` 等，`:13-25`），也存被兼容 mod 的方块引用（如 `CreateCompat.TALL_ANDESITE_DOOR`）。

**b) 三格高门方块（`common/blocks/TallDoorBlock.java`）**
- 不继承 `DoorBlock` 而是 `extends Block implements SimpleWaterloggedBlock`（`:62`），自定义属性 `THIRD = DDBlockStateProperties.TRIPLE_BLOCK_THIRD`（`TripleBlockPart`: THIRD/LOWER/UPPER）与 `FACING/OPEN/HINGE/POWERED/WATERLOGGED`（`:67-72`）。
- 关键重写：`updateShape`（LOWER 朝下 `canSurvive`，`:99-106`）、`playerWillDestroy`（`:114`）、`setPlacedBy`（拆成 3 段，`:162`）、`useWithoutItem`/`toggleDoor`/`setOpen`（游戏事件 `GameEvent.BLOCK_OPEN/CLOSE`，`:204-282`）、`neighborChanged`、`canSurvive`、`getSeed`、`getShape`+`PathType`（`net.minecraft.world.level.pathfinder.PathType` 导入早于 1.21 稳定）。

**c) Mixin 条件加载插件**
- `neoforge/.../mixin/DDMixinConfigNeoForge implements IMixinConfigPlugin`：`onLoad` 里先 `DDConfigCommon.initializeConfigs()`（**mixins 应用前读配置**），`shouldApplyMixin` 用 `DDConfigCommon.waterloggableDoors` 与 `LoadingModList.get().getModFileById("mcwdoors") != null` 决定是否应用（`DoorBlockMixin`、`JapaneseDoorBlockMixinNeoForge`、`FenceGateBlockMixin`）；Fabric 侧有对应的 `DDMixinConfigFabric`。

**d) 原版方块的"外挂状态"（`DoorBlockMixin`/`FenceGateBlockMixin`）**
- `@Inject(at = @At("TAIL"), method = "<init>(...properties;)V")` + `createBlockStateDefinition` TAIL 给原版 `DoorBlock`/`FenceGateBlock` **追加 WATERLOGGED 属性**，再 HEAD 注入 `getStateForPlacement`/`updateShape`（cancellable）实现水logging；不改原版类而是扩展其状态机。

**e) 实体 AI 兼容（`entity/ai/goal/` + 4 个实体 mixin）**
- `OpenTallDoorsTask`/`OpenShortDoorsTask` 实现 `BehaviorControl<LivingEntity>`（`:28`），沿路径节点检测 `DDBlockTags.MOB_INTERACTABLE_TALL_DOORS` 上的 `TallDoorBlock`，用原版 `InteractWithDoor.rememberDoorToClose` / `closeDoorsThatIHaveOpenedOrPassedThrough` 复用原版开关门逻辑（`:50-61`）；`DDVillagerTasks` 负责装配。
- mixin：`WalkNodeEvaluatorMixin.getPathTypeFromState`（INVOKE 处 cancellable，让新门成为可寻路方块）、`DoorInteractGoalMixin`（`isOpen` HEAD cancellable / `setOpen` TAIL / `canUse` 在 `DoorBlock.isWoodenDoor` 调用后 shift 注入）、`VillagerMixin.registerBrainGoals`、`PiglinBrainMixin.makeBrain`、`WitchMixin.registerGoals`（TAIL 追加门任务）。

**f) Create 6.x 新 API 集成（`neoforge/.../compat/CreateNeoForgeCompat.java`、`addons/create/`）**
- 不 mixin Create，走官方注册表：`MovingInteractionBehaviour.REGISTRY.registerProvider(SimpleRegistry.Provider.forBlockTag(DDBlockTags.TALL_WOODEN_DOORS, new TallDoorMovingInteraction()))`、`MovementBehaviour.REGISTRY.register(CreateCompat.TALL_ANDESITE_DOOR, new TallSlidingDoorMovementBehaviour())`。
- `TallSlidingDoorMovementBehaviour implements MovementBehaviour`（`mustTickWhileDisabled() == true`）处理 contraption/电梯列/列车车厢场景，用 `TallNeoForgeCreateSlidingDoorBlockEntity.isOpen(state)` 判定；客户端 `DDPartialModels.putFoldingDoor(id, "create/tall_andesite_door")` 注册 Flywheel 部分模型。

**g) 服务端数据改写** `AdvancementManagerMixin`（`ServerAdvancementManager.apply` HEAD）、`RecipeManagerMixin`（`RecipeManager.apply` HEAD）、`BlockLootMixin`（`BlockBehaviour.getDrops` 内 `LootTable.getRandomItems` INVOKE 处 cancellable）、`DDCompatRecipe`/`DDCompatAdvancement`：**运行时**把原版门配方/进度扩展到高/矮门，而不是写 JSON。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包（纯原版方块状态同步）。
- 配置：自研轻量库 `config/SimpleConfig.java` + `ModConfigProvider`，`DDConfigCommon.initializeConfigs()`（`:21-42`）在启动早期构建并写入 `dramaticdoors-startup`；键：`Experimental.dev_mode`、`Mixins.waterloggable_doors`、`waterloggable_fence_gates`（这些值必须在 mixin 加载前可用）。NeoForge 侧另注册 `IConfigScreenFactory → ConfigurationScreen::new` 复用平台配置界面。
- datagen：Fabric 走 `DataGeneratorEntrypoint` + `createPack().addProvider(DDModelProvider::new)`（`fabric/.../datagen/DramaticDoorsDataGenerators.java`）；NeoForge 走 `GatherDataEvent` 加 `DDBlockStateProvider`、`DDItemModelProvider`（`neoforge/.../datagen/DramaticDoorsDataGenerators.java`）。模型/方块状态由代码生成，配方与进度相反是运行时注入。

## 6. Mixin

- 三份配置：`common/src/main/resources/dramaticdoors.mixins.json`（11 个 mixin：`AdvancementManagerMixin, RecipeManagerMixin, BlockLootMixin, WalkNodeEvaluatorMixin, DoorBlockMixin, FenceGateBlockMixin, DoorInteractGoalMixin, OpenDoorsTaskMixin, PiglinBrainMixin, VillagerMixin, WitchMixin`，`compatibilityLevel: JAVA_21`，`maxShiftBy: 2`，带 refmap）、`dramaticdoors_neoforge.mixins.json`（带 `plugin`）、`dramaticdoors_fabric.mixins.json`（`plugin` + client `CPIMMixin`、server `SPIMMixin`），后两份由 `neoforge.mods.toml` 的两个 `[[mixins]]` 引入。
- 代表性 hook：`DoorBlockMixin`（`DoorBlock.<init>` / `createBlockStateDefinition` TAIL；`getStateForPlacement`、`updateShape`、`setPlacedBy` HEAD cancellable）、`WalkNodeEvaluatorMixin`（`getPathTypeFromState`）、`OpenDoorsTaskMixin`（`InteractWithDoor.closeDoorsThatIHaveOpenedOrPassedThrough`，`LocalCapture.CAPTURE_FAILSOFT`）。

## 7. 值得学的 5 条具体做法

1. **"兼容即数据表"的架构**：所有第三方适配收敛到一个 `CompatChecker` 接口 + 一张 `isModLoaded` 大表 + 每 mod 一个 `XxxCompat` 类，`isDev()` 时全开（`common/compat/Compats.java:27-374`）。做 Create/多模组联动 mod 时可照搬，避免兼容代码散落各处。
2. **common 侧只造对象、loader 侧才注册**：`DDRegistry` 产出 `List<Pair<String, Block>>`，用 `RegisterEvent` 里 `helper.register(ResourceLocation, block)` 遍历注册（`neoforge/DDNeoForgeRegistry.java:39-48`），从而让"注册什么"依赖运行时 mod 检测结果（DeferredRegister 做不到条件动态 ID）。
3. **`IMixinConfigPlugin` 在 `onLoad` 提前读配置**：把"是否启用某 mixin"变成配置开关 + 依赖检测，且早于 mixin 应用（`DDMixinConfigNeoForge.onLoad`），比在注入点里 return 更彻底（连目标类都不改写）。
4. **Create 6.x 用官方注册表扩展，不 mixin Create**：`MovingInteractionBehaviour.REGISTRY.registerProvider(SimpleRegistry.Provider.forBlockTag(...))` 与 `MovementBehaviour.REGISTRY.register(block, behaviour)`（`CreateNeoForgeCompat.java:28-46`），且用 `create-...:slim` + `transitive=false` 控制依赖体积。这是 Create 附属的正确接入姿势。
5. **用 mixin 给原版方块"加状态"而不是替换原版**：`DoorBlockMixin`/`FenceGateBlockMixin` 通过 `<init>` 与 `createBlockStateDefinition` 的 TAIL 注入为原版门/栅栏门追加 `WATERLOGGED`（并由配置与 mixin 插件双层开关保护），同时 `WalkNodeEvaluatorMixin` + 自定义 `BehaviorControl` 让原版 AI 认得新门（`entity/ai/goal/OpenTallDoorsTask.java:50-61`）。若目标是 NeoForge 1.21.1 的高版本复刻，注意这些写法属于 1.21.1 API（`PathType`、`RegisterEvent`、`IMixinConfigPlugin` 仍适用，但 `DoorBlock` 属性集与 `getPathTypeFromState` 签名在新版可能变化）。

## 8. 公开 API

非库 mod，无对外 API 包。扩展点在数据层：`DDBlockTags`（如 `MOB_INTERACTABLE_TALL_DOORS`）与 `compat/registries/` 的注册表模式可被其他 mod 参考，但无文档化接口。
