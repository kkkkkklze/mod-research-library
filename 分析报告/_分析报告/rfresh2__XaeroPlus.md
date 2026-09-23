# rfresh2/XaeroPlus 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：XaeroPlus / `xaeroplus`；作者：rfresh2；许可证：MIT（`forge/src/main/resources/META-INF/mods.toml`）
- 目标版本与加载器：`gradle.properties` 锁定 `minecraft_version=1.20.1`、`enabled_platforms=fabric,forge`、`mod_version=2.36.1`；README 徽章显示多 MC 版本（1.12.2 → 26.2）由仓库历史/分支发布，且**每个 XaeroPlus 版本只兼容特定 Xaero WorldMap/Minimap 版本**（`worldmap_version_*=1.46.0`、`minimap_version_*=26.5.0`）
- Gradle 插件：Architectury 体系 —— `xaeroplus-all.conventions` / `xaeroplus-platform.conventions`（`buildSrc/src/main/kotlin/`）+ architectury-plugin；`settings.gradle.kts` 用 version catalog 统一版本
- 关键编译依赖：`fabric-loader 0.15.11`、`fabric-api 0.92.3+1.20.1`、`forge 1.20.1-47.4.20`；**API 主体是被修改的 Xaero 系模组**（worldmap / minimap / xaerolib 1.7.3，`modCompileOnly` + 精确版本依赖）；`mixinextras 0.5.5`、`LambdaEvents 2.4.2`（自建事件总线）、`caffeine`、`org.rfresh.xerial:sqlite-jdbc:3.53.4.0`（**relocated sqlite** 避免与其它模组冲突）、`OldBiomes`、rfresh2 自维护的 `baritone-fabric/forge`、`worldtools 1.2.4`；兼容模组 sodium / embeddium / immediatelyfast / modmenu / OPAC / spark

## 2. 源码规模与包结构

实测：**271 个 .java / 23380 行**，其中 `common` 占 22252 行。包（文件数）：

- `xaeroplus.mixin.client`：61 + `mixin.client.mc`：6（**同时 mixin Xaero 与原生 MC 类**）
- `xaeroplus.module` + `module.impl`：2 + 26；`xaeroplus.settings`：10；`xaeroplus.event`：16
- `xaeroplus.util`：20 + `util.timer`：5；`feature/extensions`：15；`feature/render/*`（line 13 / ellipse 13 / highlight 11 / text 5 / shaders 5 / buffered 2 …）：约 50
- `feature/highlights` 7 + `highlights/db` 2；`feature/drawing` 7 + `drawing/db` 3；`feature/db` 2；`commands` 2
- 平台侧：`fabric` 14 个、`forge` 7 个 Java 文件
- 最大文件：`settings/Settings.java` 1227、`mixin/client/MixinGuiMap.java` 1150、`feature/drawing/db/DrawingDatabase.java` 908、`feature/drawing/DrawingCache.java` 873、`module/impl/Drawing.java` 661、`feature/highlights/ChunkHighlightSavingCache.java` 553

## 3. 入口与注册

- common 无 `@Mod`/无入口类，只有 `XaeroPlus.java`（静态门面）与 `Globals.java`（跨 mixin 共享状态）。
- Fabric：`fabric/src/main/java/xaeroplus/fabric/XaeroPlusFabric.java:25-62`（`ClientModInitializer`，`AtomicBoolean compareAndSet` 幂等初始化、注册按键、注册资源重载监听、ClientsStarted 时检查 Minimap 版本不符则弹 `IncompatibleMinimapWarningScreen`）。
- Forge：`forge/src/main/java/xaeroplus/forge/XaeroPlusForge.java:11-21`（`@Mod("xaeroplus")` + `DistExecutor.unsafeRunWhenOn(Dist.CLIENT, …)` 转 `XaeroPlusForgeClient`）。
- 注册框架：**不用 DeferredRegister/Registrate**（纯客户端、零内容注册），改用自建三件套：
  - `Settings.REGISTRY`（`settings/Settings.java:31-32`，继承 `SettingRegistry`）集中登记全部设置项；
  - `ModuleManager`（`module/ModuleManager.java:12-40`）静态构造 24 个 `Module`，按 `Class` 索引；
  - `XaeroPlus.EVENT_BUS = LambdaManager.threadSafe(new LambdaMetaFactoryGenerator())`（`XaeroPlus.java:32`）。

## 4. 核心系统

1. **Setting 体系** — `settings/SettingRegistry.java:24-46` `register0()` 用 `settingNameMap` 做重名硬校验（重复即抛 `RuntimeException`），并维护 `SettingLocation`（8 个 GUI 分区）与 `KeyMapping` 映射；`Settings.java:39-48` 演示典型的"设置项 + 生效回调 + 可见性谓词"声明式写法（如 `BaritoneHelper::isBaritonePresent`）。持久化在 `settings/SettingHooks.java:17-31`：按名排序写入 `config/xaeroplus.txt` 的 `name:serializedValue` 行，读回时 `getSettingByName` 找不到只告警不报错（向前兼容旧配置）。
2. **Module 生命周期** — `module/Module.java:30-44`：`enable()/disable()` 内部自动 `EVENT_BUS.register/unregister(this)` 并对 `onEnable/onDisable` 做异常捕获，因此"模块启用 = 订阅事件"，避免残留监听；`module/impl/*` 26 个模块（Drawing、PaletteNewChunks、Pearls、PortalSkipDetection、SpawnChunks、WorldBorder、TickTaskExecutor 等）。
3. **SQLite 持久化 + 版本迁移（本仓库最有学习价值的部分）** — `feature/db/DatabaseMigrator.java`：迁移前 `BACKUP TO` 备份 + 磁盘空间校验（`:238-250`，要求剩余空间 > 3×db 体积）+ `VACUUM`；单步迁移用 `setAutoCommit(false) → doMigration → commit`，失败 `rollback`（`:113-135`）；用 `Semaphore(1, true)` 串行化重型 DB 操作（`:138-152`）；捕获 `SQLITE_CORRUPT` 后用 `recover to` 生成新库、原子替换 main+`-journal` 文件并重连重试（`:173-236`）。接口 `DatabaseMigration`（`shouldMigrate/doMigration` + `executeCancellable` 支持中断取消）。落盘位置 `WorldMap.saveFolder/<worldId>/<name>.db`，`jdbc:rfresh_sqlite:` + `setBusyTimeout(5000)`（`feature/highlights/ChunkHighlightDatabase.java:34-60`，`DATABASE_VERSION=2`）。
4. **区块数据采集与事件化** — `mixin/client/mc/MixinClientPlayNetworkHandler.java` 在 `handleLevelChunkWithLight`（:28、:39 RETURN）、`handleChunkBlocksUpdate`（:47 `@WrapOperation`）、`handleBlockUpdate`（:60）、`handleBlockEntityData`（:74）、`close`/`handleMovePlayer`/`handleGameEvent`（:79-91）注入，产出 `event/ChunkDataEvent`、`ChunkBlockUpdateEvent` 等；事件基类 `event/PhasedEvent.java` + `Phase`（PRE/POST 相位），消费方为高亮缓存（`feature/highlights/ChunkHighlightCache`、`ChunkHighlightSavingCache`）与绘制缓存（`feature/drawing/DrawingCache`）。
5. **GUI / 渲染扩展与版本门禁** — `feature/extensions/` 全是插入 Xaero 界面的接口/组件（`IXaeroPlusSettingEntry`、`DrawOrderScreen`、`CustomWorldMapShader`、`OptimizedMapLayer`…）；`fabric/.../compat/XaeroPlusCompatibleMinimapMixinPlugin.java:26-35` 作为 `IMixinConfigPlugin`，当 Minimap 版本不匹配时 `shouldApplyMixin` 对 `xaeroplus.*` mixin 一律返回 false、只放行 `MixinMinecraftClientFabric`，实现对"硬依赖但版本必须精确"的降级保护；期望版本从 mod 元数据自定义字段读取（`XaeroPlusMinimapCompatibilityChecker.java:45-47`，`minimap_version` 由 `fabric/build.gradle.kts:88-95` 的 `processResources expand` 注入）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端；无自定义包注册）。Forge 侧 `MixinCommandSourceStack` / Fabric 侧 `MixinFabricClientCommandSource` 只是让命令源类型可用。
- 数据驱动：**无资源包/数据包驱动**；特性由代码 + 配置开关驱动。
- 配置：纯文本 `config/xaeroplus.txt`（`SettingHooks`），另有 SQLite 数据库存绘制/高亮数据。
- datagen：**无**。构建侧有价值的是 `common/build.gradle.kts` 的 `remapForge` 任务 —— 读 `common/remap/remap.txt`（格式 `fabricClassName::forgeClassName`）把 common 源码里的 Fabric 类名文本替换为 Forge 类名，产出 `build/remappedSources/forge`，从而单份 common 源码同时喂给两个平台。

## 6. Mixin

- 配置：`common/src/main/resources/xaeroplus.mixins.json`（`package: xaeroplus.mixin.client`，61+6 项，`plugin` 指向上述 mixin 插件）、`fabric/src/main/resources/xaeroplus-fabric.mixins.json`（6 项）、`forge/src/main/resources/xaeroplus-forge.mixins.json`（1 项）；另有 access widener `common/src/main/resources/xaeroplus.accesswidener`（`PalettedContainer$Data`、`LevelRenderer#cullingFrustum/viewArea`、`ClientLevel#entityStorage`、`ShaderInstance#blend`、`BeaconBlockEntity#levels` 等）。
- 代表 hook：
  - `mixin/client/MixinGuiMap.java`（1150 行，对 `GuiMap` 的 `render/init/tick/changeZoom/mouseClicked/mouseReleased/keyPressed/onInputPress/onInputRelease/shouldSkipWorldRender` 混用 `@Inject`、`@Redirect`（如 `cameraX/cameraZ` PUTFIELD, :421/:426）、`@WrapOperation`、`@ModifyArg`、`@WrapWithCondition`）
  - `mixin/client/MixinMapSaveLoad.java:25-62` → `MapSaveLoad#getOldFolder`(HEAD, cancellable)、`saveRegion`（`@Redirect` + 两处 `@Inject`），改写地图区域写盘行为
  - `mixin/client/mc/MixinClientPlayNetworkHandler.java`（见上）、`mixin/client/mc/MixinMinecraft.java:26-61` → `runTick/tick/setLevel/getMainRenderTarget/destroy`
  - `mixin/client/MixinMapProcessor.java`、`MixinMapWriter.java`、`MixinMinimapWriter.java` 等针对 Xaero 写盘/处理管线的加速改写

## 7. 值得学的 5 条具体做法

1. **给"必须精确版本"的依赖做 mixin 级门禁**：MixinConfigPlugin 在 `shouldApplyMixin` 里按运行时 mod 版本决定是否加载整包 mixin（`XaeroPlusCompatibleMinimapMixinPlugin.java:26-35`），不匹配时仅保留最小 mixin 用于弹窗提示，避免类加载崩服。
2. **数据库迁移工程化**：`DatabaseMigrator` 把"备份 → 空间检查 → 分事务迁移 → VACUUM → 损坏恢复 → 重试"串成固定流程，并用 `MAX_RETRIES`/`Semaphore` 控并发（`feature/db/DatabaseMigrator.java:39-95,138-236`）；任何要长期保存玩家数据的模组都可照搬。
3. **配置读写的向前兼容**：`SettingHooks.loadXPSettingsFromFile` 遇到未知设置名只 `LOGGER.warn` 跳过（`settings/SettingHooks.java:44-59`），删除设置项不会让老配置文件失效。
4. **自建轻量事件总线解耦 mixin 与功能**：`XaeroPlus.EVENT_BUS`（LambdaEvents）+ `Module` 启停自动订阅（`module/Module.java:33,44`），mixin 只负责发事件，功能模块只在被启用时订阅。
5. **同源跨平台 + 文本重映射**：`common/remap/remap.txt` 与 Gradle `remapForge` 任务（`common/build.gradle.kts:28-79`）用 `fabric::forge` 类名替换复用 common 源码，省掉一整套平台抽象层——仅适用于 API 差异能被文本替换覆盖的场景。

## 8. 库 / 前置 / API 类 mod

不适用（不是前置库）。但内部已具备可复用扩展形态：`feature/extensions/*` 的接口集合（如 `CustomMapProcessor.java` 用 `ThreadLocal<Boolean> xaeroplus$…` 暴露状态给 mixin）、`feature/waypoint/WaypointAPI.java`（用 `BuiltInHudModules.MINIMAP.getCurrentSession()` 读写 Xaero 航点/世界容器），是"把 mixin 状态导出成 public API 供第三方调用"的现成样本。
