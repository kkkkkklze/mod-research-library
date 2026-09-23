# terrarium-earth/Handcrafted 源码分析报告

## 1. 基本信息

- Mod 名：Handcrafted（"Epic Furniture mod!"）；mod_id `handcrafted`；作者 Alex Nijjar(Alex Nijjar/AlexModGuy 团队)、Kekie6；credits CodexAdrian、ThatGravyBoat 等（`neoforge/src/main/resources/META-INF/neoforge.mods.toml:13`）；许可证 **Terrarium Licence**（自查式许可证，非 SPDX 标准）。
- 版本 4.0.3、MC 1.21.1、Parchment `2024.07.28`（`gradle.properties:5-9`）。加载器：**fabric + neoforge**（`enabledPlatforms=fabric,neoforge`），走 **Architectury**：`dev.architectury.loom 1.6-SNAPSHOT` + `architectury-plugin 3.4-SNAPSHOT` + `com.teamresourceful.resourcefulgradle` + shadow 7.1.2（`build.gradle.kts:7-13`）。子项目 `common/fabric/neoforge`（`settings.gradle.kts`），启用 TYPESAFE_PROJECT_ACCESSORS。
- 关键依赖：**ResourcefulLib 3.0.9**（`resourcefullib-fabric/neoforge-1.21`，声明为 `required`，mods.toml 里 `versionRange="[3.0.0,)"`）；`tech.thatgravyboat:commonats:2.0`（`modCompileOnly`，common 的 access transformer）；fabric 侧 fabric-loader 0.15.11 + fabric-api 0.115.3 + modmenu 11.0.1；neoforge 侧 neoforge 21.1.1。

## 2. 源码规模与包结构

- 实测：`find . -name '*.java' | wc -l` = **86 个文件，8057 行**。几乎全部逻辑在 `common/src/main/java/earth/terrarium/handcrafted/`，平台层只有入口与 2 个 `*Impl`。
- 包结构：`common/blocks`（含 `base`、`base/properties` 6 个自定义 Property、`crockery`、`misc`、`trims`、`trophies`）约 35 个类；`common/registry` 5；`common/blockentities` 2；`common/entities` 2；`common/items` 4；`common/tags` 3；`common/utils` 2；`common/constants` 1；`client/renderer`（含 `fancypainting`）；`datagen`（**只在 neoforge 子项目**）10 个 provider。
- 最大文件：`datagen/provider/client/ModBlockStateProvider.java`(568)、`ModRecipeProvider.java`(456)、`common/blocks/trims/CornerTrimBlock.java`(371)、`common/registry/ModItems.java`(369)、`ModHighlightBlockStateProvider.java`(356)、`common/registry/ModBlocks.java`(346)、`PillarTrimBlock.java`(270)、`TableBlock.java`(205)、`entities/Seat.java`(198)。

## 3. 入口与注册

公共入口（`common/.../Handcrafted.java`）：

```java
public class Handcrafted {
    public static final String MOD_ID = "handcrafted";
    public static void init() {
        ModBlocks.BLOCKS.init();
        ModItems.ITEMS.init();
        ModItems.TABS.init();
        ModBlockEntityTypes.BLOCK_ENTITY_TYPES.init();
        ModEntityTypes.ENTITY_TYPES.init();
        ModSoundEvents.SOUND_EVENTS.init();
    }
}
```

- neoforge：`Earth.../neoforge/HandcraftedNeoForge.java` 用 `@Mod(Handcrafted.MOD_ID)`，构造里 `Handcrafted.init()`，再按 `FMLEnvironment.dist.isClient()` 调 `HandcraftedClientNeoForge.init()`。fabric 对应 `fabric/HandcraftedFabric.java`（`init()` + `addBedPoi()`）。
- **注册框架：ResourcefulLib 的 `ResourcefulRegistry`**（不是 DeferredRegister/Registrate）：`ResourcefulRegistries.create(BuiltInRegistries.BLOCK, Handcrafted.MOD_ID)` 建根，`ResourcefulRegistries.create(BLOCKS)` 建子表，最后统一 `.init()` 触发实际注册（`ModBlocks.java:23-53`）。
- 注册项为 `RegistryEntry<Block>`，惰性 `Supplier`：`BLOCKS.register("oven", () -> new OvenBlock(...))`；方块属性直接 `BlockBehaviour.Properties.ofFullCopy(Blocks.SMOKER)` 复用原版属性（`ModBlocks.java:55-59`）。

## 4. 核心系统

1. **层级化分类注册表**（`common/registry/ModBlocks.java`）：`BLOCKS → CUSHIONS/BENCHES/COUCHES/... → WOODEN_BENCHES/METAL_BENCHES`、`TRIMS → PILLAR_TRIMS/CORNER_TRIMS`、`TROPHIES → WALL/HANGING/STATUE`、`CROCKERY → CUPS/PLATES/BOWLS/CROCKERY_COMBOS`。子表天然成为"同类物品分组"，datagen 与配方可直接 `stream()` 遍历，避免手写枚举列表。
2. **可坐家具的实体方案**（`common/entities/Seat.java` + `blocks/base/SittableBlock.java` + `ModEntityTypes.java:16-22`）：注册 `seat` 为 `MobCategory.MISC`、`noSave()`、`noSummon()`、`fireImmune()`；`Seat.of(level,pos,dir)` 从 `SittableBlock.getSeatSize(state)` 取自定义 AABB 决定座位形状；构造函数里 `this.setLevelCallback(EntityInLevelCallback.NULL)` 让实体不进区块实体索引；用静态 `Multimap<ResourceKey<Level>, BlockPos> SITTING_POSITIONS` 做"该方块是否已有人坐"的跨维度去重；朝向标志 `canRotate` 通过 `new ClientboundAddEntityPacket(this, serverEntity, canRotate ? 1 : 0)` 的 data 字段同步，并在 `recreateFromPacket` 还原——**不用自建网络包就完成客户端同步**。
3. **模块化沙发/长椅形状推断**（`blocks/base/ModularSeatBlock.java` + `properties/ModularSeatProperty.java`）：`EnumProperty<ModularSeatProperty> SHAPE`（SINGLE/LEFT/RIGHT/MIDDLE/INNER_LEFT/INNER_RIGHT/OUTER_LEFT/OUTER_RIGHT）+ `WATERLOGGED`；`getShape(state, level, pos)` 由邻居同族方块推断角/边形态，`updateShape` 邻居变化时重算，`mirror`/`rotate` 交换 INNER/OUTER 左右（:45-70）。同类模式还有 `TableProperty`、`CounterProperty`、`TrimProperty`、`DirectionalBlockProperty`。
4. **一套 BE 服务多套家具**（`common/registry/ModBlockEntityTypes.java:23-37`）：`ContainerBlockEntity extends RandomizableContainerBlockEntity`（`ContainerHelper.saveAllItems/loadAllItems`，`createMenu` 直接返回 `ChestMenu.threeRows`）被 `COUNTERS/CUPBOARDS/DESKS/DRAWERS/NIGHTSTANDS/SHELVES/SIDE_TABLES` 共 7 组方块共享，注册时用 `List<RegistryEntry<Block>>` 聚合后 `BlockEntityType.Builder.of(factory, blocks...).build(null)`。
5. **小物件状态同步**（`blocks/crockery/CrockeryBlockEntity.java`）：只存一个 `ItemStack item`，`update()` 里 `level.sendBlockUpdated(pos, state, state, Block.UPDATE_ALL)` + 覆写 `getUpdateTag/getUpdatePacket`，是最小可用的 BE→客户端同步样板。
6. **平台差异抽离**（`client/utils/ClientPlatformUtils.java`）：用 Architectury 的 `@ExpectPlatform` 声明 `registerRenderer(...)`，fabric/neoforge 各写一个 `ClientPlatformUtilsImpl`；common 侧还定义 `BlockRendererRegistry` / `LayerDefinitionRegistry` 两个函数式接口当作回调，从而 common 完全不 import loader 专有 API。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自建包**。同步只借原版 `ClientboundAddEntityPacket` 的 data 字段与 BE 的 `getUpdatePacket`。
- **数据驱动**：`FancyPainting extends net.minecraft.world.entity.decoration.Painting`（`common/entities/FancyPainting.java`），挂靠原版 `Registries.PAINTING_VARIANT` 数据包注册表，`readAdditionalSaveData` 里用 `registryAccess().lookupOrThrow(Registries.PAINTING_VARIANT)` 解析；画作变体在 datagen 中 bootstrap（`datagen/provider/server/registry/ModPaintingVariantProvider.java`）。客户端 `client/renderer/fancypainting/FancyPaintingModel.java` + `FancyPaintingRenderer` 动态生成模型，故能容纳大幅画作。
- **配置：无**（无 config 文件/网络配置）。
- **datagen：完整且只在 neoforge 子项目**（`neoforge/.../datagen/HandcraftedDataGenerator.java`）：`@EventBusSubscriber(bus = MOD)` + `GatherDataEvent`，注册 `ModLangProvider / ModItemModelProvider / ModBlockStateProvider / ModHighlightBlockStateProvider`（client）与 `ModRegistryProvider / ModLootTableProvider / ModRecipeProvider / ModItemTagProvider / ModBlockTagProvider / ModPaintingVariantTagProvider`（server）；`ModRegistryProvider` 统一 bootstrap painting variant。data run 定义在 `neoforge/build.gradle.kts`（`--all --mod handcrafted --output common/src/main/generated/resources`），生成物回写 common。

## 6. Mixin

- 配置两份：`common/src/main/resources/handcrafted-common.mixins.json`（`required:true`、`package earth.terrarium.handcrafted.mixins`、`compatibilityLevel JAVA_21`、client 段含 `common.BlockElementMixin`）与 `fabric/src/main/resources/handcrafted.mixins.json`（`package ...mixins.common.fabric`，`PoiTypesAccessor`）。
- `common/.../mixins/common/BlockElementMixin.java`：`@Mixin(targets = "net.minecraft.client.renderer.block.model.BlockElement$Deserializer")`，对 `getAngle` / `getTo` / `getFrom` 做 `@Inject(method=..., at=@At("HEAD"), cancellable=true)` 并直接 `cir.setReturnValue(...)`——**移除原版对模型元素旋转角与立方体尺寸的限制**（家具模型需要超出 16 立方/45° 的几何），配合 `@Shadow getVector3f` 复用原版解析。
- `fabric/.../mixins/common/fabric/PoiTypesAccessor.java`：`@Mixin(PoiTypes.class)` + `@Accessor("TYPE_BY_STATE") static Map<BlockState, Holder<PoiType>> getTypeByState()`，供 `HandcraftedFabric.addBedPoi()` 把 `FANCY_BEDS` 的 HEAD 状态写进原版 HOME POI（让村民认床）。neoforge 侧不需要该 mixin（有官方 POI 注册 API）。

## 7. 值得学的 5 条具体做法

1. **分层 ResourcefulRegistry 当"物品分类"用**：`ResourcefulRegistries.create(BLOCKS)` 派生子表，`.init()` 统一落地（`common/registry/ModBlocks.java:23-53`）；适用：家具/装饰类模组要按颜色、材质批量生成物品与配方。
2. **座位用 MISC 实体 + `EntityInLevelCallback.NULL`**：`noSave()/noSummon()`，并用 `ClientboundAddEntityPacket` 的 data 位传状态（`common/entities/Seat.java:32-77`、`ModEntityTypes.java:16-22`）；适用：坐垫、椅子、任何"可坐"交互而不想写自定义包。
3. **一套 BE 类型覆盖多套方块**：把 7 个子注册表 `getEntries()` 聚合后一次 `BlockEntityType.Builder.of(...).build(null)`（`ModBlockEntityTypes.java:23-37`）；适用：大量外观不同但存档结构相同的容器方块，直接省掉 N 个 BE 类型。
4. **`@ExpectPlatform` 隔离加载器差异**：common 只声明抽象函数 + 函数式回调接口，fabric/neoforge 各一个 `*Impl`（`client/utils/ClientPlatformUtils.java`）；适用：想用 Architectury 但不愿被 Architectury API 侵入全部代码。
5. **mixin 只加"放宽原版限制"的一处注入**：`BlockElementMixin` 用 HEAD + cancellable 把 `getAngle/getTo/getFrom` 换成宽松版本（`common/.../mixins/common/BlockElementMixin.java`）；适用：家具/装饰模型需要超出原版 JSON 模型约束时，比自建模型加载器成本低得多。

## 8. 库/API 说明

非库 mod。对外扩展点仅在注册表的公开静态字段（`ModBlocks.*`、`ModTags`），`commonats` 只用于自身 access transformer（`common/build.gradle.kts:6-8`）。
