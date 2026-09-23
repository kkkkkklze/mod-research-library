# Propulsion-Team/create-propulsion-simulated 源码分析报告

> 重要前提：**该仓库快照不含 mod 源码**。除 `.git/` 外全仓库只有 4 个文件：`build.gradle`、`gradle.properties`、`settings.gradle`、`PatchConfig.java`（55 行，根目录）、`README.md`。`src/` 目录不存在。因此本报告只能依据构建脚本、README 与一个独立工具类，**不能分析其注册体系/核心系统**，相关条目一律标注"未确认"。判断为：发布方仅把构建脚本与产物信息开源（或快照被裁剪），mod 源码未随仓库发布。

## 1. 基本信息

| 项 | 值（来源） |
|---|---|
| Mod 名 | Create Propulsion: Simulated |
| mod_id | `createpropulsion`（`gradle.properties:19`） |
| 版本 | 1.1.5（`gradle.properties:22`） |
| 作者 | Sergey Feduk, Tronco_78, Bunting_chj, SSnowly, KyivSec（`gradle.properties:25`） |
| 主包/group | `dev.propulsionteam.propulsionsimulated`（`gradle.properties:24`） |
| 目标 MC / 加载器 | 1.21.1 / NeoForge 21.1.228，`neoforge_version_range=[21.1.228,)`，`neoforge_loader_version_range=[4,)`（`gradle.properties:8-10`） |
| Gradle 插件 | `net.neoforged.moddev` 2.0.140 + `eclipse/idea/maven-publish`（`build.gradle:5`），Java 21 toolchain（`build.gradle:16`） |
| Mappings | Parchment `1.21 / 2024.11.10`（`gradle.properties:12-13`） |
| 许可证 | MIT License（`gradle.properties:21`） |

**编译依赖（重点）**：Create `6.0.10-280`（`com.simibubi.create`，来自 maven.createmod.net）、Ponder `1.0.82`、Flywheel `1.0.6`（`dev.engine-room.flywheel`）；**核心生态 Sable**：`dev.ryanhcode.sable:sable-neoforge-1.21.1:2.0.3`、`dev.ryanhcode.sable-companion:sable-companion-common-1.21.1:1.5.0`（`api` 而非 `compileOnly`）、`dev.simulated_team.simulated:simulated-neoforge-1.21.1:1.2.1`、`dev.eriksonn.aeronautics:aeronautics-neoforge-1.21.1:1.2.1`、`dev.ryanhcode.offroad:...:1.2.1`（`build.gradle` dependencies 段）。工具链：KotlinForForge 5.9.0（implementation）、MixinExtras 0.4.1（annotationProcessor + neoforge 版）、KubeJS `2101.7.2-build.336`（compileOnly+runtimeOnly，做脚本全局量）、CC:Tweaked `1.114.2`（compileOnly）、Jackson annotations 2.18.2、joml-primitives 1.10.0；`compileOnly` 的联动 mod：Create: Diesel Generators、Create: Industry；本地 `libs/` jar 运行期：createaddition 1.5.10、create_connected 1.3.2、Jade 15.10.5。测试：JUnit 5（`tasks.named('test')` 用 JUnitPlatform）。

## 2. 源码规模与包结构

实测：`find . -name '*.java' | wc -l` = **1**，总行数 **55**（仅根目录 `PatchConfig.java`）。无包结构、无按包文件数、无最大文件榜（唯一文件 55 行）。资源/语言文件同样不在仓库内。

## 3. 入口与注册

**无源码，故无主类**。可推断的信息：
- `build.gradle` 中 `neoForge { mods { "${mod_id}" { sourceSet sourceSets.main } } }`，且 `sourceSets.main.resources { srcDirs = ['src/main/resources', 'src/generated/resources'] }` —— 说明原项目使用"手写资源 + 生成资源"双目录。
- `processResources` 对 `META-INF/neoforge.mods.toml` 与 `pack.mcmeta` 做属性展开，替换变量含 `sable_version`，说明 `neoforge.mods.toml` 里显式声明了对 Sable 的依赖（该 toml 文件本身不在快照内）。
- 无 `mixins.json`、无 mixin 配置类；但依赖里有 MixinExtras，是否使用 mixin **未确认**。

## 4. 核心系统

**无法分析**（无源码）。README 声明的功能面（供对照，均为 README 原文，未经代码验证）：Thruster（燃料推进）/ Ion Thruster（FE 推进）/ Creative Thruster（可配置）三类推进器；与 Sable + Create Aeronautics 的 contraption 物理集成，强调 force-at-point（正确扭矩）与多推进器叠加；Copycat Wings；燃料兼容 Create: TFMG、Crafts & Additions、Diesel Generators、Immersive Engineering、Mekanism Generators、Northstar: Redux、Stellaris。

## 5. 网络 / 数据驱动 / 配置 / datagen

- 配置：从 `PatchConfig.java` 的正则可知原工程使用 **NeoForge `ModConfigSpec`**（`net.neoforged.neoforge.common.ModConfigSpec`），且存在 `PropulsionConfig`（含 `COMMON_BUILDER`，按 `builder.push("...")/pop()` 分组，含 `//Thruster` 注记、`defaultFuelProperties()` 返回 `List<String>` 的默认燃料表）与 `ThrusterConfig`（带 `SPEC`、`public static final ModConfigSpec.*Value` 字段）两个配置类。具体配置项**未确认**。
- 网络 / 数据驱动 / datagen：仓库内无任何可判定证据，**未确认**。

## 6. Mixin

无配置文件（仓库内无 `*.mixins.json`）。**未确认**是否使用。

## 7. 值得学的具体做法

1. **把"Sable 生态"当第一等依赖来写 gradle**：`implementation sable-neoforge` + `api sable-companion-common`，并单独维护 `sable_version`/`sable_companion_version`/`bundled_version`（Simulated+Aeronautics+Offroad 共用同一 `bundled_version` 号），版本同步一目了然 —— `build.gradle` dependencies。
2. **对 Create 的传递依赖做精确 exclude**，剔除自己不发行的可选集成（Registrate、FTB Chunks/Teams/Library、JourneyMap、Architectury），避免开发环境被无关 mod 污染 —— `build.gradle` 的 `implementation("com.simibubi.create:...") { exclude group: ... }`。
3. **用"一次性代码工具类"批量合并/迁移配置类**（学思路而非照抄）：`PatchConfig.java:15-51` 用正则提取 `ModConfigSpec.*Value` 字段、抽取 static 初始化块（`builder` 全部替换为 `COMMON_BUILDER`）、抽取 `defaultFuelProperties()`，再按 `//Thruster` 锚点与 `COMMON_BUILDER.pop()` 锚点插回目标文件 —— 当两个配置类需要合并时，比手抄安全得多的做法；适用场景：大规模配置项搬迁、注册表批量重写。
4. **用 `runtimeOnly files("libs/xxx.jar")` 携带"运行期才需要的兼容 mod"**（Create Addition / Create Connected / Jade），配合 `compileOnly curse.maven:...` 只引用 API —— 适合"兼容但不硬依赖"的 addon。
5. **测试源集与依赖预先铺好**（`testImplementation platform(junit-bom 5.11.4)` + `gson`，`tasks.named('test')` 启 JUnitPlatform），对纯逻辑（如燃料表解析、推力公式）做单元测试，不依赖游戏运行时。

## 8. 公开 API

非库/前置 mod。仓库内无 API 包。**无**。
