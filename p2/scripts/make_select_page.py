# -*- coding: utf-8 -*-
"""选型查询页（只做"查"，全库浏览在 catalog.html）。"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.match import match_query
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'Y:\hks')
QUERIES = ['147×100×14.5', '汉德 35 吨桥，前面那副', '解放 J6P 后轮要一副',
           '乘龙 H5 前轮的片子', '客户要 FMSI 4524', 'BPW 420X180 的后蹄', '斯堪尼亚 后轮']
snap = {q: match_query(q) for q in QUERIES}

HTML = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>冠英 SELECT</title><style>
:root{--bg:#0f1115;--card:#171a21;--line:#2a2f3a;--txt:#e8eaf0;--dim:#8b93a7;--acc:#4c8dff;--ok:#39c07a;--warn:#e5a33a;--vio:#b58ce0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:14.5px/1.55 -apple-system,'Segoe UI','Microsoft YaHei',sans-serif}
.wrap{max-width:470px;margin:0 auto;padding:18px 16px 60px}
h1{font-size:19px;margin:6px 0 2px}.sub{color:var(--dim);font-size:12.5px;margin-bottom:16px}
.search{display:flex;gap:8px}input{flex:1;background:var(--card);border:1px solid var(--line);border-radius:10px;color:var(--txt);padding:12px 13px;font-size:15px;outline:none}
input:focus{border-color:var(--acc)}button{background:var(--acc);border:0;border-radius:10px;color:#fff;padding:12px 18px;font-size:15px;font-weight:600;cursor:pointer}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:10px 0 14px}
.chip{background:#1d2130;border:1px solid var(--line);color:var(--dim);border-radius:99px;padding:6px 11px;font-size:12.5px;cursor:pointer}
.chip:hover{color:var(--txt)}.meta{display:flex;gap:8px;align-items:center;margin:12px 0 10px;font-size:12.5px;color:var(--dim)}
.badge{border-radius:6px;padding:2px 7px;font-size:11.5px;font-weight:600}
.b-rule{background:#12321f;color:var(--ok)}.b-ask{background:#3a2a12;color:var(--warn)}.b-export{background:#12263d;color:#6fb0ff}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 14px;margin-bottom:10px}
.row1{display:flex;justify-content:space-between;align-items:baseline;gap:8px}.sku{font-size:15.5px;font-weight:700}
.conf{font-size:12px;border-radius:6px;padding:2px 7px}.c-高{background:#12321f;color:var(--ok)}.c-中{background:#3a2a12;color:var(--warn)}.c-低{background:#2a2f3a;color:var(--dim)}
.dims{color:#b9c3d6;font-size:13.5px;margin-top:3px}.reason{color:var(--dim);font-size:12.5px;margin-top:7px}
.ev{color:#6f7a90;font-size:12px;margin-top:6px;border-top:1px dashed var(--line);padding-top:6px}
.flags{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}.f{font-size:11px;border-radius:5px;padding:2px 6px;background:#232838;color:#9fb0cc}
.f-o{background:#2d2438;color:var(--vio)}
.ask{background:#241d12;border-color:#4a3a1c}.ask h3{margin:0 0 8px;font-size:13.5px;color:var(--warn)}.ask li{font-size:13.5px;margin:5px 0}
.exp{background:#101c2b;border-color:#1e3a5c}.exp h3{margin:0 0 8px;font-size:13.5px;color:#6fb0ff}
.kv{display:grid;grid-template-columns:70px 1fr;gap:3px 10px;font-size:12.5px;margin-top:6px}.k{color:var(--dim)}
.foot{color:#5b6478;font-size:11.5px;margin-top:20px;line-height:1.8}a{color:#6fb0ff;text-decoration:none}
</style></head><body><div class="wrap">
<h1>冠英 SELECT</h1><div class="sub">报车型 / 车桥 / 编码 / 三个尺寸，3 秒给出 3 个方案，每个带册子页码</div>
<div class="search"><input id="q" placeholder="例：汉德 35 吨桥，前面那副" autocomplete="off"><button id="go">查</button></div>
<div class="chips" id="chips"></div><div id="out"></div>
<div class="foot" id="st">连接中…</div>
<div class="foot">全库 217 条浏览 → <a href="catalog.html">打开全库页</a></div>
</div><script>
const SNAP=__SNAP__;const MODE={rule:'按资料直出',ask:'信息不足 · 追问',export:'海外对码'};
const esc=s=>(s==null?'':String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])));
const chips=document.getElementById('chips');
Object.keys(SNAP).forEach(t=>{const b=document.createElement('div');b.className='chip';b.textContent=t;b.onclick=()=>{document.getElementById('q').value=t;run();};chips.appendChild(b);});
let ONLINE=false;
fetch('/health').then(r=>r.json()).then(j=>{ONLINE=true;document.getElementById('st').textContent='实时接口在线：'+j.skus+' 条型号 · '+j.axles+' 个车桥';}).catch(()=>{document.getElementById('st').textContent='离线快照模式（'+Object.keys(SNAP).length+' 条示例结果）';});
async function run(){const q=document.getElementById('q').value.trim();if(!q)return;const out=document.getElementById('out');
 if(ONLINE){try{const t0=performance.now();const r=await fetch('/match?q='+encodeURIComponent(q));const j=await r.json();render(j,Math.round(performance.now()-t0));return;}catch(e){}}
 const hit=SNAP[q]||SNAP[Object.keys(SNAP).find(k=>k.replace(/\s/g,'')===q.replace(/\s/g,''))];
 if(!hit){out.innerHTML='<div class="card">离线快照里只有这 '+Object.keys(SNAP).length+' 条；要查任意型号请起本地服务。</div>';return;}
 render(hit,-1);}
function render(j,ms){const out=document.getElementById('out');let h='';const m=j.mode||'ask';
 h+='<div class="meta"><span class="badge b-'+m+'">'+(MODE[m]||m)+'</span><span>'+(ms>=0?j.elapsed_ms+' ms（含网络 '+ms+' ms）':'离线快照 · 引擎实测 '+j.elapsed_ms+' ms')+'</span></div>';
 (j.candidates||[]).forEach(c=>{h+='<div class="card"><div class="row1"><span class="sku">'+esc(c.sku_id)+'</span><span class="conf c-'+esc(c.confidence)+'">'+esc(c.confidence)+'</span></div>';
 h+='<div class="dims">'+esc((c.dims||{}).raw_text||'—')+'</div><div class="reason">'+esc(c.reason)+'</div>';
 const ev=(c.evidence||[])[0];if(ev)h+='<div class="ev">出处：'+esc(ev.report_id)+' 第 '+esc(ev.page)+' 页 · '+esc(ev.snippet||'')+'</div>';
 let f='';if(c.ocr)f+='<span class="f f-o">扫描图页识别</span>';f+='<span class="f">报价：询价确认</span>';
 h+='<div class="flags">'+f+'</div></div>';});
 (j.export_matches||[]).forEach(e=>{h+='<div class="card exp"><h3>海外对码 · '+esc(e.kind).toUpperCase()+'</h3>';
 h+='<div class="row1"><span class="sku">'+esc(e.shoe_code)+'</span><span class="conf c-中">p'+esc(e.page)+'</span></div><div class="kv">';
 if(e.fmsi)h+='<span class="k">FMSI</span><span>'+esc(e.fmsi)+'</span>';if(e.size)h+='<span class="k">尺寸</span><span>'+esc(e.size)+'</span>';
 if(e.oe_ref)h+='<span class="k">OE 号</span><span>'+esc(e.oe_ref)+'</span>';if(e.wva)h+='<span class="k">WVA</span><span>'+esc(e.wva)+'</span>';
 if(e.hardware)h+='<span class="k">硬件包</span><span>'+esc(e.hardware)+'</span>';h+='<span class="k">依据</span><span>'+esc(e.why)+'</span></div></div>';});
 if((j.followups||[]).length){h+='<div class="card ask"><h3>需要确认（不猜）</h3><ul>';j.followups.forEach(q=>h+='<li>'+esc(q)+'</li>');h+='</ul></div>';}
 if(!(j.candidates||[]).length&&!(j.export_matches||[]).length&&!(j.followups||[]).length)h+='<div class="card">没查到，换个说法（车型+位置，或量三个尺寸）</div>';
 out.innerHTML=h;}
document.getElementById('go').onclick=run;document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')run();});
</script></body></html>'''

out = ROOT/'p2'/'web'/'select.html'
out.write_text(HTML.replace('__SNAP__', json.dumps(snap, ensure_ascii=False)), encoding='utf-8')
print('写出', out, '%.1f KB' % (out.stat().st_size/1024), '| 快照', len(snap))
