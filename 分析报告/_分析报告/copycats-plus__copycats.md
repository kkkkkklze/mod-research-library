# 源码分析报告：copycats-plus/copycats（Create: Copycats+）

## 1. 基本信息

- Mod 名：Create: Copycats+；mod_id：`copycats`；作者：Lysine, Bennyboy1695, Redcat_XVIII
- 目标：Minecraft 1.21.1；**多加载器（Fabric + NeoForge）**，architectury 三模块结构（`common` / `fabric` / `neoforge`）
- Gradle 插件：`architectury-plugin 3.4.+`、`dev.architectury.loom 1.10.+`、Gradle 8.14、Java 21（`options.release.set(21)`）、Parchment `2024.11.17`
- 许可证：**All Rights Reserved**（`gradle.properties` 的 `mod_license`）→ 只能学思路，不能搬代码
- 关键依赖：Create `6.0.8-168`（NeoForge）/ `create_fabric_version=6.0.0.0+mc1.20.1-build.1653`（Fabric 侧版本号字符串仍标 mc1.20.1，未确认是否为笔误）、Registrate `MC1.21-1.3.0+62`、Flywheel `1.0.5`、MixinExtras `0.4.1`、Ponder `1.0.66`、JEI `19.21.0.247`、EMI `1.1.22`
- 它被谁依赖：hlysine 的 **Create: Connected** 直接依赖 `com.copycatsplus:copycats:3.0.4+mc.1.21.1-neoforge`
- 自身发布：`maven-publish` 到 GitHub Packages 与 `https://maven.realrobotix.me/copycats`

## 2. 源码规模与包结构

- `.java` 文件 **342** 个，总行数 **31 636**（实测 `find | xargs cat | wc -l`）；`common` 246 / `fabric` 52 / `neoforge` 44
- 最大文件：`common/.../CCBlocks.java` 862、`foundation/copycat/ICopycatBlock.java` 651、`content/copycat/byte_panel/CopycatBytePanelBlock.java` 566、`foundation/copycat/multistate/IMultiStateCopycatBlock.java` 534、`content/copycat/fluid_pipe/CopycatFluidPipeModelCore.java` 515、`CCShapes.java` 483、`content/copycat/bytes/CopycatByteBlock.java` 466
- 主要包（第 3 层）：`content/copycat/*`（约 40 个形状一个子包，共 94 个文件）、`foundation/copycat/{model,multistate,tooltip}`（57 个）、`mixin/*`（41 个）、`config`（11）、`datagen`（7）、`network`（3）、`compat`（5）、`utility`（13 + `utility/shape`）

## 3. 入口与注册

无 `@Mod` 于 common：`neoforge/.../neoforge/CopycatsImpl.java:16`（`@Mod(Copycats.MODID)`）、`:13` 另有 `@Mod(value=..., dist=Dist.CLIENT)` 的 `CopycatsClientImpl`；Fabric 侧为 `fabric/.../fabric/CopycatsImpl.java`。

公共初始化在 `common/.../Copycats.java:23`：

```java
private static final CreateRegistrate REGISTRATE = CreateRegistrate.create(MODID)
        .defaultCreativeTab((ResourceKey<CreativeModeTab>) null)
        .setTooltipModifierFactory(item -> TooltipUtils.sequential(...));
public static void init() {          // :41
    CCBlocks.register(); CCBlockEntityTypes.register(); CCCatVariants.register();
    CCItems.register(); CCConfigs.register(); CCPackets.register();
}
```

注册框架：**Create 的 CreateRegistrate（即 Registrate 分支）**，全部走 builder 链，例如 `CCBlocks.java:135` `REGISTRATE.block("wrapped_copycat", WrappedCopycatBlock::new)`；模型注入用 `.onRegister(onClient(() -> createBlockModel(CopycatMultiByteModelCore::new)))`（`CCBlocks.java:182`）。`CCBlocks.java:851` 用 `REGISTRATE.getAll(BuiltInRegistries.BLOCK.key())` 反查全部已注册方块，并按 `instanceof IMultiStateCopycatBlock` 分类。
平台抽象统一用 architectury `@ExpectPlatform` + 平台 `*Impl` 类（`utility/Platform.java:22`、`config/{fabric,neoforge}/CCConfigsImpl.java`）。

## 4. 核心系统

1. **拷贝方块框架**（`foundation/copycat/`）：`ICopycatBlock`（651 行，`extends IWrenchable, IStateType, TransformableBlock`）提供 `getAcceptedBlockState/getMaterial/prepareMaterial/isCTEnabled/toggleCT/hidesNeighborFace/canConnectTexturesToward/shapeCanOccludeNeighbor` 等 default 扩展点；实体侧 `ICopycatBlockEntity` + `CCCopycatBlockEntity`；`WrappedCopycatBlock` 用于"复制品包裹原版方块行为"。
2. **模型装配 DSL**（`foundation/copycat/model/assembly/`）：`CopycatRenderContext.assemblePiece(AssemblyTransform, MutableVec3 offset, MutableAABB select, MutableCullFace cull, QuadTransform...)`（`CopycatRenderContext.java:26`）把源模型的一块长方体"剪切+装配"到拷贝品上；坐标单位是体素（`vec3(x,y,z)` 内部 `/16`，`:83`）；配套 `MutableQuad/MutableVertex/MutableUV/Mutation` 与预设算子 `QuadRotate/QuadScale/QuadShear/QuadSlope/QuadUVTranslate/QuadUVRotate`。
3. **模型核心**（`foundation/copycat/model/CopycatModelCore.java:22`）：`registerModels(List<ModelEntry>)` + 抽象 `emitCopycatQuads(String key, BlockState state, CopycatRenderContext context, BlockState material)`；`ModelEntry(key, ModelGetter, CopycatModelPart, MaterialMapper, EntryType)`；`EntryType` 四态 `STATIC/COPYCAT/KINETIC/KINETIC_COPYCAT` 用两个布尔（`useCopycatLogic`、`onlyWhenVirtual`）数据化决定"是否用复制材质做遮挡/CT、是否只在虚拟渲染环境出现"；`createModel/createKineticModel` 是 `@ExpectPlatform`；`WithData<T>` 用 `ThreadLocal` 传渲染期数据。
4. **多状态拷贝**（`multistate/`）：`IMultiStateCopycatBlock.storageProperties()` 声明多个材质槽，`CopycatModelCore.registerForMultiState()/registerMultiStatePart()` 自动为每个槽生成模型条目；`MultiStateCopycatBlockEntity` + `MaterialItemStorage` 存各槽材质与物品需求。
5. **动能拷贝渲染**（`model/kinetic/`）：`CopycatInstanceManager` / `KineticCopycatRenderer` / `RendererReloadCache` / `WrappedRenderWorld` + `FilteredBlockAndTintGetter`、`ScaledBlockAndTintGetter`，在虚拟世界里渲染 Create 的 kinetic 模型。
6. **存档迁移**（`foundation/copycat/MigrationManager.java:26`）：把旧 `create:copycat` 方块实体就地转换为本 mod 的 `CCCopycatBlockEntity` / `MultiStateCopycatBlockEntity`（`migrateData`），`migrateStructure()` 处理投影/蓝图，`migrateBlockEntity()` 处理区块加载；由 `mixin/foundation/copycat/migration/{ContraptionMixin,LevelChunkMixin,StructureTemplateMixin}.java` 调起，`CCConfigs.common().disableMigration` 可关。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：`network/CCPackets.java:14`，枚举实现 Catnip 的 `BasePacketPayload.PacketTypeProvider`，`CatnipPacketRegistry(MODID, 3)` 注册版本号 + `CustomPacketPayload.Type` + `StreamCodec`；两个包 `CONFIG_SYNC(ConfigSyncPacket)`、`FILL_COPYCAT(FillCopycatPacket)`；平台网络通过 `CatnipServices.NETWORK`。
- 配置：`config/CCConfigs.java` 继承 Catnip `ConfigBase`，`CONFIGS: EnumMap<ModConfig.Type, ConfigBase>`；`config/SyncConfigBase.java:18-76` 提供 `getSyncConfig()/setSyncConfig()/writeSyncConfig()/readSyncConfig()`，服务端用 `syncToPlayer(ServerPlayer)` 发 `ConfigSyncPacket` 把服务端配置广播到客户端。注册实现分平台：`neoforge/config/neoforge/CCConfigsImpl.java`（`@EventBusSubscriber` + `ModLoadingContext`）、`fabric/config/fabric/CCConfigsImpl.java`（ForgeConfigAPIPort）。
- 功能开关：`config/FeatureToggle.java` + `FeatureCategory`，通过 Registrate `.transform(FeatureToggle.register(FeatureCategory.X))` 挂到 builder 上（`CCBlocks.java` 大量出现），并联动创造模式标签页可见性（mixin `featuretoggle.CreativeModeTabsAccessor`）。
- datagen：`datagen/{CCBlockStateGen,CCLootGen,CCTagGen,CCDatagen}.java` + `datagen/recipes/{CCStandardRecipes,CopycatsRecipeProvider,GeneratedRecipeBuilder}.java`；语言文件反向生成——`CCDatagen.provideDefaultLang()` 读 `assets/copycats/lang/default/{interface,tooltips}.json` 写进 `ProviderType.LANG`；平台入口 `fabric/.../datagen/fabric/CCDatagenImpl.java`（`DataGeneratorEntrypoint`）与 `neoforge` 侧 `GatherDataEvent` 分 HIGHEST/LOWEST 两优先级阶段。

## 6. Mixin

- 配置：`common/src/main/resources/copycats-common.mixins.json`、`fabric/.../copycats-fabric.mixins.json`、`neoforge/.../copycats-neoforge.mixins.json`，三者都挂自定义插件 `com.copycatsplus.copycats.mixin.MixinPlugin`
- 插件（`mixin/MixinPlugin.java:41`）：读 mixin 类的字节码注解，遇到 `@ModMixin(requiredMods=..., applyIfPresent=...)`（`foundation/annotation/ModMixin.java`）就按 `Mods` 枚举的加载状态决定是否应用；`onLoad` 里还调 `MixinExtrasBootstrap.init()`
- 代表性目标：`foundation.copycat.CopycatBlockMixin/CopycatBlockEntityMixin/BlockStateBaseCacheMixin`（方块状态缓存与拷贝逻辑）、`ConnectedTextureBehaviourMixin`、`RotatedPillarCTBehaviourMixin`、`multistate.AirCurrentMixin`、`migration.*`；client 侧 `ClientLevelMixin`、`CTModelMixin`、`LiquidBlockRendererMixin`、`multistate.ModelBlockRendererMixin`；`VoxelShapeAccessor/BlockEntityAccessor/SlidingDoorBlockEntityAccessor` 等 accessor；兼容类 `compat.rubidium.*`、`compat.radium.PathNodeDefaultsMixin`、`compat.verticalslabcompat.CutBlockTypeRegistryMixin`

## 7. 值得学的 5 条具体做法

1. **依赖条件 Mixin**：mixin config 挂 `MixinPlugin` + 自定义 `@ModMixin` 注解，用 ASM 读注解后按 mod 加载情况决定启用（`mixin/MixinPlugin.java:41`）。适用于一个 jar 兼容多 mod / 多渲染器（Sodium、Radium、垂直半砖）。
2. **平台抽象枚举**：`utility/Platform.java:12-27` 把平台判定收敛为 `Platform.CURRENT.isCurrent()/runIfCurrent(Supplier<Runnable>)`，业务代码不出现 `if (FabricLoader...)`。适用于任何 architectury 多加载器项目。
3. **服务端→客户端配置同步基类**：`config/SyncConfigBase.java:18` 递归把子配置写成 `CompoundTag`，客户端 `readSyncConfig` 覆盖自身值。适用于"服务端配置影响客户端渲染/行为"。
4. **渲染意图数据化**：`CopycatModelCore.EntryType`（`:231`）用两个布尔表达"是否需要复制材质 / 是否仅虚拟环境"，同一套 `emitCopycatQuads` 代码同时服务地面网格与 kinetic 虚拟渲染。
5. **存档迁移器**：`MigrationManager.migrateBlockEntity()`（`:57`）+ 反序列化钩子 mixin，把旧注册名的方块实体平滑升级为新实体。适用于重命名注册项或拆分实体类型的迭代。

## 8. 对外 API / 被接入方式

- 发布坐标：`com.copycatsplus:copycats:<version>+mc.<mcver>-<platform>`（GitHub Packages 与 `maven.realrobotix.me/copycats`），下游用 `implementation(...) { transitive = false }` + 自带 Registrate/Create 依赖。
- 外部可直接使用的公开类：`com.copycatsplus.copycats.{CCBlocks,CCItems,CCBlockEntityTypes,CCShapes,CCBuilderTransformers}`；框架层 `foundation/copycat/{ICopycatBlock,ICopycatBlockEntity,CCCopycatBlock,MultiStateCopycatBlock}`；模型层 `foundation/copycat/model/assembly/CopycatRenderContext`（可独立用于其它 mod 的模型装配）；`foundation/copycat/multistate/IMultiStateCopycatBlock` 的 `storageProperties()` 是最主要的扩展点接口。
- 注意：许可证为 All Rights Reserved，接入只能依赖二进制坐标，不能复制源码。
