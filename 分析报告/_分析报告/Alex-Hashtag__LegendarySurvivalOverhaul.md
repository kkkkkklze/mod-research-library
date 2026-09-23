# Alex-Hashtag/LegendarySurvivalOverhaul 源码分析报告

## 1. 基本信息

Legendary Survival Overhaul / mod_id `legendarysurvivaloverhaul` / 作者 Sfiomn（credits Charles445、Icey）/ 许可证 **MIT**。`gradle.properties`：MC `1.21.1`、NeoForge `21.1.197`、`mod_version=2.4.7.2`、Java 21、mapping `official`；构建插件 `net.neoforged.gradle.userdev 7.0.192`（`build.gradle:5`），无 mixin 相关配置、无 AT 文件。实际依赖：JEI `19.21.2.313`、Curios `9.5.1+1.21.1`；`neoforge.mods.toml` 声明 10+ 个 **optional** 集成依赖（sereneseasons、curios、beachparty、meadow、eclipticseasons 等，`ordering=BEFORE`）。Origins 集成在 gradle 中被 `sourceSets.main.java.exclude` 整体排除（`build.gradle:63-70`）。

## 2. 规模与包结构

实测 **481 个 `.java`、38202 行**。主要包：`api/{data/{builder,json,manager,providers},temperature,thirst,bodydamage,health,wetness,food,item,block}`、`common/{attachments(.temperature,.thirst,...),temperature(.attribute,.dynamic),listeners,events,effects,items,integration(18 个子包),blocks,containers,loot_modifiers,recipe,tags}`、`client/{render,screens,tooltips,effects,itemproperties,shaders}`、`data/{providers,integration/providers(104 文件),builders,loot}`、`network/payloads(21)`、`registry(16)`、`config`、`util`。最大文件：`config/Config.java` 1908、`config/json_old/JsonConfigRegistration` 914、`common/attachments/bodydamage/BodyDamageAttachment` 690、`common/events/CommonNeoForgeEvents` 665、`common/integration/IntegrationController` 657、`client/screens/BodyHealthScreen` 586、`api/data/json/JsonConfig` 501、`common/attachments/thirst/ThirstAttachment` 385、`util/internal/BodyDamageUtilInternal` 361、主类 335。

## 3. 入口与注册

`LegendarySurvivalOverhaul.java:104` 构造 `(IEventBus, ModContainer)`：`ModAttachments.init` → `DataComponentRegistry.init` → `Config.register()` → **15 个注册类**（Attribute/Item/MobEffect/LootModifier/Block/Container/ParticleType/Recipe/Sound/**TemperatureModifierRegistry**/BlockEntity/Feature/CreativeTab/ArmorMaterial）→ `forgeBus.addListener(CommandRegistry::registerCommandsEvent)` → `modIntegration()`（用 `ModList.get().isLoaded` 逐个开 18 个兼容模块并 `forgeBus.register(...Events.class)`）。核心装配模式在 `commonSetup`（`:228`，`event.enqueueWork` 内）：**API 门面注入实现** `TemperatureUtil.internal = new TemperatureUtilInternal()` 以及 `TemperatureDataManager.internalItem = new TemperatureItemListener()` 等 14 个；`AddReloadListenerEvent`（`:291`）把这 14 个 listener 挂成资源重载监听器。配置走 `ModConfigEvent.Loading/Reloading` → `Config.Baked.bakeCommon()/bakeClient()` 烘焙静态缓存。

## 4. 核心系统

**A. 注册表驱动的温度管綫** —— `registry/TemperatureModifierRegistry.java` 自建 3 个 `ResourceKey<Registry<...>>`（`temperature_modifiers`、`dynamic_temperature_modifiers`、`item_attribute_temperature_modifiers`），注册 **16 个 base modifier**（altitude/biome/blocks/dimension/mount/freeze/on_fire/player_huddling/sprint/time/weather/wetness 及季节/TFC 集成）+ 2 个 dynamic + 3 个 attribute。`api/temperature/ModifierBase` 只有两个扩展点 `getPlayerInfluence(player)` / `getWorldInfluence(@Nullable player, level, pos)`，并提供工具 `clampNormalizeTemperature`（把原版 -0.5~2.0 归一到 0~1）、`applyUndergroundEffect`。计算在 `util/internal/TemperatureUtilInternal.java:64`：遍历 `MODIFIERS.getEntries()` 累加，再把累加值交给 `DYNAMIC_MODIFIERS` 二次调整（如 `TemperatureResistanceModifier`、`MountDynamicModifier`），持有 `Items.DEBUG_STICK` 时逐项打印贡献值。

**B. Attachment 生存数值层** —— `common/attachments/ModAttachments.java:21` 用 NeoForge `AttachmentType.serializable(X::new).copyOnDeath()` 注册 temperature/wetness/thirst/health/body_damage（`food` 故意用 `AttachmentType.builder(...)` 纯运行时、不持久化；`:61` 注释说明 1.21 起不支持 ItemStack attachment，改用 DataComponent）。每个附件实现 `tickUpdate(player, level, isStart)` + `isDirty()/setClean()`。

**C. 脏标记驱动的同步** —— `common/events/CommonNeoForgeEvents.java:571` `PlayerTickEvent.Post` 里按配置逐要素 tick，脏了就 `UpdateTemperaturesPayload.sendToPlayer(serverPlayer, writeNBT())` 再 `setClean()`；`ThirstAttachment.java:62` 完整复刻饥饿机制：每 10 tick 检查位移（`oldPos.distanceTo > 1`，防止挂机渴死）→ 累积 exhaustion，>4 时先扣 saturation 再扣 hydration，归零后每 80 tick 按 `damageCounter * dehydrationDamageScaling` 递增伤害，且只对 `DifficultyUtil.healthAboveDifficulty(player)` 生效。

**D. 网络** —— `network/NetworkHandler.java:20` 在 `RegisterPayloadHandlersEvent` 中用 `event.registrar(MOD_ID).versioned("1")` 注册 **21 个** `playBidirectional(TYPE, STREAM_CODEC, new DirectionalPayloadHandler<>(X::handle, X::handle))`，分两类：`Update*Payload`（单玩家状态脏同步）与 `Sync*Payload`（整张 JSON 数据表在数据包重载/玩家登录后推给客户端）。

**E. JSON 数据表** —— `common/listeners/TemperatureItemListener.java` 同时是 `SimpleJsonResourceReloadListener`（路径 `legendarysurvivaloverhaul/temperature/items`）与 `ITemperatureItemManager` 实现：用 Codec 解析后**只接受 `ModList.get().isLoaded(key.getNamespace())` 的命名空间**，读取统一走静态门面 `api/data/manager/TemperatureDataManager.getXxx()`。同类数据还有 thirst、body_damage（`common/listeners` 共 15 个）。

**F. 跨 mod 兼容数据的 datagen** —— `data/providers` 19 个 provider，`data/integration/providers` **104 个**（每个联动 mod 一份），把数据生成到**别人的命名空间**下，如 `src/generated/resources/data/beachparty/legendarysurvivaloverhaul/temperature/items/*.json`；生成 API 是 `api/data/providers/TemperatureDataProvider`（抽象 `DataProvider`，9 个 `PathProvider`）+ `api/data/builder/` 16 个接口 + `data/builders` 实现。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：21 个 payload（见 D），无自定义 channel 之外的机制。
- 数据驱动：`data/<任意命名空间>/legendarysurvivaloverhaul/{temperature/{items,blocks,biomes,consumables,consumable_blocks,fuel_items,dimensions,mounts,origins},thirst/*,body_damage/*}` 下的 JSON；温度修饰器本身也在 datapack-able 注册表中。
- 配置：`config/Config.java`（1908 行，ModConfigSpec，CLIENT/COMMON 双 spec）+ `Config.Baked` 静态烘焙缓存（每 tick 读的都是烘焙值）；`config/json_old/` 保留旧版 JSON 配置（`JsonConfigRegistration` 914 行）做迁移。
- datagen：`Mod*Provider` + `Minecraft*Provider`（物品/方块/多语言/配方/战利品/标签/BM 内建项）与 104 个集成 provider，`runs { data }` 输出 `src/generated/resources`。

## 6. Mixin

**无**。全仓无 mixin 配置文件与 `@Mixin` 类；对原版与自身逻辑的介入全部通过 NeoForge 事件（`PlayerTickEvent.Post`、`ItemAttributeModifierEvent`、`LivingIncomingDamageEvent`、`LivingDamageEvent.Pre`、`MobEffectEvent.Applicable`、`SleepFinishedTimeEvent`、`OnDatapackSyncEvent` 等，见 `common/events/CommonNeoForgeEvents.java`）、自定义注册表与 Attachment 实现。

## 7. 值得学的 5 条具体做法

1. **API 门面 + `internal` 实现注入**：`api/*Util` 全是静态转发（`TemperatureUtil.internal.xxx()`），实现在 `util/internal` 里装配（`LegendarySurvivalOverhaul.java:232-254`）——API 包对外稳定、实现可换，且避免了静态初始化顺序坑。
2. **修饰器做成可注册表 + 单一累加管线**：新增一种温度来源只需注册一个 `ModifierBase`（`api/temperature/ModifierBase.java`），带 DEBUG_STICK 逐项日志，调参成本极低。
3. **要素状态用 Attachment + 脏标记增量同步**：`isDirty/setClean` 只在值变化时发 payload（`ThirstAttachment.java:158`、`CommonNeoForgeEvents.java:571`），避免每 tick 全量发包。
4. **数据表读取加命名空间白名单**：`if (ModList.get().isLoaded(key.getNamespace()))`（`TemperatureItemListener.java:63`）——同一套解析代码服务多个 mod 的命名空间而不会读到未安装 mod 的数据。
5. **把"兼容补丁"做成 datagen**：104 个集成 provider 直接生成到对方命名空间（`data/integration/providers/`），兼容逻辑不写死在运行时，且可被数据包覆盖。

## 8. 公开 API

- 包路径：`sfiomn.legendarysurvivaloverhaul.api.{temperature,thirst,bodydamage,health,wetness,food,item,block,data}`。
- 门面与接口：`TemperatureUtil`/`ThirstUtil`/`BodyDamageUtil`/`HealthUtil`/`WetnessUtil`（静态）+ 对应 `I*Util`（`ITemperatureUtil` 含 `getPlayerTargetTemperature`、`getWorldTemperature`、`addTemperatureModifier`、`add{Heat,Cold,Thermal}ResistanceModifier`、`setArmorCoatTag` 等）。
- 扩展点：1) 向 mod 事件总线注册自定义 `ModifierBase` / `DynamicModifierBase` / `AttributeModifierBase` 到三个注册表（`registry/TemperatureModifierRegistry.java:32`）；2) 数据包放置 JSON 数据（温度/口渴/身体伤害），或调用 `api/data/manager/*DataManager.getXxx()` 读取他人数据；3) 用 `api/data/providers/*DataProvider` + `api/data/builder/*` 为自己的 mod 生成兼容数据；4) `AttachmentUtil`（`util/`）提供各 `I*Attachment` 的读写入口供第三方联动。
