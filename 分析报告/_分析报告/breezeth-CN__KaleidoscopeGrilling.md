# breezeth-CN/KaleidoscopeGrilling 源码分析

## 1. 基本信息
- Mod 名：森罗物语：烟火 / Kaleidoscope Grilling；mod_id `kaleidoscope_grilling`；作者 breezeth；版本 1.1.1
- 目标平台双套：NeoForge 1.21.1（`neoforge-1.21.1/gradle.properties`：neo_version=21.1.228、Java 21、moddev 2.0.134）+ Forge 1.20.1（Java 17），两套源码目录 `forge-1.20.1/` 与 `neoforge-1.21.1/`
- 许可证 `BSD-3-Clause + CC BY-NC-SA 4.0`（`neoforge-1.21.1/src/main/resources/META-INF/neoforge.mods.toml:3`）
- 依赖：必需 `kaleidoscope_cookery`（森罗物语：厨房）`[1.4.1,)`；可选 create `[6.0.0,)`、kubejs、touhou_little_maid、order-to-cook；compileOnly JEI 19.27、Jade 15.10.5、Ponder/Flywheel/Registrate（Create 附属标准姿势，不传递依赖，见 `neoforge-1.21.1/build.gradle:75-98`）

## 2. 源码规模与包结构
- 484 个 .java：neoforge 243 文件 / 25274 行，forge 241 文件 / 24680 行，两 loader 包结构几乎镜像；仓库内非 Java 资源仅 3 个（mixins.json、kubejs.plugins.txt、mods.toml），assets/data JSON 未入库
- 包（neoforge）：mixin 40、skewer 32、oil 23、seasoning 19、food 17、world 14、compat/touhoulittlemaid 14、rack 13、jei 12、registry 11、根包 10、compat/jade 8、client 6、grill 5、kubejs 4、compat/create 4、effect 3；network/item/event/data/bootstrap/compat/ordertocook 各 1
- 最大文件：`compat/touhoulittlemaid/MaidGrillingBehavior.java` 1395 行、`registry/ModItems.java` 655、`skewer/SkewerGuiIconCache.java` 605、`rack/AdvancedRackBlockEntity.java` 466、`grill/GrillBlockEntity.java` 455、`skewer/SkeweringHandler.java` 454

## 3. 入口与注册
主类 `neoforge-1.21.1/src/main/java/cn/breezeth/kaleidoscope_grilling/KaleidoscopeGrilling.java:52-120`：构造器注入 `IEventBus, ModContainer`，注册 11 个 `DeferredRegister` + COMMON 配置 + `GrillingNetwork::register`，并用 `ModList.get().isLoaded("touhou_little_maid")` 守卫联动初始化；随后集中挂 ≈40 个 `NeoForge.EVENT_BUS.addListener`（部分带 `EventPriority.HIGHEST, true` 可取消标记）。
注册框架为纯 NeoForge：`DeferredRegister.create(BuiltInRegistries.ITEM, MOD_ID)`（`registry/ModItems.java:37`）+ `DeferredHolder` 静态常量 + 分类 List（FIXED_SKEWERS / RAW_SKEWERS / INGREDIENTS）便于批量处理。
`gradle/package-structure.gradle:1-40` 提供 `verifyPackageStructure` 任务：白名单校验根包只许放 10 个 API 类，实现类必须进领域包（grill/skewer/oil/…）。

## 4. 核心系统
1. 烤串数据系统 `data/GrillingDataManager.java` + `skewer/SkeweringHandler.java`：`Skewer` record（ingredients 为最多 3 槽的 `List<List<String>>`、cookedResult、effect/effectSeconds、rawModel/cookedModel/eatingAnimation）；物品侧用 NBT 常量键 `SkewerIngredients`/`SkewerModelVariants`（SkeweringHandler.java:31-37）存槽位与模型变体；数据源优先级 内置资源 → datapack → KubeJS 脚本。
2. 自动化 API `GrillAutomationApi.java`：`record Result(Status, int affected, ItemStack output, ItemStack heldReplacement)`、`record Snapshot`，所有动作带 `boolean simulate`；设备端用租约防争抢（`grill/GrillBlockEntity.java:266-309` tryAcquireAutomation / heartbeatAutomation / releaseAutomation / forceReleaseAutomation，DEFAULT_LEASE_TIMEOUT_TICKS=200）。
3. 烤架状态机 `grill/GrillBlockEntity.java:37-260`：SLOT_COUNT=3、FINISHED_TICKS=800、BURNT_TICKS=400，流程 点火→放串→brushOil→flip→season→extract，`flipAnimationData` 驱动客户端动画。
4. 油料/调料 `oil/`（23 文件）、`seasoning/`（19 文件）：`oil/BigVatCapabilities.java`、`oil/OilPressCapabilities.java` 注册 NeoForge capability；`seasoning/SeasoningData.java` 写入数据组件，`AdvancedSeasoningHandler` 处理附加效果。

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络 `network/GrillingNetwork.java`：`RegisterPayloadHandlersEvent.registrar("2")` + 两个 `playToClient` payload；StreamCodec 手写 decode 并做上界校验（MAX_RECIPES=4096、MAX_SELECTORS_PER_SLOT=256、slotCount≤3，行 113-142），登录时发 ThreadingRecipeSyncPayload，脚本 commit 后广播。
- 数据驱动：`GrillingDataManager` extends `SimpleJsonResourceReloadListener`（目录 `grilling`），内置 `/data/kaleidoscope_grilling/grilling/skewers.json` 与 datapack JSON 合并（行 308-316）；KubeJS 接入见 `kubejs/GrillingKubeJSPlugin.java`（registerBuilderTypes/registerBindings/afterScriptsLoaded）+ `kubejs.plugins.txt`。
- 配置 `food/HotFoodConfig.java` 以 COMMON 类型注册；datagen：未发现（仓库无 src/generated）。

## 6. Mixin
配置 `neoforge-1.21.1/src/main/resources/kaleidoscope_grilling.mixins.json`：package `cn.breezeth.kaleidoscope_grilling.mixin`，plugin `GrillingMixinPlugin`，主段 23 个 + client 段 17 个。
`mixin/GrillingMixinPlugin.java:10-39` 用 `classExists()`（classloader 查 .class 资源）静态探测 Create / 女仆 / JEI / order-to-cook / Punchy，按类名后缀决定 `shouldApplyMixin`。
代表 hook：`PotBlockEntityMixin`、`StockpotBlockEntityMixin`（厨房锅具加调料）、`FoodDataAccessor`（@Accessor）、`ItemEntityHotFoodExpiryMixin`、`AbstractContainerMenuHotMergeMixin`。

## 7. 值得学的 5 条
1. 根包只放 API 并用 Gradle 白名单任务强制分层（`gradle/package-structure.gradle`）→ 想长期对外提供 API 的模组。
2. IMixinConfigPlugin 按类存在性门禁 mixin（`mixin/GrillingMixinPlugin.java:10-17`）→ 同时兼容多个可选前置，避免 NoClassDefFoundError。
3. 自动化接口统一 `simulate` + Result/Snapshot + 带超时租约（`GrillAutomationApi.java`、`grill/GrillBlockEntity.java:266-309`）→ 给 Create/其它自动化 mod 暴露安全操作入口。
4. reload listener 与 KubeJS 注册写入同一 PENDING map，`commitScriptThreadingRecipes()` 后统一广播（`data/GrillingDataManager.java:238-243`）→ datapack 与脚本配方共存。
5. 手写 StreamCodec 时对集合长度做上界校验并抛 IllegalArgumentException（`network/GrillingNetwork.java:113-142`）→ 同步脚本/配方数据的网络包防呆。

## 8. 公开 API（扩展型模组，有 API 面）
根包导出 10 个类可直接被其它 mod 调用：GrillAutomationApi、SeasoningAutomationApi、OilPressApi、OilPressContainerApi、AdvancedRackAutomationApi、AdvancedRackCompatApi、SkewerCompatApi、HotFoodApi（`HotFoodApi.java:19-44` registerHeatDuration / makeHot / isHot / season）、TypedOilPotAccess、主类 KaleidoscopeGrilling。扩展点接口：`seasoning/SeasonedPotAccess`、`oil/PotOilAccess`、`oil/PotHudAccess`、`oil/AnvilPressAnimationAccess`、`skewer/SkewerItemRenderContext`。
