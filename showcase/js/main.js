import { $, $$, onNear, fitText, paperTooth, copyText } from './util.js';

const data = await fetch('data/site.json').then((r) => r.json());
paperTooth();

// Each part loads its code only when it comes near the screen.
const parts = [
  ['.hero', './hero.js'],
  ['.board', './board.js'],
  ['.evidence', './evidence.js'],
  ['[data-dance]', './ceili.js'],
  ['[data-wall]', './carrick.js'],
  ['[data-rub]', './kilfane.js'],
  ['[data-illum]', './tuam.js'],
  ['.tester', './tester.js'],
  ['.shop', './shopfront.js'],
  ['.glyphs', './glyphs.js'],
];
for (const [sel, mod, near] of parts) {
  const el = $(sel);
  if (!el) continue;
  onNear(near ? $(near) : el, () => import(mod).then((m) => m.init(el, data)).catch((err) => console.error(mod, err)));
}

// The research panels change the page's height when they appear, so build them
// straight away, while the reader is still near the top, rather than as they near.
const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 200));
idle(() => import('./study.js').then((m) => $$('[data-study]').forEach((el) => m.init(el, data))).catch((err) => console.error('study.js', err)));

// Footer and other fitted lines.
const fits = $$('.foot [data-fit]');
document.fonts.ready.then(() => fitText(fits));
new ResizeObserver(() => fitText(fits)).observe(document.body);

const snip = $('[data-copy-snippet]');
snip?.addEventListener('click', () => copyText($('[data-snippet]').textContent, snip));

// Kilfane's alternates: each letter shown with the stylistic set that calls it up.
for (const host of $$('[data-alts]')) {
  const f = data.faces[host.dataset.alts];
  for (const set of f.sets) {
    for (const ch of set.chars) {
      const d = document.createElement('div');
      d.className = 'alt';
      d.title = `${set.label} (${set.tag})`;
      d.innerHTML = `<span style="font-feature-settings:'${set.tag}' 1">${ch}</span><span>${ch} · ${set.tag}</span>`;
      host.appendChild(d);
    }
  }
}
