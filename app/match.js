/* =========================================================
   冠英 · 实时选型查询（P3）
   数据契约：data/reports/p3_handoff.md 第 2 节（v1.2）
   - 实时：GET {API}/match?q=...   超时 2.5s，失败重试 2 次
   - 兜底：本地缓存 localStorage → 内置 samples.js（8 条）
   ========================================================= */

(() => {
  'use strict';

  const API = (() => {
    const p = new URLSearchParams(location.search).get('api');
    if (p) return p.replace(/\/+$/, '');
    const host = location.hostname;
    // 本机演示：直连本地服务，最快
    if (/^(localhost|127\.0\.0\.1|\[::1\])$/.test(host)) return 'http://127.0.0.1:8787';
    // 线上：优先用 api-config.js 里的演示地址（隧道/自己的服务器）
    if (window.GY_API) return String(window.GY_API).replace(/\/+$/, '');
    // 若引擎已部署在同域（如阿里云方案 B），走 /b1x/api
    if (/qhqiqi\.cn$/.test(host)) return location.origin + '/b1x/api';
    return 'http://127.0.0.1:8787';
  })();

  const CACHE_KEY = 'p3_match_cache_v1';
  const TIMEOUT_MS = 2500;
  const RETRIES = 2;

  const el = {
    form: document.getElementById('searchForm'),
    input: document.getElementById('q'),
    chips: document.getElementById('chips'),
    result: document.getElementById('result'),
    notice: document.getElementById('notice'),
    status: document.getElementById('status'),
    statusText: document.getElementById('statusText')
  };

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  /* ---------------- 缓存 ---------------- */
  function readCache() {
    try { return JSON.parse(localStorage.getItem(CACHE_KEY) || '{}') || {}; }
    catch { return {}; }
  }
  function writeCache(map) {
    try {
      const keys = Object.keys(map);
      if (keys.length > 60) keys.slice(0, keys.length - 60).forEach((k) => delete map[k]);
      localStorage.setItem(CACHE_KEY, JSON.stringify(map));
    } catch { /* 隐私模式忽略 */ }
  }
  function cachePut(q, res) {
    const map = readCache();
    map[q] = { at: Date.now(), response: res };
    writeCache(map);
  }
  function cacheGet(q) {
    const hit = readCache()[q];
    return hit ? hit.response : null;
  }

  /* ---------------- 样例兜底 ---------------- */
  const SAMPLES = Array.isArray(window.P3_SAMPLES) ? window.P3_SAMPLES : [];

  const norm = (s) => String(s || '').toLowerCase().replace(/[\s×x*]/g, '');

  function sampleFor(q) {
    const nq = norm(q);
    const exact = SAMPLES.find((s) => s.request === q || norm(s.request) === nq);
    if (exact) return exact;
    return SAMPLES.find((s) => {
      const ns = norm(s.request);
      return ns && (ns.includes(nq) || nq.includes(ns));
    }) || null;
  }

  /* ---------------- 调接口 ---------------- */
  async function fetchMatch(q) {
    let lastErr;
    for (let attempt = 0; attempt <= RETRIES; attempt++) {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
      try {
        const res = await fetch(`${API}/match?q=${encodeURIComponent(q)}`, {
          signal: ctrl.signal,
          headers: { Accept: 'application/json' }
        });
        clearTimeout(timer);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (e) {
        clearTimeout(timer);
        lastErr = e;
        if (attempt < RETRIES) await new Promise((r) => setTimeout(r, 120 * (attempt + 1) ** 2));
      }
    }
    throw lastErr || new Error('接口不可用');
  }

  /* ---------------- 状态 ---------------- */
  function setStatus(kind, text) {
    el.status.className = 'status' + (kind ? ' is-' + kind : '');
    el.statusText.textContent = text;
  }

  function showNotice(html, isError) {
    if (!html) { el.notice.hidden = true; el.notice.innerHTML = ''; return; }
    el.notice.hidden = false;
    el.notice.className = 'notice' + (isError ? ' is-error' : '');
    el.notice.innerHTML = html;
  }

  /* ---------------- 渲染：公共 ---------------- */
  const confClass = (c) => ({ '高': 'b-high', '中': 'b-mid', '低': 'b-low' }[c] || 'b-plain');

  function parsedStrip(parsed) {
    if (!parsed) return '';
    const sig = [];
    const d = parsed.dims || {};
    if (d.raw_text) sig.push(`<span class="sig"><b>尺寸</b>${esc(d.raw_text)}</span>`);
    (parsed.axles || []).forEach((a) => {
      const name = [a.brand, a.model].filter(Boolean).join(' ') || a.axle_id;
      if (name) sig.push(`<span class="sig"><b>车桥</b>${esc(name)}</span>`);
    });
    (parsed.car_models || []).forEach((c) => {
      const name = typeof c === 'string' ? c : (c.name || c.model || '');
      if (name) sig.push(`<span class="sig"><b>车型</b>${esc(name)}</span>`);
    });
    (parsed.codes || []).forEach((c) => sig.push(`<span class="sig"><b>编码</b>${esc(c)}</span>`));
    if (!sig.length) return '';
    return `<div class="parsed"><span class="lead">我理解到的是</span>${sig.join('')}</div>`;
  }

  function metaBar(res, source) {
    const n = (res.candidates || []).length;
    const modeText = { rule: '规则命中', ask: '需要追问', export: '海外对码' }[res.mode] || res.mode || '—';
    const parts = [
      `<span class="mode ${esc(res.mode || '')}">${modeText}</span>`,
      res.mode === 'ask' ? '未给候选（信息不足）' : `候选 ${n} 条`,
      typeof res.elapsed_ms === 'number' ? `${res.elapsed_ms} ms` : '',
      source === 'live' ? '实时接口' : '本地缓存'
    ].filter(Boolean);
    return `<div class="answer-meta">${parts.map((p, i) => (
      i === 0 ? p : `<span class="sep">·</span>${p}`
    )).join('')}</div>`;
  }

  /* ---------------- 渲染：候选 ---------------- */
  function candCard(c, i) {
    const ev = (c.evidence && c.evidence[0]) || null;
    const price = (c.price === null || c.price === undefined) ? '询价确认'
      : (typeof c.price === 'number' ? `¥ ${c.price}` : esc(c.price));

    const badges = [];
    if (c.confidence) badges.push(`<span class="badge ${confClass(c.confidence)}">置信度 ${esc(c.confidence)}</span>`);
    badges.push(c.verified
      ? '<span class="badge b-ok">已核对原文</span>'
      : '<span class="badge b-plain">未核对</span>');
    if (c.ocr) badges.push('<span class="badge b-ocr">扫描图页识别</span>');

    const tech = [
      typeof c.score === 'number' ? `score ${c.score}` : '',
      typeof c.dims_err === 'number' && c.dims_err < 90 ? `尺寸偏差 ${c.dims_err}` : '',
      c.extractor ? `来源 ${c.extractor}` : '',
      c.src_rank ? `rank ${c.src_rank}` : ''
    ].filter(Boolean).join(' · ');

    return `
      <article class="cand">
        <div class="cand-head">
          <h3>${esc(c.sku_id)}</h3>
          ${badges.join('')}
        </div>
        ${c.reason ? `<p class="reason">${esc(c.reason)}</p>` : ''}
        <dl class="specs">
          <div><dt>尺寸</dt><dd title="${esc((c.dims || {}).raw_text || '')}">${esc((c.dims || {}).raw_text || '—')}</dd></div>
          <div><dt>类别</dt><dd>${esc(c.category || '—')}</dd></div>
          <div><dt>材质</dt><dd class="${c.material && c.material !== '未知' ? '' : 'dim'}">${esc(c.material || '未知')}</dd></div>
          <div><dt>库存</dt><dd class="dim">${esc(c.stock || '未知')}</dd></div>
        </dl>
        <div class="cand-foot">
          <span class="src">${ev
            ? `出处：<b>${esc(ev.report_id)}</b>${ev.kind ? ' · ' + esc(ev.kind) : ''} p${esc(ev.page)}`
            : '出处：—'}</span>
          <span class="price">${price}</span>
        </div>
        ${(ev && ev.snippet) || tech ? `
        <details>
          <summary>为什么是这个</summary>
          ${ev && ev.snippet ? `<p class="snippet">${esc(ev.snippet)}</p>` : ''}
          ${tech ? `<p class="tech">${esc(tech)}</p>` : ''}
        </details>` : ''}
      </article>`;
  }

  /* ---------------- 渲染：追问 ---------------- */
  function askBox(res) {
    const list = res.followups || [];
    const items = list.length
      ? `<ol>${list.map((f) => `<li>${esc(f)}</li>`).join('')}</ol>`
      : '<p class="why">这句话里没有足够的型号信号，需要再补一个条件。</p>';
    return `
      <div class="ask-box">
        <h3>先确认这几件事</h3>
        <p class="why">资料包里没有能直接对上的型号，我们不给候选，先问清楚。</p>
        ${items}
        <p class="hint">补齐任一条件再查：车桥品牌型号、旧片钢背编码、摩擦面尺寸（外弧 × 宽度 × 厚度）。</p>
      </div>`;
  }

  /* ---------------- 渲染：海外对码 ---------------- */
  function exportRows(res) {
    const rows = res.export_matches || [];
    if (!rows.length) {
      return '<div class="empty"><b>没有对到码</b>外商报的编码不在出口册 p32–34 的 34 条里，建议让客户提供旧片钢背照片。</div>';
    }
    return `<p class="export-intro">外商报的是 FMSI / OE / WVA / 英制尺寸，不是中文车型——下面是把他的码对回我方出口册的结果。</p>`
      + rows.map((m) => {
        const from = [];
        if (m.fmsi) from.push(`FMSI ${m.fmsi}`);
        if (m.wva) from.push(`WVA ${m.wva}`);
        if (m.oe_ref) from.push(`OE ${m.oe_ref}`);
        if (m.size) from.push(`尺寸号 ${m.size}`);
        if (m.hardware) from.push(m.hardware);
        const kindText = ({ american: '美系 FMSI', european: '欧系', bpw: 'BPW', saf: 'SAF' }[m.kind] || m.kind || '');
        const badges = [
          m.verified ? '<span class="badge b-ok">已核对原文</span>' : '<span class="badge b-plain">册子上写着 · 未核对</span>',
          kindText ? `<span class="badge b-plain">${esc(kindText)}</span>` : ''
        ].filter(Boolean).join('');

        return `
          <article class="export-row">
            <div class="export-from">
              <div class="label">外商报的码</div>
              <div class="code">${esc(from.join(' · ') || '未识别编码')}</div>
              <div class="meta">${esc(kindText)}</div>
            </div>
            <div class="export-arrow" aria-hidden="true">→</div>
            <div class="export-to">
              <div class="label">我方型号</div>
              <div class="code">${esc(m.shoe_code || m.sku_id || '—')}</div>
              <div class="meta">出口册 p${esc(m.page)}</div>
            </div>
            <div class="export-badges">${badges}</div>
            ${m.why ? `<div class="export-why">${esc(m.why)}</div>` : ''}
          </article>`;
      }).join('');
  }

  /* ---------------- 渲染：总入口 ---------------- */
  function render(res, source) {
    if (!res || typeof res !== 'object') {
      el.result.innerHTML = '<div class="empty"><b>返回格式不对</b>接口没有按 p3_handoff.md 第 2 节的结构返回。</div>';
      return;
    }
    let body = '';
    if (res.mode === 'ask') body = askBox(res);
    else if (res.mode === 'export') body = exportRows(res);
    else body = (res.candidates || []).map(candCard).join('')
      || '<div class="empty"><b>没有候选</b>引擎没匹配到型号。可以补车桥、尺寸或旧片编码再试。</div>';

    el.result.innerHTML = metaBar(res, source) + parsedStrip(res.parsed) + body;
  }

  /* ---------------- 查询主流程 ---------------- */
  async function run(qRaw) {
    const q = String(qRaw || '').trim();
    if (!q) { el.input.focus(); return; }

    el.result.setAttribute('aria-busy', 'true');
    el.result.innerHTML = '<div class="skeleton"></div><div class="skeleton"></div>';
    el.form.querySelector('button').disabled = true;
    showNotice('');
    setStatus('', '查询中…');

    let res = null;
    let source = 'live';

    try {
      res = await fetchMatch(q);
      cachePut(q, res);
      setStatus('live', `实时 · ${typeof res.elapsed_ms === 'number' ? res.elapsed_ms + ' ms' : '已连上'}`);
    } catch (e) {
      source = 'cache';
      const hit = cacheGet(q) || (sampleFor(q) || {}).response || null;
      res = hit;
      if (hit) {
        setStatus('cache', '离线缓存');
        showNotice(`接口没连上（<code>${esc(API)}</code>），已切到本地缓存。现场演示够用；要实时查询先起服务：<code>cd p2 &amp;&amp; python scripts/api_server.py --port 8787</code>`, false);
      } else {
        setStatus('error', '接口未连上');
        showNotice(`接口没连上（<code>${esc(API)}</code>），本地缓存也没有这条查询。先起匹配服务：<code>cd p2 &amp;&amp; python scripts/api_server.py --port 8787</code>，或用下面任意一条演示查询。`, true);
        el.result.innerHTML = `<div class="empty"><b>这条查不到</b>缓存里只有这些演示查询：
          <ul>${SAMPLES.map((s) => `<li><code>${esc(s.request)}</code> · ${esc(s.label)}</li>`).join('')}</ul></div>`;
        el.result.setAttribute('aria-busy', 'false');
        el.form.querySelector('button').disabled = false;
        return;
      }
    }

    render(res, source);
    el.result.setAttribute('aria-busy', 'false');
    el.form.querySelector('button').disabled = false;
  }

  /* ---------------- 交互 ---------------- */
  function buildChips() {
    el.chips.innerHTML = SAMPLES.map((s) => (
      `<button class="chip" type="button" data-q="${esc(s.request)}"><b>${esc(s.label)}</b>${esc(s.request)}</button>`
    )).join('');
  }

  el.chips.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    el.input.value = chip.dataset.q;
    run(chip.dataset.q);
  });

  el.form.addEventListener('submit', (e) => {
    e.preventDefault();
    run(el.input.value);
  });

  /* ---------------- 启动 ---------------- */
  buildChips();

  const initial = new URLSearchParams(location.search).get('q');
  if (initial) {
    el.input.value = initial;
    run(initial);
  } else {
    // 探测一次接口，状态灯给个准信
    fetchMatch('147×100×14.5')
      .then((r) => {
        cachePut('147×100×14.5', r);
        setStatus('live', '接口已连上');
      })
      .catch(() => setStatus('cache', '离线缓存可用'));
  }
})();
