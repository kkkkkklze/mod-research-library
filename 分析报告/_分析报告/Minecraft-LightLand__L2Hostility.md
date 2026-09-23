# Minecraft-LightLand/L2Hostility 源码分析报告

## 1. 基本信息

| 项 | 值 | 来源 |
|---|---|---|
| Mod 名 / mod_id | L2 Hostility（莱特兰-恶意）/ `l2hostility` | `src/main/resources/META-INF/mods.toml` |
| 作者 | xkmc / LightLand | `build.gradle`（`group = "dev.kxmc.l2hostility"`） |
| 目标版本 / 加载器 | MC 1.20.1 / Forge `[47.1.0,)`，同时发布 NeoForge 版本（同 jar，`loaderVersion="[46,)"`） | `mods.toml` / `build.gradle`（`addModLoader("Forge","NeoForge")`） |
| Gradle 插件 | ForgeGradle `[6.0,6.2)`、mixingradle `0.7-SNAPSHOT`、curseforgegradle、minotaur、gradle-secrets | `build.gradle` |
| 映射 | `official`（注释里保留了 parchment 的写法，实际未启用） | `build.gradle` |
| Java | 17 | `build.gradle` |
| 许可证 | **All rights reserved**（闭源授权，不可直接抄代码；仅思路可借鉴） | `mods.toml` |
| 版本 | 2.5.19（`ll_version`） | `gradle.properties` |

**编译依赖（重点：这一节最能说明它的架构）**：

- **前置硬依赖（`mods.toml` mandatory=true）**：`l2library [2.5.0,)`、`l2complements [2.6.1,)`、`curios`、`patchouli`。
- **jarJar 内嵌**（打包进自己 jar，玩家无需单独装）：`l2modularblock 1.1.0`、`l2damagetracker 0.4.3`、`mob_weapon_api 0.2.13`、`Registrate MC1.20-1.3.11`、`mixinextras-forge 0.2.0-beta.8`（当 `rootMod=false` 时不 jarJar mixinextras）。
- **编译依赖但非必需**：`kubejs-forge 2001.6.5` + `rhino-forge`（`compileOnly`）、`architectury-forge 9.2.14`、`l2serial 1.2.2`、`l2tabs/l2weaponry/l2archery`。
- **兼容目标（`implementation fg.deobf(...)`，一堆）**：Twilight Forest、Jade、Citadel、Cloth Config、GeckoLib、Placebo、Apothic Attributes、Lionfish API、L_Ender's Cataclysm、BoMD、Ice and Fire、**Alex's Caves**、Ars Nouveau、Gateways to Eternity、Goety、EEEAB's Mobs、Puzzles Lib、Mutant Monsters、Mowzie's Mobs、Valhelsia Core、Forbidden Arcanus。`libs/` 目录还有 21 个本地 slim jar 走 `flatDir`。
- 结论：**它把 `l2library` 当运行时框架（Registrate 封装 / 能力系统 / 网络 / 数据包配置）、把 `l2serial` 当序列化层、把 `l2damagetracker` 当战斗事件总线**，本体只写"词条（Trait）"与"难度"两件事。这是典型的"自建框架家族 + 单体内容 mod"结构。

## 2. 源码规模与包结构

实测：`find src -name '*.java' | wc -l` = **284**（main + test）；`wc -l` 合计 = **18528** 行。

包（第 3 层）文件数：

- `content/item` **76** — 分 8 个子包：`curio/{core,curse,misc,ring}`（饰品，含 `CurseCurioItem`）、`spawner`（词条刷怪笼）、`beacon`、`wand`（词条移除/赋予杖）、`tool`、`traits`（`TraitSymbol`，每个词条自动生成一枚展示物品）、`consumable`
- `content/traits` **37** — `base/{MobTrait, AttributeTrait, SelfEffectTrait, TargetEffectTrait}`、`common`（Fiery/Regen/Adapting/Reflect/Invisible/Shulker/Gravity/AuraEffect）、`goals`（CounterStrike、Ender — 会自己注册 Goal）、`highlevel`（Split/Drain/Erosion/Corrosion/Growth/Reprint/Arena）、`legendary`（Undying/Dementor/Dispell/KillerAura/Ragnarok/Master/Pulling/Repelling）
- `content/capability` **17** — `mob`（`MobTraitCap` 409 行 + `MinionData`/`MasterData`/`CapStorageData`/`PerformanceConstants`）、`chunk`（`ChunkDifficulty`/`SectionDifficulty`/`RegionalDifficultyModifier`）、`player`（`PlayerDifficulty`）
- `content/logic` **10** — 难度计算与词条生成：`MobDifficultyCollector`、`TraitManager`、`TraitGenerator`、`DifficultyLevel`、`PlayerFinder`、`ItemPopulator`、`LevelEditor`、`TraitEffectCache`、`InheritContext`
- `init/{data,loot,registrate,advancements,network,entries}` 共 **44**；`compat/{kubejs,gateway,data,curios,jei,jade}` 共 **41**；`content/{menu,config,entity,enchantments,command,effect}` 共 **35**；`mixin` **9**

最大的 10 个文件：

| 行数 | 文件 |
|---|---|
| 578 | `init/data/LHConfig.java`（ForgeConfigSpec 集中定义） |
| 525 | `init/data/RecipeGen.java` |
| 409 | `content/capability/mob/MobTraitCap.java` |
| 314 | `content/item/beacon/HostilityBeaconBlockEntity.java` |
| 305 | `init/registrate/LHTraits.java` |
| 269 | `init/data/LHTagGen.java` |
| 268 | `init/data/LHConfigGen.java` |
| 264 | `compat/data/CataclysmData.java` |
| 259 | `content/item/beacon/HostilityBeaconScreen.java` |
| 257 | `content/config/EntityConfig.java` |

## 3. 入口与注册

主类 `src/main/java/dev/xkmc/l2hostility/init/L2Hostility.java:49` `@Mod(MODID)` + `@Mod.EventBusSubscriber(bus = MOD)`。所有注册集中在一个 `static init()`（第 70-89 行），由构造器和外部 API 共用：

```java
LHBlocks.register();  LHItems.register();  LHTraits.register();
LHEntities.register(); LHMiscs.register(); LHConfig.init();
LHDamageTypes.register(); LHEnchantments.register(); LHEffects.register();
TraitGLMProvider.register();
MobTraitCap.register(); ChunkDifficulty.register(); PlayerDifficulty.register();
HostilityTriggers.register();
```

注册框架：`LHRegistrate extends L2Registrate`（注册表，`init/entries/LHRegistrate.java`），**自建了一个 `trait` 注册表**（`LHTraits.java:33`）：

```java
public static final L2Registrate.RegistryInstance<MobTrait> TRAITS =
        L2Hostility.REGISTRATE.newRegistry("trait", MobTrait.class, RegistryBuilder::hasTags);
```

配套还手写了 `ProviderType.register("tags/trait", ...)` 让 Registrate 能给自定义注册表出 tag 数据（`LHTraits.java:35-43`）。

**最值得注意的注册模式**：`LHRegistrate.regTrait(id, supplier, configFactory)` 一条链同时做四件事——注册 `MobTrait`、注册它的 `TraitConfig` 到数据包配置生成器、生成一个 `TraitSymbol` 物品（`item(TraitSymbol::new).build()`）、生成 lang（`.lang("Tanky")`）。见 `LHTraits.java:78-86`：

```java
TANK = L2Hostility.REGISTRATE.regTrait("tank", () -> new AttributeTrait(
        ChatFormatting.GREEN,
        new AttributeTrait.AttributeEntry("tank_health", () -> Attributes.MAX_HEALTH,
                LHConfig.COMMON.tankHealth::get, AttributeModifier.Operation.MULTIPLY_TOTAL),
        ...), rl -> new TraitConfig(rl, 20, 100, 5, 20)).lang("Tanky").register();
```

即"一次声明 = 代码 + 数据包默认值 + 物品 + 本地化"。

## 4. 核心系统

### 4.1 生物词条能力（MobTraitCap）—— 全项目的中枢

`content/capability/mob/MobTraitCap.java`（`extends GeneralCapabilityTemplate<LivingEntity, MobTraitCap>`，`@SerialClass`），通过 `GeneralCapabilityHolder` 注册到 `LivingEntity`，生效条件写成一个 lambda（第 51-55 行）：

```java
new GeneralCapabilityHolder<>(new ResourceLocation(MODID, "traits"), CAPABILITY,
    MobTraitCap.class, MobTraitCap::new, LivingEntity.class,
    e -> e.getType().is(LHTagGen.WHITELIST) || e instanceof Enemy && !e.getType().is(LHTagGen.BLACKLIST));
```

关键设计点：

1. **状态机 + 延迟初始化**：`enum Stage { PRE_INIT, INIT, POST_INIT }`。`tick()` 里若未初始化则从所在区块的 `ChunkDifficulty` 拉难度再 `init(...)`；`INIT` 阶段才跑 `ItemPopulator.postFill`（补装备）与逐个 `postInit`，并把血量回满。
2. **字段级同步标记**：`@SerialClass.SerialField(toClient = true)` 精确控制哪些字段同步给客户端（`traits`/`lv`/`stage`/`minion` 等同；`data` 不同步），`syncToClient` → `MobCapSyncToClient` 包。
3. **运行中改词条用 pending 队列**：`setTrait()` 只往 `pending` 里塞，由 `clearPending()` 在 tick 的安全点统一 `put` + 调 `initialize`/`postInit`，`rank==0` 表示删除——避免在遍历 `traits` 时结构性修改（`removeTrait` 里 `if (ticking) setTrait(trait, 0)`）。
4. **性能与自净**：`PerformanceConstants.removeTraitInterval()` 控制每 N tick 清理一次 `null` 与被配置禁用的词条（`MobTrait::isBanned`）。
5. **小兵 / 主人**：`MinionData asMinion` / `MasterData asMaster` 也挂在同一能力上，`MASTER` 词条让怪物标记 `HostilityGlowing` 并周期性召唤；`pos` 非空时若 `TraitSpawnerBlockEntity` 被移除则 `mob.discard()`。
6. **继承**：`copyFrom(parent, child, parentCap)` 让分裂类词条（SplitTrait）把父母的词条按 `MobTrait.inherited(cap, rank, InheritContext)` 传递，`dropRate *= splitDropRateFactor` 防止刷物品。

### 4.2 三层难度体系

- **玩家难度** `content/capability/player/PlayerDifficulty.java`：`@SerialClass` 的 `DifficultyLevel`、`maxRankKilled`、`rewardCount`、`dimensions`（`TreeSet<ResourceLocation>`，记录玩家进过的维度）；`onClone(boolean isWasDeath)` 死亡惩罚（可配 `keepInventory` 免罚、`deathDecayTraitCap` 掉词条上限）；tick 里若跨区块则推送 `ChunkCapSyncToClient`。
- **区块难度** `content/capability/chunk/ChunkDifficulty.java`：挂在 `LevelChunk` 上，内部是 `SectionDifficulty[] sections`（按 16 格高分段，`getSection(y)` 用 `Mth.clamp` 兜底）；`at(level, pos)` 用 `ChunkStatus.CARVERS` 取 chunk 并展开 `ImposterProtoChunk`，保证世界生成期就能拿到。`RegionalDifficultyModifier` 是它的对外接口。
- **聚合** `content/logic/MobDifficultyCollector.java`：`acceptConfig(DifficultyConfig)` 把多个来源按公式叠加（`suppression = 1 - (1-a)(1-b)` 这种"概率叠加"写法），`acceptBonus`/`traitCostFactor`/`setCap` 供词条与饰品反向影响难度，最终 `getDifficulty(random)` 用 `random.nextGaussian() * sqrt(varSq)` 生成正态分布难度并 clamp 到 `[min, cap]`。

`TraitManager.fill()` 是总入口：`cap.clampLevel(...)` 封顶 → `scale()` 给 `MAX_HEALTH` 加 `MULTIPLY_TOTAL` 属性的 `AttributeModifier`（UUID 由 `MathHelper.getUUIDFromString("hostility_health")` 稳定生成，重复时先 `removeModifier` 再 `addPermanentModifier`）→ `ItemPopulator.populateArmors` 补护甲 → `TraitGenerator.generateTraits` 抽词条。整条链上到处是 `LHTagGen.NO_SCALING` / `NO_TRAIT` / `ARMOR_TARGET` 这类实体标签开关。

### 4.3 词条生成器（加权 + 成本预算）

`content/logic/TraitGenerator.java`：构造器先过滤出 `traitPool`（排除配置黑名单、`MobTrait.allow(entity, mobLevel, maxTraitLevel)` 通过的），累计 `weights`；`pop()` 用「`val = rand.nextInt(weights)` 后逐项扣减」的加权抽样；`ins.trait_cost < 0.01` 时 `maxTrait = -1`（不限）否则按 `max / trait_cost` 限制数量。`EntityConfig` 可给出 `presetTraitsOnly`、带 `condition` 的基础词条、`maxLevel`、`minSpawnLevel`（低于则 `shouldDropDiscard`）。

### 4.4 词条基类与战斗钩子

`content/traits/base/MobTrait.java`（`extends NamedEntry<MobTrait> implements ItemLike`）是一个**纯事件回调基类**，子类只覆写需要的方法：`initialize/postInit/tick/onHurtTarget/postHurtImpl/onAttackedByOthers/onHurtByOthers/onCreateSource/onDamaged/onDeath/inherited/modifyBonusDamage`。属性类词条全部走 `AttributeTrait`（`AttributeEntry` 把 `Attribute` + `LHConfig` 的 `IntSupplier` + `Operation` 组合起来，等级 = 属性叠加次数）。战斗数值走 **l2damagetracker**：`AttackEventHandler.register(4500, new LHAttackListener())`（`L2Hostility.java:102`），词条通过 `AttackCache` / `CreateSourceEvent` / `TraitEffectCache` 参与伤害计算，`TraitEffectCache.reflectTrait(this)` 支持伤害反弹类词条。KubeJS 侧暴露 `DamageModifier` 供脚本改伤害。

### 4.5 配置 = 数据包（l2library 序列化配置）

`content/config/` 下 4 个 `@SerialClass extends BaseConfig`：`WorldDifficultyConfig`（`levelMap`/`biomeMap`/`levelDefaultTraits`/`structureDefaultTraits`）、`TraitConfig`、`WeaponConfig`、`EntityConfig`。用 `@ConfigCollect(CollectType.MAP_OVERWRITE | MAP_COLLECT)` 声明合并策略（同名覆盖 vs 合并进列表），在 `L2Hostility.java:64-67` 绑定到 `ConfigTypeEntry`，读取走 `L2Hostility.ENTITY.getMerged().get(...)`、`L2Hostility.DIFFICULTY.getMerged().get(ServerLevel, BlockPos, EntityType)`。`WorldDifficultyConfig.get(...)` 会**按当前坐标反查结构**（`structureManager.getAllStructuresAt(pos)` + `fillStartsForStructure` + `structureHasPieceAt`），实现"结构内怪物额外带词条"。

`TraitConfig` 还有个巧思：`getBlacklistTag()` / `getWhitelistTag()` 由词条 id 推导实体标签名（`<id>_blacklist` / `<id>_whitelist`），`addBlacklist(tagAppender -> ...)` 在**注册阶段就把 tag 生成器登记进 `LHTagGen.ENTITY_TAG_BUILDER`**，datagen 时统一产出——即"用实体标签表达词条的适用/禁用范围"，整合包可只改 tag。

## 5. 网络 / 数据驱动 / 配置 / datagen

**网络**：`PacketHandlerWithConfig`（l2library）+ `SerialPacketBase`（l2serial）自动序列化，`L2Hostility.java:54-60` 注册 4 个 `PLAY_TO_CLIENT` 包：`MobCapSyncToClient`、`TraitEffectToClient`、`LootDataToClient`、`ChunkCapSyncToClient`。发送侧封装 `HANDLER.toTrackingPlayers(...)` / `toClientPlayer(...)` 与 `toTrackingChunk(chunk, packet)`（`L2Hostility.java:151-153`，用 `PacketDistributor.TRACKING_CHUNK`）。客户端处理在 `init/network/ClientSyncHandler.java`：区块难度用 `TagCodec.fromTag(tag, ChunkDifficulty.class, diff, e -> true)` 反序列化；词条特效（不死图腾粒子、杀手光环火焰）用 `TraitEffectToClient` + 函数表分发。**没有用 Forge SimpleChannel 手写 write/read**，全部靠注解序列化。

**数据驱动（本 mod 的核心玩法数据）**：`init/data/LHConfigGen.java extends ConfigDataProvider`（l2library），在 `GatherDataEvent` 里产出 `data/l2hostility/.../difficulty|trait|weapon|entity` 配置文件；`L2Hostility.REGISTRATE.CONFIGS` 收集所有 `regTrait` 自动登记的 `TraitConfig`。`compat/data/` 下为 Cataclysm、Ice and Fire、Mowzie's Mobs、Mutant Monsters、Twilight Forest、BoMD 分别写了一个 `XxxData` 类生成适配配置。

**配置**：`init/data/LHConfig.java`（578 行，全仓最大文件）集中所有 `ForgeConfigSpec` 项（COMMON/CLIENT），如 `maxMobLevel`、`tankHealth`、`exponentialHealth`、`healthFactor`、`globalTraitChance`、`globalTraitSuppression`、`overHeadLevelColor`、`killerAuraRange`。词条开关用 `map.containsKey(path)` 二次拦截（`MobTrait.isBanned()`，第 171-174 行），因此整合包可以不改数据包只改 toml 就把某个词条禁用。

**Datagen**：完整。`L2Hostility.java:123-149` 的 `gatherData` 通过 `REGISTRATE.addDataGenerator(...)` 挂 `LangData`、`RecipeGen`、`LHTagGen`（BLOCK/ITEM/ENTITY/ENCHANT/EFFECT/TRAIT 六类 tag）、`AdvGen`、`SlotGen`、`TraitGLMProvider`（全局掉落修改）、`LHDamageTypes`、`GatewayConfigGen`（仅装了 Gateways 时）、`LHConfigGen`。`src/test/java/organize/GUIGenerator.java` 是一个独立工具类（259 行，用于生成 GUI 布局）。

**自定义进度触发器**：`init/advancements/HostilityTriggers` 提供 `TRAIT_LEVEL`、`TRAIT_COUNT`、`KILL_TRAITS`、`TRAIT_FLAME`、`TRAIT_EFFECT`，`MobTraitCap.onKilled()` 在击杀归属为玩家时触发。

## 6. Mixin

配置：`src/main/resources/l2hostility.mixins.json`（`priority: 1000`、`package: dev.xkmc.l2hostility.mixin`、`injectors.defaultRequire = 1`），gradle 侧 `mixin { add sourceSets.main, "l2hostility.refmap.json"; config "l2hostility.mixins.json" }`，manifest 里带 `MixinConfigs`。**只有 10 个 mixin 类**——它把绝大部分改动做成了事件 + 能力 + 数据包，这是很值得学的克制。

- `MobMixin`（`@Mixin(Mob.class)`）→ 用 **MixinExtras `@WrapOperation`** 包住 `enchantSpawnedArmor` / `enchantSpawnedWeapon` 方法体里对 `EnchantmentHelper.enchantItem(RandomSource, ItemStack, int, boolean)` 的调用，把 `level += cap.getEnchantBonus()`（= `lv * enchantmentFactor`），无侵入地让高等级怪物装备附魔更强。
- `EntityMixin` → `Entity#isCurrentlyGlowing`、`Entity#getTeamColor`、`Entity#isInRain` 三个 `@Inject(HEAD, cancellable)`：召唤物/主人词条怪发光、颜色区分。
- `ItemStackMixin` → `ItemStack#inventoryTick`（词条物品计时）、`ItemStack#useOn`（`cancellable`，词条物品交互）。
- `PlayerMixin`、`SlimeMixin`、`ShulkerBulletMixin`（史莱姆/潜影贝词条的行为修补）。
- `CuriosImplMixinHooksMixin`（兼容 Curios 饰品栏钩子）、`ForgeInternalHandlerAccessor`（accessor）。
- 客户端 2 个：`GeoEntityRendererMixin`、`GeoReplacedEntityRendererMixin` —— GeckoLib 模型渲染器补丁。
- AT 文件：`src/main/resources/META-INF/accesstransformer.cfg`。

## 7. 值得学的 5 条具体做法

1. **「一次声明 = 五份产物」的 TraitBuilder**：`LHRegistrate.regTrait()` 在一次调用里完成注册表条目 + 数据包默认配置 + 展示物品 + lang + tag，新人加词条只需照抄一行。文件：`init/entries/{LHRegistrate,TraitBuilder}.java`、`init/registrate/LHTraits.java`。适用场景：任何"注册内容 + 必须同时给默认数据包配置"的系统（词条、附魔、自定义注册表）。
2. **用能力（Capability）承载玩法状态，用 `toClient` 标记精确同步**：`MobTraitCap` / `ChunkDifficulty` / `PlayerDifficulty` 三个能力各管一层，字段级 `@SerialField(toClient = true)` 控制同步面。文件：`content/capability/**`。适用场景：给原版实体/区块/玩家挂自定义状态且需要多人同步。
3. **三层难度 + 正态分布 + 概率叠加**：玩家难度 → 区块分段难度 → `MobDifficultyCollector` 聚合，`getDifficulty()` 用 `nextGaussian()*sqrt(varSq)` 出难度，`suppression` 用 `1-(1-a)(1-b)` 叠加。文件：`content/logic/MobDifficultyCollector.java`。适用场景：任何"随玩家进展动态加难"的设计，且天然可被多个来源（维度/生物群系/结构/饰品/进度）叠加影响。
4. **运行中修改自身集合用 pending 队列**：`MobTraitCap.setTrait/clearPending` 把"改词条"变成下一 tick 的安全点动作，避免遍历中改 Map，并顺带解决了"改完要调 `initialize/postInit` 一次"的语义。文件：`content/capability/mob/MobTraitCap.java:228-261`。适用场景：词条/增益/属性集合在 tick 内被修改的场景。
5. **用实体标签表达"词条 × 生物"的适用关系，并让 tag 生成自动化**：`TraitConfig.getBlacklistTag()/getWhitelistTag()` 由词条 id 推导 tag 名，`addBlacklist(pvd -> ...)` 在注册期就把生成器塞进 `LHTagGen.ENTITY_TAG_BUILDER`，`allows(type)` 读 tag 判断。文件：`content/config/TraitConfig.java`。适用场景：需要给整合包/其他 mod 留"只管数据不改代码"的开关时，tag 比 config 项更灵活。

（补充）**KubeJS 双轨扩展**：`compat/kubejs/LHKJSPlugin.java` 把 `trait` 注册表注册进 KubeJS（`RegistryInfo.of(ResourceKey.createRegistryKey(new ResourceLocation(MODID,"trait")), MobTrait.class)`），并提供 4 种脚本词条类型 `basic/legendary/attribute/effect` 与 `TraitItemBuilder`，同时把 `L2Hostility`/`DamageModifier` 绑进脚本绑定，`clearCaches()` 里清理脚本注册的 `CustomAttackListener` 防止重载泄漏。文件：`compat/kubejs/**`。这是"让整合包用脚本加内容"的完整范例。

## 8. 对外扩展点（它本身也充当 API 提供方）

虽然没有独立 `api` 包，但它对外的三个接入面很清晰：

1. **数据包配置**（最推荐）：`data/l2hostility/` 下的 `difficulty` / `trait` / `weapon` / `entity` 四类配置，用 `@ConfigCollect(MAP_OVERWRITE|MAP_COLLECT)` 控制合并；整合包可只写 JSON 就改难度曲线、给某个生物预设词条、给结构配专属词条。生成器见 `init/data/LHConfigGen.java`，`compat/data/*Data.java` 是"如何为别的 mod 写适配数据"的现成模板。
2. **自定义注册表 `l2hostility:trait`** + tag：`LHTraits.TRAITS` 走 `RegistryBuilder::hasTags`，并为 `tags/trait` 注册了 Registrate `ProviderType`；其他 mod 可以注册自己的 `MobTrait` 子类并用 tag 控制适用范围。
3. **KubeJS 脚本**（无需编译）：`trait` 的 4 种 builder 类型 + `TraitItemBuilder`，绑定 `L2Hostility` 与 `DamageModifier`；仓库根目录 `examples/kubejs/` 提供示例。

另外它依赖的 `l2library`（能力/网络/序列化配置/Registrate 封装）与 `l2serial`（注解序列化）是同一家族的通用框架——若要复用这套架构，应先研究这两个库，而不是照抄 L2Hostility。
