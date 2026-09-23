# Team-EnderIO/EnderIO 源码分析报告

## 1. 基本信息

- Mod 名：**Ender IO**；mod_id `enderio`；作者 CrazyPants / tterrag / HenryLoenwind / MatthiasM / CyanideX / EpicSquid / Rover656 / HypherionSA / liliandev / Ferri_Arnus / dphaldes
- 目标：Minecraft **1.21.1**（`gradle/libs.versions.toml`：`minecraft = { strictly = "[1.21.1]" }`）+ **NeoForge 21.1.216**，Java 21，Parchment 2024.07.28
- Gradle：**多模块 Kotlin DSL**（`settings.gradle.kts` / `build.gradle.kts`），插件 `net.neoforged.moddev` 2.0.124、`com.palantir.git-version`（版本号从 git tag 推导，见 `buildSrc/src/main/kotlin/mod-common-conventions.gradle.kts`）、依赖用 Version Catalog（`gradle/libs.versions.toml`）
- 许可证：主 mod 与 endercore 均为 **CC0**；测试 mod `enderio_tests` 为 MIT
- 三模块：`endercore`（**纯前置库**，`displayName="Ender Core"`，描述"Supporting library for Ender IO and its Modules"）、`enderio`（主 mod）、`enderio-modded-conduits`（Mekanism/AE2/RS 管道，独立 mod_id）
- 依赖关系（`enderio/build.gradle.kts:86-90`）：`api(project(":endercore"))` + `jarJar(project(":endercore"))`，`jarJar(project(":enderio-modded-conduits"))`
- 外部：`api(libs.graphlib)` + `jarJar(libs.graphlib)`（gigaherz `dev.gigaherz.graph:GraphLib3` 3.0.5，网络图算法）；compileOnly 大量可选（JEI / CC:Tweaked / Jade / AE2 / Mekanism / Refined Storage / LaserIO / FTB Ultimine / Curios / Iris / AlmostUnified）；测试用 JUnit5 + Mockito + `net.neoforged:testframework`

## 2. 源码规模与包结构

实测：

| 模块/sourceSet | 文件数 | 行数 |
|---|---|---|
| endercore/src/main/java | 126 | 6,310 |
| endercore/src/test/java | 3 | 305 |
| enderio/src/main/java | 917 | 66,460 |
| enderio/src/datagen/java | 56 | 6,772 |
| enderio/src/gametest/java | 31 | 3,171 |
| enderio/src/test/java | 26 | 2,476 |
| enderio-modded-conduits/src/main/java | 55 | 3,363 |
| 合计 | **1,217** | **约 88,900** |

`enderio` 顶层包：`api`（对外 API，约 130 类）、`client`、`compat`、`config`、`content`（18 个内容组：conduits/machines/capacitors/enchanter/enderface/filters/travel/soul…）、`foundation`（通用基础设施：block.entity/energy/fluid/inventory/io/menu/network/recipe/souldata/task）、`init`（22 个注册类）、`mixin`。
`endercore` 包：`core.{annotations, client.{gui,icon,item,model}, common.{blockentity, capability, energy, graph, item, lang, menu, network, recipes, registries, serialization, util}, data.{model,recipe}}`。

最大文件：`content/conduits/bundle/ConduitBundleBlockEntity.java`(1839)、`datagen/.../EIOLanguageProvider.java`(803)、`content/conduits/network/ConduitNetworkImpl.java`(751)、`foundation/block/entity/MachineBlockEntity.java`(666)、`content/conduits/bundle/ConduitBundleBlock.java`(640)、`init/EIOBlocks.java`(620)、`foundation/block/entity/legacy/LegacyMachineBlockEntity.java`(610)。

## 3. 入口与注册

主类 `enderio/src/main/java/com/enderio/enderio/EnderIO.java:53-155`，构造 `(IEventBus, ModContainer)`：

```java
@Mod(EnderIO.MOD_ID)
public EnderIO(IEventBus modEventBus, ModContainer modContainer) {
    EnderIO.modEventBus = modEventBus; EnderIO.modContainer = modContainer;
    modContainer.registerConfig(COMMON, BaseConfig.COMMON_SPEC, "enderio/base-common.toml");
    modContainer.registerConfig(CLIENT, MachinesConfig.CLIENT_SPEC, "enderio/machines-client.toml");
    modContainer.registerConfig(COMMON, ConduitsConfig.COMMON_SPEC, "enderio/conduits-common.toml");
    EIODataComponents.register(modEventBus); EIOItems.register(modEventBus); EIOBlocks.register(modEventBus);
    ... EIOConduitTypes.register(modEventBus); EIOTravelTargets.register(modEventBus);
    for (var entry : MOD_INTEGRATIONS.entrySet())
        if (ModList.get().isLoaded(entry.getKey())) entry.getValue().accept(modEventBus);
    modEventBus.addListener(this::registerRegistries);
    modEventBus.addListener(this::registerDatapackRegistries);
    modEventBus.addListener(this::addBuiltInPacks);
    Integrations.register();
}
```

- 注册框架：**原生 DeferredRegister**，集中在 `init/` 22 个类（EIOBlocks/EIOItems/EIOBlockEntities/EIOConduitTypes/EIORecipes/EIOAttachments/EIOIngredientTypes/EIOTravelTargets/EIODataMaps…）
- `registerRegistries` 用 `NewRegistryEvent` 注册 **7 个自定义注册表**：`TRAVEL_TARGET_TYPES`、`TRAVEL_TARGET_SERIALIZERS`、`CONDUIT_TYPE`、`CONDUIT_DATA_TYPE`、`CONDUIT_CONNECTION_CONFIG_TYPE`、`CONDUIT_NODE_DATA_TYPE`、`CONDUIT_NETWORK_CONTEXT_TYPE`（`EnderIO.java:127-135`）
- 更进一步：`Conduit` 本体是 **数据包注册表**——`event.dataPackRegistry(EnderIORegistries.Keys.CONDUIT, Conduit.DIRECT_CODEC, Conduit.DIRECT_CODEC)`（`EnderIO.java:137-139`），产出 `data/enderio/enderio/conduit/*.json`
- `endercore` 主类 `com/enderio/core/EnderCore.java` 极简：只有 `MOD_ID` 与 `loc()`，注释明确"core 无权访问 base"，即**前置库完全不引用主 mod**
- 额外：`EIOFeatureFlags` + `META-INF/feature_flags.json`，并用 `AddPackFindersEvent` 注册 3 个内置实验性数据包（farming_station / enderface / niard）

## 4. 核心系统

**(1) 管道（Conduit）系统 —— 数据驱动 + 类型化**（`api/conduits/` + `content/conduits/`）
- `ConduitType` 用 builder 声明能力：`ConduitType.builder(EnergyConduit.CODEC, EnergyConduitConnectionConfig.TYPE).exposeCapability(Capabilities.EnergyStorage.BLOCK).doesRequireNetworkCaches().ticker(FluidConduitTicker.INSTANCE, 5).connectionComparator(...).connectionComparerFromReference(new PriorityConnectionPathComparator(conn -> ...)).build()`（`init/EIOConduitTypes.java:40-70`）
- 连接配置也是数据：`ConnectionConfig` / `IOConnectionConfig` / `RedstoneSensitiveConnectionConfig` + `ConnectionConfigType` 注册
- 路径分配：`connection/path/{ConnectionPathProperty, DefaultConnectionPathComparator, PriorityConnectionPathComparator, SpeedAndTickRatePair}`——把"优先级/速度/频率"抽成可比较的路径属性
- 光缆捆扎：`bundle/ConduitBundleBlockEntity`（1839 行，本仓库最大文件）+ `AddConduitResult` + `SlotType`

**(2) 通用机器基类**（`foundation/block/entity/MachineBlockEntity.java`）
- 静态 `ICapabilityProvider` 暴露能力：`SIDE_CONFIG_PROVIDER`、`ITEM_HANDLER_PROVIDER`、`SOUL_BINDABLE`（`:67-73`）
- 统一的 IO 配置：`IOConfig` / `getIOMode(Direction)` / `setIOMode` / `supportsIOMode` / `isIOConfigMutable` / `shouldRenderIOConfigOverlay`
- 库存布局：`MachineInventoryLayout` + `MachineInventory` + `MachineState` 增量更新（`updateMachineState(state, add)`）
- tick 节流：`canAct(int interval)`、`distributeResourcesInterval()`

**(3) API 隔离用 Java ServiceLoader**（library 设计的关键点）
- `api/conduits/ConduitApi.java:12`：`ConduitApi INSTANCE = ServiceLoader.load(ConduitApi.class).findFirst().orElseThrow();`，实现 `content/conduits/ConduitApiImpl.java`
- 服务文件真实存在（`git ls-tree HEAD` 可见）：`enderio/src/main/resources/META-INF/services/com.enderio.enderio.api.conduits.ConduitApi` 与 `...api.travel.TravelTargetApi`
- API 带版本注解：`@ApiStatus.AvailableSince("8.1.0")`、`@ApiStatus.Experimental`、`@ApiStatus.OverrideOnly`（JetBrains annotations）

**(4) Soul（灵魂/刷怪笼数据）系统**（`api/soul/` + `foundation/souldata/`）
- `Soul` / `SoulHandler` / `SoulHandlerModifiable` / `SingleComponentSoulHandler`（存于 DataComponent）
- 联网自动同步：`SpawnerSoul.SPAWNER.subscribeAsSyncable(ClientboundPoweredSpawnerSoulPacket::new)`（`foundation/network/EIONetwork.java:44-47`）——4 种 soul 各接一个包，一行完成同步

**(5) Integrations 集成管理**（`api/integration/` + `foundation/integrations/`）
- `IntegrationManager` 提供 `wrapper(modid, supplier, modEventBus)`、`noneMatch/allMatch/anyMatch/forAll/findFirst/getFirst/executeIf/getIf/collectAll`（`:15-69`），把"是否装了某 mod"从散落的 if 收拢成集合查询

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络（`foundation/network/`）：`EIONetwork.register` 用 `event.registrar("3")`（PROTOCOL_VERSION）；handler 用**单例**（`ClientPayloadHandler.getInstance()`、`ServerPayloadHandler`、`ConduitClient/Common/ServerPayloadHandler`、`MachinePayloadHandler.Client`）按用途分工；20+ 个包类在 `foundation/network/packets/`。另有 `api/network/{DumbStreamCodec, MassiveStreamCodec}` 自定义 StreamCodec
- 菜单同步：`foundation/network/menu_sync/{EnergyStorageSyncSlot, MachineStatesSyncSlot}` 用 Slot 做容器数据同步
- 数据驱动：`EIODataMaps`（DataMap）、`EnderIORegistries` 7 个自定义注册表、`Conduit` 数据包注册表、`Ingredient` 自定义类型 `EIOIngredientTypes`、3 个内置数据包
- 配置（**3 个 spec 类产出 5 个文件**）：`BaseConfig.COMMON_SPEC/CLIENT_SPEC`、`MachinesConfig.*`、`ConduitsConfig.COMMON_SPEC`，分别写到 `enderio/base-common.toml`、`base-client.toml`、`machines-common.toml`、`machines-client.toml`、`conduits-common.toml`（`EnderIO.java:85-89`），config 目录自动创建
- datagen：`datagen/EnderIODataGen.onGatherData(GatherDataEvent)`（56 个类），子包含 `common/{advancement, datapack_registries, data_maps, loot, recipes, souldata, tags}`、`client/{models, sounds}`；`EIOLanguageProvider` 803 行；动态注册表 datagen 直接产出 `data/enderio/enderio/conduit/*.json`
- gametest：`enderio/src/gametest/java` 独立 sourceSet + **独立 mod `enderio_tests`**（`enderio/src/gametest/resources/META-INF/neoforge.mods.toml`）；含 `gametests/regressions/issues/Issue1033.java`、`Issue1313.java`、`Issue1436.java` 等**以 GitHub issue 编号命名的回归测试**，以及 `util/EnderGameTestHelper`、`conduits/ConduitGameTestHelper`
- 单元测试：`endercore` 与 `enderio` 都有 `src/test/java`（JUnit5 + Mockito），MDG 的 `unitTest { enable(); testedMod = mods["endercore"] }`

## 6. Mixin

- 配置：`enderio/src/main/resources/enderio.mixins.json`，package `com.enderio.enderio.mixin`，`compatibilityLevel: JAVA_17`，common 3 个 + client 2 个
- common：`AbstractCookingRecipeAccessor`（原版配方 Accessor）、`PlayerMixin`、`RecipeManagerMixin`
- client：`GliderRotationMixin`、`BlockRenderDispatcherMixin`
- 更值得注意的是**它优先用 AccessTransformer 而非大量 Accessor mixin**：`enderio/src/main/resources/META-INF/accesstransformer.cfg` 声明的都是成品 mod 会碰的痛点，例如 `public-f net.minecraft.world.inventory.Slot x / y # used for conduitslots to hide them for other configuration`、`public net.minecraft.world.inventory.AbstractContainerMenu doClick(...)V # GhostSlotBehaviour`、`public-f net.minecraft.client.renderer.block.model.BakedQuad sprite`、`public net.minecraft.world.level.BaseSpawner nextSpawnData`、`public net.minecraft.client.sounds.SoundManager soundEngine`

## 7. 值得学的 5 条具体做法

1. **前置库独立成模块并用 jarJar 内嵌**：`endercore` 是 CC0 的纯前置 mod，主 mod 用 `api(project(":endercore"))` + `jarJar(project(":endercore"))`（`enderio/build.gradle.kts:86-87`），`EnderCore.java` 只有 MOD_ID 且注释"core 无权访问 base"——单一依赖方向、可独立发布；写库 mod 直接照搬
2. **API 用 Java ServiceLoader 而非静态字段**：`ConduitApi.INSTANCE = ServiceLoader.load(ConduitApi.class).findFirst().orElseThrow()` + `META-INF/services/` 文件（`api/conduits/ConduitApi.java:12`）；API 类不反向依赖实现，实现类可在 content 包内
3. **API 方法标 `@ApiStatus.AvailableSince("8.1.0")` / `@ApiStatus.Experimental`**（`api/conduits/ConduitApi.java:20-33`）；对外承诺版本边界，避免附属 mod 踩"哪个版本开始有"
4. **管道的"类型 + 连接配置 + 网络上下文 + 节点数据"全部做成自定义注册表，Conduit 本体做成数据包注册表**：`NewRegistryEvent` 注册 7 个 + `DataPackRegistryEvent` 注册 `CONDUIT`（`EnderIO.java:127-139`）；适合想让整合包用 JSON 增删内容的场合
5. **回归测试按 issue 编号建类**：`gametests/regressions/issues/Issue1436.java`（共 11 个），配合独立的 `enderio_tests` gametest mod；每个修复过的 bug 都留一个可执行测试

## 8. 公开 API（库/API 视角）

- 对外 API 包：`com.enderio.enderio.api`（约 130 类），根类 `EnderIOAPI`（MOD_ID/rl）、`EnderIORegistries`（`Keys.CONDUIT` 等）、`EnderIOCapabilities`、`EnderIODataComponents`
- 主要扩展点接口：
  - 管道：`conduits/{Conduit, ConduitType, ConduitApi, ConduitTickerBase, ConduitModelModifier, ConduitFacadeProvider, ConduitIngredient}`，事件 `RegisterConduitModelModifiersEvent`、`RegisterConduitScreenTypesEvent`
  - 电容/倍率：`capacitor/{CapacitorData, CapacitorModifier, CapacitorScalable, ICapacitorExtension}` + `FixedScalable/LinearScalable/QuadraticScalable/SteppedScalable`
  - 旅行目标：`travel/{TravelTarget, TravelTargetApi, TravelTargetSerializer, TravelTargetType, RegisterTravelRenderersEvent}`
  - 农业任务：`farm/{FarmTask, FarmTaskType, FarmTaskManager, FarmingMachine, FarmInteraction, RegisterFarmTasksEvent}`
  - 筛选器：`filter/{ItemFilter, FluidFilter, RedstoneFilter, RedstoneInput/OutputFilter, SoulFilter, FilterMenuProvider}`
  - IO：`io/{IOMode, SideConfig, IOConfigurable, RedstoneControl}`
  - 集成：`integration/{Integration, IntegrationManager, IntegrationWrapper, IntegrationMethods, ClientIntegration}`
- 接入方式：Java **ServiceLoader**（`META-INF/services/`）+ 自定义注册表（`NewRegistryEvent`）+ 数据包注册表 JSON + `IntegrationWrapper`（运行时判定另一个 mod 是否加载）；另有 KubeJS 之外的主要脚本/兼容入口集中在 `compat/`（cctweaked / jade / jei / curios / ftb_ultimine / laserio / almostunified / vanilla）
