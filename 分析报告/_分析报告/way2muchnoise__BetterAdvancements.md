# way2muchnoise/BetterAdvancements 源码分析报告

## 1. 基本信息

- Mod 名：Better Advancements；mod_id `betteradvancements`；作者 way2muchnoise（`gradle.properties:9`）；许可证 **"Don't Be a Jerk" non-commercial care-free license**（`NeoForge/src/main/resources/META-INF/neoforge.mods.toml:5`，非 SPDX）。
- 目标版本：`minecraftVersion=26.2`、`minecraftVersionRange=[26.2, 26.3)`、`modJavaVersion=25`（`gradle.properties:20-23`）；版本号 `specificationVersion=0.6.0` + CI build number（`build.gradle.kts:64-70`）。
- 加载器：**fabric + forge + neoforge**（`platforms=fabric,forge,neoforge`），使用 **Architectury**：`architectury-plugin 3.5-SNAPSHOT` + `dev.architectury.loom-no-remap 1.17-SNAPSHOT` + `com.gradleup.shadow 9.4.1`（`build.gradle.kts:7-11`）；9 个子项目 `Common/CommonApi/Fabric/FabricApi/Forge/ForgeApi/NeoForge/NeoForgeApi`。
- 依赖：fabric-loader 0.19.3 + fabric-api 0.155.2+26.2 + cloth-config 26.2.155 + modmenu 20.0.1（fabric）；forge 65.0.9；neoforge 26.2.0.28-beta；Parchment `mappingsParchmentMinecraftVersion=1.21.11` / `2025.12.20`。发布用 `curseforgegradle` + `minotaur`，产物输出到根目录 `output/`。

## 2. 源码规模与包结构

- 实测：`find . -name '*.java' | wc -l` = **55 个文件，3744 行**（不含 `.git`）。
- 包结构（核心在 `Common`）：`betteradvancements.common.gui` 5 个类、`common.util` 7（AdvancementComparer / ColorHelper / CriteriaDetail / CriterionGrid / CriterionTranslator / RenderUtil）、`common.advancements` 2（BetterDisplayInfo / BetterDisplayInfoRegistry）、`common.platform` 4（IPlatformHelper / IEventHelper / IAdvancementVisitor / Services）、`common.reference` 3（Constants / Resources / Textures）；`CommonApi` 5 个 API 接口；每个加载器 8-9 个类（入口、`*PlatformHelper`/`*EventHelper`/`*AdvancementVisitor`、config、handler）＋一个 Api 子模块。
- 最大文件：`Common/.../gui/BetterAdvancementsScreen.java`(525)、`BetterAdvancementWidget.java`(434)、`advancements/BetterDisplayInfo.java`(235)、`BetterAdvancementTab.java`(213)、`util/CriterionGrid.java`(166)、`Fabric/.../config/ConfigValues.java`(158)、`NeoForge/.../NeoForgeAdvancementVisitor.java`(102)。

## 3. 入口与注册

NeoForge 入口（`NeoForge/src/main/java/betteradvancements/neoforge/BetterAdvancements.java`）：

```java
@Mod(value = Constants.ID, dist = Dist.CLIENT)
public class BetterAdvancements {
    public BetterAdvancements(ModContainer container) {
        container.registerConfig(ModConfig.Type.CLIENT, Config.CLIENT);
        container.getEventBus().register(Config.instance);
        NeoForge.EVENT_BUS.register(GuiOpenHandler.instance);
    }
}
```

- 纯客户端 mod，**无内容注册**（无 DeferredRegister），`neoforge.mods.toml` 里 `displayTest="NONE"` 且依赖 `side="CLIENT"`。
- 替换原版界面的方式分两条：NeoForge/Forge 走 `ScreenEvent.Opening` → `event.setCanceled(true)` + `mc.setScreenAndShow(new BetterAdvancementsScreen(...))`（`NeoForge/.../handler/GuiOpenHandler.java:27-32`）；Fabric 无该事件，改用 mixin（见第 6 节）。
- **平台抽象 = ServiceLoader**：`Services.PLATFORM = load(IPlatformHelper.class)`（`Common/.../platform/Services.java:8`），接口只暴露 `getPlatformName()/getEventHelper()/getAdvancementVisitor()`，各加载器一个 `*PlatformHelper` 实现。注意：仓库中**未找到** `META-INF/services/betteradvancements.common.platform.IPlatformHelper` 注册文件（未确认是构建生成还是仓库遗漏）。

## 4. 核心系统

1. **`better_display` 数据驱动显示扩展**（`common/advancements/BetterDisplayInfo.java` + `BetterDisplayInfoRegistry.java`）：在 advancement 的 JSON 里读一个 `"better_display"` 对象（`BetterDisplayInfoRegistry.java:45-55`），字段含完成/未完成图标与标题颜色、`drawDirectLines`、连线颜色、`posX/posY`、`hideLines`、`allowDragging`；缺省时回落到静态默认值 `defaultCompletedIconColor` 等；同时支持服务端 mod 直接实现 `IBetterDisplayInfo`（`parseIBetterDisplayInfo`(:113)）。这是"不改原版类也能扩展显示"的典型做法。
2. **增强 GUI**（`gui/BetterAdvancementsScreen.java`）：`MIN_ZOOM=0.4 / MAX_ZOOM=1.6 / ZOOM_STEP=0.1`，静态 `zoom`、`uiScaling`、`tabPage/maxPages` 与 `BetterAdvancementTabType.getMaxTabs(width,height)` 做多标签分页（:79-87），`advConnectedToMouse` 实现"拖拽分支节点"。
3. **条件（criteria）网格渲染**（`util/CriterionGrid.java` + `CriteriaDetail.java` + `CriterionTranslator.java`）：把 `AdvancementProgress` 的 criteria 排成"行列/分页"网格，`CriteriaDetail` 枚举 `OFF/DEFAULT/SPOILER/ALL` 决定显示已获得/未获得（`showObtained()/showUnobtained()`），带 `requiresShift`、`colorWholeCriteriaText`、`criteriaRotationSpeed` 等开关。
4. **跨加载器事件桥**（`CommonApi/.../api/event/IAdvancementMovedEvent.java`、`IAdvancementDrawConnectionsEvent.java`、`IBetterAdvancementEntryGui.java`）：common 里只调 `Services.PLATFORM.getEventHelper().postAdvancementMovementEvent(gui)`（`BetterAdvancementWidget.java:133`、`BetterAdvancementsScreen.java:187`），各加载器 Api 模块把接口实现成原生事件（`NeoForgeApi/.../AdvancementMovedEvent extends net.neoforged.bus.api.Event`）。
5. **平台文件访问抽象**（`common/platform/IAdvancementVisitor.java`）：`findAdvancements(location, serverLevel, preprocessor, processor, defaultUnfoundRoot, visitAllFiles)`，common 只传回调；平台侧 `NeoForgeAdvancementVisitor` 负责定位 mod 源（jar 用 `FileSystems.newFileSystem(source.toURI(), null)`，`"minecraft"` 则借 `/assets/.mcassetsroot` 反推）或读世界存档的 `advancements/<namespace>`，再 `Files.walk`。
6. **物品栏入口按钮**：`NeoForge/.../handler/GuiOpenHandler.onGuiOpened` 监听 `ScreenEvent.Init.Post`，在 `InventoryScreen` 上加 `BetterAdvancementsScreenButton`（受 `addToInventory` 开关控制）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无自建包**。仅使用原版 `ServerboundSeenAdvancementsPacket.closedScreen()` 上报关屏（`BetterAdvancementsScreen.java:98`）。
- **数据驱动**：核心就是 advancement JSON 的 `better_display` 附加字段 + 从 mod jar / 世界目录遍历 `advancements/` 目录；无自建数据包注册表。
- **配置**：各加载器各写一份——NeoForge `ModConfigSpec`（`NeoForge/.../config/ConfigValues.java`），Fabric 用 cloth-config（`Fabric/.../config/ConfigFileHandler.java`(129) + `BetterAdvancementsModMenu`）。桥接方式是**把配置值写进 common 的 public static 字段**（`BetterDisplayInfo.default*`、`CriterionGrid.detailLevel/requiresShift/colorWholeCriteriaText/criteriaRotationSpeed`、`BetterAdvancementsScreen.uiScaling/showDebugCoordinates/orderTabsAlphabetically/keepAdvancementsTitle`、`BetterAdvancementsScreenButton.addToInventory`），common 完全不认识配置 API。
- **datagen：无**。
- **访问宽度器双份**：`Common/src/main/resources/betteradvancements.accesswidener` 与 `NeoForge/src/main/resources/META-INF/accesstransformer.cfg` 维护同一批成员：`AdvancementTabType` 类、`AbstractContainerScreen.leftPos/topPos/imageWidth`（用于在物品栏旁摆按钮）。

## 6. Mixin

- 只有 Fabric 需要：`Fabric/src/main/resources/betteradvancements.mixins.json`（`required:true`、`package betteradvancements.mixin`、`compatibilityLevel JAVA_16`、client 段含 `MinecraftMixin`），由 loom 自动挂载（无 `fabric.mod.json` 于仓库内，未确认生成方式）。
- `Fabric/src/main/java/betteradvancements/mixin/MinecraftMixin.java`：`@Mixin(Gui.class)` + `@ModifyVariable(method = "setScreen", at = @At("HEAD"), ordinal = 0, argsOnly = true)`，把入参 `AdvancementsScreen` 替换成 `new BetterAdvancementsScreen(Minecraft.getInstance().player.connection.getAdvancements())`。Forge/NeoForge 用事件替代同一逻辑，是"最小 mixin 面"的示范。

## 7. 值得学的 5 条具体做法

1. **用原版 JSON 的附加字段扩展显示，而非自建注册表**：读 advancement 里的 `better_display`（`Common/.../BetterDisplayInfoRegistry.java:54-55`）；适用：想让数据包作者/其他 mod 零成本定制你的 UI 行为。注意其解析走平台文件遍历而非 ResourceManager，属"绕过资源系统直读源文件"的取舍。
2. **loader 中立事件接口 + 每加载器实现**：`CommonApi` 定义 `I*Event`，`NeoForgeApi/ForgeApi/FabricApi` 各包装成原生事件（`NeoForge/.../NeoForgeEventHelper.java`）；适用：GUI 类 mod 要给第三方发可监听事件。
3. **ServiceLoader 三件套做平台发现**：`IPlatformHelper / IEventHelper / IAdvancementVisitor`（`Common/.../platform/`）；适用：Architectury 之外想要极薄平台层（但需记得补 `META-INF/services` 文件，本仓库快照中缺失）。
4. **配置值注入 common 静态字段**：`ConfigValues.build()` 把 ModConfigSpec 的值写进 `BetterDisplayInfo.default*` 等静态字段（`NeoForge/.../config/ConfigValues.java:43-51`）；适用：common 代码要保持零加载器依赖又需读配置。
5. **API 独立出 jar**：`Fabric/build.gradle.kts` 注册 `apiJar`（`classifier "api"`）打包 `CommonApi + FabricApi`，与 shadowJar 一起 artifacts 发布；适用：想让其他 mod 编译期只依赖你的接口包。

## 8. 公开 API

- 公共 API 包：`betteradvancements.common.api`（模块 `CommonApi`）——`IBetterDisplayInfo`（默认方法全返回 -1/null，实现者只覆写需要的项）、`IBetterAdvancementEntryGui`（`getAdvancement()/getX()/getY()`）、`api.event.IAdvancementMovedEvent`、`IAdvancementDrawConnectionsEvent`。
- 加载器侧入口：`betteradvancements.neoforge.api.event.*`、`betteradvancements.forge.api.event.*`、`betteradvancements.api.fabric.event.*`（真实可 `@SubscribeEvent`/`register` 的事件类，均为 `public class ... extends Event implements I*Event`）。
- 外部接入方式：① 让 `Advancement`/`DisplayInfo` 实现 `IBetterDisplayInfo`；② 或在 advancement JSON 加 `better_display` 字段；③ 或监听上述事件修改拖动位置/连线绘制。发布时提供独立 `-api` 分类 jar 供编译期依赖。
