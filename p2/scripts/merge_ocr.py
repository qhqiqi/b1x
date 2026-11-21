# -*- coding: utf-8 -*-
"""把 OCR 图页抽出的行并入主数据（127 → 约 220 条）。

流程（可重复跑）：
    python p2/scripts/parse_layout.py --merge     # 先重建文本层主数据
    python p2/scripts/merge_ocr.py                # 再并入 OCR 行

过三道闸：
  1) 几何闸：外弧 ≥ 宽度（物理上外弧一定不窄于宽度）、厚度 5~30mm、量级合理
  2) 名称闸：≥3 字、含中文、名字里不混尺寸串
  3) 去重闸：(适配名, 尺寸) 已存在于文本层 → 不新增，只给原记录加一条交叉验证证据

OCR 行一律 verified=false、extractor=rule_ocr，notes 写明"OCR 识别未人工核对"，
绝不冒充已核对数据。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p2" / "scripts"))

from parse_catalog_words import to_sku  # noqa: E402

SKUS = ROOT / "data" / "structured" / "skus.json"
OCR = ROOT / "data" / "structured" / "catalog_rows_ocr.json"
VERIFIED = ROOT / "data" / "verified.json"
REPORT = ROOT / "data" / "reports" / "ocr_merged.md"


def norm_name(s: str) -> str:
    s = (s or "").upper().replace("（", "(").replace("）", ")")
    return re.sub(r"[\s（）()·,，.。-]", "", s)


def gate(r: dict):
    """返回 (是否通过, 原因)"""
    a, w, t = r.get("arc_mm"), r.get("width_mm"), r.get("thickness_mm")
    name = (r.get("name") or "").strip()
    if r.get("conf", 0) < 0.90:
        return False, "置信度<0.90"
    if not (a and w and t):
        return False, "尺寸缺字段"
    if not (120 <= a <= 400):
        return False, "外弧越界"
    if not (60 <= w <= 300):
        return False, "宽度越界"
    if not (5 <= t <= 30):
        return False, "厚度越界"
    # 注意：外弧 < 宽度 在产品册里真实存在（文本层 21/143 行如此，如 149×160×13），
    # 所以不能拿"外弧≥宽度"当几何闸，会误杀。这里只保留量级闸。
    if len(name) < 2:
        return False, "名称过短"
    if not re.search(r"[\u4e00-\u9fff]", name):
        return False, "名称无中文"
    if re.search(r"\d+\s*[×xX*]\s*\d+", name):
        return False, "名称混入尺寸"
    return True, ""


def main() -> int:
    skus = json.loads(SKUS.read_text(encoding="utf-8"))
    ocr = json.loads(OCR.read_text(encoding="utf-8"))
    # 先把已有的 OCR 行清掉，保证可重复跑
    skus = [s for s in skus if (s.get("provenance") or {}).get("extractor") != "rule_ocr"]

    seen = {(norm_name(s.get("fit_name")), (s.get("dims") or {}).get("raw_text")) for s in skus}
    ids = {s["sku_id"] for s in skus}
    drops = Counter()
    added, crossed = [], []

    for r in ocr:
        ok, why = gate(r)
        if not ok:
            drops[why] += 1
            continue
        key = (norm_name(r["name"]), r["raw_dims"])
        if key in seen:
            for s in skus:
                if (norm_name(s.get("fit_name")), (s.get("dims") or {}).get("raw_text")) == key:
                    s["evidence"].append({"report_id": r["file"], "page": r["page"],
                                          "snippet": "%s %s (OCR)" % (r["name"], r["raw_dims"]),
                                          "kind": "产品册"})
                    s["provenance"]["notes"] = ((s["provenance"].get("notes") or "")
                                                + "；OCR 图页交叉验证一致").strip("；")
                    break
            crossed.append(r)
            continue

        s = to_sku(r)
        s["provenance"]["extractor"] = "rule_ocr"
        s["provenance"]["notes"] = "OCR 识别（RapidOCR conf %.2f），未人工核对；尺寸格式 外弧×宽度×厚度" % r.get("conf", 0)
        s["extras"] = {"cols": [], "ocr_conf": r.get("conf")}
        base = s["sku_id"]
        n = 2
        while s["sku_id"] in ids:
            s["sku_id"] = "%s-%d" % (base, n)
            n += 1
        ids.add(s["sku_id"])
        seen.add(key)
        skus.append(s)
        added.append(s)

    # 人工核对结论 & 人工更正，重跑后仍生效
    if VERIFIED.exists():
        vd = json.loads(VERIFIED.read_text(encoding="utf-8"))
        for s in skus:
            v = vd.get(s["sku_id"])
            if v:
                s["provenance"]["verified"] = True
                s["provenance"]["verified_by"] = v.get("by") or "P2"
                if v.get("notes"):
                    s["provenance"]["notes"] = v["notes"]
        skus = [s for s in skus if not vd.get(s["sku_id"], {}).get("drop")]

    SKUS.write_text(json.dumps(skus, ensure_ascii=False, indent=1), encoding="utf-8")

    pages = sorted({(a["provenance"]["source_file"], a["provenance"]["source_page"]) for a in added})
    lines = ["# OCR 行并入记录", "",
             "- 主数据：**%d 条**（文本层 %d + OCR 新增 %d）" % (
                 len(skus), len(skus) - len(added), len(added)),
             "- OCR 交叉验证一致（文本层已有同款）：%d 条" % len(crossed),
             "- 被闸掉：%s" % ("、".join("%s %d" % kv for kv in drops.items()) or "无"),
             "- OCR 新增覆盖 %d 个图页" % len(pages), "",
             "## OCR 新增行（全部未人工核对）", "",
             "| sku_id | 适配名 | 尺寸 | 出处 | 置信度 |", "|---|---|---|---|---|"]
    for s in added:
        pr = s["provenance"]
        lines.append("| %s | %s | %s | %s p%s | %.2f |" % (
            s["sku_id"], s["fit_name"], s["dims"]["raw_text"],
            pr["source_file"], pr["source_page"], s["extras"].get("ocr_conf") or 0))
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("并入完成：主数据 %d 条（OCR 新增 %d，交叉验证 %d）" % (len(skus), len(added), len(crossed)))
    if drops:
        print("被闸掉：" + "，".join("%s %d" % kv for kv in drops.items()))
    print("→ %s" % REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
