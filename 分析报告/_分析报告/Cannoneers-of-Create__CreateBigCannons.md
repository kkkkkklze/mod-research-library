# Cannoneers-of-Create/CreateBigCannons — Create Big Cannons

## 1. 基本信息

- Mod 名：Create Big Cannons；mod_id `createbigcannons`；作者 rbasamoyai（Cannoneers of Create）
- 目标：MC 1.21.1（`minecraft_version_range=[1.21.1,1.22)`）/ NeoForge 21.1.228（`neoforge_loader_version_range=[4,)`）；Java 21
- Gradle：ModDevGradle `net.neoforged.moddev 2.0.139`（`build.gradle:4`），Parchment `2024.11.17`；版本号由 CI 环境变量拼接（`build.gradle:26-28`，`5.11.7-dev+mc.1.21.1-build.N`）
- 许可证：MIT + CC BY-NC-SA（`LICENSE.md`、`gradle.properties:mod_license`）；mod 版本 5.11.7，group `com.rbasamoyai`
- Access Transformer：`src/main/resources/META-INF/accesstransformer.cfg`（放开 `ParticleEngine.register`、`LocalPlayer.handsBusy` 等），在 `build.gradle:78` 与 mods.toml 中声明
- 元数据：`src/main/templates/META-INF/neoforge.mods.toml`（含 `[[mixins]]`、`[[accessTransformers]]`、完整依赖表），经 `generateModMetadata` 展开
- 依赖：**必需** Create `6.0.10-280`（range `[6.0.7,6.1.0)`）、Ponder `1.0.82`、Registrate、Flywheel、`ritchiesprojectilelib 2.1.2`（弹道库，外部 API）；**可选** `copycats`、`framedblocks`、`curios`、`sable`、`simulated`

## 2. 源码规模与包结构

`find src -name '*.java' | wc -l` → 668；实测总行数 **61353**（`find … -exec wc -l {} \; | awk '{s+=$1}END{print s}'`）。是超大仓库，分析按"注册体系/网络/核心子系统/mixin/数据驱动"五块收敛。

主要包（第 3 层，括号=文件数）：`munitions/big_cannon`(93)、`effects/particles`(65，烟雾/冲击/爆炸粒子)、`cannons/big_cannons`(34)、`munitions/autocannon`(30)、`mixin/compat`(26)、`index`(26)、`network`(22)、`cannons/autocannon`(22)、`munitions/fuzes`(19)、`mixin/client`(16)、`munitions/config`(13)、`crafting/casting`(13)、`base`(13)、`remix`(12)、`config`(12)、`crafting/munition_assembly`(11)、`crafting/boring`(11)。

最大文件：`index/CBCBlocks.java`(1351)、`ponder/CannonLoadingScenes.java`(1240)、`ponder/CannonCraftingScenes.java`(1043)、`cannon_control/contraption/MountedBigCannonContraption.java`(790)、`remix/ContraptionRemix.java`(762)、`datagen/assets/CBCBuilderTransformers.java`(750)、`munitions/AbstractCannonProjectile.java`(664)、`crafting/casting/AbstractCannonCastBlockEntity.java`(663)、`cannon_control/cannon_mount/CannonMountBlockEntity.java`(591)、`cannon_control/carriage/CannonCarriageEntity.java`(563)。

## 3. 入口与注册

加载器入口 `CreateBigCannonsNeoForge.java:41`（`@Mod`），平台无关的 `CreateBigCannons.init()`（`CreateBigCannons.java:51`）做全部内容注册（Registrate + 各 `index/CBC*` 类）。关键点是**自建三张注册表**，在 `NewRegistryEvent` 中创建并 `sync(true)`（服务端→客户端同步）：

```java
evt.create(new RegistryBuilder<>(CBCRegistries.BLOCK_RECIPE_SERIALIZERS)
        .defaultKey(CreateBigCannons.resource("cannon_casting")).sync(true));
evt.create(new RegistryBuilder<>(CBCRegistries.BLOCK_RECIPE_TYPES)   ....sync(true));
evt.create(new RegistryBuilder<>(CBCRegistries.CANNON_CAST_SHAPES)   ....sync(true));
```
（`CreateBigCannonsNeoForge.java:90-102`），随后在 `RegisterEvent` 中按 `evt.getRegistryKey()` 分派填表（`:104-116`）。`index/` 下 26 个类按注册域拆分（`CBCBlocks/CBCItems/CBCBlockEntities/CBCEntityTypes/CBCDataComponents/CBCMenuTypes/CBCParticleTypes/CBCContraptionTypes/CBCArmInteractionPointTypes/CBCMunitionPropertiesHandlers`…）。`CBCContraptionTypes.java:21-31` 还额外把新类型写进 Create 的 `AllContraptionTypes.BY_LEGACY_NAME` 以便旧存档/NBT 兼容。

## 4. 核心系统

**a) 火炮 = Create Contraption**（本仓库核心思想）。`cannon_loading/` 提供 `CanLoadBigCannon` 接口（方法前缀 `createbigcannons$…`，如 `createbigcannons$getCannonLoadingColliders()`，`cannon_loading/CanLoadBigCannon.java:13-19`）与 `CBCModifiedContraptionRegistry`，让炮管能作为整体被装载/移动；`cannon_control/contraption/` 的 `MountedBigCannonContraption`(790)/`MountedAutocannonContraption`(587) 继承 Create 的 `Contraption`，`AbstractMountedCannonContraption` + `CBCContraptionRotationState` 负责旋转/后坐/仰角；运行时实体是 `PitchOrientedContraptionEntity`。配套 10+ 个 mixin 改 Create 的组装路径（`mixin/compat/create/ContraptionMixin`、`GantryContraptionMixin`、`PulleyContraptionMixin`、`ChassisBlockEntityMixin`…）。

**b) 炮座/控制** `cannon_control/`：`cannon_mount/CannonMountBlockEntity`(591)（可旋转炮架，含 `CannonMountVisual`、`CannonMountExtensionBlock` 扩展方块、`YawControllerBlock`）、`fixed_cannon_mount/`（固定炮座 + 值设置界面）、`carriage/CannonCarriageEntity`(563)（可驾驶炮车，`ServerboundCarriageWheelPacket` 驱动）、`ControlPitchContraption` / `ExtendsCannonMount` 抽象"谁控制谁"。炮座数值走 **JSON + 客户端同步**：`cannon_control/config/CannonMountPropertiesHandler` 读 `SimpleJsonResourceReloadListener`，用 `ClientboundSyncCannonMountPropertiesPacket` 下发。

**c) 弹药与弹道（数据驱动）** `munitions/`：`AbstractCannonProjectile`(664) 为所有炮弹基类；每种弹（`he_shell/ap_shell/fluid_shell/shrapnel/smoke_shell/mortar_stone/traffic_cone/…`）自带 `*PropertiesHandler`，集中登记在 `index/CBCMunitionPropertiesHandlers.java:17-30`；数值从 datapack `munition_properties/projectiles` 读取（`munitions/config/MunitionPropertiesHandler.java:35-68`，`SimpleJsonResourceReloadListener` + 每个类型一个 `PropertiesTypeHandler`），改完由 `ClientboundMunitionPropertiesPacket` 同步客户端。另有 `munitions/config/components` 与 `index/CBCDataComponents`（1.21 data component 存弹状态）、`munitions/fuzes/`(19，引信)。爆炸/伤害走 `remix/CustomExplosion`、`effects/particles/*`(65) 与自研 `ClientboundCBCExplodePacket`。

**d) 自研 BlockRecipe 体系（方块配方）** `crafting/`：`BlockRecipeType`/`BlockRecipeSerializer` 注册进自定义注册表，`crafting/casting/AbstractCannonCastBlockEntity`(663) 做"熔融金属浇铸炮管"（`CannonCastShape` 也是一张自建注册表，含 `fluidSize/diameter/castMould/isLarge/texturesCanConnect`，`crafting/casting/CannonCastShape.java:17-31`），配套 `crafting/boring`（钻孔）、`crafting/builtup`（拼接炮管）、`crafting/munition_assembly`、`crafting/incomplete`（未完成件）。同步由 `BlockRecipesManager.ClientboundBlockRecipesPacket` 完成。

**e) remix（对 Create 内部行为的重写层）** `remix/`：`ContraptionRemix`(762)、`CustomExplosion`、`LightingRemix`、`RotationPropagatorRemix`、`CustomBlockDamageDisplay`、`HasFragileContraption`、`GetItemStorage`。加上 `base/PartialBlockDamageManager`（自定义破坏进度，配 `ClientboundSendCustomBreakProgressPacket` 与存档数据 `PartialBlockDamageSaveData`）与 `base/multiple_kinetic_interface/HasMultipleKineticInterfaces`，集中放置"必须绕过 Create 实现"的能力，避免散落。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：自建 `network/CBCRootNetwork.java` 用 `Int2ObjectMap<StreamCodec>` + `Object2IntMap<Class>` 做 **varint 分发**，29 个包共用一个通道：`PACKET_STREAM_CODEC = ByteBufCodecs.VAR_INT.dispatch(getPacketId, getStreamCodec)`（`:29-30`）；NeoForge 侧只注册一个 `CBCNeoForgePacket`（record 包 `RootPacket`，`network/CBCNeoForgePacket.java:10-14`），`playBidirectional + HandlerThread.MAIN`。频道版本 `CBCRootNetwork.VERSION = "15.0.0"`（`:25`），玩家加入时发 `ClientboundCheckChannelVersionPacket` 做兼容校验（`:74-76`）。平台差异封装在 `multiloader/NetworkPlatform.java`（`sendToServer/sendToClientPlayer/sendToClientTracking/sendToClientAll`）——为将来多加载器预留。
- **配置**：`config/CBCConfigs.java:24-63` 完整照搬 Create 的 `AllConfigs` 模式（`ConfigBase` 子类 `CBCCfgClient/Common/Server` 三份，`registerAll(builder)`），并在注册时把数值灌回 Create：`BlockStressValues.IMPACTS.registerProvider(stress::getImpact)`。`onLoad/onReload` 由 `ModConfigEvent` 转调。
- **datagen**：`datagen/assets/CBCBuilderTransformers`(750) + `CBCLangGen` + `CBCBlockPartialsGen`；配方侧除了 Create 的 `CBCCraftingRecipeProvider/CBCCompactingRecipeProvider/CBCMillingRecipeProvider/CBCSequencedAssemblyRecipeProvider`，还有自研 `datagen/recipes/CannonCastRecipeProvider`、`DrillBoringRecipeProvider`、`BuiltUpHeatingRecipeProvider`；`datagen/CBCDatagenPlatform` 做平台分发。
- **兼容层**：`CBCModsNeoForge.java:19-52`（仿 Create 的 `Mods` 枚举，`LoadingModList` 判存在 + `executeIfInstalled(Supplier<Runnable>)` 惰性执行），`compat/` 下 `copycats/framedblocks/curios/sable/simulated` 各自独立子包，**类只在 mod 存在时才被加载**。

## 6. Mixin

配置 `src/main/resources/createbigcannons.mixins.json`，带 **自定义 mixin 插件** `"plugin": "rbasamoyai.createbigcannons.mixin.CBCMixinPlugin"`（`mixin/CBCMixinPlugin.java:25-31`）：`shouldApplyMixin` 里按 `CBCModsNeoForge.SABLE/SIMULATED.isLoaded()` 决定是否加载 `mixin.compat.sable.*`、`mixin.compat.simulated.*`（这是"可选依赖 mixin 不崩溃"的正解）。共 **49 个 mixin 类**，分三组：根包（`EntityMixin`、`ExplosionMixin`、`PlayerMixin`、`ServerLevelMixin`、`ServerEntityMixin`）、`mixin/client/`(16，如 `CameraMixin`、`LevelRendererMixin`、`SoundEngineMixin`、`GoggleOverlayRendererMixin`、`ScreenEffectRendererMixin`、`BufferBuilderAccessor`)、`mixin/compat/create/`(26 个，全部对准 Create：`ContraptionMixin`、`ContraptionColliderMixin`、`AbstractContraptionEntityMixin`、`BeltMovementHandlerMixin`、`FilterItemMixin`、`PulleyBlockMixin`/`PulleyBlockEntityMixin`/`PulleyContraptionMixin`、`MechanicalBearingBlockEntityMixin`、`rotation_propagation/RotationPropagatorMixin`/`KineticNetworkMixin` 等)，偏好 MixinExtras（`@WrapOperation/@WrapMethod/@ModifyExpressionValue` + `@Local`/`@Share`）。

## 7. 值得学的 5 条做法

1. **把"整台机器"做成 Create Contraption + 自定义 ContraptionType**：`index/CBCContraptionTypes.java:21-31`（注册进 `CreateBuiltInRegistries.CONTRAPTION_TYPE` 并写 `BY_LEGACY_NAME` 兼容旧名）+ `cannon_control/contraption/MountedBigCannonContraption`。适用场景：任何"用方块搭出来、要整体运动/被牵引"的结构（列车、机械臂、大型机械）。
2. **单通道 + varint 分发的网络栈**：`network/CBCRootNetwork.java:29-30,79-95` + `CBCNeoForgePacket`。适用场景：包数量 >15 的 mod，省掉几十个 `playBidirectional` 注册并集中管理协议版本。
3. **JSON 数据驱动 + 重载后主动下发客户端**：`munitions/config/MunitionPropertiesHandler`（`SimpleJsonResourceReloadListener`）+ `ClientboundMunitionPropertiesPacket`。适用场景：想让包作者/整合包通过 datapack 调数值（弹道、材料强度、炮座属性）。
4. **可选依赖的 mixin 用 `IMixinConfigPlugin` 门控**：`mixin/CBCMixinPlugin.java:25-31` + `CBCModsNeoForge.executeIfInstalled(...)`。适用场景：自己写与 Sable/Curios/FramedBlocks 等联动的附属，避免未装依赖时 ClassNotFound。
5. **集中"内部改写层"**：把必须绕过 Create/vanilla 私有实现的东西放进 `remix/`（`ContraptionRemix`、`LightingRemix`、`RotationPropagatorRemix`）+ `base/` 的管理器（`PartialBlockDamageManager`），而不是散在各处 mixin 里。适用场景：长期维护的大型附属，降低 Create 版本升级时的改动面。

## 8. 公开 API

非库模组，无独立发布的 API，但有几处**对外可用的扩展点**（接口 + 注册表）：

- `cannon_loading/CanLoadBigCannon`：自定义方块实现后可参与火炮装载；`CBCModifiedContraptionRegistry` 注册被修改的 contraption。
- `cannon_control/cannon_types/ICannonContraptionType` + `CannonContraptionTypeRegistry`：自定义炮种（口径/装填逻辑）。
- `CBCMunitionPropertiesHandlers` + 各 `*PropertiesHandler`：为自定义弹药接入 JSON 数值体系。
- `CBCRegistries.CANNON_CAST_SHAPES` 等自建注册表：第三方可通过注册表加炮管尺寸/方块配方类型。
- 兼容接入方式统一为 `compat/<mod>` 子包 + `CBCModsNeoForge` 枚举检测，见 `compat/copycats`、`compat/framedblocks`。
