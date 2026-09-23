# -*- coding: utf-8 -*-
"""通过 HTTP Range 只读取 jar 的 zip 中央目录 + 元数据文件, 提取 mods.toml 中的源码地址"""
import urllib.request, struct, zlib, json, io, re, sys, time

UA = {'User-Agent': 'Mozilla/5.0'}

def http_range(url, start=None, end=None, retries=3):
    for a in range(retries):
        try:
            h = dict(UA)
            if start is not None:
                h['Range'] = f'bytes={start}-{end if end is not None else ""}'
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), r.headers
        except Exception as e:
            if a == retries - 1:
                raise
            time.sleep(1.5)

def total_size(url):
    _, h = http_range(url, 0, 0)
    cr = h.get('Content-Range')
    if cr:
        return int(cr.split('/')[-1])
    return int(h.get('Content-Length'))

def parse_central_dir(buf):
    """parse zip central directory; returns list of (name, method, comp_size, uncomp_size, local_hdr_offset)"""
    ents = []
    i = 0
    n = len(buf)
    while i + 46 <= n:
        sig = buf[i:i+4]
        if sig != b'PK\x01\x02':
            i += 1
            continue
        (ver, verneed, flags, method, mtime, mdate, crc, csize, usize,
         nlen, elen, clen, disk, iattr, eattr, lho) = struct.unpack('<HHHHHHIIIHHHHHII', buf[i+4:i+46])
        name = buf[i+46:i+46+nlen].decode('utf-8', 'replace')
        # zip64 extra field
        if csize == 0xFFFFFFFF or usize == 0xFFFFFFFF or lho == 0xFFFFFFFF:
            ex = buf[i+46+nlen:i+46+nlen+elen]
            j = 0
            while j + 4 <= len(ex):
                hid, hsz = struct.unpack('<HH', ex[j:j+4])
                if hid == 0x0001:
                    d = ex[j+4:j+4+hsz]
                    k = 0
                    if usize == 0xFFFFFFFF:
                        usize = struct.unpack('<Q', d[k:k+8])[0]; k += 8
                    if csize == 0xFFFFFFFF:
                        csize = struct.unpack('<Q', d[k:k+8])[0]; k += 8
                    if lho == 0xFFFFFFFF:
                        lho = struct.unpack('<Q', d[k:k+8])[0]; k += 8
                j += 4 + hsz
        ents.append((name, method, csize, usize, lho))
        i += 46 + nlen + elen + clen
    return ents

def read_entry(url, ent):
    name, method, csize, usize, lho = ent
    buf, _ = http_range(url, lho, lho + 30 + 4096 + csize)
    if buf[:4] != b'PK\x03\x04':
        raise ValueError('bad local header')
    nlen, elen = struct.unpack('<HH', buf[26:30])
    start = 30 + nlen + elen
    data = buf[start:start+csize]
    if method == 0:
        return data
    return zlib.decompress(data, -15)

def jar_meta(url):
    sz = total_size(url)
    tail_len = min(200000, sz)
    tail, _ = http_range(url, sz - tail_len, sz - 1)
    # find EOCD
    p = tail.rfind(b'PK\x05\x06')
    if p < 0:
        raise ValueError('no EOCD')
    cd_size, cd_off = struct.unpack('<II', tail[p+12:p+20])
    cd_buf = None
    if cd_off >= sz - tail_len and cd_off + cd_size <= sz:
        off_in_tail = cd_off - (sz - tail_len)
        cd_buf = tail[off_in_tail:off_in_tail+cd_size]
    else:
        cd_buf, _ = http_range(url, cd_off, cd_off + cd_size - 1)
    ents = parse_central_dir(cd_buf)
    want = ['META-INF/neoforge.mods.toml', 'META-INF/mods.toml', 'fabric.mod.json', 'META-INF/MANIFEST.MF']
    out = {}
    for w in want:
        for e in ents:
            if e[0] == w:
                try:
                    out[w] = read_entry(url, e).decode('utf-8', 'ignore')
                except Exception as ex:
                    out[w] = f'<<err {ex}>>'
                break
    return out

def extract_urls(meta):
    res = {'modids': [], 'urls': [], 'licenses': []}
    for fname, text in meta.items():
        if fname.endswith('.toml'):
            res['modids'] += re.findall(r'modId\s*=\s*"([^"]+)"', text)
            for key in ('displayURL', 'issueTrackerURL', 'displayTest'):
                pass
            res['urls'] += re.findall(r'(?:displayURL|issueTrackerURL)\s*=\s*"([^"]+)"', text)
            res['licenses'] += re.findall(r'license\s*=\s*"([^"]+)"', text)
        elif fname == 'fabric.mod.json':
            try:
                j = json.loads(text)
                res['modids'].append(j.get('id'))
                c = j.get('contact') or {}
                for k in ('sources', 'homepage', 'issues'):
                    if c.get(k):
                        res['urls'].append(c[k])
            except Exception:
                pass
    res['modids'] = [m for m in res['modids'] if m and m not in ('neoforge', 'minecraft', 'forge', 'fabricloader')]
    res['urls'] = sorted(set(u for u in res['urls'] if u and 'change.me.to' not in u and 'example.invalid' not in u))
    return res

if __name__ == '__main__':
    url = sys.argv[1]
    m = jar_meta(url)
    print(json.dumps(extract_urls(m), ensure_ascii=False, indent=1))
