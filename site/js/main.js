import { $, $$, onNear, fitText, paperTooth, copyText } from './util.js';

// Big headings print in two inks: a copy of the words, hidden from screen readers, laid
// over them a little out of register in the second ink (see .ov in the stylesheet).
for (const el of $$('[data-ov]')) {
  const ov = document.createElement('span');
  ov.className = 'ov';
  ov.setAttribute('aria-hidden', 'true');
  ov.textContent = el.textContent;
  el.appendChild(ov);
}
paperTooth();
const data = await fetch('data/site.json').then((r) => r.json());

// Each part loads its code only when it comes near the screen.
const parts = [
  ['.hero', './hero.js'],
  ['.board', './board.js'],
  ['.evidence', './evidence.js'],
  ['[data-choose]', './ceili.js'],
  ['[data-wall]', './carrick.js'],
  ['[data-hands]', './kilfane.js'],
  ['[data-illum]', './tuam.js'],
  ['.tester', './tester.js'],
  ['.shop', './shopfront.js'],
  ['.poster', './poster.js'],
  ['.glyphs', './glyphs.js'],
  ['.prov', './provenance.js'],
];
for (const [sel, mod, near] of parts) {
  const el = $(sel);
  if (!el) continue;
  onNear(near ? $(near) : el, () => import(mod).then((m) => m.init(el, data)).catch((err) => console.error(mod, err)));
}

// A link to one glyph's provenance (#provenance/kilfane/G) names no element: go to the map, which loads and reads it.
const toProvenance = () => {
  const el = location.hash.startsWith('#provenance/') && $('.prov');
  if (!el) return;
  // parts above it load as the page passes them and push it down: hold it until the page settles or the reader moves
  const go = () => el.scrollIntoView({ behavior: 'instant' });
  const ro = new ResizeObserver(go);
  const stop = () => ro.disconnect();
  go(); ro.observe(document.body); setTimeout(stop, 3000);
  for (const ev of ['wheel', 'touchstart', 'keydown', 'pointerdown']) addEventListener(ev, stop, { once: true, passive: true });
};
addEventListener('hashchange', toProvenance);
toProvenance();

// The research panels (closed disclosures, opened on request) add a line to the page when
// they appear, so build them straight away, while the reader is still near the top.
const idle = (fn) => {
  const later = () => setTimeout(() => (window.requestIdleCallback || setTimeout)(fn), 1200);
  // this module awaits its data first, so the page may already have loaded
  if (document.readyState === 'complete') later(); else addEventListener('load', later, { once: true });
};
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
