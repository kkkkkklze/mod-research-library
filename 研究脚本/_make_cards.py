# -*- coding: utf-8 -*-
"""为所有已克隆仓库生成结构化速览卡片(纯 Python 文件遍历, 不依赖 unix 工具)"""
import json, os, re
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
REF = r'源码库/_参考仓库'
BULK = os.path.join(REF, '_bulk')
RPT = r'分析报告/_分析报告'
CARDS = os.path.join(RPT, '_卡片')
os.makedirs(CARDS, exist_ok=True)

union = json.load(open(os.path.join(BASE, '_union_repos.json'), encoding='utf-8'))

def find_path(gh):
    owner, repo = gh.split('/')
    for p in (os.path.join(REF, repo), os.path.join(BULK, f'{owner}__{repo}')):
        if os.path.isdir(p):
            return p
    return None

def readf(p, limit=4000):
    try:
        with open(p, encoding='utf-8', errors='ignore') as f:
            return f.read(limit)
    except Exception:
        return ''

def count_lines(fp):
    try:
        with open(fp, 'rb') as f:
            return f.read().count(b'\n') + 1
    except Exception:
        return 0

def card(item):
    gh, info = item
    path = find_path(gh)
    if not path:
        return gh, None

    per_file = {}
    total_loc = 0
    for root, dirs, fnames in os.walk(path):
        if '.git' in dirs:
            dirs.remove('.git')
        for fn in fnames:
            if fn.endswith('.java'):
                fp = os.path.join(root, fn)
                n = count_lines(fp)
                per_file[os.path.relpath(fp, path).replace('\\', '/')] = n
                total_loc += n

    pkg = Counter()
    for fp in per_file:
        parts = fp.split('/')
        if 'java' in parts:
            i = parts.index('java')
            rest = parts[i + 1:]
        else:
            rest = parts
        key = '/'.join(rest[:min(3, len(rest) - 1)]) if len(rest) > 1 else '<root>'
        pkg[key] += 1

    gp = readf(os.path.join(path, 'gradle.properties'))
    bg = readf(os.path.join(path, 'build.gradle')) or readf(os.path.join(path, 'build.gradle.kts'))
    settings = readf(os.path.join(path, 'settings.gradle')) + readf(os.path.join(path, 'settings.gradle.kts'))
    fmod = readf(os.path.join(path, 'src', 'main', 'resources', 'fabric.mod.json'))
    ntpl = ''
    for cand in ('src/main/templates/META-INF/neoforge.mods.toml', 'src/main/resources/META-INF/neoforge.mods.toml',
                 'src/main/resources/META-INF/mods.toml', 'src/main/templates/META-INF/mods.toml'):
        t = readf(os.path.join(path, cand))
        if t:
            ntpl = t
            break

    def grep(txt, pat, n=1):
        return re.findall(pat, txt, re.I)[:n]

    mc = grep(gp, r'minecraft_version\s*=\s*(.+)')
    neo = grep(gp, r'(?:neo_version|neoForge_version|neoforge_version)\s*=\s*(.+)')
    forge = grep(gp, r'forge_version\s*=\s*(.+)')
    fab = grep(gp, r'fabric_loader_version\s*=\s*(.+)')
    modver = grep(gp, r'mod_version\s*=\s*(.+)')
    modid = grep(gp, r'mod_id\s*=\s*(.+)') or grep(ntpl, r'modId\s*=\s*"([^"]+)"', 3)
    if not modid:
        m = re.search(r'"id"\s*:\s*"([^"]+)"', fmod)
        if m:
            modid = [m.group(1)]
    plugin = ('moddev' if 'net.neoforged.moddev' in bg else
              'userdev' if 'net.neoforged.gradle.userdev' in bg else
              'forgegradle' if 'net.minecraftforge.gradle' in bg else
              'architectury' if ('architectury-plugin' in bg or 'dev.architectury' in bg) else
              'loom' if 'fabric-loom' in bg else '?')
    multi = 'multiloader' if re.search(r'include\s*[\(\'"](Common|Fabric|NeoForge|Forge|common|fabric|neoforge)', settings) else 'single'
    lic = ''
    for lf in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING'):
        t = readf(os.path.join(path, lf), 300)
        if t:
            lic = ' '.join(t.split())[:60]
            break

    main_class = None
    for fp, n in sorted(per_file.items(), key=lambda x: -x[1]):
        base = os.path.basename(fp)
        if any(k in base for k in ('Mod.java', 'ModMain', 'Main.java', 'Entry.java')):
            main_class = (fp, n)
            break

    features = []
    import glob as _glob
    for pat, label in [('**/*.mixins.json', 'Mixin'), ('**/*mixin*.json', 'Mixin'),
                       ('**/network/**/*.java', 'Network'), ('**/net/**/*.java', 'Network'),
                       ('**/config/**/*.java', 'Config'), ('**/datagen/**/*.java', 'Datagen'),
                       ('**/data/**/*.java', 'Data'), ('**/client/**/*.java', 'Client'),
                       ('**/api/**/*.java', 'API'), ('**/world/**/*.java', 'Worldgen'),
                       ('**/entity/**/*.java', 'Entity'), ('**/worldgen/**/*.java', 'Worldgen'),
                       ('**/command/**/*.java', 'Command')]:
        if _glob.glob(os.path.join(path, pat), recursive=True):
            features.append(label)
    has_at = os.path.exists(os.path.join(path, 'src', 'main', 'resources', 'META-INF', 'accesstransformer.cfg'))

    L = []
    L.append(f'# {info.get("title") or gh} — 速览卡片\n')
    L.append(f'- 仓库: https://github.com/{gh}')
    L.append(f'- 出现在整合包: {", ".join(info.get("packs") or [])}；Modrinth 下载量(参考): {info.get("dl") or "未知"}')
    L.append(f'- 本地源码: `{path}`')
    L.append(f'- 目标版本: MC {", ".join(set(mc)) if mc else "?"} / NeoForge {", ".join(neo) if neo else "-"} / Forge {", ".join(forge) if forge else "-"} / Fabric {", ".join(fab) if fab else "-"}；mod 版本 {", ".join(modver) if modver else "?"}')
    L.append(f'- 构建: 插件={plugin}，工程结构={multi}；mod_id: {", ".join(sorted(set(modid))) if modid else "?"}')
    if lic:
        L.append(f'- 许可证: {lic}')
    L.append(f'- 源码规模: {len(per_file)} 个 .java，{total_loc:,} 行')
    if main_class:
        L.append(f'- 主类候选: `{main_class[0]}` ({main_class[1]} 行)')
    if features:
        L.append(f'- 目录特征: {", ".join(sorted(set(features)))}')
    if has_at:
        L.append('- 含 accesstransformer.cfg')
    L.append('')
    L.append('## 包结构（前 20，按文件数）\n')
    L.append('| 包 | 文件数 |')
    L.append('|---|---|')
    for k, v in pkg.most_common(20):
        L.append(f'| `{k}` | {v} |')
    L.append('')
    L.append('## 最大的 15 个源文件\n')
    L.append('| 文件 | 行数 |')
    L.append('|---|---|')
    for fp, n in sorted(per_file.items(), key=lambda x: -x[1])[:15]:
        L.append(f'| `{fp}` | {n} |')

    card_path = os.path.join(CARDS, gh.replace('/', '__') + '.md')
    with open(card_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    return gh, {'files': len(per_file), 'loc': total_loc, 'plugin': plugin, 'multi': multi,
                'mc': (sorted(set(mc)) or [''])[0], 'modid': (sorted(set(modid)) or [''])[0],
                'main': main_class[0] if main_class else '', 'card': card_path,
                'title': info.get('title') or gh, 'packs': info.get('packs'), 'dl': info.get('dl')}

def main():
    items = [(gh, info) for gh, info in union.items() if find_path(gh)]
    print(f'生成卡片: {len(items)} 个仓库', flush=True)
    summary = {}
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for gh, res in ex.map(card, items):
            if res:
                summary[gh] = res
            done += 1
            if done % 100 == 0:
                print(f'  {done}/{len(items)}', flush=True)
    json.dump(summary, open(os.path.join(RPT, '_卡片索引.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n_java = sum(1 for v in summary.values() if v['files'] > 0)
    print(f'完成: {len(summary)} 张卡片，其中有 Java 源码的 {n_java} 个', flush=True)

if __name__ == '__main__':
    main()
