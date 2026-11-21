# -*- coding: utf-8 -*-
"""交付前自检：skus.json 是否符合 v1.1 契约。

用法：python p2/scripts/validate_skus.py    退出码 0 = 可交给 P3
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ["sku_id", "brand", "category", "dims", "fit_name", "provenance"]
CATS = {"鼓式", "盘式", "风电"}
MATS = {"半金属", "陶瓷", "NAO", "石墨", "其他", "未知"}


def main() -> int:
    path = ROOT / "data" / "structured" / "skus.json"
    recs = json.loads(path.read_text(encoding="utf-8"))
    errs, warns, ids = [], [], [r.get("sku_id") for r in recs]
    for r in recs:
        sid = r.get("sku_id", "?")
        for k in REQUIRED:
            if k not in r:
                errs.append("%s 缺字段 %s" % (sid, k))
        if r.get("category") not in CATS:
            errs.append("%s category 非法: %s" % (sid, r.get("category")))
        if r.get("material") not in MATS:
            warns.append("%s material 非法: %s" % (sid, r.get("material")))
        d = r.get("dims") or {}
        nums = [k for k in ("width_mm", "length_mm", "thickness_mm") if d.get(k) is not None]
        if len(nums) < 2:
            errs.append("%s 尺寸不足两项（宽/长/厚），无法硬匹配" % sid)
        if not d.get("raw_text"):
            errs.append("%s 缺 dims.raw_text（展示与溯源都要）" % sid)
        for e in r.get("evidence") or []:
            if not e.get("report_id") or not isinstance(e.get("page"), int):
                errs.append("%s evidence 缺 report_id/page" % sid)
        if not (r.get("provenance") or {}).get("source_file"):
            errs.append("%s provenance.source_file 为空" % sid)
    for i in {x for x in ids if ids.count(x) > 1}:
        warns.append("重复 sku_id: %s" % i)
    ph = [r for r in recs if r.get("_placeholder")]
    ver = [r for r in recs if (r.get("provenance") or {}).get("verified")]

    print("记录数 %d | 唯一 sku_id %d | 占位 %d | 已人工核对 %d" % (len(recs), len(set(ids)), len(ph), len(ver)))
    for w in warns[:15]:
        print("  [警告] " + w)
    for e in errs[:15]:
        print("  [错误] " + e)
    if ph:
        print("\n[注意] 仍有 %d 条占位数据，提交前必须清零。" % len(ph))
    if not ver:
        print("[提醒] 目前 0 条人工核对：抽检 10% 后把 provenance.verified 改 true，答辩才敢说「可溯源」。")
    print("\n结果：%s" % ("通过" if not errs else "不通过（%d 个错误）" % len(errs)))
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())
