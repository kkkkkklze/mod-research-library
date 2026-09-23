# -*- coding: utf-8 -*-
"""把已验证映射(上一包结果 + 人工候选)应用到两个新包, 然后生成对照表"""
import json, os, re, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

def norm(name):
    n = name.rsplit('.jar', 1)[0].lower()
    n = re.sub(r'^\s*(?:\[[^\]]*\]|【[^】]*】|[\u4e00-\u9fff]+|[a-z]/)+', '', n)
    n = re.sub(r'[-_+]?v?\d[\w.+~\-]*$', '', n)   # 去尾部版本
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

# 上一包(璇穹之歌)已验证映射
prev = json.load(open(os.path.join(BASE, '_final.json'), encoding='utf-8'))
prev_lookup = {}
for fn, v in prev.items():
    if v.get('gh'):
        prev_lookup.setdefault(norm(fn), v['gh'])

# 人工候选(本轮 git ls-remote 验证通过)
MANUAL_SUBSTR = {
    'ftb-teams': 'FTBTeam/FTB-Teams', 'ftb-library': 'FTBTeam/FTB-Library',
    'ftb-essentials': 'FTBTeam/FTB-Essentials', 'ftb-ranks': 'FTBTeam/FTB-Ranks',
    'ftb-xmod-compat': 'FTBTeam/FTB-XMod-Compat', 'ftb-chunks': 'FTBTeam/FTB-Chunks',
    'ftb-ultimine': 'FTBTeam/FTB-Ultimine', 'ftb任务增强': None,
    'cofh_core': 'CoFH/CoFHCore', 'cofhcore': 'CoFH/CoFHCore',
    'kotlinforforge': 'thedarkcolour/KotlinForForge',
    'configured-': 'MrCrayfish/Configured', 'framework-forge': 'MrCrayfish/Framework',
    'fastleafdecay': 'Olafski/FastLeafDecay',
    'fastfurnace': 'Shadows-of-Fire/FastFurnace', 'fastworkbench': 'Shadows-of-Fire/FastWorkbench',
    'apothicattributes': 'Shadows-of-Fire/Apothic-Attributes',
    'gpumemleakfix': 'someaddons/gpumemleakfix', 'alltheleaks': 'pietro-lopes/AllTheLeaks',
    'brewinandchewin': 'Monad-Modding/BrewinAndChewin',
    'common-networking': 'JTK222/common-networking',
    'lostcities-1.20': 'McJty/LostCities',
    'kubejs-create': 'KubeJS-Mods/KubeJS-Create',
    'createbigcannons': 'Cannoneers-of-Create/CreateBigCannons',
    'cupboard-1': 'someaddons/cupboard',
}

def apply(key):
    final = json.load(open(os.path.join(BASE, f'_{key}_final.json'), encoding='utf-8'))
    added_prev = added_manual = 0
    for fn, v in final.items():
        if v.get('gh'):
            continue
        nl = fn.lower()
        # 1) 人工候选
        hit = None
        for sub, repo in MANUAL_SUBSTR.items():
            if sub in nl and repo:
                hit = repo
                break
        if hit:
            v['gh'] = hit
            v['via'] = 'manual'
            added_manual += 1
            continue
        # 2) 复用上一包映射
        n = norm(fn)
        if n in prev_lookup:
            v['gh'] = prev_lookup[n]
            v['via'] = 'prev-pack'
            added_prev += 1
    # 校验新增的
    new_items = [(fn, v['gh']) for fn, v in final.items() if v.get('via') in ('manual', 'prev-pack')]
    def chk(it):
        fn, gh = it
        try:
            r = subprocess.run(['git', 'ls-remote', '--exit-code', '--heads', f'https://github.com/{gh}.git'],
                               capture_output=True, timeout=60)
            return fn, r.returncode == 0
        except Exception:
            return fn, False
    from concurrent.futures import ThreadPoolExecutor
    bad = []
    with ThreadPoolExecutor(max_workers=14) as ex:
        for fn, ok in ex.map(chk, new_items):
            if not ok:
                bad.append(fn)
    for fn in bad:
        final[fn]['gh_bad'] = final[fn]['gh']
        final[fn]['gh'] = None
        final[fn]['via'] = None
    json.dump(final, open(os.path.join(BASE, f'_{key}_final.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_gh = sum(1 for v in final.values() if v['gh'])
    print(f'{key}: +manual {added_manual}, +prev {added_prev}, 无效 {len(bad)} -> 共 {n_gh}/{len(final)}')

apply('fidr')
apply('starrail')
