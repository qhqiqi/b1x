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
  vehicle: ['解放 J6', '豪沃 T7H', '欧曼 GTL', '德龙 X3000', 'Actros', 'Hino 500'],
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

const state = { mode: 'vehicle', query: '' };

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
  .replace(/[×x*]/g, '')
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
  const q = normalize(query);
  if (!q) return INDEXED;
  /* 拆词：车型 + 车桥混写也能命中 */
  const terms = q.split(/[+，,、]/).filter(Boolean);
  return INDEXED.filter((p) => terms.every((t) => p._idx.includes(t)));
}

function tagClass(type) {
  if (type === '盘式') return 'tag t-disc';
  if (type === '风电') return 'tag t-wind';
  return 'tag';
}

function renderResults() {
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

  el.results.innerHTML = list.map((p) => `
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
}

function renderPhoto() {
  el.count.textContent = '旧片比对 · 人工复核';
  el.results.innerHTML = `
    <div class="empty">
      <b>发一张旧片照片就够了</b>
      照片、钢背编号、卡钳尺寸任一即可。系统按摩擦面轮廓与孔位粗筛，再由外贸团队复核车桥变更。<br><br>
      <button class="btn btn-dark" type="button" id="fakeUpload">模拟上传照片</button>
    </div>`;
  const btn = document.getElementById('fakeUpload');
  btn?.addEventListener('click', () => {
    btn.textContent = '已提交，2 小时内回复';
    btn.disabled = true;
    toast('照片已提交（演示）：真实版本进入外贸团队待办');
  });
}

function renderChips() {
  el.chips.innerHTML = CHIPS[state.mode]
    .map((c) => `<button class="chip" type="button" data-chip="${c}">${c}</button>`)
    .join('');
}

function setMode(mode) {
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
  });
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

  /* 页面上所有“加入询价”按钮同步状态 */
  document.querySelectorAll('[data-add]').forEach((b) => {
    const inCart = cart.has(b.dataset.add);
    if (b.classList.contains('link-btn') && b.closest('.result')) {
      b.textContent = inCart ? '已加入' : '加入询价';
    }
  });

  try { localStorage.setItem('gy_cart', JSON.stringify([...cart])); } catch { /* 忽略 */ }
}

/* ---------- 4. 表单 ---------- */

function submitQuote(form) {
  const note = document.getElementById('formNote');
  const need = document.getElementById('need');
  const codes = [...cart];

  if (codes.length && !need.value.includes('GY-')) {
    need.value = `${need.value ? need.value + '\n' : ''}型号：${codes.join(', ')}`;
  }

  const required = ['company', 'country', 'contactWay'];
  let ok = true;
  required.forEach((id) => {
    const input = document.getElementById(id);
    const bad = !input.value.trim();
    input.closest('.field').classList.toggle('is-invalid', bad);
    if (bad) ok = false;
  });

  note.hidden = false;
  if (!ok) {
    note.className = 'form-note is-error';
    note.textContent = '还差带 * 的必填项：公司名称、国家/地区、联系方式。';
    return;
  }

  const id = 'GY-Q-' + new Date().toISOString().slice(0, 10).replace(/-/g, '') +
    '-' + String(Math.floor(Math.random() * 900) + 100);

  note.className = 'form-note';
  note.innerHTML = `<b>已提交 ${id}</b><br>外贸团队会在工作时段 2 小时内回复${codes.length ? '，并附上 ' + codes.length + ' 个型号的报价' : ''}。`;
  toast('需求已提交，等待外贸团队跟进');

  if (codes.length) {
    cart.clear();
    syncCart();
  }
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

function openDrawer() {
  document.getElementById('drawer').classList.add('is-open');
  document.getElementById('drawer').setAttribute('aria-hidden', 'false');
}
function closeDrawer() {
  document.getElementById('drawer').classList.remove('is-open');
  document.getElementById('drawer').setAttribute('aria-hidden', 'true');
}

function goContact() {
  const codes = [...cart];
  const need = document.getElementById('need');
  if (codes.length) {
    const line = `型号：${codes.join(', ')}`;
    if (!need.value.includes(line)) need.value = need.value ? `${need.value}\n${line}` : line;
  }
  closeDrawer();
  document.getElementById('contact').scrollIntoView({ behavior: 'smooth', block: 'start' });
  setTimeout(() => document.getElementById('company').focus({ preventScroll: true }), 500);
}

document.addEventListener('click', (e) => {
  const add = e.target.closest('[data-add]');
  if (add) { addToCart(add.dataset.add); return; }

  const rm = e.target.closest('[data-remove]');
  if (rm) { removeFromCart(rm.dataset.remove); return; }

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
  state.query = e.target.value;
  if (state.mode === 'photo' && e.target.value.trim()) {
    state.mode = 'size'; /* 输入编号时按尺寸/编号检索 */
    el.tabs.forEach((t) => t.classList.toggle('is-active', t.dataset.mode === 'size'));
  }
  renderResults();
});

document.getElementById('resetBtn').addEventListener('click', () => {
  state.query = '';
  el.input.value = '';
  renderResults();
  el.input.focus();
});

document.getElementById('cartBtn').addEventListener('click', openDrawer);
document.getElementById('drawerClose').addEventListener('click', closeDrawer);
document.getElementById('drawerGo').addEventListener('click', goContact);
document.getElementById('openQuote').addEventListener('click', goContact);
document.getElementById('drawer').addEventListener('click', (e) => {
  if (e.target.id === 'drawer') closeDrawer();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeDrawer();
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
});
nav.addEventListener('click', (e) => {
  if (e.target.tagName === 'A') {
    nav.classList.remove('is-open');
    navToggle.setAttribute('aria-expanded', 'false');
  }
});

window.addEventListener('scroll', () => {
  document.querySelector('.site-header').classList.toggle('is-scrolled', window.scrollY > 8);
}, { passive: true });

/* 入场动画 */
const io = new IntersectionObserver((entries) => {
  entries.forEach((en) => {
    if (en.isIntersecting) {
      en.target.classList.add('is-in');
      io.unobserve(en.target);
    }
  });
}, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

document.querySelectorAll('.section-head, .card, .steps li, .selector, .brand-strip, .contact-inner')
  .forEach((n) => { n.classList.add('reveal'); io.observe(n); });

/* 恢复上次清单 */
try {
  const saved = JSON.parse(localStorage.getItem('gy_cart') || '[]');
  if (Array.isArray(saved)) saved.forEach((c) => { if (PRODUCTS.some((p) => p.code === c)) cart.add(c); });
} catch { /* 忽略 */ }

/* 启动 */
setMode('vehicle');
syncCart();
