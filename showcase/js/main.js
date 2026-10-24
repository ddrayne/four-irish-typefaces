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
  ['.glyphs', './glyphs.js'],
];
for (const [sel, mod] of parts) {
  const el = $(sel);
  onNear(el, () => import(mod).then((m) => m.init(el, data)).catch((err) => console.error(mod, err)));
}

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
