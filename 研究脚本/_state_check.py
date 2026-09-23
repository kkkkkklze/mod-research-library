"""Print the true current state of the library, from disk only."""
import os
import re

ROOT = r""
REP = os.path.join(ROOT, "分析报告", "_分析报告")
CARD = os.path.join(REP, "_卡片")
IDX = os.path.join(REP, "README-索引.md")
BACKLOG = os.path.join(ROOT, "深挖待办清单.md")
LIST_MD = os.path.join(ROOT, "对照表", "未深挖清单.md")
RM = os.path.join(ROOT, "README.md")

PREFIX = ("深挖__", "对照__", "设计__", "专题__", "TeaCon", "DBE__", "README", "_", "四包", "元素反应")

cards = sorted(f[:-3] for f in os.listdir(CARD) if f.endswith(".md"))
mds = sorted(f[:-3] for f in os.listdir(REP) if f.endswith(".md"))
reports = [m for m in mds if not m.startswith(PREFIX)]
rset = {r.lower() for r in reports}
covered = [c for c in cards if c.lower() in rset]
missing = [c for c in cards if c.lower() not in rset]

print("== 磁盘实测 ==")
print("cards                 :", len(cards))
print("repo-level reports    :", len(reports), "(matched to a card:", len(covered), ")")
print("unmatched report files:", [r for r in reports if r not in cards])
print("total .md in 报告目录  :", len(mds))
print("cards without report  :", len(missing), "(case-insensitive match)")

import json
d = json.load(open(os.path.join(ROOT, "研究脚本", "_数据", "missing_reports.json"), encoding="utf-8"))
print("missing_reports.json  : missing=%d (mtime %s)"
      % (len(d["missing"]), __import__("time").strftime("%m-%d %H:%M",
         __import__("time").localtime(os.path.getmtime(os.path.join(ROOT, "研究脚本", "_数据", "missing_reports.json"))))))
print("未深挖清单.md 声明      :", re.search(r"共 (\d+) 个候选", open(LIST_MD, encoding="utf-8").read()).group(1),
      "| mtime", __import__("time").strftime("%m-%d %H:%M",
      __import__("time").localtime(os.path.getmtime(LIST_MD))))

idx = open(IDX, encoding="utf-8", newline="").read()
links = re.findall(r"\]\((\./[^)]+\.md)\)", idx)
broken = [l for l in links if not os.path.exists(os.path.join(REP, l[2:]))]
unlinked = [c for c in covered if "(./%s.md)" % c not in idx]
print("== 索引 ==")
print("links:", len(links), "| broken:", len(broken), "| 已有报告但未登记的卡片行:", len(unlinked))
for c in unlinked[:10]:
    print("   ", c)
print("概览计数行:", re.search(r"深度分析报告.*", idx).group(0)[:120])
print("CRLF:", "\r\n" in idx)

bl = open(BACKLOG, encoding="utf-8", newline="").read()
print("== 待办清单 ==")
print("CRLF:", "\r\n" in bl, "| 有本轮批量进度段:", "本轮批量进度" in bl)
for pat in (r"挖掉 (\d+) 个，剩 \*\*(\d+)\*\*", r"已挖 (\d+) 份", r"共 (\d+) 个候选", r"完整 (\d+) 项"):
    m = re.search(pat, bl)
    print("  %-22s %s" % (pat, m.groups() if m else "缺失"))
print("  表格行数(报告|为什么挖):", len(re.findall(r"^\| `[A-Za-z0-9_.\-]+` \|", bl, re.M)))

rm = open(RM, encoding="utf-8", newline="").read()
print("== README.md 计数 ==")
for m in re.finditer(r"\*\*(\d+) 份深度分析报告\*\*|\*\*(\d+) 份\*\*（", rm):
    print("  ", [g for g in m.groups() if g])
print("CRLF:", "\r\n" in rm)
