# Shadows-of-Fire/Apothic-Enchanting 源码分析

## 1. 基本信息

Apothic Enchanting / `apothic_enchanting`；作者 Shadows_of_Fire；版本 2.0.0；目标 **MC 26.1.2 + NeoForge `26.1.2.64-beta`**、Java 25（`gradle.properties`：`mcVersion`、`javaVersion`、`forgeVersion`）；单平台 NeoForge，`mixin=true`（`mixinVersion 0.8.7`）。Gradle：`net.neoforged.moddev 2.0.141`、`com.diffplug.eclipse.apt 3.42.2`、`me.modmuss50.mod-publish-plugin 2.0.0`；额外子项目 `coremods`（`java-library`，只依赖 fancymodloader `loader:11.0.5` + `asm/asm-tree 9.8`）。许可证从 `LICENSE` 首行注入 `generateModMetadata`（文件内容未确认）。依赖：**Placebo `10.0.0` 与 Apothic Attributes `3.0.0`（implementation，即它的 API/前置）**、Curios `15.0.0-beta.2+26.1.2`、Patchouli；JEI `29.5.0.26` / Jade `26.0.9` 为 localImplementation。发布依赖清单 `requiredDeps=placebo, apothic-attributes`。

## 2. 规模与包结构

实测 `src` + `coremods` 共 **102 个 `.java` / 10951 行**（`wc -l` 总计）。主包 `dev.shadowsoffire.apothic_enchanting`，按目录文件数：`table/` 18（含 `infusion/` 3）、`objects/` 14、`mixin/` 14 + `mixin/client/` 4、`data/` 10、根 7、`compat/` 5、`library/` 4、`payloads/` 3、`enchantments/`(+components/values/entity_effects) 5、`util/` 2、`api/` 2、`asm/` 1、`command/` 1、`advancements/` 1；`coremods/.../coremods/` 5 个 ASM 处理器。最大文件：`Ench.java` **605**、`data/ApothEnchantmentProvider.java` 425、`table/EnchantingInfoScreen.java` 415、`table/ApothEnchantmentScreen.java` 404、`ApothEnchEvents.java` 394、`data/EnchRecipeProvider.java` 331、`library/EnchLibraryTile.java` 319、`ApothicEnchanting.java` 311、`table/ApothEnchantmentMenu.java` 301。

## 3. 入口与注册

`ApothicEnchanting.java:87` `@Mod(MODID)`，构造器仅 `Ench.bootstrap(bus); bus.register(this);`。注册全部集中在 `Ench.java`，用 **Placebo 的 `DeferredHelper`**（`Ench.java:92` `private static final DeferredHelper R = DeferredHelper.create(MODID)`）按域拆成静态内部类 `Sounds/Attributes/Blocks/Items/EnchantEffects/Tabs/Tiles/Particles/DataMaps`，每类一个空 `bootstrap()`，由 `Ench.bootstrap(bus)`（文件末）统一调用。写法样例：

```java
public static final Holder<Block> APOTHIC_ENCHANTING_TABLE = R.block("apothic_enchanting_table", ...);   // Ench.java:135
public static final DataComponentType<BerserkingComponent> BERSERKING =
    R.enchantmentEffect("berserking", b -> b.persistent(BerserkingComponent.CODEC));                      // Ench.java:271
```

自定义注册表项走 `R.custom("warden_tendril", NeoForgeRegistries.Keys.GLOBAL_LOOT_MODIFIER_SERIALIZERS, WardenLootModifier.CODEC)`（`Ench.java:95` 附近）。主类事件：`FMLCommonSetupEvent`(init:107) 建附属数据/注册 Payload 与附属属性、`ModifyDefaultComponentsEvent` 改 `DataComponents.ENCHANTABLE`、`RegisterCapabilitiesEvent` 注册图书架/附魔台 `Capabilities.Item.BLOCK`、`BlockEntityTypeAddBlocksEvent` 把两个新附魔台挂到原版 `BlockEntityType.ENCHANTING_TABLE`、`GatherDataEvent.Client` 做 datagen。

## 4. 核心系统

- **数据映射驱动的词条数值（配置→数据迁移范例）**：`Ench.DataMaps.ENCHANTMENT_INFO = R.dataMap("enchantment_info", Registries.ENCHANTMENT, EnchantmentInfo.CODEC.codec(), c -> c.synced(EnchantmentInfo.CODEC.codec(), true))`（`Ench.java` DataMaps 区）。读取入口 `ApothicEnchanting.getEnchInfo(Holder)`（`ApothicEnchanting.java:224`）用 `ref.getData(...)`，缺失则 `EnchantmentInfo.fallback(holder)`；旧配置文件被写成 tombstone 说明文本（`MIGRATED_CONFIG_NOTICE`，`:90`，`writeMigratedConfigNotice`），并提示用 `/apoth dump_enchantment_info` 导出。
- **Coremod / ASM 重定向**（`coremods/`）：`ApothEnchCoreMod implements ClassProcessorProvider`（NeoForge `ClassProcessorProvider` SPI，26.1 起取代 JS coremod），注册 `EnchInfoRedirector`、`EnchInfoLootRedirector`、`FishingHookLureTransformer`；被注入代码回主 jar 的 `asm/EnchHooks.getMaxLevel / getMaxLootLevel / getTicksCaughtDelay`（`asm/EnchHooks.java:22/34/44`），把 `Enchantment#getMaxLevel()` 调用点改写为 datamap 查询。子项目 manifest 标 `FMLModType: LIBRARY` 并以 `jarJar(project(':coremods'))` 打进主 jar。
- **附魔台数值体系**：`table/EnchantingStatRegistry.java:28` 继承 Placebo `DynamicRegistry<BlockStats>`，`INSTANCE`(:31) 单例 + `buildStatsCache()`(:52) 脏标记缓存，把 `BlockState` 映射为 `Stats(maxEterna, eterna, quanta, arcana, clues)`（`:134`）；由 `Ench.Tiles`/数据文件驱动，`ApothEnchantmentMenu`、`ApothEnchantmentHelper` 消费。
- **书架库（Library）**：`library/EnchLibraryTile.java:42`，字段 `Object2IntMap<Holder<Enchantment>> points / maxLevels`(:46-47) 存"点数/上限"，`levelToPoints(level) = 2^(level-1)`(:130)，`depositBook`(:66) / `extractEnchant`(:97) / `canExtract`(:120)；`Set<EnchLibraryContainer> activeContainers`(:48) 让打开中的界面在数据变动时刷新，另有 `getUpdateTag/getUpdatePacket`(:172/:180) 同步客户端。
- **网络**：3 个 payload（`payloads/CluePayload`、`StatsPayload`、`SetRavenStatsPayload`），经 `ApothicEnchanting.java:137-139` `PayloadHelper.registerPayload(new X.Provider())`（Placebo 网络封装）注册；`StatsPayload` 是 `record` + `StreamCodec` + `handleClient` + `getFlow()=CLIENTBOUND`、`getSupportedProtocols()=PLAY`（`payloads/StatsPayload.java`）。Raven 台玩家设定值用 NeoForge **AttachmentType**（`table/RavenTableStats.java:26`）持久化。
- **datagen**：`ApothicEnchanting.java:172-186` `DataGenBuilder.create(MODID, "minecraft").registry(Registries.ENCHANTMENT, ...).registry(Registries.DAMAGE_TYPE, ...).registry(Registries.JUKEBOX_SONG, ...).provider(LootProvider/EnchTagsProvider/EnchItemTagsProvider/EnchDamageTypeTagsProvider/EnchRecipeProvider/EnchStatsProvider/ApothEnchDataMapProvider).build(event)`；自定义附魔由 `data/ApothEnchantmentProvider.java`（425 行）生成。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络：Placebo `PayloadProvider`/`PayloadHelper` + `CustomPacketPayload` + `StreamCodec`，仅 3 个包（Clue/Stats/SetRavenStats），单向 CLIENTBOUND 同步为主。数据驱动：enchantment datamap（上文）+ 附魔/伤害类型/唱片注册表 datagen + `EnchantingStatRegistry` 方块→数值表。配置：`ApothEnchConfig.load(new Configuration(ApothicAttributes.getConfigFile(MODID)))`（`ApothicEnchanting.java:194` 附近），并在 `ResourceReloadEvent` 重载。datagen：见 4 末条，入口 `GatherDataEvent.Client`，输出目录 `src/generated/resources/`，`src/templates/` 存未展开模板。

## 6. Mixin

配置：`src/generated/resources/apothic_enchanting.mixins.json`——**由 Gradle 自动生成**（`build.gradle` `generateModMetadata` 任务扫描 `src/main/java/dev/shadowsoffire/apothic_enchanting/mixin` 下所有类，按是否以 `client` 开头分入 `mixins`/`client` 数组，并顺便 `expand` 模板 `neoforge.mods.toml`）；`compatibilityLevel: JAVA_25`、`maxShiftBy: 0`。14 个服务端 mixin：`EnchantmentMixin`、`AnvilMenuMixin`、`EnchantingTableBlockEntityMixin`、`ItemStackMixin`、`BlocksMixin`/`BlockMixin`、`CandleBlockMixin`、`CrossbowItemMixin`、`SpellCrossbowMixin`、`TridentItemMixin`/`ThrownTridentMixin`、`TemptGoalMixin`、`IShearableMixin`、`GoldToolsHaveFortuneModuleMixin`；4 个客户端：`client.EnchantmentScreenMixin`、`client.AnvilScreenMixin`、`client.EnchantTableRendererMixin`、`client.EnchantTableRenderStateMixin`（具体注入点/方法名本次未逐文件阅读，未确认）。

## 7. 值得学的 5 条具体做法

1. 单一注册总线 + 域内部分类：`Ench.java:92` 一个 `DeferredHelper`，`Blocks/Items/EnchantEffects/Tabs/Tiles/DataMaps` 各为静态内部类且只暴露 `Holder<T>`，注册时序由 `bootstrap()` 集中控制。文件路径 `src/main/java/dev/shadowsoffire/apothic_enchanting/Ench.java`。
2. 配置迁到 datamap 并留可读墓碑：`ApothicEnchanting.java:90`（`MIGRATED_CONFIG_NOTICE` + `writeMigratedConfigNotice`），配合 `/apoth dump_enchantment_info` 导出，避免老配置"看似生效实则失效"。
3. 昂贵计算用弱键 Map 记忆化：`private static final ConcurrentMap<Holder<Enchantment>, Integer> DEFAULT_MAX_LEVEL_CACHE = new MapMaker().weakKeys().makeMap();`（`ApothicEnchanting.java:237`），数据包重载后旧 Holder 可被 GC。
4. coremod 与主 jar 严格分层：`coremods/` 子项目零 MC 依赖（只 compileOnly fancymodloader SPI + asm-tree），注入的 `INVOKESTATIC` 指向主 jar 的 `asm/EnchHooks`，靠运行期类加载器解析；manifest `FMLModType: LIBRARY` + `jarJar` 打包（`coremods/build.gradle`）。
5. Gradle 侧自动生成 mixins.json 与 mods.toml：`build.gradle` 的 `generateModMetadata` 任务扫描 mixin 包生成两个数组、并把 `src/templates/neoforge.mods.toml` 按 `gradle.properties` 展开，新增 mixin 无需手改配置。

## 8. 公开 API / 扩展点

存在少量对外接口包 `dev.shadowsoffire.apothic_enchanting/api/`：`EnchantableItem.java`、`EnchantmentStatBlock.java`（供方块/物品声明附魔属性）；真正的扩展面在 Placebo（`DeferredHelper`、`DynamicRegistry`、`PayloadProvider`、`ResourceReloadEvent`、`ITabFiller`/`TabFillingRegistry`、`DataGenBuilder`）与 Apothic Attributes（`getConfigFile`、属性注册），外部 mod 通过它们接入（未确认是否有文档化的第三方 API 清单）。
