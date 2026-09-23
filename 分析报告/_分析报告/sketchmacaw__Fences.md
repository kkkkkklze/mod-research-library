# Macaw's Fences 源码分析

## 1. 基本信息
- Mod 名 / mod_id：Macaw's Fences / `mcwfences`（主类 `MacawsFences.java:17` 的 `@Mod("mcwfences")`）
- 作者：sketchmacaw（GitHub owner）；README 只有一句"问题请提到 https://github.com/sketchmacaw/MacawsModsIssues"，无版本号
- 目标 MC 版本与加载器：**纯 Forge，无 Fabric**；仓库按目录分 5 个版本：`1.16.5 Forge`、`1.17.1 Forge`、`1.18.2 Forge`、`1.19.4 Forge`、`1.20.4 Forge`。加载器由 import 判断（`net.minecraftforge.registries.DeferredRegister`、`FMLJavaModLoadingContext`），版本号只能从目录名得到
- Gradle 插件：**未确认** —— 仓库为纯源码导出，**无 `build.gradle` / `gradle.properties` / `src/main/resources` / `fabric.mod.json` / `mods.toml`**，整个仓库非 java 文件只有 `README.md` 与 `LICENSE.md`
- 许可证：MIT（`LICENSE.md:1`，`Copyright (c) 2022 Kaupenjoe` —— 即沿用 Kaupenjoe 的 MIT mod 模板）
- 编译依赖：无任何第三方 mod 依赖，只用原版 API（1.20.4 侧仅 `net.minecraftforge.common.extensions.IForgeItem` 一个 Forge 接口，见 `1.20.4 Forge/objects/FuelItemBlock.java:9`）

## 2. 源码规模与包结构
- 37 个 `.java`，合计 **2501 行**（`find . -name '*.java' -exec wc -l {} +`），每版本 7-8 个文件（V1.16.5=8、1.17.1=7、1.18.2=7、1.19.4=7、1.20.4=8）
- 包结构（`com.mcwfences.kikoz`，5 个版本同构）：
  - 根：`MacawsFences.java`（主类，1 文件）
  - `init/`：`BlockInit`、`ItemInit`、`TabInit`（仅 1.16.5/1.19.4/1.20.4）、`DamageInit`（4-5 文件）
  - `objects/`：`WiredFence`、`StoneWiredFence`、`FuelItemBlock`（3 文件）
  - `util/`：`ClientEventBusSubscriber`（**只有 ≤1.19 有**，1.19.4/1.20.4 已删除）
- 最大的文件全部是注册表：`1.19.4 Forge/init/BlockInit.java`(236)、`1.20.4 Forge/init/BlockInit.java`(199)、`1.20.4 Forge/init/TabInit.java`(187)、`1.20.4 Forge/init/ItemInit.java`(180)、`1.18.2/1.17.1 BlockInit.java`(166)
- 无 mixin、无网络包、无 datagen、无 config

## 3. 入口与注册
`1.20.4 Forge/MacawsFences.java:24-36`：
```java
final IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();
modEventBus.addListener(this::setup);
modEventBus.addListener(this::doClientStuff);
BlockInit.BLOCKS.register(modEventBus);
ItemInit.ITEMS.register(modEventBus);
TabInit.CREATIVE_TABS.register(modEventBus);
instance = this;
MinecraftForge.EVENT_BUS.register(this);
```
- **注册框架 = 原生 Forge `DeferredRegister`**，一个注册表一个类：`BlockInit.BLOCKS`（`ForgeRegistries.BLOCKS`）、`ItemInit.ITEMS`（`ForgeRegistries.ITEMS`）、`TabInit.CREATIVE_TABS`（`Registries.CREATIVE_MODE_TAB`，1.20.4）、`DamageInit`（**空壳类，不注册任何东西**，`DamageInit.java:7-12` 仅继承 `DamageSource` 提供构造器）
- 方块与物品**同 id 成对声明**：`BlockInit.OAK_PICKET_FENCE` ↔ `ItemInit.OAK_PICKET_FENCE`（`() -> new FuelItemBlock(BlockInit.X.get(), new Item.Properties())`），石质系列用普通 `BlockItem`
- 创造标签在 1.20.4 用 `CreativeModeTab.builder()` 逐条 `entries.accept(BlockInit.X.get())`（`TabInit.java:16-19`），1.19.4 则用 `CreativeModeTabEvent.Register` 事件 + `ItemInit.ITEMS.getEntries().forEach(...)` 批量填充（见版本 diff）

## 4. 核心系统
1. **多材质 × 多方块类型的批量注册**（`init/BlockInit.java`，199-236 行）：同一模式按木材 9-11 种展开，一共约 190 个方块。例如 9 连发：
```java
public static final RegistryObject<Block> OAK_PICKET_FENCE = BLOCKS.register("oak_picket_fence", () -> new FenceBlock(BlockBehaviour.Properties.of().mapColor(MapColor.WOOD).strength(1.4F, 2.0F).sound(SoundType.WOOD)));
```
   命名规则固定为 `<wood>_<type>`，`RegistryObject` 常量名 = 上划线大写同 id，一一对应便于脚本/复制扩展。
2. **复用原版方块类而非自写 Block**：栅栏用 `FenceBlock`、栅栏门用 `FenceGateBlock(WoodType.X, props)`、树篱/草顶墙用 `WallBlock`、栏杆墙又用 `FenceBlock`（`BlockInit.java:100-144`），属性直接抄原版：`Block.Properties.ofFullCopy(Blocks.OAK_LEAVES)`（`BlockInit.java:67-75`）；1.16.5 时代写法是 `Block.Properties.of(Material.WOOD, MaterialColor.WOOD)`（`1.16.5 Forge/init/BlockInit.java:23`），可当"属性 API 迁移对照表"。
3. **带伤害的交互方块**：`objects/WiredFence.java:12-27` `extends FenceBlock`，覆写 `entityInside(...)` 调 `entityIn.hurt(worldIn.damageSources().cactus(), 2.0F)`；`StoneWiredFence` 是石质版（同结构）。注意 `WiredFence(Properties)` 构造器**完全忽略传入的 properties**，内部重新 `Properties.of()...strength(1.5f)`（`:15-21`），而 `BlockInit` 仍传 `null`
4. **燃料物品与分类物品**：`objects/FuelItemBlock.java:11-20` `extends BlockItem implements IForgeItem`，`getBurnTime(...) { return 300; }` 让木栅栏可作熔炉燃料；`init/ItemInit.java:81` 起石质墙用普通 `BlockItem`，第 173 行的 `WOODEN_CHEVAL_DE_FRISE` 用 `FuelItemBlock` 而 `IRON_CHEVAL_DE_FRISE` 用 `BlockItem`，是有意的区分

## 5. 网络 / 数据驱动 / 配置 / datagen
全部为"无"。没有 `SimpleChannel`、无自定义数据包、无 `ForgeConfigSpec`、无 JSON 数据驱动 loader、无 datagen provider。所有方块/物品属性硬编码在 Java 注册表里；`TabInit` 是唯一"元数据"（标签顺序）。语言/贴图/模型不在本仓库快照中。

## 6. Mixin
无。仓库中不存在 `mixins.json` 或任何 `@Mixin` 类（也无 mixin 依赖）。

## 7. 值得学的 5 条具体做法
1. **同一注册模式在 `BlockInit` 里平铺展开，不做循环/工厂**：每行 `RegistryObject<Block> X = BLOCKS.register("x", () -> new FenceBlock(...))`（`1.20.4 Forge/init/BlockInit.java:25-193`）。适合"材质 x 类型"组合爆炸、又想一眼看清 id 的大宗方块 mod；缺点是无法 diff 出结构变化，作者靠 `//1.20`、`// New Update 1.1.0` 注释分段（`:146`、`:163`）。
2. **属性直接抄原版方块**：`Block.Properties.ofFullCopy(Blocks.X_PLANKS / X_LEAVES)`（`BlockInit.java:67-75`、`:33-40`），改版时随原版一起变，省掉映射迁移体力。
3. **用 `implements IForgeItem` 给物品加 Forge 能力**：`FuelItemBlock` 只覆写 `getBurnTime` 返回 300 就获得燃烧能力，无需 `FurnaceFuelBurnTimeEvent`（`objects/FuelItemBlock.java:17-20`）。
4. **版本对照式仓库布局**：`1.16.5 ... 1.20.4` 五个平行目录，同名文件可直接 diff（本次即用 `diff 1.19.4/MacawsFences.java 1.20.4/MacawsFences.java` 看出 `CreativeModeTabEvent.Register` → `DeferredRegister<CreativeModeTab>` 的迁移）。写多版本 mod 时值得照搬这种"同构目录 + 版本目录名"的仓库组织。
5. **简单注册事件做 BlockItem 批量注册（旧版）**：1.16.5 用 `RegistryEvent.Register<Item>` 遍历 `BlockInit.BLOCKS.getEntries()` 生成同名 BlockItem（`1.16.5 Forge/MacawsFences.java:51-58`），1.17+ 才拆到 `ItemInit`；若需要维护老版本可参考。
6. 补充（客户端渲染层）：≤1.19 用 `util/ClientEventBusSubscriber`（`@Mod.EventBusSubscriber(bus=Bus.MOD, value=Dist.CLIENT)` + `FMLClientSetupEvent` 里上百行 `RenderTypeLookup.setRenderLayer(BlockInit.X.get(), RenderType.cutout())`，`1.16.5 Forge/util/ClientEventBusSubscriber.java:24-106`）；**1.19.4/1.20.4 该文件已删除，渲染类型应已移到资源侧（本仓库无资源，未确认具体做法）**。

## 8. 是否库/前置
非库、非前置：纯内容 mod，无对外 API 包、无扩展点接口，也不给其他 mod 提供注册入口。唯一可复用的是代码模板本身（`init/` 三件套的写法）。
