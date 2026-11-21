# -*- coding: utf-8 -*-
"""对"纯图片页"做 OCR（RapidOCR + PyMuPDF 渲染），把文字连同坐标吐出来。

用途：产品册里 33 页是 Illustrator 转曲页（无文本层），只有 OCR 能取。
用法：
    python p2/scripts/ocr_pages.py --file "冠隆产品册.pdf" --pages 12,15,20
    python p2/scripts/ocr_pages.py --auto            # 自动挑"无文本且有大图"的页
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
OUTDIR = ROOT / "data" / "ocr"


def ocr_page(page, dpi=200):
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    pix = page.get_pixmap(dpi=dpi)
    img = pix.tobytes("png")
    result, _ = engine(img)
    items = []
    for box, txt, score in (result or []):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append({"text": txt, "conf": round(float(score), 3),
                      "x": round(min(xs)), "y": round(min(ys))})
    return items


def main(argv=None) -> int:
    import pymupdf

    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="冠隆产品册.pdf")
    ap.add_argument("--pages", default="")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args(argv)

    pdf = next((p for p in (ROOT / "资料包").glob("*.pdf") if p.name == args.file), None)
    if pdf is None:
        print("找不到 %s" % args.file)
        return 2
    pages = [int(x) for x in args.pages.split(",") if x.strip()]
    doc = pymupdf.open(str(pdf))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for pno in pages:
        page = doc[pno - 1]
        items = ocr_page(page, args.dpi)
        items.sort(key=lambda d: (d["y"], d["x"]))
        out = OUTDIR / ("%s_p%02d.json" % (pdf.stem, pno))
        out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print("=== %s p%d  识别 %d 段" % (pdf.stem, pno, len(items)))
        for it in items[:25]:
            print("   y=%-5d x=%-4d %s" % (it["y"], it["x"], it["text"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
