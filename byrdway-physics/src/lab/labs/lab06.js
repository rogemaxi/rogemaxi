// Lab 6 — Friction and Incline Lab. A block on an adjustable incline with static and kinetic friction:
// static hold vs slide, the critical angle θc = tan⁻¹ μs, and the weight resolved into components.
import { incline, criticalAngle, deg, kin, C } from '../../physics/index.js';

const RAMP = 5;     // ramp (hypotenuse) length, m
const BW = 0.6;     // block length along the ramp, m
const RUN = RAMP - BW - 0.05; // distance the block can travel before reaching the stop, m
const HOLD = 1.5;   // a block held at rest by static friction ends the run after this long, s
const TMAX = 8;
const muKeff = p => Math.min(p.muK, p.muS); // μk can never exceed μs (disclosed in assumptions)

export default {
  num: 6, unit: 5, sections: ['5.5', '5.6', '5.7'],
  text: {
    title: 'Friction and Incline Lab',
    question: 'When does static friction stop holding a block on a ramp, and how fast does it accelerate once it slides?',
    params: { theta: 'Ramp angle θ', m: 'Block mass', muS: 'Static coefficient μs', muK: 'Kinetic coefficient μk', v0: 'Initial push (down the ramp)' },
    graph: ['velocity v (m/s)', 'distance down the ramp s (m)', 'acceleration a (m/s²)', 'forces along the ramp (N)'],
    series: { Fpar: 'mg·sinθ', f: 'friction', net: 'net' },
    measures: { t: 'Time', s: 'Distance down the ramp', v: 'Velocity', a: 'Acceleration', Fpar: 'Weight component along ramp', N: 'Normal force', f: 'Friction force (up the ramp)', fsMax: 'Maximum static friction', thetaC: 'Critical angle' },
    predict: {
      prompt: 'The ramp is at 20° and μs = 0.40, so the 2 kg block stays at rest. You double the block’s mass to 4 kg without changing the angle. What will happen?',
      choices: ['The heavier block now slides down', 'It still stays at rest — the mass cancels out', 'It slides, but more slowly', 'It stays at rest, but only because friction halves'],
    },
    guided: [
      'Set μs = 0.40, μk = 0.30 and no push. Raise θ in 1° steps from 18°. Record the last angle where the block holds and the first angle where it slides. Compare with tan⁻¹(0.40).',
      'Hold θ = 15° and change the mass from 1 kg to 8 kg. Watch the friction and normal-force readings. Why does the block’s state never change?',
      'Set θ = 35°, μs = 0.50, μk = 0.25. Run from rest and use the v–t graph slope to measure a. Show that a = g(sinθ − μk·cosθ).',
      'With θ below the critical angle but tanθ < μk, give the block a push of 2 m/s. Describe the motion and explain why it stops and then stays stopped.',
      'Turn on the forces graph. Explain why the friction force jumps when the block starts to slide (static → kinetic).',
    ],
    challenges: [
      'Locate the critical angle: record a run where the block just holds from rest and a run with the same μs where it slides, with the two angles at most 1.0° apart.',
      'Make the block slide the full ramp at constant velocity: give it a push and choose θ and μk so the measured acceleration is within ±0.05 m/s² of zero.',
      'With μk = 0.20 and the block released from rest, choose the angle so it reaches the stop in 2.00 s (±0.05 s). Run it.',
    ],
    evaluate: 'Before you run: a {m} kg block is released from rest on a {theta}° ramp with μs = {muS} and μk = {muK}. Calculate its acceleration down the ramp (g = 9.8 m/s²). Enter 0 if static friction holds it.',
    honors: {
      prompt: 'Using only the angle slider, the timer and the distance reading (not the friction display), design a procedure that measures both μs and μk for one surface. Give the equations and test them.',
      solution: 'Raise θ slowly from rest until the block first slides: μs = tanθc (e.g. θc ≈ 21.8° → μs = 0.40). Then, at a steeper angle, time the slide over the known distance s from rest: a = 2s/t², and from ΣF∥ = m·a, μk = tanθ − a/(g·cosθ). Example: θ = 35°, s = 4.35 m, measured t = 1.55 s → a = 2s/t² = 3.62 m/s², μk = tan 35° − 3.62/(9.8 × cos 35°) = 0.700 − 0.451 = 0.25.',
    },
    assumptions: [
      'The block is a rigid particle sliding (not rolling or tipping) on a rigid, uniform ramp; air resistance is neglected.',
      'Coulomb friction: static friction takes whatever value up to μs·N is needed to hold the block; kinetic friction has constant magnitude μk·N opposite the motion. If μk is set above μs the lab uses μk = μs.',
      'The block moves only down the ramp (an initial push is directed down the slope). If kinetic friction brings it to rest, it stays at rest, because tanθ < μk ≤ μs.',
      'g = 9.8 m/s². Motion uses exact constant-acceleration updates with the stop and bottom-arrival times solved exactly inside a time step.',
      'Thermal energy is μk·N times the distance slid. Sparks at the contact surface are a visual effect only.',
      'The run ends when the block reaches the stop, after 8 s, or after it has been held at rest for 1.5 s.',
    ],
  },
  params: [
    { id: 'theta', min: 0, max: 60, step: 0.5, value: 20, unit: '°' },
    { id: 'm', min: 0.5, max: 10, step: 0.5, value: 2, unit: 'kg' },
    { id: 'muS', min: 0, max: 1, step: 0.01, value: 0.4, unit: '' },
    { id: 'muK', min: 0, max: 1, step: 0.01, value: 0.3, unit: '' },
    { id: 'v0', min: 0, max: 3, step: 0.1, value: 0, unit: 'm/s' },
  ],
  camera: { target: [2.4, 1.4, 0], dist: 9, free: [0.28, 0.3, 1], followId: 'block' },
  view2d: { span: 8, cx: 2.5, cy: 1.9 },
  graph: {
    choices: [
      { label: 'velocity v (m/s)', y: ['v'], labels: ['v'], yLabel: 'v (m/s)' },
      { label: 'distance down the ramp s (m)', y: ['s'], labels: ['s'], yLabel: 's (m)' },
      { label: 'acceleration a (m/s²)', y: ['a'], labels: ['a'], yLabel: 'a (m/s²)' },
      { label: 'forces along the ramp (N)', y: ['Fpar', 'f', 'Fnet'], labels: ['Fpar', 'f', 'net'], yLabel: 'F (N)' },
    ],
  },
  recordKeys: ['a', 'v', 's', 't', 'f'],
  decor: p => {
    const th = deg(p.theta), cs = Math.cos(th), sn = Math.sin(th), xb = RAMP * cs;
    const arc = Array.from({ length: 13 }, (_, i) => { const a = Math.PI - th * i / 12; return [xb + 0.9 * Math.cos(a), 0.9 * Math.sin(a) + 0.01, 0.75]; });
    return [
      { shape: 'ground', size: 40 },
      { shape: 'ramp', length: RAMP, angle: p.theta, x: 0, y: 0, depth: 1.4, color: '#475569' },
      { shape: 'box', size: [0.12, 0.5, 1.4], pos: [xb + 0.06, 0.25, 0], color: '#f87171' },
      { shape: 'line', pts: arc, color: '#fbbf24' },
      { shape: 'label', text: `θ = ${p.theta}°`, pos: [xb - 1.25, 0.25, 0.8], color: '#fbbf24' },
      { shape: 'label', text: `θc = ${criticalAngle(p.muS).toFixed(1)}°`, pos: [0.4, RAMP * sn + 0.5, 0.8], color: '#94a3b8' },
    ];
  },
  create(p) {
    const g = C.g, th = deg(p.theta), sn = Math.sin(th), cs = Math.cos(th), mk = muKeff(p);
    const N = p.m * g * cs, Fpar = p.m * g * sn, fsMax = p.muS * N, aK = g * (sn - mk * cs);
    const slipsFromRest = Fpar > fsMax + 1e-12; // same test as physics/incline()
    const s = { t: 0, x: 0, v: p.v0, a: 0, f: 0, Q: 0, sliding: p.v0 > 0 || slipsFromRest, held: 0, done: false, events: [], bottom: false };
    const forces = () => { if (s.sliding) { s.a = aK; s.f = mk * N; } else { s.a = 0; s.f = Fpar; } };
    forces();
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        if (s.done) return;
        forces();
        if (!s.sliding) {
          s.t += dt; s.held += dt;
          if (s.held >= HOLD - 1e-9 || s.t >= TMAX - 1e-9) s.done = true;
          return;
        }
        const a = aK;
        let tau = dt, end = null;
        const tB = kin.timeToDx(s.v, a, RUN - s.x);
        if (tB != null && tB <= dt) { tau = tB; end = 'bottom'; }
        if (a < 0) { const tS = -s.v / a; if (tS <= tau) { tau = tS; end = 'stop'; } }
        const dx = s.v * tau + 0.5 * a * tau * tau;
        s.x += dx; s.v += a * tau; s.Q += mk * N * dx; s.t += tau;
        if (end === 'bottom') {
          s.x = RUN; s.done = true; s.bottom = true;
          const P = [(BW + RUN) * cs, (RAMP - BW - RUN) * sn + 0.2, 0];
          s.events.push({ type: 'impact', pos: P, strength: Math.min(2, s.v / 4), normal: 'x' });
        } else if (end === 'stop') {
          s.v = 0; s.sliding = false; forces(); // kinetic friction stopped it; tanθ < μk ≤ μs so static friction holds
          s.t += dt - tau; s.held += dt - tau;
        }
        if (s.t >= TMAX - 1e-9) s.done = true;
        if (s.sliding && mk > 0 && s.v > 0.3 && Math.random() < 0.12) {
          const d = s.x + BW / 2; s.events.push({ type: 'spark', pos: [d * cs, (RAMP - d) * sn, 0], strength: 0.2, speed: 0.5, color: '#fb923c', life: 0.4 });
        }
      },
      measures() {
        forces();
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 's', label: 'Distance down the ramp', value: s.x, unit: 'm', ref: RUN },
          { id: 'v', label: 'Velocity', value: s.v, unit: 'm/s', ref: 8 },
          { id: 'a', label: 'Acceleration', value: s.a, unit: 'm/s²', ref: 9.8 },
          { id: 'Fpar', label: 'Weight component along ramp', value: Fpar, unit: 'N', ref: 100 },
          { id: 'N', label: 'Normal force', value: N, unit: 'N', ref: 100 },
          { id: 'f', label: 'Friction force (up the ramp)', value: s.f, unit: 'N', ref: 100 },
          { id: 'Fnet', label: 'Net force down the ramp', value: Fpar - s.f, unit: 'N', ref: 100, hidden: true },
          { id: 'fsMax', label: 'Maximum static friction', value: fsMax, unit: 'N', ref: 100 },
          { id: 'thetaC', label: 'Critical angle', value: criticalAngle(p.muS), unit: '°', ref: 90 },
          { id: 'slide', label: 'Sliding (1) or held (0)', value: s.sliding ? 1 : 0, unit: '', hidden: true },
          { id: 'bottom', label: 'Reached the stop', value: s.bottom ? 1 : 0, unit: '', hidden: true },
        ];
      },
      energy() {
        return [
          { label: 'KE', value: 0.5 * p.m * s.v * s.v, color: '#fbbf24' },
          { label: 'PE (above stop)', value: p.m * g * (RUN - s.x) * sn, color: '#7dd3fc' },
          { label: 'Thermal (friction)', value: s.Q, color: '#f87171' },
          { label: 'Total', value: 0.5 * p.m * s.v * s.v + p.m * g * (RUN - s.x) * sn + s.Q, color: '#4ade80' },
        ];
      },
      scene() {
        const d = s.x + BW / 2, bh = 0.32 + 0.1 * Math.cbrt(p.m);       // contact-point distance from the top; block height
        const P = [d * cs, (RAMP - d) * sn, 0], n = [sn, cs], dn = [cs, -sn];
        const c = [P[0] + n[0] * bh / 2, P[1] + n[1] * bh / 2, 0];
        const k = 1.6 / (p.m * g); // force arrows: weight drawn 1.6 m long
        const sc = (u, F, z = 0) => [u[0] * F * k, u[1] * F * k, z];
        const fz = 0.75;
        return {
          bodies: [
            { id: 'block', shape: 'box', size: [BW, bh, 0.8], pos: c, rot: [0, 0, -th], color: s.sliding ? '#fbbf24' : '#f59e0b', metal: 0.2, label: `${p.m} kg` },
          ],
          vectors: [
            { id: 'W', from: [c[0], c[1], fz], vec: [0, -p.m * g * k, 0], color: '#7dd3fc', label: `mg = ${(p.m * g).toFixed(1)} N` },
            { id: 'Wpar', from: [c[0], c[1], fz], vec: sc(dn, Fpar), color: '#38bdf8', label: `mg·sinθ = ${Fpar.toFixed(1)} N` },
            { id: 'Wperp', from: [c[0], c[1], fz], vec: sc([-n[0], -n[1]], N), color: '#818cf8', label: `mg·cosθ = ${N.toFixed(1)} N` },
            { id: 'N', from: [P[0], P[1], -fz], vec: sc(n, N), color: '#a5b4fc', label: `N = ${N.toFixed(1)} N` },
            { id: 'f', from: [P[0], P[1], -fz], vec: sc([-dn[0], -dn[1]], s.f), color: '#f87171', label: s.f ? `${s.sliding ? 'fk' : 'fs'} = ${s.f.toFixed(1)} N` : '' },
            { id: 'net', from: [c[0] + n[0] * 0.5, c[1] + n[1] * 0.5, 0], vec: sc(dn, Fpar - s.f), color: '#4ade80', label: s.sliding ? `ΣF = ${(Fpar - s.f).toFixed(1)} N` : '' },
          ],
        };
      },
    };
  },
  equations(p, model) {
    const g = 9.8, th = deg(p.theta), mk = muKeff(p);
    const Fpar = p.m * g * Math.sin(th), N = p.m * g * Math.cos(th), fs = p.muS * N;
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    return [
      `F∥ = mg·sinθ = ${p.m} × 9.8 × sin ${p.theta}° = ${Fpar.toFixed(2)} N`,
      `N = mg·cosθ = ${p.m} × 9.8 × cos ${p.theta}° = ${N.toFixed(2)} N`,
      `fs,max = μs·N = ${p.muS} × ${N.toFixed(2)} = ${fs.toFixed(2)} N   (θc = tan⁻¹ ${p.muS} = ${criticalAngle(p.muS).toFixed(2)}°)`,
      m.slide
        ? `a = g(sinθ − μk·cosθ) = 9.8 × (${Math.sin(th).toFixed(4)} − ${mk} × ${Math.cos(th).toFixed(4)}) = ${m.a.toFixed(3)} m/s²`
        : `held: f = F∥ = ${Fpar.toFixed(2)} N ≤ fs,max = ${fs.toFixed(2)} N → a = 0`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r1 => r1.params.v0 === 0 && r1.final.slide === 0 && r1.final.s === 0 && runs.some(r2 => r2 !== r1 && r2.params.v0 === 0 && r2.params.muS === r1.params.muS && r2.final.s > 0 && r2.params.theta > r1.params.theta && r2.params.theta - r1.params.theta <= 1.0 + 1e-9)),
    ({ runs }) => runs.some(r => r.params.v0 > 0 && r.final.bottom === 1 && Math.abs(r.final.a) <= 0.05),
    ({ runs }) => runs.some(r => r.params.muK === 0.2 && r.params.muS >= 0.2 && r.params.v0 === 0 && r.final.bottom === 1 && Math.abs(r.final.t - 2) <= 0.05),
  ],
  evaluate(p) {
    const r = incline(p.m, p.theta, p.muS, muKeff(p));
    return { vars: { m: p.m, theta: p.theta, muS: p.muS, muK: muKeff(p) }, answer: r.slides ? r.a : 0, unit: 'm/s²', tol: 0.02 };
  },
};
