# 来源: ~/Downloads\_teacon\decompile_downloaded.py
# 已归档到 研究脚本/（Downloads 会被清理）。脚本顶部的 HERE 常量默认仍指向 _teacon 数据目录，
# 如数据目录已清，把 HERE 改成新位置或改用 --out/参数。
# -*- coding: utf-8 -*-
"""反编译下载来的星轨缺失 jar + 卡片 + 回收仓库地址 + 刷新星轨表"""
import json, os, re, subprocess, zipfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.expanduser(r'~/Downloads/_teacon')
WS = r''
REPDIR = os.path.join(WS, '分析报告', '_分析报告')
DL = os.path.join(HERE, 'downloaded')
CFR = os.path.expanduser(r'~/AppData/Local/Temp/cfr.jar')
DECDIR = os.path.join(WS, '源码库', '_参考仓库', '_pack_decompiled', '星轨重铸')
CARDS = os.path.join(WS, '源码库', '_参考仓库', '_pack_decompiled', '_卡片')
os.makedirs(DECDIR, exist_ok=True)
os.makedirs(CARDS, exist_ok=True)
safe = lambda x: re.sub(r'[\\/:*?"<>|]', '_', x)
SKIP = {'neoforge', 'minecraft', 'forge', 'fabricloader', 'kotlinforforge'}

def meta_of(jar_path):
    rec = {'modids': [], 'names': [], 'urls': [], 'version': ''}
    try:
        with zipfile.ZipFile(jar_path) as z:
            names = z.namelist()
            for w in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
                if w in names:
                    txt = z.read(w).decode('utf-8', 'ignore')
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
                        m = re.match(r'version\s*=\s*"([^"]+)"', s)
                        if m and not rec['version']: rec['version'] = m.group(1)
                    break
            if not rec['modids'] and 'fabric.mod.json' in names:
                j = json.loads(z.read('fabric.mod.json').decode('utf-8', 'ignore'))
                if j.get('id') and j['id'] not in SKIP: rec['modids'].append(j['id'])
                if j.get('name'): rec['names'].append(j['name'])
                c = j.get('contact') or {}
                rec['urls'] += [c[k] for k in ('sources', 'homepage', 'issues') if c.get(k)]
    except Exception as e:
        rec['err'] = str(e)[:50]
    BAD = ('change.me.to', 'example.invalid', 'mcreator.net')
    rec['urls'] = sorted(set(u for u in rec['urls'] if u and not any(b in u for b in BAD)))
    return rec

jars = [f for f in sorted(os.listdir(DL)) if f.endswith('.jar')]
print('待处理:', len(jars))

def work(jar):
    src = os.path.join(DL, jar)
    stem = re.sub(r'\.jar$', '', jar)
    dst = os.path.join(DECDIR, safe(stem))
    m = meta_of(src)
    if not (os.path.isdir(dst) and any(f.endswith('.java') for _, _, fs in os.walk(dst) for f in fs)):
        os.makedirs(dst, exist_ok=True)
        try:
            subprocess.run(['java', '-jar', CFR, src, '--outputdir', dst, '--silent', 'true',
                            '--caseinsensitivefs', 'true', '--comments', 'false'], capture_output=True, timeout=900)
        except Exception as e:
            m['cfr_err'] = str(e)[:40]
    files = loc = 0
    for root, dirs, fs in os.walk(dst):
        for f in fs:
            if f.endswith('.java'):
                files += 1
                try:
                    loc += open(os.path.join(root, f), 'rb').read().count(b'\n') + 1
                except Exception:
                    pass
    cname = safe('星轨重铸__' + stem) + '.md'
    open(os.path.join(CARDS, cname), 'w', encoding='utf-8').write('\n'.join([
        '# %s — 本地反编译速览' % (m['names'][0] if m['names'] else stem), '',
        '- 来源: 从整合包索引直链下载（SHA512 校验通过），整合包 星轨重铸：残响',
        '- mod id: %s；版本: %s' % (', '.join(m['modids']) or '?', m['version'] or '?'),
        '- 反编译规模: **%d 个 .java / %s 行**' % (files, format(loc, ',')),
        '- jar 元数据链接: %s' % (', '.join(m['urls']) or '（无）'), '']))
    return {'jar': jar, 'stem': stem, 'meta': m, 'files': files, 'loc': loc, 'card': cname}

with ThreadPoolExecutor(max_workers=4) as ex:
    results = list(ex.map(work, jars))
for r in results:
    print('  %-52s %5d 文件 %9s 行  id=%s' % (r['stem'][:52], r['files'], format(r['loc'], ','),
                                             ','.join(r['meta']['modids'][:2])))
json.dump(results, open(os.path.join(HERE, 'sr_decompiled.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 刷新星轨表: 标记本地反编译 + 回收仓库
GH = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')
p = os.path.join(REPDIR, '_starrail_final.json')
d = json.load(open(p, encoding='utf-8'))
by_stem = {r['stem']: r for r in results}
filled = 0
for name, v in d.items():
    stem = re.sub(r'\.jar$', '', name)
    r = by_stem.get(stem)
    if not r:
        # 索引名与文件名可能只差前缀
        for s, rr in by_stem.items():
            if s.endswith(stem) or stem.endswith(s) or s.split(']')[-1] == stem.split(']')[-1]:
                r = rr; break
    if not r:
        continue
    v['local_decompiled'] = True
    v['loc'] = r['loc']
    v['local_jar'] = r['jar']
    v['local_pack'] = '星轨重铸'
    for u in r['meta']['urls']:
        mm = GH.search(u)
        if mm:
            v['gh'] = mm.group(1).rstrip('/').replace('.git', '')
            v['gh_from'] = 'jar 元数据（下载）'
            filled += 1
            break
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('星轨表更新: 标记本地反编译 %d 个, 新回收仓库 %d 个' % (sum(1 for v in d.values() if v.get('local_decompiled')), filled))
n_gh = sum(1 for v in d.values() if v.get('gh'))
print('星轨现在: 总 %d, 有仓库 %d' % (len(d), n_gh))
