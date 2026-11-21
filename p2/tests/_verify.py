
import json, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
K = {"⻛":"风","⻰":"龙","⻁":"虎","⻢":"马","⻋":"车","⻘":"青","⻓":"长","⻔":"门","⻮":"齿","⻬":"齐","⻩":"黄"}
def norm(s):
    s = "".join(K.get(c,c) for c in (s or ""))
    s = unicodedata.normalize("NFKC", s)
    s = "".join(c for c in s if c >= " ")
    return s
def page_lines(f,p):
    parts = re.split(pat, open(r"Y:\hks\data\text_layout\%s.txt" % f, encoding="utf-8").read())
    return [l for l in parts[parts.index(str(p))+1].splitlines() if l.strip()]

skus = {s["sku_id"]: s for s in json.load(open(r"Y:\hks\data\structured\skus.json", encoding="utf-8"))}
ids = ["FIT-三一搅拌车前","FIT-三一搅拌车后","FIT-GY1054","FIT-HQ8555后",
       "FIT-东风多利卡后AABS","FIT-东风多利卡后B","FIT-新457桥后","FIT-JH6后A",
       "FIT-JH6后B","FIT-160宽","FIT-6700前","FIT-东风多利卡前"]
for sid in ids:
    s = skus.get(sid)
    if not s:
        print("!! 缺 %s" % sid); continue
    prov = s["provenance"]; dims = s["dims"]["raw_text"]; name = s["fit_name"]
    lines = page_lines(prov["source_file"], prov["source_page"])
    hits = [(i,l) for i,l in enumerate(lines) if dims in norm(l)]
    print("="*6, sid, "|", name, dims, "| p%s" % prov["source_page"], "| 命中 %d 行" % len(hits))
    for i,l in hits[:2]:
        print("   L%-3d %s" % (i, norm(l)[:110]))
    if not hits:
        # 找近似尺寸
        base = dims.split("×")[0]
        alt = [(i,l) for i,l in enumerate(lines) if base in norm(l)]
        for i,l in alt[:2]:
            print("   近似 L%-3d %s" % (i, norm(l)[:110]))
