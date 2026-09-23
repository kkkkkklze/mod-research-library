# yision1/GearsandTavern 源码分析报告

## 1. 基本信息

- Mod 名：Create: Gears and Tavern（机械动力：齿轮与酒馆） / **mod_id：`creategearsandtavern`** / 作者：yision / 版本 1.1.8
- 目标版本：**Minecraft 1.21.1 + NeoForge 21.1.220**（`gradle.properties:24,33`），Java 21 toolchain
- Gradle 插件：`net.neoforged.moddev` **2.0.116** + `java-library`；mods.toml 用 `src/main/templates/META-INF/neoforge.mods.toml` + `generateModMetadata`（ProcessResources `expand`）生成，`sourceSets.main.resources.srcDir generateModMetadata`（构建写法与 MDG 官方推荐一致）
- 许可证：BSD-3-Clause（`LICENSE.txt`，版权 2025 Yison；另有 `TEMPLATE_LICENSE.txt` = MDK 模板许可）
- 编译依赖（`build.gradle:79-93`）：Create `6.0.10-281`（maven.createmod.net，`transitive false`）、Registrate `MC1.21-1.3.0+67`、Ponder `1.0.82+mc1.21.1`、Flywheel 1.0.6（api=compileOnly / impl=runtimeOnly）、Vanillin、JEI 19.21.0.247（compileOnly+localRuntime）、**Kaleidoscope Tavern**（`curse.maven:kaleidoscope-tavern-1475175:8350856`，compileOnly + localRuntime，即"必装的可选依赖"式兼容目标）。源码里出现 `com.github.ysbbbbbb.kaleidoscopetavern.*` 与 `kaleidoscope_dim_wine / kaleidoscope_twilight / kaleidoscope_bloodwine` 三个同作者扩展命名空间——是"跨 mod 兼容"型参考。

## 2. 源码规模与包结构

实测 **53 个 .java / 5128 行**（单模块）。`src/generated/resources` 在 git 中有 **1269 个生成文件**（datagen 产物入库），`src/main/resources` 仅 7 个（mixins.json + 2 lang + 少量模型），本地工作树为稀疏检出（`assets/`、`src/generated` 未落盘）。

包结构：`compat/kaleidoscope`（24 个，含 `cabinet`/`cocktail`/`shaker` 子包）、`compat/create/arm`（3）、`compat/jei`（4）、`content/fluids/drink`（5）、`registry`（5：CGTDataComponents/CGTFluids/CGTIngredientTypes/CGTItems/CGTRecipeSerializers）、`mixin/create`(1) + `mixin/kaleidoscope`(6)、`datagen/recipe`(4)。
最大文件：`content/fluids/drink/CGTDrinkCatalog.java` 753 行、`compat/kaleidoscope/CGTKaleidoscopeBarrelFluids.java` 485、`compat/jei/CGTJeiPlugin.java` 276、`shaker/ShakerFluidHandler.java` 235、`cabinet/BarCabinetLineItemHandler.java` 179、`compat/create/arm/GrapevineTrellisHarvestPoint.java` 173、`mixin/kaleidoscope/BarrelBlockEntityMixin.java` 166。

## 3. 入口与注册

主类 `src/main/java/com/yision/creategearsandtavern/CreateGearsandTavern.java:31-50`（NeoForge 新签名 `(IEventBus, ModContainer)`），注册方式全部走 mod event bus 监听器清单：

```java
modEventBus.addListener(DataGenerators::gatherData);
modEventBus.addListener(CGTArmInteractionPointTypes::register);
modEventBus.addListener(CGTItems::registerCapabilities);          // + Kdw/Kt/Kb 三个扩展命名空间
modEventBus.addListener(CGTKaleidoscopeBarrelFluids::registerCapabilities);
modEventBus.addListener(CGTKaleidoscopeBarCabinets::registerCapabilities);
modEventBus.addListener(CGTKaleidoscopeShakerFluids::registerCapabilities);
modEventBus.addListener(CocktailItemFluidHandlers::registerCapabilities);
CreateGearsAndTavernRegistrate.registrate().registerEventListeners(modEventBus);
CGTDataComponents.register(modEventBus); CGTRecipeSerializers.RECIPE_SERIALIZERS.register(modEventBus);
CGTIngredientTypes.INGREDIENT_TYPES.register(modEventBus); CGTIngredientTypes.FLUID_INGREDIENT_TYPES.register(modEventBus);
```

`commonSetup`（`:52-57`）里用 `event.enqueueWork` 注册 Create 侧兼容（`CGTKaleidoscopeBarrelFluids::registerCreateCompat` 等），并把 `CGTShakerInteractionEvents` 挂到 `NeoForge.EVENT_BUS`。注册框架为 **Registrate 单例**（`CreateGearsAndTavernRegistrate.java:8-9`，`defaultCreativeTab(null)`）——本 mod 几乎不注册自己的方块/物品，主要用于**虚拟流体**（`CGTFluids`）与数据组件。

## 4. 核心系统

**A. 酒桶（KT 多方块机器）接入 Create 流体/物品自动化**——`compat/kaleidoscope/CGTKaleidoscopeBarrelFluids.java`。运行时按 ID 取第三方 BE 类型再注册 capability（`:38-49`：`BuiltInRegistries.BLOCK_ENTITY_TYPE.get(BARREL_BE_ID)` → `event.registerBlockEntity(Capabilities.FluidHandler.BLOCK, ...)`），因此不需要编译期依赖对方内部实现。自定义 `BarrelFluidHandler` 有两层语义：**真液体**直接代理 `FluidTank`，**酿造中的产物物品被虚拟成流体**（`visibleFluid/drainVirtual`，`:220-268`）——1 瓶 = 250mB、按 `VIRTUAL_DRAIN_REMAINDER`（`:36`，`ConcurrentHashMap<String,Integer>`，键=维度+BlockPos）记录"已排掉但不是整瓶"的余数，排空后 `consumeVirtualOutput` 扣 `getOutput()`、清零 `brewLevel/brewTime/recipeId`（`:141-170`）。多格结构通过 mixin 建立"控制器/代理部件"关系：`mixin/kaleidoscope/BarrelBlockEntityMixin.java` 用 `@Unique cgt$controllerPos/cgt$proxyPart`，在 `loadAdditional/saveAdditional` 的 `@At("TAIL")` 存储（NBT key `cgt_controller_pos` 等，`:24-65`），在 `tick` 的 `@At("HEAD") cancellable` 里取消代理部件的 tick（`:67-78`），并一次性初始化整结构（`:80-123`）；接口 `KaleidoscopeBarrelProxy` + `KaleidoscopeBarrelParts/Sides` 支撑。

**B. Create 物流/打包机认多格结构为一个库存**——`CGTKaleidoscopeBarrelFluids.java:57-60`：`InventoryIdentifier.REGISTRY.register(barrelBlock, (level,state,face) -> new InventoryIdentifier.Bounds(BoundingBox.fromCorners(origin.offset(-1,0,-1), origin.offset(1,2,1))))`；`compat/kaleidoscope/cabinet/BarCabinetLineCache.java` + `BarCabinetLineItemHandler.java` 给酒柜做同样的行/线物流（含 3 个 `BarCabinetBlock*Mixin`）。

**C. 机械臂自定义交互点（收割葡萄）**——`compat/create/arm/GrapevineTrellisHarvestPoint.java`（173 行，注释详尽）：继承 `ArmInteractionPoint`、构造时 `mode = Mode.TAKE`、`cycleMode()` 强制不可切换（`:50-52`）、`insert` 原样返回防被配成输出点；`getSlotCount` 只在"缓存非空或下方葡萄成熟"时给 1 格（`:61-67`）；`extract` 分 simulate（`Block.getDrops` 预览）与 execute（`BlockHelper.destroyBlock`，复用掉落表/`BlockDropsEvent`/`doBlockDrops` 规则，`:82-102,147-153`）；一次收割的全部掉落进 `pendingDrops` 逐轮被取走，并随 `serialize/deserialize` 存 `"PendingDrops"`（`:111-127`）。配套 `CGTArmInteractionPointTypes` 注册类型、`GrapevineTrellisHarvestPointType` 判定可交互方块。

**D. 数据驱动的"酒 → 虚拟流体"体系**——`content/fluids/drink/`：`CGTDrinkDefinition`（drinkId + 语言键 + 颜色 + `requiredMods`）、`CGTDrinkCatalog`（753 行，罗列 KT 本体与三个扩展 mod 的全部饮品定义）、`CGTFluids`。每种酒一个 `REGISTRATE.virtualFluid(path, create:fluid/potion_still, potion_flow, ...)`（`registry/CGTFluids.java:52-60`，**直接复用 Create 药水贴图**），且在类初始化时按 `ModList.get().isLoaded` 过滤（`:62-73`）——**未安装的扩展 mod 的酒不会被注册**。酒精度/品质通过 **DataComponent** 表达：`fluidStack.set(CGTDataComponents.KALEIDOSCOPE_DRINK_VARIANT, new KaleidoscopeDrinkVariant(drinkId, brewLevel))`（`:75-93`），签名鸡尾酒另挂 KT 的 `SIGNATURE_COCKTAIL_EFFECTS/COLOR`。物品侧由 `CGTItems` 扫描 `BuiltInRegistries.ITEM` 按命名空间批量注册 `IFluidHandlerItem`（`registry/CGTItems.java:33-50`）。

**E. NeoForge 1.21 新配方/材料系统**——`registry/CGTIngredientTypes.java:15-23` 注册 `IngredientType<ReadyShakerIngredient>` 与 `FluidIngredientType<SignatureCocktailFluidIngredient>`；`compat/kaleidoscope/cocktail/SignatureCocktailFillingRecipe.java` 继承 Create 的 `FillingRecipe` 并覆写 `getResultItem/rollResults`（`:27-35`），结果由 `SignatureCocktailFluidIngredient.consumeMatchedFluid()` 反查液体转物品；`compat/kaleidoscope/shaker/ShakerMixing.java` 用 `ThreadLocal CAPTURED_MIXER_RESULT`（`:20`）把 KT 摇酒壶结果接进 Create 搅拌机（`isReadyShaker` 校验 `BottleBlockItem.isValidForShaker`、`ShakerMixing/ShakerFluidHandler/ShakerIngredientConversions`）。

**F. 蓝图（Schematic）完整兼容**——`compat/kaleidoscope/CGTKaleidoscopeSchematicRequirements.java:26-46`：`SchematicRequirementRegistries.BLOCKS.register(...)` 为 KT 的酒桶（只认 INDEX==4 基座层）、葡萄藤架、药水瓶（`StrictNbtStackRequirement`）、双半砖/挂牌灯（只算下半）等批量提供 `ItemRequirement`，并用 `SafeNbtWriterRegistry.REGISTRY.register(POTION_BOTTLE_BE, ...)` 保住药水 NBT。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：**无**（无 network 包、无自定义包）。所有跨端效果依赖 NeoForge capability 与容器同步。
- **配置**：无 config 文件（用 `ModList.isLoaded` + 定义表的 `requiredMods` 做软开关）。
- **datagen**：`datagen/DataGenerators.java:10-18` 挂 `CGTFillingRecipeGen`/`CGTEmptyingRecipeGen`/`CGTCompactingRecipeGen` 三个 Create `RecipeGen`，产物入库 1269 个 json（`data/creategearsandtavern/recipe/{compacting,emptying,filling}/...`，酒瓶 × 6 个品质等级全展开）；构建中 `sourceSets.main.resources { srcDir 'src/generated/resources' }` 与 data run 的 `--output src/generated/resources` 对齐。
- **JEI**：`compat/jei/CGTJeiPlugin.java`（276 行）注册 `CGTShakerJeiCategory`/`CGTShakerJeiRecipe`，并用 `CGTJeiDrinkFluidHelper` 为"带 DataComponent 的同种流体"提供自定义渲染。

## 6. Mixin

配置 `src/main/resources/creategearsandtavern.mixins.json`（`package com.yision.creategearsandtavern.mixin`，`compatibilityLevel JAVA_21`，refmap `creategearsandtavern.refmap.json`，7 个）。代表：
- `kaleidoscope.BarrelBlockEntityMixin` → `BarrelBlockEntity#loadAdditional/saveAdditional`（`@At TAIL` 存代理坐标）与 `#tick(Level)`（`@At HEAD cancellable`，代理部件直接取消 tick）。
- `kaleidoscope.BarrelBlockEntityAccessor`（Accessor，用于读写 KT 私有 `recipeId/brewLevel/brewTime`，见 `CGTKaleidoscopeBarrelFluids.java:164-167`）。
- `kaleidoscope.BarrelBlockMixin`、`BarrelBlockEntityRenderMixin`、`BarCabinetBlockMixin`、`BarCabinetBlockBehaviourMixin`（酒柜行为/渲染扩展）。
- `create.CreateRecipeCategoryMixin`（调整 Create 的 JEI 配方类别显示）。
所有注入方法/字段统一 `cgt$` 前缀（`@Unique`），NBT 键前缀 `cgt_`，避免与对方 mod 冲突。

## 7. 值得学的 5 条具体做法

1. **用 ID + `BuiltInRegistries` 运行时解析第三方 BE 类型再注册 capability**（`CGTKaleidoscopeBarrelFluids.java:34-49`）：配合 `compileOnly` 依赖，既能深度对接对方功能，又在对方缺类型时安全降级（`barrelType == null → return`）。做跨 mod 兼容时比 mixin 更稳的第一选择。
2. **把"产物是物品"的机器虚拟成流体源**：1 瓶 = 250mB + `VIRTUAL_DRAIN_REMAINDER` 余数记账（同文件 `:36,141-170,250-268`），`getTankCapacity` 在酿造期返回 `visibleFluid(barrel).getAmount()`（`:287-299`）→ Create 管道/储罐能直接抽走工序产物。适用于酿酒、装瓶、任何"工序产出想进管网"的场景。
3. **多格机器在 Create 打包机/物流里注册成一个库存**：`InventoryIdentifier.REGISTRY.register(block, BoundingBox.fromCorners(...))`（`:57-60`）——比自定义 `MountedItemStorageType` 更省事的多格适配路径。
4. **自定义动力臂交互点的完整范式**：`GrapevineTrellisHarvestPoint.java`（`Mode.TAKE` + `pendingDrops` 跨轮缓存 + `serialize` 存档 + simulate/execute 双路 + `doBlockDrops`/`restoringBlockSnapshots` 保护 + 交互点位置 `Vec3.atLowerCornerOf(pos.below()).add(0.5,0.75,0.5)`）。做"让机械臂操作自定义方块/作物"直接照抄。
5. **合并而非重写 Create 配方**：自定义 `FillingRecipe`/`IngredientType` 覆写 `rollResults`，用 `ThreadLocal` 传递"本次匹配到的液体"（`SignatureCocktailFillingRecipe.java:27-35`、`ShakerMixing.java:20`）。在不能改 Create 类时把状态从配方匹配阶段带到结果阶段。

> 另可抄：`CGTDrinkCatalog` 式"清单 + `requiredMods` 过滤 + 语言键"的数据驱动表（新增饮品只改一处）；`SchematicRequirementRegistries`/`SafeNbtWriterRegistry` 双注册让蓝图不丢内容；mixins.json 的 `JAVA_21` + `cgt$` 命名隔离。

> 非库/前置 mod，无公开 API 包（第 8 节不适用）。
