# AlexModGuy/AlexsMobs 源码分析

## 1. 基本信息
- Mod 名 **Alex's Mobs**；mod_id `alexsmobs`；作者 Alexthe668, Carro1001, Paint_Ninja；包名 `com.github.alexthe666.alexsmobs`。
- MC **1.20.1** + Forge（`build.gradle`: `net.neoforged:forge:1.20.1-47.1.65`；`mods.toml` 要求 `[47.1.0,)`，loaderVersion `[46,)`），Java 17；版本 1.22.9。
- Gradle：`net.neoforged.gradle` `[6.0.18,6.2)`（1.20.1 时代的 NeoGradle-for-Forge）+ `org.spongepowered.mixin` 0.7.+
- 许可证 **GNU LGPL**（mods.toml）。
- 编译依赖：**Citadel `[2.6.0,)`（mandatory, AFTER）** —— 唯一的硬前置，动画/模型/生物群系配置全部来自它；JEI 仅 compileOnly/runtimeOnly。依赖方向：AlexsMobs → Citadel。

## 2. 源码规模与包结构
- **745 个 .java / 124,195 行**。
- 主要包：`entity` 129、`client/model` 122、`client/render` 119、`entity/ai` 111、`item` 42、`client/render/layer` 33、`block` 27、`misc` 24、`effect` 20、`message` 19、`client/particle` 19、`client/model/layered` 13、`tileentity` 12、`entity/util` 10、`world` 8、`config` 5、`compat/jei` 3。
- 最大文件：`entity/EntityMimicOctopus.java` 1253、`EntityBaldEagle.java` 1231、`EntityCrow.java` 1134、`EntityLaviathan.java` 1092、`EntityElephant.java` 1069、`EntityKangaroo.java` 1057、`EntityTarantulaHawk.java` 1033、`EntityVoidWorm.java` 970。

## 3. 入口与注册
`AlexsMobs.java:51` `@Mod(AlexsMobs.MODID) @Mod.EventBusSubscriber`。构造函数 `:75-114` 逐行注册 **19 个 DeferredRegister**，全部封装在各自 `*Registry` 类里（`AMBlockRegistry.DEF_REG`、`AMEntityRegistry.DEF_REG`、`AMItemRegistry`、`AMTileEntityRegistry`、`AMPointOfInterestRegistry`、`AMFeatureRegistry`、`AMSoundRegistry`、`AMParticleRegistry`、`AMPaintingRegistry`、`AMEffectRegistry.EFFECT_DEF_REG/POTION_DEF_REG`、`AMEnchantmentRegistry`、`AMMenuRegistry`、`AMRecipeRegistry`、`AMLootRegistry`、`AMBannerRegistry`、`AMCreativeTabRegistry`），随后注册 3 个世界修饰器 codec：
```java
biomeModifiers.register("am_mob_spawns", AMMobSpawnBiomeModifier::makeCodec);       // AlexsMobs.java:101
biomeModifiers.register("am_leafcutter_ant_spawns", AMLeafcutterAntBiomeModifier::makeCodec);
structureModifiers.register("am_structure_spawns", AMMobSpawnStructureModifier::makeCodec);
```
网络通道同 Citadel 模式（`alexsmobs:main_channel`，静态块 :63-73）。`AMEntityRegistry.java:31` 用 `registerEntity(EntityType.Builder..., "name")` 包装，统一 spawn placement/属性注册。

## 4. 核心系统
1. **实体 + 自定义 AI 库**：`entity/` 129 个实体（含分段身体 Part 实体如 `EntityBoneSerpentPart`、`EntityCentipedeBody`），`entity/ai` **111 个自定义 Goal**（命名规范 `AnimalAIXxx` / `XxxAIBar`），`entity/util` 放可复用工具（`VineLassoUtil`、`SquidGrappleUtil`、`TendonWhipUtil`、`LaviathanNeckSolver`、`Maths`）—— 行为工具类与实体类分离，便于被多个 mob 复用。
2. **Citadel 动画/模型体系**：189 个文件 import `citadel`，其中 71 个实现 `IAnimatedEntity`（`AnimationHandler.INSTANCE.updateAnimations` 驱动），模型走 Citadel 的 `AdvancedEntityModel`/Tabula 容器。
3. **数据驱动自定义配方 Capsid**：`misc/CapsidRecipeManager.java:21` extends `SimpleJsonResourceReloadListener`（目录 `capsid_recipes`，Gson `CapsidRecipe.Deserializer`），配 `compat/jei/CapsidRecipeCategory` + `CapsidDrawable` 做 JEI 展示；另有 `RecipeBisonUpgrade`、`RecipeMimicreamRepair`、`TransmutationData`。
4. **生物群系/刷怪配置**：`config/BiomeConfig.java` + `DefaultBiomes.java` 用 Citadel 的 `SpawnBiomeConfig` 生成/读取 JSON；运行时通过 `AMMobSpawnBiomeModifier`/`AMLeafcutterAntBiomeModifier`/`AMMobSpawnStructureModifier`（`Codec.unit(...)` + `Phase.ADD` → `AMWorldRegistry.addBiomeSpawns`）注入 Forge BiomeModifier。
5. **网络**：`message/` 19 个包，覆盖多人交互细节（`MessageCrowMountPlayer`、`MessageMosquitoDismount`、`MessageKangarooInventorySync`、`MessageTarantulaHawkSting`、`MessageUpdateEagleControls`、`MessageMungusBiomeChange`、`MessageSyncEntityPos`）—— 玩家骑乘/附着类状态全部走 C2S+S2C 配对包。
6. **配置**：`config/AMConfig.java` 用**静态 int 字段**承载数百个刷怪权重（`grizzlyBearSpawnWeight` 等），`AlexsMobs.java:129-136` 在 `ModConfigEvent` 里 `AMConfig.bake(config)` 回填，读取侧零开销。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：Forge `SimpleChannel`，`sendMSGToAll`/`sendNonLocal` 同 Citadel；包类自带 `write/read` + `Handler.handle`。
- 数据驱动：`capsid_recipes` JSON（自定义 reload listener）、`AMLootRegistry` + 5 个 `GlobalLootModifier`（`AncientDartLootModifier`、`BananaLootModifier`、`BlossomLootModifier`、`PigshoesLootModifier`）、`AMAdvancementTrigger`（自定义 criterion）、村民交易（`EmeraldsForItemsTrade`/`ItemsForEmeraldsTrade`）。
- 配置：仅 COMMON，`alexsmobs.toml`（`AlexsMobs.java:106`）；另有 Citadel 生成的 `config/alexsmobs/*.json` 生物群系表。
- datagen：**无**（无 `GatherDataEvent`；`src` 仅 `src/main`，仓库 resources 只有 `META-INF/` 与 `assets/alexsmobs/book`，模型/贴图/配方 JSON 未入库）。

## 6. Mixin
**本仓库没有任何 mixin**：无 `mixin` 包、无 `mixins.json`；`build.gradle` 的 `mixin { add sourceSets.main, "citadel.refmap.json"; config 'citadel.mixins.json' }` 实际复用 Citadel 的 18 个 mixin。所有原版行为改动均以 Forge 事件 + Citadel API 完成，这是它能跨多个 MC 版本快速移植的原因。

## 7. 值得学的 5 条做法
1. **注册分类封装为 `XxxRegistry` 类，每个类自带 `DEF_REG`**：主类只写 19 行注册，新增内容不污染入口。`AlexsMobs.java:82-98`、`entity/AMEntityRegistry.java`。
2. **`registerEntity(...)` 统一包装 EntityType**：尺寸/追踪范围/属性/生成放置一处收口，减少每个 mob 的样板错误。`AMEntityRegistry.java:32`。
3. **行为工具类抽到 `entity/util`**：`VineLassoUtil`/`TendonWhipUtil`/`LaviathanNeckSolver` 等被实体与物品共用，比塞进实体类更易复用。
4. **`SimpleJsonResourceReloadListener` 做自定义数据表 + JEI 分类**：实现"数据包可改、JEI 可看"的低成本数据驱动。`misc/CapsidRecipeManager.java:21` + `compat/jei/CapsidRecipeCategory.java`。
5. **配置用静态字段 + `bake()` 回填**：配置文件是 toml，但代码里 `AMConfig.xxx` 直接当普通静态变量读，热重载由 `ModConfigEvent` 统一处理。`config/AMConfig.java`、`AlexsMobs.java:129`。
