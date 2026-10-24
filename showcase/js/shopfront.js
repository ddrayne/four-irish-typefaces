import { $, FACES, FAMILY, fitCanvas, rng, loadFace, clamp } from './util.js';

// A painted Irish shopfront: a fascia board between two consoles, the name in gilded
// letters with a cast shadow, the trade beneath in smaller letters, and the shop
// window below. Tuam Uncial went up over real shops; here any of the four can.

const PAINTS = [
  { id: 'green', name: 'Bottle green', board: '#0E3B2B', trim: '#E9D9A6', wall: '#C9C2B0' },
  { id: 'oxblood', name: 'Oxblood', board: '#5A1414', trim: '#E9D9A6', wall: '#D9CDB6' },
  { id: 'navy', name: 'Navy', board: '#14233F', trim: '#E6E1D1', wall: '#BFC4C4' },
  { id: 'black', name: 'Black', board: '#121212', trim: '#D7C28A', wall: '#CFC8BC' },
  { id: 'cream', name: 'Cream', board: '#EFE6CF', trim: '#0E3B2B', wall: '#6E7B72', ink: '#0E3B2B' },
];

export async function init(root) {
  await Promise.all(FACES.map((k) => loadFace(k)));
  const canvas = $('[data-shop-canvas]', root);
  const nameIn = $('[data-shop-name]', root);
  const tradeIn = $('[data-shop-trade]', root);
  const facesHost = $('[data-shop-faces]', root);
  const paintHost = $('[data-shop-paints]', root);
  let face = 'tuam', paint = PAINTS[0];

  FACES.forEach((k) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'tog t-face'; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(k === face));
    b.innerHTML = `<span class="f-${k}">${FAMILY[k]}</span>`;
    b.addEventListener('click', () => { face = k; [...facesHost.children].forEach((c) => c.setAttribute('aria-checked', String(c === b))); draw(); });
    facesHost.appendChild(b);
  });
  PAINTS.forEach((p) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'swatch'; b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(p === paint)); b.setAttribute('aria-label', p.name); b.title = p.name;
    b.innerHTML = `<span style="background:${p.board}"></span><span style="background:${p.trim}"></span>`;
    b.addEventListener('click', () => { paint = p; [...paintHost.children].forEach((c) => c.setAttribute('aria-checked', String(c === b))); draw(); });
    paintHost.appendChild(b);
  });

  function fitFont(ctx, text, fam, maxW, maxH) {
    let size = maxH;
    ctx.font = `${size}px "${fam}"`;
    const w = ctx.measureText(text).width;
    if (w > maxW) size *= maxW / w;
    return Math.floor(size);
  }

  // Letters in gold leaf: a cast shadow, a dark outline, then a gradient with a bright band.
  function gild(ctx, text, x, y, size, fam, light) {
    ctx.save();
    ctx.font = `${size}px "${fam}"`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'alphabetic';
    const d = Math.max(2, size * 0.045);
    ctx.fillStyle = light ? 'rgba(14,59,43,.35)' : 'rgba(0,0,0,.55)';
    for (let k = d; k > 0; k -= 0.75) ctx.fillText(text, x + k, y + k);
    ctx.lineJoin = 'round';
    ctx.lineWidth = Math.max(1.5, size * 0.03);
    ctx.strokeStyle = light ? '#0E3B2B' : '#3A2508';
    ctx.strokeText(text, x, y);
    const g = ctx.createLinearGradient(0, y - size * 0.8, 0, y + size * 0.1);
    g.addColorStop(0, '#FFF3C4'); g.addColorStop(0.32, '#E9BE58'); g.addColorStop(0.5, '#FFE9A3');
    g.addColorStop(0.55, '#B9862C'); g.addColorStop(1, '#F2CF73');
    ctx.fillStyle = g;
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  function draw() {
    const W = canvas.clientWidth;
    const H = Math.round(clamp(W * 0.62, 300, 640));
    const { ctx } = fitCanvas(canvas, H);
    canvas.style.height = `${H}px`;
    const rand = rng(7);
    const name = (nameIn.value.trim() || 'Ó Briain').slice(0, 32);
    const trade = (tradeIn.value.trim() || 'Grósaeir agus Ceannaí Tae').slice(0, 48);
    const fam = FAMILY[face];
    const light = !!paint.ink;

    // the wall: rough render with a little weather
    ctx.fillStyle = paint.wall; ctx.fillRect(0, 0, W, H);
    for (let k = 0; k < (W * H) / 70; k++) {
      ctx.fillStyle = rand() < 0.5 ? 'rgba(255,255,255,.08)' : 'rgba(0,0,0,.07)';
      ctx.fillRect(rand() * W, rand() * H, 1.5, 1.5);
    }
    const m = W * 0.06, pil = clamp(W * 0.055, 22, 60);
    const top = H * 0.08, fasciaH = H * 0.3, cornice = H * 0.035;
    const fx0 = m + pil, fx1 = W - m - pil;

    // cornice over the fascia
    ctx.fillStyle = paint.board;
    ctx.fillRect(m - 8, top - cornice, W - 2 * m + 16, cornice);
    ctx.fillStyle = 'rgba(255,255,255,.18)'; ctx.fillRect(m - 8, top - cornice, W - 2 * m + 16, 2);
    ctx.fillStyle = 'rgba(0,0,0,.25)'; ctx.fillRect(m - 8, top - 2, W - 2 * m + 16, 2);

    // the fascia board, with a moulded trim
    ctx.fillStyle = paint.board; ctx.fillRect(fx0, top, fx1 - fx0, fasciaH);
    ctx.strokeStyle = paint.trim; ctx.lineWidth = 2;
    ctx.strokeRect(fx0 + 7, top + 7, fx1 - fx0 - 14, fasciaH - 14);
    ctx.globalAlpha = 0.5; ctx.strokeRect(fx0 + 12, top + 12, fx1 - fx0 - 24, fasciaH - 24); ctx.globalAlpha = 1;

    // consoles at each end, and pilasters down to the ground
    for (const x of [m, W - m - pil]) {
      ctx.fillStyle = paint.board; ctx.fillRect(x, top - cornice * 0.2, pil, H - top);
      ctx.fillStyle = 'rgba(255,255,255,.12)'; ctx.fillRect(x + 3, top + fasciaH, 3, H - top - fasciaH);
      ctx.fillStyle = 'rgba(0,0,0,.2)'; ctx.fillRect(x + pil - 5, top + fasciaH, 3, H - top - fasciaH);
      ctx.strokeStyle = paint.trim; ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x + pil * 0.2, top + fasciaH * 0.12);
      ctx.bezierCurveTo(x + pil * 0.95, top + fasciaH * 0.2, x + pil * 0.95, top + fasciaH * 0.75, x + pil * 0.5, top + fasciaH * 0.85);
      ctx.bezierCurveTo(x + pil * 0.25, top + fasciaH * 0.9, x + pil * 0.2, top + fasciaH * 0.7, x + pil * 0.45, top + fasciaH * 0.65);
      ctx.stroke();
    }

    // the name, gilded, as large as the board allows; the trade below the board
    const size = fitFont(ctx, name, fam, (fx1 - fx0) * 0.86, fasciaH * 0.62);
    gild(ctx, name, (fx0 + fx1) / 2, top + fasciaH * 0.5 + size * 0.34, size, fam, light);

    // the window: frame, glazing bars, a stall riser and a door
    const wy = top + fasciaH + H * 0.04, wh = H - wy - H * 0.12;
    const doorW = (fx1 - fx0) * 0.2;
    const winX1 = fx1 - doorW - 10;
    // a moulding between the board and the window
    ctx.fillStyle = paint.board; ctx.fillRect(fx0, top + fasciaH, fx1 - fx0, H - top - fasciaH);
    ctx.fillStyle = 'rgba(0,0,0,.28)'; ctx.fillRect(fx0, top + fasciaH, fx1 - fx0, 3);
    ctx.fillStyle = paint.trim; ctx.globalAlpha = 0.55; ctx.fillRect(fx0 + 4, wy - 7, fx1 - fx0 - 8, 1.5); ctx.globalAlpha = 1;
    const glass = ctx.createLinearGradient(0, wy, 0, wy + wh);
    glass.addColorStop(0, '#2E3A3A'); glass.addColorStop(1, '#111818');
    ctx.fillStyle = glass;
    ctx.fillRect(fx0 + 10, wy + 10, winX1 - fx0 - 20, wh - 20);
    ctx.fillRect(winX1 + 10, wy + 10, fx1 - winX1 - 20, H - wy - 10);
    // reflections
    ctx.fillStyle = 'rgba(255,255,255,.06)';
    ctx.beginPath(); ctx.moveTo(fx0 + 10, wy + wh * 0.7); ctx.lineTo(fx0 + (winX1 - fx0) * 0.35, wy + 10); ctx.lineTo(fx0 + (winX1 - fx0) * 0.5, wy + 10); ctx.lineTo(fx0 + 10, wy + wh); ctx.closePath(); ctx.fill();
    // glazing bars
    ctx.fillStyle = paint.board;
    const panes = Math.max(2, Math.round((winX1 - fx0) / 150));
    for (let i = 1; i < panes; i++) ctx.fillRect(fx0 + ((winX1 - fx0) * i) / panes - 3, wy + 10, 6, wh - 20);
    // the trade, gilded on the glass as a signwriter would
    const tw = (winX1 - fx0) * 0.84, cx = (fx0 + winX1) / 2;
    let tsize = fitFont(ctx, trade, fam, tw, wh * 0.16);
    const words = trade.split(' ');
    if (tsize < wh * 0.1 && words.length > 1) {
      // too small on one line: break at the space nearest the middle
      let best = 1, diff = Infinity;
      for (let i = 1; i < words.length; i++) {
        const d = Math.abs(words.slice(0, i).join(' ').length - words.slice(i).join(' ').length);
        if (d < diff) { diff = d; best = i; }
      }
      const lines = [words.slice(0, best).join(' '), words.slice(best).join(' ')];
      tsize = Math.min(...lines.map((l) => fitFont(ctx, l, fam, tw, wh * 0.15)));
      lines.forEach((l, i) => gild(ctx, l, cx, wy + wh * 0.26 + i * tsize * 1.15, tsize, fam, false));
    } else {
      gild(ctx, trade, cx, wy + wh * 0.32, tsize, fam, false);
    }
    // door panels and knob
    ctx.strokeStyle = paint.trim; ctx.lineWidth = 1.5; ctx.globalAlpha = 0.6;
    ctx.strokeRect(winX1 + 18, wy + (H - wy) * 0.55, fx1 - winX1 - 36, (H - wy) * 0.38);
    ctx.globalAlpha = 1;
    ctx.fillStyle = paint.trim; ctx.beginPath(); ctx.arc(winX1 + 20, wy + (H - wy) * 0.5, 3.5, 0, Math.PI * 2); ctx.fill();
    // the stall riser under the window
    ctx.fillStyle = 'rgba(0,0,0,.18)'; ctx.fillRect(fx0, wy + wh, winX1 - fx0, H - wy - wh);
    ctx.strokeStyle = paint.trim; ctx.globalAlpha = 0.5;
    ctx.strokeRect(fx0 + 14, wy + wh + 8, winX1 - fx0 - 28, H - wy - wh - 16);
    ctx.globalAlpha = 1;
    // pavement
    ctx.fillStyle = '#8E8B82'; ctx.fillRect(0, H - 8, W, 8);
    canvas.setAttribute('aria-label', `A painted shopfront reading ${name}, ${trade}, in ${fam}.`);
  }

  let t = 0;
  const later = () => { clearTimeout(t); t = setTimeout(draw, 120); };
  nameIn.addEventListener('input', later);
  tradeIn.addEventListener('input', later);
  let lastW = 0;
  new ResizeObserver(() => { if (canvas.clientWidth !== lastW) { lastW = canvas.clientWidth; draw(); } }).observe(canvas.parentElement);
  draw();
}
