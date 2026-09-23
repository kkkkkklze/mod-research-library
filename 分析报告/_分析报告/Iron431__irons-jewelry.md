# Iron431/Iron's Gems 'n Jewelry 源码分析

## 1. 基本信息

- Mod 名：Iron's Gems 'n Jewelry / mod_id：`irons_jewelry` / 作者：Iron431 / 版本 `1.21.1-2.0.2`
- 目标：**MC 1.21.1 + NeoForge 21.1.200（Java 21，Parchment 1.21 / 2024.07.28）**，与本项目目标一致
- Gradle 插件：`net.neoforged.gradle.userdev 7.0.170` + `java-library` + `maven-publish`（无 mod-publish-plugin，无 jarJar）
- 许可证：**All Rights Reserved**（`gradle.properties: mod_license`；仓库根无 LICENSE 文件）
- 编译依赖：**Curios 9.2.2**（required，饰品槽）、**`io.redspace:irons_lib`**（required）、`io.redspace:atlas_api`（compileOnly api + localRuntime，用于贴图图集）、`io.redspace:irons_spellbooks`（**compileOnly + classifier `api`** —— 只依赖法术的 API jar）、JEI、GeckoLib(localRuntime)
- 无 `apiJar` 任务（`artifacts.apiJar` 已被注释掉），但代码结构上 `core/` 已是完整对外 DSL

## 2. 源码规模与包结构

- `find . -name '*.java' | wc -l` = **119**；总行数 = **9337**（小而精，适合整体通读）
- 全部 119 个文件的完整清单已获取，包结构：`block/jewelcrafting_station`(4)、`client`(5)、`command`(3)、`compat`(1)+`compat/jei`(4)、`core`(3)、`core/actions`(9)、`core/bonuses`(10)、`core/data`(13)、`core/parameters`(6)、`datagen`(3)、`event`(5)、`item`(2)+`item/book`(6)、`loot`(6)、`mixin`(4)、`network`(1)+`network/packets`(5)、`registry`(17)、`utils`(6)
- 最大文件：`item/book/GuideBookScreen.java`(963，手写书 UI)、`command/GenerateSiteData.java`(717)、`datagen/JewelryDataRegistryGenerator.java`(712，内置数据全在这)、`block/jewelcrafting_station/JewelcraftingStationScreen.java`(446)、`core/data/JewelryData.java`(258)

## 3. 入口与注册

入口 `IronsJewelry.java:30` `@Mod(IronsJewelry.MODID)`，构造器 20 行内完成全部注册（15 个 `XxxRegistry.register(bus)`），并在 `AddReloadListenerEvent` 挂 `MaterialModifierDataHandler`：

```java
modEventBus.addListener(IronsJewelryRegistries::registerRegistries);        // NewRegistryEvent
modEventBus.addListener(IronsJewelryRegistries::registerDatapackRegistries); // DataPackRegistryEvent
ComponentRegistry.register(modEventBus); BonusTypeRegistry.register(modEventBus);
ParameterTypeRegistry.register(modEventBus); /* ... 共 15 个 ... */
modContainer.registerConfig(ModConfig.Type.SERVER, ServerConfig.SPEC);
```

**核心设计：`registry/IronsJewelryRegistries.java` 把 7 个注册表按"是否数据驱动"分成两类**——
- 自建 `Registry`（`NewRegistryEvent`，代码注册）：`PARAMETER_TYPE_REGISTRY`、`JEWELRY_TYPE_REGISTRY`、`BONUS_TYPE_REGISTRY`（`Registry<BonusType>`）、`ACTION_REGISTRY`（`Registry<MapCodec<? extends IAction>>`），全部带 `defaultKey(IronsJewelry.id("empty"))` —— **每个注册表都有保证存在的空对象**，彻底消灭 null 检查。
- 数据包 `Registry`（`DataPackRegistryEvent`，JSON 注册）：`pattern`、`material`、`part`。三个 `RegistryFixedCodec` 分别用于跨表引用。

## 4. 核心系统

**(1) 三层数据 DSL：BonusType × IBonusParameterType × IAction（最值得学）**
- `core/bonuses/BonusType.java`：抽象类，**只声明"触发时机"和"参数类型"**（`getParameterType()`、`getTooltipDescription()`），10 个实现 = `attribute_bonus / effect_on_hit_bonus / on_attack_bonus / on_projectile_hit_bonus / on_shield_block_bonus / on_take_damage_bonus / effect_immunity_bonus / piglin_neutral_bonus / trade_discount_bonus / empty`。
- `core/parameters/IBonusParameterType.java`：抽象"参数值域"，关键行是 `Codec<Map<IBonusParameterType<?>, Object>> BONUS_TO_INSTANCE_CODEC = Codec.dispatchedMap(PARAMETER_TYPE_REGISTRY.byNameCodec(), IBonusParameterType::codec)` —— **用 `dispatchedMap` 在一个 Map 里混装任意类型的参数**，这是整套系统能"一个 bonus 配任意参数"的枢纽。5 个实现：`empty / attribute / positive_effect / negative_effect / action`。
- `core/actions/IAction.java`：抽象"效果"，`CODEC = ACTION_REGISTRY.byNameCodec().dispatch(IAction::codec, Function.identity())`，9 个实现（`knockback / ignite / apply_effect / apply_damage / apply_freeze / heal / explode / create_items`），并自带 `handleAction(...)` 统一处理冷却（`CooldownHandler` + `PlayerData.isOnCooldown`）。
- 三者正交组合，所以 JSON 里可以写"攻击时（BonusType）→ 施加效果（ParameterType）→ 燃烧（Action）"而无需为新组合写代码。

**(2) 品质缩放 —— `core/data/QualityScalar.java`**
`record QualityScalar(double baseAmount, double qualityScalar, double min, Optional<Double> max)`，`sample(quality)` 返回 `base + (quality-1)*scalar` 并夹紧到 [min,max]；**符号感知的夹紧逻辑**（base<0 时反向夹紧，用于负收益如交易折扣）。Codec 是 `Codec.withAlternative(DIRECT_CODEC, CONSTANT_CODEC)` —— **JSON 里既可写 `{"base":5,"scalar":2}` 也可直接写 `5`**。

**(3) 饰品实例数据 —— `core/data/JewelryData.java`**
一个 DataComponent：`{pattern: Holder<PatternDefinition>, parts: Map<Holder<PartDefinition>, Holder<MaterialDefinition>>}`（`Codec` + `StreamCodec` 用 `ByteBufCodecs.holderRegistry(...)` 只传注册名）。构造时**预算并缓存** `valid`（pattern 的 partTemplate 与实际 parts 是否完全匹配）与 `bonuses`（`cacheBonuses()`），`getBonusFor()` 把三层品质乘起来：`pattern.qualityMultiplier * bonus.qualityMultiplier * parts[pattern.partForQuality].quality`。参数优先取 bonus 自身 override，否则回退到材料参数。

**(4) 图案定义 —— `core/data/PatternDefinition.java`**
`record(descriptionId, jewelryType, List<PartIngredient> partTemplate, Optional<Holder<PartDefinition>> partForQuality, boolean unlockedByDefault, double qualityMultiplier)`；`CODEC = CODEC_RAW.validate(PatternDefinition::validate)` —— **在 Codec 层做跨字段校验**（`partForQuality` 必须出现在 `parts` 列表中），错误直接进 `DataResult.error` 报给数据包作者。构造器里按 `PartIngredient::drawOrder` 排序，绘制顺序即数据顺序。

**(5) 材料参数覆盖 —— `core/MaterialModifierDataHandler.java`**
`SimpleJsonResourceReloadListener` 读取 `irons_jewelry/material_modifier/*.json`（`record Modifier(Holder<MaterialDefinition> targetMaterial, Map<IBonusParameterType<?>, Object> parameterOverrides)`），用 `ImmutableMultimap` 聚合，`getParametersWithOverrides()` 在材料自身 `bonusParameters` 之上叠加、`buildKeepingLast()`。**让整合包可以改材料效果而不动 datapack registry**。

**(6) 战利品注入 —— `loot/` 6 个类**
`LootInjectionHandler` 在 `OnDatapackSyncEvent` 里**扫描所有战利品表的物品，按"gearscore"（tag 映射：low=5 / medium=25 / high=50 / very_high=75，护甲与剑=25）评分**，把 gearscore ≥ 30 的表登记进 `TRACKED_LOOT_TABLES`（表 → 概率）。`InjectJewelryLootModifier`（GLM）在命中表里按概率注入 `modifiers/inject_jewelry` 表；另有 `AppendLootModifier`（并入指定表）、`ReplaceLootModifier`（按概率替换）。`GenerateJewelryLootFunction` 是 `LootItemFunction`，按 `HolderSet<PatternDefinition>` + `TagKey<MaterialDefinition> → HolderSet<MaterialDefinition>` 过滤随机生成成品首饰。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`network/PacketHandler.java`（单类，`@EventBusSubscriber`）——`event.registrar(MODID).versioned("1.0.0").optional()`，仅 5 个 payload：`SetJewelcraftingStationPattern`(toServer)、`ServerboundSetBookmarkPacket`(toServer)、`SyncJewelcraftingSlotStates`/`SyncPlayerDataPacket`/`OpenGuidebookScreenPacket`(toClient)。
- **数据驱动（本项目最能直接抄的结构）**：
  - 数据包注册表 `irons_jewelry:{pattern,material,part}`，代码内注册表 `irons_jewelry:{bonus_type,bonus_parameter_type,action,jewelry_type}`
  - 手写数据：`src/main/resources/data/` **71 个 JSON**（`loot_modifiers/{chest_loot,entity_drops}`、`loot_table/{blocks,chests/village,modifiers,trades}`、`recipe`、`structure/village/*`、`curios/{entities,slots}`、`tags`），另有 113 个 assets 文件
  - datagen 产出：`src/generated/resources/` **74 个**（其中 63 个 `data/irons_jewelry/irons_jewelry/{material,part,pattern}/*.json` + 9 个 `assets/.../models/item/*.json`），由 `datagen/JewelryDataRegistryGenerator.java`（712 行，用 `RegistrySetBuilder` + `BootstrapContext` 声明全部内置图案/材料/部件）与 `ItemModelDataGenerator` 生成
  - **注意**：本地 bulk 副本用 sparse-checkout（只检出 `**/*.java`/`*.gradle`/`*.properties`/`*.toml`/`*.md`），上述 JSON 不在工作树中，`git ls-files` 可见
- **配置**：仅 1 个 `ServerConfig.SPEC`（NeoForge ModConfig，如 `ENABLE_DYNAMIC_JEWELRY_LOOT`）
- **Datagen**：`datagen/DataGenerators.java`，client 生成 item model，server 生成 `DatapackBuiltinEntriesProvider`（自建注册表数据 + 物品模型）

## 6. Mixin

配置 `src/main/resources/irons_jewelry.mixins.json`，`package=io.redspace.ironsjewelry.mixin`，4 个 common、client 列表为空、`injectors.defaultRequire=1`。**注意 `"compatibilityLevel": "JAVA_17"`、`"refmap": "irons_spellbooks.refmap.json"`（复制自 ISS，refmap 名不匹配，实际无 client mixin 所以未暴露问题）**：

- `mixin/EntityMixin.java:13` `@Mixin(Entity.class)` → `@Inject(method="ignoreExplosion", at=@At("RETURN"), cancellable=true)`（`IgnorableExplosion` 配合，让自伤爆炸穿透判定）
- `mixin/VillagerMixin.java:17` `@Mixin(Villager.class)` → `updateSpecialPrices`(RETURN)（交易折扣 bonus）
- `mixin/WanderingTraderMixin.java:15` `@Mixin(WanderingTrader.class)` → `updateTrades`(RETURN)
- `mixin/LivingEntityAccessor.java:7`（`@Accessor`）

## 7. 值得学的 5 条具体做法

1. **三层正交 DSL（触发点 × 参数类型 × 效果）**：`BonusType` / `IBonusParameterType` / `IAction` 三个独立注册表，靠 `Codec.dispatchedMap` 组装，新增组合不需要新类。文件：`core/bonuses/BonusType.java`、`core/parameters/IBonusParameterType.java:17`、`core/actions/IAction.java:20`。适用：任何"事件 → 效果"的魔法/词缀/技能系统。
2. **每个自建 Registry 都设 `defaultKey("empty")`**：`RegistryBuilder<>(key).defaultKey(IronsJewelry.id("empty"))`，查询永不返回 null。`registry/IronsJewelryRegistries.java:24-27`。适用：所有自定义注册表。
3. **在 Codec 里做跨字段校验**：`CODEC_RAW.validate(PatternDefinition::validate)`，把 `partForQuality ∈ parts` 这类约束报成 `DataResult.error`。`core/data/PatternDefinition.java:38-51`。适用：数据包系统，越早报错越好。
4. **配置类 Codec 支持"简写 + 全写"**：`Codec.withAlternative(DIRECT_CODEC, CONSTANT_CODEC)`，`QualityScalar` 在 JSON 里既可写数字也可写对象。`core/data/QualityScalar.java:10-27`。适用：数值对象，降低数据包作者门槛。
5. **两段式品质乘法**：品质 = `pattern.qualityMultiplier × bonus.qualityMultiplier × 材料品质`，配合 `QualityScalar.sample()` 线性缩放 → 数据驱动出上百种成品数值差异，代码里只有一条公式。`core/data/JewelryData.java:174-176`。适用：随机生成的装备/道具。
6. **用 gearscore 自动决定注入哪些战利品表**：扫描现有表内物品的 tag 评分（`LOOT_HANDLER_*_GEARSCORE` tag + `ArmorItem/SwordItem` 兜底），≥30 才注入，`OnDatapackSyncEvent` 时重建。`loot/LootInjectionHandler.java`。适用：不想手写几十个 loot modifier JSON 的注入式掉落。
7. **只依赖其他 mod 的 api classifier**：`compileOnly "io.redspace:irons_spellbooks:...:api"`。`build.gradle:107`。适用：与其他 mod 的软兼容。

## 8. 公开 API / 扩展点

无独立 API 包/API jar，但依赖方向清晰，外部可扩展点集中在 `registry/` + `core/`：`IronsJewelryRegistries`（4 个自建注册表 + 3 个数据包注册表 key + `Codecs`）、`BonusType`、`IBonusParameterType`、`IAction`、`JewelryType`、`PatternDefinition`/`MaterialDefinition`/`PartDefinition`（数据包对象）、`ComponentRegistry.JEWELRY_COMPONENT`（饰品 DataComponent）、`JewelryModTags`（gearscore tag）、`compat/CompatHandler`、`core/ICooldownHandler`（`ISSCooldownHandler` 接 ISS 冷却）、`compat/jei/*`。

> 未确认：`io.redspace:irons_lib` 提供的具体内容（仅见 `datagen/JewelryDataRegistryGenerator.java:26` 导入 `io.redspace.ironslib.registry.IronsLibRegistries`）；仓库为 sparse-checkout 检出，assets/data JSON 文本未核对。
