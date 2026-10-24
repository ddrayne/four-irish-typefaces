import { $, reduced, loadFace, watchVisible, rng } from './util.js';

// Céilí's letters dance to a bodhrán. The drum is synthesised (a pitched thump for
// the skin, filtered noise for the slap), scheduled ahead on the audio clock, and the
// dancers move on the same clock so they land exactly on the beat. On strong beats
// letters with alternates change into them: insular r and s, uncial a and n, and so on.

const RHYTHMS = {
  // pulse: milliseconds per eighth note at 100% tempo; accents per eighth; where the second strong beat falls
  jig: { pulse: 178, acc: [1, .3, .5, .85, .3, .5], half: 3 },
  reel: { pulse: 140, acc: [1, .3, .6, .3, .85, .3, .6, .3], half: 4 },
  slip: { pulse: 168, acc: [1, .3, .5, .85, .3, .5, .85, .3, .5], half: 3 },
  polka: { pulse: 215, acc: [1, .35, .8, .35], half: 2 },
};

function noiseBuffer(ctx) {
  const buf = ctx.createBuffer(1, ctx.sampleRate * 0.5, ctx.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  return buf;
}

function drum(ctx, out, noise, t, acc) {
  const deep = acc > 0.7;
  // the skin: a sine that drops in pitch
  const o = ctx.createOscillator();
  const og = ctx.createGain();
  o.type = 'sine';
  o.frequency.setValueAtTime(deep ? 105 : 175, t);
  o.frequency.exponentialRampToValueAtTime(deep ? 46 : 92, t + (deep ? 0.22 : 0.1));
  og.gain.setValueAtTime(0.0001, t);
  og.gain.exponentialRampToValueAtTime(0.85 * acc, t + 0.004);
  og.gain.exponentialRampToValueAtTime(0.0001, t + (deep ? 0.5 : 0.16));
  o.connect(og).connect(out);
  o.start(t); o.stop(t + 0.55);
  // the slap of the tipper: band-passed noise
  const n = ctx.createBufferSource();
  n.buffer = noise;
  const bp = ctx.createBiquadFilter();
  bp.type = 'bandpass'; bp.frequency.value = deep ? 340 : 1400; bp.Q.value = deep ? 0.9 : 1.4;
  const ng = ctx.createGain();
  ng.gain.setValueAtTime(0.0001, t);
  ng.gain.exponentialRampToValueAtTime((deep ? 0.5 : 0.22) * acc, t + 0.002);
  ng.gain.exponentialRampToValueAtTime(0.0001, t + (deep ? 0.09 : 0.05));
  n.connect(bp).connect(ng).connect(out);
  n.start(t, Math.random() * 0.4); n.stop(t + 0.12);
}

export async function init(root, data) {
  await Promise.all([loadFace('ceili'), loadFace('ceili', 700)]);
  const floor = $('[data-dance-floor]', root);
  const line = $('[data-dance-line]', root);
  const input = $('[data-dance-text]', root);
  const play = $('[data-dance-play]', root);
  const rhythmSel = $('[data-dance-rhythm]', root);
  const tempo = $('[data-dance-tempo]', root);
  const sound = $('[data-dance-sound]', root);
  const section = root.closest('section');
  const buntingHost = $('[data-bunting]', section);

  // Which letters have alternates, and under which stylistic set.
  const alts = {};
  for (const set of data.faces.ceili.sets) for (const ch of set.chars.toLowerCase()) (alts[ch] ||= []).push(set.tag);

  let dancers = [];
  function setLine(text) {
    line.textContent = '';
    dancers = [...text].map((ch, i) => {
      const d = document.createElement('span');
      d.className = ch === ' ' ? 'dancer space' : 'dancer';
      if (ch !== ' ') {
        const g = document.createElement('span');
        g.className = 'g';
        g.style.display = 'inline-block';
        g.textContent = ch;
        const sh = document.createElement('i');
        d.append(g, sh);
      }
      line.appendChild(d);
      return { el: d, g: d.firstChild, sh: d.lastChild, ch, i, sets: alts[ch.toLowerCase()] || [], alt: 0 };
    });
    // Keep the line inside the floor.
    line.style.fontSize = '';
    const max = floor.clientWidth * 0.92;
    const w = line.scrollWidth;
    if (w > max) line.style.fontSize = `${parseFloat(getComputedStyle(line).fontSize) * (max / w)}px`;
  }
  setLine(input.value);
  input.addEventListener('input', () => setLine(input.value || ' '));

  // Bunting across the top of the hall.
  let flags = buildBunting(buntingHost);
  let lastW = buntingHost?.clientWidth;
  if (buntingHost) new ResizeObserver(() => {
    if (buntingHost.clientWidth === lastW) return;
    lastW = buntingHost.clientWidth;
    buntingHost.replaceChildren();
    flags = buildBunting(buntingHost);
  }).observe(buntingHost);

  // ------------------------------------------------------------------ moves
  const live = () => dancers.filter((d) => d.g && d.g.nodeType === 1);
  function hop(d, unit, high) {
    const tilt = (d.i % 2 ? -1 : 1) * (high ? 7 : 3);
    d.g.animate([
      { transform: 'translateY(0) scale(1,1)' },
      { transform: 'translateY(0) scale(1.07,.9)', offset: 0.12 },
      { transform: `translateY(${high ? -0.3 : -0.1}em) scale(.96,1.05) rotate(${tilt}deg)`, offset: 0.45 },
      { transform: 'translateY(0) scale(1.05,.95)', offset: 0.86 },
      { transform: 'none' },
    ], { duration: unit * (high ? 2.3 : 1.4), easing: 'ease-out' });
    d.sh.animate([{ transform: 'scaleX(1)', opacity: 1 }, { transform: 'scaleX(.55)', opacity: 0.4, offset: 0.45 }, { transform: 'scaleX(1)', opacity: 1 }],
      { duration: unit * (high ? 2.3 : 1.4), easing: 'ease-out' });
  }
  function swing(a, b, dur) {
    const ra = a.el.getBoundingClientRect(), rb = b.el.getBoundingClientRect();
    const half = (rb.left + rb.width / 2 - (ra.left + ra.width / 2)) / 2;
    const frames = (sign) => Array.from({ length: 13 }, (_, k) => {
      const th = (k / 12) * Math.PI * 2;
      const x = sign * (half - half * Math.cos(th));
      const y = -sign * half * 0.32 * Math.sin(th);
      return { transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)` };
    });
    a.el.animate(frames(1), { duration: dur, easing: 'ease-in-out' });
    b.el.animate(frames(-1), { duration: dur, easing: 'ease-in-out' });
  }
  function costume(d) {
    if (!d.sets.length) return;
    d.alt = (d.alt + 1) % (d.sets.length + 1);
    d.g.style.fontFeatureSettings = d.alt ? `"${d.sets[d.alt - 1]}" 1` : 'normal';
    d.el.classList.toggle('lit', d.alt === 1);
    d.el.classList.toggle('lit2', d.alt > 1);
  }

  function onBeat(step, bar, acc, R, unit) {
    const pos = step % R.acc.length;
    const ds = live();
    if (pos === 0 || pos === R.half) {
      const parity = pos === 0 ? 0 : 1;
      ds.forEach((d, k) => { if (k % 2 === parity) hop(d, unit, true); });
      ds.forEach((d) => { if (Math.random() < 0.5) costume(d); });
      flags.forEach((f, k) => { f.style.transform = `rotate(${(k % 2 === parity ? 1 : -1) * 9}deg)`; });
      setTimeout(() => flags.forEach((f) => { f.style.transform = ''; }), unit * 1.2);
    } else if (acc > 0.45) {
      ds.forEach((d, k) => { if ((k + pos) % 3 === 0) hop(d, unit, false); });
    }
    if (pos === 0 && bar % 2 === 1) {
      for (let k = 0; k + 1 < ds.length; k += 2) swing(ds[k], ds[k + 1], unit * R.acc.length);
    }
  }

  // ------------------------------------------------------------------ clock
  let ctx = null, out = null, noise = null, timer = 0, raf = 0, playing = false;
  let nextTime = 0, step = 0, queue = [];
  const R = () => RHYTHMS[rhythmSel.value] || RHYTHMS.jig;
  const unitMs = () => R().pulse * (100 / +tempo.value);

  function schedule() {
    const now = ctx.currentTime;
    while (nextTime < now + 0.12) {
      const r = R(), pos = step % r.acc.length, acc = r.acc[pos];
      if (sound.checked) drum(ctx, out, noise, nextTime, acc);
      queue.push({ t: nextTime, step, bar: Math.floor(step / r.acc.length), acc, r, unit: unitMs() });
      nextTime += unitMs() / 1000;
      step++;
    }
  }
  function frame() {
    const now = ctx.currentTime;
    while (queue.length && queue[0].t <= now) {
      const e = queue.shift();
      onBeat(e.step, e.bar, e.acc, e.r, e.unit);
    }
    raf = requestAnimationFrame(frame);
  }
  function start() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      ctx = new AC();
      const comp = ctx.createDynamicsCompressor();
      out = ctx.createGain(); out.gain.value = 0.8;
      out.connect(comp).connect(ctx.destination);
      noise = noiseBuffer(ctx);
    }
    ctx.resume();
    playing = true;
    play.setAttribute('aria-pressed', 'true');
    play.innerHTML = '<span lang="ga">Stad</span> · Stop';
    nextTime = ctx.currentTime + 0.08; step = 0; queue = [];
    timer = setInterval(schedule, 25);
    schedule();
    raf = requestAnimationFrame(frame);
  }
  function stop() {
    playing = false;
    clearInterval(timer); cancelAnimationFrame(raf); queue = [];
    play.setAttribute('aria-pressed', 'false');
    play.innerHTML = '<span lang="ga">Seinn</span> · Play';
    live().forEach((d) => { d.g.style.fontFeatureSettings = 'normal'; d.alt = 0; d.el.classList.remove('lit', 'lit2'); });
  }
  play.addEventListener('click', () => (playing ? stop() : start()));
  rhythmSel.addEventListener('change', () => { if (playing) { step = 0; } });
  // Leave the hall and the band stops.
  watchVisible(section, (v) => { if (!v && playing) stop(); });

  // At rest, someone is always tapping a foot.
  if (!reduced()) {
    setInterval(() => {
      if (playing || document.hidden) return;
      const ds = live();
      if (ds.length) hop(ds[(Math.random() * ds.length) | 0], 200, false);
    }, 1600);
  }
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
  return flags;
}
