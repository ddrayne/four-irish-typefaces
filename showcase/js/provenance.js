import { $, $$, FACES, NAME } from './util.js';

// Where each glyph of a Regular comes from: a map of the whole glyph set, marked by class
// (traced, built, modern), and for the chosen glyph the print behind it, what the research
// recorded and every judged correction that names it. All of it is read from
// data/provenance/<face>.json, which scripts/showcase_provenance.py writes from the research
// files: nothing is stated here that those files do not say. No archive pixels are shown.

const CLASS = { a: 'Traced from a 1978 print', r: 'Built from the prints', m: 'Modern, drawn to match' };
const BASIS = { sheet: 'many impressions', two: 'two prints', one: 'one print', kept: 'kept from the flyer' };
const STYLE = { bold: 'bold styles', sloped: 'sloped styles' };
const KIND = { 'original-specimen': 'trace', flyer: 'trace kept from the flyer', composite: 'letter and mark', mark: 'mark', made: 'made', rebuilt: 'rebuilt' };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const hex = (cp) => cp.toString(16).toUpperCase().padStart(4, '0');

export function init(root, site) {
  const facesHost = $('[data-pv-faces]', root);
  const map = $('[data-pv-map]', root);
  const detail = $('[data-pv-detail]', root);
  const count = $('[data-pv-count]', root);
  const more = $('[data-pv-more]', root);
  const srcSel = $('[data-pv-src]', root);
  const basisSel = $('[data-pv-basis]', root);
  const fixed = $('[data-pv-fixed]', root);
  const dis = $('[data-pv-dis]', root);
  const keys = $$('[data-pv-class]', root);
  const cache = {};
  let face = 'kilfane', data = null, picked = null, byName = {};

  const fromHash = () => {
    const m = location.hash.match(/^#provenance\/([a-z]+)(?:\/(.+))?$/);
    return m && FACES.includes(m[1]) ? [m[1], m[2] ? decodeURIComponent(m[2]) : null] : null;
  };

  FACES.forEach((k) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'tog t-face'; b.setAttribute('role', 'radio');
    b.innerHTML = `<span class="f-${k}">${NAME[k]}</span>`;
    b.addEventListener('click', () => load(k));
    facesHost.appendChild(b);
  });

  const label = (g) => {
    const name = g.u ? site.names[hex(g.u)] : null;
    return name ? name.toLowerCase() + (g.set ? `, ${g.set} form` : '') : g.n === 'space' ? 'word space' : `glyph ${g.n}`;
  };

  // One glyph as an SVG: font units, y up, centred on its ink in a square as tall as the line.
  function art(g, cls) {
    const [, asc, desc] = data.m;
    let side = (asc - desc) * 1.06;
    if (!g.b) return `<svg class="${cls}" viewBox="0 0 10 10" aria-hidden="true" focusable="false"></svg>`;
    const w = g.b[2] - g.b[0];
    side = Math.max(side, w * 1.12, (g.b[3] - g.b[1]) * 1.12);
    const cx = (g.b[0] + g.b[2]) / 2;
    // marks and signs far from the line are centred on their own ink; letters keep their place on the line
    const mid = (asc + desc) / 2, own = (g.b[1] + g.b[3]) / 2;
    const cy = g.b[3] > asc + side * 0.03 || g.b[1] < desc - side * 0.03 ? own : mid;
    const x0 = cx - side / 2;
    // the large drawing carries the baseline and the x-height
    const lines = cls === 'pv-big-art' ? [0, data.m[4]].map((y) => `<line x1="${x0}" x2="${x0 + side}" y1="${-y}" y2="${-y}"/>`).join('') : '';
    return `<svg class="${cls}" viewBox="${x0} ${-cy - side / 2} ${side} ${side}" aria-hidden="true" focusable="false">${lines}` +
      `<path transform="scale(1 -1)" d="${g.d}"/></svg>`;
  }

  async function load(k, name) {
    face = k;
    [...facesHost.children].forEach((c, i) => c.setAttribute('aria-checked', String(FACES[i] === k)));
    map.setAttribute('aria-busy', 'true');
    try {
      cache[k] ||= await fetch(`data/provenance/${k}.json`).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
    } catch (err) {
      map.removeAttribute('aria-busy');
      count.textContent = 'The provenance data could not be loaded.';
      throw err;
    }
    if (face !== k) return;                     // another face was chosen meanwhile
    data = cache[k];
    byName = Object.fromEntries(data.glyphs.map((g) => [g.n, g]));
    map.removeAttribute('aria-busy');

    srcSel.replaceChildren(new Option('Any print', ''), ...data.sources.map((s) => new Option(s.id === 'flyer' ? 'The flyer scan' : `${s.id} · ${s.title || ''}`, s.id)));
    basisSel.value = ''; fixed.setAttribute('aria-pressed', 'false'); dis.setAttribute('aria-pressed', 'false');
    dis.hidden = !data.glyphs.some((g) => g.dis);
    keys.forEach((b) => b.setAttribute('aria-pressed', 'true'));
    for (const c of 'arm') $(`[data-pv-n="${c}"]`, root).textContent = data.counts[c];

    const frag = document.createDocumentFragment();
    for (const g of data.glyphs) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'pv-cell'; b.dataset.n = g.n; b.dataset.c = g.c;
      b.setAttribute('role', 'option'); b.setAttribute('aria-selected', 'false'); b.tabIndex = -1;
      b.setAttribute('aria-label', `${label(g)}: ${CLASS[g.c].toLowerCase()}${g.rules ? ', corrected' : ''}`);
      b.innerHTML = art(g, 'pv-art') + (g.rules ? '<i class="pv-dot" aria-hidden="true"></i>' : '');
      frag.appendChild(b);
    }
    map.replaceChildren(frag);
    map.scrollTop = 0;
    facewide();
    filter();
    const first = byName[name] || data.glyphs.find((g) => g.u && String.fromCodePoint(g.u) === name) ||
      byName[{ kilfane: 'G', carrick: 'e', tuam: 'h', ceili: 'ampersand' }[k]] || data.glyphs[0];
    show(first.n, false);
    const cell = cellOf(first.n);
    if (cell) map.scrollTop = Math.max(0, cell.offsetTop - (map.clientHeight - cell.offsetHeight) / 2);
  }

  const cellOf = (n) => map.querySelector(`[data-n="${CSS.escape(n)}"]`);
  const open = () => [...map.children].filter((c) => !c.disabled);

  function filter() {
    const on = new Set(keys.filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.dataset.pvClass));
    const src = srcSel.value, basis = basisSel.value;
    const wantFixed = fixed.getAttribute('aria-pressed') === 'true', wantDis = dis.getAttribute('aria-pressed') === 'true';
    let n = 0;
    for (const c of map.children) {
      const g = byName[c.dataset.n];
      const ok = on.has(g.c) && (!src || (g.src || []).includes(src)) && (!basis || g.basis === basis) &&
        (!wantFixed || !!g.rules) && (!wantDis || !!g.dis);
      c.disabled = !ok;
      n += ok;
    }
    const total = data.glyphs.length;
    count.textContent = n === total
      ? `${total} glyphs in ${NAME[face]} ${data.v} · ${data.counts.a} traced · ${data.counts.r} built · ${data.counts.m} modern`
      : `${n} of ${total} glyphs shown`;
    const cur = picked && cellOf(picked);
    for (const c of map.children) c.tabIndex = -1;
    const stop = cur && !cur.disabled ? cur : open()[0];
    if (stop) stop.tabIndex = 0;
  }

  function show(n, link = true) {
    const g = byName[n];
    if (!g) return;
    picked = n;
    for (const c of map.children) {
      const sel = c.dataset.n === n;
      c.setAttribute('aria-selected', String(sel));
      if (!c.disabled) c.tabIndex = sel ? 0 : -1;
    }
    if (link) history.replaceState(null, '', `#provenance/${face}/${encodeURIComponent(n)}`);
    const src = (id) => data.sources.find((s) => s.id === id) || { id };
    const file = (path, text) => (path ? `<a href="${site.repo}/blob/main/${path}">${text}</a>` : '');
    const chip = (name) => {
      const p = byName[name];
      return p ? `<button type="button" class="pv-part" data-go="${esc(name)}">${art(p, 'pv-part-art')}<span class="mono">${esc(name)}</span></button>` : '';
    };

    const title = g.u ? site.names[hex(g.u)] || `U+${hex(g.u)}` : g.n === '.notdef' ? 'The missing-character box' : 'No character of its own';
    const basis = g.c !== 'a' ? '' : g.basis ? `<p class="pv-basis"><span class="mono">Basis</span> ${BASIS[g.basis] || g.basis}</p>`
      : '<p class="pv-basis"><span class="mono">Basis</span> not recorded</p>';

    let how;
    if (g.c === 'a' && g.facts?.length) how = '';       // the evidence below says it more exactly than the record's one line
    else if (g.how) how = `<p>${esc(g.how[0].toUpperCase() + g.how.slice(1))}${/[.!?]$/.test(g.how) ? '' : '.'}</p>`;
    else if (g.of) how = `<p>A form of <b>${esc(g.of)}</b> added for the release. ${data.study}’s build record does not list it; the corrections below are what the research says of it.</p>`;
    else how = `<p>Not recorded: ${data.study}’s build record does not list this glyph${g.rules ? '. The corrections below are what the research says of it' : ''}.</p>`;

    const sources = (g.src || []).map((id) => {
      const s = src(id);
      const text = `${esc(id === 'flyer' ? 'Flyer' : id)}${s.title ? ` · ${esc(s.title)}` : ''}`;
      return s.url ? `<a class="pv-src" href="${esc(s.url)}"${s.url.startsWith('#') ? '' : ' rel="noopener"'}>${text}${s.url.startsWith('#') ? '' : ' <span aria-hidden="true">↗</span>'}</a>` : `<span class="pv-src">${text}</span>`;
    }).join('');

    const facts = (g.facts || []).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('');
    const notes = (g.notes || []).map((t) => `<li>${esc(t)}</li>`).join('');
    const parts = (g.parts || (g.of ? [g.of] : [])).map(chip).join('');

    const rules = (g.rules || []).map(([i, nums, own]) => {
      const r = data.rules[i];
      return `<li><p class="pv-rule-h mono">${esc(r.label)}${r.style ? ` <span class="pv-tag">${STYLE[r.style]}</span>` : ''}</p>` +
        (own ? '' : '<p class="pv-rule-own">This entry gives no reason of its own. The entry it follows in the file says:</p>') +
        `<p>${r.reason ? esc(r.reason) : 'Reason not recorded.'}</p>` +
        (nums || r.nums ? `<p class="pv-nums mono">${[nums && `this glyph: ${esc(nums)}`, r.nums && `rule: ${esc(r.nums)}`].filter(Boolean).join(' · ')}</p>` : '') + '</li>';
    }).join('');

    detail.innerHTML = `
      <div class="pv-head">
        <div class="pv-big" data-c="${g.c}">${art(g, 'pv-big-art')}</div>
        <div class="pv-id">
          <p class="pv-class"><span class="pv-sw" data-c="${g.c}" aria-hidden="true"></span>${CLASS[g.c]}</p>
          <h3 class="pv-name">${esc(title)}</h3>
          <p class="mono pv-code">${g.u ? `U+${hex(g.u)} · ` : ''}${esc(g.n)}${g.set ? ` · ${esc(g.set)}` : ''}${g.k ? ` · ${KIND[g.k] || esc(g.k)}` : ''}</p>
          ${basis}
        </div>
      </div>
      <section><h4>${g.c === 'a' ? 'Traced from' : 'How it is made'}</h4>${how}
        ${sources ? `<p class="pv-srcs">${sources}</p>` : ''}
        ${parts ? `<div class="pv-parts"><span class="mono">${g.of ? 'A form of' : 'Made from'}</span>${parts}</div>` : ''}</section>
      ${facts || notes ? `<section><h4>${g.traced ? 'The print’s own drawing of it' : 'What the research recorded'}</h4>
        ${facts ? `<dl class="pv-facts">${facts}</dl>` : ''}${notes ? `<ul class="pv-notes">${notes}</ul>` : ''}</section>` : ''}
      <section><h4>Judged corrections${g.rules ? ` <span class="mono">${g.rules.length}</span>` : ''}</h4>
        ${rules ? `<ol class="pv-rules">${rules}</ol>` : `<p class="pv-none">None names this glyph${g.parts ? '; its parts may have their own' : ''}.</p>`}</section>
      <p class="pv-files mono">${[file(data.files.record, 'build record'), file(data.files.evidence, 'evidence'), file(data.files.edits, 'corrections')].filter(Boolean).join(' · ')}</p>`;
    detail.scrollTop = 0;
  }

  // Rules that list no glyph (spacing, the whole face, the other styles), and what the evidence cannot say.
  function facewide() {
    const wide = data.rules.filter((r) => !r.n);
    const item = (r) => `<li><p class="pv-rule-h mono">${esc(r.label)}${r.style ? ` <span class="pv-tag">${STYLE[r.style]}</span>` : ''}</p><p>${esc(r.reason || '')}</p>` +
      (r.nums ? `<p class="pv-nums mono">${esc(r.nums)}</p>` : '') + '</li>';
    more.innerHTML =
      (wide.length ? `<details><summary><span>${wide.length} corrections that name no single glyph</span><span class="mono">${NAME[face]} · spacing, whole-face rules, other styles</span></summary><ol class="pv-rules">${wide.map(item).join('')}</ol></details>` : '') +
      (data.limits.length ? `<details><summary><span>What the evidence cannot say</span><span class="mono">${data.study}</span></summary><ul class="pv-notes">${data.limits.map((t) => `<li>${esc(t)}</li>`).join('')}</ul></details>` : '');
  }

  map.addEventListener('click', (e) => { const b = e.target.closest('.pv-cell'); if (b && !b.disabled) show(b.dataset.n); });
  map.addEventListener('keydown', (e) => {
    const cur = e.target.closest('.pv-cell');
    if (!cur) return;
    const cells = open(), i = cells.indexOf(cur);
    let to = null;
    if (e.key === 'ArrowRight') to = cells[i + 1];
    else if (e.key === 'ArrowLeft') to = cells[i - 1];
    else if (e.key === 'Home') to = cells[0];
    else if (e.key === 'End') to = cells[cells.length - 1];
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      // the nearest open cell in the next row that has one
      const here = cur.getBoundingClientRect(), down = e.key === 'ArrowDown';
      let best = Infinity, row = null;
      for (const c of down ? cells.slice(i + 1) : cells.slice(0, i).reverse()) {
        const r = c.getBoundingClientRect();
        if (Math.abs(r.top - here.top) < 2) continue;
        if (row === null) row = r.top;
        if (Math.abs(r.top - row) > 2) break;
        const dx = Math.abs(r.left - here.left);
        if (dx < best) { best = dx; to = c; }
      }
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault(); show(cur.dataset.n); detail.focus(); return;
    } else return;
    e.preventDefault();
    if (to) { show(to.dataset.n); to.focus(); }
  });
  detail.addEventListener('click', (e) => {
    const b = e.target.closest('[data-go]');
    if (!b) return;
    const n = b.dataset.go, cell = cellOf(n);
    if (cell?.disabled) { keys.forEach((k) => k.setAttribute('aria-pressed', 'true')); srcSel.value = ''; basisSel.value = ''; fixed.setAttribute('aria-pressed', 'false'); dis.setAttribute('aria-pressed', 'false'); filter(); }
    show(n);
    cell?.scrollIntoView({ block: 'nearest' });
    detail.focus();
  });
  for (const b of [...keys, fixed, dis]) b.addEventListener('click', () => { b.setAttribute('aria-pressed', String(b.getAttribute('aria-pressed') !== 'true')); filter(); });
  srcSel.addEventListener('change', filter);
  basisSel.addEventListener('change', filter);
  addEventListener('hashchange', () => { const h = fromHash(); if (h) load(h[0], h[1] || picked); });

  const h = fromHash();
  return load(h ? h[0] : face, h ? h[1] : null);
}
