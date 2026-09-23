# MoePus/Flerovium 源码分析报告

## 1. 基本信息
- Mod 名：Flerovium；mod_id：`flerovium`；`mod_version=1.2.19`；`mod_license=LGPL3.0`；`mod_group_id=com.moepus`；`mod_authors`/`mod_description` 为空（`gradle.properties`）
- 目标：**Forge 1.20.1 客户端渲染优化 mod**，`minecraft_version=1.20.1`、`forge_version=47.3.7`、`forge_version_range=[47,)`、`loader_version_range=[47,)`、`mapping_channel=official`、Java 17
- Gradle：`build.gradle` 用 ForgeGradle `[6.0,6.2)` + `org.spongepowered:mixingradle:0.7-SNAPSHOT`；`mixin { add sourceSets.main, "flerovium.refmap.json" }`，`debug.export = true`
- 依赖：`implementation fg.deobf("org.embeddedt:embeddium-1.20.1:0.3.31-beta.53")`（**必需前置**，`mods.toml` 中 `modId="embeddium" mandatory=true versionRange="[0.3.25,)"`，全部依赖 `side="CLIENT"`）、`compileOnly curse.maven:oculus`（光影）、`jarJar(fg) mixinextras 0.4.1`
- 注意：`gradle.properties` 里遗留了 `create_version=0.5.1.j-55`、`flywheel_version=0.6.11-13`、`registrate_version=MC1.20-1.3.3`，但 **`build.gradle` 未引用，无任何 Create/Flywheel 依赖**——本 mod 不是 Create 附属，而是 Sodium/Embeddium 生态的渲染加速 mod

## 2. 源码规模与包结构
- `.java` **34** 个，总 **2452** 行（实测 `find -name '*.java' | wc -l` / `-exec wc -l {} +`）
- 包：`com/moepus/flerovium`(4：Flerovium/Config/ConfigParser/MixinPlugin)、`functions`(6)、`functions/BlockBreaking`(5)、`functions/Chunk`(2)、`Iris`(2)、`mixins/Particle`(4)、`mixins/Item`(4)、`mixins/Sound`(2)、`mixins/Entity`(2)、`mixins/Chunk`(2)、`mixins/Block`(1)
- 最大文件：`functions/FastEntityRenderer.java` 346、`BlockBreaking/BlockBreakingDecalGenerator.java` 190、`FastSimpleBakedModelRenderer.java` 162、`mixins/Particle/SingleQuadParticleMixin.java` 156、`IntFlatMap.java` 106、`mixins/Item/ItemTransformMixin.java` 103

## 3. 入口与注册
- 入口 `src/main/java/com/moepus/flerovium/Flerovium.java`：`@Mod(Flerovium.MODID)`，构造器只做 `modEventBus.addListener(this::commonSetup)` 与 `MinecraftForge.EVENT_BUS.register(this)`，两个事件体都是空方法——**mod 本身零注册、零内容，全部逻辑通过 mixin 生效**
- 唯一"注册"是静态字段在类加载时读配置：`public static final Config config = ConfigParser.getConfig();`（`Flerovium.java:23`）
- 版本元数据走 Forge 模板占位符：`src/main/resources/META-INF/mods.toml` 用 `${mod_id}`/`${mod_version}` 等，由 `build.gradle` 的 `processResources { filesMatching(['META-INF/mods.toml','pack.mcmeta']) { expand replaceProperties } }` 展开

## 4. 核心系统
1. **快速实体模型渲染** — `functions/FastEntityRenderer.java`：绕开原版 `ModelPart.render` 的状态机，用常量表 `CUBE_VERTICES[6][4]`/`VERTEX_X1_Y1_Z1`…`Z2` 定义正方体 8 顶点 6 面，顶点用 `long xy/zw` 打包（`Float.floatToRawIntBits` + `compose`），一次性 `nmemAlignedAlloc(64, 6*4*ModelVertex.STRIDE)` 分配 64 字节对齐 scratch buffer，配 `MemoryStack` 直接向 Sodium 的 `VertexBufferWriter` push（`ParticleVertex.put`/`ModelVertex` 格式）；由 `mixins/Entity/ModelPartMixin`（`priority = 900`，`@Inject(method="render(...)", at=@At("HEAD"), cancellable=true)`）接管
2. **物品背面剔除与批量渲染** — `mixins/Item/ItemRendererMixin.java`：`@ModifyArg` 拦截 `renderModelLists` 调用，先由 `flerovium$decideCull(ItemTransforms, ItemDisplayContext, PoseStack.Pose)` 算出"要剔除哪些面"的位掩码（`1 << Direction.X.ordinal()`，另有自定义位 `extraCull = 0b1000000` 表示双面剔除），再用 `FastSimpleBakedModelRenderer.render(...)` 自己写顶点，最后返回 `DummyModel` 让 `@Inject(... at="HEAD" cancellable) { if (model == flerovium$dummy) ci.cancel(); }` 吃掉原版渲染。判定依赖 `RenderSystem.modelViewMatrix.m32()`（视图空间 Z）区分 GUI/世界，并用 `transforms.gui.rotation.equals(30,225,0)` 识别方块类 GUI 变换
3. **区块遮挡剔除改造** — `mixins/Chunk/OcclusionCullerMixin.java`：`@Mixin(value = OcclusionCuller.class, remap = false)`（直接改 Sodium 类）用 `@Overwrite` 重写 `processQueue`，加入 `flerovium$processVisibilityByAngleOcculusion`（注明取自 sodium PR #2811）：按视点与区块中心的 `dx/dy/dz` 比较，屏蔽掉"斜穿"的可见性路径（`Occlusion.ThroughUpDown/ThroughEastWest/ThroughNorthSouth`，`Occlusion.bit(from,to) = from*8 + to` 把 8 个 `GraphDirection` 编成 64 位掩码）
4. **快速视锥** — `functions/Chunk/FastSimpleFrustum.java` + `mixins/Chunk/FrustumMixin.java`：反射取 `FrustumIntersection` 的 `Vector4f[] planes`（用 `getDeclaredField`），把 6 个平面法线摊平成 15 个 float 字段，并用 `CHUNK_SECTION_SIZE = 8.0 + 1.0 + 0.125f`（区块半径 + 最大模型外扩 + epsilon）预计算"双负 w"常量，实现无对象分配的区块可见性测试
5. **粒子/方块破坏渲染优化** — `mixins/Particle/SingleQuadParticleMixin.java`（`priority = 100`）`@Inject(render, HEAD, cancellable)` 后用 `camera.getLeftVector()/getUpVector()` + `Math.fma` 直接算 4 个顶点（注释里画了 ASCII 示意图），并用 `flerovium$lastTick/flerovium$cachedLight` 按 tick 缓存光照；`mixins/Block/CrumblingRendererMixin.java` `@Redirect(method="renderLevel", target="...Long2ObjectMap;long2ObjectEntrySet()")` 接管挖掘裂纹：自己遍历 `BlockDestructionProgress`，先 `frustum.intersection.testSphere(relx,rely,relz,0.7f)` 粗筛，再交给 `functions/BlockBreaking/BlockBreakingDecalGenerator`（自定义 `DefaultedVertexConsumer`，`calcUV` 手算各面 UV）
6. **音频与其他** — `mixins/Sound/SoundEngineMixin.java` 在 `play` 中 `resolve` 之后 cancel：非流式声音若 `library.staticChannels.getUsedCount() >= getMaxCount()` 直接丢弃（防声道耗尽）；`mixins/Sound/ClientLevelMixin.java` 按配置关闭距离剔除；`Iris/IrisCompat.java` 用反射读 `net.irisshaders.iris.vertices.IrisVertexFormats.ENTITY/TERRAIN` 做光影兼容

## 5. 网络 / 数据驱动 / 配置 / datagen
- **无网络、无数据包注册、无 datagen**（`build.gradle` 的 `data` run config 和 `src/generated/resources` 是 Forge 模板残留）
- 配置：`Config.java` 只有 4 个 public 字段（`entityBackFaceCulling`、`itemBackFaceCulling`、`reduceTerrainParticles`、`disableSoundDistanceCull`）；`ConfigParser.java` 手写 Gson 读写 `FMLPaths.CONFIGDIR/flerovium.json`（不存在则建默认并 `saveConfig()`；存在则 `fromJson` 后立即回写，会格式化覆盖原文件），`getConfig()` 懒加载。实际生效的字段少：`disableSoundDistanceCull` 在 `MixinPlugin.shouldApplyMixin` 里读，`itemBackFaceCulling` 在 `ItemRendererMixin.flerovium$decideCull` 里读（via `Flerovium.config`）

## 6. Mixin
- 配置：`src/main/resources/flerovium.mixins.json`（`required: true`、`compatibilityLevel: JAVA_17`、`refmap: flerovium.refmap.json`、`plugin: com.moepus.flerovium.MixinPlugin`），`mixins` 段仅 1 个 `Chunk.OcclusionCullerMixin`，其余 14 个在 `client` 段
- `MixinPlugin.java` 是本仓库最有价值的文件之一：`shouldApplyMixin` 用 `LoadingModList.get().getModFileById(modId) != null` 做软冲突开关——`ModelPartMixin` 遇 `bendylib`/`physicsmod` 不加载、`FrustumMixin` 遇 `acedium`/`nvidium` 不加载、`ParticleEngineMixin`/`ParticleMixin` 遇 `particle_core` 不加载、`SkipFarTerrainParticle` 遇 `valkyrienskies` 不加载、`Sound.ClientLevelMixin` 按配置与 `valkyrienskies` 决定
- 关键 hook 目标：`ModelPart#render(...)`、`ItemRenderer#renderModelLists`/`render`、`OcclusionCuller#processQueue`（@Overwrite）、`LevelRenderer#renderLevel`（@Redirect `Long2ObjectMap#long2ObjectEntrySet`）、`ParticleEngine#render`（@Redirect `Frustum#isVisible`）/`destroy`（@Inject HEAD）、`Particle#<init>`（@Redirect `RandomSource.create`）、`SingleQuadParticle#render`、`SoundEngine#play`、`ClientLevel#playSound`/`getEntityCollisions`、`ItemTransform#<init>`/`apply`、`SimpleBakedModel#getRenderTypes`（@Overwrite，缓存 RenderType 到可变 shadow 字段）
- `src/main/resources/META-INF/accesstransformer.cfg` 打开：`Frustum.f_112996_`(camX) 等 4 字段、`Particle.f_107212_/f_107213_/f_107214_/f_107221_/f_107222_`、`RenderSystem.modelViewMatrix`、`BufferBuilder.f_85658_`(format)、`Library.f_83689_`(staticChannels)、`Library$ChannelPool`（用 SRG 名，1.20.1 官方映射下生效）

## 7. 值得学的 5 条具体做法
1. **用 `IMixinConfigPlugin.shouldApplyMixin` 做兼容性开关**：`MixinPlugin.java:28-37`，按 modid 与配置动态禁用自身 mixin，适用：优化类/侵入性 mod 避免与同类 mod 打架
2. **`@ModifyArg` 换返回值 + `@Inject(HEAD, cancellable)` 吞掉原方法**：`ItemRendererMixin.java:38-56`，把原版 `renderModelLists` 整个替换成自研快路径而不改方法签名，适用：整体替换原版某渲染/计算路径
3. **预分配对齐本地内存 + `MemoryStack` 组合顶点**：`FastEntityRenderer.java:54-55` 的 `MemoryUtil.nmemAlignedAlloc(64, 6*4*ModelVertex.STRIDE)` 与 `STACK.nmalloc(...)`（`SingleQuadParticleMixin.java` 同法），适用：高频每帧顶点生成，避免 GC
4. **位掩码代替集合表示朝向**：`Occlusion.bit/dir/between`（`functions/Chunk/Occlusion.java`）与 `flerovium$decideCull` 返回的面掩码，配合 `GraphDirection*8+to` 编码，适用：方向/面的组合运算与快速求交
5. **反射兜底第三方内部 API**：`Iris/IrisCompat.java`（`Class.forName("net.irisshaders.iris.vertices.IrisVertexFormats")` + `getDeclaredField("ENTITY")`）与 `FastSimpleFrustum.getFrustumPlanes` 反射读 JOML 私有平面数组，适用：可选兼容 mod 或原版私有结构
6. （附）**缓存不可变查询结果**：`SimpleBakedModelMixin` 用 `@Mutable @Shadow` 把首次结果写回原字段做缓存；`SingleQuadParticleMixin` 按 tickCount 缓存光照

## 8. 扩展点 / API
非库模组，无公开 API 包；对外只有 `flerovium.json` 的 4 个布尔开关与配置项 `Flerovium.config` 静态可达。
