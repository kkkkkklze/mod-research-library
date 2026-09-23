# blorbee1/createaerophysicsgantry 源码分析报告

## 1. 基本信息

- Mod 名：Create Aeronautics Physics Gantry；mod_id `createaerophysicsgantry`；作者 blorbee；版本 1.0.3
- 目标：Minecraft 1.21.1 / NeoForge（`neo_version=21.1.228`，`loader_version_range=[1,)`）；Parchment 2024.11.17；Java 21
- Gradle：Groovy + `net.neoforged.moddev` 2.0.141；mod 元数据由 `src/main/templates/META-INF/neoforge.mods.toml` 经 `generateModMetadata` 展开生成（`build.gradle:145-176`）
- 许可证：MIT
- 依赖：Create 6.0.10-281（slim，非传递）、Ponder 1.0.82、Flywheel 1.0.6（api/compileOnly）、Registrate `MC1.21-1.3.0+67`；**Sable 2.0.3**（`dev.ryanhcode.sable`，排除 `foundry.veil`、非传递）与 `sable-companion-common` 1.6.0；Create Simulated 1.3.0（`flatDir libs/`，compileOnly `simulated-neoforge`）、`create-aeronautics-bundled`（runtimeOnly）；JEI 19.21.2.313
- mods.toml 依赖：create / sable / sablecompanion / aeronautics_bundled 全部 required、ordering=AFTER、BOTH

## 2. 源码规模与包结构

实测：26 个 `.java`，合计 5179 行，重度集中在单个 BlockEntity。

- `com.blorbee.createaerophysicsgantry`（根，2）：`CreateAeroPhysicsGantry`、`CreateAeroPhysicsGantryClient`
- `...content.physics_gantry_carriage`（4）：`PhysicsGantryCarriageBlockEntity`(1689)、`...Visual`(114)、`...Block`(127)、`...Renderer`(82)
- `...content.belt_wheel`（4）：`BeltWheelBlockEntity`(592)、`BeltWheelRenderer`(318)、`BeltWheelBlock`(285)、`BeltWheelVisual`(102)
- `...content.physics_gantry_shaft`（3）：`...Block`(295)、`...BlockEntity`(226)、`...Visual`
- `...registry`（4）、`...ponder`+`...ponder.scenes`（3）、`...mixin`（2）、`...compat.simulated`（1）、`...util`（1）、`...config`（1）、`...data`（1）

## 3. 入口与注册

`src/main/java/com/blorbee/createaerophysicsgantry/CreateAeroPhysicsGantry.java:25`，Registrate 单例 + 三个注册类静态 `register()`：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MOD_ID)
    .defaultCreativeTab((ResourceKey<CreativeModeTab>) null)          // :31 刻意不建标签页
    .setTooltipModifierFactory(item -> new ItemDescription.Modifier(...));
...
CAPGBlocks.register();  CAPGBlockEntityTypes.register();
CAPGCreativeTab.registerAeronauticsSections();                        // :41 挂到 simulated 分区
modEventBus.addListener(EventPriority.HIGHEST, CAPGDatagen::gatherData);
modContainer.registerConfig(ModConfig.Type.SERVER, ServerConfig.getSpec());
```

`registry/CAPGCreativeTab.java:14-28` 直接操作第三方 `SimulatedRegistrate.TAB_ITEMS` 与 `ITEM_TO_SECTION`，把 3 个物品塞进 `simulated:simulated` 分区，避免新建创造标签页。客户端 `CreateAeroPhysicsGantryClient.java:19` 用 `IConfigScreenFactory` + `ConfigurationScreen::new` 自动获得配置界面。

## 4. 核心系统

**A. 物理龙门架小车（`PhysicsGantryCarriageBlockEntity`，1689 行）**：`extends KineticBlockEntity implements IDisplayAssemblyExceptions, BlockEntitySubLevelActor`，即把 Create 龙门架改造成 Sable "SubLevel（子关卡）装配体"的驱动器。状态字段：`assembledToSubLevel`、`attachedShaftPos/Direction/CarriageFacing`、`attachedSubLevelId`/`attachedShaftSubLevelId`（UUID）、`attachedShaftProgress`、`shaftConstraintHandle`（Sable `GenericConstraintHandle`）与 `shaftConstraintWorldAnchor`。

**B. 装配 / 拆卸流程**：`forceToggleAssembly()`（:118）判断 `isAttachedPayloadSubLevel` 后走 `doSubLevelAssemble()`/`doSubLevelDisassemble()`；装配时先用 Create 的 `invokeDisassembleAndAddCreateContraptions` 处理已挂载 contraption 与其 glue，再用 `SubLevelAssemblyHelper.assembleBlocks(serverLevel, anchor, assembledBlocks, bounds)`（:472）生成 `ServerSubLevel`，并按 `plot.getCenterBlock()` 与 anchor 的差值平移锚点；失败通过 `AssemblyException`/`IDisplayAssemblyExceptions` 上屏。

**C. 参考系锁定**：`Quaterniond lockedSubLevelOrientation` / `lockedShaftFrameOrientation`、`Vector3d lockedLocalAttachmentAnchor` / `lockedRotationPoint` 配 `hasLocked*` 布尔，在装配/旋转期间冻结姿态，`runAttachmentTick`（:810）用 `lastAttachmentTickGameTime` 去重后 `tickAttachedSubLevelMovement` 重建约束。

**D. 皮带轮跨子关卡传动（`belt_wheel/`）**：`BeltWheelBlockEntity extends GeneratingKineticBlockEntity`，用静态 `WeakHashMap<Level, Set<BeltWheelBlockEntity>> INDEXED_WHEELS`（:30-42）做索引，靠 `linkedPos` + `linkedSubLevelId(UUID)` 记录配对端点，`resolveLinkedWheel`/`findLinkedWheelAnywhere` 通过 `SimulatedHelper.findBlockEntity...` 跨子关卡查找；`wouldCreateKineticLoop` 用 BFS（Queue + visitedWheels，:341-390）阻止动能环；应力/容量不依赖 Create 网络而是手动重算（`calculateAddedStressCapacity` / `calculateStressApplied` / `updateFromNetwork`）。配对操作在 `BeltWheelBlock.useItemOn`（:62-167，含 `breakLink` 与 `setLinkedTarget`）。

**E. SubLevel 桥接工具（`compat/simulated/SimulatedHelper.java`）**：集中处理子关卡坐标/法线变换——`Pose3d.transformPosition/transformNormal/transformPositionInverse`、`Sable.HELPER.projectOutOfSubLevel` 迭代投影（最多 8 次，:118-139）、`toRenderFramePosition` 把世界坐标转回渲染子关卡局部系。`util/SubLevelBlockEntityCollector` 经 `SubLevelContainer.getContainer(level).getSubLevel(uuid)` 与 `plot.getBlockEntityActors()` 枚举子关卡内方块实体。

**F. 渲染**：Flywheel 化，`PhysicsGantryCarriageVisual extends ShaftVisual implements SimpleDynamicVisual`，用 `CAPGPartialModels.PHYSICS_GANTRY_COGS` 与 `animateCogs`；方块本身复用 `BlockStateGen.directionalAxisBlock` 与手写模型路径（`registry/CAPGBlocks.java:75-96`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包；两个 mixin 注入到 Create Simulated 的粘合流程。
- 数据驱动：无 JSON 注册表；配方/blockstate/model 全部内联在 Registrate 链中（`CAPGBlocks.java:33-145`，含 `ShapedRecipeBuilder`/`ShapelessRecipeBuilder` 与 `TagGen.axeOrPickaxe`）。
- datagen：`data/CAPGDatagen.java` 只生成 LANG：用 `FilesHelper.loadJsonResource("assets/createaerophysicsgantry/lang/default/default.json")` 灌入，并调用 `PonderIndex.getLangAccess().provideLang(MOD_ID, provider::add)` 自动导出 Ponder 文本（:21-30）。
- 配置：`config/ServerConfig.java` 仅一个 `IntValue beltWheelMaxDistance`（1..64，默认 64）。

## 6. Mixin

配置 `src/main/resources/createaerophysicsgantry.mixins.json`（JAVA_21、带 refmap、`defaultRequire: 1`），两个类都用于禁止"轮对轮"粘合：`PlaceMergingGluePacketMixin` 注入 `handle` HEAD 并 `ci.cancel()`，`MergingGlueItemHandlerMixin` 注入 `onItemUseBlock` HEAD（`@Shadow BlockPos firstPos; @Shadow Direction firstDirection;`，改用客户端 `hitResult`），并用 `SimulatedHelper.findBlockEntityIncludingSubLevels` 判断端点是否为小车。

注意：两个 mixin 的 `@Mixin(...)` 实参写的是自身类名（如 `@Mixin(PlaceMergingGluePacketMixin.class)`），而文件内 import 的目标是 `dev.simulated_team.simulated.network.packets.PlaceMergingGluePacket`；`MergingGlueItemHandlerMixin` 更是没有对应 import。**未确认**该写法是否真能命中目标（疑似笔误），复用时请写明目标类全名。

## 7. 值得学的 5 条具体做法

1. 把与第三方物理库的所有交互收进一个 `SimulatedHelper`（`compat/simulated/SimulatedHelper.java`），业务类不再直接碰 `SubLevel` 数学；适用于任何"可选/重型依赖"。
2. 用静态 `WeakHashMap<Level, Set<BE>>` 索引同类型方块实体，实现跨区块/跨子关卡的配对查找（`BeltWheelBlockEntity.java:30-42`）。
3. 复杂装配用"锁定参考系"字段（`Quaterniond` + `hasLocked*` 标志 + `lastAttachmentTickGameTime` 去重），避免同 tick 内重复重建物理约束。
4. 复用 Create 的 `IDisplayAssemblyExceptions`/`AssemblyException`，把装配失败原因直接呈现给玩家。
5. 不建自己的创造标签页：把物品注册进第三方 `SimulatedRegistrate.TAB_ITEMS` 分区（`CAPGCreativeTab.java:26-27`），并只做 LANG datagen（含 Ponder 文本自动导出）。

## 8. 公开 API

非库 mod，无对外 API；接缝点是 Sable 的 `BlockEntitySubLevelActor`、`SubLevelAssemblyHelper`、`GenericConstraintHandle` 与 Create Simulated 的 `SimulatedRegistrate`、`PlaceMergingGluePacket`。
