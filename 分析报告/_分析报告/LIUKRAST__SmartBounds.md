# LIUKRAST/SmartBounds 源码分析报告

## 1. 基本信息

- Mod 名：Create: Smart Bounds；mod_id：`smart_bounds`；作者：LiukRast（`gradle.properties: mod_authors`）
- 目标：Minecraft 1.21.1 + NeoForge 21.1.186（`gradle.properties: neo_version`，`minecraft_version_range=[1.21.1,1.22)`，`neo_version_range=[21,)`，`loader_version_range=[4,)`）；版本 1.0.0
- 依赖：`create` `[6.0.0,)` required 且 **`side="CLIENT"`**（`src/main/templates/META-INF/neoforge.mods.toml`，neoforge/minecraft 亦为 CLIENT）→ 纯客户端优化模组
- Gradle：`net.neoforged.moddev` 2.0.96 + `java-library` + `maven-publish` + Parchment（2024.11.17）；Java 21
- 编译依赖（`build.gradle`）：`com.simibubi.create:create-1.21.1:6.0.4-53:slim`（`transitive=false`）、`net.createmod.ponder:Ponder-NeoForge-1.21.1:1.0.46`、`dev.engine-room.flywheel:flywheel-neoforge-api-1.21.1:1.0.2`（api=compileOnly / 本体=runtimeOnly）、`com.tterrag.registrate:Registrate:MC1.21-1.3.0+62`
- **MixinExtras 以 jarJar 内嵌**：`implementation(jarJar("io.github.llamalad7:mixinextras-neoforge:0.5.0-rc.2"))`
- 许可证：MIT（mod_license），mods.toml 模板由 `generateModMetadata` 任务从 `src/main/templates` 展开生成

## 2. 源码规模与包结构

实测：**8 个 .java / 264 行**，全部位于单一包 `src/main/java/net/liukrast/smartbounds/mixin/`。资源只有 `src/main/resources/smart_bounds.mixins.json`。

按行数：`BeltBlockEntityMixin` 50、`FactoryPanelBlockEntityMixin` 81、`ChainConveyorBlockEntityMixin` 34、`PSIAndDeployerBlockEntitiesMixin` 27、`FrogPortBlockEntityMixin` 21、`RollerBlockEntityMixin` 19、`ArmBlockEntityMixin` 17、`PackagePortBlockEntityMixin` 15。无 `@Mod` 主类、无注册类、无 assets。

## 3. 入口与注册

**没有 Java 入口类**：整个模组由 mixin 配置驱动，`mods.toml` 仅声明 `[[mixins]] config = "smart_bounds.mixins.json"`，因此无需 `@Mod` 类（NeoForge 允许纯 mixin 模组）。注册框架、网络、配置、datagen 均无。

## 4. 核心系统（本仓库本质是「一个系统 + 8 个注入」）

职责：重写 Create 方块实体的**渲染包围盒**（render bounding box），并在必要时重做包围盒缓存策略，减少不可见 BE 的渲染与每帧 AABB 重建。

统一手法是注入 Create `SmartBlockEntity#createRenderBoundingBox()` 并改返回值：
- `ArmBlockEntityMixin.java`：`@Inject(method="createRenderBoundingBox", at=@At("RETURN"), cancellable=true)` → `cir.setReturnValue(cir.getReturnValue().deflate(1,1,1).move(0,1,0))`（在原盒基础上收缩，最省事的写法）。
- `BeltBlockEntityMixin.java`：`@Shadow public int beltLength`，自算 `aabb.expandTowards(...)`；`VERTICAL` 坡度只沿 `HORIZONTAL_FACING` 的轴方向展开，`UPWARD/DOWNWARD` 用 `switch` 决定 Y 分量。**缓存优化**：`@WrapWithCondition(method="tick", at=@At(value="INVOKE", target="...invalidateRenderBoundingBox()V"))`，配合 `@Unique private int smart_bounds$storedLength` 只在 `beltLength` 变化时放行（README：Create 原本每 tick 失效一次包围盒）。
- `ChainConveyorBlockEntityMixin.java` / `FactoryPanelBlockEntityMixin.java`：`at=@At("HEAD"), cancellable=true` 完全接管，遍历连接数据算 min/max：前者遍历 `that.connections`（相对 `BlockPos`），后者遍历 `panels` 的 `targetedBy.keySet().stream().map(FactoryPanelPosition::pos)` 与 `targetedByLinks.keySet()`。FactoryPanel 还有第二组注入：`read` 的 HEAD 记录连接总数到 `@Unique smart_bounds$connectionsSize`，TAIL 再算一次，只在计数变化且 `level.isClientSide` 时 `invalidateRenderBoundingBox()`。
- `PSIAndDeployerBlockEntitiesMixin.java`：一石二鸟 `@Mixin(value = {PortableStorageInterfaceBlockEntity.class, DeployerBlockEntity.class})`，用 `BlockStateProperties.FACING` 法线 ×2 展开；mixin 类 `extends SmartBlockEntity` 仅为能调 `getBlockState()/getBlockPos()`。
- `RollerBlockEntityMixin.java`：`HORIZONTAL_FACING` 法线，`expandTowards(n.getX(), n.getY()-1, n.getZ())`。
- `FrogPortBlockEntityMixin.java`：用 MixinExtras 表达式注入 —— `@Definition(id="target", field="...FrogportBlockEntity;target:...")` + `@Expression("this.target != null")` + `@ModifyExpressionValue(method="getRenderBoundingBox", at=@At("MIXINEXTRAS:EXPRESSION"))`，把条件改成「且 `target.getExactTargetLocation(...) != Vec3.ZERO`」，修 README 中「断链后包围盒一路扩到 0,0,0」的 bug。
- `PackagePortBlockEntityMixin.java`：`@WrapWithCondition(method="read", target="...invalidateRenderBoundingBox()V")` → `return !(instance instanceof FrogportBlockEntity)`，即 FrogPort 的失效交给它自己的逻辑，避免冗余失效。

## 5. 网络 / 数据驱动 / 配置 / datagen

全部为「无」。`build.gradle` 虽声明了 `data` run config 与 gametest 相关 systemProperty，但源码中无 provider、无 `GatherDataEvent`、无网络包、无 `ModConfigSpec`。

## 6. Mixin

- 配置：`src/main/resources/smart_bounds.mixins.json`；`package: net.liukrast.smartbounds.mixin`，`compatibilityLevel: JAVA_21`，`required: true`，`overwrites.requireAnnotations: true`，`injectors.defaultRequire: 1`，并声明 `"mixinextras": { "minVersion": "0.5.0-rc.2" }`（与 jarJar 内嵌版本对应）。
- `mixins` 段为空，8 个类全在 **`client` 段**（`ArmBlockEntityMixin`、`BeltBlockEntityMixin`、`ChainConveyorBlockEntityMixin`、`FactoryPanelBlockEntityMixin`、`PackagePortBlockEntityMixin`、`PSIAndDeployerBlockEntitiesMixin`、`RollerBlockEntityMixin`、`FrogPortBlockEntityMixin`），与 mods.toml 的 CLIENT 依赖声明一致。
- Hook 目标汇总：`createRenderBoundingBox`（RETURN 或 HEAD 注入）、`tick`/`read` 中的 `invalidateRenderBoundingBox()` 调用（`@WrapWithCondition`）、`FrogportBlockEntity#getRenderBoundingBox` 的条件表达式（`@ModifyExpressionValue`）。

## 7. 值得学的 5 条具体做法

1. **用 `@WrapWithCondition` 精确掐掉冗余的失效/重算调用**：不改 Create 方法体，只按条件放行 `invalidateRenderBoundingBox()`（`BeltBlockEntityMixin.java`、`PackagePortBlockEntityMixin.java`）；适用：优化其他 mod 的高频调用。
2. **用 `@Unique` 字段做「上次值缓存」判断是否真的需要重算**：`smart_bounds$storedLength` / `smart_bounds$connectionsSize`（`BeltBlockEntityMixin.java`、`FactoryPanelBlockEntityMixin.java`）；适用：每 tick 重算的昂贵状态。
3. **改写返回值优先选 `at=@At("RETURN")` + `cir.setReturnValue(旧值.deflate/expand...)`**（`ArmBlockEntityMixin.java`）；适用：只想在原逻辑结果上微调，最不易随上游实现变动而崩。
4. **`@Mixin` 多目标数组一次覆盖多个同类 BE**（`PSIAndDeployerBlockEntitiesMixin.java`）；适用：多个类有同名同签名方法。
5. **客户端专属模组只靠 mixins.json 的 `client` 段 + mods.toml 的 `side="CLIENT"` 落地，不写主类**；适用：纯渲染/性能补丁型附属（但要接受无生命周期回调）。

（非库模组，第 8 节不适用。）
