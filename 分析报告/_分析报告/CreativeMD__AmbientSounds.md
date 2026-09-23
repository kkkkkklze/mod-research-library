# AmbientSounds 源码分析（CreativeMD）

## 1. 基本信息

- Mod 名 AmbientSounds；mod_id `ambientsounds`；作者 CreativeMD；`mod_version=6.3.8`
- 目标环境：Minecraft `[1.21.1,1.22)`、NeoForge `[21.1,)`、Java 21（`src/main/resources/META-INF/neoforge.mods.toml`、`build.gradle:9`）
- 本检出是 ForgeMods 单仓库中的**单个模块**：`build.gradle` 里 `project.evaluationDependsOn(":CreativeCore")`、`implementation project(':CreativeCore')`，但检出中无 `settings.gradle`、无 CreativeCore 目录，`forge_version` 也未在本 `gradle.properties` 定义（应在父仓库/兄弟模块，未确认）
- Gradle 插件：`net.neoforged.gradle.userdev 7.0.+`（旧式 NeoGradle userdev）+ `com.modrinth.minotaur`；另有 `build.fabric.gradle`（`fabric-loom 1.6+` + modmenu）做 Fabric 变体，构建脚本里声明 `modProperties = ['displayTest="NONE"']`、`modMixins = ["ambientsounds.mixins.json"]`、`modSides = ["client"]`
- 许可证 LGPL-3.0-only；编译/运行依赖：NeoForge 21.1 + **CreativeCore `[2.13.37,)`（required，两侧）**——CreativeCore 是它的框架依赖（配置系统、DebugTextRenderer、SpecialSoundInstance、QuadBitSet 等）

## 2. 源码规模与包结构

38 个 `.java`，4446 行（`find src -name '*.java' | wc -l`、`-exec wc -l {} +`）。`src/main/resources` 仅有 `ambientsounds.mixins.json` 与 `META-INF/neoforge.mods.toml`（音频与 `assets/ambientsounds/<engine>/` 的 JSON 引擎数据不在本次检出，`engine.md` 是其语法文档）。

包（文件数）：`sound` 6、`condition` 5、`engine` 7、`environment` 3（+`feature` 2、`pocket` 4）、`mixin` 2、`entity` 1、`region` 1、`dimension` 1、`block` 2、`mod` 1、根 2。

最大文件：`sound/AmbientSound.java`（570+ 行）、`engine/AmbientEngine.java`（512 行）、`condition/AmbientCondition.java`、`environment/pocket/AirPocketScanner.java`、`condition/AmbientTime.java`、`entity/AmbientEntityCondition.java`、`engine/AmbientTickHandler.java`

## 3. 入口与注册

`AmbientSounds.java:29` `@Mod(value = AmbientSounds.MODID, dist = Dist.CLIENT)`，类 `implements team.creative.creativecore.client.ClientLoader`；构造函数里 `CreativeCore.loader().registerClient(this)`，真正的初始化在 `onInitializeClient()`（`:60`）：

```java
TICK_HANDLER = new AmbientTickHandler();
loader.registerClientTick(TICK_HANDLER::onTick);
loader.registerClientRenderGui(TICK_HANDLER::onRender);
loader.registerLoadLevel(TICK_HANDLER::loadLevel);
```

随后把 `SimplePreparableReloadListener` 挂到 `ReloadableResourceManager`：`prepare()` 里只调 `AmbientSounds.reloadAsync()`，`apply()` 空实现（`:72-84`），从而让资源重载异步触发引擎重载；注册 `/ambient-debug`、`/ambient-reload` 客户端命令；配置交给 `CreativeCoreClient.registerClientConfig(MODID)`。**无 DeferredRegister、无注册表、无网络包**（音效在运行时用 `SoundManager.getSoundEvent(location)` 解析 `sounds.json` 条目）。

## 4. 核心系统

**A. 数据驱动引擎加载**（`engine/AmbientEngine.java`）
- `loadAmbientEngine`（`:195`）先读 `ambientsounds:config.json` → `AmbientEngineConfig`（可用引擎列表+默认名），再 `attemptToLoadEngine`（`:68`）读 `ambientsounds/<name>/engine.json` 与 `dimensions`、`regions`、`sound_collections`、`sound_categories`、`blockgroups`、`features` 六个子目录
- 全部走 `loadMultiple`（`:159`）：`manager.listResourceStacks(path, p -> p.getNamespace().equals(MODID))` 取**同名文件在所有数据包中的堆叠**，首个作 base，其余按 `AmbientStackType`（overwrite 或 `applyStackType` 反射逐字段覆盖，`:148`）合并——即“数据包可覆盖单个字段”，`AmbientRegion extends AmbientCondition` 与各类配置类都用 `@SerializedName` 对回 JSON 名

**B. 条件表达式 + 音量合成**
- `condition/AmbientCondition.java` 用大量可空字段描述条件：`always/volume/night/day/time/biome-type/biomes/bad-biomes/raining/overall-raining/snowing/storming/underwater/relative-height/absolute-height/min|max-height-relative/light/block-light/sky-light/air/temperature/sky/features/bad-features/variants/regions/bad-regions/entity`
- `value(AmbientEnvironment)`（`:130`）是一条“逐项判定，不满足即 `return null`，满足则 `selection.mulCondition(x)` 叠乘”的流水线，最终产出 `AmbientSelection`
- `condition/AmbientVolume.java` 刻意分两个通道：`conditionVolume`（条件匹配程度，参与 mute 计算）与 `settingVolume`（用户设置），`volume()=settingVolume*conditionVolume`；`SILENT`/`MAX` 两个常量用匿名子类把乘法变成 no-op；`AmbientSelection` 通过 `subSelection` 链实现 region→sound 的递归叠乘（`AmbientSelectionMulti` 用于多类别）

**C. 播放状态机与双流交叉过渡**（`sound/AmbientSound.java`，继承 `AmbientCondition`）
- 字段：`stream1/stream2`、`aimedVolume/aimedPitch`、`cachedAimedConditionVolume|cachedAimedOutputVolume`、`currentConditionVolume|currentOutputVolume`、`transition/transitionTime`、`pauseTimer`、`currentPropertries`
- `fastTick`（`:160`）每 tick 用 `Math.min(fadeIn/fadeOut, 差值)` 线性逼近目标音量与音高；有 `length` 的声音在 `remaining()<=0` 时用 `stream2 = playTransition(getRandomFileExcept(...))` 做交叉淡入淡出（默认 60 tick），有 `pause` 的则走 `pauseTimer` 间歇
- `SoundStream implements TickableSoundInstance`，`isRelative()=true`、`getAttenuation()=NONE`、`getX/Y/Z=0`，`canStartSilent()=true`：作为无位置衰减的背景层
- `sound/AmbientSoundEngine.java:33 tick` 用一个 `Double2DoubleRBTreeMap(DoubleComparators.OPPOSITE_COMPARATOR)` 收集所有流按 `mutePriority` 的 mute 值，再逐流叠加（按优先级屏蔽低优先级的静音）——"水下压低一切、但高优先级音效不受影响"的实现

**D. 环境采样（快/慢两拍）**
- `engine/AmbientTickHandler.java:183-193`：`timer % environmentTickTime == 0` 时 `environment.analyzeSlow(...)`（含群系/地形扫描），`timer % soundTickTime == 0` 时 `analyzeFast(...)` + `dimension.manipulateEnviroment(...)` + `engine.tick(env)`
- `environment/AmbientEnvironment.java:53` `analyzeFast` 采样雨/雪/雷、绝对/相对高度（用 `terrain.averageHeight/maxHeight/minHeight`）、水下深度、太阳角（`night`、`dayTimeHour`）、实体
- `environment/pocket/AirPocketScanner.java` **继承 `Thread`**：以玩家为原点逐层扩散扫描方块，统计 `HashMapDouble<BlockState> foundCount`、方块光/天空光/天空可见度（`QuadBitSet sky`）、空气量，回调产出 `AirPocket`/`BlockDistribution`，是 `light/air/sky/features` 条件的来源

**E. 反射驱动的配置注册**（`AmbientTickHandler.initConfiguration`，`:51`）
- 每次引擎加载后用 `CreativeConfigRegistry.ROOT.removeField(MODID)` 清空，再 `registerFolder(MODID, ConfigSynchronization.CLIENT)` 重建 `general`/`dimensions`/`regions`/`categories` 四级目录；字段用 `ReflectionHelper.findField(AmbientRegion.class, "volumeSetting")` + `registerField(name, field, instance)` 动态挂载
- 类别配置递归自 `AmbientSoundCategory.children`；同时把 `AmbientEngine.fadeVolume/fadePitch/silentDimensions` 也暴露为配置项；`AmbientSoundsConfig.configured(Side)` 在引擎名变化时 `scheduleReload()`

**F. 随机起始点播放（mixin 扩展原版流）**
- `sound/AmbientSound.java:527 getAudioStream` 里，当 `currentPropertries.randomOffset && CONFIG.playSoundWithOffset` 时对新建的 `JOrbisAudioStream` 调用 `((OggAudioStreamExtended) stream).setPositionRandomly(ResourceUtils.length(...), id)`
- 该方法由 `mixin/OggAudioStreamMixin.java` 实现（`@Mixin(JOrbisAudioStream.class)`，`@Shadow` 出 `audioFormat/input/readPacket/readPage/readToBuffer`）：随机 `input.skipNBytes(length*3/4 内随机)` 后用 `readChunk` 重扫 Ogg page，捕获 IOException/IllegalStateException 重试 512 次以内，失败则调用方 `inputstream.reset()` 重新建流

## 5. 网络 / 数据驱动 / 配置 / datagen / Mixin

- 网络：无（纯客户端 mod）
- 数据驱动：**全部游戏内容**由数据包 JSON 驱动（见 4.A），`blockgroups/<name>.json` 是 `String[]` 方块列表
- 配置：交给 CreativeCore 的 `@CreativeConfig` + `ConfigHolderDynamic`（含 `SelectableConfig<String> engines`、`DecimalRange` 校验）
- datagen：无；兼容层仅 `mod/SereneSeasonsCompat`（提供 `env.temperature`）
- Mixin：`src/main/resources/ambientsounds.mixins.json`，`compatibilityLevel: JAVA_21`，`refmap: ambientsounds.mixins.refmap.json`，client 列表 = `OggAudioStreamMixin`、`SoundBufferLibraryAccessor`（`@Accessor getResourceManager` 从 `SoundBufferLibrary` 取 `ResourceProvider`，用于拿到 `Resource` 计算文件长度）

## 6. 值得学的具体做法

1. **`listResourceStacks` + 反射字段合并实现“数据包可局部覆盖”**：`AmbientEngine.loadMultiple`（`AmbientEngine.java:159`）与 `applyStackType`（`:148`）让每个 JSON 只需写要改的字段（适用：大型数据驱动内容包）。
2. **用 `Thread` 做地形扫描**：`AirPocketScanner extends Thread`，结果经 `Consumer<AirPocket>` 回传，主线程只在 tick 里读快照（适用：高频空间采样）。
3. **把数据驱动内容反射挂成配置项**：`AmbientTickHandler.initConfiguration`（`AmbientTickHandler.java:51-87`）按 `ReflectionHelper.findField` 批量生成配置树，新增 region/sound 无需改配置代码（适用：内容由 JSON 定义、又要逐项给玩家可调音量的场合）。
4. **双通道音量 + mute 优先级**：`AmbientVolume` 分离 `conditionVolume/settingVolume`，`AmbientSoundEngine.tick` 用反向比较器 TreeMap 合并 mute（适用：分层环境音、动态混音）。
5. **小 mixin + 接口扩展点替代 AT**：`SoundBufferLibraryAccessor`（`@Accessor`）与 `OggAudioStreamMixin implements OggAudioStreamExtended`，只用 2 个 client mixin 就做到“随机定位播放 Ogg”，且 `setPositionRandomly` 有失败回退（`inputstream.reset()`）。
6. **异步重载管线**：资源重载监听器只在 `prepare()` 里 `reloadAsync()`（`AmbientSounds.java:72-84`），引擎重建走 `CompletableFuture.runAsync(..., Util.backgroundExecutor())`，并用 `scheduleReload/waitForReload` 状态位避免与 tick 竞争。
