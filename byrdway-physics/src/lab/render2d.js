// 2D canvas renderer: used when WebGL is unavailable or in low-graphics mode. It draws the same model state
// as the 3D renderer from the side (x right, y up) or from the top (x right, z down) when lab.view2d.plane = 'xz'.
export class Renderer2D {
  constructor(host, lab) {
    this.host = host; this.lab = lab;
    this.c = document.createElement('canvas'); this.c.className = 'lab2d'; this.c.setAttribute('aria-hidden', 'true');
    host.append(this.c); this.g = this.c.getContext('2d');
    this.trails = new Map(); this.decor = []; this.showVectors = true; this.showTrails = true; this.effectsOn = false;
    this.plane = lab.view2d?.plane || 'xy';
    this.ro = new ResizeObserver(() => this.fit()); this.ro.observe(host); this.fit();
  }
  fit() {
    const dpr = window.devicePixelRatio || 1, W = this.host.clientWidth || 600, H = this.host.clientHeight || 360;
    this.c.width = W * dpr; this.c.height = H * dpr; this.c.style.width = W + 'px'; this.c.style.height = H + 'px';
    this.g.setTransform(dpr, 0, 0, dpr, 0, 0); this.W = W; this.H = H;
    const v = this.lab.view2d || {}, cam = this.lab.camera || {};
    const span = v.span || (cam.dist || 12) * (this.lab.scale || 1) * 0.9;
    const cx = v.cx ?? (cam.target?.[0] || 0), cy = v.cy ?? (this.plane === 'xz' ? -(cam.target?.[2] || 0) : (cam.target?.[1] || 0));
    this.k = Math.min(W, H * 1.6) / span; this.cx = cx; this.cy = cy;
  }
  P(p) { const y = this.plane === 'xz' ? -(p[2] || 0) : p[1]; return [this.W / 2 + (p[0] - this.cx) * this.k, this.H / 2 - (y - this.cy) * this.k]; }
  buildDecor(items = []) { this.decor = items; }
  setCamera() {}
  clearTrails() { this.trails.clear(); }
  clearEffects() {}
  resetDynamic() { this.trails.clear(); }
  get effectVisible() { return false; }
  update(desc) {
    const g = this.g; g.clearRect(0, 0, this.W, this.H);
    g.fillStyle = this.lab.space ? '#02040b' : '#0b1220'; g.fillRect(0, 0, this.W, this.H);
    for (const d of this.decor) this.drawDecor(d);
    if (this.showTrails) for (const [, tr] of this.trails) { g.strokeStyle = tr.color; g.lineWidth = 1.5; g.beginPath(); tr.pts.forEach((p, i) => (i ? g.lineTo(...this.P(p)) : g.moveTo(...this.P(p)))); g.stroke(); }
    for (const ln of desc.lines || []) { g.strokeStyle = ln.color || '#7dd3fc'; g.globalAlpha = ln.opacity ?? 1; g.lineWidth = 1.6; g.beginPath(); ln.pts.forEach((p, i) => (i ? g.lineTo(...this.P(p)) : g.moveTo(...this.P(p)))); g.stroke(); g.globalAlpha = 1; }
    for (const b of desc.bodies || []) {
      if (b.visible === false) continue;
      if (b.trail) { let tr = this.trails.get(b.id); if (!tr) this.trails.set(b.id, tr = { pts: [], color: b.trailColor || b.color || '#7dd3fc' }); const l = tr.pts.at(-1); if (!l || Math.hypot(l[0] - b.pos[0], l[1] - b.pos[1], (l[2] || 0) - (b.pos[2] || 0)) * this.k > 2) tr.pts.push([...b.pos]); }
      this.drawBody(b);
    }
    if (this.showVectors) for (const v of desc.vectors || []) this.arrow(v.from, [v.from[0] + v.vec[0], v.from[1] + v.vec[1], (v.from[2] || 0) + (v.vec[2] || 0)], v.color, v.label);
  }
  drawBody(b) {
    const g = this.g, [x, y] = this.P(b.pos), S = this.k;
    g.fillStyle = b.emissive && b.shape === 'sphere' ? b.emissive : (b.color || '#7dd3fc'); g.globalAlpha = b.opacity ?? 1;
    const sz = b.size || [1, 1, 1];
    if (b.shape === 'sphere' || b.shape === 'cylinder' && this.plane === 'xz') { g.beginPath(); g.arc(x, y, Math.max(2, (b.r || sz[0] / 2) * S), 0, 7); g.fill(); }
    else if (b.shape === 'torus') { g.strokeStyle = b.color; g.lineWidth = 2; g.beginPath(); g.arc(x, y, (b.r || 1) * S, 0, 7); g.stroke(); }
    else {
      const w = (b.shape === 'cylinder' ? (b.r || sz[0] / 2) * 2 : sz[0]) * S, hh = (b.shape === 'cylinder' ? (b.h || sz[1]) : (this.plane === 'xz' ? (sz[2] ?? sz[0]) : sz[1])) * S;
      g.save(); g.translate(x, y); g.rotate(-(b.rot?.[2] || 0)); g.fillRect(-w / 2, -hh / 2, w, hh); g.restore();
    }
    g.globalAlpha = 1;
    if (b.label) { g.fillStyle = '#e2e8f0'; g.font = '12px system-ui'; g.textAlign = 'center'; g.fillText(b.label, x, y - Math.max(14, (b.r || sz[1] / 2 || 0.5) * S + 8)); }
  }
  arrow(a, b, color = '#fbbf24', label) {
    const g = this.g, [x1, y1] = this.P(a), [x2, y2] = this.P(b), L = Math.hypot(x2 - x1, y2 - y1);
    if (L < 1) return;
    const ang = Math.atan2(y2 - y1, x2 - x1), hd = Math.min(12, L * 0.35);
    g.strokeStyle = g.fillStyle = color; g.lineWidth = 2.5;
    g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2 - hd * Math.cos(ang) * 0.8, y2 - hd * Math.sin(ang) * 0.8); g.stroke();
    g.beginPath(); g.moveTo(x2, y2); g.lineTo(x2 - hd * Math.cos(ang - 0.4), y2 - hd * Math.sin(ang - 0.4)); g.lineTo(x2 - hd * Math.cos(ang + 0.4), y2 - hd * Math.sin(ang + 0.4)); g.fill();
    if (label) { g.font = '12px system-ui'; g.textAlign = 'center'; g.fillText(label, x2, y2 - 8); }
  }
  drawDecor(d) {
    const g = this.g;
    if (d.shape === 'ground') { const [, y] = this.P([0, d.y || 0, 0]); if (this.plane === 'xz') return; g.fillStyle = '#16213a'; g.fillRect(0, y, this.W, this.H - y); g.strokeStyle = '#334155'; g.beginPath(); g.moveTo(0, y); g.lineTo(this.W, y); g.stroke(); }
    else if (d.shape === 'ramp') {
      const th = d.angle * Math.PI / 180, x0 = d.x || 0, y0 = d.y || 0;
      const p = [[x0, y0], [x0 + d.length * Math.cos(th), y0], [x0, y0 + d.length * Math.sin(th)]].map(q => this.P([q[0], q[1], 0]));
      g.fillStyle = d.color || '#475569'; g.beginPath(); g.moveTo(...p[0]); g.lineTo(...p[1]); g.lineTo(...p[2]); g.closePath(); g.fill();
    } else if (d.shape === 'line') { g.strokeStyle = d.color || '#64748b'; g.globalAlpha = d.opacity ?? 1; g.beginPath(); d.pts.forEach((p, i) => (i ? g.lineTo(...this.P(p)) : g.moveTo(...this.P(p)))); g.stroke(); g.globalAlpha = 1; }
    else if (['box', 'sphere', 'cylinder', 'torus'].includes(d.shape)) this.drawBody(d);
    else if (d.shape === 'label') { const [x, y] = this.P(d.pos); g.fillStyle = d.color || '#94a3b8'; g.font = '12px system-ui'; g.textAlign = 'center'; g.fillText(d.text, x, y); }
    else if (d.shape === 'stars') { g.fillStyle = '#cbd5e1'; let s = 7; for (let i = 0; i < 300; i++) { s = (s * 16807) % 2147483647; const x = s % this.W; s = (s * 16807) % 2147483647; g.fillRect(x, s % this.H, 1, 1); } }
  }
  dispose() { this.ro.disconnect(); this.c.remove(); }
}
