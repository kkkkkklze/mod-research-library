# 深挖报告：Domum Ornamentum —— 方块版「材质拼接」（1.21.1 NeoForge）

> 深挖对象：`domum-ornamentum-1.0.234-snapshot-main`（ATM10 包内版本）
> 源码：`源码库/_参考仓库/_pack_decompiled/All the Mods 10 - ATM10/domum-ornamentum-1.0.234-snapshot-main/`（CFR 反编译，**类/方法/字段名完整**，局部变量名有 CFR 痕迹）
> 原始 jar（含资源，报告里的 JSON 引文都从这里取）：`~/Documents/PCL\PCL2\.minecraft\versions\All the Mods 10 - ATM10\mods\domum-ornamentum-1.0.234-snapshot-main.jar`
> 体量：231 个 .java / 15,268 行（反编译后），另有 211 个 `_spec.json` 手写模型、139 条配方、32 个 tag 文件
> 下文路径缩写：`DO/` = `.../domum-ornamentum-1.0.234-snapshot-main/com/ldtteam/domumornamentum/`

---

## 0. 一句话结论

它把"材质"表达成**源方块引用**（`Map<部件id, Block>`），存在物品的 **DataComponent** 里；渲染时按"占位贴图的 sprite 名 = 部件 id"把内层模型的每个 quad **替换成源方块对应方向的 quad**（UV 重映射 + tint 打包 + 渲染类型并集），方块行为（硬度/音效/爆炸抗性/工具）则**全部委托给主部件**。于是：**一个装饰方块的代码只管形状，材质与手感全在数据里**，加材质＝写一个数据包 tag，零代码。

## 1. 数据模型：材质 = 源方块引用

```java
public record MaterialTextureData(Map<ResourceLocation, Block> getTexturedComponents)   // DO/client/model/data/MaterialTextureData.java:26
```

| 项 | 位置 | 要点 |
|---|---|---|
| 组件注册 | `DO/component/ModDataComponents.java` | `domum_ornamentum:texture_data`，`persistent(CODEC).networkSynchronized(STREAM_CODEC)` |
| Codec | `MaterialTextureData.java:28` | `Codec.unboundedMap(ResourceLocation.CODEC, BuiltInRegistries.BLOCK.byNameCodec())` |
| StreamCodec | `MaterialTextureData.java:29` | `ByteBufCodecs.map(HashMap::new, ResourceLocation.STREAM_CODEC, ByteBufCodecs.registry(Registries.BLOCK))` |
| 空值哨兵 | `:27,:31-33` | `EMPTY`（空 map）经 `fromCodec` 收敛为同一个实例，`isEmpty()` 因此可以走 `==` |
| 裁剪 | `:39-51` | `retainComponentsFromBlock(block)`：只保留目标方块**声明过的**部件（换形状时丢多余材质） |
| 物品读写 | `:76-86` | `writeToItemStack` / `readFromItemStack` / `updateItemStack(UnaryOperator)` |
| NBT 兼容 | `:53-74` | 已标 `@Deprecated(forRemoval, since="1.21")`，改用 Codec + `RegistryOps` |

**要点：`Map<部件id, Block>` 里存的是"方块"，不是颜色、不是贴图。** 贴图、染色、音效、硬度全部从方块再取一次——这是它能做到"任何方块都能当材质"的原因，也是容器化"材质包"的最短路径。

## 2. 部件（component）：id 就是占位贴图的资源位置

```java
// DO/block/decorative/TimberFrameBlock.java:59
public static final List<IMateriallyTexturedBlockComponent> COMPONENTS = ImmutableList.builder()
  .add(new SimpleRetexturableComponent(ResourceLocation.withDefaultNamespace("block/oak_planks"),  ModTags.TIMBERFRAMES_FRAME,  Blocks.OAK_PLANKS))
  .add(new SimpleRetexturableComponent(ResourceLocation.withDefaultNamespace("block/dark_oak_planks"), ModTags.TIMBERFRAMES_CENTER, Blocks.DARK_OAK_PLANKS))
  .build();
```

一个部件 = 三元组 `(id, 可选池 tag, 默认方块)`（`DO/block/components/SimpleRetexturableComponent.java:18-30`，另有 `optional` 开关给可空部件）。

**整个机制靠一条隐式约定成立**：部件 id 写成了 `minecraft:block/oak_planks` 这种**贴图资源位置**，而 `_spec` 模型里对应部位的 `textures` 值正是同一个 RL：

```jsonc
// jar: assets/domum_ornamentum/models/block/timber_frame/double_crossed_spec.json
"textures": { "frame": "block/oak_planks", "centre": "block/dark_oak_planks", "particle": "block/dark_oak_planks" }
```

于是重贴图时不需要任何映射表：`quad.getSprite().contents().name()` 直接等于部件 id（`RetexturedBakedModelBuilder.java:107-113`）。**抽查 27 个族的 211 个 spec 模型，贴图值只出现 `oak_planks / dark_oak_planks / acacia_planks / iron_block / glowstone / clay`，与代码里声明的默认方块一一吻合**（`door` 族的 `block/iron_block` 不是任何部件 id → 它是"固定装饰件"，走 pass-through，见 §4）。

**有效池 = tag**：25 个 block tag（`DO/tag/ModTags.java:15-43`），母池是 `domum_ornamentum:default`：

```java
// DO/datagen/global/GlobalTagProvider.java:32
tag(GLOBAL_DEFAULT).add(MOSS_BLOCK, CRACKED_POLISHED_BLACKSTONE_BRICKS, ... 90+ 个原版方块)
   .addTags(EXTRA_BLOCKS, Tags.Blocks.END_STONES, BRICKS, CONCRETE, COPPER, BlockTags.TERRACOTTA,
            BlockTags.WOOL, Tags.Blocks.STORAGE_BLOCKS, Tags.Blocks.GLASS_BLOCKS, BlockTags.LOGS,
            BlockTags.WART_BLOCKS, Tags.Blocks.STONES, Tags.Blocks.COBBLESTONES, Tags.Blocks.OBSIDIANS,
            BlockTags.STONE_BRICKS, BlockTags.BASE_STONE_NETHER);
```

各族池 = 母池 + 一个专属 tag，例：`DoorsComponentTagProvider.java:25` → `doors_materials = [default, minecraft:planks]`。
**→ 任何 mod / 数据包只要把自己的方块加进 `domum_ornamentum:doors_materials`，它立刻能当门材质。这是它真正的扩展点，零代码。**

## 3. 渲染链路：三段式 + 按材质重烘焙

**① 模型 JSON 只是壳子**（datagen 生成，`DO/datagen/frames/timber/TimberFramesBlockStateProvider.java:36`）：

```jsonc
{ "parent": "domum_ornamentum:block/timber_frame/double_crossed_spec", "loader": "domum_ornamentum:materially_textured" }
```

**② loader 只读 `parent`，烘出内层模型再包一层**（`DO/client/model/loader/MateriallyTexturedModelLoader.java:26-30`、`DO/client/model/geometry/MateriallyTexturedGeometry.java:28-35`）。datagen 侧对应 `MateriallyTexturedModelBuilder extends CustomLoaderBuilder`（`DO/datagen/MateriallyTexturedModelBuilder.java:11-16`）。

**③ 包一层"每次渲染按材质重建"的 BakedModel**（`DO/client/model/baked/MateriallyTexturedBakedModel.java`）：

| 机制 | 位置 | 说明 |
|---|---|---|
| 双缓存 | `:50-51` | Guava `Cache`，`expireAfterAccess(2min)`、`maximumSize(10000)`、`concurrencyLevel(4)`；键 = `record BlockModelCacheKey(MaterialTextureData, RenderType)`（`:231`），物品键再加 `BlockItemStateProperties`（`:234`）→ 靠 record 的**结构化相等**做键，不需要自建哈希 |
| 渲染类型并集 | `:63-73` | 取**所有源方块模型**的 `getRenderTypes` 与 solid 求并集 → 玻璃/半透明材质自动生效 |
| 渲染转发 | `:76-79` | `getQuads(..., ModelData, RenderType)` 按 `(材质, 渲染类型)` 取重建模型；物品侧 `getRenderPasses` 每个渲染类型包一层 `SpecificRenderTypeBakedModelWrapper`（`:150-168`） |
| 粒子图标 | `:103-116` | 若内层模型的 particle sprite 名恰好是某个部件 id，就用该源方块的粒子图标（草方块踩上去扬草屑） |
| 渲染类型归一 | `:207-229` | translucent → `Sheets.translucentCullBlockSheet()` / 物品 `translucentItemSheet()`；其余 → `cutoutBlockSheet()` |
| 失败兜底 | `:186-189` | 重建抛异常 → 记日志 + 返回 missing model（不崩） |

**④ 重建本身**（`DO/client/model/baked/RetexturedBakedModelBuilder.java`）：

- `with(部件id, Block)`：取源方块默认状态的 baked model，**先检查它是否支持本渲染类型**，不支持就 `withOut(部件id)`（`:60-73`）= 该部件整体擦除；
- `build()`：先处理 `side == null` 的 unculled 面，再逐 `Direction` 处理 culled 面（`:82-97`）——**与 vanilla `SimpleBakedModel.Builder` 的入参顺序一致**，不匹配的 quad 原样保留（`:85-87`，这就是"固定装饰件"如门的铁件）；
- 源 quad 选取：`getQuads(null, direction, ...)`（**状态传 null**）→ 空则退回源 quad 自己的方向（`:137-140`）；
- 粒子图标同样可被重贴图（`:98-103`）。

**⑤ UV 重映射 + tint 打包**（`DO/client/model/utils/ModelSpriteQuadTransformer.java:45-78`）：

```java
// 占位贴图 UV → 归一化 → 源贴图 UV（不要求两张图分辨率/UV 布局一致，只要求是"完整贴图"）
float u = (uv[0] - minU) / uDelta;  float newU = target.sprite.getU(u);
...
int color = getColorFor(target.state());          // 液体 tint / 物品色 / 白
if (0 <= tint && tint <= 255) { color = -1; tint = Block.getId(target.state()) << 8 | tint; }
if (color != -1) QuadTransformers.applyingColor(color).processInPlace(quad);
if (tint != -1)  quad.tintIndex = tint;           // ★ 把"源方块状态 id"塞进 tintIndex 高 24 位
```

**这条 tint 打包是全篇最值得抄的技巧**：重贴图后 quad 的染色回调需要一个"该用哪个方块的染色"的线索，它把源 `BlockState` 的注册 id 左移 8 位塞进 `tintIndex`，再由色处理器还原：

```java
// DO/client/color/MateriallyTexturedBlockBlockColor.java:20-30
int blockStateId = tintIndex >> 8;   BlockState containedState = Block.stateById(blockStateId);
int tintValue = tintIndex & 0xFF;
return Minecraft.getInstance().getBlockColors().getColor(containedState, level, pos, tintValue);
```

于是**草方块/树叶/水/火的生物群系染色、染料色、物品色全部原生生效**，一行染色表都不用写。物品侧同理（`DO/client/color/MateriallyTexturedBlockItemColor.java:24-37`，液体走 `IClientFluidTypeExtensions.getTintColor`）。注册是一次 varargs（`DO/client/event/handlers/RegisterColorHandlersEventHandler.java:20-27`）。

`IMateriallyTexturedBlock.usesWorldSpecificTinting()`（`:131-133`）决定是否把 `pos` 传给原版色处理器——需要生物群系采样的方块传 pos，与位置无关的传 null 以保留原版缓存。

## 4. 行为委托：手感跟着"主材质"走

`IMateriallyTexturedBlock:52-110` 四个 default 方法把方块行为整体转给主部件的源方块：

| 行为 | 读取处 | 效果 |
|---|---|---|
| `isCorrectToolForDrops` | `:52-65` | 用什么工具能挖下来，看主材质方块 |
| `getDOExplosionResistance` | `:67-80` | 抗爆性 = 主材质方块的抗爆性 |
| `getDODestroyProgress` | `:82-95` | 挖掘速度 = 主材质方块的挖掘速度 |
| `getDOSoundType` | `:97-110` | 脚步声/破坏音 = 主材质方块 |

主部件 = `getComponents().get(0)`（`TimberFrameBlock.java:139-141`）；各族方块在自己的 `getExplosionResistance/getDestroyProgress/getSoundType` 里把 `super::` 作为回调传进去（`TimberFrameBlock.java:126-136`）。**"石头框的木门"挖掘手感像木头——这是它"材质可信"的关键。**

## 5. 材质的生命线：物品 ↔ 方块 ↔ 存档 ↔ 客户端

```
建筑师切割机产出（组件写入 ItemStack）
   ↓ 放置 applyImplicitComponents          DO/entity/block/MateriallyTexturedBlockEntity.java:99-102
方块实体 textureData（含 retainComponentsFromBlock 归一化，:41-53）
   ├─ 存档  saveAdditional  CODEC+RegistryOps:NbtOps  :64-68
   ├─ 客户端 getUpdateTag / getUpdatePacket（整个 BE 同步）  :56-62
   ├─ 渲染  getModelData() → ModelProperty MATERIAL_TEXTURE_PROPERTY  :89-91
   └─ 掉落/复制 getCloneItemStack → BlockUtils.getMaterializedItemStack
                 → BE.saveToItem() → collectImplicitComponents → DataComponent  :104-107, DO/util/BlockUtils.java:42-59
```

- **数据组件是唯一真相**：`ModDataComponents.TEXTURE_DATA` 同时是物品序列化、网络同步、BE 存档的载体（`savedSynced`）。
- **空材质有兜底不是崩**：`updateTextureDataWith` 若拿到空数据 → `MaterialTextureDataUtil.generateRandomTextureDataFrom`（`:41-53`）。
- **随机/轮播材质**（`DO/util/MaterialTextureDataUtil.java:36-57`）：按 `(nonePausedTicks/20 + Σ方块注册id) % 池大小` 取值 → 每种方块步长不同，**创造物品栏里没材质的物品每秒换一个材质**（这是"看得到它支持哪些材质"的巧办法）；`IMateriallyTexturedBlock.getRandomMaterials()`（`:41-50`）是服务端的 `ThreadLocalRandom` 版本。
- **双高方块（门）**：`setPlacedBy` 里把物品组件**再写一遍给上方方块实体**（`DO/block/vanilla/DoorBlock.java:93-96`），保证上下半扇材质一致。

## 6. 建筑师切割机：一条配方覆盖整个组合空间

**这是"避免配方爆炸"的教科书做法。**

```jsonc
// jar: data/domum_ornamentum/recipe/dynamic_timberframe.json
{ "type": "domum_ornamentum:architects_cutter", "block": "domum_ornamentum:dynamic_timberframe", "count": 2 }
// 变体用组件表达（门的样式）：
{ "type": "domum_ornamentum:architects_cutter", "block": "domum_ornamentum:fancy_door",
  "components": { "minecraft:block_state": { "type": "creeper" } } }
```

- **配方不列材料，只列产物**（`DO/recipe/architectscutter/ArchitectsCutterRecipe.java:42`；`CODEC` 字段就三个：`block` / `count` / `components`）。
- `matches`：**逐槽**校验第 i 个槽的方块 ∈ 第 i 个部件的 tag（`:66-86`）→ 一个配方覆盖 `16 种木板 × 16 种……` 的全部组合。
- `assemble`：逐槽读方块 → `textureData.setComponent(部件id, 方块)` → 写进产物组件（`:88-117`）；槽位为空且部件 `optional` 则跳过；产物数量 `max(部件数, count)`。
- **配方自动生成**：`MateriallyTexturedBlockRecipeProvider` 遍历方块注册表，对每个 `IMateriallyTexturedBlock` 调它自己的 `buildRecipes`（`DO/datagen/global/MateriallyTexturedBlockRecipeProvider.java`）——各族声明自己的份数，如木框 `count(COMPONENTS.size()*2)`（`TimberFrameBlock.java:122-124`），门按 `DoorType.values()` 逐样式一条（`DoorBlock.java:113-117`）。全 mod 139 条配方。
- **容器槽位数 = 全局最大部件数**（`ArchitectsCutterContainer.java:51,77-89`），槽位的 `mayPlace` 调 `MateriallyTexturedBlockManager.doesItemStackContainsMaterialForSlot(slotIndex, stack[, 变体])`（`DO/block/MateriallyTexturedBlockManager.java:47-84`；最大部件数靠**扫描方块注册表一次性缓存**，`:35-44`）。
- **取件消耗**：`onTake` 只消耗**该产物方块声明的前 componentSize 个槽**（`:96-123`），创造模式不消耗；UI 是切石机式的"组 + 变体"两级按钮（`:139-156`）。
- ⚠️ **隐式契约**：部件集合的**顺序即槽位语义**（`getComponents().toArray()[slotIndex]`，`MateriallyTexturedBlockManager.java:81`）——调整部件顺序＝改变数据含义。

## 7. 唯一的特例：动态木框（连通驱动 + 48 部件）

`DO/entity/block/DynamicTimberFrameBlockEntity.java`（453 行，全 mod 最大文件）把"一个方块"拆成 **48 个部件角色**：`NORTH_UP`、`NORTH_EAST_CORNER`、`BOTTOM_SOUTH_CENTER`、`EAST_SOUTH_DOWN_CENTER`……（`:46-96`，**占位贴图借用羊毛/陶瓦/混凝土当唯一 id**）。

- `handleTextureMapping()`（`:205-257`）先把 48 个角色全部指向 frame 材质或 center 材质，其余指向 **`Blocks.AIR` = 擦除**；
- `refreshTextureCache()`（`:259-307+`）按 `DynamicTimberFrameBlock.Offset` 的连通位图（6 面 + 12 棱 + 8 角的开关）重算：相邻方向就删掉交叉的棱/角、把中段换成 center 材质；
- `saveToItem` **只存 `originalTextureData`（两种材质）**，不存展开后的 48 项（`:128-135`）→ 存档体积与"材质"概念解耦，展开是渲染期的派生。

**这正是你 修仙 mod「面为中心」模型的同一问题**（面/棱/角存在性由结构决定，材质由数据给），而且它给出了一个成熟解：**位图 + 从位图派生部件→材质映射**，比在存档里存"每个面的材质"更省。

## 8. 能直接抄到你工程里的做法

| # | 做法 | 出处 | 怎么用在你这里 |
|---|---|---|---|
| 1 | **材质 = 源方块引用**，不存颜色/贴图 | `MaterialTextureData.java:26` | 你的 `face/结构` 数据槽位可以照抄：`Map<面id, 类型id>`，渲染时再解析成贴图（和你"类型值是数字"的规范化思路一致） |
| 2 | **重贴图靠 sprite 名匹配 + UV 归一化重映射** | `RetexturedBakedModelBuilder.java:107-146`、`ModelSpriteQuadTransformer.java:45-62` | 如果你不想按"源方块"而想按"47 类型贴图"重贴图，这套 quad 替换/UV 换算逻辑可以**原样复用**（换成 `类型 → RL` 映射即可） |
| 3 | **tint 打包 `blockStateId << 8 \| tintIndex`** | `ModelSpriteQuadTransformer.java:63-77` + `MateriallyTexturedBlockBlockColor.java:20-30` | 你要做"贴了材质的方块还要正确染色"（生物群系/染料）时的唯一正解，直接借字段布局 |
| 4 | **渲染类型并集 + 不支持则擦除** | `MateriallyTexturedBakedModel.java:63-73`、`RetexturedBakedModelBuilder.java:60-73` | 半透明/发光材质混搭时的正确降级方式（不是强行渲染） |
| 5 | **缓存键用不可变 record + Guava 限容限时** | `MateriallyTexturedBakedModel.java:50-51,231-235` | 你以后写"按数据重建 baked model"的缓存直接照抄参数（10k / 2min / 4 并发） |
| 6 | **一条"部件化配方"**：`matches` 按 tag、`assemble` 写组件 | `ArchitectsCutterRecipe.java:42,66-117` | 你的炼丹/炼制若要"任意 N 种主料 → 一件成品"，这是避免配方表爆炸的模板 |
| 7 | **行为委托给主部件** | `IMateriallyTexturedBlock.java:52-110` | "贴了什么材质就像什么方块"：一举解决挖掘速度/音效/抗爆，不用自己配表 |
| 8 | **连通位图派生部件映射** | `DynamicTimberFrameBlockEntity.java:205-307` | 直接对上你的**面/结构层**：存档只存声明，几何与部件映射在运行期派生 |
| 9 | **DataComponent + `applyImplicitComponents/collectImplicitComponents`** | `MateriallyTexturedBlockEntity.java:99-107` | 1.21 里"方块实体数据 ↔ 物品数据"的唯一正道（比 1.20.1 的 NBT 手工搬运干净），你已有 `AspectProfile` 序列化，这里是对照实现 |
| 10 | **空数据有确定兜底（轮播随机材质）** | `MaterialTextureDataUtil.java:36-57` | "未指定就随机但稳定"这个形状，比"随机每帧变"或"报错"都更适合内容 mod |

## 9. 与你的 47 类型调色板管线怎么结合（三条路线，含代价）

- **路线 A（纯数据）**：给 47 个类型各造一个"代表方块"（贴图即该系贴图），照抄它的"部件 + tag"机制 → 任意装饰方块立刻吃 47 类型材质。**代价**：47 个方块 + 47 条 tag 条目（数据包能写，但方块要注册）。
- **路线 B（只抄渲染层）**：保留你的美术管线产物（mask+palette 生成的贴图），把重贴图来源从 `Block` 换成 `类型id → 贴图 RL`。**代价**：丢掉"行为委托"与"源方块的染色"（要自己写 tint 兜底），换来不用注册 47 个方块、贴图直接复用你已有的 206 张 PNG。
- **路线 C（只抄数据形状）**：材质槽位存 `类型id`，面/结构决定"哪个面允许贴哪种材质"（你的 `faces/` 数据包已有 `meets`/`contact_type`，加一列材质池即可）。
- **建议**：先 **C**（形状对上你现有结构层，改数据不改代码）→ 需要"材质可信的手感"时补 **A 的委托四件套**（不需要 47 个方块，只需要"类型 → 一个代表性原版方块"的映射表，例如 火→`Blocks.MAGMA_BLOCK`）；**B 留到你真的要做"任意方块可贴任意类型"时再上**。

### 三个必须知道的陷阱

1. **"id = 占位贴图 RL"是隐式契约**：抄它就必须接受"部件 id 占用 `minecraft:block/*` 命名空间"，或者**改成显式映射表**（部件 id → 占位 sprite），否则改一次贴图名就静默失效（匹配失败→原样保留，不报错）。
2. **部件顺序 = 槽位语义**：`getComponents().toArray()[slotIndex]` 是隐式 API，跨版本/跨族调整顺序会串材质。
3. **重建模型有数量上限**：每个 `(材质组合, 渲染类型)` 一份烘焙模型，缓存 10k 上限 + 2 分钟过期，是"内存 ↔ 重烘焙"的折中；材质种类越多（比如 47 类型 × N 面）越要提前算容量。

## 10. 未确认 / 遗留

- 上游源码未做交叉验证：`ldtteam/domum-ornamentum` 未克隆（本报告全部基于 CFR 反编译产物 + 官方 jar 资源）。**行号是反编译产物的行号**，与上游仓库行号可能不同。
- `_spec.json` 是否全为手写（样本里有 `"credit": "Made with Blockbench"`）以及 datagen 是否会覆盖它们：**未确认**。
- 「27 族贴图值 = 部件 id」是**抽查**（每族取一个 spec + 各族组件定义全量比对），未逐文件全量校验 211 个 spec。
- 动态木框 48 角色的**完整**映射规则（`:307` 之后）只读了前 100 行，棱/角的组合规则未逐条展开。
- 同团队相关项目（`BlockUI`、`Stylecolonies`、`Multi-Piston`）在 ATM10 包内也有源码，可作同作者的工程风格对照（见 `深挖待办清单.md` 第一梯队 #1 的"同族一起看"）。
