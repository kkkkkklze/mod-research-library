# SophisticatedCore 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Sophisticated Core / `sophisticatedcore`（v1.5.1）
- 作者：P3pp3rF1y；许可证：All Rights Reserved（`gradle.properties` 的 `mod_license`）
- 目标：Minecraft 1.21.1、NeoForge 21.1.229（`neo_version_range=[21.1.229,)`）、`modLoader="javafml"`、`loaderVersion="${loader_version_range}"`（即 `[4,)`）——见 `src/main/templates/META-INF/neoforge.mods.toml:1-2`
- Gradle：`java-library` + `net.neoforged.moddev` 1.0.14 + curseforgegradle 1.1.15 + minotaur + spotless 7.0.4 + openrewrite（`build.gradle:1-10`）
- 依赖（`build.gradle:171-231`）：`implementation net.p3pp3rf1y:reliquary`（同类为 `findProject(':Reliquary')` 分支）；`compileOnly/localRuntime`：JEI、EMI、REI、Curios、Balm、CraftingTweaks、ItemBorders、Iceberg、Prism、Chipped、ResourcefulLib、Athena、Sawmill、MoonlightLib、TrashSlot、**Create 6.0.7（transitive=false）**、FTB Chunks/Library、Accessories、OpenPartiesAndClaims；测试用 JUnit 5 / Mockito。它就是 Sophisticated Storage / Backpacks 的 API 前置。
- 发布：GitHub Packages（`github_package_url`）+ CurseForge 618298 / Modrinth `nmoqTijg`

## 2. 源码规模与包结构

实测：`.java` 603 个、共 52538 行（含 `src/test`）。`src/main` 各包（递归文件数/行数）：

| 包 | 文件/行 | 包 | 文件/行 |
|---|---|---|---|
| upgrades | 189 / 14906 | compat | 131 / 7897 |
| client | 55 / 6681 | util | 35 / 3660 |
| settings | 31 / 2980 | linkedstorage | 28 / 1346 |
| common | 22 / 3694 | inventory | 18 / 2442 |
| network | 16 / 734 | api | 13 / 505 |
| crafting | 12 / 1000 | init | 8 / 491 |
| renderdata | 7 / 661 | controller | 5 / 1365 |
| mixin | 6 / 140 | data | 4 / 93 |

最大文件：`common/gui/StorageContainerMenuBase.java`(2037)、`client/gui/StorageScreenBase.java`(1505)、`controller/ControllerBlockEntityBase.java`(1112)、`inventory/InventoryHandler.java`(606)、`util/RecipeHelper.java`(593)、`upgrades/tank/TankUpgradeWrapper.java`(583)、`compat/craftingtweaks/CraftingUpgradeTweaksProvider.java`(564)。

## 3. 入口与注册

`src/main/java/net/p3pp3rf1y/sophisticatedcore/SophisticatedCore.java:34` 为 `@Mod(SophisticatedCore.MOD_ID)` 主类（构造签名 `(IEventBus modBus, Dist dist, ModContainer container)`）：注册 COMMON/CLIENT 配置、未装 Configured 时挂 `IConfigScreenFactory`、`ModCompat.register()`、`ModCoreDataComponents`/`ModItems` 注册、`DataGenerators::gatherData`；NeoForge 总线监听 `LevelEvent.Load`（`RecipeHelper.setLevel`）、`ServerStarted/Stopped`（`StorageWrapperRepository.clearCache()`）、`AddReloadListenerEvent`（`DatapackSettingsTemplateManager.Loader.INSTANCE`）。

```java
networkProtocolVersion = container.getModInfo().getVersion().toString(); // :43
container.registerConfig(ModConfig.Type.COMMON, Config.COMMON_SPEC);
modBus.addListener((FMLConstructModEvent event) -> construct(event, modBus));
modBus.addListener(SophisticatedCore::setup);          // FMLCommonSetupEvent
modBus.addListener(DataGenerators::gatherData);
```

注册框架：全部用 NeoForge `DeferredRegister`（无 Registrate）。`init/ModItems.java:19-38` 注册 `ITEMS`/`CREATIVE_MODE_TABS`（`DeferredHolder<Item, EnderLinkerItem> ENDER_LINKER`）；`init/ModRecipes.java:24-26` 注册 `RECIPE_SERIALIZERS` 与 `CONDITION_CODECS`（NeoForge 配方条件）；`init/ModFluids`、`init/ModCoreDataComponents`、`init/ModPayloads` 同构；每个 init 类暴露 `register(IEventBus)`。

## 4. 核心系统

**(a) 可组合升级框架**（`upgrades/UpgradeHandler.java`、`UpgradeType.java`、`IUpgradeItem.java`、`IUpgradeWrapper.java`）
- `UpgradeHandler extends ItemStackHandler`，NBT 键 `UPGRADE_INVENTORY_TAG="upgradeInventory"`；维护 `slotWrappers`(LinkedHashMap) 与按 `UpgradeType` 分组的 `typeWrappers`，`registerUpgradeDefaultsHandler(Class, Consumer)` 支持按类注入默认值。
- 升级物品 == `IUpgradeItem<T>`：`getType()` 返回 `UpgradeType<T>`（内部 `IFactory<T>.create(storageWrapper, upgrade, upgradeSaveHandler)`），把「物品→包装器」的构造集中一处。
- 槽位规则全部写成接口默认方法：`canAddUpgradeTo` 依次做 `checkUpgradePerStorageTypeLimit`（`getUpgradesPerStorage`/`getUpgradesInGroupPerStorage`/`UpgradeGroup`）、`checkForConflictingUpgrades`（`record UpgradeConflictDefinition(Predicate<Item> isConflictingItem, int maxConflictingAllowed, ...)`）、`checkThisForConflictsWithExistingUpgrades` → 统一返回 `UpgradeSlotChangeResult`，服务端与 UI 共用同一套校验。
- 每个升级一套 4 类结构：`*UpgradeItem` + `*UpgradeWrapper` + `*UpgradeContainer`(设置界面逻辑) + `*UpgradeTab`(GUI)，见 `upgrades/cooking`、`upgrades/magnet`、`upgrades/tank`。

**(b) 存储包装与库存句柄**（`api/IStorageWrapper.java`、`inventory/InventoryHandler.java`、`inventory/StorageWrapperRepository.java`）
- `IStorageWrapper` 统一暴露 4 件套：`getInventoryHandler()`、`getInventoryForInputOutput()`、`getUpgradeHandler()`、`getSettingsHandler()`，并声明 NBT 键 `SETTINGS_TAG="settings"`。
- `InventoryHandler` 抽象基类实现 `ITrackedContentsItemHandler` 与 `IInsertBlockOverride`，含 `getBaseSlotLimit`/`getBaseStackLimit`/`getStackLimit`、`ISlotTracker` 变更追踪、`InventoryPartitioner` + `InventoryPartRegistry.registerFactory`（升级可占用库存列/组合存储空间）。
- `StorageWrapperRepository` 用 Guava `Cache`（`expireAfterAccess(10, MINUTES)`）做 ItemStack 键与 UUID 键双缓存 + `AtomicLong wrapperCacheChangeCounter` 失效计数 + `migrateToUuid`（物品→方块化存储迁移）。

**(c) 设置与数据包模板**（`settings/`）
`SettingsHandler`/`SettingsManager`/`ISettingsCategory` 组装分类（main、memory、nosort、itemdisplay）；`DatapackSettingsTemplateManager` 是 `SimplePreparableReloadListener`，读数据包目录 `sophisticated_settingstemplates`，把 NBT `CompoundTag` 存成命名模板（`putTemplate` 自动把下划线转空格并首字母大写），模板由 `SettingsTemplateStorage`（SavedData，名 `sophisticatedcore_settings_templates`）持久化，通过 `SyncDatapackSettingsTemplatePayload` 下发客户端。

**(d) 渲染数据与校验器**（`renderdata/`）
`RenderInfo` + `UpgradeRenderDataType` + `UpgradeRenderDataValidatorRegistry`（静态注册 `CookingUpgradeRenderDataValidator`、`JukeboxUpgradeRenderDataValidator`），配合 `api/IUpgradeRenderer`、`api/IUpgradeRenderDataValidator` 让每个升级自己定义「客户端显示什么」和「服务端信任哪些数据」。

**(e) linkedstorage（1.5.x 新增，`linkedstorage/` 28 文件）**
`LinkedStorageService`/`LinkedStorageGroupManager`/`LinkedStorageGroupsSavedData` + `ILinkedStorageEndpointAdapter`/`ILinkedStorageHostFactory` + `EnderLinkerItem`（`ModItems.ENDER_LINKER`），把「物品内存储」与「方块存储」通过链接组打通，扩展点 `LinkedStorageHostFactories.register(id, factory)`、`LinkedStorageEndpointAdapters.register(...)`（见 `SophisticatedBackpacks.java` 的调用）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/` 16 个 payload，集中在 `init/ModPayloads.registerPayloads(RegisterPayloadHandlersEvent)`，`PayloadRegistrar registrar = event.registrar(MOD_ID).versioned(getNetworkProtocolVersion())`，逐个 `registrar.playToServer/playToClient(TYPE, STREAM_CODEC, ::handlePayload)`。协议版本直接取 mod 版本号 → 版本不一致自动断连。
- 数据驱动：设置模板数据包（`sophisticated_settingstemplates`）；`ModRecipes` 向 `NeoForgeRegistries.Keys.CONDITION_CODECS` 注册 `MapCodec<? extends ICondition>` 自定义配方条件。
- 配置：`Config.COMMON_SPEC` / `Config.CLIENT_SPEC` 用 NeoForge `container.registerConfig`；`Config.COMMON.initListeners(modBus)` 监听配置重载；`ConfigurationScreen::new` 作为内置配置界面。
- datagen：`data/DataGenerators.gatherData` → `SCFluidTagsProvider`、`SCRecipeProvider`（规模很小，4 文件）。

## 6. Mixin

- 主配置 `src/main/resources/sophisticatedcore.mixins.json`（`required: true`，`package net.p3pp3rf1y.sophisticatedcore.mixin`，`JAVA_17`）：`mixins`= `MixinAllay`、`MixinVanillaInventoryCodeHooks`；`client`= `MixinParrot`。
- `MixinAllay`：`@Mixin(Allay.class)`，`@Inject(method="aiStep", at=@At("TAIL"))`、`@Inject(method="shouldStopDancing", at=@At("HEAD"), cancellable=true)`（唱机升级时让悦灵跳舞）。
- `MixinParrot`（client）：`@Inject(method="aiStep", at=@At("TAIL"))`。
- `MixinVanillaInventoryCodeHooks`：`@Inject(method="isFull", at=@At("HEAD"), cancellable=true)`（让 SC 存储参与漏斗判定）。
- 兼容专用配置 `sophisticatedcore.create.mixins.json`：`mixin.create.MixinAbstractContraptionEntity`（Create 动态结构携带存储）。

## 7. 值得学的 5 条具体做法

1. **升级 = Item/Wrapper/Container/Tab 四件套 + 接口默认方法承载规则**：槽位上限、冲突、组限制都写在 `IUpgradeItem` 默认方法里，菜单/GUI/服务端共用一套校验，新增升级只需实现接口。`upgrades/IUpgradeItem.java`，适用任何「可插拔增强件」系统。
2. **wrapper 缓存用 Guava Cache + 变更计数器**：`CacheBuilder.newBuilder().expireAfterAccess(10, MINUTES)` + `AtomicLong wrapperCacheChangeCounter` 做 UI/网络缓存的失效判断。`inventory/StorageWrapperRepository.java:17-19`。
3. **网络协议版本 = mod 版本**：`PayloadRegistrar.versioned(container.getModInfo().getVersion().toString())`，省去手工维护协议号。`SophisticatedCore.java:43`、`init/ModPayloads.java:15`。
4. **兼容层完全隔离在 `compat/` + 惰性注册**：`init/ModCompat.java:29-45` 用 `CompatRegistry.registerCompat(CompatInfo, Supplier<Consumer<IEventBus>>)` 声明式登记十几个 mod 兼容，且依赖全部 `compileOnly`，运行时按 ModList 判定。
5. **数据包模板 + SavedData + 同步三件套给玩家「配置模板」能力**：`DatapackSettingsTemplateManager`（读包）+ `SettingsTemplateStorage`（存世界）+ `SyncDatapackSettingsTemplatePayload`（同步），适合任何「玩家可保存/应用预设」的功能。

## 8. 公开 API（库/前置 mod）

- 公开包：`net.p3pp3rf1y.sophisticatedcore.api`（`IStorageWrapper`、`IStorageFluidHandler`、`ISlotChangeResponseUpgrade`、`IIOFilterUpgrade`、`IUpgradeRenderer`、`IUpgradeRenderDataValidator`、`IDiscHandler`、`IStashStorageItem`、`InventoryLayoutFitter`/`InventoryLayoutPart`），另有 `upgrades/` 顶层接口（`IUpgradeItem`、`IUpgradeWrapper`、`UpgradeType`、`UpgradeWrapperBase`、`UpgradeItemBase`、`UpgradeGroup`）属事实公开面。
- 扩展点：新增升级（实现 `IUpgradeItem`+`IUpgradeWrapper`+`UpgradeType` 并注册物品）；库存分格 `InventoryPartRegistry.registerFactory(name, factory)`；渲染数据校验 `UpgradeRenderDataValidatorRegistry.registerValidator`；链接存储 `LinkedStorageHostFactories.register` / `LinkedStorageEndpointAdapters.register`。
- 外部接入方式：Maven 坐标 `net.p3pp3rf1y:sophisticatedcore`（GitHub Packages，`github_package_url`），`implementation` + `transitive = false`；`sophisticatedstorage`/`sophisticatedbackpacks` 的 `build.gradle` 用 `findProject(':SophisticatedCore')` 与坐标依赖双分支，同时支持源码多项目编译与二进制依赖。
