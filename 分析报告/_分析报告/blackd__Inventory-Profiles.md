# Inventory Profiles Next 源码分析报告

## 1. 基本信息
- Mod 名 Inventory Profiles Next（IPN）/ mod_id `inventoryprofilesnext` / 作者 blackd（Plamen K. Kosseff，代码中含 jsnimda 早期版权）/ 许可证 AGPL-3（`gradle.properties:ipnext.license=AGPL-3`；`org/anti_ad/mc/ipn/api/**` 为 MIT）
- 目标：MC 1.21 / 1.21.3 / 1.21.4 / 1.21.5 / 1.21.6，加载器 Fabric、Forge、NeoForge（`platforms/` 下 10 个平台工程，`settings.gradle.kts` 收录其中 10 个），服务端无关（`fabric.mod.json:"environment":"client"`、mods.toml `side="CLIENT"`）
- 版本 2.1.9（`build.gradle.kts` 内 `Version("2","1","9")`）；Kotlin 2.0.21 + JVM 21；插件 fabric-loom 1.10-SNAPSHOT、shadow 8+、ProGuard 7+、cursegradle/minotaur、Nexus 发布
- 编译依赖（关键）：**libIPN ≥6.5.0 <6.6**（`gradle.properties` 相邻 ext，仓库 `https://maven.ipn-mod.org/releases`）+ `fabric-language-kotlin`（Fabric）、`kotlinforforge`（Forge/NeoForge 的 `modLoader="kotlinforforge"`）。`org.anti_ad.mc.common.*`（配置 DSL、GUI widget、Vanilla 门面）与 `org.anti_ad.mc.alias.*`（映射别名层）均来自 libIPN，本仓库无其源码
- 注：本次工作副本为 sparse checkout，JSON 资源（`fabric.mod.json`、`mixins.ipnext.json`、hints JSON）与 git symlink 未落地，相关结论取自 `git cat-file`

## 2. 源码规模与包结构
实测 256 个 `.java` + 363 个 `.kt`；核心共享源集 `platforms/shared-1.20.5+/src` 共 110 个 java/kt、约 18.8k 行；每个平台工程 36-44 个源文件（如 `platforms/fabric-1.21/src/main/java/org/anti_ad/mc/ipnext/`）。
包（到第 3 层）：`ipnext/gui/inject` 14、`ipnext/item/rule` 13、`ipnext/inventory/{sandbox 7,data 6,action 3}`、`ipnext/event/{villagers 4}`、`ipn/api/access`、`ipnext/{config,parser,integration,profiles/config,input,debug}`。
最大文件：`event/autorefill/AutoRefillHandler.kt` 930、`ipn/features/scrolling/ScrollingUtils.kt` 712、`event/villagers/VillagerTradeManager.kt` 646、`gui/inject/SortingButtonCollectionWidget.kt` 517、`config/Configs.kt` 511、各平台 `item/ItemTypeExtensions.kt`≈490-508（版本差异文件）。

## 3. 入口与注册
`fabric.mod.json`（`platforms/modloaders/fabric/resources/`）entrypoints：`client → org.anti_ad.mc.ipnext.InventoryProfilesKt::init`、`modmenu → ...compat.ModMenuApiImpl`，并声明 `accessWidener: ipnext.accesswidener`、`mixins.ipnext.json`。`InventoryProfiles.kt:32-70` 的 `init()`：`IPNImpl.init()` → `specificInit()`（各平台 `VersionSpecificInit.kt` 为空实现）→ `ClientInitHandler.register { Integrations.init(); initInfoManager(); InputHandler.onClientInit(); InsertWidgetHandler.onClientInit(); ConfigScreenSettings.initMainConfig(); 首次运行写默认配置 }`。
无内容注册（客户端 mod），无自研注册框架；Forge/NeoForge 由 kotlinforforge 载入（未在本副本确认其 @Mod 入口类）。

## 4. 核心系统
1. **点击执行层**：`inventory/ContainerClicker.kt`（leftClick/rightClick/shiftClick(QUICK_MOVE)/qClick(THROW)/swapClick，热键栏用 swap、盔甲与副手用光标往返）；`GeneralInventoryActions.kt`；容器分类 `inventory/ContainerTypes.kt`（SORTABLE_STORAGE/CREATIVE/CRAFTING/PURE_BACKPACK，`versionSpecificContainerTypes` 由各版本平台提供）+ `AreaTypes.kt`。
2. **沙盒规划引擎**：`inventory/sandbox/ContainerSandbox.kt` + `ItemPlanner.kt` + `diffcalculator/`（`DiffCalculator.apply` 在沙盒内试算"现状→目标"点击序列，三种实现 Simple/ScoreBasedSingle/ScoreBasedDual，`MAX_CLICK_BOUND=100_000`，不变式校验 `Unequal sandbox and goal item counts`）；`inventory/data/{ItemTracker,SubTracker,ItemStat}` 跟踪物品与已抛出物。
3. **物品规则 DSL**：`item/rule/**`（Rule/SubRuleDefinition/NativeRule/ItemTypeMatcher）+ `parser/RuleParser.kt`（ANTLR，生成类 `org.anti_ad.mc.common.gen.RulesLexer/RulesParser`）+ 数据文件 `resources/assets/inventoryprofilesnext/config/rules.txt`（`@子规则`、`::参数(如 number_order=descending)`、`#tag`、NBT）。
4. **GUI 注入**：`gui/inject/InsertWidgetHandler.kt`（以 `ScreenEventListener` 随 Screen 生命周期管理 widget 列表）+ `SortingButtonCollectionWidget/ProfilesUICollectionWidget/SettingsWidget`；`MixinScreen` 在 `init/removed/close` 的 RETURN 处同步状态。
5. **锁槽位与自动补货**：`event/LockSlotsHandler.kt` + `event/LockedSlotKeeper.kt`（空槽/热键栏保护，规则文件 `LockSlotsLoader`，配 `MixinPlayerInteractionManagerForLockedSlotsMovePrevention` 阻断对被锁槽位的移动）+ `event/autorefill/AutoRefillHandler.kt`（工具/食物/消耗品补货，含 NBT 匹配与阈值单位 ABSOLUTE/PERCENTAGE）；`event/villagers/VillagerTradeManager.kt` 管理村民交易书签。
6. **配置系统**：复用 libIPN 的声明式 DSL——`object ModSettings : ConfigDeclaration` + `createBuilder().CATEGORY(...)` 与委托属性 `by bool()/int()/enum()/hotkey()/keyToggleBool()`（`config/Configs.kt:53` 起），分 `ModSettings/Debugs/LockedSlotsSettings/ScrollSettings/AutoRefillSettings/Hotkeys`，支持 per-server 配置（`PROFILES_PER_SERVER`、`ENABLE_LOCK_SLOTS_PER_SERVER`）与 profiles 脚本（`profiles.config.ProfilesConfigParser`，另一套 ANTLR 语法）。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：**无自定义数据包注册**（纯客户端 mod，未见 payload 声明）。
- 数据驱动：`assets/inventoryprofilesnext/config/` 下 `rules.txt`、`configs/itemgroups.{default,vanilla}.txt`、`configs/profiles.{default,next}.txt`、`ModIntegrationHintsNG.json` / `SlotIntegrationHints.json` / `exampleIntegrationHints.json`（结构为 `modid → 类全名 → {playerSideOnly|ignore|...}`，由 `integration/HintsManagerNG.kt` 读取并与外部 overrides 合并）。
- 配置：见 4.6，另有 `ModIntegrationOverride.json`、`ModIntegrationExport.json` 用户可导出导入。

## 6. Mixin
配置文件 `platforms/<loader>-<ver>/src/main/resources/mixins.ipnext.json`（package `org.anti_ad.mc.ipnext.mixin`，JAVA_21，仅 client 段，`plugin: org.anti_ad.mc.ipnext.mixinhelpers.IPNOptiFabricMixinPlugin`），另有 access widener `ipnext.accesswidener`（开放 `MerchantScreen$WidgetButtonPage`、`AnvilScreen.nameField`、`ForgingScreenHandler.input/inputSlots/resultSlotIndex`、`PotionContentsComponent.customEffects` 等）。
代表 mixin：`MixinContainerScreen`→`HandledScreen`（render 中 MatrixStack.translate / renderTooltip 处注入）、`MixinMinecraftClient`（`tick` HEAD/RETURN、`joinWorld` RETURN、`doItemPick` HEAD/TAIL）、`MixinClientPlayerInteractionManager`（`clickSlot` HEAD cancellable + TAIL）、`MixinPlayerInventory`（`getEmptySlot`/`addStack`/`addPickBlock`）、`MixinGameRenderer`（`priority=10000`，包住 `Screen.renderWithTooltip`）、`MixinGameRendererOptifabric` 与 `MixinVirtualMouseHandler`（Controlify，`remap=false`）、`MixinSuperMartiJnWidgetScreen`、`MixinPlayerInteractEntityC2SPacket.interactAt`、`MixinCraftingResultSlot.onCrafted`、`MixinGuiCloseC2SPacket.<init>`。

## 7. 值得学的 5 条
1. **用 git symlink 复用共享源码**：每个平台工程 `src/shared → ../../shared-1.20.5+/src/main`、`src/modloader → modloaders/<loader>`、`src/main/antlr → ../shared/antlr`、`src/integrations/optifabric`（`git ls-tree` 中 mode 120000），10 个子工程共享一套源码，版本差异只落在一个 `ItemTypeExtensions.kt` 类文件上，比多 sourceSet 更好 debug。
2. **映射别名层 + 版本访问器**：共享代码 import `org.anti_ad.mc.alias.*`（`Container`=AbstractContainerMenu、`Identifier`=ResourceLocation）与 `ipnext.ingame.\`(slots)\`/\`(clickSlot)\`` 这类反引号扩展函数（各平台 `ingame/Inventory.kt`、`VanillaAccessors.kt` 实现），把版本/映射差异压到薄薄一层。
3. **沙盒试算再落地**：所有整理/移动先在 `ContainerSandbox` 内算出点击序列并断言结果一致（`DiffCalculator.apply` 后 `error("ContainerSandbox actual result not same as goal")`），再真实发包点击，避免把容器点乱——GUI 自动化通用做法。
4. **行为数据化 + 热重载**：排序规则、物品分组、profiles、第三方 GUI 提示全部外置为 txt/json 资源，配 GUI 上的"打开配置文件夹/重载规则文件"按钮（`ModSettings.OPEN_CONFIG_FOLDER/RELOAD_RULE_FILES`）。
5. **产物压缩发布**：shadowJar `relocate` ANTLR 等依赖并 `minimize()`，再经 ProGuard（`proguard.txt`，`-optimizationpasses 15`）混淆优化，`registerMinimizeJarTask` 统一各平台产物。

## 8. 公开 API（供其他 mod 接入）
- 注解式 GUI 提示：`org.anti_ad.mc.ipn.api` → `@IPNGuiHint(button=IPNButton.…)`、`@IPNGuiHints`、`@IPNIgnore`、`@IPNPlayerSideOnly`、`@IPNSlotsIgnoreForInventoryTypes`（`IPNGuiHint.java` 提供 top/bottom/horizontalOffset 等偏移参数）；也可不改代码，直接往 `assets/inventoryprofilesnext/config/ModIntegrationHintsNG.json` 或用户 override 文件里加"类名 → 属性"映射。
- 运行时门面：`org.anti_ad.mc.ipn.api.access.IPN`（单例 `IPN.instance`，暴露 `containerClicker`、`lockedSlots`）与 `IContainerClicker`；`integration/IPNtoModIntegration.init()` 为 mod 侧集成入口（由 `compat/integrations/Integrations.kt` 加载，已内置 Carpet 集成 `CarpetIntegration.kt`）。
- 接入方式：Gradle `compileOnly` 依赖 `org.anti-ad.mc:InventoryProfilesNext-fabric-1.21:2.0.1`（或 forge/neoforge），仓库 `https://maven.ipn-mod.org/releases`；运行期强依赖 `libipn`（`fabric.mod.json` depends / mods.toml dependency）。注意：仓库 README 声明开发已迁移至 Codeberg 并归档（最后提交 2025-06-17）。
