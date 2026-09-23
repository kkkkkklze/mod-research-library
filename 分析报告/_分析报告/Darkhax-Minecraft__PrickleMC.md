# Darkhax-Minecraft/PrickleMC 源码分析报告

## 1. 基本信息

- Mod 名 **PrickleMC**（库/前置，把 Prickle 的 JSON 配置格式带进 MC）/ mod_id `prickle` / 作者 Darkhax / 版本 21.1（`gradle.properties` version=21.1，java 21）
- 目标 MC **1.21.1**（`minecraft_version=1.21.1`，range `[1.21.1, 1.22)`），一套代码出 **fabric + forge + neoforge**：NeoForge 21.1.61 / Forge 52.0.16 / Fabric 0.105.0+1.21.1
- Gradle 插件：`fabric-loom 1.7-SNAPSHOT`（fabric）、`net.neoforged.moddev 2.0.30-beta`（neoforge）、自研 buildSrc Groovy 插件 `secret-loader` / `project_validation` / `build-number` / `git-changelog` / `patreon` / `discord-notify` / `version-checker` / `readme-update`；`buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle` 是共用的"多加载器模板"
- 许可证 **LGPL 2.1**；文档 https://docs.darkhax.net/mods/prickle
- 编译依赖：**无前置 mod 依赖**（这是它作为库的卖点）；运行时只需要加载器。可选 `compileOnly` JEI（`neoforge/build.gradle`）；映射用 officialMojangMappings + Parchment
- 反过来的关系：**它是别人的 API**——外部 mod 通过 BlameJared maven 取 `net.darkhax.pricklemc:prickle:...`（`multiloader-common.gradle` 里为每个 variant 挂 capability `$group:$mod_id`）

## 2. 源码规模与包结构

实测 **41 个 .java / 2655 行**（无 datagen 代码、无贴图）。

- `common/.../common/api/annotations/` 8 个：`Value`(45)、`Adapter`、`Array`(36)、`Regex`、`RangedInt/Float/Double/Long`
- `common/.../common/api/config/` 3 个：`ConfigManager`(351)、`ConfigObjectSerializer`(132)、`PropertyResolver`(149)
- `common/.../common/api/config/comment/` 5 个：`WrappedComment`(87)、`CommentTypeAdapter`(61)、`Comment`、`IComment`、`ICommentResolver`
- `common/.../common/api/config/property/` 7 个 + `array/` 4 个：`ObjectProperty`(219)、`RangedProperty`(148)、`RegexStringProperty`(58)、`IConfigProperty`(53)、`IPropertyAdapter`(31)、`ConfigObjectProperty`(83)、`IDefaultPropertyAdapters`；`AbstractArrayProperty`(124)、`ArrayProperty`(71)、`CollectionArrayProperty`(74)、`ArraySettings`(73)
- `common/.../common/api/services/`：`Services`；`api/util/`：`CachedSupplier`(138)、`NumberUtils`(90)、`IPlatformHelper`(32)
- `common/.../common/impl/`：`Constants`(41)、`PrickleMod`(34)、`impl/config/property/CodecProperty`(130)、`MinecraftPropertyPlugin`
- 平台层各 2 个文件（`FabricMod`/`ForgeMod`/`NeoForgeMod` + `*PlatformHelper`）

最大文件前 5：ConfigManager(351) > ObjectProperty(219) > PropertyResolver(149) > RangedProperty(148) > CachedSupplier(138)。

## 3. 入口与注册

无 DeferredRegister、无游戏内容注册——它是配置库。三个平台入口只做同一件事：

```java
// neoforge/.../impl/NeoForgeMod.java
@Mod(Constants.MOD_ID)
public class NeoForgeMod {
    public NeoForgeMod(IEventBus eventBus) { PrickleMod.getInstance().init(); }
}
```

`PrickleMod`（`common/.../impl/PrickleMod.java`）是懒加载单例：`init()` 用 `hasInitialized` 防重入（重复调用抛 `IllegalStateException`），并做启动自检 `Services.PLATFORM == null → IllegalStateException`。真正的"注册"发生在 `ConfigManager.init()`（ConfigManager.java:86-95）：`Services.loadMany(IDefaultPropertyAdapters.class)` 拿到各平台注册的适配器插件，依次 `plugin.register(builder::adapter)`，再叠加调用方传入的 `configure` 消费者。

## 4. 核心系统

**A. 注解驱动的配置 schema 反射**（`ConfigObjectSerializer.java`）
- `mapSchema()` 遍历 `dataObj.getClass().getDeclaredFields()`，只认带 `@Value` 的字段（`field.setAccessible(true)`），属性名支持 `@Value(name="snake_case")` 覆盖
- 重名属性直接 `IllegalStateException`；schema 为空抛 `RuntimeException("Invalid cfg class!")`——作者把配置错误当"编程错误"处理，fast-fail
- schema 存 `LinkedHashMap<String, SchemaEntry>`（`record SchemaEntry(Field, serializedName, valueMeta, property)`）并 `Collections.unmodifiableMap` 冻结；`read()` 遇到未知键只 warn + `in.skipValue()`，向前兼容旧配置

**B. 属性适配器解析链**（`PropertyResolver.java:96-149`）
- 四级回退顺序写死在 `toProperty`：字段 `@Adapter` 覆盖（用 `adapterCache.computeIfAbsent(clazz, ...)` 反射 newInstance 并缓存）→ 注册的 `List<IPropertyAdapter<?>>` 依次尝试（返回 null 即不认）→ `ConfigObjectProperty` 子对象递归 → `ObjectProperty.FALLBACK_ADAPTER`（Gson 兜底）
- 每个 adapter 的 `toValue(resolver, field, parent, value, valueMeta)` 返回 `IConfigProperty<?>` 或 null，是标准的责任链

**C. IConfigProperty 三段式契约**（`IConfigProperty.java`）
- 只有 `value()` / `read(JsonReader, resolver, logger)` / `write(...)` / `validate(T)` 四个方法；`ObjectProperty` 实现骨架并提供 `writeValue`/`readValue` 抽象点（Read 时先 `validate`，不合法则保留默认值并 warn）
- 派生类只改"值怎么写"：`CodecProperty` 用 Mojang Codec ↔ `JsonElement`（`Streams` + `JsonOps.INSTANCE`）桥接，`RangedProperty` 在 `validate` 里用 `NumberUtils.lessThan/greaterThan` 夹取，`RegexStringProperty` 走正则可选校验

**D. JSON 带注释 + 损坏自愈**（`ConfigManager.java:97-199`）
- 读前先 `checkJsonSyntax()`：lenient Gson 解析成 `JsonElement`，非对象即判定语法错误 → 把原文件复制成 `<name>.<hex>.bak` 并放弃本次读取（不覆盖用户文件）
- 注释由 `WrappedComment` 实现"注释也是 JSON 元素"，注册 `CommentTypeAdapter` 序列化；`Constants.DEFAULT_INDENT = "  "` 统一缩进
- Gson 关键配置：`disableHtmlEscaping()`、`serializeSpecialFloatingPointValues()`、`setNumberToNumberStrategy(ToNumberPolicy.BIG_DECIMAL)`（避免长整数被写成科学计数法）、`setLenient()`

**E. 平台抽象（ServiceLoader）**（`api/services/Services.java`）
- `PLATFORM = load(IPlatformHelper.class)` 静态常量，缺失即抛 `NullPointerException`；`loadMany()` 用 `ServiceLoader.load(clazz).stream().map(Provider::get)` 收集插件
- `IPlatformHelper` 仅 `getConfigPath()`（+ 默认 `getConfigDirectory()`）与 `getName()`，实现各 8 行（`FabricLoader.getInstance().getConfigDir()` / `FMLPaths.CONFIGDIR.get()`）
- `MinecraftPropertyPlugin implements IDefaultPropertyAdapters` 预置 8 个 Codec 适配器：ResourceLocation、BlockPos、Component、Style、MobEffectInstance、AttributeModifier、ItemStack、Ingredient（`CodecProperty.java:45-77`）——**MC 类型开箱即可放进 JSON 配置**

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**
- 数据驱动：**无**（不做数据包/资源重载；`prickle.mixins.json` 虽存在但 `mixins/client/server` 全为空数组，仓库内无任何 `org.spongepowered` 引用，即**实际没有 mixin**）
- 配置：本仓库的主业——Gson + 注解生成的 `config/<name>.json`，支持注释、范围、正则、数组、子对象、Codec 类型
- datagen：**无**

## 6. Mixin

`common/src/main/resources/prickle.mixins.json`、`prickle.fabric|forge|neoforge.mixins.json` 均存在（`refmap=${mod_id}.refmap.json`，`compatibilityLevel` JAVA_18/JAVA_21），但列表为空、源码无 mixin 类：**无 mixin 实现**。

## 7. 值得学的 5 条具体做法

1. **反射 schema + 责任链适配器**：新类型支持只需加一个 `IPropertyAdapter`，核心 `PropertyResolver` 不改一行 —— `common/.../api/config/PropertyResolver.java:120-148`
2. **配置损坏先备份再重置**：`checkJsonSyntax` + 时间戳 `.bak` 副本，用户手改坏了不丢数据 —— `common/.../api/config/ConfigManager.java:97-168`
3. **把 MC Codec 桥进 Gson**：`Codec.encodeStart(JsonOps.INSTANCE, value)` → `Streams.write(json, writer)`，复用官方序列化 —— `common/.../impl/config/property/CodecProperty.java:80-90`
4. **用 ServiceLoader 承载"平台插件"而不止"平台实现"**：`IDefaultPropertyAdapters` 让其他 mod 也能往默认适配器表里加东西 —— `common/.../api/config/ConfigManager.java:88`
5. **fast-fail 的配置校验**：重复属性名 / 无 `@Value` 字段 / 服务缺失全部直接抛异常，不静默降级 —— `ConfigObjectSerializer.java:73-88`

## 8. 公开 API（库 mod）

- 入口：`net.darkhax.pricklemc.common.api.config.ConfigManager`
  - `load(String name, T defaultValue[, Consumer<Builder<T>> configure])`：一行建配置并回写
  - `init(...)` / `Builder<T>`：`adapter(IPropertyAdapter<?>)`、`gsonConfig(Consumer<GsonBuilder>)`、`gsonBuilder(...)`、`commentResolver(ICommentResolver)`、`logger(Logger)`、`build(T)`
- 注解（`api/annotations/`）：`@Value`(name/comment/reference/writeDefault)、`@Array`、`@Regex`、`@RangedInt|Float|Double|Long`、`@Adapter(clazz)`
- 扩展点接口（`api/config/property/`）：`IConfigProperty<T>`、`IPropertyAdapter<T>`、`IConfigProperty` 的既有实现 `ObjectProperty` / `ConfigObjectProperty` / `RangedProperty` / `RegexStringProperty` / `ArrayProperty` / `CollectionArrayProperty`；服务接口 `IDefaultPropertyAdapters`
- 注释体系（`api/config/comment/`）：`IComment` / `ICommentResolver` / `Comment`，可用 `Builder.commentResolver(...)` 替换
- 工具（`api/util/`）：`CachedSupplier`（带 `invalidate()`/`ifCached()` 的懒缓存）、`NumberUtils`、`IPlatformHelper`
- 接入方式：Maven（BlameJared 仓库）依赖 + 在自身 `@Mod` 构造器里调用 `ConfigManager.init(...)`，或直接 `Services.loadMany(IDefaultPropertyAdapters.class)` 注入自定义类型；发行物同时挂 `$group:$mod_id` 与 `$group:$mod_id-<platform>-<mcver>` 两个 capability
