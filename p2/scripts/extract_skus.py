# -*- coding: utf-8 -*-
"""PDF 文本 → 结构化 SKU（LLM 批抽取 + 人工抽检）。

严格约束：
  * 模型只能"抽取"，不能"推断"——原文没有的字段必须返回 null，不许编；
  * 每条输出带 provenance（来源文件 + 页码），没出处的记录直接丢弃；
  * 抽完 --merge 进 data/structured/skus.json，verified 一律 false，等人抽检。

用法：
  python scripts/extract_skus.py --dry-run            # 先看第一条提示词长什么样
  python scripts/extract_skus.py --limit 2            # 只跑前 2 个窗口，验证格式
  python scripts/extract_skus.py --merge              # 全量 + 合并
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

FIELDS = [
    "sku_id", "category", "dims", "material", "friction_coef", "wear_rate",
    "axle_fit", "cross_refs", "price", "stock", "evidence", "notes",
]

SYSTEM = """你是工业资料结构化专家，只做"抽取"，没有的事不许编。
规则：
1) 只输出原文明确出现的信息；缺失就填 null（数字）或 []（数组），禁止猜测或补全。
2) 尺寸必须是原文数字，单位 mm；原文写法保留在 dims.raw_text。
3) 适配车桥只认原文写到的品牌+型号；没写就给空数组。
4) evidence 必须使用本页的 [[PAGE n]] 标记页号。
5) 输出 JSON 数组，每个元素含字段：%s。
6) 若本页没有任何产品行，输出 []。""" % ", ".join(FIELDS)


def page_windows(path: Path, size: int = 3):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    parts = re.split(r"\[\[PAGE (\d+)\]\]", txt)
    pages = []
    for i in range(1, len(parts), 2):
        pages.append((int(parts[i]), parts[i + 1]))
    for i in range(0, len(pages), size):
        chunk = pages[i:i + size]
        label = "%s 第 %d-%d 页" % (path.stem, chunk[0][0], chunk[-1][0])
        body = "".join("[[PAGE %d]]\n%s\n" % (n, t) for n, t in chunk)
        yield label, body


def clean(rec, source, page_default):
    out = {k: rec.get(k) for k in FIELDS}
    out["brand"] = rec.get("brand") or "冠英"
    prov = {"source_file": source, "source_page": page_default, "extractor": "llm_batch",
            "verified": False, "extracted_at": None}
    ev = out.get("evidence") or []
    if ev and isinstance(ev, list) and ev[0].get("page"):
        prov["source_page"] = ev[0]["page"]
    out["provenance"] = prov
    out["_placeholder"] = False
    if not out.get("sku_id"):
        return None
    if not out.get("evidence"):
        return None  # 无出处 = 不敢用
    return out


def completeness(rec: dict) -> int:
    n = 0
    d = rec.get("dims") or {}
    n += sum(1 for k in ("outer_dia_mm", "width_mm", "thickness_mm") if d.get(k))
    n += 1 if rec.get("material") not in (None, "未知") else 0
    n += len(rec.get("axle_fit") or []) > 0
    n += len(rec.get("cross_refs") or []) > 0
    n += 1 if (rec.get("price") or {}).get("range_cny") else 0
    n += 1 if rec.get("evidence") else 0
    return int(n)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=str(ROOT / "data" / "text"))
    ap.add_argument("--out", default=str(ROOT / "data" / "structured" / "skus.json"))
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 个窗口")
    ap.add_argument("--merge", action="store_true", help="合并进已有 skus.json")
    ap.add_argument("--dry-run", action="store_true", help="只打印提示词")
    args = ap.parse_args(argv)

    files = [p for p in sorted(Path(args.text).glob("*.txt")) if not p.name.startswith("_")]
    if not files:
        print("[!] 先跑 scripts/extract_text.py")
        return 1

    windows = []
    for f in files:
        windows.extend(page_windows(f))
    if args.limit:
        windows = windows[: args.limit]

    if args.dry_run:
        label, body = windows[0]
        print("=== SYSTEM ===\n%s\n=== USER (%s) ===\n%s" % (SYSTEM, label, body[:1500]))
        return 0

    from engine.llm import LLMUnavailable, json_call
    all_recs, failed = [], 0
    for i, (label, body) in enumerate(windows, 1):
        try:
            out = json_call(
                [{"role": "user", "content": "来源：%s\n\n%s\n\n请抽取本批次出现的产品行。" % (label, body)}],
                system=SYSTEM, max_tokens=3000,
            )
        except LLMUnavailable as e:
            print("[FATAL] %s —— 确认 .env 里的 GTM_HACK_API_KEY" % e)
            return 2
        recs = out if isinstance(out, list) else out.get("items", [])
        kept = 0
        for r in recs:
            c = clean(r, label, None)
            if c:
                all_recs.append(c)
                kept += 1
        print("[%d/%d] %-30s 抽取 %d 条，保留 %d 条" % (i, len(windows), label, len(recs), kept))

    target = Path(args.out)
    existing = []
    if args.merge and target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        existing = [r for r in existing if r.get("provenance", {}).get("extractor") != "llm_batch"]
    by_id = {r["sku_id"]: r for r in existing}
    for r in sorted(all_recs, key=completeness):
        by_id[r["sku_id"]] = r  # 后写的字段更全（已排序）
    merged = sorted(by_id.values(), key=lambda x: x.get("sku_id", ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    low = [r["sku_id"] for r in merged if completeness(r) < 4]
    print("\n写出 %d 条 → %s" % (len(merged), target))
    if low:
        print("[抽检] 字段不全（需人工核对或补资料）：%s" % ", ".join(low[:20]))
    print("[提醒] verified 全为 false；随机抽 10%%（>=3 条）对着 PDF 原件核对尺寸后再改 true。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
