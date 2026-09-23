# Terrails/colorful-hearts 源码分析报告

## 1. 基本信息
- Mod 名：Colorful Hearts；mod_id：`colorfulhearts`；作者：Terrails；许可证：MIT
- 目标：**Minecraft 1.21.1**，Fabric（loader 0.16.14 / Fabric API 0.116.4+1.21.1）与 **NeoForge 21.1.195** 双端（`gradle.properties`），mod_version `10.5.9`
- Gradle：Architectury 多项目（`architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.10-SNAPSHOT` + `com.gradleup.shadow 8.3.6`，另有 minotaur / curseforgegradle 发布插件，`build.gradle`）
- 子项目：`:api:common`、`:api:fabric`、`:api:neoforge`、`:common`、`:fabric`、`:neoforge`；**api 模块用 `maven-publish` 单独发布**（artifactId `colorfulhearts-<loader>-api`）；使用 accesswidener（`common/src/main/resources/colorfulhearts.accesswidener`）
- 纯客户端 mod：`@Mod(value = ..., dist = Dist.CLIENT)`，`neoforge.mods.toml` 中 `displayTest = "IGNORE_ALL_VERSION"`、依赖 side 全为 `CLIENT`
- 编译依赖：Fabric API / NeoForge；运行时可选 AppleSkin、Farmer's Delight、Undergarden、Overflowing Bars、Cloth Config（`neoforge/build.gradle`）

## 2. 源码规模与包结构
- 53 个 `.java`，合计 **4207 行**；按子项目分布：`api/common` 8、`api/neoforge` 4、`api/fabric` 2、`common` 20、`fabric` 10、`neoforge` 9
- 包（第 3 层）：`terrails/colorfulhearts`（根：`CColorfulHearts`、`PlatformProxy`）、`render`(4)+`render/atlas/sources`(1)、`config`(4)+`config/screen`(3)+`config/screen/base`+`widgets`、`mixin`(1)、`compat`(2)；`api/heart`、`api/heart/drawing`、`api/event`
- 最大文件：`config/screen/ColorSelectionScreen.java`(361)、`render/ImageUtils.java`(257)、`fabric/config/FabConfig.java`(222)、`render/atlas/sources/ColoredHearts.java`(207)、`api/heart/drawing/OverlayHeart.java`(173)、`render/HeartUtils.java`(169)、`config/ConfigOption.java`(150)、`neoforge/ColorfulHearts.java`(141)、`api/event/HeartRenderEvent.java`(121)

## 3. 入口与注册
`neoforge/src/main/java/terrails/colorfulhearts/neoforge/ColorfulHearts.java`：
```java
public ColorfulHearts(final IEventBus bus, final ModContainer container) {
    CColorfulHearts.setup(new PlatformProxyImpl());
    CONFIG_SPEC = this.setupConfig();
    container.registerConfig(ModConfig.Type.CLIENT, CONFIG_SPEC, MOD_ID + ".toml");
    container.registerExtensionPoint(IConfigScreenFactory.class, ... new ConfigurationScreen(lastScreen));
    bus.addListener(this::setup); bus.addListener(this::registerSprite);
    bus.addListener(this::loadConfig); bus.addListener(this::reloadConfig);
    this.setupCompat(bus);
}
```
- **无 DeferredRegister**：客户端 mod 无注册表内容；注册点只有 (a) `RegisterSpriteSourceTypesEvent` 注册 `colorfulhearts:colored_hearts` 图集源（`:63-65`），(b) 配置界面扩展点 `IConfigScreenFactory`，(c) `NeoForge.EVENT_BUS.addListener(EventPriority.LOWEST, RenderEventHandler.INSTANCE::renderHearts)`（`:59-61`，LOWEST 保证在其它 HUD 层之后接管）。
- 配置用**反射扫描**：`setupConfig()` 遍历 `Configuration.HEALTH/ABSORPTION` 的字段，凡 `instanceof ConfigOption` 就 `define/defineList` 并 `option.initialize(value, value::set)`，实现"字段即配置项"（`:83-108`）。
- 兼容加载：`COMPAT = {appleskin, undergarden, overflowingbars}` 映射到 `neoforge.compat.*` 类名，`ModList.get().isLoaded(id)` 后 `Class.forName` 反射实例化（`:110-140`）。

## 4. 核心系统
1. **血条渲染器** `render/HeartRenderer.java`：`renderPlayerHearts(...)` 复刻原版节奏——`random.setSeed(tickCount * 312871)` 与香草同步随机、`Mth.ceil(min(maxHealth,20)/2.0)` 计算心数、再生效果用 `tickCount % ceil(min(maxHealth,20)+5)` 做上下浮动、低血量（`currentHealth+absorption<=4`）抖动；**用 lastHealth/lastMaxHealth/lastAbsorption/lastHardcore/lastOverlayType 做缓存键**，只有变化才重算 `Heart[]`（`:55-64`）；每颗心调用 `PROXY.preRenderEvent/singleRenderEvent/postRenderEvent`（平台无关事件代理）。
2. **血量→心阵列映射** `render/HeartUtils.java#calculateHearts`：`bottomHealthRow = floor(health/20)-1` 决定配色索引并按 `(i+1)%size` 取两色交替；吸收心偏移 `absorbingOffset = min(10, ceil(maxHealth/2))` 处理"血量不足 10 颗时吸收同行显示"；半心背景用 `Heart.half/Heart.CONTAINER_HALF`；非不透明 Overlay（如中毒/凋零）会被当作背景层叠在原心之下（`:99-165`）。
3. **数据驱动图集染色** `render/atlas/sources/ColoredHearts.java`：实现 `SpriteSource`，`CODEC = RecordCodecBuilder.mapCodec(... IS_HEALTH.fieldOf("heart"))`（`health|absorption`），在资源重载时按配置颜色列表 × 8 种变体（hardcore/half/blinking 组合）生成 sprite，用 `LazyLoadedImage` + `NativeImage.mappedCopy(colorOperator)` 内存染色，再叠 `_normal/_multiply/_screen/_overlay` 混合贴图（`ImageUtils.blendNormal/Multiply/Screen/Overlay`）。
4. **抽象心对象** `api/heart/drawing/{Heart,HeartDrawing,SpriteHeartDrawing,OverlayHeart}.java`：`Heart` 是 (drawing, half, background) 三元组并做实例缓存（`CACHE`），`OverlayHeart.Builder` 支持 `addHealth/addAbsorption/blankAbsorption/transparent` 组合，`condition` 为 `Predicate<Player>`，由 `Hearts.getOverlayHeartForPlayer(player)` 每帧筛选。
5. **Tab 列表心** `render/TabHeartRenderer.java` + `mixin/PlayerTabOverlayMixin.java`：把原版玩家列表血量改成同一套心渲染。
6. **跨加载器代理** `PlatformProxy`（`common/.../PlatformProxy.java`）：`getLoader/applyConfig/forcedHardcoreHearts/heartRegistryEvent/preRenderEvent/postRenderEvent/singleRenderEvent/heartUpdateEvent`，NeoForge 侧转成 `NeoHeartRenderEvent` 等 Forge 事件，Fabric 侧 `forcedHardcoreHearts` 走 ObjectShare。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无**（纯客户端渲染 mod，无包、无同步）。
- 数据驱动：唯一的"数据"是**图集 sprite source**（资源包可覆写 `heart/<health|absorbing>/<full|half>[_hardcore][_blinking]` 与 `_normal/_multiply/_screen/_overlay` 混合贴图），并新增 accesswidener 打开所需访问。
- 配置：`config/Configuration.java` 用 `ConfigOption<List<String>,List<Integer>>` 存 `#RRGGBB` 字符串，`COLOR_DESERIALIZER = strings -> strings.stream().map(Integer::decode)`，校验用正则 `#[A-Fa-f0-9]{6}`；健康色默认 10 色 + 中毒/凋零/冰冻单色；Fabric 侧另有 `fabric/config/FabConfig.java`（night-config）与 `PlatformProxy.applyConfig` 手动落盘。
- datagen：**无**（无 `src/generated`、无 `runData` 依赖）。

## 6. Mixin
- 配置：`common/src/main/resources/colorfulhearts-common.mixins.json`、`fabric/src/main/resources/colorfulhearts.mixins.json`、`neoforge/src/main/resources/colorfulhearts.mixins.json`（NeoForge 侧带 `plugin: terrails.colorfulhearts.neoforge.NeoMixinPlugin`）
- 代表：`common/.../mixin/PlayerTabOverlayMixin.java` → `@Inject(method = "renderTablistHearts", cancellable = true, at = @At(value = "INVOKE", target = "...GuiGraphics;blitSprite(...IIII)V", opcode = 0))`，用 MixinExtras `@Local PlayerTabOverlay.HealthState` 取值后委托 `TabHeartRenderer`，`ci.cancel()` 掉原版
- 兼容 mixin：`neoforge/.../mixin/compat/appleskin/HUDOverlayHandlerAccessor.java`（`@Accessor`）、`compat/farmersdelight/HUDOverlaysMixin.java`；Fabric 侧另有 `fabric/mixin/GuiMixin.java`

## 7. 值得学的 5 条具体做法
1. **"字段即配置项"的反射式配置生成**：`ConfigOption<T,R>` 带 path/comment/default/serializer/deserializer/validator，主类反射遍历静态字段自动 `define`，新增配置只需加字段（`config/ConfigOption.java` + `neoforge/ColorfulHearts.java:83-108`）。
2. **平台无关的渲染事件代理**：用 `PlatformProxy` 抽象 `preRenderEvent/postRenderEvent/singleRenderEvent`，让 common 代码只依赖接口，NeoForge/Fabric 各自转发到原生事件（`common/.../PlatformProxy.java`）。
3. **1.21 图集 sprite source 做运行时染色**：不预生成贴图，而在资源加载期按配置色映射 `mappedCopy(IntUnaryOperator)` 生成 sprite，并支持资源包叠 `_screen/_normal/...` 混合层（`ColoredHearts.java:94-176`）。
4. **渲染状态缓存键**：把 last* 状态作为缓存键，只有血量/吸收/难度/overlay 类型变化才重算整个 `Heart[]`（`HeartRenderer.java:55-64`），避免每帧分配。
5. **对外兼容零编译依赖**：`Map<String,String> COMPAT` + `Class.forName` 反射加载，兼容类放在独立包下，缺失 mod 时只打 debug 日志（`ColorfulHearts.java:110-140`）。
6. **降低事件优先级接管原版 HUD**：`EventPriority.LOWEST` 监听 `RenderGuiLayerEvent.Pre`，判断 `VanillaGuiLayers.PLAYER_HEALTH` 后自行 `leftHeight` 推算并 `setCanceled(true)`（`neoforge/render/RenderEventHandler.java`）。

## 8. 公开 API（本 mod 也是库）
- 公共 API 包：`terrails.colorfulhearts.api.heart`（`Hearts`：`OVERLAY_HEARTS`、`getOverlayHeartForPlayer`）、`api.heart.drawing`（`Heart`/`HeartDrawing`/`SpriteHeartDrawing`/`OverlayHeart`）、`api.event`（`HeartRegistry.registerOverlayHeart`、`HeartRenderEvent.Pre/Post`、`HeartSingleRenderEvent`）
- 加载器侧桥接：`api/neoforge/event/NeoHeartRegistryEvent|NeoHeartRenderEvent|NeoHeartSingleRenderEvent|NeoHeartUpdateEvent`；`api/fabric/ColorfulHeartsApi` + `FabHeartEvents`
- 外部接入方式：NeoForge 监听 Neo*Event（或在 `HeartRegistry` 注册 Overlay）；Fabric 通过 `ColorfulHeartsApi`（含 ObjectShare 强制 hardcore 心）；两个 api 子项目以 maven artifact 发布（`colorfulhearts-<loader>-api`），消费方无需依赖完整 mod

## 关键词
单行彩色血量渲染、图集 SpriteSource 运行时染色、ConfigOption 反射配置、PlatformProxy 跨加载器、OverlayHeart 扩展
