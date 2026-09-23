# Arsenalists-of-Create / Create-Radar 源码分析

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 | Create: Radars |
| mod_id | `create_radar` |
| 作者 | Aycer, HappySG, CeoOfGoogle, Kipti, OndatraCZE, Ray(furuochen) |
| 版本 | 5.0（`version = "${mod_version}.${GITHUB_RUN_NUMBER}+mc1.20.1"`） |
| 目标 MC / 加载器 | Minecraft **1.20.1 / Forge 47.3.0**（`forge_version_range=[47,)`） |
| Gradle 插件 | `net.minecraftforge.gradle [6.0.16,6.2)` + `org.parchmentmc.librarian.forgegradle` + **`org.spongepowered.mixin 0.7.+`** + `com.gradleup.shadow 8.3.5` + `org.jetbrains.kotlin.jvm` |
| Java | toolchain 17 |
| 许可证 | MIT |
| group | `com.happysg.radar` |
| 映射 | Parchment 2023.09.03-1.20.1 |

依赖（`gradle.properties:19-33`、`build.gradle:135-215`）：Create 6.0.8-288（`[6.0.0,6.1.0)`）、Ponder 1.0.52、Flywheel 1.0.2、Registrate MC1.20-1.3.3、mixinextras 0.4.1（**唯一使用 MixinExtras 的仓库**，`compileOnly(annotationProcessor(...))` + `implementation("...:mixinextras-forge")`）；武器链强绑定 **Create Big Cannons 5.11.2 + RPL 2.1.1（implementation/硬依赖）**，另有 CBCMW 0.0.6c、CBC-AdvancedTechnologies 0.1.3b、CBC-Warium-Projectiles 1.3.3、Create Energy Cannons（`lib/*.jar` flatDir）全部 `compileOnly`；Valkyrien Skies 2（`org.valkyrienskies:*` compileOnly + Kotlin for Forge 4.12.0）、CC:Tweaked 1.117.0、Clockwork、Trackwork、Architectury、JEI（runtimeOnly）。

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` → **1182 个文件 / 70634 行**；但其中 **`com/happysg/radar/math3/` 是整包内嵌的 Apache Commons Math（约 990 个文件、4.8 万行，最大文件 `math3/util/FastMathLiteralArrays.java` 6175 行）**。剔除后本体为 **192 个 .java / 22693 行**。另有 1 个 Kotlin 文件 `compat/vs2/VSEventHook.kt`。

本体包结构（`com/happysg/radar/`）：

| 包 | 文件数 | 说明 |
|---|---|---|
| （根） | 1 | `CreateRadar` |
| `block/` | 约 90 | 按功能分子包：`radar/{bearing,plane,radome,receiver,skyradar,sonar,track,behavior}`、`controller/{yaw,pitch,tpitch,track,firing,id,networkcontroller,utils}`、`monitor`(10)、`datalink`(8)、`arad/*`（反辐射/干扰/RWR）、`guidance`、`mount`、`siren`、`behavior/networks`(5)+`config`(4) |
| `compat/` | 34 | `cbc`(10)、`cbcwpf`(4)、`computercraft`(7 外设)、`vs2`(5)、`cbcmw`、`kaboom` |
| `registry/` | 18 | `ModBlocks/ModItems/ModBlockEntityTypes/ModCommands(701)/ModContraptionTypes/ModDisplayBehaviors/AllDataBehaviors/ModPonderIndex/ModKeybinds/...` |
| `networking/` | 2 + `packets`(8) + `networkhandlers`(2) | 见第 5 节 |
| `config/` | 4 | `RadarConfig` + client/common/server 各一（共 155 行） |
| `mixin/` | 4 | 全为 `@Accessor` |
| `item/` | 13 | `binos`、`radargoggles`、`artilleryradio`、`*filter` |
| `ponder/` | 2、`utils/` | `PonderScenes`、`RadarPonderPlugin`、`utils/screenelements`(4) |

最大文件（剔 math3）：`block/behavior/networks/NetworkData.java`(1296)、`WeaponFiringControl.java`(1094)、`block/controller/networkcontroller/NetworkFiltererBlockEntity.java`(902)、`block/monitor/MonitorRenderer.java`(749)、`utils/screenelements/SimpleEditBox.java`(702)、`registry/ModCommands.java`(701)、`pitch/AutoPitchControllerBlockEntity.java`(635)、`MonitorScreen.java`(609)、`MonitorBlockEntity.java`(597)、`compat/cbc/CannonUtil.java`(504)。

## 3. 入口与注册

主类 `src/main/java/com/happysg/radar/CreateRadar.java:58-117`：依旧是 Create 版 Registrate（`:64-67` 同样的 `ItemDescription + KineticStats` tooltip 组合）。构造函数（`:73-117`）顺序：`MinecraftForge.EVENT_BUS.register(this)` → `REGISTRATE.registerEventListeners(modEventBus)` → `ModItems/ModBlocks/ModBlockEntityTypes/ModCreativeTabs/ModLang/ModPartials` → `RadarConfig.register(context)` → `NetworkHandler.register()`。

值得注意的三点：
- **延迟注册**：`ModContraptionTypes` 与 `BlockStressValues.IMPACTS` 放在 `FMLCommonSetupEvent` 的 `event.enqueueWork` 里（`:161-176`，注释 "Must be registered after registries open"）——因为 `CreateBuiltInRegistries.CONTRAPTION_TYPE` 是运行期注册表（`registry/ModContraptionTypes.java:15-20` 直接 `Registry.register`）。
- **配置界面扩展点**：`:97-98` 用 `container.registerExtensionPoint(ConfigScreenHandler.ConfigScreenFactory.class, () -> ... RadarConfig::createConfigScreen)`。
- **compat 模块条件注册**：`:105-115` 依次 `Mods.CREATEBIGCANNONS / CBCMODERNWARFARE / COMPUTERCRAFT / SHUPAPIUM / VALKYRIENSKIES` 判断后调用 `CBCCompatRegister.registerCBC()` 等。

## 4. 核心系统

**(1) 雷达/武器网络数据 `NetworkData extends SavedData`（1296 行，本仓库最核心）**
- 职责：把"过滤器(NetworkFilterer) — 雷达 — 显示器(Monitor) — 武器挂点(Controller/CannonMount) — 数据链接"的整张关系图持久化，并驱动目标同步。
- `block/behavior/networks/NetworkData.java:36-89`：一个组用一个 `Group` 对象表示（`:43-66`），内含 `monitorEndpoints / weaponEndpoints / usedWeaponMounts / dataLinks` 四个 `Set<BlockPos>`、`RadarKind`/`Mountkind` 枚举，以及三份配置 `targetingTag / identificationTag / detectionTag`（`CompoundTag`，直接存 NBT 以免为每种配置建类）；组用 `record FilterKey(ResourceKey<Level> dim, BlockPos filtererPos)`（`:39`）字符串化后作 key。
- 反向索引齐全（`:74-89`）：`groupsByFilterer / endpointToFilterer / weaponMountToFilterer / dataLinkToFilterer / dataLinkToEndpoint / controllerToWeaponMount`，全部 `Map<String,String>`——**用字符串 key 换取 NBT 读写零成本**，代价是类型不安全。
- 生命周期 API 成对出现：`canAttachMonitor/canAttachRadar/canAttachWeaponEndpoint`（`:404-439`）+ `attachMonitor/attachRadar/attachWeaponEndpoint/addDataLinkToGroup`（`:441-494`）+ `removeDataLinkAndCleanup(:540) / onEndpointRemoved(:637) / dissolveNetworkForBrokenController(:110)`；`getFiltererPosFromGroupKey(:188)` 做 key→BlockPos 反解。

**(2) 开火控制 `WeaponFiringControl`（1094 行）**
- `block/behavior/networks/WeaponFiringControl.java:41-76`：持有 `CannonMountBlockEntity cannonMount`、`AutoPitchControllerBlockEntity pitchController`、`AutoYawControllerBlockEntity yawController`、`FireControllerBlockEntity fireController` 与 `WeaponNetworkRuntime.WeaponGroupView view`——即"一门炮的整套控制器"聚合体。
- 大量显式预算常量体现性能意识：`AIM_STABLE_REQUIRED=2 / AIM_STABLE_EPS=0.5`（瞄准稳定判定）、`LOS_SELECTION_TTL_TICKS=10 / LOS_PREFIRE_TTL_TICKS=1` + 内部 `LosCache`/`VisCache` 类（`:90-101`，视线射线结果缓存）、`VIS_REFRESH_TICKS=3`、`MAX_POINTS_PER_REFRESH=10`（**每 tick 射线预算**）、`REACQUIRE_EVERY_TICKS=10`、`VS2_SOLVE_INTERVAL=3`（VS 船体解算降频）。

**(3) 显示器多块 + 雷达屏渲染**
- `block/monitor/MonitorBlockEntity.java:43` `extends SmartBlockEntity implements IHaveHoveringInformation, INetworkNode`；`syncFromNetwork(ServerLevel)`(:158) 与 `setSelectedTargetServer(@Nullable RadarTrack)`(:175) 是"网络数据 → 显示器"的收敛点；带专用 `static final class Client` 客户端缓存。
- 多块逻辑独立成 `MonitorMultiBlockHelper.java`（`formMulti(:50) / destroyMulti(:73) / getSize(:96) / onNeighborChange(:136)`），最大尺寸受服务端配置 `monitorMaxSize`(默认 9) 控制。
- `MonitorRenderer.java:43-65` 用一组**显式深度常量**分层绘制（`DEPTH_BACKGROUND 0.94f / GRID 0.945f / SWEEP 0.947f / TRACK_BASE 0.95f / TRACK_INCREMENT 0.0001f`、`LABEL_SCALE 0.003f`），靠 0.0001 级别递增避免同一平面 z-fighting——非常实用的"平面 HUD 渲染"技巧。

**(4) 雷达抽象 `IRadar` + 目标 `RadarTrack`**
- `block/radar/behavior/IRadar.java`：极小接口 `getTracks()/getRange()/isRunning()/getWorldPos()/getGlobalAngle()/getRadarType()/getradarDirection()` + `default renderRelativeToMonitor()`，让"雷达轴承、平面雷达、天空雷达、声纳"共用同一采集契约。
- `block/radar/track/RadarTrack.java:19-151`：`id/position/velocity/scannedTime/trackCategory/entityType/entityheight`，自带 `serializeNBT/deserializeNBT`(:82,:69) 与 `updateRadarTrack(Entity)` / `updateRadarTrack(Ship, Level)`(:99,:105)——同一目标类同时支持原版实体与 VS2 船（虚拟实体）。
- `TrackCategory`（枚举 PLAYER/MOB/HOSTILE/ANIMAL/VS2/PROJECTILE/CONTRAPTION/ITEM/MISC）分类依赖实体类型标签 `RadarEntityTypeTags`（`track/RadarEntityTypeTags.java`），把分类规则交给数据包标签而非硬编码。

**(5) 数据链接（DataLink）总线**
- `block/datalink/DataLinkBlockEntity.java:23-37`：`enum WeaponEndpointType` + `DataPeripheral activeSource` / `DataController activeTarget` 两端点抽象，`updateGatheredData()`(:60) 驱动数据流；`DataLinkBlockItem.java`(557) 负责用物品"两点连线"，`clientTick()`(:515) 里用缓存的 `lastShownPos/lastShownAABB` 绘制范围预览。
- `registry/AllDataBehaviors.java:29` 定义 `Map<ResourceLocation, DataLinkBehavior> GATHERER_BEHAVIOURS` 并 `registerDefaults()`，配合 `MonitorRadarBehavior`、`TrackLinkBehavior`——这是可扩展开放式注册表（第三方可注册自己的数据采集行为）。

**(6) CBC 弹道解算 compat（学习"高精度瞄准"）**
- `compat/cbc/CannonTargeting.java:24-60`：给出带阻力的抛物线解析式 `calculateProjectileYatX(speed, dX, thetaRad, drag, g)`（用 `log(1 - drag*dX/(speed*cosθ))`），并对该函数用**内嵌 commons-math3 的 `BrentSolver` 求根**得到发射俯仰角；激光炮走 `directPitchToTarget` 直线分支。
- `compat/cbc/CannonUtil.java`(504) 从 CBC 炮的数据里读初速/阻力/重力；`CannonLead.java`+`AccelerationTracker.java`+`VelocityTracker.java` 做提前量；`VS2TargetingSolver.java` 在 VS2 场景下改用 `BOBYQAOptimizer` + `MultiStartMultivariateOptimizer` 做多起点无约束优化。
- VS2 兼容用 `compat/vs2/PhysicsHandler.java`、`VSAssemblySuppression.java` 与 Kotlin 的 `VSEventHook.kt` 做事件钩子。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络（同时存在两套，属技术债）**：
  - `networking/NetworkHandler.java:13-19`：原生 `NetworkRegistry.newSimpleChannel(rl("main"), "1", ...)`，手写 `packetId++` + `registerMessage(id, cls, encode, decode, handle)`，承载 `SaveListsPacket / BoolListPacket / RaycastPacket / FirePacket / MonitorSelectionPacket`。
  - `networking/ModMessages.java:25-56`：第二条 `SimpleChannel(rl("messages"), "1.0")`，复用 Create 的 `SimplePacketBase`（`write`/`handle`），但解码器是**反射构造**：`clazz.getConstructor(FriendlyByteBuf.class).newInstance(buf)`，用 `consumerMainThread(ModMessages::handler)` 统一回主线程；承载 `IDRecordPacket / IDRecordRequestPacket / IDRecordSyncPacket`。扩展新包只需实现 `SimplePacketBase` + 在 `register()` 加一行 `c2s/s2c`。
- **数据驱动**：无自定义数据包注册表；雷达分类用实体类型标签（`RadarEntityTypeTags`）；CBCMW 导弹制导等第三方 compat 通过 `CompoundTag` 与对方通信。`registry/ModLang.java` 走 Create 的 lang 生成。
- **配置**：用 **Create/Catnip 的 `ConfigBase`**（不是裸 ForgeConfigSpec API）——`config/RadarConfig.java` 用 `EnumMap<ModConfig.Type, ConfigBase>` 管三份配置，`new ForgeConfigSpec.Builder().configure(builder -> { config.registerAll(builder); return config; })` 生成 spec，并提供 `createConfigScreen` 挂到 Forge 的 `ConfigScreenHandler` 扩展点。**重头戏是服务端配置**（`config/server/RadarServerConfig.java:10-23`）：`radarLinkRange=128`、`monitorMaxSize=9`、`radarFOV=90`、`maxRadarRange=1000`、`radarYScanRange`、`dishRangeIncrease`、`gearRadarBearingSpeed`、`leadFiringDelay`，以及 `guidedFuzeConfig` 组（`guidedFuzeMaxSeekDegrees/MaxDegreesPerTick/SeekBeforeApex`）——把数值平衡全部外置。
- **datagen**：`ModLang`/`ModBlocks` 内联 blockstate 生成（如 `ModBlocks.java:47-70` MONITOR 的 `ConfiguredModel.builder()` 变体生成）；无独立 datagen 包。

## 6. Mixin

- 配置：`src/main/resources/create_radar.mixins.json`——`required:true`、`minVersion 0.8`、`package com.happysg.radar.mixin`、**refmap `createradar.refmap.json`**（注意文件名是 `createradar`，与 mod_id `create_radar` 不同，但 build.gradle 中 `mixin { add sourceSets.main, 'createradar.refmap.json' }` 与 jar manifest `MixinConfigs: create_radar.mixins.json` 二者一致，不构成 bug）、`compatibilityLevel JAVA_17`、`client: []`（无客户端 mixin）、`injectors.defaultRequire: 1`。
- **4 个 mixin 全部是 `@Accessor`，没有一处在注入逻辑**（说明作者刻意避免改 Create/CBC 行为）：
  - `mixin/AbstractCannonAccessor.java`：`@Mixin(AbstractMountedCannonContraption.class)`，`@Accessor(value="frontExtensionLength", remap=false) int getFrontExtensionLength()` 等——读取 CBC 炮管前后延伸长度（用于计算炮口位置）。
  - `mixin/AutoCannonAccessor.java`：`@Mixin(value = {MountedAutocannonContraption, MountedTwinAutocannonContraption, MountedHeavyAutocannonContraption}, remap = false)`，一个接口同时给 3 个类加 `@Accessor("cannonMaterial")`——**一次声明、多目标复用**。
  - `mixin/AutocannonProjectileAccessor.java`：取炮弹私有字段。
  - `mixin/ShupapiumACContraptionAccessor.java`：**接口合并模式**——`@Pseudo` + `@Mixin(targets = "net.ato.shupapium.utils.MountedShupapiumACContraption")`，且 `extends IShupapiumACContraptionAccess`（自己 compat 包里的接口），用 `targets` 字符串避免编译期依赖可选模组。这是"可选依赖 mixin"的标准写法。

## 7. 值得学的 5 条做法

1. **用 `@Pseudo` + `targets = "全限定类名"` + 自有接口实现"可选模组 mixin"**：编译期零依赖、运行期缺模组时自动跳过。`mixin/ShupapiumACContraptionAccessor.java`，配 `compat/cbcwpf/IShupapiumACContraptionAccess.java`。
2. **平面/屏幕渲染用显式深度常量分层（0.0001 递增）**避免 z-fighting，而不是靠 `renderType` 硬碰。`block/monitor/MonitorRenderer.java:46-58`。
3. **射线/视线检测要设"每 tick 预算 + TTL 缓存"**：`MAX_POINTS_PER_REFRESH=10`、`VIS_REFRESH_TICKS=3`、`LOS_SELECTION_TTL_TICKS=10`，配合内部 `LosCache/VisCache`。`block/behavior/networks/WeaponFiringControl.java:75-101`。
4. **复杂关系图用"SavedData + 字符串 key 的多个反向索引 Map"**，把 NBT 序列化成本压到最低，同时保留 `canAttachX/attachX/onXRemoved` 成对 API 保证一致性。`block/behavior/networks/NetworkData.java:74-89, 404-494`。
5. **配置用 Create 的 `ConfigBase` + `EnumMap<Type, ConfigBase>` 统一注册，并挂 `ConfigScreenHandler` 扩展点**，得到与 Create 一致的配置界面。`config/RadarConfig.java:20-50`、`CreateRadar.java:97-98`。

## 8. 公开 API / 扩展点

非库模组，但有几处对第三方开放的注册表：`registry/AllDataBehaviors.java:29` 的 `GATHERER_BEHAVIOURS`（`Map<ResourceLocation, DataLinkBehavior>`，数据采集行为）；`block/radar/behavior/IRadar.java`（自定义雷达只需实现 7 个方法即可接入显示器/网络）；`registry/ModDisplayBehaviors.java:10-15` 用 `REGISTRATE.displaySource(...).associate(be)` 把方块实体挂到 Create 的显示链接体系；`CreateBuiltInRegistries.CONTRAPTION_TYPE` 上注册的 `radar_bearing` 动态结构类型（`registry/ModContraptionTypes.java:15-20`）；`compat/computercraft` 提供 6 个外设（`MonitorPeripheral` 等）供 CC:Tweaked 脚本访问。
