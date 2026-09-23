# Minecraft Mod 开发学习指南 —— 基于《璇穹之歌》整合包开源仓库

> 配套文件：
> - `整合包Mod-GitHub对照表.md` / `.csv` —— 386 个 mod 中 298 个的公开源码地址（全部经 `git ls-remote` 验证）
> - `源码库/_参考仓库/` —— 已克隆的全部仓库源码（本汇总文件夹内），本文所有代码引用都能在里面直接打开
>
> 目标环境：Minecraft **1.21.1 / NeoForge**（你现有的 hivecolony 工程）；同时兼顾你的 1.20.1 Forge 工程（CaerulaArbor）。

---

## 目录

1. [工程脚手架：三种构建方式的实际对比](#1-工程脚手架三种构建方式的实际对比)
2. [Mod 入口与注册：从 20 行主类学组织](#2-mod-入口与注册从-20-行主类学组织)
3. [事件系统：两条总线的分工](#3-事件系统两条总线的分工)
4. [网络通信：1.21 的 CustomPacketPayload 三种典型用法](#4-网络通信121-的-custompacketpayload-三种典型用法)
5. [数据驱动与 datagen：1.21 新增的注册扩展点](#5-数据驱动与-datagen121-新增的注册扩展点)
6. [方块、方块实体与容器](#6-方块方块实体与容器)
7. [实体与 AI：Brain 体系实战（对你的蜂群工程最有用）](#7-实体与-ai大脑体系实战对你的蜂群工程最有用)
8. [客户端渲染与 UI](#8-客户端渲染与-ui)
9. [Mixin 工程化：FerriteCore 的教科书做法](#9-mixin-工程化ferritecore-的教科书做法)
10. [配置系统：从内置界面到自定义框架](#10-配置系统从内置界面到自定义框架)
11. [库 / API 设计：如果你要写前置模组](#11-库--api-设计如果你要写前置模组)
12. [工程化：GameTest、CI、发布、自动升级](#12-工程化gametestci发布自动升级)
13. [推荐阅读路径](#13-推荐阅读路径)

---

## 1. 工程脚手架：三种构建方式的实际对比

整合包里的 mod 覆盖了当前所有主流的 NeoForge 构建方案，逐个对比比看教程更直接：

| 方案 | 代表仓库 | build.gradle 关键点 |
|---|---|---|
| `net.neoforged.moddev` 2.x（**当前首选**） | FarmersDelight、TouhouLittleMaid、createaddition、FerriteCore、你自己的 hivecolony | `neoForge { version = ...; runs { client/data/gameTestServer } }`，无 ForgeGradle 的 `fg.deobf` |
| `net.neoforged.gradle.userdev` 7.x | L2Library | 老式 userdev，仍用 `implementation "net.neoforged:neoforge:..."` |
| ForgeGradle（1.20.1 及更早） | 你的 CaerulaArbor | `fg.deobf(...)`、`mappings channel: 'official'` |

要点：

- **moddev 插件自带 run 配置生成**：FarmersDelight 的 `build.gradle` 里有 `client/data/gameTestServer` 三种 run，data run 是 datagen 的运行入口（见 `FarmersDelight/build.gradle:51-84`）。
- **parchment 参数化映射**（两套工程都在用）：`parchment_minecraft_version=1.21.1` + `parchment_mappings_version=2024.07.28`，让反编译参数名可读，调试源码时体验差别巨大。
- **多加载器工程**是进阶内容，两个范本：
  - **FerriteCore**：`settings.gradle` 里 `include("Common","Fabric","NeoForge")`，根目录 `buildSrc/` 放两个约定插件；`ferritecore.loader-conventions.gradle` 用 `source(project(":Common").sourceSets.main.allSource)` 把 Common 源码并入加载器子项目，mod 元数据由 `src/main/templates` 经 `generateModMetadata` 展开（见 `FerriteCore/buildSrc/src/main/groovy/`）。这是"一份逻辑、两套加载器"的最干净做法。
  - **Jade / AppleSkin**：单源集 + `mod-publish-plugin`，靠 `apiJar` 任务只导出 `api` 包；Jade 用 `fabric.mod.json` 的 `jade` 自定义 entrypoint 加载插件（见 `Jade/build.gradle`）。
- **jarJar 嵌套依赖**（NeoForge 特有）：L2Library 用 `jarJar.enable()` 把 l2serial/l2core/l2tabs 等子模块打进包（`L2Library/build.gradle`）；TouhouLittleMaid 用 `shadowJar` + relocate 把 snakeyaml 等库重定位到 `touhoulittlemaid.libs.*`（`TouhouLittleMaid/build.gradle`）。写前置/库模组时必学。

## 2. Mod 入口与注册：从 20 行主类学组织

FarmersDelight 主类（`FarmersDelight/src/main/java/vectorwing/farmersdelight/FarmersDelight.java`，完整文件不到 70 行）是"大 mod 主类只做编排"的范例：

```java
@Mod(FarmersDelight.MODID)
public class FarmersDelight {
    public FarmersDelight(IEventBus modEventBus, ModContainer modContainer) {
        modEventBus.addListener(CommonSetup::init);
        if (FMLEnvironment.dist.isClient()) {                       // 客户端逻辑隔离
            modEventBus.addListener(ClientSetupEvents::init);
            modContainer.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new);
        }
        modContainer.registerConfig(ModConfig.Type.COMMON, Configuration.COMMON_CONFIG);
        modContainer.registerConfig(ModConfig.Type.CLIENT, Configuration.CLIENT_CONFIG);
        ModSounds.SOUNDS.register(modEventBus);                     // 每个 registry 一行
        ModBlocks.BLOCKS.register(modEventBus);
        ModItems.ITEMS.register(modEventBus);
        ModDataComponents.DATA_COMPONENTS.register(modEventBus);
        ModEntityTypes.ENTITIES.register(modEventBus);
        ModBlockEntityTypes.TILES.register(modEventBus);
        ...
        NeoForge.EVENT_BUS.addListener(VillageStructures::addNewVillageBuilding);
    }
}
```

值得抄的细节：

- **注册类按类型拆分**：`common/registry/` 下 20+ 个类（`ModBlocks` / `ModItems` / `ModEntityTypes` / `ModMenuTypes` / `ModRecipeTypes` / `ModLootModifiers` / `ModDataComponents` / `ModIngredientTypes`…），每个类一个 `DeferredRegister`，主类只负责 `.register(modEventBus)`。
- **NeoForge 便捷工厂**（你的 hivecolony 已在用）：`DeferredRegister.createItems(MODID)` / `createBlocks(MODID)` 省去手写 `Registries.ITEM`。
- **1.21 的注册面比 1.20.1 宽**：`ModDataComponents`（数据组件）、`ModIngredientTypes`（自定义合成原料类型）、`ModConditionCodecs`、`ModLootModifiers` 都是 1.21 新增，`FarmersDelight.java` 里一次性全部能看到注册方式。
- **Registrate 风格**：createaddition 用 Create 的 `CreateRegistrate`（`createaddition/src/main/java/com/mrh0/createaddition/CreateAddition.java:66`），按"方块+物品+模型+掉落+配方"一键成套注册，适合 Create 附属拖管线式内容。
- **AI 相关的扩展注册**（对你的蜂群工程直接有用）：TouhouLittleMaid 的 `init/InitEntities.java` 除了注册 `ENTITY_TYPES`，还注册 `ACTIVITIES` / `MEMORY_MODULE_TYPES` / `SENSOR_TYPES` / `SCHEDULES` / `DATA_SERIALIZERS`、`ATTRIBUTES`、`POI_TYPES` —— 即自定义 Brain 需要注册的全部类型。

## 3. 事件系统：两条总线的分工

- **mod bus**（`IEventBus`，构造器注入）：注册、模型烘焙、datagen、配置等"加载期"事件。FD 用 `modEventBus.addListener(CommonSetup::init)`；TLM 用 `eventBus.addListener(NetworkHandler::registerPacket, InitCapabilities::registerGenericItemHandlers)`。
- **`NeoForge.EVENT_BUS`**（游戏总线）：游戏运行期事件（玩家交互、tick、服务器生命周期）。FD 的示例：`NeoForge.EVENT_BUS.addListener(VillageStructures::addNewVillageBuilding)`。
- **静态订阅**：TLM 的 datagen 入口 `datagen/DataGenerator.java` 直接标 `@EventBusSubscriber` + `GatherDataEvent`；L2Library 的 `events/MiscServerEventHandler.java` 同理。
- **客户端隔离两种写法**：`FMLEnvironment.dist.isClient()` 分支（FD）或独立 `Client` 类 + `@OnlyIn(Dist.CLIENT)`（TLM 网络 handler 用后者）。

## 4. 网络通信：1.21 的 CustomPacketPayload 三种典型用法

### 4.1 最小无参包（FD）

`FarmersDelight/common/network/payload/FlipSkilletPayload.java` 全文：

```java
public record FlipSkilletPayload() implements CustomPacketPayload {
    public static final ResourceLocation ID = ResourceLocation.fromNamespaceAndPath(FarmersDelight.MODID, "flip_skillet");
    public static final FlipSkilletPayload INSTANCE = new FlipSkilletPayload();
    public static final Type<FlipSkilletPayload> TYPE = new Type<>(ID);
    public static final StreamCodec<RegistryFriendlyByteBuf, FlipSkilletPayload> STREAM_CODEC = StreamCodec.unit(INSTANCE);
    @Override public @NotNull Type<? extends CustomPacketPayload> type() { return TYPE; }
}
```

注册（`common/network/ModNetworking.java`）：

```java
public static void registerPayloadHandlers(RegisterPayloadHandlersEvent event) {
    final PayloadRegistrar registrar = event.registrar("1");            // 版本号 "1"
    registrar.playToClient(RichSoilBoostParticlesPayload.TYPE, RichSoilBoostParticlesPayload.STREAM_CODEC,
                           ClientPayloadHandler::handleRichSoilBoostParticles);
    registrar.playToServer(FlipSkilletPayload.TYPE, FlipSkilletPayload.STREAM_CODEC,
                           ServerPayloadHandler::handleFlipSkillet);
}
```

**规律**：包 = record implements CustomPacketPayload；`TYPE` + `STREAM_CODEC` 两个静态常量；handler 拆 Client/Server 两个类；注册集中在 `ModNetworking`。

### 4.2 请求-应答 + 大数据量保护（Jade）

Jade 的 tooltip 数据是"客户端请求 → 服务端应答"模式（`Jade/network/`）：`RequestBlockPacket` / `RequestEntityPacket`（C2S）、`ReceiveDataPacket`（S2C）、`ServerPingPacket` / `ShowOverlayPacket`。注意 `ReceiveDataPacket` 内置 **16KB 上限**，超限时 `removeLargest()` 裁剪 —— 同步自定义数据时这是必做的保护。

### 4.3 变化才发 / 组织大量包

- **AppleSkin**（`AppleSkin/java/squeek/appleskin/network/SyncHandler.java`）：饱和度有变化就发，消耗度差值 ≥0.01 才发，登录时清缓存。**同步频率控制**的经典写法。
- **TouhouLittleMaid**：`network/NetworkHandler.java` 里约 60 条 `playToServer/playToClient` 注册，包按 `network/message/` 与 `network/message/ai/` 分目录；发送封装统一走 `PacketDistributor.sendToPlayer / sendToPlayersTrackingEntityAndSelf / sendToPlayersNear`。**包多了以后必须有的目录结构**。
- **createaddition**：`network/ObservePacketPayload` + `IObserveBlockEntity` 接口，把"客户端观测 BE 数值"做成通用协议，配合 `EnergyNetworkPacketPayload` 同步能量状态 —— 适合参照到动力/机器类 mod。
- 你的 hivecolony 已经在用 `PayloadRegistrar`；下一步可以借鉴 Jade 的请求-应答拆分和 TLM 的分目录组织。

## 5. 数据驱动与 datagen：1.21 新增的注册扩展点

### 5.1 完整的 datagen 管线（FD）

`FarmersDelight/data/` 目录就是一份"该生成什么"的清单：

```
DataGenerators.java     ← GatherDataEvent 入口, 组装所有 provider
BlockStates.java  ItemModels.java  SoundDefinitions.java     ← 客户端资源
Recipes.java  advancement/  recipe/                          ← 配方与进度
BlockTags.java  ItemTags.java  EntityTags.java  DamageTypeTags.java  EnchantmentTags.java
LootModifiers.java  loot/  ModEnchantments.java
DataMaps.java                                                ← 1.21 新增 data map
```

主类里那些 `ModXxx` 注册类与 datagen 一一对应。**建议**：你的工程如果还没把 datagen 做成"每次改内容跑一次 data run"，这是投入产出比最高的补齐项。

### 5.2 1.21 的四个新注册面（都在 FD/TLM 里有范例）

| 扩展点 | FD 范例 | 说明 |
|---|---|---|
| DataComponent（物品数据组件） | `registry/ModDataComponents.java`、`common/item/component/` | 取代 NBT 的官方方案，1.21 自定义物品必学 |
| DataMap（原版注册表的附加数据） | `data/DataMaps.java`、TLM `DataMapGenerator`（ParrotImitation） | 不改原版注册表就能给方块/实体挂数据 |
| LootModifier（全局掉落修改） | `registry/ModLootModifiers.java`、`data/LootModifiers.java` | 不需要写 mixin 就能改掉落 |
| IngredientType / ConditionCodec | `registry/ModIngredientTypes.java`、`ModConditionCodecs.java` | 自定义配方原料与条件 |

### 5.3 自定义数据包 ReloadListener（TLM 的 skills 系统）

TLM 的 `datapack/resources/SkillsDataReloadListener.java` 扫描数据包里 `data/touhou_little_maid/skills/*/skill.md`，用正则解析成技能定义；`BoardStateDataReloadListener`、`KaomojiDataReloadListener` 同类。**把内容做成数据包文件**（而不是硬编码）是大型 mod 的可维护性关键，也是整合包作者最喜欢的特性。

### 5.4 注册新注册表（库模组用）

L2Library 的 `l2core/init/reg/simple/Reg.java` 提供 `dataReg`（走 `DataPackRegistryEvent.NewRegistry`，数据包驱动的注册表）、`dataMap`、`newRegistry` 三种注册封装；配合 `SimpleJsonResourceReloadListener` + `OnDatapackSyncEvent` 做同步。**当你需要"整合包可配置的内容注册表"时，这就是模板。**

## 6. 方块、方块实体与容器

- **完整链条**（FD）：`ModBlocks` → `ModBlockEntityTypes.TILES` → `ModMenuTypes.MENU_TYPES` → `common/block/entity/container/` 下的 Container 实现（`CookingPotBlockEntity` 等）。做带 GUI 的机器时按这条链抄。
- **每玩家状态**（Lootr，`源码库/_参考仓库/Lootr`）：源码按 `common/` 与 `neoforge/` 分包——`common/block`、`common/loot`、`common/data` 放逻辑，`neoforge/block/entity`、`neoforge/network/toClient` 放加载器相关；配合 `common/mixins/` 修改原版箱子行为。**"同一功能要按玩家区分实例"时的架构参考**（你的蜂群殖民地里每个玩家的殖民地状态同理）。
- **动力机器**（createaddition）：每个机器一个包（`blocks/rolling_mill/`、`blocks/alternator/`），包内固定四件套：`XxxBlock` + `XxxBlockEntity` + `XxxRenderer`(BER) + `XxxVisual`(Flywheel 可视化) + `package-info.java`。写 Create 附属直接套这个结构。

## 7. 实体与 AI：Brain 体系实战（对你的蜂群工程最有用）

TouhouLittleMaid 是整合包里 AI 最复杂的开源实体 mod，结构（`entity/` 包）：

```
entity/passive/EntityMaid.java        ← extends TamableAnimal implements CrossbowAttackMob, IMaid
entity/ai/brain/MaidBrain.java        ← registerBrainGoals: 分层注册 Core/Panic/Ride/Idle/Work/Rest
entity/ai/brain/{sensor,task}/        ← 自定义 Sensor 与 Behavior
entity/ai/goal/                       ← 少量传统 Goal (FairyAttackGoal 等)
entity/ai/control|navigation|path|ride/ ← 移动控制分层
entity/task/TaskManager.java          ← 上层"任务系统": 注册 IMaidTask (TaskAttack/TaskNormalFarm/TaskFishing)
```

要点：

1. **双轨制**：底层用原版 `Brain`（MemoryModule + Sensor + Activity + Behavior），上层再包一层可插拔的 "Task" 抽象（`IMaidTask`），把"女仆在做什么工作"与"底层行为树"解耦。你的 `AtomicBehaviorLibrary` / `BehaviorChainSpec` 相当于自研了后一层 —— 对比 TLM 的做法，可以看到"tasks 注册进 registry 由数据驱动选择"的另一种设计。
2. **自定义 Brain 类型全部要注册**：`InitEntities.java` 里 `ACTIVITIES`、`MEMORY_MODULE_TYPES`、`SENSOR_TYPES`、`SCHEDULES`、`DATA_SERIALIZERS`、`POI_TYPES` 一览（前面第 2 节）。
3. **属性注册**：`InitAttribute.ATTRIBUTES` + `EntityAttributeCreationEvent`（TLM 亦有）。
4. **动画**：TLM 甚至自带 fork 的 `geckolib3/` 包（core/geo/model/util），客户端用 `GeckoMaidEntity implements IGeoEntity` 桥接，模型从资源包/自定义包加载（`client/resource/GeckoModelLoader.java`、`BedrockModelLoader.java`、`CustomPackLoader.java`）—— 想学"模型不由 jar 内置、而由玩家资源包提供"的高级玩法看这里。
5. 其他值得参考的实体 mod（对照表里有仓库）：`AlexModGuy/AlexsMobs`、`AlexModGuy/AlexsCaves`、`0999312/umapyoi`（赛马娘，数据驱动角色）、`Minecraft-LightLand/L2Hostility`（怪物词条系统）。

## 8. 客户端渲染与 UI

- **Jade**（`源码库/_参考仓库/Jade`）：
  - 世界内选取目标 **不靠 mixin**，而是每 tick 用自研 `overlay/RayTracing.java` 做射线检测收集 tooltip，再用 Fabric 的 `HudRenderCallback` + `ScreenEvents.afterRender` 绘制（`util/ClientProxy.java:304-358`）。**思路**：能靠 API 轮询解决的，不动字节码。
  - 少数必要 mixin 都是"事件覆盖不到的地方"：`BossHealthOverlayMixin`（隐藏 Boss 血条）、`ClientLevelMixin`（缓存玩家名）。
  - 插件 API：`snownee.jade.api` 包（`IWailaPlugin`、`IWailaClientRegistration.registerBlockComponent`、`IBlockComponentProvider`、`IJadeProvider`），外部 mod 通过 entrypoint 注册并按 `@WailaPlugin(modid)` 校验、**禁止 `snownee.jade.*` 被冒充**（`util/CommonProxy.java:445`）。写公共 API 时这套"注解声明 + 归属校验"值得直接抄。
- **AppleSkin**（`源码库/_参考仓库/AppleSkin`）：
  - HUD 用 mixin 精确 hook：`mixin/InGameHudMixin.java` 注入 `renderFood` 的 HEAD/RETURN 与 `renderHealthBar` 的 RETURN（旧版直接改渲染方法，是最典型的 HUD mixin 场景）。
  - Tooltip 扩展：`TooltipOverlayHandler` 里 `FoodOverlay` 同时实现 `TooltipComponent` 与 `TooltipData`，再用 `TooltipComponentMixin` 把原版 `OrderedText` 换成自定义组件 —— **1.21 tooltip 扩展的标准做法**。
  - 对外 API 事件：`api/event/FoodValuesEvent.java`（改显示数值）、`api/event/HUDOverlayEvent.java`（可取消各 HUD 元素）；`api/AppleSkinApi.java` 走 entrypoint 注册。**"侵入性功能做成事件给其他 mod 关掉"的礼貌设计。**
- **L2Library 的 UI 框架**：`l2core/base/menu/`（`BaseContainerMenu`、`MenuLayoutConfig`、`PredSlot`、`scroller/`）与 `l2tabs/tabs/core/`（`TabManager`、`ITabScreen`、`FloatingButton`）。如果你的 GUI 开始出现"同一容器多个页签+滚动列表+槽位谓词"的需求，这套框架值得整体参考（它在 `libs/*-sources.jar` 里带源码）。
- **Ponder 教学动画**（createaddition）：`ponder/CAPonderPlugin.java` + `PonderScenes.java`，Create 附属给玩家做教程场景的标准入口。

## 9. Mixin 工程化：FerriteCore 的教科书做法

`源码库/_参考仓库/FerriteCore`（`Common/src/main/java/malte0811/ferritecore/`）：

1. **一个功能一个 mixin 配置 + 一个开关**：`ferritecore.fastmap.mixin.json`、`ferritecore.blockstatecache.mixin.json`…每个都带 `"plugin"` 指向同包的 `Config`（继承 `mixin/config/FerriteMixinConfig.java`，实现 `IMixinConfigPlugin`），由 `FerriteConfig.Option` 决定是否应用。**好处**：用户/其他 mod 可以逐项关闭；出兼容问题时能精确定位。
2. **注入手法**：`FastMapStateHolderMixin` 用 `@Redirect` 改表查找 + `@Overwrite populateNeighbours`；`PalettedContainerMixin` 把 `ThreadingDetector` 换成单 byte 的自研 `SmallThreadingDetector`；`PatchedDataComponentMapMixin` 把空 patch 换成单例空 map（1.21 数据组件的内层优化）。
3. **`postApply` 里动 ASM**：`FerriteMixinConfig` 在 `postApply` 把 `StateHolder.values` 字段类型从 `Reference2ObjectArrayMap` 改为 `Reference2ObjectMap`（`impl/StateHolderImpl.java` 补实现）。**进阶技巧**：mixin 不够用时，在配置插件里直接改字节码。
4. **跨加载器共享**：mixin 全放 `Common/`，加载器差异用反射桥（`util/Constants.java` 里 `Class.forName("malte0811.ferritecore.PlatformHooks")`，两个加载器各提供同名类）+ `IPlatformHooks` 接口做映射名差异（Fabric 走 `MappingResolver`）。
5. **单测**：`Common/src/test/java/.../fastmap/FastMapTest.java`、`SmallThreadingDetectorTest.java`。
6. **诚实记录收益**：根目录 `summary.md` 逐条写每个优化省多少内存（neighbors 表约 600MB），并检测 lithium 决定是否应用（`FerriteMixinConfig`）。

其他参考：L2Library 的 mixin `priority: 1000` + MixinExtras `@WrapOperation`（`ClientLocalPlayerMixin`）；FD 的 mixin 配置分 `mixins` / `client` 两节、`compatibilityLevel: JAVA_21`、`injectors.defaultRequire: 1`（`farmersdelight.mixins.json`）—— 照这个模板写就不会踩 refmap/环境分节的坑。

**性能优化类 mod 的源码清单**（对照表"性能优化"分类）：Sodium、Lithium、ModernFix、ImmediatelyFast、C2ME、Krypton、AllTheLeaks、FerriteCore、AcceleratedRendering 等，全部开源。

## 10. 配置系统：从内置界面到自定义框架

- **FD（官方 ModConfigSpec + 1.21 内建配置界面）**：`common/Configuration.java` 里 `ModConfigSpec COMMON_CONFIG/CLIENT_CONFIG` + 一堆 `Supplier<Boolean>`；主类 `registerConfig(...)`；客户端 `modContainer.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new)` —— **NeoForge 1.21 自带配置 GUI，不需要再依赖第三方**。
- **TLM（拆分 + 多类型）**：`config/GeneralConfig.java`（COMMON）聚合 `config/subconfig/{MaidConfig,ChairConfig,AIConfig,RenderConfig,...}.java` 的 `init(builder)`；另有 `ServerConfig`（SERVER 类型）；客户端用 `IConfigScreenFactory` 挂 Cloth 界面找补美观。配置类按子系统拆文件，是几百项配置的唯一活路。
- **L2Library（自研框架）**：`init/L2LibraryConfig.java extends ConfigInit`，`markL2()` 固定 `l2configs/` 目录，经 `L2Registrate.registerSynced` **自动同步到客户端**；数据包侧还有 `l2core/serial/config/` 的 JSON 配置 + reload listener。**"服务端配置要同步给客户端"的场景**直接参考。
- 第三方配置库（整合包里都有源码）：`fzzy_config`、`yacl`(YetAnotherConfigLib)、`cloth-config`、`resourcefulconfig`、`configured`。选型建议：新项目首选 NeoForge 内置 + `fzzy_config`（好用且现代）。

## 11. 库 / API 设计：如果你要写前置模组

整合包里有三套完整的库设计范本：

| 范式 | 仓库 | 关键做法 |
|---|---|---|
| 注解 + entrypoint 插件 | Jade | `@WailaPlugin(modid)` 声明归属、`IWailaClientRegistration` 注册式 API、`apiJar` 只导出 `snownee.jade.api` 包、防冒充校验 |
| 扩展点接口 + 静态列表 | TouhouLittleMaid | `api/` 包 + `ILittleMaid` + `@LittleMaidExtension` 注解，主类持有 `EXTENSIONS` 列表；`IGeoEntity` 桥接动画 |
| 多模块 jarJar | L2Library / FerriteCore | 功能拆子模块（l2core/l2serial/l2tabs/l2menustacker/l2itemselector/l2modularblocks），`jarJar` 打入或 group 坐标发布；FerriteCore 则用 buildSrc 约定插件统一 loader 工程 |

补充：API 包要**自带 nullability 声明**。L2Library 几乎每个包都有 `package-info.java` 标注 `@MethodsReturnNonnullByDefault/@ParametersAreNonnullByDefault` —— 别人接入你的 API 时 IDE 才不会满屏警告。

## 12. 工程化：GameTest、CI、发布、自动升级

- **GameTest（服务端自动化测试）**：TLM 的 `gametest/TLMGameTests.java`（`@GameTestHolder` + `@PrefixGameTestTemplate`），build.gradle 配 `gameTestServer` run；FD 的 build.gradle 同样有 gametestServer run 订阅。你的模板里已有 `gametest/` 目录，可以照 TLM 的写法把蜂群核心逻辑（行为链判定、殖民地状态机）写成 GameTest。
- **CI**：TLM 的 `.github/workflows/gradle-publish-1.21.yml` 跑 `build runGameTestServer -x test`，把 `-all.jar` 改名 snapshot 发 Release；FerriteCore `.github/workflows/build.yaml` 更简单。**测试通过才允许发布**。
- **单元测试**：FerriteCore 对纯逻辑（FastMap、SmallThreadingDetector）写 JUnit 测试，不依赖 MC 运行时 —— 你的 AI 行为链、路径评分这类纯算法也适合这么测。
- **发布**：`me.modmuss50.mod-publish-plugin` 同时发 CurseForge + Modrinth（Jade、FerriteCore）；L2Library 用 minotaur + curseforgegradle。
- **自动升级 MC 版本**：TLM 根目录 `rewrite.yml` 用 OpenRewrite 写批量迁移规则（改包名/API 调用），这是把 461 个类规模的工程从 1.20 搬到 1.21 的现实手段。**你搬 CaerulaArbor 时可以认真考虑。**
- **给 AI/协作者的说明**：TLM 提交了 `AGENTS.md`（构建/测试命令、单测过滤说明）、`.claude/settings.local.json` —— 与你的 ZCode 工作流直接兼容。

## 13. 推荐阅读路径

按"先看什么收益最大"排序（全部可在 `源码库/_参考仓库/` 直接打开）：

| 顺序 | 仓库 | 重点看 | 你会得到 |
|---|---|---|---|
| 1 | FarmersDelight | 主类 + `common/registry/` + `data/` + `Configuration.java` | 1.21 NeoForge 全量注册面、datagen 管线、官方配置界面 |
| 2 | createaddition | `index/CABlocks.java`、`blocks/<每个机器>/` 四件套、`ponder/`、`network/` | Create 附属标准架构（如果你做 Create 附属，这就是骨架） |
| 3 | TouhouLittleMaid | `entity/ai/brain/`、`entity/task/`、`network/NetworkHandler`、`config/subconfig` | Brain 双轨制 AI、几十个包的网络组织、大型配置拆分 |
| 4 | Jade | `api/` 包、`util/CommonProxy.java`、`network/`、`apiJar` 任务 | 插件式 API 设计、请求-应答网络、少用 mixin 的客户端渲染 |
| 5 | FerriteCore | 每个 `*.mixin.json` + `Config` + `buildSrc` 约定插件 | Mixin 工程化 + 多加载器共用源码 |
| 6 | AppleSkin | `InGameHudMixin`、`TooltipOverlayHandler`、`api/event/` | HUD/tooltip 扩展与对外事件 |
| 7 | L2Library | `libs/*-sources.jar`（l2core/l2serial/l2tabs）、`L2Registrate` | 库模组的模块化、自研网络/配置/UI 框架 |
| 8 | Lootr | `common/` vs `neoforge/` 分包、`network/toClient/` | 每玩家数据的架构与同步 |
| 9 | KaleidoscopeCookery | `init/`、`datagen/`、`network/`、`api/` | 中文同行的 NeoForge 工程组织（与农夫乐事同类但更贴近你的社区） |

进阶补充（未克隆，对照表里有链接，按需 clone）：

- 优化：`CaffeineMC/sodium`、`caffeinemc/lithium-fabric`、`embeddedt/ModernFix`
- 世界生成：`TelepathicGrunt/RepurposedStructures`、`TelepathicGrunt/StructureLayoutOptimizer`
- 数据驱动内容：`Iron431/irons-spells-n-spellbooks`、`Shadows-of-Fire/Apotheosis`
- 附属生态：`DragonsPlusMinecraft/CreateEnchantmentIndustry`（同作者的四个 Create 附属，代码风格统一）
- 中文生态：`Minecraft-LightLand/L2Hostility`、`0999312/umapyoi`、`KaleidoscopeMods/KaleidoscopeCookery`
- 实体/生物：`AlexModGuy/AlexsMobs`、`AlexModGuy/AlexsCaves`（含 `Citadel` 前置）

---

### 数据来源与可信度说明

- 对照表 298 个仓库：Modrinth API `source_url`（官方登记）+ jar 内 `neoforge.mods.toml` / `fabric.mod.json` 的 `displayURL/issueTrackerURL`（直接读 jar 元数据，Range 请求只下载几百 KB）+ 少量 GitHub 搜索核对；**全部经 `git ls-remote` 验证仓库真实存在**。
- 88 个未找到的：约一半是闭源 mod（Xaero 系列、DungeonsArise、Macaw 系列、部分 CurseForge 独占），其余是中文作者的附属（帕斯特系列、森罗系列附属、机械动力航空学生态的部分组件）——这类作者通常只在爱发电/QQ 群发布。
- 星标/下载量等流行度数据可用 `_modrinth_projects.json` 里的 `downloads` 字段自行排序。
