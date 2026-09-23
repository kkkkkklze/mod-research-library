# -*- coding: utf-8 -*-
"""批量稀疏克隆 591 个仓库到 _参考仓库/_bulk/ (只拉源码, 跳过贴图/音频)"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(BASE)                      # 仓库根：Mod源码研究汇总/
# 克隆落地目录：默认 仓库根/源码库/_参考仓库，可用环境变量 REF_REPO_DIR 覆盖
REF = os.environ.get('REF_REPO_DIR') or os.path.join(LIB, '源码库', '_参考仓库')
BULK = os.path.join(REF, '_bulk')

# 清单历史上挪过位置，两处都找
_union_path = next((p for p in (os.path.join(BASE, '_union_repos.json'),
                                os.path.join(LIB, '分析报告', '_分析报告', '_union_repos.json'))
                    if os.path.exists(p)), None)
if _union_path is None:
    sys.exit('找不到 _union_repos.json（owner/repo -> {title, packs, dl} 的清单）')
union = json.load(open(_union_path, encoding='utf-8'))
os.makedirs(REF, exist_ok=True)
existing = set()
for d in os.listdir(REF):
    if os.path.isdir(os.path.join(REF, d)) and d != '_bulk':
        existing.add(d.lower())

PATTERNS = ['**/*.java', '**/*.gradle', '**/*.gradle.kts', '**/*.properties', '**/*.toml',
            '**/*.mixins.json', '**/*.md', '**/*.kts', '**/*.yml', '**/*.yaml',
            '**/*.accesswidener', '**/*.cfg', '**/*.json5', '**/*.kt', '**/*.scala',
            '**/*.txt', '**/gradle/wrapper/**', '**/buildSrc/**', '**/libs/**']

def clone(item):
    gh, info = item
    owner, repo = gh.split('/')
    target = os.path.join(BULK, f'{owner}__{repo}')
    if repo.lower() in existing or os.path.isdir(target):
        return gh, 'skip', 0
    url = f'https://github.com/{gh}.git'
    t0 = time.time()
    try:
        r = subprocess.run(['git', 'clone', '--depth', '1', '--filter=blob:none', '--sparse',
                            '--quiet', url, target],
                           capture_output=True, timeout=300)
        if r.returncode != 0:
            # 部分老仓库不支持 filter, 退回普通浅克隆
            r = subprocess.run(['git', 'clone', '--depth', '1', '--quiet', url, target],
                               capture_output=True, timeout=300)
            if r.returncode != 0:
                return gh, 'fail:' + r.stderr.decode('utf-8', 'ignore')[:80], time.time() - t0
        else:
            subprocess.run(['git', '-C', target, 'sparse-checkout', 'set', '--no-cone'] + PATTERNS,
                           capture_output=True, timeout=300)
        return gh, 'ok', time.time() - t0
    except subprocess.TimeoutExpired:
        return gh, 'timeout', time.time() - t0
    except Exception as e:
        return gh, f'err:{e}', time.time() - t0

def main():
    os.makedirs(BULK, exist_ok=True)
    items = sorted(union.items(), key=lambda x: -(x[1].get('dl') or 0))
    if '--dry-run' in sys.argv:
        # 只验证清单与落地目录解析，不联网
        print(f'清单: {_union_path}')
        print(f'落地: {BULK}')
        print(f'仓库总数: {len(items)}，已在 REF 中的顶层克隆: {len(existing)}')
        for gh, info in items[:5]:
            print(f'  计划: https://github.com/{gh}.git -> {os.path.join(BULK, gh.replace("/", "__"))}  ({info.get("title")})')
        print('dry-run 结束，未执行任何克隆')
        return
    log_path = os.path.join(BASE, '_bulk_clone_log.json')
    log = json.load(open(log_path, encoding='utf-8')) if os.path.exists(log_path) else {}
    todo = [(gh, info) for gh, info in items if gh not in log or log[gh][0] not in ('ok', 'skip')]
    print(f'待克隆: {len(todo)} / {len(items)}', flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(clone, it): it[0] for it in todo}
        for fut in as_completed(futs):
            gh, status, secs = fut.result()
            log[gh] = [status, round(secs, 1)]
            done += 1
            if done % 20 == 0 or done == len(todo):
                json.dump(log, open(log_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print(f'  {done}/{len(todo)} (最近: {gh} {status})', flush=True)
    json.dump(log, open(log_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(1 for v in log.values() if v[0] in ('ok', 'skip'))
    print(f'克隆完成: {ok}/{len(log)} 成功', flush=True)
    fails = [k for k, v in log.items() if v[0] not in ('ok', 'skip')]
    if fails:
        print('失败列表(前30):', fails[:30], flush=True)

if __name__ == '__main__':
    main()
