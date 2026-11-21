# -*- coding: utf-8 -*-
"""全库浏览页：217 条 SKU，可搜索、可筛选、可展开看证据、可导出 CSV。"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'Y:\hks')
rows = []
for s in json.loads((ROOT/'data'/'structured'/'skus.json').read_text(encoding='utf-8')):
    pr = s.get('provenance') or {}
    d = s.get('dims') or {}
    ev = (s.get('evidence') or [{}])[0]
    rows.append({
        'id': s['sku_id'], 'name': s.get('fit_name') or '',
        'dims': d.get('raw_text') or '',
        'arc': d.get('arc_mm'), 'w': d.get('width_mm'),
        'th': d.get('thickness_mm'), 'th2': d.get('thickness_alt_mm'),
        'pos': s.get('position') or '', 'mat': s.get('material') or '',
        'cat': s.get('category') or '', 'page': pr.get('source_page'),
        'file': pr.get('source_file') or '', 'snip': ev.get('snippet') or '',
        'ver': bool(pr.get('verified')), 'ocr': pr.get('extractor') == 'rule_ocr',
        'conf': (s.get('extras') or {}).get('ocr_conf')})

HTML = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>冠英 刹车片全库</title><style>
:root{--bg:#0f1115;--card:#171a21;--line:#2a2f3a;--txt:#e8eaf0;--dim:#8b93a7;--acc:#4c8dff;--ok:#39c07a;--warn:#e5a33a;--vio:#b58ce0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.55 -apple-system,'Segoe UI','Microsoft YaHei',sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:16px 16px 80px}
h1{font-size:19px;margin:4px 0 2px}.sub{color:var(--dim);font-size:12.5px;margin-bottom:14px}
.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input,select{background:var(--card);border:1px solid var(--line);border-radius:10px;color:var(--txt);padding:11px 13px;font-size:14.5px;outline:none}
input:focus,select:focus{border-color:var(--acc)}#q{flex:1;min-width:220px}
.t{background:#1d2130;border:1px solid var(--line);color:var(--dim);border-radius:99px;padding:7px 12px;font-size:12.5px;cursor:pointer;user-select:none}
.t.on{background:#12263d;color:#6fb0ff;border-color:#1e3a5c}
.btn{background:var(--card);border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:9px 13px;font-size:13px;cursor:pointer}
.btn:hover{border-color:var(--acc)}
.stat{color:var(--dim);font-size:12.5px;margin:10px 0}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:600;background:#12141a;position:sticky;top:0;z-index:2;cursor:pointer;white-space:nowrap}
tbody tr{cursor:pointer}tbody tr:hover{background:#151922}
td.mono{font-variant-numeric:tabular-nums;white-space:nowrap}.id{font-weight:700}
.b{font-size:10.5px;border-radius:5px;padding:1px 5px;margin-left:5px;white-space:nowrap}
.bv{background:#12321f;color:var(--ok)}.bo{background:#2d2438;color:var(--vio)}
.src{color:#6f7a90;font-size:11.5px}
.det{background:#12151c}.det td{padding:12px 14px}.kv{display:grid;grid-template-columns:88px 1fr;gap:4px 12px;font-size:12.5px}
.k{color:var(--dim)}.ev{color:#8ea0bb;font-size:12.5px;margin-top:8px;border-top:1px dashed var(--line);padding-top:8px}
.empty{color:var(--dim);padding:26px;text-align:center}.foot{color:#5b6478;font-size:11.5px;margin-top:18px;line-height:1.7}
</style></head><body><div class="wrap">
<h1>冠英 刹车片全库</h1>
<div class="sub">全部来自 4 本官方产品册 · 每条带页码 · 点行展开看证据</div>
<div class="bar"><input id="q" placeholder="搜型号 / 适配名 / 尺寸（如 解放、205、J6、14.5）">
<select id="sort"><option value="name">按型号</option><option value="dims">按尺寸</option><option value="page">按页码</option><option value="ver">已核对优先</option></select>
<div class="btn" id="csv">导出 CSV</div></div>
<div class="bar" style="margin-top:9px"><div class="t on" data-f="all">全部</div><div class="t" data-f="ver">已核对</div><div class="t" data-f="ocr">扫描页</div><div class="t" data-f="text">文字层</div><div class="t" data-f="gb">冠隆册</div><div class="t" data-f="ko">kooying 册</div></div>
<div class="stat" id="stat"></div>
<table><thead><tr><th style="width:30%">型号 / 适配名</th><th style="width:24%">尺寸（外弧×宽×厚）</th><th style="width:8%">位置</th><th style="width:8%">材质</th><th>出处</th></tr></thead><tbody id="tb"></tbody></table>
<div class="foot">数据：217 条 = 127 文字层 + 90 扫描图页；49 条已人工核对。<br>报价一律「询价确认」（资料包无价格）；「扫描页」= OCR 识别，未经人工核对的不要当定论。</div>
</div><script>
const ROWS=__ROWS__;let filt='all',kw='',sortBy='name',open=new Set();
const esc=s=>(s==null?'':String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])));
function pass(r){
 if(filt==='ver'&&!r.ver)return false;if(filt==='ocr'&&!r.ocr)return false;if(filt==='text'&&r.ocr)return false;
 if(filt==='gb'&&!(r.file||'').includes('冠隆'))return false;if(filt==='ko'&&!(r.file||'').toLowerCase().includes('kooying'))return false;
 if(!kw)return true;const k=kw.toLowerCase().replace(/\s/g,'');
 return (r.id+' '+r.name+' '+r.dims+' '+(r.mat||'')).toLowerCase().replace(/\s/g,'').includes(k);}
function cmp(a,b){if(sortBy==='name')return a.id.localeCompare(b.id,'zh');
 if(sortBy==='dims')return (a.arc||0)-(b.arc||0)||(a.w||0)-(b.w||0);
 if(sortBy==='page')return (a.file||'').localeCompare(b.file||'')||(a.page||0)-(b.page||0);
 return (b.ver?1:0)-(a.ver?1:0)||a.id.localeCompare(b.id,'zh');}
function detail(r){return '<tr class="det"><td colspan="5"><div class="kv">'+
 '<span class="k">完整名称</span><span>'+esc(r.name||'—')+'</span>'+
 '<span class="k">尺寸原文</span><span class="mono">'+esc(r.dims||'—')+'</span>'+
 '<span class="k">数值</span><span class="mono">'+esc(r.arc)+' × '+esc(r.w)+' × '+esc(r.th)+(r.th2?(' / '+esc(r.th2)):'')+' mm</span>'+
 '<span class="k">材质 / 类型</span><span>'+esc(r.mat||'未知')+' · '+esc(r.cat||'—')+'</span>'+
 '<span class="k">出处</span><span>'+esc(r.file)+' 第 '+esc(r.page)+' 页</span>'+
 '<span class="k">核对状态</span><span>'+(r.ver?'✅ 已人工核对原文':'☐ 未人工核对')+(r.ocr?'（扫描图页 OCR，置信 '+esc(r.conf||'—')+'）':'')+'</span>'+
 '<span class="k">报价</span><span>询价确认（资料包无价格）</span></div>'+
 (r.snip?'<div class="ev">原文：'+esc(r.snip)+'</div>':'')+'</td></tr>';}
function draw(){const list=ROWS.filter(pass).sort(cmp);
 document.getElementById('stat').textContent='共 '+ROWS.length+' 条 ｜ 当前 '+list.length+' 条 ｜ 已核对 '+ROWS.filter(r=>r.ver).length+' ｜ 扫描页 '+ROWS.filter(r=>r.ocr).length;
 document.getElementById('tb').innerHTML = list.length? list.map(r=>'<tr data-id="'+esc(r.id)+'"><td><span class="id">'+esc(r.id)+'</span>'+(r.ver?'<span class="b bv">已核对</span>':'')+(r.ocr?'<span class="b bo">扫描页</span>':'')+'<div class="src">'+esc(r.name||'')+'</div></td><td class="mono">'+esc(r.dims||'—')+'</td><td>'+esc(r.pos||'—')+'</td><td>'+esc(r.mat||'—')+'</td><td class="src">'+esc(r.file)+' p'+esc(r.page)+'</td></tr>'+(open.has(r.id)?detail(r):'')).join('') : '<tr><td colspan="5" class="empty">没有匹配的型号，试试「解放」「205」「J6」</td></tr>';}
document.getElementById('tb').addEventListener('click',e=>{const tr=e.target.closest('tr');if(!tr||!tr.dataset.id)return;
 const id=tr.dataset.id;open.has(id)?open.delete(id):open.add(id);draw();});
document.getElementById('q').addEventListener('input',e=>{kw=e.target.value;draw();});
document.getElementById('sort').addEventListener('change',e=>{sortBy=e.target.value;draw();});
document.querySelectorAll('.t').forEach(t=>t.onclick=()=>{document.querySelectorAll('.t').forEach(x=>x.classList.remove('on'));t.classList.add('on');filt=t.dataset.f;draw();});
document.getElementById('csv').onclick=()=>{const list=ROWS.filter(pass);
 const head=['sku_id','适配名','尺寸','外弧','宽度','厚度','备选厚度','位置','材质','类型','出处册','页码','已核对','扫描页'];
 const lines=[head.join(',')].concat(list.map(r=>[r.id,r.name,r.dims,r.arc,r.w,r.th,r.th2||'',r.pos,r.mat,r.cat,r.file,r.page,r.ver?'是':'否',r.ocr?'是':'否'].map(v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"').join(',')));
 const blob=new Blob([new Uint8Array([239,187,191]),lines.join('\n')],{type:'text/csv;charset=utf-8'});
 const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='冠英全库_'+list.length+'条.csv';a.click();};
draw();</script></body></html>'''

out = ROOT/'p2'/'web'/'catalog.html'
html = HTML.replace('__ROWS__', json.dumps(rows, ensure_ascii=False))
out.write_text(html, encoding='utf-8')
print('写出', out, '%.1f KB' % (out.stat().st_size/1024), '| 条数', len(rows))
