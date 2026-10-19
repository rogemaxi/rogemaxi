// SVG diagram library for lesson visuals. Every diagram is generated from parameters in the content file,
// so geometry and labels stay consistent with the physics (e.g. arrow lengths are proportional to magnitudes).
import { esc } from './ui.js';

const COLORS = { good: '#4ade80', bad: '#f87171', blue: '#7dd3fc', gold: '#fbbf24', purple: '#c084fc', pink: '#f472b6', dim: '#94a3b8', txt: '#e2e8f0', orange: '#fb923c', cyan: '#22d3ee' };
const C = c => COLORS[c] || c || COLORS.gold;
const svg = (w, h, body, title) => `<svg viewBox="0 0 ${w} ${h}" class="diagram" role="img" aria-label="${esc(title || 'diagram')}"><title>${esc(title || '')}</title><defs>${['good', 'bad', 'blue', 'gold', 'purple', 'pink', 'dim', 'txt', 'orange', 'cyan'].map(k => `<marker id="ah-${k}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${COLORS[k]}"/></marker>`).join('')}</defs>${body}</svg>`;
const arrow = (x1, y1, x2, y2, c = 'gold', w = 3) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${C(c)}" stroke-width="${w}" marker-end="url(#ah-${COLORS[c] ? c : 'gold'})"/>`;
// Right-to-left labels (Arabic) get an RTL base direction; text-anchor start/end then refer to the RTL edges, so flip them
// to keep the label on the same side of its arrow.
const text = (x, y, s, c = 'txt', size = 13, anchor = 'middle') => {
  const rtl = /[\u0600-\u06FF]/.test(String(s));
  const a = rtl ? ({ start: 'end', end: 'start' }[anchor] || anchor) : anchor;
  return `<text x="${x}" y="${y}" fill="${C(c)}" font-size="${size}" text-anchor="${a}" ${rtl ? 'direction="rtl" unicode-bidi="embed"' : ''} font-family="system-ui,sans-serif">${esc(s)}</text>`;
};

const KINDS = {
  // Free-body diagram: forces [{label, dir (deg), mag, color}] on a box; arrow length ∝ magnitude.
  fbd(d) {
    const W = 480, H = 330, cx = 240, cy = 165, max = Math.max(...d.forces.map(f => f.mag)), Lmax = 80;
    let b = `<rect x="${cx - 32}" y="${cy - 26}" width="64" height="52" rx="6" fill="#334155" stroke="#94a3b8"/>`;
    if (d.surface !== false) b += `<line x1="90" y1="${cy + 26}" x2="390" y2="${cy + 26}" stroke="#475569" stroke-width="2" stroke-dasharray="${d.surface === 'none' ? '0' : '6 4'}"/>`;
    for (const f of d.forces) {
      const L = 28 + Lmax * f.mag / max, r = f.dir * Math.PI / 180;
      const x2 = cx + Math.cos(r) * (L + 32), y2 = cy - Math.sin(r) * (L + 26);
      const x1 = cx + Math.cos(r) * 32 * (Math.abs(Math.cos(r)) > 0.5 ? 1 : 0), y1 = cy - Math.sin(r) * 26 * (Math.abs(Math.sin(r)) > 0.5 ? 1 : 0);
      b += arrow(x1, y1, x2, y2, f.color || 'gold');
      b += text(x2 + Math.cos(r) * 14, y2 - Math.sin(r) * 14 + 4, f.label, f.color || 'gold', 12, Math.cos(r) > 0.3 ? 'start' : Math.cos(r) < -0.3 ? 'end' : 'middle');
    }
    if (d.net) b += text(14, 22, d.net, 'good', 14, 'start');
    return svg(W, H, b, d.title);
  },
  // Function / data plot: series [{fn: (x)=>y as string expression in x, or pts:[[x,y]]}], axes labels.
  plot(d) {
    const W = 380, H = 250, pl = 48, pr = 14, pt = 14, pb = 38;
    const [x0, x1] = d.x || [0, 10], [y0, y1] = d.y || [0, 10];
    const X = x => pl + (x - x0) / (x1 - x0) * (W - pl - pr), Y = y => H - pb - (y - y0) / (y1 - y0) * (H - pt - pb);
    let b = `<rect x="${pl}" y="${pt}" width="${W - pl - pr}" height="${H - pt - pb}" fill="#0b1220" stroke="#334155"/>`;
    if (y0 < 0 && y1 > 0) b += `<line x1="${pl}" y1="${Y(0)}" x2="${W - pr}" y2="${Y(0)}" stroke="#64748b"/>`;
    for (const tk of d.xticks || []) b += text(X(tk), H - pb + 15, tk, 'dim', 11);
    for (const tk of d.yticks || []) b += text(pl - 6, Y(tk) + 4, tk, 'dim', 11, 'end');
    b += text((pl + W - pr) / 2, H - 6, d.xLabel || 'x', 'txt', 12) + `<text transform="translate(13,${(pt + H - pb) / 2}) rotate(-90)" fill="${COLORS.txt}" font-size="12" text-anchor="middle">${esc(d.yLabel || 'y')}</text>`;
    (d.series || []).forEach((s, i) => {
      let pts = s.pts;
      if (s.fn) { const f = new Function('x', 'return ' + s.fn); pts = []; for (let k = 0; k <= 120; k++) { const x = x0 + (x1 - x0) * k / 120, y = f(x); if (Number.isFinite(y) && y >= y0 - (y1 - y0) && y <= y1 + (y1 - y0)) pts.push([x, y]); } }
      const c = C(s.color || ['gold', 'blue', 'good', 'pink'][i % 4]);
      if (s.dots) b += pts.map(p => `<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="3.5" fill="${c}"/>`).join('');
      else b += `<polyline fill="none" stroke="${c}" stroke-width="2.4" ${s.dashed ? 'stroke-dasharray="6 4"' : ''} points="${pts.map(p => `${X(p[0]).toFixed(1)},${Y(Math.max(y0, Math.min(y1, p[1]))).toFixed(1)}`).join(' ')}"/>`;
      if (s.label) b += text(X(s.lx ?? pts.at(-1)[0]) - 4, Y(s.ly ?? pts.at(-1)[1]) - 8, s.label, s.color || ['gold', 'blue', 'good', 'pink'][i % 4], 12, 'end');
      if (s.shade) b += `<polygon fill="${c}" opacity="0.18" points="${X(pts[0][0])},${Y(0)} ${pts.map(p => `${X(p[0])},${Y(p[1])}`).join(' ')} ${X(pts.at(-1)[0])},${Y(0)}"/>`;
    });
    for (const n of d.notes || []) b += text(X(n[0]), Y(n[1]), n[2], n[3] || 'gold', 12);
    return svg(W, H, b, d.title);
  },
  // Vector addition: vectors [{x, y, label, color}] drawn tip-to-tail with resultant.
  vectors(d) {
    const W = 360, H = 260, s = d.scale || 18, ox = d.ox ?? 60, oy = d.oy ?? 210;
    let b = `<line x1="20" y1="${oy}" x2="340" y2="${oy}" stroke="#334155"/><line x1="${ox}" y1="20" x2="${ox}" y2="245" stroke="#334155"/>`;
    let x = ox, y = oy;
    for (const v of d.vectors) { const nx = x + v.x * s, ny = y - v.y * s; b += arrow(x, y, nx, ny, v.color || 'blue'); b += text((x + nx) / 2 + 10, (y + ny) / 2 - 6, v.label, v.color || 'blue', 12); x = nx; y = ny; }
    if (d.resultant !== false) { b += arrow(ox, oy, x, y, 'gold', 3.5); b += text((ox + x) / 2 - 14, (oy + y) / 2 + 18, d.resultant || 'R', 'gold', 13); }
    if (d.components) { b += `<line x1="${ox}" y1="${oy}" x2="${x}" y2="${oy}" stroke="${COLORS.good}" stroke-dasharray="5 4" stroke-width="2"/><line x1="${x}" y1="${oy}" x2="${x}" y2="${y}" stroke="${COLORS.pink}" stroke-dasharray="5 4" stroke-width="2"/>`; }
    return svg(W, H, b, d.title);
  },
  // Incline with block and force components.
  incline(d) {
    const W = 380, H = 250, th = (d.angle || 30) * Math.PI / 180, x0 = 30, y0 = 220, L = 320;
    const xt = x0 + L * Math.cos(th) * 0 + 0, top = [x0, y0 - L * Math.sin(th) * 0.75];
    const base = [x0 + L * Math.cos(th) * 0.95, y0];
    let b = `<polygon points="${x0},${y0} ${base[0]},${y0} ${top[0]},${top[1]}" fill="#334155" stroke="#94a3b8"/>`;
    const mx = x0 + (base[0] - x0) * 0.42, my = y0 - (y0 - top[1]) * 0.58;
    const ang = -Math.atan2(y0 - top[1], base[0] - x0) * 180 / Math.PI;
    b += `<g transform="translate(${mx},${my}) rotate(${-ang * -1})"><rect x="-22" y="-36" width="44" height="34" rx="4" fill="#fbbf24"/></g>`;
    const ux = (base[0] - x0), uy = (y0 - top[1]); const n = Math.hypot(ux, uy); const dn = [ux / n, uy / n];
    const cx = mx + 0, cy = my - 18;
    b += arrow(cx, cy, cx, cy + 70, 'blue'); b += text(cx + 8, cy + 84, 'mg', 'blue', 12, 'start');
    b += arrow(cx, cy, cx - dn[1] * 60 * -1 * -1 + 0, cy - dn[0] * 60, 'purple'); b += text(cx - dn[1] * 60 + 0, cy - dn[0] * 60 - 8, 'N', 'purple', 12);
    if (d.components) { b += arrow(cx, cy, cx + dn[0] * 55, cy + dn[1] * 55, 'pink', 2); b += text(cx + dn[0] * 55 + 6, cy + dn[1] * 55 + 14, 'mg sinθ', 'pink', 11, 'start'); }
    if (d.friction) { b += arrow(cx, cy, cx - dn[0] * 45, cy - dn[1] * 45, 'bad', 2.5); b += text(cx - dn[0] * 45 - 4, cy - dn[1] * 45 - 6, 'f', 'bad', 12, 'end'); }
    b += text(base[0] - 46, y0 - 8, `θ = ${d.angle || 30}°`, 'dim', 12);
    return svg(W, H, b, d.title);
  },
  // Motion diagram: dots at equal time intervals for given positions.
  motion(d) {
    const W = 380, H = 120, xs = d.positions, max = Math.max(...xs), min = Math.min(0, ...xs);
    const X = x => 30 + (x - min) / (max - min || 1) * 320;
    let b = `<line x1="20" y1="70" x2="360" y2="70" stroke="#475569"/>`;
    xs.forEach((x, i) => { b += `<circle cx="${X(x)}" cy="70" r="7" fill="${COLORS.gold}" opacity="${0.4 + 0.6 * i / xs.length}"/>` + text(X(x), 95, `t${i}`, 'dim', 10); });
    if (d.vel) xs.slice(0, -1).forEach((x, i) => { b += arrow(X(x), 45, X(xs[i + 1]) - 4, 45, 'blue', 2); });
    b += text(190, 20, d.caption || '', 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Transverse wave snapshot with labeled wavelength and amplitude.
  wave(d) {
    const W = 380, H = 200, A = 50 * (d.amp || 1), lam = 140 * (d.lambda || 1), y0 = 100;
    let pts = []; for (let x = 20; x <= 360; x += 3) pts.push(`${x},${(y0 - A * Math.sin(2 * Math.PI * (x - 20) / lam + (d.phase || 0))).toFixed(1)}`);
    let b = `<line x1="20" y1="${y0}" x2="360" y2="${y0}" stroke="#334155" stroke-dasharray="4 4"/><polyline fill="none" stroke="${COLORS.blue}" stroke-width="2.5" points="${pts.join(' ')}"/>`;
    if (d.second) { pts = []; for (let x = 20; x <= 360; x += 3) pts.push(`${x},${(y0 - A * d.second.amp * Math.sin(2 * Math.PI * (x - 20) / lam + d.second.phase)).toFixed(1)}`); b += `<polyline fill="none" stroke="${COLORS.pink}" stroke-width="2" stroke-dasharray="5 4" points="${pts.join(' ')}"/>`; }
    const xp = 20 + lam / 4; b += `<line x1="${xp}" y1="${y0 - A - 12}" x2="${xp + lam}" y2="${y0 - A - 12}" stroke="${COLORS.gold}" marker-start="url(#ah-gold)" marker-end="url(#ah-gold)"/>` + text(xp + lam / 2, y0 - A - 18, 'λ', 'gold', 14);
    b += `<line x1="${xp - 6}" y1="${y0}" x2="${xp - 6}" y2="${y0 - A}" stroke="${COLORS.good}" marker-end="url(#ah-good)"/>` + text(xp - 12, y0 - A / 2, 'A', 'good', 13, 'end');
    if (d.caption) b += text(190, 190, d.caption, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Thin lens / mirror ray diagram computed from 1/f = 1/do + 1/di.
  lens(d) {
    const W = 400, H = 230, cx = 200, ay = 120, sc = d.scale || 4, f = d.f, dob = d.do, ho = d.ho || 10;
    const di = 1 / (1 / f - 1 / dob), m = -di / dob, hi = m * ho;
    const ox = cx - dob * sc, ix = cx + di * sc, oyT = ay - ho * sc, iyT = ay - hi * sc;
    let b = `<line x1="0" y1="${ay}" x2="${W}" y2="${ay}" stroke="#475569"/>`;
    b += f > 0 ? `<ellipse cx="${cx}" cy="${ay}" rx="7" ry="80" fill="rgba(125,211,252,0.18)" stroke="${COLORS.blue}"/>` : `<path d="M${cx - 8},${ay - 80} Q${cx},${ay} ${cx - 8},${ay + 80} L${cx + 8},${ay + 80} Q${cx},${ay} ${cx + 8},${ay - 80} Z" fill="rgba(125,211,252,0.18)" stroke="${COLORS.blue}"/>`;
    for (const s of [-1, 1]) b += `<circle cx="${cx + s * f * sc}" cy="${ay}" r="3" fill="${COLORS.gold}"/>` + text(cx + s * f * sc, ay + 16, 'F', 'gold', 11);
    b += arrow(ox, ay, ox, oyT, 'good', 3) + text(ox, oyT - 6, 'object', 'good', 11);
    const clip = (x, y) => [Math.max(0, Math.min(W, x)), y];
    // ray 1: parallel then through focal point
    const r1x2 = W, r1y2 = oyT + (oyT - ay) * 0 + (ay - oyT) * ((W - cx) / (f * sc)) * 1;
    b += `<polyline fill="none" stroke="${COLORS.gold}" stroke-width="1.6" points="${ox},${oyT} ${cx},${oyT} ${r1x2},${r1y2}"/>`;
    // ray 2: through center undeviated
    const slope = (ay - oyT) / (cx - ox);
    b += `<line x1="${ox}" y1="${oyT}" x2="${W}" y2="${oyT + slope * (W - ox)}" stroke="${COLORS.pink}" stroke-width="1.6"/>`;
    if (Number.isFinite(di) && Math.abs(ix) < 2 * W) {
      b += `<line x1="${ix}" y1="${ay}" x2="${ix}" y2="${iyT}" stroke="${di > 0 ? COLORS.purple : COLORS.dim}" stroke-width="3" ${di > 0 ? '' : 'stroke-dasharray="5 4"'} marker-end="url(#ah-purple)"/>`;
      b += text(ix, (di > 0 ? iyT + (hi > 0 ? -8 : 16) : iyT - 8), di > 0 ? 'real image' : 'virtual image', 'purple', 11);
      if (di < 0) b += `<line x1="${cx}" y1="${oyT}" x2="${ix}" y2="${iyT}" stroke="${COLORS.gold}" stroke-dasharray="4 4" stroke-width="1"/><line x1="${ox}" y1="${oyT}" x2="${ix}" y2="${iyT}" stroke="${COLORS.pink}" stroke-dasharray="4 4" stroke-width="1"/>`;
    }
    b += text(200, 222, d.caption || `f = ${f} cm, dₒ = ${dob} cm → dᵢ = ${di.toFixed(1)} cm, m = ${m.toFixed(2)}`, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Refraction at a boundary with Snell's law.
  refract(d) {
    const W = 360, H = 260, cx = 180, cy = 130, n1 = d.n1, n2 = d.n2, t1 = d.theta * Math.PI / 180;
    const s2 = n1 * Math.sin(t1) / n2;
    let b = `<rect x="0" y="${cy}" width="${W}" height="${H - cy}" fill="rgba(125,211,252,0.12)"/><line x1="0" y1="${cy}" x2="${W}" y2="${cy}" stroke="#7dd3fc"/><line x1="${cx}" y1="20" x2="${cx}" y2="${H - 20}" stroke="#64748b" stroke-dasharray="5 4"/>`;
    b += arrow(cx - Math.sin(t1) * 110, cy - Math.cos(t1) * 110, cx, cy, 'gold');
    if (Math.abs(s2) <= 1) { const t2 = Math.asin(s2); b += arrow(cx, cy, cx + Math.sin(t2) * 110, cy + Math.cos(t2) * 110, 'gold'); b += text(cx + 40, cy + 60, `θ₂ = ${(t2 * 180 / Math.PI).toFixed(1)}°`, 'gold', 12, 'start'); }
    else b += text(cx + 20, cy + 40, 'total internal reflection', 'bad', 12, 'start');
    b += arrow(cx, cy, cx + Math.sin(t1) * 90, cy - Math.cos(t1) * 90, 'dim', 1.5);
    b += text(cx - 50, cy - 30, `θ₁ = ${d.theta}°`, 'gold', 12, 'end') + text(16, cy - 10, `n₁ = ${n1}`, 'txt', 12, 'start') + text(16, cy + 22, `n₂ = ${n2}`, 'txt', 12, 'start');
    return svg(W, H, b, d.title);
  },
  // Simple circuit: series or parallel resistors with a battery.
  circuit(d) {
    const W = 380, H = 230; const R = d.resistors || [];
    let b = `<rect x="40" y="40" width="300" height="150" fill="none" stroke="${COLORS.dim}" stroke-width="2"/>`;
    b += `<line x1="30" y1="100" x2="50" y2="100" stroke="${COLORS.txt}" stroke-width="3"/><line x1="34" y1="112" x2="46" y2="112" stroke="${COLORS.txt}" stroke-width="3"/><rect x="28" y="90" width="24" height="30" fill="#0b1220" opacity="0"/>`;
    b += `<rect x="25" y="98" width="30" height="16" fill="#0b1220"/><line x1="28" y1="100" x2="52" y2="100" stroke="${COLORS.gold}" stroke-width="3"/><line x1="33" y1="112" x2="47" y2="112" stroke="${COLORS.gold}" stroke-width="3"/>` + text(18, 140, `${d.V} V`, 'gold', 12, 'start');
    const zig = (x, y, vert) => { let p = []; for (let i = 0; i <= 8; i++) p.push(vert ? `${x + (i % 2 ? 8 : -8) * (i > 0 && i < 8)},${y - 24 + i * 6}` : `${x - 24 + i * 6},${y + (i % 2 ? 8 : -8) * (i > 0 && i < 8)}`); return `<rect x="${vert ? x - 10 : x - 26}" y="${vert ? y - 26 : y - 10}" width="${vert ? 20 : 52}" height="${vert ? 52 : 20}" fill="#0b1220"/><polyline fill="none" stroke="${COLORS.blue}" stroke-width="2.5" points="${p.join(' ')}"/>`; };
    if (d.mode === 'parallel') {
      R.forEach((r, i) => { const x = 140 + i * 80; b += `<line x1="${x}" y1="40" x2="${x}" y2="190" stroke="${COLORS.dim}" stroke-width="2"/>` + zig(x, 115, true) + text(x + 16, 120, `${r} Ω`, 'blue', 12, 'start'); });
    } else {
      R.forEach((r, i) => { const x = 110 + i * (220 / Math.max(1, R.length - 0.5)) * 0.9; b += zig(x, 40, false) + text(x, 28, `${r} Ω`, 'blue', 12); });
    }
    if (d.caption) b += text(190, 220, d.caption, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Electric field lines around point charges [{q:+1|-1, x, y}] (coordinates 0..1).
  field(d) {
    const W = 360, H = 260, ch = d.charges.map(c => ({ ...c, X: 30 + c.x * 300, Y: 20 + c.y * 220 }));
    let b = '';
    const E = (x, y) => { let ex = 0, ey = 0; for (const c of ch) { const dx = x - c.X, dy = y - c.Y, r2 = dx * dx + dy * dy + 1, r = Math.sqrt(r2); ex += c.q * dx / (r2 * r); ey += c.q * dy / (r2 * r); } return [ex, ey]; };
    for (const c of ch.filter(c => c.q > 0)) for (let k = 0; k < 14; k++) {
      let x = c.X + 12 * Math.cos(k * Math.PI / 7), y = c.Y + 12 * Math.sin(k * Math.PI / 7), pts = [`${x.toFixed(1)},${y.toFixed(1)}`];
      for (let s = 0; s < 260; s++) { const [ex, ey] = E(x, y), n = Math.hypot(ex, ey); if (!n) break; x += 2 * ex / n; y += 2 * ey / n; pts.push(`${x.toFixed(1)},${y.toFixed(1)}`); if (x < 0 || x > W || y < 0 || y > H || ch.some(o => o.q < 0 && Math.hypot(x - o.X, y - o.Y) < 10)) break; }
      b += `<polyline fill="none" stroke="${COLORS.blue}" stroke-width="1.2" opacity="0.8" points="${pts.join(' ')}"/>`;
      const mid = pts[Math.floor(pts.length / 3)]?.split(',').map(Number), nx = pts[Math.floor(pts.length / 3) + 1]?.split(',').map(Number);
      if (mid && nx) b += arrow(mid[0], mid[1], nx[0], nx[1], 'blue', 1.2);
    }
    if (!ch.some(c => c.q > 0)) for (const c of ch) for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6; b += arrow(c.X + Math.cos(a) * 110, c.Y + Math.sin(a) * 110, c.X + Math.cos(a) * 18, c.Y + Math.sin(a) * 18, 'blue', 1.2); }
    for (const c of ch) b += `<circle cx="${c.X}" cy="${c.Y}" r="11" fill="${c.q > 0 ? COLORS.bad : COLORS.blue}"/>` + text(c.X, c.Y + 5, c.q > 0 ? '+' : '−', '#0b1220', 15);
    return svg(W, H, b, d.title);
  },
  // Orbit: central body and elliptical orbit with eccentricity e.
  orbit(d) {
    const W = 360, H = 240, a = 140, e = d.e || 0, bb = a * Math.sqrt(1 - e * e), cx = 180 + 0, c = a * e;
    let b = `<ellipse cx="${cx}" cy="120" rx="${a}" ry="${bb}" fill="none" stroke="${COLORS.blue}" stroke-dasharray="${d.dashed ? '5 4' : '0'}"/>`;
    b += `<circle cx="${cx + c}" cy="120" r="14" fill="${COLORS.gold}"/>` + text(cx + c, 150, d.central || 'Sun', 'gold', 11);
    b += `<circle cx="${cx - a}" cy="120" r="6" fill="${COLORS.good}"/>` + text(cx - a, 106, d.far || 'aphelion', 'dim', 10);
    b += `<circle cx="${cx + a}" cy="120" r="6" fill="${COLORS.good}"/>` + text(cx + a - 6, 106, d.near || 'perihelion', 'dim', 10, 'end');
    if (d.sweep) b += `<path d="M${cx + c},120 L${cx + a},120 A${a},${bb} 0 0 0 ${cx + a * Math.cos(0.5)},${120 - bb * Math.sin(0.5)} Z" fill="${COLORS.gold}" opacity="0.25"/><path d="M${cx + c},120 L${cx - a},120 A${a},${bb} 0 0 0 ${cx - a * Math.cos(0.2)},${120 + bb * Math.sin(0.2)} Z" fill="${COLORS.pink}" opacity="0.25"/>`;
    if (d.caption) b += text(180, 232, d.caption, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Spring-mass or pendulum sketch.
  spring(d) {
    const W = 360, H = 200, x = 60 + (d.stretch ?? 0.5) * 160;
    let p = [`20,100`]; for (let i = 1; i < 15; i++) p.push(`${20 + (x - 40) * i / 15},${100 + (i % 2 ? -14 : 14)}`); p.push(`${x - 20},100`);
    let b = `<rect x="10" y="50" width="10" height="100" fill="#475569"/><polyline fill="none" stroke="${COLORS.dim}" stroke-width="2" points="${p.join(' ')}"/><rect x="${x - 20}" y="78" width="44" height="44" rx="5" fill="${COLORS.gold}"/><line x1="10" y1="150" x2="350" y2="150" stroke="#475569"/>`;
    b += `<line x1="${60 + 0.5 * 160 + 2}" y1="40" x2="${60 + 0.5 * 160 + 2}" y2="160" stroke="${COLORS.good}" stroke-dasharray="4 4"/>` + text(60 + 0.5 * 160 + 2, 34, 'x = 0', 'good', 11);
    if (d.force) b += arrow(x + 2, 64, x + 2 - (x - 142) * 0.8, 64, 'bad') + text(x - 10, 56, 'F = −kx', 'bad', 12);
    if (d.caption) b += text(180, 185, d.caption, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  pendulum(d) {
    const W = 300, H = 230, L = 160, th = (d.angle || 25) * Math.PI / 180, px = 150 + L * Math.sin(th), py = 20 + L * Math.cos(th);
    let b = `<line x1="80" y1="20" x2="220" y2="20" stroke="#94a3b8" stroke-width="3"/><line x1="150" y1="20" x2="150" y2="${20 + L + 20}" stroke="#475569" stroke-dasharray="4 4"/><line x1="150" y1="20" x2="${px}" y2="${py}" stroke="${COLORS.txt}" stroke-width="2"/><circle cx="${px}" cy="${py}" r="14" fill="${COLORS.gold}"/>`;
    b += text(158, 60, 'θ', 'gold', 13, 'start') + text(px / 2 + 85, py / 2 + 5, 'L', 'txt', 13, 'end');
    if (d.forces) { b += arrow(px, py, px, py + 60, 'blue') + text(px + 6, py + 70, 'mg', 'blue', 12, 'start') + arrow(px, py, px + (150 - px) * 0.45, py + (20 - py) * 0.45, 'purple') + text(px + (150 - px) * 0.5 - 8, py + (20 - py) * 0.5, 'T', 'purple', 12, 'end'); }
    if (d.caption) b += text(150, 222, d.caption, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Energy bar chart (LOL diagram style): bars [{label, value, color}]
  bars(d) {
    const W = 360, H = 220, n = d.bars.length, bw = 240 / n, max = Math.max(...d.bars.map(b => Math.abs(b.value)), 1);
    let b = `<line x1="50" y1="170" x2="330" y2="170" stroke="#64748b"/>`;
    d.bars.forEach((r, i) => { const h = 130 * r.value / max, x = 64 + i * (bw + 8); b += `<rect x="${x}" y="${170 - Math.max(h, 0)}" width="${bw - 6}" height="${Math.abs(h)}" fill="${C(r.color || 'gold')}" rx="3"/>` + text(x + bw / 2 - 3, 190, r.label, 'txt', 11) + text(x + bw / 2 - 3, 165 - Math.max(h, 0), r.text ?? String(r.value), 'dim', 11); });
    if (d.caption) b += text(180, 212, d.caption, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Generic labeled flow / process steps
  flow(d) {
    const W = 380, n = d.steps.length, H = 40 + n * 46;
    let b = '';
    d.steps.forEach((s, i) => { const y = 20 + i * 46; b += `<rect x="40" y="${y}" width="300" height="34" rx="8" fill="#1e293b" stroke="${C(d.color || 'blue')}"/>` + text(190, y + 22, s, 'txt', 12); if (i < n - 1) b += arrow(190, y + 34, 190, y + 45, 'gold', 2); });
    return svg(W, H, b, d.title);
  },
  // Number line / position axis with labeled points
  axis(d) {
    const W = 380, H = 110, [a, z] = d.range || [-10, 10], X = x => 30 + (x - a) / (z - a) * 320;
    let b = `<line x1="20" y1="60" x2="360" y2="60" stroke="${COLORS.dim}" stroke-width="2" marker-end="url(#ah-dim)"/>`;
    for (let x = Math.ceil(a); x <= z; x += d.step || 2) b += `<line x1="${X(x)}" y1="55" x2="${X(x)}" y2="65" stroke="${COLORS.dim}"/>` + text(X(x), 82, x, 'dim', 10);
    for (const p of d.points || []) b += `<circle cx="${X(p.x)}" cy="60" r="6" fill="${C(p.color || 'gold')}"/>` + text(X(p.x), 42, p.label, p.color || 'gold', 11);
    for (const ar of d.arrows || []) b += arrow(X(ar.from), 30 + (ar.row || 0) * -10, X(ar.to), 30 + (ar.row || 0) * -10, ar.color || 'blue', 2.5) + (ar.label ? text((X(ar.from) + X(ar.to)) / 2, 22 + (ar.row || 0) * -10, ar.label, ar.color || 'blue', 11) : '');
    if (d.caption) b += text(190, 104, d.caption, 'txt', 12);
    return svg(W, H, b, d.title);
  },
  // Projectile trajectory computed from v0, angle (deg), g.
  trajectory(d) {
    const g = d.g || 9.8, th = d.angle * Math.PI / 180, vx = d.v0 * Math.cos(th), vy = d.v0 * Math.sin(th), h0 = d.h0 || 0;
    const T = (vy + Math.sqrt(vy * vy + 2 * g * h0)) / g, R = vx * T, Hm = h0 + Math.max(0, vy * vy / (2 * g));
    const pts = []; for (let k = 0; k <= 60; k++) { const t = T * k / 60; pts.push([vx * t, h0 + vy * t - 0.5 * g * t * t]); }
    const series = [{ pts, color: 'gold' }];
    if (d.compare) for (const c of d.compare) { const t2 = c * Math.PI / 180, vx2 = d.v0 * Math.cos(t2), vy2 = d.v0 * Math.sin(t2), T2 = (vy2 + Math.sqrt(vy2 * vy2 + 2 * g * h0)) / g; const p2 = []; for (let k = 0; k <= 60; k++) { const t = T2 * k / 60; p2.push([vx2 * t, h0 + vy2 * t - 0.5 * g * t * t]); } series.push({ pts: p2, color: 'blue', dashed: true, label: c + '°' }); }
    const xm = Math.max(R, ...series.map(s => s.pts.at(-1)[0])) * 1.08, ym = Math.max(Hm, ...series.flatMap(s => s.pts.map(p => p[1]))) * 1.25;
    return KINDS.plot({ title: d.title, x: [0, xm], y: [0, ym], xLabel: 'x (m)', yLabel: 'y (m)', series, xticks: [0, +(xm / 2).toFixed(0), +xm.toFixed(0)], yticks: [0, +(ym / 2).toFixed(1)], notes: [[R / 2, Hm * 1.08, `R = ${R.toFixed(1)} m, H = ${Hm.toFixed(1)} m`]] });
  },
};

export function renderDiagram(v) {
  if (!v) return '';
  const fn = KINDS[v.kind];
  if (!fn) return '';
  try { return `<figure class="fig">${fn(v)}${v.caption && !['wave', 'lens', 'circuit', 'orbit', 'spring', 'pendulum', 'bars', 'motion', 'axis'].includes(v.kind) ? `<figcaption>${esc(v.caption)}</figcaption>` : ''}</figure>`; }
  catch (e) { return `<p class="hint">[diagram unavailable: ${esc(e.message)}]</p>`; }
}
export const DIAGRAM_KINDS = Object.keys(KINDS);
