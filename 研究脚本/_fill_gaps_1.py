# 来源: ~/Downloads\_teacon\fill_gaps.py
# 已归档到 研究脚本/（Downloads 会被清理）。脚本顶部的 HERE 常量默认仍指向 _teacon 数据目录，
# 如数据目录已清，把 HERE 改成新位置或改用 --out/参数。
# -*- coding: utf-8 -*-
"""补漏: 用本地已安装 jar 补上"未定位/无源码"的 mod —— 补仓库 + 反编译 + 卡片"""
import json, os, re, subprocess, zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.expanduser(r'~/Downloads/_teacon')
WS = r''
REPDIR = os.path.join(WS, '分析报告', '_分析报告')
V = os.path.expanduser(r'~/Documents/PCL/PCL2/.minecraft/versions')
CFR = os.path.expanduser(r'~/AppData/Local/Temp/cfr.jar')
DECROOT = os.path.join(WS, '源码库', '_参考仓库', '_pack_decompiled')
CARDS = os.path.join(DECROOT, '_卡片')
os.makedirs(CARDS, exist_ok=True)

def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

local = json.load(open(os.path.join(HERE, 'local_index.json'), encoding='utf-8'))
# 本地索引: 按 modid / 名称 / 文件名归一
by_key = {}
for r in local:
    for k in [norm(x) for x in (r['modids'] + r['names'])] + [norm(re.sub(r'\.jar$', '', r['jar']))]:
        if k and len(k) >= 3:
            by_key.setdefault(k, r)

GH = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')

# ---- 收集未定位 mod ----
unresolved = []
for key, fn, pack in [('璇穹之歌', '_final.json', '璇穹之歌'),
                      ('FIDR暗涌', '_fidr_final.json', '[FIDR]暗涌：深岩恐惧')]:
    d = json.load(open(os.path.join(REPDIR, fn), encoding='utf-8'))
    for name, v in d.items():
        if not v.get('gh'):
            unresolved.append({'pack': pack, 'name': name, 'title': v.get('title') or name, 'old_gh': ''})
# ATM10 合并 extra
atm = json.load(open(os.path.join(REPDIR, '_atm10_final.json'), encoding='utf-8'))
extra = json.load(open(os.path.join(REPDIR, '_atm10_extra.json'), encoding='utf-8'))
for pid, v in atm.items():
    gh = v.get('gh') or ((extra.get(pid) or {}).get('gh'))
    if not gh:
        unresolved.append({'pack': 'All the Mods 10 - ATM10', 'name': v.get('title') or pid, 'title': v.get('title') or pid, 'old_gh': ''})
# 克隆失败的 13 个
CLONE_FAIL = ['McJty/MFFS', 'gigabit101/EnderStorage', 'ZeroNoRyouki/ExtremeReactors', 'Buuz135/titanium',
              'McJty/RFToolsBase', 'McJty/RFToolsBuilder', 'Technici4n/Modern-Industrialization',
              'Ultramega/CableTiers', 'Buuz135/Functional-Storage', 'XyCraft-Mods/XyCraft',
              'Propulsion-Team/create-propulsion-simulated', 'LOVE-U987/Adaptive-Nemesis',
              'userenxv/aeronautics-utility-objects']
clone_fail_rows = [{'pack': 'All the Mods 10 - ATM10', 'name': x, 'title': x, 'old_gh': x} for x in CLONE_FAIL]
print('未定位 mod: %d（四包）+ 克隆失败 %d' % (len(unresolved), len(clone_fail_rows)))

# ---- 匹配本地 jar ----
matched = []
for r in unresolved:
    keys = [norm(r['title']), norm(r['name'])]
    keys += [norm(x) for x in re.findall(r'[A-Za-z0-9_.\-]{4,}', r['name'] or '')]
    hit = None
    for k in keys:
        if k and k in by_key:
            hit = by_key[k]
            break
    if hit:
        r['local'] = hit
        matched.append(r)
print('匹配到本地 jar 的:', len(matched))

# 克隆失败: 按名字在 ATM10/其他包里找
for r in clone_fail_rows:
    base = norm(r['name'].split('/')[-1])
    hit = by_key.get(base)
    if hit:
        r['local'] = hit
        matched.append(r)
print('加上克隆失败匹配后:', len(matched))

# ---- 反编译 + 卡片 ----
def decompile(rec):
    jar = rec['local']['jar']
    pack = rec['local']['pack']
    stem = re.sub(r'\.jar$', '', jar)
    dst = os.path.join(DECROOT, re.sub(r'[\\/:*?"<>|]', '_', pack), re.sub(r'[\\/:*?"<>|]', '_', stem))
    src = os.path.join(V, pack, 'mods', jar)
    if not (os.path.isdir(dst) and any(f.endswith('.java') for _, _, fs in os.walk(dst) for f in fs)):
        os.makedirs(dst, exist_ok=True)
        try:
            subprocess.run(['java', '-jar', CFR, src, '--outputdir', dst, '--silent', 'true',
                            '--caseinsensitivefs', 'true', '--comments', 'false'], capture_output=True, timeout=900)
        except Exception as e:
            return rec, str(e)[:60], 0, 0
    files = loc = 0
    for root, dirs, fs in os.walk(dst):
        for f in fs:
            if f.endswith('.java'):
                files += 1
                try:
                    loc += open(os.path.join(root, f), 'rb').read().count(b'\n') + 1
                except Exception:
                    pass
    # 卡片
    cname = re.sub(r'[\\/:*?"<>|]', '_', pack + '__' + stem) + '.md'
    ms = rec['local']
    L = ['# %s — 本地反编译速览' % rec['title'], '',
         '- 来源 jar: `%s`（整合包 %s 本地安装）' % (jar, pack),
         '- mod id: %s；版本: %s' % (', '.join(ms['modids']) or '?', ms.get('version') or '?'),
         '- 反编译规模: **%d 个 .java / %s 行**' % (files, format(loc, ',')),
         '- jar 元数据里的链接: %s' % (', '.join(ms['urls']) or '（无）'), '']
    open(os.path.join(CARDS, cname), 'w', encoding='utf-8').write('\n'.join(L))
    rec['card'] = cname
    return rec, 'ok', files, loc

print('开始反编译(4 并发)...', flush=True)
results = []
done = 0
with ThreadPoolExecutor(max_workers=4) as ex:
    for rec, status, files, loc in ex.map(decompile, matched):
        rec['status'] = status
        rec['files'] = files
        rec['loc'] = loc
        results.append(rec)
        done += 1
        if done % 10 == 0:
            print('  %d/%d' % (done, len(matched)), flush=True)

# ---- 汇总: 新发现的仓库 ----
found_repo = 0
for r in results:
    for u in (r.get('local') or {}).get('urls', []):
        m = GH.search(u)
        if m:
            r['new_gh'] = m.group(1).rstrip('/').replace('.git', '')
            found_repo += 1
            break
json.dump(results, open(os.path.join(HERE, 'gap_fill.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('反编译成功:', sum(1 for r in results if r['status'] == 'ok'))
print('其中新发现仓库:', found_repo)
print('总代码量: %s 行' % format(sum(r['loc'] for r in results), ','))
print('按包:', dict(Counter(r['local']['pack'] for r in results)))
