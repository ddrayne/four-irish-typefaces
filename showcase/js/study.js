import { $, $$, FAMILY } from './util.js';

// The research studies beside the release they are rebuilding: each letter printed in
// two inks, green for the released font and orange for the latest study, so the two
// can be compared by eye. No archive pixels are shown.

const KIND = { letters: 'letters', outlines: 'letters', marks: 'accent marks', punctuation: 'punctuation' };

export async function init(root, data) {
  const face = root.dataset.study;
  const info = data.studies?.[face];
  if (!info) return;
  const family = FAMILY[face];
  const latest = info.studies[info.studies.length - 1];
  await Promise.all([document.fonts.load(`64px "${latest.family}"`), document.fonts.load(`64px "${family}"`)]).catch(() => []);
  root.hidden = false;
  const outlines = info.glyphs.length > 0;

  const intro = outlines
    ? `<b>${latest.family}</b> redraws ${family} from better reproductions in the William Curran Archive at the National Irish Visual Arts Library. It is work in progress, not a release. Green is the released ${family}; orange is the study. Where they agree, the inks print dark.`
    : `<b>${latest.family}</b> keeps ${family}'s outlines as released and adjusts only its spacing; better sources for its letters are still being sought. It is work in progress, not a release.`;

  root.innerHTML = `
    <div class="toy-bar">
      <p class="toy-title"><span class="f-${face}" lang="ga">staidéar</span><span>Work in progress · from the archive</span></p>
      ${outlines ? `<div class="toy-controls" role="group" aria-label="Which ${family} to show">
        <button type="button" class="tog" data-show="both" aria-pressed="true">Both, overprinted</button>
        <button type="button" class="tog" data-show="release" aria-pressed="false">Release</button>
        <button type="button" class="tog" data-show="study" aria-pressed="false">Study</button></div>` : ''}
    </div>
    <p class="study-text">${intro}</p>
    ${outlines ? `<div class="study-sources" role="radiogroup" aria-label="Compared with"></div>
      <div class="study-body"><figure class="study-zoom" aria-live="polite"></figure><div class="study-grid"></div></div>` : ''}
    <p class="toy-note">The archive reproductions share a printing history, so where they agree it is not proof of the original drawings. Archive images are not reproduced here.</p>`;

  if (outlines) outlineFit(root, info, face, latest);
}

function outlineFit(root, info, face, latest) {
  const grid = $('.study-grid', root);
  const body = $('.study-body', root);
  const zoom = $('.study-zoom', root);
  const srcHost = $('.study-sources', root);
  let pick = info.sources[0];
  let picked = null;

  for (const s of info.sources) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'study-src'; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(s === pick));
    b.innerHTML = `<span class="mono">${KIND[s.kind] || s.kind} · NIVAL ${s.id}</span>`;
    b.addEventListener('click', () => {
      pick = s;
      [...srcHost.querySelectorAll('.study-src')].forEach((c) => c.setAttribute('aria-checked', String(c === b)));
      draw();
    });
    srcHost.appendChild(b);
  }
  const links = document.createElement('p');
  links.className = 'study-links mono';
  const seen = new Set();
  links.innerHTML = info.sources.filter((s) => s.url && !seen.has(s.id) && seen.add(s.id))
    .map((s) => `<a href="${s.url}">Catalogue record ${s.id}${s.w ? ` (${s.w} × ${s.h} px)` : ''}</a>`).join(' · ');
  srcHost.after(links);

  const art = (g) => {
    const feat = g.tag ? `font-feature-settings:'${g.tag}' 1;` : '';
    return `<span class="sc-art" aria-hidden="true"><span class="sc-r f-${face}" style="${feat}">${g.ch}</span><span class="sc-s" style="font-family:'${latest.family}',serif;${feat}">${g.ch}</span></span>`;
  };
  const list = () => info.glyphs.filter((g) => g.src === pick.id && g.kind === pick.kind);
  function show(g) {
    picked = g.n;
    zoom.innerHTML = art(g) +
      `<figcaption><span class="mono">${g.n}${g.tag ? ` · ${g.tag}` : ''} · from NIVAL ${g.src}</span></figcaption>`;
    for (const c of grid.children) c.setAttribute('aria-pressed', String(c.dataset.n === g.n));
  }
  function draw() {
    const gs = list();
    const frag = document.createDocumentFragment();
    for (const g of gs) {
      const d = document.createElement('button');
      d.type = 'button'; d.className = 'sc'; d.dataset.n = g.n;
      d.addEventListener('click', () => show(g));
      d.innerHTML = art(g) + `<span class="sc-k mono">${g.n}</span>`;
      d.title = g.n;
      frag.appendChild(d);
    }
    grid.replaceChildren(frag);
    if (!gs.length) { zoom.innerHTML = ''; return; }
    const keep = gs.find((x) => x.n === picked);
    show(keep || gs[0]);
  }
  draw();
  $$('[data-show]', root).forEach((b) => b.addEventListener('click', () => {
    $$('[data-show]', root).forEach((c) => c.setAttribute('aria-pressed', String(c === b)));
    body.dataset.show = b.dataset.show;
  }));
  body.dataset.show = 'both';
}
