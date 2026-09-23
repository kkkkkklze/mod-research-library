# -*- coding: utf-8 -*-
"""生成 整合包Mod-GitHub对照表.md + CSV"""
import json, os, re, csv

BASE = os.path.dirname(os.path.abspath(__file__))
final = json.load(open(os.path.join(BASE, '_final.json'), encoding='utf-8'))

CATS = [
    ('性能优化 / 底层修复', ['sodium', 'lithium', 'ferritecore', 'modernfix', 'immediatelyfast', 'c2me',
        'krypton', 'voxy', 'accelerated', 'ruok', 'alltheleaks', 'gpumemleakfix', 'flerovium', 'fastleafdecay',
        'fastfurnace', 'fast-ip-ping', 'packetfixer', 'disconnect-packet', 'memoryleak', 'entityculling',
        'flatbedrock', 'zfastnoise', 'threadsafe', 'efficient_hashing', 'smart_bounds', 'clientsort',
        'structure_layout_optimizer', 'gpumem', 'createbetterfps', 'yeetusexperimentus', 'fix_attack_lag']),
    ('库 / 前置 API', ['architectury', 'cloth-config', 'balm', 'bookshelf', 'placebo', 'puzzleslib', 'puzzles',
        'forgeconfigapiport', 'resourcefulconfig', 'resourcefullib', 'lionfishapi', 'mysterious_mountain_lib',
        'l2library', 'geckolib', 'citadel', 'moogsstructurelib', 'cristellib', 'coroutil', 'uranus', 'glitchcore',
        'framework', 'yacl', 'yetanotherconfig', 'fzzy_config', 'kotlinforforge', 'rhino', 'atlas_api',
        'bjornlib', 'curios', 'architectury', 'collective', 'cupboard', 'prickle', 'runiclib', 'atlas',
        'zeta', 'baguettelib', 'lionfish', 'kotlin', 'common-networking']),
    ('Create 机械动力及其附属', ['create', 'cbc', 'aeronautics', 'sable', 'simulated', 'aero', 'powergrid',
        'drivebywire', 'copycat', 'meowchanics', 'apokinetics', 'hotstuff', 'tracks', 'railways', 'escalated',
        'interiors', 'photomancy', 'bits_n', 'lever-drugster', 'dyn-light', 'AeroEngine', 'portable_engine']),
    ('食物 / 农夫乐事生态', ['delight', 'farmersdelight', 'farmers', 'letsdo', 'kaleidoscope', 'maidsoul',
        'cuisine', 'barbeque', 'barbeques', 'condiment', 'vinery', 'brewin', 'brewery', 'candlelight',
        'herbalbrews', 'beachparty', 'wildernature', 'bakery', 'bakeries', 'tastejournal', 'ordertocook',
        'hotbath', 'flavor', 'settlements', 't_and_t']),
    ('生物 / 实体 / AI', ['touhoulittlemaid', 'maid', 'alexsmobs', 'alexscaves', 'critters', 'cave',
        'legendar', 'myths', 'ivars', 'block_factorys_bosses', 'cataclysm', 'cats', 'dmr', 'dragon',
        'moredragons', 'armoreddoggo', 'goblintrader', 'skeletons', 'slime', 'rats', 'wan_ancient']),
    ('战斗 / 魔法 / 装备', ['irons_spellbooks', 'irons_jewelry', 'irons', 'apotheosis', 'apothic',
        'combatnouveau', 'combat', 'transmog', 'armoroftheages', 'armor', 'advancednetherite', 'mythsandlegends',
        'legendary', 'equipment']),
    ('世界生成 / 结构 / 地牢', ['repurposed_structures', 'dungeonsarise', 'dungeons-and-taverns', 'dnt',
        'hopo', 'structurecompass', 'skyvillages', 'skylands', 'endrem', 'end_remastered', 'eternalstarlight',
        'biggerbetterendcities', 'medieval_buildings', 'twilightforest', 'tfremastered', 'twilightdelight',
        'explorerscompass', 'atlas', 'globalpacks', 'paxi', 'byepregen', 'wwoo', 'sereneseasons', 'weather2',
        'sable_xaero']),
    ('界面 / HUD / 便利', ['jade', 'appleskin', 'jei', 'controlling', 'mousetweaks', 'betteradvancements',
        'enchdesc', 'imblocker', 'jecharacters', 'autotranslator', 'modernui', 'guitween', 'obscure_tooltips',
        'particular', 'colorfulhearts', 'showcaseitem', 'highlighter', 'pickupnotifier', 'visualworkbench',
        'configured', 'defaults', 'searchables', 'fastrecipesearch', 'fasttag', 'eccentrictome', 'findme',
        'corpse', 'backpacked', 'cinematic', 'ShoulderSurfing', 'viewfinder', '3d', 'skinlayers',
        'sodiumdynamiclights', 'immersive_melodies', 'netmusic', 'ambientsounds', 'presencefootsteps',
        'sound-physics', 'do_a_barrel_roll', 'xaero', 'minimap', 'worldmap', 'fancymenu', 'melody', 'konkrete',
        'retraining', 'transmog', 'apricity', 'ruok']),
    ('玩法 / 系统 / 数据', ['kubejs', 'lootjs', 'lootr', 'fishingreal', 'sereneseasons', 'toughasnails',
        'legendarysurvivaloverhaul', 'solcarrot', 'playerrevive', 'spark', 'serverwarashi', 'smsn',
        'mail', 'mighty_mail', 'trade', 'market', 'polymorph', 'justenoughprofessions', 'powerful_dummy',
        'exposure', 'screenshot', 'biomespy', 'fragmentum', 'frequency', 'ultramarine', 'electroenergetics',
        'mechanicals', 'alloy_smelter', 'createnuclear', 'Industrial']),
]

def cat_of(name, title):
    s = (name + ' ' + (title or '')).lower()
    for cat, keys in CATS:
        for k in keys:
            if k.lower() in s:
                return cat
    return '其他 / 综合'

groups = {}
for fn, v in final.items():
    c = cat_of(fn, v.get('title'))
    groups.setdefault(c, []).append((fn, v))

order = [c for c, _ in CATS] + ['其他 / 综合']
lines = []
n_gh = sum(1 for v in final.values() if v['gh'])
lines.append('# 璇穹之歌 1.1.9 整合包 — Mod 源码(GitHub)对照表\n')
lines.append(f'- 整合包: `璇穹之歌` v1.1.9 (Minecraft 1.21.1 / NeoForge)')
lines.append(f'- mod 总数: **{len(final)}**；找到并验证公开 GitHub 仓库: **{n_gh}**；未找到: {len(final) - n_gh}')
lines.append('- 数据来源: Modrinth API `source_url` + jar 内 `neoforge.mods.toml` 元数据 + GitHub 搜索核对，所有链接均经 `git ls-remote` 验证存在')
lines.append('- 未找到的绝大多数是闭源 mod（如 Xaero 系列、DungeonsArise）或中文作者未开源的附属（帕斯特系列、森罗系列附属、机械动力航空学生态等）\n')

with_gh = [(fn, v) for fn, v in final.items() if v['gh']]
no_gh = [(fn, v) for fn, v in final.items() if not v['gh']]

for cat in order:
    items = []
    for fn, v in with_gh:
        if cat_of(fn, v.get('title')) == cat:
            items.append((fn, v))
    if not items:
        continue
    items.sort(key=lambda x: -(x[1].get('_dl') or 0))
    lines.append(f'\n## {cat}（{len(items)}）\n')
    lines.append('| mod | 项目名 | GitHub |')
    lines.append('|---|---|---|')
    for fn, v in items:
        t = (v.get('title') or fn).replace('|', '/')
        lines.append(f'| `{fn}` | {t} | https://github.com/{v["gh"]} |')

lines.append(f'\n## 未找到公开仓库（{len(no_gh)}）\n')
lines.append('| mod 文件 | 说明 |')
lines.append('|---|---|')
for fn, v in sorted(no_gh):
    note = ''
    low = fn.lower()
    if 'xaero' in low:
        note = '闭源（Xaero 系列从不公开源码）'
    elif 'dungeonsarise' in low:
        note = '闭源'
    elif 'macaw' in low or 'mcw-' in low:
        note = 'Macaw 系列，源码未公开'
    elif 'kaleidoscope' in low or '森罗' in fn:
        note = '中文作者，附属未开源（主模组 KaleidoscopeCookery 已开源）'
    elif 'pasterdream' in low or '帕斯特' in fn:
        note = '中文作者未开源'
    elif 'sable' in low or 'aero' in low or '航空' in fn:
        note = '机械动力航空学生态，部分未开源'
    elif 'coroutil' in low:
        note = '已确认为 Corosauce/CoroUtil'
    else:
        note = 'CurseForge 独占 / 未公开源码'
    lines.append(f'| `{fn}` | {note} |')

out_md = os.path.join(BASE, '整合包Mod-GitHub对照表.md')
open(out_md, 'w', encoding='utf-8').write('\n'.join(lines))
print('written', out_md, len(lines), 'lines')

# CSV
out_csv = os.path.join(BASE, '整合包Mod-GitHub对照表.csv')
with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['mod文件', '项目名', 'GitHub', '来源'])
    for fn, v in sorted(final.items()):
        w.writerow([fn, v.get('title') or '', ('https://github.com/' + v['gh']) if v['gh'] else '', v.get('via') or ''])
print('written', out_csv)

# 统计每个分类数量
for cat in order:
    n = sum(1 for fn, v in with_gh if cat_of(fn, v.get('title')) == cat)
    if n:
        print(f'  {cat}: {n}')
