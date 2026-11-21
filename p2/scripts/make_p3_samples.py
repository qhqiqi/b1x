# -*- coding: utf-8 -*-
"""给 P3 的喂料包：跑 5 条演示查询，把真实 JSON 落盘，接口字段以真实输出为准。

用法（仓库根目录）：
    python p2/scripts/make_p3_samples.py

产出：data/reports/p3_samples.jsonl（每行一条 query 的完整返回）
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2"))

from engine.match import match_query  # noqa: E402

QUERIES = [
    ("尺寸直查", "147×100×14.5"),
    ("车桥口语", "汉德 35 吨桥，前面那副"),
    ("适配名直查", "解放虎威前"),
    ("只有车型（应追问，不瞎配）", "客户说这车是欧曼 400"),
    ("内部型号", "GY1054"),
]


def main():
    out = ROOT / "data" / "reports" / "p3_samples.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for label, q in QUERIES:
            r = match_query(q)
            row = {"label": label, "request": q, "response": r}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n = len(r.get("candidates") or [])
            top = (r.get("candidates") or [{}])[0].get("sku_id", "—")
            print("%-22s %-24s mode=%-4s cand=%d top=%s %sms"
                  % (label, q, r.get("mode"), n, top, r.get("elapsed_ms")))
    print("写出: %s" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
