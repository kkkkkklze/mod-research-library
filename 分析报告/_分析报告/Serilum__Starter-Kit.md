# Serilum/Starter-Kit 源码分析报告

## 1. 基本信息
- Mod 名 Starter Kit；mod_id `starterkit`；作者 Serilum（Rick South）；mod 版本 8.1（`neoforge.mods.toml`）
- 目标 MC 26.2（`minecraft_version=26.2`、`neo_form_version=26.2-1`、java_version 25）
- 加载器：Fabric（fabric-api 0.152.1+26.2、loader 0.19.3）+ Forge 65.0.0 + NeoForge 26.2.0.1-beta，三端同仓
- Gradle：fabric-loom 1.15-SNAPSHOT + moddev 2.0.141；自研 `buildSrc` 约定插件 multiloader-common / multiloader-loader（与 YUNGs 同源思路）
- 许可证 **All Rights Reserved**（`license.md`、mods.toml）→ 只能读思路，不可抄代码
- 编译依赖：**Collective 8.29 为必需前置**（`collective-common`/`collective-fabric`，`Common/build.gradle:22-23`、`Fabric/build.gradle:19-20`）；Fabric 另加 modmenu 20.0.0-beta.2（配置屏入口）

## 2. 源码规模与包结构
- 39 个 .java / 3547 行（实测）：Common 25、Fabric 4、Forge 5、NeoForge 5
- 包（Common）：`inventory` 5、`functions` 6、`networking.packets` 5、`data` 4、`events` 2、`util` 2、`cmds`/`config`/`networking` 各 1
- 最大文件：StarterKitAbstractContainerScreen 597、StarterGearFunctions 414、CommandStarterkit 387、StarterKitInventoryScreen 251、StarterClientFunctions 211、StarterDataFunctions 197、StarterKitInventoryMenu 195
- 资源：`Common/src/main/resources` 下 `META-INF/mods.toml`、`META-INF/neoforge.mods.toml`、`starterkit.mixins.json`（同一份 Common 资源供三端 jar 使用）；**无 fabric.mod.json**（未确认是否裁剪）

## 3. 入口与注册
`Common/.../ModCommon.java:8-20`：
```java
public static void init() { ConfigHandler.initConfig(); registerPackets(); load(); }
private static void load() { StarterDataFunctions.initConfigFolders(); StarterGearFunctions.processKitFiles(); }
```
三端入口模式完全一致（`ModFabric.java:23-32`、`ModForge.java`、`ModNeoForge.java:21-32`）：`ShouldLoadCheck.shouldLoad(MOD_ID)` → `setGlobalConstants()` → `ModCommon.init()` → loader 专属配置屏/事件注册 → `RegisterMod.register(NAME, MOD_ID, VERSION, ACCEPTED_VERSIONS)`（均为 Collective 的 API）。
- 注册内容：网络包（`networking/PacketRegistration.java` 链式 `Network.registerPacket(...)`，5 个包）、命令（`CommandStarterkit.register` 挂 Fabric `CommandRegistrationCallback` / NeoForge `RegisterCommandsEvent`）、配置屏扩展点（NeoForge `IConfigScreenFactory`、Forge `ConfigScreenHandler.ConfigScreenFactory`、Fabric ModMenu）。
- 无 DeferredRegister、无 @AutoRegister：本 mod 不注册任何原版注册表对象（无方块/物品），只处理数据与 UI。

## 4. 核心系统
1. 网络（全委托 Collective）：包类自带 `static CHANNEL = Identifier.fromNamespaceAndPath(MOD_ID, ...)` + `encode/decode/handle(PacketContext<>)`（`networking/packets/ToServerSendKitChoicePacket.java`）；发送用 `Dispatcher.sendToClient/sendToServer`；`ToClientReceiveKitDataPacket.java` 用 `buf.writeMap` 手写 lambda 并注释“因 NeoForge 上二义性”不使用方法引用。
2. 客户端 mod 存在性握手：`ToClientAskIfModIsInstalledPacket` → 客户端置 `VariablesClient.waitingForAnnouncement`，在 `StarterClientEvents.onClientTick` 等到 `mc.getConnection() != null` 才回 `ToServerAnnounceModIsInstalledPacket`（避开 NeoForge `EntityJoinLevelEvent` 时连接为空的坑）→ 服务端记录 UUID 并下发 kit 数据 → 客户端据 `openChooseKitScreen` 打开选择界面。
3. 数据驱动 kit：kit 定义就是配置文件（`config/starterkit/` 的 kits/inactiveKits/descriptions 目录，`.txt` 内为 gear 字符串），运行时读入 `Variables.starterGearEntries`/`starterKitDescriptions`（HashMap<String,String>）；`StarterDataFunctions.processRetroConfig` 自动迁移旧版 `starterkit.txt` 结构；`StarterDefaultKitFunctions` 生成 Default/Archer/Lumberjack/Witch 默认 kit。
4. 首次加入追踪：世界 `data/tracking.json`，结构 `Map<"singleplayer"|"multiplayer", Map<worldName|UUID, Boolean>>`（`data/Constants.java:23`）；`processExistingTrackingData` 扫 `world/playerdata/*.dat` 补录老玩家；`StarterCheckFunctions.shouldPlayerReceiveStarterKit` 单人按世界名、多人按 UUID 判定；`StarterServerEvents.onSpawn` 仍兼容 `entityTags` 里的 `collective.firstJoin.<modid>` 旧标记。
5. 客户端套装编辑 GUI：`inventory/StarterKitAbstractContainerScreen`(597) + `StarterKitInventoryScreen`(251) + `StarterKitInventoryMenu extends AbstractCraftingMenu`(195，含背包/护甲/副手槽位常量与 recipe book 变体)，配合 `StarterClientFunctions` 暂存/还原玩家原装备。
6. 配置：`config/ConfigHandler extends DuskConfig`，用 `@Entry` 静态字段声明 7 项开关 + `configMetaData` 写注释，`DuskConfig.init(NAME, MOD_ID, ConfigHandler.class)` 一次性初始化。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：5 个自建包（2 上行 / 3 下行），序列化全部手写 FriendlyByteBuf，无 codec、无 StreamCodec。
- 配置：Collective `DuskConfig` 统一读写 + 三端配置屏集成（见 3、4.6）。
- 数据驱动：kit 文件来自 config 目录（非数据包）；运行期用 Gson 读写 `tracking.json`（`Constants.gson`/`gsonPretty`）。
- datagen：无。

## 6. Mixin
`Common/src/main/resources/starterkit.mixins.json` 的 `mixins/client/server` 三个数组**全为空**，`compatibilityLevel: JAVA_25`，`injectors.defaultRequire: 1`。即本 mod 完全不使用 mixin，跨端差异靠 Collective 的事件抽象 + 各 loader 事件转接层吸收。

## 7. 值得学的 5 条做法
1. Common 里只放纯逻辑，loader 子工程只做“事件转接”：`NeoForgeStarterServerEvents`/`ForgeStarterServerEvents` 的 `@SubscribeEvent` 方法一行调用 `StarterServerEvents.onSpawn(...)` 等（`NeoForgeStarterServerEvents.java`），Common 永不 import loader 类。
2. 客户端可选性设计：先问后答的握手包决定“走 GUI 选套装”还是“聊天命令选套装”，客户端没装 mod 也不影响发套装（`StarterGearFunctions.initStarterKitHandle` 里 100 tick 后兜底 `chooseOrGiveStarterKit`）。
3. “是否首次加入”用世界存档文件（tracking.json）+ 扫描 playerdata 补录，而非纯 NBT/entityTag，配合旧 tag 兼容分支。
4. 配置目录结构升级自动化：`processRetroConfig()` 检测旧 `starterkit.txt` 并搬运成新目录结构（`StarterDataFunctions.java`），老用户无感。
5. 资源集中放 `Common/src/main/resources`（含两份 mods.toml 模板），由 `buildSrc/src/main/groovy/multiloader-common.gradle` 的 `processResources` 用 `expandProps` 为每个 loader 展开同源元数据 + `filesMatching(['fabric.mod.json','*.mixins.json'])` 做 JSON 转义。

## 8. 与 Collective（前置库）的耦合
本 mod 是 Collective 8.29 的消费范例，值得作为“库模组 API 该长什么样”的参考：`collective.config.DuskConfig`（`@Entry` + `DuskConfigScreen`）、`collective.check.ShouldLoadCheck/RegisterMod`、`collective.implementations.networking.api.Network/Dispatcher` 与 `data.PacketContext/Side`、`collective.functions.GearFunctions/ItemFunctions/MessageFunctions/TaskFunctions/WorldFunctions`、`collective.data.GlobalVariables`、`collective.fabric.callbacks.CollectiveCommandEvents`（跨端命令事件抽象，绕开 Fabric/NeoForge 事件名差异）。
