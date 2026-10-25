// Type for the poster maker, set from the fonts' own outlines (data/outlines, written by
// scripts/showcase.py) rather than by the browser, so that the preview, the PNG, the SVG
// and the PDF are all the same drawing. Kerning comes from each font's kern feature, and
// the stylistic sets are applied as the fonts define them.
//
// Geometry is kept as flat command lists in poster units (y down):
//   0 x y  move · 1 x y  line · 2 x1 y1 x2 y2 x y  curve · 3  close

const FILE = { ceili: 'CeiliDigital', carrick: 'CarrickDigital', kilfane: 'KilfaneDigital', tuam: 'TuamUncialDigital' };
const fonts = new Map();

export function loadFont(face, style = 'Regular') {
  const key = `${face}|${style}`;
  if (!fonts.has(key)) {
    const url = `data/outlines/${FILE[face]}-${style.replace(' ', '')}.json`;
    fonts.set(key, fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${url}: ${r.status}`);
      return r.json();
    }).then((d) => new Font(d)).catch((err) => { fonts.delete(key); throw err; }));
  }
  return fonts.get(key);
}

class Font {
  constructor(d) {
    [this.upm, this.asc, this.desc, this.cap, this.xh] = d.m;
    this.face = d.face;
    this.style = d.style;
    this.cmap = new Map(Object.entries(d.cmap).map(([k, v]) => [+k, v]));
    this.g = d.g;
    this.paths = [];
    this.kern = new Map(d.kern.map(([a, b, v]) => [a * 65536 + b, v]));
    this.sets = d.sets.map((s) => ({ tag: s.tag, label: s.label, map: new Map(Object.entries(s.map).map(([k, v]) => [+k, v])) }));
    this.space = this.cmap.has(32) ? this.g[this.cmap.get(32)][0] : this.upm / 4;
    this.runs = new Map();
  }

  /** A glyph's outline as commands, in font units (y up). */
  path(gi) {
    let p = this.paths[gi];
    if (!p) {
      p = [];
      for (const [, op, args] of this.g[gi][2].matchAll(/([MLCZ])([^MLCZ]*)/g)) {
        const n = args.trim() ? args.trim().split(' ').map(Number) : [];
        if (op === 'M') p.push(0, n[0], n[1]);
        else if (op === 'L') for (let i = 0; i < n.length; i += 2) p.push(1, n[i], n[i + 1]);
        else if (op === 'C') for (let i = 0; i < n.length; i += 6) p.push(2, n[i], n[i + 1], n[i + 2], n[i + 3], n[i + 4], n[i + 5]);
        else p.push(3);
      }
      this.paths[gi] = p;
    }
    return p;
  }

  glyph(ch) {
    const cp = ch.codePointAt(0);
    if (this.cmap.has(cp)) return this.cmap.get(cp);
    // a letter the font lacks: its base letter, without the accent
    const base = ch.normalize('NFD')[0];
    if (base !== ch && this.cmap.has(base.codePointAt(0))) return this.cmap.get(base.codePointAt(0));
    const sub = { '’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-', '…': '.' }[ch];
    return sub && this.cmap.has(sub.codePointAt(0)) ? this.cmap.get(sub.codePointAt(0)) : -1;
  }

  /**
   * Set one line: [{gi, x}] in font units, its advance width, and its ink bounds
   * (l, r left and right; t, b top and bottom, y up). tags: stylistic sets to apply.
   */
  run(text, tags = []) {
    const key = `${tags.join(',')}|${text}`;
    let r = this.runs.get(key);
    if (r) return r;
    const sets = this.sets.filter((s) => tags.includes(s.tag));
    const gs = [];
    let x = 0, prev = -1;
    for (const ch of text.normalize('NFC')) {
      let gi = this.glyph(ch);
      if (gi < 0) { x += this.space; prev = -1; continue; }
      for (const s of sets) if (s.map.has(gi)) gi = s.map.get(gi);
      if (prev >= 0) x += this.kern.get(prev * 65536 + gi) || 0;
      gs.push({ gi, x });
      x += this.g[gi][0];
      prev = gi;
    }
    let l = Infinity, rr = -Infinity, t = -Infinity, b = Infinity;
    for (const { gi, x: gx } of gs) {
      const box = this.g[gi][1];
      if (!box) continue;
      l = Math.min(l, gx + box[0]); rr = Math.max(rr, gx + box[2]);
      b = Math.min(b, box[1]); t = Math.max(t, box[3]);
    }
    if (l === Infinity) { l = 0; rr = 0; t = 0; b = 0; }
    r = { text, gs, w: x, l, r: rr, t, b, font: this };
    if (this.runs.size > 400) this.runs.clear();
    this.runs.set(key, r);
    return r;
  }
}

/**
 * Append a run's outlines to cmds. size: the type size in poster units. (x, y): where the
 * run's origin on its baseline goes. ex, ey: the directions of the baseline and of "up"
 * (normally [1, 0] and [0, -1]; turned for type that runs up the sheet).
 */
export function outline(cmds, run, size, x, y, ex = [1, 0], ey = [0, -1]) {
  const k = size / run.font.upm;
  for (const { gi, x: gx } of run.gs) {
    const p = run.font.path(gi);
    for (let i = 0; i < p.length;) {
      const op = p[i++];
      cmds.push(op);
      const n = op === 0 || op === 1 ? 1 : op === 2 ? 3 : 0;
      for (let j = 0; j < n; j++) {
        const u = (p[i++] + gx) * k, v = p[i++] * k;
        cmds.push(x + u * ex[0] + v * ey[0], y + u * ex[1] + v * ey[1]);
      }
    }
  }
  return cmds;
}

export function rect(cmds, x, y, w, h) {
  cmds.push(0, x, y, 1, x + w, y, 1, x + w, y + h, 1, x, y + h, 3);
  return cmds;
}

export function circle(cmds, cx, cy, r) {
  const c = r * 0.5522847;
  cmds.push(0, cx + r, cy,
    2, cx + r, cy + c, cx + c, cy + r, cx, cy + r,
    2, cx - c, cy + r, cx - r, cy + c, cx - r, cy,
    2, cx - r, cy - c, cx - c, cy - r, cx, cy - r,
    2, cx + c, cy - r, cx + r, cy - c, cx + r, cy, 3);
  return cmds;
}

/** Walk a command list, calling the canvas-style methods of target (a 2D context or a recorder). */
export function trace(target, cmds) {
  for (let i = 0; i < cmds.length;) {
    const op = cmds[i++];
    if (op === 0) { target.moveTo(cmds[i], cmds[i + 1]); i += 2; }
    else if (op === 1) { target.lineTo(cmds[i], cmds[i + 1]); i += 2; }
    else if (op === 2) { target.bezierCurveTo(cmds[i], cmds[i + 1], cmds[i + 2], cmds[i + 3], cmds[i + 4], cmds[i + 5]); i += 6; }
    else target.closePath();
  }
}
