# talrey/CreateDeco — Create Deco

## 1. 基本信息

- Mod 名：Create Deco；mod_id `createdeco`；作者 Kayla, Talrey, Ordana, Cassian
- 目标：MC 1.21.1 / NeoForge 21.1.209（`gradle.properties`：`minecraft_version=1.21.1`、`neo_version=21.1.209`、`loader_version_range=[1,)`）；Java 21
- Gradle：ModDevGradle `net.neoforged.moddev 2.0.107`（`build.gradle:4`），Parchment `2024.11.17`
- 许可证：All Rights Reserved（`gradle.properties:mod_license`），mod 版本 2.1.2，group `com.github.talrey.createdeco`
- 元数据同样走 `src/main/templates` + `generateModMetadata`（`build.gradle:127-149`），datagen 输出目录 `src/generated/resources`（`build.gradle:85,115`）
- 依赖（`build.gradle` dependencies 段）：Create `6.0.7-159`（`create-1.21.1:...:slim` 且 `transitive = false`）、Ponder `1.0.64`、Registrate、Flywheel（api compileOnly / 实现 runtimeOnly）、JEI。**纯装饰性下游附属**，无自带 API 暴露

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` → 48；`wc -l` 合计 5741 行。是三个仓库里最小的一个，适合通读。

包（第 2-3 层）：`com/github/talrey/createdeco/api`(18)、`blocks`(13)、根包(6)、`items`(5)、`connected`(3)、`mixin`(1)、`forge`(1)、`events`(1)。

最大文件：`BlockStateGenerator.java`(722)、`api/Bricks.java`(431)、`BlockRegistry.java`(416)、`blocks/CatwalkRailingBlock.java`(265)、`api/Catwalks.java`(223)、`blocks/ShippingContainerBlock.java`(207)、`blocks/CatwalkStairBlock.java`(191)、`blocks/SupportWedgeBlock.java`(185)、`blocks/CageLampBlock.java`(180)、`api/Windows.java`(162)。

## 3. 入口与注册

**双类分离**：加载器入口 `forge/CreateDecoModForge.java:9-16` 只有 7 行——

```java
@Mod(CreateDecoMod.MOD_ID)
public class CreateDecoModForge {
    public CreateDecoModForge(IEventBus eventBus) {
        CreativeTabs.register(eventBus);
        CreateDecoMod.REGISTRATE.registerEventListeners(eventBus);
        CreateDecoMod.init();
    }
}
```

平台无关部分在 `CreateDecoMod.java:13-18`：`REGISTRATE = CreateRegistrate.create(MOD_ID)`，`init()` 只调 `ItemRegistry.init(); BlockRegistry.init();`。所有注册都在静态初始化（类加载时）完成，没有 DeferredRegister（唯一例外是 `CreativeTabs.java:16` 的两个创造模式标签页 `props_tab` / `bricks_tab`）。

注册组织方式是**"材质/颜色 × 方块族"的 HashMap 表**：`BlockRegistry.java:49-86` 声明 25+ 个 `HashMap<String, BlockEntry<...>>`（`BRICKS/STAIRS/SLABS/WALLS/WINDOWS/CATWALKS/HULLS/SUPPORTS/FACADES/COIN_BLOCKS/SHIPPING_CONTAINERS`…），`BlockRegistry.init()`（`:95-110`）用 `ItemRegistry.METAL_TYPES.forEach(BlockRegistry::registerBars)` 之类的循环批量注册各族方块——加一种金属只需在 `ItemRegistry.METAL_TYPES`（`ItemRegistry.java:39-45`，`HashMap<String, Function<String, Item>>`）加一行。

## 4. 核心系统

**a) 每个方块族一个 `api/*` 构建器**（本仓库最有价值的结构）。`api/Catwalks.java`、`Bars`、`Bricks`、`Windows`、`SheetMetal`、`ShippingContainers`、`Doors`、`Ladders`、`Hulls`、`Supports`、`Wedges`、`Facades`、`Decals`、`CageLamps`、`Coins`、`Placards`、`MeshFences` 各暴露 `public static BlockBuilder<X,?> build(CreateRegistrate reg, String metal)`，把该族方块的 properties、loot 表、tag、renderLayer、BlockItem、blockstate/model、配方、connected texture 一次性写进一条 Registrate 链（`api/Catwalks.java:40-75`）。扩展点清晰：新增装饰只需复制一个 api 类。

**b) 程序化 blockstate/model 生成** `BlockStateGenerator.java`（722 行，全静态方法）。例如 `bar(...)`（`:31-78`）用 `MultiPartBlockStateBuilder` 以 vanilla `iron_bars_*` 为父模型生成直杆/侧杆/末端杆的组合条件（`model.conditions.put(BlockStateProperties.NORTH, false)` 等），支持叠加第二层贴图；同文件还有 `catwalkItem/windowPane/container` 等生成器，由 api 类通过 `.model((ctx,prov)-> BlockStateGenerator.xxx(...))` 调用。避免了 25×N 个手写 json。

**c) Connected Textures 集成** `connected/`。`SpriteShifts.java:20-28` 用多张 `HashMap<..., CTSpriteShiftEntry>`（含 `Couple<CTSpriteShiftEntry>` 的 `VAULT_TOP/FRONT/SIDE/BOTTOM`）集中管理 CT 贴图位移；`CatwalkCTBehaviour extends SimpleCTBehaviour` 只覆写 `connectsTo`（仅垂直面 + 同方块，`connected/CatwalkCTBehaviour.java:16-18`）并提供 `Supplier<ConnectedTextureBehaviour> getSupplier()` 供 Registrate 使用；注册点在 api 类里：`CreateRegistrate.connectedTextures(...)`（`api/Catwalks.java:72-73`、`api/ShippingContainers.java:59`、`api/Windows.java:80-81`、`api/SheetMetal.java:39-40`，后两者复用 Create 自带的 `HorizontalCTBehaviour/GlassPaneCTBehaviour/RotatedPillarCTBehaviour`）。

**d) 复用 Create 的 ItemVault 做"集装箱"** `blocks/ShippingContainerBlock.java:31` `extends ItemVaultBlock`（Create `content.logistics.vault`），自带内部 `Entity extends ItemVaultBlockEntity`，用 `COLOR` 字段区分染色并在 `isSameType` 中阻止异色连接（`:51-53`）；多方块连通靠 Create 的 `ConnectivityHandler`，能力注册在 `events/CreateDecoCommonEvents.java:12-15`（`@EventBusSubscriber` + `RegisterCapabilitiesEvent`）。历史上需要 mixin `ItemVaultBlockEntityMixin` 改 `initCapability()` 里的 `partAt` 参数，现已废弃（类头注释说明，`mixin/ItemVaultBlockEntityMixin.java:11-14`）。

**e) 自定义形状装饰方块 + 专用 BlockItem**：`CatwalkBlock/CatwalkRailingBlock/CatwalkStairBlock`(265/191)、`SupportBlock/SupportWedgeBlock`、`CageLampBlock`、`CoinStackBlock`(可叠层)、`DecalBlock`、`FacadeBlock`。配套 `items/` 下 5 个 `*BlockItem`（`CatwalkBlockItem`、`RailingBlockItem`、`CatwalkStairBlockItem`、`ShippingContainerBlockItem`、`CoinStackItem`）重写放置/交互，把复杂放置逻辑从 Block 里拆出。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯装饰模组，无 payload 注册，`network` 包不存在）。
- 配置：**无**（无 ModConfigSpec）。
- 数据驱动：仅通过 Create 的 CT/ponder 机制与 datapack tag（`api/CreateDecoTags.java`）；配方、loot、模型全部走 **Registrate datagen provider** 内联生成（`RegistrateRecipeProvider` + `ShapedRecipeBuilder/SingleItemRecipeBuilder.stonecutting`，见 `api/Catwalks.java:164-215`、`api/Decals.java:56-66`），构建产物在 `src/generated/resources`，仓库（bulk 快照）中未包含 assets/data，因此源码里看不到 json。
- 语言文件也由代码写入：`CreateDecoMod.REGISTRATE.addLang("itemGroup", ...)`（`ItemRegistry.java:34-35`）。

## 6. Mixin

两个配置：`src/main/resources/createdeco-common.mixins.json`（package `com.github.talrey.createdeco.mixin`）与 `src/main/resources/createdeco.mixins.json`（package `...mixin.forge`）。**两者的 `mixins`/`client` 数组都是空**——这是多加载器（Architectury 风格）时代的遗留骨架，唯一的 mixin 类 `mixin/ItemVaultBlockEntityMixin.java` 已被 `@Deprecated` 且不在配置中加载（hook 目标为 `ItemVaultBlockEntity.initCapability()V` 中 `ConnectivityHandler.partAt(...)` 调用，用 `@ModifyArg` 换 type）。**结论：实际零 mixin**，全部效果靠 Create 公开 API 实现。

## 7. 值得学的 5 条具体做法

1. **"一族方块一个构建器 + 材质表驱动"批量注册**：`BlockRegistry.java:49-110` + `ItemRegistry.METAL_TYPES`（`ItemRegistry.java:39`）。适用场景：自己写装饰/材料类附属时把 N×M 组合压成一次循环，新增材质改一行 Map。
2. **程序化 multiPart blockstate 生成器**：`BlockStateGenerator.bar(...)`（`BlockStateGenerator.java:31-78`）用 vanilla 父模型 + 布尔条件组合，替代手写 json。适用场景：铁栏杆类、栅栏类、栏杆/扶手等多连接形态方块。
3. **集中式 CT 贴图表 + 一行 `.onRegister(connectedTextures(...))`**：`connected/SpriteShifts.java:20-28`、`api/Windows.java:80-81`。适用场景：任何要做 Create 风格连通贴图的方块（玻璃、金属板、集装箱顶面）。
4. **加载器入口与平台无关逻辑分离**：`forge/CreateDecoModForge.java`(7 行) + `CreateDecoMod.init()`。适用场景：未来要出 Fabric/多平台版本时，把 `@Mod` 类做薄，其余零加载器依赖。
5. **BlockItem 拆出复杂放置交互**：`items/RailingBlockItem.java`、`items/CatwalkStairBlockItem.java`。适用场景：扶手/楼梯/集装箱这类放置时需要读邻居状态或朝向的方块，避免 Block 类膨胀。

## 8. 公开 API

非库模组。可复用面：`api/` 包内 18 个 `build(...)` 静态构建器与 `BlockStateGenerator` 的静态生成方法本身是 public 的，理论上可被别的 Create 附属直接调用（但未发布 maven、无 API 稳定性承诺，视为内部实现）。
