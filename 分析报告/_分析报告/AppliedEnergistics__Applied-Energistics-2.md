# AppliedEnergistics/Applied-Energistics-2 源码分析报告

## 1. 基本信息

- Mod 名：Applied Energistics 2；mod_id：`ae2`；作者：Team AppliedEnergistics（`src/main/neoforge.mods.toml`）
- 目标版本/加载器：本 checkout 为**最新开发分支**——`gradle.properties`：`minecraft_version=26.1.2`、`neoforge_version=26.1.2.21-beta`、`java_version=25`、`guideme_version=26.1.10-alpha`；**仅 NeoForge**（`[[dependencies.ae2]] neoforge REQUIRED`，仓库内无 fabric 源集）
- Gradle：ModDevGradle `net.neoforged.moddev` 2.0.141 + `net.neoforged.moddev.repositories`、spotless 6.25.0、foojay-resolver（`settings.gradle` 的 pluginManagement / dependencyResolutionManagement，`RepositoriesMode.FAIL_ON_PROJECT_REPOS`）
- 许可证：**双许可**——`appeng/api/**` 文件头为 MIT（Copyright Team AppliedEnergistics），其余实现为 LGPL-3.0；mods.toml 只写 `license="See GitHub repository for details"`
- 编译依赖：`implementation("org.appliedenergistics:guideme:${guideme_version}")` —— **GuideME 是硬依赖**（mods.toml 中 `guideme` REQUIRED）；`compileOnly` 有 REI、WTHIT、Jade、JEI 19.x；测试用 junit/assertj/mockito；另有 flatbuffers、snakeyaml、directory-watcher、ffmpeg。它是**平台类 mod**（提供 `appeng.api` 给其他附属）

## 2. 源码规模与包结构

实测：**1453 个 .java，165797 行**。源集：`src/main` 1081、`src/client` 310（含 datagen 35 + mixins 6）、`src/test` 52、`src/buildtools` 1。**注意它把客户端与 datagen 从 main 里拆成独立源集**。

main 顶层包文件数：`api` 266、`menu` 97、`parts` 78、`core` 73、`server` 67、`me` 64、`block` 53、`items` 52、`blockentity` 51、`integration` 41、`util` 41、`crafting` 32、`recipes` 32、`helpers` 28、`init` 16、`hooks` 14、`worldgen` 13、`debug` 12、`spatial` 9、`mixins` 9、`decorative` 7、`thirdparty` 7。

最大文件：`CraftingRecipes.java` 1511、`CableBusContainer.java` 1101、`AEBaseScreen.java` 1100、`AEBaseMenu.java` 1049、`TestPlots.java` 1022、`MEStorageScreen.java` 871、`PatternProviderLogic.java` 818、`GridNode.java` 787、`AEConfig.java` 777、`MEChestBlockEntity.java` 734。

## 3. 入口与注册

- 入口三段式：`appeng.core.AppEng` 是**接口**（`MOD_ID` 与 `instance()`/`makeId()` 静态方法，`AppEngBase.INSTANCE` 承载实现）；`AppEngBase` 是共享基类；`AppEngServer`（`@Mod(value = AppEng.MOD_ID, dist = Dist.DEDICATED_SERVER)`，`AppEngServer.java:30`）与客户端源集里的 `AppEngClient` 分别继承。
- 注册集中在 `AppEngBase` 构造器（`AppEngBase.java:121-192`）：

```java
AEBlocks.DR.register(modEventBus);      AEItems.DR.register(modEventBus);
AEBlockEntities.DR.register(modEventBus);  AEComponents.DR.register(modEventBus);
AEEntities.DR.register(modEventBus);    AERecipeTypes.DR.register(modEventBus);
AEAttachmentTypes.register(modEventBus);  InitStructures.register(modEventBus);
modEventBus.addListener(InitNetwork::init);
modEventBus.addListener(EventPriority.HIGH, InitCapabilityProviders::markProxyableCapabilities);
modEventBus.addListener(InitCapabilityProviders::register);
```

- 每个注册表一个 `DeferredRegister` 静态字段，命名为 `DR`（`AEBlocks.java`、`AEComponents.java:41`、`AEAttachmentTypes` 等），**定义类与注册器同文件**：`AEBlocks` 既持有 `DR` 也定义 `BlockDefinition<T>`（`core/definitions/BlockDefinition.java:34`，打包 block+item+englishName+`id()`，还提供 `genericStack()` 直接产出 AE 存储键）。
- 自定义注册表用 `NewRegistryEvent`（`AppEngBase.java:249-260`）建 `AEKeyType` 注册表；`AEKeyType` 自身带 `CODEC` 与 `STREAM_CODEC`（`ByteBufCodecs.registry(...)`），因此可作为数据包与 JSON 字段类型。
- 少数注册直接走原版 `Registry.register`（声音、创造模式标签、`Registries.TEST_INSTANCE_TYPE`，`AppEngBase.java:245-268`）。

## 4. 核心系统

**(1) 网格（Grid / GridNode）** — `src/main/java/appeng/me/`
- `Grid.create(GridNode center)` 由中心节点创建，`pivot` 随节点增删漂移（`Grid.java:86-130`）；`SetMultimap<Class<?>, IGridNode> machines` 按 owner 类型分组（`:73`）；静态 `ITERATION_BUFFER` 复用以避免 ConcurrentModificationException（`:70`）
- 节点通过 `IGridHelper` + `IGridNodeListener<T>` 创建，owner **无需实现任何接口**（API.md 明确说明，便于外部 mod 无硬依赖接入）
- 网格**纯服务端概念**，客户端不存在；通道/路径计算在 `me/pathfinding/`：`PathingCalculation`、`ChannelFinalizer`、`ControllerValidator`、`AdHocChannelUpdater`

**(2) 网格服务注册表** — `src/main/java/appeng/api/networking/GridServices.java`
- 静态 `List<GridCacheRegistration<?>>` + 反射构造，注释明示"不得重排，存在相互依赖"；服务实现集中在 `me/service/`：`CraftingService`、`EnergyService`、`StorageService`、`PathingService`、`P2PService`、`StatisticsService`、`SpatialPylonService`、`TickManagerService`；`Grid.getService(Class<C>)` 按接口取服务（`Grid.java:147-150`）

**(3) 通用存储键抽象（自定义注册表的核心）** — `src/main/java/appeng/api/stacks/`
- `AEKey`（类型而非数量）+ `GenericStack(key, amount)` + `KeyCounter`；`AEKeyType` 描述一类键（`getAmountPerByte()`/`getAmountPerOperation()`/`filter()`/`supportsFuzzyRangeSearch()`），注册表 `ResourceKey<Registry<AEKeyType>> REGISTRY_KEY`（`AEKeyType.java:55-60`）
- `AEKeyTypes.register(...)` 是**附属 mod 扩展点**（`api/stacks/AEKeyTypes.java:56`），`AEKeyTypesInternal` 只对内暴露
- `MEStorage`（`api/storage/MEStorage.java:52`）只用 `insert/extract(AEKey, long, Actionable, IActionSource)` + `getAvailableStacks(KeyCounter out)`，`Actionable` 区分模拟/执行，`IActionSource` 传递发起者与上下文 —— 整套接口与物品/流体/自定义键无关

**(4) 枚举设置同步框架** — `src/main/java/appeng/api/config/`
- `Setting<T extends Enum<T>>` 是不可变值对象，`Settings` 是一张 `Map<String, Setting<?>>` 的全局注册表，`Setting.setFromString(cm, value)` 按**枚举名字符串**反序列化（`Setting.java:46-56`），因此 NBT/数据包/GUI 循环全靠 `IConfigManager` 一套代码
- 终端/机器上的 `ModSettings` 与 `menu` 包联动，97 个 menu 类共享 `AEBaseMenu`（`AEBaseMenu.java:92`）

**(5) 制造与样板** — `src/main/java/appeng/crafting/`
- `crafting/pattern/` 下每种配方类型一个编码后的样板类：`EncodedCraftingPattern`、`EncodedProcessingPattern`、`EncodedSmithingTablePattern`、`EncodedStonecuttingPattern`，**全部存进数据组件**（`AEComponents.java`），不再用 NBT；`crafting/execution/` 负责实际执行，`PatternProviderLogic` 818 行是样板供应器核心

**(6) 游戏内测试基建（少见）** — `src/main/java/appeng/server/testplots/TestPlots.java`（1022 行）
- 用原版 GameTest 框架搭"测试地块"，在 `RegisterGameTestsEvent` 里注册（`AppEngBase.java:330-332`），并写 mixin 扩展 `TestInstanceBlockEntity`/`TestCommand` 以支持自定义结构模板（`mixins/tests/`）；`src/test` 另有 52 个 JUnit 类

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`appeng/core/network/InitNetwork.java` 手工逐个注册约 40 个包，分 `clientbound/`、`serverbound/`、`bidirectional/` 三个子包；`ClientboundPacket`/`ServerboundPacket` 接口提供 `static handleOnServer`/`handleOnClient` 作为 handler 方法引用；注册用私有辅助方法 `serverbound(...)`/`bidirectional(...)` 去重复代码（`InitNetwork.java:88-101`）。另有同步配方下发：`OnDatapackSyncEvent` → `registerSynchronizedRecipes`（`AppEngBase.java:192-197`）
- **数据驱动**：配方走 `AERecipeTypes`/`AERecipeSerializers`；`AppEng.getRecipeMapForType(level, type)` 走 `RecipeMap` 做无查找开销的配方索引（`AppEng.java:88`）；`guidebook/` 目录是纯 Markdown 的指南书内容（配合 GuideME）
- **配置**：`appeng/core/AEConfig.java`（777 行）用 `ModConfigSpec` 内部分成 `ClientConfig`/`CommonConfig` 两个内部类，`container.registerConfig(CLIENT/COMMON)` 注册，在 `ModConfigEvent.Loading` 时执行 `common.sync()` 把配置值灌进静态字段（`AEConfig.java:56-62`）；`core/settings/` 放 `TickRates` 等
- **datagen**：入口 `src/client/java/appeng/datagen/AE2DataGenerators.java:64`（`onGatherData(GatherDataEvent.Client)`），provider 分 `advancements/localization/loot/models/recipes/tags` 六个目录，`IAE2DataProvider` 做统一接口
- **构建期校验工具**：`src/buildtools/java/ValidateResourceIds.java`（独立源集），在 build 阶段校验资源 id 命名

## 6. Mixin

配置：`src/main/resources/ae2.mixins.json`（`package: appeng.mixins`，`plugin: appeng.mixins.ConfigPlugin` 做条件化启用，`injectors.defaultRequire: 1`），在 mods.toml 里 `[[mixins]] config="ae2.mixins.json"`。共 15 个 mixin（main 9 / client 6）。代表性：

- `chunkloading/ChunkMapMixin.java:26` — `@Inject(at = @At("RETURN"), method = "anyPlayerCloseEnoughForSpawning", cancellable = true)`，让空间锚（spatial anchor）强制加载的区块也允许刷怪/随机 tick
- `spatial/MinecraftServerMixin.java:62` — `@Inject(method = "createLevels", at = @At("TAIL"))`，注入空间存储维度
- `AnvilMenuMixin.java:24` — `@ModifyExpressionValue(method = "createResultInternal", at = @At(value="INVOKE", target="...ItemStack.isDamageableItem()Z", ordinal = 1))`
- `ItemEntityMixin.java:42/56`、`EnchantmentHelperMixin.java:17`、`StructureTemplateMixin.java:18/23`（`fillFromWorld` 的 HEAD/TAIL 分别用于开始/结束记录结构）
- 客户端：`client/PartModelLoaderMixin.java:18` `@WrapMethod(method = "loadBlockStates")`；`client/PickColorMixin.java:27`（`Minecraft.pickBlockOrEntity`）；`client/GuiGraphicsMixin.java:40`；**`client/PonderWorldMixin.java:21` 直接 mixin `com.simibubi.create.foundation.ponder.PonderWorld`（`remap = false, require = 0`）** —— 对 Create 的软兼容做法

## 7. 值得学的 5 条具体做法

1. **自有"存储键"抽象，把物品/流体/任意类型统一成 key+amount**：`api/stacks/AEKey.java` + `api/stacks/AEKeyType.java` + `api/storage/MEStorage.java:52` —— 适用需要支持多种"可存储物"（物品/流体/能量/自定义）的库。
2. **把枚举设置做成全局注册表 + 按名反序列化**：`api/config/Setting.java`、`Settings.java` —— 适用一张 GUI 要同时服务 NBT/数据包/命令多套出口的场景，省掉每处 switch。
3. **API 接口 + Base 实现 + 分端子类的三段式入口**：`core/AppEng.java`（接口/工具方法）、`AppEngBase.java`（共享注册）、`AppEngServer`/`AppEngClient` —— 适用库 mod 需要给外部 mod 一个不依赖加载器的静态入口。
4. **mixins.json 里挂 `plugin` 做条件化 mixin**：`ae2.mixins.json` 的 `"plugin": "appeng.mixins.ConfigPlugin"` —— 适用希望 mixin 受配置开关控制。
5. **用原版 GameTest 搭机器测试地块**：`server/testplots/TestPlots.java` + `mixins/tests/TestInstanceBlockEntityMixin.java` + `RegisterGameTestsEvent` —— 适用大型科技 mod 做可回归的功能测试。

## 8. 公开 API（平台 mod）

- API 包：`src/main/java/appeng/api/`（266 文件，MIT 许可），根文档 `API.md` 列出扩展点：`AEKeyTypes`（自定义存储类型）、`GridServices`（网格服务）、`BlockEntityMoveStrategies`、`GridLinkables`、`StorageCells`、`Locatables`、`P2PTunnelAttunement`、`StorageCellModels`
- 初始化顺序问题：加载器无关的入口接口 `appeng/api/IAEAddonEntrypoint.java`（API.md 说明 Fabric 上 mod 初始化顺序不定，依赖 AE2 物品已注册的附属需用它）
- 稳定 id 常量：`appeng/api/ids/AEItemIds.java`、`AEBlockIds`、`AEPartIds`、`AETags`、`AEComponents` —— 附属引用 AE2 内容时从这里取，不硬编码字符串
