# -*- coding: utf-8 -*-
"""生成人工抽检工单：从 120 条 SKU 里按页等距抽 12 条（10%），写成一张核对表。

用法（仓库根目录）：
    python p2/scripts/make_spot_check.py            # 默认 12 条，种子固定，可复现
    python p2/scripts/make_spot_check.py --n 30     # 扩到 30 条

产出：data/reports/spot_check_12.md
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKUS = ROOT / "data" / "structured" / "skus.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT_DIR = ROOT / "data" / "reports"

CATALOG_NAME = {
    "kooying_catalog": "kooying catalog",
    "冠隆产品册": "冠隆产品册",
    "2026年浙江冠英企业介绍": "企业介绍",
}


def load():
    recs = json.loads(SKUS.read_text(encoding="utf-8"))
    return [r for r in recs if not r.get("_placeholder")]


def pick(recs, n):
    """先保证「每个原页至少抽 1 条」，剩下的名额再轮流补。

    抽检的意义是验「解析在每一页都对」，所以页面覆盖优先于条数均匀。
    """
    groups = {}
    for r in recs:
        key = (r["provenance"]["source_file"], r["provenance"]["source_page"])
        groups.setdefault(key, []).append(r)

    keys = sorted(groups)
    ordered = {k: sorted(v, key=lambda r: r["sku_id"]) for k, v in groups.items()}
    rows = [ordered[k][0] for k in keys]
    pool = {k: ordered[k][1:] for k in keys}

    while len(rows) < n:
        added = False
        for k in keys:
            if len(rows) >= n:
                break
            if pool[k]:
                rows.append(pool[k].pop(0))
                added = True
        if not added:
            break

    rows = rows[:n]
    return sorted(
        rows,
        key=lambda r: (r["provenance"]["source_file"], r["provenance"]["source_page"], r["sku_id"]),
    )


def render(rows, n, total_recs, total_pages):
    from spotcheck import machine_check  # 复用独立复核
    covered = len({(r["provenance"]["source_file"], r["provenance"]["source_page"]) for r in rows})
    lines = []
    lines.append(
        "# 人工抽检工单（%d 条 / %d 条，%.0f%%｜覆盖 %d / %d 个原页）\n"
        % (n, total_recs, 100.0 * n / max(total_recs, 1), covered, total_pages)
    )
    lines.append(
        "> 全部 %d 条数据来自 %d 个原页，本单已保证**每个原页至少 1 条**。\n"
        "> 目的：这是答辩里说「数据可溯源」的唯一凭据。\n"
        "> 做法：打开对应产品册 PDF 的对应页，核对「适配名」和「外弧×宽度×厚度」是否与原文一致。\n"
        "> 核完把该条的 `provenance.verified` 改 true、`verified_by` 填你的名字：\n"
        ">   `python p2/scripts/mark_verified.py --sku <sku_id> --by P2`\n"
        "> 不一致的不要改 true，写在「差异」列里，回到解析脚本修。\n"
        % (total_recs, total_pages)
    )
    lines.append("> 机器预判是**独立复核**（用版式文本判断名称与尺寸是否同页同区），只用来排优先级：先核「可疑」的。")
    lines.append("| # | sku_id | 适配名 | 尺寸（原文） | 出处 | 机器预判 | 核对 | 差异 / 备注 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        src = r["provenance"]["source_file"]
        page = r["provenance"]["source_page"]
        book = CATALOG_NAME.get(src, src)
        dims = (r.get("dims") or {}).get("raw_text") or "—"
        lines.append(
            "| %d | `%s` | %s | %s | %s p%d | %s | ☐ 一致 / ☐ 不一致 |  |"
            % (i, r["sku_id"], r.get("fit_name") or "—", dims, book, page, machine_check(r))
        )
    lines.append("")
    lines.append("## 抽检结论（核完填这一段，直接抄进 PPT）\n")
    lines.append("- 核对条数：__ / %d" % n)
    lines.append("- 一致：__ 条；不一致：__ 条")
    lines.append("- 覆盖率：__ / %d = __%%" % total_recs)
    lines.append("- 不一致的原因归类：__")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()

    recs = load()
    rows = pick(recs, args.n)
    total_pages = len({(r["provenance"]["source_file"], r["provenance"]["source_page"]) for r in recs})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / ("spot_check_%d.md" % args.n)
    out.write_text(render(rows, args.n, len(recs), total_pages), encoding="utf-8")
    print("抽出 %d 条 -> %s" % (len(rows), out.relative_to(ROOT)))


if __name__ == "__main__":
    main()
