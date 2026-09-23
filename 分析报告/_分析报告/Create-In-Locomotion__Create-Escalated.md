# Create: Escalated 源码分析

## 1. 基本信息
- Mod 名 / mod_id：Create: Escalated / `escalated`（版本 1.3.2）
- 作者：rbasamoyai（README 自称 rbasamoyai mod）
- MC 1.21.1 + NeoForge（`gradle.properties: neoforge_version=21.1.228`，loader range `[4,)`），Java 21，Parchment 2024.11.17
- Gradle：`net.neoforged.moddev` 2.0.139 + `java-library` + `maven-publish`；`src/main/templates/META-INF/neoforge.mods.toml` 走 `generateModMetadata` 占位符替换
- 许可证：MIT（mods.toml）
- 编译依赖（谁是谁的 API）：Create `com.simibubi.create:create-1.21.1:6.0.10-280`（transitive=false，**它是 Create 附属**）、Ponder `net.createmod.ponder:ponder-neoforge:1.0.82`、Flywheel api/runtime 1.0.6、Registrate `MC1.21-1.3.0+67`、可选 `dev.ryanhcode.sable:sable-neoforge-1.21.1:2.0.5`（用 `api` scope 暴露）

## 2. 源码规模与包结构
64 个 `.java`，6373 行（实测）。包（`src/main/java/rbasamoyai/escalated/`）：
- `walkways/` 22 文件（核心）、`index/` 15（注册）、`handrails/` 7、`datagen/` 5、`config/` 3、`advancements/` 2、`compat/sable/` 2、`mixin/compat/sable/` 1、`platform/` 1、`ponder/` 1
- 最大文件：`walkways/WalkwayConnectorItem.java`(523)、`walkways/AbstractWalkwayBlock.java`(492)、`walkways/WalkwayBlockEntity.java`(354)、`walkways/WalkwayMovementHandler.java`(297)、`index/EscalatedBlocks.java`(294)、`ponder/WalkwayPonders.java`(280)
- 资源极简：`src/main/resources` 只有 `escalated.mixins.json`（贴图/模型/lang 未包含在此快照，未确认）

## 3. 入口与注册
`CreateEscalated.java:19` 持有 `CreateRegistrate REGISTRATE = CreateRegistrate.create("escalated")`；`init()` 调 `ModGroup.register()`（清空默认创造标签）+ `EscalatedBlocks/Items/BlockEntities.register()`。NeoForge 侧 `CreateEscalatedNeoForge`（`@Mod`）做 `REGISTRATE.registerEventListeners(modBus)`、`EscalatedConfigs.registerConfigs(mlContext.getActiveContainer()::registerConfig)`、注册 `RegisterEvent`（数据组件 + 触发器）、`ServerTickEvent.Post` 与 `ServerStoppingEvent`。注册框架 = **Create 的 CreateRegistrate 链式注册**，配合 `EscalatedBuilderTransformers` 生成 blockstate/model，`.transform(TagGen.pickaxeOnly())` 加挖掘标签，`.tag(AllTags.AllBlockTags.SAFE_NBT.tag)` 允许蓝图 NBT。创造标签用原生 `DeferredRegister<CreativeModeTab>`（`ModGroup.java:25`），`withTabsBefore(Create.asResource("palettes"))` 插到 Create 标签后。

## 4. 核心系统
1. **自动步道链条/控制器**（`walkways/WalkwayBlock.java` 静态 `initWalkway/getWalkwayChain/nextSegmentPosition` + `WalkwayBlockEntity`）：终端→斜坡→中段逐段推进（`WalkwaySlope.TERMINAL/TOP/MIDDLE/BOTTOM/HORIZONTAL`），每段记录 `controller` 位置，`isController()` 才跑动画与 `updateNeighbors()` 宽度扫描；`propagateRotationTo` 用 `getController().equals()` 保证同一链条转速一致；`calculateStressApplied` 只在控制器上返回应力。
2. **实体输送**（`WalkwayMovementHandler`，注释明示 "Adapted from BeltMovementHandler"）：`TransportedEntityInfo{ticksSinceLastCollision,...}` 存在 BE 的 `passengers` map 中，>3 tick 无碰撞视作离带；`canBeTransported`（潜行玩家不算）；对角/斜坡用 `movement.add(0,±|axis.choose(...)|,0)`；玩家有移动输入时走 `applyPlayerInputCombinedMovement`（按输入点乘 0.2/0.35/0.55 分级助推），否则直接 `entity.move(SELF, ...)`；非玩家生物临时把 `Attributes.STEP_HEIGHT` 设为 1.0 再还原（`:129-134,180-182`）。
3. **连接器物品**（`WalkwayConnectorItem` 523 行，`extends BlockItem`）：`useOn`→`canConnect`/`createSteps` 现场铺整条步道，`registerBlocks(map,item)` 把整套方块都指回同一物品；起点位置存在**数据组件** `EscalatedDataComponents.WALKWAY_FIRST_TERMINAL`（`persistent(BlockPos.CODEC)+networkSynchronized(BlockPos.STREAM_CODEC)`）。
4. **材质变体抽象**（`walkways/WalkwaySet.java`）：接口 + `record Impl(NonNullSupplier<Block> narrow,wideSide,wideCenter,terminal,handrail)`，`EscalatedWalkwaySets` 提供 metal/wooden × walkway/escalator 四套，新材质只需加 4 个方块。
5. **Flywheel 渲染**（`WalkwayVisual/WalkwayRenderer` + 自建 `index/EscalatedInstanceTypes.HANDRAIL` 用 `SimpleInstanceType.builder(HandrailInstance::new)`；`EscalatedBlockPartials.resolveDeferredModels()`）：`visualProgress` 按 `getSpeed()/480f` 累加并取 0.5 模，客户端与控制器同步（`WalkwayBlockEntity.read` 里按速度补偿一帧）。
6. **手扶栏杆**（`handrails/`）：`AbstractHandrailBlock.placeHandrail` 复用 Create 的 `AllItems.BELT_CONNECTOR` 作为安装器（`WalkwayHelper.isHandrail`），染色的 `applyColor` 沿链条+宽度方向广播到所有段。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无自建包（只有 `notifyUpdate`/`sendData` 之类 Create 既有同步与数据组件网络同步）。
- 数据组件：`index/EscalatedDataComponents.java`。
- 配置：`EscalatedConfigBase extends net.createmod.catnip.config.ConfigBase`，`EscalatedConfigs` 用 `EnumMap<ModConfig.Type,ConfigBase>` + `ModConfigSpec.Builder().configure(...)`（照抄 Create 的 `AllConfigs`），游戏内界面注册 `IConfigScreenFactory → BaseConfigScreen`（Create 的配置 UI，在 `FMLLoadCompleteEvent` 里注册）。
- datagen：`datagen/EscalatedDataGeneration.java` 用 `@EventBusSubscriber`，`onGatherRegistrateData` 标 `HIGHEST`、`onGatherData` 标 `LOWEST`；含 `EscalatedBuilderTransformers`（Registrate 模型/blockstate）、`EscalatedLangGen`、`EscalatedCraftingRecipeProvider`、`EscalatedPartialsGen`（`evt.includeClient()`）、Ponder lang（`PonderIndex.getLangAccess().provideLang`）。
- 进度：`WalkwayTravelTracker` 静态 `Reference2ObjectArrayMap<Player,Info>`，在 `ServerTickEvent.Post` 里 tick；玩家在步道上累计 100 格高度差触发 `EscalatorTriggers.ESCALATOR_100` 与下界版；`ServerStopping` 清理。

## 6. Mixin
- 配置：`src/main/resources/escalated.mixins.json`（`required:true`，`JAVA_17`），`"plugin": "rbasamoyai.escalated.EscalatedMixinPlugin"`
- 唯一 mixin：`mixin/compat/sable/AbstractWalkwayBlockMixin` — `@Mixin(AbstractWalkwayBlock.class) implements BlockWithSubLevelCollisionCallback`，无 `@Inject`，纯接口注入（给 Sable 物理体提供碰撞回调 `WalkwayBlockCallback.INSTANCE`）
- 插件 `EscalatedMixinPlugin.shouldApplyMixin`：包名以 `mixin.compat.sable` 开头且 `EscalatedModsNeoForge.SABLE.isLoaded()==false` 时返回 false

## 7. 值得学的 5 条做法
1. **用 mixin 插件按 mod 有无开关兼容 mixin**：`EscalatedMixinPlugin.java:17`，避免为可选前置换依赖。
2. **给可选兼容留运行时扩展点而非 mixin**：`WalkwayMovementHandler.addWalkwayTransformer` + `TRANSFORMERS`（`:270-295`），Sable 子空间坐标变换由 `compat/sable/SableCompat` 注入（`getEntityPos/transformMovement`）。
3. **多材质 = 接口 + record 供应商**：`WalkwaySet.Impl` 用 `NonNullSupplier<Block>` 延迟取块，风格适合任何"同一逻辑多套材质方块"的附属 mod。
4. **临时改属性基值实现"上台阶"**：输送非玩家实体时 `getAttribute(STEP_HEIGHT).setBaseValue(1.0f)` 并在结束时还原（`WalkwayMovementHandler.java:129-182`）。
5. **item 状态用数据组件而非 NBT**：`DataComponentType<BlockPos>` 同时 `persistent`+`networkSynchronized`，客户端可直接读连接起点。
6. 补充：客户端入口单独用 `@Mod(value=MOD_ID, dist=Dist.CLIENT)`（`CreateEscalatedNeoForgeClient`）+ `platform/EnvExecute.executeOnClient` 隔离专用服类加载；兼容检测用枚举 `EscalatedModsNeoForge`（`LoadingModList.get().getModFileById`，注释说明抄自 Create 的 Mods）。

## 8. 是否库/前置
非库 mod；但它对外提供了可用的扩展点：`WalkwayMovementHandler.WalkwayTransformer`（实体位置/位移变换）、`WalkwaySet`（新材质步道注册，见 4.4）。外部 mod 接入方式为直接调用静态注册方法（`addWalkwayTransformer`）。
