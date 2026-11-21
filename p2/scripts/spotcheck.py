# -*- coding: utf-8 -*-
"""人工抽检工具：生成抽样清单 → 在 Excel 里打勾 → 回写 verified。

三步：
    1) python p2/scripts/spotcheck.py --gen --n 12     # 生成 data/reports/spotcheck.csv
    2) 用 Excel 打开 CSV（UTF-8 BOM，中文不乱码），对着 PDF 原页核「适配名 + 尺寸」，判定列填 ok / no
    3) python p2/scripts/spotcheck.py --apply          # ok → verified=true；no → 生成不一致清单

抽样分层（按 文件+页 轮转），种子固定可复现。
"机器预判"列是独立复核（用版式文本二次判断），只用来排优先级，不替代人眼。
"""
import argparse
import csv
import json
import random
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
SKUS = ROOT / "data" / "structured" / "skus.json"
CSV_PATH = ROOT / "data" / "reports" / "spotcheck.csv"
MD_PATH = ROOT / "data" / "reports" / "spotcheck.md"
BAD_PATH = ROOT / "data" / "reports" / "spotcheck_mismatch.md"

KANGXI = {"⻛": "风", "⻰": "龙", "⻁": "虎", "⻢": "马", "⻋": "车", "⻘": "青",
          "⻓": "长", "⻔": "门", "⻮": "齿", "⻬": "齐", "⻩": "黄"}
DIMM = None


def load():
    return json.loads(SKUS.read_text(encoding="utf-8"))


def norm(s: str) -> str:
    s = "".join(KANGXI.get(c, c) for c in (s or ""))
    s = unicodedata.normalize("NFKC", s)
    s = "".join(ch for ch in s if ch >= " " or ch == "")
    return s.replace("（", "(").replace("）", ")").replace(" ", "")


def page_lines(source_file: str, page) -> list:
    f = ROOT / "data" / "text_layout" / ("%s.txt" % source_file)
    if not f.exists():
        return []
    import re
    B = chr(92)
    pat = B + "[" + B + "[" + "PAGE (" + B + "d+)" + B + "]" + B + "]"
    parts = re.split(pat, f.read_text(encoding="utf-8", errors="ignore"))
    for i in range(1, len(parts), 2):
        if parts[i] == str(page):
            return [l for l in parts[i + 1].splitlines() if l.strip()]
    return []


def machine_check(sku: dict) -> str:
    """独立复核：名称与尺寸是否同页、且横向位置对得上。
    返回：机器一致(同行) / 机器一致(上下行) / 可疑(未同页同区) / 需看图(图片页)"""
    global DIMM
    if DIMM is None:
        import re
        DIMM = re.compile(r"\d{2,4}\s*[×xX*]\s*\d{2,3}")
    prov = sku.get("provenance") or {}
    lines = page_lines(prov.get("source_file") or "", prov.get("source_page"))
    if not lines:
        return "需看图(图片页)"
    name = norm(sku.get("fit_name") or "")
    dims = norm((sku.get("dims") or {}).get("raw_text") or "")
    if not name or not dims:
        return "可疑(字段空)"
    short = name.replace("(ABS)", "").replace("ABS", "") or name
    nl = [norm(l) for l in lines]
    for i, line in enumerate(nl):
        if dims not in line:
            continue
        for key in (name, short):
            if key and key in line:
                return "机器一致(同行)"
        p_dim = line.find(dims)
        for j in range(max(0, i - 2), min(len(nl), i + 3)):
            if j == i:
                continue
            for key in (name, short):
                p_name = nl[j].find(key) if key else -1
                if key and p_name >= 0 and abs(p_name - p_dim) <= 70:
                    return "机器一致(上下行)"
    return "可疑(未同页同区)"


def gen(n: int, seed: int) -> int:
    skus = [s for s in load() if not s.get("_placeholder")]
    pools = defaultdict(list)
    for s in skus:
        prov = s.get("provenance") or {}
        pools[(prov.get("source_file"), prov.get("source_page"))].append(s)
    keys = sorted(pools, key=lambda k: (str(k[0]), k[1] or 0))
    random.seed(seed)
    for k in keys:
        random.shuffle(pools[k])
    picked, i = [], 0
    while len(picked) < n and any(pools[k] for k in keys):
        k = keys[i % len(keys)]
        if pools[k]:
            picked.append(pools[k].pop())
        i += 1

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["序号", "sku_id", "适配名", "尺寸原文", "产品册", "页码",
                    "机器预判", "判定(ok/no)", "备注"])
        for j, s in enumerate(picked, 1):
            d = (s.get("dims") or {}).get("raw_text") or ""
            prov = s.get("provenance") or {}
            w.writerow([j, s["sku_id"], s.get("fit_name"), d, prov.get("source_file"),
                        prov.get("source_page"), machine_check(s), "", ""])

    lines = ["# 人工抽检清单（%d 条）" % len(picked), "",
             "| # | sku_id | 适配名 | 尺寸原文 | 产品册 | 页 | 机器预判 | 人眼判定 |",
             "|---|---|---|---|---|---|---|---|"]
    for j, s in enumerate(picked, 1):
        prov = s.get("provenance") or {}
        lines.append("| %d | %s | %s | %s | %s | %s | %s | |" % (
            j, s["sku_id"], s.get("fit_name"), (s.get("dims") or {}).get("raw_text"),
            prov.get("source_file"), prov.get("source_page"), machine_check(s)))
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("抽样 %d 条（种子 %d），覆盖 %d 个页面" % (len(picked), seed,
                                                 len({(s.get("provenance") or {}).get("source_page") for s in picked})))
    print("清单 → %s" % CSV_PATH)
    for j, s in enumerate(picked, 1):
        prov = s.get("provenance") or {}
        print("  %2d) %-16s %-18s %s p%s  [%s]" % (
            j, s.get("fit_name"), (s.get("dims") or {}).get("raw_text"),
            prov.get("source_file"), prov.get("source_page"), machine_check(s)))
    return 0


def apply(by: str) -> int:
    if not CSV_PATH.exists():
        print("没有 %s，先跑 --gen" % CSV_PATH)
        return 2
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    verdict = {}
    for r in rows:
        v = (r.get("判定(ok/no)") or "").strip().lower()
        if v:
            verdict[r["sku_id"]] = (v, (r.get("备注") or "").strip())

    data = load()
    ok = bad = 0
    bad_list = []
    for s in data:
        if s["sku_id"] in verdict:
            v, note = verdict[s["sku_id"]]
            if v.startswith("ok") or v in ("y", "yes", "1", "对", "一致"):
                s["provenance"]["verified"] = True
                s["provenance"]["verified_by"] = by
                s["provenance"]["notes"] = ((s["provenance"].get("notes") or "") + "；抽检一致(%s)" % by).strip("；")
                ok += 1
            else:
                bad += 1
                bad_list.append((s["sku_id"], s.get("fit_name"), (s.get("dims") or {}).get("raw_text"),
                                 (s.get("provenance") or {}).get("source_page"), note))
    SKUS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if bad_list:
        lines = ["# 抽检不一致清单（必须处理）", "",
                 "| sku_id | 适配名 | 当前尺寸 | 页 | 你看到的不一致 |", "|---|---|---|---|---|"]
        for b in bad_list:
            lines.append("| %s | %s | %s | %s | %s |" % b)
        lines += ["", "处理方式：改解析器（不要手改 skus.json），重跑 parse_layout.py --merge，再抽一次。"]
        BAD_PATH.write_text("\n".join(lines), encoding="utf-8")
        print("不一致 %d 条 → %s" % (bad, BAD_PATH))
    print("已回写：一致 %d（by=%s），不一致 %d，未判定 %d" % (ok, by, bad, len(rows) - ok - bad))
    print("可以对外说：抽检 %d 条，一致 %d 条。" % (ok + bad, ok))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--by", default="P2")
    args = ap.parse_args(argv)
    if args.apply:
        return apply(args.by)
    return gen(args.n, args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
