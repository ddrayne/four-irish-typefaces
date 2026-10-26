import { $, $$, reduced, loadFace, rng, lcs, slideFrom, offscreen, fitCanvas, clamp } from './util.js';

// What makes Kilfane itself: true capitals beside its lower case, Irish letters with
// Roman forms (ss01) and insular forms (ss02) to call up, and four styles. A line is set
// large on a cutting mat, with its cap height, x-height and baseline ruled under it, and
// every change is rubbed down letter by letter, the way the face went onto paper in
// 1978: the letters that change lift off, and their new forms come through in speckles.
// The line is real text, so the browser sets it with the font's own spacing and kerning.

const STYLES = [['Regular', 400, 'normal'], ['Italic', 400, 'italic'], ['Bold', 700, 'normal'], ['Bold Italic', 700, 'italic']];
const FORMS = [
  { tag: null, label: 'Standard' },
  { tag: 'ss01', label: 'Roman' },
  { tag: 'ss02', label: 'Insular' },
];
const PREVIEW = 'ATdg';
const feat = (tag) => (tag ? `"${tag}" 1` : 'normal');

/** Capitals as Irish writes them: a prefix before a capital stays lower case (nÓG, hÉIREANN, bhFEAR). */
export function irishUpper(text) {
  return text.split(/(\s+)/).map((w) => {
    const m = w.match(/^(\p{Ll}{1,2})(?=\p{Lu})/u);
    return m ? m[1] + w.slice(m[1].length).toUpperCase() : w.toUpperCase();
  }).join('');
}

// Speckle masks, from none of the letter to nearly all of it: a rubbed letter comes
// through a speckle at a time, as dry transfer does.
function speckles(n, size = 64, cell = 2) {
  const r = rng(53909), N = size / cell, cells = Array.from({ length: N * N }, r);
  return Array.from({ length: n }, (_, k) => {
    const c = offscreen(size, size), x = c.getContext('2d');
    x.fillStyle = '#000';
    cells.forEach((v, i) => { if (v < k / n) x.fillRect((i % N) * cell, Math.floor(i / N) * cell, cell, cell); });
    return `url(${c.toDataURL()})`;
  });
}

export async function init(root, data) {
  await Promise.all([loadFace('kilfane'), loadFace('kilfane', 400, 'italic'), loadFace('kilfane', 700), loadFace('kilfane', 700, 'italic'),
    document.fonts.load('600 12px "Fragment Mono"').catch(() => [])]);
  const mat = $('[data-hands-mat]', root);
  const grid = $('[data-hands-grid]', root);
  const guides = $('[data-hands-guides]', root);
  const line = $('[data-hands-line]', root);
  const input = $('[data-hands-text]', root);
  const formsHost = $('[data-hands-forms]', root);
  const stylesHost = $('[data-hands-styles]', root);
  const capsBtn = $('[data-hands-caps]', root);
  const live = $('[data-hands-live]', root);
  const burnisher = $('[data-hands-burnisher]', root);
  const FRAMES = speckles(7);
  const rand = rng(1978);

  // which letters each set changes: Kilfane has true capitals, so the list is exact about case
  const sets = Object.fromEntries(data.faces.kilfane.sets.map((s) => [s.tag, new Set(s.chars)]));
  const formOf = (ch, tag) => (tag && sets[tag]?.has(ch.normalize('NFD')[0]) ? tag : null);

  const state = { form: null, style: 0, caps: false };
  let letters = [];       // {ch, id, el}
  let size = 0, job = 0;

  const shown = () => {
    const t = input.value.replace(/\s+/g, ' ').trim() || 'Kilfane';
    return state.caps ? irishUpper(t) : t;
  };

  // ------------------------------------------------------------------ setting the line
  function apply() {
    const [, w, st] = STYLES[state.style];
    line.style.fontFeatureSettings = feat(state.form);
    line.style.fontWeight = w;
    line.style.fontStyle = st;
  }
  function fill(text) {
    line.replaceChildren();
    const out = [];
    for (const part of text.split(/(\s+)/)) {
      if (!part) continue;
      if (/^\s+$/.test(part)) { line.append(' '); continue; }
      const w = document.createElement('span');
      w.className = 'hw';
      const b = document.createElement('i');
      b.className = 'hb';
      w.appendChild(b);
      for (const ch of part) {
        const el = document.createElement('span');
        el.className = 'hl';
        el.textContent = ch;
        w.appendChild(el);
        out.push({ ch, id: '', el });
      }
      line.appendChild(w);
    }
    return out;
  }
  // as large as the mat allows: two lines at most on a wide mat, three on a phone
  const widest = () => Math.max(0, ...$$('.hw', line).map((w) => w.getBoundingClientRect().width));
  function fit() {
    const avail = line.clientWidth;
    if (!avail) return size;
    const maxLines = avail > 640 ? 2 : 3;
    for (let s = Math.floor(Math.min(190, Math.max(40, avail / 4.2))); s >= 26; s -= 3) {
      line.style.fontSize = `${s}px`;
      const rows = new Set($$('.hb', line).map((b) => Math.round(b.getBoundingClientRect().top))).size;
      if (rows <= maxLines && widest() <= avail) return s;
    }
    return 26;
  }

  // cap height, x-height and baseline under each line, measured from the style itself
  function rule() {
    guides.replaceChildren();
    const [, w, st] = STYLES[state.style];
    const m = offscreen(1, 1).getContext('2d');
    m.font = `${st} ${w} ${size}px "Kilfane Digital"`;
    const cap = m.measureText('H').actualBoundingBoxAscent, xh = m.measureText('x').actualBoundingBoxAscent;
    const box = mat.getBoundingClientRect();
    const bases = [...new Set($$('.hb', line).map((b) => Math.round(b.getBoundingClientRect().top - box.top)))];
    bases.forEach((y, i) => {
      for (const [name, at] of [['cap height', y - cap], ['x-height', y - xh], ['baseline', y]]) {
        const g = document.createElement('div');
        g.className = `hg hg-${name.split(/[ -]/)[0]}`;
        g.style.top = `${at.toFixed(1)}px`;
        if (i === 0) { const t = document.createElement('span'); t.textContent = name; g.appendChild(t); }
        guides.appendChild(g);
      }
    });
  }

  /**
   * Set the line again. Letters that look the same as before stay, sliding to their new
   * places; letters that change lift off, and their new forms are rubbed down in order.
   */
  function set(animate = !reduced()) {
    const text = shown();
    const old = letters;
    const before = old.map((l) => l.el.getBoundingClientRect());
    const box = mat.getBoundingClientRect();
    let ghost = null;
    if (animate && old.length) {
      // the old line stays on the mat until its letters are lifted
      ghost = line.cloneNode(true);
      ghost.classList.add('hands-ghost');
      ghost.removeAttribute('data-hands-line');
      ghost.setAttribute('aria-hidden', 'true');
      Object.assign(ghost.style, { left: `${line.offsetLeft}px`, top: `${line.offsetTop}px`, width: `${line.offsetWidth}px` });
    }
    apply();
    letters = fill(text);
    size = fit();
    // a letter looks the same if it is the same character, in the same form, style and size
    letters.forEach((l) => { l.id = `${l.ch}|${formOf(l.ch, state.form)}|${state.style}|${size}`; });
    const pairs = lcs(old.map((l) => l.id), letters.map((l) => l.id));
    const kept = new Map(pairs.map(([i, j]) => [j, i]));
    const keptOld = new Set(pairs.map(([i]) => i));
    rule();
    const my = ++job;
    if (!animate) return;

    // the letters that stay slide; the ghosts of the ones that go wait to be lifted
    const ghostEls = ghost ? $$('.hl', ghost) : [];
    ghostEls.forEach((g, i) => { if (keptOld.has(i)) g.style.visibility = 'hidden'; });
    if (ghost) mat.appendChild(ghost);
    slideFrom(letters.map((l, j) => (kept.has(j) ? l.el : null)), letters.map((l, j) => (kept.has(j) ? before[kept.get(j)] : null)));
    const fresh = letters.filter((l, j) => !kept.has(j));
    const going = ghostEls.filter((g, i) => !keptOld.has(i));
    const stagger = fresh.length > 14 ? 40 : 56, step = 44;
    const ink = getComputedStyle(line).color;
    fresh.forEach((l) => {
      l.el.classList.add('rub');
      l.el.style.setProperty('--mx', `${(rand() * 64) | 0}px`);
      l.el.style.setProperty('--my', `${(rand() * 64) | 0}px`);
      l.el.style.setProperty('--mask', FRAMES[0]);
    });
    // a letter just rubbed down shows for a moment in the second ink
    const done = (l) => {
      if (!l.el.classList.contains('rub')) return;
      l.el.classList.remove('rub');
      l.el.style.removeProperty('--mask');
      l.el.animate([{ color: '#FF8A3D' }, { color: ink }], { duration: 1100, easing: 'ease-out' });
    };
    fresh.forEach((l, i) => {
      for (let k = 1; k <= FRAMES.length; k++) {
        setTimeout(() => {
          if (job !== my) return;
          if (k < FRAMES.length) l.el.style.setProperty('--mask', FRAMES[k]); else done(l);
        }, i * stagger + k * step);
      }
    });
    // each old letter is lifted as its replacement goes down
    going.forEach((g, i) => {
      const at = Math.min(i, Math.max(0, fresh.length - 1)) * stagger;
      g.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 220, delay: at, easing: 'ease-in', fill: 'forwards' });
      g.animate([{ top: '0em' }, { top: '-.06em' }], { duration: 220, delay: at, easing: 'ease-in', fill: 'forwards', composite: 'add' });
    });
    const total = Math.max(fresh.length, going.length) * stagger + FRAMES.length * step + 80;
    setTimeout(() => { ghost?.remove(); if (job === my) fresh.forEach(done); }, total);
    burnish(fresh, stagger, step, box);
  }

  // the burnisher works along the line, zigzagging over each letter as it goes down
  function burnish(fresh, stagger, step, box) {
    if (!fresh.length) return;
    const r = clamp(size * 0.09, 8, 18);
    burnisher.style.width = burnisher.style.height = `${r * 2}px`;
    const pts = [];
    fresh.forEach((l) => {
      const b = l.el.getBoundingClientRect();
      const x0 = b.left - box.left, y0 = b.top - box.top;
      for (const [fx, fy] of [[0.2, 0.32], [0.85, 0.45], [0.2, 0.58], [0.85, 0.7]]) pts.push([x0 + b.width * fx - r, y0 + b.height * fy - r]);
    });
    const dur = fresh.length * stagger + FRAMES.length * step;
    const frames = pts.map(([x, y], k) => ({ transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`, offset: (k / Math.max(1, pts.length - 1)) * 0.92 + 0.04 }));
    frames.unshift({ ...frames[0], opacity: 0, offset: 0 });
    frames[1].opacity = 1;
    frames[frames.length - 1].opacity = 1;
    frames.push({ ...frames[frames.length - 1], opacity: 0, offset: 1 });
    burnisher.getAnimations().forEach((a) => a.cancel());
    burnisher.animate(frames, { duration: dur, easing: 'linear' });
  }

  // ------------------------------------------------------------------ controls
  const radio = (host, label, i, on, pick) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'tog hp';
    b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(on));
    b.tabIndex = on ? 0 : -1;
    b.append(...label);
    b.addEventListener('click', () => {
      [...host.children].forEach((c) => { c.setAttribute('aria-checked', String(c === b)); c.tabIndex = c === b ? 0 : -1; });
      pick(i);
    });
    host.appendChild(b);
  };
  const keys = (host) => host.addEventListener('keydown', (e) => {
    const dir = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!dir) return;
    e.preventDefault();
    const bs = [...host.children], i = bs.indexOf(document.activeElement);
    const b = bs[(i + dir + bs.length) % bs.length];
    b.focus(); b.click();
  });
  const sample = (text, css) => { const s = document.createElement('span'); s.className = 'hp-g f-kilfane'; s.setAttribute('aria-hidden', 'true'); s.textContent = text; Object.assign(s.style, css); return s; };
  FORMS.forEach((f, i) => radio(formsHost, [sample(PREVIEW, { fontFeatureSettings: feat(f.tag) }), f.tag ? `${f.label} · ${f.tag}` : f.label], i, i === 0, () => {
    state.form = f.tag;
    live.textContent = `${f.label} forms`;
    set();
  }));
  STYLES.forEach(([name, w, st], i) => radio(stylesHost, [sample('Aa', { fontWeight: w, fontStyle: st }), name], i, i === 0, () => {
    state.style = i;
    live.textContent = name;
    set();
  }));
  keys(formsHost); keys(stylesHost);
  capsBtn.prepend(sample('AA', {}));
  capsBtn.addEventListener('click', () => {
    state.caps = !state.caps;
    capsBtn.setAttribute('aria-pressed', String(state.caps));
    live.textContent = state.caps ? 'Capitals' : 'As typed';
    set();
  });
  let timer = 0;
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => set(), 120); });

  // ------------------------------------------------------------------ the mat
  function drawMat() {
    const { w: W, h: H, ctx: x } = fitCanvas(grid);
    x.fillStyle = '#1C5743'; x.fillRect(0, 0, W, H);
    const nr = rng(3);
    for (let k = 0; k < (W * H) / 60; k++) { x.fillStyle = nr() < 0.5 ? 'rgba(255,255,255,.035)' : 'rgba(0,0,0,.06)'; x.fillRect(nr() * W, nr() * H, 1.3, 1.3); }
    const cell = clamp(Math.round(W / 64), 10, 18);
    const ox = 34, oy = 30;
    x.font = '600 10px "Fragment Mono", monospace';
    for (let gx = ox, i = 0; gx < W; gx += cell, i++) {
      x.strokeStyle = i % 5 === 0 ? 'rgba(160,210,180,.34)' : 'rgba(160,210,180,.12)';
      x.lineWidth = i % 5 === 0 ? 1 : 0.7;
      x.beginPath(); x.moveTo(gx + 0.5, oy); x.lineTo(gx + 0.5, H); x.stroke();
      if (i % 5 === 0) { x.fillStyle = 'rgba(227,239,231,.8)'; x.textAlign = 'center'; x.fillText(String(i / 5), gx, oy - 9); }
      x.strokeStyle = 'rgba(227,239,231,.7)'; x.lineWidth = 1;
      x.beginPath(); x.moveTo(gx + 0.5, oy - (i % 5 === 0 ? 6 : 3)); x.lineTo(gx + 0.5, oy); x.stroke();
    }
    for (let gy = oy, i = 0; gy < H; gy += cell, i++) {
      x.strokeStyle = i % 5 === 0 ? 'rgba(160,210,180,.34)' : 'rgba(160,210,180,.12)';
      x.lineWidth = i % 5 === 0 ? 1 : 0.7;
      x.beginPath(); x.moveTo(ox, gy + 0.5); x.lineTo(W, gy + 0.5); x.stroke();
      if (i % 5 === 0 && i) { x.fillStyle = 'rgba(227,239,231,.8)'; x.textAlign = 'right'; x.fillText(String(i / 5), ox - 8, gy + 3.5); }
      x.strokeStyle = 'rgba(227,239,231,.7)'; x.lineWidth = 1;
      x.beginPath(); x.moveTo(ox - (i % 5 === 0 ? 6 : 3), gy + 0.5); x.lineTo(ox, gy + 0.5); x.stroke();
    }
    x.fillStyle = 'rgba(227,239,231,.5)'; x.textAlign = 'left';
    x.fillText('cm', 8, oy - 9);
  }

  // ------------------------------------------------------------------ start
  set(false);
  drawMat();
  let lastW = mat.clientWidth, lastH = mat.clientHeight;
  new ResizeObserver(() => {
    if (mat.clientWidth !== lastW) { lastW = mat.clientWidth; set(false); }
    if (mat.clientHeight !== lastH || grid.width !== Math.round(grid.clientWidth * Math.min(devicePixelRatio || 1, 2))) { lastH = mat.clientHeight; drawMat(); }
  }).observe(mat);
  // The first time the mat comes into view, the line is rubbed down in front of you.
  if (!reduced()) {
    line.style.visibility = 'hidden';
    const io = new IntersectionObserver((en) => {
      if (!en.some((x) => x.isIntersecting)) return;
      io.disconnect();
      line.style.visibility = '';
      letters = [];               // nothing on the mat yet: every letter is rubbed down
      set();
    }, { threshold: 0.5 });
    io.observe(mat);
  }
}
