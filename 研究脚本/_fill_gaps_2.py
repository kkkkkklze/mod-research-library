# 来源: ~/Downloads\_teacon\fill_gaps2.py
# 已归档到 研究脚本/（Downloads 会被清理）。脚本顶部的 HERE 常量默认仍指向 _teacon 数据目录，
# 如数据目录已清，把 HERE 改成新位置或改用 --out/参数。
# -*- coding: utf-8 -*-
"""补漏第二轮: 更宽松的匹配(词切分+双向包含), 补反编译"""
import json, os, re, subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.expanduser(r'~/Downloads/_teacon')
WS = r''
REPDIR = os.path.join(WS, '分析报告', '_分析报告')
V = os.path.expanduser(r'~/Documents/PCL/PCL2/.minecraft/versions')
CFR = os.path.expanduser(r'~/AppData/Local/Temp/cfr.jar')
DECROOT = os.path.join(WS, '源码库', '_参考仓库', '_pack_decompiled')
CARDS = os.path.join(DECROOT, '_卡片')

def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

def tokens(s):
    """把名字切成有意义的词"""
    ws = re.split(r'[\s\-_+.\[\]（）()：:，,]+', s or '')
    out = []
    for w in ws:
        n = norm(w)
        if len(n) >= 4 and not re.fullmatch(r'(neoforge|forge|fabric|minecraft|jar|common|beta|alpha|release|pre|snapshot|hotfix|build|mc)', n) \
           and not re.fullmatch(r'\d+', n):
            out.append(n)
    return out

local = json.load(open(os.path.join(HERE, 'local_index.json'), encoding='utf-8'))
prev = json.load(open(os.path.join(HERE, 'gap_fill.json'), encoding='utf-8'))
done_names = set(r['name'] for r in prev)

# 本地索引: 文件名 -> 记录
local_by_file = {}
for r in local:
    local_by_file[r['jar']] = r

def match(name, pack):
    """返回最佳本地 jar 记录"""
    ts = tokens(name)
    # 1) 精确键
    for t in ts:
        for r in local:
            if r['pack'] != pack:
                continue
            keys = set([norm(x) for x in (r['modids'] + r['names'])] + [norm(re.sub(r'\.jar$', '', r['jar']))])
            if t in keys:
                return r, t
    # 2) 包含匹配(词 ∈ 本地键 或 本地键 ∈ 词)
    best = None
    for r in local:
        if r['pack'] != pack:
            continue
        keys = [norm(re.sub(r'\.jar$', '', r['jar']))] + [norm(x) for x in (r['modids'] + r['names'])]
        for t in ts:
            for k in keys:
                if not k or len(k) < 5:
                    continue
                if t == k:
                    return r, t
                if t in k or k in t:
                    score = min(len(t), len(k))
                    if not best or score > best[1]:
                        best = (r, score, t)
    if best and best[1] >= 6:
        return best[0], best[2]
    return None, None

# 重建未匹配列表
unres = []
for fn, pack in [('_final.json', '璇穹之歌'), ('_fidr_final.json', '[FIDR]暗涌：深岩恐惧')]:
    d = json.load(open(os.path.join(REPDIR, fn), encoding='utf-8'))
    for name, v in d.items():
        if not v.get('gh') and name not in done_names:
            unres.append((pack, name))
atm = json.load(open(os.path.join(REPDIR, '_atm10_final.json'), encoding='utf-8'))
extra = json.load(open(os.path.join(REPDIR, '_atm10_extra.json'), encoding='utf-8'))
for pid, v in atm.items():
    n = v.get('title') or pid
    gh = v.get('gh') or (extra.get(pid) or {}).get('gh')
    if not gh and n not in done_names:
        unres.append(('All the Mods 10 - ATM10', n))

print('待重匹配:', len(unres))
matched = []
for pack, name in unres:
    r, key = match(name, pack)
    if r:
        matched.append({'pack': pack, 'name': name, 'title': name, 'local': r, 'matched_by': key})
print('宽松匹配到:', len(matched))

def decompile(rec):
    jar = rec['local']['jar']
    pack = rec['local']['pack']
    stem = re.sub(r'\.jar$', '', jar)
    safe = lambda x: re.sub(r'[\\/:*?"<>|]', '_', x)
    dst = os.path.join(DECROOT, safe(pack), safe(stem))
    src = os.path.join(V, pack, 'mods', jar)
    if not (os.path.isdir(dst) and any(f.endswith('.java') for _, _, fs in os.walk(dst) for f in fs)):
        os.makedirs(dst, exist_ok=True)
        try:
            subprocess.run(['java', '-jar', CFR, src, '--outputdir', dst, '--silent', 'true',
                            '--caseinsensitivefs', 'true', '--comments', 'false'], capture_output=True, timeout=900)
        except Exception as e:
            rec['status'] = str(e)[:50]
            return rec
    files = loc = 0
    for root, dirs, fs in os.walk(dst):
        for f in fs:
            if f.endswith('.java'):
                files += 1
                try:
                    loc += open(os.path.join(root, f), 'rb').read().count(b'\n') + 1
                except Exception:
                    pass
    cname = safe(pack + '__' + stem) + '.md'
    ms = rec['local']
    open(os.path.join(CARDS, cname), 'w', encoding='utf-8').write('\n'.join([
        '# %s — 本地反编译速览' % rec['title'], '',
        '- 来源 jar: `%s`（整合包 %s 本地安装）' % (jar, pack),
        '- mod id: %s；版本: %s' % (', '.join(ms['modids']) or '?', ms.get('version') or '?'),
        '- 匹配依据: %s' % rec.get('matched_by'),
        '- 反编译规模: **%d 个 .java / %s 行**' % (files, format(loc, ',')),
        '- jar 元数据链接: %s' % (', '.join(ms['urls']) or '（无）'), '']))
    rec['card'] = cname
    rec['files'], rec['loc'] = files, loc
    rec['status'] = 'ok'
    return rec

print('反编译(4 并发)...', flush=True)
out = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for i, r in enumerate(ex.map(decompile, matched), 1):
        out.append(r)
        if i % 10 == 0:
            print('  %d/%d' % (i, len(matched)), flush=True)

GH = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')
for r in out:
    for u in (r['local'].get('urls') or []):
        m = GH.search(u)
        if m:
            r['new_gh'] = m.group(1).rstrip('/').replace('.git', '')
            break
json.dump(out, open(os.path.join(HERE, 'gap_fill2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('成功:', sum(1 for r in out if r.get('status') == 'ok'), '/', len(out))
print('新发现仓库:', sum(1 for r in out if r.get('new_gh')))
print('总代码量: %s 行' % format(sum(r.get('loc', 0) for r in out), ','))
still = [u for u in unres if u[1] not in set(r['name'] for r in out)]
print('仍未匹配:', len(still))
for p, n in still[:30]:
    print('   [%s] %s' % (p[:8], n[:56]))
