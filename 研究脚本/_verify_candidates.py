# -*- coding: utf-8 -*-
"""批量验证候选 GitHub 仓库是否真实存在(git ls-remote)"""
import subprocess, sys
from concurrent.futures import ThreadPoolExecutor

CANDIDATES = {
    # FTB 系列
    'ftb-library-neoforge-2101.1.35.jar': 'FTBTeam/FTB-Library',
    'ftb-teams-neoforge-2101.1.11.jar': 'FTBTeam/FTB-Teams',
    '[FTB 任务] ftb-quests-neoforge-2101.1.34.jar': 'FTBTeam/FTB-Quests',
    'ftb-xmod-compat-neoforge-21.1.11.jar': 'FTBTeam/FTB-XMod-Compat',
    # 其他知名 mod
    'kubejs-neoforge-2101.7.2-build.368.jar': 'KubeJS-Mods/KubeJS',
    'kotlinforforge-5.12.0-all.jar': 'tth05/KotlinForForge',
    'configured-neoforge-1.21.1-2.6.3.jar': 'MrCrayfish/Configured',
    'framework-neoforge-1.21.1-0.13.11.jar': 'MrCrayfish/Framework',
    'goblintraders-neoforge-1.21.1-1.11.2.jar': 'MrCrayfish/GoblinTraders',
    '[MrCrayfish 的家具：重制] refurbished_furniture-neoforge-1.21.1-1.0.22.jar': 'MrCrayfish/Refurbished-Furniture',
    'ApothicAttributes-1.21.1-2.10.1.jar': 'Shadows-of-Fire/ApothicAttributes',
    '加速熔炉FastFurnace-1.21.1-9.0.1.jar': 'Shadows-of-Fire/FastFurnace',
    'l2complements-3.1.3.jar': 'Minecraft-LightLand/L2Complements',
    'l2hostility-3.0.18.jar': 'Minecraft-LightLand/L2Hostility',
    'Retraining-neoforge-1.21-2.0.0.jar': 'Mrbysco/Retraining',
    'clientsort-neoforge-3.89.0-beta.2+1.21.1.jar': 'TerminalMC/ClientSort',
    '[局部气候&风暴] weather2-neoforge-1.21.0-2.8.7.jar': 'Corosauce/Weather2',
    'fastleafdecay-35.jar': 'olafskiii/FastLeafDecay',
    'JustEnoughProfessions-neoforge-1.21.1-4.0.5.jar': 'Mrbysco/JustEnoughProfessions',
    'StructureCompass-1.21.1-4.2.1.jar': 'Mrbysco/StructureCompass',
    '傀儡装配modulargolems-3.1.43.jar': 'Minecraft-LightLand/ModularGolems',
    '内存泄漏alltheleaks-1.1.12+1.21.1-neoforge.jar': 'AllTheMods/AllTheLeaks',
    '[修复GPU内存泄漏] gpumemleakfix-1.21-1.8.jar': 'MrCrayfish/GPUMemoryLeakFix',
    'irons_jewelry-1.21.1-1.6.0.jar': 'Iron431/Irons-Jewelry',
    'atlas_api-1.21.1-1.2.0.jar': 'Iron431/Atlas-API',
    'powerful_dummy-21-0.0.9-hotfix.jar': 'AlexModGuy/PowerfulDummy',
    'eccentrictome-1.21.1-1.2.0.jar': 'EccentricVamp/EccentricTome',
    '[工业平台] Industrial Platform-1.21.1-1.8.0.jar': 'IndustrialPlatform/IndustrialPlatform',
    '保存我的配方书smrb-1.0.0.jar': 'Fuzss/SaveMyRecipeBook',
    '味蕾乐事tastejournal-neoforge-1.21.1-latest.jar': 'DragonsPlusMinecraft/TasteJournal',
    '乡野neoforge1.21.1-7.20.jar': 'MCreator/roadtothedream',
}

def check(item):
    fn, repo = item
    url = f'https://github.com/{repo}.git'
    r = subprocess.run(['git', 'ls-remote', '--exit-code', '--heads', url],
                       capture_output=True, timeout=90)
    ok = r.returncode == 0
    try:
        txt = r.stdout.decode('utf-8', 'ignore')
    except Exception:
        txt = ''
    branch = ''
    if ok:
        branches = [l.split('refs/heads/')[-1] for l in txt.splitlines() if 'refs/heads/' in l]
        pref = [b for b in branches if b in ('1.21.1', '1.21', 'main', 'master', 'dev')]
        branch = (pref[0] if pref else (branches[0] if branches else ''))
    return fn, repo, ok, branch

with ThreadPoolExecutor(max_workers=8) as ex:
    for fn, repo, ok, branch in ex.map(check, CANDIDATES.items()):
        print(('OK  ' if ok else 'FAIL') + f'  {repo:<45} branch={branch:<10} {fn[:40]}')
