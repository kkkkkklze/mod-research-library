# NotEnoughAnimations 源码分析报告

## 1. 基本信息
- Mod 名：Not Enough Animations；mod_id：`notenoughanimations`；作者 tr7zw；版本 1.12.4（`gradle-compose.yml`）；Modrinth `MPCX6s5C` / CurseForge 433760。
- 目标版本与加载器：Stonecutter 多版本同源（源码内大量 `//? if >= 1.21.11 {` 预处理注释），最新提交 `07d22d9 Add neo 26.2`；Fabric/Forge/NeoForge 同时发布（`gradle-compose.yml` 的 `publishFabric/publishForge/publishNeo` 标志）。
- Gradle 插件：无仓库内 `build.gradle`/`gradle.properties`，工程由 `gradle-compose.yml` + `replacements.gradle` 从外部模板 `ProcessedModTemplate` 生成（`.github/workflows/build.yml` 用 JDK 25）。
- 许可证：仓库内无 LICENSE 文件（未确认）。
- 编译依赖：`compileOnly` gson 2.10.1、log4j-core 2.20.0（`gradle-compose.yml`）；运行期打包 tr7zw 自研库 TRansition（`dev.tr7zw.transition.*`）与 TRender GUI（`dev.tr7zw.trender.gui.*`，见 `addTRenderLib/addTRansitionLib` 标志）。
- 软依赖：`NEAVersionless/src/main/java/dev/tr7zw/notenoughanimations/versionless/NEABaseMod.java:30` 用 `Class.forName("dev.tr7zw.firstperson.FirstPersonModelCore")` 探测 FirstPersonModel 并改默认值。

## 2. 源码规模与包结构
实测 `find . -name '*.java' | wc -l` = **71 文件 / 5361 行**，其中 `src/main` 4932 行，`NEAVersionless` 共享层 9 文件。
- `animations/fullbody` 8、`animations/hands` 11、`animations/vanilla` 8（三类动画实现）
- `mixins` 13、`api` 3、`access` 3、`logic` 3、`util` 4、`config` 1、`renderlayer` 1、根包 4
- `dev.tr7zw.notenoughanimations.versionless.*`（Config/BodyPart/DataHolder 等版本无关层）
最大文件：`logic/HeldItemHandler.java`(351)、`config/ConfigScreenProvider.java`(280)、`util/AnimationUtil.java`(260)、`renderlayer/SwordRenderLayer.java`(189)、`logic/PlayerTransformer.java`(184)、`animations/fullbody/LadderAnimation.java`(165)、`mixins/PlayerEntityModelMixin.java`(163)、`logic/AnimationProvider.java`(158)。

## 3. 入口与注册
Fabric entrypoint `dev.tr7zw.notenoughanimations.NEAnimationsMod`（`gradle-compose.yml`），类链 `NEAnimationsMod extends NEAnimationsLoader extends NEABaseMod`：
```java
public class NEAnimationsMod extends NEAnimationsLoader implements ClientModInitializer {
    public void onInitializeClient() { onEnable(); }
}
```
`NEAnimationsLoader`(:23-56) 构造时 `ModLoaderUtil.disableDisplayTest()`、`ModLoaderUtil.registerConfigScreen(ConfigScreenProvider::createConfigScreen)`；`enable()` 建 `PlayerTransformer/HeldItemHandler/AnimationProvider`，`lateInit()` 在客户端首个 tick 再 `refreshEnabledAnimations()`（等其它 mod 初始化完，:58-61）。
无 DeferredRegister / Registrate——不注册任何游戏对象，全走 mixin 挂客户端渲染管线；每 tick 入口是 `mixins/ClientLevelMixin.java:15`（`ClientLevel.tickEntities` HEAD → `INSTANCE.clientTick()`）。

## 4. 核心系统
**(a) 部位级动画仲裁 `logic/AnimationProvider.java`**
- `applyAnimations`(:64-93)：每个 `BodyPart` 一个 `int[] priorities` + `BasicAnimation[] animation`，遍历启用动画，`isValid` → `getPriority`，仅当 `prio > priorities[part]` 才覆盖，实现"单部位胜者制"而整体可叠加。
- 三段式 `prepare/apply/cleanup`，`api/BasicAnimation.java:59-68` 用 `isPrepared` 标志保证 `precalculate` 只跑一次。
- 优先级区间是公开契约：1-999 被动持物、1000-1999 载具/梯子、2000-2999 主动（进食）、3000-3999 高优先（原版拉弓）、-1 禁用（`api/BasicAnimation.java:46-57`）。
- `basicAnimations`（全量）与 `enabledBasicAnimations`（配置过滤后）分离，`refreshEnabledAnimations()`(:137) 可热切换。

**(b) 姿态平滑 `logic/PlayerTransformer.java`**
- 状态是 `float[ENTRY_SIZE(9) * ENTRY_AMOUNT(5)]` 扁平数组，注释写明 9 槽含义：0-2 当前目标、3-5 上 tick 目标、6-8 上次渲染值（:108-109）。
- `interpolate`(:106-143) 用 `AnimationUtil.lerpAngle` 做帧间补间；`timePassed > 50`（超过 1 tick）直接重置，避免卡顿后拖影；`cleanInvalidData`(:175) 兜住 QuickCharge 5 弩产生的 NaN。
- 身体朝向锁复用第 5 段：`RotationLock.SMOOTH` 时插值 `yBodyRot`，头身夹角 >90° 把速度 ×0.9（:156-158）防瞬间回正。

**(c) 手持物处理 `logic/HeldItemHandler.java`**
- 自身即 `DataHolder<HeldItemState>`，状态经 `PlayerData.getData(holder, builder)` 的 `computeIfAbsent` 挂在实体上（`mixins/PlayerEntityMixin.java:121`）。
- `onRenderItem`(:57+) 在物品渲染前决定 cancel/替换：睡觉不持物、自定义模型物品不替换、`hideItemsForTheseBows` 隐藏双手；`util/MapRenderer.java` 另把地图内容画到手上。

**(d) 每玩家状态与渲染态搬运**
- `mixins/PlayerEntityMixin implements PlayerData`(:23-43) 集中存 lastRotations、sideSword、disableBodyRotation、poseOverwrite、`Map<DataHolder<?>,Object>`。
- 1.21.2+ 渲染状态化后，`mixins/LivingEntityRendererMixin.java:22` 在 `extractRenderState` HEAD 把实体塞进 `LivingRenderStateMixin` 的 `@Unique` 字段，模型层再取回（`access/ExtendedLivingRenderState.java`）；1.21.9+ 再经 `util/RenderStateHolder.java` 挂到 `AvatarRenderState`——跨版本 RenderState 断链的通用解法。

**(e) 版本兼容三层**：`NEAVersionless`（版本无关代码，单独子项目）、Stonecutter `//? if` 注释、`util/NMSWrapper.java` 反射兜底。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无（纯客户端视觉，README 声明与原版/第三方服务端兼容）。
- 配置：单文件 `config/notenoughanimations.json`，Gson `setPrettyPrinting` 直序列化 `Config` 字段（`NEAVersionless/.../NEABaseMod.java:21-46`）；`config/ConfigUpgrader.java:5-58` 用 `configVersion` 阶梯 if 逐版本补默认值并返回 changed 决定是否回写。
- 配置界面：`config/ConfigScreenProvider.java:44+` 用 TRender 的 `AbstractConfigScreen` + `WTabPanel/WListPanel/WTextField` 手搭分页 UI；ModMenu 走 `NEAModMenu`。
- datagen：无。`src/test/java/dev/tr7zw/tests/` 有 MixinTests/TestMod/TestUtil。

## 6. Mixin
配置 `src/main/resources/notenoughanimations.mixins.json`（package `dev.tr7zw.notenoughanimations.mixins`，`client` 13 个，`injectors.defaultRequire=1`，compatibilityLevel JAVA_8）。代表 hook：
- `mixins/PlayerEntityModelMixin.java:58,96,128` → `PlayerModel.setupAnim` HEAD（preUpdate）与两处 RETURN（应用动画、消费 poseOverwrite）。
- `mixins/PlayerEntityMixin.java:45` `Player.tick` RETURN；:52 `getMaxHeadRotationRelativeToBody` HEAD cancellable（改头身最大转角上限）。
- `mixins/ItemInHandLayerMixin.java:68` `submitArmWithItem` HEAD cancellable（接管持物渲染）。
- `mixins/ItemInHandRendererMixin.java:17,31` `renderPlayerArm` HEAD/RETURN（置 `renderingFirstPersonArm` 标志，跳过第一人称手臂）。
- `mixins/LivingEntityMixin.java:22` `tickHeadTurn` HEAD cancellable；`mixins/ClientLevelMixin.java:15` `tickEntities` HEAD。
- `mixins/EntityRenderDispatcherAccessor.java:11` `@Accessor("blockModelResolver")`。

## 7. 值得学的 5 条具体做法
1. 用"每身体部位优先级数组"代替单一动画状态机：`logic/AnimationProvider.java:64-93`，多动画天然可叠加/局部覆盖，适合任何动作系统。
2. 基类固化 `prepare→apply→cleanup` + `isPrepared` 标志：`api/BasicAnimation.java:59-68`，每帧多实体调用时避免重复重算。
3. 扁平 float 数组存插值历史并注释槽位含义：`logic/PlayerTransformer.java:25-26,106-143`，减少对象分配且便于整体存取。
4. `configVersion` 阶梯 if + changed 返回值的配置升级：`NEAVersionless/.../ConfigUpgrader.java:5-58`，老配置文件加字段不炸档。
5. 反射探测软依赖后改默认值（FirstPersonModel 共存适配）：`NEAVersionless/.../NEABaseMod.java:28-36`，可选前置无需写 build 依赖。

## 8. 公开 API（本 mod 含 API 包）
- 包：`dev.tr7zw.notenoughanimations.api`。
- 入口：`api/NotEnoughAnimationsApi.java:13-23` 的 `registerAnimation(BasicAnimation)`、`refreshEnabledAnimations()`。
- 扩展点：继承 `api/BasicAnimation.java`（必须实现 isEnabled/isValid/getBodyParts/getPriority/apply），可选实现 `api/PoseOverwrite.java` 在 setupAnim 前改实体姿态；`access/PlayerData.java` 提供 `setDisableBodyRotation/setRotateBodyToHead/setPoseOverwrite/getData`，动画可临时夺权（玩家实体因 mixin 实现该接口可直接强转）。
- 接入方式：静态 API 调用，无 mod 元数据耦合；`versionless/animations/BodyPart.java` 的 6 部位枚举是跨包公共契约。
