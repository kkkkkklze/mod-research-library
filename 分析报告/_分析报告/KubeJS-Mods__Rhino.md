# KubeJS-Mods / Rhino 源码分析报告

## 1. 基本信息

- Mod 名：Rhino（Mozilla Rhino 的 Minecraft 向 fork）；mod_id：`rhino`；作者：`latvian.dev, Mozilla`（`src/main/resources/META-INF/neoforge.mods.toml`）；group `dev.latvian.mods`。
- 目标版本与加载器：`gradle.properties` → `minecraft_version=1.21.1`、`supported_versions=1.21, 1.21.1, 1.21.2, 1.21.3, 1.21.4, 26.1.2`、`neoforge_version=21.1.97`、`mod_version=2101.2.8`、`loom.platform=neoforge`。许可证 MPL-2.0。两个元数据文件并存：`META-INF/neoforge.mods.toml` 与 `META-INF/mods.toml`，均为 `modLoader = "lowcodefml"`、`loaderVersion = "[2,)"`；Forge 侧另有 `displayTest = "NONE"`；无 `fabric.mod.json`（build.gradle 的 processResources 仍为其保留 expand 分支）。
- Gradle 插件：`net.neoforged.moddev` 2.0.138 + `me.shedaniel.unified-publishing`（build.gradle:1-10），`options.release.set(21)`，`afterEvaluate` 设置 `-Xmaxerrs 1000`。
- 编译依赖：**只有 test 依赖**（`build.gradle:68-76`：junit-jupiter-api/engine、guava、gson）；无 Minecraft / 加载器 / Mixin 依赖 → 纯库。

## 2. 源码规模与包结构

- 实测：`find . -name '*.java' | wc -l` = **315**，总 **75551** 行；`src/main/java` 为 276 个文件 / 72496 行（其余 39 个在 `src/test`）。
- 包（文件数，至第 3 层）：`dev/latvian/mods/rhino` 138、`.ast` 66、`.type` 25、`.util` 20、`.classfile` 10、`.v8dtoa` 6、`.util.wrap` 5、`.regexp` 5、`.json` 1。
- 最大的 8 个文件：`classfile/ClassFileWriter.java` 4353、`Parser.java` 4246、`ScriptRuntime.java` 3461、`regexp/NativeRegExp.java` 2895、`Interpreter.java` 2461、`NativeArray.java` 2407、`ScriptableObject.java` 2267、`Context.java` 2027（另有 `IRFactory.java` 1948、`CodeGenerator.java` 1508）。

## 3. 入口与注册

**无 mod 入口类**：全部 `src/main/java` 中 `grep "net.neoforged\|net.minecraft"` 命中 0 处，也没有 `@Mod`。它靠 `mods.toml`/`neoforge.mods.toml` 提供元数据、以 jar 形式随宿主分发（`modLoader="lowcodefml"`），功能入口是**库 API** 而非事件。无 DeferredRegister/Registrate 之类注册框架。

真正的"注册"是上下文定制与类型包装注册：

```java
// ContextFactory.java:13-43（节选）
public class ContextFactory {
    private final ThreadLocal<Context> currentContext;
    public ContextFactory() { this.currentContext = ThreadLocal.withInitial(this::createContext); ... }
    protected Context createContext() { return new Context(this); }
    public Context enter() { return currentContext.get(); }
    public synchronized TypeWrappers getTypeWrappers() { return typeWrappers; }
}
```

## 4. 核心系统

1. **上下文与线程模型**（`ContextFactory.java:14/22/30/36`）：每线程一个 `Context`（ThreadLocal），`createContext()` 可被子类覆写注入自定义 Context —— 测试即用 `TestContextFactory`（`src/test/.../TestContextFactory.java:6`）返回带 `testName` 字段的 `TestContext`（`TestContext.java:8`）。`instanceStaticFallback`（:101-107）控制实例方法可否当静态调用；`CachedClassStorage.GLOBAL_PUBLIC`（:109-111）集中缓存反射信息。
2. **编译与执行**：`Context.compileString(...)`（`Context.java:538`）与 `evaluateString(...)`（:464，内部先编译）；`initStandardObjects()`（:296/344/405 → `ScriptRuntime.initStandardObjects`）。两套执行后端：`Interpreter.java`（解释执行）与 `CodeGenerator.java` + `classfile/ClassFileWriter.java`（生成 JVM 字节码，`classfile` 包自带 ConstantPool/ByteCode/SuperBlock）。
3. **类型转换与包装（本 fork 的核心改造）**：`type/TypeInfo.java:27` 接口 + 25 个实现（`ClassTypeInfo/ArrayTypeInfo/RecordTypeInfo/JSFunctionTypeInfo/JSOrTypeInfo/ParameterizedTypeInfo…`）；`type/TypeConsolidator.java:28/42` 负责泛型实参归并。`Context` 侧：`wrap`（:1087/1127）、`wrapAsJavaObject`（:1258）、`javaToJS`（:1523）、`jsToJava`（:1537）、`arrayOf/listOf/setOf/mapOf`（:1335/1354/1390/1412）、`getConversionWeight`（:1742）做重载选择。`util/wrap` 提供 `TypeWrappers/TypeWrapperFactory/DirectTypeWrapperFactory/TypeWrapperValidator` 供宿主注册"Java→JS"适配器。
4. **沙箱与可见性**：`Context.visibleToScripts(String fullClassName, ClassVisibilityContext)`（`Context.java:1083`），`ClassVisibilityContext` 为枚举（`util/ClassVisibilityContext.java:3`），按使用位置判定可见性（`ARGUMENT`，见 :1478/1486）。
5. **Java 互操作与 MC 生态扩展**：`JavaMembers/MemberBox/NativeJavaObject/NativeJavaClass/InterfaceAdapter`；`LambdaFunction/LambdaConstructor/LambdaAccessorSlot/JavaAdapter`；record 支持（`ContextFactory.registerDefaultRecordProperties:49`、`getRecordConstructor:74`，用 `MethodHandles`）；KubeJS 追加的 `NativeMap/NativeSet/NativeWeakMap/NativePromise/NativeGSON/NativeJSON/ES6Generator/ES6Iterator`。
6. **测试基建**：`src/test` 39 个文件，JUnit5（`build.gradle:78-80` `useJUnitPlatform()`），`RhinoTest.java` 统一持有 `ContextFactory` 并 `factory.enter()` 取 Context。

## 5. 网络 / 数据驱动 / 配置 / datagen

全部**无**：无网络包、无 config、无 datagen、无资源数据（`src/main/resources` 仅 `Messages.properties` 与两个 mods.toml）。

## 6. Mixin

无 mixin 配置、无 mixin 类。

## 7. 值得学的 5 条具体做法

1. **ThreadLocal 上下文 + 工厂方法覆写**：`ContextFactory` 让宿主（KubeJS）注入自己的 Context 子类而无须改引擎（`ContextFactory.java:22,30`；`Context.java:207` 持 `factory` 引用）→ 适用：任何"库+宿主"架构要允许宿主扩展运行时状态。
2. **用类型对象而不是裸 `Class` 描述转换目标**：`TypeInfo`/`TypeConsolidator` 支持泛型、数组、record、JS 常量与函数式接口，使重载决议可打分（`Context.java:1742`）→ 适用：脚本/配置解析层需要把弱类型值"最合适地"映射到 Java 参数。
3. **注解驱动的 JS 命名映射**：`util/RemapForJS.java`（`@RemapForJS("name")`）配合 `@RemapPrefixForJS`、`@HideFromJS`、`@ReturnsSelf`，把 Java 方法名与脚本可见名解耦 → 适用：Java API 重构但脚本兼容性不能破。
4. **把"类是否对脚本可见"做成带上下文维度的方法**：`visibleToScripts(name, ClassVisibilityContext)`（`Context.java:1083`）→ 适用：给脚本系统做细粒度白名单/黑名单，而不是一刀切开关。
5. **库与平台彻底解耦 + 自带可运行单测**：main 源码 0 处 Minecraft import，测试直接 `factory.enter()` 跑 JUnit（`build.gradle:68-80`；`src/test/.../RhinoTest.java:34`）→ 适用：写"框架型/前置型"mod，能独立测、可被多宿主复用。

## 8. 公开 API 与外部接入

- API 包：`dev.latvian.mods.rhino`（`Context`、`ContextFactory`、`Scriptable`、`ScriptableObject`、`Function`、`ScriptRuntime`、`NativeJavaObject`…）、`dev.latvian.mods.rhino.type`（`TypeInfo` 及其实现）、`dev.latvian.mods.rhino.util`（注解 + `util.wrap.TypeWrappers`）、`dev.latvian.mods.rhino.classfile`（体积引擎，通常视为内部）。
- 接入方式：继承 `ContextFactory` → `enter()` 得 `Context` → `initStandardObjects()` 建全局作用域 → `compileString/evaluateString` 执行脚本；`getTypeWrappers()` 注册自定义类型包装；Java↔JS 边界走 `Context.wrap/javaToJS/jsToJava`。
- 已知宿主：KubeJS（同组织的 `KubeJS-Mods/KubeJS`）。本仓库 1.21.1 版本可直接作为 NeoForge 1.21.1 的脚本引擎依赖来研究/使用（mod id `rhino`）。
