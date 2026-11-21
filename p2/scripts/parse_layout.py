# -*- coding: utf-8 -*-
"""版式文本 → 产品册表格行（列位置感知，确定性解析）。

关键点：pypdf layout 模式用空格保留了列位置。于是：
  1) 单元格 = 被 2+ 空格分隔的片段，并记录其字符偏移（≈ 横向坐标）；
  2) 尺寸单元格 → 在同一行左侧、或上方 1-4 行中找横向重叠的名称单元格；
  3) 单空格分隔的"名称 尺寸 数量"按顺序就近配对。

用法：python p2/scripts/parse_layout.py [--merge]
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
RADICALS = {"⻛": "风", "⻰": "龙", "⻁": "虎", "⻢": "马", "⻋": "车", "⻥": "鱼", "⻦": "鸟",
            "⻨": "麦", "⻩": "黄", "⻭": "齿", "⻮": "齿", "⻬": "齐", "⻫": "齐", "⻅": "见",
            "⻓": "长", "⻔": "门", "⻜": "飞", "⻙": "韦", "⻚": "页", "⻝": "食", "⻤": "鬼",
            "⻧": "卤", "⻪": "黾", "⻯": "龙", "⻲": "龟", "⻳": "龟"}
DIM = re.compile(r"(\d{2,4})\s*[×xX]\s*(\d{2,3})\s*[×xX]\s*(\d{1,2}(?:\.\d)?)(?:\s*/\s*(\d{1,2}(?:\.\d)?))?")
CJK = re.compile(r"[\u4e00-\u9fff]")
NUM = re.compile(r"^\(?\d{1,3}(?:\.\d)?\)?\.?$")


RADICALS.update({"⻘": "青", "⻮": "齿", "⻬": "齐", "⻩": "黄", "⻪": "黾", "⻭": "齿"})
CTRL = re.compile(r"[\x00-\x1f\x7f]") if False else re.compile("[" + chr(0) + "-" + chr(31) + chr(127) + "]")


def clean(s):
    s = CTRL.sub("", s)
    s = "".join(RADICALS.get(c, c) for c in s)
    s = unicodedata.normalize("NFKC", s) if not s.isascii() else s
    s = "".join(RADICALS.get(c, c) for c in s)
    return s.replace("（", "(").replace("）", ")").strip()


def cells(line):
    out, pos = [], 0
    for part in re.split(r"(\s{2,})", line):
        if part.strip():
            out.append([pos, pos + len(part), clean(part.strip())])
        pos += len(part)
    return out


def is_name(t):
    t = t.strip()
    if len(t) < 2 or DIM.search(t) or NUM.match(t):
        return False
    if re.fullmatch(r"[\d\s./×xX+\-()]+", t):
        return False
    if re.fullmatch(r"(?i)GY?s?[-\s]?\d{2,4}", t):
        return True
    # 短型号名：Q54 / Hq8555 / J6 这类（产品册里确实存在）
    if re.fullmatch(r"[A-Za-z]{1,3}\d{1,4}[A-Za-z]?", t):
        return True
    return bool(CJK.search(t))


def parse_page(pno, body, fname, base_id):
    rows, prev_names = [], []      # prev_names: [(line_idx, start, end, text)]
    lines = [l for l in body.splitlines() if l.strip()]
    for li, line in enumerate(lines):
        cs = cells(line)
        for idx, (s, e, txt) in enumerate(cs):
            m = DIM.search(txt)
            if not m:
                continue
            head = txt[: m.start()].strip()
            tail = txt[m.end():].strip()
            qty = [t for t in re.split(r"\s+", tail) if t][:3]
            name, name_line = None, None
            if head and is_name(head):
                name, name_line = head, li
            elif idx > 0 and is_name(cs[idx - 1][2]):
                name, name_line = cs[idx - 1][2], li
            else:
                # 名称可能在尺寸上方（常见）或在下方（块状排版，如 p17 的 Q54）
                # 打分：上方给折扣（0.5），下方不打折；同分再看横向距离
                best = None
                for (pli, ps, pe, ptxt) in prev_names:
                    dy = li - pli
                    if dy > 4:
                        continue
                    if ps <= e + 8 and pe >= s - 8:      # 横向重叠（容差）
                        sc = dy * 0.5 + abs(ps - s) * 0.01
                        if best is None or sc < best[0]:
                            best = (sc, ptxt)
                for lj in range(li + 1, min(len(lines), li + 3)):
                    for (s2, e2, t2) in cells(lines[lj]):
                        if not is_name(t2):
                            continue
                        if s2 <= e + 10 and e2 >= s - 10:
                            sc = (lj - li) * 1.0 + abs(s2 - s) * 0.01
                            if best is None or sc < best[0]:
                                best = (sc, t2)
                if best:
                    name = best[1]
            if name is None:
                continue
            rows.append({
                "row_id": "L%04d" % (base_id + len(rows)),
                "file": fname, "page": pno, "name": clean(name), "raw_dims": m.group(0),
                "arc_mm": float(m.group(1)), "width_mm": float(m.group(2)),
                "thickness_mm": float(m.group(3)),
                "thickness_alt_mm": float(m.group(4)) if m.group(4) else None,
                "extras": qty,
            })
        prev_names = [(li, s, e, clean(t)) for (s, e, t) in cs if is_name(t)]
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=str(ROOT / "data" / "text_layout"))
    ap.add_argument("--out", default=str(ROOT / "data" / "structured" / "catalog_rows.json"))
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args(argv)

    all_rows = []
    for f in sorted(Path(args.text).glob("*.txt")):
        if f.name.startswith("_"):
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        pages = re.split(r"\[\[PAGE (\d+)\]\]", txt)
        got = []
        for i in range(1, len(pages), 2):
            got += parse_page(int(pages[i]), pages[i + 1], f.stem, len(all_rows) + len(got))
        if got:
            print("%-22s 行 %-4d 页 %s" % (f.stem, len(got), sorted({g["page"] for g in got})))
        all_rows += got

    print("\n合计 %d 行" % len(all_rows))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(all_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("写出 %s" % out)

    if args.merge:
        from parse_catalog_words import to_sku   # 复用同一个 to_sku
        skus, seen = [], set()
        for r in all_rows:
            if len(r["name"]) < 2:
                continue
            s = to_sku(r)
            key = (s["sku_id"], s["dims"]["raw_text"])
            if key in seen:
                continue
            seen.add(key)
            # 同一适配名有多个尺寸（A/B 变体）时给 sku_id 加后缀，保证主键唯一
            n = 2
            while any(x["sku_id"] == s["sku_id"] for x in skus):
                s["sku_id"] = "%s-%d" % (s["sku_id"].rsplit("-", 1)[0] if s["sku_id"].rsplit("-", 1)[-1].isdigit() else s["sku_id"], n)
                n += 1
            skus.append(s)
        # 应用人工确认的更正（可追溯：每条都写明为什么）
        fixp = ROOT / "data" / "curated_fixes.json"
        if fixp.exists():
            fx = {f["sku_id"]: f for f in json.loads(fixp.read_text(encoding="utf-8"))}
            for s in skus:
                f = fx.get(s["sku_id"])
                if not f:
                    continue
                if f.get("action") == "rename" and f.get("new_fit_name"):
                    s["fit_name"] = f["new_fit_name"]
                elif f.get("action") == "drop":
                    s["_drop"] = True
                    continue
                s["provenance"]["notes"] = ((s["provenance"].get("notes") or "") + "；人工更正：" + f.get("note", "")).strip("；")
                s["provenance"]["verified"] = True
                s["provenance"]["verified_by"] = "P2-人工核对"

        skus = [s for s in skus if not s.get("_drop")]
        # 人工核对结论单独存 data/verified.json，重跑解析不会丢
        vp = ROOT / "data" / "verified.json"
        if vp.exists():
            vd = json.loads(vp.read_text(encoding="utf-8"))
            for s in skus:
                v = vd.get(s["sku_id"])
                if v:
                    s["provenance"]["verified"] = True
                    s["provenance"]["verified_by"] = v.get("by") or "P2"
                    if v.get("notes"):
                        s["provenance"]["notes"] = v["notes"]
            skip = {k for k in vd if vd[k].get("drop")}
            if skip:
                skus = [s for s in skus if s["sku_id"] not in skip]
        tgt = ROOT / "data" / "structured" / "skus.json"
        tgt.write_text(json.dumps(skus, ensure_ascii=False, indent=2), encoding="utf-8")
        print("合并 → skus.json：%d 条" % len(skus))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
