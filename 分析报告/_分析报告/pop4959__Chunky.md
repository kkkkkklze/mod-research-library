# pop4959/Chunky 源码分析报告

## 1. 基本信息

- Mod 名：Chunky（"Pre-generates chunks, quickly, efficiently, and safely"）；mod_id：`chunky`（`neoforge/src/main/java/org/popcraft/chunky/ChunkyNeoForge.java:49`）；作者 pop4959
- 版本：`1.5` + 构建期追加 `git describe` 的提交数（`gradle.properties:4`、`build.gradle.kts` 的 `commitsSinceLastTag()`）
- 目标 MC / 加载器：本检出分支面向 **MC 26.1**（`neoforge/build.gradle.kts` `minecraft(group="com.mojang", name="minecraft", version="26.1")`）；NeoForge `26.1.0.15-beta`、Fabric Loader `0.18.5` + Fabric API `0.144.3+26.1`、Forge `26.1-62.0.9`（userdev）；同一份代码另有 bukkit / paper / folia / sponge 平台模块
- Java：toolchain 25，`options.release = 25`（`build.gradle.kts`）
- 许可证：GNU GPLv3（`neoforge.mods.toml` `license="GNU GPLv3"`）
- Gradle 插件：`com.gradleup.shadow` 9.4.0（每平台一个 shadowJar）+ `org.relativitymc.neo-loom` 1.16.0-alpha.4（Fabric/NeoForge/Forge 三个模块统一用 RTM 的 neo-loom，少见但有效）
- 编译依赖：无第三方 mod 依赖（仅 fabric 侧 `compileOnly me.lucko:fabric-permissions-api`）；`nbt` 模块是自研 NBT/区域文件读写（读写 `.mca` 做 trim）

## 2. 源码规模与包结构

实测：**.java 192 个 / 12474 行**。

模块与文件数：common 95、nbt 20、neoforge 19、forge 19、fabric 19、sponge 10、bukkit 8、paper 1、folia 1。

`common` 包结构（`common/src/main/java/org/popcraft/chunky/`）：`api` + `api/event/task`、`command`（23 个子命令）、`event` + `event/command`+`event/task`、`iterator`（6 种迭代器 + PatternType）、`platform` + `platform/impl` + `platform/util`、`shape`（12 个几何形状）、`util`（22 个）、`integration`（BorderIntegration）。

最大文件：`util/Hilbert.java` 362（Hilbert 曲线坐标映射）、`sponge/ChunkySponge.java` 352、`command/TrimCommand.java` 290、`GenerationTask.java` 272、`platform/impl/GsonConfig.java` 250、`bukkit/platform/BukkitWorld.java` 244、`iterator/RegionChunkIterator.java` 241、`Selection.java` 227、`platform/NeoForgeWorld.java` 200、`Chunky.java` 196。

## 3. 入口与注册

`ChunkyNeoForge.java:47`：

```java
@Mod(ChunkyNeoForge.MOD_ID)
public class ChunkyNeoForge {
    @SubscribeEvent public void onServerStarting(ServerStartingEvent e) {
        Path configPath = FMLPaths.CONFIGDIR.get().resolve("chunky/config.json");
        this.chunky = new Chunky(new NeoForgeServer(this, server), new GsonConfig(configPath));
        if (chunky.getConfig().getContinueOnRestart()) { /* 自动 continue 上次任务 */ }
        chunky.getEventBus().subscribe(GenerationTaskUpdateEvent.class, new BossBarTaskUpdateListener(bossBars));
    }
}
```

**不使用 DeferredRegister/Registrate**（无方块物品）。两条自研"注册"链路：
1. 子命令表：`Chunky.loadCommands()`（`Chunky.java:106`）返回 `Map<String, ChunkyCommand>`，命令类与平台无关（`common/command/*.java`），每个加载器只写 Brigadier 骨架再用 `input.split(" ")` 把 token 交给 `ChunkyCommand.execute(sender, arguments)`（`ChunkyNeoForge.java:88-94`），参数类型全用 `word()`/`string()` 以免平台差异。
2. 事件总线：`common/event/EventBus.java`（自研 `subscribe(Class, Consumer)` + `call(Event)`），`Chunky.java:147` 暴露；API 事件在 `api/event/task/`。

## 4. 核心系统

1. **GenerationTask（多线程预生成，最值得学）**：`common/src/main/java/org/popcraft/chunky/GenerationTask.java:24`，`implements Runnable` 由 `TaskScheduler` 执行。要点：① 用 `Semaphore working = new Semaphore(MAX_WORKING_COUNT=50)` 限制在途区块数，可用 `-Dchunky.maxWorkingCount` 调整（:25、:124）；② 每个区块走 `world.isChunkGenerated(...).thenCompose(generated -> ... world.getChunkAtAsync(x,z))`（:146-159），完成回调里 `working.release(); update(...)`，全程不阻塞主线程；③ 速率估算用 `Deque<Pair<Long, AtomicLong>>` 分桶（窗口 `SAMPLE_INTERVAL=30s`、子桶 1s，:26-27、:65-87），据此算剩余时间；④ 线程名改成 `Chunky-<world> Thread` 便于 profiler 观察（:119-120）。
2. **ChunkIterator 家族（生成顺序可插拔）**：`iterator/ChunkIterator.java` 只有 `next()/total()/name()` 与 `default boolean process()`（重活前置到 process，便于"续跑"）；`ChunkIteratorFactory`（`iterator/ChunkIteratorFactory.java`）按 `PatternType`（concentric/loop/spiral/csv/region/world）与形状分派；`util/Hilbert.java` 为螺旋类迭代器提供 Hilbert 曲线序列。
3. **平台抽象**：`platform/` 下 `World`/`Server`/`Sender`/`Player`/`Border`/`Config` 六个接口，各加载器各写一份实现（`NeoForgeWorld/FabricWorld/ForgeWorld/BukkitWorld`）；`platform/impl/GsonConfig.java` 是全平台共用的 Gson 配置（`ConfigModel`/`TaskModel`，任务列表即持久化），另有 `.chunky.properties` 读限速、classloader 读 `version.properties`（`Chunky.java:85-104`）。
4. **异步区块加载（核心黑魔法）**：`neoforge/.../platform/NeoForgeWorld.java:96-122`——非主线程时先 `CompletableFuture.supplyAsync(..., world.getServer())` 弹回主线程，然后 `serverChunkCache.addTicketWithRadius(CHUNKY, chunkPos, 0)` 加票 → `((ServerChunkCacheMixin) cache).invokeRunDistanceManagerUpdates()` → `invokeGetChunkFutureMainThread(x,z,ChunkStatus.FULL,create)`，`thenApplyAsync(Function.identity(), ((ChunkMapMixin) chunkMap).getMainThreadExecutor())`（注释明确说是防原版区块系统与实体区块竞争导致内存泄漏），`whenCompleteAsync` 里移除票并 `chunky$markChunkSystemHousekeeping()`。另有 Moonrise 兼容分支（`ChunkyNeoForge.ENABLE_MOONRISE_WORKAROUNDS`）。
5. **已生成判定 + RegionCache**：`NeoForgeWorld.isChunkGenerated`（:62-93）先查 `invokeGetVisibleChunkIfPresent(pack)` 的 `getLatestStatus()==FULL`，否则 `invokeReadChunk` 或 `serverChunkCache.chunkScanner().scanChunk(...)` 流式读 NBT 的 `Status` 字段（不全量反序列化）；`util/RegionCache.java` 用 `Map<Long,BitSet>`（32×32 区块为一个 region，`ChunkMath.pack/regionIndex`）记录本轮已生成，避免重复读盘。
6. **并发调度**：`util/TaskScheduler.java` 用 `ThreadPoolExecutor(3, Integer.MAX_VALUE, 5min, SynchronousQueue)` + daemon 线程 + `prestartAllCoreThreads()`，`runTask` 后 `futures.removeIf(Future::isDone)` 防止句柄堆积。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无自定义包；进度展示用原版 BossBar（`listeners/bossbar/BossBarTaskUpdateListener`，`ServerBossEvent` 存在 `ConcurrentHashMap<Identifier, ServerBossEvent>`，`ChunkyNeoForge.java:52`）。
- 配置：`config/chunky/config.json`（Gson + 内部 `ConfigModel`，含 `tasks` 表用于重启续跑）；`.chunky.properties` 覆盖生成限速。
- 国际化：`util/TranslationKey` + `Translator` + language 配置项。
- datagen：无。

## 6. Mixin

配置：`neoforge/src/main/resources/chunky.mixins.json`（`required=true`、`minVersion=0.8`、`package=org.popcraft.chunky.mixin`、`compatibilityLevel=JAVA_17`），fabric/forge 各有同名副本，mods.toml 用 `[[mixins]] config=` 声明。

- `ChunkMapMixin`：`@Invoker("getVisibleChunkIfPresent")`、`@Invoker("readChunk")`、`@Accessor` 取 `mainThreadExecutor`
- `ServerChunkCacheMixin`：`@Invoker("getChunkFutureMainThread")`、`@Invoker("runDistanceManagerUpdates")`
- `MinecraftServerMixin`：`@Inject(method="tickServer", at=@At(value="INVOKE", target="Lnet/minecraft/server/MinecraftServer;tickConnection()V"))` + `@Unique` 字段（在 tick 内插入自己的调度）
- `ServerLevelMixin`：`@Accessor`；`MinecraftServerAccess`：`@Accessor setEmptyTicks` 等
- 客户端 `client/IntegratedServerMixin`：`@Inject(method="tickServer", at=@At(value="INVOKE", target=".../IntegratedServer;tickPaused()V"))`，让单人游戏暂停时预生成仍推进

## 7. 值得学的 5 条做法

1. **"common 接口 + 薄平台实现"多加载器分层**：`common` 95 个文件承载全部逻辑，fabric/neoforge/forge 各 ~19 个文件只做接口实现与事件接线——1.21.1 单版本 mod 欲留移植余地的最佳模板（见 `neoforge/src/main/java/org/popcraft/chunky/platform/`）。
2. **信号量限制在途异步任务**：`GenerationTask.java:124` `new Semaphore(50)` + `whenComplete(...release())`，一行解决"异步流水线打爆内存/线程"。
3. **用 @Invoker + 主线程 executor 安全加载区块**：`NeoForgeWorld.java:96-122` 的 ticket → runDistanceManagerUpdates → getChunkFutureMainThread → 主线程 executor 四步，是"非原版机制强制加载区块"的完整参考实现。
4. **流式扫 NBT 判断区块状态**：`isChunkGenerated` 用 `CollectFields`/`FieldSelector` 只取 `Status` 字段而不 new 整个 Chunk，显著省内存（`NeoForgeWorld.java:82-91`）。
5. **自研极简 EventBus + 公开 API 包**：`common/event/EventBus.java` 与 `api/ChunkyAPI`、`ChunkyProvider.get()`（懒注册、未加载抛 `IllegalStateException`），第三方无需依赖具体加载器即可接入。

## 8. 公开 API（Chunky 亦被当作前置）

- API 包：`org.popcraft.chunky.api`（`api/ChunkyAPI.java`：`version()`、`startTask/pauseTask/continueTask/cancelTask`、`onGenerationProgress/onGenerationComplete(Consumer<...>)`）+ `api/event/task/GenerationProgressEvent`、`GenerationCompleteEvent`。
- 获取实例：`org.popcraft.chunky.ChunkyProvider.get()`（`ChunkyProvider.java`，由 `Chunky` 构造时 `register`）。
- 另有面向"世界边界"的集成扩展点：`common/integration/BorderIntegration.java` + `integration/Integration.java`，第三方用 `Chunky#getCommands().containsKey("border")` 检测能力（见 `ChunkyNeoForge.java:149`）。
