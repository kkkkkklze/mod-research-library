# Sinytra/ForgifiedFabricAPI 源码分析报告

> 库/前置类项目：把 **Fabric API 移植到 NeoForge**（依赖 Sinytra 的 Forgified Fabric Loader）。当前快照目标 MC 26.1.2 / Java 25，构建脚本为 Kotlin DSL。

## 1. 基本信息

- 项目名：Forgified Fabric API（`settings.gradle.kts` `rootProject.name = "forgified-fabric-api"`）；maven group `org.sinytra.forgified-fabric-api`
- `gradle.properties`：`version=0.155.2`（跟随上游 Fabric API 版本号）、`minecraft_version=26.1.2`、`loader_version=0.18.4`、`installer_version=1.0.1`、`prerelease=false`；完整版本号由 `build.gradle.kts` 拼为 `$upstreamVersion+$versionMc+$implementationVersion`（本地额外加 `+local`）
- 构建插件：`net.neoforged.moddev`（ModDevGradle，`neoForge { enable { version = versionNeoForge; isDisableRecompilation = true } }`）+ `maven-publish` + `me.modmuss50.mod-publish-plugin`
- 关键依赖：`jarJar("org.sinytra:forgified-fabric-loader")` 且 `api(...)`（FFLoader 是运行底座，被内嵌又对外暴露）；`accessTransformers(project(":fabric-transitive-access-wideners-v1"))`
- 许可证：Apache-2.0（各模块源文件头部为 FabricMC 的 Apache 头）；仓库根为上游 fork，无独立 LICENSE 文件可见（未确认）
- 大量模块自定义版本号：`gradle.properties` 中 `fabric-networking-api-v1-version=6.3.1` 等，由 `getSubprojectVersion()` 生成 `版本+git短哈希+sha256Hex(versionMc)前2位`

## 2. 源码规模与包结构

- **1513 个 `.java`，共 130118 行**（`find . -name '*.java' -print0 | xargs -0 cat | wc -l`）
- 45 个 `fabric-*` 顶层模块（每个 = 一个独立可发布 jar）+ `deprecated`、`internal`、`fabric-api-bom`、`fabric-api-catalog` 四个元项目
- 单模块内部固定分层：`src/main/java/net/fabricmc/fabric/api/...`（公开 API）、`.../impl/...`（实现）、`.../mixin/...`（Mixin）；客户端代码单独放 `src/client/java`（由 `ffapi.neo-setup.gradle.kts` 把 `src/client/java` 挂到 main sourceSet），测试用 `src/testmod`、`src/testmodClient`
- 最大文件：`fabric-convention-tags-v2/.../ItemTagsGenerator.java` 944、`BlockTagsGenerator.java` 749、`api/tag/convention/v2/ConventionalItemTags.java` 678、`FabricEntityTypeBuilder.java` 630、`fabric-renderer-indigo/.../AoCalculator.java` 590、`MutableQuadView.java` 577
- 注意：本快照中**所有 `fabric.mod.json` 均缺失（find 计数 0）**，`accesswidener` 仅剩 1 个；因此下文关于元数据的事实来自读取它们的构建任务源码（`buildSrc/src/main/kotlin/org/sinytra/ffapi/task/GenerateModMetadataTask.kt`、`ffapi.neo-entrypoint.gradle.kts`）

## 3. 入口与注册

- **入口是代码生成的**：`buildSrc/src/main/kotlin/ffapi.neo-entrypoint.gradle.kts` 里 `GenerateForgeModEntrypoint` 解析模块的 `fabric.mod.json`，取出 `main/client/server` entrypoint，过滤出不存在的类，生成 `org/sinytra/fabric/<模块名>/generated/GeneratedEntryPoint.java`：
  ```java
  @net.neoforged.fml.common.Mod(GeneratedEntryPoint.MOD_ID)
  public class GeneratedEntryPoint {
      public static final String MOD_ID = "fabric_networking_api_v1";
      public static final String RAW_MOD_ID = "fabric-networking-api-v1";
      public GeneratedEntryPoint(net.neoforged.bus.api.IEventBus bus) {
          // Initialize client entrypoints
          if (net.neoforged.fml.loading.FMLEnvironment.getDist().isClient()) { new X().onInitializeClient(); }
      }
  }
  ```
  entrypoint 的 `a::b` 语法也支持（`createEntrypointCall`），modid 统一 `'-' → '_'`；每个 `sourceSet`（含 testmod）各自生成一份。
- **元数据注册**：`GenerateModMetadataTask` 把 `fabric.mod.json` 的 `id/version/environment/icon/authors/description/mixins/depends` 转成 `META-INF/neoforge.mods.toml`（`license` 缺省填 `All Rights Reserved`；`mixins` 数组转 `[[mixins]] config=`，`depends` 去掉 fabricloader/java/minecraft 并统一为 `required/*/NONE/BOTH`，再自动追加 neoforge 与 minecraft 版本区间约束）。`ffapi.neo-conversion.gradle.kts` 同时生成 `META-INF/accesstransformer.cfg` 与 `META-INF/interfaces.json` 到 `src/generated/<sourceSet>/resources`，jar 任务 `exclude("fabric.mod.json")`。
- **多模组并行装载**：`build.gradle.kts` 对每个子项目执行 `neoForge.mods.register(p.name) { sourceSet(p.sourceSets.main.get()) }`，有 `src/testmod` 的再注册 `<name>-testmod`；`neoForge.runs` 的 client/server 只加载非 test 模块。AT/接口注入通过 `MergeAccessTransformersTask` / `MergeInterfaceInjectionTask` 合并成 `merged.accesstransformer` / `merged.json` 后 `publish(...)`。

## 4. 核心系统

1. **事件总线（fabric-api-base）**：`Event<T>` 只有 `protected volatile T invoker` + `register` + `addPhaseOrdering`（`fabric-api-base/src/main/java/net/fabricmc/fabric/api/event/Event.java:36,47,63,88`），监听器被"折叠"成单个 invoker 直接调用，**没有订阅者列表的遍历开销**；`EventFactory.createArrayBacked(type, emptyInvoker, invokerFactory)`（`EventFactory.java:67-77`）在 0/1/2+ 监听器三种情况下分别返回空实现、直接返回该监听器、才真正合并；`createWithPhases(...)` 用有序 phase 组做优先级（`Event.java:63` `DEFAULT_PHASE`）。实现 `impl/base/event/ArrayBackedEvent.java` 用 `Map<Identifier, EventPhaseData>` + `NodeSorting.sort`（拓扑排序）维护 `sortedPhases`，`register` 时 `rebuildInvoker`。`EventFactoryImpl` 用 `MapMaker().weakKeys()` 收集所有事件以支持 `invalidate()`（`impl/base/event/EventFactoryImpl.java:35`）。`AutoInvokingEvent` 注解用于"上下文对象自己实现回调即自动触发"的场景。
2. **网络（fabric-networking-api-v1）**：`PayloadTypeRegistry<B extends FriendlyByteBuf>` 提供 `register(type, StreamCodec)` / `registerLarge(type, codec, maxPacketSize)`（超尺寸自动拆包，`api/networking/v1/PayloadTypeRegistry.java:46,63,84`），按 serverbound/clientbound × configuration/play 四个静态实例注册；发送侧 `ServerPlayNetworking`/`ClientPlayNetworking` 提供 `registerGlobalReceiver`、`registerReceiver(listener, type, handler)`、`canSend`、`getSender`、`send`（`ServerPlayNetworking.java:78,126,198,261,287`），并有 `PacketSender`、`PlayerLookup`、`FriendlyByteBufs`、`EntityTrackingEvents` 等辅助 API；实现走 `impl/networking/{AbstractChanneledNetworkAddon, ClientCommonNetworkAddon, *ConfigurationNetworkAddon, *LoginNetworkAddon}`，把 login/configuration/play 三阶段统一成 addon 链。
3. **API Lookup（fabric-api-lookup-api-v1）**：跨模组能力查询的通用解，`BlockApiLookup.get(Identifier, ApiClass, ContextClass)` + `registerForBlocks/registerForBlockEntity/registerFallback`（`api/lookup/v1/block/BlockApiLookup.java:44-104`），附带 `BlockApiCache` 与 `ApiLookupMap/ApiProviderMap`，实体/物品各有对应 Lookup——是 NeoForge Capability 的替代品，学它的"三级 fallback（方块实体→方块→全局）"设计。
4. **注册表同步（fabric-registry-sync-v0）**：`FabricRegistryBuilder`、`RegistryAttribute`、`RegistryEntryAddedCallback`、`RegistryIdRemapCallback`、`DynamicRegistries`/`DynamicRegistryView`，impl 侧 `FapiRemapBridge`、`RemapStateImpl`，Mixin `MappedRegistryAccessor/BaseMappedRegistryMixin/RegistryDataLoaderMixin`。
5. **数据附件（fabric-data-attachment-api-v1）**：`AttachmentRegistry`/`AttachmentType`/`AttachmentTarget`/`AttachmentSyncPredicate` + `GlobalAttachments`，同步包 `impl/attachment/sync/clientbound/ClientboundAttachmentSyncPayload`，存储 `AttachmentSavedData`（对应 NeoForge DataAttachment）。
6. **缩略/渲染与流体内部模块**：`fabric-renderer-indigo`（`AoCalculator` 等顶点/光照计算）、`internal/ffapi-fluid-types`（`FabricFluidTypes` + `CommonHooksMixin`，为 FFLoader 补 FluidType 语义）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见上，模块即 `fabric-networking-api-v1`；不做自定义封包框架外的序列化，全部基于原版 `CustomPacketPayload` + `StreamCodec`。
- 数据驱动：`fabric-convention-tags-v2`（datagen 生成 `c:` 约定标签，`src/datagen/java` 独立 sourceSet）、`fabric-resource-conditions-api-v1`、`fabric-loot-api-v3`、`fabric-tag-api-v1`、`fabric-recipe-api-v1`、`deprecated/fabric-resource-loader-v0`。
- 配置/元数据生成：无运行时配置文件；构建期生成 `neoforge.mods.toml`、`accesstransformer.cfg`、`interfaces.json`、入口类（见第 3 节）。
- 版本目录：`fabric-api-bom`（`java-platform`，把所有子项目塞进 `constraints`）与 `fabric-api-catalog`（`version-catalog`，`catalog { versionCatalog { library(name, "net.fabricmc.fabric-api:${proj.name}:${proj.version}") } }`）。

## 6. Mixin

- 每个模块自带 `<模块名>.mixins.json`（客户端用 `src/client/resources/<模块名>.client.mixins.json`），package 形如 `net.fabricmc.fabric.mixin.<域>`，`compatibilityLevel: JAVA_25`，`injectors.defaultRequire: 1`。
- `fabric-api-base.mixins.json`：`mixins: [BootstrapMixin, MappedRegistryMixin]`，并开启 `overwrites.requireAnnotations: true`（强制 overwrite 必须写 `@Overwrite` 注解）。
- `fabric-lifecycle-events-v1.mixins.json`：主表 13 个（`ChunkHolderMixin/ChunkMapMixin/EntityMixin/LevelMixin/MinecraftServerMixin/PlayerListMixin/...`），`server: [server.LevelChunkMixin]` 用 `server` 列表区分端，`injectors.maxShiftBy: 3` 放宽容错。
- 代表 hook：`fabric-registry-sync-v0` 注入 `MappedRegistry`/`RegistryDataLoader`；`fabric-lifecycle-events-v1` 注入 `PersistentEntitySectionManager`、`ServerLevelEntityCallbacksMixin` 等发实体加载事件；`fabric-api-base` 的 `BootstrapMixin`（`Bootstrap#bootStrap`）用于提前初始化 `EarlyRegistry`（`impl/base/registry/EarlyRegistry.java`）。
- 这些 mixin 配置最终由 `GenerateModMetadataTask` 写进生成的 `neoforge.mods.toml` 的 `[[mixins]]` 段，NeoForge 侧无需额外声明。

## 7. 值得学的 5 条具体做法

1. **AccessWidener → AccessTransformer 自动转换**：`buildSrc/src/main/kotlin/org/sinytra/ffapi/Aw2At.kt` 用 `net.fabricmc.classtweaker.api` 解析器把 `ACCESSIBLE→PUBLIC`、`EXTENDABLE/MUTABLE→PUBLIC+REMOVE`，产出 NeoForge 的 `accesstransformer.cfg`；跨加载器移植源码时可直接复用这套"语法翻译"思路（`GenerateAccessTransformerTask.kt`、`InterfaceInjection.kt` 同理处理接口注入）。
2. **由 `fabric.mod.json` 反向生成 `neoforge.mods.toml` 与入口类**：`GenerateModMetadataTask.kt` + `GenerateForgeModEntrypoint`（`ffapi.neo-entrypoint.gradle.kts`）让同一份元数据/入口声明跨两个加载器，生成物落在 `src/generated/<sourceSet>/` 并由 `generate`/`clean` 任务联动；多平台项目可用此法消灭手工同步。
3. **"折叠监听器成单 invoker"的事件设计**：`EventFactory.createArrayBacked(type, emptyInvoker, factory)` 的 0/1/多分支（`EventFactory.java:67-77`）+ `ArrayBackedEvent` 的 phase 拓扑排序，是低开销事件总线的教科书实现。
4. **按需自定义事件优先级**：`Event.addPhaseOrdering` + `NodeSorting.sort`（`impl/base/toposort/NodeSorting.java`，含环检测告警），比"注册顺序即执行顺序"更适合库模组。
5. **单模块独立版本号 + git 溯源**：`getSubprojectVersion()` 读取 `<模块名>-version` 属性并拼接该目录最近一次 commit 短哈希与 MC 版本哈希前 2 位，使 45 个子 jar 可独立发布且版本可追溯（`build.gradle.kts` 中 `getSubprojectVersion`）。

## 8. 公开 API / 扩展点（库项目）

- 公开 API 包根：`net.fabricmc.fabric.api.*`，按模块划分子域：`event`（`Event/EventFactory/AutoInvokingEvent`）、`networking.v1`（`ServerPlayNetworking/ClientPlayNetworking/PayloadTypeRegistry/PacketSender/PlayerLookup/context.PacketContext`）、`lookup.v1.{block,entity,item,custom}`、`attachment.v1`、`event.lifecycle.v1` 与 `client.event.lifecycle.v1`、`event.registry.*`（`FabricRegistry/FabricRegistryBuilder/RegistryEntryAddedCallback`）、`tag.convention.v2`、`object.builder.v1` 等。
- 实现类一律在 `net.fabricmc.fabric.impl.*`（如 `impl.base.event.ArrayBackedEvent`、`impl.networking.*NetworkAddon`），`Event` 标注 `@ApiStatus.NonExtendable`，扩展方式只有 `register` 监听与 `EventFactory`（`Event.java:29`）。
- 第三方接入方式：依赖 FFAPI 的内嵌 FFLoader（`org.sinytra:forgified-fabric-loader`）+ 目标模块 maven 坐标 `net.fabricmc.fabric-api:<模块名>:<version>`（`fabric-api-catalog/build.gradle` 的 version-catalog 与 `fabric-api-bom` 的 `java-platform` constraints 提供对齐版本）；NeoForge 侧的 modid 为 `fabric_<模块名>`（连字符转下划线），入口为 `org.sinytra.fabric.<name>.generated.GeneratedEntryPoint`。
- 额外内部模块：`internal/ffapi-fluid-types`（`org.sinytra.ffapi.impl.fluids.FabricFluidTypes`）、`fabric-transitive-access-wideners-v1`（只提供 build.gradle + 测试，AW 文件在本快照中缺失），以及 `deprecated/fabric-resource-loader-v0`。
