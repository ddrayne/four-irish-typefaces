export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export const FACES = ['ceili', 'carrick', 'kilfane', 'tuam'];
// NAME is the 1978 design; FAMILY is the font, which carries "Digital" so it is never taken for the original type
export const NAME = { ceili: 'Céilí', carrick: 'Carrick', kilfane: 'Kilfane', tuam: 'Tuam Uncial' };
export const FAMILY = { ceili: 'Céilí Digital', carrick: 'Carrick Digital', kilfane: 'Kilfane Digital', tuam: 'Tuam Uncial Digital' };
export const cssFamily = (k) => `"${FAMILY[k]}", Georgia, serif`;

export const PROVERBS = [
  ['Is fearr Gaeilge bhriste ná Béarla cliste.', 'Broken Irish is better than clever English.'],
  ['Tír gan teanga, tír gan anam.', 'A country without a language is a country without a soul.'],
  ['Ní neart go cur le chéile.', 'There is no strength without unity.'],
  ['Ar scáth a chéile a mhaireann na daoine.', 'People live in one another’s shelter.'],
  ['Tús maith leath na hoibre.', 'A good start is half the work.'],
  ['Mol an óige agus tiocfaidh sí.', 'Praise the young and they will flourish.'],
  ['Is glas iad na cnoic i bhfad uainn.', 'Faraway hills are green.'],
  ['De réir a chéile a thógtar na caisleáin.', 'Castles are built a little at a time.'],
  ['Níl aon tinteán mar do thinteán féin.', 'There is no hearth like your own hearth.'],
  ['Bíonn blas ar an mbeagán.', 'A little has its own flavour.'],
  ['Is maith an scéalaí an aimsir.', 'Time is a good storyteller.'],
  ['An té nach bhfuil láidir, ní foláir dó a bheith glic.', 'Whoever is not strong had better be clever.'],
  ['Aithníonn ciaróg ciaróg eile.', 'One beetle knows another.'],
];

/** Run fn once, when el first comes within `margin` of the viewport. */
export function onNear(el, fn, margin = '700px') {
  if (!el) return;
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) { io.disconnect(); fn(); }
  }, { rootMargin: margin });
  io.observe(el);
}

/** Call cb(true/false) as el enters and leaves the viewport. */
export function watchVisible(el, cb, margin = '0px') {
  const io = new IntersectionObserver((entries) => cb(entries[entries.length - 1].isIntersecting), { rootMargin: margin });
  io.observe(el);
  return io;
}

export function loadFace(k, weight = 400, style = 'normal') {
  return document.fonts.load(`${style} ${weight} 64px "${FAMILY[k]}"`).catch(() => []);
}

export function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src; s.onload = resolve; s.onerror = () => reject(new Error(`Could not load ${src}`));
    document.head.appendChild(s);
  });
}

/** Seeded PRNG (mulberry32). */
export function rng(seed = 1) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Size a canvas to its CSS box at device resolution; returns {w, h, r, ctx}. */
export function fitCanvas(canvas, h) {
  const r = Math.min(window.devicePixelRatio || 1, 2);
  const w = canvas.clientWidth;
  const hh = h ?? canvas.clientHeight;
  canvas.width = Math.round(w * r);
  canvas.height = Math.round(hh * r);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(r, 0, 0, r, 0, 0);
  return { w, h: hh, r, ctx };
}

export function offscreen(w, h) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h));
  return c;
}

/** Fit each element's text to the width of its own box. */
export function fitText(els) {
  const range = document.createRange();
  for (const el of els) {
    const cs = getComputedStyle(el);
    const avail = el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    if (avail <= 0) continue;
    el.style.fontSize = '100px';
    range.selectNodeContents(el);
    const w = range.getBoundingClientRect().width;
    if (w) el.style.fontSize = `${Math.floor((100 * avail) / w * 0.99)}px`;
  }
}

/** A tile of paper tooth, drawn once, used as a fixed overlay. */
export function paperTooth() {
  const c = offscreen(160, 160);
  const x = c.getContext('2d');
  const img = x.createImageData(160, 160);
  const rand = rng(1978);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = rand();
    const dark = v < 0.5;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = dark ? 20 : 255;
    img.data[i + 3] = Math.round(Math.abs(v - 0.5) * 2 * (dark ? 16 : 10));
  }
  x.putImageData(img, 0, 0);
  try { document.documentElement.style.setProperty('--tooth', `url(${c.toDataURL()})`); } catch { /* tainted or unsupported: no tooth */ }
}

export function copyText(text, btn) {
  const done = (msg) => { if (!btn) return; const old = btn.textContent; btn.textContent = msg; setTimeout(() => { btn.textContent = old; }, 1400); };
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => done('Copied'), () => done('Select and copy'));
  } else done('Select and copy');
}

export const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

/** A longest common subsequence of two lists: the [i, j] index pairs that match, in order. */
export function lcs(a, b, same = (x, y) => x === y) {
  const n = a.length, m = b.length, t = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) {
    t[i][j] = same(a[i], b[j]) ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
  }
  const out = [];
  for (let i = 0, j = 0; i < n && j < m;) {
    if (same(a[i], b[j])) { out.push([i, j]); i++; j++; } else if (t[i + 1][j] >= t[i][j + 1]) i++; else j++;
  }
  return out;
}

/**
 * Slide inline letters from where they were to where the line now sets them. The
 * letters are position: relative spans, so they keep the text's own shaping (a
 * transform would need inline-blocks, and inline-blocks are not kerned).
 */
export function slideFrom(els, before, duration = 320) {
  els.forEach((el, k) => {
    const a = before[k];
    if (!a || !el?.isConnected) return;
    const b = el.getBoundingClientRect();
    const dx = a.left - b.left, dy = a.top - b.top;
    if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
    el.animate([{ left: `${dx}px`, top: `${dy}px` }, { left: '0px', top: '0px' }],
      { duration, easing: 'cubic-bezier(.3, .7, .2, 1)', composite: 'add', id: 'slide' });
  });
}
