// Lightweight canvas plotter for lab graphs: multiple series, recorded-run overlays, axes with units.
import { fmt } from '../app/ui.js';

const PALETTE = ['#fbbf24', '#7dd3fc', '#4ade80', '#f472b6', '#c084fc', '#fb923c', '#22d3ee', '#f87171'];
export const seriesColor = i => PALETTE[i % PALETTE.length];

export class Graph {
  constructor(canvas, { xLabel = 't (s)', yLabel = '' } = {}) {
    this.c = canvas; this.ctx = canvas.getContext('2d');
    this.xLabel = xLabel; this.yLabel = yLabel;
    this.series = [];     // [{label, color, pts:[[x,y]], dashed}]
    this.ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => this.draw()) : null;
    this.ro?.observe(canvas);
  }
  set(series, { xLabel, yLabel } = {}) {
    this.series = series;
    if (xLabel) this.xLabel = xLabel;
    if (yLabel != null) this.yLabel = yLabel;
    this.draw();
  }
  destroy() { this.ro?.disconnect(); }
  draw() {
    const c = this.c, dpr = window.devicePixelRatio || 1;
    const W = c.clientWidth || 400, H = c.clientHeight || 220;
    if (c.width !== Math.round(W * dpr) || c.height !== Math.round(H * dpr)) { c.width = Math.round(W * dpr); c.height = Math.round(H * dpr); }
    const g = this.ctx; g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    const css = getComputedStyle(document.documentElement);
    const txt = css.getPropertyValue('--txt').trim() || '#e2e8f0', dim = css.getPropertyValue('--dim').trim() || '#94a3b8';
    const pad = { l: 58, r: 12, t: 12, b: 36 };
    const all = this.series.flatMap(s => s.pts).filter(p => Number.isFinite(p[0]) && Number.isFinite(p[1]));
    g.font = '12px system-ui, sans-serif'; g.fillStyle = dim;
    if (!all.length) { g.fillText('—', W / 2, H / 2); return; }
    let [x0, x1] = extent(all.map(p => p[0])), [y0, y1] = extent(all.map(p => p[1]));
    if (y0 > 0 && y0 < (y1 - y0) * 0.6) y0 = 0;
    if (y1 < 0 && -y1 < (y1 - y0) * 0.6) y1 = 0;
    if (x1 === x0) x1 = x0 + 1;
    if (y1 === y0) { y0 -= 1; y1 += 1; }
    const yr = y1 - y0; y0 -= yr * 0.05; y1 += yr * 0.05;
    const X = x => pad.l + (x - x0) / (x1 - x0) * (W - pad.l - pad.r);
    const Y = y => H - pad.b - (y - y0) / (y1 - y0) * (H - pad.t - pad.b);
    // grid + ticks
    g.strokeStyle = 'rgba(148,163,184,0.18)'; g.lineWidth = 1;
    g.textAlign = 'right'; g.textBaseline = 'middle';
    for (const v of ticks(y0, y1, 5)) { g.beginPath(); g.moveTo(pad.l, Y(v)); g.lineTo(W - pad.r, Y(v)); g.stroke(); g.fillText(fmt(v, 3), pad.l - 6, Y(v)); }
    g.textAlign = 'center'; g.textBaseline = 'top';
    for (const v of ticks(x0, x1, 6)) { g.beginPath(); g.moveTo(X(v), pad.t); g.lineTo(X(v), H - pad.b); g.stroke(); g.fillText(fmt(v, 3), X(v), H - pad.b + 4); }
    if (y0 < 0 && y1 > 0) { g.strokeStyle = 'rgba(226,232,240,0.5)'; g.beginPath(); g.moveTo(pad.l, Y(0)); g.lineTo(W - pad.r, Y(0)); g.stroke(); }
    g.fillStyle = txt; g.fillText(this.xLabel, (pad.l + W - pad.r) / 2, H - 16);
    g.save(); g.translate(12, (pad.t + H - pad.b) / 2); g.rotate(-Math.PI / 2); g.textBaseline = 'middle'; g.fillText(this.yLabel, 0, 0); g.restore();
    // series
    let ly = pad.t + 4;
    for (const s of this.series) {
      g.strokeStyle = s.color; g.lineWidth = s.dashed ? 1.5 : 2.2; g.setLineDash(s.dashed ? [5, 4] : []);
      g.beginPath();
      s.pts.forEach((p, i) => (i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1]))));
      g.stroke(); g.setLineDash([]);
      if (s.points) { g.fillStyle = s.color; for (const p of s.pts) { g.beginPath(); g.arc(X(p[0]), Y(p[1]), 3.5, 0, 7); g.fill(); } }
      if (s.label) { g.fillStyle = s.color; g.textAlign = 'left'; g.textBaseline = 'top'; g.fillText('■ ' + s.label, pad.l + 8, ly); ly += 15; }
    }
  }
}

function extent(a) { let lo = Infinity, hi = -Infinity; for (const v of a) { if (v < lo) lo = v; if (v > hi) hi = v; } return [lo, hi]; }
function ticks(a, b, n) {
  const span = b - a, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0)), r = step0 / mag;
  const step = (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag;
  const out = []; for (let v = Math.ceil(a / step) * step; v <= b + 1e-9 * span; v += step) out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  return out;
}
