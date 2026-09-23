# Luke100000/ImmersiveAircraft 源码分析报告

## 1. 基本信息

- Mod 名：Immersive Aircraft；mod_id `immersive_aircraft`（短 ID `ic_air`，用于网络频道，见 `common/src/main/java/immersive_aircraft/Main.java:11-12`）；作者 Conczin（Maven 组 `net.conczin`）。
- 目标版本：MC **1.20.1**，加载器 **fabric + forge 双端**（`gradle.properties`: `enabled_platforms=fabric,forge`）；Forge 47.0.3、Fabric Loader 0.15.9 / API 0.83.1。
- Gradle：**Architectury** 多模块（`architectury-plugin 3.4-SNAPSHOT` + `dev.architectury.loom 1.10-SNAPSHOT`），Mojang mappings + **Parchment 2023.09.03**，Java 17，`group_id=net.conczin`。
- 编译依赖：cloth-config 11.0.99、mod-menu 7.0.1、JEI 15.2.0.27、REI 12.0.684，另有跨 mod 兼容项 `ad_astra_version`、`man_of_many_planes`、`immersive_machinery`（均为 SNAPSHOT）。许可证未在 `gradle.properties` 声明（未确认具体协议）；注意 `Main.java:22` 调用了 mxparser 的 `License.iConfirmNonCommercialUse("Conczin")` —— 该数学表达式库为**非商用**授权。
- 注意：本地为 partial clone（`.git` 内有 promisor pack），`src/main/resources` 仅拉到了 `assets/immersive_aircraft/sounds`，其余资源/数据 json 未下载。

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **179 个文件，12088 行**（比一般实体 mod 小，但单文件密度极高）。

包结构（`common/src/main/java/immersive_aircraft/`，三层）：
- `entity`（14 个载具类：`AirplaneEntity/AirshipEntity/BiplaneEntity/GyrodyneEntity/QuadrocopterEntity/WarshipEntity/BambooHopperEntity/CargoAirshipEntity` 等）、`entity/bullet`、`entity/weapon`、`entity/inventory`(+`slots`)、`entity/misc`
- `client/render/entity/renderer`(+`bullet`/`utils`)、`client/hud`（姿态仪 5 个指示器）、`client/gui`、`screen`(+`slot`)
- `network/c2s`（5）、`network/s2c`（5）、`cobalt/network`、`cobalt/registration`（跨平台抽象层）
- `item/upgrade`、`config/configEntries`、`data`、`resources/bbmodel`（自写 BlockBench 模型解析）、`mixin`(+`client`)、`combat`、`util`

最大文件：`VehicleEntity.java` 1014 行、`InventoryVehicleEntity.java` 427、`EngineVehicle.java` 387、`client/OverlayRenderer.java` 337、`resources/bbmodel/BBCube.java` 199、`entity/misc/VehicleData.java` 198、`WarshipEntity.java` 195、`client/hud/AttitudeIndicator.java` 195。

## 3. 入口与注册

主类 `common/src/main/java/immersive_aircraft/Main.java` 是纯静态常量/工具类（无 @Mod，无平台代码），真正的平台入口是两个薄壳：

- Forge：`forge/src/main/java/immersive_aircraft/forge/CommonForge.java:18-37`，`@Mod(Main.MOD_ID)`；静态块里只做**注入实现**，再 bootstrap 各注册模块：

```java
static { Main.MOD_LOADER = "forge"; new RegistrationImpl(); new NetworkHandlerImpl(); new CobaltFuelRegistryImpl(); }
public CommonForge() {
    DataLoaders.bootstrap(); Items.bootstrap(); Sounds.bootstrap(); Entities.bootstrap();
    WeaponRegistry.bootstrap(); Messages.loadMessages();
    DEF_REG.register(FMLJavaModLoadingContext.get().getModEventBus());
}
```

- Fabric：`fabric/src/main/java/immersive_aircraft/fabric/CommonFabric.java:18-46`，`ModInitializer`，同样静态块替换三件实现，`onInitialize` 里直接 `Registry.register(BuiltInRegistries.CREATIVE_MODE_TAB, ...)`。

- **注册框架 = 自研 "cobalt" 抽象层**（不是 DeferredRegister/Registrate 直用）：`cobalt/registration/Registration.java` 暴露 `register(Registry, ResourceLocation, Supplier)`、`register(EntityType, EntityRendererProvider)`、`registerDataLoader/ResourceLoader`，由平台 `RegistrationImpl` 实现。Forge 侧 `forge/cobalt/registration/RegistrationImpl.java:55-79` 内部按 `(namespace, registry)` 缓存 **DeferredRegister** 实例，`register` 时惰性创建对应的 `DeferredRegister.create(registry, namespace)`。

## 4. 核心系统

### 4.1 载具实体基类 VehicleEntity（**最值得精读**）
`entity/VehicleEntity.java`（1014 行）。职责：一套通用的"可骑乘载具"物理 + 同步骨架，所有载具（飞机/飞艇/坦克）继承。
- 同步数据用 `SynchedEntityData`：`DATA_HEALTH`、`DAMAGE_WOBBLE_TICKS/SIDE/STRENGTH`、`BOOST`（第 73-81 行）。
- 输入用 **插值对象** `InterpolatedFloat pressingInterpolatedX/Y/Z`（97-99 行）+ `setInputs()`，避免客户端按键在服务端跳变。
- 服务端权威位置 + 客户端插值：`lerpTo(...)`（375 行）与 `handleClientSync()`（561 行）按 `interpolationSteps` 逐 tick 迫近 `x/y/z`、`serverYRot/serverXRot`；`isControlledByLocalInstance()` 时才重置插值步。
- `tick()` 拆成 `tickPilot()/tickDamageParticles()/handleClientSync()`，子类只需实现 `updateVelocity()` 与 `updateController()`（582/588 行）——典型的"模板方法"式载具架构。
- 撞墙伤害在**客户端算、发包给服务端**：重写 `move()`（779-799 行），用 `prediction.distanceTo(position())` 与位移长度之差求碰撞强度，再 `NetworkHandler.sendToServer(new CollisionMessage(damage))`；`repeat = 1 - (wobbleTicks+1)/10` 做冷却衰减。
- 骑手下车被拦截：`mixin/PlayerEntityMixin.java:22` 注入 `Player.wantsToStopRiding` 返回 false。

### 4.2 引擎/燃料子系统 EngineVehicle
`entity/EngineVehicle.java:38-236`。`ENGINE`/`UTILIZATION`/`LOW_ON_FUEL` 三个同步字段；`enginePower` 是 `InterpolatedFloat(20.0f)`，`enginePower.setSteps(getEngineReactionSpeed() / getProperties().get(VehicleStat.ACCELERATION))`（128 行）——**用配装属性决定插值速度**，即车辆升级直接改变物理手感。燃料常量 `TARGET_FUEL=1000 / LOW_FUEL=900`，`consumeFuel()` 由 `InventoryVehicleEntity` 里的燃料槽供给（`CobaltFuelRegistry` 允许其他 mod 注册燃料）。带 `Cautions` 枚举警告灯系统供 HUD 使用。

### 4.3 数据驱动载具定义（datapack）
`entity/misc/VehicleData.java` + `data/VehicleDataLoader.java`。载具的**属性、物品栏槽位、武器挂点、乘客座位、碰撞箱、尾迹**全部由一个 json 定义，Datapack 可覆盖。
- 目录由 `super(new Gson(), "aircraft")` 决定（`VehicleDataLoader.java:22`），即 `data/<ns>/aircraft/*.json`；`REGISTRY`（服务端）与 `CLIENT_REGISTRY` 两份 Map，`get()` 对未知 id 返回共享 `EMPTY` 实例避免 null。
- `VehicleData` 三套构造：`JsonObject`（数据包）、`FriendlyByteBuf`（网络同步，`readInt` + `readUtf`）、空构造。
- `passengerPositions` 是 `List<List<PositionDescriptor>>`（每个座位多个候选点），`weaponMounts` 为 `Map<Integer, Map<WeaponMount.Type, List<WeaponMount>>>` 并以 `blocking` 标记是否为遮挡火力位。
- 武器槽数量由 `inventoryDescription.getSlots(WEAPON)` 与 `weaponMounts` 数组**按下标一一配对**（`slot = weaponSlots.remove(0)`，`VehicleData.java:38-41`）。

### 4.4 自写 BlockBench 模型渲染（bbmodel）
`resources/bbmodel/` + `client/render/entity/renderer/utils/BBModelRenderer.java`。把 BlockBench 的 `.bbmodel` 直接解析成运行时模型（`BBCube` 199 行），载具细节因此可以随时改模型而不用改 Java；这是"用工具链降低美术迭代成本"的范例。

### 4.5 升级/属性系统
`item/upgrade/VehicleStat.java`（枚举 `STATS` Map，含 `defaultValue()`）、`VehicleUpgrade`、`VehicleUpgradeRegistry`。升级数据同样走 datapack（`data/UpgradeDataLoader.java`），解析时只接受 `VehicleStat.STATS` 中存在的键，未知键静默忽略（`DataLoader.java:16-25`），保证数据包向前兼容。

## 5. 网络 / 数据驱动 / 配置 / datagen

**网络（cobalt 抽象层，不依赖 Fabric Networking API 或 SimpleChannel 直接调用）**
- `cobalt/network/Message.java` 只有两个抽象方法：`encode(FriendlyByteBuf)` + `receive(Player)`；`NetworkHandler`（41 行）提供 `registerMessage(Class<T>, Function<FriendlyByteBuf,T>)`、`sendToServer`、`sendToPlayer`、`sendToTrackingPlayers`，`Impl` 抽象类静态注入实现（`INSTANCE = this`）。消息类通过 `构造函数(FriendlyByteBuf)` 引用注册，等价于 Mojang 的 codec 但更短。
- 全部 10 条消息集中注册在 `Messages.java:9-18`（c2s：`EnginePowerMessage/CommandMessage/RequestInventory/CollisionMessage/FireMessage`；s2c：`OpenGuiRequest/InventoryUpdateMessage/VehicleUpgradesMessage/AircraftDataMessage/FireResponse`），命名前缀 `Main.SHORT_MOD_ID` 作频道命名空间。
- `CommandMessage` 带 `Key` 枚举（DISMOUNT/BOOST 等）+ 当前速度 `getDeltaMovement()`，把"按键意图"和"载具状态"一起发，方便服务端校验：客户端读客户端按键 → 发包 → 服务端执行。
- **数据包内容联网同步**：`AircraftDataMessage` 把服务端 `VehicleDataLoader.REGISTRY`（全部载具 json 数据）在玩家登录/数据包重载时整体序列化下发（`Fabric` 侧挂 `ServerLifecycleEvents.SYNC_DATA_PACK_CONTENTS`，`CommonFabric.java:46`），客户端存 `CLIENT_REGISTRY`。即"数据包规则服务端权威、客户端只读副本"。
- 客户端接口 `network/NetworkManager.java`（3 个 handle 方法）由 `ClientNetworkManager` 实现，避免 common 代码直接引用客户端类。

**配置**：完全自研的 `config/JsonConfig.java` —— 反射遍历自身字段上的注解（`@BooleanConfigEntry/@FloatConfigEntry/@IntegerConfigEntry`）填默认值，`loadOrCreate(new Config(MOD_ID), Config.class)` 生成 `config/immersive_aircraft.json`，并有 `version/getVersion()` 做迁移；`ConfigScreen` + `ModMenuIntegration` 提供 GUI。比 Cloth Config 前置更省依赖。

**datagen**：无（无 `runData`/DataGenerator 相关代码与 `datagen` 包）。

## 6. Mixin

配置文件 `common/src/main/resources/immersive_aircraft.mixins.json`：`required: true`，`compatibilityLevel: JAVA_17`，`defaultRequire: 1`。
- 通用 3 个：`PlayerEntityMixin`、`ProjectileUtilMixin`、`ServerPlayerEntityMixin`。
- 客户端 11 个：`AbstractClientPlayerMixin`、`CameraMixin`、`ClientPlayerEntityMixin`、`ClientPlayerInteractionManagerMixin`、`ClientPlayNetworkHandlerMixin`、`EntityRenderDispatcherMixin`、`GameRendererMixin`、`KeyMappingAccessorMixin`、`KeyMappingMixin`、`LivingEntityRendererMixin`、`PlayerEntityRendererMixin`。

代表 hook（`mixin/PlayerEntityMixin.java`，`@Mixin(value = Player.class, priority = 1100)`）：
- `wantsToStopRiding` @ HEAD, cancellable → 阻止骑手下车；
- `updatePlayerPose()V` @ TAIL → 强制 `Pose.STANDING`（否则骑乘姿势被原版改回）；
- `isScoping()Z` @ HEAD → 载具瞄准镜代替玩家望远镜；
- `getDestroySpeed` @ RETURN → 在载具上挖掘速度 ×5。
`priority = 1100`（高于默认 1000）说明作者刻意让自己在其他 mixin 之后生效。

## 7. 值得学的 5 条具体做法

1. **跨平台抽象层只包两件事**：`cobalt/registration` 包注册、`cobalt/network` 包发包，平台侧各自一个 `Impl` 子类在 `static {}` 中挂上（`CommonForge.java:19-25` / `CommonFabric.java:19-25`），common 代码零 `@Mod`。适用：任何想做双端加载器的实体/载具 mod。
2. **载具物理用模板方法拆分**：`VehicleEntity` 管同步/插值/乘客/伤害，子类只写 `updateVelocity()` 与 `updateController()`；新增机型成本 = 一个类 + 一个 datapack json。
3. **输入用 `InterpolatedFloat` 平滑并参与同步**（`entity/VehicleEntity.java:97-99`，`util/InterpolatedFloat.java`），并让插值步长由升级属性驱动（`EngineVehicle.java:128`）。适用：所有"手感敏感"的载具/机械实体。
4. **客户端预测、服务端裁决的碰撞伤害**：客户端在 `move()` 里算碰撞强度发包（`VehicleEntity.java:779-799`），服务端只处理伤害 —— 省去服务端逐 tick 反推，同时带 `repeat` 冷却防连击。
5. **datapack 定义实体参数 + 登录时整包下发**（`VehicleDataLoader` + `AircraftDataMessage`），配合"未知键忽略"的宽松解析（`DataLoader.java:16-25`）让数据包不像代码那样容易崩版本。适用：Create 附属/机械类 mod 的配方与属性表。

## 8. 公开 API / 扩展点

非库 mod，但留了两个外部接入点：
- **燃料注册**：`cobalt/registration/CobaltFuelRegistry.java`（平台实现 `CobaltFuelRegistryImpl`），其他 mod 可把自定义燃料物品登记进引擎系统（`EngineVehicle.consumeFuel`，`EngineVehicle.java:224`）。
- **载具/升级数据包**：外部 mod 只要在 `data/<自己的ns>/aircraft/*.json` 放文件（`VehicleDataLoader` 用 `SimpleJsonResourceReloadListener` 按目录扫描并保留原始 id 命名空间），即可新增载具定义；`WeaponRegistry.bootstrap()`（`common/src/main/java/immersive_aircraft/WeaponRegistry.java:13`，由两个平台入口调用）是武器类型注册入口。
- 兼容适配：`combat/JEICCombat.java`、`combat/REICombat.java`、`CompatUtilImpl` 展示了"同功能多 mod 兼容（JEI/REI 二选一）"的写法。
