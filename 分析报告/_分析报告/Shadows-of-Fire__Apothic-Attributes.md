# Shadows-of-Fire/Apothic-Attributes 源码分析报告

> 注意：本副本检出的是 **`26.1` 分支**（`git log` 顶部 `100e648 Migrate to MPPv2`），非 1.21.1。`gradle.properties` 记载 `mcVersion=26.1.2`、`javaVersion=25`、`forgeVersion=26.1.2.70-beta`、`mixinVersion=0.8.7`。下述内容以该分支为准，包结构与 API 形态可作参考，具体符号名在旧版本上可能不同。

## 1. 基本信息

- Mod 名：Apothic Attributes（旧名 AttributesLib）；mod_id：`apothic_attributes`；作者 Shadows_of_Fire；版本 3.0.1；`desc=A library mod providing Attributes and related things.`
- 目标：MC 26.1.2 / NeoForge 26.1.2.70-beta / Java 25；`modLoaders=NeoForge`
- 构建：Gradle + `net.neoforged.moddev 2.0.141` + `com.diffplug.eclipse.apt` + `me.modmuss50.mod-publish-plugin 2.0.0`
- **依赖（关键）**：`requiredDeps=placebo`，`implementation "dev.shadowsoffire:Placebo:${mcVersion}-${placeboVersion}"`（placeboVersion=10.0.0）——Placebo 提供 `DeferredHelper`、`Configuration`、`PayloadHelper`、`DataGenBuilder` 等基础设施；`curiosVersion=15.0.0-beta.2+26.1.2` 真依赖（`CuriosCompat.java`）；JEI 29.5.0.26 / Jade 26.0.9 仅 `localImplementation`（dev 运行）；`.gitignore` 级可选：Patchouli/Bookshelf/GameStages/Twilight Forest/Gateways。发布坐标 `dev.shadowsoffire:ApothicAttributes:${mcVersion}-${version}`（`build.gradle` publishing 段）。
- 许可证：仓库根**无 LICENSE 文件**（`build.gradle` 会读其首行填入 toml，本副本缺失，未确认实际许可证）；`modifiers/StackAttributeModifiersEvent.java` 头部保留 Forge 的 `SPDX-License-Identifier: LGPL-2.1-only`（该文件改写自 Forge）。

## 2. 源码规模与包结构

48 个 `.java`，5819 行。包（`dev.shadowsoffire.apothic_attributes`）：`api`(5)、`modifiers`(6)、`client`(6)、`mixin`(6+1 client)、`mob_effect`(7)、`impl`(1)、`util`(5)、`compat`(2)、`payload`(2)、`data`(1)、`commands`(1)、`event`(1)、`repack/evalex`(1)。
最大文件：`repack/evalex/Expression.java`(1061，内嵌表达式求值库)、`client/AttributesGui.java`(582)、`impl/AttributeEvents.java`(468)、`api/ALObjects.java`(454)、`modifiers/StackAttributeModifiersEvent.java`(272)、`client/AttributesLibClient.java`(233)、`util/AuxDmgTracker.java`(218)、`ApothicAttributes.java`(216)、`ALConfig.java`(213)、`api/ALCombatRules.java`(171)、`mixin/LivingEntityMixin.java`(164)。

## 3. 入口与注册

`src/main/java/dev/shadowsoffire/apothic_attributes/ApothicAttributes.java:56` `@Mod`。不使用 DeferredRegister，而用 Placebo 的 `DeferredHelper R = DeferredHelper.create(MODID)`（:59）。

```java
public ApothicAttributes(IEventBus bus) {
    bus.register(this);
    NeoForge.EVENT_BUS.register(new AttributeEvents());
    NeoForge.EVENT_BUS.addListener(ApothicAttributes::trackAttackStrength);
    NeoForge.EVENT_BUS.addListener(ApothicAttributes::pruneCooldowns);
    if (FMLEnvironment.getDist().isClient()) { NeoForge.EVENT_BUS.register(new AttributesLibClient()); bus.register(AttributesLibClient.ModBusSub.class); }
    PayloadHelper.registerPayload(new CritParticlePayload.Provider());
    ALObjects.bootstrap(bus);
    NeoForgeMod.enableMergedAttributeTooltips();
}
```

关键注册点：`applyAttribs(EntityAttributeModificationEvent)` 对 `e.getTypes()` 全部实体类型批量挂上 21 个自定义属性（:100-127）；`setup(FMLCommonSetupEvent)` 里遍历 `BuiltInRegistries.ATTRIBUTE`，对 `DefaultAttributes.getSupplier(EntityType.PLAYER)` 拥有的属性统一 `setSyncable(true)`，再按需 `CuriosCompat::init`（:135-145）。

## 4. 核心系统

**（1）自定义属性集合（API 主干）** — `api/ALObjects.java`
内部分组类：`BuiltInRegs`（注册 `Registry<EntityEquipmentSlot>` 与 `Registry<EntitySlotGroup>`，均 `c.sync(true)`）、`Attributes`（`ARMOR_PIERCE/ARMOR_SHRED/ARROW_DAMAGE/ARROW_VELOCITY/COLD_DAMAGE/CRIT_CHANCE(基值0.05)/CRIT_DAMAGE(1.5)/CURRENT_HP_DAMAGE/DODGE_CHANCE/DRAW_SPEED/EXPERIENCE_GAINED/FIRE_DAMAGE/GHOST_HEALTH/HEALING_RECEIVED/LIFE_STEAL/OVERHEAL/PROJECTILE_DAMAGE/PROT_PIERCE/PROT_SHRED/ELYTRA_FLIGHT(BooleanAttribute)/COOLDOWN_REDUCTION`，统一 `R.attribute(...).setSyncable(true)`）、`MobEffects`（`extends net.minecraft.world.effect.MobEffects` 只为把原版常量引入作用域）、`Particles/Sounds/DamageTypes/Potions`（含 `R.singlePotion("resistance", ...)` 等批量药水）。

**（2）战斗公式（可配置 + 可外部调用）** — `api/ALCombatRules.java`
公开 `getDamageAfterProtection / getProtDamageReduction / getDamageAfterArmor / getAValue / getArmorDamageReduction / getBypassResistance`。每个公式**先查配置表达式**再回退硬编码默认，例如 `getProtDamageReduction` 默认 `1 - Math.min(0.025F*protPoints, 0.85F)`，若 `ALConfig.getProtExpr()` 存在则 `get().setVariable("protPoints", new BigDecimal(protPoints)).eval().floatValue()`。护甲改用 `DR = A/(A+armor)`，`A = damage < 20 ? 10 : 10 + (damage-20)/2`；护甲穿透被护甲韧性抵消（`getBypassResistance = min(toughness*0.02, 0.6)`）。

**（3）可扩展装备槽 / 槽组（数据驱动）** — `modifiers/`
`interface EntityEquipmentSlot { Iterable<ItemStack> getStacks(LivingEntity entity); }`（注释明确是 `EquipmentSlot` 的可扩展版本，配 `EquipmentSlotCompat`/`VanillaEquipmentSlot` 做互操作）；`record EntitySlotGroup(Identifier id, HolderSet<EntityEquipmentSlot> slots) implements Predicate<Holder<EntityEquipmentSlot>>`，带 `CODEC = BuiltInRegs.ENTITY_SLOT_GROUP.byNameCodec()` 与 `STREAM_CODEC = ByteBufCodecs.registry(...)` —— 槽组是可被数据包/JSON 引用的注册对象。

**（4）物品属性修改事件** — `modifiers/StackAttributeModifiersEvent.java`
在 `ItemStack#getAttributeModifiers()` 被查询时触发（有无 `ATTRIBUTE_MODIFIERS` 组件都会触发），提供 `addModifier(Holder<Attribute>, AttributeModifier, EntitySlotGroup)`、`removeModifier`、`replaceModifier`、按条件批量删除，内部用 `StackAttributeModifiersBuilder`，`getModifiers()` 返回只读视图并警告"别用返回值构造 StackAttributeModifiers"。javadoc 强调：modifier 的 `Identifier` 必须唯一且稳定，否则卸下装备时不会被移除。

**（5）冷却系统（分层 API）** — `api/AbilityCooldowns.java` + `api/CooldownTracker.java`
对外只用 `AbilityCooldowns`（`isOnCooldown/startCooldown/getRemaining/applyCDR/clear`），自动按 `COOLDOWN_REDUCTION` 属性缩放 `baseCooldown`；`CooldownTracker` 是内部存储，基于 `Object2LongMap<Identifier>`（`defaultReturnValue(-1)`），`MAX_COOLDOWN_TICKS = 20*60*60*4`（4 小时），作为 synced Attachment 存在所有生物上，玩家登录时 `pruneCooldowns` 清理（`ApothicAttributes.java:196-202`）。

**（6）伤害事件流水线** — `impl/AttributeEvents.java`(468)
按优先级串起所有属性效果：`LivingDamageEvent.Pre`(LOWEST) 记录伤害前血量 → `LivingIncomingDamageEvent`(LOWEST) 近战属性 → (HIGH) 暴击 → `arrow/projDmg`(HIGHEST) → `dodge` → `LivingDamageEvent.Post` 吸血/过量治疗；并用静态 `noRecurse` 防止递归触发（:136）。`util/AuxDmgTracker.java` 用 `IdentityHashMap` + `Codec` 按 `DamageType` 记录附加伤害。`trackAttackStrength` 在 `AttackEntityEvent` 时把 `p.getAttackStrengthScale(0.5F)` 缓存进静态字段，`getLocalAtkStrength(Entity)` 供后续伤害事件读取（玩家为真实值、非玩家恒为 1）。

**（7）客户端属性 GUI** — `client/AttributesGui.java`(582) + `client/ModifierSource/ModifierSourceType`
`ModifierSourceType<T>` 是"属性来源类型"的可注册扩展点：内置 `EQUIPMENT`（遍历 `EquipmentSlot` 与 `item.forEachModifier`）与 `MOB_EFFECT`（遍历 `getActiveEffects()` 的 `attributeModifiers`），实现 `extract(LivingEntity, BiConsumer<AttributeModifier, ModifierSource<?>>)` + `getPriority()`；`CuriosCompat` 用同一套机制把 Curios 槽接进 GUI。GUI 开关/按钮位置来自 `ALConfig`（`Offset` + `AnchorPoint`），并配 `mixin/client/AbstractContainerScreenMixin` 处理拖动。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：仅 2 个 payload，且**走 Placebo 抽象**——`payload/ConfigPayload.java` 是 `record ConfigPayload(float knowledgeMultiplier) implements CustomPacketPayload`，通过内部 `class Provider implements dev.shadowsoffire.placebo.network.PayloadProvider<ConfigPayload>`（`getType/getCodec`）注册，`PayloadHelper.registerPayload(new ConfigPayload.Provider())`；另一个是 `CritParticlePayload`。
- 配置：**不用 ModConfigSpec**，用 Placebo 的 `Configuration`（`ALConfig.load()` 读写 `config/apotheosis/apothic_attributes.cfg`），全静态字段（`enableAttributesGui/hiddenAttributes/knowledgeMultiplier/negativeArmorFactor`）；`hiddenAttributes` 支持 `namespace:*` 通配与 `!id` 否定条目并按顺序处理；4 个表达式配置（`protExpr/aValueExpr/armorExpr/toughnessExpr`）用内嵌 `repack.evalex.Expression` 求值；类实现 `ResourceManagerReloadListener`。
- 数据驱动：槽组/装备槽走自定义 Registry + Codec（可被数据包引用）；`Tags`、`DamageTypes`、`Potions` 走标准注册。属性数值本身不是数据驱动（在代码里）。
- datagen：`data/MixProvider.java`（名称来自"混合"属性/药水），经 Placebo `DataGenBuilder.create(MODID).provider(MixProvider::new).build(e)` 注册到 `GatherDataEvent.Client`；`build.gradle` 的 `data` run 输出到 `src/generated/resources`，并被加入 `sourceSets.main.resources`。

## 6. Mixin

配置 `src/generated/resources/apothic_attributes.mixins.json`（**由 build.gradle 生成**，见第 7 节）：`package dev.shadowsoffire.apothic_attributes.mixin`、`compatibilityLevel: JAVA_25`、`refmap: apothic_attributes.refmap.json`、`maxShiftBy: 5`、`required: true`。mixins 段 6 个、client 段 1 个，**全部 `remap = false`**（该分支走 NeoForge 官方映射）：

- `mixin/LivingEntityMixin.java:44` — `@Mixin(value = LivingEntity.class, remap = false)`，三个 `@Redirect` 打在同一方法 `getDamageAfterMagicAbsorb`：① 把 `Math.max(FF)` 改为先叠加 Sundering 效果伤害（`value += damage*level*0.2F`）并直接改 `damageContainers.peek().setNewDamage(...)`（注释说明返回值被忽略）；② 把 `hasEffect(Holder)` 强行返回 true 以进入分支；③ `getAmplifier()` 空安全。另把 `CombatRules.getDamageAfterMagicAbsorb(FF)` 重定向到 `ALCombatRules.getDamageAfterProtection`；`canGlide()Z` 用 `@Inject(HEAD, cancellable)` 让 `ELYTRA_FLIGHT > 0` 的生物可滑翔；`updateFallFlying()V` 用 MixinExtras `@Local List<EquipmentSlot> slotsWithGliders` 在 `Util.getRandom` 前 `ci.cancel()` 防崩。
- `mixin/CombatRulesMixin.java`（`@Mixin(CombatRules.class)`）、`PlayerMixin.java:27`（`@WrapOperation` 包 `Entity.hurtOrSimulate`，`attack`/`doSweepAttack` 两处）、`ThrownTridentMixin.java:19`（`@ModifyConstant(floatValue = 8.0F)`）、`EntityMixin.java:18`（`@ModifyVariable(argsOnly = true)` 改 `checkFallDamage` 参数）、`NearestAttackableTargetGoalMixin.java:31`（`findTarget()V` HEAD）、`mixin/client/AbstractContainerScreenMixin.java:21`（`mouseDragged` RETURN + cancellable）。

## 7. 值得学的 5 条具体做法

1. **build.gradle 自动生成 mixins.json**：`generateModMetadata` 任务遍历 `src/main/java/<group>/<modid>/mixin` 目录，把以 `client` 开头的类放进 `client` 数组、其余放进 `mixins`，再 `expand` 到模板重命名为 `${modid}.mixins.json`（`build.gradle` 中 `filesMatching('mixins.json')` 段）。新增 mixin 不需要手改 json。注意本副本未见该模板文件本体（`src/templates` 只有 `neoforge.mods.toml`，未确认原因）。
2. **公式级配置化**：每个战斗公式先尝试 `ALConfig.getXExpr().get().setVariable("x", new BigDecimal(v)).eval().floatValue()`，再回退硬编码默认；`api/ALCombatRules.java:56-58,110-118`。适合"让整合包作者改数值公式"。
3. **把装备槽做成可扩展注册对象**：接口 `EntityEquipmentSlot` + `Registry` + `record EntitySlotGroup(Identifier, HolderSet<...>)` 自带 Codec/StreamCodec，第三方（如 Curios）只需注册新槽与槽组即可接入属性系统；`modifiers/EntityEquipmentSlot.java`、`EntitySlotGroup.java`。
4. **暴露"物品属性修改事件"而不是要求改数据组件**：`StackAttributeModifiersEvent` 让任何 mod 在任意 `ItemStack` 上增删改属性（含槽组），并对"Identifier 必须唯一稳定否则卸下不移除"写了明确警告；`modifiers/StackAttributeModifiersEvent.java`。
5. **冷却做成 API + 同步 Attachment 分层**：对外 `AbilityCooldowns`（自动吃 CDR）、内部 `CooldownTracker`（`Object2LongMap`、`MAX_COOLDOWN_TICKS` 上限、登录 prune）；`api/AbilityCooldowns.java`、`api/CooldownTracker.java`。任何"技能/道具冷却"都可直接抄。
6. （补充）**缓存上下文相关数值**：`AttackEntityEvent` 里抓 `getAttackStrengthScale(0.5F)` 存静态字段，供后续无法获取该值的伤害事件使用，并对非玩家返回 1；`ApothicAttributes.java:88-96,163-166`。

## 8. （库/前置/API 类 mod 专项）

**公开 API 包路径：`dev.shadowsoffire.apothic_attributes.api`**（`ALObjects`、`ALCombatRules`、`AttributeHelper`、`AbilityCooldowns`、`CooldownTracker`）+ **`dev.shadowsoffire.apothic_attributes.modifiers`**（`StackAttributeModifiersEvent`、`StackAttributeModifiers`、`EntityEquipmentSlot`、`EntitySlotGroup`、`EquipmentSlotCompat`、`VanillaEquipmentSlot`）。

- 扩展点接口：`EntityEquipmentSlot`（自定义装备槽，须注册进 `ALObjects.BuiltInRegs.ENTITY_EQUIPMENT_SLOT`）、`ModifierSourceType<T>`（给属性 GUI 增加"属性来源"提取器，`client` 包但被 `CuriosCompat` 跨包使用）、`LEInvoker`（暴露 `internalSetAbsorptionAmount` 的 mixin 接口）。
- 外部 mod 接入方式：① 编译期依赖 `dev.shadowsoffire:ApothicAttributes:<mcVersion>-<version>`，运行期还需 **Placebo**；② 物品属性通过监听 `StackAttributeModifiersEvent`（NeoForge 事件总线）或在 `ItemAttributeModifierEvent` 上加；③ 冷却/战斗数值直接调 `AbilityCooldowns.*`、`ALCombatRules.*`、`AttributeHelper.modify/addToBase/addXTimesNewBase/multiplyFinal`（javadoc 完整解释了 ADD_VALUE → ADD_MULTIPLIED_BASE → ADD_MULTIPLIED_TOTAL 的执行顺序与示例）；④ 槽组通过 `EntitySlotGroup` 注册表 + Codec 在数据/代码里引用。所有注册对象由 `ALObjects` 暴露为 `Holder<T>`，无接口版本号/`@ApiStatus` 分级（仅个别构造器标 `@ApiStatus.Internal`）。
- 外部集成示例：`compat/CuriosCompat.java`（把 `CuriosSlotTypes`/`CurioAttributeModifierEvent`/`ICurioStacksHandler` 映射到本模组的槽组与 `ModifierSource`），可作为"接入 Curios 属性"的模板。
