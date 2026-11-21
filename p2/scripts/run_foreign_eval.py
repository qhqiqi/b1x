# -*- coding: utf-8 -*-
"""海外对码评测：外商报 FMSI/OE/WVA/英制尺寸，看能不能对回出口册里的型号。"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"Y:\hks")
sys.path.insert(0, str(ROOT / "p2"))
from engine.match import match_query  # noqa: E402

cases = [json.loads(l) for l in (ROOT / "data" / "eval" / "cases_foreign.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
rows, ok_n, t_ms = [], 0, []
for c in cases:
    r = match_query(c["input"])
    t_ms.append(r["elapsed_ms"])
    exp = c["expected"]
    if exp.get("none"):
        ok = not r["export_matches"] and r["mode"] == "ask"
        got = "（正确追问）" if ok else "有对码: %s" % [e["shoe_code"] for e in r["export_matches"]]
    else:
        got = r["export_matches"][0]["shoe_code"] if r["export_matches"] else "无"
        ok = got == exp["shoe_code"]
    ok_n += ok
    rows.append((c["case_id"], c["input"], exp.get("shoe_code") or "无对码", got, ok,
                 r["export_matches"][0]["page"] if r["export_matches"] else "—",
                 r["export_matches"][0]["why"] if r["export_matches"] else ""))

md = ["# 海外对码评测（%d 条）" % len(cases), "",
      "> 场景：外商报 FMSI 号 / OE 号 / WVA 衬片号 / 英制尺寸，看能不能对回出口册（kooying p32–34）的型号。",
      "> 数据来自图页 OCR 重建，**未人工核对**，结论只能说「册子上这么写的」。", "",
      "| # | 外商说法 | 期望 | 实际 | 结果 | 证据页 | 命中理由 |", "|---|---|---|---|---|---|---|"]
for cid, q, exp, got, ok, pg, why in rows:
    md.append("| %s | %s | %s | %s | %s | %s | %s |" % (cid, q, exp, got, "✅" if ok else "❌", pg, why))
md += ["", "**通过 %d/%d（%.0f%%）**，平均 %.1f ms。" % (
    ok_n, len(cases), 100.0 * ok_n / len(cases), sum(t_ms) / max(len(t_ms), 1))]
out = ROOT / "data" / "reports" / "foreign_suite.md"
out.write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md[-12:]))
print("->", out)
