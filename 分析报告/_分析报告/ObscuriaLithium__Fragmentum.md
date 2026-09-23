# ObscuriaLithium/Fragmentum 源码分析报告

## 1. 基本信息

- Mod 名：Fragmentum（mod_name=Fragmentum，MOD_NAME 常量写 "FragmentumAPI"）；mod_id：`fragmentum`；作者：Obscuria。
- 目标版本（`gradle.properties`）：`minecraft_version=26.1`、`minecraft_version_range=[26.1, 26.2)`、`java_version=25`、`neoforge_version=26.1.0.1-beta`、`fabric_version=0.144.0+26.1`、`fabric_loader_version=0.18.4`。代码中已用 `net.minecraft.resources.Identifier`（非 ResourceLocation）。
- Gradle 插件（根 `build.gradle` + `settings.gradle`）：`net.fabricmc.fabric-loom 1.16-SNAPSHOT`、`net.neoforged.moddev 2.0.141`、`dev.obscuria.hekate 1.2.0`（作者自研插件，配合 `multiloader-loader`）。模块：`common` / `fabric` / `neoforge`（settings.gradle:32-34）。
- 许可证：Obscuria Ecosystem License (OEL) v1.3（自定义协议，非开源许可）。
- 编译依赖：NeoForge 侧 `jarJar` 打包 YACL `yet-another-config-lib`（neoforge/dependencies.gradle），common 侧 `api` 引入 `fuzs.forgeconfigapiport`；Fabric 侧 `include` YACL + ForgeConfigAPIPort。即 Fragmentum 把 YACL/ForgeConfigAPIPort 当作配置 API 的底座。

## 2. 规模与包结构

`find . -name '*.java' | wc -l` = **127**；总行数 **4920**（含全部模块）。最大文件：`core/common/_Easing.java`(236)、`_RichTextTags.java`(201)、`api/common/Color.java`(187)、`_RichTextLayout.java`(144)、`richtext/RichTextOptions.java`(143)、`_HSVColor.java`(130)、`_ComponentColor.java`(129)、`_PackedColor.java`(123)。

包分布（文件数）：`v2/api/common/registry`(12)、`v2/core/common/richtext`(9)、`v2/core/common/signal`(7)、`v2/core/common/registry`(7)、`v2/api/common/signal`(7)、`{neoforge,fabric}/service`(各 6)、`v2/api/common/richtext`(6)、`service`(6)。整体是 **api / core 双层 + per-loader service 实现**三类。

## 3. 入口与注册

`neoforge/.../NeoForgeFragmentum.java`（`@Mod(Fragmentum.MOD_ID)`）、`fabric/.../FabricFragmentum.java`（`ModInitializer`）都只做一件事：调用 `Fragmentum.init()`。真正的跨平台装配靠 JDK `ServiceLoader`（`common/.../Fragmentum.java:17-18`）：

```java
public static final Platform PLATFORM = ServiceLoader.load(Platform.class).findFirst().orElseThrow();
public static final FragmentumServices SERVICES = ServiceLoader.load(FragmentumServices.class).findFirst().orElseThrow();
```

`FragmentumServices`（registrar/factory/network/server/client/config 六个子服务，均已 `@ApiStatus.Internal`）由 `NeoForgeServices`、`FabricServices` 实现；各 loader 侧提供 `NeoForgeRegistrar`/`FabricRegistrar`、`*PayloadRegistrar` 等。

## 4. 核心系统

- **注册与延迟持有**：`v2/api/common/registry/*`。`FragmentumRegistry.registrar(modId)` → `Registrar` 接口提供 `registerItem/Block/Entity/BlockEntity/Particle/Attribute`、`createRegistry`、`createDataRegistry`、`createSyncedDataRegistry`；返回值统一为 `Deferred<T> extends Supplier<T>`，带 `holder()`。`Deferred.create(Holder)` 使"无注册表也能量产 Deferred"（`Deferred.java`）。`BootstrapContext` 是函数式注册上下文：`(name, Supplier<T>) ->` 绑定 RegistryKey + idResolver，适合数据驱动批量注册。
- **API/Core 命名约定**：公开接口在 `v2/api/**`，实现类在 `v2/core/**` 且一律以 `_` 前缀命名（`_Deferred`、`_RichText`、`_ConfigBuilder`、`_FragmentumProxy`），公开类只暴露 static 转发方法（`FragmentumFactory.newParticleType(...)` → `_FragmentumFactory`）。便于一眼区分"A 面/实现面"。
- **Signal 事件总线**：`v2/api/common/signal/Signal0..Signal5`（按参数个数分型），`Signal<T>` 接口提供重载的 `connect(source, oneShot, breaker, listener)` 与 `disconnect(Object source)`；实现 `_Signal`（`v2/core/common/signal/_Signal.java:14,19`）支持按 source 反注册、一次性监听、跳闸（breaker）信号。内置信号：`FragmentumServer.SERVER_STARTING/SERVER_SAVING/SERVER_STOPPING`（`v2/api/server/FragmentumServer.java:9-11`）。
- **富文本 DSL**：`RichText.process(Component|String, @Nullable Object source, RichTextOptions)` 走"词法分析→布局"流水线（`_RichTextLexer`/`_RichTextLayout`/`_RichTextBuilder`）；标签用注册表 `_RichTextTags.REGISTRY`（`Map<String, RichTextTag.Handler>`，`register()` 重复注册只警告不抛错），每个 handler 捕获异常并记日志，`source` 参数用于随时间/上下文变色的动画文本。
- **跨平台颜色与缓动**：`Color`（接口）+ `_Color/_PackedColor/_HSVColor/_ComponentColor`，`Easing` 内 40+ 条缓动曲线，供动画/渐变复用。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`v2/api/common/network/FragmentumNetworking` 静态门面（`sendTo/sendToAllTracking(level|entity)/sendToAll/sendToServer/reply`），注册用 `PayloadRegistrar.registerClientbound/Serverbound(Class, Type, StreamCodec, BiConsumer)`；`allowClientOnly()/allowServerOnly()` 在 NeoForge 侧落到 `registrar.optional()`。`reply` 依赖 `NeoForgeNetworking.replyConsumer` 静态字段：处理器执行前写入 `context::reply`、执行后置 null（`NeoForgePayloadRegistrar.java`），即"只能在 handler 同步栈内回复"，需注意并发安全（该字段非线程隔离）。
- 配置：`v2/api/config/ConfigBuilder`（`create(fileName)`、`comment/pushCategory/defineBoolean/defineInt/defineDouble/defineString/DefineEnum/defineList`、`buildClient/buildCommon/buildServer(modId)`），经 `ConfigService` 落到 NeoForge `ModConfigSpec`。注意 common 接口 `ConfigService` 直接 import `net.neoforged.neoforge.common.ModConfigSpec`，跨平台抽象未完全隔离。
- 数据驱动：`createDataRegistry` / `createSyncedDataRegistry(registryKey, codec[, networkCodec])`，用 Mojang `Codec` 声明式注册。
- datagen：NeoForge 侧 `runs.data`（`--mod --all --output src/generated/resources`，neoforge/build.gradle），无独立 datagen 子系统。

## 6. Mixin

三份配置：`common/src/main/resources/fragmentum.mixins.json`（MixinMinecraftServer、MixinServerPacksSource、client.MixinCreateWorldScreen、client.MixinMinecraft）、`fragmentum.fabric.mixins.json`、`fragmentum.neoforge.mixins.json`。

代表性 hook：
- `mixin/MixinMinecraftServer.java`：`@Inject` 到 `runServer` 中 `buildServerStatus()` 调用点（发 SERVER_STARTING）、`saveEverything`、`stopServer`（SERVER_STOPPING）。
- `mixin/MixinServerPacksSource.java`：`@ModifyArg` 改 `PackRepository.<init>` 的 `RepositorySource[]`，用 `ArrayUtils.addAll` 插入内置数据包源（自定义 `PackType.SERVER_DATA` 包层）。
- `neoforge/.../MixinClientTooltipComponentManager.java`：`@Inject(method="createClientTooltipComponent", at=@At("RETURN"), cancellable=true)` + `remap=false`，把自定义 `TooltipComponent` 映射成 `ClientTooltipComponent`（Fabric 侧对应改 `ClientTooltipComponent` 构造）。

## 7. 值得学的做法

1. 用 `ServiceLoader` 做多 loader 装配，主类保持为空壳（`Fragmentum.java:17-18`，场景：multiloader 库）。
2. 公开 API 与实现类用目录 + `_` 前缀双隔离（`v2/api/**` vs `v2/core/_Xxx`，场景：库模组对外接口管理）。
3. 事件总线按参数个数分型（`Signal0..Signal5`）+ `source`/`oneShot`/`breaker` 三件套（`_Signal.java:14,19`，场景：自研事件系统）。
4. 文本标签走"注册表 + 单 handler try/catch"，单标签出错不炸整条文本（`_RichTextTags.register/open/close`，场景：可扩展格式文本）。
5. `@ModifyArg` + `ArrayUtils.addAll` 往 `PackRepository` 注入数据包源（`MixinServerPacksSource.java`，场景：给所有存档注入内置数据包/配置）。

## 8. 公开 API（库模组）

对外入口集中在 `dev.obscuria.fragmentum.v2.api`：`FragmentumAPI`（modId/modName/platform）、`FragmentumRegistry`、`FragmentumNetworking`、`FragmentumFactory`、`FragmentumProxy`、`FragmentumServer`/`FragmentumServerRegistry`（命令注册）、`FragmentumClientRegistry`/`TooltipComponentRegistry`、`Integration.create(modId)`（`isLoaded/getIfLoaded/runIfLoaded/runIfMissing` 软依赖探测）、`RichText`、`ConfigBuilder`。README 明确声明：本模组只服务 Obscuria Collection 内部，**不面向第三方 modder 作为通用库**——评估是否依赖它时需注意。
