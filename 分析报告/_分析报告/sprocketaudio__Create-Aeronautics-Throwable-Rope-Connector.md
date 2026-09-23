# sprocketaudio/Create-Aeronautics-Throwable-Rope-Connector 源码分析报告

## 1. 基本信息
- Mod 名：Create Aeronautics: Throwable Rope Connector；mod_id：`create_aeronautics_throwable_rope_connector`；版本 0.4.1；许可证 **All Rights Reserved**（`gradle.properties` `mod_license`，`TEMPLATE_LICENSE.txt` 为 NeoForge MDK 模板文本）。
- 目标：MC 1.21.1 + **NeoForge 21.1.228**（纯单平台，无 architectury）；Java 21 toolchain；Parchment 1.21.1/2024.11.17；Gradle 插件 `net.neoforged.gradle.userdev 7.1.25`（`build.gradle`）。
- 依赖（谁提供 API）：Create `1.21.1-6.0.10`（**compileOnly 直接引用本地实例路径 `E:/Games/CurseForge/Instances/.../create-1.21.1-6.0.10.jar`**）、Create Aeronautics 打包版 `libs/create-aeronautics-bundled-1.21.1-1.3.0.jar`、`libs/sable-neoforge-1.21.1-2.0.1.jar`、`libs/flywheel-neoforge-1.21.1-1.0.6.jar`、`net.createmod.ponder:ponder-neoforge:1.0.82+mc1.21.1`；`mods.toml` 声明 required `create [6.0.10,)`、`aeronautics_bundled [1.3.0,)`，optional `simulated [1.3.0,)`。
- 构建技巧：`extractSimulatedJar`（Copy + zipTree）从 aeronautics bundle 里抽出 `META-INF/jarjar/dev.simulated_team.simulated...jar` 供 compileOnly，因为 Simulated 无公开 maven。

## 2. 源码规模与包结构
- 30 个 `.java`，3459 行。包：`registry` 5、`client` 7、`item` 4、`network` 4、`block` 2、`entity` 2、`integration` 2、`config` 1、根 1。
- 最大文件：`block/MountedRopeLauncherBlockEntity.java` 823、`item/ThrowableRopeConnectorPlacement.java` 319、`entity/ThrowableRopeConnectorProjectile.java` 286、`client/ThrowableRopeConnectorProjectileRenderer.java` 264、`block/MountedRopeLauncherBlock.java` 239、`entity/MountedRopeLauncherSeatEntity.java` 224。
- 无 mixin 包、无 `assets/`/`lang/`（仓库 21 处 `Component.translatable` 无对应 lang 文件，资源被裁剪）。

## 3. 入口与注册
`CreateAeronauticsThrowableRopeConnector.java`（`@Mod`）构造器即全部装配：`ModBlocks/ModBlockEntityTypes/ModEntityTypes/ModItems/ModCreativeTabs` 五个 `register(modEventBus)`，`modEventBus.addListener(ModNetworking::register)`，`registerCapabilities`、`onConfigLoaded/onConfigReloaded`，`modContainer.registerConfig(ModConfig.Type.COMMON, ModCommonConfig.SPEC)`，`if (FMLEnvironment.dist == Dist.CLIENT) CreateAeronauticsThrowableRopeConnectorClient.init(...)`。
注册框架：**NeoForge DeferredRegister**（`registry/ModBlocks.java:13` 用 `DeferredRegister.createBlocks`、`registry/ModItems.java:14` 用 `DeferredRegister.createItems`），未用 Registrate。

## 4. 核心系统
1. **抛掷投射物**：`entity/ThrowableRopeConnectorProjectile.java` 继承 `ThrowableItemProjectile`。5 个 `EntityDataAccessor`（3 个 trail 来源标记 + `DATA_HAS_MOUNTED_SOURCE`/`DATA_MOUNTED_SOURCE_POS`）做客户端表现同步；`tick()` 里 `position().distanceTo(origin) > maxThrowDistance` 即 `failAndReturn`（射程自毁）；`onHitBlock` 走 `placeConnectorAndGiveRope`，成功 `broadcastEntityEvent(this,(byte)3)` 触发粒子后 `discard()`；失败按 `consumeOnSuccessOnly` 决定是否 `returnThrowableItem`。
2. **放置语义**：`item/ThrowableRopeConnectorPlacement.java`（`placeConnectorAndGiveRope` / `placeConnectorFromMountedLauncher` / `resolvePlacementTarget` 返回 `PlacementTarget` record / 源槽位消耗与 8 处回退逻辑）：成功时用集成层创建一个"预设好的一端"的 Rope Coupling 给玩家。
3. **对 Simulated 的软依赖集成**：`integration/CreateSimulatedIds.java` + `CreateSimulatedIntegration.java` 全程用 `ResourceLocation` + `BuiltInRegistries.ITEM` / `BuiltInRegistries.DATA_COMPONENT_TYPE` 反查 `simulated:rope_connector`、`simulated:rope_coupling`、`simulated:rope_first_connection` 组件（`DataComponentType<BlockPos>` 强转后 `stack.set`），**编译期不引用 Simulated 的类**，缺失即返回 `Optional.empty()`。
4. **挂载式发射器**：`block/MountedRopeLauncherBlockEntity.java` 继承 Simulated 的 `RopeWinchBlockEntity`（复用绳索机逻辑），内含 1 格 `ItemStackHandler` + 包装成只读/可插入的自动化 `IItemHandler`；`fireInDirection` 做冷却、已连接、无弹药、前方被挡（`getCollisionShape` 非空）四道校验；`registerCapabilities` 挂能力；`entity/MountedRopeLauncherSeatEntity.java`（`IEntityWithComplexSpawn`）作为载具座椅承载玩家并每次发射回传瞄准角。
5. **配置与上游钳制**：`config/ModCommonConfig.java` 用 `ModConfigSpec` 分 `throwing/launcher/mounted/general/visual` 五组；`getSimulatedMaxRopeRange()` 读 `SimConfigService.INSTANCE.server().blocks.maxRopeRange.getF()`，`correctRangeValuesToSimulatedMax()` 在 `ModConfigEvent.Loading/Reloading` 时把三个射程 set 到不超过上限。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`network/ModNetworking.java` 用 NeoForge `RegisterPayloadHandlersEvent`，`event.registrar("1")` 链式注册：1 个 `playToClient`（LauncherShoot，仅演出）+ 3 个 `playToServer`（Mounted 开火/下坐/释放）。服务端处理统一做**归属校验**：`context.player() instanceof ServerPlayer` 且 `player.getVehicle() instanceof MountedRopeLauncherSeatEntity seat` 且 `seat.getId() == packet.seatEntityId()` 才执行，防伪造包。
- 配置：仅 `ModConfig.Type.COMMON`（NeoForge ModConfigSpec）+ 上述钳制逻辑；客户端注册 `IConfigScreenFactory → ConfigurationScreen::new` 提供内置配置界面。
- datagen：`build.gradle` 有 data run 且 `srcDir('src/generated/resources')`，但仓库内无生成文件（未确认是否实际使用）。
- 资源：仓库只含 `src/main/resources/META-INF/neoforge.mods.toml`。

## 6. Mixin
无。仓库没有 mixins 包、没有 mixin 配置 json、`neoforge.mods.toml` 无 `[[mixins]]` 段；功能全部通过 NeoForge 事件、能力与继承 Create/Simulated 基类实现。

## 7. 值得学的 5 条具体做法
1. **用注册表 ID 做软依赖集成**：`integration/CreateSimulatedIntegration.java` 通过 `BuiltInRegistries` 查 `simulated:rope_coupling` 与其数据组件，避免编译/运行强绑定 —— 适用：依赖尚未发布 maven 或版本漂移的附属 mod。
2. **消耗型物品"仅成功才扣"**：`consumeOnSuccessOnly` 贯穿投射物与方块实体（`MountedRopeLauncherBlockEntity.fireInDirection` 里 `pendingAmmoConsumed` + `refundPendingAmmo`）—— 适用：投射/放置类工具的弹药体验。
3. **把玩法参数钳到上游上限**：`config/ModCommonConfig.correctRangeValuesToSimulatedMax()` 在 config load/reload 事件里写回配置 —— 适用：与其它 mod 的 server config 有冲突上限时。
4. **服务端包处理先校验载具归属**：`network/ModNetworking.handleMountedLauncherFire` 三重判定（玩家、载具类型、实体 id）—— 适用：所有"客户端发指令操作服务端实体"的交互。
5. **零依赖的打包期取 jar 技巧**：`build.gradle` 的 `extractSimulatedJar` 从上游 bundle 抽 jar-in-jar 当 compileOnly —— 适用：依赖只以 JiJ 形式分发、无公开 maven 的前置（如 Simulated）。

## 8. 库/API 类 mod 的公开 API
不适用（非库 mod）。但它本身是"**消费别人的 API**"的范例：`mounted` 模块复用 `RopeWinchBlockEntity`、`ShieldBlockItem`/`CustomArmPoseItem` 等 Create 扩展点（`item/RopeConnectorLauncherItem.java` 实现 `CustomArmPoseItem` + `initializeClient` 注册 `SimpleCustomRenderer`）。
