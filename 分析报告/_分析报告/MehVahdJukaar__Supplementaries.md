# Supplementaries 源码分析报告

## 1. 基本信息

| 项 | 值 | 来源 |
|---|---|---|
| Mod 名 / mod_id | Supplementaries / `supplementaries` | `gradle.properties` |
| 作者 | MehVahdJukaar, Plantkillable | `gradle.properties` |
| 版本 | 1.21.1-3.9.9 | `gradle.properties` |
| MC / Java | 1.21.1 / Java 21 | `gradle.properties` (`minecraft_version`, `java_version`) |
| 加载器 | NeoForge 21.1.248 + Fabric Loader 0.19.3 / Fabric API 0.116.15+1.21.1（单仓库三模块 common/fabric/neoforge） | `gradle.properties`, `settings.gradle.kts` |
| Gradle | Kotlin DSL；自研/私有插件 `com.possible-triangle.core|common|fabric|neoforge` v1.4 + `net.mehvahdjukaar.candlelight` v1.2.4；`org.gradle.daemon=false` | `settings.gradle.kts:1-12`, `build.gradle.kts:2-8` |
| 许可证 | Supplementaries Team License v1.5（自定义，All Rights Reserved，非开源许可） | `LICENSE.md:1-5` |
| 必选依赖 | **Moonlight（CurseForge 名 Selene）** `1.21.1-3.6.4`，min `1.21-3.6.4`；NeoForge `[21.1.247,)` | `neoforge/src/main/resources/META-INF/neoforge.mods.toml` |
| 编译期依赖 | `moonlight-common`（compileOnly + accessTransformers）、`mixinsquared-common/forge 0.1.1`（annotationProcessor）、`candlelight 1.2.6`；大量 `modCompileOnly`：Create/`mvn.createmod.net`、Flywheel、Registrate、JEI、EMI、Jade、REI、Curios、Trinkets、Farmer's Delight、Exposure、ImmediatelyFast、Sable-Companion（`modApi`） | `common/build.gradle.kts:19-74` |
| 声明的兼容约束 | Create（仅 NeoForge 侧启用）、Amendments、`farmersdelight <1.3.0` 不兼容、`sodium <0.8.12-beta.1` 不兼容、lithium `moving_block_shapes=false` | `neoforge.mods.toml` |

**分工**：Moonlight 提供平台抽象（`RegHelper`/`PlatHelper`/`ClientHelper`/`NetworkHelper`）、配置框架（`ConfigBuilder`）、木种/颜色 BlockSet API、软流体（SoftFluid）、动态资源包 API、`SimpleMixinPlugin`/`@OptionalMixin`、大量客户端渲染工具。Supplementaries 自身不写加载器抽象层，只写"内容 + 交互 + 渲染"。

## 2. 源码规模与包结构

- `.java` 文件 **1012** 个，总 **104,710** 行（`find . -name '*.java' | wc -l`；`-print0 | xargs -0 cat | wc -l`）
- 分模块：common **856** 文件 / **95,391** 行；neoforge **97** / **6,681**；fabric **59** / **2,638**
- common 内二级包文件数：`common/` 512、`client/` 166、`mixins/` 89、`integration/` 52、`reg/` 22、`dynamicpack/` 4、`configs/` 3、`api/` 3、`unused/` 2
- 三级分布：`common/block/blocks` **105** 文件、`common/block/tiles` **45**、`common/network` **38**、`client/renderers/tiles` 24、`client/screens` 14、`mixins/compat` 3

最大文件（行数）：`configs/CommonConfigs.java` 1399、`reg/ModRegistry.java` 1264、`client/renderers/entities/funny/SkibidiAnimations.java` 835、`common/misc/globe/GlobeTextureGenerator.java` 750、`reg/ModCreativeTabs.java` 649、`reg/ClientRegistry.java` 637、`common/block/tiles/CannonBlockTile.java` 631、`common/misc/mob_container/MobContainer.java` 623、`common/entities/HatStandEntity.java` 621、`common/misc/map_data/MapTintColorsHandler.java` 607、`common/network/ClientReceivers.java` 585。

## 3. 入口与注册

- **公共入口**：`common/src/main/java/net/mehvahdjukaar/supplementaries/Supplementaries.java:50` `commonInit()`，集中调用 20+ 个 `Xxx.init()`（`ModRegistry`、`ModEntities`、`ModNetwork`、`ModCreativeTabs`、`MapTintColorsHandler`、`DispenserBehaviorsManager` …），并在此注册 4 个服务端 reload listener 与动态资源包提供者。
- **NeoForge 入口**：`neoforge/src/main/java/net/mehvahdjukaar/supplementaries/platform/SupplementariesForge.java:26` `@Mod(Supplementaries.MOD_ID)`，构造器里只做加载器专属事：`Supplementaries.commonInit()`、`CapabilityHandler.init(bus)`、`ServerEventsForge.init()`、客户端分支 `ClientRegistry.init()/ClientEventsForge.init()`、`DeferredRegister` 注册 `IGlobalLootModifier`。
- **Fabric 入口**：`fabric/.../platform/SupplementariesFabric.java:15` `implements ModInitializer`，同样先 `commonInit()`，再挂 `ServerEventsFabric`/`ClientEventsFabric`。两个加载器入口各不足 40 行。
- **注册框架**：不使用原生 `DeferredRegister`（仅 NeoForge 专有的 loot modifier 用），全部走 Moonlight `RegHelper` 静态方法（`RegHelper.registerBlock/registerItem/registerBlockWithItem/registerBlockEntityType/registerDataAttachment/registerFullBlockSet`…）。`common/build.gradle.kts:24` 显示 Moonlight 只作 `modCompileOnly`，运行时由外部模组提供。

```java
// common/.../reg/RegUtils.java:100-117 —— 单行注册包装层
public static <T extends Block> RegSupplier<T> regBlock(String name, Supplier<T> sup) {
    return RegHelper.registerBlock(Supplementaries.res(name), sup);
}
public static <T extends Block> RegSupplier<T> regWithItem(String name, Supplier<T> blockFactory, Item.Properties properties) {
    RegSupplier<T> block = regBlock(name, blockFactory);
    regBlockItem(name, block, properties);
    return block;
}
```

`ModRegistry` 规模：`regWithItem(` 60 处、`regItem(` 52、`regBlock(` 51、`regTile(` 44。全部名字字符串集中在 `reg/ModConstants.java`，同时被配置项 key 复用（`builder.feature(ModConstants.WIND_VANE_NAME)`）。颜色/木种变体由工厂方法批量产出：`RegUtils.registerCandleHolders/registerBuntings/registerFlags/registerPresents/registerAwnings`（返回 `Map<DyeColor, Supplier<Block>>`），木种相关物品（way_sign、cannon_boat）走 `BlockSetAPI.addDynamicRegistration(...)`，遍历 `WoodTypeRegistry.INSTANCE` 注册（`RegUtils.java:52-58, 241-264`）。方块套件用 `RegHelper.registerFullBlockSet(res(name), Blocks.STONE_BRICKS)` 一行产出 stairs/slab/wall 等（`ModRegistry.java:973, 1017-1022`）。

## 4. 核心系统

### 4.1 配置驱动的注册/内容开关
`configs/CommonConfigs.java`（1399 行）用 Moonlight `ConfigBuilder.create(MOD_ID, ConfigType.COMMON_SYNCED)`，内部分 6 个静态嵌套类：`Redstone`/`Building`/`Functional`/`Tools`/`Tweaks`/`General`（行 188/359/662/925/1129/1367）。
- 每个功能一个 `builder.feature(name)` 叶节点（`CommonConfigs.java:341-349`），并提供全局查询 `CommonConfigs.isEnabled(String key)`（:111）。
- 该查询被注册成配方条件：`RegHelper.registerSimpleRecipeCondition(res("flag"), CommonConfigs::isEnabled)`（`Supplementaries.java:57`），从而用配置整体开关物品/配方/进度。
- 特性间有依赖链：`builder.dependsOn(Tools.ANTIQUE_INK_ENABLED).feature("sepia_globe")`（:566），注释明确要求初始化顺序（:58-60）。

### 4.2 数据驱动管理器（服务端 reload listener）
在 `Supplementaries.java:91-94` 用 `PlatHelper.addServerReloadListener(Supplier, ResourceLocation)` 一次性注册 4 个：`SongsManager`（`supplementaries:flute_songs`）、`HourglassTimesManager`（`hourglass_data`）、`FaucetBehaviorsManager`（`faucet_interactions`）、`CapturedMobHandler`（`catchable_mobs_properties`）；另有 `FireBehaviorsManager`、`PlaceableBookManager`、`DispenserBehaviorsManager` 由各自 `init()` 挂载。
- `HourglassTimesManager`（`common/block/hourglass/HourglassTimesManager.java:38`）继承 `SimpleJsonResourceReloadListener`，目录名 `"hourglass_dusts"`；用 Moonlight `SidedInstance` 做双端单例，数据解码用 `RegistryOps`，并有 `sendDataToClient(ServerPlayer)` 主动把整表同步给客户端（发包 `ClientBoundSendHourglassDataPacket`）。

### 4.3 网络层
`common/network/ModNetwork.java:7` 只有 3 行核心逻辑：`NetworkHelper.addNetworkRegistration(ModNetwork::registerMessages, 5)`（5 = 协议版本）。36 个数据包全部实现 Moonlight 的 `Message` 接口，用 `Message.makeType(res("..."), Ctor::new)` 声明 codec，`handle(Context)` 转派到 `ClientReceivers`（585 行）—— 分类注册：23 clientBound、10 serverBound、4 bidirectional。示例 `ClientBoundSyncAntiqueInk`（38 行）用 record + `TypeAndCodec`。同步策略分层：偶然事件用一次性数据包（如 `ClientBoundParticlePacket`、`ClientBoundSendKnockbackPacket`），持久玩家状态用数据附件（下节），方块实体状态另有 16 个 tile 覆写 `getUpdatePacket/getUpdateTag`。

### 4.4 数据附件 / 世界存档数据
`reg/ModData.java` 把加载器差异封进 Moonlight：`RegHelper.registerDataAttachment(res("slimed_data"), () -> RegHelper.AttachmentBuilder.create(SlimedData::new).syncWith(SlimedData.STREAM_CODEC).persistent(SlimedData.CODEC), LivingEntity.class)` 同时指定同步流 codec 与持久 codec；`registerWorldSavedData` 注册 `COOPERATIVE_PULLEYS`、`GLOBE_DATA`（`GlobeData.CODEC` + `STREAM_CODEC`）。Slime 黏液效果即通过 `ModData.SLIMED_DATA.getOrCreate(livingEntity)` 在 mixin 中写入。

### 4.5 客户端注册与自定义烘焙模型
`reg/ClientRegistry.java:166-198` 把 15 类客户端注册一次性委托给 Moonlight `ClientHelper`（`addEntityRenderersRegistration`、`addBlockEntityRenderersRegistration`、`addModelLoaderRegistration`、`addItemDecoratorsRegistration`、`addShaderRegistration`…），`init()` 只登记回调，`setup()` 才执行；`ClientHelper.addClientReloadListener` 另挂 3 个客户端数据管理器（`MobHeadShadersManager`、`FlowerBoxModelsManager`、`PlaceableBookManagerClient`）。渲染类型按方块逐个 `ClientHelper.registerRenderType(block, RenderType.cutout())`（:200-260，含 `values().forEach` 批量处理 16 色变体）。
- 自定义模型加载器/烘焙模型在 `client/block_models/`（15 个类，如 `SignPostBlockBakedModel`、`RopeKnotBlockBakedModel`、`JarModelLoader`），配合 Moonlight `NestedModelLoader` 做"方块状态驱动的模型拼装"（栅栏连接、绳索节点、钟表指针）。

### 4.6 兼容层
`integration/CompatHandler.java` 用 ~100 个 `public static final boolean XXX = isLoaded("modid")` 常量做静态能力探测（含 `PlatHelper.getPlatform().isFabric()` 分支，如 `CREATE` 在 Fabric 强制 false，:31-33），`CompatHandlerClient` 对应客户端侧。每个具体模组一个包装类（AmendmentsCompat、QuarkCompat、SableCompat、FlywheelCompat…），加载器专属实现放 `*/integration/platform/*Impl.java`。Create 集成（`neoforge/src/main/java/.../integration/create/`）用 DisplaySource/DisplayTarget 成对实现：`ClockDisplaySource`、`GlobeDisplaySource`、`NoticeBoardDisplaySource/Target`、`BlackboardDisplayTarget`。

### 4.7 交互行为覆盖表
`common/events/overrides/InteractEventsHandler.java:44-49` 维护四张 `IdentityHashMap`：`ITEM_USE_ON_BLOCK_HP`(高优先级)、`ITEM_USE_ON_BLOCK`、`ITEM_USE`、`BLOCK_USE`，键为 `Item`/`Block` 实例，值为 `ItemUseOnBlockBehavior`/`BlockUseBehavior` 等接口实现（17 个类，如 `SoapBehavior`、`WrenchBehavior`、`ThrowableBricksBehavior`）；`registerOverrides(HolderLookup.Provider)` 在每次数据重载时 `clear()` 后重建，保证注册与 tag 一致。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：见 4.3。统一由 Moonlight `NetworkHelper` 注册，自带协议版本号（每次加包需递增）。
- **数据驱动**：JSON 资源位于 `common/src/main/resources/assets/`（资源）与玩家数据包路径（reload listener 目录 `hourglass_dusts`、`faucet_interactions`、`catchable_mobs_properties`、`flute_songs`）；`api/ICatchableMob.java` 是给外部 mod 实现/复制的接口（注释明确"你可以把这个类复制到你的 mod 里实现"）。
- **配置**：Moonlight `ConfigBuilder`，`COMMON_SYNCED` 类型（服务端配置自动同步客户端）；`CommonConfigs` + `ClientConfigs` 分侧，`configs/ConfigUtils.java` + 各模块 `configs/platform/ConfigUtilsImpl.java` 处理加载器差异。
- **datagen**：**无**。仓库内不存在任何 `DataGenerator`/`GatherDataEvent` 类，三个 `build.gradle` 也无 datagen 配置；取而代之是运行时动态资源包生成：`dynamicpack/ModServerDynamicResources.java`（合成标签、合成 lang 等）与 `ModClientDynamicResources.java` 继承 Moonlight `DynamicServerResourceProvider`，用 `RegHelper.registerDynamicResourceProvider(...)` 注册（`Supplementaries.java:89,97`），生成策略由 `CommonConfigs.General.DYNAMIC_ASSETS_GEN_MODE`（`GenMode`）决定，dev 环境下 `PackGenerationStrategy.CACHED`。
- **访问扩宽**：`common/src/main/resources/supplementaries.accesswidener`，用 `common { accessWidener() }` 应用（`common/build.gradle.kts:6-9`）。仓库同时使用 AT（`accessTransformers("...moonlight-common")`）。

## 6. Mixin

配置文件 3 个，两个加载器共用一套插件：
- `common/src/main/resources/supplementaries-common.mixins.json`：package `net.mehvahdjukaar.supplementaries.mixins`，`compatibilityLevel: JAVA_17`，mixins 62 个 / client 26 个，`overwrites.conformVisibility: true`
- `neoforge/src/main/resources/supplementaries.mixins.json`（package `...mixins.neoforge`，含 `self/` 子包 11 个）
- `fabric/src/main/resources/supplementaries.mixins.json`（package `...mixins.fabric`，18 个类，含 `MC263524FixMixin`、`BiomeAccessor` 等加载器缺陷绕过）
- 三者都指定 `"plugin": "net.mehvahdjukaar.supplementaries.mixins.MixinPlugin"`——该类只有 6 行，`extends SimpleMixinPlugin`（Moonlight），配合 `@OptionalMixin` 做条件加载；`mixinextras.minVersion 0.5.3`

代表性 mixin 与注入点：
- `mixins/SlimeMixin.java:26` `@Inject(method="dealDamage", at=@At(value="INVOKE", target="Lnet/minecraft/world/entity/monster/Slime;playSound(Lnet/minecraft/sounds/SoundEvent;FF)V"))` —— 在放音那一瞬给对方实体挂 `SLIMED_DATA`，并用 `ModTags.CAN_SLIME` + `CommonConfigs.Tweaks.SLIMED_PER_SIZE` 双重门控；注入方法名统一 `supp$` 前缀。
- `mixins/compat/CompatCreeperArclightMixin.java:22-24` `@OptionalMixin(value="io.izzel.arclight.common.mixin.core.world.entity.monster.CreeperMixin")` + `@Unique private boolean supplementaries$festive`，用 mixinextras `@WrapWithCondition` 包裹 vanilla 逻辑；这是"只在该 mod 存在时才应用"的标准写法。
- `neoforge/.../mixins/neoforge/self/SelfFrameMixin.java`：`@Mixin(FrameBlock.class)` 但目标是**自己的类**，通过覆写 `getEnchantPowerBonus` 让框架方块透传内部方块附魔能力 —— 因为 NeoForge 给方块加了接口默认方法，只能靠 mixin 注入自身类。

## 7. 值得学的 5 条具体做法

1. **注册薄包装层 + 名字常量双用**：`RegUtils.regBlock/regItem/regTile/regWithItem` 四行一物的包装（`common/.../reg/RegUtils.java:92-117`），名字全部来自 `ModConstants`，同一常量同时喂给注册与配置 key，避免字符串漂移。适用：任何注册量大的内容 mod。
2. **用配置叶节点当功能开关 + 注册为配方条件**：`builder.feature(name)` 生成可开关功能，再 `RegHelper.registerSimpleRecipeCondition(res("flag"), CommonConfigs::isEnabled)` 让被禁用的东西不出现配方/进度（`Supplementaries.java:57`，`CommonConfigs.java:341-349`）。适用：想做"高可配置"的 mod。
3. **用动态资源包生成替代 datagen**：`dynamicpack/ModServerDynamicResources` + `RegHelper.registerDynamicResourceProvider`，运行时按当前注册表和配置合成标签/资源（`Supplementaries.java:89-97`）。适用：需要在运行时按配置组合资源、或想让资源随其它 mod 数据变化的场景。
4. **兼容探测集中常量 + `@OptionalMixin`**：`CompatHandler` 只用 `isLoaded("id")` 常量声明能力，mixins 用 `@OptionalMixin(value="target.Class")` 标注依赖目标类存在，`MixinPlugin extends SimpleMixinPlugin` 统一裁决（`integration/CompatHandler.java:22-60`、`mixins/compat/CompatCreeperArclightMixin.java:24`）。适用：多加载器 + 大量可选兼容。
5. **loader 差异靠 `platform/` 包隔离，入口文件极小**：公共逻辑全在 common（`commonInit()`），加载器特化只有 `platform/SupplementariesForge`（`@Mod`，含 `ItemAbility`、`DeferredRegister<IGlobalLootModifier>`、Capability）与 `platform/SupplementariesFabric`（`ModInitializer`），平台接口实现全部放 `*/platform/*Impl.java`。适用：多加载器共用一套代码库时的目录约定。

## 8. 公开 API 与外部接入（非纯库 mod，但有扩展点）

- `api/` 包（3 个文件）：`ICatchableMob`（实体可实现或提供 capability，注释明确允许"复制进你的 mod"）、`CapturedMobInstance`、`IFireItemBehaviorProvider`。
- 外部接入的主渠道是**数据 + 标签 + 月光的注册事件**而非 Java API：软流体交互、faucet 交互、可捕获生物属性、沙漏沙数据、笛子歌曲均为 JSON 数据包条目；`ModTags` 定义了大量 `CAN_SLIME` 之类的行为标签；NeoForge 侧另有 `api/platform/RegisterFireBehaviorsEvent` 自定义事件。
- 未确认项：Moonlight 侧的 `SimpleMixinPlugin`/`RegHelper` 具体实现不在本仓库，需要读 Moonlight 源码才能确认其内部注册时机与裁决规则。
