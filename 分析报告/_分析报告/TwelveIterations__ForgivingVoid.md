# TwelveIterations/ForgivingVoid 源码分析报告

## 1. 基本信息
- Mod 名：Forgiving Void；mod_id：`forgivingvoid`；作者：BlayTheNinth（TwelveIterations）
- 目标版本：`gradle/libs.versions.toml` 中 `minecraft = "26.2"`、`neoForge = "26.2.0.0-beta"`、`forge = "63.0.2"`、`fabricApi = "0.152.1+26.2"`、`shogi = "26.2.0.1-SNAPSHOT"`，`java_version = 25`（快照期版本，非 1.21.1）
- 构建：多加载器模板（`build-logic/src/main/groovy/multiloader-common.gradle` + `multiloader-loader.gradle`）；NeoForge 用 ModDevGradle，Fabric 用 Fabric Loom，Forge 用 ForgeGradle，发布用 CurseForgeGradle + Minotaur
- 许可证：`gradle.properties` 写 `license=All Rights Reserved`（闭源）
- 关键依赖：`net.blay09.mods:balm-*`（作者自研跨加载器框架，提供事件/配置/注册/持久化 NBT 抽象）、`net.blay09.mods:shogi-api`（数据驱动数值表达式引擎）。即本 mod 是 Balm + Shogi 的消费者，可作 API 消费范例

## 2. 源码规模与包结构
- `.java` 文件 **20** 个，总 **570** 行（实测 `find . -name '*.java' | wc -l` / `-exec wc -l {} +`），极小型仓库
- 包结构（按源码根去掉后第 3 层）：`common/net/blay09/mods/forgivingvoid`（6 文件）、`.../forgivingvoid/mixin`（5）、`neoforge/.../neoforge`（2）、`fabric/.../fabric/datagen`（2）、`fabric/.../fabric`（2）、`neoforge`+`forge`+`fabric` 各 1 个 mixin 包（空实现，占位）
- 最大文件：`ForgivingVoid.java` 261 行（承载几乎全部逻辑）、`ForgivingVoidConfig.java` 70、`mixin/CombatTrackerMixin.java` 31、`ForgivingVoidFallThroughEvent.java` 31、`ForgivingVoidRules.java` 29

## 3. 入口与注册
- 公共入口 `common/.../ForgivingVoid.java:40` 的静态 `initialize(BalmRegistrars)`；各加载器入口只做转发：
  - `neoforge/.../neoforge/NeoForgeForgivingVoid.java`：`@Mod(MOD_ID)` 构造器内 `Balm.initializeMod(MOD_ID, new NeoForgeLoadContext(modContainer, modEventBus), ForgivingVoid::initialize)`
  - `fabric/.../fabric/FabricForgivingVoid.java`：`ModInitializer#onInitialize` → `Balm.initializeMod(..., FabricLoadContext.INSTANCE, ...)`
- 不使用 `DeferredRegister`/`Registrate`：本 mod 无任何方块/物品注册，只注册事件监听与配置：`ServerTickCallback.ServerEntityTick.BEFORE.register(ForgivingVoid::onEntityTick)`、`LivingEntityCallback.Fall.Before.EVENT.register(ForgivingVoid::onLivingEntityFall)`（`ForgivingVoid.java:43-44`）
- 资源模板：`neoforge/src/main/resources/META-INF/neoforge.mods.toml` 用 `${license}`/`${version}` 占位符，由 `build-logic/.../multiloader-common.gradle:152-156` 在 `processResources` 阶段替换（`META-INF/*.toml`、`fabric.mod.json`、`*.mixins.json`）；Fabric 无手写 `fabric.mod.json`，由其生成

## 4. 核心系统
1. **虚空坠落传送（主逻辑）** — `ForgivingVoid.java:47-117` `onEntityTick(Entity)`：每 tick 对所有实体判 `entity.getY() < level.getMinY() - triggerAtDistanceBelow && entity.yo < ...`（必须连续两 tick 在阈值下，避免刚传送瞬间误触发）；用 `entity.onGround()` 时把 `LastGroundedPos` 写入 Balm 持久化 NBT（`Balm.hooks().getPersistentData(entity)`）、并清零 `Loops`；触发时把乘客/载具一并收集进 `entitiesToTeleport`，`ejectPassengers()` → 逐实体 `teleportTo` → `startRiding(vehicle)` 还原骑乘关系
2. **落点与循环计数** — 落点 Y 由数据包表达式求值：`ForgivingVoidRules.fallingHeight.getOrDefault(makeContext(entity, loops))`（`ForgivingVoid.java:90`）；`ForgivingVoidRules.java:12-19` 用 Shogi 声明 `scope = Shogi.scope(id("rules"))` 与 `intValue(id("falling_height"), ctx -> ctx.requireLevel().getHeight())`，把 `loops` 作为变量注入 `MutableShogiContext`，从而允许数据包按"第几次坠落"返回不同高度
3. **落地伤害改写** — `ForgivingVoid.java:194-227`：只在 `TAG_IS_FALLING` 为真时生效，`calculateFallDamage` 支持 `DamageOnFallMode.ABSOLUTE / RELATIVE_CURRENT / RELATIVE_MAX`（`DamageOnFallMode.java`），百分比 >1 自动除以 100 归一化，`preventDeath` 时把伤害压到 `health - 1f`，最后 `Math.min(damage, originalDamage)` 保证只减不增
4. **"未落地"状态维护** — `ForgivingVoid.java:100-116`：因 `LivingFallEvent` 在落水/飞行时不触发，mod 自行兜底——`hasLanded()` 检查 `onGround()/isInWater()/isInLava()` 及 `FALL_CATCHING_BLOCKS = Set.of(Blocks.COBWEB)`（:171），`isOrMayFly()` 检查鞘翅/`abilities.mayfly`，命中才清 `TAG_IS_FALLING`；同时借 `ServerPlayerAccessor.setIsChangingDimension(true)` 让原版反作弊在坠落期间放行
5. **公开扩展事件** — `ForgivingVoidFallThroughEvent.java`：`BidirectionalEventMapper` + `EventMapper.createBound(...)`，`fireForgivingVoidEvent` 在传送前触发并可 `setCanceled`
6. **实体与维度过滤** — `isAllowedEntity`（:149）与 `isEnabledForDimension`（:235）：原版三维度走布尔开关，自定义维度走 `dimensionAllowList/dimensionDenyList`（allowList 非空时忽略 denyList）；`tridentForgiveness` 让忠诚三叉戟也可被原谅（Forge 不支持）

## 5. 网络 / 数据驱动 / 配置 / datagen
- **无自定义网络包**；全部逻辑服务端执行
- **配置**：`ForgivingVoidConfig.java` 用 Balm 的注解式反射配置 `@Config(MOD_ID)` + `@Comment` + `@NestedType(String.class|Identifier.class)`；字段直接是 `int/boolean/float/List<String>/Set<Identifier>`；`getActive()` = `Balm.config().getActiveConfig(ForgivingVoidConfig.class)`；效果列表用 `"namespace:effect|duration|amplifier"` 字符串 DSL（`applyFallThroughVoidEffects`，:119-136，含非法值容错）
- **数据驱动**：`ForgivingVoidRules` 走 Shogi（`shogi-api`），支持数据包覆盖 `falling_height`；Fabric 侧 `include(libs.shogiApi)`（`fabric/dependencies.gradle`）
- **datagen**：仅 i18n 导出，`fabric/.../fabric/datagen/ModDataGenerator.java` 调 `I18nExport.writeStaticI18nKeys(MOD_ID, new File("i18n.export.json"))`

## 6. Mixin
- 配置：`common/src/main/resources/forgivingvoid.mixins.json`（`required: true`，`defaultRequire: 1`，`compatibilityLevel: JAVA_17`）；另有 `forgivingvoid.{fabric,neoforge,forge}.mixins.json` 三个空 mixin 列表（仅保留扩展位），在 `neoforge.mods.toml` 通过 `[[mixins]] config=` 显式挂载
- 代表性 mixin（全部在 common）：
  - `mixin/CombatTrackerMixin.java`：`@Inject(method = "getFallMessage(...)Component", at = @At("HEAD"), cancellable = true)`，命中 `ForgivingVoidIsFalling` 时替换为 `death.fell.forgivingvoid`
  - `mixin/ServerPlayerAccessor.java`：`@Accessor void setIsChangingDimension(boolean)`
  - `mixin/ServerGamePacketListenerImplAccessor.java`：`@Accessor Vec3 getAwaitingPositionFromClient()`，用于跳过正在反作弊拉回中的玩家
  - `mixin/ThrownTridentAccessor.java`：`@Accessor("ID_LOYALTY") static EntityDataAccessor<Byte>`

## 7. 值得学的 5 条具体做法
1. **用 Accessor mixin 做原版私有状态读写而非 AT**：`ServerPlayerAccessor.setIsChangingDimension(true)` 复用原版"换维度中"标记来临时关掉反作弊，`ForgivingVoid.java:111-115`；适用：需触碰 `ServerPlayer`/`ServerGamePacketListenerImpl` 私有字段的场景
2. **多次连续判定避免误触发**：`entity.getY() < triggerAtY && entity.yo < triggerAtY`（:53）用前后两 tick 位置共同判定，适用：传送/击退类逻辑防抖
3. **载具乘客整体传送模板**：`isVehicle()/getVehicle()` 双向收集 + `ejectPassengers()` 后再 `startRiding()` 还原（:66-99），适用：任何实体传送类 mod
4. **脏状态自清理**：`FALL_CATCHING_BLOCKS` + `hasLanded()/isOrMayFly()` 兜底（:100-116、:171-192），因为原版事件不覆盖落水/飞行；适用：依赖原版回调但回调有缺口时
5. **配置值容错归一**：`damage > 1` 时自动 `/100f`、效果字符串解析失败打日志而非崩（:212-227、:126-134），适用：面向服主的数值型配置

## 8. 库/API 扩展点
本 mod 非库，但公开两类扩展点：Java 事件 `ForgivingVoidFallThroughEvent.EVENT`（BidirectionalEventMapper，可取消）与数据包规则 `ForgivingVoidRules.fallingHeight`（Shogi `intValue`，命名空间默认 `forgivingvoid`/`shogi`）。
