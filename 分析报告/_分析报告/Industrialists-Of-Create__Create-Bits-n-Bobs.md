# Create: Bits 'n' Bobs 源码分析报告

## 1. 基本信息

- Mod 名：Create Bits 'n' Bobs / `mod_id=bits_n_bobs` / 版本 2.3.4
- 作者：Cake, Kipti, NormalGuy, Astral, Spydnel（`gradle.properties:16`）
- 目标：MC 1.21.1 + NeoForge `21.1.248`（`neo_version_range=[21.1.236,)`），Parchment 2024.11.17
- 许可证：MIT；Gradle 插件：`net.neoforged.moddev 2.0.140`、`me.modmuss50.mod-publish-plugin`、`net.azmod.release 0.2.1`（`build.gradle:1-6`）
- 编译依赖（`build.gradle:113-158`）：Create `6.0.10-280`（**compileOnly + slim**）、Ponder `1.0.82`、Flywheel API、Registrate `MC1.21-1.3.0+67`、Veil `4.2.1`、**Azimuth 1.4.0 + Struts 1.2.2-SNAPSHOT（自家 maven `maven.azmod.net`，是其行为框架 API）**、`sable-companion` 走 `jarJar(api(...))`；CC:Tweaked / create-connected / slice-and-dice 等为 compileOnly 可选兼容。

## 2. 源码规模与包结构

310 个 `.java`，31489 行（实测 `find -name '*.java' | wc -l` + `xargs wc -l`）。

主要包（第 3-4 层，文件数）：`content/kinetics` 76、`content/decoration` 45、`content/trinkets` 30、`mixin` 25（另 `mixin/dyeable` 13、`mixin/compat` 5、`mixin/cogwheel_material` 3）、`registry/content` 13、`foundation/ponder` 11、`network/packets` 10、`registry/core` 9、`foundation/{config,client,caching,behaviour,generation}` 各 3-5。

最大文件：`BnbPaletteBlockPartial.java` 631、`NixieDisplayScenes.java` 604、`CogwheelChainBehaviour.java` 594、`CogwheelChainBehaviourRenderer.java` 588、`FlywheelBearingBlockEntity.java` 564、`HeadlampBlockEntity.java` 504、`CogwheelChainWholeShape.java` 428、`BnbFeatureFlag.java` 397、`CogwheelChain.java` 367。

## 3. 入口与注册

主类 `src/main/java/com/kipti/bnb/CreateBitsnBobs.java:41`。用 Create 的 `CreateRegistrate`（:49-54）统一注册并挂 Create 风格提示：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MOD_ID)
        .defaultCreativeTab((ResourceKey<CreativeModeTab>) null)
        .setTooltipModifierFactory(item -> new ItemDescription.Modifier(item, FontHelper.Palette.STANDARD_CREATE)
                .andThen(TooltipModifier.mapNull(KineticStats.create(item))));
```

构造器内按顺序调用各注册类（:70-92）：`BnbCreativeTabs / BnbDataComponents / BnbCogwheelChainTypes / BnbDataConditions`（mod bus）+ `BnbItems / BnbBlocksBootstrap / BnbEntityTypes / BnbBlockEntities / BnbTags / BnbPackets`（Registrate 惰性）。自定义注册类型用 NeoForge `RegistryBuilder`（`registry/core/BnbRegistries.java:15-25`，`COGWHEEL_CHAIN_TYPES`，`.sync(true)` 强制同步到客户端），键在 `BnbResourceKeys`。

## 4. 核心系统

**4.1 CogwheelChain（齿轮链传动，项目最大子系统）**
`content/kinetics/cogwheel_chain/` 含 13 个子包（graph/segment/shape/behaviour/render/riding/placement/edit/migration）。设计要点：
- **控制器 + 从属节点**：`behaviour/CogwheelChainBehaviour.java:41-52` 控制器持 `CogwheelChain controlledChain`，非控制器只存 `Vec3i controllerOffset` 做 "dumb integrity check"；`setLazyTickRate(20)` 低频校验，`checkIntegrityNextTick` 延迟标记。
- 链数据以自定义注册类型存 NBT：`graph/CogwheelChain.java:44-62` 用 `cogwheel_pos_count` + `cogwheel_pos_i` 索引键（避免 ListTag 版本兼容问题），`chain_type`/`returned_item` 存 ResourceLocation 而非枚举。
- 几何与渲染分离：`graph/CogwheelChainGeometryBuilder` 生成 `RenderedChainPathNode`，`cachedSegments` 惰性缓存。
- 与 Azimuth 行为框架深度绑定：`CogwheelChainBehaviour` 实现 `SuperBlockEntityBehaviour` + `KineticBehaviourExtension / RenderedBehaviourExtension / ItemRequirementBehaviourExtension`（可被蓝图/拆解正确回收物品）。

**4.2 FeatureFlag 特性开关体系**
`registry/core/BnbFeatureFlag.java` 是枚举，把"每个特性"映射到它引入的方块 Supplier（如 `CHAIN_PULLEY(BLOCK, "desc", CHAIN_PULLEY::get, CHAIN_ROPE::get, CHAIN_PULLEY_MAGNET::get)`），配 `FeatureCategories` / `BnbFeatureGroup` 归类。开关状态可直接用作数据包条件：`foundation/config/conditions/BnbFeatureEnabledCondition.java` 是 `ICondition` record，`CODEC` 用 `RecordCodecBuilder`（唯一字段 `feature`），`test()` 直接查 `BnbFeatureFlag.isEnabled(key)`——被禁用的特性连配方/进度都不会加载。

**4.3 装饰调色板系统**：`content/decoration` 45 文件 + `BnbPaletteBlockPartial`（631 行）+ `registry/worldgen/BnbPaletteStoneTypes`，用 partial 抽象批量派生"石种 × 形状"方块族；`AllPaletteStoneTypesMixin` 把自定义石种注入 Create 调色板。

**4.4 Trinkets 饰件**：`content/trinkets/light/headlamp/`（`HeadlampBlockEntity` 504 行 + `CCLightAddressing` 对接 CC:Tweaked 外设）、`nixie/`（`GenericNixieDisplayBlockEntity` + `SputnikDisplaySource` 式显示源抽象）、`chair/`（`ChairBlockStateGen` 367 行，配合 `mixin/chair/ContraptionMixin` 让椅子可被装置携带）。

**4.5 foundation 基础设施**：`BnbConfigBridge`、`BnbSuppression/SuppressionFilters`（屏蔽其它 mod 的 cogwheel 资源）、`caching`、`behaviour`、`generation`、`gui`，是跨系统复用的支撑层。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/BnbPackets.java` 实现 Catnip（Create/createmod）的 `BasePacketPayload.PacketTypeProvider`，枚举 6 个 C2S（`PlaceCogwheelChainPacket`、`WrenchCogwheelChainPacket`、`PartialEditCogwheelChainPacket`、`CogwheelChainRidingPacket`、`DragInteractionUpdatePacket`、`...QueueDisassembly`）+ 4 个 S2C（`ApplyHeadlampQueuedOperationsPacket`、`PeekCogwheelChainControllerHighlightPacket`、`CogwheelChainCarriageUpdateDistPacket`、`CogwheelChainRidingBroadcastPacket`），注册 `new CatnipPacketRegistry(MOD_ID, 1)`，负载名=枚举名小写。**"排队操作下发"模式**（`Apply*QueuedOperationsPacket`）用于 S2C 批量指令。
- 配置：沿用 Create 的 `ConfigBase`（catnip），`registry/core/BnbConfigs.java:31-58` 用 `EnumMap<ModConfig.Type, ConfigBase>`，`register(ModLoadingContext, ModContainer)` 注册 common/server 两档；`@EventBusSubscriber` 监听 `ModConfigEvent`。
- 数据驱动：`foundation/config/conditions/` 提供 `ICondition` 实现；`registry/datagen/BnbDataConditions` 注册条件编解码器；`registry/datagen/BnbLangEntries` + `foundation/BnbLang` 集中管理语言键；`CreateBitsnBobsData.gatherData` 在 datagen 时手动 `PonderIndex.addPlugin(new BnbPonderPlugin())`（因 FMLClientSetupEvent 不在 datagen 跑）再导出 Ponder 语言，`BnbAdvancements.dataProvider(...)` 通过 `generator.addProvider` 输出。

## 6. Mixin

配置 `src/main/resources/bits_n_bobs.mixins.json`：`package=com.kipti.bnb.mixin`，`plugin=com.kipti.bnb.mixin.BnbMixinPlugin`，`required=true`，`injectors.defaultRequire=1`；共约 40 个 common + 20 个 client mixin。

- **插件做可选依赖门控**（`mixin/BnbMixinPlugin.java:37-46`）：`shouldApplyMixin` 判断 mixin 类名是否以 `com.kipti.bnb.mixin.compat` 开头，再按子路径是否含 `create_connected / createadditionallogistics / createcasing` 决定是否 `isModLoaded`——**一个 mixin 可同时 target 多个可选 mod 的类，只对其中的可选目标做门控**（如 `CogwheelMaterialVisualMixin`）。
- 代表 mixin：`cogwheel_material.CogwheelMaterialVisualMixin`（Flywheel visual，改齿轮材质）、`dyeable.fluid_tank.FluidTankBlockEntityMixin` / `dyeable.pipes.FluidPipeBlockMixin`（让 Create 流体管道/储罐可染色）、`encasable_piston_poles.MechanicalPistonBlockMixin`、`AllCreatePonderScenesMixin`（改 Create 自带 Ponder 场景）、`RotationPropagatorMixin`、`BakedGlyphMixin` / `FontAccessMixin`（字体与字形）。
- `mixin_accessor/` 与 `*Accessor`（`PlayerSkyhookRendererAccessor`、`ConfigChangeAccessor`）用 Accessor 而非 @Redirect。

## 7. 值得学的 5 条做法

1. **行为（Behaviour）而非方块实体承载复杂逻辑**：`content/kinetics/cogwheel_chain/behaviour/CogwheelChainBehaviour.java`，逻辑挂到任意 `SmartBlockEntity` 上，天然支持与 Create 装置/蓝图交互——写 Create 附属时优先考虑。
2. **枚举式特性开关 + 数据包条件**：`registry/core/BnbFeatureFlag.java` + `foundation/config/conditions/BnbFeatureEnabledCondition.java`，一次定义即可同时控制物品栏可见性、配方加载与方块能力。
3. **MixinConfigPlugin 按包路径做可选 mod 门控**：`mixin/BnbMixinPlugin.java:37-46`，避免为每个兼容 mod 写一个独立 mixin 配置。
4. **自定义注册类型用 `RegistryBuilder().sync(true)`**：`registry/core/BnbRegistries.java:15`，数据驱动类型需要下发客户端时直接同步注册表，比手写包简单。
5. **datagen 中手动初始化 PonderIndex**：`CreateBitsnBobsData.java:24-30`，解决 Ponder 语言键不在 datagen 环境下注册的常见坑。

注：本 mod 非库模组，`registry/azimuth/BnbBehaviourApplicators` 暴露的注册点是给自家 Azimuth 行为框架用的内部扩展点，不构成对外 API。
