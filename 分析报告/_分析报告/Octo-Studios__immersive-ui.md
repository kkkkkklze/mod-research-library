# Octo-Studios/immersive-ui 源码分析报告

## 1. 基本信息
- Mod 名：ImmersiveUI；mod_id `immersiveui`；作者 OctoStudios；版本 0.3.2（`gradle.properties:7`）
- 目标 MC / 加载器：MC **1.21.1**（`gradle.properties:16`），Fabric + NeoForge 双平台（`enabled_platforms = fabric,neoforge`，无 quilt），Architectury API 13.0.6、fabric_loader 0.15.11、fabric_api 0.114.0+1.21.1、neoforge 21.1.90
- Gradle：`dev.architectury.loom 1.10-SNAPSHOT` + `architectury-plugin 3.4-SNAPSHOT` + `com.gradleup.shadow 8.3.6`（`build.gradle:1-5`）；mappings 用 official + Parchment `parchment-1.21.1:2024.11.17`；Lombok 1.18.32
- 许可证：All Rights Reserved（`gradle.properties:11`）
- 编译依赖：**octolib `0.6.0.3+1.21`**（`gradle.properties:22`，neoforge.mods.toml 中 `[[dependencies.immersiveui]] modId="octolib" required versionRange="[0.6.0.3,)" side="CLIENT"`）；minecraft/neoforge 依赖同样 `side = "CLIENT"` —— 这是一个**纯客户端模组**
- 快照内未见 `fabric.mod.json`（architectury 工程缺失，未确认原因）；neoforge.mods.toml 声明两个 mixin 配置：`immersiveui-common.mixins.json` + `immersiveui.mixins.json`

## 2. 源码规模与包结构
- 33 个 `.java`，共 1352 行（小体量，纯 mixin + 工具）
- 包结构（文件数）：`common/.../immersiveui/mixin`(13)、`util`(4)、`compat`(4)、`client`(3)、`client/particle`(2)、根包(2：`ImmersiveUI`、`Config`)、`neoforge/.../neoforge/mixin`(2)、`neoforge`(1)、`fabric`(2)
- 最大文件：`util/CommonCode.java`(168)、`mixin/AbstractContainerScreenMixin.java`(162)、`neoforge/mixin/StorageScreenBaseMixin.java`(124)、`util/RenderUtils.java`(121)、`mixin/InGameHudMixin.java`(68)、`util/Easing.java`(65)、`Config.java`(65)

## 3. 入口与注册
- `common/.../ImmersiveUI.java:8-14`：`MOD_ID`、`public static Config CONFIG`、`public static SophisticatedProxy SOPHISTICATED_COMPAT`，`init()` 为空（无内容注册）
- Fabric：`fabric/.../ImmersiveUIFabric.java` 在 `onInitialize()` 里 `ConfigManager.registerConfig("immersiveui", ImmersiveUI.CONFIG)`（直接调 octolib 的 API）；`ImmersiveUIFabricClient` 为空壳
- NeoForge：`neoforge/.../ImmersiveUINeoForge.java`（`@Mod(ImmersiveUI.MOD_ID)` + `@EventBusSubscriber(bus=MOD)`）构造里调 `ImmersiveUI.init()`，若 `Platform.isModLoaded("sophisticatedcore")` 则 `Class.forName("...compat.SophisticatedCompat").getDeclaredConstructor().newInstance()` 反射装入真实兼容实现；`@SubscribeEvent FMLCommonSetupEvent` 中注册配置
- 注册框架：**没有内容注册**（无 DeferredRegister/注册表），只有"配置注册 + mixin 挂点 + 兼容实现替换"

## 4. 核心系统
1. **配置（外部 API 接入示例）**：`Config.java` 实现 octolib 的 `OctoConfig`，18 个 `@Prop(comment=...)` 字段（`enableHotbarSelectorAnimation`、`enableRarityParticles`、`hotbarSelectorSpeed`、`hoveredItemScale`、`enableScreenShake`、`shakeTimer`、`enableCurseFormatting`…），用 Lombok `@Data` 生成 getter/setter —— 库前置的正确用法样板（库负责文件 IO/同步，mod 只写 POJO）
2. **容器屏沉浸式渲染**：`mixin/AbstractContainerScreenMixin.java`（`abstract class ... implements ExtraScreenData`），用 `@Unique Map<Slot,Float> expandingProgress`、`@Unique MouseInfo/RenderInfo/timerCommon` 存每个屏的动画状态；hook：`renderBackground` 中 `INVOKE renderBg` 前(`:97`)、`renderFloatingItem@HEAD(cancellable)`(`:114`)、`renderSlot` 中 `renderItem` 前(`:124`, `require=0`)、`renderSlotHighlight@HEAD(cancellable)`(`:129`)、`render` 中 `INVOKE Slot.isActive` 前 + `locals = LocalCapture.CAPTURE_FAILSOFT`(`:144`)、`render@RETURN`(`:158`)
3. **快捷栏（hotbar）动画**：`mixin/InGameHudMixin.java`（`@Mixin(value = Gui.class, priority = -1)`）在 `renderItemHotbar` 里对 `blitSprite` 的 `ordinal = 1` 调用做 `@Inject(BEFORE/AFTER)` 包住选中框，并 `@ModifyArg(index = 1)` 改参数；选择框速度来自 `Config.hotbarSelectorSpeed`
4. **UI 粒子**：`client/particle/FlameUIParticle.java`、`RarityUIParticle.java`（继承 octolib 的 `UIParticle`）；`util/CommonCode.renderFurnaceParticles(...)`（`:41` 起，`Random` + `FlameUIParticle(fuelSlot.x+8±6, ...)`，带 `AtomicBoolean shouldBurst` 一次性爆发）；节流逻辑 `CommonCode.gooeyRenderCode`：`TARGET_INTERVAL_MS = 350` 的"时间片"状态机存在 `client/VariableStorage.java:9`，另有 `SCREEN_ZORDER = 50`、`shakeScreen` 列表
5. **软依赖兼容（可选 mod 集成）**：接口 `compat/SophisticatedProxy`（`isStorageScreenBase(Screen)`）+ 默认空实现 `DummySophisticatedCompat` + 真实实现 `SophisticatedCompat`；由 NeoForge 入口用 `Class.forName` 只在实际装了 Sophisticated Core 时加载，配套 NeoForge 专属 mixin `neoforge/mixin/StorageScreenBaseMixin.java`(124 行) 与 `FloatingItemMixin.java`(51 行)
6. **其余观感效果**：`mixin/EnchantmentMixin.java:21` 在 `Enchantment.getFullname` 的 `ComponentUtils.mergeStyles` 后注入（诅咒附魔特殊格式）、`EnchantmentScreenMixin`（附魔台粒子 + `mouseClicked` 中 `handleInventoryButtonClick` 钩点）、`AdvancementToastMixin`（`renderFakeItem` 前后包裹做"抖动"）、`AnvilMenuMixin`/`SmithingMenuMixin`（`onTake@HEAD` 触发效果）、`GooeyMixin`（`Gui.render@TAIL`）

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无**（无自定义包注册，全部效果本地/客户端计算）
- 配置：委托 octolib `ConfigManager.registerConfig`；两个平台各写一遍（Fabric `onInitialize`、NeoForge `FMLCommonSetupEvent`）
- 数据驱动：无
- datagen：无

## 6. Mixin
- `common/src/main/resources/immersiveui-common.mixins.json`（client 列表 13 个：`AbstractContainerScreenAccessor`、`AbstractContainerScreenMixin`、`AbstractFurnaceMenuAccessor`、`AbstractFurnaceScreenMixin`、`AdvancementToastMixin`、`AnvilMenuMixin`、`EnchantmentMixin`、`EnchantmentScreenMixin`、`GooeyMixin`、`InGameHudMixin`、`ItemStackMixin`、`ScreenMixin`、`SmithingMenuMixin`；`compatibilityLevel` 写 `JAVA_17`）
- `neoforge/src/main/resources/immersiveui.mixins.json`（client：`FloatingItemMixin`、`StorageScreenBaseMixin`）
- 注入点要点：以 `ordinal = 1` + `blitSprite` 定位原版热键栏贴图（`InGameHudMixin.java:35,40,45`）；以 `LocalCapture.CAPTURE_FAILSOFT` 拿循环局部变量（`AbstractContainerScreenMixin.java:144`）；对同屏状态用 `@Unique` 字段挂在 mixin 类上而非全局 Map（`AbstractContainerScreenMixin.java:37`）

## 7. 值得学的 5 条具体做法
1. 用"接口 + Dummy 实现 + Class.forName 反射真实现"做可选依赖（`compat/SophisticatedProxy.java`、`ImmersiveUINeoForge.java` 构造中 `Platform.isModLoaded(...)` 判断）—— 想兼容某个 mod 但不想硬依赖时最干净的写法。
2. 平台专属 mixin 的放在 `neoforge/` 模块、各自 mixin json（`neoforge/src/main/resources/immersiveui.mixins.json`），只在目标 class 存在的平台启用 —— 跨平台工程处理"只存在于一个 loader 环境的目标类"。
3. 每个屏幕的动画状态挂在 mixin 类自身的 `@Unique` 字段上（`mixin/AbstractContainerScreenMixin.java:26-52`），配 `ExtraScreenData` 接口对外暴露 —— 比全局静态 Map 更不容易泄漏。
4. 用 `AtomicBoolean shouldBurst` 做"进屏一次性爆发"效果（`util/CommonCode.java:41` 起，`renderFurnaceParticles(..., AtomicBoolean shouldBurst)`）—— 状态放在调用方（mixin 字段）而不是粒子类里，避免每次 `new` 粒子丢状态。
5. 把"节奏"统一成 350ms 时间片（`client/VariableStorage.java:9-15` 的 `TARGET_INTERVAL_MS/currentTime/elapsedTime`）再用 `CommonCode.gooeyRenderCode()` 每帧推进 —— 需要多种 UI 动画共享节拍时很省事，且成本极低。

## 8. 公开 API / 接入方式（说明：本身不是库，而是 octolib 的消费者）
- 本 mod 无对外 API；反向价值在于它是 **octolib 下游接入的最佳参考实现**：
  - 配置接入：`common/.../immersiveui/Config.java`（实现 `OctoConfig` + `@Prop` 字段）+ 两平台注册点（`fabric/.../ImmersiveUIFabric.java:9`、`neoforge/.../ImmersiveUINeoForge.java` 的 `FMLCommonSetupEvent`）
  - 兼容层接口暴露：`compat/ExtraScreenData`、`compat/SophisticatedProxy`（供 mixin 与兼容实现互相通信）
- 依赖声明方式：NeoForge 在 `neoforge.mods.toml` 中列 `architectury`/`octolib` 为 `required` 且 `side="CLIENT"`
