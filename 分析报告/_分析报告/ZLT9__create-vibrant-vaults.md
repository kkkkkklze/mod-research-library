# ZLT9/create-vibrant-vaults 源码分析报告

## 1. 基本信息

| 项 | 值（来源） |
|---|---|
| Mod 名 / mod_id | Create: Vibrant Vaults / `create_vibrant_vaults`（`CreateVibrantVaults.java:18`） |
| 版本 / group | `0.3.2` / `net.zlt`（`gradle.properties`） |
| 目标 MC / 加载器 | **1.20.1 / Fabric**（fabric-loom `1.10.+`，Java 17 —— 见 `mixins.json` 的 `JAVA_17`） |
| 作者 | 仓库内**无 authors 字段**（`fabric.mod.json` 不在快照内），仅能从包名 `net.zlt` 推断，**未确认** |
| 许可证 | **未确认**：`build.gradle` 的 `jar { from("LICENSE") }` 引用 LICENSE，但仓库内无该文件 |
| Fabric 依赖 | loader `0.17.2`、fabric-api `0.92.6+1.20.1`、Parchment `2023.09.03` |
| 关键编译依赖 | **Create Fabric `6.0.8.1+build.1744-mc1.20.1`**（`com.simibubi.create:create-fabric`，mvn.devos.one）→ 传递带入 **Registrate / Flywheel / Ponder / Porting Lib**；开发期 recipe viewer 可选 JEI/REI/EMI（本仓库设 `emi`），Mod Menu 7.1.0 |

## 2. 源码规模与包结构

实测：**60 个 `.java`，4271 行**。
- `mixin` **25 个**（common 16 含 `accessor/IWrenchableAccessor`，client 9）
- `block` 10（ModBlocks、ItemVaultConnectivityHelper、ModBlockTags、5 个 Vibrant*Block）
- `data` 9（Datagen / TagProvider / RecipeProvider / CreateSplashingRecipeProvider / LangProvider / CompositeModelBuilder / 2 个 BlockStateGenerator）
- `item` 4 + `item/crafting` 3（ModRecipeSerializers、VaultColoringRecipe、VaultRotatingRecipe）
- `duck` 3、`ct` 3、`client` 2

最大文件：`block/ItemVaultConnectivityHelper.java` 410、`block/ModBlockTags.java` 362、`item/ModItemTags.java` 361、`data/CreateVibrantVaultsTagProvider.java` 338、`block/ModBlocks.java` 308、`data/CreateVibrantVaultsRecipeProvider.java` 203、`data/CreateVibrantVaultsDatagen.java` 188、`mixin/ItemVaultBlockEntityMixin.java` 100。

## 3. 入口与注册

`CreateVibrantVaults implements ModInitializer`（Fabric），注册框架仍用 **Create 的 `CreateRegistrate`**：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(ID);
public void onInitialize() {
    ModBlockTags.init(); ModItemTags.init(); ModCreativeModeTabs.init();
    ModBlocks.init(); ModSpriteShifts.init(); ModRecipeSerializers.init();
    REGISTRATE.register();
    ModInventoryIdentifiers.init();
}
```

客户端 `CreateVibrantVaultsClient implements ClientModInitializer`（仅 `ModPartialModels.init()`）；datagen 入口 `data/CreateVibrantVaultsDatagen implements DataGeneratorEntrypoint`。（`fabric.mod.json` 缺失，entrypoint 声明本身未确认。）配方序列化器手工注册：`Registry.register(BuiltInRegistries.RECIPE_SERIALIZER, asResource("crafting_special_vaultcoloring"), new SimpleCraftingRecipeSerializer<>(VaultColoringRecipe::new))`（`item/crafting/ModRecipeSerializers.java`）。

## 4. 核心系统

**① 颜色 × 形态 的方块矩阵注册 —— `block/ModBlocks.java`**
- 枚举 `VibrantVaultColor`（16 个 DyeColor + `BASE`）与 `VibrantVaultType`（ITEM_VAULT / SHIPPING_CONTAINER / BASIC_SHIPPING_CONTAINER）；用**二维 List 索引**代替 map：`VIBRANT_VAULTS.get(type.ordinal()*2 + (vertical?1:0)).get(color.ordinal())`（:112-136）。
- 命名规则在注册时计算：`String blockName = color == BASE ? typeId : colorId + "_" + typeId`（:163）；方块类只是数据载体：`VibrantVaultBlock extends ItemVaultBlock`，字段 `type`/`color`（`VibrantVaultBlock.java`），Packager/Frogport/StockLink/RedstoneRequester 同构。
- 方块模型在注册链里内联声明：`.blockstate(vibrantVaultBlockState(...))` 用 `p.getVariantBuilder().forAllStates(...)` 基于 Create 原版模型改贴图键（:138-158）。

**② 多方块连通重写 —— `block/ItemVaultConnectivityHelper.java`（本仓库最核心，410 行）**
- 自定义连接判定：`isVault(Block a, Block b)` —— Create 原版 vault 之间互通，本 mod 的彩色 vault **只有同种方块才相连**（:35-45）。
- 自实现多方块成型搜索：`formItemVaultMulti` 用 `PriorityQueue<Pair<Integer,T>>`（按可成型格数降序）+ `SearchCache` 缓存 + 边界 `minX/minY/minZ` 剪枝（:298-371）；`tryToFormNewItemVaultMultiOfWidth` 逐个宽度试探取最优（:262-296）。
- 支持**垂直 vault**：靠交换 width/height 语义（`getMaxLength(axis,width)` 与 `getMaxWidth()` 互换），并处理 controller 位置约束（:183-215）。
- 接入方式全是 mixin `@Redirect`（见 §6），即"不改 Create 源码、替换其连通算法"。

**③ 与 Create 其它子系统的"贴皮"扩展**
- `item/ModInventoryIdentifiers.java`：遍历所有彩色 vault，用 Create 公开 API 注册库存标识 —— `InventoryIdentifier.REGISTRY.register(vault.get(), (level,state,face) -> level.getBlockEntity(face.getPos()) instanceof ItemVaultBlockEntity be ? be.getInvId() : null)`（:15-21）。
- `duck/` 3 个接口 + mixin 实现的 **duck interface 模式**：`ItemPredicateMixinDuck`（给原版 `ItemPredicate` 挂 `createVibrantVaults:ingredient` 字段：`matches` 里提前 return false、`fromJson`/`serializeToJson` 读写自定义 key，配 accesswidener 打开 `ItemPredicate$Builder.<init>`）、`FactoryPanelBlockEntityRenderDataMixinDuck`（把 `restockerColor` 塞进面板的 `RenderData`，随 `read/write` 的 clientPacket 同步）、`ModelBuilderMixinDuck.uncheckedTexture`（datagen 阶段绕开贴图存在性校验，见 §5）。
- `ct/` 连接纹理：`HorizontalVaultCTBehaviour` / `VerticalVaultCTBehaviour` + `ModSpriteShifts`，注册链里 `connectedTextures(...)`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自建包**（未使用 Payload/通道注册）；跨端同步走 Create `BlockEntity.write/read(..., boolean clientPacket)`（如 `FactoryPanelBlockEntityMixin` 的 restockerColor）与 Create 的菜单数据。
- **配置：无**（无 Config 类）。
- **数据驱动（本项目最值得学的部分）**：
  - Fabric datagen 与 Registrate 对接：`REGISTRATE.setupDatagen(pack, ExistingFileHelper.withResourcesFromArg())`，再按 `ProviderType` 逐个挂生成器（LANG / BLOCKSTATE / BLOCK_TAGS / ITEM_TAGS），配方用 `pack.addProvider(RecipeProvider::new)`（`data/CreateVibrantVaultsDatagen.java:23-37`）。
  - **程序化生成模型**：直接 `provider.models().getBuilder(...).parent(new ModelFile.UncheckedModelFile(Create.asResource("block/packager/block"))).texture("0", ...)`，把 Create 原版模型的贴图键重新指向彩色贴图，一次循环生成 16 色 × N 种部件的全部模型 JSON（:53-187）。
  - **缺贴图键时的兜底**：`((ModelBuilderMixinDuck<BlockModelBuilder>) builder).createVibrantVaults$uncheckedTexture("3", Create.asResource("block/packager_iris_closed"))` —— mixin 给 ModelBuilder 加"不检查存在性"的 texture 方法（:88、:143）。
  - 语言文件也程序化：读 `assets/create_vibrant_vaults/lang/default/interface.json` 后用 `FilesHelper.loadJsonResource` 批量灌入 Registrate 的 LANG provider（:39-51）。
  - `data/CompositeModelBuilder.java`：**从 Forge 移植**的 `CustomLoaderBuilder`（`PortingLib.id("composite")`），产出 `children` + `item_render_order` 的 composite 模型，用于彩色物品的多层模型。
  - `VibrantPackagerBlockStateGenerator` / `VibrantStockLinkBlockStateGenerator extends SpecialBlockStateGen`：按 `LINKED/POWERED/FACING` 组合返回不同 parent 模型。

## 6. Mixin

配置：`src/main/resources/create_vibrant_vaults.mixins.json`（common 16 + client 9，`defaultRequire: 1`）+ **accesswidener** `create_vibrant_vaults.accesswidener`（`extendable method net/minecraft/advancements/critereon/ItemPredicate$Builder <init>()V`）。全程使用 **MixinExtras**（`@ModifyExpressionValue` / `@WrapOperation` / `@Local` / `@ModifyReturnValue`）。
代表性 hook：
- `ItemVaultBlockEntityMixin` → `@Redirect` 掉 `removeController`/`notifyMultiUpdated` 中的 `ItemVaultBlock.isVault(BlockState)`、`updateConnectivity` 中的 `ConnectivityHandler.formMulti`、`initCapability` 中的 `ConnectivityHandler.partAt`；`@WrapOperation` 改 `getMaxLength` 内的 `getMaxWidth()/getMaxLength(int)`（垂直 vault 关键）；`@Inject(HEAD, cancellable)` 重写 `updateComparators`（因为垂直多方的 comparator 更新顺序不同）。
- `ItemVaultBlockMixin` / `ItemVaultItemMixin` → 改 `onWrenched`/`onRemove` 的 `splitMulti`、`getVaultBlockAxis`、`isLarge`、`tryMultiPlace` 的 `BlockPos.offset`。
- `BlockEntityTypeMixin` → `@ModifyReturnValue isValid(RETURN)`，让彩色方块复用 Create 的 BlockEntityType。
- 大量"把 `AllBlocks.XXX.has(state)` 改成也认我的方块"型 hook：`PackagerBlockEntityMixin`/`PackagerBlockMixin`/`ChainConveyorBlockMixin`/`ChainConveyorInteractionHandlerMixin`/`RedstoneRequesterBlockMixin`/`AllArmInteractionPointTypesPackagerTypeMixin`/`FactoryPanelBlockEntityMixin`/`FactoryPanelConnectionHandlerMixin`/`PackagePortTargetSelectionHandlerMixin`。
- 客户端：`FrogportRendererMixin`/`FrogportVisualMixin`/`PackagerRendererMixin` 用 `@ModifyExpressionValue` 替换 `AllPartialModels.FROGPORT_BODY/HEAD/TONGUE/PACKAGER_TRAY_*` 字段以换色；`client/AllCreatePonderScenesMixin` 在 `AllCreatePonderScenes.register`(TAIL) 追加自己的 ponder 场景；`client/ModelBuilderMixin` 提供上述 `uncheckedTexture`。

## 7. 值得学的 5 条做法

1. **"枚举 × 枚举 → List 索引"批量注册同质方块**（`ModBlocks.java:112-136`、:242-304），命名规则集中在一处计算；新增颜色只需改枚举，注册、贴图路径、tag、配方全部自动跟随。
2. **不改上游源码地替换其核心算法**：把 Create 的 `ConnectivityHandler.formMulti/splitMulti` 用 `@Redirect` 换成自己的 `ItemVaultConnectivityHelper`（`mixin/ItemVaultBlockEntityMixin.java:49-52`、`block/ItemVaultConnectivityHelper.java`）——做"Create 方块子类化但保留多方块行为"时最省事的路线。
3. **duck 接口 = "给上游类加字段"的安全做法**：`@Unique` 字段 + 接口暴露 getter/setter（`mixin/ItemPredicateMixin.java`、`duck/ItemPredicateMixinDuck.java`），需要时再配 accesswidener 打开构造器，比 `@Shadow` 猜字段稳定。
4. **datagen 里直接继承上游模型并替换贴图键**，配 `uncheckedTexture` 绕过校验（`data/CreateVibrantVaultsDatagen.java:53-187`）——做"换色/换皮 addon"时能省掉整套模型文件。
5. **用 tag 而不是硬编码方块表对外暴露扩展点**：`ModBlockTags`（`VIBRANT_VAULTS` / `HORIZONTAL_VAULTS` / `VERTICAL_VAULTS` / 16 个颜色 tag）既驱动自身逻辑（`isVault` 判断全走 tag：`ItemVaultConnectivityHelper.java:24,28,40`），也让外部 addon 能靠 tag 兼容。

## 8. 公开 API

非库/前置 mod。对外可用的扩展点主要是**数据侧**：`create_vibrant_vaults:vibrant_vaults` 等方块/物品 tag 家族（`block/ModBlockTags.java`、`item/ModItemTags.java`），以及 Create 公开的 `InventoryIdentifier.REGISTRY`（`item/ModInventoryIdentifiers.java`）与 Create 原生气泡式 API。`duck` 包接口仅供本 mod 与 mixin 间通信，**非对外 API**。
