# -*- coding: utf-8 -*-
"""主数据加载 + 检索基础件（BM25，纯标准库）。"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "structured"


def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def load_skus(path=None, include_placeholders=False):
    recs = load_json(path or DATA / "skus.json", [])
    if not include_placeholders:
        recs = [r for r in recs if not r.get("_placeholder")]
    return recs


def load_axles(path=None):
    return load_json(path or DATA / "axles.json", [])


def norm_code(code: str) -> str:
    """编码归一：大写、去掉所有非字母数字。"""
    return re.sub(r"[^A-Za-z0-9]", "", (code or "")).upper()


def sku_text(s: dict) -> str:
    """拼检索文本：型号 + 类别 + 材质 + 车桥 + 编码 + 尺寸原文。"""
    parts = [s.get("sku_id", ""), s.get("fit_name") or "", s.get("part_no") or "",
             s.get("category", ""), s.get("material", ""), s.get("position") or ""]
    d = s.get("dims") or {}
    if d.get("raw_text"):
        parts.append(d["raw_text"])
    for axle in s.get("axle_fit") or []:
        parts += [axle.get("brand", ""), axle.get("model", ""), axle.get("brake_spec") or ""]
    for c in s.get("cross_refs") or []:
        parts += [c.get("code", ""), c.get("brand") or ""]
    parts.append(s.get("stock", ""))
    return " ".join(p for p in parts if p)


def tokenize(text: str):
    text = (text or "").lower()
    words = re.findall(r"[a-z0-9.-]+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    bigrams = ["".join(p) for p in zip(cjk, cjk[1:])]
    return words + bigrams + cjk


class BM25:
    """极简 BM25（k1=1.5, b=0.75），不依赖第三方。"""

    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [tokenize(d) for d in docs]
        self.k1, self.b = k1, b
        self.N = len(self.docs) or 1
        self.avgdl = (sum(len(d) for d in self.docs) / self.N) if self.docs else 0.0
        self.df = {}
        for d in self.docs:
            for t in set(d):
                self.df[t] = self.df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in self.df.items()}

    def scores(self, query: str):
        q = tokenize(query)
        out = []
        for d in self.docs:
            tf = {}
            for t in d:
                tf[t] = tf.get(t, 0) + 1
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                idf = self.idf.get(t, 0.0)
                f = tf[t]
                dl = len(d) or 1
                s += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
            out.append(s)
        return out
