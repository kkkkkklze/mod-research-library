# PedroRok/CreateHypertubes 源码分析报告

## 1. 基本信息

- **Mod 名 / mod_id**：Create Hypertube / `create_hypertube`（`gradle.properties:10-11`）
- **作者**：Rok（Pedro Lucas）；包名 `com.pedrorok.hypertube`
- **目标 MC / 加载器**：Minecraft 1.21.1 + NeoForge `21.1.228`（`gradle.properties:5,7`），Java 21
- **Gradle 插件**：`net.neoforged.moddev`（ModDevGradle，`build.gradle`）+ `maven-publish`；`settings.gradle` 用 `org.gradle.toolchains.foojay-resolver-convention` 0.8.0
- **许可证**：Apache License 2.0
- **编译依赖**（`build.gradle:83-103`）：
  - `com.simibubi.create:create-1.21.1:6.0.10-281:slim`（`transitive = false`）
  - `net.createmod.ponder:ponder-neoforge:1.0.82+mc1.21.1`
  - `flywheel-neoforge-api-1.21.1:1.0.6`（compileOnly / runtimeOnly 分离）
  - `com.tterrag.registrate:Registrate:MC1.21-1.3.0+62`
  - **`api("dev.ryanhcode.sable:sable-neoforge-1.21.1:2.0.3")`**（排除 `foundry.veil`）—— 关键：它把 Sable 作为 **api** 依赖暴露
  - `Lombok 1.18.32`（`compileOnly` + `annotationProcessor`，源码里大量 `@Getter`）
  - `compileOnly("curse.maven:betterthirdperson-435044:5833474")`；`runtimeOnly("maven.modrinth:create-aeronautics:YhZLrAFC")`
- 元数据同样走 `generateModMetadata` + `${}` 模板替换（`build.gradle:105-123`）

## 2. 源码规模与包结构

实测：**121 个 java 文件，12283 行**。包结构（`com.pedrorok.hypertube` 下）：

| 包（第 3 层） | 文件数 | 内容 |
|---|---|---|
| `mixin.core` | 11 | 相机/玩家/实体/移动/模型注入 |
| `utils` | 10 | 数学、射线、消息、Codec 工具 |
| `registry` | 9 | ModBlocks/ModBlockEntities/ModItems/ModCreativeTab/ModDataComponent/ModKeybinds/ModPartialModels/ModParticles/ModSounds |
| `network.packets` | 9 | 9 个 `CustomPacketPayload` |
| `blocks`（含 blockentities） | 7 + 5 + 3 | 方块与方块实体 |
| `core.travel`（+client） | 6 + 3 | 旅行系统：路径、移动器、常量 |
| `core.connection`（+interfaces） | 3 + 4 | Bezier 管道连接数据模型 |
| `core` 其他 | ~20 | `camera`、`collision`、`compat`、`data`、`escape`、`placement`、`smarttube`、`sound` |
| `ponder`（+scenes/elements） | 3 + 5 + 1 | 5 个 Ponder 场景 |
| `client`（+renderer/particles） | 3 + 4 + 1 | 渲染器与粒子 |

最大文件：`core/connection/BezierConnection.java` 376 行、`blocks/HypertubeBlock.java` 344、`core/travel/client/ClientTravelPathMover.java` 329、`client/BezierTextureRenderer.java` 326、`blocks/blockentities/HyperJunctionBlockEntity.java` 268、`core/placement/TubePlacement.java` 264。

## 3. 入口与注册

主类 `src/main/java/com/pedrorok/hypertube/HypertubeMod.java:23-54`。使用 **CreateRegistrate**（Create 自带的 Registrate 子类）：

```java
public static final CreateRegistrate REGISTRATE = CreateRegistrate.create(HypertubeMod.MOD_ID)
        .defaultCreativeTab((ResourceKey<CreativeModeTab>) null);

public HypertubeMod(IEventBus modEventBus, ModContainer modContainer) {
    modultainer.registerConfig(ModConfig.Type.CLIENT, ClientConfig.SPEC, MOD_ID + "-client.toml");
    modContainer.registerConfig(ModConfig.Type.SERVER, ServerConfig.SPEC, MOD_ID + "-server.toml");
    REGISTRATE.registerEventListeners(modEventBus);
    ModPartialModels.init();
    ModBlocks.register();  ModBlockEntities.register();  ModItems.register();
    ModCreativeTab.register(modEventBus);   ModDataComponent.register(modEventBus);
    ModParticles.register(modEventBus);     ModSounds.register(modEventBus);
    ITubeAttachment.init();
}
```

组织方式值得注意：**混合式**——`ModBlocks/Items/BlockEntities` 走 Registrate（声明式链式 builder），而 `ModCreativeTab/ModDataComponent/ModParticles/ModSounds` 走原生 `DeferredRegister` + `register(modEventBus)`。`ModBlockEntities.java:23-50` 是 Registrate 典型用法：`REGISTRATE.blockEntity("hypertube_entrance_entity", HyperEntranceBlockEntity::new).renderer(() -> EntranceBlockEntityRenderer::new).validBlocks(ModBlocks.HYPERTUBE_ENTRANCE).register()`。每个注册类都带一个空的 `public static void register(){}` 用于触发类初始化（静态字段副作用），这是规避 Registrate 惰性初始化的常用手法。

## 4. 核心系统

### 4.1 旅行系统（TravelManager + TravelPathMover）
`core/travel/TravelManager.java:47-253`。核心状态是静态 `Object2ObjectArrayMap<UUID, TravelPathMover> travelDataMap`（`:49`）。`tryStartTravel(entity, blockEntity, facingDirection, speed)`（`:52-113`）做完整门禁：实体持久化 NBT 上的 `TRAVEL_TAG` 防重入、观战模式排除、`LAST_TRAVEL_BLOCKPOS` + `LAST_TRAVEL_TIME` 做"同一入口冷却"，且**从上一段继承速度**（`speed += entityPersistentData.getFloat(LAST_TRAVEL_SPEED)`，`:76-78`）。路径点少于 3 个时拒绝并给玩家发 actionbar 提示（`:82-86`）。服务端创建 mover 后立刻 `PacketDistributor.sendToPlayersTrackingEntityAndSelf` 广播 `MovePathPacket`（`:99-105`），即**服务端算路径、客户端只回放**。`finishTravel(EndTravelData)`（`:146-207`）负责收尾：写回 `LAST_TRAVEL_*` 持久化字段、`IMMUNITY_TAG` 免疫标记、终点若是 HyperEntranceBlock 则把出射点偏移到管道口外侧、`entity.teleportTo(..., RelativeMovement.ALL, ...)` 后 `setDeltaMovement(lastDir.scale(...))` + `hurtMarked = true`（强制客户端同步）、`setPose(Pose.SWIMMING)`、`player.startFallFlying()`——用鞘翅飞行状态接管玩家运动，避免自己写一整套运动学。

### 4.2 BezierConnection：可序列化曲线数据模型
`core/connection/BezierConnection.java:33-377`。同时定义 `Codec`（NBT/JSON，`:35-40`，字段 `fromPos/toPos/tubeSegments/curvePoints`）与 `StreamCodec`（网络，`:42-48`），用 `RecordCodecBuilder` / `StreamCodec.composite`。关键设计：**只缓存相对起点方块坐标的曲线点** `cachedRelativeBezierPoints`（`:66,91-115`），绝对坐标由 `getBezierPoints(level, currentFromPos)` 现算（`:129-138`）——这样方块移动/复制时无需重算。`detailLevel = max(3, 起点到终点距离)`（`:75`）自适应采样密度；`distance() >= MAX_REASONABLE_DISTANCE(1000)` 直接返回空列表防炸（`:93`）。控制点用 `distance * 0.4` 沿朝向推（`createFirstControlPoint/createSecondControlPoint`，`:160-186`），曲线取标准三次 Bezier 展开式（`:188-201`）。校验集中在 `getValidation()`（`:255-275`）+ `MAX_DISTANCE = 40f` / `MAX_ANGLE = 0.54f`（`:52-53`），返回 `ResponseDTO`（国际化 key + 是否有效），让调用方直接 `MessageUtils.sendActionMessage`。

### 4.3 数据驱动的放置预览（TubePlacement）
`core/placement/TubePlacement.java:57-134`。**同一段校验逻辑被客户端预览与服务端确认共用**：`clientTick()` 每帧构造候选 `BezierConnection`、跑 `getValidation() → checkSurvivalItems → checkBlockCollision → checkClickedHypertube` 的管道式校验（`:111-121`），并用 `LerpedFloat animation`（0 无效 / 0.8 有效）驱动 `drawPath` 线框颜色（在 `BezierConnection.line()` 里 `Color.mixColors(0xEA5C2B, 0x95CD41, animation.getValue())`）。`handleHypertubeClicked`（`:136-194`）在服务端复用完全相同的校验链，避免"客户端能放服务端不能放"的错位。`tickPlayerServer`（`:229-243`）每 20 tick 检查手持物品里的 `TUBE_CONNECTING_FROM` 数据组件指向的方块是否还存在，失效则清空——**用 data component 承载跨 tick 的玩家交互状态**。

### 4.4 Mods 兼容枚举 + MixinPlugin 条件加载
`core/compat/Mods.java:16-84`：枚举 `SABLE`，构造器里 `LoadingModList.get().getModFileById(id) != null` 在类加载期即判定是否装载（`:23-25`）；提供 `runIfInstalled(Supplier<Supplier<T>>)` / `executeIfInstalled(Supplier<Runnable>)` / `executeIfInstalled(Supplier<Function<T,T>>, T)` 三种"存在才执行"的包装（`:60-83`），调用点如 `TravelManager.java:107` `Mods.SABLE.executeIfInstalled(() -> () -> SableCompat.stickToSubLevel(entity, center))`——**用嵌套 Supplier 把对可选 mod 类的引用推迟到 lambda 内部，避免静态链接导致 NoClassDefFoundError**。配套 `mixin/compat/CompatMixinPlugin.java:20-34` 实现 `IMixinConfigPlugin#shouldApplyMixin`：按类名包含 `.mixin.compat.` 后逐级拼接包路径去 `MOD_FOLDERS` 查表，只有对应 mod 装载才应用 mixin（`compat.mixins.json` 里 `"required": false` + `"plugin": ...`）。

### 4.5 管线连接的状态机式接口（ITubeConnectionEntity）
`core/connection/interfaces/ITubeConnectionEntity.java:24-206`。把"可连接方块实体"的全部契约集中在一个接口：`getConnectionInDirection` / `setConnection` / `clearConnection` / `hasConnectionAvailable` / `getFacesConnectable` / `getConnectionOffsetOnDirection` / `wrenchClicked` / `getExitDirection`，且把 NBT 读写做成 `default` 方法（`getConnection` / `writeConnection` / `getConnectionRelative` / `writeConnectionRelative`）。关键点：**NBT 里存相对坐标**（`writeConnectionRelativeSingle` 用 `pos.subtract(referencePos)`，`:106-132`），并额外写 `key + "_version"` 标记（`:102`），读取时按该标记区分新旧格式（`getConnectionRelative`，`:53-97`）——这是给"已存在的存档"做向前迁移的标准做法，且对每个字段单独 try/catch 降级到 `SimpleConnection` 再降级到 `null`（`:80-96`），单点数据损坏不会崩存档。破坏方块时 `blockBroken(level, connection, selfPos)`（`:155-196`）会反向通知另一端 `clearConnection`，并调用 `TubeFiller.remove` 清掉落；对 `SimpleConnection` 出现在此路径直接 `throw new TubeConnectionException` 报错（`:178`），属于防御性编程。

### 4.6 网络：9 个 payload 全量注册
`network/NetworkHandler.java:14-62` 用 `@EventBusSubscriber(modid=..., bus = Bus.MOD)` + `RegisterPayloadHandlersEvent`，`event.registrar("1")` 声明协议版本 `1`，然后 9 次 `playToClient` / `playToServer`。方向划分清晰：**路径与位置同步（`MovePathPacket`、`SyncEntityPosPacket`、`SpeedChangePacket`）走 S→C**；**玩家意图（`MoveDirectionPacket`、`EscapeTubePacket`、`ActionPointReachPacket`、`FinishPathPacket`）走 C→S**。`MovePathPacket.java:25-89` 是 record + 手写 `StreamCodec.of(encode, decode)`，逐字段 `buf.writeInt/writeDouble/writeBlockPos`，`actionPoints` 用 `Set<BlockPos>` 去重；`junctionDirection` 只在 `isJunctionEnd` 为 true 时才写（`:52-53`）——**可空字段用前置布尔门控的紧凑编码**。handler 一律 `ctx.enqueueWork(() -> ...)`（`:79-83`），保证在主线程执行。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：见 4.6，9 个 payload，`CustomPacketPayload` + `StreamCodec` 新式 API（无 SimpleChannel）。
- **数据驱动**：datagen 已启用但仅 1 个 provider：`core/data/DataGenerators.java:21-31`（`@EventBusSubscriber` + `GatherDataEvent`，`generator.addProvider(event.includeServer(), new HypertubeRecipeGen(packOutput, lookupProvider))`）；`RegistrateDataProvider` 那行被注释掉（`:30`）。同包还有 `HypertubeRecipeGen.java`、`JunctionMode.java`、`JunctionModeProperty.java`（方块状态枚举属性）、`MoveDirection.java`（网络枚举）。源码中未见 `/data/<mod>/...` 的 JSON 资源。
- **配置**：`config/ClientConfig.java` / `config/ServerConfig.java`，注册为 `Type.CLIENT` / `Type.SERVER`，显式指定文件名 `create_hypertube-client.toml` / `-server.toml`（`HypertubeMod.java:34-35`）。`ServerConfig.java:19-30+` 用 `Pair<INSTANCE, SPEC>` 双例写法，含 `EnumValue<EntityListMode>` + `List<? extends String>` 白/黑名单，以及 `SPEED_MULTIPLIER`、`STRESS_IMPACT_ENTRANCE`、`STRESS_IMPACT_ACCELERATOR` 等 Create 应力相关数值（说明它与 Create 的 kinetic 系统对接）。
- 主类里 `commonSetup` 是空方法（`HypertubeMod.java:56-58`），未使用。

## 6. Mixin

三个配置文件：
- `src/main/resources/create_hypertube.mixins.json`：`required: true`，`compatibilityLevel: JAVA_8`，`mixins` = `EntityTravelingMixin`、`IPlayerExtensionMixin`、`KineticBlockMixin`、`PlayerMixin`、`PlayerMovementMixin`、`ServerGamePacketListenerImplMixin`；`client` = `CameraAccessorMixin`、`CameraMixin`、`LocalPlayerMixin`、`PlayerModelAccessor`、`PlayerModelMixin`
- `src/main/resources/compat.mixins.json`：`required: false` + `plugin: CompatMixinPlugin`，`client: ["sable.EntityMixin"]`
- `src/main/resources/conflict_fix.mixins.json`：`required: false`，`client: ["MixinBetterThirdPerson"]`（`@Mixin(value = CustomCamera.class, remap = false)`）

代表 hook（`mixin/core/`）：

| 类 | 目标 | 注入 |
|---|---|---|
| `CameraMixin.java:33,50` | `Camera` | `setup` `@At("HEAD")` cancellable（管道旅行时接管相机） |
| `CameraAccessorMixin.java:11-23` | `Camera` | `@Invoker("setPosition"/"setRotation"/"move"/"getMaxZoom")` 暴露私有方法 |
| `EntityTravelingMixin.java:14-38` | `Entity` | `getGravity` / `getPose` / `hurt` / `isInvulnerableTo` 全部 `HEAD` cancellable（旅行中改物理与免疫） |
| `LocalPlayerMixin.java:14-17` | `LocalPlayer` | `isShiftKeyDown` `HEAD` |
| `PlayerMovementMixin.java:15-18` | `Player` | `canPlayerFitWithinBlocksAndEntitiesWhen` `HEAD`（SWIMMING 姿态下放行碰撞检查） |
| `PlayerModelMixin.java:17-21` | `HumanoidModel` | `setupAnim*` `RETURN`，`priority = 1001`、`order = 1001`（姿势动画） |
| `PlayerModelAccessor.java:12,15` | `PlayerModel` | `@Accessor("cloak")` |
| `KineticBlockMixin.java:22-25` | `BlockBehaviour` | `getCollisionShape` `RETURN`（与 Create 应力/动能方块交互） |
| `ServerGamePacketListenerImplMixin.java:17-20` | `ServerGamePacketListenerImpl` | **`@WrapOperation`**（MixinExtras，非 @Redirect，可与其他 mod 叠加） |

## 7. 值得学的 5 条具体做法

1. **可选依赖用"枚举 + 嵌套 Supplier 惰性引用"隔离**：`core/compat/Mods.java:60-83` + `TravelManager.java:107`。`Mods.SABLE.executeIfInstalled(() -> () -> SableCompat.stickToSubLevel(...))`——外层 Supplier 在 mod 未装时根本不解析 lambda，从而不会触发 `SableCompat` 的类加载。适用：任何 soft-dependency（你依赖 Create/Sable/CC 等可选 mod 时）。
2. **给同一 compat 包配一个 `IMixinConfigPlugin` 按 mod 存在性开关 mixin**：`mixin/compat/CompatMixinPlugin.java:20-34` + `compat.mixins.json`（`required:false`）。目录即约定（`.mixin.compat.sable.X` → 查 `Sable` 是否加载），比在每个 mixin 里写 `@Pseudo`/`@Mixin(remap=false)` 更整齐。
3. **NBT 存相对坐标 + `_version` 字段 + 逐字段 try/catch 降级**：`core/connection/interfaces/ITubeConnectionEntity.java:53-132`。让存了旧存档的玩家无损升级，且单个字段坏了不会崩。适用：所有自研方块实体的连接/多块结构数据。
4. **曲线点只存相对坐标，绝对坐标按需现算**：`core/connection/BezierConnection.java:66,91-138`。结构被活塞推动/复制/分块加载时缓存不失效。适用：轨道、管道、绳索、缆线类几何。
5. **服务端定路径 + 一次性 packet 广播，客户端只回放**：`core/travel/TravelManager.java:91-105` + `network/packets/MovePathPacket.java:25-89`。避免每 tick 同步位置（只在关键点用 `SyncEntityPosPacket`），带宽与一致性都更好；结束时用 `teleportTo(..., RelativeMovement.ALL, ...)` + `hurtMarked = true` 强制客户端对齐。

（补充：`core/placement/TubePlacement.java:111-121,161-170` 客户端预览与服务端确认复用同一条校验链，是防止"客户端能放服务端拒绝"的标准解法；`registry/ModBlockEntities.java` 每个注册类配 `public static void register(){}` 空方法强制类初始化的写法可直接照搬。）

## 8. 公开 API

本项目**不是**库模组，但它对外暴露了两个可供 Create 生态其他 mod 复用的扩展点：

- `core/connection/interfaces/ITubeConnectionEntity`（`ITubeConnectionEntity.java:24-206`）：任何新方块实体只要实现它（含 12 个 `default` NBT 读写方法），就能接入本 mod 的管道连接体系。
- `core/compat/Mods` 枚举 + `mixin/compat/CompatMixinPlugin` 的目录约定：是"如何优雅地做可选 mod 兼容"的参考实现（可被反向复用）。
- `build.gradle:97-99` 将 `dev.ryanhcode.sable:sable-neoforge` 声明为 **`api`** 依赖，即 Sable 类型泄漏到本 mod 公开签名中——接入方需注意这一点。
