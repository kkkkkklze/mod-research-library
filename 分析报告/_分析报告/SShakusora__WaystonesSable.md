# SShakusora/WaystonesSable 源码分析报告

## 1. 基本信息
WaystonesSable / `waystonessable` / Shinonome Shakusora / 1.0.8-SNAPSHOT / MIT / group `com.sshakusora` / Java 21。MC 1.21.1，NeoForge 21.1.228（loader `[4,)`），单模块。插件：`java-library` + `net.neoforged.moddev 2.0.141`（`build.gradle:1-6`）；`publishSnapshot` 自定义任务用 `HttpURLConnection` PUT 到 Nexus `maven.sshakusora.com/repository/waystones-sable`（`:246-282`）。依赖：`waystones-neoforge 21.1.39+1.21.1`（被接入 API）、`balm-neoforge 21.0.59`（事件/hook）、`sable-neoforge 2.0.3`（被兼容的 SubLevel）、`veil-common 4.1.4`、`sable-companion-common 1.6.0` compileOnly、`create 6.0.10-280` 与 `create-aeronautics 1.3.0`（`includeCreateRuntime` 属性切换 compileOnly/implementation）、ponder/registrate/flywheel compileOnly。`neoforge.mods.toml` 由 `src/main/templates` 经 `generateModMetadata` 展开。

## 2. 规模与包结构
`.java` 29 个 / 4069 行。包：`compat`(7)、`compat/create`(1)、`gametest`(6)、`mixin`(5)、`mixin/client`(3)、`network`(3)、`client`(2)、`command`(1)。最大：`compat/SableWaystoneCompat.java` 989、`gametest/SubLevelWaystoneUnloadTest.java` 761、`compat/SableWaystoneEventHandler.java` 288、`mixin/WaystonesSableMixinPlugin.java` 282。资源：`waystonessable.mixins.json`、lang en/zh、`assets/waystones/.../groups/sable.png`、5 个 `data/waystonessable/structure/*.gravity.nbt`（gametest 结构）。

## 3. 入口与注册
`WaystonesSable.java:23-48`：`@Mod` 构造器调 `ModPayloads.register(modEventBus)`、`SableWaystoneEventHandler.register()`、`registerCreateAttachedCheckIfAvailable()`、客户端 `SableWaystoneClientHandler.register`，以及 `NeoForge.EVENT_BUS.addListener(this::onRegisterCommands)`（`/waystones activateall`）。网络 `network/ModPayloads.java:9-30` 用 `RegisterPayloadHandlersEvent`+`PayloadRegistrar("1")` 注册 2 个 playToClient payload。第三方事件全走 Waystones 的 Balm 总线：`Balm.getEvents().onEvent(WaystoneTeleportEvent.Pre.class, ...)` 等 9 个（`SableWaystoneEventHandler.java:20-30`）。Create 为软依赖：`ModList.get().isLoaded("create")` + `Class.forName(...).getMethod("register").invoke(null)` 反射注册。

## 4. 核心系统
1. **坐标兼容层 `SableWaystoneCompat`(989 行)**：plot（SubLevel 内部坐标）↔ 世界可见坐标互转——`projectToVisible`、`getVisibleWaystonePos`、`resolveVisibleTeleportPos`、`getPlotCoordinate`、`isInternalPlotPosition`、`isWaystoneOnSubLevel`（服务端查 `SubLevelTrackingPointSavedData` 的 TrackingPoint；客户端用注入的 `Predicate<Waystone>`，`client/SableWaystoneClientHandler.java:22-30`）。
2. **Waystone 装饰器族**（`SableWaystoneEventHandler.java:166-286`）：`TrackedTargetWaystone`、`VisibleSourceWaystone`、`SubLevelWaystone extends MutablePersonalizedWaystoneDelegate` 各覆写 `getPos()/isValidInLevel()`——菜单里显示可见坐标，Prepare 阶段换回 plot-local 权威目标；另有 `TwinboundSubLevelWaystone`（`SableWaystoneCompat.java:955-977`）。
3. **五段式传送流水线**（`SableWaystoneEventHandler.java:50-155`）：`WaystoneTeleportEvent.Pre`（refresh tracking point、包 target/from）→ `.Prepare`（同步恢复 SubLevel：`prepareStoredSubLevelForTeleport`/`useLoadedStorageWaystoneChunks`，失败给 `WaystoneTeleportError.DestinationOutOfBounds`）→ `WaystoneTeleportEntityEvent.Pre`（重算可见落点、跨维度前 `prepareCrossDimensionTeleport`）→ `.Post`（`syncTrackingAfterTeleport`+`resetEntityMotion`）。
4. **客户端防回弹**：`SableTeleportPayload`（`network/SableTeleportPayload.java:40-63`，`StreamCodec.composite` 打包 optional UUID + 3 double）在客户端 `moveTo` 后 `sable$setTrackingSubLevel`/`setPlotPosition(null)` + `EntitySubLevelUtil.setOldPosNoMovement`；`SubLevelGuardPayload` 触发 `ClientTeleportGuard.protect(5000L)`，使 `ClientboundStopTrackingSubLevelPacketMixin` 在 5 秒内取消 stop-tracking 包。
5. **持久化修补**：`compat/WaystonePositionSnapshotSavedData.java` 是 `SavedData`+`SubLevelObserver`（`FILE_ID="waystonessable_position_snapshots"`，观察 SubLevel 移除清理快照）；`compat/SableTrackingPointerSync.java` 缓存 `UUID→GlobalSavedSubLevelPointer`，在 `SubLevelHoldingChunkMap.saveAll()` 返回后 flush 回写 TrackingPoint，修 Sable "先移除再赋指针" 的索引漂移（对应 commit `827a594 ... #13`）。
6. **gametest 覆盖**：`gametest/` 5 个测试（放置/装配/卸载/API 兼容/分类基准）+ `SubLevelWaystoneTestSupport` 脚手架 + `*.gravity.nbt` 结构模板。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络：2 个 payload，均 `playToClient` + `context.enqueueWork`（见上）。数据驱动：无 recipe/loot，仅结构 NBT + lang；`SableWaystoneGroups.defaultGroup()` 提供 `waystonessable:sable` 分组与图标（经 `CollectDefaultWaystoneGroupsEvent`/`CollectDynamicWaystoneGroupsEvent` 注入）。配置：无（仅 -D 系统属性开关 mixin）。datagen：无。

## 6. Mixin
`src/main/resources/waystonessable.mixins.json`（`required:true`、`package com.sshakusora.waystonessable.mixin`、`plugin: WaystonesSableMixinPlugin`、`injectors.defaultRequire=1`）。hook 点：
- `WaystoneBlockBaseMixin`：让目标类 `implements BlockSubLevelAssemblyListener`，实现 `afterMove(...)`（detach→onLoad→initializeFromExisting→updateWaystoneTrackingPoint→`WaystoneSyncManager.sendWaystoneUpdateToAll`）
- `WaystoneBlockEntityBaseMixin`：`onLoad` @RETURN
- `SubLevelAssemblyHelperMixin`：`assembleBlocks(...)` @HEAD cancellable `require=0`，`ThreadLocal` 重入保护后 `cir.setReturnValue(...)` 递归原方法，把 Waystone 另一半补进装配集合（`remap=false`）
- `HoldingSubLevelMixin`：`setPointer(...)` @RETURN 记录指针；`SubLevelHoldingChunkMapMixin`：`saveAll()` @RETURN flush + 两个 `@Invoker`（配套 `compat/SubLevelHoldingChunkMapAccessor`）
- 客户端：`ClientPacketListenerMixin`（`handleForgetLevelChunk` 内 `@At(INVOKE, ClientLevel.getChunkSource)` 取消）、`ClientboundStartTrackingSubLevelPacketMixin`/`ClientboundStopTrackingSubLevelPacketMixin`（`handle(PacketContext)` @HEAD）
- **ASM 探测式 MixinPlugin**（`mixin/WaystonesSableMixinPlugin.java`，282 行）：用 `ClassReader`+`ClassNode`(SKIP_CODE|DEBUG|FRAMES) 探测目标方法/字段描述符（`assembleBlocks`、`setPointer`、Create `BlockMovementChecks.registerAttachedCheck`）决定 `shouldApplyMixin`，并有 `-Dwaystonessable.forceSableAssemblyMixin`/`disableSableAssemblyMixin`/`disableSableTrackingPacketMixins` 覆盖。

## 7. 值得学的 5 条
1. 第三方版本自适应 mixin：`shouldApplyMixin` 里 ASM 探测签名 + 系统属性开关（`WaystonesSableMixinPlugin.java`），避免 `require=1` 崩游戏。
2. 用装饰器包装第三方数据对象而非改其代码（`WaystoneDelegate` 子类只改 `getPos/isValidInLevel`），适合"显示坐标≠真实坐标"。
3. 优先用第三方事件总线（`Balm.getEvents().onEvent(...)`）而非 mixin 做兼容。
4. `@Inject(HEAD, cancellable)` + `ThreadLocal` 重入保护 + 递归调用原方法实现"扩参重放"（`SubLevelAssemblyHelperMixin.java:31-64`）。
5. `SavedData`+`SubLevelObserver` 快照 + 延迟 flush 修上游写入顺序竞态（`WaystonePositionSnapshotSavedData`、`SableTrackingPointerSync`）。

## 8. 库/API 视角
不提供对外 API，属纯补丁型兼容层：消费 Waystones `net.blay09.mods.waystones.api.*`（`Waystone`、`WaystoneGroup`、`WaystoneDelegate`、`MutablePersonalizedWaystone`、`WaystonesAPI`、`WaystoneSyncManager`、`api/event/*`）与 Sable `dev.ryanhcode.sable.api.*`（`SubLevelContainer`、`SubLevelAssemblyHelper`、`BlockSubLevelAssemblyListener`、`SubLevelObserver`、`EntitySubLevelUtil`）及 `mixinterface` 扩展（`EntityStickExtension.sable$setPlotPosition`、`EntityMovementExtension.sable$setTrackingSubLevel`）。可作为"事件优先 + mixin 兜底 + gametest 验证 + 反射软依赖"的兼容补丁范例。
