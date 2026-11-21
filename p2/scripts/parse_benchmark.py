# -*- coding: utf-8 -*-
"""把企业介绍 p25「行业对比检测 2」的 14 项台架数据抽成结构化 JSON。

这张表是资料包里唯一"可引用的检测数据"：同一台架、同一条件下的冠英 vs NC 对比。
注意：**企业级对比，不是单型号数据**，不许挂到具体 SKU 上。

用法：python p2/scripts/parse_benchmark.py
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
LINE = re.compile(r"^(\d{1,2})\s+(.+?)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*$")


def main() -> int:
    txt = (ROOT / "data" / "text" / "2026年浙江冠英企业介绍.txt").read_text(encoding="utf-8")
    pages = re.split(r"\[\[PAGE (\d+)\]\]", txt)
    body = ""
    for i in range(1, len(pages), 2):
        if pages[i] == "25":
            body = pages[i + 1]
            break
    items = []
    for line in body.splitlines():
        m = LINE.match(line.strip())
        if not m:
            continue
        items.append({
            "no": int(m.group(1)), "item": m.group(2).strip(),
            "kooying": float(m.group(3)), "nc": float(m.group(4)), "delta": float(m.group(5)),
        })
    out = {
        "source": {"file": "2026年浙江冠英企业介绍", "page": 25, "kind": "对比检测"},
        "title": "行业对比检测 2（冠英 vs NC）",
        "scope": "企业级台架对比，非单型号数据；对外引用需注明",
        "items": items,
    }
    dst = ROOT / "data" / "structured" / "benchmark.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for it in items:
        print("%2d %-24s 冠英=%-7s NC=%-7s 差=%s" % (it["no"], it["item"], it["kooying"], it["nc"], it["delta"]))
    print("\n共 %d 项 → %s" % (len(items), dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
