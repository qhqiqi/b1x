
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import fitz
OUT = r"Y:\hks\data\images"
os.makedirs(OUT, exist_ok=True)
jobs = [
    (r"Y:\hks\资料包\冠隆产品册.pdf", [12, 15, 18], "gl"),
    (r"Y:\hks\资料包\kooying catalog.pdf", [3, 6, 21], "ky"),
    (r"Y:\hks\资料包\2026年浙江冠英企业介绍.pdf", [25], "intro"),
]
for path, pages, tag in jobs:
    doc = fitz.open(path)
    for p in pages:
        page = doc[p-1]
        txt = page.get_text().strip()
        pix = page.get_pixmap(dpi=110)
        fn = os.path.join(OUT, "%s_p%02d.png" % (tag, p))
        pix.save(fn)
        print("%s p%-3d fitz_text=%d pypdf_seen=%s  -> %s" % (tag, p, len(txt), "?", fn))
    doc.close()
