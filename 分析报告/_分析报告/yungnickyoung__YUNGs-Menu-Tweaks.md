# yungnickyoung/YUNGs-Menu-Tweaks 源码分析报告

## 1. 基本信息

- Mod 名：YUNG's Menu Tweaks；mod_id `yungsmenutweaks`；作者 YUNGNICKYOUNG；group `com.yungnickyoung.minecraft.yungsmenutweaks`
- 目标版本与加载器（`gradle.properties`）：`mc_version=26.1.2`（`[26.1,)`）、`neoforge_version=26.1.2.75`、Fabric `fabric_version=0.150.0` / loader 0.18.6、`version=3.1.0`、`java_version=25`；**多加载器（Common / Fabric / NeoForge）**
- Gradle：与 Travelers-Titles 同一套 YUNG 多加载器模板（根 `build.gradle` 声明 fabric-loom 1.15.5 与 moddev 2.0.141 apply false；`buildSrc/src/main/groovy/multiloader-common.gradle` 统一 `processResources` 展开）
- 许可证：LGPLv3
- 编译依赖：YUNG's API（YungsApi）6.1.0（`Common/build.gradle:20-22` compileOnly，加载器侧 implementation），运行前置写在 `NeoForge/src/main/resources/META-INF/neoforge.mods.toml` 的 `[[dependencies]] modId="yungsapi"`；Fabric 侧可选 Cloth Config（clothconfig 26.1.154）+ ModMenu 18.0.0-beta.1；纯客户端 mod

## 2. 源码规模与包结构

- 23 个 `.java`，共 563 行（实测）——体量极小，适合当"多加载器 + mixin"模板读
- Common：`yungsmenutweaks`(1)、`mixin`(4)、`module`(1)、`services`(3)
- NeoForge：`yungsmenutweaks`(1)、`config`(1)、`mixin`(1)、`module`(1)、`services`(2)、资源 `META-INF/{neoforge.mods.toml,accesstransformer.cfg}`
- Fabric：`yungsmenutweaks`(1)、`config`(3，含 `config/gui/YMTModMenu`)、`mixin`(1)、`module`(1)、`services`(2)
- 最大文件：`NeoForge/.../config/YMTConfigNeoForge.java` 46、`NeoForge/.../module/ConfigModuleNeoForge.java` 43、`NeoForge/.../mixin/AbstractSelectionListMixinNeoForge.java` 42、`Fabric/.../mixin/AbstractSelectionListMixinFabric.java` 42、`Common/.../mixin/AbstractSliderButtonMixin.java` 38

## 3. 入口与注册

无任何注册内容（不改物品/方块/注册表）。NeoForge 入口 `NeoForge/src/main/java/com/yungnickyoung/minecraft/yungsmenutweaks/YungsMenuTweaksNeoForge.java:9-18`：

```java
@Mod(value = YungsMenuTweaksCommon.MOD_ID, dist = Dist.CLIENT)
public class YungsMenuTweaksNeoForge {
    public static IEventBus loadingContextEventBus;
    public YungsMenuTweaksNeoForge(IEventBus eventBus, ModContainer container) {
        YungsMenuTweaksNeoForge.loadingContextEventBus = eventBus;
        YungsMenuTweaksCommon.init();
        ConfigModuleNeoForge.init(container);
    }
}
```

Fabric 入口仅 `ClientModInitializer#onInitializeClient` → `YungsMenuTweaksCommon.init()`。Common 侧 `YungsMenuTweaksCommon.java:15-18` 只做两件事：`YungAutoRegister.scanPackageForAnnotations("...module")` 与 `Services.MODULES.loadModules()`（无 DeferredRegister/Registrate，因为无内容注册）。

## 4. 核心系统

**a. 4 个 Common mixin 做纯行为微调**（`Common/.../mixin/`）：
- `AbstractSelectionListMixin`：`@Mixin(AbstractWidget.class)`，注入 `isValidClickButton` 的 HEAD 并 `cancellable`，让 `CycleButton` 接受右键（`:18-23`）。
- `CycleButtonMixin`：`@Mixin(CycleButton.class)`，`onPress` HEAD cancel，用 `GLFW.glfwGetMouseButton(..., MOUSE_BUTTON_RIGHT)` 探测右键 + `Minecraft.hasShiftDown()` 决定 `cycleValue(-1)` 还是 `cycleValue(1)`（`:84-93`）。
- `AbstractSliderButtonMixin`：`@Mixin(AbstractSliderButton.class) extends AbstractWidget`，**直接覆盖 `mouseScrolled`**（非 @Inject），用 `@Shadow` 的 `setValue(double)`、`value` 按 ±0.01 步进滑条（`:48-61`）。
- `ScreenMixin`：`@Mixin(Screen.class)` 注入 `extractBackground` 的 HEAD cancel，改调 `Services.PLATFORM.renderBackground((Screen)(Object)this, graphics, CONFIG.backgroundTexture, ...)` 换自定义背景（`:108-114`）。

**b. 加载器差异用"同名 mixin 各放一份"解决**：`AbstractSelectionListMixinNeoForge` 与 `...Fabric`（`:15-42` / `:57-84`）代码完全相同，注入 `AbstractScrollArea.mouseScrolled` HEAD cancellable，遍历 `OptionsList` → entry.children()，对鼠标悬停的 `AbstractSliderButton` 转发滚轮事件并 `cir.setReturnValue(true)`；两份分别登记在 `yungsmenutweaks_neoforge.mixins.json` / `yungsmenutweaks_fabric.mixins.json`。`OptionsList$Entry` 通过 AT 公开：`NeoForge/src/main/resources/META-INF/accesstransformer.cfg` → `public net.minecraft.client.gui.components.OptionsList$Entry`。

**c. 平台服务抽象**（`Common/.../services/Services.java:8-17`）：`ServiceLoader.load(clazz, Services.class.getClassLoader()).findFirst().orElseThrow()`，暴露 `IPlatformHelper`（`getPlatformName/isModLoaded/isDevelopmentEnvironment` + `renderBackground(...)`）与 `IModulesLoader`。`NeoForgePlatformHelper.java:29-32` 在自绘背景后**补发** `new ScreenEvent.Render.Background(...)`（因为 mixin cancel 导致原事件不再发出，注释明确写明）；`FabricPlatformHelper.java:26-28` 用 `guiGraphics.blit(RenderPipelines.GUI_TEXTURED, tex, 0,0,0,0, screen.width, screen.height, 32, 32, 0xFF404040)` 平铺纹理。

**d. 配置三层结构**：Common `ConfigModule` 是纯 POJO（`enableRightClickCycleButton`、`enableMouseScrollOnSliders`、`enableBackgroundTexture`、`Identifier backgroundTexture` 默认 `minecraft:textures/block/dirt.png`）；NeoForge `YMTConfigNeoForge` 用 `ModConfigSpec` 静态块定义 4 项，注册为 `ModConfig.Type.COMMON` + 固定文件名 `"yungsmenutweaks-neoforge-26_1.toml"`（`ConfigModuleNeoForge.java:78-82`），`LevelEvent.Load` 与 `ModConfigEvent` 都触发 `bakeConfig()`；Fabric 用 AutoConfig（`@Config(name="yungsmenutweaks-fabric-26_1")` + `Toml4jConfigSerializer`）并注册 save/load listener。平台 `bakeConfig` 里都用 `Identifier.tryParse` 校验贴图路径，失败则 `LOGGER.error` 并回落默认贴图（`ConfigModuleNeoForge.java:98-105`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无（纯客户端）。
- 数据驱动：无（无 datapack/标签/JSON 逻辑）。
- 配置：见 4.d；NeoForge 与 Fabric 两套 config 类名/字段一一对应（`ConfigYungsMenuTweaksFabric`），但 Common 只认识 `ConfigModule` 的 POJO。
- datagen：无。

## 6. Mixin

- 配置：`Common/src/main/resources/yungsmenutweaks.mixins.json`（client 段：`AbstractSelectionListMixin`、`AbstractSliderButtonMixin`、`CycleButtonMixin`、`ScreenMixin`）；`NeoForge/src/main/resources/yungsmenutweaks_neoforge.mixins.json`（client：`AbstractSelectionListMixinNeoForge`）；`Fabric/src/main/resources/yungsmenutweaks_fabric.mixins.json`（client：`AbstractSelectionListMixinFabric`）。`neoforge.mods.toml` 末尾用两个 `[[mixins]] config=...` 同时登记 common 与 neoforge 两份配置。
- 注入点汇总：`AbstractWidget#isValidClickButton`(HEAD,cancellable)、`CycleButton#onPress`(HEAD,cancellable)、`AbstractSliderButton#mouseScrolled`(整体覆盖)、`Screen#extractBackground`(HEAD,cancellable)、`AbstractScrollArea#mouseScrolled`(HEAD,cancellable)；均 `defaultRequire:1`。

## 7. 值得学的 5 条具体做法

1. **覆盖而非 @Inject 原版方法**：`AbstractSliderButtonMixin` 直接重写 `mouseScrolled` 并用 `@Shadow setValue/value` 操作内部状态 —— `Common/.../mixin/AbstractSliderButtonMixin.java:48-61`；比注入 + 反射取值简洁。
2. **cancel 后手动补发平台事件**：NeoForge 侧 `NeoForge.EVENT_BUS.post(new ScreenEvent.Render.Background(...))` 保证其它 mod 的监听不被自己吞掉 —— `NeoForge/.../services/NeoForgePlatformHelper.java:31`；写会 cancel 原版渲染/事件的 mixin 时必须考虑。
3. **加载器专属 mixin 用"同代码两份 + 各自 mixins.json"**：避免 common 里用条件判断，模板见 `AbstractSelectionListMixinNeoForge/Fabric` 与三个 mixins.json；配合 `[[mixins]]` 多条登记。
4. **AT 公开内部类而非重写整段逻辑**：只需 `public net.minecraft.client.gui.components.OptionsList$Entry` 就能遍历选项列表条目 —— `NeoForge/src/main/resources/META-INF/accesstransformer.cfg`。
5. **config 烘焙函数做输入校验 + 回落默认值**：`Identifier.tryParse` 失败写日志并回默认贴图，NeoForge/Fabric 两处实现一致 —— `NeoForge/.../module/ConfigModuleNeoForge.java:98-105`、`Fabric/.../module/ConfigModuleFabric.java:28-35`；凡用户可填资源路径的配置都应这么写。

## 8. 公开 API

不适用（纯客户端 QoL mod，无对外 API）。可复用其骨架：`services/{Services,IPlatformHelper,IModulesLoader}` 的 ServiceLoader 平台抽象是现成的多加载器脚手架。
