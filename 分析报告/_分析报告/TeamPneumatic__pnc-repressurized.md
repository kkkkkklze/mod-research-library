# PneumaticCraft: Repressurized 源码分析报告

分析对象：`源码库/_参考仓库/_bulk/TeamPneumatic__pnc-repressurized`（HEAD 稀疏检出，仅 java + 一个 toml，见第 2 节）。
阅读取舍：17 万行不可能通读——先读 `gradle.properties` / `build.gradle` / 两个 @Mod 入口 / 包结构，然后细读三个子系统（无人机编程执行栈、组件化机器与升级聚合、网络与 GUI 字段同步 + 空气扩散），其余（elevator、heat、hacking、pneumatic_armor、thirdparty、datagen）按包略读并只引用签名。凡未展开的文件不写结论。

## 1. 基本信息

- mod_id `pneumaticcraft`（`gradle.properties:23`，`src/main/resources/META-INF/neoforge.mods.toml` 的 `[[mods]] modId="pneumaticcraft"`）；作者 `Des Herriott,Minemaarten`（`gradle.properties:29`）。
- 版本：MC 1.21.1 / NeoForge 21.1.205，版本区间 `[1.21.1,1.22)` 与 `[21.1.181,)`（`gradle.properties:10,12`，及 `minecraft_version_range`/`neo_version_range` 行）；无 Forge/Fabric 双载分支。mod 版本 8.2.23（`gradle.properties:25`）。
- 加载器声明：`modLoader="javafml"`，`[[mixins]] config = "mixins.pneumaticcraft.json"`（mods.toml）。
- 许可证：GPLv3（`gradle.properties:28` `mod_license=GPL3`；mods.toml `license="GNU GPLv3"`）。值得注意：`src/api/**` 的文件头写的是 **LGPL**（如 `src/api/java/me/desht/pneumaticcraft/api/drone/IProgWidget.java:1-16`），主源码是 GPL——API 与被 GPL 的实现分开发布，这是它作为「被 addon 依赖的库」的许可策略。
- Gradle 工程：单模块 + 三个 sourceSet（`build.gradle:93-118`）：`api`（独立编译，`addModdingDependenciesTo(sourceSets.api)` 见 :120）、`main`（`compileClasspath += api.output`）、`test`（本检出缺目录）。插件 `net.neoforged.moddev` 2.0.141（:15）、`me.modmuss50.mod-publish-plugin` 2.1.1（:16）、buildscript 里另有 parchment librarian（:4）。Java 21 toolchain（:91）。
- 发布坐标：`me.desht.pneumaticcraft:pneumaticcraft-repressurized:8.2.23+mc1.21.1`（`build.gradle:262-266`），除主 jar 外显式产出 `apiJar`（:235-238）与 `sourcesJar`（:241-244）并 `artifacts { archives ... }`（:246-249）；远程仓库 modmaven（:275-283）。这就是 addon 侧 `compileOnly` 拿到的东西。
- 依赖策略（`build.gradle:166-212`）：几乎所有第三方（JEI/Curios/Patchouli/Mekanism/IE/Create/CraftTweaker/FTB/CC:Tweaked/Thermal/GameStages）都是 `compileOnly` + `localRuntime`/`localImplementation` 成对出现——编译期只见 API，运行期 dev 环境才真加载。另有 `extra-mods-1.21.1/` 目录下的 jar 自动变成 `localRuntime` 依赖（:205-212），注释明说这个点子来自 AE2。

## 2. 源码规模与包结构

实测（`find`+`wc -l`，与卡片 1534/178,776 的差异是卡片行数偏高约 1.5k）：

- 总 1534 个 `.java` / 177,242 行。分源集：`src/main` 1400 文件 / 165,851 行；`src/api` 134 文件 / 11,391 行。
- `src/main/java/me/desht/pneumaticcraft/` 五段：`common` 998 文件 / 119,181 行、`client` 345 / 41,371、`datagen` 31 / 4,094、`mixin` 19 / 306、`lib` 5 / 609，外加根目录 2 个入口类（`PneumaticCraftRepressurized.java` + `CapabilitySetup.java`，共 290 行）。
- common 内大包（文件数）：`block` 167、`drone` 152、`thirdparty` 124、`network` 82（GUI/BE 字段同步 + 70 个 payload）、`inventory` 67（菜单）、`item` 57、`hacking` 39、`registry` 28、`pneumatic_armor` 29、`sensor` 23、`recipes` 31、`util` 50、`config` 13、`tubemodules` 17、`entity` 24、`heat` 16、`fluid` 16、`upgrades` 9。
- client 内：`gui` 165（其中 `client/gui/programmer` 32 文件 2,485 行，是「每个编程模块一个子 GUI」的集中体现）、`render` 90、`pneumatic_armor` 48。
- api 内：`drone` 18、`crafting` 16、`client` 19、`item` 10、`misc` 11、`pneumatic_armor` 11、`universal_sensor` 7、`heat` 5、`tileentity` 6、`remote` 5、`registry` 1（`PNCRegistries`）。
- 最大源文件（行数，实测 `wc -l`）：`datagen/ModRecipeProvider.java` 1926、`common/entity/drone/DroneEntity.java` 1807、`client/gui/ProgrammerScreen.java` 1291、`common/block/entity/elevator/ElevatorBaseBlockEntity.java` 1086、`common/block/entity/drone/ProgrammableControllerBlockEntity.java` 952、`client/gui/widget/WidgetAnimatedStat.java` 885、`common/thirdparty/computer_common/DroneInterfaceBlockEntity.java` 867、`common/config/CommonConfig.java` 790、`common/block/entity/processing/PressureChamberValveBlockEntity.java` 789、`common/block/entity/utility/AirCannonBlockEntity.java` 785、`common/block/entity/utility/SecurityStationBlockEntity.java` 778、`common/block/entity/AbstractPneumaticCraftBlockEntity.java` 775。
- **检出完整性**：`find src -type f` 只有 1534 个 .java 加 1 个 .toml。也就是 `src/main/resources` 只剩 `META-INF/neoforge.mods.toml`，lang/模型/方块状态/Patchouli 手册/`mixins.pneumaticcraft.json` 全部缺失；`src/generated/resources`（build.gradle:102 声明的 datagen 输出）与 `src/test`（build.gradle:105-110 定义了 test sourceSet、:159-160 声明 junit5）都不在树里。因此本报告不引用任何 JSON/资产内容；第 6 节 mixin 配置的分包归属只能从 mods.toml 的 `[[mixins]]` 与 java 注解反推（未验证）。

## 3. 入口与注册

三个入口，全部是 NeoForge 惯用法，没有 coremod：

1. `PneumaticCraftRepressurized.java:69-101` —— `@Mod(Names.MOD_ID)` 构造器：先 `PneumaticRegistry.init(PneumaticCraftAPIHandler.getInstance())` 把 API 实现塞进静态服务定位器（:74），再 `ConfigHolder.init` / `AuxConfigHandler.preInit`（:76-77），把生命周期监听挂到 modBus，把游戏事件对象 `register` 到 forgeBus（:88-100，例如 `MiscEventHandler`、`PneumaticArmorHandler`、`UniversalSensorHandler`、`DroneSpecialVariableHandler`、`HackEventListener.getInstance()`、`PlayerLogoutTracker.INSTANCE`）。
2. `client/PneumaticCraftRepressurizedClient.java:78-97` —— `@Mod(value = Names.MOD_ID, dist = Dist.CLIENT)` 独立客户端入口：9 个 modBus `addListener`（渲染器/层/粒子/按键/Screen/GUI overlay），`modContainer.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new)`（:91）复用 NeoForge 通用配置界面；`onClientSetup`（:99-110）里注册"每个编程模块的编辑子 GUI 工厂"和"每个管子模块的 GUI 工厂"。
3. `datagen/DataGenerators.java:23-46` —— `@EventBusSubscriber` + `GatherDataEvent`，逐个 `addProvider`，并把 registry 类数据集中走 `RegistrySetBuilder` + `DatapackBuiltinEntriesProvider`（:54-64），还自己写了 `append(...)` 把 patch 后的 lookup 传给下游 tags provider（:66-68）。

关键片段（`PneumaticCraftRepressurized.java:103-114`）：

```java
private void newRegistries(NewRegistryEvent event) {
    thirdPartyPreInit();   // 在"确定装了哪些 mod"之后、注册表初始化之前才做三方发现
    event.register(PNCRegistries.HOE_HANDLER_REGISTRY);
    event.register(PNCRegistries.HARVEST_HANDLER_REGISTRY);
    event.register(PNCRegistries.PROG_WIDGETS_REGISTRY);
    event.register(PNCRegistries.PLAYER_MATCHER_REGISTRY);
    event.register(PNCRegistries.AREA_TYPE_SERIALIZER_REGISTRY);
    event.register(PNCRegistries.REMOTE_WIDGETS_REGISTRY);
}
```

注册方式：28 个 `common/registry/Mod*.java` 各持一个 `DeferredRegister`，由 `registerAllDeferredRegistryObjects(modBus)` 一次性挂总线（`PneumaticCraftRepressurized.java:125-159`，包括 `ModDataComponents`、`ModAttachmentTypes`、`ModGameEvents` 与 6 个自定义注册表的 deferred）。自定义注册表的"注册即编解码"模式见 `common/registry/ModProgWidgetTypes.java:32-34`：`register(name, factory, CODEC, STREAM_CODEC)` 三件套，注册表本体在 `api/registry/PNCRegistries.java:17-40`，其中 `PROG_WIDGETS`、`AREA_TYPE_SERIALIZER`、`REMOTE_WIDGETS` 用 `.sync(true)`（网络按名编解码的前提）。能力集中注册在 `CapabilitySetup.java:23-87`，其中 :53-76 遍历 `ModBlockEntityTypes.streamBlockEntities()`，靠 BE 基类的 `hasItemCapability()/hasFluidCapability()/hasEnergyCapability()` 虚方法决定注册哪个能力——新机器不需要再写一遍能力注册。事件总线订阅面：`@EventBusSubscriber` 出现在 31 个文件里。

## 4. 核心系统

### 4.1 无人机程序：可视化模块 → Goal 序列

**数据表示**。程序不是一个枚举任务列表，而是一组 `IProgWidget`（`api/drone/IProgWidget.java`）实例，每个实例带网格坐标（`PositionFields`，`common/drone/progwidgets/ProgWidget.java:59-63`）和"下一步连接"。语义靠三个接口方法表达：`getWidgetAI(drone, widget)` 与 `getWidgetTargetAI(...)`（`IProgWidget.java:89,97`）返回原版 `Goal`，`getOutputWidget(drone, allWidgets)`（:121）返回下一模块。模块的参数/黑白名单槽用 `getParameters()`/`returnType()`（:129-147）声明，`ProgWidget` 构造器按参数数分配 `IProgWidget[2*n]`（`ProgWidget.java:70-79`）——右侧白名单、左侧黑名单共用一套索引。子接口即能力标签：`ICondition`、`IJumpBackWidget`、`IMaxActions`、`IVariableWidget`、`IAreaProvider` 等，`common/drone/progwidgets/` 下 99 个文件里 68 个是 `ProgWidget*` 具体实现。
**拓扑重建**。连接关系不入 NBT：`common/drone/ProgWidgetUtils.java:66-130` 的 `updatePuzzleConnections()` 先把所有 widget 按 `PositionFields` 建 `Map` 索引（注释明写这让整体是 O(n)），再两轮扫描把"下方/右/左"的邻居接成 step/参数连接。玩家拖动模块 = 改坐标 → 重算拓扑。
**执行与节流**。`common/drone/ai/DroneAIManager.java` 是手写的 `GoalSelector` 复刻（文件头 :50-53 直说"因为原版类需要一堆 AT，我把大部分抄了过来"）：`TICK_RATE = 3`（:56），`onUpdateTasks()`（:369-439）每 tick 都跑当前执行中的 goal，只在 `tickCount++ % 3 == 0` 那拍才做 `canUse` 重估 + `updateWidgetFlow()` 推进程序；`canUse`/`areTasksCompatible`（:455-482）用原版 `Goal.Flag` 集合判互斥。`setActiveWidget()`（:263-306）在跳过无 AI 的模块时用 `Set<IProgWidget> visitedWidgets` 防死循环（:270-271），遇到跳转（`getOutputWidget() != 直下模块`）就 `addJumpBackWidget()` 压栈，栈深 >100 直接 `drone.overload("jumpStackTooLarge", ...)` 停程序（:308-320）——**程序化行为必须有硬上限，这条最容易被忽略**。
**运行态变量**。`DroneAIManager` 自己实现 `IVariableProvider`，坐标/物品变量各一张 `Map`，`writeToNBT/readFromNBT`（:138-179）用 `BlockPos.CODEC` / `ItemStack.OPTIONAL_CODEC` 编解码；变量名前缀分作用域：`$` 走 `SpecialVariableRetrievalEvent` 事件（:183-186）、`%`/`#` 走跨无人机全局变量（`common/variables/GlobalVariableHelper`），裸名是本机私有（:187-191）。
**与无人机无关的同构复用**：`DroneAIManager` 的持有者是 `IDroneBase`，所以 `ProgrammableControllerBlockEntity`（952 行）能跑同一套程序而无实体，ComputerCraft 的 `DroneInterfaceBlockEntity` 用 `DroneAIExternalProgram` 嵌套子管理器（`DroneAIManager.java:130-132`、`connectVariables` :117-120）。

### 4.2 程序的存储与跨端流转

一份程序有四种表示，全部来自同一对编解码器：`ProgWidget.java:48-53` 的 `CODEC = registry.byNameCodec().dispatch(IProgWidget::getType, ProgWidgetType::codec)` 与 `STREAM_CODEC = ByteBufCodecs.registry(PROG_WIDGETS_KEY).dispatch(...)`。因此：
- 存 BE/实体 NBT：`DroneEntity.java:1136` `tag.put(NBT_WIDGETS, ProgWidgetUtils.putWidgetsToNBT(...))`，:1174 反向。
- 存物品组件：`common/drone/progwidgets/SavedDroneProgram.java:23-30` 一个不可变包装 + `Codec`/`StreamCodec`，注册为数据组件（`ModDataComponents.SAVED_DRONE_PROGRAM`，:47-53 提供 `fromItemStack/writeToItem`）。放无人机 → `readFromItemStack`（`DroneEntity.java:331-335`），收无人机 → `writeToItemStack`（:356-377）。这是 1.20.5+ 组件化最干净的落地样例：**行为脚本作为一个数据组件在"实体—物品—GUI"之间流转**，还自带 `getRequiredPuzzlePieces()`（:65-67，`freeToUse()` 的模块不计费）与 `isValidForDrone()`（:69-71，按无人机类型筛掉不支持的模块）。
- 网络同步 GUI 编辑：`PacketProgrammerSync`（`common/network/PacketProgrammerSync.java:40-69`）双向，payload 就是 `List<IProgWidget>` 的 StreamCodec，`handle` 复用 `PacketUtil.getBlockEntity` 定位 BE。
- 剪贴板/Pastebin JSON：`ProgWidgetUtils.java:30-48` 用 `Versioned.CODEC`（`ProgWidget.JSON_VERSION = 3`，:53）在 `JsonOps` 上解析/导出，即玩家分享的程序文本，带版本号。
**运行时只同步极少量东西**：`SynchedEntityData` 里只有 `PROGRAM_KEY`（当前活动模块的注册名）、`ACTIVE_WIDGET`（索引）、`LABEL`（标签名）等 14 个标量（`DroneEntity.java:166-179`、`defineSynchedData` :380-397、`setActiveProgram` :787-789）。完整模块列表只在玩家显式开启调试时按需下发（`common/debug/DroneDebugger.java:63-71`：先 `PacketSyncDroneProgWidgets` 再补发历史调试条目）。

### 4.3 寻路、卡死兜底与区块加载（读者最关心的坑）

- 导航器：`DroneEntity.java:306-312` `createNavigation` 返回 `EntityPathNavigateDrone`（`FlyingPathNavigation`），节点评估器换成 `NodeProcessorDrone`（`drone/NodeProcessorDrone.java:24-31`，在 `FlyNodeEvaluator` 上叠一层 `isBlockValidPathfindBlock` 白名单）。
- **路径失败的兜底是一等公民**：`drone/EntityPathNavigateDrone.java:69-127` 的 `createPath` 处理三种"到不了"：目标点非满方块（半砖/管道）时把精度从 0 放宽到 1；已在 0.75 距离内直接造一条单节点 Path 当作到达；下方碰撞盒 `maxY > 1`（墙/栅栏）时强制 accuracy=1。路径终点距目标 >accuracy 判为无效（:122-126）。无效且允许时启动**传送兜底**：`teleportCounter` 计时 120 tick（:51,145-179），期间喷粒子、结束后 `moveTo(null)` + 直接 `setWantedPosition` 并扣 `DRONE_USAGE_TELEPORT` 空气。`isDone()`（:139-141）在传送进行中返回 false，避免上层 goal 以为到位。
- **区块边界**：`checkForChunkLoading(pos)`（:239-241）= `配置允许 navigate 未加载区块 || level.isLoaded(pos)`；`moveTo(Path,...)`（:247-255）在目标未加载时**直接拒绝并写一条调试条目** `"progWidget.general.debug.unloadedChunk"`，把原因暴露给玩家而不是让无人机撞空气墙。传送前同样只查一次（:129-133，另含安全站保护区与 `maxDroneTeleportRange` 判定）。
- **谁负责让区块活着**：升级决定半径——`DroneEntity.java:703-705` `shouldLoadChunk(cp)` 用曼哈顿距离 < 红石升级数；:652-655 有升级时建 `DynamicChunkLoader` 并跟 `prevChunkPos`。`common/util/chunkloading/DynamicChunkLoader.java:41-58` 只对 3×3 候选做增删差集，:74-79 用 `TicketController.forceChunk` 发放票据；票据控制器由 modBus 注册（`PneumaticCraftRepressurized.java:83`）。**并且卸载条件是"主人离线超时"**：`shouldLoadChunk` 先问 `PlayerLogoutTracker.isPlayerLoggedOutTooLong(...)`（`DynamicChunkLoader.java:69-72`，`PlayerLogoutTracker.java:27-45` 记 `Map<UUID,Long>` 登出时间戳，从未上线返回 `Long.MAX_VALUE`）。同一份 `DynamicChunkLoader` 也被 Programmable Controller 复用（`forProgrammableController`，:36-38）。
- **区块快照**：动作 goal 不直接读 level，`DroneAIBlockInteraction.java:58,80` 在 start 时拿 `progWidget.getChunkCache(level)`，即 `ProgWidgetAreaItemBase.java:86-89` 按区域外接盒构造的 `ChunkCache`；同一 goal 内所有方块查询走它。
- **并发工作互斥**：`drone/DroneClaimManager.java:28-53` 按维度一个实例，`Map<BlockPos,Integer>` 记认领代龄，`tick()` 里超过 `TIMEOUT = DroneAIManager.TICK_RATE + 1` 就清（防死掉的无人机永久占位），goal 在决定目标与执行时 `claim()`（`DroneAIBlockInteraction.java:210,255`）。

### 4.4 组件化机器：升级槽 + 管子模块 + 能力/属性聚合

三层可组合部件，各自有独立的"聚合与序列化"写法：

1. **升级槽**：BE 基类内嵌 `UpgradeHandler extends BaseItemStackHandler`（`AbstractPneumaticCraftBlockEntity.java:739-775`），`isItemValid` = 适用 + 同种唯一，`getStackLimit` 直接向 DB 问上限，`onContentsChanged` 只做 `upgradeCache.invalidateCache()`。适用矩阵在 `common/upgrades/ApplicableUpgradesDB.java:42-49`：三张 Guava `Table`（`BlockEntityType×PNCUpgrade×maxCount`、`EntityType×...`、`Item×...`），全部 `Tables.synchronizedTable`。声明侧是很干净的 DSL（`UpgradesDBSetup.java:29-64`）：`new Builder().with(VOLUME, 25).with(SPEED, 10)...`，再用 `Builder.copyOf(BASIC_DRONE_UPGRADES).with(MINIGUN, 1)` 做**类型间继承**——五种无人机的升级差异全靠组合，不靠重写。查询走 `UpgradeCache`（`upgrades/UpgradeCache.java:30-77`）：`byte[] countCache` 按 upgrade 的注册表数字 ID 索引，`invalidateCache()` 置 null 即下次查询懒重建，重建时顺便 `holder.onUpgradesChanged()`。
2. **管子模块**（真正插在机器六个面上的组件）：`tubemodules/AbstractTubeModule.java:49-83` 一个模块绑 `Direction` + 宿主 `PressureTubeBlockEntity`，构造时按宽/高算好 6 个朝向的 `VoxelShape[]`；类型身份直接借用物品注册名（`getType()` :191-196、`getInternalId()` :86-88），**没有单独的模块类型注册表**，宿主用 `EnumMap<Direction, AbstractTubeModule>` 存（`PressureTubeBlockEntity.java:74`），放置/替换见 :137-144、`mayPlaceModule` 规则（inline 模块每管只允许一个）见 :286-301。序列化是手写 NBT（`AbstractTubeModule.java:156-171` 存 `dir/lowerBound/higherBound/upgraded/advancedConfig`，宿主 `writeModulesToNBT` :111-126 存 `type` 名），**未走 Codec**，与 4.2 的 progwidget 风格不一致——这是同一个作者在不同年代留下的两套写法。
3. **BE ↔ ItemStack 的隐式组件迁移**：`AbstractPneumaticCraftBlockEntity.java:660-715` 覆写 `applyImplicitComponents`/`collectImplicitComponents`，把储罐内容、红石控制模式、侧面配置、升级、空气量分别落成数据组件（`SAVED_REDSTONE_CONTROLLER`/`SAVED_SIDE_CONFIG`/`ITEM_UPGRADES`/`AIR`），并且只在 `shouldPreserveStateOnBreak()`（shift-wrench，:628-632）时才收集，避免误保留。空气量还走 `handler.addPendingAir(...)`，等 volume 升级恢复后再结算（`MachineAirHandler.java:130-140`）。
另外属性聚合的边界很清晰：机器是否可连某面由 `canConnectPneumatic(dir)`（`AbstractAirHandlingBlockEntity.java:63-77`）决定，`initializeHullAirHandlers()`（:147-156）把 6 面的 handler 收成 `IdentityHashMap<handler, EnumSet<Direction>>` 再 `setConnectableFaces`，`handleUpdateTag`/`onLoad`（:81-93）、旋转（:124-131）、邻居方块更新（:171-174）三处都会重算。

### 4.5 空气"网络"：没有图，只有本地扩散 + 懒缓存的模块网

对照库里已挖的 Mekanism 报告（`分析报告/_分析报告/mekanism__Mekanism.md`）：那份只覆盖到 transmitter 包结构，未展开其网格 tick 算法，而本检出里没有 refinedstorage2 报告，所以这里**只给本仓库实测结论**，不做跨仓库优劣判断。

- 压缩气**不做全局图合并**：`common/capabilities/MachineAirHandler.java` 每个 handler 每 tick 自己扩散（:126-165 `tick()` → :295-322 `disperseAir()`）。算法是"我 + 所有更低压的邻居"求总容积/总气量，按邻居容积比例算目标量，`setAirToDisperse(max(0, target - 现有))` 明确**禁止回流**（:310-311），最后逐邻居 `min(maxDispersion, toDisperse)` 转移（:315-322）。
- 限频是**每连接**的：`getMaxDispersion(owner, dir)`（:380-384）委托宿主 `IAirListener`，管子的实现（`PressureTubeBlockEntity.java:246-251`）在对应面插了 `IInfluenceDispersing` 模块时返回模块给的流量上限（`RegulatorModule.java:46`、`VacuumModule.java:109`、`FlowDetectorModule.java:65`）——组件化机器与"网络限流"由此正交组合。
- 邻居查询不重复扫 level：`neighbourAirHandlers` 是 `EnumMap<Direction, BlockCapabilityCache<...>>`（字段 `:62`），首次用时 `BlockCapabilityCache.create(...)`（:274-292），失效由 `setChanged/invalidated` 回调处理。
- **跨端不是同步整个网络，而是脏 + 降频**：服务端只在"漏气状态改变"或"正在漏气且 `(gameTime & 0x1f) == 0`"时发一个 `PacketUpdatePressureBlock`（:164-170），即约 32 tick 一次；客户端只跑同一 handler 的粒子/音效（`AbstractAirHandlingBlockEntity.java:96-101` 注释写明"需要客户端也 tick，为了漏气粒子和声音"）。过压破坏是概率化的（`MachineAirHandler.java:188-201`：越接近 critical 越可能爆炸/吱嘎响），且刻意在服务启动 20 tick 内跳过（:157-159）。
- 真正需要"图"的是**联动型模块**（红石/恒温器/物流），它们才走 `common/tubemodules/ModuleNetworkManager.java`：`Map<AbstractTubeModule, Set<...>> connectionCache` + 单一 `needInvalidate` 布尔（:36-56），`getConnectedModules()` 命中就返回；`invalidateCache()` 是**整表清空**的粗粒度脏标记，调用点只有管子增删/方块变化（`PressureTubeBlockEntity.java:317,357`、`PressureTubeBlock.java:185`）。连通性计算 `computeConnectedTubes`（:62-85）用 `ArrayDeque` BFS，两侧都问 `ITubeNetworkConnector.canConnectToNetwork`，并靠 `traversedPositions` 去重、`level.isLoaded(pos1)` 跳过未加载。缓存按 `Map<ResourceLocation, ModuleNetworkManager>` 分维度，`serverStopping` 里 `ModuleNetworkManager.clear()`（`PneumaticCraftRepressurized.java:195`）。
- **物品/流体物流另起一套**，与空气无关：`common/drone/LogisticsManager.java` 把物流半方块按 4 个优先级装进 `List<List<Frame>>`（:34-50），`getTasks()`（:52-115）在有人查询时才现算 provider→requester 配对（pull 式，无预建任务表），一旦成功就把 requester/provider 轮转到列表尾实现**round-robin 公平**（:100-110），无人机路径还会先问 `frame.isObstructed(PathComputationType.AIR)` 跳过堵住的站点（:60-62, :71-73）。

### 4.6 配方缓存与 /reload 一致性

`common/recipes/RecipeCache.java:11-29` 是定长 1024 的 `Int2ObjectLinkedOpenHashMap` LRU（`getAndMoveToFirst` 命中即前移，`removeLast` 淘汰，key 是自定义 `IntSupplier` 算出的输入哈希）。`PneumaticCraftRecipeType.java:68-100` 每个类型自己缓存 `Map<RL, RecipeHolder>`，并在这一步做需要跨类型合并的预处理（assembly drill+laser 合成链 :88-95、fluid mixer 的输入并集）。失效路径集中且**必须通知客户端**：`clearCachedRecipes()`（:137-155）除了清各类缓存，还显式重置 heat/仓库存/燃料/方块热属性等派生缓存；`CacheReloadListener.reload()`（:156-168）在准备阶段调它并 `sendToAll(PacketClearRecipeCache.INSTANCE)`。监听器在 `PneumaticCraftRepressurized.java:182-184` 通过 `AddReloadListenerEvent` 挂上。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **Payload**：`common/network/NetworkHandler.java` 在 `RegisterPayloadHandlersEvent` 里用 `event.registrar(MOD_ID).versioned("1")` 显式注册 **70** 个 `registrar.playToServer/playToClient/playBidirectional`（分节注释：misc 上行/下行、tube modules、amadron、hacking、pneumatic armor、drone），命名规整为 `PacketXxx.TYPE + STREAM_CODEC + ::handle`。三种值得抄的细节：(a) `PacketUtil.getBlockEntity`（`network/PacketUtil.java:41-58`）在服务端**不信客户端给的 BlockPos**，改从 `player.containerMenu` 取 BE 并核对坐标；(b) `DronePacket`（`network/DronePacket.java:21-60`）把"打给飞行无人机"和"打给 Programmable Controller 方块"统一成 `DroneTarget(Either<Integer,BlockPos>)`，一个 `handle` 静态方法分诊；(c) `ILargePayload`（:22-30）标记可能超 32000 字节的消息自带 `dumpToBuffer/handleLargePayload`。
- **字段级同步框架**（GUI 与远端描述包共用）：三种注解 `@DescSynced`（64 格内所有玩家）、`@GuiSynced`（仅开容器者）、`@LazySynced`/`@FilteredSynced`（`common/network/DescSynced.java:23-33`、`GuiSynced.java:23-33`）。`NetworkUtils.getSyncedFields(obj, 注解)`（`network/NetworkUtils.java:41-53`）沿继承链反射扫描，数组字段自动展开成多个 `SyncedField`（:55-90），支持 int/float/boolean/String/ItemStack/FluidTank/IItemHandler 等（`SyncedField.java:55-66` 的 `update()` 做"与上次值比较"判脏）。BE 侧：`AbstractPneumaticCraftBlockEntity.java:183-196` 懒建字段表并用 `BitSet fieldsToSync` 记脏位，:220-242 的 `defaultServerTick()` 每拍比较、非空即 `sendDescriptionPacket()`（:198-210，`hasData()` 才发，且 `forceFullSync` 给跨线程的 CC:Tweaked Lua 用，:216-217）。菜单侧：`AbstractPneumaticCraftMenu.java:113-145` 在 `broadcastChanges()` 里只给"值变了"的字段按 `idx` 发 `PacketUpdateGui`，玩家集合靠 `p.containerMenu == this` 过滤。
- **数据驱动程度**（哪些能靠 JSON、哪些必须写 Java）：
  - 走 Codec/JSON：全部 progwidget 与其 area 子类型（`api/drone/area/AreaTypeSerializer.java:9-33` 是 `MapCodec + StreamCodec + defaultSupplier` 三元组）、机器配方类型（`common/recipes/machine/` 10 个 `*RecipeImpl` + `common/recipes/assembly/`）、Amadron 交易作为配方类型（`recipes/amadron/AmadronOffer.java`，`common/amadron/AmadronOfferManager.java:64-66` 注明"静态/周期交易从配方 datapack 读取"）、世界 damage type / tags / loot / advancements 由 datagen 产出。
  - 必须写 Java：新 progwidget（要实现 `getWidgetAI` 并给 Goal 类）、新管子模块（继承 `AbstractTubeModule` 并手写 NBT）、新 BE、升级适用矩阵（`UpgradesDBSetup`）、`HackManager.addDefaultEntries()`、`HeatBehaviourManager` 等启动期硬编码表。
  - 程序级 JSON：玩家侧的程序文本 `ProgWidgetUtils.java:30-48`（带 `JSON_VERSION`），以及管理员用的 `common/config/subconfig/ProgWidgetConfig.java:21-70` —— 一个 `AuxConfigJson` 子类，写 `blacklist` + 顺带 dump `allWidgets` 参考表，被 `IProgWidget.isAvailable()` 消费（`ProgWidget.java` 的 `isAvailable`，`SavedDroneProgram.isValidForDrone` 同族），即"禁用某模块"是配置而非 datapack。
- **配置**：`common/config/` = `ModConfigSpec` 三件套 + 装配器。`CommonConfig.java`（790 行）用静态内嵌类分组（`General`/`Worldgen`/`Machines`/`Drones`/…），字段全是 `ConfigValue`，`ConfigHolder` 负责 build，`ConfigHelper.common().drones.xxx.get()` 是全局访问点（如 `EntityPathNavigateDrone.java:240`、`DroneAIManager.java:370`）。旁路配置 `config/subconfig/` 是**手写 JSON 文件**体系：`IAuxConfig`（:39-55 `preInit/postInit/clear/useWorldSpecificDir`）+ `AuxConfigHandler` 支持"按世界单独存"（单机切服时 `clearPerWorldConfigs()`，`PneumaticCraftRepressurized.java:194-201`），里面放玩家护甲 HUD 布局、微型导弹（micromissile）默认值、Amadron 玩家报价、模块黑名单。
- **datagen**：`datagen/` 31 文件，一 provider 一类（`ModRecipeProvider.java` 1926 行为最大文件），配方按 mod 自己的类型建 builder：`datagen/recipe/` 下 13 个 `*RecipeBuilder`（PressureChamber/Refinery/FluidMixer/HeatFrameCooling/Amadron/Assembly/CompressorUpgrade/FuelQuality/HeatProperties…）+ `AbstractPNCRecipeBuilder` 打底，registry 数据走 `RegistrySetBuilder`（`DataGenerators.java:54-64`）。输出目录在 build.gradle 里声明为 `src/generated/resources` 并被 main resources 引用（:102），但本检出未生成。

## 6. Mixin

有，规模小，且分两类（`src/main/java/me/desht/pneumaticcraft/mixin/`，19 文件 306 行；`mixins.pneumaticcraft.json` 不在检出内，包归属按目录名与 mods.toml 的 `[[mixins]]` 反推）：

- `mixin/accessors/` 17 个纯 `@Mixin + @Accessor/@Invoker` 的读取器，无逻辑注入。代表：`BlockEntityTypeAccess.java:10-12`（取 `BlockEntityType.validBlocks`，被 `ApplicableUpgradesDB` 用来反查一个 BE 类型对应哪些方块，import 见 :28、使用点见 :187）；`ServerPlayerGameModeAccess.java:7-12`（`isDestroyingBlock`/`hasDelayedDestroy`，让挖方块 AI 判断假玩家是否已在破坏，`DroneAIDig.java:116-118`）；另有 `EntityAccess`、`MobAccess`、`ItemEntityAccess`、`ShulkerAccess`、`WitchAccess`、`BaseSpawnerAccess`、`TooltipAccess`、`ShapedRecipeAccess` 等，全部是"原版私有字段/方法不够用"的最小出口。
- `mixin/coremods/` 2 个真注入：`LivingEntityMixin.java:15-24` 在 `LivingEntity#onEquipItem` 中 `isSilent()` 调用点前注入，检测服务端玩家穿/换气动护甲（并靠 `getComponentsPatch()` 比较避免无关更新）；`BaseSpawnerMixin.java:12-14` 在 `BaseSpawner#isNearPlayer` 的 RETURN 处 cancellable 注入（供加压刷怪笼接管玩家判定）。选点特征：都是"事件点在原版方法中段/返回处，用事件替代会漏时机"的场景，其余一律走 NeoForge 事件。

## 7. 值得学的 5 条

1. **一份模型、四种表示，全靠 registry 的 dispatch Codec/StreamCodec**：`src/main/java/me/desht/pneumaticcraft/common/drone/progwidgets/ProgWidget.java:48-53` + `common/drone/progwidgets/SavedDroneProgram.java:23-30`。行为脚本因此可以零成本地进 NBT、进物品数据组件、进网络包、进玩家可分享的 JSON（`common/drone/ProgWidgetUtils.java:30-48`）。蜂群的 NPC 行为表应该照抄这个形状：定义一个自定义注册表 + `.sync(true)`，让 `Codec`/`StreamCodec` 成对挂在类型上，从此不再有"序列化写三遍"。
2. **执行引擎的节流与硬上限**：`common/drone/ai/DroneAIManager.java:56,369-410`（每 tick 只跑执行中 goal 的 `tick()`，重估与推进程序每 3 tick 一次）+ `:270-271,308-320`（visited 集合防死循环、跳转栈 >100 直接停程序并把原因报给玩家）。任何"分支/循环式行为树"都必须自带这两道闸门，否则一个玩家手滑就锁死服务器 tick。
3. **把"为什么没干活"做成可观测数据**：`src/api/java/me/desht/pneumaticcraft/api/drone/debug/DroneDebugEntry.java:10-16`（`record(progWidgetIndex, message, Optional<BlockPos>, receivedTime)` + StreamCodec）、`common/debug/DroneDebugger.java:38-51`（服务端记一条并只推给订阅玩家）、`common/drone/EntityPathNavigateDrone.java:247-255`（拒绝 moveTo 未加载区块时写 `unloadedChunk` 调试条目）。条目**带模块索引**，所以 GUI 能在具体那块程序模块上高亮原因。分层行为系统最容易缺的就是这个，抄它。
4. **服务端不接受客户端坐标**：`common/network/PacketUtil.java:41-58` —— 处理上行 GUI 包时从 `player.containerMenu` 反查 BE，只把客户端给的 `BlockPos` 当一致性校验。所有"改机器配置"的包都该走这一条，比逐包再写权限判断可靠。配套：`common/inventory/AbstractPneumaticCraftMenu.java:113-145` 的按字段判脏同步，比原版 `DataSlot`（每 tick 全量 int）表达力强且能传 ItemStack/FluidStack。
5. **区块加载的责任链写成一个可复用对象**：`common/util/chunkloading/DynamicChunkLoader.java:41-79` —— 3×3 候选差集 + `TicketController` + `(主人在线? / 半径?)` 谓词（`PlayerLogoutTracker.java:27-45`、`DroneEntity.java:703-705`），且 `forDrone`/`forProgrammableController` 两个工厂把"跟随实体"和"固定方块"统一成 `Either`。领地建筑/巡逻单位要长期占区块的话，这是能直接搬的实现骨架，别自己写 `forceChunk` 循环。

### 结论：给「蜂群」与「新星殖民地」的可搬形状（对应本仓库重点问题⑥）

- **给「蜂群」分层行为系统，形状 1：程序与执行器分离 + 拓扑不入库。** 行为单元（对应 `IProgWidget`）只携带"配置数据 + 造 Goal 的工厂方法"（`api/drone/IProgWidget.java:89,97,121`），连接关系每次装载后由坐标重算（`common/drone/ProgWidgetUtils.java:66-130`，O(n)）。好处是编辑期与运行期完全解耦：GUI 拖动即改坐标、无副作用；存/传/序列化只搬数据。领地建筑的"可组合指令表"照这个分法写，能省掉一整套"运行时对象也参与序列化"的坑。
- **给「蜂群」，形状 2：三级同步预算。** ① 结构（行为表）只在物品/BE NBT 与按需包里走（`SavedDroneProgram.java:23-30` + `debug/DroneDebugger.java:63-71`）；② 运行时状态只同步 `SynchedEntityData` 的 14 个标量（`DroneEntity.java:166-179,380-397`，含"当前执行到第几个模块"的索引 :787-789）；③ GUI 字段按脏位/`BitSet` 聚合发一次描述包（`AbstractPneumaticCraftBlockEntity.java:183-210,220-242`）。NPC 数量一多，唯一能扛住的就是这种"结构懒同步、状态窄同步、界面判脏同步"的分层。另外把 `DroneAIManager.TICK_RATE=3` 的"重估降频"（`DroneAIManager.java:56,383`）和 `DroneClaimManager` 的 TTL 认领（`DroneClaimManager.java:28-53`）一起搬走。
- **给「新星殖民地」到港/物流，1 条：pull 式优先级网络 + 轮转公平，不预建任务表。** `common/drone/LogisticsManager.java:34-115`：站点按 4 个优先级分桶登记，任务只在有货/有无人机来问时现算，命中后把 provider 与 requester 各自 `add(remove(idx))` 轮到队尾（:100-110），无人机侧还先问 `isObstructed(PathComputationType.AIR)` 跳过堵死站点（:60-62）。每日结算若要"到港→分派给谁"，这个形状比"每次结算全表扫描"稳：优先级桶 + 游标轮转是 O(命中数)，还天然带反饿死。配套的缓存一致性做法见 `PneumaticCraftRecipeType.java:137-168`（派生缓存集中清理 + reload 时广播失效包）。
- **1000+ 文件规模下的一处工程化优点：按"宿主 mod"而非"功能"切分集成层，且可选依赖零携带。** 证据：`src/main/java/me/desht/pneumaticcraft/common/thirdparty/` 下 23 个按 mod 命名的子包（`ae2/ botania/ cofhcore/ coldsweat/ computercraft/ create/ curios/ ffs/ ftbteams/ gamestages/ immersiveengineering/ mekanism/ patchouli/ theoneprobe/` 等）实现同一个 `IThirdParty`，由 `ThirdPartyManager.java:42-56` 集中 `ModList` 探测并按 `ModType` 分桶，`build.gradle:166-212` 保证这些库全部 `compileOnly`/`localRuntime`；同时能力注册不在各集成里散落，而是收敛到 `CapabilitySetup.java:23-87` 一处。对读者的意义：新星/蜂群以后要接 JEI、FTB Teams、CC:Tweaked 时，"一个 mod 一个包 + 一个接口 + 一个 manager + 一处能力注册"这套骨架在 1500 文件规模下仍然找得到路。次要但同样加分的两点：注册表类一律 `ModXxx.java` 命名并集中在 `common/registry/`（28 文件），日志出口唯一（`lib/Log.java`，`lib` 包 5 文件 609 行）。
- **遗留 / 未验证**：`src/generated/resources`、`src/test`（build.gradle:105-110 有 sourceSet、:159-160 声明 junit5）、`mixins.pneumaticcraft.json` 与全部资产都不在检出内，故本报告对 datagen 产物内容、mixin 配置的分包归属、以及任何 lang/模型驱动的细节不做断言；与 refinedstorage2 / Mekanism 网格算法的横向对比未展开（库里那两份报告未覆盖对应内部，见 4.5 开头）。

## 8. 公开 API

它是明确给 addon 用的库：独立 `src/api` 源集 + `apiJar`（`build.gradle:93-118,235-249`），LGPL 头，坐标 `me.desht.pneumaticcraft:pneumaticcraft-repressurized`（另附 `-api` 与 `-sources`）。

- **入口包 `me.desht.pneumaticcraft.api`**：`PneumaticRegistry.java:42-72` 是静态服务定位器（实现方在 `common/PneumaticCraftAPIHandler`，由主类构造器 `init()` 注入，`PneumaticCraftRepressurized.java:74`），内部接口 `IPneumaticCraftInterface`（:80-102）暴露 11 个工厂/注册表访问器：air handler 工厂、client/common 护甲注册表、`IDroneRegistry`、`IHeatRegistry`、`IClientRegistry`、`ISensorRegistry`、`IItemRegistry`、`IUpgradeRegistry`、`IFuelRegistry`、`IWrenchRegistry`。同包 `PNCCapabilities.java` 提供自定义能力常量（`AIR_HANDLER_MACHINE/ENTITY/ITEM`、`HEAT_EXCHANGER_*`、`ENTITY_AUTOMATION`）。
- **自定义注册表 = addon 的主要扩展面**：`api/registry/PNCRegistries.java:17-40` 声明 6 个 `ResourceKey`+`Registry`（其中 progwidget、area 序列化器、remote widget 是 `.sync(true)`），主类在 `NewRegistryEvent` 注册进原版注册表（`PneumaticCraftRepressurized.java:103-114`），addon 侧只需 `DeferredRegister.create(PNCRegistries.PROG_WIDGETS_REGISTRY, "自己的modid")` 并给 `ProgWidgetType(name, factory, codec, streamCodec)`（参照 `common/registry/ModProgWidgetTypes.java:32-34`）。
- **扩展点接口（按能干什么分）**：
  - 无人机行为：`api/drone/IProgWidget`（:89,97 造 Goal；:121 控制流；:129-147 参数槽；:198-208 `WidgetDifficulty` 决定 GUI 里何时可见）、`ICustomBlockInteract`/`IBlockInteractHandler`、`IDrone`、`IPathNavigator`、`IPathfindHandler`、`area/AreaType`+`AreaTypeSerializer`、`debug/IDroneDebugger`，以及事件 `DroneConstructingEvent`、`DroneSuicideEvent`、`AmadronRetrievalEvent`、`SpecialVariableRetrievalEvent`（`DroneAIManager.java:183-186` 就是它的消费端——addon 可以往 `$xxx` 变量里塞自定义坐标）。
  - 机器与升级：`api/upgrade/PNCUpgrade`+`IUpgradeItem`+`IUpgradeRegistry`（:33/:41/:49 三个 `addApplicableUpgrades` 重载，addon 给自己的 BE/实体/物品声明可用升级与上限）、`api/tileentity/IAirHandler(Machine/Item/Factory)`+`IAirListener`（`getMaxDispersion`/`addConnectedPneumatics`/`onAirDispersion`，让 addon 机器接入扩散与限流）、`api/pressure/PressureTier`+`PressureHelper`、`api/block/ITubeNetworkConnector`（自己造可入网的管子）、`api/heat/*`（`HeatBehaviour`、`IHeatExchangerLogic`）、`api/harvesting/HarvestHandler`+`HoeHandler`（可收割方块注册，对应两个自定义注册表）。
  - 护甲/穿戴：`api/pneumatic_armor/IArmorUpgradeHandler`+`BaseArmorUpgradeHandler`+`ICommonArmorRegistry`（主类 `commonSetup` 里 `CommonUpgradeHandlers.init()` 填内置项，并在 `enqueueWork` 里 `freeze()` 关闭注册窗口，`PneumaticCraftRepressurized.java:166,175`——注册期结束的显式收口）、`api/client/pneumatic_helmet/*`（HUD 块追踪 `IBlockTrackEntry`）、`api/client/ITickableWidget`+`IGuiAnimatedStat`（addon 往 HUD 面板加控件）。
  - 其他：`api/remote/*`（远程热点小部件）、`api/universal_sensor/*`（可编程传感器）、`api/semiblock/*`、`api/crafting/recipe`+`ingredient`（配方类型与自定义 Ingredient）、`api/wrench/IWrenchRegistry`（让别的 mod 的扳手兼容）、`api/item/IProgrammable`（任何物品都能变可编程）。
- **接入方式**：addon 在 `build.gradle` 里 `compileOnly "me.desht.pneumaticcraft:pneumaticcraft-repressurized:<ver>+mc1.21.1"`（它自己正是这样消费 JEI/Mekanism/IE 的，`build.gradle:166-212`），运行期可选依赖用 mods.toml 的 `type="optional"` 声明（patchouli/jei/emi）；对未安装 mod 的兼容不在 addon 里做，而是在**它自己身上**由 `common/thirdparty/` 的 23 个按 mod 分包 + `IThirdParty` 接口 + `ThirdPartyManager.discoverMods()`（`common/thirdparty/ThirdPartyManager.java:42-70`）统一 `ModList` 探测、按 `ModType` 分桶、并留一个 `IMPLICIT_INIT` 空实现给注解式初始化的 mod。三方集成全部 `compileOnly`，主 jar 不携带任何可选 mod 的类。
- **稳定性策略**：`src/api` 内共 33 处 `@ApiStatus.Internal/Experimental/NonExtendable`；`NonExtendable` 专门钉在"实现由框架调用、addon 不得覆写"的方法上（如 `IProgWidget.java:31-56,141-156`、`PneumaticCraftRecipeType` 相关接口），而真正的扩展点保持可继承。这份"哪些能改哪些不能改"的显式契约，是它敢在 GPL/LGPL 之间切一刀的底气。
