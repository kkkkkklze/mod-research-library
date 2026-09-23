# McJtyMods/LostCities 源码分析报告

## 1. 基本信息

- Mod 名：Lost Cities（失落的城市）；`mod_id = lostcities`；作者 McJty；版本 `1.20-7.5.5`（gradle.properties）
- 目标：**Forge 1.20.1**（`loaderVersion="[47,)"`，`modId="forge" versionRange="[43.1.30,)"`，src/main/resources/META-INF/mods.toml），Java 17，纯 Java（无 mixin）
- Gradle：ForgeGradle `5.1.+` + ParchmentMC librarian + `com.hypherionmc.modutils:modpublisher:2.0.4`；`build.gradle` 中 `apply from 'https://raw.githubusercontent.com/McJtyMods/MultiWorkspace/1.20_tech/gradletools.gradle'`，因此用 `repos() / runs('lostcities') / jars('lostcities')` 这类 McJty 自研 DSL 声明依赖
- 许可证：MIT；编译依赖仅 JEI / TOP（The One Probe），无强制运行时前置
- `task apiJar` 只打包 `mcjty/lostcities/api/**`，说明它是**被其他 mod 依赖的API型 mod**（见第 8 节）

## 2. 源码规模与包结构

实测：`223` 个 `.java`，共 `28153` 行。第 3 层包文件数：`worldgen` 131、`api` 20、`varia` 14、`commands` 14、`gui` 12、`config` 9、`setup` 8、`playerdata` 3、`network` 3、`editor` 3、`datagen` 2。

最大文件：`worldgen/LostCityTerrainFeature.java`(2355)、`worldgen/lost/BuildingInfo.java`(2295)、`worldgen/NoiseChunkOpt.java`(962)、`config/LostCityProfile.java`(816)、`worldgen/highway/IntercityHighwayPlanner.java`(634)、`gui/GuiLCConfig.java`(570)、`worldgen/lost/cityassets/CityStyle.java`(567)、`setup/ForgeEventHandlers.java`(556)、`worldgen/gen/Scattered.java`(537)、`worldgen/lost/CitySphere.java`(509)。

注意：本副本 `src/main/resources/` 只剩 `META-INF`，内建数据资产（`data/lostcities/lostcities/` 的 buildings/palettes 等）被裁剪；`AGENTS.md` 确认资产目录原本存在。

## 3. 入口与注册

主类 `src/main/java/mcjty/lostcities/LostCities.java:24`（`@Mod` + `@Mod.EventBusSubscriber(bus=MOD)`）：构造里 `Registration.init(bus)`、`CustomRegistries.init(bus)`、注册 CLIENT/COMMON/SERVER 三份 ForgeConfigSpec、`setup.preInit()`，并用 `bus.addListener` 挂 init / IMC / datapack 回调。

```java
Registration.init(bus);            // 只注册 2 个 Feature
CustomRegistries.init(bus);        // 13 个 datapack registry
ModLoadingContext.get().registerConfig(ModConfig.Type.SERVER, Config.SERVER_CONFIG);
bus.addListener(CustomRegistries::onDataPackRegistry);  // DataPackRegistryEvent.NewRegistry
```

注册框架是 Forge 原生 `DeferredRegister`。`setup/Registration.java:26-27` 只注册 `lostcity`、`spheres` 两个 `Feature`，真正的重头在 `setup/CustomRegistries.java`：13 个独立 datapack registry（buildings/palettes/parts/styles/conditions/citystyles/multibuildings/variants/worldstyles/predefinedcities/predefinedspheres/scattered/stuff），各自 `ResourceKey.createRegistryKey` + `event.dataPackRegistry(KEY, XXXRE.CODEC)`（`CustomRegistries.java:70-84`）。

## 4. 核心系统

**4.1 数据驱动资产层** `worldgen/lost/cityassets/AssetRegistries.java`
- 用统一的 `RegistryAssetRegistry<运行期对象, RE原始元素>` 桥接 datapack registry 与运行期对象（`AssetRegistries.java:15-27`），每种资产一份（如 `PARTS`、`BUILDINGS`、`PALETTES`）。
- 惰性两阶段加载：`load(CommonLevelAccessor)` 只加载生成必需的 parts/buildings/stuff；`loadPredefinedStuff()` 延迟加载 predefined cities/spheres，避免每次开世界全量解析。
- `volatile boolean loaded` + `synchronized` 双检锁；`reset()` 在换世界时整体清空（由 `LostCityFeature.cleanUpInternal()` 调用）。
- `STUFF_BY_TAG` 在加载后一次性把 stuff 按 tag 建索引，避免生成期遍历。

**4.2 区块特征判定与缓存** `worldgen/lost/BuildingInfo.java`
- `private static final TimedCache<ChunkCoord, LostChunkCharacteristics> CITY_INFO_MAP`（`BuildingInfo.java:161`），TTL 来自 `Config.CACHE_CLEANUP_SECONDS`；`getChunkCharacteristics` 走带锁的双检（`BuildingInfo.java:368-374`），生成期可并发读取同一 chunk 特征。
- `LostCityEvent.CharacteristicsEvent` 在特征算完后派发（`BuildingInfo.java:480`），允许外部 mod 改写城市/建筑类型——数据外的第二层扩展点。
- `getBuildingInfo(ChunkCoord, IDimensionInfo)` 与 `getChunkCharacteristicsGui(...)` 分离 GUI 查询与生成查询路径。

**4.3 城市/街道布局** `worldgen/lost/City.java`
- 每维度一份 `CITY_RARITY_MAP`（`City.java:34`）与 `TimedCache<ChunkCoord, CityStyle> CITY_STYLE_CACHE`，`isCityCenter/getCityRadius/getCityStyle/getCityFactor` 都由哈希噪声 + rarity map 推导，保证纯函数式可重算。
- 预定义城市/建筑/街道用 `volatile Map` 惰性构建（`predefinedCityMap` 等 `City.java:29-37`），`calculateOccupied` 预先算出被占 chunk。
- 高层规划器：`worldgen/highway/IntercityHighwayPlanner`、`worldgen/street/HierarchicalStreetPlanner`，通过 `IDimensionInfo.getHighwayPlanner()/getStreetPlanner()` 暴露给生成代码。

**4.4 生成主流程** `worldgen/LostCityTerrainFeature.java`
- `generate(WorldGenRegion, ChunkAccess)` 为总入口，分派 `doNormalChunk` / `doCityChunk`；地形侧 `generateHeightmap`、`correctTerrainShape`、`clearRange`，内容侧 `generateBuilding`、`generateStreet`、`generateBorders`、`generateRubble`、`generateRuins`、`generateDebris`、`handleLoot`。
- 写方块统一走 `setBlocksFromPalette(..., char character)` + `CompiledPalette`（`LostCityTerrainFeature.java:2142`），即"字符 → 调色板 → BlockState"两级映射，这也是数据包只写字符就能造建筑的原因。
- 支持 `StructureAvoidance` 与村庄/结构规避（`Config.isAvoidedStructure`），并在生成失败时调用 `ErrorLogger` 记录 chunk 快照而不崩溃。

**4.5 并发与生命周期** `worldgen/LostCityFeature.java`
- 4096 条 striped `ReentrantLock`，`getGenerationLockStripe(dimension, chunkX, chunkZ)` 做混合哈希，`runWithChunkNeighborhoodLocks` 对 3x3 邻域取锁并按序加解锁（`LostCityFeature.java:96-131`）——因为后处理会跨 chunk 边界写方块。
- `ReentrantReadWriteLock lifecycleLock` + `static volatile int globalDimensionInfoDirtyCounter`：单机换图时用计数器+写锁统一清空 `dimensionInfo`、`AssetRegistries`、`LostCitiesImp`、`ForgeEventHandlers` 缓存（`lockCurrentLifecycleForReading`）。

**4.6 配置与 Profile** `config/LostCityProfile.java`(816 行) + `config/ProfileSetup.java`
- `ProfileSetup.STANDARD_PROFILES` 是 `Map<String, LostCityProfile>`，除内建 profile 外还从 `config/lostcities/*.json` 读用户 profile（`ProfileSetup.java:479`）。
- `LostCityProfile.toJson(boolean readonly)` / 构造 `LostCityProfile(String name, String json)` 支持 profile 整份 JSON 序列化往返，客户端选定的 profile JSON 由 `GuiLCConfig.selectProfile` 写入 `Config.profileFromClient/jsonFromClient`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/PacketHandler.java:26-40`，旧式 `NetworkRegistry.newSimpleChannel(new ResourceLocation("lostcities", name), () -> "1.0", s->true, s->true)`，只 2 个包 `PacketRequestProfile` / `PacketReturnProfileToClient`（手写 `toBytes/构造器/handle`）。用途：客户端把选好的 profile(JSON) 带到服务器、服务器把 profile 回传给客户端。
- 数据驱动：核心就是第 3 节的 13 个 datapack registry，每个 `XXXRE`（`worldgen/lost/regassets/*.java`）带自己的 `Codec`；`RE` 只负责解析，运行期对象（`cityassets/*.java`）由 `RegistryAssetRegistry` 转换，解析与执行彻底分离。
- 配置：`setup/Config.java` 三份 `ForgeConfigSpec`（client.toml/common.toml/server.toml）；`getProfileForDimension` 惰性构建 `dimensionProfileCache`，`DIMENSION_PROFILES` 用 `"<dimensionId>=<profileName>"` 字符串列表表达维度→profile 映射；`SELECTED_PROFILE="<CHECK>"` 时才回退到客户端选值（`Config.java:93-107`）。
- datagen：`datagen/DataGenerators.java` 仅注册 `LCBlockTags`（方块 tag），资源源集包含 `src/generated/resources`。

## 6. Mixin

**无 mixin**。全仓库无 `*.mixins.json`、无 `spongepowered` 引用、无 refmap；`build.gradle` 未加载 MixinGradle。对原版私有成员的访问全部通过 `src/main/resources/META-INF/accesstransformer.cfg`（如 `CreateWorldScreen` 的 `f_100833_`/`field_146331_K`/`tabManager`、`NoiseChunk m_209247_`、`DensityFunctions$Marker`、`NoiseBasedChunkGenerator m_224284_`、`StructureManager f_220460_`），其余介入点用 Forge 事件（`ForgeEventHandlers`：`RegisterCommandsEvent`、`AttachCapabilitiesEvent<Entity>`、`PlayerLoggedInEvent`、`LevelTickEvent`、`ServerAboutToStartEvent`、`CreateSpawnPosition`、`PlayerSleepInBedEvent`）。教程价值：**能不做 mixin 就不做**，AT + 事件 + datapack registry 已足够支撑一整套程序化城市生成。

## 7. 值得学的 5 条做法

1. **把内容做成 datapack registry 而不是硬编码**：13 个 `ResourceKey<Registry<...>>` + `DataPackRegistryEvent.NewRegistry#dataPackRegistry`，让数据包可新增建筑/风格（`setup/CustomRegistries.java:70-84`）；适用：任何"内容量大且要被包作者扩展"的 mod。
2. **解析对象(RE) 与运行期对象分离 + 统一桥 `RegistryAssetRegistry`**：`worldgen/lost/cityassets/AssetRegistries.java:15-27`；适用：数据驱动内容需要预热/条件化，或运行期对象不能直接反序列化。
3. **惰性双阶段加载 + volatile 双检锁**：生成必需资产与"预定义"资产分两批加载（`load` / `loadPredefinedStuff`），换世界只 `reset()`；适用：世界生成 mod 的启动开销控制。
4. **可复用的 TTL 缓存 `varia/TimedCache.java`**：`ConcurrentMap + ttl 供给函数 IntSupplier + AtomicLong 定期清理（cas 抢清理权）`，被 `BuildingInfo.BuildingInfo`/`City` 复用，TTL 直接绑到 config 值；适用：生成期需要跨 chunk 记忆但必须能释放。
5. **跨 chunk 写入用分条锁(striped lock)而非全局锁**：`LostCityFeature.java:96-131` 对 (dimension,x,z) 求哈希取 4096 条锁之一，3x3 邻域去重后按序加锁，允许非重叠 chunk 并发生成；适用：任何会破坏邻域的 worldgen。

## 8. 对外 API（库/前置型）

- 公开包：`src/main/java/mcjty/lostcities/api/`（20 个文件），并单独产出 `apiJar`（build.gradle `task apiJar`，只 include `mcjty/lostcities/api/**`）。
- 接入方式：Forge **IMC**，`LostCities.java:69-80` 中 `event.getIMCStream(ILostCities.GET_LOST_CITIES::equals)` / `GET_LOST_CITIES_PRE`；调用方按 `ILostCities.java` 注释发送 `InterModComms.sendTo("lostcities", ILostCities.GET_LOST_CITIES, ModSetup.GetLostCities::new)`。
- 主要扩展点：`ILostCities`（`getLostInfo(Level)`、`registerDimension(key, profile)`、`setOverworldProfile(profile)`）、`ILostCityInformation`（`getChunkInfo/getSphere/getRealHeight/getBuildings/getMultiBuildings/getCityStyles`）、`ILostCityProfileSetup.createProfile(name, baseProfile)`（实现在 `config/LostCityProfileSetupImp.java`，在 `FMLCommonSetupEvent` 前注册自定义 profile）、以及 `LostCityEvent` 的 5 个子事件（`CharacteristicsEvent`/`PreGenCityChunkEvent`/`PostGenCityChunkEvent`/`PostGenOutsideChunkEvent`/`PreExplosionEvent`）。
- 兼容层：`src/api/java/ivorius/reccomplex/dimensions/DimensionDictionary.java` 是给 Recurrent Complex 用的编译期 API stub（独立 sourceSet，不打包）。
