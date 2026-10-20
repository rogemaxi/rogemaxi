// Lab 4 — Projectile Launcher. A ball is launched with speed v0 at angle θ from a platform of height h0.
// The state (x, y, vx, vy) is integrated with the library's RK4 step using the same force law as
// projectileDrag: a = (0, −g) − k|v|v (k = 0 → ideal projectile, for which RK4 is exact).
import { rk4Step, projectile, projectileDrag, deg, C } from '../../physics/index.js';

const M = 0.5; // kg, ball mass (sets the energy bars only)
const T_MAX = 15; // s

export const deriv = (k, g = C.g) => ([, , vx, vy]) => { const sp = Math.hypot(vx, vy); return [vx, vy, -k * sp * vx, -g - k * sp * vy]; };

export default {
  num: 4, unit: 4, sections: ['4.1', '4.2', '4.3', '4.4', '4.6', '4.7'],
  text: {
    title: 'Projectile Launcher',
    question: 'How do launch speed, launch angle, and launch height determine a projectile’s time of flight, maximum height, and range — and how does air resistance change the answer?',
    params: { v0: 'Launch speed', th: 'Launch angle', h0: 'Launch height', k: 'Air drag k (0 = none)', xT: 'Target distance' },
    graph: ['trajectory y vs x (m)', 'height y (m) vs time', 'velocity components (m/s)', 'speed (m/s)'],
    series: { y: 'height', vx: 'vx', vy: 'vy', sp: 'speed', vac: 'no-drag path' },
    measures: { t: 'Time', x: 'Horizontal position', y: 'Height', vx: 'Horizontal velocity vx', vy: 'Vertical velocity vy', sp: 'Speed', hMax: 'Maximum height', range: 'Range', tFlight: 'Time of flight', vImpact: 'Impact speed', miss: 'Miss distance (landing − target)' },
    predict: {
      prompt: 'With no air drag, a ball is launched at 20 m/s from ground level, first at 30° and then at 60°. How will the two ranges compare?',
      choices: ['The 60° range is about twice the 30° range', 'The ranges are equal', 'The 30° range is about twice the 60° range', 'The 60° ball lands closer because it goes higher'],
    },
    guided: [
      'Drag off, h0 = 0, v0 = 20 m/s. Run angles 15°, 30°, 45°, 60°, 75° and record each. Which angle gives the greatest range? Which pairs give the same range?',
      'Launch horizontally (θ = 0°) from h0 = 20 m at 10 m/s and at 20 m/s. Compare the times of flight. What does this tell you about horizontal and vertical motion?',
      'Use the velocity-components graph: what happens to vx during the flight with no drag? What is the slope of the vy line, and what is vy at the top?',
      'Turn on drag (k = 0.01 /m). Compare range, maximum height, and time of flight with the faint no-drag path. Is the trajectory still symmetric?',
      'With drag on, try 35°, 40°, and 45°. Is 45° still the best angle?',
    ],
    challenges: [
      'Hit the target: make the ball land within 1.0 m of the target distance. Record the run.',
      'With drag off and h0 = 0, record two runs with the same launch speed at complementary angles (adding to 90°, not 45° + 45°) and show their ranges agree within 1 %.',
      'With drag k ≥ 0.01 /m, h0 = 0 and the same launch speed, record runs at 45° and at least two other angles, where a run below 45° goes farther than the 45° run.',
    ],
    evaluate: 'Before you run (with drag k = 0): a ball is launched at {v0} m/s at {th}° above horizontal from a height of {h0} m. Calculate its horizontal range when it lands on the ground (g = 9.8 m/s²).',
    honors: {
      prompt: 'Show that, without drag and from ground level, the range is R = v₀²·sin(2θ)/g, and use calculus to show that R is greatest at 45°. Then explain why launching from a height makes the best angle smaller than 45°.',
      solution: 'From y = v₀sinθ·t − ½gt² = 0, t = 2v₀sinθ/g, so R = v₀cosθ·t = v₀²·2sinθcosθ/g = v₀²sin2θ/g. dR/dθ = 2v₀²cos2θ/g = 0 → θ = 45°. From a height h₀ the ball keeps moving forward while it falls the extra distance, so a flatter launch (more horizontal speed) wins; e.g. v₀ = 15 m/s, h₀ = 20 m: the best angle is ≈ 31° (R ≈ 34 m) versus R ≈ 31.6 m at 45°.',
    },
    assumptions: [
      'The ball is a particle; g = 9.8 m/s² downward and uniform; the ground is flat and level at y = 0.',
      'Air drag, when on, is quadratic: a_drag = −k·|v|·v with constant k (per unit mass); no wind, lift, or spin. With k = 0 there is no air resistance at all.',
      'Motion is integrated with RK4 every 1/240 s (exact for the no-drag parabola); the landing point is interpolated within the last step. The run ends at landing or after 15 s.',
      'The ball’s 0.5 kg mass only sets the energy bars; with no drag the trajectory does not depend on mass.',
      'The muzzle flash and the dust burst at impact are visual effects only.',
    ],
  },
  params: [
    { id: 'v0', min: 2, max: 40, step: 0.5, value: 20, unit: 'm/s' },
    { id: 'th', min: 0, max: 90, step: 1, value: 45, unit: '°' },
    { id: 'h0', min: 0, max: 30, step: 1, value: 0, unit: 'm' },
    { id: 'k', min: 0, max: 0.05, step: 0.005, value: 0, unit: '1/m' },
    { id: 'xT', min: 5, max: 150, step: 1, value: 30, unit: 'm' },
  ],
  camera: { target: [32, 10, 0], dist: 85, free: [0.15, 0.25, 1], followId: 'ball' },
  view2d: { span: 100, cx: 40, cy: 18 },
  graph: {
    choices: [
      { label: 'trajectory y vs x (m)', x: 'x', xLabel: 'x (m)', y: ['y'], labels: ['y'], yLabel: 'y (m)' },
      { label: 'height y (m) vs time', y: ['y'], labels: ['y'], yLabel: 'y (m)' },
      { label: 'velocity components (m/s)', y: ['vx', 'vy'], labels: ['vx', 'vy'], yLabel: 'v (m/s)' },
      { label: 'speed (m/s)', y: ['sp'], labels: ['sp'], yLabel: '|v| (m/s)' },
    ],
  },
  recordKeys: ['range', 'hMax', 'tFlight', 'vImpact', 'miss'],
  decor: p => [
    { shape: 'ground', size: 500, divisions: 50 },
    ...(p.h0 > 0 ? [{ shape: 'box', size: [3, p.h0, 3], pos: [-1.2, p.h0 / 2, 0], color: '#475569' }] : []),
    { shape: 'cylinder', r: 2, h: 0.1, pos: [p.xT, 0.05, 0], color: '#f8fafc' },
    { shape: 'cylinder', r: 1.3, h: 0.12, pos: [p.xT, 0.06, 0], color: '#ef4444' },
    { shape: 'cylinder', r: 0.5, h: 0.14, pos: [p.xT, 0.07, 0], color: '#f8fafc' },
    { shape: 'label', text: `target ${p.xT} m`, pos: [p.xT, 1.2, 0], color: '#fecaca' },
    ...Array.from({ length: 9 }, (_, i) => ({ shape: 'label', text: `${i * 20} m`, pos: [i * 20, 0.2, 4], color: '#94a3b8' })),
    // faint no-drag (vacuum) parabola for comparison
    { shape: 'line', color: '#94a3b8', opacity: p.k > 0 ? 0.55 : 0.18, pts: (() => { const P = projectile(p.v0, p.th, p.h0); return Array.from({ length: 81 }, (_, i) => { const [x, y] = P.pos(P.tFlight * i / 80); return [x, Math.max(0, y), -0.6]; }); })() },
  ],
  create(p) {
    const f = deriv(p.k);
    const s = { t: 0, y: [0, p.h0, p.v0 * Math.cos(deg(p.th)), p.v0 * Math.sin(deg(p.th))], hMax: p.h0, landed: false, tFlight: NaN, range: NaN, vImpact: NaN, done: false, events: [] };
    const E0 = M * (0.5 * p.v0 * p.v0 + C.g * p.h0);
    let fired = false;
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        if (!fired) { fired = true; s.events.push({ type: 'burst', pos: [Math.cos(deg(p.th)) * 2, p.h0 + 1 + Math.sin(deg(p.th)) * 2, 0], strength: 0.5, speed: 1.5, color: '#fb923c', life: 0.6 }); }
        const prev = s.y, next = rk4Step(f, prev, dt);
        // apex inside the step: quadratic through the step with its mean vertical acceleration
        // (exact for k = 0, where RK4 reproduces the parabola and ay = −g)
        if (prev[3] > 0 && next[3] <= 0) {
          const ay = (next[3] - prev[3]) / dt, tau = -prev[3] / ay;
          s.hMax = Math.max(s.hMax, prev[1] + prev[3] * tau + 0.5 * ay * tau * tau);
        }
        s.hMax = Math.max(s.hMax, next[1]);
        if (next[1] < 0) {
          const fr = prev[1] / (prev[1] - next[1]);
          s.y = prev.map((v, i) => v + fr * (next[i] - v));
          s.y[1] = 0; s.t += fr * dt;
          s.landed = true; s.tFlight = s.t; s.range = s.y[0]; s.vImpact = Math.hypot(s.y[2], s.y[3]); s.done = true;
          s.events.push({ type: 'impact', pos: [s.y[0], 0.1, 0], strength: Math.min(2, s.vImpact / 15), normal: 'y', color: '#d6d3d1' });
          return;
        }
        s.y = next; s.t += dt;
        if (s.t >= T_MAX - 1e-9) s.done = true;
      },
      measures() {
        const [x, y, vx, vy] = s.y;
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'x', label: 'Horizontal position', value: x, unit: 'm', ref: 150 },
          { id: 'y', label: 'Height', value: y, unit: 'm', ref: 50 },
          { id: 'vx', label: 'Horizontal velocity vx', value: vx, unit: 'm/s', ref: 40 },
          { id: 'vy', label: 'Vertical velocity vy', value: vy, unit: 'm/s', ref: 40 },
          { id: 'sp', label: 'Speed', value: Math.hypot(vx, vy), unit: 'm/s', ref: 40, hidden: true },
          { id: 'hMax', label: 'Maximum height', value: s.hMax, unit: 'm', ref: 50 },
          { id: 'tFlight', label: 'Time of flight', value: s.tFlight, unit: 's', ref: 8 },
          { id: 'range', label: 'Range', value: s.range, unit: 'm', ref: 150 },
          { id: 'vImpact', label: 'Impact speed', value: s.vImpact, unit: 'm/s', ref: 40, hidden: true },
          { id: 'miss', label: 'Miss distance (landing − target)', value: s.landed ? s.range - p.xT : NaN, unit: 'm', ref: 50 },
        ];
      },
      energy() {
        const [, y, vx, vy] = s.y, KE = 0.5 * M * (vx * vx + vy * vy), PE = M * C.g * y;
        return [
          { label: 'KE', value: KE, color: '#fbbf24' },
          { label: 'PE (gravity)', value: PE, color: '#7dd3fc' },
          { label: 'Lost to drag', value: Math.max(0, E0 - KE - PE), color: '#f87171' },
          { label: 'Total (start)', value: E0, color: '#4ade80' },
        ];
      },
      scene() {
        const [x, y, vx, vy] = s.y, k = 0.25, base = [0, p.h0 + 0.6, 0];
        const r = deg(p.th);
        return {
          bodies: [
            { id: 'barrel', shape: 'cylinder', r: 0.35, h: 2.6, pos: [base[0] + Math.cos(r) * 1.1, base[1] + Math.sin(r) * 1.1, 0], rot: [0, 0, r - Math.PI / 2], color: '#334155', metal: 0.7 },
            { id: 'mount', shape: 'sphere', r: 0.7, pos: base, color: '#1f2937', metal: 0.6 },
            { id: 'ball', shape: 'sphere', r: 0.45, pos: [x, Math.max(0.3, y), 0], color: '#fbbf24', emissive: '#f59e0b', glow: 0.35, trail: true, trailColor: '#fde68a', label: s.landed ? `R = ${s.range.toFixed(2)} m` : `${Math.hypot(vx, vy).toFixed(1)} m/s` },
          ],
          vectors: [
            { id: 'vx', from: [x, y, 0], vec: [vx * k, 0, 0], color: '#f87171', label: `vx ${vx.toFixed(1)}` },
            { id: 'vy', from: [x, y, 0], vec: [0, vy * k, 0], color: '#60a5fa', label: `vy ${vy.toFixed(1)}` },
            { id: 'v', from: [x, y, 0], vec: [vx * k, vy * k, 0], color: '#4ade80', label: '' },
            { id: 'g', from: [x, y, 0.8], vec: [0, -1.8, 0], color: '#c084fc', label: 'g' },
          ],
        };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    const P = projectile(p.v0, p.th, p.h0), f = x => (Number.isFinite(x) ? x.toFixed(2) : '—');
    return [
      `vx₀ = ${p.v0}·cos ${p.th}° = ${f(P.vx)} m/s;   vy₀ = ${p.v0}·sin ${p.th}° = ${f(P.vy)} m/s`,
      `y = ${p.h0} + ${f(P.vy)}t − ½(9.8)t² = 0  →  t = ${f(P.tFlight)} s (no drag)`,
      `range = vx₀·t = ${f(P.vx)} × ${f(P.tFlight)} = ${f(P.range)} m;   hMax = ${p.h0} + vy₀²/2g = ${f(P.hMax)} m (no drag)`,
      p.k > 0 ? `with drag k = ${p.k}: a = −g ĵ − k|v|v  →  simulated range ${f(m.range)} m, hMax ${f(m.hMax)} m` : `simulated: x = ${f(m.x)} m, y = ${f(m.y)} m, vy = ${f(m.vy)} m/s`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => Number.isFinite(r.final.range) && Math.abs(r.final.range - r.params.xT) <= 1),
    ({ runs }) => runs.some(a => a.params.k === 0 && a.params.h0 === 0 && a.params.th !== 45 && runs.some(b => b !== a && b.params.k === 0 && b.params.h0 === 0 &&
      b.params.v0 === a.params.v0 && a.params.th + b.params.th === 90 && a.final.range > 0 && Math.abs(b.final.range / a.final.range - 1) <= 0.01)),
    ({ runs }) => {
      const ok = runs.filter(r => r.params.k >= 0.01 && r.params.h0 === 0 && Number.isFinite(r.final.range));
      return ok.some(r45 => r45.params.th === 45 && (() => {
        const same = ok.filter(r => r.params.v0 === r45.params.v0 && r.params.k === r45.params.k);
        return new Set(same.map(r => r.params.th)).size >= 3 && same.some(r => r.params.th < 45 && r.final.range > r45.final.range);
      })());
    },
  ],
  evaluate(p) {
    return { vars: { v0: p.v0, th: p.th, h0: p.h0 }, answer: projectile(p.v0, p.th, p.h0).range, unit: 'm', tol: 0.02 };
  },
  // exposed for tests and the honors extension
  dragReference: (p, dt = 1 / 240) => projectileDrag(p.v0, p.th, p.k, { h0: p.h0, dt }),
};
