// Lab 12 — Fluid Dynamics Lab. (1) A cube hangs from a spring scale and is lowered into a tank: buoyant force,
// apparent weight, Archimedes' principle. (2) The cube is released at the surface (or dropped) and bobs to its
// floating equilibrium with viscous damping. (3) A Venturi pipe: continuity A₁v₁ = A₂v₂ and Bernoulli pressures.
import { buoyantForce, fractionSubmerged, continuityV2, bernoulliP2, rk4Step, C } from '../../physics/index.js';

const g = C.g;
const HS = 1.0;          // fluid surface height above the tank floor, m
const TANK = 1.6;        // tank inner width, m
const U = 0.08;          // lowering speed of the scale hook, m/s
const ZETA = 0.12;       // damping ratio of the bobbing motion (linear viscous drag)
const HOLD = 1.0;        // scale mode: hold time after the block reaches its lowest point, s
const TMAX = 12;         // drop runs end after this long, s (scale runs end after the hold)
// Venturi pipe geometry (x along the pipe, m)
const D1 = 0.3, P1 = 150e3, PATM = C.atm, Y0 = 0.55;
const XS = [-3.5, -1.5, -1.0, 1.0, 1.5, 3.5]; // inlet | taper | narrow | taper | outlet
const PIPE_TMAX = 30;
const VOL = 1e-3;        // energy bars track a 1-litre parcel of fluid, m³

const sub = (yb, a) => Math.min(a, Math.max(0, HS - yb));          // submerged depth of the cube
const bodyOf = p => {
  const a = p.a, m = p.rhoB * a ** 3, k = p.rhoF * g * a * a;      // hydrostatic stiffness k = ρF·g·a²
  return { a, m, k, b: 2 * ZETA * Math.sqrt(k * m), W: m * g };
};
// Buoyant-force potential: Ub(d) = ρF g a² ∫₀^d s(x) dx, with d the depth of the cube's bottom below the surface.
const Ub = (p, d) => { const a = p.a, K = p.rhoF * g * a * a; if (d <= 0) return 0; if (d <= a) return K * d * d / 2; return K * (a * a / 2 + a * (d - a)); };

// Pipe profile: diameter and centre-line height at position x.
function pipeAt(p, x) {
  const d2 = p.r * D1, y2 = Y0 + p.dh;
  const lerp = (u, a, b) => a + (b - a) * u;
  if (x <= XS[1]) return { D: D1, y: Y0, seg: 0 };
  if (x < XS[2]) { const u = (x - XS[1]) / (XS[2] - XS[1]); return { D: lerp(u, D1, d2), y: lerp(u, Y0, y2), seg: 1 }; }
  if (x <= XS[3]) return { D: d2, y: y2, seg: 2 };
  if (x < XS[4]) { const u = (x - XS[3]) / (XS[4] - XS[3]); return { D: lerp(u, d2, D1), y: lerp(u, y2, Y0), seg: 3 }; }
  return { D: D1, y: Y0, seg: 4 };
}
const area = D => Math.PI * D * D / 4;
function pipeState(p, x) {
  const A1 = area(D1), Q = A1 * p.v1, at = pipeAt(p, x), v = Q / area(at.D);
  return { ...at, v, Q, P: bernoulliP2(P1, p.rhoF, p.v1, Y0, v, at.y) };
}

const mid = (a, b) => (a + b) / 2;
const cylAlong = (id, x0, y0, x1, y1, r0, r1, color, opacity) => {
  const L = Math.hypot(x1 - x0, y1 - y0), al = Math.atan2(-(x1 - x0), y1 - y0);
  // CylinderGeometry top (+y local, r) maps to the (x1, y1) end after rotation by α about z
  return { id, shape: 'cylinder', r: r1, r2: r0, h: L, pos: [mid(x0, x1), mid(y0, y1), 0], rot: [0, 0, al], color, opacity };
};

export default {
  num: 12, unit: 11, sections: ['11.1', '11.2', '11.4', '11.5', '11.6'],
  text: {
    title: 'Fluid Dynamics Lab',
    question: 'How large is the buoyant force on a submerged object, where does a floating object settle, and how do speed and pressure change as a fluid flows through a narrowing pipe?',
    params: { mode: 'Experiment', rhoB: 'Block density ρ_block', rhoF: 'Fluid density ρ_fluid', a: 'Cube side a', h0: 'Drop height above surface (drop mode)', v1: 'Inlet speed v₁ (pipe)', r: 'Throat diameter ratio d₂/d₁ (pipe)', dh: 'Throat raised by Δh (pipe)' },
    options: { scale: 'Lower on a spring scale', drop: 'Release and float (bobbing)', pipe: 'Venturi pipe flow' },
    graph: ['scale reading & buoyant force vs depth (scale)', 'depth of block bottom vs time (drop)', 'forces on the block vs time', 'tracer speed vs time (pipe)', 'pressure at tracer vs position (pipe)'],
    series: { T: 'scale reading', Fb: 'buoyant force', W: 'weight', d: 'depth', vp: 'tracer speed', Pp: 'pressure' },
    measures: { t: 'Time', d: 'Depth of block bottom', frac: 'Fraction submerged', v: 'Block velocity (up +)', W: 'True weight mg', Fb: 'Buoyant force', T: 'Spring-scale reading', Wapp: 'Apparent weight mg − F_b', N: 'Floor normal force', Tb: 'Measured bobbing period', v1: 'Inlet speed v₁', v2: 'Throat speed v₂', Q: 'Volume flow rate', P1: 'Inlet pressure P₁', P2: 'Throat pressure P₂', dP: 'Pressure drop P₁ − P₂', xp: 'Tracer position', vp: 'Tracer speed', Pp: 'Pressure at tracer', tN: 'Time to cross the 2 m throat' },
    predict: {
      prompt: 'A cube with density 600 kg/m³ floats in water (1000 kg/m³). You release the same cube in a liquid of density 1200 kg/m³ instead. Once it settles, how does the fraction of the cube below the surface compare?',
      choices: ['A larger fraction is submerged', 'The same fraction is submerged', 'A smaller fraction is submerged', 'It sinks to the bottom'],
    },
    guided: [
      'Scale mode, ρ_fluid = 1000 kg/m³, a = 0.20 m, ρ_block = 2700 kg/m³ (aluminium). Run and use the graph of scale reading vs depth. Why does the reading fall only while the block is entering the fluid and then stay constant?',
      'Compare the drop in the scale reading with the weight of the displaced fluid ρ_fluid·a³·g. Repeat with ρ_fluid = 1400 kg/m³ and explain the change.',
      'Drop mode, h0 = 0: release cubes with ρ_block = 300, 600 and 900 kg/m³ in water. Record the fraction submerged at rest each time and compare it with ρ_block/ρ_fluid.',
      'Still in drop mode, measure the bobbing period for a = 0.10 m and a = 0.40 m with the same densities. Show that it agrees with T = 2π·√(ρ_block·a/(ρ_fluid·g)) (to within the small damping correction).',
      'Pipe mode, d₂/d₁ = 0.5, Δh = 0: by what factor does the speed increase in the throat? Use the pressure readings to check P₁ − P₂ = ½ρ(v₂² − v₁²).',
      'Raise the throat (Δh = 0.8 m) without changing the flow. Explain the extra pressure drop using the ρ·g·h term of Bernoulli’s equation.',
    ],
    challenges: [
      'Make a cube float at rest with 60% (±1%) of its volume submerged. Run it in drop mode until it settles.',
      'In scale mode, find a block whose fully submerged scale reading is exactly half of its true weight (±2%). Run it to the end.',
      'In pipe mode with a level throat (Δh = 0), make the pressure in the throat exactly 20 kPa (±1 kPa) lower than at the inlet. Run the tracer through.',
    ],
    evaluate: 'Before you run: a cube {a} m on a side with density {rhoB} kg/m³ hangs from a spring scale and is lowered completely into a fluid of density {rhoF} kg/m³. Calculate the scale reading once it is fully submerged and at rest (g = 9.8 m/s²). Enter 0 if the block floats.',
    honors: {
      prompt: 'A floating cube bobs with angular frequency ω = √(k/m), where the restoring “spring” comes from buoyancy. Derive k for a cube of side a and show that the period does not depend on the fluid density alone but on the ratio ρ_block/ρ_fluid and on a. Test your result with two runs.',
      solution: 'Pushing the cube a distance x deeper adds a displaced volume a²·x, so the extra buoyant force is −ρ_fluid·g·a²·x: k = ρ_fluid·g·a². With m = ρ_block·a³: ω = √(ρ_fluid·g/(ρ_block·a)), T = 2π·√((ρ_block/ρ_fluid)·a/g). Example: a = 0.30 m, ρ_block/ρ_fluid = 0.4 → T₀ = 2π√(0.12/9.8) = 0.695 s; the lab’s damping ratio 0.12 lengthens it to T₀/√(1 − 0.12²) = 0.700 s. Doubling both densities leaves T unchanged.',
    },
    assumptions: [
      'The fluids are incompressible and at rest in the tank; the tank is wide enough that the surface level does not rise when the block enters (the displaced volume is neglected for the level).',
      'The block is a rigid cube that stays upright (no tilting or rotation). The buoyant force is ρ_fluid·g·V_submerged (Archimedes), computed from the exact submerged depth.',
      'Water resistance on the moving block is modelled as linear viscous drag b·v with b chosen so the bobbing has damping ratio 0.12; added (entrained) fluid mass and surface waves are neglected. Drag acts only while part of the block is in the fluid.',
      'Scale mode: the hook lowers the block at a steady 0.08 m/s, so the reading while moving is mg − F_b − b·v; the reading at rest at the lowest point is exactly mg − F_b. If the reading reaches zero the cable goes slack and the block floats free.',
      'A block that reaches the tank floor stops there (perfectly inelastic contact); the floor then supplies the normal force mg − F_b.',
      'Pipe mode: steady, inviscid, incompressible flow with a uniform speed across each cross-section; P₁ = 150 kPa (absolute) at the inlet; Bernoulli’s equation holds along the centre line. If it predicts a negative absolute pressure the real liquid would cavitate and the model no longer applies.',
      'g = 9.8 m/s². The manometer columns above the pipe are drawn at 1/10 of the true pressure head; dye particles are visual aids that follow the same flow-speed model as the measured tracer.',
    ],
  },
  params: [
    { id: 'mode', value: 'scale', options: [{ value: 'scale', label: 'Lower on a spring scale' }, { value: 'drop', label: 'Release and float (bobbing)' }, { value: 'pipe', label: 'Venturi pipe flow' }] },
    { id: 'rhoB', min: 100, max: 3000, step: 10, value: 2700, unit: 'kg/m³' },
    { id: 'rhoF', min: 700, max: 1400, step: 10, value: 1000, unit: 'kg/m³' },
    { id: 'a', min: 0.1, max: 0.4, step: 0.01, value: 0.2, unit: 'm' },
    { id: 'h0', min: 0, max: 0.4, step: 0.01, value: 0, unit: 'm' },
    { id: 'v1', min: 0.5, max: 3, step: 0.05, value: 1.5, unit: 'm/s' },
    { id: 'r', min: 0.4, max: 1, step: 0.01, value: 0.5, unit: '' },
    { id: 'dh', min: 0, max: 1, step: 0.05, value: 0, unit: 'm' },
  ],
  camera: { target: [0, 0.9, 0], dist: 7.5, free: [0.3, 0.3, 1] },
  view2d: { span: 8, cx: 0, cy: 1.1 },
  graph: {
    choices: [
      { label: 'scale reading & buoyant force vs depth (scale)', x: 'd', xLabel: 'depth of bottom (m)', y: ['T', 'Fb'], labels: ['T', 'Fb'], yLabel: 'force (N)' },
      { label: 'depth of block bottom vs time (drop)', y: ['d'], labels: ['d'], yLabel: 'depth (m)' },
      { label: 'forces on the block vs time', y: ['W', 'Fb', 'T'], labels: ['W', 'Fb', 'T'], yLabel: 'force (N)' },
      { label: 'tracer speed vs time (pipe)', y: ['vp'], labels: ['vp'], yLabel: 'v (m/s)' },
      { label: 'pressure at tracer vs position (pipe)', x: 'xp', xLabel: 'position along pipe (m)', y: ['Pp'], labels: ['Pp'], yLabel: 'P (kPa)' },
    ],
  },
  recordKeys: ['W', 'Fb', 'T', 'frac', 'Tb', 'v2', 'dP', 'P2'],
  decor: p => {
    const out = [{ shape: 'ground', size: 40, divisions: 40 }];
    if (p.mode !== 'pipe') {
      const w = TANK, wall = 0.04, H = 1.35, glass = '#94a3b8';
      out.push(
        { shape: 'box', size: [w + 2 * wall, 0.04, w * 0.7], pos: [0, 0.02 - 0.04, 0], color: '#334155' },
        { shape: 'box', size: [wall, H, w * 0.7], pos: [-w / 2 - wall / 2, H / 2, 0], color: glass, opacity: 0.25 },
        { shape: 'box', size: [wall, H, w * 0.7], pos: [w / 2 + wall / 2, H / 2, 0], color: glass, opacity: 0.25 },
        { shape: 'box', size: [w, H, wall], pos: [0, H / 2, -w * 0.35], color: glass, opacity: 0.2 },
        { shape: 'box', size: [w, HS, w * 0.7 - 0.02], pos: [0, HS / 2, 0], color: p.rhoF > 1100 ? '#0e7490' : p.rhoF < 900 ? '#a16207' : '#1d4ed8', opacity: 0.35 },
        { shape: 'line', pts: [[-w / 2, HS, w * 0.36], [w / 2, HS, w * 0.36]], color: '#93c5fd' },
        { shape: 'label', text: `ρ_fluid = ${p.rhoF} kg/m³`, pos: [-w / 2 + 0.35, HS + 0.08, w * 0.36], color: '#93c5fd' },
        ...[0, 0.25, 0.5, 0.75, 1].map(y => ({ shape: 'label', text: `${(HS - y).toFixed(2)} m deep`, pos: [w / 2 + 0.35, y, w * 0.36], color: '#64748b' })),
      );
      if (p.mode === 'scale') out.push(
        { shape: 'box', size: [0.1, 2.4, 0.1], pos: [-1.2, 1.2, -0.5], color: '#475569' },
        { shape: 'box', size: [1.3, 0.08, 0.08], pos: [-0.6, 2.4, -0.5], color: '#475569' },
      );
    } else {
      out.push(
        { shape: 'box', size: [7.6, 0.1, 0.6], pos: [0, 0.05, 0], color: '#334155' },
        ...[XS[0] + 0.3, (XS[2] + XS[3]) / 2].map(x => ({ shape: 'box', size: [0.08, Y0 + (x > XS[1] ? p.dh : 0) - 0.1, 0.08], pos: [x, (Y0 + (x > XS[1] ? p.dh : 0)) / 2, 0], color: '#475569' })),
        { shape: 'box', size: [0.08, Y0 - 0.1, 0.08], pos: [XS[5] - 0.3, Y0 / 2, 0], color: '#475569' },
        { shape: 'label', text: 'flow →', pos: [XS[0] + 0.4, Y0 - 0.35, 0.3], color: '#93c5fd' },
        { shape: 'label', text: 'manometer heights × 1/10', pos: [XS[5] - 0.9, 2.6, 0], color: '#64748b' },
      );
    }
    return out;
  },
  create(p) {
    const B = bodyOf(p), pipe = p.mode === 'pipe';
    const s = { t: 0, done: false, events: [], yb: 0, v: 0, phase: 'free', T: 0, Ed: 0, Eimp: 0, hold: 0, tSlack: Infinity, lastCross: NaN, Tb: NaN, prevV: 0,
      xp: XS[0], tIn: NaN, tOut: NaN, dye: Array.from({ length: 14 }, (_, i) => XS[0] + (i / 14) * (XS[5] - XS[0])) };
    const yLow = HS - p.a - 0.15;
    if (!pipe) {
      if (p.mode === 'scale') { s.yb = HS + 0.15; s.phase = 'hook'; }
      else { s.yb = HS + p.h0; s.phase = 'free'; }
    }
    const y0 = s.yb, Ub0 = Ub(p, HS - y0);
    const Fb = yb => buoyantForce(p.rhoF, p.a * p.a * sub(yb, p.a));
    // free motion: state [y, v, E_drag]
    const deriv = ([y, v]) => { const sd = sub(y, p.a), drag = sd > 0 ? B.b * v : 0; return [v, (Fb(y) - B.W - drag) / B.m, sd > 0 ? B.b * v * v : 0]; };
    const recordCross = (vOld, vNew, dt) => {
      // maximum depth ⇔ velocity crosses from negative (moving down) to positive; interpolate the crossing time
      if (vOld < 0 && vNew >= 0 && sub(s.yb, p.a) > 0) {
        const tc = s.t - dt + dt * (-vOld) / (vNew - vOld);
        if (Number.isFinite(s.lastCross)) s.Tb = tc - s.lastCross;
        s.lastCross = tc;
      }
    };
    const pipeStep = dt => {
      const f = x => [pipeState(p, x[0]).v];
      const x0 = s.xp, x1 = rk4Step(f, [s.xp], dt)[0];
      const t0 = s.t; s.t += dt; s.xp = x1;
      // throat entry / exit times, interpolated inside the step (speed is constant across the throat ends)
      // the speed is exactly v₂ inside the throat, so the part of the step spent there fixes the crossing times
      const v2 = pipeState(p, 0).v;
      if (x0 < XS[2] && x1 >= XS[2]) s.tIn = x1 <= XS[3] ? s.t - (x1 - XS[2]) / v2 : t0 + dt * (XS[2] - x0) / (x1 - x0);
      if (x0 < XS[3] && x1 >= XS[3]) s.tOut = x0 >= XS[2] ? t0 + (XS[3] - x0) / v2 : s.tIn + (XS[3] - XS[2]) / v2;
      s.dye = s.dye.map(x => { let n = rk4Step(f, [x], dt)[0]; if (n > XS[5]) n = XS[0] + (n - XS[5]); return n; });
      if (s.xp >= XS[5]) { s.xp = XS[5]; s.done = true; }
      if (s.t >= PIPE_TMAX - 1e-9) s.done = true;
    };
    const buoyStep = dt => {
      if (s.phase === 'hook') {
        const sd0 = sub(s.yb, p.a);
        let ny = s.yb - U * dt;
        if (ny <= yLow) ny = yLow;
        s.yb = ny; s.t += dt;
        const sd = sub(s.yb, p.a);
        s.T = B.W - Fb(s.yb) - (sd > 0 ? B.b * U : 0);
        if (sd > 0) s.Ed += B.b * U * U * dt;
        if (sd0 === 0 && sd > 0) s.events.push({ type: 'burst', pos: [0, HS, 0], strength: 0.4, speed: 0.4, color: '#bfdbfe', life: 0.6 });
        if (s.T <= 0) { s.T = 0; s.phase = 'free'; s.v = -U; s.tSlack = s.t; }
        else if (s.yb <= yLow) { s.phase = 'hold'; s.v = 0; s.T = B.W - Fb(s.yb); }
      } else if (s.phase === 'hold') {
        s.t += dt; s.hold += dt; s.T = B.W - Fb(s.yb);
        if (s.hold >= HOLD - 1e-9) s.done = true;
      } else if (s.phase === 'free') {
        const wasOut = sub(s.yb, p.a) === 0, vOld = s.v;
        const [y, v, ed] = rk4Step(deriv, [s.yb, s.v, 0], dt);
        s.yb = y; s.v = v; s.Ed += ed; s.t += dt; s.T = 0;
        if (wasOut && sub(s.yb, p.a) > 0 && vOld < -0.05) s.events.push({ type: 'burst', pos: [0, HS, 0], strength: Math.min(1.5, -vOld), speed: 0.6, color: '#bfdbfe', life: 0.8 });
        recordCross(vOld, s.v, dt);
        if (s.yb <= 0) {
          s.Eimp += 0.5 * B.m * s.v * s.v; s.yb = 0; s.v = 0; s.phase = 'rest';
          s.events.push({ type: 'impact', pos: [0, 0.02, 0], strength: 0.6, normal: 'y', color: '#93c5fd' });
        }
      } else s.t += dt; // resting on the floor
      if (p.mode === 'drop' && s.t >= TMAX - 1e-9) s.done = true;
      if (s.t >= 30 || s.t >= s.tSlack + 6 - 1e-9) s.done = true;
    };
    const model = {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) { if (pipe) pipeStep(dt); else buoyStep(dt); },
      measures() {
        const NaNs = ids => ids.map(id => ({ id, label: id, value: NaN, hidden: true }));
        if (pipe) {
          const st1 = pipeState(p, XS[0]), st2 = pipeState(p, 0), tr = pipeState(p, s.xp);
          return [
            { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
            { id: 'v1', label: 'Inlet speed v₁', value: p.v1, unit: 'm/s', ref: 3 },
            { id: 'v2', label: 'Throat speed v₂', value: st2.v, unit: 'm/s', ref: 20 },
            { id: 'Q', label: 'Volume flow rate', value: st1.Q * 1000, unit: 'L/s', ref: 220 },
            { id: 'P1', label: 'Inlet pressure P₁', value: st1.P / 1000, unit: 'kPa', ref: 150 },
            { id: 'P2', label: 'Throat pressure P₂', value: st2.P / 1000, unit: 'kPa', ref: 150 },
            { id: 'dP', label: 'Pressure drop P₁ − P₂', value: (st1.P - st2.P) / 1000, unit: 'kPa', ref: 150 },
            { id: 'xp', label: 'Tracer position', value: s.xp, unit: 'm', hidden: true },
            { id: 'vp', label: 'Tracer speed', value: tr.v, unit: 'm/s', ref: 20 },
            { id: 'Pp', label: 'Pressure at tracer', value: tr.P / 1000, unit: 'kPa', ref: 150 },
            { id: 'tN', label: 'Time to cross the 2 m throat', value: s.tOut - s.tIn, unit: 's', ref: 5 },
            ...NaNs(['d', 'frac', 'v', 'W', 'Fb', 'T', 'Wapp', 'N', 'Tb']),
          ];
        }
        const sd = sub(s.yb, p.a), fb = Fb(s.yb);
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'd', label: 'Depth of block bottom', value: HS - s.yb, unit: 'm', ref: 1 },
          { id: 'frac', label: 'Fraction submerged', value: 100 * sd / p.a, unit: '%', ref: 100 },
          { id: 'v', label: 'Block velocity (up +)', value: s.phase === 'hook' ? -U : s.v, unit: 'm/s', ref: 2 },
          { id: 'W', label: 'True weight mg', value: B.W, unit: 'N', ref: 2000 },
          { id: 'Fb', label: 'Buoyant force', value: fb, unit: 'N', ref: 2000 },
          { id: 'T', label: 'Spring-scale reading', value: p.mode === 'scale' ? s.T : 0, unit: 'N', ref: 2000, hidden: p.mode !== 'scale' },
          { id: 'Wapp', label: 'Apparent weight mg − F_b', value: B.W - fb, unit: 'N', ref: 2000 },
          { id: 'N', label: 'Floor normal force', value: s.phase === 'rest' ? Math.max(0, B.W - fb) : 0, unit: 'N', ref: 2000, hidden: p.mode !== 'drop' },
          { id: 'Tb', label: 'Measured bobbing period', value: s.Tb, unit: 's', ref: 2, hidden: p.mode !== 'drop' },
          ...NaNs(['v1', 'v2', 'Q', 'P1', 'P2', 'dP', 'xp', 'vp', 'Pp', 'tN']),
        ];
      },
      energy() {
        if (pipe) {
          const tr = pipeState(p, s.xp), rho = p.rhoF;
          const PV = tr.P * VOL, KE = 0.5 * rho * VOL * tr.v ** 2, PE = rho * VOL * g * (tr.y - Y0);
          return [
            { label: 'P·V (1 L parcel)', value: PV, color: '#7dd3fc' },
            { label: 'KE ½ρVv²', value: KE, color: '#fbbf24' },
            { label: 'PE ρVgh', value: PE, color: '#4ade80' },
            { label: 'Bernoulli total', value: PV + KE + PE, color: '#e2e8f0' },
          ];
        }
        if (p.mode !== 'drop') return [];
        const KE = 0.5 * B.m * s.v * s.v, dPEg = B.W * (s.yb - y0), dUb = Ub(p, HS - s.yb) - Ub0;
        return [
          { label: 'KE', value: KE, color: '#fbbf24' },
          { label: 'Gravitational PE released', value: -dPEg, color: '#4ade80' },
          { label: 'Work against buoyancy', value: dUb, color: '#7dd3fc' },
          { label: 'Thermal (drag + floor)', value: s.Ed + s.Eimp, color: '#f87171' },
        ];
      },
      scene() {
        if (pipe) {
          const d2 = p.r * D1, y2 = Y0 + p.dh, bodies = [], vectors = [];
          const segs = [[XS[0], Y0, XS[1], Y0, D1, D1], [XS[1], Y0, XS[2], y2, D1, d2], [XS[2], y2, XS[3], y2, d2, d2], [XS[3], y2, XS[4], Y0, d2, D1], [XS[4], Y0, XS[5], Y0, D1, D1]];
          segs.forEach(([x0, ya, x1, yb, r0, r1], i) => bodies.push(cylAlong('pipe' + i, x0, ya, x1, yb, r0 / 2, r1 / 2, '#3b82f6', 0.4)));
          s.dye.forEach((x, i) => { const st = pipeState(p, x), off = ((i * 7) % 5 - 2) / 5 * st.D * 0.35; bodies.push({ id: 'dye' + i, shape: 'sphere', r: 0.035, pos: [x, st.y + off, 0], color: '#bae6fd' }); });
          const tr = pipeState(p, s.xp);
          bodies.push({ id: 'tracer', shape: 'sphere', r: 0.06, pos: [s.xp, tr.y, 0], color: '#fbbf24', emissive: '#f59e0b', glow: 0.6, trail: true, label: `${tr.v.toFixed(2)} m/s` });
          // manometer columns: height = gauge pressure head / 10
          for (const [id, x] of [['m1', XS[0] + 0.3], ['m2', 0], ['m3', XS[5] - 0.3]]) {
            const st = pipeState(p, x), head = (st.P - PATM) / (p.rhoF * g) / 10, top = st.y + st.D / 2, h = Math.max(0.01, head);
            bodies.push({ id: id + 'g', shape: 'cylinder', r: 0.05, h: 2.2, pos: [x, top + 1.1, 0], color: '#cbd5e1', opacity: 0.18 });
            bodies.push({ id, shape: 'cylinder', r: 0.04, h, pos: [x, top + h / 2, 0], color: head > 0 ? '#38bdf8' : '#f87171', label: `${(st.P / 1000).toFixed(1)} kPa`, labelOffset: [0, h / 2 + 0.15, 0] });
          }
          const st2 = pipeState(p, 0);
          vectors.push({ id: 'v1', from: [XS[0] + 0.6, Y0 + D1 / 2 + 0.12, 0], vec: [p.v1 * 0.08, 0, 0], color: '#fbbf24', label: `v₁ = ${p.v1.toFixed(2)} m/s` });
          vectors.push({ id: 'v2', from: [-0.4, y2 - d2 / 2 - 0.15, 0], vec: [Math.min(2.5, st2.v * 0.08), 0, 0], color: '#f472b6', label: `v₂ = ${st2.v.toFixed(2)} m/s` });
          return { bodies, vectors };
        }
        const a = p.a, cy = s.yb + a / 2, fb = Fb(s.yb), k = 1.2 / Math.max(B.W, fb, 1); // force arrows scaled to fit
        const bodies = [{ id: 'block', shape: 'box', size: [a, a, a], pos: [0, cy, 0], color: p.rhoB > p.rhoF ? '#a8a29e' : '#d97706', metal: p.rhoB > 2000 ? 0.6 : 0.05, label: `${p.rhoB} kg/m³`, labelOffset: [0, a / 2 + 0.1, 0] }];
        const vectors = [
          { id: 'W', from: [0.0, cy, a / 2 + 0.05], vec: [0, -B.W * k, 0], color: '#7dd3fc', label: `mg = ${B.W.toFixed(1)} N` },
          { id: 'Fb', from: [0.1, cy, a / 2 + 0.05], vec: [0, fb * k, 0], color: '#4ade80', label: fb > 0 ? `F_b = ${fb.toFixed(1)} N` : '' },
        ];
        const lines = [];
        if (p.mode === 'scale') {
          const hookY = s.yb + a, scaleY = 2.1;
          bodies.push({ id: 'scale', shape: 'box', size: [0.16, 0.36, 0.12], pos: [0, scaleY, 0], color: '#e2e8f0', label: `scale: ${s.T.toFixed(1)} N`, labelOffset: [0.45, 0, 0] });
          lines.push({ id: 'cable', pts: [[0, scaleY - 0.18, 0], [0, hookY, 0]], color: s.T > 0 ? '#e2e8f0' : '#64748b', opacity: s.T > 0 ? 1 : 0.35 });
          lines.push({ id: 'arm', pts: [[0, 2.4, -0.5], [0, 2.4, 0], [0, scaleY + 0.18, 0]], color: '#94a3b8' });
          vectors.push({ id: 'T', from: [-0.1, s.yb + a, a / 2 + 0.05], vec: [0, s.T * k, 0], color: '#fbbf24', label: s.T > 0 ? `T = ${s.T.toFixed(1)} N` : '' });
        }
        if (s.phase === 'rest') vectors.push({ id: 'N', from: [-0.1, s.yb, a / 2 + 0.05], vec: [0, Math.max(0, B.W - fb) * k, 0], color: '#a5b4fc', label: 'N' });
        return { bodies, vectors, lines };
      },
    };
    return model;
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'pipe') {
      const v2 = continuityV2(area(D1), p.v1, area(p.r * D1));
      return [
        'A₁v₁ = A₂v₂  →  v₂ = v₁·(d₁/d₂)²',
        `v₂ = ${p.v1} × (1/${p.r})² = ${v2.toFixed(3)} m/s`,
        'P₁ + ½ρv₁² + ρgh₁ = P₂ + ½ρv₂² + ρgh₂',
        `P₁ − P₂ = ½·${p.rhoF}·(${v2.toFixed(2)}² − ${p.v1}²) + ${p.rhoF}·9.8·${p.dh} = ${m.dP.toFixed(2)} kPa`,
        `P₂ = ${m.P2.toFixed(2)} kPa${m.P2 < 0 ? '  (negative: the liquid would cavitate)' : ''}`,
      ];
    }
    const V = p.a ** 3, sd = m.frac / 100 * p.a;
    return [
      `m = ρ_block·a³ = ${p.rhoB} × ${p.a}³ = ${(p.rhoB * V).toFixed(2)} kg,  mg = ${m.W.toFixed(2)} N`,
      `F_b = ρ_fluid·g·a²·s = ${p.rhoF} × 9.8 × ${p.a}² × ${sd.toFixed(3)} = ${m.Fb.toFixed(2)} N`,
      `apparent weight = mg − F_b = ${m.Wapp.toFixed(2)} N`,
      `floating: s/a = ρ_block/ρ_fluid = ${p.rhoB}/${p.rhoF} = ${(100 * fractionSubmerged(p.rhoB, p.rhoF)).toFixed(1)} %`,
      `T_bob = 2π·√(ρ_block·a/(ρ_fluid·g)) = ${(2 * Math.PI * Math.sqrt(p.rhoB * p.a / (p.rhoF * g))).toFixed(3)} s (undamped)`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'drop' && Math.abs(r.final.frac - 60) <= 1 && Math.abs(r.final.v) < 0.01 && r.final.N === 0),
    ({ runs }) => runs.some(r => r.params.mode === 'scale' && r.final.frac >= 100 - 1e-9 && r.final.T > 0 && Math.abs(r.final.T / r.final.W - 0.5) <= 0.01 && Math.abs(r.final.v) < 1e-12),
    ({ runs }) => runs.some(r => r.params.mode === 'pipe' && r.params.dh === 0 && Math.abs(r.final.dP - 20) <= 1 && r.final.xp >= XS[5] - 1e-9),
  ],
  evaluate(p) {
    const W = p.rhoB * p.a ** 3 * g, Fb = buoyantForce(p.rhoF, p.a ** 3);
    return { vars: { a: p.a, rhoB: p.rhoB, rhoF: p.rhoF }, answer: Math.max(0, W - Fb), unit: 'N', tol: 0.02 };
  },
};
