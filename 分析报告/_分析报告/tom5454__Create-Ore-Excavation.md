# Create Ore Excavation 源码分析报告

## 1. 基本信息

- Mod 名：Create Ore Excavation；mod_id：`createoreexcavation`；作者：tom5454；许可证：MIT License
- **多加载器双工程结构**（仓库根下两个独立 Gradle 根工程）：
  - `NeoForge/`：Minecraft `1.21.1`、NeoForge `21.1.211`、`mod_version=1.6.8`、Java 21、插件 `net.neoforged.gradle.userdev 7.0.168`（`NeoForge/gradle.properties`、`NeoForge/build.gradle:1-8`）
  - `Fabric/`：Minecraft `1.20.1`、Fabric Loader `0.15.7`、Fabric API `0.92.0`、`mod_version=1.5.4`、**Create 0.5.1-f + PortingLib 2.3.2**（`Fabric/gradle.properties`，PortingLib 模块 `accessors,base,transfer,networking,...`）
- 编译依赖：`create-1.21.1:6.0.x:slim`(transitive=false)、Ponder、Flywheel(api compileOnly)、Registrate；JEI `19.25.0.322`（compileOnly api + runtimeOnly full）、Jade、The One Probe、Adorned（`curse.maven:adorned-1036809`）、JourneyMap API `2.0.0-1.21.4-SNAPSHOT`、KubeJS `2101.7.2-build.295` + Rhino + Architectury + `kubejs-create`、CC:Tweaked（compileOnly, `maven.modrinth:cc-tweaked`）

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **136 个文件、11636 行**（NeoForge + Fabric 合计）。NeoForge 侧分两处源码根：`src/main/java`（加载器相关、JEI、datagen、cc、jm、network）与 **`src/platform-shared/java`（跨加载器共用：block / block.entity / recipe / menu / kubejs / client / util）**，由 `sourceSets { main { java { srcDir "src/platform-shared/java" } resources { srcDir "src/platform-shared/resources" } } }` 合并（`NeoForge/build.gradle:136-155`）。

主要包：`block`+`block/entity`（19）、`recipe`(4)、`client`(9)、`jei`(11)、`jm`(5)、`kubejs`(12)、`network`(4)、`menu`(3)、`item`(3)、`util`(11)、`compat` 前端（Fabric 侧另有一套 `rei`(11)、`emi`(10)）。

最大文件：`menu/OreVeinAtlasScreen.java`(544)、`data/COERecipes.java`(399)、`block/entity/ExcavatingBlockEntity.java`(376)、`Registration.java`(326)、`jm/OreVeinsOverlay.java`(298)、`block/MultiblockPart.java`(284)、`SampleDrillBlockEntity.java`(256)、`client/PonderScenes.java`(251)、`recipe/VeinRecipe.java`(232)。

**注意（事实）**：仓库内**不包含 assets/data 资源**——非 java 文件只有 15 个（`find` 结果：3 个 build 脚本 ×2、mods.toml、`kubejs.plugins.txt`、README/Credits/FUNDING），`*.png` 数量为 0，无 `assets`/`generated` 目录。模型/贴图/语言生成依赖 `Registrate` datagen（`Registration.java` 中大量 `.blockstate(...) .lang(...) .model(...)`）与运行时 jar，未入库（贴图来源未确认）。

## 3. 入口与注册

主类 `NeoForge/src/main/java/com/tom/createores/CreateOreExcavation.java:51-106`：

```java
public static final RecipeTypeGroup<DrillingRecipe> DRILLING_RECIPES = recipe("drilling", DrillingRecipe.Serializer::new);
public static final RecipeTypeGroup<ExtractorRecipe> EXTRACTING_RECIPES = recipe("extracting", ExtractorRecipe.Serializer::new);
public static final RecipeTypeGroup<VeinRecipe> VEIN_RECIPES = recipe("vein", VeinRecipe.Serializer::new);
public static final Supplier<AttachmentType<OreDataAttachment>> ORE_DATA = ATTACHMENT_TYPES.register("ore_vein",
        () -> AttachmentType.serializable(OreDataAttachment::new).build());
private static <T extends Recipe<?>> RecipeTypeGroup<T> recipe(String name, Supplier<RecipeSerializer<T>> serializer) { ... }
public static class RecipeTypeGroup<T extends Recipe<?>> { /* type + serializer + id 三元组 */ }
```

- **CreateRegistrate** 统一注册方块/方块实体/物品/菜单/创造栏（`Registration.java:45-224`，`REGISTRATE.block("drilling_machine", DrillBlock::new)`、`.menu("vein_atlas", OreVeinAtlasScreen::new)`），语言全部用 `REGISTRATE.addRawLang`（`Registration.java:226-304`，约 80 条 key）。
- **DeferredRegister** 4 个：`RECIPE_SERIALIZER`、`RECIPE_TYPE`、`ATTACHMENT_TYPES`（`NeoForgeRegistries.Keys.ATTACHMENT_TYPES`）、`DeferredRegister.DataComponents`（`CreateOreExcavation.java:59-74`）。
- 能力注册集中在 `:178-182`（`IO_TILE` 的 ItemHandler/FluidHandler/EnergyStorage，说明其兼容 FE 能量）。

## 4. 核心系统

**4.1 虚拟矿脉生成（最值得学）** `OreVeinGenerator.java` + `util/RandomSpreadGenerator.java` + `recipe/VeinRecipe.java`
- 矿脉不是真实地形，而是**吃原版结构放置算法**：`VeinRecipe` 持有 `RandomSpreadStructurePlacement placement` 与 `biomeWhitelist/blacklist`、`priority`、`finite`(自定义 `ThreeState`)、`amountMultiplierMin/Max`。
- `RandomSpreadGenerator.pick(chunk)` 遍历按优先级排序的矿脉配方，调 `placement.getPotentialStructureChunk(seed, x, z)`，命中则用 `WorldgenRandom(new LegacyRandomSource(0L)) + setLargeFeatureSeed(seed,x,z)` 采样该区块生物群系做白/黑名单判定，返回该矿脉（`RandomSpreadGenerator.java:33-48`）。
- 结果缓存在静态 `AtomicReference`（双检锁 + `synchronized`），并在 `TagsUpdatedEvent` 时 `OreVeinGenerator.invalidate()`（`CreateOreExcavation.java:165-168`）；确定性随机用 `seed ^ chunkPos.toLong()`（`OreVeinGenerator.java:37-41`）。
- 还需要 `RandomSpreadGenerator.locate()` 支撑"最近矿脉"定位（供 `/coe locate` 与 Vein Finder 使用）。

**4.2 区块级矿脉状态（NeoForge Attachment）** `OreDataAttachment.java` + `OreData.java`
- 每区块的剩余矿量/随机倍率存在 chunk **attachment** 上（替代旧版 Capability 思路），`implements INBTSerializable<CompoundTag>`，内部用 `OreData.Serialized.CODEC` 与 `provider.createSerializationContext(NbtOps.INSTANCE)` 编解码。
- 读取入口 `OreDataAttachment.getData(LevelChunk)`：客户端访问直接抛异常（`throw new RuntimeException("Ore Data accessed from client")`），首次访问懒加载 `data.populate(chunk)` 并按需 `chunk.setData(...)`。

**4.3 采集机器（SmartBlockEntity + 多结构）** `block/entity/ExcavatingBlockEntity.java`（抽象基类）+ `ExcavatingBlockEntityImpl`（各加载器实现）
- tick 逻辑：`kinetic.getRotationSpeed() >= SpeedLevel.MEDIUM.getSpeedValue()` 才推进，进度按 `rotationSpeed / MEDIUM` 的倍率增长（`:150-151`）；每 tick 用 `kinetic.setStress(current.value().getStress())` 让配方反过来决定应力，实现"变应力机器"。
- 三态校验：配方要求 `getDrill().test(drillStack)`（钻头物品）、机器下方 2 格必须是实心方块（`getBelow() = worldPosition.below(2)`）、`data.canExtract(...)`（每脉最大提取器数量）。
- 状态机 `ExcavatorState {NO_ERROR, NO_VEIN, VEIN_EMPTY, TOO_MANY_EXCAVATORS, NO_RECIPE}`，tooltip 用 `info.coe.drill.err_ + name.toLowerCase()` 拼 key（`:101-103`）。
- 客户端同步走 `SmartBlockEntity.read/write(..., clientPacket=true)` 的差异字段：只写 `state/veinId/resRem/currentRecipeId/hasRot`（`:199-238`），不额外发包。
- 钻头装卸与图鉴交互在 `onClick`（`:270-303`），`createRenderBoundingBox` 扩大 3x3 渲染盒（`:314-316`）。

**4.4 多方块框架** `block/MultiblockPart.java`(284) + `MultiblockController.java` + `block/entity/MultiblockCapHandler`
- `MultiblockPart` 接口拆分 `MultiblockGhostPart`（幽灵方块：`noLootTable().pushReaction(BLOCK)`、扳手拆父方块、`makeCtx` 重定向命中）与 `MultiblockMainPart`（`getSize(facing)`、`getPartTypeAt(facing,x,y,z)`、`getGhostDirection`、`getBlockRotation`、枚举 `MultiblockPartType`）。
- `MultiblockController extends Block implements MultiblockMainPart` 提供 `HORIZONTAL_FACING` 状态定义、镜像/旋转、`getVisualShape=Shapes.empty()` 与 `getShadeBrightness=1.0`（让控制器本体视觉上透明）；`MultiblockCapHandler.dropInv()` 负责拆机时掉库存。

**4.5 配方体系** `recipe/ExcavatingRecipe.java` + `DrillingRecipe/ExtractorRecipe/VeinRecipe`
- 抽象基类含公共字段 `veinId / drill(Ingredient) / priority / ticks / stressMul / drillingFluid(Optional<FluidIngredient>)`，用 record `ExcavatingRecipeCommon` 承载 codec 字段，`Serializer<T>` 抽象类只留 `fromNetwork/toNetwork` 给子类扩展——**公共字段与子类字段分离序列化**，同时被 `MapCodec` 与 `StreamCodec` 复用。
- `VeinRecipe` 甚至实现了 `Recipe<CraftingInput>` 但 `matches()` 恒 false（`:61-64`），纯粹把配方系统当"数据注册表"用；`isInfiniteClient()` 在客户端按 `Config.defaultInfinite` 回退（`:124-134`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络（NeoForge）：`network/NetworkHandler.java` 在 `RegisterPayloadHandlersEvent` 中 `event.registrar("1")`，`playToServer(OreVeinAtlasClickPacket...)` / `playToClient(OreVeinInfoPacket...)`，统一 `context.enqueueWork(...)`，自定义 `Packet` 接口 + `STREAM_CODEC`。Fabric 侧为 `Fabric/src/main/java/com/tom/createores/network/{NetworkHandler,ClientNetwork}.java`。
- 数据驱动：三种配方类型（`drilling`/`extracting`/`vein`）全部数据驱动，README 直接给出 KubeJS 语法（`event.recipes.createoreexcavation.vein(...).placement(spacing,separation,salt).priority().alwaysFinite().veinSize(5,8).biomeWhitelist('forge:is_overworld')`）。
- 配置：`Config.java`（platform-shared）用 NeoForge `ModConfigSpec` 分 `Server/Common`，每个值都 `.translation("config.coe.xxx")`，文案由 `Registration.add()` 注入。
- datagen：`data/DataGenerators.java` + `data/COERecipes.java`（`extends RecipeProvider`，生成合成表 + 全部矿脉/钻探配方，Fabric 用 `COEDataGenerator`）。
- 客户端：`OreVeinAtlasScreen`(544 行，含分页 `PagedListWidget`) + `OreVeinAtlasMenu`、`menu` 走 Registrate `MenuEntry`；`client/PonderScenes.java` 注册 Ponder 场景；`jm/OreVeinsOverlay` 是 JourneyMap 覆盖层。

## 6. Mixin

**无。** `find . -name '*mixins*.json'` 在 NeoForge 与 Fabric 两侧都返回空，源码中无 `@Mixin` 类。跨加载器差异不靠 mixin，而是靠"`platform-shared` 共用代码 + 每侧独立的实现类"（如 `ExcavatingBlockEntityImpl`、`MultiblockCapHandler` 实现、`PlatformClient`）解决。

## 7. 值得学的 5 条具体做法

1. **`platform-shared` 源码集做多加载器共用**（`NeoForge/build.gradle:136-155` 加 `srcDir`）；适用：1.21 NeoForge + 1.20 Fabric 双端，避免复制 90% 代码。
2. **把"矿脉"建模成带 `RandomSpreadStructurePlacement` 的配方**（`VeinRecipe.java:40`、`RandomSpreadGenerator.pick`）；适用：需要按区块确定性分布、可被数据包/KubeJS 改的世界资源点。
3. **用 NeoForge 区块 Attachment 存每区块状态**（`OreDataAttachment.java` + `CreateOreExcavation.java:73-74`）；适用：需要一个 chunk 一份可序列化自定义数据的机器逻辑。
4. **静态缓存 + tags 重载事件失效**（`OreVeinGenerator.invalidate()` 挂在 `TagsUpdatedEvent`）；适用：从 RecipeManager 预计算索引，避免每 tick 全表遍历。
5. **配方公共字段抽 record + 抽象 Serializer 钩子**（`ExcavatingRecipe.ExcavatingRecipeCommon` 与 `Serializer<T>`）；适用：同一族多个配方类型（drilling/extracting）共享字段与编解码。
6. （附带）**变应力机器**：每 tick `kinetic.setStress(recipe.getStress())`（`ExcavatingBlockEntity.java:147`）；适用：应力随配方/进度变化的机器。

## 8. 公开 API / 扩展点

非库 mod，但扩展面很清晰：新增钻头只需物品加 `#createoreexcavation:drills` 标签 + 贴图 `assets/<modid>/textures/entity/drill/<name>.png`（README）；新增矿脉/钻探/抽取全部走数据包 JSON 或 KubeJS（`kubejs/KubeJSExcavation.java` 注册 3 个 RecipeSchema、`ComponentComponent`/`PlacementJS`/`FluidIngredientJS` 自定义组件、绑定 `coeutil`）；CC:Tweaked 侧暴露 `finder.search()`（`cc/OreVeinFinderTurtle.java`）；JEI 侧提供 `VeinIngredient` 自定义 ingredient 供他人复用。
