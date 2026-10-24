import { $, $$, FACES, FAMILY, PROVERBS, reduced, lerp, loadFace, watchVisible } from './util.js';

// The title is printed in two inks (green, orange) that overprint where they meet.
// Every letter is its own type cell: move across it and it changes to the next face.
// Each cell takes the width of its letter in its current face, and eases to the
// new width when the face changes, so the line breathes instead of jumping.

export async function init(hero) {
  await Promise.all(FACES.map((k) => loadFace(k)));
  const riso = $('[data-riso]', hero);
  const lines = $$('.riso-line', riso).map((l) => l.dataset.text);
  riso.textContent = '';

  const measure = document.createElement('canvas').getContext('2d');
  const widths = {};
  const widthEm = (ch, k) => {
    const key = ch + k;
    if (!(key in widths)) {
      measure.font = `100px "${FAMILY[k]}"`;
      widths[key] = measure.measureText(ch).width / 100;
    }
    return widths[key];
  };

  const layers = ['l-green', 'l-orange'].map((cls) => {
    const layer = document.createElement('span');
    layer.className = `riso-layer ${cls}`;
    layer.setAttribute('aria-hidden', 'true');
    riso.appendChild(layer);
    return layer;
  });
  const cells = [];   // [{ch, face, els:[green, orange]}]
  lines.forEach((text, li) => {
    const lineEls = layers.map((layer) => {
      const l = document.createElement('span');
      l.className = 'riso-line';
      layer.appendChild(l);
      return l;
    });
    [...text].forEach((ch, ci) => {
      const face = FACES[(ci + li * 2) % 4];
      const cell = { ch, face, els: [] };
      lineEls.forEach((l) => {
        const s = document.createElement('span');
        s.className = `cell f-${face}`;
        s.textContent = ch;
        s.style.width = `${widthEm(ch, face)}em`;
        s.dataset.i = cells.length;
        l.appendChild(s);
        cell.els.push(s);
      });
      cells.push(cell);
    });
  });

  const setFace = (cell, face, pop = true) => {
    cell.face = face;
    const w = `${widthEm(cell.ch, face)}em`;
    for (const el of cell.els) {
      el.className = `cell f-${face}${pop ? ' pop' : ''}`;
      el.style.width = w;
    }
    if (pop) setTimeout(() => cell.els.forEach((el) => el.classList.remove('pop')), 220);
  };
  const next = (cell) => setFace(cell, FACES[(FACES.indexOf(cell.face) + 1) % 4]);

  // Move across (or tap) a letter to change its face.
  let last = -1;
  riso.addEventListener('pointermove', (e) => {
    const el = e.target.closest?.('.cell');
    const i = el ? +el.dataset.i : -1;
    if (i >= 0 && i !== last) next(cells[i]);
    last = i;
  });
  riso.addEventListener('pointerleave', () => { last = -1; });
  riso.addEventListener('pointerdown', (e) => {
    const el = e.target.closest?.('.cell');
    if (el && e.pointerType !== 'mouse') next(cells[+el.dataset.i]);
  });

  // Misregistration follows the pointer, and drifts a little at rest.
  const off = { x: 0, y: 0, tx: 0, ty: 0 };
  window.addEventListener('pointermove', (e) => {
    off.tx = (e.clientX / innerWidth - 0.5) * 2;
    off.ty = (e.clientY / innerHeight - 0.5) * 2;
  }, { passive: true });

  let visible = true;
  watchVisible(hero, (v) => { visible = v; if (v) loop(); });
  const still = reduced();
  let raf = 0;
  const t0 = performance.now();
  function loop() {
    cancelAnimationFrame(raf);
    if (!visible) return;
    const t = (performance.now() - t0) / 1000;
    // With reduced motion the plates stay put, slightly out of register, as printed.
    const driftX = still ? 0.35 : Math.sin(t * 0.7) * 0.25;
    const driftY = still ? 0.25 : Math.cos(t * 0.5) * 0.2;
    off.x = still ? driftX : lerp(off.x, off.tx + driftX, 0.08);
    off.y = still ? driftY : lerp(off.y, off.ty + driftY, 0.08);
    const k = Math.min(14, innerWidth / 90);
    riso.style.setProperty('--gx', `${(-off.x * k).toFixed(2)}px`);
    riso.style.setProperty('--gy', `${(-off.y * k * 0.6).toFixed(2)}px`);
    riso.style.setProperty('--ox', `${(off.x * k).toFixed(2)}px`);
    riso.style.setProperty('--oy', `${(off.y * k * 0.6).toFixed(2)}px`);
    if (!still) raf = requestAnimationFrame(loop);
  }
  loop();

  // Opening roll, then one letter at a time keeps changing.
  if (!still) {
    let n = 0;
    const roll = setInterval(() => {
      cells.forEach((c) => setFace(c, FACES[(Math.random() * 4) | 0], false));
      if (++n > 14) {
        clearInterval(roll);
        cells.forEach((c, i) => setFace(c, FACES[i % 4]));
      }
    }, 70);
    setInterval(() => {
      if (!visible || document.hidden) return;
      next(cells[(Math.random() * cells.length) | 0]);
    }, 1300);
  }

  const hint = $('.hero-hint', hero);
  if (hint && matchMedia('(pointer: coarse)').matches) hint.textContent = 'Touch a letter to change its typeface';

  // The ticker: proverbs, each in a different face, twice over for a seamless loop.
  const track = $('[data-ticker]', hero);
  if (track) {
    const run = PROVERBS.map(([ga], i) => `<span class="f-${FACES[i % 4]}" lang="ga">${ga}</span><span class="sep f-tuam">⁊</span>`).join('');
    track.innerHTML = run + run;
  }
}
