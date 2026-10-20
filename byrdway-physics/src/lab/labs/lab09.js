// Lab 9 — Orbital Mechanics Lab. A satellite launched from altitude h above a spherical planet moves under
// Newtonian gravity alone. The two-body equations are integrated with fixed-step RK4 (planet fixed, satellite
// mass negligible). The period is measured by counting full revolutions and compared with Kepler's third law.
import { rk4Step, orbitalSpeed, orbitalPeriod, escapeSpeed, C } from '../../physics/index.js';

const R = C.Re;              // planet radius (m) — kept at Earth's radius for every mass setting
const MSAT = 1000;           // satellite mass (kg), used only for the energy bars
const SCALE = 1e6;           // metres per 3D scene unit
const PLAY = 12;             // real seconds of playback per (capped) orbit at 1×
const FAR = 15 * R;          // the run ends when the satellite leaves this radius
const deg = d => d * Math.PI / 180;

// Launch geometry and the time compression used for playback (deterministic for given parameters).
function launch(p) {
  const GM = C.G * p.M * C.Me, r0 = R + p.h * 1000, vc = orbitalSpeed(p.M * C.Me, r0), v0 = p.f * vc;
  const eps = v0 * v0 / 2 - GM / r0, a = eps < 0 ? -GM / (2 * eps) : Infinity;
  const Tc = orbitalPeriod(p.M * C.Me, r0), Tk = Number.isFinite(a) ? 2 * Math.PI * Math.sqrt(a ** 3 / GM) : Infinity;
  const W = Math.min(Tk, 6 * Tc) / PLAY; // physical seconds simulated per real second
  return { GM, r0, vc, v0, eps, a, Tc, Tk, W, tMax: 30 * W, hMax: Tc / 2000, vesc: escapeSpeed(p.M * C.Me, r0) };
}

export default {
  num: 9, unit: 8, sections: ['8.5', '8.6', '8.7', '8.8', '8.9'],
  dt: 1 / 120, sampleEvery: 30, space: true, scale: SCALE,
  text: {
    title: 'Orbital Mechanics Lab',
    question: 'How does a satellite’s launch speed decide whether it circles, follows an ellipse, or escapes — and how does its orbital period depend on the size of its orbit?',
    params: { h: 'Launch altitude', f: 'Launch speed ÷ circular speed', phi: 'Launch angle above horizontal', M: 'Planet mass (Earth masses)' },
    graph: ['altitude (km)', 'speed (km/s)', 'energy per kg (MJ/kg)', 'orbit path y vs x (km)'],
    series: { alt: 'altitude', v: 'speed', KEs: 'kinetic', Us: 'potential', Es: 'total', Y: 'path' },
    measures: { t: 'Time (s)', tmin: 'Time', alt: 'Altitude', v: 'Speed', g: 'Local gravity g', Es: 'Total energy per kg', a: 'Semi-major axis (from energy)', ecc: 'Eccentricity', revs: 'Revolutions', Tm: 'Measured period', Tk: 'Kepler period 2π√(a³/GM)', kr: 'Kepler ratio T²GM/(4π²a³)', v0: 'Launch speed', vc: 'Circular speed at launch', vesc: 'Escape speed at launch', X: 'x', Y: 'y', KEs: 'Kinetic energy per kg', Us: 'Potential energy per kg', rmin: 'Closest distance from centre', rmax: 'Farthest distance from centre', escaped: 'Escaped', crashed: 'Crashed', amin: 'Semi-major axis (measured)' },
    predict: {
      prompt: 'A satellite is launched horizontally at 1.20 × the circular-orbit speed instead of exactly the circular speed. Compared with the circular orbit, its orbital period will be…',
      choices: ['The same — period depends only on the planet', 'Longer — the orbit becomes a bigger ellipse', 'Shorter — it moves faster', 'There is no period — it escapes'],
    },
    guided: [
      'Keep f = 1.00 and the launch angle at 0°. Run and confirm the trail is a circle: the speed and altitude graphs stay flat and the eccentricity reads ≈ 0.',
      'Run with f = 0.97, 1.10, and 1.25 (below about 0.96 the perigee dips under the surface). For each, note the closest and farthest distances and the measured period. Where on the ellipse is the satellite fastest?',
      'For each bound run, compare the measured period with the Kepler period 2π√(a³/GM). Check that the Kepler ratio T²GM/(4π²a³) stays at 1.000.',
      'Open the energy graph. Kinetic and potential energy trade back and forth; explain why the total stays constant and why it is negative for every closed orbit.',
      'Raise f until the satellite no longer returns. Find the smallest f that escapes and compare v₀ with the escape speed √(2GM/r) — what is the ratio to the circular speed?',
      'Double the planet mass and repeat a circular launch. By what factor does the circular speed change? The period?',
    ],
    challenges: [
      'Put a satellite into a circular orbit: record a run that completes at least one revolution with eccentricity below 0.01.',
      'Test Kepler’s third law: record two complete orbits around the same planet whose measured semi-major axes differ by at least a factor of 1.5, with measured period ratio equal to (a ratio)^1.5 within 1%.',
      'Escape with the least possible launch speed: record a run that escapes (total energy ≥ 0) with v₀ no more than 2% above the escape speed.',
    ],
    evaluate: 'Before you run: a satellite is in a circular orbit at altitude {h} km above a planet of {M} Earth masses (Earth mass 5.972 × 10²⁴ kg, radius 6371 km, G = 6.674 × 10⁻¹¹ N·m²/kg²). Calculate its orbital period in minutes. (Check it with f = 1.00.)',
    honors: {
      prompt: 'A horizontal launch at f × the circular speed puts the launch point at perigee. Use conservation of energy and angular momentum to predict the apogee distance in terms of r₀ and f, then predict the apogee altitude for h = 1000 km, f = 1.20 on Earth and test it (closest/farthest distance readouts).',
      solution: 'Angular momentum: r₀v₀ = r_a v_a. Energy: v₀²/2 − GM/r₀ = v_a²/2 − GM/r_a. With v₀² = f²GM/r₀ these give r_a = r₀ f²/(2 − f²). For r₀ = 7371 km and f = 1.20: r_a = 7371 × 1.44/0.56 = 18 954 km, an apogee altitude of 12 583 km. The orbit is bound only while 2 − f² > 0, i.e. f < √2 — the escape condition v₀ ≥ √2·v_c.',
    },
    assumptions: [
      'Only Newtonian gravity from a spherically symmetric planet acts (it pulls as a point mass at its centre); there is no atmosphere, drag, thrust after launch, Moon, or Sun.',
      'The satellite’s mass is negligible compared with the planet’s, so the planet stays fixed. Changing the planet mass keeps its radius at 6371 km.',
      'The motion is integrated with a fixed-step fourth-order Runge–Kutta method; total energy is conserved to better than one part in a million over a run.',
      'Time is compressed for viewing: one real second shows many minutes of orbit (the graphs and readouts use true time). The run ends after two revolutions, on impact, beyond 15 planet radii, or after 30 s of playback.',
      'The measured period is the time for the polar angle to sweep 360°; the measured semi-major axis is (closest + farthest distance)/2 over the first revolution.',
      'The satellite and its panels are drawn far larger than scale so they can be seen. The impact flash is a visual effect only.',
    ],
  },
  params: [
    { id: 'h', min: 200, max: 5000, step: 50, value: 1000, unit: 'km' },
    { id: 'f', min: 0.7, max: 1.6, step: 0.01, value: 1, unit: '' },
    { id: 'phi', min: -30, max: 30, step: 1, value: 0, unit: '°' },
    { id: 'M', min: 0.5, max: 4, step: 0.5, value: 1, unit: '' },
  ],
  camera: { target: [0, 0, 0], dist: 30, free: [0.25, 1, 0.75], followId: null },
  view2d: { plane: 'xz', span: 6e7, cx: 0, cy: 0 },
  graph: {
    choices: [
      { label: 'altitude (km)', x: 'tmin', xLabel: 't (min)', y: ['alt'], labels: ['alt'], yLabel: 'altitude (km)' },
      { label: 'speed (km/s)', x: 'tmin', xLabel: 't (min)', y: ['v'], labels: ['v'], yLabel: 'v (km/s)' },
      { label: 'energy per kg (MJ/kg)', x: 'tmin', xLabel: 't (min)', y: ['KEs', 'Us', 'Es'], labels: ['KEs', 'Us', 'Es'], yLabel: 'E/m (MJ/kg)' },
      { label: 'orbit path y vs x (km)', x: 'X', xLabel: 'x (km)', y: ['Y'], labels: ['Y'], yLabel: 'y (km)' },
    ],
  },
  recordKeys: ['v0', 'ecc', 'rmin', 'rmax', 'Tm', 'Tk', 'Es'],
  decor: p => {
    const r0 = R + p.h * 1000, n = 96;
    const ring = (r, color, opacity) => ({ shape: 'line', color, opacity, pts: Array.from({ length: n + 1 }, (_, i) => [r * Math.cos(2 * Math.PI * i / n), 0, -r * Math.sin(2 * Math.PI * i / n)]) });
    return [
      { shape: 'stars' },
      { shape: 'sphere', r: R, pos: [0, 0, 0], color: '#1d4ed8', rough: 0.8 },
      { shape: 'sphere', r: R * 1.025, pos: [0, 0, 0], color: '#7dd3fc', opacity: 0.18 },
      { shape: 'torus', r: R * 1.001, tube: 0.04 * SCALE, pos: [0, 0, 0], rot: [Math.PI / 2, 0, 0], color: '#22c55e' },
      ring(r0, '#475569', 0.5),
      ring(FAR, '#334155', 0.35),
      { shape: 'label', text: `launch: ${p.h} km`, pos: [r0, 1.2 * SCALE, 0] },
      { shape: 'label', text: `planet ${p.M} M⊕`, pos: [0, R + 1.5 * SCALE, 0] },
    ];
  },
  create(p) {
    const L = launch(p), GM = L.GM, ph = deg(p.phi);
    // state [X, Y, VX, VY] in the orbital plane; the 3D scene maps (X, Y) → (x, −z) so motion is counter-clockwise from above
    let y = [L.r0, 0, L.v0 * Math.sin(ph), L.v0 * Math.cos(ph)];
    const s = { t: 0, done: false, events: [], ang: 0, revT: [], rmin: L.r0, rmax: L.r0, rmin1: 0, rmax1: 0, crashed: false, escaped: false };
    const f = q => { const r3 = Math.hypot(q[0], q[1]) ** 3; return [q[2], q[3], -GM * q[0] / r3, -GM * q[1] / r3]; };
    const st = () => {
      const r = Math.hypot(y[0], y[1]), v = Math.hypot(y[2], y[3]), eps = v * v / 2 - GM / r;
      const rv = y[0] * y[2] + y[1] * y[3], k = v * v - GM / r;
      const ex = (k * y[0] - rv * y[2]) / GM, ey = (k * y[1] - rv * y[3]) / GM;
      return { r, v, eps, ecc: Math.hypot(ex, ey), a: eps < 0 ? -GM / (2 * eps) : 0 };
    };
    const model = {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      get state() { return y.slice(); },
      step(dt) {
        if (s.done) return;
        const H = dt * L.W, n = Math.max(1, Math.ceil(H / L.hMax)), h = H / n;
        for (let i = 0; i < n && !s.done; i++) {
          const a0 = Math.atan2(y[1], y[0]);
          y = rk4Step(f, y, h); s.t += h;
          let da = Math.atan2(y[1], y[0]) - a0;
          if (da > Math.PI) da -= 2 * Math.PI; else if (da < -Math.PI) da += 2 * Math.PI;
          const prev = s.ang; s.ang += da;
          const r = Math.hypot(y[0], y[1]);
          s.rmin = Math.min(s.rmin, r); s.rmax = Math.max(s.rmax, r);
          const k = s.revT.length + 1;
          if (s.ang >= 2 * Math.PI * k) { // a revolution is completed inside this sub-step: interpolate the crossing time
            s.revT.push(s.t - h + h * (2 * Math.PI * k - prev) / da);
            if (k === 1) { s.rmin1 = s.rmin; s.rmax1 = s.rmax; }
            if (k === 2) s.done = true;
          }
          if (r <= R) {
            s.crashed = true; s.done = true; y = [y[0] * R / r, y[1] * R / r, 0, 0];
            s.events.push({ type: 'impact', pos: [y[0], 0, -y[1]], strength: 1.6, color: '#fb923c', normal: 'y' });
          } else if (r >= FAR) { s.done = true; }
          if (st().eps >= 0) s.escaped = true;
        }
        if (s.t >= L.tMax) s.done = true;
      },
      measures() {
        const q = st(), T1 = s.revT.length ? (s.revT.length === 2 ? s.revT[1] / 2 : s.revT[0]) : 0;
        const am = s.rmin1 ? (s.rmin1 + s.rmax1) / 2 : 0;
        return [
          { id: 't', label: 'Time (s)', value: s.t, unit: 's', hidden: true },
          { id: 'tmin', label: 'Time', value: s.t / 60, unit: 'min', ref: 300 },
          { id: 'alt', label: 'Altitude', value: (q.r - R) / 1000, unit: 'km', ref: 40000 },
          { id: 'v', label: 'Speed', value: q.v / 1000, unit: 'km/s', ref: 15 },
          { id: 'g', label: 'Local gravity g', value: GM / (q.r * q.r), unit: 'm/s²', ref: 40 },
          { id: 'Es', label: 'Total energy per kg', value: q.eps / 1e6, unit: 'MJ/kg', ref: 60 },
          { id: 'a', label: 'Semi-major axis (from energy)', value: q.a / 1000, unit: 'km', ref: 60000 },
          { id: 'ecc', label: 'Eccentricity', value: q.ecc, unit: '', ref: 1 },
          { id: 'revs', label: 'Revolutions', value: Math.max(0, s.ang) / (2 * Math.PI), unit: '', ref: 2 },
          { id: 'Tm', label: 'Measured period', value: T1 / 60, unit: 'min', ref: 1500 },
          { id: 'Tk', label: 'Kepler period 2π√(a³/GM)', value: Number.isFinite(L.Tk) ? L.Tk / 60 : 0, unit: 'min', ref: 1500 },
          { id: 'kr', label: 'Kepler ratio T²GM/(4π²a³)', value: T1 && am ? T1 * T1 * GM / (4 * Math.PI ** 2 * am ** 3) : 0, unit: '', ref: 1 },
          { id: 'amin', label: 'Semi-major axis (measured)', value: am / 1000, unit: 'km', ref: 60000, hidden: true },
          { id: 'v0', label: 'Launch speed', value: L.v0 / 1000, unit: 'km/s', ref: 15 },
          { id: 'vc', label: 'Circular speed at launch', value: L.vc / 1000, unit: 'km/s', ref: 15, hidden: true },
          { id: 'vesc', label: 'Escape speed at launch', value: L.vesc / 1000, unit: 'km/s', ref: 15, hidden: true },
          { id: 'rmin', label: 'Closest distance from centre', value: s.rmin / 1000, unit: 'km', ref: 60000 },
          { id: 'rmax', label: 'Farthest distance from centre', value: s.rmax / 1000, unit: 'km', ref: 60000 },
          { id: 'KEs', label: 'Kinetic energy per kg', value: q.v * q.v / 2e6, unit: 'MJ/kg', hidden: true },
          { id: 'Us', label: 'Potential energy per kg', value: -GM / q.r / 1e6, unit: 'MJ/kg', hidden: true },
          { id: 'X', label: 'x', value: y[0] / 1000, unit: 'km', hidden: true },
          { id: 'Y', label: 'y', value: y[1] / 1000, unit: 'km', hidden: true },
          { id: 'escaped', label: 'Escaped', value: s.escaped ? 1 : 0, unit: '', hidden: true },
          { id: 'crashed', label: 'Crashed', value: s.crashed ? 1 : 0, unit: '', hidden: true },
        ];
      },
      energy() {
        const q = st();
        return [
          { label: 'KE', value: 0.5 * MSAT * q.v * q.v, color: '#fbbf24' },
          { label: 'U = −GMm/r', value: -GM * MSAT / q.r, color: '#60a5fa' },
          { label: 'Total E', value: MSAT * q.eps, color: '#4ade80' },
        ];
      },
      scene() {
        const q = st(), pos = [y[0], 0, -y[1]], kv = 900, kg = 7e5;
        const ux = y[0] / q.r, uy = y[1] / q.r, ga = GM / (q.r * q.r);
        return {
          bodies: [
            { id: 'sat', shape: 'sphere', r: 0.35 * SCALE, pos, color: '#fbbf24', metal: 0.6, emissive: '#f59e0b', glow: 0.35, trail: true, trailColor: s.escaped ? '#f87171' : '#fde68a', label: s.crashed ? 'impact' : `${(q.v / 1000).toFixed(2)} km/s`, labelOffset: [0, 0.9 * SCALE, 0] },
            { id: 'panel', shape: 'box', size: [1.6 * SCALE, 0.05 * SCALE, 0.4 * SCALE], pos, rot: [0, Math.atan2(y[1], y[0]), 0], color: '#38bdf8', metal: 0.5 },
          ],
          vectors: [
            { id: 'vel', from: pos, vec: [y[2] * kv, 0, -y[3] * kv], color: '#4ade80', label: `v = ${(q.v / 1000).toFixed(2)} km/s` },
            { id: 'grav', from: pos, vec: [-ux * ga * kg, 0, uy * ga * kg], color: '#f87171', label: `g = ${ga.toFixed(2)} m/s²` },
          ],
        };
      },
    };
    return model;
  },
  equations(p, model) {
    const L = launch(p), m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    return [
      `g = GM/r² = ${m.g.toFixed(3)} m/s² at altitude ${m.alt.toFixed(0)} km`,
      `v_c = √(GM/r₀) = ${(L.vc / 1000).toFixed(3)} km/s → v₀ = ${p.f} × v_c = ${(L.v0 / 1000).toFixed(3)} km/s`,
      `E/m = v²/2 − GM/r = ${m.Es.toFixed(4)} MJ/kg (launch: ${(L.eps / 1e6).toFixed(4)} MJ/kg)`,
      L.eps < 0 ? `a = −GM/(2E/m) = ${(L.a / 1000).toFixed(0)} km → T = 2π√(a³/GM) = ${(L.Tk / 60).toFixed(2)} min` : 'E/m ≥ 0 → the orbit is unbound (parabola or hyperbola): the satellite escapes',
      `measured T = ${m.Tm ? m.Tm.toFixed(2) + ' min' : '— (complete a revolution)'}`,
      `v_esc = √(2GM/r₀) = √2 · v_c = ${(L.vesc / 1000).toFixed(3)} km/s`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.final.Tm > 0 && r.final.revs >= 1 && r.final.ecc < 0.01 && !r.final.crashed),
    ({ runs }) => runs.some(r1 => runs.some(r2 => r1 !== r2 && r1.params.M === r2.params.M && r1.final.Tm > 0 && r2.final.Tm > 0 && r1.final.amin > 0 && r2.final.amin > 0 &&
      r2.final.amin / r1.final.amin >= 1.5 && Math.abs((r2.final.Tm / r1.final.Tm) / (r2.final.amin / r1.final.amin) ** 1.5 - 1) <= 0.01)),
    ({ runs }) => runs.some(r => r.final.escaped === 1 && r.final.v0 >= r.final.vesc && r.final.v0 <= 1.02 * r.final.vesc),
  ],
  evaluate(p) {
    return { vars: { h: p.h, M: p.M }, answer: orbitalPeriod(p.M * C.Me, R + p.h * 1000) / 60, unit: 'min', tol: 0.02 };
  },
};
