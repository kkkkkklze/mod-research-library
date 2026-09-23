# YUNG-GANG/YUNGs-Bridges 源码分析报告

## 1. 基本信息
- Mod 名 YUNG's Bridges；mod_id `yungsbridges`；作者 YUNGNICKYOUNG；版本 6.1.0
- 目标 MC `26.1.2`（range `[26.1,)`），java_version 25（`gradle.properties:1-16`）
- 加载器：NeoForge 26.1.2.75（moddev 2.0.141）+ Fabric（fabric-loom 1.15.5、loader 0.18.6、fabric-api 0.150.0）
- Gradle：`settings.gradle:20` include Common/Fabric/NeoForge；自研 `buildSrc` 约定插件 multiloader-common / multiloader-loader
- 许可证 LGPLv3；group `com.yungnickyoung.minecraft.yungsbridges`
- 编译依赖：**YungsApi 6.1.0（必需前置，双端各取 artifact）**；Fabric 另 cloth-config 26.1.154、modmenu 18.0.0-beta.1、Reflections 0.10.2（`include` 内嵌）；Common mixin 0.8.5 + mixinextras 0.5.3（compileOnly）

## 2. 源码规模与包结构
- 35 个 .java / 1504 行（实测）。Common 30、Fabric 4、NeoForge 3
- 包：`world.processor` 13、`world.feature(+.config)` 5、`module` 3、`services` 3、`world.placement` 2、`mixin` 1
- 最大文件：ITemplateFeatureProcessor 231、BridgePlacement 206、AbstractTemplateFeature 86、OptionalBlockProcessor 70、BridgeFeature 64
- 快照资源极少：仅 `Common/src/main/resources/yungsbridges.mixins.json` 与 `NeoForge/src/main/resources/META-INF/neoforge.mods.toml`；无 fabric.mod.json、无 lang/data/NBT（是否裁剪未确认）

## 3. 入口与注册
主类 `Common/.../yungsbridges/YungsBridgesCommon.java:13-14`：
```java
YungAutoRegister.scanPackageForAnnotations("com.yungnickyoung.minecraft.yungsbridges.module");
Services.MODULES.loadModules();
```
Fabric 端 `YungsBridgesFabric implements ModInitializer`；NeoForge 端 `@Mod` 构造器调 `init()`。
- 注册不是 DeferredRegister，而是 **YungsApi `@AutoRegister` 注解 + 包扫描**：类上 `@AutoRegister(MOD_ID)`、字段上 `@AutoRegister("bridge")`（`module/FeatureModule.java`、`module/PlacementModifierTypeModule.java`），注册表由字段类型（Feature / PlacementModifierType）推断。
- 非注解注册：`module/FeatureProcessorModule.java` 静态 `PROCESSORS` 列表 + `register()`。
- 平台服务用 `java.util.ServiceLoader`（`services/Services.java`）：`IPlatformHelper`、`IModulesLoader`；`FabricModulesLoader` 额外调 `BiomeModificationModuleFabric.init()`，NeoForge 侧为空实现。

## 4. 核心系统
1. 模板特征流水线 `world/feature/AbstractTemplateFeature.java:60,74`：`getStructureManager().get(id)` → `template.placeInWorld(...)` → `processors.forEach(processTemplate)`；`BridgeFeature.java:21-31` 用 `useProcessors()` 挂 12 个处理器。
2. 处理器体系 `ITemplateFeatureProcessor`（含 `generatePillarDown`、`getStairsBlockWithState` 等 default 工具）；`DynamicLegProcessor.java:29,57` 用 `template.filterBlocks(...)` 按“标记方块”判型（黄玻璃=原木腿、粉玻璃=石砖腿、海晶石墙=圆石墙腿）就地下延生成桥腿，并用 YungsApi `BlockStateRandomizer` 加权随机（`.addBlock(MOSSY_STONE_BRICKS, .5f)`）。
3. 放置校验 `BridgePlacement.java:75-190`：以海平面在 16×16 网格扫描候选，要求两端 `canOcclude()` 且 `Heightmap.WORLD_SURFACE ≤ seaLevel+1`、两端各满足 `numSolidBlocksNeeded` 个实心块、中间 `min_water_z..max_water_z` 全为液体；7 个参数全部用 MapCodec 暴露（`BridgePlacement.java:20-27`）。
4. `MultipleAttemptSingleRandomFeature`：在 `HolderSet<PlacedFeature>` 中随机试放直至成功，并实现 `getSubFeatures()` 供解析器下钻。
5. `RngInitializerPlacement.java:31-33`：按坐标重设 `randomSource` 种子（大质数常数），补救 MC 不初始化 placement RNG。
6. 群系注入：Fabric 走 `BiomeModifications.add(ADDITIONS, hasTag(has_structure/bridge), addFeature(...))`（`BiomeModificationModuleFabric`），NeoForge 交给数据包。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无。
- 配置：无配置类；Fabric 依赖 cloth-config/modmenu，但快照代码中无任何引用（用途未确认）。
- 数据驱动：configured/placed_feature 由数据包提供，结构 NBT 经 `BridgeFeatureConfig.id` 指向；快照无 data 目录。
- datagen：`NeoForge/build.gradle` 有 data run（`--mod yungsbridges --all --output src/generated/resources/`），`Common/build.gradle` 定义 `generated` sourceSet 与 `commonGeneratedResources` 配置；产物未入库。

## 6. Mixin
`Common/src/main/resources/yungsbridges.mixins.json`（package `...yungsbridges.mixin`，compatibilityLevel JAVA_17）。唯一 `mixin/SuppressLogMixin.java`：`@Inject(method="logAndPauseIfInIde(Ljava/lang/String;)V", at=HEAD, cancellable=true, require=0)`，消息以 `Detected setBlock in a far chunk` 开头且含 `yungsbridges:bridge_list` 时取消日志。

## 7. 值得学的 5 条做法
1. `buildSrc` 约定插件做 multiloader：`multiloader-common.gradle:57-70` 暴露 `commonJava/commonResources/commonGeneratedResources` 配置 + `io.github.mcgradleconventions.loader` 属性，`multiloader-loader.gradle:14-40` 让 loader 子工程直接编译/打包 Common 源码资源，不需 shadow 或复制源码。
2. “静态 NBT + 运行时处理器流水线”结构改造（`AbstractTemplateFeature` + `ITemplateFeatureProcessor`），比 jigsaw 轻量。
3. 用特定方块当占位标记在 NBT 里表达动态逻辑（`DynamicLegProcessor.java:29`），数据作者无需写代码。
4. 放置条件封装成自定义 `PlacementModifier` 并全参数化（`BridgePlacement`），同一 feature 可被多条 placed_feature json 复用。
5. 兼容性 mixin 一律 `require = 0` + 精确字符串过滤（`SuppressLogMixin`），上游改名/分支差异不会崩。

## 8. 库特性
本 mod 非库；但它是 **YungsApi 的接入样板**（`@AutoRegister`/`YungAutoRegister`、`BlockStateRandomizer`、platform service 模板），可作为消费 YungsApi 的参考。
