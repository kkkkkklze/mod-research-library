# starfish-studios/Naturalist 源码分析报告

## 1. 基本信息

- Mod 名 Naturalist / `mod_id=naturalist` / 作者 Starfish Studios / 版本 1.0.2 / 许可证 MIT（`gradle.properties`）
- 目标 MC 1.21.1、仅 NeoForge 21.1.226（`neoforge_version_range=[1.21.1]`），Java 21 toolchain；构建用 `net.neoforged.moddev` 2.0.105 + `me.modmuss50.mod-publish-plugin`（`build.gradle:1-12`）
- 依赖：`implementation geckolib-neoforge-1.21.1:4.7.3`（**GeckoLib 是其动画/模型 API**，必装）、`compileOnly + localRuntime lambdynamiclights`（可选光照兼容）、maven 里还有 modrinth/blamejared/forge（JEI 等）
- 无 fabric 模块（单平台仓库）

## 2. 源码规模与包结构

- 155 个 `.java` / 16,536 行（`find src -name '*.java' -exec wc -l {} +`）
- 主要包：`server/entity/mob`(24)、`client/renderer`(24)、`client/model`(24)、`server/entity/ai/goal`(17)、`datagen`(11)、`mixin`(9)、`registry`(8)、`server/item`(7)、`server/entity/base`(7)、`server/block`(6)、`client/renderer/layers`(5)
- 最大文件：`server/entity/mob/Bear.java` 853、`Lion.java` 516、`Rhino.java` 509、`Butterfly.java` 485、`Snake.java` 475、`Snail.java` 440、`Bird.java` 440、`Vulture.java` 417、`Giraffe.java` 410、`Tortoise.java` 404；`datagen/NaturalistLanguageProvider.java` 331

## 3. 入口与注册

主类 `src/main/java/com/starfish_studios/naturalist/Naturalist.java`，`@Mod(Naturalist.MOD_ID)` 构造器里集中做四件事（第 64-93 行）：注册 `NaturalistConfig.COMMON_CONFIG_SPEC`（`naturalist-server.toml`）、挂 mod/NeoForge 总线监听、客户端扩展点 `IConfigScreenFactory`、把 9 个 `DeferredRegister` 挂到 `modEventBus`。注册类在 `registry/` 下：`NaturalistRegistry`（BLOCKS + ITEMS 两个 DeferredRegister，`registerBlock()` 辅助方法一次注册方块与同名 BlockItem，第 126-134 行）、`NaturalistEntityTypes`（30 个实体，`EntityType.Builder` + `MobCategory`）、`NaturalistSoundEvents`、`NaturalistPotions`、`NaturalistRecipes`（自定义 `RecipeType` "net"）、`NaturalistBiomeModifiers`、`NaturalistTags`、`NaturalistCreativeTab`。属性、生成规则、酿造、发射器行为都堆在主类的 `createAttributes/registerSpawnPlacements/registerBrewingRecipes/registerDispenserBehaviors` 里（第 120-249 行）。

## 4. 核心系统

1. **动物实体族 + 能力接口**：`server/entity/base/` 用接口拆解特性 —— `Catchable`（可被虫网捕捉）、`EggLayingAnimal`、`SleepingAnimal`、`HidingAnimal`、`ClimbingAnimal`，基类 `NaturalistAnimal`（仅自定义生成规则 `checkNaturalistAnimalSpawnRules`）、`NaturalistGeoEntity`（GeckoLib 适配，重写 `getBoneResetTime()=5`）。
2. **变体系统**：每个 mob 自带 `enum Variant` + `EntityDataAccessor<INT> DATA_VARIANT` + `BY_ID` 数组，NBT 键 "Variant" 存 id，例 `Butterfly.java:68-70`、`:119-142`、`:330-366`（`getCommonSpawnVariant` 控制自然生成权重）。
3. **自定义 AI goal 库**：17 个 goal，如 `SleepGoal`、`LayEggGoal`、`EggLayingBreedGoal`、`HideGoal`、`BigPanicGoal`/`BabyPanicGoal`、`FlyingWanderGoal`、`SearchForItemsGoal`、`AttackAlligatorEggGoal`、`DistancedFollowParentGoal`。
4. **捕捉/产卵玩法**：`server/item/BugNetItem` + `server/recipe/BugNetInteractionRecipe`（自注册 RecipeType/Serializer，数据包可加配方）；蛋方块 `AlligatorEggBlock/TortoiseEggBlock/SnailEggBlock` 继承原版 `TurtleEggBlock/FrogspawnBlock`；`DuckEggItem` + `ThrownDuckEgg`。
5. **数据驱动刷怪**：`registry/NaturalistBiomeModifiers.java:14-16` 注册 `add_animals` 的 `MapCodec<BiomeModifier>`，实现类 `server/level/modifiers/AddAnimalsBiomeModifier`，由数据包 JSON 注入刷怪。
6. **运行时内置资源包**：`Naturalist.java:95-114` 用 `AddPackFindersEvent` 把 jar 内 `resourcepacks/custom_spawn_eggs` 作为 `PackSource.BUILT_IN` 资源包挂载（给 1.21.5+ 蛋贴图兼容用）。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络：**无自定义包**，全部靠 `SynchedEntityData` + 原版实体同步（如 `Snake.java:67-69` 的 REMAINING_ANGER_TIME/SLEEPING/EAT_COUNTER）。数据驱动：`BiomeModifier`（见上）、标签（datagen 生成）、`BugNetInteractionRecipe` 配方。配置：单一 `ModConfigSpec`（`NaturalistConfig.java`，COMMON 类型，字段名与 mob 名 camelCase 对应，如 `alligatorRemoved`），并通过 `registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new)` 提供 NeoForge 内置配置界面（`Naturalist.java:78`）。datagen：11 个 provider（`datagen/NaturalistDataGenerators.java` 注册方块状态、物品模型、语言、战利品表、方块/物品/实体类型/生物群系标签），输出到 `src/generated/resources`（`build.gradle` 的 `mods`/`data` run + `sourceSets.main.resources { srcDir 'src/generated/resources' }`）。

## 6. Mixin

配置 `src/main/resources/naturalist.mixins.json`（required、`compatibilityLevel: JAVA_21`、refmap `naturalist.refmap.json`）。client 2 个：`ClientLevelMixin`（注入 `getMarkerParticleTarget` RETURN —— 手持 GlowGoop 时允许生存模式显示发光标记粒子）、`ClientPacketListenerMixin`。通用 7 个：`CreeperMixin`（`registerGoals` HEAD 追加 `AvoidEntityGoal<Lion/Catfish>`）、`MobMixin`（`doHurtTarget` HEAD：青蛙咬萤火虫给发光；`checkDespawn` HEAD：按配置强制移除本 mod 实体）、`BottleItemMixin`、`CropBlockMixin`、`MapItemMixin`、`MonsterMixin`、`ZombieMixin`。

## 7. 值得学的 5 条具体做法

1. 单点集中登记属性与生成规则（`Naturalist.java:120-187`），30 个实体一览无遗，便于复制新 mob。
2. 变体枚举 + `BY_ID` 数组 + INT 同步数据（`Butterfly.java:330-366`）——1.21 实体变体最省事的写法。
3. 能力接口拆分实体特性（`server/entity/base/Catchable.java` 等），配合 `instanceof` 判定，避免庞大继承树。
4. 自定义 `BiomeModifier` 序列化器让刷怪由数据包驱动（`registry/NaturalistBiomeModifiers.java`）+ `ModSpawns.Registrar` 抽象把 "注册生成规则" 的平台差异隔离成一个函数式接口（`registry/ModSpawns.java:19-21,60-62`）。
5. 用 `AddPackFindersEvent` 挂内置资源包做版本兼容资源（`Naturalist.java:95-114`）。
6. 反面案例（可避免）：`MobMixin.checkDespawn` 用反射按 mob 名拼出 config 字段名再读取（`mixin/MobMixin.java:52-70`），字段重命名即崩，建议改用 `Map<String, BooleanSupplier>`。
