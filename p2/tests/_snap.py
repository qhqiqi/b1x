
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
p = r"Y:\hks\data\structured\skus.json"
d = json.load(open(p, encoding="utf-8"))
out = {}
for s in d:
    pr = s.get("provenance") or {}
    if pr.get("verified"):
        out[s["sku_id"]] = {"by": pr.get("verified_by"), "notes": pr.get("notes"), "date": "2026-11-21"}
json.dump(out, open(r"Y:\hks\data\verified.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已持久化 verified 记录 %d 条" % len(out))
