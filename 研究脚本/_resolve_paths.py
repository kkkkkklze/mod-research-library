"""Resolve local source paths for the missing-report candidates."""
import os
import re
import sys

ROOT = r""
LIB = os.path.join(ROOT, "源码库", "_参考仓库")
MD = os.path.join(ROOT, "对照表", "未深挖清单.md")

rows = []
for line in open(MD, encoding="utf-8"):
    m = re.match(r"\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*([\d,]+)\s*\|", line)
    if m:
        rows.append((int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)))

print("total rows: %d" % len(rows))
found = 0
missing_dir = []
for rank, stem, nf, lines in rows[:80]:
    cand = [os.path.join(LIB, stem), os.path.join(LIB, "_bulk", stem)]
    hit = next((c for c in cand if os.path.isdir(c)), None)
    if hit is None:
        # cards may use a sanitized stem; try fuzzy
        pref = stem.split("__")[0]
        base = os.path.basename(stem).lower().replace("-", "_")
        hits = []
        for d in cand:
            parent, want = (LIB, stem) if d == os.path.join(LIB, stem) else (os.path.join(LIB, "_bulk"), stem)
            if os.path.isdir(parent):
                for e in os.listdir(parent):
                    el = e.lower().replace("-", "_")
                    if el == want.lower() or (want.split("__")[0] in el and base.split("__")[0] in el):
                        hits.append(os.path.join(parent, e))
        hit = hits[0] if hits else None
    if hit:
        found += 1
        print("%3d OK  %-58s %s" % (rank, stem, os.path.relpath(hit, ROOT)))
    else:
        missing_dir.append((rank, stem))
print("resolved %d/80" % found)
for rank, stem in missing_dir:
    print("MISSING %d %s" % (rank, stem))
