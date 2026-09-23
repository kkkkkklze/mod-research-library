# wisp-forest/accessories 源码分析报告

## 1. 基本信息

- Mod 名：**Accessories**；mod_id `accessories`；group `io.wispforest`；`mod_version=1.4.3-beta`；作者 `blodhgarm, chyzman, Dr.Zeal`（贡献者含 glisco、BasiqueEvangelist 等）；`gradle.properties` 自述 "An extendable and data-driven Accessory Mod for Minecraft"
- 目标版本：本快照分支 `1.21.9`（`git branch -a`），但 `libs.versions.toml` 已写 `minecraft = "1.21.10"`、`java = "21"`、Parchment `2025.10.12`
- 加载器：**Fabric + NeoForge 双端**（`settings.gradle.kts` 三个子项目 common/fabric/neoforge + `neoforge-publish`）。Fabric：loader `0.17.2`、fabric-api `0.135.0+1.21.10`；NeoForge `21.10.16-beta`、`[21.10.16-beta,)`、loader `[4,)`
- Gradle：Kotlin DSL（`build.gradle.kts`）+ `buildSrc` 约定插件 + **Version Catalog（`libs.versions.toml`）**；用 `gradle.properties` 的开关做"平台/物品查看器/测试 mod"可选构建：`enabled_platforms=fabric,neoforge`、`enabled_item_viewers=emi,rei,jei`、`selected_item_viewers=none`、`enabled_testmod_platforms=fabric,neoforge`、`enabled_mixin_debugging_platforms=fabric`
- 许可证：MIT
- 编译依赖（`libs.versions.toml`）：**`owo-lib`（`io.wispforest:owo-lib(-neoforge)`）为必装前置**（`neoforge.mods.toml` 中 `modId="owo" required=true`）；`endec 0.1.11`（+ netty/gson/jankson 适配）、`jankson`、`mixinextras 0.5.0`；NeoForge 侧额外依赖 `org.sinytra.forgified-fabric-api:fabric-api-base`（`ffapi_base`）——**即 NeoForge 版通过 Sinytra FFAPI 使用 Fabric API 的 `TriState` 等类型**。可选集成：Mod Menu、REI/EMI/JEI、GeckoLib、**Curios `10.0.1+1.21.4`**、**Trinkets `3.10.0`**、Sodium
- `neoforge.mods.toml` 显式声明 `accessories_compat_layer` 版本 `(,0.1.9]` 为 **incompatible**

## 2. 源码规模与包结构

实测：**451 个 `.java`，38759 行**（`find -print0 | xargs -0 wc -l` 求和）。

包结构（第 3 层文件数）：`io/wispforest/accessories/mixin/client` 35、`api/client` 29、`api/events` 23、`commands/api` 21、`client/gui` 18、`api/slot` 17、`api/data` 12、`compat/config` 11、`api/tooltip` 11、`neoforge/mixin` 9、`api/action` 9、`networking/client` 8、`data/api` 8、`mixin/owo` 7、`fabric/mixin` 7、`api/components` 7、`api/caching` 7、`impl/slot` 5、`impl/core` 5、`api/core` 5、`networking/server` 4、`impl/caching` 3、`api/equip` 3、`pond/stack` 2、`api/menu` 2。

最大的 10 个文件：`client/gui/AccessoriesScreen.java` 1608、`impl/event/AccessoriesEventHandler.java` 932、`commands/AccessoriesCommands.java` 681、`impl/core/AccessoriesContainerImpl.java` 651、`menu/variants/AccessoriesMenu.java` 548、`client/AccessoriesClient.java` 546、`commands/api/base/CommandTreeBuilderWithArgs.java` 492、`client/gui/components/AccessoriesScreenSettingsLayout.java` 432、`compat/config/client/components/ConfigurableStructLayout.java` 419、`api/client/rendering/RenderingFunctionOps.java` 400。

**分包哲学**：对外可见的全在 `api/`（约 150 文件），内部实现全部在 `impl/`；`pond/` 是 duck-interface 包（该 mod 用 "pond" 代替 "extensions" 命名）。

## 3. 入口与注册

common 侧 `io/wispforest/accessories/Accessories.java` 是门面，`init()` 里做四件事：

```java
// common/.../Accessories.java:127-131（init 开头）
Reflection.initialize(SlotTypeLoader.class, SlotGroupLoader.class, EntitySlotLoader.class, CustomRendererLoader.class);
AccessoriesCommands.init();
AllowEntityModificationCallback.EVENT.register((target, player, reference, buffer) -> { ... });
ArmorSlotTypes.INSTANCE.init();
```

- **`Reflection.initialize(...)` 强制触发四个数据加载器的静态初始化**（Guava 的反射技巧），避免注册顺序依赖——很值得抄。
- 数据包加载器统一定义四个 ResourceLocation 常量：`slot_loader` / `entity_slot_loader` / `slot_group_loader` / `data_reload_hook`（`Accessories.java:47-50`）。
- 平台入口：NeoForge `neoforge/.../AccessoriesForge.java` `@Mod`（文件内 import 了 `EntityCapability`、`RegisterCapabilitiesEvent`、`AttachmentType`、`IAttachmentSerializer`、`OnDatapackSyncEvent`、`ModifyDefaultComponentsEvent`，可见其用 **NeoForge Capability + Data Attachment 承载饰品数据**）；Fabric `fabric/.../AccessoriesFabric.java` + `AccessoriesFabricInternals`；两侧各有 `Accessories*Internals` / `Accessories*LoaderInternals` 做 SPI 实现（`utils/ServiceLoaderUtils.java` 用 `ServiceLoader.load(...).findFirst().orElseThrow()`，**本快照中 `META-INF/services` 文件缺失，具体服务名未确认**）。
- 配置：`AccessoriesConfig.createAndLoad(...)`（owo-lib 的 config）+ `compat/config/` 11 文件做**配置界面组件**（owo 的 GUI 库），配置项支持 `SyncServerOverrideOption.hookUpdate(...)` 做服务端覆盖同步（`Accessories.java:145-150`）。
- 进度/统计：`criteria/AccessoryChangedCriterion` 通过 mixin accessor 注册触发器 `accessories:equip_accessory` / `accessories:unequip_accessory`（`Accessories.java:153-157`）。

## 4. 核心系统

1. **数据驱动的槽位系统（本 mod 最大卖点）**：四种 JSON 数据包，全部由 `data/api/ManagedEndecDataLoader` 派生：`SlotTypeLoader`（`accessories/slot/*.json`）、`EntitySlotLoader`（实体↔槽位绑定）、`SlotGroupLoader`（槽位分组：head/chest/arm/leg/feet/misc）、`CustomRendererLoader`。每类 loader 都是 `INSTANCE` 单例 + 静态查询方法 + `Map<EntityType<?>, ...>` 双端缓存（`data/SlotTypeLoader.java:33-80`）。**序列化不用 Gson/Codec 而用自家 `endec`（`StructEndec`/`Endec`）**，见 `api/data/providers/slot/RawSlotType.java`（record + `StructEndecBuilder.of(String.fieldOf("name",...), BOOLEAN.optionalOf().fieldOf("replace",...), ...)`）。
2. **槽位抽象与验证管线**：`api/slot/` 17 文件——`SlotType`、`SlotGroup`、`SlotPath` / `DelegatingSlotPath` / `SlotPathWithStack` / `SlotReference` / `SlotEntryReference`（"第几个戒指槽"这类定位对象）、`UniqueSlotHandling`（动态增删槽位）、`validator/SlotValidator` + `SlotValidatorRegistry`、`SlotPredicateRegistry`（内置谓词 id：`accessories:all/none/tag/attribute/component`，见 `api/data/AccessoriesBaseData.java:36-40`）。另有 `api/caching/`（`ItemStackPredicate` / `ItemTagPredicate` / `DataComponentsPredicate` 等 7 个）为高频装备判定做缓存。
3. **Accessory 能力接口 + 注册表**：`api/core/Accessory`（`tick(stack, reference)` / `canEquip` / `canUnequip` / `getAttributeModifiers` / 掉落规则等），`api/core/AccessoryRegistry` 用 `Map<Item, Accessory>` 做绑定，未注册物品回退到 `DEFAULT` / `DEFAULT_NEST`（`api/core/AccessoryRegistry.java:21-52`）；`canEquip` 的判定顺序是 **事件 → Accessory 接口 → 默认成功**，中间通过 `ActionResponseBuffer` + `ValidationState`（IRRELEVANT 表示没人表态）串联（`AccessoryRegistry.java:88-107`）。
4. **实体侧数据承载**：`api/AccessoriesCapability`（接口，静态 `get(LivingEntity)` 通过 duck interface `pond/AccessoriesAPIAccess#accessoriesCapability()` 拿）+ `AccessoriesContainer` + `AccessoriesStorage`/`AccessoriesStorageLookup`/`SimpleAccessoriesStorage`，实现类在 `impl/core/`（`AccessoriesContainerImpl` 651 行、`AccessoriesHolderImpl`）。**跨平台差异由平台侧承担：NeoForge 用 `EntityCapability` + `AttachmentType`，Fabric 用 mixin 注入接口**。
5. **事件体系（双版本并存）**：`api/events/`（旧：`CanEquipCallback`、`AccessoryChangeCallback`、`OnDropCallback`、`DropRule`…）与 `api/events/v2/`（新：`CanEquipCallback`、`AllowEntityModificationCallback`…）并存过渡；`api/events/extra/` 是"内置附赠能力"集合——`AllowWalkingOnSnow`、`EndermanMasked`、`FortuneAdjustment`、`OnTotemActivate`、`PiglinNeutralInducer`、`ShouldFreezeEntity`、`v2/LootingAdjustment` 等，**做成事件意味着其它 mod 可以复用这些原版行为改写点**。业务聚合在 `impl/event/AccessoriesEventHandler.java`（932 行）。
6. **客户端渲染 API**：`api/client/` 29 文件——`AccessoriesRendererRegistry.bindItemToRenderer(item, id, () -> Renderer)`（见 testmod `AppleAccessory.clientInit()`），渲染器接口 `AccessoryRenderer` / `SimpleAccessoryRenderer`（只实现 `renderStack` + `align`）/ `DefaultAccessoryRenderer` / `AccessoryNestRenderer`（嵌套饰品）；`api/client/rendering/` 是一套**小型表达式/变换系统**：`RenderingFunction`(+`Ops`)、`RenderingPredicate`、`ModelTransformOps` / `TransformOps`（400+393 行），用于给不同部位/朝向声明式指定位移旋转。
7. **饰品/数据组件**：`api/components/`（7 文件）——`AccessoriesDataComponents`、`AccessorySlotValidationComponent`、`AccessoryItemAttributeModifiers`、`AccessoryMobEffectsComponent`、`AccessoryCustomRendererComponent`、`AccessoryStackSettings`、`AccessoryNestContainerContents`；属性侧 `api/attributes/`（`AccessoryAttributeBuilder`、`SlotAttribute`、`AttributeModificationData`、`AccessoryAttributeUtils`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`AccessoriesNetworking`（统一 channel 封装，基于 owo/endec），包在 `networking/client/`（`SyncData`、`SyncContainerData`、`SyncEntireContainer`、`SyncPlayerOptions`、`SyncServerOverrideOption`、`AccessoryBreak`、`InvalidateEntityCache`、`ScreenVariantPing`）与 `networking/server/`（`ContainerClose`、`ScreenOpen`、`SyncCosmeticToggle`、`NukeAccessories`）。
  **对外扩展点**：其它 mod 可往同一 channel 注册自己的包——testmod 里 `AccessoriesNetworking.CHANNEL.registerServerbound(TestScreenPacket.class, TestScreenPacket.ENDEC, AccessoriesNetworking.serverHandler(TestScreenPacket::handlePacket))`（`neoforge/src/testmod/.../Testccessories.java:57-59`）。**这是"前置 mod 开放网络通道给下游"的样板。**
- **数据驱动**：全部走数据包 JSON（`accessories/slot`、`accessories/entity`、slot group、custom renderer），并有 reload listener（mixin `SimpleJsonResourceReloadListenerMixin/Accessor`、`DataPackContentsMixin`、`pond/ReplaceableJsonResourceReloadListener` 支持替换/热重载）。
- **配置**：owo-lib config（`compat/config/AccessoriesConfig`）+ 自绘配置界面（owo GUI）；含"服务端覆盖客户端选项"的同步机制（`SyncServerOverrideOption`）。
- **datagen**：**为下游 mod 提供了完整 datagen API**——`api/data/providers/BaseDataProvider` 之下有 `slot/SlotDataProvider`（+`SlotBuilder`）、`group/GroupDataProvider`（+`SlotGroupBuilder`、`RawSlotGroup`）、`entity/EntityBindingProvider`（+`EntityBindingBuilder`、`RawEntityBinding`）；`SlotDataProvider` 强制输出到 `PackOutput.Target.DATA_PACK`、路径 `accessories/slot`、重复 ID 直接 `IllegalStateException`（`SlotDataProvider.java:28-70`）。

## 6. Mixin

- 配置：`common/src/main/resources/accessories-common.mixins.json`（`package: io.wispforest.accessories.mixin`、`plugin: io.wispforest.accessories.mixin.AccessoriesMixinPlugin`、`compatibilityLevel: JAVA_17`、`test_refmap`）+ `accessories-fabric.mixins.json` + `accessories-neoforge.mixins.json`；另有 testmod 两份。
- 组织：**`client` 段 35 个，`mixins` 段 50+ 个**，无按功能子包细分（全平铺在 `mixin/`），但客户端独立一个大段。`mixin/owo/` 专门修 owo-lib（`ConfigWrapperAccessor`、`NbtDeserializerMixin`、`TagValueInputAccessor` 等 7 个）；`neoforge/mixin/curios/CurioInventoryMixin` 做 Curios 兼容；`neoforge/mixin/neoforge/BaseRenderStateAccessor` 适配 NeoForge 渲染；**甚至有 `sodium.MPOATVConstructingVertexConsumerMixin_SodiumImpl`（按 mod 名做实现后缀）**。
- 代表性目标：`ItemStackMixin` / `ItemStackAccessor` / `PatchedDataComponentMapMixin`（给 ItemStack 挂饰品组件、`pond/stack/ItemStackExtension`）、`LivingEntityMixin` + `LivingEntityAccessor` + `PlayerMixin`（注入 `AccessoriesAPIAccess` 提供 capability）、`EquipmentSlotMixin` / `EquipmentSlotTypeMixin`（扩展装备槽枚举）、`InventoryMixin`、`DispenserBlockMixin`、`PiglinAiMixin`、`PowderSnowBlockMixin`（原版行为改写）、`ServerGamePacketListenerImplMixin`（菜单/同步）、`SimpleJsonResourceReloadListenerMixin`、`CriteriaTriggersAccessor`（注册自定义判据）。客户端：`EntityRendererMixin`、`AvatarRendererMixin`、`InventoryScreenMixin`、`CreativeInventoryScreenMixin`、`GuiGraphicsMixin`(含内部类 `$ScissorStackMixin`)、`WingsLayerMixin`、`LoadingOverlayMixin`、一堆 `*Accessor`。

## 7. 值得学的 5 条具体做法

1. **用 `Reflection.initialize(...)` 强制初始化静态数据加载器**（`Accessories.java:128`）：不写静态块、不依赖调用顺序，所有数据 loader 只在自己类里做单例。适合任何"多个 ResourceReloadListener 需要按序初始化"的 mod。
2. **JSON 槽位定义 + 数据包扩展**（`data/SlotTypeLoader.java` + `api/data/providers/slot/RawSlotType.java`）：`accessories/slot/*.json` 用 `{name, replace, icon, order, amount, validators, dropRule}` 描述一个槽位，**新增槽位不用写代码**，甚至可被资源包/整合包覆盖。
3. **`ActionResponseBuffer` + `ValidationState.IRRELEVANT` 三态决策链**（`api/core/AccessoryRegistry.java:88-107`、`api/action/` 9 文件）：事件先表态，没人表态再问 Accessory 实现，最后兜底 true。比"boolean 短路"表达力强得多，且能带拒绝理由（`ActionResponse.of(false, Component...)`）。
4. **前置 mod 主动开放能力给下游**：`AccessoriesNetworking.CHANNEL`（网络）、`AccessoriesRendererRegistry`（渲染）、`UniqueSlotHandling.EVENT`（动态槽位）、datagen `SlotDataProvider/GroupDataProvider/EntityBindingProvider`，全部在 `api/` 下公开，并在仓库内自带 **`testmod`**（fabric/neoforge 两套）作为可运行用法示例——**做库模组时"自带 testmod + 平台双份"是最省事的下游文档**。
5. **平台差异集中到 `*Internals` / `*LoaderInternals` + `pond` duck interface**：common 只写接口，NeoForge 用 `EntityCapability`/`AttachmentType`、Fabric 用 mixin 实现同一接口（`pond/AccessoriesAPIAccess`、`fabric/.../AccessoriesFabricInternals`、`utils/ServiceLoaderUtils`）。比 architectury 依赖更轻量，值得作为双端库的参考模板。

## 8. 公开 API / 扩展点（本 mod 是前置库，重点）

- **公开 API 根包：`io.wispforest.accessories.api`**，子包划分清晰：`api.core`（`Accessory`、`AccessoryItem`、`AccessoryRegistry`、`AccessoryNest`）、`api.slot`（+ `api.slot.validator`）、`api.events`（+ `api.events.v2`、`api.events.extra`）、`api.data`（+ `api.data.providers.*` datagen）、`api.components`、`api.attributes`、`api.client.*`（渲染/屏幕/提示框）、`api.action`、`api.caching`、`api.equip`、`api.menu`、`api.tooltip`。
- **注意：`api/AccessoriesAPI.java` 整个类已标 `@Deprecated(forRemoval = true)`**（第 33 行），所有静态方法都只是转发到 `AccessoryRegistry` / `SlotValidatorRegistry` / `SlotPredicateRegistry` / `AccessoryAttributeLogic`。**新代码应直接用这些 Registry 类，不要用 `AccessoriesAPI`。**
- 外部 mod 接入方式（以仓库自带 testmod 为实证，`neoforge/src/testmod/.../Testccessories.java`）：
  1. 实现 `Accessory` 接口并 `AccessoryRegistry.register(Items.APPLE, new AppleAccessory())`（`AppleAccessory.init()`）；
  2. 客户端 `AccessoriesRendererRegistry.bindItemToRenderer(item, ResourceLocation, Supplier<AccessoryRenderer>)`（`AppleAccessory.clientInit()`）；
  3. 自定义槽位走 datagen（`SlotDataProvider` + `SlotBuilder`）或数据包 JSON；动态槽位走 `UniqueSlotHandling.EVENT.register(...)`；
  4. 自定义网络包复用 `AccessoriesNetworking.CHANNEL`；
  5. 装备/卸下/掉落/属性修改等行为通过 `api.events` 回调或 `api.events.extra` 内置能力注册。
- 上游必读：**owo-lib（`io.wispforest.owo`，GUI + 配置 + 序列化，必装）**、**endec（`io.wispforest:endec`，替代 Codec 的序列化框架）**、NeoForge Capability/Attachment、Fabric API（NeoForge 侧经 Sinytra FFAPI 间接使用 `TriState` 等）。
