import re, shutil
from pathlib import Path

ROOT = Path(r"C:\Users\hhh\Documents\deepseek-harness\default-workspace\Decompiler")

def edit(path, pairs, must=True):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in s:
            print(f"  !! anchor not found in {path}: {old[:60]}")
            if must: continue
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print(f"  ok {path}")

# ---------- 1. site.css 组件 ----------
css_add = """

/* ---------- v3: generated visuals ---------- */
.card .thumb{
  margin:-22px -22px 16px; width:calc(100% + 44px); display:block;
  aspect-ratio:16/9; object-fit:cover; border-radius:16px 16px 0 0;
  filter:saturate(.95) contrast(1.02);
  transition:transform .5s cubic-bezier(.2,.9,.2,1);
}
a.card:hover .thumb{transform:scale(1.03)}
.banner{position:relative;margin:26px 0 4px;border:1px solid var(--line);border-radius:16px;overflow:hidden;background:#05060A}
.banner img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.banner .cap{
  position:absolute;left:14px;bottom:12px;font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;
  color:rgba(255,255,255,.78);background:rgba(7,8,11,.55);border:1px solid rgba(255,255,255,.12);
  padding:4px 9px;border-radius:6px;backdrop-filter:blur(6px)
}
.banner:after{content:"";position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(to top,rgba(7,8,11,.55),transparent 42%)}
@media(max-width:760px){.banner img{aspect-ratio:16/10}}
"""
css = ROOT / "assets/site.css"
css.write_text(css.read_text(encoding="utf-8") + css_add, encoding="utf-8")
print("ok assets/site.css")

# ---------- 2. 档案库卡片缩略图 ----------
arch = (ROOT / "archive/index.html").read_text(encoding="utf-8")
thumbs = {
    "xiaohongshu.html": "a01_xhs",
    "gacha.html": "a02_gacha",
    "douyin.html": "a03_douyin",
    "duolingo.html": "a04_duolingo",
    "pinduoduo.html": "a05_pdd",
    "xianyu.html": "a06_xianyu",
}
for fname, img in thumbs.items():
    old = f'<a class="card" href="{fname}"'
    new = f'<a class="card" href="{fname}"'
    if old not in arch:
        print("  !! card anchor missing:", fname); continue
    # 在开标签后插入缩略图
    idx = arch.index(old)
    end = arch.index(">", idx) + 1
    arch = arch[:end] + f'\n      <img class="thumb" src="../assets/img/{img}.jpg" alt="" loading="lazy">' + arch[end:]
(ROOT / "archive/index.html").write_text(arch, encoding="utf-8")
print("ok archive/index.html")

# ---------- 3. 各档案页 banner ----------
banners = {
    "archive/xiaohongshu.html": ("a01_xhs", "A-01 · 生成式视觉", "../assets/img/"),
    "archive/gacha.html":       ("a02_gacha", "A-02 · 生成式视觉", "../assets/img/"),
    "archive/douyin.html":      ("a03_douyin", "A-03 · 生成式视觉", "../assets/img/"),
    "archive/duolingo.html":    ("a04_duolingo", "A-04 · 生成式视觉", "../assets/img/"),
    "archive/pinduoduo.html":   ("a05_pdd", "A-05 · 生成式视觉", "../assets/img/"),
    "archive/xianyu.html":      ("a06_xianyu", "A-06 · 生成式视觉", "../assets/img/"),
    "method.html":              ("method_anatomy", "方法 · 生成式视觉", "assets/img/"),
    "devices/index.html":       ("devices_field", "装置库 · 生成式视觉", "../assets/img/"),
}
for path, (img, cap, pre) in banners.items():
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    m = re.search(r'(\n\s*<div class="crumb">.*?</div>\n)', s, re.S)
    if not m:
        print("  !! crumb not found:", path); continue
    banner = (f'\n  <figure class="banner reveal">\n'
              f'    <img src="{pre}{img}.jpg" alt="" loading="lazy">\n'
              f'    <figcaption class="cap">{cap}</figcaption>\n'
              f'  </figure>\n')
    s = s[:m.end()] + banner + s[m.end():]
    p.write_text(s, encoding="utf-8")
    print("  ok", path)

# ---------- 4. 主页：概念片 ----------
lab = ROOT / "index.html"
s = lab.read_text(encoding="utf-8")
film_css = """
/* ---------- concept film ---------- */
.film{position:relative;border:1px solid var(--line2);border-radius:18px;overflow:hidden;background:#05060A;margin:8px 0 4px}
.film video{width:100%;display:block;aspect-ratio:16/9;object-fit:cover;background:#05060A}
.film .play{
  position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;
  cursor:pointer;background:radial-gradient(circle at 50% 50%,rgba(5,6,10,.15),rgba(5,6,10,.55));transition:.25s;
}
.film .play:hover{background:radial-gradient(circle at 50% 50%,rgba(5,6,10,.05),rgba(5,6,10,.45))}
.film .play b{
  width:74px;height:74px;border-radius:50%;display:grid;place-items:center;font-size:22px;color:#0A0C08;
  background:radial-gradient(circle at 50% 36%,#E2FF9E,#B8FF3C 44%,#84C617 76%,#4E7A05);
  box-shadow:0 10px 30px rgba(184,255,60,.25),inset 0 2px 6px rgba(255,255,255,.7);
}
.film .play em{font-style:normal;font-family:var(--mono);font-size:10px;letter-spacing:.18em;color:rgba(255,255,255,.7)}
.film.playing .play{display:none}
"""
s = s.replace("/* ---------- arcade key ---------- */", film_css + "\n/* ---------- arcade key ---------- */", 1)

film_html = """  <div class="sec-head reveal">
    <span class="no">00.5</span><h2>概念片 · 5 秒</h2>
    <span class="hint">generated video · 点击播放</span>
  </div>

  <div class="film reveal" id="film">
    <video id="filmVideo" src="assets/video/hero.mp4" poster="assets/img/method_anatomy.jpg" preload="none" muted loop playsinline></video>
    <div class="play" onclick="playFilm()">
      <b>▶</b><em>DECOMPILE · 5s</em>
    </div>
  </div>

"""
anchor = '  <div class="sec-head reveal">\n    <span class="no">01–05</span>'
if anchor in s:
    s = s.replace(anchor, film_html + anchor, 1)
    print("ok film section inserted")
else:
    print("!! film anchor missing")

# 播放脚本
js = """
function playFilm(){
  const f = document.getElementById('film'), v = document.getElementById('filmVideo');
  if(!v) return;
  f.classList.add('playing');
  v.preload = 'auto';
  v.play().catch(()=>{ f.classList.remove('playing'); flash('浏览器拦截了自动播放，请再点一次'); });
}
"""
s = s.replace("/* ---------- 街机实体键", js + "\n/* ---------- 街机实体键", 1)
lab.write_text(s, encoding="utf-8")
print("ok index.html")

print("done")
