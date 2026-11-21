# -*- coding: utf-8 -*-
"""把 kooying 出口册 p32–34（美系 FMSI / 欧系 BPW / SAF 对照表）从 OCR 结果拼成结构化对照表。

这三页没有文本层，是给海外客户看的"码对码"表：
  美系: FMSI NO. | WIDTH | OE REFERENCE | BRAKE SHOE | HARDWARE KITS
  欧系: SIZE | BRAKE SHOE | OE REFERENCE | LINING WVA（BPW / SAF / 其他）

输出 data/structured/export_refs.json，每条带页码与 OCR 置信度，verified 一律 false。
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"Y:\hks")
OUT = ROOT / "data" / "structured" / "export_refs.json"
REPORT = ROOT / "data" / "reports" / "export_refs.md"

RE_WIDTH = re.compile(r"^\d{1,2}(?:\.\d{1,3})?\s*[\"”]?$")
RE_FMSI = re.compile(r"^\d{4}[A-Z]?$")
RE_SHOE = re.compile(r"^\d{4}\s?(?:Q|ES2|ES|Q2|Q\+)$", re.I)
RE_HW = re.compile(r"^E-?\d{3,5}[A-Z]?$", re.I)
RE_OE = re.compile(r"^(?:A|R|K|B|W)?\s?\d{3,7}[A-Z]{0,3}\d{0,3}$", re.I)
RE_SIZE = re.compile(r"^\d{3}\s?[xX×*]\s?\d{2,3}(?:\.\d)?$")
RE_WVA = re.compile(r"^\d{4,5}$")


def rows_of(items, tol=12):
    """按 y 聚类成行（OCR 有 3–5px 抖动）。
    注意：一个版面常有左右两张并排的表，必须按 x 分块再聚类，
    否则左表的 FMSI 会和右表的型号配成一对（错配）。"""
    xs = sorted(i["x"] for i in items)
    mid = xs[len(xs) // 2]
    items = [(i, 0 if i["x"] < mid else 1) for i in items]
    out = []
    for blk in (0, 1):
        sub = sorted([i for i, b in items if b == blk], key=lambda i: (i["y"], i["x"]))
        cur, last_y = [], None
        for it in sub:
            if last_y is None or abs(it["y"] - last_y) <= tol:
                cur.append(it)
                last_y = it["y"] if last_y is None else (last_y + it["y"]) / 2
            else:
                out.append(sorted(cur, key=lambda i: i["x"]))
                cur, last_y = [it], it["y"]
        if cur:
            out.append(sorted(cur, key=lambda i: i["x"]))
    return out


def parse_page(page: int, kind: str):
    f = ROOT / "data" / "ocr" / ("kooying catalog_p%02d.json" % page)
    items = json.loads(f.read_text(encoding="utf-8"))
    out = []
    for r in rows_of(items):
        toks = [(i["x"], (i["text"] or "").strip(), i["conf"], i["y"]) for i in r]
        txt = [t for _, t, _, _ in toks]
        if kind == "american":
            fmsi = next((t for t in txt if RE_FMSI.match(t)), None)
            shoe = next((t for t in txt if RE_SHOE.match(t)), None)
            if not (fmsi and shoe):
                continue
            width = next((t for t in txt if re.match(r'^\d{1,2}(\.\d{1,3})?"?$', t)), None)
            hw = next((t for t in txt if RE_HW.match(t)), None)
            oe = next((t for t in txt if t not in (fmsi, shoe, width, hw) and re.match(r"^A\s?\d{3,7}[A-Z]?\d{0,4}$", t, re.I)), None)
            # 自校验：4524Q 必须配 FMSI 4524，配不上的说明左右表串行了，直接丢
            if re.sub(r"\D", "", shoe)[:4] != re.sub(r"\D", "", fmsi)[:4]:
                continue
            if oe:
                oe = re.sub(r"\s+", "", oe)
            out.append({"kind": "american", "fmsi": fmsi, "width": width, "oe_ref": oe,
                        "shoe_code": shoe, "hardware": hw, "page": page,
                        "conf": round(min(i[2] for i in toks), 3)})
        else:
            size = next((t for t in txt if RE_SIZE.match(t)), None)
            shoe = next((t for t in txt if RE_SHOE.match(t) or re.match(r"^[A-Z]{2,3}\d{3,4}[A-Z]?$", t)), None)
            if not (size and shoe):
                continue
            wva = next((t for t in txt if re.fullmatch(r"\d{5}", t)), None)
            oe = next((t for t in txt if re.match(r"^\d{6,9}$", t)), None)
            out.append({"kind": kind, "size": size.replace(" ", ""), "shoe_code": shoe,
                        "oe_ref": oe, "wva": wva, "page": page,
                        "conf": round(min(i[2] for i in toks), 3)})
    return out


def main() -> int:
    recs = parse_page(32, "american") + parse_page(33, "bpw") + parse_page(34, "saf")
    for r in recs:
        r["verified"] = False
        r["source"] = "kooying catalog p%d（出口册图页，OCR）" % r["page"]
    OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# 出口册对码表（kooying p32–34，OCR 重建）", "",
          "> 这三页是给海外客户的**码对码**表：外商报 FMSI / OE / WVA 号，我们反查自己的刹车蹄与硬件包。",
          "> 全部来自图页 OCR，**未人工核对（verified=false）**，置信度见每行。", "",
          "**已知断点（必须说清）**：这 34 条把「外商号」对到了「出口册型号」（如 4524Q、BPW180），",
          "但这些出口型号**不在国内 217 条 SKU 里**（交叉核对 0/34 命中）。",
          "也就是说：外商报 FMSI → 我们能说'对应 4524Q，册子 p32'；但'4524Q 对应哪个国内型号/多少钱/有没有货'，",
          "资料包里没有这张对照表，**不能编**。要打通，得向客户要「出口编码 ↔ 国内型号」映射。", "",
          "| 类型 | 关键码 | 尺寸 | 我方型号 | OE 参考 | 硬件包/WVA | 页 | 置信 |",
          "|---|---|---|---|---|---|---|---|"]
    for r in recs:
        md.append("| %s | %s | %s | %s | %s | %s | p%s | %.2f |" % (
            r["kind"], r.get("fmsi") or r.get("shoe_code"), r.get("width") or r.get("size") or "—",
            r["shoe_code"], r.get("oe_ref") or "—", r.get("hardware") or r.get("wva") or "—",
            r["page"], r["conf"]))
    REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("解析出 %d 条：美系 %d / BPW %d / SAF %d" % (
        len(recs), sum(1 for r in recs if r["kind"] == "american"),
        sum(1 for r in recs if r["kind"] == "bpw"), sum(1 for r in recs if r["kind"] == "saf")))
    print("->", OUT)
    print("->", REPORT)
    for r in recs[:10]:
        print("   ", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
