# tr7zw/EntityCulling 源码分析报告

## 1. 基本信息

- Mod 名 / id：EntityCulling / `entityculling`，作者 tr7zw，当前版本 1.10.5（`gradle-compose.yml` 的 `replacements.version`）。
- 目标 MC 与加载器：一个源码树同时产出多版本，见 `legacy.json`（1.19.4 / 1.20.1 / 1.20.2 / 1.20.4 / 1.20.6 / 1.21.1 / 1.21.3 / 1.21.4 / 1.21.5 / 1.21.8 / 1.21.10 / 1.21.11 的 forge+fabric，部分含 neoforge）与 `modern.json`（26.1/26.2 的 neoforge+fabric）。本项目是纯客户端 mod（`EntitycullingModBase.clientTick`/`worldTick`）。
- Gradle 插件/构建：仓库根**没有** `build.gradle`、`gradle.properties`、`settings.gradle`（文件不存在或为空），构建脚本由 `gradle/gradle-compose.jar` + `gradle-compose.yml` 依据模板 `https://github.com/tr7zw/ProcessedModTemplate` 现场生成；`versions/` 仅提交了一个文本文件 `mainProject`（内容 `26.2-fabric`），真正的子项目是生成物（`.gitignore` 忽略 build）。CI 用重命名的 wrapper `./gradlecw build`，产物收集 `versions/**/build/libs/*.jar`（`.github/workflows/build.yml`），JDK 25。
- 许可证：tr7zw Protective License（`LICENSE-EntityCulling`），禁止商业获利。
- 编译依赖（`gradle-compose.yml` 的 `dependencies`/子项目 Versionless 段）：`com.logisticscraft:occlusionculling:0.0.8-SNAPSHOT`（**核心算法库，compileOnly，运行时由 includeLibs 打进 jar**）、gson 2.10.1、log4j-core；`enabledFlags` 中的 `addTransitionLib` / `addTRenderLib` 引入 `dev.tr7zw.transition.*`（加载器抽象：`ModLoaderUtil`、`ModLoaderEventUtil`、`GeneralUtil`、`ClientUtil`、`CodeManager`）与 `dev.tr7zw.trender.gui.*`（配置界面控件）。即：加载器差异与 GUI 全部外包给自家库，业务代码几乎不 import Fabric/Forge API。

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **31**，总行数 **2320**（含独立子项目 `EntityCulling-Versionless/`）。

- `dev.tr7zw.entityculling`（根包，10 文件）：Mod 主体 `EntityCullingModBase`、`EntityCullingMod`、`EntityCullingBootstrap`、`CullTask`、`Provider`、`NMSCullingHelper`、`DebugCollector`、`KeybindHolder`、`BlockEntityRenderFabricExtension`
- `dev.tr7zw.entityculling.mixin`（11 文件，最大块）
- `dev.tr7zw.entityculling.access`（2）：`Cullable`、`EntityRendererInter`
- `dev.tr7zw.entityculling.config`（2）：`ConfigScreenProvider`、`EntityCullingModMenu`
- `dev.tr7zw.entityculling.debugEntries`（4）
- `dev.tr7zw.entityculling.versionless`（3，独立 gradle 子项目 `EntityCulling-Versionless/`）：`Config`、`ConfigUpgrader`、`EntityCullingVersionlessBase`

最大文件：`EntityCullingModBase.java` 248、`WorldRendererMixin.java` 241、`ConfigScreenProvider.java` 220、`CullTask.java` 176、`BlockEntityRenderDispatcherMixin.java` 126、`ClientWorldMixin.java` 114、`EntityRendererMixin.java` 107、`DebugCollector.java` 101。

## 3. 入口与注册

无 DeferredRegister / Registrate，也没有 `fabric.mod.json`、`neoforge.mods.toml`（由模板生成）。注册全走 tr7zw transition 的静态工具。

- Fabric 入口：`EntityCullingMod` 实现 `net.fabricmc.api.ClientModInitializer`（`EntityCullingMod.java:19-32`）；ModMenu 入口 `config/EntityCullingModMenu.java:9-14`。
- (Neo)Forge 入口：`EntityCullingBootstrap.java:11-24`（Forge `@Mod("entityculling")` + `DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> new EntityCullingMod().onInitialize())`）；NeoForge 版用 `registerClientSetupListener`。注意这两个类体整段被 `//? if forge {` 注释块包裹——同一文件容纳三平台。
- 初始化内容 `EntityCullingMod.initModloader()`（`EntityCullingMod.java:34-49`）：`ModLoaderEventUtil.registerClientTickStartListener/registerWorldTickStartListener`、`KeybindHolder.registerKeybinds()`、`ModLoaderUtil.registerConfigScreen(...)`、`disableDisplayTest()`；1.21.9+ 再注册 4 条 debug 行。
- 核心对象装配在 `EntityCullingModBase.onInitialize()`（`:44-63`）：`culling = new OcclusionCullingInstance(config.tracingDistance, new Provider())`、`cullTask = new CullTask(culling)`、`new Thread(cullTask, "CullThread")` 并设置 `setUncaughtExceptionHandler`；`CodeManager.getInstance().registerCode("entityculling_debug"/"entityculling_freezecam", ...)`。

## 4. 核心系统

**(a) 异步剔除线程**：`CullTask.java:53-79`。`while (Minecraft.getInstance().isRunning()) { Thread.sleep(sleepDelay=10ms); ... }`，仅在 `requestCull` 或相机位置变化时重算，每次 `culling.resetCache()` 后依次 `cullBlockEntities` / `cullEntities`；`run()` 整体 try/catch Exception 打印，不让线程死掉。剔除判据（`CullTask.java:97-118`、`:145-158`）：`isForcedVisible()` / 发光 / 超出 `tracingDistance`(128) / 方块实体超出 64 格 / AABB 任一边 > `hitboxLimit`(50) 一律不剔除；否则 `culling.isAABBVisible(aabbMin, aabbMax, camera)`。复用预分配 `Vec3d lastPos/aabbMin/aabbMax` 避免 GC。

**(b) 跨线程数据交接**：主线程 `EntityCullingModBase.clientTick()`（`:130-171`）每 `captureRate`（默认 5）tick 做一次"防御性拷贝"：`client.level.entitiesForRendering()` → `prefetchEntityData`（填 `setEc$BoundingBox`/`setEc$Position`/发光）；方块实体只扫玩家 chunk ±8（17×17 区块）`prefetchBlockEntityData`。然后 `cullTask.setEntitiesForRendering(...)`/`setBlockEntities(...)`（Lombok `@Setter`，`CullTask.java:39-47`）。异步侧对迭代器遇到 `NullPointerException|ConcurrentModificationException` 直接 `break`，注释明确"不同步主线程，NPE/CME 是允许的，比同步开销小"。

**(c) 状态字段注入**：`access/Cullable.java` 定义 `setCulled/isCulled/setOutOfCamera/isOutOfCamera/setTimeout/isForcedVisible/shouldEntityAppearGlowing/ec$BoundingBox/ec$Position`；`mixin/CullableMixin.java:12-26` 用 `@Mixin({Entity.class, BlockEntity.class})` 把字段与实现塞进原版类（字段名带 `ec$` 前缀防冲突）。`setCulled(false)` 会 `setTimeout()` 给 1 秒强制可见宽限（`:29-44`），`isCulled()/isOutOfCamera()` 在全局 `enabled=false` 时恒 false。

**(d) 渲染期跳过（mixin 侧）**：`WorldRendererMixin.java:47-82` 在 1.21.9+ 注入 `LevelRenderer.extractEntity` HEAD：命中剔除则 `skippedEntities++`，构造一个 `entityType = EntityTypes.INTERACTION` + `isInvisible = true` 的假 `EntityRenderState` 返回（`processNametag` 单独补名牌，实现"隔墙看名牌"），旧版本则注入 `renderEntity` 并 `info.cancel()`（`:154-203`）。`BlockEntityRenderDispatcherMixin.java:27-88` 注入 `tryExtractRenderState` HEAD（1.21.9+ 前为 `render`，`:93`），`info.setReturnValue(null)` 跳过；并在 `:61-73` 用同一份 `setupAABB` + `frustum.isVisible(...)` 补做**原版缺失的方块实体视锥剔除**。

**(e) 实体 tick 剔除**：`ClientWorldMixin.java:34-72` 注入 `ClientLevel.tickNonPassenger` HEAD cancellable，被剔除实体只跑 `basicTick()`（`:83-100`：`setOldPosAndRot` + `tickCount++` + `LivingEntity.aiStep()` + `hurtTime--`，并手工补 Warden 心跳音效与 `getWardenHeartBeatDelay` 的私有方法拷贝）。强制保留清单：`ignoresCulling(entity)`、本地玩家/相机实体、`isPassenger()/isVehicle()`、`instanceof AbstractMinecart`（注释说明用抽象类以覆盖 mod 矿车）。`outOfCamera` 起到"延迟一 tick 才跳"的缓冲作用（先 `setOutOfCamera(true)`，下一轮才跳）。

**(f) 配置与扩展点**：`versionless/Config.java` 是纯 Gson POJO，`configVersion = 8` 配合 `ConfigUpgrader.upgradeConfig` 做迁移；落盘 `config/entityculling.json`（`EntityCullingVersionlessBase.java:26-27`、`writeConfig()` `:58`）。白名单以字符串资源 ID 存配置、客户端 tick 时解析成 `Set<EntityType<?>>`（`EntityCullingModBase.java:74-94`），默认内置 create/botania 等兼容项。对外 API：`addDynamicEntityWhitelist(Function<Entity,Boolean>)` / `addDynamicBlockEntityWhitelist(...)`（`:234-246`）供其他 mod 运行时豁免剔除。`setupAABB` 为抽象方法，各平台各自实现（Fabric 侧用自建 `BlockEntityRenderFabricExtension`，`:52-67`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**任何自定义包（纯客户端计算，剔除状态不进 NBT、不参与原版存档序列化）。
- 数据驱动 / 数据包：**无**。
- 配置：Gson + `config/entityculling.json`，UI 用 `trender` 的 `AbstractConfigScreen`/`WListPanel`/`WToggleButton`（`config/ConfigScreenProvider.java:9-18`、`ConfigScreen` 内部类 `:37-214`），`save()`/`reset()` 直接改 `EntityCullingModBase.instance.config`。
- datagen：**无**（资源仅 `assets/entityculling/lang/` 20 个语言文件 + `entityculling.mixins.json`）。

## 6. Mixin

配置：`src/main/resources/entityculling.mixins.json`——`required: true`、`compatibilityLevel: JAVA_16`、`refmap: entityculling.refmap.mixins.json`、`client` 数组 10 个、`injectors.defaultRequire = 1`。

| Mixin | 目标 | 注入点 |
|---|---|---|
| `CullableMixin` | `Entity`、`BlockEntity` | 接口+字段注入 |
| `WorldRendererMixin` | `LevelRenderer`（旧）/ `LevelExtractor`（≥26.2） | `renderEntity` / `extractEntity` HEAD cancellable、`extractVisibleEntities` HEAD（存 frustum） |
| `BlockEntityRenderDispatcherMixin` | `BlockEntityRenderDispatcher` | `render` / `tryExtractRenderState` HEAD |
| `ClientWorldMixin` | `ClientLevel` | `tickNonPassenger` HEAD |
| `EntityRendererMixin` | `EntityRenderer` | 实现 `EntityRendererInter`；`@Shadow shouldShowName/createRenderState/affectedByCulling/getBoundingBoxForCulling` |
| `DebugHudMixin` | `DebugScreenOverlay` | `getGameInformation` RETURN（追加剔除计数行） |
| `DebugScreenEntriesAccessor` / `LivingEntityRendererAccessor` | `DebugScreenEntries` / `LivingEntityRenderer` | `@Invoker invokeRegister` / `invokeShouldShowName` |
| `DisplayAccessor` | `Display` | `invokeSetWidth/SetHeight`（给 0 尺寸展示实体 3×3 包围盒以便剔除） |
| `BlockEntityRendererMixin` | `BlockEntityRenderer` | 接口 `BlockEntityRenderFabricExtension` |

## 7. 值得学的 5 条做法

1. **注释式多版本预处理器**：`//? if >= 1.21.9 {`…`//? }` 让同一文件同时容纳多版本 API（`WorldRendererMixin.java:30-36` 在 `LevelExtractor` 与 `LevelRenderer` 之间切换），本地编辑用 IDE 内现成本版代码、发布时由工具解注释。适用：要长期跟多个 MC 版本。
2. **异步线程只吃主线程做好的快照，不共享可变集合**：`CullTask.java:39-47` 的 `@Setter` 拷贝字段 + 对 NPE/CME 宽容 `break`（`:126-140`）；比加锁更省。适用：渲染/寻路等后台计算。
3. **剔除带"防抖宽限 + 保守豁免"**：`setCulled(false)` 触发 1 秒 `setTimeout()` 强制可见（`CullableMixin.java:29-36`），超出 `tracingDistance`、`hitboxLimit` 过大、`shouldRenderOffScreen` 的对象一律不剔除。适用：所有"激进优化"类功能，避免玩家看到闪烁/消失。
4. **渲染状态的"假对象"返回法**：不 cancel 而是返回一个 `EntityTypes.INTERACTION` + `isInvisible` 的 `EntityRenderState`（`WorldRendererMixin.java:54-74`），从而在跳过渲染的同时保留名牌/调试盒等必要附挂逻辑。适用：1.21.9+ 分离式渲染管线下的渲染拦截。
5. **把"给其他 mod 用"的钩子做成 `Function` 白名单**：`addDynamicEntityWhitelist`/`addDynamicBlockEntityWhitelist`（`EntityCullingModBase.java:234-246`）+ 配置里预置 `create:contraption`、`botania:mana_burst` 等已知冲突 id，一次解决兼容与误剔除。
6. （附加）**用 Objenesis 做无游戏实例的 mixin 自检**：`src/test/java/dev/tr7zw/tests/MixinTests.java:34-57` 直接 `objenesis.newInstance(Pig.class)` 断言 `instanceof Cullable`，可在 CI 里第一时间发现 mixin 目标/签名失效。

## 8. 对外扩展点（本 mod 非库类，但存在接入面）

- 单例：`EntityCullingModBase.instance`（公开静态）。
- 编程式豁免：`addDynamicEntityWhitelist(Function<Entity,Boolean>)`、`addDynamicBlockEntityWhitelist(Function<BlockEntity,Boolean>)`；读取钩子 `isEntityDynamicWhitelisted/isBlockEntityDynamicWhitelisted`（`EntityCullingModBase.java:210-246`）。
- 配置项：`EntityCullingModBase.instance.config`（`Config` 全部字段 public，资源 id 字符串列表），玩家侧也可在配置界面维护。
- 未确认：是否存在 `fabric.mod.json` 中导出的自定义 entrypoint（模板生成物不在仓库中，无法核对）。
