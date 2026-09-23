# Ars Nouveau 源码分析报告

> 仓库根：`源码库/_参考仓库/_bulk/baileyholl__Ars-Nouveau`。下文所有 `文件:行号` 均相对仓库根（Java 路径省略 `src/main/java/com/hollingsworth/arsnouveau/` 前缀时用 `…/` 标记，首次出现给全路径）。本报告基于 5.13.1 分支快照，1.20.x 时代的"被动符文"等机制在本版已不存在，凡未直接读到的行为一律标注"未验证"。

## 1. 基本信息

- mod_id `ars_nouveau`，作者 Bailey Hollingsworth，版本 5.13.1（`gradle.properties:13-18`）
- 目标平台：MC 1.21.1 / NeoForge 21.1.228，版本区间 `[1.20.6,1.21.2)`（`gradle.properties:7-11`）；无 Forge/Fabric 侧
- 许可证：代码 LGPL v3（`README.md:12`），贴图/模型 All Rights Reserved（`README.md:9-10`）；`license.txt` 为 LGPL 正文
- 构建：单模块工程，插件 `net.neoforged.moddev 2.0.91` + `com.gradleup.shadow 9.0.0-beta15`（`build.gradle:6-7`），Java 21（`build.gradle:22`）
- 编译依赖：GeckoLib、Patchouli、Curios、Caelus(compileOnly-api)、JEI/EMI、TerraBlender、Jade、自带库 `com.hollingsworth.nuggets`(jarJar 内嵌)、Apache Lucene（shadow 着色内嵌，供文档检索，`build.gradle:232-234`）
- maven 发布：group `com.hollingsworth.ars_nouveau`，artifactId `ars_nouveau-1.21.1`，version 5.13.1(.BUILD_NUMBER)；build.gradle 的 publishing 写本地 maven（`build.gradle:271-285`），正式版发布到 BlameJared maven 供 addon 依赖（`README.md:14-19`）

## 2. 源码规模与包结构

实测：1500 个 `.java`，`cat|wc -l` 合计 140,605 行（卡片写 142,105，本次复核为 140.6k，差异可能来自统计口径）。按顶层包：`common` 880 文件、`api` 297、`client` 280、`setup` 40、`gametest` 2。主要子包（文件数）：

| 包 | 数 | 包 | 数 |
|---|---|---|---|
| common/block(+tile) | 151 | client/particle | 38 |
| common/spell/effect | 67 | setup/registry | 31 |
| common/network | 65 | api/spell | 30 |
| common/items | 52 | common/crafting/recipes | 26 |
| common/entity | 46 | common/ritual | 24 |
| common/datagen | 39(+patchouli 16) | api/registry | 22 |

最大源文件（复核后行数）：`common/datagen/LangDatagen.java` 1843、`common/entity/pathfinding/pathjobs/AbstractPathJob.java` 1352、`common/datagen/ApparatusRecipeProvider.java` 1180、`setup/registry/Documentation.java` 1027、`common/entity/WildenChimera.java` 974、`common/datagen/RecipeDatagen.java` 937、`client/gui/book/GuiSpellBook.java` 865、`common/datagen/PatchouliProvider.java` 844。datagen 与怪物寻路占据榜首——业务核心（`api/spell` 30 文件 + `common/spell` 约 100 文件）反而紧凑，取舍时我只细读 spell 子系统、投射实体、注册/配置与网络层，实体 AI/寻路/装饰内容按包略读。

稀疏检出注意：`src/main/resources` 只剩 `META-INF/accesstransformer.cfg`(103 行)、`META-INF/neoforge.mods.toml` 与 `ars_nouveau.mixins.json`；`assets/`、`data/`、`src/generated/` 均缺失，故报告中的 JSON 类型清单反推自 datagen provider 与 RecipeSerializer，而非成品文件。

## 3. 入口与注册

入口 `com/hollingsworth/arsnouveau/ArsNouveau.java:79-125`，`@Mod(ArsNouveau.MODID)` 构造器：

```java
public ArsNouveau(IEventBus modEventBus, ModContainer modContainer) {
    APIRegistry.setup();                                  // 静态注册全部 glyph/ritual/perk/familiar
    modContainer.registerConfig(ModConfig.Type.SERVER, ServerConfig.SERVER_CONFIG); // 另有 STARTUP/COMMON/CLIENT
    modEventBus.addListener(Networking::register);
    ModSetup.registers(modEventBus);                      // DeferredRegister 批量 register
    NeoForge.EVENT_BUS.addListener(BreezeEvent::onSpellResolve); ...
```

- 注册方式双轨：方块/物品/实体/配方等走 NeoForge `DeferredRegister`（`setup/ModSetup.java:35`、`setup/registry/RecipeRegistry.java:18`）；**glyph 不走游戏注册表**——`api/registry/GlyphRegistry.java:35-45` 的 `registerSpell()` 把 `AbstractSpellPart` 塞进静态 `ConcurrentHashMap`，并为每个 glyph 单独 build 一个 `ModConfigSpec`、以 `<namespace>/<path>.toml` 注册为 SERVER 配置。glyph 物品在 `setup/registry/ItemsRegistry.java:263` 遍历 `glyphItemMap` 延迟生成（因注册表冻结，`api/spell/AbstractSpellPart.java:152-160` 缓存 `Glyph` item 实例）。
- 事件总线订阅点：模组自身在 `NeoForge.EVENT_BUS` 挂投射/溶解/breeze 等零散监听；对 addon 暴露的事件全部定义在 `api/event/`（25 个类：`SpellCastEvent`、`SpellResolveEvent.Pre/Post`、`EffectResolveEvent.Pre/Post`、`SpellProjectileHitEvent`、`SpellDamageEvent`、`SpellCostCalcEvent`、`ManaRegenCalcEvent` 等），由 resolver 统一 post。

## 4. 核心系统

### 4.1 法术的数据结构与存放位置（问题①）

一个 spell 就是**符文（`AbstractSpellPart`）的有序不可变列表**外加表现元数据。`api/spell/Spell.java:33-96`：字段 `List<AbstractSpellPart> recipe + name + ParticleColor color + ConfiguredSpellSound sound + TimelineMap particleTimeline`；`CODEC`(35-41) 与 `STREAM`(43-59) 成对。符文本身的序列化只是注册表 id 字符串——`AbstractSpellPart.CODEC = ResourceLocation.CODEC.xmap(GlyphRegistry::getSpellPartOrDefault, …getRegistryName)`（`api/spell/AbstractSpellPart.java:30`），因此一条法术的 JSON 就是 `"recipe": ["ars_nouveau:projectile", "ars_nouveau:ignite", …]`。另有 gzip+base64 的"分享码"编解码（`Spell.java:118-155`）。

存放位置分三层：
- **物品数据组件**：施法器（wand/spell_book/bow…）把 `SpellCaster` 组件写入 `ItemStack`，其核心是 `SpellSlotMap = record Map<Integer, Spell>`（`api/spell/SpellSlotMap.java:13`，组件注册于 `setup/registry/DataComponentRegistry.java:41`，persistent+networkSynchronized 各带 CODEC/STREAM_CODEC）。法术不存在玩家 NBT 里，换物品即换负载。
- **玩家能力（capability）**：已学符文集合在 `common/capability/IPlayerCap.java:16-30`（`getKnownGlyphs/unlockGlyph/knowsGlyph`，实现 `ANPlayerDataCap`），经 `PacketSyncPlayerCap` 同步；mana 上限/回复是相邻的另一个 cap（`setup/registry/CapabilityRegistry.getMana`，`common/items/Glyph.java:57-63` 学习时顺带抬高 glyphBonus）。
- **实体同步数据**：投射物 `EntityProjectileSpell` 把整个 `SpellResolver` 作为 synched entity data 同步（`common/entity/EntityProjectileSpell.java:126-128`）。序列化采用"脱水/复水"设计：`SpellResolver.CODEC` 只存 `SpellContext`，而 `SpellContext.CODEC` 只存 `Spell`（`api/spell/SpellContext.java:58-60`）；caster 引用不落盘，反序列化后服务端 `rehydrate(level)` 现场重建（`api/spell/SpellResolver.java:67-71`）——这解决了"引用实体无法持久化"的经典难题。方块实体（如 implementer/turret）与符阵（rune）同样通过 `TileCaster` 包装复用同一 resolver（见 4.2）。

### 4.2 符文的注册、分类与施法状态机（问题②）

符文没有"效果枚举+参数"，而是**每个 glyph 一个 Java 类单例**，`AbstractSpellPart` 之下四种子类：`AbstractCastMethod`（形态，`common/spell/method/` 5 个：projectile/touch/self/underfoot/pantomime）、`AbstractEffect`（效果，`common/spell/effect/` 67 个文件、约 60 个 glyph）、`AbstractAugment`（增强，`common/spell/augment/` 13 个）、`AbstractFilter extends AbstractEffect`（过滤器，成本 0，目标不符时 `spellContext.setCanceled(true, FILTER_FAILED)`，`api/spell/AbstractFilter.java:14-46`，注释言明源自 addon TooManyGlyphs）。**主动/被动之分在本版本已消失**：全仓库 grep `Passive` 无 glyph 相关类；被动类玩法被拆到施法器之外的系统——护甲 perk（`api/perk`）、reactive 附魔（`common/crafting/recipes/ReactiveEnchantmentRecipe.java` + `PacketReactiveSpell`）、ritual、familiar。
注册点在 `setup/registry/APIRegistry.java:44-128` 的 `registerSpell(X.INSTANCE)` 硬编码清单（约 90 个 glyph + 24 ritual + 6 familiar + 19 perk），构造器阶段调用（`ArsNouveau.java:86`），addon 同样直接调 `GlyphRegistry.registerSpell`。

**施法状态机完全在服务端跑**，链路：
1. 客户端右键/快捷键 → `AbstractCaster.castOnServer` 发 `PacketCastSpell`（只带 slot+视角，`api/spell/AbstractCaster.java:330-332`、`common/network/PacketCastSpell.java:66-86`）；或物品 `use()` 已在服务端时直接进 `castSpell`。
2. `AbstractCaster.castSpell`（`api/spell/AbstractCaster.java:282-324`，非 ServerLevel 直接 pass）：取当前槽 Spell → `getSpellResolver(new SpellContext(...))` → 服务端 rayTrace → 按命中类型分派 `resolver.onCast/onCastOnBlock/onCastOnEntity`。
3. `SpellResolver.canCast`（`api/spell/SpellResolver.java:86-113`）：先过 `ISpellValidator` 链，再查 mana（不足时 `NotEnoughManaPacket` 提示客户端）。post `SpellCastEvent` 可整个取消。
4. 形态执行：`castType.onCast(...)` 返回 `CastResolveType`，SUCCESS 才 `expendMana()`（`SpellResolver.java:127-137`）。projectile 形态在这里生成 `1+split` 个 `EntityProjectileSpell` 并交替偏转射出（`common/spell/method/MethodProjectile.java:49-70`），**法术本身此刻还没执行任何效果**——resolver 被原样交给投射实体携带。
5. 效果循环 `SpellResolver.resume`（`api/spell/SpellResolver.java:203-271`，`world.isClientSide` 直接 return）：`SpellContext.currentIndex` 逐步推进（`nextPart`，`SpellContext.java:124-141`）；遇到 augment 跳过——augment 的作用方式是在每个效果解析前用 `spell.getAugments(currentIndex-1)` 收集"紧随其后的连续 augment 段"现算一份 `SpellStats`（`SpellResolver.java:220-225`），即增强不修改数据、只在求值瞬间参与；每个效果前后 post `EffectResolveEvent.Pre/Post`，并查询命中方块/实体的 `IResolveListener` capability（`BLOCK/ENTITY_SPELL_RESOLVE_CAP`，`SpellResolver.java:236-246`），目标可返回 `STOP_ALL` 掐断后续链。
6. 链式/延迟：`makeChildContext()` 把剩余符文切给新 context（`SpellContext.java:143-161`），配合 `IContextManipulator`（bounce、delay、summoned-creature-casts 等）实现"法术中套法术"；被召唤物持 focus 可继承法术再由 `EntitySpellResolver` 施放（`api/spell/AbstractEffect.java:77-90`），`EntitySpellResolver` 只是免除 mana 检查的子类（`api/spell/EntitySpellResolver.java:20-23`）。

### 4.3 校验管线与解锁进度联动（问题④）

`common/spell/validation/` 14 个文件：`StandardSpellValidator` 用布尔 `enforceCastTimeValidations` 把同一批 validator 编成"合成期"与"施法期"两条链（`common/spell/validation/StandardSpellValidator.java:21-66`），组合器 `CombinedSpellValidator` 收集全部 `SpellValidationError`。与进度直接挂钩的两个：`GlyphKnownValidator.digestSpellPart`（`common/spell/validation/GlyphKnownValidator.java:26-32`）在施法期逐个符文查 `IPlayerCap.knowsGlyph`，不认识即报 `glyph_not_known`；`GlyphMaxTierValidator`（`…/GlyphMaxTierValidator.java:10-32`）限定符文最高 tier——tier 来自每个 glyph 的 toml 配置（`AbstractSpellPart.java:226-233` 的 `GLYPH_TIER`），书等级（SpellTier ONE/TWO/THREE）决定可持有上限。学习入口三条：右键 Glyph 物品（消耗自身、`unlockGlyph`+同步 cap+按已知数量涨 mana 上限，`common/items/Glyph.java:43-73`）；`AnnotatedCodex` 把 knownGlyphs 存进 `CODEX_DATA` 组件、可转授他人（`common/items/AnnotatedCodex.java:56-95`）；命令 `/learnGlyph`（`common/command/LearnGlyphCommand.java`）。卷轴类物品走另一条线：`ItemScroll` 把法术写进 `ITEM_SCROLL_DATA` 组件（`common/items/ItemScroll.java:38-68`），配合 datapack 的 `caster_tome` 配方（`common/crafting/recipes/CasterTomeData.java:130-140`，`spell` 字段就是 ResourceLocation 列表）分发预制法术。合成期校验（在抄写台 ScribesTable）与施法期校验共用 `GlyphOccurrencesPolicyValidator`（每 glyph 的 per_spell_limit 配置）、`AugmentCompatibilityValidator`、`InvalidCombinationValidator`（每 glyph 的"禁止组合"同样是配置项，`AbstractSpellPart.java:277-280`）。**结论：解锁知识 = 玩家 cap 里的 id 集合，法术组合合法性 = 校验器链，两者只在"施法期校验"这一个交点相遇，耦合极干净。**

### 4.4 数值配置系统（问题③的硬编码侧）

每个 glyph 一个服务器 TOML：基类给出 `enabled / cost / starter / per_spell_limit / glyph_tier`（`api/spell/AbstractSpellPart.java:226-233`）；`AbstractEffect.buildConfig` 追加伤害 `damage`、增幅 `amplify`、药水时长、随机概率、augment 次数上限、augment 成本覆盖、非法组合清单（`api/spell/AbstractEffect.java:127-173, 267-297`）。效果代码读的是配置对象而非字面量，如 `EffectHarm` 伤害 = `DAMAGE.get() + AMP_VALUE.get() * amp`（`common/spell/effect/EffectHarm.java:34`）。这意味着"改数值/禁用某符文/改费用/改组合规则"全部零 datapack、零代码。

### 4.5 表现层与投射实体（问题⑤）

颜色、音效、粒子时间轴是 Spell 数据的一部分（4.1），因此任何载体（法杖、箭、符阵、impluder 炮台）施放同一法术表现一致。渲染侧：`EntityProjectileSpell` 按 `TimelineMap` 逐 tick 驱动 `ParticleEmitter`（`common/entity/EntityProjectileSpell.java:251, 274`），客户端粒子/着色体系在 `client/particle`(38 文件) 与 `api/particle`（configurations/timelines，均有 registry 供 addon 注册自定义粒子运动学）。**伤害判定发生在服务端投射物命中帧**：`onHit`（`EntityProjectileSpell.java:376-432`）先 post 可取消的 `SpellProjectileHitEvent`，处理 pierce 剩余次数/sensitive 穿透方块，然后 `resolver().onResolveEffect(level, result)`；伤害经 `IDamageEffect.attemptDamage`：`SpellDamageEvent.Pre` → `entity.hurt` → `SpellDamageEvent.Post`（`api/spell/IDamageEffect.java:39-70`）。客户端只收纯表现包（`PacketANEffect`、`PacketTimedEvent`、`EventQueue` 定时事件）。GeckoLib 驱动生物/法杖动画（`implements GeoEntity/GeoItem`，如 `EntityProjectileSpell.java:50-53`、`common/items/SpellBook.java:55`）。

### 4.6 周边复用同一 resolver 的系统

ritual（24 个 `AbstractRitual`，`api/registry/RitualRegistry`）、turret/implementer（`TileCaster`，且 turret 免 mana——`SpellResolver.expendMana` 对 `CasterType.TURRET` 直接 return，`api/spell/SpellResolver.java:273-280`）、rune（`EffectRune`）、bow/arrow（`FormSpellArrow`）、reactive 附魔触发（`PacketReactiveSpell`）都以"构造 SpellContext + 选 Resolver 子类"复用 4.2 的状态机，不各写一套执行逻辑。`EffectRewind` 甚至实现"状态回滚"：`common/spell/rewind/` 用 attachment 记录实体/方块前后态（`IRewindCallback`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`common/network/` 65 文件、约 50 个 `CustomPacketPayload`（`Networking.java:21` 统一在 `RegisterPayloadHandlersEvent` 注册）。核心 payload：`PacketCastSpell`/`PacketQuickCast`（上行施法）、`PacketUpdateCaster`/`PacketSetCasterSlot`（上行写组件）、`PacketSyncPlayerCap`/`NotEnoughManaPacket`（下行）、`PacketANEffect`/`PacketTimedEvent`（下行表现）、`PacketUpdateBookGUI`/`PacketOpenGlyphCraft`（GUI 流式内容）。
- **数据驱动边界**：能靠 JSON 改的——14+ 种自定义配方（`setup/registry/RecipeRegistry.java:39-85`：`enchanting_apparatus`、`imbuement`、`glyph` 合成、`caster_tome`、`summon_ritual`、`scry_ritual`、`crush`、`book_upgrade`、`armor_upgrade`、`spell_write`、`reactive`、`potion_flask`、`alakarkinos`、`budding_conversion`…），每种都有 `MapCodec`+`StreamCodec`，其中 `CasterTomeData` 的 `spell` 字段直接吃 glyph id 列表（`common/crafting/recipes/CasterTomeData.java:132`）；外加 vanilla 全家桶（advancement/loot/worldgen/tags，见 datagen 清单）。**不能靠 JSON 改的**——glyph 的存在性与行为逻辑（一个类一个 glyph）、每 glyph 的属性数值（走 TOML 不走 datapack）、粒子时间轴（Java registry）。即：**组合与分发是数据驱动的，语义是代码驱动的**，两层各自用最合适的载体。
- **配置**：四段全局（STARTUP/SERVER/COMMON/CLIENT，`ArsNouveau.java:87-90`）+ 每 glyph 一个 SERVER toml（4.4 前述）；`setup/config/Config.java` 提供 `isGlyphEnabled` 等聚合查询（`common/items/Glyph.java:46` 使用）。
- **datagen**：`common/datagen/` 39 provider + `patchouli/` 16 页生成器，`runs/data` 配置见 `build.gradle:56-59`；覆盖 lang（1843 行的 `LangDatagen` 含 glyph 名/描述/augment 描述全自动生成，源头是 `AbstractSpellPart.getBookDescLang`/`addAugmentDescriptions`）、配方、图鉴（Patchouli 页面与 `api/documentation` 双轨，后者配 Lucene 全文检索供 in-game wiki）。文档系统支持 addon 注入条目（`api/documentation/builder`、`Documentation.java` 1027 行）。

## 6. Mixin

`src/main/resources/ars_nouveau.mixins.json`（jar manifest `MixinConfigs` 亦声明，`build.gradle:256`），package `common.mixin`，带 `MixinPlugin`（条件启用），`compatibilityLevel JAVA_21`；无独立 server 段，公共 patch 在 `mixins`（31 项）、`client`（10 项）。代表性条目：
- `ItemStackMixin`：`@WrapMethod(method="inventoryTick")` 注入 `EffectPrestidigitation.onInventoryTick`——让"戏法"glyph 观察手持物品 tick（`common/mixin/ItemStackMixin.java:14-18`）。
- `DamageSourceMixin`：`@Inject getLocalizedDeathMessage`，`@At INVOKE ItemStack.isEmpty shift BEFORE`、cancellable，定制法术死亡消息。
- `perks/PerkLivingEntity`、`perks/UnbreakablePerk`：实现护甲 perk 的属性/耐久行为；`rewind/RewindEntityMixin`：支持 `EffectRewind` 的实体状态快照；`looting/EnchantedCountIncreaseFunctionMixin` 等 2 个：让 luck 附魔函数受法术增益影响；`camera/`(4 个)与 `elytra/`(2 个)：自定义相机跟随系统（对应 `api/camera`）；`light/`(4 个，client)：动态光源渲染（对应 `common/light`）；`structure/` 与 `jar/`：结构模板与 MobJar 维度化。
- Accessor 类：`EntityAccessor`、`LivingAccessor`、`MobAccessor`、`BlockBehaviourAccessor`、`BlockItemAccessor`、`PufferfishAccessor`、`ChatComponentAccessor`、`BrushableBlockEntityAccessor` 等，只读取私有字段。
- 另有 103 行 `META-INF/accesstransformer.cfg`（public 了 `Entity.position`、`Player.inventory`、`Explosion *` 等，配合 `validateAccessTransformers=true`，`build.gradle:36`）。整体 mixin 用量克制（61 文件对 1500），多数问题用 capability/event 解决。

## 7. 值得学的 5 条

1. **"每 glyph 一个 TOML"的配置面**（`api/registry/GlyphRegistry.java:35-45` + `api/spell/AbstractSpellPart.java:226-233`）：注册即生成 enabled/费用/tier/每咒上限/非法组合五件套，整合包作者不碰任何文件结构就能平衡数值。求仙问道的功法数值可直接抄这个形状——把"数值可调"从 datapack 挪到 server config，比 JSON 更易发现、带注释。
2. **注册表 id xmap 的最小序列化**（`api/spell/AbstractSpellPart.java:30`）：法术 = id 数组，Codec 与 StreamCodec 同构、人可读、物品 tooltip 可渲染、`/item replace …ars_nouveau:spell_caster…{spells:{…}}` 可直接造咒。功法序列照抄：存 id 列表，解析时查自定义注册表，查不到回落默认（`getSpellPartOrDefault`）而非报错——升级容错。
3. **augment 不落数据、求值时现算**（`api/spell/SpellResolver.java:220-225` 配合 `Spell.getAugments`，`Spell.java:246-260`）：序列里只有平铺的 id，效果解析前扫"紧随其后的连续增强段"构建一次性 `SpellStats`。好处：Spell 永不变异、可缓存可 hash、版本迁移就是存 id。符箓"叠加强化"完全可以复用这个语义。
4. **脱水/复水的 resolver 持久化**（`api/spell/SpellResolver.java:53-71`、`api/spell/SpellContext.java:58-80`）：带实体引用的运行时对象要跨存档/跨实体传输时，Codec 只序列化纯数据（Spell），caster 在反序列化端重新绑定。投射物、延迟法术、存档恢复共用这一套。
5. **目标侧 capability 拦截法术效果**（`api/spell/SpellResolver.java:236-246`，接口 `api/spell/IResolveListener.java`）：命中方块/实体先问其 `BLOCK/ENTITY_SPELL_RESOLVE_CAP`，目标可改判或 `STOP_ALL` 否决。修仙 mod 的"护体罡气/禁制方块抵挡法术"用这个模式实现，无需在每种效果里写特判。

## 8. 公开 API（addon 扩展点）

- 入口：`api/ArsNouveauAPI.getInstance()`（`api/ArsNouveauAPI.java:133`）——主要暴露两个 `ISpellValidator` 获取口（crafting/casting，`ArsNouveauAPI.java:96/106`）；**注册 glyph 走静态门面** `api/registry/GlyphRegistry.registerSpell(part)`，在 addon 的 Mod 构造器里调用即可（与主模组自身 `APIRegistry.setup()` 同一入口，无事件式注册）。addon 官方示例仓库在 `README.md:7`。
- 扩展点接口/基类：glyph 四基类 `AbstractCastMethod/AbstractEffect/AbstractAugment/AbstractFilter`（注：`AbstractSpellPart.java:68-78` 明示 `spellSchools`、`compatibleAugments` 是 public 可变集合，"Addons should add and access this list directly"——addon 可以给主模组的 glyph 挂新学派/新增强）；施法载体 `AbstractCaster` 子类 + `api/registry/SpellCasterRegistry.from(stack)` 识别任意物品上的组件（`api/spell/ItemCasterProvider.java`）；caster 包装 `api/spell/wrapped_caster/`（Living/Player/Tile/Empty）；`IResolveListener`、`IContextManipulator`、`IContextAttachment`（SpellContext 可扩展附件袋，`api/spell/SpellContext.java:56,116-122`）；`api/registry/` 共 21 个注册表覆盖 ritual、familiar、perk、particle timeline/color/motion、sound、imbuement、documentation 等。事件面 `api/event/` 25 类均为 cancellable 或可改写。
- 接入方式：依赖 maven `com.hollingsworth.ars_nouveau:ars_nouveau-1.21.1`（BlameJared maven），构造器期注册 glyph，datagen 可复用 `common/datagen/` 的 provider 基类生成 lang/书页（`DocProvider`/`PatchouliProvider` 支持 addon 命名空间）。生态验证：同作者 addon "Ars Elemental" 即以纯 addon 形式存在（`build.gradle:225` localRuntime 引用）。

## 附：对"求仙问道"的结论（问题⑥）

可直接借用：Spell=符文 id 列表的不可变数据结构与其 Codec/StreamCodec 双份（4.1）、`glyph → 专属 TOML` 的配置生成（4.4/§7.1）、校验器链与"合成期/施法期"分段（4.3）、augment 求值时现算 + 目标侧 capability 拦截（§7.3/7.5）、脱水/复水 resolver 与"载体无关"的 SpellContext（§7.4）——这些与加载器版本无关，是纯设计形状。必须换掉/重做：(a) glyph 语义仍是每符文一个 Java 单例类，datapack 只能改配方与数值、**不能新增符文行为**——若求仙问道要求"功法内容本身数据化"（数百门功法不可能每门一个类），需要在 effect 层之下再造一层"参数化效果模板"（record + type 注册表 + 数据驱动字段），Ars 的 `wrapped_caster/validation` 架构允许你替换这一层而不动状态机；(b) 玩家能力系统（IPlayerCap/mana cap）按 NeoForge 1.21 Attachment API 重写（Ars 已在 gametest/attachments 上留了 `AttachmentsRegistry.java` 过渡痕迹）；(c) GeckoLib 依赖与 Patchouli 文档栈视你的技术选型替换；(d) 解锁与"知识"仅存在于玩家 cap，若功法需要宗门/悟道等复合前置，Ars 没有现成形状可抄，只能照抄其"校验器读外部状态"的接口风格（`GlyphKnownValidator` 把 `IPlayerCap` 作为构造参数注入即是范例）。
