
import json, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
K = {"⻛":"风","⻰":"龙","⻁":"虎","⻢":"马","⻋":"车","⻘":"青","⻓":"长","⻔":"门"}
def norm(s):
    s = "".join(K.get(c,c) for c in s)
    s = unicodedata.normalize("NFKC", s)
    return s.replace("（","(").replace("）",")").replace(" ","")
def page_lines(f,p):
    parts = re.split(pat, open(f,encoding="utf-8").read())
    return parts[parts.index(str(p))+1].splitlines()
skus = json.load(open(r"Y:\hks\data\structured\skus.json", encoding="utf-8"))
want = ["宇通校车后(ABS)","新江铃前A(ABS)","德龙K5000后","青岛3T"]
for s in skus:
    if s["fit_name"] in want:
        prov = s["provenance"]; dims = norm(s["dims"]["raw_text"])
        lines = page_lines(r"Y:\hks\data\text_layout\%s.txt" % prov["source_file"], prov["source_page"])
        hit = [l for l in lines if dims in norm(l)]
        print("%-16s %-18s p%s -> 命中行: %s" % (s["fit_name"], s["dims"]["raw_text"], prov["source_page"], (hit[0][:90] if hit else "无")))
