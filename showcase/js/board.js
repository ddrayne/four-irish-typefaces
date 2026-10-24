import { $$, FACES, fitText, loadFace } from './util.js';

// The results board: each winner's name set as wide as its row allows.
export async function init(board) {
  await Promise.all(FACES.map((k) => loadFace(k)));
  const names = $$('[data-fit]', board);
  const fit = () => fitText(names);
  fit();
  new ResizeObserver(fit).observe(board);
}
