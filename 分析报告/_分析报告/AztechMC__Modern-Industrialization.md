# AztechMC/Modern-Industrialization 源码分析报告

> 注：本仓库本地不存在（`_参考仓库/_bulk/AztechMC__Modern-Industrialization` 为空），分析时从 GitHub 克隆默认分支 **1.21.x**（commit `e0b405a1`）到上述路径。

## 1. 基本信息

- Mod 名：Modern Industrialization；mod_id `modern_industrialization`；作者 Azerococo、Technici4n（`src/main/templates/META-INF/neoforge.mods.toml`）
- 目标：Minecraft **1.21.1** + **NeoForge 21.1.219**（`gradle.properties`），Parchment 2024.07.28
- Gradle 插件：`net.neoforged.moddev` 2.0.112 + `dev.lukebemish.immaculate`（代码风格）+ `net.neoforged.licenser` + `mod-publish-plugin`；`java-library`，group `aztech`
- 许可证：**MIT**
- 编译依赖（`build.gradle` dependencies 块）：
  - **必需**：`api jarJar("dev.technici4n:GrandPower:3.0.0")`——它不是库 mod，而是**直接把能量 API 抽成外部库 GrandPower**（`ILongEnergyStorage`），自己 `api + jarJar` 引入（`api/energy/EnergyApi.java:41-45` 明说"与 GrandPower 同类型，仅 EU 换算比可配"）
  - **必需**：`implementation "org.appliedenergistics:guideme:21.1.5"`——指南书用 AE2 团队的 GuideME 渲染
  - `api "org.jspecify:jspecify:1.0.0"`（API 包带空安全注解）
  - 可选：JEI / REI / EMI（`runtime_itemlist_mod` 开关决定 dev 运行时用哪个）、Jade、AE2、KubeJS、AlmostUnified、Argonauts、Athena、FTB Quests/Teams
- 它的"API"是 `src/main/java/aztech/modern_industrialization/api/` 包（26 个类）

## 2. 源码规模与包结构

实测（`find -name '*.java' | wc -l` / `xargs cat | wc -l`）：

| sourceSet | 文件数 | 行数 |
|---|---|---|
| src/main/java | 610 | 59,231 |
| src/client/java | 178 | 18,672 |
| 合计 | **788** | **77,903** |

采用 **NeoForge split client sourceSet**（`src/client/java`）+ `src/generated`（生成资源）。

主要包（main，文件数）：`machines/components` 25、`materials/part` 20、`util` 19、`items` 19、`nuclear` 18、`inventory` 18、`machines/guicomponents` 15、`machines/blockentities` 15、`datagen/recipe` 13、`network/machines` 12、`machines/blockentities/multiblocks` 12、`thirdparty/fabrictransfer/api/storage` 11、`machines/recipe` 11、`compat/kubejs/recipe` 11、`pipes/*` 约 30、`compat/*` 约 40。

最大文件：`machines/components/CrafterComponent.java`(891)、`machines/init/MultiblockMachines.java`(803)、`materials/MIMaterials.java`(753)、`pipes/impl/PipeBlockEntity.java`(686)、`MITooltips.java`(590)、`items/SteamDrillItem.java`(575)。

## 3. 入口与注册

主类 `src/main/java/aztech/modern_industrialization/MI.java:104-282`，构造 `(ModContainer, IEventBus, Dist)`：

```java
@Mod(MI.ID)
public MI(ModContainer modContainer, IEventBus modBus, Dist dist) {
    modContainer.registerConfig(ModConfig.Type.SERVER, MIServerConfig.SPEC);
    modContainer.registerConfig(ModConfig.Type.STARTUP, MIStartupConfig.SPEC);
    KubeJSProxy.checkThatKubeJsIsLoaded();
    MIAdvancementTriggers.init(modBus); MIComponents.init(modBus); MIFluids.init(modBus);
    MIBlock.init(modBus); MIItem.init(modBus); MIRegistries.init(modBus);
    MIMaterials.init();                                       // 材料 → 生成全部物品/方块/配方
    MIMachineRecipeTypes.init(); SingleBlockCraftingMachines.init(); MultiblockHatches.init();
    MultiblockMachines.init(); KubeJSProxy.instance.fireRegisterMachinesEvent();
    MIPipes.INSTANCE.setup(); ...
}
```

注册框架：NeoForge **`DeferredRegister.Blocks` / `DeferredRegister.Items`**（`MIBlock.java:72`、`MIItem.java:57`）外面再套一层自定义 `BlockDefinition<T>` / `ItemDefinition<T>`（`definition/` 包），并存入 `SortedMap<ResourceLocation, BlockDefinition<?>> BLOCK_DEFINITIONS = new TreeMap<>()`（`MIBlock.java:73`，TreeMap 保证遍历顺序稳定）。同时 `Definition.TRANSLATABLE_DEFINITION` 静态收集所有带英文名的定义，供 datagen 的 `TranslationProvider` 直接产出 lang 文件（`definition/Definition.java:34-50`）。

## 4. 核心系统

**(1) 机器组件化体系**（`machines/`，25 个组件）
- `MachineBlockEntity extends FastBlockEntity`，持有两个容器：`ComponentStorage.GuiServer guiComponents` 与 `ComponentStorage.Server components`（`MachineBlockEntity.java:75-78`），`registerComponents(MachineComponent...)` 统一注册
- `MachineComponent` 接口只要求 4 个方法，且把"存档同步"与"客户端同步"分开：`writeNbt/readNbt(tag, registries, boolean isUpgradingMachine)` 与 `writeClientNbt/readClientNbt`，并有 `ClientOnly` / `ServerOnly` 子接口（`machines/MachineComponent.java`）
- 24 个内建组件：`CrafterComponent`（配方加工核心，891 行）、`EnergyComponent`、`FluidStorageComponent`、`MachineInventoryComponent`、`UpgradeComponent`、`OverclockComponent`、`RedstoneControlComponent`、`TemperatureComponent`、`ShapeValidComponent`、`ActiveShapeComponent`、`SteamHeaterComponent`、`NeutronHistoryComponent` 等
- 对外只暴露 `api/machine/component/{Crafter,Energy,Fluid,Item,Inventory}Access` 与 `api/machine/holder/*ComponentHolder`，附属 mod 通过 holder 读机器状态而不碰实现

**(2) 多方块形状系统**（`machines/multiblocks/`）
- `ShapeTemplate`：`Map<BlockPos, SimpleMember> simpleMembers` + `Map<BlockPos, HatchFlags> hatchFlags` + `MachineCasing hatchCasing`；Builder 提供 `add3by3`、`add3by3Levels`、`add3by3LevelsRoofed`，以及 **`LayeredBuilder` 用 `String[][] layers` + `key(char, SimpleMember, HatchFlags)` 字符画定义结构**（`ShapeTemplate.java:108-180`）
- `ShapeMatcher implements ChunkEventListener`：按区块监听变化逐步匹配，`toWorldPos/toTemplateState` 做模板↔世界坐标转换，匹配到的 `HatchBlockEntity` 依 `HatchFlags.allows(hatch.getHatchType())` 归位（`ShapeMatcher.java:46-167`）
- `HatchType`/`HatchTypes`/`HatchFlags` 抽象"输入仓/输出仓/能量仓"等插槽语义

**(3) 通用管道网络 API**（`pipes/api/`）
- `PipeNetworkManager`（442 行）：一个 level 一个管理器，`Map<BlockPos, PipeNetwork>` + `Map<BlockPos, Set<Direction>> links`，用 **DFS 做网络合并/拆分**（`addLink/removeLink` 内 `class Dfs`）
- `spannedChunks` + `updateTickingChunks/notifyTickingChanged`：只在有节点的区块 tick，闲置网络不耗 tick
- 网络整体 NBT 序列化（`toTag/fromNbt`）+ `nextNetworkId` 稳定 ID
- 物品/流体传输基于**内嵌的 Fabric Transfer API**（`thirdparty/fabrictransfer/`），API 层通过 `pipes/api/{PipeNetworkNode,PipeNetworkData,PipeEndpointType,PipeMenuProvider}` 暴露

**(4) 材料系统（MI 最独特处）**（`materials/`）
- `Material` + `MaterialBuilder` + `MaterialRegistry`，`MIMaterials` 声明 100+ 材料（铁/铜/不锈钢/钛/铀…）
- `part/` 20 个类定义"材料部件"：`MIParts`、`PartTemplate`、`MaterialItemPart`/`MaterialItemPartImpl`、`CasingPart`、`CablePart`、`OrePart`、`RawMetalPart`、`BarrelPart`、`TankPart`、`BatteryPart`、`NuclearFuelPart`、`ControlRodPart`；`PartKey`/`PartKeyProvider` 做部件标识，`PartEnglishNameFormatter`/`PartItemPathFormatter` 统一命名，`TextureGenParams` 驱动纹理生成
- `set/`（`MaterialSet`、`MaterialBlockSet`、`MaterialOreSet`、`MaterialRawSet`）+ `property/`（`MaterialProperty`、`MaterialHardness`）描述材料族
- `recipe/` 用 `MaterialRecipeBuilder`/`MIRecipeBuilder`/`ForgeHammerRecipeBuilder`/`StandardRecipes` 把配方也一起批量生成
- 结论：**一处声明材料 → 自动产出物品/方块/模型/纹理/配方/翻译**

**(5) 能量 API**（`api/energy/`）
- `EnergyApi` 基于 NeoForge Capability（`EnergyApi.SIDED`、`EnergyApi.ITEM`、`EnergyApi.BLOCK`），内部类型是 GrandPower 的 `ILongEnergyStorage`（long 级能量，避免 int 溢出）；`CableTier`/`CableTierHolder` 定义线缆等级，`MIEnergyStorage` 做适配

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络（`network/MIPackets.java`）：`registrar("1")` 版本化通道；静态 `registrations` 列表 + `register(String path, Class<P>, StreamCodec)`，并用 `Map<Class<? extends BasePacket>, CustomPacketPayload.Type<?>> packetTypes` 反查；全部 `playBidirectional`，由 `BasePacket.Context`（含 `clazz` 与 `PacketContext`）做 handler 分发。`BasePacket` 抽象基类 + `MIStreamCodecs` 共享编解码器；包分 `network/machines`、`network/pipes`、`network/armor`
- 数据驱动：NeoForge **DataMaps**——`RegisterDataMapTypesEvent` 注册 `MIDataMaps.FLUID_FUELS`（流体燃料值）、`ITEM_PIPE_UPGRADES`、`MACHINE_UPGRADES`、`ITEM_TOOLTIPS`
- 配置：`MIServerConfig`（SERVER）+ `MIStartupConfig`（STARTUP，含 `datagenOnStartup`、`loadRuntimeGeneratedResources`、`loadAe2Compat`）
- 配置/兼容开关驱动的行为在构造器里直接读（`MIStartupConfig.INSTANCE.loadAe2Compat()` → `MIAEAddon.init(modBus)`）
- **运行时 datagen**（很值得学）：`AddPackFindersEvent` 里，若 `MIStartupConfig.datagenOnStartup` 为真则在服务端启动时跑 `RuntimeDataGen.run(MIDatagenServer::configure)`，把数据生成到 `gamedir/modern_industrialization/runtime_datagen`；同时若 `loadRuntimeGeneratedResources` 为真，用自定义 `GeneratedPathPackResources extends FastPathPackResources`（`resource/GeneratedPathPackResources.java:39`）把 `gamedir/modern_industrialization/generated_resources` 注册成内置数据包。同一套 provider 通过 `build.gradle` 的 `runtimeDatagen` 布尔参数复用（`MIDatagenServer.configure(gen, helper, lookup, run, runtimeDatagen)`，`MI.java:226-233`）
- datagen 结构：`MIDatagenServer` 用 `AggregateDataProvider`（"Server Data"）把 12 个配方 provider 聚合（Petrochem/Plank/HeatExchanger/Hatch/Alloy/Material/Dye/Assembler/Compat/Upgrade/VanillaCompat/资源），另有 loot、`DatapackBuiltinEntriesProvider`（动态注册表）、tags、DataMap、translation、advancement、structure；client 侧 `client/datagen/{model,texture}` 生成模型与纹理
- 测试：`RegisterGameTestsEvent` 注册 `MIGameTests`；自带 `test/framework/MIGameTestHelper extends GameTestHelper`，提供 `pipe(...)`+`PipeBuilder`、`assertEnergy`、`assertFluid`、`requireCapability` 等断言封装（`test/framework/MIGameTestHelper.java:50-133`），测试类 `GeneratorTests`、`MultiblockTests`、`FluidPipeTests`

## 6. Mixin

- `src/main/resources/modern_industrialization.mixins.json`：package `aztech.modern_industrialization.mixin`，仅 1 个 mixin `BlockStateBaseMixin`，`injectors.defaultRequire=1`，`required: true`
- `src/main/java/aztech/modern_industrialization/mixin/BlockStateBaseMixin.java:37-39`：`@Mixin(BlockBehaviour.BlockStateBase.class)` + `@Inject(method = "getDestroyProgress", at = @At("HEAD"), cancellable = true)`——按玩家手持工具自定义挖掘速度
- 另存在 `src/client/resources/modern_industrialization.client_mixins.json`，内容声明 `mixin.client.BlockMixin`，但**该 .java 文件在 1.21.x 检出中不存在**，且 `neoforge.mods.toml:15-16` 只声明了 main 配置——判断为遗留/未生效文件（原文事实，未确认其历史用途）
- 整体结论：MI 几乎不用 mixin，倾向用 NeoForge 事件 + 能力 + DataMap 替代

## 7. 值得学的 5 条具体做法

1. **把能量 API 抽成外部库再 `api + jarJar` 引入**：`api jarJar("dev.technici4n:GrandPower")`（`build.gradle` dependencies），本 mod 只做 EU 换算适配（`api/energy/EnergyApi.java:41-45`）；好处是能量 API 可跨 mod 版本复用、避免"API 与实现同生命周期"
2. **Definition 包装 + TreeMap 注册表 + 翻译自动收集**：所有方块/物品走 `BlockDefinition`/`ItemDefinition` 并进入 `SortedMap`，`Definition.TRANSLATABLE_DEFINITION` 顺带喂给 `TranslationProvider` 生成 lang（`MIBlock.java:72-73`、`definition/Definition.java:34-50`）；适合物品数 500+ 的科技 mod
3. **机器 = 组件容器，存档与客户端同步分离**：`ComponentStorage.Server/GuiServer` + `MachineComponent` 的 `writeNbt/readNbt` vs `writeClientNbt/readClientNbt` + `ClientOnly/ServerOnly`（`machines/MachineBlockEntity.java:75-78`、`machines/MachineComponent.java`）；解决"大 BE 一个 NBT 方法分支爆炸"
4. **多方块用字符画模板 + 区块事件增量匹配**：`ShapeTemplate.LayeredBuilder(String[][] layers).key(char, ...)` + `ShapeMatcher implements ChunkEventListener`（`ShapeTemplate.java:108-180`、`ShapeMatcher.java:46`）；适合机器形状多、且要动态增删仓口的场合
5. **同一套 datagen provider 支持"启动期运行时生成"**：`configure(..., boolean runtimeDatagen)` 布尔穿透 + `RuntimeDataGen` + `GeneratedPathPackResources` 注册成内置包（`misc/runtime_datagen/RuntimeDataGen.java`、`MI.java:249-275`）；适合"数据依赖配置/其它 mod 内容、无法离线生成"的整合包场景

## 8. 公开 API

- API 包：`aztech.modern_industrialization.api`（26 类），子包 `energy`（`EnergyApi`、`CableTier`、`MIEnergyStorage`）、`machine.component`（`Crafter/Energy/Fluid/Item/InventoryAccess`）、`machine.holder`（5 个 `*ComponentHolder`）、`datamaps`（`MIDataMaps`、`FluidFuel`、`ItemPipeUpgrade`、`MachineUpgrade`、`ItemTooltip`）
- 管道 API：`pipes/api/`（`PipeNetworkManager`、`PipeNetwork`、`PipeNetworkNode`、`PipeNetworkData`、`PipeNetworkType`、`PipeEndpointType`、`PipeMenuProvider`）
- 扩展方式：KubeJS 脚本绑定（`compat/kubejs/`：`machine/`、`material/`、`recipe/`、`registration/`，入口 `KubeJSProxy.checkThatKubeJsIsLoaded()` + `fireRegisterMachinesEvent()`，`MI.java:117,133`）；DataMap 数据包（4 种）与 datagen provider 也是外部接入点
