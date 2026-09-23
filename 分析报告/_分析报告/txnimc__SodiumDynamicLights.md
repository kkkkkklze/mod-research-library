# txnimc/SodiumDynamicLights 源码分析报告

## 1. 基本信息
- Mod 名：Sodium Dynamic Lights；mod_id：`sodiumdynamiclights`；作者：toni（Txni，`mod.author=toni`），署名含原作者 LambdAurora（LambDynLights 的 fork）
- 目标 MC：stonecutter 激活版本 `1.21.5-neoforge`（`stonecutter.gradle.kts:5`）；`settings.gradle.kts` 中 1.20.1/1.21.1/1.21.4 的 mc 声明被注释掉，仅启用 `mc("1.21.5", "fabric", "neoforge")`
- 加载器：NeoForge + Fabric 双端（`versions/1.21.5-neoforge/gradle.properties: loom.platform=neoforge`）；资源里有 `META-INF/mods.toml` 与 `META-INF/neoforge.mods.toml`（模板占位符 `${id}` 等），无 fabric.mod.json（由构建插件生成）
- 许可证：MIT（`gradle.properties: mod.license=MIT`，`LICENSE.md`）
- Gradle 插件：自定义 `toni.blahaj` 2.0.16（`build.gradle.kts:7`）+ `dev.architectury.loom` 1.10-SNAPSHOT + `dev.kikugie.stonecutter` 0.6-alpha.5。源码用预处理宏 `#if mc >= 215 / #if FABRIC / #if NEO / #if FORGE / #if FORGELIKE / #if AFTER_21_1 / #if CURRENT_20_1` 做多版本/多平台条件编译
- 编译依赖（`build.gradle.kts`）：`sodium`（modrinth mc1.21.5-0.6.13-neoforge，implementation）；`com.github.bawnorton.mixinsquared:mixinsquared-*:0.2.0-beta.6`（compileOnly + include）；Syntra forgified-fabric-api 的 `fabric-api-base`/`fabric-rendering-data-attachment-v1`/`fabric-block-view-api-v2` 与 `net.caffeinemc:fabric-renderer-api-v1:6.0.0`（均 compileOnly，说明 mixin 直接打这些 Fabric API 内部类）

## 2. 源码规模与包结构
- `.java` 40 个，共 3538 行（`find src -name '*.java' -exec wc -l {} +`）
- 包（第 3 层）：`toni.sodiumdynamiclights`（8）、`.accessor`（2）、`.mixin`（11）、`.mixin.fabric`（1）、`.mixin.lightsource`（8）、`.mixin.sodium`（4）、`.util`（2）；API 兼容包 `dev.lambdaurora.lambdynlights.api`（3）、`.api.item`（3）
- 最大文件：`SodiumDynamicLights.java` 677、`mixin/lightsource/EntityMixin.java` 219、`api/item/ItemLightSource.java` 209、`api/DynamicLightHandlers.java` 190、`mixin/lightsource/BlockEntityMixin.java` 171、`DynamicLightsConfig.java` 154、`util/DynamicLightingPage.java` 138、`api/DynamicLightHandler.java` 134、`api/item/ItemLightSources.java` 121、`DynamicLightSource.java` 103

## 3. 入口与注册
- 主类 `src/main/java/toni/sodiumdynamiclights/SodiumDynamicLights.java:128`：`@Mod("sodiumdynamiclights") public class SodiumDynamicLights implements ClientModInitializer`（宏包裹），构造器里 `modEventBus.addListener(this::clientSetup)` 且 `modContainer.registerConfig(ModConfig.Type.CLIENT, DynamicLightsConfig.SPECS)`（`:140-152`）
- Fabric 侧 `onInitializeClient()`（`:155`）做四件事：注册客户端配置、从 entrypoint `dynamiclights`/`sodiumdynamiclights` 读取 `DynamicLightsInitializer` 并反射调用（兼容新旧签名，`:173-203`）、注册 `SimpleSynchronousResourceReloadListener` 触发 `ItemLightSources.load`、`WorldRenderEvents.START` 里调用 `updateAll`；ForgeLike 侧用 `@SubscribeEvent clientSetup` + `registerReloadListener(PackType.CLIENT_RESOURCES, …)`
- 无物品/方块/实体注册（纯客户端光照 mod），无 DeferredRegister/Registrate

## 4. 核心系统
1. **光源追踪与节流更新**（`SodiumDynamicLights.java:135-302`）：`Set<DynamicLightSource> dynamicLightSources` + `ReentrantReadWriteLock lightSourcesLock`；`updateAll(renderer)` 以 `now >= lastUpdate + 50` 毫秒节流，逐光源 `sodiumdynamiclights$updateDynamicLight(renderer)`；`updateTracking` 依据 `luminance > 0` 与 `isDynamicLightEnabled` 做增删
2. **光照级别与 lightmap 合成**（`:320-407`）：`maxDynamicLightLevel` 取 `MAX_RADIUS = 7.75` 平方衰减 `multiplier = 1 - sqrt(dist²)/MAX_RADIUS`；`getLightmapWithDynamicLight` 直接位操作 lightmap（`lightmap &= 0xfff00000; lightmap |= luminance & 0x000fffff`，`:353-355`）；提供 `getLightmapWithDynamicLight(Entity, int)` 取 `max(位置光照, 实体亮度)`
3. **光源接口 + mixin 注入**（`DynamicLightSource.java:21-103`）：接口方法统一前缀 `sdl$`/`sodiumdynamiclights$`（避免冲突），由 `mixin/lightsource/EntityMixin.java`（`@Unique` 字段 `sodiumdynamiclights$luminance`/`lastUpdate`/`lastLuminance`，`isOnFire() ? 15 : 0`，移动 `>0.1D` 才重建区块）和 `BlockEntityMixin.java` 实现；`PlayerEntityMixin`、`LivingEntityMixin`、`PrimedTntEntityMixin`、`AbstractMinecartEntityMixin`、`AbstractHurtingProjectileEntityMixin`、`BlockAttachedEntityMixin` 补齐各类光源
4. **公开 API 层**（`dev/lambdaurora/lambdynlights/api/`）：`DynamicLightHandler<T>`（`makeHandler`、`makeLivingEntityHandler`、`makeCreeperEntityHandler`，含 `isWaterSensitive` 默认方法）；`DynamicLightHandlers.registerDefaultHandlers()` 按 `EntityType` 注册 Default（BLAZE 10、ENDERMAN 手持方块亮度、GLOW_ITEM_FRAME ≥14、GLOW_SQUID 用 `Mth.clampedLerp` 渐变等）；`DynamicLightHandlerHolder<T>` 访问器把 handler 存回 `EntityType`/`BlockEntityType`（`mixin/EntityTypeMixin`、`BlockEntityTypeMixin` 用 `@Unique` 字段持有）
5. **数据驱动物品光源**（`api/item/ItemLightSources.java:47-67`）：reload 时 `resourceManager.listResources("dynamiclights/item", path -> endsWith(".json"))`，逐文件 `JsonParser` 解析后 `ItemLightSource.fromJson`；`ItemLightSource.java` 处理水下敏感（`submergedInWater`）
6. **Sodium 集成**：`mixin/sodium/ArrayLightDataCacheMixin`（`@Inject(method="get(III)I", at=HEAD, require=0)`）、`FlatLightPipelineMixin`（`getOffsetLightmap` RETURN ordinal=1）、`LightDataAccessMixin`（`getLightmap` RETURN，`remap=false`）——用 `@Mixin(targets={...})` 直接打 Sodium 内部类；`SodiumOptionsGuiMixin`（`priority=100`，`<init>` RETURN 注入）+ `util/DynamicLightingPage.java` 用 Sodium 的 `OptionPage/OptionGroup/OptionImpl + CyclingControl + SodiumOptionsStorage` 把动态光照页塞进 Sodium 视频设置
7. **配置**：`DynamicLightsConfig.java:60-95` 用 `ModConfigSpec` 定义 `mode`(枚举)/`entities`/`self`/`block_entities`/`water_sensitive_check`/`tnt`/`creeper`；`DynamicLightsMode.java` 枚举 `OFF/SLOW(500ms)/FAST(250ms)/REALTIME`

## 5. 网络 / 数据驱动 / 配置 / datagen
- 网络：无（无网络包注册，纯客户端 mod）
- 数据驱动：仅物品光源 JSON（资源路径 `dynamiclights/item/*.json`），走原版 reload listener，不用 Codec/Registry
- 配置：NeoForge/Forge 原生 `ModConfigSpec`，Fabric 侧通过 `forgeconfigapiport`（`ConfigRegistry`/`NeoForgeConfigRegistry`/`ForgeConfigRegistry`，`:165-170`）
- datagen：无

## 6. Mixin
- 配置：`META-INF/mods.toml` 中 `[[mixins]] config = "mixins.${id}.json"`，但仓库 `src/main/resources` 下**不存在**该 json（应由 `toni.blahaj` 构建插件生成，未确认）；`sodiumdynamiclights.accesswidener` 内容仅 `accessWidener v2 named`（空表），另有 1.20.1/1.21.1/1.21.4 三份版本化文件
- 代表性 hook：`MixinSquared` 编译依赖表明用于跨 mod mixin 冲突协调；`mixin/CommonLevelRendererMixin.java:32` 注入 `LevelRenderer#getLightColor(BlockAndTintGetter,BlockState,BlockPos)`（`priority=900`）；`LevelRendererBrightnessMixin.java:12` 直接打字面混淆名 `LevelRenderer$BrightnessGetter#method_68890(...)` 的 TAIL；`EntityRendererMixin`（`getBlockLightLevel` RETURN cancellable）；`ClientLevelMixin`（`removeEntity(IL…RemovalReason;)V` HEAD）；`LevelMixin`（`tickBlockEntities`）；`MinecraftClientMixin`（`updateLevelInEngines` HEAD）；`mixin/fabric/AoCalculatorMixin` 打 `net.fabricmc.fabric.impl.client.indigo.renderer.aocalc.AoCalculator#getLightmapCoordinates`（RETURN ordinal=0，`remap=false`）

## 7. 值得学的 5 条具体做法
1. **单文件多平台/多版本条件编译**：一个 `SodiumDynamicLights.java` 用 `#if NEO/#if FORGE/#if FABRIC` 承载三端初始化（`SodiumDynamicLights.java:60-114,140-280`），适用于想用 stonecutter 维护单代码库的 mod
2. **接口方法加命名空间前缀**：`sdl$getLuminance()`、`sodiumdynamiclights$scheduleTrackedChunksRebuild()`（`DynamicLightSource.java`）避免与其他 mod 的 mixin 注入接口冲突
3. **lightmap 位运算直接改写**：不做后处理，`lightmap = (lightmap & 0xfff00000) | ((int)(level*16) & 0x000fffff)`（`SodiumDynamicLights.java:353`），适用于任何"叠加自定义光源到原版光照"的需求
4. **用 `ReentrantReadWriteLock` + 读写分离保护跨线程光源集合**（`SodiumDynamicLights.java:136,296-300`），适用于渲染线程与逻辑线程共享的可变集合
5. **对外兼容旧 API 的反射兜底**：遍历 entrypoint 类的方法，先试无参 `onInitializeDynamicLights()`，失败再试单参旧签名（`SodiumDynamicLights.java:182-199`），适用于 fork 遗产 API 的平滑过渡

## 8. 公开 API 与接入方式
- API 包：`dev.lambdaurora.lambdynlights.api`（`DynamicLightHandler`、`DynamicLightHandlers`、`DynamicLightsInitializer`）与 `.api.item`（`ItemLightSource`、`ItemLightSources`、`ItemLightSourceManager`）
- 扩展点一：实现 `DynamicLightsInitializer`（`onInitializeDynamicLights()`）并在 Fabric 侧注册 entrypoint `dynamiclights` 或 `sodiumdynamiclights`
- 扩展点二：直接调用静态 `DynamicLightHandlers.registerDynamicLightHandler(EntityType|BlockEntityType, DynamicLightHandler)`，可在任意客户端初始化阶段注册
- 扩展点三：资源包/数据包放 `assets/<ns>/dynamiclights/item/*.json` 声明物品光源（`ItemLightSources.load`）
- handler 存储方式：通过 `DynamicLightHandlerHolder` 接口 + `@Mixin(EntityType.class)`/`@Mixin(BlockEntityType.class)` 的 `@Unique` 字段挂载到原版注册对象上（`accessor/DynamicLightHandlerHolder.java:23-30`）
