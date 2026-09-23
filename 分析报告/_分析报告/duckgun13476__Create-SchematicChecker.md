# duckgun13476/Create-SchematicChecker 源码分析报告

## 1. 基本信息

- Mod 名：Create: Schematic Checker（CSC，服务端防护模组：扫描上传的 Create 蓝图并阻断/清洗恶意 NBT）；modId：`createschematicchecker`；作者：duckgun13476 / 团队 "Pink_Cats"
- 支持矩阵（`README.md`）：Forge 1.14.4/1.15.2/1.16.5/1.17.1/1.18.2/1.19.2/1.20.1（Create 0.2.3→6.0.x）+ Fabric 1.18.2/1.19.2/1.20.1/1.21.1 + NeoForge 1.21.1（Create 6.0.x）
- 许可证：GNU LGPL 3.0（`LICENSE.txt`、`project/neoforge/1.21.1-6.0.x/src/main/templates/META-INF/neoforge.mods.toml`）
- NeoForge 1.21.1 目标：`neo_version=21.1.219`、Java 21、Create `[6.0.1,)`、**额外必需 mod `torqueapi`**（版本范围由 `torque_api_version_range` 展开）
- Gradle：根工程只用 `fabric-loom 1.10.5`（`apply false`）+ `idea-ext`，真正的构建脚本在 `gradle/*.gradle` 与各版本子工程（`net.neoforged.moddev` / `moddev.legacyforge` + `curseforgegradle` + `silk` + `mod-publish-plugin`，见 `project/forge/1.20.1-6.0.x/build.gradle`）
- **架构要点**：依赖自制跨版本抽象层 `com.pinkcats.torque:TorqueAPI-layer-api`（`common/build.gradle` compileOnly），loader 实现 `TorqueAPI-<mc>-<loader>` 通过 `gradle/csc-torque-embed-modern.gradle`（及 legacy 版）内嵌进 jarJar

## 2. 源码规模与包结构

实测：**202 个 .java / 20528 行**。模块：`common` 50 文件 / 8411 行（与版本无关的扫描引擎）、`project` 152 文件 / 12117 行（每版本 9–17 文件、约 600–900 行的胶水层）、`global`（聚合任务）、`gradle-runners`、`update`（changelog）。

`common` 包（`common/src/main/java/com/Pink_Cats/createschematicchecker/`）：`core` + `core/BlueEngine`（+`checks`）、`core/ChainEngine`、`core/attach`、`FancyConfig`（7 文件）、`online`、`network`、`event`、`database`、`echo`（命令）、`lang`、`Compat/pattern_schematics`。
最大文件：`core/BlueEngine/NbtFunc.java` 1074、`FancyConfig/SimpleTomlEditor.java` 897、`FancyConfig/ConfigRegister.java` 717、`network/SimpleJsonParser.java` 535、`online/VersionChecker.java` 325、`core/ChainEngine/MagicChain.java` 325、`core/BlueEngine/BlockSweeper.java` 295、`core/BlueEngine/checks/TripwireDuperScanner.java` 257、`echo/CscCommandActions.java` 243。
NeoForge 1.21.1 子工程 12 文件 / 810 行：`Createschematicchecker`、`CscLifecycle`（在 common）、`event/CheckBlueprint` 141、`mixin/handleFinishedUploadMixin` 126、5 个 mixin、`Compat/PendingSchematicStore`。

## 3. 入口与注册

`project/neoforge/1.21.1-6.0.x/src/main/java/com/Pink_Cats/createschematicchecker/Createschematicchecker.java`：`@Mod(MODID)`，`CSC_VERSION = "0.21.18"` 是硬编码常量；构造器把 mod 事件总线（`FMLCommonSetupEvent`）、`ModEventHandler`、`GameEventHandler`（`ServerStartingEvent`/`ServerStoppingEvent`/`PlayerLoggedInEvent`/`RegisterCommandsEvent`）分别挂到 mod/游戏总线，并把 `new CheckBlueprint(new BlueCore())` 注册为事件监听器。

生命周期被抽到 common 的 `CscLifecycle`（`common/.../CscLifecycle.java`）：`commonSetup()` → `CSC_Variables_Load()/CSC_INIT()`；`serverStarting()` → 启动扫描线程池与在线任务、`injectCreateConfig()`（从 `AllConfigs.server().schematics/kinetics` 读 `schematicannonDelay`、`maxBeltLength`、`maxEjectorDistance`、`maxChassisRange`，并用**反射**探测 `maxChainConveyorLength` 判断 Create 6.0/0.5，见 `NeoForgeCreateConfigSource`）；`serverStopping()` 先停任务再落盘配置。
本模组**不用** NeoForge `ModConfigSpec`，`ModConfigEvent` 只当"重载触发器"用（`Config.java` 调 `CSC_RELOAD()`），真实配置是自研 `FancyConfig`（`config/CSC/config.toml`）。

## 4. 核心系统

1. **上传拦截链（mixin → 事件 → 异步任务 → 主线程回写）** — `mixin/handleFinishedUploadMixin.java`、`event/SchematicUploadEvent.java`、`event/CheckBlueprint.java`。要点：①`@Mixin(ServerSchematicLoader.class, remap=false)`，HEAD 注入用 `ThreadLocal` 记住 `玩家名/蓝图名` 组成 id，另一个 `@Inject(locals = LocalCapture.CAPTURE_FAILSOFT)` 在 `getTable` 调用前抓 `Level/BlockPos`；②`@Redirect` 拦截 `SchematicTableInventory.setStackInSlot`，slot==1（玩家拿到的蓝图物品）时不落槽，改写进 `Compat/PendingSchematicStore`（`ConcurrentHashMap<String,ItemStack>` + `PendingMeta(dim,pos)`）并**留空槽位**，保证未检的蓝图永不入包；③TAIL 注入 `NeoForge.EVENT_BUS.post(new SchematicUploadEvent(...))` 触发检查；④`CheckBlueprint.applyResultOnServerThread` 通过 `server.execute` 回到主线程，通过则 `table.inventory.setStackInSlot(1, pending)` 还原，拒绝则把 slot0 换成 `AllItems.EMPTY_SCHEMATIC`（若装了 `create_pattern_schematics` 则换对应空图样，见 `Compat/pattern_schematics/PatternSchematicsCompat.java`）。
2. **异步扫描调度** — `event/SchematicScanTasks.java`：单线程 `ThreadPoolExecutor`（`ArrayBlockingQueue(8)` + `AbortPolicy` + 守护线程工厂，启动时 `prestartCoreThread()`），`submit(scan, rejectedWhileRunning)` 在队列满时安全拒绝（直接判失败）而不是阻塞服务器线程；`stopServer()` 停服即 `shutdownNow()`，避免扫描任务比服务器活得久。
3. **NBT 检查引擎** — `core/BlueCore.java` + `core/BlueEngine/NbtFunc.java`。`BlueCore.SchematicBlueCore(blueprintId, CheatLog)`：解析路径 → `Nbt.readCompressed` → 可选备份 `config/CSC/backup/<user>/` → `NbtFunc.NBTCheck(...)` → 按结果上报样本 → 把清洗后的 NBT 写回 `./schematics/uploaded/<user>/`。`NBTCheck` 返回 `Map<String,Object>{CannotCheck,Problem,Cheat,WhiteListModFiltered,nbt_data}`，要点：①palette 归一化（缺 `Name` 的条目补 `minecraft:air`，与 `StructureTemplate` 行为对齐；空 `Name` 判 `CannotCheck` 并中断）；②逐方块/逐实体 `BaseBlockHandle`/实体处理，命中即写 `CheatLog`；③内置规则：`minecraft:sign` 含 `run_command`、`createbigcannons:fuzed_block` 内嵌物品 id 非白名单（含 `components.createbigcannons:fuze` 新格式解析）、`checks/IllegalEnchantmentScanner`（非法附魔）、`checks/TripwireDuperScanner`（绊线复制）、`checks/ClipboardSanitizer`（剪贴板）；④`BlockSweeper` 负责按配置清方块/清标签。
4. **声明式规则引擎 MagicChain** — `core/ChainEngine/MagicChain.java`（325 行）+ `core/ChainEngine/ConveyorInterface`。用字符串 DSL 描述 NBT 路径与操作：`ChainSplit`/`KnifeSplit` 切分（`ConfigValue.ChainSplit`/`KnifeSplit` 可配置），支持 `find`（按 id 计数，`SweeperIfHasId`）、`clear`、`replace`、`limit`（上下限）、`operate` 等分支，遍历出的 `CompoundTag` 上直接改 NBT；是"配置驱动扫描规则"的核心。
5. **自研配置框架 FancyConfig** — `FancyConfig/ConfigRegister.java`（717 行，全部配置项以 `ConfigBuild.define("core.Enable", true).comment(...)` 链式声明）、`ConfigValue.java`、`SimpleTomlEditor.java`（897 行，自写 TOML 读写）、`ConfigHook.java`、`FileIO.java`、`ConfigArchiveNotice/WhitelistModeNotice`。特色：`MIGRATABLE_CONFIG_KEYS` 白名单 + `ConfigVersion` + `ensureValidConfigToml()/archiveOutdatedConfigToml()` 实现**配置迁移/归档**；`Language` 键可切换 `CSCLanguage.translateDirect` 的翻译；配置项按 `core./debug./function./online.` 分组（如 `core.Enable`、`core.BanBlock`、`core.KillEntity`、`debug.EnableBackup`、`function.maxConveyorCheatDistanceLimit`、`online.report`）。
6. **在线层（规则热更 / 遥测 / 心跳）** — `network/OnlineTasks.java`、`network/SimpleJsonParser.java`（`UpdateRuleThread`）、`online/VersionChecker.java`（`disableSSLVerification()` + GET 拉取）、`online/OnlineInterface.java`（POST 端点硬编码 `https://mc.aisaveworld.tech:8144/`）、`online/NbtFileUploader.java` + `online/ReportQueue.java`（仅上报被判定 `CannotCheck/Problem/Cheat/WhitelistFiltered` 的样本，失败进 `config/CSC/report-queue/` 重试）、`online/SimpleHeartbeatPusher.java`。在线规则缓存于 `config/CSC/online/`，本地规则 `config/CSC/user_rule.json`（`online.enableManualConfig` 开关）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无自定义 payload 注册**；本模组的方向是"服务端校验别人的包"，即用 mixin 拦住 Create 的现有 C2S 包：`mixin/FilterScreenPacketMixin.java`（`FilterScreenPacket.handle` HEAD，`UPDATE_FILTER_ITEM` 时要求 `data` 有 `Slot`、槽位合法、`requested.getCount()==1` 且 `ItemItemStack.isSameItemSameComponents` 能在玩家背包里找到同物品，否则 `ci.cancel()`）、`mixin/ChainConveyorRidingPacketMixin.java`（`ServerboundChainConveyorRidingPacket.applySettings` HEAD，用 `Map<UUID,ChainRidingState>` 记录上次位置/时间，按 15° 采样链环 + 线段点距（阈值 1.5 格）与 `0.6 + |speed|/360*elapsedTicks*1.25` 上限判定，越界即 `ServerChainConveyorHandler.handleStopRidingPacket` 并取消——防止客户端伪造心跳重置坠落计数）、`mixin/RadialWrenchMenuSubmitPacketMixin.java`、`mixin/OpenEndedPipeMixin.java`（`removeFluidFromSpace` 中在 `VanillaFluidTargets.drainBlock` 之后修 Quark 熔岩流体化复制，`locals = CAPTURE_FAILHARD`）。每个包都受配置开关控制（`function.validateFilterScreenPacket` 等）。
- 配置：见第 4 节第 5 点（自研 TOML + `config/CSC/`）。
- 数据驱动：规则（内置 + `user_rule.json` + 在线 JSON）、语言（`lang/Message.java`、`CSCLanguage`）、日志（`database/SingleLog.CSC_MES/CSC_WARN` 双文件 + `DataCount` 计数）。
- datagen：**无**（无 provider、无生成资源）。

## 6. Mixin

- 配置：`common/src/main/resources/createschematicchecker.mixins.json`（默认，`compatibilityLevel: JAVA_17`）+ 各版本 `project/<loader>/<ver>/src/main/resources/createschematicchecker.mixins.json`（如 NeoForge 1.21.1 用 `JAVA_21`，多出 `FilterScreenPacketMixin`）；`gradle/csc-common.gradle` 的 `processResources` 会在目标自带配置文件时 `exclude` 共享默认文件，避免打包不存在的类名。
- 代表类与注入点（NeoForge 1.21.1）：`handleFinishedUploadMixin`（`ServerSchematicLoader#handleFinishedUpload`：HEAD + `LocalCapture.CAPTURE_FAILSOFT` + `@Redirect` 到 `SchematicTableInventory#setStackInSlot` + TAIL）、`FilterScreenPacketMixin`（`FilterScreenPacket#handle` HEAD）、`ChainConveyorRidingPacketMixin`（`applySettings(...)` HEAD）、`OpenEndedPipeMixin`（`removeFluidFromSpace` 中 INVOKE `VanillaFluidTargets;drainBlock`）、`RadialWrenchMenuSubmitPacketMixin`。全部 `remap=false`（Create 非 MC 类）。

## 7. 值得学的 5 条具体做法

1. **「先扣物、后检查、主线程回写」的三段式安全模型**：上传物品先进 `PendingSchematicStore` 并清空槽位，检查完再在主线程还原（`mixin/handleFinishedUploadMixin.java` + `event/CheckBlueprint.java`）；适用：任何"异步校验 + 需回滚游戏状态的拦截"。
2. **专用单线程池 + 有界队列 + AbortPolicy 做安全拒绝**：`SchematicScanTasks.submit(scan, rejectedWhileRunning)`，队列满时按失败处理而不是卡服（`event/SchematicScanTasks.java`）；适用：会读取大文件（蓝图/结构）的异步 IO。
3. **跨版本用「common + 自研抽象层 + jarJar 内嵌」而非多套代码**：`common/build.gradle` 只依赖 `TorqueAPI-layer-api`，NBT 用 `com.pinkcats.torque.layer...CompoundTag`，版本差异全压在每版本 ~10 个文件的胶水层（`gradle/csc-common.gradle` 把 `common/src/main/java` 加进各子工程 srcDir）；适用：想同时维护 1.14–1.21 多 loader。
4. **配置用白名单键做自动迁移**：`MIGRATABLE_CONFIG_KEYS` + `ConfigVersion` + `ensureValidConfigToml()/archiveOutdatedConfigToml()`（`FancyConfig/ConfigRegister.java`）；适用：多次改配置结构又不能丢用户设置。
5. **给不可信的第三方 C2S 包补服务端权威校验**：FilterScreen 要求物品真的在玩家背包、ChainRiding 用服务端位置/速度算位移上限（`mixin/FilterScreenPacketMixin.java`、`mixin/ChainConveyorRidingPacketMixin.java`）；适用：附属要堵别人 mod 的客户端信任漏洞。

另可参考的工程手段：`Message.diag("[Diag][类][阶段] ...")` 统一诊断日志、`/csc reload` 命令经 Torque 抽象注册（`echo/CscCommands.java`、`NeoForgeCommandEvents.register`）、Fabric 1.21.1 无 Create 时用 `project/stubs/create-fabric/1.21.1` 提供编译期桩类。

（非库模组，第 8 节不适用。）
