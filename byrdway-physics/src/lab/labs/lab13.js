// Lab 13 — Thermal Energy Lab. (1) Two bodies in thermal contact inside an insulated box exchange heat by
// Newton's law (P = G·ΔT) until they share one temperature; the result is checked against calorimetry.
// (2) An ideal monatomic gas under a piston is taken quasi-statically through an isothermal, isobaric or
// isochoric process; P, V, T, work, heat and internal energy are tracked (first law ΔU = Q − W).
import { mixTemp, idealGasP, isothermalWork, isobaricWork, rk4Step, C } from '../../physics/index.js';

const MATS = {
  water: { label: 'Water', c: 4186, rho: 1000, color: '#38bdf8' },
  aluminum: { label: 'Aluminium', c: 900, rho: 2700, color: '#cbd5e1' },
  iron: { label: 'Iron', c: 450, rho: 7870, color: '#78716c' },
  copper: { label: 'Copper', c: 385, rho: 8960, color: '#d97706' },
  granite: { label: 'Granite', c: 790, rho: 2700, color: '#a8a29e' },
};
const matOpts = Object.entries(MATS).map(([value, m]) => ({ value, label: m.label }));
const R = C.R, CV = 1.5 * R;      // monatomic ideal gas, Cv = 3/2 R
const TI = 300;                   // gas initial temperature, K
const TAU = 6;                    // duration of the quasi-static gas process, s
const GAS_HOLD = 0.5;             // the gas run ends this long after the process, s
const REAL_RUN = 8;               // contact mode: the time-lapse is set so a run lasts ~8 s on screen

const lam = p => { const C1 = p.m1 * MATS[p.mat1].c, C2 = p.m2 * MATS[p.mat2].c; return { C1, C2, l: p.G * (1 / C1 + 1 / C2) }; };
const gasEnd = p => p.proc === 'isochoric' ? { V2: p.V1, T2: TI * p.ratio } : { V2: p.V1 * p.ratio, T2: p.proc === 'isothermal' ? TI : TI * p.ratio };
const heatColor = Tc => { const k = Math.max(0, Math.min(1, Tc / 100)); const r = Math.round(40 + 215 * k), b = Math.round(230 - 200 * k), g = Math.round(90 + 40 * (1 - Math.abs(k - 0.5) * 2)); return `rgb(${r},${g},${b})`; };
const tri = x => { const f = ((x % 2) + 2) % 2; return f < 1 ? f : 2 - f; }; // triangle wave in [0, 1] (molecule bounce, visual)

export default {
  num: 13, unit: 12, sections: ['12.1', '12.2', '12.3', '12.5', '12.6', '12.7'],
  text: {
    title: 'Thermal Energy Lab',
    question: 'How do two objects at different temperatures reach thermal equilibrium, and how are heat, work and internal energy related when a gas is compressed, expanded or heated?',
    params: { mode: 'Experiment', m1: 'Body A mass', mat1: 'Body A material', T1: 'Body A initial temperature', m2: 'Body B mass', mat2: 'Body B material', T2: 'Body B initial temperature', G: 'Contact conductance G', proc: 'Gas process', n: 'Amount of gas n', V1: 'Initial volume V₁', ratio: 'Final ratio (V₂/V₁, or T₂/T₁ if isochoric)' },
    options: { contact: 'Two bodies in thermal contact', gas: 'Gas in a piston', water: 'Water', aluminum: 'Aluminium', iron: 'Iron', copper: 'Copper', granite: 'Granite', isothermal: 'Isothermal (T constant)', isobaric: 'Isobaric (P constant)', isochoric: 'Isochoric (V constant)' },
    graph: ['temperatures vs time (contact)', 'heat flow rate vs time (contact)', 'P–V diagram (gas)', 'gas temperature vs time', 'work, heat and ΔU vs time (gas)'],
    series: { T1: 'body A', T2: 'body B', P: 'heat current', Pg: 'pressure', Tg: 'T', W: 'W by gas', Q: 'Q into gas', dU: 'ΔU' },
    measures: { t: 'Time', T1: 'Body A temperature', T2: 'Body B temperature', dT: 'Temperature difference', H: 'Heat flow rate A → B', Qa: 'Heat lost by A', Qb: 'Heat gained by B', tHalf: 'Time for ΔT to halve', Pg: 'Gas pressure', V: 'Gas volume', Tg: 'Gas temperature', W: 'Work done by the gas', Q: 'Heat added to the gas', dU: 'Change in internal energy' },
    predict: {
      prompt: '1 kg of water at 80 °C and a 1 kg copper block at 20 °C are sealed together in an insulated box. Where will their common final temperature be?',
      choices: ['Closer to 20 °C', 'Exactly 50 °C', 'Closer to 80 °C', 'The copper ends hotter than the water'],
    },
    guided: [
      'Contact mode with the defaults. Run and read the final temperatures. Use the energy bars to compare the heat lost by the water with the heat gained by the copper.',
      'Change body B to 1 kg of water at 20 °C. Predict the final temperature, then run. Why is the answer now exactly halfway?',
      'Double the contact conductance G. Does the final temperature change? What does change on the temperature–time graph and in the “time for ΔT to halve” reading?',
      'Gas mode, isothermal, n = 1 mol, V₁ = 10 L, ratio = 2. Run and compare the work on the P–V graph with nRT·ln(V₂/V₁). Where did the energy for that work come from?',
      'Repeat as isobaric and as isochoric with the same ratio. For each, read W, Q and ΔU and check that ΔU = Q − W.',
      'Compress the gas isothermally (ratio 0.5). What are the signs of W and Q now, and what do they mean physically?',
    ],
    challenges: [
      'Using two different materials, make the bodies settle at 40.0 °C (±0.5 °C). Run until they reach equilibrium.',
      'Choose masses, materials and the conductance so that the temperature difference halves in 60 s (±3 s). Run it.',
      'Compress 1 mol of gas isothermally so that it gives out 1000 J (±30 J) of heat to the surroundings.',
    ],
    evaluate: 'Before you run: a {m1} kg body with specific heat {c1} J/(kg·K) at {T1} °C touches a {m2} kg body with specific heat {c2} J/(kg·K) at {T2} °C inside an insulated box. Calculate their final common temperature.',
    honors: {
      prompt: 'With heat flow P = G·(T_A − T_B), show that the temperature difference decays exponentially, find its time constant in terms of G and the two heat capacities, and test your expression by measuring the halving time.',
      solution: 'C_A·dT_A/dt = −G·ΔT and C_B·dT_B/dt = +G·ΔT, so dΔT/dt = −G(1/C_A + 1/C_B)·ΔT → ΔT = ΔT₀·e^(−t/τ) with τ = 1/[G(1/C_A + 1/C_B)], and t½ = τ·ln 2. Example: 1 kg water (4186 J/K) and 1 kg copper (385 J/K) with G = 10 W/K: τ = 1/[10(1/4186 + 1/385)] = 35.3 s, t½ = 24.4 s. The final temperature does not depend on G at all.',
    },
    assumptions: [
      'Contact mode: the box is perfectly insulated, so heat flows only between the two bodies; each body has a single uniform temperature (lumped model) and constant specific heat; no phase changes occur (keep water between 0 and 100 °C).',
      'Heat flows at the rate P = G·(T_A − T_B) (Newton’s law of cooling for contact conduction) and is integrated with RK4. The animation is time-lapsed so each contact run lasts about 8 s on screen; the time readings are real (model) seconds.',
      'Gas mode: an ideal monatomic gas (C_v = 3/2·R) starts at 300 K and is changed quasi-statically (always in equilibrium) over 6 s; the work W = ∫P dV is integrated step by step.',
      'W is the work done BY the gas (positive on expansion); Q is the heat added TO the gas; the first law is ΔU = Q − W.',
      'Colours, the moving gas molecules and the heat-flow arrows are visual aids; molecule speeds are drawn proportional to √T but do not represent individual measured molecules.',
    ],
  },
  params: [
    { id: 'mode', value: 'contact', options: [{ value: 'contact', label: 'Two bodies in thermal contact' }, { value: 'gas', label: 'Gas in a piston' }] },
    { id: 'm1', min: 0.1, max: 5, step: 0.1, value: 1, unit: 'kg' },
    { id: 'mat1', value: 'water', options: matOpts },
    { id: 'T1', min: 0, max: 100, step: 1, value: 80, unit: '°C' },
    { id: 'm2', min: 0.1, max: 5, step: 0.1, value: 1, unit: 'kg' },
    { id: 'mat2', value: 'copper', options: matOpts },
    { id: 'T2', min: 0, max: 100, step: 1, value: 20, unit: '°C' },
    { id: 'G', min: 1, max: 50, step: 1, value: 10, unit: 'W/K' },
    { id: 'proc', value: 'isothermal', options: [{ value: 'isothermal', label: 'Isothermal (T constant)' }, { value: 'isobaric', label: 'Isobaric (P constant)' }, { value: 'isochoric', label: 'Isochoric (V constant)' }] },
    { id: 'n', min: 0.1, max: 2, step: 0.1, value: 1, unit: 'mol' },
    { id: 'V1', min: 2, max: 20, step: 0.5, value: 10, unit: 'L' },
    { id: 'ratio', min: 0.4, max: 3, step: 0.05, value: 2, unit: '' },
  ],
  camera: { target: [0, 1.0, 0], dist: 6.5, free: [0.35, 0.35, 1] },
  view2d: { span: 6, cx: 0, cy: 1.3 },
  graph: {
    choices: [
      { label: 'temperatures vs time (contact)', y: ['T1', 'T2'], labels: ['T1', 'T2'], yLabel: 'T (°C)' },
      { label: 'heat flow rate vs time (contact)', y: ['H'], labels: ['P'], yLabel: 'P (W)' },
      { label: 'P–V diagram (gas)', x: 'V', xLabel: 'V (L)', y: ['Pg'], labels: ['Pg'], yLabel: 'P (kPa)' },
      { label: 'gas temperature vs time', y: ['Tg'], labels: ['Tg'], yLabel: 'T (K)' },
      { label: 'work, heat and ΔU vs time (gas)', y: ['W', 'Q', 'dU'], labels: ['W', 'Q', 'dU'], yLabel: 'energy (J)' },
    ],
  },
  recordKeys: ['T1', 'T2', 'Qa', 'tHalf', 'Pg', 'V', 'Tg', 'W', 'Q', 'dU'],
  decor: p => {
    const out = [{ shape: 'ground', size: 30, divisions: 30 }];
    if (p.mode === 'contact') out.push(
      { shape: 'box', size: [2.8, 0.08, 1.4], pos: [0, 0.04, 0], color: '#475569' },
      { shape: 'box', size: [2.8, 1.5, 0.04], pos: [0, 0.79, -0.7], color: '#f8fafc', opacity: 0.12 },
      { shape: 'box', size: [0.04, 1.5, 1.4], pos: [-1.4, 0.79, 0], color: '#f8fafc', opacity: 0.12 },
      { shape: 'box', size: [0.04, 1.5, 1.4], pos: [1.4, 0.79, 0], color: '#f8fafc', opacity: 0.12 },
      { shape: 'label', text: 'insulated box', pos: [0, 1.7, -0.7], color: '#94a3b8' },
    );
    else out.push(
      { shape: 'box', size: [1.4, 0.12, 1.4], pos: [0, 0.06, 0], color: '#334155' },
      { shape: 'label', text: 'heat reservoir / burner', pos: [0, 0.05, 0.9], color: '#94a3b8' },
    );
    return out;
  },
  create(p) {
    const contact = p.mode === 'contact';
    const { C1, C2, l } = lam(p);
    const lapse = contact ? (8 / l) / REAL_RUN : 1;   // model seconds per animation second
    const end = gasEnd(p);
    const n = p.n, V1 = p.V1 / 1000, V2 = end.V2 / 1000;
    const P1 = idealGasP(n, TI, V1);
    const s = { t: 0, done: false, events: [], T1: p.T1, T2: p.T2, tHalf: NaN, V: V1, Tg: TI, W: 0, u: 0, path: 0 };
    const dT0 = p.T1 - p.T2;
    const gasAt = u => {
      if (p.proc === 'isochoric') return { V: V1, T: TI + (end.T2 - TI) * u };
      const V = V1 + (V2 - V1) * u;
      return { V, T: p.proc === 'isothermal' ? TI : P1 * V / (n * R) };
    };
    const Pof = (V, T) => idealGasP(n, T, V);
    const flow = ([a, b]) => { const H = p.G * (a - b); return [-H / C1, H / C2]; };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        if (contact) {
          const h = dt * lapse, prev = s.T1 - s.T2, t0 = s.t;
          [s.T1, s.T2] = rk4Step(flow, [s.T1, s.T2], h);
          s.t += h;
          const now = s.T1 - s.T2;
          if (!Number.isFinite(s.tHalf) && dT0 !== 0 && Math.abs(now) <= Math.abs(dT0) / 2) {
            // interpolate on ln|ΔT| (exactly linear in time for this model) inside the step
            const a = Math.log(Math.abs(prev)), b = Math.log(Math.abs(now)), target = Math.log(Math.abs(dT0) / 2);
            s.tHalf = t0 + h * (a - target) / (a - b);
          }
          if (s.t >= 8 / l - 1e-9 || dT0 === 0) s.done = true; // 8 time constants: ΔT has fallen to 0.03 %
        } else {
          s.t += dt;
          const u0 = s.u, u1 = Math.min(1, s.t / TAU);
          const a = gasAt(u0), b = gasAt(u1), m = gasAt((u0 + u1) / 2);
          s.W += Pof(m.V, m.T) * (b.V - a.V);       // midpoint rule for ∫P dV
          s.u = u1; s.V = b.V; s.Tg = b.T;
          s.path += dt * Math.sqrt(s.Tg / TI);
          if (s.t >= TAU + GAS_HOLD - 1e-9) s.done = true;
        }
      },
      measures() {
        const NaNs = ids => ids.map(id => ({ id, label: id, value: NaN, hidden: true }));
        if (contact) {
          const H = p.G * (s.T1 - s.T2);
          return [
            { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
            { id: 'T1', label: 'Body A temperature', value: s.T1, unit: '°C', ref: 100 },
            { id: 'T2', label: 'Body B temperature', value: s.T2, unit: '°C', ref: 100 },
            { id: 'dT', label: 'Temperature difference', value: s.T1 - s.T2, unit: 'K', ref: 100 },
            { id: 'H', label: 'Heat flow rate A → B', value: H, unit: 'W', ref: 5000 },
            { id: 'Qa', label: 'Heat lost by A', value: C1 * (p.T1 - s.T1), unit: 'J', ref: 4e5 },
            { id: 'Qb', label: 'Heat gained by B', value: C2 * (s.T2 - p.T2), unit: 'J', ref: 4e5 },
            { id: 'tHalf', label: 'Time for ΔT to halve', value: s.tHalf, unit: 's', ref: 600 },
            ...NaNs(['Pg', 'V', 'Tg', 'W', 'Q', 'dU']),
          ];
        }
        const P = Pof(s.V, s.Tg), dU = n * CV * (s.Tg - TI);
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'Pg', label: 'Gas pressure', value: P / 1000, unit: 'kPa', ref: 3000 },
          { id: 'V', label: 'Gas volume', value: s.V * 1000, unit: 'L', ref: 60 },
          { id: 'Tg', label: 'Gas temperature', value: s.Tg, unit: 'K', ref: 900 },
          { id: 'W', label: 'Work done by the gas', value: s.W, unit: 'J', ref: 8000 },
          { id: 'Q', label: 'Heat added to the gas', value: dU + s.W, unit: 'J', ref: 8000 },
          { id: 'dU', label: 'Change in internal energy', value: dU, unit: 'J', ref: 8000 },
          ...NaNs(['T1', 'T2', 'dT', 'H', 'Qa', 'Qb', 'tHalf']),
        ];
      },
      energy() {
        if (contact) return [
          { label: 'Heat lost by A', value: C1 * (p.T1 - s.T1), color: '#f87171' },
          { label: 'Heat gained by B', value: C2 * (s.T2 - p.T2), color: '#7dd3fc' },
        ];
        const dU = n * CV * (s.Tg - TI);
        return [
          { label: 'Q (heat in)', value: dU + s.W, color: '#f87171' },
          { label: 'W (work by gas)', value: s.W, color: '#4ade80' },
          { label: 'ΔU', value: dU, color: '#fbbf24' },
        ];
      },
      scene() {
        if (contact) {
          const side = (m, mat) => Math.min(1.0, Math.max(0.25, Math.cbrt(m / MATS[mat].rho) * 2.2)); // drawn size grows with volume
          const a = side(p.m1, p.mat1), b = side(p.m2, p.mat2), H = p.G * (s.T1 - s.T2);
          const bodies = [
            { id: 'A', shape: 'box', size: [a, a, a], pos: [-a / 2, 0.08 + a / 2, 0], color: heatColor(s.T1), metal: p.mat1 === 'water' ? 0 : 0.5, opacity: p.mat1 === 'water' ? 0.85 : undefined, label: `A ${MATS[p.mat1].label}: ${s.T1.toFixed(1)} °C`, labelOffset: [0, a / 2 + 0.75, 0] },
            { id: 'B', shape: 'box', size: [b, b, b], pos: [b / 2, 0.08 + b / 2, 0], color: heatColor(s.T2), metal: p.mat2 === 'water' ? 0 : 0.5, opacity: p.mat2 === 'water' ? 0.85 : undefined, label: `B ${MATS[p.mat2].label}: ${s.T2.toFixed(1)} °C`, labelOffset: [0, b / 2 + 0.75, 0] },
          ];
          // thermometers: column height ∝ temperature (0–100 °C → 0–0.6 m)
          for (const [id, x, top, T] of [['thA', -a / 2, 0.08 + a, s.T1], ['thB', b / 2, 0.08 + b, s.T2]]) {
            const h = Math.max(0.01, 0.6 * T / 100);
            bodies.push({ id: id + 'g', shape: 'cylinder', r: 0.035, h: 0.62, pos: [x, top + 0.31, 0.1], color: '#e2e8f0', opacity: 0.25 });
            bodies.push({ id, shape: 'cylinder', r: 0.022, h, pos: [x, top + h / 2, 0.1], color: '#ef4444' });
          }
          const k = 0.6 / Math.max(1, Math.abs(p.G * dT0));
          return { bodies, vectors: [{ id: 'H', from: [-0.3 * Math.sign(H || 1), 0.08 + Math.min(a, b) / 2, Math.max(a, b) / 2 + 0.1], vec: [H * k, 0, 0], color: '#fb923c', label: Math.abs(H) > 0.01 ? `heat ${Math.abs(H).toFixed(1)} W` : '' }] };
        }
        const Pk = Pof(s.V, s.Tg) / 1000, hgt = s.V * 1000 * 0.05, R0 = 0.45, base = 0.12; // 1 L → 5 cm of cylinder
        const bodies = [
          { id: 'cyl', shape: 'cylinder', r: R0 + 0.03, h: 3.2, pos: [0, base + 1.6, 0], color: '#cbd5e1', opacity: 0.15 },
          { id: 'gas', shape: 'cylinder', r: R0, h: hgt, pos: [0, base + hgt / 2, 0], color: heatColor((s.Tg - 200) / 7), opacity: 0.35 },
          { id: 'piston', shape: 'cylinder', r: R0, h: 0.08, pos: [0, base + hgt + 0.04, 0], color: '#94a3b8', metal: 0.7, label: `P = ${Pk.toFixed(1)} kPa  V = ${(s.V * 1000).toFixed(2)} L  T = ${s.Tg.toFixed(0)} K`, labelOffset: [0, 0.35, 0] },
          { id: 'rod', shape: 'cylinder', r: 0.04, h: 1.2, pos: [0, base + hgt + 0.68, 0], color: '#64748b' },
        ];
        for (let i = 0; i < 24; i++) {
          const ph = i * 0.6180339, sp = 0.6 + (i % 5) * 0.15;
          const x = (tri(ph * 3 + s.path * sp * 1.3) - 0.5) * R0 * 1.2, z = (tri(ph * 5 + s.path * sp * 0.9) - 0.5) * R0 * 1.2, y = base + 0.04 + tri(ph * 7 + s.path * sp * 1.7) * Math.max(0.02, hgt - 0.08);
          bodies.push({ id: 'mol' + i, shape: 'sphere', r: 0.03, pos: [x, y, z], color: '#fde68a' });
        }
        const proc = s.u < 1 && s.t > 0;
        const vectors = [];
        if (proc && p.proc !== 'isochoric') vectors.push({ id: 'Wv', from: [R0 + 0.25, base + hgt, 0], vec: [0, Math.sign(V2 - V1) * 0.5, 0], color: '#4ade80', label: V2 > V1 ? 'gas does work (expands)' : 'work done on gas' });
        const heatIn = p.proc === 'isothermal' ? Math.sign(V2 - V1) : Math.sign(end.T2 - TI);
        if (proc && heatIn) vectors.push({ id: 'Qv', from: [-R0 - 0.3, heatIn > 0 ? 0.1 : base + 0.4, 0], vec: [0, heatIn * 0.4, 0], color: heatIn > 0 ? '#f87171' : '#60a5fa', label: heatIn > 0 ? 'heat in' : 'heat out' });
        bodies.push({ id: 'burner', shape: 'box', size: [1.0, 0.04, 1.0], pos: [0, 0.1, 0], color: '#334155', emissive: proc ? (heatIn > 0 ? '#ef4444' : heatIn < 0 ? '#3b82f6' : null) : null, glow: 0.6 });
        return { bodies, vectors };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'contact') {
      const c1 = MATS[p.mat1].c, c2 = MATS[p.mat2].c, Te = mixTemp(p.m1, c1, p.T1, p.m2, c2, p.T2), { C1, C2, l } = lam(p);
      return [
        'heat lost by A = heat gained by B:  m_A c_A (T_A − T) = m_B c_B (T − T_B)',
        `T_eq = (${p.m1}·${c1}·${p.T1} + ${p.m2}·${c2}·${p.T2}) / (${p.m1}·${c1} + ${p.m2}·${c2}) = ${Te.toFixed(2)} °C`,
        `P = G·(T_A − T_B) = ${p.G} × ${m.dT.toFixed(2)} = ${m.H.toFixed(1)} W`,
        `τ = 1/[G(1/C_A + 1/C_B)] = 1/[${p.G}(1/${C1.toFixed(0)} + 1/${C2.toFixed(0)})] = ${(1 / l).toFixed(2)} s,  t½ = τ·ln2 = ${(Math.LN2 / l).toFixed(2)} s`,
        `Q_lost(A) = ${m.Qa.toFixed(0)} J,  Q_gained(B) = ${m.Qb.toFixed(0)} J`,
      ];
    }
    const end = gasEnd(p), V1 = p.V1 / 1000, V2 = end.V2 / 1000, P1 = idealGasP(p.n, TI, V1);
    const Wth = p.proc === 'isothermal' ? isothermalWork(p.n, TI, V1, V2) : p.proc === 'isobaric' ? isobaricWork(P1, V1, V2) : 0;
    return [
      `PV = nRT:  P = ${p.n}·8.314·${m.Tg.toFixed(1)} / ${(m.V / 1000).toFixed(4)} = ${m.Pg.toFixed(2)} kPa`,
      p.proc === 'isothermal' ? `W = nRT·ln(V₂/V₁) = ${p.n}·8.314·300·ln(${p.ratio}) = ${Wth.toFixed(1)} J` : p.proc === 'isobaric' ? `W = P·ΔV = ${(P1 / 1000).toFixed(2)} kPa × ${((V2 - V1) * 1000).toFixed(2)} L = ${Wth.toFixed(1)} J` : 'W = 0 (no volume change)',
      `ΔU = n·(3/2)R·ΔT = ${p.n}·12.47·${(m.Tg - TI).toFixed(1)} = ${m.dU.toFixed(1)} J`,
      `Q = ΔU + W = ${m.dU.toFixed(1)} + ${m.W.toFixed(1)} = ${m.Q.toFixed(1)} J`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'contact' && r.params.mat1 !== r.params.mat2 && Math.abs(r.final.T1 - 40) <= 0.5 && Math.abs(r.final.T2 - 40) <= 0.5 && Math.abs(r.final.T1 - r.final.T2) < 0.1),
    ({ runs }) => runs.some(r => r.params.mode === 'contact' && Math.abs(r.final.tHalf - 60) <= 3),
    ({ runs }) => runs.some(r => r.params.mode === 'gas' && r.params.proc === 'isothermal' && r.params.n === 1 && r.params.ratio < 1 && Math.abs(r.final.Q + 1000) <= 30 && r.t >= TAU),
  ],
  evaluate(p) {
    const c1 = MATS[p.mat1].c, c2 = MATS[p.mat2].c;
    return { vars: { m1: p.m1, c1, T1: p.T1, m2: p.m2, c2, T2: p.T2 }, answer: mixTemp(p.m1, c1, p.T1, p.m2, c2, p.T2), unit: '°C', tol: 0.01 };
  },
};
