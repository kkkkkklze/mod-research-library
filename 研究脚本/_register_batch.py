"""Register newly written depth reports into README-索引.md.

- flips the 深度报告 "—" cell into a link for every card row that now has a report
- recomputes the overview counts from disk (cards / repo-level reports / total md)
- keeps CRLF
Usage: py _register_batch.py            # scans all cards, links whatever exists
"""
import os
import re

ROOT = r""
REP = os.path.join(ROOT, "分析报告", "_分析报告")
CARD = os.path.join(REP, "_卡片")
IDX = os.path.join(REP, "README-索引.md")

PREFIX = ("深挖__", "对照__", "设计__", "专题__", "TeaCon", "DBE__", "README", "_", "四包")

cards = sorted(f[:-3] for f in os.listdir(CARD) if f.endswith(".md"))
have = {f[:-3] for f in os.listdir(REP)
        if f.endswith(".md") and not f.startswith(PREFIX)}
total_md = len([f for f in os.listdir(REP) if f.endswith(".md")])
covered = [c for c in cards if c in have]
print("cards=%d repo_reports=%d(matched=%d) total_md=%d"
      % (len(cards), len(have), len(covered), total_md))

raw = open(IDX, encoding="utf-8", newline="").read()
had_crlf = "\r\n" in raw
lines = raw.replace("\r\n", "\n").split("\n")

linked = 0
for i, line in enumerate(lines):
    if not line.startswith("|") or "./_卡片/" not in line:
        continue
    m = re.search(r"\./_卡片/([^)/]+)\.md", line)
    if not m:
        continue
    stem = m.group(1)
    if stem not in have:
        continue
    link = " [报告](./%s.md) " % stem
    if link.strip() in line:
        continue
    cells = line.split("|")
    idxs = [j for j, c in enumerate(cells) if c.strip() in ("—", "-")]
    if not idxs:
        continue
    cells[idxs[-1]] = link
    lines[i] = "|".join(cells)
    linked += 1
print("newly linked rows:", linked)

text = "\n".join(lines)
pat = re.compile(r"深度分析报告（子 agent 逐仓库阅读源码后撰写，含文件路径级引用）: \d+ 份"
                 r"（其中 \*\*\d+ 份\*\*与速览卡片一一对应，其余 \d+ 份为[^）]*）")
repl = ("深度分析报告（子 agent 逐仓库阅读源码后撰写，含文件路径级引用）: %d 份"
        "（其中 **%d 份**与速览卡片一一对应，其余 %d 份为专题/横向/设计/版本差异类）"
        % (total_md, len(covered), total_md - len(covered)))
text, n = pat.subn(repl, text)
print("overview count updated:", n)

out = text.replace("\n", "\r\n") if had_crlf else text
open(IDX, "w", encoding="utf-8", newline="").write(out)
print("wrote", IDX, len(out.split("\n")), "lines")
