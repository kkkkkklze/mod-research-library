# Bookshelf 源码分析报告

## 1. 基本信息
- Mod 名 Bookshelf / mod_id `bookshelf` / 作者 Darkhax / 许可证 LGPL 2.1（`gradle.properties`）
- 目标：MC 1.21.1（`minecraft_version_range=[1.21.1,1.22)`），NeoForge 21.1.209 + Fabric Loader 0.17.2（无 Forge 子模块，multiloader 三模块 `common`/`neoforge`/`fabric`，`settings.gradle`）
- Gradle 插件：`net.neoforged.moddev 2.0.112`、`fabric-loom 1.11-SNAPSHOT` + 自研 `buildSrc` 插件（`buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle`、`version-checker.gradle` 等）。Java 21
- 编译依赖：`compileOnly` mixin 0.8.5、mixinextras-common 0.4.0、JEI common-api（`common/build.gradle:9-18`）。它是被依赖方，发布到 `maven.blamejared.com`（common/fabric/neoforge/forge 四种坐标，见 README）

## 2. 源码规模与包结构
实测 166 个 `.java`、9626 行：`common` 150 文件/8642 行，`fabric` 8/485，`neoforge` 8/499。
包（`common/src/main/java/net/darkhax/bookshelf/common/`）：`api` 68（`data` 14、`util` 10、`commands` 6、`function` 6、`registry` 6、`text` 6、`network` 4、`entity` 4、`menu` 3）、`impl` 48、`mixin` 34（`access` 19、`patch` 15）。
最大文件：`api/util/TextHelper.java` 489、`api/data/codecs/map/MapCodecs.java` 485、`api/registry/ContentProvider.java` 347、`api/data/codecs/map/MapCodecHelper.java` 341、`api/function/ReloadableCache.java` 236、`neoforge/.../NeoForgeRegistryHelper.java` 201。

## 3. 入口与注册
`neoforge/.../NeoForgeMod.java:11` `@Mod(Constants.MOD_ID)`；`fabric/.../FabricMod.java` 实现 `ModInitializer`。两者都只做三件事（NeoForge 版）：

```java
BookshelfMod.getInstance().init();
Services.CONTENT.get().forEach(NeoForgeRegistryHelper::new);
if (Services.NETWORK instanceof NeoForgeNetworkHandler handler) eventBus.addListener(handler::registerPayloadHandlers);
```

注册框架不是 DeferredRegister，而是 **自定义适配器体系**：外部 mod 实现 `ContentProvider`（`api/registry/ContentProvider.java:54`，全部 default 方法：defineBlocks/defineItems/defineCommands/definePackets/defineLoadConditions…），实现类名写进 `META-INF/services/net.darkhax.bookshelf.common.api.registry.ContentProvider`，由 `Services.CONTENT`（`api/service/Services.java:25`）经 ServiceLoader 发现。每个 provider 生成一个平台 `RegistryHelper`，它把请求转发给 `impl/registry/adapter/` 下 19 个适配器（BlockRegistryAdapter、MenuTypeAdapter、PacketAdapter、VillagerTradeAdapter…），共享 `RegistrationContext`（命名空间、placeableBlocks、装饰陶罐图案，`api/registry/RegistrationContext.java:19-45`）。NeoForge 侧在 `RegisterEvent` 里按注册表懒执行，Fabric 侧直接注册（`FabricRegistryHelper.java`）。

## 4. 核心系统
1. **服务定位层**：`Services` 静态持有 `PLATFORM/GAMEPLAY/NETWORK` + `CONTENT` 懒加载列表，跨加载器只换实现类。
2. **注册/适配器层**：见上；`RegistryReference`+`CachedSupplier` 让注册结果可延迟解析（`api/registry/RegistryReference.java`）。
3. **网络层**：`AbstractPacket`（`api/network/AbstractPacket.java:36-51`）把 `CustomPacketPayload.Type` + `StreamCodec` + `Destination` 打包；`INetworkHandler` 由平台实现（NeoForge 用 `PayloadRegistrar` 按命名空间 `.optional()`，Fabric 用 `PayloadTypeRegistry` + `ClientPlayNetworking`）。发送前强制校验包已注册且玩家存在，否则抛异常。
4. **数据驱动层**：`ILoadCondition`/`LoadConditions`（`api/data/conditions/LoadConditions.java:19-35`）为 JSON 资源提供 `load_conditions` 通用条件（And/Or/Not/ModLoaded/OnPlatform/RegistryContains），dispatch codec 按 `ConditionType` 注册；配方管理器与资源重载被 mixin 挂钩。
5. **缓存与刷新**：`CachedSupplier`（懒加载一次）、`ReloadableCache`/`SidedReloadableCache`（重载后自动失效，按 `Level` 取值）。
6. **内容辅助**：`LootPoolEntryDescriptions` + `LootPoolEntryDescriber` 给原版掉落池条目加描述；村民交易辅助 `VillagerOffers/Buys/Sells`、`MerchantTier`；命令集 `impl/command/`（hand/font/rename/enchant/translate/structure/blocktag→itemtag，仅开发环境注册 DebugCommands）。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络与数据驱动见第 4 节；`MapCodecs`/`MapCodecHelper`/`StreamCodecs` 提供注册表键、标签、组件等常用 Codec 工厂，是写 datapack 兼容代码的实用工具箱。**配置：无**（`IPlatformHelper` 只暴露 config 目录路径）。**datagen：无**（仓库内 grep 不到 `GatherDataEvent`/`DataGenerator`）。

## 6. Mixin
`common/src/main/resources/bookshelf.mixins.json`（package `net.darkhax.bookshelf.common.mixin`，refmap `${mod_id}.refmap.json`，JAVA_18，client 段独立），另有 `bookshelf.fabric.mixins.json`、`bookshelf.neoforge.mixins.json`。
- `access.loot.*`（AccessorLootPool/LootTable/CompositeEntryBase/LootItem 等）——为读取内部字段而加访问器
- `patch.item.MixinCreativeModeTab` → `buildContents` TAIL，回调 `IItemHooks.addCreativeTabForms`
- `patch.locale.MixinClientLanguage` → `getOrDefault`/`has` HEAD cancellable（翻译兜底）
- `patch.level.MixinWalkNodeEvaluator` → `getPathTypeFromState`（INVOKE BlockState.getBlock 处，`IBlockHooks`）
- `patch.level.MixinRecipeManager` → `apply`/`replaceRecipes` RETURN；`patch.server.MixinReloadableServerResources` → `<init>` RETURN（重载缓存失效）
- `patch.client.MixinClientPacketListener`（`priority=1005`，`<init>` TAIL）

## 7. 值得学的 5 条
1. 用 ServiceLoader 做多加载器服务发现（`api/service/Services.java:29-39`）：外部 mod 只写一行 services 文件即可接入，API 与实现完全解耦。
2. 单接口 + 平台适配器覆盖 20 多种注册表（`ContentProvider.java` + `impl/registry/adapter/` 19 个适配器）：新增注册类型只加适配器，不动调用方。
3. 启动防呆：`BookshelfMod.detectInvalidContentProviders()`（`impl/BookshelfMod.java:31-46`）用 `Services.findServices` 反射读 services 文件，发现旧版 `IContentProvider` 直接抛异常阻止启动，避免难查的崩溃。
4. `ReloadableCache`/`CachedSupplier` 替代 `static final` 注册对象，天然处理数据包重载后的失效问题（`api/function/ReloadableCache.java`）。
5. NeoForge 网络注册按命名空间 `registrar(namespace).optional()`（`NeoForgeNetworkHandler.registerPayloadHandlers`），避免与未装客户端/服务端的连接被拒。

## 8. 公开 API（库 mod）
- 入口包：`net.darkhax.bookshelf.common.api`（子包 `registry`、`network`、`data`、`util`、`text`、`function`、`entity`、`menu`、`commands`、`block`、`item`）
- 扩展点：`ContentProvider`（注册一切内容，注册方式为 services 文件）；`INetworkHandler`/`IPacket`（自定义包）；`ILoadCondition`（自定义 JSON 加载条件）；`IGameplayHelper`/`IPlatformHelper`/`IRenderHelper`（平台能力）
- 接入方式：Gradle 依赖 `net.darkhax.bookshelf:bookshelf-common-1.21.1`（common/编译期）/`bookshelf-neoforge-1.21.1`/`bookshelf-fabric-1.21.1`（运行时），仓库 `https://maven.blamejared.com`；实现 `ContentProvider` 并在自己 jar 内提供 `META-INF/services/...ContentProvider` 文件即完成注册。`@InternalUse`/`@OnlyFor` 仅为阅读标记，非运行时约束。
