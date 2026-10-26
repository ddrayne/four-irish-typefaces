import { $, loadFace, loadScript, fitCanvas, offscreen, rng, watchVisible, reduced, lcs, PROVERBS } from './util.js';

// Carrick is from carraig, rock. Its letters are stones that tumble in and settle into
// courses of properly set type, like a drystone wall built from words. Each stone's
// place is where Carrick itself sets that letter: the line is measured on a canvas with
// the font's spacing and kerning (each letter goes where the text before it, kerned,
// ends). The collision shape is the convex hull of the letter as drawn, so a c sits
// differently from an l. Knock a stone out and it finds its way back to its place;
// Shake brings the wall down, and it builds itself again, bottom course first.

const PROVERB = 'de réir a chéile a thógtar na caisleáin';
const STONE = ['#16170F', '#25261D', '#33332A', '#1E2018', '#2C2A22'];
const LICHEN = ['#E09A17', '#D8B13A', '#C98A12', '#A8B04A'];
const LH = 1.04;            // course height, in ems
const DESC = 0.213;         // Carrick's descender, in ems
// collision categories: the ground and sides; stones laid in the wall; loose stones
const GROUND = 1, LAID = 2, LOOSE = 4;

function hull(points) {
  const pts = points.slice().sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower = [], upper = [];
  for (const p of pts) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop(); lower.push(p); }
  for (let i = pts.length - 1; i >= 0; i--) { const p = pts[i]; while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop(); upper.push(p); }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

function simplify(poly, minLen) {
  // Drop vertices closer than minLen to the previous kept vertex.
  const out = [];
  for (const p of poly) {
    const q = out[out.length - 1];
    if (!q || Math.hypot(p.x - q.x, p.y - q.y) >= minLen) out.push(p);
  }
  return out.length >= 3 ? out : poly;
}

/** Break words into k lines, each no wider than limit, as evenly as can be (least sum of squared widths). */
function balance(words, ww, sp, k, limit) {
  const n = words.length;
  const width = (i, j) => ww.slice(i, j).reduce((a, b) => a + b, 0) + sp * (j - i - 1);
  // best[l][i]: the cost of setting words i.. in l lines
  const best = Array.from({ length: k + 1 }, () => new Array(n + 1).fill(Infinity));
  const cut = Array.from({ length: k + 1 }, () => new Array(n + 1).fill(-1));
  best[0][n] = 0;
  for (let l = 1; l <= k; l++) for (let i = n - 1; i >= 0; i--) {
    for (let j = i + 1; j <= n; j++) {
      const w = width(i, j);
      if (w > limit) break;
      const c = w * w + best[l - 1][j];
      if (c < best[l][i]) { best[l][i] = c; cut[l][i] = j; }
    }
  }
  const lines = [];
  for (let l = k, i = 0; l > 0 && i < n; l--) { const j = cut[l][i]; lines.push(words.slice(i, j).join(' ')); i = j; }
  return lines;
}

/**
 * Set text in courses, centred, at the largest size that fits the field: the lines are
 * balanced, and every letter is placed where the font's own shaping puts it.
 * Returns {size, glyphs: [{ch, x, base, line}]}.
 */
function setCourses(text, W, H, font) {
  const m = offscreen(1, 1).getContext('2d');
  m.fontKerning = 'normal';
  const words = text.normalize('NFC').trim().split(/\s+/).filter(Boolean);
  if (!words.length) return { size: 0, glyphs: [] };
  const padX = Math.max(14, W * 0.045), availW = W - padX * 2;
  const availH = H * 0.8;                  // the top of the field is left for stones to fall through
  for (let size = Math.floor(Math.min(168, availW / 2.6, availH / LH)); size >= 18; size -= 2) {
    m.font = font(size);
    const lh = size * LH, sp = m.measureText(' ').width;
    const ww = words.map((w) => m.measureText(w).width);
    const wrap = (limit) => {
      const lines = [];
      let cur = [], w = 0;
      for (let k = 0; k < words.length; k++) {
        if (ww[k] > limit) return null;
        if (cur.length && w + sp + ww[k] > limit) { lines.push(cur); cur = []; w = 0; }
        w += (cur.length ? sp : 0) + ww[k];
        cur.push(words[k]);
      }
      lines.push(cur);
      return lines;
    };
    const fewest = wrap(availW);
    if (!fewest || fewest.length * lh > availH) continue;
    const lines = balance(words, ww, sp, fewest.length, availW);
    const glyphs = [];
    const lastBase = H - size * 0.1 - size * DESC;
    lines.forEach((t, li) => {
      const x0 = (W - m.measureText(t).width) / 2, base = lastBase - (lines.length - 1 - li) * lh;
      const chars = [...t];
      let pre = '';
      chars.forEach((ch) => {
        pre += ch;
        // where this letter starts: the end of the kerned text up to and including it, less its own advance
        if (/\S/.test(ch)) glyphs.push({ ch, x: x0 + m.measureText(pre).width - m.measureText(ch).width, base, line: li });
      });
    });
    return { size, glyphs, lines: lines.length };
  }
  return { size: 0, glyphs: [] };
}

export async function init(root) {
  await Promise.all([loadFace('carrick'), window.Matter ? null : loadScript('vendor/matter.min.js')]);
  const M = window.Matter;
  const field = $('[data-wall-field]', root);
  const canvas = $('[data-wall-canvas]', root);
  const input = $('[data-wall-input]', root);
  const gloss = $('[data-wall-gloss]', root);
  const shakeBtn = $('[data-wall-shake]', root);
  const rand = rng(53913);
  const font = (px) => `${px}px "Carrick Digital"`;

  const engine = M.Engine.create({ enableSleeping: true });
  engine.gravity.y = 1;
  engine.positionIterations = 8;
  engine.velocityIterations = 6;
  const world = engine.world;

  let W = 0, H = 0, ctx = null, size = 0, bg = null, text = '';
  let ground = [];
  let stones = [];
  let queue = [];
  const sprites = new Map();
  const now = () => performance.now();

  // ------------------------------------------------------------------ stones
  function sprite(ch, tone, mossy, seed) {
    const key = `${ch}|${tone}|${mossy}|${seed}|${size}`;
    if (sprites.has(key)) return sprites.get(key);
    const r = Math.min(window.devicePixelRatio || 1, 2);
    const m = offscreen(1, 1).getContext('2d');
    m.font = font(size);
    const tm = m.measureText(ch);
    const padPx = Math.ceil(size * 0.08);
    const w = Math.ceil(tm.actualBoundingBoxLeft + tm.actualBoundingBoxRight) + padPx * 2;
    const h = Math.ceil(tm.actualBoundingBoxAscent + tm.actualBoundingBoxDescent) + padPx * 2;
    if (w <= padPx * 2 || h <= padPx * 2) return null;
    const ox = padPx + tm.actualBoundingBoxLeft, oy = padPx + tm.actualBoundingBoxAscent;   // the letter's origin, on its baseline
    // the hull, from the letter's own pixels
    const mask = offscreen(w, h).getContext('2d', { willReadFrequently: true });
    mask.font = font(size); mask.fillStyle = '#000'; mask.fillText(ch, ox, oy);
    const a = mask.getImageData(0, 0, w, h).data;
    const pts = [];
    for (let y = 0; y < h; y++) {
      let lo = -1, hi = -1;
      for (let x = 0; x < w; x++) if (a[(y * w + x) * 4 + 3] > 110) { if (lo < 0) lo = x; hi = x; }
      if (lo >= 0) { pts.push({ x: lo, y }, { x: hi + 1, y }, { x: lo, y: y + 1 }, { x: hi + 1, y: y + 1 }); }
    }
    if (pts.length < 6) return null;
    const poly = simplify(hull(pts), size * 0.05);
    const centre = M.Vertices.centre(poly);
    // the drawing: soft shadow, stone tone, lichen, a highlight along the top edge
    const sr = rng(seed);
    const c = offscreen(w * r, h * r);
    const x = c.getContext('2d');
    x.scale(r, r);
    x.font = font(size);
    x.shadowColor = 'rgba(30, 26, 15, .35)'; x.shadowBlur = size * 0.05; x.shadowOffsetY = size * 0.03;
    x.fillStyle = tone; x.fillText(ch, ox, oy);
    x.shadowColor = 'transparent';
    x.globalCompositeOperation = 'source-atop';
    const g = x.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, 'rgba(255,255,255,.10)'); g.addColorStop(0.35, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(0,0,0,.12)');
    x.fillStyle = g; x.fillRect(0, 0, w, h);
    for (let k = 0; k < 90; k++) { // grain
      x.fillStyle = sr() < 0.5 ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.12)';
      x.fillRect(sr() * w, sr() * h, 1.2, 1.2);
    }
    if (mossy) {
      // a crust of lichen, in a tight cluster
      const cx = sr() * w, cy = sr() * h * 0.7;
      const col = LICHEN[(sr() * LICHEN.length) | 0];
      for (let k = 0; k < 14; k++) {
        x.fillStyle = col;
        x.globalAlpha = 0.45 + sr() * 0.4;
        x.beginPath();
        x.arc(cx + (sr() - 0.5) * size * 0.2, cy + (sr() - 0.5) * size * 0.14, size * (0.006 + sr() * 0.014), 0, Math.PI * 2);
        x.fill();
      }
      x.globalAlpha = 1;
    }
    const s = { c, w, h, poly, ox, oy, cx: centre.x, cy: centre.y };
    sprites.set(key, s);
    return s;
  }

  const filters = {
    laid: { category: LAID, mask: LOOSE, group: 0 },
    solid: { category: LOOSE, mask: GROUND | LAID | LOOSE, group: 0 },
    ghost: { category: LOOSE, mask: GROUND, group: 0 },          // still overlapping something: falls through it
    none: { category: 0, mask: 0, group: 0 },
  };
  const filter = (s, f) => { s.body.collisionFilter = { ...filters[f] }; s.ghost = f === 'ghost'; };

  /** Cut a stone's body (again, if the type size has changed) at a position and angle. */
  function cut(s, x, y, angle) {
    const sp = sprite(s.ch, s.tone, s.mossy, s.seed);
    if (!sp) return false;
    if (s.body) M.Composite.remove(world, s.body);
    s.sp = sp;
    s.body = M.Bodies.fromVertices(x, y, [sp.poly], { friction: 0.9, frictionStatic: 1.4, restitution: 0.05, density: 0.0024, slop: 0.02 });
    if (!s.body) return false;
    M.Body.setAngle(s.body, angle);
    M.Composite.add(world, s.body);
    return true;
  }
  const homeOf = (s, g) => ({ x: g.x - s.sp.ox + s.sp.cx, y: g.base - s.sp.oy + s.sp.cy });

  function lay(s) {
    M.Body.setStatic(s.body, true);
    M.Body.setPosition(s.body, s.home);
    M.Body.setAngle(s.body, 0);
    filter(s, 'laid');
    s.state = 'laid';
    // a loose stone lying where this one goes is not shoved out of the way: it lies in front
    for (const o of stones) {
      if (o.state === 'loose' && !o.ghost && M.Query.collides(o.body, [s.body]).length) filter(o, 'ghost');
    }
  }
  function goHome(s) {
    const v = s.body.velocity;
    s.v = { x: v.x, y: v.y, a: s.body.angularVelocity };
    M.Body.setStatic(s.body, true);
    filter(s, 'none');
    // turn the short way back upright
    const a = s.body.angle;
    M.Body.setAngle(s.body, a - Math.PI * 2 * Math.round(a / (Math.PI * 2)));
    s.state = 'homing';
  }
  function loosen(s, vx, vy, va, wait, orderly = false) {
    if (s.state === 'gone') return;
    if (s.body.isStatic) M.Body.setStatic(s.body, false);
    filter(s, 'ghost');
    M.Sleeping.set(s.body, false);
    M.Body.setVelocity(s.body, { x: vx, y: vy });
    M.Body.setAngularVelocity(s.body, va);
    Object.assign(s, { state: 'loose', t0: now(), wait, orderly, still: 0, falling: false });
  }
  function discard(s) {
    if (s.body.isStatic) M.Body.setStatic(s.body, false);
    filter(s, 'none');
    M.Sleeping.set(s.body, false);
    M.Body.setVelocity(s.body, { x: (rand() - 0.5) * 4, y: -2 - rand() * 3 });
    M.Body.setAngularVelocity(s.body, (rand() - 0.5) * 0.2);
    s.state = 'gone';
  }
  function newStone(ch) {
    return { ch, tone: STONE[(rand() * STONE.length) | 0], mossy: rand() < 0.2, seed: (rand() * 1e9) | 0, state: 'new' };
  }

  // ------------------------------------------------------------------ the field
  function makeGround() {
    if (ground.length) M.Composite.remove(world, ground);
    const t = 400, o = { isStatic: true, friction: 1, collisionFilter: { category: GROUND, mask: LOOSE, group: 0 } };
    ground = [
      M.Bodies.rectangle(W / 2, H + t / 2, W * 3, t, o),
      M.Bodies.rectangle(-t / 2, H / 2 - H, t, H * 4, o),
      M.Bodies.rectangle(W + t / 2, H / 2 - H, t, H * 4, o),
    ];
    M.Composite.add(world, ground);
  }

  function makeBg() {
    const r = Math.min(window.devicePixelRatio || 1, 2);
    bg = offscreen(W * r, H * r);
    const x = bg.getContext('2d');
    x.scale(r, r);
    const g = x.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#C7C2B3'); g.addColorStop(1, '#B3AD9C');
    x.fillStyle = g; x.fillRect(0, 0, W, H);
    const rr = rng(2);
    for (let k = 0; k < (W * H) / 90; k++) {
      x.fillStyle = rr() < 0.5 ? 'rgba(255,255,255,.12)' : 'rgba(40,36,26,.10)';
      const s = rr() * 1.8 + 0.4;
      x.fillRect(rr() * W, rr() * H, s, s);
    }
    // the grykes of a limestone pavement
    x.strokeStyle = 'rgba(40,36,26,.06)'; x.lineWidth = 1.2;
    for (let k = 0; k < 7; k++) {
      x.beginPath();
      let px = rr() * W, py = 0;
      x.moveTo(px, py);
      while (py < H) { px += (rr() - 0.5) * 40; py += 30 + rr() * 30; x.lineTo(px, py); }
      x.stroke();
    }
  }

  // ------------------------------------------------------------------ building
  /**
   * Set the wall's words. Stones whose letters are still in the text keep their place
   * in the order and move to their new one; new letters fall in, bottom course first;
   * stones no longer wanted drop away.
   */
  function build(next, animate = !reduced()) {
    text = next;
    canvas.setAttribute('aria-label', `The words “${text}” set in Carrick, each letter a stone in a drystone wall`);
    const L = setCourses(text, W, H, font);
    const resized = L.size !== size;
    size = L.size;
    const old = stones.filter((s) => s.state !== 'gone' && s.state !== 'new');
    queue = [];
    stones = stones.filter((s) => s.state === 'gone');
    const placed = new Array(L.glyphs.length);
    for (const [i, j] of lcs(old.map((s) => s.ch), L.glyphs.map((g) => g.ch))) placed[j] = old[i];
    for (const s of old) if (!placed.includes(s)) { if (animate) { discard(s); stones.push(s); } else M.Composite.remove(world, s.body); }
    // bottom course first, each course from the left, as a waller builds
    const order = L.glyphs.map((g, j) => j).sort((a, b) => L.glyphs[b].line - L.glyphs[a].line || a - b);
    let delay = 0;
    order.forEach((j, rank) => {
      const g = L.glyphs[j];
      let s = placed[j];
      if (s && resized) {
        const { x, y } = s.body.position;
        if (!cut(s, x, y, s.body.angle)) return;
        if (s.state === 'laid') { s.state = 'homing'; s.v = { x: 0, y: 0, a: 0 }; M.Body.setStatic(s.body, true); filter(s, 'none'); }
        else if (s.state === 'homing') { M.Body.setStatic(s.body, true); filter(s, 'none'); }
        else filter(s, 'ghost');
      }
      if (!s) {
        s = newStone(g.ch);
        if (!cut(s, -9999, -9999, 0)) return;
        s.home = homeOf(s, g);
        if (animate) {
          s.state = 'new';
          M.Composite.remove(world, s.body);
          queue.push({ s, at: now() + delay });
          delay += 55;
        } else lay(s);
      }
      s.home = homeOf(s, g);
      s.rank = rank;
      if (!animate) { if (s.state !== 'new') lay(s); }
      else if (s.state === 'laid' && (Math.abs(s.body.position.x - s.home.x) > 0.5 || Math.abs(s.body.position.y - s.home.y) > 0.5)) {
        s.v = { x: 0, y: 0, a: 0 };
        s.state = 'homing';
        filter(s, 'none');
      }
      stones.push(s);
    });
    wake();
    draw();
  }

  function spawn({ s }) {
    const x = s.home.x + (rand() - 0.5) * size * 0.5;
    const y = -size * (0.7 + rand() * 0.5);
    M.Composite.add(world, s.body);
    M.Body.setStatic(s.body, false);
    M.Body.setPosition(s.body, { x, y });
    M.Body.setAngle(s.body, (rand() - 0.5) * 0.9);
    M.Body.setVelocity(s.body, { x: 0, y: 2 });
    M.Body.setAngularVelocity(s.body, (rand() - 0.5) * 0.06);
    filter(s, 'solid');
    Object.assign(s, { state: 'loose', t0: now(), wait: 250, orderly: false, still: 0, falling: true });
  }

  // ------------------------------------------------------------------ the loop
  const order = { laid: 0, homing: 1, loose: 2, gone: 3 };
  function draw() {
    if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    if (bg) ctx.drawImage(bg, 0, 0, W, H);
    const list = stones.filter((s) => s.state !== 'new').sort((a, b) => order[a.state] - order[b.state]);
    for (const s of list) {
      const { x, y } = s.body.position;
      if (y > H + size * 2) continue;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(s.body.angle);
      ctx.drawImage(s.sp.c, -s.sp.cx, -s.sp.cy, s.sp.w, s.sp.h);
      ctx.restore();
    }
  }

  // a damped spring, in Matter's units (one step is a sixtieth of a second)
  const W0 = 0.24, Z = 0.82;
  function spring(s) {
    const b = s.body, v = s.v, cap = size * 0.3;
    v.x += W0 * W0 * (s.home.x - b.position.x) - 2 * Z * W0 * v.x;
    v.y += W0 * W0 * (s.home.y - b.position.y) - 2 * Z * W0 * v.y;
    v.a += W0 * W0 * (0 - b.angle) - 2 * Z * W0 * v.a;
    const sp = Math.hypot(v.x, v.y);
    if (sp > cap) { v.x *= cap / sp; v.y *= cap / sp; }
    M.Body.setPosition(b, { x: b.position.x + v.x, y: b.position.y + v.y });
    M.Body.setAngle(b, b.angle + v.a);
    const far = Math.abs(s.home.x - b.position.x) + Math.abs(s.home.y - b.position.y);
    if (far < 0.3 && Math.abs(v.x) + Math.abs(v.y) < 0.3 && Math.abs(b.angle) < 0.003 && Math.abs(v.a) < 0.003) lay(s);
  }

  let raf = 0, running = false, visible = false, held = null;
  function tick() {
    const t = now();
    while (queue.length && queue[0].at <= t) spawn(queue.shift());
    M.Engine.update(engine, 1000 / 60);
    const solids = stones.filter((s) => s.state === 'laid' || (s.state === 'loose' && !s.ghost)).map((s) => s.body);
    for (const s of stones) {
      if (s.state === 'loose') {
        // a stone knocked out of the wall overlaps its neighbours: it is solid once clear of them
        if (s.ghost && !M.Query.collides(s.body, solids.filter((b) => b !== s.body)).length) filter(s, 'solid');
        const speed = s.body.speed + Math.abs(s.body.angularVelocity) * size * 0.5;
        s.still = speed < 0.5 ? s.still + 1 : 0;
        const age = t - s.t0;
        // a stone falling in that drops past its place (the course below is not built yet) is caught there
        const past = s.falling && s.body.position.y > s.home.y + size * 0.3;
        if (s !== held && age > s.wait && (s.orderly || past || s.still > 8 || age > s.wait + 2600)) goHome(s);
      } else if (s.state === 'homing') spring(s);
    }
    for (const s of stones) if (s.state === 'gone' && s.body.position.y > H + size * 3) M.Composite.remove(world, s.body);
    stones = stones.filter((s) => !(s.state === 'gone' && s.body.position.y > H + size * 3));
    draw();
    const busy = queue.length || held || stones.some((s) => s.state !== 'laid');
    if (visible && busy) raf = requestAnimationFrame(tick);
    else running = false;
  }
  function wake() {
    if (!running && visible) { running = true; raf = requestAnimationFrame(tick); }
  }

  function resize() {
    ({ w: W, h: H, ctx } = fitCanvas(canvas));
    makeGround(); makeBg();
    if (!text) return draw();
    // a new field: the wall is set again at its new size, straight into place
    for (const s of stones) M.Composite.remove(world, s.body);
    stones = []; queue = []; size = 0;
    build(text, false);
  }

  // ------------------------------------------------------------------ start
  resize();
  new ResizeObserver(() => { if (canvas.clientWidth !== W || canvas.clientHeight !== H) resize(); }).observe(field);
  if (reduced()) { shakeBtn.disabled = true; shakeBtn.title = 'Shaking is off while your system asks for less motion'; }
  // The wall is built in front of you: it starts when the field comes into view.
  let started = false;
  watchVisible(field, (v) => {
    visible = v;
    if (v && !started) { started = true; build(input.value.trim() || PROVERB); }
    if (v) wake(); else { cancelAnimationFrame(raf); running = false; }
  }, '-15% 0px');

  // ------------------------------------------------------------------ hands
  const local = (e) => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  const hit = (p) => {
    const list = stones.filter((s) => s.state !== 'new' && s.state !== 'gone').sort((a, b) => order[b.state] - order[a.state]);
    return list.find((s) => M.Vertices.contains(s.body.vertices, p));
  };
  const knock = (s, p) => {
    const dir = p.x < s.body.position.x ? 1 : -1;
    loosen(s, dir * (1.5 + rand() * 3), -7 - rand() * 4, dir * (0.05 + rand() * 0.12), 900);
  };
  // a thump on the field shakes loose the stones near it
  const thump = (p) => {
    const R = size * 1.25;
    for (const s of stones) {
      if (s.state === 'new' || s.state === 'gone') continue;
      const dx = s.body.position.x - p.x, dy = s.body.position.y - p.y, d = Math.hypot(dx, dy);
      if (d > R) continue;
      const f = 1 - d / R;
      loosen(s, (dx / (d || 1)) * 6 * f + (rand() - 0.5), -4 - 7 * f, (rand() - 0.5) * 0.3 * f, 900 + rand() * 300);
    }
    wake();
  };
  let down = null, grab = null;
  canvas.addEventListener('pointerdown', (e) => {
    if (reduced() || !size) return;
    const p = local(e);
    down = { p, t: now(), id: e.pointerId, s: hit(p), mouse: e.pointerType === 'mouse' };
    if (down.s && down.mouse) { e.preventDefault(); canvas.setPointerCapture(e.pointerId); }
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!down || e.pointerId !== down.id) return;
    const p = local(e);
    if (!grab && down.s && down.mouse && Math.hypot(p.x - down.p.x, p.y - down.p.y) > 4) {
      // carry the stone
      held = down.s;
      loosen(held, 0, 0, 0, 700);
      const off = M.Vector.rotate(M.Vector.sub(down.p, held.body.position), -held.body.angle);
      grab = M.Constraint.create({ pointA: p, bodyB: held.body, pointB: off, stiffness: 0.12, damping: 0.08, length: 0 });
      M.Composite.add(world, grab);
      canvas.classList.add('dragging');
      wake();
    }
    if (grab) { grab.pointA = p; M.Sleeping.set(held.body, false); }
  });
  const up = (e) => {
    if (!down || e.pointerId !== down.id) return;
    const p = local(e);
    if (grab) {
      M.Composite.remove(world, grab);
      grab = null;
      held.t0 = now();
      held = null;
      canvas.classList.remove('dragging');
    } else if (e.type === 'pointerup' && Math.hypot(p.x - down.p.x, p.y - down.p.y) < 10 && now() - down.t < 500) {
      if (down.s) { knock(down.s, p); wake(); } else thump(p);
    }
    down = null;
  };
  canvas.addEventListener('pointerup', up);
  canvas.addEventListener('pointercancel', up);

  let timer = 0;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const t = input.value.replace(/\s+/g, ' ').trim();
      if (t && t !== text) { build(t); gloss.textContent = ''; }
    }, 260);
  });
  let pi = PROVERBS.findIndex(([ga]) => ga.toLowerCase().startsWith('de réir'));
  $('[data-wall-proverb]', root).addEventListener('click', () => {
    pi = (pi + 1) % PROVERBS.length;
    const [ga, en] = PROVERBS[pi];
    const t = ga.toLowerCase().replace(/[.!]+$/, '');
    input.value = t;
    gloss.textContent = `${en} `;
    build(t);
  });
  shakeBtn.addEventListener('click', () => {
    // everything comes down, then the wall builds itself again, bottom course first
    for (const s of stones) {
      if (s.state === 'new' || s.state === 'gone') continue;
      loosen(s, (rand() - 0.5) * 9, -5 - rand() * 9, (rand() - 0.5) * 0.4, 1500 + s.rank * 32, true);
    }
    wake();
  });
}
