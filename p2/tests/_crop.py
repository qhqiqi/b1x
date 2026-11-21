# -*- coding: utf-8 -*-
"""把 OCR 抽检清单里的行，从 PDF 原页裁出对应区域，存成 PNG 供人眼核对。"""
import json, re, sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"Y:\hks")
OUT = ROOT / "data" / "reports" / "ocr_crops"
OUT.mkdir(parents=True, exist_ok=True)

md = (ROOT / "data" / "reports" / "ocr_review_12.md").read_text(encoding="utf-8")
ids = re.findall(r"\|\s*\d+\s*\|\s*(\S+)\s*\|", md)
skus = {s["sku_id"]: s for s in json.loads((ROOT / "data" / "structured" / "skus.json").read_text(encoding="utf-8"))}
pdfs = {p.stem: p for p in (ROOT / "资料包").glob("*.pdf")}
print("PDF:", list(pdfs))
made = []
for sid in ids:
    s = skus.get(sid)
    if not s:
        print("缺", sid); continue
    pr = s["provenance"]
    stem, page = pr["source_file"], int(pr["source_page"])
    pdf = pdfs.get(stem)
    if not pdf:
        print("找不到 PDF", stem); continue
    doc = fitz.open(str(pdf))
    pg = doc[page - 1]
    zoom = 200 / 72.0
    pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    full = OUT / ("_full_%s_p%d.png" % (stem.replace(" ", "_"), page))
    pix.save(str(full))
    im = Image.open(full)
    # 用 OCR 坐标定位该行的尺寸串/名称
    ocrj = ROOT / "data" / "ocr" / ("%s_p%02d.json" % (stem, page))
    cx = cy = None
    if ocrj.exists():
        items = json.loads(ocrj.read_text(encoding="utf-8"))
        want = s["dims"]["raw_text"].replace("×", "").replace(".", "")
        for it in items:
            t = (it.get("text") or "").replace("×", "").replace(".", "")
            if want[:6] and want[:6] in t:
                xs = [it.get("x", 0)]; ys = [it.get("y", 0)]
                cx, cy = sum(xs), sum(ys)
                break
    if cx is None:
        cx, cy = im.width / 2, im.height / 2
    box = (max(0, int(cx - 640)), max(0, int(cy - 300)), min(im.width, int(cx + 760)), min(im.height, int(cy + 380)))
    crop = im.crop(box)
    safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", sid)
    out = OUT / ("%s_p%d.png" % (safe, page))
    crop.save(out)
    made.append((sid, out.name, crop.size))
    doc.close()
for m in made:
    print(m)
print("共裁 %d 张 → %s" % (len(made), OUT))
