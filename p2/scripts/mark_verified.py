# -*- coding: utf-8 -*-
"""把人工抽检的结论写回主数据：只动 provenance，不碰尺寸/页码本身。

用法（仓库根目录）：
    python p2/scripts/mark_verified.py --list                 # 看还剩多少条没核
    python p2/scripts/mark_verified.py --sku FIT-解放虎威前A --by P2
    python p2/scripts/mark_verified.py --sku A --sku B --by P2 --notes "与 p19 原文一致"
    python p2/scripts/mark_verified.py --sku FIT-xxx --by P2 --reject --notes "尺寸应为 147×100×14.5/16.5"

规则：--reject 表示核对不符，不会置 true，只记录备注，提示回去修解析。
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
SKUS = ROOT / "data" / "structured" / "skus.json"


def load():
    return json.loads(SKUS.read_text(encoding="utf-8"))


def save(recs):
    SKUS.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sku", action="append", default=[], help="sku_id，可重复")
    ap.add_argument("--by", default="P2", help="核对人")
    ap.add_argument("--notes", default="", help="备注")
    ap.add_argument("--reject", action="store_true", help="标记核对不符（不会置 verified=true）")
    ap.add_argument("--list", action="store_true", help="列出未核对条数")
    args = ap.parse_args()

    recs = load()

    if args.list:
        done = [r for r in recs if (r.get("provenance") or {}).get("verified")]
        todo = len(recs) - len(done)
        print("总 %d 条 | 已核对 %d 条 | 未核对 %d 条" % (len(recs), len(done), todo))
        for r in done:
            p = r["provenance"]
            print("  ✔ %s  核对人 %s  %s" % (r["sku_id"], p.get("verified_by"), p.get("notes") or ""))
        return

    if not args.sku:
        ap.error("至少给一个 --sku，或者用 --list")

    index = {r["sku_id"]: r for r in recs}
    hit = 0
    for sid in args.sku:
        r = index.get(sid)
        if r is None:
            print("!! 跳过：%s 不在主数据里" % sid)
            continue
        p = r.setdefault("provenance", {})
        if args.reject:
            p["verified"] = False
            p["verified_by"] = None
            p["notes"] = (args.notes or "核对不符") .strip()
            print("✘ %s 记下不符：%s" % (sid, p["notes"]))
        else:
            p["verified"] = True
            p["verified_by"] = args.by
            p["verified_on"] = date.today().isoformat()
            if args.notes:
                p["notes"] = args.notes.strip()
            print("✔ %s 标记为已核对（%s）" % (sid, args.by))
        hit += 1

    if hit:
        save(recs)
        done = [r for r in recs if (r.get("provenance") or {}).get("verified")]
        print("已写回 %s：已核对 %d / %d 条（%.0f%%）" % (SKUS.name, len(done), len(recs), 100.0 * len(done) / len(recs)))
        print("提醒：改完跑一次 python p2/scripts/validate_skus.py")


if __name__ == "__main__":
    main()
