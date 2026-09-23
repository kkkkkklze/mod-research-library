# CreativeMD/EnhancedVisuals 源码分析报告

## 1. 基本信息

- Mod 名 / mod_id：EnhancedVisuals / `enhancedvisuals`；作者 CreativeMD, Sonicjumper；版本 1.8.31；许可证 **LGPL-3.0-only**（`src/main/resources/META-INF/neoforge.mods.toml`）
- 目标：`neoforge [21.1,)`、`minecraft [1.21.1,1.22)`，即 MC 1.21.1 + NeoForge（`build.gradle` 用 `net.neoforged.gradle.userdev 7.0.+`，Java 21）
- 另有 `build.fabric.gradle` 与 `enhancedvisuals.fabric.mixins.json`（Fabric 变体，本报告未展开）
- 硬依赖：**CreativeCore `[2.13.38,)`**（required, BOTH）。`build.gradle` 里 `project.evaluationDependsOn(":CreativeCore")`、`dependencies { implementation project(':CreativeCore') }` —— 设计上要求与 CreativeCore 同工作区复合构建，**单仓库无法直接构建**（本地无 CreativeCore 目录）
- **可见性 sourceSet**：`build.gradle` 创建 `api` sourceSet 指向 `src/api/java`，并让 `main` 的 compile/runtime classpath 追加其输出。该目录 9 个文件全是**软依赖 mod 的 API 桩类**：`toughasnails/api/{temperature,thirst}`、`com/momosoftworks/coldsweat/api/util/Temperature`、`com/stereowalker/survive/api/needs/{PlayerNeeds,Stamina,Temperature,Water}` —— 编译期直接 import 这些类，运行期靠 `isModLoaded` 分支保护

## 2. 源码规模与包结构（实测）

- `find . -name '*.java' | wc -l` = **78**，总 **4196 行**（其中 `src/api/java` 9 个）
- 包根 `team.creative.enhancedvisuals`：`api`(4) + `api/type`(9) + `api/event`(4)；`client`(2) + `client/render`(4) + `client/sound`(3)；`common/handler`(12)、`common/packet`(3)、`common/addon/{toughasnails,survive,coldsweat}`(3/3/2)、`common/death`(1)、`common/event`(1)、`common/visual`(1)；`mixin`(11)；`server`(1) + `server/command`(2)
- 最大文件：`common/handler/DamageHandler.java` 247、`client/VisualManager.java` 192、`client/render/EVRenderer.java` 180、`api/type/VisualTypeTexture.java` 155、`api` 桩 `toughasnails/.../TemperatureHelper.java` 118、`common/handler/ExplosionHandler.java` 112、`api/type/VisualType.java` 110

## 3. 入口与注册

`@Mod(value = EnhancedVisuals.MODID) public class EnhancedVisuals implements CommonLoader, ClientLoader`（CreativeCore 的加载器抽象，`EnhancedVisuals.java`）。构造器只做 `CreativeCore.loader().register(this); loader.registerClient(this);`，逻辑全在 `onInitialize()`：

```java
NETWORK.registerType(ExplosionPacket.class, ExplosionPacket::new);   // 3 个包
VisualHandlers.init();  MESSAGES = new DeathMessages();
if (loader.isModLoaded("survive")) SurviveAddon.load();   // 同样 tan / cold_sweat
ConfigHolderDynamic root = CreativeConfigRegistry.ROOT.registerFolder(MODID);
root.registerValue("general", CONFIG = new EnhancedVisualsConfig(), ConfigSynchronization.CLIENT, false);
ConfigHolderDynamic handlers = root.registerFolder("handlers", ConfigSynchronization.CLIENT);
for (Entry<ResourceLocation, VisualHandler> e : VisualRegistry.entrySet()) handlers.registerValue(e.getKey().getPath(), e.getValue());
```

`onInitializeClient()` 里注册客户端钩子：`registerClientStarted(EVClient::init)`、`registerClientTick(...)`、`registerClientRenderGui(EVRenderer::render)`、`CreativeCoreClient.registerClientConfig(MODID)`。**无 DeferredRegister**（不注册任何方块/物品）。

## 4. 核心系统

1. **Handler 体系（"处理器即配置对象"）**：`api/VisualHandler.java` 是基类，字段 `@CreativeConfig boolean enabled`、`@CreativeConfig @DecimalRange(max=1,min=0) float opacity`，并直接把配置值当渲染系数（`getOpacity() = handler.opacity * visual.opacity * type.opacity`）。`common/handler/VisualHandlers.java` 用 `VisualRegistry.registerHandler(ResourceLocation, handler)` 注册 11 个：explosion/potion/sand/splash/damage/slender/saturation/heartbeat/underwater/rain/health；`VisualHandlers.DAMAGE` 这类字段同时是单例与配置树节点（配置路径 `enhancedvisuals:handlers/damage`）
2. **视觉数据模型**：`api/Visual.java` = type + handler + `Curve animation` + variant；`tick()` 用 `opacity = (float) animation.valueAt(tick++)` 生成淡入淡出，`endless` 表示不消失；`api/VisualCategory.java` 是枚举 `{overlay, particle, shader}` 并在枚举常量内覆写抽象方法 `isAffectedByWater()`。`api/type/VisualType.java` 抽象基类在构造器里 `types.add(this)` **自注册**；9 个子类：Texture / AnimatedTexture / Overlay / Particle / ParticleColored / Shader / Blur / Saturation
3. **视觉集合管理**：`client/VisualManager.java` 用 CreativeCore 的 `HashMapList<VisualCategory, Visual>` 按类别存放，`onTick` 在 `synchronized (visuals)` 内 tick 每个 Visual（**玩家眼睛在水里时对受影响视觉多 tick `waterSubstractFactor` 次**以加速消散），并提供 `addParticlesFadeOut`（随机数量/位置/尺寸/旋转的粒子组）、`generateOffset`（`1 - rand^2` 分布让粒子更靠近屏幕中心）、`playTicking`（Curve 驱动的淡出音效）
4. **渲染管线**：`client/render/EVRenderer.java` 自建着色器 `enhancedvisuals:position_tex_col_smooth`（由 `mixin/GameRendererMixin.java` 在 `reloadShaders` 里把 `ShaderInstance` 塞进原版 `shaders` 列表）；渲染时重设正交投影 `new Matrix4f().setOrtho(0, screenWidth, screenHeight, 0, 1000, 21000)` + modelView 平移 `-11000F`，按 **shader → overlay → particle** 顺序分两批绘制；`DeathScreen` 时不绘制而改画随机死亡留言；`CONFIG.fixBlurShader` 时用 `blendFuncSeparate(ZERO, ONE_MINUS_SRC_COLOR, ONE, ZERO)` 画一层黑修正原版模糊着色
5. **资源包驱动的贴图**：`api/type/VisualTypeTexture.loadResources` 按 `visuals/<category>/<name>/<name><i>.png` **连续编号探测**（`TextureCache.parse` 返回 null 即停），用 `ImageIO` 读首图拿 `dimension/ratio`；`animationSpeed > 0` 时用 `System.nanoTime()/3000000/animationSpeed` 做帧动画；`getVariantAmount() = resources.length` → Visual 随机选变体。即**资源包可以往里加图片**来扩展效果
6. **音频**：`client/sound/PositionedSound.java` / `TickedSound.java`（曲线淡出）+ `SoundMuteHandler` 通过 `SoundEngineAccessor`/`SoundManagerAccessor` 直接改原版 `SoundEngine` 通道音量实现"心跳时的环境音渐隐"

## 5. 网络 / 数据驱动 / 配置

- **网络**：CreativeCore `CreativeNetwork(1, LOGGER, ResourceLocation.tryBuild(MODID, "main"))` + `CreativePacket` 子类三件套 `common/packet/{DamagePacket,ExplosionPacket,PotionPacket}.java`。`DamagePacket` 序列化 `Holder<DamageType>` + `sourceCauseId/sourceDirectId` + `@CanBeNull Vec3 sourcePosition`，客户端 `getSource(Level)` 重建 `DamageSource` 后调 `VisualHandlers.DAMAGE.playerDamaged(...)`；服务端在 `common/event/EVEvents.java` 的 `damage`/`explosion`/`impact` 里 `NETWORK.sendToClient(packet, ServerPlayer)`。**服务端只发"发生了什么"，视觉表现全在客户端计算**
- **配置**：CreativeCore 配置系统，`@CreativeConfig` 注解字段 + `ICreativeConfig.configured(Side)`；`ConfigSynchronization.CLIENT` 表示同步到客户端；13 个 handler 各自一棵配置子树自动生成 GUI；`EnhancedVisualsConfig` 仅 4 个开关（doEffectsInCreative / waterSubstractFactor / enableDamageDebug / fixBlurShader）
- **数据驱动**：仅"资源包追加贴图"；**无 datagen**

## 6. Mixin

`src/main/resources/enhancedvisuals.mixins.json`（`compatibilityLevel JAVA_17`，带 `refmap`）：`mixins` 5 个 + `client` 5 个。
- Accessor 类：`EntityAccessor`（`wasEyeInWater`）、`ExplosionAccessor`（x/y/z/radius/source，供 `EVEvents.explosion` 取爆炸参数）、`PostChainAccessor`、`SoundEngineAccessor`、`SoundManagerAccessor`
- 逻辑注入：`ProjectileMixin`（`Projectile#onHit` HEAD → `EVENTS.impact`，用于投掷药水）、`ClientPacketListenerMixin`（`handleRespawn` TAIL → `EVENTS.respawn` → `VisualManager.clearEverything()`）、`GameRendererMixin`（`reloadShaders` 注入自定义 shader + `processBlurEffect` 修正）、`ExplosionMixin`、`PlayerMixin`

## 7. 值得学的具体做法

1. **`src/api/java` 独立 sourceSet 放软依赖 mod 的 API 桩**（`build.gradle`）——编译期可强类型调用 ToughAsNails/ColdSweat/Survive，运行期用 `isModLoaded` 保护，比纯反射干净
2. **"Handler 即配置对象"**：视觉参数直接写成 `@CreativeConfig` 字段，配置树按 handler 名自动挂载并自动生成界面（`VisualHandlers.init()` + `EnhancedVisuals.onInitialize()`）
3. **视觉 = Curve 驱动的不透明度动画 + 类型类别集合**：`Visual.tick()` 只改 alpha，渲染器只读，动画表现与渲染解耦（`api/Visual.java`、`client/VisualManager.java`）
4. **资源包追加贴图实现效果扩展**：`visuals/<cat>/<name>/<name><i>.png` 连续编号探测（`api/type/VisualTypeTexture.java`）
5. **Accessor mixin 暴露原版私有状态**（`wasEyeInWater`、爆炸坐标/半径、SoundEngine 通道）而不改逻辑，随后给 SoundMuteHandler 做真实音量渐变
6. **在 `GameRenderer#reloadShaders` 注入自己的 `ShaderInstance`** 是 1.21.1 上加载自定义后处理/着色器的轻量做法，同时提供了自定义 shader 文件加载的机会

## 8. 对外 API

存在 `team.creative.enhancedvisuals.api` 包（`Visual`、`VisualHandler`、`VisualCategory`、`api/type/*`、`api/event/*`）以及公开的 `VisualRegistry.registerHandler(ResourceLocation, VisualHandler)` 与 `VisualManager.add*/addParticlesFadeOut`，理论上外部 mod 可注册自己的 handler（`TANAddon`/`SurviveAddon`/`ColdSweatAddon` 就是同仓库内的范例，只是用 `isModLoaded` 在内部加载）。但**未见公开的扩展点接口/fabric.mod.json 式入口，是否被作为 API 对外承诺未确认**；它本身不是前置库，硬依赖方向是 EnhancedVisuals → CreativeCore。
