# 来源: ~/Downloads\_teacon\fill_gaps3.py
# 已归档到 研究脚本/（Downloads 会被清理）。脚本顶部的 HERE 常量默认仍指向 _teacon 数据目录，
# 如数据目录已清，把 HERE 改成新位置或改用 --out/参数。
# -*- coding: utf-8 -*-
"""第三轮: 星轨重铸的未定位 mod 拿去全库匹配 + 边角补漏 + 汇总"""
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
    ws = re.split(r'[\s\-_+.\[\]（）()：:，,]+', s or '')
    out = []
    for w in ws:
        n = norm(w)
        if len(n) >= 3 and not re.fullmatch(r'(neoforge|forge|fabric|minecraft|jar|common|beta|alpha|release|pre|snapshot|hotfix|build|mc|api|lib)', n) \
           and not re.fullmatch(r'\d+', n):
            out.append(n)
    return out

local = json.load(open(os.path.join(HERE, 'local_index.json'), encoding='utf-8'))
prev = json.load(open(os.path.join(HERE, 'gap_fill.json'), encoding='utf-8')) + json.load(open(os.path.join(HERE, 'gap_fill2.json'), encoding='utf-8'))
done = set(r['name'] for r in prev)

# 星轨重铸未定位 + 8 个边角
targets = []
sr = json.load(open(os.path.join(REPDIR, '_starrail_final.json'), encoding='utf-8'))
for name, v in sr.items():
    if not v.get('gh') and name not in done:
        targets.append(('星轨重铸', name))
LEFTOVER = [('璇穹之歌', '[机械动力火炮：先进技术] cbc_at_Neoforge_1.21.1_0.1.4c.jar'),
            ('璇穹之歌', 'atlas_api-1.21.1-1.2.0.jar'),
            ('璇穹之歌', '橱柜库.jar'),
            ('璇穹之歌', '渲染优化ruok-neoforge_1.21.1_Pre-Release_5-1.7.4.jar'),
            ('[FIDR]暗涌：深岩恐惧', 'Quest Kill Task-0.2.0+1.20.1-forge.jar'),
            ('All the Mods 10 - ATM10', 'ATO - All the Ores'),
            ('All the Mods 10 - ATM10', 'Clean Swing Through Grass'),
            ('All the Mods 10 - ATM10', 'BSL Shaders')]
targets += [t for t in LEFTOVER if t[1] not in done]
print('本轮目标:', len(targets), '（星轨 %d）' % sum(1 for t in targets if t[0] == '星轨重铸'))

def match(name, pack):
    ts = tokens(name)
    best = None
    for r in local:
        # 星轨的 mod 可能出现在任意包
        if pack != '星轨重铸' and r['pack'] != pack:
            continue
        keys = [norm(re.sub(r'\.jar$', '', r['jar']))] + [norm(x) for x in (r['modids'] + r['names'])]
        for t in ts:
            for k in keys:
                if not k or len(k) < 3:
                    continue
                if t == k:
                    return r, t
                if len(t) >= 5 and (t in k or k in t):
                    score = min(len(t), len(k))
                    if not best or score > best[1]:
                        best = (r, score, t)
    if best and best[1] >= 5:
        return best[0], best[2]
    return None, None

matched = []
for pack, name in targets:
    r, key = match(name, pack)
    if r:
        matched.append({'pack': pack, 'name': name, 'title': name, 'local': r, 'matched_by': key,
                        'cross_pack': (r['pack'] != pack)})
print('匹配:', len(matched), '（跨包匹配 %d）' % sum(1 for m in matched if m.get('cross_pack')))
for m in matched:
    if m.get('cross_pack'):
        print('   [跨包] %s → %s/%s' % (m['name'][:34], m['local']['pack'][:12], m['local']['jar'][:40]))

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
        '- 来源 jar: `%s`（整合包 %s 本地安装%s）' % (jar, pack, '，供 星轨重铸 参考' if rec.get('cross_pack') else ''),
        '- mod id: %s；版本: %s' % (', '.join(ms['modids']) or '?', ms.get('version') or '?'),
        '- 匹配依据: %s' % rec.get('matched_by'),
        '- 反编译规模: **%d 个 .java / %s 行**' % (files, format(loc, ',')),
        '- jar 元数据链接: %s' % (', '.join(ms['urls']) or '（无）'), '']))
    rec['card'] = cname
    rec['files'], rec['loc'] = files, loc
    rec['status'] = 'ok'
    return rec

with ThreadPoolExecutor(max_workers=4) as ex:
    out = list(ex.map(decompile, matched))
GH = re.compile(r'github\.com/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)')
for r in out:
    for u in (r['local'].get('urls') or []):
        m = GH.search(u)
        if m:
            r['new_gh'] = m.group(1).rstrip('/').replace('.git', '')
            break
json.dump(out, open(os.path.join(HERE, 'gap_fill3.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('反编译成功:', sum(1 for r in out if r.get('status') == 'ok'), '/', len(out),
      '；新仓库:', sum(1 for r in out if r.get('new_gh')),
      '；代码量:', format(sum(r.get('loc', 0) for r in out), ','))

# ---- 汇总三轮 ----
allr = prev + out
print()
print('=== 三轮补漏汇总 ===')
print('反编译 total:', sum(1 for r in allr if r.get('status') in ('ok', None)), '/', len(allr))
print('新发现仓库 total:', sum(1 for r in allr if r.get('new_gh')))
print('代码量 total:', format(sum(r.get('loc', 0) for r in allr), ','))
print('按包:', dict(Counter(r['local']['pack'] for r in allr)))
json.dump(allr, open(os.path.join(HERE, 'gap_fill_all.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
