import { $, $$, reduced, loadFace, rng, lcs, slideFrom, watchVisible } from './util.js';

// Choose your letters. Céilí has other forms for some letters, in three stylistic sets:
// insular r and s (ss01), uncial a and n (ss02), and alternate a, d, e, j, l and v (ss03).
// The line is real text, set by the browser with the face's own spacing; a letter with
// other forms is a button that cycles them, and the whole line can be set in one hand.
// A change is gentle: the letter fades up and out, comes back in its new form, and the
// letters after it slide to where the face now sets them.

const NAMES = { ss01: 'insular', ss02: 'uncial', ss03: 'alternate' };
const MODES = [
  { id: 'plain', label: 'Plain', preview: [['a', null], ['n', null], ['r', null], ['s', null]] },
  { id: 'ss01', label: 'Insular', preview: [['r', 'ss01'], ['s', 'ss01']] },
  { id: 'ss02', label: 'Uncial', preview: [['a', 'ss02'], ['n', 'ss02']] },
  { id: 'ss03', label: 'Alternate', preview: [['a', 'ss03'], ['d', 'ss03'], ['e', 'ss03'], ['l', 'ss03'], ['v', 'ss03']] },
  { id: 'mixed', label: 'Mixed', preview: [['r', 'ss01'], ['a', 'ss02'], ['d', 'ss03']] },
];
const feat = (tag) => (tag ? `"${tag}" 1` : 'normal');

export async function init(root, data) {
  await loadFace('ceili');
  const section = root.closest('section');
  const floor = $('[data-choose-floor]', root);
  const line = $('[data-choose-line]', root);
  const said = $('[data-choose-said]', root);
  const live = $('[data-choose-live]', root);
  const input = $('[data-choose-text]', root);
  const modesHost = $('[data-choose-modes]', root);
  const formsHost = $('[data-choose-forms]', root);
  const buntingHost = $('[data-bunting]', section);
  const rand = rng(1978);

  // Which letters each set changes. The face is unicase, so a capital in the list stands
  // for both cases; a lower-case letter (j) only for itself. Accented letters follow their base.
  const sets = data.faces.ceili.sets.map((s) => {
    const has = new Set();
    for (const c of s.chars) { has.add(c); if (c !== c.toLowerCase()) has.add(c.toLowerCase()); }
    return { tag: s.tag, label: s.label, has };
  });
  const formsOf = (ch) => [null, ...sets.filter((s) => s.has.has(ch.normalize('NFD')[0])).map((s) => s.tag)];
  const formName = (tag) => (tag ? NAMES[tag] || tag : 'standard');

  let letters = [];       // {ch, word, forms, k, el}
  let mode = 'plain', current = null;

  // ------------------------------------------------------------------ the line
  function build(text, keep = []) {
    line.replaceChildren();
    letters = [];
    for (const part of text.split(/(\s+)/)) {
      if (!part) continue;
      if (/^\s+$/.test(part)) { line.append(' '); continue; }
      const w = document.createElement('span');
      w.className = 'cw';
      for (const ch of part) {
        const el = document.createElement('span');
        el.className = 'cl';
        el.textContent = ch;
        const L = { ch, word: part, forms: formsOf(ch), k: 0, el };
        if (L.forms.length > 1) {
          el.classList.add('can');
          el.setAttribute('role', 'button');
          el.tabIndex = -1;
          el.addEventListener('click', () => { pick(L); cycle(L); });
          el.addEventListener('focus', () => pick(L));
        } else el.setAttribute('aria-hidden', 'true');
        w.appendChild(el);
        letters.push(L);
      }
      line.appendChild(w);
    }
    // carry over the forms of the letters that are still there; new ones follow the line's hand
    const kept = new Set();
    for (const [i, j] of lcs(keep.map((l) => l.ch), letters.map((l) => l.ch))) { letters[j].k = keep[i].next ?? keep[i].k; kept.add(j); }
    letters.forEach((L, j) => { if (!kept.has(j)) L.k = mode ? target(L, mode) : 0; });
    letters.forEach(paint);
    const can = letters.filter((L) => L.forms.length > 1);
    (can.find((L) => L === current) || can[0])?.el.setAttribute('tabindex', '0');
    if (!can.includes(current)) current = null;
    said.textContent = text;
    fit();
    showForms();
  }

  function paint(L) {
    const tag = L.forms[L.k];
    L.el.style.fontFeatureSettings = feat(tag);
    if (tag) L.el.dataset.set = tag; else delete L.el.dataset.set;
    if (L.forms.length > 1) L.el.setAttribute('aria-label', `${L.ch} in ${L.word}: ${formName(tag)}, ${L.k + 1} of ${L.forms.length}`);
  }

  // As large as the floor allows: two lines at most on a wide floor, three on a phone,
  // with a little room to spare for a wider form.
  const widest = () => Math.max(0, ...$$('.cw', line).map((w) => w.getBoundingClientRect().width));
  function fit() {
    const avail = floor.clientWidth;
    if (!avail) return;
    const pad = parseFloat(getComputedStyle(floor).paddingLeft) * 2;
    const maxLines = avail > 700 ? 2 : 3;
    const hi = Math.min(170, Math.max(40, (avail - pad) / 3.4));
    for (let s = Math.floor(hi); s >= 30; s -= 3) {
      line.style.fontSize = `${s}px`;
      const rows = new Set($$('.cw', line).map((w) => w.offsetTop)).size;
      if (rows <= maxLines && widest() <= line.clientWidth - s * 0.25) return;
    }
  }

  // ------------------------------------------------------------------ changing a letter
  // the letter fades up and out, and back in its new form; the rest slide to their new places
  const fade = (el, from, to, duration, easing, fill = 'none') => {
    el.animate([{ top: from }, { top: to }], { duration, easing, composite: 'add' });
    return el.animate([{ opacity: from === '0em' ? 1 : 0 }, { opacity: from === '0em' ? 0 : 1 }], { duration, easing, fill });
  };
  function change(L, k, quiet = false) {
    if (k === (L.next ?? L.k)) return;
    const first = L.next === undefined;
    L.next = k;
    const swap = () => {
      if (L.next === undefined || !L.el.isConnected) return;
      const els = letters.map((l) => l.el);
      const before = els.map((el) => el.getBoundingClientRect());
      L.k = L.next;
      L.next = undefined;
      L.out?.cancel();
      paint(L);
      if (widest() > line.clientWidth) fit();   // a wider form no longer fits
      if (!reduced()) {
        slideFrom(els.map((el) => (el === L.el ? null : el)), before);
        fade(L.el, '.16em', '0em', 380, 'cubic-bezier(.2, .7, .2, 1)');
      }
      if (L === current) showForms();
    };
    if (reduced()) swap();
    else if (first) (L.out = fade(L.el, '0em', '-.14em', 150, 'ease-in', 'forwards')).onfinish = swap;
    flutter(letters.indexOf(L));
    if (!quiet) live.textContent = `${L.ch}: ${formName(L.forms[k])}`;
  }
  function cycle(L) { setMode(null); change(L, ((L.next ?? L.k) + 1) % L.forms.length); }

  function target(L, m) {
    if (m === 'plain') return 0;
    if (m === 'mixed') return (rand() * L.forms.length) | 0;
    return Math.max(0, L.forms.indexOf(m));
  }
  // A mix that uses every set it can: each letter takes the form least used so far.
  function mix(can) {
    const used = {};
    return can.map((L) => {
      if (rand() < 0.15) return 0;
      const opts = L.forms.map((t, k) => [t, k]).filter(([t]) => t).sort((a, b) => (used[a[0]] || 0) - (used[b[0]] || 0) || rand() - 0.5);
      used[opts[0][0]] = (used[opts[0][0]] || 0) + 1;
      return opts[0][1];
    });
  }
  function wholeLine(m) {
    setMode(m);
    const can = letters.filter((L) => L.forms.length > 1);
    if (m === 'mixed') {
      // a fresh mix each time, never the same as the line already is
      let ks;
      for (let tries = 0; tries < 8; tries++) {
        ks = mix(can);
        if (ks.some((k, i) => k !== can[i].k)) break;
      }
      can.forEach((L, i) => setTimeout(() => change(L, ks[i], true), reduced() ? 0 : i * 70));
    } else can.forEach((L, i) => setTimeout(() => change(L, target(L, m), true), reduced() ? 0 : i * 55));
    live.textContent = m === 'plain' ? 'The whole line in its standard letters' : m === 'mixed' ? 'The whole line mixed' : `The whole line with ${NAMES[m]} letters`;
  }

  // ------------------------------------------------------------------ the whole line at once
  const modeBtns = MODES.map((m) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'tog cm';
    b.dataset.mode = m.id;
    b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', 'false');
    const g = document.createElement('span');
    g.className = 'cm-g f-ceili';
    g.setAttribute('aria-hidden', 'true');
    for (const [ch, tag] of m.preview) {
      const s = document.createElement('span');
      s.textContent = ch;
      s.style.fontFeatureSettings = feat(tag);
      g.append(s);
    }
    b.append(g, m.label);
    b.addEventListener('click', () => wholeLine(m.id));
    modesHost.appendChild(b);
    return b;
  });
  function setMode(m) {
    mode = m;
    modeBtns.forEach((b, i) => {
      b.setAttribute('aria-checked', String(b.dataset.mode === m));
      b.tabIndex = b.dataset.mode === m || (!m && i === 0) ? 0 : -1;
    });
  }
  // a radio group is one stop for the keyboard; the arrows move along it
  modesHost.addEventListener('keydown', (e) => {
    const dir = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!dir) return;
    e.preventDefault();
    const i = modeBtns.indexOf(document.activeElement);
    const b = modeBtns[(i + dir + modeBtns.length) % modeBtns.length];
    b.focus(); b.click();
  });

  // ------------------------------------------------------------------ the letter's forms, side by side
  function pick(L) {
    if (current === L) return;
    current = L;
    letters.forEach((l) => { if (l.forms.length > 1) l.el.tabIndex = l === L ? 0 : -1; l.el.classList.toggle('on', l === L); });
    showForms();
  }
  function showForms() {
    formsHost.replaceChildren();
    if (!current) {
      const p = document.createElement('p');
      p.className = 'cf-hint';
      p.textContent = 'Tap a letter with a dot under it to see its other forms.';
      formsHost.appendChild(p);
      return;
    }
    const L = current;
    const head = document.createElement('p');
    head.className = 'cf-head mono';
    head.textContent = `${L.ch} · ${L.forms.length} forms`;
    const row = document.createElement('div');
    row.className = 'cf-row';
    row.setAttribute('role', 'group');
    row.setAttribute('aria-label', `Forms of ${L.ch}`);
    L.forms.forEach((tag, k) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'cf';
      if (tag) b.dataset.set = tag;
      b.setAttribute('aria-pressed', String(k === L.k));
      const g = document.createElement('span');
      g.className = 'cf-g f-ceili';
      g.textContent = L.ch;
      g.style.fontFeatureSettings = feat(tag);
      g.setAttribute('aria-hidden', 'true');
      const t = document.createElement('span');
      t.className = 'cf-t mono';
      t.textContent = tag ? `${formName(tag)} · ${tag}` : 'standard';
      b.append(g, t);
      b.setAttribute('aria-label', `${L.ch}, ${formName(tag)}${tag ? ` (${tag})` : ''}`);
      b.addEventListener('click', () => { setMode(null); change(L, k); });
      row.appendChild(b);
    });
    formsHost.append(head, row);
  }

  // the letters are one stop for the keyboard too: arrows move, Enter or Space changes
  line.addEventListener('keydown', (e) => {
    const can = letters.filter((L) => L.forms.length > 1);
    const i = can.indexOf(current);
    if (e.key === 'Enter' || e.key === ' ') { if (current) { e.preventDefault(); cycle(current); } return; }
    const to = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: can.length - 1 }[e.key];
    if (to === undefined || !can.length) return;
    e.preventDefault();
    can[(to + can.length) % can.length].el.focus();
  });

  // ------------------------------------------------------------------ bunting across the hall
  let flags = buildBunting(buntingHost);
  let lastW = buntingHost?.clientWidth;
  if (buntingHost) new ResizeObserver(() => {
    if (buntingHost.clientWidth === lastW) return;
    lastW = buntingHost.clientWidth;
    buntingHost.replaceChildren();
    flags = buildBunting(buntingHost);
  }).observe(buntingHost);
  // a changed letter stirs the flag above it
  function flutter(i) {
    if (reduced() || !flags.length || i < 0) return;
    const f = flags[Math.min(flags.length - 1, Math.floor((i / Math.max(1, letters.length)) * flags.length))];
    f.style.transform = `rotate(${(i % 2 ? -1 : 1) * 9}deg)`;
    setTimeout(() => { f.style.transform = ''; }, 200);
  }

  // ------------------------------------------------------------------ start
  input.addEventListener('input', () => build(input.value.replace(/\s+/g, ' ').trim() || 'céilí', letters));
  setMode('plain');
  build(input.value.trim() || 'céilí mór anocht');
  let lastFloorW = floor.clientWidth;
  new ResizeObserver(() => { if (floor.clientWidth !== lastFloorW) { lastFloorW = floor.clientWidth; fit(); } }).observe(floor);

  // The first time the hall comes into view, the line changes into a mix of its other
  // letters, one at a time, to show what it can do.
  let shown = false;
  watchVisible(floor, (v) => {
    if (!v || shown) return;
    shown = true;
    setTimeout(() => { if (mode === 'plain' && letters.every((L) => L.k === 0)) wholeLine('mixed'); }, reduced() ? 0 : 500);
  }, '-25% 0px');
}

function buildBunting(host) {
  if (!host) return [];
  const W = Math.max(320, host.clientWidth), H = 120;
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

  const colours = ['var(--ceili-pink)', 'var(--ceili-orange)', 'var(--ceili-fg)', 'var(--ceili-mint)'];
  const flags = [];
  const rand = rng(7);
  // two strings, each a gentle sag across the hall
  const sagK = Math.min(1, W / 1200);
  [[0, 14, W, 24, 70 * sagK], [0, 36, W, 10, 92 * sagK]].forEach(([x0, y0, x1, y1, sag], si) => {
    const pt = (t) => [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + Math.sin(Math.PI * t) * sag];
    const string = document.createElementNS(NS, 'path');
    let d = '';
    for (let k = 0; k <= 40; k++) { const [x, y] = pt(k / 40); d += `${k ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`; }
    string.setAttribute('d', d);
    string.setAttribute('fill', 'none');
    string.setAttribute('stroke', 'rgba(246,238,220,.55)');
    string.setAttribute('stroke-width', '1.5');
    svg.appendChild(string);
    const n = Math.max(7, Math.round(W / 62));
    for (let k = 0; k < n; k++) {
      const t = (k + 0.5 + si * 0.5) / (n + 0.5);
      const [x, y] = pt(t);
      const [xa, ya] = pt(t + 0.001);
      const ang = Math.atan2(ya - y, xa - x) * 180 / Math.PI;
      const g = document.createElementNS(NS, 'g');
      g.setAttribute('transform', `translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${ang.toFixed(1)})`);
      const f = document.createElementNS(NS, 'path');
      const fw = 20 + rand() * 4, fh = 30 + rand() * 6;
      f.setAttribute('d', `M${-fw} 0 L${fw} 0 L0 ${fh} Z`);
      f.setAttribute('class', 'flag');
      f.style.fill = colours[(k + si) % colours.length];
      g.appendChild(f);
      svg.appendChild(g);
      flags.push(f);
    }
  });
  host.appendChild(svg);
  // flags in order across the hall, so a letter stirs the one above it
  return flags.sort((a, b) => a.parentNode.transform.baseVal[0].matrix.e - b.parentNode.transform.baseVal[0].matrix.e);
}
