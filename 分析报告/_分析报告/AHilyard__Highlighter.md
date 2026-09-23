# AHilyard/Highlighter 源码分析报告

## 1. 基本信息

- Mod 名 Highlighter / mod_id `highlighter` / 作者 Grend（anthonyhilyard）/ 版本 1.1.11
- 目标 MC **1.21**（`gradle.properties` minecraftVersion=1.21），一套代码构建 **fabric + forge + neoforge** 三平台（`enabledPlatforms=fabric,forge,neoforge`）
- Gradle：Architectury（architectury-plugin + `dev.architectury.loom` + `io.github.goooler.shadow`）。注意 `build.gradle:1-17` 从本地 `../architectury-loom/build/libs` 载入自编译的 `architectury-loom-1.7.9999` 并手动补 ASM/guava 等 classpath——这是一个改过的 loom 分支
- 许可证 **CC BY-NC-ND 4.0**（`neoforge/src/main/resources/META-INF/neoforge.mods.toml:3`）
- 关键依赖 **Iceberg**（`iceberg` required，range `[1.2.0,)`，`ordering=AFTER`，neoforge.mods.toml:28-33）。Highlighter 自身几乎没有基础设施：配置、事件、渲染工具全部来自 Iceberg（`com.anthonyhilyard.iceberg.config.IcebergConfig`、`iceberg.events.client.NewItemPickupEvent / ItemTooltipEvent`、`iceberg.util.ItemColor / Easing / GuiHelper`）。想学"库+内容 mod 分家"的写法，这是最小样本

## 2. 源码规模与包结构

实测 `find -name '*.java' | wc -l` = **12 个文件 / 531 行**（无 datagen、无资源生成代码）。

- `common/.../highlighter/`：`Highlighter.java`(201)、`config/HighlighterConfig.java`(71)
- `common/.../highlighter/mixin/`：`GuiMixin`(35)、`InventoryScreenMixin`(30)、`AbstractContainerMenuMixin`(23)
- 三平台各一份同名 `mixin/AbstractContainerScreenMixin`（forge 36 / fabric 36 / neoforge 35）
- 平台入口：`fabric/HighlighterFabric`(14)、`forge/HighlighterForge`(16)、`forge/client/HighlighterForgeClient`(18)、`neoforge/client/HighlighterNeoForgeClient`(16)

最大的 5 个文件即上表前 5 项，无隐藏巨类。

## 3. 入口与注册

无 DeferredRegister、无任何游戏内容注册（纯客户端 UI mod）。统一入口是 `Highlighter.init()`，由各平台分别调用：

```java
// common/.../Highlighter.java:42-48
public static void init() {
    HighlighterConfig.register(HighlighterConfig.class, MODID);
    NewItemPickupEvent.EVENT.register(Highlighter::newItemPickup);
    ItemTooltipEvent.EVENT.register(Highlighter::onItemTooltip);
}
```

- Forge：`@Mod(Highlighter.MODID)` + `HighlighterForgeClient` 用 `@EventBusSubscriber(bus=Bus.MOD, value=Dist.CLIENT)` 在 `FMLConstructModEvent` 里 init（只有客户端加载）
- NeoForge：`@Mod(value = MODID, dist = Dist.CLIENT)` 构造器内 init
- Fabric：`ModInitializer#onInitialize` 直接 init
- 配置注册走 Iceberg：`HighlighterConfig extends IcebergConfig<HighlighterConfig>`，构造器接收 `IIcebergConfigSpecBuilder`，用 `build.comment(...).push("client").push("options").add("clear_on_close", true)` 这种 builder 链声明（`HighlighterConfig.java:37-48`）

## 4. 核心系统

**A. 新物品标记（唯一业务逻辑）** `common/.../Highlighter.java`
- 状态只是一个 `Set<Integer> markedSlots`（Highlighter.java:40），用 `player.getInventory().getSlotWithRemainingSpace(item)` 预测拾取落点，否则 `getFreeSlot()`，把该 slot 索引标记为"新"（:61-78）
- 三个清除时机分别由配置开关控制：关背包 `clearOnInventoryClose`、悬停 tooltip `clearOnHover`、切快捷栏 `clearOnSelect`
- 渲染用 `Util.getMillis() % 2000` 驱动上下弹跳 + `Easing.Ease(0,1,t)`，纹理当图标（`NEW_ITEM_MARKS` 8x8，按 `iconPosition` 枚举四角对齐，:154-200）

**B. 颜色缓存与失效** `config/HighlighterConfig.java:52-70`
- `Map<Pair<Item, DataComponentMap>, TextColor> colorCache`：以物品 + 数据组件快照（`new PatchedDataComponentMap(itemStack.getComponents())`）为键缓存物品名颜色，避免每帧查组件
- 重写 `onReload()` 时 `colorCache.clear()`，配置变更即失效

**C. 渲染 hook 分平台下沉**
- common 只放与加载器无关的注入（`Gui#renderSlot` 快捷栏、`AbstractContainerMenu#doClick`、`InventoryScreen#onClose`）
- `AbstractContainerScreen#renderSlot` 因各平台映射/混淆差异，在 fabric/forge/neoforge 各写一份；Forge 那份显式 `remap = false`（`forge/.../mixin/AbstractContainerScreenMixin.java:26`）
- 用 accesswidener 打开 `AbstractContainerScreen.hoveredSlot`（`common/src/main/resources/highlighter.accesswidener`，仅 1 行），而不是加 mixin accessor

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**
- 数据驱动：无（无 recipe/loot/JSON 定义），只有一张 16x16 图标贴图
- 配置：Iceberg 的 Forge-Config-like 客户端配置，输出到 `config/highlighter-client.toml`（路径由 Iceberg 决定，未在本仓库确认）；枚举型选项用 `build.addEnum("icon_position", IconPosition.UpperLeft)`
- datagen：**无**

## 6. Mixin

配置：`common/src/main/resources/highlighter.mixins.json`（`com.anthonyhilyard.highlighter.mixin`，client: AbstractContainerMenuMixin / InventoryScreenMixin / GuiMixin），三平台各一份 `highlighter.<platform>.mixins.json`；Forge 在 `forge/build.gradle:6-11` 通过 `loom { forge { mixinConfig ... } }` 显式登记。

代表性 hook：
- `GuiMixin#renderSlot`：`@Inject(method="renderSlot", at=@At(INVOKE, target="GuiGraphics;renderItemDecorations(Font,ItemStack,II)V", shift=AFTER))`，用 `player.getInventory().items.indexOf(item)` 反查索引（GuiMixin.java:20-35）
- `AbstractContainerMenuMixin#doClick`：`@At("HEAD")`，仅当 `this instanceof InventoryMenu` 时清除标记
- `InventoryScreenMixin`：覆盖 `onClose()` 调 `inventoryClosed()`，并 `@Shadow protected void renderBg(...)`

## 7. 值得学的 5 条具体做法

1. **业务逻辑零加载器依赖**：`Highlighter.java` 只用 MC + Iceberg API，平台模块只做 "谁在什么时候调 init"，新平台接入成本≈10 行 —— `common/.../Highlighter.java:42`
2. **用事件代替 mixin**：物品拾取/悬停这类有官方扩展点的功能走 Iceberg 事件总线，只有渲染与容器点击才 mixin —— `Highlighter.java:46-47`
3. **平台差异下沉策略**：common 放共用 mixin，签名/映射有差异的（AbstractContainerScreen#renderSlot）每平台一份 —— `fabric|forge|neoforge/.../mixin/AbstractContainerScreenMixin.java`
4. **accesswidener 只有 1 行**：只放开必需的 `hoveredSlot`，其余一律不动 —— `common/src/main/resources/highlighter.accesswidener`
5. **配置驱动的缓存失效**：重写 `onReload()` 清缓存而非每帧重算；缓存键用 `Pair<Item, DataComponentMap>` 覆盖 NBT/组件差异 —— `HighlighterConfig.java:54-69`

## 8. 公开 API

非库 mod，无对外 API 包。它对 Iceberg 的接入方式（`IcebergConfig` 子类 + `init()` 里 register 事件 + `mods.toml` 声明 `ordering=AFTER` 的硬依赖）可作为"附属 mod 接入前置"的参考模板。
