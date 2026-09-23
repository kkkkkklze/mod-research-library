# ParticleStorm 源码深度分析

仓库根目录：`源码库\_参考仓库\_bulk\westernat__ParticleStorm`（下称路径均相对根目录）

## 1. 基本信息

| 项 | 值 | 出处 |
|---|---|---|
| mod 名 / id | ParticleStorm / `particlestorm` | gradle.properties:22,26 |
| 作者 / 版本 | Westernat / 1.4.2.1 | gradle.properties:28,31 |
| 许可证 | LGPL-3.0 | gradle.properties:24；LICENSE 为 GNU LGPL v3 全文 |
| MC / 加载器 | 1.21.1 / NeoForge 21.1.219（Java 21，Parchment 2024.06.23） | gradle.properties:9,13,19 |
| 构建插件 | `net.neoforged.moddev` 2.0.141（无 shadow/mixin-gradle 插件，用官方 mixin 支持） | build.gradle:3 |
| 可选依赖 | GeckoLib 4.8.4（`compileOnly` + `localRuntime`，非硬依赖） | build.gradle:60-67 |
| 分支（`git ls-remote --heads origin`） | `fabric-dev/26.1.2`, `forge-dev/1.20.1`, `neoforge-dev/1.21.1`, `neoforge-dev/26.1.2`, `neoforge/1.21.1`(=默认分支/HEAD `06fe5af`) | 实测 |

本地仓库干净、仅检出 `neoforge/1.21.1`，工作区无改动（`git status --porcelain` 空）。构建脚本里有 `systemProperty 'particlestorm.debug'`、JetBrains 热重载 JVM 参数（build.gradle:75-85），`DEBUG` 开启时才注册 GeckoLib 示例内容（ParticleStorm.java:47,89-93）。

## 2. 基岩粒子格式的覆盖度

注册入口全部在 `src/main/java/org/mesdag/particlestorm/PSGameClient.java:184-234`（`registerComponents()` / `registerEventNodes()`）。

已实现的 emitter 组件：`emitter_local_space`、`emitter_initialization`、`emitter_rate_instant/steady/manual`、`emitter_lifetime_looping/once/expression/events`（PSGameClient.java:185-196）、`emitter_shape_point/sphere/box/entity_aabb/disc`（PSGameClient.java:197-201，实现见 data/component/EmitterShape.java，sealed 类，五种子类）。

已实现的 particle 组件：`particle_initial_speed/spin/initialization`（PSGameClient.java:203-205，注意官方 "Particle Component List" 页未列出 `particle_initialization`）、`particle_motion_dynamic/parametric/collision`（207-209）、`particle_appearance_billboard/tinting/lighting`（211-213）、`particle_lifetime_expression`、`particle_lifetime_events`、`particle_kill_plane`、`particle_expire_if_in_blocks`、`particle_expire_if_not_in_blocks`（215-219）。

其它格式要素：
- **curves**：`ParticleCurve`（data/curve/ParticleCurve.java:41-113）支持 `linear/bezier/bezier_chain/catmull_rom`，含 `input`/`horizontal_range`/`nodes`（键值对与数组两种写法，CODEC 用 either 兼容）。curve 会被注册成 `variable.<curvename>`（ParticlePreset.java:97-108）。
- **事件节点**（`events` 段）：`sequence`、`weight`、`randomize`、`particle_effect`、`sound_effect`、`expression`、`log`（PSGameClient.java:225-231；`particle_effect` 的 4 种 type：EMITTER / EMITTER_BOUND / PARTICLE / PARTICLE_WITH_VELOCITY，data/event/ParticleEffect.java:71-80）。未知节点名回退为 `log`（api/IEventNode.java:getCodec）。
- **Molang 函数**：30 个 `math.*` + `query.is_block`（data/molang/compiler/MolangParser.java:41-72），覆盖 abs/acos/asin/atan/atan2/ceil/clamp/cos/die_roll(_integer)/exp/floor/lerprotate/hermite_blend/lerp/ln/max/min/mod/pi/pow/random(_integer)/round/sin/sqrt/to_deg/to_rad/trunc。
- **query 变量**：14 个内置（MolangQueries.java:70-88），另有 `query.total_emitter_count/total_particle_count` 扩展。

未实现 / 与基岩差异：
- 无 `emitter_shape_custom`（全仓库 grep 无该字符串；官方文档中它与 point 并列）。**未确认**是否作者认为点形状即自定义。
- 名称与官方文档不完全一致：官方写作 `minecraft:emitter_shape_entity-aabb`、`minecraft:emitter_disc`，本实现注册为 `emitter_shape_entity_aabb`（PSGameClient.java:200），disc 注册为 `emitter_shape_disc`（201）。用官方文档原名写的 JSON 可能解析失败。
- Molang 表达式字符白名单很窄（`MolangParser.java:36`，仅 `[\w\s_+-/*%^&|<>=!?:.,()']`），高级 Molang（数组/loop/字符串函数/`->`）不支持；除上表 31 个函数外的函数在编译期按"变量"处理或报错（MolangParser.java:300-311）。
- 材质是"翻译"而非等价：`particles_alpha`/`particle_sheet_lit` 都映射到 Java 的 `PARTICLE_SHEET_LIT`，`particles_opaque` 映射到 `PARTICLE_SHEET_OPAQUE`，未知材质落到 `NO_RENDER`（ParticlePreset.java:47-66）；基岩原版贴图名（如 `minecraft:glitter_7`，见 particle_definitions/loading.particle.json:10）在 Java 端必须存在于粒子图集里，否则拿 missing 贴图。
- 官方 wiki 差异页（github.com/westernat/ParticleStorm/wiki）本次抓取因证书错误失败，**未确认**作者自述的差异清单。

## 3. 源码规模与包结构

`src/**/*.java`：**182 个文件 / 11544 行**（无 datagen、无 platform 分离层）。

| 包 | 文件数 | 行数 | 职责 |
|---|---|---|---|
| particle/ | 12 | 2037 | 引擎（MolangParticleEngine）、emitter、粒子实例、preset、RenderType 相关 |
| particle/attach/ | 5 | 332 | 附着到方块/实体的 emitter 与自动清理 |
| data/component/ | 21 | 2555 | 全部基岩组件 Codec + 运行逻辑 |
| data/molang/** | 61 | 3024 | 表达式词法/语法/求值、函数库（37 个函数类）、VariableTable |
| data/curve/ | 6 | 266 | 曲线 |
| data/event/ | 7 | 310 | 事件节点 |
| data/description/ | 4 | 120 | description / basic_render_parameters / 材质枚举 |
| data/（顶层） | 3 | 149 | DefinedParticleEffect（总 Codec）、MathHelper |
| api/ | 21 | 748 | 组件/事件/Molang 实例接口 + 各 Register*Event |
| api/geckolib/ | 8 | 551 | GeckoLib 对接辅助、示例方块/实体 |
| mixed/ | 8 | 112 | `IPS*` 混入接口 |
| mixin/ + mixin/integration/geckolib/ | 8 + 9 | 585 | 原版与 GeckoLib 注入 |
| network/ | 5 | 233 | 4 个包 |
| 根（ParticleStorm/PSGameClient/PSClientConfigs） | 4 | 522 | 入口、客户端事件、配置 |

最大文件 Top 10：MolangParticleInstance 581、EmitterShape 497、ParticleEmitter 460、MolangParser 425、MolangParticleEngine 372、ParticleAppearanceBillboard 302、PSGameClient 245、GeckoLibHelper 217、ParticleAppearanceTinting 209、EmitterLifetime 206（行）。

## 4. 启动与加载链

1. 资源定位：`FileToIdConverter.json("particle_definitions")`（MolangParticleEngine.java:64），即任意命名空间 `assets/<ns>/particle_definitions/*.json`。
2. 监听器注册：`RegisterClientReloadListenersEvent`（PSGameClient.java:170-175）里注册组件、事件节点、材质、emitter 类型，再 `event.registerReloadListener(MolangParticleEngine.INSTANCE)`。
3. 解析：`MolangParticleEngine.reload`（337-371）后台线程 `listMatchingResources` → 逐文件读 JSON 取顶层 `particle_effect` 字段 → `DefinedParticleEffect.CODEC.parse(JsonOps.INSTANCE, ...)`（344）→ 主线程为每个 effect 建 `ParticlePreset`（粒子侧，含表达式编译）与 `EmitterPreset`（发射器侧）。
4. **数据驱动方式：DFU Codec（RecordCodecBuilder + dispatchedMap），不是手写解析器**。组件是 `Codec.dispatchedMap(ResourceLocation.CODEC, IComponent.COMPONENTS::get)`（data/DefinedParticleEffect.java:22），事件是 `Codec.unboundedMap(String, IEventNode.CODEC)`（23）。好处：JSON 里 `minecraft:xxx` 名与代码解耦、第三方可注册新组件。
5. 贴图绑定：`MinecraftMixin.onResourceLoadFinished` → `particlestorm$bindSprites()`（mixin/ParticleEngineMixin.java）按 `id2Effect` 顺序把每个定义的 texture 填进 `ExtendMutableSpriteSet`，并把下标写回 `DescriptionParameters.bindTexture(index)`；粒子构造时 `setSprite(sprites.get(index))`（MolangParticleInstance.java:74）。

## 5. Molang 引擎

- **完全自研 parser**（MolangParser，425 行，源码同形于 McHorse 的 McLib，见第 11 节）。流程：`decomposeExpression`（正则白名单校验 + 去空白 + 小写化 + 括号配平，MolangParser.java:135-157）→ `compileSymbols`（手写分词，最长匹配运算符、逗号切参数，181-253）→ `parseSymbols` → 三元 `compileTernary` / 运算 `compileCalculation` / 函数 `compileFunction`（314-409）。支持 `return`、`;` 多语句（CompoundValue）、变量赋值（`variable.x=1`）、`!`、一元负号。
- **变量表**：`VariableTable`（Hashtable + parent 链，data/molang/VariableTable.java）。preset 级默认变量 `variable.particle_age/lifetime/particle_random_1..4`（ParticlePreset.java:129-138）；粒子级 `ParticleVariableTable` 做三级查找：粒子 preset 表 → 其父表 → emitter 表（ParticleVariableTable.java:15-26），所以 emitter 的 `creation_expression` 变量可被粒子读到。
- **query 扩展**：`MolangQueries` 静态注册 14 个 query 并支持 `q.`→`query` 别名（MolangQueries.java:63-88）；注册在 `RegisterMolangQueriesEvent` 时进行，之后 `FROZEN_QUERIES` 冻结，二次注册抛异常（MolangQueries.java:38-46,89-90）。`query.*` 走 `FROZEN_QUERIES.getOrDefault`（未知 query 返回常量 0，不报错）。
- **性能考量**：所有表达式在 reload 期一次性编译成 MathValue 树（ParticlePreset.java:109-114、EmitterPreset.java:70-72，`MolangExp.compile` 幂等，MolangExp.java:46-55），运行期只做树求值；curve 首次求值后缓存 SplineCurve（ParticleCurve.java:56-76）；常量标记 `markImmutable`。缺点是**每个 preset 独立编译、无共享 AST 缓存**，且求值是逐粒子逐帧的虚调用链。

## 6. 渲染实现

- 粒子类：`MolangParticleInstance extends TextureSheetParticle`（MolangParticleInstance.java:30），复用原版粒子物理/光照，但 UV、朝向、加速度全部由组件驱动。
- 批渲染：`MolangParticleEngine.renderParticles`（185-229）按 `ParticleRenderType` 分组（`groupedParticles`），对每组 `type.begin(...)` 开一个 QUADS buffer，逐粒子 `isVisible`+`render`，最后 `BufferUploader.drawWithShader`。注入点：`ParticleEngineMixin.renderMolang` 挂在 `ParticleEngine.render` 的 `RenderSystem.depthMask(Z)` 调用处（mixin/ParticleEngineMixin.java）。
- RenderType/材质：新增两个自定义类型 `PARTICLE_ADD`、`PARTICLE_BLEND`（PSGameClient.java:45-74），并注册自定义 shader `particle_no_discard`（PSGameClient.java:88-90；assets/particlestorm/shaders/core/particle_no_discard.{json,fsh}）；未装 Iris 且 renderType 为半透明时替换原版粒子 shader（MolangParticleEngine.java:203-205），解决原版 shader 的 alpha 裁剪问题。
- 无自定义 mesh/VertexFormat，沿用 `DefaultVertexFormat.PARTICLE`（QUADS）。
- **FaceCameraMode**（particle/FaceCameraMode.java）：实现 `SingleQuadParticle.FacingCameraMode`，12 种模式完整覆盖基岩的 `rotate_xyz/rotate_y/lookat_xyz/lookat_y/direction_x/y/z/lookat_direction/emitter_transform_xy|xz|yz`（DO_NOTHING 为兜底）。
- **ExtendMutableSpriteSet**（particle/ExtendMutableSpriteSet.java）：继承 `ParticleEngine.MutableSpriteSet`，突破 `sprites` 字段的 protected 可见性（靠 AT），提供 `addSprite/clear/get(index)/bindMissing`，使"每个粒子定义一张图集贴图 + 按下标取"成为可能。
- UV 归一化：`IPSTextureAtlasSprite`（mixin/TextureAtlasSpriteMixin.java）缓存 `1/originX`、`1/originY`，粒子构造时取用（MolangParticleInstance.java:75-79）以换算基岩的 texturewidth/textureheight。
- 兼容性分支：Sodium 加载时走手写顶点顺序（MolangParticleInstance.java:453-468）；`ParticleStorm.SODIUM_LOADED/IRIS_LOADED/GECKOLIB_LOADED` 在 ParticleStorm.java:44-46 用 `LoadingModList` 探测。

## 7. 网络与同步

仅 4 个 payload（ParticleStorm.java:64-71，`EmitterRemoval/Synchronize` 双向，`Creation/Attach` S2C）：

| 包 | 方向 | 内容 |
|---|---|---|
| EmitterCreationPacketS2C | S2C | particleId + MolangExp 字符串 + 坐标 + 可选 attach entityId（/particlestorm add 用，MolangParticleCommand） |
| EmitterAttachPacketS2C | S2C | 把已有 emitter 绑到实体 |
| EmitterRemovalPacket | 双向 | emitter id |
| EmitterSynchronizePacket | 双向 | id + 完整 NBT（`ParticleEmitter.serialize()`，含组件状态/随机数等） |

服务端把 emitter NBT 存到玩家 `persistentData` 的 `particlestorm:emitters`，玩家登录时逐个回放（ParticleStorm.java:77-87）。**粒子本体、贴图、表达式求值完全在客户端**，无需同步；同步的只是"发射器存在性 + 绑定关系 + 参数"。

## 8. 扩展 API（api/ 包）

| 事件 | 时机/总线 | 用法 |
|---|---|---|
| `RegisterCustomComponentEvent` | mod bus，reload 时（PSGameClient.java:221） | `register(id, Codec<? extends IComponent>)`，自定义基岩组件；实现 `IEmitterComponent`/`IParticleComponent`（可选 `order()` 控制初始化顺序，api/IComponent.java:order 注释：<0 = 早期初始化且不更新） |
| `RegisterCustomEventNodeEvent` | mod bus（PSGameClient.java:233） | `register(name, Codec<? extends IEventNode>)`，实现 `execute(MolangInstance)` |
| `RegisterCustomParticleTypeEvent` | 由 ParticleEngineMixin.registerProviders 触发 | `register(type, Provider)` / `registerWithSprites`，把自定义 `ParticleType` 与粒子工厂绑定（`ExtendMutableSpriteSet` 一并注入，api/RegisterCustomParticleTypeEvent.java:33-39） |
| `RegisterCustomMaterialEvent` | 首次序列化材质时惰性触发（data/description/DescriptionMaterial.java:33-40） | `register("name")` 增加材质名 |
| `RegisterCustomEmitterTypeEvent` | reload 时（PSGameClient.java:173, api/RegisterCustomEmitterTypeEvent.java:26-35） | `register(type, (level,tag)->emitter, (parent,effect)->emitter)`，自定义 emitter 子类与 NBT 反序列化 |
| `RegisterMolangQueriesEvent` | 类初始化时（MolangQueries.java:88） | `registerVariable("query.x", instance->float)`，必须在冻结前 |
| `AddDefaultVariableEvent(.Entity/.BlockEntity)` | **NeoForge 总线** | 给实体/方块实体变量表加 `variable.*`（EntityMixin.java、BlockEntityMixin.java） |
| `AttachEmitterToBlockEvent` | 首 tick 惰性 post（EmitterAttachHandler.postEvent） | 6 个重载把 block/blockstate → 粒子，`allowsVanilla`（是否继续跑原版 animateTick）、`ignoreSameBlock`、`ignoreRange`；由 `ClientLevelMixin` 在 `doAnimateTick` 处 WrapWithCondition 接管原版粒子 |
| `EmitterPresetLoadedEvent` / `ParticlePresetLoadedEvent` | 每个 preset 构造完 | 配合 `preset.setTicket(Class,Object)/getTicket` 存放自定义数据（ParticlePreset.java:44-50,119-127） |
| `MolangParticleLoadEvent.Pre/Post` | 资源重载前后 | Pre 在后台线程，Post 在主线程 |

其它可插拔点：`MolangParticleMobEffect`（api/MolangParticleMobEffect.java，MobEffect 携带 `MolangParticleOption`；`LivingEntityMixin.tickEffects` 拦截后转为 tracked emitter，同实体同粒子的重复添加会被去重，上限 `PSClientConfigs.maxTrackersPerEntity`，PSClientConfigs.java:31）、`MolangParticleEngine.addTrackedEmitter`、`/particlestorm add|remove` 命令（MolangParticleCommand.java）、`PSClientConfigs.ParticleConfig`（把粒子做成可配置开关，PSClientConfigs.java:88-152）。

## 9. GeckoLib 集成细节（与 BleedZone7 的接口）

`mixed/` 的 8 个 `IPS*` 接口全部由 GeckoLib 侧/原版侧 mixin 实现（`@Pseudo` + `remap = false`，硬编码 GeckoLib 类与内部字段）：

- `IPSGeoBone`（GeoBoneMixin）存 `Map<String, LocatorValue>`；数据来自 `BakedModelFactory$BuiltinMixin` 在 `constructBone` 返回时注入 `boneStructure.self().locators()`。
- `IPSAnimatableInstanceCache`（AnimatableInstanceCacheMixin）保存 `LocatorValue -> IntList(emitter id)` 与 `LocatorState`（由 locator 的 offset×0.0625、rotation 度→弧度算出）。
- `IPSAnimationController`（AnimationControllerMixin）缓存"有 locator 的骨骼"。
- `IPSParticleKeyframeData`（ParticleKeyframeDataMixin）把动画 JSON 关键帧的 `effect`/`script` 字段解析为 `ResourceLocation` 与 `MolangExp`。
- `IPSEntity`/`IPSBlockEntity`（EntityMixin/BlockEntityMixin）提供 per-instance 变量表（实体默认带 `variable.entity_scale`）。

接入链路：
1. `AnimationProcessorMixin.tickAnimation` 在调用 `controller.process(...)` 前把 `getRegisteredBones()` 灌入 controller（`particlestorm$setBonesWhichHasLocators`）。
2. `AnimationControllerMixin` 用 `@WrapWithCondition` 拦截 `processCurrentAnimation` 中 GeckoLib 输出"无 keyframe 处理"日志的那次 `Logger.log(Level,String)` 调用，改为 `GeckoLibHelper.processParticleEffect(animatable, controller, keyframeData)`（mixin/integration/geckolib/AnimationControllerMixin.java:processParticleEffect）。
3. `GeckoLibHelper.processParticleEffect`（api/geckolib/GeckoLibHelper.java:64-115）按 animatable 类型取变量表（Entity / `WithCurrentEntity`（GeoReplacedEntityRenderer 场景，`GeoReplacedEntityRendererMixin` 在 render 时 `setCurrentEntity`）/ BlockEntity），遍历有 locator 的骨骼，按关键帧的 locator 名找 `LocatorValue`，为每个 locator 建 `ParticleEmitter`（关键帧 `script` 作为 emitter 表达式）、`attachEntity/attachBlock`，id 存入 instanceCache；动画状态进入 `TRANSITIONING` 时（`resetEventKeyFrames` HEAD）清掉旧 emitter，避免残留。
4. 骨骼→局部空间矩阵：`GeoModelMixin.handleAnimations` TAIL 对所有注册骨骼调用 `GeckoLibHelper.transformLocator`（GeckoLibHelper.java:150-170），矩阵由 `RegisterLocatorPreTransformerEvent` 的 `Transformer` 提供（默认实现把骨骼链 pivot/rot/scale 累积；实体还包括身体/头部朝向、死亡旋转、床朝向、倒置、原版 scale，见 RegisterLocatorPreTransformerEvent.java:66-131），最后 `emitter.setLocalSpace(matrix, true)` 配合 `emitter_local_space` 让粒子跟随骨骼。
5. 额外：`MolangQueriesMixin` 把 `query.total_emitter_count/total_particle_count` 注入 GeckoLib 自己的 Molang（GeckoLib 动画脚本也能用）。

对接方式总结（给 BleedZone7 这类"替换原版实体渲染 + GeckoLib 动画"的 mod）：模型 `.geo.json` 里给骨骼加 locator，动画里放 particle keyframe（effect=粒子 id，script=Molang 表达式）即可，无需写 Java；需要特殊变换（坐骑/悬浮/旋转基座）时注册 `RegisterLocatorPreTransformerEvent`。注意 `ParticleStorm.DEBUG` 才注册示例 `TestBlock`/`ReplacedCreeperRenderer`（ParticleStorm.java:47,89-93、PSGameClient.java:93-97），示例可读 `api/geckolib/`。

## 10. 值得学的 5 条做法 + 自研的坑

**值得学**
1. **"组件名 → Codec"的 dispatchedMap + 全局注册表**（DefinedParticleEffect.java:22、api/IComponent.java）：JSON 用 `minecraft:`/自定义命名空间，代码零改动扩展组件；`HashBiMap` 还能防重复注册。
2. **表达式编译前置**：reload 期把所有 MolangExp/curve 编译成求值树并缓存（ParticlePreset.java:109-114），运行期零词法解析；curve 首次求值再缓存 SplineCurve。
3. **变量表 parent 链**（VariableTable/ParticleVariableTable）：emitter 变量被粒子继承、query 只读 + variable 可写分离，语义清晰且实现极简（两个 Hashtable）。
4. **用 `@WrapWithCondition` 精确改写第三方 mod 的日志调用点**接入关键帧（AnimationControllerMixin），不改 GeckoLib 源码，也不侵入用户的动画代码。
5. **客户端模拟 + 最小同步**：粒子/贴图/求值全在客户端，只同步 emitter 的存在与绑定（network/），并配 FPS 阈值与距离衰减自动清理（EmitterAttachHandler.java:ableToAddEmitter/isFarAwayFromCamera、PSClientConfigs）。

**坑**
1. 每 tick 每 emitter/每粒子做树求值 + 多趟 `removeIf`，粒子量大时是主线程热点；批量渲染按 RenderType 分组缓解（MolangParticleEngine.java:185-229），但建议自研时引入表达式/变量的 JIT 或缓存常见表达式。
2. 大量 AT 与注入原版内部（accesstransformer.cfg 10 条：`MutableSpriteSet.sprites`、`Particle.MAXIMUM_COLLISION_VELOCITY_SQUARED`、`ParticleEngine.particles`、`Frustum.cubeInFrustum`、`Minecraft.fps` 等），MC 升级必然返工；`renderMolang` 甚至以 `depthMask(Z)` 调用为注入锚点。
3. GeckoLib 集成全部依赖 `@Pseudo` + 硬编码方法描述符/局部变量名（如 `@Local(name="keyframeData")`、`processCurrentAnimation` 内的 log 序号 `ordinal = 1`），GeckoLib 版本一变就失效。
4. 与渲染优化 mod 的不确定性：Sodium/Iris 需运行时探测并走不同代码路径（MolangParticleInstance.java:453、MolangParticleEngine.java:203）。
5. 材质/贴图映射是近似的（第 2 节），移植基岩资源包时要逐一核对，否则会静默落到 NO_RENDER 或 missing 贴图。

## 11. 反编译/源码可用性备注

- 本地为**原始源码**（含 javadoc 与中文注释，例如 ParticleEmitter.java:299 的"以附着实体/方块位置为基准…"），不是反编译产物。
- 源码与资源完整：182 个 java 文件 + `assets/particlestorm/{particle_definitions(3),shaders/core,textures,lang,geo,animations,blockstates}`、`META-INF/{neoforge.mods.toml,accesstransformer.cfg}`、`particlestorm.mixins.json`（client 段 17 个 mixin）。
- 两个小缺口：build.gradle:15 引用的 `src/generated/resources` 目录不存在（无 datagen 源码，不影响构建）；`.bbmodel` 被显式排除（build.gradle:18）。
- 许可证注意：`src/main/java/org/mesdag/particlestorm/data/molang/compiler/mclib` **不是 Java 源文件**，而是 2018 年 McHorse 的 MIT 许可证全文（1093 字节）；MolangParser/Operator 等类的方法名与结构（decomposeExpression/compileSymbols/parseSymbols/compileValue/compileCalculation）与 McLib 的 Molang 编译器高度一致，但包内文件头**没有**任何 MIT 归属声明。若要在 LGPL-3.0 项目里复用这部分，需自行补上 MIT 许可与归属（**未确认**上游是否有另行声明的许可）。
- 本地未能构建验证（无网络/未执行 gradle），wiki 差异页抓取失败（TLS 证书错误），相关条目已标 **未确认**。
