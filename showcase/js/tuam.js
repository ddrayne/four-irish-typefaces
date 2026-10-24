import { $, loadFace, fitCanvas, offscreen, rng, clamp, reduced } from './util.js';

// An insular page set in Tuam Uncial. The first letter is a great initial: its
// counters are found by flood fill and filled with pigment, and rows of red-lead dots
// follow its outline at fixed distances (a distance transform, traced with marching
// squares). The letters after it shrink, as in the Lindisfarne Gospels. Knotwork bands
// are a true over-and-under plait on a lattice, with symmetric breaks.

const PALETTES = [
  { id: 'kells', name: 'Kells', bg: '#EADFC2', ink: '#1C140D', dot: '#C4321B', fills: ['#E1AC34', '#2B7B64', '#6B3D6E', '#27408F'], knot: '#E1AC34', knot2: '#2B7B64' },
  { id: 'lindisfarne', name: 'Lindisfarne', bg: '#EEE5CC', ink: '#1C140D', dot: '#C4321B', fills: ['#2B7B64', '#E1AC34', '#C4321B', '#6B3D6E'], knot: '#27408F', knot2: '#C4321B' },
  { id: 'durrow', name: 'Durrow', bg: '#E5D7B4', ink: '#1C140D', dot: '#C4321B', fills: ['#C4321B', '#E1AC34', '#2B7B64', '#E1AC34'], knot: '#C4321B', knot2: '#E1AC34' },
  { id: 'night', name: 'Night', bg: '#1F1913', ink: '#EADFC2', dot: '#E1AC34', fills: ['#C4321B', '#2B7B64', '#27408F', '#E1AC34'], knot: '#E1AC34', knot2: '#C4321B' },
];

// ------------------------------------------------------------------ knotwork
function knot(ctx, x0, y0, cols, rows, cell, seed, col, ink, bg) {
  const rand = rng(seed);
  const I = cols * 2, J = rows * 2, q = cell / 4;
  const type = new Map();
  const key = (i, j) => i * 1000 + j;
  for (let i = 0; i <= I; i++) for (let j = 0; j <= J; j++) {
    if ((i + j) % 2 === 0) continue;
    if (i === 0 || i === I) type.set(key(i, j), 'V');
    else if (j === 0 || j === J) type.set(key(i, j), 'H');
  }
  // breaks, mirrored left-right and top-bottom
  for (let i = 1; i <= I / 2; i++) for (let j = 1; j <= J / 2; j++) {
    if ((i + j) % 2 === 0) continue;
    const r = rand();
    const t = r < 0.16 ? 'V' : r < 0.3 ? 'H' : 'X';
    for (const [a, b] of [[i, j], [I - i, j], [i, J - j], [I - i, J - j]]) type.set(key(a, b), t);
  }
  const P = (i, j) => [x0 + (i * cell) / 2, y0 + (j * cell) / 2];
  const ok = (i, j) => i >= 0 && i <= I && j >= 0 && j <= J;
  const pass1 = [], pass2 = [];
  const arm = (p, d) => [p[0] + d[0] * q, p[1] + d[1] * q];
  const NE = [1, -1], NW = [-1, -1], SE = [1, 1], SW = [-1, 1];
  const curve = (p, a, b) => {
    const A = arm(p, a), B = arm(p, b), k = q * 1.05;
    return (c) => { c.moveTo(A[0], A[1]); c.bezierCurveTo(A[0] - a[0] * k, A[1] - a[1] * k, B[0] - b[0] * k, B[1] - b[1] * k, B[0], B[1]); };
  };
  const line = (p, a, b) => { const A = arm(p, a), B = arm(p, b); return (c) => { c.moveTo(A[0], A[1]); c.lineTo(B[0], B[1]); }; };
  for (const [k, t] of [...type.entries(), ...interior()]) {
    const i = Math.floor(k / 1000), j = k % 1000, p = P(i, j);
    const has = (d) => ok(i + d[0], j + d[1]);
    if (t === 'X') {
      const slash = line(p, SW, NE), back = line(p, NW, SE);
      if (i % 2 === 0) { pass1.push(back); pass2.push(slash); } else { pass1.push(slash); pass2.push(back); }
    } else if (t === 'V') {
      if (has(NW) && has(SW)) pass1.push(curve(p, NW, SW));
      if (has(NE) && has(SE)) pass1.push(curve(p, NE, SE));
    } else {
      if (has(NW) && has(NE)) pass1.push(curve(p, NW, NE));
      if (has(SW) && has(SE)) pass1.push(curve(p, SW, SE));
    }
  }
  function* interior() {
    for (let i = 1; i < I; i++) for (let j = 1; j < J; j++) {
      if ((i + j) % 2 === 0 || type.has(key(i, j))) continue;
      yield [key(i, j), 'X'];
    }
  }
  const sw = cell * 0.27, o = Math.max(1, cell * 0.04), gap = Math.max(1, cell * 0.05);
  ctx.save();
  ctx.lineCap = 'butt'; ctx.lineJoin = 'round';
  for (const pass of [pass1, pass2]) for (const piece of pass) {
    for (const [w, c] of [[sw + 2 * o + 2 * gap, bg], [sw + 2 * o, ink], [sw, col]]) {
      ctx.beginPath(); piece(ctx); ctx.lineWidth = w; ctx.strokeStyle = c; ctx.stroke();
    }
  }
  ctx.restore();
}

// ------------------------------------------------------------------ image analysis
function chamfer(solid, w, h) {
  const INF = 1e9, d = new Float32Array(w * h);
  for (let i = 0; i < d.length; i++) d[i] = solid[i] ? 0 : INF;
  const a = 1, b = Math.SQRT2;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x; let v = d[i];
    if (x > 0) v = Math.min(v, d[i - 1] + a);
    if (y > 0) { v = Math.min(v, d[i - w] + a); if (x > 0) v = Math.min(v, d[i - w - 1] + b); if (x < w - 1) v = Math.min(v, d[i - w + 1] + b); }
    d[i] = v;
  }
  for (let y = h - 1; y >= 0; y--) for (let x = w - 1; x >= 0; x--) {
    const i = y * w + x; let v = d[i];
    if (x < w - 1) v = Math.min(v, d[i + 1] + a);
    if (y < h - 1) { v = Math.min(v, d[i + w] + a); if (x < w - 1) v = Math.min(v, d[i + w + 1] + b); if (x > 0) v = Math.min(v, d[i + w - 1] + b); }
    d[i] = v;
  }
  return d;
}

function flood(open, w, h, seeds) {
  const seen = new Uint8Array(w * h), stack = [];
  for (const s of seeds) if (open[s] && !seen[s]) { seen[s] = 1; stack.push(s); }
  while (stack.length) {
    const i = stack.pop(), x = i % w;
    for (const n of [i - w, i + w, x > 0 ? i - 1 : -1, x < w - 1 ? i + 1 : -1]) {
      if (n >= 0 && n < open.length && open[n] && !seen[n]) { seen[n] = 1; stack.push(n); }
    }
  }
  return seen;
}

// Closed contours of a binary image (marching squares), as point loops.
function contours(B, w, h) {
  const W2 = 2 * w + 1;
  const nb = new Map();
  const link = (a, b) => { (nb.get(a) || nb.set(a, []).get(a)).push(b); (nb.get(b) || nb.set(b, []).get(b)).push(a); };
  for (let y = 0; y < h - 1; y++) for (let x = 0; x < w - 1; x++) {
    const tl = B[y * w + x], tr = B[y * w + x + 1], br = B[(y + 1) * w + x + 1], bl = B[(y + 1) * w + x];
    const c = tl * 8 + tr * 4 + br * 2 + bl;
    if (c === 0 || c === 15) continue;
    const T = (2 * y) * W2 + 2 * x + 1, R = (2 * y + 1) * W2 + 2 * x + 2, Bo = (2 * y + 2) * W2 + 2 * x + 1, L = (2 * y + 1) * W2 + 2 * x;
    switch (c) {
      case 1: case 14: link(L, Bo); break;
      case 2: case 13: link(Bo, R); break;
      case 3: case 12: link(L, R); break;
      case 4: case 11: link(T, R); break;
      case 6: case 9: link(T, Bo); break;
      case 7: case 8: link(L, T); break;
      case 5: link(L, T); link(Bo, R); break;
      case 10: link(T, R); link(L, Bo); break;
    }
  }
  const loops = [], used = new Set();
  for (const start of nb.keys()) {
    if (used.has(start)) continue;
    const loop = [];
    let prev = -1, cur = start;
    while (cur !== undefined && !used.has(cur)) {
      used.add(cur);
      loop.push([(cur % W2) / 2, Math.floor(cur / W2) / 2]);
      const n = nb.get(cur);
      const nx = n[0] !== prev ? n[0] : n[1];
      prev = cur; cur = nx;
    }
    if (loop.length > 8) loops.push(loop);
  }
  return loops;
}

function resample(loop, step, phase) {
  const out = [];
  let acc = phase * step;
  for (let k = 0; k < loop.length; k++) {
    const a = loop[k], b = loop[(k + 1) % loop.length];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    while (acc <= len) { const t = acc / len; out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); acc += step; }
    acc -= len;
  }
  return out;
}

// ------------------------------------------------------------------ the page
export async function init(root) {
  await loadFace('tuam');
  const canvas = $('[data-illum-canvas]', root);
  const page = $('[data-illum-page]', root);
  const input = $('[data-illum-text]', root);
  const swHost = $('[data-illum-palettes]', root);
  let pal = PALETTES[0], seed = 1978, timer = 0, first = true;

  PALETTES.forEach((p, i) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'swatch'; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(i === 0)); b.setAttribute('aria-label', p.name); b.title = p.name;
    b.innerHTML = `<span style="background:${p.fills[0]}"></span><span style="background:${p.knot === p.fills[0] ? p.knot2 : p.knot}"></span>`;
    b.addEventListener('click', () => {
      pal = p;
      [...swHost.children].forEach((c) => c.setAttribute('aria-checked', String(c === b)));
      draw();
    });
    swHost.appendChild(b);
  });

  function draw() {
    const text = (input.value.trim() || 'Tús maith leath na hoibre').replace(/\s+/g, ' ');
    const W = page.clientWidth;
    const m = clamp(W * 0.05, 14, 56);
    const band = clamp(Math.round(W * 0.064), 30, 78);
    const Fi = clamp(W * 0.3, 118, 380);
    const Ft = clamp(W * 0.058, 22, 58);
    const font = (px) => `${px}px "Tuam Uncial"`;
    const meas = offscreen(1, 1).getContext('2d');

    const initial = text[0];
    const rest = text.slice(1);
    const sp = rest.indexOf(' ');
    const dimin = sp < 0 ? rest : rest.slice(0, sp);
    const body = sp < 0 ? '' : rest.slice(sp + 1);

    // the initial and its diminishing letters, on one baseline
    meas.font = font(Fi);
    const im = meas.measureText(initial);
    const ascent = im.actualBoundingBoxAscent, descent = im.actualBoundingBoxDescent;
    const dots = [Fi * 0.06, Fi * 0.105];
    const reach = dots[1] + Fi * 0.03;
    const top = m + band + m * 0.5 + reach;
    const base = top + ascent;
    const ix = m + reach + im.actualBoundingBoxLeft;
    const glyphs = [{ ch: initial, x: ix, size: Fi }];
    let x = ix + im.width + Fi * 0.06;
    [...dimin].forEach((ch, k) => {
      const size = Math.max(Ft * 1.25, Fi * 0.46 * Math.pow(0.86, k));
      meas.font = font(size);
      if (x + meas.measureText(ch).width > W - m) return;
      glyphs.push({ ch, x, size });
      x += meas.measureText(ch).width + size * 0.04;
    });

    // the body text: beside the great letters while there is room, as on an insular
    // page, then across the full measure below them
    meas.font = font(Ft);
    const lh = Ft * 1.22;
    const sideX = x + reach + Ft * 0.5;
    const sideW = W - m - sideX;
    const clusterBottom = base + descent + reach;
    const sideSlots = sideW > Ft * 5 ? Math.max(0, Math.floor((clusterBottom - top) / lh)) : 0;
    const lines = [];
    let cur = '';
    for (const word of body.split(' ').filter(Boolean)) {
      const t = cur ? `${cur} ${word}` : word;
      const room = lines.length < sideSlots ? sideW : W - 2 * m;
      if (meas.measureText(t).width > room && cur) { lines.push(cur); cur = word; } else cur = t;
    }
    if (cur) lines.push(cur);
    const textTop = clusterBottom + Ft * 0.35;
    const placed = lines.map((t, k) => (k < sideSlots
      ? { t, x: sideX, y: top + Ft * 0.85 + k * lh }
      : { t, x: m, y: textTop + Ft * 0.8 + (k - sideSlots) * lh }));
    const colo = Math.max(12, Ft * 0.42);
    const H = Math.round(textTop + Math.max(0, lines.length - sideSlots) * lh + colo * 2.2 + m * 0.6 + band + m);

    const { ctx, r } = fitCanvas(canvas, H);
    canvas.style.height = `${H}px`;

    // vellum
    ctx.fillStyle = pal.bg; ctx.fillRect(0, 0, W, H);
    const vr = rng(11);
    for (let k = 0; k < (W * H) / 3200; k++) {
      const cx = vr() * W, cy = vr() * H, s = 30 + vr() * 110;
      const gr = ctx.createRadialGradient(cx, cy, 0, cx, cy, s);
      const tone = vr() < 0.6 ? '120,80,20' : '255,255,255';
      gr.addColorStop(0, `rgba(${tone},${tone[0] === '1' ? 0.05 : 0.07})`);
      gr.addColorStop(1, `rgba(${tone},0)`);
      ctx.fillStyle = gr;
      ctx.fillRect(cx - s, cy - s, s * 2, s * 2);
    }
    ctx.strokeStyle = 'rgba(110,70,20,.05)'; ctx.lineWidth = 0.8;
    for (let k = 0; k < (W * H) / 1800; k++) {
      const fx0 = vr() * W, fy0 = vr() * H, a = vr() * Math.PI, l = 6 + vr() * 22;
      ctx.beginPath(); ctx.moveTo(fx0, fy0); ctx.lineTo(fx0 + Math.cos(a) * l, fy0 + Math.sin(a) * l); ctx.stroke();
    }

    // knotwork bands, top and bottom
    const cell = band / 2;
    const cols = Math.max(4, Math.floor((W - 2 * m) / cell));
    const bx = (W - cols * cell) / 2;
    knot(ctx, bx, m, cols, 2, cell, seed, pal.knot, pal.ink, pal.bg);
    knot(ctx, bx, H - m - band, cols, 2, cell, seed + 1, pal.knot2, pal.ink, pal.bg);

    // analyse the decorated letters at CSS resolution
    const ax0 = Math.max(0, Math.floor(m * 0.5)), ay0 = Math.floor(top - reach - 4);
    const aw = Math.min(W - ax0, Math.ceil(x - ax0 + reach + 8)), ah = Math.ceil(base + descent + reach + 8 - ay0);
    const scale = Math.min(1, Math.sqrt(380000 / (aw * ah)));
    const w = Math.max(2, Math.round(aw * scale)), h = Math.max(2, Math.round(ah * scale));
    const mk = offscreen(w, h).getContext('2d', { willReadFrequently: true });
    mk.scale(scale, scale); mk.translate(-ax0, -ay0);
    mk.fillStyle = '#000';
    for (const gl of glyphs) { mk.font = font(gl.size); mk.fillText(gl.ch, gl.x, base); }
    const px = mk.getImageData(0, 0, w, h).data;
    const ink = new Uint8Array(w * h), open = new Uint8Array(w * h);
    for (let i = 0; i < ink.length; i++) { ink[i] = px[i * 4 + 3] > 120 ? 1 : 0; open[i] = 1 - ink[i]; }
    const border = [];
    for (let xx = 0; xx < w; xx++) border.push(xx, (h - 1) * w + xx);
    for (let yy = 0; yy < h; yy++) border.push(yy * w, yy * w + w - 1);
    const outside = flood(open, w, h, border);
    // counters: each enclosed region gets its own pigment
    const fill = offscreen(w, h);
    const fx = fill.getContext('2d');
    const img = fx.createImageData(w, h);
    const done = new Uint8Array(w * h);
    let n = 0;
    const hex = (c) => [1, 3, 5].map((k) => parseInt(c.slice(k, k + 2), 16));
    for (let i = 0; i < ink.length; i++) {
      if (ink[i] || outside[i] || done[i]) continue;
      const region = flood(open.map((v, k) => (v && !outside[k] && !done[k] ? 1 : 0)), w, h, [i]);
      const [cr, cg, cb] = hex(pal.fills[n++ % pal.fills.length]);
      for (let k = 0; k < region.length; k++) if (region[k]) {
        done[k] = 1;
        const kx = k % w;
        // grow by a pixel so no paper shows between pigment and ink
        for (const t of [k, k - 1, k + 1, k - w, k + w]) if (t >= 0 && t < done.length && (kx > 0 || t !== k - 1)) {
          img.data[t * 4] = cr; img.data[t * 4 + 1] = cg; img.data[t * 4 + 2] = cb; img.data[t * 4 + 3] = 255;
        }
      }
    }
    fx.putImageData(img, 0, 0);
    const solid = new Uint8Array(w * h);
    for (let i = 0; i < solid.length; i++) solid[i] = ink[i] || done[i] ? 1 : 0;
    const dist = chamfer(solid, w, h);

    const dotR = Math.max(1.6, Fi * 0.0125);
    const spacing = Fi * 0.042;
    const dotList = [];
    dots.forEach((dd, row) => {
      const B = new Uint8Array(w * h);
      for (let i = 0; i < B.length; i++) B[i] = dist[i] <= dd * scale ? 1 : 0;
      for (const loop of contours(B, w, h)) {
        for (const [lx, ly] of resample(loop, spacing * scale, row * 0.5)) dotList.push([ax0 + lx / scale, ay0 + ly / scale, row]);
      }
    });

    // compose: pigment, then the ink drawn at full resolution, then the dots
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(fill, ax0, ay0, aw, ah);
    ctx.fillStyle = pal.ink;
    for (const gl of glyphs) { ctx.font = font(gl.size); ctx.fillText(gl.ch, gl.x, base); }
    ctx.font = font(Ft);
    placed.forEach((l) => ctx.fillText(l.t, l.x, l.y));
    ctx.font = font(colo);
    ctx.fillStyle = pal.dot;
    ctx.textAlign = 'center';
    ctx.fillText('tuam uncial ⁊ jarlath hayes ⁊ 1978', W / 2, H - m - band - colo * 0.9);
    ctx.textAlign = 'left';

    const paint = (list) => {
      ctx.fillStyle = pal.dot;
      for (const [dx, dy, row] of list) { ctx.beginPath(); ctx.arc(dx, dy, dotR * (row ? 0.85 : 1), 0, Math.PI * 2); ctx.fill(); }
    };
    if (first && !reduced()) {
      // the scribe works round the letter
      first = false;
      const per = Math.ceil(dotList.length / 40);
      let k = 0;
      const step = () => { paint(dotList.slice(k, k + per)); k += per; if (k < dotList.length) requestAnimationFrame(step); };
      requestAnimationFrame(step);
    } else paint(dotList);
    void r;
  }

  draw();
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(draw, 220); });
  $('[data-illum-knot]', root).addEventListener('click', () => { seed = (seed * 7 + 13) % 100000; draw(); });
  let lastW = page.clientWidth;
  new ResizeObserver(() => { if (page.clientWidth !== lastW) { lastW = page.clientWidth; draw(); } }).observe(page);
}
