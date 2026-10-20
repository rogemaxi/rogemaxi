// Lab 8 — Collision Laboratory. Two gliders on a frictionless air track: collisions with a coefficient of
// restitution e (1 = elastic, 0 < e < 1 = inelastic, 0 = perfectly inelastic), or an explosion / recoil release.
import { collide1D, C } from '../../physics/index.js';

const TRACK = 10;          // m
const W = 0.4;             // glider length, m
const X1 = 3, X2 = 5.5;    // starting centres (collision mode), m
const RELEASE_T = 0.5;     // explosion mode: the compressed spring is released at this time, s
const TMAX = 15;
const mu = (m1, m2) => m1 * m2 / (m1 + m2);

// Velocities after a release of energy Ex between two gliders moving together at V (momentum conserved).
export function explode(m1, m2, V, Ex) {
  const u = Math.sqrt(2 * Ex / mu(m1, m2)), M = m1 + m2; // relative separation speed
  return [V - m2 * u / M, V + m1 * u / M];
}
// Final velocity of each glider predicted from the parameters (no collision if they never close).
export function outcome(p) {
  if (p.mode === 'explosion') return explode(p.m1, p.m2, p.v1, p.Ex);
  return p.v1 > p.v2 ? collide1D(p.m1, p.v1, p.m2, p.v2, p.e) : [p.v1, p.v2];
}

export default {
  num: 8, unit: 7, sections: ['7.1', '7.3', '7.4', '7.5', '7.6'],
  text: {
    title: 'Collision Laboratory',
    question: 'In a collision or an explosion, which quantities are conserved — momentum, kinetic energy, or both?',
    params: { mode: 'Event', m1: 'Glider 1 mass m₁', m2: 'Glider 2 mass m₂', v1: 'Glider 1 initial velocity', v2: 'Glider 2 initial velocity', e: 'Coefficient of restitution e', Ex: 'Spring energy released (explosion)' },
    options: { collision: 'Collision', explosion: 'Explosion / recoil (start together)' },
    graph: ['velocities (m/s)', 'momentum (kg·m/s)', 'kinetic energy (J)', 'positions (m)'],
    series: { v1: 'glider 1', v2: 'glider 2', p1: 'glider 1', p2: 'glider 2', p: 'total', K1: 'glider 1', K2: 'glider 2', K: 'total', x1: 'glider 1', x2: 'glider 2' },
    measures: { t: 'Time', v1: 'Velocity 1', v2: 'Velocity 2', p: 'Total momentum', K: 'Total KE', pBefore: 'Momentum before', pAfter: 'Momentum after', KBefore: 'KE before', KAfter: 'KE after', eMeas: 'Measured e' },
    predict: {
      prompt: 'Two 0.50 kg gliders. Glider 1 moves at 0.60 m/s toward glider 2, which is at rest. The collision is elastic (e = 1). What happens after the collision?',
      choices: ['Both move together at 0.30 m/s', 'Glider 1 stops and glider 2 moves off at 0.60 m/s', 'Glider 1 bounces back at 0.60 m/s and glider 2 stays still', 'Both gliders stop'],
    },
    guided: [
      'Run the default elastic collision. Compare the total momentum and total KE before and after (use the momentum and KE graphs).',
      'Set e = 0 (perfectly inelastic). Repeat with the same masses and speeds. Which conserved quantity survives? What fraction of the KE is lost? Compare with m₂/(m₁ + m₂).',
      'Elastic, with m₁ = 0.20 kg hitting m₂ = 1.00 kg at rest, then the reverse (heavy into light). Describe each outcome and check it with v₁′ = (m₁ − m₂)v₁/(m₁ + m₂).',
      'Try e = 0.5. Use the velocities to calculate e = (v₂′ − v₁′)/(v₁ − v₂) and compare with the measured value.',
      'Switch to explosion mode with both gliders at rest. Release 2 J with m₁ = 0.5 kg and m₂ = 1.0 kg. Show that the total momentum stays zero and find the ratio of speeds.',
    ],
    challenges: [
      'Perfectly inelastic (e = 0): choose masses and velocities so both gliders are at rest (|v| ≤ 0.01 m/s) after they stick together, with at least one glider moving at the start.',
      'Glider 2 starts at rest: choose the masses and an e below 1 so that glider 1 stops dead (|v₁′| ≤ 0.01 m/s) after the collision.',
      'Explosion from rest: make glider 2 move off at exactly twice the speed of glider 1 (ratio 2.00 ± 0.02).',
    ],
    evaluate: 'Before you run: m₁ = {m1} kg starts at {v1} m/s and m₂ = {m2} kg at {v2} m/s (e = {e}; in explosion mode they start together and {Ex} J is released). Calculate glider 1’s final velocity (positive = to the right).',
    honors: {
      prompt: 'Show that for any 1-D collision with restitution e the fraction of kinetic energy lost is (1 − e²)·μ(v₁ − v₂)²/(2K), where μ = m₁m₂/(m₁ + m₂) is the reduced mass and K the initial KE. Test it with a run.',
      solution: 'Write the KE as the centre-of-mass part ½(m₁ + m₂)V² (unchanged, because momentum is conserved) plus the relative part ½μ(v₁ − v₂)². Restitution multiplies the relative velocity by −e, so the relative KE becomes ½μe²(v₁ − v₂)² and the loss is ½μ(1 − e²)(v₁ − v₂)². Example: m₁ = m₂ = 0.5 kg, v₁ = 0.6, v₂ = 0, e = 0.5: μ = 0.25, loss = ½ × 0.25 × 0.75 × 0.36 = 0.03375 J of K = 0.09 J (37.5%), matching KE before − KE after in the run.',
    },
    assumptions: [
      'The air track is level and frictionless; the gliders move in one dimension and air drag is neglected.',
      'The collision is instantaneous: momentum is exactly conserved and the relative velocity is reversed and multiplied by e (Newton’s restitution law). With e = 0 the gliders stick together.',
      'Contact is detected exactly (the step is split at the moment the gliders touch). External forces are absent, so the total momentum before equals the total momentum after.',
      'In explosion mode the gliders start touching with a common velocity (glider 1’s setting) and a massless compressed spring releases the chosen energy instantly at t = 0.5 s; v₂ and e are not used.',
      'KE lost in a collision is shown as thermal/deformation energy. The flash at impact is a visual effect only.',
      'The run ends when a glider reaches an end of the 10 m track or after 15 s.',
    ],
  },
  params: [
    { id: 'mode', value: 'collision', options: [{ value: 'collision', label: 'Collision' }, { value: 'explosion', label: 'Explosion / recoil (start together)' }] },
    { id: 'm1', min: 0.1, max: 2, step: 0.05, value: 0.5, unit: 'kg' },
    { id: 'm2', min: 0.1, max: 2, step: 0.05, value: 0.5, unit: 'kg' },
    { id: 'v1', min: -2, max: 2, step: 0.05, value: 0.6, unit: 'm/s' },
    { id: 'v2', min: -2, max: 2, step: 0.05, value: 0, unit: 'm/s' },
    { id: 'e', min: 0, max: 1, step: 0.05, value: 1, unit: '' },
    { id: 'Ex', min: 0, max: 5, step: 0.1, value: 1, unit: 'J' },
  ],
  camera: { target: [5, 0.4, 0], dist: 9, free: [0.15, 0.35, 1] },
  view2d: { span: 11, cx: 5, cy: 0.8 },
  graph: {
    choices: [
      { label: 'velocities (m/s)', y: ['v1', 'v2'], labels: ['v1', 'v2'], yLabel: 'v (m/s)' },
      { label: 'momentum (kg·m/s)', y: ['p1', 'p2', 'p'], labels: ['p1', 'p2', 'p'], yLabel: 'p (kg·m/s)' },
      { label: 'kinetic energy (J)', y: ['K1', 'K2', 'K'], labels: ['K1', 'K2', 'K'], yLabel: 'KE (J)' },
      { label: 'positions (m)', y: ['x1', 'x2'], labels: ['x1', 'x2'], yLabel: 'x (m)' },
    ],
  },
  recordKeys: ['v1', 'v2', 'pBefore', 'pAfter', 'KBefore', 'KAfter', 'eMeas'],
  decor: () => [
    { shape: 'ground', size: 40, y: -0.6 },
    { shape: 'box', size: [TRACK + 0.4, 0.12, 0.35], pos: [TRACK / 2, 0, 0], color: '#94a3b8', metal: 0.6 },
    { shape: 'box', size: [TRACK + 0.4, 0.5, 0.2], pos: [TRACK / 2, -0.3, 0], color: '#334155' },
    { shape: 'box', size: [0.12, 0.4, 0.5], pos: [-0.2, 0.15, 0], color: '#f87171' },
    { shape: 'box', size: [0.12, 0.4, 0.5], pos: [TRACK + 0.2, 0.15, 0], color: '#f87171' },
    ...Array.from({ length: 6 }, (_, i) => ({ shape: 'label', text: `${i * 2} m`, pos: [i * 2, -0.05, 0.4] })),
  ],
  create(p) {
    const ex = p.mode === 'explosion';
    const s = ex
      ? { t: 0, x1: TRACK / 2 - W / 2, x2: TRACK / 2 + W / 2, v1: p.v1, v2: p.v1 }
      : { t: 0, x1: X1, x2: X2, v1: p.v1, v2: p.v2 };
    Object.assign(s, { done: false, events: [], hit: false, stuck: ex, Q: 0, store: ex ? p.Ex : 0 });
    const P = () => p.m1 * s.v1 + p.m2 * s.v2, K = () => 0.5 * p.m1 * s.v1 * s.v1 + 0.5 * p.m2 * s.v2 * s.v2;
    const before = { p: P(), K: K(), v1: s.v1, v2: s.v2 };
    const after = {};
    const move = h => { s.x1 += s.v1 * h; s.x2 += s.v2 * h; s.t += h; };
    const contact = () => [(s.x1 + s.x2) / 2, 0.3, 0];
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        if (s.done) return;
        let rem = dt;
        if (ex && !s.hit && s.t + rem >= RELEASE_T - 1e-12) {
          const tau = Math.max(0, RELEASE_T - s.t); move(tau); rem -= tau;
          [s.v1, s.v2] = explode(p.m1, p.m2, s.v1, p.Ex); s.store = 0; s.hit = true; s.stuck = false;
          Object.assign(after, { p: P(), K: K(), v1: s.v1, v2: s.v2 });
          s.events.push({ type: 'burst', pos: contact(), strength: Math.min(2, 0.4 + p.Ex / 3), speed: 0.8, color: '#fbbf24', life: 0.6 });
        } else if (!ex && !s.hit) {
          const gap = s.x2 - s.x1 - W, close = s.v1 - s.v2;
          if (close > 1e-12 && gap - close * rem <= 0) {
            const tau = Math.max(0, gap / close); move(tau); rem -= tau;
            const K0 = K();
            [s.v1, s.v2] = collide1D(p.m1, s.v1, p.m2, s.v2, p.e);
            if (p.e === 0) s.v2 = s.v1; // stick: identical velocities (avoid round-off separation)
            s.Q = K0 - K(); s.hit = true; s.stuck = p.e === 0;
            Object.assign(after, { p: P(), K: K(), v1: s.v1, v2: s.v2 });
            s.events.push({ type: 'impact', pos: contact(), strength: Math.min(2, 0.3 + Math.abs(close)), normal: 'x', color: p.e > 0.5 ? '#7dd3fc' : '#fb923c' });
          }
        }
        move(rem);
        const lo = Math.min(s.x1, s.x2) - W / 2, hi = Math.max(s.x1, s.x2) + W / 2;
        if (lo <= 0 || hi >= TRACK || s.t >= TMAX - 1e-9) s.done = true;
      },
      measures() {
        const a = s.hit ? after : { p: P(), K: K(), v1: s.v1, v2: s.v2 };
        const dv = before.v1 - before.v2;
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'x1', label: 'Position 1', value: s.x1, unit: 'm', hidden: true },
          { id: 'x2', label: 'Position 2', value: s.x2, unit: 'm', hidden: true },
          { id: 'v1', label: 'Velocity 1', value: s.v1, unit: 'm/s', ref: 2 },
          { id: 'v2', label: 'Velocity 2', value: s.v2, unit: 'm/s', ref: 2 },
          { id: 'p1', label: 'Momentum 1', value: p.m1 * s.v1, unit: 'kg·m/s', hidden: true },
          { id: 'p2', label: 'Momentum 2', value: p.m2 * s.v2, unit: 'kg·m/s', hidden: true },
          { id: 'p', label: 'Total momentum', value: P(), unit: 'kg·m/s', ref: 4 },
          { id: 'K1', label: 'KE 1', value: 0.5 * p.m1 * s.v1 * s.v1, unit: 'J', hidden: true },
          { id: 'K2', label: 'KE 2', value: 0.5 * p.m2 * s.v2 * s.v2, unit: 'J', hidden: true },
          { id: 'K', label: 'Total KE', value: K(), unit: 'J', ref: 4 },
          { id: 'pBefore', label: 'Momentum before', value: before.p, unit: 'kg·m/s', ref: 4 },
          { id: 'pAfter', label: 'Momentum after', value: a.p, unit: 'kg·m/s', ref: 4 },
          { id: 'KBefore', label: 'KE before', value: before.K, unit: 'J', ref: 4 },
          { id: 'KAfter', label: 'KE after', value: a.K, unit: 'J', ref: 4 },
          { id: 'eMeas', label: 'Measured e', value: !ex && s.hit && Math.abs(dv) > 1e-12 ? (a.v2 - a.v1) / dv : 0, unit: '', ref: 1 },
          { id: 'hit', label: 'Collided / released', value: s.hit ? 1 : 0, unit: '', hidden: true },
        ];
      },
      energy() {
        const k1 = 0.5 * p.m1 * s.v1 * s.v1, k2 = 0.5 * p.m2 * s.v2 * s.v2;
        return [
          { label: 'KE glider 1', value: k1, color: '#fbbf24' },
          { label: 'KE glider 2', value: k2, color: '#7dd3fc' },
          ex ? { label: 'Spring (stored)', value: s.store, color: '#c084fc' } : { label: 'Thermal / deformation', value: s.Q, color: '#f87171' },
          { label: 'Total', value: k1 + k2 + (ex ? s.store : s.Q), color: '#4ade80' },
        ];
      },
      scene() {
        const hgt = m => 0.18 + 0.12 * Math.sqrt(m), kv = 0.8, kp = 1.2;
        const g1 = hgt(p.m1), g2 = hgt(p.m2), y = 0.06;
        const bodies = [
          { id: 'g1', shape: 'box', size: [W, g1, 0.42], pos: [s.x1, y + g1 / 2, 0], color: '#fbbf24', metal: 0.5, label: `${p.m1} kg` },
          { id: 'g2', shape: 'box', size: [W, g2, 0.42], pos: [s.x2, y + g2 / 2, 0], color: '#7dd3fc', metal: 0.5, label: `${p.m2} kg` },
          { id: 'f1', shape: 'box', size: [0.03, 0.18, 0.12], pos: [s.x1, y + g1 + 0.09, 0], color: '#e2e8f0' },
          { id: 'f2', shape: 'box', size: [0.03, 0.18, 0.12], pos: [s.x2, y + g2 + 0.09, 0], color: '#e2e8f0' },
          // bumper pads: springy (blue) when e is large, putty (orange) when e is small
          { id: 'b1', shape: 'box', size: [0.04, g1 * 0.6, 0.3], pos: [s.x1 + W / 2 - 0.02, y + g1 / 2, 0], color: p.e > 0.5 || ex ? '#60a5fa' : '#fb923c' },
          { id: 'b2', shape: 'box', size: [0.04, g2 * 0.6, 0.3], pos: [s.x2 - W / 2 + 0.02, y + g2 / 2, 0], color: p.e > 0.5 || ex ? '#60a5fa' : '#fb923c' },
        ];
        const lines = [];
        if (ex && !s.hit) lines.push({ id: 'spring', pts: Array.from({ length: 9 }, (_, i) => [s.x1 + W / 2 - 0.1 + 0.2 * i / 8, y + 0.1 + (i % 2 ? 0.05 : -0.05) * (i % 8 ? 1 : 0), 0.24]), color: '#c084fc' });
        return {
          bodies, lines,
          vectors: [
            { id: 'v1', from: [s.x1, y + g1 + 0.3, 0], vec: [s.v1 * kv, 0, 0], color: '#fbbf24', label: `v₁ = ${s.v1.toFixed(2)} m/s` },
            { id: 'v2', from: [s.x2, y + g2 + 0.3, 0], vec: [s.v2 * kv, 0, 0], color: '#7dd3fc', label: `v₂ = ${s.v2.toFixed(2)} m/s` },
            { id: 'p1', from: [s.x1, y + 0.1, 0.35], vec: [p.m1 * s.v1 * kp, 0, 0], color: '#f59e0b', label: '' },
            { id: 'p2', from: [s.x2, y + 0.1, 0.35], vec: [p.m2 * s.v2 * kp, 0, 0], color: '#38bdf8', label: '' },
            { id: 'ptot', from: [(s.x1 * p.m1 + s.x2 * p.m2) / (p.m1 + p.m2), y + Math.max(g1, g2) + 0.75, 0], vec: [P() * kp, 0, 0], color: '#4ade80', label: `Σp = ${P().toFixed(3)} kg·m/s` },
          ],
        };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'explosion') {
      const u = Math.sqrt(2 * p.Ex / mu(p.m1, p.m2));
      return [
        'Σp before = Σp after;  ΔKE = released spring energy',
        `Σp = (${p.m1} + ${p.m2}) × ${p.v1} = ${m.pBefore.toFixed(3)} kg·m/s`,
        `separation speed u = √(2E/μ) = √(2 × ${p.Ex} / ${mu(p.m1, p.m2).toFixed(4)}) = ${u.toFixed(3)} m/s`,
        `after: ${p.m1} × ${m.v1.toFixed(3)} + ${p.m2} × ${m.v2.toFixed(3)} = ${m.pAfter.toFixed(3)} kg·m/s`,
      ];
    }
    return [
      'm₁v₁ + m₂v₂ = m₁v₁′ + m₂v₂′;   v₂′ − v₁′ = e(v₁ − v₂)',
      `before: ${p.m1} × ${p.v1} + ${p.m2} × ${p.v2} = ${m.pBefore.toFixed(3)} kg·m/s;  KE = ${m.KBefore.toFixed(4)} J`,
      `after: ${p.m1} × ${m.v1.toFixed(3)} + ${p.m2} × ${m.v2.toFixed(3)} = ${m.pAfter.toFixed(3)} kg·m/s;  KE = ${m.KAfter.toFixed(4)} J`,
      `e = (v₂′ − v₁′)/(v₁ − v₂) = ${m.eMeas.toFixed(3)};  KE lost = ${(m.KBefore - m.KAfter).toFixed(4)} J`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'collision' && r.params.e === 0 && r.final.hit === 1 && r.final.KBefore > 0.01 && Math.abs(r.final.v1) <= 0.01 && Math.abs(r.final.v2) <= 0.01),
    ({ runs }) => runs.some(r => r.params.mode === 'collision' && r.params.v2 === 0 && r.params.v1 !== 0 && r.params.e < 1 && r.final.hit === 1 && Math.abs(r.final.v1) <= 0.01),
    ({ runs }) => runs.some(r => r.params.mode === 'explosion' && r.params.v1 === 0 && r.final.hit === 1 && Math.abs(r.final.v1) > 1e-6 && Math.abs(Math.abs(r.final.v2 / r.final.v1) - 2) <= 0.02),
  ],
  evaluate(p) {
    const ex = p.mode === 'explosion';
    return { vars: { m1: p.m1, v1: p.v1, m2: p.m2, v2: ex ? p.v1 : p.v2, e: p.e, Ex: ex ? p.Ex : 0 }, answer: outcome(p)[0], unit: 'm/s', tol: 0.02 };
  },
};
