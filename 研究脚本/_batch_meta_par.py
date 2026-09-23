# -*- coding: utf-8 -*-
"""并行版: 批量从 jar 元数据提取源码地址"""
import json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _jar_meta import jar_meta, extract_urls

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, '_jar_sources.json')

data = json.load(open(os.path.join(BASE, 'modrinth.index.json'), encoding='utf-8'))
rows = json.load(open(os.path.join(BASE, '_rows.json'), encoding='utf-8'))

have_gh = set(r['file'] for r in rows if r['gh'])

todo = []
for f in data['files']:
    p = f['path']
    if not p.startswith('mods/'):
        continue
    name = p.split('/', 1)[1]
    if name in have_gh:
        continue
    cand = []
    for u in f['downloads']:
        if 'cdn.modrinth.com' in u:
            cand.append(u)
        elif 'forgecdn.net' in u:
            cand.append(u.replace('edge.forgecdn.net', 'mediafilez.forgecdn.net'))
    if cand:
        todo.append({'name': name, 'urls': cand})

results = {}
if os.path.exists(OUT):
    results = json.load(open(OUT, encoding='utf-8'))

pending = [t for t in todo if t['name'] not in results]
print(f'total {len(todo)}, pending {len(pending)}', flush=True)

GH = re.compile(r'https?://github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')
GH_BAD = re.compile(r'(change\.me\.to|example\.invalid|github\.com/(features|about|topics|sponsors|orgs|marketplace|apps|settings))')

def work(item):
    rec = {'url_tried': None, 'modids': [], 'urls': [], 'gh': None, 'err': None}
    for u in item['urls']:
        rec['url_tried'] = u
        try:
            m = jar_meta(u)
            ex = extract_urls(m)
            rec['modids'] = ex['modids']
            rec['urls'] = ex['urls']
            for x in ex['urls']:
                mm = GH.match(x)
                if mm and not GH_BAD.search(x):
                    rec['gh'] = mm.group(1).rstrip('.git')
                    break
            if not rec['gh']:
                for fn, txt in m.items():
                    for mm in GH.finditer(txt):
                        cand = mm.group(1).rstrip('.git')
                        if not GH_BAD.search(mm.group(0)):
                            rec['gh'] = cand
                            break
                    if rec['gh']:
                        break
            rec['err'] = None
            break
        except Exception as e:
            rec['err'] = f'{type(e).__name__}: {e}'
    return item['name'], rec

lock = __import__('threading').Lock()
done = 0
with ThreadPoolExecutor(max_workers=10) as ex_:
    futs = {ex_.submit(work, t): t for t in pending}
    for fut in as_completed(futs):
        name, rec = fut.result()
        with lock:
            results[name] = rec
            done += 1
            if done % 5 == 0:
                json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            status = rec['gh'] or ('ERR' if rec['err'] else 'no-gh')
            print(f"[{done}/{len(pending)}] {name[:52]:<54} {status}", flush=True)

json.dump(results, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
n_gh = sum(1 for v in results.values() if v.get('gh'))
print(f'DONE  with github: {n_gh}/{len(results)}', flush=True)
