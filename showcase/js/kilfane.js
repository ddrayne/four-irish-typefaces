import { $, loadFace, fitCanvas, offscreen, rng, clamp } from './util.js';

// Dry transfer, the way Kilfane was sold: a translucent carrier sheet of letters
// (S53909) lying on a cutting mat. Rubbing over the sheet moves ink from the sheet to
// the mat, a speckle at a time, so a quick rub leaves the cracked, part-transferred
// letter every designer of the 1970s knew. The sheet keeps a grey ghost where its
// letters have gone. Drag the sheet by its top band.

const ROWS = [
  'AAABBCCDDEEEFFGGHHIIJKLLMMNNOOPPQRRSSTTUUVWXYZ',
  'aaaabbccddeeeeffgghhiiijkllmmnnnoooopprrssstttuuvwxyz',
  'aeeiinnorst1234567890&?!£$(;:).,’-',
  '´´´´´´´´˙˙˙˙˙¨¨ˆˆ˜ˇ˚',
];

export async function init(root, data) {
  await Promise.all([loadFace('kilfane'), document.fonts.load('600 12px "Fragment Mono"').catch(() => [])]);
  const mat = $('[data-rub-mat]', root);
  const canvas = $('[data-rub-canvas]', root);
  const liftBtn = $('[data-rub-lift]', root);
  const have = new Set(data.faces.kilfane.cps);
  const rows = ROWS.map((r) => [...r].filter((ch) => have.has(ch.codePointAt(0))).join('')).filter(Boolean);
  const rand = rng(53909);

  let W = 0, H = 0, R = 1, ctx = null;
  let F = 40;                         // sheet letter size, CSS px
  let matBg, transfer, sheetBase, sheetInk, noise, tmp, chunk;
  let items = [];
  const S = { x: 0, y: 0, w: 0, h: 0, band: 0, shown: true, tx: 0, ty: 0 };
  const dev = (v) => Math.round(v * R);

  // ---------------------------------------------------------------- the mat
  function drawMat() {
    matBg = offscreen(dev(W), dev(H));
    const x = matBg.getContext('2d');
    x.scale(R, R);
    x.fillStyle = '#1C5743'; x.fillRect(0, 0, W, H);
    const nr = rng(3);
    for (let k = 0; k < (W * H) / 60; k++) { x.fillStyle = nr() < 0.5 ? 'rgba(255,255,255,.035)' : 'rgba(0,0,0,.06)'; x.fillRect(nr() * W, nr() * H, 1.3, 1.3); }
    const cell = clamp(Math.round(W / 64), 10, 18);
    const ox = 34, oy = 30;
    for (let gx = ox, i = 0; gx < W; gx += cell, i++) {
      x.strokeStyle = i % 5 === 0 ? 'rgba(160,210,180,.42)' : 'rgba(160,210,180,.16)';
      x.lineWidth = i % 5 === 0 ? 1 : 0.7;
      x.beginPath(); x.moveTo(gx + 0.5, oy); x.lineTo(gx + 0.5, H); x.stroke();
      if (i % 5 === 0) { x.fillStyle = 'rgba(227,239,231,.85)'; x.font = '600 10px "Fragment Mono", monospace'; x.textAlign = 'center'; x.fillText(String(i / 5), gx, oy - 9); }
      x.strokeStyle = 'rgba(227,239,231,.7)'; x.lineWidth = 1;
      x.beginPath(); x.moveTo(gx + 0.5, oy - (i % 5 === 0 ? 6 : 3)); x.lineTo(gx + 0.5, oy); x.stroke();
    }
    for (let gy = oy, i = 0; gy < H; gy += cell, i++) {
      x.strokeStyle = i % 5 === 0 ? 'rgba(160,210,180,.42)' : 'rgba(160,210,180,.16)';
      x.lineWidth = i % 5 === 0 ? 1 : 0.7;
      x.beginPath(); x.moveTo(ox, gy + 0.5); x.lineTo(W, gy + 0.5); x.stroke();
      if (i % 5 === 0 && i) { x.fillStyle = 'rgba(227,239,231,.85)'; x.font = '600 10px "Fragment Mono", monospace'; x.textAlign = 'right'; x.fillText(String(i / 5), ox - 8, gy + 3.5); }
      x.strokeStyle = 'rgba(227,239,231,.7)'; x.lineWidth = 1;
      x.beginPath(); x.moveTo(ox - (i % 5 === 0 ? 6 : 3), gy + 0.5); x.lineTo(ox, gy + 0.5); x.stroke();
    }
    // angle guides from the lower left corner
    x.strokeStyle = 'rgba(227,239,231,.22)'; x.lineWidth = 1;
    for (const deg of [30, 45, 60]) {
      const a = (deg * Math.PI) / 180;
      x.beginPath(); x.moveTo(ox, H); x.lineTo(ox + Math.cos(a) * W * 1.5, H - Math.sin(a) * W * 1.5); x.stroke();
    }
    x.fillStyle = 'rgba(227,239,231,.5)'; x.font = '600 10px "Fragment Mono", monospace'; x.textAlign = 'left';
    x.fillText('cm', 8, oy - 9);
  }

  // ---------------------------------------------------------------- the sheet
  function layout() {
    for (F = clamp(Math.round(W / 17), 26, 50); F >= 20; F -= 2) {
      const m = F * 0.5, gap = F * 0.16, lh = F * 1.32;
      S.w = Math.min(W - 24, Math.max(320, W * 0.86), 860);
      S.band = Math.round(F * 1.05 + 14);
      const meas = offscreen(1, 1).getContext('2d');
      meas.font = `${F}px "Kilfane"`;
      items = [];
      let x = m, base = S.band + m + F * 0.95;
      for (const row of rows) {
        for (const ch of row) {
          const w = meas.measureText(ch).width;
          if (x + w > S.w - m) { x = m; base += lh; }
          items.push({ ch, x, base, w });
          x += w + gap;
        }
        x = m; base += lh;
      }
      S.h = Math.round(base - lh + F * 0.55 + m);
      if (S.h <= H * 0.66) break;
    }
  }

  function drawSheet() {
    const sw = dev(S.w), sh = dev(S.h);
    sheetBase = offscreen(sw, sh);
    sheetInk = offscreen(sw, sh);
    const b = sheetBase.getContext('2d');
    b.scale(R, R);
    // the carrier film: translucent, so the mat shows through
    b.fillStyle = 'rgba(248,247,238,.52)';
    b.beginPath(); b.roundRect(0, 0, S.w, S.h, 4); b.fill();
    b.strokeStyle = 'rgba(255,255,255,.7)'; b.lineWidth = 1; b.stroke();
    // the top band, where you hold it
    b.fillStyle = 'rgba(246,245,236,.96)';
    b.beginPath(); b.roundRect(0, 0, S.w, S.band, [4, 4, 0, 0]); b.fill();
    b.fillStyle = '#121210';
    b.font = `600 ${Math.round(S.band * 0.34)}px "Fragment Mono", monospace`;
    b.textBaseline = 'middle'; b.textAlign = 'left';
    b.fillText('S53909', 12, S.band / 2);
    const codeW = b.measureText('S53909').width;
    b.font = `400 ${Math.round(S.band * 0.22)}px "Fragment Mono", monospace`;
    b.fillStyle = '#3a3a34';
    if (S.w > 420) b.fillText('KILFANE · 30 PT · 7.5 MM · DRY TRANSFER', 24 + codeW, S.band / 2);
    b.textAlign = 'right';
    b.fillText('⋮⋮ DRAG', S.w - 12, S.band / 2);
    b.fillStyle = 'rgba(18,18,16,.8)'; b.fillRect(0, S.band - 1.5, S.w, 1.5);
    // fine print
    b.textAlign = 'right'; b.textBaseline = 'alphabetic';
    b.font = `400 9px "Fragment Mono", monospace`;
    b.fillStyle = 'rgba(18,18,16,.55)';
    b.fillText('Burnish firmly over the letter, then lift the sheet slowly. Store flat.', S.w - 10, S.h - 8);
    // ghosts of the letters (they show where ink has gone)
    b.textAlign = 'left';
    b.font = `${F}px "Kilfane"`;
    b.fillStyle = 'rgba(120,122,110,.30)';
    for (const it of items) b.fillText(it.ch, it.x, it.base);
    freshInk();
  }

  function freshInk() {
    const k = sheetInk.getContext('2d');
    k.setTransform(1, 0, 0, 1, 0, 0);
    k.globalCompositeOperation = 'source-over';
    k.clearRect(0, 0, sheetInk.width, sheetInk.height);
    k.scale(R, R);
    k.font = `${F}px "Kilfane"`;
    k.fillStyle = '#0E0E0C';
    for (const it of items) k.fillText(it.ch, it.x, it.base);
  }

  function makeNoise() {
    noise = offscreen(256, 256);
    const x = noise.getContext('2d');
    const img = x.createImageData(256, 256);
    for (let i = 0; i < img.data.length; i += 4) img.data[i + 3] = rand() < 0.42 ? 255 : 0;
    x.putImageData(img, 0, 0);
  }

  // ---------------------------------------------------------------- rubbing
  const brushR = () => F * 0.17;
  function stamp(lx, ly) {
    const r = brushR(), d = Math.ceil(r * 2 * R) + 2;
    if (!tmp || tmp.width !== d) { tmp = offscreen(d, d); chunk = offscreen(d, d); }
    const t = tmp.getContext('2d'), c = chunk.getContext('2d');
    const sx = Math.round((lx - r) * R), sy = Math.round((ly - r) * R);
    // a speckled disc: where this pass of the burnisher actually bites
    t.globalCompositeOperation = 'source-over';
    t.clearRect(0, 0, d, d);
    t.fillStyle = '#000';
    t.beginPath(); t.arc(d / 2, d / 2, r * R * (0.8 + rand() * 0.2), 0, Math.PI * 2); t.fill();
    t.globalCompositeOperation = 'destination-in';
    t.drawImage(noise, -Math.floor(rand() * (256 - d)), -Math.floor(rand() * (256 - d)));
    // the ink under it
    c.globalCompositeOperation = 'source-over';
    c.clearRect(0, 0, d, d);
    c.drawImage(sheetInk, -sx, -sy);
    c.globalCompositeOperation = 'destination-in';
    c.drawImage(tmp, 0, 0);
    // onto the mat, off the sheet
    transfer.getContext('2d').drawImage(chunk, dev(S.x) + sx, dev(S.y) + sy);
    const k = sheetInk.getContext('2d');
    k.save(); k.setTransform(1, 0, 0, 1, 0, 0);
    k.globalCompositeOperation = 'destination-out';
    k.drawImage(tmp, sx, sy);
    k.restore();
  }
  function rubLine(a, b) {
    const step = brushR() * 0.45;
    const n = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / step));
    for (let i = 1; i <= n; i++) stamp(a.x + ((b.x - a.x) * i) / n, a.y + ((b.y - a.y) * i) / n);
  }

  // A word already rubbed down, one letter not quite finished.
  function seedWord() {
    const x = transfer.getContext('2d');
    x.save(); x.scale(R, R);
    x.font = `${Math.round(F * 1.5)}px "Kilfane"`;
    x.fillStyle = '#0E0E0C';
    const word = 'Fáilte';
    const tx = 46, ty = H - Math.round(F * 0.9);
    x.fillText(word, tx, ty);
    // the last letter was rubbed in a hurry
    const ew = x.measureText('e').width, ex = tx + x.measureText('Fáilt').width;
    x.globalCompositeOperation = 'destination-out';
    for (let k = 0; k < 70; k++) {
      x.globalAlpha = 0.9;
      x.fillRect(ex + rand() * ew, ty - F * 1.05 + rand() * F * 1.1, 1 + rand() * 2.2, 1 + rand() * 1.4);
    }
    x.restore();
  }

  // ---------------------------------------------------------------- frame
  let dirty = true, cursor = null, slide = 0;
  function render() {
    dirty = false;
    ctx.clearRect(0, 0, W, H);
    ctx.drawImage(matBg, 0, 0, W, H);
    ctx.drawImage(transfer, 0, 0, W, H);
    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,.32)'; ctx.shadowBlur = 18; ctx.shadowOffsetY = 8;
    ctx.fillStyle = 'rgba(248,247,238,.01)';
    ctx.fillRect(S.x + 2, S.y + 2, S.w - 4, S.h - 4);
    ctx.restore();
    ctx.drawImage(sheetBase, S.x, S.y, S.w, S.h);
    ctx.drawImage(sheetInk, S.x, S.y, S.w, S.h);
    if (cursor) {
      ctx.strokeStyle = 'rgba(255,106,31,.9)'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(cursor.x, cursor.y, brushR(), 0, Math.PI * 2); ctx.stroke();
    }
  }
  function frame() {
    if (slide) {
      S.x += (S.tx - S.x) * 0.18; S.y += (S.ty - S.y) * 0.18;
      if (Math.abs(S.tx - S.x) + Math.abs(S.ty - S.y) < 0.5) { S.x = S.tx; S.y = S.ty; slide = 0; }
      dirty = true;
    }
    if (dirty) render();
    requestAnimationFrame(frame);
  }

  function setup() {
    const old = transfer;
    ({ w: W, h: H, r: R, ctx } = fitCanvas(canvas));
    layout();
    drawMat();
    transfer = offscreen(dev(W), dev(H));
    if (old) transfer.getContext('2d').drawImage(old, 0, 0, transfer.width, transfer.height);
    drawSheet();
    S.x = S.tx = Math.round((W - S.w) / 2);
    S.y = S.ty = 44;
    S.shown = true; liftBtn.textContent = 'Lift the sheet';
    if (!old) seedWord();
    dirty = true;
  }
  makeNoise();
  setup();
  requestAnimationFrame(frame);
  let lastW = W;
  new ResizeObserver(() => { if (canvas.clientWidth !== lastW) { lastW = canvas.clientWidth; setup(); } }).observe(mat);

  // ---------------------------------------------------------------- hands
  let mode = null, last = null;
  const local = (e) => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  const onSheet = (p) => S.shown && p.x >= S.x && p.x <= S.x + S.w && p.y >= S.y && p.y <= S.y + S.h;
  canvas.addEventListener('pointerdown', (e) => {
    const p = local(e);
    if (!onSheet(p)) return;
    canvas.setPointerCapture(e.pointerId);
    e.preventDefault();
    if (p.y - S.y <= S.band) { mode = 'drag'; canvas.style.cursor = 'grabbing'; }
    else { mode = 'rub'; stamp(p.x - S.x, p.y - S.y); dirty = true; }
    last = p;
  });
  canvas.addEventListener('pointermove', (e) => {
    const p = local(e);
    const over = onSheet(p) && p.y - S.y > S.band;
    canvas.style.cursor = mode === 'drag' ? 'grabbing' : onSheet(p) && !over ? 'grab' : over ? 'none' : 'default';
    cursor = (over || mode === 'rub') && e.pointerType === 'mouse' ? p : null;
    if (mode === 'drag') {
      S.x = S.tx = clamp(S.x + p.x - last.x, -S.w + 60, W - 60);
      S.y = S.ty = clamp(S.y + p.y - last.y, -S.h + S.band + 10, H - S.band);
    } else if (mode === 'rub') {
      rubLine({ x: last.x - S.x, y: last.y - S.y }, { x: p.x - S.x, y: p.y - S.y });
    }
    last = p;
    dirty = true;
  });
  const end = () => { mode = null; canvas.style.cursor = ''; dirty = true; };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('pointerleave', () => { cursor = null; dirty = true; });

  liftBtn.addEventListener('click', () => {
    S.shown = !S.shown;
    S.ty = S.shown ? 44 : -S.h - 30;
    S.tx = S.shown ? Math.round((W - S.w) / 2) : S.x;
    if (!S.shown) S.shown = false;
    slide = 1;
    liftBtn.textContent = S.shown ? 'Lift the sheet' : 'Put the sheet back';
  });
  $('[data-rub-fresh]', root).addEventListener('click', () => { freshInk(); dirty = true; });
  $('[data-rub-clear]', root).addEventListener('click', () => { transfer.getContext('2d').clearRect(0, 0, transfer.width, transfer.height); dirty = true; });
}
