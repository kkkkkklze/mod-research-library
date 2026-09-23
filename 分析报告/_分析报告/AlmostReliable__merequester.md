# ME Requester 源码分析报告

## 1. 基本信息
- Mod 名 ME Requester / mod_id `merequester` / 作者 Almost Reliable / 版本 1.5.1 / 许可证 LGPL-3.0（`gradle.properties`）
- 目标：MC 26.1.2 + NeoForge 26.1.2.81（单模块 NeoForge-only，`src/main/java`），mixin `compatibilityLevel: JAVA_25`（`src/main/resources/merequester.mixins.json`）
- Gradle 插件：`net.neoforged.moddev 2.0.143` + `com.almostreliable.almostgradle 2.3.2`（`build.gradle.kts:1-4`）；该插件负责生成 `ModConstants`（源码中不存在此类文件，由 `almostgradle.buildconfig = ModConstants` 生成）与 run configs
- 编译依赖：AE2 `appliedenergistics2`（`api` 作用域，`aeVersion=26.1.10-beta`）、AE2WTLib API `de.mari_023:ae2wtlib_api`（`compileOnly`，`wtlibVersion=26.1.1-beta`，另 `localRuntime` 跑测试）、JEI（recipeViewers runConfig）与 GuideME（`guidebook/` + `guideme.ae2.guide.sources` 系统属性，`build.gradle.kts:10-33`）

## 2. 源码规模与包结构
实测 65 个 `.java`、4090 行，全部在 `src/main/java/com/almostreliable/merequester/`。包分布：`requester` 10（+`abstraction` 3、`status` 10）、`client` 3（+`abstraction` 3、`widgets` 5）、`compat/wtlib` 5、`network` 5、`core` 3、`terminal` 2、`mixin/accessors` 4。
最大文件：`client/abstraction/AbstractRequesterScreen.java` 325、`requester/RequesterBlockEntity.java` 284、`requester/Request.java` 231、`client/RequesterTerminalScreen.java` 196、`requester/StorageManager.java` 191、`client/widgets/NumberField.java` 186、`requester/abstraction/AbstractRequesterMenu.java` 170、`core/ModRegistration.java` 168。

## 3. 入口与注册
`MERequester.java:20`：`@Mod(ModConstants.MOD_ID)`，构造器只做三件事 `ModRegistration.init(modEventBus); PacketHandler.init(modEventBus); Config.init(modContainer);`。
注册集中在 `core/ModRegistration.java`：五个 `DeferredRegister`（`BLOCKS`/`ITEMS`/`BLOCK_ENTITY_TYPE`/`MENU`/`createDataComponents`），注册 `RequesterBlock(+Item)`、`RequesterBlockEntity`、`RequesterMenu`、`PartItem<RequesterTerminalPart>` 与 `RequesterTerminalMenu`，并在 `RegisterEvent`（`EventPriority.HIGH`，注释说明因为 AE2WTLib 在注册事件里关闭自己的注册器）里手动注册创造模式标签 `ResourceKey<CreativeModeTab>` + `BuildCreativeModeTabContentsEvent` 填充。数据组件带双向编解码：

```java
COMPONENTS.register("exported_requests", () -> DataComponentType.<List<Request.Component>>builder()
    .persistent(Request.Component.CODEC.listOf())
    .networkSynchronized(Request.Component.STREAM_CODEC.apply(ByteBufCodecs.list())).build());
```

AE2 侧集成：`AEBaseBlockEntity.registerBlockEntityItem(type, item)` + `block.setBlockEntity(...)`，能力注册用 `event.registerBlockEntity(AECapabilities.IN_WORLD_GRID_NODE_HOST, REQUESTER_ENTITY.get(), (r, _) -> r)`（`core/ModRegistration.java:137-146`）。

## 4. 核心系统
1. **AE 网格方块实体**（`requester/RequesterBlockEntity.java:63`）：`extends AENetworkedBlockEntity implements RequestHost, IGridTickable, ICraftingRequester`，在 `getMainNode()` 上 `.addService(IGridTickable/ICraftingRequester/IStorageWatcherNode)`，用 `MachineSource(this)` 作为网络操作来源，tick 返回 `TickRateModulation` 做自适应节流。
2. **请求状态机**（`requester/status/`）：`RequestStatus` 枚举 + 每状态一个类 `IdleState/CpuState/PlanState/ExportState/LinkState/BlockingState/MissingState`（`StatusState` 基类），`Request.clientStatus` 只用于客户端展示，真实状态存 BE（`Request.java:45-48` 注释明确分离）。
3. **库存感知与合成量计算**（`requester/StorageManager.java:19`）：`implements IStorageWatcherNode`，`updateWatcher` 时 `resetWatcher()` 重算 `knownAmount`，`onStackChange` 命中 `host.getRequestManager().getKey(i)` 时更新并清 `pendingAmount`；`computeAmountToCraft(slot)` 供请求端使用。
4. **请求数据模型**（`requester/Request.java`）：`implements ValueIOSerializable`（`ValueOutput/ValueInput` 存 `state/key/amount/batch/status`）+ 内嵌 `record Component` 同时提供 `Codec`（`AEKey.CODEC`）和 `StreamCodec`（`AEKey.STREAM_CODEC`），同一结构既做物品数据组件又做网络传输。
5. **客户端同步**（`network/RequesterSyncPacket.java`）：`record ... implements CustomPacketPayload`，`StreamCodec.composite(ByteBufCodecs.BOOL, ... VAR_LONG, Payload.PAYLOAD_STREAM_CODEC ...)`；`handle` 里判 `Minecraft.getInstance().screen instanceof AbstractRequesterScreen<?>` 才 `updateFromMenu`，并用 `createClearData()` 关界时清缓存。
6. **无线终端软兼容**（`compat/wtlib/WirelessTerminalCompat.java:28-121`）：单例 + 内嵌 `Guard`/`GuardClient` 静态内部类延迟加载（`isLoaded()` 判断），所有 wtlib 类只在 Guard 内引用，避免 `compileOnly` 依赖缺失时 `NoClassDefFoundError`；菜单/物品/能力/创造标签分别由 `init/initClient/registerWirelessTerminal/registerCapabilities/collectItems` 注入主注册流程。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络：`network/PacketHandler.java`，`event.registrar("1")`（协议号字符串）后 `playToClient(RequesterSyncPacket)`、`playToServer(RequestUpdatePacket/DragAndDropPacket)`，统一用 `wrapHandler` 把 handler 包进 `context.enqueueWork(...)` 保证主线程执行。
配置：`core/Config.java`，`ModConfigSpec.Builder().configure(CommonConfig::new)` 内嵌 `CommonConfig` 类，`requests`（1-64，决定数组长度）/`idleEnergy`/`requireChannel`，`COMMON` 类型注册在 ModContainer 上。
datagen：无。数据驱动：无 JSON 数据包，数据全部走数据组件 `exported_requests` 与 `ValueIOSerializable` 的 NBT/ValueIO 序列化。GuideME 手册以 `guidebook/merequester.md` 打包进 `assets/merequester/ae2guide`（`build.gradle.kts:38-42`）。

## 6. Mixin
`src/main/resources/merequester.mixins.json`（minVersion 0.8.5，全部 client，package `...mixin`）：`accessors.EditBoxMixin`（`@Accessor("isEditable")`）、`accessors.SlotMixin`（`@Accessor @Mutable` 的 `x`/`y`，用于重排槽位）、`accessors.WidgetContainerMixin`（AE2 的 `WidgetContainer#widgets`，`remap = false`）。另有 AT：`src/main/resources/META-INF/accesstransformer.cfg` 把 `AbstractContainerScreen#imageWidth/imageHeight` 放开为 protected-f（因 AE2 GUI 布局需要）。

## 7. 值得学的 5 条具体做法
1. 一个 record 同时给 `Codec` + `StreamCodec`（`requester/Request.java:206-230`），数据组件与网络包共用模型，NeoForge 上少写一套序列化。
2. 第三方软兼容用"单例 + 静态内部类 Guard"隔离类引用（`compat/wtlib/WirelessTerminalCompat.java:72`），`isLoaded()` 判断后才加载，彻底避免可选依赖缺失崩溃。
3. 注册事件优先级处理依赖方时序：`modEventBus.addListener(EventPriority.HIGH, ...)` 并注释说明原因（`core/ModRegistration.java:110`）。
4. 服务端整屏状态用"增量包 + 清缓存包"两用结构（`RequesterSyncPacket.createClearData()`），客户端只在打开对应 Screen 时消费。
5. 网格方块实体用"每状态一个类"替代 switch（`requester/status/`），每个 tick 逻辑独立可测，新增状态不改旧类。

## 8. 公开 API（库/前置类）
本体不是库；对外扩展点是 AE2 而非自己的 API。可复用片段：`requester/abstraction/RequestHost`/`RequestTracker`、`requester/abstraction/AbstractRequesterMenu`、`client/widgets/`（`NumberField`/`RequestWidget`/`StatusDisplay`/`StateBox`/`SubmitButton`）。下游接入靠 AE2 的 `AECapabilities`/`ae2wtlib_api`（`build.gradle.kts:28-29`）。
