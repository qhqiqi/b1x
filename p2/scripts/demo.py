# -*- coding: utf-8 -*-
"""演示脚本：把「客户怎么问 → 系统怎么答」跑成一段可录屏的文字。

用法：
    cd p2
    python scripts/demo.py              # 5 条固定演示查询
    python scripts/demo.py --json       # 给 P3 看的原始 JSON
    python scripts/demo.py --query "..."  # 单条

产出：data/reports/demo_transcript.md（可直接贴 PPT 附录 / 录屏字幕）
"""
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2"))

from engine.match import match_query  # noqa: E402
from engine.store import load_axles, load_skus  # noqa: E402

DEMO = [
    ("尺寸直查（修理工量出来的）", "147×100×14.5"),
    ("车桥口语（客户嘴里的说法）", "汉德 35 吨桥，前面那副"),
    ("适配名直查（销售常用）", "解放虎威前"),
    ("小数型号 + A/B 变体", "沃胜桥 11.5 吨的，A 款"),
    ("实测近似尺寸（容差内多候选）", "客户发来旧片，说大概是 151×80×13"),
    ("只有车型（必须追问，不瞎配）", "客户说这车是欧曼 400，要前片"),
]

BAR = "─" * 46


def fmt(c, i):
    d = (c.get("dims") or {}).get("raw_text") or "—"
    ev = (c.get("evidence") or [{}])[0]
    page = "第 %s 页" % ev.get("page") if ev.get("page") else "页码缺失"
    price = "询价确认（资料包无价格）" if not c.get("price") else c["price"]
    return ("  %d. %-22s 置信度 %s\n"
            "     规格 %s（外弧×宽度×厚度）\n"
            "     出处 %s %s\n"
            "     报价 %s\n"
            % (i, c["sku_id"], c["confidence"], d, ev.get("report_id", "—"), page, price))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--query")
    ap.add_argument("--out", default=str(ROOT / "data" / "reports" / "demo_transcript.md"))
    args = ap.parse_args(argv)

    skus, axles = load_skus(), load_axles()
    queries = [(args.query, args.query)] if args.query else DEMO
    lines = ["# Demo 文字稿（自动生成，可直接做录屏字幕）", "",
             "> 数据：%d 条 SKU（冠隆 + kooying 鼓式适配表），全部带产品册页码。" % len(skus),
             "> 引擎：纯规则离线，毫秒级；无网络、无大模型也能跑。", ""]

    for title, q in queries:
        r = match_query(q)
        print("【提问】%s" % q)
        print("【场景】%s" % title)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
            continue
        p = r["parsed"]
        slots = []
        if p["has_dims"]:
            slots.append("尺寸 " + (p["dims"].get("raw_text") or "?"))
        if p["axles"]:
            slots.append("车桥 " + "/".join(a["axle_id"] for a in p["axles"]))
        if p["codes"]:
            slots.append("编码 " + "/".join(p["codes"]))
        if not slots and r["candidates"]:
            import re as _re
            m2 = _re.search(r"适配名命中 (\S+)", r["candidates"][0].get("reason", ""))
            if m2:
                slots.append("适配名 " + m2.group(1))
        print("【识别】%s" % ("；".join(slots) if slots else "未识别到硬线索（尺寸/车桥/编码）"))
        if r["candidates"]:
            print("【结果】Top%d" % len(r["candidates"]))
            for i, c in enumerate(r["candidates"], 1):
                print(fmt(c, i), end="")
        else:
            print("【结果】无可靠候选 —— 按红线只追问，不瞎配")
        if r["followups"]:
            print("【追问】")
            for f in r["followups"]:
                print("   - " + f)
        print("%s 耗时 %d ms ｜ 模式 %s" % (BAR, r["elapsed_ms"], r["mode"]))
        print()

        lines.append("## %s" % q)
        lines.append("")
        lines.append("场景：%s ｜ 耗时 %d ms ｜ 模式 %s" % (title, r["elapsed_ms"], r["mode"]))
        lines.append("")
        if r["candidates"]:
            lines.append("| # | 型号 | 置信 | 规格 | 出处 |")
            lines.append("|---|---|---|---|---|")
            for i, c in enumerate(r["candidates"], 1):
                ev = (c.get("evidence") or [{}])[0]
                lines.append("| %d | %s | %s | %s | %s p%s |" % (
                    i, c["sku_id"], c["confidence"],
                    (c.get("dims") or {}).get("raw_text"), ev.get("report_id"), ev.get("page")))
        else:
            lines.append("无可靠候选，返回追问：")
            for f in r["followups"]:
                lines.append("- " + f)
        lines.append("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("写出 %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
