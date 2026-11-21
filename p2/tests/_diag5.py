
import json, sys, re
sys.stdout.reconfigure(encoding="utf-8")
rows = json.load(open(r"Y:\hks\data\structured\catalog_rows.json", encoding="utf-8"))
for r in rows:
    if r["file"] == "冠隆产品册" and r["page"] == 19:
        print("%-16s %-18s %s" % (r["name"], r["raw_dims"], r["extras"]))
print("----- L42 repr")
B = chr(92)
pat = B+"["+B+"[PAGE ("+B+"d+)"+B+"]"+B+"]"
parts = re.split(pat, open(r"Y:\hks\data\text_layout\冠隆产品册.txt", encoding="utf-8").read())
lines = parts[parts.index("19")+1].splitlines()
for i in (41, 42):
    print(i, repr(lines[i]))
