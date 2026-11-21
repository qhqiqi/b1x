# -*- coding: utf-8 -*-
"""版式文本 → 产品册表格行（确定性解析，不用 LLM，可复现）。

原理：pypdf layout 模式保留了列的横向位置，同一行里"名称 / 尺寸 / 数量 / 孔位"
是固定顺序出现的；跨行的名称按 FIFO 与尺寸配对。

产出：data/structured/catalog_rows.json
用法：
  python p2/scripts/parse_catalog.py            # 解析 + 打印自检
  python p2/scripts/parse_catalog.py --merge    # 同时合并进 skus.json
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]

# PDF 字体把这些字映射到了 CJK 部首区，必须归一化，否则搜索"解放虎威"搜不到"解放⻁威"
RADICALS = {"⻛": "风", "⻰": "龙", "⻁": "虎", "⻢": "马", "⻋": "车", "⻥": "鱼", "⻦": "鸟",
            "⻨": "麦", "⻩": "黄", "⻭": "齿", "⻮": "齿", "⻬": "齐", "⻫": "齐", "⻅": "见",
            "⻓": "长", "⻔": "门", "⻜": "飞", "⻙": "韦", "⻚": "页", "⻝": "食", "⻤": "鬼",
            "⻧": "卤", "⻪": "黾", "⻯": "龙", "⻲": "龟", "⻳": "龟", "⻃": "臣", "⻇": "臣"}

DIM = re.compile(r"(\d{2,4})[×xX](\d{2,3})[×xX](\d{1,2}(?:\.\d)?)(?:/(\d{1,2}(?:\.\d)?))?")
CJK = re.compile(r"[\u4e00-\u9fff]")
NUMLIKE = re.compile(r"^\(?\d{1,3}(?:\.\d)?\.?\)?$")


def clean(s: str) -> str:
    s = "".join(RADICALS.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", " ", s).strip()


def looks_name(tok: str) -> bool:
    if not tok or DIM.search(tok) or NUMLIKE.match(tok):
        return False
    if CJK.search(tok):
        return True
    return bool(re.fullmatch(r"(?i)gy?s?[-\s]?\d{2,4}", tok))


def parse_page(pno: int, body: str, fname: str, start_id: int):
    rows = []
    buf = []          # 跨行待配对的名字
    pending = None    # 当前行内尚未配对的名字
    for line in body.splitlines():
        if not line.strip():
            continue
        flat = [clean(t) for t in re.split(r"\s{2,}|\s", line.strip()) if t]
        i = 0
        while i < len(flat):
            tok = flat[i]
            if DIM.fullmatch(tok):
                name = pending if pending else (buf.pop(0) if buf else None)
                pending = None
                extras = []
                j = i + 1
                while j < len(flat) and NUMLIKE.match(flat[j]) and not looks_name(flat[j]):
                    extras.append(flat[j].lstrip("(.").rstrip(".)."))
                    j += 1
                    if len(extras) >= 3:
                        break
                m = DIM.fullmatch(tok)
                rows.append({
                    "row_id": "R%04d" % (start_id + len(rows)),
                    "file": fname.replace(".txt", ""), "page": pno,
                    "name": name,
                    "raw_dims": tok,
                    "width_mm": float(m.group(1)), "length_mm": float(m.group(2)),
                    "thickness_mm": float(m.group(3)),
                    "thickness_alt_mm": float(m.group(4)) if m.group(4) else None,
                    "extras": extras,
                })
                i = j
                continue
            if NUMLIKE.match(tok) and pending:
                # 名称后面直接跟数字、没有尺寸 → 该行尺寸在 PDF 里是旋转/图片文字被丢掉了
                rows.append({"row_id": "R%04d" % (start_id + len(rows)), "file": fname.replace(".txt", ""),
                             "page": pno, "name": pending, "raw_dims": None,
                             "width_mm": None, "length_mm": None, "thickness_mm": None,
                             "thickness_alt_mm": None, "extras": [tok]})
                pending = None
                i += 1
                continue
            if looks_name(tok):
                # 名称被空格拆成两段（"小J6" + "80宽"、"福田80" + "宽"）时合并
                if pending and (tok in ("宽", "前", "后") or tok.startswith(("80宽", "宽"))):
                    pending = pending + tok
                else:
                    if pending:
                        buf.append(pending)
                    pending = tok
            i += 1
        if pending:
            buf.append(pending)
            pending = None
    return rows


def parse_file(path: Path, start_id: int):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    pages = re.split(r"\[\[PAGE (\d+)\]\]", txt)
    rows = []
    for i in range(1, len(pages), 2):
        rows += parse_page(int(pages[i]), pages[i + 1], path.name, start_id + len(rows))
    return rows


def to_sku(row: dict) -> dict:
    name = row["name"] or "未命名"
    sid = "FIT-" + re.sub(r"[^\w\u4e00-\u9fff]+", "", name)[:18]
    pos = "前" if "前" in name else ("后" if "后" in name else "未知")
    abs_flag = "ABS" in name.upper() or "（ABS）" in name or "(ABS)" in name
    return {
        "sku_id": sid,
        "brand": "冠英",
        "category": "鼓式",
        "fit_name": name,
        "position": pos,
        "abs": abs_flag,
        "part_no": name if re.fullmatch(r"(?i)GY?s?[-\s]?\d{2,4}", name) else None,
        "dims": {
            "width_mm": row["width_mm"], "length_mm": row["length_mm"],
            "thickness_mm": row["thickness_mm"], "thickness_alt_mm": row["thickness_alt_mm"],
            "outer_dia_mm": None, "raw_text": row["raw_dims"],
        },
        "material": "未知",
        "axle_fit": [],
        "cross_refs": [],
        "extras": {"cols": row["extras"]},
        "evidence": [{"report_id": row["file"], "page": row["page"],
                      "snippet": "%s %s" % (name, row["raw_dims"]), "kind": "产品册"}],
        "price": None,
        "stock": "未知",
        "provenance": {"source_file": row["file"], "source_page": row["page"],
                       "extracted_at": "2026-11-21", "extractor": "rule_layout",
                       "verified": False, "verified_by": None, "notes": "版式解析，需抽检"},
        "_placeholder": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=str(ROOT / "data" / "text_layout"))
    ap.add_argument("--rows-out", default=str(ROOT / "data" / "structured" / "catalog_rows_layout.json"))
    ap.add_argument("--merge", action="store_true", help="合并进 skus.json")
    args = ap.parse_args(argv)

    files = [p for p in sorted(Path(args.text).glob("*.txt")) if not p.name.startswith("_")]
    all_rows, rows = [], 0
    for f in files:
        r = parse_file(f, rows)
        all_rows += r
        rows += len(r)
        if r:
            print("%-28s 行 %d（页 %d-%d）" % (f.stem, len(r), min(x["page"] for x in r), max(x["page"] for x in r)))
    named = [x for x in all_rows if x["name"]]
    print("\n合计 %d 行，有名称 %d 行，缺名称 %d 行" % (len(all_rows), len(named), len(all_rows) - len(named)))

    out = Path(args.rows_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("写出 %s" % out)

    if args.merge:
        skus = [to_sku(r) for r in named]
        seen, uniq = set(), []
        for s in skus:
            key = (s["sku_id"], s["dims"]["raw_text"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(s)
        tgt = ROOT / "data" / "structured" / "skus.json"
        old = json.loads(tgt.read_text(encoding="utf-8")) if tgt.exists() else []
        keep = [x for x in old if not x.get("_placeholder")]
        merged = keep + uniq
        tgt.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        print("合并：旧 %d 条 + 产品册 %d 条 → %d 条" % (len(keep), len(uniq), len(merged)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
