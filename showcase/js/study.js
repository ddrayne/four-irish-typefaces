import { $, $$, FAMILY, offscreen } from './util.js';

// The original-source research beside the release it is rebuilding. Two kinds of
// evidence, each shown only where the research has it:
//
// - Outlines: each letter printed in two inks, green for the released font (traced
//   from the flyer) and orange for the latest study (traced from better reproductions),
//   with the study's own measurement of how well each fits the archive source.
// - Spacing: the release's worst colliding letter pairs, set in both fonts. The
//   overlapping ink is found here, in the browser, by drawing each letter on its own
//   and intersecting them, and is printed red.
//
// Scores are measures of fit to correlated reproductions, not proof of authenticity.
// No archive pixels are shown.

const pct = (v) => `${Math.max(0, Math.min(100, ((v - 0.75) / 0.25) * 100)).toFixed(1)}%`;
const fmt = (n) => Number(n).toLocaleString('en-IE');
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
    ? `<b>${latest.family}</b> (version ${latest.version}) rebuilds ${family} from better reproductions in the William Curran Archive at the National Irish Visual Arts Library. It is a research candidate, not a release.` +
      (info.studies.length > 1 ? ` ${describe(info.studies)}` : '') +
      ` Green is the released ${family}, traced from the flyer; orange is the study. Where they agree, the inks print dark.`
    : `<b>${latest.family}</b> (version ${latest.version}) keeps ${family}'s outlines exactly as released and corrects only its spacing. Better sources for these outlines are still being sought. It is a research candidate, not a release.`;

  root.innerHTML = `
    <div class="toy-bar">
      <p class="toy-title"><span class="f-${face}" lang="ga">staidéar</span><span>Work in progress · from better sources</span></p>
      ${outlines ? `<div class="toy-controls" role="group" aria-label="Which ${family} to show">
        <button type="button" class="tog" data-show="both" aria-pressed="true">Both, overprinted</button>
        <button type="button" class="tog" data-show="release" aria-pressed="false">Release</button>
        <button type="button" class="tog" data-show="study" aria-pressed="false">Study</button></div>` : ''}
    </div>
    <p class="study-text">${intro}</p>
    ${outlines ? `<div class="study-sources" role="radiogroup" aria-label="Compared with"></div>
      <div class="study-body"><figure class="study-zoom" aria-live="polite"></figure><div class="study-grid"></div></div>` : ''}
    <div class="study-pairs"></div>
    <p class="toy-note">Scores measure how well each version fits reproductions that share a printing history, so they are not independent originals and not proof of authenticity.${info.sources.some((s) => s.method) ? ' The latest round samples each pixel by its covered area, so its scores are not directly comparable with earlier rounds.' : ''} Archive images are not reproduced here.</p>`;

  if (outlines) outlineFit(root, info, face, latest);
  spacing(root, info, face, latest);
}

// "Kilfane Study 1 rebuilt the letters; Study 2 adds the sheet's loose accent marks and corrects the spacing."
function describe(studies) {
  return studies.map((x, i) => {
    const name = i ? x.family.replace(/^.*?(Study \d+)$/, '$1') : x.family;
    const now = i === studies.length - 1, did = [];
    if (x.measured.includes('letters')) did.push(now ? 'rebuilds the letters' : 'rebuilt the letters');
    if (x.measured.includes('marks')) did.push(now ? 'takes the accent marks from the original sheets' : 'took the accent marks from the original sheets');
    if (x.measured.includes('punctuation')) did.push(now ? 'takes the punctuation from the original brochure' : 'took the punctuation from the original brochure');
    if (x.spacing_changes) did.push(now ? 'corrects the spacing' : 'corrected the spacing');
    return `${name} ${did.join(' and ') || 'continues the work'}`;
  }).join('; ') + '.';
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
    const r = s.regressed || [];
    const reg = r.length ? ` · fit worse: ${r.slice(0, 6).join(', ')}${r.length > 6 ? ` and ${r.length - 6} more` : ''}` : '';
    const down = s.after < s.before;
    b.classList.toggle('down', down);
    b.innerHTML = `<span class="mono">${KIND[s.kind] || s.kind} · against NIVAL ${s.id}</span>` +
      `<span class="study-big"><span>${s.before.toFixed(3)}</span><span aria-hidden="true">${down ? '↘' : '→'}</span><b>${s.after.toFixed(3)}</b></span>` +
      `<span class="mono">mean overlap${down ? ', slightly lower' : ''} · ${s.improved} of ${s.n} fit better${reg}</span>`;
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
      `<figcaption><span class="mono">${g.n}${g.tag ? ` · ${g.tag}` : ''} · against NIVAL ${g.src}</span>` +
      `<span class="study-big"><span>${g.before.toFixed(3)}</span><span aria-hidden="true">→</span><b>${g.after.toFixed(3)}</b></span>` +
      `<span class="mono">overlap with the source: release → ${g.study}</span></figcaption>`;
    for (const c of grid.children) c.setAttribute('aria-pressed', String(c.dataset.n === g.n));
  }
  function draw() {
    const gs = list();
    const frag = document.createDocumentFragment();
    for (const g of gs) {
      const d = document.createElement('button');
      d.type = 'button'; d.className = 'sc'; d.dataset.n = g.n;
      d.addEventListener('click', () => show(g));
      d.innerHTML = art(g) +
        `<span class="sc-k mono">${g.n}</span>` +
        `<span class="sc-bar" aria-hidden="true"><i class="a" style="width:${pct(g.before)}"></i><i class="b${g.after >= g.before ? '' : ' worse'}" style="width:${pct(g.after)}"></i></span>` +
        `<span class="sc-v mono">${g.before.toFixed(2)} → ${g.after.toFixed(2)}</span>`;
      d.title = `${g.n}: overlap with ${g.src} ${g.before.toFixed(3)} (release) → ${g.after.toFixed(3)} (${g.study})`;
      frag.appendChild(d);
    }
    grid.replaceChildren(frag);
    if (!gs.length) { zoom.innerHTML = ''; return; }
    const keep = gs.find((x) => x.n === picked);
    show(keep || gs.reduce((a, b) => (b.after - b.before > a.after - a.before ? b : a), gs[0]));
  }
  draw();
  $$('[data-show]', root).forEach((b) => b.addEventListener('click', () => {
    $$('[data-show]', root).forEach((c) => c.setAttribute('aria-pressed', String(c === b)));
    body.dataset.show = b.dataset.show;
  }));
  body.dataset.show = 'both';
}


// ------------------------------------------------------------------ spacing
function spacing(root, info, face, latest) {
  const host = $('.study-pairs', root);
  const rel = info.release_pairs, st = latest.pairs;
  if (!rel || !st || !rel.worst?.length) { host.remove(); return; }
  const family = FAMILY[face];
  host.innerHTML = `
    <div class="pairs-head">
      <p class="pairs-title">Letters that collided</p>
      <p class="pairs-stat"><span class="mono">pairs whose ink overlaps, of ${fmt(rel.tested)} tested</span>
        <span class="study-big"><span>${fmt(rel.collisions)}</span><span aria-hidden="true">→</span><b>${fmt(st.collisions)}</b></span>
        <span class="mono">release → ${latest.family}${latest.spacing_changes ? ` · ${fmt(latest.spacing_changes)} pair corrections` : ''}</span></p>
    </div>
    <p class="pairs-text">Every pair of Latin letters was set with the fonts' own kerning and checked for ink that runs into its neighbour, with the overlap printed red here. ${latest.common_pairs?.length
      ? 'First the worst among the letters of ordinary text, then the worst of all, which mostly involve the long s (ſ).'
      : "These are the release's worst. Most involve the long s (ſ), whose tall stroke reaches over the next letter."}</p>
    <div class="pairs-grid"></div>`;
  const grid = $('.pairs-grid', host);
  const ink = getComputedStyle(root).color;
  const examples = [
    ...(latest.common_pairs || []).map((p) => ({ text: p.text, note: `overlapped by ${fmt(Math.round(-p.gap))} units` })),
    ...rel.worst.map((w) => ({ text: w.text, note: `${fmt(w.area)} units² of overlap` })),
  ].slice(0, 8);
  for (const ex of examples) {
    const cell = document.createElement('figure');
    cell.className = 'pair';
    const a = pairCanvas(ex.text, family, ink, true);
    const b = pairCanvas(ex.text, latest.family, ink, false);
    cell.append(label(`release · ${ex.note}`), a.canvas, label(`study · ${b.overlap ? 'touching' : 'clear'}`), b.canvas);
    const cap = document.createElement('figcaption');
    cap.textContent = [...ex.text].join(' + ');
    cell.appendChild(cap);
    grid.appendChild(cell);
  }
}

function label(t) {
  const s = document.createElement('span');
  s.className = 'pair-k mono';
  s.textContent = t;
  return s;
}

// Set a two-letter pair as the browser shapes it, find where the two letters' ink
// overlaps, and print that red.
function pairCanvas(text, family, ink, mark) {
  const size = 64, r = Math.min(window.devicePixelRatio || 1, 2);
  const [c1, c2] = [...text];
  const m = offscreen(1, 1).getContext('2d');
  m.font = `${size}px "${family}"`;
  const a1 = m.measureText(c1).width, a2 = m.measureText(c2).width, both = m.measureText(text).width;
  const kern = both - a1 - a2;
  const W = Math.ceil(both + size * 0.9), H = Math.ceil(size * 1.75), x0 = size * 0.45, base = size * 1.22;
  const layer = (ch, x) => {
    const c = offscreen(W * r, H * r), x2 = c.getContext('2d');
    x2.scale(r, r); x2.font = `${size}px "${family}"`; x2.fillStyle = '#000'; x2.fillText(ch, x, base);
    return x2.getImageData(0, 0, W * r, H * r).data;
  };
  const A = layer(c1, x0), B = layer(c2, x0 + a1 + kern);
  const canvas = document.createElement('canvas');
  canvas.width = W * r; canvas.height = H * r;
  canvas.style.width = `${W}px`; canvas.style.height = `${H}px`;
  const ctx = canvas.getContext('2d');
  ctx.scale(r, r);
  ctx.font = `${size}px "${family}"`; ctx.fillStyle = ink;
  ctx.fillText(text, x0, base);
  const img = ctx.getImageData(0, 0, W * r, H * r);
  let overlap = 0, x1 = 1e9, y1 = 1e9, x2 = -1, y2 = -1;
  const rowW = W * r;
  for (let i = 3; i < A.length; i += 4) {
    if (A[i] > 128 && B[i] > 128) {
      overlap++;
      const p = (i - 3) / 4, px = p % rowW, py = (p / rowW) | 0;
      x1 = Math.min(x1, px); x2 = Math.max(x2, px); y1 = Math.min(y1, py); y2 = Math.max(y2, py);
      if (mark) { img.data[i - 3] = 236; img.data[i - 2] = 38; img.data[i - 1] = 38; img.data[i] = 255; }
    }
  }
  if (mark && overlap) {
    ctx.putImageData(img, 0, 0);
    // ring the collision so even a sliver of overlap is easy to find
    const cx = (x1 + x2) / 2 / r, cy = (y1 + y2) / 2 / r;
    const rx = Math.max(9, (x2 - x1) / 2 / r + 7), ry = Math.max(9, (y2 - y1) / 2 / r + 7);
    ctx.strokeStyle = 'rgb(236,38,38)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); ctx.stroke();
  }
  return { canvas, overlap };
}
