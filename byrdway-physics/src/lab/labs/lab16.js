// Lab 16 — Electric Field Explorer. Up to three fixed point charges; field lines and a field-arrow grid are
// traced from the library fieldAt, a test charge is released from rest and integrated with RK4 under the
// Coulomb force, and the electric potential is read at the release point (probe) and along the path.
import { fieldAt, potentialAt, rk4Step, C } from '../../physics/index.js';

const uC = 1e-6;
const POS = [[-1.5, 0], [1.5, 0], [0, 2]];   // fixed charge positions (m)
const BOX = 4;          // the run ends when the test charge leaves |x| > 4 m or |y| > 4 m
const R_HIT = 0.15;     // the run ends when the test charge comes within 0.15 m of a source charge
const TMAX = 6;
const SUB = 8;          // RK4 sub-steps per harness step

export const charges = p => [p.q1, p.q2, p.q3].map((q, i) => ({ q: q * uC, x: POS[i][0], y: POS[i][1], uc: q })).filter(c => c.q !== 0);

// Field line traced along +E (dir = 1) or −E (dir = −1) with unit steps of ds, using fieldAt.
function traceLine(chs, start, dir, ds = 0.04, nMax = 400) {
  const pts = [[start[0], start[1], 0]];
  let x = start[0], y = start[1], end = 'box';
  for (let i = 0; i < nMax; i++) {
    const f = q => { const [ex, ey] = fieldAt(chs, q); const m = Math.hypot(ex, ey) || 1; return [dir * ex / m, dir * ey / m]; };
    // midpoint step (RK2) along the unit field direction
    const k1 = f([x, y]), k2 = f([x + k1[0] * ds / 2, y + k1[1] * ds / 2]);
    x += k2[0] * ds; y += k2[1] * ds;
    pts.push([x, y, 0]);
    const hit = chs.find(c => Math.hypot(x - c.x, y - c.y) < 0.12);
    if (hit) { end = hit; break; }
    if (Math.abs(x) > BOX + 1 || Math.abs(y) > BOX) break;
  }
  return { pts, end };
}

export function fieldLines(p) {
  const chs = charges(p), out = [];
  for (const c of chs) {
    const n = Math.max(4, Math.round(4 * Math.abs(c.uc)));
    for (let k = 0; k < n; k++) {
      const a = (k + 0.5) / n * 2 * Math.PI, s = [c.x + 0.14 * Math.cos(a), c.y + 0.14 * Math.sin(a)];
      if (c.q > 0) out.push({ pts: traceLine(chs, s, 1).pts, color: '#fca5a5' });
      else {
        // lines arriving at a negative charge from a positive one are already drawn; keep only those from far away
        const tr = traceLine(chs, s, -1);
        if (!(tr.end && tr.end.q > 0)) out.push({ pts: tr.pts, color: '#93c5fd' });
      }
    }
  }
  return out;
}

export default {
  num: 16, unit: 15, sections: ['15.3', '15.4', '15.5', '15.6', '15.8'],
  text: {
    title: 'Electric Field Explorer',
    question: 'How do several point charges combine to make an electric field, and how does a test charge move and trade potential energy for kinetic energy in that field?',
    params: { q1: 'Charge q₁ at (−1.5, 0) m', q2: 'Charge q₂ at (+1.5, 0) m', q3: 'Charge q₃ at (0, +2.0) m', qt: 'Test charge q', mt: 'Test charge mass', x0: 'Release point x₀', y0: 'Release point y₀' },
    graph: ['speed v (m/s)', 'energy (J)', 'potential at the test charge V (V)', 'field strength at the test charge E (N/C)', 'path: y vs x (m)'],
    series: { KE: 'kinetic', U: 'potential energy qV', Etot: 'total' },
    measures: { t: 'Time', x: 'x', y: 'y', v: 'Speed', E: 'Field strength at test charge', F: 'Force on test charge', V: 'Potential at test charge', Vp: 'Potential at release point (probe)', E0: 'Field strength at release point', disp: 'Distance from release point', KE: 'Kinetic energy', U: 'Electric potential energy qV', Etot: 'Total energy', status: 'Ended: 1 escaped, 2 hit a charge' },
    predict: {
      prompt: 'A positive test charge is released from rest near a positive source charge (q₁ = +3 μC, q₂ = −3 μC). As it moves, what happens to its electric potential energy?',
      choices: ['It increases', 'It decreases while the kinetic energy increases', 'It stays constant', 'It increases and the kinetic energy increases too'],
    },
    guided: [
      'Set q₁ = +3 μC and q₂ = q₃ = 0. Look at the field lines and arrows. Move the release point and use the probe readings to show that E = k·q/r² and V = k·q/r (r is the distance from q₁).',
      'Make a dipole: q₁ = +3 μC, q₂ = −3 μC. Release a +0.2 μC test charge at (−0.5, 1.0). Compare its path with the field lines. Does the charge follow a field line exactly? Why not?',
      'With the dipole, use the energy graph: show that kinetic energy gained equals the loss of qV, so the total stays constant (ΔKE = −qΔV).',
      'Set q₁ = q₂ = +3 μC. Find the point between them where the field is zero. Is the potential zero there too? Explain the difference between E = 0 and V = 0.',
      'Turn on q₃. Use superposition: at the release point, add the three fields as vectors and compare with the E reading.',
    ],
    challenges: [
      'Find an equilibrium point: with at least two source charges on, record a full 6 s run in which the test charge stays within 0.02 m of its release point.',
      'With at least two source charges on, choose a release point where the potential is zero (|V| ≤ 500 V) but the field is not (E ≥ 1000 N/C). Run it.',
      'Use only q₁ (q₂ = q₃ = 0) and a test charge with the same sign. Release it from (−1.0, 0) and make it leave the field region with a speed of 5.0 m/s (±0.15 m/s).',
    ],
    evaluate: 'Before you run: q₁ = {q1} μC at (−1.5, 0) m, q₂ = {q2} μC at (1.5, 0) m and q₃ = {q3} μC at (0, 2) m. Calculate the electric potential at the release point ({x0}, {y0}) m (k = 8.99 × 10⁹ N·m²/C²).',
    honors: {
      prompt: 'For q₁ = +4 μC at x = −1.5 m and q₂ = +1 μC at x = +1.5 m (q₃ = 0), predict where on the x-axis the net field is zero. Then confirm it in the lab by releasing a test charge there, and explain why the potential there is not zero.',
      solution: 'Between two like charges the fields oppose, so the zero lies between them, nearer the smaller charge: k(4 μC)/(x + 1.5)² = k(1 μC)/(1.5 − x)² → 2(1.5 − x) = x + 1.5 → x = 0.5 m. Released at (0.5, 0) the test charge stays put (E = 0). The potential there is V = k(4 μC)/2 + k(1 μC)/1 = 8.99 × 10⁹ × (2 + 1) × 10⁻⁶ ≈ 2.70 × 10⁴ V: potentials add as scalars and never cancel for like charges.',
    },
    assumptions: [
      'Source charges are fixed point charges; the test charge is a point charge whose own field does not move them.',
      'Coulomb’s law with k = 8.988 × 10⁹ N·m²/C²; the charges are in vacuum. Gravity, air drag and radiation are neglected (think of a frictionless horizontal air table seen from above).',
      'The test-charge motion is integrated with fourth-order Runge–Kutta (8 sub-steps of 1/1920 s per frame step); total energy KE + qV is conserved to better than 0.1 %.',
      'Field lines are traced from fieldAt by stepping along the field direction; their number per charge is proportional to |q| (4 per μC). Lines are a picture of direction, not a measurement.',
      'The field-arrow lengths use a logarithmic scale so both weak and strong regions are visible; only their directions are exact.',
      'The run ends after 6 s, when the test charge leaves the 8 m × 8 m region, or when it comes within 0.15 m of a source charge. The flash at a collision is a visual effect only.',
    ],
  },
  params: [
    { id: 'q1', min: -5, max: 5, step: 0.5, value: 3, unit: 'μC' },
    { id: 'q2', min: -5, max: 5, step: 0.5, value: -3, unit: 'μC' },
    { id: 'q3', min: -5, max: 5, step: 0.5, value: 0, unit: 'μC' },
    { id: 'qt', min: -1, max: 1, step: 0.05, value: 0.2, unit: 'μC' },
    { id: 'mt', min: 0.1, max: 10, step: 0.1, value: 2, unit: 'g' },
    { id: 'x0', min: -3.5, max: 3.5, step: 0.1, value: -0.5, unit: 'm' },
    { id: 'y0', min: -3.5, max: 3.5, step: 0.1, value: 1, unit: 'm' },
  ],
  camera: { target: [0, 0, 0], dist: 11.5, free: [0.18, 0.28, 1], followId: 'test' },
  view2d: { span: 10, cx: 0, cy: 0 },
  graph: {
    choices: [
      { label: 'speed v (m/s)', y: ['v'], labels: ['v'], yLabel: 'v (m/s)' },
      { label: 'energy (J)', y: ['KE', 'U', 'Etot'], labels: ['KE', 'U', 'Etot'], yLabel: 'energy (J)' },
      { label: 'potential at the test charge V (V)', y: ['V'], labels: ['V'], yLabel: 'V (V)' },
      { label: 'field strength at the test charge E (N/C)', y: ['E'], labels: ['E'], yLabel: 'E (N/C)' },
      { label: 'path: y vs x (m)', x: 'x', xLabel: 'x (m)', y: ['y'], labels: ['y'], yLabel: 'y (m)' },
    ],
  },
  recordKeys: ['Vp', 'E0', 'v', 'KE', 'disp', 'status'],
  decor: p => {
    const out = [
      { shape: 'plane', size: [2 * BOX + 1, 2 * BOX], pos: [0, 0, -0.06], color: '#0f172a', opacity: 0.9 },
      { shape: 'line', pts: [[-BOX, -BOX, 0], [BOX, -BOX, 0], [BOX, BOX, 0], [-BOX, BOX, 0], [-BOX, -BOX, 0]], color: '#475569' },
      { shape: 'line', pts: [[-BOX, 0, -0.02], [BOX, 0, -0.02]], color: '#334155', opacity: 0.6 },
      { shape: 'line', pts: [[0, -BOX, -0.02], [0, BOX, -0.02]], color: '#334155', opacity: 0.6 },
      ...[-3, -2, -1, 1, 2, 3].map(i => ({ shape: 'label', text: `${i} m`, pos: [i, -0.25, 0], color: '#64748b' })),
      { shape: 'label', text: 'probe (release point)', pos: [p.x0, p.y0 - 0.35, 0], color: '#fde68a' },
      { shape: 'torus', r: 0.14, tube: 0.015, pos: [p.x0, p.y0, 0], color: '#fde68a' },
    ];
    for (const l of fieldLines(p)) out.push({ shape: 'line', pts: l.pts, color: l.color, opacity: 0.75 });
    return out;
  },
  create(p) {
    const chs = charges(p), q = p.qt * uC, m = p.mt * 1e-3;
    const nSrc = chs.length;
    const s = { t: 0, y: [p.x0, p.y0, 0, 0], done: false, status: 0, events: [] };
    const deriv = y => { const [ex, ey] = fieldAt(chs, [y[0], y[1]]); return [y[2], y[3], q * ex / m, q * ey / m]; };
    const Vp = potentialAt(chs, [p.x0, p.y0]);
    const E0 = Math.hypot(...fieldAt(chs, [p.x0, p.y0]));
    const near = (x, y) => chs.some(c => Math.hypot(x - c.x, y - c.y) < R_HIT);
    if (near(p.x0, p.y0)) s.done = true;
    const read = () => {
      const [x, y, vx, vy] = s.y, Ev = fieldAt(chs, [x, y]), V = potentialAt(chs, [x, y]);
      const KE = 0.5 * m * (vx * vx + vy * vy), U = q * V;
      return { x, y, vx, vy, Ev, E: Math.hypot(...Ev), V, KE, U };
    };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        if (s.done) return;
        const h = dt / SUB;
        for (let i = 0; i < SUB; i++) {
          s.y = rk4Step(deriv, s.y, h); s.t += h;
          if (near(s.y[0], s.y[1])) {
            s.done = true; s.status = 2;
            s.events.push({ type: 'impact', pos: [s.y[0], s.y[1], 0], strength: 0.6, color: '#fde68a' });
            return;
          }
          if (Math.abs(s.y[0]) > BOX || Math.abs(s.y[1]) > BOX) { s.done = true; s.status = 1; return; }
        }
        if (s.t >= TMAX - 1e-9) s.done = true;
      },
      measures() {
        const r = read();
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'x', label: 'x', value: r.x, unit: 'm', ref: BOX, hidden: true },
          { id: 'y', label: 'y', value: r.y, unit: 'm', ref: BOX, hidden: true },
          { id: 'v', label: 'Speed', value: Math.hypot(r.vx, r.vy), unit: 'm/s', ref: 10 },
          { id: 'E', label: 'Field strength at test charge', value: r.E, unit: 'N/C', ref: 1e6 },
          { id: 'F', label: 'Force on test charge', value: Math.abs(q) * r.E, unit: 'N', ref: 0.1 },
          { id: 'V', label: 'Potential at test charge', value: r.V, unit: 'V', ref: 1e5 },
          { id: 'Vp', label: 'Potential at release point (probe)', value: Vp, unit: 'V', ref: 1e5 },
          { id: 'E0', label: 'Field strength at release point', value: E0, unit: 'N/C', ref: 1e6 },
          { id: 'disp', label: 'Distance from release point', value: Math.hypot(r.x - p.x0, r.y - p.y0), unit: 'm', ref: 8 },
          { id: 'KE', label: 'Kinetic energy', value: r.KE, unit: 'J', ref: 0.05, hidden: true },
          { id: 'U', label: 'Electric potential energy qV', value: r.U, unit: 'J', ref: 0.05, hidden: true },
          { id: 'Etot', label: 'Total energy', value: r.KE + r.U, unit: 'J', ref: 0.05, hidden: true },
          { id: 'status', label: 'Ended: 1 escaped, 2 hit a charge', value: s.status, unit: '', hidden: true },
          { id: 'nSrc', label: 'Source charges', value: nSrc, unit: '', hidden: true },
        ];
      },
      energy() {
        const r = read();
        return [{ label: 'KE', value: r.KE, color: '#fbbf24' }, { label: 'U = qV', value: r.U, color: '#a78bfa' }, { label: 'Total', value: r.KE + r.U, color: '#4ade80' }];
      },
      scene() {
        const r = read();
        const bodies = chs.map((c, i) => ({ id: 'src' + i, shape: 'sphere', r: 0.12 + 0.03 * Math.abs(c.uc), pos: [c.x, c.y, 0], color: c.q > 0 ? '#ef4444' : '#3b82f6', emissive: c.q > 0 ? '#7f1d1d' : '#1e3a8a', glow: 0.8, label: `${c.uc > 0 ? '+' : ''}${c.uc} μC` }));
        bodies.push({ id: 'test', shape: 'sphere', r: 0.08, pos: [r.x, r.y, 0], color: q >= 0 ? '#fde68a' : '#a5f3fc', emissive: '#facc15', glow: 0.6, trail: true, trailColor: '#fde68a', label: `q = ${p.qt} μC` });
        const vectors = [];
        // field-arrow grid (log length scale, exact direction)
        for (let gx = -3.5; gx <= 3.51; gx += 1) for (let gy = -3.5; gy <= 3.51; gy += 1) {
          if (chs.some(c => Math.hypot(gx - c.x, gy - c.y) < 0.35)) continue;
          const [ex, ey] = fieldAt(chs, [gx, gy]), e = Math.hypot(ex, ey);
          if (e < 1) continue;
          const L = Math.min(0.55, Math.max(0.08, 0.09 * Math.log10(e / 100)));
          vectors.push({ id: `g${gx}_${gy}`, from: [gx - ex / e * L / 2, gy - ey / e * L / 2, 0.02], vec: [ex / e * L, ey / e * L, 0], color: '#64748b', head: 0.4 });
        }
        if (r.E > 0) {
          const L = Math.min(1.2, Math.max(0.2, 0.2 * Math.log10(r.E / 100)));
          const sg = Math.sign(q) || 1;
          vectors.push({ id: 'Ft', from: [r.x, r.y, 0.05], vec: [sg * r.Ev[0] / r.E * L, sg * r.Ev[1] / r.E * L, 0], color: '#f472b6', label: `F = ${(Math.abs(q) * r.E).toExponential(2)} N` });
        }
        const sp = Math.hypot(r.vx, r.vy);
        if (sp > 1e-6) vectors.push({ id: 'vt', from: [r.x, r.y, 0.05], vec: [r.vx / sp * Math.min(1, 0.15 * sp), r.vy / sp * Math.min(1, 0.15 * sp), 0], color: '#4ade80', label: `v = ${sp.toFixed(2)} m/s` });
        return { bodies, vectors };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    const chs = charges(p), r0 = chs.map(c => Math.hypot(p.x0 - c.x, p.y0 - c.y));
    return [
      'E = Σ k·qᵢ/rᵢ² (vector sum),  V = Σ k·qᵢ/rᵢ (scalar sum)',
      `V(probe) = ${chs.map((c, i) => `k(${c.uc} μC)/${r0[i].toFixed(3)} m`).join(' + ') || '0'} = ${m.Vp.toFixed(0)} V`,
      `F = |q|·E = ${Math.abs(p.qt)} μC × ${m.E.toExponential(3)} N/C = ${m.F.toExponential(3)} N`,
      `KE + qV = ${m.KE.toExponential(4)} + ${m.U.toExponential(4)} = ${m.Etot.toExponential(4)} J (constant)`,
      `ΔKE = −qΔV:  ${m.KE.toExponential(3)} J = −(${p.qt} μC)(${(m.V - m.Vp).toFixed(0)} V)`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.final.nSrc >= 2 && r.t >= TMAX - 1e-6 && r.final.status === 0 && r.final.disp <= 0.02 && r.params.qt !== 0),
    ({ runs }) => runs.some(r => r.final.nSrc >= 2 && Math.abs(r.final.Vp) <= 500 && r.final.E0 >= 1000),
    ({ runs }) => runs.some(r => r.params.q2 === 0 && r.params.q3 === 0 && r.params.q1 * r.params.qt > 0 && Math.abs(r.params.x0 + 1) < 1e-9 && Math.abs(r.params.y0) < 1e-9 && r.final.status === 1 && Math.abs(r.final.v - 5) <= 0.15),
  ],
  evaluate(p) {
    return { vars: { q1: p.q1, q2: p.q2, q3: p.q3, x0: p.x0, y0: p.y0 }, answer: potentialAt(charges(p), [p.x0, p.y0]), unit: 'V', tol: 0.02 };
  },
};
