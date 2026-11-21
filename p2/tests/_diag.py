
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
def page_lines(f, p):
    parts = re.split(pat, open(f, encoding="utf-8").read())
    i = parts.index(str(p))
    return parts[i+1].splitlines()
cases = [("kooying_catalog", 27, "宇通校车后", "150×150×9.5/13.5"),
         ("kooying_catalog", 29, "新江铃前A", "149×100×13.5/15"),
         ("冠隆产品册", 19, "德龙K5000后", "154×100×10.5/13.5"),
         ("kooying_catalog", 28, "德龙LM180", "201×180×13/16.5"),
         ("冠隆产品册", 18, "青岛3T", "208×140×16")]
for f, p, name, dims in cases:
    lines = page_lines(r"Y:\hks\data\text_layout\%s.txt" % f, p)
    print("="*10, f, p, name, dims)
    for i, l in enumerate(lines):
        if name in l or dims in l:
            print("  L%-3d %s" % (i, l[:120]))
