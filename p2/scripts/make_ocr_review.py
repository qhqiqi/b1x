# -*- coding: utf-8 -*-
"""把 OCR 抽检的 12 条做成一份带红框标注的 PDF，人眼一页一页核对。"""
import json, random, re, sys
from collections import defaultdict
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
BT = chr(96)
ROOT = Path(r"Y:\hks")
OUT = ROOT / "data" / "reports"
CROP = OUT / "ocr_crops"
CROP.mkdir(parents=True, exist_ok=True)

skus = json.loads((ROOT / "data" / "structured" / "skus.json").read_text(encoding="utf-8"))
ocr = [s for s in skus if (s.get("provenance") or {}).get("extractor") == "rule_ocr"]
pages = defaultdict(list)
for s in ocr:
    pages[(s["provenance"]["source_file"], s["provenance"]["source_page"])].append(s)

import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument("--ids", default="", help="逗号分隔的 sku_id，指定就只出这几条")
_ap.add_argument("--out", default="OCR抽检_12条.pdf")
_args = _ap.parse_args()

if _args.ids:
    want = [x.strip() for x in _args.ids.split(",") if x.strip()]
    by_id = {s["sku_id"]: s for s in ocr}
    picked = [by_id[w] for w in want if w in by_id]
    missing = [w for w in want if w not in by_id]
    if missing:
        print("跳过（不是 OCR 行）:", missing)
else:
    random.seed(7)
    picked = []
    for k in sorted(pages):
        picked.append(random.choice(pages[k]))
        if len(pages[k]) > 1:
            picked.append(random.choice(pages[k]))
    picked = picked[:12]
picked.sort(key=lambda s: (s["provenance"]["source_file"], s["provenance"]["source_page"]))

pdfs = {p.stem: p for p in (ROOT / "资料包").glob("*.pdf")}
doc = pymupdf.open()
rows_md = ["# OCR 图页抽检（12 条，6 个图页）", "",
           "> 全部来自**冠隆产品册 p12–p17**（这 6 页没有文本层，只能 OCR）。",
           "> 配套 PDF：" + BT + "data/reports/OCR抽检_12条.pdf" + BT + "，每页一个红框，框里就是要核的那一行。", "",
           "| # | sku_id | 适配名 | OCR 尺寸 | 出处 | 置信度 | 判定 |", "|---|---|---|---|---|---|---|"]
for i, s in enumerate(picked, 1):
    pr = s["provenance"]
    src = pdfs.get(pr["source_file"])
    page = int(pr["source_page"])
    src_doc = pymupdf.open(str(src))
    src_page = src_doc[page - 1]
    # 用 OCR 坐标框出该行
    box = None
    oj = ROOT / "data" / "ocr" / ("%s_p%02d.json" % (pr["source_file"], page))
    dims_key = s["dims"]["raw_text"].replace("×", "").replace(".", "")
    if oj.exists():
        items = json.loads(oj.read_text(encoding="utf-8"))
        for it in items:
            t = (it.get("text") or "").replace("×", "").replace(".", "")
            if dims_key[:5] and dims_key[:5] in t:
                x, y = float(it.get("x", 0)), float(it.get("y", 0))
                box = pymupdf.Rect(max(0, x - 120), max(0, y - 26), x + 260, y + 46)
                break
    # 渲染整页
    zoom = 1.8
    pix = src_page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    d = ImageDraw.Draw(img)
    if box:
        d.rectangle([box.x0 * zoom, box.y0 * zoom, box.x1 * zoom, box.y1 * zoom],
                    outline=(220, 0, 0), width=6)
    fn = "%02d_%s_p%d.png" % (i, re.sub(r"[^\w\u4e00-\u9fff-]+", "_", s["sku_id"]), page)
    img.save(CROP / fn)
    jpg = CROP / (fn[:-4] + ".jpg")
    img.save(jpg, "JPEG", quality=72)   # PDF 里放 JPG，否则 12 页能到 100MB
    # 塞进 PDF（一页一张，等比缩到 A4 宽）
    newpage = doc.new_page(width=595, height=842)
    newpage.insert_text((40, 40), "%d. %s  %s  (%s p%d)" % (
        i, s["fit_name"], s["dims"]["raw_text"], pr["source_file"], page), fontsize=13)
    newpage.insert_text((40, 60), "核对：名称是否一致 / 三个数字是否认错（1-7 5-6 0-O 8-3）", fontsize=9)
    rect = pymupdf.Rect(30, 80, 565, 810)
    newpage.insert_image(rect, filename=str(jpg), keep_proportion=True)
    src_doc.close()
    rows_md.append("| %d | %s | %s | %s | %s p%d | %.2f | ☐ ok / ☐ no |" % (
        i, s["sku_id"], s["fit_name"], s["dims"]["raw_text"],
        pr["source_file"], page, (s.get("extras") or {}).get("ocr_conf") or 0))

pdf_out = OUT / _args.out
doc.save(str(pdf_out))
doc.close()
(OUT / "ocr_review_12.md").write_text("\n".join(rows_md) + "\n", encoding="utf-8")
print("PDF ->", pdf_out)
print("PNG ->", CROP)
for i, s in enumerate(picked, 1):
    print("  %2d %-16s %-18s p%s" % (i, s["fit_name"], s["dims"]["raw_text"], s["provenance"]["source_page"]))
