# -*- coding: utf-8 -*-
"""ATM10: CurseForge projectID -> 名称(cfwidget) -> GitHub(复用已有映射 / Modrinth 搜索)"""
import json, os, re, sys, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'zcode-mod-research/1.0'}

def cfw(pid):
    url = f'https://api.cfwidget.com/{pid}'
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            return pid, {'title': d.get('title'), 'slug': d.get('slug'),
                         'url': (d.get('urls') or {}).get('curseforge'),
                         'downloads': d.get('downloads')}
        except Exception as e:
            if a == 2:
                return pid, {'err': f'{type(e).__name__}: {e}'}
            time.sleep(2)

def modrinth_search(name):
    url = 'https://api.modrinth.com/v2/search?limit=3&query=' + urllib.parse.quote(name)
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                hits = json.loads(r.read().decode())['hits']
            for h in hits:
                if h.get('project_id'):
                    purl = f"https://api.modrinth.com/v2/project/{h['slug']}"
                    req2 = urllib.request.Request(purl, headers=UA)
                    with urllib.request.urlopen(req2, timeout=30) as r2:
                        p = json.loads(r2.read().decode())
                    if p.get('source_url'):
                        return p['source_url']
            return None
        except Exception:
            if a == 2:
                return None
            time.sleep(2)

def norm(name):
    n = (name or '').lower()
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def main():
    ids = json.load(open(os.path.join(BASE, '_atm10_ids.json')))['ids']
    cache = os.path.join(BASE, '_atm10_cf.json')
    data = json.load(open(cache, encoding='utf-8')) if os.path.exists(cache) else {}
    todo = [i for i in ids if str(i) not in data]
    print(f'cfwidget 待查: {len(todo)}', flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(cfw, i): i for i in todo}
        for fut in as_completed(futs):
            pid, info = fut.result()
            data[str(pid)] = info
            done += 1
            if done % 25 == 0:
                json.dump(data, open(cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print(f'  {done}/{len(todo)}', flush=True)
            time.sleep(0.15)
    json.dump(data, open(cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for v in data.values() if v and v.get('title'))
    print(f'名称解析成功: {ok}/{len(ids)}', flush=True)

    # 名称 -> 已有映射
    known = {}
    for f in ('_final.json', '_fidr_final.json', '_starrail_final.json'):
        p = os.path.join(BASE, f)
        if not os.path.exists(p):
            continue
        for fn, v in json.load(open(p, encoding='utf-8')).items():
            if v.get('gh'):
                known.setdefault(norm(v.get('title')), v['gh'])
                known.setdefault(norm(fn), v['gh'])
    # 手动别名(名称->仓库)
    alias = {
        'justenoughitems': 'mezz/JustEnoughItems', 'jei': 'mezz/JustEnoughItems',
        'jade': 'Snownee/Jade', 'resourcefullib': 'Team-Resourceful/ResourcefulLib',
        'mekanism': 'mekanism/Mekanism', 'appliedenergistics2': 'AppliedEnergistics/Applied-Energistics-2',
        'botania': 'VazkiiMods/Botania', 'immersiveengineering': 'BluSunrize/ImmersiveEngineering',
        'thermalexpansion': 'CoFH/ThermalExpansion', 'thermalexpansionlegacy': 'CoFH/ThermalExpansion',
        'create': 'Creators-of-Create/Create', 'apotheosis': 'Shadows-of-Fire/Apotheosis',
        'mysticalagriculture': 'BlakeBr0/MysticalAgriculture', 'powah': 'owmii/Powah',
        'industrialforegoing': 'Buuz135/Industrial-Foregoing', 'xnet': 'McJty/XNet',
        'rftoolsbase': 'McJty/RFToolsBase', 'rftoolsbuilder': 'McJty/RFToolsBuilder',
        'mffs': 'McJty/MFFS', 'deepresonance': 'McJty/DeepResonance',
        'thermalcultivation': 'CoFH/ThermalCultivation', 'thermaldynamics': 'CoFH/ThermalDynamics',
        'thermalfoundation': 'CoFH/ThermalFoundation', 'thermalinnovation': 'CoFH/ThermalInnovation',
        'thermalintegration': 'CoFH/ThermalIntegration', 'thermallocomotion': 'CoFH/ThermalLocomotion',
        'thermalfoundationlegacy': 'CoFH/ThermalFoundation', 'cofhcore': 'CoFH/CoFHCore',
        'ensorcellation': 'CoFH/Ensorcellation', 'arsnouveau': 'baileyholl/Ars-Nouveau',
        'occultism': 'klikli-dev/occultism', 'enderio': 'Team-EnderIO/EnderIO',
        'fluxnetworks': 'sonar-rsm/Flux-Networks', 'mobgrindingutils': 'vadis365/Mob-Grinding-Utils',
        'agricraft': 'AgriCraft/AgriCraft', 'extendedcrafting': 'BlakeBr0/ExtendedCrafting',
        'bloodmagic': 'WayofTime/BloodMagic', 'roots': 'MysticMods/Roots',
        'ironsspellsnspellbooks': 'Iron431/irons-spells-n-spellbooks',
        'ironjetpacks': 'BlakeBr0/IronJetpacks', 'cucumber': 'BlakeBr0/Cucumber',
        'mysticalagradditions': 'BlakeBr0/MysticalAgradditions',
        'botanypots': 'Darkhax-Minecraft/BotanyPots', 'extendedcrafting': 'BlakeBr0/ExtendedCrafting',
        'pneumaticcraft': 'TeamPneumatic/pnc-repressurized', 'pipez': 'henkelmax/pipez',
        'modularrouters': 'desht/ModularRouters', 'darkutils': 'Darkhax-Minecraft/DarkUtils',
        'bigreactors': 'erogenousbeef-zz/BigReactors', 'extremereactors': 'ZeroNoRyouki/ExtremeReactors',
        'torchmaster': 'xalcon/torchmaster', 'silentgear': 'SilentChaos512/Silent-Gear',
        'storagedrawers': 'jaquadro/StorageDrawers', 'framedblocks': 'XFactHD/FramedBlocks',
        'sophisticatedbackpacks': 'P3pp3rF1y/SophisticatedBackpacks',
        'sophisticatedcore': 'P3pp3rF1y/SophisticatedCore',
        'sophisticatedstorage': 'P3pp3rF1y/SophisticatedStorage',
        'functionalstorage': 'Buuz135/Functional-Storage', 'titanium': 'Buuz135/titanium',
        'constructionwand': 'Theta-Dev/ConstructionWand', 'waystones': 'TwelveIterations/Waystones',
        'balm': 'TwelveIterations/Balm', 'ironfurnaces': 'XxAndroidxX/IronFurnaces',
        'xycraft': 'XyCraft-Mods/XyCraft', 'xycraftmachines': 'XyCraft-Mods/XyCraft',
        'arsenergistique': 'Ridanisaurus/Ars-Energistique',
        'railcraft': 'Railcraft/Railcraft', 'forestry': 'ForestryMC/ForestryMC',
        'integrateddynamics': 'CyclopsMC/IntegratedDynamics', 'integratedcrafting': 'CyclopsMC/IntegratedCrafting',
        'integratedterminals': 'CyclopsMC/IntegratedTerminals', 'integratedtunnels': 'CyclopsMC/IntegratedTunnels',
        'cyclopscore': 'CyclopsMC/CyclopsCore', 'commoncapabilities': 'CyclopsMC/CommonCapabilities',
        'evilcraft': 'CyclopsMC/EvilCraft', 'enderstorage': 'gigabit101/EnderStorage',
        'morered': 'Commoble/MoreRed', 'littlelogistics': 'Commoble/LittleLogistics',
        'elevatorid': 'VsnGamer/ElevatorMod', 'itemcollectors': 'SuperMartijn642/ItemCollectors',
        'supermartijn642scorelib': 'SuperMartijn642/SuperMartijn642sCoreLib',
        'supermartijn642sconfiglib': 'SuperMartijn642/SuperMartijn642sConfigLib',
        'fusion': 'SuperMartijn642/Fusion', 'trashcans': 'SuperMartijn642/TrashCans',
        'gravestone': 'henkelmax/gravestone-mod', 'simplemagnets': 'SuperMartijn642/SimpleMagnets',
        'cookingforblockheads': 'TwelveIterations/CookingForBlockheads',
        'netherportalfix': 'TwelveIterations/NetherPortalFix',
        'laserio': 'Direwolf20-MC/LaserIO', 'titanium': 'Buuz135/titanium',
        'cabletiers': 'Ultramega/CableTiers', 'modernindustrialization': 'Technici4n/Modern-Industrialization',
        'mekanismgenerators': 'mekanism/Mekanism', 'mekanismtools': 'mekanism/Mekanism',
        'mekanismadditions': 'mekanism/Mekanism', 'mekanismextras': 'mekanism/Mekanism',
        'fluxnetworks': 'sonar-rsm/Flux-Networks', 'hostilenetworks': 'shBLOCK/Hostile-Neural-Networks',
        'arsnouveau': 'baileyholl/Ars-Nouveau', 'deeperdarker': 'ObliviousSpartan/DeeperAndDarker',
        'thebumblezone': 'TelepathicGrunt/Bumblezone', 'blueprint': 'TeamAbnormals/Blueprint',
        'curios': 'TheIllusiveC4/Curios', 'patchouli': 'VazkiiMods/Patchouli',
    }
    miss = []
    results = {}
    for pid_s, info in data.items():
        if not info or not info.get('title'):
            continue
        t = info['title']
        key = norm(t)
        gh = known.get(key)
        if not gh:
            # 去括号后缀再试
            k2 = norm(re.sub(r'[\(\[（【].*?[\)\]）】]', '', t))
            gh = known.get(k2)
        if not gh:
            for a, repo in alias.items():
                if a in key or a in norm(info.get('slug')):
                    gh = repo
                    break
        results[pid_s] = {'title': t, 'slug': info.get('slug'), 'gh': gh, 'via': 'known' if gh else None}
        if not gh:
            miss.append((pid_s, t))
    json.dump(results, open(os.path.join(BASE, '_atm10_final.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'已有映射命中: {sum(1 for v in results.values() if v["gh"])}/{len(results)}', flush=True)
    print(f'剩余待搜索: {len(miss)}', flush=True)
    json.dump(miss, open(os.path.join(BASE, '_atm10_miss.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
