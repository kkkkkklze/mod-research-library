# -*- coding: utf-8 -*-
"""两个 jar 的类级差异（按条目 CRC32）——回答"这次更新改了什么"

比"两边都反编译再 diff"准确得多也快得多：
  · 反编译产物受 CFR 版本/顺序影响，会产生大量假差异
  · zip 中央目录里每个条目的 CRC32 是**编译产物**的真实指纹，改一个字节就变

用法:
  py _jar_diff.py <旧.jar> <新.jar>                 # 汇总 + 明细（按包聚合）
  py _jar_diff.py <旧.jar> <新.jar> --list 30       # 只列前 30 条变更
  py _jar_diff.py <旧.jar> <新.jar> --extract-changed <目录>   # 导出变更的 .class（供选择性反编译）
  py _jar_diff.py <旧.jar> <新.jar> --json out.json            # 机器可读

退出码: 0 无差异 / 1 有差异 / 2 出错
"""
import argparse
import collections
import io
import json
import os
import re
import sys
import zipfile


def index(path):
    """类名 → CRC；同时记录体积与压缩前大小"""
    out = {}
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            if i.filename.endswith('/'):
                continue
            if i.filename.endswith('.class'):
                out[i.filename] = (i.CRC, i.file_size)
    return out


def pkg_of(name):
    parts = name.split('/')
    return '/'.join(parts[:4]) if len(parts) > 4 else '/'.join(parts[:-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('old')
    ap.add_argument('new')
    ap.add_argument('--list', type=int, default=200, help='明细条数上限')
    ap.add_argument('--extract-changed', metavar='DIR', help='把变更的 .class（新版的）导出到该目录')
    ap.add_argument('--json', metavar='FILE')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    try:
        o, n = index(a.old), index(a.new)
    except Exception as e:                                  # noqa: BLE001
        print('读取失败: %s' % e)
        return 2

    added = sorted(set(n) - set(o))
    removed = sorted(set(o) - set(n))
    changed = sorted(k for k in set(o) & set(n) if o[k][0] != n[k][0])

    if not a.quiet:
        print('旧: %s  (%d 个 class)' % (os.path.basename(a.old), len(o)))
        print('新: %s  (%d 个 class)' % (os.path.basename(a.new), len(n)))
        print()
        print('新增 %d / 删除 %d / 修改 %d' % (len(added), len(removed), len(changed)))

        for title, items in (('新增', added), ('修改', changed), ('删除', removed)):
            if not items:
                continue
            c = collections.Counter(pkg_of(x) for x in items)
            print('\n【%s】按包（前 15）' % title)
            for p, k in c.most_common(15):
                print('  %4d  %s' % (k, p))

        def show(title, items):
            if not items:
                return
            print('\n【%s】明细（前 %d）' % (title, min(a.list, len(items))))
            for x in items[:a.list]:
                cls = x.split('/')[-1][:-6]
                print('  %s' % x)
        show('新增', added)
        show('修改', changed)
        show('删除', removed)

    if a.extract_changed:
        os.makedirs(a.extract_changed, exist_ok=True)
        cnt = 0
        with zipfile.ZipFile(a.new) as z:
            for k in added + changed:
                dst = os.path.join(a.extract_changed, *k.split('/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'wb') as f:
                    f.write(z.read(k))
                cnt += 1
        print('\n已导出 %d 个 .class 到 %s' % (cnt, a.extract_changed))
        print('选择性反编译:  java -jar cfr.jar <目录> --outputdir <输出> --silent true --caseinsensitivefs true')

    if a.json:
        json.dump({'old': a.old, 'new': a.new, 'added': added, 'removed': removed, 'changed': changed},
                  io.open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('已写 %s' % a.json)

    return 1 if (added or removed or changed) else 0


if __name__ == '__main__':
    sys.exit(main())
