# Iron431/Iron's Spells 'n Spellbooks 源码分析

## 1. 基本信息

- Mod 名：Iron's Spells 'n Spellbooks（法术书） / mod_id：`irons_spellbooks` / 作者：Iron431, Lab3 / 版本 `1.21.1-3.16.3`
- 目标：**MC 1.21.1 + NeoForge 21.1.200（Java 21，Parchment 2024.11.17）** —— 与本项目 NeoForge 1.21.1 目标完全一致
- Gradle 插件：`net.neoforged.gradle.userdev 7.0.182`（注意是旧版 **userdev**，非 moddev）+ `java-library` + `maven-publish` + `mod-publish-plugin`；`jarJar.enable()` 开启嵌套 jar
- 许可证：**All Rights Reserved**（`gradle.properties: mod_license`，有 `LICENSE.md`、`CLA.md`）—— 可读不可抄
- 编译依赖：**GeckoLib 4.7.5.1**（模型/动画）、**kosmx player-animator 2.0.1**（第一人称施法动画）、**Curios 9.5.1**（饰品槽）、`io.redspace:irons_lib 1.21.1-2.1.0-SNAPSHOT`（自有库；代码中未见直接 import，用途**未确认**）、JEI compileOnly、Gson
- 仓库自带 `apiJar` 任务：`include 'io/redspace/ironsspellbooks/api/**/*'`，以 classifier `api` 发布到 `code.redspace.io` maven

## 2. 源码规模与包结构

- `find . -name '*.java' | wc -l` = **1006**；总行数 = **96963**（超大仓库，本次按"注册体系/网络/核心子系统/mixin/数据驱动"聚焦）
- 顶层 `io.redspace.ironsspellbooks` 下 30 个子包，文件数前列：`particle`(46)、`effect`(36)、`mixin`(34)、`item`(28)、`render`(25)、`item/armor`(25)、`entity/mobs/goals`(25)、`registries`(24)、`entity/spells`(21)、`capabilities/magic`(20)、`command`(19)、`spells/evocation`(17)、`network/casting`(17)、`api/spells`(17)、`api/events`(13)
- 法术按学派分包：`spells/{blood,eldritch,ender,evocation,fire,holy,ice,lightning,nature}`，共约 120 个法术类
- 最大文件：`entity/mobs/wizards/fire_boss/FireBossEntity.java`(1186)、`api/util/Utils.java`(1015)、`entity/mobs/ice_spider/IceSpiderEntity.java`(830)、`player/ServerPlayerEvents.java`(780)、`entity/mobs/dead_king_boss/DeadKingBoss.java`(720)、`registries/EntityRegistry.java`(689)、`api/spells/AbstractSpell.java`(640)

## 3. 入口与注册

入口 `IronsSpellbooks.java:43` `@Mod(IronsSpellbooks.MODID)`，构造器里**一个长列表显式调用 25 个 `XxxRegistry.register(eventBus)`**（`IronsSpellbooks.java:69-91`），注册类集中在 `registries/` 包。三种注册路径并存：

```java
// 1) 普通 DeferredRegister（注册类内自持）
private static final DeferredRegister<Attribute> ATTRIBUTES =
    DeferredRegister.create(Registries.ATTRIBUTE, IronsSpellbooks.MODID);   // AttributeRegistry.java:19
// 2) 自建 Registry（NeoForge NewRegistryEvent）
public static final Registry<AbstractSpell> REGISTRY =
    new RegistryBuilder<>(SPELL_REGISTRY_KEY).create();                     // api/registry/SpellRegistry.java:35
// 3) datapack 注册表（DataPackRegistryEvent）
event.dataPackRegistry(UPGRADE_ORB_REGISTRY_KEY, UpgradeOrbType.CODEC, UpgradeOrbType.CODEC);
```

`SpellRegistry`/`SchoolRegistry` 用 `modEventBus.addListener(SpellRegistry::registerRegistry)` 挂 `NewRegistryEvent`；`UpgradeOrbTypeRegistry` 挂 `DataPackRegistryEvent`。`SpellRegistry` 用一个私有 `NoneSpell` 作**空对象 fallback**（`getSpell()` 找不到时返回它，避免 NPE）。

## 4. 核心系统

**(1) 法术基类与施法管线 —— `api/spells/AbstractSpell.java`**
法术 = 一个 `AbstractSpell` 单例 + 4 个数值字段（`baseManaCost / manaCostPerLevel / baseSpellPower / spellPowerPerLevel / castTime`）+ `DefaultConfig` 预设 + 一组钩子：`attemptInitiateCast` → `canBeCastedBy`（返回 `CastResult` 含失败文案）→ `SpellPreCastEvent` → `MagicData.initiateCast()` → 发 `UpdateCastingStatePacket`/`OnCastStartedPacket`；完成时 `castSpell()` → `SpellOnCastEvent` → 扣蓝 + `SyncManaPacket` → `onCast()` → 冷却。`onClientPreCast / onClientCast / onServerPreCast / onServerCastTick / onRecastFinished / shouldAIStopCasting` 构成完整的双端生命周期。**法术数值全部即时经 `SpellConfigManager.getSpellConfigValue(...)` 读取**，所以数据包/配置文件能在不改代码的情况下重平衡。

**(2) 法术配置系统（最有学习价值）—— `api/config/SpellConfigManager.java`**
`extends SimpleJsonResourceReloadListener`，**同一套 JSON schema 支持三种来源**：数据包 `data/<ns>/irons_spellbooks_spell_config/<spell>.json`、本地 `config/irons_spellbooks_spell_config/<ns>/<spell>.json`、以及 `global_config.json` 全局兜底（只在 spell 用默认值时生效）。用 `SpellConfigParameter<T>`（key + Codec + 默认值）声明参数，`RegisterConfigParametersEvent` 允许**外部 mod 追加参数**，`ModifyDefaultConfigValuesEvent` 允许二遍修改默认值。加载完在 `OnDatapackSyncEvent` 里通过 `SyncJsonConfigPacket` 把配置同步给客户端（登录单独发、`/reload` 全体发）。

**(3) 魔法数据与属性 —— `api/magic/MagicData.java` + `api/registry/AttributeRegistry.java`**
玩家/生物魔法状态用 **NeoForge Attachment** 而非 Capability：`DataAttachmentRegistry.MAGIC_DATA`，`AttachmentType.builder(...).serialize(new PlayerMagicProvider())`。`MagicData` 聚合 mana / cooldowns（`PlayerCooldowns`）/ recasts（`PlayerRecasts`）/ `SyncedSpellData` / 施法状态。属性用两个自定义类 `MagicRangedAttribute`、`MagicPercentAttribute`，注册了 8 个全局属性（`max_mana` 100、`mana_regen`、`cooldown_reduction`、`spell_power`、`spell_resist`、`cast_time_reduction`、`summon_damage`、`casting_movespeed`）+ 9 学派 × (spell_power / magic_resist)，并在 `EntityAttributeModificationEvent` 里 `e.getTypes().forEach(entity -> ...e.add(entity, attribute))` 一次性给所有生物挂上。

**(4) 学派 —— `api/spells/SchoolType.java` + `api/registry/SchoolRegistry.java`**
`SchoolType` = id + focus 物品 Tag + 显示名 + power 属性 + resist 属性 + 施法音效 + 伤害类型，`getPowerFor(LivingEntity)` 供 `AbstractSpell.getSpellPower` 相乘。学派本身是自建 Registry 对象（可被数据包/附属追加）。

**(5) 施法与冷却管理 —— `capabilities/magic/MagicManager.java`**
全局单例（`IronsSpellbooks.MAGIC_MANAGER`），持有 `tick(Level)`（每 10 tick 回蓝 `MANA_REGEN_TICKS`）、`addCooldown`（`getEffectiveSpellCooldown` 按 `cooldown_reduction` 属性折算）、`spawnParticles` 等集中式服务。

**(6) 法术物品与容器 —— `api/spells/SpellData.java` + `ISpellContainer` / `IPresetSpellContainer` / `SpellContainer`**
法术存在物品上的载体：`SpellData`（spell + level + locked，带 `CODEC`/手写 buffer 读写），容器接口 `ISpellContainer(Mutable)` 把"法术书/卷轴/剑"统一抽象，`CastSource` 枚举区分 SPELLBOOK/SWORD/SCROLL。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`setup/PayloadHandler.java` 单类集中注册，`event.registrar(MODID).versioned("1.0.0").optional()` 后逐条 `payloadRegistrar.playToClient(TYPE, STREAM_CODEC, X::handle)` / `playToServer(...)`，约 40 个 payload 按注释分区（GENERAL / PARTICLES / CASTING / SPELLS）。**`versioned("1.0.0")` + `optional()`** 是它做协议兼容的策略。
- **数据驱动**：不是主流路线，但数据文件确实入库——`src/main/resources/data/` 有 **814 个 JSON**（`advancement/`、`curios/{entities,slots}`、`dimension`/`dimension_type`、`worldgen/`、`tags`、以及**跨 mod 命名空间的 compat 数据**如 `data/irons_jewelry/tags/irons_jewelry/{material,pattern}/*.json`、`data/curios/tags/item/{ring,necklace,spellbook}.json` —— 用"往别的 mod 的命名空间塞数据"实现零代码兼容）；`src/generated/resources` 有 **246 个** datagen 产物（`advancement/recipe`、`damage_type`、`irons_spellbooks/upgrade_orb_type`（即 DataPackRegistry 的输出）、`loot_table/blocks`、`neoforge/biome_modifier`、`recipe`、`tags/damage_type`、`worldgen/{configured,placed}_feature`）。datagen 仅 5 个类（`datagen/DataGenerators.java`：`RegistryDataGenerator`(DatapackBuiltinEntries)、`DamageTypeTagGenerator`、`IronLootTableProviders`、`IronRecipeProvider`、`PackMetadataGenerator`）。
  > **重要（读取方法）**：本地 bulk 副本用 sparse-checkout（`.git/info/sparse-checkout` 只检出 `**/*.java`/`*.gradle`/`*.properties`/`*.toml`/`*.md`），上述 data/asset JSON **不在工作树中**（`git ls-files` 可见）。本报告的数据内容结论来自 Java 侧代码，未核对 JSON 文本。
- **配置**：NeoForge `ModConfig` 双文件（`ClientConfigs.SPEC` / `ServerConfigs.SPEC`）+ 上面的 SpellConfigManager 自定义 JSON 体系；`/ironsSpellbooks config` 命令可在游戏内生成/导出配置文件。
- **资源包**：`AddPackFindersEvent` 里用 `Pack.readMetaAndCreate` 注册内置资源包 `legacy_dead_king_resource_pack`（`IronsSpellbooks.java:119-130`）。
- **IMC**：只留了空的 `enqueueIMC`/`processIMC` 骨架。

## 6. Mixin

配置 `src/main/resources/irons_spellbooks.mixins.json`：`package=io.redspace.ironsspellbooks.mixin`，`compatibilityLevel=JAVA_21`，`injectors.defaultRequire=1`，22 个 common + 11 个 client，且指定了 **`"plugin": "io.redspace.ironsspellbooks.mixin.MixinPlugin"`**。代表性：

- `EntityMixin` / `LivingEntityMixin` / `PlayerMixin` / `ItemStackMixin` / `MobEffectMixin` / `LevelMixin`（通用行为注入）
- `EntityAccessor` / `LivingEntityAccessor` / `AbstractArrowAccessor` / `VaultServerDataAccessor`（`@Accessor`/`@Invoker` 取私有成员）
- `Iron431__irons-spells-n-spellbooks` 特有：`Compat$apothic_attributes$AttributeHandler`（按 modid 命名的条件兼容 mixin）、`CurioHooksMixin`、`SmithingRecipeMixin`、`DispenserBlockMixin`、`TridentItemMixin`
- **`mixin/MixinPlugin.java:shouldApplyMixin`**：类名按 `Compat$<modid>$<Name>` 约定，用 `FMLLoader.getLoadingModList().getModFileById(modid) != null` 判断目标 mod 是否加载，未加载则直接不应用该 mixin —— 无需为每个兼容项写一个 mixin 配置。

## 7. 值得学的 5 条具体做法

1. **"同名多来源"的配置系统**：一个 `SimpleJsonResourceReloadListener` 同时吃数据包 JSON 与本地 config 目录 JSON，再加一份 global 兜底，且低优先级不覆盖高优先级（`buildConfigManager` 里 `config.isDefault(paramType)` 判断）。`api/config/SpellConfigManager.java:278-332`。适用：需要让整合包/玩家/数据包三方都能改数值的系统。
2. **参数化配置 + 外部注册**：`SpellConfigParameter<T>`(key+Codec+默认值) + `RegisterConfigParametersEvent`，附属 mod 可为自己新增可配置参数。`SpellConfigManager.java:242-255`。适用：想让 KubeJS/附属 mod 扩展的数值系统。
3. **配置同步进网络层**：`OnDatapackSyncEvent` 里区分"单玩家登录"和"全体 /reload"两种分发，并只在 `dirty` 时重建。`SpellConfigManager.java:123-156`。适用：服务端权威的 JSON 配置需要客户端一致展示的场景。
4. **按 modid 命名的条件 mixin + IMixinConfigPlugin**：`Compat$<modid>$<Class>` 命名 + `shouldApplyMixin` 自动按 `ModList` 过滤。`mixin/MixinPlugin.java:22-31`。适用：兼容 mixin 数量大、不想污染 mixins.json。
5. **空对象模式防 NPE**：`SpellRegistry.none()` 返回 `NoneSpell` 而非 null，所有 `getSpell` 失败路径安全。`api/registry/SpellRegistry.java:49-55,74-80`。适用：被大量下游代码调用的查找器。
6. **数值与逻辑分离**：法术类里只有公式和钩子，`baseManaCost` 等字段私有受保护，一切对外数值走 `SpellConfigManager`/属性，使得"改平衡"不需要重新编译。`api/spells/AbstractSpell.java:160-166,211-225`。
7. **单类集中注册 ~40 个 payload**，用注释分块 + `versioned/optional` 声明协议——比"每个包一个注册类"更好审阅。`setup/PayloadHandler.java:21-24`。

## 8. 公开 API / 外部接入

- API 包：`io.redspace.ironsspellbooks.api.*`（构建期单独产出 `api` jar）
- 扩展点：`SpellRegistry`/`SchoolRegistry`（新增法术/学派）、`AbstractSpell`（继承实现新法术）、`SpellDataRegistryHolder`、`IMagicEntity`/`NoopMagicEntity`、`IScroll`/`ISpellbook`/`IPresetSpellContainer`、`IMagicManager`
- 事件总线（`api/events/`，13 个）：`SpellPreCastEvent`、`SpellOnCastEvent`、`SpellDamageEvent`、`SpellHealEvent`、`SpellTeleportEvent`、`CounterSpellEvent`、`ModifySpellLevelEvent`、`ChangeManaEvent`、`SpellSummonEvent`、`SetSummonOwnerEvent`、`InscribeSpellEvent`、`SpellCooldownAddedEvent`、`CustomizeScrollModNameEvent`
- 配置扩展：`RegisterConfigParametersEvent`、`ModifyDefaultConfigValuesEvent`、`IronConfigParameters`
- 兼容层：`compat/`（`ApotheosisHandler`、`Curios`、`tetra/ITetraProxy`、`CompatHandler`）

> 未确认：`io.redspace:irons_lib` 的具体用途与内容（本地无源码，本 mod 代码中无直接 import；而 irons-jewelry 的 datagen 用了 `io.redspace.ironslib.registry.IronsLibRegistries`，推测是其共享注册表库）；`LICENSE.md` 正文条款细节；仓库为 sparse-checkout 检出，assets/data JSON 文本未核对。
