import { $, $$, reduced, easeInOut, clamp } from './util.js';

// The flyer, scrolled through as evidence. The scan is drawn with its real pixels
// (no smoothing), and the outlines traced from it are drawn on top in the same
// coordinates, so what you see is exactly the match between print and font.

const SVGNS = 'http://www.w3.org/2000/svg';
const el = (name, attrs = {}) => {
  const n = document.createElementNS(SVGNS, name);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
};
const pad = (b, f, min = 0) => {
  const w = b[2] - b[0], h = b[3] - b[1];
  const p = Math.max(min, Math.max(w, h) * f);
  return [b[0] - p, b[1] - p, b[2] + p, b[3] + p];
};
// Overlap 0.85 (orange) to 0.98 (green).
const scoreColour = (s) => {
  const t = clamp((s - 0.85) / 0.13, 0, 1);
  const a = [255, 106, 31], b = [0, 159, 88];
  return `rgba(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(',')},.62)`;
};

export async function init(section, data) {
  const traced = await fetch('data/traced.json').then((r) => r.json());
  const { regions, w: FW, h: FH } = data.flyer;
  const svg = $('.ev-svg', section);
  const stage = $('[data-ev-stage]', section);
  const cap = $('[data-ev-cap]', section);
  const tip = $('[data-ev-tip]', section);
  const g = { boxes: $('.ev-boxes', svg), paths: $('.ev-paths', svg), handles: $('.ev-handles', svg), marks: $('.ev-marks', svg) };
  const modeBtns = $$('[data-ev-mode]', section);
  const audit = data.audit;

  // Numbers in the copy come from the audit, so they follow future rebuilds.
  const total = Object.values(audit).reduce((s, a) => s + a.n, 0);
  const mean = Object.values(audit).reduce((s, a) => s + a.n * a.mean, 0) / total;
  $$('[data-count="glyphs"]', section).forEach((n) => { n.textContent = total; });
  $$('[data-count="mean"]', section).forEach((n) => { n.textContent = mean.toFixed(3); });

  const glyphsIn = (face, rect) => (traced[face] || []).filter((gl) => gl.b[2] > rect[0] && gl.b[0] < rect[2] && gl.b[3] > rect[1] && gl.b[1] < rect[3]);
  const find = (face, name) => (traced[face] || []).find((gl) => gl.n === name);
  const focusGlyph = find('kilfane', 'G') || traced.kilfane[0];
  const lowest = (face) => Object.entries(audit[face]?.glyphs || {}).sort((a, b) => a[1] - b[1])[0]?.[0];

  const VIEWS = {
    flyer: { rect: [0, 0, FW, FH], mode: 'scan', cap: () => `The flyer · ${FW} × ${FH} px` },
    cut: { rect: pad(regions.kilfane, 0.04), face: 'kilfane', mode: 'boxes', cap: () => `Kilfane · ${traced.kilfane.length} glyphs cut out` },
    trace: { rect: pad(focusGlyph.b, 0.55), face: 'kilfane', mode: 'points', focus: focusGlyph, cap: () => `Kilfane ${focusGlyph.n} · ${focusGlyph.p.filter((p) => p[2]).length} points` },
    score: { rect: pad(regions.ceili, 0.04), face: 'ceili', mode: 'score', hot: lowest('ceili'), cap: () => `Céilí · mean overlap ${audit.ceili.mean.toFixed(3)}` },
    wipe: { rect: pad(regions.carrick, 0.03), mode: 'wipe', cap: () => 'Left: the 1978 print · right: the traced outlines' },
    sheet: { rect: [170, 960, 600, 1110], mode: 'scan', marks: [{ x: 398, y: 1040.5, rx: 11, ry: 5.5, rot: -12, label: '©1973' }, { x: 735, y: 962, rx: 34, ry: 11, rot: -9, label: 'S53909' }], cap: () => 'Sheet S53909 · photographed on the flyer' },
  };

  let vb = [0, 0, FW, FH];
  let view = VIEWS.flyer, mode = 'scan', anim = 0;

  // The wipe: every traced outline, filled, over paper, clipped to the right of a line.
  let frac = 0.5;
  const defs = el('defs');
  const clip = el('clipPath', { id: 'ev-clip' });
  const clipRect = el('rect', { x: 0, y: 0, width: FW, height: FH });
  clip.appendChild(clipRect); defs.appendChild(clip); svg.prepend(defs);
  const wipe = el('g', { class: 'ev-wipe', display: 'none' });
  const wipeArt = el('g', { 'clip-path': 'url(#ev-clip)' });
  wipeArt.appendChild(el('rect', { x: -FW, y: -FH, width: FW * 3, height: FH * 3, fill: '#F4F2EA' }));
  for (const face of Object.keys(traced)) for (const gl of traced[face]) wipeArt.appendChild(el('path', { d: gl.d, fill: '#15160F' }));
  const wipeLine = el('line', { class: 'ev-wipe-line' });
  const wipeKnob = el('circle', { class: 'ev-wipe-knob' });
  wipe.append(wipeArt, wipeLine, wipeKnob);
  $('image', svg).after(wipe);
  function placeWipe() {
    const x = vb[0] + vb[2] * frac;
    clipRect.setAttribute('x', x.toFixed(2));
    clipRect.setAttribute('y', (vb[1] - 10).toFixed(2));
    clipRect.setAttribute('width', (vb[2] * 2).toFixed(2));
    clipRect.setAttribute('height', (vb[3] + 20).toFixed(2));
    for (const [k, v] of Object.entries({ x1: x, x2: x, y1: vb[1] - 10, y2: vb[1] + vb[3] + 10 })) wipeLine.setAttribute(k, v.toFixed(2));
    wipeKnob.setAttribute('cx', x.toFixed(2));
    wipeKnob.setAttribute('cy', (vb[1] + vb[3] / 2).toFixed(2));
    wipeKnob.setAttribute('r', (11 * unit()).toFixed(2));
  }

  const aspectFit = (r) => {
    const sw = stage.clientWidth || 1, sh = stage.clientHeight || 1, A = sw / sh;
    let [x0, y0, x1, y1] = r;
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    let w = x1 - x0, h = y1 - y0;
    if (w / h < A) w = h * A; else h = w / A;
    // Keep the view on the scan where the scan is big enough to fill it.
    const keep = (c, size, full) => (size >= full ? full / 2 : clamp(c, size / 2, full - size / 2));
    const kx = keep(cx, w, FW), ky = keep(cy, h, FH);
    return [kx - w / 2, ky - h / 2, w, h];
  };
  const setVB = (v) => { vb = v; svg.setAttribute('viewBox', v.map((n) => n.toFixed(2)).join(' ')); sizeHandles(); if (mode === 'wipe') placeWipe(); };
  const unit = () => vb[2] / (stage.clientWidth || 1);   // user units per CSS pixel

  function zoomTo(rect) {
    const target = aspectFit(rect);
    cancelAnimationFrame(anim);
    if (reduced()) { setVB(target); return; }
    const from = vb.slice(), t0 = performance.now(), dur = 1100;
    const step = (now) => {
      const t = easeInOut(Math.min(1, (now - t0) / dur));
      setVB(from.map((f, i) => f + (target[i] - f) * t));
      if (t < 1) anim = requestAnimationFrame(step);
    };
    anim = requestAnimationFrame(step);
  }

  function sizeHandles() {
    const u = unit();
    for (const c of g.handles.querySelectorAll('circle')) c.setAttribute('r', (3.2 * u).toFixed(3));
    for (const r of g.handles.querySelectorAll('rect')) {
      const s = 7 * u; r.setAttribute('width', s.toFixed(3)); r.setAttribute('height', s.toFixed(3));
      r.setAttribute('x', (+r.dataset.x - s / 2).toFixed(3)); r.setAttribute('y', (+r.dataset.y - s / 2).toFixed(3));
    }
    for (const t of g.marks.querySelectorAll('text')) { t.setAttribute('font-size', (13 * u).toFixed(3)); t.setAttribute('stroke-width', (3 * u).toFixed(3)); }
  }

  function clear() { Object.values(g).forEach((n) => n.replaceChildren()); g.boxes.classList.remove('show'); g.paths.className.baseVal = 'ev-paths'; }

  function drawPaths(list, cls) {
    const frag = document.createDocumentFragment();
    for (const gl of list) {
      const p = el('path', { d: gl.d, pathLength: 1, 'data-n': gl.n, 'data-face': gl.face });
      if (cls?.fill) p.style.fill = cls.fill(gl);
      if (cls?.hot === gl.n) p.classList.add('hot');
      frag.appendChild(p);
    }
    g.paths.appendChild(frag);
  }

  function drawPoints(gl) {
    const frag = document.createDocumentFragment();
    const pts = gl.p;
    // Each off-curve point hangs from the on-curve point next to it.
    for (let i = 0; i < pts.length; i++) {
      if (pts[i][2]) continue;
      const prev = pts[i - 1], nextP = pts[i + 1];
      const anchor = prev && prev[2] ? prev : nextP && nextP[2] ? nextP : null;
      if (anchor) frag.appendChild(el('line', { x1: anchor[0], y1: anchor[1], x2: pts[i][0], y2: pts[i][1] }));
    }
    for (const p of pts) {
      if (p[2]) frag.appendChild(el('rect', { 'data-x': p[0], 'data-y': p[1] }));
      else frag.appendChild(el('circle', { cx: p[0], cy: p[1], r: 1 }));
    }
    g.handles.appendChild(frag);
  }

  function render() {
    clear();
    const face = view.face;
    const rect = view.rect;
    const pool = face ? glyphsIn(face, pad(rect, 0.3)).map((gl) => ({ ...gl, face })) : [];
    if (mode === 'boxes') {
      pool.forEach((gl, i) => {
        const r = el('rect', { x: gl.b[0] - 0.8, y: gl.b[1] - 0.8, width: gl.b[2] - gl.b[0] + 1.6, height: gl.b[3] - gl.b[1] + 1.6 });
        r.style.transitionDelay = `${i * 12}ms`;
        g.boxes.appendChild(r);
      });
      requestAnimationFrame(() => requestAnimationFrame(() => g.boxes.classList.add('show')));
    } else if (mode === 'outline' || mode === 'points') {
      drawPaths(pool);
      if (mode === 'points') {
        const fg = view.focus && pool.find((p) => p.n === view.focus.n) ? [view.focus] : pool.slice(0, 6);
        fg.forEach(drawPoints);
      }
      requestAnimationFrame(() => requestAnimationFrame(() => g.paths.classList.add('show')));
    } else if (mode === 'score') {
      const scores = audit[face]?.glyphs || {};
      drawPaths(pool, { fill: (gl) => scoreColour(scores[gl.n] ?? 0.95), hot: view.hot });
      g.paths.classList.add('score');
      requestAnimationFrame(() => requestAnimationFrame(() => g.paths.classList.add('show', 'fill')));
      if (view.hot) {
        const gl = find(face, view.hot);
        if (gl) mark({ x: (gl.b[0] + gl.b[2]) / 2, y: (gl.b[1] + gl.b[3]) / 2, rx: (gl.b[2] - gl.b[0]) * 0.9, ry: (gl.b[3] - gl.b[1]) * 0.8, label: `${gl.n} · ${(scores[gl.n] ?? 0).toFixed(3)}` });
      }
    }
    wipe.setAttribute('display', mode === 'wipe' ? 'inline' : 'none');
    svg.classList.toggle('wiping', mode === 'wipe');
    if (mode === 'wipe') placeWipe();
    (view.marks || []).forEach(mark);
    sizeHandles();
    modeBtns.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.evMode === mode || (mode === 'boxes' && b.dataset.evMode === 'outline'))));
    cap.textContent = view.cap();
  }

  function mark(m) {
    g.marks.appendChild(el('ellipse', { cx: m.x, cy: m.y, rx: m.rx, ry: m.ry, transform: `rotate(${m.rot || 0} ${m.x} ${m.y})` }));
    const t = el('text', { x: m.x, y: m.y - m.ry - 3, 'data-mark': 1 });
    t.textContent = m.label;
    g.marks.appendChild(t);
  }

  function show(name) {
    view = VIEWS[name] || VIEWS.flyer;
    mode = view.mode;
    render();
    zoomTo(view.rect);
  }

  modeBtns.forEach((b) => b.addEventListener('click', () => {
    const m = b.dataset.evMode;
    if (m === 'scan') mode = 'scan';
    else if (m === 'wipe') mode = 'wipe';
    else {
      if (!view.face) { view = { ...VIEWS.cut, mode: m }; zoomTo(view.rect); }
      mode = m === 'score' ? 'score' : m;
    }
    render();
  }));

  // Drag (or, with a mouse, just move) across the stage to move the wipe.
  let wiping = false;
  const wipeAt = (e) => {
    const r = svg.getBoundingClientRect();
    frac = clamp((e.clientX - r.left) / r.width, 0, 1);
    placeWipe();
  };
  svg.addEventListener('pointerdown', (e) => { if (mode !== 'wipe') return; wiping = true; svg.setPointerCapture(e.pointerId); wipeAt(e); });
  svg.addEventListener('pointerup', () => { wiping = false; });
  svg.addEventListener('pointercancel', () => { wiping = false; });
  svg.addEventListener('pointermove', (e) => { if (mode === 'wipe' && (wiping || e.pointerType === 'mouse')) wipeAt(e); });

  // Hover a traced glyph for its name and score.
  svg.addEventListener('pointermove', (e) => {
    const p = e.target.closest?.('path');
    if (!p) { tip.hidden = true; return; }
    const face = p.dataset.face, n = p.dataset.n;
    const s = audit[face]?.glyphs?.[n];
    tip.textContent = s ? `${n} · overlap ${s.toFixed(3)}` : n;
    tip.hidden = false;
  });
  svg.addEventListener('pointerleave', () => { tip.hidden = true; });

  // Steps: whichever is in the middle band of the screen drives the stage.
  const steps = $$('.ev-step', section);
  let current = null;
  const io = new IntersectionObserver((entries) => {
    for (const en of entries) {
      if (!en.isIntersecting) continue;
      const v = en.target.dataset.view;
      if (v === current) continue;
      current = v;
      steps.forEach((s) => s.classList.toggle('on', s === en.target));
      show(v);
    }
  }, { rootMargin: '-48% 0px -48% 0px' });
  steps.forEach((s) => io.observe(s));

  new ResizeObserver(() => { cancelAnimationFrame(anim); setVB(aspectFit(view.rect)); }).observe(stage);
  setVB(aspectFit(VIEWS.flyer.rect));
  render();
}
