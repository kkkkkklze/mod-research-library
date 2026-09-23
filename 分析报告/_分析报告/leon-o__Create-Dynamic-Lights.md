# leon-o/Create-Dynamic-Lights 源码分析报告

## 1. 基本信息

- Mod 名：Create Dynamic Light；mod_id `createdynlight`；作者 Leon；版本 2.0.0
- 目标：Minecraft 1.21.1 / NeoForge（`neo_version=21.1.209`，`neoforge.mods.toml` 对 neoforge 要求 `[21.1.129,)`，side=CLIENT）；Parchment 2024.11.17
- Gradle：Groovy + `net.neoforged.gradle.userdev` 7.0.192（旧式 NeoGradle，非 moddev）
- 许可证：MIT（`LICENSE.txt`）
- 编译依赖：`compileOnly` Create 6.0.1-12、Ponder 1.0.39、Flywheel 1.0.0-10、Iris 1.8.8；`implementation maven.modrinth:sodium-dynamic-lights:1.0.10`，代码直接引用 `toni.sodiumdynamiclights.*`，因此该 mod 是事实上的必需运行依赖（README 也把 Embeddium/Rubidium Dynamic Lights 列为推荐）
- mods.toml 声明：create 必选（AFTER，BOTH），`sodiumdynamiclights` 可选（CLIENT）
- 目录只有 NeoForge 分支（`src/main/resources/META-INF/neoforge.mods.toml`），README 中的 Fabric/LambDynamicLights 属旧版说明

## 2. 源码规模与包结构

实测：14 个 `.java`，合计 859 行（极小体量，是"单点功能深挖"的范例）。

- `top.leonx.dynlight`（根，4）：`CreateDynLight`、`LambModEventHandler`、`LightBehaviourProvider`、`LightMovementBehaviour`
- `top.leonx.dynlight.config`（4）：`CreateDynLightAllConfigs`/`Common`/`Client`/`Server`
- `top.leonx.dynlight.lamb`（6）：`CreateDynLightSource`(189)、`CreateDynLightSourceHolder`(96)、`ContraptionEntityEventHandler`(79)、`CreateDynLightSourceForge`(64)、`LambDynLightsDelegate`(56)、`CreateDynLightSourceCreator`(10)

## 3. 入口与注册

`src/main/java/top/leonx/dynlight/CreateDynLight.java:25` `@Mod(CreateDynLight.MODID)`。不使用 Registrate/DeferredRegister（本 mod 无新方块物品），唯一注册动作在 `commonSetup`：

```java
event.enqueueWork(() -> {
    MovementBehaviour.REGISTRY.registerProvider(new LightBehaviourProvider());   // :60
});
```

上面的注释代码（:44-57）记录了旧方案：遍历 `BuiltInRegistries.BLOCK` 找 `getLightEmission()>0` 的方块逐个 `MovementBehaviour.REGISTRY.register`，被 Provider 方案替代（`:64 registerBehaviours` 仍保留）。

## 4. 核心系统

**A. 行为 Provider（Create API 用法最值得学）**：`LightBehaviourProvider implements SimpleRegistry.Provider<Block, MovementBehaviour>`（`LightBehaviourProvider.java:15`），构造时预建 `Map<Integer, LightMovementBehaviour>`（亮度 1..15 → 实例），`get()` 按 `block.defaultBlockState().getLightEmission()` 查表返回，实现"任意发光方块自动获得行为"且不产生每方块一个新对象。

**B. 光块（服务端）**：`LightMovementBehaviour implements MovementBehaviour`（`LightMovementBehaviour.java:10`），`visitNewPosition` 先清旧 `Blocks.LIGHT` 再放新光块，`stopMoving` 清理；上一位置以 `MovementContext.data` 的 NBT 键 `"LightBlockPrevPos"` 保存（:34-55）。受服务端配置 `enableLightBlock`/`lightBlockEmissionLowerLimit` 控制。

**C. 动态光源（客户端）**：`CreateDynLightSource` 由 `AbstractContraptionEntity` + 局部坐标 `localPos` 构成，位置用 `entity.toGlobalVector(VecHelper.getCenterOf(localPos), 1)` 求世界坐标，亮度每次从 `contraption.getContraption().getBlocks().get(localPos).state().getLightEmission()` 取（:96-109）；`getLuminance()` 乘配置倍率。更新前做双重节流：位移/亮度阈值 0.1 与毫秒级时间间隔（:140、`shouldUpdateDynamicLight` :111-125），再按 LambDynamicLights 的"7 次环绕 + 记录已点亮区块"策略 scheduleChunkRebuild（:144-177）。

**D. 第三方后端隔离**：`LambDynLightsDelegate`（静态转发 `scheduleChunkRebuild`/`updateTrackedChunks`/`add/removeLightSource`、读取 `DynamicLightsConfig.DYNAMIC_LIGHTS_MODE` 与模式延迟）是唯一的第三方 API 接触面；`CreateDynLightSourceForge implements toni.sodiumdynamiclights.DynamicLightSource` 用 `sdl$` 前缀方法转发抽象类。换渲染后端只改这两处。

**E. 光源注册表与生命周期**：`CreateDynLightSourceHolder` 单例，`Map<LightSourceKey(entityId, blockPos), CreateDynLightSource>` + `AtomicInteger` 自增 id + `ReentrantReadWriteLock`（渲染线程并发保护，:20-32）。`LambModEventHandler` 监听 `EntityJoinLevelEvent`/`EntityLeaveLevelEvent`/`LevelTickEvent.Post`，转交 `ContraptionEntityEventHandler`：contraption 尚未构建时先入 `scheduledToAddContraptionEntities` 队列，tick 时重试；运行中切换配置会 `onDynamicLightEnabledChanged` 全量增删（:36-78）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无。
- 数据驱动：无。
- 配置：`config/CreateDynLightAllConfigs.java:42-62` 用 Create catnip 的 `ConfigBase` + `new ModConfigSpec.Builder().configure(...)`，把 Client/Server 两个 ConfigBase 装进 `Map<ModConfig.Type, ConfigBase>` 后逐项 `container.registerConfig`；`onLoad/onReload` 按 spec 匹配分发。`CreateDynLightCommon` 已被注释停用。`CreateDynLightClient.getUpdateInterval()` 把自身 `updateInterval` 与 `LambDynLightsDelegate.getDynamicLightsModeDelay()`（SLOW 500/FAST 200）相加或替代，由 `ignoreLambModeSetting` 决定。
- datagen：无。
- Mixin：无。

## 6. Mixin

无。全部集成通过 Create 的公开注册表 + NeoForge 事件完成，是这个仓库最突出的工程取向。

## 7. 值得学的 5 条具体做法

1. 批量注入行为用 `SimpleRegistry.Provider`（`LightBehaviourProvider.java:22-27`）：一次注册覆盖所有满足条件的方块，避免遍历注册表；适用于给第三方方块批量加行为。
2. 按参数缓存行为实例：`Map<Integer, LightMovementBehaviour>` 只创建 15 个对象，而不是每个方块一个。
3. 用 Delegate 类收拢第三方 API（`lamb/LambDynLightsDelegate.java`）：换库只改一个文件；代价是 `implementation` 依赖未声明为可选，实际会变成硬依赖（可改为反射/条件加载）。
4. 客户端高频逻辑双重节流：位移 >0.1 或亮度变化才重建区块光照，再加毫秒级 `updateInterval` 配置（`CreateDynLightSource.java:111-140`）。
5. 实体加入世界时目标对象可能未就绪 → 延迟队列 + 每 tick 重试（`ContraptionEntityEventHandler.java:22-54`）；配置运行时切换时全量重扫（:63-78）。

## 8. 公开 API

非库 mod，未定义对外 API/扩展点；仅通过 Create 的 `MovementBehaviour.REGISTRY` 参与他人注册表。
