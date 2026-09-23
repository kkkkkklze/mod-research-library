# klinbee/No-Void-Structures 源码分析报告

## 1. 基本信息
- Mod 名：No Void Structures（虚空结构抑制）；mod_id **未确认**（工作区无 `build.gradle`/`gradle.properties`/`fabric.mod.json`，仅 `README.md` 被检出）。
- 作者：klinbee（README 致谢 cputnam-a11y 的 1.21 Fabric PR、Cdogsnappy 的 1.19 Forge 回移）。
- 目标版本：README 写明 Fabric 1.21、Forge 1.19.2/1.20.1/1.21（对应远端分支 `deprecated-mod-1.19.2`、`deprecated-mod-1.20.1`、`deprecated-mod-1.21`、`deprecated-mod-main`）。
- 加载器/Gradle 插件/许可证/编译依赖：**本地不可测**（无构建脚本）。README 声明现方案改为 **datapack + Lithostitched**（`https://github.com/Apollounknowndev/lithostitched`），旧 Java 实现已废弃。
- 仓库形态：远端分支 `main`（仅文档）、`datapack`、4 个 `deprecated-mod-*`；本地 clone 开了 sparse checkout（`git ls-files -v` 显示 `.gitattributes`、`LICENSE` 为 skip-worktree，工作区只有 `README.md`），当前 HEAD `b8dbbfc`（2025-08-28 "Update README.md"）。

## 2. 源码规模与包结构
- `.java` 文件数：**0**；总行数：0（`find . -name '*.java' | wc -l` → 0）。
- 无包结构可列。仅有文档 1 个：`README.md`（2870 字节）。

## 3. 入口与注册
无。`main` 分支不含任何 Java 源码或资源。

## 4. 核心系统
无代码可分析。README 记载的历史实现职责（旧 mod，非本分支）：
- 阻止结构在虚空生成（"No Structures will generate below -56"）。
- Mineshaft 生成改为按地表偏移计算（默认用 sea-level）。
- Jungle Pyramid 改用 Desert Pyramid 的放置方式，避免漂浮在岛屿边缘。
- Mansion / Desert Pyramid 不再向下打柱子（pillar down）。
README 自述旧实现的问题：不灵活、不兼容、会破坏超平坦（superflat）结构。

## 5. 网络 / 数据驱动 / 配置 / datagen
无 Java 网络、无 datagen。README 提到"Adding config files"为未来目标（未实现），且新方向是数据驱动（编辑 JSON 配合 Lithostitched）。

## 6. Mixin
无配置文件、无 mixin 类。

## 7. 值得学的 5 条具体做法（均来自 README + 分支布局，非代码）
1. **公开弃用旧实现并写清原因**：`README.md:8-15` 明说旧 mod "inflexible, incompatible, broke superflat structures"，并给出替代路线；适用于任何准备重构的附属 mod，避免用户误装。
2. **分支按用途命名保留历史**：远端 `datapack` 与 `deprecated-mod-<MC版本>` 分离新老实现（`git ls-remote --heads` 输出）；适用于跨大版本重构时保留可回溯源码。
3. **把"能否交给上游库"作为架构判断**：README 明确指出 Lithostitched 出现后本 mod 不再必要，改为数据包；适用于决定"做 mod 还是做 datapack/兼容层"。
4. **数据驱动优于硬编码逻辑**：README:11 强调数据包方案"customization for this is made a lot more friendly"，让整合包作者改 JSON 即可；适用于结构/世界生成类需求。
5. **依赖定位到具体上游项目**：README 直接给出 Lithostitched 仓库地址作为新实现的运行时前置；适用于依附世界生成库的轻量扩展。

## 8. 库/API 类 mod 的公开 API
不适用（非库 mod）。

## 备注
- 本仓库对"学工程"的代码价值为 0（无 Java 源码）；价值在 README 记录的架构决策（mod → datapack+Lithostitched）。
- 若需旧实现代码，应检出 `deprecated-mod-1.21` / `deprecated-mod-1.20.1` 分支后重新分析（本次未检出，属"未确认"）。
