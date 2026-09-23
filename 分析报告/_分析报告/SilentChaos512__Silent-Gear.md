# Silent Gear 源码分析报告

> 本报告分析的是「物品侧材质/部件拼接」路线。为对照，方块侧同类分析见 `深挖__Domum-Ornamentum__方块版材质拼接.md`。
> 路径约定：正文中 `SG/…` 代表 `src/main/java/net/silentchaos512/gear/…`；数据 JSON 路径从仓库根写全。所有行号均为本次实测核对。

## 1. 基本信息

- mod_id：`silentgear`（`gradle.properties` `mod_id`；`SG/SilentGear.java:23`）
- 作者：SilentChaos512（`gradle.properties` `mod_authors`）
- 许可证：MIT（`gradle.properties` `mod_license`）
- 目标版本：**MC 1.21.1 / NeoForge 21.1.219**，mod 版本 4.2.1（`gradle.properties` `minecraft_version` / `neo_version` / `mod_version`）。速览卡片把它写成「1.20.1 userdev」是错的：加载器是 **NeoForge**（清单文件为 `src/main/resources/META-INF/neoforge.mods.toml`，非 `mods.toml`），版本线是 1.21.1。
- Gradle 插件：`net.neoforged.gradle.userdev` 7.0.170（`build.gradle:7`，即 NeoGradle），非旧 ForgeGradle；另有 `com.gradleup.shadow`、`cursegradle`、`minotaur`、`maven-publish`。
- 工程结构：single（单模块，无子项目）。
- Java 版本：**21**（`build.gradle:33` `java.toolchain.languageVersion = 21`，注释「Mojang ships Java 21 … 1.20.5」）。
- 编译依赖与发布坐标：`net.silentchaos512:silent-gear-1.21.1-neoforge`（`build.gradle:16` `archiveNameNeo`，发布 artifactId 见 `build.gradle:263`），经 GitHub Packages 发布（`build.gradle:251-269`）。运行期依赖 `silent-lib`、`curios`、`caelus`；`jei`/`emi` 为 compileOnly。内置 `com.scrtwpns:mixbox`（物理混色库）并 relocate 进 shadow jar（`build.gradle:41-50`）。

## 2. 源码规模与包结构

- 实测 **507 个 `.java`**、**约 49,109 行**（`wc` 两批 36,056 + 13,053）。无 test / generated Java，全部位于 `src/main/java`，故源码树完整。
- 资源亦完整：`src/generated/resources/data/silentgear/` 下有 **132 份材料 JSON**、**48 份部件 JSON**、**75 份特性 JSON**；`src/main/resources/data` 含 recipe/worldgen/patchouli 等。
- 主要包及文件数（顶层，`SG/` 下）：`api` 75、`block` 63、`item` 61、`gear` 57、`client` 55、`crafting` 41、`data` 32、`setup` 27、`network` 19、`util` 15、`core` 12、`compat` 11、`command` 9、`loot` 8、`event`/`entity` 各 5、`mixin` 3。
- 最大源文件（行数实测）：`SG/data/MaterialsProvider.java` 2011、`SG/data/recipes/ModRecipesProvider.java` 1834、`SG/util/GearHelper.java` 841、`SG/data/trait/TraitsProvider.java` 651、`SG/util/GearData.java` 624、`SG/block/alloymaker/AlloyMakerBlockEntity.java` 451、`SG/Config.java` 433、`SG/event/GearEvents.java` 418、`SG/block/charger/ChargerBlockEntity.java` 418、`SG/data/tags/ModItemTagsProvider.java` 398、`SG/command/TraitsCommand.java` 384、`SG/api/data/material/MaterialBuilder.java` 365。
- 注意：前两名都是 **datagen 生成器**（把材料/配方写成 Java 构建再 dump 成 JSON），不是运行期逻辑——这是「数据驱动」与「类型安全构建」折中的信号。

## 3. 入口与注册

入口 `SG/SilentGear.java:21` `@Mod(SilentGear.MOD_ID)`，构造器仅做分流：

```java
PROXY = FMLEnvironment.dist == Dist.CLIENT
        ? new SideProxy.Client(modEventBus, modContainer)
        : new SideProxy.Server(modEventBus, modContainer);
modContainer.registerConfig(ModConfig.Type.COMMON, Config.Common.SPEC);
```

真正的注册在 `SG/SideProxy.java:45-86` 的构造器里：
- 把所有 `DeferredRegister` 挂到 mod 总线（`SG/SideProxy.java:46-72`），含 `SgDataComponents.REGISTRAR`（`:60`）与 8 个自定义 Registry 的注册（`SG/setup/SgRegistries.java:70-80` `NewRegistryEvent`）。
- 数据管理器作为 **reload listener** 注册（`SG/SideProxy.java:129-133` `AddReloadListenerEvent`）：`event.addListener(SgRegistries.TRAIT/MATERIAL/PART)`。
- 全局事件：命令、server started/stopping；客户端在 `SideProxy.Client` 追加 `ColorHandlers::onItemColors`、HUD、tooltip、`ModItemModelProperties.register`（`:190-205`）。
- 事件订阅点：mod 总线上 `NewRegistryEvent`（自定义注册表）、`AddReloadListenerEvent`（数据管理器）、`RegisterCapabilitiesEvent`（给 9 个方块实体注册 `Capabilities.ItemHandler.BLOCK`，`SG/SideProxy.java:107-121`）；game 总线上由 `SG/event/GearEvents.java`（418 行，事件/附魔/掉落钩子）与 `@EventBusSubscriber` 类（如 `SG/setup/SgDataComponents.java` 内嵌 `TooltipHandler`、`GearData` 内嵌 `EventHandler`）承担。
- 事件订阅采用 `@EventBusSubscriber`（mod 或 game 总线，类上/方法上 `@SubscribeEvent`）；`EventBusSubscriber.Bus.MOD` 见 `SG/setup/SgRegistries.java:24`。

## 4. 核心系统

### 4.1 一件 gear 物品的数据规格 = 两个 DataComponent（问题①）
1.21 里 **不再用 NBT**，而用注册式 `DataComponentType`（`SG/setup/SgDataComponents.java:31` `DeferredRegister.createDataComponents`）。一件 gear 只挂两个核心组件：
- `GEAR_CONSTRUCTION`（`SgDataComponents.java:45`）→ record `GearConstructionData(parts, isExample, brokenCount, repairedCount)`（`SG/core/component/GearConstructionData.java:19-42`，自带 `CODEC` + `STREAM_CODEC`）。`parts` 是 `PartList`（`SG/api/part/PartList.java:22`，`AbstractList<PartInstance>`）——**部件槽位**就在这一份 immutable 列表里。
- `GEAR_PROPERTIES`（`SgDataComponents.java:51`）→ `GearPropertiesData(Map<GearProperty,GearPropertyValue>)`，是**算完并缓存下来的属性结果**，用 `Codec.dispatchedMap` 按属性名编解码（`SG/core/component/GearPropertiesData.java:24-49`）。
另有派生/辅助组件：`GEAR_MODEL_KEY`、`GEAR_MODEL_INDEX`（均 `@Deprecated // Remove in 1.21.2`，`SgDataComponents.java:69-82`）、`PAINT_COLOR`、`TRAIT_ENCHANTMENTS`、`MATERIAL_GRADE` 等。
**蓝图 vs 规格的关系**：`GearBlueprintItem`（`SG/item/blueprint/GearBlueprintItem.java:40-47`）本身只声明「我是某 gearType 的 MAIN 部件来源」（`getPartType()=MAIN`），它不是整件装备的规格；整件装备的完整部件集由 `PartList` 承载。gear item 的 `getRequiredParts()`（默认仅 MAIN，`SG/api/item/GearItem.java:27,71`）给出该类型要求的槽位集合，`construct(parts)`（`SG/api/item/GearItem.java:33-48`）= `writeConstructionParts` + `recalculateGearData` + 触发 `onGearCrafted`。改装/升级通过 `addUpgradePart`/`addOrReplacePart` 往 `PartList` 增删并重写 construction 组件（`SG/util/GearData.java:425-523`）。

### 4.2 属性汇总的时机与来源（问题①续）
来源分层，全在 `SG/util/GearData.java`：
- `getProperties(stack)`（`:54-65`）读 `GEAR_PROPERTIES`；**若不存在则触发重算并回读**——即「结果写回物品、下次直接读」的**惰性缓存**模型。
- `recalculateGearData`（`:90`）被显式要求「**ANY TIME an item is modified** 都要调用」（`:82-84` javadoc）。它发 `GearRecalculateEvent.Pre/Post`（`:99-105`），再走 `tryRecalculateGearData`（`:117`）三趟：
  1. `calculateBaseProperties`（`:195-217`）：`parts.getPropertyModifiersFromParts(gearType)`（`SG/api/part/PartList.java:79-95`）汇总**各部件**贡献，叠加 **gear item 类**与 **gear type** 的相关属性；材料属性经 `Material.getPropertyModifiers`（`SG/gear/material/AbstractMaterial.java:128-134`，父材料兜底）流入。
  2. `calculateBonusProperties`（`:219-250`）：第 1 趟得到的 traits 逐条 `getBonusProperties`，再叠加 `Config.Common.getPropertyBonusMultiplier(property)` 全局修正。
  3. `calculateFinalProperties`（`:252-266`）：base + bonus 合并，`property.computeUnchecked(...)` 求最终值，`gear.set(GEAR_PROPERTIES, finalProperties)`（`:136`）**写回物品**。
- `GearProperty` 带 `isForMaterialsOnly()` 标记：这类属性只在算材料时出现，进 gear 第一趟时被显式 `continue` 丢弃（`:203-207`），保证「材料内部属性」不污染装备结果。
- `onRecalculatePre/Post`（`:143-193`）顺带把结果翻译进原版组件：`DataComponents.TOOL`（`:168`）、`ITEM_NAME`（`:147`）、`DYED_COLOR`（`:182`）、`GEAR_MODEL_INDEX`/`GEAR_MODEL_KEY`（`:173-177`）。
- 版本迁移兜底：玩家登录时对手持/curio 槽 gear 强制重算一次（`SG/util/GearData.java:606-622`）。
结论：**既非纯懒算也非每帧算**，而是「修改即重算 + 结果烘进 item 组件、读取即命中」。

### 4.3 材料系统（问题②）
材料 = 一个 JSON 文件，落在自定义数据文件夹 `silentgear_materials/`（`SG/gear/material/MaterialManager.java:32-41`），由 `DataResourceManager` 在 `onResourceManagerReload` 里 `listResources(dataPath, *.json)` 解析（`SG/core/DataResourceManager.java:160-213`），**不是**注册表实例。取数走 `MaterialManager.fromItem(stack)`——遍历用 `material.getIngredient().test(stack)` 匹配、优先返回子材料（`:134-160`）。
- **继承**：每份 JSON 有 `parent`（如 `"parent":"silentgear:empty"`），`AbstractMaterial.getPropertyModifiers/getCategories/getPartTypes` 在本级为空时递归父级（`SG/gear/material/AbstractMaterial.java:52-58,116-134`）。
- **分类 category**：`crafting.categories`（如 `metal/endgame`），`isInCategory` 判定；`fromItem` 冲突检测用 `ingredientChecks` Multimap 报告同一材料料冲突（`MaterialManager.java:54-73`）。
- **属性 bag**：材料的 stats 是 `Map<PartType, GearPropertyMap>`（`AbstractMaterial.java:31`），即「同一材料在不同槽位（main/rod/tip/…）给不同属性」。运行期一件装备上的「材料实例」是 `MaterialInstance = DataResource<Material> + ItemStack + List<MaterialModifier>`（`SG/gear/material/MaterialInstance.java:41-58`）——grade/charged/crude 等增强作为 `IMaterialModifier` 挂在这个 bag 上，可整体编解码。
- 实测 JSON 结构（`src/generated/resources/data/silentgear/silentgear_materials/azure_electrum.json`）：顶层 `type`/`parent`/`crafting`/`display`/`properties`；`properties` 下按 `silentgear:main`、`silentgear:rod` 分组，值可为裸数字（base）或 `{"operation":"ADD"/"MULTIPLY_TOTAL","value":n}`（modifier），还能带 per-gear 子键（如 `attack_speed/axe`）与 `traits` 列表（每条含 `conditions`+`level`+`trait`）。`display.color` 是 ARGB hex、`main_texture_type` 为 `HIGH_CONTRAST`/`LOW_CONTRAST`。
- 材料按 `type`（`MaterialSerializer` 注册表分发，`SG/gear/material/MaterialSerializers.java`）分四类实现：`SimpleMaterial`、`CompoundMaterial`/`CustomCompoundMaterial`（复合材料，blend 子材料色与属性）、`ProcessedMaterial`（需机器加工、可带 grade）；`MaterialCategories.java` 定义 category 常量集（metal/organic/wood/endgame…）供 trait 条件与配方筛选。

### 4.4 部件与蓝图（问题①/④）
部件同材料：`silentgear_parts/` 一份 JSON，`type` 分 `silentgear:core`（可组合进 gear 的核心件）与简单件；`core` 件带 `gear_type`+`part_type`+`properties`（见 `src/generated/resources/data/silentgear/silentgear_parts/axe_head.json`：main 槽 + `attack_damage ADD 5`）。`PartManager`/`PartList` 复用同一 `DataResourceManager` 基类。蓝图（`GearBlueprintItem`/`PartBlueprintItem`，`SG/item/blueprint/`）只是「某 gearType 的 MAIN/某槽位部件的物品化载体」，`BlueprintType` 控制模板（一次性）还是蓝图（可复用，`AbstractBlueprintItem.java:30-44`），可用类型由 `Config` 决定（`:46-50`）。
- 槽位容量由 `PartType.maxPerItem()` 决定（注册表记录的一部分）：`addOrReplacePart` 在同类部件已达上限时先移除最旧再放入（`SG/util/GearData.java:509-523`），使「同槽多件」与「同槽唯一」都成为数据而非代码约束。

### 4.5 特性 traits（问题④）
`silentgear_traits/` JSON → `TraitManager`（同为 `DataResourceManager`）。trait 由「条件（`TraitConditionSerializer` 注册表）+ 效果（`TraitEffectType` 注册表）」组合，见 `SG/gear/trait/effect/` 下 20 种效果（属性、附魔、自修、拾取磁吸等）。特性在 4.2 第 1 趟随材料/部件属性一并算出，存入 `GEAR_PROPERTIES.TRAITS`，第 2 趟据此产 bonus。
- 条件类型在 `SG/gear/trait/condition/`：`material_ratio`（材料占比达标，见 azure_electrum.json 的 `accelerate` 条件）、`material_count`、`gear_type`、以及 `and/or/not` 组合子——故「某材料占比≥35% 才给加速特性」纯 JSON 表达。
- 效果类型 `SG/gear/trait/effect/` 是注册表枚举（`AttributeTraitEffect`/`EnchantmentTraitEffect`/`DurabilityTraitEffect`/`SelfRepairTraitEffect`/`AttachDataComponentsTraitEffect` 等），addon 要新行为需注册新 `TraitEffectType`（属「类型=Java」侧）。

### 4.6 渲染与 tint（问题③，对照方块侧）
方块侧是「sprite 名 = 部件 id + 烘焙」；**物品侧完全不同**：
- gear item 模型只 `parent: builtin/entity`（`src/main/resources/assets/silentgear/models/item/axe.json` → `base_gear.json:2`），即交给自定义渲染器 `GearItemRenderer`（`extends BlockEntityWithoutLevelRenderer`），通过 `GearItemExtensions.getCustomRenderer()`（`SG/client/renderer/GearItemExtensions.java:12-18`）注册（`SG/setup/SgEntities.java:76-77`）。
- **贴图命中键 = “gearType + 槽位形状 + 材料纹理类别”，不是部件 id**：`getPartTextureLocations`（`SG/client/renderer/GearItemRenderer.java:66-167`）按 `partType` 拼出通用路径，如 `item/pickaxe/main_generic_lc|_hc`、`rod_generic_<alias>`、`tip_sharp`、`grip_wool`、`binding_generic`、`adornment_generic`。材料只决定 `TextureType` 变体（HIGH_CONTRAST 会额外叠 `_highlight` 层）与 **tint 颜色**，不新增贴图。
- **上色**：`renderByItem`（`:258-347`）逐部件取通用 sprite，`renderColoredSprite`（`:169-190`）把 ARGB 拆成顶点色乘进去（alpha 强制 1）。颜色来自 `GearColorUtils.getBlendedColorForPartInGear`（`SG/client/util/GearColorUtils.java:31-45`），复合材料用 **mixbox 混色算法**（`ColorBlendAlgorithm.MIXBOX`，`:28`）。
- **两套缓存键**：① 几何——`QUADS_FOR_SPRITES_CACHE`（Guava，max 128 / 5min），键 = `TextureAtlasSprite` → `List<BakedQuad>`，用 `UnbakedGeometryHelper.bakeElements` 烘一次即复用（`GearItemRenderer.java:42-64`）；② 颜色——`GEAR_COLOR_CACHE`（max 1000 / 5min），键 = **model key 字符串**（`GearData.getModelKey`，`SG/util/GearData.java:312-326`，形如 `ns:item:` + 各部件 `getModelKey()` 逗号拼接）+ 动画帧（`GearColorUtils.java:47-74`）。
- 结论：**每帧不重算**——quad 几何按 sprite 烘焙缓存，blended 颜色按 model-key 缓存，帧内只做一次缓存查表 + 顶点色乘法。（另有一条旧的 tint-index 路径 `GearItem.getItemColors()`（`SG/api/item/GearItem.java:92-110`）+ `ColorHandlers`，与 model-key 组件同属 `@Deprecated`，正在被 BERL 取代。）
- 特化渲染另起三类：远程武器/弓箭走 `GearRangedItemRenderer`、三叉戟走 `GearTridentRenderer`（内部复用 `GearItemExtensions.renderer.renderByItem`，`SG/client/renderer/GearTridentRenderer.java:28`）、盔甲与鞘翅靠 `GearItemExtensions.getArmorLayerTintColor`（`SG/client/renderer/GearItemExtensions.java:20-26`）取 `GearArmorItem.getArmorColor`。钓鱼竿的线/浮子按 `bobber_<textureAlias>` + 混合色在 `rodLineRendering` 里叠画（`GearItemRenderer.java:208-248`）。
- `GEAR_MODEL_INDEX` 是一枚位掩码（`SG/util/GearData.java:328-353`）：broken→0；否则按主材料纹理 `highContrast?3:2` 起底，`hasTip` 再 `|=4`、`hasGrip` 再 `|=8`——旧式「用整数选一组模型 override」的遗留，1.21.2 计划随 model-key 组件一并移除。

### 4.7 蓝图驱动的合成（问题①/④，README「blueprint 消除配方冲突」的落地）
`SG/crafting/` 41 个文件，核心是**自定义 Ingredient** 而非写死物品。`SG/crafting/ingredient/BlueprintIngredient.java:28` 实现 NeoForge `ICustomIngredient`，只按 `part_type + gear_type` 两个字段匹配（`CODEC` `:29-34`，注册进 `SgIngredientTypes`）：`test()` 时 `dissolve()` 扫 `BuiltInRegistries.ITEM` 过滤出所有 `IBlueprint` 并按类型判定（`:66-88`）——**配方里从不列举具体蓝图物品**，因此 addon 加蓝图无需新配方即自动被识别，这就是 README:3 所说「无配方冲突」的机制。同类还有 `GearPartIngredient`、`PartMaterialIngredient`、`GearTypeIngredient`、`CustomAlloyIngredient`（`SG/crafting/ingredient/`），均由 `SgIngredientTypes.REGISTRAR`（`SG/setup/SgIngredientTypes.java`）以 `IngredientType`+`MapCodec` 注册。
成品配方：`ShapedGearRecipe`/`ShapelessGearRecipe` 用上述 ingredient 摆出各槽位，产出经 `GearItem.construct`→写 construction→`recalculateGearData`（即 4.2 管线的入口）。改装线另有一整套配方类型：`smithing/`（gear/coating/upgrade 三型）、`salvage/`（拆件回料）、`press/`、`alloy/`（6 种合金机配方）、`modkit/`（用改件 kit 增删部件）、`GearPartSwapRecipe`（换部件）、`QuickRepairRecipe`/`QuickPaintRecipe`/`ConversionRecipe`/`ToolActionRecipe`。故「新部件能否进某装备」由配方 + `GearPart.canAddToGear`（`GearItem.supportsPart` `SG/api/item/GearItem.java:65-69`）共同决定，而非硬编码。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **自定义包**（`SG/network/`）：`SgNetwork.java:14` 用 `RegisterPayloadHandlersEvent` 注册版本化 registrar `"4.2"`。关键设计：materials/parts/traits 是数据管理器不是同步注册表，故服务端把它们整表推给客户端——`SyncMaterialsPayload`/`SyncPartsPayload`/`SyncTraitsPayload`（play-to-client，`SgNetwork.java:17-31`），payload 内含 `Map<ResourceLocation,T>` 用 `DISPATCH_STREAM_CODEC` 编码（`SG/network/payload/server/SyncMaterialsPayload.java:17-33`），客户端 `DataResourceManager.handleSyncPacket` 整表替换（`SG/core/DataResourceManager.java:249-263`）。此外还有 `RecalculateStatsPayload`、`SelectBlueprintInBookPayload`、`SwingGearPayload` 等 C2S。真正的结构注册表用 `.sync(true)` 走 NeoForge 注册表同步（`SG/setup/SgRegistries.java:35-60`）。
- **Codec 覆盖**：`GearConstructionData`、`MaterialInstance`、`PartList`、`GearPropertiesData` 均同时给 `CODEC`（持久化/磁盘）与 `STREAM_CODEC`（网络），组件在 `SgDataComponents` 里 `.persistent(CODEC).networkSynchronized(STREAM_CODEC)` 双绑定。
- **配置**（`SG/Config.java`，433 行，COMMON/CLIENT 两份 TOML）：材料等级分布（`median_grade`/`standard_deviation` :291-297）、repair kit 容量/效率（:117-136）、蓝图可用类型 `types_allowed`（:93）、`force_remove_enchantments`（:210）、属性全局修正（:273，被 `GearData.java:242` 消费）。
- **datagen**：完整。`SG/data/DataGenerators.java:37-70` `GatherDataEvent` 挂 `MaterialsProvider`/`PartsProvider`/`TraitsProvider`/`ModRecipesProvider`/tags/loot/advancement/客户端模型。材料 JSON 由 Java 侧 `MaterialBuilder`（365 行）构建后 dump——「数据驱动」但「构建期类型安全」。生成物入 `src/generated/resources`（`build.gradle:108` 将其并入 main resources）。
- **可选 datapack 分发**：仓库根带 `optional_data_packs/Easy Super Mixer/`，是作者预置的平衡性补丁包（改配方的「难度预设」）——一种「不写代码即可换玩法」的官方样板。游戏内另有材料书 GUI（`SG/client/gui/book/`）从数据管理器读取全部材料，作为可浏览的活文档。
- **数据化程度（问题④）**：加一种**新部件/新蓝图/新材料**通常 **0 行 Java + 1 份 datapack JSON** 即可（材料料件、属性、traits、颜色、纹理类别全在 JSON；配方走原版/自定义 recipe JSON）。需要 Java 的是**新类别/新行为**：新 `PartType`/`GearType`/`GearProperty`/`TraitEffectType`/`MaterialSerializer` 等——它们是注册表项。也就是说「实例=JSON，类型=Java 注册表」。
- **版本耦合（问题⑤，读者在 Forge 1.20.1 借用会撞的点）**：
  1. **DataComponents 整套不可用**：`SgDataComponents.java:31` `DeferredRegister.createDataComponents`、`registerComponentType(...persistent/networkSynchronized)`、以及 `core/component/*` 的 record + `StreamCodec`——`DataComponentType`/`StreamCodec` 是 1.20.5+/NeoForge 才有的，Forge 1.20.1 只能回到 `ItemStack` NBT（`getOrCreateTag()`/`getShareTag`）。
  2. **注册表**：`SgRegistries.java:35-49` 用 `new RegistryBuilder<>(key).sync(true)` + `NewRegistryEvent`（NeoForge）；Forge 1.20.1 对应 `DeferredRegister.makeRegistry` + `RegistryEvent.NewRegistry`。
  3. **网络**：`SgNetwork.java:14` 的 `RegisterPayloadHandlersEvent`/`CustomPacketPayload`/payload registrar；Forge 1.20.1 是 `NetworkRegistry.newSimpleChannel` + `PacketDistributor`，写法完全不同。
  4. **渲染/客户端属性**：`GearItemRenderer.java:52-53` 的 `UnbakedGeometryHelper.createUnbakedItemElements/bakeElements` 与 `:221` 的 `ItemProperties.getProperty` 属 1.21 客户端模型重写；Forge 1.20.1 需用旧 `IItemPropertyFunction`/`ItemOverrideList`。
  5. **Java 21**（`build.gradle:33`）vs 1.20.1 的 Java 17。
  6. `AbstractBlueprintItem.java:22` `properties.component(DataComponents.RARITY, …)` 亦 1.20.5+。
  可平移的部分：**架构思想**（construction/properties 分离、三趟汇总、写回缓存、DataResourceManager+自定义数据文件夹整表同步、通用 sprite + tint + 双缓存渲染）与 **tint-index 上色路径**（`RegisterColorHandlersEvent.Item`/`ItemColor` 在 Forge 1.20.1 同样存在）。

## 6. Mixin

少量，2 个，位于 `SG/mixin/`（`silentgear.mixins.json`，`compatibilityLevel: JAVA_16`）：
- `MixinItemEntity.java:17-19`：`@Inject(HEAD, cancellable)` 于 `ItemEntity#hurt`——为掉落物相关特性/磁吸拦截伤害。
- `MixinPowderSnowBlock.java:13-15`：`@Inject(HEAD, cancellable)` 于 `PowderSnowBlock#canEntityWalkOnPowderSnow`——让带特定 armor 特性的 gear 允许踩细雪。
除此之外大量扩展靠事件（`event/`、`@EventBusSubscriber`）与 Forge/NeoForge hook，而非 Mixin。

## 7. 值得学的 5 条

1. **结果写回 item 组件、读取即命中的惰性缓存**：`SG/util/GearData.java:54-65` + `:136`——`getProperties` 无组件才重算并把最终 map `set` 回 stack。法宝/装备属性稳定读取时避免每帧遍历材料树；代价是「改完必调 recalculate」这条纪律（`:82-84`）。
2. **三趟分离的属性汇总管线**：`SG/util/GearData.java:131-135`（base=部件+材料+类型 → bonus=traits+config → final=合并）。把「来源」正交拆层，新增一类来源只动一趟，是装备系统可维护的关键骨架。
3. **通用 sprite + tint + 双缓存渲染**：`SG/client/renderer/GearItemRenderer.java:42-64,66-167` 与 `SG/client/util/GearColorUtils.java:47-50`。用「按形状分组的少量贴图」+ 顶点色，把「N 材料 × M 部件」的贴图爆炸压成 O(形状数)；缓存一个按 sprite、一个按 model-key，帧内零重算——直接可搬到法宝外观系统。
4. **「实例走 JSON、类型走注册表」的分层 + 整表网络同步**：`SG/core/DataResourceManager.java:160-213,249-263` + `SG/network/payload/server/SyncMaterialsPayload.java`。自定义数据文件夹热重载、客户端靠服务端推整表，绕开注册表同步限制；addon 加材料零 Java。
5. **面向 addon 的公开构建/事件面**：`SG/api/data/material/MaterialBuilder.java`、`SG/api/data/part/PartBuilder.java`、`SG/api/data/trait/TraitBuilder.java` + `SG/api/event/`（`GearRecalculateEvent`、`GetPropertyModifiersEvent`、`GetTraitsEvent`）——把「扩展点」显式沉到 `api` 包，README `:25-95` 直接教 addon 作者引 Maven 坐标 + 继承 ProviderBase。

### ⑥ 与 Domum Ornamentum「源方块引用」路线的取舍对照

| 维度 | Silent Gear（物品侧，本仓库） | Domum Ornamentum（方块侧，源方块引用） |
|---|---|---|
| 数据载体 | 两个 DataComponent：construction(PartList) + properties(结果缓存) | 引用源方块 + 部件/材质 JSON |
| 命中键 | 通用 sprite 路径（gearType+形状+纹理类别），材料仅定 tint | 源方块 / 部件 id 直接选贴图 |
| 上色 | 顶点色乘入 + mixbox 混色；颜色缓存键 = model-key | 依源方块纹理/调色 |
| 掉落与复制 | 结构在 construction 组件里，掉落/复制天然保留整件规格 | 引用式需注意复制是否丢引用上下文 |
| 适用面 | 「同形状多材料」的装备（工具/武器/护甲） | 「同槽位多源块」的装饰方块组合 |

给「求仙问道」法宝系统的 2 条直接建议：
1. **把「法宝规格」拆成 *construction*（材质/部件列表）与 *properties*（算好的属性）两份数据**，照 `GearData.java:117-141` 写一条「修改即重算、结果回写、读取即命中」的管线，并在 `api` 暴露一个 `RecalculateEvent` 让别的 mod 注入加成——这是本仓库最该抄的工程骨架。注意 1.20.1 Forge 无 DataComponent，落地时把这两个组件降级为 ItemStack tag 的两个子 compound 即可，思想不变。
2. **外观走「少量通用贴图 + tint + 双缓存」而非「每材料一张贴图」**：做法宝直接照 `GearItemRenderer`（`builtin/entity` + BERL 逐层顶点色）与 `GearColorUtils` 的 model-key 颜色缓存。若目标停在 Forge 1.20.1，`getCustomRenderer()` BERL 与 tint-index 两条路都可用，只把 `UnbakedGeometryHelper`/`ItemProperties` 换回旧 API。

## 8. 公开 API（它是被 addon 依赖的库）

- 入口/扩展包：`net.silentchaos512.gear.api.*`（75 文件）。子包 `api/item`（`GearItem`/`GearType`/`GearTool`/`GearArmor` 接口，用 default 方法做 mixin 式基类）、`api/part`、`api/material`、`api/property`（`GearProperty`/`NumberProperty`/`ComputeContext`）、`api/traits`、`api/util`（`DataResource`/`PropertyKey`/`PartGearKey`/`PropertyProvider`）、`api/event`、`api/data/{material,part,trait}`（Builder + `*ProviderBase` datagen 基类）。
- 主要扩展点：
  1. **注册表**（addon 直接 `DeferredRegister` 进去）：`GEAR_TYPE`、`PART_TYPE`、`GEAR_PROPERTY`、`TRAIT_CONDITION`、`TRAIT_EFFECT_TYPE`、`MATERIAL_SERIALIZER`、`PART_SERIALIZER`、`MATERIAL_MODIFIER_TYPE`（`SG/setup/SgRegistries.java:35-60`，README `:7` 明示「addon 可加 part/gear/trait type」）。
  2. **数据驱动**：放 JSON 进 `data/<ns>/silentgear_materials|parts|traits/`，或继承 `MaterialsProviderBase`/`PartsProviderBase`/`TraitsProviderBase` 用 Builder 自建 datagen。
  3. **事件**：`GearRecalculateEvent.Pre/Post`、`GetPropertyModifiersEvent`、`GetMaterialPropertiesEvent`、`GetTraitsEvent`、`GearItemEvent`、`GearNamePrefixesEvent`（`SG/api/event/`）。
  4. **自定义材料增强**：注册 `IMaterialModifierType`（`SG/api/material/modifier/`，grade/charged/crude 皆其实现）。
- 引用式软依赖：跨数据引用一律用 `DataResource<T>`（`SG/api/util/DataResource.java`）按 `ResourceLocation` 存、延迟向对应 `DataResourceManager`/注册表解析，使 addon 材料可安全引用核心材料而不承担加载顺序问题。
- 接入方式：README `:25-95`——GitHub Packages 三个仓库（silent-gear / silentlib / silent-utils）+ 个人 `gradle.properties` 配 `gpr.username`/`gpr.token`；坐标 `net.silentchaos512:silent-gear-<mc>-neoforge:<ver>`（本仓库即 `silent-gear-1.21.1-neoforge`）。作为库它还 `maven-publish` sources + javadoc jar（`build.gradle:204-217`）。
