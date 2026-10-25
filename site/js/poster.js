import { $, $$, FACES, NAME } from './util.js';
import { loadFont } from './poster-type.js';
import { compose, LAYOUTS, PRESETS, INKS, PAPERS, SIZES, FINISHES } from './poster-layouts.js';
import { raster, svg, pdf } from './poster-render.js';

// The poster maker: ready-made posters to start from, words, a layout, a face and an
// ink for each plate, paper, finish, and the poster saved at its print size as a PNG,
// or as clean vectors in an SVG or a PDF with each ink's plate on its own page.

const STYLES = { ceili: ['Regular', 'Italic', 'Bold', 'Bold Italic'], kilfane: ['Regular', 'Italic', 'Bold', 'Bold Italic'], carrick: ['Regular', 'Italic'], tuam: ['Regular', 'Italic'] };
const byId = (list, id) => list.find((x) => x.id === id) || list[0];
const MAX_PX = 16_700_000;        // the largest canvas every browser will draw (iOS caps at 16.7 MP)

// little drawings of each layout, in the chosen inks
const ICON = {
  sun: '<circle class="i1" cx="15" cy="14" r="11"/><rect class="i2" x="4" y="21" width="22" height="6"/><rect class="i2" x="8" y="30" width="14" height="3"/>',
  initial: '<path class="i1" d="M5 3h20v7H14v5h9v6h-9v15H5z"/><rect class="i2" x="3" y="26" width="24" height="5"/><rect class="i2" x="3" y="33" width="15" height="3"/>',
  stack: '<rect class="i1" x="3" y="3" width="24" height="9"/><rect class="i2" x="3" y="14" width="24" height="7"/><rect class="i1" x="3" y="23" width="24" height="9"/><rect class="i2" x="3" y="35" width="16" height="3"/>',
  shadow: '<rect class="i1" x="0" y="0" width="30" height="26"/><rect class="ip" x="4" y="6" width="20" height="5"/><rect class="ip" x="4" y="14" width="14" height="5"/><rect class="i2" x="6" y="8" width="20" height="5"/><rect class="i2" x="6" y="16" width="14" height="5"/><rect class="i2" x="4" y="31" width="20" height="3"/>',
  two: '<rect class="i1" x="3" y="6" width="24" height="10"/><rect class="i2" x="5" y="9" width="22" height="9"/><rect class="i1" x="3" y="21" width="24" height="10"/><rect class="i2" x="3" y="24" width="20" height="9"/>',
  repeat: '<rect class="i1" x="-4" y="3" width="16" height="5"/><rect class="i1" x="14" y="3" width="16" height="5"/><rect class="i2" x="4" y="7" width="16" height="5"/><rect class="i2" x="22" y="7" width="16" height="5"/><rect class="i1" x="-8" y="11" width="16" height="5"/><rect class="i1" x="10" y="11" width="16" height="5"/><rect class="i2" x="0" y="15" width="16" height="5"/><rect class="i2" x="18" y="15" width="16" height="5"/><rect class="i1" x="-2" y="19" width="16" height="5"/><rect class="i1" x="16" y="19" width="16" height="5"/><rect class="i1" x="4" y="32" width="20" height="3"/>',
  tiles: '<rect class="i1" x="3" y="3" width="8" height="8"/><rect class="i1" x="19" y="3" width="8" height="8"/><rect class="i1" x="11" y="11" width="8" height="8"/><rect class="i1" x="3" y="19" width="8" height="8"/><rect class="i1" x="19" y="19" width="8" height="8"/><rect class="i2" x="13" y="5" width="4" height="4"/><rect class="i2" x="5" y="13" width="4" height="4"/><rect class="i2" x="21" y="13" width="4" height="4"/><rect class="i2" x="13" y="21" width="4" height="4"/><rect class="i2" x="3" y="32" width="18" height="3"/>',
  halftone: '<g class="i1"><circle cx="5" cy="4" r="3.4"/><circle cx="12" cy="4" r="3.4"/><circle cx="19" cy="4" r="3.4"/><circle cx="26" cy="4" r="3.4"/><circle cx="8.5" cy="10" r="2.6"/><circle cx="15.5" cy="10" r="2.6"/><circle cx="22.5" cy="10" r="2.6"/><circle cx="5" cy="16" r="1.8"/><circle cx="12" cy="16" r="1.8"/><circle cx="19" cy="16" r="1.8"/><circle cx="26" cy="16" r="1.8"/><circle cx="8.5" cy="22" r="1"/><circle cx="15.5" cy="22" r="1"/><circle cx="22.5" cy="22" r="1"/></g><rect class="i2" x="3" y="25" width="24" height="6"/><rect class="i2" x="3" y="34" width="14" height="3"/>',
  upright: '<rect class="i2" x="0" y="0" width="11" height="42"/><rect class="i1" x="4" y="3" width="10" height="36"/><rect class="i1" x="18" y="4" width="9" height="3"/><rect class="i1" x="18" y="9" width="7" height="3"/><rect class="i2" x="18" y="36" width="9" height="2"/>',
  specimen: '<rect class="i1" x="3" y="3" width="24" height="7"/><rect class="i2" x="3" y="13" width="24" height="1.5"/><path class="i1" d="M3 30l5-13h3l5 13h-3l-1-3h-5l-1 3zM8.5 24.5h3l-1.5-4z"/><rect class="i2" x="18" y="18" width="9" height="3"/><rect class="i2" x="3" y="33" width="24" height="2"/><rect class="i2" x="3" y="37" width="20" height="2"/>',
};

export async function init(root) {
  const view = $('[data-poster-canvas]', root);
  const cap = $('[data-poster-cap]', root);
  const head = $('[data-poster-head]', root), sub = $('[data-poster-sub]', root), foot = $('[data-poster-foot]', root);
  const S = {
    layout: 'sun', type: [{ face: 'tuam', style: 'Regular' }, { face: 'ceili', style: 'Regular' }],
    inks: ['pink', 'medium-blue'], paper: 'natural', size: 'a3', finish: 'riso', seed: 1978,
    tags: { ceili: [], kilfane: [] },
  };
  const noSave = !!document.querySelector('[data-no-downloads]');

  // ---------------------------------------------------------------- controls
  let uid = 0;
  function picks(host, name, items, get, set, render, cls = '') {
    host.replaceChildren(...items.map((it) => {
      const lab = document.createElement('label');
      lab.className = `pick ${cls}`;
      const inp = document.createElement('input');
      inp.type = 'radio'; inp.name = name; inp.value = it.id; inp.className = 'pick-in';
      inp.id = `pk-${name}-${it.id}-${++uid}`;
      inp.checked = it.id === get();
      inp.addEventListener('change', () => { if (inp.checked) { set(it.id); changed(); } });
      const face = document.createElement('span');
      face.className = 'pick-face';
      face.innerHTML = render(it);
      lab.append(inp, face);
      if (it.hex) lab.title = it.name;
      return lab;
    }));
  }
  const sync = (host, id) => { const inp = host.querySelector(`input[value="${CSS.escape(id)}"]`); if (inp) inp.checked = true; };

  const layoutHost = $('[data-poster-layouts]', root);
  picks(layoutHost, 'p-layout', LAYOUTS, () => S.layout, (v) => { S.layout = v; },
    (l) => `<svg class="pick-icon" viewBox="0 0 30 42" aria-hidden="true">${ICON[l.id]}</svg><span>${l.name}</span>`, 'pick-layout');

  const typeRows = $$('[data-poster-type]', root);
  const inkRows = $$('[data-poster-ink]', root);
  const altsHost = $('[data-poster-alts]', root);
  const styleSel = [];
  typeRows.forEach((row, n) => {
    const label = document.createElement('p'); label.className = 'ctl-k'; label.textContent = n ? 'Second ink' : 'First ink';
    const faces = document.createElement('div'); faces.className = 'picks picks-face';
    const sel = document.createElement('select'); sel.id = `poster-style-${n}`; sel.className = 'style-sel';
    const selLab = document.createElement('label'); selLab.className = 'sel-wrap';
    selLab.innerHTML = `<span class="vh">${n ? 'Second' : 'First'} ink's style</span>`;
    selLab.append(sel);
    sel.addEventListener('change', () => { S.type[n].style = sel.value; changed(); });
    row.append(label, faces, selLab);
    picks(faces, `p-face-${n}`, FACES.map((k) => ({ id: k, name: NAME[k] })), () => S.type[n].face,
      (v) => { S.type[n].face = v; if (!STYLES[v].includes(S.type[n].style)) S.type[n].style = 'Regular'; },
      (f) => `<span class="f-${f.id}">${f.name}</span>`, 'pick-chip');
    styleSel.push(sel);
  });
  function fillStyles() {
    styleSel.forEach((sel, n) => {
      const t = S.type[n];
      sel.replaceChildren(...STYLES[t.face].map((st) => { const o = document.createElement('option'); o.value = st; o.textContent = st; return o; }));
      sel.value = t.style;
    });
  }
  let altFonts = {};
  async function fillAlts() {
    const faces = [...new Set(S.type.map((t) => t.face))].filter((f) => S.tags[f]);
    const fonts = await Promise.all(faces.map((f) => loadFont(f)));
    altFonts = Object.fromEntries(faces.map((f, i) => [f, fonts[i]]));
    altsHost.replaceChildren(...faces.flatMap((f) => altFonts[f].sets.map((set) => {
      const lab = document.createElement('label'); lab.className = 'chk';
      const inp = document.createElement('input'); inp.type = 'checkbox'; inp.checked = S.tags[f].includes(set.tag);
      inp.addEventListener('change', () => {
        S.tags[f] = inp.checked ? [...S.tags[f], set.tag] : S.tags[f].filter((t) => t !== set.tag);
        changed();
      });
      lab.append(inp, ` ${NAME[f]}: ${set.label}`);
      return lab;
    })));
    altsHost.hidden = !altsHost.children.length;
  }

  inkRows.forEach((row, n) => {
    const label = document.createElement('p'); label.className = 'ctl-k';
    const sw = document.createElement('div'); sw.className = 'picks picks-ink';
    row.append(label, sw);
    picks(sw, `p-ink-${n}`, INKS, () => S.inks[n], (v) => { S.inks[n] = v; },
      (i) => `<span class="dot" style="background:${i.hex}"></span><span class="vh">${i.name}</span>`, 'pick-swatch');
  });
  const papersHost = $('[data-poster-papers]', root), sizesHost = $('[data-poster-sizes]', root), finHost = $('[data-poster-finishes]', root);
  picks(papersHost, 'p-paper', PAPERS, () => S.paper, (v) => { S.paper = v; },
    (p) => `<span class="dot dot-paper" style="background:${p.hex}"></span><span class="vh">${p.name}</span>`, 'pick-swatch');
  picks(sizesHost, 'p-size', SIZES, () => S.size, (v) => { S.size = v; }, (z) => `<span>${z.name}</span>`, 'pick-chip');
  picks(finHost, 'p-finish', FINISHES, () => S.finish, (v) => { S.finish = v; }, (f) => `<span>${f.name}</span>`, 'pick-chip');

  $('[data-poster-swap]', root).addEventListener('click', () => {
    S.inks.reverse();
    inkRows.forEach((row, n) => sync(row, S.inks[n]));
    changed();
  });
  $('[data-poster-shift]', root).addEventListener('click', () => { S.seed = (S.seed * 31 + 7) % 99991; changed(); });

  // ---------------------------------------------------------------- drawing
  const sheet = () => byId(SIZES, S.size);
  async function doc(state = S, words = { head: head.value, sub: sub.value, foot: foot.value }) {
    const z = byId(SIZES, state.size);
    const fonts = await Promise.all(state.type.map((t) => loadFont(t.face, t.style)));
    const W = 1000, H = Math.round(1000 * z.mm[1] / z.mm[0] * 10) / 10;
    const sp = (n) => ({ font: fonts[n], tags: state.tags[state.type[n].face] || [] });
    return { W, H, plates: compose({ W, H, ...words, a: sp(0), b: sp(1) }, state.layout) };
  }
  const inkHex = (state = S) => state.inks.map((i) => byId(INKS, i).hex);
  const inkName = (state = S) => state.inks.map((i) => byId(INKS, i).name);

  function describe() {
    const z = sheet(), L = byId(LAYOUTS, S.layout);
    const [i1, i2] = inkName();
    const faces = S.type.map((t) => `${NAME[t.face]}${t.style === 'Regular' ? '' : ` ${t.style}`}`);
    const typeText = faces[0] === faces[1] ? faces[0] : `${faces[0]} and ${faces[1]}`;
    cap.textContent = `${z.name} · ${z.inches || `${z.mm[0]} × ${z.mm[1]} mm`} · ${i1} and ${i2} on ${byId(PAPERS, S.paper).name.toLowerCase()} paper`;
    view.setAttribute('aria-label', `Poster preview, ${L.name} layout: “${head.value.replace(/\s+/g, ' ').trim()}” in ${typeText}, printed in ${i1} and ${i2}.`);
    root.style.setProperty('--ink1', byId(INKS, S.inks[0]).hex);
    root.style.setProperty('--ink2', byId(INKS, S.inks[1]).hex);
    root.style.setProperty('--paper-c', byId(PAPERS, S.paper).hex);
    root.style.setProperty('--ratio', String(z.mm[1] / z.mm[0]));
    inkRows.forEach((row, n) => { $('.ctl-k', row).textContent = `${n ? 'Second' : 'First'} ink · ${byId(INKS, S.inks[n]).name}`; });
    const dims = pngSize();
    $('[data-poster-png]', root).textContent = `PNG · ${dims.w} × ${dims.h} px`;
    $('[data-poster-save-note]', root).textContent = `The PNG is printed at ${dims.dpi} dpi, grain and all. The SVG and the PDF are clean vectors at ${z.name}; the PDF adds each ink's plate on its own page, as a print shop asks for them.`;
  }

  let gen = 0;
  async function draw() {
    const my = ++gen;
    const d = await doc();
    if (my !== gen) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = view.clientWidth || 600;
    raster(d, { px: Math.round(cw * dpr), inks: inkHex(), paper: byId(PAPERS, S.paper).hex, finish: S.finish, seed: S.seed, into: view });
    view.style.aspectRatio = `${d.W} / ${d.H}`;
    describe();
  }
  let t = 0;
  const later = (ms = 140) => { clearTimeout(t); t = setTimeout(() => draw().catch((e) => console.error('poster', e)), ms); };
  // the style menus and the alternates follow the faces chosen; rebuilt only when those change
  let facesShown = '';
  function changed() {
    const faces = S.type.map((t) => `${t.face}:${t.style}`).join('|');
    if (faces !== facesShown) {
      facesShown = faces;
      fillStyles();
      fillAlts().catch((e) => console.error('poster', e));
    }
    later(0);
  }
  for (const el of [head, sub, foot]) el.addEventListener('input', () => later());

  // ---------------------------------------------------------------- ready-made posters
  const wall = $('[data-poster-presets]', root);
  const thumbs = PRESETS.map((pr, i) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'pz';
    b.setAttribute('aria-label', `Start from the ${pr.name} poster`);
    b.style.setProperty('--tilt', `${[-1.6, 1.1, -0.6, 1.8, -1.2, 0.7, -1.9, 1.3, -0.8, 1.5][i % 10]}deg`);
    b.innerHTML = `<canvas class="pz-art" aria-hidden="true"></canvas><span class="pz-t f-${pr.b[0]}">${pr.name}</span>`;
    b.addEventListener('click', () => {
      apply(pr);
      $$('.pz', wall).forEach((x) => x.removeAttribute('aria-current'));
      b.setAttribute('aria-current', 'true');
      const top = root.querySelector('.studio').getBoundingClientRect().top;
      if (top < 0 || top > innerHeight * 0.6) root.querySelector('.studio').scrollIntoView({ block: 'start' });
    });
    wall.appendChild(b);
    return { pr, b };
  });
  const stateOf = (pr) => ({
    layout: pr.layout, inks: [...pr.inks], paper: pr.paper, size: 'a3', finish: 'riso', seed: 1978,
    type: [pr.a, pr.b].map(([face, style = 'Regular']) => ({ face, style })), tags: { ceili: [], kilfane: [] },
  });
  function apply(pr) {
    Object.assign(S, stateOf(pr), { size: S.size, finish: S.finish });
    head.value = pr.head; sub.value = pr.sub; foot.value = pr.foot;
    sync(layoutHost, S.layout);
    typeRows.forEach((row, n) => sync(row, S.type[n].face));
    inkRows.forEach((row, n) => sync(row, S.inks[n]));
    sync(papersHost, S.paper);
    changed();
  }
  thumbs[0].b.setAttribute('aria-current', 'true');
  async function drawThumbs() {
    for (const { pr, b } of thumbs) {
      await new Promise((res) => (window.requestIdleCallback || setTimeout)(res, { timeout: 400 }));
      const c = $('canvas', b);
      const st = stateOf(pr);
      const d = await doc(st, pr);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      raster(d, { px: Math.round((c.clientWidth || 160) * dpr), inks: inkHex(st), paper: byId(PAPERS, st.paper).hex, finish: 'riso', seed: 1978, into: c });
    }
  }

  // ---------------------------------------------------------------- saving
  function pngSize() {
    const z = sheet();
    const wi = z.mm[0] / 25.4, hi = z.mm[1] / 25.4;
    const dpi = Math.min(300, Math.floor(Math.sqrt(MAX_PX / (wi * hi))));
    return { dpi, w: Math.round(wi * dpi), h: Math.round(hi * dpi) };
  }
  const slug = () => (head.value.trim() || 'poster').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'poster';
  const fileName = (ext) => `${slug()}-${S.size}.${ext}`;
  function download(blob, name) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  async function busy(btn, job) {
    const old = btn.textContent;
    btn.disabled = true; btn.textContent = 'Printing…';
    await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 30)));
    try { await job(); } catch (e) { console.error('poster', e); btn.textContent = 'Could not save'; await new Promise((r) => setTimeout(r, 1600)); }
    btn.disabled = false; btn.textContent = old;
  }
  const saveBox = $('[data-poster-save]', root);
  if (noSave) saveBox.hidden = true;      // the preview viewer cannot save files
  const title = () => head.value.replace(/\s+/g, ' ').trim() || 'Poster';
  $('[data-poster-png]', root).addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const d = await doc(), dims = pngSize();
    const c = raster(d, { px: dims.w, inks: inkHex(), paper: byId(PAPERS, S.paper).hex, finish: S.finish, seed: S.seed });
    const blob = await new Promise((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error('PNG encoding failed'))), 'image/png'));
    c.width = c.height = 0;
    download(blob, fileName('png'));
  }));
  $('[data-poster-svg]', root).addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const d = await doc();
    const text = svg(d, { inks: inkHex(), inkNames: inkName(), paper: byId(PAPERS, S.paper).hex, sizeMM: sheet().mm, title: title() });
    download(new Blob([text], { type: 'image/svg+xml' }), fileName('svg'));
  }));
  $('[data-poster-pdf]', root).addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const d = await doc();
    download(await pdf(d, { inks: inkHex(), inkNames: inkName(), sizeMM: sheet().mm, title: title() }), fileName('pdf'));
  }));

  // ---------------------------------------------------------------- go
  facesShown = S.type.map((t) => `${t.face}:${t.style}`).join('|');
  fillStyles();
  await fillAlts();
  await draw();
  let lastW = view.clientWidth;
  new ResizeObserver(() => { if (Math.abs(view.clientWidth - lastW) > 1) { lastW = view.clientWidth; later(60); } }).observe(view);
  drawThumbs().catch((e) => console.error('poster thumbnails', e));
  root.posterReady = true;
}
