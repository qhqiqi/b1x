
import sys
sys.path.insert(0, r"Y:\hks\p2")
sys.stdout.reconfigure(encoding="utf-8")
from engine.match import match_query
qs = ["客户说这车是欧曼 400，要前片",
      "修理工量了一下 147×100×14.5 让我配",
      "汉德 35 吨桥，前面那副",
      "沃胜桥 11.5 吨的，A 款",
      "有没有乘龙 H5 前轮的片子",
      "客户发来旧片，说大概是 151×80×13"]
for t in qs:
    r = match_query(t)
    print("Q:", t, "|", r["mode"], r["elapsed_ms"], "ms")
    for c in r["candidates"][:3]:
        print("    %-24s %s %s" % (c["sku_id"], c["confidence"], c["dims"]["raw_text"]))
    if r["followups"]:
        print("    追问:", r["followups"][:2])
