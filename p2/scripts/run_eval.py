# -*- coding: utf-8 -*-
"""跑 20 条评估集，输出可上 PPT 的准确率数字。

指标（分开报，别只报一个总数）：
  * 正例 Top1 / Top3 命中率
  * 陷阱题"是否正确追问"（有没有给出高置信假答案）
  * 编码映射命中率
  * 平均耗时

用法：
  python scripts/run_eval.py
  python scripts/run_eval.py --llm --demo-data     # 联调版（有 key 时）
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2"))

from engine.match import match_query
from engine.store import load_skus
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass



def run(cases, use_llm, include_placeholders):
    skus = load_skus(include_placeholders=include_placeholders)
    rows, t0 = [], time.time()
    for c in cases:
        r = match_query(c["input"], skus=skus, use_llm=use_llm,
                        include_placeholders=include_placeholders)
        top1 = r["candidates"][0]["sku_id"] if r["candidates"] else None
        top3 = [x["sku_id"] for x in r["candidates"]]
        exp = c["expected"]
        kind = exp["type"]
        ok = False
        if kind == "match":
            pool = top3 if exp.get("top3") else ([top1] if top1 else [])
            ok = any(s in (exp.get("sku") or []) for s in pool)
        elif kind == "cross_ref":
            ok = any(s in top3 for s in (exp.get("sku") or []))
        elif kind == "ask_followup":
            confident = [x for x in r["candidates"] if x["confidence"] == "高"]
            ok = (not confident) and len(r["followups"]) >= exp.get("min_questions", 1)
        rows.append({"case_id": c["case_id"], "input": c["input"], "type": kind,
                     "ok": ok, "top1": top1, "top3": top3, "followups": len(r["followups"]),
                     "ms": r["elapsed_ms"]})
    el = time.time() - t0
    return rows, el


def summarize(rows):
    def rate(t):
        sub = [r for r in rows if r["type"] == t]
        return (sum(r["ok"] for r in sub), len(sub))
    hit1, n1 = rate("match")
    mapok, n2 = rate("cross_ref")
    ask, n3 = rate("ask_followup")
    tot_ok = sum(r["ok"] for r in rows)
    return {
        "正例 Top1": (hit1, n1), "编码映射（Top3）": (mapok, n2),
        "陷阱题正确追问": (ask, n3), "总体": (tot_ok, len(rows)),
        "平均耗时ms": round(sum(r["ms"] for r in rows) / max(len(rows), 1), 1),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(ROOT / "data" / "eval" / "cases.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "reports" / "eval_report.md"))
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--demo-data", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.cases)
    cases = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows, el = run(cases, args.llm, args.demo_data)
    s = summarize(rows)

    lines = ["# 评估报告（%d 条）" % len(rows), "",
             "模式：%s%s" % ("LLM 消歧" if args.llm else "纯规则",
                             "，含占位数据（仅供联调，不可上 PPT）" if args.demo_data else ""), "",
             "| 指标 | 结果 | 占比 |", "|---|---|---|"]
    for k, v in s.items():
        if isinstance(v, tuple):
            lines.append("| %s | %d/%d | %.0f%% |" % (k, v[0], v[1], 100.0 * v[0] / max(v[1], 1)))
        else:
            lines.append("| %s | %s | - |" % (k, v))
    lines += ["", "总耗时 %.1fs" % el, "", "## 逐条", "",
              "| # | 输入 | 类型 | 结果 | Top1 | 追问数 |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %d |" % (
            r["case_id"], r["input"][:34], r["type"], "✅" if r["ok"] else "❌", r["top1"] or "-", r["followups"]))
    misses = [r for r in rows if not r["ok"]]
    if misses:
        lines += ["", "## 失败样本（优先修这些）", ""]
        for r in misses:
            lines.append("- #%s %s → 期望 %s，实际 %s" % (r["case_id"], r["input"], r["type"], r["top3"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:12]))
    print("\n写出: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
