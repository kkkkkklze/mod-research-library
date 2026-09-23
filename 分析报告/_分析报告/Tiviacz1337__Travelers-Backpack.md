# Tiviacz1337/Travelers-Backpack 源码分析报告

本地路径：`...\_bulk\Tiviacz1337__Travelers-Backpack`（下文路径相对仓库根）

## 1. 基本信息

Traveler's Backpack / mod_id `travelersbackpack` / 作者 Tiviacz1337 / 版本 9.1.57 / 许可证 LGPL（`gradle.properties:9-11`）。
目标：Minecraft `1.20.1`、**Forge 47.4.1**（`gradle.properties:22-25`），Java 17，`[46,)` 之类版本区间写在 `src/main/resources/META-INF/mods.toml`。
Gradle：`net.minecraftforge.gradle [6.0,6.2)` + Parchment librarian + `org.spongepowered.mixin` 0.7.+（`build.gradle:1-8`）。
依赖（全部 compileOnly/运行时可选，`build.gradle:97-160`）：Curios、Accessories、Forge Config Screens、Balm、Crafting Tweaks、TrashSlot、Comforts、Corpse、Gravestone、Tough as Nails、Tetra、Polymorph、Create、GregTech CEu、spark、JEI/EMI/REI 等，**它不依赖任何前置 API，只被这些 mod 依赖**。
注意：`handlers/NeoForgeEventHandler.java` 文件名带 NeoForge，但全仓库 117 个文件用 `net.minecraftforge`、0 个用 `net.neoforged`——遗留命名。

## 2. 规模与包结构

227 个 `.java` / 25642 行。包：`inventory` 65、`client` 37、`compat` 26、`items` 17、`util` 14、`network` 11、`init` 11、`common` 8、`fluids` 6、`commands` 5、`handlers` 4、`capability` 4、`datagen` 3、`config` 3、`mixin` 2。
最大文件：`inventory/BackpackWrapper.java` 917、`common/BackpackAbilities.java` 870、`config/TravelersBackpackConfig.java` 831、`inventory/menu/BackpackBaseMenu.java` 715、`common/ServerActions.java` 627、`handlers/NeoForgeEventHandler.java` 588、`blockentity/BackpackBlockEntity.java` 560、`items/TravelersBackpackItem.java` 549。
本副本资源已被裁剪（仅 `META-INF/mods.toml`、`accesstransformer.cfg`、`data/.../tags/items/readme.txt`），故 mixin 配置 json 不在快照内。

## 3. 入口与注册

主类 `src/main/java/com/tiviacz/travelersbackpack/TravelersBackpack.java`（`@Mod("travelersbackpack")`）：注册 3 个 ModConfigSpec（SERVER/COMMON/CLIENT），把 11 个 `init/*` 的 DeferredRegister 挂到 mod 事件总线：

```java
ModItems.ITEMS.register(eventBus); ModItems.ENTITY_TYPES.register(eventBus);
ModBlocks.BLOCKS.register(eventBus); ModBlockEntityTypes.BLOCK_ENTITY_TYPES.register(eventBus);
ModMenuTypes.MENU_TYPES.register(eventBus); ModRecipeSerializers.SERIALIZERS.register(eventBus);
ModFluids.FLUID_TYPES.register(eventBus); ModFluids.FLUIDS.register(eventBus);
ModCreativeTabs.CREATIVE_MODE_TABS.register(eventBus); ModLootModifiers.LOOT_MODIFIER_SERIALIZERS.register(eventBus);
```

构造器里用 `ModList.get().isLoaded(...)` 缓存 16 个兼容 mod 布尔（`curiosLoaded` 等）；`setup(FMLCommonSetupEvent)` 内 `enqueueWork` 依次注册网络通道、发射器行为、`EffectFluidRegistry.initEffects()`、炼药锅交互、`ActionTypeTrigger.register()`。还含旧配置迁移：`readOldCommonConfig()` 读 `travelersbackpack-common.toml` 后在 `defaultconfigs/` 写 `travelersbackpack-server.toml`（`TravelersBackpack.java:readOldCommonConfig/generateDefaultConfig`）。

## 4. 核心系统

1. **背包数据模型** `inventory/BackpackWrapper.java`：包一份 `ItemStack` + 三个 `ItemStackHandler`（`inventory/upgrades/tools`），字段 `screenID`（`Reference.WEARABLE_SCREEN_ID`/`BLOCK_ENTITY_SCREEN_ID`）、`dataLoad = {1,1,1}` 分段懒加载、`saveHandler`/`abilityHandler` 回调、`playersUsing` 列表、`DUMMY` 静态实例；槽位数由 `ModDataHelper.STORAGE_SLOTS/UPGRADE_SLOTS/TOOL_SLOTS` + `Tiers` 决定。
2. **能力/装备**：`capability/ITravelersBackpack`（`@AutoRegisterCapability`）+ `TravelersBackpackWearable`（实现 `INBTSerializable<CompoundTag>`，`equipBackpack/updateBackpack/applyComponents`，每次变更调 `synchronise()` 发 `ClientboundSyncCapabilityPacket`）；`CapabilityUtils` 用 `LOAD_ALL/TOOLS_ONLY` 等 int[] 掩码控制取用范围。
3. **升级系统**：`inventory/UpgradeManager.java` 用 `BiMap<Integer slot, Optional<UpgradeBase<?>>> mappedUpgrades` 管理，`canAddUpgrade` 按 `upgradeItem.getUpgradeClass()` 去重；`inventory/upgrades/` 下按功能分包（crafting/smelting/tanks/magnet/pickup/refill/jukebox/feeding），统一实现 `IUpgrade/IEnable/ITickableUpgrade/FilterUpgradeBase`，每个升级配一个 `*Widget` 做 GUI，另有 `upgradesTracker` 记录"已同步给客户端"的副本。
4. **背包能力/事件**：`common/BackpackAbilities.java`（`ABILITIES` 单例 + `checkBackpack(player, item)`，用 `ArrayListMultimap` 把能力挂到背包物品），效果来自 `config/BackpackEffect.java` 与 `config/Cooldown.java`（配置驱动）；僵尸/苦力怕等行为在 `handlers/NeoForgeEventHandler.java` 里用 Forge 事件实现。
5. **动作分发**：`common/ServerActions.java` 提供静态方法（`swapTool` 换工具、睡袋、软管/炼药锅液体、`ContainerSorter` 排序、插件检查后 `player.containerMenu.broadcastChanges()`），由 `ServerboundActionTagPacket` 等包按 tag 字符串调用——客户端按钮 → 服务端方法的一层间接。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`init/ModNetwork.java` 用 Forge `SimpleChannel`（`NetworkRegistry.ChannelBuilder`，protocol 版本 `travelersbackpack:1`），12 条消息固定 id 0-11，逐条 `messageBuilder(...).decoder().encoder().consumerNetworkThread/consumerMainThread().add()`；C2S 走 `consumerMainThread`（`ServerboundSlotPacket`、`ServerboundActionTagPacket`、`ServerboundFilterSettingsPacket`、`ServerboundFilterTagsPacket`、`ServerboundRetrieveBackpackPacket`），S2C 有 `ClientboundSyncCapabilityPacket`、`ClientboundSyncItemStackPacket`、`ClientboundSyncComponentsPacket`（后两者在网络线程处理）与 `SupporterBadgePacket` 双向。
- 配置：`config/TravelersBackpackConfig.java`（831 行）三套 spec；`ModEventHandler` 监听 `ModConfigEvent.Loading/Reloading` 调 `TravelersBackpackConfig.SERVER.reload()` 重建缓存。
- datagen：`datagen/ModRecipeProvider`、`ModLootTableProvider`、`ModBlockLootTables`，由 `handlers/ModEventHandler.onGatherData`（`GatherDataEvent`）注册，产物写到 `src/generated/resources`。
- 数据驱动：无 JSON 数据驱动系统；合成配方为代码注册的 `common/recipes/ShapedBackpackRecipe`；标签仅 `ModTags`。

## 6. Mixin

仅 2 个：`mixin/PlayerMixin.java`（`@Mixin(Player.class)`，`@Shadow @Final private Abilities abilities`，`@Inject(method="getFlyingSpeed", at=@At("RETURN"), cancellable=true)` 里判断 `BackpackAbilities.ABILITIES.checkBackpack(player, ModItems.FOX_TRAVELERS_BACKPACK.get())` 后改滑翔速度）与 `mixin/MinecraftMixin.java`。
配置文件名由 `build.gradle` 的 `mixin { config "mixins.${mod_id}.json" }` + `MixinConfigs` manifest 决定（即 `mixins.travelersbackpack.json`），**该 json 不在本快照的资源裁剪范围内**，无法读其内容（未确认）。

## 7. 值得学的 5 条做法

1. 一个 `Wrapper` 同时服务"穿戴"与"方块实体"两种形态：`BackpackWrapper(screenID, dataLoad)`（`inventory/BackpackWrapper.java`）用同一套容器代码支撑物品/方块两条路径。
2. 兼容 mod 全部编译期 compileOnly + 运行期 `isLoaded` 布尔开关（`TravelersBackpack.java` 构造器、`compat/` 26 个文件），零硬依赖。
3. 升级用 `BiMap<slot, Optional<UpgradeBase>>` + `upgradesTracker` 副本（`inventory/UpgradeManager.java`）：槽↔逻辑双向可查，且显式区分"本地状态"与"已同步状态"。
4. 客户端按钮统一走一个 tag 包再由 `common/ServerActions` 静态方法分发（`network/ServerboundActionTagPacket`、`common/ServerActions.java`），新增交互不必加新包。
5. 用 `readOldCommonConfig()` 做配置 schema 迁移（读旧 toml → 写 `defaultconfigs/`），避免升级后玩家配置失效。

## 8. API

仅 `src/main/java/com/tiviacz/travelersbackpack/api/fluids/EffectFluid.java` 一个对外包（自定义"药水效果流体"）；装备能力接口 `capability/ITravelersBackpack` 未标注 @ApiStatus，未确认是否对外承诺稳定。
