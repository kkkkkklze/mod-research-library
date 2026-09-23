# Xalcon/TorchMaster 源码分析

## 1. 基本信息

- Mod 名 / mod_id：Torchmaster / `torchmaster`；作者 Xalcon；版本 `21.1.12`（`gradle.properties`）
- 目标：**Minecraft 1.21.1 / Java 21**，加载器 **Fabric + NeoForge 双端**（`neoforge_version=21.1.41`、`fabric_version=0.103.0+1.21.1`、`fabric_loader 0.16.2`）
- Gradle：官方 MultiLoader 模板结构（`common` / `fabric` / `neoforge` 三子项目，`settings.gradle`），插件 **fabric-loom 1.7-SNAPSHOT + net.neoforged.moddev 0.1.110**，buildSrc + `expandProps` 占位符替换资源
- 许可证 MIT；mapping 用 Parchment 2024.07.28
- 依赖：Fabric 侧 Fabric API、**OwO-lib 0.12.11（配置 GUI/ConfigWrapper）**、ModMenu 11.0.2（仅 UI）；NeoForge 侧 `ModConfigSpec` 原生。它是独立 mod，不对外提供 API

## 2. 源码规模与包结构

- 67 个 `.java`，合计 4296 行（common 45 / fabric 11 / neoforge 11）
- 最大文件：`client/VolumeRendererOverlay.java`(368)、`blocks/FeralFlareLanternBlockEntity.java`(205)、`neoforge/TorchmasterNeoforgeConfig.java`(204)、`client/gui/EntityBlockingLightSettingsScreen.java`(168)、`events/TorchmasterEventHandler.java`(159)、`commands/CommandTorchmaster.java`(143)、`logic/entityblocking/FilteredLightManager.java`(130)、`ModRegistry.java`(124)
- 包：`torchmaster`（Constants/EntityFilterList/ModRegistry/Torchmaster）、`.blocks`、`.items`、`.menu`、`.client`(+`.gui`)、`.commands`、`.compat`、`.config`、`.events`、`.logic`(+`.entityblocking`+`.dreadlamp`/`.megatorch`)、`.mixin`、`.platform`(+`.services`)、`.utils`

## 3. 入口与注册

- common `Torchmaster.java:36 init()`：设置日志级别 → `ModRegistry.initialize()`；`getRegistryForLevel(Level)`（`:52`）用 `serverLevel.getDataStorage().computeIfAbsent(FilteredLightManager.Factory, "torchmaster_lights_" + dimensionIdentifier)` 取每维度 SavedData
- 注册体系是**平台无关的 RegistrationProvider**：`ModRegistry.java:27-31` 定义 `RegistrationProvider<Block> BLOCKS = RegistrationProvider.create(Registries.BLOCK, MOD_ID)` 等 5 个 provider，再 `BLOCKS.register("megatorch", () -> new EntityBlockingLightBlock(...))` 返回 `RegistryObject<T>`；Fabric 侧 `FabricRegistrationFactory`、NeoForge 侧 `NeoforgeRegistrationFactory` 通过 **`META-INF/services/net.xalcon.torchmaster.platform.RegistrationProvider$Factory`** 由 `Services.load()`（`platform/Services.java` 用 `ServiceLoader`）注入
- `IPlatformHelper`（`platform/services/IPlatformHelper.java`）是 common→平台 的桥：`createBlockEntityType`、`createMenuType`、`createCreativeModeTab`、`openMenu`、`getConfig`、`isModLoaded`，实现分别为 `FabricPlatformHelper` / `NeoForgePlatformHelper`
- 入口：Fabric `fabric.mod.json` entrypoints `main=TorchmasterFabric`、`client=TorchmasterFabricClient`；NeoForge `TorchmasterNeoforge.java:22 @Mod(Constants.MOD_ID)` 构造里 `container.registerConfig(ModConfig.Type.COMMON, TorchmasterNeoforgeConfig.spec, "torchmaster.toml")` + `Torchmaster.init()`

## 4. 核心系统

**(a) 维度级光源注册表 FilteredLightManager**：`logic/entityblocking/FilteredLightManager.java` 是 SavedData + `IBlockingLightManager` 实现，内部 `Map<String, IEntityBlockingLight> lights`，核心查询 `shouldBlockEntityType(EntityType, Level, Vec3, MobSpawnType)` 与 `shouldBlockVillageZombieRaid(Vec3)` 全部只做"任一光源命中即 true"的短路遍历；表项由 `IEntityBlockingLight` 实现（`MegatorchEntityBlockingLight`、`DreadLampEntityBlockingLight`）提供，各自通过 `ILightSerializer` 注册进 `LightSerializerRegistry` 做 NBT 序列化——**新增一种阻光方块只需加 1 个 light + 1 个 serializer**。

**(b) 距离判定策略 IDistanceLogic**：`logic/IDistanceLogic.java` 用两个 lambda 常量提供 `Cubic`（含边界 clamp，range=0 即自身 1 格）与 `Cylinder`（`dx²+dz²<=range && |dy|<=range`），`VolumeLogic` 持有 set/getMode 供 GUI 切换；**几何形状是配置项而非硬编码条件**。

**(c) 实体过滤表 EntityFilterList**：`EntityFilterList.java` 维护 `Set<ResourceLocation>`，`applyListOverrides(List<String>)` 支持配置里用 `+modid:entity` / `-modid:entity` 追加/移除，用 `Pattern.compile("[+-][a-z0-9_-]+:[a-z0-9_-]+")`（`IsValidFilterString`）作为 `defineListAllowEmpty` 的校验器，且 `BuiltInRegistries.ENTITY_TYPE.containsKey` 不存在的 id 只警告不崩。两个实例：`Torchmaster.MegaTorchFilterRegistry` / `DreadLampFilterRegistry`。

**(d) 跨加载器生成拦截**：common 侧 `events/TorchmasterEventHandler.java` 是**纯逻辑 API**——`onCheckSpawn(MobSpawnType, Entity, Vec3, EventResultContainer)`、`onPlayerSpawnPhantoms`、`onVillageSiege`、`onServerLevelTickEnd`；平台侧注入：NeoForge `NeoforgeEventHandler.java:18` 订阅 `MobSpawnEvent.PositionCheck` / `PlayerSpawnPhantomsEvent` / `VillageSiegeEvent`（`EventPriority.HIGH`），并把 loader 的 `Result` 枚举与自定义 `EventResult` 互转；Fabric 侧用 mixin（见第 6 节）。`isIntentionalSpawn()`（`:18`）白名单了 SPAWN_EGG/BREEDING/DISPENSER/BUCKET/CONVERSION/TRIGGERED/COMMAND/EVENT/TRIAL_SPAWNER，`isNaturalSpawn()` 只承认 NATURAL/CHUNK_GENERATION/PATROL；两个开关 `blockOnlyNaturalSpawns`、`aggressiveSpawnChecks`（后者 false 时尊重其它 mod 的 ALLOW）决定是否放行。

**(e) Feral Flare Lantern**：`blocks/FeralFlareLanternBlockEntity.java` 按 tickRate 自增计数，在 `feralFlareRadius` 内随机找 `feralFlareMinLightLevel` 以下的暗点放置 `InvisibleLightBlock`（可被替换的隐形光源），受 `feralFlareLanternLightCountHardcap` 限制，并把坐标存入自身 NBT 以便拆除时回收。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **无自定义网络**（仅 `platform` 层 `openMenu` 走 loader 原生菜单打开；`FeralFlareLanternMenu` + `EntityBlockingLightSettingsScreen` 直接读写方块实体/GUI）
- **配置抽象**：common 只依赖接口 `config/ITorchmasterConfig.java`（11 个 getter：半径、tickRate、硬上限、两个 boolean 开关、两个 blockList overrides）。NeoForge 实现 `TorchmasterNeoforgeConfig.java`（`ModConfigSpec`，`defineInRange("megaTorchRadius",64,0,MAX)`、`defineListAllowEmpty(..., EntityFilterList::IsValidFilterString)`）；Fabric 实现走 **OwO-lib**（`TorchmasterConfigModel` / `TorchmasterOwOConfigWrapper`）
- **数据驱动（部分）**：方块属性/战利品/配方在 `common/src/main/resources/data/torchmaster/...`（1.21 新目录名 `loot_table`/`recipe`）；实体黑白名单不是数据包，而是**代码内置表 + 配置 override**
- **datagen**：无（资源 JSON 手写，含 `zh_cn.json` 等 16 种语言）
- **持久化**：`EntityBlockingManager`（旧式全局表）+ `FilteredLightManager`（每维度 SavedData，key `torchmaster_lights_<dim>`）

## 6. Mixin

- 配置：`common/.../torchmaster.mixins.json`（空 mixins，占位）、`fabric/.../torchmaster.fabric.mixins.json`（5 个）、`neoforge/.../torchmaster.neoforge.mixins.json`（空，改走事件）；refmap `${mod_id}.refmap.json`，JAVA_21
- Fabric 侧类（`fabric/src/main/java/net/xalcon/torchmaster/mixin/`）：`NaturalSpawnerMixin` 用 MixinExtras `@WrapOperation` 包裹 `NaturalSpawner.isValidPositionForMob` 与 `spawnMobsForChunkGeneration` 中对 `Mob.checkSpawnRules` 的调用（`:27-49`，转给 `MobWrapper.checkSpawnRules`）；另有 `BaseSpawnerMixin`、`PhantomSpawnerMixin`、`SpawnUtilMixin`、`VillageSiegeMixin`、`package-info.java`
- NeoForge 侧唯一 mixin 为 `neoforge/.../mixin/MixinTitleScreen.java`（与刷怪无关）
- 注释里明确记录了取舍：不 hook `Mob#checkSpawnRules` 本身是因为"子类覆写不调 super 就会漏"

## 7. 值得学的 5 条具体做法

1. **MultiLoader 平台服务层**：common 只写逻辑 + 接口，平台用 `META-INF/services` + `ServiceLoader` 注入 `IPlatformHelper` / `RegistrationProvider.Factory`；`common/.../platform/Services.java`；适用于同时出 Forge/NeoForge/Fabric 的库。
2. **`RegistrationProvider` 代替 DeferredRegister 写跨平台注册**：`BLOCKS.register("megatorch", supplier)` 返回 `RegistryObject`，common 代码无 loader 概念；`common/.../platform/RegistrationProvider.java`。
3. **跨加载器事件统一成普通方法**：把生成拦截写成 `TorchmasterEventHandler.onCheckSpawn(..., EventResultContainer)`，NeoForge 用事件、Fabric 用 mixin 各自接线；`common/.../events/TorchmasterEventHandler.java`；避免逻辑分叉两份。
4. **配置项校验器复用业务正则**：`defineListAllowEmpty(..., EntityFilterList::IsValidFilterString)` 让配置加载期就拒绝坏格式，`+/-` 前缀式 override；`neoforge/TorchmasterNeoforgeConfig.java:89`。
5. **SavedData 按维度分片 + 工厂静态字段**：`FilteredLightManager.Factory` + `computeIfAbsent(Factory, "torchmaster_lights_"+dim)`；`Torchmaster.java:57`；适用于"每维度一份"的运行时表。

## 8. 公开 API

非 API 类 mod，无对外扩展点。可复用的工程面是 `net.xalcon.torchmaster.platform`（`Services`/`IPlatformHelper`/`RegistrationProvider`/`RegistryObject`，源自 jaredlll08 MultiLoader 模板）与 `logic.IDistanceLogic` 的函数式距离策略；第三方想扩展阻光方块需在 common 内新增 `IEntityBlockingLight` + `ILightSerializer` 实现，没有对外的注册入口。

注：本快照目录缺少部分文件（如 `fabric.mod.json`、`META-INF/services/*`），上述内容以 `git ls-files` / `git show HEAD:...` 读到的版本库内容为准。
