# -*- coding: utf-8 -*-
"""从已有 SKU 反推车桥词典（只收"…桥…"这类适配名，车型名不算车桥）。

产出 data/structured/axles.json：
  {axle_id, brand, model, aliases, brake_spec, known_sku_ids, source, verified}

用法：python p2/scripts/build_axles.py
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    skus = json.loads((ROOT / "data" / "structured" / "skus.json").read_text(encoding="utf-8"))
    axles = {}
    for s in skus:
        name = s.get("fit_name") or ""
        m = re.match(r"^(.+?)桥(.+)$", name)
        if not m:
            continue
        brand = m.group(1).strip()
        rest = re.sub(r"(前|后)(\(ABS\)|ABS)?$", "", m.group(2)).strip()
        model = rest or "未知"
        key = "%s-%s" % (brand, model)
        a = axles.setdefault(key, {
            "axle_id": key, "brand": brand, "model": model, "aliases": [],
            "brake_type": "鼓式",
            "brake_spec": {"drum_dia_mm": None, "pad_width_mm": None,
                           "thickness_mm": None, "bonding": "未知"},
            "known_sku_ids": [], "source": "由产品册适配名反推（%s 等）" % name,
            "verified": False,
        })
        if s["sku_id"] not in a["known_sku_ids"]:
            a["known_sku_ids"].append(s["sku_id"])
        d = s["dims"]
        if a["brake_spec"]["pad_width_mm"] is None and d.get("width_mm"):
            a["brake_spec"] = {
                "drum_dia_mm": None,
                "pad_width_mm": d.get("width_mm"),
                "thickness_mm": d.get("thickness_mm"),
                "bonding": "未知",
                "note": "取自 %s 的尺寸，未核实" % s["sku_id"],
            }
        for alias in {brand + model, brand + model.replace("T", "吨"), brand + "桥" + model}:
            if alias and alias not in a["aliases"]:
                a["aliases"].append(alias)

    out = sorted(axles.values(), key=lambda x: x["axle_id"])
    dst = ROOT / "data" / "structured" / "axles.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for a in out:
        print("%-18s 关联 %d 条 SKU  别名 %s" % (a["axle_id"], len(a["known_sku_ids"]), a["aliases"][:3]))
    print("\n共 %d 个车桥 → %s" % (len(out), dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
