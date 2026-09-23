# AHilyard/AdvancementPlaques 源码分析报告

## 1. 基本信息

- Mod 名：Advancement Plaques / mod_id：`advancementplaques` / 作者：Grend（anthonyhilyard）/ 版本 1.6.8
- 目标：**MC 1.21.1**，三平台 fabric + forge + neoforge（`gradle.properties`：`fabricVersion=0.108.0+1.21.1`、`forgeVersion=1.21.1-52.0.28`、`neoforgeVersion=21.1.77`）
- 许可证：`CC BY-NC-ND 4.0`（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）
- Gradle：`architectury-plugin` + `dev.architectury.loom` + `io.github.goooler.shadow`；根 `build.gradle` 同样用 `flatDir '../architectury-loom/build/libs'` 的**自建 architectury 工具链**（`architectury-loom-1.7.9999`）
- 编译依赖（`common/build.gradle`）：`../libs/Iceberg-1.21-fabric-1.2.7.jar`、`../libs/Prism-1.21-fabric-1.0.9.jar`、`../libs/ToastManager-1.21-1.1.0.jar`（**本地 libs 目录，仓库中未包含**）；`curse.maven` 的 advancementscreenshot、toastcontrol、jade、wthit、aether
- 运行时依赖：`iceberg` required（>=1.2.2）；`prism`、`toastcontrol` optional（mods.toml）

## 2. 源码规模与包结构

- **15 个 .java，共 1029 行**（实测，含平台壳）；`common` 承担全部逻辑，三个平台模块各 2 个文件
- 包结构：`common/.../advancementplaques/` 根（`AdvancementPlaques.java` 26 行常量与 init）、`client/`、`config/`、`compat/`（6 个可选 mod 适配类）、`ui/`（`ToastComponentWrapper.java` 150 行）、`ui/render/`（`AdvancementPlaque.java` 352 行）
- 最大文件：`ui/render/AdvancementPlaque.java` 352、`config/AdvancementPlaquesConfig.java` 251、`ui/ToastComponentWrapper.java` 150

## 3. 入口与注册

`AdvancementPlaques.java:23-27` 只有一个 `init()` → `AdvancementPlaquesConfig.register(AdvancementPlaquesConfig.class, MODID)`（Iceberg 配置注册）+ 两个 `ResourceLocation` 贴图/音效常量（`TEXTURE_PLAQUES`、`TEXTURE_PLAQUE_EFFECTS`，音效用 `SoundEvent.createVariableRangeEvent`）。

平台壳仅负责"在客户端启动后替换 Toast 组件"：
- NeoForge：`@Mod(value = MODID, dist = Dist.CLIENT)` 构造器里 `AdvancementPlaques.init()`，再 `@SubscribeEvent(priority = EventPriority.LOWEST) FMLClientSetupEvent` → `event.enqueueWork(() -> AdvancementPlaquesClient.wrapToasts(Minecraft.getInstance()))`（`neoforge/.../AdvancementPlaquesNeoForgeClient.java`）
- Forge：`FMLConstructModEvent` 里 init + 注册事件总线，同样 LOWEST 优先级 `FMLClientSetupEvent`
- Fabric：`ClientLifecycleEvents.CLIENT_STARTED.register(AdvancementPlaquesClient::wrapToasts)`

**核心手法（无 mixin）**：`client/AdvancementPlaquesClient.wrapToasts` 直接把 `minecraft.toast` 字段替换成自己的子类实例：

```java
if (minecraft.toast != null) {
    minecraft.toast = new ToastComponentWrapper(minecraft, minecraft.toast);
}
```
（`common/.../client/AdvancementPlaquesClient.java:12-30`；`Minecraft.toast` 的 `mutable` 由 AW 授予）

## 4. 核心系统

1. **ToastComponent 装饰器**：`ui/ToastComponentWrapper extends ToastComponent` 持有 `wrapped`（原版组件）并全部转发；`addToast` 拦截 `AdvancementToast`，若 `AdvancementPlaquesConfig.showPlaqueForAdvancement()` 通过则放进自己的 `Deque<AdvancementToast> advancementToastsQueue`，否则交还原版（`:48-64`）；`render` 先渲染 wrapped，再渲染自己的 plaque 数组（`AdvancementPlaque[] plaques = new AdvancementPlaque[1]`，同时最多一条），队列出队补位；`wrapLock`（`ReentrantLock(true)` 公平锁）保护对 wrapped 的并发访问（`:37-139`）
2. **牌匾渲染器**：`ui/render/AdvancementPlaque.java`（352 行）——256×32 贴图九宫格绘制，按 `DisplayInfo.getType()`（TASK/GOAL/CHALLENGE）分别取配置里的 fadeInTime/fadeOutTime/duration（单位秒 ×1000 转毫秒）；`getVisibility(currentTime)` 用 `Mth.clamp((now-animationTime)/200f)` 再平方做淡入曲线；暂停/加载界面（`PauseScreen`/`LevelLoadingScreen`）时**不推进计时**直接返回 `Visibility.SHOW`（`:69-77`）；用 `graphics.drawManaged(...)` 保证与物品模型渲染的 z 层正确；个别渲染器（如 Canvas）下淡出 alpha 直接置 0 的硬兼容写在 `:115-118`
3. **配置系统**：`config/AdvancementPlaquesConfig.java` 用 Iceberg 的 `IIcebergConfigSpecBuilder`：`on_top`、`hide_waila`、`tasks/goals/challenges` 开关、title/name 颜色（支持 `#AARRGGBB`，装有 Prism 时支持 Prism 颜色定义）、`blacklist`/`whitelist`（支持模组 ID、`minecraft:story/` 这类分类前缀）
4. **过滤逻辑**：`showPlaqueForAdvancement(AdvancementHolder)`（`:131-163`）先查黑名单 → 无 `display()` 直接 false → 按类型开关过滤 → 被过滤时再查白名单救回，逻辑清晰可抄
5. **可选依赖隔离**：`compat/` 下 6 个类（WailaHandler/JadeHandler/AdvancementScreenshotHandler/PrismHandler/AetherHandler）**全部由 `Services.getPlatformHelper().isModLoaded("xxx")` 判定后用 `Class.forName(...).getMethod(...).invoke(null)` 反射调用**，本 mod 代码不直接 import 它们，避免类加载期崩溃：

```java
Class.forName("com.anthonyhilyard.advancementplaques.compat.WailaHandler").getMethod("disableWaila").invoke(null);
```
（`ui/ToastComponentWrapper.java:96-115`；先 `Services.getPlatformHelper().isModLoaded("waila"/"jade")` 判断，弹牌匾时临时关掉 HUD 提示，`hideWaila` 配置开启时）

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无（纯客户端）
- 数据驱动：无数据包/资源重载；贴图固定为 `advancementplaques:textures/gui/plaques.png` 与 `plaqueeffect.png`
- 配置：Iceberg 配置注册（`AdvancementPlaquesConfig.register(class, MODID)`），`getInstance()` 从静态 `configInstances` 取
- datagen：无
- AW（`common/src/main/resources/advancementplaques.accesswidener`）：`AdvancementToast.advancement`（accessible）、`Minecraft.toast`（**accessible + mutable**，这是本 mod 无 mixin 的关键）、`Minecraft.itemColors`、`ItemRenderer.blockEntityRenderer`

## 6. Mixin

**无任何 mixin**：本仓库没有任何 `*.mixins.json`，改原版行为完全靠 (a) AW 让 `Minecraft.toast` 可写 + 子类替换，(b) Iceberg 提供的事件/渲染工具（`CustomItemRenderer`、`GuiHelper`），(c) 反射调用可选的 Jade/Waila/Prism/Aether API。

## 7. 值得学的 5 条具体做法

1. **用 AW 把 `Minecraft.toast` 变成 mutable，然后继承原组件做装饰器**（`ToastComponentWrapper`），比 mixin 更稳、可与其他 mod 的 toast 组件链式共存（`wrapToasts` 里传入 `minecraft.toast` 而非 new 一个）。适用：替换/包装原版 GUI 组件的场景。
2. **装饰器模式 + 转发 + 拦截**：只对 `AdvancementToast` 特判，其余 toast 原样转发给被包装对象（`addToast`/`render`/`clear` 三处加锁），第三方 toast mod 不受影响。
3. **公平重入锁保护跨组件调用**：`private final ReentrantLock wrapLock = new ReentrantLock(true);` 包住所有对被包装组件的调用（`ToastComponentWrapper.java:27, 40-43, 61-63, 75-77, 144-146`）。
4. **可选 mod 兼容用"isModLoaded 判断 + 反射调用"**，把兼容类放在独立包并由类名字符串引用（`compat/*Handler`），彻底避免类加载错误。
5. **动画时长全部走配置且按成就类型分档**（task/goal/challenge 各自的 fadeIn/fadeOut/duration），并在暂停/加载画面时冻结计时（`AdvancementPlaque.java:69-104`），避免玩家暂停后回来动画错乱。

## 8. 公开 API

本 mod 无对外注册 API；它本身是 Iceberg/Prism 的下游消费者。可复用的公开面是"平台抽象"用法：`Services.getPlatformHelper().isModLoaded(...)`、Iceberg 的 `CustomItemRenderer`/`GuiHelper`，以及平台壳里统一的 `init()` + `wrapToasts()` 分层（common 逻辑 / 平台入口只做时机控制）。
