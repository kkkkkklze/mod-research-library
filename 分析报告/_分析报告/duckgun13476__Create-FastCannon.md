# duckgun13476/Create-FastCannon 源码分析报告

## 1. 基本信息

- Mod 名：Create: Fast Schematic Cannon（CFC，中文名"机械动力：更快的蓝图加农炮"）；mod_id `createfastschematiccannon`；作者 Pink_Cats；版本 1.4.1-0.5.1j（git 分支 `1.20.1-forge-0.5.1f`，commit `a5c5884`）。
- 目标/加载器：MC **1.20.1 + Forge 47.4.8**（`gradle.properties:44-47`），Java 17（`gradle/java.gradle:3`）；构建用 `net.neoforged.moddev.legacyforge` 2.0.74（新 ModDev 的 Forge 兼容模式，非 ForgeGradle）+ `net.darkhax.curseforgegradle` + `dev.ithundxr.silk` 0.11.15 + `me.modmuss50.mod-publish-plugin`（`build.gradle:7-12`）。
- 许可证：MIT（`gradle.properties:7`、`src/main/resources/META-INF/mods.toml:3`）。
- 依赖：**Create** `curse.maven:create-328085:5838779`（mods.toml 声明 `[0.5.1.f,0.5.2)` mandatory、ordering=AFTER）+ Registrate（`build.gradle:170-172`）；MixinExtras 0.4.1（compileOnly + annotationProcessor）；observable / architectury-api / kotlin-for-forge 由 curse.maven 拉入（Create 传递需要）。JEI/Curios/Ponder 版本只写在 gradle.properties，实际依赖被注释。
- 工程特点：`build.gradle:262-275` 的 `publishCurseForge`/`publishMods` 任务会**强制读取 `api.properties`（CF_TOKEN/MODRINTH_TOKEN）**，缺文件即构建报错；jar manifest 写入 `MixinConfigs` 与 `git rev-parse` 得到的 Git-Hash，changelog 从 `update/changelog.md` 取。

## 2. 源码规模与包结构

- 仅 **4 个 `.java` 文件、544 行**（`find . -name '*.java' | wc -l`；`cat | wc -l`），是纯 mixin 型小型附属。
- 全部在 `src/main/java/com/Pink_Cats/createfastschematiccannon/`：`Config.java`(118)、`mixin/SchematicCannonBlockEntityMixin.java`(379)、`Createfastschematiccannon.java`(33)、`mixin/SmartBlockEntityMixin.java`(14，**空类，遗留占位**)。
- 资源只有 `src/main/resources/createfastschematiccannon.mixins.json` 与 `META-INF/mods.toml`，**无任何 assets/data 内容**。

## 3. 入口与注册

主类 `src/main/java/com/Pink_Cats/createfastschematiccannon/Createfastschematiccannon.java:14`，`@Mod(MODID)`，Forge 旧式入口 `FMLJavaModLoadingContext.get().getModEventBus()`，构造器只做三件事（`:21-26`）：注册 commonSetup 监听、`MinecraftForge.EVENT_BUS.register(this)`、`ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, Config.SPEC)`。没有任何方块/物品注册——所有功能都通过对 Create 的蓝图炮（Create 0.5.1 中 `SchematicannonBlockEntity`，作者沿用旧译名"蓝图炮"）打 mixin 实现。

## 4. 核心系统

1. **加速核心：整段重写 `tick`** `mixin/SchematicCannonBlockEntityMixin.java:65-120`。`@Inject(method = "tick", at = @At("HEAD"), cancellable = true, remap = false)` → 先 `super.tick()`，再把 Create 原本的 tick 主体**复制**进 `for (int x = 0; x < Config.SchematicSpeedupPerTick; x++)` 循环（含 `neighbourCheckCooldown`、`tickFlyingBlocks/tickPaperPrinter/refillFuelIfPossible`、`while (blockSkipped && skipsLeft-- > 0) tickPrinter()`、`schematicProgress` 计算与 `sendBlockUpdated(..., 6)`），最后 `ci.cancel()` 丢弃原方法体。mixin 类本身 `extends SmartBlockEntity implements MenuProvider` 并在构造器转发，以通过 `super.tick()` 类型检查。
2. **闲置降频（lazyTick）**：两个 `@Unique` 字段 `MissingTick/MissingCount`（`:44-45`），`@Inject` 到 `tickPrinter` 中 `refillFuelIfPossible()` 之后与 `statusMsg` 的 `PUTFIELD, ordinal = 5` 之后置位（`:205-234`）——无燃料时把 tick 提前 cancel 并每 `Config.lazyTick` 刻放行一次，配合 `Config.lazyTick` 范围 1-200。
3. **方块黑名单（防"无尽锅炉"）** `:249-286`：`@Redirect` 包住 `SchematicPrinter.handleCurrentTarget`，把传入的 `BlockTargetHandler` 换成自己的 lambda，先查 `Config.blocks_unbreak.stream().anyMatch(targetstring::equals)`（`targetstring` 由 `block.toString()` 正则剥掉 `Block{...}` 得到，默认 `create:blaze_burner`），命中则 `blockSkipped = true; statusMsg = "searching"` 直接 return，不调用原 handler；`Config.enable_debug` 时打日志。另有 `@Inject` 到 `initializePrinter`（HEAD，cancellable，`:129-199`）复制原校验逻辑并新增"锚点超距只报错一次"的 `IsNotLoad` 状态。
4. **火药续燃扩展** `:299-378`：`@Inject` 到 `refillFuelIfPossible`（HEAD，cancellable）复制原逻辑并加入 `gunpowder_blocks_compat` 分支——硬编码 descriptionId 列表 `createfastschematiccannon$charge = ["block.cratedelight.gunpowder_bag"]`，从附属容器中抽取 1 个该物品转换为 9 个 `Items.GUNPOWDER` 塞进槽位 4。
5. **配置** `Config.java`：`ForgeConfigSpec` 6 项——`EnableCannonSpeedUp`、`SpeedupPerTick`(1-400，默认 20)、`lazyTick`(1-200，默认 5)、`blocks_unbreak`(列表，带 `validateItemName` 校验)、`debug`、`gunpowder_blocks_compat`（每项都是中英双语 comment）；`LoadPara()` 在 `ModConfigEvent.Loading/Reloading` 时把配置值刷进静态字段供 mixin 直接读取（`:98-117`）。
   - **实测缺陷**：`enable_CFC` 只在 `Config.java:85,111` 被赋值，全仓库无任何读取点（`grep -rn enable_CFC src/main/java` 仅这两处）——即 `EnableCannonSpeedUp` 开关当前无效。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：无（纯单机/服务端逻辑改动，不需要同步包）。
- 数据驱动：无（无 data/ 目录，黑名单写在配置而非数据包）。
- 配置：如上，Forge COMMON 配置 + 静态字段热读写模式。
- datagen：`build.gradle` 里有 `data()` run 与 `sourceSets.main.resources { srcDir 'src/generated/resources' }`，但仓库无 `src/generated/resources`，**无 datagen 类**。

## 6. Mixin

- 配置：`src/main/resources/createfastschematiccannon.mixins.json`——`required: true`、`priority: 1200`、`compatibilityLevel: "JAVA_8"`（对 Java 17 已过时，未确认是否告警）、`refmap: createfastschematiccannon.refmap.json`、`injectors.defaultRequire: 1`、`overwrites.requireAnnotations: true`；在 jar manifest 的 `MixinConfigs` 中声明（`build.gradle:230`），dev run 额外传 `-mixin.config=create.mixins.json` 并开 `mixin.debug.export/verbose`（`:120-124`）。
- 两个 mixin 类（列表由 json 手写维护）：`SchematicCannonBlockEntityMixin`（目标 `SchematicannonBlockEntity`，注入点：`tick` HEAD、`initializePrinter` HEAD、`tickPrinter` 的 `INVOKE refillFuelIfPossible` 后 / `statusMsg` PUTFIELD ordinal 5 后 / `shouldPlaceCurrent` 后、`refillFuelIfPossible` HEAD、`handleCurrentTarget` Redirect）；`SmartBlockEntityMixin`（目标 `SmartBlockEntity`，无注入，空壳）。

## 7. 值得学的 5 条

1. 想给 Create 机器加"一次 tick 干 N 次活"时，用 `@Inject(HEAD, cancellable=true)` + 在 mixin 内 `super.tick()` 再手写原逻辑外套一层 for 循环（`SchematicCannonBlockEntityMixin.java:65-120`）——比逐处 `@ModifyConstant` 注入更直接可控。
2. 用 `@Redirect` 包住 Create 传进来的 `BlockTargetHandler`/handler lambda 做"行为插桩"（`:249-286`），可以只替换一步判断而不重写整个方法——适用于 Create 系列的所有 `handleCurrentTarget`/`ITargetHandler` 模式。
3. 配置统一走 `LoadPara()` + 静态字段热读取，mixin 里直接 `Config.xxx`（`Config.java:110-117`）——避免在热路径上反复 `SPEC.get()`。
4. 用 `@Inject` 的 `at = @At(value="FIELD", opcode=PUTFIELD, ordinal=N)` 精确锚定原方法第 N 次对某字段赋值（`:221-234`）——定位混乱大方法里的特定分支，比数行号稳。
5. 发布流水线参考：`curseforgegradle` + `mod-publish-plugin` 同存、`git rev-parse` 结果写 manifest、changelog 从 `update/changelog.md` 读取、`api.properties` 存 token（`build.gradle:230-275`）——适用于给自己的附属做一键双平台发布（注意别把 token 文件提交进仓库）。

反面提醒（移植/维护）：`enable_CFC` 是死配置（:`Config.java:85`）、`compatibilityLevel` 仍写 `JAVA_8`、方块黑名单用 `Block.toString()` 字符串比较、`SmartBlockEntityMixin` 空类未删；以及大幅复制 Create 原方法体，Create 版本一变就要重抄——升级 Create 时这几处是首要风险点。

## 8. 公开 API

无（不导出 API，无对外扩展点；功能完全由 COMMON 配置 + mixin 决定）。
