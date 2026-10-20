// Lab 18 — Magnetic Field Lab. Three experiments:
//  • particle: a charged particle in a uniform field B (along +y), integrated with RK4 under F = q v × B; the measured
//    radius and period are compared with the library cyclotronRadius / cyclotronPeriod (circle or helix);
//  • magnet: a bar magnet (point dipole) moves at constant speed along the axis of an N-turn coil; EMF = −N dΦ/dt;
//  • rails: a conducting rod slides on rails in a vertical field and is braked by its own induced current (Lenz).
import { rk4Step, cross3, cyclotronRadius, cyclotronPeriod, forceOnCharge, motionalEMF, C } from '../../physics/index.js';

const SUB = 4;               // RK4 sub-steps per harness step (particle)
const P_TMAX = 20, P_BOX = 8, P_YMAX = 6;
const MD = 20;               // magnet dipole moment, A·m² (a strong bar magnet / electromagnet)
const A_COIL = 0.5;          // coil radius, m
const X_START = -3, X_END = 3, COIL_Y = 1.2;
const L_RAIL = 1.0, M_ROD = 0.2, RAIL_END = 6, ROD_X0 = 0.5, R_TMAX = 8;

// Flux through ONE turn of a coil of radius a from a point dipole md on its axis at axial distance x.
export const dipoleFlux = (md, a, x) => C.mu0 * md * a * a / (2 * (a * a + x * x) ** 1.5);
// Analytic dΦ/dx for one turn (used only by tests and the equations panel; the model differentiates numerically).
export const dipoleFluxSlope = (md, a, x) => -1.5 * C.mu0 * md * a * a * x / (a * a + x * x) ** 2.5;

const opt = [{ value: 'particle', label: 'Charged particle in uniform B' }, { value: 'magnet', label: 'Magnet through a coil' }, { value: 'rails', label: 'Rod on rails (magnetic braking)' }];

export default {
  num: 18, unit: 17, sections: ['17.1', '17.2', '17.5', '17.6', '17.7', '17.9'],
  text: {
    title: 'Magnetic Field Lab',
    question: 'How does a magnetic field steer a moving charge, and how does a changing magnetic flux induce an EMF whose current opposes the change?',
    params: { mode: 'Experiment', B: 'Field strength B (particle, rails)', q: 'Particle charge q', m: 'Particle mass', v: 'Speed (particle, magnet, or rod push)', theta: 'Angle between v and B (particle)', N: 'Coil turns N (magnet)', R: 'Circuit resistance R (magnet, rails)' },
    options: { particle: 'Charged particle in uniform B', magnet: 'Magnet through a coil', rails: 'Rod on rails (magnetic braking)' },
    graph: ['EMF ε (V)', 'magnetic flux Φ (Wb)', 'induced current I (A)', 'speed (m/s)', 'path seen from above: z vs x (m)'],
    series: { emf: 'ε', Phi: 'Φ', I: 'I', spd: 'speed', z: 'z' },
    measures: { t: 'Time', x: 'x', y: 'Height y', z: 'z', spd: 'Speed', F: 'Magnetic force', rTh: 'Radius from m·v⊥/(|q|B)', rMeas: 'Measured radius', Tth: 'Period from 2πm/(|q|B)', Tmeas: 'Measured period', pitch: 'Helix pitch (rise per turn)', KE: 'Kinetic energy', Phi: 'Magnetic flux Φ (per turn × N for coil)', emf: 'EMF ε = −dΦ/dt', emfPk: 'Peak |EMF|', I: 'Induced current', Fdrag: 'Magnetic drag force (opposes motion)', Eth: 'Thermal energy in circuit', tHalf: 'Time to halve the rod speed', pos: 'Magnet / rod position' },
    predict: {
      prompt: 'A bar magnet, north pole first, passes completely through a coil at constant speed. Which describes the EMF in the coil?',
      choices: ['One pulse that keeps the same sign the whole time', 'A pulse of one sign as it enters, then a pulse of the opposite sign as it leaves', 'A constant EMF while the magnet moves', 'Zero, because the speed is constant'],
    },
    guided: [
      'Particle mode, θ = 90°: run with B = 1 T, q = 2 mC, m = 1 g, v = 2 m/s. Compare the measured radius and period with r = mv/(|q|B) and T = 2πm/(|q|B).',
      'Double the speed and run again. What happens to the radius? To the period? Explain why the period does not depend on speed.',
      'Set θ = 60°. The path becomes a helix. Show that the radius uses v⊥ = v·sinθ and that the pitch equals v∥·T = v·cosθ·T. Check that the kinetic energy never changes — why can the magnetic force do no work?',
      'Magnet mode: run at 1 m/s and 2 m/s. Compare the peak EMF and the time the pulse lasts. Use the flux graph to show ε = −N·dΦ/dt (the EMF is largest where Φ changes fastest, and zero at the centre).',
      'Watch the induced-field arrow at the coil as the magnet approaches and leaves. Use Lenz’s law to explain each direction, and explain why the drag force on the magnet always opposes its motion.',
      'Rails mode: give the rod a 3 m/s push with B = 1 T and R = 2 Ω. Show that ε = BLv, I = ε/R, F = BIL, and that the kinetic energy lost equals the thermal energy in the resistor.',
    ],
    challenges: [
      'Particle mode with θ = 90°: make the particle move in a circle of measured radius 1.50 m (±0.03 m).',
      'Particle mode: record two runs with the same q, m, B and θ = 90° but speeds that differ by a factor of at least 2, whose measured periods agree within 1 %.',
      'Rails mode: choose B and R so the rod’s speed falls to half its starting value in 1.00 s (±0.05 s).',
      'Magnet mode: record two runs with the same N and R where the second magnet speed is double the first, and show that the peak EMF doubles (ratio 2.00 ± 0.06).',
    ],
    evaluate: 'Before you run (particle experiment): a particle with q = {q} mC moves at {v} m/s at {theta}° to a uniform field B = {B} T. Calculate the magnitude of the magnetic force on it.',
    honors: {
      prompt: 'In rails mode the rod (m = 0.20 kg, L = 1.0 m) is pushed and released. Derive v(t) from Newton’s second law with the magnetic braking force, find the time to halve the speed, and predict how far the rod coasts in total. Test with B = 1 T, R = 2 Ω, v₀ = 3 m/s.',
      solution: 'ε = BLv, I = BLv/R, F = −BIL = −B²L²v/R, so m dv/dt = −(B²L²/R)v → v = v₀e^(−t/τ) with τ = mR/(B²L²) = 0.2 × 2/1 = 0.40 s. Half speed at t = τ ln 2 = 0.277 s. Total coasting distance = ∫v dt = v₀τ = 3 × 0.40 = 1.20 m, so the rod stops near x = 0.5 + 1.2 = 1.70 m. Energy check: ½mv₀² = 0.90 J all becomes thermal energy in R.',
    },
    assumptions: [
      'Particle: the field is uniform and points straight up (+y) inside the region; gravity, drag and radiation are neglected; speeds are non-relativistic. The motion is integrated with RK4 (4 sub-steps per 1/240 s step). Positive charges circle clockwise seen from above.',
      'Particle sizes are classroom-scale (mC, g) so the radius is metres and the period seconds; the same formulas hold for electrons and protons.',
      'Magnet: modeled as a point magnetic dipole of moment 20 A·m² moving at constant speed along the axis of a 0.50 m radius coil; the flux through one turn is Φ = μ₀m·a²/(2(a² + x²)^(3/2)). The model computes ε = −N·ΔΦ/Δt each step; the coil’s self-inductance is neglected, so I = ε/R.',
      'Rails: the rails are frictionless and resistance-free, the rod has mass 0.20 kg and length 1.0 m, and all the circuit resistance R is in the resistor at the end. Self-inductance is neglected; the rod motion is integrated with RK4.',
      'Signs: flux and EMF are positive for the coil axis +x (magnet) or +y (rails), counter-clockwise by the right-hand rule. Arrow lengths are scaled for visibility; their directions follow Lenz’s law exactly.',
      'Runs end after two particle periods (at most 20 s) or when the particle leaves the field region; when the magnet reaches x = +3 m; or after 8 s / at the end of the rails.',
    ],
  },
  params: [
    { id: 'mode', value: 'particle', options: opt },
    { id: 'B', min: 0.1, max: 2, step: 0.05, value: 1, unit: 'T' },
    { id: 'q', min: -5, max: 5, step: 0.5, value: 2, unit: 'mC' },
    { id: 'm', min: 0.5, max: 10, step: 0.5, value: 1, unit: 'g' },
    { id: 'v', min: 0.5, max: 5, step: 0.1, value: 2, unit: 'm/s' },
    { id: 'theta', min: 0, max: 90, step: 5, value: 90, unit: '°' },
    { id: 'N', min: 10, max: 1000, step: 10, value: 200, unit: 'turns' },
    { id: 'R', min: 0.5, max: 20, step: 0.1, value: 2, unit: 'Ω' },
  ],
  camera: { target: [0, 1, 0], dist: 12, free: [0.45, 0.55, 1] },
  view2d: { plane: 'xz', span: 10, cx: 0, cy: 0 },
  graph: {
    choices: [
      { label: 'EMF ε (V)', y: ['emf'], labels: ['emf'], yLabel: 'ε (V)' },
      { label: 'magnetic flux Φ (Wb)', y: ['Phi'], labels: ['Phi'], yLabel: 'Φ (Wb)' },
      { label: 'induced current I (A)', y: ['I'], labels: ['I'], yLabel: 'I (A)' },
      { label: 'speed (m/s)', y: ['spd'], labels: ['spd'], yLabel: 'speed (m/s)' },
      { label: 'path seen from above: z vs x (m)', x: 'x', xLabel: 'x (m)', y: ['z'], labels: ['z'], yLabel: 'z (m)' },
    ],
  },
  recordKeys: ['rTh', 'rMeas', 'Tth', 'Tmeas', 'pitch', 'emfPk', 'tHalf', 'Eth', 'KE'],
  decor: p => {
    const out = [{ shape: 'ground', size: 40, divisions: 40 }];
    const upArrows = (xs, zs, y0, h, col) => { for (const x of xs) for (const z of zs) out.push({ shape: 'line', pts: [[x, y0, z], [x, y0 + h, z]], color: col, opacity: 0.45 }, { shape: 'cone', r: 0.06, h: 0.16, pos: [x, y0 + h, z], color: col }); };
    if (p.mode === 'particle') {
      const g = [-4, -2, 0, 2, 4];
      upArrows(g, g, 0.02, P_YMAX - 0.2, '#38bdf8');
      out.push({ shape: 'label', text: `B = ${p.B} T (up)`, pos: [-4, P_YMAX + 0.2, -4], color: '#7dd3fc' }, { shape: 'label', text: 'start', pos: [0, -0.3, 0.3], color: '#e2e8f0' });
    } else if (p.mode === 'magnet') {
      for (let k = 0; k < 9; k++) out.push({ shape: 'torus', r: A_COIL, tube: 0.025, pos: [-0.24 + k * 0.06, COIL_Y, 0], rot: [0, Math.PI / 2, 0], color: '#b45309', metal: 0.7 });
      out.push({ shape: 'line', pts: [[X_START - 0.5, COIL_Y, 0], [X_END + 0.5, COIL_Y, 0]], color: '#475569', opacity: 0.6 },
        { shape: 'box', size: [0.12, COIL_Y - 0.5, 0.12], pos: [0, (COIL_Y - 0.5) / 2, 0.5], color: '#334155' },
        { shape: 'label', text: `coil: N = ${p.N}, a = ${A_COIL} m, R = ${p.R} Ω`, pos: [0, COIL_Y + 0.85, 0], color: '#fcd34d' },
        { shape: 'label', text: '+x axis (positive Φ)', pos: [X_END + 0.6, COIL_Y + 0.2, 0], color: '#94a3b8' });
    } else {
      out.push({ shape: 'box', size: [RAIL_END, 0.06, 0.06], pos: [RAIL_END / 2, 0.05, -L_RAIL / 2], color: '#cbd5e1', metal: 0.8 },
        { shape: 'box', size: [RAIL_END, 0.06, 0.06], pos: [RAIL_END / 2, 0.05, L_RAIL / 2], color: '#cbd5e1', metal: 0.8 },
        { shape: 'box', size: [0.18, 0.18, L_RAIL * 0.6], pos: [0, 0.1, 0], color: '#d6b98c' },
        { shape: 'line', pts: [[0, 0.06, -L_RAIL / 2], [0, 0.06, -L_RAIL * 0.3]], color: '#cbd5e1' }, { shape: 'line', pts: [[0, 0.06, L_RAIL * 0.3], [0, 0.06, L_RAIL / 2]], color: '#cbd5e1' },
        { shape: 'label', text: `R = ${p.R} Ω`, pos: [-0.4, 0.4, 0], color: '#fde68a' },
        { shape: 'label', text: `B = ${p.B} T (up)`, pos: [3, 1.4, -1.2], color: '#7dd3fc' },
        ...[1, 2, 3, 4, 5].map(i => ({ shape: 'label', text: `${i} m`, pos: [i, 0.1, L_RAIL / 2 + 0.35], color: '#94a3b8' })));
      upArrows([0.5, 1.5, 2.5, 3.5, 4.5, 5.5], [-0.9, 0, 0.9], 0.02, 1.0, '#38bdf8');
    }
    return out;
  },
  create(p) {
    const mode = p.mode;
    const s = { t: 0, done: false, events: [], emf: 0, I: 0, Phi: 0, emfPk: 0, Eth: 0, tHalf: NaN };
    const base = { get t() { return s.t; }, get done() { return s.done; }, events: s.events };
    const zero = { x: 0, y: 0, z: 0, spd: 0, F: 0, rTh: 0, rMeas: 0, Tth: 0, Tmeas: 0, pitch: 0, KE: 0, Phi: 0, emf: 0, emfPk: 0, I: 0, Fdrag: 0, Eth: 0, tHalf: 0, pos: 0 };
    const list = (vals, show) => {
      const meta = { t: ['Time', 's', 20], x: ['x', 'm', 8], y: ['Height y', 'm', 6], z: ['z', 'm', 8], spd: ['Speed', 'm/s', 5], F: ['Magnetic force', 'N', 0.05], rTh: ['Radius from m·v⊥/(|q|B)', 'm', 5], rMeas: ['Measured radius', 'm', 5], Tth: ['Period from 2πm/(|q|B)', 's', 20], Tmeas: ['Measured period', 's', 20], pitch: ['Helix pitch (rise per turn)', 'm', 6], KE: ['Kinetic energy', 'J', 1], Phi: ['Magnetic flux Φ (per turn × N for coil)', 'Wb', 0.01], emf: ['EMF ε = −dΦ/dt', 'V', 0.2], emfPk: ['Peak |EMF|', 'V', 0.2], I: ['Induced current', 'A', 1], Fdrag: ['Magnetic drag force (opposes motion)', 'N', 2], Eth: ['Thermal energy in circuit', 'J', 2], tHalf: ['Time to halve the rod speed', 's', 4], pos: ['Magnet / rod position', 'm', 6] };
      return [{ id: 't', label: 'Time', value: s.t, unit: 's', hidden: true }, ...Object.keys(meta).filter(k => k !== 't').map(k => ({ id: k, label: meta[k][0], value: vals[k] ?? 0, unit: meta[k][1], ref: meta[k][2], hidden: !show.includes(k) }))];
    };

    if (mode === 'particle') {
      const q = p.q * 1e-3, m = p.m * 1e-3, th = p.theta * Math.PI / 180, Bv = [0, p.B, 0];
      const vperp = p.v * Math.sin(th), vpar = p.v * Math.cos(th);
      const rTh = q ? cyclotronRadius(m, vperp, q, p.B) : Infinity, Tth = q ? cyclotronPeriod(m, q, p.B) : Infinity;
      const tEnd = q ? Math.min(2 * Tth, P_TMAX) : 6;
      let y = [0, 0.3, 0, vperp, vpar, 0];
      const deriv = Y => { const a = cross3([Y[3], Y[4], Y[5]], Bv); return [Y[3], Y[4], Y[5], q / m * a[0], q / m * a[1], q / m * a[2]]; };
      let phi = 0, lastAng = Math.atan2(y[5], y[3]), rMax = 0, Tmeas = NaN, pitch = NaN;
      const KE0 = 0.5 * m * p.v * p.v;
      const vals = () => {
        const sp = Math.hypot(y[3], y[4], y[5]), F = Math.abs(q) * Math.hypot(...cross3([y[3], y[4], y[5]], Bv));
        return { x: y[0], y: y[1], z: y[2], spd: sp, F, rTh, rMeas: rMax / 2, Tth, Tmeas, pitch, KE: 0.5 * m * sp * sp };
      };
      return {
        ...base,
        step(dt) {
          const h = dt / SUB;
          for (let i = 0; i < SUB; i++) {
            const prev = y, tPrev = s.t;
            y = rk4Step(deriv, y, h); s.t += h;
            const ang = Math.atan2(y[5], y[3]); let d = ang - lastAng; if (d > Math.PI) d -= 2 * Math.PI; if (d < -Math.PI) d += 2 * Math.PI;
            const phPrev = phi; phi += d; lastAng = ang;
            if (Number.isNaN(Tmeas) && Math.abs(phi) >= 2 * Math.PI) {
              const f = (2 * Math.PI - Math.abs(phPrev)) / (Math.abs(phi) - Math.abs(phPrev));
              Tmeas = tPrev + f * h; pitch = prev[1] + f * (y[1] - prev[1]) - 0.3;
              s.events.push({ type: 'spark', pos: [y[0], y[1], y[2]], strength: 0.3, speed: 0.5, color: '#a5f3fc', life: 0.5 });
            }
            rMax = Math.max(rMax, Math.hypot(y[0], y[2]));
          }
          if (s.t >= tEnd - 1e-9 || y[1] > P_YMAX || Math.abs(y[0]) > P_BOX || Math.abs(y[2]) > P_BOX) s.done = true;
        },
        measures() { return list(vals(), ['spd', 'F', 'rTh', 'rMeas', 'Tth', 'Tmeas', 'pitch', 'KE']); },
        energy() { const v = vals(); return [{ label: 'KE now', value: v.KE, color: '#fbbf24' }, { label: 'KE at start', value: KE0, color: '#94a3b8' }]; },
        scene() {
          const v = vals(), sp = v.spd || 1, Fv = cross3([y[3], y[4], y[5]], Bv).map(c => c * q), Fm = Math.hypot(...Fv) || 1;
          return {
            bodies: [{ id: 'pq', shape: 'sphere', r: 0.14, pos: [y[0], y[1], y[2]], color: q > 0 ? '#f87171' : q < 0 ? '#60a5fa' : '#e5e7eb', emissive: q > 0 ? '#ef4444' : '#3b82f6', glow: 0.7, trail: true, trailColor: '#fde68a', label: `q = ${p.q} mC` }],
            vectors: [
              { id: 'vv', from: [y[0], y[1], y[2]], vec: [y[3] / sp * 1.0, y[4] / sp * 1.0, y[5] / sp * 1.0], color: '#4ade80', label: `v = ${v.spd.toFixed(2)} m/s` },
              { id: 'FB', from: [y[0], y[1], y[2]], vec: v.F > 0 ? Fv.map(c => c / Fm * 0.9) : [0, 0, 0], color: '#f472b6', label: v.F > 0 ? `F = qv×B = ${v.F.toExponential(2)} N` : '' },
              { id: 'Bv', from: [y[0] + 0.4, y[1], y[2] + 0.4], vec: [0, 0.8, 0], color: '#38bdf8', label: 'B' },
            ],
          };
        },
      };
    }

    if (mode === 'magnet') {
      const N = p.N, R = p.R;
      let x = X_START; s.Phi = N * dipoleFlux(MD, A_COIL, x);
      const vals = () => ({ x, y: COIL_Y, z: 0, spd: p.v, Phi: s.Phi, emf: s.emf, emfPk: s.emfPk, I: s.I, Fdrag: s.emf * s.I / p.v, Eth: s.Eth, pos: x });
      return {
        ...base,
        step(dt) {
          let h = dt; if (x + p.v * h > X_END) h = (X_END - x) / p.v;
          if (h <= 0) { s.done = true; return; }
          x += p.v * h; s.t += h;
          const Phi = N * dipoleFlux(MD, A_COIL, x);
          s.emf = -(Phi - s.Phi) / h; s.Phi = Phi; s.I = s.emf / R;
          s.emfPk = Math.max(s.emfPk, Math.abs(s.emf)); s.Eth += s.emf * s.emf / R * h;
          if (x >= X_END - 1e-12) s.done = true;
        },
        measures() { return list(vals(), ['Phi', 'emf', 'emfPk', 'I', 'Fdrag', 'Eth', 'pos']); },
        energy() { return [{ label: 'Thermal in coil = work against drag', value: s.Eth, color: '#f87171' }]; },
        scene() {
          const sgn = Math.sign(s.I), mag = Math.min(1.6, Math.abs(s.I) / 0.02 * 1.6);
          const Bavg = dipoleFlux(MD, A_COIL, x) / (Math.PI * A_COIL * A_COIL); // magnet's average field through the coil
          return {
            bodies: [
              { id: 'magN', shape: 'box', size: [0.4, 0.3, 0.3], pos: [x + 0.2, COIL_Y, 0], color: '#dc2626', label: 'N' , labelOffset: [0.2, 0.3, 0] },
              { id: 'magS', shape: 'box', size: [0.4, 0.3, 0.3], pos: [x - 0.2, COIL_Y, 0], color: '#2563eb' },
              { id: 'coilglow', shape: 'torus', r: A_COIL + 0.04, tube: 0.02, pos: [0, COIL_Y, 0], rot: [0, Math.PI / 2, 0], color: '#f59e0b', emissive: '#f59e0b', glow: Math.min(2, Math.abs(s.I) / 0.01), label: `ε = ${(s.emf * 1000).toFixed(1)} mV, I = ${(s.I * 1000).toFixed(1)} mA` },
            ],
            vectors: [
              { id: 'Bm', from: [0, COIL_Y - 0.15, 0], vec: [Math.min(1.6, Bavg / 3.2e-5 * 1.6), 0, 0], color: '#38bdf8', label: 'magnet’s B (average over coil)' },
              { id: 'Bind', from: [0, COIL_Y + 0.15, 0], vec: [sgn * mag, 0, 0], color: '#f472b6', label: s.I ? 'induced B (Lenz)' : '' },
              { id: 'Icoil', from: [0, COIL_Y + A_COIL + 0.05, -sgn * mag * 0.3], vec: [0, 0, sgn * mag * 0.6], color: '#fbbf24', label: s.I ? 'I' : '' },
              { id: 'drag', from: [x, COIL_Y + 0.35, 0], vec: [-Math.min(1.5, s.emf * s.I / p.v / 2e-4 * 0.5), 0, 0], color: '#f87171', label: s.I ? 'drag' : '' },
            ],
          };
        },
      };
    }

    // rails
    const R = p.R, Bf = p.B, tau = M_ROD * R / (Bf * Bf * L_RAIL * L_RAIL);
    let y = [ROD_X0, p.v, 0]; // x, v, thermal energy
    s.Phi = Bf * L_RAIL * y[0];
    const deriv = Y => { const I = Bf * L_RAIL * Y[1] / R; return [Y[1], -I * L_RAIL * Bf / M_ROD, I * I * R]; };
    const KE0 = 0.5 * M_ROD * p.v * p.v;
    const vals = () => ({ x: y[0], y: 0, z: 0, spd: y[1], Phi: s.Phi, emf: s.emf, emfPk: s.emfPk, I: s.I, Fdrag: Math.abs(s.I) * L_RAIL * Bf, Eth: y[2], KE: 0.5 * M_ROD * y[1] * y[1], tHalf: Number.isNaN(s.tHalf) ? 0 : s.tHalf, pos: y[0] });
    return {
      ...base,
      step(dt) {
        const prev = y, tPrev = s.t;
        y = rk4Step(deriv, y, dt); s.t += dt;
        const Phi = Bf * L_RAIL * y[0];
        s.emf = -(Phi - s.Phi) / dt; s.Phi = Phi; s.I = s.emf / R; s.emfPk = Math.max(s.emfPk, Math.abs(s.emf));
        if (Number.isNaN(s.tHalf) && y[1] <= p.v / 2) {
          // interpolate in log(v) (exact for exponential decay within the step)
          const f = Math.log(prev[1] / (p.v / 2)) / Math.log(prev[1] / y[1]);
          s.tHalf = tPrev + f * dt;
        }
        if (y[0] >= RAIL_END - 0.1) { s.done = true; s.events.push({ type: 'impact', pos: [y[0], 0.2, 0], strength: 0.5, normal: 'x' }); }
        if (s.t >= R_TMAX - 1e-9) s.done = true;
      },
      measures() { return list(vals(), ['spd', 'Phi', 'emf', 'I', 'Fdrag', 'KE', 'Eth', 'tHalf', 'pos']); },
      energy() { const v = vals(); return [{ label: 'KE', value: v.KE, color: '#fbbf24' }, { label: 'Thermal in R', value: v.Eth, color: '#f87171' }, { label: 'KE + thermal', value: v.KE + v.Eth, color: '#4ade80' }]; },
      scene() {
        const v = vals(), cur = -Math.sign(s.I); // I < 0 (clockwise from above) ⇒ conventional current flows +z in the rod
        const kI = Math.min(0.8, Math.abs(s.I) * 0.15);
        return {
          bodies: [
            { id: 'rod', shape: 'cylinder', r: 0.05, h: L_RAIL + 0.3, pos: [y[0], 0.12, 0], rot: [Math.PI / 2, 0, 0], color: '#e5e7eb', metal: 0.8, emissive: '#f59e0b', glow: Math.min(1.5, Math.abs(s.I) / 2), label: `v = ${y[1].toFixed(2)} m/s` },
            { id: 'area', shape: 'box', size: [1, 0.01, L_RAIL], pos: [y[0] / 2, 0.03, 0], scale: [Math.max(0.01, y[0]), 1, 1], color: '#38bdf8', opacity: 0.18 },
          ],
          vectors: [
            { id: 'vel', from: [y[0], 0.45, 0], vec: [Math.min(1.5, 0.4 * y[1]), 0, 0], color: '#4ade80', label: 'v' },
            { id: 'Frod', from: [y[0], 0.3, -0.25], vec: [-Math.min(1.5, v.Fdrag * 0.5) * Math.sign(y[1] || 1), 0, 0], color: '#f87171', label: v.Fdrag > 1e-4 ? `F = BIL = ${v.Fdrag.toFixed(3)} N` : '' },
            { id: 'Irod', from: [y[0] + 0.15, 0.15, -cur * kI / 2], vec: [0, 0, cur * kI], color: '#fbbf24', label: Math.abs(s.I) > 1e-4 ? `I = ${Math.abs(s.I).toFixed(3)} A` : '' },
          ],
        };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'particle') {
      const vp = p.v * Math.sin(p.theta * Math.PI / 180);
      return [
        'F = q v × B (perpendicular to v, so |v| and KE stay constant)',
        `r = m·v⊥/(|q|B) = ${p.m / 1000} × ${vp.toFixed(3)} / (${Math.abs(p.q) / 1000} × ${p.B}) = ${m.rTh.toFixed(4)} m (measured ${m.rMeas.toFixed(4)} m)`,
        `T = 2πm/(|q|B) = 2π × ${p.m / 1000} / (${Math.abs(p.q) / 1000} × ${p.B}) = ${m.Tth.toFixed(4)} s (measured ${Number.isFinite(m.Tmeas) ? m.Tmeas.toFixed(4) : '—'} s)`,
        `F = |q|·v·B·sinθ = ${forceOnCharge(p.q / 1000, p.v, p.B, p.theta).toExponential(3)} N`,
        `pitch = v·cosθ·T = ${(p.v * Math.cos(p.theta * Math.PI / 180) * m.Tth).toFixed(3)} m`,
      ];
    }
    if (p.mode === 'magnet') {
      const x = m.pos;
      return [
        'Φ = N·μ₀·m·a²/(2(a² + x²)^(3/2)),  ε = −N·dΦ/dt = −N·(dΦ/dx)·v',
        `Φ = ${m.Phi.toExponential(3)} Wb at x = ${x.toFixed(2)} m`,
        `ε = −N(dΦ₁/dx)v = −${p.N} × (${dipoleFluxSlope(MD, A_COIL, x).toExponential(3)}) × ${p.v} = ${(-p.N * dipoleFluxSlope(MD, A_COIL, x) * p.v).toExponential(3)} V (model ${m.emf.toExponential(3)} V)`,
        `I = ε/R = ${m.emf.toExponential(3)} / ${p.R} = ${m.I.toExponential(3)} A`,
        'Lenz: the induced current makes a field that opposes the change in flux — the magnet is repelled as it approaches and attracted back as it leaves.',
      ];
    }
    return [
      'ε = −dΦ/dt = −B·L·v,  I = ε/R,  F = B·I·L (opposes v)',
      `|ε| = BLv = ${p.B} × ${L_RAIL} × ${m.spd.toFixed(3)} = ${motionalEMF(p.B, L_RAIL, m.spd).toFixed(4)} V`,
      `I = ${Math.abs(m.emf).toFixed(4)} / ${p.R} = ${Math.abs(m.I).toFixed(4)} A,  F = ${p.B} × ${Math.abs(m.I).toFixed(4)} × ${L_RAIL} = ${m.Fdrag.toFixed(4)} N`,
      `v = v₀e^(−t/τ), τ = mR/(B²L²) = ${M_ROD} × ${p.R}/(${p.B}² × ${L_RAIL}²) = ${(M_ROD * p.R / (p.B * p.B)).toFixed(4)} s`,
      `½mv₀² = ${(0.5 * M_ROD * p.v * p.v).toFixed(4)} J = KE ${m.KE.toFixed(4)} J + thermal ${m.Eth.toFixed(4)} J`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'particle' && r.params.theta === 90 && Number.isFinite(r.final.Tmeas) && Math.abs(r.final.rMeas - 1.5) <= 0.03),
    ({ runs }) => runs.some(a => runs.some(b => a !== b && a.params.mode === 'particle' && b.params.mode === 'particle' && a.params.theta === 90 && b.params.theta === 90
      && a.params.q === b.params.q && a.params.m === b.params.m && a.params.B === b.params.B && b.params.v >= 2 * a.params.v - 1e-9
      && Number.isFinite(a.final.Tmeas) && Number.isFinite(b.final.Tmeas) && Math.abs(b.final.Tmeas / a.final.Tmeas - 1) <= 0.01)),
    ({ runs }) => runs.some(r => r.params.mode === 'rails' && r.final.tHalf > 0 && Math.abs(r.final.tHalf - 1) <= 0.05),
    ({ runs }) => runs.some(a => runs.some(b => a !== b && a.params.mode === 'magnet' && b.params.mode === 'magnet' && a.params.N === b.params.N && a.params.R === b.params.R
      && Math.abs(b.params.v / a.params.v - 2) < 1e-9 && a.final.emfPk > 0 && Math.abs(b.final.emfPk / a.final.emfPk - 2) <= 0.06)),
  ],
  evaluate(p) {
    return { vars: { q: p.q, v: p.v, theta: p.theta, B: p.B }, answer: forceOnCharge(p.q * 1e-3, p.v, p.B, p.theta), unit: 'N', tol: 0.02 };
  },
};
