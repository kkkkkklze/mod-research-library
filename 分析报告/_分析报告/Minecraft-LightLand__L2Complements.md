# Minecraft-LightLand/L2Complements 源码分析报告

## 1. 基本信息

| 项 | 值 | 来源 |
|---|---|---|
| Mod 名 / mod_id | L2 Complements（莱特兰-扩充）/ `l2complements` | `src/main/resources/META-INF/mods.toml` |
| 作者 | xkmc / LightLand | `build.gradle`（`group = "dev.kxmc.l2complements"`） |
| 目标版本 / 加载器 | MC 1.20.1（`versionRange="[1.20.1,1.20.2)"`）/ Forge `[47.1.0,)` | `mods.toml` |
| Gradle 插件 | ForgeGradle `[6.0,6.2)`、mixingradle、curseforgegradle、minotaur、gradle-secrets | `build.gradle` |
| 映射 | `official` | `build.gradle` |
| Java | 17 | `build.gradle` |
| 许可证 | **All rights reserved**（闭源授权） | `mods.toml` |
| 版本 | 2.6.1（`ll_version`） | `gradle.properties` |

**编译依赖（重点）**：

- **必需**：`l2library 2.5.3`（框架：Registrate 封装 / 序列化配置 / PacketHandlerWithConfig / `GeneralEventHandler`）、`l2serial 1.2.2`（注解序列化 + 网络包基类）、`l2screentracker 0.1.4`（`DefaultQuickAccessActions` 快捷访问栏）、`l2itemselector 0.1.8`、`l2tabs 0.3.2`（创造模式标签页）。
- **jarJar 内嵌**：`l2damagetracker 0.4.4`（**关键**：材料系统 `IMatVanillaType`/`GenItemVanillaType`/`GenericArmorItem`/`GenericTieredItem`、`AttackEventHandler`、`ArmorEffectConfig` 都从这里来）、`Registrate MC1.20-1.3.3`、`mixinextras-forge 0.2.0-beta.8`。
- **可选/软兼容**（`mods.toml`）：`l2hostility [2.4.20,) ordering=BEFORE`、`curseofpandora [2.4.15,) ordering=BEFORE`；`runtimeOnly pandora`。
- **代码内 soft-compat**：JEI/EMI（`LCJeiPlugin`/`LCEmiPlugin`）、Curios（`CurioCompat`）、Twilight Forest（`TFCompat`）、Ars Nouveau（`compat/ars/`）、Forbidden Arcanus（`compat/forbidden/`）。
- 定位：它是 **L2 家族的"基础内容与前置库"** —— L2Hostility 的 `mods.toml` 把它列为 `mandatory=true`，且 `L2Hostility` 里到处 `import dev.xkmc.l2complements.init.registrate.LCEffects/LCItems`。因此它的角色更接近"给同家族 mod 提供材料/附魔/效果/谓词的公共服务层"，只是没有独立 `api` 包。

## 2. 源码规模与包结构

实测：`find src -name '*.java' | wc -l` = **225**（含 `src/test/java/organize/GUIGenerator.java`）；`wc -l` 合计 = **12297** 行。

包（第 2 层）文件数：

- `content/enchantment` **56** — 分 `core`（11 个基类/构建器）、`digging`（23 个，范围挖掘框架）、`weapon`（7）、`armors`（5）、`special`（5）
- `content/item` **48** — `anvil`（永恒铁砧 Block+Menu）、`base`（`ContainerBook`/`ScreenBook` GUI 书籍）、`create`（Create 联动：`RefinedRadianceItem`/`ShadowSteelItem`/`NoGravMagicalDohickyItem`/`VoidEyeItem`）、`curios`、`equipments`（5 种材料 × Tool/Armor 各 1 类）、`misc`（各种图腾、`WarpStone`、`WindBottle`、`FireChargeItem`）、`wand`（8 根法杖）
- `content/effect` **13** — `force`（`FlameEffect`/`IceEffect`/`CurseEffect`/`ArmorReduceEffect`/`StoneCageEffect`/`NoSelfRenderEffect`）、`skill`（`BleedEffect`/`CleanseEffect`/`StackingEffect`/`SkillEffect`/`EmeraldPopeEffect`）
- `init/data` **10**（`RecipeGen` 1244 行、`LCConfig`、`TagGen`、`LangData`、`LCConfigGen`、`DamageTypeGen`、`LCDatapackRegistriesGen`、`LCSpriteSourceProvider`、`LCKeys`）、`content/client` **9**、`init/registrate` **8**、`content/entity` **8**（`fireball` 4 种自定义火球）、`content/{recipe,feature}` 各 **5**、`compat/ars` **5**、`events` **9**、`mixin` **16**、`init/materials` **2**

最大的 10 个文件：

| 行数 | 文件 |
|---|---|
| 1244 | `init/data/RecipeGen.java`（全部配方） |
| 288 | `init/registrate/LCItems.java` |
| 269 | `init/registrate/LCEnchantments.java` |
| 267 | `src/test/java/organize/GUIGenerator.java` |
| 242 | `init/data/LCConfig.java` |
| 223 | `events/MagicEventHandler.java` |
| 203 | `content/enchantment/core/EnchantmentRecipeBuilder.java` |
| 195 | `init/data/TagGen.java` |
| 194 | `events/SpecialEquipmentEvents.java` |
| 177 | `mixin/ItemStackMixin.java` |

## 3. 入口与注册

主类 `src/main/java/dev/xkmc/l2complements/init/L2Complements.java:50` `@Mod(MODID)` + `@Mod.EventBusSubscriber(bus = MOD)`。构造器（第 64-78 行）一次性完成：

```java
ForgeMod.enableMilkFluid();          // 强制启用 Forge 的牛奶流体
LCItems.register();  LCBlocks.register();  LCEffects.register();  LCParticle.register();
LCEnchantments.register();  LCEntities.register();  LCRecipes.register();
LCConfig.init();  SoulBoundPlayerData.register();  DamageTypeGen.register();
new L2ComplementsClick(new ResourceLocation(MODID, "main"));
AttackEventHandler.register(5000, new MaterialDamageListener());
```

注册框架：`L2Registrate`（来自 l2library，Registrate 封装），每个注册域一个 `LCXxx` 类（`LCItems`/`LCBlocks`/`LCEnchantments`/`LCEffects`/`LCEntities`/`LCParticle`/`LCRecipes`）。两个值得注意的写法：

1. **自定义附魔类别**：`LCEnchantments.java:30` `public static final EnchantmentCategory ALL = EnchantmentCategory.create("ALL", e -> e.getMaxStackSize() == 1);` —— 一个"只要不能堆叠就能附"的万能类别，绕开原版类别限制。
2. **自定义网络通道参数直接写在 `PacketHandlerWithConfig` 构造里**（第 53-59 行），4 个包一次注册：

```java
new PacketHandlerWithConfig(new ResourceLocation(MODID, "main"), 5,
    e -> e.create(EmptyRightClickToServer.class, PLAY_TO_SERVER),
    e -> e.create(RotateDiggerToServer.class, PLAY_TO_SERVER),
    e -> e.create(WandEffectToClient.class, PLAY_TO_CLIENT),
    e -> e.create(SpeedTrackerPacket.class, PLAY_TO_CLIENT));
```

`FMLCommonSetupEvent` 里做三件事：`LCEffects.registerBrewingRecipe()`、给 3 种自定义火球注册 `DispenserBlock.registerBehavior` 发射器行为、把永恒铁砧注册进 `DefaultQuickAccessActions.quickAccess(MenuType.ANVIL, ...)`（l2screentracker 的快捷栏双击开 GUI）。

## 4. 核心系统

### 4.1 附魔体系（56 个类，本 mod 的主体）

`content/enchantment/core/` 是一套**分层基类**：

- `ImmuneEnchantment` → `BannableEnchantment`（可用 `LCConfig.enableImmunityEnchantments` 全局禁用，禁用时 `getFullname` 返回"BANNED + 删除线样式"，`BannableEnchantment.java:19-25`）
- `SingleLevelEnchantment`（单级）、`CraftableEnchantment`（带 `getCraftableLevels()`）、`UnobtainableEnchantment`（不可附魔台获得）、`CustomDescEnchantment`（自定义 tooltip 逐等级描述 + `getDecoColor` 覆盖字符颜色）
- `AttributeEnchantment` / `BattleEnchantment` / `SourceModifierEnchantment` / `DiggerAndSwordEnchantment`（工具与剑双适用）

**附魔配方自动化**是亮点：`core/EnchantmentRecipeBuilder.java` 实现 `RecipeBuilder`，用原版工作台形状配方（`rows` + `key`）来合成附魔书，`compat/ars` 与 `compat/forbidden` 下各写了一份 `XxxRecipeBuilder` 把同样的配方导到 Ars Nouveau 与 Forbidden Arcanus 的配方类型。`LCEnchantments` 里每个附魔用 `reg(...)` 一行声明（`shulker_armor`/`ender_mask`/`ender`/`smelt`/`cubic`/`plane`/`vein`/`tree`/`echo`/`wind_sweep`/`ice_blade`/`soul_bound`/`life_sync`/`eternal`…）。

**附魔免疫/覆盖的落地方式全靠 6 个 mixin 类**（不是事件）：`ItemStackMixin` 用 `@Inject(HEAD, cancellable)` 短路 `makesPiglinsNeutral` / `isPiglinCurrency` / `isEnderMask` / `canWalkOnPowderedSnow`；`LivingEntityMixin` 短路 `canStandOnFluid` / `canFreeze`；`EntityMixin` 与 `ItemEntityMixin` 短路 `dampensVibrations`（对应 `DAMPENED` 附魔，与 `SpecialEquipmentEvents.blockSound(stack)` 联动）。

### 4.2 范围挖掘（Range Digging）框架 —— 最值得抄的一块

`content/enchantment/digging/`（23 个类）把"连锁挖掘"抽象成三级可组合结构：

- **`BlockBreaker`（接口，选择哪种形状 + 描述 + 可合成等级）** → **`BlockBreakerInstance`（`find(level, pos, pred)` 返回待破坏方块列表）** → 由 `RangeDiggingEnchantment` 承载。

```java
public interface BlockBreaker {
    BlockBreakerInstance getInstance(DiggerContext ctx);
    int getMaxLevel();
    default boolean ignoreHardness() { return false; }
    List<Component> descFull(int lv, String key, boolean alt, boolean book);
    default Set<Integer> getCraftableLevels() { return CraftableEnchantment.DEF; }
}
```

已实现的形状：`CubicBlockBreaker`、`PlaneBlockBreaker`、`SmartPlaneBlockBreaker`、`DrillBlockBreaker`、`OreDigger`（矿脉，`VeinInstance`）、`EchoDigger`（`EchoInstance`）、`TreeDigger`（`TreeInstance`）、`CubicChunkBreaker` / `PlaneChunkBreaker`（超大范围）、`DelayedBlockBreaker`（分批延迟）。

关键设计点：

1. **递归守卫**：`RangeDiggingEnchantment.execute(player, run)` 用一个 `synchronized (BREAKER)` 的 `Set<UUID>` 防止"破坏方块本身又触发附魔"导致无限递归（`RangeDiggingEnchantment.java:40-59`），并暴露 `isSuppressed(uuid)` 给 `ServerPlayerGameModeMixin`（在 `destroyBlock` 的 HEAD/RETURN 各 `@Inject` 一次）。
2. **硬度门槛**：`getTargets()` 先算 `hardness = state.getDestroySpeed * LCConfig.chainDiggingHardnessRange`（`ignoreHardness()` 为 true 时取 -1 表示不限），`canBreak` 同时校验 `player.hasCorrectToolForDrops(state)` 与 `speed <= hardness`，避免把黑曜石一起连锁掉。
3. **大范围用持久化调度**：方块数超过 `chainDiggingDelayThreshold` 时改走 `GeneralEventHandler.schedulePersistent(new DelayedBlockBreaker(player, blocks)::tick)`（l2library 的持久任务调度），并且可要求额外带 `ENDER` 附魔，否则发 `LangData.IDS.DELAY_WARNING` 提示（第 105-125 行）。
4. **多把范围附魔的切换**：`DiggerHelper` 把"当前选中的挖掘附魔"存进 `ItemStack` 的 tag（key = `l2complements:selected_digger`），客户端按键发 `RotateDiggerToServer(reverse)` 包，服务端 `DiggerHelper.rotateDigger(stack, reverse)` 在附魔集合里轮换。即"用物品 NBT 表达选中态 + 一个只带 boolean 的包"。
5. **挖掘预览**：客户端 `content/client/RangeDiggingOutliner.java` + `RangeDiggingOverlay.java` 按 `LCConfig.CLIENT.diggingPreview` 渲染将要被破坏的位置。

### 4.3 材料系统（LCMats 枚举 → 全套装备）

`init/materials/LCMats.java` 是一个 `enum implements IMatVanillaType`（接口来自 `l2damagetracker`），5 个条目 `TOTEMIC_GOLD`/`POSEIDITE`/`SHULKERATE`/`SCULKIUM`/`ETERNIUM`，每条声明：等级、装备音效、`ToolStats`、`ArmorStats`、`ToolConfig`、`ArmorConfig`、`ExtraToolConfig`、`ExtraArmorConfig`、工具手柄材料、**盔甲纹饰颜色**（`ChatFormatting trim_text_color`，在 `gatherDataAfter` 里被生成为 `TrimMaterial` 数据包注册项）。构造器里 `tier = new ForgeTier(level, tool.durability(), ...)`。配合 `L2Complements.MATS = new GenItemVanillaType(MODID, REGISTRATE)` 一行生成全套 5×（镐斧锹锄剑 + 4 件盔甲 + 纹饰）。

配套的 `events/SpecialEquipmentEvents.java` 用 `instanceof GenericTieredItem / GenericArmorItem` 读取 `getExtraConfig()`（`hideWithEffect()` / `dampenVibration()`）实现"隐身时装备也隐藏"、"降低振动"这类装备特性——**把特性写进材料配置而非写进新物品类**，是很好的复用模式。`LCConfigGen` 则把"哪套盔甲免疫哪些负面效果"输出为 `L2DamageTracker.ARMOR` 数据包配置（`ArmorEffectConfig`）。

### 4.4 永恒铁砧与 GUI 书籍

- `content/item/anvil/`：`EternalAnvilBlock` + `EternalAnvilMenu`（自建 Container/Menu），`mixin/AnvilBlockMixin`（`damage` HEAD cancellable，铁砧不损坏）、`mixin/AnvilScreenMixin`（`keyPressed` HEAD，容器界面按键），并用 `DefaultQuickAccessActions.quickAccess(MenuType.ANVIL, LCBlocks.ETERNAL_ANVIL.asItem(), ...)` 接入快捷栏。
- `content/item/base/ContainerBook` + `ScreenBook`：可翻页书籍 GUI 的可复用基类。

### 4.5 效果 / 弹射物 / 法杖

`content/effect/force`（火/冰/诅咒/破甲/石笼，多为"持续施加的强制效果"）与 `content/effect/skill`（`BleedEffect` 流血、`CleanseEffect` 净化、`StackingEffect` 可叠层）；`content/entity/fireball` 有 `BaseFireball` + `SoulFireball`/`StrongFireball`/`BlackFireball`，并在 `setup` 里给它们注册发射器行为；`content/item/wand` 有 8 根法杖（`BoreasScepter`/`HeliosScepter`/`HellfireWand`/`WinterStormWand`/`SonicShooter`/`DiffusionWand`…）配合 `WandEffectToClient` 做客户端特效。

### 4.6 Feature Predicate（可组合的"条件谓词"）

`content/feature/FeaturePredicate.java` 只有一个 `boolean test(LivingEntity e)`，实现有 `EntityFeature`、`EnchantmentFeaturePredicate`（`EnchantmentHelper.getEnchantmentLevel(e, entity) > 0`）、`SlotEnchantmentFeaturePredicate`、`CurioFeaturePredicate`（查 Curios 饰品）。这些谓词被 `LCConfig`（效果/装备条件）与 `MagicEventHandler` 复用，是"把条件写成对象"的轻量方案。

## 5. 网络 / 数据驱动 / 配置 / datagen

**网络**：`PacketHandlerWithConfig`（l2library）+ `SerialPacketBase`/`@SerialClass`（l2serial）**全注解序列化，无手写 write/read**。4 个包：`EmptyRightClickToServer`（空手右键）、`RotateDiggerToServer`（只带一个 `boolean reverse`）、`WandEffectToClient`、`SpeedTrackerPacket`。

**配置**：`init/data/LCConfig.java`（242 行）两个 ForgeConfigSpec：`Client`（`renderEnchOverlay`/`enchOverlayZVal`/`diggingPreview`）与 `Common`（`chainDiggingHardnessRange`、`chainDiggingDelayThreshold`、`delayDiggingRequireEnder`、`enableImmunityEnchantments`、`windSpeed`、`belowVoid`、`phantomHeight`、`eternalTotemCoolDown`、各法杖伤害/冷却…）。

**数据驱动配置**：`init/data/LCConfigGen.java extends ConfigDataProvider`（l2library），把"盔甲 → 免疫效果"写成 `L2DamageTracker.ARMOR` 配置（`ArmorEffectConfig.add(LCMats.TOTEMIC_GOLD.armorPrefix(), MobEffects.POISON, ...)`），因此整合包可只改数据包改盔甲特性。

**Datagen（很完整，是本仓库最值得看的工程化部分）**：

- `gatherData`（`EventPriority.HIGH`）：`REGISTRATE.addDataGenerator(ProviderType.LANG/RECIPE/BLOCK_TAGS/ITEM_TAGS/ENTITY_TAGS, ...)` + 自定义 ProviderType `TagGen.EFF_TAGS`（药水效果标签）与 `TagGen.ENCH_TAGS`（附魔标签）+ `LCConfigGen` + **`LCSpriteSourceProvider`**（自动生成 `atlases` 的 SpriteSource，让自定义 GUI 贴图进图集）。
- `gatherDataAfter`（`EventPriority.LOW`）：`DamageTypeGen`（生成 damage_type 数据包）+ `LCDatapackRegistriesGen`，用 `RegistrySetBuilder.add(Registries.TRIM_MATERIAL, ctx -> ...)` 遍历 `LCMats.values()` 生成 5 个盔甲纹饰材料（颜色取 `e.trim_text_color`）；若加载了 Forbidden Arcanus 再生成一份 `FARegistries.RITUAL`。

## 6. Mixin

配置：`src/main/resources/l2complements.mixins.json`（`priority: 1000`、`package: dev.xkmc.l2complements.mixin`）。共 16 个类，10 个通用 + 6 个客户端。大量使用 **MixinExtras**（`@WrapOperation` / `@ModifyReturnValue` / `@ModifyVariable`），而不是 `@Redirect`。

通用：

- `ItemStackMixin`（177 行，最重）：`@Inject(HEAD, cancellable)` → `makesPiglinsNeutral`、`isPiglinCurrency`、`isEnderMask`、`canWalkOnPowderedSnow`；`@ModifyVariable(at = LOAD, argsOnly)` + `@Inject(HEAD, cancellable)` → `hurtAndBreak`；`@WrapOperation` 包住 `hurt` 里的 `setDamageValue`；`@ModifyReturnValue` → `hurt`、`getMaxDamage`、`getSweepHitBox`（**自定义耐久上限与耐久条**）
- `LivingEntityMixin`：`@WrapOperation` 改 `getArmorCoverPercentage` 里的 `ItemStack.isEmpty()`；`@Inject(HEAD, cancellable)` → `canStandOnFluid`、`canFreeze`；`@WrapOperation` 改 `dropExperience` 里的 `ExperienceOrb;award`
- `ItemMixin`：`@WrapOperation` 改 `getBarWidth`/`getBarColor` 里对 `Item;getMaxDamage` 的调用（**让自定义耐久上限在耐久条上正确显示**）
- `ServerPlayerGameModeMixin`：`destroyBlock` 的 `@At("HEAD")`/`@At("RETURN")`（配合范围挖掘的递归守卫）
- `BlockMixin` → `Block#spawnDestroyParticles`（HEAD, cancellable）；`BlockBehaviorMixin` → `IBlockExtension#getDestroyProgress`（HEAD）；`ItemEntityMixin` → `dampensVibrations` + `hurt` 内 `ItemStack;onDestroyed` 注入点；`EntityMixin` → `dampensVibrations`；`AnvilBlockMixin` → `damage`（HEAD, cancellable）；`LevelAccessor`

客户端：`AnvilScreenMixin`（`keyPressed`）、`ElytraLayerMixin`（`@WrapOperation`，让自定义鞘翅物品渲染）、`FogRendererMixin`（`@WrapOperation` 改 `setupFog` 里的 `Entity;isSpectator()Z`，用于自定义雾）、`HumanoidArmorLayerMixin`（`renderArmorPiece` HEAD cancellable，实现"隐身穿透明盔甲"）、`ItemInHandLayerMixin`（`renderArmWithItem` HEAD cancellable）、`LocalPlayerMixin`（`hurtTo`/`handleEntityEvent` 的 TAIL）。

## 7. 值得学的 5 条具体做法

1. **把"连锁挖掘"抽象成 `BlockBreaker` + `BlockBreakerInstance` 两级接口**：形状（cubic/plane/vein/tree/drill/echo/chunk…）与执行（`RangeDiggingEnchantment`）分离，加新形状只需实现 `getInstance(ctx)` 与 `find(...)`。文件：`content/enchantment/digging/{BlockBreaker,BlockBreakerInstance,RangeDiggingEnchantment}.java`。适用场景：任何"多形状/多模式"的工具或法术（挖掘、范围攻击、区域放置）。
2. **用 `Set<UUID>` 守卫 + `execute(player, run)` 包裹，防止附魔自身递归触发**：`synchronized` + try/finally 保证异常也能摘除，并把 `isSuppressed(uuid)` 暴露给 `ServerPlayerGameModeMixin` 判定。文件：`content/enchantment/digging/RangeDiggingEnchantment.java:38-59`。适用场景：任何"破坏方块会再次触发同一事件"的连锁/分裂机制。
3. **一个 `enum implements IMatVanillaType` 生成整套材料**：`LCMats` 每条含 Tier/ArmorMaterial/工具属性/盔甲属性/额外配置/纹饰颜色，配合 `GenItemVanillaType` 一行出全套装备，顺便在 datagen 阶段产出 `TrimMaterial` 数据包项。文件：`init/materials/LCMats.java`、`init/L2Complements.java:123-129`。适用场景：需要批量加材料/装备体系时，先把"材料参数"收敛成一个枚举/数据类。
4. **用 ItemStack tag 记录"当前选中模式"，网络包只传一个 boolean**：`DiggerHelper` 用 key `l2complements:selected_digger` 存 ResourceLocation，`rotateDigger(stack, reverse)` 在附魔集合里轮换；键盘侧只发 `RotateDiggerToServer(reverse)`。文件：`content/enchantment/digging/DiggerHelper.java`、`network/RotateDiggerToServer.java`。适用场景：工具多模式切换（连锁挖掘、范围破坏、镐/斧切换），避免为了同步模式而定义复杂包。
5. **优先用 MixinExtras 的 `@WrapOperation`/`@ModifyReturnValue` 而不是 `@Redirect`**：`@Redirect` 只能有一处生效、与其他 mod 冲突率高，而 `@WrapOperation` 可叠加且能 `op.call(...)` 保留原逻辑。本仓库 16 个 mixin 里大量使用（`ItemMixin` 改 `getBarWidth`/`getBarColor`、`LivingEntityMixin` 改 `dropExperience`、`MobMixin` 式的附魔等级加成）。文件：`mixin/ItemMixin.java`、`mixin/LivingEntityMixin.java`。适用场景：所有需要"在保留原版行为的前提下改一个参数/返回值"的 mixin。

（补充）**datagen 全自动化 + 自定义 ProviderType**：`L2Complements.gatherData` 挂 7 类 Provider，其中 `TagGen.EFF_TAGS`/`ENCH_TAGS` 是自己 `ProviderType.register` 出来的自定义 tag 类型；`LCSpriteSourceProvider` 自动生成贴图图集清单；`LCDatapackRegistriesGen` 用 `RegistrySetBuilder` 生成动态注册项。文件：`init/L2Complements.java:93-134`、`init/data/{TagGen,LCSpriteSourceProvider,LCDatapackRegistriesGen}.java`。适用场景：内容量大、需要保证 tag/lang/配方/注册项一致性的 mod。

## 8. 对外扩展点（作为家族前置的接入面）

1. **材料与装备体系**：其他 mod 只要 `implements IMatVanillaType`（来自 `l2damagetracker`）就能复用同款 `GenItemVanillaType` 生成流程；盔甲特性通过 `ArmorEffectConfig`（数据包）声明。
2. **附魔基类**：`content/enchantment/core/` 的 `SingleLevelEnchantment`/`UnobtainableEnchantment`/`CustomDescEnchantment`/`AttributeEnchantment` 都是 `public` 且不依赖本 mod 内部状态（除 `LCConfig` 查询），可直接继承。注意仓库是 `All rights reserved`，可读不可抄。
3. **`FeaturePredicate` / `EntityFeature`**：一个只依赖 `LivingEntity` 的谓词接口，四个现成实现，可被其他 mod 用作条件系统。
4. **配方兼容层**：`compat/ars/ArsRecipeBuilder`、`compat/forbidden/FaARecipe` 是"同一配方输出到多个 mod 配方类型"的模板。
5. **数据包配置**：`LCConfigGen` 产出的 `L2DamageTracker.ARMOR`（以及同家族 mod 的其他配置类型）可被整合包覆盖。
6. **附魔合成配方**：`EnchantmentRecipeBuilder` 是通用 `RecipeBuilder`，`TagGen.ENCH_TAGS`/`EFF_TAGS` 提供附魔与效果的公共标签。

最后提示：本 mod 与 `l2library`（Registrate 封装 / 序列化配方与配置 / 网络 / 持久任务调度 / 能力系统）高度耦合，`GeneralEventHandler.schedulePersistent`、`PacketHandlerWithConfig`、`ConfigDataProvider` 都来自那里。要复用这套写法，应先读 `l2library` 与 `l2damagetracker`。
