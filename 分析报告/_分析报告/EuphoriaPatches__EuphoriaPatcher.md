# EuphoriaPatches/EuphoriaPatcher 源码分析报告

## 1. 基本信息

- Mod 名：Euphoria Patcher；mod_id `euphoria_patcher`；作者 SpacEagle17；许可证 MPL-2.0（`EuphoriaPatcher/gradle.properties:13`）；`version.properties:1` = `1.10.1-r5.9.1`（mod 版本 `-` 补丁对应 Complementary 版本）。
- 多加载器 / 多 MC 版本单仓库：子项目 `common / fabric / forge / neoforge / forgeLegacy / forge1_7_10`（`settings.gradle:38-43`）。neoforge 子项目目标 MC 1.21.0、NeoForge 21.0.143（`neoforge/gradle.properties:9-11`）；`forge` 子项目目标 MC 1.14.4 / Forge 28.2.26（`forge/gradle.properties:7,10`）；另有 1.7.10 与 Legacy。
- Gradle 插件：`net.neoforged.moddev 2.0.141` + `com.gradleup.shadow 8.3.6` + `me.modmuss50.mod-publish-plugin`，并用 `includeBuild(build-logic/mod-publish-plugin)` 自带一个发布插件（`settings.gradle:1-2`）。
- 编译依赖（全部 shade + relocate，`neoforge/build.gradle:82-91`）：`io.sigpipe:jbsdiff:1.0`（bsdiff 二进制补丁）、gson 2.8.9、commons-compress 1.21、commons-io 2.11.0、commons-codec 1.15、guava 32.1.2-jre（`transitive = false`）。它不依赖任何 mod API 做核心功能，只软依赖 Iris/Sodium（靠反射 + mixin 软开关）。
- 定位：纯客户端工具，运行时改写 shaderpack 目录内容。

## 2. 源码规模与包结构

- 实测：`find . -name '*.java' | wc -l` = **196 个文件，28237 行**。
- 加载器层文件数：fabric 49 / forge 44 / neoforge 27（大部分是 mixin）；common 为共享逻辑。
- common 主要包（到第 3 层）：`integration/iris` 7、`integration/uniforms` 5、`integration/seasons` 4、`integration/sodium` 2、`features/shader_settings` 4、`features/properties` 3、`features/steganography` 3、`services` 4、`monitoring` 3、`logging` 4、`io` 4、`util/mod` 4、`config` 3。
- 最大文件：`services/ShaderDetector.java`(1058)、`features/shader_settings/UpdateShaderConfig.java`(759)、`forge/.../mixin/IrisHeaderEntryMixin.java`(736)、`integration/ShaderLoader.java`(730)、`fabric/.../IrisHeaderEntryMixinYarn.java`(624)、`fabric/.../IrisHeaderEntryMixin.java`(610)、`monitoring/ShaderpacksWatcher.java`(607)、`DevPatchGenerator.java`(572)。

## 3. 入口与注册

neoforge 入口（`neoforge/src/main/java/com/euphoriapatches/euphoria_patcher/neoforge/ClientEuphoriaPatcher.java:7-17`）：

```java
@Mod("euphoria_patcher")
public class ClientEuphoriaPatcher {
    public ClientEuphoriaPatcher() {
        NeoforgeModLoaderSpecifics neoforgeSpecifics = new NeoforgeModLoaderSpecifics();
        ModLoaderSpecifics.setInstance(neoforgeSpecifics);
        if (ModLoaderSpecifics.serverCheckStatic()) return;
        new EuphoriaPatcher();
    }
}
```

- 无 DeferredRegister / Registrate：注册内容只有配置项与 shader 侧数据，不注册物品方块。
- 多加载器抽象靠 `util/mod/ModLoaderSpecifics` 抽象类 + 静态单例注入：`setInstance/getInstance`，抽象方法 `getShaderpacksPath / getConfigDirectory / serverCheck / getCurrentDimension / isCurrentDimensionInMappings`，各加载器实现一份。
- 主类 `common/.../EuphoriaPatcher.java:52-114` 是"构造函数即启动器"：`ConfigHandler.configStuff()` → `UserPersistentData.validateShaderDataHash()` → `ModFolderVersionChecker.existsNewerModInFolder()` → `UpdateChecker.checkForUpdates()` → `ShaderLoader.getShaderLoader()` → `initializeServices()` → 探测/打补丁。用 `ALREADY_LAUNCHED` 布尔 + 静态 `instance` 防重复执行。

## 4. 核心系统

1. **Shader 探测与补丁流水线**（`common/.../services/`）：`ShaderDetector.detectInstalledShaders(namingService)` 返回 `ShaderInfo`（`isAlreadyInstalled / baseFile / styleReimagined / styleUnbound / installedDir`）；`ShaderPatchingService` + `ShaderNamingService` + `ShaderValidator` 分工。枚举式风格布尔（Reimagined/Unbound）是可借鉴的"包识别"模型。
2. **增量补丁分发**（`io/ArchiveOperations.java` + `DevPatchGenerator.java`）：用 jbsdiff `FileUI` 生成/应用 bsdiff；`PatchInfo` 硬编码 `BASE_TAR_SHA256` 与 `BASE_TAR_SIZE=1650176`，`verifyBaseArchive()`(:225) 对用户手里的基础包做 SHA256 + 大小双重校验，避免版本错配导致补丁失败。
3. **外部文件热重载 + 去抖**（`features/properties/PropertiesWatcher.java`）：`WatchService` × 2（config、properties）+ 两个守护线程；常量 `DEBOUNCE_DELAY_MS = 1000`、`MERGE_COOLDOWN_MS = 2000`、`lastModificationTimes` 并发 Map 抑制抖动；`PropertiesMerger.mergeProperties(propertiesDir, targetFile)` 按 `PropertiesOrder` 固定顺序把 `blockProperties/*.properties` 合并进 `block.properties`。
4. **截图 LSB 隐写**（`features/steganography/`）：把 shader 设置文本嵌进截图像素——只改 blue 通道（`BLUE_BYTE_OFFSET = 2`、`BLUE_BIT_SHIFT = 16`，`ShaderSteganography.java:34-35`），码流打包在 `SteganographyCodec`；用 LWJGL `STBImage/STBImageWrite` 而非 ImageIO（因为 Minecraft 禁用了 AWT headless），并用反射访问 `NativeImage` 以规避模组环境差异。
5. **多 shader 加载器适配**（`integration/ShaderLoader.java`，730 行）：常量枚举 `iris/oculus/optifine/angelica/neoculus/unknown`，提供 `getShaderLoader()`、`getShaderLoaderMCVersion()`、`getShaderLoaderVersionDefine()`、`getShaderLoaderConfigPath()`、`getCurrentShaderpackPath()`；上层用 `integration/uniforms/IrisUniformBridge` 与 `OptifineUniformBridge` 统一 uniform 注入。`integration/seasons/*Helper` 用同样思路适配 FabricSeasons / SereneSeasons / EclipticSeasons。
6. **Iris 深度集成**（`integration/iris/`）：`IrisColortexAdder`（动态追加 colortex）、`IrisReloadManager`、`DimensionShaderRefresh`、`EuphoriaShaderPackCache`、`DimensionWildcardMap`——全部通过反射/mixin，不在编译期依赖 Iris。

## 5. 网络 / 数据驱动 / 配置 / datagen

- **网络：无**。未发现任何 payload/channel 注册，纯客户端。
- **配置**：自研 `config/Config.java`，`readWriteConfig(category, key, defaultValue, description[, allowedValues][, TypeMigration...])`，用 `TypeMigration.map(old, new)` 做旧值迁移，落在 `config/euphoria_patcher/` 下；`regenerateConfig()`(:293) 可整表重建，`startConfigWatcher()`(:397) 监听配置文件变更。运行时状态集中在 `ConfigHandler` 的静态字段（如 `doPopUpLogging`、`UpdateMode.IMPORTANT/ALL/NONE`、`EmbedShaderSettingsMode.ENABLED/DISABLED/DEBUG`）。
- **数据驱动**：几乎"无资源"——`common/src/main/resources` 仅 `settingsConversions.txt` 与 `_0EuphoriaPatches_ErrorShader/shaders/shaders.properties`（错误 shader 占位）；真正数据是 shaderpack 内的 `.glsl/.properties`，由 `features/shader_settings/UpdateShaderConfig.java`(759) + `SettingsConverterUtil` 逐键改写；`io/JsonUtilReader` 读提示消息，`util/UserPersistentData` 写 `data.json` 持久化用户风格选择。
- **datagen：无**（`neoforge/build.gradle` 里配了 `data` run 但没有 DataProvider）。

## 6. Mixin

- 配置：`neoforge/src/main/resources/euphoria_patcher.mixins.json`（另有 fabric/forge 各一份）：`"required": false`、`package com.euphoriapatches.euphoria_patcher.neoforge.mixin`、`plugin EuphoriaMixinPlugin`；`mixins` 9 个（IrisModern* 系列 + EuphoriaPatcherMixin），`client` 14 个。
- 代表类与 hook 目标（目标类常量见 `neoforge/.../mixin/EuphoriaMixinPlugin.java:11-29`）：
  - `IrisHeaderEntryMixin`（561 行）→ `net.irisshaders.iris.gui.element.ShaderPackOptionList$HeaderEntry`，在 Iris shader 选项菜单里插入 Euphoria 自己的条目；
  - `SodiumMessagePopupMixin`(312) / `SodiumMessagePopupContainerMixin` → Sodium 弹窗；
  - `NativeImageMixin` + `ScreenshotMixin` → `com.mojang.blaze3d.platform.NativeImage`、`net.minecraft.client.Screenshot`（隐写落地）；
  - `ReloadShadersOnDimensionChangeMixin`、`ClientTickMixin`、`RenderTypeMixin` / `PreparedRenderTypeMixin` / `EnderDragonRendererMixin`（Iris 新版渲染管线兼容）；
  - `IrisModernPipelineManagerMixin`、`IrisModernShaderPackMixin`、`IrisModernShaderPropertiesMixin`、`IrisModernPackRenderTargetDirectivesMixin`、`IrisModernStandardMacrosMixin`、`IrisModernExtendedDataHelperMixin` → 分别对应 Iris 的 PipelineManager / ShaderPack / ShaderProperties / PackRenderTargetDirectives / gl.shader.StandardMacros / vertices.ExtendedDataHelper。
- 关键机制：`EuphoriaMixinPlugin.shouldApplyMixin()` 对每个 mixin 用 `checkClassExists(常量类名)` 决定是否应用，从而在"没装 Iris / Iris 版本不同 / 没装 Sodium"时整体跳过，而不是崩溃或需要 shadow 包。

## 7. 值得学的 5 条具体做法

1. **软依赖 mixin 开关**：`IMixinConfigPlugin.shouldApplyMixin` + `Class.forName` 存在性判断，把"依赖别人 mod 内部类"的 mixin 全部做成可选（`neoforge/.../mixin/EuphoriaMixinPlugin.java:42+`）；适用：mixin 进他人 mod 内部实现、需兼容多个 mod 版本。
2. **加载器无关的抽象单例**：`util/mod/ModLoaderSpecifics`（`setInstance` 由各加载器入口注入），common 只写抽象调用；适用：architectury 之外想自己控制多加载器分层。
3. **外部文件监听 + 去抖 + 冷却**：`WatchService` 线程池 + `DEBOUNCE_DELAY_MS`/`MERGE_COOLDOWN_MS`/`lastModificationTimes`（`features/properties/PropertiesWatcher.java:22-39`）；适用：热重载配置、自动生成派生文件。
4. **第三方库 shadow + relocate + minimize**：`shadowJar { relocate 'com.google', 'com.euphoriapatches.shadow.com.google' }` + `minimize()` + `jar.enabled = false`（`neoforge/build.gradle:99-149`）；适用：不能在 mod 里引入裸库（gson/guava 冲突）。
5. **增量补丁 + 基包指纹校验**：bsdiff 只发差量，`PatchInfo.BASE_TAR_SHA256 / BASE_TAR_SIZE` + `verifyBaseArchive()` 双重校验后再打补丁（`io/ArchiveOperations.java:225-280`）；适用：分发大数据包/资源包更新（避免全量下载与错版本污染）。
6. （附加）**静态服务类手动装配** `initializeServices()`（`EuphoriaPatcher.java:119-134`）把版本比较器、探测器、命名服务、打补丁服务按依赖顺序 new 出来，不引入 DI 框架也保持可测。

## 8. 库/API 说明

非库 mod，不对外提供 API。其"扩展面"是实现 `ModLoaderSpecifics` 抽象类并调用 `setInstance()`（新增加载器），入口类名固定为各子项目下的 `ClientEuphoriaPatcher`。
