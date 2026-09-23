# MaliceZed/frequency-create 源码分析报告

## 1. 基本信息

- Mod 名：Frequency for Create（`displayName` 同）；mod_id：`frequency`；作者：MaZe (MaliceZed)
- 目标：Minecraft 1.21.1 + NeoForge（`src/main/resources/META-INF/neoforge.mods.toml`：loaderVersion `[4,)`，neoforge `[21.1.190,)`，mod 版本 0.2.0）
- 依赖：`create` `[6.0.0,)` required（BOTH）；**Create 是硬依赖**（mods.toml required，build.gradle `implementation "com.simibubi.create:create-1.21.1:6.0.11-292"`）
- Gradle：`net.neoforged.moddev` 2.0.141，Java 21，`sourceSets.main.resources { srcDir 'src/generated/resources' }`
- 编译期可选：JEI（common/neoforge api，19.27.0.340）、EMI（1.1.14+1.21.1:api）、REI（16.0.788 API）——全部 `compileOnly`，运行期由玩家自带
- Registrate 在 build.gradle 里被注释掉，但代码 `FrequencyMod.REGISTRATE = Registrate.create(MODID)` 与 `MenuEntry` 仍在用 → 实际经 Create 传递获取，属脆弱点
- 许可证：未指定（mods.toml `license="Not specified"`，仓库无 LICENSE）

## 2. 源码规模与包结构

实测：**79 个 .java / 5604 行**。包（第 3 层）文件数：`init` 6、`item` 6、`block` 10、`mixin` 7、`client` 9（+gui 6 / model 4 / renderer 2）、`compat` 2（+jei 3 / emi 4 / rei 4）、`datagen` 7、`network` 3、`world/inventory` 2、`data/component` 1、`config` 1、根 2。

最大文件：`compat/emi/FrequencyEmiRecipe.java` 370、`client/gui/BaseSymbolSwapScreen.java` 329、`init/FrequencyModItems.java` 264、`block/LogicCombinatorBehaviour.java` 244、`client/gui/LogicCombinatorScreen.java` 220、`compat/rei/ScrollableGridWidget.java` 184、`block/SymbolFrameBlock.java` 171、`datagen/FrequencyBlockStates.java` 167。

## 3. 入口与注册

入口 `src/main/java/maze/frequency/FrequencyMod.java`：`@Mod("frequency")`，构造注入 `IEventBus, ModContainer`；`modEventBus.addListener(this::registerNetworking / DataGenerators::gatherData)`，`NeoForge.EVENT_BUS.addListener(FrequencyMod::registerCommands)`。

注册框架**混用**：物品/方块/方块实体/数据组件用 `DeferredRegister`（如 `FrequencyModItems.ITEMS`、`FrequencyModComponents.COMPONENTS`），菜单用 Registrate（`MenuEntry<SymbolSwapMenu> BRASS_SYMBOL_SWAP = REGISTRATE.menu("symbol_swap", (type,id,inv,buf)->..., ()->screenFactory)`，见 `init/FrequencyModMenus.java`）。

一个值得注意的写法：显式类加载以保证 datagen 前所有注册类已加载——`FrequencyModTabs.TABS.getClass(); FrequencyModItems.ITEMS.getClass(); FrequencyModMenus.BRASS_SYMBOL_SWAP.getClass(); FrequencyModBlockEntities.register();`（`FrequencyMod.java`，`register()` 是空方法体，仅触发类初始化）。

## 4. 核心系统

1. **符号物品体系（3 档 × 78 个 + 液体符号）** — `init/FrequencyModItems.java`、`item/BaseSymbolItem.java`、`item/ISymbolItem.java`。要点：①名字列表 `SYMBOL_NAMES / ANDESITE_SYMBOL_NAMES / COPPER_SYMBOL_NAMES` 驱动注册，配 `Map<String, DeferredHolder>` 索引 + `getSymbol(name)`；②`List<ItemStack>` 懒加载缓存（`getAllBrassSymbolStacks()`，`allBrassSymbolStacks == null` 时构建）；③`displayChar(name)` 把注册名映射成显示字形（含私有区 `\uE000`–`\uE004` 自定义字形、`↑↓←→`、数学符号）；④`ITEMS.addAlias` 保留旧 ID 兼容。
2. **换符 GUI / 菜单** — `item/BaseSymbolItem.use()` 用 `SimpleMenuProvider` 打开 `SymbolSwapMenu`，并把 `Supplier<List<ItemStack>>` 注入菜单（`world/inventory/SymbolSwapMenu.java` 有「打开用构造器」和「网络用构造器」，后者按 menuType 选 `FrequencyModItems::getAllXSymbolStacks`）；服务端校验落在包处理器里，见第 5 节。
3. **符号展示框** — `block/SymbolFrameBlock.java`（`BaseEntityBlock` + `SimpleWaterloggedBlock`，`FACING/ROTATION/WATERLOGGED`，`dynamicShape()`+`noOcclusion()`）与 `block/SymbolFrameBlockEntity.java`。要点：①服务端只存字符串 `symbolName`（NBT 键 `"symbol"`），`getUpdatePacket/onDataPacket` 做同步；②**客户端模型数据用静态工厂注入以避免服务端加载客户端类**：`private static Function<String,Object> modelDataFactory`，由 `SymbolFrameBlockEntity.setModelDataFactory(...)` 在客户端初始化时设置，`getModelData()` 惰性构建；③`onDataPacket` 里 `requestModelDataUpdate()` + 静态 `sectionDirtyHandler.accept(worldPosition)` 触发区块重烘焙；④`FrameInteractionHandler`（服务端/客户端各一份 dirtyHandler 实现，`ServerSectionDirtyHandler.INSTANCE` 为默认）。
4. **逻辑组合器（Create Behaviour 实战）** — `block/LogicCombinatorBehaviour.java`、`block/LogicCombinatorBlock.java`、`block/GateMode.java`。要点：①继承 Create `BlockEntityBehaviour`，持 3 个 `LinkBehaviour`（`LinkBehaviour.receiver(be, Pair.of(slot0,slot1), power->{...})` ×2 + `transmitter(be, ..., ()->outputPower)`）；②每个槽位用自定义 `ValueBoxTransform`（`LogicCombinatorSlotTransform`）实现 6 个频率槽；③**自环防护**：比较 `outputLink.getNetworkKey()` 与两个输入的 networkKey，相等且输出 >0 时强制置 0；④NBT 手写 `write/read`（`Links` 复合 + `GateMode` ordinal），`GateMode.NOT` 时同步改方块状态 `SINGLE`。
5. **把「液体频率」接入 Create 红石链路** — `mixin/FrequencyAccessor.java` + `mixin/FrequencyFluidDataMixin.java` + `data/component/FluidData.java` + `item/LiquidSymbolItem.java`。要点：①`FluidData(ResourceLocation fluid)` 是带 `persistent`+`networkSynchronized` 双 codec 的 `DataComponentType`；②mixin 目标 `RedstoneLinkNetworkHandler$Frequency`，用 `@Accessor` 拿私有 `stack/color`，`@Inject` 到 `hashCode` 的 HEAD 与 `equals` 的 RETURN 把 fluid 纳入相等性（`item.hashCode()*31*31 ^ color*31 ^ fluidHash`）；③`LiquidSymbolItem.useOn` 先用 `level.getCapability(Capabilities.FluidHandler.BLOCK,...)` 的 SIMULATE drain 读罐内液体，再退化为读世界流体；④渲染用 `mixin/FluidSymbolItemRendererMixin.java` 注入 `ItemRenderer.render` 的 `popPose` 之前，用 `IClientFluidTypeExtensions` 的 still sprite 画 cutout 四边形（在 `BaseSymbolSwapScreen` 中跳过）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`RegisterPayloadHandlersEvent` → `event.registrar(MODID)`，三次 `playBidirectional(TYPE, STREAM_CODEC, Handler)`（`SymbolSwapPacket`、`FrameUpdatePacket`、`GateModeChangePacket`）。序列化统一 `StreamCodec`：`StreamCodec.composite(ByteBufCodecs.VAR_INT, SymbolSwapPacket::symbolIndex, SymbolSwapPacket::new)` 或手写 `StreamCodec.of(writeBlockPos/writeUtf, read...)`；处理用 `context.enqueueWork(...)`。**服务端权威示例**：`FrameUpdatePacket.handle` 先校验 `name.startsWith("symbol_")` 且 `FrequencyModItems.getSymbol("brass_"+name) != null`，再写 BE；`SymbolSwapPacket.handle` 校验 `containerMenu instanceof SymbolSwapMenu` 才执行 `swapSymbol`。
- 配置：`config/FrequencyConfig.java`，`ModConfigSpec` 单键 `enableStartupMessage`，以 `container.registerConfig(ModConfig.Type.CLIENT, SPEC)` 注册；客户端还有 `StartupToggleCommand` 注册 `/` 命令切换。
- datagen：`datagen/DataGenerators.java` 于 `GatherDataEvent` 注册 8 个 provider。特色：两个 `LanguageProvider`（en_us/ru_ru）先从 `assets/frequency/lang/default/<locale>/interface.json` 读默认文案，再用 `displayChar` 自动补齐所有符号物品的翻译；另有 `FrequencyItemModels/FrequencyBlockStates/FrequencyBlockLoot/FrequencyRecipeProvider/FrequencyBlockTagProvider/FrequencyItemTagProvider`。标签在 `FrequencyTags.java` 定义（`symbols/andesite_symbols/brass_symbols/copper_symbols`）。
- mod 元数据：mods.toml 声明 `enumExtensions="META-INF/enumextensions.json"` 与 `[[dataFixers]] dataFixerVersion = 1`；`enumextensions.json` 在 `git ls-files` 中存在但当前工作副本缺失（内容未确认）。

## 6. Mixin

配置：`src/main/resources/frequency.mixins.json`（`refmap: frequency.mixins.refmap.json`，package `maze.frequency.mixin`，compatibilityLevel JAVA_21）。
- `mixins`: `FrequencyAccessor`（`@Accessor("stack"/"color")`）、`FrequencyFluidDataMixin`（hook `hashCode` HEAD / `equals` RETURN，`remap=false`）。
- `client`: `ValueBoxRendererMixin`、`DepotRendererMixin`、`BeltRendererMixin`、`TableClothRendererMixin`、`FluidSymbolItemRendererMixin`（均为让符号物品在 Create 的数值框/置物台/传送带/桌布上以正确的 DisplayContext 渲染；除最后一个外未逐一阅读）。
- 注入点示例：`FluidSymbolItemRendererMixin` 目标 `ItemRenderer.render(ItemStack,ItemDisplayContext,boolean,PoseStack,MultiBufferSource,int,int,BakedModel)`，`@At(value="INVOKE", target="...PoseStack;popPose()V", shift=At.Shift.BEFORE)`。

## 7. 值得学的 5 条具体做法

1. **客户端类型不泄漏到服务端**：BE 里只用 `Object` 装 ModelData，靠 `Function<String,Object>` 静态工厂 + `@OnlyIn(Dist.CLIENT)` 的 setter 由客户端注入（`block/SymbolFrameBlockEntity.java`）；适用：服务端可加载的 BE 需要客户端专属缓存时。
2. **菜单「双构造器 + Supplier 数据源」模式**：一个构造器给打开菜单用，一个给 `RegistryFriendlyByteBuf` 用，物品列表用 `Supplier<List<ItemStack>>` 注入而不是序列化（`world/inventory/SymbolSwapMenu.java`、`item/BaseSymbolItem.java`）；适用：GUI 需展示大量同类物品。
3. **拓展别的 mod 的 equals/hashCode 前先 Accessor 取私有字段**：`@Accessor` 接口 + 在同一 mixin 里改 `hashCode`/`equals`，把自有数据组件纳入判定（`mixin/FrequencyAccessor.java`、`mixin/FrequencyFluidDataMixin.java`）；适用：Create 附属要给 Link/频率类加自定义维度。
4. **每个数据包都在 handler 里做服务端校验**：名字必须前缀合法且注册表中存在、菜单类型必须匹配（`network/FrameUpdatePacket.java`、`network/SymbolSwapPacket.java`）；适用：任何新增 C2S 包。
5. **显式类加载 + 空 `register()` 方法保证注册顺序**：在构造器末尾逐个 `ClassName.FIELD.getClass()`，配合 BE 类的空 `register()`（`FrequencyMod.java`、`init/FrequencyModBlockEntities.java`）；适用：注册类多、datagen 与注册互相依赖时。

（非库模组，第 8 节不适用。）
