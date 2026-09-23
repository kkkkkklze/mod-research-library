# Shadows-of-Fire/Apotheosis 源码分析

## 1. 基本信息

- Mod 名：Apotheosis（神化） / mod_id：`apotheosis` / 作者：Shadows_of_Fire / 版本 9.0.3
- 目标：**MC 26.1.2 + NeoForge 26.1.2.76，Java 25**（`gradle.properties`）。本地检出分支为 `26.1`（`git branch` 只有 `origin/26.1`），**注意不是 1.21.1**——阅读旧版逻辑时需注意映射/API 差异（如 `Identifier` 取代 `ResourceLocation`）
- Gradle 插件：`net.neoforged.moddev 2.0.141` + `java-library` + `maven-publish` + `me.publish-plugin`；`modLoaders=NeoForge`
- 许可证：仓库根**无 LICENSE 文件**（bulk 副本已剔除）；`build.gradle` 的 `generateModMetadata` 会强制读取 `LICENSE` 首行注入 mods.toml 的 `license` 字段
- 编译依赖：`dev.shadowsoffire:Placebo`（核心前置/注册与动态注册 API）、`ApothicAttributes`（required，提供 `ALObjects`/`EntitySlotGroup`/`StackAttributeModifiersEvent`）；可选 ApothicSpawners / ApothicEnchanting / Gateways / Patchouli / Curios / JEI / Jade。历史模块（Enchanting/Spawner）已拆为独立 mod，本仓库只剩 Adventure 模块。

## 2. 源码规模与包结构

- `find . -name '*.java' | wc -l` = **333**；总行数 = **39822**
- 顶层包 `dev.shadowsoffire.apotheosis` 下 37 个子包，文件数前列：`util`(23)、`data`(23)、`client`(20)、`mixin`(18)、`affix/effect`(18)、`compat/jei`(14)、`affix`(11)、`socket/gem/storage`(10)、`socket/gem`(10)、`loot`(10)、`tiers`(7)、`socket/gem/bonus`(7)、`mobs/util`(7)
- 最大文件：`data/AffixProvider.java`(1000)、`data/GemProvider.java`(973)、`Apoth.java`(742)、`client/AdventureModuleClient.java`(664)、`data/ApothRecipeProvider.java`(606)、`data/ApothGateProvider.java`(568)
- 另有一本**数据格式文档目录** `schema/`（72 个 .md，如 `schema/gem/Gem.md` 用 "Dependencies + ```js Schema 块" 描述每个数据对象的字段）

## 3. 入口与注册

入口 `Apotheosis.java:98` `@Mod(Apotheosis.MODID)`，构造器仅做转调；**真正的注册集中在 `Apoth.java`（自述 "Object Holder Class"）**，用 Placebo 的 `DeferredHelper`：

```java
public static final DeferredHelper R = DeferredHelper.create(Apotheosis.MODID);
public static final DataComponentType<ItemAffixes> AFFIXES =
    R.component("affixes", b -> b.persistent(ItemAffixes.CODEC)
                                 .networkSynchronized(ItemAffixes.STREAM_CODEC));
public static void bootstrap(IEventBus bus) { bus.register(R); /* 然后逐个 XX.bootstrap() */ }
```

组织方式：把注册项按类型拆成**静态内部类** `BuiltInRegs/Components/Attachments/Blocks/Items/Tiles/Menus/Features/Tabs/Sounds/Songs/RecipeTypes/RecipeSerializers/Ingredients/SlotDisplays/LootPoolEntries/LootModifiers/LootConditions/LootFunctions/Triggers/EntitySubPredicates/DataComponentPredicates/LootTables/Tags/DamageTypes/Advancements/Particles/Stats/LootCategories/DataMaps`，每个类一个空 `private static void bootstrap() {}` 用于强制类加载，`Apoth.bootstrap` 里统一触发。11 个动态注册表在 `Apotheosis.setup`（`FMLCommonSetupEvent`）中 `registerToBus()`。

## 4. 核心系统

**(1) 词缀 API —— `affix/Affix.java`**
抽象类 `Affix implements CodecProvider<Affix>, Weighted`，**用约 20 个空实现勾子把"附魔逻辑"完全外置**：`canApplyTo / addModifiers(StackAttributeModifiersEvent) / getDamageProtection / getDamageBonus / doPostAttack / doPostHurt / onProjectileFired / onItemUse / onShieldBlock / onBlockBreak / getDurabilityBonusPercentage / onHurt / enablesTelepathy / getEnchantmentLevels / modifyLoot / modifyEntityLoot`。附带值 `Affix.MAX_LEVEL=2.0F`、`STANDARD_MAX_LEVEL=1.0F`（设计点：level 是"相对强度"的 float 而非整数等级）。`Affix.id()` 由注册表反查，`makeUniqueId(inst, salt)`（`Affix.java:314`）用"词缀 id + LootCategory 的槽位组 + salt"生成确定性 Identifier，解决"同词缀多槽位 AttributeModifier ID 冲突"。

**(2) 数据驱动动态注册表 —— `affix/AffixRegistry.java` + `tiers/TieredDynamicRegistry.java`**
`AffixRegistry extends TieredDynamicRegistry<Affix> extends placebo DynamicRegistry<V>`。子类型由**公开的 `SubtypedSerializer`** 声明，注释明说是给外部 mod 用的扩展点：
`public static final SubtypedSerializer<Affix> SERIALIZER = RegistrySerializer.<Affix>subtypedSynced("affixes").register(Apotheosis.loc("attribute"), AttributeAffix.CODEC)...`（20 个叶子类型）。`onReload` 里重建 `Multimap<AffixType, DynamicHolder<Affix>>`，并做两项校验：开发环境检查 lang key、服务器端 `validateAffixExclusiveSets()` 检查互斥集引用的词缀是否已绑定。

**(3) 分层权重 —— `tiers/TieredWeights.java`**
`record TieredWeights(Map<WorldTier, Weight> weights)`，`Weight(int weight, float quality)`；取权重公式 `getWeight(luck) = weight + round(luck * quality)`——**quality 让"幸运值"直接改写掉落权重**。Codec 用 `Codec.mapEither(单权重, WorldTier->Weight 映射).xmap(fillAll, toEither)`，允许 JSON 里写一个数字或写五档地图，`toEither` 在五档全等时再折叠回单值。

**(4) 宝石/插槽 —— `socket/gem/Gem.java` + `socket/gem/bonus/GemBonus.java`**
`Gem` 构造时把 `List<GemBonus>` 按 `GemClass.types()` 摊平成 `IdentityHashMap<LootCategory, GemBonus> bonusMap`，并用 `validateBonus` **在加载期抛 IllegalArgumentException 检测同类冲突**（而不是运行时静默）。外部 mod 可通过 `ExtraGemBonusRegistry` + 包私有 `appendExtraBonus` 给已有宝石追加 bonus。`SocketHelper` 走 `ItemContainerContents` 组件槽位。

**(5) 掉落生成 —— `loot/LootController.java` + `loot/LootRule.java` + `looot/LootRarity`**
`createLootItem(stack, cat, rarity, ctx)` 是"给物品随机挂词缀"的唯一入口；`LootRarity` 是含 `color/material/weights/rules/sortIndex/renderData/invaderSound` 的数据对象，`getRules(category)` 会先查 `RarityOverrideRegistry` 的按类别覆盖，再回退默认 rules。

**(6) Boss/入侵者 —— `mobs/` + `ApothMobEvents.java`**
`Invader/Elite/Augmentation` 三套注册表 + `InvaderSpawnRules` 按维度存放在自定义 DataMap（`Apoth.DataMaps.INVADER_SPAWN_RULES`）；等级增强是否已应用由 `AttachmentType<Boolean> TIER_AUGMENTS_APPLIED` 记录（`Apoth.java:232`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：不自建通道，统一走 Placebo 的 `PayloadHelper.registerPayload(new XxxPayload.Provider())`（`Apotheosis.java:165-171`），共 7 个：BossSpawn / RerollResult / RadialState / WorldTier / ConfigPayload / LinkItemToChat / GemCaseSelect。每个 payload 是 `record ... implements CustomPacketPayload` + 内部 `Provider implements PayloadProvider<T>`，提供 `getType/getCodec/handleClient/handleServer/getSupportedProtocols/getFlow/getVersion`（见 `net/WorldTierPayload.java:33-71`）——**协议版本号 + 支持协议列表**是它防客户端/服务端不匹配的做法。
- **序列化/同步**：组件用 `persistent(Codec).networkSynchronized(StreamCodec)` 成对声明（`Apoth.Components`）；动态注册表对象用 `DynamicHolder` 的 `holderCodec()/holderStreamCodec()` **只同步注册名**，而不是把整个对象发过去。
- **数据驱动**：核心——绝大部分数据对象由 `data/` 下 23 个 Provider（AffixProvider/GemProvider/GLMProvider/InvaderProvider/TierAugmentProvider/…）在 `runData` 产出，`Apotheosis.data(GatherDataEvent.Client)` 用 Placebo 的 `DataGenBuilder` 链式注册；**datagen 产物已提交入库**（`src/generated/resources` 计 558 个文件，含 `.cache` 校验目录）。手写数据集中在 `src/main/resources/data/apotheosis/`（55 个 JSON：`tags/`、`worldgen/{configured_feature,placed_feature,structure,structure_set,template_pool,processor_list}`、`recipe/`、`damage_type/`、`neoforge/biome_modifier/`），另有 1046 个 assets 文件（Patchouli 手册、模型、lang、贴图）。
  > **重要（读取方法）**：本地 bulk 副本用 sparse-checkout（`.git/info/sparse-checkout` 只检出 `**/*.java`/`*.gradle`/`*.properties`/`*.toml`/`*.md` 等），因此 `src/main/resources` 与 `src/generated/resources` 在**工作树中几乎为空**——它们仍在 git 索引里（用 `git ls-files` 可查）。本报告的"数据 JSON 内容"结论来自 `data/` 包的 Provider 代码与 `schema/*.md`，未逐一核对 JSON 文本。
- **配置**：Placebo `Configuration`，两份文件（主配置 + `name_generation` 命名生成），并在 `AddServerReloadListenersEvent` 里挂 `RunnableReloader`——**改配置后 `/reload` 即可生效**（`Apotheosis.java:264-275,187`）。

## 6. Mixin

配置 `src/generated/resources/apotheosis.mixins.json`（由 `build.gradle` 的 `generateModMetadata` 任务**扫描 mixin 包目录自动生成** entry 列表），`package=dev.shadowsoffire.apotheosis.mixin`，`compatibilityLevel=JAVA_25`，`maxShiftBy=5`，含 18 个 common + 7 个 `client.*`。代表性：

- `ItemStackMixin.java:31` `@Mixin(value=ItemStack.class, priority=500)` → `getHoverName`(RETURN,cancellable)、`useOn`(RETURN)、`copy`(RETURN ordinal=1)、`inventoryTick`(HEAD)
- `EnchantmentHelperMixin.java` → `getDamageProtection`、`modifyDamage`、`doPostAttackEffectsWithItemSource`(TAIL)、`processDurabilityChange`
- `LivingEntityMixin.java:23,41` → `detectEquipmentUpdates` HEAD/TAIL（装备变化时重算词缀）
- `MobMixin.java:23` → `dropFromLootTable`(TAIL)；`DamageSourceMixin.java:25` → `is(TagKey)`(RETURN)
- 条件兼容 mixin：`GoldToolsHaveFortuneModuleMixin` 直接 `@Mixin(targets="org.violetmoon.quark...", remap=false)` 处理 Quark 冲突

## 7. 值得学的 5 条具体做法

1. **"对象持有类"模式**：把所有注册项从 @Mod 类剥离到一个巨型 `Apoth.java`，用静态内部类分组 + `bootstrap()` 空方法强制类加载；好处是 `Apoth.Items.GEM` 这类引用永远安全。文件：`Apoth.java:710-740`。适用：注册项 >100 的中大型 mod。
2. **build.gradle 自动生成 mixins.json**：遍历 mixin 包目录、以 `client` 前缀区分 common/client 列表并注入模板。`build.gradle`（`tasks.named("generateModMetadata")`）。适用：mixin 数量多、避免手写列表漏项。
3. **权重绑定"世界层级 + 幸运值"**：`Weight(weight, quality)` 让 `luck` 线性修正权重，一套数据即可让同一份掉落表在 5 个 tier 里有不同分布。`tiers/TieredWeights.java:46-72`。适用：任何按进度分层的战利品/刷怪系统。
4. **公开 `SubtypedSerializer` 作为扩展点**：注释明确写 "so external mods can register additional Affix subtypes during their setup phase"。`affix/AffixRegistry.java:37`。适用：想被 KubeJS/附属 mod 扩展的数据驱动系统。
5. **加载期校验代替运行时容错**：Gem 的 bonus 类别冲突在构造器 `Preconditions`/`IllegalArgumentException`；Affix 互斥集在 server reload 时校验并 `logger.error`。`socket/gem/Gem.java:236-243`、`affix/AffixRegistry.java:93-101`。适用：数据包系统，错误应在 reload 时暴露。
6. **手写 `schema/*.md` 数据格式文档**：72 个 md 与 codec 一一对应，含 Dependencies 与字段默认值。适用：数据包为主要内容的 mod。

## 8. 公开 API / 外部接入

非库 mod，但有明确对外面：`AffixRegistry.SERIALIZER`（注册新 Affix 子类型）、`GemBonus.CODEC`/`GemBonus.initCodecs()`（注册新 bonus 类型）、`ExtraGemBonusRegistry.INSTANCE`（给已有宝石加 bonus）、`affix/ItemAffixes`（组件读写 + Builder：put/upgrade/remove/removeIf）、`socket/SocketHelper`、`loot/LootController.createLootItem(...)`、`Apoth.*` 全部公开常量（Components/Tags/DataMaps/Attachments）。兼容层集中在 `compat/`（gateways / spawners / enchanting / curios / patchouli / jei / twilight），均以 `ModList.get().isLoaded(...)` 守卫。

> 未确认：`LICENSE`/`LICENSE_ASSETS` 内容（工作树中无该文件，但 `build.gradle` 会读取并断言其存在）；Placebo 内部 `DynamicRegistry`/`DynamicHolder`/`PayloadProvider` 实现细节（属外部依赖，本地无源码）；仓库为 sparse-checkout 检出，assets/data JSON 文本未核对。
