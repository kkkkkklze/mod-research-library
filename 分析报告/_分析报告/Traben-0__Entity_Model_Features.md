# Entity Model Features (EMF) 源码分析报告

## 1. 基本信息

| 项 | 值 |
|---|---|
| Mod 名 / mod_id | Entity Model Features / `entity_model_features` |
| 作者 | Traben（`neoforge.mods.toml:11`） |
| 版本 / 许可证 | `mod_version=3.3.5`（`gradle.properties`）/ LGPL-3.0（`src/main/resources/META-INF/neoforge.mods.toml:4`） |
| 侧 | 纯客户端，`side = "CLIENT"`（`neoforge.mods.toml:23`） |
| MC 版本 | 1.20.1 → 26.2，共 19 个子项目：`1.20.1-forge`、`1.21(-neoforge)`、`1.21.3/4/5/6/9/11-x`、`26.1-x`、`26.2-x`（`settings.gradle.kts` 末尾的 `.version(12111)...` 链，含 fabric/forge/neoforge） |
| 构建 | Kotlin DSL + **Essential 多版本插件** `gg.essential.multi-version` 0.7.2 + `gg.essential.defaults`（Architectury Loom 封装） |
| 关键依赖 | `maven.modrinth:entitytexturefeatures`（**硬依赖 ETF ≥ 7.2.0**，`neoforge.mods.toml:33-37`）、`traben.tconfig` 配置库、MixinExtras 0.4.1（Forge 内置打包，NeoForge <1.20.2 打包）、`org.ow2.asm:asm:9.7`（`build.gradle.kts:183-193`） |

编译器特性：**单份源码 + 预处理器注释**，`//#if FABRIC / FORGE / MC >= 12109`，被注释掉的版本用 `//$$` 前缀（见 `EMFInit.java`：同文件里同时存在 Fabric/Forge/NeoForge 三种入口）。`versions/<版本>/` 下只有 `gradle.properties`，没有重复源码。

## 2. 规模与包结构

`src/main/java` 共 **157 个 .java、21009 行**（`find src -name '*.java' -exec wc -l {} +`）。根包 `traben/entity_model_features`。

| 包（第 3 层） | 文件数 |
|---|---|
| `mixin/mixins`（总 64 个 mixin 类） | 15；`rendering` 10、`rendering/attachments` 8、`rendering/model` 8、`rendering/feature` 6、`arrows` 4、`submits` 4、`accessor` 4、`exporting` 3、`optional` 1 |
| `models` | 5（EMFModelMappings、EMFModel_ID、IEMFModel…） |
| `models/animation` | 4 + `math` 2 + `math/asm` 5 + `math/expression_tree` 9 + `math/methods`（emf 6 / optifine 7 / simple 4）+ `math/variables` 2 + `factories` 5 + `state` 6 |
| `models/parts` | 5（EMFModelPart / EMFModelPartVanilla / EMFModelPartRoot / EMFModelPartCustom / EMFModelPartWithState） |
| `models/jem_objects` | 3（EMFJemData / EMFPartData / EMFBoxData） |
| `utils` | 12；`propeties`（原文拼写）6；`mod_compat` 3；`config` 2 |

最大文件：`models/EMFModelMappings.java` 1924 行、`EMFManager.java` 930、`models/animation/math/EMFMath.java` 833、`models/parts/EMFModelPart.java` 664、`config/EMFConfig.java` 651、`EMFAnimationApi.java` 593（API 全靠静态接口方法）。

## 3. 入口与注册

入口 `EMFInit.java`（每 loader 一段，预处理切换）：Fabric 走 `ClientModInitializer.onInitializeClient → EMF.init()`；Forge `@Mod` 构造器里注册 `ConfigScreenHandler.ConfigScreenFactory`；NeoForge 1.21+ 用 `IConfigScreenFactory`。共同点是只注册"配置屏 + 初始化"，无任何 DeferredRegister（无方块/物品）。

`EMF.init()`（`EMF.java:51-152`）承担全部注册：

```java
configHandler = new TConfigHandler<>(EMFConfig::new, MOD_ID, "EMF");
ETF.registerConfigHandler(configHandler);                       // 配置交给 ETF 统一管理
ETFEntityRenderState.setEtfRenderStateConstructor("for EMF",
        etf -> new EMFEntityRenderStateViaReference((EMFEntity) etf));  // 复用 ETF 的渲染状态
EMFManager.getInstance();
ETFApi.registerCustomRandomPropertyFactory(MOD_ID,              // 6 个自定义 .properties 属性
        RandomProperties.RandomPropertyFactory.of("modelRule", ...),
        RandomProperties.RandomPropertyFactory.of("modelSuffix", ...), /* var/varb/global_var/global_varb */);
ETFApi.registerCustomRandomPropertyFactory(...);
```
另外注册 ETF 配置警告、`ETFSubmitData.DATA_IN/DATA_OUT`（1.21.9+ 渲染提交阶段数据传递）、PAL/player_animation_library 暂停钩子。`EMF.testForForgeLoadingError()`（`EMF.java:165-194`）专门规避"Forge 检测到缺失依赖 → 不加载 access widener → EMF mixin 崩"的坑，捕获 `IncompatibleClassChangeError` 后自我禁用。

## 4. 核心系统

**(a) 模型查找与目录兼容**（`utils/EMFDirectoryHandler.java`）：枚举 `EMFDirectory{EMF, EMF_SUB, OPTIFINE, OPTIFINE_SUB}`，分别映射 `assets/<ns>/emf/cem/<name>` 与 OptiFine 的 `assets/<ns>/optifine/cem/<name>`，`fallback()/override()` 让两套目录互为备份（`EMFDirectoryHandler.java:186-222`）；带 `isSubFolder` 变体模式与"取第几个资源包"的 `packIndex()`，保证资源包优先级与 OptiFine 一致。模型 ID 是 `EMFModel_ID`（`namespace:fileName` + **fallback 链** `addFallbackModel`，`EMFModel_ID.java:135`），路径拼装见 `EMFModel_ID.java:270-273`。

**(b) 解析：.jem/.jpm JSON → POJO**：`EMFJemData`（`texture/textureSize/shadow_size/models`，`prepare()` 做路径与纹理校验）、`EMFPartData`（`baseId/model/id/part/attach/submodels/submodel/invertAxis/translate/rotate/mirrorTexture/animations`）、`EMFBoxData`（`textureOffset` + 逐面 UV `uvDown/uvUp/uvFront/...` + `sizeAddX/Y/Z`），完全对齐 OptiFine CEM 语法并扩展。

**(c) 烘焙**：核心技巧是**直接继承原版 `ModelPart`**——`EMFModelPart extends ModelPart`（`models/parts/EMFModelPart.java:51`），`EMFModelPartRoot extends EMFModelPartVanilla`，配合 access widener 把 `ModelPart` 变 `extendable`、`cubes/children` 变 `mutable`、`compile` 变 `accessible`（`src/main/resources/entity_model_features_15.accesswidener:3-20`），从而无需自建一套平行模型体系。注入点在 `Mixins/MixinEntityModelLoader`：`bakeLayer` 的 `@At("RETURN")` 返回 EMF 根（`mixin/mixins/MixinEntityModelLoader.java:17`）。

**(d) 动画数学引擎**（`models/animation/math`）：`.jem` 的动画行先解析成表达式树（`expression_tree/MathExpressionParser` 433 行、`MathOperator`/`MathMethod` 注册表），再**用 ASM 编译成字节码**：`ASMParser.compileOrNull()`（`asm/ASMParser.java:28`）为整个模型的动画集生成一个类 `traben.asm_generated.EMF_ASM_Parsed_N`，方法签名 `eval([F[Z)V`，变量落在 `float[]/boolean[]` 数组索引上（`asm/ASMVariableHandler`），生成失败回退解释执行。`asm/ASMHelper.java` 提供可直接被生成的字节码调用的静态数学函数（sin/cos/torad/log_ASM…）。方法分三套：`methods/optifine`（`if/in/max/min/print/random`，兼容 OptiFine）、`methods/emf`（扩展 `nbt/keyframe/keyframeloop/catch/randomb/ifb`）、`methods/simple`（一元/二元/三元/多元注册）。

**(e) 变体（模型切换）**：`EMFModelPartRoot.discoverAndInitVariants/doVariantCheck/setVariantStateTo`（`models/parts/EMFModelPartRoot.java:147/245/332`），每个 `EMFModelPartVanilla` 持 `allKnownStateVariants`，实体 UUID 缓存上次变体（`ETFLruCache.UUIDInteger`，`EMFModelPartRoot.java:41`）。变体判定复用 ETF 的 `.properties` 规则与后缀：`variantTester = ETFApi.ETFVariantSuffixProvider`——**ETF 决定贴图后缀，EMF 用同一后缀切模型变体**，这就是两者的分工边界。

**(f) 原版模型导出**：`EMFModelMappings.exploreProvidedEntityModelAndExportIfNeeded` + `printModel`（`models/EMFModelMappings.java:1539/1636`）把运行时原版模型序列化成 `.jem` 写到 `emf/export/...`；`mixin/mixins/exporting/MixinEntityModelSet`（`priority = 1001`）抓未被修改的 layer 根做导出参照。

**(g) 兼容层**：`mod_compat/`（EBE 配置改写、Iris 阴影 pass 检测、PAL 暂停）、`utils/EMFAnimationPauseHandler`（识别 Emotecraft/KosmX 与 Essential 表情，暂停动画）、`utils/EMFLODHandler.isLODSkippingThisFrame`（远处跳过动画）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无**（纯客户端渲染 mod，不含任何包注册）。
- **数据驱动**：全部资源包驱动。模型 `assets/<ns>/{optifine,emf}/cem/<name>.jem`（含 `<name>/<name>.jem` 子文件夹变体形态），变体规则为 OptiFine 的 `.properties`（实际由 ETF 读取）；`EMFResourceCaching.resourceExists` 缓存资源存在性，`EMFManager.resetInstance()`（`EMFManager.java:129`）在资源重载时清空所有缓存（由 `mixin/mixins/MixinResourceReloadStart/End` 触发）。
- **配置**：`TConfigHandler<EMFConfig>`，JSON 持久化，UI 用 `TConfigEntryCategory/TConfigEntryBoolean` 构建（`config/EMFConfig.java:52-56`），配置屏幕由 `ETF.getConfigScreen` 代理；含大量 OptiFine 兼容开关（`enforceOptiFineSubFoldersVariantOnly`、`enforceOptiFineAnimSyntaxLimits`、`allowOptifineFallbackProperties`）。
- **datagen：无**。

## 6. Mixin

配置文件 `src/main/resources/entity_model_features.mixins.json`：`package = traben.entity_model_features.mixin.mixins`，`plugin = traben.entity_model_features.mixin.Plugin`，`compatibilityLevel = JAVA_17`，`injectors.defaultRequire = 1`，`client` 列表 64 个类（无 common）。

`mixin/Plugin.java`：`onLoad` 里 `MixinExtrasBootstrap.init()`；**`shouldApplyMixin` 对目标 `traben.entity_texture_features.mixin.CancelTarget` 返回 false**——即 ETF 通过改自己 mixin 目标类来自禁用时（"取消 mixin"惯用法），EMF 的 mixin 要跟着一起失效，保证两个 mod 同生共死。

代表性 hook：`rendering/MixinEntityRenderDispatcher`（`@Mixin(EntityRenderDispatcher.class)`，`@Inject` 到 `render` 的 `RETURN` 与 `INVOKE ...EntityRenderer;submit` 前后，`@ModifyExpressionValue` 改 `getShadowRadius/getShadowStrength` 与火焰尺寸），`rendering/attachments/*`（Dolphin/Enderman/Fox/Head/Panda/Villager/Witch 的手持与顶戴方块偏移），`rendering/model/*`（重入重设 pose、狼项圈、暖色变体模型），`exporting/MixinEntityModelSet`（`priority = 1001`，`vanilla()` RETURN 处留出未修改根）。大量使用 **MixinExtras**（`@ModifyExpressionValue`、`@Local`）；方法名/描述符字符串在源码里用 `//#if` 逐版本切换。

Access widener：`entity_model_features_3..15.accesswidener` 共 14 份，`build.gradle.kts:47-63` 按 MC 版本选取；NeoForge 26.1+ 因架构改动不再自动转换，脚本 `generateAt`（`build.gradle.kts:379-471`）把 AW 文本解析后写成 `META-INF/accesstransformer.cfg`。

## 7. 值得学的 5 条做法

1. **单份源码 + 预处理器多版本**：`//#if MC >= 12109` + `//$$` 注释行，`settings.gradle.kts` 用 `.version(12111)` 循环生成 19 个子项目，避免 N 份分支代码 —— 适用于任何要跨 1.20-1.21+ 的客户端 mod。
2. **继承原版 `ModelPart` 而非另起体系**：`EMFModelPart extends ModelPart` + AW 把 `ModelPart` 设 `extendable`、`cubes/children` 设 `mutable`（`entity_model_features_15.accesswidener`），于是所有渲染 mixin 都能无感接受 EMF 模型 —— 想替换原版渲染对象时的最低成本路径。
3. **动画表达式"先解释、再 ASM 编译"**：`ASMParser.compileOrNull` 生成 `eval([F[Z)V`，变量用数组下标而非 Map 查找，失败回退解释器（`asm/ASMParser.java:28`）—— 高频求值场景的性能优化模板。
4. **双目录 + fallback 链的格式兼容策略**：`emf/cem` 与 `optifine/cem` 互为 `fallback()/override()`，`EMFModel_ID` 支持多级 fallback 名称 —— 做"兼容某老牌格式"时的稳妥做法：先读兼容目录，再允许自有扩展目录覆盖。
5. **把原版模型导出成合法示例文件**：`EMFModelMappings.printModel` 生成 `.jem` 到 `emf/export/`，资源包作者以原版模型为起点改 —— 内置"自助工具"减少用户求助，适合任何自定义格式的库 mod。

## 8. 公开 API（EMFAnimationApi）

`EMFAnimationApi.java` 是**接口 + 静态方法**式的 API 门面，`getApiVersion()` 当前返回 `11`（`:56`），被弃用方法保留但只打印警告（保证向后兼容）。扩展点：

- 变量：`registerSingletonAnimationVariable(modId, name, 说明, BooleanSupplier/Supplier<Float>)`、`registerUniqueAnimationVariableFactory(modId, name, UniqueVariableFactory)`，实现于 `VariableRegistry`（`models/animation/math/variables/VariableRegistry.java:38`，含 `singletonASMVariablesBool/Float` 的 ASM 快路径）。
- 函数：`registerCustomFunctionFactory` / `registerCustomFunctionFromStaticMethod(..., ASMVisitable asmCompiler)`（可同时提供解释实现与字节码编译器）。
- 渲染期：`registerAnimationHook(EMFAnimationHook)`、`animateModelForEntity/animateModelForState`、`pauseAllCustomAnimationsForEntity`、`registerPauseCondition`、`registerVanillaModelCondition`、`lockEntityToVanillaModel`、`getCurrentEMFVariantOfModel`、`isModelAnimatedByEMF / isModelCustomizedByEMF / isModelPartCustomToEMF`。
- 查询：`getCurrentEntity()`（返回 `EMFEntity`，实体或方块实体的统一包装）。

对外接入方式：仅客户端、需先装 ETF；EMF 也反向把 6 个自定义随机属性注册进 ETF（`EMF.java:64-82`），是 mod 间双向扩展（互相注册扩展点）的范例。未确认处：`SampledFloat` 等旧类型在新版本中的具体包路径未逐一核对。
