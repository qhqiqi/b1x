
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d)+"+B+"]"+B+"]".replace("(d)","d")
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
parts = re.split(pat, open(r"Y:\hks\data\text_layout\冠隆产品册.txt", encoding="utf-8").read())
body = parts[parts.index("17")+1]
lines = body.splitlines()
for i, l in enumerate(lines[:12]):
    print("L%-2d %s" % (i, l))
print("----- 含 152×100×12.5 与 JH6 的行")
for i, l in enumerate(lines):
    if "152×100×12.5" in l or "JH6后" in l or "Q54" in l:
        print("L%-2d %s" % (i, l[:150]))
