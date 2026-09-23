# AHilyard/Iceberg 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Iceberg / `iceberg`（`gradle.properties`：`modVersion=1.2.10`，`group=com.anthonyhilyard.iceberg`）
- 作者 / 许可证：Grend（anthonyhilyard）；CC BY-NC-ND 4.0（`neoforge/src/main/resources/META-INF/neoforge.mods.toml:3`、`forge/src/main/resources/META-INF/mods.toml:3`）
- 定位（mods.toml description）："A library containing events, helpers, and utilities to make modding easier."
- 目标版本：Minecraft **1.21.3**，三加载器：Fabric `0.16.9` / Fabric API `0.107.0+1.21.3`、Forge `1.21.3-53.0.7`、NeoForge `21.3.11-beta`（`gradle.properties` 的 `enabledPlatforms=fabric,forge,neoforge`）
- Gradle / 架构：Architectury 多加载器（`settings.gradle` include `common/fabric/forge/neoforge`），`architectury-loom-1.7.9999` + `architectury-plugin-3.4.9999` 由本地 `flatDir ../architectury-loom/build/libs` 提供（作者私有 fork）；Shadow 插件 `io.github.goooler.shadow:8.1.7`；Java 21（`build.gradle` 中 `VERSION_21`）
- 依赖：common 仅编译期依赖 fabric-loader；Fabric 端额外 `night-config core/toml 3.6.4` 并以 `shadowBundle` 打进 jar、硬依赖本地 `libs/sodium-fabric-0.6.0-beta.2+mc1.21.1.jar`；NeoForge 端 `byte-buddy 1.14.18` + sodium jar；更新检查走 `https://mc-update-check.anthonyhilyard.com/520110`（CurseForge project 520110）
- 反向依赖（Legendary Tooltips、Prism）的具体接入代码不在本仓库，**未确认**；本仓库中被依赖的形态见第 8 节

## 2. 源码规模与包结构

实测：**87 个 `.java`，9015 行**（common 49 / fabric 16 / neoforge 12 / forge 10）。注意这是 sparse-checkout 仓库（`.git/info/sparse-checkout` 只保留 java/gradle/toml/mixins.json 等），`fabric.mod.json`、贴图、lang 未下载。

主要包（`com.anthonyhilyard.iceberg.*`）：`client`、`config`、`events`(+`events/client`、`events/common`、`events/server`)、`mixin`、`registry`、`renderer`、`services`、`util`；平台侧镜像包 `fabric|forge|neoforge` 下各含 `client/config/mixin/server/services`。

最大文件：`fabric/config/FabricIcebergConfigSpec.java` 850、`forge/config/ForgeIcebergConfigSpec.java` 769、`renderer/CustomItemRenderer.java` 739、`neoforge/config/NeoForgeIcebergConfigSpec.java` 716、`util/Tooltips.java` 546、`util/Selectors.java` 435、`util/EntityCollector.java` 369、`fabric/config/ConfigTracker.java` 271、`common/mixin/GuiGraphicsMixin.java` 163。

## 3. 入口与注册

没有统一主类：`common/.../Iceberg.java` 只有 `MODID="iceberg"` 与 `LOGGER`。客户端公共初始化在 `common/.../client/IcebergClient.java:17` `init()`（注册 `TitleBreakComponent.registerFactory()` 与 `RenderTooltipEvents.GATHER`）。

NeoForge 入口 `neoforge/.../IcebergNeoForge.java:26-45`：

```java
@Mod(Iceberg.MODID)
public final class IcebergNeoForge {
	public IcebergNeoForge(IEventBus modBus) {
		if (FMLEnvironment.dist == Dist.CLIENT) {
			IcebergClient.init();
			NeoForge.EVENT_BUS.register(IcebergNeoForgeClient.NeoForgeEvents.class);
			modBus.register(NeoForgeKeyMappingRegistrar.class);
```

注册框架：**无 DeferredRegister / Registrate**。`registry/AutoRegistry.java`（194 行）与 `registry/RendererRegistrar.java` 整体被注释掉，是 1.12/1.16 时代的反射注册遗产（`registryMap`、`registerEntity`），现仅 `services/*Registrar` 承担"注册器"角色（键位、reload listener）。**无网络包注册代码**。

## 4. 核心系统

**(1) 自研事件总线**（`events/Event.java`、`EventFactory.java`、`ToggleableEvent.java`、`TypeTrackedEvent.java`）
- `Event<T>` 维护 `listeners[]`，每次 `register` 后调用 `invokerFactory.apply(listeners)` 生成合并 invoker（`Event.java:47-50`），调用点无遍历开销。
- `EventFactory.EVENTS` 用 `MapMaker().weakKeys()` 弱键集合持有全部事件，提供 `invalidate()` 重建所有 invoker（`EventFactory.java:11-18`），用于配置/重载后刷新。
- `ToggleableEvent.disable()` 切换为 `dummyInvoker`（空实现），实现"整套事件可关闭"；`TypeTrackedEvent` 强制 `register(Type, listener)` 并维护 `Map<Class,T>`，用于按数据类型查工厂（`events/client/RegisterTooltipComponentFactoryEvent.java`）。

**(2) Tooltip 渲染管线**（`util/Tooltips.java:181-291`、`mixin/TooltipRenderUtilMixin.java`、`mixin/GuiGraphicsMixin.java`）
- 四阶段事件：`GATHER`（收集组件，可改 `maxWidth`）→ `PREEXT`（可改 x/y/font）→ `COLOREXT`（背景/边框渐变颜色）→ `POSTEXT`；每阶段用 record 结果对象传递（`RenderTooltipEvents.java:95-97`），`InteractionResult != PASS` 即短路。
- 渐变背景绕过原版 sprite：`TooltipRenderUtilMixin.java:19,35` 用两个 `@Redirect`（`ordinal=0/1`）拦截 `GuiGraphics.blitSprite`，读静态 `Tooltips.currentColors/gradientBackground`（`Tooltips.java:53-55`、`renderGradientBackground:160`）。
- `Tooltips.TitleBreakComponent`（`Tooltips.java:57`）实现 `TooltipComponent + ClientTooltipComponent`，让 tooltip 有"标题行"概念，`centerTitle`/`calculateTitleLines` 据此居中标题。

**(3) 跨平台服务层**（`services/Services.java:13-52`）
- 用 `ServiceLoader.load(clazz).findFirst()` 加载平台实现，`ConcurrentHashMap` + 双检锁懒加载缓存；6 个接口：`IPlatformHelper`（`isModLoaded`/`modVersionMeets`）、`IBufferSourceFactory`、`IIcebergConfigSpecBuilder`、`IKeyMappingRegistrar`、`IReloadListenerRegistrar`、`IFontLookup`。

**(4) 配置系统**（`config/IcebergConfig.java`、`config/IIcebergConfigSpec.java` + 各平台 `*IcebergConfigSpec`）
- `IcebergConfig.register(subClass, modId)` 静态注册，内部用 `ConfigEvents.REGISTER/LOAD/RELOAD`（`IcebergConfig.java:144-146`）桥接平台原生配置；Fabric 端自研 `ConfigTracker`(271 行)+NightConfig TOML，NeoForge 端用 `ModContainer.registerConfig`（`IcebergNeoForge.java:56`）。

**(5) 物品渲染与帧缓冲**（`renderer/CustomItemRenderer.java:84`、`renderer/CheckedBufferSource.java`、`renderer/VertexCollector.java`）
- 继承 `ItemRenderer` 追加 `renderDetailModelIntoGUI`、`renderItemModelIntoGUIWithAlpha`；通过自定义 BufferSource 生成顶点缓冲以支持"旋转物品/多帧"渲染。Sodium 兼容用运行时探测：`CheckedBufferSource.java:34` `isModLoaded("sodium") && modVersionMeets("sodium","0.6.0")`。

**(6) 工具库**：`util/Selectors.java`（物品选择器 DSL：`validateSelector`、`itemMatches`、`selectorDocumentation()` 供 GUI 展示）、`util/EntityCollector.java`（伪装 `Level` 收集物品可生成的实体，`itemCreatesEntity`）、`util/DynamicResourcePack.java`（运行时合成资源包）、`util/Easing.java`、`util/ItemColor.java`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（仓库内无 packet/handler 类）。客户端事件由 mixin 本地触发。
- 数据驱动：**无 codec/registry 数据加载**；`DynamicResourcePack` 属资源侧动态生成。
- 配置：见 4-(4)；序列化为 TOML（NightConfig 3.6.4），`neoforge.mods.toml` 声明 `configuredProviders = ["com.anthonyhilyard.iceberg.compat.configured.IcebergConfigProvider"]`，但该类**未出现在本仓库 Java 清单中（未确认，可能被 sparse checkout 排除或已移除）**。
- datagen：仓库内无 datagen 目录/Provider，**无**。

## 6. Mixin

- 公共：`common/src/main/resources/iceberg.mixins.json`（`required=true`、`defaultRequire=1`）；`mixins` 段：`PlayerAdvancementsMixin`（→ `CriterionEvent`）、`ItemMixin`；`client` 段：`ScreenMixin`、`ClientPacketListenerMixin`（→ `NewItemPickupEvent`）、`TextColorMixin`、`MinecraftMixin`（→ `RenderTickEvents`）、`TooltipRenderUtilMixin`、`GuiGraphicsMixin`、`LevelRendererMixin`。
- 平台：`iceberg.fabric.mixins.json` / `iceberg.neoforge.mixins.json` / `iceberg.forge.mixins.json` 各自只含一个 `GuiGraphicsMixin`（同包名下平台专用实现），在 NeoForge 通过 `[[mixins]]`、Forge 通过 `loom { forge { mixinConfig ... } }` 加载。
- 代表 hook：`GuiGraphicsMixin.java:109-111` `@Inject(method="renderTooltipInternal", at=@At(INVOKE, target="TooltipRenderUtil.renderTooltipBackground", ordinal=0, shift=BEFORE))` 在画背景前算颜色；`ScreenMixin.java:24` `@Inject(method="getTooltipFromItem", at=HEAD)` 反射写入 `GuiGraphics` 的 `tooltipStack` 字段（Fabric 侧字段名不同，见 `common/mixin/GuiGraphicsMixin.java:52-59` 按平台名反射 `icebergTooltipStack`/`tooltipStack`）。
- `common/src/main/resources/iceberg.accesswidener`：放开 `ClientTextTooltip.text`、`AbstractContainerScreen.hoveredSlot`、`GuiGraphics.bufferSource`、`ItemRenderer.renderModelLists`、`UseOnContext` 构造器，并 `extendable` 了 `ItemRenderer.hasAnimatedTexture`。

## 7. 值得学的 5 条具体做法

1. **事件返回值用 record 承载**，监听器链式改写、`InteractionResult` 短路：`common/.../events/client/RenderTooltipEvents.java:23-36、95-97`。适合任何"多方修改同一参数"的渲染/工具事件。
2. **弱引用事件注册表 + 全局 `invalidate()`** 重建 invoker：`common/.../events/EventFactory.java:11-18`。适合需要热重载/配置变化后重建回调链的库。
3. **`ToggleableEvent` + `dummyInvoker`** 让整套事件可一键停用而不卸载监听器：`common/.../events/ToggleableEvent.java:29-39`。适合性能敏感或兼容开关场景。
4. **ServiceLoader + 懒加载缓存的平台抽象**，common 只依赖接口，平台 jar 提供实现：`common/.../services/Services.java:13-52` 配合 `fabric|forge|neoforge/**/services/*PlatformHelper`。比 Architectury 的 `@ExpectPlatform` 更少魔法、可直接单测。
5. **只把第三方库 shadow 进 jar（`shadowBundle`），common 用 `transformProductionXxx` 配置合并**：`fabric/build.gradle`、`neoforge/build.gradle`。适合库模组避免与用户端其它版本的 NightConfig 冲突。
6. （附）**用 accesswidener 一次性放开原版私有成员**（`iceberg.accesswidener`），替代大量 `@Accessor` mixin；NeoForge 侧还需 `remapJar { atAccessWideners.add('iceberg.accesswidener') }`。

## 8. 公开 API 与外部接入方式（库模组）

- 事件门面（`static final` 字段，直接 `EVENT.register(...)`）：
  - `com.anthonyhilyard.iceberg.events.client.RenderTooltipEvents.{GATHER,PREEXT,COLOREXT,POSTEXT}`
  - `com.anthonyhilyard.iceberg.events.client.RegisterTooltipComponentFactoryEvent.EVENT`（`TypeTrackedEvent`，把自定义 `TooltipComponent` 映射为 `ClientTooltipComponent`，是 1.21.3 之前缺失的官方扩展点替代）
  - `events.client.NewItemPickupEvent.EVENT`、`events.client.RenderTickEvents.START`、`events.common.CriterionEvent.EVENT`、`events.common.ConfigEvents.{REGISTER,LOAD,RELOAD}`
- 工具/API 静态方法：`util.Tooltips.renderItemTooltip(...)`、`gatherTooltipComponents(...)`、`calculateRect(...)`、`centerTitle(...)`、`renderGradientBackground/renderGradientBorder`（`util/Tooltips.java:160-546`）；`util.GuiHelper.drawGradientRect/blit`；`util.Selectors.itemMatches/validateSelector`；`util.EntityCollector.collectEntitiesFromItem`；`config.IcebergConfig.register(Class, modId)`。
- 扩展点接口：`services/IPlatformHelper`、`IBufferSourceFactory`、`IIcebergConfigSpecBuilder`、`IKeyMappingRegistrar`、`IReloadListenerRegistrar`、`IFontLookup`；`util/ITooltipAccess` 由 `GuiGraphicsMixin` 实现到 `GuiGraphics` 上，供外部读写当前 tooltip 的 `ItemStack`。
- 接入方式：外部 mod 以 `modImplementation/compileOnly` 依赖 Iceberg（CurseForge/Maven 坐标未在仓库中出现，**未确认**），直接引用上述静态事件；Iceberg 自身把 common 与 NightConfig 打包进各平台产物（`shadowJar` + `remapJar`），因此消费方无需再带依赖。同作者生态（Legendary Tooltips、Prism 等 tooltip/UI 增强）即在此 API 上做标题居中、渐变背景、tooltip 图标与自定义组件渲染。
