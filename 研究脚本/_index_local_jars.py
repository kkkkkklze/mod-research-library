# 来源: ~/Downloads\_teacon\index_local.py
# 已归档到 研究脚本/（Downloads 会被清理）。脚本顶部的 HERE 常量默认仍指向 _teacon 数据目录，
# 如数据目录已清，把 HERE 改成新位置或改用 --out/参数。
# -*- coding: utf-8 -*-
"""为本地已安装的三个整合包建立 jar 索引(含 mods.toml 元数据)"""
import json, os, re, zipfile
from concurrent.futures import ThreadPoolExecutor

V = os.path.expanduser(r'~/Documents/PCL/PCL2/.minecraft/versions')
HERE = os.path.expanduser(r'~/Downloads/_teacon')
PACKS = ['璇穹之歌', '[FIDR]暗涌：深岩恐惧', 'All the Mods 10 - ATM10', 'TeaCon 2026']

SKIP = {'neoforge', 'minecraft', 'forge', 'fabricloader', 'kotlinforforge'}

def parse_toml(toml):
    own, names, urls, ver, authors = [], [], [], '', []
    section = ''
    for line in toml.splitlines():
        s = line.strip()
        if s.startswith('['):
            section = s
            continue
        if 'dependencies' in section:
            continue
        for pat, dst in ((r'modId\s*=\s*"([^"]+)"', own), (r'displayName\s*=\s*"([^"]+)"', names),
                         (r'(?:displayURL|issueTrackerURL)\s*=\s*"([^"]+)"', urls),
                         (r'authors\s*=\s*"([^"]*)"', authors), (r'credits\s*=\s*"([^"]*)"', authors)):
            m = re.match(pat, s)
            if m:
                dst.append(m.group(1))
                break
        m = re.match(r'version\s*=\s*"([^"]+)"', s)
        if m and not ver:
            ver = m.group(1)
    return own, names, urls, ver, authors

def meta(args):
    pack, jar = args
    p = os.path.join(V, pack, 'mods', jar)
    rec = {'pack': pack, 'jar': jar, 'size': os.path.getsize(p), 'modids': [], 'names': [], 'urls': [], 'version': ''}
    try:
        with zipfile.ZipFile(p) as z:
            names_ = z.namelist()
            for w in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
                if w in names_:
                    own, nm, urls, ver, au = parse_toml(z.read(w).decode('utf-8', 'ignore'))
                    rec['modids'] = [x for x in own if x not in SKIP]
                    rec['names'], rec['urls'], rec['version'] = nm, urls, ver
                    break
            if not rec['modids'] and 'fabric.mod.json' in names_:
                try:
                    j = json.loads(z.read('fabric.mod.json').decode('utf-8', 'ignore'))
                    if j.get('id') and j['id'] not in SKIP:
                        rec['modids'].append(j['id'])
                    if j.get('name'):
                        rec['names'].append(j['name'])
                    c = j.get('contact') or {}
                    rec['urls'] = [c[k] for k in ('sources', 'homepage', 'issues') if c.get(k)]
                except Exception:
                    pass
    except Exception as e:
        rec['err'] = str(e)[:60]
    BAD = ('change.me.to', 'example.invalid', 'mcreator.net')
    rec['urls'] = sorted(set(u for u in rec['urls'] if u and not any(b in u for b in BAD)))
    return rec

tasks = []
for pack in PACKS:
    md = os.path.join(V, pack, 'mods')
    if not os.path.isdir(md):
        print('跳过(无 mods):', pack)
        continue
    for jar in sorted(os.listdir(md)):
        if jar.endswith('.jar'):
            tasks.append((pack, jar))
print('待索引 jar:', len(tasks))
out = []
with ThreadPoolExecutor(max_workers=10) as ex:
    for r in ex.map(meta, tasks):
        out.append(r)
json.dump(out, open(os.path.join(HERE, 'local_index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(dict(Counter(r['pack'] for r in out)))
print('有 github 链接的:', sum(1 for r in out if any('github' in u for u in r['urls'])))
