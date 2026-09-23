# TheCBProject/EnderStorage 源码分析报告

## 1. 基本信息

- Mod 名 EnderStorage；mod_id `enderstorage`；作者 ChickenBones / covers1624（TheCBProject）；MIT（`LICENSE.txt`、`META-INF/neoforge.mods.toml:4`）
- 目标 MC 1.21.11 / NeoForge 21.11.42，Java 21，插件 `net.neoforged.moddev` 2.0.141；版本 `1.21.11-2.14.0.<BUILD_NUMBER>`（`gradle.properties`、`build.gradle`）
- 依赖：**CodeChickenLib** `io.codechicken:CodeChickenLib:1.21.11-4.7.0.+`（implementation + `accessTransformers` + `interfaceInjectionData`，硬依赖 `[4.7.0,5.0.0)`）、JEI（`transitive false`）
- 发布工程化：`withSourcesJar/JavadocJar`、`signJar`（GPG in-memory）、`publishingMetadata` json（CurseForge/Modrinth id）、推送到 `nexus.covers1624.net`

## 2. 源码规模与包结构

67 个 `.java` / 4404 行。包（`codechicken.enderstorage`）：`manager`(6)、`client/render/{,entity,item,tile}`(4+)、`api`(4)、`tile`(3)、`block`(3)、`init`(3)、`storage`(2)、`recipe`(2)、`plugin`(2+`jei`)、`item`(2)、`client/{gui,model}`、`container`(1)、`network`(1)、`config`(1)、`misc`

最大文件：`tile/TileEnderTank.java`(257)、`manager/EnderStorageManager.java`(249)、`storage/EnderItemStorage.java`(214)、`block/BlockEnderStorage.java`(200)、`init/DataGenerators.java`(199)、`client/render/RenderCustomEndPortal.java`(178)、`recipe/ReColourRecipe.java`(175)

## 3. 入口与注册

主类 `EnderStorage.java:21` 构造器串行 init：`EnderStorageConfig.load()` → `EnderStorageModContent.init(modBus)` → `ClientInit.init`（仅客户端）→ `EnderStorageNetwork.init` → `EnderStorageManager.init()` + `registerPlugin(new EnderItemStoragePlugin()/EnderLiquidStoragePlugin())` → `NeoForge.EVENT_BUS.register(new EnderStorageManager.EnderStorageSaveHandler())` → `ServerTankSynchronizer.init` → `DataGenerators.init`。

注册全在 `init/EnderStorageModContent.java`，NeoForge `DeferredRegister`（无 Registrate）：`createBlocks/createItems` + `BLOCK_ENTITY_TYPE/DATA_COMPONENT_TYPE/MENU/RecipeSerializer`；`init()` 末尾 `modBus.addListener` 挂 `BuildCreativeModeTabContentsEvent` 与 `RegisterCapabilitiesEvent`：

```java
public static final DeferredHolder<DataComponentType<?>, DataComponentType<Frequency>> FREQUENCY_DATA_COMPONENT =
    DATA_COMPONENTS.register("frequency", () -> DataComponentType.<Frequency>builder()
        .persistent(Frequency.CODEC).networkSynchronized(Frequency.STREAM_CODEC).build());
// onRegisterCaps: Capabilities.Item.BLOCK / Capabilities.Fluid.BLOCK → tile.getItemHandler()/getFluidHandler()
```

## 4. 核心系统

**A. Frequency 作为数据组件** `api/Frequency.java`
- `record Frequency(EnumColour left/middle/right, Optional<UUID> owner, Optional<Component> ownerName)`，同时实现 `Codec`（`RecordCodecBuilder` + `UUIDUtil.CODEC.optionalFieldOf`）与 `StreamCodec`（`StreamCodec.composite` + `ByteBufCodecs.optional`）
- 物品侧用 `putComponent/getComponentOrEmpty`（`:80`）；方块实体只在 NBT 存 Frequency，其余状态由频段推导

**B. 全局存储管理器** `manager/EnderStorageManager.java`
- 按 side 分单例 `serverManager/clientManager` + `instance(boolean)` 懒加载；`Map<String, AbstractEnderStorage>`，key = `freq + ",type=" + type.name()`（`:196`）
- 增量存盘：`AbstractEnderStorage.setDirty()` → `manager.requestSave()` 入 `dirtyStorage`，只在 `LevelEvent.Save` 落盘
- 三文件轮转：`data1.dat/data2.dat/lock.dat`，`saveTo = lock ^ 1`（`:120`），成功写完才翻 lock；注释自陈"looks like cancer, but actually quite smart"

**C. 存储类型插件 API** `api/EnderStoragePlugin.java`、`api/StorageType.java`、`plugin/*`
- `StorageType<T>(String name)` 作类型键；`EnderStoragePlugin<T>` 只需 `createEnderStorage`、`identifier`、`sendClientInfo(player, list)`（登录/换维度补发）
- `storage/EnderItemStorage` 实现 `Container`，`sizes={9,27,54}` 随配置 `alignSize()` 扩缩容；`storage/EnderLiquidStorage` 用新 transfer API `FluidStacksResourceHandler`（`onContentsChanged → setDirty`），容量 16B

**D. 网络（CCL StreamNetworkChannel）** `network/EnderStorageNetwork.java`
- 不用 `PayloadRegistrar`：5 个 `playToClient`（tile_update/client_open/tank_sync/liquid_sync/pressure_sync）+ 1 个 `playToServer`（tank_visibility），handler 直接读 `RegistryFriendlyByteBuf`
- 菜单数据随包附带：`openContainer()` 里 `packet.cc$writeWithRegistryCodec(Frequency.STREAM_CODEC, freq)` + `writeByte(size)`（`storage/EnderItemStorage.java:179`）

**E. 液体同步 + 客户端平滑** `manager/{ServerTankSynchronizer,ClientTankSynchronizer,PlayerItemTankCache,TankState}.java`
- 可见性驱动：客户端每帧 `newFrame()` 收集被渲染的 tank 频段，与上一帧求差集，用 `TANK_VISIBILITY` 一次性上报 new/old（`PlayerItemTankCache.Client.update`）
- 服务端节流：`TankState.Server.update()` 仅在流体种类/组件变化、液位差 > 250 mB、或服务端已空客户端有残留时发 `tank_sync`
- 客户端 `TankState.Client` 用 `MathHelper.approachExpI/retreatExpI(..., 0.1)` 指数逼近显示值

**F. 数据驱动配方** `recipe/{CreateRecipe,ReColourRecipe}.java`
- `CreateRecipe extends ShapedRecipe` 重写 `assemble()`：扫网格找唯一羊毛 → `EnumColour.fromWoolStack` 定色 → `new Frequency(c,c,c).putComponent(...)`
- `ReColourRecipe implements CraftingRecipe`，`matches()` 自解析箱子/染料位置
- 各有 `RecipeSerializer`（`MapCodec` + `StreamCodec.composite`），注册在 `RECIPE_SERIALIZERS`

## 5. 网络 / 数据驱动 / 配置 / datagen

- 配置：不用 `ModConfigSpec`，用 CCL `ConfigFile` 写 `./config/EnderStorage.cfg`（`config/EnderStorageConfig.java:39`），`CrashLock` 防重复 init；`personalItem` 非法时回退 `Items.DIAMOND` 并 `reset()+save()` 写回
- datagen：`init/DataGenerators.java` 在 `GatherDataEvent.Client` 下注册 `Models`（`createParticleOnlyBlock` + `ItemModelUtils.specialModel/conditional/select/composite`，自定义 `BagOwnedModelCondition/BagOpenModelCondition/BagFrequencySelectProperty`）、`BlockTagGen`（`MINEABLE_WITH_PICKAXE`）、`Recipes`（`customShaped(...CreateRecipe::new)`、`special(id, ReColourRecipe)`）
- `sourceSets.main.resources.srcDirs += "src/main/generated"`，data run 输出到 `src/main/generated`

## 6. Mixin

**无**（无 `*.mixins.json`）；仅有 `src/main/resources/META-INF/accesstransformer.cfg`，通过 `neoForge { accessTransformers { publish ... } }` 声明

## 7. 值得学的 5 条做法

1. **把"共享键"做成数据组件**：`Frequency` 一套 `Codec`/`StreamCodec` 物品、方块实体、网络三处复用；`api/Frequency.java`。
2. **lock 文件轮转双备份存盘**：写 data → 翻 lock，崩溃后仍可读旧档；`manager/EnderStorageManager.java:112`。
3. **可见性驱动的同步**：客户端只上报"我在看这个频段"，服务端只给关注者发同步包，避免全量广播；`manager/PlayerItemTankCache.java:57`。
4. **`StorageType<T>` + 插件接口做可扩展存储种类**：新增能量/气体只需实现 `EnderStoragePlugin`；`api/EnderStoragePlugin.java`、`plugin/EnderItemStoragePlugin.java`。
5. **客户端指数插值而非直接置值**：`approachExpI/retreatExpI(..., 0.1)` 平滑远端液位；`manager/TankState.java:75`。

## 8. 公开 API / 对外接入

- `codechicken.enderstorage.api`（有 `package-info.java` + `@NonNullApi`）：`Frequency`、`AbstractEnderStorage`、`EnderStoragePlugin<T>`、`StorageType<T>`
- 接入：实现 `EnderStoragePlugin<T>` 并在构造期 `EnderStorageManager.registerPlugin(plugin)`；实例经 `EnderStorageManager.instance(client).getStorage(freq, TYPE)` 获取
- 集成参考：`plugin/jei/*`（`ESCraftingRecipeWrapper`）、`init/ClientInit.java`
