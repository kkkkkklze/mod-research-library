# Shoulder Surfing Reloaded 源码分析报告

## 1. 基本信息

- Mod 名：Shoulder Surfing Reloaded；mod_id：`shouldersurfing`；作者：Exopandora（+12 位 contributors，见 `gradle.properties`）
- 目标版本：**MC 26.2 / NeoForge 26.2.0.0-beta / Forge 26.2-65.0.0 / Fabric loader 0.19.3**（`gradle/libs.versions.toml`）；Java 25（`javaVersion = 25`）。注意当前检出分支不是 1.21.1，读代码时需注意 Mojang 映射已改名（`ResourceLocation`→`Identifier`、`new ResourceLocation` 等）
- 构建：Gradle 多模块（`settings.gradle.kts` include `:api :common :compat :forge :neoforge :fabric`），`buildSrc` 提供 `multiloader-common`、`multiloader-modloader` 两个约定插件；各加载器用 ModDevGradle 2.0.141 / ForgeGradle 7.0.28 / Loom 1.17
- 许可证：MIT（`neoforge/src/main/resources/META-INF/neoforge.mods.toml`）；纯客户端（`side = "CLIENT"`、`displayTest = "NONE"`）
- 编译依赖（全部 compileOnly，无运行期强依赖）：forgeconfigapiport（供 Fabric 使用 NeoForge ModConfigSpec API）、WTHIT、Jade、Curios（`classifier("api")`）、Cobblemon

## 2. 源码规模与包结构

- 182 个 `.java`，共 9883 行（实测 `find . -name '*.java' -exec wc -l {} +`）
- 模块分布：`api/`（对外 API，53 文件）、`common/`（跨加载器实现，约 100 文件）、`compat/`（Create 0.5/6.0/CreateFly 的 Couple、ContraptionHandlerClient 版本桩）、`forge/neoforge/fabric/`（各约 6-8 文件）
- `common` 主要包：`client/`、`client/event/handler/`（16 个默认 handler 实现）、`client/renderer/`、`client/world/phys/`、`config/`（9 文件）、`mixin/`（26 文件）、`compat/mixin/*`、`event/`、`plugin/`、`util/`
- 最大文件：`config/CameraConfig.java` 916 行、`client/ShoulderSurfingCamera.java` 361、`client/ShoulderSurfing.java` 338、`client/renderer/CrosshairRenderer.java` 275、`client/event/handler/ComputeTargetCameraOffsetEventHandlerImpl.java` 255、`api/config/ICameraConfig.java` 242、`config/CrosshairConfig.java` 223、`event/EventBus.java` 203

## 3. 入口与注册

- 无 NeoForge 主类里的物品/方块注册；入口 `neoforge/src/main/java/com/github/exopandora/shouldersurfing/neoforge/ShoulderSurfingNeoForge.java:24`：`@Mod(value = MOD_ID, dist = Dist.CLIENT)`，构造器里 `modContainer.registerConfig(Type.CLIENT, Config.CLIENT_SPEC)`、`registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new)`，`FMLClientSetupEvent` 中把游戏事件监听挂到 `NeoForge.EVENT_BUS`（`clientTickEvent`、`preRenderGuiOverlayEvent` 用 `EventPriority.HIGHEST` + 接收已取消事件、`movementInputUpdateEvent` 用 `EventPriority.LOW`）。
- 注册 19 个键位（`RegisterKeyMappingsEvent`：相机上下左右前后、换肩、四种视角直切、自由视角、相机解耦、XYZ 偏移预设切换）。
- 跨加载器入口 `common/.../ShoulderSurfingCommon.java`；加载器差异（版本查询、mod 列表）抽到 `IPlatform`，各加载器给 `Platform`（`neoforge/Platform.java:16` 用 `FMLLoader.getCurrent().getLoadingModList()` 查第三方 mod 版本）。
- 自己实现 ServiceLoader 加载：`api/client/IShoulderSurfing.java:12` `INSTANCE = ServiceLoader.load(IShoulderSurfing.class).findFirst().orElseThrow()`；`plugin/PluginLoader.java:12` 同理加载平台子类。

## 4. 核心系统

1. **相机状态机**（`common/src/main/java/com/github/exopandora/shouldersurfing/client/ShoulderSurfingCamera.java`）：字段成对保存"当前/上一帧"值以便插值——`offset/offsetO`、`rotation/rotationO`、`rotationOffset/rotationOffsetO`、`maxCameraDistance/maxCameraDistanceO`；`tick()` 做 `offset.lerp(targetOffset, cameraTransitionSpeedMultiplier)` 与 `turnCameraWithPlayerDelay/EaseIn` 缓入（行 76-103）；`renderTick()` 只在非临时第一人称时推 `renderRotation`（行 105-126）；`setup(camera, level, partialTick, entity)` 计算 `renderOffset`（行 128-145）。
2. **相机防穿墙（8 点采样）**：`maxZoom()`（行 163-191）用 `i & 1 / i >> 1 & 1 / i >> 2 & 1` 枚举 8 个角偏移构造 `ClipContext`，在 `camera.upVector()/leftVector()/forwardVector()` 拼出的世界偏移上取最小命中距离；`maxCameraDistance` 只允许"变小即时生效、变大平滑"（`if (targetCameraDistance < maxCameraDistance)`，行 138-142），避免抖动。
3. **自定义事件总线 + 插件系统**：`api/event/IEventBus.java` 为 16 类事件各提供 `register(priority, handler)` 与默认优先级重载（`DEFAULT_PRIORITY = 1000`）；`common/event/EventBus.java` 用 `Map<Class<?>, HandlerList>` + `ConcurrentHashMap` 派发，加载完成后 freeze；插件通过 `common/plugin/PluginLoader.java` 扫描每个 mod jar 内的 `shouldersurfing_plugin.json`（`entrypoints` 数组 → 反射实例化 `IShoulderSurfingPlugin` → `PluginContainer` record），NeoForge 实现 `neoforge/plugin/PluginLoaderNeoForge.java` 遍历 `ModList.get().getModFiles()` 取 `JarResource`。所有跨 mod 交互走 `EventHooks.xxx()`（`common/.../client/EventHooks.java`）→ fire → 取 result。
4. **射线拾取（Pick）体系**：API 侧 `api/client/world/phys/` 有 `PickContext`（builder 式，含 `entityTrace/entityFilter/toClipContext`）、`PickVector`（枚举，决定从相机还是玩家出射线）、`DynamicPickContext/OffsetPickContext/ObstructionPickContext`；实现 `client/world/phys/ObjectPicker.java` 先 `pickBlocks` 再用命中距离收紧 range 去 `pickEntities`（行 21-36），`clip()` 用 `BlockGetter.traverseBlocks` + `BlockCollisionPredicate` 让不可碰撞方块（配置里的表达式匹配）不参与相机遮挡。
5. **临时第一人称 / 视角状态**：`client/ShoulderSurfing.java` 集中 `isShoulderSurfing/isTemporaryFirstPerson/isAiming/isCameraDecoupled/isFreeLooking` 等布尔状态，`computeIsCameraDecoupled()`（行 143-155）优先级明确：鞘翅 → 不解耦、睡觉 → 解耦、瞄准且十字准星非 `isAimingDecoupled` → 不解耦、否则看配置与事件。`changePerspective()` 在退出越肩时把相机旋转写回玩家（或 `lookAtCrosshairTargetInternal()`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端 mod，无 packet 注册）。
- 数据驱动：无自定义数据包类型；配置支持"方块 id 表达式" `Util.expressionToMatchPredicate`（`ShoulderSurfingCamera.hasNoCollision`，行 284-295）。
- 配置：NeoForge `ModConfigSpec`（`config/Config.java:18-22`），ClientConfig 下分 7 个子配置类：Camera(916 行，最大)、Perspective、Player、ObjectPicker、Crosshair、Audio、Integrations；`set(ConfigValue, value)` 统一打脏标记 `requiresSaving`，由 `ShoulderSurfing.tick()` 每 tick 检查后 `Config.CLIENT_SPEC.save()`（行 55-57）。`ModConfigEvent.Reloading` 触发 `Config.onConfigReload()` 修正视角合法性。API 侧只暴露只读接口（`api/config/IClientConfig.java` → `ICameraConfig` 数百个 getter + `default getOffset()` 聚合方法）。
- datagen：**无**（无 GatherDataEvent，无 `src/generated`）。

## 6. Mixin

- 配置文件 8 个：`common/src/main/resources/shouldersurfing.common.mixins.json`（26 个 client mixin）、`.common.compat.mixins.json`（列表为空、`defaultRequire: 0`）、`neoforge/forge/fabric` 各自 `.mixins.json` + `.compat.mixins.json`（全部在 `neoforge.mods.toml` 的多个 `[[mixins]]` 段声明）。
- `common/.../mixin/CameraMixin.java`（167 行，最核心）：
  - `Camera#alignWithEntity` HEAD → 重置自增 `@Unique float zRot`（相机 roll）。
  - 同一方法中 `@Inject` 在 `setPosition(DDD)V` 之后（`shift = Shift.AFTER, ordinal = 0`）覆盖 `setRotation(rotation.y(), rotation.x())`。
  - `@Redirect` `Camera#move(FFF)V`（ordinal 0）把越肩偏移换算成相机本地轴：`move(-offset.z(), offset.y(), -offset.x())`，并叠加 `calcCameraSway` 的 roll（行 111-124）。
  - `@ModifyVariable(method="calculateFov", at=@At(value="TAIL", shift=Shift.BY, by=-2), ordinal=1)` 实现 FOV 覆盖（`fovOverride / options.fov * lerpedFov`）。
  - `@Unique shouldersurfing$rotate()` 直接把 `rotationYXZ` + `FORWARDS/UP/LEFT.rotate` 重算，绕过原版 setter。
- `neoforge/.../neoforge/mixin/CameraMixin.java`：`@ModifyArg` 打在 `Quaternionf.rotationYXZ` 的 `index = 2`（`remap = false`），把 `zRot` 转弧度注入 roll —— 加载器层用 ModifyArg 补第三个欧拉角。
- mixin duck 接口：`mixinduck/CameraDuck.java`（`shouldersurfing$getZRot/setZRot`）、`OptionsDuck.java`（`shouldersurfing$setCameraTypeDirect`，绕开原版 `Options` 的相机类型写入回调）。
- 兼容 mixin 动态加载：`compat/ShoulderSurfingCompatMixinPlugin.java` + 各加载器子类实现 `IMixinConfigPlugin.getMixins()`，按 `Mods.CREATE.isLoaded()` 与版本区间 `[6.0.0,)` / `(,6.0.0)` 选 `create.ContraptionHandlerClientMixin_6_0_0` 或 `_0_5_0`（`ShoulderSurfingCompatMixinPluginNeoForge.java:28-38`），Create API 版本差异的桩类放在 `compat/src/create-0.5.0`、`create-6.0.0`、`createFly` 三个 source set 里（`com.simibubi.create.foundation.utility.Couple` vs `net.createmod.catnip.data.Couple`）。

## 7. 值得学的 5 条具体做法

1. **"当前值 + 上一帧值"成对字段 + 配置的插值系数**做平滑：`ShoulderSurfingCamera.java:28-44` + `tick()` 里 `lerp(x, target, cameraTransitionSpeedMultiplier)`，所有缓动都是纯 lerp，无需时间戳。适用：任何跟随相机/UI 缓动。
2. **相机穿墙用 8 角采样而非单条射线**：`ShoulderSurfingCamera.maxZoom()` 行 169-189，用 `camera.upVector()/leftVector()/forwardVector()` 组合世界偏移，把角色宽度并入采样半径（`clamp(bw/2/sqrt2, 0, 0.15)`）。适用：第三人称/过肩相机、任何要避免"半个身子穿墙"的相机。
3. **跨 mod 扩展点 = 自建事件总线 + jar 内 JSON 插件清单**：`plugin/PluginLoader.java`（读 `shouldersurfing_plugin.json` 的 `entrypoints`）+ `api/event/IEventBus.java`（带 priority 的强类型注册）。适用：需要被大量第三方 mod 挂钩的客户端 mod（比 mixin 稳定）。做成 mod 基座时可直接照抄。
4. **mixin 冲突用 duck 接口 + `@Unique` 前缀字段/方法**：`mixinduck/CameraDuck.java`、`shouldersurfing$getZRot()` 命名，让加载器层 mixin 与公共层 mixin 共享私有状态。适用：多 mixin 加同一目标类。
5. **兼容代码按版本拆 source set + `IMixinConfigPlugin.getMixins()` 动态选类**：`settings.gradle.kts`/`buildSrc` 的 `compat/src/create-0.5.0`、`create-6.0.0`，配 `ShoulderSurfingCompatMixinPluginNeoForge`，避免用反射或 `@Pseudo` 硬扛版本差异。适用：需要同时兼容 Create 0.5/6.0 之类 API 大改的兼容层。

## 8. 公开 API（库/API 类 mod）

- API 包：`api/src/main/java/com/github/exopandora/shouldersurfing/api/`
  - `api/client/IShoulderSurfing`（门面，`getInstance()`）、`IShoulderSurfingCamera`、`Perspective`、`CrosshairType`、`CrosshairVisibility`、`TurningMode`、`CameraDistanceAttributeMode`、`ViewBobbingMode`
  - `api/client/world/phys/`：`IObjectPicker`、`PickContext`（含 Builder）、`PickVector`、`PickOrigin`、`OffsetPickContext`、`DynamicPickContext`、`ObstructionPickContext`、`BlockCollisionPredicate`
  - `api/client/renderer/`：`ICameraEntityRenderer`、`ICrosshairRenderer`
  - `api/config/`：`IClientConfig` 及 7 个子配置接口（只读 getter）
  - `api/event/`：`Event`、`CancellableEvent`、`IEventBus`（16 个 handler 接口在 `api/client/event/handler/`）
  - `api/plugin/IShoulderSurfingPlugin`（`void register(IEventBus)`）、`api/math/Vec2f`、`api/util/{Couple,EntityHelper}`
- 外部接入方式：在自己的 mod jar 根放 `shouldersurfing_plugin.json` → `{"entrypoints": ["com.foo.MyPlugin"]}`，类实现 `IShoulderSurfingPlugin` 并在 `register(IEventBus)` 中注册 handler；运行时也可 `IShoulderSurfing.getInstance()` 直接查询/切换视角（`changePerspective/toggleCameraCoupling/swapShoulder/resetState`）。
