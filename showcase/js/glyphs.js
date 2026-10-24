import { $, FACES, FAMILY, copyText } from './util.js';

export function init(root, data) {
  const facesHost = $('[data-g-faces]', root);
  const grid = $('[data-g-grid]', root);
  const find = $('[data-g-find]', root);
  const big = $('[data-g-char]', root);
  const name = $('[data-g-name]', root);
  const code = $('[data-g-code]', root);
  const copy = $('[data-g-copy]', root);
  let face = 'kilfane', picked = 0xE1;

  FACES.forEach((k) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'tog t-face'; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(k === face));
    b.innerHTML = `<span class="f-${k}">${FAMILY[k]}</span>`;
    b.addEventListener('click', () => {
      face = k;
      [...facesHost.children].forEach((c) => c.setAttribute('aria-checked', String(c === b)));
      build();
    });
    facesHost.appendChild(b);
  });

  const hex = (cp) => cp.toString(16).toUpperCase().padStart(4, '0');
  function show(cp) {
    picked = cp;
    big.textContent = String.fromCodePoint(cp);
    big.className = `g-big-char f-${face}`;
    name.textContent = data.names[hex(cp)] || 'Unnamed';
    code.textContent = `U+${hex(cp)}`;
    for (const c of grid.children) c.setAttribute('aria-pressed', String(+c.dataset.cp === cp));
  }

  function build() {
    const q = find.value.trim().toUpperCase();
    const cps = data.faces[face].cps.filter((cp) => !q || (data.names[hex(cp)] || '').includes(q) || String.fromCodePoint(cp) === find.value.trim());
    const frag = document.createDocumentFragment();
    for (const cp of cps) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = `g-cell f-${face}`; b.dataset.cp = cp;
      b.textContent = String.fromCodePoint(cp);
      b.setAttribute('aria-label', data.names[hex(cp)] || `U+${hex(cp)}`);
      frag.appendChild(b);
    }
    grid.replaceChildren(frag);
    show(cps.includes(picked) ? picked : cps[0] ?? 0x61);
  }
  grid.addEventListener('click', (e) => { const b = e.target.closest('.g-cell'); if (b) show(+b.dataset.cp); });
  grid.addEventListener('pointerover', (e) => { const b = e.target.closest('.g-cell'); if (b && e.pointerType === 'mouse') show(+b.dataset.cp); });
  find.addEventListener('input', build);
  copy.addEventListener('click', () => copyText(String.fromCodePoint(picked), copy));
  build();
}
