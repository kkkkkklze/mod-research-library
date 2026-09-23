# mekanism/Mekanism 源码分析报告

## 1. 基本信息

- Mod 名：Mekanism；mod_id：`mekanism`（`Mekanism.java:138` = `MekanismAPI.MEKANISM_MODID`）；作者：Aidancbrady, Thommy101, Thiakil, pupnewfster, dizzyd（`src/main/resources/META-INF/neoforge.mods.toml`）
- 目标版本/加载器：**Minecraft 1.21.1 + NeoForge 21.1.200，仅 NeoForge**（`gradle.properties`：`minecraft_version=1.21.1`、`neo_version=21.1.200`、`neo_version_range=[21.1.194,)`、`java_version=21`、`mod_version=10.7.19`）
- Gradle 插件：`net.neoforged.moddev` 2.0.107、curseforgegradle、minotaur、grgit、maven-publish（`build.gradle:16-25`）；Gradle 9.0.0
- 许可证：MIT（mods.toml `license="MIT"`；仓库根目录无 LICENSE 文件）
- 编译依赖（`build.gradle:452-515`）：`project(':annotation-processor')` 是自研注解处理器模块；`compileOnly` 引用 JEI/EMI API、TOP、Jade、WTHIT、CraftTweaker、JsonThings、ProjectE API、Flux Networks、GrandPower、Curios API、CC:Tweaked 等（全部是 `compileOnly`，非硬依赖）。它**提供** API 给：Applied-Mekanistics、appmek（在 mods.toml 里声明为 `incompatible`）、Mekanism 三件套（Additions/Generators/Tools 同仓库内）。

## 2. 源码规模与包结构

实测：**2455 个 .java，257399 行**。按源集分布：`src/main` 1760、`src/api` 265、`src/datagen` 147、`src/generators` 121、`src/additions` 64、`src/tools` 52、`src/test` 24、`src/gameTest` 12。

包结构（`mekanism` 命名根）：
- `mekanism.common`：`registries`(26 类，注册总表)、`registration/impl`(29 类，注册框架)、`tile/{base,machine,component}`、`lib/{multiblock,transmitter,inventory,frequency,radiation,security,chunkloading,math}`、`capabilities/{energy,chemical,fluid,heat,item,merged,holder}`、`content/{qio,network,gear,boiler,evaporation,matrix,sps,tank,transporter}`、`recipe`、`config`、`network`(75 类)、`world`、`integration`、`command/builders`
- `mekanism.client`：`gui/{element,machine,qio,robit,tooltip}`、`render/{tileentity,entity,armor,item,transmitter,obj}`、`model/{baked,data}`、`recipe_viewer/{jei,emi}`、`key`、`sound`
- `mekanism.api`：`chemical`、`energy`、`heat`、`radiation`、`recipes/ingredients`、`gear`、`security`、`datagen`、`integration`

最大文件：`MekanismLangProvider.java` 1832、`TileEntityMekanism.java` 1712、`MekanismRecipeProvider.java` 1674、`TileEntityDigitalMiner.java` 1487、`MekanismBlocks.java` 1131、`MekanismBlockTypes.java` 963、`QIOItemViewerContainer.java` 930、`QIOCraftingWindow.java` 927。

## 3. 入口与注册

单仓库内 4 个 @Mod 类，分别对应 4 个源集：`mekanism.common.Mekanism`（`Mekanism.java:135`）、`MekanismGenerators`、`MekanismAdditions`、`MekanismTools`，各自还有 `dist = Dist.CLIENT` 的客户端伴生类（`MekanismClient.java:31` 等）。三件套 + 主模组都实现 `IModModule`（`src/main/java/mekanism/common/base/IModModule.java`），通过 `Mekanism.addModule()` 汇入静态列表 `modulesLoaded`（`Mekanism.java:174/221`）。

主类构造器工作流（`Mekanism.java:188-219`）：配置注册 → 挂 NeoForge 事件总线监听 → `modEventBus.addListener` 挂能力/公共初始化 → `addRegistrationListeners` 把 30 个 DeferredRegister 一次性 `register(modEventBus)`（`Mekanism.java:229-262`）：

```java
MekanismItems.ITEMS.register(modEventBus);
MekanismBlocks.BLOCKS.register(modEventBus);
MekanismFluids.FLUIDS.register(modEventBus);
MekanismTileEntityTypes.TILE_ENTITY_TYPES.register(modEventBus);
MekanismChemicals.CHEMICALS.register(modEventBus);   // 自定义注册表
MekanismModules.MODULES.register(modEventBus);
```

自定义注册表用 `NewRegistryEvent` 单独注册（`Mekanism.java:264-269`）：`MekanismAPI.CHEMICAL_REGISTRY`、`CHEMICAL_INGREDIENT_TYPES`、`MODULE_REGISTRY`、`ROBIT_SKIN_SERIALIZER_REGISTRY`。

注册框架是**自研封装**：`MekanismDeferredRegister<T> extends DeferredRegister<T>`，覆写 `createHolder` 返回 `MekanismDeferredHolder`（`src/main/java/mekanism/common/registration/MekanismDeferredRegister.java`）；`registration/impl/` 下每种类型一个子类（`ItemDeferredRegister`、`BlockDeferredRegister`、`ChemicalDeferredRegister`、`FluidDeferredRegister`、`TileEntityTypeDeferredRegister`…）。关键在于**子类覆写 `register(IEventBus)` 顺带挂载事件监听**（`ItemDeferredRegister.java:36-56`）：注册物品的同时挂 `RegisterCapabilitiesEvent`、`RegisterEvent`(LOWEST，附加默认容器)、`ModifyDefaultComponentsEvent`。`BlockRegistryObject` 用 `DoubleWrappedRegistryObject<Block,BLOCK,Item,ITEM>` 把方块与物品持有者捆成一个"方块+物品"对象，直接实现 `ItemLike/IHasTextComponent`。

## 4. 核心系统

**(1) 能力系统（Capabilities）** — `src/main/java/mekanism/common/capabilities/Capabilities.java`
- `MultiTypeCapability<T>` 把 Block/Item/Entity 三态能力合并为单一常量：`ENERGY`/`FLUID`/`ITEM`/`CHEMICAL`/`STRICT_ENERGY`（`Capabilities.java:54-63`）
- 自建能力 ID：`chemical_handler`、`strict_energy_handler`、`heat_handler`、`configurable`、`alloy_interaction`、`config_card`、`laser_receptor`、`radiation`
- 代理注册：`TileEntityBoundingBlock.proxyCapability(event, …)` 让"占位方块"自动转发母方块能力（`Capabilities.java:103-115`）

**(2) 自定义能量单位：Strict Energy** — `src/api/java/mekanism/api/energy/IStrictEnergyHandler.java`
- API 用 `long` 存能量（`getEnergy/setEnergy/insertEnergy(int container,long,Action)`），不依赖 Forge 的 `int` FE；`src/main/java/mekanism/common/capabilities/energy/` 下按机器差异派生 `BasicEnergyContainer`/`MachineEnergyContainer`/`VariableCapacityEnergyContainer`/`LaserEnergyContainer`/`MinerEnergyContainer` 等，转换逻辑集中在 `EnergyCompatUtils`。

**(3) TileEntity 组件化** — `src/main/java/mekanism/common/tile/base/TileEntityMekanism.java`
- 抽象基类实现 `IFrequencyHandler, ITileDirectional, IConfigCardAccess, ITileActive, ITileSound…`（`:155`），持 `List<ITileComponent> components`（`:167`，注册入口 `addComponent` `:467`）
- `tickServer`（`:629`）内固定顺序驱动 `frequencyComponent`/`upgradeComponent`/chunkloader（`:640-645`），再跑子类 `onUpdateServer`；`ticker` 计数器（`:167`）供"每 N tick"节流
- 组件实现见 `tile/component/`：`TileComponentConfig`、`TileComponentUpgrade`、`TileComponentSecurity`、`TileComponentEjector`、`TileComponentChunkLoader`（后者还注册了 `TicketController`，`Mekanism.java:413`）

**(4) 多方块框架** — `src/main/java/mekanism/common/lib/multiblock/`
- `MultiblockManager<T>` + `MultiblockData` + `IStructureValidator` + `FormationProtocol` + `CuboidStructureValidator` + `StructureHelper`
- 5 个实例在 `Mekanism.java:166-170` 静态持有：`dynamicTank / inductionMatrix / thermoelectricBoiler / evaporation / sps`
- `MultiblockData` 直接实现 6 个 handler 接口（`MultiblockData.java:56`：`IMekanismInventory, IMekanismFluidHandler, IMekanismStrictEnergyHandler, ITileHeatHandler, IMekanismChemicalHandler`），因此多方块对外就是一个组合容器；`serverStopped` 时统一 `MultiblockManager.reset()`（`Mekanism.java:328`）

**(5) 自定义注册表数据驱动：化学/模块** — `src/api/java/mekanism/api/chemical/`、`common/registries/MekanismChemicals.java`
- 化学物质是一等注册表对象（`Chemical`/`ChemicalStack`/`ChemicalBuilder`/`IChemicalTank`/`IChemicalHandler`），`MekanismChemicals` 里以颜色常量 + `ChemicalConstants` 批量注册（`registerInfuse`/`register`）
- 装备模块（MekaSuit）走 `MekanismModules` + IMC：`MekanismIMC.addMekaSuitHelmetModules(...)` 等按槽位批量注入（`Mekanism.java:337-358`），处理在 `InterModProcessEvent` → `ModuleHelper.get().processIMC()`（`:360-362`）

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`src/main/java/mekanism/common/network/`（75 类）。`BasePacketHandler` 用模板方法强制子类实现 `registerClientToServer`/`registerServerToClient`，并自定义 `record PacketRegistrar(PayloadRegistrar, boolean toServer)` 包装 NeoForge 注册器，提供 `play/configuration/playInstanced` 三种注册方式（`BasePacketHandler.java:16-40`）。`PacketHandler` 按 `to_client/`、`to_server/` 分子包（再分 `configuration_update/filter/frequency/qio/robit/button`），并在构造器里注册 `RegisterConfigurationTasksEvent` 的 `SyncAllSecurityData` 配置阶段同步（`PacketHandler.java:64-69`）。高价值技巧：`registrar.playInstanced(id, handler)` 发"无负载"包（`showModeChange`/`killItemViewer`，`PacketHandler.java:151-160`）
- **配置**：`MekanismConfig.registerConfigs(modContainer)` + `modEventBus.addListener(MekanismConfig::onConfigLoad)`（`Mekanism.java:192/212`），并有 `common/config/listener` 做配置变更分发
- **DataMap**：`MekanismDataMapTypes.REGISTER` + `DataMapsUpdatedEvent` 回调把数据包数据刷进 `Chemical`（`Mekanism.java:261/297-301`），即"NBT 之外用 datapack 调化学属性"
- **datagen**：`src/datagen` 分 `main/additions/generators/tools` 四个源集，与四个模块一一对应；入口 `src/datagen/main/java/mekanism/common/MekanismDataGenerator.java`，provider 归 `common/{advancements,loot,recipe,registries,tag}` 与 `client/{lang,model,sound,state,texture}`，产物落到 `src/datagen/generated/`
- **Annotation Processor**：独立 Gradle 模块 `annotation-processor/src/main/java/mekanism/`（`MekAnnotationProcessors`、`ComputerMethodProcessor`、`MethodFactoryProcessor`），主工程 `compileOnly(project(':annotation-processor'))`，用于生成 CC/OC 的计算机外设方法

## 6. Mixin

**无。**全仓库 `src` 下不存在任何 mixin 配置文件或 mixin 类（`find src -name '*mixin*'` 无结果，`grep -rl mixin src/main/resources` 无结果）。所有对原版的介入都走 NeoForge 官方事件（`ItemAttributeModifierEvent`、`TagsUpdatedEvent`、`RegisterTicketControllersEvent` 等，`Mekanism.java:195-215`）与能力系统。

## 7. 值得学的 5 条具体做法

1. **用"多源集 + IModModule"代替多个 Gradle 子工程**：`build.gradle:57`（`secondaryModules = ['additions','generators','tools']`）为每个附属模块建独立源集、独立 @Mod 类与 datagen，但共享同一 `mekanism.common` 与注册框架 —— 适用"一个核心 + 若干可独立发布的附属模组"。
2. **把事件监听塞进 DeferredRegister 子类**：`ItemDeferredRegister.java:36-56` 中 `register(bus)` 顺带挂 `RegisterCapabilitiesEvent`/`ModifyDefaultComponentsEvent` —— 适用希望"注册物品即自动带能力/默认组件"的场合。
3. **MultiTypeCapability 折叠 block/item/entity 三态能力**：`Capabilities.java:54-63` —— 适用自建能力且需要同时支持方块、物品与实体的库。
4. **TileEntity 组件化基类**：`TileEntityMekanism.java:167/467/629` —— 适用大量机器共享"配置/升级/安全/自动输出"逻辑的科技 mod，避免继承树爆炸。
5. **能力代理（proxy）让占位方块透明转发**：`Capabilities.java:103-115` `TileEntityBoundingBlock.proxyCapability` —— 适用多方块/大体积机器用多个占位 BlockEntity 拼形状的场景。

## 8. 对外 API（平台 mod）

- API 包：`src/api/java/mekanism/api/`（265 个文件），根入口 `MekanismAPI.java`，服务注入用 `MekanismAPI.getService(Class)`；扩展点接口集中在 `IMekanismAccess`（`src/api/java/mekanism/api/IMekanismAccess.java`，提供 JEI/EMI helper 与 item/fluid/chemical stack ingredient creator）
- 接入方式：外部 mod 实现 `IModModule` 并调 `Mekanism.addModule()`；IMC 常量见 `MekanismIMC`（`addModuleContainer`/`addModulesToAll`/`addMekaSuitModules` 等）；自定义化学注册表 `MekanismAPI.CHEMICAL_REGISTRY`
- 数据生成支持：`src/api/java/mekanism/api/datagen`，第三方 recipe/模型生成可直接复用 Mekanism 的 provider 基类
