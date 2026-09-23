# cakeGit/Create-Ez-Stock-Ticker 源码分析报告

## 1. 基本信息

- **Mod 名 / mod_id**：Create: Ez Stock Ticker / `create_ez_stock_ticker`（`gradle.properties:26,28`）
- **作者**：Cake
- **目标 MC / 加载器**：Minecraft 1.21.1 + NeoForge `21.1.219`（`gradle.properties:15,19`），Java 21
- **Gradle 插件**：`net.neoforged.moddev` 2.0.141（ModDevGradle，非 ForgeGradle）+ `java-library`、`maven-publish`、`me.modmuss50.mod-publish-plugin` 1.1.0（`build.gradle:1-7`）
- **许可证**：MIT
- **编译依赖**（`build.gradle:137-151`）：
  - `com.simibubi.create:create-1.21.1:6.0.10-+`（`:slim`，`transitive = false`）—— 核心目标 mod
  - `net.createmod.ponder:ponder-neoforge:1.0.82+mc1.21.1`
  - `dev.engine-room.flywheel:flywheel-neoforge-api-1.21.1:1.0.6`（compileOnly + runtimeOnly 分离）
  - `com.tterrag.registrate:Registrate:MC1.21-1.3.0+67`
  - `io.github.llamalad7:mixinextras-neoforge:0.5.4`（经 `jarJar` 内嵌）
  - JEI 19.27.0.340：`compileOnly` + `localRuntime`
  - 版本管理用 Parchment `2024.11.17` 映射（`build.gradle:36-39`）
- **元数据生成**：`src/main/templates/META-INF/neoforge.mods.toml` 通过自定义 `generateModMetadata` 任务做 `${}` 属性替换（`build.gradle:155-178`），并在其中声明 `[[mixins]] config="${mod_id}.mixins.json"`

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **9 个 java 文件，552 行**（`find ... -exec wc -l {} +`）。这是一个极小的"补丁型" mod，无独立注册系统。

包结构（`com.aztech.ez_stock_ticker` 下）：

| 包 | 文件数 | 内容 |
|---|---|---|
| `ez_stock_ticker`（根） | 3 | 主类、客户端入口、`ClientConfig` |
| `.foundation` | 1 | `StackSnapping`（111 行） |
| `.mixin` | 3 | 3 个 mixin 类 |
| `.accessor` | 2 | 纯接口 accessor（配合 mixin 使用） |

最大的文件：
- `mixin/StockKeeperRequestScreenMixin.java` 211 行
- `foundation/StackSnapping.java` 111 行
- `ClientConfig.java` 82 行
- `CreateEasyStockTicker.java` 56 行

资源仅 `src/main/resources/create_ez_stock_ticker.mixins.json` 一个文件（纹理由 `run-data`/生成目录提供，源码树中未列）。

## 3. 入口与注册

主类 `src/main/java/com/aztech/ez_stock_ticker/CreateEasyStockTicker.java:16-27`：

```java
@Mod(CreateEasyStockTicker.MOD_ID)
public class CreateEasyStockTicker {
    public static final String MOD_ID = "create_ez_stock_ticker";
    public static final ModContainer MOD_CONTAINER = ModList.get().getModContainerById(MOD_ID).orElseThrow();
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_CONTAINER.getModInfo().getDisplayName());

    public CreateEasyStockTicker(IEventBus eventBus, ModContainer modContainer) {
        attemptConfigMigration();
        modContainer.registerConfig(ModConfig.Type.CLIENT, ClientConfig.CONFIG_SPEC);
        eventBus.addListener(CreateEasyStockTickerClient::onClientSetup);
    }
}
```

**无 DeferredRegister / 无 Registrate 使用**——虽然依赖了 Registrate，但源码中没有任何注册调用。该 mod 完全通过 mixin 改行为，不新增任何游戏对象。客户端入口 `CreateEasyStockTickerClient.java:10-17` 在 `FMLClientSetupEvent` 中做两件事：注册 `IConfigScreenFactory` 扩展点（指向 NeoForge 的 `ConfigurationScreen`），以及 `StockKeeperRequestScreen.hasShiftDown()` 这一句"预热"调用——用一次无害调用强制 Clinit 加载目标类，避免 mixin 首次应用时出现类加载顺序问题（值得注意的小技巧）。

## 4. 核心系统

### 4.1 滚动吸附（StackSnapping）
`foundation/StackSnapping.java:8-100`。枚举 `NONE/SHIFT/CONTROL/SHIFT_CONTROL`，每个枚举常量持有一个 `Supplier<String> expressionSupplier`（惰性读配置，避免静态初始化时 config 尚未加载）。`get()` 用 `Screen.hasShiftDown()/hasControlDown()` 判定当前组合。表达式解析支持纯数字与 `stack*N` / `stack/N` 两种形式：`getSnappingIncrement` 用 `expression.charAt(5)` 取运算符、`Double.parseDouble(expression.substring(6))` 取因子，乘法用 `Math.ceil(stackSize * operand)`，除法 `Math.ceil(stackSize / operand)`，最后 `Math.max(1, snapping)` 夹紧防 0（`:72-100`）。工厂物流的流体 stackSize 会先 `stackSize <= 0 → 1`（`:73`）。

### 4.2 Mixin 注入定位（不用 @Redirect，用 FIELD 定位）
`mixin/StockKeeperRequestScreenMixin.java` 全部注入都用 `@At(value = "FIELD", target = "...BigItemStack;count:I")` 配合 `ordinal` 与 `shift = At.Shift.AFTER/BY` 精确定位字节码中的赋值行，再用 MixinExtras 的 `@Local(name = "current")` / `LocalIntRef transfer` 取局部变量改写：

```java
@Inject(method = "mouseScrolled",
    at = @At(value = "FIELD", target = "Lcom/simibubi/create/content/logistics/BigItemStack;count:I",
             ordinal = 1, shift = At.Shift.BY, by = -2))
```
`by = -2` 表示"在该字段写入指令之前 2 条指令处"插入（`:95-104`），`by = -5` 用于另一处（`:136-144`）。这种做法避免使用 `@Redirect` 而引发与其他 mod 的注入冲突（`@Redirect` 是互斥的），是对 Create 生态常见写法的改进。

### 4.3 阻止栈被滚没
`preventStackDeletion` 逻辑（`:115-132`）：仅在 `orderClicked || recipeClicked` 时生效，把目标值夹到 `Math.max(1, target)`；未开启吸附时单独判断 `if (target < 1) transfer.set(current - 1)`。

### 4.4 GUI 内嵌配置入口
`:198-210` 的 `@Unique` 方法 `create_Ez_Stock_Ticker$getEzLocation()` 用 `HEADER.getHeight() + FOOTER.getHeight()` 加上循环累加 `BODY.getHeight()` 算出贴图右下角坐标（`x+13, y-13`），把 16x7 的补丁贴图 `textures/gui/stock_keeper_patch.png` 画在 GUI 上，左键点击即 `Minecraft.getInstance().setScreen(new ConfigurationScreen(MOD_CONTAINER, this))`（`:165-175`）——即"从 Create GUI 直接进入 NeoForge 配置页"的玩家友好入口。

### 4.5 Accessor 双件套（mixin + 纯接口）
`accessor/StockTickerBlockEntityAccess.java` 声明 `List<ItemStack> getCategories()`，`mixin/StockTickerBlockEntityMixin.java:11-20` 用 `@Shadow protected List<ItemStack> categories;` 实现它（读取 Create 受保护字段 `categories`）。`accessor/StockKeeperRequestScreen$CategoryEntryAccess.java` 同理暴露内部类 `StockKeeperRequestScreen.CategoryEntry` 的 `y` / `targetBECategory` / `hidden`（`StockKeeperRequestScreen$CategoryEntryMixin.java:11-30`）。注意全部 mixin 均标注 `remap = false`（Create 是无关映射的第三方类）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络 / 数据驱动**：无。无 packet、无 datapack 内容。
- **配置**：`ClientConfig.java:13-20` 用静态块 + `ModConfigSpec.Builder().configure(ClientConfig::new)` 的双例（`Pair<ClientConfig, ModConfigSpec>`）写法，注册为 `ModConfig.Type.CLIENT`。9 个配置项全部带 `translation(...)` 键与 `comment(...)`。4 个 snapping 表达式项使用自定义校验器 `.define("...", "1", value -> StackSnapping.isValidExpression((String) value))`（`:64,69,74,79`），在配置加载/编辑期就拒绝非法表达式。
- **配置迁移**：`CreateEasyStockTicker.java:33-54` 有 `@Deprecated(forRemoval = true)` 的 `attemptConfigMigration()`：旧版单个 `ez_stock_ticker_enabled` 开关若为 false，则用 `CommentedFileConfig`（nightconfig）把 4 个新子开关全部写成 false 再 `save()`。变量名把 `config` 放在 try-with-resources 里（`:38`），保证资源释放。
- **datagen**：build.gradle 配置了 `data` run 与 `src/generated/resources`（`build.gradle:68-76,105`），但源码中无任何 `DataGenerator` 实现，实际未使用。

## 6. Mixin

配置：`src/main/resources/create_ez_stock_ticker.mixins.json`
- `"required": true`、`"compatibilityLevel": "JAVA_21"`、`"injectors.defaultRequire": 1`（任一注入失败即崩溃，属于强绑定策略）
- `mixins`（通用）：`StockTickerBlockEntityMixin`
- `client`：`StockKeeperRequestScreenMixin`、`StockKeeperRequestScreen$CategoryEntryMixin`

代表 hook：

| Mixin 类 | 目标 | 注入点 |
|---|---|---|
| `StockKeeperRequestScreenMixin.java:64` | `StockKeeperRequestScreen#init` | `@At("TAIL")` → 自动聚焦搜索框 |
| 同上 `:71-80` | `mouseClicked` | FIELD `BigItemStack.count` `ordinal=0` PUTFIELD 后 → 右键减半 |
| 同上 `:95-104` | `mouseScrolled` | FIELD `count` `ordinal=1`，`shift=BY, by=-2` → 减量吸附 |
| 同上 `:136-144` | `mouseScrolled` | FIELD `StockKeeperRequestScreen.blockEntity`，`shift=BY, by=-5` → 增量吸附 |
| 同上 `:165-175` | `mouseClicked` | `@At("HEAD") cancellable` → GUI 左上角配置按钮命中检测 |
| 同上 `:177-181` | `renderBg` | `INVOKE AllGuiTextures.render` `ordinal=2` 后 → 画按钮贴图 |
| 同上 `:183-196` | `renderForeground` | `@At("TAIL")` → 按钮 tooltip |
| `StockTickerBlockEntityMixin` | `StockTickerBlockEntity` | 仅 `@Shadow` 字段，无注入 |
| `...$CategoryEntryMixin` | `StockKeeperRequestScreen$CategoryEntry` | 仅 `@Shadow` 字段，无注入 |

## 7. 值得学的 5 条具体做法

1. **用 `@Local(name=...)` + MixinExtras 代替 `@Redirect` 改写行为**：`StockKeeperRequestScreenMixin.java:81-93`。`@Redirect` 对同一调用点互斥，多个 mod 想改 Create 的同一行会互相踢掉；`@Inject` + `@Local` 可叠加。适用：Create 附属修改 GUI/容器逻辑时。
2. **`@At(value="FIELD", ordinal=N, shift=At.Shift.BY, by=±k)` 精确绕过无源码行号问题**：`StockKeeperRequestScreenMixin.java:95-104`。当目标方法被混淆/顺序变化时，字段序号 + 字节码偏移比 `INVOKE ordinal` 更细粒度可控。
3. **配置项自定义校验器** `.define(key, default, validator)`：`ClientConfig.java:64`。让非法输入在配置屏就报错，而不是在游戏逻辑里抛异常；配合 `StackSnapping.isValidExpression`（`StackSnapping.java:102-109`）做一次静默试运行来验证。
4. **枚举 + `Supplier<String>` 惰性读配置**：`StackSnapping.java:8-22`。枚举常量在类初始化时求值，直接读 `CONFIG.x.get()` 会在配置未加载时拿到空值；存 Supplier 可延迟到调用时取值。适用：任何"枚举映射配置项"的场景。
5. **客户端 setup 里对目标类做一次无害调用以强制加载**：`CreateEasyStockTickerClient.java:12` `StockKeeperRequestScreen.hasShiftDown();`。提前触发目标类的 clinit，规避 mixin 首次应用时的类初始化时序告警。适用：mixin 目标类有复杂静态初始化时。

（补充：`build.gradle:206-258` 的 `publishMods` 从 `.env` 读 token、从 `changelog.yml` 按 `minecraft_version-mod_version` 键自动取 changelog 的发布流水线，也值得直接照搬。）

## 8. 公开 API

非库模组，无对外 API 包。唯一的"扩展点"是向 NeoForge 注册 `IConfigScreenFactory`（`CreateEasyStockTickerClient.java:14-16`），使其他入口（如本 mod 自己在 Create GUI 上的按钮，以及 ModList 配置按钮）都能打开同一配置屏。
