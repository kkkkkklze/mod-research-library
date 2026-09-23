# -*- coding: utf-8 -*-
"""对 ATM10 剩余 mod 用 Modrinth 搜索找 source_url"""
import json, os, re, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
BASE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'zcode-mod-research/1.0'}
GH = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')

def search_one(item):
    pid, title = item
    q = re.sub(r'[\(\[（【].*?[\)\]）】]', '', title).strip()
    try:
        url = 'https://api.modrinth.com/v2/search?limit=3&query=' + urllib.parse.quote(q)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            hits = json.loads(r.read().decode())['hits']
    except Exception as e:
        return pid, None, f'search-err {e}'
    qn = re.sub(r'[^a-z0-9]', '', q.lower())
    for h in hits:
        hn = re.sub(r'[^a-z0-9]', '', h['title'].lower())
        sn = re.sub(r'[^a-z0-9]', '', h['slug'].lower())
        if not (hn == qn or sn == qn or qn in hn or hn in qn):
            continue
        try:
            purl = f"https://api.modrinth.com/v2/project/{h['slug']}"
            req2 = urllib.request.Request(purl, headers=UA)
            with urllib.request.urlopen(req2, timeout=30) as r2:
                p = json.loads(r2.read().decode())
            u = p.get('source_url')
            m = GH.search(u or '')
            if m:
                return pid, m.group(1).replace('.git', ''), 'modrinth'
        except Exception as e:
            return pid, None, f'proj-err {e}'
    return pid, None, 'no-match'

miss = json.load(open(os.path.join(BASE, '_atm10_miss.json'), encoding='utf-8'))
outpath = os.path.join(BASE, '_atm10_extra.json')
out = json.load(open(outpath, encoding='utf-8')) if os.path.exists(outpath) else {}
todo = [m for m in miss if str(m[0]) not in out]
print(f'待搜索: {len(todo)}', flush=True)
done = 0
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(search_one, m): m for m in todo}
    for fut in as_completed(futs):
        pid, gh, how = fut.result()
        out[str(pid)] = {'gh': gh, 'how': how}
        done += 1
        if done % 25 == 0:
            json.dump(out, open(outpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(f'  {done}/{len(todo)}', flush=True)
json.dump(out, open(outpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
ok = sum(1 for v in out.values() if v.get('gh'))
print(f'搜索命中: {ok}/{len(out)}', flush=True)
