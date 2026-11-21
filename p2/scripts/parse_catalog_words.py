# -*- coding: utf-8 -*-
"""按 PDF 字符坐标解析产品册表格（不依赖阅读顺序，最可靠）。

做法：
  1) 取每个文本块的 (x, y, 字号)，按 y 聚类成"视觉行"；
  2) 行内按 x 合并相邻块 → 完整名称/尺寸（PDF 常把一个词拆成多块）；
  3) 名称在尺寸上方同一列 → 用 (dx, dy) 最近邻配对；
  4) 配不到的尺寸/名称单独留痕，不猜。

用法：python p2/scripts/parse_catalog_words.py
产出：data/structured/catalog_rows.json
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

RADICALS = {"⻛": "风", "⻰": "龙", "⻁": "虎", "⻢": "马", "⻋": "车", "⻥": "鱼", "⻦": "鸟",
            "⻨": "麦", "⻩": "黄", "⻭": "齿", "⻮": "齿", "⻬": "齐", "⻫": "齐", "⻅": "见",
            "⻓": "长", "⻔": "门", "⻜": "飞", "⻙": "韦", "⻚": "页", "⻝": "食", "⻤": "鬼",
            "⻧": "卤", "⻪": "黾", "⻯": "龙", "⻲": "龟", "⻳": "龟"}
DIM = re.compile(r"(\d{2,4})\s*[×xX]\s*(\d{2,3})\s*[×xX]\s*(\d{1,2}(?:\.\d)?)(?:\s*/\s*(\d{1,2}(?:\.\d)?))?")
CJK = re.compile(r"[\u4e00-\u9fff]")
FRAGMENT = {"前", "后", "宽", "孔", "通", "左", "右", "上", "下", "内", "外", "mm", "A", "B"}


def clean(s: str) -> str:
    return "".join(RADICALS.get(ch, ch) for ch in s).replace("（", "(").replace("）", ")")


def char_w(t: str, fs: float) -> float:
    w = 0.0
    for ch in t:
        w += fs * (1.02 if CJK.match(ch) else 0.56)
    return w


def build_lines(page):
    chunks = []

    def visitor(text, cm, tm, font_dict, font_size):
        t = text.strip()
        if t:
            fs = float(font_size or abs(tm[0]) or 10.0)
            chunks.append({"x": float(tm[4]), "y": float(tm[5]), "t": clean(t), "fs": fs})

    page.extract_text(visitor_text=visitor)
    rows = {}
    for c in chunks:
        key = round(c["y"] / 3.0)
        rows.setdefault(key, []).append(c)
    lines = []
    for key in sorted(rows, reverse=True):   # PDF 坐标 y 向上
        items = sorted(rows[key], key=lambda c: c["x"])
        segs, cur = [], None
        for it in items:
            if cur is None:
                cur = dict(it)
                continue
            gap = it["x"] - (cur["x"] + char_w(cur["t"], cur["fs"]))
            if gap < 0.9 * cur["fs"] and not DIM.search(it["t"]) and not DIM.search(cur["t"]):
                cur["t"] += it["t"]
            else:
                segs.append(cur)
                cur = dict(it)
        if cur:
            segs.append(cur)
        # 粘连的"名称+尺寸"再拆开
        split = []
        for s in segs:
            m = DIM.search(s["t"])
            if m and m.start() > 0:
                split.append(dict(s, t=s["t"][: m.start()].strip()))
                split.append(dict(s, t=m.group(0), x=s["x"] + char_w(s["t"][: m.start()], s["fs"])))
            else:
                split.append(s)
        lines.append(split)
    return lines


def is_name(t: str) -> bool:
    t = t.strip()
    if len(t) < 2 or t in FRAGMENT or DIM.fullmatch(t):
        return False
    if re.fullmatch(r"[\d\s./×xX:+\-()]+", t):
        return False
    return bool(CJK.search(t)) or bool(re.fullmatch(r"(?i)GY?s?[-\s]?\d{2,4}", t))


def parse_page(page, pno, fname, start_id):
    lines = build_lines(page)
    names, dims, nums = [], [], []
    for segs in lines:
        for s in segs:
            m = DIM.fullmatch(s["t"])
            if m:
                dims.append(dict(s, m=m))
            elif is_name(s["t"]):
                names.append(s)
            elif re.fullmatch(r"\d{1,3}(?:\.\d)?", s["t"]):
                nums.append(s)

    rows, used, used_dims = [], set(), set()
    # 配对优先级：同一行左侧 → 正上方同列；名称碎片按 x 顺序拼接
    cands = []
    for di, d in enumerate(dims):
        for ni, n in enumerate(names):
            dy = n["y"] - d["y"]   # PDF y 向上：名称在尺寸上方 → dy > 0
            dx = d["x"] - n["x"]
            if abs(dy) < 4 and 0 < dx < 220:
                cands.append((10 + dx, di, ni))
            elif 0 < dy <= 110 and abs(n["x"] - d["x"]) <= 75:
                cands.append((5 + abs(n["x"] - d["x"]) * 0.5 + dy * 0.2, di, ni))
    for _, di, ni in sorted(cands):
        if di in used_dims or ni in used:
            continue
        d, base = dims[di], names[ni]
        group = [n for m, n in enumerate(names)
                 if n["y"] == base["y"] and abs(n["y"] - base["y"]) < 4 and n["x"] >= base["x"]
                 and d["x"] - n["x"] >= 0]
        used_dims.add(di)
        for gi, n in enumerate(names):
            if n in group:
                used.add(gi)
        extras = sorted([(n2["x"] - d["x"], n2["t"]) for n2 in nums
                         if abs(n2["y"] - d["y"]) < 4 and 0 < (n2["x"] - d["x"]) < 300])[:3]
        m = d["m"]
        rows.append({
            "row_id": "R%04d" % (start_id + len(rows)),
            "file": fname, "page": pno,
            "name": " ".join(x["t"] for x in sorted(group, key=lambda z: z["x"])) or base["t"],
            "raw_dims": d["t"],
            "width_mm": float(m.group(1)), "length_mm": float(m.group(2)),
            "thickness_mm": float(m.group(3)),
            "thickness_alt_mm": float(m.group(4)) if m.group(4) else None,
            "extras": [e[1] for e in extras],
        })
    for ni, n in enumerate(names):
        if ni not in used and len(n["t"]) >= 3 and n["t"] not in FRAGMENT:
            rows.append({"row_id": "R%04d" % (start_id + len(rows)), "file": fname, "page": pno,
                         "name": n["t"], "raw_dims": None, "width_mm": None, "length_mm": None,
                         "thickness_mm": None, "thickness_alt_mm": None, "extras": []})
    return rows




def to_sku(row: dict) -> dict:
    name = (row.get("name") or "").strip()
    sid = "FIT-" + re.sub(r"[^\w\u4e00-\u9fff]+", "", name)[:20]
    pos = "前" if "前" in name else ("后" if "后" in name else "未知")
    is_abs = "ABS" in name.upper()
    part = name if re.fullmatch(r"(?i)GY?s?[-\s]?\d{2,4}", name) else None
    axle = []
    for brand, kw in (("汉德", "汉德"), ("沃胜", "沃胜"), ("BPW", "BPW"), ("SAF", "SAF")):
        if kw in name:
            axle.append({"brand": brand, "model": name, "brake_spec": row["raw_dims"], "verified": False})
    return {
        "sku_id": sid, "brand": "冠英", "category": "鼓式",
        "fit_name": name, "position": pos, "abs": is_abs, "part_no": part,
        # 产品册表头（中/英）：外弧 × 宽度 × 厚度 = outer arch / width / thickness
        "dims": {"arc_mm": row.get("arc_mm", row.get("width_mm")),
                 "width_mm": row.get("width_mm", row.get("length_mm")),
                 "thickness_mm": row.get("thickness_mm"),
                 "thickness_alt_mm": row.get("thickness_alt_mm"),
                 "raw_text": row["raw_dims"]},
        "material": "未知",
        "axle_fit": axle,
        "cross_refs": [],
        "extras": {"cols": row.get("extras") or []},
        "evidence": [{"report_id": row["file"], "page": row["page"],
                      "snippet": "%s %s" % (name, row["raw_dims"]), "kind": "产品册"}],
        "price": None, "stock": "未知",
        "provenance": {"source_file": row["file"], "source_page": row["page"],
                       "extracted_at": "2026-11-21", "extractor": "rule_coord",
                       "verified": False, "verified_by": None,
                       "notes": "坐标解析，需抽检；尺寸单位 mm，格式 外弧×宽度×厚度"},
        "_placeholder": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", default=str(ROOT / "资料包"))
    ap.add_argument("--out", default=str(ROOT / "data" / "structured" / "catalog_rows.json"))
    ap.add_argument("--merge", action="store_true", help="写出 skus.json（替换占位数据）")
    args = ap.parse_args(argv)

    from pypdf import PdfReader

    all_rows, seq = [], 0
    for pdf in sorted(Path(args.pdf_dir).glob("*.pdf")):
        if "企业介绍" in pdf.name:
            continue
        reader = PdfReader(str(pdf))
        got = []
        for i, page in enumerate(reader.pages):
            try:
                got += parse_page(page, i + 1, pdf.stem, seq + len(got))
            except Exception as e:  # noqa: BLE001
                print("[WARN] %s p%d: %s" % (pdf.name, i + 1, type(e).__name__))
        named = [g for g in got if g["raw_dims"]]
        print("%-22s 行 %-4d 其中有尺寸 %-4d" % (pdf.stem, len(got), len(named)))
        all_rows += got
        seq += len(got)

    print("\n合计 %d 行，有尺寸 %d 行" % (len(all_rows), sum(1 for r in all_rows if r["raw_dims"])))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("写出 %s" % out)

    if args.merge:
        skus, seen = [], set()
        for r in all_rows:
            if not r.get("raw_dims") or not r.get("name") or len(r["name"]) < 2:
                continue
            s = to_sku(r)
            key = (s["sku_id"], s["dims"]["raw_text"])
            if key in seen:
                continue
            seen.add(key)
            skus.append(s)
        tgt = ROOT / "data" / "structured" / "skus.json"
        old = json.loads(tgt.read_text(encoding="utf-8")) if tgt.exists() else []
        keep = [x for x in old if x.get("provenance", {}).get("extractor") == "manual"]
        tgt.write_text(json.dumps(keep + skus, ensure_ascii=False, indent=2), encoding="utf-8")
        print("合并 → skus.json：%d 条真实产品行（占位数据已清除）" % len(skus))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
