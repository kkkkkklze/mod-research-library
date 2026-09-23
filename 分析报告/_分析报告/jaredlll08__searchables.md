# Searchables 源码分析（jaredlll08）

## 1. 基本信息

- Mod 名 Searchables；mod_id `searchables`；作者 Jaredlll08；`gradle.properties` 记 `mod_version=1.0`（实际发布版本由构建逻辑 `GMUtils.updatingVersion` 生成）
- 目标环境：`gradle.properties` 为 `minecraft=26.2`、`java_version=25`、`neo_form_version=26.2-1`、`fabric=0.152.1+26.2`、`fabric_loader=0.19.3`、`neoforge=26.2.0.1-beta`、`neoforge_loader=[4,)`（READ.ME 徽章仍指向 1.21.8 分支，本检出为最新分支）
- 三源集多加载器：`common`（纯原版 API）+ `fabric` + `neoforge`（`settings.gradle` 里 `includeBuild('build-logic')`）
- Gradle 插件：`net.neoforged.moddev 2.0.141`（common/neoforge）、`net.fabricmc.fabric-loom 1.16.3`（fabric）、自研 `com.blamejared.root-plugin / common-plugin / loader-plugin`（来自 `maven.blamejared.com`，源码在 `build-logic/src/main/java/com/blamejared/`），发布用 `minotaur` + `curseforgegradle`
- 许可证 MIT（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）；依赖仅 `neoforge` + `minecraft`（无第三方前置）；common 源集额外 compileOnly `sponge mixin 0.8.5`、`mixinextras-common 0.3.5`，测试用 JUnit5 + hamcrest（`common/build.gradle`）

## 2. 源码规模与包结构

47 个 `.java`（含 build-logic 4、test 3），3164 行（`find . -name '*.java' | wc -l`、`-exec wc -l {} +`；不含 build-logic 约 2800 行）。

包（第 3 层，文件数）：`api` 4、`api/autcomplete` 5、`api/context` 6、`api/formatter` 4、`lang` 5、`lang/expression/type` 5、`lang/expression/visitor` 3、`mixin` 2、`tests` 2。

最大文件：`api/autcomplete/AutoComplete.java`、`api/TokenRange.java`、`api/SearchableType.java`、`api/formatter/FormattingVisitor.java`、`api/autcomplete/AutoCompletingEditBox.java`、`api/autcomplete/CompletionVisitor.java`、`lang/SLParser.java`（`find -printf '%s'` 排序）

## 3. 入口与注册

- `neoforge/.../SearchablesNeoForge.java`：`@Mod("searchables")`，构造函数空实现，**不做任何注册**；`fabric/.../SearchablesFabric.java` 是空类。本检出中 fabric 源集没有 `fabric.mod.json`（未确认，可能由 loom 生成或未纳入检出）
- 无 DeferredRegister / Registrate / 注册表 / 网络 / 配置 / datagen——mod 外壳只负责把 `api` 包带进 classpath
- 两个加载器的 mixins.json（`searchables.neoforge.mixins.json`、`searchables.fabric.mixins.json`）mixin 列表均为空，`compatibilityLevel: JAVA_21`；common 的 `searchables.mixins.json` 为 `JAVA_18`

## 4. 核心系统

**A. 搜索 DSL（词法/语法/访问者三层）**
- `lang/SLScanner.java` → `lang/Token.java` + `lang/TokenType.java`（仅 `COLON, IDENTIFIER, STRING, SPACE, EOL` 五种）→ `lang/SLParser.java` 递归下降生成 AST
- AST 四种节点在 `lang/expression/type/`：`LiteralExpression`（单值）、`ComponentExpression`（`key:value`）、`GroupingExpression`（空格并列）、`PairedExpression`（`:x` 无 key 的降级形式）；`SLParser.grouping()`（`SLParser.java:37`）按 `TokenType.COLON` 区分组件式与并列式
- `lang/StringSearcher.java` 是唯一静态入口：`search(String, Visitor)`、`search(String, ContextAwareVisitor, C)`、`expression(String)`；访问者只有 `Visitor`/`ContextAwareVisitor` 两个接口，重复利用同一棵 AST

**B. SearchableType / SearchableComponent（对外模型）**
- `api/SearchableType.java`：`Map<String, SearchableComponent<T>> components` + `@Nullable defaultComponent`（builder 里重复设置会抛 `IllegalStateException`）；`filterEntries(entries, search, extraPredicate)`（`:111`）把 `SearchContext.createPredicate(this)` 与外部谓词 `and` 后流式过滤
- `api/context/SearchContext.java` 把多条 `SearchPredicate` 用 `reduce(t -> true, Predicate::and)` 合成单一谓词；`ContextVisitor` 负责把 AST 落成谓词
- `api/SearchableComponent.java`：`key + Function<T,Optional<String>> toString + BiPredicate<T,String> filter`；三个静态工厂（`:37/:52/:66`）默认用 `StringUtils.containsIgnoreCase(toString, search)` 做匹配；`toString` 构造时统一 `andThen` 一层 `VALID_SUGGESTION` 过滤

**C. 自动补全**
- `api/autcomplete/AutoComplete.java`（`extends AbstractWidget implements Consumer<String>`）：`suggestionHeight/maxSuggestions(默认 7)/displayOffset/selectedIndex(=-1 无选中)/lastMousePosition/Vector2d` 组成一个独立下拉控件
- `SearchableType.getSuggestionsFor(...)`（`:48`）用 `TokenRange.rangeIndexAtPosition(position)` 的 switch 分三种上下文：0=补全组件名、1=补全第一个词、2=词内补全；`CompletionSuggestion(name, Component, suffix, replacementRange)` 携带替换后缀（`":"` 或 `" "`）
- `api/TokenRange.java` 负责多区间（key 区间+词区间）的位置判定/裁剪/简化（`rangeAtPosition`、`contains`、`simplify`、`range(i)`），是补全与高亮共用的基础设施

**D. 输入框语法高亮**
- `api/formatter/FormattingVisitor.java`：`implements Consumer<String>, EditBox.TextFormatter, ContextAwareVisitor<TokenRange, FormattingContext>`，产出 `List<Pair<TokenRange, Style>> tokens`，支持 `reset()` 复用实例
- 三种样式写死在 `api/formatter/FormattingConstants.java`：`INVALID`=红+下划线、`KEY`=0x669BBC、`TERM`=0xEECC77，第三方无法自定义（未提供扩展点）

**E. 引号/转义策略**（`api/SearchablesConstants.java`）
- `STRING_CHARACTERS = "'\"`"`；`VALID_SUGGESTION` 过滤掉同时含三种引号的字符串（解析器暂无转义）；`QUOTE = Util.memoize(...)` 为含空格/引号的词自动挑一个不冲突的引号包裹，避免手工转义

## 5. 网络 / 数据驱动 / 配置 / datagen

全部为「无」。mod 是纯客户端搜索 UI 库，无 packet、无 sound/registry 注册、无 data 包资源、无 tooltip 数据驱动。

## 6. Mixin

`common/src/main/resources/searchables.mixins.json`：仅 `client: ["AccessEditBox"]`，`injectors.defaultRequire=1`，refmap `searchables.refmap.json`。代表类 `mixin/AccessEditBox.java` 用 `@Accessor("responder") Consumer<String> searchables$getResponder()` 拿到 `EditBox` 私有 responder，供 `AutoCompletingEditBox` 在补全插入文本后主动触发搜索回调。

## 7. 值得学的具体做法

1. **用 TokenRange 承载“多区间编辑”**：`api/TokenRange.java` 把“key 区间+值区间”抽象成可裁剪集合，补全、替换、高亮三处复用，避免各自算下标（适用：任何带补全的输入控件）。
2. **访问者 + 上下文参数**：`lang/expression/visitor/ContextAwareVisitor.java` 让同一 AST 既产出 `Predicate` 又产出 `Pair<TokenRange,Style>` 高亮，`Expression.accept(visitor, C)` 保持零依赖（适用：DSL 多消费者）。
3. **自动引号包裹**：`SearchablesConstants.QUOTE` 用 `Util.memoize` 缓存并把“含空格的词”统一加引号，补全插入即可直接再解析（适用：文本查询语法）。
4. **组件式 builder 的对外 API**：`SearchableType.Builder` + `SearchableComponent` 三个工厂重载，把“如何匹配/如何显示”拆成两个函数参数，接入方只写 lambda（适用：库模组扩展点设计）。
5. **加载器壳 + 单元测试**：`neoforge`/`fabric` 主类近乎空类，全部逻辑在 `common`，并用 `common/src/test/.../AutoCompleteTest.java`（15KB，JUnit5）对 DSL 与补全结果做断言——不启游戏就能验证的核心逻辑（适用：多加载器库模组）。

## 8. 库/API 类 mod 专属

- 公开 API 包：`com.blamejared.searchables.api`（`:api`、`:api.autcomplete`、`:api.context`、`:api.formatter` 四个子包，均带 `package-info.java`）
- 扩展点：`SearchableType.Builder#component/defaultComponent`、`SearchableComponent#create`、`AutoCompletingEditBox`（构造需 Font/坐标/宽高/上一个框/占位 Component/SearchableType/`Supplier<List<T>>`）、`AutoComplete` 控件、`FormattingVisitor`（挂到 `EditBox.addFormatter`）；未提供注册表/事件，无跨 mod 注册机制（`SearchableType.java:161` 留了 `//TODO An event could be fired here` 注释）
- 发布坐标：`com.blamejared.searchables:Searchables-{common,fabric,forge}-<mc版本>`，仓库 `https://maven.blamejared.com`；`common/build.gradle` 暴露 `commonJava`/`commonResources` 两个 consumable configuration 并给所有 variants 打上 `io.github.mcgradleconventions.loader` 属性，供 MultiLoader 模板消费
