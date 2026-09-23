# Raguto/AlexsMobs-1.21.1 源码分析报告

## 1. 基本信息

- 名称：Alex's Mobs（官方 mod 的 1.21.1 移植分支）；mod_id `alexsmobs`；原作者 AlexModGuy/Alexthe666，mods.toml 署名 `Alexthe668, Carro1001, Paint_Ninja, Raguto`；版本 1.22.17；许可证 **GPL-3.0**（`src/main/resources/META-INF/neoforge.mods.toml:3`）；git 分支 `master`，commit `27987e6`。
- 目标/加载器：MC **1.21.1** + NeoForge **21.1.203**，Java 21（`build.gradle:16`、`:54`），ModDevGradle 2.0.111 + Parchment 2024.07.28；用 AT 文件 `src/main/resources/META-INF/accesstransformer.cfg`。
- 依赖：**Citadel** `com.github.alexthe666.citadel:citadel-1.21.1:2.7.0`（jitpack，required，`versionRange="[2.6.0,)" ordering=AFTER`）——Citadel 是它的实际 API/框架来源；JEI 19.21.2.313（compileOnly api + runtimeOnly，无版本号写在 gradle.properties 里：`gradle.properties:4-5`）。
- 移植质量提示（实证）：`settings.gradle` 里写着 `includeBuild('C:\\Users\\Raguto\\Desktop\\MyModsSourceCode\\Citadel-1.21.1\\Citadel-1.21')`，硬编码作者本机绝对路径，**他人无法直接构建**；`build.gradle` 末尾有 `deploy` 任务把 jar 拷到 `D:/instances/NeoForge 1.21.1/minecraft/mods` 并 `tasks.named('build') { finalizedBy deploy }`。AT 文件里仍是 1.16 时代的 SRG 名（`f_110901_`、`m_20272_`、`ChunkBiomeContainer` 等），与 1.21.1 的 Mojang 映射不匹配，**是否生效未确认**。

## 2. 源码规模与包结构

- 751 个 `.java`，共 125039 行（`find … | wc -l`、`cat | wc -l`）。
- 包（到第 3 层）：`entity`(129)、`client/model`(122)、`client/render`(119)、`entity/ai`(111)、`item`(43)、`client/render/layer`(33)、`block`(29)、`misc`(25)、`network`(21)、`effect`(20)、`client/particle`(19)、`client/model/layered`(13)、`tileentity`(12)、`entity/util`(10)、`world`(8)。
- 最大文件：`entity/EntityMimicOctopus.java`(1257)、`EntityBaldEagle`(1235)、`EntityCrow`(1133)、`EntityLaviathan`(1089)、`EntityKangaroo`(1071)、`EntityElephant`(1067)、`EntityTarantulaHawk`(1032)、`EntityVoidWorm`(971)、`EntityCachalotWhale`(970)。
- 补充：本次工作区是 **sparse checkout**（`git sparse-checkout list` 仅含 `**/*.java`、`**/*.gradle`、`**/*.properties`、`**/*.toml` 等），所以 `src/main/resources/data/**`（646 个 JSON：loot_table/tags/advancement/recipe）与大部分 assets 不在磁盘上，是抓取方式所致，不是仓库缺失。

## 3. 入口与注册

主类 `src/main/java/com/github/alexthe666/alexsmobs/AlexsMobs.java:49`，`@Mod(MODID)`。构造器（`:60-106`）是典型的"大 mod 集中注册"写法：逐个 `XXXRegistry.DEF_REG.register(modBusEvent)`（AMBlockRegistry / AMEntityRegistry / AMItemRegistry / AMTileEntityRegistry / AMPointOfInterestRegistry / AMSoundRegistry / AMParticleRegistry / AMEffectRegistry / AMMenuRegistry / AMRecipeRegistry / AMLootRegistry / AMBannerRegistry / AMCreativeTabRegistry / AMDataComponents …），再注册 BiomeModifier/StructureModifier 的 `MapCodec`（`:92-98`）、`modContainer.registerConfig(ModConfig.Type.COMMON, ConfigHolder.COMMON_SPEC)`、`PROXY.init()`、`AMNetworking::register`，并用 `Calendar` 判断愚人节/万圣节的彩蛋开关。每个内容类自带 `DeferredRegister`，实体注册是"一行一个"内联 Builder：

```java
public static final DeferredHolder<EntityType<?>, EntityType<EntityGrizzlyBear>> GRIZZLY_BEAR =
    DEF_REG.register("grizzly_bear", () -> registerEntity(EntityType.Builder.of(EntityGrizzlyBear::new, MobCategory.CREATURE).sized(1.6F, 1.8F).setTrackingRange(10), "grizzly_bear"));
```

属性与刷怪放置走事件：`AMEntityRegistry::initializeAttributes`（`EntityAttributeCreationEvent`）与 `registerSpawnPlacements(RegisterSpawnPlacementsEvent)`。客户端/服务端分离用 `PROXY = unsafeRunForDist(() -> ClientProxy::new, () -> CommonProxy::new)`（`:56`、`:173-178`）。`AMEnchantmentRegistry` 被显式禁用（1.21 附魔数据驱动化），旧 `SimpleChannel` 网络已全部删除。

## 4. 核心系统

1. **实体 + 自定义 AI 库** `entity/`(129) + `entity/ai/`(111)：AI 是"每种生物专用 Goal + 通用 Goal 库"混合，且大量自定义移动控制器/寻路：`AdvancedPathNavigateNoTeleport`、`BoneSerpentPathNavigator`+`BoneSerpentNodeProcessor`、`AquaticMoveController`、`AnimalSwimMoveControllerSink`（配合 Citadel 的 `AdvancedPathNavigate`/`PathingStuckHandler`）。
2. **多部件（multipart）实体**：大型生物拆成多个真实 `EntityType`（`centipede_head/body/tail`、`bone_serpent_part`、`EntityCachalotPart`、`EntityAnacondaPart`），碰撞命中经客户端发 `MessageHurtMultipart`/`MessageInteractMultipart` 转发给父实体（`entity/EntityCachalotPart.java:52,76`、`entity/EntityCentipedeBody.java:167`），同时父实体实现 `isMultipartEntity()/getParts()`（`EntityCachalotWhale.java:819-824`）。
3. **Citadel 动画/模型体系**：`IAnimatedEntity`(71 处) + `Animation` + `AnimationHandler`(31) + 客户端 `ModelAnimator`(33)、`AdvancedEntityModel`(130)/`AdvancedModelBox`(121)，动画状态由服务端触发、Citadel 负责同步与播放——这是它"生物动作丰富"的基础，学习价值在于把动画与 AI 解耦。
4. **网络层** `network/AMNetworking.java:13-20+`：`event.registrar("1")` 后批量 `playToClient / playToServer / playBidirectional` 注册 20 个包；每个包是 record 实现 `CustomPacketPayload`，`StreamCodec.composite(ByteBufCodecs.VAR_INT/COMPOUND_TAG, …)`，静态 `handle/handleClient` 内 `context.enqueueWork`（`network/MessageSyncEntityData.java:27-48`，用 Citadel 的 `CitadelEntityData.setCitadelTag` 同步实体附加数据）。发送工具集中在主类 `sendMSGToServer/sendMSGToAll/sendNonLocal`（`AlexsMobs.java:142-156`）。
5. **数据驱动内容**：`misc/CapsidRecipeManager extends SimpleJsonResourceReloadListener`（GSON 手工解析 `capsid_recipes` 目录，转 ImmutableMap，`:22-45`，注册在 `ServerEvents` 的 `AddReloadListenerEvent`）；`misc/AMLootRegistry` 注册 4 个 `IGlobalLootModifier` 的 MapCodec（banana_drop/blossom_drop/ancient_dart/pigshoes）；`world/AMMobSpawnBiomeModifier`、`AMLeafcutterAntBiomeModifier`、`AMMobSpawnStructureModifier` 用 NeoForge 的 BiomeModifier/StructureModifier 实现**数据包驱动的刷怪**，配置结构来自 Citadel 的 `SpawnBiomeData/BiomeEntryType`。
6. **配置** `config/`(5 类)：`ConfigHolder.COMMON_SPEC` + 在 `ModConfigEvent.Loading/Reloading` 里 `AMConfig.bake(config)` 重烘焙静态字段（`AlexsMobs.java:124-139`），`BiomeConfig.init()` 同步初始化刷怪权重。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：如上，纯 NeoForge `PayloadRegistrar`（20 个包，双向/单向混用），无自研 channel 框架。
- 数据驱动：`capsid_recipes` 自定义 JSON 目录 + 原版 recipe/loot_table/advancement/tags（646 个 data JSON）+ Biome/Structure modifier JSON；大量 tag 常量集中在 `misc/AMTagRegistry`。
- 配置：NeoForge COMMON 配置 + 静态字段 bake 模式。
- datagen：`build.gradle:65-68` 配了 `data()` run（输出 `src/generated/resources/`，`sourceSets.main.resources` 含该目录），但仓库中 `src/generated/resources` 不存在，说明**没有提交 datagen 产物**，数据包 JSON 是手写/直接放在 `src/main/resources/data`。

## 6. Mixin

**完全没有**。`grep -rln spongepowered src/main/java` 无结果，无 `*.mixins.json`，mods.toml 里没有 `[[mixins]]`。所有侵入式改动靠：AccessTransformer（但内容疑似过期）、Citadel 提供的能力（动画/模型/寻路/`ICustomCollisions`/事件如 `EventGetOutlineColor`、`EventPosePlayerHand`）、以及 NeoForge 事件（`event/ServerEvents.java`，`@EventBusSubscriber` + 30 余个监听）。

## 7. 值得学的 5 条

1. 多部件大生物用"部件 = 真 EntityType + 命中转发包"实现多段碰撞（`entity/EntityCachalotPart.java:52,76`、`entity/util/AnacondaPartIndex.java`）——适用于巨兽/长条生物/机械臂。
2. 自定义数据驱动用 `SimpleJsonResourceReloadListener` + GSON 局部反序列化并容错（逐条 try/catch 记日志，`misc/CapsidRecipeManager.java:22-45`）——适用于结构简单、不值得上 Codec 的配置。
3. 刷怪规则做成 BiomeModifier/StructureModifier 的 `MapCodec`（`world/AMMobSpawnBiomeModifier.java`、`AlexsMobs.java:92-98`）——数据包可改生态刷怪，避免硬编码。
4. 掉落用 `IGlobalLootModifier` 的 MapCodec 注册（`misc/AMLootRegistry.java`）——比在实体里手写掉落更可配置。
5. 每个内容域自带 `DeferredRegister` 并在主类构造器集中 `register(bus)`，客户端逻辑靠 `unsafeRunForDist` 代理隔离（`AlexsMobs.java:56,69-90`）——适用于 100+ 实体的大规模注册管理。

## 8. 公开 API

本仓库不导出 API 包（无 `api/` 包，无对外文档）；对外扩展点全部依赖 **Citadel**（动画 `IAnimatedEntity`/`AnimationHandler`、模型 `AdvancedEntityModel`、寻路 raycoms、`CitadelEntityData` 实体附加数据、客户端事件）。想复用它的模式应参考 Citadel 而不是本项目。
