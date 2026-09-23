# AlexModGuy/AlexsCaves 源码分析报告

## 1. 基本信息

| 项 | 值 | 来源 |
|---|---|---|
| Mod 名 / mod_id | Alex's Caves / `alexscaves` | `src/main/resources/META-INF/mods.toml` |
| 作者 | Alexthe668, Noonyeyz | 同上 |
| 目标版本 / 加载器 | MC 1.20.1 / Forge（`loaderVersion="[46,)"`，依赖 `forge [47.1.3,)`） | `mods.toml` |
| Gradle 插件 | ForgeGradle 5.1.+、mixingradle 0.7-SNAPSHOT、parchment 映射 | `build.gradle` |
| 映射 | `parchment 2023.09.03-1.20.1` | `build.gradle` |
| Java 版本 | 17（toolchain） | `build.gradle` |
| 许可证 | GNU LGPL（mods.toml 声明；仓库内无 LICENSE 文本文件，本地检出未包含） | `mods.toml` |
| 版本 | 2.0.2 | `build.gradle` / `mods.toml` |

**编译依赖（重点）**：`fg.deobf("curse.maven:citadel-331936:6702068")` 是 **compile 期硬依赖**，`mods.toml` 中 `modId="citadel" mandatory=true versionRange="[2.6.0,)" ordering="AFTER"`。JEI 仅 `compileOnly`（`jei-1.20.1-common-api` / `-forge-api`，15.20.0.116），非硬依赖。**Citadel 就是它的 API 基座**：本 mod 的 mixin 配置里同时加载了 `citadel.mixins.json`（`build.gradle` 的 `mixin { config 'citadel.mixins.json' }`），并直接调用 Citadel 的 `ExpandedBiomes`、`PartEntity`、`CitadelConstants.REMAPREFS`、`EventReplaceBiome`。

**注意本地检出的完整性**：仓库有 `.git`（HEAD `4718f42`），且存在 non-cone 稀疏检出模式列表（`**/*.java`、`**/*.properties`、`**/*.mixins.json` 等）。结果：`src/main/java`（996 个 java）、`alexscaves.mixins.json`、`assets/alexscaves/books/**`（560 个 txt 图鉴）在，但 **`src/main/resources/data/**`（worldgen biome/structure/feature JSON、tag、recipe）与贴图/lang 不在本地检出里**，因此凡涉及数据文件的具体内容一律标"未确认"。

## 2. 源码规模与包结构

实测：`find src -name '*.java' | wc -l` = **996**；`cat | wc -l` = **126562** 行（平均约 127 行/文件）。

包（第 3 层）文件数 Top：

- `server/entity/ai` **91** — 全部自定义 Goal（`AtlatitanMeleeGoal`、`UnderzealotProcessionGoal`、`GingerbreadManStealGoal` …）与自定义路径导航（`AdvancedPathNavigateNoTeleport`、`SemiAquaticPathNavigator`、`AllFluidsPathNavigator`、`GroundPathNavigatorNoSpin`、`FlightPathNavigatorNoSpin`）与 NodeEvaluator（`NotLavaSwimNodeEvaluator`、`AllFluidsNodeEvaluator`）
- `client/render/entity` **90** — 每个生物一个渲染器（含 `layer/` 子包）
- `server/level/feature` **62** — 世界生成 feature（`feature/config` 子包 10 个 Codec 配置类）
- `server/entity/living` **54** — 生物主体类
- `server/entity/item` **40** / `server/entity/util` **38** — 投掷物与接口/混入型工具类
- `server/level/structure` **39**（含 `piece/`、`processor/`）
- `server/block/blockentity` **21**，`client/render/blockentity` **13**，`client/gui/book` **10**（洞窟图鉴 GUI）
- 其他：`server/level/biome` 5、`server/level/surface` 2、`server/level/carver` 2、`mixin` + `mixin/client` 54

最大的 10 个文件：

| 行数 | 文件 |
|---|---|
| 1431 | `server/entity/living/TremorzillaEntity.java` |
| 1160 | `client/event/ClientEvents.java` |
| 1108 | `client/model/ForsakenModel.java` |
| 1079 | `client/ClientProxy.java` |
| 911 | `server/entity/living/GumWormEntity.java` |
| 868 | `server/entity/living/MagnetronEntity.java` |
| 842 | `server/entity/living/CandicornEntity.java` |
| 823 | `client/model/TremorzillaModel.java` |
| 778 | `client/model/RelicheirusModel.java` |
| 740 | `server/entity/living/GummyBearEntity.java` |

观察：模型/渲染代码占比极高（`client/model` 用 `AdvancedModelBox` 手写动画），没有独立的 `api` 包，是典型的"内容 mod"而非库 mod。

## 3. 入口与注册

主类 `src/main/java/com/github/alexmodguy/alexscaves/AlexsCaves.java:63` `@Mod(MODID)`。

注册框架：**纯 Forge `DeferredRegister` + 每个子系统一个 `ACXxxRegistry` 类**，统一在构造器里挂到 mod 事件总线（`AlexsCaves.java:104-130`）：

```java
ACBlockRegistry.DEF_REG.register(modEventBus);
ACItemRegistry.DEF_REG.register(modEventBus);
ACEntityRegistry.DEF_REG.register(modEventBus);
ACFeatureRegistry.DEF_REG.register(modEventBus);
ACStructureRegistry.DEF_REG.register(modEventBus);
ACStructurePieceRegistry.DEF_REG.register(modEventBus);
ACStructureProcessorRegistry.DEF_REG.register(modEventBus);
ACSurfaceRuleConditionRegistry.DEF_REG.register(modEventBus);
ACCarverRegistry.DEF_REG.register(modEventBus);
ACPotPatternRegistry.DEF_REG.register(modEventBus);
PROXY.commonInit();
ACBiomeRegistry.init();
```

注册规模：`ACEntityRegistry` 83 个实体、`ACFeatureRegistry` 50 个 feature、`ACStructureRegistry` 14 个 `StructureType`（`underground_cabin`/`ferrocave`/`volcano`/`dino_bowl`/`acid_pit`/`ocean_trench`/`abyssal_ruins`/`forlorn_canyon`/`forlorn_bridge`/`cave_cake`/`soda_bottle`/`donut_arch`/`licowitch_tower`/`gingerbread_town`）、16 个网络包。

**双端代理模式**：`AlexsCaves.java:67` `public static CommonProxy PROXY = DistExecutor.runForDist(() -> ClientProxy::new, () -> CommonProxy::new)`，`PROXY.commonInit()` / `clientInit()` / `initPathfinding()` 分流。`clientSetup` 只做 `event.enqueueWork(() -> PROXY.clientInit())`（`AlexsCaves.java:176-178`）。

**自定义 MobCategory**（`ACEntityRegistry.java:24-25`）——扩展原版刷怪分类，为洞穴生物单独开辟刷怪桶：

```java
public static final MobCategory CAVE_CREATURE = MobCategory.create("cave_creature", "alexscaves:cave_creature", 10, true, true, 128);
public static final MobCategory DEEP_SEA_CREATURE = MobCategory.create("deep_sea_creature", "alexscaves:deep_sea_creature", 20, true, false, 128);
```

## 4. 核心系统

### 4.1 洞穴群系"稀有群系"注入体系（本项目最值得学的一块）

**职责**：不改原版 `dimension/overworld.json`，把 6 个自定义洞穴群系（`magnetic_caves`/`primordial_caves`/`toxic_caves`/`abyssal_chasm`/`forlorn_hollows`/`candy_cavity`）插进原版 `MultiNoiseBiomeSource`，并按 Voronoi 单元"稀有地生成"。

**核心文件**：`server/level/biome/ACBiomeRegistry.java`、`ACBiomeRarity.java`、`VoronoiGenerator.java`（在 `server/misc/`）、`server/config/BiomeGenerationConfig.java`、`BiomeGenerationNoiseCondition.java`、`mixin/BiomeSourceMixin.java`、`mixin/MultiNoiseBiomeSourceMixin.java`、`mixin/ChunkStatusMixin.java`

**关键设计点**：

1. **先"扩容"群系集合，再"劫持"取样**。`ACBiomeRegistry.init()`（第 29-36 行）通过 Citadel 的 `ExpandedBiomes.addExpandedBiome(KEY, LevelStem.OVERWORLD)` 把 6 个群系登记进主世界可生成集合；`BiomeSourceMixin` 混入 `BiomeSource`，用 `@Shadow public Supplier<Set<Holder<Biome>>> possibleBiomes` 把它换成 `Suppliers.memoize(builder::build)` 的新集合，并实现 `BiomeSourceAccessor` 暴露 `Map<ResourceKey<Biome>, Holder<Biome>>` 供反查（`getResourceKeyMap()`）：
   ```java
   @Shadow public Supplier<Set<Holder<Biome>>> possibleBiomes;
   public void expandBiomesWith(Set<Holder<Biome>> newGenBiomes) { ... possibleBiomes = Suppliers.memoize(builder::build); }
   ```
2. **`@Inject(at = HEAD, cancellable = true)` 直接短路 `getNoiseBiome`**（`MultiNoiseBiomeSourceMixin.java:29-47`，`@Mixin(priority = -69420)` 保证最后执行）：用 `ACBiomeRarity.getRareBiomeInfoForQuad(seed, x, z)` 求该 quadrant 的 Voronoi 单元 → `getRareBiomeOffsetId` → 匹配 `BiomeGenerationConfig.BIOMES` 里同 offset 的 `BiomeGenerationNoiseCondition` → 命中即 `cir.setReturnValue(...)` 绕过原版气候取样。
3. **噪声条件用"中心点采样"而非逐点采样**：`BiomeGenerationNoiseCondition.test()` 先算 Voronoi 中心 `ACBiomeRarity.getRareBiomeCenter(info)`，只在中心处 `sampler.sample(...)` 取 continentalness/erosion/humidity/temperature/weirdness/depth，再逐区间比对——保证同一群系在单元内形状完整、边界不碎裂。默认条件示例：`magnetic_caves` = 主世界 + `distanceFromSpawn(400)` + `rarityOffset(0)` + `continentalness(0.6,1)` + `depth(0.2,1)`。
4. **世界种子传递靠第三个 mixin**：`MultiNoiseBiomeSource.getNoiseBiome` 本身拿不到 seed，`ChunkStatusMixin` 在 `ChunkStatus.generate(...)` 的 HEAD 处把 `serverLevel.getSeed()` 与 `serverLevel.dimension()` 塞进 `MultiNoiseBiomeSourceAccessor`，供下次取样使用。

### 4.2 群系视觉/环境参数集中表

`ACBiomeRegistry` 把"群系 → 视觉"做成静态查表：`getBiomeAmbientLight`、`getBiomeFogNearness`、`getBiomeWaterFogFarness`、`getBiomeSkyOverride`、`getBiomeLightColorOverride`（如 `TOXIC_CAVES_LIGHT_COLOR = new Vec3(0.5, 1.5, 0.5)` 允许 >1 的高亮），并由客户端 mixin（`FogRenderer` 相关、`BiomeAmbientSoundsHandler*`、`UnderwaterAmbientSound*`）消费，实现"洞内独立天空盒/光照/雾/环境音"。

### 4.3 多部件实体（Multipart）

`server/entity/util/ACMultipartEntity.java` 继承 Forge `PartEntity<T>`：`blocksBuilding = true`、`fireImmune() = true`、`save()` 返回 false（不落盘）、`isPickable()/canBeCollidedWith()` 全转发父实体。玩家交互在客户端通过 `MultipartEntityMessage(parentId, playerId, 0, 0)` 发回服务端，再由父实体 `interact` 处理——即"单个逻辑实体 + 多个碰撞盒"（Tremorzilla / Atlatitan / Luxtructosaurus 这类巨型生物）。

### 4.4 自定义路径导航与 Goal 库

`server/entity/ai` 下 91 个类，抽象出可复用组件：`AdvancedPathNavigateNoTeleport`（禁传送、适配巨型/挖掘生物）、`SemiAquaticPathNavigator` / `VerticalSwimmingMoveControl`（水陆两栖）、`FlightPathNavigatorNoSpin` + `LookForwardsGoals`（飞行不转头）、`AllFluidsPathNavigator` + `AllFluidsNodeEvaluator`（可穿酸液等自定义流体）、`GroundPathNavigatorNoSpin`。配套通用 Goal：`MobTarget3DGoal`、`MobTargetClosePlayers`、`MobWanderThroughStructureGoal`、`AnimalPackTargetGoal`、`AnimalJoinPackGoal`、`LookAtLargeMobsGoal`——都是可直接借鉴的参数化 Goal。

### 4.5 表面规则与地形

`server/level/surface/ACSurfaceRules.java` + `ACSurfaceRuleConditionRegistry.java`：把自定义 `SurfaceRules.Condition`（实现 `LazyXZCondition`/`LazyYCondition`）注册后，用 `ACSurfaceRules.setup()` 在 `FMLCommonSetupEvent` 里拼装 `SurfaceRules.RuleSource`，让不同洞穴群系刷不同表层。这需要大量 AT 开放原版内部成员——见 `src/main/resources/META-INF/accesstransformer.cfg` 里对 `SurfaceRules$Context`（`updateXZ`/`updateY`/`blockX/blockY/blockZ`）、`NoiseBasedChunkGenerator#createNoiseChunk`、`LevelChunkSection#biomes`、`ChunkMap#randomState` 的破封。

## 5. 网络 / 数据驱动 / 配置 / datagen

**网络**：Forge `SimpleChannel`（`AlexsCaves.java:70-75`），`PROTOCOL_VERSION = "1"`，通道 `alexscaves:main_channel`。16 个包在 `commonSetup` 顺序注册，全部手写 `write`/`read`/`handle` 三方法引用（`NETWORK_WRAPPER.registerMessage(idx++, X.class, X::write, X::read, X::handle)`），无自动序列化框架。工具方法：`sendMSGToServer`、`sendMSGToAll`、`sendNonLocal(msg, player)`（`NetworkDirection.PLAY_TO_CLIENT`）。典型包：`MultipartEntityMessage`、`UpdateEffectVisualityEntityMessage`、`UpdateBossBarMessage`、`UpdateCaveBiomeMapTagMessage`、`WorldEventMessage`（自定义世界事件广播）。

**配置（数据驱动、可被整合包调参）**：双 ForgeConfigSpec —— `ACServerConfig`（`alexscaves-general.toml`）+ `ACClientConfig`（`alexscaves-client.toml`）；另外 `BiomeGenerationConfig` 不读 toml 而是**手写 GSON 文件读写**，把每个群系的生成条件落到 `config/` 下的独立 JSON（`getOrCreateConfigFile(configDir, configName, defaults, type, isInvalid)`，`FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES`），并在 `ModConfigEvent.Loading` / `Reloading` 回调里 `reloadConfig()` 重建 `BIOMES` 表。整合包作者因此可以单独关掉某个洞穴群系或改其深度/大陆度范围。

**无 datagen**：全仓 grep 不到 `GatherDataEvent` / `DataProvider`，`build.gradle` 也无 `data` run 之外的收集任务（`data` run config 只用来起客户端做调试）。资源（worldgen JSON、lang、模型、贴图）都是手工维护的。这一条对想抄其"注册 50 个 feature"的人来说是成本提示。

**Mod 互操作**：`server/misc/ACLoadedMods.java` 在 `FMLLoadCompleteEvent` 后缓存 `ModList.get().isLoaded("distanthorizons" | "entityculling")`，避免每帧查 ModList；`AlexsCaves.readModIncompatibilities()`（`AlexsCaves.java:203-217`）用 `WebHelper.getURLContents` **在线拉取 GitHub 上的 `mod_generation_conflicts.txt`**，把不兼容 modid 列表塞进 `MOD_GENERATION_CONFLICTS` 做世界生成前的警告——一种"不需要发版就能更新兼容性黑名单"的做法。

## 6. Mixin

配置文件：`src/main/resources/alexscaves.mixins.json`（`required: true`、`package: com.github.alexmodguy.alexscaves.mixin`、`compatibilityLevel: JAVA_17`、`refmap: alexscaves.refmap.json`），通过 gradle `mixin { config 'alexscaves.mixins.json' }` + `add sourceSets.main, "citadel.refmap.json"` 接入；`build.gradle` 同时把 `citadel.mixins.json` 也加进 config 列表。共 54 个 mixin 类（`mixin/` 29 + `mixin/client/` 25）。

代表性 hook 目标：

- `MultiNoiseBiomeSourceMixin` → `MultiNoiseBiomeSource#getNoiseBiome(IIILClimate$Sampler;)`，`@At("HEAD")` + `cancellable`（洞穴群系接管，上文 4.1）
- `BiomeSourceMixin` → `BiomeSource#possibleBiomes`（`@Shadow` 字段改写 + 实现 accessor 接口）
- `ChunkStatusMixin` → `ChunkStatus#generate(Executor, ServerLevel, ChunkGenerator, ...)`，`@At("HEAD")`（传递 seed/dimension）
- `NaturalSpawnerMixin` → `NaturalSpawner#spawnMobsForChunkGeneration(ServerLevelAccessor, Holder<Biome>, ChunkPos, RandomSource)`（干预洞内刷怪）
- `LivingEntityMixin` → `LivingEntity#calculateEntityAnimation(Z)`、`LivingEntity#tick()`、`LivingEntity#increaseAirSupply(I)`（水下呼吸/动画）
- `EntityMixin` → `Entity#<init>(EntityType, Level)`（`@At("TAIL")`，注意用了 `remap = CitadelConstants.REMAPREFS`）、`Entity#tick()`、`Entity#onSyncedDataUpdated(EntityDataAccessor)`
- `PlayerMixin` → `Player#getSpeed()`、`Player#getFlyingSpeed()`（磁力/坐骑影响移动）
- `MonsterMixin` / `MobMixin` / `FoodDataMixin` / `PotionUtilsMixin` / `IllagerMixin` / `FrogMixin`
- 世界生成相关：`CoralFeatureMixin`、`KelpFeatureMixin`、`SeagrassFeatureMixin`、`LakeFeatureMixin`、`MultifaceGrowthFeatureMixin`（在群系内允许/禁止原版地物）
- 结构相关：`JigsawStructureMixin`、`OceanMonumentStructureMixin`、`ShipwreckStructureMixin`、`SwampHutPieceMixin`（把原版结构挪进/移出洞穴群系）
- 客户端 25 个：`CameraMixin`、`LevelRendererMixin`、`LightTextureMixin`、`GameRendererMixin`、`MinecraftMixin`、`LocalPlayerMixin`、`ClientLevelMixin`、`LiquidBlockRendererMixin`、`SpriteResourceLoaderMixin`、`SoundEngineMixin`、`OptionsMixin` 等

AT 文件 `src/main/resources/META-INF/accesstransformer.cfg` 是另一条"绕开 mixin"的路径，公开了约 45 个原版成员，重点在 `SurfaceRules.*`、`StructureTemplate#palettes/entityInfoList`、`FireworkRocketEntity`、`ClientChunkCache$Storage`、`SoundEngine`、`LevelChunkSection#biomes`。

## 7. 值得学的 5 条具体做法

1. **用 Voronoi 单元 + "中心点采样"代替逐点气候采样来放稀有群系**：把"稀有"与"位置条件"解耦，Voronoi 决定能不能生成、气候条件决定长什么样，避免群系边界被气候噪声切碎。文件：`server/level/biome/ACBiomeRarity.java`、`server/config/BiomeGenerationNoiseCondition.java`。适用场景：任何要往原版维度插入"大块、稀有、形态完整"的自定义群系。
2. **三 mixin 协作完成"seed 传递 → 群系集合扩容 → 取样短路"**：`ChunkStatusMixin` 注入 seed、`BiomeSourceMixin` 扩集合、`MultiNoiseBiomeSourceMixin` 短路取值，每个 mixin 只干一件事并用 accessor 接口 (`BiomeSourceAccessor`/`MultiNoiseBiomeSourceAccessor`) 解耦。文件：`mixin/ChunkStatusMixin.java`、`mixin/BiomeSourceMixin.java`、`mixin/MultiNoiseBiomeSourceMixin.java`。适用场景：需要在 mixin 之间传状态时，用"mixin 实现接口 + `(XxxAccessor) this` 强转"而不是静态变量。
3. **自定义 `MobCategory.create(...)` 开辟专属刷怪桶**：`ACEntityRegistry.java:24-25` 用 6 参数 `create(name, key, spawnCap, isFriendly, isPersistent, despawnDistance)` 造出 `cave_creature`(cap 10) 与 `deep_sea_creature`(cap 20)，再用 `NaturalSpawnerMixin` 控制只有对应群系/高度才刷。适用场景：洞穴/深海/天空等原版刷怪逻辑覆盖不到的维度层。
4. **巨型生物用 `PartEntity` 做"一个逻辑实体 + N 个碰撞盒"**：`server/entity/util/ACMultipartEntity.java` 不落盘、不免疫交互、`interact` 全转发父实体，客户端命中通过自定义包回传服务端。适用场景：Boss/巨兽需要分部位受击与显示伤害数字。
5. **配置既支持 toml 也支持 JSON 落盘 + 事件重载**：`BiomeGenerationConfig.reloadConfig()` 在 `ModConfigEvent.Loading/Reloading` 里重建 `BIOMES` 表，整合包可逐个群系开关。文件：`server/config/BiomeGenerationConfig.java`、`AlexsCaves.java:135-141`。适用场景：需要给整合包作者细粒度开关世界生成内容的库/内容 mod。

（补充可选做法）**在线拉取兼容性黑名单**：`AlexsCaves.readModIncompatibilities()` + `server/misc/WebHelper.java`，把不兼容 mod 列表放 GitHub 原始文件里热更新。适用范围有限（离线环境需容错），但思路可借鉴于"生成冲突"这类需要持续维护的清单。

## 8. 非库 mod 说明

本仓库不含公开 API 包，无对外扩展点设计（`server/entity/util` 下的 `KaijuMob`、`GummyColors`、`PossessesCamera` 等接口是本 mod 内部跨类协作约定）。它是 Citadel API 的**消费者**而非提供者；若要复用其技术，路径是抄实现（mixin + accessor + 数据表）而非依赖其 API。
