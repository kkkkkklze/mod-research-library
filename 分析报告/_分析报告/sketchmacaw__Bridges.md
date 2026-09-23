# Macaw's Bridges 源码分析

## 1. 基本信息
- Mod 名 / mod_id：Macaw's Bridges / `mcwbridges`（Forge 主类 `MacawsBridges.java:17` `@Mod("mcwbridges")`；Fabric 主类同名）
- 作者：sketchmacaw（包名里保留原作者 `kikoz`）；README 一行："Macaw's Bridges adds lots of bridges, bridge stairs and piers."
- 目标 MC 版本与加载器：3 个平行目录 —— `1.20.1  Fabric`（Yarn 映射，包 `net.kikoz.mcwbridges`）、`1.20.1 Forge`、`1.20.4 Forge`（包 `com.mcwbridges.kikoz`，**两个平台包名不同**）
- Gradle 插件：**未确认** —— 纯源码快照，**无 `build.gradle` / `gradle.properties` / `src/main/resources` / `fabric.mod.json` / license 文件**，非 java 文件只有 `README.md`
- 编译依赖：无第三方 mod 依赖；Forge 侧仅用 `net.minecraftforge.common.extensions.IForgeItem`、`api.distmarker.OnlyIn`；Fabric 侧用 `net.fabricmc.fabric.api.itemgroup.v1.FabricItemGroup`、`fabric.api.blockrenderlayer.v1.BlockRenderLayerMap`（Fabric API）

## 2. 源码规模与包结构
- 55 个 `.java`，合计 **7273 行**（`1.20.1 Fabric` 17、`1.20.1 Forge` 19、`1.20.4 Forge` 19）
- 包结构（三版本同构）：
  - 根：`MacawsBridges.java`（主类）
  - `init/`：`BlockInit`（206-227 行，**145 个 `RegistryObject<Block>`**）、`ItemInit`（146 个物品）、`TabInit`（仅 Forge 有）
  - `objects/`：`Bridge_Block`、`Bridge_Block_Rope`、`Bridge_Stairs`、`Bridge_Support`、`Iron_Bridge`、`Log_Bridge`、`Rail_Bridge`、`Bamboo_Bridge`
  - `objects/items/`：`Bridge_Torch`、`Bridge_Lantern`、`Plier`
  - `util/`：`BlockItemWithInfo`、`LightInfo`、`FuelBlockItemWithInfo`、`FuelItemBlock`（Forge）、`ClientEventBusSubscriber`（Fabric 侧是 `ClientModInitializer`）
- 最大文件：`objects/Bridge_Block_Rope.java`(442/429)、`objects/Bridge_Block.java`(333)、`objects/Bridge_Stairs.java`(227)、`init/BlockInit.java`(227 Fabric / 206 Forge)、`init/ItemInit.java`(197)

## 3. 入口与注册
Forge（`1.20.4 Forge/MacawsBridges.java:23-34`）：
```java
final IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
modEventBus.addListener(this::setup);
modEventBus.addListener(this::doClientStuff);
ItemInit.ITEMS.register(modEventBus);
BlockInit.BLOCKS.register(modEventBus);
TabInit.CREATIVE_TABS.register(modEventBus);
```
- Forge 用原生 `DeferredRegister`（`BlockInit.java:28`、`ItemInit`、`TabInit` 各自持有 1 个 `DeferredRegister`），每个方块一行 `BLOCKS.register("id", () -> new Log_Bridge(BlockBehaviour.Properties.ofFullCopy(Blocks.X_PLANKS)))`，属性**一律抄原版**（`1.20.4 Forge/init/BlockInit.java:32-60`）；1.20.1 用 `Properties.copy(...)`，1.20.4 改名为 `ofFullCopy(...)`（可直接 diff `1.20.1 Forge/init/BlockInit.java:30` vs `1.20.4 Forge/init/BlockInit.java:30`）
- Fabric 用裸 `Registry.register(Registries.BLOCK, new Identifier(MOD_ID, name), block)`，封装在 4 个私有 helper 里：`registerBlock / registerLightBlock / registerBridgeBlock / registerBlockItem / registerLightBlockItem / registerBridgeBlockItem`（`1.20.1  Fabric/init/BlockInit.java:194-226`）。**方块的物品在 BlockInit 一起注册**（所以 Fabric `ItemInit` 只有 1 个 `public static final Item`，即 `PLIERS`）。Fabric 主类 `onInitialize()` 调 `BlockInit.registerModBlocks()`（该方法体**为空**，注册全在类静态初始化时完成）+ `ItemInit.registerModItems()`，创造标签用 `FabricItemGroup.builder()` + `RegistryKey<ItemGroup>`（`MacawsBridges.java:24-33`）

## 4. 核心系统
1. **连接状态驱动的桥体形状**（`objects/Bridge_Block.java`）：核心是一个 16 值枚举 `ConnectionStatus`（`BASE / MIDDLE_NS / MIDDLE_EW / CORNER_* / SIDE_* / END_*_TOGGLED / BASE_TOGGLED`，`:201-217`），`getConnectionStatus(north,east,south,west)` 用四邻布尔做**穷举查表**（`:165-199`），由 `StairState()` 在 `onPlace`/`getStateForPlacement`/`updateShape` 三处重算。形状用成对 `VoxelShape` 数组：`SIDE_0/90/180/270`、`CORNER_*`、`MIDDLE_*` 走 `getShape`，另一套 `COLLISION_*`（高度 2→25）走 `getCollisionShape`，**碰撞箱比外观高**，玩家因此能"踩在栏杆上"（`:35-63, 71-153`）
2. **手动形态锁定**：所有 `*_TOGGLED` 状态在 `updateShape` 里直接 `return state` 短路（`:311-317`），使玩家用钳子掰出的造型不会被邻居方块更新覆盖
3. **钳子/剪刀交互状态机**（`Bridge_Block.use`，`:219-294`）：`item == ItemInit.PLIERS.get() || item == Items.SHEARS` 时按固定环路切换 `SIDE→BASE_TOGGLED→CORNER_SW→…→END_W_TOGGLED→BASE_TOGGLED`；同一分支还处理"手持同类方块的物品右键 → 在面朝方向放置下一段桥"（`level.setBlock(placePos, defaultBlockState(), 3)`，非创造模式 `itemstack.shrink(1)`），并提供 `getStateForPlacement` 返回 `null` 来禁止在桥面正上方叠放（`:320-332`）
4. **索桥**（`Bridge_Block_Rope.java`，442 行，最大类）：在 24 值枚举基础上再加第二属性 `FACING_TD`（`DirectionProperty.create("facing", NORTH/EAST/SOUTH/WEST)`，`:74`）表示吊绳朝向，`StairState` 里两个属性一起算（`:237`）；`Bridge_Stairs` 则是 4 值枚举 `BASE/DOUBLE/LEFT/RIGHT` + `FACING`，用水平朝向枚举判定 double/left/right（`:120, 192-207`）
5. **桥墩**（`objects/Bridge_Support.java`）：唯一实现 `SimpleWaterloggedBlock` 的类，`WATERLOGGED` 在 `getStateForPlacement` 里按流体判定（`:42-47`）；`getOcclusionShape` 与 `getRenderShape=MODEL`、`onBroken` 触发 `level.levelEvent(1029, pos, 0)`，另暴露 `placeAt(Level, BlockPos)` 供世界生成/其他方块调用（`:54-56`）
6. **附加灯具**（`objects/items/Bridge_Torch.java` 195 行 + `Bridge_Lantern extends Bridge_Torch`）：`HorizontalDirectionalBlock` + `LIGHTSTATE(bridge/stair)` 由**下方方块类型**决定（`LightState.byState(BlockState)`，`:181-187`），`getLightEmission` 返回构造传入的 `lightValue`（注册时 15，`BlockInit.java:149-150`），`getCollisionShape` 返回空 → 可穿过；`neighborChanged` 在下方被破坏时 `destroyBlock`，`getStateForPlacement` 在下方式样为 `BASE/BASE_TOGGLED` 时返回 `null` 阻止放置在桥端

## 5. 网络 / 数据驱动 / 配置 / datagen
全部为"无"：无 `SimpleChannel`/自定义包、无 `ForgeConfigSpec`、无数据驱动 loader、无 datagen；方块状态枚举全部手写在 Java 里，行为全靠 `VoxelShape` + `BlockState` 属性。客户端渲染层是唯一"平台差异"：Forge 用 `ClientEventBusSubscriber`（`FMLClientSetupEvent` + `RenderTypeLookup.setRenderLayer`，1.20.1 Forge 侧），Fabric 用 `ClientModInitializer` + `BlockRenderLayerMap.INSTANCE.putBlock(block, RenderLayer.getCutout())`（`1.20.1  Fabric/util/ClientEventBusSubscriber.java:7-20`）；1.20.4 目录里已无该类，应已移到资源侧（本快照无资源，未确认）。

## 6. Mixin
无：三个版本目录都不含 mixins 配置或 `@Mixin` 类。

## 7. 值得学的 5 条具体做法
1. **"四邻布尔 → 枚举查表"处理连接形状**：`Bridge_Block.getConnectionStatus(boolean,boolean,boolean,boolean)` 一个纯函数穷举 16 种情况（`Bridge_Block.java:165-199`），比逐方向 `canConnect` 更易调试；配套 `StringRepresentable` 枚举让 blockstate JSON 直接可读。
2. **外观形状与碰撞形状分离**：`getShape` 用矮模型、`getCollisionShape` 用高的 `COLLISION_SIDE_*`（`Bridge_Block.java:52-63`），实现"栏杆可站人"而不改模型。
3. **邻居更新短路保护手工状态**：`updateShape` 对 `*_TOGGLED` 状态提前返回（`Bridge_Block.java:312-316`），这是所有"工具改形方块"都需要的模式。
4. **一个方块类同时是"物品右键延伸器"**：在 `use()` 里判断 `itemstack.getItem() instanceof BlockItem && blockItem.getBlock() == this`（`Bridge_Block.java:278-292`），无需额外物品即可让玩家连续铺设同类方块。
5. **工具物品与交互解耦**：`Plier`只是一个带 tooltip 的普通 `Item`（`objects/items/Plier.java`），交互逻辑写在方块里并额外接受原版 `Items.SHEARS`，玩家不装 mod 物品也能操作。
6. 补充：**双平台共用同一份方块逻辑**，差异只集中在注册（DeferredRegister vs `Registry.register`）与渲染层（`RenderTypeLookup` vs `BlockRenderLayerMap`），是"1 个源码两个加载器"最省力的组织方式；tooltip 复用同一套 `util` 类（`BlockItemWithInfo`/`LightInfo`/`FuelBlockItemWithInfo`）分别给桥、灯、可燃方块换描述 key。

## 8. 是否库/前置
非库、非前置：内容 mod，无对外 API 包与扩展点接口。可复用资产是三类 UI/行为基类 —— `util/BlockItemWithInfo`（tooltip 基类）、`util/FuelItemBlock`/`FuelBlockItemWithInfo`（`IForgeItem.getBurnTime` 返回 300）、`objects/Bridge_Support`（提供 `placeAt` 供外部世界生成调用）。
