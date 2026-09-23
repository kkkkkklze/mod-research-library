# CircuitLord/AdventureRedefined 源码分析报告

> 注意：仓库名为 `AdventureRedefined`，但仓库内实际是 **Reactive Music**（`gradle.properties`：`mod.id=reactivemusic`、`mod.name=Reactive Music`、`mod.group=circuitlord.reactivemusic`、`mod.version=1.3.5`；README 标题 "Reactive Music"）。

## 1. 基本信息

- Mod 名 / id：Reactive Music / `reactivemusic`；作者：CircuitLord；许可证：GPLv3（`forge/src/main/resources/META-INF/mods.toml`）
- 目标版本与加载器：Stonecutter 多版本（`settings.gradle.kts:19-27`）—— 版本 `1.19.2 / 1.20.1 / 1.21.1 / 1.21.11`；分支 `fabric`（全部）、`forge`（1.19.2、1.20.1）、`neoforge`（1.21.1）。Java 17，`>=1.20.5` 自动切 21（`build.gradle.kts:29-35`）
- Gradle 插件：`dev.kikugie.stonecutter 0.6`、`dev.architectury.loom 1.13-SNAPSHOT`、`architectury-plugin 3.4-SNAPSHOT`、`com.github.johnrengelman.shadow 8.1.1`（`stonecutter.gradle.kts:1-6`）
- 依赖（`versions/1.21.1/gradle.properties`）：yarn mappings、`fabric-loader 0.16.14`、`fabric-api 0.116.7+1.21.1`、`neo neoforge_loader 21.1.66`、`modmenu 11.0.3`（可选，见 `fabric/src/main/java/circuitlord/reactivemusic/fabric/ModMenuIntegration.java`）。**无第三方 API 依赖**，音频解码（`rm_javazoom.jl`）与 YAML（`org.rm_yaml.snakeyaml`）以源码 vendored 进 `src/main/java`
- mod 元数据：`fabric.mod.json` 未包含在本地快照中（由 `fabric/build.gradle.kts:106-113` 的 `processResources properties(...)` 注入 `${id}/${name}/${version}/${minecraft}` 占位符）；Forge / NeoForge 的 toml 同样使用 `${loader}`、`${id}` 占位符

## 2. 源码规模与包结构

实测：**205 个 .java / 36376 行**（含 vendored）；**自有代码 26 个文件 / 3224 行**。

- `circuitlord.reactivemusic`：11（含 6 个最大类）
- `circuitlord.reactivemusic.config`：5；`.entries`：3；`.mixin`：4；`.platform`：2；`.compat`：1
- `org.rm_yaml.snakeyaml.*`：~180（vendored YAML）、`rm_javazoom.jl.*`：若干（vendored MP3）
- 最大自有文件：`config/ModConfig.java` 729、`ReactiveMusic.java` 710、`SongPicker.java` 552、`RMSongpackLoader.java` 283、`PlayerThread.java` 250、`entries/RMRuntimeEntry.java` 197

## 3. 入口与注册

无内容注册（纯客户端 mod，无 DeferredRegister/Registrate）。三段式入口：

- Fabric：`fabric/.../fabric/ReactiveMusicFabric.java:15-19` → `ReactiveMusic.init()` + `initClient()`，并用 `ClientCommandRegistrationCallback` 注册 `/reactivemusic` 及其子命令
- NeoForge：`neoforge/.../neoforge/ReactiveMusicNeoForge.java:20-36` → `@Mod("reactivemusic")`，`FMLClientSetupEvent` 里 `enqueueWork(ReactiveMusic::initClient)`，注册 `IConfigScreenFactory` + `RegisterClientCommandsEvent`
- 初始化被拆为 `ReactiveMusic.init()`（仅 `ModConfig.GSON.load()`，服务端安全）与 `initClient()`（`SongPicker.initialize()`、`new PlayerThread()`、`RMSongpackLoader.fetchAvailableSongpacks()`、恢复上次 songpack；`ReactiveMusic.java:98-140`）

## 4. 核心系统

1. **事件驱动的选曲（SongPicker）** — `SongPicker.java`。每 20 tick 执行 `tickEventMap()` 刷新 `public static Map<SongpackEventType, Boolean> songpackEventMap`（时间/维度/生物群系/骑乘实体/降水/村庄半径 30、敌对生物半径 12/血量<35%/bossbar 等，`SongPicker.java:81-286`）；`isEntryValid()` 对 `RMRuntimeEntry.conditions` 做"外层 AND、内层各列表 OR"判定（`SongPicker.java:481-542`）；`pickRandomSong()` 用长度为 8 的 `recentlyPickedSongs` 做近期去重（`SongPicker.java:438-473`）。
2. **Songpack 数据驱动加载** — `RMSongpackLoader.java`：内置包从 `classpath:/musicpack/ReactiveMusic.yaml` 读取（`RMSongpackLoader.java:22`），用户包扫描 `resourcepacks/` 下的 `.yaml`（含 zip 内，用 `FileSystems.newFileSystem` 打开，`:96`）；反序列化到 `SongpackConfig`/`SongpackEntry`，逐条校验 MP3 是否存在（`":255`），失败写入 `SongpackZip.errorString` + `blockLoading` 而非崩溃；事件字符串语法经 `RMRuntimeEntry.create()` 解析为 `block=id,count` / `biome=` / `biometag=` / `dim=` / 枚举事件名，`||` 分隔 OR（`entries/RMRuntimeEntry.java:69-160`）。
3. **独立音频播放线程** — `PlayerThread.java`：daemon 线程 + vendored `AdvancedPlayer` 播放 mp3（`:73-105`），主线程只写 `volatile` 状态；增益模型 `MIN_GAIN=-50 / MAX_GAIN=0`、`processRealGain()` 综合 MC 音量曲线重映射、`gainPercentage`（淡出）、`quietPercentage`（暂停时降到 0.7）、`musicDiscDuckPercentage`（`:158-222`）。
4. **音乐 ducking（唱片压制）** — `mixin/SoundManagerMixin.java:25-63`：注入 `SoundManager#play` HEAD，命中 `music_disc`、`battle.pv`（cobblemon 兼容）或配置 `soundsMuteMusic` 时登记实例；`ReactiveMusic.processTrackedSoundsMuteMusic()` 判定 65 格内、类别音量 `>=0.04` 才压低音乐（`ReactiveMusic.java:619-679`）。
5. **跨加载器抽象** — `platform/PlatformHelper.java`、`platform/BiomeTagHelper.java` 用 `ServiceLoader.load(...).findFirst()` 在 common 侧取实现；`BiomeTagHelper` 把统一标签路径映射到平台命名空间（Fabric/NeoForge `c`、Forge `forge`），并给无前缀标签补 `is_` 前缀做向后兼容（`platform/BiomeTagHelper.java:29-47`、`entries/RMRuntimeEntry.java:172-186`）。
6. **配置与自绘 GUI** — `config/ModConfig.java`：`ConfigStore` 读写 `config/ReactiveMusic.json5`，用 `JsonReader.setLenient(true)` 允许 JSON5 风格、失败回落默认值（`:675-729`）；配置界面为自写 `VanillaConfigScreen`（`:79+`，不依赖 Cloth/ModMenu），NeoForge 通过 `IConfigScreenFactory` 暴露。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（纯客户端，无包注册、无 `ServerPlayNetworking`）。
- 数据驱动：**有（重点）**——songpack YAML（事件条件 + 歌曲列表），支持内置包与用户 resourcepack 包/zip。
- 配置：JSON5（`config/ReactiveMusic.json5`）、Gson 序列化 + 集合空值兜底 `ensureCollections()`。
- datagen：**无**。

## 6. Mixin

- 配置：`src/main/resources/reactivemusic-common.mixins.json`（`package: circuitlord.reactivemusic.mixin`，`JAVA_17`，`client` 下列 4 项；NeoForge toml 通过 `[[mixins]] config` 声明，Forge 侧未在快照中看到对应声明）
- 代表类与 hook：
  - `mixin/MinecraftClientMixin.java:26-31` → `MinecraftClient#tick` `@At("RETURN")`，调用 `ReactiveMusic.newTick()`（主循环落点）
  - `mixin/MusicTrackerMixin.java:16-23` → `MusicTracker#tick` `@At("HEAD") cancellable`，无条件 `ci.cancel()` 关闭原版音乐
  - `mixin/SoundManagerMixin.java:25` → `SoundManager#play(SoundInstance)` HEAD（1.21.9 起改用返回 `PlayResult` 的签名，用 Stonecutter 注释双写）
  - `mixin/BossBarHudAccessor.java:15-18` → `@Mixin(BossBarHud.class)` 接口 accessor `getBossBars()`，供 BOSS 事件判定

## 7. 值得学的 5 条具体做法

1. **Stonecutter 注释块应对多版本 API 差异**：`//? if >=1.21.9 { ... } else { ... }` 直接写在共用源码里（`mixin/SoundManagerMixin.java:21-27`、`SongPicker.java:184-193`），配合 `settings.gradle.kts` 的 branch 只编译对应版本，适用于跨 1.19–1.21 的单仓共用代码。
2. **ServiceLoader 做加载器抽象**：`platform/PlatformHelper.java:7-8` 用 `ServiceLoader.load(PlatformHelper.class).findFirst().orElseThrow(...)`，common 侧不 import 任何 loader 类，实现放在 `fabric/forge/neoforge` 子项目。
3. **音频播放放独立 daemon 线程，主线程只维护状态机**：`PlayerThread.java:66-134` + `ReactiveMusic.newTick()` 的 `gainPercentage/fadeOutTicks` 驱动，避免解码阻塞客户端 tick。
4. **数据包容错而非崩溃**：`RMSongpackLoader.java:165-199,229-281` 把所有解析异常、缺失 MP3 收集进 `errorString`/`blockLoading`，并在 GUI 展示——玩家自制数据包（songpack/resourcepack）场景可直接套用。
5. **用系统属性开启性能埋点**：`ReactiveMusic.java:29-30,337-359`（`-Dreactivemusic.performanceLogging=true`，每 5 秒打印 tick 平均/最差耗时），dev 环境排查"每秒扫描 51×51 方块"这类热点的低成本手段。

## 8. 库 / 前置 / API 类 mod

不适用：非库 mod；但 `entries/RMEntryCondition`、`SongpackEntry`/`SongpackConfig` 事实上是对外数据契约（第三方 songpack 的 API），错误信息通过模组 GUI 回显（`ModConfig.VanillaConfigScreen` 中的 `showWarnings`，`config/ModConfig.java:570,586`）。
