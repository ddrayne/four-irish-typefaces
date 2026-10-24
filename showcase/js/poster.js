import { $, FACES, FAMILY, loadFace, offscreen, rng } from './util.js';

// A two-colour risograph poster. Each ink is its own plate: drawn as a mask, given
// the grain of a drum print, offset a little out of register, and multiplied onto
// the paper, so where the inks cross they make a third colour. 1200 x 1600 pixels.

const INKS = [
  { id: 'green-orange', name: 'Green and orange', a: '#00A95C', b: '#FF6C2F' },
  { id: 'pink-blue', name: 'Fluorescent pink and blue', a: '#FF48B0', b: '#0078BF' },
  { id: 'red-teal', name: 'Bright red and teal', a: '#F15060', b: '#00838A' },
  { id: 'yellow-black', name: 'Yellow and black', a: '#FFE800', b: '#1A1A1A' },
];
const LAYOUTS = [
  { id: 'initial', name: 'Great initial' },
  { id: 'stack', name: 'Stacked' },
  { id: 'repeat', name: 'Repeat' },
];
const W = 1200, H = 1600;

export async function init(root) {
  await Promise.all(FACES.map((k) => loadFace(k)));
  const view = $('[data-poster-canvas]', root);
  const head = $('[data-poster-head]', root);
  const sub = $('[data-poster-sub]', root);
  const foot = $('[data-poster-foot]', root);
  const faceA = $('[data-poster-face-a]', root);
  const faceB = $('[data-poster-face-b]', root);
  const inkHost = $('[data-poster-inks]', root);
  const layHost = $('[data-poster-layouts]', root);
  const save = $('[data-poster-save]', root);
  const shift = $('[data-poster-shift]', root);
  let ink = INKS[0], layout = LAYOUTS[0], seed = 1978;

  for (const sel of [faceA, faceB]) {
    for (const k of FACES) {
      const o = document.createElement('option');
      o.value = k; o.textContent = FAMILY[k];
      sel.appendChild(o);
    }
  }
  faceA.value = 'tuam'; faceB.value = 'ceili';

  const radios = (host, list, get, set) => list.forEach((it) => {
    const b = document.createElement('button');
    b.type = 'button'; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(it === get()));
    if (it.a) {
      b.className = 'swatch'; b.title = it.name; b.setAttribute('aria-label', it.name);
      b.innerHTML = `<span style="background:${it.a}"></span><span style="background:${it.b}"></span>`;
    } else { b.className = 'tog'; b.textContent = it.name; }
    b.addEventListener('click', () => { set(it); [...host.children].forEach((c) => c.setAttribute('aria-checked', String(c === b))); draw(); });
    host.appendChild(b);
  });
  radios(inkHost, INKS, () => ink, (v) => { ink = v; });
  radios(layHost, LAYOUTS, () => layout, (v) => { layout = v; });

  const font = (k, px) => `${px}px "${FAMILY[k]}"`;
  function fit(ctx, text, k, maxW, maxPx) {
    ctx.font = font(k, maxPx);
    const w = ctx.measureText(text).width;
    return Math.floor(w > maxW ? maxPx * (maxW / w) : maxPx);
  }
  function wrap(ctx, text, k, px, maxW) {
    ctx.font = font(k, px);
    const lines = []; let cur = '';
    for (const word of text.split(/\s+/).filter(Boolean)) {
      const t = cur ? `${cur} ${word}` : word;
      if (ctx.measureText(t).width > maxW && cur) { lines.push(cur); cur = word; } else cur = t;
    }
    if (cur) lines.push(cur);
    return lines;
  }

  // Each layout draws two masks (black on transparent): plate A and plate B.
  function compose(A, B) {
    const a = A.getContext('2d'), b = B.getContext('2d');
    for (const c of [a, b]) { c.fillStyle = '#000'; c.textBaseline = 'alphabetic'; }
    const h = head.value.trim() || 'Céilí mór', s = sub.value.trim(), f = foot.value.trim();
    const kA = faceA.value, kB = faceB.value, m = 80;
    if (layout.id === 'initial') {
      // one huge letter in ink A, the words over it in ink B
      const ch = [...h][0];
      const px = 1500;
      a.font = font(kA, px);
      const mt = a.measureText(ch);
      const gw = mt.actualBoundingBoxLeft + mt.actualBoundingBoxRight;
      const gh = mt.actualBoundingBoxAscent + mt.actualBoundingBoxDescent;
      const k = Math.min((W - 40) / gw, (H * 0.86) / gh);
      a.font = font(kA, px * k);
      const m2 = a.measureText(ch);
      a.fillText(ch, (W - (m2.actualBoundingBoxRight - m2.actualBoundingBoxLeft)) / 2, H * 0.08 + m2.actualBoundingBoxAscent);
      const lines = wrap(b, h, kB, 200, W - 2 * m);
      const hp = Math.min(200, ...lines.map((l) => fit(b, l, kB, W - 2 * m, 200)));
      b.font = font(kB, hp);
      let y = H * 0.56;
      for (const l of lines) { b.fillText(l, m, y); y += hp * 1.02; }
      if (s) { const sp = fit(b, s, kB, W - 2 * m, 64); b.font = font(kB, sp); b.fillText(s, m, y + sp * 0.4); }
    } else if (layout.id === 'stack') {
      // the headline as tall as it will go, line by line, alternating inks
      const words = h.split(/\s+/).filter(Boolean);
      let y = m;
      words.forEach((w, i) => {
        const ctx = i % 2 ? b : a, k = i % 2 ? kB : kA;
        const px = fit(ctx, w, k, W - 2 * m, 420);
        ctx.font = font(k, px);
        const mt = ctx.measureText(w);
        y += mt.actualBoundingBoxAscent;
        ctx.fillText(w, m, y);
        y += mt.actualBoundingBoxDescent + 28;
      });
      if (s) {
        const lines = wrap(b, s, kB, 66, W - 2 * m);
        b.font = font(kB, 66);
        let yy = Math.min(y + 70, H - 260);
        for (const l of lines.slice(0, 4)) { b.fillText(l, m, yy); yy += 76; }
      }
    } else {
      // the headline repeated down the sheet, both inks crossing on alternate rows
      const px = fit(a, h, kA, W * 1.3, 230);
      const step = px * 0.7;                                  // rows overlap, so the inks cross
      const rows = Math.floor((H - 360) / step);
      for (let i = 0; i < rows; i++) {
        const ctx = i % 2 ? b : a, k = i % 2 ? kB : kA;
        ctx.font = font(k, px);
        ctx.fillText(`${h} ${h} ${h}`, -((i * 137) % 400), 40 + px * 0.82 + i * step);
      }
      if (s) {
        const sp = fit(a, s, kA, W - 2 * m, 72);
        a.font = font(kA, sp);
        a.fillText(s, m, H - 200);
      }
    }
    // the footer line, small, in ink B along the bottom, with a rule
    const fl = f || 'Design an Irish Typeface · 1978';
    b.fillRect(m, H - 150, W - 2 * m, 4);
    const fp = fit(b, fl, kB, W - 2 * m, 48);
    b.font = font(kB, fp);
    b.fillText(fl, m, H - 80);
  }

  // A plate: the mask, eroded by grain where the drum starved the ink.
  function plate(mask, colour, grainSeed) {
    const c = offscreen(W, H), x = c.getContext('2d');
    x.fillStyle = colour; x.fillRect(0, 0, W, H);
    x.globalCompositeOperation = 'destination-in';
    x.drawImage(mask, 0, 0);
    const g = offscreen(W, H), gx = g.getContext('2d');
    const img = gx.createImageData(W, H), r = rng(grainSeed);
    for (let i = 3; i < img.data.length; i += 4) img.data[i] = r() < 0.075 ? 255 : 0;
    gx.putImageData(img, 0, 0);
    x.globalCompositeOperation = 'destination-out';
    x.drawImage(g, 0, 0);
    return c;
  }

  let out = null;
  function draw() {
    const A = offscreen(W, H), B = offscreen(W, H);
    compose(A, B);
    out = offscreen(W, H);
    const o = out.getContext('2d');
    o.fillStyle = '#F2EEE3'; o.fillRect(0, 0, W, H);
    const r = rng(seed);
    o.globalCompositeOperation = 'multiply';
    o.drawImage(plate(A, ink.a, seed + 1), Math.round((r() - 0.5) * 12), Math.round((r() - 0.5) * 12));
    o.drawImage(plate(B, ink.b, seed + 2), Math.round((r() - 0.5) * 12), Math.round((r() - 0.5) * 12));
    o.globalCompositeOperation = 'source-over';
    // paper fibre
    const pr = rng(7);
    for (let k = 0; k < 9000; k++) { o.fillStyle = pr() < 0.5 ? 'rgba(0,0,0,.035)' : 'rgba(255,255,255,.05)'; o.fillRect(pr() * W, pr() * H, 1.5, 1.5); }
    // show it at the size of its box
    const v = view.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = view.clientWidth;
    view.width = Math.round(cw * dpr); view.height = Math.round(cw * dpr * (H / W));
    v.imageSmoothingQuality = 'high';
    v.drawImage(out, 0, 0, view.width, view.height);
    view.setAttribute('aria-label', `A two-colour poster reading ${head.value}, in ${FAMILY[faceA.value]} and ${FAMILY[faceB.value]}.`);
  }

  let t = 0;
  const later = () => { clearTimeout(t); t = setTimeout(draw, 160); };
  for (const el of [head, sub, foot]) el.addEventListener('input', later);
  for (const el of [faceA, faceB]) el.addEventListener('change', draw);
  shift.addEventListener('click', () => { seed = (seed * 31 + 7) % 99991; draw(); });
  // The preview viewer cannot save files, so the button only appears where saving works.
  if (document.querySelector('[data-no-downloads]')) save.hidden = true;
  save.addEventListener('click', () => {
    out.toBlob((blob) => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `poster-${(head.value || 'ceili').toLowerCase().replace(/[^a-z0-9áéíóú]+/g, '-')}.png`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    }, 'image/png');
  });
  let lastW = 0;
  new ResizeObserver(() => { if (view.clientWidth !== lastW) { lastW = view.clientWidth; draw(); } }).observe(view);
}
