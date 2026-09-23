# AHilyard/LegendaryTooltips 源码分析报告

## 1. 基本信息

- Mod 名：Legendary Tooltips / mod_id：`legendarytooltips` / 作者：Grend（anthonyhilyard）/ 版本 1.5.5
- 目标：**MC 1.21.1**，三平台 **fabric + forge + neoforge**（`gradle.properties`：`enabledPlatforms=fabric,forge,neoforge`、forgeVersion 1.21.1-52.0.47、neoforgeVersion 21.1.115）
- 许可证：`CC BY-NC-ND 4.0`（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）
- Gradle：`architectury-plugin` + `dev.architectury.loom` + `io.github.goooler.shadow`；**注意根 `build.gradle:1-33` 的 buildscript 用 `flatDir dirs '../architectury-loom/build/libs'` 引用 `architectury-loom-1.7.9999`，即作者自建的 architectury 工具链分支**（非公共版本），复刻此仓库需注意
- 编译依赖：`iceberg`（required, >=1.3.0）与 `prism`（required, >=1.0.11）——**同作者的两个库模组，本 mod 的架构完全建立其上**；可选 `equipmentcompare`；开发期 `curse.maven:emi`、`curse.maven:relics`（`common/build.gradle`）
- 多平台产物：common 通过 `shadowBundle project(':common', 'transformProductionNeoForge')` 打包进平台 jar，`remapJar.atAccessWideners` 注入 AW

## 2. 源码规模与包结构

- **25 个 .java，共 2929 行**（实测）；模块：`common`（全部逻辑）+ 三个平台壳
- `common` 包结构：根 `LegendaryTooltips.java`(189 行，含全部事件回调)、`config/`(2 文件 930 行)、`mixin/`(7 文件 + `mixin/emi/` 子包)、`tooltip/`(3 文件 530 行)、`client/LegendaryTooltipsClient.java`(28 行)
- 最大文件：`config/LegendaryTooltipsConfig.java` 724、`mixin/GuiGraphicsMixin.java` 528、`tooltip/TooltipDecor.java` 269、`config/FrameResourceParser.java` 206

## 3. 入口与注册

无 DeferredRegister（本 mod 无方块/物品注册）。`common/.../LegendaryTooltips.java:56` 只做 `LegendaryTooltipsConfig.register(LegendaryTooltipsConfig.class, MODID)`（Iceberg 的配置注册）。客户端 `client/LegendaryTooltipsClient.java:14-28`：

```java
ItemModelComponent.registerFactory();
RenderTooltipEvents.GATHER.register(LegendaryTooltips::onGatherComponentsEvent);
RenderTooltipEvents.COLOREXT.register(LegendaryTooltips::onTooltipColorEvent);
RenderTooltipEvents.POSTEXT.register(LegendaryTooltips::onPostTooltipEvent);
RenderTickEvents.START.register(LegendaryTooltips::onRenderTick);
Services.getReloadListenerRegistrar().registerListener(FrameResourceParser.INSTANCE, ResourceLocation.fromNamespaceAndPath(MODID, "frame_definitions"));
```

三平台入口极薄：`LegendaryTooltipsFabric implements ModInitializer`、`LegendaryTooltipsNeoForgeClient @Mod(dist=Dist.CLIENT)` 构造器直接调 init、Forge 用 `@EventBusSubscriber(bus=MOD) + FMLConstructModEvent`。跨平台能力（按键、配置、资源重载监听、平台判断）一律走 **Iceberg 的服务定位器 `Services.getXxx()`**，不写自己的抽象层。

## 4. 核心系统

1. **数据驱动的"边框定义"系统**：`config/FrameResourceParser.java` 实现 `ResourceManagerReloadListener`，用 `resourceManager.getResourceStack(legendarytooltips:frame_definitions.json)` **按资源包顺序层叠读取多份 JSON**，解析 `image/index/sizes(frameWidth,partSize)/offsets(partOffset,cornerOffset)/startColor/endColor/bgColor/priority/selectors`（缺省值全有默认），产出 `FrameDefinition` record（字段用 `Supplier<Integer>` 惰性取色）；`onResourceManagerReload` 开头先 `reset()` + `clearDataFrames()` 保证删文件即失效（`FrameResourceParser.java:35-205`，JSON 格式注释写在方法里，是很好的文档范例）
2. **tooltip 渲染注入**：`mixin/GuiGraphicsMixin.java` 全部针对 `GuiGraphics.renderTooltipInternal`——`@ModifyVariable(ordinal=0)` 把 components 复制成可变 List 并记录 `numTitleLines/titleStart/hasItemModel`（`@Unique` 字段存状态）；`@ModifyArg` 两次改 `ClientTooltipPositioner.positionTooltip` 的 width/height 参数（index=4/5）；另用 `@Group(name="tooltipWidth", max=1)` 同时 hook 主方法与 **lambda 目标 `lambda$renderTooltipInternal$3`**，因为 1.21 里背景绘制在 lambda 内（`:185-200`）——这是 1.21 注入 tooltip 的关键坑
3. **边框/阴影绘制**：`tooltip/TooltipDecor.java` 用 9-slice 思路画 `legendarytooltips:textures/gui/tooltip_borders.png`（`NUM_FRAMES = 16`，`DEFAULT_BORDERS` 为默认图），`drawBorder/drawShadow/drawSeparator` 接收 `FrameDefinition`，另有 `setCurrentTooltipBorderStart/End` 等把颜色暂存供后续阶段使用（GATHER→COLOREXT→POSTEXT 三阶段协作）
4. **边框选择与优先级**：`LegendaryTooltipsConfig.getFrameDefinition(item, provider)`（`:600-707`）依次尝试：API 注册的 `customFrameDefinitions`（按 `priority` 排序）、配置的 `level0_entries..level15_entries`（`itemSelectors.get(frameIndex)`）、`blacklist`；匹配用 Iceberg 的 `Selectors.itemMatches(item, entry, provider)`（配置校验用 `Selectors.validateSelector`，注释里附 `Selectors.selectorDocumentation()` 自动生成说明）；结果缓存在 `frameDefinitionCache`，`itemSelectors`/`formattedTitleCache` 同理
5. **超长 tooltip 滚动**：`tooltip/TooltipScroll.java` 每索引独立 `ScrollData`（scrollOffset/targetOffset/scrollTop/Bottom），`onRenderTick` 用 `Easing.Ease(..., EasingType.Quad, EasingDirection.Out)` 0.15s 插值；`MouseHandlerMixin`（`@Mixin(priority=999)`）注入 `onScroll` cancellable 转成滚动量，`ScreenMixin`/`KeyboardHandlerMixin` 处理按键释放与关闭时复位
6. **3D 物品模型**：`tooltip/ItemModelComponent.java` + `ItemModelComponent.registerFactory()` 把 `TooltipComponent` 注册进原版工厂，`LegendaryTooltips.onGatherComponentsEvent` 里插到标题前并加空行；标题组件的居中/内边距靠 Iceberg 的 `IExtendedText.setAlignment/setPadding`（`:102-138`）

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端 mod）
- 数据驱动：`frame_definitions.json`（资源包可覆盖、可叠加），`legendarytooltips/frame_definitions` 作为 reload 监听 ID
- 配置：Iceberg 的 `IIcebergConfigSpecBuilder` 构建（`build.comment(...).add("on_top", true)`、`addListAllowEmpty("level0_entries", ..., Selectors::validateSelector)`），支持 hex 颜色与 Prism 颜色定义；`compacting`/`compactTooltips` 会删掉 `item.modifiers.` 开头的行（`LegendaryTooltips.java:61-105`）
- datagen：无
- accesswidener：`common/src/main/resources/legendarytooltips.accesswidener` 打开 `AbstractContainerScreen.hoveredSlot`、`Screen.font`、`ItemRenderer.blockEntityRenderer`、`Minecraft.itemColors`、`ClientTextTooltip.text`；for 版本为 1.21.1（`accessible v1 named`）

## 6. Mixin

- `common/src/main/resources/legendarytooltips.mixins.json`：`plugin = MixinConfig`，client 列表 7 个（`emi.EmiRenderHelperMixin`、`BakedGlyphMixin`、`GuiGraphicsMixin`、`ItemStackMixin`、`KeyboardHandlerMixin`、`MouseHandlerMixin`、`ScreenMixin`）
- 另有平台级：`legendarytooltips.neoforge.mixins.json`（`AttributeUtilMixin`）、`legendarytooltips.fabric.mixins.json`（JEI/REI 各一个）
- 代表性 hook：`GuiGraphics.renderTooltipInternal`（@ModifyVariable/@ModifyArg/@Inject/@Group）、`MouseHandler.onScroll`、`KeyboardHandler.method_1454` @ModifyArg(index=0 改 keyReleased 的键码)、`Screen.onClose/keyPressed` @HEAD、`BakedGlyph.render` @Inject HEAD + 4×@ModifyArg（描边/阴影） 、`ItemStack.addModifierTooltip` @Redirect（修 MC-271840 攻击力显示，`ItemStackMixin.java:31-64`）
- 兼容 mixin 的**自动条件加载**值得抄：`mixin/MixinConfig.java:22-36` 把 mixin 类名子包当作 mod id（`mixin/emi/...` → `emi`），`Services.getPlatformHelper().isModLoaded(modId)` 决定是否应用

## 7. 值得学的 5 条具体做法

1. **库化拆分**：把平台抽象、事件总线、选择器、渲染工具全部下沉到 Iceberg 库（`Services`、`RenderTooltipEvents`、`Selectors`、`IExtendedText`、`CustomItemRenderer`），业务 mod 只剩 2929 行——`common/build.gradle`。适用：想同时维护多平台 + 多 mod 的作者。
2. **MixinConfig 用"子包名 = mod id"自动条件加载兼容 mixin**（`mixin/MixinConfig.java:22-36`），新增兼容只需建子包，不用改配置。
3. **同一个方法的多条注入路径用 `@Group(name, max=1)` 声明互斥**，兼容原版重构（主方法 vs lambda）时只生效一条（`GuiGraphicsMixin.java:185`）。
4. **数据定义放资源包 + `getResourceStack` 层叠**，并用 `ResourceManagerReloadListener` 做热重载、reload 时先 clear 再重建（`FrameResourceParser.java:68-75`）——数据包作者可直接改边框而无需改配置。
5. **对外 API 走 `addFrameDefinition(...)` + `FrameSource.API` + priority 排序**（`LegendaryTooltipsConfig.java:558-598`），并允许配置里的 `-1` 占位表达"数据/API 边框的相对优先级"，让第三方注册不与用户配置冲突。

## 8. 公开 API / 扩展方式（本 mod 非库，但有 API 面）

- 外部 mod 可调 `LegendaryTooltipsConfig.addFrameDefinition(resource, index, startBorder, endBorder, background, priority, selectors[, frameWidth, partSize, partOffset, cornerOffset])` 注册自定义边框（`FrameSource.API`）
- 依赖方向：LegendaryTooltips → Iceberg（配置/事件/服务/选择器/工具）、Prism（颜色定义）；Iceberg/Prism 的接口即其扩展面
