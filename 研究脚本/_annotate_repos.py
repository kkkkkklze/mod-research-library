# 来源: ~/Downloads\_teacon\annotate_new_repos.py
# 已归档到 研究脚本/（Downloads 会被清理）。脚本顶部的 HERE 常量默认仍指向 _teacon 数据目录，
# 如数据目录已清，把 HERE 改成新位置或改用 --out/参数。
# -*- coding: utf-8 -*-
"""给 rest_new_repos.md 加备注列(标注误匹配) + 分梯队候选"""
import io, json, re, os

HERE = os.path.expanduser(r'~/Downloads/_teacon')
WS = r''
b = json.load(io.open(os.path.join(HERE, 'rest_packs_summary.json'), encoding='utf-8'))['new_repos']

# 误匹配 / 非源码仓
JUNK = {
    'FabricMC/fabric-example-mod': '示例模板仓（元数据里挂的是模板地址）',
    'MinecraftForge/MinecraftForge': '指向 Forge 主仓（元数据填错）',
    'cofh/feedback': '问题反馈仓，非源码',
    'Serilum/.issue-tracker': '问题反馈仓，非源码',
    'Zepalesque/Aether-Redux-Issue-Tracker': '问题反馈仓，非源码',
    'Soaryn/XyCraftTracker': '问题追踪仓，源码在 CurseForge/私有',
    'satisfyu/Let-s-Do-Hub': 'monorepo hub 仓（Let\'s Do 系列共用）；实际代码可能在其中子目录',
    'gisellevonbingen-Minecraft/JustEnoughMekanismMultiblocks': '组织名带连字符，疑似解析产物；正确应为 gisellevonbingen/JustEnoughMekanismMultiblocks',
    'Nova-Committee/Re': '仓库名被截断；实际应为 Nova-Committee/Re-Avaritia（同表另一条）',
    'DHJComical/IngameIME-1.12.2': '方向反了：仓库是 fork/移植版，原版在 ThinkingStudios',
    'ZeroNoRyouki/ExtremeReactors2': '已在「四包补漏」里回收过（此处按新仓库重复列出）',
    'ZeroNoRyouki/ZeroCore2': '同 ExtremeReactors2，属 ZeroNoRyouki 系列',
}

# 值得深挖的候选: 仓库 -> (一句话为什么)
CAND = {
    'TeamDman/SuperFactoryManager': 'SFM：把一门**自有编程语言**做进方块（词法/语法/编译器/解释器 + 物流执行），与 CC:Tweaked/Carpet 同类，是"DSL 进 MC"的工业范本 → 第二梯队',
    'fzzyhmstrs/pc': 'Particle Core：抽象粒子库（粒子作为数据+行为对象），与 ParticleStorm/aoa_particles 凑成三方对照 → 第二梯队',
    'Traben-0/EmissiveMod': 'Entity Texture Features：实体贴图特性（发光/随机/眨眼材质）——正是我美术管线 `_e` 发光约定的**实现侧**，能拿到命名/打包/性能的全部规则 → 第二梯队',
    'cc-tweaked/CC-Tweaked': 'ComputerCraft：内嵌 Lua 运行时 + 多机网络 + 持久化 + 权限；与 NeoMTR 的 Rhino 对照 → 第二梯队',
    'gnembon/fabric-carpet': 'Carpet：自带测试框架（`/carpet test` + 内置 scarpet 语言），是"无头可复现验证"的成熟做法 → 第二梯队',
    'OnyxStudios/Cardinal-Components-API': 'Fabric 官方式的 capability/数据附着系统（实体/世界/物品注册、同步策略、迁移）——与我 `AspectProfile` 的能力设计同题 → 第二梯队',
    'NovaWostra/Dungeons-and-Taverns': '把**纯结构 datapack 当 mod 发**（大量结构生成 + 群系/结构集），与我的 faces/structures 数据包路线同题 → 第二梯队',
    'Moog-s-Mods/MoogsVoyagerStructures': '同上的结构生成族（另有 FinnSetchell/Moogs* 两个），可对照生成规则组织方式',
    'AppliedEnergistics/Immersive-Energistics': 'AE2 官方团队自研的跨 mod 集成（IE×AE2）——"集成该由谁写、怎么写"的教科书 → 第三梯队(见待办 #11)',
    'Low-Drag-MC/Multiblocked2': 'Multiblocked2：多方块机器 DSL（结构+配方+能力可视化编辑）→ 第三梯队',
    'CleanroomMC/HadEnoughItems': '1.12.2 现代化社区（CleanroomMC）重写的 JEI ——老版本长线维护工程怎么写 → 第三梯队',
    'Elite-Modding-Team/TinkersAntique': "Tinkers' 1.12.2 续作：老 mod 的跨版本续命工程组织方式 → 第三梯队",
    'Povstalec/StargateJourney': '星际之门：维度/传送网络 + 自定义多方块传送装置 → 第三梯队',
    'igentuman/NuclearCraft-Neoteric': 'NuclearCraft 移植：大体系 mod 的跨版本重写 → 第三梯队',
    'KosmX/minecraftPlayerAnimator': 'Player Animator：玩家模型动画（与 BleedZone7 的 dcanim、GeckoLib 对照）→ 第三梯队',
    'Polarice3/Goety-2': 'Goety：大型"暗魔法"内容 mod（仆从/仪式/法术），内容规模与工程组织 → 第三梯队',
    'ramidzkh/Applied-Botanics': 'AE2×Botania 桥：植物魔法自动化接 AE2 → 第三梯队',
    'quek04/The-Undergarden': 'The Undergarden：独立维度 mod（群系/生物/方块全套）→ 第三梯队',
    'ThePansmith/DeepMobEvolution': 'Deep Mob Evolution：刷怪演进/数据驱动生物掉落 → 第三梯队',
    'beelakes/Cluttered-1.19.2-MCreator-Fabric': 'MCreator 生成的 mod 混进正式整合包（与 BleedZone7 同类，可对照 MCreator 产物质量）',
    'Yesssssman/epicfightmod': 'Epic Fight：战斗系统重做（动作驱动的判定/连招/受击反应/武器动作集），与我的战斗机制设计同题 → 第二梯队',
    'matthewperiut/Chisel-Reborn': 'Chisel：方块变体 + CTM 连接材质——「方块材质拼接」的第二条路线（与 Domum Ornamentum 对照）→ 第一梯队同族',
    'architectury/architectury-api': 'Architectury：Fabric/Forge/NeoForge 一套代码的抽象层（我维护两套加载器的方法论参考）→ 第二梯队',
    'OreCruncher/DynamicSurroundingsFabric': 'Dynamic Surroundings：环境音效/粒子/天气的表现层工程（客户端表现设计的成熟范例）→ 第三梯队',
}

rows = sorted(b.items(), key=lambda x: (x[1][1], x[1][0].lower()))
L = ['# 剩余整合包中发现的新仓库（不在已有 591/164 映射里）', '',
     '来源：15 个剩余整合包的 jar 元数据（mods.toml / neoforge.mods.toml / fabric.mod.json / **mcmod.info**）。',
     '共 **%d** 个仓库。备注列标出误匹配与值得深挖的候选。' % len(rows), '',
     '| # | 仓库 | Mod | 所在包 | 备注 |', '|---|---|---|---|---|']
n_cand = 0
for i, (gh, (nm, p)) in enumerate(rows, 1):
    note = JUNK.get(gh, '')
    if gh in CAND:
        note = ('⚠ ' if note else '★ ') + CAND[gh]
        n_cand += 1
    L.append('| %d | https://github.com/%s | %s | %s | %s |' % (i, gh, nm.replace('|', '/')[:50], p, note.replace('|', '/')))
L += ['', '## 过滤统计', '',
      '- 误匹配/非源码仓：**%d** 个（见上表备注开头为「指向/问题反馈/示例模板」的行）' % len(JUNK),
      '- 值得深挖候选：**%d** 个（备注开头 ★ / ⚠）' % n_cand,
      '- 其余为普通依赖/小工具 mod，已进总表备查']
io.open(os.path.join(HERE, 'rest_new_repos.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('已写 rest_new_repos.md（%d 行，误匹配 %d，候选 %d）' % (len(rows), len(JUNK), n_cand))
