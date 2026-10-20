// Lab 11 — Pendulum and Spring Lab.
//  • pendulum: θ'' = −(g/L)·sinθ − (b/m)·θ' — the exact large-angle equation (no small-angle approximation),
//    integrated with fixed-step RK4; the measured period is compared with 2π√(L/g) and the exact AGM period;
//  • spring: m·x'' = −k·x − b·x' + F0·cos(ωd·t) on a frictionless track — damped, optionally driven (resonance).
// Work by the drive and heat from damping are integrated alongside the motion so the energy books balance.
import { rk4Step, pendulumPeriodSmall, pendulumPeriodExact, drivenAmplitude, C } from '../../physics/index.js';

const PIV = [0, 2.6, 0];     // pendulum pivot
const WALL = -1.6, XE = 0.3, YM = 0.35, BOX = 0.3; // spring: wall, equilibrium position, mass height, mass size
const SUB = 2;               // RK4 sub-steps per harness step
const deg = d => d * Math.PI / 180, todeg = r => r * 180 / Math.PI;
const tEnd = p => (p.mode === 'spring' && p.F0 > 0 ? 40 : 20);

export default {
  num: 11, unit: 10, sections: ['10.1', '10.2', '10.3', '10.4', '10.5', '10.6', '10.7', '10.8'],
  dt: 1 / 240, sampleEvery: 1 / 30,
  text: {
    title: 'Pendulum and Spring Lab',
    question: 'What sets the period of a pendulum and of a mass on a spring, when does the simple formula 2π√(L/g) stop working, and what happens when an oscillator is pushed at its natural frequency?',
    params: { mode: 'Oscillator', L: 'Pendulum length L', th0: 'Release angle θ₀', m: 'Mass m', k: 'Spring constant k', x0: 'Spring release displacement x₀', b: 'Damping coefficient b', F0: 'Drive force amplitude F₀ (spring)', wd: 'Drive angular frequency ωd (spring)' },
    options: { pendulum: 'Pendulum (exact large-angle motion)', spring: 'Mass on a spring (damped, driven)' },
    graph: ['displacement vs time (θ in °, x in m)', 'velocity vs time (ω in rad/s, v in m/s)', 'energy (J)', 'phase portrait: velocity vs displacement'],
    series: { disp: 'displacement', vel: 'velocity', KE: 'kinetic', PE: 'potential', E: 'mechanical total' },
    measures: { t: 'Time', theta: 'Angle θ', omega: 'Angular velocity ω', x: 'Displacement x', v: 'Velocity v', disp: 'Displacement', vel: 'Velocity', Tm: 'Measured period (latest cycle)', Tsmall: 'Small-angle period 2π√(L/g)', Texact: 'Exact period (AGM)', ratio: 'Measured ÷ small-angle period', Tsp: 'Predicted period 2π/ω_d', w0: 'Natural angular frequency √(k/m)', Apeak: 'Latest peak amplitude', Ass: 'Predicted steady-state amplitude', cycles: 'Cycles completed', fm: 'Measured frequency', KE: 'Kinetic energy', PE: 'Potential energy', E: 'Mechanical energy', Q: 'Heat from damping', W: 'Work by the drive' },
    predict: {
      prompt: 'A 1.0 m pendulum is released from 60° (no damping). Will its measured period match the small-angle formula T = 2π√(L/g) = 2.007 s?',
      choices: ['Yes — the period never depends on amplitude', 'No — it will be a few percent longer', 'No — it will be a few percent shorter', 'No — it will be about twice as long'],
    },
    guided: [
      'Pendulum, b = 0: run at θ₀ = 5°, 30°, 60°, 90°, and 150°. Record each run and plot the measured ÷ small-angle ratio against θ₀. Where does the small-angle formula fail by more than 1%?',
      'Check that the measured period agrees with the exact (AGM) period at every angle — the RK4 model never uses the small-angle approximation.',
      'Change the pendulum length by a factor of 4 at a small angle. By what factor does the period change? Change the mass — what happens?',
      'Switch to the spring. Double m, then double k, and compare the measured periods with 2π√(m/k). Open the energy graph: when is KE largest?',
      'Add damping (b = 0.3 kg/s). Measure two successive peaks and use A₂/A₁ = e^(−bT/2m) to recover b. Show that the heat bar grows as the mechanical energy falls.',
      'Set x₀ = 0, b = 0.2 kg/s, F₀ = 0.5 N, and sweep ωd from well below to well above √(k/m), recording the steady peak amplitude each time. Sketch the resonance curve.',
    ],
    challenges: [
      'Pendulum (no damping): find the release angle at which the measured period is exactly 10% longer than the small-angle prediction (ratio 1.100 ± 0.005).',
      'Spring (no damping, no drive): build an oscillator whose measured period is 1.00 s (±0.01 s).',
      'Resonance: drive a damped spring (b > 0) within 2% of its natural frequency and reach a steady peak amplitude of at least 90% of the resonance value F₀/(b·ω₀).',
    ],
    evaluate: 'Before you run: a pendulum of length {L} m is released from rest at {th0}° (no damping, g = 9.8 m/s²). Calculate its period, including the large-angle correction T ≈ 2π√(L/g)·(1 + θ₀²/16 + 11θ₀⁴/3072) with θ₀ in radians (accurate to better than 1% up to about 100°).',
    honors: {
      prompt: 'The spring model solves m·x″ + b·x′ + k·x = F₀cos(ωd·t). Derive the steady-state amplitude A(ωd), find the drive frequency that maximises it, and predict the peak amplitude for m = 1 kg, k = 20 N/m, b = 0.2 kg/s, F₀ = 0.5 N. Test your prediction.',
      solution: 'Try x = A·cos(ωd·t − δ): substitution gives A = F₀/√((k − mωd²)² + (bωd)²). The maximum is at ωd² = k/m − b²/(2m²), essentially ω₀ = √(k/m) = 4.472 rad/s for light damping, where A ≈ F₀/(bω₀) = 0.5/(0.2 × 4.472) = 0.559 m (exactly 0.559 m at the true peak 4.4699 rad/s). After the transient decays (time constant 2m/b = 10 s) the readout settles at this value.',
    },
    assumptions: [
      'The pendulum is a point bob on a rigid, massless rod (so release angles above 90° are possible) swinging about a frictionless pivot; g = 9.8 m/s².',
      'Damping is a linear drag force −b·v on the bob or block; there is no other friction or air resistance. With b = 0 mechanical energy is conserved.',
      'The spring is ideal (Hooke’s law, massless) on a frictionless horizontal track; the drive is a sinusoidal force F₀cos(ωd·t) applied directly to the block.',
      'Both oscillators are integrated with fixed-step fourth-order Runge–Kutta (two sub-steps of 1/480 s per frame); heat from damping and work by the drive are integrated alongside the motion.',
      'The measured period is the time between successive downward zero crossings (linearly interpolated); the peak amplitude is the most recent maximum of the displacement. The run lasts 20 s (40 s when driven).',
    ],
  },
  params: [
    { id: 'mode', value: 'pendulum', options: [{ value: 'pendulum', label: 'Pendulum (exact large-angle motion)' }, { value: 'spring', label: 'Mass on a spring (damped, driven)' }] },
    { id: 'L', min: 0.2, max: 2, step: 0.05, value: 1, unit: 'm' },
    { id: 'th0', min: 2, max: 170, step: 1, value: 60, unit: '°' },
    { id: 'm', min: 0.1, max: 5, step: 0.1, value: 1, unit: 'kg' },
    { id: 'k', min: 1, max: 100, step: 0.5, value: 20, unit: 'N/m' },
    { id: 'x0', min: 0, max: 0.5, step: 0.01, value: 0.2, unit: 'm' },
    { id: 'b', min: 0, max: 2, step: 0.02, value: 0, unit: 'kg/s' },
    { id: 'F0', min: 0, max: 5, step: 0.1, value: 0, unit: 'N' },
    { id: 'wd', min: 0.5, max: 15, step: 0.05, value: 4.5, unit: 'rad/s' },
  ],
  camera: { target: [0, 1.4, 0], dist: 5.8, free: [0.3, 0.25, 1] },
  view2d: { span: 5.6, cx: 0, cy: 1.4 },
  graph: {
    choices: [
      { label: 'displacement vs time', y: ['disp'], labels: ['disp'], yLabel: 'θ (°) or x (m)' },
      { label: 'velocity vs time', y: ['vel'], labels: ['vel'], yLabel: 'ω (rad/s) or v (m/s)' },
      { label: 'energy (J)', y: ['KE', 'PE', 'E'], labels: ['KE', 'PE', 'E'], yLabel: 'E (J)' },
      { label: 'phase portrait', x: 'disp', xLabel: 'displacement', y: ['vel'], labels: ['vel'], yLabel: 'velocity' },
    ],
  },
  recordKeys: ['Tm', 'Tsmall', 'Texact', 'ratio', 'Tsp', 'Apeak', 'Ass'],
  decor: p => {
    const out = [{ shape: 'ground', size: 30 }];
    if (p.mode === 'pendulum') {
      const n = 48, a = deg(p.th0);
      out.push(
        { shape: 'box', size: [1.6, 0.08, 0.35], pos: [0, PIV[1] + 0.06, 0], color: '#475569', metal: 0.4 },
        { shape: 'box', size: [0.08, PIV[1] + 0.06, 0.08], pos: [-0.8, (PIV[1] + 0.06) / 2, -0.15], color: '#334155' },
        { shape: 'box', size: [0.08, PIV[1] + 0.06, 0.08], pos: [0.8, (PIV[1] + 0.06) / 2, -0.15], color: '#334155' },
        { shape: 'line', pts: [PIV, [0, PIV[1] - p.L - 0.15, 0]], color: '#334155' },
        { shape: 'line', color: '#64748b', opacity: 0.6, pts: Array.from({ length: n + 1 }, (_, i) => { const q = -a + 2 * a * i / n; return [p.L * Math.sin(q), PIV[1] - p.L * Math.cos(q), -0.02]; }) },
        { shape: 'label', text: `θ₀ = ${p.th0}°`, pos: [p.L * Math.sin(a) + 0.15, PIV[1] - p.L * Math.cos(a), 0] },
      );
    } else {
      out.push(
        { shape: 'box', size: [0.12, 1.0, 0.8], pos: [WALL - 0.06, 0.5, 0], color: '#475569' },
        { shape: 'box', size: [3.4, 0.2, 0.5], pos: [0.1, 0.1, 0], color: '#334155' },
        { shape: 'line', pts: [[XE, YM + BOX / 2 + 0.05, 0.3], [XE, 0.2, 0.3]], color: '#4ade80' },
        { shape: 'label', text: 'equilibrium', pos: [XE, YM + BOX / 2 + 0.2, 0.3] },
      );
    }
    return out;
  },
  create(p) {
    const pend = p.mode === 'pendulum', g = C.g, TEND = tEnd(p);
    // state y = [q, q', W (work by drive), Q (heat), t]
    const f = pend
      ? y => [y[1], -(g / p.L) * Math.sin(y[0]) - (p.b / p.m) * y[1], 0, p.b * p.L * p.L * y[1] * y[1], 1]
      : y => { const Fd = p.F0 * Math.cos(p.wd * y[4]); return [y[1], (-p.k * y[0] - p.b * y[1] + Fd) / p.m, Fd * y[1], p.b * y[1] * y[1], 1]; };
    let y = [pend ? deg(p.th0) : p.x0, 0, 0, 0, 0];
    const s = { done: false, events: [], cross: [], peak: 0, peaks: 0 };
    const KEf = q => (pend ? 0.5 * p.m * (p.L * q[1]) ** 2 : 0.5 * p.m * q[1] * q[1]);
    const PEf = q => (pend ? p.m * g * p.L * (1 - Math.cos(q[0])) : 0.5 * p.k * q[0] * q[0]);
    const E0 = KEf(y) + PEf(y);
    const w0 = Math.sqrt(p.k / p.m), gam = p.b / (2 * p.m), wdamp = Math.sqrt(Math.max(0, w0 * w0 - gam * gam));
    return {
      get t() { return y[4]; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        if (s.done) return;
        const h = dt / SUB;
        for (let i = 0; i < SUB; i++) {
          const prev = y; y = rk4Step(f, y, h);
          if (prev[0] > 0 && y[0] <= 0) s.cross.push(prev[4] + h * prev[0] / (prev[0] - y[0])); // downward zero crossing
          if (prev[1] > 0 && y[1] <= 0) { s.peak = Math.max(prev[0], y[0]); s.peaks++; }        // a maximum of displacement
        }
        if (y[4] >= TEND - 1e-9) s.done = true;
      },
      measures() {
        const n = s.cross.length, Tm = n >= 2 ? s.cross[n - 1] - s.cross[n - 2] : 0;
        const Ts = pendulumPeriodSmall(p.L), Tx = pendulumPeriodExact(p.L, p.th0);
        const KE = KEf(y), PE = PEf(y);
        const ap = s.peaks ? s.peak : (pend ? deg(p.th0) : p.x0);
        return [
          { id: 't', label: 'Time', value: y[4], unit: 's', hidden: true },
          { id: 'theta', label: 'Angle θ', value: todeg(y[0]), unit: '°', ref: 180, hidden: !pend },
          { id: 'omega', label: 'Angular velocity ω', value: y[1], unit: 'rad/s', ref: 10, hidden: !pend },
          { id: 'x', label: 'Displacement x', value: y[0], unit: 'm', ref: 0.5, hidden: pend },
          { id: 'v', label: 'Velocity v', value: y[1], unit: 'm/s', ref: 3, hidden: pend },
          { id: 'disp', label: 'Displacement', value: pend ? todeg(y[0]) : y[0], unit: pend ? '°' : 'm', hidden: true },
          { id: 'vel', label: 'Velocity', value: y[1], unit: pend ? 'rad/s' : 'm/s', hidden: true },
          { id: 'Tm', label: 'Measured period (latest cycle)', value: Tm, unit: 's', ref: 6 },
          { id: 'Tsmall', label: 'Small-angle period 2π√(L/g)', value: Ts, unit: 's', ref: 6, hidden: !pend },
          { id: 'Texact', label: 'Exact period (AGM)', value: Tx, unit: 's', ref: 6, hidden: !pend },
          { id: 'ratio', label: 'Measured ÷ small-angle period', value: Tm ? Tm / Ts : 0, unit: '', ref: 2, hidden: !pend },
          { id: 'w0', label: 'Natural angular frequency √(k/m)', value: w0, unit: 'rad/s', ref: 30, hidden: pend },
          { id: 'Tsp', label: 'Predicted period 2π/ω_d', value: wdamp > 0 ? 2 * Math.PI / wdamp : 0, unit: 's', ref: 6, hidden: pend },
          { id: 'Apeak', label: 'Latest peak amplitude', value: pend ? todeg(ap) : ap, unit: pend ? '°' : 'm', ref: pend ? 180 : 0.5 },
          { id: 'Ass', label: 'Predicted steady-state amplitude', value: p.F0 > 0 ? drivenAmplitude(p.F0, p.m, p.k, p.b, p.wd) : 0, unit: 'm', ref: 0.5, hidden: pend || !(p.F0 > 0) },
          { id: 'cycles', label: 'Cycles completed', value: Math.max(0, n - 1), unit: '', ref: 20 },
          { id: 'fm', label: 'Measured frequency', value: Tm ? 1 / Tm : 0, unit: 'Hz', ref: 5 },
          { id: 'KE', label: 'Kinetic energy', value: KE, unit: 'J', hidden: true },
          { id: 'PE', label: 'Potential energy', value: PE, unit: 'J', hidden: true },
          { id: 'E', label: 'Mechanical energy', value: KE + PE, unit: 'J', ref: Math.max(1e-9, E0) },
          { id: 'Q', label: 'Heat from damping', value: y[3], unit: 'J', hidden: true },
          { id: 'W', label: 'Work by the drive', value: y[2], unit: 'J', hidden: true },
        ];
      },
      energy() {
        const out = [
          { label: 'KE', value: KEf(y), color: '#fbbf24' },
          { label: pend ? 'PE gravity' : 'PE spring', value: PEf(y), color: '#60a5fa' },
          { label: 'Heat (damping)', value: y[3], color: '#f87171' },
        ];
        if (!pend) out.push({ label: 'Work by drive', value: y[2], color: '#4ade80' });
        return out;
      },
      scene() {
        if (pend) {
          const q = y[0], bob = [PIV[0] + p.L * Math.sin(q), PIV[1] - p.L * Math.cos(q), 0], rb = 0.06 + 0.05 * Math.cbrt(p.m);
          const vt = p.L * y[1];
          return {
            bodies: [
              { id: 'rod', shape: 'cylinder', r: 0.012, h: p.L, pos: [(PIV[0] + bob[0]) / 2, (PIV[1] + bob[1]) / 2, 0], rot: [0, 0, q], color: '#cbd5e1', metal: 0.7 },
              { id: 'pivot', shape: 'sphere', r: 0.04, pos: PIV, color: '#94a3b8', metal: 0.8 },
              { id: 'bob', shape: 'sphere', r: rb, pos: bob, color: '#fbbf24', metal: 0.5, trail: true, trailColor: '#fde68a', label: `${todeg(q).toFixed(1)}°` },
            ],
            vectors: [
              { id: 'v', from: bob, vec: [vt * Math.cos(q) * 0.25, vt * Math.sin(q) * 0.25, 0], color: '#4ade80', label: `v = ${Math.abs(vt).toFixed(2)} m/s` },
              { id: 'mg', from: bob, vec: [0, -Math.min(1.2, p.m * g * 0.04), 0], color: '#7dd3fc', label: 'mg' },
              { id: 'Ft', from: bob, vec: [-p.m * g * Math.sin(q) * Math.cos(q) * 0.04, -p.m * g * Math.sin(q) * Math.sin(q) * 0.04, 0], color: '#f472b6', label: 'restoring −mg·sinθ' },
            ],
          };
        }
        const xc = XE + y[0], left = xc - BOX / 2, N = 14, seg = N * 12;
        const coil = Array.from({ length: seg + 1 }, (_, i) => { const u = i / seg, ph = 2 * Math.PI * N * u, r = i < 6 || i > seg - 6 ? 0 : 0.1; return [WALL + (left - WALL) * u, YM + r * Math.sin(ph), r * Math.cos(ph)]; });
        const Fs = -p.k * y[0], Fd = p.F0 * Math.cos(p.wd * y[4]), kf = 0.06;
        return {
          bodies: [{ id: 'block', shape: 'box', size: [BOX, BOX, BOX], pos: [xc, YM, 0], color: '#fbbf24', metal: 0.3, label: `${p.m} kg` }],
          lines: [{ id: 'spring', pts: coil, color: '#cbd5e1' }],
          vectors: [
            { id: 'Fs', from: [xc, YM + BOX / 2 + 0.05, 0], vec: [Math.max(-1.5, Math.min(1.5, Fs * kf)), 0, 0], color: '#60a5fa', label: `kx = ${Math.abs(Fs).toFixed(2)} N` },
            { id: 'Fd', from: [xc, YM - 0.05, BOX / 2 + 0.05], vec: [Math.max(-1.5, Math.min(1.5, Fd * kf * 3)), 0, 0], color: '#4ade80', label: p.F0 > 0 ? 'drive' : '' },
            { id: 'v', from: [xc, YM + BOX / 2 + 0.3, 0], vec: [y[1] * 0.4, 0, 0], color: '#fbbf24', label: `v = ${y[1].toFixed(2)} m/s` },
          ],
        };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'pendulum') {
      return [
        'θ″ = −(g/L)·sinθ − (b/m)·θ′   (solved with RK4 — no small-angle approximation)',
        `T₀ = 2π√(L/g) = 2π√(${p.L}/9.8) = ${m.Tsmall.toFixed(4)} s`,
        `T_exact = T₀ / AGM(1, cos(θ₀/2)) = ${m.Texact.toFixed(4)} s  (θ₀ = ${p.th0}°)`,
        `T_measured = ${m.Tm ? m.Tm.toFixed(4) + ' s → ratio ' + m.ratio.toFixed(4) : '— (wait for two zero crossings)'}`,
        `E = ½m(Lω)² + mgL(1 − cosθ) = ${m.E.toFixed(4)} J`,
      ];
    }
    return [
      'm·x″ = −k·x − b·x′ + F₀·cos(ωd·t)',
      `ω₀ = √(k/m) = √(${p.k}/${p.m}) = ${m.w0.toFixed(4)} rad/s → T = 2π√(m/k) = ${(2 * Math.PI / m.w0).toFixed(4)} s`,
      p.b > 0 ? `damped: ω_d = √(ω₀² − (b/2m)²) → T = ${m.Tsp.toFixed(4)} s;  amplitude ∝ e^(−bt/2m), 2m/b = ${(2 * p.m / p.b).toFixed(2)} s` : 'undamped: E = ½kx² + ½mv² is constant',
      p.F0 > 0 ? `steady state: A = F₀/√((k − mωd²)² + (bωd)²) = ${m.Ass.toFixed(4)} m  (ωd/ω₀ = ${(p.wd / m.w0).toFixed(3)})` : `measured T = ${m.Tm ? m.Tm.toFixed(4) + ' s' : '—'}`,
      `latest peak = ${m.Apeak.toFixed(4)} m;  E = ${m.E.toFixed(4)} J`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'pendulum' && r.params.b === 0 && r.final.Tm > 0 && Math.abs(r.final.ratio - 1.1) <= 0.005),
    ({ runs }) => runs.some(r => r.params.mode === 'spring' && r.params.b === 0 && r.params.F0 === 0 && r.final.Tm > 0 && Math.abs(r.final.Tm - 1) <= 0.01),
    ({ runs }) => runs.some(r => {
      const q = r.params; if (q.mode !== 'spring' || !(q.b > 0) || !(q.F0 > 0)) return false;
      const w0 = Math.sqrt(q.k / q.m);
      return Math.abs(q.wd / w0 - 1) <= 0.02 && r.final.Apeak >= 0.9 * q.F0 / (q.b * w0);
    }),
  ],
  evaluate(p) {
    return { vars: { L: p.L, th0: p.th0 }, answer: pendulumPeriodExact(p.L, p.th0), unit: 's', tol: 0.015 };
  },
};
