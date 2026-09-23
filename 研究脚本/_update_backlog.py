"""Update 深挖待办清单.md with the 2026-09-23 batch progress (keeps CRLF, line-based matching)."""
import os
import re

P = r"深挖待办清单.md"
raw = open(P, encoding="utf-8", newline="").read()
had_crlf = "\r\n" in raw
lines = raw.replace("\r\n", "\n").split("\n")

new_note = ("> 并发实测（2026-09-23）：同一宿主会话里 **3 路并行稳定**（每路一个仓库、各写一份报告）；"
            "一次性开 6 路时 5 路被「模型服务连接中断」打断（只有 1 路落盘），按 3 路一批重跑即全绿。"
            "重跑只补失败项，已落盘的报告不会被覆盖。")

hits = []
for i, line in enumerate(lines):
    if line.startswith("> 注意：") and "串行" in line:
        lines[i] = new_note
        hits.append("note")
    if line.startswith("### 15.") and "`[ ]`" in line:
        lines[i] = line.replace("`[ ]`", "`[~]`", 1)
        lines.insert(i + 1, "- **本轮进度**：已挖 1/3 —— ViScriptRecipe（报告 `分析报告/_分析报告/zhenshiz__ViScriptRecipe.md`）。"
                           "意外结论：它**不嵌脚本语言**，`.recipe` 是 NBT 覆盖文件 + 游戏内可视化编辑器，加载期编译成正版 Recipe；"
                           "与 Hex Casting（栈式 VM）/ NeoMTR（Rhino）的分界判据已写进该报告第 8 节。剩余 2/3：SFM、CC:Tweaked（Carpet 亦未挖）。")
        hits.append("item15")
        break

batch = [
    "## 本轮批量进度（2026-09-23）",
    "",
    "> 缺口盘点：`研究脚本/_missing_reports.py` → 生成 `对照表/未深挖清单.md`（有速览卡片、无深度报告的仓库，按行数降序）。",
    "> 本轮从 **265** 个缺口挖掉 13 个，剩 **252**（其中 ≥1000 行的 184 个）。登记已同步：`分析报告/_分析报告/README-索引.md`"
    " 的 13 行「深度报告」列由 — 改为链接 + 概览计数 + `README.md` 计数。",
    "",
    "**已挖 13 份**（统一 8 节、150~200 行、每份 68~177 处 `文件:行号`）：",
    "",
    "| 报告 | 为什么挖 | 一句话结论 |",
    "|---|---|---|",
    "| `XFactHD__FramedBlocks` | #14 同题：形状×材质如何不爆炸 | 253 个 BlockType 只配 255 份 blockstate / 82 个模型；连接态不是 blockstate property，而是挂在 BlockState 对象上的两个 long 位掩码 |",
    "| `Tower-of-Sighs__AUI` | 卡牌 GUI 的框架参考 | 等于在 MC 里重写了一个精简浏览器（手写 HTML/CSS 解析 + flexbox）；最值得抄的是两趟帧管线与「渲染前强制补交 pending 布局」 |",
    "| `baileyholl__Ars-Nouveau` | 功法数据化 | 每个 glyph 注册即自带一份服务器 TOML（开关/费用/tier/每咒上限/非法组合）——数值平衡外包给整合包作者 |",
    "| `klikli-dev__occultism` | 仪式玩法 | 仪式时间线只有一个 `currentTime` 标量，15 个 Ritual 子类无一覆盖 `update()`（=没有多阶段仪式）；进度只存「配方 ID + 已消耗清单」，剩余材料由全集反算 |",
    "| `zhenshiz__ViScriptRecipe` | #15 语言进方块 | 不嵌语言：NBT 覆盖文件 + 游戏内编辑器，加载期编译成 Recipe；可抄的是「副本构建 + 原子换表 + 基线快照」这套事务骨架 |",
    "| `Raguto__Citadel-1.21.1` | 妖兽动画引擎 | 一个 mixin 给所有 LivingEntity 挂同一条同步 COMPOUND_TAG 并自动存读；但本检出只登记 3/16 个 mixin，Tabula 动画轨解析后即丢弃 |",
    "| `breeze-devs__Settlements-Alpha` | 蜂群/新星同题 | 原版 Brain 当宿主 + 自研 DayPlan 当调度器（只注入 2 个 behavior）；周期热路径用 `floorMod(uuid, interval)` 错峰，一行消掉整村同 tick 尖峰 |",
    "| `MagicHarp__confluence` | Colossus 的 BOSS 样本 | **boss 内核在缺失的 git submodule 里**（本检出只有主模块 ConfluenceOtherworld），招式调度/血条只能标未验证；外围可抄 KillBoard 的「enum 单例 + Codec/StreamCodec 成对 + 全表快照包」，另附三条反例 |",
    "| `Low-Drag-MC__KilaGraph` | 阵图/回路节点化 | `PreparedGraph` 用一次预解析换零运行期查找；它划的界线要一起抄——可以优化寻址，不可以优化求值次序（惰性拉输入是可观察语义） |",
    "| `Minecraft-LightLand__ModularGolems` | 傀儡 + 1.20.1 基础设施 | 它不做方块结构识别：把「拼结构」外包给原版配方系统（自定义 RecipeSerializer），免费拿到 datapack 覆盖 / JEI / 进度 / `/recipe`，零网络代码 |",
    "| `SilentChaos512__Silent-Gear` | 法宝 = 材料 × 部件 | construction（材质规格）与 properties（算好的属性）分离 + 三趟汇总 + 结果烘回物品、读取即命中；真实版本是 1.21.1 NeoForge（卡片写的 1.20.1 错） |",
    "| `jinqinxixi__Trinkets-and-Baubles-Forge-1.20.1` | 1.20.1 槽位系统 | 槽位/GUI/穿戴全外包给 Curios，本仓库只是内容包；真正可抄的是 `ICapabilitySerializable` 直转发的落盘最短路径，外加一串静默失效的反面教材 |",
    "| `FINDERFEED__FDLib` | Colossus HUD 层 | bar 靠 UUID + entityId(-1) 脱离实体；「两个 int 的旁路事件通道」一套协议服务所有血条表现；`AttackChain`（stage 推进 + NBT 续招）近乎零依赖可整包搬 |",
    "",
    "**顺带纠正的既有事实**：confluence 的 boss 内核不在此检出；Silent-Gear 卡片的「1.20.1 userdev」错误（实为 NeoForge 21.1.219）；"
    "Trinkets-and-Baubles 卡片把它当独立槽位系统（实为 Curios 内容包）；速览卡片的行数普遍比实测偏高（最多差值 = 文件数，末行换行符口径），"
    "13 份报告各自在第 2 节标注了复核值与稀疏检出缺什么。",
    "",
    "**下一批候选**（≥1000 行、与在用工程直接同题、仍只有卡片）：`TelepathicGrunt__Bumblezone`（multiloader 范本）、"
    "`MysticMods__Roots`、`TeamPneumatic__pnc-repressurized`、`refinedmods__refinedstorage2`、`Railcraft__Railcraft`、"
    "`Draconic-Inc__Draconic-Evolution`、`Geforce132__SecurityCraft`、`breezeth-CN__OrdertoCook`、"
    "`Lightman314__LightmansCurrency`（新星殖民地的经济对照）、`ARxyt__ColonyPathingEdition`（1.20.1 殖民寻路）、"
    "`zhenshiz__ViScriptShop`、`CyclopsMC__*` 一族（IntegratedDynamics/Terminals/Tunnels + CyclopsCore）。",
    "",
    "---",
    "",
]

if "## 本轮批量进度（2026-09-23）" not in "\n".join(lines):
    for i, line in enumerate(lines):
        if line.startswith("## 第一梯队"):
            lines[i:i] = batch
            hits.append("batch")
            break
    else:
        print("WARN: 第一梯队 anchor missing")
else:
    print("batch section already present")

out = "\r\n".join(lines) if had_crlf else "\n".join(lines)
bak = P + ".bak-0923"
if not os.path.exists(bak):
    open(bak, "w", encoding="utf-8", newline="").write(raw)
open(P, "w", encoding="utf-8", newline="").write(out)
print("edited:", hits, "| lines:", len(lines), "| crlf:", had_crlf)
