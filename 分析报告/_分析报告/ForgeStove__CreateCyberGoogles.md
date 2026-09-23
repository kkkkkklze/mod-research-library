# ForgeStove/CreateCyberGoogles 源码分析报告

## 1. 基本信息

- Mod 名：Create: Cyber Goggles；modId `create_cyber_goggles`；作者 ForgeStove（credits：CMS、misterpemodder 等）
- 目标：MC 1.21.1 / NeoForge 21.1.248（`gradle.properties:loaderVersion`）；版本 8.6.1，MIT
- 定位：**纯客户端**辅助 mod（`@Mod(value = CCG.ID, dist = Dist.CLIENT)`），为 Create 6 提供模块化 goggles 信息/提示/覆盖层
- Gradle：Kotlin DSL（`build.gradle.kts`），NeoForge moddev（编译器参数含 `-XX:+AllowEnhancedClassRedefinition` 与 Mixin 热替换 agent `dev.vfyjxf:mixin-hotswap-agent`，`build.gradle.kts:20-33`）
- 编译/运行依赖（`build.gradle.kts:49-76`）：create 6.0.11-300、flywheel 1.0.6-44、ponder 1.0.87、Registrate、sable/sable-companion、aeronautics/offroad/simulated、veil；compileOnly：create-enchantment-industry、dragons-plus、EMI、sophisticated-core、ars_nouveau、appliedenergistics2、thirst；runtimeOnly Jade；`implementation` 里还含 JEI 与 createfluidlogistic
- 值得一提：`implementation("com.simibubi.create:...) { isTransitive = false }`（手工控传递依赖），并有 Modrinth/CurseForge 发布配置（`build.gradle.kts:87-96`）

## 2. 源码规模与包结构

- 263 个 `.java`，总 16849 行（`find -exec cat {} + | wc -l`）
- 两套包（同一仓库内嵌了自己的库 `flexconfig`）：
  - `io.github.forgestove.flexconfig`：69 文件 / 4401 行——通用反射式 TOML 配置框架（含配置 GUI、网络锁）
  - `io.github.forgestove.create_cyber_goggles`：194 文件 / 12448 行
- 主要包文件数：`mixin/misc` 45、`flexconfig/client/gui` 32、`mixin/provider` 32、`mixin/compact` 19、`core/util` 19、`core/event` 19、`flexconfig/api` 15、`core/factory` 14、`core/tooltipRenderer` 11、`mixin/goggles` 10、`mixin/tooltip` 6、`api` 5、`mixin/accessor` 4
- 最大文件：`core/factory/AutoReplenishScreen.java`(1045)、`core/event/forceOverlay/ForceOverlayRenderer.java`(550)、`mixin/misc/StockKeeperReplenishEntryMixin.java`(498)、`flexconfig/client/gui/ColorPickerScreen.java`(303)、`core/util/RedstoneRequesterInteractions.java`(296)、`core/util/GoggleTooltipUtil.java`(294)、`flexconfig/tree/RootConfigNode.java`(237)
- 资源仅 2 个文件：`src/main/resources/create_cyber_goggles.mixins.json`、`META-INF/accesstransformer.cfg`（无 assets/lang，翻译键大量复用 Create 自带的 `create.gui.goggles.*`）

## 3. 入口与注册

`CCG.java` 极简（11 行），只做 ID、Logger 与配置初始化：

```java
@Mod(CCG.ID) public final class CCG {
    public static final String ID = "create_cyber_goggles";
    public static final CCGConfig config = ConfigRegistry.init(CCGConfig.class);
}
```

真正的注册集中在 `CCGClient.java`（`@Mod(value=ID, dist=Dist.CLIENT)`）：构造器里 `container.getEventBus()` + `NeoForge.EVENT_BUS` 上以方法引用批量 `addListener`（KeyInput::key、ItemTooltip::itemTooltip、TooltipOverlay::register 等 20+ 个），并用 `CCGMods.simulated.executeIfInstalled(() -> ...)` 条件注册可选依赖相关监听器（`CCGClient.java:26,43-46`）。无 DeferredRegister/Registrate 内容注册——纯 mixin + 事件驱动。

## 4. 核心系统

1. **flexconfig 配置框架（最大亮点）**：`@Config(modId)` 标注 POJO，`ConfigRegistry.init(Class)` 建 `ConfigHandler`→`ConfigSerializer`，反射遍历 `@Category` 字段生成 TOML；`savedConfig` 与 `activeConfig` 双实例分离（运行时锁定值只写 active，不污染 TOML，`ConfigRegistry.java:applyLockedValue`）；注解驱动校验/交互：`@IntRange/@DoubleRange/@ColorValue/@Condition("simulated")/@WarnCheat/@RequiresRestart/@OnChange(SoundReloadHandler.class)/@Order`（`flexconfig/api/`，配置示例 `CCGConfig.java:7-170`）。
2. **配置 GUI**：`flexconfig/client/gui` 32 文件——`ConfigScreen`、`ConfigCategoryTab`、`ConfigEntryList` + `entry/*ConfigEntry`（Boolean/Int/Float/Double/Long/Enum/String/Keybind/Color/Point/Capturable…），`EntryTypeRegistry` 按字段类型派发控件，`ColorPickerScreen`+`ColorPreviewWidget`、`EnumDropdownScreen`、`SmoothScroll`、`Highlight` 等自绘组件。
3. **配置同步/服务端锁**：`flexconfig/network` 用 NeoForge `RegisterPayloadHandlersEvent.registrar(FlexConfig.ID).optional()` 注册 `ConfigLockPayload`(playToServer)/`ConfigSyncPayload`(playToClient)；服务端 `ServerConfigLockStore` 存锁定项，`handleConfigLockServer` 校验 `player.hasPermissions(2)`，改动后 `PacketDistributor.sendToAllPlayers` 广播；客户端收到后 `context.enqueueWork` 刷新打开的 ConfigScreen（`ConfigNetwork.java:14-48`）。
4. **goggles 信息 provider mixin 群**：`mixin/provider` 32 个类对 Create 的 BlockEntity 注入 `IHaveGoggleInformation#addToGoggleTooltip`（`@Inject(at=HEAD, cancellable=true)` + `cir.setReturnValue(...)`），统一实现 `Self<T>` 契约拿 `thiz()`，内容由 `core/util/GoggleTooltipUtil` 各静态方法拼装，用 `ccg$` 前缀命名避免冲突（`mixin/provider/BasinBlockEntityMixin.java`）。
5. **工具提示渲染体系**：`api/TooltipRenderer`(supports/canRender/width/height/render) + `core/tooltipRenderer` 11 个实现 + `tooltip/*Mixin`（`@WrapMethod` 包裹 Create 的 `containedFluidTooltip`，`mixin/tooltip/IHaveGoggleInformationMixin.java`）；`core/event/TooltipOverlay`、`ItemTooltip` 负责事件与 tooltip component 注册。
6. **可选依赖兼容层**：`core/util/CCGMods`（enum，成员=modid）提供 `isLoaded()`（`LoadingModList.get().getModFileById(id) != null`）、`runIfInstalled(Supplier)`→`Optional`、`executeIfInstalled(Runnable)`、`rl(path)`，配合 `compat/*`（jei/thirst/fluidlogistics）与 `mixin/compact/*` 分包；`@Condition("simulated")` 让配置项在依赖缺失时不显示（`CCGConfig.java:13`）。
7. **子层级受力可视化**：`ForceOverlay`/`ForceOverlayRenderer`(550 行) 在 `RenderLevelStageEvent.Stage.AFTER_LEVEL` 用 `PoseStack`+`RenderSystem.getModelViewStack().pushMatrix()/set(modelViewMatrix)` 渲染力箭头、质心，依赖 Sable/Aeronautics API（`ForceGroups`、`SubLevelContainer.getContainer(level)`）。

## 7. 值得学的 5 条具体做法

1. **配置即 POJO + 注解**：字段默认值就是默认配置，反射生成 TOML 与 GUI，无需为每个选项写注册代码（`CCGConfig.java` + `flexconfig/ConfigSerializer.java:serialize`）；适用：选项上百的客户端 mod。
2. **active/saved 双配置实例**：服务端下发的"锁定值"只改 active，`resetToSaved` 从 TOML 重新加载覆盖两份（`ConfigRegistry.java`）；适用：需要"服务器强制值 vs 玩家本地值"分离的场景。
3. **可选依赖用枚举 + Supplier 包装**：用 `CCGMods.simulated.executeIfInstalled(...)` 而不是硬编码判断，缺失即静默跳过（`core/util/CCGMods.java`）；适用：兼容一堆可选 mod。
4. **mixin 按"目标类型"分包**：`provider/`（IHaveGoggleInformation 提供者）、`compact/<dep>/`（第三方兼容）、`accessor/`、`tooltip/`、`wrench/` 目录化；mixin json 里用全限定相对路径列出，且 `"required": false, "minVersion": "0"`（`create_cyber_goggles.mixins.json`）。
5. **`@WrapMethod` 优于大量 `@Redirect`**：包裹 Create 方法并保留 `original.call(...)` 兜底路径（`mixin/tooltip/IHaveGoggleInformationMixin.java`），需要 MixinExtras；调试期用 mixin 热替换 agent（`build.gradle.kts:20-33`）。

## 8. 公开 API（准库模组）

`io.github.forgestove.create_cyber_goggles.api`：`TooltipRenderer`（工具提示扩展接口）、`AutoTooltipRenderer`、`ItemRenderable`、`OutlineRenderable`、`SelfKineticInfo`。`flexconfig` 是完整可复用库：`flexconfig.api`（`@Config`/`@Category`/`@IntRange`/`@Condition`/`@ColorValue`/`@OnChange`/`@WarnCheat`/`@RequiresRestart`/`@Order`/`@StringLength`/`@DoubleRange`… 15 文件）、扩展点 `EntryTypeRegistry`（自定义控件类型）、`ConfigScreenFactory`、`ClientLockManager`。接入方式：依赖本 jar → 写 `@Config("yourid")` POJO → `ConfigRegistry.init(YourConfig.class)`。

## 5/6. 网络与 Mixin 摘要

网络：仅 flexconfig 的 2 个 payload（`ConfigLockPayload`、`ConfigSyncPayload`），`register(...).optional()`，服务端权限 2 校验 + 全量广播。
Mixin：单配置文件 `src/main/resources/create_cyber_goggles.mixins.json`（`package: ...mixin`，全部列在 `"client"` 数组，约 120 个类），代表目标：`GogglesItem`/`GoggleOverlayRenderer`/`KineticBlockEntity`（goggles 包）、`IHaveGoggleInformation#containedFluidTooltip`（@WrapMethod）、各 Create BlockEntity 的 `addToGoggleTooltip`（provider 包）、`EditBox`/`Font`/`FilesHelper`/`NbtAccounter`（misc 包）。另有 `META-INF/accesstransformer.cfg`。
