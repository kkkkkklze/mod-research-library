# Minecraft-LightLand/FruitsDelight（果园乐事）源码分析

## 1. 基本信息

- Mod 名 / mod_id：Fruits Delight（果园乐事）/ `fruitsdelight`，版本 1.1.3
- 作者 / 许可证：`lcy0x1`（mods.toml 中 credits="LightLand Team"）/ LGPL-2.1
- 目标版本与加载器：MC 1.20.1 + Forge 47.4.10（`build.gradle` 的 publishCurseForge 里 `addModLoader("Forge","NeoForge")`，即同时声明 NeoForge 兼容）
- Gradle：ForgeGradle 6.0+、mixingradle 0.7-SNAPSHOT、parchment librarian、jarJar 开启、Java 17、parchment 2023.09.03-1.20.1
- 编译依赖（重点）：**Registrate MC1.20-1.3.11（jarJar）**、`dev.xkmc.l2library 2.4.11-slim`、`l2serial 1.2.0`、`l2harvester 0.1.2`（三者均 jarJar，同作者自研库 = 它的 API 基座）、mixinextras 0.2.0-beta.8（jarJar）；Farmer's Delight、Cuisine Delight、JEI 15.20.0.104、Curios 为前置；botany pots / serene seasons / diet / create / biomes-o-plenty / terralith / thirst-was-taken / collectors-reap 为可选

## 2. 源码规模与包结构

`find src/main/java -name '*.java' | wc -l` = **146**（其中 20 个 `package-info.java`）；全仓库 `.java` 总行数 **8667**（含 `src/test` 的 GUIGenerator 267 行）。一级包 `dev.xkmc.fruitsdelight`，第三层主要包（文件数）：

- `content/block` 20、`content/cauldrons` 9、`content/effects` 11、`content/item` 6、`content/recipe` 5
- `init/food` 13、`init/data` 11、`init/plants` 10、`init/registrate` 6、`init/entries` 5、`init` 3
- `compat/botanypot` 9、`compat/create` 5、`compat/biomes` 4、`compat/sereneseasons|jei` 各 3、`compat/thirst|diet` 各 2
- `mixin` 11、`events` 6、`util` 2

最大文件：`init/data/RecipeGen.java` 346、`content/block/DurianLeavesBlock.java` 263、`init/plants/FDMelons.java` 253、`content/item/FDFoodItem.java` 214、`init/plants/FDPineapple.java` 203、`compat/create/CreateRecipeGen.java` 196、`init/plants/FDBushes.java` 193、`content/block/PassableLeavesBlock.java` 185、`init/food/FDJuice.java` 164。

## 3. 入口与注册

主类 `src/main/java/dev/xkmc/fruitsdelight/init/FruitsDelight.java:33`（`@Mod(MODID)` + `@Mod.EventBusSubscriber(bus = MOD)`）。用 **Registrate**（`L2Registrate`）而非 DeferredRegister：

```java
public static final L2Registrate REGISTRATE = new L2Registrate(MODID);
public static final PacketHandler HANDLER = new PacketHandler(new ResourceLocation(MODID,"main"), 1,
        e -> e.create(BlockEffectToClient.class, NetworkDirection.PLAY_TO_CLIENT));
public FruitsDelight() {                     // 构造函数里按模块顺序注册
  FDTrees.register(); FDBushes.register(); FDMelons.register(); FDPineapple.register();
  FDItems.register(); FDEffects.register(); FDJuice.register(); FDFood.register();
  FDBlocks.register(); FDCauldrons.register(); FDMiscs.register();
  FDGLMProvider.register(); FDFluids.register();
  REGISTRATE.addDataGenerator(ProviderType.RECIPE, RecipeGen::genRecipes); ... }
```

`commonSetup`（`:72`）在 `event.enqueueWork` 里做堆肥表注册、大锅配方开关、`ModList.isLoaded(Create.ID)` 判断后 `CreateCompat.init()`、Thirst 兼容、`EffectSyncEvents.TRACKED` 效果同步；`gatherData`（`:94`）挂 5 个 provider。

## 4. 核心系统

**① 枚举 + 接口驱动的植物注册**（`init/plants/PlantDataEntry.java:20`，`FDTrees.java`）：`FruitPlant<E> extends PlantDataEntry<E>` 定义 `registerComposter/registerConfigs/registerPlacements/getPlacementKey`；`FDTrees` 等 4 个枚举常量在构造器里一次性注册树叶、树苗、盆栽、果实物品，并各生成 3 个 `ResourceKey`（configured/wild/placed feature）。`PlantDataEntry.gen(val, mod)` 统一遍历 4 个枚举 `values()` 批量跑同一逻辑，新增一种水果只需加一个枚举常量。世界生成配置写进数据包：`FDDatapackRegistriesGen.java:28` 用 `RegistrySetBuilder` 注册 CONFIGURED_FEATURE / PLACED_FEATURE / BIOME_MODIFIERS（`ForgeBiomeModifiers.AddFeaturesBiomeModifier`）。

**② 声明式注册 + datagen 一体**（`init/registrate/FDItems.java:41`）：方块/物品的 blockstate、model、lang、tag、loot、color 全部内联在 builder 链上，例如果酱瓶 `blockstate((ctx,pvd)->…pvd.modLoc("block/jam_bottle_block")…renderType("cutout"))` + `.color(() -> () -> (stack, layer) -> layer == 0 ? -1 : fruit.color)`；`JELLY/JELLO` 用 `BlockEntry[]`/`ItemEntry[]` 数组按 `FruitType.values()` 批量生成。

**③ 食物数据抽象**（`init/food/`）：`FruitType`×`FoodType`×`IFDFood`/`IFoodClass`，`FoodType.build(Item.Properties, IFDFood)` 由 `IFoodClass.build(block, props, type)` 决定实例类型（`RecordFood`/`EffectEntry` 提供效果）。`FDJuice.java:121` 的嵌套 `Type`/`Category` 枚举用布尔位（cook/heated/waterCraft/waterMix）决定该饮品走烹饪锅还是合成台，配方生成 `FDJuice.recipe()` 直接读这些位。

**④ 大锅交互数据化**（`content/cauldrons/FDCauldronInteraction.java:19`）：用 `record implements CauldronInteraction`（字段 action/result/sound/pred/requiresHeat），`perform()` 里 `level.getBlockState(pos.below()).is(TagRef.HEAT_SOURCES)` 判断热源，把"什么物品 + 什么条件 → 什么方块"缩成一行数据。

**⑤ 虚拟流体**：`init/entries/FruitFluid.java` + `VirtualFluidBuilder extends FluidBuilder`（继承了 Registrate 的流体构建器并覆盖 `asSupplier()`），`ClientFruitFluid` 分离客户端渲染。

**⑥ 效果与客户端同步**：`content/effects/*`（RangeSearchEffect/RangeRenderEffect/SizeEffect…），`events/BlockEffectToClient.java:13` 是 `@SerialClass extends SerialPacketBase`（l2serial 自动序列化），`events/EffectHandlers.java:25` 为 `Bus.FORGE` 订阅者，处理 `EntityEvent.Size`（缩小效果）、`LivingEntityUseItemEvent`、`ItemTooltipEvent` 等。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：l2serial 的 `PacketHandler`（主类 `:41`），单包 `BlockEffectToClient`，`@SerialClass.SerialField` 声明 `block/id/type`，`Type` 枚举持 `BiConsumer<Block,Entity>` 在客户端回调粒子。
- 数据驱动：`GlobalLootModifier`（`init/data/FDGLMProvider.java:17` 用 `REGISTRATE.simple(..., ForgeRegistries.Keys.GLOBAL_LOOT_MODIFIER_SERIALIZERS, ...)` 注册 Codec；`ReplaceItemLootModifier` 让嗅探兽挖掘 5% 掉榴莲树苗），自定义 `RecipeSerializer` 两种（`init/registrate/FDMiscs.java:15`，基于 l2library 的 `AbstractShaped/ShapelessRecipe`，`JellyCraftShapelessRecipe.assemble` 把果冻用到的水果种类写成 NBT `FDFoodItem.ROOT`）。
- 配置：`init/data/FDModConfig.java:8` ForgeConfigSpec（CLIENT+COMMON），含生长/掉落概率、效果范围、大锅配方与 Thirst 兼容开关；`FDConfigGen` 用 l2library 生成配置文件。
- datagen：Registrate `ProviderType`（BLOCK_TAGS/ITEM_TAGS/RECIPE/LANG）+ `GatherDataEvent` 里的 `DatapackBuiltinEntriesGen`/`BotanyGen`（联动 Botany Pots）/`FDBiomeTagsProvider`/`FDGLMProvider`。

## 6. Mixin

配置 `src/main/resources/fruitsdelight.mixins.json`：`priority: 1000`、`required: true`、`injectors.defaultRequire: 1`、package `dev.xkmc.fruitsdelight.mixin`，common 10 个 + client 1 个（`SimpleBakedModelMixin`）。代表：
- `mixin/PlayerMixin.java:23` `@ModifyVariable(at=@At("LOAD"), method="canEat", argsOnly=true)` → 拥有 `APPETIZING` 效果时可无视饥饿进食；`:28` `@ModifyReturnValue(method="getFoodData")` 把 player 塞进 `FoodDataAccessor`（`FoodDataMixin` 实现的接口），从而让食物数据能反查玩家（配合 `events/FoodDataAccessor.java`）。
- 其余：`AbstractCauldronBlockAccessor`（accessor）、`AnimalMixin`、`BoatMixin`、`HoneyBlockMixin`、`BrushableBlockMixin`、`AbstractArrowMixin`、`LivingEntityMixin`、`BlockStateBaseMixin`。

## 7. 值得学的 5 条具体做法

1. **枚举当注册表 + 统一遍历**：`PlantDataEntry.LIST` + `gen/run` 让"新增一种果树"只写一个枚举常量，worldgen/composter/配方/tag 全自动跟上（`init/plants/PlantDataEntry.java:22`）；适合任何"同类内容成批出现"的 mod。
2. **注册与 datagen 写在同一 builder 链里**：`init/registrate/FDItems.java:41` 把 blockstate/model/lang/tag/color 内联，避免"模型忘写"类错误；适合内容量大的食物/方块 mod。
3. **可选依赖用 `ModList.isLoaded(...)` + 单一 compat 入口**：`init/FruitsDelight.java:80`、`compat/create/CreateCompat.java:9`（用 Create 的 `OpenPipeEffectHandler.REGISTRY.registerProvider` 官方扩展点，而非 mixin）——能不动字节码就不动。
4. **record 承载交互数据**：`FDCauldronInteraction` 用 record + 工厂方法（`of/withHeat`）描述交互，`TagRef.HEAT_SOURCES` 判热源，新增配方零新增类；适合自定义方块交互。
5. **自研库用 jarJar 内嵌**：`build.gradle` 对 l2library/l2serial/l2harvester/Registrate/mixinextras 全部 `jarJar` + `jarJar.ranged`，并配合 `tasks.jarJar.finalizedBy('reobfJarJar')` 与 `archiveClassifier` 处理主/瘦包（`build.gradle` 末尾），是分发前置依赖的样板写法。
