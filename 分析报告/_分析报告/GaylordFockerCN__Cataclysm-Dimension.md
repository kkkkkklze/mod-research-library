# GaylordFockerCN/Cataclysm-Dimension（灾变维度）源码分析

## 1. 基本信息

- Mod 名：Cataclysm Dimension；mod_id `cataclysm_dimension`；作者 P1nero、WonderfulAiChen；版本 1.7.0
- 目标：MC 1.21.1 + NeoForge 21.1.185（`gradle.properties`），Java 21，Parchment 2024.11.17
- Gradle：NeoForge ModDevGradle `net.neoforged.moddev 2.0.95`（无 MixinGradle），`mods.toml` 由 `src/main/templates` + `generateModMetadata` 任务展开
- 许可证：All Rights Reserved
- 编译依赖（`build.gradle:106-113`，均来自 cursemaven）：`lendercataclysm`（灾变本体，被依赖的 API）、`lionfish-api`（其前置库）、`curios`、`cupboard`、`structure-essentials`。**它是"围栏 mod"：不改灾变源码，只补维度与流程**

## 2. 源码规模与包结构

- 14 个 `.java`，共 1865 行（`find . -name '*.java' -exec wc -l {} +`）；仓库被 sparse checkout，未检出的资源需 `git show HEAD:<path>` 读取
- 包结构（第 3 层）：`com.p1nero.cataclysm_dimension`(2)、`.client`(2)、`.entity`(2)、`.worldgen`(4)、`.worldgen.placements`(2)
- 最大文件：`CataclysmDimensionMod.java`(663) > `worldgen/CataclysmDimensions.java`(303) > `worldgen/CDNoiseSettings.java`(253) > `CataclysmDimensionModConfig.java`(171) > `worldgen/CDSurfaceRuleData.java`(166) > `entity/ReturnRiftEntity.java`(96)
- 资源：`assets/cataclysm_dimension/lang/{en_us,zh_cn}.json`、`packs/`（6 个内置数据包、109 个 json）、`cataclysm_dimension.mixins.json`、`META-INF/accesstransformer.cfg`（共 143 个受版本控制文件）

## 3. 入口与注册

主类 `src/main/java/com/p1nero/cataclysm_dimension/CataclysmDimensionMod.java:85`，构造签名 `(ModContainer, IEventBus)`，注册集中在一处：

```java
CDPlacementTypes.STRUCTURE_PLACEMENT_TYPES.register(bus);
CDEntities.ENTITY_TYPES.register(bus);
if (FMLEnvironment.dist.isClient()) CataclysmDimensionClient.init(bus);
```

- 用 `DeferredRegister`：`entity/CDEntities.java:12` 注册唯一实体 `return_rift`；`worldgen/placements/CDPlacementTypes.java:11` 注册自定义结构放置类型 `spawn_pos_placement`
- 客户端单独隔离在 `client/CataclysmDimensionClient.java`，由 `dist.isClient()` 分支调用（专用服务端不加载）
- GameEvent 全部用 `NeoForge.EVENT_BUS.addListener(this::xxx)` 方法引用式注册；`FMLCommonSetupEvent.enqueueWork` 里预建两张静态表，避免单人下懒初始化被双线程首触

## 4. 核心系统

**A. 眼睛传送**（`CataclysmDimensionMod.java:123-231`）。静态 `Map<Item, TeleportConfig>`，`record TeleportConfig(ResourceKey<Level> dimensionKey, int targetY, int effectDuration)`；用 `DimensionTransition` 跨维，落点固定 `(0, targetY, 0)`；前置条件 `isShiftKeyDown`、`ALLOW_USE_EYE_IN_DIMENSION`、600 tick 冷却，进入前把玩家坐标写进 `player.getPersistentData()`。

**B. 归返裂隙**（`entity/ReturnRiftEntity.java`）。MISC 实体，`updateInterval(Integer.MAX_VALUE)`、`fireImmune()`、`hurt()` 恒 false，右键 `CataclysmDimensionMod.teleportBack()` 送回 PersistentData 中 `cataclysm_dimension:return_point` 记录点，缺失则回主世界出生点；渲染 `client/ReturnRiftRenderer.java` 悬浮自旋对应眼睛物品，物品由 `getEyeItemFor(dimension)` 反查维度→眼睛映射。

**C. 结构地形重盖**（`CataclysmDimensionMod.java:365-601`）。用 `DIRTY_DIMS`+落盘 `cataclysm_dimension_dirty_dims.txt` 记"用过的维度"；玩家再进时排入 `PENDING_RESTORE_POS/DELAY`（延迟 40 tick 等区块加载），`restoreStructure()` 用 `StructureManager.getAllStructuresAt` 定位结构 → 逐区块 `start.placeInChunk(level, sm, generator, new WorldgenRandom(new LegacyRandomSource(level.getSeed())), chunkBox, cp)` 重放生成，只动已加载区块；`PURGE_STALE_RIFTS` + `EntityJoinLevelEvent.loadedFromDisk()` 拦截异步迟到的旧裂隙。

**D. 数据包开关式配置**（`CataclysmDimensionMod.java:640-661`）。用 `AddPackFindersEvent`（mod 总线、`EventPriority.HIGHEST`）把 jar 内 `packs/<name>`（`base_dimension`、`keep_original`/`not_keep_original`、`random_spread`/`random_spread_dim`、`disable_respawn`）按配置项动态挂载，`Pack.Position.TOP`；用于同一份结构在"留在原维度"与"搬进新维度"两套 worldgen JSON 间切换。

**E. 手工维度与世界生成**（`worldgen/CataclysmDimensions.java:97-303`、`CDNoiseSettings.java`）。8 套 DimensionType（逐一给 base 维度设时间/天空光/天花板/超高温/坐标缩放/海平面/环境光）+ `FixedBiomeSource` + `NoiseBasedChunkGenerator`；`CDNoiseSettings` 的 NoiseRouter 直接 `ResourceKey.create(Registries.DENSITY_FUNCTION, ResourceLocation.withDefaultNamespace("overworld/sloped_cheese"))` **复用原版密度函数**，AT 文件把 `NoiseRouterData.overworld/nether` 提权为 public。

**F. 自定义 StructurePlacement**（`worldgen/placements/SpawnPosPlacement.java`）。`RecordCodecBuilder.mapCodec(inst -> inst.stable(new SpawnPosPlacement()))` 做无参反序列化，`isPlacementChunk` 只在 `chunkX==0 && chunkZ==0` 返回 true —— 让 boss 结构确定性生成在出生点区块，配合"传送落点 (0,targetY,0)"使竞技场位置可预测。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（`grep -rn "payload|Payload|SimpleChannel"` 无命中），全部逻辑服务端本地执行
- 数据驱动：世界生成全走数据包（`packs/**`：dimension、dimension_type、worldgen/{noise_settings,noise,density_function,biome,structure,structure_set}、`cataclysm/tags/worldgen/biome/*`）；同时有 javacode 版 datagen（`worldgen/CDDataGenerators.java` + `CDWorldGenProvider` 的 `RegistrySetBuilder.add(DIMENSION_TYPE/NOISE_SETTINGS/BIOME/LEVEL_STEM)`），但 `CDBiomes.boostrap` 为空体，注释写明"复制粘贴现成数据包更方便"
- 配置：**未用** NeoForge `ModConfigSpec`，而是自写 Gson 配置 `config/cataclysm_dimension/cataclysm_dimension.json`（`CataclysmDimensionModConfig.java:67`），`DEFAULT_CONFIG` 表在加载时自动补齐缺失键并回写（含 11 个布尔开关）

## 6. Mixin

`src/main/resources/cataclysm_dimension.mixins.json` 存在但 `"mixins": []`、`"client": []` 均为空、无 `com.p1nero.cataclysm_dimension.mixin` 包 —— **实际零 mixin**，需要访问私有成员时走 AT（`accesstransformer.cfg` 仅 2 行，公开 `NoiseRouterData.overworld/nether`）。

## 7. 值得学的 5 条具体做法

1. **自定义 StructurePlacement 把结构钉死在 (0,0) 区块** —— `SpawnPosPlacement.java:24`；做"每维度一个固定 boss 场地"时用，避免 random_spread 导致的定位困难。
2. **内置多套数据包 + AddPackFindersEvent 按配置切换** —— `CataclysmDimensionMod.java:640`；同一 jar 提供 worldgen 的多种策略，不改文件即可换行为（对标 NeoForge 官方 dynamic pack 用法）。
3. **结构原地重放而不是重建维度** —— `restoreStructure` 的 `placeInChunk` 逐区块重放 + 新 `LegacyRandomSource(level.getSeed())`；做副本/竞技场"重开一局"时最省事的做法。
4. **`loadedFromDisk()` 过滤区分"新生成"与"从盘载入"的实体** —— `CataclysmDimensionMod.java:285`；需要清除世界残留实体但不想误伤新实体时的标准判据。
5. **NoiseRouter 复用原版密度函数 key** —— `CDNoiseSettings.java:214-226` + AT；自建维度想保留原版地形手感时，只换 sea level / slide 参数，不必搬整套 JSON。

## 8. 库/API 类 mod 扩展点

非库 mod。对外可复用点仅为注册项：实体 `cataclysm_dimension:return_rift`、放置类型 `cataclysm_dimension:spawn_pos_placement`、8 个维度 id，以及 11 个 Gson 布尔开关（`enable_return_rift`、`reset_structure_on_reentry`、`reset_structure_requires_boss_kill` 等）。
