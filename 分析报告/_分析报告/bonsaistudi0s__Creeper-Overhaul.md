# bonsaistudi0s/Creeper-Overhaul 源码分析报告

## 1. 基本信息

- Mod 名 Creeper Overhaul / `mod_id=creeperoverhaul` / 作者：美术 Joosh、程序 ThatGravyBoat / 版本 4.0.6（`gradle.properties`）
- 目标 MC 1.21+（`neoforge.mods.toml`：`neoforge [21.0,)`、`minecraft [1.21,)`），多加载器：`common` / `fabric` / `neoforge` 三模块，用 Fabric Loom + `libs.plugins.resourceful.loom`（TeamResourceful 的跨平台 Loom 插件）与根 `build.gradle.kts` 的 `getPlatform()` 分支（root `build.gradle.kts:15-40`）
- 许可证："All rights reserved"（非开源许可，仅可读不可复用代码）
- 编译依赖：**ResourcefulLib**（`modApi rlib`，提供 `Network`/`ResourcefulRegistry`）、**ResourcefulConfig**（`modApi rconfig`，注解式配置）、**GeckoLib 4.5.5+**（`modImplementation`，模型/动画，必装）、`yabn`/`bytecodecs`/`mclib`（`forgeRuntimeLibrary` 补 GeckoLib 依赖）；`rcosmetics` 库以 `include` jar-in-jar 打包
- common 层用 Architectury 的 `@ExpectPlatform` 注解声明平台差异（`client/CreepersClient.java:1-3`），fabric/neoforge 各提供 `CreepersClientImpl`/`PlatformUtilsImpl`/`ModItemsImpl`

## 2. 源码规模与包结构

- 80 个 `.java` / 4,973 行（common 4,415 / fabric 358 / neoforge 200）；小体量、结构清晰
- 主要包：`client/cosmetics`(8，含 `service`/`ui`)、`client/renderer/{normal,replaced,cosmetics}`(10)、`common/entity/{base,custom,goals}`(14)、`common/registry`(6)、`common/config`(3)、`common/network/{packets}`(3)、`mixin`(6)
- 最大文件：`common/entity/base/BaseCreeper.java` 400、`common/entity/CreeperTypes.java` 318、`common/entity/base/CreeperType.java` 278、`custom/PufferfishCreeper.java` 219、`fabric/CreepersFabric.java` 140、`client/cosmetics/CosmeticTexture.java` 126

## 3. 入口与注册

- 主类 `common/.../Creepers.java`：`init()` 只注册配置与六个注册器（`Creepers.java:24-34`），另有 `registerAttributes(Map)` 把 16 种苦力怕的属性写进传入的 Map（由各平台自行消费），`id(String)` 统一 ResourceLocation。
- 注册框架是 **ResourcefulLib 的 `ResourcefulRegistry`**：`ModEntities.ENTITIES = ResourcefulRegistries.create(BuiltInRegistries.ENTITY_TYPE, MODID)`，每个实体写 `ENTITIES.register("jungle_creeper", () -> EntityType.Builder.of(BaseCreeper.of(CreeperTypes.JUNGLE), MobCategory.MONSTER)...build("jungle_creeper"))`（`registry/ModEntities.java:16-25`）。
- 平台入口：`fabric/CreepersFabric.java`（`ModInitializer`，注册属性/生成规则/生物群系刷怪增删 + `PluginLoader.load()`）、`neoforge/forge/CreepersForge.java`（`@Mod`，`EntityAttributeCreationEvent`/`RegisterSpawnPlacementsEvent`/`FMLCommonSetupEvent`/`InterModProcessEvent`）。

## 4. 核心系统

1. **数据即实体（CreeperType + Builder）**：`common/entity/base/CreeperType.java` 是一条 `record`，含 23 个字段（贴图/发光贴图/带电贴图/模型/去毛模型/动画/近战伤害/方块替换器 `Map<Predicate<BlockState>, Function<RandomSource, BlockState>>`/害怕的实体/攻击的实体/爆炸施加药水/死亡药水云/伤害免疫/属性回调/剪刀掉落/7 个声音函数/`canSpawn`），配一个全默认值的 `Builder`（第 78-276 行）；`common/entity/CreeperTypes.java` 用 Builder 声明 16 种变体（314 行），全部差异只在数据层，实体类只有 4 个。
2. **实体族**：`BaseCreeper extends Creeper implements GeoEntity, Shearable`（400 行）承载膨胀/爆炸/交互/受击；子类 `NeutralCreeper`、`PassiveCreeper`、`WaterCreeper`、`PufferfishCreeper` 只改行为；工厂方法 `BaseCreeper.of(type)/ofNeutral/ofPassive` 供注册使用（`BaseCreeper.java:75-85`）。
3. **爆炸即世界改造**：`BaseCreeper.explode()`（第 193-233 行）按 `type.inflictingPotions()` 给被炸玩家上药水、按 `type.replacer()` 把爆点下方方块替换（蘑菇→菌丝体、洞穴→1% 煤矿）、并用 `AreaEffectCloud` 生成带药水效果的云；`isExplodingCreeper()` 用 `type.melee()==0` 判定"爆炸型 vs 近战型"。
4. **客户端双渲染器**：`client/renderer/normal/CreeperRenderer + CreeperModel/GlowLayer/PowerLayer` 渲染本 mod 实体，`renderer/replaced/ReplacedCreeper*` 用来替换**原版**苦力怕的渲染（配置/兼容开关式共存），`RenderTypes.java` 自定义 RenderType。
5. **Cosmetics 系统（原版玩家外观挂件）**：`client/cosmetics/` 从远端 API 下载模型/贴图（`service/CosmeticsApi.java`、`DownloadedAsset`、`StatusCode`），`Cosmetic.fromJson` 解析 texture/model/anchor/transformation，用 GeckoLib 渲染；`renderer/cosmetics/CosmeticLayer` 通过 `LivingEntityRendererInvoker.invokeAddLayer` 挂到玩家渲染器上，并有完整 UI（CosmeticGridWidget/CosmeticPreview/CosmeticsClaimModal/LoginModal）。
6. **可插拔第三方扩展（Plugin API）**：`api/CreeperPlugin`（`id()`、`canAttack(LivingEntity)`、`isAfraidOf(BaseCreeper, LivingEntity)`）+ 单例 `api/PluginRegistry`（重复 id 抛异常；`canAttack` 为"全部插件通过与"、`isAfraidOf` 为"任一插件或"），在 AI 中生效：`BaseCreeper.registerAttackGoals` 的 `NearestAttackableTargetGoal` 谓词直接调 `PluginRegistry.getInstance().canAttack(this, entity)`（`BaseCreeper.java:99-104`）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**ResourcefulLib `Network`** 封装，`NetworkHandler.NETWORK = new Network(Creepers.id("main"), 1)`（版本号 1），仅 2 个包：`ServerboundCosmeticPacket`(boolean) 与 `ClientboundCosmeticPacket(Object2BooleanMap<UUID>)`；包用 `ByteCodec`（bytecodecs 库）定义编解码，再 `map(...)` 成 record 工厂，`CodecPacketType.Server.create(id, codec, NetworkHandle.handle(...))` 一行完成注册与处理（`network/packets/*.java`）。
- 配置：**ResourcefulConfig 注解式**（`@Category("spawning")`、`@ConfigEntry(id=...)`、`@Comment`），`Creepers.CONFIGURATOR.register(CreepersConfig.class)`；`SpawningConfig` 每个变体一个 `allowXxxCreeperSpawning` 布尔，被 `CreeperTypes` 的 `setCanSpawn(...)` 与 `ModSpawns.getPredicate` 双层把关（`registry/ModSpawns.java:19-21`）。客户端 `ClientConfig.showCosmetic` 用 `addListener` 监听变化并即时发包。
- 刷怪/生物群系：fabric 侧用 `BiomeModifications.addSpawn` + `ModificationPhase.REMOVALS` 移除原版苦力怕（`fabric/CreepersFabric.java:58-140`）；neoforge 侧只注册生成规则，靠 `ModSpawns.Registrar` 接口抹平 API 差异（`CreepersForge.java:52-58`）。
- datagen：**无**（无 datagen 源码，资源为手工 assets/data）。

## 6. Mixin

- 配置：`common/src/main/resources/creeperoverhaul-common.mixins.json`（required、JAVA_17；mixins: IronGolemMixin、PlayerListMixin；client: ClientPacketListenerMixin、LivingEntityRendererInvoker）+ `fabric/src/main/resources/creeperoverhaul.mixins.json`（fabric.BaseCreeperMixin、client fabric.EntityRenderDispatcherMixin）。
- `IronGolemMixin`：注入 lambda 方法 `method_6498`（`IronGolem` 的攻击目标谓词），把被动型/近战型苦力怕排除在铁傀儡攻击范围外。
- `PlayerListMixin.placeNewPlayer`(TAIL) → 玩家进服同步 cosmetics；`ClientPacketListenerMixin.handleLogin`(TAIL) → `minecraft.tell` 回传本地 `ClientConfig.showCosmetic`。
- `LivingEntityRendererInvoker`：`@Invoker("addLayer")` 暴露 `LivingEntityRenderer#addLayer` 给 `CosmeticLayer` 用；fabric 的 `EntityRenderDispatcherMixin` 在 `onResourceManagerReload`(TAIL) 重新挂层，规避资源重载后丢层。
- `fabric.BaseCreeperMixin`：重写 `goDownInWater/jumpInLiquid/moveRelative` 用自定义 `swim_speed` 属性（fabric 无法加属性，见 `registry/fabric/FabricAttributes.java`）。
- `common/src/main/resources/creeperoverhaul.accesswidener`：仅开放 `RenderType#create`。

## 7. 值得学的 5 条具体做法

1. **变体数据化**：把"一种怪"的所有差异收进一个 record + Builder（`CreeperType.java`），实体只写一次 —— 加新变体 = 加一段 Builder 声明（`CreeperTypes.java`）。
2. **爆炸后处理**：`BaseCreeper.explode()` 的 `Map<Predicate<BlockState>, Function<RandomSource, BlockState>> replacer` 让"爆炸改造地形"完全数据化（`CreeperTypes.MUSHROOM`/`CAVE`）。
3. **轻量插件 API**：`api/CreeperPlugin` + `PluginRegistry` 单例（合成真值表式聚合），Fabric 走 entrypoint、NeoForge 走 `InterModComms "plugin/register"`（`fabric/PluginLoader.java`、`CreepersForge.java:66-75`）—— 小 mod 做扩展点最少代码的做法。
4. **平台差异函数式抽象**：`ModSpawns.Registrar`、`registerAttributes(Map)` 这类"注册动作参数化"，让 common 完全不含平台判断。
5. **几何/渲染小技巧**：`@Invoker` 暴露 `addLayer` 后自行挂玩家渲染层（`mixin/LivingEntityRendererInvoker.java` + `CosmeticLayer`），以及用 `ReplacedCreeper*` 渲染器替换原版实体外观的成对方案。
