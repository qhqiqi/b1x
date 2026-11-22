# -*- coding: utf-8 -*-
r"""P3 前端换版后的自检：文件是否齐、接口字段是否还对得上、HTTP 是否 200。

用法：python scripts\check_app.py            （默认查 8787）
     python scripts\check_app.py --port 8787 --query "客户要 FMSI 4524"
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"Y:\hks")
APP = ROOT / "app"

REQUIRED = ["index.html", "match.html", "match.js", "styles.css", "match.css", "samples.js"]
FIELDS = ["mode", "candidates", "export_matches", "followups", "confidence",
          "evidence", "sku_id", "report_id", "page", "verified", "ocr"]


def head(title):
    print("\n== %s" % title)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--query", default="客户要 FMSI 4524")
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.port
    bad = 0

    head("1. app/ 文件")
    if not APP.exists():
        print("  ✗ app/ 不存在")
        return 1
    for name in REQUIRED:
        p = APP / name
        print("  %s %-14s %s" % ("✓" if p.exists() else "✗", name,
                                 ("%.1f KB" % (p.stat().st_size / 1024)) if p.exists() else "缺失"))
        bad += 0 if p.exists() else 1
    extra = sorted(p.relative_to(APP).as_posix() for p in APP.rglob("*")
                   if p.is_file() and p.suffix in (".html", ".js", ".css"))
    print("  共 %d 个页面/脚本文件" % len(extra))

    head("2. 接口字段对齐")
    if (APP / "match.js").exists():
        js = (APP / "match.js").read_text(encoding="utf-8", errors="replace")
        used = [f for f in FIELDS if re.search(r"\b%s\b" % f, js)]
        miss = [f for f in FIELDS if f not in used]
        print("  前端用到: %s" % "、".join(used))
        if miss:
            print("  前端未引用（可能换了解析方式，人工确认）: %s" % "、".join(miss))
    else:
        print("  ✗ 没有 match.js，跳过")

    head("3. HTTP 冒烟")
    for path in ["/health", "/app/match.html", "/app/index.html", "/app/match.js"]:
        try:
            with urllib.request.urlopen(base + path, timeout=6) as r:
                print("  ✓ %-18s %s  %d 字节" % (path, r.status, len(r.read())))
        except Exception as e:  # noqa: BLE001
            print("  ✗ %-18s %s" % (path, e))
            bad += 1

    head("4. 真实查询")
    try:
        url = base + "/match?q=" + urllib.parse.quote(args.query)
        with urllib.request.urlopen(url, timeout=10) as r:
            j = json.loads(r.read().decode("utf-8"))
        keys = set(j)
        need = {"mode", "candidates", "followups", "export_matches"}
        print("  查询: %s" % args.query)
        print("  mode=%s 候选=%d 对码=%d 追问=%d  %sms" % (
            j.get("mode"), len(j.get("candidates", [])), len(j.get("export_matches", [])),
            len(j.get("followups", [])), j.get("elapsed_ms")))
        missing = need - keys
        if missing:
            print("  ✗ 返回缺字段: %s" % missing)
            bad += 1
        else:
            print("  ✓ 顶层字段齐全")
        for c in j.get("candidates", [])[:1]:
            print("  样例候选: %s / %s / %s" % (c.get("sku_id"), c.get("confidence"),
                                            (c.get("evidence") or [{}])[0].get("page")))
    except Exception as e:  # noqa: BLE001
        print("  ✗ 查询失败: %s" % e)
        bad += 1

    print("\n结果：%s" % ("全部通过" if bad == 0 else "%d 项异常" % bad))
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
