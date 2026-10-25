import { $, loadFace, loadScript, fitCanvas, offscreen, rng, watchVisible, clamp } from './util.js';

// Carrick is from carraig, rock. Its letters are stones: they fall, settle and stack
// into a drystone wall. Each stone's collision shape is the convex hull of the letter
// as drawn, so a c sits differently from an l. Some stones carry lichen.

const PROVERB = 'de réir a chéile a thógtar na caisleáin';
const STONE = ['#16170F', '#25261D', '#33332A', '#1E2018', '#2C2A22'];
const LICHEN = ['#E09A17', '#D8B13A', '#C98A12', '#A8B04A'];

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

export async function init(root) {
  await Promise.all([loadFace('carrick'), window.Matter ? null : loadScript('vendor/matter.min.js')]);
  const M = window.Matter;
  const field = $('[data-wall-field]', root);
  const canvas = $('[data-wall-canvas]', root);
  const input = $('[data-wall-input]', root);
  const rand = rng(53913);

  const engine = M.Engine.create({ enableSleeping: true });
  engine.gravity.y = 1;
  engine.positionIterations = 8;
  engine.velocityIterations = 6;
  const world = engine.world;

  let W = 0, H = 0, ctx = null, size = 80, bg = null;
  let walls = [];
  const stones = [];
  const sprites = new Map();

  function sprite(ch, tone, mossy) {
    const key = `${ch}|${tone}|${mossy}|${size}`;
    if (sprites.has(key)) return sprites.get(key);
    const r = Math.min(window.devicePixelRatio || 1, 2);
    const font = `${size}px "Carrick Digital"`;
    const m = offscreen(1, 1).getContext('2d');
    m.font = font;
    const tm = m.measureText(ch);
    const padPx = Math.ceil(size * 0.08);
    const w = Math.ceil(tm.actualBoundingBoxLeft + tm.actualBoundingBoxRight) + padPx * 2;
    const h = Math.ceil(tm.actualBoundingBoxAscent + tm.actualBoundingBoxDescent) + padPx * 2;
    if (w <= padPx * 2 || h <= padPx * 2) return null;
    const ox = padPx + tm.actualBoundingBoxLeft, oy = padPx + tm.actualBoundingBoxAscent;
    // the hull, from the letter's own pixels
    const mask = offscreen(w, h).getContext('2d', { willReadFrequently: true });
    mask.font = font; mask.fillStyle = '#000'; mask.fillText(ch, ox, oy);
    const a = mask.getImageData(0, 0, w, h).data;
    const pts = [];
    for (let y = 0; y < h; y++) {
      let lo = -1, hi = -1;
      for (let x = 0; x < w; x++) if (a[(y * w + x) * 4 + 3] > 110) { if (lo < 0) lo = x; hi = x; }
      if (lo >= 0) { pts.push({ x: lo, y }, { x: hi + 1, y }, { x: lo, y: y + 1 }, { x: hi + 1, y: y + 1 }); }
    }
    if (pts.length < 6) return null;
    const poly = simplify(hull(pts), size * 0.05);
    // the drawing: soft shadow, stone tone, lichen, a highlight along the top edge
    const c = offscreen(w * r, h * r);
    const x = c.getContext('2d');
    x.scale(r, r);
    x.font = font;
    x.shadowColor = 'rgba(30, 26, 15, .35)'; x.shadowBlur = size * 0.06; x.shadowOffsetY = size * 0.035;
    x.fillStyle = tone; x.fillText(ch, ox, oy);
    x.shadowColor = 'transparent';
    x.globalCompositeOperation = 'source-atop';
    const g = x.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, 'rgba(255,255,255,.10)'); g.addColorStop(0.35, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(0,0,0,.12)');
    x.fillStyle = g; x.fillRect(0, 0, w, h);
    for (let k = 0; k < 90; k++) { // grain
      x.fillStyle = rand() < 0.5 ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.12)';
      x.fillRect(rand() * w, rand() * h, 1.2, 1.2);
    }
    if (mossy) {
      // a crust of lichen or two, in tight clusters
      for (let p = 0; p < 1 + ((rand() * 2) | 0); p++) {
        const cx = rand() * w, cy = rand() * h * 0.7;
        const col = LICHEN[(rand() * LICHEN.length) | 0];
        for (let k = 0; k < 14; k++) {
          x.fillStyle = col;
          x.globalAlpha = 0.45 + rand() * 0.4;
          x.beginPath();
          x.arc(cx + (rand() - 0.5) * size * 0.22, cy + (rand() - 0.5) * size * 0.16, size * (0.006 + rand() * 0.016), 0, Math.PI * 2);
          x.fill();
        }
      }
      x.globalAlpha = 1;
    }
    const s = { c, w, h, poly };
    sprites.set(key, s);
    return s;
  }

  function makeWalls() {
    if (walls.length) M.Composite.remove(world, walls);
    const t = 200;
    walls = [
      M.Bodies.rectangle(W / 2, H + t / 2, W * 3, t, { isStatic: true, friction: 1 }),
      M.Bodies.rectangle(-t / 2, H / 2 - H, t, H * 4, { isStatic: true }),
      M.Bodies.rectangle(W + t / 2, H / 2 - H, t, H * 4, { isStatic: true }),
    ];
    M.Composite.add(world, walls);
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

  function resize() {
    const prevW = W;
    ({ w: W, h: H, ctx } = fitCanvas(canvas));
    size = clamp(Math.round(W / 9), 46, 104);
    makeWalls(); makeBg();
    if (prevW && prevW !== W) stones.forEach((s) => M.Body.setPosition(s.body, { x: clamp(s.body.position.x * (W / prevW), 20, W - 20), y: Math.min(s.body.position.y, H - 20) }));
    draw();
  }

  function drop(ch, x, y = -size, spin = true) {
    if (!/\S/.test(ch)) return;
    const mossy = rand() < 0.22;
    const sp = sprite(ch, STONE[(rand() * STONE.length) | 0], mossy);
    if (!sp) return;
    const centre = M.Vertices.centre(sp.poly);
    const body = M.Bodies.fromVertices(x ?? (size * 0.6 + rand() * (W - size * 1.2)), y, [sp.poly], {
      friction: 0.9, frictionStatic: 1.4, restitution: 0.04, density: 0.0024, slop: 0.02,
    });
    if (!body) return;
    if (spin) M.Body.setAngle(body, (rand() - 0.5) * 0.6);
    M.Composite.add(world, body);
    stones.push({ body, sp, ox: centre.x, oy: centre.y });
    while (stones.length > 150) M.Composite.remove(world, stones.shift().body);
    wake();
  }

  function draw() {
    if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    if (bg) ctx.drawImage(bg, 0, 0, W, H);
    for (const s of stones) {
      const { x, y } = s.body.position;
      if (y > H + 200) continue;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(s.body.angle);
      ctx.drawImage(s.sp.c, -s.ox, -s.oy, s.sp.w, s.sp.h);
      ctx.restore();
    }
  }

  let raf = 0, running = false, visible = false, still = 0;
  function tick() {
    M.Engine.update(engine, 1000 / 60);
    draw();
    const moving = stones.some((s) => !s.body.isSleeping);
    still = moving ? 0 : still + 1;
    if (visible && still < 30) raf = requestAnimationFrame(tick);
    else running = false;
  }
  function wake() {
    if (!running && visible) { running = true; still = 0; raf = requestAnimationFrame(tick); }
  }
  watchVisible(field, (v) => { visible = v; if (v) wake(); else { cancelAnimationFrame(raf); running = false; } });

  resize();
  new ResizeObserver(() => { if (canvas.clientWidth !== W || canvas.clientHeight !== H) resize(); }).observe(field);

  // Open on a wall already built: the proverb, laid in courses and allowed to settle.
  {
    const pool = PROVERB.replace(/\s+/g, '') + 'carraigagusclochcarrick';
    const perRow = Math.max(5, Math.floor(W / (size * 0.72)));
    const rowsWanted = Math.max(3, Math.floor((H * 0.5) / (size * 0.9)));
    const letters = Array.from({ length: perRow * rowsWanted }, (_, i) => pool[i % pool.length]);
    letters.forEach((ch, i) => {
      const row = Math.floor(i / perRow), col = i % perRow;
      const x = (col + 0.5 + (row % 2) * 0.35) * (W / (perRow + 0.4));
      drop(ch, x, H - size * 0.6 - row * size * 0.95, false);
    });
    for (let k = 0; k < 240; k++) M.Engine.update(engine, 1000 / 60);
    draw();
  }

  // ------------------------------------------------------------------ hands
  let grab = null;
  const local = (e) => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  canvas.addEventListener('pointerdown', (e) => {
    const p = local(e);
    const hit = M.Query.point(stones.map((s) => s.body), p)[0];
    if (hit && e.pointerType === 'mouse') {
      e.preventDefault();
      canvas.setPointerCapture(e.pointerId);
      M.Sleeping.set(hit, false);
      const off = M.Vector.rotate(M.Vector.sub(p, hit.position), -hit.angle);
      grab = M.Constraint.create({ pointA: p, bodyB: hit, pointB: off, stiffness: 0.12, damping: 0.08, length: 0 });
      M.Composite.add(world, grab);
      canvas.classList.add('dragging');
      wake();
    } else if (hit) {
      M.Sleeping.set(hit, false);
      M.Body.setVelocity(hit, { x: (rand() - 0.5) * 6, y: -9 - rand() * 4 });
      M.Body.setAngularVelocity(hit, (rand() - 0.5) * 0.3);
      wake();
    } else {
      drop('carrick'[(rand() * 7) | 0], clamp(p.x, size / 2, W - size / 2));
    }
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!grab) return;
    grab.pointA = local(e);
    M.Sleeping.set(grab.bodyB, false);
    wake();
  });
  const release = () => {
    if (!grab) return;
    M.Composite.remove(world, grab);
    grab = null;
    canvas.classList.remove('dragging');
  };
  canvas.addEventListener('pointerup', release);
  canvas.addEventListener('pointercancel', release);

  input.addEventListener('input', (e) => {
    const text = e.data ?? input.value;
    for (const ch of text || '') drop(ch);
    input.value = '';
  });
  $('[data-wall-proverb]', root).addEventListener('click', () => {
    [...PROVERB].forEach((ch, i) => setTimeout(() => drop(ch, (i + 0.5) * (W / PROVERB.length)), i * 45));
  });
  $('[data-wall-shake]', root).addEventListener('click', () => {
    for (const s of stones) {
      M.Sleeping.set(s.body, false);
      M.Body.setVelocity(s.body, { x: (rand() - 0.5) * 8, y: -6 - rand() * 9 });
      M.Body.setAngularVelocity(s.body, (rand() - 0.5) * 0.4);
    }
    wake();
  });
  $('[data-wall-clear]', root).addEventListener('click', () => {
    for (const s of stones) M.Composite.remove(world, s.body);
    stones.length = 0;
    draw();
  });
}
