# -*- coding: utf-8 -*-
"""把 OCR 结果（data/ocr/*.json）拼成产品册行。

只做"抽取 + 报告"，**不直接并进 skus.json**：
OCR 有误识别风险，必须先人工看 data/reports/ocr_rows.md 的抽样，
认可后再跑 --merge（并保留 extractor="ocr"，verified=false）。

用法：
    python p2/scripts/ocr_to_rows.py
    python p2/scripts/ocr_to_rows.py --merge     # 审过之后再用
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2" / "scripts"))

DIM = re.compile(r"^(\d{2,4})\s*[×xX*]\s*(\d{2,3})\s*[×xX*]\s*(\d{1,2}(?:\.\d)?)(?:\s*/\s*(\d{1,2}(?:\.\d)?))?$")
CJK = re.compile(r"[\u4e00-\u9fff]")
BAD = re.compile(r"[\u4e00-\u9fff]")


HEADER = ("外弧", "宽度", "厚度", "孔数", "名称", "适配车型", "图样", "鼓式")


def is_name(t):
    t = t.strip()
    if any(h in t for h in HEADER):
        return False
    if len(t) < 2 or DIM.match(t) or BAD.search(t) and len(t) > 12:
        return False
    if re.fullmatch(r"[\d\s./×xX+\-()]+", t):
        return False
    return bool(CJK.search(t)) or bool(re.fullmatch(r"(?i)GY?s?[-\s]?\d{2,4}", t)) or bool(re.fullmatch(r"[A-Za-z]{2,}\d{1,3}[A-Za-z]?", t))


def near(items, x, y, dx=160, dy=110):
    best, bd = None, 1e9
    for it in items:
        if not (0 < y - it["y"] <= dy):
            continue
        if abs(it["x"] - x) > dx:
            continue
        d = (y - it["y"]) + abs(it["x"] - x) * 0.3
        if d < bd:
            best, bd = it, d
    return best


def model_text(items, x, y):
    """同行右侧的适配车型文字（x 大于尺寸列，y 相近）。"""
    cands = [it["text"] for it in items if abs(it["y"] - y) <= 18 and it["x"] > x + 220]
    return " ".join(cands)[:60]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args(argv)

    rows = []
    for f in sorted((ROOT / "data" / "ocr").glob("*.json")):
        if f.name.startswith("_"):
            continue
        items = json.loads(f.read_text(encoding="utf-8"))
        stem, page = f.stem.rsplit("_p", 1)
        for it in items:
            m = DIM.match(it["text"].strip())
            if not m or it["conf"] < 0.85:
                continue
            nm = near(items, it["x"], it["y"])
            if not nm or not is_name(nm["text"]):
                continue
            if DIM.search(nm["text"]) or re.search(r"[×xX*]\s*\d", nm["text"]):
                continue
            rows.append({
                "row_id": "O%04d" % (len(rows) + 1),
                "file": stem, "page": int(page),
                "name": nm["text"].strip(), "raw_dims": m.group(0),
                "arc_mm": float(m.group(1)), "width_mm": float(m.group(2)),
                "thickness_mm": float(m.group(3)),
                "thickness_alt_mm": float(m.group(4)) if m.group(4) else None,
                "fit_model_raw": model_text(items, it["x"], it["y"]),
                "conf": round(min(it["conf"], nm["conf"]), 3),
            })

    # 去重（同页同名同尺寸）
    seen, uniq = set(), []
    for r in rows:
        k = (r["page"], r["name"], r["raw_dims"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)

    out = ROOT / "data" / "structured" / "catalog_rows_ocr.json"
    out.write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# OCR 行抽取结果（**未并入主数据**）", "",
          "共 %d 行（去重后）。抽取规则：尺寸 token 完整匹配 + OCR 置信度 ≥0.85 + 上方有名称。"
          % len(uniq), "", "| 页 | 名称 | 外弧×宽×厚 | 置信 | 右侧适配车型(OCR) |", "|---|---|---|---|---|"]
    for r in uniq[:40]:
        md.append("| %s p%d | %s | %s | %.2f | %s |" % (
            r["file"][:6], r["page"], r["name"], r["raw_dims"], r["conf"], r["fit_model_raw"]))
    rp = ROOT / "data" / "reports" / "ocr_rows.md"
    rp.write_text("\n".join(md), encoding="utf-8")
    if args.merge:
        from parse_catalog_words import to_sku
        skus = []
        for r in uniq:
            s = to_sku({"name": r["name"], "raw_dims": r["raw_dims"], "arc_mm": r["arc_mm"],
                        "width_mm": r["width_mm"], "thickness_mm": r["thickness_mm"],
                        "thickness_alt_mm": r["thickness_alt_mm"], "file": r["file"],
                        "page": r["page"], "extras": []})
            s["provenance"]["extractor"] = "rule_layout"
            s["provenance"]["notes"] = "OCR 抽取（RapidOCR），未经人工核对，慎用"
            skus.append(s)
        dst = ROOT / "data" / "structured" / "skus_ocr.json"
        dst.write_text(json.dumps(skus, ensure_ascii=False, indent=2), encoding="utf-8")
        print("合并（单独文件，不动主数据）→ %s：%d 条" % (dst, len(skus)))

    print("抽取 %d 行（去重 %d）→ %s" % (len(rows), len(uniq), out))
    print("抽样报告 → %s" % rp)
    for r in uniq[:12]:
        print("  p%-3d %-16s %-18s %.2f %s" % (r["page"], r["name"], r["raw_dims"], r["conf"], r["fit_model_raw"][:28]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
