# TartaricAcid/TouhouLittleMaid 源码分析报告

## 1. 基本信息

- Mod 名：Touhou Little Maid（东方女仆）/ mod_id：`touhou_little_maid` / 作者：TartaricAcid 等 12 人
- 目标：**MC 1.21.1 + NeoForge**（`neo_version=21.1.219`，`loader_version_range=[4,)`），mod 版本 `1.5.3-neoforge+mc1.21.1`（`gradle.properties:19-27`）
- 许可证：`MIT / CC BY-NC-SA 4.0`（代码 MIT、资源非商用）
- Gradle 插件：`java-library`、`net.neoforged.moddev 2.0.95`、`com.gradleup.shadow 8.3.6`、`org.openrewrite.rewrite 7.32.2`（`build.gradle:2-17`）；Java 21 toolchain，`parchment 2024.11.17` 官方映射
- 编译依赖（重点）：**KubeJS**（compileOnly，`kubejs-neoforge:2101.7.2`）、Curios、Jade、Patchouli、Cloth Config、JEI、REI/EMI、Iron Chests、Carry On、Sophisticated Backpacks、Travelers Backpack、TACZ 枪械（jitpack）、Superb Warfare、SlashBlade；音频解码库经 `mcLib` 配置 + `shadowJar` 打入（vorbis-java-core、concentus、mp3spi、snakeyaml，`build.gradle:213-232,330`）
- 注意：仓库**内嵌了两份被改写到本模组命名空间的库源码**：`com.github.tartaricacid.touhoulittlemaid.geckolib3`（GeckoLib 分支，含 AnimatableEntity/AnimationState/PlayState/molang/keyframe/controller）与 `com.github.tartaricacid.simplebedrockmodel`（Bedrock 模型解析 + Sodium/Embeddium 顶点写入兼容）。同时 `runtimeOnly` 仍保留上游 `geckolib-neoforge:4.7.5`（`build.gradle:289`）——即"改包名内嵌 + 上游仅运行时"的双轨做法。

## 2. 源码规模与包结构

- `src/main/java` 下 **1498 个 .java，共 124,431 行**（`find src -name '*.java' -print0 | xargs -0 cat | wc -l`）；其中 1466 个在 `touhoulittlemaid`，32 个在 `simplebedrockmodel`
- 主要包（文件数）：`geckolib3/core` 129、`client/gui` 101、`ai/service` 92、`entity/ai` 86、`client/renderer` 65、`network/message` 58、`client/animation` 56、`geckolib3/geo` 35、`compat/kubejs` 34、`api/event` 33、`entity/task` 29、`ai/agent` 25、`ai/manager` 24、`inventory/container` 20、`compat/gun` 19、`molang/parser` 17、`event/maid` 17
- 最大文件：`entity/passive/EntityMaid.java` 2836 行、`api/game/gomoku/ZhiZhangAIService.java` 1733、`api/game/chess/Position.java` 1187、`api/game/xqwlight/Position.java` 1121、`client/gui/entity/model/AbstractModelGui.java` 825、`client/gui/entity/maid/ai/AIChatScreen.java` 820、`api/client/decoder/GifDecoder.java` 788、`client/gui/entity/maid/AbstractMaidContainerGui.java` 750、`client/resource/CustomPackLoader.java` 727、`client/animation/inner/MaidBaseAnimation.java` 707

## 3. 入口与注册

主类 `src/main/java/com/github/tartaricacid/touhoulittlemaid/TouhouLittleMaid.java:23`，构造函数式入口（NeoForge 1.21 风格）：

```java
@Mod(TouhouLittleMaid.MOD_ID)
public final class TouhouLittleMaid {
    public static final String MOD_ID = "touhou_little_maid";
    public static List<ILittleMaid> EXTENSIONS = Lists.newArrayList();  // 第三方扩展收集
    public TouhouLittleMaid(IEventBus modEventBus, ModContainer modContainer) {
        initRegister(modEventBus);
        registerConfiguration(modContainer);
        CommonDefaultPack.initCommonDefaultPack();
        AquacultureCompat.init(modEventBus);
    }
```

注册方式：**全量 DeferredRegister**，集中在 `init/` 包，由 `initRegister`（`:37-65`）一次性 register(eventBus)：`InitEntities`（ENTITY_TYPES / MEMORY_MODULE_TYPES / SENSOR_TYPES / SCHEDULES / DATA_SERIALIZERS / ACTIVITIES——脑记忆与 Activity 都自定义注册）、`InitBlocks`、`InitItems`、`InitCreativeTabs`、`InitContainer`、`InitSounds`、`InitRecipes`、`InitCommand.ARGUMENT_TYPE`、`InitPoi.POI_TYPES`、`InitTrigger.TRIGGERS`、`InitDataAttachment.ATTACHMENT_TYPES`、`InitDataComponent.DATA_COMPONENTS`、`InitLootModifier`。监听器通过 `eventBus.addListener(NetworkHandler::registerPacket)` 挂载，配置用 `modContainer.registerConfig(COMMON/SERVER, ...)`（`:67-70`）。客户端入口 `TouhouLittleMaidClient.java`。

第三方扩展机制：`api/ILittleMaid.java` 是唯一扩展入口，全 default 方法（`addMaidTask`、`addMaidBackpack`、`addExtraMaidBrain`、`registerTaskData`、`registerChatBubble`、`registerAITool`、`registerAIMaidContext`、`registerMagicCastingAnimation` 等），主类持有静态 `EXTENSIONS` 列表，各 Manager 在 `init()` 时遍历调用。

## 4. 核心系统

### 4.1 女仆实体与任务（Task）系统
- `entity/passive/EntityMaid.java:2836 行` 为巨型实体类；`entity/task/TaskManager.java` 用 `Map<ResourceLocation, IMaidTask>` + `List<IMaidTask>` 双结构管理任务，`init()` 内硬编码注册 20+ 内置任务（TaskAttack/TaskBowAttack/TaskNormalFarm/TaskSugarCane/TaskFishing/TaskBoardGames…），再遍历 `EXTENSIONS` 追加（`TaskManager.java:22-60`）
- 任务即"行为包"：每个 `IMaidTask` 提供 Brain 目标（`getBrainTask`）、工作/休息 Activity、搜索半径与维度（`EntityMaid.java:1864-1873` 委派 `task.searchDimension/Radius`）
- 任务私有数据用自研 **TaskDataKey** 机制：`entity/data/TaskDataRegister.java` 注册 `Codec<T>`，并提供 `writeSaveData/syncCodec` 双编解码器（存档 NBT 与网络同步格式可不同），`EntityMaid.getData(TaskDataKey)`（`:454`）读取，实现"任务可挂任意第三方数据而不改实体类"

### 4.2 原版 Brain 架构的深度定制
- `entity/ai/brain/MaidBrain.java` 定义 `getMemoryTypes()/getSensorTypes()`，并在 `registerBrainGoals` 中按"日程 schedule × 载具/非载具 × 工作/休息/恐慌"注册 9 组 Activity（`:56-73`）；自定义 `MaidSchedule`（ALL/NIGHT/DAY）+ 自定义 `Activity`/`SensorType` 注册进原版注册表
- `entity/ai/brain/task/` 55 个 Behavior 子类（MaidFarmPlantTask、MaidCollectHoneyTask、MaidExtinguishingTask、MaidFeedOwnerTask、MaidTridentTargetTask…），比原版村民 Brain 细化得多，可作为"用 Brain 写复杂职业 AI"的范本
- 扩展点：`api/entity/ai/IExtraMaidBrain` + `ExtraMaidBrainManager.EXTRA_MAID_BRAINS`，外部 mod 可注入 MemoryModuleType / SensorType / Activity（`MaidBrain.java:38-46` 用 forEach 汇总）

### 4.3 AI 聊天（LLM/TTS/STT）子系统
- 目录 `ai/`：`service/llm`（LLMSite/LLMClient/openai）、`service/tts`（fishaudio / gptsovits / minimax / player2 / siliconflow + system 本地实现）、`service/stt`、`manager/entity`（MaidAIChatManager、MaidAIChatData、HistoryMessagesCheck、grounded/summary）、`manager/setting`（CharacterSetting 角色卡 + SettingReader）
- Agent 化设计：`ai/agent/tool/ITool`、`ai/agent/tool/implement` 定义大模型可调用的原子游戏操作；`ai/agent/context`（`ContextCategory`/`GameContextRegister`）按分类按需投喂上下文，避免一次性塞入
- 站点序列化可扩展：`ai/service/SerializerRegister` + `ServiceType`，第三方可新增站点 API 类型；`ILittleMaid.registerAIChatSerializer` 暴露

### 4.4 客户端模型/动画的"数据驱动 + 多后端"
- `client/resource/CustomPackLoader.java:727 行`：从 `config/` 与资源目录扫描 **目录或 zip 包**，用 Gson 解析 `maid_model.json`（`MaidModelInfo`/`ChairModelInfo`/`CustomModelPack`），加载 Bedrock 模型（`simplebedrockmodel`）、贴图（`ZipPackTexture`/`FilePackTexture`）、自定义音效（`CustomSoundLoader`）——整个"女仆模型包"生态靠它
- 三套动画并存：`client/animation/inner/`（硬编码 Java 动画，`HardcodedAnimationManger`）、`client/animation/gecko/`（GeckoLib JSON 动画 + `condition/` 条件管理器 + `Priority` 优先级 + molang）、`client/animation/script/`（JS 自定义动画，`CustomJsAnimationManger`）
- 服务端侧 `entity/info/ServerCustomPackLoader.java` 与 `CommonDefaultPack` 负责把模型/音效 ID 同步给客户端（对应 `MaidModelPackage`/`SetMaidSoundIdPackage`）

### 4.5 网络层
- 单一注册点 `network/NetworkHandler.java`：`RegisterPayloadHandlersEvent` + `PayloadRegistrar`（version `"1.0.0"`），**逐条 playToServer/playToClient 注册 60+ 包**（`:20-82`），每条 `TYPE + STREAM_CODEC + ::handle` 三段式；工具方法 `sendToClientPlayer`（PacketDistributor.sendToPlayer）、`sendToNearby`（sendToPlayersTrackingEntityAndSelf / sendToPlayersNear + 距离参数）
- `network/message/ai/` 单独放 AI 相关包（OpenMaidAIChatPacket、SyncMaidAIDataPacket、SyncAISitesPacket、SaveLLMSitePacket、TTSAudioToClientPackage、TTSSystemAudioToClientPackage）；可见"注册早期无法决定是否装 YSM 所以后续补发"的注释，说明兼容分支的处理思路

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：见 4.5；包按业务拆文件（58 个 message 类），无自研框架，纯 NeoForge payload 体系
- 数据驱动：资源包/zip 模型包（4.4）；`src/main/resources/data/` 下含 `touhou_little_maid`、`minecraft`、`tacz`、`spawnanimations`、`twilightforest` 等命名空间，说明会**向其他 mod 的 data 命名空间注入**数据（如 TACZ 枪械、Twilight Forest 兼容）；`assets/.../ponder` 目录表明用 **Create Ponder** 做教程
- 配置：`config/GeneralConfig`（COMMON）+ `config/ServerConfig`（SERVER）两个 spec；另有大量运行时 GUI 配置存于女仆自身（MaidConfigPackage / MaidSubConfigPackage 同步）
- datagen：存在 `src/generated/resources`（build.gradle 把它加入 sourceSets），`runData` 配置齐全，`--mod touhou_little_maid --all`
- 兼容层：`compat/` 下 kubejs（KubeJSPlugin + 事件桥 + 注册桥 `MaidRegisterJS` + recipe schema）、gun（tacz/swarfare）、cloth（MenuIntegration）、jei/rei/emi、jade/top、curios、aquaculture
- KubeJS 接入方式值得抄：`compat/kubejs/ModKubeJSPlugin.java` 实现 `KubeJSPlugin` 的 `init/registerEvents/registerBindings/registerRecipeSchemas`，并用 `ModList.get().isLoaded("jade")` 条件注册扩展事件监听

## 6. Mixin

- 配置文件：`src/main/resources/touhou_little_maid.mixins.json`（`required: true`，`compatibilityLevel JAVA_17`，refmap 开启），指定 **`plugin: com.github.tartaricacid.touhoulittlemaid.mixin.plugin.MixinPlugin`**
- `MixinPlugin.java` 典型条件 mixin 写法：`getMixins()` 仅在 `InvTweaksCompat.isInstalled() && FMLEnvironment.dist == Dist.CLIENT` 时返回 `"client.compat.InvTweaksMixin"`——用 IMixinConfigPlugin 动态决定兼容 mixin 是否加载
- 代表性 mixin 与注入点：
  - `EntityMixin`：`positionRider` @HEAD（让女仆骑乘定位）、`move` @INVOKE(Entity.collide) 与 shift AFTER（碰撞处理）、`getBoundingBox` @RETURN
  - `MobInteractMixin`：`interact` @HEAD cancellable（拦截右键换女仆交互）
  - `PlayerMixin`：`removeVehicle` @HEAD、`wantsToStopRiding` @HEAD cancellable（禁止玩家从女仆载具上被踢下）
  - `ArrowMixin.tick()` @HEAD、`ThrownTridentMixin.onHitEntity` @HEAD、`MixinCrossbowItem.shootProjectile` @HEAD cancellable、`FishingHookPredicateMixin.matches` @RETURN cancellable
  - `NavigationMixin` + `NodeEvaluatorBurningCacher`/`BlockBurningCache`：`isBurningBlock` @HEAD/@RETURN **加缓存**，优化寻路热路径
  - `PersistentEntitySectionManagerMixin.tick` @INVOKE、`StructureTemplateMixin.createEntityIgnoreException` @RETURN cancellable（结构生成的实体兜底）
  - 客户端：`client.ClientPacketListenerMixin`、`client.HumanoidModelMixin`、`client.LanguageMixin`、`client.LivingEntityRendererMixin`、`client.ItemPropertiesMixin`
- `accessor/` 下 5 个 Accessor（ArrowAccessor、CropBlockAccessor、EntityAccessor、FenceGateBlockAccessor、LivingEntityAccessor）+ `META-INF/accesstransformer.cfg`

## 7. 值得学的 5 条具体做法

1. **能力全部收敛到一个 `ILittleMaid` 全 default 方法扩展入口**（`api/ILittleMaid.java`），主类持静态 `EXTENSIONS` 列表，各 Manager 初始化时遍历注入——加新扩展点不破坏旧实现。适用：任何需要第三方扩展的中大型 mod。
2. **Task 数据外挂：`TaskDataKey` + 双 Codec**（`entity/data/TaskDataRegister.java`，`register(key, saveCodec, syncCodec)`），让"任务私有数据"既能存档又可同步且格式可分离，实体类不膨胀。适用：给实体挂可扩展状态。
3. **IMixinConfigPlugin 动态载入兼容 mixin**（`mixin/plugin/MixinPlugin.java` getMixins 按 ModList 判断返回类名列表），避免为可选依赖单独出包。
4. **寻路热路径加缓存**（`NodeEvaluatorBurningCacher` + `BlockBurningCache` 注入 `isBurningBlock`），针对 Brain/寻路每 tick 调用的昂贵判断做 per-tick 缓存，是 AI 性能优化范本。
5. **内嵌库改写包名（jar-in-jar 的替代方案）**：把 GeckoLib 与 Bedrock 模型解析器源码搬进 `com.github.tartaricacid.*` 命名空间（`geckolib3/`、`simplebedrockmodel/`）避免与用户已装版本冲突，同时用 `shadowJar` + 自定义 `mcLib` configuration 打小体积依赖。适用：需要长期魔改某个前置库。

## 8. 库/API 视角补充（本模组不是纯库，但有对外 API）

- 公开 API 根包：`com.github.tartaricacid.touhoulittlemaid.api`（33 个事件类 + 20+ 接口）
- 扩展点接口：`api/ILittleMaid`（总入口）、`api/task/IMaidTask`、`api/entity/ai/IExtraMaidBrain`、`api/bauble/IMaidBauble`、`api/backpack/IMaidBackpack`、`api/entity/IMaid`、`api/block/*`、`api/entity/data/TaskDataKey`
- 事件总线：`api/event/`（MaidTaskEnableEvent、MaidAttackEvent、MaidHurtEvent、MaidTamedEvent、RegisterKubeJSEvent…）+ `api/event/client/`，通过 NeoForge EVENT_BUS 派发
- 外部接入：KubeJS（`compat/kubejs/`，可 JS 注册 task/事件/配方）、Jade/TOP 信息注入（`AddJadeInfoEvent`/`AddTopInfoEvent`）
