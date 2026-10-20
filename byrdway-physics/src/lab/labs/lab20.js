// Lab 20 — Relativity Explorer. A ship carrying a light clock flies at constant speed βc from Earth to a star D
// light-years away and straight back (the twin trip). Everything is computed in the Earth frame:
//   Earth time tE, ship position x(tE), ship proper time τ = tE/γ, Earth-measured ship length L = L0/γ,
//   crew-measured distance to the star D' = D/γ, and the light-clock photon whose path in the Earth frame is the
//   familiar zig-zag (it moves at c along the diagonal; the ship-frame tick is 2h/c).
import { C, gamma, dilatedTime, contractedLength, relKE, restEnergy } from '../../physics/index.js';

const S = 20;          // scene distance Earth → star (scene units); 1 ly = S/D scene units
const T_ANIM = 12;     // the whole round trip is shown in 12 s of animation (time-lapse; Earth years scale with D/β)
const H_LY = 0.25;     // light-clock mirror separation h = 0.25 light-year → one ship-frame tick 2h/c = 0.5 yr
const TICK = 2 * H_LY; // ship-frame tick (years)
const SHIP_LEN = 2.4;  // drawn ship length at rest (scene units, schematic)
const Y = 0.8;         // ship height in the scene
const tri = u => { const f = u - Math.floor(u); return f < 0.5 ? 2 * f : 2 - 2 * f; }; // 0 → 1 → 0 each tick

function numbers(p) {
  const v = p.beta * C.c, g = gamma(v);
  const tE = 2 * p.D / p.beta;          // Earth-frame round-trip time, years (distance in ly, speed in ly/yr)
  // one ship-frame light-clock tick (proper time 2h/c) lasts γ times longer by Earth clocks
  return { v, g, tE, tS: tE / g, gap: tE - tE / g, L: contractedLength(p.L0, v), Dp: contractedLength(p.D, v), tickE: dilatedTime(TICK, v) };
}

export default {
  num: 20, unit: 19, sections: ['19.1', '19.2', '19.3', '19.4', '19.9'], advanced: true, space: true,
  text: {
    title: 'Relativity Explorer',
    question: 'If a spaceship moves at a large fraction of the speed of light, whose clock runs slow, how long is the ship, and who is younger when the traveler returns?',
    params: { beta: 'Ship speed v/c (β)', D: 'Distance to the star (Earth frame)', L0: 'Ship proper length L0' },
    graph: ['clock readings vs Earth time', 'ship position (ly)', 'age difference (years)', 'light-clock photon height'],
    series: { earth: 'Earth clock', ship: 'ship clock', x: 'position', gap: 'Earth − ship', y: 'photon height' },
    measures: {
      t: 'Animation time', tE: 'Earth clock', tS: 'Ship clock', g: 'Lorentz factor γ', x: 'Ship position (Earth frame)', L: 'Ship length measured from Earth', Dp: 'Distance to star (ship frame)',
      gap: 'Age difference (Earth − ship)', tickE: 'One ship tick by Earth clocks', ticks: 'Light-clock ticks (ship)', ticksE: 'Light-clock ticks (Earth clock)', rateS: 'Ship clock rate dτ/dt', y: 'Photon height', leg: 'Leg (1 out, 2 back)',
    },
    predict: {
      prompt: 'A twin flies at 0.80c to a star 4 light-years away and comes straight back. When the ship lands, how does the travelling twin’s age compare with the twin who stayed on Earth?',
      choices: ['The traveller is older', 'They are the same age', 'The traveller is younger', 'Each twin sees the other as younger, so it cannot be decided'],
    },
    guided: [
      'Set D = 4 ly. Run at β = 0.20, 0.60, 0.80 and 0.95. Record the Earth-clock and ship-clock readings at landing and show that ship time = Earth time / γ every time.',
      'Choose the graph “clock readings vs Earth time”. Explain why the ship-clock line is straight with slope 1/γ, and what a slope of 1 would mean.',
      'Watch the light-clock photon’s trail. In the ship it bounces straight up and down, but from Earth it travels a diagonal. Use the diagonal (length c·Δt) to derive Δt = γ·Δt0.',
      'Keep L0 = 100 m and increase β. Record the Earth-measured length L and the crew-measured distance to the star. Show both are divided by the same γ.',
      'Both twins see the other moving. Explain what makes the trip asymmetric (only the traveller changes inertial frames at the star).',
    ],
    challenges: [
      'Make the ship clock run at exactly half the Earth rate: complete a trip with γ = 2.00 (±0.02).',
      'Plan a trip from which the traveller returns exactly 5.0 years younger than the Earth twin (±0.1 yr). Run it to landing.',
      'With a proper ship length of 100 m, choose a speed so Earth measures the ship as 25 m long (±1 m). Run it.',
      'Choose D and β so that the crew measures the one-way distance to the star as 3.00 ly (±0.05) while Earth measures it as at least 5 ly. Run it.',
    ],
    evaluate: 'Before you run: the ship travels at {beta}c to a star {D} light-years away (Earth frame) and immediately returns. How many years pass on the ship’s clock for the round trip?',
    honors: {
      prompt: 'Using the light clock, derive the time-dilation formula from the two postulates, then use it to explain the muon puzzle: muons made 15 km up (lifetime 2.2 μs) reach the ground at 0.995c. Check the speed’s γ in the lab.',
      solution: 'In the ship a tick is Δt0 = 2h/c. From Earth the photon covers the diagonal: (cΔt/2)² = h² + (vΔt/2)² → Δt = (2h/c)/√(1 − v²/c²) = γ·Δt0. At β = 0.995, γ = 10.0. Without dilation a muon travels only 0.995c × 2.2 μs ≈ 0.66 km per lifetime; in Earth’s frame its lifetime is γ × 2.2 μs = 22 μs → 6.6 km, so a significant fraction survives 15 km (e^(−15/6.6) ≈ 10 % vs e^(−15/0.66) ≈ 10⁻¹⁰). In the muon’s frame the 15 km is contracted to 1.5 km instead — same prediction.',
    },
    assumptions: [
      'Special relativity in the Earth (inertial) frame; the ship moves at constant speed and turns around instantaneously at the star. Acceleration phases, gravity and Earth’s own motion are ignored.',
      'The round trip is shown in 12 s of animation for every setting (a time-lapse); all clock readings are computed exactly as tE = 2D/β and τ = tE/γ, independent of the animation rate.',
      'The light clock is schematic: its mirrors are drawn 0.25 light-year apart so one ship tick is 0.5 yr, and horizontal and vertical distances use the same ly scale so the photon’s zig-zag path in the Earth frame has the correct angle. The ship’s drawn size is not to scale with the distances.',
      'Length contraction is drawn by shrinking the ship along its motion by 1/γ (as measured in the Earth frame); transverse dimensions are unchanged. What a camera would actually see (light-travel delays, Terrell rotation, Doppler colour shifts) is not shown.',
      'Energy bars are per kilogram of ship: rest energy mc² and kinetic energy (γ − 1)mc².',
      'Engine glow and star field are visual only.',
    ],
  },
  params: [
    { id: 'beta', min: 0.05, max: 0.995, step: 0.005, value: 0.8, unit: 'c' },
    { id: 'D', min: 2, max: 10, step: 0.5, value: 4, unit: 'ly' },
    { id: 'L0', min: 20, max: 200, step: 5, value: 100, unit: 'm' },
  ],
  camera: { target: [S / 2, 1.5, 0], dist: 30, free: [0.15, 0.3, 1], followId: 'ship' },
  view2d: { span: 26, cx: S / 2, cy: 2 },
  graph: {
    choices: [
      { label: 'clock readings vs Earth time', x: 'tE', xLabel: 'Earth time (yr)', y: ['tE', 'tS'], labels: ['earth', 'ship'], yLabel: 'clock reading (yr)' },
      { label: 'ship position (ly)', x: 'tE', xLabel: 'Earth time (yr)', y: ['x'], labels: ['x'], yLabel: 'x (ly)' },
      { label: 'age difference (years)', x: 'tE', xLabel: 'Earth time (yr)', y: ['gap'], labels: ['gap'], yLabel: 'Earth − ship (yr)' },
      { label: 'light-clock photon height', x: 'tE', xLabel: 'Earth time (yr)', y: ['y'], labels: ['y'], yLabel: 'height (ly)' },
    ],
  },
  recordKeys: ['g', 'tE', 'tS', 'gap', 'L', 'Dp'],
  decor(p) {
    const k = S / p.D, out = [{ shape: 'stars' }];
    for (let i = 0; i <= p.D; i++) out.push({ shape: 'line', pts: [[i * k, -0.6, 0], [i * k, -0.2, 0]], color: '#475569' });
    out.push({ shape: 'line', pts: [[0, -0.4, 0], [S, -0.4, 0]], color: '#475569' });
    out.push({ shape: 'label', text: `${p.D} ly (Earth frame)`, pos: [S / 2, -0.9, 0] });
    out.push({ shape: 'sphere', r: 1.1, pos: [-1.6, Y, 0], color: '#2563eb' }, { shape: 'label', text: 'Earth', pos: [-1.6, Y + 1.7, 0] });
    out.push({ shape: 'sphere', r: 1.0, pos: [S + 1.6, Y, 0], color: '#fde68a', emissive: '#f59e0b', glow: 1.2 }, { shape: 'label', text: 'star', pos: [S + 1.6, Y + 1.6, 0] });
    return out;
  },
  create(p) {
    const N = numbers(p), k = S / p.D, H = H_LY * k; // scene units per ly; clock mirror separation in scene units
    const s = { t: 0, done: false, events: [] };
    const tE = () => Math.min(N.tE, s.t / T_ANIM * N.tE);                 // Earth years elapsed
    const xLy = te => (te <= p.D / p.beta ? p.beta * te : 2 * p.D - p.beta * te); // ship position (ly)
    const tau = te => te / N.g;                                            // ship proper time (constant speed)
    const model = {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        const before = tE();
        s.t += dt;
        if (before < p.D / p.beta && tE() >= p.D / p.beta) s.events.push({ type: 'burst', pos: [S, Y, 0], strength: 0.6, color: '#fde68a', life: 0.8 });
        if (s.t >= T_ANIM - 1e-9) { s.t = T_ANIM; s.done = true; }
      },
      // light-clock photon in the Earth frame (light-years): rides with the ship horizontally, bounces vertically
      photon(te = tE()) { return { x: xLy(te), y: H_LY * tri(tau(te) / TICK), tE: te }; },
      measures() {
        const te = tE(), ts = tau(te);
        return [
          { id: 't', label: 'Animation time', value: s.t, unit: 's', hidden: true },
          { id: 'tE', label: 'Earth clock', value: te, unit: 'yr', ref: N.tE },
          { id: 'tS', label: 'Ship clock', value: ts, unit: 'yr', ref: N.tE },
          { id: 'g', label: 'Lorentz factor γ', value: N.g, unit: '', ref: 10 },
          { id: 'rateS', label: 'Ship clock rate dτ/dt', value: 1 / N.g, unit: '', ref: 1, hidden: true },
          { id: 'x', label: 'Ship position (Earth frame)', value: xLy(te), unit: 'ly', ref: p.D },
          { id: 'L', label: 'Ship length measured from Earth', value: N.L, unit: 'm', ref: p.L0 },
          { id: 'Dp', label: 'Distance to star (ship frame)', value: N.Dp, unit: 'ly', ref: p.D },
          { id: 'gap', label: 'Age difference (Earth − ship)', value: te - ts, unit: 'yr', ref: N.tE },
          { id: 'ticks', label: 'Light-clock ticks (ship)', value: Math.floor(ts / TICK + 1e-9), unit: '', ref: 100 },
          { id: 'tickE', label: 'One ship tick by Earth clocks', value: N.tickE, unit: 'yr', ref: 5 },
          { id: 'ticksE', label: 'Light-clock ticks (Earth clock)', value: Math.floor(te / TICK + 1e-9), unit: '', ref: 100, hidden: true },
          { id: 'y', label: 'Photon height', value: model.photon(te).y, unit: 'ly', hidden: true },
          { id: 'leg', label: 'Leg (1 out, 2 back)', value: te < p.D / p.beta ? 1 : 2, unit: '', hidden: true },
        ];
      },
      energy() { return [{ label: 'Rest energy mc² (per kg)', value: restEnergy(1), color: '#a5b4fc' }, { label: 'Kinetic (γ−1)mc² (per kg)', value: relKE(1, N.v), color: '#fbbf24' }]; },
      scene() {
        const te = tE(), ts = tau(te), out = te < p.D / p.beta, dir = out ? 1 : -1;
        const sx = xLy(te) * k, len = SHIP_LEN / N.g; // Earth-frame (contracted) length
        const ph = model.photon(te), clockY = Y + 0.6;
        const earthPh = H_LY * tri(te / TICK);
        return {
          bodies: [
            { id: 'ship', shape: 'box', size: [len, 0.45, 0.6], pos: [sx, Y, 0], color: '#e2e8f0', metal: 0.6, label: `ship clock ${ts.toFixed(2)} yr` },
            { id: 'nose', shape: 'cone', r: 0.25, h: Math.max(0.12, 0.5 / N.g), pos: [sx + dir * (len / 2 + Math.max(0.12, 0.5 / N.g) / 2), Y, 0], rot: [0, 0, -dir * Math.PI / 2], color: '#94a3b8' },
            { id: 'flame', shape: 'cone', r: 0.18, h: 0.35, pos: [sx - dir * (len / 2 + 0.17), Y, 0], rot: [0, 0, dir * Math.PI / 2], color: '#fb923c', emissive: '#f97316', glow: 1.2, visible: !s.done },
            { id: 'mlo', shape: 'box', size: [0.5, 0.04, 0.4], pos: [sx, clockY, 0], color: '#cbd5e1', metal: 0.9 },
            { id: 'mhi', shape: 'box', size: [0.5, 0.04, 0.4], pos: [sx, clockY + H, 0], color: '#cbd5e1', metal: 0.9 },
            { id: 'ph', shape: 'sphere', r: 0.1, pos: [ph.x * k, clockY + ph.y * k, 0], color: '#fde047', emissive: '#facc15', glow: 1.5, trail: true, trailColor: '#fde047' },
            { id: 'emlo', shape: 'box', size: [0.5, 0.04, 0.4], pos: [-1.6, Y + 1.4, 0], color: '#cbd5e1', metal: 0.9 },
            { id: 'emhi', shape: 'box', size: [0.5, 0.04, 0.4], pos: [-1.6, Y + 1.4 + H, 0], color: '#cbd5e1', metal: 0.9, label: `Earth clock ${te.toFixed(2)} yr` },
            { id: 'eph', shape: 'sphere', r: 0.1, pos: [-1.6, Y + 1.4 + earthPh * k, 0], color: '#fde047', emissive: '#facc15', glow: 1.5 },
          ],
          vectors: [
            { id: 'v', from: [sx, Y - 0.5, 0], vec: [dir * 2.5 * p.beta, 0, 0], color: '#4ade80', label: `v = ${p.beta}c` },
          ],
          lines: [
            { id: 'L', pts: [[sx - len / 2, Y - 0.35, 0], [sx + len / 2, Y - 0.35, 0]], color: '#f472b6' },
          ],
        };
      },
    };
    return model;
  },
  equations(p, model) {
    const N = numbers(p), m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    return [
      `γ = 1/√(1 − β²) = 1/√(1 − ${p.beta}²) = ${N.g.toFixed(4)}`,
      `Earth: t = 2D/v = 2 × ${p.D} ly / ${p.beta}c = ${N.tE.toFixed(3)} yr`,
      `Ship: τ = t/γ = ${m.tE.toFixed(3)} / ${N.g.toFixed(4)} = ${m.tS.toFixed(3)} yr  (Δt = γ·Δt0)`,
      `L = L0/γ = ${p.L0} / ${N.g.toFixed(4)} = ${N.L.toFixed(2)} m;  D′ = D/γ = ${N.Dp.toFixed(3)} ly`,
      `Age gap on landing = ${N.tE.toFixed(3)} − ${N.tS.toFixed(3)} = ${N.gap.toFixed(3)} yr`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => Math.abs(r.final.g - 2) <= 0.02 && Math.abs(r.final.tS / r.final.tE - 1 / r.final.g) < 1e-9 && r.final.tE >= 2 * r.params.D / r.params.beta - 1e-9),
    ({ runs }) => runs.some(r => r.final.tE >= 2 * r.params.D / r.params.beta - 1e-9 && Math.abs(r.final.gap - 5) <= 0.1),
    ({ runs }) => runs.some(r => r.params.L0 === 100 && Math.abs(r.final.L - 25) <= 1 && r.final.tE > 0),
    ({ runs }) => runs.some(r => r.params.D >= 5 && Math.abs(r.final.Dp - 3) <= 0.05 && r.final.tE > 0),
  ],
  evaluate(p) {
    const N = numbers(p);
    return { vars: { beta: p.beta, D: p.D }, answer: N.tS, unit: 'yr', tol: 0.02 };
  },
};
