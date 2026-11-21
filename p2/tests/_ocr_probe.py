
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pymupdf
print("pymupdf", pymupdf.__version__)
doc = pymupdf.open(r"Y:\hks\资料包\冠隆产品册.pdf")
p = doc[14]
info = p.get_image_info()
print("gl_p15 images:", len(info), [ (round(i["bbox"][2]-i["bbox"][0]), round(i["bbox"][3]-i["bbox"][1])) for i in info][:6])
print("gl_p15 drawings:", len(p.get_drawings()))
print("gl_p15 text blocks:", len(p.get_text("blocks")))
for m in ("pymupdf_layout", "pymupdf4llm", "rapidocr_onnxruntime", "ocr"):
    try:
        __import__(m); print("module ok:", m)
    except Exception as e:
        print("module miss:", m, type(e).__name__)
try:
    tp = p.get_textpage_ocr(dpi=150, full=True)
    print("OCR:", p.get_text(textpage=tp)[:300])
except Exception as e:
    print("OCR failed:", type(e).__name__, str(e)[:200])
