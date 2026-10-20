// Lab 17 — Circuit Builder. A battery and three resistors wired in series, in parallel, or as a combination
// (R1 in series with R2 ∥ R3), solved with the library's Modified Nodal Analysis solveDC; plus an RC-charging
// mode in which the capacitor is treated as a voltage source Vc = Q/C inside solveDC and Q is integrated with RK4.
import { solveDC, rk4Step, seriesR, parallelR } from '../../physics/index.js';

const TDC = 5;            // DC runs last 5 s (the circuit is already in its steady state)
const TRC_MAX = 60;       // RC runs last 5τ, capped at 60 s
const K_VIS = 1.5;        // electron animation: 1 A ↔ 1.5 scene-m/s (visual scale only)
const V_VIS_MAX = 5;      // capped at 5 scene-m/s
const SPACING = 0.36;     // electron spacing along the wires (scene m)

// Element lists for solveDC. Node 1 = battery +, node 0 = battery − (ground).
export function netlist(p, Vc = 0) {
  const bat = { type: 'V', a: 1, b: 0, value: p.V };
  switch (p.mode) {
    case 'series': return { nodes: 4, els: [bat, { type: 'R', a: 1, b: 2, value: p.R1 }, { type: 'R', a: 2, b: 3, value: p.R2 }, { type: 'R', a: 3, b: 0, value: p.R3 }] };
    case 'parallel': return { nodes: 2, els: [bat, { type: 'R', a: 1, b: 0, value: p.R1 }, { type: 'R', a: 1, b: 0, value: p.R2 }, { type: 'R', a: 1, b: 0, value: p.R3 }] };
    case 'combo': return { nodes: 3, els: [bat, { type: 'R', a: 1, b: 2, value: p.R1 }, { type: 'R', a: 2, b: 0, value: p.R2 }, { type: 'R', a: 2, b: 0, value: p.R3 }] };
    default: return { nodes: 3, els: [bat, { type: 'R', a: 1, b: 2, value: p.R1 }, { type: 'V', a: 2, b: 0, value: Vc }] }; // rc
  }
}
// Solve the DC circuit: battery current and per-resistor current / voltage drop / power.
export function solve(p, Vc = 0) {
  const { nodes, els } = netlist(p, Vc), r = solveDC(nodes, els);
  const Rs = els.map((e, i) => ({ e, I: r.currents[i] })).filter(x => x.e.type === 'R');
  const I = r.currents[0];
  const br = [0, 1, 2].map(k => Rs[k] ? { I: Rs[k].I, V: Rs[k].I * Rs[k].e.value, P: Rs[k].I * Rs[k].I * Rs[k].e.value } : { I: 0, V: 0, P: 0 });
  return { I, br, V: r.V };
}

// Wire segments (scene coordinates, x right, y up) with the branch whose conventional current flows along pts.
// key: 'I' battery current, 0/1/2 resistor index, 'I23' = I2 + I3.
function layout(mode) {
  const L = (a, b, key) => ({ pts: [a, b], key });
  const B = [L([-3, 0.6], [-3, 2], 'I')], E = [L([-3, -2], [-3, -0.6], 'I')];
  if (mode === 'series') return {
    segs: [...B, L([-3, 2], [3, 2], 'I'), L([3, 2], [3, -2], 'I'), L([3, -2], [-3, -2], 'I'), ...E],
    res: [{ pos: [0, 2], vert: false }, { pos: [3, 0], vert: true }, { pos: [0, -2], vert: false }],
  };
  if (mode === 'parallel') return {
    segs: [...B, L([-3, 2], [-1, 2], 'I'), L([-1, 2], [1, 2], 'I23'), L([1, 2], [3, 2], 2),
      L([-1, 2], [-1, -2], 0), L([1, 2], [1, -2], 1), L([3, 2], [3, -2], 2),
      L([3, -2], [1, -2], 2), L([1, -2], [-1, -2], 'I23'), L([-1, -2], [-3, -2], 'I'), ...E],
    res: [{ pos: [-1, 0], vert: true }, { pos: [1, 0], vert: true }, { pos: [3, 0], vert: true }],
  };
  if (mode === 'combo') return {
    segs: [...B, L([-3, 2], [1, 2], 'I'), L([1, 2], [3, 2], 2), L([1, 2], [1, -2], 1), L([3, 2], [3, -2], 2),
      L([3, -2], [1, -2], 2), L([1, -2], [-3, -2], 'I'), ...E],
    res: [{ pos: [-1, 2], vert: false }, { pos: [1, 0], vert: true }, { pos: [3, 0], vert: true }],
  };
  return { // rc
    segs: [...B, L([-3, 2], [3, 2], 'I'), L([3, 2], [3, 0.12], 'I'), L([3, -0.12], [3, -2], 'I'), L([3, -2], [-3, -2], 'I'), ...E],
    res: [{ pos: [0, 2], vert: false }], cap: [3, 0],
  };
}
const segLen = s => Math.hypot(s.pts[1][0] - s.pts[0][0], s.pts[1][1] - s.pts[0][1]);

export default {
  num: 17, unit: 16, sections: ['16.1', '16.2', '16.3', '16.4', '16.5', '16.6', '16.7', '16.9'],
  text: {
    title: 'Circuit Builder',
    question: 'How do current, voltage and power divide among resistors wired in series, in parallel, and in combination — and how does a capacitor charge through a resistor?',
    params: { mode: 'Circuit', V: 'Battery emf ε', R1: 'Resistor R₁', R2: 'Resistor R₂', R3: 'Resistor R₃', C: 'Capacitor C (RC mode)' },
    options: { series: 'Series: R₁, R₂, R₃ in one loop', parallel: 'Parallel: R₁ ∥ R₂ ∥ R₃', combo: 'Combination: R₁ + (R₂ ∥ R₃)', rc: 'RC charging: R₁ and C in series' },
    graph: ['resistor currents (A)', 'voltage drops (V)', 'power (W)', 'capacitor voltage Vc (V)', 'battery current I (A)', 'energy (J)'],
    series: { I1: 'I₁', I2: 'I₂', I3: 'I₃', V1: 'V₁', V2: 'V₂', V3: 'V₃', P1: 'P₁', P2: 'P₂', P3: 'P₃', Vc: 'Vc', I: 'I', Wbat: 'battery work', Uc: 'capacitor energy', Eth: 'thermal' },
    measures: { t: 'Time', Req: 'Equivalent resistance', I: 'Battery current', I1: 'Current in R₁', I2: 'Current in R₂', I3: 'Current in R₃', V1: 'Voltage across R₁', V2: 'Voltage across R₂', V3: 'Voltage across R₃', P1: 'Power in R₁', P2: 'Power in R₂', P3: 'Power in R₃', Ptot: 'Battery power output', Vc: 'Capacitor voltage', Q: 'Capacitor charge', tau: 'Time constant τ = R₁C', Wbat: 'Energy from battery', Uc: 'Energy stored in C', Eth: 'Thermal energy in resistors' },
    predict: {
      prompt: 'In the parallel circuit (ideal battery), you raise R₃ from 10 Ω to 40 Ω. What happens to the current through R₁?',
      choices: ['It increases', 'It decreases', 'It stays the same', 'It drops to zero'],
    },
    guided: [
      'Series mode, ε = 12 V, R₁ = R₂ = R₃ = 10 Ω. Record a run. Show that the same current flows through every resistor and that V₁ + V₂ + V₃ = ε (Kirchhoff’s loop rule).',
      'Parallel mode with the same values. Show that every resistor has the full 12 V across it and that I = I₁ + I₂ + I₃ (junction rule). Compare the battery current with the series run.',
      'Combination mode: R₁ = 10 Ω, R₂ = 20 Ω, R₃ = 30 Ω. Calculate Req = R₁ + R₂R₃/(R₂ + R₃) by hand, then check the reading. Which resistor dissipates the most power, and why?',
      'Watch the electron animation in each mode. Where do the electrons move fastest? Relate the speed to the current in each wire. (Electrons move opposite to the conventional-current arrows.)',
      'RC mode: ε = 12 V, R₁ = 20 Ω, C = 100 mF. Read Vc at t = τ = 2 s and compare with 63 % of ε. Use the energy bars to show that half the battery’s work ends up stored in the capacitor.',
    ],
    challenges: [
      'With ε = 12.0 V and a DC circuit (series, parallel or combination), build a circuit whose battery current is 0.50 A (±0.01 A). Run it.',
      'Make the combination circuit’s equivalent resistance exactly 15.0 Ω (±0.1 Ω) and run it.',
      'RC mode: choose R₁ and C so that τ = 2.0 s (±0.05 s), and run the charge to completion (Vc ≥ 99 % of ε).',
    ],
    evaluate: 'Before you run: with the selected circuit, ε = {V} V, R₁ = {R1} Ω, R₂ = {R2} Ω, R₃ = {R3} Ω (in RC mode, C = {C} mF and the capacitor starts uncharged), calculate the current leaving the battery at t = 0.',
    honors: {
      prompt: 'In combination mode with ε = 12 V and R₁ = 10 Ω, R₂ = 20 Ω, R₃ = 30 Ω, use Kirchhoff’s rules (not the Req shortcut) to find all three currents. Then show that the total power dissipated equals ε·I.',
      solution: 'Junction: I₁ = I₂ + I₃. Loop through R₁ and R₂: 12 − 10I₁ − 20I₂ = 0. Loop around R₂ and R₃: 20I₂ − 30I₃ = 0 → I₃ = (2/3)I₂, so I₁ = (5/3)I₂ and 12 = (50/3 + 20)I₂ → I₂ = 0.3273 A, I₃ = 0.2182 A, I₁ = 0.5455 A (Req = 22 Ω). Powers: 10(0.5455)² + 20(0.3273)² + 30(0.2182)² = 2.975 + 2.142 + 1.428 = 6.545 W = 12 V × 0.5455 A.',
    },
    assumptions: [
      'The battery is ideal (no internal resistance) and the wires have zero resistance; resistors are ohmic and do not change with temperature.',
      'DC circuits are solved by Modified Nodal Analysis (library solveDC). They reach steady state instantly; a DC run simply lasts 5 s to accumulate energy.',
      'RC mode: the capacitor is modeled in solveDC as a voltage source Vc = Q/C; dQ/dt = I is integrated with fourth-order Runge–Kutta. The capacitor starts uncharged; the run lasts 5τ (at most 60 s). The large capacitances (mF) are chosen so τ is seconds long.',
      'The moving electrons show the direction of electron flow (opposite to conventional current) with a speed proportional to the current in each wire: 1 A ↔ 1.5 scene-m/s, capped at 5. Real drift speeds are well below 1 mm/s; the animation and resistor glow are visual only.',
      'Power in each resistor P = I²R = V²/R; thermal energy is the time integral of the total power.',
    ],
  },
  params: [
    { id: 'mode', value: 'series', options: [{ value: 'series', label: 'Series: R₁, R₂, R₃ in one loop' }, { value: 'parallel', label: 'Parallel: R₁ ∥ R₂ ∥ R₃' }, { value: 'combo', label: 'Combination: R₁ + (R₂ ∥ R₃)' }, { value: 'rc', label: 'RC charging: R₁ and C in series' }] },
    { id: 'V', min: 1, max: 24, step: 0.5, value: 12, unit: 'V' },
    { id: 'R1', min: 1, max: 100, step: 1, value: 10, unit: 'Ω' },
    { id: 'R2', min: 1, max: 100, step: 1, value: 10, unit: 'Ω' },
    { id: 'R3', min: 1, max: 100, step: 1, value: 10, unit: 'Ω' },
    { id: 'C', min: 10, max: 1000, step: 10, value: 100, unit: 'mF' },
  ],
  dt: 1 / 240,
  camera: { target: [0, 0, 0], dist: 10.5, free: [0.22, 0.25, 1] },
  view2d: { span: 9, cx: 0, cy: 0 },
  graph: {
    choices: [
      { label: 'resistor currents (A)', y: ['I1', 'I2', 'I3'], labels: ['I1', 'I2', 'I3'], yLabel: 'I (A)' },
      { label: 'voltage drops (V)', y: ['V1', 'V2', 'V3'], labels: ['V1', 'V2', 'V3'], yLabel: 'V (V)' },
      { label: 'power (W)', y: ['P1', 'P2', 'P3'], labels: ['P1', 'P2', 'P3'], yLabel: 'P (W)' },
      { label: 'capacitor voltage Vc (V)', y: ['Vc'], labels: ['Vc'], yLabel: 'Vc (V)' },
      { label: 'battery current I (A)', y: ['I'], labels: ['I'], yLabel: 'I (A)' },
      { label: 'energy (J)', y: ['Wbat', 'Uc', 'Eth'], labels: ['Wbat', 'Uc', 'Eth'], yLabel: 'energy (J)' },
    ],
  },
  recordKeys: ['Req', 'I', 'I1', 'I2', 'I3', 'V1', 'V2', 'V3', 'Ptot', 'Vc', 'tau'],
  decor: p => {
    const lay = layout(p.mode), out = [];
    for (const s of lay.segs) out.push({ shape: 'line', pts: s.pts.map(q => [q[0], q[1], 0]), color: '#cbd5e1' });
    // thin cylinders over the wires make them read as solid in 3D
    for (const s of lay.segs) {
      const [a, b] = s.pts, len = segLen(s), vert = Math.abs(a[0] - b[0]) < 1e-9;
      out.push({ shape: 'cylinder', r: 0.03, h: len, pos: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0], rot: vert ? [0, 0, 0] : [0, 0, Math.PI / 2], color: '#94a3b8', metal: 0.6 });
    }
    // battery: body + positive terminal
    out.push({ shape: 'cylinder', r: 0.32, h: 1.2, pos: [-3, 0, 0], color: '#1f2937', metal: 0.3 },
      { shape: 'cylinder', r: 0.33, h: 0.35, pos: [-3, 0.42, 0], color: '#f59e0b' },
      { shape: 'cylinder', r: 0.1, h: 0.12, pos: [-3, 0.66, 0], color: '#e5e7eb', metal: 0.8 },
      { shape: 'label', text: `ε = ${p.V} V`, pos: [-3.9, 0, 0], color: '#fde68a' },
      { shape: 'label', text: '+', pos: [-2.6, 0.55, 0], color: '#fca5a5' }, { shape: 'label', text: '−', pos: [-2.6, -0.55, 0], color: '#93c5fd' });
    if (lay.cap) {
      out.push({ shape: 'box', size: [0.9, 0.06, 0.6], pos: [3, 0.12, 0], color: '#a78bfa' }, { shape: 'box', size: [0.9, 0.06, 0.6], pos: [3, -0.12, 0], color: '#a78bfa' },
        { shape: 'label', text: `C = ${p.C} mF`, pos: [3.95, 0, 0], color: '#c4b5fd' });
    }
    out.push({ shape: 'label', text: { series: 'Series circuit', parallel: 'Parallel circuit', combo: 'Combination circuit', rc: 'RC charging circuit' }[p.mode], pos: [0, 2.8, 0], color: '#e2e8f0' });
    return out;
  },
  create(p) {
    const rc = p.mode === 'rc', Cap = p.C * 1e-3, tau = p.R1 * Cap;
    const tEnd = rc ? Math.min(5 * tau, TRC_MAX) : TDC;
    const lay = layout(p.mode);
    const Req = p.mode === 'series' ? seriesR(p.R1, p.R2, p.R3) : p.mode === 'parallel' ? parallelR(p.R1, p.R2, p.R3) : p.mode === 'combo' ? p.R1 + parallelR(p.R2, p.R3) : p.R1;
    // state: Q (C), battery work, thermal energy
    const s = { t: 0, y: [0, 0, 0], done: false, events: [], phase: lay.segs.map(() => 0) };
    const sol = () => solve(p, rc ? s.y[0] / Cap : 0);
    const deriv = y => { const r = solve(p, rc ? y[0] / Cap : 0); return [rc ? r.I : 0, p.V * r.I, r.br.reduce((a, b) => a + b.P, 0)]; };
    let cur = sol();
    const segI = (r, key) => key === 'I' ? r.I : key === 'I23' ? r.br[1].I + r.br[2].I : r.br[key].I;
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        let h = dt; if (s.t + h > tEnd) h = tEnd - s.t;
        if (h > 0) { s.y = rk4Step(deriv, s.y, h); s.t += h; }
        cur = sol();
        lay.segs.forEach((sg, i) => { s.phase[i] += Math.max(-V_VIS_MAX, Math.min(V_VIS_MAX, K_VIS * segI(cur, sg.key))) * dt; });
        if (s.t >= tEnd - 1e-9) s.done = true;
      },
      measures() {
        const r = cur, Q = s.y[0];
        const b = r.br;
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'Req', label: 'Equivalent resistance', value: Req, unit: 'Ω', ref: 300, hidden: rc },
          { id: 'I', label: 'Battery current', value: r.I, unit: 'A', ref: 5 },
          { id: 'I1', label: 'Current in R₁', value: b[0].I, unit: 'A', ref: 5, hidden: rc },
          { id: 'I2', label: 'Current in R₂', value: b[1].I, unit: 'A', ref: 5, hidden: rc },
          { id: 'I3', label: 'Current in R₃', value: b[2].I, unit: 'A', ref: 5, hidden: rc },
          { id: 'V1', label: 'Voltage across R₁', value: b[0].V, unit: 'V', ref: 24 },
          { id: 'V2', label: 'Voltage across R₂', value: b[1].V, unit: 'V', ref: 24, hidden: rc },
          { id: 'V3', label: 'Voltage across R₃', value: b[2].V, unit: 'V', ref: 24, hidden: rc },
          { id: 'P1', label: 'Power in R₁', value: b[0].P, unit: 'W', ref: 50 },
          { id: 'P2', label: 'Power in R₂', value: b[1].P, unit: 'W', ref: 50, hidden: rc },
          { id: 'P3', label: 'Power in R₃', value: b[2].P, unit: 'W', ref: 50, hidden: rc },
          { id: 'Ptot', label: 'Battery power output', value: p.V * r.I, unit: 'W', ref: 100 },
          { id: 'Vc', label: 'Capacitor voltage', value: rc ? Q / Cap : 0, unit: 'V', ref: p.V, hidden: !rc },
          { id: 'Q', label: 'Capacitor charge', value: Q, unit: 'C', ref: p.V * Cap, hidden: !rc },
          { id: 'tau', label: 'Time constant τ = R₁C', value: rc ? tau : 0, unit: 's', ref: 10, hidden: !rc },
          { id: 'Wbat', label: 'Energy from battery', value: s.y[1], unit: 'J', ref: 100, hidden: true },
          { id: 'Uc', label: 'Energy stored in C', value: rc ? Q * Q / (2 * Cap) : 0, unit: 'J', ref: 100, hidden: true },
          { id: 'Eth', label: 'Thermal energy in resistors', value: s.y[2], unit: 'J', ref: 100, hidden: true },
        ];
      },
      energy() {
        const Q = s.y[0];
        const e = [{ label: 'Battery work', value: s.y[1], color: '#4ade80' }, { label: 'Thermal (resistors)', value: s.y[2], color: '#f87171' }];
        if (rc) e.push({ label: 'Stored in C', value: Q * Q / (2 * Cap), color: '#a78bfa' });
        return e;
      },
      scene() {
        const r = cur, bodies = [], vectors = [];
        lay.res.forEach((rs, i) => {
          const P = r.br[i].P, R = p['R' + (i + 1)];
          bodies.push({ id: 'R' + i, shape: 'box', size: rs.vert ? [0.34, 1.1, 0.34] : [1.1, 0.34, 0.34], pos: [rs.pos[0], rs.pos[1], 0], color: '#d6b98c', emissive: '#f97316', glow: Math.min(1.5, P / 10), label: `R${i + 1} = ${R} Ω · ${Math.abs(r.br[i].I).toFixed(3)} A` });
          // colour bands
          for (let k = -1; k <= 1; k++) bodies.push({ id: `band${i}${k}`, shape: 'box', size: rs.vert ? [0.36, 0.07, 0.36] : [0.07, 0.36, 0.36], pos: rs.vert ? [rs.pos[0], rs.pos[1] + k * 0.25, 0] : [rs.pos[0] + k * 0.25, rs.pos[1], 0], color: ['#7c2d12', '#000000', '#b45309'][k + 1] });
          // conventional-current arrow beside each resistor, length ∝ current
          const Lv = Math.min(1.2, 0.4 * Math.abs(r.br[i].I)) * Math.sign(r.br[i].I);
          const dir = { series: [[1, 0], [0, -1], [-1, 0]], parallel: [[0, -1], [0, -1], [0, -1]], combo: [[1, 0], [0, -1], [0, -1]], rc: [[1, 0]] }[p.mode][i];
          vectors.push({ id: 'Iarr' + i, from: [rs.pos[0] + (rs.vert ? 0.45 : -dir[0] * Lv / 2), rs.pos[1] + (rs.vert ? -dir[1] * Lv / 2 : 0.45), 0.1], vec: [dir[0] * Lv, dir[1] * Lv, 0], color: '#fbbf24', label: `I${i + 1}` });
        });
        // electrons: uniformly spaced, moving opposite to conventional current
        lay.segs.forEach((sg, i) => {
          const len = segLen(sg), n = Math.max(1, Math.floor(len / SPACING)), d = len / n;
          const [a, b] = sg.pts, ux = (b[0] - a[0]) / len, uy = (b[1] - a[1]) / len;
          for (let j = 0; j < n; j++) {
            const u = ((j * d - s.phase[i]) % len + len) % len;
            bodies.push({ id: `e${i}_${j}`, shape: 'sphere', r: 0.06, pos: [a[0] + ux * u, a[1] + uy * u, 0.06], color: '#38bdf8', emissive: '#0ea5e9', glow: 0.8 });
          }
        });
        if (rc) {
          const Vc = s.y[0] / Cap;
          bodies.push({ id: 'capfill', shape: 'box', size: [0.8, 0.16, 0.5], pos: [3, 0, 0], color: '#7c3aed', opacity: 0.15 + 0.75 * Math.min(1, Vc / p.V), label: `Vc = ${Vc.toFixed(2)} V` });
        }
        return { bodies, vectors };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'rc') {
      const tau = p.R1 * p.C * 1e-3;
      return [
        'I = (ε − Vc)/R₁,  dQ/dt = I,  Vc = Q/C',
        `τ = R₁C = ${p.R1} Ω × ${p.C / 1000} F = ${tau.toFixed(3)} s`,
        `Vc = ε(1 − e^(−t/τ)) = ${p.V}(1 − e^(−${m.t.toFixed(2)}/${tau.toFixed(2)})) = ${m.Vc.toFixed(3)} V`,
        `I = (${p.V} − ${m.Vc.toFixed(3)})/${p.R1} = ${m.I.toFixed(4)} A`,
        `W_battery = ${m.Wbat.toFixed(3)} J = U_C ${m.Uc.toFixed(3)} J + thermal ${m.Eth.toFixed(3)} J`,
      ];
    }
    const head = { series: `Req = R₁ + R₂ + R₃ = ${p.R1} + ${p.R2} + ${p.R3} = ${m.Req.toFixed(3)} Ω`, parallel: `1/Req = 1/${p.R1} + 1/${p.R2} + 1/${p.R3} → Req = ${m.Req.toFixed(3)} Ω`, combo: `Req = R₁ + R₂R₃/(R₂ + R₃) = ${p.R1} + ${(p.R2 * p.R3 / (p.R2 + p.R3)).toFixed(3)} = ${m.Req.toFixed(3)} Ω` }[p.mode];
    return [
      head,
      `I = ε/Req = ${p.V} / ${m.Req.toFixed(3)} = ${m.I.toFixed(4)} A`,
      `V₁ = I₁R₁ = ${m.I1.toFixed(4)} × ${p.R1} = ${m.V1.toFixed(3)} V;  V₂ = ${m.V2.toFixed(3)} V;  V₃ = ${m.V3.toFixed(3)} V`,
      `P = I²R: ${m.P1.toFixed(3)} + ${m.P2.toFixed(3)} + ${m.P3.toFixed(3)} = ${(m.P1 + m.P2 + m.P3).toFixed(3)} W = εI = ${m.Ptot.toFixed(3)} W`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode !== 'rc' && r.params.V === 12 && Math.abs(r.final.I - 0.5) <= 0.01),
    ({ runs }) => runs.some(r => r.params.mode === 'combo' && Math.abs(r.final.Req - 15) <= 0.1),
    ({ runs }) => runs.some(r => r.params.mode === 'rc' && Math.abs(r.final.tau - 2) <= 0.05 && r.final.Vc >= 0.99 * r.params.V),
  ],
  evaluate(p) {
    const r = solve(p, 0);
    return { vars: { V: p.V, R1: p.R1, R2: p.R2, R3: p.R3, C: p.C }, answer: r.I, unit: 'A', tol: 0.02 };
  },
};
