// Lab 3 — Motion Simulator. Two cars on parallel straight lanes, each with constant acceleration.
// The state is advanced with the exact constant-acceleration update, so x(t), v(t) match the kinematic
// equations to rounding error. Meeting times and turnaround points are found exactly inside each step.
import { kin } from '../../physics/index.js';

const T_END = 12; // s
const LANE = { A: 1.6, B: -1.6 }; // scene z of each lane

// Smallest root τ in (lo, hi] of c0 + c1·τ + ½·c2·τ² = 0, or null.
export function firstRoot(c0, c1, c2, lo, hi) {
  const roots = [];
  if (Math.abs(c2) < 1e-14) { if (Math.abs(c1) > 1e-14) roots.push(-c0 / c1); }
  else {
    let d = c1 * c1 - 2 * c2 * c0;
    if (d < 0 && d > -1e-9 * (c1 * c1 + Math.abs(2 * c2 * c0))) d = 0; // tangent touch lost to rounding
    if (d >= 0) { const q = Math.sqrt(d); roots.push((-c1 - q) / c2, (-c1 + q) / c2); }
  }
  const ok = roots.filter(r => r > lo && r <= hi).sort((a, b) => a - b);
  return ok.length ? ok[0] : null;
}

export default {
  num: 3, unit: 3, sections: ['3.1', '3.2', '3.3', '3.4', '3.5', '3.7'],
  text: {
    title: 'Motion Simulator',
    question: 'How are a car’s position–time, velocity–time, and acceleration–time graphs related, and how can they tell us when and where two cars meet?',
    params: { x0A: 'Car A start position', v0A: 'Car A initial velocity', aA: 'Car A acceleration', x0B: 'Car B start position', v0B: 'Car B initial velocity', aB: 'Car B acceleration' },
    graph: ['position x (m)', 'velocity v (m/s)', 'acceleration a (m/s²)', 'gap xB − xA (m)'],
    series: { xA: 'car A', xB: 'car B', vA: 'car A', vB: 'car B', aA: 'car A', aB: 'car B', gap: 'gap' },
    measures: { t: 'Time', xA: 'Car A position', vA: 'Car A velocity', aA: 'Car A acceleration', xB: 'Car B position', vB: 'Car B velocity', aB: 'Car B acceleration', gap: 'Gap xB − xA', tMeet: 'First meeting time', xMeet: 'Meeting position', xMaxA: 'Car A farthest position', dA: 'Car A distance travelled' },
    predict: {
      prompt: 'Car A starts from rest with a = 2 m/s². At the same instant car B passes it at a constant 10 m/s. When does car A catch up with car B?',
      choices: ['Never — B is always ahead', 'At t = 5 s, when their speeds are equal', 'At t = 10 s', 'At t = 20 s'],
    },
    guided: [
      'Run the default set-up. Read the v–t graph: at what time are the speeds equal? Read the x–t graph: at what time do the cars meet? Explain why these are different times.',
      'Use the v–t graph of car A to find its displacement after 6 s as the area under the line. Check it against the position measurement.',
      'Give car A v₀ = 12 m/s and a = −3 m/s². Describe its x–t graph (shape, turning point) and its v–t graph (where it crosses zero). What is the acceleration at the instant v = 0?',
      'Set car B 30 m ahead at rest with a = 1 m/s², and car A at 0 m with 8 m/s and a = 0. Do they meet once, twice, or never? Use the gap graph.',
      'Compare distance travelled with displacement for a run in which car A turns around.',
    ],
    challenges: [
      'Set the cars up so that they first meet at exactly t = 6.0 s (± 0.05 s). Record the run.',
      'Give car A a positive initial velocity and a negative acceleration so that it turns around and is back at (or behind) its starting position by the end of the 12 s run.',
      'Car A starts with v₀ = 20 m/s. Choose its acceleration so that its turnaround point is exactly 40 m (± 0.5 m) beyond its start. Run it.',
    ],
    evaluate: 'Before you run: car A starts at x = {x0A} m with v = {v0A} m/s and a constant acceleration of {aA} m/s². Calculate its position at t = 5.0 s.',
    honors: {
      prompt: 'Write the gap Δx(t) = xB − xA as a quadratic in t. Use it to find a condition on the starting gap, the relative velocity and the relative acceleration for the cars to meet exactly once after t = 0. Test a set-up that just touches (one meeting).',
      solution: 'Δx(t) = Δx₀ + Δv·t + ½Δa·t². A single tangent meeting needs the discriminant Δv² − 2·Δa·Δx₀ = 0 with the root t = −Δv/Δa > 0. Example: B 25 m ahead at rest, a_B = 2 m/s²; A at 10 m/s, a_A = 0: Δx₀ = 25, Δv = −10, Δa = 2 → 100 − 100 = 0, so A just reaches B at t = 5 s, x = 50 m.',
    },
    assumptions: [
      'Each car is a particle moving along a straight lane; the lanes are side by side, so the cars can pass without colliding.',
      'Each acceleration is constant for the whole 12 s run (a car with negative acceleration does not stop; it reverses).',
      'Positions are measured from the same zero line along +x; velocities and accelerations are positive toward +x.',
      'The state is advanced with the exact constant-acceleration equations every 1/240 s; meeting times and turnaround points are solved exactly within each step.',
      'The flash when the cars meet and the once-per-second dots are visual aids; wheels and car shapes have no physical role.',
    ],
  },
  params: [
    { id: 'x0A', min: -50, max: 50, step: 1, value: 0, unit: 'm' },
    { id: 'v0A', min: -20, max: 25, step: 0.5, value: 0, unit: 'm/s' },
    { id: 'aA', min: -6, max: 6, step: 0.1, value: 2, unit: 'm/s²' },
    { id: 'x0B', min: -50, max: 50, step: 1, value: 0, unit: 'm' },
    { id: 'v0B', min: -20, max: 25, step: 0.5, value: 10, unit: 'm/s' },
    { id: 'aB', min: -6, max: 6, step: 0.1, value: 0, unit: 'm/s²' },
  ],
  camera: { target: [50, 0, 0], dist: 85, free: [0.15, 0.55, 1], followId: 'carA' },
  view2d: { plane: 'xz', span: 180, cx: 60, cy: 0 },
  graph: {
    choices: [
      { label: 'position x (m)', y: ['xA', 'xB'], labels: ['xA', 'xB'], yLabel: 'x (m)' },
      { label: 'velocity v (m/s)', y: ['vA', 'vB'], labels: ['vA', 'vB'], yLabel: 'v (m/s)' },
      { label: 'acceleration a (m/s²)', y: ['aA', 'aB'], labels: ['aA', 'aB'], yLabel: 'a (m/s²)' },
      { label: 'gap xB − xA (m)', y: ['gap'], labels: ['gap'], yLabel: 'Δx (m)' },
    ],
  },
  recordKeys: ['xA', 'vA', 'xB', 'vB', 'tMeet', 'xMeet', 'xMaxA'],
  decor: () => [
    { shape: 'ground', size: 1000, divisions: 100 },
    { shape: 'box', size: [600, 0.06, 2.6], pos: [150, 0.03, LANE.A], color: '#334155' },
    { shape: 'box', size: [600, 0.06, 2.6], pos: [150, 0.03, LANE.B], color: '#334155' },
    { shape: 'line', pts: [[-150, 0.08, 0], [450, 0.08, 0]], color: '#facc15' },
    { shape: 'box', size: [0.4, 0.08, 6], pos: [0, 0.05, 0], color: '#f8fafc' },
    ...Array.from({ length: 21 }, (_, i) => ({ shape: 'label', text: `${(i - 5) * 20} m`, pos: [(i - 5) * 20, 0.2, 4.5], color: '#94a3b8' })),
    ...Array.from({ length: 21 }, (_, i) => ({ shape: 'line', pts: [[(i - 5) * 20, 0.07, 3.2], [(i - 5) * 20, 0.07, -3.2]], color: '#475569' })),
  ],
  create(p) {
    const car = (x0, v0, a) => ({ x: x0, v: v0, a, x0, dist: 0, xMax: x0, dots: [[x0]] });
    const A = car(p.x0A, p.v0A, p.aA), B = car(p.x0B, p.v0B, p.aB);
    const s = { t: 0, tMeet: NaN, xMeet: NaN, meets: 0, lastMeet: -Infinity, done: false, events: [] };
    const advance = (c, h) => {
      // turnaround inside the step: exact maximum / distance bookkeeping
      const tau = c.a !== 0 ? -c.v / c.a : null;
      if (tau != null && tau > 0 && tau < h) {
        const xt = kin.x(c.x, c.v, c.a, tau);
        c.dist += Math.abs(xt - c.x) + Math.abs(kin.x(c.x, c.v, c.a, h) - xt);
        c.xMax = Math.max(c.xMax, xt);
      } else c.dist += Math.abs(kin.x(c.x, c.v, c.a, h) - c.x);
      c.x = kin.x(c.x, c.v, c.a, h); c.v = kin.v(c.v, c.a, h); c.xMax = Math.max(c.xMax, c.x);
    };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        const h = Math.min(dt, T_END - s.t);
        // roots on the step boundaries are accepted once (rounding can put them a hair either side)
        let tau = firstRoot(B.x - A.x, B.v - A.v, B.a - A.a, -1e-9, h + 1e-9);
        if (tau != null && (s.t + tau < 1e-9 || s.t + tau - s.lastMeet < 1e-6)) tau = firstRoot(B.x - A.x, B.v - A.v, B.a - A.a, tau + 1e-9, h + 1e-9);
        if (tau == null && B.a !== A.a) { // tangent touch: the gap's extremum inside the step is within 1 µm of zero
          const g0 = B.x - A.x, dv = B.v - A.v, da = B.a - A.a, te = -dv / da;
          if (te >= 0 && te <= h && Math.abs(g0 + dv * te + 0.5 * da * te * te) < 1e-6) tau = te;
        }
        if (tau != null && s.t + tau >= 1e-9 && s.t + tau - s.lastMeet >= 1e-6) {
          tau = Math.max(0, tau); s.lastMeet = s.t + tau; s.meets++;
          if (!Number.isFinite(s.tMeet)) { s.tMeet = s.t + tau; s.xMeet = kin.x(A.x, A.v, A.a, tau); }
          s.events.push({ type: 'impact', pos: [kin.x(A.x, A.v, A.a, tau), 1, 0], strength: 0.9, normal: 'x', color: '#fbbf24' });
        }
        const before = Math.floor(s.t + 1e-9);
        advance(A, h); advance(B, h); s.t += h;
        if (Math.floor(s.t + 1e-9) > before) { A.dots.push([A.x]); B.dots.push([B.x]); }
        if (s.t >= T_END - 1e-9) s.done = true;
      },
      measures() {
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'xA', label: 'Car A position', value: A.x, unit: 'm', ref: 200 },
          { id: 'vA', label: 'Car A velocity', value: A.v, unit: 'm/s', ref: 40 },
          { id: 'aA', label: 'Car A acceleration', value: A.a, unit: 'm/s²', ref: 6 },
          { id: 'xB', label: 'Car B position', value: B.x, unit: 'm', ref: 200 },
          { id: 'vB', label: 'Car B velocity', value: B.v, unit: 'm/s', ref: 40 },
          { id: 'aB', label: 'Car B acceleration', value: B.a, unit: 'm/s²', ref: 6 },
          { id: 'gap', label: 'Gap xB − xA', value: B.x - A.x, unit: 'm', ref: 100 },
          { id: 'tMeet', label: 'First meeting time', value: s.tMeet, unit: 's', ref: T_END },
          { id: 'xMeet', label: 'Meeting position', value: s.xMeet, unit: 'm', ref: 200 },
          { id: 'xMaxA', label: 'Car A farthest position', value: A.xMax, unit: 'm', ref: 200 },
          { id: 'dA', label: 'Car A distance travelled', value: A.dist, unit: 'm', ref: 200 },
          { id: 'meets', label: 'Meetings', value: s.meets, unit: '', hidden: true },
        ];
      },
      energy() { return []; },
      scene() {
        const bodies = [], vectors = [];
        for (const [id, c, col, z] of [['A', A, '#f87171', LANE.A], ['B', B, '#60a5fa', LANE.B]]) {
          bodies.push(
            { id: 'car' + id, shape: 'box', size: [4, 1.2, 2], pos: [c.x, 0.9, z], color: col, metal: 0.5, label: `${id}: ${c.v.toFixed(1)} m/s` },
            { id: 'cab' + id, shape: 'box', size: [2, 0.8, 1.8], pos: [c.x - 0.3, 1.9, z], color: '#cbd5e1', opacity: 0.8 },
            { id: 'w1' + id, shape: 'cylinder', r: 0.4, h: 2.2, pos: [c.x - 1.3, 0.4, z], rot: [Math.PI / 2, 0, 0], color: '#111827' },
            { id: 'w2' + id, shape: 'cylinder', r: 0.4, h: 2.2, pos: [c.x + 1.3, 0.4, z], rot: [Math.PI / 2, 0, 0], color: '#111827' },
            ...c.dots.map((d, i) => ({ id: `dot${id}${i}`, shape: 'sphere', r: 0.25, pos: [d[0], 0.15, z + (z > 0 ? 1.6 : -1.6)], color: col })),
          );
          vectors.push(
            { id: 'v' + id, from: [c.x, 3, z], vec: [c.v * 0.5, 0, 0], color: '#4ade80', label: `v = ${c.v.toFixed(1)}` },
            { id: 'a' + id, from: [c.x, 4.2, z], vec: [c.a * 1.5, 0, 0], color: '#fbbf24', label: c.a ? `a = ${c.a}` : '' },
          );
        }
        return { bodies, vectors };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value])), t = m.t.toFixed(2), f = x => x.toFixed(2);
    return [
      'x = x₀ + v₀t + ½at²,   v = v₀ + at',
      `A: x = ${p.x0A} + ${p.v0A}(${t}) + ½(${p.aA})(${t})² = ${f(m.xA)} m;  v = ${p.v0A} + ${p.aA}(${t}) = ${f(m.vA)} m/s`,
      `B: x = ${p.x0B} + ${p.v0B}(${t}) + ½(${p.aB})(${t})² = ${f(m.xB)} m;  v = ${p.v0B} + ${p.aB}(${t}) = ${f(m.vB)} m/s`,
      `meet when Δx₀ + Δv·t + ½Δa·t² = 0:  ${p.x0B - p.x0A} + ${f(p.v0B - p.v0A)}t + ½(${f(p.aB - p.aA)})t² = 0  →  t = ${Number.isFinite(m.tMeet) ? f(m.tMeet) + ' s' : 'not yet'}`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => Math.abs(r.final.tMeet - 6) <= 0.05),
    ({ runs }) => runs.some(r => r.params.v0A > 0 && r.params.aA < 0 && r.final.vA < 0 && r.final.xA <= r.params.x0A + 0.05),
    ({ runs }) => runs.some(r => r.params.v0A === 20 && r.params.aA < 0 && Math.abs(r.final.xMaxA - r.params.x0A - 40) <= 0.5),
  ],
  evaluate(p) {
    return { vars: { x0A: p.x0A, v0A: p.v0A, aA: p.aA }, answer: kin.x(p.x0A, p.v0A, p.aA, 5), unit: 'm', tol: 0.02 };
  },
};
