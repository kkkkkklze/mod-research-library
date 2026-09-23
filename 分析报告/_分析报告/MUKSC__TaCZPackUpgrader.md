# MUKSC/TaCZPackUpgrader 源码分析

## 1. 基本信息

TaCZ Pack Upgrader / `taczpackupgrader`；作者 MUKSC（`me.muksc`）；版本 2.1.3；目标 **MC 1.21.1 + NeoForge `21.1.93`**（`[21,)`）、Java 17+（Kotlin 2.3.0）；单加载器 NeoForge，无 mixin。Gradle：`net.neoforged.moddev 2.0.74`、`org.jetbrains.kotlin.jvm 2.3.0`、`me.modmuss50.mod-publish-plugin 1.0.0`、`co.uzzu.dotenv.gradle 4.0.0`；版本集中在 `gradle/libs.versions.toml`。许可证 ARR（`neoforge.mods.toml:license = "ARR"`）。编译/运行依赖：仅 neoforge + minecraft，**无第三方 mod 依赖**（不依赖 TaCZ 本体，纯文件迁移工具）。

## 2. 规模与包结构

实测 3 个源文件、约 434 行：`src/main/java/me/muksc/taczpackupgrader/TaCZPackUpgrader.java`（19 行，入口）、`src/main/kotlin/me/muksc/taczpackupgrader/Upgrader.kt`（**410 行，全仓最大，全部逻辑**）、`Tag.kt`（5 行，`data class Tag(type, value)`）。单包结构，无 config/network/datagen/mixin 子包。

## 3. 入口与注册

`TaCZPackUpgrader.java`：

```java
@Mod(TaCZPackUpgrader.MOD_ID)
public class TaCZPackUpgrader {
    public static final String MOD_ID = "taczpackupgrader";
    public static ModContainer container;
    public TaCZPackUpgrader(IEventBus bus, ModContainer container) {
        TaCZPackUpgrader.container = container;
        Upgrader.INSTANCE.run(FMLPaths.GAMEDIR.get().resolve("tacz"));
    }
}
```

要点：① 逻辑在 **mod 构造器**内同步执行（早于注册阶段），不进 `FMLCommonSetupEvent`；② 注入 `ModContainer` 静态保存，供 `Upgrader` 读取自身 jar 内资源；③ 无任何 DeferredRegister——它不注册游戏内容，只做"启动时改写磁盘文件"。无 mixin（仓库内无 mixins.json）。

## 4. 核心系统

- **内嵌映射表**（`Upgrader.kt:23-28`）：`TaCZPackUpgrader.container.modInfo.owningFile.file.findResource("conversion.json")` → Gson `TypeToken<Map<String, Tag>>` 得 `conversion`；即"旧 ID → (type, value)"查表数据。
- **包解压与归位**（`Upgrader.kt:30` `run`、`:45` `extractPacks`、`:56/:76` `extractZip/JarPacks`）：工作目录 `taczpackupgrader`（每次 `deleteRecursively()` 重建，`run:31-35`），备份目录 `tacz+1.20.1`（`:36`）；zip/jar 先备份原件、解到 `temp/`，识别 jar 内三种布局 `assets/<namespace>/gunpack`、`custom`、`addon`（`:89-118`），最后把解出的目录 `moveTo(tacz/<name>)`。
- **目录包判定与升级**（`:128` `processPacks`、`:167` `iterateDirectoryPacks`）：以 `gunpack.meta.json` 存在作为"枪包"判据（递归搜索）；`shouldUpgrade`（`:152`）跳过 `tacz_default_gun` 与已带 `+1.21.1` 后缀者，保证幂等；对每个包先 `copyToRecursively` 备份，再对 `data/<namespace>` 依次 `upgradeBlockDatas / upgradeLootInjectors / upgradeRecipes`（`:210/:240/:270`），最后 `zip(...)` 输出 `<name>+1.21.1.zip` 并删除原目录。
- **JSON 迁移细则**：`upgradeLootInjector` 把 `minecraft:set_nbt` 改写为 `minecraft:set_components` + `minecraft:custom_data`（并 `remove("tag")`）；物品/标签 ID 用 `conversion` 查表改写 `tag` / `item` 字段（`:340-346`）；每个文件 try/catch，解析失败则 `deleteExisting()` 丢弃坏文件不中断批处理。

## 5. 网络 / 数据驱动 / 配置 / datagen

网络、配置、datagen 均**无**。唯一"数据驱动"是内嵌只读资源 `conversion.json`（随 jar 打包，改版本只需改数据不改代码）；`Upgrader` 另有 `SUFFIX = "+1.21.1"` 常量驱动输出命名（`:20`）。

## 6. Mixin

无（`src/main/resources` 下只有 `META-INF/neoforge.mods.toml`，无 mixins 配置）。

## 7. 值得学的 5 条做法

1. 读自身 jar 内资源用 `ModContainer.modInfo.owningFile.file.findResource(...)`（`Upgrader.kt:23`），绕开类加载器差异，比 `getResourceAsStream` 更适合"打包数据表"场景。
2. 破坏性批处理前先整目录备份到 `<原目录名>+1.20.1`（`run:36`、`processPacks:128-136`），用户可随时回滚。
3. 幂等判定写进命名规则：输出带 `+1.21.1` 后缀，`shouldUpgrade` 检查后缀 + 默认包黑名单（`:152-156`），重复启动不会二次处理。
4. Kotlin `iterator {}` 协程式生成器封装递归遍历（`iterateDirectoryPacks:167`、`iterateFilePacks:158`），调用方直接 for 循环，无需收集列表。
5. 迁移规则外置：`when (conversion.type) { "tag" -> ...; else -> obj.add("item", ...) }`（`:342-346`）查表改写，新增映射零代码改动；解析失败即删坏文件，保证批处理不卡死。

## 8. 公开 API / 扩展点

不适用（非库 mod，无对外 API）。
