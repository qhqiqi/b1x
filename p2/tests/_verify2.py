
import re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
K = {"⻛":"风","⻰":"龙","⻁":"虎","⻢":"马","⻋":"车","⻘":"青","⻓":"长","⻔":"门"}
def norm(s):
    s = "".join(K.get(c,c) for c in (s or ""))
    s = unicodedata.normalize("NFKC", s)
    return "".join(c for c in s if c >= " ").rstrip()
def pg(f,p):
    parts = re.split(pat, open(r"Y:\hks\data\text_layout\%s.txt" % f, encoding="utf-8").read())
    return [l for l in parts[parts.index(str(p))+1].splitlines() if l.strip()]
for f, p, lo, hi in [("kooying_catalog",28,0,10),("kooying_catalog",29,0,8),
                     ("冠隆产品册",18,10,22),("冠隆产品册",18,0,8),("kooying_catalog",27,8,14)]:
    print("#"*8, f, "p", p)
    for i, l in enumerate(pg(f,p)[lo:hi], lo):
        print("L%-3d|%s|" % (i, norm(l)))
