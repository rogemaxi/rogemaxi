// Lab 5 — Newton's Force Lab. A cart on a level track pushed by a constant applied force, with optional friction.
import { pushedBlock, C } from '../../physics/index.js';

const TRACK = 12; // m
const muS = mu => (mu > 0 ? mu + 0.05 : 0); // static coefficient slightly above kinetic (disclosed in assumptions)

export default {
  num: 5, unit: 5, sections: ['5.1', '5.2', '5.3', '5.5', '5.7'],
  text: {
    title: 'Newton’s Force Lab',
    question: 'How does a cart’s acceleration depend on the net force acting on it and on its mass?',
    params: { m: 'Cart mass', F: 'Applied force', mu: 'Kinetic friction coefficient μk' },
    graph: ['velocity v (m/s)', 'position x (m)', 'acceleration a (m/s²)', 'forces (N)'],
    series: { applied: 'applied', friction: 'friction', net: 'net' },
    measures: { t: 'Time', x: 'Position', v: 'Velocity', a: 'Acceleration', Fnet: 'Net force', f: 'Friction force', N: 'Normal force' },
    predict: {
      prompt: 'You will double the cart’s mass while keeping the applied force the same (no friction). What will happen to the acceleration?',
      choices: ['It doubles', 'It stays the same', 'It halves', 'It drops to zero'],
    },
    guided: [
      'Set μk = 0 and m = 4 kg. Run with F = 10 N, 20 N, and 40 N. Record each run. What happens to the acceleration each time the force doubles?',
      'Keep F = 20 N with no friction. Run with m = 2, 4, and 8 kg. Compare the slopes of the velocity–time graphs.',
      'Turn on friction (μk = 0.20) with m = 5 kg and F = 30 N. Use the measurements to show that a = (F − μk·m·g)/m.',
      'Switch to the conceptual view. Describe, without numbers, how the green net-force arrow compares to the acceleration in every run.',
    ],
    challenges: [
      'With friction off, choose a mass and force that give an acceleration of exactly 2.0 m/s² (±0.05). Run it.',
      'Record two runs with the same force and friction where the second mass is double the first. Show that the second acceleration is half the first.',
      'With μk = 0.20 and m = 5.0 kg, find the applied force that makes the net force exactly 10 N (±0.3 N). Run it.',
    ],
    evaluate: 'Before you run: for m = {m} kg, F = {F} N, and μk = {mu}, calculate the cart’s acceleration (use g = 9.8 m/s²). Enter 0 if the cart will not move.',
    honors: {
      prompt: 'Design a single run whose velocity–time graph lets you measure μk without reading the friction display. Explain the measurement and the equation you would use, then test it.',
      solution: 'Choose any F above the static-friction threshold. The slope of the v–t graph is a. From ΣF = m·a: F − μk·m·g = m·a, so μk = (F − m·a)/(m·g). Example: m = 5 kg, F = 30 N, measured a = 4.04 m/s² → μk = (30 − 20.2)/49 = 0.200.',
    },
    assumptions: [
      'The track is level and perfectly rigid; the cart is treated as a particle (no rotation of wheels).',
      'The applied force is constant and horizontal; air resistance is neglected.',
      'Friction follows the simple Coulomb model: kinetic friction μk·N opposes motion; static friction holds the cart until the applied force exceeds μs·N, with μs = μk + 0.05 in this lab.',
      'g = 9.8 m/s². The run stops when the cart reaches the end of the 12 m track or after 8 s.',
      'The thruster exhaust is a visual effect only; it does not represent a measured quantity.',
    ],
  },
  params: [
    { id: 'm', min: 1, max: 20, step: 0.5, value: 4, unit: 'kg' },
    { id: 'F', min: 0, max: 60, step: 0.5, value: 20, unit: 'N' },
    { id: 'mu', min: 0, max: 0.6, step: 0.05, value: 0, unit: '' },
  ],
  camera: { target: [3.5, 0.6, 0], dist: 8.5, free: [0.2, 0.32, 1], followId: 'cart' },
  view2d: { span: 15, cx: 5.5, cy: 1.5 },
  graph: {
    choices: [
      { label: 'velocity v (m/s)', y: ['v'], labels: ['v'], yLabel: 'v (m/s)' },
      { label: 'position x (m)', y: ['x'], labels: ['x'], yLabel: 'x (m)' },
      { label: 'acceleration a (m/s²)', y: ['a'], labels: ['a'], yLabel: 'a (m/s²)' },
      { label: 'forces (N)', y: ['F', 'f', 'Fnet'], labels: ['applied', 'friction', 'net'], yLabel: 'F (N)' },
    ],
  },
  recordKeys: ['a', 'Fnet', 'v', 'x'],
  decor: () => [
    { shape: 'ground', size: 60 },
    { shape: 'box', size: [TRACK + 1, 0.1, 1.4], pos: [TRACK / 2 - 0.5, 0.05, 0], color: '#334155' },
    ...Array.from({ length: 7 }, (_, i) => ({ shape: 'label', text: `${i * 2} m`, pos: [i * 2, 0.15, 0.9] })),
    { shape: 'box', size: [0.2, 1.2, 1.4], pos: [TRACK, 0.6, 0], color: '#f87171' },
  ],
  create(p) {
    const muSt = muS(p.mu);
    const s = { t: 0, x: 0, v: 0, a: 0, f: 0, N: p.m * C.g, done: false, events: [], moving: false };
    const forces = () => {
      if (!s.moving && s.v === 0) {
        const r = pushedBlock(p.m, p.F, muSt, p.mu);
        return { a: r.moving ? r.a : 0, f: r.moving ? r.friction : -p.F, moving: r.moving };
      }
      const f = -p.mu * p.m * C.g;
      return { a: (p.F + f) / p.m, f, moving: true };
    };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        const fr = forces(); s.a = fr.a; s.f = fr.f; s.moving = fr.moving;
        // exact update for constant acceleration over dt
        s.x += s.v * dt + 0.5 * s.a * dt * dt; s.v += s.a * dt; s.t += dt;
        if (s.v < 0) s.v = 0;
        if (s.x >= TRACK - 0.45) { s.x = TRACK - 0.45; s.done = true; s.events.push({ type: 'impact', pos: [TRACK - 0.2, 0.6, 0], strength: Math.min(2, s.v / 6), normal: 'x' }); }
        if (s.t >= 8) s.done = true;
        if (s.moving && p.F > 0 && Math.random() < 0.15) s.events.push({ type: 'spark', pos: [s.x - 0.55, 0.55, 0], strength: 0.25, speed: 0.6, color: '#fb923c', life: 0.5 });
      },
      measures() {
        if (s.t === 0) { const fr = forces(); s.a = fr.a; s.f = fr.f; }
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'x', label: 'Position', value: s.x, unit: 'm', ref: TRACK },
          { id: 'v', label: 'Velocity', value: s.v, unit: 'm/s', ref: 15 },
          { id: 'a', label: 'Acceleration', value: s.a, unit: 'm/s²', ref: 10 },
          { id: 'F', label: 'Applied force', value: p.F, unit: 'N', ref: 60, hidden: true },
          { id: 'f', label: 'Friction force', value: s.f, unit: 'N', ref: 60 },
          { id: 'Fnet', label: 'Net force', value: p.F + s.f, unit: 'N', ref: 60 },
          { id: 'N', label: 'Normal force', value: p.m * C.g, unit: 'N', ref: 200 },
        ];
      },
      energy() { return [{ label: 'KE', value: 0.5 * p.m * s.v * s.v, color: '#fbbf24' }, { label: 'Work by F', value: p.F * s.x, color: '#4ade80' }, { label: 'Thermal (friction)', value: -s.f * s.x * (s.moving ? 1 : 0), color: '#f87171' }]; },
      scene() {
        const side = 0.5 + Math.cbrt(p.m) * 0.25, y = 0.1 + side / 2, k = 0.05; // force arrow scale: 0.05 m per N
        return {
          bodies: [
            { id: 'cart', shape: 'box', size: [side * 1.4, side, 1], pos: [s.x, y, 0], color: '#fbbf24', metal: 0.4, trail: false, label: `${p.m} kg` },
            { id: 'w1', shape: 'cylinder', r: 0.12, h: 1.1, pos: [s.x - side * 0.45, 0.22, 0], rot: [Math.PI / 2, -s.x / 0.12, 0], color: '#1e293b' },
            { id: 'w2', shape: 'cylinder', r: 0.12, h: 1.1, pos: [s.x + side * 0.45, 0.22, 0], rot: [Math.PI / 2, -s.x / 0.12, 0], color: '#1e293b' },
            { id: 'thr', shape: 'cone', r: 0.18, h: 0.4, pos: [s.x - side * 0.7 - 0.15, y, 0], rot: [0, 0, Math.PI / 2], color: '#94a3b8', emissive: p.F > 0 ? '#fb923c' : null, glow: p.F / 60 },
          ],
          vectors: [
            { id: 'F', from: [s.x + side * 0.7, y + 0.1, 0.55], vec: [p.F * k, 0, 0], color: '#fbbf24', label: `F = ${p.F.toFixed(1)} N` },
            { id: 'f', from: [s.x - side * 0.7, 0.2, 0.55], vec: [s.f * k, 0, 0], color: '#f87171', label: s.f ? `f = ${Math.abs(s.f).toFixed(1)} N` : '' },
            { id: 'net', from: [s.x, y + side / 2 + 0.6, 0], vec: [(p.F + s.f) * k, 0, 0], color: '#4ade80', label: `ΣF = ${(p.F + s.f).toFixed(1)} N` },
            { id: 'W', from: [s.x, y, 0.55], vec: [0, -Math.min(2.5, p.m * C.g * 0.012), 0], color: '#7dd3fc', label: 'mg' },
            { id: 'Nf', from: [s.x, y, 0.55], vec: [0, Math.min(2.5, p.m * C.g * 0.012), 0], color: '#a5b4fc', label: 'N' },
          ],
        };
      },
    };
  },
  equations(p, model, view) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    return [
      'ΣF = F − f = m·a',
      `f = μk·m·g = ${p.mu} × ${p.m} × 9.8 = ${(p.mu * p.m * 9.8).toFixed(2)} N`,
      `ΣF = ${p.F} − ${Math.abs(m.f).toFixed(2)} = ${m.Fnet.toFixed(2)} N`,
      `a = ΣF/m = ${m.Fnet.toFixed(2)} / ${p.m} = ${m.a.toFixed(3)} m/s²`,
    ];
  },
  challenges: [
    ({ params: p, runs }) => p.mu === 0 && Math.abs(p.F / p.m - 2) <= 0.05 && runs.some(r => r.params.mu === 0 && Math.abs(r.final.a - 2) <= 0.05),
    ({ runs }) => runs.some(r1 => runs.some(r2 => r1 !== r2 && r1.params.F === r2.params.F && r1.params.mu === r2.params.mu && Math.abs(r2.params.m / r1.params.m - 2) < 1e-9 && r1.final.a > 0 && Math.abs(r2.final.a / r1.final.a - 0.5) < 0.03)),
    ({ runs }) => runs.some(r => r.params.mu === 0.2 && r.params.m === 5 && Math.abs(r.final.Fnet - 10) <= 0.3 && r.final.v > 0),
  ],
  evaluate(p) {
    const r = pushedBlock(p.m, p.F, muS(p.mu), p.mu);
    return { vars: { m: p.m, F: p.F, mu: p.mu }, answer: r.moving ? r.a : 0, unit: 'm/s²', tol: 0.02 };
  },
};
