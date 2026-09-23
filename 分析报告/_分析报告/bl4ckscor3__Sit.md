# bl4ckscor3/Sit 源码分析报告

> 前提：本地 `_bulk/bl4ckscor3__Sit` 检出的是**默认分支 `26.1.1`**（commit 2f08957，"Fix compatibility with NeoForge 26.1.2.21-beta"），即 MC 26.1.2 / NeoForge 26.1.2.27-beta / Java 25（`gradle.properties`）。因此代码里出现的是新 API 名（`Identifier` 取代 `ResourceLocation`、`ValueInput/ValueOutput` 取代 CompoundTag、`hurtServer`、`BreakBlockEvent`）。移植到 1.21.1/1.20.1 时需自行对照旧分支。

## 1. 基本信息

- Mod 名 / mod_id：Sit / `sit`；作者 bl4ckscor3；许可证 **MIT**；版本 1.5.2
- 目标：MC 26.1.2，三模块 `common` / `fabric` / `neoforge`（`settings.gradle`）
- Gradle：根 `build.gradle` 统一 `subprojects` 配置（jar 输出到 `../build/libs`、`processResources` 用 `expand` 把 `neoforge.mods.toml` / `fabric.mod.json` / `*.mixins.json` 里的 `${mod_id}` 等占位符展开）；`common` 与 `neoforge` 用 `net.neoforged.moddev`（`neoFormVersion` / `version`），`fabric` 用 `net.fabricmc.fabric-loom`
- 关键依赖：**`fuzs.forgeconfigapiport`**（common 用 `forgeconfigapiport-common-neoforgeapi`，fabric 用 `forgeconfigapiport-fabric:v5`）+ `mixinextras-common 0.3.5`（含 annotationProcessor）；maven 源用 Fuzss modresources（`build.gradle` repositories）
- 平台共享技巧：`fabric/build.gradle`、`neoforge/build.gradle` 都 `source(project(":common").sourceSets.main.allSource)` + `from project(":common").sourceSets.main.resources`，即**不发布 common jar，直接编译进各平台 jar**

## 2. 源码规模与包结构（实测）

- 12 个 `.java`，总 **586 行**。common 8（含 mixin 1）、neoforge 3、fabric 2
- 包根 `bl4ckscor3.mod.sit`：`mixin`(1)；资源 `common/src/main/resources/sit.mixins.json`
- 最大文件：`common/.../SitUtil.java` 144、`SitHandler.java` 117、`SitEntity.java` 83、`neoforge/.../NeoEntrypoint.java` 56

## 3. 入口与注册

跨加载器最小抽象：一个 `Platform` 接口（单方法 `register(ResourceKey<? extends Registry<R>>, Supplier<T> entry, String path)`）+ 平台无关的 `Sit.initialize(Platform)`，重复调用抛 `IllegalArgumentException`。实体用懒初始化 `Suppliers.memoize`：

```java
public static final Supplier<EntityType<?>> SIT_ENTITY_TYPE = Suppliers.memoize(() -> EntityType.Builder
    .<SitEntity>of(SitEntity::new, MobCategory.MISC).clientTrackingRange(256).updateInterval(20)
    .sized(0.0001F, 0.0001F).build(ResourceKey.create(Registries.ENTITY_TYPE, SIT_ENTITY_ID)));
```

（`common/src/main/java/bl4ckscor3/mod/sit/Sit.java`）

- NeoForge：`@Mod(Sit.MODID) @EventBusSubscriber class NeoEntrypoint implements Platform`，内部按需缓存 `DeferredRegister`（`Map<ResourceKey<? extends Registry<?>>, DeferredRegister<?>>`，第一次 register 时创建并 `r.register(modBus)`）；配置走原生 `modContainer.registerConfig(ModConfig.Type.SERVER, Configuration.CONFIG_SPEC)`；事件用 `@SubscribeEvent` 静态方法（`PlayerInteractEvent.RightClickBlock`、`BreakBlockEvent`）
- Fabric：`FabricEntrypoint implements ModInitializer, Platform`，直接 `Registry.register(...)`，配置走 `ConfigRegistry.INSTANCE.register(MODID, ModConfig.Type.SERVER, Configuration.CONFIG_SPEC)`
- 客户端：`NeoClientEntrypoint`（`@Mod(dist=CLIENT)` 里 `registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new)` + `EntityRenderersEvent.RegisterRenderers` → `NoopRenderer`）；Fabric 用 `ConfigScreenFactoryRegistry` + `EntityRenderers::register`

## 4. 核心系统

1. **座位实体** `SitEntity extends Entity`：`noPhysics = true`，构造时定位到方块中心 `pos + 0.5`；`defineSynchedData` / `readAdditionalSaveData(ValueInput)` / `addAdditionalSaveData(ValueOutput)` **全部空实现**（不需要任何同步字段，纯靠原版 add-entity + 骑乘同步）；`shouldRender` 返回 false、`hurtServer` 返回 false（不可被攻击）；`remove(RemovalReason)` 里反查映射表清理
2. **座位占用表** `SitUtil`：`Map<Identifier, Map<BlockPos, Pair<SitEntity, Vec3>>> OCCUPIED`，**只在服务端填充**，键为维度 id → 方块坐标 → (座实体, 玩家坐下前的坐标)。所有查询都先 `if (!level.isClientSide())` 短路，客户端永远返回 null/false
3. **坐下判定** `SitHandler.onRightClickBlock`：要求服务端 + 点击面 `Direction.UP` + 未在坐 + 未潜行 + 主手空 + 上方为空气 + `isPlayerInRange`（AABB 包围盒，参数 `block_reach_distance`，为 0 时必须站在方块正上方）；方块白名单 = Slab/Stair/（可选的第三方扩展 `isModBlock`，当前恒 false）+ 半张床（`BedBlock` 且对向方块不是床）；Slab 的 `SlabType.BOTTOM`、Stair 的 `Half.BOTTOM` 直接 `InteractionResult.PASS`
4. **下座与拆除**：`SitEntity.getDismountLocationForPassenger` 先取回坐下前坐标并 `discard()`，若下方方块不是完整坚固面（`isFaceSturdy(..., SupportType.FULL)`）则把玩家抬高 1 格防止卡进地面；`SitHandler.onBreak` 在方块被破坏时 `ejectPassengers()`
5. **Mixin 修原版行为**：`mixin/ServerGamePacketListenerImplMixin.java` 用 MixinExtras `@WrapOperation(method="handleUseItemOn", target="…ServerPlayer;sendBuildLimitMessage(ZI)V", ordinal=5)` 把这次调用整体替换为空方法体（方法名 `makeTheGameNotLie`），消除"在建筑高度上限外右键方块"的误报提示

## 5. 网络 / 数据驱动 / 配置

- **网络：无**（0 个自定义包），完全依赖原版实体生成与 `startRiding` 同步
- **配置**：单个 SERVER 配置 `ModConfigSpec`，字段 `block_reach_distance`（`defineInRange(..., 4, 0, 1000)`）；Fabric 上通过 ForgeConfigAPIPort v5 复用**同一 ModConfigSpec 与同一个 NeoForge `ConfigurationScreen`**，实现两平台一套配置代码 + 一套配置界面
- **数据驱动 / datagen：无**

## 6. Mixin

- `common/src/main/resources/sit.mixins.json`（package `bl4ckscor3.mod.sit.mixin`，`mixins: ["ServerGamePacketListenerImplMixin"]`，`compatibilityLevel: JAVA_25`），由 `processResources` 展开占位符
- 唯一 hook 点：`ServerGamePacketListenerImpl#handleUseItemOn` 中第 5 次 `sendBuildLimitMessage` 调用（`@WrapOperation`）

## 7. 值得学的具体做法

1. **单接口 Platform + 静态 initialize**：跨加载器抽象压到最小（1 个接口 1 个方法），注册项用 `Supplier` + `Suppliers.memoize` 延迟到注册时刻求值（`Sit.java`）——适合"只有 1~3 个注册项"的小 mod
2. **共享源集而非共享 jar**：`fabric/neoforge` 的 build 里 `source(project(":common").sourceSets.main.allSource)`（`fabric/build.gradle`、`neoforge/build.gradle`）——避免 public API 泄漏与 maven 发布负担
3. **"位置 → 实体"映射表**：用 `Map<BlockPos, Pair<SitEntity, Vec3>>` 替代遍历世界找座位实体，同时顺手存下"坐下前坐标"用于精确下座（`SitUtil.java`）
4. **极限精简的实体**：`sized(0.0001F)`、`noPhysics`、`shouldRender=false`、无同步数据、不可伤害——把实体当"看不见的座位标记"用（`SitEntity.java`）
5. **`@WrapOperation` 精确移除单个原版调用**（按 `ordinal` 定位）比 `@Overwrite`/`@Redirect` 更安全地"去掉某一处提示/副作用"（`ServerGamePacketListenerImplMixin.java`）
6. **ForgeConfigAPIPort 复用 NeoForge 配置 API + 配置界面**：Fabric 侧零成本得到 `ConfigurationScreen`（`FabricClientEntrypoint.java`）

## 8. 无

非库/前置 mod，只依赖 ForgeConfigAPIPort 与 MixinExtras，不对外提供 API。
