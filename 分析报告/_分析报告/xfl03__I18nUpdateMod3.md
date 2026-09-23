# xfl03/I18nUpdateMod3（自动汉化更新）源码分析

## 1. 基本信息

- Mod 名 / mod_id：自动汉化更新模组Ⅲ，`i18nupdatemod`
- 作者：xfl03；资源包由 CFPAOrg 维护（`src/main/resources/fabric.mod.json` 中 license 为 `AGPL-3.0-only`）
- 目标 MC / 加载器：`gradle.properties:minecraft` 列出 1.6.1~1.21.11 共 56 个版本；加载器支持 Forge、NeoForge、Fabric、Quilt（单 jar 通吃）
- 构建：**不使用 ForgeGradle / Fabric Loom / Architectury**，只有 `java` + `com.github.johnrengelman.shadow 8.1.1` + `com.modrinth.minotaur` + `cursegradle`（`build.gradle.kts:1-5`），Java 8 编译，`configurations.configureEach { isTransitive = false }`
- 编译依赖（全部 compileOnly/implementation，无 MC 依赖）：`fabric-loader 0.15.9`、`cpw.mods:modlauncher 8.1.3`、`net.minecraft:launchwrapper 1.12`、`archive-patcher-applier 1.2`（shadow relocate 到 `include.com.google.archivepatcher`）、`commons-io 2.16.1`、`asm 9.7`、`gson 2.11.0`
- 值得注意：工作区里 `src/main/resources/**` 未 checkout，实际文件由 git 跟踪（`git show HEAD:src/main/resources/...` 可读）

## 2. 源码规模与包结构

21 个 `.java` 文件、共 1397 行（`find . -name '*.java' -exec wc -l {} +`）。包结构（第三层）：

| 包 | 文件数 | 说明 |
|---|---|---|
| `i18nupdatemod` | 1 | 主流程 `I18nUpdateMod.java`（126 行） |
| `i18nupdatemod.core` | 4 | `I18nConfig`(124)、`ResourcePackConverter`(100)、`ResourcePack`(100)、`GameConfig`(54) |
| `i18nupdatemod.util` | 9 | `AssetUtil`(127)、`Log`(85)、`FileUtil`(82)、`VersionRange`(74)、`Version`(70)、`ModUtil`(67)、`Reflection`(64)、`DigestUtil`(35)、`BsDiffUtil`(16) |
| `i18nupdatemod.entity` | 4 | Gson POJO：`AssetMetaData`/`GameAssetDetail`/`GameMetaData`/`I18nMetaData` |
| `i18nupdatemod.modlauncher` | 1 | `ModLauncherService`(86) |
| `i18nupdatemod.fabricloader` | 1 | `FabricLoaderMod`(75) |
| `i18nupdatemod.launchwrapper` | 1 | `LaunchWrapperTweaker`(69) |

最大文件即 `AssetUtil`、`I18nUpdateMod`、`I18nConfig`，整体是"薄启动器 + 纯 Java 业务"的极简结构。

## 3. 入口与注册

无注册框架（无 DeferredRegister/Registrate，无方块物品）。三个加载器入口最终都调用同一静态方法 `I18nUpdateMod.init(Path minecraftPath, String minecraftVersion, String loader, HashSet<String> modDomainsSet)`：

- Forge 1.6~1.12.2：`build.gradle.kts:21-29` 在 manifest 写 `TweakClass=i18nupdatemod.launchwrapper.LaunchWrapperTweaker`、`TweakOrder=33`
- Forge 1.13+ / NeoForge：`src/main/resources/META-INF/services/cpw.mods.modlauncher.api.ITransformationService` → `i18nupdatemod.modlauncher.ModLauncherService`（`transformers()` 返回空列表，只在 `initialize()` 里干活）
- Fabric/Quilt：`fabric.mod.json` 的 `client` entrypoint → `i18nupdatemod.fabricloader.FabricLoaderMod`

```java
public static void init(Path minecraftPath, String minecraftVersion, String loader, @NotNull HashSet<String> modDomainsSet) {
    try (InputStream is = I18nUpdateMod.class.getResourceAsStream("/i18nMetaData.json")) {
        MOD_VERSION = GSON.fromJson(new InputStreamReader(is), JsonObject.class).get("version").getAsString();
    } catch (Exception e) { Log.warning("Error getting version: " + e); }
    modDomainsSet.remove("i18nupdatemod");
    ... // 检测网易客户端后直接 return，拒绝下载
}
```

主流程（`I18nUpdateMod.java:63-91`）：`I18nConfig.getAssetDetail()` 取资产清单 → 逐项 `ResourcePack.checkUpdate()` → `ResourcePackConverter.convert()` → `GameConfig.addResourcePack()` 写 options.txt。

## 4. 核心系统

**① 跨版本 MC 版本探测（无编译期依赖的关键）**
`ModLauncherService.java:60-85`、`LaunchWrapperTweaker.java:42-68`、`FabricLoaderMod.java:28-48` 用反射逐代回退：`cpw.mods.fml.relauncher.FMLInjectionData.mccversion`（1.6~1.7.10）→ `net.minecraftforge.fml.relauncher.FMLInjectionData`（1.8）→ `net.minecraftforge.common.ForgeVersion.mcVersion`（1.8.8~1.12.2）→ 从 `Launcher.INSTANCE.argumentHandler.args` 里找 `--fml.mcversion` → 读 `FMLLoader` 的 `/forge_version.json` 取 `mc`；Fabric 用 `FabricLoaderImpl.INSTANCE.getGameProvider().getNormalizedGameVersion()`，失败再试 Quilt。全部包在 try/catch 里，任一成功即返回。

**② i18nMetaData.json 索引驱动**
classpath 内嵌 `src/main/resources/i18nMetaData.json`（约 5 KB），结构为 `version/games/assets`：`games[].gameVersions` 是字符串版本区间（如 `"[1.6.1,1.8.9]"`），配 `packFormat` 或 `minFormat`+`maxFormat`，以及 `convertFrom`（要合并哪些历史语言包）。`I18nConfig.getGameMetaData()` 用 `VersionRange.contains(Version.from(mc))` 命中条目；`getAssetMetaData()` 先按 `targetVersion` 再按 `loader` 过滤、找不到 loader 就取第 0 条（`I18nConfig.java:53-59`）。`GameMetaData.useNewFormat()` = `minFormat != null && maxFormat != null`。

**③ 镜像竞速 `AssetUtil.getFastestUrl()`（`AssetUtil.java:47-91`）**
候选 URL = `MIRRORS`（raw.githubusercontent + IP 镜像）+ `CFPA_ASSET_ROOT`，固定线程池并发发 HEAD 请求（connect 3s / read 5s），用 `CompletableFuture.anyOf` 循环取最先成功者并 `cancel(true)` 其余；全失败回退 CFPA 源。命中 GitHub raw 时改走 `getGitIndex()` 读 `version-index.json` 拼 release 下载地址（`I18nConfig.java:94-123`）。

**④ ResourcePack 的"本地即缓存"增量更新（`ResourcePack.java`）**
本地临时文件同时是"已应用包的缓存"，`isUpToDate()` 三级短路：文件不存在 → 更新；`mtime > now - UPDATE_TIME_GAP(1 天)` → 判定为最新（限流）；否则比对远端 md5 文本。下载时先落 `.tmp`、校验 md5 后才 `move(REPLACE_EXISTING)`（`ResourcePack.java:75-91`），失败仅告警，只要 tmp 存在就继续 —— 离线可用。

**⑤ ResourcePackConverter 的合并 + 域过滤（`ResourcePackConverter.java:36-79`）**
一次 `ZipOutputStream` 顺序遍历所有源 zip：`parts.length >= 2 && !modDomainsSet.contains(parts[1])` 时跳过该 entry（即只保留 `assets/<domain>/...` 中玩家真实安装的 mod 的翻译）；用 `HashSet<String> fileList` 去重同名 entry（后包不覆盖前包）；遇到 `pack.mcmeta` 时反序列化成内部 `PackMeta` POJO，按目标版本择一写 `pack_format` 或 `min_format`/`max_format`（`ResourcePackConverter.java:81-88`），再交给 `FileUtil.syncTmpFile()` 落地。

**⑥ ModUtil 递归扫 jar 提取 mod domain（`ModUtil.java:31-66`）**
用 `JarInputStream` 流式读 `mods/*.jar`，遇到 `assets/<x>/` 就收 `x`；遇到 entry 名以 `.jar` 结尾（nested jar，如 JiJ）就读进 `ByteArrayOutputStream` 后递归解析，得到"该整合包里实际存在哪些资源域"。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无自定义网络包**（无 SimpleChannel/Payload/Networking）。只有 HTTP(S) 下载：资源包 zip + 对应 md5 文本，用 `commons-io FileUtils.copyURLToFile` 设 3s/33s 超时。
- 数据驱动：`i18nMetaData.json`（内嵌，编译期打包，非 datapack）。
- 配置：无 ModConfig、无界面。改的是游戏 `options.txt`——`GameConfig` 用 Gson 把每行当 key/value 读，`addResourcePack(baseName, resourcePack)` 移除旧同名条目（`it.contains(baseName)`）后追加，1.12 及以下不加 `file/` 前缀（`I18nUpdateMod.java:85-86`）。
- 本地存储：`getLocalStoragePos()` 依次取 `LocalAppData` → macOS `Library/Application Support` → `XDG_DATA_HOME`/`~/.local/share`，兼容旧版 `~/.i18nupdatemod`（`I18nUpdateMod.java:103-125`）。
- datagen：无。
- 其他：自带 `Log`（`Log.setMinecraftLogFile(minecraftDir)` 把日志写进游戏目录）；`BsDiffUtil.applyPatch()` 依赖 archive-patcher 为"未来增量更新"预留，当前未被调用。

## 6. Mixin

**无 mixin**（无 `*.mixins.json`、无 mixin 配置、无 `@Mixin` 类）。这是本 mod 的刻意选择：零 MC 依赖 = 不可能因版本更新而崩，代价是只能做启动期一次性动作。

## 7. 值得学的 5 条具体做法

1. **一个 jar 通吃 56 个 MC 版本**：把启动接入点做成"三个加载器各一个薄适配器"，反射逐代回退探测版本，业务代码 100% 不碰 MC API（`ModLauncherService.java:60-85`、`LaunchWrapperTweaker.java:42-68`、`FabricLoaderMod.java:28-48`）。适用：纯资源/工具类、无需注册内容的 mod。
2. **镜像竞速 + `CompletableFuture.anyOf` 容错下载**：并发 HEAD 探活、取最快、全败回退主源（`AssetUtil.java:47-91`）。适用：任何依赖外部 CDN 的 mod 更新器。
3. **本地文件即缓存的三级更新判定**（不存在 → mtime 限流一天 → md5 比对）（`ResourcePack.java:50-64`）。适用：大体积远端资源的低频拉取。
4. **先写 `.tmp` 再校验再原子 move**，失败只 warning 并在离线时继续使用旧缓存（`ResourcePack.java:75-91`）。适用：任何"下载会破坏可用状态"的场景。
5. **用 `assets/<domain>/` 反查玩家实装 mod 再裁剪资源包**，避免把没装的 mod 的翻译塞进包里（`ModUtil.java:31-66` + `ResourcePackConverter.java:48-50`）。适用：汉化/资源包合并工具、资源裁剪。

## 8. 公开 API / 外部接入

非库 mod，无对外 API 包。可复用点：`i18nupdatemod.util.Log`（可写游戏目录日志）、`Version`/`VersionRange`（解析 `"[1.6.1,1.8.9]"` 形式区间，`util/VersionRange.java`）、`ModUtil`（扫 mods 目录取资源域）、`FileUtil.syncTmpFile`（双副本同步）。对外协议层面唯一"接口"是 CFPAOrg/Minecraft-Mod-Language-Package 的产物格式（文件名 + md5 文本 + version-index.json）。
