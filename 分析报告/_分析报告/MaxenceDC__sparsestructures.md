# MaxenceDC/sparsestructures 源码分析报告

## 1. 基本信息

- Mod 名：Sparse Structures；`mod_id = sparsestructures`；作者 MaxenceDC；版本 `3.1.3`（gradle.properties）
- 目标：**多加载器**——Fabric（`fabric_version=0.148.0+26.1.2`、loader `0.19.2`）+ **NeoForge**（`neoforge_version=26.1.2.43-beta`，`loader_version_range=[4,)`）；MC `26.1.2`，`java_version=25`
- Gradle：Fabric Loom `1.15.5` + NeoForge ModDevGradle `2.0.141`（根 `build.gradle`），采用 **jaredlll08 Multiloader 模板**：`settings.gradle` 里 `include('common','fabric','neoforge')`，公共逻辑在 `buildSrc/src/main/groovy/multiloader-common.gradle` / `multiloader-loader.gradle`
- 许可证：MIT（`credits` 中致谢 jaredlll08 的 Multiloader 模板）
- 编译依赖：**无第三方库依赖**（仅各加载器自身 + MC）；`neoforge.mods.toml` 只声明依赖 `neoforge` 与 `minecraft`
- 用途定位：纯"结构性"工具 mod —— 读取并改写数据包里的 `structure_set` JSON，使所有结构更稀疏

## 2. 源码规模与包结构

实测：`17` 个 `.java`，共 `488` 行（极小，适合作为"多加载器骨架 + mixin 数据改写"的样板）。

包结构：`common/.../sparsestructures`（6 个类 + `command` 1 + `mixin` 2 + `platform` 1 + `platform/services` 1）、`fabric/.../sparsestructures`（入口 + `mixin` 1 + `platform` 1）、`neoforge/.../sparsestructures`（入口 + `mixin` 1 + `platform` 1）。

最大文件：`fabric/.../mixin/MakeStructuresSparseFabric.java`(62)、`common/.../command/DumpStructureSetsCommand.java`(59)、`neoforge/.../mixin/MakeStructuresSparseNF.java`(56)、`common/.../SparseStructuresConfig.java`(38)、`common/.../SparseStructuresCommon.java`(36)。

## 3. 入口与注册

- Fabric：`fabric/src/main/java/io/github/maxencedc/sparsestructures/SparseStructuresFabric.java`，`implements ModInitializer`，`onInitialize()` 里 `SparseStructuresCommon.init()` + `CommandRegistrationCallback.EVENT.register(...)` 注册 `/dumpstructuresets`
- NeoForge：`neoforge/src/main/java/io/github/maxencedc/sparsestructures/SparseStructuresNeoForge.java`，`@Mod(Constants.MOD_ID)` 构造器注入 `IEventBus`，`NeoForge.EVENT_BUS.addListener(this::registerCommands)`（`RegisterCommandsEvent`）
- **没有方块/物品/实体注册**——这是个"零注册 mod"，所有逻辑靠 mixin + 配置文件。注册框架：无 `DeferredRegister`、无 Registrate

## 4. 核心系统

**4.1 核心：在 JSON 反序列化阶段改写 structure_set**（本仓库最值得学的一点）
`common/.../mixin/MakeStructuresSparseNF.java:19-22` 与 `MakeStructuresSparseFabric.java:23-26` 都 `@Mixin(targets = "net.minecraft.resources.RegistryLoadTask$PendingRegistration")`，在 `loadFromResource` 里、**解码之前**拦截原始 `JsonElement`：

```java
@Inject(method = "loadFromResource", at = @At(value = "INVOKE",
        target = "Lnet/neoforged/neoforge/common/util/NeoForgeExtraCodecs;decodeOnly(...)"))
private static <T> void loadFromResource(..., @Local(name = "json") JsonElement json)
```

关键设计点：
- 过滤 `elementKey.registryKey().identifier().getPath().equals("worldgen/structure_set")`，只处理这一种 registry；跳过 `type == minecraft:concentric_rings`（要塞等不在数据包里写 spacing 的 placement）。
- 直接用 Gson `JsonObject` 改键值：`placement.addProperty("spacing", spacing)`、`"separation"`、`"salt"`、禁用时 `"frequency", 0.0`；并保证 `separation < spacing`（`if (separation >= spacing) separation = spacing - 1`）——**因为原版有 isSpacingValid 校验**，这点是踩坑成果。
- 两平台的注入点不同：NeoForge 用 `NeoForgeExtraCodecs.decodeOnly` 的 INVOKE 点，Fabric 用 `Decoder.parse` 的 INVOKE 点；都用 **MixinExtras 的 `@Local(name = "json")`** 拿局部变量，避免 `@Redirect`/`@Overwrite`。

**4.2 配置系统（自写 JSON5 + Gson）**
- `common/.../SparseStructuresConfig.java`：`spreadFactor`、`idBasedSalt`、`List<CustomSpreadFactors> customSpreadFactors`；`getSpreadFactor(ResourceKey, JsonObject)` 支持两种匹配——结构集 id 本身，或结构集 json 的 `structures[].structure` 里出现该结构 id（`SparseStructuresConfig.java:29-34`），后者让用户写一个 `minecraft:village_plains` 就能改整个 set。
- `common/.../SparseStructuresCommon.java:21-33`：配置文件不存在时从 jar 内 `sparse-structures-default-config.json5` 复制到 `config/sparsestructures.json5`，再用 `new Gson().fromJson(...)` 解析（JSON5 注释靠 Gson 的宽松解析容忍）；解析失败抛带人工提示的异常。
- 常量集中在 `Constants.java`（`CONFIG_RESOURCE_NAME` / `CONFIG_FILENAME` / `CONFIG_FILE_PATH = Path.of("config", ...)`）。

**4.3 平台抽象**：`common/.../platform/Services.java` 用 `ServiceLoader.load(IPlatformHelper.class).findFirst().orElseThrow(...)` 做服务发现，`fabric/neoforge` 各提供 `FabricPlatformHelper`/`NeoForgePlatformHelper`（由 `META-INF/services` 声明），公共代码只调 `Services.PLATFORM.isModLoaded(...)`。

**4.4 用户辅助命令** `common/.../command/DumpStructureSetsCommand.java`
- 权限 `Commands.LEVEL_ADMINS`，把 `StructureSetsSet.structureSets`（`TreeSet<String>`，在 4.1 的 mixin 里每次加载 structure_set 时 `add`，见 `MakeStructuresSparseNF.java:31`）导出为**可直接粘贴进配置的片段**，每行 `{ "structure": "...", "factor": 1 }`
- 文件名带时间戳（`SimpleDateFormat`），dedicated server 上额外提示"文件在服务器目录"；全部文本走 `Component.translatable`（有 i18n key）。

**4.5 两个通用 mixin**（写在 common 的 mixins.json，两平台共享）
- `common/.../mixin/PushSpreadLimit.java`：`@ModifyConstant(method={"lambda$static$0","method_40170"}, constant=@Constant(intValue=4096))` 返回 `Integer.MAX_VALUE`，解除原版 separation/spacing 上限 4096 的 codec 校验。
- `common/.../mixin/FixLocateDistance.java`：`@Mixin(LocateCommand.class)` + `@Overwrite` 重写 `dist(...)`，用 `Math.hypot` 修 MC-177381（`/locate` 返回直线距离错误）；带 `@author`/`@reason` javadoc（Mixin 规范要求）。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 网络：**无**（无包注册、无 channel）。
- 数据驱动：**是，但方向相反**——不新增 registry，而是 mixin 改写**原版/其他 mod 的 datapack JSON**（`worldgen/structure_set`），因此天然兼容所有 mod 与数据包；同时监听 `addStructureSet` 收集 id 供命令导出。
- 配置：自写 `config/sparsestructures.json5`（Gson 反序列化，非 JSON5 库），默认值随 jar 分发（`common/src/main/resources/sparse-structures-default-config.json5`，注释里写明需重启游戏生效）；`Constants.CONFIG_FILE_PATH` 用相对路径 `config/`。
- datagen：**无**。

## 6. Mixin

三份配置，均 `required: true`、`minVersion: 0.8`、`injectors.defaultRequire: 1`：

- `common/src/main/resources/sparsestructures.mixins.json`：`compatibilityLevel JAVA_18`，`refmap ${mod_id}.refmap.json`，mixins `FixLocateDistance`、`PushSpreadLimit`
- `fabric/src/main/resources/sparsestructures.fabric.mixins.json`：`JAVA_21`，`MakeStructuresSparseFabric`
- `neoforge/src/main/resources/sparsestructures.neoforge.mixins.json`：`JAVA_21`，`MakeStructuresSparseNF`（注意 `neoforge.mods.toml` 里用两个 `[[mixins]] config = ...` 同时挂载 common 与 neoforge 两份）

Hook 目标汇总：`RegistryLoadTask$PendingRegistration#loadFromResource`（NeoForge：`NeoForgeExtraCodecs.decodeOnly` 调用点；Fabric：`Decoder.parse` 调用点）、`RandomSpreadStructurePlacement` 静态常量 4096（`@ModifyConstant`）、`LocateCommand#dist`（`@Overwrite`）。

## 7. 值得学的 5 条做法

1. **在 registry 解码前改 JSON，而不是在游戏里改对象**：`MakeStructuresSparseNF.java:22-27` 注入 `loadFromResource` 拿原始 `JsonElement` 再回写 key，一套代码就能影响所有 mod/datapack 的结构集；适用：需要统一改写世界生成数据的工具 mod。
2. **MixinExtras `@Local(name = "...")` 取局部变量代替 `@Redirect`**：`MakeStructuresSparseNF.java:23`；适用：需要读被注入方法内部临时变量，且不想重写整个方法。
3. **改完数据要保证通过原版校验**：`if (separation >= spacing) { spacing = Math.max(1, spacing); separation = spacing - 1; }`（`MakeStructuresSparseNF.java:44-47`）；适用：任何改写 codec 约束值的 injection。
4. **默认配置随 jar 分发 + 首次启动复制到 config/**：`SparseStructuresCommon.java:21-29`，用户拿到带完整注释的模板，升级不覆盖用户改动；适用：自写配置文件（非 NeoForge/Forge ConfigSpec）的 mod。
5. **提供"把运行期数据导出成配置片段"的命令**：`DumpStructureSetsCommand.java` 用 mixin 顺手收集到的 `StructureSetsSet` 反向生成可粘贴 JSON；适用：配置项多、用户需要发现 id 的 mod。

## 8. 公开 API

无对外 API 包（无 service 接口供他人实现，`platform/services/IPlatformHelper` 仅内部多加载器抽象）。接入方式是"零配置生效"：装上即改写所有 `worldgen/structure_set`，用户只需编辑 `config/sparsestructures.json5`。
