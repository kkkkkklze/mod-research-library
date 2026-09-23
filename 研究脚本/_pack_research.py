# -*- coding: utf-8 -*-
"""通用整合包 mod→GitHub 研究脚本
用法: python _pack_research.py <pack_key> <pack_json_path>
流程: Modrinth API 批量查询 -> jar 元数据 Range 提取补齐 -> git ls-remote 校验
输出: _<key>_final.json / _<key>_projects.json
"""
import json, os, re, sys, time, subprocess, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _jar_meta import jar_meta, extract_urls

BASE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'zcode-mod-research/1.0'}
GH_RE = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')
BAD_OWNERS = {'orgs', 'features', 'about', 'topics', 'sponsors', 'marketplace',
              'apps', 'settings', 'org', 'users', 'collections'}


def parse_gh(url):
    if not url or 'toml-lang/toml' in url:
        return None
    m = GH_RE.search(url)
    if not m:
        return None
    p = re.sub(r'\.git$', '', m.group(1)).rstrip('/')
    if p.split('/')[0].lower() in BAD_OWNERS:
        return None
    return p


def http_json(url, retries=3):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if a == retries - 1:
                raise
            time.sleep(2)


def modrinth_projects(ids):
    out = {}
    B = 60
    ids = sorted(set(ids))
    for i in range(0, len(ids), B):
        batch = ids[i:i + B]
        url = 'https://api.modrinth.com/v2/projects?ids=' + urllib.parse.quote(json.dumps(batch))
        for a in range(4):
            try:
                for p in http_json(url):
                    out[p['id']] = {
                        'slug': p.get('slug'), 'title': p.get('title'),
                        'source_url': p.get('source_url'), 'issues_url': p.get('issues_url'),
                        'downloads': p.get('downloads'), 'followers': p.get('followers'),
                        'license': (p.get('license') or {}).get('id'),
                        'loaders': p.get('loaders'),
                    }
                break
            except Exception as e:
                print(f'  modrinth batch {i//B} retry {a}: {e}', flush=True)
                time.sleep(3)
    return out


def load_pack(path):
    d = json.load(open(path, encoding='utf-8'))
    mods = []
    for f in d['files']:
        p = f['path']
        if not p.startswith('mods/'):
            continue
        mid, cand = None, []
        for u in f['downloads']:
            m = re.search(r'cdn\.modrinth\.com/data/([^/]+)/', u)
            if m and not mid:
                mid = m.group(1)
            if 'cdn.modrinth.com' in u:
                cand.append(u)
            elif 'forgecdn.net' in u:
                cand.append(u.replace('edge.forgecdn.net', 'mediafilez.forgecdn.net'))
        mods.append({'path': p, 'file': p.split('/', 1)[1], 'mid': mid, 'urls': cand})
    return d, mods


def jar_meta_worker(item):
    rec = {'url': None, 'modids': [], 'urls': [], 'gh': None, 'err': None}
    for u in item['urls']:
        rec['url'] = u
        try:
            m = jar_meta(u)
            ex = extract_urls(m)
            rec['modids'] = ex['modids']
            rec['urls'] = ex['urls']
            for x in ex['urls']:
                g = parse_gh(x)
                if g:
                    rec['gh'] = g
                    break
            if not rec['gh']:
                for fn, txt in m.items():
                    for mm in GH_RE.finditer(txt):
                        g = parse_gh(mm.group(0))
                        if g:
                            rec['gh'] = g
                            break
                    if rec['gh']:
                        break
            rec['err'] = None
            break
        except Exception as e:
            rec['err'] = f'{type(e).__name__}: {e}'
    return rec


def verify_all(items):
    def chk(it):
        fn, gh = it
        r = subprocess.run(['git', 'ls-remote', '--exit-code', '--heads', f'https://github.com/{gh}.git'],
                            capture_output=True, timeout=90)
        return fn, r.returncode == 0
    bad = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        for fn, ok in ex.map(chk, items):
            if not ok:
                bad.append(fn)
    return bad


def main():
    key, pack_path = sys.argv[1], sys.argv[2]
    pack, mods = load_pack(pack_path)
    print(f'== {pack["name"]} v{pack["versionId"]} ==  mods: {len(mods)}', flush=True)

    # 1) Modrinth API
    mids = [m['mid'] for m in mods if m['mid']]
    proj_cache = os.path.join(BASE, f'_{key}_projects.json')
    projects = {}
    if os.path.exists(proj_cache):
        projects = json.load(open(proj_cache, encoding='utf-8'))
    need = [i for i in mids if i not in projects]
    if need:
        print(f'查询 Modrinth API: {len(need)} 个项目', flush=True)
        projects.update(modrinth_projects(need))
        json.dump(projects, open(proj_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # 2) 组装 + jar 元数据补齐
    final = {}
    for m in mods:
        p = projects.get(m['mid']) if m['mid'] else None
        gh = parse_gh(p['source_url']) if p else None
        final[m['file']] = {
            'path': m['path'],
            'title': (p or {}).get('title') or m['file'],
            'gh': gh, 'source': (p or {}).get('source_url'),
            'downloads': (p or {}).get('downloads'),
            'license': (p or {}).get('license'),
            'via': 'modrinth-api' if gh else None,
        }

    todo = [m for m in mods if not final[m['file']]['gh'] and m['urls']]
    print(f'需 jar 元数据补齐: {len(todo)}', flush=True)
    meta_cache = os.path.join(BASE, f'_{key}_jarmeta.json')
    meta = json.load(open(meta_cache, encoding='utf-8')) if os.path.exists(meta_cache) else {}
    pending = [t for t in todo if t['file'] not in meta]
    done = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(jar_meta_worker, t): t for t in pending}
        for fut in as_completed(futs):
            t = futs[fut]
            meta[t['file']] = fut.result()
            done += 1
            if done % 10 == 0:
                json.dump(meta, open(meta_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print(f'  jar 元数据 {done}/{len(pending)}', flush=True)
    json.dump(meta, open(meta_cache, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    for fn, rec in meta.items():
        if fn in final and not final[fn]['gh'] and rec.get('gh'):
            final[fn]['gh'] = rec['gh']
            final[fn]['via'] = 'jar-meta'

    # 3) 校验
    gh_items = [(fn, v['gh']) for fn, v in final.items() if v['gh']]
    print(f'校验 {len(gh_items)} 个仓库 ...', flush=True)
    for fn in verify_all(gh_items):
        final[fn]['gh_bad'] = final[fn]['gh']
        final[fn]['gh'] = None
        final[fn]['via'] = None

    json.dump(final, open(os.path.join(BASE, f'_{key}_final.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n_gh = sum(1 for v in final.values() if v['gh'])
    print(f'== 结果: {n_gh}/{len(final)} 找到并验证 GitHub; 未找到 {len(final)-n_gh}', flush=True)


if __name__ == '__main__':
    main()
