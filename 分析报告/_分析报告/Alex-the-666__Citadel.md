# Alex-the-666/Citadel 源码分析（库/前置 mod）

## 1. 基本信息
- Mod 名 **Citadel**（"A shared code library for many of Alexthe666's mods. Code used from LLibrary with permission."）；mod_id `citadel`；作者 Alexthe666，credits Gegy1000；包名 `com.github.alexthe666.citadel`（Gradle group 仍是历史值 `com.tfar.citadel`）。
- 本快照：MC **1.19.3** + Forge **44.0.1**（`gradle.properties`: `mc_version= 1.19.3`、`forge_version=44.0.1`；`mods.toml` version 2.3.3，loaderVersion `[44,)`），Java 17。
- Gradle：**ForgeGradle 5.1.+（旧版，非 NeoGradle）** + `com.github.johnrengelman.shadow` 7.1.2（多一个 `shade`/`library` 配置 + `minecraft.runs.all` 注入 classpath）+ mixingradle。
- 许可证 **GNU LGPL**。编译依赖只有 `minecraft 'net.minecraftforge:forge:...'` 与 mixin annotationProcessor，**不依赖任何其他 mod** —— 它是链条顶端。
- 注意：AlexsMobs(1.20.1) 依赖的 `citadel [2.6.0,)` 是 1.20.1 分支产物，与本仓库快照版本不同（API 形态基本一致）。

## 2. 源码规模与包结构
- **152 个 .java / 14,555 行**（典型前置库量级：小而接口密集）。
- 包（直接文件数）：`client/model/container` 11、`mixin` 10、`client/gui/data` 9、`client/gui` 9、`client/model` 8、`mixin/client` 8、`server/tick/modifier` 7、`animation` 7、`server/entity/collision` 6、`client/event` 6、`server/message` 5、`server/entity` 5、`math` 5、`item` 5、`server/generation` 4、`server/world` 4、`config/biome` 4、`client/render` 4。
- 最大文件：`client/gui/GuiBasicBook.java` 764、`math/Tuple2f.java` 535、`client/model/container/JsonUtils.java` 503、`math/Tuple2i.java` 468、`client/model/AdvancedModelBox.java` 401、`client/game/Tetris.java` 359、`math/CitadelSimplexNoise.java` 356、`client/render/LightningBoltData.java` 326。

## 3. 入口与注册
`Citadel.java:74` `@Mod("citadel")`。用**静态初始化**建通道（可被其他类直接引用）：
```java
public static final SimpleChannel NETWORK_WRAPPER = NetworkRegistry.ChannelBuilder
    .named(PACKET_NETWORK_NAME).clientAcceptedVersions(PROTOCOL_VERSION::equals)...simpleChannel(); // :79-84
public static ServerProxy PROXY = DistExecutor.runForDist(() -> ClientProxy::new, () -> ServerProxy::new);
```
构造函数 `:102-120`：注册 `ITEMS`/`BLOCKS`/`BLOCK_ENTITIES`（debug、citadel_book、effect_item、fancy_item、icon_item、lectern）+ `BIOME_MODIFIER_SERIALIZERS`（`mob_spawn_probability` = `SpawnProbabilityModifier`）；`FMLCommonSetupEvent` 里注册 4 个包（PropertiesMessage/AnimationMessage/SyncClientTickRateMessage/DanceJukeboxMessage，`:140-143`）并**联网**从 GitHub raw 拉 `patreon.txt`（`WebHelper.getURLContents`，失败仅告警）—— 付费者名单热更新的取巧做法。

## 4. 核心系统
1. **动画框架**：`animation/IAnimatedEntity.java`（`NO_ANIMATION`、get/setAnimationTick、get/setAnimation、getAnimations[]）+ `animation/Animation.java`（`Animation.create(duration)`、事件回调）+ `AnimationHandler.INSTANCE`（枚举单例，`sendAnimationMessage` 只发 `ArrayUtils.indexOf(entity.getAnimations(), animation)` 一个 int 索引 + 实体 id，`updateAnimations` 自增 tick 并在起止帧 post `AnimationEvent.Start/Tick` 到 Forge 总线，可 cancel）。
2. **Tabula 模型体系**：`client/model/TabulaModelHandler.java:27`（枚举单例，`addDomain(String)` 白名单 + `loadTabulaModel(path)` 读 `.tbl`/model.json，Gson 反序列化到 `TabulaModelContainer`）；`TabulaModel`/`AdvancedEntityModel`/`AdvancedModelBox`/`BasicModelPart`/`ModelAnimator`/`ITabulaModelAnimator`/`LegArticulator`；`math/`（SimplexNoise、Tuple2f/2i）辅助骨骼插值。
3. **可变 tick 速率系统**：`server/tick/TickRateTracker.java`（`List<TickRateModifier>` + `masterTickCount`，提供 `getDayTimeIncrement`、`getEntityTickLengthModifier`、`addTickBlockedEntity`、`tickEntityAtCustomRate` 抽象）+ `server/tick/modifier/*`（`CELESTIAL`/`GLOBAL`/`LOCAL_ENTITY`/`LOCAL_POSITION` 四类修饰器，全部 `toTag/fromTag` 存档）+ `server/world/ModifiableTickRateServer.java`、`client/tick/ClientTickRateTracker.java`，由 `MinecraftServerMixin`/`ServerLevelMixin`/`IModifiesTime` 接入。
4. **跨模组世界生成注入**：`server/generation/SurfaceRulesManager.java:13-58` 用 4 个静态 `List<SurfaceRules.RuleSource>`（Overworld/Nether/End/Cave）+ `mergeRules` 把多个 mod 的 surface rule 串起来，再由 `ChunkGeneratorMixin`/`NoiseBasedChunkGeneratorMixin` 一次性注入；同目录还有 `VillageHouseManager`、`SpawnProbabilityModifier`；`server/world/ExpandedBiomeSource`/`ExpandedBiomes` + `BiomeSourceMixin`/`MultiNoiseBiomeSourceMixin` 实现"往已有群系源里塞自定义群系"。
5. **实体附加数据**：`server/entity/ICitadelDataEntity` + `CitadelEntityData.java:15-28`（`getOrCreateCitadelTag(LivingEntity)`，由 `LivingEntityMixin` 持久化+同步的 NBT 容器）；同目录 `IComandableMob`、`IDancesToJukebox`、`IModifiesTime`；`server/entity/collision/*`（6 文件）提供可复用碰撞盒。
6. **配置**：`config/ConfigHolder.java` + `ServerConfig.java`（ForgeConfigSpec，注册 COMMON）；`config/biome/SpawnBiomeConfig.java` 另外维护 JSON 配置体系。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：Forge `SimpleChannel`，4 个 `server/message/*`（`PacketBufferUtils` 提供公共读写工具）：**动画同步（AnimationMessage）、实体属性同步（PropertiesMessage）、客户端 tick 速率（SyncClientTickRateMessage）、唱片机跳舞（DanceJukeboxMessage）**；工具方法 `sendMSGToServer/sendMSGToAll/sendNonLocal`（`Citadel.java:122-134`）。
- 数据驱动：`config/biome/SpawnBiomeConfig.java:30` `create(ResourceLocation fileName, SpawnBiomeData default)` —— 使用方只给"命名空间+文件名+默认值"，Citadel 负责在 `FMLPaths.CONFIGDIR/<ns>/<name>.json` 生成/读取（`getOrCreateConfigFile`，Gson + 自定义 `SpawnBiomeData.Deserializer`）；`BiomeEntryType` 支持按群系/tag/列表匹配。`recipe/SpecialRecipeInGuideBook.java` 是配方展示用的辅助实现。
- 配置：`citadel-common.toml`（ConfigHolder.SERVER_SPEC）。
- datagen：**无**（无 `GatherDataEvent`，src 仅 `src/main`；resources 只含 `assets/citadel/{book,patreon.txt,backup_text.txt}` 与 mixin 配置）。

## 6. Mixin
配置 `src/main/resources/citadel.mixins.json`：**10 个主 mixin**（BiomeSource、ChunkGenerator、ChunkStatus、Level、LivingEntity、MinecraftServer、MultiNoiseBiomeSource、NoiseBasedChunkGenerator、ServerLevel、SmithingMenu）+ **8 个 client**（AbstractClientPlayer、ClientLevel、HumanoidModel、ItemBlockRenderTypes、LevelRenderer、LivingEntityRenderer、SoundEngine、TitleScreen），`injectors.defaultRequire=1`。代表 hook：
- `mixin/MinecraftServerMixin` / `ServerLevelMixin` 注入 tick 流程驱动 `TickRateTracker`；
- `mixin/client/LevelRendererMixin.java:34/40/46` 注入 `initOutline()`/`resize(II)`/`renderLevel(...)`（自定义 shader/渲染层）、:77/:92 用 `@Redirect`；
- `mixin/client/HumanoidModelMixin.java:26/36` 注入 `poseRightArm`/`poseLeftArm` HEAD cancellable（给玩家自定义手臂姿态）；
- `mixin/SmithingMenuMixin.java:21` `@Redirect`；`client/ClientLevelMixin.java:33` 注入 `getStarBrightness(F)F`。所有注入统一带 `remap = CitadelConstants.REMAPREFS`。

## 7. 值得学的 5 条做法
1. **动画同步只发一个 int**：`AnimationHandler.sendAnimationMessage` 发 `indexOf(entity.getAnimations(), anim)`，用"实体 id + 索引"同步任意长动画，零自定义序列化成本。`animation/AnimationHandler.java:23-29`。
2. **把跨 mod 的 worldgen 注入集中成静态表 + 单点 mixin**：`SurfaceRulesManager` 避免"每个 mod 各混一处 chunk generator"的冲突。`server/generation/SurfaceRulesManager.java`。
3. **为使用者预置 JSON 配置文件**：`SpawnBiomeConfig.create(...)` 让接入方一行代码得到"缺省+可手改+可热重载"的配置文件。`config/biome/SpawnBiomeConfig.java:30`。
4. **枚举单例 + 静态 channel**：`AnimationHandler.INSTANCE`、`TabulaModelHandler.INSTANCE`、`NETWORK_WRAPPER` 静态常量，外部 mod 无需实例即可调用（前置库应尽量少状态）。
5. **可变 tick 速率抽象**：`TickRateModifier` 抽象类 + 4 种作用域 + `toTag/fromTag`，实现了"局部时间流速"这种通常要做一大堆硬编码的特效（配合 `IModifiesTime`）。`server/tick/`。

## 8. 公开 API / 扩展点（外部 mod 接入方式）
- `com.github.alexthe666.citadel.animation`：`IAnimatedEntity`（实体实现 5 个方法即可获得动画）、`Animation.create(int duration)`、`AnimationHandler.INSTANCE.updateAnimations(entity)`（在 entity.tick 调用）、`AnimationEvent.Start/Tick`（Forge 总线可取消）、`IScaleable`、`LegSolverQuadruped`。
- `com.github.alexthe666.citadel.client.model`：`TabulaModelHandler.INSTANCE.addDomain("yourmod")` + `loadTabulaModel(path)`；`AdvancedEntityModel`/`AdvancedModelBox`/`ITabulaModelAnimator`/`ModelAnimator`。
- `com.github.alexthe666.citadel.config.biome`：`SpawnBiomeConfig.create(fileName, SpawnBiomeData)`、`SpawnBiomeData`/`BiomeEntryType`。
- `com.github.alexthe666.citadel.server.generation`：`SurfaceRulesManager.registerOverworld/Nether/End/CaveSurfaceRule(...)`、`VillageHouseManager`、`SpawnProbabilityModifier`。
- `com.github.alexthe666.citadel.server.entity`：`ICitadelDataEntity` + `CitadelEntityData.getOrCreateCitadelTag(LivingEntity)`、`IModifiesTime`、`IComandableMob`、`IDancesToJukebox`。
- `com.github.alexthe666.citadel.server.tick`：`TickRateModifier`/`TickRateModifierType`/`ServerTickRateTracker`。
- `com.github.alexthe666.citadel.client.render`：`LightningBoltData` + `LightningRender`（可复用闪电特效）；`client/texture`：`CitadelTextureManager`/`ColorMappedTexture`。
- 典型接入顺序：mods.toml 声明 `citadel` 依赖 → 实体 implements `IAnimatedEntity` → `client/model` 里 `addDomain` → 需要世界生成/群系配置时调用 `SurfaceRulesManager`/`SpawnBiomeConfig`。

> 补充：本仓库快照为 1.19.3，若目标平台是 1.20.1 请参照 `_bulk/AlexModGuy__AlexsMobs` 的 `curse.maven:citadel-331936` 依赖版本；另 `_bulk` 内还有 `Raguto__Citadel-1.21.1` 可作为 1.21.1 移植参考。
