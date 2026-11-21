# -*- coding: utf-8 -*-
"""生成"离线演示单文件"：把几条真实查询返回烘进 HTML，
P1 双击就能看（不需要 Python、不需要起服务、不需要联网）。"""
import html
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.match import match_query  # noqa: E402

ROOT = Path(r"Y:\hks")
WEB = ROOT / "p2" / "web"

QUERIES = [
    "147×100×14.5",
    "汉德 35 吨桥，前面那副",
    "解放 J6P 后轮要一副",
    "乘龙 H5 前轮的片子",
    "客户要 FMSI 4524",
    "BPW 420X180 的后蹄",
    "斯堪尼亚 后轮",
]

data = {q: match_query(q) for q in QUERIES}
tpl = (WEB / "index.html").read_text(encoding="utf-8")

# 把 fetch 换成本地数据
inject = """
const OFFLINE = %s;
async function run(){
  const q = document.getElementById("q").value.trim();
  const out = document.getElementById("out");
  if (!q) return;
  const hit = OFFLINE[q] || OFFLINE[Object.keys(OFFLINE).find(k => k.replace(/\\s/g,"") === q.replace(/\\s/g,""))];
  if (!hit){
    out.innerHTML = '<div class="card">离线快照里只有这几条，试试下面的示例：<br>' +
      Object.keys(OFFLINE).map(k => '· ' + k).join('<br>') + '</div>';
    return;
  }
  render(hit, 0);
}
""" % json.dumps(data, ensure_ascii=False)

# 去掉原来的 fetch 版 run()
start = tpl.index("async function run(){")
end = tpl.index("function render(j, ms){")
tpl = tpl[:start] + inject + "\n" + tpl[end:]
tpl = tpl.replace('<div class="sub">报车型 / 车桥 / 编码 / 尺寸，3 秒给出 3 个方案，每个都能翻到册子页码</div>',
                  '<div class="sub">离线快照（%d 条真实结果）· 不需要联网 · 双击即可看</div>' % len(QUERIES))
tpl = tpl.replace('fetch("/health").then', 'Promise.resolve({json:()=>({skus:217,axles:7})}).then')
out = WEB / "demo_offline.html"
out.write_text(tpl, encoding="utf-8")
print("写出", out, "%.1f KB" % (out.stat().st_size / 1024))
print("包含查询：")
for q in QUERIES:
    r = data[q]
    print("  %-24s mode=%-6s cand=%d export=%d" % (q, r["mode"], len(r["candidates"]), len(r["export_matches"])))
