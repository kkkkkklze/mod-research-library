# Traben-0/Entity_Texture_Features 源码分析报告

## 1. 基本信息
Entity Texture Features（ETF），mod_id `entity_texture_features`（`src/main/resources/META-INF/mods.toml`、`neoforge.mods.toml`），作者 Traben，LGPL-3.0，`side = "CLIENT"`（纯客户端，无方块/物品/网络注册）。版本 `mod_version=7.2.1`（`gradle.properties`）。多版本方案：Essential 工具链 `gg.essential.multi-version 0.7.2`（`settings.gradle.kts`），`versions/<mc>-<loader>/gradle.properties` 只覆盖依赖坐标（如 `versions/1.21.11-forge` → `net.minecraftforge:forge:1.21.11-61.0.2`、`versions/26.2-fabric` → `com.mojang:minecraft:26.2`），覆盖 1.20.1→26.2 的 forge/neoforge/fabric；源码级兼容用 ReplayMod 预处理器注释 `//#if MC >= 12103`、`//#elseif FABRIC`（被裁行保留为 `//$$`，如 `ETFInit.java` 一文件内含三平台入口）。编译依赖：Sodium/Embeddium、Iris/Oculus、ImmediatelyFast、3dSkinLayers、ModMenu（Modrinth maven + 按 MC 版本写死 file id，`build.gradle.kts` 的 `modImpl(...)` 表）、MixinExtras 0.4.1、`com.demonwav.mcdev:annotations`。

## 2. 规模与包结构
192 个 `.java` / 21,388 行（全在 `src/main/java`）。主要包：`features/property_reading/properties/{etf_properties(30), etf_properties/external(16), optifine_properties(13), generic_properties(7)}`；`mixin/mixins/{entity/misc(12), entity/renderer(7), entity/renderer/feature(5), vertexconsumers(5), submit(4), mods/{sodium,iris,iris/old}(各3), reloading(2)}`；`features/{state(6), texture_handlers(5), player(4)}`；自研配置框架 `traben.tconfig(3)` + `tconfig/gui/entries(11)`。最大文件：`features/player/ETFPlayerTexture.java`(1473)、`config/screens/skin/ETFConfigScreenSkinTool.java`(1002)、`features/texture_handlers/ETFTexture.java`(662)、`config/ETFConfig.java`(577)、`ETFApi.java`(569)、`utils/ETFUtils2.java`(519)、`MixinPaintingEntityRenderer.java`(467)、`features/ETFManager.java`(323)、`features/state/ETFState.java`(290)。

## 3. 入口与注册
无注册框架。`ETFInit.java`：Fabric 为 `ClientModInitializer`；Forge/NeoForge 为 `@Mod("entity_texture_features")` 构造函数内判断 `FMLEnvironment.dist.isClient()`、按 MC 版本注册配置屏扩展点（`ConfigScreenHandler.ConfigScreenFactory` / `IConfigScreenFactory`），再调 `ETF.start()`。`ETF.java:67-124`：建 `TConfigHandler<ETFConfig>` 主配置与 `etf_warnings.json`，一次探测 `skinlayers3d`/`iris|oculus`/`fabric-api`，注册配置警告（Figura/EBE/Quark/iris+3dSkinLayers/无 EMF），其中 Figura 警告带自动修复（关 `skinFeaturesEnabled` 并保存）。配置屏不用 Cloth Config，而是 `traben.tconfig.gui.entries` 自研控件。

## 4. 核心系统
1. **资源包规则引擎**：`features/property_reading/PropertiesRandomProvider.java:47-90` 读 `<贴图>.properties` 并构造 `RandomPropertyRule` 列表，末条非“恒真”时补哨兵 `DEFAULT_RETURN`（:68）；rule 号由键名解析（`rule.3.*`，:161-179），支持 `weights`、`seedOffset.N`、`seedSource.N`、后缀数组/区间，并校验 OptiFine 跳号兼容（:133-158）；仅当定义规则的包同时是该贴图最高优先包时才采用（:72-79）；首次见实体缓存“仅出生有效”属性，可更新属性按 `entityCanUpdate(uuid)` 重算（:236-257）。
2. **属性注册表**：`properties/RandomProperties.java` 静态块注册约 57 个工厂，统一签名 `RandomPropertyFactory.of(id, 翻译键, factory, isSpawnLocked)`，分 ETF 自有/ETF external/OptiFine 三组；`updatesOverTime()` 由 `isSpawnLocked` 取反，工厂内按配置屏蔽/限速。
3. **纹理分流与缓存**：`features/texture_handlers/ETFTextureVariator.java:21-29` 依据是否存在 `.properties` 选 `ETFTextureMultiple` 或 `ETFTextureSingleton`；`variantMap<Integer,ETFTexture>` 预载变体、缺图回落基础贴图（:137-145）；每实体后缀缓存 `ETFLruCache.UUIDInteger`（:115），过期策略由 `textureUpdateFrequency_V2` 决定，延迟模式用 `gameTime % delay == |uuid.hashCode()| % delay` 错峰（:193-208）。
4. **渲染状态栈**：`features/state/ETFState.java` 以 `ConcurrentLinkedDeque<ETFEntityRenderState>` 做 mount/unMount/state，另有 `specialPhaseStack`、`renderLayerModifyStack`；`stackVerify`（:115）错位时自愈、`stackVerifyEmpty` 收尾；`isRenderingFeatures`（:160）区分主渲染与 feature 层；`modifyRenderLayerIfRequired`（:200-255）按配置替换 RenderType。
5. **发光/附魔渲染**：`ETFTexture`（`isEmissive/isEnchanted`）+ `ETFSprite`、`ETFArmorHandler`，通过 `utils/{ETFVertexConsumer, ETFRenderLayerWithTexture, URenderTypeToVertexConsumer}` 在顶点消费者层换贴图/RenderType，并为 Sodium/Iris/ImmediatelyFast 各设包装 mixin。
6. **玩家皮肤**：`features/player/ETFPlayerTexture`(1473 行)、`ETFPlayerFeatureRenderer`、`ETFPlayerEntity`、`ETFPlayerSkinHolder`；`ETFManager.getPlayerTexture`（:280-313）用 `ETFLruCache<UUID, ETFPlayerTexture>` 缓存并显式处理构造期崩溃重试。

## 5. 网络 / 数据驱动 / 配置 / datagen
网络与 datagen：无。数据全部来自资源包：`<贴图>.properties`（OptiFine random entity 格式）、`optifine|textures|etf/emissive.properties` 发光后缀（`ETFManager.java:60-92`）、`*N.png` 变体与目录化（`ETFDirectory.getDirectoryVersionOf`）。配置：自研 `traben.tconfig.TConfigHandler<TConfig>`，GSON 写 `<gameDir>/config/ETF.json` 与 `etf_warnings.json`（`TConfigHandler.java:24-27,66,91`），`ETF.registerConfigHandler` 支持多份配置，`ETFConfigWarning` 可带自动修复回调。替代 datagen 的是 13 份按版本编号的 accesswidener（`entity_texture_features_3..15.accesswidener`，`build.gradle.kts` 按 `mcVersion` 区间选索引），NeoForge ≥26 走 `manuallyAccessTransform`。

## 6. Mixin
配置：`src/main/resources/entity_texture_features.mixins.json` —— `required true`、`minVersion 0.8`、`compatibilityLevel JAVA_16`（刻意压低以兼容宽区间）、`package traben.entity_texture_features.mixin.mixins`、`plugin traben.entity_texture_features.mixin.Plugin`、`injectors { maxShiftBy: 2, defaultRequire: 1 }`，约 60 条全部列在 `client` 段。插件 `mixin/Plugin.java:31-37`：`onLoad` 调 `MixinExtrasBootstrap.init()`，`shouldApplyMixin` 用 `MixinService...getClassNode(...)` 探测 Sodium 类决定是否应用 `MixinModelPartSodium`，并统一禁用指向空类 `traben.entity_texture_features.mixin.CancelTarget` 的 mixin（声明式停用）。代表 hook：`mixin/mixins/entity/renderer/MixinLivingEntityRenderer.java:48` 在 `render/submit` 的 `INVOKE Ljava/util/List;iterator()` 处注入、用 MixinExtras `@Share LocalRef` 传状态并置 `isRenderingFeatures`，在 `PoseStack.popPose()` 处复位（:67-72）；渲染方法描述符按版本用预处理常量切换（:40-46）。

## 7. 值得学的 5 条做法
1. 规则解析抽成可复用 provider：`ETFApi.ETFVariantSuffixProvider`（`ETFApi.java:464`）只暴露 `getSuffixForETFEntity/entityCanUpdate/getAllSuffixes`，EMF 直接复用它做模型变体。
2. 规则表末尾补哨兵 `DEFAULT_RETURN`（`PropertiesRandomProvider.java:68`），消除“无规则命中”分支。
3. 渲染上下文用栈管理而非全局单例：`ETFState.mount/unMount/stackVerify/stackVerifyEmpty`（`ETFState.java:44-155`），异常可自愈。
4. 缓存用 LRU + 错峰过期（`ETFTextureVariator.java:193-208`），把大量实体的属性重算摊到不同 tick。
5. 兼容 mixin 按 mod 分子包 + 运行期类存在性判定（`mixin/mixins/mods/*`、`Plugin.java:31-46`），并用 `CancelTarget` 空类做停用约定。

## 8. 公开 API
`ETFApi.java`（`ETFApiVersion = 12`，:83）对外静态方法：`registerCustomRandomPropertyFactory(modId, RandomPropertyFactory...)`（:434）、`registerCustomETFConfigWarning(modId, ETFConfigWarning...)`（:447）、`getCurrentETFVariantTextureOfEntity/ofBlockEntity`、`getCurrentETFEmissiveTextureOfEntityOrNull`、`renderETFEmissiveModel/ModelPart`（供 EMF 之类接管发光渲染）、`getLastMatchingRuleOfEntity/ofBlockEntity`、`getETFConfigObject/getCopyOfETFConfigObject/saveETFConfigChangesAndResetETF`、`stateOfEntityOrEntityState(Object)`、`getUUIDForBlockEntity(BlockEntity)`；扩展接口 `ETFVariantSuffixProvider` 需经 `getVariantSupplierOrNull(propertiesId, vanillaId, suffixKeys...)` 构造；常量 `ETF_GENERIC_UUID`、`ETF_SPAWNER_MARKER` 标识刷怪笼等非实体来源。
