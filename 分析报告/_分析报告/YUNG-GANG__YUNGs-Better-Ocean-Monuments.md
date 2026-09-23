# YUNG-GANG/YUNGs-Better-Ocean-Monuments 源码分析报告

## 1. 基本信息

- Mod 名：YUNG's Better Ocean Monuments；mod_id `betteroceanmonuments`；作者 YUNGNICKYOUNG, Tera
- 目标版本：`gradle.properties:2` version=5.1.1，`mc_version=26.1.2`，`mc_version_range=[26.1,)`；`java_version=25`
- 加载器：NeoForge `26.1.2.75`（`neoforge_version_range=[26.1.2.75,)`）+ Fabric（loader `0.18.6`，fabric-api `0.150.0`）
- Gradle 插件：`build.gradle:3-6` → `net.fabricmc.fabric-loom 1.15.5`、`net.neoforged.moddev 2.0.141`、curseforgegradle、minotaur；`settings.gradle:6` foojay-resolver
- 多项目结构：`settings.gradle:12` `include("Common", "Fabric", "NeoForge")`
- 许可证：LGPLv3（`gradle.properties:11`）
- 编译依赖：**YUNGs-API 为硬前置**，`NeoForge/.../META-INF/neoforge.mods.toml` 中 `modId="yungsapi" versionRange="[${mc_version}-NeoForge-${yungsapi_version},)" type="required"`（`yungsapi_version=6.1.3`）。Fabric 侧用 cloth-config `26.1.154` + modmenu `18.0.0-beta.1`

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **33 个文件，987 行**（极小仓库）。

| 包（第 3 层） | 文件数 |
|---|---|
| `betteroceanmonuments.world.processor` | 10 |
| `...services` (Common/Fabric/NeoForge) | 3 + 2 + 2 |
| `...module` | 3（+NeoForge/Fabric 各 1） |
| `...mixin` / `...mixin.accessor` | 2 / 1 |
| `...config`（Fabric/NeoForge）| 2 / 2 |

最大文件：`RandomOxidizationProcessor.java` 62、`LegProcessor.java` 59、`PersistentTridentMixin.java` 57、`WaterlogProcessor.java` 56、`RandomPrismarineSlabDecorationProcessor.java` 54。

## 3. 入口与注册

NeoForge 入口 `NeoForge/src/main/java/com/yungnickyoung/minecraft/betteroceanmonuments/BetterOceanMonumentsNeoForge.java:12`（`@Mod` + 构造注入 `IEventBus, ModContainer`）；Fabric 入口 `Fabric/.../BetterOceanMonumentsFabric.java:7` 仅调用 `BetterOceanMonumentsCommon.init()`。共同初始化 `Common/.../BetterOceanMonumentsCommon.java:20-27`：

```java
public static void init() {
    YungAutoRegister.scanPackageForAnnotations("...betteroceanmonuments.module");
    Services.MODULES.loadModules();
    LocateReplacer.register(BuiltinStructures.OCEAN_MONUMENT,
        ResourceKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath(MOD_ID, "ocean_monument")),
        () -> CONFIG.general.disableVanillaMonuments);
}
```

**注册框架是 YUNGs-API 的注解扫描**，不用 DeferredRegister：`module/StructureProcessorTypeModule.java:8` 类上 `@AutoRegister(MOD_ID)`，字段上 `@AutoRegister("air_processor")` 等，共注册 10 个 `StructureProcessorType`（air/waterlog/random_prismarine_slab/random_dark_prismarine_slab/structure_void/sand_gravel/random_oxidization/seagrass/random_sponge/leg）。跨平台对象获取走 Java SPI：`services/Services.java:11-17` `ServiceLoader.load(...).findFirst().orElseThrow(...)`。

## 4. 核心系统

1. **StructureProcessor 后处理体系（数据驱动的主体）**：每个 processor 实现 `processBlock(LevelReader, BlockPos jigsawPiecePos, BlockPos jigsawPieceBottomCenterPos, blockInfoLocal, blockInfoGlobal, StructurePlaceSettings)` 并返回新 `StructureTemplate.StructureBlockInfo`。设计点：①占位方块模式——`LegProcessor.java:36` 用 `Blocks.BLUE_STAINED_GLASS`、`RandomSpongeProcessor.java:33` 用 `ORANGE_STAINED_GLASS` 作为"指令方块"，生成时替换为真实结构（水中墩柱 / 海绵与空腔）；②位置确定性随机——`RandomOxidizationProcessor.java:34` `structurePlacementData.getRandom(blockInfoGlobal.pos())` 保证同坐标可复现；③用 `withPropertiesOf(state)` 保留楼梯/台阶的朝向属性（同文件 47-54 行）。
2. **水中放置的正确性处理**：`WaterlogProcessor.java:35-41` 除了给带 `BlockStateProperties.WATERLOGGED` 的方块灌水，还在 `WorldGenRegion.getCenter().equals(ChunkPos.containing(pos))` 且坐标 %16 落在 0/15 的 chunk 边界时调用 `getChunk(pos).markPosForPostprocessing(pos)`，靠原版后处理机制补排流体 tick 修边界水。`AirProcessor.java:32-37` 把海平面以下的空气换成 `Blocks.WATER`。
3. **禁用原版海底神殿的两段式方案**：`mixin/DisableVanillaMonumentsMixin.java:26-42` 注入 `ChunkGenerator#tryGenerateStructure` 的 HEAD，命中 `StructureType.OCEAN_MONUMENT` 且配置开启则 `cir.setReturnValue(false)`；同时 `LocateReplacer.register` 把 `/locate` 从原版结构重定向到自家结构 key，避免"结构存在但定位失败"。
4. **结构内三叉戟永不消失**：`mixin/PersistentTridentMixin.java:33-41` 注入 `AbstractArrow#tickDespawn` HEAD，条件为「是 `ThrownTrident` + owner UUID 等于硬编码常量 `"e624cdc1-c238-4dde-9f22-1f76b5123ce8"` + 所在位置 `structureManager().getStructureWithPieceAt(pos, TagModule.BETTER_OCEAN_MONUMENT)` 有效」时 cancel；取 owner 靠 `mixin/accessor/ProjectileAccessor.java` 的 `@Accessor getOwner()`。
5. **配置作为单一真源 + 双平台烘焙**：`Common/.../module/ConfigModule.java` 是纯 POJO（`boolean disableVanillaMonuments = true`），各平台在 config 变化时把值写回它——NeoForge 见 `NeoForge/.../module/ConfigModuleNeoForge.java:19-31`（`LevelEvent.Load` + `ModConfigEvent` 双触发）；Fabric 用 cloth-autoconfig `Toml4jConfigSerializer`（`config/BOMConfigFabric.java:7` `@Config(name="betteroceanmonuments-fabric-26_1")`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（无任何 packet/network 注册代码）。
- 数据驱动：结构 JSON 与 NBT 模板**不在本仓库快照内**——`Common/src/main/resources` 下仅有 `betteroceanmonuments.mixins.json`，`find . -name '*.nbt' | wc -l` = 0（模板应为外部资源/独立发布，未确认）。
- 配置：见 4.5；NeoForge 侧文件名 `betteroceanmonuments-neoforge-26_1.toml`，`BOMConfigForge.java:12` 用 `BUILDER.push("YUNG's Better Ocean Monuments")` 建分组。
- datagen：**无**。

## 6. Mixin

配置：`Common/src/main/resources/betteroceanmonuments.mixins.json`（`required:true`，`compatibilityLevel: "JAVA_17"`——注意与实际 `java_version=25` 不一致，`defaultRequire:1`）。
- `DisableVanillaMonumentsMixin` → target `ChunkGenerator#tryGenerateStructure`，HEAD @Inject cancellable
- `PersistentTridentMixin` → target `AbstractArrow#tickDespawn`，HEAD @Inject cancellable
- `accessor.ProjectileAccessor` → target `Projectile`，`@Accessor getOwner()`

## 7. 值得学的 5 条具体做法

1. **用占位方块携带"指令"**：模板里放蓝玻璃/橙玻璃，processor 读到就生成动态结构，美术与逻辑解耦（`world/processor/LegProcessor.java:36`，适用任何需要程序化几何的结构）。
2. **位置种子随机而非全局随机**：`structurePlacementData.getRandom(pos)` 让同一坐标每次生成结果一致（`RandomOxidizationProcessor.java:34`，适用随机化装饰/矿脉）。
3. **chunk 边界流体用 `markPosForPostprocessing` 补 tick**，而不是自己写流体更新（`WaterlogProcessor.java:38`，适用水下/跨区块结构）。
4. **配置 POJO 放在 Common、各平台只做 bake**：逻辑代码只读 `BetterOceanMonumentsCommon.CONFIG`，平台差异被限制在两个 ConfigModule 内（`Common/.../module/ConfigModule.java` + `NeoForge/.../module/ConfigModuleNeoForge.java`）。
5. **重定向 + 移除原版结构要成对处理**：既 mixin 阻止生成，又注册 `LocateReplacer` 保证 `/locate` 可用（`BetterOceanMonumentsCommon.java:24`）。

## 8. 库 / API 说明

非库模组。对外暴露仅是结构标签 `module/TagModule.java:10` `TagKey<Structure> BETTER_OCEAN_MONUMENT`（`betteroceanmonuments:better_ocean_monuments`），供外部判断是否处于本 mod 结构内。
