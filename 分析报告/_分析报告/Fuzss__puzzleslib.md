# Puzzles Lib 源码分析报告

> 分析对象：`Fuzss/puzzleslib` 分支 `1.21.1`（commit 601d5f8）。**重要前提**：本地 `_bulk/Fuzss__puzzleslib` 的默认分支 `main`（1c58b4a）只有 README/.github/versions.json 等文档文件，**不含任何源码**；源码按 MC 版本分散在 `1.21.1`、`1.20.1`… 等分支上。本报告内容取自 `1.21.1` 分支快照（解压到临时目录实测）。

## 1. 基本信息

- Mod 名：Puzzles Lib / mod_id：`puzzleslib` / 作者：Fuzs / 许可证：MPL-2.0
- 目标：MC 1.21.1，多加载器 `project.platforms=Common, Fabric, NeoForge`（`gradle.properties`），`mod.version=21.1.60`，`mod.group=fuzs.puzzleslib`
- Gradle：自研插件 `fuzs.multiloader.multiloader-convention-plugins-{root,common,fabric,neoforge}`（`project.plugins=1.1-SNAPSHOT`、`project.libs=1.21.1-SNAPSHOT`），底层为 Fabric Loom + NeoGradle；根 `build.gradle.kts` 仅一行 plugins
- 依赖：Fabric 侧 `modApi(fabricapi.fabric)` + `modApi(forgeconfigapiport.fabric)`（`Fabric/build.gradle.kts:8-10`）；Common 侧 `compileOnlyApi(sharedLibs.forgeconfigapiport.common)`
- **关键点**：`Common` 源码直接 import `net.neoforged.neoforge.common.ModConfigSpec`（`api/config/v3/ConfigCore.java:3`），Fabric 上靠 ForgeConfigAPIPort 提供该类——即它的配置 API 直接建立在 NeoForge 配置 API 之上

## 2. 源码规模与包结构（实测）

- `find . -name '*.java' | wc -l` = **909**；总行数 **65015**（`find … -exec cat {} + | wc -l`）
- 模块分布：`Common/src/main/java` 540 个、`Fabric/src/main/java` 226 个、`NeoForge/src/main/java` 143 个
- 包根 `fuzs.puzzleslib`；`api/` 按"版本号"分子包：`api/event/v1`(87)、`api/client/event`(45)、`api/core/v1`(33)+`v2`、`api/client/core`(21)、`api/client/gui`(19)、`api/init/v3`(18)+`v4`、`api/client/renderer`(17)、`api/data/v2`+`v3`(15)、`api/network/v3`(11)+`v4`(10)、`api/config/v3`(11)、`api/capability/v3`(11)、`api/util/v1`、`api/item/v2`、`api/attachment/v4`、`api/biome/v1`、`api/block/v1`、`api/container/v1`、`api/entity/v1`、`api/codec/v1`、`api/resources/v1`、`api/shape/v1` 等；实现集中在 `impl/*`（core、event、init、network、config、capability、attachment、client、data、item、resources、content）
- 最大文件：`NeoForgeEventInvokerRegistryImpl.java` 1207、`NeoForgeClientEventInvokers.java` 989、`api/init/v3/registry/RegistryManager.java` 952、`FabricEventInvokerRegistryImpl.java` 776、`api/client/data/v2/AbstractLanguageProvider.java` 643、`FabricClientEventInvokers.java` 625、`AbstractLootProvider.java`/`ReflectionHelper.java` 499、`impl/config/serialization/ConfigDataSetImpl.java` 483

## 3. 入口与注册

- Common 常量类 `impl/PuzzlesLib.java`（仅 MOD_ID/MOD_NAME/LOGGER）；真正的模组主体 `impl/PuzzlesLibMod.java:14-17`：

```java
public class PuzzlesLibMod extends PuzzlesLib implements ModConstructor {
    public static final NetworkHandler NETWORK = NetworkHandler.builder(MOD_ID)
            .optional().registerClientbound(ClientboundEntityCapabilityMessage.class);
    @Override public void onConstructMod() { ProxyImpl.get().registerEventHandlers(); }
```

- NeoForge 入口 `NeoForge/…/neoforge/impl/PuzzlesLibNeoForge.java:12-16`：`@Mod(PuzzlesLib.MOD_ID)` 构造器里 `ModConstructor.construct(PuzzlesLib.MOD_ID, PuzzlesLibMod::new)`；Fabric 入口 `Fabric/…/fabric/impl/PuzzlesLibFabric.java:12-16`（`ModInitializer`）写**同一行**调用。开发环境下额外构造 `common/development` 一个虚拟 ModConstructor
- **没有 DeferredRegister / Registrate**：`impl/core/ModContext.java` 按 modId 懒创建四件套（NetworkHandler、ConfigHolder、RegistryManager、CapabilityController），`ModContext.runBeforeConstruction()`（:107）冻结网络与配置并 `setupHandshakePayload`，`runAfterConstruction()`（:119）冻结 registryManager
- `RegistryManager`（:69 注释）"Registration is performed instantly on Fabric and is deferred on Forge"，由 `impl/init/RegistryManagerImpl.java` 统一实现，`RegistryManager.from(modId)` 是外部入口

## 4. 核心系统

**(a) ModConstructor + Context 注册模型**：`api/core/v1/ModConstructor.java` 用 ~20 个 `default void onXxx(Context)` 空实现暴露注册时机（`onRegisterGameplayContent`、`onRegisterEntityAttributes`、`onRegisterSpawnPlacements`、`onRegisterVillagerTrades`、`onRegisterGameRegistries`、`onAddDataPackFinders`、`onCommonSetup`…），配套 17 个 Context 类在 `api/core/v1/context/`；**v2 只新增 `BiomeModificationsContext`**（`api/core/v2/context/`），旧方法标 `@Deprecated` 指向新包

**(b) 跨加载器事件系统**：`api/event/v1/core/EventInvoker.java`（`lookup(Class[,context])` → 拉到加载器实现；`register(EventPhase, callback)`）、`EventInvokerRegistry.register(clazz, converter, joinInvokers)`、`EventPhase`/`EventResult`/`EventResultHolder`；实现为 `impl/event/core/EventInvokerImpl.java` + 加载器侧 `NeoForgeEventInvokerRegistryImpl`(1207)/`FabricEventInvokerRegistryImpl`(776)，把 87 个公共回调接口映射到原生事件；`impl/event/data/` 下 `EventMutable{Boolean,Int,Float,Double,Value}`/`EventDefaulted*` 把"可改返回值"包装成对象

**(c) ModContext 与握手/存在性检测**：每个 mod 生成独立握手 payload `ResourceLocation.fromNamespaceAndPath(modId, "handshake")`（`impl/core/ModContext.java:38`），抽象方法 `isPresentServerside()`/`isPresentClientside(ServerPlayer)` 由加载器实现；对外暴露为 `api/network/v4/NetworkingHelper.java:120-141` 的 `isModPresentServerside/Clientside`

**(d) 注册与自定义注册表**：`api/init/v3/registry/RegistryManager.java`(952) 覆盖 Block/Item/BlockEntity/EntityType/MenuType/Potion/Enchantment/DataComponentType/DamageType…；`api/init/v4/registry/RegistryFactory.java` 创建自定义 `Registry`（`create`/`createSynced`，取自 `ProxyImpl.get().getRegistryFactoryV4()`）；另有 `BlockSetFamily`/`BlockSetVariant`（木石套装族）、`tags/{TagFactory,BoundTagFactory}`

**(e) Capability / 数据附件**：`api/capability/v3/CapabilityController.java` + `data/{Entity,BlockEntity,Level,LevelChunk}CapabilityKey`、`SyncStrategy`、`CopyStrategy`、`CapabilityComponent`；`api/attachment/v4/DataAttachmentRegistry.java`/`DataAttachmentType.java`（impl 在 `impl/attachment/`）

**(f) Proxy / SPI 加载器抽象**：`api/core/v1/{Proxy,ModLoader,ModLoaderEnvironment,CommonAbstractions,ServiceProviderHelper}`；`ProxyImpl.get()` 是一切加载器相关实现的唯一入口，通过 `META-INF/services/fuzs.puzzleslib.impl.core.proxy.ProxyImpl`（Fabric、NeoForge 各一份）与 `ModLoaderEnvironment`、`ClientProxyImpl` 三份 ServiceLoader 文件挂接

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络有两代并存**：v3 = `api/network/v3/NetworkHandler.java`（`builder(modId)` → Builder，`ClientboundMessage`/`ServerboundMessage`/`MessageV3`/`PlayerSet` + 自研 `codec/StreamCodecRegistry`）；v4 = `api/network/v4/NetworkingHelper.java` + `message/{play,configuration}` 两阶段消息 + `MessageSender`、`impl/network/{NetworkHandlerRegistryImpl,CustomPacketPayloadAdapterImpl}`、`impl/network/codec/RecordStreamCodec.java`（用 record 组件反射式生成 StreamCodec）。配置阶段任务完成用 `NetworkingHelper.finishConfigurationTask(...)`
- **配置**：`api/config/v3/` 共 11 个文件——`ConfigCore`（注解驱动，可嵌套）、`ConfigHolder.builder(modId)`/`getHolder(Class)`（按 class 而非 ConfigType 存）、`ConfigDataHolder`、`ValueCallback`、`getDefaultNameFactory(type)` 生成 `<modId>-<type>.toml`；`serialization/ConfigDataSet` 支持"字符串列表 ↔ 注册表项"；`impl/config/ConfigHolderImpl`、`ConfigHolderRegistry`
- **datagen**：`api/data/v2`+`v3`（`AbstractLanguageProvider` 643 行、`AbstractLootProvider` 499、`AbstractTagAppender` 404）、`impl/data/SortingTagBuilder.java`，`api/client/data`（模型/语言相关 Provider）
- 仓库源码内**没有** `fabric.mod.json`、`*.toml`（mods.toml）、`*.mixins.json`：只有 `Common/src/main/resources/{pack.mcmeta,pack.png,puzzleslib.classtweaker}` —— 这些元数据由 Gradle 插件在构建期生成

## 6. Mixin

- **没有 mixin 配置 json 文件**，配置由 Gradle DSL 生成（`Common/build.gradle.kts:16-19`）：

```kotlin
multiloader { mixins {
    plugin.set("${project.group}.mixin.MixinConfigPluginImpl")
    mixin("AbstractMinecartMixin", "DataCommandsMixin", "EnchantCommandMixin")
    clientMixin("ClientSuggestionProviderMixin", "EditBoxMixin", "ModelBakeryMixin")
    serverMixin("DedicatedServerSettingsMixin", "EulaMixin") } }
```

- 类数量（实测）：Common 12 / Fabric 86 / NeoForge 16
- 代表性类与目标：`Fabric/…/mixin/LivingEntityFabricMixin.java`(460 行，补齐 Fabric 缺失的原生事件)；`Common/…/mixin/AbstractMinecartMixin.java`、`server/EulaMixin.java`、`client/ModelBakeryMixin.java`；NeoForge 侧有 `accessor(...)` 列表（`NeoForge/build.gradle.kts:14-20`）
- 另有 `puzzleslib.classtweaker`（ClassTweaker/AT 替代部分 mixin），以及 `MixinConfigPluginImpl`/`MixinConfigPluginFabricImpl`/`MixinConfigPluginNeoForgeImpl` 三个平台化 Mixin 配置插件

## 7. 值得学的 5 条做法

1. **用新包版本代替破坏性改动**：`api/network/v3` 与 `v4`、`api/init/v3` 与 `v4`、`api/core/v1` 与 `v2` 长期并存，旧接口只标 `@Deprecated` → 库升级不逼着下游改代码（`api/network/v3/NetworkHandler.java` vs `api/network/v4/NetworkingHelper.java`）
2. **把 mixin 声明搬进 Gradle DSL**：`build.gradle.kts` 里声明 mixin 类名，插件生成 json 与 mod 元数据，避免在每个版本手工维护 json（三份 `*/build.gradle.kts` 的 `multiloader { mixins {} }`）
3. **每个 mod 一个 ModContext + freeze 生命周期**：注册表/网络/配置在 `runBeforeConstruction` / `runAfterConstruction` 两个时机自动冻结，越权注册直接抛异常（`impl/core/ModContext.java:107-132`）
4. **不依赖 ModList 做存在性判断**：自己发一个 `<modId>:handshake` 载荷，服务端/客户端双向检测（`impl/core/ModContext.java:38,55-65`；`api/network/v4/NetworkingHelper.java:120`）
5. **API 层只放接口、实现全部下沉 + ServiceLoader SPI**：`api/…` 接口用 `ProxyImpl.get()`/静态工厂拿到 `impl/*` 实例，加载器差异通过 `META-INF/services` 三个文件注入 → 同一份 Common 源码同时给 Fabric/NeoForge 用
6. **事件返回值用可变包装类**：`impl/event/data/EventMutableBoolean` 等，避免回调里返回 null/解包样板（`impl/event/data/` 共 21 个类）

## 8. 公开 API 与外部接入方式（库模组）

- 公开包：`fuzs.puzzleslib.api.**`（`core/v1`、`event/v1`、`init/v3|v4`、`network/v3|v4`、`config/v3`、`capability/v3`、`attachment/v4`、`data/v2|v3`、`client/**`、`biome/v1`、`block/v1`、`entity/v1`、`item/v2`、`container/v1`、`chat/v1`、`codec/v1`、`resources/v1`、`shape/v1`、`util/v1`）
- 接入步骤：外部 mod 实现 `ModConstructor`（或较薄的 `BaseModConstructor`），在自己加载器入口（`@Mod` 构造器 / `ModInitializer#onInitialize`）调用 `ModConstructor.construct(MOD_ID, MyMod::new)`；随后用 `RegistryManager.from(modId)`、`EventInvoker.lookup(EventClass)`+`register`、`NetworkHandler.builder(modId)`（或 v4 `NetworkingHelper`）、`ConfigHolder.builder(modId)`、`CapabilityController`、`DataAttachmentRegistry` 注册内容
- 扩展点接口：`ModConstructor`、`ModConstructorImpl`、`EventInvokerRegistry`（可注册自定义事件实现）、`RegistryFactory`、`ContentRegistrationFlags`（声明需要加载器侧额外注册的内容，缺失时 `throwForFlag`）
- 下游实例：Fuzss 自己的 `Fuzss__configureddefaults`、`mutantmonsters`、`visualworkbench`、`pickupnotifier` 等 mod 均以此为前置
