# YUNG-GANG/YUNGs-API 源码分析报告

> 本地仓库 `源码库\_参考仓库\YUNGs-API`（shallow clone，仅 `1.21.1` 分支，HEAD `f7bf091` "v5.1.8"）

## 1. 基本信息

| 项 | 值 | 出处 |
|---|---|---|
| Mod 名 / mod_id | YUNG's API / `yungsapi`（archivesName `YungsApi`） | `gradle.properties:5-8` |
| 作者 | YUNGNICKYOUNG | `gradle.properties:9` |
| 版本 | 5.1.8 | `gradle.properties:2` |
| 目标 MC | 1.21.1；`mc_version_range=[1.21,1.22)`，`mc_version_range_fabric=>=1.21` | `gradle.properties:18-22` |
| Java | 21 | `gradle.properties:3` |
| 加载器 | Forge 52.0.17（loader `[51,)`）/ NeoForge 21.1.66（loader `[4,)`）/ Fabric loader 0.15.11 + Fabric API 0.102.0 | `gradle.properties:30-42` |
| Gradle 插件 | fabric-loom 1.10-SNAPSHOT、spongepowered.mixin 0.7-SNAPSHOT、spongepowered.gradle.vanilla 0.2.1（Common 子项目）`Common/build.gradle:3`、neoforged.gradle.userdev 7.0.181、curseforgegradle 1.1.24、minotaur 2.+、idea-ext | `build.gradle:1-7`、`NeoForge/build.gradle:1-6` |
| 许可证 | LGPLv3 | `LICENSE` |
| 编译依赖 | Common 仅 `compileOnly` mixin 0.8.5 / asm-tree 9.4 / jsr305 —— **零第三方 mod 依赖**；Fabric 侧 jar-in-jar 内嵌 `org.reflections:0.10.2` + `javassist:3.29.2-GA` | `Common/build.gradle:13-17`、`Fabric/build.gradle:16-19` |

**版本管理与多版本兼容策略（重点）**
- 单仓 4 个子项目：`settings.gradle:38` `include("Common","Fabric","Forge","NeoForge")`。
- Jar 版本号由 buildSrc 统一拼成 `${mc_version}-${loader}-${modVersion}` → 如 `1.21.1-Fabric-5.1.8`（`buildSrc/src/main/groovy/multiloader-common.gradle:9`）。
- Common 源码通过自定义 configuration `commonJava/commonResources/commonGeneratedResources` 被三个 loader 子项目直接 `source(...)` 进自身 sourceSet（`buildSrc/src/main/groovy/multiloader-loader.gradle:17-38`）——同一份 Common 源码按三端各编译一次，**不用 architectury / shadow jar**。
- 发布：3 个 CurseForge 项目 id + 1 个 Modrinth 项目（`gradle.properties:26-31`），Maven 坐标经 mavenJava publication 发布，并额外声明 3 个 capability 别名 `$group:$mod_id:$version`、`$group:$mod_id-<loader>-<mc>:$version`（`multiloader-common.gradle:49-54`）。
- MC 范围写成 `[1.21,1.22)`，一个 jar 覆盖 1.21.x 补丁版本。历史分支命名线索：pom 的 license URL 仍指向 `blob/forge/1.18/LICENSE`（`multiloader-common.gradle:136`），说明曾按 `forge/1.18` 式分支管理；远端完整分支列表**未确认**（浅克隆仅 `1.21.1`）。
- 平台差异一律走 ServiceLoader，不用 mixin/条件编译：`services/Services.java:8-11` 载入 4 个 helper（`IPlatformHelper`/`IAutoRegisterHelper`/`IBlockEntityTypeHelper`/`IParticleTypeHelper`），三端各有 `XxxAutoRegisterHelper` 等实现，靠 `META-INF/services/*` 声明。

## 2. 源码规模与包结构

- 实测 `find . -name '*.java' | wc -l` = **205** 个文件，总行数 **14625**。
- 分项目：Common 122 / Fabric 29 / Forge 27 / NeoForge 27。
- 最大 10 文件：`noise/FastNoise.java` 2198、`world/structure/jigsaw/assembler/JigsawStructureAssembler.java` 790、`noise/OpenSimplex2S.java` 492、`api/world/randomize/BlockStateRandomizer.java` 294、`world/structure/jigsaw/JigsawManager.java` 281、`world/structure/jigsaw/element/YungJigsawSinglePoolElement.java` 252、`api/world/randomize/ItemRandomizer.java` 250、`.../terrainadaptation/adaptations/EnhancedTerrainAdaptation.java` 249、`.../beardifier/EnhancedBeardifierHelper.java` 243、`world/structure/YungJigsawStructure.java` 241。
- Common 主要包（文件数）：`world.structure.condition` 15、`api.autoregister` 12、`world.structure.jigsaw.element` 8、`mixin.accessor` 8、`mixin` 7、`world.structure.terrainadaptation`（`aquiferoverride` 7 / `adaptations` 6 / `beardifier` 4）、`services` 5、`module` 4、`autoregister` 4、`json` 4、`world.structure.action` 4。
- 三端包结构完全对称：`yungsapi/{mixin,module,services}`；Forge/NeoForge 各 21 个 `*Module*` 类，Fabric 19 个——**"模块类按加载器各写一份、逻辑放 Common"** 的划分即 Better X 系列共用面的来源。

## 3. 入口与注册

- Common：`YungsApiCommon`（`Common/src/main/java/com/yungnickyoung/minecraft/yungsapi/YungsApiCommon.java:12-19`）只存 `MOD_ID`/`LOGGER`，`init()` 调 `AutoRegistrationManager.initAutoRegPackage("...yungsapi.module")`。
- Fabric：`YungsApiFabric implements ModInitializer`（`Fabric/.../YungsApiFabric.java:5`）；Forge：`@Mod(YungsApiCommon.MOD_ID)`；NeoForge：`@Mod` 构造函数注入 `IEventBus`（`NeoForge/.../YungsApiNeoForge.java:16-24`）。
- **不用 DeferredRegister/Registrate**，自研 `@AutoRegister` 注解（`api/autoregister/AutoRegister.java:32-36`，可打在 TYPE/FIELD/METHOD）。
- 4 步流程（`autoregister/AutoRegistrationManager.java:38-49`）：扫描包 → 反射取静态字段 → `AutoRegisterFieldRouter.queueField` 按 `instanceof` 分派进 19 个 `List<AutoRegisterField>`（`autoregister/AutoRegisterFieldRouter.java:17-57`，注释明言"永不重构，用 if 堆到天荒地老"）→ `processQueuedAutoRegEntries()`（Forge/NeoForge 逐 Module `processEntries()` 订阅注册事件，Fabric 立即注册）→ 调用带注解的静态无参方法。
- 写法样例（`module/StructurePoolElementTypeModule.java:13-37`）：

```java
@AutoRegister(YungsApiCommon.MOD_ID)
public class StructurePoolElementTypeModule {
    @AutoRegister("yung_single_element")
    public static StructurePoolElementType<YungJigsawSinglePoolElement> YUNG_SINGLE_ELEMENT =
            () -> YungJigsawSinglePoolElement.CODEC;
```

- Forge 侧扫描用 FML 的 `ModFileScanData` ASM 注解数据，两趟：先收类级 `@AutoRegister` 值当 namespace，再处理字段（`Forge/.../services/ForgeAutoRegisterHelper.java:49-63`）；NeoForge 用 `event.register(registryKey, helper -> …)` 并 `markProcessed()` 去重（`YungsApiNeoForge.java:50-55`）。消费者 mod 只需在初始化开头调 `YungAutoRegister.scanPackageForAnnotations("你的包")`（仅 Fabric 真正执行，`api/YungAutoRegister.java:29-33`）。

## 4. 核心系统

**(1) 结构类型 `yungsapi:yung_jigsaw`**：`world/structure/YungJigsawStructure.java:37-55` 的 CODEC 暴露 `start_pool/start_jigsaw_name/size/x_offset_in_chunk/z_offset_in_chunk/use_expansion_hack/project_start_to_heightmap/max_distance_from_center/max_y/min_y/enhanced_terrain_adaptation/dimension_padding/liquid_settings`；`validateRange`（:182-205）禁止同时用 vanilla 与原版 `terrain_adaptation`，并校验 `max_distance_from_center + 适配核半径 ≤ 128`（超了会结构溢出 chunk）。`findGenerationPoint` 委托 `YungJigsawManager`。

**(2) JigsawStructureAssembler**（`world/structure/jigsaw/assembler/JigsawStructureAssembler.java`）：改写自 vanilla `JigsawPlacement.Placer`；`unprocessedPieceEntries` 用 `Deque` 做 BFS 装配（:100-123）；`pieceCounts`/`maxPieceCounts` 两张 Map 实现 `max_count` 限制（:82-88）；`is_priority` piece 置顶选取（`JigsawManager.java:164-170`）；权重选取先 `Util.shuffle` 再累减（:150-185）；某 piece 放不下任何子块时回退 deadend pool 并回滚 junction/octree/计数（:209-246）。

**(3) 数据驱动修饰 DSL（condition + actions + target_selector）**：`world/structure/modifier/StructureModifier.java:23-28` CODEC = `condition` / `actions`(list) / `target_selector`，`apply` 顺序为"判条件→选目标→逐 action"（:40-55）；14 种 condition（`structure/condition/StructureConditionType.java:36-48`：any_of/all_of/not/altitude/depth/random_chance/piece_in_range/mod_loaded/mod_loader/piece_in_horizontal_direction/rotation/biome 等）、2 种 action（delay_generation/transform）、1 种 target_selector（self）。类型表**不用注册表**，而是 interface + 静态 HashMap + `flatXmap`/`dispatch`（:19-33），外部可调 interface 静态 `register(ResourceLocation, MapCodec)` 扩展（:53）。统一上下文 `StructureContext`（Builder 11 字段：depth/pos/rotation/pieces/pieceEntry/random/randomState/biomeSource…，`structure/context/StructureContext.java:89-163`）。

**(4) 增强地形适配 + Beardifier 接管**：`EnhancedTerrainAdaptationType`（`terrainadaptation/adaptations/EnhancedTerrainAdaptationType.java:36-41`：none / carved_top_no_beard_large / small / custom）；`EnhancedBeardifierHelper.forStructuresInChunk`/`computeDensity`（`beardifier/EnhancedBeardifierHelper.java:41,135`）重写密度计算；`mixin/BeardifierMixin.java:31-47` 以 `priority = 1100` + `@Inject(at=RETURN, cancellable)` 接管原版结果；`NoiseChunkMixin` 把 `NoiseChunk` 反挂进 beardifier，配合 `AquiferOverride`（none/replace/solidify，7 个类）在结构范围内改写含水层。

**(5) 池元素扩展**：抽象基类 `YungJigsawPoolElement`（`world/structure/jigsaw/element/YungJigsawPoolElement.java:26-103`）额外字段 `name / max_count / min_required_depth / max_possible_depth / is_priority / ignore_bounds / condition / enhanced_terrain_adaptation`（字段名即 JSON key）；实现类 `YungJigsawSinglePoolElement`（252 行，带 modifiers 列表）、`YungJigsawFeatureElement`，旧 `MaxCount*` 4 个已 `@Deprecated`。

**(6) 通用工具/数据抽象**：`api/world/randomize/BlockStateRandomizer`（294 行，概率表 + 默认方块 + 每项可带 `condition`，:258-284；同时提供 Codec 与 CompoundTag 存取）与 `ItemRandomizer`（250 行）同构；Gson 侧另有 `json/BlockStateRandomizerAdapter`、`ItemRandomizerAdapter`；`io/JSON.java` 统一 Gson 读写；`codec/CodecHelper.BLOCKSTATE_STRING_CODEC` 让 JSON 写 `"minecraft:stone[axis=y]"`；`util/BoxOctree`（八叉树，`subdivideThreshold=10`/`maximumDepth=3`，:14-21）做部件边界检测；`world/util/{BoundingBoxHelper,SurfaceHelper}`、`math/ColPos`、`world/banner/{Banner,ColoredBannerPattern}`、`world/spawner/MobSpawnerData`；`noise/FastNoise`+`OpenSimplex2S` 实现 `noise/INoiseLibrary`（给第三方 noise 库留兼容层）；`world/structure/processor/ISafeWorldModifier` 绕过 PaletteContainer 锁写方块规避多线程崩溃（注释署 TelepathicGrunt + YUNGNICKYOUNG）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（未发现任何自定义包/networking/channel 类）。
- 数据驱动：**有且是核心**。结构类型、池元素类型、condition/action/target_selector、enhanced_terrain_adaptation、aquifer_override 全部 codec + JSON；自带 4 个结构 tag（`Common/src/main/resources/data/yungsapi/tags/worldgen/structure/remove_{delta,basalt_columns,magma,vines}_feature_in.json`），配 4 个 mixin 全局清除结构内定点特征。
- 配置：**无** config 类。
- datagen：**无**（无 `GatherDataEvent`/`DataGenerator`/`FabricDataGenerator` 引用）；但 buildSrc 预留了 `src/generated/resources` 与 `commonGeneratedResources` 通道（`Common/build.gradle:35-47`），Forge/NeoForge build.gradle 保留 `data` run。

## 6. Mixin

- 配置：`Common/src/main/resources/yungsapi.mixins.json`（package `…yungsapi.mixin`，`compatibilityLevel: JAVA_17`，plugin `YungsApiMixinPlugin`，7 个 mixin + 8 个 accessor）；另有 `yungsapi_fabric.mixins.json`（3 个）、`yungsapi_forge.mixins.json`（1 个）、`yungsapi_neoforge.mixins.json`（1 个），由各端 `fabric.mod.json`/`neoforge.mods.toml`/`mods.toml` 注册。
- 代表性 hook：

| Mixin | 目标 | 注入 |
|---|---|---|
| `mixin/BeardifierMixin.java:31-47` | `Beardifier`（priority 1100） | `@Inject(method="forStructuresInChunk", at=RETURN, cancellable)`、`method="compute"` |
| `mixin/NoiseChunkMixin.java:52-65` | `NoiseChunk` | `@Inject("<init>", RETURN)` 缓存引用；`@Inject("getInterpolatedState", RETURN, cancellable)` 用 `AquiferOverrideMask` 阻止填方块 |
| `mixin/accessor/StructureTemplatePoolAccessor.java:11-14` | `StructureTemplatePool` | `@Accessor getRawTemplates()` 取池权重表 |
| `mixin/NoXxxInStructuresMixin`（4 个） | 特征/地形特征 | 按结构 tag 抑制玄武岩柱/三角洲/岩浆/藤蔓 |
| `NeoForge/.../mixin/IncreaseStructureWeightLimitMixinNeoForge.java:18-29`（三端各一份） | `StructureTemplatePool` | `@WrapOperation` 目标 `Codec.intRange(II)`（`lambda$static$1`/`method_28886`，`require=0, remap=false`），把权重上限提到 5000，绕 MC-203131 |
| `Fabric/.../mixin/EntityProcessorMixinFabric.java:38-80` | `StructureTemplate.placeInWorld/placeEntities` | 用 `ThreadLocal<StructureProcessingContext>` 把 `StructureEntityProcessor` 应用到结构实体（Fabric 特有） |

- `YungsApiMixinPlugin.java:31-39` 的 `shouldApplyMixin` 仅对 `MinecraftServerMixin` 在开发环境返回 false，避免与 ServerCore 等冲突。

## 7. 值得学的 5 条具体做法

1. **注解 + 包扫描的跨加载器注册**：`@AutoRegister` + `AutoRegistrationManager`/`AutoRegisterFieldRouter` 把 20 个注册表压成"声明一个静态字段"，Fabric 立即注册、Forge/NeoForge 由各 Module 订阅事件 —— 适用：想消掉 DeferredRegister 样板的库/多加载器 mod（`Common/src/main/java/.../autoregister/AutoRegisterFieldRouter.java`、`module/StructurePoolElementTypeModule.java`）。
2. **Common 源码以 sourceSet 注入而非 shadow/architectury**：`commonJava/commonResources` configuration + `source(configurations.commonJava)`，三端各编一份 —— 适用：不想引入第三方多加载器构建链（`buildSrc/src/main/groovy/multiloader-loader.gradle:17-38`）。
3. **interface + 静态 HashMap + `flatXmap` 自建 JSON 类型表**代替原版注册表（含 `register(ResourceLocation, MapCodec)` 扩展点，未知类型给出明确报错）—— 适用：给自己 mod 加一套小 DSL 又不想污染 registry（`world/structure/condition/StructureConditionType.java:19-33`）。
4. **`priority = 1100` + RETURN-cancellable 注入接管整段算法**（Beardifier 密度计算外包给 `EnhancedBeardifierHelper`）—— 适用：要改世界生成算法且需与其它 mixin 共存（`mixin/BeardifierMixin.java:31-47`）。
5. **装配完成后统一跑一遍 `applyModifications()`，并把"延迟生成"部件在列表末尾重排**（保证结构整体一致性与生成顺序）—— 适用：结构/地物生成后期需要全局视角的修正（`world/structure/jigsaw/assembler/JigsawStructureAssembler.java:614-643`）。

（另可借：`util/BoxOctree.java:14-21` 八叉树做 AABB 集合检测；`@WrapOperation(require=0, remap=false)` 以"打不中就静默"换取多版本兼容。）

## 8. 公开 API（库/前置 mod 专章）

- **公开 API 包**：`com.yungnickyoung.minecraft.yungsapi.api`
  - `api/YungAutoRegister.java:29` `scanPackageForAnnotations(String)`（消费者入口）
  - `api/YungJigsawManager.java:62` `assembleJigsawStructure(...)`
  - `api/autoregister/`：`AutoRegister` 注解 + `AutoRegisterBlock/Item/EntityType/BlockEntityType/CreativeTab/MobEffect/Potion/ParticleType/SoundEvent/Command` 包装类 + `AutoRegisterUtils`（brew/compost 注册）
  - `api/world/randomize/`：`BlockStateRandomizer`、`ItemRandomizer`
- **扩展点接口**：`StructureConditionType` / `StructureActionType` / `StructureTargetSelectorType` / `EnhancedTerrainAdaptationType` / `AquiferOverrideType` 的静态 `register(ResourceLocation, MapCodec)`（interface 静态方法默认 public，外部 mod 可注册新 JSON 类型）；`YungJigsawPoolElement` 抽象类可继承出自定义池元素；`ISafeWorldModifier`（安全写世界的工具接口）；`StructureEntityProcessor`（Fabric 侧结构实体处理接口）。
- **外部 mod 接入方式**：结构 JSON 里 `"type": "yungsapi:yung_jigsaw"`（`api/YungJigsawManager.java:18-19` 明确从 1.19.2 起不再需要调 API，改 JSON 即可）；池元素 JSON 用 `yungsapi:yung_single_element` / `yungsapi:yung_feature_element`；构建依赖坐标 `com.yungnickyoung.minecraft.yungsapi:YungsApi:<mc>-<loader>-<版本>`（或 capability `$group:$mod_id:$version`），并调用 `YungAutoRegister.scanPackageForAnnotations`.
- **未确认**：Better X 系列各 mod 对 API 的具体使用点无法在本仓库内验证，只能从 `api/` 与 `module/`、`services/` 的划分推断共用面（注册/AutoRegister、结构装配、randomizer、beardifier、noise 兼容层）。
