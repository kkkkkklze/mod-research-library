# DBE / Spark —— 两个发布版本之间的差异（1.0.1004 → 1.0.1009）

> 起因：2026-09-21 用户说「DBE's Spark Engine 这个 mod 更新了，下载一份新的反编译一下」。
> 结论先说：**公开渠道没有比 9 月 5 日更新的构建**，而 9 月 5 日那份与本库已反编译的 jar **逐字节相同**；
> 于是改为把**两次发布之间的差异**测出来 —— 这恰好回答了「更新了什么」。

## 1. 证据链：最新版就是已反编译的那份

| 项 | 结果 |
|---|---|
| CurseForge 项目 | `dbes-spark-engine`（project id **1659148**，owner `DBE_inLang`） |
| CF 文件总数 | **2 个**（`api.cfwidget.com` 镜像 API 直读，无需过 Cloudflare） |
| 最新文件 | fileId **8813615**，`DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar`，release，**2026-09-05 11:28:48 UTC**，38,878,758 字节 |
| 上一个文件 | fileId **8682647**，`SparkEngine-1.21.1-neoforge-1.0.1004.jar`，release，**2026-08-19 06:25:24 UTC**，72,553,137 字节 |
| 最新文件的 sha256 | `0a81edbc19b5651bc548f8fa1ff3de2bb743bf087214bcdf478032375b4bd67f` |
| 本库已反编译的 jar | `Downloads\DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar`（2026-09-16 19:31 下载）→ **sha256 完全相同**（重新下载自 CF 后逐字节比对） |
| jar 内版本 | `neoforge.mods.toml`: `dbe` / `dbe_npc` = **1.0.1009-SNAPSHOT**，包内最新文件时间戳 2026-09-05 16:27 |
| Modrinth（同项目的另一发行） | `spark-core` 最新 = `1.0.957-SNAPSHOT`（beta，**2025-11-16**）→ 更旧 |
| GitHub | `SolarMoonQAQ/Spark-Core`，分支 `1.21.1-neoforge` 最后提交 **2026-01-02** → 更旧，且**只有 core** |

→ 所以「下载一份新的反编译」这一步没有对象；已反编译的 `源码库/_参考仓库/DBE-1.1.0-neoforge-1.21.1/`（3656 个 .java）
就是当前最新公开版。**若作者在内测群（mcmod 页给出的 QQ 群/Discord）发了更新的包，丢进 `Downloads/_teacon/downloaded/` 我随时补。**

## 2. 更新了什么：1.0.1004 → 1.0.1009

工具：`研究脚本/_jar_diff.py`（按 zip 中央目录的 **CRC32** 比对 class，避免"两边都反编译再 diff"的假差异）。
原始数据：`研究脚本/_数据/DBE_版本差异.json`。

```
旧 1.0.1004 (8/19)  7011 个 class
新 1.0.1009 (9/5)   7149 个 class
新增 5458 / 删除 5320 / 修改 1327
```

### 2.1 最大的变更：**命名空间统一（renamespace）**

| 命名空间 | 旧 1.0.1004 | 新 1.0.1009 |
|---|---|---|
| `cn/solarmoon/**`（Spark Core 本体） | **3238** | **0** |
| `cn/dbe/**`（引擎侧） | 3190 | **6566** |
| `ru/nsk/**`（KStateMachine 状态机） | 377 | 377（仅内部改动） |
| `com/jme3`, `jme3utilities`, `vhacd`, `au/edu`（内嵌物理/碰撞库） | 不变 | 不变 |

即：**旧版是「Core 在 `cn.solarmoon.spark_core`、引擎在 `cn.dbe`」的双命名空间共存；新版把 Core 整体并入 `cn.dbe`。**
这解释了为什么公开 GitHub 仓库（`cn/solarmoon/spark_core`，只有 animation/physics/mixin）**对不上**现在发布的 jar——
仓库停在改名之前。

### 2.2 新增的子系统（按新增 class 数）

| 新增包 | 数量 | 读作 |
|---|---|---|
| `cn/dbe/ui/animation_editor` | 540 | **游戏内动画图编辑器 UI**（作者宣传里"随时可编辑的动画图"） |
| `cn/dbe/animation_graph/nodes` | 474 | 动画图**节点库** |
| `cn/dbe/tools/blueprint` | 371 | **蓝图（可视化脚本）工具链** |
| `cn/dbe/effect/particle` | 332 | 粒子/效果系统 |
| `cn/dbe/ui/blueprint` | 265 | 蓝图编辑器 UI |
| `cn/dbe/animation_graph/debug` | 264 | 动画图调试/可视化 |
| `cn/dbe/animation/playback` | 164 | 动画播放层（与旧 core 分离） |
| `cn/dbe/animation/ik` | 161 | **IK**（宣传里的"后续实时 IK"已进来一部分） |
| `cn/dbe/tools/debug` / `tools/storage` | 151 / 151 | 统一调试/存储工具 |
| `cn/dbe/action/runtime`、`action/notifications` | 118 / 111 | 动作库（Montage/GAS 路线的运行时与通知） |
| `cn/dbe/animation_graph/integration`、`runtime` | 115 / 93 | 动画图与外部系统的对接层 |
| `cn/dbe/animation/root_motion` | 93 | 根运动 |

### 2.3 被删除/重写的部分

| 删除的包 | 数量 | 说明 |
|---|---|---|
| `cn/solarmoon/spark_core/animation` | 2087 | 搬进 `cn/dbe/animation*`（不是删除功能，是搬家） |
| `cn/dbe/npc/client` | 531 | NPC 客户端渲染整体移除 → 新版走别的渲染路径（很可能是并入 `cn/dbe/ui`/新动画图） |
| `cn/dbe/blueprint/client`、`blueprint/mgmc` | 289 / 197 | 蓝图客户端与 mgmc 集成重写（新版 toml 里 `mgmc` 是 optional 依赖） |
| `cn/solarmoon/spark_core/gas`、`physics`、`state_machine`、`pack`、`util` | 267 / 172 / 92 / 76 / 57 | 全部搬到 `cn/dbe/*` |
| `cn/dbe/action/runtime`（旧实现） | 152 | 同名重写（新实现 118 个） |
| `cn/dbe/particle/molang`、`particle/client`、`particle/common` | 103 / 77 / 73 | 粒子层重构为 `cn/dbe/effect/particle` |

### 2.4 修改最重的包（有增无删的功能演进）

`cn/dbe/npc/network` 287、`cn/dbe/npc/ai` 232、`ru/nsk/kstatemachine/{state,statemachine,transition,event}` 85/42/32/26、
`cn/dbe/state_tree/authoring` 79、`cn/dbe/npc/control` 47、`cn/dbe/action/asset` 40 —— **NPC 的 AI/网络与状态机**是这版重点。

## 3. 对已有分析的影响

- 本库的深度报告（`分析报告/_分析报告/DBE__dbe-1.1.0-neoforge-1.21.1.md`）读的是**新版（1.0.1009）**反编译产物，
  与当前最新公开版一致，**不需要重做**。
- 阅读时注意：报告里提到的"GAS/状态树/物理/NPC"这些包，新版都在 `cn/dbe/**`；若对照公开 GitHub 仓库，
  那是**改名前的 core**（`cn.solarmoon.spark_core`），两边的包路径不能直接对照。
- 想读**可读源码**（Kotlin 原码，非反编译）时用 GitHub 仓库，但只覆盖 core 且落后约 8 个月。

## 4. 复现

```bash
py 研究脚本/_downloader.py --cf 8813615 "DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar" -o 下载缓存
py 研究脚本/_downloader.py --cf 8682647 "SparkEngine-1.21.1-neoforge-1.0.1004.jar"  -o 下载缓存
py 研究脚本/_jar_diff.py 下载缓存/SparkEngine-1.21.1-neoforge-1.0.1004.jar \
                        下载缓存/DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar \
                        --json 研究脚本/_数据/DBE_版本差异.json
py 研究脚本/_downloader.py --head "https://mediafilez.forgecdn.net/files/8813/615/DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar"
```

> 两个坑记在 `研究脚本/README.md`：① CF 的网页与 `/download/<fileId>` 有 Cloudflare 挑战（脚本直连 403），
> 走 `api.cfwidget.com` 取元数据、走 `mediafilez.forgecdn.net` 下载；② forgecdn 直链**必须用与 CF 完全一致的文件名**
> （我一开始拿新文件名去下旧 fileId，得到 403，误以为是"老文件被删"）；③ 该 CDN 不支持 Range（501），只能整包下。
