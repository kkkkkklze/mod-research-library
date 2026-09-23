# FoundationGames/Automobility 源码分析报告

## 1. 基本信息
- Mod 名：Automobility；mod_id：`automobility`；作者 FoundationGames；许可证 MIT（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）
- 目标：`gradle.properties` 中 `minecraft_version=1.21.1`、`neoforge_version=21.1.119`、`fabric_version=0.16.10`、`fabric_api_version=0.115.1+1.21.1`、`mod_version=0.5.0.h`；Mojang 官方映射 + Parchment `2024.11.17`
- 构建：Gradle Kotlin DSL，`settings.gradle.kts` 只 include `common`/`fabric`/`neoforge` 三个模块；common 也走 `fabric-loom`（`common/build.gradle.kts`，`accessWidenerPath = automobility.accesswidener`），NeoForge 模块走 NeoGradle。Mixinextras 0.3.5 + sponge-mixin 0.15.3
- 依赖：common 仅 `compileOnly org.jetbrains:annotations`、`de.javagl:obj:0.4.0`（OBJ 模型加载）、`mixinextras-common`；Fabric 可选 `jsonem`、`controlify`（`gradle.properties` 声明 `jsonem_version`、`controlify_version`），NeoForge 侧把 JsonEM 源码 vendored 进仓库（`neoforge/.../neoforge/vendored/jsonem/`）
- 资源：仓库内几乎没有 assets/data（全仓库非 java 文件仅 14 个），贴图/模型/音效不在本快照中（未确认）

## 2. 源码规模与包结构
- `.java` **182** 个，总 **14726** 行（实测 `find -name '*.java' | wc -l` / `-exec wc -l {} +`）
- 主要包（common 下 `io/github/foundationgames/automobility/`）：`item`(18)、`mixin`(14)、`block`(13)、`automobile/attachment/rear`(13)、`util`(12)、`automobile`(10)、`screen`(7)、`automobile/render`(7)、`automobile/attachment/front`(7)、`entity`(5)、`sound`(4)、`recipe`(3)、`util/network`(3)、`block/model`(3)；neoforge 侧另有 `neoforge/mixin/jsonem`(6)、`vendored/jsonem`(3)、`block/render`(4)；fabric 侧有 `fabric/resource`、`fabric/controller/controlify`、`fabric/block/render`
- 最大文件：`entity/AutomobileEntity.java` 2174 行、`automobile/AutomobileFrame.java` 411、`screen/AutoMechanicTableScreen.java` 368、`block/entity/AutomobileAssemblerBlockEntity.java` 360、`automobile/attachment/front/AutopilotFrontAttachment.java` 292、`automobile/render/AutomobileModels.java` 289、`block/AutopilotSignBlock.java` 269

## 3. 入口与注册
- 公共入口 `common/.../Automobility.java`：`init()` 依次 `AutomobilitySounds/Blocks/Items/Entities/Particles.init()` → `initOther()` → `CommonPackets.init()`（`Automobility.java:56-65`）
- **自研注册队列**：`util/RegistryQueue.register(registry, rl, supplier)` 返回 `Eventual<V>`（懒值容器，`get()/require()/create()`），各平台在 `RegisterEvent`/`ModInitializer` 中遍历队列并 `create()`。用法如 `AutomobilityEntities.AUTOMOBILE = RegistryQueue.register(BuiltInRegistries.ENTITY_TYPE, rl("automobile"), () -> Platform.get().entityType(...))`
- **平台抽象**：`platform/Platform.java` 定义 20+ 方法（`entityType/menuType/creativeTab/serverSendPacket/clientSendPacket/simpleParticleType/registerDataSerializer/controller`），由 `GlobalPlatformInstance.INSTANCE` 单例注入；Fabric/NeoForge 各实现一份 `FabricPlatform`/`NeoForgePlatform`，入口先 `XxxPlatform.init()` 再 `Automobility.init()`
- NeoForge 入口 `neoforge/.../AutomobilityNeoForge.java`：`@Mod` + `@EventBusSubscriber(bus = MOD)`，处理 `RegisterPayloadHandlersEvent`、`DataPackRegistryEvent.NewRegistry`、`GatherDataEvent`、`RegisterEvent`

## 4. 核心系统
1. **车辆实体（物理/驾驶）** — `entity/AutomobileEntity.java`（2174 行，继承裸 `Entity`）。`tick()`（:683）拆成 `positionTrackingTick / collisionStateTick / steeringTick / driftingTick / burnoutTick / movementTick / postMovementTick`，客户端每 4 tick（`CLIENT_SYNC_INTERVAL`）发一次 `ClientPackets.sendServerboundAutomobileSyncPacket`，服务端 `syncData()` 回 `sendClientboundAutomobileSyncPacket`。自定义 `collide(Vec3)`（:1808）实现坡道爬升：先 `collideBoundingBox`，若水平被挡则尝试"先上台阶再水平"路径比较 `horizontalDistanceSqr()` 取更优解。`Displacement` 内部类用 20 步/格扫点（`SCAN_STEPS_PER_BLOCK = 20`）+ 四元数 slerp 做悬挂姿态倾斜
2. **数据驱动部件注册表** — `AutomobileFrame`/`AutomobileWheel`/`AutomobileEngine` 均为 record，各自持有 `ResourceKey<Registry<T>> REGISTRY`、`Codec<T> DIRECT_CODEC`、`StreamCodec`、`DefaultRegistrar<T> BOOTSTRAP`，通过 `Automobility.initDynamicRegistries` 注册为**同步数据包注册表**（NeoForge `DataPackRegistryEvent`/Fabric `DynamicRegistries.registerSynced`）。部件即物品组件的值，用 `EntityDataSerializer`（`EntityDataSerializer.forValueType(STREAM_CODEC)`）同步到客户端
3. **数值统计派生** — `automobile/AutomobileStats.java:22-27`：`from(frame, wheel, engine)` 用加权公式把三个部件算成 acceleration/comfortableSpeed/handling/grip 四项（示例：`acceleration = ((1 - ((frame.weight() + wheel.size()) / 2)) + (2 * engine.torque()) / 3)`），再经 `DisplayStat` 供 GUI 展示——典型"部件组合出属性"的设计
4. **前后挂件系统** — `automobile/attachment/BaseAttachment`（`pos()/tick()/writeNbt()/readNbt()/updatePacketRequested(ServerPlayer)/canModify(BlockPos)`）派生 `FrontAttachment`/`RearAttachment`；13 种后挂件（`RearAttachmentType`：CHEST/BANNER_POST/BACKHOE/PAVER/SADDLED_BARREL…）+ 7 种前挂件（割草、收割、自动驾驶 `AutopilotFrontAttachment` 等）；`BaseAttachment.canModify` 用 `AutomobilityBlocks.ALLOW` 方块逐级判定修改权限；客户端动画用 SynchedEntityData `REAR_ATTACHMENT_YAW/REAR_ATTACHMENT_ANIMATION/FRONT_ATTACHMENT_ANIMATION`
5. **装配套件（Multiblock 交互）** — `block/entity/AutomobileAssemblerBlockEntity.java`（360 行）配合 `item/AutomobileComponentItem`（Frame/Wheel/Engine Item 分别是其子类）把部件"装配"成车辆；`block/SlopeBlock`+`block/model/SlopeBakedModel.java` 用自定义 `GeometryBuilder`（Fabric/NeoForge 各一份实现）在烘焙阶段生成斜面模型
6. **音效/控制器抽象** — `sound/AutomobilitySounds` + `entity/AutomobileEntity` 里的静态回调 `engineSound/skidSound/hornSound`（common 不依赖客户端类）；`controller/AutomobileController` 接口把"油门/刹车/漂移/震动"抽象出来，Fabric 侧 `controlify/ControlifyController` 接手柄，NeoForge 返回 `INCOMPATIBLE`

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**统一单包壳**。`util/network/AutomobilityPacketPayload` 是 `record(ResourceLocation id, byte[] bytes) implements CustomPacketPayload`，用 `StreamCodec.composite(ResourceLocation.STREAM_CODEC, ..., ByteBufCodecs.BYTE_ARRAY, ...)` 编解码；`CommonPackets.SERVERBOUND_HANDLERS`/`ClientPackets.CLIENTBOUND_HANDLERS` 是 `Map<ResourceLocation, 处理函数>`，按 id 分发（Fabric 注册 `ServerPlayNetworking.registerGlobalReceiver`，NeoForge 用 `reg.playBidirectional`）。手工写 `FriendlyByteBuf`：`AutomobileEntity.writeSyncStateData/readSyncStateData` 负责车辆状态（:217/:230），另有 attachments/banner_post/extendable_attachment/request_sync_automobile_components 等子协议
- 数据驱动：三个 datapack 注册表 + `recipe/AutoMechanicTableRecipe`（`Recipe<ContainerRecipeInput>` 自定义 RecipeType/Serializer，支持多 Ingredient 无序匹配与排序字段 `sortNum`/`sortId`）
- datagen：NeoForge `GatherDataEvent` 用 `RegistrySetBuilder` + `DatapackBuiltinEntriesProvider` 导出默认部件 JSON；`util/AutomobilityClientResourceDumper` 把动态注册表按 `codec.encode(..., JsonOps.INSTANCE)` dump 到游戏目录 `automobility_dump/`，供做资源包模板
- 无配置文件（纯数据包驱动）

## 6. Mixin
- 配置：`common/src/main/resources/automobility.mixins.json`（`refmap: automobility-refmap.json`）、`fabric/src/main/resources/automobility_fabric.mixins.json`、`neoforge/src/main/resources/automobility_neoforge.mixins.json`；另有 `automobility.accesswidener` + NeoForge `META-INF/accesstransformer.cfg`
- 代表性 mixin：
  - `mixin/EntityMixin.java`：`@Inject(method="stopRiding", at=@At("HEAD"))` 下车前强制一次最终同步
  - `mixin/LocalPlayerMixin.java`：`@Inject(method="rideTick", at=@At("TAIL"))` 把玩家按键注入车辆 `input`
  - `mixin/EntityRenderDispatcherMixin.java`：在 `render(...)` 的 `@At(value="INVOKE")` 前后成对注入，对车上实体做旋转/还原变换
  - `mixin/AbstractContainerMenuMixin.java`、`ItemCombinerMenuMixin.java`、`PlayerEnderChestContainerMixin.java`：全部在 `stillValid` 的 `@At("HEAD") cancellable = true`，让装在车上的方块 GUI 在移动时不被关闭（并配 `PlayerEnderChestContainerMixin implements EnderChestContainerDuck` 存"是否在车上"）
  - `mixin/ServerGamePacketListenerImplMixin.java`：在 `handlePlayerCommand` 中 `resetLastActionTime()` 之后注入，实现骑乘状态按 E 打开车上容器
  - `mixin/AABBMixin.java implements CollisionArea`、`ShovelItemAccess`、`KeyMappingAccess`、`SoundChannelAccess/SoundEngineMixin`（把车辆音效强制为全局声道）

## 7. 值得学的 5 条具体做法
1. **懒注册队列 + 平台单例**：`util/RegistryQueue.java` + `util/Eventual.java` + `platform/Platform.java`；common 只写一次注册代码，两个加载器各自"重放"队列，避免 DeferredRegister/Registry 双写
2. **统一包壳 + id 路由**：`AutomobilityPacketPayload(ResourceLocation id, byte[] bytes)` + `Map<ResourceLocation, Handler>`，加新协议只加一行注册与一个 handler，不必写新 payload 类
3. **原版私有状态用 AccessWidener/AT 而非 mixin 反射**：`automobility.accesswidener` 与 `accesstransformer.cfg` 暴露字段，仅在必须改行为时用 mixin
4. **移动方块 GUI 的 `stillValid` 重写**：`AbstractContainerMenuMixin` / `ItemCombinerMenuMixin` / `PlayerEnderChestContainerMixin` 三处 HEAD 注入，适用任何"可移动容器/载具上开 GUI"的需求
5. **注册表内容可导出**：`AutomobilityClientResourceDumper.dumpDynamicRegistry` 用 codec 反向编码成 JSON 写到 `gameDir/automobility_dump`，方便玩家做数据包（`Automobility.dumpDynamicRegistries` 暴露入口）

## 8. 扩展点 / API
- 数据包扩展：新增 `automobile_frame`/`automobile_wheel`/`automobile_engine` JSON 即可加载具（README 指向官方示例仓库 City-Vehicles-Example-Addon）
- `DefaultRegistrar`/`SimpleMapContentRegistry`（`util/`）提供无 Registry 键的内容注册（挂件类型）
- `AutomobileEntity.engineSound/skidSound/hornSound` 为 `public static Consumer<AutomobileEntity>` 函数式插槽，供扩展覆盖音效
