
import sys, json
sys.stdout.reconfigure(encoding="utf-8")
import pymupdf
doc = pymupdf.open(r"Y:\hks\资料包\2026年浙江冠英企业介绍.pdf")
for pno in (24, 25):
    page = doc[pno-1]
    tabs = page.find_tables()
    print("page", pno, "tables:", len(tabs.tables))
    for ti, t in enumerate(tabs.tables):
        rows = t.extract()
        print("  table %d  rows=%d cols=%d" % (ti, len(rows), len(rows[0]) if rows else 0))
        for r in rows[:4]:
            print("    ", r)
        print("    ...")
