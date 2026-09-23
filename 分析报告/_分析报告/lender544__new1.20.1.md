# lender544/new1.20.1（L_Ender's Cataclysm）源码分析

## 1. 基本信息
- Mod 名 **L_Ender's Cataclysm**；mod_id `cataclysm`；作者 L_Ender（credits: 0dyss2y/HedwigOwls/gytator/danimodder/Gibb50）；包名 `com.github.L_Ender.cataclysm`。
- MC **1.20.1** + Forge **47.3.22**（`gradle.properties` `minecraft_version/forge_version`），Java 17，`gradle.properties` 版本 3.27 / `build.gradle` version `3.28-optimization`。
- Gradle：`net.minecraftforge.gradle` 6.0.x、`org.spongepowered.mixin` 0.7、`io.github.0ffz.github-packages`。
- 许可证 **CC BY-NC-ND 4.0**（禁止再分发/修改发布）。
- 关键依赖：**Lionfish API**（`curse.maven:lionfish-api-1001614`，作者自己的前置库，提供动画框架）、MixinExtras（jarJar 内嵌）、JEI/Curios 仅 compileOnly。依赖方向：Cataclysm → Lionfish API。

## 2. 源码规模与包结构
- **826 个 .java / 167,090 行**（`find . -name "*.java" | wc -l`、`-exec cat {} + | wc -l`）。
- 主要包（含直接子文件数）：`client/render/entity` 92、`client/model/entity` 70、`items` 61、`entity/projectile` 44、`client/render/layer` 44、`client/particle` 39、`client/animation` 34、`blocks` 28、`client/model/item` 23、`init` 20、`entity/etc` 15、`message` 14、`mixin` 13、`entity/effect` 13、`util` 10、`entity/AI` 9、`world/structures` 多项。
- 最大文件：`client/model/entity/Ignis_Model.java` 3551、`entity/AnimationMonster/BossMonsters/Ignis_Entity.java` 3318、`client/animation/Ancient_Remnant_Animation.java` 3287、`.../Scylla/Scylla_Entity.java` 3276、`client/model/entity/The_Leviathan_Model.java` 3175、`Maledictus_Entity.java` 2931。

## 3. 入口与注册
`Cataclysm.java:42` `@Mod(Cataclysm.MODID) @Mod.EventBusSubscriber`。构造函数 `Cataclysm.java:65-104` 里一次性注册 **17 个 DeferredRegister**（ModGroup/ModEffect/ModBlocks/ModParticle/ModStructures×2/ModTileentites/ModEntityDataSerializers/ModEntities/ModItems/ModSounds/ModRecipeSerializers/ModRecipeTypes/ModMenu/ModAttribute/ModStructurePlacementType/ModStructureProcessor），另有局部 `DeferredRegister<Codec<? extends BiomeModifier>>`（:98-103）。网络通道在静态块构造：
```java
NetworkRegistry.ChannelBuilder.named(new ResourceLocation(MODID,"main_channel"))
  .clientAcceptedVersions(version::equals)...simpleChannel();   // :54-62
```
`init/ModEntities.java:46` 用 `@Mod.EventBusSubscriber(bus = MOD)` 承接 `EntityAttributeCreationEvent` / `SpawnPlacementRegisterEvent`。注册风格：无 Registrate，全部手写 `DeferredRegister + RegistryObject`。

## 4. 核心系统
1. **动画驱动 AI**（旗舰）：`entity/AnimationMonster/LLibrary_Monster.java:19` implements `IAnimatedEntity`（来自 lionfishapi），`tick()` 只调 `AnimationHandler.INSTANCE.updateAnimations(this)`；`tickDeath()` 用 `getDeathAnimation()` 播死亡动画。12 个实体继承自 `Animation_Monsters`/`LLibrary_Monster`。配套 `entity/AnimationMonster/AI/AnimationGoal.java:10` 是"动画帧驱动行为"的 Goal 基类：`canUse()=test(entity.getAnimation())`，`interruptsAI` 时 `setFlags(MOVE,LOOK,JUMP)`，`requiresUpdateEveryTick()=true` —— 行为与动画状态机完全解耦。
2. **客户端骨骼关键帧动画**：`client/animation/*`（34 文件）用原版 `AnimationDefinition.Builder.withLength(...).looping()` + `AnimationChannel` + `Keyframe(KeyframeAnimations.degreeVec(...), CATMULLROM)` 按骨骼名（如 `"right_finger"`）描述，模型侧用 `CMModelLayers` 注册 LayerDefinition。
3. **增强 Jigsaw 结构**：`structures/jisaw/CataclysmJigsawManager.java:37`（自有 `addPieces` 返回 `Structure.GenerationStub`，内部 `Placer`/`FallbackPlacer`/`InteriorPlacer`/`DeadEndConnectorPlacer`，用 `poolPlaceOrder`+`placeOrderComparator` 控制拼块顺序），配合 `CataclysmPoolElement/FallbackPoolElement` 及 9 个 `No*InStructuresMixin`（NoOre/NoLakes/NoGeode…）清理原版特征。
4. **自定义移动与碰撞**：`entity/etc/` 下 `CMEntityMoveHelper`(extends `MoveControl`)、`MovementControllerCustomCollisions`+`ICustomCollisions`、`SmartBodyHelper2`、`FlightMoveController`/`FowardMoveController`，`entity/etc/path/` 的 `CMPathFinder`、`SemiAquaticPathNavigator`、`GroundPathNavigatorWide`、`DirectPathNavigator` 组成水生/巨型生物的寻路体系。
5. **Capability 技能系统**：`init/ModCapabilities.java:16-42` 用 `CapabilityManager.get(new CapabilityToken<>(){})` 取 token，`AttachCapabilitiesEvent<Entity>` 给所有 LivingEntity 挂 5 个 provider（Hook/Charge/RenderRush/TidalTentacle/Parry），每个都有配对同步包（MessageCharge/MessageHookFalling/MessageRenderRush/MessageTidalTentacle/MessageParryFrame）。
6. **配置**：`config/ConfigHolder.java` 用 `Pair<XxxConfig, ForgeConfigSpec>` 静态初始化 + `ModConfigEvent` 回调把值刷进静态字段，CLIENT/COMMON 双 spec。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：`Cataclysm.java:136-149` 手工 `registerMessage(packetsRegistered++, Cls, encode, decodeCtor, handler)`，**14 个包**用递增 int 当 discriminator；消息类自带 `FriendlyByteBuf` 构造（见 `message/MessageParticle.java:22`，用 `record QueuedParticle` 承载批量粒子）。工具方法 `sendMSGToServer/sendMSGToAll/sendNonLocal`（:111-123）。
- 数据驱动：`world/CMMobSpawnBiomeModifier.java`、`CMMobSpawnStructureModifier.java` 以 `Codec.unit/factory` + `DeferredRegister(BIOME_MODIFIER_SERIALIZERS)` 注册（id `cataclysm_mob_spawns`、`cataclysm_structure_spawns`）；结构模板由 `ModJigsaw.registerJigsawElements()` 在 `FMLCommonSetupEvent.enqueueWork` 注册。
- 配置：ForgeConfigSpec，产出 `cataclysm-client.toml` / `cataclysm-common.toml`（`Cataclysm.java:73-74`）。
- datagen：**无**（无 `GatherDataEvent`/`DataGenerator`，src 只有 `src/main`；仓库 resources 仅 `META-INF/` 与 `cataclysm.mixins.json`，assets/data 未入库）。

## 6. Mixin
配置 `src/main/resources/cataclysm.mixins.json`：14 个主 mixin + 2 个 client（`Client.HumanoidArmorLayerMixin`、`Client.HumanoidModelMixin`）+ 11 个 `accessor.*`（StructureTemplatePool/ListPoolElement/BoundingBox/Beardifier 等），`injectors.defaultRequire=1`。代表 hook：`LivingEntityMixin.java:51/56` `addEffect(...)` `@At("HEAD") cancellable`；`NoteBlockMixin.java:22` `getCustomSoundId` HEAD；`StructureTemplateMixin.java:18`。另用 `META-INF/accesstransformer.cfg` 公开 `ModelPart`、`LivingEntityRenderer.entityModel`、`Camera.move/setRotation`、`Mob.navigator` 等。

## 7. 值得学的 5 条做法
1. **动画即状态机**：实体只维护 `currentAnimation/animationTick`，AI 用 `AnimationGoal.test(animation)` 判断是否接管 → 新增技能只加 Animation + Goal。`entity/AnimationMonster/AI/AnimationGoal.java`、`LLibrary_Monster.java`。
2. **网络包按注册顺序编号**：`packetsRegistered++` 单计数器，避免手写 id 冲突；消息类提供 `encode/decodeCtor` 引用供 `registerMessage`。`Cataclysm.java:136`。
3. **Capability + 配对消息**：所有自定义状态（Hook/Charge/Parry）挂在 LivingEntity 上，每个状态自带一收一发消息，多人环境天然正确。`init/ModCapabilities.java`。
4. **用 mixin 批量"清除"原版地层特征**：9 个 `NoXxxInStructuresMixin` 复用于所有结构，一处开关控制全模组结构干净度。`mixin/`。
5. **扩展 Jigsaw 而不是自造结构系统**：复制并扩展原版 JigsawManager 的 Placer 分派（Fallback/Interior/DeadEnd），保留原版 JSON 结构数据格式，学习成本与兼容性都最优。`structures/jisaw/CataclysmJigsawManager.java`。

> 学习提示：动画框架本体在 **lender544/Lionfish-API**（本仓库 `_bulk` 内亦有 `lender544__Lionfish-API`），若只想借动画系统应直接看那边，而不是 Cataclysm 的调用侧。
