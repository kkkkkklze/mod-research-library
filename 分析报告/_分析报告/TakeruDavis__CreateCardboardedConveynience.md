# TakeruDavis/CreateCardboardedConveynience 源码分析报告

## 1. 基本信息
- Mod 名：Create: Cardboarded Conveynience；mod_id：`cardboarded_conveynience`（`gradle.properties`，archives_name `create-cardboarded-conveynience`）；作者 TakeruDavis。
- 目标：MC 1.20.1，**Architectury 三工程**（`common` / `fabric` / `forge`），Fabric Loader 0.17.2 + Fabric API 0.92.6，Forge 47.4.13。
- Gradle：`dev.architectury.loom 1.10-SNAPSHOT` + `architectury-plugin 3.4-SNAPSHOT` + `com.github.johnrengelman.shadow 8.1.1`（`build.gradle`）；Java 17；许可证 MIT（`forge/src/main/resources/META-INF/mods.toml`）。
- 依赖（谁提供 API）：Create `6.0.8-289`（Forge slim）/ `create-fabric 6.0.8.1`（Modrinth）、`net.createmod.ponder 1.0.91`、`flywheel 1.0.5`、**Registrate MC1.20-1.3.3 走本地 `libs/` jar**（注释：maven.tterrag.com 证书 2025-12-23 过期）、Architectury API 9.2.14、Fabric 侧 Porting Lib 2.3.13 十个模块、`forgeconfigapiport 8.0.0`、`milk-lib 1.2.60`、`reach-entity-attributes 2.4.0`、`mixinextras-forge 0.4.1`。`common` 只 `modCompileOnly` Create + Ponder。

## 2. 源码规模与包结构
- 55 个 `.java`，8250 行。包分布：`util` 11、`test` 8、`ponder` 8、`mixin` 7、`network` 5、`advancement` 4、`fabric/mixin` 3、`forge` 2、`fabric` 2、`forge/util` 1、`fabric/util` 1、`config` 1、根 1、遗留 1。
- 最大文件：`forge/.../test/ChuteTeleportGameTest.java` 858、`fabric/src/gametest/.../ChuteTeleportGameTest.java` 829、`ponder/FrogportDeliveryScene.java` 513、`ponder/BeltTunnelScene.java` 467、`util/ChuteTeleportHelper.java` 406、`mixin/ChainConveyorNametagRoutingMixin.java` 371。
- 遗留：`src/main/java/net/TakeruDavis/create_cardboarded_conveynience/mixin/BeltTunnelBlockMixin.java`（128 行，与 common 版不同，疑为废弃副本）。

## 3. 入口与注册
`common/.../CardboardedConveynience.java:13` 只做三件事：`ModConfig.load()`、`ModCriteria.register()`、`CardboardedNetworking.init()`。平台入口再包一层事件：
- Forge：`forge/.../CardboardedConveynienceForge.java` `@Mod`，`DistExecutor.unsafeRunWhenOn(CLIENT)` 内 `PonderIndex.addPlugin(new CardboardPonderIndex())`、`DismountHelper.registerPacketSender(...)`；用 `MinecraftForge.EVENT_BUS` 订阅 ServerTick（逐玩家 `ChuteTeleportHelper.tickPlayer`）、PlayerLoggedOut（重置 Pose）。
- Fabric：`fabric/.../CardboardedConveynienceFabric.java` `ModInitializer`，等价地用 `ServerTickEvents.END_SERVER_TICK` / `ServerPlayConnectionEvents.DISCONNECT`。
本 mod **不注册任何物品/方块**，是纯 mixin + 事件玩法扩展。

## 4. 核心系统
1. **链式传送带铭牌路由**（最值得看）：`mixin/ChainConveyorNametagRoutingMixin.java`。改 `ChainConveyorRidingHandler`：在 `clientTick` HEAD 做"延迟下马"（`@Unique shouldDismount` + `ci.cancel()`，注释说明为避免 mid-frame NPE），在 `updateTargetPosition` HEAD 分流"行进中检测到达 Frogport"与"路口选支"。门槛：`CardboardHelper.testForArmor` + 副手带自定义名名牌；`PackageItem.matchAddress(destination, port.filter())` 匹配。
2. **路口路由的服务端问答**：`network/RouteQueryC2SPacket` / `RouteResponseS2CPacket` + `util/RouteCache.java`（`cachedRoutes` Map、`pendingQueryJunction` 去重、`BlockPos.ZERO` 表示无路线并 `invalidate`），把 Create 的本地 sight-steering 换成服务端权威寻路，并**预查询**即将到达的路口。
3. **纸箱伪装穿越带式隧道**：`mixin/BeltTunnelBlockMixin.java` 注入 `BlockBehaviour.getCollisionShape`（HEAD，cancellable），用 `BeltTunnelShapes.getShape` 挖出内腔（`Shapes.join(base, box(2,-5,2,14,10,14), ONLY_FIRST)`，`ConcurrentHashMap` 缓存），Brass 隧道用 `brassTunnel.testFlapFilter` 四方向试空物品判断"是否有过滤"（保守策略），投射物白名单在 `util/TunnelPassthroughRegistry.java`（`LinkedHashMap` 保证子类先匹配：Trident→Arrow→Firework→Pearl→Potion→Snowball→FishingRod）。
4. **滑槽投送（Chute teleport）**：`util/ChuteTeleportHelper.java` 服务端每 tick 扫脚下滑槽链（`scanAndValidateChutePath`、`passesSmartChuteFilter`、`isValidExit`），冷却 20 tick、警告 40 tick；由两个平台入口的 server tick 驱动。
5. **Ponder 教程接入**：`ponder/CardboardPonderIndex.java` 实现 `PonderPlugin`，用 `helper.forComponents(create:xxx).addStoryBoard("cardboard/...", ..., sb -> sb.orderAfter("create","..."))` 把 4 个场景（disguise/belt_tunnel/chute/frogport）插到 Create 原场景之后。
6. **进度与跨平台抽象**：`advancement/ModCriteria.java` 注册 3 个 `CriteriaTriggers`（Disguise/FrogportDelivery/ChuteTeleport）；`util/DismountHelper.java` 用 `registerPacketSender` 让 common 代码调用平台实现的 `ChainConveyorPacketHelper`。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`network/CardboardedNetworking.java:19` 用 **Architectury `NetworkChannel.create(new ResourceLocation(MOD_ID,"main"))`**，`register(Class, encode, new, apply)` 注册 4 个包（FrogportArrival C2S、FrogportAnimationS2C、RouteQuery C2S、RouteResponse S2C）；S2C 按半径筛选 `level.getPlayers(...)` 后 `sendToPlayer`。
- 配置：手写 Gson JSON，写入 `Platform.getConfigFolder()/cardboarded_conveynience.json`（`config/ModConfig.java`，当前仅 `maxChutePathLength=384`），非 ModConfigSpec/Forge Config。
- datagen：无（仅有 GameTest 与 `gameteststructures`）。仓库未包含 `assets/`、`lang/`、`fabric.mod.json`（资源被裁剪，语言键由 Create 侧/发布包提供）。

## 6. Mixin
- 配置：`common/src/main/resources/cardboarded_conveynience-common.mixins.json`（`required:false`、`injectors.defaultRequire:0`、refmap `create-cardboarded-conveynience-1.20.1-common-common-refmap.json`），mixins 4 个 + client 3 个；`fabric/src/main/resources/cardboarded_conveynience-fabric.mixins.json` 3 个 client。Forge 侧 `forge/build.gradle` 里 `loom { forge { mixinConfig "cardboarded_conveynience-common.mixins.json" } }`。
- 代表性 hook：
  - `ChainConveyorRidingHandler.clientTick` @Inject HEAD（cancellable）、`updateTargetPosition` HEAD；`ChainConveyorRidingHandler.clientTick` 另有 `@ModifyVariable(at=STORE)`（`ChainConveyorRidingHandlerMixin`）。
  - `BlockBehaviour.getCollisionShape` @Inject HEAD（`BeltTunnelBlockMixin`）。
  - `CardboardArmorHandler.testForStealth` @Inject HEAD（`remap=false`）、`FrogportBlockEntity.startAnimation` @Redirect（`FrogportAnimationMixin`）、`ServerChainConveyorHandler.handleTTLPacket/handleStopRidingPacket` @Inject TAIL。
  - Fabric 专属：`Entity` `@Accessor("DATA_POSE")`、`LivingEntity.onSyncedDataUpdated` @Inject TAIL、`CardboardArmorHandlerClient.playerRendersAsBoxWhenSneaking` HEAD。

## 7. 值得学的 5 条具体做法
1. **延迟下马**：不在当前帧改状态，只置 `@Unique` 标记并在下一个 `clientTick` HEAD 处理再 `ci.cancel()` —— 避免 mid-frame NPE（`common/.../mixin/ChainConveyorNametagRoutingMixin.java:90-126`）。适用：所有"卸载骑乘/实体"操作。
2. **把本地预测换成服务端问答 + 预查询缓存**：`RouteCache.shouldQuery/markQuerySent/` 配合行进中就查询下一路口（`.../util/RouteCache.java`）。适用：需要权威判定又要低延迟的载具/物流玩法。
3. **上游扩展点优先，mixin 兜底**：教程用官方 `PonderPlugin` + `orderAfter` 插入而不改 Create（`.../ponder/CardboardPonderIndex.java`）。适用：给 Create 加教程/兼容内容。
4. **碰撞形状"掏空"实现穿越**：只重写 `getCollisionShape` 并缓存派生 VoxelShape，不改 Create 逻辑（`.../mixin/BeltTunnelBlockMixin.java:46-72`）。适用：让玩家/投射物穿过已有方块。
5. **平台差异用注入式回调隔离**：`DismountHelper.registerPacketSender(ChainConveyorPacketHelper::sendStopRidingPacket)` 让 common 不 import 平台类（`forge/.../CardboardedConveynienceForge.java`）。适用：Architectury 多平台共享逻辑。

## 8. 库/API 类 mod 的公开 API
不适用（非库 mod）。
