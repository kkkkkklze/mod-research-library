# YaLTeR/MouseTweaks 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Mouse Tweaks / `mousetweaks` |
| 作者 | Ivan Molodetskikh (YaLTeR)，贡献者 mezz、juliand665、panoskj 等 |
| 版本 | `modVersion = 2.31`（`gradle.properties`） |
| 目标版本 | Minecraft `26.2`（`fabricMcVersion`/`neoMcVersion`/`forgeMcVersion` 均为 26.2），Java 25 |
| 加载器 | Fabric Loader `0.19.3` + Fabric API `0.152.1+26.2`（另依赖 ModMenu `20.0.0-beta.2`）、NeoForge `26.2.0.0-beta`（loader `[4,)`）、Forge `65.0.0`（loader `[65,)`）；**纯客户端 mod**（`fabric.mod.json: "environment": "client"`，`mods.toml: clientSideOnly=true`） |
| Gradle 插件 | 三个独立构建：`net.fabricmc.fabric-loom 1.15-SNAPSHOT`、`net.neoforged.moddev 2.0.141`、`net.minecraftforge.gradle [7.0.17,8)`；另有 `fabric-compat-test` 用 loom 的 `ClientProductionRunTask` |
| 许可证 | BSD-3-Clause（可参考借用） |
| 编译依赖 | Fabric API / Forge / NeoForge 事件 API、mixinExtras（`@WrapOperation`）；无第三方库依赖 |

工程组织是最大亮点：**根目录没有 build.gradle**，`fabric/`、`neoforge/`、`forge/` 各自是独立 Gradle 构建（各有 `settings.gradle`，`gradle.properties` 只有一行 `../gradle.properties` 引用），三个构建都用 `sourceSets.main.java.srcDirs = ['../src/main/java']` 共享源码，并各自 `exclude` 掉其他 loader 的包；版本号通过 `processResources { filesMatching('fabric.mod.json'|'META-INF/*.mods.toml') { expand([...]) } }` 注入。README 里的构建命令即 `./gradlew -p fabric build`。

## 2. 源码规模与包结构

29 个 `.java`、2662 行。`src/main/java/yalter/mousetweaks/` 19 个文件（其中 `api/` 3 个 + README），测试 `src/testmodClient/java/yalter/mousetweaks/test/` 3 个文件。

最大文件：`src/testmodClient/java/yalter/mousetweaks/test/InventoryTests.java` 800 行、`src/main/java/yalter/mousetweaks/Main.java` 735 行、`Config.java` 113、`api/IMTModGuiContainer3Ex.java` 100、`forge/MouseTweaksForge.java` 93、`ConfigScreen.java` 86、`neoforge/MouseTweaksNeo.java` 84、`handlers/GuiContainerHandler.java` 78、`handlers/IMTModGuiContainer3ExHandler.java` 59、`fabric/MouseTweaksFabric.java` 36。

包结构：`yalter.mousetweaks`（核心状态机 + 配置 + 枚举）、`.handlers`（3 个 handler 实现）、`.api`（对外兼容 API + 2 个注解）、`.fabric` / `.neoforge` / `.forge`（各 loader 入口）、`.mixin` + `.fabric.mixin`（访问器与 drag hook）。`ScrollHandling.java` 与 `IMouseState.java` 全仓库无引用，疑似遗留未使用（未确认）。

## 3. 入口与注册

无注册表（纯客户端），入口是"事件接线 + 单例状态机"。核心 `Main.java` 是静态状态机：

```java
private static Screen openScreen = null;
private static IGuiScreenHandler handler = null;
private static boolean disableWheelForThisContainer = false;
private static Slot oldSelectedSlot = null;
private static double accumulatedScrollDelta = 0;
private static boolean canDoLMBDrag = false, canDoRMBDrag = false, rmbTweakLeftOriginalSlot = false;
```

- `Main.initialize()`：建 `Minecraft` 引用，`new Config(gameDir + "/config/MouseTweaks.cfg")` 并 `read()`。
- `Main.updateScreen(Screen)`：换界面时重置全部标志，重读配置文件，`findHandler()` 选 handler（`Main.java:607`）：`IMTModGuiContainer3Ex` → `GuiContainerCreativeHandler` → 任一 `AbstractContainerScreen` → null（null 即整体禁用）。
- 三个 loader 入口文件：`neoforge/MouseTweaksNeo.java`（`@Mod`）、`forge/MouseTweaksForge.java`（`@Mod` + `BusGroup.DEFAULT.register(MethodHandles.lookup(), this)` + 内部类 `@Mod.EventBusSubscriber`）、`fabric/MouseTweaksFabric.java`（`ClientModInitializer`）。

## 4. 核心系统

**① 事件接线差异**（跨 loader 的关键学习点）：NeoForge/Forge 用 `ScreenEvent.MouseButtonPressed.Pre` / `MouseButtonReleased.Pre` / `MouseDragged.Pre`（可取消，`event.setCanceled(true)` 或返回 `true`），滚轮用 `MouseScrolled.Post`（不可取消，仅当无人处理时才触发）；Fabric 用 `ScreenMouseEvents.allowMouseClick/allowMouseRelease`（返回 `!Main.onMouseClicked(...)`）与 `afterMouseScroll`，拖拽则因 Fabric API 无对应 hook，改用 `fabric/mixin/MixinMouseHandler.java` 的 `@WrapOperation(method="handleAccumulatedMovement", target=Screen.mouseDragged)`，Mouse Tweaks 处理时直接 `return true` 跳过原调用。设计取舍全部记录在 `notes.txt`（例如"Forge 的 Post click/release 事件永远不会送达"）。

**② 三个拖拽 tweak**（`Main.onMouseClicked/onMouseDrag/onMouseReleased`，`Main.java:101/205/182`）：用"点击时置标志、拖到新槽位才动作、松开清标志"的状态机，避免依赖原版 `isQuickCrafting`。`onMouseDrag` 先判 `selectedSlot == oldSelectedSlot` 直接返回（原版拖拽每秒上报上百次）；RMB 拖拽首次离开原槽位时调 `handler.disableRMBDraggingFunctionality()` 关掉原版 quickCrafting；LMB 拖物品合并前有硬约束——`stackOnMouse.getCount() + selectedSlotStack.getCount() > stackOnMouse.getMaxStackSize()` 则不动作（否则物品会卡死在槽里），并且非合成输出槽要点两次（合并 + 取回）。

**③ 滚轮 tweak**（`Main.onMouseScrolled`，`Main.java:306-586`）：先做缩放与累加 `accumulatedScrollDelta`（与 `MouseHelper.scrollCallback` 同法，方向反转时清零），`delta = (int) accumulatedScrollDelta` 得到要移动的物品数与方向；`WheelScrollDirection` 的 `isPositionAware()` 配合 `otherInventoryIsAbove()`（`Main.java:588`，比较上下方"另一侧背包槽位数"）决定推/拉方向。推送用 `findPushSlots`（`Main.java:683`）两趟：先塞兼容且未满的非空槽，再用空槽；合成输出槽要求 `mustDistributeAll=true`（一批只能整批搬）。拉取用 `findPullSlot`（`Main.java:632`）按 `WheelSearchOrder` 正向/反向扫描，只找"容器归属不同侧"的兼容槽。拾取默认用右键，原因写在注释里：右键不会重置熔炉熔炼进度、也不会把物品塞进收纳袋（bundle）；仅当鼠标为空且槽内数量 ≤ 需搬运量时改用左键。

**④ 兼容 API 层**：`IGuiScreenHandler`（`IGuiScreenHandler.java`）抽象出 8 个操作（`getSlotUnderMouse/clickSlot/isIgnored/isCraftingOutput/disableRMBDraggingFunctionality`…），`GuiContainerHandler` 用 `AbstractContainerScreenAccessor` 实现，`GuiContainerCreativeHandler` 只额外覆写 `isIgnored`（`slot.container != mc.player.getInventory()`，即屏蔽创造模式物品列表），`IMTModGuiContainer3ExHandler` 把调用转发给第三方容器。

**⑤ 手写配置系统**：`Config.java` 用 `java.util.Properties` 读写 `config/MouseTweaks.cfg`（布尔写成 `1/0`，枚举写 ordinal，`static` 块提供默认值），每次开界面 `read()` 一次，`ConfigScreen.removed()` 时 `save()`；配置界面用 `CycleButton` 手搓（`ConfigScreen.java`），Fabric 走 ModMenu、NeoForge 走 `IConfigScreenFactory`、Forge 走 `MinecraftForge.registerConfigScreen`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无（纯客户端）。
- 数据驱动：无。仅有 `pack.mcmeta`。
- 配置：见 ④（`config/MouseTweaks.cfg`，非 TOML，逐行 `Key=Value` 手写）。
- datagen：NeoForge 构建里配了 `clientData` run（`--mod mousetweaks --all --output build/generated/resources`），但主源码无 DataProvider，属于模板残留。

## 6. Mixin

- `src/main/resources/mousetweaks.mixins.json`（package `yalter.mousetweaks.mixin`，client）：`AbstractContainerScreenAccessor` —— `@Invoker("getHoveredSlot")`、`@Invoker("slotClicked")`（Mojang 映射下的 protected 成员）、`@Accessor("isQuickCrafting")`(get/set)、`quickCraftingButton`(get)、`skipNextRelease`(set)、`leftPos`/`topPos`(get)。
- `src/main/resources/mousetweaks-fabric.mixins.json`（package `yalter.mousetweaks.fabric.mixin`）：`MixinMouseHandler` —— `@WrapOperation` 注入 `MouseHandler.handleAccumulatedMovement` 内对 `Screen.mouseDragged(MouseButtonEvent, DD)Z` 的调用。
- NeoForge/Forge 侧不额外加 mixin（事件够用），只在 run 配置里加 `--mixin.config=mousetweaks.mixins.json`。

## 7. 值得学的 5 条具体做法

1. **一份 `src/main/java` 被三个独立 Gradle 构建共享**：各 loader 构建 `srcDirs = ['../src/main/java']` 并互相 `exclude` 对方包，见 `fabric/build.gradle`、`neoforge/build.gradle`、`forge/build.gradle`；比 MultiLoader-Template 的子工程 + 源集复制更简单直白，适合小型客户端 mod。
2. **入口只做适配、逻辑全在一个静态状态机**：`Main.onMouseClicked/onMouseDrag/onMouseReleased/onMouseScrolled` 全 loader 同签名，各 loader 文件 30-90 行只负责转发与取消事件；换 MC 版本时只需改事件绑定。
3. **抽象 handler 支持第三方容器接管**：`IGuiScreenHandler` + `findHandler` 的 if-else 链（`Main.java:607`），配合 `api.IMTModGuiContainer3Ex`（全部方法 `MT_` 前缀避免冲突）与 `@MouseTweaksIgnore`/`@MouseTweaksDisableWheelTweak` 注解；对外还额外产出 `apiJar`（`neoforge/build.gradle` 里 `tasks.register('apiJar')` 只打包 `yalter/mousetweaks/api/**`）。
4. **客户端自动化游戏测试**：`src/testmodClient` 用 Fabric 的 `FabricClientGameTest` 真启动客户端、模拟输入并断言槽位物品（`InventoryTests.java` 有 `testRmbTweak/testLmbTweakWithItem/testWheelTweak/testWheelTweakWithBundle/testCraftingOutputSlot/testFurnaceSmeltingPreserved` 等 9 个用例，`InventoryTestHelper` 提供 `assertSlotContains/assertSlotEmpty`）；`fabric-compat-test` 更进一步：对**预编译的生产 jar** 跑同一套测试（`ClientProductionRunTask` + `-Dfabric.noGui=true`），用来在 MC 补丁版发布后自动验证兼容性——非常适合 GUI 交互类 mod 的回归测试。
5. **把事件语义调研写进仓库**：`notes.txt` 记录了各 loader 事件的可取消性、触发时机与拖拽上报频率，以及"用标志位而非依赖原版 dragSplitting"的决策过程；配合 `Logger.DebugLog`（`Config.debug` 开关）在 UI 里可实时开调试日志。
