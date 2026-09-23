# decce6/AsyncLogger 源码分析报告

## 1. 基本信息

- Mod 名/ID：Async Logger / `asynclogger`；作者 decce（credits：Asbestosstar、Aresky）；version 2.2.2
- 目标版本与加载器（`settings.gradle.kts` stonecutter 块）：fabric 26.1(unobf)/1.21.11/1.20.1/1.16.5、neoforge 26.1/1.21.11/1.21.1、forge 1.20.1~1.16.5(archloom)、legacy forge 1.12.2(unimined)、ornithe 1.8.9(ploceus)；默认目标 `1.21.11-fabric`
- Gradle 插件：`dev.kikugie.stonecutter 0.9.7`、buildSrc 约定插件 `transformingbase-common-conventions`、core 子工程用 `com.gradleup.shadow 9.6.0`；`includeBuild("core")`
- 许可证：LGPL-3.0-only（`gradle.properties: mod_license`）
- 依赖：`net.lenni0451.classtransform:core:1.15.0-SNAPSHOT`（class transform，shade 且 relocate）、`net.lenni0451:Reflect:1.6.2`（shade+relocate）、`log4j-core:2.19.0` compileOnly、LWJGL 3.3.1 compileOnly、jabel javac 插件（Java 21 工具链编译 `options.release = 8`）

## 2. 源码规模与包结构

- `.java` 文件 37 个，合计 **2019 行**（`find . -name '*.java' -exec wc -l {} + | tail -1`）
- 三个源码集：`core/`（`me.decce.transformingbase.core`、`.transform`、`.util`、`.constants`）、`src/service/`（`service`、`service.fabric/forge/neoforge/legacyforge`）、`src/mod-src/`（`me.decce.asynclogger` + 各加载器入口 + `mixins`）
- 最大文件：LoggerConfigurator 190、service/ConfigLoader 157、ForgeModLocator 129、ClassLoaderHandlerImpl 125、AsyncFilter 102、WrappedPrintStream 99、FilterImpl 98、LoggerTester 96、ClassLoaderHandler 90

## 3. 入口与注册

无 DeferredRegister/Registrate（非内容 mod）。真正的初始化在 **pre-launch**：`src/service/java/me/decce/transformingbase/service/fabric/FabricPreLaunchEntrypoint.java`（`PreLaunchEntrypoint.onPreLaunch()`）、`service/forge/ForgeTransformationService.java`（`ITransformationService.initialize()`）都调用 `Bootstrapper.bootstrap()`；普通入口 `neoforge/NeoForgeEntrypoint.java`（`@Mod(Constants.MOD_ID)`）与 `fabric/FabricEntrypoint.java` 只调 `AsyncLoggerMod.init()`（空）。

## 4. 核心系统

- **Bootstrapper 类加载器注入**（`src/service/.../service/Bootstrapper.java:15`）：用 `ClassLoaderHandlerImpl(Logger.class.getClassLoader(), Bootstrapper.class.getClassLoader())` 把 `/com/lmax`（LMAX Disruptor）和 `Constants.CORE_PACKAGE_PATH=/me/decce/asynclogger/core` 的字节码 `defineClass` 进 log4j 所在类加载器，随后 `removeModClassesFromServiceLayer`；`bootstrapped`/`skippedDisruptorLoading` 幂等标志
- **LoggerConfigurator**（`core/.../core/LoggerConfigurator.java`）：静态块把 ringBufferSize 等映射为 `log4j2.asyncLoggerRingBufferSize` 等系统属性（0 时用 `16*1024` 默认值）；`configure()` 先快照原 root 的 appenders/appenderRefs，再 `LogManager.setFactory(new Log4jContextFactory(new BasicAsyncLoggerContextSelector()))` + `Configurator.reconfigure(配置源 URI)`，最后把原 appenders 补回（`:81-95`）
- **过滤体系**：`AsyncFilter`(继承 `AbstractFilter`)+`FilterImpl`+`FilteringInfo`（levels/loggers/strings/regexes 四个数组）。两级挂载：`LoggerContext.addFilter`（global，Logger 阶段、调用者线程）或 root `LoggerConfig.addFilter`（异步线程、零调用者开销），见 `:163-175`；`FilterImpl.java:15-60` 手写索引 for 循环避免迭代器分配
- **配置声明式读取**：`AsyncLoggerConfig` 字段加 `@Comment`/`@Key` 注解，`ConfigLoader.toNightConfig/fromNightConfig`（`:112-156`）反射读写 nightconfig TOML；`loadExtras/readExtras` 把 `config/asynclogger/*.toml` 的过滤列表合并进主配置
- **stdout/stderr 包装**：`RedirectingPrintStream`/`FilteringPrintStream`/`WrappedPrintStream` 将 System.out/err 重定向到 logger 或按 INFO/ERROR 过滤
- **LoggerTester**：`testPerformance` 开关，在配置前后各跑一批消息并打结果

## 5. 网络 / 数据驱动 / 配置 / datagen

无网络、无 datagen。配置即 nightconfig TOML（`config/asynclogger.toml` + `config/asynclogger/*.toml`），不依赖 MC 的 config API，故能覆盖 1.8.9~26.1 全版本。

## 6. Mixin

配置 `src/mod-src/resources/asynclogger.mixins.json`（package `me.decce.asynclogger.mixins`，`required: true`，`compatibilityLevel: JAVA_17`，client/server 各一个 `defaultRequire:1`）。`mixins/ClientMainMixin.java:14` — `@Inject(method="main", at=@At("HEAD"))` 注入 `net.minecraft.client.main.Main`，注释说明 NeoForge 下 FML 会在进入 main 前重配 logger，故需再次 `LoggerConfigurator.configure()`；同目录还有服务端对应 `ServerMainMixin`。

## 7. 值得学的 5 条做法

1. 用类加载器注入把核心库塞进 log4j 的类加载器，绕开早期初始化顺序/模块可读性问题（`Bootstrapper.java:21-38`、`transform/ClassLoaderHandler.java:30-48`）——适用于要在别人类加载器里加载自定义类的场景。
2. 配置类"字段 + @Comment/@Key 注解 → 反射读写 TOML"，自动生成带注释的完整配置文件（`core/.../AsyncLoggerConfig.java`、`ConfigLoader.java:112-155`）——适合自研轻量配置。
3. 过滤提供两级挂载点，把"零调用者开销"与"省去 LogEvent 创建"的取舍交给用户（`LoggerConfigurator.java:163-175`）。
4. 单例标志 + 允许重复 configure，容忍加载器多次重配 logger 的时序（`LoggerConfigurator.java:99-105`）——处理"mod 被其他框架反复初始化"。
5. 内置 `testPerformance` 自测把性能声明变成可复现日志（`LoggerTester.java` + README 基准表）——库模组宣传性能时的可信做法。
6. Stonecutter + 源码注释预处理（`//? if neoforge && <1.21.9`）在单文件维护多版本多加载器代码。

## 8. 公开 API

`me.decce.transformingbase` 的 core/service 是作者自用的"跨加载器早期 bootstrapping 基座"（`loadCoreClasses`、`expandModuleReads`、`removeModClassesFromServiceLayer`），未构成对外 API；同作者的 Ixeris 等 mod 复用该基座，但本仓库未暴露扩展点。
