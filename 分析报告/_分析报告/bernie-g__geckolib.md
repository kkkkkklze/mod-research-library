# GeckoLib 源码分析报告（bernie-g/geckolib）

> 分析对象：`源码库\_参考仓库\_bulk\bernie-g__geckolib`（HEAD `d561f34 Update to 5.5.5`，分支 main）
> 快照说明：磁盘上 `fabric/src/main/resources/fabric.mod.json`、三个 loader 的 `META-INF/services/*`、`fabric/src/main/resources/geckolib.classtweaker`、`interface_injections.json` 等资源缺失（`git ls-files` 显示已跟踪），本报告中这些文件内容通过 `git show HEAD:<path>` 读取。

## 1. 基本信息

| 项 | 值 | 来源 |
| --- | --- | --- |
| Mod 名 / mod_id | GeckoLib 5 / `geckolib` | `gradle.properties`（modDisplayName、modId） |
| 版本 | 5.5.5 | `gradle/libs.versions.toml:4` |
| 作者 | Tslat；贡献者 Zigy, Witixin, Gecko | `gradle.properties` |
| 许可证 | MIT | `gradle.properties` modLicense、`LICENSE` |
| 目标 MC | `prefer = 26.2`，`strictly = "[26.2,)"`；Java 25；NeoForm `26.2-1` | `gradle/libs.versions.toml` |
| 加载器 | NeoForge `26.2.0.71`、Forge `65.1.3`(FML 65)、Fabric Loader `0.19.3` + Fabric API `0.158.0+26.2` | `gradle/libs.versions.toml` |
| Gradle 插件 | ModDevGradle 2.0.144、ForgeGradle `[7.0.36,)`、Loom `1.17-SNAPSHOT`、Minotaur 2.9.0、CurseForgeGradle 1.3.33 | `gradle/libs.versions.toml`、各模块 `build.gradle.kts` |
| Gradle / 构建 | Gradle 9.7.1 wrapper、Kotlin DSL、version catalog + `buildSrc` 约定插件 | `gradle/wrapper/gradle-wrapper.properties`、`buildSrc/src/main/kotlin/geckolib-convention.gradle.kts` |
| 编译依赖 | 仅 Mixin 0.8.7 + MixinExtras 0.5.4（common `compileOnly`）；**无任何第三方 mod 依赖** | `common/build.gradle.kts:20-22` |
| 对外分发 | 发布到 Cloudsmith maven（`geckolib3/geckolib`，无凭据时回落 `mavenLocal`），artifactId = `geckolib-<module>-<mcVersion>`；同时发布 Modrinth/CurseForge | `buildSrc/.../geckolib-convention.gradle.kts`（repositories/publishing）、各模块 publishing 块 |

它是"被依赖方"：本身不含任何注册物品/方块/实体，只提供 API + 渲染/网络/资源加载实现。

## 2. 源码规模与包结构

- `.java` 文件 **351** 个、总 **24354** 行；分模块：common 258、fabric 31、forge 31、neoforge 31（loader 三模块几乎只有 1:1 的 SPI 实现 + 事件类）。
- 主要包（第 3 层，括号为文件数，均含 `package-info.java`）：
  - `com.geckolib`(4)：GeckoLibConstants / GeckoLibServices / GeckoLibClientServices
  - `animatable`(7) + `animatable/client`(2)、`animatable/instance`(4)、`animatable/manager`(3)、`animatable/stateless`(8)
  - `animation`(4) + `animation/keyframehandler`(2)、`animation/object`(4)、`animation/state`(8)
  - `cache`(6) + `cache/animation`(6)、`cache/animation/keyframeevent`(5)、`cache/model`(7)、`cache/model/cuboid`(3)
  - `constant`(3) + `constant/dataticket`(3)；`event`(2)；`model`(6)；`object`(4)；`service`(5)；`util`(7)
  - `loading`(1) + `loading/definition/animation`(10)、`loading/definition/geometry`(15)、`loading/loader`(3)、`loading/math`(5) 及 `loading/math/function/{generic 13,limit 4,misc 4,random 5,round 9}`、`loading/math/value`(10)
  - `mixin/client`(12)、`mixin/common`(7)；`network`(1) + `network/packet/{blockentity,entity,singleton}`(各 5)
  - `renderer`(7) + `renderer/base`(7)、`renderer/internal`(2)、`renderer/layer`(3)、`renderer/layer/builtin`(7)、`renderer/specialty`(3)、`renderer/texture`(2)
- 最大文件：`loading/math/MathParser.java`(756)、`event/GeoRenderEvent.java`(626)、`animation/AnimationController.java`(602)、`renderer/layer/builtin/ItemArmorGeoLayer.java`(543)、`renderer/GeoReplacedEntityRenderer.java`(520)、`renderer/GeoEntityRenderer.java`(518)、`renderer/GeoArmorRenderer.java`(440)、`animation/object/EasingType.java`(380)、`loading/math/MolangQueries.java`(346)、`util/RenderUtil.java`(332)、`renderer/base/RenderPassInfo.java`(327)。

## 3. 入口与注册

注册内容极少：全局只注册 1 个数据组件 `stack_animatable_id`。

- NeoForge `neoforge/src/main/java/com/geckolib/GeckoLib.java:9-18`：
  ```java
  @Mod(GeckoLibConstants.MODID)
  public final class GeckoLib {
      public static final DeferredRegister.DataComponents DATA_COMPONENTS_REGISTER =
          DeferredRegister.createDataComponents(Registries.DATA_COMPONENT_TYPE, GeckoLibConstants.MODID);
      public GeckoLib(IEventBus modBus) {
          GeckoLibNetworkingNeoForge.init(modBus);   // 注册 RegisterPayloadHandlersEvent
          DATA_COMPONENTS_REGISTER.register(modBus);
          GeckoLibConstants.init();
      }
  }
  ```
- Forge `forge/.../GeckoLib.java`：`DeferredRegister.create(BuiltInRegistries.DATA_COMPONENT_TYPE.key(), MODID)` + `context.getModBusGroup()`；客户端 `GeckoLibClient` 用 `RegisterClientReloadListenersEvent` 挂 `GeckoLibResources`。
- Fabric `fabric/.../GeckoLib.java:8-13`（`ModInitializer`）：`GeckoLibConstants.init(); GeckoLibNetworking.init();`；`fabric/.../GeckoLibClient.java:15-18` 用 `ResourceLoader.get(PackType.CLIENT_RESOURCES).registerReloadListener(...)`。
- 数据组件定义在 `common/.../GeckoLibConstants.java:17`：`GeckoLibServices.PLATFORM.registerDataComponent("stack_animatable_id", b -> b.persistent(Codec.LONG).networkSynchronized(ByteBufCodecs.VAR_LONG))`。
- 无 Registrate；除上述 DeferredRegister 外无注册框架。

## 4. 核心系统

**（1）多加载器 SPI（ServiceLoader）** — `common/.../GeckoLibServices.java:14-15`、`GeckoLibClientServices.java`、`common/.../service/{GeckoLibPlatform,GeckoLibNetworking,GeckoLibEvents,GeckoLibClient}.java`。四个接口分别覆盖平台信息/注册、网络、渲染事件分发、客户端特化逻辑；每个 loader 提供实现类并通过 `META-INF/services/com.geckolib.service.*` 声明（如 `fabric/.../services/...GeckoLibPlatform -> com.geckolib.platform.GeckoLibFabric`）。`GeckoLibNetworking` 用 `static init()` + `default` 方法集中写死 12 个包的注册与发送逻辑，loader 只实现 `registerPacketInternal` / 三个 send 原语。

**（2）动画状态机** — `animatable/GeoAnimatable.java`（唯一必须实现的两个方法 `registerControllers`、`getAnimatableInstanceCache`）、`animatable/manager/AnimatableManager.java`（`ControllerRegistrar` 一次性注册，`tryTriggerAnimation` 惰性搜索）、`animation/AnimationController.java:41-70`（字段：`transitionTicks`、`animationSpeed`、`additiveAnimations`、`triggerableAnimations`、`playState`、`timeline`）、`animation/state/{ControllerState,AnimationPoint,BoneSnapshot,AnimationTimeline}.java`。设计点：控制器名唯一化后按名字放入 `Object2ObjectArrayMap`；触发式动画（`triggerableAnim(name, RawAnimation)`）与状态驱动动画（`AnimationStateHandler` 回调）共用同一控制器；`PlayState` + `transitionFromPoint` 实现过渡插值。

**（3）RenderState 数据管道** — `renderer/base/GeoRenderState.java`（`DataTicket<?>`→Object 的 map，`Impl` 为无原版 RenderState 时的兜底）、`constant/dataticket/DataTicket.java`、`renderer/base/GeoRendererInternals.java:73-129`。`fillRenderState` 固定顺序：`captureDefaultRenderState` → `addRenderData` → `GeoModel.addAdditionalStateData` → 各 `GeoRenderLayer.addRenderData` → 触发 `CompileRenderState` 事件 → `setMolangQueryValues` → `AnimationProcessor.extractControllerStates`。渲染线程只读 RenderState 中的 `ANIMATABLE_MANAGER`/`ANIMATABLE_INSTANCE_ID`，不再回查实体，天然线程安全。`RenderPassInfo.java` 额外提供 `addPerBoneRender`、`addBoneUpdater`、`addBonePositionListener`，`GeoRendererInternals.submitPerBoneRenderTasks` 按骨骼矩阵提交子任务。

**（4）资源烘焙** — `cache/GeckoLibResources.java`：实现 `PreparableReloadListener`，`prepareSharedState` 写入 `PendingResources` 状态键，`reload` 并行 `loadModels`/`loadAnimations`，`preparationBarrier::wait` 后再 `applyResources` 换掉静态 cache（`BakedModelCache`/`BakedAnimationCache`）；路径规整由 `SUFFIX_STRIPPER`（去 `.geo`/`.animation(s)`/`.json`）与 `PREFIX_STRIPPER`（去 `geckolib/`、`animations/`、`models/`）承担。加载器 SPI `loading/loader/GeckoLibLoader.java` 允许外部注册非 JSON 格式（`supportedExtensions` + `deserialize*`/`bake*`，`GeckoLibResources.addLoader` 前插入优先匹配）。Molang 表达式在 `loading/math/MathParser.java`（756 行，`compileMolang` 递归下降解析、`createWithDeduplication` 复用常量节点、`loading/math/function/*` 注册 40+ 内置函数、`MolangQueries` 定义 `query.*`）。

**（5）渲染器族** — `renderer/base/GeoRenderer.java` 与 `GeoRendererInternals.java` 用 sealed interface 拆分：内部接口放 `captureDefaultRenderState`/`fillRenderState`/`fire*Event` 等，公开面只留 `getGeoModel`、`getTextureLocation`、`getRenderColor`、`addRenderData`、`setMolangQueryValues`。6 个具体渲染器 `Geo{Entity,Block,Item,Armor,Object,ReplacedEntity}Renderer`，7 个内置 layer（`renderer/layer/builtin/`：AutoGlowing、BlockAndItem、ItemArmor、ItemInHand、TextureLayer、CustomBoneTexture），2 个 specialty（`DirectionalProjectileRenderer`、`DyeableGeoArmorRenderer`），加上 `renderer/texture/GeckoLibAnimatedTexture.java` 支持贴图序列帧动画。

**（6）ItemStack 级动画 id** — `animatable/GeoItem.java:41-57`（`getId`/`getOrAssignId` 走数据组件）、`cache/AnimatableIdCache.java`（`SavedData` + `SavedDataType` 持久自增 id）、`cache/SyncedSingletonAnimatableCache.java`（`IdentityHashMap` + 类名→实例映射供网络还原）。为让该组件不破坏 ItemStack 堆叠/同步，配了 6 个 common mixin（见下）在 parity 比较时忽略它，再在 `LivingEntityMixin#equipmentHasChanged` 单独恢复以便装备同步——`util/GeckoLibUtil.java` 的 `areComponentsMatchingIgnoringGeckoLibId` 是配套工具。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：共 12 个包（`network/packet/{blockentity,entity,singleton}` 各 4 个：AnimTrigger / StopTriggered / StatelessPlay / StatelessStop），统一实现 `network/packet/MultiloaderPacket.java`（`receiveMessage(@Nullable Player, Consumer<Runnable> workQueue)`，由加载器决定执行线程：NeoForge `context::enqueueWork`、Fabric `server/client()::execute`）。注册入口 `service/GeckoLibNetworking.java:35-51` 的 `static init()` 逐条登记 `CustomPacketPayload.Type` + `StreamCodec`；NeoForge 在 `RegisterPayloadHandlersEvent` 的 `registrar(MODID).optional()` 下注册（`neoforge/.../GeckoLibNetworkingNeoForge.java:25-31`），Fabric 用 `PayloadTypeRegistry.clientboundPlay()/serverboundPlay()`。发送侧三个原语 `sendToAllPlayersTrackingEntity`（NeoForge `PacketDistributor.sendToPlayersTrackingEntityAndSelf`）/`sendToAllPlayersTrackingBlock`（同 chunk）/`sendToPlayer`。触发链：`GeoEntity#triggerAnim`（`animatable/GeoEntity.java:29-46`）客户端直接改本地 `AnimatableManager`，服务端发 `EntityAnimTriggerPacket`。
- **数据驱动**：动画与模型完全资源驱动，根目录为 `geckolib/animations`、`geckolib/models`（`GeckoLibResources.ANIMATIONS_PATH/MODELS_PATH`），文件名经前后缀剥离后即资源 id，可被 `GeckoLibLoader` SPI 换成任意反序列化格式；模型/动画/贴图路径由 `GeoModel`/`DefaultedGeoModel`（`subtype()` 决定 `entity/`、`block/`、`item/` 等子目录与 `textures/<subtype>/`）推导。
- **配置**：无（`grep -rn "ModConfigSpec\|ConfigSpec"` 无命中）。
- **datagen**：无（`grep -rn "DataProvider\|GatherDataEvent\|DataGenerator"` 无命中）。

## 6. Mixin

配置：`common/src/main/resources/geckolib.mixins.json`（`required: true`、`package: com.geckolib.mixin`、`injectors.defaultRequire: 1`），三个 loader 均通过各自元数据/启动参数加载同一份（`mods.toml` 的 `[[mixins]] config`、`neoforge.mods.toml`、Forge run args `--mixin.config=geckolib.mixins.json`）。共 17 个 mixin 类（client 11 + common 6），大量使用 MixinExtras 0.5.4。

代表性：
- `mixin/client/TextureManagerMixin.java`：`@Mixin(value = TextureManager.class, priority = 2000)`，`@WrapOperation` 包住 `getTexture(Identifier)` 中的 `NEW SimpleTexture`，动画贴图换成 `GeckoLibAnimatedTexture`，再用 `@WrapWithCondition` 取消原生 `registerAndLoad`（避免二次注册）。
- `mixin/client/EntityRendererMixin.java`（priority 5000）：`@WrapMethod(method = "createRenderState(Lnet/minecraft/world/entity/Entity;F)Lnet/minecraft/client/renderer/entity/state/EntityRenderState;")` 供 `GeoRenderProvider` 介入原版渲染状态抽取。
- `mixin/client/EntityRenderStateMixin.java`：给 `EntityRenderState` "duck 接口"式实现 `GeoRenderState`，`@Unique private final Map<DataTicket<?>, Object> geckolib$data`，并把 `lightCoords`/`ageInTicks` 桥接为 `PACKED_LIGHT`/`TICK` 默认值。
- `mixin/client/ModelMixin.java`：`@Inject(method = "setupAnim", at = @At("TAIL"))` 调 `VanillaModelModifier.runModifierSetup`；`HumanoidModelMixin`/`PlayerModelMixin` 同点注入。
- `mixin/common/LivingEntityMixin.java`：`@WrapOperation(method = "equipmentHasChanged", target = ItemStack.matches)` 恢复 GeckoLib stack id 参与比较；配套 `ItemStackMixin#isSameItemSameComponents`、`HashedStackMixin#matches`、`AbstractContainerMenuMixin#triggerSlotListeners`、`SlotMixin#safeClone`、`SynchronizedRemoteSlotMixin#matches` 全部改为忽略该组件。
- 渲染状态接口注入在三个 loader 各有一套等价声明：NeoForge `common/.../interface_injections.json`（moddevgradle `interfaceInjectionData`）、Fabric `fabric/.../geckolib.classtweaker`（`transitive-inject-interface`）、Forge `forge/.../geckolib.facade.cfg`；AT 统一用 `common/.../META-INF/accesstransformer.cfg`（含 `PatchedDataComponentMap copyOnWrite`、`LevelRenderer levelRenderState` 等）。

## 7. 值得学的 5 条具体做法

1. **用 ServiceLoader 做零依赖的多加载器 SPI**：`GeckoLibServices`/`GeckoLibClientServices` 两个持有类 + `META-INF/services/com.geckolib.service.*`，common 代码只依赖接口，匹配不到时抛 `NullPointerException("Failed to load service for ...")` 便于定位。适用：所有跨加载器库。`common/.../GeckoLibServices.java:14-30`。
2. **构建期把 common 源码并入各 loader 源集，而不是 shadow/relocate**：`buildSrc/src/main/kotlin/geckolib-convention.gradle.kts` 的 `withCommonSource { }` 把 `:common` 的 `allSource` 加进 `compileJava`、并把 common 的 `resources` 通过 `ProcessResources` 合入 loader jar，同时用 `expand(expandProps)` 给 `fabric.mod.json`/`mods.toml`/`*.mixins.json` 注入版本号。适用：想同时支持 Forge/NeoForge/Fabric 且不想维护三套代码。同文件。
3. **把渲染所需数据全部打进 RenderState（DataTicket 键值袋 + duck 接口）**：`GeoRenderState` + `EntityRenderStateMixin` 让原版 RenderState 携带动画数据，`fillRenderState` 里固定顺序采集默认值/自定义值/layer 值/事件值。适用：任何需要在 1.21.9+ 提交式渲染管线里做自定义渲染、且想避免渲染线程访问实体状态的场景。`common/.../renderer/base/GeoRenderState.java`、`GeoRendererInternals.java:115-129`。
4. **资源格式留 SPI 口子 + 每轮 reload 建解析器**：`GeckoLibLoader`（`supportedExtensions`/`deserialize*`/`bake*`）+ `GeckoLibUtil.addResourceLoader(predicate, loader)` 前插匹配，配合 `MathParser.createWithDeduplication()` 在每次 reload 内复用常量节点、`PendingResources` 状态键让 `prepareSharedState`/`reload` 分离。适用：数据驱动 mod 想支持自有格式（如 NBT/二进制模型）或想在烘焙阶段做全局去重。`common/.../cache/GeckoLibResources.java:80-136`。
5. **给 ItemStack 分配持久化动画 id，并用 mixin 抵消它带来的堆叠副作用**：`stack_animatable_id` 数据组件 + `AnimatableIdCache`（`SavedData` 自增 id），再在 6 处 parity 比较中忽略该组件、唯独 `equipmentHasChanged` 放行，实现"每个 ItemStack 独立动画状态"且不破坏堆叠。适用：任何需要在物品 NBT/组件上挂运行时状态又不想影响堆叠与同步的 mod。`common/.../cache/AnimatableIdCache.java`、`common/.../mixin/common/*`。

## 8. 公开 API / 扩展点 / 外部 mod 接入方式

- **接入方式**：依赖 Cloudsmith maven（`https://dl.cloudsmith.io/public/geckolib3/geckolib/maven/`，group `com.geckolib`，artifactId `geckolib-<common|fabric|forge|neoforge>-<mcVersion>`），运行时仍需 GeckoLib 本体 jar 存在（非 jar-in-jar 内嵌）；文档在 wiki.geckolib.com，示例仓库通过 `com.geckolib.example:*` 坐标发布并用 `localRuntimeOnly` 本地调试（各模块 build 中注释保留）。
- **公开 API 包**：`com.geckolib.animatable`（`GeoAnimatable` 及其 `Geo{Entity,BlockEntity,Item,ReplacedEntity}`、`SingletonGeoAnimatable`、`animatable/stateless/StatelessAnimatable`）、`com.geckolib.animatable.client.GeoRenderProvider`（物品/盔甲渲染器提供者，等价于 Forge `IClientItemExtensions`）、`com.geckolib.animation`（`AnimationController`、`RawAnimation`、`animation/object/{EasingType,LoopType,PlayState}`）、`com.geckolib.model`（`GeoModel`、`Defaulted*GeoModel`）、`com.geckolib.renderer`（6 个渲染器 + `renderer/layer/GeoRenderLayer` 扩展点 + `renderer/specialty/*`）、`com.geckolib.constant.dataticket.DataTicket`（自定义渲染数据键）、`com.geckolib.object.VanillaModelModifier`、`com.geckolib.util.GeckoLibUtil`。
- **扩展点清单**：
  - 动画控制器注册：`GeoAnimatable#registerControllers(AnimatableManager.ControllerRegistrar)`；
  - 缓动/循环自定义：`GeckoLibUtil.addCustomEasingType` / `addCustomSimpleEasingType` / `addCustomLoopType`（须在 mod 构造期调用）；
  - 资源格式：`GeckoLibUtil.addResourceLoader(GeckoLibLoader.Predicate, GeckoLibLoader<?>)`；
  - 逐帧变量：`GeoRenderer#setMolangQueryValues` + `MathParser.setVariable/registerVariable`；
  - 渲染钩子：`GeoRenderLayer#preRender/submitRenderTask/addRenderData/addPerBoneRender`，以及事件接口 `com.geckolib.event.GeoRenderEvent` 的三个阶段 `CompileRenderLayers`/`CompileRenderState`/`Pre`（六个类别：Entity/Block/Item/Armor/ReplacedEntity/Object），loader 侧具体事件类在 `com.geckolib.event.<类别>`（如 NeoForge 订阅 `com.geckolib.event.entity.GeoEntityPreRenderEvent`，Forge 版本额外自带静态 `BUS`）。
  - 键位事件回调：`AnimationController#setSoundKeyframeHandler/setParticleKeyframeHandler/setCustomInstructionKeyframeHandler`（对应动画 JSON 的 sound/particle 指令帧）。

---

# 补充：GeckoLib **4.x**（1.20.1 分支 / v4.8.4）精读与 4.x↔5.x 对比

> 追加时间 2026-09-16。针对本机实际使用的版本线（Forge 1.20.1，项目侧 GeckoLib 4.4.9 级别）。
> 数据来源：同一克隆仓库的 `origin/1.20.1` 分支（`git fetch --depth 1 origin 1.20.1:refs/remotes/origin/1.20.1`），文件按 `git show origin/1.20.1:<path>` 读取；该分支 `gradle.properties`：`version=4.8.4`、`minecraft_version=1.20.1`、`mod_display_name=GeckoLib 4`。
> 规模：4.x 分支 339 个 .java（5.x main 为 351 个）。

## A. 模块布局：4.x 的"复制式多加载器" vs 5.x 的 SPI

| 方面 | **4.x（1.20.1）** | 5.x（main，MC 26.2） |
|---|---|---|
| 包名 | `software.bernie.geckolib` | `com.geckolib` |
| 模块 | `core/`(44) + `Forge/`(145) + `Fabric/`(150) | `common/`(258) + fabric/forge/neoforge 各 31 |
| 平台差异处理 | **各加载器各写一份**（loading/network/renderer/cache/model/util/mixins 都是 `Forge/…` 与 `Fabric/…` 两条平行实现） | 收敛为 ServiceLoader SPI：`GeckoLibPlatform / GeckoLibNetworking / GeckoLibEvents / GeckoLibClient` + `META-INF/services` |
| 共享层内容 | 仅纯逻辑：`core/{animation, keyframe, molang, animatable, object, state}` | 全部逻辑进 common，loader 只留 SPI 实现 + 事件类 |

**4.x `core/` 模块细分**：`keyframe(15)` / `molang(9)` / `animation(8)` / `animatable(7)` / `object(4: Axis, Color, DataTicket, PlayState)` / `state(1)`。
**平台模块（Forge）**：`loading(42: FileLoader, json/, object/)`、`network(35: GeckoLibNetwork, SerializableDataTicket, packet/)`、`renderer(32)`、`animatable(25: GeoEntity/GeoItem/GeoBlockEntity/GeoReplacedEntity/SingletonGeoAnimatable/stateless)`、`cache(20: AnimatableIdCache, GeckoLibCache, object/, texture/)`、`model(12: GeoModel + Defaulted{Entity,Block,Item}GeoModel + data/)`、`util(10)`、`mixins(7 Fabric / 3 Forge)`、`constant(4)`、`resource(2)`、`event(2)`。

→ **教训（写库模组的路线图）**：跨加载器库的常见演进是"先复制、后抽 SPI"。抽 SPI 的前提是先说清"哪些是平台相关"——网络线程模型、事件总线、注册表、资源重载。4.x 的 Forge/Fabric 包差异主要在 loading/network/renderer 三处，5.x 的 4 个 SPI 接口正好对应这三处 + 客户端特化。

## B. `GeoAnimatable` 契约（4.x 必需实现的两个方法）

`core/animatable/GeoAnimatable.java`：

```java
public interface GeoAnimatable {
    void registerControllers(AnimatableManager.ControllerRegistrar controllers);  // 注册控制器
    AnimatableInstanceCache getAnimatableInstanceCache();                          // 实例缓存（GeckoLibUtil#createCache）
    default double getBoneResetTime() { return 5; }        // 无动画骨骼回正的耗时
    default boolean shouldPlayAnimsWhileGamePaused() { return false; }
    // + getTick(object)：为"不 tick 的自定义对象"提供动画时间基准
}
```

配套约定（写在接口注释里，值得照抄给自家 API 写文档）：**一个控制器同一时刻只能播一个动画**，要并发就注册多个控制器；多个动画若操作同一骨骼（或父子骨骼）会互相覆盖。

## C. `AnimationController` 内部结构（4.x）

字段（`core/animation/AnimationController.java:37-68`）：
`animatable` / `name` / `stateHandler`（状态回调）· `boneAnimationQueues` + `boneSnapshots`（**按骨骼名**的动画队列与快照）· `animationQueue`（`AnimationProcessor.QueuedAnimation`）· `isJustStarting`/`needsAnimationReload`/`shouldResetTick`/`justStartedTransition`（状态位）· **三个关键帧处理器** `soundKeyframeHandler`/`particleKeyframeHandler`/`customKeyframeHandler` · `triggerableAnimations` + `triggeredAnimation` + `handlingTriggeredAnimations`（触发式动画）· `transitionLength`（过渡）· `currentRawAnimation`/`currentAnimation`/`animationState(State)` · `tickOffset`/`lastPollTime` · `animationSpeedModifier`/`overrideEasingTypeFunction` · `lastModel(CoreGeoModel<T>)`。
4 个构造器：`(animatable, handler)` / `(animatable, name, handler)` / `(animatable, transitionTicks, handler)` / `(animatable, name, transitionTicks, handler)`。

设计点：
- **控制器 = 一条动画通道**；`name` 用于网络同步与触发（`triggerAnim(controllerName, animName)`）。
- **状态位驱动**而非每帧重建队列：`needsAnimationReload`/`shouldResetTick` 等把"何时重算"显式化，是本库性能好的原因之一。
- 动画速度与缓动可**按 animatable 动态覆写**（`Function<T, Double>` / `Function<T, EasingType>` 字段）——不用为"某个实体要慢放"新建控制器。

## D. 关键帧体系（`core/keyframe`，15 类）——**对外最重要的扩展点**

- 数据面：`Keyframe` / `KeyframeLocation` / `KeyframeStack` / `AnimationPoint` + `AnimationPointQueue` / `BoneAnimation` + `BoneAnimationQueue`（把"某骨骼在某时刻的目标值"流水线化）。
- 事件面：`event/KeyFrameEvent` + `event/data/{Sound, Particle, CustomInstruction}KeyframeData`（对应 `KeyFrameEvent` 家族的 `SoundKeyframeEvent` / `ParticleKeyframeEvent` / `CustomInstructionKeyframeEvent`）。
- 用法：`controller.setSoundKeyframeHandler(...)` / `setParticleKeyframeHandler(...)` / `setCustomInstructionKeyframeHandler(...)`——**动画时间轴里写 `sound`/`particle`/`custom` 关键帧即可在代码里收事件**。
- 衔接：ParticleStorm 就是接在这一层的（`mixed/IPSParticleKeyframeData` 等接口 + mixin 读取粒子关键帧数据，把基岩粒子挂在骨骼上；见 `westernat__ParticleStorm.md` 第 9 节）。同一个 mod（BleedZone7）同时用 GeckoLib + ParticleStorm，说明"粒子关键帧 + 挂点"是这两库的标准协作方式。

## E. Molang（4.x 自带引擎）

`core/molang/`：`MolangParser`（求值）/ `MolangQueries`（`query.*` 定义）/ `LazyVariable`（惰性变量）/ `expressions/` / `functions/`。
5.x 把它重构为 `loading/math/MathParser.java`（756 行，递归下降 + 常量去重）+ `loading/math/function/*`（40+ 内置函数）+ `MolangQueries`。
→ 项目里若要暴露自定义变量：4.x 走 `MolangParser` 的注册入口；跨库场景下（如 ParticleStorm）则用事件（`RegisterMolangQueriesEvent`）来贡献 query。

## F. 网络（4.x 每加载器 15 个包 → 5.x 收敛为 12）

4.x 包清单（Forge 与 Fabric 各一份）：`AnimDataSyncPacket`、`AnimTriggerPacket`、`BlockEntityAnimDataSyncPacket`、`BlockEntityAnimTriggerPacket`、`EntityAnimDataSyncPacket`、`EntityAnimTriggerPacket`、`Stateless*PlayAnimPacket`/`StopAnimPacket`（Entity/BlockEntity/Singleton 共 6）、`StopTriggered*Packet`（Entity/BlockEntity/Singleton 共 3），外加 `GeckoLibNetwork`（注册与发送）与 `SerializableDataTicket`。
5.x 改为 `network/packet/{blockentity,entity,singleton}` 各 4 个 + 统一 `MultiloaderPacket`（`receiveMessage` 由加载器决定线程）。
→ 迁移点：4.x 直接 `SimpleChannel`；5.x 用 `CustomPacketPayload`+`StreamCodec`。

## G. Mixin（4.x：Fabric 7 / Forge 3）

Forge 侧 3 个：`mixin/client/TextureManagerMixin`、`mixin/common/AbstractContainerMenuMixin`、`mixin/common/ItemStackMixin`；Fabric 侧 7 个（多出 `ItemRendererAccessor`、`MixinItemRenderer`、`MixinHumanoidArmorLayer`、`LivingEntityMixin` 等）。
用途与 5.x 一致：**为"物品级动画 id"（数据组件/容器比较）打补丁**、贴图与渲染钩子。5.x 对应 client 12 + common 7（含 parity 忽略、装备同步恢复等，见主报告第 6 节）。

## H. 对 1.20.1 工程（GeckoLib 4.4.9）的实践结论

1. **1.20.1 分支已到 4.8.4**，与 4.4.9 同代（4.x），修 bug 升级可直接换版本，无需改代码结构。
2. **4.x → 5.x 是大版本迁移**（包名 `software.bernie`→`com.geckolib`、渲染改 `GeoRenderState`/`DataTicket` 管道、网络改 `CustomPacketPayload`、多加载器改 SPI），建议只在换 MC 版本时做。
3. **4.x 上可用的扩展点**（做内容 mod 够用）：`registerControllers` + 状态回调、`triggerAnim` 触发式动画、三个关键帧 handler（音效/粒子/自定义指令）、`animationSpeedModifier`/`overrideEasingTypeFunction`、`GeoModel`/`GeoRenderer` 子类化、`MolangParser` 自定义 query。
4. 与 VFX/粒子系统的协作范式：**动画关键帧 → 事件 → 外部特效库**（ParticleStorm 的接入点即在此），比"在动画里硬编码特效"可维护得多。
