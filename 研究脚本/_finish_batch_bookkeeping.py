"""Final bookkeeping for the 2026-09-23 batch: 16 reports.
Backlog table/counts, README counts. Backlog normalized CRLF -> LF deliberately.
"""
import os

ROOT = r""
BL = os.path.join(ROOT, "深挖待办清单.md")
RM = os.path.join(ROOT, "README.md")

# ---- backlog ----
t = open(BL, encoding="utf-8", newline="").read().replace("\r\n", "\n")
before = t

t = t.replace("**已挖 13 份**（统一 8 节、150~200 行、每份 68~177 处 `文件:行号`）：",
              "**已挖 16 份**（统一 8 节、119~201 行、每份 68~177 处 `文件:行号`）：")

anchor = "| `FINDERFEED__FDLib` | Colossus HUD 层 |"
rows = [
    "| `TelepathicGrunt__Bumblezone` | multiloader 工程范本（读者两边都写） | 这仓库**没有 Forge 侧**（`settings.gradle:22` 只 include common/fabric/neoforge）；共享靠\"common 的 java 被两个 loader 各编译一遍\"，不是 Architectury 转换层；`ModuleHolder(id, codec, factory)` 让 common 完全不碰存储 API，各 loader 各自落成 AttachmentType，\"死亡是否复制\"是声明参数。附带纠正：它也没有天气系统（grep weather=0）、不用 NightConfig（NeoForge 用自带 ModConfigSpec，Fabric 用 MidnightLib） |",
    "| `MysticMods__Roots` | 灵力/可再生资源循环 | 「自然之力」Grove Power **没有全局池、没有 SavedData**：每个 Grove Stone 方块实体每 tick 从周围方块现算瞬时功率，消费者用 `PowerTicket` 按 grove tag 分账撮合；限频三闸门全在数据侧（同类方块计数上限 / 对径形状匹配 / rank 倍率）。仪式时间线仍只是 `lifetime` 单标量——与 Occultism 同样**没有阶段机**，差异在失败语义与自动续期 |",
    "| `TeamPneumatic__pnc-repressurized` | 蜂群行为系统 + 殖民物流的重工业版 | 一份 `IProgWidget` 只写一对编解码器（`byNameCodec().dispatch` + `ByteBufCodecs.registry().dispatch`）就同时进 BE NBT / 物品数据组件 / 双向 GUI 同步包 / 可分享 JSON——照这个形状写行为表就不存在\"序列化写三遍\"；无人机另有 `TICK_RATE=3` 降频、ChunkCache 快照 + TTL 认领、`@DescSynced`+BitSet 脏位。压缩气**没有全局图**，是每 handler 本地扩散 + `BlockCapabilityCache` 邻居缓存 |",
]
if anchor in t and "TelepathicGrunt__Bumblezone` | multiloader" not in t:
    i = t.index(anchor)
    j = t.index("\n", i) + 1
    t = t[:j] + "\n".join(rows) + "\n" + t[j:]

t = t.replace("**顺带纠正的既有事实**：confluence 的 boss 内核不在此检出；",
              "**顺带纠正的既有事实**：confluence 的 boss 内核不在此检出（git submodule 未取回）；"
              "Bumblezone 无 Forge 侧、无天气系统、不用 NightConfig；"
              "索引里 occultism 的项目名写作「Occultism KubeJS」但这版并无 KubeJS compat；")

old_head = "**下一批候选**（≥1000 行、与在用工程直接同题、仍只有卡片）："
i = t.find(old_head)
if i >= 0:
    j = t.index("\n", i)
    t = t[:i] + (old_head + "`refinedmods__refinedstorage2`、`Railcraft__Railcraft`、`Draconic-Inc__Draconic-Evolution`、"
                 "`Geforce132__SecurityCraft`（CameraFeed 已被两份设计文档引用）、`breezeth-CN__OrdertoCook`、"
                 "`Lightman314__LightmansCurrency`（新星殖民地的经济对照）、`ARxyt__ColonyPathingEdition`（1.20.1 殖民寻路）、"
                 "`CyclopsMC__*` 一族（IntegratedDynamics/Terminals/Tunnels + CyclopsCore）、`CoFH__CoFHCore`、"
                 "`The-Aether-Team__The-Aether`、`KODU16__vsie`、`Ellpeck__ActuallyAdditions`；"
                 "另有 #14 的 Chisel Reborn + CTM（不在 591 仓库里，需先用 `_bulk_clone.py` 补克隆）。"
                 "完整 249 项见 `对照表/未深挖清单.md`。") + t[j:]
print("backlog changed:", t != before)
open(BL, "w", encoding="utf-8", newline="\n").write(t)

# ---- README ----
r = open(RM, encoding="utf-8", newline="").read()
n1 = r.count("349")
r = r.replace("**349 份深度分析报告**（328 份与速览卡片一一对应）",
              "**353 份深度分析报告**（331 份与速览卡片一一对应）")
r = r.replace("| **349 份**（328 份与卡片一一对应", "| **353 份**（331 份与卡片一一对应")
r = r.replace("2026-09-23：580 个仓库中 252 个仍只有卡片", "2026-09-23：580 个仓库中 249 个仍只有卡片")
open(RM, "w", encoding="utf-8", newline="\n").write(r)
print("README '349' occurrences before:", n1, "| after:", r.count("349"))
