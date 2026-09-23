# YUNG-GANG/YUNGs-Better-Desert-Temples 源码分析

> 本地路径 `源码库\_参考仓库\_bulk\YUNG-GANG__YUNGs-Better-Desert-Temples`，报告内文件路径均相对于该仓库根。

## 1. 基本信息

- Mod 名：YUNG's Better Desert Temples；mod_id `betterdeserttemples`；作者 YUNGNICKYOUNG（credits: Tera）；许可 LGPLv3；版本 5.1.1。
- 目标：MC `26.1.2`（`mc_version_range=[26.1,)`）、Java 25；NeoForge `26.1.2.75`（loader ≥4）、Fabric loader `0.18.6` + fabric-api `0.150.0`；Fabric 侧依赖 ClothConfig `26.1.154`、软依赖 ModMenu `18.0.0-beta.1`。
- Gradle：`settings.gradle` 分 `Common/Fabric/NeoForge` 三子项目；插件 fabric-loom 1.15.5、NeoForge moddev 2.0.141、curseforgegradle、minotaur（`build.gradle:1-10`），共用 `buildSrc/src/main/groovy/multiloader-{common,loader}.gradle`。
- 关键依赖：**YUNG's API `6.1.3`**（`gradle.properties:39`，NeoForge `implementation`、Common `compileOnly`，见 `NeoForge/build.gradle:13`）。无其他前置 mod。

## 2. 源码规模与包结构

- `find . -name '*.java' | wc -l` = **69**，总行数 **3771**；Common 48 个 / Fabric 11 / NeoForge 10。
- 主要包（第 3 层，Common）：`world.processor` 30、`world`+`world.state`+`world.placement` 6、`module` 4、`services` 4、`mixin`(+`mixin.pharaoh`/`accessor`) 8、`util` 1。
- 最大文件：`NeoForge/.../module/ConfigModuleNeoForge.java` 204、`Fabric/.../module/ConfigModuleFabric.java` 200、`world/processor/RedBannerProcessor.java` 197、`LimeBannerProcessor.java` 180、`util/PharaohUtil.java` 122、`world/ArmorStandChances.java` 110、`world/state/TempleStateRegion.java` 106。
- 注意：本地检出只落地了部分资源（`Common/src/main/resources` 仅 `betterdeserttemples.mixins.json`），其余资源经 `git ls-files` 确认存在。

## 3. 入口与注册

- 公共入口 `Common/src/main/java/com/yungnickyoung/minecraft/betterdeserttemples/BetterDesertTemplesCommon.java:22-28`；Fabric 由 `BetterDesertTemplesFabric`（ModInitializer）、NeoForge 由 `@Mod BetterDesertTemplesNeoForge:12-17` 调用，NeoForge 构造器额外调用 `ConfigModuleNeoForge.init(container)`。

```java
public static void init() {
    YungAutoRegister.scanPackageForAnnotations("com.yungnickyoung.minecraft.betterdeserttemples.module");
    Services.MODULES.loadModules();
    LocateReplacer.register(BuiltinStructures.DESERT_PYRAMID,
            ResourceKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath(MOD_ID, "desert_temple")),
            () -> CONFIG.general.disableVanillaPyramids);
}
```

- **不使用 DeferredRegister/Registrate**：全部走 YUNGs-API 的 `@AutoRegister` 注解（类级=modId，字段级=注册名）。`module/StructureProcessorModule.java` 注册 **25 个 `StructureProcessorType`**，`StructurePlacementTypeModule` 注册自定义 placement，`TagModule` 只是 `TagKey` 常量。`IProcessorProvider`/`IModulesLoader`/`IPlatformHelper` 通过 `ServiceLoader` 由 loader 模块实现（`services/Services.java`）。

## 4. 核心系统

1. **自定义结构放置（避开水/河）** `world/placement/BetterDesertTemplePlacement.java`：继承 `RandomSpreadStructurePlacement`，重写 `isPlacementChunk`，用 `biomeSource.findBiomeHorizontal(pos, 48, 2, holder -> IS_RIVER||IS_OCEAN, ...) != null` 否决候选点；BiomeSource 经 accessor 取得（`mixin/accessor/ChunkGeneratorStructureStateAccessor`）。CODEC 用 `RecordCodecBuilder` 复刻原版字段（salt/spacing/separation…）。
2. **“神殿是否已清”持久化** `world/state/TempleStateCache.java` + `TempleStateRegion.java`：按 region（`r.X.Z.temples`）分文件，`NbtIo.write/read` 存 `CompoundTag`，`ConcurrentHashMap<Long,Boolean>` 内存缓存，方法 `synchronized`；`mixin/ServerLevelMixin.java:40-56` 在 `ServerLevel.<init>` 的 RETURN 处用 `levelStorage.getDimensionPath(dimension)` 建缓存，并让 ServerLevel 实现 `ITempleStateCacheProvider`。
3. **法老识别与击杀解锁** `util/PharaohUtil.java`：`isPharaoh` 不看自定义实体，而是查 Husk 的 `PLAYER_HEAD` 部件 `DataComponents.PROFILE` 里 `textures` 属性是否等于常量 base64（:33,:60-65）；生成期另有基于 `CompoundTag`/`ArmorItems[3]` 的重载（:46-58）。死亡/移除时 `mixin/pharaoh/LivingEntityMixin.java:27`（`die` HEAD）、`EntityMixin.java:24`（`discard` HEAD）触发 `onKillOrDiscardPharaoh`：置位 cleared、给殿内玩家发 `BEACON_DEACTIVATE` 音效并 `removeEffect(MINING_FATIGUE)`。
4. **挖掘疲劳机制** `mixin/ServerPlayerTickMixin.java:45-69`：`@Inject(method="tick", at=HEAD)`，每 100 tick 检查 `structureManager().getStructureWithPieceAt(pos, TagModule.APPLIES_MINING_FATIGUE)`；未清理时发 `ELDER_GUARDIAN_CURSE` 音效并施加 600 tick、amplifier 2 的 `MINING_FATIGUE`。
5. **法老坐标随实体走**：`entity/IPharaohData` + `mixin/pharaoh/HuskMixin`（`@Unique Vec3 bdtOriginalSpawnPos`）与 `ZombieMixin`（`readAdditionalSaveData` RETURN / `addAdditionalSaveData` HEAD 读写 NBT key `bdtOriginalSpawnPos`），使“多神殿 + 灵魂出窍”也能正确判定归属。
6. **结构处理器族** `world/processor/*`（30 个）：多数是无状态替换/随机化（如 `RedBannerProcessor`、`YellowWoolProcessor`）；`ArmorStandProcessor`/`ItemFrameProcessor`/`PharaohProcessor` 因需 loader 特有 API，Common 只留类型，`IProcessorProvider` 由 `Fabric/NeoForgeProcessorProvider` 提供 CODEC。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无自定义包（未发现 `PayloadRegistrar`/`ClientboundCustomPayloadPacket` 类）；同步靠原版包（`ClientboundSoundPacket`、`MobEffectInstance`）与结构生成。
- **数据驱动**：198 个 `data/betterdeserttemples/structure/**.nbt`、28 个 `worldgen/template_pool/*.json`、1 个 `structure_set`、1 个 `structure`、1 个 `processor_list`（`main.json`）、10 个 loot_table、3 个 advancement、2 个 structure tag（含 `applies_mining_fatigue`）、biome tag。
- **配置**：双轨。（a）平台配置包住 `module/ConfigModule.General`（`disableVanillaPyramids`、`applyMiningFatigue`）——NeoForge 用 `ModConfigSpec` 注册 COMMON 配置 `neoforge-26_1.toml`，Fabric 用 ClothConfig `AutoConfig.register(..., Toml4jConfigSerializer::new)`，并在 `ConfigChange`/`LevelEvent.Load` 重新 bake（`NeoForge/.../ConfigModuleNeoForge.java:24-35`）。（b）自定义 JSON 目录 `config/betterdeserttemples/{neoforge-26_1|fabric-26_1}`，把 `ArmorStandChances`/`ItemFrameChances`（单例 + `ItemRandomizer`）序列化，缺文件时写默认值并附 README。
- **datagen**：NeoForge `build.gradle` 有 `data` run 配置与 `sourceSets.main.resources { srcDir 'src/generated/resources' }`，但仓库内无 `src/generated/resources` 文件（资源为手写）。

## 6. Mixin

配置 `Common/src/main/resources/betterdeserttemples.mixins.json`（`required:true`、`defaultRequire:1`、JAVA_17）：`DisableVanillaPyramidsMixin`（`@Mixin(ChunkGenerator)`，`tryGenerateStructure` HEAD cancellable，用 `structureSetEntry.structure().value().type()==StructureType.DESERT_PYRAMID` 直接返回 false）、`ServerLevelMixin`、`ServerPlayerTickMixin`、`accessor.ChunkGeneratorStructureStateAccessor`（`@Accessor`）、`pharaoh.{EntityMixin,HuskMixin,LivingEntityMixin,ZombieMixin}`。

## 7. 值得学的 5 条做法

1. 关掉原版结构不要改结构集，而是注入 `ChunkGenerator#tryGenerateStructure` 头部返回 false，并由配置开关控制（`mixin/DisableVanillaPyramidsMixin.java:27-33`）——对其他数据包/结构 mod 最友好。
2. “每个结构一次性状态”用 region 分片文件 + `ConcurrentHashMap` 懒加载（`world/state/TempleStateRegion.java:28-70`）——比重写整张 SavedData 简单，且按需读盘。
3. 用头颅 profile 的 `textures` base64 认“特殊怪”（`util/PharaohUtil.java:33`），既不需要新实体，也能在结构处理器阶段通过 NBT 版本识别。
4. 实体的附加字段用 mixin `@Unique` 字段 + 读写 NBT 两个 hook 持久化（`mixin/pharaoh/HuskMixin.java`、`ZombieMixin.java:21-33`），比注册自定义实体/DataComponent 便宜。
5. 只在真正需要 loader API 的地方引入 `ServiceLoader` 抽象（`services/IProcessorProvider.java` + 各 loader 实现），其余全部放 Common。
