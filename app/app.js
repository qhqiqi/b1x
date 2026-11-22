/* =========================================================
   冠英 GUANYING — 交互逻辑
   1) 产品映射库（演示数据，接入产品目录后替换 fetch）
   2) 选型匹配（车型 / 车桥 / 尺寸 / 旧片）
   3) 询价清单 + 表单提交（前端模拟）
   ========================================================= */

/* ---------- 1. 演示数据 ----------
   真实环境：GET /api/products 返回产品目录 + 车桥适配 + 报告编号
   字段说明：
   code   冠英自有编码（不依赖 OE 号）
   type   鼓式 / 盘式 / 风电
   size   摩擦面尺寸（mm）
   axles  适配车桥
   cars   适配车型（后市场常见写法）
   mat    材质
   mu     摩擦系数
   temp   工作温度
   moq    最小起订
   lead   交期
*/
const PRODUCTS = [
  { code: 'GY-D420-180', type: '鼓式', size: 'Φ420×180', axles: ['457 桥', '485 桥'], cars: ['解放 J6', '豪沃 T7H', '欧曼 GTL'], mat: '半金属', mu: '0.38', temp: '-40~650 ℃', moq: '100 套', lead: '15 天' },
  { code: 'GY-D410-220', type: '鼓式', size: 'Φ410×220', axles: ['13T 桥', '16T 桥'], cars: ['豪沃 T7H', '德龙 X3000'], mat: '低金属', mu: '0.37', temp: '-40~650 ℃', moq: '100 套', lead: '15 天' },
  { code: 'GY-D440-200', type: '鼓式', size: 'Φ440×200', axles: ['奔驰桥', '斯太尔桥'], cars: ['Actros', '斯太尔'], mat: '半金属', mu: '0.39', temp: '-40~700 ℃', moq: '80 套', lead: '18 天' },
  { code: 'GY-D360-160', type: '鼓式', size: 'Φ360×160', axles: ['富华桥', 'BPW 桥'], cars: ['挂车', '半挂车'], mat: '低金属', mu: '0.36', temp: '-40~600 ℃', moq: '200 套', lead: '12 天' },
  { code: 'GY-P290-44', type: '盘式', size: '290×44', axles: ['前桥'], cars: ['欧曼 EST', '杰狮 C500'], mat: '低金属', mu: '0.41', temp: '-40~700 ℃', moq: '100 套', lead: '18 天' },
  { code: 'GY-P330-45', type: '盘式', size: '330×45', axles: ['前桥'], cars: ['解放 J7', '汕德卡 C7H'], mat: '低金属', mu: '0.42', temp: '-40~700 ℃', moq: '100 套', lead: '20 天' },
  { code: 'GY-P258-40', type: '盘式', size: '258×40', axles: ['轻卡前桥'], cars: ['江铃 凯运', '福田 奥铃'], mat: '陶瓷', mu: '0.40', temp: '-40~650 ℃', moq: '200 套', lead: '15 天' },
  { code: 'GY-P376-45', type: '盘式', size: '376×45', axles: ['奔驰桥'], cars: ['Actros', 'Arocs'], mat: '低金属', mu: '0.41', temp: '-40~700 ℃', moq: '80 套', lead: '20 天' },
  { code: 'GY-W320-40', type: '风电', size: '320×40', axles: ['主轴制动'], cars: ['风机主轴'], mat: '复合纤维', mu: '0.35', temp: '-40~500 ℃', moq: '50 套', lead: '25 天' },
  { code: 'GY-W420-50', type: '风电', size: '420×50', axles: ['偏航制动'], cars: ['风机偏航'], mat: '复合纤维', mu: '0.34', temp: '-40~500 ℃', moq: '50 套', lead: '25 天' }
];

const CHIPS = {
  vehicle: ['解放 J6', '豪沃 T7H', '欧曼 GTL', '德龙 X3000', 'Actros', '解放 J7'],
  axle: ['457 桥', '485 桥', '13T 桥', '富华桥', '奔驰桥'],
  size: ['Φ420×180', 'Φ410×220', '290×44', '330×45', '320×40'],
  photo: []
};

const PLACEHOLDER = {
  vehicle: '例如：解放 J6 / 豪沃 T7H / Actros',
  axle: '例如：457 桥 / 13T 桥 / 富华桥',
  size: '例如：420×180 / 290 44',
  photo: '拍照或输入旧片上的任何编号'
};

/* ---------- 2. 选型匹配 ---------- */

const state = { mode: 'vehicle', query: '', expanded: false };

const el = {
  results: document.getElementById('results'),
  count: document.getElementById('resultCount'),
  chips: document.getElementById('chips'),
  input: document.getElementById('q'),
  hint: document.getElementById('searchHint'),
  tabs: Array.from(document.querySelectorAll('.tab'))
};

const normalize = (s) => String(s)
  .toLowerCase()
  .replace(/[Φφ]/g, '')
  .replace(/(?<=\d)\s*[×x*]\s*(?=\d)/g, '')
  .replace(/[\s\-_/]/g, '');

/* 每个产品生成一条可检索文本；客户怎么写都能撞上 */
function indexText(p) {
  return normalize([
    p.code, p.type, p.size, p.mat,
    p.axles.join(' '), p.cars.join(' ')
  ].join(' '));
}

const INDEXED = PRODUCTS.map((p) => ({ ...p, _idx: indexText(p) }));

function search(query) {
  const q = query.trim();
  if (!q) return INDEXED;
  /* 拆词：车型 + 车桥混写也能命中 */
  const terms = q.replace(/(\d)\s*[×x*]\s*(?=\d)/gi, '$1').split(/[+，,、\s]+/).map(normalize).filter(Boolean);
  return INDEXED.filter((p) => terms.every((t) => p._idx.includes(t)));
}

function tagClass(type) {
  if (type === '盘式') return 'tag t-disc';
  if (type === '风电') return 'tag t-wind';
  return 'tag';
}

function renderResults() {
  const more = document.getElementById('moreResults');
  more.hidden = true;
  more.setAttribute('aria-expanded', 'false');
  if (state.mode === 'photo') return renderPhoto();
  const list = search(state.query);
  el.count.textContent = `共 ${list.length} 条 · 匹配「${state.query || '全部'}」`;

  if (!list.length) {
    el.results.innerHTML = `
      <div class="empty">
        <b>没有命中这个条件</b>
        把旧片照片、车桥铭牌或卡钳尺寸发过来，我们人工确认。<br>
        也可以直接清空条件看全部 ${PRODUCTS.length} 条示例型号。
      </div>`;
    return;
  }

  const expandable = !state.query.trim() && list.length > 4;
  const visible = expandable && !state.expanded ? list.slice(0, 4) : list;
  more.hidden = !expandable;
  more.setAttribute('aria-expanded', String(expandable && state.expanded));
  more.textContent = state.expanded ? '收起示例型号 ↑' : `继续浏览其余 ${list.length - visible.length} 款型号 ↓`;
  if (expandable) el.count.textContent = `共 ${list.length} 款示例 · 当前展示 ${visible.length} 款`;

  el.results.innerHTML = visible.map((p) => `
    <article class="result">
      <div class="result-title">
        <b>${p.code}</b>
        <span class="${tagClass(p.type)}">${p.type}</span>
      </div>
      <button class="link-btn result-add" type="button" data-add="${p.code}">加入询价</button>
      <p class="result-meta">
        ${p.size} ｜ 适配 <span>${p.cars.join(' · ')}</span> ｜ 车桥 <span>${p.axles.join(' / ')}</span>
      </p>
      <div class="result-specs">
        <i>${p.mat}</i><i>μ ${p.mu}</i><i>${p.temp}</i><i>MOQ ${p.moq}</i><i>交期 ${p.lead}</i>
      </div>
    </article>`).join('');
  updateAddButtons();
}

let photoUrl = '';
function renderPhoto() {
  el.count.textContent = '旧片比对 · 本地预览';
  el.results.innerHTML = `
    <div class="empty">
      <b>从一张旧片照片开始</b>
      建议准备正反面照片、孔位和尺寸，方便后续人工确认。<br>
      <button class="btn btn-dark" type="button" id="choosePhoto">选择旧片照片 ↗</button>
      <input id="photoInput" type="file" accept="image/jpeg,image/png,image/webp" hidden>
      <img class="photo-preview" id="photoPreview" alt="所选旧片照片预览" hidden>
      <p class="photo-note" id="photoNote" role="status">仅在当前浏览器预览，不会上传或自动识别。</p>
    </div>`;
  const input = document.getElementById('photoInput');
  const preview = document.getElementById('photoPreview');
  if (photoUrl) { preview.src = photoUrl; preview.hidden = false; }
  document.getElementById('choosePhoto').addEventListener('click', () => input.click());
  input.addEventListener('change', () => {
    const file = input.files[0];
    if (!file) return;
    const note = document.getElementById('photoNote');
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
      note.textContent = '请选择不超过 10 MB 的 JPG、PNG 或 WebP 图片。';
      input.value = '';
      return;
    }
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    photoUrl = URL.createObjectURL(file);
    preview.src = photoUrl;
    preview.hidden = false;
    preview.onerror = () => {
      preview.hidden = true;
      URL.revokeObjectURL(photoUrl);
      photoUrl = '';
      note.textContent = '无法读取这张图片，请选择有效的 JPG、PNG 或 WebP 图片。';
    };
    note.textContent = `已选择 ${file.name}，仅在本地预览。请在联系团队时另行提供照片。`;
  });
}

function renderChips() {
  el.chips.innerHTML = CHIPS[state.mode]
    .map((c) => `<button class="chip" type="button" data-chip="${c}">${c}</button>`)
    .join('');
}

function setMode(mode) {
  state.expanded = false;
  state.mode = mode;
  state.query = '';
  el.input.value = '';
  el.input.placeholder = PLACEHOLDER[mode];
  el.hint.textContent = {
    vehicle: '车型或车系，如 解放 J6、豪沃 T7H',
    axle: '车桥型号，如 457 桥、13T 桥',
    size: '摩擦面尺寸，如 420×180',
    photo: '旧片编号 / 上传照片'
  }[mode];
  el.tabs.forEach((t) => {
    const on = t.dataset.mode === mode;
    t.classList.toggle('is-active', on);
    t.setAttribute('aria-selected', String(on));
    t.tabIndex = on ? 0 : -1;
  });
  el.results.setAttribute('aria-labelledby', `tab-${mode}`);
  renderChips();
  renderResults();
}

/* ---------- 3. 询价清单 ---------- */

const cart = new Set();

function addToCart(code) {
  if (!PRODUCTS.some((p) => p.code === code)) return;
  if (cart.has(code)) {
    toast(`${code} 已在询价清单里`);
    return;
  }
  cart.add(code);
  syncCart();
  toast(`${code} 已加入询价清单`);
}

function removeFromCart(code) {
  cart.delete(code);
  syncCart();
}

function syncCart() {
  document.getElementById('cartCount').textContent = String(cart.size);

  const list = document.getElementById('drawerList');
  const empty = document.getElementById('drawerEmpty');
  const items = PRODUCTS.filter((p) => cart.has(p.code));

  empty.hidden = items.length > 0;
  list.innerHTML = items.map((p) => `
    <li>
      <div><b>${p.code}</b><small>${p.type} · ${p.size} · ${p.mat}</small></div>
      <button class="icon-btn" type="button" data-remove="${p.code}" aria-label="移除 ${p.code}">×</button>
    </li>`).join('');

  updateAddButtons();
  try { localStorage.setItem('gy_cart', JSON.stringify([...cart])); } catch { /* 浏览器可能禁用存储 */ }
}

function updateAddButtons() {
  document.querySelectorAll('[data-add]').forEach((button) => {
    const selected = cart.has(button.dataset.add);
    button.setAttribute('aria-pressed', String(selected));
    button.textContent = selected ? '已加入 ✓' : button.closest('.result') ? '加入询价 +' : '加入询价清单 ↗';
  });
}

/* ---------- 4. 表单 ---------- */

let quoteUrl = '';

function syncNeed() {
  const need = document.getElementById('need');
  const text = need.value.split('\n').filter(line => !line.startsWith('型号：')).join('\n').trim();
  need.value = [text, cart.size ? `型号：${[...cart].join(', ')}` : ''].filter(Boolean).join('\n');
}

function submitQuote(form) {
  const note = document.getElementById('formNote');
  const required = ['company', 'country', 'contactWay'];
  let firstInvalid = null;
  required.forEach((id) => {
    const input = document.getElementById(id);
    const bad = !input.value.trim();
    input.closest('.field').classList.toggle('is-invalid', bad);
    input.setAttribute('aria-invalid', String(bad));
    if (bad) { input.setAttribute('aria-describedby', 'formNote'); firstInvalid ||= input; }
    else input.removeAttribute('aria-describedby');
  });
  note.hidden = false;
  if (firstInvalid) {
    note.className = 'form-note is-error';
    note.textContent = '请填写公司名称、国家 / 地区和联系方式。';
    firstInvalid.focus();
    return;
  }
  syncNeed();
  const now = new Date();
  const date = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('');
  const id = `GY-Q-${date}-${String(Math.floor(Math.random() * 900) + 100)}`;
  const data = new FormData(form);
  const lines = ['冠英 · 询价草稿', `草稿编号：${id}`, '状态：仅本地生成，尚未发送', '',
    `公司名称：${data.get('company')}`, `国家 / 地区：${data.get('country')}`,
    `联系方式：${data.get('contactWay')}`, `年采购量：${data.get('qty') || '待确认'}`,
    '', '需求：', data.get('need') || '待补充', '', '价格、适配、材质、MOQ 与交期均需人工确认。'];
  if (quoteUrl) URL.revokeObjectURL(quoteUrl);
  quoteUrl = URL.createObjectURL(new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/plain;charset=utf-8' }));
  note.className = 'form-note';
  note.replaceChildren();
  const title = document.createElement('strong');
  title.textContent = `草稿已生成 · ${id}`;
  const detail = document.createElement('p');
  detail.textContent = '尚未发送给团队。请下载草稿，通过确认后的联系方式发送。';
  const link = document.createElement('a');
  link.href = quoteUrl;
  link.download = `${id}.txt`;
  link.textContent = '下载询价草稿 ↓';
  note.append(title, detail, link);
  toast('询价草稿已生成，清单已保留');
}

/* ---------- 5. 交互绑定 ---------- */

let toastTimer;
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('is-show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('is-show'), 2400);
}

let drawerReturnFocus = null;
let previousOverflow = '';
const drawer = document.getElementById('drawer');
const backgroundRegions = [...document.querySelectorAll('.site-header, main, .site-footer, .skip-link')];
function openDrawer() {
  if (drawer.classList.contains('is-open')) return;
  drawerReturnFocus = document.activeElement;
  previousOverflow = document.body.style.overflow;
  document.body.style.overflow = 'hidden';
  backgroundRegions.forEach(node => { node.inert = true; });
  drawer.inert = false;
  drawer.setAttribute('aria-hidden', 'false');
  drawer.classList.add('is-open');
  document.getElementById('drawerClose').focus();
}
function closeDrawer() {
  if (!drawer.classList.contains('is-open')) return;
  drawer.classList.remove('is-open');
  backgroundRegions.forEach(node => { node.inert = false; });
  document.body.style.overflow = previousOverflow;
  drawerReturnFocus?.focus({ preventScroll: true });
  drawer.inert = true;
  drawer.setAttribute('aria-hidden', 'true');
}

function goContact() {
  syncNeed();
  closeDrawer();
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.getElementById('contact').scrollIntoView({ behavior: reduced ? 'instant' : 'smooth', block: 'start' });
  document.getElementById('company').focus({ preventScroll: true });
}

document.addEventListener('click', (e) => {
  const add = e.target.closest('[data-add]');
  if (add) { addToCart(add.dataset.add); return; }

  const rm = e.target.closest('[data-remove]');
  if (rm) { removeFromCart(rm.dataset.remove); (document.querySelector('[data-remove]') || document.getElementById('drawerClose')).focus(); return; }

  const chip = e.target.closest('[data-chip]');
  if (chip) {
    el.input.value = chip.dataset.chip;
    state.query = chip.dataset.chip;
    renderResults();
    return;
  }

  const tab = e.target.closest('.tab');
  if (tab) { setMode(tab.dataset.mode); return; }
});

document.getElementById('q').addEventListener('input', (e) => {
  const value = e.target.value;
  if (state.mode === 'photo' && value.trim()) {
    setMode('size');
    el.input.value = value;
  }
  state.query = value;
  renderResults();
});

document.querySelector('.tabs').addEventListener('keydown', (e) => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
  e.preventDefault();
  const current = el.tabs.indexOf(document.activeElement);
  const next = e.key === 'Home' ? 0 : e.key === 'End' ? el.tabs.length - 1 : (current + (e.key === 'ArrowRight' ? 1 : -1) + el.tabs.length) % el.tabs.length;
  setMode(el.tabs[next].dataset.mode);
  el.tabs[next].focus();
});

document.getElementById('resetBtn').addEventListener('click', () => {
  state.expanded = false;
  state.query = '';
  el.input.value = '';
  renderResults();
  el.input.focus();
});

document.getElementById('moreResults').addEventListener('click', () => {
  state.expanded = !state.expanded;
  renderResults();
});

document.getElementById('cartBtn').addEventListener('click', openDrawer);
document.getElementById('drawerClose').addEventListener('click', closeDrawer);
document.getElementById('drawerGo').addEventListener('click', goContact);
document.getElementById('openQuote').addEventListener('click', goContact);
document.getElementById('drawer').addEventListener('click', (e) => {
  if (e.target.id === 'drawer') closeDrawer();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeDrawer();
    if (nav.classList.contains('is-open')) { closeNav(); navToggle.focus(); }
  }
  if (e.key === 'Tab' && drawer.classList.contains('is-open')) {
    const focusable = [...drawer.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled)')];
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
});

document.getElementById('quoteForm').addEventListener('submit', (e) => {
  e.preventDefault();
  submitQuote(e.target);
});

/* 导航 */
const navToggle = document.getElementById('navToggle');
const nav = document.getElementById('nav');
navToggle.addEventListener('click', () => {
  const open = nav.classList.toggle('is-open');
  navToggle.setAttribute('aria-expanded', String(open));
  navToggle.setAttribute('aria-label', open ? '关闭菜单' : '打开菜单');
});
nav.addEventListener('click', (e) => {
  if (e.target.tagName === 'A') {
    closeNav();
  }
});

function closeNav() {
  nav.classList.remove('is-open');
  navToggle.setAttribute('aria-expanded', 'false');
  navToggle.setAttribute('aria-label', '打开菜单');
}
document.addEventListener('click', event => {
  if (!event.target.closest('.site-header')) closeNav();
});
window.matchMedia('(min-width: 901px)').addEventListener('change', event => { if (event.matches) closeNav(); });
document.querySelector('.hero-search').addEventListener('submit', event => {
  const query = document.getElementById('heroQuery');
  query.value = query.value.trim();
  if (!query.value) { event.preventDefault(); query.reportValidity(); }
});
document.getElementById('quoteForm').addEventListener('input', event => {
  const input = event.target;
  if (input.required && input.value.trim()) {
    input.setAttribute('aria-invalid', 'false');
    input.closest('.field').classList.remove('is-invalid');
    input.removeAttribute('aria-describedby');
  }
});

window.addEventListener('scroll', () => {
  document.querySelector('.site-header').classList.toggle('is-scrolled', window.scrollY > 8);
}, { passive: true });

/* 入场动画 */
const io = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
  entries.forEach((en) => {
    if (en.isIntersecting) {
      en.target.classList.add('is-in');
      io.unobserve(en.target);
    }
  });
}, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }) : null;

document.querySelectorAll('.section-head, .card, .steps li, .selector, .brand-strip, .contact-inner')
  .forEach((n) => { n.classList.add('reveal'); io?.observe(n); });

/* 恢复上次清单 */
try {
  const saved = JSON.parse(localStorage.getItem('gy_cart') || '[]');
  if (Array.isArray(saved)) saved.forEach((c) => { if (PRODUCTS.some((p) => p.code === c)) cart.add(c); });
} catch { /* 忽略 */ }

/* 启动 */
setMode('vehicle');
syncCart();
