# -*- coding: utf-8 -*-
"""对 data/text 做关键词普查：确认"数据到底存不存在、在哪份里"。

判断 1（几万组测试报告是真金矿）能不能站住，就看这份报告的数字。

用法：
  python scripts/scan_keywords.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[2]

GROUPS = {
    "车桥品牌": ["BPW", "SAF", "富华", "FUWA", "中集", "CIMC", "蓬翔", "约斯特", "JOST", "安凯", "汉德"],
    "关键字段": ["鼓径", "片宽", "厚度", "外径", "摩擦系数", "磨损率", "材质", "半金属", "陶瓷", "NAO",
                 "铆接", "粘接", "MOQ", "起订量", "型号"],
    "标准/认证": ["FMVSS", "ECE", "R90", "GB5763", "E11", "ECE-R90", "DOT"],
    "市场/客户": ["询价", "报价", "客户", "出口", "海", "售后"],
}
PATTERNS = {
    "尺寸串 420x200": re.compile(r"\d{2,4}\s*[xX×*]\s*\d{2,4}"),
    "报告编号": re.compile(r"(?:TR|TST|REP|报告)[-_ ]?\d{3,}"),
    "百分比数值": re.compile(r"\d{1,2}\.\d{1,2}\s*%"),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=str(ROOT / "data" / "text"))
    ap.add_argument("--out", default=str(ROOT / "data" / "reports" / "keyword_census.md"))
    args = ap.parse_args(argv)

    tdir = Path(args.text)
    files = [p for p in sorted(tdir.glob("*.txt")) if not p.name.startswith("_")]
    if not files:
        print("[!] %s 里没有 .txt，先跑 scripts/extract_text.py" % tdir)
        return 1

    docs = {p.name: p.read_text(encoding="utf-8", errors="ignore") for p in files}
    lines = ["# 关键词普查（%d 份文档）" % len(docs), "",
             "> 用途：回答「数据在不在、在哪个文件、够不够撑起 Demo」。", ""]

    for group, kws in GROUPS.items():
        lines += ["## " + group, "", "| 关键词 | 出现次数 | 命中文件数 | 首个上下文 |", "|---|---|---|---|"]
        for kw in kws:
            total, hit_files, ctx = 0, 0, ""
            for name, txt in docs.items():
                n = txt.count(kw)
                if n:
                    total += n
                    hit_files += 1
                    if not ctx:
                        i = txt.find(kw)
                        s = txt[max(0, i - 30): i + 40].replace("\n", " ").replace("|", "/")
                        ctx = "%s: …%s…" % (name, s.strip())
            if total:
                lines.append("| %s | %d | %d | %s |" % (kw, total, hit_files, ctx[:90]))
        lines.append("")

    lines += ["## 结构化信号", "", "| 模式 | 命中次数 |", "|---|---|"]
    for name, pat in PATTERNS.items():
        total = sum(len(pat.findall(t)) for t in docs.values())
        lines.append("| %s | %d |" % (name, total))
    lines.append("")

    dim_files = [n for n, t in docs.items() if PATTERNS["尺寸串 420x200"].search(t)]
    lines += ["## 结论提示（自动生成，人工修正）", "",
              "- 含尺寸串的文件：%d 份 %s" % (len(dim_files), dim_files[:5]),
              "- 若「摩擦系数/磨损率」命中为 0，说明测试报告还没进 inbox，**先补资料，不要把 PPT 数字编出来**。",
              ""]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("写出: %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
