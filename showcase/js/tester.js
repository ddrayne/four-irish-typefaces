import { $, FACES, FAMILY, PROVERBS } from './util.js';

const STYLE = { Regular: [400, 'normal'], Italic: [400, 'italic'], Bold: [700, 'normal'], 'Bold Italic': [700, 'italic'] };

export function init(root, data) {
  const facesHost = $('[data-t-faces]', root);
  const stylesHost = $('[data-t-styles]', root);
  const setsHost = $('[data-t-sets]', root);
  const size = $('[data-t-size]', root);
  const all = $('[data-t-all]', root);
  const out = $('[data-t-out]', root);
  const text = $('[data-t-text]', root);
  const gloss = $('[data-t-gloss]', root);
  const study = $('[data-t-study]', root);
  const studyWrap = $('[data-t-study-wrap]', root);
  const studyLabel = $('[data-t-study-label]', root);
  // the latest research study of a face, if any (Regular only)
  const latest = (k) => { const s = data.studies?.[k]; return s ? s.studies[s.studies.length - 1].family : null; };
  let face = 'kilfane', style = 'Regular', sets = new Set(), pi = 0;
  if (innerWidth < 640) size.value = String(Math.round(innerWidth / 7));

  const radio = (host, label, checked, onPick, cls = '') => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = `tog ${cls}`; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(checked)); b.innerHTML = label;
    b.addEventListener('click', () => { [...host.children].forEach((c) => c.setAttribute('aria-checked', String(c === b))); onPick(); });
    host.appendChild(b);
    return b;
  };
  FACES.forEach((k) => radio(facesHost, `<span class="f-${k}">${FAMILY[k]}</span>`, k === face, () => { face = k; build(); }, 't-face'));

  function build() {
    const f = data.faces[face];
    const anyStudy = FACES.some(latest);
    studyWrap.hidden = !anyStudy;
    studyLabel.textContent = all.checked ? 'Research studies' : latest(face) || 'No study yet';
    study.disabled = !all.checked && !latest(face);
    stylesHost.replaceChildren();
    if (!f.styles.includes(style) || (study.checked && !study.disabled)) style = 'Regular';
    f.styles.forEach((s) => {
      const b = radio(stylesHost, s, s === style, () => { style = s; apply(); });
      if (study.checked && !study.disabled && s !== 'Regular') { b.disabled = true; b.title = 'The studies are Regular only'; }
    });
    setsHost.replaceChildren();
    sets = new Set([...sets].filter((t) => f.sets.some((s) => s.tag === t)));
    f.sets.forEach((s) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'tog'; b.setAttribute('aria-pressed', String(sets.has(s.tag)));
      b.textContent = s.label; b.title = s.tag;
      b.addEventListener('click', () => { sets.has(s.tag) ? sets.delete(s.tag) : sets.add(s.tag); b.setAttribute('aria-pressed', String(sets.has(s.tag))); apply(); });
      setsHost.appendChild(b);
    });
    apply();
  }

  function css(k) {
    const useStudy = study.checked && latest(k);
    const [w, st] = STYLE[!useStudy && data.faces[k].styles.includes(style) ? style : 'Regular'];
    return { fontFamily: `"${useStudy ? latest(k) : FAMILY[k]}", "${FAMILY[k]}", Georgia, serif`, fontWeight: w, fontStyle: st };
  }
  function apply() {
    const px = `${size.value}px`;
    const feats = [...sets].map((t) => `"${t}" 1`).join(', ') || 'normal';
    let rows = $('.t-all-rows', out);
    if (all.checked) {
      text.hidden = true;
      if (!rows) { rows = document.createElement('div'); rows.className = 't-all-rows'; out.appendChild(rows); }
      rows.replaceChildren(...FACES.map((k) => {
        const d = document.createElement('div');
        const lab = document.createElement('span'); lab.className = 'mono'; lab.textContent = study.checked && latest(k) ? latest(k) : FAMILY[k];
        const p = document.createElement('div'); p.textContent = text.textContent;
        Object.assign(p.style, css(k), { fontSize: `${Math.min(+size.value, 120)}px`, lineHeight: 1.12, overflowWrap: 'anywhere' });
        d.append(lab, p);
        return d;
      }));
    } else {
      rows?.remove();
      text.hidden = false;
      Object.assign(text.style, css(face), { fontSize: px, fontFeatureSettings: feats });
    }
  }
  size.addEventListener('input', apply);
  all.addEventListener('change', build);
  study.addEventListener('change', build);
  text.addEventListener('input', () => { gloss.textContent = ''; });
  $('[data-t-proverb]', root).addEventListener('click', () => {
    pi = (pi + 1) % PROVERBS.length;
    text.textContent = PROVERBS[pi][0];
    gloss.textContent = PROVERBS[pi][1];
    apply();
  });
  build();
}
