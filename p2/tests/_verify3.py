
import re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return "".join(c for c in s if c >= " ").rstrip()
parts = re.split(pat, open(r"Y:\hks\data\text_layout\冠隆产品册.txt", encoding="utf-8").read())
lines = [l for l in parts[parts.index("18")+1].splitlines() if l.strip()]
for i, l in enumerate(lines[13:20], 13):
    n = norm(l)
    print("L%-3d len=%d |%s|" % (i, len(n), n[:60] + " ... " + n[150:230]))
