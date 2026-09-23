# 来源: ~/Downloads\_teacon\index_rest_packs.py
# 已归档到 研究脚本/（Downloads 会被清理）。脚本顶部的 HERE 常量默认仍指向 _teacon 数据目录，
# 如数据目录已清，把 HERE 改成新位置或改用 --out/参数。
# -*- coding: utf-8 -*-
"""索引剩余整合包: 逐包提取 mod 列表(含元数据) + 汇总新仓库 + 生成每包清单"""
import json, os, re, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

V = os.path.expanduser(r'~/Documents/PCL/PCL2/.minecraft/versions')
HERE = os.path.expanduser(r'~/Downloads/_teacon')
WS = r''
TBL = os.path.join(WS, '对照表')
os.makedirs(TBL, exist_ok=True)

# 已处理的包(不再索引)
DONE_PACKS = {'璇穹之歌', '[FIDR]暗涌：深岩恐惧', 'All the Mods 10 - ATM10', 'TeaCon 2026',
              '元年', '1.20.1-Forge_47.4.23'}

SKIP = {'neoforge', 'minecraft', 'forge', 'fabricloader', 'kotlinforforge'}

def parse_toml(txt):
    rec = {'modids': [], 'names': [], 'urls': [], 'version': '', 'authors': []}
    sec = ''
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith('['):
            sec = s; continue
        if 'dependencies' in sec: continue
        m = re.match(r'modId\s*=\s*"([^"]+)"', s)
        if m and m.group(1) not in SKIP: rec['modids'].append(m.group(1)); continue
        m = re.match(r'displayName\s*=\s*"([^"]+)"', s)
        if m: rec['names'].append(m.group(1)); continue
        m = re.match(r'(?:displayURL|issueTrackerURL)\s*=\s*"([^"]+)"', s)
        if m: rec['urls'].append(m.group(1)); continue
        m = re.match(r'(?:authors|credits)\s*=\s*"([^"]*)"', s)
        if m: rec['authors'].append(m.group(1)); continue
        m = re.match(r'version\s*=\s*"([^"]+)"', s)
        if m and not rec['version']: rec['version'] = m.group(1)
    return rec

def parse_mcmod(txt):
    """Forge <=1.12.2 的 mcmod.info: JSON 数组(或单对象)"""
    rec = {'modids': [], 'names': [], 'urls': [], 'version': '', 'authors': []}
    try:
        j = json.loads(txt)
    except Exception:
        try:
            j = json.loads(re.sub(r',\s*([}\]])', r'\1', txt))   # 容忍尾随逗号
        except Exception:
            return rec
    for e in (j if isinstance(j, list) else [j]):
        if not isinstance(e, dict):
            continue
        mid = e.get('modid') or e.get('modId')
        if mid and mid not in SKIP: rec['modids'].append(mid)
        if e.get('name'): rec['names'].append(e['name'])
        for k in ('url', 'updateJSON', 'displayURL'):
            v = e.get(k)
            if isinstance(v, str) and v: rec['urls'].append(v)
        if isinstance(e.get('version'), str): rec['version'] = rec['version'] or e['version']
        al = e.get('authorList')
        if isinstance(al, list): rec['authors'] += [str(a) for a in al if a]
        elif isinstance(e.get('author'), str): rec['authors'].append(e['author'])
    return rec

def parse_manifest(txt):
    """META-INF/MANIFEST.MF: 折行续行 + 找 URL 属性(老 mod 只有这里带地址)"""
    flat, out = {}, None
    for raw in txt.splitlines():
        if raw.startswith(' ') and out:      # 续行
            flat[out] += raw[1:]
            continue
        if ':' not in raw: continue
        k, _, v = raw.partition(':')
        out = k.strip()
        flat[out] = v.strip()
    urls = [v for k, v in flat.items()
            if re.search(r'(URL|Homepage|Website|Source|Github)', k, re.I) and 'github.com' in v.lower()]
    return urls

def meta(args):
    pack, jar = args
    p = os.path.join(V, pack, 'mods', jar)
    rec = {'pack': pack, 'jar': jar, 'size': os.path.getsize(p),
           'modids': [], 'names': [], 'urls': [], 'version': '', 'authors': []}
    try:
        with zipfile.ZipFile(p) as z:
            names = z.namelist()
            for w in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
                if w in names:
                    rec.update({k: v for k, v in parse_toml(z.read(w).decode('utf-8', 'ignore')).items()})
                    break
            if not rec['modids'] and 'fabric.mod.json' in names:
                j = json.loads(z.read('fabric.mod.json').decode('utf-8', 'ignore'))
                if j.get('id') and j['id'] not in SKIP: rec['modids'].append(j['id'])
                if j.get('name'): rec['names'].append(j['name'])
                c = j.get('contact') or {}
                rec['urls'] += [c[k] for k in ('sources', 'homepage', 'issues') if c.get(k)]
                if isinstance(j.get('version'), str): rec['version'] = rec['version'] or j['version']
            if not rec['modids'] and 'mcmod.info' in names:
                rec2 = parse_mcmod(z.read('mcmod.info').decode('utf-8', 'ignore'))
                for k in rec2:
                    if isinstance(rec2[k], list): rec[k] = rec[k] + [x for x in rec2[k] if x not in rec[k]]
                    elif rec2[k] and not rec[k]: rec[k] = rec2[k]
            if not rec['urls'] and 'META-INF/MANIFEST.MF' in names:
                rec['urls'] += parse_manifest(z.read('META-INF/MANIFEST.MF').decode('utf-8', 'ignore'))
    except Exception as e:
        rec['err'] = str(e)[:50]
    BAD = ('change.me.to', 'example.invalid', 'mcreator.net')
    rec['urls'] = sorted(set(u for u in rec['urls'] if u and not any(b in u for b in BAD)))
    return rec

packs = [d for d in sorted(os.listdir(V)) if os.path.isdir(os.path.join(V, d))]
packs = [p for p in packs if p not in DONE_PACKS and os.path.isdir(os.path.join(V, p, 'mods'))]
print('剩余整合包:', len(packs))
tasks = []
for p in packs:
    for jar in sorted(os.listdir(os.path.join(V, p, 'mods'))):
        if jar.endswith('.jar'):
            tasks.append((p, jar))
print('待索引 jar:', len(tasks))

out = []
with ThreadPoolExecutor(max_workers=12) as ex:
    for i, r in enumerate(ex.map(meta, tasks), 1):
        out.append(r)
        if i % 500 == 0:
            print('  %d/%d' % (i, len(tasks)), flush=True)
json.dump(out, open(os.path.join(HERE, 'index_rest_packs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

GH = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')
def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

# 已有映射(四包 + TeaCon + 本机补漏) 
known = set()
for f in ('_union_repos.json',):
    p = os.path.join(WS, '分析报告', '_分析报告', f)
    if os.path.exists(p):
        known |= set(json.load(open(p, encoding='utf-8')).keys())
try:
    known |= set(json.load(open(os.path.join(HERE, 'final_rows.json'), encoding='utf-8'))[0].keys())
except Exception:
    pass
known_norm = set(norm(x.split('/')[-1]) for x in known)
# 含本机四包所有 jar 的 modid
for f in ('local_index.json', 'index_rest_packs.json'):
    for r in json.load(open(os.path.join(HERE, f), encoding='utf-8')):
        for m in r['modids']:
            known_norm.add(norm(m))

# 逐包清单 + 新仓库
new_repos = {}
pack_stats = {}
for p in packs:
    rows = [r for r in out if r['pack'] == p]
    withrepo = 0
    L = ['# %s — Mod 清单' % p, '', '- mod 数: **%d**' % len(rows), '',
         '| # | Mod 名 | mod id | 版本 | 文件 | GitHub |', '|---|---|---|---|---|---|']
    for i, r in enumerate(sorted(rows, key=lambda x: (x['names'][0] if x['names'] else x['jar']).lower()), 1):
        nm = (r['names'][0] if r['names'] else re.sub(r'\.jar$', '', r['jar'])).replace('|', '/')
        gh = ''
        for u in r['urls']:
            m = GH.search(u)
            if m:
                gh = m.group(1).rstrip('/').replace('.git', '')
                break
        if gh:
            withrepo += 1
            if norm(gh.split('/')[-1]) not in known_norm:
                new_repos[gh] = (nm, p)
        L.append('| %d | %s | %s | %s | `%s` | %s |' % (i, nm, ','.join(r['modids'][:2]), r['version'],
                                                        r['jar'][:60], ('https://github.com/' + gh) if gh else '—'))
    open(os.path.join(TBL, 'Mod清单__%s.md' % re.sub(r'[\\/:*?"<>|]', '_', p)), 'w', encoding='utf-8').write('\n'.join(L))
    pack_stats[p] = (len(rows), withrepo)

print()
print('=== 各包 mod 数 / 元数据里带仓库的 ===')
for p, (n, w) in sorted(pack_stats.items(), key=lambda x: -x[1][0]):
    print('  %-52s %4d 个 mod，带仓库 %3d' % (p[:52], n, w))
print()
print('总计: %d 个 mod（去重前），新仓库（不在已有映射里）: %d' % (sum(n for n, _ in pack_stats.values()), len(new_repos)))
json.dump({'stats': pack_stats, 'new_repos': new_repos}, open(os.path.join(HERE, 'rest_packs_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open(os.path.join(HERE, 'rest_new_repos.md'), 'w', encoding='utf-8') as f:
    f.write('# 剩余整合包中发现的新仓库（不在已有 591/164 映射里）\n\n| # | 仓库 | Mod | 所在包 |\n|---|---|---|---|\n')
    for i, (gh, (nm, p)) in enumerate(sorted(new_repos.items(), key=lambda x: x[1][1]), 1):
        f.write('| %d | https://github.com/%s | %s | %s |\n' % (i, gh, nm, p))
print('已写: 对照表/Mod清单__<包>.md × %d, rest_new_repos.md' % len(packs))
