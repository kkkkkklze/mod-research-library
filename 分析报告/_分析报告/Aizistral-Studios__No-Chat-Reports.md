# No Chat Reports 源码分析报告

## 1. 基本信息

- **Mod 名 / mod_id**：No Chat Reports / `nochatreports`
- **作者**：Aizistral（contributors：Madis0/robotkoer、tibequadorian、xbjfk）
- **目标版本与加载器**：`gradle.properties:6-11` — `minecraft_version=26.2`、`fabric_loader_version=0.19.3`、`forge_version=65.0.0`、`neoforge_version=26.2.0.6-beta`；**三加载器共用一套 common 源码**（Fabric 为根模块，`:forge`、`:neoforge` 为子模块，见 `settings.gradle`）
- **Gradle 插件**：`net.fabricmc.fabric-loom 1.17-SNAPSHOT`、`com.modrinth.minotaur`、`net.darkhax.curseforgegradle`（`build.gradle:4-8`）
- **Java 版本**：25（`build.gradle:76-79`、`tasks.withType(JavaCompile)` release 25）
- **许可证**：WTFPL（`gradle.properties:23`）
- **编译依赖**：`fabric-api`、`modmenu`、`cloth-config-fabric`（`api` 方式暴露，`build.gradle:92-98`）；本质不依赖任何"前置库"，自身即是终端用户 mod，无公共 API 设计

## 2. 源码规模与包结构

`find -name '*.java'` = **65 个文件、3553 行**（含三平台，`common` 通过符号链接被重复计数一次）。

| 包（第 3 层） | 文件数 |
|---|---|
| `common.mixins.client` | 19 |
| `common.config` | 7 |
| `common.mixins.server` | 6 |
| `common.gui` | 6 |
| `common.core` | 5 |
| `common.platform`(+`events`) | 3+4 |
| `forge.mixins.client` / `neoforge.mixins.client` | 3 / 3 |

最大文件：`common/config/ClothConfigIntegration.java`(269)、`NCRConfigClient.java`(207)、`mixins/client/MixinChatScreen.java`(180)、`gui/FontHelper.java`(152)、`mixins/client/MixinChatListener.java`(123)、`core/ServerSafetyState.java`(117)、`config/JSONConfig.java`(108)。

## 3. 入口与注册

无 DeferredRegister / Registrate（本 mod 不加任何注册项），入口是**"平台适配器 + 单例门面"**：

- `common/platform/PlatformProvider.java` 定义 4 个方法：`isOnClient()` / `isOnDedicatedServer()` / `getMinecraftDir()` / `getConfigDir()`
- 各平台主类实现它并在构造/初始化时调 `NCRCore.awaken(this)`：
  - Fabric：`src/main/java/com/aizistral/nochatreports/fabric/NoChatReports.java`（`ModInitializer`）
  - NeoForge：`neoforge/src/main/java/com/aizistral/nochatreports/neoforge/NoChatReports.java:22`（`@Mod("nochatreports")`，同时注册 `IConfigScreenFactory` 扩展点）
- `common/NCRCore.java:27-48` 是唯一初始化点：

```java
public static void awaken(PlatformProvider platformProvider) {
    Preconditions.checkArgument(provider == null, "NCRCore already awake");
    provider = platformProvider;
    setup();                       // NCRConfig.load()
    if (provider.isOnClient()) clientSetup();   // NCRClient.setup()
}
```

## 4. 核心系统

**(1) 服务器安全等级评估** — `core/ServerSafetyLevel.java`（枚举 `SECURE / SINGLEPLAYER / UNINTRUSIVE / INSECURE / REALMS / UNKNOWN / UNDEFINED`）+ `core/ServerSafetyState.java`。全局静态状态：`AtomicBoolean ALLOW_CHAT_SIGNING`、`volatile ServerSafetyLevel current`、两个延迟回调队列 `RESET_ACTIONS` / `SIGNING_ACTIONS`。`setAllowChatSigning()` 在开启前会异步 `prepareKeyPair()` 拿密钥对再 `connection.setKeyPair()`。

**(2) 签名策略分层** — `core/SigningMode.java`：`DEFAULT / NEVER / ALWAYS / PROMPT / ON_DEMAND / NEVER_FORCED`。关键设计：`resolve()` 把 `DEFAULT` 解析成全局默认、`NEVER_FORCED` 解析成 `NEVER`；`isSelectable()` 让 `NEVER_FORCED` 不进 UI。per-server 覆盖存于 `config/NCRServerPreferences.java` 的 `HashMap<ServerAddress, SigningMode>`。

**(3) 服务器能力探测（协议层）** — `mixins/common/MixinJsonByteBufCodec.java:32,54` 注入 `net.minecraft.network.codec.ByteBufCodecs$34`（ServerStatus 的 JSON codec）的 `encode`/`decode`，在 JSON 里加/读 `"preventsChatReports": true`；结果存 `core/ServerStatusCache.java`（`ThreadLocal<Boolean>`）。这是"不需要对方装 mod 也能感知"的核心。

**(4) 服务端去签名** — `mixins/server/MixinServerCommonPacketListenerImpl.java:30,59` 在 `send()` 的 HEAD 把 `ClientboundPlayerChatPacket` 改写成 `ClientboundSystemChatPacket`（系统消息不走签名校验）；另有 `MixinServerboundChatPacket.signature()` 返回空、`MixinServerboundChatCommandSignedPacket.argumentSignatures()`、`MixinServerboundChatSessionUpdatePacket.handle()` 取消、`MixinPlayerList.verifyChatTrusted()` 放行、`MixinDedicatedServer.enforceSecureProfile()` 强制 false。

**(5) 客户端 UI 改造** — `mixins/client/MixinChatListener.java:94` 把 `ChatTrustLevel.NOT_SECURE/MODIFIED` 直接改回 `SECURE`；`MixinOptions.onlyShowSecureChat` 关掉；`MixinToastComponent.addToast` 屏蔽警告；`gui/UnsafeServerScreen`、`gui/RealmsWarningScreen` 自建警告页。

**(6) 遥测禁用** — `MixinYggdrasilUserApiService.java:22`（`newTelemetrySession` 取消）、`MixinMinecraft.allowsTelemetry`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无自定义 packet 注册、无 payload。唯一"网络行为"是通过 ServerStatus 的 JSON 传附加字段（见 4-3），序列化由 Mojang 的 codec 承担。
- **配置**：自研 `config/JSONConfig.java` 基类（Gson + 自定义 `ExclusionStrategy` 跳过静态/瞬态字段），文件落 `config/NoChatReports/`，另有 `ServerAddressAdapter`（`TypeAdapter<ServerAddress>`）实现 `host:port` 作为 JSON map key。三份配置：`NCRConfigCommon`（`convertToGameMessage`/`addQueryData`/`demandOnClient`/`enableDebugLog`）、`NCRConfigClient`（`showServerSafety`/`hideWarningToast`/`disableTelemetry`/`defaultSigningMode` 等 20 项）、`NCRServerPreferences`。`ClothConfigIntegration.java`(269 行) 是可选 GUI，`ACTIVE` 常量做软依赖探测。
- **datagen**：无。

## 6. Mixin

配置：`src/main/resources/mixins/common/nochatreports.mixins.json`（`required:true`，common/server/client 三组，客户端 19 + 服务端 6 + 通用 1）、`mixins/fabric/nochatreports-fabric.mixins.json`、`mixins/forge|neoforge/nochatreports-*.mixins.json`；Fabric 侧在 `fabric.mod.json` 声明，Forge/NeoForge 侧在 `mods.toml`/`neoforge.mods.toml` 用 `[[mixins]] config=` 声明。

代表性 hook：
- `MixinJsonByteBufCodec` → `ByteBufCodecs$34.encode/decode`（HEAD / RETURN，cancellable）
- `MixinChatListener` → `ChatListener.handleSystemMessage`（HEAD）、`evaluateTrustLevel`（HEAD）
- `MixinClientPacketListener` → `ClientCommonPacketListenerImpl.send`（HEAD）
- `AccessorClientPacketListener` → `@Accessor("commands")`、`@Accessor("suggestionsProvider")`、`@Invoker("setKeyPair")`
- 平台侧：`Connection.channelInactive`、`ClientHandshakePacketListenerImpl.onDisconnect`、`ClientCommonPacketListenerImpl.onDisconnect`（trigger `ClientEvents.DISCONNECT`）
- AT 文件 `neoforge/src/main/resources/META-INF/accesstransformer.cfg` 开了大量 client GUI 私有成员（`ClientPacketListener.signedMessageEncoder/chatSession`、`Screen.minecraft/font`、`Tooltip.message` 等）

## 7. 值得学的 5 条做法

1. **符号链接共享多平台源码**：`build.gradle:24-60` 的 `createLink()` 在构建时把 `src/main/java/.../common` 链进 forge/neoforge 模块，避免复制粘贴或复杂 sourceSet 配置。适用：中小型三加载器 mod。
2. **平台差异收敛成 4 个方法的接口**：`common/platform/PlatformProvider.java` + `NCRCore.awaken()`（`NCRCore.java:27`），所有 common 代码零平台引用。
3. **用 ServerStatus JSON 夹带自定义字段实现"单边可用"能力探测**：`MixinJsonByteBufCodec.java:32`，不需自定义 channel/payload，也不要求对端装 mod。适用：需要感知服务器配置的客户端 mod。
4. **枚举配置项的"分层解析"**：`SigningMode.resolve()`（`SigningMode.java:73`）让 `DEFAULT` 动态指向全局默认、`NEVER_FORCED` 降级为 `NEVER`，UI 层再靠 `isSelectable()` 过滤。适用：全局 + 每实例两级配置。
5. **延迟回调队列处理异步同意流程**：`ServerSafetyState.scheduleSigningAction()` / `scheduleResetAction()`（`ServerSafetyState.java:98-104`），把"用户点了同意后再重发消息"这类跨屏幕流程解耦。
6. **AT 文件优先于 accessor mixin**：`accesstransformer.cfg` 直接开放私有 GUI 字段，减少 mixin 数量。

## 8. 公开 API

非库 mod，无稳定公共 API。唯一可被第三方利用的扩展点是 `common/core/ServerDataExtension.java`（由 `MixinServerData` 在 `ServerData` 上实现），其他 mod 可通过它读取 `preventsChatReports()`；`ServerStatusCache` 同时也是跨类读取探测结果的入口。
