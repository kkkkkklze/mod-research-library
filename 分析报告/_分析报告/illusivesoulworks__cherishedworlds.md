# illusivesoulworks/cherishedworlds 源码分析报告

## 1. 基本信息

- Mod 名：Cherished Worlds（收藏/置顶世界与服务器）；mod_id：`cherishedworlds`（`gradle.properties:11`）；作者 Illusive Soulworks
- 版本/平台：`version=17.0.0+26.2`、`minecraft_version=26.2`、`java_version=25`、`mod_author=Illusive Soulworks`、`license=LGPL-3.0-or-later`
- 加载器：Fabric（`fabric_version=0.155.2+26.2`、`fabric_loader_version=0.19.3`）+ NeoForge（`neoforge_version=26.2.0.23-beta`）；`settings.gradle` 中 `forge` 子项目存在但被注释掉（`//include("forge")`），根目录仍有 `forge/` 源码与 `META-INF/mods.toml`（Forge 65.0.5）
- Gradle 组织：多加载器模板 `buildSrc/src/main/groovy/multiloader-common.gradle` + `multiloader-loader.gradle`；后者用 Gradle 配置 `commonJava/commonResources` 把 `:common` 的源码和资源直接并入各 loader 子项目（`compileJava { source(configurations.commonJava) }`），并用 `Attribute.of('io.github.mcgradleconventions.loader', String)` 做能力区分——这是"common 源码物理共享、无需 remap 转换"的经典写法
- 编译依赖重点：**SpectreLib**（`spectrelib_version=0.22.0+26.2`，作者自家库，提供 `SpectreConfig/SpectreConfigLoader` 跨加载器配置）；Minecraft 侧主用 Fabric API（`ScreenEvents`/`Screens`）与 NeoForge 事件总线
- 资源模板：`buildSrc/.../multiloader-common.gradle` 的 `processResources` 用 `expand expandProps` 统一展开 `fabric.mod.json / META-INF/mods.toml / META-INF/neoforge.mods.toml / *.mixins.json`（本快照中 `fabric.mod.json` 文件缺失，具体位置未确认）

## 2. 源码规模与包结构

- 34 个 `.java`，共 **1956** 行（实测）
- 包分布：`common/.../cherishedworlds`（根）3、`client` 1、`client/favorites` 3、`client/favorites/impl` 3、`mixin` 1、`mixin/core` 12、`platform` 1、`platform/services` 1；`fabric/...` 3、`neoforge/...` 3（另一份 `forge/...` 3）
- 最大文件：`client/favorites/AbstractFavoritesListWidget.java` 391、`mixin/CherishedWorldsMixinHooks.java` 189、`client/favorites/impl/FavoriteCreateWorldWidget.java` 157、`client/favorites/FavoritesList.java` 89、`impl/FavoriteServersWidget.java` 86、`mixin/core/MixinServerSelectionList.java` 54、`impl/FavoriteWorldsWidget.java` 54

## 3. 入口与注册

- 无注册表类（无方块/物品/包）。Fabric 入口 `fabric/src/main/java/com/illusivesoulworks/cherishedworlds/CherishedWorldsFabricMod.java`：
  ```java
  public void onInitializeClient() {
    CherishedWorldsCommonMod.setup();
    ScreenEvents.AFTER_INIT.register((client, screen, w, h) ->
        ScreenEventHooks.addFavoritesWidget(screen, widget -> Screens.getWidgets(screen).add(widget)));
  }
  ```
- NeoForge 入口 `neoforge/.../CherishedWorldsNeoForgeMod.java`：`@Mod(MOD_ID)` 构造器里 `eventBus.addListener(this::setupClient)` + `CherishedWorldsCommonMod.setupConfig()`；`setupClient` 中 `NeoForge.EVENT_BUS.register(new ScreenEventsListener())`，监听器用 `@SubscribeEvent ScreenEvent.Init.Post` → `ScreenEventHooks.addFavoritesWidget(evt.getScreen(), evt::addListener)`。
- 关键设计：**平台无关的"加控件"抽象** `common/.../client/ScreenEventHooks.java`，两个加载器只提供 `Consumer<AbstractWidget>` 注入方式（`Screens.getWidgets(...)` vs `evt::addListener`），业务代码零平台分支。
- 平台服务：`platform/Services.java` 用 `ServiceLoader.load(IPlatformHelper.class)` 取单例（`Services.PLATFORM`），Fabric/NeoForge 各实现 `isModLoaded` / `getGamePath`（`FabricLoader.getInstance().isModLoaded/getGameDir` vs `ModList.get().isLoaded/FMLPaths.GAMEDIR`）。
- 配置注册：`CherishedWorldsCommonMod.setupConfig()` → `SpectreConfigLoader.add(SpectreConfig.Type.CLIENT, CherishedWorldsConfig.CLIENT_SPEC, MOD_ID)`。

## 4. 核心系统

1. **收藏数据存储**（`common/.../client/favorites/FavoritesList.java`）：静态 `HashSet<String> favorites`，键的语义按界面不同——世界用 `LevelSummary.getLevelId()`，服务器用 `name + ip`，LAN 用 `LanServer.getAddress()`；持久化用原版 NBT：`NbtIo.write` 到 `new File(Services.PLATFORM.getGamePath(), "cherishedworlds-favorites.dat")`，结构 `CompoundTag{"favorites": ListTag<StringTag>}`，写入前 `FileUtils.forceMkdirParent`。
2. **Mixin 逻辑外移（Hooks 模式）**（`common/.../mixin/CherishedWorldsMixinHooks.java`）：12 个 mixin 类都极薄，只做 `cir.setReturnValue(...)` / 转发，全部判断逻辑集中在 189 行的静态钩子类：`getBackupStatus`、`canDelete`、`isNotValidSwap`、`editDeleteButton`、`updateOnlineServers/updateNetworkServers`、`getLevelComparator`、`getChildAt`、`renameFavorite`。好处是逻辑可单测、可跨加载器复用。
3. **排序与"收藏不可删"语义**：`getLevelComparator()` 返回 Comparator，收藏项恒排前面、其余回落到 `LevelSummary#compareTo`；`isNotValidSwap` 禁止拖动收藏服务器到非收藏位；`canDelete` 恒 false（`MixinLevelSummary` 注入 `canDelete` 的 RETURN 改返回值）。
4. **自绘列表图标控件**（`client/favorites/AbstractFavoritesListWidget.java`）：泛型 `<T extends ObjectSelectionList<E>, E extends Entry<E>>`，在父列表左侧 `child.getX() - 16` 画 9x9 星标；逐行做上下裁剪（`topOffset/bottomOffset/startV/endV` 后 `blit` 局部纹理）、`graphics.containsPointInScissor` 防误触、`WidgetTooltipHolder`+`Tooltip.create(Component.translatable("selectWorld.cherishedworlds.favorite"/"unfavorite"))`、无障碍 `NarratedElementType.TITLE/USAGE`、方向键 `FocusNavigationEvent.ArrowNavigation` 焦点与 `applyFocus()` 自动滚屏。
5. **命中测试接管**（`mixin/core/MixinContainerEventHandler.java` + `CherishedWorldsMixinHooks.getChildAt`）：用 `@ModifyReturnValue` 修改 `ContainerEventHandler#getChildAt(DD)` 的 RETURN，让悬停/点击优先落到自绘控件上——把控件挂在屏幕外层容器时的必要手段。
6. **重开备份提示**（`CherishedWorldsConfig.BackupType` = ALL/FAVORITED/NONE + `MixinWorldOpenFlows`）：在 `openWorldCheckVersionCompatibility` 处 `@Redirect` `LevelSummary.backupStatus()`，当旧存档版本低于当前 dataVersion 且（ALL 或该世界被收藏）时返回 `LevelSummary.BackupStatus.UPGRADE_TO_SNAPSHOT`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端；无自定义包）。
- 配置：SpectreLib `SpectreConfigSpec.Builder`，字段 `backupWorldType` 用 `defineEnum("backupWorldType", BackupType.ALL)` 并带 `.comment(...)`、`.translation("cherishedworlds.config.backupWorldType")`；只做客户端（`SpectreConfig.Type.CLIENT`）。
- 数据驱动：无资源包/JSON 驱动；文案走语言键 `selectWorld.cherishedworlds.*`、`gui.narrate.cherishedworlds.*`。
- datagen：无。

## 6. Mixin

- 配置：`common/src/main/resources/cherishedworlds.mixins.json`，`package=...mixin.core`，`compatibilityLevel=JAVA_21`，client 列表 12 个，`injectors.defaultRequire=1`（保证注入目标缺失时直接报错）。
- 注入点汇总：`MixinWorldSelectionList#fillLevels`（INVOKE `WorldSelectionList.setSelected` 之后）→ 重新排序；`MixinServerSelectionList#updateOnlineServers/#updateNetworkServers`（INVOKE `refreshEntries` 处）→ 收藏置顶；`MixinServerSelectionListEntry#swap`(HEAD, cancellable) → 拦截非法交换；`MixinManageServerScreen#onAdd`(HEAD)、`MixinJoinMultiplayerScreen#onSelectedChange`(TAIL) → 改名时同步收藏键；`MixinLevelSummary#canDelete`(RETURN)；`MixinContainerEventHandler#getChildAt(DD)`(`@ModifyReturnValue`)；`MixinWorldOpenFlows` 的 `@Redirect LevelSummary.backupStatus()`。
- Accessor 型：`AccessorWorldSelectionScreen`（`SelectWorldScreen` 的 list/searchBox）、`AccessorWorldSelectionList`（`@Invoker callFillLevels`、`@Accessor getCurrentlyDisplayedLevels`）、`AccessorJoinMultiplayerScreen`（`serverSelectionList`）、`AccessorNetworkServerEntry`。仓库中**未发现任何 accesswidener / accesstransformer 文件**，私有成员访问全用 Mixin accessor，这是比 AT 更跨加载器的方案。

## 7. 值得学的 5 条具体做法

1. **Screen 挂控件的双平台抽象**：把"如何往屏幕加 widget"折叠成 `Consumer<AbstractWidget>`，加载器只实现这一句（`common/.../client/ScreenEventHooks.java`、`fabric/.../CherishedWorldsFabricMod.java`、`neoforge/.../client/ScreenEventsListener.java`）；适用于任何要给原版 GUI 加按钮的 mod。
2. **Mixin 薄壳 + Hooks 静态逻辑**：注入点只转发到 `CherishedWorldsMixinHooks`，逻辑可被外部（含其它 mod）直接调用与测试（`common/.../mixin/CherishedWorldsMixinHooks.java`）。
3. **用 `@ModifyReturnValue` 改 `getChildAt` 实现自绘控件命中**：自绘组件不继承原版按钮时，靠这一招拿到鼠标事件（`mixin/core/MixinContainerEventHandler.java`）。
4. **ServiceLoader 单例平台服务**：`Services.PLATFORM` + `IPlatformHelper`（`platform/Services.java`、`platform/services/IPlatformHelper.java`），common 代码零 loader 引用，文件路径/模组加载查询统一入口。
5. **资源统一 `expand` 展开**：`buildSrc/src/main/groovy/multiloader-common.gradle` 的 `processResources { filesMatching([...]) { expand expandProps } }` 用同一份 `gradle.properties` 填 `fabric.mod.json` 和两个 `mods.toml`，避免多平台元数据漂移。

## 8. 库/API 说明

非库模组，不对外发布 API。唯一"接口层"是内部 `com.illusivesoulworks.cherishedworlds.platform.services.IPlatformHelper`（ServiceLoader 契约，需在 `META-INF/services` 注册实现，本快照中未见该资源文件，未确认），以及跨加载器配置底座 SpectreLib（`com.illusivesoulworks.spectrelib.config.SpectreConfigLoader`）。
