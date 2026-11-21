# -*- coding: utf-8 -*-
"""海外对码：外商报 FMSI / OE / WVA / 英制尺寸，反查我们出口册里的对应型号。

数据来自 kooying 出口册 p32–34（美系 FMSI 表、BPW 表、SAF 表），图页 OCR 重建，
每条带页码证据，verified 一律 False —— 答辩时只能说"册子上写着"，不能说"我们核过"。
"""
import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "data" / "structured" / "export_refs.json"
_CACHE = {"data": None, "mtime": None}

RE_FMSI = re.compile(r"(?<![A-Z0-9])(\d{4})(?![0-9])")
RE_WVA = re.compile(r"(?<![A-Z0-9])(\d{5})(?![0-9])")
RE_OE = re.compile(r"\b([A-Z]{1,2}\s?\d{3,7}[A-Z]?\d{0,4})\b")
RE_IMP = re.compile(r"(\d{2,3}(?:\.\d{1,2})?)\s*[xX×*\"”]\s*(\d{2,3}(?:\.\d{1,2})?)(?:\s*[xX×*\"”]\s*(\d{1,2}(?:\.\d{1,2})?))?")


def _load():
    if not _PATH.exists():
        return []
    m = _PATH.stat().st_mtime
    if _CACHE["data"] is None or _CACHE["mtime"] != m:
        _CACHE["data"] = json.loads(_PATH.read_text(encoding="utf-8"))
        _CACHE["mtime"] = m
    return _CACHE["data"]


def _norm(s):
    return re.sub(r"[^A-Z0-9.]", "", (s or "").upper())


def lookup(query: str, limit: int = 3):
    """返回与这句查询对得上的出口册记录（按可信度降序）。"""
    q = (query or "").upper()
    qn = _norm(q)
    refs = _load()
    if not refs or not qn:
        return []
    kind_pref = None
    if re.search(r"\bBPW\b", q):
        kind_pref = "bpw"
    elif re.search(r"\bSAF\b|赛夫", q):
        kind_pref = "saf"
    elif re.search(r"AMERICAN|美系|FMSI", q):
        kind_pref = "american"

    oe_hits = [_norm(m) for m in RE_OE.findall(q)]
    # FMSI/WVA 要在"保留空格"的串上找：'FMSI 4524' 里 4524 前面是空格不是字母；
    # 但如果先去掉空格变成 FMSI4524 就会被 (?<![A-Z0-9]) 挡住。
    q_sp = re.sub(r"[^A-Z0-9. ]", " ", q)
    q_sp = re.sub(r"s+", " ", q_sp)
    fmsi = [m for m in RE_FMSI.findall(q_sp)]
    wva = [m for m in RE_WVA.findall(q_sp)]
    sizes = [tuple(x for x in m if x) for m in RE_IMP.findall(q)]

    out = []
    for r in refs:
        score, why = 0.0, []
        if r.get("fmsi") and r["fmsi"] in fmsi:
            score, _ = 0.98, why.append("FMSI %s 命中" % r["fmsi"])
        if r.get("oe_ref") and _norm(r["oe_ref"]) in oe_hits:
            score = max(score, 0.96)
            why.append("OE 号 %s 命中" % r["oe_ref"])
        if r.get("wva") and r["wva"] in wva:
            score = max(score, 0.9)
            why.append("WVA %s 命中" % r["wva"])
        if r.get("shoe_code") and _norm(r["shoe_code"]) == qn:
            score = max(score, 0.95)
            why.append("我方型号 %s 直查" % r["shoe_code"])
        if r.get("size"):
            rs = _norm(r["size"])
            for a, b, *c in sizes:
                if rs.startswith(_norm(a)) and _norm(b) in rs:
                    score = max(score, 0.85)
                    why.append("英制尺寸 %s 对上 %s" % ("x".join([a, b] + c), r["size"]))
                    break
        if not score:
            continue
        if kind_pref and r.get("kind") != kind_pref:
            score -= 0.05
            why.append("（品牌不是 %s，降权）" % kind_pref)
        out.append({
            "score": round(score, 3),
            "kind": r.get("kind"),
            "fmsi": r.get("fmsi"),
            "oe_ref": r.get("oe_ref"),
            "shoe_code": r.get("shoe_code"),
            "size": r.get("size") or r.get("width"),
            "wva": r.get("wva"),
            "hardware": r.get("hardware"),
            "page": r.get("page"),
            "verified": False,
            "why": "；".join(why),
            "source": r.get("source"),
        })
    out.sort(key=lambda x: -x["score"])
    return out[:limit]
