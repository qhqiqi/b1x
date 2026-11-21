
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
parts = re.split(pat, open(r"Y:\hks\data\text_layout\冠隆产品册.txt", encoding="utf-8").read())
for p, keys in (("19", ["少林客车", "170×130×13", "151×80×13.5"]),
                ("18", ["杰狮C6前A", "191×160×14/17", "Hq8555后", "151×160×14"]),
                ("17", ["东风天龙前B", "208×150×10/15"])):
    body = parts[parts.index(p)+1]
    lines = body.splitlines()
    print("="*12, "p", p)
    for i, l in enumerate(lines):
        if any(k in l for k in keys):
            print("L%-3d %s" % (i, l[:160]))
