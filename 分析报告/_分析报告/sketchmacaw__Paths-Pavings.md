# sketchmacaw/Paths-Pavings 源码分析报告

## 1. 基本信息
- Mod 名：Macaw's Paths and Pavings；mod_id：`mcwpaths`；作者 Sketch Macaw & Peachy Macaw；MIT（`LICENSE.md`，版权署名却是 `Copyright (c) 2022 Kaupenjoe`，即作者沿用了 Kaupenjoe 的模板工程）
- 版本/加载器：**仓库内没有 `build.gradle`/`gradle.properties`/`settings.gradle`**，无 Gradle 插件信息；只能从元数据推断——`neoforge/main/resources/META-INF/neoforge.mods.toml` 写 `version="1.1.1"`、`loaderVersion="[1,)"`；`forge/src/main/resources/META-INF/mods.toml` 写 `loaderVersion="[28,)"`（Forge 28+，配合 `Item.Properties().setId()`、`useItemOn(ItemStack,...)`、`TooltipDisplay` 等 API，应为 1.21.9 之后的版本；fabric 模块则用 Yarn 映射）
- 依赖：无任何外部 mod 依赖（mods.toml 里也没有 dependencies 段），纯原版 API
- 仓库结构特点：**三个加载器各存一份完整且互相独立的源码目录**，不共享 common：`fabric/main/java/...`（注意没有 `src`）、`forge/src/main/java/...`、`neoforge/main/java/...`，包名统一 `com.mcwpaths.kikoz`

## 2. 源码规模与包结构
- `.java` **30** 个，总 **4061** 行（实测 `find -name '*.java' | wc -l` / `-exec wc -l {} +`）
- 包：`com.mcwpaths.kikoz`（主类）、`...init`（BlockInit/ItemInit/TabInit）、`...objects`（PathBlock/FacingPathBlock/EngravedBlock/FlattenedBlock）、`...util`（EngravedBlockTooltip/FlattenedBlockTooltip/FuelItemBlock）
- 最大文件：`BlockInit.java`（neoforge 437 行 / forge 439 行 / fabric 462 行，几乎全是逐行注册）、`MacawsPaths.java`（fabric 版含 300+ 行 `entries.add` 清单）、`ItemInit.java`
- 资源文件：仓库内**只有 2 个 `META-INF/*.toml`**，贴图/模型/语言文件/配方均不在本快照中（未确认）

## 3. 入口与注册
- NeoForge（`neoforge/main/java/com/mcwpaths/kikoz/MacawsPaths.java`）：`@Mod(MOD_ID)` 构造器 `(IEventBus bus)` 内三行 `ItemInit.ITEMS.register(bus); BlockInit.BLOCKS.register(bus); TabInit.CREATIVE_TABS.register(bus);`
- Forge：`@Mod("mcwpaths")` 构造器 `(FMLJavaModLoadingContext context)`，取 `context.getModBusGroup()` 后 `BlockInit.BLOCKS.register(modBusGroup)`；带一个空的 `@Mod.EventBusSubscriber(value = Dist.CLIENT)` 内部类
- Fabric：`MacawsPaths implements ModInitializer`，`onInitialize()` 里 `BlockInit.registerModBlocks()`，再用 `FabricItemGroup.builder()` + 逐条 `entries.add(BlockInit.XXX)` 建创造栏（**该文件有 bug**：`RegistryKey.of(RegistryKeys.ITEM_GROUP, Identifier.of("mod_id", "pathgroup"))` 把命名空间写死成字符串 `"mod_id"` 而非 `MacawsPaths.MOD_ID`）
- 注册框架：NeoForge 用 `DeferredRegister.createBlocks/createItems/create(MENU...)`（`DeferredBlock/DeferredItem/DeferredHolder`）；Forge 用 `DeferredRegister.Blocks/Items`；Fabric 用裸 `Registry.register(Registries.BLOCK, Identifier.of(MOD_ID, name), block)` + 私有 `registerBlock/registerEngravedBlock/registerFlattenedBlock` 帮助方法。新 API 下每个 register 都要 `ResourceKey`：`getKeyForBlock(String path)` / `getKeyForItem(String path)` 统一生成，再 `Properties.ofFullCopy(...).forceSolidOn().setId(getKeyForBlock("xxx"))`

## 4. 核心系统
1. **声明式方块族注册** — `neoforge/.../init/BlockInit.java`：一个机械重复的注册表，实测各类实例数为 `PathBlock`130 + `StairBlock`52 + `SlabBlock`52 + `EngravedBlock`52 + `FacingPathBlock`25 + `FlattenedBlock`5（`grep -o "new [A-Za-z]*(" | sort | uniq -c`）。学习点在于**没有**抽象成循环/工厂，而是给每个方块显式写 `BLOCKS.register("id", () -> new XxxBlock(...))`——适合代码生成式内容包，但维护成本高
2. **路面高度微调** — `objects/PathBlock.java`：`SHAPE = Block.box(0.0, 0.01, 0.0, 16.0, 0.99, 16.0)`，覆盖 `getShape()` 返回，使路面比全方块低 0.01/0.99；Fabric 版额外覆盖 `getRenderType()` 返回 `BlockRenderType.MODEL`
3. **朝向型路面** — `objects/FacingPathBlock.java`（继承 PathBlock）：`EnumProperty<Direction> FACING = HorizontalDirectionalBlock.FACING`，默认 `Direction.NORTH`，`getStateForPlacement` 用 `context.getHorizontalDirection().getClockWise()`（**顺时针取反**，让贴图花纹朝向玩家），并实现 `rotate()`
4. **工具交互切换方块状态** — `objects/EngravedBlock.java`：`BooleanProperty ENGRAVED`，`useItemOn` 中判 `heldItem.is(ItemTags.PICKAXES)` → 播放 `SoundEvents.UI_STONECUTTER_TAKE_RESULT` → `state.cycle(ENGRAVED)` → `level.setBlock(pos, newState, 3)` → 非创造模式 `heldItem.hurtAndBreak(1, player, LivingEntity.getSlotForHand(hand))`；`objects/FlattenedBlock.java` 完全同构，只是换成 `ItemTags.SHOVELS` + `SoundEvents.SHOVEL_FLATTEN`。两者用同一套 `CUBE`/`ENGRAVE` 两个 VoxelShape（15/16 高）随状态切换
5. **可燃烧的木路面物品** — `util/FuelItemBlock.java`：继承 `BlockItem`，覆写 `getBurnTime(ItemStack, RecipeType) { return 50; }`；`ItemInit` 里所有木板路面用 `FuelItemBlock`，石材铺装用普通 `BlockItem`
6. **提示文本物品** — `util/EngravedBlockTooltip.java` / `FlattenedBlockTooltip.java`：继承 `BlockItem` 覆写 `appendHoverText(ItemStack, Item.TooltipContext, TooltipDisplay, Consumer<Component>, TooltipFlag)`，固定输出 `Component.translatable("mcwpaths.engraved.desc")`（灰色），用于提示"可用镐雕刻/可铲平"

## 5. 网络 / 数据驱动 / 配置 / datagen
全部**无**：无自定义网络包、无 Codec/数据包注册表、无配置文件、无 datagen 类（`fabric/.../BlockInit.registerModBlocks()` 是空方法体）。资源与配方依赖仓库外提供的 assets/data。

## 6. Mixin
无。三个模块均无 mixin 包、无 `*.mixins.json`、无 accesswidener/AT。

## 7. 值得学的 5 条具体做法
1. **新注册 API 的 key 工厂**：`BlockInit.getKeyForBlock(path)` + `ItemInit.getKeyForItem(path)`（`neoforge/.../init/*.java:25`），每个 `Properties` 都 `.setId(key)`，避免手写 `ResourceLocation.fromNamespaceAndPath` 几十次
2. **同构方块类复制改标签/声音即可造新变体**：`EngravedBlock` 与 `FlattenedBlock` 只差 `ItemTags.PICKAXES/SHOVELS` 与音效，适合"同一交互不同工具"的系列方块
3. **用 `state.cycle(BooleanProperty)` 做开关式变体**：比两个独立方块省一倍注册量，且 NBT/模型共用
4. **`ItemTags` 而非硬编码物品判断**：`heldItem.is(ItemTags.SHOVELS)` 自动兼容所有模组铲子，且 `hurtAndBreak(1, player, LivingEntity.getSlotForHand(hand))` 是 1.21 后正确的耐久扣减签名
5. **多加载器"三份源码"策略**：可作反面参照——fabric 目录用 Yarn、forge/neoforge 用 Mojang 映射各写一遍，导致同一 bug 需改三处（如上述 `Identifier.of("mod_id", ...)`）

## 8. 扩展点 / API
非库模组，无公开 API；所有内容（约 316 个方块 + 对应物品）通过 `BlockInit`/`ItemInit`/`TabInit` 的静态字段公开，其他 mod 可用 `BlockInit.XXX.get()`（NeoForge/Forge）或直接引用 `Block` 常量（Fabric）。
