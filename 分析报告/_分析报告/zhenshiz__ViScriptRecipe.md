# ViScriptRecipe 源码分析报告

> 先说结论性纠偏：仓库名里的 "ViScript" 不是脚本语言。本仓库没有任何词法/语法分析器或脚本引擎——对 `src` 全量 grep `rhino|luaj|graal|nashorn|javax.script|ScriptEngine|antlr|lexer` 只命中 build.gradle:208 的 Rhino 依赖声明（见第 1 节），零处 Java import。
>
> 它是"可视化配方编辑器 + NBT 覆盖文件"路线：作者/整合包编辑者在游戏内 GUI 里改配方，序列化成 `.recipe`（NBT 二进制）文件，加载期编译成原版 `Recipe` 对象。本报告仍按"把可编辑内容做进 mod 要付多少代价"来拆，且它是 DSL 路线的**对照组**——第 8 节末尾给出对照结论。

## 1. 基本信息

- mod_id `viscript_recipe`、作者 zhenshiz、许可证 GNU LGPL 3.0、版本 1.0.8 beta：均见 `gradle.properties:14,19,16,17`。
- 目标平台：MC 1.21.1 / NeoForge 21.1.228（`gradle.properties:7,9`），Parchment 2024.11.17（`:12-13`）。Java 21（`build.gradle:119` toolchain；`viscript_recipe.mixins.json` compatibilityLevel=JAVA_21）。
- 工程结构：单模块，插件 `net.neoforged.moddev 2.0.82`（`build.gradle:5`）+ `io.freefair.lombok 8.6`（`:6`）+ `dev.vfyjxf.modaccessor 1.1`（`:7`，配合 `modAccessor{}` `:193-196` 在编译期包装配 AT）；dev 运行配置挂 mixin-hotswap-agent + `-XX:+AllowEnhancedClassRedefinition`（`:121-129,170-178`），纯开发期热更工具。
- 关键第三方依赖：
  - LDLib2 `com.lowdragmc.ldlib2:ldlib2-neoforge-1.21.1:2.2.33`（`build.gradle:201`，版本 `gradle.properties:22`）——GUI 框架、`@Persisted` syncdata 序列化、RPC 网络层全部来自它。
  - ViScriptLib `com.zhenshiz:ViScriptLib-neoforge-1.21.1:1.1.6.2`（`build.gradle:202-205`，implementation + jarJar 内置），flatDir 指向兄弟项目 `../viscript_lib/build/libs`（`:110-112`）——同作者编辑器基座，源码不在本仓库（内部行为未验证）。
  - Rhino `dev.latvian.mods:rhino:2101.2.7-build.81` 与 KubeJS `dev.latvian.mods:kubejs-neoforge:2101.7.2-build.368`（`build.gradle:208-209`，版本 `gradle.properties:25-26`）：**src 内无任何引用**（grep 验证），疑为模板残留依赖——这是本仓库"有脚本引擎坐标、无脚本引擎代码"的直接证据。
  - 17 个联动 mod 的 compileOnly/implementation 依赖（`:213-262`，含 Create、Mekanism、Iron's Spells 等），另有一个本地 jar `libs/Confluence-Magic-Lib-0.0.8.jar`（`:255`）。
- 依赖声明：`neoforge.mods.toml:30-31` ldlib2 required，`:37-134` 17 个 optional 联动 mod 条目。

## 2. 源码规模与包结构

实测（`find`+`wc -l`，非卡片转抄）：262 个 .java、39,699 行（卡片写 39,961，本次复核为 39,699，差 262 行——大概率卡片把 `build.gradle` 等一并计入或统计时点不同）。

| 包 | 文件数 | 行数 | 占比 |
|---|---|---|---|
| `com/viscript_recipe/gui`（全部在 `gui/editor`） | 53 | 23,592 | 59% |
| `com/viscript_recipe/data`（含 18 个子包） | 130 | 7,150 | 18% |
| `com/viscript_recipe/compat`（含 jei 子包） | 48 | 6,220 | 16% |
| `com/viscript_recipe/recipe`（含 importer/vanilla） | 14 | 1,443 | 3.6% |
| `com/viscript_recipe/network`（含 c2s/s2c） | 7 | 530 | 1.3% |
| `com/viscript_recipe/mixin` | 5 | 128 | 0.3% |
| `client` / `command` / 根（ViScriptRecipe+Config） | 2/1/2 | 264/241/131 | — |

最大 12 个源文件（行数实测）：

| 文件 | 行数 |
|---|---|
| `src/main/java/com/viscript_recipe/gui/editor/RecipeEditorController.java` | 7,121 |
| `src/main/java/com/viscript_recipe/gui/editor/CraftingWorkbenchView.java` | 4,356 |
| `src/main/java/com/viscript_recipe/gui/editor/MekanismCanvasFactory.java` | 1,046 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipePropertiesSections.java` | 1,027 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipePropertiesView.java` | 960 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipeDefaultDataInitializer.java` | 703 |
| `src/main/java/com/viscript_recipe/recipe/RecipeOverrideManager.java` | 578 |
| `src/main/java/com/viscript_recipe/gui/editor/CreateProcessingCanvasFactory.java` | 566 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipeNavigationView.java` | 548 |
| `src/main/java/com/viscript_recipe/gui/editor/IndustrialForegoingPropertiesSections.java` | 481 |
| `src/main/java/com/viscript_recipe/gui/editor/RecipeSearchComponents.java` | 472 |
| `src/main/java/com/viscript_recipe/compat/create/CreateRecipeFactory.java` | 398 |

单是前两个编辑器文件就占全仓 29% 的行数；真正"引擎"部分（recipe+network+mixin+client+command）合计不到 2,600 行——60% 的代码是编辑器 GUI，这就是"用 GUI 顶替 DSL"路线的真实账单。

资源为稀疏检出：`src/main/resources` 只有 `META-INF/accesstransformer.cfg`、`META-INF/neoforge.mods.toml`、`viscript_recipe.mixins.json`；README:334 引用的 `docs/compatibility-development.md` 不在工作区；仓库内 **无任何 `.recipe` 示例文件**（find 验证；该格式是用户在游戏里生成的 NBT 二进制，本就不适合入库）。

对卡片的复核修正两处：总行数应为 39,699（卡片 39,961）；"主类候选 `data/RecipeEntry.java`" 是误判，真正的 mod 入口是根包的 `ViScriptRecipe.java`（`@Mod` 注解在 `:24`），RecipeEntry 只是条目数据模型。

## 3. 入口与注册

入口 `com/viscript_recipe/ViScriptRecipe.java:29-42`，构造器签名直接吃 `(IEventBus, ModContainer, Dist)`，只做四件事（`:30-41`）：注册登录补同步事件、注册编辑器菜单类型、注册 COMMON 配置、客户端分支再注册客户端事件与配置界面扩展点（`if (dist.isClient())` 块，具体见下）：

```java
RecipeDeltaServerEvents.register();                       // 登录时补发增量同步基线
PlayerUIMenuType.register(RecipeEditor.WINDOW_ID, ignored -> player -> {
    if (player.level().isClientSide) return RecipeEditor.createUI();  // 编辑器只在客户端建树
    return new ModularUI(UI.empty());                     // 服务端侧是空壳 UI
});
modContainer.registerConfig(ModConfig.Type.COMMON, Config.CONFIG_SPEC, Config.CONFIG_FILE_NAME);
```

命令注册走 LDLib 注解：`command/ViScriptRecipeCommands.java:37` `@LDLRegister(registry = ICommand.COMMAND_ID, name = "recipe")`，由 ViScriptLib 的 `ICommand` 收集器挂进 `RegisterCommandsEvent`（收集器本体在 ViScriptLib 内，未验证）。配方类型注册表是**静态初始化驱动**：`data/RecipeEditorTypes.java:129-131` 的 static 块调 `RecipeCompatModules.registerEditorTypes()`（`compat/RecipeCompatModules.java:69-76`），逐个 `isModLoaded` 过滤后把 17 个联动 mod + 原版的类型塞进两个 LinkedHashMap（`:126-127`）。"脚本"（`.recipe` 文件）的加载入口不自主——搭原版重载的车：`mixin/RecipeManagerMixin.java:24-29` 在 `RecipeManager.apply` 的 TAIL 注入 `RecipeOverrideManager.apply(...)`，因此 `/reload`、进世界、datapack 增删之后都会自动重放覆盖；文件发现是 `recipe/RecipeFileLoader.java:20-31` 直接 `Files.walk` 磁盘目录 `LDLib2.getAssetsDir()/viscript_recipe/recipes`（`recipe/RecipeAssetPaths.java:14-16`，README:27），与原版 ResourcePack 体系完全无关。

## 4. 核心系统

### 4.1 文件格式与数据模型（对应问题①"脚本形态/编译产物/缓存"）

`.recipe` 是 **NBT 文件不是文本 DSL**：`RecipeFileLoader.java:39` 用 `NbtIo.read` 读，裸读失败回退 `NbtIo.readCompressed`（`:48-52`），保存用 `NbtIo.write`（`:63-69`）。没有词法、没有语法、没有 AST——"解析"就是把 CompoundTag 灌进数据类。

顶层模型 `data/RecipeFile.java:19-28`：`formatVersion=1`、`packId`、`recipeNamespace`（条目默认命名空间，`:30-32` 用 `ResourceLocation.tryBuild` 校验合法性）、`List<RecipeEntry>`。每条 `data/RecipeEntry.java:51-58` 四个 `@Persisted` 字段：`enabled`、`operation`(ADD/REPLACE/REMOVE)、`recipeId`、`type`，外加按 type 延迟实例化的 `IVSRecipeData` 载荷（`:77-81`），序列化时载荷以自己的 `getDataName()` 为 key 嵌入同一 CompoundTag（`:61-65`）；`copy()` 的实现是"序列化再反序列化"（`:185-190`），保证深拷贝跟格式定义永远一致。

(反)序列化没有一行手写 NBT 读写——全靠 LDLib syncdata 的 `@Persisted` 注解反射 + `ISkipDefaultedSerialize`（`data/IVSRecipeData.java:13,35-40`，来自 ViScriptLib）跳过默认值压缩体积。类型系统"有没有"的答案是：有，但是静态手写类型——`type` 字段经 `RecipeEditorTypes.require()` 查表得到 dataClass（`RecipeEntry.java:73-75`），未知 type 直接抛 `IllegalArgumentException`（`RecipeEditorTypes.java:168-170`），没有任何类型推导或动态成员。

"编译产物"是原版 `Recipe<?>` 对象：`RecipeEntry.java:170` `compile()` 委托给数据类的 `compile(typeId)`，例如 `data/vanilla/ShapedCraftingRecipeData.java:43-61` 把 pattern/key 编成 `ShapedRecipePattern` 再 new 一个 `ShapedRecipe`（带容器返还规则时改 new 本 mod 的 `recipe/vanilla/ViscriptShapedRecipe.java:14`，仅覆写 `getRemainingItems` `:23-32`）。**无缓存、无失效策略**：每次 apply/reload 全量重扫目录、重解析、重编译（`RecipeOverrideManager.java:165`），代价是 O(文件数) 磁盘 IO，换来的是零失效逻辑。

### 4.2 类型注册表与宿主绑定（对应问题②）

不存在"脚本里调用游戏对象 API"这回事，宿主绑定对象是**编辑器 UI 与文件 schema**，机制是手写 wrapper 而非注解扫描或 method handle：`data/RecipeEditorType.java:9-14` 一个 record `{id, category, translationKey, dataClass, dataSupplier, requiredMods...}`，`:21-26` `isAvailable()` 按 requiredMods 决定是否出现在编辑器里。引用注册表条目（物品/流体/标签/附魔/实体）在数据层就是存 `ResourceLocation`/`ItemStack` 字段（如 `data/RecipeIngredient.java:34-38` 的 ITEM/TAG/ITEM_ABILITY 三态），`compile()` 时才查 `BuiltInRegistries` 并验证（`:68-90`：未知物品标签直接抛 `IllegalArgumentException` `:84`，带数据组件的物品降级成 `DataComponentIngredient` `:76`）。属性面板由 LDLib `IConfigurable` 接口从同一批 `@Persisted` 字段自动生成（`RecipeEntry.java:48` `implements IConfigurable`），一份模型同时服务"文件持久化 + 配置 UI + 校验"，这是全仓库最核心的省力设计。

反向绑定（游戏对象 → 文件条目）由导入器承担，这是"手写 wrapper"成本的另一半：`recipe/importer/RecipeImporter.java:54,103-105` 把原版 handler 加 17 个联动 handler 排成链，逐个 `canImport(RecipeHolder)` 试探（原版判定即 `:29-38` 的 instanceof 开关）；遇到无法无损表达的自定义 Ingredient 明确抛 `RecipeImportException` 而非静默降级（如符号耗尽 `:243-246`）。编辑器打开时服务端还要把物品/流体/结构标签注册表快照推给客户端供搜索补全（`command/ViScriptRecipeCommands.java:68-77` → `network/RecipeRegistrySnapshot.java:25`、`network/StructureTagSnapshot.java:31`）。

### 4.3 应用管线与回滚（配方注册时机）

`recipe/RecipeOverrideManager.java:156-255` `applyOverrides`：先把 RecipeManager 当前配方快照成 `baseRecipes`（`:44-48` 首建、`:57-59` reload 复用——所以 `/reload` 叠加在"上次 vanilla 结果"上而不会被自己的旧覆盖污染），然后在**新 LinkedHashMap 副本**上逐条目应用（`:167` 拷贝 base，showcase 模式从空表起步 `:166`），全部完成后一次性 `recipeManager.replaceRecipes(recipes.values())`（`:212`）——构建期失败不会留下半套状态，这就是它的"回滚"。

操作语义（三种 operation 都不是硬失败）：`ADD` 撞已有 ID → 警告后替换（`:472-474`）；`REPLACE` 找不到目标 → 警告后当新增（`:475-477`）；`REMOVE` 目标不存在 → SKIPPED + 日志（`:448-453`）；编译产物为空也算 FAILED 而不是崩（`:467-470`）。条目级容错：`applyEntry` 的 try/catch（`:383-386`）把单条目异常记为 FAILED 计数并继续，加载器级容错同理（`RecipeFileLoader.java:57-60` 单文件解析失败返回 null 被过滤）。

状态挂在 `WeakHashMap<RecipeManager, ManagerState>`（`:31`）上随服务端重载自然失效，`revision` 自增（`:219`）供客户端对账。Create 的二级配方缓存单独打洞失效（`:213,257-261`）。特例：Iron's Spells 奥术铁砧配方**不进 RecipeManager**（原版菜单不走 RecipeManager 查询），改由 `IronArcaneAnvilOverrideManager.compile` 收集（`:389-406`）+ `@Pseudo` mixin 在 `ArcaneAnvilMenu.createResult` HEAD 拦截（`mixin/IronArcaneAnvilMenuMixin.java:15-31`）——"目标 mod 不在场也合法"的 Pseudo 用法。Create `block_cutting` 一个条目按输出数派生多个配方 ID（`:485-493,515-520` `_output_N` 后缀），删除时按同样规则展开（`:503-513`）。

### 4.4 编辑器 GUI 与"服务端开客户端界面"

编辑器是纯客户端 LDLib `EditorWindow`，项目格式注册在 `gui/editor/RecipeProjectType.java:18-22`：`EditorFileFormat(MOD_ID, "recipes", ".recipe")`，load/save 即 `NbtIo.read`/`NbtIo.write` 套 RecipeFile（`:29-52`），脏检查的判定是"当前内存序列化 NBT 与磁盘 NBT 是否相等"（`:54-67`）——格式规范到不需要专门 diff 逻辑。跨端玩法：`/viscript_recipe editor` 在服务端执行，但服务端菜单是空壳（`ViScriptRecipe.java:31-36`），真实 UI 在客户端由 RPC 唤起（`command/ViScriptRecipeCommands.java:68-80`：先推结构标签/注册表快照，再 `PlayerUIMenuType.openUI`）；文件名补全在客户端扫本地目录（`:121-128`），单机时编辑的就是本机文件，联机时改完走上传（见第 5 节）。单人/局域网/专用服务器同一套代码，靠的是 LDLib RPC 而非自写 payload。

### 4.5 运行时求值时机（对应问题⑤）

全部求值发生在**加载期**：mixin TAIL（datapack reload）或命令 reload 时解析+compile+replaceRecipes；此后游戏内匹配/取产物走原版 `RecipeManager` 与原版 `Recipe.matches`，本 mod 在每次合成时零开销（唯一每合成执行的自定义代码是 `ViscriptShapedRecipe.getRemainingItems`，纯 Java 查表）。这正是数据文件路线相对 DSL 的本质优势：没有"判定热路径上跑脚本"这回事。

沙箱问题的答案随之坍缩（对应问题③）：格式承载纯数据（NBT tag），不存在 IO/反射/死循环能力，无需沙箱设计；剩余攻击面只有文件路径与体积——上传路径经 `EditorAssetFiles.resolveRuntimeFile` 校验（`command/ViScriptRecipeCommands.java:91-95`），解析体积用 `NbtAccounter.unlimitedHeap()` 显式放开（`RecipeFileLoader.java:49`，即"信任本机/管理员文件"的取舍，入口命令已 `requires(hasPermission(4))` 把关 `:43`）。错误回报走双通道：详情进日志（`RecipeOverrideManager.java:384`），摘要进聊天回执计数（`RecipeOverrideManager.java:202-207,230-238` 统计 → `command/ViScriptRecipeCommands.java:180-189` 发送），不会出现"一个条目写错整个包崩掉"。

### 4.6 跨端流转：增量同步与 JEI（对应问题③④的一部分）

三条同步路径（`recipe/RecipeReloadSyncService.java:19-69`）：full = 原版 `ClientboundUpdateRecipesPacket` + 配方书 + 基线 RPC（`:36,81`），顺手把 showcase 开关同步给 JEI 过滤层（`:82-86`）；delta = 服务器端把新旧两次"受管配方集合"做 NBT 级 diff（`RecipeOverrideManager.java:275-330`，比较方式是 encode 成 Tag 后 equals `:322-330`），装进 `RecipeDeltaSnapshot` record（`network/RecipeDeltaSnapshot.java:23-34`：`baseRevision/revision/baseline/showcaseOnly/removed/upserted/managedEditorTypes/recipeTypeHints/arcaneAnvilRecipes`）逐玩家 RPC 下发。

值得注意的实现选择：delta 里的配方载荷不写自定义协议，直接 `Recipe.CODEC` encode/decode（`RecipeDeltaSnapshot.java:71,106`）并带 `protocol=1` 版本闸（`:36,93`）——任何注册了合法 serializer 的 mod 配方自动获得增量传输能力，本 mod 无需为 17 个联动 mod 手写网络格式。

三层自动回退（`RecipeOverrideManager.java:97-111,528-542`）：编码抛异常→ENCODING_FAILED；showcase 模式开关变化→SHOWCASE_MODE；变化量超 256 条或超"32 且 1/5 配方总量"→TOO_MANY_CHANGES，全部退化为 full 同步并在命令回执里给翻译键原因。客户端对账：revision 不匹配就 C2S 请求全量（`client/RecipeDeltaClientState.java:112-120,180-186`）；登录后服务端补发基线（`recipe/RecipeDeltaServerEvents.java:18-28`）；原版配方包到达时 HIGHEST 优先级清状态（`client/RecipeDeltaClientEvents.java:19-23` + `RecipeDeltaClientState.java:67-78`）。JEI 侧用公开 runtime API 局部换页，专用展示对象或异常时退化为"只重载 JEI 不重传配方"，并有 256 隐藏页上限（`compat/jei/RecipeDeltaJeiSynchronizer.java:24,126`；入口 `compat/jei/ViScriptRecipeJeiPlugin.java:23-30` onRuntimeAvailable/Unavailable）。

## 5. 网络 / 数据驱动 / 配置 / datagen（对应问题④热重载）

- 存放：`ldlib2/assets/viscript_recipe/recipes/*.recipe`（`RecipeAssetPaths.java:15`），游戏内编辑器可把文件上传到服务器的这个目录（`gui/editor/RecipeEditor.java:98-124` → ViScriptLib `EditorServerUploads`，路径穿越防御在 `command/ViScriptRecipeCommands.java:91-95` 借 `EditorAssetFiles.resolveRuntimeFile` 抛 IAE 拦截；解析实现位于 ViScriptLib，内部细节未验证）。
- 重载触发四档（命令树 `ViScriptRecipeCommands.java:42-59`，全部 `requires(hasPermission(4))` `:43`）：
  - `/reload`：隐式，原版数据包重载经 mixin 自动重放覆盖；
  - `/viscript_recipe reload`：重读文件 + 全量配方包 + 配方书，不发标签包（`:175-191`）；
  - `/viscript_recipe reload delta`：只发变化配方 + JEI 局部刷新，条件不满足自动退 full（`:193-224`）；
  - `/viscript_recipe reload full`：在 reload 基础上补发 `ClientboundUpdateTagsPacket` 帮 JEI 感知标签变化（`syncTags=true` 传参链 `:178-179` → `RecipeReloadSyncService.java:37-39`）。
  - 另有 `/viscript_recipe status` 回显上次加载统计（`:226-240`）。
- 与 datapack 重载的顺序关系由 mixin TAIL 保证"永远最后覆盖"（`RecipeManagerMixin.java:24-27`，priority 900）。改脚本→生效：改文件 + 任一档 reload，无需重启。
- 配置：仅 1 项 `recipes.showcase_only_viscript_recipes`（`Config.java:21-24`）；关键点是不注册 FileWatch 而是**每次 reload 前手动从磁盘重读 config**（`Config.java:28-40`，调用点 `ViScriptRecipeCommands.java:177,195`），让"改配置开关 showcase 模式"搭 reload 的车。
- datagen：`build.gradle:165-168` 有 data run 配置，但 src 内无 `GatherDataEvent`/`DataProvider`（grep 零命中）——无 datagen，语言资源等靠手写在未检出的 resources 里。

## 6. Mixin

`src/main/resources/viscript_recipe.mixins.json`（package `com.viscript_recipe.mixin`，5 个条目全部服务端侧，client 列表为空）：
- `RecipeManagerMixin.java:24-29`：TAIL 注入 `RecipeManager.apply`，覆盖应用的总入口。
- `IronArcaneAnvilMenuMixin.java:16-31`：`@Pseudo` targets 铁魔法奥术铁砧菜单 `createResult` HEAD cancellable——配方不进 RecipeManager 的旁路。
- `IronAlchemistCauldronFluidHandlerMixin.java:12-13`：`@Pseudo` 放行炼金锅自定义流体。
- `MysticalAgricultureInfusionRecipeAccessor/AwakeningRecipeAccessor`：`@Pseudo`+`@Accessor` 读 MA 私有字段（`transferComponents` 等）供导入器无损回读。
另有 `META-INF/accesstransformer.cfg:1-4` 开 `SmithingTransformRecipe` 四个私有字段。`defaultRequire: 1`、`overwrites.requireAnnotations: true`（mixins.json），联动 mod 的注入点全部 `@Pseudo` 保证目标缺席不炸。

## 7. 值得学的 5 条

1. **副本构建 + 原子换表 + 基线快照**（`recipe/RecipeOverrideManager.java:167,212` 与 `:44-48,57-59`）：覆盖系统永远在 base 快照的副本上演算、一次 `replaceRecipes` 提交，天然获得"失败的覆盖不残留"与"`/reload` 幂等"，比 KubeJS 式边解析边改全局状态干净得多——任何"可重载内容包"都该抄这个事务结构。
2. **条目级容错 + 面向玩家的统计回执**（`RecipeOverrideManager.java:383-386` + `command/ViScriptRecipeCommands.java:175-191`）：单条目异常只进 failed 计数、日志留详情、命令回显"文件/条目/应用/跳过/失败/当前总数"，另有 `/status` 复查——"一个脚本写错整个包崩掉"在这条路线里结构性不存在，这套回执格式值得直接搬进求仙问道的内容加载器。
3. **带 revision 计数与三层回退的增量同步**（`RecipeOverrideManager.java:28-29,97-111` + `client/RecipeDeltaClientState.java:112-120`）：diff 超阈值/编码失败/模式切换自动退 full，客户端版本不匹配主动 C2S 要全量——增量优化的正确姿势是"增量失败必须无损降级到全量"，而不是让客户端自行猜测状态。
4. **一份 `@Persisted` 模型三用：文件格式、属性面板、校验**（`data/RecipeEntry.java:48-58`、`data/RecipeIngredient.java:68-90`）：schema 即数据类，新增一种可编辑内容只写数据类+compile()，UI 由 LDLib IConfigurable 反射生成——把"DSL 的解释器成本"换成"注解反射成本"，17 个联动 mod 的类型注册共用一张表（`compat/RecipeCompatModules.java:45-64`）就是这个模式的规模验证。
5. **编译产物直接复用原版对象，运行期零挂钩**（`data/vanilla/ShapedCraftingRecipeData.java:43-61`）：需要偏离原版行为时才 subclass（`ViscriptShapedRecipe.java:14,23-32` 只为改 getRemainingItems），subclass 仍以原版 `ShapedRecipeSerializer` 的输入域构造——下游 mod（JEI/配方书/其他 mod 的配方查询）看到的都是正品 Recipe，兼容性免费。

## 8. 公开 API（面向"脚本作者"= 内容作者与联动作者）

- 文件契约：NBT `RecipeFile{formatVersion,packId,recipeNamespace,entries[]}`，条目 `{enabled,operation,recipeId,type,<dataName载荷>}`（`data/RecipeFile.java:19-28`、`data/RecipeEntry.java:51-58`）；type 取值即 README:119-315 的联动类型表（`ars_nouveau:imbuement`、`mekanism:crushing` 等）。仓库内**无最小可运行示例**：`.recipe` 是二进制且由编辑器 GUI 产出（README:328 明确"不是原版 JSON 数据包文件"），稀疏检出也排除了所有非代码资源——语法示例缺失是事实而非偷懒，文本层面无法"原样引用"。
- 命令面：`/viscript_recipe editor [file] | reload [delta|full] | status`（`command/ViScriptRecipeCommands.java:42-59`，权限 4）。
- 扩展点（给联动 mod 作者）：实现 `data/IVSRecipeData`（契约只有一个 `compile(ResourceLocation)`，`data/IVSRecipeData.java:32`）+ 注册 `RecipeEditorType` record（`data/RecipeEditorType.java:9-19`）+ 可选导入器 `recipe/importer/RecipeImportHandler`（`RecipeCompatModules.java:78-84` 聚合）；对第三方 mod 的注入用 `@Pseudo` mixin（第 6 节）。
- 与 ViScriptShop 的关系：两者共享的不是脚本引擎而是 **ViScriptLib 基座**，包名 `com.viscript_lib`——本仓库 15 个文件引用其 `gui.editor.{FunctionFileEditor,FunctionFileProjectType,EditorAssetFiles,EditorServerUploads}`、`register.ICommand`、`util.ISkipDefaultedSerialize`（import 实测），ViScriptShop 卡片（mod_id viscript_shop）同样是 LDLib+GUI 路线。引擎不存在，"哪个包"的答案是：内容框架在 `com.viscript_lib`（jarJar 内置，`build.gradle:205`），其内部源码未检出、未验证。
- 必答问题⑥——若要把类似"功法/阵图可脚本化"引入求仙问道：本仓库给出的是**非 DSL 最小可行方案**：schema 数据类（@Persisted 或 Codec）→ 加载期 compile 成正版游戏对象 → 副本+原子换表 + mixin TAIL 保证在 datapack 之后应用 → `/x reload` + 条目级容错回执；NeoForge 1.21.1 上这套几乎不改结构就能用（RecipeManager.replaceRecipes 在 NeoForge 仍在）。三笔必须付的代价（都对应本仓库真实支出）：其一，schema 膨胀税——17 个 mod 的联动写了 48 个 compat 文件（工厂/导入器/UI 支持）+ 130 个 data 类（第 2 节计数），每加一种可编辑内容都要新数据类+校验分支，DSL 用通用语法把这个成本摊给语言，这里全摊给 Java；其二，"表达力不够就只能改代码"——容器返还规则这种小差异也要专门 subclass `ViscriptShapedRecipe` 并处理镜像 pattern（`:34-61`），DSL 里这是一行函数；其三，同步工程量的大头不在解析在分发——本仓库 recipe 核心才 1.4k 行，但为了改完不卡（delta/revision/JEI 局部刷新/三层回退）网络+client 又花了约 800 行外加同步语义文档（README:72-97 整节）。与 NeoMTR 路线（深挖待办 #7）一句对照：NeoMTR 嵌 Rhino 换来运行期每次渲染都能求值动态内容、代价是热路径 interpreter 开销与沙箱设计，ViScriptRecipe 则是把求值全部押到加载期、用编辑器 GUI 顶替语言表达力——功法/阵图若判定发生在热路径（战斗每 tick 查条件）更接近 NeoMTR 的问题域，若是构建期展开（阵图布局、功法表）本仓库的事务加载器就是更好的模板。
