# ochotonida/artifacts 源码分析报告

## 1. 基本信息

- Mod 名：**Artifacts**（奇异饰品）；mod_id `artifacts`；作者 `Wouter`（ochotonida）；`gradle.properties` `version=15.1.3`
- 目标版本：**`minecraft_version=26.1.2`**（新版 MC 版本号体系）、`java_version=25`、`neo_form_version=26.1.2-1`；本仓库只有 `26.1` 一个分支（`git branch -a`），**没有 1.20.1/1.21.1 分支快照**
- 加载器：**Fabric + NeoForge 双端**（`settings.gradle` 三个子项目 `common` / `fabric` / `neoforge`）。Fabric：loader `0.19.2`、fabric-api `0.145.3+26.1.1`、`minecraft_version_range_fabric=~26.1`；NeoForge `26.1.2.103`、`[26.1.2.100,)`
- Gradle 插件：`net.fabricmc.fabric-loom 1.15.5` + `net.neoforged.moddev 2.0.141`（`build.gradle:1-6`），common 用 neoform 反混淆
- 许可证：MIT
- 编译依赖（`gradle.properties`）：**`expandability 14.0.2`（必装）**；饰品槽 API 三家同时支持：`curios 15.0.0+26.1.2`、`trinkets 4.0.0-rc.1+26.1`（mod id 为 `trinkets_updated`）、**`accessories 1.3.8-beta+1.21.8`**；其余：`yumi`、`cardinal-components-api 8.0.0`、`owo 0.12.15.4`、`cloth-config 26.1.154`、`mod-menu`、`night-config 3.8.0`；集成：`lootr`、`apoli`
- `neoforge.mods.toml` 里 curios / accessories / trinkets_updated / cloth_config 全部 `type="optional"`，**说明饰品前置是软依赖**，靠 `ModCompat` 运行时探测

## 2. 源码规模与包结构

实测：**290 个 `.java`，19096 行**（`find -print0 | xargs -0 wc -l` 求和）。

根包 `artifacts`（common 侧）下二级包：`client`（item/model、item/mesh、item/renderer）、`component`、`config`、`effect`、`entity`、`equipment`、`event`、`extensions`、`integration`、`item`、`lang`、`loot`、`mixin`、`network`、`platform`、`registry`、`util`、`world`、`attribute`。

最大的 10 个文件：`config/ItemConfigs.java` 1402、`registry/ModItems.java` 689、`entity/MimicEntity.java` 455、`neoforge/data/LootModifiers.java` 423、`config/ConfigManager.java` 419、`neoforge/data/LootTables.java` 393、`util/TooltipHelper.java` 353、`event/ArtifactHooks.java` 346、`neoforge/data/Language.java` 308、`item/ArtifactProperties.java` 299。

包规模偏小但极碎：`mixin/ability/*` 按"能力"再分一层子包（`enchantment`5、`equipabletotem`、`hurtsound`、`enderpearlhungercost`、`retaliation`、`phantomrepellent`…），一处能力 = 一个 mixin 子包 = 若干个 mixin 类。

## 3. 入口与注册

**common 无 `@Mod`**，只有静态门面 `artifacts/Artifacts.java`（`Artifacts.java:53-79` 的 `setup()`）串起全部注册；各平台入口调它：

```java
// common/.../Artifacts.java:66-79
ModMobEffects.MOB_EFFECTS.register();
ModDataComponents.DATA_COMPONENT_TYPES.register();
ModSoundEvents.SOUND_EVENTS.register();
ModLootConditions.LOOT_CONDITION_TYPES.register();
ModLootFunctions.LOOT_FUNCTION_TYPES.register();
ModPlacementModifierTypes.PLACEMENT_MODIFIER_TYPES.register();
ModAttributes.ATTRIBUTES.register();
ModEntityTypes.ENTITY_TYPES.register();
ModConsumeEffects.CONSUME_EFFECT_TYPES.register();
ModItems.ITEMS.register();
ModItems.CREATIVE_MODE_TABS.register();
ModFeatures.FEATURES.register();
ModGameEvents.GAME_EVENTS.register();
```

- NeoForge 入口 `neoforge/.../ArtifactsNeoForge.java:30` `@Mod(Artifacts.MOD_ID)`，构造里 `Artifacts.setup()` + 平台专属注册（`ModConditions` / `ModLootModifiers` / `ModAttachmentTypes`）+ 事件监听。
- Fabric 入口 `fabric/.../ArtifactsFabric.java:20` `implements ModInitializer`，同样 `Artifacts.setup()` 后接 Fabric API 事件（`ServerEntityEvents.ENTITY_LOAD`、`LootTableEvents.MODIFY`、`ServerConfigurationConnectionEvents.CONFIGURE`）。
- **注册框架是自研的**：`registry/Register.java`（抽象 `Register<R>`，持有 `ResourceKey<Registry<R>>` + `List<RegistryHolder<R,?>>`）+ `registry/RegistryHolder.java`（**同时实现 `Holder<R>` 和 `Supplier<V>`**，内部 `Holder` 在 `bind()` 时才注入）。`Register.create()` 通过 `PlatformServices.getPlatformHelper().createRegister(...)` 委托平台实现（neoforge 有 `NeoForgeRegister.java`）。
- 特殊处理：`Register.register()` 对 `ATTRIBUTE` / `MOB_EFFECT` / `DATA_COMPONENT_TYPE` 三个注册表**在注册时就立刻 `bind`**（`Register.java:41-47`），其它类型延迟到 `register()` 统一 bind——这是为了让属性/效果能被后续注册内容提前引用。

## 4. 核心系统

1. **"能力即数据组件"（本仓库最值得抄的设计）**：所有饰品效果不是硬编码的 Item 子类，而是 **DataComponent**。`item/ArtifactProperties.java:95-201` 是一个链式 builder，把 `increasesAttribute / mobEffect / damageOnMeleeAttack / durability / cooldownOnHurt / equipmentAbility…` 全部翻译成 `ModDataComponents.*` 上的组件；`registry/ModDataComponents.java:29-40` 定义 `Set<TickingAbility<?,?>> TICKING_ABILITIES` + 每种组件的 `ComponentType.Singleton`（`registerSynced` / `registerCached` 区分是否走网络同步）。**收益：新增一件饰品 ≈ 加几行 builder 调用，不新增类**。
2. **装备槽抽象层**：`equipment/EquipmentSlotManager.java` 维护一个 `LinkedHashSet<EquipmentSlotProvider>`，对外只暴露 `iterateEquipment(entity, skipItemsOnCooldown, skipDisabledItems, Consumer<ItemStack>)` 和 `reduceEquipment(...)`（`EquipmentSlotManager.java:22-58`），由各 provider（`integration/minecraft/ArmorSlotProvider`、`integration/trinkets/TrinketsSlotProvider`、`integration/accessories/AccessoriesSlotProvider`，neoforge 再加 `curios/CuriosSlotProvider`）各自贡献槽位。**上层能力代码只认 `EquipmentSlotAccess`，完全不知道 Curios/Trinkets/Accessories 的存在**。
3. **配置系统（含服务端→客户端同步）**：自研 `config/ConfigManager.java`（419 行）基于 `com.electronwill.nightconfig`：`CommentedFileConfig` + `ConfigSpec` 校验纠错 + `FileWatcher` 热重载 + 损坏时 `createBackup(path, 5)` 轮转备份（`ConfigManager.java:62-101`、`209-228`）；`ConfigValueBuilder.syncToClients()` 标记后，值通过 `UpdateConfigValuePacket` 在**配置阶段**下发（Fabric `ServerConfigurationConnectionEvents.CONFIGURE` / NeoForge `RegisterConfigurationTasksEvent`，见 `ArtifactsNeoForge.java:73-89`），客户端断连时 `onClientDisconnect()` 重读本地值复原（`Artifacts.java:102-108`）。
4. **事件桥（mixin 只做检测，逻辑全在 common）**：mixin 类只负责在正确的注入点调 `ArtifactHooks.xxx`（如 `mixin/ability/LivingEntityMixin.java` 里 `handleEquipmentChanges` HEAD 调 `ArtifactHooks.onItemChanged`），真正的业务集中在 `event/ArtifactHooks.java`（346 行，`livingUpdate` / `beforeLivingDamaged` / `onFall` / `onJump` …）。**这样一套逻辑被 Fabric 与 NeoForge 共用，mixin 层极薄**。
5. **扩展面接口（duck interface）**：`extensions/` 包（`ability/LivingEntityExtensions`、`client/LivingEntityRenderStateExtensions`、`item/pocketpiston/LivingEntityExtensions`、`mobeffect/magnetism/ItemEntityExtensions`）声明 `artifacts$xxx()` 方法，mixin 里 `implements` 并给 `@Unique` 字段——避免把状态存到原版实体上又不用强转。**注意 `@Unique` + `artifacts$` 前缀是本仓库统一约定**。
6. **饰品槽 API 集成层**：`integration/` 9+ 文件按前置分组（`accessories/`、`trinkets/`、`curios/`、`lootr/`、`origins/`），`integration/ModCompat.java` 用 `ModInfo` 记录 mod id + 别名 + **supersededBy（被谁取代）**，例如 `ORIGINS = new ModInfo("origins", ORIGINS_LEGACY, NEOFORGE)`；`isLoaded()` 里先判 supersededBy 再判 id/alias（`ModCompat.java:63-75`）。
7. **世界生成/战利品**：`world/`（`CampsiteFeature` 营地结构 + 一堆自定义 `PlacementModifier`：`SurfaceFlatnessFilter`、`CampsiteHeightRangePlacement` 等）、`loot/`（`ArtifactRarityAdjustedChance`、`ConfigValueChance`、`ReplaceWithLootTableFunction`、`ConfigValueCondition`——**把 config 值做成战利品条件/函数/结构放置判定**，实现"配置直接控制世界生成"）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：不直接用加载器 API，而是 common 侧 `network/NetworkHandler.java` 维护 `SERVERBOUND_HANDLERS` / `CLIENTBOUND_HANDLERS` 两个 `List<PayloadHandler<?>>`，`PayloadHandler` = `(Type, StreamCodec, Receiver)` record；平台侧只负责把这两个列表注册进加载器（`neoforge/network/NeoForgeNetworkHandler`、`fabric/network/FabricNetworkHandler`）。发送统一封装 `sendToServer` / `sendToPlayer` / `sendToClient(Consumer<Packet<?>>)`，**`Consumer<Packet<?>>` 这个抽象同时兼容游戏内连接与配置阶段的连接**（`NetworkHandler.java:44-56`）。5 个 payload：`DoubleJumpPacket`、`PlaySoundAtPlayerPacket`、`ToggleKeyPressedPacket`、`UpdateConfigValuePacket`、`UpdateSwimFlyingPacket`。
- **数据驱动**：`neoforge/condition/ConfigValueCondition.java` + `ModConditions`（把 config 变成数据包条件）、`DataMaps`、`ModLootTables`、`ModTags`。
- **配置**：见上（night-config + 自研同步）；另有 `config/screen/ArtifactsConfigScreen` 基于 Cloth Config + Mod Menu（NeoForge 通过 `IConfigScreenFactory` 扩展点注册，`ArtifactsNeoForge.java:64-71`）。
- **datagen**：**很完整**，`neoforge/data/` 下 `Recipes`、`LootTables`、`LootModifiers`、`Language`、`ItemModels`、`SoundDefinitions`、`Advancements`、`ConfiguredFeatures`、`PlacedFeatures`、`DataMaps`、`EntityEquipment` + `data/tags/*`（Item/Block/EntityType/DamageType/GameEvent/MobEffect 六类 tag）；`ArtifactsData.java` 统一挂到 `GatherDataEvent`。**语言文件也是 datagen 产出**（`Language.java` 308 行 + `lang/LangEntry` 体系）。

## 6. Mixin

- 3 份配置：`common/src/main/resources/artifacts.common.mixins.json`、`fabric/.../artifacts.fabric.mixins.json`、`neoforge/.../artifacts.neoforge.mixins.json`；`compatibilityLevel: JAVA_25`、`required:true`、`mixinextras.minVersion: 0.5.0`、`overwrites.requireAnnotations: true`、`injectors.defaultRequire: 1`。
- **`plugin: artifacts.ArtifactsMixinPlugin`**：`shouldApplyMixin` 里按包名约定自动判定 mod 兼容——凡是 `artifacts.mixin.compat.<modid>.*` / `artifacts.fabric.mixin.compat.*` / `artifacts.neoforge.mixin.compat.*` 的 mixin，只在该 mod 已加载时应用（`ArtifactsMixinPlugin.java:36-44`）。**这是"兼容 mixin 自动开关"的干净实现**。
- 代表性 hook：
  - `mixin/ability/LivingEntityMixin` → `LivingEntity#actuallyHurt`，用 MixinExtras `@ModifyReceiver` 在 `setHealth(F)V` 调用处拦截，拿到"最终伤害值"（注释明说为了在护甲/效果之后取值）；`causeFallDamage` 用 `@Definition`/`@Expression` + `@Local(name="dmg")` 拿局部变量；`handleEquipmentChanges` HEAD 抓装备变化。
  - `mixin/attribute/LivingEntityMixin` / `attribute.PlayerMixin` → 动态属性修饰符；`attribute.eatingspeed.ConsumableMixin`、`attribute.villagerreputation.VillagerMixin`、`attribute.invincibilityticks.LivingEntityMixin` 同理。
  - 客户端：`client/LivingEntityRendererMixin`、`client/LivingEntityRenderStateMixin`、`ability.nightvision.client.GameRendererMixin`、`item.umbrella.client.ItemInHandRendererMixin`、`accessors.client.GuiAccessor`；服务端专属：`item.umbrella.server.ServerGamePacketListenerImplMixin`（json 里单独 `server` 段）。

## 7. 值得学的 5 条具体做法

1. **能力用 DataComponent 表达，不用继承**：`ArtifactProperties`（`item/ArtifactProperties.java:95-201`）+ `ModDataComponents`（`registry/ModDataComponents.java`）——新增饰品只写 builder 链，可复用于任何物品甚至原版物品。
2. **饰品槽抽象 `EquipmentSlotProvider` + `iterateEquipment/reduceEquipment`**（`equipment/EquipmentSlotManager.java:22-58`）：一套代码同时适配 Curios / Trinkets / Accessories / 原版护甲槽，上层零感知。
3. **配置值直接当"战利品条件/结构放置判定"用**：`loot/ConfigValueCondition.java`、`loot/ConfigValueChance.java`、`world/placement/ConfigValueFilter.java` —— 让配置文件变成数据包级别的开关。
4. **config 值可声明 `syncToClients()` 并走 MC 的配置阶段下发**（`ConfigManager.java:192-207` + `ArtifactsNeoForge.java:73-89` + Fabric `CONFIGURE` 事件），客户端断连后回读本地值（`Artifacts.java:102-108`）——**双端 mod 同步配置的正确姿势**。
5. **MixinExtras 的 `@ModifyReceiver` / `@Expression` + `@Local`**：`ability/LivingEntityMixin.java` 用它们替代复杂的 `@Redirect` + `CallbackInfoReturnable` 计算，可读性明显更高；配合 `overwrites.requireAnnotations: true` 强制所有 overwrite 写注释。

## 8. 公开 API / 扩展点

非库模组，无对外 API 包。但它是**"如何接入饰品槽 API"的最佳参考**：`integration/{accessories,trinkets,curios}/` 三套 `*SlotProvider` + `*Compat` + `*RenderingHandler` 成对实现；`integration/ModCompat.java` 的 `ModInfo`（mod id + 别名 + supersededBy）是判断"哪个饰品前置实际生效"的现成方案。上游必读 API：`be.florens.expandability`（水下行走等）、NeoForge `DataComponent` / `AttachmentType` / `Condition`、Fabric `LootTableEvents`。

**注意（对本项目 1.21.1 目标的适配）**：本快照是 MC 26.1.2 / Java 25 版本，`Identifier` 替代了 `ResourceLocation`、`DataComponentInitializers` 等 API 与 1.21.1 不同；读取时需注意版本差异，但上述架构（数据组件能力、槽位抽象、配置同步、mixin 事件桥）在设计层可直接照搬。
