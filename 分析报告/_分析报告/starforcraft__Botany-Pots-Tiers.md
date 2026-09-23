# starforcraft/Botany-Pots-Tiers 源码分析报告

## 1. 基本信息
BotanyPotsTiers / `botanypotstiers` / Ultramega / 7.0.11 / LGPL v2.1 / group `com.ultramega.botanypotstiers` / Java 21。MC 1.21.1，NeoForge 21.1.209 + Fabric 0.116.6，多加载器三模块 `common/neoforge/fabric`（`settings.gradle:47-50` 仍 include('forge')，但无 forge 目录）。插件：fabric-loom 1.11、moddev 2.0.112、curseforgegradle、minotaur；子模块用的 `multiloader-*` 约定插件不在仓库内（`git ls-files | grep -i buildsrc` 为空，来源未确认）。依赖（`common/build.gradle:14-27`）：`botanypots 21.1.41`（被扩展 API）、`bookshelf 21.1.75`（注册/加载条件）、`prickle 21.1.4`（配置），JEI 19.21.1.304 仅 compileOnly。仓库为 sparse-checkout，JSON 未落地，需 `git show HEAD:<path>` 查看。

## 2. 规模与包结构
`.java` 15 个 / 1296 行；tracked 3732 个文件（资源 3703）。包（`common/.../common/impl/`）：根（BotanyPotsTiersMod、BotanyPotsTiersContent、PotTier）、`block`、`block/entity`、`block/menu`、`config`、`data`、`data/conditions`、`item`；加载器侧各 1 文件。最大：`TieredBotanyPotFileGenerator.java` 410（生成器）、`TieredBotanyPotMenu.java` 197、`BotanyPotsTiersContent.java` 169。资源：recipe 1467、loot_table 549、blockstates 549、models 1103、tags 16、lang 9。

## 3. 入口与注册
NeoForge `neoforge/.../impl/NeoForgeMod.java:14-30`：`@Mod` 构造器调 `BotanyPotsTiersMod.init()` 并挂 `RegisterCapabilitiesEvent`，仅 `Direction.DOWN` 面返回 `SidedInvWrapper`。Fabric `FabricMod.java:6-11` 同样只调 `init()`。无 DeferredRegister：走 **Bookshelf ContentProvider SPI**（`common/src/main/resources/META-INF/services/net.darkhax.bookshelf.common.api.registry.ContentProvider`），实现 `defineBlocks/defineItems/defineBlockEntities/defineCreativeTabs/defineBlockRenderers/defineBlockRenderTypes/defineLoadConditions/namespace`，全部由枚举循环展开（`BotanyPotsTiersContent.java:71-98`：3 tier × DyeColor × 3 类锅 = 549 块）。

## 4. 核心系统
1. **PotTier 唯一真源**（`PotTier.java:20-34`）：ELITE/ULTRA/MEGA，`getSpeedMultiplier/getOutputMultiplier` 直读 `BotanyPotsTiersMod.CONFIG.get().gameplay.*`，`getPrevious/getNext` 供升级判定。
2. **继承而非改 botanypots**：`TieredBotanyPotBlock extends BotanyPotBlock`，只覆写 `getGrowthModifier/getYieldModifier`（`:42-50`）、`newBlockEntity`、`getTicker`；BE 类型反查用 `CachedSupplier.of(BuiltInRegistries.BLOCK_ENTITY_TYPE, id(tier+"_botany_pot")).cast()`（`TieredBotanyPotBlockEntity.java:26-28`）。
3. **升级物品换块搬运数据**（`UpgradeItem.java:31-91`）：由旧块注册名 `replaceFirst(旧tier+"_","")` 推目标 id；`saveWithFullMetadata` → **清空 Container 防复制** → `setBlock(UPDATE_ALL)` → `loadWithComponents`。
4. **配置开关配方**：`data/conditions/ConfigLoadCondition.java`（record + `RecordCodecBuilder`，`TYPE_ID=botanypotstiers:config`，property→Supplier<Boolean> map），配合 recipe JSON 的 `"bookshelf:load_conditions"` 生效（如 `data/botanypotstiers/recipe/pots/elite_terracotta_botany_pot.json` 用 `pattern ["MAM","MPM","BMB"]`，`P` 引 tag `botanypotstiers:regular_botany_pots`）。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络：无。数据驱动：recipe/loot/blockstate/model/tag 均为提交进仓库的生成产物。配置：Prickle（`config/{Config,Gameplay,Recipes}.java`），`@Value(comment=...)`，`CachedSupplier.cache(() -> ConfigManager.load(...))` 懒加载并在 `init()` 强制求值先写文件（`BotanyPotsTiersMod.java:15,22`）。datagen：无 DataGenerator，改用 Java 写文件生成器 `TieredBotanyPotFileGenerator`（410 行模板 + `$tier/$material_id` 占位符，入口 `BotanyPotsTiersContent.generatePotFiles()` 已被注释，属离线工具）。

## 6. Mixin
无（无 `*.mixins.json`；mixin 依赖仅 compileOnly）。

## 7. 值得学的 5 条
1. 一个枚举承载注册+数值+配方+本地化键：`PotTier.java` / `BotanyPotsTiersContent.java`。
2. 用第三方 SPI 免写加载器适配：`META-INF/services/...ContentProvider` + `defineXxx` 回调，common 一份代码通吃双加载器。
3. 配方可用性交给数据包加载条件（自定义 condition + `bookshelf:load_conditions`），服主可配置开关。
4. 1467 个同构 JSON 用一次性生成器产出后提交：`TieredBotanyPotFileGenerator.java`。
5. 换块升级先清容器再写数据：`UpgradeItem.java:64-87`，避免掉落/复制。
