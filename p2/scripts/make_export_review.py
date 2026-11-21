# -*- coding: utf-8 -*-
"""出口对码抽检 PDF：把 p32–34 里指定的几行圈出来，人眼确认「外商号 ↔ 我方型号」没配错。"""
import json
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from parse_export import rows_of  # noqa: E402

ROOT = Path(r"Y:\hks")
OUT = ROOT / "data" / "reports"
CROP = OUT / "export_crops"
CROP.mkdir(parents=True, exist_ok=True)
BT = chr(96)

# 要核的 10 条（1-based，对应 export_refs.json 顺序）
CHOSEN = [1, 4, 10, 12, 19, 20, 22, 27, 31, 33]

refs = json.loads((ROOT / "data" / "structured" / "export_refs.json").read_text(encoding="utf-8"))
pdfs = {p.stem: p for p in (ROOT / "资料包").glob("*.pdf")}
doc = pymupdf.open()
md = ["# 出口对码抽检（10 条）", "",
      "> 看三件事：① 外商号（FMSI/OE/WVA）是不是这个 ② 我方型号是不是这个 ③ 两者是不是同一行。",
      "> 配套 PDF：" + BT + "data/reports/出口对码抽检_10条.pdf" + BT + "，一页一条，红框就是要核的那行。", "",
      "| # | 类型 | 外商号 | 我方型号 | 尺寸 | 页 | 判定 |", "|---|---|---|---|---|---|---|"]
zoom = 2.78  # 200 dpi，和 OCR 坐标一致
for n, idx in enumerate(CHOSEN, 1):
    rec = refs[idx - 1]
    page = int(rec["page"])
    src_doc = pymupdf.open(str(pdfs["kooying catalog"]))
    pix = src_doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    src_doc.close()
    items = json.loads((ROOT / "data" / "ocr" / ("kooying catalog_p%02d.json" % page)).read_text(encoding="utf-8"))
    want = {str(rec.get(k)).replace(" ", "") for k in ("fmsi", "shoe_code", "oe_ref", "wva") if rec.get(k)}
    box = None
    for row in rows_of(items):
        texts = {(i["text"] or "").replace(" ", "") for i in row}
        if texts & want:
            xs = [i["x"] for i in row]
            ys = [i["y"] for i in row]
            box = (max(0, min(xs) - 40), max(0, min(ys) - 40), min(img.width, max(xs) + 340), min(img.height, max(ys) + 50))
            break
    if not box:
        print("定位失败", n, rec["shoe_code"])
        box = (200, 800, 1500, 1000)
    crop = img.crop(box)
    d = ImageDraw.Draw(crop)
    d.rectangle([2, 2, crop.width - 3, crop.height - 3], outline=(220, 0, 0), width=5)
    tgt = CROP / ("%02d_%s_p%d.jpg" % (n, rec["shoe_code"], page))
    crop.save(tgt, "JPEG", quality=80)
    np_ = doc.new_page(width=595, height=420)
    np_.insert_text((36, 40), "%d. %s  外商号=%s  OE=%s  WVA=%s" % (
        n, rec["shoe_code"], rec.get("fmsi") or rec.get("size"), rec.get("oe_ref") or "—", rec.get("wva") or "—"), fontsize=12)
    np_.insert_text((36, 60), "选自 kooying 出口册 p%d ｜ OCR 置信 %.2f ｜ 判断：这一行是不是「外商号 → 这个型号」" % (
        page, rec["conf"]), fontsize=9)
    np_.insert_image(pymupdf.Rect(30, 76, 565, 400), filename=str(tgt), keep_proportion=True)
    md.append("| %d | %s | %s | %s | %s | p%d | ☐ ok / ☐ no |" % (
        n, rec["kind"], rec.get("fmsi") or rec.get("oe_ref") or rec.get("wva") or "—",
        rec["shoe_code"], rec.get("size") or rec.get("width") or "—", page))

out = OUT / "出口对码抽检_10条.pdf"
doc.save(str(out))
doc.close()
(OUT / "export_review_10.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("PDF ->", out, "(%.2f MB)" % (out.stat().st_size / 1024 / 1024))
for n, idx in enumerate(CHOSEN, 1):
    r = refs[idx - 1]
    print("  %2d %-9s %-10s %s p%s" % (n, r["shoe_code"], r.get("fmsi") or r.get("size"), r.get("oe_ref") or r.get("wva") or "", r["page"]))
