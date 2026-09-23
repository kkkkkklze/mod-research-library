# YUNG-GANG/YUNGs-Better-Mineshafts 源码分析报告

本地路径：`...\_bulk\YUNG-GANG__YUNGs-Better-Mineshafts`（下文路径相对仓库根）

## 1. 基本信息

YUNG's Better Mineshafts / mod_id `bettermineshafts` / 作者 YUNGNICKYOUNG / 版本 6.1.1 / 许可证 LGPLv3（`gradle.properties:1-11`）。
目标：MC `26.1.2`（`mc_version_range=[26.1,)`），Java 25；**双加载器**：Fabric（loom 1.15.5、fabric 0.150.0、loader 0.18.6、Cloth Config 26.1.154、ModMenu 18.0.0-beta.1）+ NeoForge（moddev 2.0.141、neoforge 26.1.2.75）。
第三方 API：**YungsApi 6.1.3**（`yungsapi_version`），Common 里 `compileOnly("com.yungnickyoung.minecraft.yungsapi:YungsApi:...")`（`Common/build.gradle:19-25`）；还 compileOnly mixin 0.8.5 与 mixinextras-common 0.5.3。
Gradle 结构：根 `build.gradle` 只声明插件与发布任务，`buildSrc/src/main/groovy/multiloader-common.gradle`、`multiloader-loader.gradle` 提供约定；Common 用 `commonJava/commonResources/commonGeneratedResources` configuration + 自定义 loader attribute 供子工程消费（`Common/build.gradle:28-70`）。

## 2. 规模与包结构

41 个 `.java` / 4457 行（Common 27、Fabric 7、NeoForge 7）。包：`world.generator.pieces` 11、`world.generator` 1、`world.config` 1、`mixin` 4、`module` 3、`services` 3（+ 各加载器镜像包）。
最大文件：`.../pieces/BigTunnel.java` 801、`pieces/BetterMineshaftPiece.java` 600、`pieces/VerticalEntrance.java` 360、`pieces/SmallTunnel.java` 266、`pieces/SideRoom.java` 185、`pieces/LayeredIntersection4.java` 172、`pieces/ZombieVillagerRoom.java` 170、`world/config/BetterMineshaftConfiguration.java` 165、`generator/BetterMineshaftGenerator.java` 134。
本副本资源被裁剪：Common 只有 `bettermineshafts.mixins.json`，NeoForge 只有 `META-INF/neoforge.mods.toml`，datapack JSON（structure/tag）不在快照内。

## 3. 入口与注册

- NeoForge：`NeoForge/src/main/java/.../BetterMineshaftsNeoForge.java`，`@Mod(BetterMineshaftsCommon.MOD_ID)`，构造器 `(IEventBus eventBus, ModContainer container)`：`BetterMineshaftsCommon.init(); ConfigModuleNeoForge.init(container);`（同时把 eventBus 存静态字段供配置模块加监听）。
- Fabric：`Fabric/.../BetterMineshaftsFabric.java` 实现 `ModInitializer`，只调 `BetterMineshaftsCommon.init()`。
- Common 入口 `Common/src/main/java/.../BetterMineshaftsCommon.java`：

```java
YungAutoRegister.scanPackageForAnnotations("com.yungnickyoung.minecraft.bettermineshafts.module");
Services.MODULES.loadModules();
LocateReplacer.register(BuiltinStructures.MINESHAFT,
    TagKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath(MOD_ID, "better_mineshafts")),
    () -> CONFIG.disableVanillaMineshafts);
```

- 注册框架：**无 DeferredRegister**，用 YungsApi 的注解注册器 `@AutoRegister`：`module/StructureTypeModule.java`（`@AutoRegister("mineshaft") public static StructureType<BetterMineshaftStructure> BETTER_MINESHAFT = () -> BetterMineshaftStructure.CODEC;`）与 `module/StructurePieceTypeModule.java`（11 个 `StructurePieceType`，id 形如 `bmsbigtunnel`、`bmsverticalentrance`）。
- 跨加载器解耦：`services/Services.java` 用 `ServiceLoader.load(IPlatformHelper/IModulesLoader)`，两个加载器各提供 `FabricModulesLoader`/`NeoForgeModulesLoader` 与 `*PlatformHelper`。

## 4. 核心系统

1. **结构主体** `world/BetterMineshaftStructure.java`：`MapCodec` = `settingsCodec(builder)` + `BetterMineshaftConfiguration.CODEC.fieldOf("config")`；`findGenerationPoint` 在 `[CONFIG.minY, CONFIG.maxY]` 随机取 y，用 `WorldgenRandom(new LegacyRandomSource(0)) + setLargeFeatureSeed` 定起始朝向，`VerticalEntrance(-1, pos, direction, config, heightAccessor.getMaxY())` 作为入口并 `addChildren` 递归生成全图。
2. **数据驱动的结构配置** `world/config/BetterMineshaftConfiguration.java`：`replacementRate / legVariant / decorationChances / blockStates / blockStateRandomizers` 全为 Codec 字段（`BlockStateRandomizer` 来自 YungsApi），即结构行为由 datapack JSON 决定；piece 侧 `BetterMineshaftPiece.addAdditionalSaveData` 把同一份配置逐字段写 NBT（block id 用 `Block.BLOCK_STATE_REGISTRY.getId`，随机器 `saveTag()`），构造函数再反向读回，保证存档重载一致。
3. **Piece 图生成** `world/generator/BetterMineshaftGenerator.java`：全是静态工厂 `generateAndAddBigTunnelPiece/generateAndAddSmallTunnelPiece/generateAndAddSideRoomPiece/...`，大隧道 `chainLength > 3` 即停；小隧道按 `randomSource.nextInt(100)` 阈值 90/80/70/60 依次尝试 LayeredIntersection4 → SmallTunnelStairs → SmallTunnelTurn → LayeredIntersection5 → SmallTunnel，链尾按 `zombieVillagerRoomSpawnRate` 放僵尸村民房或 `OreDeposit`；每步 `structurePieceAccessor.addPiece(newPiece); newPiece.addChildren(...)`——**两阶段：先建图（不落方块），`generate` 时才写方块**（`BetterMineshaftPiece.addChildren` 基类为空实现）。
4. **Piece 局部坐标与状态** `pieces/BigTunnel.java`：常量 `SECONDARY_AXIS_LEN=9 / Y_AXIS_LEN=8 / MAIN_AXIS_LEN=24` 与 `LOCAL_X_END/LOCAL_Y_END/LOCAL_Z_END`，用 `List<BlockPos> smallShaftLeftEntrances / smallShaftRightEntrances`、`List<BoundingBox> sideRoomEntrances`、`List<Integer> bigSupports / smallSupports`、`List<Pair<Integer,Integer>> gravelDeposits` 记录连接点，每个列表都有对应的 NBT 读写。
5. **通用生成工具** `BetterMineshaftPiece`：`addBarrel(world, bbox, random, pos, ResourceKey<LootTable>)`（放桶并 `setLootTable`）、`BlockBehaviourAccessor.callCanSurvive` 判断植物/藤蔓可放置、`BetterMineshaftsCommon.DEBUG_LOG` 与 `surfaceEntrances`/`count` 用于调试计数。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯世界生成 mod，无自定义包/通道）。
- 数据驱动：结构配置走 datapack Codec（见 4.2）；结构本身靠 `structure`/`structure_set` JSON 与 `LocateReplacer` 注册的 `bettermineshafts:better_mineshafts` tag（本副本缺这些 JSON）。
- 配置：Common 侧 `module/ConfigModule.java` 是**纯 POJO**（`disableVanillaMineshafts=true`、`minY=-55`、`maxY=30`、`Ores`（cobble 50/coal 20/iron 9/redstone 7/gold 7/lapis 3/emerald 3/diamond 1）、`SpawnRates`（lantern 0.0067、torch 0.02、workstation 0.025、`zombieVillagerRoomSpawnRate=2`、`smallShaftPieceChainLength=9` 等））；加载器侧 `ConfigOresNeoForge` 等用 `ModConfigSpec`（大量 `worldRestart()` + `defineInRange`），`ConfigModuleNeoForge.bakeConfig()` 把 spec 值拷进 Common POJO，并在 `LevelEvent.Load` 与 `ModConfigEvent` 时重新 bake。
- datagen：**无**（无 GatherDataEvent/DataGenerator 代码）。

## 6. Mixin

配置 `Common/src/main/resources/bettermineshafts.mixins.json`（`required=true`、`compatibilityLevel=JAVA_17`、`defaultRequire=1`），4 个 mixin（纯 common，双加载器共用）：
- `mixin/DisableVanillaMineshaftsMixin.java`：`@Mixin(ChunkGenerator.class)`，`@Inject(method="tryGenerateStructure", at=@At("HEAD"), cancellable=true)`，条件 `CONFIG.disableVanillaMineshafts && structureSetEntry.structure().value().type() == StructureType.MINESHAFT` 时 `cir.setReturnValue(false)`——从根上关掉原版矿井。
- `mixin/SuppressLogMixin.java`：`@Mixin(Util.class)`，`@Inject(method="logAndPauseIfInIde(Ljava/lang/String;)V", at=@At("HEAD"), cancellable=true, require=0)` 屏蔽 "Detected setBlock in a far chunk" + `bettermineshafts:mineshaft` 日志（`require=0` 容忍目标方法被改名）。
- `mixin/BlockBehaviourAccessor.java`：`@Invoker boolean callCanSurvive(...)`；`mixin/BoundingBoxAccessor.java`：`@Accessor("minX") void setMinX(int)` 等 6 个 setter，用于调整 AABB 范围。

## 7. 值得学的 5 条做法

1. 多加载器"Common + services ServiceLoader"三工程结构（`Common/services/Services.java`、`NeoForge/.../NeoForgeModulesLoader.java`），公共逻辑 100% 放 Common，加载器工程只做绑定。适用：你需要同时上 Fabric/NeoForge 的任何 mod。
2. 配置 POJO + spec bake（`module/ConfigModuleNeoForge.bakeConfig()`）：worldgen 代码只读普通字段，不碰 ModConfigSpec，双加载器共用同一份读取代码。
3. 结构 piece 的"先建图后落方块"（`BetterMineshaftGenerator` 与 `BetterMineshaftPiece.addChildren`）：`addChildren` 只调 `addPiece` 并记连接点，方块在 `generate` 阶段才写，便于整体裁剪与调试。
4. 用 `chainLength` + 权重阈值控制链条长度与分支类型（`BetterMineshaftGenerator.generateAndAddSmallTunnelPiece`：`if (chainLength > ... - 2) return` 之类的护栏），保证结构必然终止。
5. 用 mixin 而非 datapack 关原版结构（`DisableVanillaMineshaftsMixin` + YungsApi `LocateReplacer`），并用 `SuppressLogMixin` 的 `require=0` 抑制大规模 setBlock 的告警日志。

## 8. API

非库模组，无对外 API 包；扩展点仅在 YungsApi（`@AutoRegister`、`BlockStateRandomizer`、`LocateReplacer`、`BoundingBoxHelper`），本 mod 是 YungsApi 的**消费者**而非提供者。
