# ausmez/create-storage-neo-forge 源码分析报告

## 1. 基本信息

- Mod 名：Create: Storage（NeoForge 移植版）；mod_id：`fxntstorage`
- 作者：FoxyNoTail（原 Fabric 作者）、ausmez（NeoForge）；版本 1.3.4
- 目标：MC 1.21.1 / NeoForge 21.1.248（`neo_version_range=[21.1.181,）`），Java 21
- 构建：Gradle + `net.neoforged.moddev` 2.0.142；`src/main/templates/META-INF/neoforge.mods.toml` 做 ${} 变量替换
- 许可证：GNU GPL 3.0（`gradle.properties:mod_license`）
- 依赖（`gradle.properties` + `build.gradle:116-181`）：**Create 6.0.10-280（required，`[6.0.7,6.1.0)`）**、Ponder 1.0.82、Flywheel 1.0.6（api compileOnly + runtimeOnly）、Registrate MC1.21-1.3.0+67、Curios 9.5.1（optional，仅 `:api` compileOnly）；可选兼容 Construction Sticks、Every Compat/Selene、Sable（Create Aeronautics）、vanillabackport；JEI/EMI/REI 均为 compileOnly，通过 `#ifdef`-风格 Gradle property（`recipe_viewer=EMI`）切换 runtime。

## 2. 源码规模与包结构

- 297 个 `.java`，36771 行（`find . -name '*.java' -exec wc -l {} +`）
- 主包 `net.fxnt.fxntstorage` 下：`backpack` 79、`compat` 30、`simple_storage` 25、`container` 16、`reserve_storage` 15、`datagen` 14、`ponder` 13、`init` 20、`storage_network` 3、`network/packet` 30 个包类、`mixin` 14
- 最大文件：`backpack/client/menu/BackpackMenu.java`(1151)、`backpack/client/menu/BackpackScreen.java`(891)、`simple_storage/SimpleStorageBoxEntity.java`(876)、`backpack/upgrade/jetpack/JetpackHandler.java`(797)、`simple_storage/mounted/SimpleStorageBoxMountedStorage.java`(708)、`backpack/upgrade/workshop/WorkshopUpgrade.java`(674)、`backpack/BackpackEntity.java`(599)、`init/ModBlocks.java`(584)

## 3. 入口与注册

主类 `src/main/java/net/fxnt/fxntstorage/FXNTStorage.java:75`，用 **CreateRegistrate** 统一注册：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MOD_ID)
        .defaultCreativeTab((ResourceKey<CreativeModeTab>) null)
        .addDataGenerator(ProviderType.LANG, ModLangProvider::provide);
```

构造函数（同文件:89-124）顺序：注册 CLIENT/SERVER 配置 → 事件监听（common setup / capabilities / PacketHandler）→ `ModBlocks/ModBlockEntities/ModItems/ModTabs/ModEffects/ModMenuTypes/ModDataComponents/ModLootConditionTypes/ModLootFunctionTypes/ModAttachmentTypes.register()` → `UpgradeRegistry.register()` → `REGISTRATE.registerEventListeners(bus)` → 条件式加载 Curios/Construction Stick/Every Compat 兼容。Capability 注册集中在 `FXNTStorage.java:143-160`（8 个 BlockEntity 的 `ItemHandler.BLOCK` + 5 种背包的 `ItemHandler.ITEM`）。客户端事件放内部类 `@EventBusSubscriber(Dist.CLIENT) ClientModEvents`（:175-297）。

## 4. 核心系统

**（1）背包升级系统（最值得学）** — `backpack/upgrade/`
`IUpgrade.java` 定义 14+ 个 default 钩子（`tick / onInstalled / onRemoved / onPlayerTouchItem / onLivingFall / onAttackEntity / onLeftClickBlock / onBlockBreak / onPickBlock / onBackpackEquipped / createPanel / createSlots / getSettings / getDefaultSettings`）；`UpgradeRegistry.java` 用 `EnumMap<UpgradeType, IUpgrade>` + `initialized` 防重复注册，并以 `getDefaultSetting(UpgradeDataSync.Field)` 反查默认开关；14 个升级各占一子包（`jetpack/`、`oremining/`、`jukebox/` 等），`UpgradeContext` 传递玩家/背包/槽位上下文。

**（2）Create 动态结构（Contraption）物品存储** — `init/ModMountedStorageTypes.java`
用 Registrate 的 `REGISTRATE.mountedItemStorage(name, supplier)` 注册 4 种 `MountedItemStorageType`（储物箱/简易箱/预留箱/背包），配合各类的 `*MountedStorageType` + `*MovementBehaviour` + `*MountedMenu/Screen` 四件套，接入 Create 的 contraption mounted storage API。

**（3）储物网络** — `storage_network/StorageNetwork.java`(432)
`StorageControllerEntity` 持有一个 `StorageNetwork`；`tick()` 中先 `checkBoxes()` 再按 `ConfigManager.ServerConfig.SIMPLE_STORAGE_NETWORK_UPDATE_TIME` 节流调用 `refreshStorageNetwork()`；用 `Set<BlockPos> components` 做连通块 diff，移除的组件调 `StorageInterfaceEntity.forgetController()`；对外暴露 `IItemHandlerModifiable NetworkItemHandler`；`SlotMapping(int boxIndex, int tierSlot)` record 做扁平槽位映射；`networkVersion` 用于客户端 `StorageNetworkSyncPacket` 增量同步。

**（4）压缩链（Compacting）** — `simple_storage/CompactingChain.java / CompactingItemHandler.java / CompactingRecipeHelper.java / CompactingWheelScreen.java / SimpleStorageBoxCompactingSlot.java`
按配方把物品自动压/解压（9→1 或 1→9），客户端在 `RecipesUpdatedEvent` 时 `CompactingRecipeHelper.rebuild(recipeManager, registryAccess)`（`FXNTStorage.java:211-216`），滚动切换层级走 `CompactingTierScrollPacket`。

**（5）配置同步** — `config/ConfigManager.java`(476)
内部类 `ClientConfig/ServerConfig` 各持 `ModConfigSpec`；`record SyncableConfigEntry(String key, ModConfigSpec.ConfigValue<?> value)` 带 `writeToNBT(CompoundTag)`（switch 模式匹配 Integer/Double/Float/Boolean/String/Enum/List），把客户端设置写进玩家持久数据 `fxntstorageSettings`（`CURRENT_DATA_VERSION = 1`，含 `migrateClientConfigFile()` 迁移）；`SYNCED_CLIENT_SETTINGS` 列表 + `SyncClientSettingsPacket` 做 C→S 同步；`Configured` 未装时注册 `ConfigurationScreen` 作为 config 界面。

**（6）Ponder 教程** — `ponder/CsPonderPlugin.java` 在 `FMLClientSetupEvent` 注册；9 个 `*Scenes.java` 覆盖每个方块，并自定义 `CsInputWindowElement / CsOutlineInstruction` 两个 Ponder 元素。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/PacketHandler.java` 单类集中注册，`event.registrar("1")` 协议版本；**14 个 playToClient + 16 个 playToServer**（共 30 个 packet 类），一律 `registrar.playToX(TYPE, TYPE.STREAM_CODEC, TYPE::handle)`，无自定义通道；含 `StorageNetworkSyncPacket`、`SyncMountedStoragePacket`、`SyncDataComponentPacket`、`JetpackFuelSyncPacket` 等同步型包与 `KeyPressedPacket / PlayerInputPacket / SortInventoryPacket` 等输入型包。
- datagen：`datagen/DataGenerators.java` 注册 Block/Item TagProvider、`ModBackpackRecipeProvider`、`ModConditionalLootProvider`、`ModCuriosDataProvider`；`ModLangProvider.provide` 挂在 Registrate 的 `ProviderType.LANG`；`datagen/helper` 与 `ShapedBackpackRecipeBuilder` 做自定义 builder。
- 数据驱动：方块形状/储物箱容量的"tier"配置在 `init/ModBlocks.java`（584 行）用 Registrate builder 生成；`ModDataComponents`、`ModAttachmentTypes`、`ModLootConditionTypes/FunctionTypes`、`ModInventoryIdentifiers`、`ModUnpackers`（KubeJS/配方式解包）均在 `init/` 集中。

## 6. Mixin

配置：`src/main/resources/fxntstorage.mixins.json`（`required: true`、`compatibilityLevel: JAVA_21`、`package: net.fxnt.fxntstorage.mixin`、`injectors.defaultRequire: 1`，14 个 common + 1 个 client）。代表性：

- `mixin/PlayerMixin.java:9` — `@Mixin(Player.class)`，`@ModifyExpressionValue` 注入 `getDigSpeed` 里的 `Player.onGround()`，实现"背喷气背包未落地时挖掘减速"，并用 `ConfigManager.ServerConfig.JETPACK_MINING_PENALTY` 开关。
- `mixin/AbstractContraptionEntityMixin.java:14` — `@Mixin(AbstractContraptionEntity.class)`，`@Inject(method="handlePlayerInteraction", at=HEAD/RETURN, remap=false)`。
- `mixin/DeployerMovementBehaviourMixin.java:12` — `@Inject(method="visitNewPosition", at=HEAD/RETURN, remap=false)`（Create 类，必须 `remap=false`）。
- `mixin/InventoryMenuMixin.java:20` — `@Mixin(AbstractContainerMenu.class)`，`@Inject(method="clicked", at=HEAD, cancellable=true)` 拦截点击做背包/整理逻辑。
- `mixin/ThresholdSwitchBlockEntity.java:16`、`ItemStackMixin.java:13`、`ToolboxDisposeAllPacketMixin.java:23`（内部再套 `@Mixin(ToolboxBlockEntity.class)` 嵌套类）—— 均注入 `<clinit>` / `lambda$handle$0` 等，属"改缓存/常量"型补丁。
- 兼容 mixin：`EMIVanillaPluginMixin`（`register(Ldev/emi/emi/api/EmiRegistry;)V`）、`REIDefaultClientPluginMixin`（client 段，`registerTransferHandlers(Lme/shedaniel/rei/...)V`），因目标方法是混淆无关的 API 方法而写全描述符。

## 7. 值得学的 5 条具体做法

1. **用 `IUpgrade` 接口把 14 个背包功能收敛成钩子表**，新增功能只写一个子包 + 在 `UpgradeRegistry.register()` 加一行；`backpack/upgrade/IUpgrade.java`。适用于任何"可插拔模块/升级项"系统。
2. **Capability 只集中注册一次**，在 `registerCapabilities(RegisterCapabilitiesEvent)` 里为每个 BE/物品挂 `IItemHandler`；`FXNTStorage.java:143-160`。避免各 BE 自行实现 `ICapabilityProvider`。
3. **`record SyncableConfigEntry(key, ConfigValue<?>)` + switch 模式匹配写 NBT**，让配置项自动可选地持久化到玩家数据并同步；`config/ConfigManager.java:29-50`。适用于服务端可调参数需要下发到客户端/写入玩家存档。
4. **客户端设置同步 + 配置重载时按需重建**：`ClientModEvents.onConfigReload` 仅在"连通纹理模式"变化时调 `levelRenderer.allChanged()`，其余只发包；`FXNTStorage.java:187-203`。
5. **Contraption 挂载存储用 Create 官方 API 而非 mixin**：`REGISTRATE.mountedItemStorage(...)` + `MountedStorageType`；`init/ModMountedStorageTypes.java`。做成 Create 附属时应优先这条路。
6. （补充）`ContraptionStorageFilters` 用 `Collections.synchronizedMap(new WeakHashMap<>())` 以 contraption 为键缓存过滤表，并提供 `cleanupContraption` 防泄漏；`registry/ContraptionStorageFilters.java:13-14`。

## 8. （库/前置类 mod 专项）

非前置库，无对外 API 包；扩展点对外仅体现在 `compat/` 下的被动集成（Curios slot、EMI/REI/JEI transfer handler、Every Compat 材质、Construction Sticks、Sable）与 `ModCompats` 里的 modId 常量表 + `InterModEnqueueEvent` IMC（`inventorysorter`）。
