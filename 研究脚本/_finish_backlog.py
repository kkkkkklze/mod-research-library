"""Finish the 2026-09-23 backlog bookkeeping: add batch-3 rows, fix candidate list, normalize to LF."""
import os

P = r"深挖待办清单.md"
t = open(P, encoding="utf-8", newline="").read()
t = t.replace("\r\n", "\n")

anchor = "| `FINDERFEED__FDLib` | Colossus HUD 层 |"
add = [
    "| `TelepathicGrunt__Bumblezone` | multiloader 工程范本（读者两边都写） | 根本没有 Forge 侧（`settings.gradle:22` 只 include common/fabric/neoforge），共享靠\"common 的 java 被两个 loader 各编译一遍\"而非 Architectury 转换层；`ModuleHolder(id, codec, factory)` 让 common 不碰任何存储 API，各 loader 各自落成 AttachmentType；顺带纠正任务书前提：它**没有天气系统**（grep weather = 0）、**不用 NightConfig** |",
    "| `MysticMods__Roots` | 灵力/可再生资源循环 | 「自然之力」Grove Power **没有全局池也没有 SavedData**：每个 Grove Stone 方块实体每 tick 从周围方块现算瞬时功率，消费者用 `PowerTicket` 按 tag 分账撮合；限频三闸门全在数据侧（同类方块计数上限 / 对径形状匹配 / rank 倍率）；仪式时间线仍只是 `lifetime` 单标量，与 Occultism 同样**没有阶段机** |",
    "| `TeamPneumatic__pnc-repressurized` | 蜂群行为系统 + 殖民物流的重工业版 | 一份 `IProgWidget` 只写一对编解码器（`byNameCodec().dispatch` + `ByteBufCodecs.registry().dispatch`）就同时进 BE NBT / 物品数据组件 / 双向 GUI 同步包 / 可分享 JSON —— 照这个形状写行为表就不存在\"序列化写三遍\"；无人机另有 `TICK_RATE=3` 降频、ChunkCache 快照 + TTL 认领、`@DescSynced`+BitSet 脏位 |",
]
if anchor in t and "Bumblezone` | multiloader" not in t:
    i = t.index(anchor)
    j = t.index("\n", i) + 1
    t = t[:j] + "\n".join(add) + "\n" + t[j:]
    print("added 3 rows")

t = t.replace("**已挖 13 份**（统一 8 节、150~200 行、每份 68~177 处 `文件:行号`）",
              "**已挖 16 份**（统一 8 节、119~201 行、每份 68~177 处 `文件:行号`）")
t = t.replace("**顺带纠正的既有事实**：confluence 的 boss 内核不在此检出；",
              "**顺带纠正的既有事实**：confluence 的 boss 内核不在此检出；"
              "Bumblezone 侧没有 Forge（卡片与索引未标注）、没有天气系统、也不用 NightConfig；"
              "occultism 在索引里的项目名写作「Occultism KubeJS」但这个版本并无 KubeJS compat；")

old_cand = "**下一批候选**（≥1000 行、与在用工程直接同题、仍只有卡片）："
i = t.find(old_cand)
if i >= 0:
    j = t.index("\n", i)
    t = t[:i] + ("**下一批候选**（≥1000 行、与在用工程直接同题、仍只有卡片）：`refinedmods__refinedstorage2`、"
                 "`Railcraft__Railcraft`、`Draconic-Inc__Draconic-Evolution`、`Geforce132__SecurityCraft`（CameraFeed 已被两份设计文档引用）、"
                 "`breezeth-CN__OrdertoCook`、`Lightman314__LightmansCurrency`（新星殖民地的经济对照）、"
                 "`ARxyt__ColonyPathingEdition`（1.20.1 殖民寻路）、Chisel Reborn + CTM（#14 的另两条材质路线，需先用 `_bulk_clone.py` 补克隆）、"
                 "`CyclopsMC__*` 一族（IntegratedDynamics/Terminals/Tunnels + CyclopsCore）、`CoFH__CoFHCore`、`The-Aether-Team__The-Aether`、"
                 "`KODU16__vsie`、`Ellpeck__ActuallyAdditions`。完整 249 项见 `对照表/未深挖清单.md`。") + t[j:]
    print("candidate list refreshed")

open(P, "w", encoding="utf-8", newline="\n").write(t)
print("normalized to LF, wrote", P, len(t.split("\n")), "lines")
