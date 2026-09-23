# DragonsPlusMinecraft/VisualityReforged 源码分析

## 1. 基本信息

- Mod 名：Visuality: Reforged（`mod_name=visuality-forge`）/ mod_id：`visuality` / 作者：LimonBlaze（DragonsPlusMinecraft，中文作者）
- 目标：NeoForge `21.8.36`（`neo_version_range=[21.8.0,)`）、MC `1.21.8`（`gradle.properties`）、Java 21、Parchment `2025.07.20`
- Gradle 插件：`net.neoforged.moddev` 2.0.143 + `me.modmuss50.mod-publish-plugin` 2.1.1（`build.gradle:4-5`）
- 许可证：MIT。编译依赖：除 NeoForge/MC 外无强依赖（JEI 相关行被注释，`build.gradle:89-95`）
- 纯客户端 Mod：`@Mod(value = Visuality.ID, dist = Dist.CLIENT)`（`Visuality.java:15`），数据全部 `sync(false)`

## 2. 源码规模与包结构

- 34 个 `.java`，共 2428 行（`find src -name '*.java' -exec wc -l {} +`）
- 包结构（`src/main/java/plus/dragons/visuality/`）：`config`（7 文件，最大）、`particle`（9）、`particle/type`（2）、`mixin`（6）、`data`（4）、`registry`（2）、`event`（1）
- 最大文件：`config/BlockAmbientParticleConfig.java` 295、`config/EntityArmorParticleConfig.java` 259、`config/EntityHitParticleConfig.java` 219、`config/ReloadableJsonConfig.java` 202、`config/BlockStepParticleConfig.java` 163、`particle/type/ColorScaleParticleType.java` 110

## 3. 入口与注册

主类 `src/main/java/plus/dragons/visuality/Visuality.java:20-32`：modBus 上注册 DeferredRegister、客户端 JSON 重载监听、`RegisterParticleProvidersEvent`，并用 `container.registerConfig(ModConfig.Type.CLIENT, Config.SPEC, ID + "/config.toml")` 指定 TOML 路径。

注册框架用原生 `DeferredRegister`，但**自建注册表**（`registry/VisualityRegistries.java:11-20`）：

```java
public static final ResourceKey<Registry<ParticleType<?>>> PARTICLE_TYPES_KEY =
    ResourceKey.createRegistryKey(Visuality.location("particle_type"));
public static final DeferredRegister<ParticleType<?>> PARTICLE_TYPES =
    DeferredRegister.create(PARTICLE_TYPES_KEY, Visuality.ID);
PARTICLE_TYPES_REGISTRY = PARTICLE_TYPES.makeRegistry(builder -> builder.sync(false));
```

13 个粒子类型在 `registry/VisualityParticles.java:17-37` 注册（sparkle/bone/feather/slime_blob/charge/water_circle/emerald/soul），provider 在 `registerProviders`（同文件 41-56）挂到自定义的 `VisualityParticleEngine`；`resources/META-INF/accesstransformer.cfg` 打开 `ParticleEngine$MutableSpriteSet`。

## 4. 核心系统

1. **可热重载 JSON 配置基类**：`config/ReloadableJsonConfig.java:34-123`，继承 `SimplePreparableReloadListener<List<Pair<String,JsonObject>>>`，同时从 `config/<ns>/*.json` 文件与资源包栈读取，先应用本地文件再叠加资源包条目；本地文件解析失败时不覆盖原文件（`configLoadFailed` 标记，185-199）。支持 `ICondition` 条件字段（106、125-131）。
2. **数据驱动方块粒子发射器**：`config/BlockAmbientParticleConfig.java`。`Entry` record 用 `RecordCodecBuilder` 定义 schema：`block`（`CompressedListCodec` 压缩单元素列表）、`direction`（`optionalField` 全 6 面时省略）、`particle`（`ParticleWithVelocity`）、`interval`；运行时构建 `IdentityHashMap<Block, Emitter>` + tag 查询列表，命中同方块时按 `priority`（`nextPriority++`）胜出（93-101）。
3. **旧配置平滑升级**：`registerLegacyCommonTag`（126-130）在加载旧版（显式列原版矿石 ID）配置时，运行时补挂 `Tags.Blocks.ORES_*` 通用标签，使新加模组矿石无需用户改配置即生效。
4. **带参数粒子类型**：`particle/type/ColorParticleType.java`（`ExtraCodecs.VECTOR3F` + `StreamCodec.ofMember` 同步颜色）、`ColorScaleParticleType.java`（颜色 + 缩放）；`data/ParticleWithVelocity.java` 把「粒子 + 初速度」打包成 codec，供 JSON 直接描述。
5. **粒子注册别名（AT+接口注入）**：`mixin/ParticleEngineMixin.java:22-47` 用 `@Shadow` 直接写 `ParticleEngine.providers/spriteSets`，并 `@ModifyExpressionValue` 改 `makeParticle` 里的 `Registry.getKey`，从而支持自定义注册表的粒子类型。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 无自定义网络包：自建注册表 `sync(false)`，全部逻辑客户端执行。
- 配置双轨：TOML（`config/Config.java`，`ModConfigSpec`，slime/charge/waterCircle 三类）；JSON（`config/visuality/particle_emitters/` 下 4 个文件：block_ambient、block_step、entity_hit、entity_armor），可被资源包覆盖。
- datagen：**无**（源码中没有 `GatherDataEvent`/DataProvider，`build.gradle` 仍保留 data run 配置）。

## 6. Mixin

配置：`src/main/resources/visuality.mixins.json`（package `plus.dragons.visuality.mixin`，`defaultRequire: 1`，全部 `client`）。代表性 hook：

- `mixin/ParticleEngineMixin.java:41` — `ParticleEngine.makeParticle`，`@ModifyExpressionValue` 改 `Registry.getKey`
- `mixin/SlimeMixin.java:30` — `Slime.spawnCustomParticles`，`@Inject(RETURN, cancellable=true, remap=false)`
- `mixin/BlockMixin.java:25/33/40` — `Block.fallOn`、`stepOn`、`animateTick` 的 TAIL
- `mixin/WaterFluidMixin.java:20` — `WaterFluid.animateTick` HEAD；`mixin/EntityMixin.java:19` — `Entity.hurtClient` HEAD；`mixin/LivingEntityMixin.java:12` — `LivingEntity.tick` TAIL

## 7. 值得学的 5 条做法

1. `ReloadableJsonConfig` 模式：把「配置文件 + 资源包」合并成同一份可重载数据源，并对非法条目只跳过不覆盖用户文件（`config/ReloadableJsonConfig.java:85-123`）——适合任何需要玩家/整合包自定义的数据表。
2. 自建 `Registry` + `sync(false)` 注册粒子类型，绕过原版 `ParticleTypes` 的同步开销（`registry/VisualityRegistries.java:11-17`）。
3. `CompressedListCodec`：单元素列表编码时不写数组，让手写 JSON 更简洁（`data/CompressedListCodec.java`）。
4. 数据表带 `priority` 字段 + `nextPriority++` 解决「方块 ID 与标签同时命中」的歧义（`config/BlockAmbientParticleConfig.java:93-107`）。
5. 版本迁移用运行时补挂标签，而不是让玩家重写配置（`BlockAmbientParticleConfig.java:116-130`）。

## 8. 库/API 说明

非库 Mod；对外扩展点仅「资源包 JSON」（`config/visuality/particle_emitters/<name>.json`，`block` 支持 `#tag` 写法）与 TOML 配置。
