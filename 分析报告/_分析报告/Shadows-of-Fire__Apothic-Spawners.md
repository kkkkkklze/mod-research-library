# Shadows-of-Fire/Apothic-Spawners 源码分析报告

## 1. 基本信息

- Mod 名：Apothic Spawners（原 Apotheosis 的刷怪笼模块，已拆成独立 mod）；mod_id `apothic_spawners`；作者 Shadows_of_Fire；版本 2.0.1（git 分支 `26.1`，commit `a5401df4`）。
- 目标：MC **26.1.2** + NeoForge 26.1.2.84，Java **25**（`gradle.properties:7-15`）。注意这是较新的 MC/NeoForge 世代，代码里已是 `Identifier`、`ValueOutput/ValueInput`、`RecipeMap`、`RecipeDisplay` 等新 API。
- 构建：NeoForge ModDevGradle 2.0.141 + Mixin 0.8.7（annotationProcessor）+ `com.diffplug.eclipse.apt` + `me.modmuss50.mod-publish-plugin`（`build.gradle:1-7`）。
- 依赖：强依赖 Placebo `Placebo:26.1.2-10.0.0`（`build.gradle:110`），Placebo 是它的 API 来源（DeferredHelper / DataGenBuilder / PayloadHelper / TabFillingRegistry / LegacyRecipeProvider / Configuration）；JEI 29.5.0.26、Jade 26.0.9 为 localImplementation（可选软兼容）。
- 许可证：`build.gradle` 的 generateModMetadata 强制要求根目录 `LICENSE` 并把首行写进 mods.toml（`build.gradle:142-146`），但本次检出的工作区没有该文件，**具体协议未确认**。

## 2. 源码规模与包结构

- 32 个 `.java`，共 2900 行（小体量、高信息密度，适合通读）。
- 包（到第 3 层）：`stats/`(7)、`compat/`(6)、根包(5)、`block/`(4)、`mixin/`(3)、`data/`(3)、`modifiers/`(2)、`advancements/`(2)。
- 最大文件：`block/ApothSpawnerTile.java`(492)、`block/LyingLevel.java`(273)、`compat/SpawnerCategory.java`(202, JEI)、`ASEvents.java`(176)、`block/ApothSpawnerBlock.java`(166)、`modifiers/SpawnerModifier.java`(148)、`modifiers/StatModifier.java`(110)、`block/ApothSpawnerItem.java`(92)。

## 3. 入口与注册

主类 `src/main/java/dev/shadowsoffire/apothic_spawners/ApothicSpawners.java:32`，`@Mod(MODID)`，构造器只做三件事：`ASObjects.bootstrap(bus)`、`NeoForge.EVENT_BUS.register(new ASEvents())`、`bus.register(this)`。最关键的初始化在 `setup(FMLCommonSetupEvent)`（`:45-52`）：

```java
ObfuscationReflectionHelper.<BlockEntityType<?>, BlockEntityType.BlockEntitySupplier<?>>setPrivateValue(
    BlockEntityType.class, BlockEntityType.MOB_SPAWNER, ApothSpawnerTile::new, "factory");
ASConfig.load();
TabFillingRegistry.registerSimple(Items.SPAWNER, CreativeModeTabs.TOOLS_AND_UTILITIES);
PayloadHelper.registerPayload(new ConfigPayload.Provider());
```

即**直接接管原版刷怪笼的 BlockEntityType 工厂**，而不是新增方块。注册体系全部走 Placebo 的 `DeferredHelper`（`ASObjects.java:25-47`：`HELPER.recipe/recipeSerializer/enchantmentEffect/custom/componentPredicate`），自定义注册表在 `regs(NewRegistryEvent)` 里注册（`:55-57`）。AT 文件 `src/main/resources/META-INF/accesstransformer.cfg` 打开了 `SpawnerBlockEntity.spawner` 与 `BaseSpawner` 的 11 个字段 + `getOrCreateNextSpawnData`/`isNearPlayer`（含 `minSpawnDelay/nextSpawnData/spin/oSpin` 等），这是它改装原版逻辑的前提。

## 4. 核心系统

1. **可注册的"刷怪笼属性"注册表** `stats/`：`SpawnerStats.REGISTRY = new RegistryBuilder<SpawnerStat<?>>(REGISTRY_KEY).sync(true).create()`（`stats/SpawnerStats.java:14-16`），注册 16 个 stat（min_delay…echoing）。接口 `SpawnerStat<T>`（`stats/SpawnerStat.java:16`）定义 `valueCodec/valueStreamCodec/getValue/setValue/getTooltip/applyModifier`，并用 `getId().toLanguageKey("stat")` 自动生成 lang key。两条实现路线：`VanillaStat` 用 getter/setter 直接读写 BaseSpawner 字段（配 AT），`CustomStat` 把值存进 tile 的 `IdentityHashMap<SpawnerStat<?>, Object>`（`block/ApothSpawnerTile.java:66`）。
2. **声明式修改器（数据驱动）** `modifiers/`：`StatModifier<T>(stat, value, min, max, mode)` 用 **registry dispatch codec**，并按 stat 缓存动态生成的 MapCodec/StreamCodec（`StatModifier.java:29-33`、`createModifierCodec`；`Mode` 有 `ADD/SET`）。`SpawnerModifier` 是真正的 `Recipe`：`mainHand`/`offHand` 双 Ingredient + `consumes_offhand` + `stat_changes`，`isSpecial()=true`、`placementInfo=NOT_PLACEABLE`、`display()` 为空（`SpawnerModifier.java:100-123`）；匹配时"有副手的优先"排序（`:141-145`）。
3. **接管原版刷怪逻辑** `block/ApothSpawnerTile.SpawnerLogicExt extends BaseSpawner`（`:220-486`）：`serverTick` 里逐项消费 stat——`IGNORE_LIGHT` 时用 `LyingLevel` 从 0 到 15 逐个假光照试探 `checkSpawnRules`（`:338-352`）；`NO_AI` 给 mob 打 `apotheosis:movable` persistentData，再由 `ASEvents.tickDumbMobs` 在 `EntityTickEvent.Pre` 里临时解除 noAI 手动 `travel()` 位移（`ASEvents.java:120-129`），并取消其传送；"不稳定刷怪笼"倒计时 60 tick 后爆炸并按 `UNSTABLE_SPAWNER_LOOT` 掉落表弹射物品（`:61-63,167-218`）。持久化用新 `ValueOutput/ValueInput` API 把每个 stat 以 codec 编码为 NBT 子键，失败仅记日志（`:93-136`，容错写法值得学）。
4. **LyingLevel 假世界包装** `block/LyingLevel.java`：`implements ServerLevelAccessor`，包一个真 `ServerLevel` 只重写 `getMaxLocalRawBrightness/…` 加 `setFakeLightLevel(int)`，其余全部委托——用来"骗过"原版刷怪光照/条件检查，比复制一份逻辑干净得多。
5. **兼容层** `compat/`：JEI `SpawnerCategory`(+`SpawnerJEIPlugin`)、Jade `SpawnerHwylaPlugin`+`SpawnerServerDataProvider`（用 `TagValueOutput.createWithContext` 调 `saveCustomOnly` 把自定义 stats 塞进 Jade 的服务器数据，`SpawnerServerDataProvider.java:22-27`）、`SpawnerRecipeCache`（客户端从 `RecipesReceivedEvent.getRecipeMap()` 重建并按 id 倒序排序，`ASClient.java:17-22`）。
6. **成就/触发**：`advancements/ModifierTrigger` 自定义 `SimpleCriterionTrigger`，`TriggerInstance` 记录 min/max 各 stat 期望区间。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：不用原版 registrar，走 Placebo `PayloadProvider`；`ASConfig.ConfigPayload`（`ASConfig.java:44-95`）是 record，`StreamCodec.composite(ByteBufCodecs.VAR_INT,…)`，声明 `getSupportedProtocols()=PLAY`、`getFlow()=CLIENTBOUND`、`getVersion()="3"`（PayloadHelper 用 version 做兼容校验）；`OnDatapackSyncEvent` 时 `e.sendRecipes(SPAWNER_MODIFIER)` + 给每个玩家发 ConfigPayload（`ASEvents.java:144-150`）。
- 数据驱动：刷怪笼修改器 = datapack 配方（`data/apothic_spawners/recipe/spawner_modifiers/*.json`，含 `_inverse/*` 逆操作），可被数据包/其他 mod 覆盖；`SpawnerRecipeCache` 客户端镜像。
- 配置：Placebo `Configuration`，路径刻意放在 `config/apotheosis/apothic_spawners.cfg` 以便和 Apotheosis 同目录（`ASConfig.java:27-28`），注释里标注 "Synced." / "Server-authoritative." 表达同步语义；`ResourceReloadEvent` 时服务端重载配置。
- datagen：`GatherDataEvent.Client` + `DataGenBuilder.create(MODID).registry(ENCHANTMENT,…).provider(ASRecipeProvider/ASLootProvider)`（`ApothicSpawners.java:60-67`）；`data/ASRecipeProvider` 用 Placebo `LegacyRecipeProvider` 以 `intChange/floatChange/boolSet` 等 helper 批量生成修饰符 JSON。

## 6. Mixin

配置由 Gradle 生成：`src/templates/mixins.json` + `generateModMetadata` 任务**扫描 `src/main/java/.../mixin/` 目录自动填充 mixins/mixins(client) 列表**并改名 `<modid>.mixins.json`（`build.gradle:150-190`），输出到 `src/generated/resources/apothic_spawners.mixins.json`；`[[mixins]]` 段落也由 Gradle 拼进 mods.toml。三个 mixin 全部用 `remap = false` + mixinextras：
- `mixin/BlocksMixin.java`：`@ModifyArg` 注入 `Blocks.<clinit>` 中对 `Blocks.register(...)` 的调用，用 `@Slice(from CONSTANT stringValue=spawner, to stringValue=creaking_heart)` 定位 `index = 1` 参数，把 spawner 方块工厂换成 `ApothSpawnerBlock::new`。
- `mixin/ItemsMixin.java`：`@ModifyVariable` 注入 `Items.registerItem` 头部，把 `minecraft:spawner` 的物品工厂替换为 `ApothSpawnerItem`。
- `mixin/ItemStackMixin.java`：`@WrapOperation` 包 `ItemStack.is(...)`（`ordinal = 0`，targets 指向 neoForge 的 `VanillaDataComponentTooltips`），对自定义 spawner item 返回 false 以跳过原版刷怪笼 tooltip。

## 7. 值得学的 5 条

1. 想"改造原版方块"时用 AT 打开原版字段 + 反射替换 `BlockEntityType` 工厂 + mixin 替换方块/物品工厂，从而零新增方块 ID 地接管原版内容（`ApothicSpawners.java:47`、`mixin/BlocksMixin.java`）——适用于任何"重做原版机制"的 mod。
2. 把"可被数据包配置的机制"做成 `SpawnerStat` 注册表 + `StatModifier` dispatch codec + `SpawnerModifier` 配方三件套（`stats/SpawnerStats.java`、`modifiers/StatModifier.java:32-33`）——适用于给机器/刷怪/天气等系统做可扩展参数。
3. 每个实现类型缓存"按注册项动态生成"的 MapCodec/StreamCodec（`CODEC_CACHE`/`STREAM_CODEC_CACHE` + `computeIfAbsent`，`StatModifier.java:29-33,57-64`）——适用于泛型注册项的序列化。
4. 用 `implements ServerLevelAccessor` 的委托包装类伪造环境（光照）而不是复制逻辑（`block/LyingLevel.java`）——适用于绕过原版条件判断的任意场景。
5. 让 Gradle 从源目录生成 `mixins.json`/`mods.toml`（`build.gradle:132-190`），并把首次出现的信息（LICENSE 首行、依赖版本、平台依赖 slug）统一由 gradle.properties 驱动——适用于多分支/多版本维护的工程化 mod 模板。

## 8. 公开 API / 扩展点

本质是"模块化 mod"，公开扩展点集中在 `stats/SpawnerStat`（外部可注册新 spawner stat）+ `SpawnerStats.REGISTRY`（`sync(true)` 的自定义注册表）+ `SpawnerModifier` 配方的 JSON schema（`stat_changes` 数组，`mode: add|set`，可选 `min/max`）；JEI/Jade 集成通过 `compat/` 中的插件类注册（`SpawnerJEIPlugin`/`SpawnerHwylaPlugin`）。
