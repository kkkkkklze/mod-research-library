# BmtUltra/Kaleidoscope-Compat（森罗物语兼容层）源码分析

## 1. 基本信息

- Mod 名 / mod_id：Kaleidoscope Compat（森罗物语系列兼容层）/ `kaleidoscope_compat`，版本 `2.10.0-neoforge+mc1.21.1`
- 作者 / 许可证：BmtUltra / `MIT + CC BY-NC-SA 4.0`（代码 MIT、数据包资源 CC BY-NC-SA）
- 目标版本与加载器：MC 1.21.1 + NeoForge 21.1.228，Java 21，parchment 2024.11.17
- Gradle：`net.neoforged.moddev 2.0.119`（NeoGradle 时代已过）、`jarJar` 内嵌 `blank:resourcefulconfig:neoforge-1.21-3.0.11`、AT 文件 `src/main/resources/META-INF/accesstransformer.cfg`、mixin 配置在 `neoforge.mods.toml` 的 `[[mixins]]` 块
- 编译依赖（重点，分层极清晰）：**核心依赖** `kaleidoscope-cookery 1.4.1`（`implementation`，主 mod 本体）；**大量 `compileOnly` 联动**：create 6.0.10、create-central-kitchen、create-dragons-plus、`net.createmod.ponder`、aeronautics 1.3.0 + simulated + sable（RyanH/EngineRoom maven）、farmers-delight 1.21.1-1.3.2、farm_and_charm(lets-do)、vinery、youkaisfeasts、botany-pots、mystical-agriculture、curios 9.5.1、accessories、quark+zeta、spectrum、touhou-little-maid、thirst-was-taken/reclaimed、sol-carrot(spice-of-life)、appleskin、emi/rei/jei、kubejs、jade、patchouli；`implementation` 仅 architectury-api / artifacts / kubejs / owo-lib / cucumber / kaleidoscope-end / jade

## 2. 源码规模与包结构

`find . -name '*.java' | wc -l` = **145**，总行数 **9339**（`src/main/resources` 仅 `kaleidoscope_compat.mixins.json` + `accesstransformer.cfg`，`src/main/templates/META-INF/neoforge.mods.toml` 由 `generateModMetadata` 展开；**快照中不含 datapack JSON 资源，见 §5**）。第三层主要包（文件数）：

- `mixins/kaleidoscope_cookery` 10 + `.../accessor` 7 + `.../jei` 5 + `.../emi` 2 + `.../rei` 2；`mixins/farmersdelight` 6、`mixins/farm_and_charm` 3、`mixins/kaleidoscope_tavern` 3、`mixins/kaleidoscope_doll` 3、`mixins/create` 3、`mixins/youkaisfeasts` 3、`mixins/vinery|spectrum|solcarrot` 各 2
- `config/category` 10 + `config/category/{arm,contraption,ejector,spectrum}`；`compat/spectrum` 9、`compat/create/arm` 6、`compat/create/automation` 5、`compat/touhoulittlemaid` 5 + `.../task` 3
- `datamap/soup` 2、`datapack` 2、`event` 4、`init` 1 + `init/soupbase` 1、`network` 1、`util` 2、`client` 体系 4

最大文件：`compat/create/automation/WorkBlockItemAutomation.java` 645、`compat/touhoulittlemaid/MaidPressingTubBehavior.java` 380、`MaidChoppingBoardBehavior.java` 303、`compat/create/arm/CreateSteamerArm.java` 177、`mixins/kaleidoscope_cookery/RecipeItemTeapotMixin.java` 174、`compat/thirst/ThirstCompat.java` 166。

## 3. 入口与注册

主类 `src/main/java/com/bmt/kaleidoscope_compat/KaleidoscopeCompat.java:24`（`@Mod(MOD_ID)`，构造函数注入 `IEventBus`）：

```java
CONFIGURATOR = new Configurator(MOD_ID);      // ResourcefulConfig
CONFIGURATOR.register(MainConfig.class);
CreateCompat.init(modEventBus); SpectrumCompat.init(modEventBus);
FarmAndCharmCompat.init(); LittleMaidCompat.init(); KaleidoscopeDollCompat.init(modEventBus);
modEventBus.addListener(this::registerCapabilities);
NeoForge.EVENT_BUS.addListener(this::onAddReloadListener);
if (ModList.get().isLoaded("kaleidoscope_tavern")) NeoForge.EVENT_BUS.addListener(this::onRegisterCommands);
```

几乎没有自己的注册表（无 DeferredRegister 集中地），唯一注册是能力：`registerCapabilities`（`:51`）`event.registerBlockEntity(Capabilities.ItemHandler.BLOCK, ModBlocks.POT_BE.get(), (pot, side) -> new PotItemHandler(pot))`——直接用主 mod 的 BlockEntityType 挂标准物品能力。

## 4. 核心系统

**① 兼容模块分发 + 双层门控**：`compat/*` 每个联动一个类，`init(...)` 内部**先判 mod 是否加载再判配置**：`CreateCompat.java:15` `ModList.get().getModContainerById("create").ifPresent(ct -> { ...; if (!CreateCategory.createCompatEnabled) return; if (ArmConfig.potEnabled) CreatePotArm.init(modEventBus); ... })`。同理 `LittleMaidCompat.java:18`（`littleMaidCompatEnabled`）+ `IS_KALEIDOSCOPE_TAVERN_LOADED` 决定是否注册第三个 maid 任务。

**② Mixin 插件门控**（`mixins/MainMixinPlugin.java:11`）：`implements IMixinConfigPlugin`，`shouldApplyMixin` 按类名子串判断——含 `.create.` 要求 `isModLoaded("create")`；含 `GoggleMixin` 额外用 `Class.forName("com.simibubi.create.api.equipment.goggles.IHaveGoggleInformation", false, loader)` 探测**类是否真的存在**（Create 6 与 5 的 API 差异），不然整个混入在旧版 Create 上会崩。

**③ 外部扩展点接入（多 mod 联动范式）**：`touhoulittlemaid` 用官方注解 `@LittleMaidExtension` + `ILittleMaid.addMaidTask(TaskManager)` 注册 3 个 AI 任务（`TaskChoppingBoard/TaskMillstone/TaskPressingTub`，行为类 300+ 行）；`init/KCSoupBases.java:12` `SoupBaseManager.registerSoupBase(new MilkBucketSoupBase())`；`compat/spectrum/*` 8 个 `ItemHandler` 给 Spectrum 机器接物品槽；`solcarrot/FoodListFilter`、`appleskin/AppleSkinCompat` 均为"接管对方数据源"式联动。

**④ Create 机械臂/自动化**：`compat/create/arm/`（Pot/Stockpot/Steamer/Millstone/ShawarmaSpit/Teapot 六个 Arm + `ArmRecipeAttachments` 注册 attachment 类型），`compat/create/automation/`（`WorkBlockItemAutomation` 645 行做"工作方块物品"右键自动化，`DeployerAutomation`/`RecipeItemAutomation` 用 `EventPriority.HIGHEST` 抢右键事件）。

**⑤ 数据驱动**：`datamap/soup/StockpotVisualOverrideManager.java:16` `extends SimpleJsonResourceReloadListener("soup")`，`apply()` 内用 Codec 解析 JSON 数组/对象到静态 `Map<ResourceLocation, StockpotVisualOverride>`（按配方 id 覆盖汤锅视觉），在主类 `onAddReloadListener` 注册。

**⑥ 自定义网络**（`network/RequestPlayerDollPayload.java:19`）：`record implements CustomPacketPayload` + 静态 `TYPE` + `StreamCodec<RegistryFriendlyByteBuf,...>`，`handle` 里 `context.enqueueWork`；安全要点齐全——`playerId.matches("^[a-zA-Z][a-zA-Z0-9_]{2,15}$")` 校验、`containerMenu instanceof ComputerMenu` 复核、通过 `ComputerMenuAccessor`（mixin accessor）读写私有 `ItemStackHandler input/output`、`PlayerSkinFetcher.fetchPlayerUuid(...).thenAccept(...)` 异步结果再 `player.server.execute(...)` 回主线程。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：NeoForge 新式 `CustomPacketPayload`（仅 1 个包，无集中注册器；`NeoForge`/`modEventBus` 上没见到 `RegisterPayloadHandlersEvent`，注册路径未确认）。
- 数据包：`datapack/DatapackLoader.java:19` 在 `AddPackFindersEvent(SERVER_DATA)` 里按 `MainConfig.datapackMode`（`DatapackMode.NONE/COMPAT/UNITE`）与各联动配置动态挂载内置包：`packs/always`、`packs/compat|unite`、`packs/soup`、`packs/disable_*`（关闭 FD 煮锅/切菜板、Farm&Charm 锅、Vinery 发酵桶、YoukaisFeasts 蒸笼配方）、`packs/unite_*`（按 mod 加载）。**这些 JSON 不在本快照内（`src/main/resources` 只有 mixins.json 与 AT），包内容未确认**。
- 配置：ResourcefulConfig（`config/MainConfig.java:15` `@Config(value="kaleidoscope_compat", categories={10 个 Category})` + `@ConfigInfo` + `@ConfigEntry`/`@Comment`），静态字段直接读（如 `MainConfig.isItemBlacklisted(Item)` 解析逗号分隔黑名单），并有 `jarJar` 内嵌 resourcefulconfig 供运行时。
- datagen：**无**（无 `GatherDataEvent`/`addDataGenerator`，数据靠内置数据包与运行时注册）。

## 6. Mixin

配置 `src/main/resources/kaleidoscope_compat.mixins.json`：`plugin: MainMixinPlugin`、`package com.bmt.kaleidoscope_compat.mixins`、`compatibilityLevel JAVA_21`、`mixinextras.minVersion 0.5.0`，共 **59 项（client 5 + common 54）**，按目标 mod 分子包（kaleidoscope_cookery 26 含 accessor、farmersdelight 6、create 3、kaleidoscope_tavern 3、kaleidoscope_doll 3、youkaisfeasts 3…）。代表：
- `mixins/kaleidoscope_cookery/RecipeItemTeapotMixin.java:27` `@Mixin(RecipeItem.class)`，`@Inject(method="useOn", at=@At("RETURN"), cancellable=true)` 在原逻辑返回 PASS 时接管，另注入 `getName` 改物品名；`@Unique` 成员统一加前缀 `kaleidoscope_Compat_1_21_1_NeoForge$` 防冲突。
- `mixins/kaleidoscope_cookery/accessor/*`（7 个）访问主 mod 私有字段：`PotBlockEntityAccessor`、`StockpotBlockEntityAccessor`、`TeapotBlockEntityAccessor`、`MillstoneBlockEntityAccessor`、`FoodBiteBlockAccessor`、`BlockEntityAccessor`、`MobEffectInstanceAccessor`；`kaleidoscope_doll/ComputerMenuAccessor` 被网络包直接强转使用。
- `mixins/minecraft/TagLoaderMixin.java`、`mixins/solcarrot/FoodListMixin`、`mixins/quark/SimpleHarvestEventMixin` 属于"改第三方数据/事件"。

## 7. 值得学的 5 条具体做法

1. **兼容层只写 compat/mixins/config 三层**：`compat/<目标 mod>/` 放正规扩展点接入、`mixins/<目标 mod>/` 放不得不改的、`config/category/<目标 mod>Category` 放开关；三者同名前缀使"支持了谁"一眼可查（`KaleidoscopeCompat.java:39-43`、`mixins` 子包）。
2. **`IMixinConfigPlugin` 按 mod/类存在性裁剪 mixin**：`mixins/MainMixinPlugin.java:35` 用 `LoadingModList.get().getModFileById(modId)` 与 `Class.forName(..., false, loader)` 双条件，一套 jar 兼容多个主 mod 版本，避免 NoClassDefFoundError。
3. **官方 API 优先、mixin 兜底**：maid 用 `@LittleMaidExtension`、汤底用 `SoupBaseManager.registerSoupBase`、管道效果用 `OpenPipeEffectHandler`（对比 FruitsDelight），只有 `RecipeItem.useOn` 这类没有扩展点的才注入。
4. **数据包当"可选内容开关"**：用 `AddPackFindersEvent` + `Pack.Position.TOP` 动态挂 `disable_*` 包实现"关掉别的 mod 的某类配方"，而不是逐个 mixin 修改配方加载器（`datapack/DatapackLoader.java:44-58`）。
5. **服务端包安全三件套**：输入用正则白名单、菜单类型 instanceof 复核、异步结果回主线程执行（`network/RequestPlayerDollPayload.java:45-80`），并用 accessor mixin 访问对方私有容器而非反射——多 mod 联动的服务端自定义包可以照抄。
