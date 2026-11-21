# -*- coding: utf-8 -*-
"""把 data/inbox 里的 PDF / DOCX / XLSX / TXT 统一抽成带页码标记的纯文本。

产出：
  data/text/<stem>.txt        每页以 [[PAGE n]] 开头
  data/text/_manifest.json    每份文件的页数、字符数、是否疑似扫描件

用法：
  python scripts/extract_text.py
  python scripts/extract_text.py --inbox data/inbox --out data/text
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

PAGE_MARK = "[[PAGE {n}]]"


def _safe_stem(p: Path) -> str:
    s = re.sub(r"[^\w\-\.\u4e00-\u9fff]+", "_", p.stem, flags=re.UNICODE)
    return s.strip("_")[:80] or "doc"


def pdf_pages(path: Path, layout: bool = False):
    """layout=True 用 pypdf 的版式模式（保留列位置，适合产品册表格）。"""
    if layout:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return [(p.extract_text(extraction_mode="layout") or "") for p in reader.pages]
    try:
        import pdfplumber  # type: ignore
        pages = []
        with pdfplumber.open(str(path)) as pdf:
            for pg in pdf.pages:
                txt = pg.extract_text() or ""
                tables = pg.extract_tables() or []
                if tables:
                    rows = []
                    for t in tables:
                        for row in t:
                            rows.append(" | ".join((c or "").replace("\n", " ").strip() for c in row))
                    txt += "\n[TABLE]\n" + "\n".join(rows)
                pages.append(txt)
        return pages
    except ImportError:
        pass
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return [(p.extract_text() or "") for p in reader.pages]


def docx_text(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    out = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        out.append("[TABLE]")
        for row in t.rows:
            out.append(" | ".join(c.text.replace("\n", " ").strip() for c in row.cells))
    return "\n".join(out)


def xlsx_text(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append("[SHEET] %s" % ws.title)
        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c) for c in row]
            if any(cells):
                out.append(" | ".join(cells))
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", default=str(ROOT / "data" / "inbox"))
    ap.add_argument("--out", default=str(ROOT / "data" / "text"))
    ap.add_argument("--layout", action="store_true", help="版式模式：保留列位置（产品册表格必备）")
    args = ap.parse_args(argv)

    inbox, outdir = Path(args.inbox), Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    exts = {".pdf", ".docx", ".xlsx", ".txt", ".md"}
    files = [p for p in sorted(inbox.rglob("*"))
             if p.is_file() and p.suffix.lower() in exts and not p.name.startswith("_")]
    if not files:
        print("[!] %s 里没有可处理的文件。把赛题资料包（PDF/DOCX/XLSX）丢进去再跑。" % inbox)
        return 1

    manifest = []
    for f in files:
        try:
            if f.suffix.lower() == ".pdf":
                pages = pdf_pages(f, layout=args.layout)
            elif f.suffix.lower() == ".docx":
                pages = [docx_text(f)]
            elif f.suffix.lower() == ".xlsx":
                pages = [xlsx_text(f)]
            else:
                pages = [f.read_text(encoding="utf-8", errors="ignore")]
        except Exception as e:  # noqa: BLE001
            print("[ERR] %s: %s: %s" % (f.name, type(e).__name__, e))
            manifest.append({"file": str(f), "ok": False, "error": str(e)})
            continue

        chunks = [PAGE_MARK.format(n=i + 1) + "\n" + (t or "").strip() for i, t in enumerate(pages)]
        text = "\n\n".join(chunks)
        dst = outdir / (_safe_stem(f) + ".txt")
        dst.write_text(text, encoding="utf-8")
        chars_per_page = [len((t or "").strip()) for t in pages]
        empty = sum(1 for c in chars_per_page if c < 20)
        manifest.append({
            "source": str(f), "text": str(dst), "pages": len(pages),
            "chars": len(text), "empty_pages": empty,
            "scanned_likely": bool(pages) and (sum(chars_per_page) / max(len(pages), 1) < 60),
        })
        print("[OK] %-40s pages=%-4d chars=%-7d empty=%-3d %s" % (
            f.name, len(pages), len(text), empty, "<-- 疑似扫描件，需 OCR" if manifest[-1]["scanned_likely"] else ""))

    (outdir / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = [m for m in manifest if m.get("scanned_likely")]
    print("\n完成 %d 份；疑似扫描件 %d 份。清单：%s" % (len(manifest), len(bad), outdir / "_manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
