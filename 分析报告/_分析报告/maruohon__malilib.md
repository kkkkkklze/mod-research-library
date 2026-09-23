# maruohon/malilib 源码分析报告

## 1. 基本信息

- Mod 名 / id：MaLiLib / `malilib`；作者 masa；许可证 `LGPLv3`（`LICENSE.txt`）；`environment: client`，纯客户端库。
- **重要前提**：本次检出的是 `bugfix/ornithe/1.12.2-0.60.x` 分支（commit `e12414e`，2025-04-02），且本地 clone 为单分支（`git config remote.origin.fetch` 只 fetch 该分支）。`gradle.properties` 显示 `minecraft_version = 1.12.2`、`mod_version = 0.60.2`、`fabric_loader_version = 0.15.3`、`osl_version = 0.11.3`，依赖 `minecraft: 1.12.x` + `osl-entrypoints`/`osl-resource-loader`。所以本地代码**不是** 1.20.1/1.21 版本（未确认，仓库其他分支未 fetch）。
- Gradle：`fabric-loom 1.4-SNAPSHOT` + Ornithe `ploceus 1.4.2`（MCP stable 1.12/39 映射）、`maven-publish`、Java 8（`options.release = 8`，即便新版 MC 也只用 Java 8 语法，见 README）。
- 依赖：fabric-loader、modmenu（`compat/modmenu/ModMenuImpl`）、jsr305、OSL。
- `README.md` 明确说明："new code"（重写版）只存在于 `liteloader_1.12.2` 与 `ornithe/1.12.2` 分支，所有 1.13+/1.20.1/1.21 分支仍是 2019 年的旧代码。**学新架构只有本分支可看**，这也是本报告的定位。

## 2. 源码规模与包结构

576 个 `.java`，73926 行（`find src/main/java -name '*.java' | wc -l` 与 `-exec wc -l {} +`），仅 `src/main`，无测试源集。

一级包（文件数）：`gui` 229、`util` 101、`config` 73、`render` 37、`input` 31、`overlay` 28、`action` 23、`event` 16、`mixin` 12、`network` 8、`listener` 4、`interoperation` 2、`registry` 1。二/三级重点：`gui/widget` 130（其中 `widget/list/entry` 57、`entry/config` 36）、`config/option` 38、`util/data` 45、`render/text` 16、`overlay/widget` 16、`action/builtin` 7、`util/datadump` 7。

最大文件：`gui/widget/BaseTextFieldWidget.java`(1244)、`gui/BaseScreen.java`(1167)、`gui/widget/DropDownListWidget.java`(1087)、`gui/widget/list/BaseFileBrowserWidget.java`(943)、`render/ShapeRenderUtils.java`(891)、`gui/widget/list/BaseListWidget.java`(881)、`util/data/json/JsonUtils.java`(875)、`gui/widget/BaseWidget.java`(872)、`util/position/LayerRange.java`(832)、`config/util/ConfigLockHandler.java`(724)。

## 3. 入口与注册

`fabric.mod.json` 的 `client-init` → `malilib.MaLiLib`（实现 OSL `ClientModInitializer`，类本身几乎为空，只提供 `LOGGER`/`debugLog`）。真正的注册在游戏初始化完成后由 `event/dispatch/InitializationDispatcherImpl.java:34` 触发 `MaLiLibInitHandler.registerMalilibHandlers()`：

```java
Registry.CONFIG_MANAGER.registerConfigHandler(BaseModConfig.createDefaultModConfig(MOD_INFO, CONFIG_VERSION, CATEGORIES));
Registry.CONFIG_SCREEN.registerConfigScreenFactory(MaLiLibReference.MOD_INFO, MaLiLibConfigScreen::create);
Registry.CONFIG_TAB.registerConfigTabSupplier(MaLiLibReference.MOD_INFO, MaLiLibConfigScreen::getConfigTabs);
Registry.HOTKEY_MANAGER.registerHotkeyProvider(MaLiLibHotkeyProvider.INSTANCE);
Registry.RENDER_EVENT_DISPATCHER.registerGameOverlayRenderer(Registry.INFO_OVERLAY);
ConfigLockPacketHandler.updateRegistration(true);
```

注册框架不是 DeferredRegister/Registrate，而是**自建静态服务定位器** `registry/Registry.java`（64 行，全部 `public static final` 字段，如 `CONFIG_MANAGER`、`HOTKEY_MANAGER`、`CLIENT_PACKET_CHANNEL_HANDLER`、4 个事件 dispatcher）。外部 mod 从 `Registry.*` 拿管理器注册自己的东西，再用 `InitializationDispatcher.registerInitializationHandler()`（按 priority 排序）拿到"注册时机"。

## 4. 核心系统

1. **配置系统**（`config/`）：`BaseConfig` → `BaseConfigOption<T>`（`option/BaseConfigOption.java`，带 `valueChangeCallback`/`valueLoadCallback`/`valueChangeListeners`/`locked`/`lockOverrideMessages`）+ `BaseGenericConfig<T>`（值存取）。25+ 具体类型在 `config/option/`（`BooleanConfig`、`BooleanAndInt/Double/FileConfig`、`HotkeyedBooleanConfig`、`ColorConfig`、`Vec2iConfig`、`OptionListConfig`…），列表型在 `config/option/list/`（`BlockListConfig`、`ItemListConfig`、`BlackWhiteListConfig`…）。层级：`category/`（`ConfigOptionCategory`）→ `group/`（`ExpandableConfigGroup`、`PopupConfigGroup`）。能力：`oldNames` 兼容旧键名、`ConfigDataUpdater` 做版本迁移（`config/JsonModConfig.java`）、`ConfigManagerImpl` 用 `Map<ModInfo, ModConfig>` 一 mod 一配置。
2. **配置 GUI 体系**（`gui/config/` + `gui/widget/list/entry/config/`）：`ConfigWidgetRegistry.java` 用 `HashMap<Class<? extends ConfigInfo>, ConfigOptionWidgetFactory<?>>` 做"配置类型 → 控件"映射，缺省回退 `MissingConfigTypeFactory`，外部 mod 可注册自定义配置类型的控件与搜索信息（`ConfigSearchInfo`）。`ConfigScreenRegistry` 存 `Map<ModInfo, Supplier<BaseScreen>>`；`ConfigTabRegistryImpl` 支持"扩展 mod 往别的 mod 配置界面加 tab"（`registerExtensionModConfigTabSupplier`，父 mod 供应商插 index 0）。
3. **多键 Keybind + Action 系统**（`input/`、`action/`）：`KeyBindImpl.java` 每个绑定持 `IntArrayList keyCodes`（支持一绑多键、按键顺序敏感 `orderSensitive`、`exclusive`、`toggle`、`priority`），行为由 `KeyBindSettings` 13 个字段描述（`Context.INGAME/GUI`、`KeyAction`、`CancelCondition`、`allowExtraKeys`…）。按键触发的逻辑被外移到 Action 体系：`ActionRegistry`/`ActionList`/`ActionGroup`/`AliasAction`/`MacroAction`/`ParameterizedAction` + `builtin/`（BooleanToggle/Enable/Disable、`ConfigActions`、`UtilityActions`），于是同一动作可由热键、`ActionWidgetScreen`（命令面板）或命令触发。扩展点 `HotkeyProvider`（`getAllHotkeys()` / `getHotkeysByCategories()`）+ `CustomHotkeyManager`。
4. **事件分发层**（`event/` + `event/dispatch/`）：不直接用 loader 事件 API，定义 `ClientTickHandler`、`ClientWorldChangeHandler`、`PostGameOverlayRenderer`、`PostScreenRenderer`、`PostItemTooltipRenderer`、`PostWorldRenderer`、`InitializationHandler`（继承 `PrioritizedEventHandler`），各自有 interface + `*Impl` 单例；渲染回调用 profiler push 包裹。
5. **消息/覆盖层系统**（`overlay/`）：`InfoOverlay` + `InfoWidgetManager` + `InfoWidgetRegistry` + `overlay/widget/{sub}`，多 mod 的信息行自动排布；`MessageDispatcher` 是流式 builder（`type()/console()/location()/time()/marker()`），`MessageRedirectManager` 做输出重定向，消息支持 `StyledText` 富文本。
6. **文本渲染管线**（`render/text/`）：`StyledText`/`StyledTextLine`/`StyledTextSegment`/`TextStyle`/`StyledTextParser` 把字符串解析成带样式段（含缓存 `StyledTextCacheKey`），`StringListRenderer`/`SingleTextLineRenderer` 负责排布换行与 Glyph。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：`network/PluginChannelHandler` + `ClientPacketChannelHandlerImpl.java`（`ArrayListMultimap<ResourceLocation, PluginChannelHandler>`；`registerClientChannelHandler` 时向服务器发 `minecraft:register`/`unregister` 自定义负载，频道名用 `\0` 拼接，见 `sendRegisterPacket`）。`PacketSplitter` 处理超长包分片，`PacketUtils.retainedSlice` 零拷贝切片。现存实现一个：`message/ConfigLockPacketHandler.java`，频道 `malilib:cfglock`，载荷 = `boolean resetFirst` + JSON 字符串（`JsonUtils.parseJsonFromString`），服务器可下发配置锁定；配套 `config/util/ConfigLockUtils.java`、`ConfigLockHandler.java`(724 行)。
- **配置持久化**：`config/JsonModConfig.java`（`loadFromFile`/`saveToFile`/`updateConfigDataBeforeLoading`/`ConfigDataUpdater` 接口）+ `config/serialization/JsonConfigSerializerRegistry.java`，按类注册三组接口：`ConfigToJsonSerializer`、`ConfigFromJsonLoader`、`ConfigFromJsonOverrider`；`JsonConfigSerializers`/`JsonConfigDeserializers` 提供默认实现。写入方式可配（`FileWriteType.TEMP_AND_RENAME`，见 `MaLiLibConfigs.Generic.CONFIG_WRITE_METHOD`）。
- **JSON 工具**：`util/data/json/JsonUtils.java`（875 行）统一 GSON（`setPrettyPrinting`），大量 `hasX/getXOrDefault/getXIfExists/addIfNotEqual/blockPosToJson` 风格 API，是"省略默认值"的紧凑写盘基础。
- **数据驱动 / 工具数据**：`util/data/palette/`（`Palette`/`HashMapPalette`/`LinearPalette`/`PaletteResizeHandler`）用于渲染批次的 id→索引分配与扩容；`util/datadump/`（`DataDump` + `RowFormatter{AsciiTable,CompactTable,Csv,SimpleText}`）把游戏数据导出成表格/CSV；`util/game/wrap/GameUtils` 包一层版本差异；`util/position`、`util/inventory`、`util/nbt` 为通用工具。
- **datagen**：无（`grep -rln "DataGenerator|datagen" src/main/java` 无结果），资源仅 `en_us.lang` + 贴图 + 一个 shader。

## 6. Mixin

配置 `src/main/resources/mixins.malilib.json`（`required: true`, `defaultRequire: 1`, 12 个 client mixin，分 5 组）：

- `event/MinecraftMixin`：`init`(RETURN)、`runTick()V`(INVOKE getSystemTime)、`loadWorld` HEAD/RETURN → 触发初始化/客户端 tick/世界切换事件。
- `input/MinecraftMixin`：`runTickKeyboard`、`runTickMouse` 在 `dispatchKeypresses()` / `Mouse.getEventButton()` 处**可取消**注入，抢占原始输入；`input/GuiScreenMixin`：`handleInput` 在 `handleKeyboardInput()` 与 `handleMouseInput()` 调用点取消，实现 GUI 内热键与自定义点击处理。
- `command/GuiScreenMixin`：`sendChatMessage(String;Z)` 处注入 → 拦截客户端命令（`malilib/command/`）。
- `command/TabCompleterMixin`：`requestCompletions`/`setCompletions`(@ModifyVariable)/`complete()`(@ModifyArg) → 自定义补全。
- `network/MixinNetHandlerPlayClient`：`handleCustomPayload` RETURN → 交给 `ClientPacketChannelHandler.processPacketFromServer`。
- `render/EntityRendererMixin`：`renderWorldPass(IFJ)`、`updateCameraAndRender(FJ)` 两处 → 世界/屏幕后置渲染回调；`render/GuiScreenMixin`：`renderToolTip` RETURN → tooltip 后置渲染。
- `access/`：`AbstractHorseMixin`、`GuiContainerMixin`、`NBTBaseMixin`、`NBTTagLongArrayMixin` 提供访问器。

## 7. 值得学的 5 条做法

1. **单一静态 Registry 作 API 门面**：所有管理器/dispatcher 集中为 `public static final` 字段（`registry/Registry.java`），下游 mod 只 import 一个类；内部方法用 `NOT PUBLIC API - DO NOT CALL` 注释标记（全库 9 个文件），不额外拆 api 包。适用：任何前置库。
2. **注册时机用优先级 dispatcher**：`InitializationDispatcherImpl` 让外部 `InitializationHandler` 按 `getPriority()` 排序后统一 `registerModHandlers()`，再 `loadAllConfigsFromFile()`，避免 loader 事件顺序踩坑（`event/dispatch/InitializationDispatcherImpl.java`）。适用：多 mod 扩展同一注册流程。
3. **配置类型 → 控件注册表 + 缺省回退**：`ConfigWidgetRegistry` 用 Class 作 key，未注册类型走 `MissingConfigTypeFactory` 而不是崩溃（`gui/config/registry/ConfigWidgetRegistry.java`）。适用：可扩展的配置界面。
4. **配置项自带迁移与锁定元数据**：`BaseConfigOption.lockOverrideMessages` + `lockMessage` + `ConfigDataUpdater`（`config/option/BaseConfigOption.java:20`、`config/JsonModConfig.java:100`），使"服务器锁配置""旧版本存档升级"成为框架能力而非各处 if。适用：需要服务端/整合包管控的 mod。
5. **流式消息 + action 解耦**：`MessageDispatcher`（`.console().translate(key,args)`）统一所有提示输出，动作逻辑从热键里抽到 `Action` 层，同一逻辑可被热键/命令/界面复用（`overlay/message/MessageDispatcher.java`、`action/ActionRegistry.java`）。适用：需要大量开关与提示的客户端 mod。

## 8. 公开 API 与外部接入方式

不以独立 `api` 包暴露，约定俗成的接入面在 `malilib/` 根包与暴露的接口：配置注册 `Registry.CONFIG_MANAGER.registerConfigHandler(...)` + `BaseModConfig.createDefaultModConfig(ModInfo, version, categories)`；配置界面 `Registry.CONFIG_SCREEN.registerConfigScreenFactory(...)`、`Registry.CONFIG_TAB.registerConfigTabSupplier(...)`、`Registry.CONFIG_TAB_EXTENSION` + `registerExtensionModConfigTabSupplier`（扩展别的 mod 的界面）；热键 `HotkeyProvider`/`SimpleHotkeyProvider`/`HotkeyCategory` 经 `Registry.HOTKEY_MANAGER.registerHotkeyProvider`；网络 `PluginChannelHandler` 经 `Registry.CLIENT_PACKET_CHANNEL_HANDLER.registerClientChannelHandler`；事件 `Registry.*_EVENT_DISPATCHER.register*`；数据互操作 `interoperation/BlockPlacementPositionProvider`（注册可覆盖方块放置坐标的 provider，供 Litematica 类 mod 使用）；图标 `IconRegistry`、信息行 `InfoWidgetRegistry`、序列化 `Registry.JSON_CONFIG_SERIALIZER`。所有跨 mod 身份用 `util/data/ModInfo`（modId + 显示名）标识。
