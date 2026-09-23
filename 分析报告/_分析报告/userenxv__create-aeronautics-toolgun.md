# userenxv/create-aeronautics-toolgun 源码分析报告

## 1. 基本信息

| 项 | 值 | 来源 |
| --- | --- | --- |
| Mod 名 | Create Aeronautics: Toolgun | `gradle.properties:29` |
| mod_id | `create_aeronautics_toolgun` | `gradle.properties:28` |
| 作者 | enxv233 | `gradle.properties:31` |
| MC / 加载器 | 1.21.1 / NeoForge 21.1.228 | `gradle.properties:13-14` |
| Gradle 插件 | `java-library`、`net.neoforged.moddev 2.0.141` | `build.gradle:1-5` |
| 许可证 / 版本 | CC-BY-NC-4.0（禁止商用）/ 0.3.6 | `gradle.properties:30` |
| group | `com.enxv.aeronauticsstructuretool` | `gradle.properties:32` |

**依赖（重点）**：`create [6.0.10,6.1.0)`；`sable [1.1.3,3.0.0)`（`build.gradle:187` 用 `api(...)`，物理/子关卡引擎）；`simulated`、`aeronautics`（`dev.eriksonn.aeronautics`）、`offroad`（`implementation`，`build.gradle:188-195`）；可选 `sable_schematic_api [0.4.0,)`。`primaryNestedJars` 被 `implementation` + `ext.legacyNestedJars` 用于 jarJar 式内嵌（`build.gradle:200-201`）。仓库还用 `gradle/verification.gradle` 额外拉了一套 **legacy Sable 1.1.3** 组合做兼容编译。

## 2. 源码规模与包结构

实测 331 个 `.java`、**45336 行**：`src/main` 313 文件 42609 行，`src/verification` 18 文件 2727 行。

按顶层包（`com.enxv.aeronauticsstructuretool`，depth-1 文件数）：`blueprint` 62、`compat` 52、`client` 48、`toolgun` 42、`printer` 12、`network` 12、`vehicle` 10、`server` 4、`mixin` 2、`core` 2，其余约 60 个类平铺在根包（多为 payload / item / enum）。

`blueprint` 二级子包：`capture / codec / compat / geometry / importer / lifecycle / material / model / placement / preview / runtime / security / storage`（全 13 个）。
`compat` 二级子包按目标 mod 切分：`aeronautics / cbc / common / copycats / create / drivebywire / hardblock / mianbao / offroad / sable / sableschematicapi / simulated / synaxis`。

最大文件：`vehicle/storage/StoredVehicleRepository.java` 962 行、`client/screen/ToolModeScreen.java` 948、`client/render/ClientItemRenderRegistry.java` 814、`client/render/ClientToolOverlayRenderer.java` 737、`client/render/SimpleWeldGhostRenderer.java` 699、`toolgun/magnetic/MagneticGunServerService.java` 634、`blueprint/placement/NativeBlueprintPlacementService.java` 524。

## 3. 入口与注册

主类 `src/main/java/com/enxv/aeronauticsstructuretool/AeronauticsStructureToolMod.java:27`（无 Mod 级注册框架，纯 `DeferredRegister`）：

```java
public AeronauticsStructureToolMod(IEventBus modBus, ModContainer modContainer) {
    modContainer.registerConfig(ModConfig.Type.SERVER, SurvivalToolgunConfig.SPEC);
    ModBlocks.register(modBus); ModBlockEntities.register(modBus);
    ModItems.register(modBus); ModCreativeTabs.register(modBus);
    ModPayloads.register(modBus);
    modBus.addListener(ModSetup::onCommonSetup);
    if (FMLEnvironment.dist == Dist.CLIENT) registerClientHooks(modBus);
    NeoForge.EVENT_BUS.addListener(AeronauticsStructureToolMod::onRegisterCommands);
    NeoForge.EVENT_BUS.addListener(AeronauticsStructureToolMod::onItemCrafted);
    ServerServices.register(NeoForge.EVENT_BUS);
}
```

关键点：**客户端钩子用反射隔离**（第 48-55 行 `Class.forName("...client.ClientHooks")` + `getMethod("register", IEventBus.class).invoke`），避免专用服务器加载客户端类；服务端对象统一登记在 `server/ServerServices.java:16-33` 的静态单例表里，再一次性 `gameBus.register(...)`。

## 4. 核心系统

**(1) 服务端会话 + 姿势事务** — `toolgun/transform/TranslationSessionManager.java:17`
`static final Map<UUID, TranslationSession> SESSIONS = new LinkedHashMap<>()` 以玩家 UUID 为键；`begin/adjust/finish` 三阶段，`adjust` 只累加 `pendingLocalOffset` 不改世界，`finish(confirm=false)` 直接丢弃即天然撤销（第 60-66 行）。所有落盘走 `ConstraintPoseTransaction.apply(level, subLevelId, consumer)`（`toolgun/constraint/ConstraintPoseTransaction.java`），配套 `RotationSessionManager`、`SubLevelRemovalCoordinator`。`finish` 里用 `SubLevelHelper.getConnectedChain(...)` 把变换扩散到整条连接链（第 71-89 行）。

**(2) 蓝图流水线** — `blueprint/` 下 13 个子包：`capture`（`ConnectedSubLevelCollector`、`NativeBlueprintCaptureService`）→ `codec`（`NativeBlueprintFormat`、`BlueprintArchiveCodec`、`NbtTagValidator`）→ `security`（`BlueprintBlockEntitySanitizer`：加载前清洗方块实体数据）→ `placement`（`NativeBlueprintPlacementService`，524 行，含 `BlueprintPlacementRollback` 回滚与 `PlacementTargetMath`）→ `runtime`（`RuntimeContraptionRestoreCoordinator` 恢复 Create 装置/约束）。另含 `importer/vmod`（Litematica 式 VMod 导入，5 文件）与 `material`（`BlueprintMaterialAnalyzer`、`EmbeddedMaterialScanner` 生存模式材料核算）。

**(3) 网络层** — `ModPayloads.java:26-67` 在 `RegisterPayloadHandlersEvent` 里用 `PayloadRegistrar` 注册 **40 个 payload**（`playToServer` 29 个、`playToClient` 9 个），Handler 按业务拆成 9 个 `*PayloadHandlers` 类放 `network/handler/`。复杂上传（蓝图分块）另走 `network/transfer/BlueprintLoadUploadManager`。

**(4) 磁力枪控制** — `toolgun/magnetic/MagneticGunServerService.java` + `MagneticDragPhysics` + `MagneticDragControlMath`（临界阻尼/四元数误差），含 `verifyMagneticDragControl` 回归任务校验数值。

**(5) 客户端 UI** — `client/screen/ToolModeScreen.java`（948 行）+ `client/screen/toolmode/`（9 个面板/Renderer 类）+ `client/tool/`（`ClientStructureToolHandler`、`ClientToolInputController`）+ `client/render/`（幽灵方块预览、光束、叠加层）。

**(6) 第三方兼容层** — `compat/`（52 文件）每个子包对接一个 mod（`drivebywire` 线控、`synaxis` 控制器、`hardblock`、`mianbao`、`cbc`、`copycats`、`simulated` 等），并各自带 `*RegressionCheck`。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：payload 全部是 `record ... implements CustomPacketPayload`，`STREAM_CODEC` 用 `StreamCodec.of(...)` 手写字段读写（如 `MagneticGunStartPayload.java:18-39`：UUID 拆两 long、double 直写），不用 `ByteBufCodecs` 组合。
- **配置**：仅一个 `SERVER` 配置 `SurvivalToolgunConfig.java`，`builder.push("survivalToolgun")` 下 7 个布尔（`allowSave/Query/Weld/SimpleWeld/Translate/Rotate/Disconnect`）+ 静态 getter；权限判定集中在 `toolgun/ToolgunAccessPolicy.java:21`（`rejectSurvivalFeature` 统一发受限提示）。
- **数据驱动**：无 datagen。蓝图以 NBT/自定义二进制格式存取，`NativeBlueprintFormat` 有版本号与 `LegacyPlotBlockCoordinates` 等兼容路径。
- **验证（本仓库最有特色的工程实践）**：`src/verification` 独立源集 + `gradle/verification.gradle` 定义 **17 个 `JavaExec` 验证任务**（`verifyBlueprintData`、`verifyBlueprintPlacement`、`verifyConstraintPersistentNbt`、`verifyMissingBiomeFallback`、`verifyCompatibilitySymbols` …）全部挂在 `check` 上；另有 `verifySourceHygiene` 用正则扫描源码，**直接 fail 构建**：空 catch 块、`if (true/false)` 硬编码分支、`System.out/err` 与 `printStackTrace`（`gradle/verification.gradle:32-56`）；`compileLegacySableJava` 用旧版 Sable 1.1.3 类路径重编译全部主源码验证 API 兼容（第 58-72 行）。

## 6. Mixin

配置 `src/main/resources/create_aeronautics_toolgun.mixins.json`（`required: true`、`compatibilityLevel: JAVA_21`），仅 2 个 mixin，都指向 Sable 内部实现：

- `mixin/compat/sable/RapierVoxelColliderBakeryMixin.java:19-24` — `@Pseudo` + `@Mixin(targets = "dev.ryanhcode.sable.physics.impl.rapier.collider.RapierVoxelColliderBakery", remap = false)`；两个 `@Redirect` 命中 `buildPhysicsDataForBlock(...)` 内的 `BlockSubLevelCollisionShape.getSubLevelCollisionShape` 与 `BlockState.getCollisionShape`，注入方法名带 mod 前缀 `createAeronauticsToolgun$bakeExtensionShapeWithCurrentState`，用 try/finally 保证还原（注释说明是在 2.0.3 上 backport 上游提交）。
- `mixin/compat/sable/PhysicsColliderBlockGetterAccess.java:8-15` — `@Invoker("setup")` 暴露 Sable 私有方法，同样 `@Pseudo` + `remap = false`。

即：**对第三方内部实现用 `targets` 字符串 + remap=false，对需要跨版本的注入点用 `@Redirect`+`require = 1`**。

## 7. 值得学的 5 条具体做法

1. **"累加待定值 → 确认才落盘"的会话模型**：`TranslationSessionManager.adjust` 只改 `pendingLocalOffset`，`finish(confirm=false)` 丢弃即撤销（第 60-66 行）；`ConstraintPoseTransaction.apply` 作为唯一世界写入出口。适用场景：任何需要"拖动预览 + 确认提交 + 中途取消"的结构编辑功能。
2. **把验证代码做成独立 Gradle 源集 + 任务，并挂到 `check`**：`gradle/verification.gradle:1-6, 179-198`，`src/verification` 只加进 classpath 不进 jar。适用场景：给纯逻辑（编解码、坐标换算、控制数学）写可离线跑的回归检查。
3. **用构建期正则扫描强制代码卫生**：`gradle/verification.gradle:32-56` 的 `verifySourceHygiene` 禁止空 catch / 常量化 if / 控制台输出，违规即 `GradleException`。适用场景：团队或多 AI 协作时防止"静默失败"代码混入。
4. **对可选/内部依赖全部下沉到 `compat/<modname>` 子包并只经一行反射/接口调用**：`compat/` 52 文件 13 个子包，主类只 `Class.forName("...client.ClientHooks")` 一次（`AeronauticsStructureToolMod.java:48-55`）。适用场景：核心代码必须能在目标 mod 缺失时正常加载。
5. **payload 用 record + 手写 `StreamCodec.of` 并把 Handler 按业务分文件**：`ModPayloads.java:26-67` 集中注册 40 条，`network/handler/` 拆 9 个 Handler 类。适用场景：payload 数量多、需要一眼看清"谁发谁收"时，集中注册表比分散在各类里更易审计。

## 8. 库 / API 视角

非前置库。本 mod 是 Sable / Create Aeronautics 的**消费者**：对外部只用到 `dev.ryanhcode.sable.api.SubLevelHelper`、`sable.api.block.BlockSubLevelCollisionShape`、`SubLevelContainer` 等 `api` 包，对内部实现（`sable.physics.impl.rapier.*`）才用 `@Pseudo` mixin。
