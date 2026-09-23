# yungnickyoung/YUNGs-Better-End-Island 源码分析

> 本地路径 `源码库\_参考仓库\_bulk\yungnickyoung__YUNGs-Better-End-Island`，报告内文件路径均相对于该仓库根。

## 1. 基本信息

- Mod 名：YUNG's Better End Island；mod_id `betterendisland`；作者 YUNGNICKYOUNG（credits: Acarii）；许可 LGPLv3；版本 4.1.0。
- 目标：MC `26.1.2`（`[26.1,)`）、Java 25；NeoForge `26.1.2.75`、Fabric loader `0.18.6` + fabric-api `0.150.0`；ClothConfig `26.1.154`、ModMenu `18.0.0-beta.1`。
- Gradle：Common/Fabric/NeoForge 三项目；插件 fabric-loom 1.15.5、NeoForge moddev 2.0.141、curseforgegradle、minotaur；共享 `buildSrc` 的 multiloader 约定。
- 关键依赖：**YUNG's API `6.1.1`**（`gradle.properties:39`，`NeoForge/build.gradle` implementation / Common compileOnly）。

## 2. 源码规模与包结构

- `find . -name '*.java' | wc -l` = **47**，总行数 **2911**；Common 35 / Fabric 7 / NeoForge 5。
- 包（Common）：`mixin` 11（+`mixin.accessor` 1）、`world` 6、`world.util` 4、`world.feature` 4、`world.processor` 3、`module` 4、`services` 3、`command` 1。
- 最大文件：`mixin/EnderDragonFightMixin.java` **602**、`world/BetterDragonRespawnStage.java` 243、`world/feature/BetterSpikeFeature.java` 151、`world/processor/BlockReplaceProcessor.java` 150、`world/util/EndSpikeUtils.java` 134、`world/feature/BetterEndPodiumFeature.java` 125、`world/util/ExitPortalUtils.java` 117、`mixin/ServerLevelMixin.java` 115。
- 本地仅落地了 `betterendisland.mixins.json` 与 `neoforge.mods.toml`，其余资源（lang、41 个 nbt、tags）由 `git ls-files` 确认存在。

## 3. 入口与注册

- `Common/.../BetterEndIslandCommon.java:20-26`：同样是 YUNGs-API 的注解注册路线（无 DeferredRegister），并缓存兼容性开关：

```java
public static void init() {
    YungAutoRegister.scanPackageForAnnotations("com.yungnickyoung.minecraft.betterendisland.module");
    Services.MODULES.loadModules();
    betterEnd = Services.PLATFORM.isModLoaded("betterend");
    endergetic = Services.PLATFORM.isModLoaded("endergetic");
    moreDragonEggs = Services.PLATFORM.isModLoaded("moredragoneggs");
}
```

- 平台入口：`BetterEndIslandFabric implements ModInitializer`、`@Mod BetterEndIslandNeoForge`（构造器再调 `ConfigModuleNeoForge.init(container)`）。
- 注册内容：`module/StructureProcessorTypeModule.java` 3 个处理器类型（block_replace / obsidian / dragon_egg）、`module/CommandModule.java` 用 `AutoRegisterCommand.of(EndIslandCommand::register)` 注册 `/end_island reset [forceNewPortalPos]`。

## 4. 核心系统

1. **末地龙战全面接管** `mixin/EnderDragonFightMixin.java`（`@Mixin(EnderDragonFight)`，implements `IBetterDragonFight`）：`@Inject(method="tick", at=HEAD, cancellable=true)` 整段重写原版 tick（:140-201），靠 `@Shadow` 取私有字段（`gateways`/`respawnCrystals`/`aliveCrystals`…），新增状态统一用 `@Unique` + `bei$` 前缀（`bei$dragonRespawnStage`、`bei$hasDragonEverSpawned`、`bei$numTimesDragonKilled`、`bei$isFirstExitPortalSpawn`，:107-110）。原版方法被替换的模式很明确：`tryRespawn`（:387）、`respawnDragon`（:449）、`setDragonKilled`（:474）、`onCrystalDestroyed`（:360）全部 HEAD 注入 + `ci.cancel()` 自己实现；另用 `accessor.EnderDragonFightAccessor` 暴露 `exitPortalLocation`、`invokeCreateNewDragon`、`getGateways`。
2. **重生阶段状态机** `world/BetterDragonRespawnStage.java`：`enum implements StringRepresentable`，`START → PREPARING_TO_SUMMON_PILLARS(100t 龙吼) → SUMMONING_PILLARS(每柱 40t：爆炸特效 + 清除非 END_STONE 方块 + 重新 `Feature.END_SPIKE.place`) → SUMMONING_DRAGON(100t) → END`；抽象 `tick(ServerLevel, EnderDragonFight, List<EndCrystal>, phaseTimer)` + `onStart` 钩子；`advanceRespawnStage` 由 mixin 侧实现（:522-529）。END 阶段随机把 obsidian 变 crying obsidian，概率按击杀次数 `Mth.lerp(kills/10f, 0f, 0.5f)`（:176-199）。
3. **首次进岛才召唤龙** `mixin/ServerLevelMixin.java:87-112`：`tick` HEAD 每 5 tick 检查非旁观者玩家是否距 (0,0) 中心 <25 格，满足则 `doInitialDragonSpawn()`；同时驱动 `tickBellSound()`（每 100 tick 钟声）。
4. **自定义柱/结构模板替换** `world/feature/BetterSpikeFeature.java`：Guava `LoadingCache`（5 分钟过期）按 seed 生成柱位（`SpikeCacheLoader`：半径 54、10 根、`2+index/3` 粗细）；模板名 `pillar_{initial|guarded|broken}_{h}` + `pillar_bottom_{h}`，`Rotation` 由 `seed ^ centerX ^ centerZ` 决定以保证每场战斗一致（:79-82）；`StructurePlaceSettings` 挂 `BlockReplaceProcessor`（terracotta/concrete → obsidian/crying obsidian）与 `ObsidianProcessor(numberTimesDragonKilled)`。
5. **战斗进度写进 level.dat**：`world/ExtraFightData.java`（`RecordCodecBuilder` Codec，字段 `FirstExitPortalSpawn`/`HasDragonEverSpawned`/`NumberTimesDragonKilled`）+ `mixin/PrimaryLevelDataMixin.java`（`parse` RETURN 读 `bei_ExtraDragonFight`、`setTagData` RETURN 写回）+ `mixin/ServerLevelMixin.java:61-85`（`<init>` RETURN 灌回 dragonFight，`saveLevelData` HEAD 收集并回写）。
6. **原版生成器可开关替换**：`EndSpikeFeatureMixin`（`getSpikesForLevel`/`placeSpike` HEAD cancellable → 转发到 `BetterSpikeFeature`）、`EndPlatformFeatureMixin`、`EndGatewayFeatureMixin`、`TheEndGatewayBlockEntityMixin`（`findTallestBlock`/`findValidSpawnInChunk`），配合 `ConfigModule` 的 `useVanillaSpawnPlatform`/`useVanillaEndGateways`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无自定义包，全部靠原版机制与 mixin。
- **数据驱动**：41 个 `data/betterendisland/structure/*.nbt`（gateway、pillar_*）；tags：`betterendisland:end_gateway_cannot_place_player_on`、覆盖 `minecraft:dragon_immune`。无 worldgen JSON（末地生成全在代码里）。
- **配置**：NeoForge `ModConfigSpec`（`config/BEIConfigNeoForge.java`，6 个布尔）+ Fabric ClothConfig `AutoConfig`；`module/ConfigModule.java` 是平台无关的 6 个默认值镜像，供 mixin 内直接读。
- **datagen**：无（未见 `src/generated`、DataProvider）。

## 6. Mixin

`Common/src/main/resources/betterendisland.mixins.json`（`mixinPriority: 500`、`defaultRequire: 1`）：`EnderDragonFightMixin`、`EndergeticExpansionMixins`（`@Mixin(value=ServerLevel.class, priority=2000)`，第三方兼容）、`EndGatewayFeatureMixin`、`EndPlatformFeatureMixin`、`EndSpikeMixin`（`<init>` RETURN / `getHeight` HEAD）、`PrimaryLevelDataMixin`、`ServerLevelMixin`、`EndSpikeFeatureMixin`、`TheEndGatewayBlockEntityMixin`、`accessor.EnderDragonFightAccessor`。

## 7. 值得学的 5 条具体做法

1. 接管原版 boss 逻辑时把“状态机”抽成 enum（`world/BetterDragonRespawnStage.java`），mixin 只负责保存/推进状态与快照——602 行的 mixin 因此仍然可读。
2. `@Unique` 字段统一加 mod 前缀（`bei$`）避免与其它 mixin 冲突（`mixin/EnderDragonFightMixin.java:107-110`）。
3. 能拿私有成员时优先 `@Shadow`，需要调用/改写入参外的私有方法才建 accessor（`mixin/accessor/EnderDragonFightAccessor.java`）。
4. 世界生成数据（柱位列表）用 Guava `LoadingCache` + `CacheLoader` 缓存，5 分钟过期（`world/feature/BetterSpikeFeature.java:43-46`）。
5. 需要跨存档持久的进度不要另建 SavedData，直接塞进 `level.dat`：`Codec` + `PrimaryLevelDataMixin` 读写（`mixin/PrimaryLevelDataMixin.java:28-44`）。
