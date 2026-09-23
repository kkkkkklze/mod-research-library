# 专题：材质拼接 · 美术特效 · 复合效果 —— Tinkers' Construct / Tetra / Silent Gear 三家实现对比

> 分析对象（均已浅克隆到 `源码库/_参考仓库/_bulk/`）：
> - `SlimeKnights/TinkersConstruct` 分支 **1.20.1**（1966 java）
> - `mickelus/tetra` 分支 **1.20**（789 java）
> - `SilentChaos512/Silent-Gear` 分支 **1.21.1**（4.x，507 java / 2013 json）＋ 对照分支 **1.20.x**（3.x）
> 方法：三个子系统分头精读（草稿在 `Downloads/_mats/parts/`），关键论断由我二次核验（下文标 ✅ 的为实测确认）。
> 提醒：Silent Gear 仓库**不含任何 png**（贴图在美术侧分发），所以它的"材质拼接"分析以代码路径为准。

---

## TL;DR：三条技术路线

| | 贴图从哪来 | 颜色怎么上 | 多材质（复合） | 效果组合 |
|---|---|---|---|---|
| **Tinkers' Construct** | **灰阶母版 + 材质调色板 → datagen 逐像素重着色**，产出 **545 张贴图**（`src/generated/.../tool/parts/`）✅ | 颜色已烘进贴图，**主模型完全不 tint**（`tintIndex=-1`）；只有"材质无专属图"时才退回顶点色 tint | 每个部件独立选自己的生成贴图 → **多张贴图拼一个模型** | Modifier(本体+等级) / Hook(能力接口) / Module(可序列化实现) 三层，**链式叠加 + priority 排序 + 同名等级相加** |
| **Tetra** | 贴图**不生成**：加载期由 `material.textures` 顺序在 `availableTextures` 里挑一个文件名（如 iron→`metal`），拼成 `.../head/basic_shovel/metal` | **顶点色乘法 tint**（`ColorQuadTransformer` 写 COLOR），外加 `emission` 自发光、`renderLayer` 层序 | 多 module 分层拼贴图 + improvement **追加层**；盾牌走骨骼盒 armature | Effect / Improvement(同组互斥) / Hone / Gild / Glyph / Tweak / **Synergy(组合奖励)** + requirement 组合树 |
| **Silent Gear 4.x** | **不生成、不拼图**：`TextureType` 只剩两档 `HIGH_CONTRAST/LOW_CONTRAST` 通用模板，贴图路径在 `GearItemRenderer` 里**硬编码** | 全部靠**顶点色 tint**（alpha 强制 1.0） | 复合材质 = **MIXBOX 真颜料混色**算出一个颜色 → 套单一模板；**贴图层不含比例信息** | Trait **全数据驱动**（75 个 json、19 种 effect 类型、6 种 condition），同名等级求和后**按来源数摊薄** |
| （Silent Gear 3.x 旧版） | 材质 json 声明**层列表**（`main`: `[ {texture:main_generic_hc,color:#FF6189}, {texture:_highlight} ]`），并有**逐材质护甲贴图** `crimson_iron_layer_1.png` ✅ | 层内各自带 `color` | 同 4.x 思路（旧版靠 `PartTextureSet` 三档 + 材质层列表） | Trait 体系雏形 |

**一句话总结**：Tinkers 走"**把颜色烘进贴图**"（画质优先、成本高）；Tetra 走"**选中性贴图 + 顶点色 + 层**"（扩展性优先、每部件一层）；Silent Gear 4.x 走"**两档模板 + 顶点色**"（极致省资源、牺牲材质质感），并额外用第三方**颜料混色库**解决复合材质的配色。

---

## 一、材质拼接

### 1.1 Tinkers' Construct —— "灰阶母版 + 调色板 + datagen 生成"（最值得抄）

**链路**：美术只画 **30 张灰阶/单色基础图**（`src/main/resources/assets/tconstruct/textures/item/tool/parts/`）→ 每个材质在 json 里给一个**调色板/变换器** → datagen 做"材质 × 部件"笛卡尔积，**逐像素重着色**产出 545 张 png（含 10 个 `.mcmeta` 动画）✅。

- 生成器：`library/client/data/material/MaterialPartTextureGenerator.java`，装配点 `tools/TinkerTools.java:413`；输出命名 `<部件>_<材质ns>_<材质路径>.png`（`MaterialPartTextureGenerator.java:120`）——即 `bowstring_tconstruct_vine.png` 的由来。
- 变换器族（`library/client/data/spritetransformer/`，✅ 已核对存在）：
  - **`GreyToSpriteTransformer`**：建立"灰度 0-255 → 颜色或另一张贴图"的调色板；取像素最亮通道当灰度（`GreyToColorMapping.java:282`），在调色板上找最近两点插值（`:269`），最后按原图各通道相对灰度**比例缩放**（`scaleColor` `:287`）——**这一步保住了明暗层次与抗锯齿边缘**，是"灰阶母版"能用的关键。
  - `RecolorSpriteTransformer` + `IColorMapping`：7 档 palette（`000/063/102/140/178/216/255`，见 `iron.json`）。
  - 调色板条目可以是纯色，也可是**贴图**（把另一张贴图当颜料，`SpriteMapping` `GreyToSpriteTransformer.java:320`）。
  - `AnimatedGreyToSpriteTransformer` / `FramesSpriteTransformer`：逐帧调色 + `.mcmeta` → 动画贴图。
- **运行时三档优先级**（`MaterialRenderInfo.getSprite` `:53`）：① 材质专属生成图存在 → `color=-1`，**不 tint**；② 材质的 fallback 图（如 `head_metal`）存在 → 用 `vertexColor` tint；③ 都没有 → 基础图 + tint。
- 工具模型是**动态重烘焙**：`ToolModel.MaterialOverrideHandler` 实现 `ItemOverrides.resolve`，缓存键 `ToolCacheKey(materials, modifierData)`（`ToolModel.java:759,851`）；每个 `ToolPart` 按 NBT 里的材质下标独立取图、独立生成 quad（`.java:407-432`）→ **"木柄+铁头"= 两张生成贴图拼一个模型**。
- 装甲另走一条：`MaterialArmorTextureSupplier` → `TintedArmorTexture`，颜色在**渲染期**作为参数传入（`TintedArmorTexture.java:47`）。

### 1.2 Tetra —— "加载期选贴图名 + 顶点色 tint + 层序"

- **自定义模型加载器** `tetra:modular_loader`（`client/model/ModularModelLoader.java:19`）：物品 json 只声明 loader + display，**几何在渲染期按 NBT 动态烘焙**（`UnresolvedItemModel` 返回空壳 + ItemOverrides）。
- 材质如何决定外观（**加载期**完成）：`ModuleRegistry.expandMaterialVariants`（`:96-112`）→ `MaterialVariantData.combine` → `MaterialData.kneadModel` → **`GridTextureModelData.forMaterial`**（`:52-71`）：在 module 的 `extract.availableTextures`（如 `{crude, metal, shiny}`）里，按 `material.textures` 顺序取第一个可用名拼到 `location` 尾部；同时把 `tint` 设为 `material.tints.texture`（颜色名 → `ItemColors` 表，iron=`0xffffff`）。
- **tint 是顶点色乘法**（`ColorQuadTransformer.java:21-26` 写 COLOR），不是换贴图 → 同一张 `metal.png` 能被不同材质染成不同颜色；`inheritTint` 用哨兵色 `0x000000` 表示"继承父层 overlayTint"（`ItemColors.java:132`、`GridTextureModelData.java:83-90`）。
- **层叠规则**：module 先按自身 `renderLayer`(Priority) 稳定排序，major module = 基础 variant 模型 + **improvement 模型追加在后**（`ItemModuleMajor.java:406-409`）；层序数组下标越大越上层；`textures/item/module/<类型>/<部件>/<模块>/improvements/*.png` 就是改进层贴图（`_bevel`/`_shadow`/`_0..2` 表拆分或多帧）。
- 盾牌是例外：`modular/shield/*.json` 只声明 `parts`（origin/dimensions/rotation/uv）→ `ModularShieldModel.createLayer` 拼 ModelPart 树，走 BEWLR 渲染（`ModularShieldRenderer.java:73-114`）。
- 缓存：`ModularOverrideList` 缓存 1000 条/5 分钟；数据包重载时 `ModularModelLoader.clearCaches` 清空。

### 1.3 Silent Gear —— 4.x"两档模板 + 顶点色"，3.x"材质层列表"

**4.x（1.21.1，当前分支）**：
- 材质只剩 2 个外观字段：`MaterialDisplayData(name, namePrefix, color, mainTextureType)`，`TextureType` 仅 `HIGH_CONTRAST("hc")` / `LOW_CONTRAST("lc")`（✅ 与旧版对比后确认这是**大幅简化**）。
- "层"= 部件槽位：`GearItemRenderer.getPartTextureLocations`（`:66-167`）**硬编码** PartType→贴图（MAIN → `main_generic_hc` + 额外 `_highlight` 层；ROD → `rod_generic_*`；TIP → `tip_sharp`；SETTING → `adornment_generic`+`adornment_highlight`…）。highlight 是 **gearType 级通用图**，不是材质自定义。
- 运行时：`builtin/entity` + BEWLR（`GearItemRenderer.renderByItem:258-346`）→ 取 AtlasSprite → 生成 quad → **`renderColoredSprite` 用顶点色画**（alpha 强制 1.0 避免 cutout 掉面）；**全仓库无 `NativeImage`/`DynamicTexture`/拼接逻辑** → 不合成新贴图。
- 两级缓存：`QUADS_FOR_SPRITES_CACHE`（128 条/5min，**key 只有 sprite**，与材质无关）、`GEAR_COLOR_CACHE`（1000 条/5min，key = 构造部件模型键）→ 同一材质组合只算一次颜色。
- 缺失层回退：无 main 画白色 `main_generic_lc`、无 rod 画 `rod_generic_lc`…（`:272-325`，全部 `renderUncoloredSprite`）。

**3.x（1.20.x，对照）**——老式"材质层列表"确实存在（✅ 实测）：
- 材质 json 直接写层数组：`"main": [{"texture":"silentgear:main_generic_hc","color":"#FF6189"},{"texture":"silentgear:_highlight"}]`、`"main/fragment"`、`"rod/all"`、`"rod/part"` 等键 → 每个部件可配多张层贴图 + 各自颜色。
- `gear/part/PartTextureSet.java` 是三档枚举（`LOW_CONTRAST` / `HIGH_CONTRAST` / `HIGH_CONTRAST_WITH_HIGHLIGHT`），每档给出 PartType → `List<PartTextures>`；`client/model/PartTextures.java` 是层常量表。
- 且 3.x 有**逐材质护甲贴图**（`crimson_iron_layer_1.png`、`all_layer_1_overlay.png`）——即"材质自带的成品图"。

**演进解读（重要）**：SG 从 3.x 的"数据声明层 + 逐材质成品图"退到 4.x 的"代码硬编码两档模板 + 顶点色"，代价是**丢失材质质感差异**，收益是：① 任意第三方 mod 材质无需美术资源即可生效；② 仓库/包体不再背贴图（本仓库 0 png 即证据）；③ 渲染路径统一、无运行时合成开销。

---

## 二、复合效果

### 2.1 Tinkers：Modifier / Hook / Module 三层 + 链式叠加

- **三层结构**：`Modifier`（效果本体+等级）→ `Hook`（能力接口，按域分包 `hook/{build,combat,mining,armor,interaction,display,behavior,ranged,special}`，集中在 `ModifierHooks` 注册）→ `Module`（可序列化实现，`ModuleHook`/`ModuleHookMap`/`HookProvider`）。
- **叠加是链式的**（不是覆盖）：`ModuleHookMap.createMap`（`:33`）把多个 module 压成"hook→组合实现"（`ModuleHook.merge` + `AllMerger`），逐个串联；例：`ConditionalStatModifierHook.getModifiedStat` 里 `for (ModifierEntry entry : tool.getModifierList()) value = entry.getHook(...).modifyStat(..., value, multiplier)` —— **后一个能看到前一个的结果**，最后 `clamp`。
- **优先级**：`Modifier.getPriority()`（默认 100，**数字大者先执行**），`ModifierEntry.compareTo` 决定 tooltip 与钩子顺序；**同名多次添加 = 等级相加**（`ModifierNBT.Builder.add`）。
- **材质如何贡献效果**：`tinkering/materials/{definition,stats,traits}/*.json` 分工；`tool_definitions/*.json` 的 `part_stats` 模块按顺序列槽位，与 `MaterialStatsModule.statTypes` 一一对应。
- 未发现通用"互斥/排他"框架（`conflict` 只出现在配方层）——互斥要靠 modifier 自己实现 `ValidateModifierHook`。

### 2.2 Tetra：相加 / 覆盖双轨 + 组合协同 + requirement 树

- **Effect**：字符串键注册表（`ItemEffect.get` computeIfAbsent，内置 95 个常量），数值走 `EffectData extends TierData`（level + efficiency 双通道）。
- **合并语义（两套并存，按层区分）**：
  - `EffectData.merge`：**同 key 的 level 与 efficiency 相加**（跨 module 与 synergy 累加）。
  - `VariantData.merge` 走 `EffectData.overwrite`：**后写覆盖**（模块/变体/改进层是覆盖）。
- **Improvement（改进/镶嵌）**：`{key, level, group, enchantment}`；同 key 只生效 NBT 里 level 相符的那条；**同 `group` 互斥**（`removeCollidingImprovements`）；Hone（5 级进度）/Gild（镀金）都是同一机制的数据化用法；带视觉的改进通过 `models` **追加图层**。
- **Synergy（协同）**：`SynergyData` 要求 `modules`/`moduleVariants`/`improvements`/`sameVariant` 的组合，命中后其 attributes/effects 与模块同级参与合并（`IModularItem.java:950-978`）——**"套装奖励"的数据化实现**。
- **属性前缀语法**：key 以 `**` 开头 = MULTIPLY_TOTAL、`*` = MULTIPLY_BASE、无前缀 = ADDITION（`AttributesDeserializer.java:21-24`）；合并时 `AttributeHelper.collapseRound` 把 MULTIPLY_BASE 折算进 ADDITION 并保留一条 MULTIPLY_TOTAL —— 让"按基础值百分比放大"（hone 的 flat/mult 两种成长曲线）成立。
- **requirement 组合树**：`AndRequirement`/`OrRequirement`/`NotRequirement` + `ModuleRequirement`/`HasImprovementRequirement`/`AspectRequirement`/`SlotRequirement`（`module/schematic/requirement/`）——hone_1..5 的"必须已有上一级"就是它实现的。
- 新方向：`data/tetra/item_effects/*.json`（trigger on_use/on_hit/on_mine_block…）用 provider+condition+outcome 表达式描述效果，**不写 Java** 也能加效果。

### 2.3 Silent Gear：复合材质 = 颜料混色 + 等级"摊薄"

- **比例编码**：复合产物是 `CompoundMaterialItem`，`MATERIAL_LIST` 里**同一材质放 N 次就是 N 份**（`create(materials, materials.size())`）。
- **颜色**：`CompoundMaterial.getColor` → `GearColorUtils.getBlendedColorForCompoundMaterial` → `ColorUtils.blend(ColorBlendAlgorithm.MIXBOX, colors)` —— **MIXBOX 真颜料减色混色**（`com.scrtwpns:mixbox:2.0.0`，✅ build.gradle:41 实测；shadowJar 打包并 relocate 到 `shadow.silentgear.scrtwpns`，build.gradle:44-51）。同一算法还用于调色板混合与喷漆配方。
- **贴图**：复合材质**不覆写** `getMainTextureType()`，沿用自己 json 的 HC/LC 模板 → **贴图层完全没有比例信息**；外观 = "混出 1 个颜色 + 1 张模板 + 顶点色"。
- **Trait 数据驱动（最成熟的一套）**：`Trait.CODEC = {max_level,name,description,effects[],conditions[],extra_wiki_lines[]}`，从 `data/<ns>/silentgear_traits/*.json` 加载（本仓库内置 75 个）；**effect 19 种、condition 6 种**由代码注册表 dispatch（`TraitEffectTypes`/`TraitConditions`）。
- **叠加与摊薄**（`TraitListProperty.computeTraits:78-115`）：
  ```java
  map.merge(trait, level, Integer::sum);              // 同名 trait 等级求和
  count.merge(trait, 1, Integer::sum);
  final float divisor = Math.min(traits.size() / 2f, matsWithTrait);
  final int value = Math.round(map.get(trait) / divisor);
  map.put(trait, Mth.clamp(value, 1, trait.getMaxLevel()));   // 钳到 max_level
  ```
  → **来源越多、总条目越多，等级被除权**，专门防"多材质堆叠刷等级"，这就是"复合效果"的平衡核心。
- 触发钩子表齐全（onAttackEntity/onEntityIncomingDamage/onDurabilityDamage/onGetAttributeModifiers/onItemUse/onItemSwing/getMiningSpeedModifier/onUpdate/addLootDrops…，实现为 `TraitEffect` 的 11 个方法）。
- 缺口：`TraitHelper.cancelTraits()` 整段被注释 → "trait 相克"在本分支不可用。

### 2.4 三方对比（复合效果）

| 维度 | Tinkers | Tetra | Silent Gear 4.x |
|---|---|---|---|
| 多来源合成语义 | **链式**（后者读前者结果） | **相加**（effect）/ **覆盖**（variant）双轨 | **求和后摊薄** + 钳 max_level |
| 优先级/互斥 | priority 数字大者先；无通用互斥 | Priority 排序；improvement **同 group 互斥** | 无优先级（插入序）；靠摊薄防超模 |
| 比例/权重表达 | 无（每个部件独立材质） | 无（每部件覆盖） | **重复条目**编码比例 |
| 组合奖励 | 部分 trait 依赖槽位材质 | **Synergy 数据化套装奖励** | condition（and/or/not + material_count/ratio） |
| 数据驱动程度 | 数值/绑定在 json，行为在 Java | 数值/层/材料在 json，**新效果可纯 json** | **Trait 完全 json**，effect 类型在 Java |

---

## 三、美术特效

| | Tinkers' Construct | Tetra | Silent Gear 4.x |
|---|---|---|---|
| 自发光 | `MaterialRenderInfo.luminosity`(0-15) → `TintedSprite.emissivity`；装甲直接把 packedLight 抬到 (15,15) | `emission` → `QuadTransformers.settingEmissivity`（如宝石孔 emission 4、碎裂层 emission 8） | 充能材质直接 `ENCHANTMENT_GLINT_OVERRIDE=true`（`ChargedMaterialModifier`） |
| 附魔光效 | 装甲 `getArmorFoilBuffer(hasGlint)` | 改进的 `enchantment` 字段控制光泽 | `hasEffect()` 统一入口，**配置默认关闭**（注释称原版实现有 bug） |
| 自定义粒子 | 仅 `AttackParticle`/`SlimeParticle`（复用原版） | **最多**：扫光弧 `SweepingStrikeParticle`（自绘 quad + 自定义 RenderType + 左右交替）、追踪火花、血/史莱姆滴落、sculk 蔓延、回响；**json 驱动粒子效果**（`item_effects/*.json` + `ParticleItemEffectOutcome`） | 无粒子特效（grep gradient/sparkle/shimmer 零命中） |
| 渲染模型增强 | modifier 视觉模型族：Dyed / Fluid / Tank / Trim(纹样) / Banner / Potion / Conditional / MaterialHasFallback（两套模型切换） | 层叠 + 顶点色 + 盾牌 armature + 投掷自旋（`ThrownModularItemRenderer` 按 tick 自旋，盾牌 100°/s） | 拉动/蓄力状态层（`_1/_2/_3` 变体）、油漆覆盖材质色、破损换 `empty.png` |
| HUD/GUI | 书内材质章节、修饰列表 | **hone 进度条 + toast + 能力条（charge/combo/revenge/focus）** | 等级仅文本（`[C]`、DEEPSKYBLUE 行）；耐久条 HSV 从绿到红 |
| 品质视觉 | 无（同级不换贴图） | 抽奖式：`aspects.honed` 数值 + 金色进度反馈 | 等级 **不改变贴图/颜色**，只加文本 |

**小结**：美术特效投入 Tetra ≫ Tinkers > Silent Gear 4.x。Tetra 把"效果→视觉"做成了系统（粒子 provider + json outcome + HUD 体系）；Tinkers 的视觉贡献主要在 modifier 模型族与材质自发光；SG 4.x 基本放弃视觉表现（只剩 tint/glint/文本）。

---

## 四、对你自己项目（修仙 mod / 47 类型调色板 / 复合效果）的启示

1. **材质数量 × 美术产能决定路线**：
   - 材质少而精、要画质 → **Tinkers 路线**（灰阶母版 + 调色板 datagen）；代价是每种材质要配一份 palette + transformer。
   - 材质多、期望第三方 mod 材质自动生效 → **SG 4.x 路线**（两档模板 + 顶点色）；代价是丢失质感差异。
   - 部件 × 材质组合多、要层叠覆盖 → **Tetra 路线**（选贴图名 + 顶点色 + improvement 层）。
2. **最该抄的两个具体机制**（都与你的现状对得上）：
   - **`GreyToSpriteTransformer`**（灰阶母版 → 调色板最近两点插值 → 按原图通道比例缩放保明暗）：这正是你美术生产线"灰阶母版 + palette + 47 类型"的**自动化版本**，可用 datagen 展开"类型 × 部件"全组合，只在需要时回退顶点色 tint。
   - **SG 的摊薄公式 + 同组互斥**（`TraitListProperty.computeTraits` + Tetra 的 `group`）：解决"复合/多来源叠出超模词条"，比单纯 cap 更优雅。
3. **复合效果三种语义，按用途挑**：
   - 数值成长（你要的"功法/心术叠加"）→ Tetra 式 **相加**；
   - 同槽位替换（换功法）→ Tetra 式 **覆盖**；
   - 多材质混合的平衡 → SG 式 **求和 + 摊薄 + 钳上限**；
   - 组合奖励（成套）→ Tetra 的 **Synergy**（数据化条件匹配）比写死 Java 强。
4. **顶点色 tint vs 烘焙贴图**的取舍表（可直接用于你的 47 类型决策）：
   | | 烘焙贴图（Tinkers） | 顶点色 tint（Tetra/SG） |
   |---|---|---|
   | 画质 | 最高（明暗/纹理保真） | 中（同一明暗分布，靠色相区分） |
   | 包体 | 大（545 png） | 小（几张模板） |
   | 新材质成本 | 需 palette + 一次 datagen | **零资源**（给个颜色即可） |
   | 与"高级系=复合效果"的契合 | 高（每个高级类型可独立调色板） | 低（只有色相差异，需叠加层补效果） |
5. **你们的"两套方案"建议**：主力类型走 **Tinkers 式调色板 datagen**（你已经有 palette 生产线，边际成本最低）；对"允许第三方扩展的类型"留一条 **SG 式两档模板 + 顶点色** 的兜底路径——这正是 Tetra/SG 各自妥协后仍保留的东西。

---

## 五、溯源与未确认项

- 源码位置：`源码库/_参考仓库/_bulk/{SlimeKnights__TinkersConstruct, mickelus__tetra, SilentChaos512__Silent-Gear}`；三份精读草稿在 `Downloads/_mats/parts/{tinkers,tetra,silentgear}.md`（本报告在其事实基础上重写为对比形式，并做了二次核验）。
- ✅ 本文已实测核验：Tinkers `spritetransformer` 包与 `RecolorSpriteTransformer`/`ISpriteTransformer` 存在、生成贴图 545 png + 10 mcmeta、`MaterialPartTextureGenerator` 装配点；Silent Gear `com.scrtwpns:mixbox:2.0.0` + shadowJar relocate、4.x `TextureType` 仅两档、3.x 的 `PartTextureSet` 三档与材质 json 层列表、逐材质护甲贴图存在。
- **未确认**：Tinkers 的 `emissivity` 底层光照覆写（在 Mantle 库内，本仓库未见）；Tinkers 是否有"按 tier 换贴图"（未发现）；Tetra 的 `TWF`/粒子细节未逐帧验证；Silent Gear 4.x 的 `getColorWeight` 为遗留死代码（无调用方，是否计划恢复未知）；SG 3.x→4.x 的具体决策记录（无 changelog 佐证，属推断）。
