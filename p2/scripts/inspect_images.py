# -*- coding: utf-8 -*-
"""体检：哪些页是"纯图片页"，那些图片到底是什么。

不 OCR，只看结构：每页的图片数量、像素面积、占版面比例、是否有矢量绘图。
用来判断"值得不值得 OCR"。

用法：python p2/scripts/inspect_images.py
产出：data/reports/image_pages.md
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]


def main():
    from pypdf import PdfReader

    rows = []
    for pdf in sorted((ROOT / "资料包").glob("*.pdf")):
        reader = PdfReader(str(pdf))
        for i, page in enumerate(reader.pages, start=1):
            try:
                imgs = page.images
            except Exception:
                imgs = []
            area = 0
            for im in imgs:
                try:
                    area += im.image.size[0] * im.image.size[1]
                except Exception:
                    pass
            mb = page.mediabox
            page_pts = float(mb.width) * float(mb.height)
            # 版面面积按 72dpi 折算成像素面积
            page_px = (float(mb.width) / 72 * 150) * (float(mb.height) / 72 * 150)
            text = (page.extract_text() or "").strip()
            rows.append({
                "file": pdf.stem, "page": i,
                "chars": len(text),
                "images": len(imgs),
                "img_px": area,
                "cover": round(area / page_px, 2) if page_px else 0,
                "blank": len(text) < 20,
            })

    out = ROOT / "data" / "reports" / "image_pages.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    blank = [r for r in rows if r["blank"]]
    lines = ["# 纯图片页体检", "",
             "共 %d 页，其中无文本页 %d 页。" % (len(rows), len(blank)), "",
             "> cover = 图片像素面积 / 版面像素面积（150dpi 估算）。≈1 说明整页是一张图（照片/扫描）；明显小于 1 说明是排版图 + 矢量文字/图形。",
             "",
             "| 文件 | 页 | 字符数 | 图片数 | 覆盖度 | 形态判断 |",
             "|---|---|---|---|---|---|"]
    def verdict(r):
        if r["images"] == 0:
            return "无图片（矢量排版）"
        if r["cover"] >= 0.85:
            return "整页一张大图（照片/扫描）"
        if r["cover"] >= 0.3:
            return "多图拼版（产品照阵列）"
        return "小图点缀"

    for r in blank:
        lines.append("| %s | %d | %d | %d | %.2f | %s |" % (
            r["file"], r["page"], r["chars"], r["images"], r["cover"], verdict(r)))
    out.write_text("\n".join(lines), encoding="utf-8")
    for r in blank:
        print("%-22s p%-3d chars=%-5d imgs=%-2d cover=%.2f  %s" % (
            r["file"], r["page"], r["chars"], r["images"], r["cover"], verdict(r)))
    print("\n写出 %s" % out)


if __name__ == "__main__":
    main()
