"""Diff cards vs depth reports: which repos have a speed-card but no deep-dive report."""
import os
import re
import json

ROOT = r""
REP = os.path.join(ROOT, "分析报告", "_分析报告")
CARD = os.path.join(REP, "_卡片")

NON_REPO_PREFIXES = ("深挖__", "对照__", "设计__", "TeaCon", "DBE__", "README", "_", "四包")

covered = {}
for fn in os.listdir(REP):
    if not fn.endswith(".md"):
        continue
    if fn.startswith(NON_REPO_PREFIXES):
        continue
    covered[fn[:-3].lower()] = fn[:-3]

rows = []
for fn in sorted(os.listdir(CARD)):
    if not fn.endswith(".md"):
        continue
    stem = fn[:-3]
    path = os.path.join(CARD, fn)
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print("READFAIL", fn, e)
        continue
    m = re.search(r"(\d[\d,]*)\s*个\s*\.?java[^\d]*?([\d,]+)\s*行", text)
    nf = int(m.group(1).replace(",", "")) if m else -1
    nl = int(m.group(2).replace(",", "")) if m else -1
    pk = re.search(r"目标版本:\s*MC\s*([^\n/]*)", text)
    mc = pk.group(1).strip() if pk else "?"
    bl = re.search(r"构建:\s*([^\n]*)", text)
    build = bl.group(1).strip() if bl else "?"
    lic = re.search(r"许可证[^\n]*", text)
    pack = re.search(r"出现在整合包:\s*([^;；\n]*)", text)
    rows.append({
        "repo": stem,
        "java": nf,
        "lines": nl,
        "mc": mc,
        "build": build[:60],
        "lic": (lic.group(0)[:40] if lic else "?"),
        "pack": (pack.group(1).strip()[:40] if pack else "?"),
        "has_report": stem.lower() in covered,
        "in_bulk": "_bulk" in text,
    })

missing = [r for r in rows if not r["has_report"]]
have = [r for r in rows if r["has_report"]]
missing.sort(key=lambda r: -r["lines"])

print("cards=%d reports_covered=%d missing=%d" % (len(rows), len(have), len(missing)))
print("missing with source (>1 java file): %d" % len([r for r in missing if r["java"] > 1]))
print("missing >=2000 lines: %d | >=1000: %d | >=500: %d" % (
    len([r for r in missing if r["lines"] >= 2000]),
    len([r for r in missing if r["lines"] >= 1000]),
    len([r for r in missing if r["lines"] >= 500])))

out = os.path.join(ROOT, "研究脚本", "_数据", "missing_reports.json")
json.dump({"missing": missing, "covered": sorted(covered)}, open(out, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote", out)

md = os.path.join(ROOT, "对照表", "未深挖清单.md")
with open(md, "w", encoding="utf-8") as f:
    f.write("# 有速览卡片但无深度分析报告的仓库（按源码行数降序）\n\n")
    f.write("生成：2026-09-23，脚本 `研究脚本/_missing_reports.py`。共 %d 个候选。\n\n" % len(missing))
    f.write("| # | 仓库 | .java | 行数 | MC | 构建 | 来源包 |\n|---|---|---|---|---|---|---|\n")
    for i, r in enumerate(missing, 1):
        f.write("| %d | `%s` | %d | %s | %s | %s | %s |\n" % (
            i, r["repo"], r["java"], format(r["lines"], ","), r["mc"],
            r["build"].replace("|", "/"), r["pack"]))
print("wrote", md)
