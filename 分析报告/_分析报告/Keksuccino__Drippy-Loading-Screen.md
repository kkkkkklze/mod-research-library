# Keksuccino / Drippy-Loading-Screen 源码分析报告

> 重要前提：本地仓库（`源码库\_参考仓库\_bulk\Keksuccino__Drippy-Loading-Screen`）**不包含任何源码**。实测 `find . -path ./.git -prune -o -type f -print` 仅有 `README.md`、`changelog.txt`、`wip_changelog.txt`、`LICENSE.md`、`.github/ISSUE_TEMPLATE/*.yml`（8 个文件、0 个 `.java`）。README 明确写道"Check the branches to see the **source code** for all versions"。本地为 blob:none + shallow 克隆（`git count-objects -v`：in-pack 16、size-pack 75），仅有 `refs/remotes/origin/main`（单提交 `a313a8c Update changelog.txt`）。因此下文 2/3/4/6 节无法给出代码级事实，仅记录元数据与从 changelog 可证实的工程信息。

## 1. 基本信息

- Mod 名：Drippy Loading Screen（FancyMenu 的加载画面定制附属）。作者：Keksuccino（版权 2021-2026）。
- 目标版本/加载器：changelog.txt:21 `v3.1.4` "Ported the mod to Minecraft 26.2"；changelog.txt:31 `v3.1.0` "Dropped support for (Lex)Forge for Minecraft 1.21+"，同时 changelog.txt:32 丢弃 1.18.2/1.21.4/1.21.8；changelog.txt:157 曾"Ported to NeoForge 1.20.4"。即 1.21+ 仅 NeoForge（含 Fortge→NeoForge 路线），与本机 NeoForge 1.21.1 方向一致。
- `mod_id` / Gradle 插件 / `fabric.mod.json`：**未确认**（源码分支不在本地）。
- 许可证：DSMSLv3（DON'T SNATCH MA STUFF LICENSE V3，LICENSE.md）。要点：允许作为 modpack 依赖引用官方下载源，但**禁止复制其代码**、禁止再分发编译产物；"For Devs: you're allowed to create addons or integrate support… but must not copy any of its code"。→ 本仓库**只能做行为/接口层面的参考，不可抄代码**。
- 编译依赖（从 changelog 反推）：FancyMenu（硬依赖，且版本区间敏感，如 changelog.txt:4 "Added support for FancyMenu v3.9.9"、changelog.txt:109 "Now requires FancyMenu v3.3.5+"）；可选 "Drippy Early Loading Module"（changelog.txt:34-36）。

## 2. 源码规模与包结构

无本地源码，无 `.java` 文件，无法统计包结构与最大文件（未确认）。

## 3. 入口与注册

未确认。可从 changelog 推断的两个集成面：NeoForge 的 custom loading screen（changelog.txt:46 "Improved how Drippy hooks into NeoForge's custom loading screen and 'takes over'"）与 Early Loading Screen（changelog.txt:34-36，需额外安装 Early Loading Module，且其编辑器功能受限，"because of how limited the early loading screen is"）。

## 4. 核心系统

无源码可分析。可从 changelog 确认的功能面：布局/元素系统复用 FancyMenu 的布局格式（changelog.txt:7-8 说明 Drippy 布局中禁用元素级 auto-sizing、浏览器/视频元素、菜单背景、装饰浮层，因为这些在加载画面"don't work correctly"），以及 "Vanilla-Like Loading Bar" 元素支持 HEX 颜色含 alpha（changelog.txt:49 修复项）。

## 5. 网络 / 数据驱动 / 配置 / datagen

未确认。

## 6. Mixin

未确认（无源码、无 mixin 配置可读）。

## 7. 值得学的 5 条具体做法

仅能给出与 changelog 对应、可验证的工程做法（非代码级）：

1. **在附属中"接管"宿主 API 时，改成尽量后置、少破坏的接管方式**：changelog.txt:46 记录为避免破坏其他在加载画面注入逻辑的 mod 而重写 hook 方式 → 适用：给 NeoForge 加载画面/主菜单做覆盖式改写的场景。
2. **对承载能力不足的界面禁用不适用功能，而非让它悄悄出错**：changelog.txt:7-8 → 适用：同一套布局 JSON 被复用到不同渲染上下文（加载画面 vs 菜单）时，按上下文裁剪可用元素集。
3. **服务端/客户端类加载隔离**：changelog.txt:10 "Fixed Drippy on NeoForge trying to load a client-side class on the server-side, resulting in a crash" → 适用：NeoForge 双端 mod 的 Mod 构造器/静态初始化别碰客户端类。
4. **对外声明最小依赖版本并随宿主大版本升级同步放行**：changelog.txt:4/109/128/322 反复出现的 "Minimum FancyMenu version is now …" → 适用：编写依赖宿主内部 API 的附属（Create 附属同理）。
5. **非开源许可下的合规复用方式**：LICENSE.md 要求"作为外部依赖从官方源下载"，不得内嵌文件 → 适用：本项目若需 Drippy 风格加载画面，应走依赖引用而非抄代码。

## 8. 库 / API

非库类 mod（是面向玩家的附属），无公开 API 包（未确认）。

## 备注（给后续分析者的可执行补充）

若要补齐本报告，需要按版本分支重新克隆，例如 `git clone -b <1.21.x 分支> https://github.com/Keksuccino/Drippy-Loading-Screen.git`（remote 已确认为 origin，见 `.git/config`）；且因其许可限制，只能用于阅读工程结构与接口设计，不可复制代码。
