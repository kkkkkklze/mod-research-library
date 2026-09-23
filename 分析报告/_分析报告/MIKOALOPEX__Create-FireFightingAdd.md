# MIKOALOPEX/Create-FireFightingAdd 源码分析报告

## 1. 基本信息

- Mod 名：Create Firefighting Add；mod_id：`createfirefightingadd`；作者 MIKOALOPEX
- 版本 0.2.3-beta（`HANDOFF.md` 记录基线为 0.2.1-beta）；目标 MC 1.21.1 / NeoForge 21.1.228，Java 21
- 构建：Gradle + `net.neoforged.moddev` 2.0.141；`src/main/templates/META-INF/neoforge.mods.toml`（`[[mixins]] config = "${mod_id}.mixins.json"`）
- 许可证：`Code: MIT; Art Assets: All Rights Reserved`（README 明确双许可）
- 依赖（`gradle.properties` + `build.gradle:133-143`）：**Create 6.0.10-280（required `[6.0.10,6.1.0)`）**、Ponder 1.0.82、Flywheel 1.0.6、Registrate MC1.21-1.3.0+67；JEI `-api` compileOnly/runtimeOnly；Jade 用**本地 jar** `compileOnly files("libs/jade-15.10.5.jar")`；可选 Sable / Aeronautics / Simulated / Offroad / Synaxis / Tracks / `sable_schematic_api`。注意：虽依赖 Registrate，主类实际用原生 `DeferredRegister`。

## 2. 源码规模与包结构

210 个 `.java`，38101 行。三大包：`com.mikoalopex.createfirefightingadd.api`（12 文件，5 子包）、`content`（最大，分 `blocks/extension_ladder|fire_hose|fire_pole|flow_meter|traffic_cone`、`equipment/backtank|extinguisher|handheld`、`fluids/hydraulic_ram|nozzle|water_intake`、`items/configurator|firefighter`、`kinetics/pump|turbine`、`contraptions`、`ponder`）、`integration`（`sable` 14、`sableschematic` 2、`burnt` 1、`WaterIntakeJadePlugin`）。
最大文件：`content/fluids/nozzle/AbstractSprayDeviceBlockEntity.java`(2457)、`blocks/fire_hose/FireHoseBlockEntity.java`(2261)、`fluids/nozzle/SprayDeviceMovementBehaviour.java`(1035)、`CreateFireFightingAdd.java`(937)、`items/configurator/MultifunctionConfiguratorScreen.java`(908)、`fluids/hydraulic_ram/HydraulicRamBlockEntity.java`(769)。

## 3. 入口与注册

主类 `src/main/java/com/mikoalopex/createfirefightingadd/CreateFireFightingAdd.java:181`。注册全用**原生 DeferredRegister** 字段（:189-200）：`BLOCKS / ITEMS / CREATIVE_MODE_TABS / BLOCK_ENTITY_TYPES / MENU_TYPES / SOUND_EVENTS / ARMOR_MATERIALS / ENTITY_TYPES / DATA_COMPONENTS / MOUNTED_FLUID_STORAGE_TYPES`（最后一个用 `DeferredRegister.create(CreateRegistries.MOUNTED_FLUID_STORAGE_TYPE, MODID)`，:199-200），构造器里逐个 `register(modEventBus)`（:546-555）。

```java
public static final DeferredHolder<DataComponentType<?>, DataComponentType<SimpleFluidContent>> FIRE_EXTINGUISHER_FLUID =
    DATA_COMPONENTS.registerComponentType("fire_extinguisher_fluid",
        builder -> builder.persistent(SimpleFluidContent.CODEC)
            .networkSynchronized(SimpleFluidContent.STREAM_CODEC));  // :202-205
```

Create 注册表在 `commonSetup` 的 `enqueueWork` 里手动登记（:574-586）：`MovementBehaviour.REGISTRY.register(...)` 6 个、`MountedFluidStorageType.REGISTRY.register(...)` 4 个、`BlockStressValues.IMPACTS/CAPACITIES.register(...)` 4 个（:565-568）。Capability 集中在 `registerCapabilities`：11 个 `FluidHandler.BLOCK`、1 个 `ItemHandler.BLOCK`、1 个 `FluidHandler.ITEM`（:603-664）。另有 `RemapManager`（顶层类）做旧 block id → 新 Block 实例的迁移映射（:540-544）。

## 4. 核心系统

**（1）喷雾设备体系（最核心）** — `content/fluids/nozzle/`
`AbstractSprayDeviceBlockEntity`（2457 行）抽象基类，`ConeNozzleBlockEntity / FlatNozzleBlockEntity / BucketControllerBlockEntity` 继承；切面形状抽为 `SprayShape` 接口，实现 `ConeSprayShape / FanSprayShape / CylinderSprayShape`：`forEachPosition(origin,direction,PositionAction)` 按距离排序遍历体素，`stratifiedDirections(baseDirection,count,tick,Random)` 保证**客户端/服务端用同一 seed 生成完全一致的喷射方向**（`SprayShape.java:36-42`），另有 `randomSprayDirection` 的双 RandomSource/Random 重载。流体行为由 `enum FluidBehavior` + 大量常量（`RAY_STEP=0.5`、`PUSH_STREAM_SPEED=0.20`）驱动。

**（2）可配置喷雾规则（数据驱动）** — `NozzleSprayRule` / `NozzleSprayRuleSet`
`record NozzleSprayRule(FluidStack target, NozzleParticlePalette particles, boolean flammable, extinguishing, igniting, List<ResourceLocation> effects, @Nullable ResourceLocation fanProcessingType, boolean locked)`，`MAX_EFFECTS=32`，构造器强制 `extinguishing && igniting → igniting=false`；`NozzleSprayRuleSet` 上限 `MAX_RULES=64`，`find()` 跳过 `locked` 规则做**同流体+同组件**匹配（`FluidStack.isSameFluidSameComponents`），`findForSpray()` 再放宽到只比流体类型。规则以物品 `CustomData`（TAG = `"NozzleSprayRules"`）持久化，用 `content/items/configurator/MultifunctionConfiguratorScreen`(908) 图形化编辑 + `MultifunctionConfiguratorSavePacket` 回传。

**（3）喷雾性能治理** — `SprayProjectileBudget.java` / `SprayAuxiliaryScheduler.java`
预算用 `Collections.synchronizedMap(new WeakHashMap<>())` 按 owner 计活跃弹数与"生成信用"（soft/hard 双阈值 + `spawnRate(active,soft,hard)` 平滑）；调度器按 `sourcePos` 哈希相位错峰（`phase = floorMod(key ^ key>>>32, interval)`），活跃喷嘴超过 `sprayMaxActiveNozzlesBeforeDegrade` 时区间最多放大 8 倍。`AbstractSprayDeviceBlockEntity` 里还有硬上限常量 `MAX_PATH_BLOCK_CHECKS_PER_TICK=4096`、`MAX_PATH_EFFECTS_PER_TICK=96`。并有 `SprayPerformanceDebug`、`SprayDebugRenderer`。

**（4）消防水带（含动态结构）** — `content/blocks/fire_hose/`
`FireHoseBlockEntity`(2261) 实现 `api.fire_hose.FireHoseConnectionAccess`，内部私有 `record PipePressureInfo(float inbound,float outward,boolean directionKnown,boolean pushesTowardRequester)`、`record PumpScanResult(...)` 与私有类 `HoseFluidHandler implements IFluidHandler`；`HoseRoute` 是可视化路径（`UUID id`、`List<Node> nodes`、`ResourceLocation appearance = FireHoseAppearances.DEFAULT`、`long revision`），注释明确"首尾节点是唯一流体端点"；`HoseRoutes` 做路由表，`FireHoseMovingEndpoints` + `FireHoseMovementBehaviour` 处理被 contraption 带走的情况。

**（5）第三方兼容用反射隔离** — `AbstractSprayDeviceBlockEntity.java:117-350`
对 TFC（`tryTfcDouse`）、Wildfire（`smolderTrackerClass`/`smolderStrengthField`）、Create Diesel Generators（`cdgFuelTypeKeyField`/`cdgNormalMethod`）都用缓存的 `Method/Field` + `Available/Checked` 双布尔懒初始化，避免硬依赖；`registerSableSchematicCompat()` 甚至用 `Class.forName(...).getMethod("register").invoke(null)` 并捕获 `LinkageError`（`CreateFireFightingAdd.java:588-601`）。

**（6）扩展点 API** — `api/nozzle/NozzleSprayInteractionRegistry.java`
`CopyOnWriteArrayList<NozzleSprayBlockInteraction>` + `ConcurrentHashMap.newKeySet()` 的 `REPORTED_FAILURES` 实现**每个回调 try/catch + 只警告一次**（`warnOnce`），配合 `NozzleSprayBlockTarget`（方块或 BE 均可实现）双路派发（`targetShouldReceive` 同时查 `state.getBlock()` 与 `level.getBlockEntity()`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络（**值得注意的反例/优点**）：17 个 `record ... implements CustomPacketPayload`，**每个包类自己就是 `@EventBusSubscriber`** 并暴露 `@SubscribeEvent static void register(RegisterPayloadHandlersEvent event)`，用 `event.registrar(CreateFireFightingAdd.MODID).playToServer(TYPE, STREAM_CODEC, X::handle)` 自注册——没有中央 PacketHandler（见 `content/equipment/handheld/HandheldNozzleSprayPacket.java:20-27`）。Codec 用 `StreamCodec.composite(ByteBufCodecs.BOOL, ...)`，handler 内 `context.player() instanceof ServerPlayer player` 校验。
- 配置：`Config.java`（SERVER，`ModConfigSpec`，常量如 `HOSE_MAX_LENGTH / HOSE_PRESSURE_RECOVERY_PER_TICK / sprayAuxiliaryInterval`）+ `ClientConfig.java`（CLIENT），类上 `@EventBusSubscriber` 监听 `ModConfigEvent`。
- 数据驱动：无 JSON/数据包驱动内容；"数据"载体是物品 DataComponent（`NozzleSprayRuleSet`）。
- datagen：**无** datagen 包；`src/main/resources` 在本副本中仅含 `createfirefightingadd.mixins.json`（assets/data 未包含，原因未确认）。
- 其他：Ponder 由 `content/ponder/CreateFireFightingPonderPlugin` + `index/CreateFireFightingPonderScenes|Tags` + 8 个 `scenes/*Scenes.java` 组织。

## 6. Mixin

`src/main/resources/createfirefightingadd.mixins.json`：`required:true`、`compatibilityLevel: JAVA_21`、`package: com.mikoalopex.createfirefightingadd.mixin`、`injectors.defaultRequire:1`、`overwrites.requireAnnotations:true`，但 **`mixins` 与 `client` 数组均为空** —— 本模组不使用任何 Mixin，全部通过 Create 官方 API（`MovementBehaviour.REGISTRY`、`MountedFluidStorageType.REGISTRY`、`BlockStressValues`、`CreateRegistries`）+ NeoForge 事件实现。

## 7. 值得学的 5 条具体做法

1. **不用 mixin 也能做 Create 附属**：官方注册表 + `enqueueWork` 延迟注册是首选路径；`CreateFireFightingAdd.java:564-586`。适合对稳定性敏感的发布版。
2. **`stratifiedDirections(baseDirection, count, tick, Random)` 共享 seed 保证双端一致**，避免喷射方向同步包；`SprayShape.java:36-42`。适用于任何需要两端视觉一致的效果。
3. **"预算 + 错峰"双管性能**：`WeakHashMap` 按 owner 记额度（`SprayProjectileBudget`）+ 按方块坐标哈希相位错峰并随负载线性降频（`SprayAuxiliaryScheduler`）。适合大范围扫描/粒子/实体生成类系统。
4. **给运行期回调加"故障熔断 + 一次警告"**：`NozzleSprayInteractionRegistry.safeOnHit` 用 `try/catch` 包住外部模组回调，`REPORTED_FAILURES` 保证同 handler 只警告一次；`api/nozzle/NozzleSprayInteractionRegistry.java`。适合暴露 API 的库/附属。
5. **可选依赖只用反射，且缓存在 `*Checked/*Available` 布尔 + `Method/Field` 字段里，并捕获 `LinkageError`**；`AbstractSprayDeviceBlockEntity.java:117-350`、`CreateFireFightingAdd.java:588-601`。适合兼容 TFC/同类流体模组。
6. （补充）**`RemapManager.registerAll(blockName -> switch (blockName) {...})`** 把"旧存档方块 id → 新 Block"的迁移集中成 switch；`CreateFireFightingAdd.java:540-544`。

## 8. （库/前置类 mod 专项）

非前置，但含对外 `api` 包：`api/nozzle/`（`NozzleSprayInteractionRegistry`、`NozzleSprayBlockTarget`、`NozzleSprayBlockInteraction`、`NozzleSprayHitContext`、`NozzleSprayFluidType`）、`api/fire_hose/`（`FireHoseAppearances`、`FireHoseConnectionAccess`、`FireHoseConnectionHelper`、`FireHoseEndpointModel`）、`api/backtank/MultipurposeBacktankFluidApi`、`api/handheld/HandheldNozzleBindingApi`、`api/kinetics/PressureSourceStressProvider`（成员方法取名 `createFireFightingAdd$getPressureSourceSpeed()` 前缀避免与其它模组接口冲突）。接入方式：实现接口（`NozzleSprayBlockTarget`）或注册回调（`NozzleSprayInteractionRegistry.register`）+ 各 `*Api` 静态方法，无 Forge/NeoForge 注解或 `@Mod` 级插件机制。
