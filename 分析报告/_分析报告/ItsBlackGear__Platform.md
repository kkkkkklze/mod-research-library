# ItsBlackGear/Platform 源码分析报告

## 1. 基本信息
- Mod 名 Platform（跨平台库/前置）；mod_id `platform`；作者 ItsBlackGear
- 版本：`gradle.properties` mod_version=1.2.8，`forge/src/main/resources/META-INF/mods.toml` version=1.2.7（不一致）
- 目标 MC 1.19.2；加载器 Fabric（loader 0.15.9、fabric-api 0.77.0+1.19.2）+ Forge（43.0.8），`enabled_platforms=fabric,forge`
- Gradle：Architectury（architectury-plugin 3.4-SNAPSHOT、dev.architectury.loom 1.7-SNAPSHOT）、shadow 8.1.1 用于打包 common 进 forge；Java 17；Parchment 2022.11.06（`build.gradle:36-40`）
- 许可证 LGPLv3（LICENSE.md、mods.toml）
- 编译依赖：night-config core/toml 3.6.0（自带配置系统）、mixinextras-common 0.3.5、fabric-loader 仅用于 `@Environment` 注解（`common/build.gradle:9-14`）

## 2. 源码规模与包结构
- 159 个 .java / 8487 行（实测），common/fabric/forge 三层 + `@ExpectPlatform` 配对实现
- 主要包：`core/util/config` 9、`core/mixin/access` 9、`core/helper` 8、`common/worldgen/placement/parameters` 6、`core/events` 5、`core/network/base` 4
- 最大文件：SimpleConfigSpec 612、ConfigBuilder 284、ModConfig 217、SimpleConfigBuilder 213、CreativeTabs 200、Environment 196、ConfigFileTypeHandler 177、fabric FogRendererMixin 177、ModInstance 146
- 快照资源：三份 mixins.json、`platform.accesswidener`、`META-INF/mods.toml`；**无 fabric.mod.json**（未确认是否裁剪）

## 3. 入口与注册
`common/.../platform/Platform.java`：
```java
public static final ModInstance INSTANCE = ModInstance.create(MOD_ID).build();
public static void bootstrap() {
    INSTANCE.bootstrap();
    MessageHandler.bootstrap(); ConfigLoader.bootstrap(); BiomeManager.bootstrap();
}
```
Fabric 入口 `fabric/.../PlatformFabric.java`（ModInitializer → `Platform.bootstrap()` + FabricClientEvents/FabricCommonEvents/ServerLifecycle）；Forge 入口 `forge/.../PlatformForge.java`（`@Mod`）。
- 注册框架自研：抽象类 `core/CoreRegistry.java` + 两个 `@ExpectPlatform create(...)`，Fabric 立即 `Registry.register`（`fabric/.../CoreRegistryImpl.java:31-36`），Forge 推迟到 `bootstrap()`；`core/helper/` 提供 BlockRegistry（block+BlockItem 一次注册）、ItemRegistry、EntityRegistry、BlockEntityTypeBuilder、ParticleRegistry、SoundRegistry、DataSerializerRegistry 等封装。

## 4. 核心系统
1. 平台抽象 `core/Environment.java`（196 行，全部 `@ExpectPlatform` 静态方法：isClientSide/isProduction/hasModLoaded/getModVersion/getCurrentServer/getGameExecutor/getGameDir/getConfigDir/registerSafeConfig/getLoader）；全仓共 44 个 `@ExpectPlatform` 方法，fabric/forge 各写 Impl。
2. `core/ModInstance.java` + `ParallelDispatch`（fabric 实现 `FabricParallelDispatch`）：Builder 风格四段式回调 common/postCommon/client/postClient，`ModInstanceBuilderImpl` 按端决定是否跑 client 段。
3. 网络框架 `core/network/`：`MessageHandler.java:8` 建 `NetworkChannel(MOD_ID, 1, "networking")`，`PacketRegistry`（`@ExpectPlatform`）负责通道/包注册与发送；`base/Packet`、`PacketHandler`（encode/decode/handle）、`PacketContext.apply(player, level)`、`NetworkDirection`；`NetworkChannel` 提供 sendToServer/sendToPlayer/sendToPlayersInLevel/sendToAllLoadedPlayers/sendToPlayersInRange。
4. 自带配置文件系统 `core/util/config/`：把 Forge Config 移植到 common（ConfigBuilder 接口 + SimpleConfigBuilder/SimpleConfigSpec + ModConfig + ConfigTracker + ConfigFileTypeHandler），`ServerMainMixin.java:15-22` 注入 `net.minecraft.server.Main#main`（目标 `Util.startTimerHackThread()`）加载 SERVER 配置，含 `ConfigSyncPacket` 同步。
5. 创意标签与集成 `common/CreativeTabs.java`（`MODIFICATIONS` 列表 + `CreativeModeTabMixin` 注入 `CreativeModeTab#fillItemList` TAIL 插入物品）、`common/integration/`（BlockIntegration 改 AxeItem STRIPPABLES/ShovelItem FLATTENABLES、MobIntegration、TradeIntegration、VillagerLevel）、`common/worldgen/`（BiomeManager/BiomeModifier/placement 参数）、`client/`（GameRendering 雾效、ParticleFactories、RendererRegistry、animator、model）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：见 4.3，含 `ConfigSyncPacket`（服务端配置下发）。
- 配置：自有系统，`Environment.registerSafeConfig/registerUnsafeConfig` 为对外入口。
- 数据驱动：`common/data/TagRegistry`、`LootModifier`（loader 各写 Impl，forge 用 `@Mod.EventBusSubscriber`）。
- datagen：无（仓库内无 datagen 类）。

## 6. Mixin
- `common/src/main/resources/platform-common.mixins.json`：9 个 `access.*` accessor + `common.BlockEntityTypeMixin/CreativeModeTabMixin/OverworldBiomeBuilderMixin/ShearsItemMixin/SwordItemMixin` + `config.ServerMainMixin` + 3 个 client mixin
- `fabric/src/main/resources/platform.mixins.json`：5 个 + 7 个 client（含 177 行 `FogRendererMixin`）；`forge/src/main/resources/platform.mixins.json`：仅 `client.MinecraftMixin`（forge 用 `mixinConfig` 在 build.gradle 声明）
- `common/src/main/resources/platform.accesswidener`：放行 WoodType 构造/register、`Sheets.createSignMaterial`、`AxeItem.STRIPPABLES`、`ShovelItem.FLATTENABLES`、`FireBlock.setFlammable`、`Registry.registerSimple` 等

## 7. 值得学的 5 条做法
1. 用 `@ExpectPlatform` + 抽象基类（`CoreRegistry`/`ModInstance`）把“注册时机差异”（Fabric 立即注册 vs Forge 事件注册）收进一处，业务代码只调公共 API。
2. `ModInstance` 四段式生命周期（common/postCommon/client/postClient + ParallelDispatch）让跨端初始化顺序可声明。
3. 把 Forge Config 整套 API 复刻到 common（`ConfigBuilder`/`SimpleConfigSpec`），使配置文件系统能跨端复用并用 ServerMainMixin 解决服务端配置加载时机。
4. 用 accesswidener + mixin accessor 暴露原版私有成员（如 `Registry.registerSimple`）而不是反射，跨端一致。
5. 对外 API 全部走 `core/helper/*Registry` 门面（如 BlockRegistry 一次注册 block+BlockEntityType+Item），降低使用方样板代码。

## 8. 公开 API（库 mod）
- 包路径：`com.blackgear.platform.Platform`（MOD_ID/resource）、`core`（ModInstance、CoreRegistry、Environment、ParallelDispatch）、`core.helper`、`core.network`、`core.util.config`、`core.events`、`common`（CreativeTabs、integration、worldgen、entity、data、block、item）、`client`（GameRendering、RendererRegistry、ParticleFactories）
- 扩展点接口：`PacketHandler<T>`/`Packet<T>`/`PacketContext`（自定义包）、`ConfigBuilder`（配置定义）、各 `*Integration`（工具/刷怪/交易集成）、`BiomeModifier` 系列（群系修改）
- 外部 mod 接入方式：依赖 platform jar 后调 `Platform.INSTANCE`/`ModInstance.create(...)`、`CoreRegistry.create(Registry.X, modid)`、`new NetworkChannel(...)`、`Environment.registerSafeConfig(...)`；本库自身即通过同一 API 引导自己。注意其基于 Architectury 的 1.19.2 方案，迁移到 NeoForge 1.21.1 时可只借鉴“平台抽象 + 门面注册器”的思路。
