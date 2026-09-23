# -*- coding: utf-8 -*-
"""应用最终映射并生成两个新整合包的对照表(md+csv)"""
import json, os, re, csv, subprocess
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = r'../'

FINAL_MANUAL = {
    'fidr': {
        'EpheroLib-1.20.1-FORGE-1.2.0.jar': 'ExcessiveAmountsOfZombies/EpheroLib',
        '[万象] ensorcellation-1.20.1-5.0.2.24.jar': 'CoFH/Ensorcellation',
        '[时装盔甲重置版] cosmeticarmorreworked-1.20.1-v1a.jar': 'zlainsama/CosmeticArmorReworked',
    },
    'starrail': {
        'structureessentials-1.21.1-5.0.jar': 'someaddons/structureessentials',
        'a/[平滑区块保存] smoothchunk-1.21-4.1.jar': 'someaddons/smoothchunksave',
    },
}

PACKS = {
    'fidr': {'json': '_pack_fidr.json', 'out': '整合包Mod-GitHub对照表-FIDR暗涌1.20.1', 'loader': 'Forge 47.4.16'},
    'starrail': {'json': '_pack_starrail.json', 'out': '整合包Mod-GitHub对照表-星轨重铸1.21.1', 'loader': 'NeoForge'},
}

CATS = [
    ('性能优化 / 底层修复', ['sodium', 'embeddium', 'lithium', 'ferritecore', 'modernfix', 'immediatelyfast',
        'c2me', 'krypton', 'accelerated', 'ruok', 'alltheleaks', 'gpumemleakfix', 'flerovium', 'fastleafdecay',
        'fastfurnace', 'fastworkbench', 'fast-ip-ping', 'packetfixer', 'memoryleak', 'entityculling', 'entitycull',
        'flatbedrock', 'zfastnoise', 'efficient_hashing', 'smart_bounds', 'clientsort', 'structure_layout',
        'createbetterfps', 'yeetus', 'fix_attack_lag', 'lightspeed', 'fastboot', 'smoothchunk', 'structureessentials',
        'redirectionor', 'chloride', 'gpu', 'nothirium', 'ferrite']),
    ('库 / 前置 API', ['architectury', 'cloth-config', 'balm', 'bookshelf', 'placebo', 'puzzleslib', 'puzzles',
        'forgeconfigapi', 'resourcefulconfig', 'resourcefullib', 'lionfishapi', 'mysterious_mountain_lib',
        'l2library', 'geckolib', 'citadel', 'moogsstructurelib', 'cristellib', 'coroutil', 'uranus', 'glitchcore',
        'framework', 'yacl', 'fzzy_config', 'kotlinforforge', 'rhino', 'atlas_api', 'bjornlib', 'curios',
        'collective', 'cupboard', 'prickle', 'runiclib', 'zeta', 'baguettelib', 'cofh_core', 'epherolib',
        'ephero', 'geckolib', 'blueprint', 'accessories', 'caelus', 'resourceful', 'guideme', 'kubejs',
        'codechicken', 'common-networking', 'insanelib', 'puzzles', 'libipn', 'libraryferret', 'lionfish',
        'gunsmithlib', 'moonlight', 'supplementaries']),
    ('Create 机械动力及航空学生态', ['create', 'cbc', 'aeronautics', 'sable', 'simulated', 'aero', 'powergrid',
        'drivebywire', 'copycat', 'meowchanics', 'apokinetics', 'hotstuff', 'tracks', 'railways', 'escalated',
        'interiors', 'photomancy', 'bits_n', 'dyn-light', 'AeroEngine', 'portable_engine', 'things_and_misc',
        'ultimine']),
    ('食物 / 农夫乐事生态', ['delight', 'farmersdelight', 'farmers', 'farmersrespite', 'letsdo', 'kaleidoscope',
        'maidsoul', 'cuisine', 'barbeque', 'condiment', 'vinery', 'brewin', 'brewery', 'candlelight',
        'herbalbrews', 'beachparty', 'wildernature', 'bakery', 'bakeries', 'tastejournal', 'ordertocook',
        'hotbath', 'flavor', 'settlements', 'cookbook', 'cocktail', 'corn', 'nethersdelight', 'ends_delight',
        'alexsdelight', 'engineers', 'crate', 'displaydelight', 'vanillacookbook']),
    ('生物 / 实体 / AI', ['touhoulittlemaid', 'maid', 'alexsmobs', 'alexscaves', 'critters', 'legendar',
        'myths', 'ivars', 'block_factorys_bosses', 'cataclysm', 'dmr', 'dragon', 'moredragons', 'armoreddoggo',
        'goblintrader', 'skeletons', 'slime', 'rats', 'wan_ancient', 'dragonfight', 'zombie', 'enhancedai',
        'dummmmmmy', 'parcool']),
    ('战斗 / 魔法 / 装备', ['irons_spellbooks', 'irons_jewelry', 'irons', 'apotheosis', 'apothic', 'combat',
        'transmog', 'armoroftheages', 'advancednetherite', 'legendary', 'tacz', 'gun', 'weaponmaster',
        'artifacts', 'ensorcellation', 'itemrarity', 'bountiful', 'baubles', 'cosmetic', 'spyglass']),
    ('世界生成 / 结构 / 地牢', ['repurposed_structures', 'dungeonsarise', 'dungeons-and-taverns', 'dnt', 'hopo',
        'structurecompass', 'skyvillages', 'skylands', 'endrem', 'end_remastered', 'eternalstarlight', 'yungs',
        'yung', 'biggerbetterendcities', 'medieval_buildings', 'twilightforest', 'explorerscompass', 'atlas',
        'globalpacks', 'paxi', 'byepregen', 'wwoo', 'sereneseasons', 'weather2', 'lostcities', 'unusualend',
        'caveore', 'lunarnether', 'naturescompass', 'aetherial', 'islands', 'diabolical', 'the_afterdark',
        'afterdark', 'endertrigon']),
    ('界面 / HUD / 便利', ['jade', 'appleskin', 'jei', 'controlling', 'mousetweaks', 'betteradvancements',
        'enchdesc', 'imblocker', 'jecharacters', 'autotranslator', 'modernui', 'guitween', 'obscure_tooltips',
        'particular', 'colorfulhearts', 'showcaseitem', 'highlighter', 'pickupnotifier', 'visualworkbench',
        'configured', 'searchables', 'fastrecipesearch', 'fasttag', 'eccentrictome', 'findme', 'corpse',
        'backpacked', 'cinematic', 'shouldersurfing', 'viewfinder', '3d', 'skinlayers', 'sodiumdynamiclights',
        'immersive_melodies', 'netmusic', 'ambientsounds', 'presencefootsteps', 'sound-physics', 'do_a_barrel_roll',
        'xaero', 'minimap', 'worldmap', 'fancymenu', 'melody', 'konkrete', 'retraining', 'apricity', 'customskin',
        'i18n', 'inventoryprofiles', 'inventory', 'carryon', 'travelersbackpack', 'backpack', 'shoppy',
        'customstartinggear', 'lookinmyeyes', 'rummage', 'modern_glass', 'chat', 'notenoughanimations', 'betterf3',
        'legendarytooltips', 'waystones', 'jeimultiblocks', 'ibeeditor', 'panoramica', 'drippy', 'f3', 'quark',
        'worldedit', 'spark', 'recipe', 'gbags', 'sisser', 'jrftl', 'notrample', 'alwaysEat']),
    ('玩法 / 系统 / 数据', ['kubejs', 'lootjs', 'lootr', 'fishingreal', 'toughasnails', 'solcarrot', 'playerrevive',
        'serverwarashi', 'smsn', 'mail', 'trade', 'market', 'polymorph', 'justenoughprofessions', 'powerful_dummy',
        'exposure', 'screenshot', 'biomespy', 'fragmentum', 'frequency', 'ultramarine', 'electroenergetics',
        'mechanicals', 'alloy_smelter', 'createnuclear', 'industrial', 'mekanism', 'immersiveengineering',
        'immersive_aircraft', 'immersivepetroleum', 'appliedenergistics', 'botanypots', 'aquaculture', 'easyLAN',
        'locator', 'asynclogger', 'ping', 'voicechat', 'moonlight', 'waystones', 'quests', 'quest', 'ftb',
        'mysterious', 'species', 'botania', 'thermal',
        'incontrol', 'itemblacklist', 'timecontrol', 'global-server-config', 'nochatreports', 'paraglider',
        'spyglass', 'cucumber', 'corail', 'mystical', 'mob', 'torohealth']),
]

def cat_of(name, title):
    s = (name + ' ' + (title or '')).lower()
    for cat, keys in CATS:
        for k in keys:
            if k.lower() in s:
                return cat
    return '其他 / 综合'

def gh_ok(repo):
    try:
        r = subprocess.run(['git', 'ls-remote', '--exit-code', '--heads', f'https://github.com/{repo}.git'],
                           capture_output=True, timeout=60)
        return repo, r.returncode == 0
    except Exception:
        return repo, False

def process(key):
    cfg = PACKS[key]
    final = json.load(open(os.path.join(BASE, f'_{key}_final.json'), encoding='utf-8'))
    # 应用最终映射
    new = [(fn, gh) for fn, gh in FINAL_MANUAL[key].items() if fn in final and not final[fn].get('gh')]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for fn, ok in ex.map(lambda it: gh_ok(it[1]) and (it[0], True) or (it[0], False) if False else (it[0], gh_ok(it[1])[1]), new):
            src = dict(new)
            if ok:
                final[fn]['gh'] = src[fn]
                final[fn]['via'] = 'manual-verified'
    json.dump(final, open(os.path.join(BASE, f'_{key}_final.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    pack = json.load(open(os.path.join(BASE, cfg['json']), encoding='utf-8'))
    n_total = len(final)
    with_gh = [(fn, v) for fn, v in final.items() if v.get('gh')]
    no_gh = [(fn, v) for fn, v in final.items() if not v.get('gh')]

    L = []
    L.append(f'# {pack["name"]} ({pack["versionId"]}) — Mod 源码(GitHub)对照表\n')
    L.append(f'- 整合包: `{pack["name"]}` v{pack["versionId"]}（{cfg["loader"]}）')
    L.append(f'- mod 总数: **{n_total}**；找到并验证公开 GitHub 仓库: **{len(with_gh)}**；未找到: {len(no_gh)}')
    L.append('- 数据来源: Modrinth API `source_url` + jar 内 `mods.toml`/`neoforge.mods.toml` 元数据 + GitHub 搜索核对；所有链接经 `git ls-remote` 验证\n')

    order = [c for c, _ in CATS] + ['其他 / 综合']
    for cat in order:
        items = sorted([(fn, v) for fn, v in with_gh if cat_of(fn, v.get('title')) == cat],
                       key=lambda x: -(x[1].get('downloads') or 0))
        if not items:
            continue
        L.append(f'\n## {cat}（{len(items)}）\n')
        L.append('| mod | 项目名 | GitHub |')
        L.append('|---|---|---|')
        for fn, v in items:
            t = (v.get('title') or fn).replace('|', '/')
            L.append(f'| `{fn}` | {t} | https://github.com/{v["gh"]} |')

    L.append(f'\n## 未找到公开仓库（{len(no_gh)}）\n')
    L.append('| mod 文件 | 说明 |')
    L.append('|---|---|')
    for fn, v in sorted(no_gh):
        low = fn.lower()
        if 'xaero' in low:
            note = '闭源'
        elif 'dungeonsarise' in low:
            note = '闭源'
        elif 'tacz' in low or 'gunsmithlib' in low:
            note = '永恒枪械工坊系列，闭源'
        elif 'macaw' in low or 'mcw-' in low:
            note = 'Macaw 系列，源码未公开'
        elif 'globalpacks' in low:
            note = '作者 JTK222 未开源'
        elif '金锭' in fn or 'rsinfinitybooster' in low:
            note = ''
        elif any(k in low for k in ('机械动力', 'create_', 'sable', 'aero', 'cbc')):
            note = 'Create 生态附属，作者未开源'
        else:
            note = 'CurseForge 独占 / 未公开源码'
        L.append(f'| `{fn}` | {note} |')

    out_md = os.path.join(WORKSPACE, cfg['out'] + '.md')
    open(out_md, 'w', encoding='utf-8').write('\n'.join(L))
    out_csv = os.path.join(WORKSPACE, cfg['out'] + '.csv')
    with open(out_csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['mod文件', '项目名', 'GitHub', '来源'])
        for fn, v in sorted(final.items()):
            w.writerow([fn, v.get('title') or '', ('https://github.com/' + v['gh']) if v.get('gh') else '', v.get('via') or ''])
    print(f'{key}: {len(with_gh)}/{n_total} -> {out_md}')

for k in PACKS:
    process(k)
