# isXander/YetAnotherConfigLib（YACL）源码分析

## 1. 基本信息

- Mod 名：YetAnotherConfigLib（YACL）；mod_id：`yet_another_config_lib_v3`；作者 isXander；许可证 LGPL-3.0-or-later；modVersion=3.9.6（`gradle.properties:1-3`、`build.gradle.kts:72`）
- 目标版本与加载器（Stonecutter 多版本单源码）：`26.1`（fabric+neoforge）、`26.2-pre-4`（fabric+neoforge）、`26.3-snapshot-4`（仅 fabric），见 `settings.gradle.kts:34-40`、`versions/*/gradle.properties:3`
- Gradle：Stonecutter 0.8.2 + **modstitch 0.8.4**（`dev.isxander.modstitch.base`，`build.gradle.kts:6`）统一 loom / moddevgradle；平台由 `versions/26.1-fabric/gradle.properties:1` = `modstitch.platform=fabric-loom`、`26.1-neoforge/…` = `moddevgradle` 切换；另用 secrets / mod-publish-plugin / grgit（`:13-16`）
- 依赖：fabric-api（BOM + `fabric-resource-loader-v1`）、quiltmc parsers json/gson（JSON5 读写）、twelvemonkeys imageio-core/webp/metadata（WebP/GIF）、fabric-language-kotlin（Kotlin DSL），全部 JiJ；`deps.mixinExtras` 在 `build.gradle.kts:169` 被引用但仓库内 gradle.properties 未定义（未确认当前是否实际启用，mixin 中已用 `@WrapOperation`）
- 它对外即 API：发布 `dev.isxander:yet-another-config-lib`（`build.gradle.kts:334-335`）

## 2. 规模与包结构

实测：`src/main` 242 个 .java / 17313 行 + 6 个 .kt / 779 行；含 testmod 全仓 248 java / 18245 行。主要包（main，文件数）：`config/v2/api/autogen` 28、`config/v2/impl/autogen` 23、`api/controller` 22、`impl` 19、`impl/controller` 18、`api` 18、`gui` 13、`gui/controllers` 11、`config/v3` 10、`gui/controllers/dropdown` 9、`mixin` 8、`gui/controllers/slider` 7、`config/v2/api` 7、`dsl`(kotlin) 5、`platform` 4。

最大文件：`gui/OptionListWidget.java` 662、`gui/YACLScreen.java` 540、`gui/controllers/ColorPickerWidget.java` 496、`gui/controllers/string/StringControllerElement.java` 479、`impl/ListOptionImpl.java` 460、`impl/OptionImpl.java` 355、`config/v2/impl/ConfigClassHandlerImpl.java` 291、`config/v2/impl/serializer/GsonConfigSerializer.java` 269。

## 3. 入口与注册

唯一入口 `src/main/java/dev/isxander/yacl3/platform/PlatformEntrypoint.java`，用 Stonecutter 注释块在一个文件里写三份实现：

```java
/*? if fabric {*/
public class PlatformEntrypoint implements ClientModInitializer {
    public void onInitializeClient() {
        YACLConfig.HANDLER.load();
        ResourceLoader.get(PackType.CLIENT_RESOURCES).registerReloadListener(YACLImageReloadListener.getId(), new YACLImageReloadListener());
/*?} elif neoforge {*/
@Mod("yet_another_config_lib_v3") ... modEventBus.addListener(AddClientReloadListenersEvent.class, ...)
```

无 DeferredRegister/Registrate（纯客户端库、无方块物品）。mod 元数据由 modstitch 从 `src/main/templates/META-INF/{mods.toml,neoforge.mods.toml}` 生成，mixin 配置自动写入 manifest（`build.gradle.kts:110-116`）。自身配置 `platform/YACLConfig.java:8-13` 用的就是自己的 `ConfigClassHandler` + `@SerialEntry`，`yacl.json5`。

## 4. 核心系统

**（1）Option/StateManager 状态模型** — `api/StateManager.java`、`api/Binding.java`、`impl/OptionImpl.java`
- UI 不直接写绑定：`Option.requestSet()` → `stateManager.set()` 暂存 pending，`applyValue()` 才提交（`impl/OptionImpl.java:125-152`）；`forgetPendingValue/resetToDefault/sync/isSynced` 支撑"改动未保存"与撤销。
- 四种 StateManager：`SimpleStateManager`（pending）、`InstantStateManager`（set 即 apply）、`ImmutableStateManager`、`XMappedStateManager`；`StateManager.xmap(fn,fn)` 让不同类型 Option 共享同一后端状态。
- `Binding.minecraft(OptionInstance)` 借 `mixin/OptionInstanceAccessor` 拿到 initialValue 接入原版选项。

**（2）注解自动生成 GUI（autogen）** — `config/v2/api/autogen/*`（28 个注解）、`config/v2/impl/autogen/OptionFactoryRegistry.java`、`ConfigClassHandlerImpl.generateGui()`
- 字段标 `@AutoGen(category, group)` + 类型注解（`@TickBox/@IntSlider/@Dropdown/@ListGroup/@Boolean(formatter=…)…`）；`OptionFactoryRegistry` 用 `Map<Class<?>, OptionFactory>` 注册 18 个工厂，字段上工厂注解数必须为 1，否则 warn 并跳过（`OptionFactoryRegistry.java:24-56`）。
- 分组/联动：`@MasterTickBox({"testTickBox", …})` 按字段名引用同组 option 做"总开关"；`OptionAccess`/`OptionAccessImpl` 存 `Map<字段名, Option<?>>` 并 `checkBadOperations()` 校验引用不存在的字段。
- i18n key 约定 `yacl3.config.<id>.title / category.<c> / category.<c>.group.<g>[.desc]`（`ConfigClassHandlerImpl.java:139-165`）。

**（3）GUI 框架** — `gui/YACLScreen.java`、`gui/OptionListWidget.java`、`gui/tab/*`
- `TabManager`/`TabExt`/`ScrollableNavigationBar` 自管分类 tab；`CategoryTab` 内含保存/取消/撤销按钮与搜索框；`updateGlobalSearch`（`YACLScreen.java:299`）跨 tab 搜索。
- `OptionListWidget extends YACLSelectionList` 自绘列表，条目有 `updateSearchQuery/isViewable/refreshVisibilityState`（`:260-300`），折叠分组时只隐藏不卸载。

**（4）Controller 体系** — `api/Controller.java`、`api/controller/*Builder`、`impl/controller/*BuilderImpl`、`gui/controllers/*`
- `Controller.provideWidget(screen, Dimension)` 产出 `AbstractWidget`；三种字符串控制器（field/dropdown/cycling）与数值 slider/field 二选一；弹出式控制器走 `ControllerPopupWidget`/`PopupControllerScreen`，由 `YACLScreen.currentPopupController` 管理。

**（5）配置序列化 v2** — `config/v2/impl/serializer/GsonConfigSerializer.java`、`config/v2/impl/ConfigClassHandlerImpl.java`
- 反射发现 `@SerialEntry`/`@AutoGen` 字段；`@SerialEntry(comment=…, required=…, nullable=…)`；JSON5 时用 `JsonWriter.comment()` 把注释写进文件（`:57-60`），字段名 `LOWER_CASE_WITH_UNDERSCORES`。
- 加载先写进**新实例**再整体替换，失败则保持原配置；逐字段 try/catch，`LoadResult = SUCCESS/DIRTY/NO_CHANGE/FAILURE`，缺 `required` 字段 → DIRTY → 立即重存（`ConfigClassHandlerImpl.java:204-250`）。
- 默认适配器：`Component`（包装 vanilla Codec）、`Style`、`Color`(int RGB)、`Item`(注册名)。

**（6）新的 Codec 式配置 v3（实验性）** — `config/v3/CodecConfig.java`、`JsonFileCodecConfig.java`、`AbstractConfigEntry.java`
- 配置字段变成对象：`ConfigEntry<T>` 自带 `value/defaultValue/modifyGet/modifySet`；`CodecConfig` 自身实现 `Codec<S>`，`encode/decode` 用 `ops.mapBuilder()` 遍历 entries，彻底摆脱反射；`JsonFileCodecConfig` 只负责文件读写 + `SaveError/LoadError` 错误分类。

**（7）图片系统** — `gui/image/`：`AnimatedDynamicTextureImage`/`DynamicTextureImage`/`ResourceTextureImage` + `ImageRendererManager`，`YACLImageReloadListener` 在资源重载时预加载 WebP/GIF（`preloadComplexImageFormats` 开关）。

## 5. 网络 / 数据驱动 / datagen

- 网络：**无**（全仓无 `CustomPacketPayload`/payload 注册，纯客户端本地状态）。
- 数据驱动：无；datagen：无。配置持久化即 §4(5)(6)。

## 6. Mixin

- `src/main/resources/yacl.mixins.json`（`client`, JAVA_17）：`AbstractSelectionListMixin`(`@WrapOperation`)、`MinecraftMixin`(`@Inject`)、`GuiGraphicsExtractorMixin`、四个 Accessor（`AbstractSelectionListAccessor`、`GuiAccessor`、`OptionInstanceAccessor`、`TabNavigationBarAccessor`，后者 `@Accessor("tabManager")`/`"tabButtons"` 等）。
- `src/main/resources/yacl-fabric.mixins.json`（仅 fabric）：`ContainerEventHandlerMixin` 用 `@Redirect` 改写 `ContainerEventHandler` 交互。

## 7. 值得学的 5 条

1. **单源码多版本/多加载器**：Stonecutter 的 `/*? if fabric {*/ … /*?}*/` 注释切换 + `versions/*/gradle.properties` 注入版本常量，配合 modstitch 一份 build 脚本产出 loom 与 moddevgradle 两种构建（`platform/PlatformEntrypoint.java:1-30`、`versions/26.1-neoforge/gradle.properties`）。
2. **平台差异只留一处**：`platform/YACLPlatform.java` 集中 `getConfigDir/isDevelopmentEnv/getEnvironment`，其余代码零 loader 判断，改动面极小。
3. **pending/apply 分离**：`StateManager` 把"编辑中的值"和"已提交值"解耦（`impl/OptionImpl.java:125-152`），界面可以做到取消/撤销/未保存提示而不污染业务对象。
4. **注解工厂注册表**：`Map<注解类, OptionFactory>` + `OptionFactory` 公开接口（`OptionFactoryRegistry.registerOptionFactory`）让第三方为自定义注解扩展 autogen，而不改核心。
5. **写文件时注入注释**：序列化走 Quilt `JsonWriter` + `jsonWriter.comment(serial.comment())` 输出 `json5`（`GsonConfigSerializer.java:52-64`），用户配置文件自带字段说明。

## 8. 公开 API 与接入

- 构建式 API：`dev.isxander.yacl3.api`（`YetAnotherConfigLib`/`ConfigCategory`/`OptionGroup`/`Option`/`ListOption`/`ButtonOption`/`LabelOption`/`OptionDescription`/`OptionFlag`/`Controller`/`Binding`/`StateManager`；静态工厂 `createBuilder()`）。
- 配置 API：`config.v2.api`（`ConfigClassHandler`、`SerialEntry`、`ConfigSerializer`、`GsonConfigSerializerBuilder`、`autogen.*`）、`config.v3`（`@ApiStatus.Experimental`，`CodecConfig`/`JsonFileCodecConfig`）。
- Kotlin DSL：`dev.isxander.yacl3.dsl`（`RootDsl/CategoryDsl/GroupDsl/OptionDsl`、委托 `registering`/`ref`/`futureRef`，用 `CompletableFuture` 解耦"先引用后注册"，`dsl/API.kt:20-60`）。
- 接入方式：Maven 坐标 `dev.isxander:yet-another-config-lib:<ver>`（`maven.isxander.dev/releases`），fabric 侧需 fabric-api + fabric-language-kotlin。
