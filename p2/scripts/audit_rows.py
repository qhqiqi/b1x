# -*- coding: utf-8 -*-
"""全量一致性审计：对 120 条 SKU 逐条做"独立复核"，输出通过率与可疑清单。

复核逻辑与抽取器无关：用版式文本判断「名称与尺寸是否同页同区」。
- 机器一致(同行)   ：名称和尺寸在同一行
- 机器一致(上下行) ：名称在上方 1-2 行且那行不含别的尺寸串
- 可疑            ：都对不上（可能是串行、或该页在图片层需人眼）

用法：python p2/scripts/audit_rows.py
产出：data/reports/consistency.md
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2" / "scripts"))

from spotcheck import machine_check  # noqa: E402


def main() -> int:
    skus = json.loads((ROOT / "data" / "structured" / "skus.json").read_text(encoding="utf-8"))
    stat = {}
    rows = []
    for s in skus:
        if s.get("_placeholder"):
            continue
        v = machine_check(s)
        stat[v] = stat.get(v, 0) + 1
        rows.append((s["sku_id"], s.get("fit_name"), (s.get("dims") or {}).get("raw_text"),
                     (s.get("provenance") or {}).get("source_file"),
                     (s.get("provenance") or {}).get("source_page"), v))

    total = sum(stat.values())
    good = sum(n for k, n in stat.items() if k.startswith("机器一致"))
    bad = total - good
    md = ["# 全量一致性审计（%d 条）" % total, "",
          "- 机器复核通过：**%d/%d = %.1f%%**" % (good, total, 100.0 * good / total if total else 0),
          "- 可疑：%d 条" % bad, "",
          "| 结论 | 条数 |", "|---|---|"]
    for k, n in sorted(stat.items(), key=lambda x: -x[1]):
        md.append("| %s | %d |" % (k, n))
    if bad:
        md += ["", "## 可疑清单（人眼优先看这些）", "",
               "| sku_id | 适配名 | 尺寸 | 文件 | 页 |", "|---|---|---|---|---|"]
        for r in rows:
            if not r[5].startswith("机器一致"):
                md.append("| %s | %s | %s | %s | %s |" % (r[0], r[1], r[2], r[3], r[4]))
    out = ROOT / "data" / "reports" / "consistency.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")

    print("全量 %d 条：通过 %d（%.1f%%），可疑 %d" % (total, good, 100.0 * good / total if total else 0, bad))
    for k, n in sorted(stat.items(), key=lambda x: -x[1]):
        print("  %-16s %d" % (k, n))
    for r in rows:
        if not r[5].startswith("机器一致"):
            print("  可疑 %-22s %-18s %s p%s" % (r[0], r[2], r[3], r[4]))
    print("→ %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
