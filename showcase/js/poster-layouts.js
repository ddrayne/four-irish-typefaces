import { outline, rect, circle } from './poster-type.js';

// What a poster is made of. A layout draws two plates, one per ink, as lists of
// operations in poster units (the sheet is 1000 wide): {c} fills a shape, {c, erase}
// cuts it out of what that plate has printed so far. The renderers in poster-render.js
// turn the plates into a PNG, an SVG or a PDF.

// Inks a risograph print shop stocks, by their usual names and screen colours.
export const INKS = [
  { id: 'green', name: 'Green', hex: '#00A95C' },
  { id: 'orange', name: 'Orange', hex: '#FF6C2F' },
  { id: 'pink', name: 'Fluorescent Pink', hex: '#FF48B0' },
  { id: 'red', name: 'Bright Red', hex: '#F15060' },
  { id: 'yellow', name: 'Yellow', hex: '#FFE800' },
  { id: 'sunflower', name: 'Sunflower', hex: '#FFB511' },
  { id: 'blue', name: 'Blue', hex: '#0078BF' },
  { id: 'medium-blue', name: 'Medium Blue', hex: '#3255A4' },
  { id: 'federal-blue', name: 'Federal Blue', hex: '#3D5588' },
  { id: 'teal', name: 'Teal', hex: '#00838A' },
  { id: 'hunter-green', name: 'Hunter Green', hex: '#407060' },
  { id: 'purple', name: 'Purple', hex: '#765BA7' },
  { id: 'burgundy', name: 'Burgundy', hex: '#914E72' },
  { id: 'black', name: 'Black', hex: '#1A1A1A' },
];
export const PAPERS = [
  { id: 'natural', name: 'Natural', hex: '#F3EEE1' },
  { id: 'white', name: 'White', hex: '#FBFAF6' },
  { id: 'buff', name: 'Buff', hex: '#ECDDB8' },
  { id: 'pink', name: 'Pale pink', hex: '#F7D9D6' },
  { id: 'sky', name: 'Sky', hex: '#D5E5EA' },
  { id: 'kraft', name: 'Kraft', hex: '#CDAE84' },
];
export const SIZES = [
  { id: 'a4', name: 'A4', mm: [210, 297] },
  { id: 'a3', name: 'A3', mm: [297, 420] },
  { id: 'a2', name: 'A2', mm: [420, 594] },
  { id: 'letter', name: 'Letter', mm: [215.9, 279.4], inches: '8½ × 11 in' },
  { id: 'tabloid', name: 'Tabloid', mm: [279.4, 431.8], inches: '11 × 17 in' },
  { id: 'square', name: 'Square', mm: [300, 300] },
];
export const FINISHES = [
  { id: 'clean', name: 'Clean' },
  { id: 'riso', name: 'Risograph' },
  { id: 'worn', name: 'Worn drum' },
];

const CREDIT = { ceili: ['Céilí', 'Hermann Hecht'], carrick: ['Carrick', 'William Curran'], kilfane: ['Kilfane', 'William Curran'], tuam: ['Tuam Uncial', 'Jarlath Hayes'] };

// ---------------------------------------------------------------- setting type in a box
function kit(P) {
  const { W, H } = P;
  const m = W * 0.06;
  const bleed = W * 0.012;
  const run = (sp, text) => sp.font.run(text, sp.tags);
  // a face's working top and bottom: its ascenders and descenders, without accents
  const top = (sp) => run(sp, 'Hdlkbfh').t;
  const bot = (sp) => Math.min(0, run(sp, 'gjpqy').b);
  const inkW = (r, s) => (r.r - r.l) * s / r.font.upm;
  const fitW = (sp, text, maxW, maxS) => {
    const r = run(sp, text), w = (r.r - r.l) / r.font.upm;
    return w > 0 ? Math.min(maxS, maxW / w) : maxS;
  };
  const words = (text) => text.split(/[ \t]+/).filter(Boolean);
  // break into lines no wider than maxW at size s; a newline always breaks
  function wrap(sp, text, s, maxW) {
    const out = [];
    for (const para of text.split('\n')) {
      let cur = '';
      for (const w of words(para)) {
        const t = cur ? `${cur} ${w}` : w;
        if (cur && inkW(run(sp, t), s) > maxW) { out.push(cur); cur = w; } else cur = t;
      }
      if (cur) out.push(cur);
    }
    return out.map((l) => run(sp, l));
  }
  const height = (sp, n, s, lead) => ((top(sp) - bot(sp)) / sp.font.upm) * s + (n - 1) * lead * s;
  // the largest size, up to max, at which the text fits the box
  function block(sp, text, boxW, boxH, { max, lead = 1, min = 6 }) {
    const ok = (s) => {
      const lines = wrap(sp, text, s, boxW);
      return lines.every((l) => inkW(l, s) <= boxW + 0.01) && height(sp, lines.length, s, lead) <= boxH ? lines : null;
    };
    let lo = min, hi = Math.max(min, max), best = ok(hi) ? hi : null;
    if (best === null) {
      for (let i = 0; i < 22; i++) { const mid = (lo + hi) / 2; if (ok(mid)) lo = mid; else hi = mid; }
      best = lo;
    }
    let lines = wrap(sp, text, best, boxW);
    // balance the lines: the narrowest measure that still breaks into as many
    if (lines.length > 1) {
      let a = boxW * 0.4, z = boxW;
      for (let i = 0; i < 16; i++) { const mid = (a + z) / 2; if (wrap(sp, text, best, mid).length <= lines.length) z = mid; else a = mid; }
      lines = wrap(sp, text, best, z);
    }
    return { sp, s: best, lead, lines, h: height(sp, lines.length, best, lead) };
  }
  // draw a block with its top at y, aligned within [x, x + w]
  function put(c, B, x, y, w, align = 'left', dx = 0, dy = 0) {
    const { sp, s, lead } = B, k = s / sp.font.upm;
    B.lines.forEach((r, i) => {
      const base = y + top(sp) * k + i * lead * s;
      const lw = inkW(r, s);
      const left = align === 'center' ? x + (w - lw) / 2 : align === 'right' ? x + w - lw : x;
      outline(c, r, s, left - r.l * k + dx, base + dy);
    });
    return c;
  }
  const fill = (ops, c) => { if (c.length) ops.push({ c }); return c; };
  const erase = (ops, c) => { if (c.length) ops.push({ c, erase: true }); return c; };
  // the footer: a rule and one line along the foot of the sheet; returns the space left above it
  function footer(ops, sp, x0 = m, x1 = W - m) {
    if (!P.foot) return H - m;
    const s = fitW(sp, P.foot, x1 - x0, W * 0.032), r = run(sp, P.foot), k = s / sp.font.upm;
    const base = H - m;
    const c = outline([], r, s, x0 - r.l * k, base);
    const ruleY = base - top(sp) * k - W * 0.022;
    rect(c, x0, ruleY - W * 0.004, x1 - x0, W * 0.004);
    fill(ops, c);
    return ruleY - W * 0.04;
  }
  // a wrapped block that sits on bottomY; returns its top
  function under(ops, sp, text, x0, x1, bottomY, size, align = 'left', lead = 1.12) {
    if (!text) return bottomY;
    // one line if it can stay a fair size, otherwise wrapped
    const one = fitW(sp, text, x1 - x0, size);
    const B = one >= size * 0.62 && !text.includes('\n')
      ? { sp, s: one, lead, lines: [run(sp, text)], h: height(sp, 1, one, lead) }
      : block(sp, text, x1 - x0, H * 0.22, { max: size, lead });
    fill(ops, put([], B, x0, bottomY - B.h, x1 - x0, align));
    return bottomY - B.h;
  }
  return { W, H, m, bleed, run, top, bot, inkW, fitW, wrap, block, put, fill, erase, footer, under, words };
}

// lines of a headline: as typed if it has line breaks, otherwise a word to a line
const linesOf = (text, words) => (text.includes('\n') ? text.split('\n').map((l) => l.trim()).filter(Boolean) : words(text));
const oneLine = (text) => text.replace(/\s*\n\s*/g, ' ').trim();

// ---------------------------------------------------------------- the layouts
function sun(P, K) {
  const { W, H, m } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const r = Math.min(W * 0.43, H * 0.29);
  const cy = Math.max(m + r * 0.92, H * 0.37);
  K.fill(A, circle([], W / 2, cy, r));
  const floor = K.footer(B, b);
  const subTop = K.under(A, a, P.sub, m, W - m, floor, W * 0.05, 'center');
  const y0 = cy + r * 0.18, y1 = subTop - W * 0.035;
  const T = K.block(b, P.head, W - 2 * m, y1 - y0, { max: W * 0.24, lead: 0.92 });
  K.fill(B, K.put([], T, m, y1 - T.h, W - 2 * m, 'center'));
  return [A, B];
}

function initial(P, K) {
  const { W, H, m } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const ch = [...P.head.replace(/\s/g, '')][0] || 'C';
  const r = K.run(a, ch), u = a.font.upm;
  const s = Math.min((W - 2 * m * 0.4) * u / Math.max(1, r.r - r.l), (H * 0.8) * u / Math.max(1, r.t - r.b));
  const k = s / u;
  K.fill(A, outline([], r, s, (W - (r.r - r.l) * k) / 2 - r.l * k, H * 0.05 + r.t * k));
  const floor = K.footer(B, b);
  const subTop = K.under(B, b, P.sub, m, W - m, floor, W * 0.05);
  const y1 = subTop - W * 0.03;
  const T = K.block(b, P.head, W - 2 * m, y1 - H * 0.42, { max: W * 0.28, lead: 0.94 });
  K.fill(B, K.put([], T, m, y1 - T.h, W - 2 * m));
  return [A, B];
}

function stack(P, K) {
  const { W, m } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const floor = K.footer(B, b);
  const subTop = K.under(B, b, P.sub, m, W - m, floor, W * 0.05);
  const lines = linesOf(P.head, K.words);
  const sp = (i) => (i % 2 ? b : a);
  const gap = W * 0.018;
  let sizes = lines.map((l, i) => K.fitW(sp(i), l, W - 2 * m, W * 0.46));
  const hOf = (sz) => sz.reduce((h, s, i) => { const r = K.run(sp(i), lines[i]); return h + (r.t - r.b) * s / r.font.upm; }, 0) + gap * (lines.length - 1);
  const avail = subTop - W * 0.04 - m;
  const total = hOf(sizes);
  if (total > avail) sizes = sizes.map((s) => s * (avail - gap * (lines.length - 1)) / (total - gap * (lines.length - 1)));
  let y = m;
  lines.forEach((l, i) => {
    const r = K.run(sp(i), l), k = sizes[i] / r.font.upm;
    y += r.t * k;
    K.fill(i % 2 ? B : A, outline([], r, sizes[i], m - r.l * k, y));
    y += -r.b * k + gap;
  });
  return [A, B];
}

function shadow(P, K) {
  const { W, H, m, bleed } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const T = K.block(a, P.head, W - 2 * m, H * 0.64 - 2.4 * m, { max: W * 0.32, lead: 0.9 });
  const fh = Math.min(H * 0.64, Math.max(H * 0.42, T.h + 3.2 * m));      // the flood, fitted to its words
  K.fill(A, rect([], -bleed, -bleed, W + 2 * bleed, fh + bleed));
  const y = (fh - T.h) / 2;
  K.erase(A, K.put([], T, m, y, W - 2 * m));
  const d = Math.max(W * 0.008, T.s * 0.055);
  // the same words in the second face, offset: a cast shadow through the cut
  const S = { ...T, sp: b, lines: T.lines.map((l) => K.run(b, l.text)) };
  S.s = Math.min(T.s, ...S.lines.map((l) => (W - 2 * m) * l.font.upm / Math.max(1, l.r - l.l)));
  K.fill(B, K.put([], S, m, y + (K.top(a) * T.s / a.font.upm - K.top(b) * S.s / b.font.upm), W - 2 * m, 'left', d, d));
  const floor = K.footer(B, b);
  const B2 = K.block(b, P.sub || '', W - 2 * m, floor - fh - m * 0.9, { max: W * 0.075, lead: 1.08 });
  if (P.sub) K.fill(B, K.put([], B2, m, fh + m * 0.8, W - 2 * m));
  return [A, B];
}

function twoFaces(P, K) {
  const { W, m } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const floor = K.footer(B, b);
  const subTop = K.under(B, b, P.sub, m, W - m, floor, W * 0.05);
  const lines = linesOf(P.head, K.words);
  const gap = W * 0.03;
  let rows = lines.map((l) => {
    const ra = K.run(a, l), rb = K.run(b, l);
    const sa = K.fitW(a, l, W - 2 * m, W * 0.5), sb = K.fitW(b, l, W - 2 * m, W * 0.5);
    return { ra, rb, sa, sb };
  });
  const asc = (r, s) => r.t * s / r.font.upm, desc = (r, s) => -r.b * s / r.font.upm;
  const hOf = (rs) => rs.reduce((h, q) => h + Math.max(asc(q.ra, q.sa), asc(q.rb, q.sb)) + Math.max(desc(q.ra, q.sa), desc(q.rb, q.sb)), 0) + gap * (rs.length - 1);
  const avail = subTop - W * 0.04 - m, total = hOf(rows);
  if (total > avail) {
    const f = (avail - gap * (rows.length - 1)) / (total - gap * (rows.length - 1));
    rows = rows.map((q) => ({ ...q, sa: q.sa * f, sb: q.sb * f }));
  }
  let y = m + Math.max(0, avail - hOf(rows)) / 2;
  for (const q of rows) {
    y += Math.max(asc(q.ra, q.sa), asc(q.rb, q.sb));
    const ka = q.sa / q.ra.font.upm, kb = q.sb / q.rb.font.upm;
    K.fill(A, outline([], q.ra, q.sa, m + ((W - 2 * m) - K.inkW(q.ra, q.sa)) / 2 - q.ra.l * ka, y));
    K.fill(B, outline([], q.rb, q.sb, m + ((W - 2 * m) - K.inkW(q.rb, q.sb)) / 2 - q.rb.l * kb, y));
    y += Math.max(desc(q.ra, q.sa), desc(q.rb, q.sb)) + gap;
  }
  return [A, B];
}

function repeat(P, K) {
  const { W, H, m, bleed } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const text = oneLine(P.head);
  const s = Math.max(W * 0.1, Math.min(W * 0.24, K.fitW(a, text, W * 0.95, W * 0.24)));
  const band = H - (P.foot ? W * 0.13 : 0) - (P.sub ? W * 0.12 : 0) - m * 0.6;
  const step = s * 0.56;
  const ca = [], cb = [];
  for (let i = 0; ; i++) {
    const sp = i % 2 ? b : a, r = K.run(sp, text), k = s / r.font.upm;
    const y = s * 0.15 + K.top(sp) * k + i * step;
    if (y - K.top(sp) * k > band) break;
    const adv = r.w * k + K.run(sp, ' ').w * k * 1.4;
    let x = -(((i * 0.37) % 1) * adv);
    while (x < W + bleed) { outline(i % 2 ? cb : ca, r, s, x, y); x += adv; }
  }
  K.fill(A, ca); K.fill(B, cb);
  // a clean band across the foot for the words
  const cut = rect([], -bleed, band, W + 2 * bleed, H - band + bleed);
  K.erase(A, cut.slice()); K.erase(B, cut);
  const floor = K.footer(B, b);
  K.under(A, a, P.sub, m, W - m, floor, W * 0.055);
  return [A, B];
}

function tiles(P, K) {
  const { W, m } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const floor = K.footer(B, b);
  const subTop = K.under(B, b, P.sub, m, W - m, floor, W * 0.05);
  const chars = [...oneLine(P.head)].filter((c) => c !== ' ').slice(0, 42);
  if (!chars.length) chars.push('C');
  const aw = W - 2 * m, ah = subTop - W * 0.04 - m;
  let cols = Math.max(1, Math.round(Math.sqrt(chars.length * aw / ah)));
  while (Math.ceil(chars.length / cols) * (aw / cols) > ah && cols < chars.length) cols++;
  const rows = Math.ceil(chars.length / cols);
  const cell = Math.min(aw / cols, ah / rows);
  const x0 = m + (aw - cell * cols) / 2;
  const flood = [], cut = [], ink = [];
  chars.forEach((ch, i) => {
    const r0 = Math.floor(i / cols), c0 = i % cols;
    const x = x0 + c0 * cell, y = m + r0 * cell;
    const on = (r0 + c0) % 2 === 0;
    const sp = on ? a : b, r = K.run(sp, ch), u = r.font.upm;
    const s = Math.min(cell * 0.8 * u / Math.max(1, r.r - r.l), cell * 0.78 * u / Math.max(1, r.t - r.b));
    const k = s / u;
    const gx = x + (cell - (r.r - r.l) * k) / 2 - r.l * k, gy = y + (cell - (r.t - r.b) * k) / 2 + r.t * k;
    if (on) { rect(flood, x, y, cell, cell); outline(cut, r, s, gx, gy); } else outline(ink, r, s, gx, gy);
  });
  K.fill(A, flood); K.erase(A, cut); K.fill(B, ink);
  return [A, B];
}

function halftone(P, K) {
  const { W, H, m } = K, b = P.b;
  const A = [], B = [];
  const pitch = W / 30, ang = (15 * Math.PI) / 180;
  const cs = Math.cos(ang), sn = Math.sin(ang);
  const dots = [];
  const R = Math.hypot(W, H);
  for (let i = -R / pitch; i < R / pitch; i++) {
    for (let j = -R / pitch; j < R / pitch; j++) {
      const x = W / 2 + (i * cs - j * sn) * pitch, y = H / 2 + (i * sn + j * cs) * pitch;
      if (x < -pitch || x > W + pitch || y < -pitch || y > H + pitch) continue;
      const t = Math.max(0, 1 - y / (H * 0.74));
      const rr = pitch * 0.58 * Math.pow(t, 0.85);
      if (rr > pitch * 0.04) circle(dots, x, y, rr);
    }
  }
  K.fill(A, dots);
  const floor = K.footer(B, b);
  const subTop = K.under(B, b, P.sub, m, W - m, floor, W * 0.05);
  const y1 = subTop - W * 0.03;
  const T = K.block(b, P.head, W - 2 * m, y1 - H * 0.36, { max: W * 0.26, lead: 0.92 });
  K.fill(B, K.put([], T, m, y1 - T.h, W - 2 * m));
  return [A, B];
}

function upright(P, K) {
  const { W, H, m, bleed } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const band = W * 0.36;
  K.fill(B, rect([], -bleed, -bleed, band + bleed, H + 2 * bleed));
  const text = oneLine(P.head);
  const r = K.run(a, text), u = r.font.upm;
  const s = Math.min((H - 2 * m) * u / Math.max(1, r.r - r.l), (W * 0.56) * u / Math.max(1, r.t - r.b));
  const k = s / u;
  // reading up the sheet: the baseline runs bottom to top, the letters' tops face left
  const bx = m * 0.7 + r.t * k, by = H - m + r.l * k;
  K.fill(A, outline([], r, s, bx, by, [0, -1], [-1, 0]));
  const x0 = Math.max(band + m * 0.6, bx - r.b * k + m * 0.6);
  const colW = W - m - x0;
  const floor = K.footer(B, b, x0, W - m);
  if (P.sub) {
    const S = K.block(a, P.sub, colW, (floor - m) * 0.7, { max: W * 0.09, lead: 1.05 });
    K.fill(A, K.put([], S, x0, m, colW));
  }
  return [A, B];
}

function specimen(P, K) {
  const { W, H, m } = K, a = P.a, b = P.b;
  const A = [], B = [];
  const T = K.block(a, P.head, W - 2 * m, H * 0.25, { max: W * 0.24, lead: 0.92 });
  K.fill(A, K.put([], T, m, m, W - 2 * m));
  let y = m + T.h + W * 0.035;
  if (P.sub) {
    const S = K.block(a, P.sub, W - 2 * m, H * 0.08, { max: W * 0.05, lead: 1.1 });
    K.fill(B, K.put([], S, m, y, W - 2 * m));
    y += S.h + W * 0.03;
  }
  K.fill(B, rect([], m, y, W - 2 * m, W * 0.008));
  y += W * 0.04;
  const floor = K.footer(B, b);
  const unicase = a.font.cmap.get(65) === a.font.cmap.get(97);
  const pair = K.run(a, unicase ? 'ag' : 'Ag'), u = pair.font.upm;
  const lines = [unicase ? null : 'ABCDEFGHIJKLM', unicase ? null : 'NOPQRSTUVWXYZ', 'abcdefghijklm', 'nopqrstuvwxyz', '0123456789 &?!', 'áéíóú ḃċḋḟġṁṗṡṫ ⁊'].filter(Boolean);
  const alpha = lines.join('\n');
  const room = floor - y;
  const colW = (W - 2 * m) * 0.5;
  const ps = Math.min(colW * 0.92 * u / Math.max(1, pair.r - pair.l), room * 0.6 * u / Math.max(1, pair.t - pair.b));
  const pk = ps / u;
  K.fill(A, outline([], pair, ps, m - pair.l * pk, y + pair.t * pk));
  const [name, who] = CREDIT[a.font.face];
  const cx = m + colW + W * 0.03, cw = W - m - cx;
  const N = K.block(a, name, cw, room * 0.25, { max: W * 0.09, lead: 1 });
  K.fill(B, K.put([], N, cx, y, cw));
  const C = K.block(a, `${who}\n1978`, cw, room * 0.2, { max: W * 0.045, lead: 1.15 });
  K.fill(B, K.put([], C, cx, y + N.h + W * 0.025, cw));
  const ay = y + Math.max((pair.t - pair.b) * pk, N.h + C.h + W * 0.05) + W * 0.04;
  const L = K.block(a, alpha, W - 2 * m, floor - ay, { max: W * 0.07, lead: 1.18 });
  K.fill(B, K.put([], L, m, ay, W - 2 * m));
  return [A, B];
}

export const LAYOUTS = [
  { id: 'sun', name: 'Sun', draw: sun },
  { id: 'initial', name: 'Great initial', draw: initial },
  { id: 'stack', name: 'Stacked', draw: stack },
  { id: 'shadow', name: 'Cut out', draw: shadow },
  { id: 'two', name: 'Two faces', draw: twoFaces },
  { id: 'repeat', name: 'Repeat', draw: repeat },
  { id: 'tiles', name: 'Tiles', draw: tiles },
  { id: 'halftone', name: 'Halftone', draw: halftone },
  { id: 'upright', name: 'Upright', draw: upright },
  { id: 'specimen', name: 'Specimen', draw: specimen },
];

/**
 * Lay out a poster. P: { W, H, head, sub, foot, a, b } where a and b are the two inks'
 * type, each { font, tags }. Returns the two plates.
 */
export function compose(P, layoutId) {
  const L = LAYOUTS.find((l) => l.id === layoutId) || LAYOUTS[0];
  const head = P.head.trim() || 'Céilí mór';
  const Q = { ...P, head, sub: P.sub.trim(), foot: P.foot.trim() };
  return L.draw(Q, kit(Q));
}

// ---------------------------------------------------------------- ready-made posters
// Irish phrases and proverbs, each in a layout, inks and faces that suit it.
export const PRESETS = [
  { name: 'Céilí mór anocht', head: 'Céilí mór anocht', sub: 'Halla an pharóiste · a naoi a chlog', foot: 'Fáilte roimh chách · All welcome',
    layout: 'sun', a: ['tuam'], b: ['ceili'], inks: ['pink', 'medium-blue'], paper: 'natural' },
  { name: 'Oíche Shamhna', head: 'Oíche\nShamhna', sub: 'Bairín breac, tine chnámh agus púcaí', foot: 'Halloween · 31 Deireadh Fómhair',
    layout: 'shadow', a: ['tuam'], b: ['tuam'], inks: ['orange', 'black'], paper: 'natural' },
  { name: 'Tús maith leath na hoibre', head: 'Tús maith leath na hoibre', sub: 'A good start is half the work.', foot: 'Seanfhocal · Irish proverb',
    layout: 'stack', a: ['carrick'], b: ['kilfane'], inks: ['green', 'orange'], paper: 'natural' },
  { name: 'Fáilte', head: 'Fáilte', sub: 'Céad míle fáilte · A hundred thousand welcomes', foot: 'Kilfane · William Curran · 1978',
    layout: 'initial', a: ['kilfane', 'Bold'], b: ['kilfane'], inks: ['teal', 'red'], paper: 'white' },
  { name: 'Ceithre chló', head: 'ceithre\nchló', sub: 'Céilí · Carrick · Kilfane · Tuam Uncial', foot: 'Design an Irish Typeface · 1978',
    layout: 'two', a: ['ceili'], b: ['tuam'], inks: ['pink', 'teal'], paper: 'natural' },
  { name: 'Ní neart go cur le chéile', head: 'Ní neart go cur le chéile', sub: 'There is no strength without unity', foot: 'Seanfhocal · Irish proverb',
    layout: 'repeat', a: ['tuam'], b: ['ceili'], inks: ['blue', 'pink'], paper: 'white' },
  { name: 'Sláinte', head: 'Sláinte', sub: 'Seisiún ceoil · Dé hAoine', foot: 'Ceol beo · Live music',
    layout: 'tiles', a: ['carrick'], b: ['carrick'], inks: ['yellow', 'purple'], paper: 'white' },
  { name: 'Is glas iad na cnoic', head: 'Is glas iad na cnoic i bhfad uainn', sub: 'Faraway hills are green', foot: 'Seanfhocal · Irish proverb',
    layout: 'halftone', a: ['ceili'], b: ['ceili', 'Bold'], inks: ['green', 'federal-blue'], paper: 'sky' },
  { name: 'Tír gan teanga', head: 'Tír gan teanga', sub: 'Tír gan teanga, tír gan anam. A country without a language is a country without a soul.', foot: 'Seanfhocal',
    layout: 'upright', a: ['tuam'], b: ['kilfane'], inks: ['red', 'sunflower'], paper: 'natural' },
  { name: 'Cill Chainnigh', head: 'Cill Chainnigh', sub: 'Named after Kilfane, County Kilkenny', foot: 'Commended · Design an Irish Typeface · 1978',
    layout: 'specimen', a: ['kilfane'], b: ['kilfane'], inks: ['federal-blue', 'red'], paper: 'buff' },
];
