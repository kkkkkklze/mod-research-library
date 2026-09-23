# thedarkcolour/KotlinForForge 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：Kotlin for Forge / `kotlinforforge`（`src/kffmod/templates/META-INF/neoforge.mods.toml:11`），作者 thedarkcolour，版本 `kff_version=6.3.0`（`gradle.properties`），许可证 LGPL。
- 目标 MC：`gradle.properties` 里 `min_mc_version = 1.21.9`、`unsupported_mc_version = 26.3`，模板 toml 用 `${min_mc_version},${unsupported_mc_version})` 展开（本仓库为 6.x 分支，面向 1.21.9+，分支名 `6.x`）。**注意：不是 1.21.1，Forge 1.21+ 支持尚未实现（README 明说 "Forge support Not yet implemented"）。**
- 构建：`build.gradle.kts`，Kotlin JVM 2.4.0、NeoForge moddev 2.0.71、shadow 9.1.0、JarJar（moddevgradle）、GradleUp shadow、mod-publish-plugin；`settings.gradle.kts` 用子项目 `combined:kfflang/kfflib/kffmod` 生成 JarJar 元数据。
- 关键依赖：kotlin-stdlib/reflect/coroutines/serialization（`gradle/libs.versions.toml` 的 `bundles.kotlin`）、ASM 9.5、log4j、`net.minecraftforge:forgespi`、`net.neoforged:bus`、night-config。全部以 `compileOnly` 引入，运行期由它自带/打包。
- 它是"语言提供者"型前置：其它 mod 通过 `modLoader="kotlinforforge"` 使用它，自己不需要写 Java 入口（README 的 gradle 片段：`implementation 'thedarkcolour:kotlinforforge-neoforge:6.0.0'`）。

## 2. 源码规模与包结构

实测（含未 checkout 的资源文件共 70 个 git 跟踪文件）：**28 个 `.kt`、1827 行**；`src/fakecraft` 另有 18 个 `.java`、274 行（假签名）。

- `src/kfflang/{neoforge,forge}/kotlin/thedarkcolour/kotlinforforge/`：语言提供者层（`KotlinLanguageLoader.kt` 61、`KotlinModContainer.kt` 134、`AutoKotlinEventBusSubscriber.kt` 178、`KotlinModLoadingContext.kt` 26、`Logger.kt` 11）；Forge 版对应 `KotlinLanguageProvider.kt` 83、`KotlinModContainer.kt` 98、`EventBusMakers.kt` 36。
- `src/kfflib/{common,neoforge,forge}/.../forge/`：工具库层（`Forge.kt` 157/123、`KDeferredRegister.kt` 36、`DeferredHolders.kt` 19、`CapabilityUtil.kt` 8、`ProfilerUtil.kt` 14、`PoseStackUtil.kt` 12、`vectorutil/` 6 个文件约 500 行、`kotlin/Kotlin.kt` 85）。
- `src/kffmod/{neoforge,forge}/.../test/KotlinForForge.kt`：11 行的 KFF 自身 mod 入口；`src/kffmod/templates/META-INF/*.toml` 是给下游复制用的模板。
- 最大文件：`AutoKotlinEventBusSubscriber.kt`(178)、`kfflib/forge/.../Forge.kt`(157)、`kfflang/forge/.../AutoKotlinEventBusSubscriber.kt`(140)、`KotlinModContainer.kt`(134/98)、`kfflib/neoforge/.../Forge.kt`(123)。

## 3. 入口与注册

KFF 自身入口极简，`src/kffmod/neoforge/kotlin/.../test/KotlinForForge.kt`：

```kotlin
@Mod("kotlinforforge")
public object KotlinForForge {
    private val LOGGER = LogManager.getLogger()
    init { LOGGER.info("Kotlin For Forge Enabled!") }
}
```

语言接入靠 ServiceLoader 文件（仓库中已跟踪，工作区快照未落地，用 `git show` 读取）：
`src/kfflang/neoforge/resources/META-INF/services/net.neoforged.neoforgespi.language.IModLanguageLoader` 内容为 `thedarkcolour.kotlinforforge.neoforge.KotlinLanguageLoader`；Forge 侧同名文件填 `...kotlinforforge.KotlinLanguageProvider`。前者 jar 的 manifest 打 `FMLModType=LIBRARY`，后者打 `FMLModType=LANGPROVIDER`，库本体打 `GAMELIBRARY`（`combined/*/build.gradle.kts` 与 `build.gradle.kts:201-262`）。

下游 mod 的 toml 只需 `modLoader="kotlinforforge"` + `loaderVersion="[5,)"`（`src/kffmod/templates/META-INF/neoforge.mods.toml:1-4`）。KFF 自身不注册任何游戏内容。

## 4. 核心系统

1. **KotlinLanguageLoader（NeoForge）** `src/kfflang/neoforge/.../KotlinLanguageLoader.kt`：实现 `IModLanguageLoader`，在 ASM 扫描结果里筛 `annotationType == Mod` 且 `value == modId` 且 `dist` 匹配的类（`:28-34`），交给 `KotlinModContainer`；`validate()` 对"@Mod 的 modid 没在 toml 里声明"的情况报 `dangling_entrypoint` 错误（`:45-53`）。方法签名刻意用可空返回 `version(): String?` 与 `filter/map` 而非 stream，注释"to avoid classloading kotlin Intrinsics"——避免在语言层加载 Kotlin 运行时。
2. **KotlinModContainer**（`:21-134`）：继承 `ModContainer`，自己用 `BusBuilder.builder().setExceptionHandler(...).markerType(IModBusEvent).allowPerPhasePost().build()` 造事件总线（`:36-40`），并按 `info.owningFile.file.id` 找到 ModuleLayer、`Class.forName(layer, entrypoint)` 加载入口类。`constructMod()` 是精髓：**`modClass.kotlin.objectInstance != null` 时直接用 object 单例作为 mod 实例**（`:76-79`），否则要求"恰好 1 个 public 构造器"且参数只能从 `{IEventBus, ModContainer, FMLModContainer, Dist}` 白名单里注入（`:86-105`），并对 `InvocationTargetException` 解包后包成 `ModLoadingIssue.error("fml.modloadingissue.failedtoloadmod")`。
3. **AutoKotlinEventBusSubscriber**（178 行）：NeoForge 只能自动注册静态方法/类，无法处理 Kotlin `object` 与文件级注解，于是 KFF 自己反射：扫所有 `@EventBusSubscriber` 注解，取 `kClass.objectInstance`（`UnsupportedOperationException` 且消息含 "file facades" 时说明是文件级注解，走"伪造一个 `ModFileScanData` 再交回 NeoForge 的 `AutomaticEventSubscriber.inject`"，`:158-164`）。
4. **按事件类型自动选总线**：对 object 内的每个 `@SubscribeEvent` 函数用 `kotlin.reflect` 取 `javaMethod`，校验"仅 1 个参数且是 Event 子类"（`:122-124`），再按 `IModBusEvent::class.java.isAssignableFrom(eventType)` 分流：mod 事件进 `mod.eventBus`，其余进 game bus；`registerMemberMethod` 用 `SubscribeEventListener(obj, method).withoutCheck` 直接注册到对应总线（`:169-177`）。无 mod 事件时保留旧行为（整个 object 注册到 game bus，`:135-141`）。
5. **KotlinModLoadingContext / 惰性入口** `KotlinModLoadingContext.kt`：持有 container 的 eventBus，`get()` 从 `ModLoadingContext.get().activeContainer` 取并强转，为兼容 FancyModLoader 3.x 还会反射往 `ModContainer.contextExtension` 塞一个 `Supplier { context }`（`KotlinModContainer.kt:44-49`）。用户侧入口是 `kfflib` 的扩展属性：`MOD_BUS` = `KotlinModLoadingContext.get().getKEventBus()`、`FORGE_BUS` = `NeoForge.EVENT_BUS`、`MOD_CONTEXT`、`DIST`（`kfflib/neoforge/.../forge/Forge.kt:16-37`），全部是 inline getter，**访问时才求值**，这正是"延迟初始化"的实现方式。
6. **Forge 变体**：`KotlinLanguageProvider.kt` 实现 `IModLanguageProvider`，通过 `scanData.addLanguageLoader(...)` 注册 `KotlinModTarget`；由于 Forge 与 KFF 的类加载器不同，`loadMod` 里用 `Thread.currentThread().contextClassLoader` + 反射 `Class.forName("thedarkcolour.kotlinforforge.KotlinModContainer")` 构造容器（`:40-52`），失败时再反射构造 `ModLoadingException`（`catastrophe`，`:70-80`），这是典型的"跨 classloader 不能直接引用类型"的绕法。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无（不注册任何包），仅提供 bus/工具。
- 配置：无自有配置系统；`libs.versions.toml` 引入 night-config 仅因 Forge 侧编译需要，KFF 本身未使用（未确认具体用途）。
- 数据驱动 / datagen：无。仓库只有 `src/kffmod/common/resources/{pack.mcmeta, kotlinforforge_icon.png}`。
- Kotlin 库打包：`build.gradle.kts:263-283` 用 JarJar 把 `combined:kfflang/kfflib/kffmod` 与 `bundles.kotlin`（stdlib/reflect/coroutines/serialization-json）一起塞进 `-all` jar；Maven 侧再单独发布 `mavenJar`（只含 Kotlin 库）+ 手写 POM 依赖 `kfflang/kfflib/kffmod`。

## 6. Mixin

无 mixin（全仓库无 `*.mixins.json`、无 `@Mixin`）。它靠 ASM 扫描（`ModFileScanData`）+ 反射 + 自建语言提供者实现目标，不触碰 Minecraft 类。

## 7. 值得学的 5 条具体做法

1. **用 `object` 直接当 mod 入口实例**：`modClass.kotlin.objectInstance` 非空即取单例，免去无参构造要求（`KotlinModContainer.kt:76-79`），这是 KFF 让 `@Mod object` 成立的核心。
2. **构造器参数白名单注入**：只允许 `IEventBus / ModContainer / FMLModContainer / Dist` 且禁止重复类型（`KotlinModContainer.kt:86-105`），给 Kotlin 用户 Koin 式的手写 DI 而不破坏加载器约束。
3. **按事件基类自动分流总线**：`IModBusEvent` 判据把同一 object 里的监听器拆到不同 event bus（`AutoKotlinEventBusSubscriber.kt:127-152`），省去人工选总线。适用场景：写多总线加载器的自动订阅工具。
4. **语言层刻意不触碰 Kotlin 运行时**：`version(): String?`、去掉 stream、注释明说要避开 classloading `Intrinsics`（`KotlinLanguageLoader.kt:21-27`）。适用场景：在类加载早期运行的加载器代码。
5. **用 shadow relocate 复用一套源码打两个加载器**：`kfflib/common` 写 `thedarkcolour.kotlinforforge.forge` 包，NeoForge 产物用 `relocate("...forge", "...neoforge.forge")` 改名，source jar 用字符串替换同步修包声明（`build.gradle.kts:188-194, 232-241`）。适用场景：Forge/NeoForge 双发行。
6. **假签名编译（fakecraft）**：`src/fakecraft/java/net/minecraft/...` 只放用到的少量 MC/Forge 类签名（如 `Vec3.java`、`DeferredRegister.java`），让工具库源码不依赖整份 Minecraft（`build.gradle.kts:82-84, 153-155`），库因此可以脱离 mod 环境编译。

## 8. 公开 API（前置/库 mod）

- Maven：`thedarkcolour:kotlinforforge-neoforge:<ver>`（POM 自动带 `kfflang/kfflib/kffmod` 与 Kotlin 库依赖），仓库 `https://thedarkcolour.github.io/KotlinForForge/`。
- 下游扩展点：`modLoader="kotlinforforge"` 的 toml + `@Mod` 标注的 Kotlin `class`/`object`/顶层文件；事件用 `@EventBusSubscriber`（或 `@file:Mod.EventBusSubscriber` + 顶层 `@SubscribeEvent fun`）；总线入口用 `MOD_BUS`/`FORGE_BUS`/`MOD_CONTEXT`/`DIST`（`thedarkcolour.kotlinforforge.neoforge.forge` 包，Forge 为 `...kotlinforforge.forge`）。
- 工具 API：`KDeferredRegister.registerObject` 返回 `ObjectHolderDelegate`（`by` 委托，同时是 `Supplier` 和 `() -> V`，`KDeferredRegister.kt`）；NeoForge 侧 `DeferredHolder/DeferredBlock/DeferredItem` 的 `getValue` 委托（`DeferredHolders.kt`）；`runForDist/runWhenOn/callWhenOn/lazySidedDelegate/sidedDelegate` 替代 `DistExecutor`（`Forge.kt:42-123`）；`ProfilerFiller.use(name) {}`（`ProfilerUtil.kt`）；`ICapabilityProvider.getCapabilityOrThrow`（`CapabilityUtil.kt`）；JOML 向量工具 `vectorutil/v{2,3,4}d/*`。
