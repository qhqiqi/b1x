
import sys, re
sys.path.insert(0, r"Y:\hks\p2\scripts")
sys.stdout.reconfigure(encoding="utf-8")
from parse_layout import cells, is_name
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
parts = re.split(pat, open(r"Y:\hks\data\text_layout\冠隆产品册.txt", encoding="utf-8").read())
lines = [l for l in parts[parts.index("17")+1].splitlines() if l.strip()]
for i in (7, 8, 11, 12):
    print("L%d" % i)
    for (s, e, t) in cells(lines[i]):
        print("    [%3d-%3d] %-28r name=%s" % (s, e, t, is_name(t)))
