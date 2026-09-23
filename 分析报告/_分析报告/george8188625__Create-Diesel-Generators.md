# george8188625 / Create-Diesel-Generators 源码分析

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 | Create Diesel Generators |
| mod_id | `createdieselgenerators` |
| 作者 | George VI |
| 版本 | 1.21.1-1.3.15 |
| 目标 MC / 加载器 | Minecraft 1.21.1 / **NeoForge 21.1.228**（`neo_version_range=[21.1.174,)`，`loader_version_range=[1,)`） |
| Gradle 插件 | `net.neoforged.moddev` 2.0.89（neoForge 块配置 runs/mods，非旧的 ForgeGradle） |
| Java | toolchain 21 |
| 许可证 | MIT |
| group | `com.jesz.createdieselgenerators` |
| 映射 | Parchment 1.21.1 / 2024.11.17 |

编译依赖（`gradle.properties:19-39`、`build.gradle:87-135`）：
- **Create 6.0.10-280**（`create_version_range=[6.0.7,6.1.0)`，`slim` 分类器，`transitive=false`）——它同时是 API 与运行宿主
- Ponder 1.0.82、Flywheel 1.0.6（api = compileOnly，实现 = runtimeOnly；标准 Create 附属写法）
- **Registrate MC1.21-1.3.0+67**（注册框架）+ `com.tterrag.registrate` 的 `RegistryEntry`
- JEI 19.21.2.313（implementation）、CC:Tweaked 1.116.1（compileOnly core-api + forge-api，runtime 完整版）
- KubeJS（`curse.maven:kubejs` compileOnly）+ Rhino（implementation，用于 KubeJS 脚本回调）
- Architectury API、Selene/moonlight（curse，用于 EveryCompat 兼容）
- Sable / Aeronautics / Simulated / Offroad（`dev.ryanhcode.*`），并对 **sable-companion 使用 jarJar 打包**
- `annotationProcessor org.spongepowered:mixin:0.8.5:processor`，注解处理器可选
- `jar { manifest.attributes(["MixinConfigs": "${mod_id}.mixins.json"]) }`（`build.gradle:194-198`）

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` → **200 个 .java，共 21284 行**（`src/main/java` 下）。

主要包（`com/jesz/createdieselgenerators/` 下的直接子包，文件数为该包及子包）：

| 包 | 文件数 | 内容 |
|---|---|---|
| （根） | 19 | `CreateDieselGenerators`、`CDGBlocks/CDGItems/CDGFluids/CDGBlockEntityTypes/CDGEntityTypes/CDGMenuTypes/CDGRecipes/CDGConfig/CDGDataComponents/CDGDisplaySources/CDGMountedStorageTypes/CDGRegistries/CDGTags/CDGSoundEvents/CDGPartialModels/CDGRecipes/...` |
| `content/*` | 约 110 | 每个内容一个子包：`diesel_engine/{normal,modular,huge}`、`distillation`、`bulk_fermenter`、`pumpjack`(16)、`oil_barrel`、`turret`、`entity_filter`(7)、`molds`、`canister`、`tools/{hammer,lighter,wire_cutters}`、`track_layers_bag`、`sheetmetal` 等 |
| `mixins` | 15 | 见第 6 节 |
| `compat` | — | `computercraft/peripherals`、`jei`、`kubejs`、`strut_your_stuff`（+ 根级 `EveryCompatCompat`） |
| `ponder` | 8 | 8 个 Ponder 场景（`DieselEngineScenes` 319 行、`PumpjackScene` 261 行、`TurretScenes` 等） |
| `events` | 2+1 | `GameEvents`(271)、`ModEvents`、`events/datagen/CDGRecipeProvider` |
| `packets` | 2 | `CDGPackets`、`EntityFilterScreenPacket` |
| `contraption` | 3 | `*MovementBehaviour`（蒸汽/泵机在动态结构上的行为） |
| `world` | 1 | `OilChunksSavedData` |
| 其他 | 少量 | `fuel_type`(1)、`mixin_interfaces`(1)、`commands`(1) |

最大文件：`content/distillation/DistillationTankBlockEntity.java`(881)、`content/bulk_fermenter/BulkFermenterBlockEntity.java`(828)、`content/track_layers_bag/TrackLayersBagPlacement.java`(798)、`content/diesel_engine/modular/ModularDieselEngineBlockEntity.java`(474)、`CDGBlocks.java`(435)、`content/oil_barrel/OilBarrelBlockEntity.java`(386)、`huge/HugeDieselEngineBlockEntity.java`(323)。

注意：仓库中 `src/main/resources` **只含 `createdieselgenerators.mixins.json`**，无 assets/data/lang；`src/generated/resources` 为空目录。即这是一个"纯代码"快照，模型/配方/语言文件未随仓库提供。模组元数据来自 `src/main/templates/neoforge.mods.toml`（占位符由 `generateModMetadata` 任务展开，`build.gradle:137-166`），其中 `[[mixins]] config="${mod_id}.mixins.json"`，并对 `create` 声明 required、对 `struts` 声明 optional。

## 3. 入口与注册

主类 `src/main/java/com/jesz/createdieselgenerators/CreateDieselGenerators.java:32-43`：

```java
@Mod(ID)
public class CreateDieselGenerators {
    public static final String ID = "createdieselgenerators";
    public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(ID)
        .setTooltipModifierFactory(item -> new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)
                .andThen(TooltipModifier.mapNull(KineticStats.create(item))));
    public CreateDieselGenerators(IEventBus modEventBus, ModContainer container) {
        REGISTRATE.defaultCreativeTab((ResourceKey<CreativeModeTab>) null);
        REGISTRATE.registerEventListeners(modEventBus);
        ...
```

组织方式：**Create 版 Registrate**（`com.simibubi.create.foundation.data.CreateRegistrate`）+ 每个注册类别一个 `CDG*` 静态类，构造函数里顺序调用其 `register()`（`:45-58`）：`CDGItems / CDGBlocks / CDGFluids / CDGBlockEntityTypes / CDGEntityTypes / CDGSoundEvents(bus) / CDGRecipes(bus) / CDGMenuTypes / MoldType / CDGMountedStorageTypes / CDGCreativeTab(bus) / CDGPackets / CDGDataComponents(bus) / CDGDisplaySources`。

条件注册模式值得抄：`CreateDieselGenerators.java:59-66` 用 `if (ModList.get().isLoaded("struts")) ...`、`Mods.COMPUTERCRAFT.executeIfInstalled(() -> CCProxy::register)`、`CatnipServices.PLATFORM.executeOnClientOnly(() -> () -> onClient(...))`；配置在 `:67-68,73` 分 SERVER/COMMON/CLIENT 三份注册（`CDGConfig.*_SPEC`）。

Create 6 新 API 的接入示例：`CDGDisplaySources.java:12` 用 `REGISTRATE.displaySource(name, PumpjackOilAmountDisplaySource::new)` 注册仪表盘数据源；`CDGMountedStorageTypes.java:12` 用 `REGISTRATE.mountedFluidStorage(...)` 注册挂载式流体存储（动态结构上的油桶）。

## 4. 核心系统

**(1) 数据包驱动的燃料类型（最值得学）**
- 职责：把"哪种流体=什么性能"完全外置为数据包注册表，而不是硬编码 enum。
- `CDGRegistries.java:9` 定义 `ResourceKey<Registry<FuelType>> FUEL_TYPE`；`events/ModEvents.java:94-100` 用 `DataPackRegistryEvent.NewRegistry#dataPackRegistry(FUEL_TYPE, FuelType.CODEC, FuelType.NCODEC)` 注册同步。
- `fuel_type/FuelType.java:15-35`：`record FuelType(HolderSet<Fluid> fluid, PerEngineProperties normal/modular/huge, float soundPitch, float burnerStrength)`；**双 Codec**：`CODEC`（存档用，`RegistryCodecs.homogeneousList(Registries.FLUID)` 允许用 tag 引用）与 `NCODEC`（**网络同步用**，`getter` 处把 HolderSet 转成 `HolderSet.direct(...)` 全量列表）。注释明确说明原因：客户端加入服务器时还没有 tag 数据，用 NCODEC 避免报错——这是 1.21 自定义注册表同步的经典坑。
- 查询入口 `FuelType.getTypeFor(lookup, fluid)`（`:49-55`）用 `fluid.builtInRegistryHolder()` 逐个 `contains` 匹配，查不到返回 `EMPTY` 常量（`:37`）；调用方统一 `level.registryAccess().lookupOrThrow(CDGRegistries.FUEL_TYPE)`（见 `content/burner/BurnerBlockEntity.java:51`、`content/tools/lighter/LighterItem.java:65` 等十余处）。

**(2) 引擎燃料缓存（IEngine）**
- `content/diesel_engine/IEngine.java:12-67`：接口给三种引擎（normal/modular/huge）共用。`getFuelType()` 在 `FluidStack.isSameFluid(current, getLastCachedFluid())` 为假时才重算，并一次性缓存 speed/capacity/burnRate（`:38-51`）；`getFuelSpeed/getFuelCapacity/getFuelBurnRate` 是 default 方法，先 `getFuelType()` 再返回缓存。避免每 tick 查注册表。
- `FuelType.getGenerated(BlockEntity)`（`FuelType.java:41-47`）用 `instanceof` 分派到 normal/modular/huge 三套参数。

**(3) 多方块蒸馏塔（复刻 Create 流体罐）**
- `content/distillation/DistillationTankBlockEntity.java:59` `extends SmartBlockEntity implements IMultiBlockEntityContainer.Fluid, IHaveGoggleInformation, IHaveHoveringInformation`，`:60` `MAX_SIZE = 3`；直接复用 Create 的 `ConnectivityHandler`、`SmartFluidTank`、`IMultiBlockEntityContainer` 体系，是本仓库最大文件（881 行）。

**(4) 油泵（Pumpjack）与动态结构行为**
- `content/pumpjack/PumpjackBearingBlockEntity.java:22 extends MechanicalBearingBlockEntity`（复用 Create 的轴承动力学）；配套 `PumpjackCrankValueBox`（数值框）、`PumpjackHoleRenderer`、`PumpjackHoleGenerator`。
- `contraption/` 下 `PumpjackBearingBMovementBehaviour`、`PumpjackHeadMovementBehaviour`、`DieselEngineMovementBehaviour` 实现动态结构（列车/轴承）上的行为。
- `content/track_layers_bag/TrackLayersBagPlacement.java`(798) 负责轨道铺设的**预放置计算**（`placeTracks(...)` at `:498`），把"预览-放置"逻辑从 Item 中抽出独立类——`TrackLayersBagItem`(294) 只负责交互。

**(5) 实体属性过滤器（扩展 Create 的 AbstractFilterMenu）**
- `content/entity_filter/` 7 个文件：`EntityFilterMenu extends AbstractFilterMenu`（`EntityFilterMenu.java:28`），`EntityAttribute` 为接口 + `Codec`/`StreamCodec`（`EntityAttribute.java:26-38`），带 `enum StandardTraits implements EntityAttribute`（`:99`）与 `record EntityAttributeEntry(EntityAttribute, boolean inverted)`（`:209`）；`EntityFilteringBehaviour`/`EntityFilteringRenderer` 把它接到方块/渲染；`ReverseLootTable` 借助 mixin 的 LootTableAccessor 反查战利品表。
- 网络侧只有一条包 `EntityFilterScreenPacket`，`record ... implements ServerboundPacketPayload`，用 `StreamCodec.composite(Option.STREAM_CODEC, ..., EntityAttribute.STREAM_CODEC, ...)`，`handle(ServerPlayer player)` 里直接改 `player.containerMenu` 的服务端字段（`packets/EntityFilterScreenPacket.java:19-45`）。

**(6) 区块级油田（世界数据）**
- `world/OilChunksSavedData.java` `extends SavedData`，`Map<ChunkPos,Integer> chunks` 手动 NBT 序列化（`:31-44`）；产油量 = `PerlinNoise.create(RandomSource.create(seed), List.of(-2,-1,0,1))` + 生物群系标签判定（`CDGTags.OIL_BIOMES` / `DENY_OIL_BIOMES`，`:55-71`），并预留 `CDGKubeJSPlugin.calculateOilChunks(biomes, chunk, seed)` 供脚本覆写。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：不用 NeoForge 原生 `RegisterPayloadHandlersEvent`，而是 **Create 6 的 Catnip 包框架**。`packets/CDGPackets.java` 是一个 `enum implements BasePacketPayload.PacketTypeProvider`，构造时把每个包登记为 `CatnipPacketRegistry.PacketType<>(CustomPacketPayload.Type<>(rl(name)), clazz, codec)`；`register()` 里 `new CatnipPacketRegistry(ID, 1)` → 逐包 `registerPacket` → `registerAllPackets()`。包体是 `record` + `StreamCodec.composite`，方向由实现 `ServerboundPacketPayload`/`ClientboundPacketPayload` 决定，`handle(ServerPlayer)` 收口。版本号 `1` 直接写在注册处。
- **数据驱动**：自定义数据包注册表 `fuel_type`（见 4.1），`DataPackRegistryEvent` 注册 + 双 Codec 同步。原版数据包内容（配方/标签）不在仓库中。
- **配置**：`CDGConfig` 手写 `ModConfigSpec`（`CDGConfig.java:10-12` 三个 SPEC），SERVER/COMMON/CLIENT 分别在主类 `:67-68`（容器注册）与 `:73`（客户端）注册，含"Normal/Modular/Huge Diesel Engines"开关、涡轮增压倍率、燃料 tooltip 开关等。
- **datagen**：仅一个 `events/datagen/CDGRecipeProvider`（`ModEvents.java` 中通过 `event.addProvider(new CDGRecipeProvider(packOutput, lookupProvider))` 挂到 `GatherDataEvent`），其余资源靠手写/外部。

## 6. Mixin

- 配置：`src/main/resources/createdieselgenerators.mixins.json`——`required:true`、`minVersion 0.8`、**`priority: 1177`**（远高于默认 1000，用于压在 Create 之上）、`refmap: createdieselgenerators.refmap.json`、`compatibilityLevel: JAVA_17`、`package com.jesz.createdieselgenerators.mixins`、`injectors.defaultRequire:1`。**12 个通用 mixin + 3 个 client**：通用 `BasinRecipeMixin, ContraptionMixin, CopycatBlockMixin, CreeperMixin, EntityMixin, LootItemAccessor, LootPoolAccessor, LootTableAccessor, MechanicalPressBlockEntityMixin, ShaftBlockMixin, UseOnContextInvoker, SableAssemblyMixin`；client `AgeableListModelAccessor, BasinRendererMixin, ModelPartAccessor`。
- 命名约定清晰：`*Accessor`/`*Invoker` 走 `@Accessor`/`@Invoker` 拿 Create 的私有成员，`*Mixin` 做注入（如 `LootItemAccessor` 被 `GameEvents` 用来改战利品池）。
- 代表：`mixins/ShaftBlockMixin.java:14-21`，`@Inject(method = "pickCorrectShaftType", at = @At("HEAD"), remap = false, cancellable = true)` 到 Create 的 `ShaftBlock`，命中时 `cir.setReturnValue(PoweredEngineShaftBlock.getEquivalent(stateForPlacement))`——用 Create 自己的方法名挂接，`remap=false` 因为是 Create 的方法。
- **条件 mixin**：`CDGMixinPlugin.java` 实现 `IMixinConfigPlugin`，`shouldApplyMixin` 中当 `sable` 模组未加载时返回 false 跳过 `SableAssemblyMixin`（`LoadingModList.get().getModFileById("sable") == null`）。注意：mixin 插件必须在 mixin 配置 JSON 中以 `"plugin": "<全限定类名>"` 声明，而本仓库 `createdieselgenerators.mixins.json` 中**没有 `plugin` 字段**，`build.gradle` 也无相关引用（`grep` 无命中）——该 plugin 在当前快照中疑似未生效（死代码），若需软依赖裁剪务必补上 `"plugin"` 字段。

## 7. 值得学的 5 条做法

1. **自定义注册表用"双 Codec"解决 tag 同步问题**：存档 Codec 允许 tag 引用、网络 Codec 展开成直接列表，注释直接写明原因——任何把 tag 放进同步注册表的 mod 都会踩这个坑。`fuel_type/FuelType.java:17-35`。
2. **用 Create 的 Catnip 包框架替代裸 NeoForge 网络**：`enum implements PacketTypeProvider` + `CatnipPacketRegistry`，一个枚举集中管理 ID/类型/Codec，新增包只加一行枚举值。`packets/CDGPackets.java:13-40`。
3. **能力/数据源注册走 Registrate 的 Create 扩展方法**：`REGISTRATE.displaySource(...)`、`REGISTRATE.mountedFluidStorage(...)`，避免手写 `DeferredRegister` 与 RegistryKey 拼接。`CDGDisplaySources.java:12`、`CDGMountedStorageTypes.java:12`。
4. **热路径数据用"失效比较式缓存"**：`IEngine.getFuelType()` 只在 `FluidStack` 变化时重查注册表，其它时刻读缓存的 speed/burnRate。`content/diesel_engine/IEngine.java:38-51`。
5. **给 mixin 配 `IMixinConfigPlugin` 做软依赖裁剪**：按 `LoadingModList` 判断可选模组是否加载来决定是否应用对应 mixin（本仓库用于 sable）。`CDGMixinPlugin.java:27-32`。

## 8. 公开 API / 扩展点

非库模组。对外扩展点：`CDGRegistries.FUEL_TYPE` 数据包注册表（第三方可用 JSON 定义燃料，字段 `fluid/normal/modular/huge/sound_pitch/burner_multiplier`）；`compat/kubejs` 下的 `CDGKubeJSPlugin`（含 `calculateOilChunks` 覆写点）；`compat/strut_your_stuff/StrutYourStuffRegistryEntries`（第三方模组联动注册入口）。
