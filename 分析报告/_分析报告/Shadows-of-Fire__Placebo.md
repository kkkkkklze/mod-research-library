# Shadows-of-Fire/Placebo 源码分析报告

## 1. 基本信息
- Mod 名 Placebo / `placebo` / 作者 Shadows_of_Fire / 版本 `10.0.2`
- **本地检出分支为 `26.1`（`git branch -a` 只有 26.1）**：`gradle.properties` 为 `mcVersion=26.1.2`、`javaVersion=25`、`forgeVersion=26.1.2.64-beta`；生成物 `src/generated/resources/META-INF/neoforge.mods.toml` 声明依赖 `minecraft [26.1.2,)`、`neoforge [26.1.2.64-beta,)`。**未包含 1.21.1 分支代码**，参考时注意 API 差异
- 构建：`net.neoforged.moddev 2.0.141` + `maven-publish` + `mod-publish` + `eclipse-apt`；mixin 0.8.7；许可证 MIT
- 定位：神化（Apotheosis）等 mod 的前置库；`desc=1 (one) library boi`

## 2. 源码规模与包结构
- 107 个 `.java`，13393 行。包（`dev.shadowsoffire.placebo.*`）：`util` 13、`menu` 10、`dynreg` 10、`json` 7、`config` 7、`mixin` 5、`dynreg/tag` 5、`datagen` 5、`patreon` 4、`commands` 4、`codec` 4、`screen` 3、`network` 3、`block_entity` 3、`systems/{gear,mixes}`、`tabs`、`events`、`registry`、`cap`、`color`
- 最大文件：`config/Configuration.java`(1484)、`config/Property.java`(1027)、`registry/DeferredHelper.java`(734)、`dynreg/DynamicRegistry.java`(606)、`util/AbstractBiMap.java`(535)、`datagen/LegacyRecipeProvider.java`(386)、`dynreg/tag/DynamicHolderSet.java`(304)

## 3. 入口与注册
`src/main/java/dev/shadowsoffire/placebo/Placebo.java:34` `@Mod(Placebo.MODID)`，构造：`bus.register(this)`、`NeoForge.EVENT_BUS.addListener(...)`（commands/serverReload/serverStart）、`bus.register(new PayloadHelper())`、`PlaceboConfig.load()`。`setup(FMLCommonSetupEvent)` 里批量 `PayloadHelper.registerPayload(...)` 6 个内建包，并把 `GearSetRegistry.INSTANCE`/`MixRegistry.INSTANCE` `registerToBus()`。**无硬编码方块/物品注册**，注册能力全部以 API 形式外放。

## 4. 核心系统
1. **统一延迟注册门面 `DeferredHelper`**（`registry/DeferredHelper.java:106`）：`DeferredRegister` 之上的单入口，除 `block/item/...` 常规方法外提供 `custom(String, ResourceKey, Supplier)` 注册任意注册表；在 `NewRegistryEvent` 阶段用 `RegistryBuilder` 创建自定义注册表（文件内有"root registry 占位 key"的注释说明）。
2. **可重载数据驱动注册表 `DynamicRegistry<R>`**（`dynreg/DynamicRegistry.java:64`）：继承 `SimplePreparableReloadListener<Map<Identifier,JsonElement>>`，"像注册表一样但不是 datapack registry，可以重载"；内含 `BiMap<Identifier,R> registry`（重载时 clear→freeze）、`DynamicHolder`、`getOrCreateTag(DynamicTagKey)`、`RegistryCallback` 回调集；目录布局 `data/<ns>/<reg.ns>/<reg.path>/`、tag 同级。
3. **网络抽象 `PayloadHelper`**（`network/PayloadHelper.java:20`）：静态 `ALL_PROVIDERS` 表 + `locked` 标志，全部在 `RegisterPayloadHandlersEvent` 里一次性 `NetworkRegistry.register`；`PayloadProvider` 抽象出 codec、flow、protocols、`HandlerThread.MAIN|NETWORK`，内层 `PayloadHandler` 校验 flow/protocol 并按线程分发。
4. **重载同步三段协议**（`dynreg/DynRegPayloads.java`）：`Start/Content/End` 三个 record payload（id 为 `placebo:reload_sync_start` 等），`Content` 用 `Either<V, ByteBuf>` 支持惰性传递，配合 `staged/stagedTags` 在主线程一次性 apply。
5. **自研配置系统**（`config/Configuration.java`、`Property.java`、`ConfigCategory.java`，源码头保留 Forge LGPL 声明）：不依赖 NeoForge `ModConfig`，自带 TOML 读写与 GUI 用的 `ConfigElement`，多个下游 mod 靠它做客户端可编辑配置。
6. **`json`/`codec` 工具包**：`ChancedEffectInstance`、`WeightedItemStack`、`RandomAttributeModifier`、`OptionalStackCodec`、`codec/PlaceboCodecs`。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：NeoForge payload 体系，见上；`payloads/` 有 `ButtonClickPayload`、`PatreonDisablePayload`。
- 数据驱动：`DynamicRegistry` + `dynreg/tag/DynamicTagManager`（`Placebo.serverReload` 里以 `DynamicTagManager.ID` 注册为 server reload listener）。
- datagen：`datagen/DataGenBuilder`、`FieldOrderingFactory`/`FilteredOrderingFactory`（**强制 JSON 字段输出顺序**，保证 datagen 结果稳定）、`RegisterFieldOrderingsEvent`、`util/data/DynamicTagProvider`。
- 配置：`PlaceboConfig` + 自研 Configuration。

## 6. Mixin
`src/main/resources/placebo.mixins.json`（`compatibilityLevel: JAVA_25`）：
- mixins：`AnvilBlockMixin`（`onLand` TAIL）、`DatagenModLoaderMixin`（`begin` HEAD）、`DataProviderMixin`、`HashCacheMixin`（`purgeStaleAndWrite` 内 INVOKE `Map.forEach`）、`ItemStackMixin`
- client：`client.AbstractContainerScreenMixin`、`client.ChatComponentMixin`（`ModifyConstant` 改 `logChatMessage`）
- `src/main/resources/META-INF/accesstransformer.cfg` 打开 `RecipeManager.recipes/byName`、`LootPool$Builder.entries/conditions/functions`、`TextColor.NAMED_COLORS`、`PotionBrewing.potionMixes` 等。

## 7. 值得学的 5 条做法
1. **把 `DeferredRegister` 再包一层统一门面**，下游只调 `DeferredHelper.xxx()`（`registry/DeferredHelper.java`）——库 mod 降低接入成本的典型手法。
2. **用 reload listener 实现"可重载注册表"**，并用 `DynamicHolder` 让下游按 id 惰性取（`dynreg/DynamicRegistry.java`）——适合"数据包定义内容物"的系统。
3. **payload 注册收敛到一个静态表 + 一个事件**（`network/PayloadHelper.java:32-54`），并强制 `HandlerThread` 语义，避免各 mod 到处注册。
4. **datagen 时固定 JSON 字段顺序**（`datagen/FieldOrderingFactory.java` + `FilteredOrderingFactory.java`）——多人协作时减少无意义 diff。
5. **自带配置系统而非绑定加载器 API**（`config/Configuration.java`）——跨加载器/跨版本迁移成本低。

## 8. 公开 API 与接入方式
- API 包：`dev.shadowsoffire.placebo.*` 全树公开，主要扩展点：
  - 注册：`registry/DeferredHelper`
  - 数据驱动注册表：`dynreg/DynamicRegistry`、`RegistrySerializer`、`RegistryCallback`、`dynreg/tag/*`、`WeightedDynamicRegistry`
  - 网络：`network/PayloadHelper`、`network/PayloadProvider`、`payloads/*`
  - 菜单 UI：`menu/BlockEntityMenu`、`PlaceboContainerMenu`、`QuickMoveHandler`、`FilteredSlot`、`SimpleDataSlots`；`screen/*`
  - 工具：`util/PlaceboUtil`、`PlaceboTaskQueue`、`AbstractBiMap`、`StepFunction`、`RandomRange`；`block_entity/TickingBlockEntity(TickSide)`
  - 事件：`events/ResourceReloadEvent`、`datagen/RegisterFieldOrderingsEvent`
- 接入方式：下游 mod 在自己的 `@Mod` 构造/setup 事件里 `new` 上述类、`registerToBus()`、`PayloadHelper.registerPayload(...)`；无服务端发现机制（无 `@PlaceboPlugin` 之类），纯编译期依赖。
