# Mari023/AE2WirelessTerminalLibrary 源码分析

## 1. 基本信息

- Mod 名 / mod_id：AE2WTLib / `ae2wtlib`，作者 mari_023、Ridanisaurus；许可证 MIT（贴图 CC BY-NC-SA）
- 目标版本：**NeoForge 专用**，`neoforgeVersion=26.1.2.87`、Parchment MC `1.21.9`、`java.toolchain = 25`（`gradle.properties`、`build.gradle.kts:45`）；代码使用 `Identifier`、`ItemStackTemplate`、`DeltaTracker` 等新 API，属 1.21.9+ 世代
- 构建：**net.neoforged.moddev 2.0.141 + com.diffplug.spotless 7.0.0 + maven-publish**（`settings.gradle.kts`），版本号由 `ae2wtlibCurrentMajor=26` 拼成 `260.0.0-SNAPSHOT`，CI 用 `PR_NUMBER`/`TAG` 环境变量覆盖并 publish 到 modmaven
- **双模块**：`:`（主体）与 `:ae2wtlib_api`（独立 mod_id 的 API，`jarJar(project(":ae2wtlib_api"))` + `api(...)` 内嵌，见 `build.gradle.kts:31-32`）
- 依赖：AE2 `org.appliedenergistics:appliedenergistics2:26.1.10-beta`（必需）、Curios（mods.toml 声明 OPTIONAL，Curio 集成代码在 `WUTHandler.java:130` 被 FIXME 注释掉）、JEI/REI/EMI 仅 compileOnly + 由 `runtimeItemlistMod` 选择运行期模组；`mods.toml` 依赖顺序 `ae2wtlib_api BEFORE`、`ae AFTER`

## 2. 源码规模与包结构

- 103 个 `.java`，合计 5706 行（API 模块约 35 个）
- 最大文件：`api/terminal/WTMenuHost.java`(275)、`AE2wtlibEvents.java`(205)、`api/gui/ScrollingUpgradesPanel.java`(201)、`api/terminal/WUTHandler.java`(174)、`AE2wtlibForge.java`(170)、`api/gui/TerminalSelectionPanel.java`(152)、`wct/CraftingTerminalHandler.java`(148)、`api/registration/WTDefinition.java`(142)
- API 模块包：`api`、`api.gui`、`api.registration`、`api.results`、`api.terminal`、`api.mixin`
- 主体包：`ae2wtlib`、`.networking`、`.mixin`、`.hotkeys`、`.recipeviewer`、以及四种终端 `wct`（合成）/`wet`（样板编码）/`wat`（样板访问）/`wut`（通用终端）、`wct.magnet_card`
- 每个包都有 `package-info.java`（含 `@NullMarked`，`api/package-info.java`）

## 3. 入口与注册

主类 `src/main/java/de/mari_023/ae2wtlib/AE2wtlibForge.java:37`：

```java
@Mod(AE2wtlibAPI.MOD_NAME) @EventBusSubscriber
public class AE2wtlibForge {
    public AE2wtlibForge(IEventBus modEventBus, ModContainer modContainer) {
        new AE2wtlibAPIImplementation();
        modContainer.registerConfig(ModConfig.Type.COMMON, AE2wtlibConfig.SPEC, MOD_NAME + ".toml");
        AE2wtlibItems.DR.register(modEventBus);
        modEventBus.addListener((RegisterEvent e) -> {
            if (e.getRegistryKey().equals(Registries.MENU)) AE2wtlib.registerMenus();
            if (!e.getRegistryKey().equals(Registries.ITEM)) return;
            AE2wtlib.registerTerminals(); ...
```

注册组织方式：**只有 AttachmentType 用 DeferredRegister**（`AE2wtlib.java:39`），物品/Menu/配方序列化器一律 `Registry.register(BuiltInRegistries.X, ...)`，并用监听 `RegisterEvent` 过滤注册表 key（以 ITEM 作为"最后"锚点顺序编排终端注册）。数据组件单独一套：`AE2wtlibAdditionalComponents.init()` + 静态 `Map<Identifier, DataComponentType<?>> DR`（`api/AE2wtlibComponents.java:36`）。

## 4. 核心系统

**(a) 终端定义注册表 WTDefinition + AddTerminalEvent**：`api/registration/WTDefinition.java` 是 record（terminalName / containerOpener / WTMenuHostFactory / menuType / item / universalTerminal / componentType / upgradeCount / icon），静态 `Map<String,WTDefinition>` + `List` 保序，并提供 `CODEC`（`Codec.STRING.comapFlatMap`）与 `STREAM_CODEC`（`ByteBufCodecs.STRING_UTF8.map`）供持久化/网络用。注册入口是**一次性事件** `AddTerminalEvent.java`：`register(Consumer)` 在 `run()` 之后调用会抛 `IllegalStateException`（用 `HANDLERS = null` 作哨兵），`builder(...).addTerminal()` 链式提交；主体的 `AE2wtlib.registerTerminals()`（`:42`）就注册 crafting/pattern_encoding/pattern_access 三种。

**(b) 通用终端 WUT 机制**：`ItemWUT` 不靠 NBT 而是**每组终端一个 `DataComponentType<Unit>` 标记组件**，另用 `AE2wtlibComponents.CURRENT_TERMINAL`（类型就是 `WTDefinition`）记录当前终端；`WTDefinition.ofOrNull(ItemStack)`（`:114`）在 WUT 上按组件存在性判定并顺手写回 CURRENT_TERMINAL。`WUTHandler.java:73 nextTerminal()` 用 `do/while` 跳过该 WUT 未安装的终端；`getUpgradeCardCount()` 把各终端 `upgradeCount` 求和作为 WUT 升级槽上限。

**(c) WTMenuHost 宿主抽象**：`api/terminal/WTMenuHost.java:46` 继承 AE2 的 `WirelessTerminalMenuHost<ItemWT>`，扩展三件事——`SupplierStorage`/`StackDependentSupplier` 让存储随手上物品实时解析（`:63`、`:88`）、`createInv()` 用 `AppEngInternalInventory` + `InternalInventoryHost.saveChangedInventory` 把 GUI 改动直接写回 DataComponent（`:242`）、`ItemWT#injectAEPower` 双份 `consumeIdlePower` 模拟/真实调用实现**量子网络给终端反向充电且绝不让网络低于 50%**（`:208-233`）。

**(d) 量子桥接与链接状态**：`WTMenuHost.findQuantumBridge` 用 `Locatables.quantumNetworkBridges().get(level, ±frequency)`（正负频率都试），`isQuantumLinked()`（`:151`）依次检查 升级卡→奇点频率→桥存在→两端网络一致（`QuantumCluster.getCenter().getQEFrequency()`）→是否供电，每步失败返回 `Status` 枚举的 `toILinkStatus()`；`getActionableNode()` 在量子连通时**替换为桥的节点**，因此 ME 访问完全走远程网络。

**(e) AE2 集成扩展点（不靠 mixin 的部分）**：`AE2wtlib.java` 统一调用 AE2 公开 API——`GridLinkables.register(...WirelessTerminalItem.LINKABLE_HANDLER)`（无线连网）、`UpgradeHelper`/`Upgrades.add`（升级卡）、`HotkeyActions.register`（restock/magnet/stow 三个热键动作）、`InitScreens.register(event, TYPE, Screen::new, jsonPath)`（用 AE2 的 JSON 界面描述注册 screen）。

**(f) 快捷键/被动功能**：`AE2wtlibEvents.java` 提供 `restock(player, item, now, setStack)`、`insertStackInME(ItemEntity, Player)`、`pickBlock(...)`，由 `AE2wtlibForge.java:97-159` 的一批 `@SubscribeEvent`（`LivingEntityUseItemEvent.Finish`、`PlayerInteractEvent.RightClickBlock/EntityInteractSpecific`、`ItemEntityPickupEvent.Pre`、`ArrowNockEvent`、`ArrowLooseEvent`，多为 `EventPriority.LOWEST`）驱动，实现自动补货与捡取直入 ME。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`RegisterPayloadHandlersEvent` + `PayloadRegistrar`，C2S 3 个（CycleTerminal、SelectTerminal、TerminalSettings）S2C 3 个（UpdateWUT、UpdateRestock、RestockAmount），统一 `playToServer/playToClient(id, STREAM_CODEC, (packet, ctx) -> ctx.enqueueWork(() -> packet.processPacketData(ctx.player())))`（`AE2wtlibForge.java:80-90`）；包基类 `AE2wtlibPacket` 用 `CustomPacketPayload.Type<T>` 携带 `ResourceLocation`。
- **数据驱动**：无 datapack 内容注册；配方新增（`Upgrade`/`Combine` 序列化器）手写注册；文档走 **GuideME 的 markdown**（`assets/ae2wtlib/ae2guide/**/*.md`，并有专门 `guide` run config 注入 `guideme.ae2.guide.sources`）。
- **配置**：`ModConfig.Type.COMMON` + `AE2wtlibConfig.SPEC`（`AE2wtlib/C*`），另 `AE2wtlibClientConfig`；API 侧还有 `api/terminal/AE2wtlibConfigManager implements IConfigManager`，专门把 AE2 的终端设置（`Setting<T>`）读写到 DataComponent：`writeToNBT(ValueOutput)`/`readFromNBT(ValueInput)`/`importSettings(Map<String,String>)`/`exportSettings()`（`:66-104`）。
- **datagen**：无（仅 Spotless 格式化与 eclipse `codeformat/codeformat.xml`）。

## 6. Mixin

- 主体 `src/main/resources/ae2wtlib.mixins.json`（package `de.mari_023.ae2wtlib.mixin`，mixins=[AEItemsMixin, ServerGamePacketListenerImplMixin, ServerPlayerGameModeMixin, ServerPlayerMixin]，client=[GuiMixin]）
- API `ae2wtlib_api/src/main/resources/ae2wtlib_api.mixins.json`（package `de.mari_023.ae2wtlib.api.mixin`，client=[WidgetContainerAccessor]，compatibilityLevel JAVA_25）
- 注入点：`AEItemsMixin.java:32` `@Inject(method="item(Ljava/lang/String;Lnet/minecraft/resources/Identifier;Ljava/util/function/Function;)...", at=HEAD, cancellable=true)` 替换 AE2 物品定义；`ServerPlayerGameModeMixin.java:20` `@Inject(method="useItemOn", at=RETURN)`；`ServerPlayerMixin.java:24` `@Inject(method="drop(Z)V", at=TAIL)`；`ServerGamePacketListenerImplMixin.java:22` `@Inject(method="tryPickItem", at=@At(INVOKE, shift=AFTER, target="...send(Lnet/minecraft/network/protocol/Packet;)V"))`；客户端 `GuiMixin.java:28` 在 `extractSlot` 处取消原版 `itemDecorations`（隐藏耐久条）
- `WidgetContainerAccessor` 是 `@Accessor Map<String,ICompositeWidget> getCompositeWidgets()`，用于把自定义面板插进 AE2 的 WidgetContainer
- 两侧 AT：`META-INF/accesstransformer.cfg` 只公开 `ItemEntity.target`、`Slot.x/y`

## 7. 值得学的 5 条具体做法

1. **API 作为独立 mod + stub 自实例化**：`api/AE2wtlibAPIImpl.java:32` 静态块 `if (!AE2wtlibAPI.isModPresent("ae2wtlib")) new AE2wtlibAPIImpl();` 提供全部返回默认值的空实现；有主 mod 时由 `AE2wtlibAPIImplementation` 覆盖。**依赖者可只装 API 不崩**——库/前置 mod 设计范本。
2. **一次性注册事件**：`AddTerminalEvent` 用可空列表 + `run()` 置 null，注册窗口关闭后再注册直接抛异常；`api/registration/AddTerminalEvent.java`；适合"必须在固定时机完成的注册"。
3. **DataComponent 即数据模型**：每个终端一个 `DataComponentType<Unit>` 标记 + `CURRENT_TERMINAL` 存 WTDefinition，配 `Codec`/`StreamCodec`；`AE2wtlibComponents.java`、`WTDefinition.java:54-61`；替代 NBT 的现代写法。
4. **`SupplierStorage` + `StackDependentSupplier` 绑定物品栈状态的容器**：存储/背包随物品栈实时解析，`saveChangedInventory` 回写组件；`api/terminal/WTMenuHost.java:63-68`、`:242-258`；适合"物品内存储 + GUI 编辑"。
5. **状态枚举 → ILinkStatus 的短路诊断链**：`Status` 枚举（NoUpgrade/NoSingularity/BridgeNotFound/DifferentNetworks/NotPowered）逐条短路并可直接 `toILinkStatus()` 在 GUI 显示；`WTMenuHost.java:151-191` + `api/results/Status.java`；适合网络/多方连接类功能。

## 8. 公开 API

- 门面 `de.mari_023.ae2wtlib.api.AE2wtlibAPI`：`id/apiId`、`isModPresent`、`hasQuantumBridgeCard`、`isUniversalTerminal(Item|ItemStack)`、`makeWUT(DataComponentType<Unit>)`、`getWUT()`、`updateClientTerminal(ServerPlayer, ItemMenuHostLocator, ItemStack)`
- 扩展点：`AddTerminalEvent.register(Consumer<AddTerminalEvent>)` → `builder(name, WTMenuHostFactory, MenuType, ItemWT, Icon).hotkeyName(...).upgradeCount(...).addTerminal()`；`UpgradeHelper.addUpgradeToAllTerminals(ItemLike, int)`（`0` 表示最大）
- 基类/接口：`terminal.ItemWT`（单终端物品）、`terminal.ItemWUT`（通用终端）、`terminal.WTMenuHost`（菜单宿主）、`terminal.IUniversalTerminalCapable`、`terminal.AE2wtlibConfigManager`、`results.*`
- GUI 复用件：`api.gui.Icon/IconButton/UpgradeBackground/ScrollingUpgradesPanel/TerminalSelectionPanel`、`AE2wtlibSlotSemantics`、`api.mixin.WidgetContainerAccessor`
- 接入方式：Maven `modmaven`（group `de.mari_023`，artifact `ae2wtlib`），运行期需同时装 `ae2wtlib_api`（由主 jar jarJar 内嵌），强依赖 AE2 `[26.1.10-beta,27.0.0)`
