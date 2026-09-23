# ggrgg13/Create--Redstone-Link-GUI 源码分析

## 1. 基本信息

- Mod 名：Create: Redstone Link GUI；mod_id：`createredstonelinkgui`；作者：ggrgg
- 目标：Minecraft 1.21.1 + NeoForge 21.1.1（`gradle.properties`：`neo_version=21.1.1`、`parchment 2024.11.17`）；Gradle 插件 `net.neoforged.moddev 2.0.141`；MIT；版本 `1.21.1-1.9.2`
- 编译依赖（`build.gradle:150-160`）：Create `6.0.10-280:slim`(transitive=false)、Ponder `1.0.82`、Flywheel API(compileOnly)、Registrate `MC1.21-1.3.0+67`；JEI `19.21.0.247` 与 EMI `1.1.22` 均为 `compileOnly` + api
- `src/main/templates/META-INF/neoforge.mods.toml` 依赖：create `[6.0.0,)` required；sable / jei(CLIENT) / emi(CLIENT) 为 optional
- README 自述 "AI coded with some human review"；仓库含 `TestProcedure.md`（手工测试步骤）与 `CHANGELOG.md`

## 2. 源码规模与包结构

**45 个 .java，5758 行**。包（第 3 层）：

- `client`(3)：`ClientClickHandler`、`ClientHooks`、`RedstoneLinkMoveHandler`(238)
- `client.screen`(5+2)：`AbstractLinkConfigScreen`(419)、`RedstoneLink/TinyRedstoneLink/VectorThrusterLink/VoidLinkConfigScreen`、`BlockPreviewRenderer`(265)；`client.screen.widget`：`FrequencyPresetPanel`(407)、`RedstoneLinkToggleWidget`
- `common`(4)：`TinyRedstoneCreateCompatibility`(241)、`VoidLinkHelper`、`SableHelper`
- `common.menu`(6)：`AbstractLinkMenu`(259)、`RedstoneLinkMenu`、`TinyRedstoneLinkMenu`、`VectorThrusterLinkMenu`、`VoidLinkMenu`、`FrequencyHelper`(199)、`GhostRecipeSlot`
- `common.network`(11 个 payload)、`common.preset`(2：`FrequencyPresetData`170、`FrequencyPresetHelper`)
- `compat.jei`(1)、`compat.emi`(2)、`compat.frequency`(2，含 `SymbolPickerScreen` 422 = 最大文件)、`compat.propulsion`(1)
- 根：`CreateRedstoneLinkGUI`、`CreateRedstoneLinkGUIClient`、`Config`、`ClientConfig`

## 3. 入口与注册

主类 `src/main/java/com/ggrgg/createredstonelinkgui/CreateRedstoneLinkGUI.java:50-74`：构造参数 `(IEventBus modEventBus, ModContainer modContainer)`

```java
this.networkProtocol = modContainer.getModInfo().getVersion().toString(); // 版本号当网络协议版本
FrequencyPresetData.ATTACHMENT_TYPES.register(modEventBus);
modEventBus.addListener(this::registerPackets);
RedstoneLinkMenu.MENUS.register(modEventBus); // 另 3 个 MenuType 同理
if (FMLEnvironment.dist == Dist.CLIENT) { modEventBus.addListener(this::registerScreens);
    modContainer.registerConfig(ModConfig.Type.CLIENT, ClientConfig.SPEC); }
modContainer.registerConfig(ModConfig.Type.COMMON, Config.SPEC);
```

`registerPackets`（:76-136）用 `event.registrar(networkProtocol)` 注册 **11 个全部 playToServer** 的 payload；`registerScreens`（:138-143）`RegisterMenuScreensEvent` 绑定 4 个容器界面。菜单为 `DeferredRegister`（`MENUS`）。

## 4. 核心系统

1. **反射式 Create 互操作**：`common/menu/FrequencyHelper.java:45-98` 懒解析 `LinkBehaviour#setFrequency(boolean,ItemStack)`、私有字段 `frequencyFirst/frequencyLast`、私有方法 `notifySignalChange`；失败时退化为直接 field 写入 + `Frequency.of()`（:168-180）。对 Create Utilities 的 `VoidLinkBehaviour` 用 `Class.forName` 同套逻辑（:69-80）。
2. **菜单抽象层**：`common/menu/AbstractLinkMenu.java` 约定 slot 索引契约——0/1 为频率 ghost 槽、2-9 为 4×2 预设槽（:27-45）；`clicked()` 只放行 `PICKUP/THROW`（:120-135）；`processSlotUpdate()` 实现 JEI 式 ghost 行为（Q 清除、有手持物则放 1 个、空手清除，:149-167）；`quickMoveStack` 返回 `ItemStack.EMPTY`、`stillValid` 恒 true。坐标常量与客户端 `FrequencyPresetPanel` 手工对齐并注明"不能直接引用（common 不能引 client 类）"（:32-45）。
3. **玩家级预设存储**：`common/preset/FrequencyPresetData.java` 实现 `INBTSerializable<CompoundTag>`，注册为 NeoForge `AttachmentType` `frequency_presets`，`.serialize(SERIALIZER).copyOnDeath()`（:34-41）；`getAsTag` 固定写 `First`/`Last` 两个键以匹配 Create `ClipboardCloneable`（:104-113）；网络同步走 `toTagList/fromTagList` + `PresetSlotUpdatePayload`。
4. **TinyCreate/Redstone 兼容**：`common/TinyRedstoneCreateCompatibility.java:10-21` 明确注释"绝不调用 `TinyRedstoneLink` 的任何 getDeclaredMethod/方法表访问——`render(PoseStack,…)` 会迫使服务端加载客户端类"，因此只读 `linkProvider` 字段（:100-109）并在 `RedstoneLinkProvider` 上反射 `getFreq1/updateFrequencies/setTransmitter`（:113-224）。
5. **GUI 基类与开窗流程**：`client/screen/AbstractLinkConfigScreen.java` 抽象 4 个界面（覆盖纹理、预览坐标、是否显示 Move 按钮、`addExtraWidgets` 钩子）；`common/network/OpenLinkMenuPayload.java:37-97` 服务端 `distanceToSqr>64` 距离校验 → `be.setChanged()+sendBlockUpdated(pos,…,3)` → `SimpleMenuProvider` 带额外数据写入器 `buf -> buf.writeBlockPos(pos)` 开菜单。
6. **点击/移动交互**：`client/ClientClickHandler.java:27-` 监听 `InputEvent.InteractionKeyMappingTriggered.isUseItem()`，按 `ClientConfig.ClickMode`（SLOT/SHIFT_SLOT/SHIFT_BLOCK，默认 SHIFT_SLOT）判定；移动功能 `client/RedstoneLinkMoveHandler` + `RedstoneLinkMovePayload` + `Config.MOVE_RANGE`（默认 24，1–256）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：11 个 `record implements CustomPacketPayload`，`Type<>` + `StreamCodec.composite(...)`（如 `OpenLinkMenuPayload.java:24-30`），服务端 handler 全在 `context.enqueueWork` 内。
- 配置：COMMON `Config.MOVE_RANGE`；CLIENT `ClientConfig.CLICK_MODE`（枚举）。
- Attachment：1 个（玩家预设，见上）。**datagen：无**（无 `GatherDataEvent`）；数据在 `src/main/resources` 内。

## 6. Mixin

**无 mixin**（全仓无 mixins.json / Mixin 类；兼容全靠反射 + 事件）。

## 7. 值得学的具体做法

1. 用 `modContainer.getModInfo().getVersion().toString()` 当网络协议版本（`CreateRedstoneLinkGUI.java:52`），自动随 mod 版本断开不匹配客户端。
2. 开自定义容器时用 `openMenu(SimpleMenuProvider, buf -> buf.writeBlockPos(pos))` 传自定义数据（`OpenLinkMenuPayload.java:75-78`），避免自造 `MenuType` 之外的同步。
3. 玩家级持久数据用 AttachmentType + `copyOnDeath()`（`FrequencyPresetData.java:34-41`），比 Capability/NBT 手写更省事。
4. 跨 mod 兼容层统一"类不加载即失效"策略：`Class.forName` + 懒解析 + 全部 `try/catch` 吞异常（`FrequencyHelper`、`SableHelper`、`VectorThrusterHelper`），并显式规避会触发客户端类加载的方法表访问（`TinyRedstoneCreateCompatibility.java:10-21`）。
5. 用 JEI `IGuiContainerHandler#getGuiExtraAreas` 返回 `blockPreviewBounds/presetPanelBounds`（`compat/jei/AddonJEIPlugin.java:68-103`），避免 JEI 面板与自绘区域重叠。

## 8. 库/API 扩展点

不适用（非库 mod）；对外仅提供 4 个界面与配置项。
