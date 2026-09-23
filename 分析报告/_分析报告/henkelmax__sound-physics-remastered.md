# Sound Physics Remastered 源码分析报告

## 1. 基本信息

- **Mod 名 / mod_id**：Sound Physics Remastered / `sound_physics_remastered`
- **作者**：henkelmax；上游链：Sound Physics（Sonic Ether）→ Sound Physics Fabric（vlad2305m）→ 本项目（`README.md`），包名仍保留 `com.sonicether.soundphysics`
- **目标版本与加载器**：`gradle.properties` — `minecraft_version=26.3-rc-2`、`mod_version=1.5.1+26.3`、`fabric_loader_version=0.19.3`、`java_version=25`；`settings.gradle` 当前**只 include `common` 与 `fabric`**（`neoforge`、`forge` 被注释掉，目录仍在）
- **Gradle 插件**：`com.gradleup.shadow`、`fabric-loom 1.17-SNAPSHOT`、`de.maxhenkel.cursegradle`、`minotaur`、`mod-update`；每个子工程再 `apply from: "https://raw.githubusercontent.com/henkelmax/mod-gradle-scripts/1.1.5/mod.gradle"`（因此仓库内**没有** `fabric.mod.json` / `mods.toml`，由远程脚本生成；`processResources` 里用 `expand` 填 `java_version`、`voicechat_api_version` 等）
- **许可证**：未确认（仓库根目录无 LICENSE 文件）
- **编译依赖**：`de.maxhenkel.voicechat:voicechat-api:2.6.0`（另 `runtimeOnly ...:fabric-stub` 占位）、`me.shedaniel.cloth:cloth-config-fabric`（`api`，可选 GUI）、`com.terraformersmc:modmenu`；**无任何硬前置**

## 2. 源码规模与包结构

`find -name '*.java'` = **47 个文件、4214 行**（含未纳入构建的 forge/neoforge；`common`+`fabric` = 3846 行）。

包（`common/src/main/java/com/sonicether/soundphysics/`）：`config`(+`config/blocksound`) 共 12 个、`mixin` 11 个、`world` 5 个、`utils` 4 个、根 4 个（`SoundPhysics`、`SoundPhysicsMod`、`ReflectedAudio`、`Loggers`）、`integration/voicechat` 2 个、`debug`、`profiling` 各 1 个；`fabric` 侧 3 个。

最大文件：`SoundPhysics.java`(703)、`fabric/.../ClothConfigIntegration.java`(286)、`config/blocksound/BlockSoundConfigBase.java`(206)、`config/SoundPhysicsConfig.java`(201)、`world/ClonedLevelChunk.java`(161)、`config/SoundTypes.java`(156)、`world/ClonedClientLevel.java`(132)、`utils/LevelAccessUtils.java`(132)、`integration/voicechat/SimpleVoiceChatPlugin.java`(121)。

## 3. 入口与注册

**无注册项**（纯客户端 mod，不加方块/物品/包）。入口是"抽象基类 + 平台子类"：

- `SoundPhysicsMod.java:15-58` 是抽象基类，持有 4 个静态配置对象 `CONFIG` / `REFLECTIVITY_CONFIG` / `OCCLUSION_CONFIG` / `SOUND_RATE_CONFIG`，`init()`、`initClient()`（后者含旧配置 `allowed_sounds.properties` → `sound_rates.properties` 的迁移），唯一的平台抽象方法是 `getConfigFolder()`
- `fabric/.../FabricSoundPhysicsMod.java` 实现 `ModInitializer` + `ClientModInitializer`，只重写 `getConfigFolder()` 返回 `FabricLoader.getInstance().getConfigDir()`
- 声学系统真正的初始化点在 mixin 里：`mixin/SoundSystemMixin.java:28` 注入 `SoundEngine.loadLibrary` 中 `Listener.reset()` 调用点 → `SoundPhysics.init()`（EFX 槽位必须在 OpenAL 上下文建立后创建）

## 4. 核心系统

**(1) OpenAL EFX 声学引擎** — `SoundPhysics.java`。`setupEFX()`（:85）检测 `ALC_EXT_EFX`、读 `ALC_MAX_AUXILIARY_SENDS`，创建 4 个 auxiliary effect slot + 4 个 `AL_EFFECT_EAXREVERB` + 1 个直达 lowpass filter + 4 个 send lowpass filter。核心计算 `evaluateEnvironment()`（:207）：遮挡用 `occlusionAccumulation` 累加，`directCutoff = exp(-occ * blockAbsorption*3)`，`directGain = pow(directCutoff, 0.1)`；混响用黄金角 `PHI=1.618` 球面螺旋采样 `environmentEvaluationRayCount`(默认 32) 条射线，每条最多 `environmentEvaluationRayBounces`(默认 4) 次反射，按 `totalRayDistance*0.12*reflectivity` 算延迟，用 4 个三角权重 `cross0..cross3` 分配到 4 个 reverb send。`setEnvironment()`（:625）把结果写成 `alFilterf(AL_LOWPASS_GAIN/GAINHF)` + `alSource3i(AL_AUXILIARY_SEND_FILTER, auxSlot, send#, filter)`，并按 `maxAuxSends` 分级降级。

**(2) 声音方向重定向** — `ReflectedAudio.java`。收集 `directDirection` 与 `airspaceDirections`（方向向量 + 累计路径长度），`evaluateSoundPosition()`（:65）按 `1/d²` 加权平均方向，输出 `normalize().scale(音源到听者距离).add(听者位置)`，再由 `setSoundPos()` 用 `AL_POSITION` 移动声源 —— 实现"声音沿走廊传来"的绕射感。门控在 `shouldEvaluateDirection()`：`soundDirectionEvaluation` / `redirectNonOccludedSounds` / `AudioChannel.isVoicechatSound`。

**(3) 跨线程关卡快照** — `utils/LevelAccessUtils.java` + `world/`。音频线程不能直接读 `ClientLevel`，于是在主线程 tick（`mixin/ClientLevelMixin.java:38` 注入 `ClientLevel.tick` 的 TAIL）把玩家周围 `levelCloneRange` 个区块克隆为 `ClonedClientLevel`/`ClonedLevelChunk`（`extends ChunkAccess`），塞进 `ClientLevel` 上用 mixin 注入的 `@Unique AtomicReference`（接口 `world/CachingClientLevel.java`）；读侧 `getClientLevelProxy()` 返回 `ClientLevelProxy`（`extends BlockGetter`）。过期条件 = `levelCloneMaxRetainTicks` 或 `levelCloneMaxRetainBlockDistance`；`unsafeLevelAccess=true` 时退回 `UnsafeClientLevel` 直连主线程对象。

**(4) 数据驱动的方块声学** — `config/blocksound/`。`BlockSoundConfigBase.java:63` 的 `getBlockDefinitionValue()` 四级回退：block id → block tag → `SoundType` → 默认值；配置 key 支持三种写法（`WOOD=1.0` / `\#minecraft\:logs=1.0` / `minecraft\:oak_log=1.0`），由 `BlockDefinition` 的三个子类 + `loadBlockDefinition()` 工厂解析，并用 `blockCache/blockTagCache/soundTypeCache` 三份惰性缓存加速。`ReflectivityConfig`、`OcclusionConfig` 皆继承它。

**(5) Simple Voice Chat 集成** — `integration/voicechat/SimpleVoiceChatPlugin.java`。SVC 使用**独立的 OpenAL context**，因此监听 `CreateOpenALContextEvent` 时用 `EXTThreadLocalContext.alcSetThreadContext()` 切过去再 `SoundPhysics.init()`（:81）；`OpenALSoundEvent` → `AudioChannel` 缓存 `UUID→通道`，500ms/1 格节流；`hearSelf` 时把本地语音作为 `auxOnly=true` 只吃混响。语音音量分类 `own_voice` 在 `VoicechatServerStartedEvent` 注册。

**(6) OpenAL 通道注入** — `mixin/SourceMixin.java` 注入 `com.mojang.blaze3d.audio.Channel`：`setSelfPosition` 存位置，`play` 时调 `SoundPhysics.onPlaySound(..., source)`；`@ModifyVariable` 把 `linearAttenuation` 除以 `attenuationFactor`，`RETURN` 时 `alSourcef(AL_REFERENCE_DISTANCE, attenuation/2)`。`mixin/LibraryMixin.java` 用 `@ModifyArgs` 在 `alcCreateContext` 的参数尾部追加 `ALC_MAX_AUXILIARY_SENDS=4`（关键：原版不申请这么多 aux send）。`mixin/SoundEventMixin.java` 用 `@ModifyConstant` 把 `SoundEvent.getRange` 的 `16F` 乘 `soundDistanceAllowance`。`mixin/SoundSystemMixin.java:38` 按 `soundUpdateInterval` 用 `(gameTime + sound.hashCode()) % interval` 周期重算移动音源。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络**：无。零自定义包、零网络注册，纯客户端本地计算（`attenuationFactor`/`soundDistanceAllowance` 的注释说明需服务端也装才生效，但本项目未实现任何同步通道）。
- **配置**：全部走 maxhenkel 的 `configbuilder`（`ConfigBuilder.builder(SoundPhysicsConfig::new)` 与 `CommentedPropertyConfig`），集中目录 `config/sound_physics_remastered/` 下 4 个 properties：`soundphysics.properties`（约 40 项 `ConfigEntry`，含 `maxOcclusionRays`、`levelCloneRange`、`renderSoundBounces` 等）、`reflectivity.properties`、`occlusion.properties`、`sound_rates.properties`（每音效限流）。`SoundTypes.java:17-123` 手写 `SoundType→名字` 映射表（注释说明"因 remap 不能靠枚举名"）供配置 key 用。GUI 在 `fabric/.../ClothConfigIntegration.java`(286 行) + `ModMenuIntegration`。
- **datagen**：无。

## 6. Mixin

配置：`fabric/src/main/resources/sound_physics_remastered.mixins.json`（`package com.sonicether.soundphysics.mixin`，`mixins`: `EntityMixin`/`SoundEventMixin`；`client`: `SoundSystemMixin`/`SourceMixin`/`DebugRendererMixin`/`LibraryMixin`/`ChannelAccessor`/`ClientLevelMixin`/`LocalPlayerMixin`/`MinecraftMixin`/`ClientPacketListenerMixin`；`compatibilityLevel: JAVA_17` 已陈旧）。全部集中在 `common/.../mixin/`。

代表性 hook：
- `SoundSystemMixin` → `SoundEngine.loadLibrary`(INVOKE `Listener.reset`)、`SoundEngine.play`(FIELD `instanceBySource` + `locals=CAPTURE_FAILHARD`)、`SoundEngine.tickInGameSound`
- `SourceMixin` → `Channel.setSelfPosition`(HEAD)、`Channel.play`(HEAD)、`Channel.linearAttenuation`(`@ModifyVariable` argsOnly + RETURN)
- `LibraryMixin` → `Library.init` 内 `ALC10.alcCreateContext`(`@ModifyArgs`)
- `ChannelAccessor` → `Channel.getSource()`(`@Accessor`)
- `ClientLevelMixin` → `ClientLevel.tick`(TAIL)，并 implements `CachingClientLevel` 注入 `AtomicReference` 字段
- `ClientPacketListenerMixin` → `ClientPacketListener.handleLogin`(TAIL)；`MinecraftMixin` → `Minecraft.setLevel`(HEAD)、`Minecraft.disconnect`(HEAD)
- `LocalPlayerMixin` → `LocalPlayer.playSound`(HEAD, cancellable，改走 `playLocalSound`)；`EntityMixin` → `Entity.playSound(SoundEvent,FF)` 的 `Level.playSound` 调用(`@ModifyArg` index=2，Y 偏移)；`SoundEventMixin` → `SoundEvent.getRange`(`@ModifyConstant` 16F)

## 7. 值得学的 5 条具体做法

1. **`@ModifyArgs` 修改 OpenAL context 创建参数**：`mixin/LibraryMixin.java:23` 往 `alcCreateContext` 的属性列表里插 `ALC_MAX_AUXILIARY_SENDS=4`，绕开原版不申请多路 EFX send 的限制。适用：任何需要额外 OpenAL 能力的音频 mod。
2. **把不可跨线程的世界访问换成"主线程克隆的只读快照"**：`LevelAccessUtils` + `ClonedClientLevel`/`ClonedLevelChunk`，用 `AtomicReference` 发布、按 tick/距离失效，并保留 `unsafeLevelAccess` 逃生开关。适用：音频/渲染/异步计算线程读方块。
3. **抽象模组基类 + 子类只实现一个方法**：`SoundPhysicsMod.java` 用 `getConfigFolder()` 隔离平台，静态配置四处共用。适用：多加载器共享源码。
4. **三角权重分配 4 段混响尾巴**：`SoundPhysics.java:378-386` 用 `cross0..cross3 = 1-|delay-k|` 把同一条反射路径的能量按延迟摊到 4 个 reverb slot，避免额外的延迟线。适用：用 EFX 做简易多段混响。
5. **跨类隐式参数传递**：`SoundSystemMixin` 在 `SoundEngine.play` 里 `locals=CAPTURE_FAILHARD` 抓 `soundSource`/`identifier` 存静态字段，`SourceMixin` 在 `Channel.play` 时取用（`SoundPhysics.setLastSoundCategoryAndName`）。适用：hook 点拿不到上下文、但下游 hook 又能拿到的场景。
6. **第三方 API 用 shadow + 可选运行时**：`voicechat-api` 以 `implementation` + `runtimeOnly ...:fabric-stub` + shadow 打包，做到"SVC 未安装也不崩"。适用：可选集成。
7. **自建 `TaskProfiler`**（`profiling/TaskProfiler.java`）：100 长环形队列 + `WeakReference` handle + 每 100 次任务打印 min/avg/max。适用：给高频隐藏开销做量化。

## 8. 公开 API

非库 mod。对外只暴露 `integration/voicechat` 的 SVC 插件入口（`de.maxhenkel.voicechat.api.VoicechatPlugin` 实现 + `getPluginId()` 返回 modid），无自有 API 包。
