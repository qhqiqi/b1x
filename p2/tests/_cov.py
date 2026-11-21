
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"Y:\hks\p2")
from engine.store import load_skus, load_axles
from engine.match import match_query
skus, axles = load_skus(), load_axles()
idx = {s["sku_id"]: s for s in skus}
DEMO = ["147×100×14.5", "汉德 35 吨桥，前面那副", "解放虎威前", "沃胜桥 11.5 吨的，A 款",
        "客户发来旧片，说大概是 151×80×13", "客户说这车是欧曼 400，要前片"]
spoken = [json.loads(l)["input"] for l in open(r"Y:\hks\data\eval\cases_spoken.jsonl", encoding="utf-8") if l.strip()]
tot = ver = 0
miss = []
for q in DEMO + spoken:
    r = match_query(q, skus, axles, top=3)
    for c in r["candidates"] or []:
        tot += 1
        s = idx.get(c["sku_id"]) or {}
        ok = bool((s.get("provenance") or {}).get("verified"))
        ver += ok
        if not ok:
            miss.append((c["sku_id"], (s.get("provenance") or {}).get("extractor")))
print("Top3 命中行：%d 个，已核对 %d（%.0f%%）" % (tot, ver, 100.0*ver/max(tot,1)))
for m in miss:
    print("   未核:", m)
