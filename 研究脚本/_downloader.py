# -*- coding: utf-8 -*-
"""通用模组下载器（多源回退 + 哈希校验）

为什么有这个：本仓库经常要补下整合包里缺失的 jar（整合包索引里的直链、CurseForge 文件、
GitHub Release）。国内直连不稳，单一源失败会浪费大量重试，所以统一走「多源回退 + 校验入库」。

用法（推荐 `py`，本机 python/python3 被拦）：

  # 1) 直接下（自动尝试该源的备用镜像）
  py _downloader.py "https://cdn.modrinth.com/data/xxxx/versions/yyy/foo.jar" -o ../_下载缓存

  # 2) 带校验（强烈建议：整合包索引 / Modrinth API 都能拿到 sha512）
  py _downloader.py "<url>" --sha512 <hex>

  # 3) CurseForge 文件（只能走 CDN；CF 网页/下载端点有 Cloudflare 挑战，脚本直连必 403）
  #    文件页 https://www.curseforge.com/minecraft/mc-mods/<slug>/files/<fileId> 上能看到文件名
  py _downloader.py --cf 8813615 "DBE-1.21.1-neoforge-1.1.0-SNAPSHOT.jar" -o .

  # 4) 批量清单（每行: URL  或  URL<TAB>sha512，`#` 开头为注释）
  py _downloader.py --list urls.txt -o .

  # 5) 只要元信息（体积/最后修改），不下载
  py _downloader.py --head "<url>"

退出码: 0 全部成功 / 1 有失败。文件已存在且哈希（或体积）匹配时跳过（幂等）。

来源备注（踩过的坑）:
  - mediafilez.forgecdn.net 通；edge.forgecdn.net 对部分老文件 404/403；CF 的
    /download/<id> 与网页一样有 Cloudflare 挑战，脚本别走网页端。
  - cdn.modrinth.com 偶发超时 → cdn-raw.modrinth.com 通常可用；国内再退 BMCLAPI。
  - archive.teacon.cn 用 urllib 会 404，curl 正常（本脚本用 urllib，遇到该站请手动 curl）。
"""
import argparse
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
CF_CDNS = ['https://mediafilez.forgecdn.net/files/{a}/{b}/{name}',
           'https://edge.forgecdn.net/files/{a}/{b}/{name}']


def mirrors(url):
    """给一个下载源生成「主源 + 备用源」列表（PCL 式回退顺序）"""
    out = [url]
    if 'cdn.modrinth.com' in url:
        path = url.split('cdn.modrinth.com/data/', 1)[-1]
        out += ['https://cdn-raw.modrinth.com/data/' + path,
                'https://bmclapi2.bangbang93.com/maven/' + path]
    if 'mediafilez.forgecdn.net' in url:
        out.append(url.replace('mediafilez.forgecdn.net', 'edge.forgecdn.net'))
    if 'edge.forgecdn.net' in url:
        out.append(url.replace('edge.forgecdn.net', 'mediafilez.forgecdn.net'))
    if 'raw.githubusercontent.com' in url:
        out.append(url.replace('raw.githubusercontent.com', 'raw.gitmirror.com'))
    # 去重保序
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def cf_urls(file_id, name):
    """CurseForge 文件 → CDN 直链（fileId 前 4 位/后 N 位分目录）"""
    return [t.format(a=file_id[:4], b=file_id[4:], name=name) for t in CF_CDNS]


def check(data, sha512=None, sha1=None, md5=None, size=None):
    if size is not None and len(data) != size:
        return 'size %d != %d' % (len(data), size)
    if sha512 and hashlib.sha512(data).hexdigest().lower() != sha512.lower():
        return 'sha512 mismatch'
    if sha1 and hashlib.sha1(data).hexdigest().lower() != sha1.lower():
        return 'sha1 mismatch'
    if md5 and hashlib.md5(data).hexdigest().lower() != md5.lower():
        return 'md5 mismatch'
    return None


def fetch(url, dst, sha512=None, sha1=None, md5=None, size=None, tries=3, quiet=False):
    """下载并校验；返回 (成功?, 说明)"""
    last = 'no url'
    for u in mirrors(url):
        for attempt in range(1, tries + 1):
            try:
                req = urllib.request.Request(u, headers=UA)
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = r.read()
                if len(data) < 1024:
                    raise ValueError('too small: %d bytes' % len(data))
                bad = check(data, sha512, sha1, md5, size)
                if bad:
                    raise ValueError(bad)
                tmp = dst + '.part'
                with open(tmp, 'wb') as f:
                    f.write(data)
                os.replace(tmp, dst)
                return True, '%s  %.1f KB' % (u.split('/')[2], len(data) / 1024.0)
            except Exception as e:                      # noqa: BLE001 网络/校验一视同仁重试
                last = '%s: %s' % (type(e).__name__, str(e)[:80])
                if not quiet:
                    sys.stderr.write('  · %s 第%d次失败: %s\n' % (u.split('/')[2], attempt, last))
                time.sleep(2 * attempt)
    return False, last


def head(url):
    for u in mirrors(url):
        try:
            req = urllib.request.Request(u, headers=UA, method='HEAD')
            with urllib.request.urlopen(req, timeout=60) as r:
                return {'url': u, 'status': r.status,
                        'length': int(r.headers.get('Content-Length') or -1),
                        'last_modified': r.headers.get('Last-Modified') or '',
                        'type': r.headers.get('Content-Type') or ''}
        except Exception as e:                          # noqa: BLE001
            last = '%s: %s' % (type(e).__name__, str(e)[:80])
    return {'error': last}


def main():
    ap = argparse.ArgumentParser(description='多源回退 + 哈希校验的模组下载器')
    ap.add_argument('url', nargs='?', help='下载直链')
    ap.add_argument('--cf', nargs=2, metavar=('FILEID', 'FILENAME'),
                    help='CurseForge 文件：fileId 与文件名（从文件页抄）')
    ap.add_argument('--list', metavar='FILE', help='批量清单（每行 URL[<TAB>sha512]）')
    ap.add_argument('--head', action='store_true', help='只查元信息，不下载')
    ap.add_argument('-o', '--out', default='.', help='输出目录（默认当前目录）')
    ap.add_argument('--sha512'), ap.add_argument('--sha1'), ap.add_argument('--md5')
    ap.add_argument('--size', type=int)
    ap.add_argument('--tries', type=int, default=3)
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    jobs = []          # (url, 目标文件名, 校验字典)
    ver = dict(sha512=a.sha512, sha1=a.sha1, md5=a.md5, size=a.size)
    if a.cf:
        fid, name = a.cf
        for u in cf_urls(fid, name):
            jobs.append((u, name, ver))
    elif a.list:
        with open(a.list, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                u = parts[0]
                v = dict(ver)
                if len(parts) > 1 and len(parts[1]) == 128:
                    v['sha512'] = parts[1]
                jobs.append((u, os.path.basename(u.split('?')[0]), v))
    elif a.url:
        if a.head:
            print(head(a.url))
            return 0
        jobs.append((a.url, os.path.basename(a.url.split('?')[0]) or 'download.bin', ver))
    else:
        ap.error('需要 url / --cf / --list 之一')

    os.makedirs(a.out, exist_ok=True)
    ok = 0
    for url, name, v in jobs:
        dst = os.path.join(a.out, re.sub(r'[\\/:*?"<>|]', '_', name))
        if os.path.exists(dst) and os.path.getsize(dst) > 1024:
            with open(dst, 'rb') as f:
                data = f.read()
            if check(data, **v) is None:
                print('= 跳过（已存在且校验通过）  %s' % name)
                ok += 1
                continue
        print('↓ %s' % name)
        good, msg = fetch(url, dst, tries=a.tries, quiet=a.quiet, **v)
        print('  %s %s' % ('✓' if good else '✗', msg))
        ok += 1 if good else 0
    print('完成 %d / %d' % (ok, len(jobs)))
    return 0 if ok == len(jobs) else 1


if __name__ == '__main__':
    sys.exit(main())
