// Lab 2 — Vector Explorer. Two or three vectors are added head-to-tail by components.
// "Walk" mode: a walker follows displacement vectors A, B, C in turn (constant speed on each leg).
// "River" mode: a boat with velocity A relative to the water crosses a river whose current B flows along +x.
// Physics coordinates: x = east, y = north (across the river). Scene: (x, height, −y), seen from above.
import { vecFromPolar, vecAdd, vecMag, vecAngle } from '../../physics/index.js';

const LEG = 1.5;          // s of animation per displacement leg (walk mode)
const RIVER_TMAX = 40;    // s: a boat that has not crossed by then never will (or is too slow)
const S = (x, y, h = 0.15) => [x, h, -y];

// The vectors in play for the chosen mode (river mode: current along +x, no third vector).
export function vectorsFor(p) {
  const river = p.mode === 'river';
  const list = [{ id: 'A', mag: p.A, ang: p.thA }, { id: 'B', mag: p.B, ang: river ? 0 : p.thB }];
  if (!river && p.C > 0) list.push({ id: 'C', mag: p.C, ang: p.thC });
  return list.map(v => ({ ...v, vec: vecFromPolar(v.mag, v.ang) }));
}
export function resultant(p) {
  const vs = vectorsFor(p), R = vecAdd(...vs.map(v => v.vec));
  return { vs, R, mag: vecMag(R), ang: vecAngle(R) };
}

export default {
  num: 2, unit: 2, sections: ['2.3', '2.4', '2.5', '2.6'],
  dt: 1 / 120,
  text: {
    title: 'Vector Explorer',
    question: 'How do the magnitudes and directions of two or three vectors combine into a single resultant, and how does that decide where a boat lands when it crosses a moving river?',
    params: { mode: 'Scenario', A: 'Vector A magnitude', thA: 'Vector A direction', B: 'Vector B magnitude (river: current speed)', thB: 'Vector B direction (walk only)', C: 'Vector C magnitude (walk only; 0 = off)', thC: 'Vector C direction (walk only)', W: 'River width' },
    options: { river: 'River crossing (velocities)', walk: 'Displacement walk (head-to-tail)' },
    graph: ['position components (m)', 'distance vs displacement (m)', 'path: y vs x (m)'],
    series: { x: 'x (east)', y: 'y (north)', dist: 'distance travelled', disp: '|displacement|' },
    measures: { t: 'Time', Rx: 'Resultant x-component', Ry: 'Resultant y-component', R: 'Resultant magnitude', thR: 'Resultant direction', x: 'Position x', y: 'Position y', dist: 'Distance travelled', disp: 'Displacement magnitude', tCross: 'Crossing time', drift: 'Downstream drift', leg: 'Legs completed' },
    predict: {
      prompt: 'The boat points straight across the river (A at 90°). If the current speed B is doubled, what happens to the time it takes to reach the far bank?',
      choices: ['It takes longer', 'It stays the same', 'It takes less time', 'The boat never reaches the far bank'],
    },
    guided: [
      'River mode, A = 4 m/s at 90°, B = 3 m/s, W = 40 m. Run it. Use components to explain the 5.0 m/s ground speed, the 10 s crossing time, and the 30 m drift.',
      'Keep the heading at 90° and change only the current (B = 0, 3, 6 m/s). Record each run. Which measurements change and which do not? Explain using independent components.',
      'Walk mode: A = 4 m at 0°, B = 3 m at 90°, C = 0. Predict the resultant magnitude and direction, then run. Compare the distance travelled with the displacement.',
      'Add a third vector C. Change only the ORDER of the vectors (swap A and B). Does the resultant change? Does the path change?',
      'In river mode, find the heading that takes the boat straight across when B = 2 m/s and A = 4 m/s. Explain why the crossing then takes longer.',
    ],
    challenges: [
      'Walk mode: choose three non-zero vectors that bring the walker back to the start (resultant ≤ 0.2 m). Run it to the end.',
      'River mode with a current of at least 2 m/s: choose a heading that lands the boat within 0.5 m of the point directly across. Run it.',
      'Walk mode: record two complete runs that use the same two vectors in opposite order (swap A and B, including directions, with A ≠ B) and show the resultants are identical.',
    ],
    evaluate: 'Before you run: add the vectors A = {A} at {thA}°, B = {B} at {thB}°, and C = {C} at {thC}° (directions measured counterclockwise from +x). Calculate the magnitude of the resultant.',
    honors: {
      prompt: 'For a boat of speed vb in a current vc < vb, find the heading that minimises the crossing time, and the heading that lands directly across. Derive the crossing time for each and test both with W = 40 m, vb = 4 m/s, vc = 2 m/s.',
      solution: 'Crossing time t = W/(vb·sin θ) is smallest at θ = 90°: t = 40/4 = 10 s (drift = vc·t = 20 m). To land directly across, vb·cos θ = −vc → θ = 180° − cos⁻¹(vc/vb) = 120°; then vy = vb·sin 120° = √(vb² − vc²) = 3.46 m/s and t = 40/3.46 = 11.5 s.',
    },
    assumptions: [
      'Vectors are two-dimensional and angles are measured counterclockwise from the +x (east) axis.',
      'Walk mode: the walker moves at constant speed along each leg in turn, taking 1.5 s per leg regardless of its length; only the displacements matter for the resultant.',
      'River mode: the current is uniform across the whole river and flows along +x; vector B’s direction and vector C are not used. The boat’s velocity relative to the water is constant and it starts instantly.',
      'The boat is a point for the measurements; its picture is only drawn pointing along its heading. If it has not crossed after 40 s (or is moving away from the far bank) the run ends without a crossing.',
      'Water ripples and the grid are visual aids only.',
    ],
  },
  params: [
    { id: 'mode', value: 'river', options: [{ value: 'river', label: 'River crossing (velocities)' }, { value: 'walk', label: 'Displacement walk (head-to-tail)' }] },
    { id: 'A', min: 0, max: 10, step: 0.5, value: 4, unit: 'm or m/s' },
    { id: 'thA', min: 0, max: 360, step: 5, value: 90, unit: '°' },
    { id: 'B', min: 0, max: 10, step: 0.5, value: 3, unit: 'm or m/s' },
    { id: 'thB', min: 0, max: 360, step: 5, value: 0, unit: '°' },
    { id: 'C', min: 0, max: 10, step: 0.5, value: 0, unit: 'm' },
    { id: 'thC', min: 0, max: 360, step: 5, value: 180, unit: '°' },
    { id: 'W', min: 10, max: 60, step: 5, value: 40, unit: 'm' },
  ],
  camera: { target: [0, 0, -14], dist: 62, free: [0.12, 1, 0.75], followId: 'mover' },
  view2d: { plane: 'xz', span: 75, cx: 0, cy: 14 },
  graph: {
    choices: [
      { label: 'position components (m)', y: ['x', 'y'], labels: ['x', 'y'], yLabel: 'position (m)' },
      { label: 'distance vs displacement (m)', y: ['dist', 'disp'], labels: ['dist', 'disp'], yLabel: 'length (m)' },
      { label: 'path: y vs x (m)', x: 'x', xLabel: 'x (m)', y: ['y'], labels: ['y'], yLabel: 'y (m)' },
    ],
  },
  recordKeys: ['Rx', 'Ry', 'R', 'thR', 'disp', 'tCross', 'drift'],
  decor: p => {
    const out = [{ shape: 'ground', size: 200, divisions: 40 }];
    if (p.mode === 'river') {
      out.push(
        { shape: 'box', size: [200, 0.06, p.W], pos: [0, 0.03, -p.W / 2], color: '#1e3a8a', opacity: 0.85 },
        { shape: 'box', size: [200, 0.4, 3], pos: [0, 0.2, 1.5], color: '#4d7c0f' },
        { shape: 'box', size: [200, 0.4, 3], pos: [0, 0.2, -p.W - 1.5], color: '#4d7c0f' },
        { shape: 'cylinder', r: 0.6, h: 2.5, pos: [0, 1.25, -p.W - 1.2], color: '#f87171' },
        { shape: 'label', text: 'directly across', pos: [0, 3, -p.W - 1.2], color: '#fecaca' },
        { shape: 'label', text: `current → (${p.B} m/s)`, pos: [-25, 0.4, -p.W / 2], color: '#93c5fd' },
        ...Array.from({ length: 9 }, (_, i) => ({ shape: 'label', text: `${(i - 4) * 10} m`, pos: [(i - 4) * 10, 0.4, 4], color: '#94a3b8' })),
      );
      for (let i = -9; i <= 9; i++) out.push({ shape: 'line', pts: [S(i * 10, p.W * 0.3, 0.08), S(i * 10 + 3, p.W * 0.3, 0.08)], color: '#60a5fa', opacity: 0.6 }, { shape: 'line', pts: [S(i * 10 + 5, p.W * 0.7, 0.08), S(i * 10 + 8, p.W * 0.7, 0.08)], color: '#60a5fa', opacity: 0.6 });
    } else {
      out.push(
        { shape: 'line', pts: [S(-30, 0, 0.05), S(30, 0, 0.05)], color: '#64748b' },
        { shape: 'line', pts: [S(0, -30, 0.05), S(0, 30, 0.05)], color: '#64748b' },
        { shape: 'label', text: '+x (E)', pos: S(31, 0, 0.3) }, { shape: 'label', text: '+y (N)', pos: S(0, 31, 0.3) },
        { shape: 'cylinder', r: 0.5, h: 0.2, pos: S(0, 0, 0.1), color: '#e2e8f0' },
        { shape: 'label', text: 'start', pos: S(0, -1.5, 0.3), color: '#e2e8f0' },
      );
      for (let i = -3; i <= 3; i++) if (i) out.push({ shape: 'label', text: `${i * 10}`, pos: S(i * 10, -1.5, 0.2), color: '#94a3b8' }, { shape: 'label', text: `${i * 10}`, pos: S(-2, i * 10, 0.2), color: '#94a3b8' });
    }
    return out;
  },
  create(p) {
    const river = p.mode === 'river', res = resultant(p), vs = res.vs.filter(v => v.mag > 0);
    const s = { t: 0, x: 0, y: 0, dist: 0, leg: 0, tCross: NaN, drift: NaN, done: false, events: [] };
    const tips = []; { let a = [0, 0]; for (const v of vs) { a = vecAdd(a, v.vec); tips.push(a); } }
    const walkPos = t => {
      let start = [0, 0], dist = 0;
      for (let i = 0; i < vs.length; i++) {
        const f = Math.min(1, Math.max(0, (t - i * LEG) / LEG));
        if (f < 1) return { pos: [start[0] + f * vs[i].vec[0], start[1] + f * vs[i].vec[1]], dist: dist + f * vs[i].mag, leg: i };
        start = tips[i]; dist += vs[i].mag;
      }
      return { pos: start, dist, leg: vs.length };
    };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        if (river) {
          const [vx, vy] = res.R;
          let h = dt;
          if (vy > 0 && s.y + vy * dt >= p.W) { h = (p.W - s.y) / vy; }
          s.x += vx * h; s.y += vy * h; s.t += h; s.dist += res.mag * h;
          if (vy > 0 && s.y >= p.W - 1e-12) {
            s.y = p.W; s.tCross = s.t; s.drift = s.x; s.done = true;
            s.events.push({ type: 'impact', pos: S(s.x, p.W, 0.3), strength: 0.8, normal: 'y', color: '#93c5fd' });
          }
          if (s.t >= RIVER_TMAX - 1e-9 || s.y < -2) s.done = true;
        } else {
          s.t += dt;
          const w = walkPos(s.t);
          if (w.leg > s.leg && w.leg <= vs.length) s.events.push({ type: 'spark', pos: S(...tips[w.leg - 1], 0.5), strength: 0.3, speed: 0.6, color: '#fde68a', life: 0.5 });
          s.x = w.pos[0]; s.y = w.pos[1]; s.dist = w.dist; s.leg = w.leg;
          if (s.t >= vs.length * LEG + 0.3 - 1e-9) s.done = true;
        }
      },
      measures() {
        const u = river ? 'm/s' : 'm';
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'Rx', label: 'Resultant x-component', value: res.R[0], unit: u, ref: 20 },
          { id: 'Ry', label: 'Resultant y-component', value: res.R[1], unit: u, ref: 20 },
          { id: 'R', label: 'Resultant magnitude', value: res.mag, unit: u, ref: 20 },
          { id: 'thR', label: 'Resultant direction', value: res.mag > 1e-12 ? res.ang : NaN, unit: '°', ref: 180 },
          { id: 'x', label: 'Position x', value: s.x, unit: 'm', ref: 40 },
          { id: 'y', label: 'Position y', value: s.y, unit: 'm', ref: 40 },
          { id: 'dist', label: 'Distance travelled', value: s.dist, unit: 'm', ref: 40 },
          { id: 'disp', label: 'Displacement magnitude', value: Math.hypot(s.x, s.y), unit: 'm', ref: 40 },
          { id: 'tCross', label: 'Crossing time', value: s.tCross, unit: 's', ref: 30, hidden: !river },
          { id: 'drift', label: 'Downstream drift', value: s.drift, unit: 'm', ref: 40 },
          { id: 'leg', label: 'Legs completed', value: s.leg, unit: '', hidden: true },
        ];
      },
      energy() { return []; },
      scene() {
        const COL = { A: '#f87171', B: '#60a5fa', C: '#c084fc' }, vectors = [];
        const bodies = [];
        if (river) {
          const k = 2.5, at = S(s.x, s.y, 0.6), heading = p.thA * Math.PI / 180;
          bodies.push({ id: 'mover', shape: 'box', size: [3, 0.8, 1.4], pos: S(s.x, s.y, 0.45), rot: [0, heading, 0], color: '#f8fafc', trail: true, trailColor: '#fbbf24', label: `boat ${res.mag.toFixed(2)} m/s` });
          const vA = res.vs[0].vec, vB = res.vs[1].vec;
          vectors.push(
            { id: 'A', from: at, vec: [vA[0] * k, 0, -vA[1] * k], color: COL.A, label: `A = ${p.A} m/s` },
            { id: 'B', from: [at[0] + vA[0] * k, at[1], at[2] - vA[1] * k], vec: [vB[0] * k, 0, -vB[1] * k], color: COL.B, label: `current ${p.B} m/s` },
            { id: 'R', from: at, vec: [res.R[0] * k, 0, -res.R[1] * k], color: '#4ade80', label: `v = ${res.mag.toFixed(2)} m/s` },
          );
        } else {
          let a = [0, 0];
          for (const v of vs) { vectors.push({ id: v.id, from: S(...a, 0.2), vec: [v.vec[0], 0, -v.vec[1]], color: COL[v.id], label: `${v.id} = ${v.mag} m @ ${v.ang}°` }); a = vecAdd(a, v.vec); }
          vectors.push(
            { id: 'R', from: S(0, 0, 0.3), vec: [res.R[0], 0, -res.R[1]], color: '#4ade80', label: `R = ${res.mag.toFixed(2)} m` },
            { id: 'Rx', from: S(0, 0, 0.1), vec: [res.R[0], 0, 0], color: '#fde68a', label: `Rx = ${res.R[0].toFixed(2)}` },
            { id: 'Ry', from: S(res.R[0], 0, 0.1), vec: [0, 0, -res.R[1]], color: '#fdba74', label: `Ry = ${res.R[1].toFixed(2)}` },
          );
          bodies.push({ id: 'mover', shape: 'sphere', r: 0.6, pos: S(s.x, s.y, 0.6), color: '#fbbf24', emissive: '#f59e0b', glow: 0.3, trail: true, label: `distance ${s.dist.toFixed(1)} m` });
        }
        return { bodies, vectors };
      },
    };
  },
  equations(p, model) {
    const res = resultant(p), f = x => x.toFixed(2);
    const terms = c => res.vs.map(v => `${v.mag}·${c}(${v.ang}°)`).join(' + ');
    const eq = [
      `Rx = ${terms('cos')} = ${f(res.R[0])}`,
      `Ry = ${terms('sin')} = ${f(res.R[1])}`,
      `|R| = √(${f(res.R[0])}² + ${f(res.R[1])}²) = ${f(res.mag)} ${p.mode === 'river' ? 'm/s' : 'm'}`,
      `θ = atan2(Ry, Rx) = ${res.mag > 1e-12 ? f(res.ang) : '—'}°`,
    ];
    if (p.mode === 'river') {
      const vy = res.R[1];
      eq.push(vy > 0 ? `t = W / vy = ${p.W} / ${f(vy)} = ${f(p.W / vy)} s;  drift = vx·t = ${f(res.R[0])} × ${f(p.W / vy)} = ${f(res.R[0] * p.W / vy)} m` : 'vy ≤ 0: the boat never reaches the far bank');
    }
    return eq;
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'walk' && r.params.A > 0 && r.params.B > 0 && r.params.C > 0 && r.final.leg === 3 && r.final.R <= 0.2 && r.final.disp <= 0.2),
    ({ runs }) => runs.some(r => r.params.mode === 'river' && r.params.B >= 2 && Number.isFinite(r.final.tCross) && Math.abs(r.final.drift) <= 0.5),
    ({ runs }) => runs.some(a => a.params.mode === 'walk' && runs.some(b => b !== a && b.params.mode === 'walk' &&
      a.params.A === b.params.B && a.params.thA === b.params.thB && a.params.B === b.params.A && a.params.thB === b.params.thA &&
      a.params.C === b.params.C && (a.params.C === 0 || a.params.thC === b.params.thC) && (a.params.A !== a.params.B || a.params.thA % 360 !== a.params.thB % 360) &&
      a.final.leg >= 2 && b.final.leg >= 2 && Math.abs(a.final.R - b.final.R) < 1e-9 && Math.abs(a.final.disp - b.final.disp) < 1e-6)),
  ],
  evaluate(p) {
    const river = p.mode === 'river', res = resultant(p);
    return { vars: { A: p.A, thA: p.thA, B: p.B, thB: river ? 0 : p.thB, C: river ? 0 : p.C, thC: river ? 0 : p.thC }, answer: res.mag, unit: river ? 'm/s' : 'm', tol: 0.02 };
  },
};
