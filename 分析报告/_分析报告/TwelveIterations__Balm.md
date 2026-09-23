# TwelveIterations/Balm 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Balm / `balm` |
| 作者 | BlayTheNinth (TwelveIterations) |
| 目标版本 | Minecraft `26.2`（`gradle/libs.versions.toml`：`minecraft = "26.2"`、`neoForm = "26.2-1"`） |
| 加载器 | NeoForge `26.2.0.0-beta`、Fabric Loader `0.19.3` + Fabric API `0.152.1+26.2`、Forge `65.0.3`（`gradle.properties` 当前 `include_forge=false`，Forge 模块源码存在但不参与默认构建） |
| Gradle 插件 | `net.fabricmc.fabric-loom 1.17-SNAPSHOT`、`net.neoforged.moddev 2.0.141`、`net.minecraftforge.gradle [7,8)`、`curseforgegradle`、`minotaur`；自研约定插件放在 `build-logic/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle`（不发布） |
| Java | 25（`gradle.properties: java_version = 25`） |
| 许可证 | All Rights Reserved（`gradle.properties: license = All Rights Reserved`）；**代码不可直接复制** |
| 编译依赖 | `api libs.kumaCommon`（Kuma API `26.2.0.1`，NeoForge 侧 `jarJar`）；compileOnly：JEI、Jade、WTHIT、TheOneProbe、Cloth Config、Configured、Trinkets、Curios、FTB Ultimine、Vivecraft、mixinExtras 0.5.2 |

关键点：Balm 自身是"加载器抽象层"，`net.blay09.mods.balm.platform.*` 为平台无关 API，各 loader 模块提供实现。

## 2. 源码规模与包结构

856 个 `.java`、33288 行。模块分布：common 499 / fabric 125 / neoforge 112 / forge 107 / 三个 example 13。

主要包（common，深度 5，文件数）：
- `platform/config/schema` + `schema/builder` 34、`client/platform/config/screen` 系列 36 —— 配置系统最大
- `platform/event/callback` 15、`platform/event/internal` 9 —— 事件
- `internal/mixin` 13、`mixin` 8 —— mixin
- `platform/compatibility/*`（config/hudinfo/milk/multiminers/recipeviewer/trinkets/vr）约 40 —— 三方 mod 统一兼容层
- `world` 系列（item/block/entity/inventory/level/loot）约 50；`network` 12；`core`（注册器）8

最大文件：`BalmConfigListEditorScreen.java` 383 行、`NeoForgeBalmConfig.java` 352、`ConfiguredConfigProvider.java` 349、`ClothConfigSupport.java` 319、`BalmConfigScreen.java` 316、`world/inventory/QuickMove.java` 314、`ForgeBalmConfig.java` 304、`Balm.java` 262、`BalmRegistrars.java` 229、`NeoForgeBalmRuntime.java` 211。

## 3. 入口与注册

- 公共门面：`common/src/main/java/net/blay09/mods/balm/Balm.java`（静态 API，`Balm.config()/networking()/capabilities()/hooks()/platform()` 等）。
- 运行时通过 SPI 装载：`common/.../platform/runtime/internal/BalmRuntimeSpi.java:9` 用 `ServiceLoader.load(BalmRuntimeFactory.class)` 取实现；各 loader 在 `{fabric,neoforge,forge}/src/main/resources/META-INF/services/net.blay09.mods.balm.platform.runtime.internal.BalmRuntimeFactory` 中声明实现类（另有 `BalmClientRuntimeFactory`）。
- NeoForge 入口：`neoforge/.../neoforge/internal/NeoForgeBalm.java`（`@Mod("balm")`）——注册 `BalmLoadContexts`、初始化 runtime、注册 loot modifier codec、`DeferredRegisters.register("balm", modBus)`、注册 3 个 capability fallback。
- Fabric 入口：`fabric/.../fabric/internal/FabricBalm.java`（`ModInitializer`）——`ItemStorage.SIDED.registerFallback`、`FluidStorage.SIDED.registerFallback`、`ServerPlayerEvents.COPY_FROM` 复制附加数据。
- 注册框架：不是 DeferredRegister 直用，而是 `core/BalmRegistrars.java`（229 行）把每个 registry 包装成"scoped registrar"（`BalmItemRegistrar`/`BalmBlockRegistrar`/`BalmEntityTypeRegistrar`/`BalmMenuTypeRegistrar`/`BalmParticleTypeRegistrar`/`BalmCustomStatRegistrar`/`BalmArgumentTypeRegistrar`/`BalmResourceReloadListenerRegistrar`/`BalmDataComponentTypeRegistrar`/`BalmDataAttachmentTypeRegistrar`/`BalmWorldGen`/`BalmLootTables`…），统一签名 `void items(String namespace, Consumer<BalmItemRegistrar>)`。
- 使用方式（`common-example/src/main/java/com/example/balm/BalmExample.java`）：`registrars.registerModule(new CustomRegistryTestModule())`；每个模块实现 `platform/module/BalmModule.java`，覆写 `registerItems/registerBlocks/registerNetworking/registerConfig…` 默认方法。NeoForge 侧由 `@Mod` 构造器调用 `Balm.initializeMod("balm_example", new NeoForgeLoadContext(modContainer, modEventBus), BalmExample::initialize)`。
- NeoForge 注册表实现：`neoforge/.../neoforge/core/internal/DeferredRegisters.java:15` 用 `Table<ResourceKey<?>, String, DeferredRegister<?>>` 按 (registry, modId) 去重缓存，第 41 行动态 `deferredRegister.register(modEventBus)`——避免每个 mod 重复创建 DeferredRegister。

## 4. 核心系统

**① Runtime 抽象**（`platform/runtime/internal/BalmRuntime.java`、各 `*BalmRuntime`）：interface 描述所有平台能力（`menuTypes/entityTypes/particleTypes/initializeMod/sidedProxy/platformProxy/modProxy`），每 loader 一份实现（`NeoForgeBalmRuntime.java` 211 行、`FabricBalmRuntime.java` 211 行）——同一套业务代码零 loader 分支。

**② 事件系统**（`platform/event/`）：`Event`/`EventFactory`（内部 `ArrayBackedEvent`，与 Fabric API 事件同构）+ `EventPhases` 定义 `balm:lowest/low/default/high/highest` 优先级（`EventPhases.java`）；`BidirectionalEventMapper` 把公共回调同时映射到 loader 事件总线并可 `invoker()` 反向触发（`configureMapping(registrar, invoker)`），未绑定的 loader 事件也能复用同一接口。回调清单在 `platform/event/callback/`（`PlayerCallback`、`LivingEntityCallback`、`ItemCallback`、`CommandCallback`、`ServerTickCallback`、`CropCallback`…）。

**③ 配置系统**（`platform/config/`）：注解声明式——`@Config("modid")` 类 + `@Comment/@Range/@NestedType/@CustomControl/@ValidateWith/@ValidateCollectionWith`（见 `common-example/.../ExampleConfig.java`），由 `platform/config/reflection/internal/ConfigReflection.schemaOf(Class)` 反射生成 `BalmConfigSchema`；值类型为 `ConfiguredBoolean/Int/Long/Double/Float/String/Enum/Identifier/List/Set`（`platform/config/schema/`）；支持无 TOML 环境（`platform/config/notoml/`）；自带配置界面 `client/platform/config/screen/BalmConfigListEditorScreen.java`（383 行），并可通过 `getPreferredConfigScreenProviders` 让 Cloth Config / Configured 接管（`platform/compatibility/config/internal/ClothConfigSupport.java`、`ConfiguredConfigProvider.java`）。

**④ Capability 统一层**（`platform/capabilities/BalmCapabilities.java` + 各 loader 实现）：公共标识 `CommonCapabilities.CONTAINER/FLUID_TANK/ENERGY_STORAGE`，业务侧只实现 `BalmContainerProvider`/`BalmFluidTankProvider`/`BalmEnergyStorageProvider`；NeoForge 映射到新 transfer API（`ResourceHandler<ItemResource>`、`EnergyHandler`），Fabric 映射到 `ContainerStorage.of`/`FluidStorage`。实现里用 `private boolean running` 做递归保护（`NeoForgeBalm.java` / `FabricBalm.java`），防止 fallback 自调用死循环——很值得抄的模式。

**⑤ 网络**（`network/BalmNetworking.java`）：基于原版 `CustomPacketPayload` + `StreamCodec<RegistryFriendlyByteBuf, T>`，`registerClientboundPacket/registerServerboundPacket`，`sendTo/sendToTracking(BlockPos|Entity)/sendToAll/sendToServer/reply`；另有 mod 列表与网络版本协商（`NetworkVersions.java`、`RemotePlayerModList.java`、`ServerboundModListMessage.java`）。

**⑥ 容器快速移动 DSL**（`world/inventory/QuickMove.java` 314 行）：`QuickMove.create(this, this::moveItemStackTo).route(...).build()`，用 `"container"/"player"` 命名槽位区间，业务在 `quickMoveStack` 里一行 `quickMove.transfer(this, player, index)` 完成 shift-click 路由——比手写 20 个 `moveItemStackTo` 分支清晰得多，可直接借鉴。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 ④，统一 `CustomPacketPayload`，无自定义协议编号。
- 数据驱动：`createDynamicRegistry(ResourceKey, Codec<T>)`（`core/BalmRegistrar.java`）让业务 mod 一条语句注册数据包加载的动态注册表；`server/packs/resources` 下提供跨平台 `ResourceReloadListener` 与 `ResourceCondition` 注册。
- 配置：TOML，每 schema 一个 `config/<namespace>-<path>.toml`；有本地/生效配置区分（`MutableLoadedConfig` / `LoadedConfig` / `getActiveConfig`，用于服务端下发覆盖）。
- datagen：common 无 DataGenerator 源集；Fabric 侧配置了 datagen run，输出目录固定为 `../common/src/generated/resources`（`fabric/build.gradle:42-46`），common 用 `sourceSets.generated` + `commonGeneratedResources` 构件分发；仓库内当前无 `src/generated`。

## 6. Mixin

- `common/src/main/resources/balm.mixins.json`（`net.blay09.mods.balm.internal.mixin`）：`MinecraftServerMixin`、`ReloadableServerResourcesMixin`、`LivingEntityMixin`、`CropBlockMixin`、`StemBlockMixin`、`BlockStateBaseAccessor/Mixin`、`ChunkMapAccessor`、`TrackedEntityAccessor`；client：`DebugScreenOverlayMixin`、`LevelExtractorMixin`、`ChestRendererMixin`。
- `balm.api.mixins.json`（`net.blay09.mods.balm.mixin`）：对外暴露的访问器——`SlotAccessor`、`RecipeManagerAccessor`、client 侧 `AbstractContainerScreenAccessor`、`MouseHandlerAccessor`、`ScreenAccessor`、`KeyMappingAccessor`、`CheckboxAccessor`、`ImageButtonAccessor`（业务 mod 可直接 cast 使用）。
- loader 专属：`balm.neoforge.mixins.json`（`EntityMixin`、`LivingEntityMixin`、client `MinecraftMixin`/`ScreenMixin`）、`balm.fabric.mixins.json`（30+ 个，如 `GuiMixin`、`KeyboardHandlerMixin`、`ChatComponentMixin`）；`forge` 另有自己的配置。

## 7. 值得学的 5 条具体做法

1. **同一套业务代码跑三 loader**：SPI（`META-INF/services/...BalmRuntimeFactory`）+ `ServiceLoader` 选择 runtime，见 `platform/runtime/internal/BalmRuntimeSpi.java:9`；适用于任何多加载器库或需要按 loader 换实现的服务。
2. **注册表按 (registry, modId) 去重缓存**：`neoforge/core/internal/DeferredRegisters.java:15`；适用于把 DeferredRegister 包装成统一 API 时避免重复注册。
3. **capability fallback 递归保护**：`private boolean running` + 二次自查（`NeoForgeBalm.java`、`FabricBalm.java`）；适用于跨 API 桥接、防止 provider 互相调用死循环。
4. **声明式 shift-click 路由 DSL**：`world/inventory/QuickMove.java`；适用于任何自定义容器菜单。
5. **配置用注解 + 反射生成 schema**：`platform/config/reflection` + `common-example/ExampleConfig.java`；配置项校验（`@Range`、`ConfigValidator` 子类）与界面自动生成，避免手写 GUI 与读写代码。
6. （补充）**三方 mod 兼容统一抽象**：`platform/compatibility/BalmModSupport.java` 把 Jade/WTHIT/TheOneProbe、JEI/REI、Curios/Trinkets、FTB Ultimine、Vivecraft 各收敛成一个接口；业务 mod 不再写 `isModLoaded` 分支。
7. （补充）**example 模块即文档**：`common-example` 9 个文件演示注册/动态注册表/capability/配置/客户端模块的完整用法。

## 8. 公开 API（库/前置类 mod）

- 主入口 API：`net.blay09.mods.balm.Balm`（`initializeMod`、`config()`、`networking()`、`capabilities()`、`hooks()`、`platform()`、`modSupport()`、`commands()`、`lootModifiers()`、`biomeModifications()`、`permissions()`、`sidedProxy`、`platformProxy`、`modProxy`）；客户端 `net.blay09.mods.balm.client.BalmClient` + `BalmClientModule`。
- 模块扩展点：`net.blay09.mods.balm.platform.module.BalmModule`（30+ 个 `registerXxx` 默认方法）——推荐的接入方式。
- 非 Balm 用户的接入：`net.blay09.mods.balm.Balmstrap#onRuntimeAvailable(Runnable)` 与 `createBoundCustomEvent(Class)`（`Balmstrap.java`），供第三方 mod 等 Balm 就绪后回调。
- 平台探针：`Balm.platform().isModLoaded(...)`、`Balm.initializeIfLoaded(modId, className)`（按需延迟类加载，见 `FabricBalm.java` 中 Reborn Energy 兼容）。
- Mixin 级 API：`net.blay09.mods.balm.mixin.*Accessor`（`balm.api.mixins.json`）。
- 许可为 All Rights Reserved：只能学结构与模式，不能搬代码。
