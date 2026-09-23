# -*- coding: utf-8 -*-
"""生成: 1) 分析库总索引 README-索引.md  2) 四包 Mod→GitHub 总表 3) ATM10 对照表"""
import json, os, re, csv

BASE = os.path.dirname(os.path.abspath(__file__))
WS = r'../'
RPT = os.path.join(WS, '_源码分析报告')
CARDS = os.path.join(RPT, '_卡片')

union = json.load(open(os.path.join(BASE, '_union_repos.json'), encoding='utf-8'))
prog = json.load(open(os.path.join(RPT, '_进度.json'), encoding='utf-8'))
reports = set(f[:-3] for f in os.listdir(RPT) if f.endswith('.md') and not f.startswith('_'))
cards = set(f[:-3] for f in os.listdir(CARDS) if f.endswith('.md'))
card_idx = json.load(open(os.path.join(RPT, '_卡片索引.json'), encoding='utf-8'))
atm10 = json.load(open(os.path.join(BASE, '_atm10_final.json'), encoding='utf-8'))
atm10_extra = json.load(open(os.path.join(BASE, '_atm10_extra.json'), encoding='utf-8')) if os.path.exists(os.path.join(BASE, '_atm10_extra.json')) else {}

# ---- 1) 总索引 ----
n_rep = sum(1 for gh in union if gh.replace('/', '__') in reports)
n_card = sum(1 for gh in union if gh.replace('/', '__') in cards)

CAT = [
    ('性能优化 / 引擎底层', ['sodium', 'lithium', 'ferrite', 'modernfix', 'immediatelyfast', 'c2me', 'krypton',
        'embeddium', 'oculus', 'memoryleak', 'gpumemleak', 'flerovium', 'lightspeed', 'entityculling',
        'smooth', 'structurelayout', 'accelerated', 'alltheleaks', 'chunky', 'dynamic-fps', 'fastworkbench',
        'fastfurnace', 'fastleafdecay', 'gputape', 'nothirium', 'redirectionor', 'threadsafe']),
    ('库 / 前置 / API', ['clothconfig', 'architectury', 'balm', 'bookshelf', 'placebo', 'puzzles', 'resourceful',
        'citadel', 'geckolib', 'curios', 'caelus', 'accessories', 'moonlight', 'blueprint', 'cucumber', 'l2library',
        'mmlib', 'lionfish', 'lithostitched', 'prickle', 'searchables', 'iceberg', 'prism', 'octo', 'cristel',
        'malilib', 'midnightlib', 'yacl', 'fconfig', 'owo', 'collective', 'creativecore', 'konkrete', 'melody',
        'kotlinforforge', 'rhino', 'coroutil', 'glitchcore', 'terablender', 'forgeconfigapi', 'baguettelib',
        'framework', 'more-red', 'supermartijn', 'ldlib', 'placebo', 'puzzleslib', 'atlas', 'aero', 'sable']),
    ('Create 机械动力及附属', ['create', 'cbc', 'aeronautics', 'powergrid', 'drivebywire', 'copycat', 'railways',
        'escalated', 'interiors', 'mechanical', 'kinetic']),
    ('科技 / 工业 / 能源', ['mekanism', 'appliedenergistics', 'immersiveengineering', 'immersivepetroleum',
        'thermal', 'enderio', 'modern-industrialization', 'mysticalagriculture', 'occultism', 'botania', 'ars-nouveau',
        'arsnouveau', 'powah', 'industrialforegoing', 'xnet', 'rftools', 'flux', 'hostilenetworks', 'sophisticated',
        'functionalstorage', 'merequester', 'botanypots', 'incontrol', 'torchmaster', 'ironfurnaces', 'deimos',
        'railcraft', 'forestry', 'integrated', 'bigreactors', 'extremereactors', 'enderstorage', 'pipez',
        'cabletiers', 'mffs', 'mobgrinding', 'agricraft', 'pneumaticcraft', 'xycraft', 'titanium', 'coehl',
        'enderstorage', 'mekanismgenerators', 'thermalexpansion']),
    ('实体 / 生物 / AI', ['touhoulittlemaid', 'maid', 'alexsmobs', 'alexscaves', 'critters', 'naturalist',
        'cataclysm', 'lender', 'legendary-monsters', 'block_factorys', 'creeper-overhaul', 'enderman-overhaul',
        'deeperdarker', 'bumblezone', 'twilightforest', 'iceandfire', 'ice_and_fire', 'umapyoi', 'dragonfight',
        'cave', 'myths', 'ivars', 'zombie', 'rats', 'domestication', 'immmersive_aircraft', 'immersiveaircraft',
        'horseman', 'sable', 'shouldersurfing']),
    ('战斗 / 枪械 / 装备 / 属性', ['tacz', 'gun', 'weaponmaster', 'irons', 'apotheosis', 'apothic',
        'combatnouveau', 'transmog', 'armor', 'advancednetherite', 'solcarrot', 'artifacts', 'jewelry',
        'ensorcellation', 'attributefix', 'max-health', 'projectile', 'fastcannon', 'moreshells']),
    ('世界生成 / 结构 / 维度', ['repurposed', 'yungs', 'dungeons', 'dnt', 'hopo', 'skyvillages', 'lostcities',
        'dimdungeons', 'moogs', 'sparse', 'novoid', 'no-void', 'enderscape', 'aetherial', 'eternalstarlight',
        'biomesoplenty', 'terrablender', 'sereneseasons', 'weather2', 'dynamic-trees', 'dynamictrees',
        'naturescompass', 'explorerscompass', 'aether', 'paradise', 'deeperdarker', 'aetherial-islands']),
    ('食物 / 农夫乐事生态', ['delight', 'farmersdelight', 'farmersrespite', 'letsdo', 'let-s-do', 'kaleidoscope',
        'beachparty', 'candlelight', 'herbalbrews', 'brewery', 'vinery', 'wildernature', 'brewin', 'corn',
        'cookbook', 'cuisine', 'cocktail', 'maidsoul']),
    ('GUI / HUD / 客户端体验', ['jade', 'appleskin', 'jei', 'rei', 'emi', 'controlling', 'mousetweaks',
        'betteradvancements', 'enchdesc', 'imblocker', 'jecharacters', 'autotranslator', 'modernui', 'guitween',
        'tooltips', 'colorfulhearts', 'highlighter', 'pickupnotifier', 'showcaseitem', 'visualworkbench',
        'configured', 'inventoryprofiles', 'carryon', 'travelersbackpack', 'backpacked', 'chat', 'skin',
        'fancymenu', 'drippy', 'blur', 'eatinganimation', 'smooth-swapping', 'nametag', 'iris', 'continuity',
        'entity_model', 'entity_texture', 'notenoughanimations', '3d-skin', 'emotecraft', 'emotes', 'xaero',
        'map', 'minimap', 'worldmap', 'netmusic', 'ambientsounds', 'sound', 'musics', 'visual', 'exposure',
        'screenshot', 'betterf3', 'legendarytooltips', 'prism', 'tooltip', 'immersive-ui', 'menu-tweaks',
        'worldedit', 'midnight', 'cherished', 'netherportalfix', 'forgivingvoid', 'sit', 'paxi']),
]

def cat_of(gh, title):
    s = (gh + ' ' + (title or '')).lower()
    for cat, keys in CAT:
        for k in keys:
            if k in s:
                return cat
    return '其他 / 综合'

rows = []
for gh, info in union.items():
    key = gh.replace('/', '__')
    rows.append({'gh': gh, 'title': info.get('title') or gh, 'packs': info.get('packs') or [],
                 'dl': info.get('dl') or 0, 'report': key in reports, 'card': key in cards})

L = []
L.append('# 知名 Mod 源码分析库 — 总索引\n')
L.append(f'本目录是「四个整合包的 mod 源码」分析成果，供学习 mod 工程化开发使用。\n')
L.append('## 概览\n')
L.append(f'- 覆盖整合包: 璇穹之歌(1.21.1 NeoForge)、暗涌：深岩恐惧(1.20.1 Forge)、星轨重铸：残响(1.21.1 NeoForge，航空学)、All the Mods 10(1.21.1 NeoForge)')
L.append(f'- 唯一 GitHub 仓库: **{len(union)}** 个（全部经 git ls-remote 验证 + 稀疏克隆到本地）')
L.append(f'- **深度分析报告（子 agent 逐仓库阅读源码后撰写，含文件路径级引用）: {n_rep} 份** → `_源码分析报告/<owner>__<repo>.md`')
L.append(f'- **速览卡片（脚本自动提取：文件数/行数/包结构/构建方式/主类/许可证）: {n_card} 份** → `_源码分析报告/_卡片/<owner>__<repo>.md`')
L.append(f'- 本地源码: `_参考仓库/`（15 个重点仓库）+ `_参考仓库/_bulk/`（其余全部，稀疏检出只含源码）')
L.append('')
L.append('> 说明：深度报告是 agent 逐个仓库读源码写出的（重点覆盖高频使用/教学价值高的 mod）；速览卡片覆盖全部仓库，给出可检索的结构数据。两者都以 `owner__repo` 命名，一一对应。\n')

L.append('## 使用方式\n')
L.append('1. 想系统学某个主题 → 看下文分类表，挑 `有深度报告` 的仓库报告阅读，报告内每条结论都带 `文件:行号`，可直接打开本地源码对照。')
L.append('2. 想快速了解某个 mod 的规模/结构 → 打开对应速览卡片。')
L.append('3. 想自己跑一遍：脚本在 `~/\Downloads\\_make_cards.py`（卡片生成）、`_pack_research.py`（包→仓库解析）、`_bulk_clone.py`（批量稀疏克隆）。\n')

order = [c for c, _ in CAT] + ['其他 / 综合']
for cat in order:
    items = sorted([r for r in rows if cat_of(r['gh'], r['title']) == cat],
                   key=lambda x: (not x['report'], -(x['dl'] or 0)))
    if not items:
        continue
    L.append(f'## {cat}（{len(items)}）\n')
    L.append('| 仓库 | 项目 | 包 | 深度报告 | 卡片 |')
    L.append('|---|---|---|---|---|')
    for r in items:
        key = r['gh'].replace('/', '__')
        rep = f'[报告](./{key}.md)' if r['report'] else '—'
        card = f'[卡片](./_卡片/{key}.md)' if r['card'] else '—'
        L.append(f"| [{r['gh']}](https://github.com/{r['gh']}) | {r['title'][:40]} | {len(r['packs'])}包 | {rep} | {card} |")
    L.append('')

open(os.path.join(RPT, 'README-索引.md'), 'w', encoding='utf-8').write('\n'.join(L))
print('written README-索引.md', len(rows), 'repos')

# ---- 2) ATM10 对照表 ----
atm_rows = []
for pid, v in atm10.items():
    gh = v.get('gh')
    if not gh:
        e = atm10_extra.get(str(pid)) or atm10_extra.get(pid) or {}
        gh = e.get('gh')
    atm_rows.append((v.get('title') or pid, gh))
n_gh = sum(1 for _, g in atm_rows if g)
L2 = []
L2.append('# All the Mods 10 (v8.1, 1.21.1 NeoForge) — Mod 源码(GitHub)对照表\n')
L2.append(f'- mod 总数: **{len(atm_rows)}**；找到并验证公开 GitHub 仓库: **{n_gh}**；未找到: {len(atm_rows) - n_gh}')
L2.append('- 来源: CurseForge 项目ID → cfwidget 名称 → 与前三包映射复用 + Modrinth 搜索\n')
L2.append('| Mod | GitHub |')
L2.append('|---|---|')
for title, gh in sorted(atm_rows, key=lambda x: (x[1] is None, (x[0] or '').lower())):
    t = (title or '').replace('|', '/')
    L2.append(f'| {t} | {("https://github.com/" + gh) if gh else "未找到"} |')
open(os.path.join(WS, '整合包Mod-GitHub对照表-ATM10.md'), 'w', encoding='utf-8').write('\n'.join(L2))
with open(os.path.join(WS, '整合包Mod-GitHub对照表-ATM10.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['Mod', 'GitHub'])
    for title, gh in sorted(atm_rows):
        w.writerow([title, ('https://github.com/' + gh) if gh else ''])
print('written ATM10 表', n_gh, '/', len(atm_rows))

# ---- 3) 四包总表 ----
with open(os.path.join(WS, '四个整合包Mod-GitHub总表.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['GitHub', '项目名', '出现整合包', 'Modrinth下载量', '有深度报告', '有速览卡片'])
    for r in sorted(rows, key=lambda x: -(x['dl'] or 0)):
        key = r['gh'].replace('/', '__')
        w.writerow(['https://github.com/' + r['gh'], r['title'], '/'.join(r['packs']), r['dl'],
                    'Y' if key in reports else '', 'Y' if key in cards else ''])
print('written 四个整合包Mod-GitHub总表.csv', len(rows))
