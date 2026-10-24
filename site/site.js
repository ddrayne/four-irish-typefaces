/* Four Irish Typefaces: the test page. No framework; every section works on its own. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const CFG = JSON.parse(document.getElementById('config').textContent);
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const store = {
    get(k, d) { try { const v = localStorage.getItem('irish-typefaces:' + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem('irish-typefaces:' + k, JSON.stringify(v)); } catch { /* private mode */ } },
  };
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v; else if (k === 'style') n.style.cssText = v;
      else n.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids) if (kid !== null && kid !== undefined) n.append(kid);
    return n;
  };
  const NS = 'http://www.w3.org/2000/svg';
  const svg = (tag, attrs = {}) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  };
  // the same small wobble every time for the same letter in the same place
  const jitter = (i, salt = 0) => {
    const f = k => { const x = Math.sin((i + 1) * 12.9898 + salt * 78.233 + k * 37.719) * 43758.5453; return x - Math.floor(x); };
    return [f(1), f(2), f(3)];
  };
  const FACES = CFG.faces;
  const ORDER = CFG.order;
  const featCSS = f => (f ? `"${f}"` : 'normal');
  // the four styles; Carrick and Tuam Uncial have no bold, and answer a bold with their one weight
  const W = st => (st.includes('Bold') ? 700 : 400), SL = st => (st.includes('Italic') ? 'italic' : 'normal');
  const styleOf = (k, st) => {
    const has = FACES[k].styles;
    if (has.includes(st)) return { st, note: '' };
    const fall = st.includes('Italic') ? 'Italic' : 'Regular';
    return { st: fall, note: `${FACES[k].family} has no bold: it is black already` };
  };
  function chipGroup(box, value, onPick) {
    const chips = $$('.chip', box);
    const set = v => chips.forEach(c => c.setAttribute('aria-pressed', c.dataset.style === v ? 'true' : 'false'));
    set(value);
    box.addEventListener('click', e => { const c = e.target.closest('.chip'); if (!c) return; set(c.dataset.style); onPick(c.dataset.style); });
  }

  /* ------------------------------------------------------------------ hero: letters rubbed down by hand */
  const title = $('.hero-title');
  if (title) {
    const words = title.textContent.split(' '); title.textContent = '';
    let i = 0;
    words.forEach((w, wi) => {
      if (wi) title.append(' ');
      const word = el('span', { class: 'w', 'aria-hidden': 'true' });
      for (const ch of w) {
        const [a, b] = jitter(i, 3);
        const s = el('span', { class: 'ch', text: ch });
        s.style.setProperty('--i', i++);
        s.style.setProperty('--r', ((a - .5) * 1.6).toFixed(2) + 'deg');
        s.style.setProperty('--dy', ((b - .5) * .028).toFixed(3) + 'em');
        word.append(s);
      }
      title.append(word);
    });
  }

  /* ------------------------------------------------------------------ tabs */
  const tabHandlers = {};
  function selectTab(group, key, focus = false) {
    $$(`[data-tabs="${group}"] .tab`).forEach(t => {
      const on = t.dataset.face === key;
      t.setAttribute('aria-selected', on); t.tabIndex = on ? 0 : -1;
      if (on && focus) t.focus();
    });
    tabHandlers[group] && tabHandlers[group](key);
  }
  $$('[data-tabs]').forEach(list => {
    const group = list.dataset.tabs;
    $$('.tab', list).forEach(t => t.setAttribute('aria-controls', group === 'sheet' ? 'sheet-film' : 'chars'));
    list.addEventListener('click', e => { const t = e.target.closest('.tab'); if (t) selectTab(group, t.dataset.face); });
    list.addEventListener('keydown', e => {
      const tabs = $$('.tab', list); const i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      const j = e.key === 'ArrowRight' ? (i + 1) % tabs.length : e.key === 'ArrowLeft' ? (i - 1 + tabs.length) % tabs.length : -1;
      if (j >= 0) { e.preventDefault(); selectTab(group, tabs[j].dataset.face, true); }
    });
  });
  $$('.face-tile a').forEach(a => a.addEventListener('click', () => { selectTab('sheet', a.dataset.face); }));

  /* ------------------------------------------------------------------ the transfer sheet and the board */
  const board = {
    face: store.get('board-face', 'kilfane'),
    items: store.get('board-items', null),
    line: $('#board-line'), paper: $('#board-paper'), input: $('#board-input'),
    size: $('#board-size'), sizeOut: $('#board-size-out'), hand: $('#board-hand'),
  };
  if (!FACES[board.face]) board.face = 'kilfane';
  if (!Array.isArray(board.items)) board.items = [...FACES[board.face].sample].map(c => ({ c }));
  board.hand.checked = store.get('board-hand', true);
  board.size.value = store.get('board-size', innerWidth < 600 ? 64 : 96);

  function renderBoard(fresh = -1) {
    const { line, items, face } = board;
    const fam = FACES[face].stack;
    line.style.fontFamily = fam;
    line.style.fontSize = board.size.value + 'px';
    board.sizeOut.textContent = board.size.value;
    line.textContent = '';
    if (board.hand.checked) {
      // placed one by one, as by hand: no kerning, a little wobble; words stay whole
      let word = null;
      items.forEach((it, i) => {
        if (it.c === '\n') { line.append(el('br')); word = null; return; }
        if (!it.c.trim()) { line.append(document.createTextNode(it.c)); word = null; return; }
        if (!word) { word = el('span', { class: 'bw' }); line.append(word); }
        const s = el('span', { class: 'bl' + (i === fresh ? ' new' : ''), text: it.c });
        if (it.f && it.face === face) s.style.fontFeatureSettings = featCSS(it.f);
        if (it.c.trim()) {
          const [a, b, c] = jitter(i, it.c.codePointAt(0) % 97);
          s.style.setProperty('--r', ((a - .5) * 2.6).toFixed(2) + 'deg');
          s.style.setProperty('--dy', ((b - .5) * .05).toFixed(3) + 'em');
          s.style.setProperty('--dx', ((c - .5) * .03).toFixed(3) + 'em');
        }
        word.append(s);
      });
    } else {
      // typeset: runs of plain text, so the font's kerning and accents work across letters
      let run = null, runF = null;
      items.forEach((it, i) => {
        const f = it.f && it.face === face ? it.f : null;
        if (it.c === '\n') { line.append(el('br')); run = null; return; }
        if (i === fresh) { line.append(Object.assign(el('span', { class: 'bl new', text: it.c }), {})); run = null; return; }
        if (!run || runF !== f) { run = el('span'); runF = f; if (f) run.style.fontFeatureSettings = featCSS(f); line.append(run); }
        run.textContent += it.c;
      });
    }
    line.append(el('span', { class: 'caret', 'aria-hidden': 'true' }));
    store.set('board-items', items.slice(0, 240)); store.set('board-face', face);
  }
  function addToBoard(text, f = null) {
    let fresh = -1;
    for (const c of text) {
      if (board.items.length >= 240) break;
      board.items.push(f ? { c, f, face: board.face } : { c }); fresh = board.items.length - 1;
    }
    renderBoard(fresh);
    if (!board.hand.checked) setTimeout(() => renderBoard(), 600);
  }
  board.input.addEventListener('input', e => {
    if (e.isComposing) return;
    const v = board.input.value.replace(/\r/g, ''); board.input.value = '';
    if (v) addToBoard(v);
  });
  board.input.addEventListener('compositionend', () => {
    const v = board.input.value; board.input.value = ''; if (v) addToBoard(v);
  });
  board.input.addEventListener('keydown', e => {
    if (e.key === 'Backspace' && !board.input.value) { e.preventDefault(); board.items.pop(); renderBoard(); }
  });
  board.input.addEventListener('focus', () => board.paper.classList.add('focus'));
  board.input.addEventListener('blur', () => board.paper.classList.remove('focus'));
  board.size.addEventListener('input', () => { store.set('board-size', +board.size.value); renderBoard(); });
  board.hand.addEventListener('change', () => { store.set('board-hand', board.hand.checked); renderBoard(); });
  $('#board-undo').addEventListener('click', () => { board.items.pop(); renderBoard(); });
  $('#board-clear').addEventListener('click', () => { board.items = []; renderBoard(); board.input.focus(); });
  $('#board-copy').addEventListener('click', async e => {
    const text = board.items.map(i => i.c).join('');
    try { await navigator.clipboard.writeText(text); flash(e.target, 'Copied'); } catch { flash(e.target, 'Copy failed'); }
  });
  $('#board-save').addEventListener('click', () => saveBoard());
  function flash(btn, msg) { const t = btn.textContent; btn.textContent = msg; setTimeout(() => { btn.textContent = t; }, 1400); }

  // Inside the claude.ai preview, files are saved through the host's downloads capability.
  const host = (window.claude && typeof window.claude.use === 'function') ? window.claude.use('downloads').catch(() => null) : null;
  async function saveFile(filename, blob) {
    const dl = host ? await host : null;
    if (dl) return dl.save({ filename, data: blob });
    const a = el('a', { href: URL.createObjectURL(blob), download: filename });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    return { status: 'saved' };
  }

  async function saveBoard() {
    const face = FACES[board.face]; const px = +board.size.value; const scale = 2;
    await document.fonts.load(`${px}px ${face.stack}`);
    const c = document.createElement('canvas'); const ctx = c.getContext('2d');
    const font = `${px}px ${face.stack}`; ctx.font = font;
    const lines = [[]]; board.items.forEach((it, i) => { if (it.c === '\n') lines.push([]); else lines[lines.length - 1].push([it, i]); });
    const lh = px * 1.3, pad = px * .45;
    const widthOf = ln => board.hand.checked ? ln.reduce((w, [it]) => w + ctx.measureText(it.c).width, 0) : ctx.measureText(ln.map(([it]) => it.c).join('')).width;
    const W = Math.max(320, Math.ceil(Math.max(...lines.map(widthOf)) + 2 * pad)), H = Math.ceil(lines.length * lh + 2 * pad);
    c.width = W * scale; c.height = H * scale;
    ctx.scale(scale, scale);
    const css = getComputedStyle(document.documentElement);
    ctx.fillStyle = css.getPropertyValue('--paper-hi').trim() || '#fbf8f1'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = css.getPropertyValue('--ink').trim() || '#171513'; ctx.font = font; ctx.textBaseline = 'alphabetic';
    lines.forEach((ln, li) => {
      const y = pad + li * lh + px * 1.0;
      if (!board.hand.checked) { ctx.fillText(ln.map(([it]) => it.c).join(''), pad, y); return; }
      let x = pad;
      ln.forEach(([it, i]) => {
        const w = ctx.measureText(it.c).width;
        const [a, b, d] = jitter(i, it.c.codePointAt(0) % 97);
        ctx.save(); ctx.translate(x + w / 2 + (d - .5) * .03 * px, y + (b - .5) * .05 * px); ctx.rotate((a - .5) * 2.6 * Math.PI / 180);
        ctx.fillText(it.c, -w / 2, 0); ctx.restore(); x += w;
      });
    });
    c.toBlob(blob => { if (blob) saveFile(`${face.file}-board.png`, blob).catch(() => {}); }, 'image/png');
  }

  function renderSheet(key) {
    const f = FACES[key]; board.face = key;
    $('#sheet-code').textContent = f.sheets[0][0];
    $('#sheet-name').textContent = `${f.family} · ${f.sheets[0][1]} · ${f.sheets[0][2]}`;
    const body = $('#sheet-body'); body.textContent = ''; body.style.fontFamily = f.stack;
    const addRow = (chars, label) => {
      if (label) body.append(el('div', { class: 'sheet-label', text: label }));
      const row = el('div', { class: 'sheet-row' });
      for (const item of chars) {
        const [c, feat, alabel] = Array.isArray(item) ? item : [item, null, null];
        const b = el('button', { type: 'button', class: 'sg', text: c, 'aria-label': alabel ? `${c}, ${alabel}` : `Rub down ${c}`, 'data-f': feat });
        if (feat) b.style.fontFeatureSettings = featCSS(feat);
        row.append(b);
      }
      body.append(row);
    };
    f.rows.forEach(r => addRow([...r]));
    if (f.alts.length) addRow(f.alts, 'Alternates');
    renderBoard();
  }
  $('#sheet-body').addEventListener('click', e => {
    const b = e.target.closest('.sg'); if (!b) return;
    addToBoard(b.textContent, b.dataset.f || null);
    b.classList.remove('used'); void b.offsetWidth; b.classList.add('used');
  });
  $('#sheet-body').addEventListener('animationend', e => e.target.classList.remove('used'));
  board.paper.addEventListener('click', () => board.input.focus());
  tabHandlers.sheet = renderSheet;
  selectTab('sheet', board.face);

  /* ------------------------------------------------------------------ tester */
  const T = { text: $('#tester-text'), preset: $('#tester-preset'), size: $('#tester-size'), out: $('#tester-size-out'), guides: $('#tester-guides'),
    style: 'Regular' };
  const covers = Object.fromEntries(ORDER.map(k => [k, new Set(FACES[k].cmap)]));
  function paintRow(row) {
    const k = row.dataset.face, f = FACES[k], px = +T.size.value;
    const txt = row.querySelector('.row-text');
    const s = styleOf(k, T.style);
    txt.style.fontWeight = W(s.st); txt.style.fontStyle = SL(s.st);
    let note = row.querySelector('.row-style');
    if (!note) { note = el('span', { class: 'row-style' }); row.querySelector('.row-meta').append(note); }
    note.textContent = s.note; note.hidden = !s.note;
    const lh = Math.round(px * 1.3);
    txt.style.fontSize = px + 'px'; txt.style.lineHeight = lh + 'px';
    if (T.guides.checked) {
      const bl = Math.round((lh - (f.m.asc - f.m.desc) * px) / 2 + f.m.asc * px), xl = Math.round(bl - f.m.xh * px);
      txt.style.backgroundImage = `repeating-linear-gradient(to bottom, transparent 0 ${xl}px, var(--blue-soft) ${xl}px ${xl + 1}px, transparent ${xl + 1}px ${bl}px, var(--blue) ${bl}px ${bl + 1}px, transparent ${bl + 1}px ${lh}px)`;
    } else txt.style.backgroundImage = 'none';
  }
  function paintTester() {
    const v = T.text.value;
    T.out.textContent = T.size.value;
    $$('.row').forEach(row => {
      const k = row.dataset.face;
      row.querySelector('.row-text').textContent = v || ' ';
      const missing = [...new Set([...v].filter(c => c.trim() && !covers[k].has(c.codePointAt(0)) && !/\p{M}/u.test(c)))];
      const cov = row.querySelector('.row-cover');
      cov.textContent = missing.length ? `Not in this face: ${missing.join(' ')}` : 'Every character is in this face';
      cov.classList.toggle('miss', missing.length > 0);
      paintRow(row);
    });
    store.set('tester', { text: v, size: +T.size.value, guides: T.guides.checked, style: T.style });
  }
  const saved = store.get('tester', null);
  if (saved) { T.text.value = saved.text; T.size.value = saved.size; T.guides.checked = saved.guides; if (saved.style) T.style = saved.style; }
  else if (innerWidth < 600) T.size.value = 40;           // so a word of Tuam Uncial fits a phone
  T.preset.addEventListener('change', () => {
    const p = CFG.presets[+T.preset.value]; T.text.value = p[2]; T.text.lang = p[0]; paintTester();
  });
  [T.text, T.size, T.guides].forEach(x => x.addEventListener('input', paintTester));
  chipGroup($('#tester-style'), T.style, st => { T.style = st; paintTester(); });
  T.guides.addEventListener('change', paintTester);
  $$('.row').forEach(row => {
    row.addEventListener('click', e => {
      const b = e.target.closest('.feat'); if (!b) return;
      b.setAttribute('aria-pressed', b.getAttribute('aria-pressed') !== 'true');
      const on = $$('.feat[aria-pressed="true"]', row).map(x => `"${x.dataset.feat}"`);
      row.querySelector('.row-text').style.fontFeatureSettings = on.length ? on.join(', ') : 'normal';
    });
  });
  paintTester();

  /* ------------------------------------------------------------------ data for the characters and the accents */
  const DATA = {};
  const getData = k => DATA[k] || (DATA[k] = fetch(`data/${k}.json${CFG.q}`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }));

  /* ------------------------------------------------------------------ every character */
  const C = { face: store.get('chars-face', 'ceili'), filter: 'all', q: '', list: [], sel: -1, data: null, style: 'Regular',
    grid: $('#chars'), panel: $('#inspect'), find: $('#chars-find') };
  if (!FACES[C.face]) C.face = 'ceili';
  const isAccented = ch => { const d = ch.normalize('NFD'); return d.length > 1 && /\p{L}/u.test(d[0]); };
  function filtered() {
    const d = C.data; if (!d) return [];
    let rows = C.filter === 'alt' ? d.alts.map(a => ({ ...a, alt: true })) : d.chars.slice();
    if (C.filter === 'flyer') rows = rows.concat(d.alts.map(a => ({ ...a, alt: true }))).filter(r => d.flyer[r.g]);
    else if (C.filter === 'L') rows = rows.filter(r => r.k === 'L' && !isAccented(r.c));
    else if (C.filter === 'acc') rows = rows.filter(r => isAccented(r.c));
    else if (C.filter === 'N') rows = rows.filter(r => r.k === 'N');
    else if (C.filter === 'PS') rows = rows.filter(r => r.k === 'P' || r.k === 'S' || r.k === 'Z' || r.k === 'M');
    const raw = C.q.trim(), q = raw.toLowerCase();
    if ([...raw].length === 1) {
      // one character: that letter in both cases, then everything built on it
      const base = c => c.normalize('NFD')[0].toLowerCase();
      rows = rows.filter(r => base(r.c) === base(raw));
      rows.sort((a, b) => (b.c === raw) - (a.c === raw) || (b.c.toLowerCase() === q) - (a.c.toLowerCase() === q));
    } else if (q) {
      const hex = q.replace(/^u\+/, '');
      const words = q.split(/\s+/);
      rows = rows.filter(r => words.every(w => (r.u || '').toLowerCase().split(/\s+/).some(x => x.startsWith(w))) || r.g.toLowerCase() === q ||
        (/^[0-9a-f]{2,6}$/.test(hex) && r.cp === parseInt(hex, 16)));
    }
    return rows;
  }
  function renderChars(keepSel = false) {
    const prev = keepSel && C.list[C.sel] ? C.list[C.sel].g : null;
    C.list = filtered();
    const fam = FACES[C.face].stack, gs = styleOf(C.face, C.style);
    C.grid.textContent = '';
    C.grid.style.fontFamily = fam; C.grid.style.fontWeight = W(gs.st); C.grid.style.fontStyle = SL(gs.st);
    if (!C.list.length) { C.grid.append(el('div', { class: 'chars-empty', text: C.data ? 'Nothing matches.' : 'Loading…' })); return; }
    const frag = document.createDocumentFragment();
    C.list.forEach((r, i) => {
      const b = el('button', { type: 'button', role: 'option', class: 'cg' + (C.data.flyer[r.g] ? ' fly' : ''), 'aria-selected': 'false',
        'data-i': i, 'aria-label': r.alt ? `${r.c}, ${r.l}` : `${r.c}, ${r.u}` }, r.c,
        el('span', { class: 'cp', 'aria-hidden': 'true', text: r.alt ? r.f : r.cp.toString(16).toUpperCase().padStart(4, '0') }));
      b.tabIndex = -1;
      if (r.alt) b.style.fontFeatureSettings = featCSS(r.f);
      frag.append(b);
    });
    C.grid.append(frag);
    const j = prev ? C.list.findIndex(r => r.g === prev) : -1;
    select(j >= 0 ? j : 0, false);
  }
  function select(i, focus = true) {
    if (!C.list.length) return;
    i = Math.max(0, Math.min(C.list.length - 1, i));
    const old = C.grid.querySelector('[aria-selected="true"]'); if (old) { old.setAttribute('aria-selected', 'false'); old.tabIndex = -1; }
    const b = C.grid.querySelector(`[data-i="${i}"]`); C.sel = i;
    if (b) { b.setAttribute('aria-selected', 'true'); b.tabIndex = 0; if (focus) b.focus({ preventScroll: false }); b.scrollIntoView({ block: 'nearest' }); }
    inspect(C.list[i]);
  }
  C.grid.addEventListener('click', e => { const b = e.target.closest('.cg'); if (b) select(+b.dataset.i); });
  C.grid.addEventListener('keydown', e => {
    if (!C.list.length) return;
    const cols = Math.max(1, Math.round(C.grid.clientWidth / (C.grid.firstElementChild?.offsetWidth || 64)));
    const d = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols, ArrowUp: -cols, Home: -1e6, End: 1e6 }[e.key];
    if (d !== undefined) { e.preventDefault(); select(C.sel + d); }
  });
  $$('.chip[data-filter]').forEach(b => b.addEventListener('click', () => {
    $$('.chip[data-filter]').forEach(x => x.setAttribute('aria-pressed', x === b)); C.filter = b.dataset.filter; renderChars();
  }));
  C.find.addEventListener('input', () => { C.q = C.find.value; renderChars(); });
  chipGroup($('#chars-style'), C.style, st => { C.style = st; renderChars(true); });

  const PROV = {
    flyer: ['Printed on the 1978 flyer', 'and traced from it'],
    rebuilt: ['Rebuilt from the flyer', ''],
    composite: ['Made from the flyer’s letters', ''],
    mark: ['Mark', ''],
    made: ['Drawn to match the face', ''],
  };
  function provText(p) {
    const [cat, how] = p;
    const line = (kind, label, rest) => el('p', { class: 'insp-prov ' + kind }, el('b', { text: label }), rest);
    if (cat === 'flyer') return line('p-flyer', 'Printed on the 1978 flyer', ' and traced from it.');
    if (cat === 'rebuilt') return line('p-flyer', 'Rebuilt from the flyer: ', how + '.');
    const fromFlyer = /sheet|flyer/.test(how);
    if (cat === 'composite') return line(fromFlyer ? 'p-sheet' : 'p-made', 'Assembled: ', how + '.');
    if (fromFlyer) return line('p-sheet', 'From the flyer: ', how + '.');
    return line('p-made', 'Drawn to match: ', how + '.');
  }
  function glyphSVG(r, compact) {
    const d = C.data, upm = d.upm;
    const adv = r.a || upm * .5;
    const fs = upm * (compact ? .085 : .062);              // label size
    const gutter = fs * 5.4;                                // labels live left of the drawing
    const W = gutter + Math.max(adv, upm * .55) + upm * .16;
    const top = d.asc + 60, bot = -d.desc + 40;
    const x0 = gutter + (W - gutter - adv) / 2;
    const s = svg('svg', { viewBox: `0 ${-top} ${W} ${top + bot}`, role: 'img', 'aria-label': `${r.c} drawn large with its metric lines` });
    const lines = [['ascender', d.asc], ['x-height', d.xh], ['baseline', 0], ['descender', d.desc]];
    if (!d.unicase) lines.splice(1, 0, ['cap height', d.cap]);
    lines.forEach(([name, y]) => {
      s.append(svg('line', { x1: gutter - fs * .4, x2: W, y1: -y, y2: -y, class: name === 'baseline' ? 'm-base' : 'm-line', 'vector-effect': 'non-scaling-stroke' }));
      const t = svg('text', { x: gutter - fs * .7, y: -y + fs * .34, class: 'm-label', 'font-size': fs.toFixed(1), 'text-anchor': 'end' });
      t.textContent = name === 'cap height' ? 'cap' : name === 'x-height' ? 'x' : name === 'ascender' ? 'asc' : name === 'descender' ? 'desc' : 'base';
      s.append(t);
    });
    s.append(svg('rect', { x: x0, y: -d.asc, width: adv, height: d.asc - d.desc, class: 'm-adv', 'vector-effect': 'non-scaling-stroke' }));
    const t = svg('text', { x: x0, y: 0, 'font-size': upm, class: 'm-ink' });
    t.style.fontFamily = FACES[C.face].stack; if (r.alt) t.style.fontFeatureSettings = featCSS(r.f);
    t.textContent = r.c; s.append(t);
    return s;
  }
  function compare(r) {
    const o = C.data.flyer[r.g]; if (!o) return null;
    const [x, y, w, h] = o.r;
    // square view around the letter, so both panels line up
    const side = Math.max(w, h * .86), cx = x + w / 2, cy = y + h / 2;
    const art = svg('svg', { viewBox: `${cx - side / 2} ${cy - side * .58} ${side} ${side * 1.16}`, role: 'img',
      'aria-label': `The 1978 print of ${r.c} with the font laid over it` });
    const img = svg('image', { href: CFG.flyer, x: 0, y: 0, width: CFG.flyerSize[0], height: CFG.flyerSize[1], preserveAspectRatio: 'none' });
    const fill = svg('path', { d: o.d, class: 'cmp-fill', 'fill-rule': 'nonzero' });
    const line = svg('path', { d: o.d, class: 'cmp-line', 'vector-effect': 'non-scaling-stroke' });
    art.append(img, fill, line);
    const range = el('input', { type: 'range', min: 0, max: 100, value: store.get('cmp', 0), 'aria-label': 'Fade from the 1978 print to the font' });
    const outline = el('input', { type: 'checkbox', checked: store.get('cmp-line', true) });
    const apply = () => {
      const t = +range.value / 100;
      fill.style.opacity = t; img.style.opacity = 1 - .92 * t; line.style.display = outline.checked ? '' : 'none';
      store.set('cmp', +range.value); store.set('cmp-line', outline.checked);
    };
    range.addEventListener('input', apply); outline.addEventListener('change', apply); apply();
    const view = el('figure', { class: 'view view-print' },
      el('figcaption', {}, 'On the 1978 print', el('span', { text: `${(o.iou * 100).toFixed(1)}% overlap` })),
      el('div', { class: 'view-box' }, art));
    const ctl = el('div', { class: 'cmp-ctl' }, el('span', { text: 'Print' }), range, el('span', { text: 'Font' }),
      el('label', { class: 'switch' }, outline, el('span', { text: 'Outline' })));
    return { view, ctl };
  }
  function inspect(r) {
    const p = C.panel; p.textContent = '';
    if (!r) { p.append(el('div', { class: 'inspect-empty', text: 'Select a character.' })); return; }
    const name = r.alt ? `Alternate ${r.c} · ${r.l}` : (r.u || 'Character');
    const code = r.alt ? `${r.f} · ${r.g}` : `U+${r.cp.toString(16).toUpperCase().padStart(4, '0')} · ${r.g}`;
    const cmp = compare(r);
    const views = el('div', { class: 'views' + (cmp ? ' two' : '') },
      el('figure', { class: 'view' }, el('figcaption', { text: (cmp ? 'The font' : 'The font, with its metrics') + (C.style !== 'Regular' ? ' (regular)' : '') }),
        el('div', { class: 'view-box' }, glyphSVG(r, !!cmp))),
      cmp && cmp.view);
    const f = FACES[C.face];
    const styles = el('div', { class: 'insp-styles', 'aria-label': `${r.c} in every style of ${f.family}` },
      ...f.styles.map(st => el('figure', {},
        el('span', { class: 'g', text: r.c, style: `font-family:${f.stack};font-weight:${W(st)};font-style:${SL(st)};` +
          (r.alt ? `font-feature-settings:${featCSS(r.f)}` : '') }),
        el('figcaption', { text: st }))));
    const styleNote = f.styles.length > 1 ? el('p', { class: 'insp-note', text: 'The regular is the 1978 drawing; ' +
      (f.styles.includes('Bold') ? 'the italic, bold and bold italic were' : 'the italic was') + ' drawn from it in 2026.' }) : null;
    const unicaseNote = C.data.unicase && !r.alt && /\p{Lu}/u.test(r.c) && r.c.toLowerCase() !== r.c
      ? el('p', { class: 'insp-note', text: `${C.data.family} has one set of letters for both cases, so ${r.c} uses the same glyph as ${r.c.toLowerCase()}.` }) : null;
    p.append(...[
      el('div', { class: 'insp-head' }, el('span', { class: 'insp-name', text: name }), el('span', { class: 'insp-char', text: code })),
      views,
      cmp && cmp.ctl,
      provText(r.p),
      unicaseNote,
      styles,
      styleNote,
      el('div', { class: 'insp-nav' },
        el('button', { type: 'button', class: 'tool', 'data-step': '-1', text: '← Previous' }),
        el('button', { type: 'button', class: 'tool', 'data-step': '1', text: 'Next →' }))].filter(Boolean));
  }
  C.panel.addEventListener('click', e => { const b = e.target.closest('[data-step]'); if (b) select(C.sel + +b.dataset.step); });
  async function showChars(key) {
    C.face = key; store.set('chars-face', key); C.data = null; renderChars();
    try { C.data = await getData(key); if (C.face === key) renderChars(); }
    catch { C.grid.textContent = ''; C.grid.append(el('div', { class: 'chars-empty', text: 'Could not load the character list.' })); }
  }
  tabHandlers.chars = showChars;

  /* ------------------------------------------------------------------ the accent sets on the flyer */
  const PIECE = {
    acute: ['fada (acute)', 'á'], tilde: ['tilde', 'ñ'], 'dieresis.l': ['diaeresis', 'ä'], 'dieresis.r': ['diaeresis', 'ä'],
    dot: ['dot of the séimhiú', 'ḃ'], ring: ['ring', 'å'], 'ring.b': ['ring, second copy', 'å'], circumflex: ['circumflex', 'â'],
    caron: ['háček', 'ž'], 'guil.r1': ['guillemets', '»'], 'guil.r2': ['guillemets', '»'], 'guil.l1': ['guillemets', '«'],
    'guil.l2': ['guillemets', '«'], emdash: ['em dash', '—'], endash: ['en dash', '–'], ringdot: ['a ring and a diaeresis dot, joined by ink', 'ä'],
  };
  async function drawAccents(fig) {
    const key = fig.dataset.acc; let d;
    try { d = await getData(key); } catch { return; }
    if (!d.pieces) return;
    const [x, y, w, h] = d.pieces.r;
    const art = svg('svg', { viewBox: `${x} ${y} ${w} ${h}`, role: 'img', 'aria-label': `${d.family}’s accent set on the 1978 flyer, numbered` });
    art.append(svg('image', { href: CFG.flyer, x: 0, y: 0, width: CFG.flyerSize[0], height: CFG.flyerSize[1], preserveAspectRatio: 'none' }));
    const legend = $('.acc-legend', fig); legend.textContent = '';
    const nums = {}; let n = 0;
    d.pieces.pts.forEach(pt => {
      const [label, ex] = PIECE[pt.n] || [pt.n, ''];
      const lk = label + ex;
      if (!(lk in nums)) {
        nums[lk] = ++n;
        const li = el('li', {}, el('span', { class: 'n', text: n }), el('span', { text: label }), el('span', { class: 'ex', text: ex }));
        li.querySelector('.ex').style.fontFamily = FACES[key].stack;
        legend.append(li);
      }
      const k = nums[lk];
      const g = svg('g'); const c = svg('circle', { cx: pt.x + 2.6, cy: pt.y - 2.6, r: 1.9, class: 'acc-pin' });
      const t = svg('text', { x: pt.x + 2.6, y: pt.y - 2.5, class: 'acc-pin-t' }); t.textContent = k;
      g.append(c, t); art.append(g);
    });
    const box = $('.acc-art', fig); box.textContent = ''; box.append(art);
  }

  /* lazy: fetch data when the sections come near the screen */
  const lazy = new IntersectionObserver(entries => entries.forEach(en => {
    if (!en.isIntersecting) return;
    lazy.unobserve(en.target);
    if (en.target.id === 'characters') selectTab('chars', C.face);
    else drawAccents(en.target);
  }), { rootMargin: '600px 0px' });
  lazy.observe($('#characters'));
  $$('.acc').forEach(f => lazy.observe(f));

  /* ------------------------------------------------------------------ the web snippet, the browser check */
  const cssURL = new URL('css/four-irish-typefaces.css', document.baseURI).href;
  if (location.protocol.startsWith('http')) $('#css-url').textContent = cssURL;
  $$('[data-copy]').forEach(b => b.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($(b.dataset.copy).textContent); flash(b, 'Copied'); } catch { flash(b, 'Select and copy'); }
  }));
  async function check() {
    const rows = $('#check-rows'); let ok = 0;
    const res = performance.getEntriesByType('resource');
    let fonts = 0, styles = 0;
    for (const k of ORDER) {
      const f = FACES[k];
      let n = 0;
      for (const st of f.styles) {
        try { if ((await document.fonts.load(`${SL(st)} ${W(st)} 32px ${f.stack}`, 'a')).length > 0) n++; } catch { /* not loaded */ }
      }
      const loaded = n === f.styles.length; fonts += n; styles += f.styles.length;
      const hit = res.filter(r => r.name.includes(`/${f.file}-Regular.`)).pop();
      const fmt = hit ? (hit.name.includes('.woff2') ? 'WOFF2' : hit.name.includes('.woff') ? 'WOFF' : 'TTF') : (loaded ? 'cached' : '–');
      const size = hit && hit.encodedBodySize ? `${(hit.encodedBodySize / 1024).toFixed(1)} KB` : (hit && hit.transferSize === 0 ? 'from cache' : '–');
      if (loaded) ok++;
      const td = el('td', { text: f.family }); td.style.fontFamily = f.stack;
      rows.append(el('tr', {}, td, el('td', { text: `${n} of ${f.styles.length}` }), el('td', { text: fmt }), el('td', { text: size })));
    }
    const v = $('#check-verdict');
    v.textContent = ok === ORDER.length ? `All ${styles} fonts loaded. They will work in this browser.` : `${fonts} of ${styles} fonts loaded.`;
    v.classList.toggle('ok', ok === ORDER.length);
    const a = $('#kern-a').getBoundingClientRect().width, b = $('#kern-b').getBoundingClientRect().width;
    $('#kern-result').textContent = Math.abs(a - b) > 1 ? 'Kerning is applied in this browser: P. F. V, LV close up.' : 'Kerning was not detected.';
  }
  document.fonts.ready.then(check);

  /* ------------------------------------------------------------------ downloads in the preview */
  if (CFG.pack) {
    $$('[data-full]').forEach(n => { n.hidden = true; });
    const CRC = new Uint32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
    const crc32 = u8 => { let c = 0xFFFFFFFF; for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
    const deflate = async u8 => {
      if (typeof CompressionStream !== 'function') return null;
      try { return new Uint8Array(await new Response(new Blob([u8]).stream().pipeThrough(new CompressionStream('deflate-raw'))).arrayBuffer()); }
      catch { return null; }
    };
    const bytes = async path => { const r = await fetch(path); if (!r.ok) throw new Error('fetch'); return new Uint8Array(await r.arrayBuffer()); };
    async function makeZip(entries) {
      const enc = new TextEncoder(), parts = [], central = [];
      const time = 12 << 11, date = ((2026 - 1980) << 9) | (10 << 5) | 18;
      let offset = 0;
      for (const [zname, src] of entries) {
        const data = await bytes(src), name = enc.encode(zname), crc = crc32(data), packed = await deflate(data);
        const deflated = packed && packed.length < data.length, body = deflated ? packed : data, method = deflated ? 8 : 0;
        const h = new DataView(new ArrayBuffer(30));
        h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint16(8, method, true);
        h.setUint16(10, time, true); h.setUint16(12, date, true); h.setUint32(14, crc, true); h.setUint32(18, body.length, true);
        h.setUint32(22, data.length, true); h.setUint16(26, name.length, true);
        parts.push(new Uint8Array(h.buffer), name, body);
        const c = new DataView(new ArrayBuffer(46));
        c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
        c.setUint16(10, method, true); c.setUint16(12, time, true); c.setUint16(14, date, true); c.setUint32(16, crc, true);
        c.setUint32(20, body.length, true); c.setUint32(24, data.length, true); c.setUint16(28, name.length, true); c.setUint32(42, offset, true);
        central.push(new Uint8Array(c.buffer), name);
        offset += 30 + name.length + body.length;
      }
      const size = central.reduce((n, p) => n + p.length, 0), end = new DataView(new ArrayBuffer(22));
      end.setUint32(0, 0x06054b50, true); end.setUint16(8, entries.length, true); end.setUint16(10, entries.length, true);
      end.setUint32(12, size, true); end.setUint32(16, offset, true);
      return new Blob([...parts, ...central, new Uint8Array(end.buffer)], { type: 'application/zip' });
    }
    $$('a[href$=".zip"], a[href$=".pdf"]').forEach(a => a.addEventListener('click', async e => {
      e.preventDefault();
      const label = a.querySelector('b') || a, was = label.textContent, pdf = a.getAttribute('href').endsWith('.pdf');
      label.textContent = pdf ? 'Preparing the PDF…' : 'Packing the fonts…';
      try {
        const blob = pdf ? new Blob([await bytes(a.getAttribute('href'))], { type: 'application/pdf' }) : await makeZip(CFG.pack.entries);
        const r = await saveFile(pdf ? 'Four-Irish-Typefaces-specimen.pdf' : CFG.pack.name, blob);
        label.textContent = r && r.status === 'saved' ? 'Saved' : was;
      } catch (err) {
        label.textContent = err && err.code === 'declined' ? was : 'Couldn’t save here';
      }
      setTimeout(() => { label.textContent = was; }, 2200);
    }));
  }

  /* ------------------------------------------------------------------ the flyer, close up */
  const lb = $('#lightbox'); let z = 1;
  $$('[data-open-flyer]').forEach(b => b.addEventListener('click', () => { if (lb.showModal) lb.showModal(); else window.open(CFG.flyer); }));
  $('.lightbox-close', lb).addEventListener('click', () => lb.close());
  lb.addEventListener('click', e => { if (e.target === lb) lb.close(); });
  $$('[data-zoom]', lb).forEach(b => b.addEventListener('click', () => {
    z = Math.max(1, Math.min(4, z * (b.dataset.zoom > 0 ? 1.5 : 1 / 1.5))); $('#lightbox-view').style.setProperty('--z', z.toFixed(3));
  }));
})();
