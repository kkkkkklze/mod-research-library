# MehVahdJukaar/DuMmmMmmy 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：MmmMmmMmmMmm（"目标假人"）/ `dummmmmmy`（`gradle.properties`：`mod_name=MmmMmmMmmMmm`、`mod_version=1.21-2.1.1`）
- 作者 / 许可证：Mehvahdjukaar（`mod_authors` 另列 Bonusboni、Gooigipunch、Plantkillable）；**Supplementaries Team License v.1.5**
- 目标版本：Minecraft **1.21.1**、Java 21、Parchment `2024.11.17`
- 加载器：**NeoForge 21.1.248** + **Fabric**（loader 0.19.3、fabric-api 0.116.15+1.21.1），三模块结构 `common / fabric / neoforge`（Gradle **KTS**）
- Gradle 插件：作者自研 `com.possible-triangle.core` / `.common` / `.fabric` / `.neoforge` + `net.mehvahdjukaar.candlelight 1.2.4`（多加载器脚手架，仓库外提供）
- 编译/运行依赖（重点）：**Moonlight (Selene) `1.21.1-3.3.4` 为硬依赖**（`neoforge/mods.toml:37-44` → `modId="moonlight"` required，range `[1.21-3.2.3,)`；Modrinth 侧声明 `required("moonlight")`）；`codecui 1.21.1-1.3.6`（注释写明 "Declarative codec schema API, needed at runtime by moonlight"）；可选兼容 `critical_strike 1.0.2+1.21.1`（`Dummmmmmy.CRITICAL_STRIKE = PlatHelper.isModLoaded("critical_strike")`，`Dummmmmmy.java:46`）。即：本 mod 是**消费 Moonlight API 的样板**，注册/网络/配置/客户端注册全部调用 moonlight 的 `RegHelper`/`NetworkHelper`/`ClientHelper`。

## 2. 源码规模与包结构

实测 **36 个 `.java` / 3179 行**（common 30、fabric 4、neoforge 2）。

包与文件数（`net.mehvahdjukaar.dummmmmmy`）：`client` 9（粒子/模型/渲染器/4 个装备图层/配置界面 showcase）、`mixins` 6、`common` 5、`configs` 3、`network` 3、根包 3、`compat` 1；`fabric` 侧 4（`platform/DummmmmmyFabric`、`platform/DummyPlatStuffImpl`、`mixins/fabric/MobMixin`、`integration/platform/ModMenuCompat`）；`neoforge` 侧 2（`platform/DummmmmmyForge`、`platform/DummyPlatStuffImpl`）。

最大文件：`common/TargetDummyEntity.java` **928**、`client/DamageNumberParticle` 222、`configs/ClientConfigs` 193、`client/TargetDummyModel` 179、`Dummmmmmy.java` 145、`client/DummyShowcaseWidget` 134、`network/ClientBoundDamageNumberMessage` 130、`common/ModEvents` 126。

资源侧可见：`common/src/main/resources/dummmmmmy-common.mixins.json`、`dummmmmmy.accesswidener`（本仓库是 sparse checkout，`fabric.mod.json`、贴图、lang、model json 未下载）。

## 3. 入口与注册

common 无 `@Mod`/`ModInitializer`，主类是 `Dummmmmmy`，由平台入口调用其 `init()`：

```java
// Dummmmmmy.java:52-66
public static void init() {
    if (PlatHelper.getPhysicalSide().isClient()) { DummmmmmyClient.init(); ClientConfigs.init(); ... }
    ModMessages.init();
    CommonConfigs.init();
    PlatHelper.addCommonSetup(Dummmmmmy::setup);
    RegHelper.addAttributeRegistration(Dummmmmmy::registerEntityAttributes);
    RegHelper.addItemsToTabsRegistration(Dummmmmmy::registerItemsToTab);
}
```

NeoForge 入口 `neoforge/.../platform/DummmmmmyForge.java:28-35`：`@Mod(Dummmmmmy.MOD_ID)` 构造器里 `RegHelper.startRegisteringFor(bus); Dummmmmmy.init(); NeoForge.EVENT_BUS.register(this);`，并用 `@SubscribeEvent` 监听 `CriticalHitEvent`、`FinalizeSpawnEvent`、`EntityJoinLevelEvent`（转发给 `ModEvents`）。Fabric 入口 `fabric/.../platform/DummmmmmyFabric.java` 同构 + `ModMenuCompat`。

注册框架：**无 DeferredRegister/Registrate**，全部是 Moonlight 的 `RegHelper.registerXxx`（`Supplier<T>` 惰性 + 事件驱动），也即 Mod 自身把"注册框架"外包给前置。注册内容（`Dummmmmmy.java:105-133`）：`TARGET_DUMMY`(`EntityType<TargetDummyEntity>`，MobCategory.MISC、`clientTrackingRange(10)`、`updateInterval(40)`、`sized(0.6f,2f)`)、`DUMMY_ITEM`、`NUMBER_PARTICLE`/`HAY_PARTICLE` 两个 `SimpleParticleType`、4 个物品 tag（各类生物头颅）+ 5 个 `DamageType` tag（is_thorn/is_fire/is_explosion/is_wither/is_cold）；`HolderReference<DamageType>` 用 moonlight API 做延迟持有（`TRUE_DAMAGE`/`CRITICAL_DAMAGE`）。客户端注册集中在 `DummmmmmyClient.init()`（`ClientHelper.addModelLayerRegistration/addEntityRenderersRegistration/addParticleRegistration`，另注册配置界面的"可击打假人"展示组件 `ConfigScreenExtensions.registerShowcase`）。

## 4. 核心系统

1. **假人实体 `common/TargetDummyEntity.java`（928 行，extends `Mob`）**：木桩语义——`xpReward=0`、`setCanPickUpLoot(false)`、`armorDropChances` 全 1.1f、`playersTracker.showHealthBar(...)`；统计字段 `lastTickActuallyDamaged`（同 tick 多来源合并）、`totalDamageTakenInCombat`/`totalHealingTakenInCombat`、`critRecordsThisTick`（`List<CritRecord>`）；血量用 `ServerBossEvent` 呈现（`PlayersTracker.showHealthBar`）；`healthRechargeTimer`(`HEALTH_RECHARGE_TIME=160`)/`shieldCooldown`(`SHIELD_COOLDOWN=100`) 两个常量做战斗节奏；`SynchedEntityData.defineId` 同步 `SHEARED`（剪毛）与 `BOSS` 两个布尔。
2. **装备驱动的行为状态机 `common/DummyMobType.java`**：enum `UNDEFINED/UNDEAD/AQUATIC/ARTHROPOD/NETHER_MOB/SCARECROW/DECOY`，`setItemSlot(HEAD)` 时 `this.mobType = DummyMobType.get(stack)`（`TargetDummyEntity.java:145-151`）；`get(ItemStack)` 纯靠 tag + 名字判断（南瓜=稻草人 → `canScare()`、玩家头=诱饵 → `canAttract()`），并提供 `isInvertedHealAndHarm()`/`ignoresPoisonAndRegen()`/`isVulnerableTo(Enchantment)`/`freezeHurtsExtra()` 模拟原版亡灵/节肢 tag 语义（注释："mimics old behavior now driven by tags in a dynamic manner"）。
3. **伤害数字与动画同步**：`network/ClientBoundDamageNumberMessage` 是 `record` + moonlight `Message` 接口，`TYPE = Message.makeType(res("s2c_damage_number"), …)`，字段 `entityID/damageAmount/Holder<DamageType>/isCrit/critMult`，用 `DamageType.STREAM_CODEC` 编码；客户端在 `handle` 里 `Minecraft.getInstance().level.getEntity(id)` 并调 `dummy.getNextNumberPos()` 在半圆上排布飘字位置（`damageNumberPos` 字段），另有 `ClientBoundUpdateAnimationMessage` 同步动画相位。
4. **伤害/治疗/暴击事件总线**：`common/ModEvents`（`@EventCalled` 标注）由 mixin 与平台事件调用：`onEntityDamage(entity, mitigatedAmount, source)`、`onEntityHeal(entity, actualHealAmount)`、`onEntityCriticalHit(attacker, target, damageModifier)`、`onCheckSpawn`、`onEntityJoinWorld`（给生物加 `AvoidEntityGoal`/`NearestAttackableTargetGoal` 实现稻草人/诱饵行为）；`compat/CritCompat` 抽象 critical_strike 兼容。
5. **客户端呈现**：`client/TargetDummyRenderer` + `TargetDummyModel`（3 个 `ModelLayerLocation`：body/armor_outer/armor_inner）+ 4 个装备图层（Armor/Cape/Elytra/Shield）+ `DamageNumberParticle`/`HayParticle`；配置界面用 `DummyShowcaseWidget` 替换 mod 图标。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：Moonlight `NetworkHelper.addNetworkRegistration(ModMessages::registerMessages, 2)`（**协议版本号 2**，`network/ModMessages.java:8-15`），只 `event.registerClientBound(...)` 两个包；序列化手工 `write(RegistryFriendlyByteBuf)` / 静态 `of(buf)` 工厂。
- 数据驱动：仅 tag（`EntityTypeTags.SENSITIVE_TO_IMPALING` 用于 `EntityPredicate`，5 个 `DamageType` tag，4 个头颅 tag）；**无 codec/registry 数据加载**。
- 配置：Moonlight 配置体系，`configs/CommonConfigs`(92)、`configs/ClientConfigs`(193)、enum `CritMode`（暴击显示模式）；`ClientConfigs.DAMAGE_NUMBERS`/`HAY_PARTICLES` 直接控制客户端表现。
- datagen：仓库内无 `data`/Provider 类，**未确认**（也可能由 candlelight 插件在构建期生成，源码不在本仓库）。

## 6. Mixin

配置：`common/src/main/resources/dummmmmmy-common.mixins.json`（package `…dummmmmmy.mixins`，6 个，`defaultRequire=1`）+ `fabric/src/main/resources/dummmmmmy.mixins.json`（`…mixins.fabric`，1 个 `MobMixin`）+ neoforge 同名空配置；三者在 `neoforge.mods.toml:7-10` 以两段 `[[mixins]]` 加载。另有 accesswidener 打开 `CombatTracker.entries/lastDamageTime/inCombat`（`common/src/main/resources/dummmmmmy.accesswidener`）。

代表 hook（MixExtras 风格为主）：
- `LivingEntityMixin`：`@WrapOperation(method="actuallyHurt", at=INVOKE LivingEntity.setHealth(F))` 用"实际掉的血压差"上报伤害（`LivingEntityMixin.java:23-33`）；`heal` 同理上报"实际治疗量"；`hurt` 里 `@ModifyExpressionValue` 改 `EntityType.is(TagKey)`（ordinal 0）使假人按 `mobType.freezeHurtsExtra()` 受冻伤（:48-53）
- `PlayerMixin#actuallyHurt`（`@WrapOperation` `Player.setHealth`）；`SwordItemMixin`/`ToolItemMixin#hurtEnemy`（`@Inject HEAD`，武器命中假人时上报）；`EnchantmentMixin` 多处 `@WrapOperation`/`@ModifyExpressionValue` 拦 `ConditionalEffect.matches`（亡灵类附魔的反向效果）；`ArmorStandFIxMixin` 拦 `ArmorStandItem#useOn` 中的 `ArmorStand.moveTo`；fabric `MobMixin#<init>`（在 `Mob.registerGoals()` 调用点注入）。

## 7. 值得学的 5 条具体做法

1. **用 `@WrapOperation` 包 `setHealth(F)` 而不是 `@Inject`**，直接取"实际生效的掉血/回血量"（`mixins/LivingEntityMixin.java:23-46`）——做伤害统计、反馈、成就判定时不受其它 mod 减伤影响，MixExtras 的典型正确用法。
2. **统一走 MixExtras 而非 `@Inject`+locals**：同文件 `@ModifyExpressionValue` 改 `EntityType.is(TagKey)` 的布尔值（:48-53），比 `@Redirect` 更稳。
3. **装备槽驱动 enum 状态机**（`DummyMobType.get(ItemStack)` + `setItemSlot`，`TargetDummyEntity.java:145-151`）：一个实体靠头部装备变成亡灵/水生/节肢/稻草人/诱饵，行为与附魔抗性都由 enum 派生。
4. **服务端按 tick 聚合、客户端按索引排布**：每 tick 合并同来源伤害只发一个包，客户端用 `getNextNumberPos()` 在半圆上分配飘字位置（`TargetDummyEntity.java:83-84` + `ClientBoundDamageNumberMessage`）。任何"飘字"需求可直接照搬。
5. **common 静态门面 + 平台 Impl 替代 Architectury `@ExpectPlatform`**：`DummyPlatStuff`（common，:11）对 `fabric|neoforge/.../DummyPlatStuffImpl`，入口类只做"注册事件 + 调 init"（`DummmmmmyForge.java:29-34`）。配合 Moonlight 的 `RegHelper`/`ClientHelper`/`PlatHelper`，整个 mod 只有 2 个平台专有 Java 文件。

## 8. 公开 API 与外部接入方式

非库模组，不提供对外 API；反向依赖只有可选 `critical_strike`（通过 `PlatHelper.isModLoaded` 软探测，具体接入代码在对方仓库，**未确认**）。可作为"1.21.1 双加载器 + Moonlight 前置 + 实体/渲染/网络全套"的最小完整样例。
