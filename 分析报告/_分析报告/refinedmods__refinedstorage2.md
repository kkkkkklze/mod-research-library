# Refined Storage 2 源码分析报告

> 仓库：`源码库/_参考仓库/_bulk/refinedmods__refinedstorage2`（develop 分支，HEAD a99fc93）。所有 `文件:行号` 相对仓库根。本报告基于 2026-09 的本地检出实测，行号以 `wc -l`/Read 复核。

## 1. 基本信息

- **mod_id**：`refinedstorage`（`refinedstorage-neoforge/build.gradle.kts:6`；`refinedstorage-neoforge/src/main/templates/META-INF/neoforge.mods.toml:6`）
- **作者**：Refined Mods（neoforge.mods.toml:11）；**许可证**：MIT（`LICENSE.md:1-3`）
- **目标 MC / 加载器**：develop 面向 Minecraft 26.1.x（`.github/ISSUE_TEMPLATE/bug-report.yml:38`，同时维护 1.21.1 线，同文件:39）；NeoForge 依赖 `versionRange="[26.1.2.74,)"`（neoforge.mods.toml:20），loaderVersion `[2,)`（同文件:2）；另有 Fabric 通道（`refinedstorage-fabric/build.gradle.kts`）。判定 26.x 的旁证：源码使用 `net.minecraft.resources.Identifier` 与 `ValueInput/ValueOutput`（如 `refinedstorage-common/src/main/java/com/refinedmods/refinedstorage/common/support/network/AbstractBaseNetworkNodeContainerBlockEntity.java:40-41`）。
- **Gradle 插件与工程结构**：自研多模块插件 `com.refinedmods.refinedarchitect` 1.7.0（`gradle.properties:1`，`settings.gradle.kts:36-42`），Gradle wrapper 9.5.0（`gradle/wrapper/gradle-wrapper.properties:3`）。版本号、MC/加载器版本全部外置在 refinedarchitect 版本目录中，本地检出不可见——**MC 精确补丁版本：未验证**。
- **模块清单**（`settings.gradle.kts:46-59`，rootProject.name=refinedstorage）：

| 模块 | 职责 |
|---|---|
| refinedstorage-core-api | 组件系统最小内核：`ComponentMap/ComponentMapFactory`、`Action`、`CoreValidations`（仅 7 个文件） |
| refinedstorage-resource-api | 资源抽象 `ResourceKey/ResourceAmount`、可监听资源列表、查询 repository |
| refinedstorage-storage-api | Storage 接口族：composite/root/tracked/limited/external |
| refinedstorage-query-parser | 网格搜索语法的词法+语法分析器（lexer/parser 两包） |
| refinedstorage-autocrafting-api | 自动合成领域模型：Task/Pattern/Preview/Plan |
| refinedstorage-network-api | 网络与网络节点接口层（Network、NetworkNode、NetworkComponent） |
| refinedstorage-network | 网络纯 Java 实现（节点实现、builder、图组件） |
| refinedstorage-common-api | MC 侧公共 API：注册表、各类策略接口、跨加载器 SPI（有 MC 依赖） |
| refinedstorage-common | 全部游戏内容：方块/BE/菜单/包/datagen 数据，加载器无关但依赖 MC |
| refinedstorage-fabric-api / refinedstorage-fabric | Fabric 适配层与其 API（能源、plugin 入口） |
| refinedstorage-neoforge-api / refinedstorage-neoforge | NeoForge 适配层与其 API（ResourceHandler 桥接、datagen 驱动） |
| refinedstorage-network-test | 测试夹具库：`@InjectNetwork` JUnit 扩展与 fixture（主源码即测试设施） |

- **Java 版本**：mixin `compatibilityLevel=JAVA_17`（两平台 mixins.json），实际编译工具链由 refinedarchitect 决定——**未验证**。
- **发布坐标**：group `com.refinedmods.refinedstorage`（`build.gradle.kts:13`），Maven Central + CurseForge project 243076 + Modrinth `KDvYkUg3`（`refinedstorage-neoforge/build.gradle.kts:10-13`）。CHANGELOG 最新发布条目 [3.2.1] 2026-06-07。

## 2. 源码规模与包结构

实测（`find *.java | wc` 主/测试分列，行数按 `wc -l` 累加）：

| 模块 | main 文件/行 | test 文件/行 |
|---|---|---|
| refinedstorage-common | 752 / 59,235 | 22 / 2,205 |
| refinedstorage-neoforge | 108 / 10,531 | 52 / 8,519 |
| refinedstorage-fabric | 94 / 6,766 | 0 |
| refinedstorage-network | 86 / 5,024 | 66 / 14,654 |
| refinedstorage-common-api | 117 / 3,214 | 0 |
| refinedstorage-autocrafting-api | 59 / 3,011 | 23 / 4,424 |
| refinedstorage-storage-api | 39 / 1,695 | 23 / 3,563 |
| refinedstorage-network-api | 43 / 772 | 0 |
| 其余（core/resource/query/两平台 api/network-test） | 104 / 3,011 | 28 / 3,156 |
| **合计** | **1,402 / 93,259** | **214 / 36,521** |

总计 **1,616 个 .java / 129,780 行**。速览卡片写 131,396 行，本次复测为 129,780（文件数 1616 一致）；差异未深究，以本报告实测为准。测试占 28% 的行数，`refinedstorage-network` 的测试行数是主源码的近 3 倍（14,654 对 5,024）——纯 Java 内核的重测试策略。

主要包（refinedstorage-common 顶层，按文件数）：support 238、autocrafting 101、storage 93、grid 78、networking 41、constructordestructor 32、security 26、content 26、repackage 18、storagemonitor 16、upgrade 15、controller 14；包结构按 feature 切分（`docs/architecture/decision/009-package-by-feature.md`）。

最大 10 个主源文件（行数实测）：`refinedstorage-neoforge/.../datagen/model/ModelProviders.java` 1185、`refinedstorage-neoforge/.../ConfigImpl.java` 1152、`refinedstorage-neoforge/.../ModInitializer.java` 1065、`refinedstorage-common/.../grid/screen/AbstractGridScreen.java` 1014、`refinedstorage-common/.../AbstractModInitializer.java` 1008、`refinedstorage-fabric/.../ModInitializerImpl.java` 1004、`refinedstorage-common/.../autocrafting/preview/AutocraftingPreviewScreen.java` 1003、`refinedstorage-neoforge/.../datagen/recipe/MainRecipeProvider.java` 961、`refinedstorage-fabric/.../ConfigImpl.java` 892、`refinedstorage-common/.../repackage/org/abego/treelayout/TreeLayout.java` 892（第三方合成树布局库的内嵌复制）。

**检出完整性**：本仓库为完整克隆（非稀疏），但 `refinedstorage-common/src/main/resources` 不存在、无任何 `src/generated/resources` 产物、`assets/lang` 计数为 0——资源全部由 datagen 构建时生成，检出中不含生成结果。因此下文不描述任何 JSON 资产格式。

## 3. 入口与注册

NeoForge 入口是 `@Mod` 构造器（`refinedstorage-neoforge/src/main/java/com/refinedmods/refinedstorage/neoforge/ModInitializer.java:195-269`），核心片段：

```java
@Mod(IdentifierUtil.MOD_ID)                                   // :195
public class ModInitializer extends AbstractModInitializer {  // :196
    public ModInitializer(final IEventBus eventBus, final ModContainer modContainer) {
        PlatformProxy.loadPlatform(new PlatformImpl(modContainer));   // :229
        initializePlatformApi();                                      // :230
        ...
        eventBus.addListener(this::registerPackets);                  // :263
        NeoForge.EVENT_BUS.addListener(this::registerWrenchingEvent); // :266
```

- 注册方式：每个平台建 7 个 `DeferredRegister`（block/item/BE/menu/sound/recipeSerializer/dataComponent，:210-223），统一交给 common 层的 `registerBlocks(callback, factory)` 等 `final` 模板方法（`refinedstorage-common/.../AbstractModInitializer.java:304,364,568,722`），加载器差异被 `RegistryCallback`/`MenuTypeFactory` 这类函数接口包住。
- 共享初始化 `initializePlatformApi()`（AbstractModInitializer.java:184-198）依次装配：API 委托（`RefinedStorageApiProxy.setDelegate(new RefinedStorageApiImpl())` :185）、存储/资源类型注册表、各策略工厂，最后是网络组件工厂（:256-286）——网络是"组件map + 工厂注册"拼出来的，没有硬编码。
- 事件订阅点：`RegisterPayloadHandlersEvent`（:738-739 建 `PayloadRegistrar`）、`ServerTickEvent.Pre → ServerListener.tick`（:1045-1046）、`ServerStarting/Stopped` 管线程池（:1050,1055 附近）。Fabric 侧对位：`ModInitializerImpl extends AbstractModInitializer implements ModInitializer`（`refinedstorage-fabric/.../ModInitializerImpl.java:190`），`ServerTickEvents.START_SERVER_TICK.register(ServerListener::tick)`（同文件:984-986）。

## 4. 核心系统

### 4.1 网络图：不持久化、每次变更全量 BFS + 三集差分

设计定死在 ADR `docs/architecture/decision/006-no-persistent-networks.md`：网络与节点绝不落盘，一切持久状态属于方块实体；启动/入网/拆/合都是内存重建。

- 登记：BE 的容器经 `NetworkNodeContainerProvider.initialize/update/remove(level)` 逐个转发（`refinedstorage-common-api/.../support/network/NetworkNodeContainerProvider.java:19-33`）。`initialize` 是排队的：`RefinedStorageApiImpl.initializeNetworkNodeContainer` 把动作塞进 `ServerListener.queue(...)`，下个 tick 开头才执行，并带 `container.isRemoved()` 守卫处理第三方 mod 抢替换 BE 的竞态（`refinedstorage-common/.../RefinedStorageApiImpl.java:316-337`）。
- 连接发现：`ConnectionProviderImpl.findConnections` 从 pivot 做 BFS（`refinedstorage-common/.../support/network/ConnectionProviderImpl.java:40-68`），邻接查询走 `getContainerProviderSafely`（跨维度 GlobalPos + 1 格懒查，:141-153），方向语义由每类设备的 `ConnectionStrategy`（如 `ColoredConnectionStrategy`、`RelayInput/OutputConnectionStrategy`）经 `ConnectionSinkImpl` 声明；跨维度连接由 wireless transmitter/receiver 的出边策略提供。
- 差分聚合：BFS 结果一次性算出 `Connections(foundEntries, newEntries, removedEntries)` 三元集合（`refinedstorage-network-api/.../Connections.java:11-24`）——"变更怎么聚合"的答案是全量重扫后做集合差，而不是增量维护。
- 结构变更：`NetworkBuilderImpl.initialize/remove/update`（`refinedstorage-network/.../impl/NetworkBuilderImpl.java:35-46,109-132,135-146`）。合并按 `sortDeterministically`（按坐标排序）遍历、找最高优先级成员的现有网络当宿主（:93-106），逐容器 `addContainer` 后对旧网络发一次 `merge` 通知（:70）；拆分把 removedEntries 逐个脱网再以 `initialize` 重建、最后发一次 `split` 通知（:160-195）。
- 每网络的图状态只有三个索引：容器全集、按类索引、按 key 索引（`GraphNetworkComponentImpl.java:21-23`），后者供 O(1) 反查（如按 GlobalPos 找回容器）。增删即改索引（:60-96），组件生命周期回调只有日志（:98-116）——图本身很薄。
- 事件广播：`NetworkImpl` 把 addContainer/removeContainer/split/merge 扇出给全部 `NetworkComponent`（`refinedstorage-network/.../impl/NetworkImpl.java:19-41`），组件按需响应：存储组件 addSource/removeSource（4.2）、grid 组件重挂 watcher（4.3）、能量组件增删 EnergyProvider。

### 4.2 存储聚合：组合树 + 单一聚合列表

网络的 `StorageNetworkComponentImpl` 就是一个 `RootStorageImpl`（`refinedstorage-network/.../impl/storage/StorageNetworkComponentImpl.java:17-40`）：容器入场时若节点是 `StorageProvider` 就把它的 Storage 挂为 source。`RootStorageImpl` 内部是 `CompositeStorageImpl` 包一个可监听聚合列表（`refinedstorage-storage-api/.../root/RootStorageImpl.java:36-40`）。关键形状：**插入/提取走各成员，聚合视图走缓存列表**——`getAll()` 直接 `list.copyState()`（`refinedstorage-storage-api/.../composite/CompositeStorageImpl.java:148-150`），O(缓存) 而非 O(全盘)；`insert/extract` 在 EXECUTE 后把净增量同步回列表（:111-113,141-143），嵌套组合经 `compositeInsert/Extract` 返回 `amountForList` 双记账避免重复计数（:96-105）。列表变更由 `ListenableResourceList` 发出携带**净变化量**的 `OperationResult`（`refinedstorage-resource-api/.../list/listenable/ListenableResourceList.java:27-40`），这就是 4.3 增量的源头。插入前还能被 `RootStorageListener.beforeInsert` 截留（安全面板的权限扣减），越界直接抛 IllegalStateException（`RootStorageImpl.java:90-112`）。

### 4.3 Grid 同步：一次全量 + 限频增量

- 打开菜单：客户端构造器收 `GridData`（active + 全资源列表 + 可合成资源 + 进行中任务，`refinedstorage-common/.../grid/GridData.java:26-53`），经菜单的 StreamCodec 一次性传输。
- 服务器菜单构造时 `grid.addWatcher(this, PlayerActor.class)` 挂 watcher（`refinedstorage-common/.../grid/AbstractGridContainerMenu.java:166`），此后每个列表变化经 `GridWatcherRootStorageListener.changed` 变成 `(resource, change, trackedResource)` 增量（`refinedstorage-network/.../impl/node/grid/GridWatcherRootStorageListener.java:23-30`）。
- 拆/合并时的重同步：`GridNetworkNode.setNetwork` 与 `attachAll` 先 `watcher.invalidate()` 再带 `replay=true` 重挂、把新网络全量重放成"变化"（`refinedstorage-network/.../impl/node/grid/GridWatcherManagerImpl.java:44-63`、`GridWatcherRegistration.java:22-35`）。重放之所以正确，靠的是容器优先级 `NetworkNodeContainerPriorities.GRID = Integer.MAX_VALUE`：grid 必先于存储被处理（`refinedstorage-network/.../impl/node/container/NetworkNodeContainerPriorities.java:6-22`，对应 NetworkBuilderImpl 的 LOWEST/HIGHEST_PRIORITY_FIRST 排序）。
- 限频见第 5 节 PendingGridUpdates。

### 4.4 磁盘：容量可插、序列化集中、跨端只传状态枚举

- 容量是装饰器：`LimitedStorageImpl` 包装任意 Storage，插入前 `capacity - getStored()` 夹断（`refinedstorage-storage-api/.../limited/LimitedStorageImpl.java:32-40`）；磁盘=有界存储+追踪层+状态层。已用量随成员 `getStored()`。
- 序列化不落在磁盘 ItemStack 上：所有存储内容存进一份 level SavedData `refinedstorage:storages`，`Map<UUID, StorageContents>`，Codec 经 `StorageType` 注册表 dispatch，解码回内存时注入 `repository::markAsChanged` 作为脏回调（`refinedstorage-common/.../storage/StorageRepositoryImpl.java:26-57,98-100`）。磁盘物品只持有 UUID 数据组件；内容格式为 `{capacity?, resources:[{resource, amount, changed?{by,at}}]}`，坏条目用 `ErrorHandlingListCodec` 跳过并留日志（`refinedstorage-common/.../storage/ResourceStorageType.java:24-62`）。
- 跨端表达是**状态而非数量**：`StateTrackedStorage` 把 (stored/capacity) 归约为三态 NORMAL/NEAR_CAPACITY(≥75%)/FULL，只在跨态时通知（`refinedstorage-storage-api/.../StateTrackedStorage.java:16,45-61`）；磁盘 LED 序列化为 `Disk(item, state)` record（`refinedstorage-common/.../storage/Disk.java:15-28`）。要看具体余量再按需拉：C2S `StorageInfoRequestPacket(UUID)` → S2C `StorageInfoResponsePacket(UUID, stored, capacity)`（`refinedstorage-common/.../support/packet/s2c/StorageInfoResponsePacket.java:16`）。

### 4.5 能量与激活：每 tick 轮询但 20 tick 节流

`AbstractNetworkNode.doWork` 每 tick 先从能量组件扣自己的 `getEnergyUsage()`（`refinedstorage-network/.../impl/node/AbstractNetworkNode.java:36-41`）；能量组件对 provider 集合求和时防溢出封顶 Long.MAX_VALUE（`refinedstorage-network/.../impl/energy/EnergyNetworkComponentImpl.java:28-47`）。激活判定 = 区块已加载 ∧ 红石模式 ∧ 能量够（`AbstractBaseNetworkNodeContainerBlockEntity.java:83-93`），但状态翻转被 `ACTIVENESS_CHANGE_TICK_RATE = 20` 节流（:56,:95-109）——防止网络临界态下每 tick 抖方块状态。控制器自己用四带滞回把能量百分比映射为 ON/NEARLY_ON/NEARLY_OFF/OFF（`refinedstorage-network/.../impl/node/controller/ControllerNetworkNode.java:18-37`）。

### 4.6 自动合成：tick 内步进、tick 外计算、NBT 存快照

模式登记进 `AutocraftingNetworkComponentImpl` 的多索引（providerByPattern/providerById/providerByTaskId，`refinedstorage-network/.../impl/autocrafting/AutocraftingNetworkComponentImpl.java:57-62`）；预览与最大产量计算是 `CompletableFuture.supplyAsync(..., executorService)` 扔进专用池（:118-160），该池即 `ServerListener` 的 4 线程、**队列上限 2、AbortPolicy** 的 ThreadPoolExecutor（`refinedstorage-common/.../util/ServerListener.java:23-25,47-57`）。任务执行回到 tick：autocrafter 节点 `doWork → tasks.step(network, stepBehavior, this)`（`refinedstorage-network/.../impl/node/patternprovider/PatternProviderNetworkNode.java:207-213`）。任务列表以 `TaskSnapshot` 编码进方块实体 NBT，重启后重建 `TaskImpl`（`refinedstorage-common/.../autocrafting/autocrafter/AutocrafterBlockEntity.java:246-256,286-290`）。线程边界：异步算完不直接碰客户端，而是 `ServerListener.queue(server -> sendToClient(...))` 回投到 tick 开头执行（`refinedstorage-common/.../autocrafting/PlatformAutocraftingNetworkComponent.java:35`）。exporter/constructor 的多任务公平性用 `SchedulingMode` 三实现（默认首个成功即返回/轮询/随机）限一 tick 一动作（`refinedstorage-network/.../impl/node/task/DefaultSchedulingMode.java:8-14`、`RoundRobinSchedulingMode.java:15-21`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **包**：全部为 `CustomPacketPayload` record + `StreamCodec.composite`，双端各一份注册。s2c 27 个、c2s 33 个类（`refinedstorage-common/.../support/packet/s2c|c2s/`），跨加载器复用：处理器写成平台无关的 `PacketHandler<T>`，NeoForge 用 `PayloadRegistrar`（带 modVersion 通道）注册并 `wrapHandler` 适配（`refinedstorage-neoforge/.../ModInitializer.java:738-741,1040-1042`）。代表性形状 `GridUpdatePacket(resource, VAR_LONG amount, Optional<TrackedResource>)`（`refinedstorage-common/.../support/packet/s2c/GridUpdatePacket.java:20-38`）——增量、按资源类型编码、量用 varlong。
- **限频/去抖证据汇总**：① `PendingGridUpdates`：每资源类型 4 次/秒 RateLimiter，超限的进 `Map<resource, PendingUpdate>` 累加净 delta，另有 1 次/秒的 flush 闸（`refinedstorage-common/.../grid/PendingGridUpdates.java:18,25,31-66`），flush 挂在菜单 `broadcastChanges()`（每 tick）尾部（`AbstractGridContainerMenu.java:363-368`）；② 节点激活 20-tick 节流（§4.5）；③ 探测器红石输出需稳定 20 tick 才翻转（`refinedstorage-common/.../detector/DetectorBlockEntity.java:44,173-178`，注释明说为修 chunk 加载瞬态误报）；④ 初始化排队到 tick 开头（§4.1）。
- **数据驱动程度**：存储内容、磁盘、任务快照、菜单数据、包体全部 Codec/StreamCodec 化（§4.4 与 GridData）；`StorageType`、`ResourceType`、`GridResourceType`、`ConnectionStrategy`、网络组件等都走 `PlatformRegistry` 注册表 + `ComponentMapFactory`。但配方/战利品/模型等 vanilla 数据不手编 JSON，见 datagen。
- **配置**：平台无关 `Config` 接口（约 90 个 getter，按设备分组 `SimpleEnergyUsageEntry`/`StorageBlockEntry` 等，`refinedstorage-common/.../Config.java:16-188`）；NeoForge 用 `ModConfigSpec` 实现（`refinedstorage-neoforge/.../ConfigImpl.java:21-32`），Fabric 用 Cloth Config（`refinedstorage-fabric/.../ConfigImpl.java:24`）。能耗、1k/4k/16k/64k 分档等全部可配。
- **datagen**：有，集中在 NeoForge 模块 `refinedstorage-neoforge/.../datagen/`（DataGenerators + advancement/loot/model/recipe/tag 五包，入口挂 `GatherDataEvent.Client`，`datagen/DataGenerators.java:26`）；common 模块以 `commonResources` 配置向两平台输出共享资源（`refinedstorage-neoforge/build.gradle.kts:9` 的 `dataGeneration(project(":refinedstorage-common"))`）；Fabric 在 ProcessResources 里把 blockstates 的 `"type"` 键批量替换为 `"fabric:type"`（`refinedstorage-fabric/build.gradle.kts:75-77`）。

## 6. Mixin

两个平台各一个 mixin 配置，数量极少、用途克制：

- NeoForge：`refinedstorage-neoforge/src/main/resources/refinedstorage.mixins.json` 共 2 个——`AbstractContainerMenuMixin` 注入 `doClick` 的 `@At("HEAD")`、cancellable，创意模式中键克隆时把存储容器内容清空只留满堆引用（`.../mixin/AbstractContainerMenuMixin.java:35-62`）；`AbstractGuiGraphicsExtractorMixin` 注入 `GuiGraphicsExtractor#item` HEAD，取消 vanilla 物品渲染以走自绘（`.../mixin/AbstractGuiGraphicsExtractorMixin.java:15-19`）。
- Fabric：同名两注点之外用 accessor（`EditBoxAccessor`、`KeyMappingAccessor`）与 access widener 取字段（Slot.y 可变、AbstractContainerMenu.lastSlots/remoteSlots 可读、RecipeManager.recipes 可读，`refinedstorage-fabric/src/main/resources/refinedstorage.accesswidener:2-8`）。
- 规律：注点全在客户端渲染/容器交互的边缘，**没有任何一处用于改服务端玩法逻辑**——玩法差异全走 4.x 的接口反转，这正是它能双加载器共享 common 的原因。

## 7. 值得学的 5 条

1. **两段限频 + delta 合并的同步器**：`refinedstorage-common/src/main/java/com/refinedmods/refinedstorage/common/grid/PendingGridUpdates.java:18-66`——入口按资源类型 4/s 放行，超额进 map 累加净变化，出口 1/s 统一 flush，且 flush 点搭在 `broadcastChanges()` 上（`grid/AbstractGridContainerMenu.java:363-368`）不新增 tick 负担。值得抄：它把"每秒几百次库存变化"压成常数包，且合并的是 delta 不是快照，天然幂等。
2. **三态滞回容量状态机**：`refinedstorage-storage-api/src/main/java/com/refinedmods/refinedstorage/api/storage/StateTrackedStorage.java:16,45-61`——连续量(capacity,stored)只在跨越 NORMAL/NEAR_CAPACITY/FULL 时产生一次通知，下游（LED、tooltip、方块状态）只同步枚举（`common/.../storage/Disk.java:15-28`）。值得抄：把"脏标记"从每次数值变动提升到离散状态跃迁，同步频率与容量精度解耦。
3. **tick 头事件队列 + 有界后台池**：`refinedstorage-common/src/main/java/com/refinedmods/refinedstorage/common/util/ServerListener.java:32-57`——ACTIONS 队列在 START_SERVER_TICK 排空（NeoForge 挂点 `neoforge/ModInitializer.java:1045-1046`，Fabric `fabric/ModInitializerImpl.java:984`），异步池 4 线程/队列 2/AbortPolicy，且消费端回投一律走 queue（`common/.../autocrafting/PlatformAutocraftingNetworkComponent.java:35`）。值得抄：一个类就把"哪个线程算、哪个线程发"钉死，重开世界时旧池先 `stopPool`（:63-71,83-95）。
4. **UUID 间接层的存储仓储**：`refinedstorage-common/src/main/java/com/refinedmods/refinedstorage/common/storage/StorageRepositoryImpl.java:24-57`——物品只持 UUID 引用，内容集中在一份 SavedData、经类型注册表 dispatch 的 Codec 序列化，构造存储时注入 `markAsChanged` 回调当写脏位；坏数据用 ErrorHandlingListCodec 局部降级（`storage/ResourceStorageType.java:24-62`）。值得抄：磁盘丢失/复制不产生幽灵库存，存档体积与设备数解耦。
5. **用容器优先级固定重放顺序**：`refinedstorage-network/src/main/java/com/refinedmods/refinedstorage/api/network/impl/node/container/NetworkNodeContainerPriorities.java:6-22`——GRID=MAX_VALUE 保证 split/merge 时观察者优先失效再重挂、其后存储才逐个重新入场（配合 `GridWatcherManagerImpl.java:44-63` 的 invalidate+replay），增量协议永远不需要"网络切换"这种包。值得抄：结构事件靠处理顺序约定收敛成纯增量流，注释把 why 写进了常量声明处。

**它做坏的一处**：节点变更全量重扫。每次 initialize/update/remove 都从 pivot 跑一遍全网络 BFS（`common/src/main/java/com/refinedmods/refinedstorage/common/support/network/ConnectionProviderImpl.java:40-68`、`refinedstorage-network/src/main/java/com/refinedmods/refinedstorage/api/network/impl/NetworkBuilderImpl.java:35-46,109-132`），而 chunk 卸载会对每个 BE 调一次 `remove`（`common-api/src/main/java/com/refinedmods/refinedstorage/common/api/support/network/NetworkNodeContainerProvider.java:30-33`）——N 节点网络整段卸载/装载退化为 O(N²) 次邻接探测。这是 ADR-006"正确性优先"的代价，作者也清楚（grid 优先级注释），但对大网络是真实热点，读者不应照搬"每次变更全量 BFS"，宜保留它的三集差分接口（Connections 记录）但在外层加脏区域/批量合并。

### 给两个自建工程的形状（结论）

- **新星殖民地·每日结算**：(a) 结算不直接发包/改 UI——把结算结果 `queue` 进 ServerListener 式 tick 头队列（`ServerListener.java:32-45`），结算中途任何子系统重入都安全；(b) 到港/货币的重复广播学 PendingGridUpdates：`Map<入账键, 净delta>` 累加 + 每秒一次 flush（`PendingGridUpdates.java:58-66`），多次结算自动合并成一包，且改 delta 后重放幂等。
- **蜂群·库存网络**：(a) 网络层直接借用它的对象形状：`Connections(found/new/removed)` 三集记录 + NetworkComponent 生命周期回调（`Connections.java:11-24`、`NetworkComponent.java:10-24`），网络本身不落盘、以 BE 为唯一事实源（ADR-006），从根上消灭"幽灵节点"类 bug；(b) 库存聚合抄 CompositeStorageImpl 的"成员为事实、聚合为缓存、增量双记账"（`CompositeStorageImpl.java:28-31,111-113,148-150`），查询 O(缓存)，配合按 actor 类型追溯最近变更（`findTrackedResourceByActorType`，同文件:158-166）正好对应"哪个工蜂动过这格"。

## 8. 公开 API

它是当框架卖的：`@API(status=STABLE/INTERNAL, since=...)`（apiguardian）遍布 api 模块，7 个平台无关模块（core/resource/storage/network-api/network/autocrafting/query-parser）**导入 net.minecraft 的文件数为 0**（逐一 grep 实测），且 network 的 gradle 依赖只有自家 api + slf4j（`refinedstorage-network/build.gradle.kts:16-21`）。分层规则写在 ADR-002/-003/-001：纯 Java 内核在下，common-api 是"MC 但加载器无关"的中间层，平台模块只做注册/包/渲染桥接（§3、§6 是其存在形式的证据）。接口反转的轴心是 `Platform`/`PlatformProxy`（`refinedstorage-common/src/main/java/com/refinedmods/refinedstorage/common/Platform.java:55`，144 行的窄接口：注册表、配置、容器查询、能耗模式等），构造期由 `PlatformProxy.loadPlatform(new PlatformImpl(...))` 注入实现。

扩展点（对 addon 作者）：入口包 `com.refinedmods.refinedstorage.common.api`，聚合接口 `RefinedStorageApi`（232 行，`common-api/.../api/RefinedStorageApi.java`）暴露一批注册表/工厂：`StorageType`、`ResourceType`、`GridResourceType`、`GridSynchronizer`、网格插入/提取/滚轮策略工厂、importer/exporter 搬运策略、外部存储 provider、constructor/destructor 策略、pattern 外部 sink、网络组件工厂（可往 ComponentMapFactory 注入自己的 NetworkComponent，见 `common/.../AbstractModInitializer.java:256-286` 的用法示例）。实例获取走代理反转：`RefinedStorageApi.INSTANCE` 是 Proxy，平台启动时 `setDelegate`（`common-api/.../RefinedStorageApiProxy.java`）——插件 mod 永不触碰构造器。各平台还有对位 API（`RefinedStorageNeoForgeApi` 的 ResourceHandler 桥、`RefinedStorageFabricApi` + `RefinedStoragePlugin` 入口）。接入方式：对 Maven 坐标 `com.refinedmods.refinedstorage:refinedstorage-*` 声明 compileOnly/api 依赖（各模块 publishing.maven=true，`refinedstorage-common/build.gradle.kts:10`）。

**这套分层值不值得读者的工程照搬**：值得搬思想、不值得搬仪式。值得的：纯领域模块零 MC 依赖（网络/存储/合成三内核都可在 JVM 单测里跑，network 模块 14,654 行测试即是红利）、`Connections` 差分接口、tick 头队列。不值得的：14 模块 + 自研 Gradle 插件 + 双平台 -api 模块的工程税，对个人 mod 而言 2~3 个模块（core/common/loader）已到收益上限。对「新星殖民地」（单 NeoForge）建议只划一层"无 MC 依赖的内核包"而非独立 module；对「蜂群」若库存网络要单测，可仿 core/storage/network-api 三件套的接口面（每模块 40~80 文件、千行级），而不必上 Maven 发布。
