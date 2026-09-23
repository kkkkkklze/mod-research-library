# Schauweg/Smooth-Swapping 源码分析报告

## 1. 基本信息

- Mod 名：Smooth Swapping；mod_id：`smoothswapping`；作者：Schauweg；版本 `0.9.3`
- 目标：Minecraft `1.21`，Java 21。**多加载器（Architectury 三层结构：`common/` + `fabric/` + `neoforge/`）**
  - Fabric：Loader `0.16.5`、Fabric API `0.102.0+1.21`、ModMenu `11.0.2`
  - NeoForge：`21.0.167`（`gradle.properties`、`neoforge.mods.toml` 要求 neoforge `[21,)`、minecraft `[1.21,)`）
- Gradle：`architectury-plugin 3.4-SNAPSHOT`、`dev.architectury.loom 1.6-SNAPSHOT`、`me.shedaniel.unified-publishing`（`build.gradle:1-5`）；Mappings 用 Yarn `1.21+build.9` + `dev.architectury:yarn-mappings-patch-neoforge`（`build.gradle:22-27`）
- 许可证：GNU LGPL 3.0（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）
- 编译依赖：common 只依赖 fabric-loader（仅为 `@Environment` 与 mixin 注解，`common/build.gradle`），无第三方 mod 依赖；纯客户端 mod

## 2. 源码规模与包结构

- `.java` **24 个文件，共 1944 行**（`find -name '*.java' -exec wc -l {} +`）
- 包结构（`dev.shwg.smoothswapping`）：
  - 根 5 个：`SmoothSwapping`(全局状态)、`SwapUtil`、`SwapStacks`(diff 记录)、`Vec2`(自带向量)、`ItemStackAccessor`(duck 接口)
  - `swaps/` 3 个：`InventorySwap`(基类)、`ItemToItemInventorySwap`、`ItemToCursorInventorySwap`
  - `config/` 5 个：`Config`、`ConfigManager`、`ConfigScreen`、`CatmullRomWidget`(曲线编辑器)、`InventoryWidget`
  - `mixin/` 5 个：`HandledScreenMixin`、`DrawContextMixin`、`ClickSlotPacketMixin`、`ItemStackMixin`、`SimpleInventoryAccessor`
  - `fabric/`、`neoforge/` 各 1-3 个平台入口 + 各自 `config/*/ConfigManagerImpl`
- 最大文件：`config/CatmullRomWidget.java`(12.0KB)、`mixin/DrawContextMixin.java`(11.9KB)、`mixin/HandledScreenMixin.java`(9.5KB)、`config/InventoryWidget.java`(8.2KB)、`SwapUtil.java`(6.0KB)

## 3. 入口与注册

无内容注册（客户端渲染 mod），仅初始化与平台差异注入：

```java
// fabric/.../SmoothSwappingFabric.java
public class SmoothSwappingFabric implements ClientModInitializer {
    @Override public void onInitializeClient() { SmoothSwapping.init(); }
}
// neoforge/.../SmoothSwappingNeoForge.java
@Mod(SmoothSwapping.MOD_ID)
public class SmoothSwappingNeoForge {
    public SmoothSwappingNeoForge() {
        SmoothSwapping.init();
        ModLoadingContext.get().registerExtensionPoint(IConfigScreenFactory.class, ConfigScreenFactory::new);
    }
}
```

跨加载器差异用 Architectury `@ExpectPlatform` 抽成静态方法：`ConfigManager.getConfigPath()`（`config/ConfigManager.java:20-21`），由两端的 `ConfigManagerImpl` 实现。全局状态集中在 `SmoothSwapping.java:23-30`（`swaps` Map、`oldStacks/currentStacks` DefaultedList、`currentCursorStack` AtomicReference + `ReentrantLock`）。

## 4. 核心系统

**a) 库存 diff → swap 推断** `mixin/HandledScreenMixin.java:47-171`
- `@Inject(method = "render", at = @At("HEAD"))`，每帧把 `handler.getStacks()` 存为 `currentStacks`，与上一帧 `oldStacks` 比对（`smooth_Swapping$getChangedStacks` `:174-184`，逐槽 `ItemStack.areEqual`）。
- 按"变多/变少"分流：变多且 `handler.getSlot(i).canTakePartial(player)` 进 `moreStacks`，变少进 `lessStacks`（`:112-127`），再调 `SwapUtil.assignI2ISwaps / assignI2CSwaps`。
- 屏幕切换、`clickSwap` 标志时清表并重置基准（`:91-102`）；整个 `doRender` 包 try/catch，异常时 `SwapUtil.reset()`（`:49-53`）。
- 用 `@Unique private Screen smooth_Swapping$currentScreen` 记忆上次屏幕。

**b) swap 几何模型** `swaps/InventorySwap.java`、`SwapUtil.java`
- `InventorySwap` 存 `x,y,startX,startY,distance,angle`、`checked`、`amount`、`swapItem`；`hasArrived()` 靠"象限 + 分量符号"判定到达（`SwapUtil.java:22-33` + `getQuadrant(angle)` `:50-52`）。
- `SwapUtil.map()`（`:54-56`）做通用区间重映射，把曲线进度映射到坐标。

**c) 渲染劫持** `mixin/DrawContextMixin.java`
- `@Inject(method = "drawItem(...)", at = @At("HEAD"), cancellable = true)`（`:50`），若该 stack 有 swap 记录则自行绘制动画并 `cbi.cancel()`（`:59-127`）；热键栏内不接管（`smooth_Swapping$isHotbar()`）。
- 用 duck 接口防重入：`ItemStackAccessor.smooth_Swapping$isSwapStack()` / `setIsSwapStack()`（`ItemStackAccessor.java`，实现在 `mixin/ItemStackMixin.java`，`@Unique private boolean isSwapStack`），`SwapUtil.java:65,82` 给复制的 swap stack 打标。
- `drawItemInSlot` 也被 HEAD 注入（`:180`）处理数量文字。

**d) 客户端预测（包级）** `mixin/ClickSlotPacketMixin.java`
- `@Inject` 到 `ClickSlotC2SPacket.<init>(...)` 的 `TAIL`（`:40`），用 `@Shadow` 读 `actionType` / `modifiedStacks` / `slot`；对 `QUICK_MOVE` 判断是否输出槽（`canTakePartial`）决定 `clickSwapStack`，对 `SWAP`（F 键换手）置 `clickSwap = true`，并移除被提前移动的 swap（`SmoothSwapping.swaps.remove(slot)`）。

**e) 可编辑缓动曲线** `config/CatmullRomWidget.java`
- 把 Catmull-Rom 样条做成可拖动控件：`CatmullRomSpline(p0,p1,p2,p3)`、`static getProgress(double t, List<CatmullRomSpline>)`（`:169-175`）、`splinesFromPoints`（`:155`）；曲线控制点序列化为 `Config.curvePoints`（`float[][]`），首尾各补 2 个点模拟端点切线（`config/Config.java:getCurvePoints()`）。

**f) 配置系统** `config/ConfigManager.java` + `Config.java` + `ConfigScreen.java` + `InventoryWidget.java`
- 手写 Gson 加载/保存（非 ClothConfig）：`SmoothSwapping.GSON`（`LOWER_CASE_WITH_UNDERSCORES` + pretty）、`@ExpectPlatform getConfigPath()`、懒加载 `getConfig()`；`ConfigScreen` 是自定义 `Screen`，`InventoryWidget` 提供动画预览。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包；**只读取/拦截原版 `ClickSlotC2SPacket`**（客户端侧），不发送任何自定义包。
- 配置：JSON 手写序列化，路径跨加载器由 `@ExpectPlatform` 决定；无 datagen。

## 6. Mixin

- 配置：`common/src/main/resources/smoothswapping-common.mixins.json`（`compatibilityLevel: JAVA_21`，`client: [ClickSlotPacketMixin, DrawContextMixin, HandledScreenMixin, SimpleInventoryAccessor, ItemStackMixin]`），由 `neoforge.mods.toml` 的 `[[mixins]] config = ...` 引用。
- hook 目标汇总：

| 类 | 目标 | 注入点 |
|---|---|---|
| `HandledScreenMixin` | `HandledScreen.render` | `@At("HEAD")`（`@Shadow handler/x/y`） |
| `DrawContextMixin` | `DrawContext.drawItem(...)` / `drawItemInSlot(...)` | `HEAD`, cancellable |
| `ClickSlotPacketMixin` | `ClickSlotC2SPacket.<init>` | `TAIL` |
| `ItemStackMixin` | `ItemStack` | 实现 duck 接口（无注入点） |
| `SimpleInventoryAccessor` | `SimpleInventory.heldStacks` | `@Accessor` |

## 7. 值得学的 5 条具体做法

1. **帧间 diff 驱动动画**：不注册任何事件，只在 `HandledScreen.render` HEAD 比较前后两个 `DefaultedList<ItemStack>` 快照来推断"发生了什么移动"（`mixin/HandledScreenMixin.java:104,174-184`）。适用于任何"服务端不告知、只能靠观察状态差"的客户端表现层。
2. **mixin 成员统一前缀 `smooth_Swapping$` + `@Unique`**，并用 duck 接口（`ItemStackAccessor`）给原版对象挂临时渲染标记，避免与其它 mixin 撞名（`ItemStackAccessor.java`、`DrawContextMixin.java:52`）。
3. **渲染注入必须 try/catch + 状态复位**：异常时 `SwapUtil.reset()` 全清（`HandledScreenMixin.java:49-53`、`DrawContextMixin.java:53-57`），否则残留 swap 会让物品永久不渲染。这是渲染类 mixin 的必备防御。
4. **用 `@ExpectPlatform` 静态方法抽平台差异**：`ConfigManager.getConfigPath()` 一个方法即可，无需为整个类做平台抽象（`config/ConfigManager.java:20-21`）；NeoForge 侧配置界面走 `IConfigScreenFactory` extension point，Fabric 侧走 ModMenu，二者共用同一个 `ConfigScreen`。
5. **把"用户可编辑缓动曲线"序列化成控制点数组**：`float[][] curvePoints` + Catmull-Rom 插值（`config/Config.java`、`config/CatmullRomWidget.java:169`），配置读写简单且曲线可无限扩展，比枚举动效类型灵活。

## 8. 公开 API

非库 mod，无对外 API 包；`common` 模块可发布到 maven（`common/build.gradle` 的 `mavenCommon` publication），但无文档化扩展点。
