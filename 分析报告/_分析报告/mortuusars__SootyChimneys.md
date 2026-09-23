# mortuusars/SootyChimneys 源码分析报告

## 1. 基本信息
- Mod 名：Sooty Chimneys；mod_id：`sootychimneys`；作者：mortuusars；版本 1.3.5；许可证 MIT（`gradle.properties`）。
- 目标：MC 1.21.1（`minecraft_version_range=[1.21,)`），双加载器 NeoForge 21.1.129（`neoforge_version_range=[21,)`）+ Fabric Loader 0.16.9 / Fabric API 0.102.1；Java 21（mixin `compatibilityLevel: JAVA_21`）。
- Gradle 插件：`dev.architectury.loom 1.7-SNAPSHOT` + `architectury-plugin 3.4-SNAPSHOT` + shadow 8.1.1（`build.gradle`），三模块 `common`/`fabric`/`neoforge`，common 用 `transformProduction*` 打包进各平台 jar。
- 依赖：**Create 6.0.3-47 + Ponder 1.0.45 + Flywheel 1.0.1 + Registrate（仅 neoforge 模块，integration 用）**；`fuzs.forgeconfigapiport`（NeoForge 风格 config 移植到 Fabric）；JEI 19.19 compileOnlyApi；Parchment 映射。

## 2. 源码规模与包结构
实测 44 个 `.java`，2791 行。包（`common/src/main/java/io/github/mortuusars/sootychimneys/`）：`block/` 2、`data/` 5（+`data/smoke/` 3、`data/wind/` 5）、`recipe/` 2（+`recipe/result/` 1）、`integration/create/` 2、`integration/jei/` 8、`utils/` 1、根 4 个（`SootyChimneys`/`Register`/`Config`/`PlatformSpecific`）；`fabric/` 4、`neoforge/` 6。
最大文件：`block/ChimneyBlock.java` 346、`SootyChimneys.java` 328、JEI 的 `SootScrapingRecipeCategory` 134、`Register.java` 119。
注：仓库未提交 `assets/`、`data/`，三个 resources 目录只有 accesswidener + 3 个 mixins.json（模型/贴图不在版本库内，未确认原因）。

## 3. 入口与注册
`SootyChimneys.init()`（`SootyChimneys.java:32`）只按顺序调用嵌套静态类 `Blocks/BlockEntityTypes/Items/DataComponents/MenuTypes/RecipeTypes/RecipeSerializers/CriteriaTriggers/SoundEvents/...` 的 `init()`，用静态字段初始化触发注册（"字段即注册"）。
跨平台注册统一走 `common/.../Register.java` 的 `@ExpectPlatform`（`dev.architectury.injectables.annotations.ExpectPlatform`）静态方法（`block/item/blockEntityType/menuType/recipeType/recipeSerializer/particleType/dataComponentType/worldGenFeature` 等 13 个），平台实现在 `fabric/.../fabric/RegisterImpl.java`（直接 `Registry.register(BuiltInRegistries.X, ...)`）与 `neoforge/.../neoforge/RegisterImpl.java`（`DeferredRegister`，在 `SootyChimneysNeoForge` 构造器里逐个 `RegisterImpl.BLOCKS.register(modEventBus)`，`neoforge/.../SootyChimneysNeoForge.java:36-48`）。
平台专属逻辑用同类模式：`PlatformSpecific.canBeUsedToScrapeSoot(ItemStack)` → Fabric 判 `soot_scrapers` 标签，NeoForge 判 `ItemAbilities.AXE_SCRAPE`。

## 4. 核心系统
1. **烟囱方块状态机** `block/ChimneyBlock.java`：3 个 blockstate `LIT`/`BLOCKED`/`STACKED`（`BooleanProperty.create("blocked"/"stacked")`）；`updateState()` 在 `onPlace`/`neighborChanged` 时计算"上方是否为烟囱（STACKED）""下方是否未点亮（`isDisabledChimneyBelow`）"，并用 `Chimney.getCleanBlock()` 把堆叠后被压在下面的脏烟囱自动变干净。
2. **干净/脏双向映射** `data/Chimney.java`：`BiMap<ChimneyBlock, ChimneyBlock> CHIMNEY_STATES_MAP`（Guava `HashBiMap`）+ `getCleanBlock/getDirtyBlock`（inverse），避免为 7 种材质 14 个方块写 switch。随机刻脏化：`ChimneyBlock.randomTick()` 概率 `Config.Common.DIRTY_CHANCE`。
3. **刮灰交互 + 数据驱动配方** `ChimneyBlock.useItemOn()` → 校验 `PlatformSpecific.canBeUsedToScrapeSoot` → `level.getRecipeManager().getRecipeFor(SOOT_SCRAPING, ...)` → 逐个 `ChanceResult.rollOutput(random)` 掉落；`recipe/SootScrapingRecipe.java` 是 `isSpecial()=true` 的 `Recipe<SingleRecipeInput>`，`Serializer` 提供 `MapCodec`（`Ingredient.CODEC` + `ChanceResult.CODEC.listOf(0,3)` 带 size 校验）与 `StreamCodec.composite`（`Ingredient.CONTENTS_STREAM_CODEC` + `ByteBufCodecs.list`）。
4. **风系统（跨模组视觉效果）** `data/wind/Wind.java`：单例 `WindData`，每 `LevelTickEvent.Post` 由 `Config.Common.WIND_ENABLED` 控制 `Wind.update(level)`（`neoforge/event/ClientEvents.java`）；风向由时间/天气/天数推导 `WindState{CALM,BREEZE,WINDY,STORMY}`，再用 `Mth.lerp(0.1f, ...)` 平滑逼近目标强度。`data/smoke/SmokeProperties.java` 按 `ChimneyType` 提供 `particleOrigin/intensity/speed/particleSpread`。
5. **Create 兼容（可选依赖）** `neoforge/.../integration/create/CreateIntegration.java`：`MovementBehaviour.REGISTRY.register(block, behaviour)` + `MovingInteractionBehaviour.REGISTRY.register(...)`（Create 6 的注册表 API，逐块 register），触发点 `CommonEvents.onEnqueueIMC` 里 `ModList.get().isLoaded("create")`（`InterModEnqueueEvent` + `enqueueWork`）。common 模块同名类已被整体注释（Create 5 API 遗留），说明其迁移路径。
6. **JEI 插件** `integration/jei/SootyChimneysJeiPlugin.java` + 两个 category（`SootScrapingRecipeCategory`/`SootCoveringRecipeCategory`），自绘 `ChimneySmokeAnimatedDrawable`、`ScalableItemStackRenderer`，开关走客户端配置。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无自定义包（无 `network/` 包；烟囱粒子为客户端 tick 生成）。配方同步走原版 `RecipeSerializer.streamCodec()`。
- 配置：`Config.java` 用 **NeoForge `ModConfigSpec`** 写在 common 模块，两端分别注册——NeoForge 用 `container.registerConfig(ModConfig.Type.COMMON/CLIENT, SPEC)`，Fabric 用 `NeoForgeConfigRegistry.INSTANCE.register(...)`（forgeconfigapiport）。这样一份配置类同时服务两平台，是本仓库最值得复用的点。
- 数据驱动：`data/` 只有代码常量（`ChimneyTypes`/`ChimneyShape`），无 reload listener、无 datagen（无 `generators`/`datagen` 包）。
- 统计：`SootyChimneys.Stats`（自定义 `CUSTOM_STAT` + `StatFormatter`），NeoForge 在构造器用 `RegisterImpl.CUSTOM_STATS.register`，Fabric 里 `stats.register()` 直接注册 + `FMLCommonSetupEvent` 里 `Stats.CUSTOM.get` 让条目出现在统计界面。

## 6. Mixin
配置：`common/src/main/resources/sootychimneys.mixins.json`（无 client 段，公共段 1 个；`defaultRequire: 1`）、`sootychimneys.neoforge.mixins.json`、`sootychimneys.fabric.mixins.json`，前两者在 `neoforge.mods.toml` 的 `[[mixins]]` 里登记。accesswidener：`common/src/main/resources/sootychimneys.accesswidener`。
唯一 mixin：`mixin/CampfireParticleMixin` → `@Mixin(CampfireBlock.class)`，`@Inject(method="makeParticles", at=@At("HEAD"), cancellable=true)`：整体复刻原版粒子生成逻辑但把速度替换为 `wind.getAdjustedStrength()` 实现"原版营火烟也被风吹"，受 `WIND_ENABLED`/`WIND_AFFECTS_CAMPFIRE` 两个配置开关控制，未启用时直接 return 不 cancel。

## 7. 值得学的 5 条具体做法
1. **一份 `ModConfigSpec` 双平台**：common 写 `Config.java`，Fabric 侧用 forgeconfigapiport 的 `NeoForgeConfigRegistry.INSTANCE.register`（`fabric/SootyChimneysFabric.java:22`）——NeoForge 1.21.1 + Fabric 双端 mod 的省事配置方案。
2. **`@ExpectPlatform` 集中式注册门面**：`Register.java` 一个类包住 13 种注册类型，common 代码调用点零平台分支，新增类型只加一个静态方法 + 两个 Impl（`common/.../Register.java`、`fabric/.../RegisterImpl.java`、`neoforge/.../RegisterImpl.java:1`）。
3. **干净/脏双变体用 `HashBiMap` 反查**（`data/Chimney.java:16`）：适合"材质变体 × 状态变体"的方块族，避免为每个变体写映射方法。
4. **`ChanceResult` 双形态 Codec**：`Codec.either(ItemStack.CODEC, CHANCE_RESULT_ONLY_CODEC).xmap(...)`，JSON 里既可写裸物品（概率 1）也可写 `{item, chance}` 对象，写入时按 `chance>=1` 自动简写（`recipe/result/ChanceResult.java:26`）——掉落/概率产出的通用写法。
5. **Mixin 版"复制原版方法体 + 替换物理参数"**：`CampfireParticleMixin` 在 HEAD 完全实现并 `ci.cancel()`，比多处 `@Redirect` 更易读、也便于加配置短路（`mixin/CampfireParticleMixin.java:31`）。
