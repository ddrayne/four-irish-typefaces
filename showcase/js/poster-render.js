import { trace } from './poster-type.js';
import { rng } from './util.js';

// Three ways to print the same two plates:
//   raster(): a canvas, as a risograph prints it: each ink its own layer, grainy where the
//             drum ran short, a little out of register, multiplied onto the paper
//   svg():    clean vectors, the two inks multiplied over the paper colour
//   pdf():    clean vectors at the paper size: the poster, then each ink as its own plate
//             (black, for a print shop's masters). The paper is left to the paper.

const FINISH = {
  clean: { grain: 0, shift: 0, patch: 0, streak: 0, fibre: 0 },
  riso: { grain: 0.07, shift: 0.0035, patch: 0.16, streak: 0.05, fibre: 1 },
  worn: { grain: 0.16, shift: 0.009, patch: 0.38, streak: 0.16, fibre: 1.4 },
};

const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };

let grainTile = null;
function grain() {
  if (grainTile) return grainTile;
  const N = 512, c = canvas(N, N), x = c.getContext('2d');
  const img = x.createImageData(N, N), r = rng(53909);
  // alpha: a fine speckle, where the stencil passed no ink
  for (let i = 0; i < N * N; i++) { const v = r(); img.data[i * 4 + 3] = v < 0.5 ? Math.round(255 * Math.pow(v * 2, 6)) : 0; }
  x.putImageData(img, 0, 0);
  return (grainTile = c);
}

function noise(w, h, seed, amp) {
  const c = canvas(w, h), x = c.getContext('2d'), img = x.createImageData(c.width, c.height), r = rng(seed);
  for (let i = 0; i < c.width * c.height; i++) img.data[i * 4 + 3] = Math.round(255 * amp * Math.pow(r(), 2.2));
  x.putImageData(img, 0, 0);
  return c;
}

/**
 * Print the plates onto a canvas `px` pixels wide. inks: two hex colours; paper: hex.
 * finish: clean, riso or worn; seed: which print of the run (misregistration, grain).
 */
export function raster(doc, { px, inks, paper, finish = 'riso', seed = 1978, into = null }) {
  const { W, H, plates } = doc;
  const F = FINISH[finish] || FINISH.riso;
  const k = px / W;
  const w = Math.round(W * k), h = Math.round(H * k);
  const out = into || canvas(w, h);
  if (into) { into.width = w; into.height = h; }
  const o = out.getContext('2d');
  o.globalCompositeOperation = 'source-over';
  o.fillStyle = paper; o.fillRect(0, 0, w, h);
  const plate = canvas(w, h), p = plate.getContext('2d');
  const r = rng(seed);
  plates.forEach((ops, n) => {
    p.setTransform(1, 0, 0, 1, 0, 0);
    p.globalCompositeOperation = 'source-over';
    p.clearRect(0, 0, w, h);
    p.setTransform(k, 0, 0, k, 0, 0);
    p.fillStyle = inks[n];
    for (const op of ops) {
      p.globalCompositeOperation = op.erase ? 'destination-out' : 'source-over';
      p.beginPath(); trace(p, op.c); p.fill('nonzero');
    }
    p.setTransform(1, 0, 0, 1, 0, 0);
    p.globalCompositeOperation = 'destination-out';
    if (F.grain) {
      const pat = p.createPattern(grain(), 'repeat');
      const gk = Math.max(1, k * 0.42);
      pat.setTransform(new DOMMatrix().translate(r() * 512, r() * 512).scale(gk));
      p.globalAlpha = Math.min(1, F.grain * 7);
      p.fillStyle = pat; p.fillRect(0, 0, w, h);
    }
    if (F.patch) {
      // uneven inking: soft patches where the drum ran short
      p.globalAlpha = 1; p.imageSmoothingEnabled = true; p.imageSmoothingQuality = 'high';
      p.drawImage(noise(14, Math.round(14 * H / W), seed * 7 + n, F.patch), 0, 0, w, h);
    }
    if (F.streak) {
      p.drawImage(noise(90, 1, seed * 13 + n, F.streak), 0, 0, w, h);
    }
    p.globalAlpha = 1;
    o.globalCompositeOperation = 'multiply';
    const dx = (r() - 0.5) * 2 * F.shift * W * k, dy = (r() - 0.5) * 2 * F.shift * W * k;
    o.drawImage(plate, Math.round(dx), Math.round(dy));
  });
  o.globalCompositeOperation = 'source-over';
  if (F.fibre) {
    const fr = rng(7), n = Math.round((w * h) / 230 * F.fibre), s = Math.max(1, k * 1.1);
    for (let i = 0; i < n; i++) { o.fillStyle = fr() < 0.5 ? 'rgba(0,0,0,.035)' : 'rgba(255,255,255,.06)'; o.fillRect(fr() * w, fr() * h, s, s); }
  }
  plate.width = plate.height = 0;
  return out;
}

// ---------------------------------------------------------------- vectors
const num = (v) => { const s = (Math.round(v * 10) / 10).toString(); return s === '-0' ? '0' : s; };
function svgPath(cmds) {
  const d = [];
  for (let i = 0; i < cmds.length;) {
    const op = cmds[i++];
    if (op === 0) { d.push(`M${num(cmds[i])} ${num(cmds[i + 1])}`); i += 2; }
    else if (op === 1) { d.push(`L${num(cmds[i])} ${num(cmds[i + 1])}`); i += 2; }
    else if (op === 2) { d.push(`C${num(cmds[i])} ${num(cmds[i + 1])} ${num(cmds[i + 2])} ${num(cmds[i + 3])} ${num(cmds[i + 4])} ${num(cmds[i + 5])}`); i += 6; }
    else d.push('Z');
  }
  return d.join('');
}
const esc = (s) => s.replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));

// Each fill is cut by every erase that follows it on its plate.
function masked(ops) {
  const out = [];
  let after = [];
  for (let i = ops.length - 1; i >= 0; i--) {
    if (ops[i].erase) after = [ops[i].c, ...after];
    else out.unshift({ c: ops[i].c, cuts: after });
  }
  return out;
}

/** The poster as an SVG document (a string). sizeMM: [width, height] of the sheet. */
export function svg(doc, { inks, inkNames, paper, sizeMM, title }) {
  const { W, H, plates } = doc;
  const defs = [], body = [];
  let mid = 0;
  const maskFor = new Map();
  plates.forEach((ops, n) => {
    const parts = [];
    for (const f of masked(ops)) {
      let attr = '';
      if (f.cuts.length) {
        const key = f.cuts;
        if (!maskFor.has(key)) {
          const id = `cut${++mid}`;
          maskFor.set(key, id);
          defs.push(`<mask id="${id}" maskUnits="userSpaceOnUse" x="0" y="0" width="${num(W)}" height="${num(H)}"><rect width="${num(W)}" height="${num(H)}" fill="#fff"/>${f.cuts.map((c) => `<path fill="#000" d="${svgPath(c)}"/>`).join('')}</mask>`);
        }
        attr = ` mask="url(#${maskFor.get(key)})"`;
      }
      parts.push(`<path${attr} d="${svgPath(f.c)}"/>`);
    }
    const slug = inkNames[n].toLowerCase().replace(/[^a-z]+/g, '-');
    body.push(`<g id="ink-${n + 1}-${slug}" fill="${inks[n]}" style="mix-blend-mode:multiply">${parts.join('')}</g>`);
  });
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${sizeMM[0]}mm" height="${sizeMM[1]}mm" viewBox="0 0 ${num(W)} ${num(H)}">
<title>${esc(title)}</title>
${defs.length ? `<defs>${defs.join('')}</defs>\n` : ''}<rect id="paper" width="${num(W)}" height="${num(H)}" fill="${paper}"/>
${body.join('\n')}
</svg>
`;
}

// ---------------------------------------------------------------- PDF
const hexRGB = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
const f3 = (v) => (Math.round(v * 1000) / 1000).toString();
function pdfPath(cmds) {
  const d = [];
  for (let i = 0; i < cmds.length;) {
    const op = cmds[i++];
    if (op === 0) { d.push(`${num(cmds[i])} ${num(cmds[i + 1])} m`); i += 2; }
    else if (op === 1) { d.push(`${num(cmds[i])} ${num(cmds[i + 1])} l`); i += 2; }
    else if (op === 2) { d.push(`${num(cmds[i])} ${num(cmds[i + 1])} ${num(cmds[i + 2])} ${num(cmds[i + 3])} ${num(cmds[i + 4])} ${num(cmds[i + 5])} c`); i += 6; }
    else d.push('h');
  }
  return d.join('\n');
}
const pdfText = (s) => `<FEFF${[...s].map((c) => { const u = c.codePointAt(0); return u > 0xFFFF ? '' : u.toString(16).padStart(4, '0').toUpperCase(); }).join('')}>`;

async function deflate(text) {
  const bytes = new TextEncoder().encode(text);
  if (typeof CompressionStream === 'undefined') return { bytes, filter: '' };
  try {
    const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream('deflate'));
    return { bytes: new Uint8Array(await new Response(stream).arrayBuffer()), filter: '/Filter /FlateDecode ' };
  } catch { return { bytes, filter: '' }; }
}

/** The poster as a PDF (a Blob): page 1 in its inks, then a page per ink in black. */
export async function pdf(doc, { inks, inkNames, sizeMM, title }) {
  const { W, H, plates } = doc;
  const pw = sizeMM[0] / 25.4 * 72, ph = sizeMM[1] / 25.4 * 72;
  const s = pw / W;
  const objs = [];                     // [dict, streamText?]
  const add = (dict, stream) => { objs.push({ dict, stream }); return objs.length; };
  const catalog = add('');            // filled in below
  const pages = add('');
  const toUnits = `${f3(s)} 0 0 ${f3(-s)} 0 ${f3(ph)} cm`;
  const box = `/BBox [0 0 ${f3(pw)} ${f3(ph)}]`;
  // a plate as a transparency group, its fills cut by luminosity masks
  function plateForm(ops, rgb) {
    const gs = [];
    const body = [toUnits, `${rgb.map(f3).join(' ')} rg`];
    for (const f of masked(ops)) {
      if (f.cuts.length) {
        // a soft mask is drawn in the space in force where it is set: here, poster units
        const m = add(`/Type /XObject /Subtype /Form /BBox [0 0 ${num(W)} ${num(H)}] /Group << /S /Transparency /CS /DeviceGray >>`,
          `1 g\n0 0 ${num(W)} ${num(H)} re f\n0 g\n${f.cuts.map(pdfPath).join('\n')}\nf`);
        gs.push(`/K${gs.length} << /Type /ExtGState /SMask << /Type /Mask /S /Luminosity /G ${m} 0 R >> >>`);
        body.push(`q /K${gs.length - 1} gs\n${pdfPath(f.c)}\nf Q`);
      } else body.push(`${pdfPath(f.c)}\nf`);
    }
    return add(`/Type /XObject /Subtype /Form ${box} /Group << /S /Transparency /CS /DeviceRGB /I true >> /Resources << /ExtGState << ${gs.join(' ')} >> >>`, body.join('\n'));
  }
  const kids = [];
  const page = (forms, multiply) => {
    const xo = forms.map((f, i) => `/P${i} ${f} 0 R`).join(' ');
    const content = add('', `${multiply ? '/M gs\n' : ''}${forms.map((_, i) => `/P${i} Do`).join('\n')}`);
    kids.push(add(`/Type /Page /Parent ${pages} 0 R /MediaBox [0 0 ${f3(pw)} ${f3(ph)}] /Resources << /XObject << ${xo} >> /ExtGState << /M << /Type /ExtGState /BM /Multiply >> >> >> /Contents ${content} 0 R`));
  };
  const inkForms = plates.map((ops, n) => plateForm(ops, hexRGB(inks[n])));
  page(inkForms, true);
  plates.forEach((ops) => page([plateForm(ops, [0, 0, 0])], false));
  objs[catalog - 1].dict = `/Type /Catalog /Pages ${pages} 0 R /PageLabels << /Nums [0 << /P (Poster) >> 1 << /P (${inkNames[0].replace(/[()\\]/g, '')} plate) >> 2 << /P (${inkNames[1].replace(/[()\\]/g, '')} plate) >>] >>`;
  objs[pages - 1].dict = `/Type /Pages /Kids [${kids.map((k) => `${k} 0 R`).join(' ')}] /Count ${kids.length}`;
  const info = add(`/Title ${pdfText(title)} /Creator (Four Irish Typefaces poster maker)`);

  const enc = new TextEncoder();
  const chunks = [enc.encode('%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')];
  const offsets = [];
  let pos = chunks[0].length;
  for (let i = 0; i < objs.length; i++) {
    offsets.push(pos);
    const { dict, stream } = objs[i];
    let parts;
    if (stream !== undefined) {
      const { bytes, filter } = await deflate(stream);
      parts = [enc.encode(`${i + 1} 0 obj\n<< ${dict} ${filter}/Length ${bytes.length} >>\nstream\n`), bytes, enc.encode('\nendstream\nendobj\n')];
    } else parts = [enc.encode(`${i + 1} 0 obj\n<< ${dict} >>\nendobj\n`)];
    for (const p of parts) { chunks.push(p); pos += p.length; }
  }
  const xref = [`xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`, ...offsets.map((o) => `${String(o).padStart(10, '0')} 00000 n \n`)].join('');
  chunks.push(enc.encode(`${xref}trailer\n<< /Size ${objs.length + 1} /Root ${catalog} 0 R /Info ${info} 0 R >>\nstartxref\n${pos}\n%%EOF\n`));
  return new Blob(chunks, { type: 'application/pdf' });
}
