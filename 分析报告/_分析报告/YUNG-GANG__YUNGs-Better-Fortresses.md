# YUNG's Better Nether Fortresses 源码分析

> 分析对象：`_参考仓库/_bulk/YUNG-GANG__YUNGs-Better-Fortresses`（GitHub: YUNG-GANG/YUNGs-Better-Fortresses），分支 `26.1.2`，HEAD `ab41a3c v4.1.1`。
> 注：该快照只检出了 `**/*.java|*.gradle|*.properties|*.toml`（git skip-worktree），资源文件（169 个 `.nbt`、39 个 `.json`）通过 `git show HEAD:<path>` 读取。

## 1. 基本信息

- Mod 名：YUNG's Better Nether Fortresses；**mod_id `betterfortresses`**；作者 YUNGNICKYOUNG、Acarii（`NeoForge/src/main/resources/META-INF/neoforge.mods.toml`）
- 版本/目标（`gradle.properties`）：mod `version=4.1.1`、`java_version=25`、`mc_version=26.1.2`、`mc_version_range=[26.1,)`、`neoforge_version=26.1.2.75`、`fabric_loader_version=0.18.6`、`fabric_version=0.150.0`、`mc_version_neo_form=26.1.2-1`
- 加载器/构建：Fabric + NeoForge 双平台，三模块 `Common/Fabric/NeoForge`（`settings.gradle`），`buildSrc/src/main/groovy/multiloader-common.gradle` 与 `multiloader-loader.gradle` 为约定插件；插件 `net.fabricmc.fabric-loom 1.15.5`、`net.neoforged.moddev 2.0.141`（`build.gradle`），发布用 curseforgegradle + minotaur
- 许可证：LGPLv3
- 编译依赖（关键：它依赖谁）
  - **YUNGs-API 是它的"平台层"**：`com.yungnickyoung.minecraft.yungsapi:YungsApi:${mc_version}-{Common|Fabric|NeoForge}-6.1.3`（三个子项目 build.gradle）
  - Fabric 侧：`fabric-api ${fabric_version}+${mc_version}`、`cloth-config-fabric 26.1.154`、`modmenu 18.0.0-beta.1`、`org.reflections:reflections:0.10.2`（`include()` 打进 jar）
  - Common 侧：compileOnly `mixin 0.8.5`、`mixinextras-common 0.5.3`
  - 无 accesswidener / accesstransformer（仓库内无该文件）

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **33 个文件 / 1628 行**（Common 16 文件 798 行、Fabric 9 文件 410 行、NeoForge 8 文件 420 行）。这是一个"小而重数据"的仓库：Java 只有 1.6k 行，数据资源却有 199 个文件。

包（到第 3 层，均以 `com.yungnickyoung.minecraft.betterfortresses` 为前缀）：
- Common：`betterfortresses` 1（主类）、`.mixin` 2、`.module` 2、`.services` 4、`.world` 1、`.world.processor` 6
- Fabric：根 1、`.config` 2、`.config.gui` 1、`.module` 1、`.services` 3、`.world` 1
- NeoForge：根 1、`.config` 2、`.module` 1、`.services` 3、`.world` 1（与 Fabric 同构）

最大文件：`NeoForge/.../module/ConfigModuleNeoForge.java` 163、`Fabric/.../module/ConfigModuleFabric.java` 163、`Fabric/.../world/ItemFrameProcessor.java` 157、`NeoForge/.../world/ItemFrameProcessor.java` 153、`Common/.../world/processor/BridgeArchProcessor.java` 143、`Common/.../world/ItemFrameChances.java` 89、`StairPillarProcessor.java` 86、`PillarProcessor.java` 86。

## 3. 入口与注册

公共入口 `Common/src/main/java/com/yungnickyoung/minecraft/betterfortresses/BetterFortressesCommon.java:20-27`：

```java
public static void init() {
    YungAutoRegister.scanPackageForAnnotations("com.yungnickyoung.minecraft.betterfortresses.module");
    Services.MODULES.loadModules();
    LocateReplacer.register(BuiltinStructures.FORTRESS,
            ResourceKey.create(Registries.STRUCTURE, Identifier.fromNamespaceAndPath(MOD_ID, "fortress")),
            () -> CONFIG.general.disableVanillaFortresses);
}
```

- NeoForge：`@Mod(BetterFortressesCommon.MOD_ID)`，构造器注入 `(IEventBus, ModContainer)` → `BetterFortressesCommon.init()` + `ConfigModuleNeoForge.init(container)`（`BetterFortressesNeoForge.java:8-17`）
- Fabric：`ModInitializer.onInitialize()` → `init()`（`BetterFortressesFabric.java`）
- **注册框架不是 DeferredRegister**，而是 YUNGs-API 的注解式自动注册：`@AutoRegister(MOD_ID)` 标类、`@AutoRegister("pillar_processor")` 标静态字段，启动时按包扫描（`module/StructureProcessorTypeModule.java:15-36`，注册 7 个 `StructureProcessorType`）
- 跨平台能力用 `java.util.ServiceLoader` 解耦：`services/Services.java:8-18` 载入 `IPlatformHelper` / `IModulesLoader` / `IProcessorProvider`，实现类由 `Fabric|NeoForge/src/main/resources/META-INF/services/<接口全名>` 指定（各 3 个）

## 4. 核心系统

**(1) 结构处理器链（StructureProcessor，全数据驱动）** `Common/.../world/processor/*`
- 6 个处理器在 `data/betterfortresses/worldgen/processor_list/main.json` 里按 `processor_type: betterfortresses:*` 串成一条链，所有结构池都引用 `betterfortresses:main`
- 两种 Codec 风格：无参单例 `MapCodec.unit(() -> INSTANCE)`（`BridgeArchProcessor.java:27-28`、`NetherWartProcessor.java:21`、`StairPillarProcessor.java:27`、`RedSandstoneStairsProcessor.java:27`）；带参 `RecordCodecBuilder.mapCodec`（`PillarProcessor.java:27-34`：`target_block` / `target_block_output` / `pillar_states` / `direction` / `pillar_length`；`LiquidBlockProcessor.java:23-26`）
- 设计要点：**用彩色方块当"占位标记"**（orange/yellow terracotta、wool、concrete、PRISMARINE_STAIRS），处理器在生成时替换并按需向下延伸柱子（`PillarProcessor.java:57-79`）、生成桥墩与连接墙（`BridgeArchProcessor.java:37-110`）；随机化交给 yungsapi 的 `BlockStateRandomizer` + `StructureContext`（支持 `yungsapi:altitude` 条件，见 processor_list 里 `top_cutoff_y:31/33` 的岩浆块/裂纹砖）
- **只写当前生成区块**：`worldGenRegion.getCenter().equals(ChunkPos.containing(pos))` 判断后才 `setBlockState`（`BridgeArchProcessor.java:118-142`、`PillarProcessor.java:58-60`）

**(2) 结构定义与 Jigsaw 池** `data/betterfortresses/worldgen/*`
- `structure/fortress.json`：`"type":"yungsapi:yung_jigsaw"`、`start_pool: betterfortresses:starts`、`start_jigsaw_name: betterfortresses:anchor`、`size:46`、`enhanced_terrain_adaptation{type:yungsapi:custom, kernel_size:24, top:carve}`、`spawn_overrides.monster` 逐怪权重（blaze 10、wither_skeleton 8、zombified_piglin 5、magma_cube 3、skeleton 2）
- 18 个 worldgen JSON（structure 1 / structure_set 1 / processor_list 1 / template_pool 15）+ 169 个 `.nbt`（halls 70、bridge 44、keep 31、blaze 11、battle_bridge 7、mobs 3、mod_integration 2）
- 池元素统一 `element_type: yungsapi:yung_single_element`，并挂 `condition`（`yungsapi:depth`、`yungsapi:altitude`、`yungsapi:all_of`）、`deadend_pool`、`fallback`、`enhanced_terrain_adaptation`、`is_priority`（`starts.json`、`bridge.json`、`halls.json`）
- 结构池还能带 mod 条件：`starts.json` 中用 `condition{type:yungsapi:mod_loaded, modid:"create"}` 指向 `mod_integration/keep_create.nbt`

**(3) 结构集注入与对外兼容（关键范式）**
- **不覆盖原版 `minecraft:nether_complexes`**，而是新增 `structure_set/fortress.json`，用 `placement.type: yungsapi:enhanced_random_spread`（`spacing:30` / `separation:20`）并声明 `enhanced_exclusion_zone.other_set: "#betterfortresses:fortress_avoid"`（`tags/worldgen/structure_set/fortress_avoid.json` → `minecraft:nether_complexes`），实现与原版堡垒互斥
- 对外暴露 `tags/worldgen/structure/better_fortresses.json`（内容为 `betterfortresses:fortress`），本仓库自带示范：`data/morevillagers/tags/worldgen/structure/on_fortress_explorer_maps.json` 直接引用该 tag；`data/yungsapi/tags/worldgen/structure/remove_{basalt_columns,delta}_feature_in.json` 把本结构加进 yungsapi 的清理名单
- 生成条件用 `tags/worldgen/biome/has_structure/better_fortress.json`：`#minecraft:is_nether` + 可选 `#c:in_nether`（`required:false`）

**(4) 原版替换与刷怪修复（全部由 2 个 mixin 完成）**
- `mixin/DisableVanillaFortressesMixin.java:26-43`：`@Inject(method="tryGenerateStructure", at=@At("HEAD"), cancellable=true)` 注入 `ChunkGenerator`，当配置开启且 `structureSetEntry.structure().value().type() == StructureType.FORTRESS` 时返回 false，彻底停用原版堡垒
- `mixin/FixMobSpawningMixin.java:30-39`：`@Inject(method="isInNetherFortressBounds", at=@At("HEAD"), cancellable=true)` 注入 `NaturalSpawner`，用 `@Unique` 缓存的 `ResourceKey<Structure> BETTER_FORTRESS` 复刻原版"下界砖上刷怪"规则
- 原版进度也被数据包覆盖：`data/minecraft/advancement/nether/find_fortress.json` 的 `location.structures` 同时接受 `minecraft:fortress` 与 `betterfortresses:fortress`

**(5) 物品展示框随机化（跨平台 API 差异的典型案例）**
- `world/ItemFrameProcessor.processEntity`：读实体 NBT 里 `Item.id` 作为"池标记"（stone_sword / iron_ingot / cobweb / apple / nether_wart / glowstone_dust），从 `ItemFrameChances` 取随机物品写回 NBT，含附魔书 `minecraft:stored_enchantments` 特例与 `ItemRotation` 随机旋转（`NeoForge/.../ItemFrameProcessor.java:36-137`）
- `world/ItemFrameChances.java:14-59` 单例 + 权重表，与外部 JSON `config/betterfortresses/{fabric|neoforge}-26_1/itemframes.json` 双向同步（`ConfigModule*.java:133-158` 用 yungsapi `JSON.createJsonFileFromObject` / `loadObjectFromJsonFile`）
- **平台差异导致同一类写两份**：Fabric 版 `extends StructureEntityProcessor`（yungsapi，6 参 `processEntity`，`ServerLevelAccessor`），NeoForge 版 `extends StructureProcessor`（新签名多一个 `StructureTemplate` 参数、`jspecify @Nullable`）；两边差异仅此，于是把反射入口收敛到服务接口——`module/StructureProcessorTypeModule.java:36` 用 `Services.PROCESSORS::itemFrameProcessorCodec` 注册 `ITEM_FRAME_PROCESSOR`

**(6) 配置：Common 存值 + 平台读取回填**
- Common 只有容器 `module/ConfigModule.java`（`CONFIG.general.disableVanillaFortresses = true`），平台侧 `bakeConfig()` 把真实配置写回（`ConfigModuleNeoForge.java:160-162`、`ConfigModuleFabric.java:160-162`）
- NeoForge：`ModConfigSpec`（`BNFConfigNeoForge` + `ConfigGeneralNeoForge`，选项带 `worldRestart()`），`container.registerConfig(COMMON, SPEC, "betterfortresses-neoforge-26_1.toml")`，监听 `ModConfigEvent` 与 `LevelEvent.Load` 时 bake + 重载 JSON
- Fabric：ClothConfig `AutoConfig.register(...Toml4jConfigSerializer::new)` + save/load listener，ModMenu 配置界面 `config/gui/BNFModMenu.java:12-17`，`ServerLifecycleEvents.SERVER_STARTED` 重载 JSON

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（全仓库无 payload / 网络通道代码）
- 数据驱动：结构内容 100% 在 `Common/src/main/resources/data/`（199 个文件：`structure/*.nbt` 169、`worldgen` 18、`loot_table` 9——beacon/extra/hall/keep/obsidian/puzzle/quarters/storage/worship、`tags` 3），代码侧只有处理器逻辑，无硬编码建筑
- datagen：**没有生成器**（`grep -rn "DataProvider|GatherDataEvent|DataGenerator"` 无命中），但 Gradle 管道已铺好：`NeoForge/build.gradle` 有 `data` run（`--mod betterfortresses --all --output src/generated/resources/ --existing src/main/resources/`）、`sourceSets.main.resources.srcDir 'src/generated/resources'`，`Common/build.gradle` 暴露 `commonGeneratedResources` 配置给加载器模块；`.gitattributes` 对 `src/generated/**` 锁 LF。结论：**资源是手写提交的，datagen 只是预留位**
- 资源内联展开：`buildSrc/.../multiloader-common.gradle` 的 `processResources` 用 `expandProps` 把 gradle.properties 的字段（`mod_id`、`version`、`mc_version_range`、`yungsapi_version`…）注入 `fabric.mod.json`、`neoforge.mods.toml`、`pack.mcmeta`、`*.mixins.json`

## 6. Mixin

- 配置：`Common/src/main/resources/betterfortresses.mixins.json`（`package: ...betterfortresses.mixin`、`required:true`、`defaultRequire:1`、`compatibilityLevel: JAVA_17`）；该文件同时被 `fabric.mod.json` 的 `mixins` 数组与 `neoforge.mods.toml` 的 `[[mixins]] config` 引用
- 代表类与注入点：
  - `mixin/DisableVanillaFortressesMixin.java:26` → `net.minecraft.world.level.chunk.ChunkGenerator#tryGenerateStructure`，`@At("HEAD")` + `cancellable`，按 `StructureType.FORTRESS` 拦截
  - `mixin/FixMobSpawningMixin.java:30` → `net.minecraft.world.level.NaturalSpawner#isInNetherFortressBounds`，`@At("HEAD")` + `cancellable`，`@Unique` 静态 `ResourceKey` 缓存
- 没有 mixinextras 用法（Common 只声明了 compileOnly 依赖）

## 7. 值得学的 5 条具体做法

1. **"占位标记方块 + Codec 配置的处理器"替代硬编码建筑细节**：`BridgeArchProcessor.java:37-110` 把 `PRISMARINE_STAIRS` 当锚点生成桥墩与连接墙，`PillarProcessor.java:57-79` 用 `orange_terracotta` 等锚点向下抽柱子；美术只在 NBT 里摆占位符。适用：地形自适应、可数据包调参的建筑。
2. **一个处理器类被 JSON 多次实例化**：`processor_list/main.json` 里 `betterfortresses:pillar_processor` 出现 4 次，只是参数（target_block / 权重 / altitude 条件）不同——参数全部走 `RecordCodecBuilder`（`PillarProcessor.java:27-34`）。适用：想让整合包作者自己调参数的机制。
3. **平台差异用 ServiceLoader + `META-INF/services` 收敛成 3 个接口**（`services/Services.java`、`IProcessorProvider`），而不是在业务类里写 if(loader)；例证就是 `ItemFrameProcessor` 因基类签名不同而必须写两份。适用：多加载器项目中"只有个别 API 不一致"的情况。
4. **对外兼容靠公共 tag + 数据包覆盖，代码里不出现第三方 mod 名**：`tags/worldgen/structure/better_fortresses.json` 被 morevillagers 的 tag 与 yungsapi 内置 tag 引用（`data/morevillagers/...`、`data/yungsapi/...`），原版进度用同名文件覆盖 criteria。适用：让第三方 mod 可选接入、且不想加依赖。
5. **高级玩家配置放进 `config/<modid>/<loader>-<version>/` 并自动生成教学 README**：`ConfigModuleFabric.java:41-127` / `ConfigModuleNeoForge.java:45-127` 建目录、写 README.txt、首次运行导出默认 `itemframes.json`，并在 `LevelEvent.Load` / `SERVER_STARTED` / 配置变更时重载。适用：结构 mod 里"数据包覆盖不到、又需要逐版本兼容"的随机权重表。

## 8. 公开 API（非库 mod，本条为分工说明）

本 mod 不是库/前置，而是 **YUNGs-API 的消费者**：它没有对外 API 包，扩展点全部来自 yungsapi —— `api.autoregister.AutoRegister` / `api.YungAutoRegister`（注解式注册与包扫描）、`api.world.structure.locate.LocateReplacer`（`/locate` 重定向，配套 lang key `"Use /locate structure betterfortresses:fortress instead!"`）、`api.world.randomize.ItemRandomizer` / `BlockStateRandomizer`、`world.processor.StructureEntityProcessor`、`world.structure.context.StructureContext`、`io.JSON`（单例 ↔ JSON 落盘）。结构侧同样复用 yungsapi 的注册名：结构类型 `yungsapi:yung_jigsaw`、结构集放置 `yungsapi:enhanced_random_spread`、池元素 `yungsapi:yung_single_element`、条件/地形适配 `yungsapi:depth|altitude|all_of|mod_loaded|custom|none`。**分工结论：YUNGs-API 负责 Jigsaw/条件/随机化/自动注册/定位重定向等通用机制，Better Fortresses 只写"处理器逻辑 + 数据 + 平台胶水"**——这是该系列所有 mod 的通用骨架。
