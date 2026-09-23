# TreyRuffy/BetterF3 源码分析报告

## 1. 基本信息

- Mod 名：BetterF3；mod_id：`betterf3`（NeoForge 侧包名 `me.treyruffy.betterf3`，common/Fabric 侧仍为 `me.cominixo.betterf3`）
- 作者：cominixo / TreyRuffy；许可证 MIT（`LICENSE.txt:1`）
- 目标：`gradle.properties:8` `minecraft_version=26.2`（新版本号方案，非 1.21.1）、`mod_version=19.0.0`、`platforms=fabric,neoforge`、`fabric_loader_version=0.19.3`、`neoforge_version=26.2.0.8-beta`
- Gradle 插件（`build.gradle:5-14`）：architectury-plugin 3.5、`dev.architectury.loom-no-remap` 1.14、indra 3.2.0（含 checkstyle/git）、spotless、errorprone 5.1.0、shadow 9.4.1、unified-publishing
- 编译依赖重点：`me.shedaniel.cloth:cloth-config`（必装，NeoForge 侧 mods.toml 中 `mandatory=true`）、ModMenu/`NeoForgeModMenu`（可选，`neoforge.mods.toml` 依赖段）、Fabric API；JSON/TOML 配置由内嵌库 `com.electronwill.night-config` 提供，并在 shadowJar 中 relocate 到 `me.cominixo.betterf3.libs.nightconfig`（`fabric/build.gradle` shadowJar 段）
- 质量工具：`build.gradle:41-52` 强制 NullAway（ERROR 级）+ JSpecify，注解包 `me.cominixo.betterf3,me.treyruffy.betterf3`

## 2. 源码规模与包结构

- 66 个 `.java`，共 **5594** 行（实测 `find . -name '*.java' | wc -l` / `wc -l` 汇总）；另有 3 个 JUnit5 测试类（`common/src/test/...`：`ModConfigFileGeneralOptionsTest`、`BaseModuleCachingTest` 等）
- 包分布（common 主源）：`modules` 17、`utils` 7、`config/gui/modules` 5、`mixin` 4、`mixin/{chunk,scoreboard,bossbar,autof3}` 各 2-3、`ducks` 3、`config` 3、`config/gui` 3
- 最大文件：`modules/BaseModule.java` 442、`config/gui/modules/EditModulesScreen.java` 304、`ModuleListWidget.java` 271、`modules/LocationModule.java` 242、`utils/DebugRenderer.java` 238、`config/ModConfigFile.java` 228、`modules/ChunksModule.java` 222、`modules/SystemModule.java` 189

## 3. 入口与注册

- Fabric：`fabric/src/main/java/me/cominixo/betterf3/BetterF3Fabric.java`，`ClientModInitializer#onInitializeClient` 中先 `Utils.modVersion(...)`，然后逐个 `new XxxModule().init()` / `init(PositionEnum.RIGHT)`，最后 `ModConfigFile.load(ModConfigFile.FileType.JSON)`。注意：仓库快照中**未见 `fabric.mod.json`**（`fabric/build.gradle` 有 `filesMatching("fabric.mod.json")` 展开逻辑但文件缺失，可能被裁剪/由构建生成，未确认）；Fabric 侧兼容级别为 `JAVA_21`。
- NeoForge：`neoforge/src/main/java/me/treyruffy/betterf3/BetterF3NeoForge.java`，`@Mod("betterf3")`，构造器判 `FMLEnvironment.getDist()==DEDICATED_SERVER` 直接告警跳过，否则 `ClientSetup.setup()`；仅在 `ModList.get().isLoaded("cloth_config")` 时注册 ModMenu 页，配置文件类型用 TOML。
- 注册框架：不使用 DeferredRegister/Registrate（纯客户端 HUD mod，无方块物品注册）；"注册"体现为**模块自注册**：`BaseModule.modules` / `modulesRight` / `allModules` 三个静态 List，`BaseModule.init()` 按 `PositionEnum` 投递（`BaseModule.java:125-143`），模块 id 由类名推导 `getSimpleName().replace("Module","").toLowerCase()`（`BaseModule.java:99`）。
- Mixin 注册：`neoforge.mods.toml` 用两段 `[[mixins]] config=`，同时挂载 `betterf3.neoforge.mixins.json` 与 common 的 `betterf3.mixins.json`；另有 `[[accessTransformers]] file=META-INF/accesstransformer.cfg`，common 用 AW `betterf3.accesswidener`。

## 4. 核心系统

1. **模块/行（DebugLine）数据驱动布局系统**（`modules/BaseModule.java`、`utils/DebugLine.java`、`utils/DebugLineList.java`）：每模块持有 `List<DebugLine> lines`；`DebugLine#value(Object)` 直接存任意值（String/Component/List），渲染时才用 `Component.translatable(this.format, nameStyled, valueStyled)` 组装（`DebugLine.java:73-86`）；行名走语言键 `text.betterf3.line.<id>`（`DebugLine.java:144`）；`value` 为空串时自动 `active=false` 隐藏该行。`DebugLineList` 用于"一行显示多个值列表"。模块可覆写 `loadModuleConfig/saveModuleConfig` 追加自己的配置字段（`BaseModule.java:374-385`）。
2. **配置持久化与顺序化**（`config/ModConfigFile.java`）：`saveRunnable` 静态 Runnable 写 JSON/TOML，结构为 `general` + `modules_left` + `modules_right` 数组；加载时保留旧格式 `modules` 分支兼容（`ModConfigFile.java:99-137`）。拖拽排序通过 `modules_left_order` 数组按模块 id 反序列化重建顺序；模块实例用 `moduleTemplate.getClass().getDeclaredConstructor().newInstance()` 反射重建（`ModConfigFile.java:188-207`），这是"配置决定布局"的关键做法。
3. **渲染与性能优化**（`utils/DebugRenderer.java`）：`newText()` 统一收集左右两栏；脏标记缓存：`BaseModule` 内 `dirty/cachedLines/cachedStateHash`，`markDirty()`、`refreshDirtyFromState()`、`stateHash()`（把 enabled+颜色+所有行的 `cacheStateHash()` 混入），`cachedLinesFormatted()` 命中缓存直接返回（`BaseModule.java:293-319`）；非每帧刷新的模块再叠加 `STATIC_REFRESH_INTERVAL_MS=250` 与 `IdentityHashMap<BaseModule,Long> LAST_UPDATE_TIMES` 限流（`DebugRenderer.java:26-42`）。整个开关由 `GeneralOptions.enablePerformanceOptimizations` 控制。
4. **滑动动画与显隐**（`utils/Utils.java` `xPos/START_X_POS=200/closingAnimation/lastAnimationUpdate` + `mixin/DebugMixin.java`）：`renderAnimation` 在 `DebugScreenOverlay#extractRenderState` 内按 `Util.getMillis()` 每 10ms 步进 `xPos`，靠 `graphics.pose().pushMatrix()/popMatrix()`（HEAD/TAIL 注入）保证矩阵成对。
5. **模块实现示例与鸭子接口**（`modules/ChunksModule.java` 222 行、`ducks/ClientChunkManagerAccess.java`）：用 `LINE_*` 常量索引定位行，通过 Mixin 把 `ClientChunkCache.Storage` 的私有 `chunks` 暴露成接口 `betterF3$getChunks()`（`mixin/chunk/ClientChunkMapMixin.java`、`ClientChunkManagerMixin.java`），而不是用反射/AT——客户端侧自定义数据访问的干净范式。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端，无包注册）。
- 配置：JSON（Fabric）/ TOML（NeoForge），night-config `FileConfig.builder(path).concurrent().autosave()`；所有字段集中在 `config/GeneralOptions.java` 的静态可变字段（含 `backgroundColor=0x6F505050`、`fontScale`、`hideBossbar`、`disableMod` 等 16 项）。
- 数据驱动：模块内容非资源包驱动，但**文本全部走语言键**（`text.betterf3.module.*`、`text.betterf3.line.*`、`format.betterf3.default_format`），由 Crowdin 翻译（`crowdin.yml`）；`assets/betterf3/lang/` 在当前快照中只有 README（语言文件应随构建获取，未确认）。
- datagen：无（无 `data/` 生成器目录）。

## 6. Mixin

- common `common/src/main/resources/betterf3.mixins.json`（`required=true`，client-only 列表 8 个）：`DebugMixin`、`DebugScreenEntryListMixin`、`KeyboardMixin`、`autof3.DebugOptionMixin`、`bossbar.BossbarMixin`、`chunk.ClientChunkManagerMixin`、`chunk.ClientChunkMapMixin`、`scoreboard.ScoreboardMixin`
- 代表性注入点：
  - `mixin/DebugMixin.java:74-100` — 两个 `@Redirect` 分别改 `DebugScreenEntryList#getCurrentlyEnabled()`（返回自定义 `BETTERF3_LIST`）与 `DebugScreenEntryList#isOverlayVisible()`（返回 false 以关闭原版渲染），是"替换原版 HUD"的核心；`extractRenderState` 另有 HEAD/TAIL 矩阵注入与 `getCurrentlyEnabled` INVOKE+`shift=AFTER` 处的字体缩放。
  - `mixin/KeyboardMixin.java:35` — `KeyboardHandler#handleDebugKeys` HEAD，`cancellable`，接管 F3 按键。
  - `mixin/autof3/DebugOptionMixin.java:43/53/63` — `DebugScreenOverlay#<init>`(RETURN)、`reset`(RETURN)、`showDebugScreen`(HEAD)；`DebugScreenEntryListMixin` 注入 `setOverlayVisible`(HEAD) 并用 `@Shadow isOverlayVisible` 直接改字段实现"关闭动画"。
  - `mixin/bossbar/BossbarMixin.java:31`、`mixin/scoreboard/ScoreboardMixin.java:29` — `BossHealthOverlay#extractRenderState`、`Gui#displayScoreboardSidebar` 的 HEAD `cancellable`，实现"看 F3 时隐藏侧边栏/Boss 条"。
- 平台侧：Fabric `FabricDebugMixin` 与 NeoForge `NeoForgeDebugMixin` 都注入 `DebugScreenOverlay#extractLines` HEAD（NeoForge 侧 `order = 2000`），因为该方法的可见性/签名两侧不同——**同一功能按平台拆 mixin** 的做法值得学。

## 7. 值得学的 5 条具体做法

1. **脏标记 + 状态哈希的 HUD 缓存**：`BaseModule.stateHash()` 把配置与渲染相关状态混成 int 与上次比较决定重算，配合 `cachedLinesFormatted()` 把"字符串拼接+翻译"这种昂贵操作压到只在变化时执行（`modules/BaseModule.java:281-319`）；适用于任何每帧渲染的性能敏感 HUD。
2. **按刷新频率给模块分级**：`updatesEveryFrame()` + 250ms 静态刷新阈值 + `IdentityHashMap` 记录上次更新时间（`utils/DebugRenderer.java:26-42`），避免所有模块每帧取样系统信息。
3. **用鸭子接口暴露私有字段替代反射**：`ducks/ClientChunkManagerAccess`、`ClientChunkMapAccess` + Mixin 实现 `betterF3$getChunks()`，调用处直接强转（`modules/ChunksModule.java` 导入这两个接口）。
4. **配置即布局**：保存 `modules_left/modules_right` 数组（每项含 `name/name_color/value_color/enabled/lines`）并从配置反射重建模块实例，读写对称（`config/ModConfigFile.java:32-77`、`modules/BaseModule.java:326-360`）；做可自定义 UI 布局的 mod 可直接抄这套对称 save/load。
5. **语言键驱动 + 自己写开发文档**：所有可见文本走 `text.betterf3.line.*` 语言键（`DebugLine.java:144`），并在 `docs/developers/CreateModule.md` 写明"扩展新模块的 6 步"（继承 `BaseModule` → 设颜色 → `lines.add(new DebugLine(...))` → 写 `update(Minecraft)` → 入口 `init()` → 加语言键），是小型 mod 对外提供扩展点的低成本方案。

## 8. 库/API 说明

非库模组，无公开 API artifact（`maven-publish` + indra 发布的是普通 jar）。对外扩展点仅有上文的"继承 `BaseModule` 并 `init()`"约定，无事件/注册接口，属于源码级扩展而非 API 级（`docs/developers/CreateModule.md`）。
