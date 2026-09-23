# Towdium/JustEnoughCharacters（拼音搜索）源码分析

> 说明：本地 `_bulk` 检出的是 `1.18` 分支（`git log -1` = `36a9d7f` "Merge remote-tracking branch 'JechOfficial/1.18'"，2023-07-01），**不是** 1.20+ 的 multiloader 版本。工作树缺失部分非 Java 文件（`generate.py`、`scripts/*.js`），已用 `git show HEAD:<path>` 从 git 对象读取。

## 1. 基本信息

- Mod 名 / mod_id：Just Enough Characters / `jecharacters`（`src/main/resources/META-INF/mods.toml`）
- 作者：Towdium, yzl210, Death-123；许可证 MIT（mods.toml `license=`）
- 目标 MC / 加载器：`gradle.properties`: `mc_version=1.18.2`、`forge_version=1.18.2-40.1.0`、`loom.platform=forge`，**Architectury Loom**（`dev.architectury.loom 1.1-SNAPSHOT`）+ Mojang mappings + parchment-1.19.2；Java 17
- 版本号：`${mc_version}-${verspec}.${verbuild}` = 1.18.2-4.3.12
- 核心依赖：`com.github.towdium:PinIn:1.6.0`（JitPack，作者自己的拼音匹配库，经 `include(...)` 打进 jar、同时 `forgeRuntimeLibrary` 暴露给 coremod）；`modImplementation mezz.jei:jei-1.18.2-forge:10.2.1.1002`（JEI 只在开发期用于编译，运行时不强依赖）
- MIT/AGPL 提示：`processResources` 只展开 mods.toml 里的 `${version}`

## 2. 源码规模与包结构

**6 个 `.java` 文件、768 行**（`find . -name '*.java' -exec wc -l {} +`）——本项目把"重活"外移了，Java 侧极薄：

| 包 | 文件 | 行数 |
|---|---|---|
| `me.towdium.jecharacters` | `JustEnoughCharacters`(57)、`JechConfig`(93)、`JechCommand`(148) | 298 |
| `me.towdium.jecharacters.utils` | `Profiler`(258)、`Match`(174)、`Greetings`(38) | 470 |

另有**生成物/脚本资源**：`src/main/resources/me/towdium/jecharacters/scripts/` 下 `_lib.js`(4 KB)、`jei1.js`/`jei2.js`/`jei3.js`/`psi.js`（1.5~1.8 KB），构建时由 `generate.py`(24 KB) 生成 `_gen*.js` 与 `META-INF/coremods.json`。最大文件是 `Profiler.java`（258 行）。

## 3. 入口与注册

主类 `JustEnoughCharacters.java:25-33`：`@Mod("jecharacters")` + `@Mod.EventBusSubscriber(bus = MOD)`，构造器只做 `JechConfig.register()`。没有方块/物品/实体注册，没有 DeferredRegister。

最关键的"注册"是 **coremod 的动态生成**：`build.gradle` 里 `task generate(type: Exec) { commandLine 'python', 'generate.py' }` 且 `compileJava.dependsOn generate`。`generate.py` 维护四张"目标表"——`contains`（约 100 条，几乎覆盖所有知名物流/手册/键位 mod）、`suffix`（原版搜索树）、`regExp`、`equals`——每条形如 `fully.qualified.Class:methodName(desc)`：

```python
pattern = """// Generated
function initializeCoreMod() {{
    Java.type('net.minecraftforge.coremod.api.ASMAPI').loadFile('me/towdium/jecharacters/scripts/_lib.js');
    return {{ 'jecharacters-gen{idx}': {{ 'target': {{ 'type': 'METHOD', 'class': '{clazz}',
        'methodName': Api.mapMethod('{name}'), 'methodDesc': '{desc}' }},
        'transformer': trans{op} }} }} }} }}"""
```

脚本为每条目标输出一个 `_gen<N>.js` 并汇总成 `coremods.json`；手动维护的 4 个脚本（`jei1/2/3.js`、`psi.js`）用于需要特殊处理的场景。

## 4. 核心系统

**① ASM 层"调用点替换"是全部魔法所在（`src/main/resources/me/towdium/jecharacters/scripts/_lib.js`）**
只提供 4 个 JS 变换函数，对应 4 类搜索实现：
- `transInvoke(method, srcOwner, srcName, srcDesc, dstOwner, dstName, dstDesc)`：遍历 `method.instructions`，命中 `MethodInsnNode` 时把 `INVOKEVIRTUAL/INVOKESPECIAL/INVOKESTATIC` 一律改成 `Ops.INVOKESTATIC` 并改 owner/name/desc；同一函数还处理 `InvokeDynamicInsnNode`（lambda/方法引用）的 `bsmArgs[1]` 句柄。
- `transInvokeLambda(...)`：只改 `bsmArgs[1]` 的 `Handle`（保留 `h.tag`），用于 `<clinit>` 里以方法引用构造搜索树的情况。
- `transConstruct(method, src, dst)`：把 `NEW`/`INVOKESPECIAL` 的 `desc`/`owner` 从原版类改成替身类（如 `net/minecraft/client/searchtree/SuffixArray` → `Match$FakeArray`）。
- `transContains` 把 `String.contains(CharSequence)` 与 `kotlin/text/StringsKt.contains(...)`（含 3 参和 2 参两个重载）换成 `Match.contains`；`transEquals`、`transRegExp`（`String.matches` + `Pattern.matcher`）同理。

**② `Match`：PinIn 适配层（`Match.java:30-152`）**
`static final PinIn context = new PinIn(new Loader()).config().accelerate(true).commit();` 全局单例。对外只暴露几个静态方法：`contains(String, CharSequence)`、`contains(CharSequence, CharSequence, boolean lower)`、`equals(String, Object)`、`matcher(Pattern, CharSequence)`（把正则匹配"降级"为拼音包含匹配，返回 `p.matcher("a")` / `p.matcher("")` 作为真假 Matcher）。`matches()` 特殊处理 `.*xxx.*` 形式：剥掉首尾 `.*` 再交给 `contains`，且当 `start && end && s2.length() < 4` 时忽略结尾（避免短词全变模糊）。
内嵌两个**搜索树替身**：`Match.FakeTree<T> extends GeneralizedSuffixTree<T>`（覆写 `getSearchResults/put/getAllElements`，让 JEI 的旧搜索树直接落到 PinIn 的 `TreeSearcher`）与 `Match.FakeArray<T> extends SuffixArray<T>`（覆写 `add/search`，`generate()` 空实现）。所有替身都被 `Collections.newSetFromMap(new WeakHashMap<>())` 弱引用登记，配置变化时统一 `refresh()`。
`Loader extends DictLoader.Default` 额外 `feed` 了 14 个 CJK 扩展区生僻字（如 `'\uE900' → "lu2"` 钅卢），用于修补 PinIn 数据缺字。

**③ `JechConfig` 配置 + 热重载（`JechConfig.java`）**
纯 `ForgeConfigSpec` 手写（无自动化 builder），`push("General")` / `push("Utilities")`。键位是一个枚举 `Spell`（QUANPIN/DAQIAN/XIAOHE/ZIRANMA/SOUGOU/GUOBIAO/MICROSOFT/PINYINPP/ZIGUANG），每个枚举持有 PinIn 的 `Keyboard` 对象。模糊音 8 个开关（`enableFZh2z`、`enableFSh2s`、`enableFCh2c`、`enableFAng2an`、`enableFIng2in`、`enableFEng2en`、`enableFU2v`）直接映射到 PinIn 的 `.fZh2Z()/.fSh2S()/...`。`Match.onConfigChange()` 把配置推给 `context.config()` 后 `searchers.forEach(TreeSearcher::refresh)`（`Match.java:96-103`），并由 `ModConfigEvent` 订阅触发。

**④ `/jech` 客户端命令（`JechCommand.java`）**
绕过 Forge 命令注册：自己 new 一个 `CommandDispatcher<SharedSuggestionProvider>` 并在 `ScreenEvent.InitScreenEvent`（打开 `ChatScreen`）时把 `builder.build()` 挂到 `player.connection.getCommands().getRoot()` 的 `jech` 子节点（`JechCommand.java:100-106`），再用 `ClientChatEvent` 拦截 `/jech` 前缀、取消原版发送后自行 `dispatcher.execute(parse)`。子命令：`profile`、`verbose true/false`、`silent`、`keyboard <9 种拼法>`（切键盘时顺带 `enableQuote.set(false)`）。

**⑤ `Profiler`：自动考古工具（`Profiler.java`）**
这是"如何发现需要 patch 的调用点"的答案。`ANALYZERS` 常量表把 7 条字节码特征（`String.contains`、`StringsKt.contains` 两种、`String.equals`、`String.matches`、`Pattern.matcher`、构造函数 `new SuffixArray`）映射到 4 个分类 `Type`（CONTAINS/EQUALS/REGEXP/SUFFIX）。`run()` 扫 `new File("mods")` 下所有 jar，用 ASM `ClassNode` 逐类扫描，把命中的 `clazz.name + ":" + method.name + method.desc` 收进 `EnumMap<Type, Set<String>>`，结果按 mod 分组输出为 `Report{jars[].{mods[], contains[], regExp[], suffix[], equals[]}}`，`/jech profile` 在 **MIN_PRIORITY 线程**里跑并写成 `logs/jecharacters.txt`（`JechCommand.java:82-98`）。也就是说：生成脚本里的目标表是"扫全量 mods 用工具算出来的"，而不是手抄的。

**⑥ `Greetings`：多 mod 共存协调（`Greetings.java:18-37`）**
`MODS = {"jecharacters","jecalculation"}` 语义为"同系列 mod 只让 Master 打日志"，`FRIENDS` 表把 modid 映射到作者名（`kiwi→Snownee`、`i18nupdatemod/touhou_little_maid→TartaricAcid`），命中则 `logger.info("Good to see you, {}")`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端 mod，无包注册）。
- 数据驱动：无 datapack/json 数据；"数据"即 `coremods.json` + `_gen<N>.js` 这套构建期生成的 coremod 清单。
- 配置：`ForgeConfigSpec` COMMON 类型，文件名固定 `config/jecharacters.toml`（`FMLPaths.CONFIGDIR + JechConfig.PATH`，`JechConfig.java:72-75`）；无 GUI（README 明确说明 Forge 当时无官方 config GUI 支持），改配置靠文本或 `/jech`。
- datagen：无。
- 构建期代码生成：`generate.py` + `compileJava.dependsOn generate`（等价 datagen，但生成的是 coremod 脚本）。

## 6. Mixin / Coremod

**无 mixin**（无 mixins.json、无 `@Mixin`），用 **Forge Coremod（JS + Nashorn）**：

- 清单：`src/main/resources/META-INF/coremods.json`（构建时由 `generate.py` 写出），每项 `name → scripts/xxx.js`
- 通用库：`me/towdium/jecharacters/scripts/_lib.js`，由每个脚本首行 `ASMAPI.loadFile(...)` 引入，提供 `transInvoke/transInvokeLambda/transConstruct/transContains/transSuffix/transRegExp/transEquals`
- 代表目标（`generate.py` 表内条目，格式 `类:方法名(描述符)`）：`net.minecraft.client.gui.screens.inventory.CreativeModeInventoryScreen:m_98630_()V`（原版创造模式搜索）、`mezz.jei.common.search.ElementSearchLowMem:matches(Ljava/lang/String;Lmezz/jei/core/search/PrefixInfo;Lmezz/jei/common/ingredients/IListElementInfo;)Z`、`vazkii.patchouli.client.book.BookEntry:isFoundByQuery(Ljava/lang/String;)Z`、`blusunrize.lib.manual.ManualPages$ItemDisplay:listForSearch(Ljava/lang/String;)Z` 等
- 注入点：`target.type = METHOD`，`methodName` 经 `ASMAPI.mapMethod('m_xxxxx_')` 做 SRG/Mojmap 映射，**不插入指令，只原地改写既有指令的 owner/name/desc/opcode**（`_lib.js` 全程 `n.owner = ...` / `n.setOpcode(Ops.INVOKESTATIC)`）
- 手动脚本示例（`scripts/jei1.js`）：对 `mezz.jei.search.ElementPrefixParser.<clinit>` 与 `mezz.jei.common.search.ElementPrefixParser.<clinit>` 用 `transInvokeLambda` 把 `GeneralizedSuffixTree.<init>` 的方法引用换成 `Match$FakeTree.<init>`——同一脚本内用两个 key（`jecharacters-jei9-1`、`jecharacters-jei10-1`）覆盖 JEI 9/10 两代包名。

## 7. 值得学的 5 条具体做法

1. **把"逐 mod 兼容"降级为一张声明式目标表 + 代码生成**：`generate.py:manual/suffix/contains/equals/regExp` + 生成 `coremods.json`，新增一个 mod 支持只需往数组加一行 `类:方法(描述符)`（`generate.py`）。适用：需要给大量第三方 mod 打同类补丁的适配型 mod。
2. **字节码层纯"调用点替换"而非注入**：写完即返回的 `transInvoke` 三板斧（改 opcode/owner/desc + 兼容 InvokeDynamic 的 `bsmArgs[1]` Handle），不动栈帧不增指令，移植风险最低（`scripts/_lib.js`）。适用：统一替换第三方库里的某个底层查询 API。
3. **用 `WeakHashMap` 反向登记所有运行时创建的搜索结构，配置变更时统一 refresh**（`Match.java:33-39,102`）。适用：搜索/缓存对象散落在第三方代码里、需要热重载配置的场景。
4. **写一个"扫描全量 jar 找调用点"的 Profiler 工具并暴露为游戏内命令**：ASM 扫 `mods/`，按 4 类特征归类，JSON 输出到 `logs/`（`Profiler.java:29-56,58-63` + `JechCommand.java:82-98`）。适用：任何需要定位"哪些 mod 用了 X API"的兼容工作。
5. **不改原版注册也能加客户端命令**：手动 `CommandDispatcher` + `ScreenEvent.InitScreenEvent` 挂到 `RootCommandNode`，`ClientChatEvent` 拦截执行（`JechCommand.java:67-69,100-142`）。适用：纯客户端调试命令，想避免服务端命令树/权限问题。

## 8. 公开 API / 外部接入

不是库 mod，但有两个"隐式 API"：
- `me.towdium.jecharacters.utils.Match` 的静态方法签名就是 coremod 的契约（`contains(String, CharSequence)`、`contains(CharSequence, CharSequence, boolean)`、`equals(String, Object)`、`matcher(Pattern, CharSequence)`、`matches(String, String)`），`scripts/_lib.js` 的 desc 必须与之严格一致；
- 真正的可复用核心是外部库 **PinIn**（`me.towdium.pinin.PinIn`、`searchers.TreeSearcher`、`DictLoader.Default`、`Keyboard` 枚举），本 mod 只是它的注入式外壳。
