# -*- coding: utf-8 -*-
"""把全库页搬到 app/，并套上 index 的 premium 配色（浅纸色 + 铜色强调）。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"Y:\hks")
src = ROOT / "p2" / "web" / "catalog.html"
html = src.read_text(encoding="utf-8")

OVERRIDE = """
<style>
  /* premium 主题覆盖：浅纸 + 铜色，与 app/index.html 一致 */
  :root{
    --bg:#f2f0eb; --card:#ffffff; --line:#dedddb; --txt:#282827; --dim:#767574;
    --acc:#d38b5d; --ok:#4a7c59; --vio:#a9693c;
  }
  body{font-family:Inter,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--txt)}
  h1{letter-spacing:-.02em}
  .topbar{background:#161615;color:#f4f1ec;border-bottom:1px solid #2a2826}
  .sub,.stat,.src{color:var(--dim)}
  input,select,.btn{background:#fff;border:1px solid var(--line);border-radius:3px;color:var(--txt);font-family:inherit}
  input:focus,select:focus{border-color:var(--acc)}
  .btn:hover{border-color:var(--acc);color:#a9693c}
  table{background:#fff;border:1px solid var(--line);border-radius:3px;overflow:hidden}
  th{background:#e9e6e0;color:#5c5852;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
  th,td{border-bottom:1px solid #eceae5}
  tbody tr:hover{background:#faf9f6}
  .b{border:1px solid #e3d3c4;background:#fdf6f0;color:#a9693c;border-radius:2px}
  .det{background:#faf9f6}
  .kv,.ev{font-size:13px}
  .ev{color:#7d786f;border-top:1px solid #eceae5;font-family:Consolas,monospace}
  .foot{color:var(--dim)}
</style>
</head>"""

html = html.replace("</head>", OVERRIDE, 1)

# 顶部加一条返回首页的链接（P3 的落地页）
bar = ('<div style="max-width:960px;margin:0 auto;padding:14px 16px 0;font-size:13px">'
       '<a href="index.html" style="color:#a9693c;text-decoration:none">&larr; 返回冠英首页</a></div>')
html = html.replace('<div class="wrap">', bar + '<div class="wrap">', 1)

out = ROOT / "app" / "catalog.html"
out.write_text(html, encoding="utf-8")
print("写出", out, "%.1f KB" % (out.stat().st_size / 1024))
print("含返回首页:", "返回冠英首页" in html, "| 含铜色:", "#d38b5d" in html)
