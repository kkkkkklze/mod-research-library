# -*- coding: utf-8 -*-
"""合并三个来源 -> 最终 mod→GitHub 对照表, 并用 git ls-remote 批量校验"""
import json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(BASE, 'modrinth.index.json'), encoding='utf-8'))
rows = json.load(open(os.path.join(BASE, '_rows.json'), encoding='utf-8'))
jar_src = json.load(open(os.path.join(BASE, '_jar_sources.json'), encoding='utf-8'))

GH_RE = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')

def parse_gh(url):
    """从 url 中提取 owner/repo, 去掉结尾 .git / 斜杠; 排除 orgs/ 等非仓库路径"""
    if not url or 'toml-lang/toml' in url:
        return None
    m = GH_RE.search(url)
    if not m:
        return None
    p = m.group(1)
    p = re.sub(r'\.git$', '', p).rstrip('/')
    if p.split('/')[0] in ('orgs', 'features', 'about', 'topics', 'sponsors',
                           'marketplace', 'apps', 'settings', 'org', 'users'):
        return None
    return p

# ---- 1) Modrinth API 来源(从原始 source_url 重新解析)
by_file = {}
for r in rows:
    gh = parse_gh(r['source'])
    by_file[r['file']] = {
        'title': r['title'], 'gh': gh,
        'source': r['source'] if (r['source'] and 'toml-lang' not in r['source']) else None,
        'via': 'modrinth-api' if gh else None,
    }

# ---- 2) jar 元数据来源(从原始 urls 重新解析)
for fn, rec in jar_src.items():
    gh = None
    for u in rec.get('urls') or []:
        gh = parse_gh(u)
        if gh:
            break
    if fn in by_file:
        if not by_file[fn]['gh'] and gh:
            by_file[fn]['gh'] = gh
            by_file[fn]['via'] = 'jar-meta'
    else:
        by_file[fn] = {'title': fn, 'gh': gh, 'source': None, 'via': 'jar-meta' if gh else None}

# ---- 3) 人工整理(已用 GitHub 组织列表/搜索确认)
MANUAL = {
    'ftb-library-neoforge-2101.1.35.jar': 'FTBTeam/FTB-Library',
    'ftb-teams-neoforge-2101.1.11.jar': 'FTBTeam/FTB-Teams',
    '[FTB 任务] ftb-quests-neoforge-2101.1.34.jar': 'FTBTeam/FTB-Quests',
    'ftb-xmod-compat-neoforge-21.1.11.jar': 'FTBTeam/FTB-XMod-Compat',
    'kubejs-neoforge-2101.7.2-build.368.jar': 'KubeJS-Mods/KubeJS',
    'kotlinforforge-5.12.0-all.jar': 'thedarkcolour/KotlinForForge',
    'configured-neoforge-1.21.1-2.6.3.jar': 'MrCrayfish/Configured',
    'framework-neoforge-1.21.1-0.13.11.jar': 'MrCrayfish/Framework',
    'goblintraders-neoforge-1.21.1-1.11.2.jar': 'MrCrayfish/GoblinTraders',
    '[MrCrayfish 的家具：重制] refurbished_furniture-neoforge-1.21.1-1.0.22.jar': 'MrCrayfish/MrCrayfishFurnitureMod-Refurbished',
    'ApothicAttributes-1.21.1-2.10.1.jar': 'Shadows-of-Fire/Apothic-Attributes',
    '[神化] Apotheosis-1.21.1-8.7.0.jar': 'Shadows-of-Fire/Apotheosis',
    '[神化附魔] ApothicEnchanting-1.21.1-1.6.0.jar': 'Shadows-of-Fire/Apothic-Enchanting',
    '[神化刷怪笼] ApothicSpawners-1.21.1-1.4.0.jar': 'Shadows-of-Fire/Apothic-Spawners',
    '加速熔炉FastFurnace-1.21.1-9.0.1.jar': 'Shadows-of-Fire/FastFurnace',
    'l2complements-3.1.3.jar': 'Minecraft-LightLand/L2Complements',
    'l2hostility-3.0.18.jar': 'Minecraft-LightLand/L2Hostility',
    'irons_spellbooks-1.21.1-3.15.2.jar': 'Iron431/irons-spells-n-spellbooks',
    'irons_jewelry-1.21.1-1.6.0.jar': 'Iron431/irons-jewelry',
    'Retraining-neoforge-1.21-2.0.0.jar': 'Mrbysco/Retraining',
    'clientsort-neoforge-3.89.0-beta.2+1.21.1.jar': 'TerminalMC/ClientSort',
    '[局部气候&风暴] weather2-neoforge-1.21.0-2.8.7.jar': 'Corosauce/Weather2',
    'fastleafdecay-35.jar': 'Olafski/FastLeafDecay',
    'JustEnoughProfessions-neoforge-1.21.1-4.0.5.jar': 'Mrbysco/JustEnoughProfessions',
    'StructureCompass-1.21.1-4.2.1.jar': 'Mrbysco/StructureCompass',
    '傀儡装配modulargolems-3.1.43.jar': 'Minecraft-LightLand/ModularGolems',
    '内存泄漏alltheleaks-1.1.12+1.21.1-neoforge.jar': 'pietro-lopes/AllTheLeaks',
    '[修复GPU内存泄漏] gpumemleakfix-1.21-1.8.jar': 'someaddons/gpumemleakfix',
    'eccentrictome-1.21.1-1.2.0.jar': 'EccentricVamp/EccentricTome',
    '[冰火传说社区版] iceandfire-2.1.jar': 'IAFEnvoy/IceAndFire-CE',
    '冰火前置uranus-2.4.1-bugfix-1.21.1-neoforge.jar': 'IAFEnvoy/Uranus',
    '四季前置GlitchCore-neoforge-1.21.1-2.1.0.2.jar': 'Glitchfiend/GlitchCore',
    '[静谧四季／季节] SereneSeasons-neoforge-1.21.1-10.1.0.3.jar': 'Glitchfiend/SereneSeasons',
    '[遗体] corpse-neoforge-1.21.1-1.1.13.jar': 'henkelmax/corpse',
    '[稀有精英怪] infernalmobs-1.21.1.3NF.jar': 'AtomicStryker/atomicstrykers-minecraft-mods',
    '[生活调味料：胡萝卜版] solcarrot-1.21.1-1.16.6.jar': 'Cazsius/Spice-of-Life-Carrot-Edition',
    '[暮色森林] twilightforest-1.21.1-4.8.3345-universal.jar': 'TeamTwilight/twilightforest',
    '[探险者指南针 修改] explorerscompass-edited-1.21.1-3.0.4-neoforge.jar': 'MattCzyr/ExplorersCompass',
    '[找到我] findme-1.21.1-neoforge-1.3.0-test.7.jar': 'Buuz135/FindMe',
    # overrides 内自定义 mod
    '[背包] backpacked-neoforge-1.21.1-3.0.5.jar': 'MrCrayfish/Backpacked',
    '【[机械动力：交错电网] powergrid】[机械动力：交错电网] powergrid-mc1.21.1-0.6.0.1.jar': 'patryk3211/PowerGrid',
    '【[沉浸农艺] letsdo-farm and charm-neoforge】[沉浸农艺] letsdo-farm_and_charm-neoforge-1.1.23.jar': 'satisfyu/Let-s-Do-Hub',
    '【[沙滩派对] letsdo-beachparty-neoforge】[沙滩派对] letsdo-beachparty-neoforge-2.1.4.jar': 'satisfyu/Let-s-Do-Hub',
    '【[煨茶酝露] letsdo-herbalbrews-neoforge】[煨茶酝露] letsdo-herbalbrews-neoforge-1.1.3.jar': 'satisfyu/Let-s-Do-Hub',
    '【[盛节精酿] letsdo-brewery-neoforge】[盛节精酿] letsdo-brewery-neoforge-2.1.9.jar': 'satisfyu/Let-s-Do-Hub',
    '【[野性自然] letsdo-wildernature-neoforge】[野性自然] letsdo-wildernature-neoforge-1.1.5.jar': 'satisfyu/Let-s-Do-Hub',
    '【[小动物crittersandcompanions-neoforge】?': None,
    '【小动物crittersandcompanions-neoforge】小动物crittersandcompanions-neoforge-1.21.1-2.7.0.jar': 'bonsaistudi0s/CrittersAndCompanions',
    '【农夫乐事】[地牢乐事] neoforge-dungeonsdelight-1.21.1-1.5.0.jar': 'Yirmiri/Dungeons-Delight',
    '【蓝图工具sable-photomancy】蓝图工具sable-photomancy-1.0.1.jar': 'Rew1nd-dev/sable-schematic-api',
    'vanillin-neoforge-1.21.1-1.1.3-local.jar': 'Engine-Room/Flywheel',
    'do_a_barrel_roll-neoforge-3.7.3+1.21.jar': 'enjarai/do-a-barrel-roll',
    'lukis-crazy-chambers-1.0.3.jar': None,
    # 第二轮 GitHub 搜索 + jar 作者字段核对后确认
    '饮酒作乐BrewinAndChewin-neoforge-4.5.0+1.21.1.jar': 'Monad-Modding/BrewinAndChewin',
    'sootychimneys-neoforge-1.3.5.jar': 'mortuusars/SootyChimneys',
    'obscure_tooltips-neoforge-1.21.1-4.2.4.jar': 'ObscuriaLithium/obscure-tooltips',
    'structure_layout_optimizer-neoforge-1.0.12.jar': 'TelepathicGrunt/StructureLayoutOptimizer',
    '看看你在干什么前置coroutil-neoforge-1.21.0-1.3.9.jar': 'Corosauce/CoroUtil',
    'Searchables-neoforge-1.21.1-1.0.2.jar': 'Jaredlll08/Searchables',
    '信雅互联connector-2.0.0-beta.17+1.21.1-full.jar': 'Sinytra/Connector',
    '[烘焙坊] bakeries-1.21.1-NeoForge-1.0.3.jar': 'Renyigesai/bakery',
    '保存我的配方书smrb-1.0.0.jar': 'MoePus/SaveMyRecipeBook',
    '【小动物crittersandcompanions-neoforge】小动物crittersandcompanions-neoforge-1.21.1-2.7.0.jar': 'bonsaistudi0s/CrittersAndCompanions',
}
for fn, gh in MANUAL.items():
    if gh is None:
        continue
    if fn in by_file:
        by_file[fn]['gh'] = gh
        by_file[fn]['via'] = 'manual'
    else:
        by_file[fn] = {'title': fn, 'gh': gh, 'source': None, 'via': 'manual'}

# ---- 覆盖整合包真实文件名为准
final = {}
for f in data['files']:
    p = f['path']
    if not p.startswith('mods/'):
        continue
    name = p.split('/', 1)[1]
    rec = by_file.get(name, {'title': name, 'gh': None, 'source': None, 'via': None})
    final[name] = rec

# ---- 校验所有 github 链接
def check(item):
    fn, rec = item
    gh = rec['gh']
    if not gh:
        return fn, None
    r = subprocess.run(['git', 'ls-remote', '--exit-code', '--heads',
                        f'https://github.com/{gh}.git'], capture_output=True, timeout=90)
    return fn, (r.returncode == 0)

gh_list = [(fn, rec) for fn, rec in final.items() if rec['gh']]
print(f'校验 {len(gh_list)} 个 GitHub 仓库 ...', flush=True)
bad = []
with ThreadPoolExecutor(max_workers=16) as ex:
    for fn, ok in ex.map(check, gh_list):
        if ok is False:
            bad.append(fn)

print(f'无效链接: {len(bad)}')
for fn in bad:
    print('  BAD:', fn, final[fn]['gh'])
    final[fn]['gh_bad'] = final[fn]['gh']
    final[fn]['gh'] = None

json.dump(final, open(os.path.join(BASE, '_final.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

n = len(final)
with_gh = sum(1 for v in final.values() if v['gh'])
print(f'\n整合包 mod 总数: {n}')
print(f'找到 GitHub 仓库: {with_gh}')
print(f'未找到: {n - with_gh}')
