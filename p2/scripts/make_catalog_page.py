# -*- coding: utf-8 -*-
"""全库离线页：把 217 条 SKU 全部烘进一个 HTML，可按名称/尺寸筛，带核对与 OCR 标记。"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"Y:\hks")
rows = json.loads((ROOT / "data" / "structured" / "skus.json").read_text(encoding="utf-8"))
out_rows = []
for s in rows:
    pr = s.get("provenance") or {}
    out_rows.append({
        "id": s["sku_id"],
        "name": s.get("fit_name") or "",
        "dims": (s.get("dims") or {}).get("raw_text") or "",
        "pos": s.get("position") or "",
        "page": pr.get("source_page"),
        "file": pr.get("source_file"),
        "ver": bool(pr.get("verified")),
        "ocr": pr.get("extractor") == "rule_ocr",
        "mat": s.get("material") or "",
    })

page = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>冠英 全库 217 条</title>
<style>
:root{--bg:#0f1115;--card:#171a21;--line:#2a2f3a;--txt:#e8eaf0;--dim:#8b93a7;--acc:#4c8dff;--ok:#39c07a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:16px}
h1{font-size:18px;margin:4px 0 2px}
.sub{color:var(--dim);font-size:12.5px;margin-bottom:12px}
.bar{display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap}
input{flex:1;min-width:200px;background:var(--card);border:1px solid var(--line);border-radius:9px;color:var(--txt);padding:10px 12px;outline:none}
input:focus{border-color:var(--acc)}
.t{background:#1d2130;border:1px solid var(--line);color:var(--dim);border-radius:99px;padding:6px 11px;font-size:12.5px;cursor:pointer}
.t.on{background:#12263d;color:#6fb0ff;border-color:#1e3a5c}
.stat{color:var(--dim);font-size:12.5px;margin:6px 0 10px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:600;position:sticky;top:0;background:#12141a}
td.mono{font-variant-numeric:tabular-nums;white-space:nowrap}
.id{font-weight:700}
.b{font-size:10.5px;border-radius:5px;padding:1px 5px;margin-left:5px;white-space:nowrap}
.bv{background:#12321f;color:var(--ok)}.bo{background:#2d2438;color:#b58ce0}
.src{color:#6f7a90;font-size:11.5px}
.more{color:var(--dim);font-size:12px;margin-top:10px}
</style></head><body><div class="wrap">
<h1>冠英 全库 · 217 条刹车片</h1>
<div class="sub">全部来自 4 本官方产品册，每条带页码；点过滤按钮筛选。</div>
<div class="bar">
  <input id="q" placeholder="搜型号 / 适配名 / 尺寸，例如 解放 / 205 / J6">
  <div class="t on" data-f="all">全部</div>
  <div class="t" data-f="ver">已核对</div>
  <div class="t" data-f="ocr">扫描图页</div>
  <div class="t" data-f="text">文字层</div>
</div>
<div class="stat" id="stat"></div>
<table><thead><tr><th style="width:34%">型号</th><th style="width:26%">尺寸（外弧×宽×厚）</th><th>位置</th><th>出处</th></tr></thead>
<tbody id="tb"></tbody></table>
<div class="more" id="more"></div>
</div>
<script>
const ROWS = __ROWS__;
let filt = "all", kw = "";
const esc = s => (s==null?"":String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])));
function pass(r){
  if (filt==="ver" && !r.ver) return false;
  if (filt==="ocr" && !r.ocr) return false;
  if (filt==="text" && r.ocr) return false;
  if (!kw) return true;
  const k = kw.toLowerCase().replace(/\\s/g,"");
  return (r.id+" "+r.name+" "+r.dims+" "+(r.mat||"")).toLowerCase().replace(/\\s/g,"").includes(k);
}
function draw(){
  const list = ROWS.filter(pass);
  document.getElementById("stat").textContent =
    "共 " + ROWS.length + " 条，当前显示 " + list.length + " 条 · 已核对 " +
    ROWS.filter(r=>r.ver).length + " 条 · 扫描图页 " + ROWS.filter(r=>r.ocr).length + " 条";
  document.getElementById("tb").innerHTML = list.map(r =>
    "<tr><td><span class='id'>"+esc(r.id)+"</span>"+(r.ver?"<span class='b bv'>已核对</span>":"")+
    (r.ocr?"<span class='b bo'>扫描页</span>":"")+"</td>"+
    "<td class='mono'>"+esc(r.dims||"—")+"</td><td>"+esc(r.pos||"—")+"</td>"+
    "<td class='src'>"+esc(r.file||"")+" p"+esc(r.page)+"</td></tr>").join("");
  document.getElementById("more").textContent = list.length===ROWS.length ? "" :
    "（已折叠其余 "+(ROWS.length-list.length)+" 条，清空搜索或点“全部”看全库）";
}
document.getElementById("q").addEventListener("input", e => { kw = e.target.value; draw(); });
document.querySelectorAll(".t").forEach(t => t.onclick = () => {
  document.querySelectorAll(".t").forEach(x => x.classList.remove("on"));
  t.classList.add("on"); filt = t.dataset.f; draw();
});
draw();
</script></body></html>"""
out = ROOT / "p2" / "web" / "catalog_217.html"
out.write_text(page.replace("__ROWS__", json.dumps(out_rows, ensure_ascii=False)), encoding="utf-8")
print("写出", out, "%.1f KB" % (out.stat().st_size / 1024))
print("条数", len(out_rows), "已核对", sum(r["ver"] for r in out_rows), "OCR", sum(r["ocr"] for r in out_rows))
