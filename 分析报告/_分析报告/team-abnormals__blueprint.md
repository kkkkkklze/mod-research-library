# team-abnormals/blueprint 源码分析报告

## 1. 基本信息

- Mod 名：Blueprint（库模组）；mod_id：`blueprint`
- 作者：Team Abnormals（SmellyModder / bageldotjpg / Jackson / abigailfails）
- 目标版本：MC 1.21.1，NeoForge 21.1.160（`gradle.properties:11-14`），Java 21
- Gradle 插件：`net.neoforged.gradle.userdev 7.0.182`、`java-library`、`maven-publish`、`me.modmuss50.mod-publish-plugin`（`build.gradle:2-7`）
- 许可证：ABNORMALS LICENSE 1.0（`LICENSE.txt:1-2`，非标准开源协议，按许可条款分发）
- 编译依赖：仅 `net.neoforged:neoforge`（`build.gradle:55-57`）。**它本身是 Team Abnormals 全系列 mod 的 API**，通过 `https://maven.teamabnormals.com` 分发，下游在 `neoforge.mods.toml` 里声明 `modId = "blueprint"`、`type = "required"`（`README.md` 开发者章节）
- 使用 accessTransformer（`src/main/resources/META-INF/accesstransformer.cfg`）与 mixin（`blueprint.mixins.json`）

## 2. 源码规模与包结构

- `src/main/java`：310 个 `.java`，28852 行；含 `src/test` 的模拟附属 mod 共 350 个文件、约 3 万行
- 主要包（含文件数）：
  - `core/`（主类、配置、注册）与 `core/registry`(11)、`core/util`(11)、`core/util/registry`(9)、`core/mixin`(23)+`core/mixin/client`(13)、`core/api`(8)、`core/api/conditions`(2)/`config`(9)/`loot`(3)
  - `core/endimator`(12)+子包（effects/interpolation/model/entity/util）——动画库
  - `core/data/client`(3)、`core/data/server`(3)+`tags`(4)——datagen
  - `core/sonar`(3)、`core/events`(6)、`core/other`(2)+`tags`(4)
  - `common/remolder`(17)+`data`(12)+`util`(5)——数据驱动的资源改写器
  - `common/world/modification`(3)+`chunk`/`structure`（多条件群系/结构替换）、`common/world/storage`（tracking/receiver）
  - `common/block`(6)+`chest`/`sign`/`thatch`、`common/entity`(4)、`common/network`(1)+`entity`(3)+`particle`(1)
  - `client/`(8) 及渲染/屏幕子包
- 最大文件：`common/remolder/util/DataExpression.java`(1431)、`common/remolder/data/DataVisitors.java`(1301)、`core/util/DataUtil.java`(736)、`core/util/BiomeUtil.java`(602)、`core/endimator/Endimation.java`(568)、`core/data/client/BlueprintBlockStateProvider.java`(501)、`common/remolder/data/JsonMolding.java`(462)、`core/endimator/Endimator.java`(418)

## 3. 入口与注册

主类 `core/Blueprint.java`（`@Mod(Blueprint.MOD_ID)`，`Blueprint.java:92-100`）。持有全局 `RegistryHelper`（`Blueprint.java:97`）和 `EndimationLoader`。

注册组织：`RegistryHelper` 不自己持有 DeferredRegister，而是维护 `Map<ResourceKey<? extends Registry<?>>, ISubRegistryHelper<?>> subHelpers`，默认装入 ITEM/BLOCK/SOUND_EVENT/BLOCK_ENTITY_TYPE/ENTITY_TYPE 五个子helper（`RegistryHelper.java:82-88`），`getSubHelper(registry)` 做泛型强转取回（`RegistryHelper.java:92-98`）。子helper 由 `AbstractSubRegistryHelper<T, R extends DeferredRegister<T>>` 实现，暴露 `getDeferredRegister()` 与 `register(IEventBus)`（`AbstractSubRegistryHelper.java:17-50`）。此外还有 `BlockSubRegistryHelper` / `ItemSubRegistryHelper` / `BlockEntitySubRegistryHelper` / `EntitySubRegistryHelper` / `SoundSubRegistryHelper` 等便捷方法（如 `collectBlocks(BlueprintChiseledBookShelfBlock.class)`，`Blueprint.java:166`）。

datapack 注册中心 `core/registry/BlueprintDataPackRegistries.java`，用 `DataPackRegistryEvent.NewRegistry` 注册两个自建注册表：`blueprint:structure_repaletters`、`blueprint:modded_biome_slices`（该文件:8-19）。其余注册（POI、placement modifier、density function、surface rule、condition codec、loot condition）散在 `core/registry/*` 中的 DeferredRegister。

## 4. 核心系统

**(1) Remolder 数据驱动资源改写**（最高学习价值）
- 职责：让数据包在资源加载时用 JSON 声明的"指令"改写任意资源（配方、模型、战利品表、实体数据等）。
- 文件：`common/remolder/RemolderLoader.java`、`Remolder.java`、`RemoldingCompiler.java`、`RemoldableResourceManager.java`、`data/MoldingTypes.java`
- 关键设计：`Remolder` 接口只有 `void remold(Molding molding)` + `codec()`（`Remolder.java:36-38`）；`CODEC` 是"map → VERBOSE_CODEC（dispatch 注册表），list → SequenceRemolder"的双形态 codec（`Remolder.java:20-34`）。`RemolderLoader.reloadRemolders` 用 `FileToIdConverter.json("remolders")` 扫描并以 `CompletableFuture.runAsync` 并行编译，条目按 `fileExtension → MoldingType → (直接路径 map / 谓词过滤器)` 索引（`RemolderLoader.java:62-123`），同路径条目按 `Entry.priority` 排序（`:237-240`）。
- 接入点：`core/mixin/MultiPackResourceManagerMixin.java` 对 `getResource` / `getResourceStack` / `listResources` / `listResourceStacks` 全部 `@At("RETURN") cancellable` 注入，把结果交给 `RemolderLoader` 改写（该文件:24-58）。
- 自定义类型可注册：`RemolderTypes.REGISTRY` 用 `dispatchStable(Remolder::codec, ...)`。

**(2) TrackedData 通用数据跟踪/同步**
- 文件：`common/world/storage/tracking/TrackedData.java`、`TrackedDataManager.java`、`SyncType.java`
- 设计：一个 `TrackedData<T>` 同时含 `MapCodec<T>`（NBT 存档）、`StreamCodec`（网络）、`Supplier<T> defaultValue`、`SyncType`、`persistent` 五个字段（`TrackedData.java:21-35`）。Builder 默认 `SyncType.TO_CLIENTS`，`enableSaving(codec)` 才落盘，`enablePersistence()` 让玩家死亡不清（`:132-146`）。实例在 `commonSetup` 注册：`TrackedDataManager.INSTANCE.registerData(location("slabfish_head"), SLABFISH_SETTINGS)`（`Blueprint.java:163`）。

**(3) Endimator 动画库**：`core/endimator/` 12 个文件。`Endimation` 是数据驱动关键帧动画（`Codec<Endimation> CODEC`，含 length / blendWeight / partKeyframes / effects，`Endimation.java:30-35`）；`Endimator.compile(ModelPart root)` 编译模型部件树（`Endimator.java:43`），`apply(Endimation, float time, ResetMode)` 播放，`ResetMode` 区分 RESET / UNAPPLY，避免同帧多个动画互相污染（`Endimator.java:257-260`）。支持 effects（sound/particle/shaking，`core/endimator/effects/`）与多种插值（`interpolation/`）。

**(4) 群系/结构数据驱动改写**：`common/world/modification/ModdedBiomeSource.java` 用 `MapCodec<BiomeSource> CODEC` 包装原版 `BiomeSource`，字段 `original_biome_source` + 按 slice 叠加（`:31-33`），注册为 `Registries.BIOME_SOURCE` 的 `blueprint:modded`（`Blueprint.java:200-202`）；配套 `structure/StructureRepaletterEntry`、`condition/StructureCondition`（数据包控制结构生成）。

**(5) 注册与内容辅助**：`core/api/WoodTypeRegistryHelper`（静态 `HashMap<String, WoodType>` 缓存 + `setupAtlas()`/`registerWoodTypes()`，`WoodTypeRegistryHelper.java:13-29`）、`core/api/BlockSetTypeRegistryHelper`、`core/api/BlueprintTrims.java`(365 行，自定义盔甲纹饰)、`core/util/item/CreativeModeTabContentsPopulator.java`(363 行，用事件向任意创造标签页插物品)。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：NeoForge 1.21 `RegisterPayloadHandlersEvent` + `PayloadRegistrar("1")`，5 个 payload 全部集中在一个方法里：`playToClient(UpdateEndimationPayload / TeleportEntityPayload / SpawnParticlesPayload / UpdateEntityDataPayload)`、`playToServer(UpdateSlabfishHatPayload)`（`Blueprint.java:238-245`）。发送侧集中在 `core/util/NetworkUtil.java`。
- 数据驱动：Remolder（见上）、两个自建 datapack registry、`core/api/conditions` 的配置条件（`ConfigValueCondition` + 7 个 `IConfigPredicate`：Equals/GreaterThan/GreaterThanOrEqual/LessThan/LessThanOrEqual/Contains/Matches，在 `Blueprint.java:103-109` 注册 codec）、`ConfigLootCondition` / `RaidCheckCondition` / `RandomDifficultyChanceCondition`。
- 配置：`core/BlueprintConfig.java`，注册 CLIENT 与 COMMON 两个 spec（`Blueprint.java:158-159`），`ModConfigEvent` 监听后手动 `BlueprintConfig.CLIENT.load()` 并向客户端推 slabfish 设置（`:120-137`）。
- datagen：`dataSetup(GatherDataEvent)` 统一注册 7 个 provider（tags ×4、recipe、datapack builtin、data map，`Blueprint.java:182-197`）；提供 `core/data/client/BlueprintBlockStateProvider.java`(501 行) 等可复用基类。`build.gradle:36-43` 的 `runs.data` 把 `--mod blueprint --all --output src/generated/resources` 写死，且用 `modSources` 把 `blueprint_test` 测试源集作为附加 mod 加载。

## 6. Mixin

配置：`src/main/resources/blueprint.mixins.json`（`required: true`、`compatibilityLevel: JAVA_21`、`refmap: blueprint.refmap.json`），主包 `com.teamabnormals.blueprint.core.mixin`，36 个 mixin 类（23 主 + 13 client）。

代表性：
- `MultiPackResourceManagerMixin` → 注入 `getResource` / `getResourceStack` / `listResources` / `listResourceStacks`（`@At("RETURN")`、cancellable），实现 Remolder 的资源改写；同时 `implements RemoldableResourceManager` 以挂载 `RemolderLoader` 实例（mixin 类加接口存状态，很值得学）
- `ServerEntityMixin`、`EntityMixin`、`ChickenMixin`、`RabbitMixin`、`ZombieMixin`——实体数据同步与变体
- `ReloadableServerResourcesMixin`、`SimpleJsonResourceReloadListenerMixin`、`ServerAdvancementManagerMixin`——数据包重载链钩子（对应 `core/events/SimpleJsonResourceListenerPreparedEvent.java`）
- `StructureMixin`/`StructureStartMixin`/`StructurePieceMixin`/`StructureTemplateMixin`——结构替换
- client 侧：`CameraMixin`、`MinecraftMixin`、`ModelPartMixin`（Endimator）、`PlayerRendererMixin`

## 7. 值得学的 5 条具体做法

1. **用 mixin 给原版类挂载自定义状态**：`MultiPackResourceManagerMixin implements RemoldableResourceManager`，把 RemolderLoader 实例存进被 mixin 的类，再用 `@At("RETURN") cancellable` 改写所有资源查询返回值。适用：需要拦截"所有资源读取"的场合。文件：`src/main/java/com/teamabnormals/blueprint/core/mixin/MultiPackResourceManagerMixin.java`
2. **一个数据对象同时携带"存档 codec + 网络 codec + syncType + default"**：`TrackedData` 把同步策略声明式化，调用方只写 Builder。适用：实体/玩家附加数据。文件：`src/main/java/com/teamabnormals/blueprint/common/world/storage/tracking/TrackedData.java:21-35`
3. **注册 helper 用 Map<RegistryKey, ISubRegistryHelper> 统一收口**：`REGISTRY_HELPER` 一个静态字段 + 泛型 `getSubHelper` 取回，避免每个 mod 各写一堆 DeferredRegister。适用：多注册表的中大型 mod。文件：`src/main/java/com/teamabnormals/blueprint/core/util/registry/RegistryHelper.java:30-134`
4. **codec 做"简写/详写"双形态自动分派**：`Remolder.CODEC` 用 `ops.getMapValues(input).result().isPresent()` 判断是 map 还是 list，分别走注册表派发或序列化。适用：为数据包作者提供"数组简写"。文件：`src/main/java/com/teamabnormals/blueprint/common/remolder/Remolder.java:20-34`
5. **开发期绕过 mod 依赖检查**：`areModsLoaded()` 先看系统属性 `blueprint.indev`（`build.gradle` 里对 client/server run 统一设 `-Dblueprint.indev=true`）为 true 就整体返回 true。适用：联动模块的单仓库联调。文件：`src/main/java/com/teamabnormals/blueprint/core/util/registry/AbstractSubRegistryHelper.java:58-66`；`build.gradle:20-22`

## 8. 公开 API（库模组）

- 扩展点根包：`com.teamabnormals.blueprint.core.api`（`BlueprintItemTier`、`BlueprintTrims`、`BlueprintRabbitVariants`、`EggLayer`、`IChestBlock`、`AdvancedRandomPos`、`WoodTypeRegistryHelper`、`BlockSetTypeRegistryHelper`）与 `core.api.conditions`（自定义合成/战利品条件）
- 工具 API：`core.util`（`DataUtil`、`BiomeUtil`、`BlockUtil`、`EntityUtil`、`NetworkUtil`、`TagUtil`、`TradeUtil`、`GenerationUtil`、`PropertyUtil`、`MathUtil`）、`core.util.item.CreativeModeTabContentsPopulator`、`core.util.modification`（`ResourceSelector` + 9 种 selector 实现，供 Remolder/结构替换复用）
- 事件：`core/events`（`AnimateTickEvents`、`EntityStepEvent`、`FallingBlockEvent`、`LoadThisClassEvent`、`SimpleEvent`、`SimpleJsonResourceListenerPreparedEvent`）——`SimpleEvent`/`LoadThisClassEvent` 是自建的最小事件总线风格扩展点
- 其他接入面：`client.screen.shaking`（屏幕震动 effect 注册）、`client.renderer.texture.atlas.BlueprintSpriteSources`（图集 sprite source 注册）、`common/world/modification/structure/condition`（结构条件扩展）
- 外部接入方式：Maven `com.teamabnormals:blueprint:<mc>-<ver>` + `neoforge.mods.toml` 声明依赖；仓库内含 `src/test/java` 的 `blueprint_test` 示例 mod（11 个注册类），是学习 API 用法的现成范本
