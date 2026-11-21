# -*- coding: utf-8 -*-
"""匹配引擎：规则优先 → BM25 召回 → (可选) LLM 消歧与追问。

原则（写入代码，不靠自觉）：
  1. 候选只来自主数据表，绝不生成表外型号；
  2. 信号不足时返回追问，不给"看起来对"的答案；
  3. 无 LLM key 也能跑（纯规则模式），保证演示断网可用。

CLI:
    python -m engine.match --query "BPW ECO Plus 420x200" --demo-data
    python -m engine.match --query "2019 Hilux 后桥换过"
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.store import BM25, load_axles, load_skus, norm_code, sku_text

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TOP_N = 3
TOL_DIA_MM = 1.5
TOL_WIDTH_MM = 2.0
TOL_THICK_MM = 0.6

DIM_RE = re.compile(
    r"(?<![\d.])(\d{2,4})\s*(?:x|X|×|\*)\s*(\d{2,4})(?:\s*(?:x|X|×|\*)\s*(\d{1,2}(?:\.\d)?))?"
)
DIA_WORD_RE = re.compile(r"(?:鼓径|外径|直径)\D{0,6}?(\d{2,4})")
CODE_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9][A-Za-z0-9\-]{5,}(?![A-Za-z0-9])")

CAR_MODELS = [
    "hilux", "海拉克斯", "卡罗拉", "corolla", "普拉多", "prado", "兰德酷路泽", "land cruiser",
    "toyota", "丰田", "hino", "日野", "isuzu", "五十铃", "mitsubishi", "三菱",
    "volvo", "沃尔沃", "scania", "斯堪尼亚", "man", "曼恩", "benz", "奔驰", "actros",
    "iveco", "依维柯", "daf", "达夫", "renault", "雷诺",
    "解放", "东风", "重汽", "陕汽", "欧曼", "红岩", "江淮",
]


def parse_query(text: str, axles: list) -> dict:
    """从自由文本里抽实体（纯规则，不依赖网络）。"""
    low = text.lower()
    # 产品册口径：宽×长×厚(/备选厚)。鼓径(外径)仅用于鼓体类产品，可选。
    # 产品册口径（表头原文）：外弧 × 宽度 × 厚度 = outer arch / width / thickness
    dims = {"arc_mm": None, "width_mm": None, "thickness_mm": None,
            "thickness_alt_mm": None, "outer_dia_mm": None, "raw_text": None}
    m = DIM_RE.search(text)
    if m:
        dims["arc_mm"] = float(m.group(1))
        dims["width_mm"] = float(m.group(2))
        dims["thickness_mm"] = float(m.group(3)) if m.group(3) else None
        dims["raw_text"] = m.group(0).strip()
        alt = re.search(r"/\s*([\d.]+)", m.group(0))
        dims["thickness_alt_mm"] = float(alt.group(1)) if alt else None
    else:
        m2 = DIA_WORD_RE.search(text)
        if m2:
            dims["outer_dia_mm"] = float(m2.group(1))
            dims["raw_text"] = m2.group(0).strip()

    dim_like = re.compile(r"\d+\s*[xX×*]\s*\d+(?:\s*[xX×*]\s*\d+)*")
    codes = [c for c in CODE_RE.findall(text) if not c.isdigit() and not dim_like.fullmatch(c)]
    # 归一化查询：去空格/标点，"35 吨"→"35T"，这样"汉德 35 吨桥"能对上车桥别名"汉德35T"
    qk = re.sub(PUNCT_RE, "", text).upper().replace("吨", "T")
    axle_hits = []
    for a in axles:
        keys = list(a.get("aliases") or []) + [a.get("model", ""), a.get("axle_id", "")]
        for k in keys:
            if not k or len(k) < 3:
                continue
            if re.sub(PUNCT_RE, "", k).upper().replace("吨", "T") in qk:
                axle_hits.append(a)
                break
        else:
            if a.get("brand") and a["brand"].lower() in low and len(axle_hits) < 3:
                axle_hits.append(a)
    car = [c for c in CAR_MODELS if c in low]

    return {
        "dims": dims,
        "has_dims": dims["arc_mm"] is not None or dims["outer_dia_mm"] is not None,
        "codes": codes,
        "norm_codes": [norm_code(c) for c in codes],
        "axles": [{"axle_id": a.get("axle_id"), "brand": a.get("brand"), "model": a.get("model")} for a in axle_hits],
        "car_models": car,
    }


def _dims_hit(sku: dict, d: dict) -> bool:
    """宽/长/厚三项，能比的都必须在容差内；至少要比到两项才敢判命中。"""
    sd = sku.get("dims") or {}
    checked = 0
    for key in ("arc_mm", "width_mm", "thickness_mm"):
        q, v = d.get(key), sd.get(key)
        if q is None or v is None:
            continue
        tol = TOL_WIDTH_MM if key != "thickness_mm" else TOL_THICK_MM
        if abs(float(v) - float(q)) > tol:
            return False
        checked += 1
    if checked >= 2:
        return True
    # 只剩鼓径可比
    if d.get("outer_dia_mm") is not None and sd.get("outer_dia_mm") is not None:
        return abs(float(sd["outer_dia_mm"]) - float(d["outer_dia_mm"])) <= TOL_DIA_MM
    return False


def _code_hit(sku: dict, norm_codes: list) -> str | None:
    for ref in sku.get("cross_refs") or []:
        if norm_code(ref.get("code", "")) in norm_codes:
            return ref.get("code")
    return None


def _axle_hit(sku: dict, axle_hits: list) -> str | None:
    for ax in axle_hits:
        for fit in sku.get("axle_fit") or []:
            same_brand = (fit.get("brand") or "").lower() == (ax.get("brand") or "").lower()
            same_model = (ax.get("model") or "") and ax["model"].lower() in (fit.get("model") or "").lower()
            if same_brand and (same_model or not ax.get("model")):
                return "%s %s" % (fit.get("brand"), fit.get("model"))
    return None


def _confidence(score: float, hard_hit: bool) -> str:
    if hard_hit and score >= 0.7:
        return "高"
    if score >= 0.45:
        return "中"
    return "低"


def _followups(parsed: dict, best: float) -> list:
    q = []
    if parsed["has_dims"]:
        d = parsed["dims"]
        missing = [k for k in ("arc_mm", "width_mm", "thickness_mm") if d.get(k) is None]
        if missing:
            q.append("能补一下旧片的宽/长/厚吗？（差 2mm 就会串型号）")
    else:
        q.append("车桥铭牌上的品牌与型号是什么？（如 BPW ECO Plus、富华 FUWA 13T）")
    if not parsed["codes"]:
        q.append("旧刹车片背面有没有印编码？或者旧包装上的号？")
    if parsed["car_models"] and not parsed["axles"] and not parsed["has_dims"]:
        q.append("这台车的后桥是否更换过？换过的话按现桥匹配，不按车型。")
    if best < 0.45 and len(q) < 2:
        q.append("现场能量一下旧片的宽×长×厚吗？这是最硬的判据。")
    return q[:3]


PUNCT_RE = "[" + chr(92) + "s，。、,.！!？?]"


def name_keys(name: str) -> set:
    """适配名归一：去空格/标点，'吨'→'T'，并给出"去桥字"变体。
       客户嘴里是"汉德 35 吨桥"，产品册写"汉德桥35T前"，必须能对上。"""
    n = re.sub(PUNCT_RE, "", (name or "")).upper().replace("吨", "T")
    keys = {n}
    if "桥" in n:
        keys.add(n.replace("桥", ""))
    if "T" in n:
        keys.add(n.replace("T", "吨"))
    return {k for k in keys if len(k) >= 4}


def _bigrams(s: str) -> set:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _name_hit(sku: dict, qkey: str) -> str | None:
    """先试子串；不中就用字符二元组覆盖率（容忍"汉德 35 吨桥"与"汉德桥35T前"的语序差异）。"""
    qb = None
    best, best_k = 0.0, None
    for k in name_keys(sku.get("fit_name") or ""):
        if k in qkey:
            return k
        if qb is None:
            qb = _bigrams(qkey)
        kb = _bigrams(k)
        if not kb:
            continue
        r = len(kb & qb) / len(kb)
        if r > best:
            best, best_k = r, k
    return best_k if best >= 0.75 else None


def _dims_err(sku: dict, d: dict) -> float:
    """尺寸偏差（归一化到各自容差），用于同分时的排序：越准越靠前。"""
    sd = sku.get("dims") or {}
    err = 0.0
    for key, tol in (("arc_mm", TOL_DIA_MM), ("width_mm", TOL_WIDTH_MM), ("thickness_mm", TOL_THICK_MM)):
        q, v = d.get(key), sd.get(key)
        if q is not None and v is not None:
            err += abs(float(v) - float(q)) / tol
    return round(err, 3)


def _reason(sku: dict, tags: list, parsed: dict) -> str:
    d = sku.get("dims") or {}
    dim_txt = d.get("raw_text") or ""
    head = "；".join(tags) if tags else "文本相似"
    pos = sku.get("position") or ""
    abs_ = "ABS" if sku.get("abs") else ""
    tail = " ".join(x for x in [sku.get("fit_name") or "", pos, abs_, dim_txt, sku.get("material") or ""] if x and x != "未知")
    return ("%s。%s" % (head, tail)).strip()


def match_query(query: str, skus=None, axles=None, top: int = TOP_N,
                use_llm: bool = False, include_placeholders: bool = False) -> dict:
    t0 = time.time()
    if skus is None:
        skus = load_skus(include_placeholders=include_placeholders)
    if axles is None:
        axles = load_axles()
    parsed = parse_query(query, axles)

    bm25 = BM25([sku_text(s) for s in skus]) if skus else None
    bm_scores = bm25.scores(query) if bm25 else [0.0] * len(skus)
    bm_max = max(bm_scores) if bm_scores else 0.0
    # BM25 归一化后"最高分永远是 1.0"，单靠它会给出假候选；
    # 必须叠加"查询词在文档中的覆盖率"，否则"帮我配刹车片"也会命中。
    from engine.store import tokenize
    q_tokens = set(tokenize(query))
    coverages = []
    for s in skus:
        if not q_tokens:
            coverages.append(0.0)
            continue
        hit = q_tokens & set(tokenize(sku_text(s)))
        coverages.append(len(hit) / len(q_tokens))

    scored = []
    qkey = re.sub(r"[\s，。、,.！!？?]", "", query).upper().replace("吨", "T")
    for sku, bs, cov in zip(skus, bm_scores, coverages):
        tags, comps = [], []
        hit = _name_hit(sku, qkey)
        if hit:
            tags.append("适配名命中 %s" % hit)
            comps.append(0.9)
        dim_err = 99.0
        if parsed["has_dims"] and _dims_hit(sku, parsed["dims"]):
            tags.append("尺寸硬匹配")
            comps.append(1.0)
            dim_err = _dims_err(sku, parsed["dims"])
        code = _code_hit(sku, parsed["norm_codes"]) if parsed["norm_codes"] else None
        if code:
            tags.append("编码 %s 命中" % code)
            comps.append(1.0)
        ax = _axle_hit(sku, parsed["axles"]) if parsed["axles"] else None
        if ax:
            tags.append("适配车桥 %s" % ax)
            comps.append(0.75)
        text_s = (bs / bm_max) * cov if bm_max > 0 else 0.0
        if text_s > 0.12 and cov >= 0.34:
            comps.append(text_s * 0.55)
        if not comps:
            continue
        score = min(1.0, max(comps) + 0.15 * (sum(comps) - max(comps)))
        # 前后位偏好："前面那副"要压过同名的"后"
        pos = sku.get("position") or ""
        if pos in ("前", "后"):
            if pos in qkey:
                score = min(1.0, score + 0.03)
            elif any(p in qkey for p in ("前", "后")):
                score -= 0.03
        if parsed["has_dims"] and dim_err != 99.0:
            score = min(1.0, score + 0.05 / (1.0 + dim_err))
        hard = bool({"尺寸硬匹配"} & set(tags)) or any(t.startswith("编码") for t in tags)
        scored.append({
            "sku_id": sku.get("sku_id"),
            "score": round(score, 3),
            "dims_err": dim_err,
            "confidence": _confidence(score, hard),
            "reason": _reason(sku, tags, parsed),
            "dims": sku.get("dims"),
            "material": sku.get("material"),
            "category": sku.get("category"),
            "axle_fit": sku.get("axle_fit"),
            "evidence": sku.get("evidence"),
            "price": sku.get("price"),
            "stock": sku.get("stock"),
            "placeholder": bool(sku.get("_placeholder")),
        })

    scored.sort(key=lambda x: (-x["score"], x.get("dims_err", 99)))
    top_hits = scored[:top]
    best = top_hits[0]["score"] if top_hits else 0.0

    # 同分多候选（典型：同尺寸不同材质）→ 降置信 + 追问。宁缺勿假：不替客户选材质。
    followups = [] if best >= 0.45 else _followups(parsed, best)
    if len(top_hits) >= 2 and best - top_hits[1]["score"] <= 0.05:
        mats = {c["material"] for c in top_hits[:2] if c.get("material")}
        if len(mats) > 1 and not any((m or "") in query for m in mats):
            for c in top_hits:
                if c["confidence"] == "高":
                    c["confidence"] = "中"
            followups = ["同尺寸有多个材质（%s），客户要哪一种？" % " / ".join(sorted(mats))] + followups

    result = {
        "query": query,
        "parsed": parsed,
        "mode": "rule",
        "candidates": top_hits if best >= 0.3 else [],
        "followups": followups[:3],
        "elapsed_ms": int((time.time() - t0) * 1000),
    }
    if not result["candidates"]:
        result["mode"] = "ask"

    if use_llm and result["candidates"]:
        result = _llm_refine(query, result, use_llm=True)
    return result


LLM_SYSTEM = """你是冠英刹车片的型号匹配助手。候选型号来自冠英主数据表，你只能在其中挑选，
绝对不允许创造表中没有的型号。若证据不足以区分，就少给候选并生成追问。
只输出 JSON，字段：{"picked":[{"sku_id":"","confidence":"高|中|低","reason":"一句话中文差异说明"}],
"followups":["最多3个中文追问"],"note":"可选一句风险提示"}"""


def _llm_refine(query: str, result: dict, use_llm: bool = False) -> dict:
    try:
        from engine.llm import json_call
    except Exception:
        return result
    brief = [
        {"sku_id": c["sku_id"], "dims": c["dims"], "material": c["material"],
         "axle_fit": c["axle_fit"], "reason_rule": c["reason"]}
        for c in result["candidates"][:6]
    ]
    msg = [{"role": "user", "content": json.dumps(
        {"query": query, "parsed": result["parsed"], "candidates": brief},
        ensure_ascii=False)}]
    try:
        out = json_call(msg, system=LLM_SYSTEM, max_tokens=700)
    except Exception as e:  # 网络挂了就降级，绝不让演示挂
        result["mode"] = "rule(llm_unavailable: %s)" % type(e).__name__
        return result

    allow = {c["sku_id"]: c for c in result["candidates"]}
    picked = []
    for p in (out.get("picked") or [])[:TOP_N]:
        sid = p.get("sku_id")
        if sid in allow:
            c = dict(allow[sid])
            c["confidence"] = p.get("confidence") or c["confidence"]
            c["reason"] = p.get("reason") or c["reason"]
            picked.append(c)
    if picked:
        result["candidates"] = picked
    if out.get("followups"):
        result["followups"] = out["followups"][:3]
    if out.get("note"):
        result["note"] = out["note"]
    result["mode"] = "llm"
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="冠英刹车片型号匹配引擎")
    ap.add_argument("--query", required=True)
    ap.add_argument("--top", type=int, default=TOP_N)
    ap.add_argument("--llm", action="store_true", help="启用 LLM 消歧（需 GTM_HACK_API_KEY）")
    ap.add_argument("--demo-data", action="store_true", help="允许使用 _placeholder 占位数据")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = ap.parse_args(argv)

    res = match_query(args.query, top=args.top, use_llm=args.llm,
                      include_placeholders=args.demo_data)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print("Q: %s" % res["query"])
    print("解析: dims=%s codes=%s axle=%s car=%s" % (
        res["parsed"]["dims"]["raw_text"], res["parsed"]["codes"],
        [a["axle_id"] for a in res["parsed"]["axles"]], res["parsed"]["car_models"]))
    print("模式: %s  (%d ms)" % (res["mode"], res["elapsed_ms"]))
    if not res["candidates"]:
        print("\n[无可靠候选 —— 按红线只追问，不瞎配]")
    for i, c in enumerate(res["candidates"], 1):
        print("\n%d. %s  [%s]  score=%s" % (i, c["sku_id"], c["confidence"], c["score"]))
        print("   %s" % c["reason"])
        if c["evidence"]:
            for e in c["evidence"]:
                print("   证据: %s 第 %s 页  %s" % (e.get("report_id"), e.get("page"), e.get("snippet", "")))
        if c["price"]:
            print("   参考价: %s  MOQ=%s" % (c["price"].get("range_cny"), c["price"].get("moq")))
    if res["followups"]:
        print("\n追问:")
        for q in res["followups"]:
            print(" - %s" % q)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
