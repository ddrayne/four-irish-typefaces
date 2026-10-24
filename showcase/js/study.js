import { $, $$, FAMILY } from './util.js';

// A research candidate beside the release it is rebuilding. Each letter is printed in
// two inks: green for the released font (traced from the flyer), orange for the study
// (traced from better reproductions). Where they agree the inks overprint dark. The
// scores are the study's own: how well each version fits the archive source, which
// is a measure of fit, not proof of authenticity. No archive pixels are shown.

const pct = (v) => `${Math.max(0, Math.min(100, ((v - 0.8) / 0.2) * 100)).toFixed(1)}%`;

export async function init(root, data) {
  const st = (data.studies || []).find((s) => s.face === root.dataset.study);
  if (!st) return;
  await document.fonts.load(`64px "${st.family}"`).catch(() => []);
  root.hidden = false;
  const grid = $('[data-study-grid]', root);
  const body = $('.study-body', root);
  const zoom = $('[data-study-zoom]', root);
  let picked = null;
  const srcHost = $('[data-study-sources]', root);
  const family = FAMILY[st.face];
  let source = st.sources[0]?.id;

  $('[data-study-text]', root).innerHTML =
    `<b>${st.family}</b> (version ${st.version}) is ${family} rebuilt letter by letter from better reproductions in the William Curran Archive at the National Irish Visual Arts Library. ` +
    `It is a research candidate, not a release. Green is the released ${family}, traced from the flyer; orange is the study. Where the two agree, the inks print dark.`;
  $('[data-study-note]', root).textContent =
    'Both reproductions share the same printing history and blemishes, so they are not independent originals, and the study was traced from them. ' +
    'The scores measure how well each version fits those sources, not authenticity. Archive images are not reproduced here.';

  st.sources.forEach((s, i) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'study-src'; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(i === 0));
    const reg = s.regressed?.length ? ` · fits worse: ${s.regressed.join(', ')}` : '';
    b.innerHTML = `<span class="mono">Against NIVAL ${s.id}${s.w ? ` · ${s.w} × ${s.h} px` : ''}</span>` +
      `<span class="study-big"><span>${s.before.toFixed(3)}</span><span aria-hidden="true">→</span><b>${s.after.toFixed(3)}</b></span>` +
      `<span class="mono">mean overlap · ${s.improved} of ${s.glyphs} letters fit better${reg}</span>`;
    b.addEventListener('click', () => {
      source = s.id;
      [...srcHost.children].forEach((c) => c.setAttribute('aria-checked', String(c === b)));
      draw();
    });
    srcHost.appendChild(b);
    if (s.url) {
      const a = document.createElement('a');
      a.href = s.url; a.className = 'study-link mono'; a.textContent = `Catalogue record ${s.id}`;
      srcHost.appendChild(a);
    }
  });

  const art = (g) => {
    const feat = g.tag ? `font-feature-settings:'${g.tag}' 1;` : '';
    return `<span class="sc-art" aria-hidden="true"><span class="sc-r f-${st.face}" style="${feat}">${g.ch}</span><span class="sc-s" style="font-family:'${st.family}',serif;${feat}">${g.ch}</span></span>`;
  };
  function show(g) {
    picked = g.n;
    zoom.innerHTML = art(g) +
      `<figcaption><span class="mono">${g.n}${g.tag ? ` · ${g.tag}` : ''} · against NIVAL ${g.src}</span>` +
      `<span class="study-big"><span>${g.before.toFixed(3)}</span><span aria-hidden="true">→</span><b>${g.after.toFixed(3)}</b></span>` +
      `<span class="mono">overlap with the source: release → study</span></figcaption>`;
    for (const c of grid.children) c.setAttribute('aria-pressed', String(c.dataset.n === g.n));
  }
  function draw() {
    const list = st.glyphs.filter((x) => x.src === source);
    const frag = document.createDocumentFragment();
    for (const g of list) {
      const d = document.createElement('button');
      d.type = 'button';
      d.className = 'sc';
      d.dataset.n = g.n;
      d.addEventListener('click', () => show(g));
      const better = g.after >= g.before;
      d.innerHTML = art(g) +
        `<span class="sc-k mono">${g.n}</span>` +
        `<span class="sc-bar" aria-hidden="true"><i class="a" style="width:${pct(g.before)}"></i><i class="b${better ? '' : ' worse'}" style="width:${pct(g.after)}"></i></span>` +
        `<span class="sc-v mono">${g.before.toFixed(2)} → ${g.after.toFixed(2)}</span>`;
      d.title = `${g.n}: overlap with ${source} ${g.before.toFixed(3)} (release) → ${g.after.toFixed(3)} (study)`;
      frag.appendChild(d);
    }
    grid.replaceChildren(frag);
    // open on the letter that changed most
    const keep = list.find((x) => x.n === picked);
    show(keep || list.reduce((a, b) => (b.after - b.before > a.after - a.before ? b : a), list[0]));
  }
  draw();

  $$('[data-study-show]', root).forEach((b) => b.addEventListener('click', () => {
    $$('[data-study-show]', root).forEach((c) => c.setAttribute('aria-pressed', String(c === b)));
    body.dataset.show = b.dataset.studyShow;
  }));
  body.dataset.show = 'both';
}
