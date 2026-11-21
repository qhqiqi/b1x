
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"Y:\hks\p2")
from engine.store import load_skus, load_axles
from engine.match import match_query
skus, axles = load_skus(), load_axles()
idx = {s["sku_id"]: s for s in skus}
def vd(sid):
    s = idx.get(sid) or {}
    return bool((s.get("provenance") or {}).get("verified"))
spoken = [json.loads(l) for l in open(r"Y:\hks\data\eval\cases_spoken.jsonl", encoding="utf-8")]
print("%-34s %-22s %s" % ("问法", "Top1", "已核对"))
for c in spoken:
    r = match_query(c["input"], skus, axles, top=3)
    top = (r["candidates"] or [{}])[0]
    print("%-34s %-22s %s" % (c["input"][:32], top.get("sku_id", "—"), "✅" if vd(top.get("sku_id")) else "—"))
