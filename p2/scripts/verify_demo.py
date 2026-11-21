# -*- coding: utf-8 -*-
"""给 Demo/口语 Top1 命中的行做文本层逐字核对，通过的写 verified。
用法：python p2/scripts/verify_demo.py [--apply]"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"Y:\hks")
sys.path.insert(0, str(ROOT / "p2"))
sys.path.insert(0, str(ROOT / "p2" / "scripts"))

from engine.store import load_skus, load_axles
from engine.match import match_query
from spotcheck import machine_check, page_lines, norm

APPLY = "--apply" in sys.argv
DEMO = ["147×100×14.5", "汉德 35 吨桥，前面那副", "解放虎威前", "沃胜桥 11.5 吨的，A 款",
        "客户发来旧片，说大概是 151×80×13", "客户说这车是欧曼 400，要前片"]
spoken = [json.loads(l)["input"] for l in (ROOT / "data" / "eval" / "cases_spoken.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

skus, axles = load_skus(), load_axles()
idx = {s["sku_id"]: s for s in skus}
todo = []
for q in DEMO + spoken:
    r = match_query(q, skus, axles, top=3)
    for c in (r["candidates"] or [])[:1]:
        s = idx.get(c["sku_id"])
        if s and not (s.get("provenance") or {}).get("verified"):
            todo.append((q, s))
seen, rows = set(), []
for q, s in todo:
    if s["sku_id"] in seen:
        continue
    seen.add(s["sku_id"])
    pr = s["provenance"]
    v = machine_check(s)
    evidence = ""
    if v.startswith("机器一致"):
        for l in page_lines(pr["source_file"], pr["source_page"]):
            if s["dims"]["raw_text"] in norm(l):
                evidence = norm(l).strip()[:70]
                break
    rows.append((s["sku_id"], s["fit_name"], s["dims"]["raw_text"], pr["source_file"], pr["source_page"], v, evidence))

ok = [r for r in rows if r[5].startswith("机器一致") and r[3] != "" and (idx[r[0]]["provenance"].get("extractor") != "rule_ocr")]
ocr_left = [r for r in rows if idx[r[0]]["provenance"].get("extractor") == "rule_ocr"]
print("Demo/口语 Top1 未核对 %d 条：文本层可自动核 %d，OCR 需人眼 %d" % (len(rows), len(ok), len(ocr_left)))
for r in rows:
    print("  %-22s %-18s %-8s %s" % (r[0], r[2], r[5], r[6][:40]))

md = ["# Demo / 口语 Top1 命中行的核对", "",
      "- 待核 %d 条：文本层 %d（逐字比对）、OCR 图页 %d（需人眼）" % (len(rows), len(ok), len(ocr_left)), "",
      "| sku_id | 适配名 | 尺寸 | 出处 | 机器预判 | 原文行 |", "|---|---|---|---|---|---|"]
for r in rows:
    md.append("| %s | %s | %s | %s p%s | %s | %s |" % r)
(ROOT / "data" / "reports" / "verify_demo.md").write_text("\n".join(md) + "\n", encoding="utf-8")

if APPLY and ok:
    vp = ROOT / "data" / "verified.json"
    vd = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}
    for r in ok:
        vd[r[0]] = {"by": "P2", "notes": "文本层逐字比对一致(2026-11-21，Demo/口语 Top1)"}
        s = idx[r[0]]
        s["provenance"]["verified"] = True
        s["provenance"]["verified_by"] = "P2"
        s["provenance"]["notes"] = vd[r[0]]["notes"]
    (ROOT / "data" / "structured" / "skus.json").write_text(json.dumps(skus, ensure_ascii=False, indent=1), encoding="utf-8")
    vp.write_text(json.dumps(vd, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写入 verified：%d 条" % len(ok))
