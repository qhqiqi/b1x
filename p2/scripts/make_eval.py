# -*- coding: utf-8 -*-
"""由主数据生成回归评估集（20 条），跑 run_eval.py 用。

注意：回归集由主数据自动派生，用来防回归，不能当"独立准确率"对外报；
     对外报的 20 条要用人工挑选的、来自真实询价/销售提问的题。
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2"))

skus = json.loads((ROOT / "data" / "structured" / "skus.json").read_text(encoding="utf-8"))
random.seed(7)
cases, cid = [], 0


def add(inp, exp, why):
    global cid
    cid += 1
    cases.append({"case_id": cid, "input": inp, "expected": exp, "why": why})


# 1) 尺寸直查（10 条，尺寸唯一的行）
by_dims = {}
for s in skus:
    d = s["dims"]
    by_dims.setdefault((d["arc_mm"], d["width_mm"], d["thickness_mm"]), []).append(s)
uniq = [v[0] for k, v in by_dims.items() if len(v) == 1]
for s in random.sample(uniq, min(10, len(uniq))):
    add(s["dims"]["raw_text"], {"type": "match", "sku": [s["sku_id"]]}, "尺寸直查")

# 2) 名称/车桥直查（4 条）
named = [s for s in skus if len(s["fit_name"]) >= 4]
for s in random.sample(named, min(4, len(named))):
    add(s["fit_name"], {"type": "match", "top3": True, "sku": [s["sku_id"]]}, "按适配名查")

# 3) 只有宽×长（缺厚度）→ 允许 Top3 命中（3 条）
for s in random.sample([x for x in uniq if x["dims"]["thickness_mm"]], 3):
    d = s["dims"]
    add("%g×%g" % (d["arc_mm"], d["width_mm"]),
        {"type": "match", "top3": True, "sku": [s["sku_id"]]}, "缺厚度，容许 Top3")

# 4) 陷阱（3 条）：必须追问
add("2019 款丰田 Hilux，后桥换过", {"type": "ask_followup", "min_questions": 2}, "车型不可靠")
add("帮我配一下刹车片", {"type": "ask_followup", "min_questions": 1}, "零实体")
add("刹车片异响、抖动怎么办", {"type": "ask_followup", "min_questions": 1}, "售后问题")

out = ROOT / "data" / "eval" / "cases.jsonl"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cases) + "\n", encoding="utf-8")
print("生成 %d 条 → %s" % (len(cases), out))
