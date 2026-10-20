// Lab 10 — Rotation and Torque Lab. Two experiments share one apparatus area:
//  • torque: a rigid body on a fixed axle is spun up by a cord pulled with force F at angle φ from the radius
//    (τ = R·F·sinφ) for tOn seconds, against an optional constant axle-friction torque; exact piecewise
//    constant-α updates (the step is split at the moment the force stops and at the moment the body stops);
//  • roll: a hoop, a disk, a hollow sphere, and a solid sphere roll without slipping 4 m down an incline,
//    each with a = g·sinθ/(1 + β), β = I/(m r²) — exact constant-acceleration kinematics.
import { inertia, shapeFactor, rollingAccel, C } from '../../physics/index.js';

const AX = [0, 1.6, 0];      // axle position (torque mode)
const DIST = 4;              // rolling distance along the incline (m)
const TEND = 12;             // torque-mode run length cap (s)
const RACERS = [
  { id: 'hoop', name: 'Hoop', key: 'Hoop', color: '#f87171' },
  { id: 'hollowSphere', name: 'Hollow sphere', key: 'Hollow', color: '#c084fc' },
  { id: 'disk', name: 'Disk', key: 'Disk', color: '#38bdf8' },
  { id: 'solidSphere', name: 'Solid sphere', key: 'Solid', color: '#fbbf24' },
];
const SHAPES = { hoop: 'Hoop (I = MR²)', disk: 'Solid disk (I = ½MR²)', solidSphere: 'Solid sphere (I = ⅖MR²)', hollowSphere: 'Hollow sphere (I = ⅔MR²)', rod: 'Rod about its centre (I = ¹⁄₁₂M(2R)²)' };
const momentOf = (shape, M, R) => (shape === 'rod' ? inertia.rodCenter(M, 2 * R) : inertia[shape](M, R));
const rollerOf = shape => (shape === 'rod' ? 'disk' : shape); // a rod cannot roll; the race highlights the disk instead
const rad = d => d * Math.PI / 180;
const lane = p => Math.max(0.9, 2.4 * p.R);
const ramp = p => { const Lh = DIST + 0.5 + p.R * Math.tan(rad(p.theta) / 2); return { Lh, x0: -2.6, H: Lh * Math.sin(rad(p.theta)), u0: 0.25 }; };

export default {
  num: 10, unit: 9, sections: ['9.1', '9.2', '9.3', '9.5', '9.6', '9.7', '9.8'],
  dt: 1 / 240, sampleEvery: 1 / 30,
  text: {
    title: 'Rotation and Torque Lab',
    question: 'How does a torque change a body’s rotation, how does the distribution of its mass (moment of inertia) resist that change, and why do round objects of different shapes roll down a ramp at different rates?',
    params: { mode: 'Experiment', shape: 'Shape', M: 'Mass M', R: 'Radius R (rod: half-length)', F: 'Cord force F', phi: 'Angle between cord and radius φ', tOn: 'Force duration', tf: 'Axle friction torque', theta: 'Incline angle θ (race)' },
    options: { torque: 'Torque on a fixed axle', roll: 'Rolling race down an incline', ...SHAPES },
    graph: ['angular velocity ω (rad/s)', 'angle turned θ (rad)', 'net torque and angular momentum', 'race: speeds of all four (m/s)'],
    series: { w: 'ω', ang: 'θ', tauNet: 'τnet (N·m)', L: 'L (kg·m²/s)', vHoop: 'hoop', vHollow: 'hollow sphere', vDisk: 'disk', vSolid: 'solid sphere' },
    measures: { t: 'Time', ang: 'Angle turned θ', revs: 'Revolutions', w: 'Angular velocity ω', alpha: 'Angular acceleration α', tauA: 'Applied torque R·F·sinφ', tauNet: 'Net torque', I: 'Moment of inertia', L: 'Angular momentum Iω', KErot: 'Rotational KE', alphaOn: 'Measured spin-up α (ω at release ÷ tOn)', Loff: 'Angular momentum at release', s: 'Distance rolled', v: 'Speed', a: 'Acceleration along incline', wr: 'Spin rate ω = v/R', KEt: 'Translational KE', KEr: 'Rotational KE', frac: 'Fraction of KE that is rotational', tFin: 'Finish time (highlighted shape)', tHoop: 'Hoop finish time', tHollow: 'Hollow sphere finish time', tDisk: 'Disk finish time', tSolid: 'Solid sphere finish time', vHoop: 'Hoop speed', vHollow: 'Hollow sphere speed', vDisk: 'Disk speed', vSolid: 'Solid sphere speed', beta: 'Shape factor β = I/(MR²)' },
    predict: {
      prompt: 'A hoop, a hollow sphere, a solid disk, and a solid sphere — all with the same mass and radius — are released together at the top of the same incline and roll without slipping. Which reaches the bottom first?',
      choices: ['The hoop', 'The hollow sphere', 'The disk', 'The solid sphere', 'They all tie'],
    },
    guided: [
      'Race (default settings). Record the four finish times. Rank the shapes and connect the order to β = I/(MR²) shown for each shape.',
      'Race again with a different mass and radius but the same angle. Do the finish times change? Use a = g·sinθ/(1 + β) to explain why M and R cancel.',
      'Switch to “Torque on a fixed axle” with a disk, F = 10 N, φ = 90°, no friction. Check that α = τ/I using the readouts, then change only φ to 30° and explain the halved torque.',
      'Keep the same torque and switch the shape from disk to hoop. Predict, then measure, how the spin-up angular acceleration changes.',
      'Add axle friction (τf = 0.5 N·m). After the force stops, measure the spin-down α from the ω graph and compare with −τf/I. Use the energy bars to show that work by the cord = rotational KE + thermal energy.',
      'Use the torque–angular-momentum graph to verify the rotational impulse theorem: τnet·Δt = ΔL.',
    ],
    challenges: [
      'Torque experiment: produce a measured spin-up angular acceleration of 2.00 rad/s² (±0.05) and let the force finish its pull.',
      'Torque experiment: give the body an angular momentum of exactly 10.0 kg·m²/s (±0.2) at the moment the force stops.',
      'Race: record two races with the same incline angle and highlighted shape but a different mass AND a different radius, whose finish times agree within 0.5%.',
    ],
    evaluate: 'Before you run the race: an object with shape factor β = {beta} (I = β·M·R²) starts from rest and rolls without slipping {d} m down a {theta}° incline. Calculate the time it takes to reach the finish (g = 9.8 m/s²).',
    honors: {
      prompt: 'Use energy conservation to show that a rolling object’s speed after dropping a height h is v = √(2gh/(1 + β)), and that the fraction of its kinetic energy that is rotational is β/(1 + β). Then verify both for the hoop and the solid sphere using the race readouts.',
      solution: 'Mgh = ½Mv² + ½Iω² with ω = v/R and I = βMR² gives Mgh = ½Mv²(1 + β), so v = √(2gh/(1 + β)). KE_rot/KE_total = ½βMv² / [½(1 + β)Mv²] = β/(1 + β): ½ for the hoop (β = 1) and 2/7 ≈ 0.286 for the solid sphere (β = 0.4). Neither depends on M or R, which is why the race order is set by shape alone.',
    },
    assumptions: [
      'All bodies are rigid with uniform density; moments of inertia are the textbook values: hoop MR², disk ½MR², solid sphere ⅖MR², hollow sphere ⅔MR², rod of length 2R about its centre ¹⁄₁₂M(2R)².',
      'Torque experiment: the cord is wrapped around a light drum of radius R on the axle, so its lever arm is always R; the force is constant while it acts. Axle friction is a constant torque τf opposing the rotation; the body starts only if the applied torque exceeds τf (static = kinetic).',
      'Race: every object rolls without slipping (static friction does no work), there is no rolling resistance or air drag, and the racers stop at the finish line. A rod cannot roll, so the race highlights the disk when the rod is selected.',
      'The time steps are exact for constant angular (and linear) acceleration; the run is split exactly where the force switches off or the body comes to rest. g = 9.8 m/s².',
      'Spokes, stripes, and rim markers are drawn only so the rotation can be seen; lanes are spaced so that large racers do not overlap.',
    ],
  },
  params: [
    { id: 'mode', value: 'roll', options: [{ value: 'roll', label: 'Rolling race down an incline' }, { value: 'torque', label: 'Torque on a fixed axle' }] },
    { id: 'shape', value: 'disk', options: Object.entries(SHAPES).map(([value, label]) => ({ value, label })) },
    { id: 'M', min: 0.5, max: 10, step: 0.5, value: 2, unit: 'kg' },
    { id: 'R', min: 0.1, max: 1, step: 0.05, value: 0.4, unit: 'm' },
    { id: 'F', min: 0, max: 40, step: 0.5, value: 10, unit: 'N' },
    { id: 'phi', min: 10, max: 90, step: 5, value: 90, unit: '°' },
    { id: 'tOn', min: 0.5, max: 6, step: 0.5, value: 3, unit: 's' },
    { id: 'tf', min: 0, max: 2, step: 0.05, value: 0, unit: 'N·m' },
    { id: 'theta', min: 5, max: 40, step: 1, value: 20, unit: '°' },
  ],
  camera: { target: [-0.3, 1.2, 0], dist: 8, free: [0.35, 0.3, 1] },
  view2d: { span: 8.5, cx: -0.3, cy: 1.4 },
  graph: {
    choices: [
      { label: 'angular velocity ω (rad/s)', y: ['w'], labels: ['w'], yLabel: 'ω (rad/s)' },
      { label: 'angle turned θ (rad)', y: ['ang'], labels: ['ang'], yLabel: 'θ (rad)' },
      { label: 'net torque and angular momentum', y: ['tauNet', 'L'], labels: ['tauNet', 'L'], yLabel: 'τ (N·m), L (kg·m²/s)' },
      { label: 'race: speeds of all four (m/s)', y: ['vHoop', 'vHollow', 'vDisk', 'vSolid'], labels: ['vHoop', 'vHollow', 'vDisk', 'vSolid'], yLabel: 'v (m/s)' },
    ],
  },
  recordKeys: ['alphaOn', 'Loff', 'tFin', 'tHoop', 'tHollow', 'tDisk', 'tSolid'],
  decor: p => {
    const out = [{ shape: 'ground', size: 40 }];
    if (p.mode === 'torque') {
      out.push(
        { shape: 'box', size: [1.4, 0.12, 1.0], pos: [0, 0.06, -0.45], color: '#334155' },
        { shape: 'box', size: [0.16, AX[1], 0.16], pos: [0, AX[1] / 2, -0.45], color: '#475569', metal: 0.5 },
        { shape: 'cylinder', r: 0.05, h: 0.5, pos: [0, AX[1], -0.25], rot: [Math.PI / 2, 0, 0], color: '#94a3b8', metal: 0.8 },
        { shape: 'label', text: 'axle', pos: [0.25, AX[1] - 0.25, -0.45] },
      );
    } else {
      const g = ramp(p), th = rad(p.theta), W = lane(p) * RACERS.length + 0.4;
      const at = u => [g.x0 + u * Math.cos(th), g.H - u * Math.sin(th)];
      const [fx, fy] = at(g.u0 + DIST), [sx, sy] = at(g.u0);
      out.push(
        { shape: 'ramp', angle: p.theta, length: g.Lh, x: g.x0, y: 0, depth: W, color: '#475569' },
        { shape: 'line', pts: [[fx, fy + 0.01, -W / 2], [fx, fy + 0.01, W / 2]], color: '#f8fafc' },
        { shape: 'line', pts: [[sx, sy + 0.01, -W / 2], [sx, sy + 0.01, W / 2]], color: '#4ade80' },
        { shape: 'label', text: 'finish', pos: [fx + 0.3, fy + 0.15, W / 2] },
        { shape: 'label', text: `start · ${DIST} m to go`, pos: [sx, sy + 2.2 * p.R + 0.3, W / 2] },
      );
    }
    return out;
  },
  create(p) {
    const roll = p.mode === 'roll', I = momentOf(p.shape, p.M, p.R), tauA = p.R * p.F * Math.sin(rad(p.phi));
    const s = { t: 0, ang: 0, w: 0, alpha: 0, Wa: 0, Q: 0, wOff: null, done: false, events: [] };
    const hi = rollerOf(p.shape), betaHi = shapeFactor[hi];
    const racers = RACERS.map(r => ({ ...r, beta: shapeFactor[r.id], a: rollingAccel(p.theta, shapeFactor[r.id]), s: 0, v: 0, tFin: 0 }));
    const H = racers.find(r => r.id === hi);
    const applied = () => (s.t < p.tOn - 1e-12 ? tauA : 0);
    const netAlpha = () => { const ta = applied(); if (s.w === 0 && ta <= p.tf) return 0; return (ta - p.tf) / I; };

    function stepTorque(h) {
      let left = h;
      while (left > 1e-13) {
        const ta = applied(), seg0 = s.t < p.tOn ? Math.min(left, p.tOn - s.t) : left;
        let seg = seg0; const al = netAlpha(); let stopped = false;
        if (al < 0 && s.w + al * seg < 0) { seg = -s.w / al; stopped = true; }
        const dth = s.w * seg + 0.5 * al * seg * seg;
        s.ang += dth; s.Wa += ta * dth; s.Q += (s.w > 0 || al > 0 ? p.tf : 0) * dth;
        s.w = stopped ? 0 : s.w + al * seg; s.alpha = al; s.t += seg; left -= seg;
        if (s.wOff === null && s.t >= p.tOn - 1e-12) { s.t = Math.max(s.t, p.tOn); s.wOff = s.w; }
        if (stopped) s.alpha = netAlpha();
      }
      s.alpha = netAlpha();
      if (s.t >= TEND - 1e-12 || (s.wOff !== null && s.w === 0)) s.done = true;
    }
    function stepRoll(h) {
      s.t += h;
      for (const r of racers) {
        if (r.tFin) continue;
        r.s = 0.5 * r.a * s.t * s.t; r.v = r.a * s.t;
        if (r.s >= DIST) { r.tFin = Math.sqrt(2 * DIST / r.a); r.s = DIST; r.v = r.a * r.tFin; }
      }
      if (racers.every(r => r.tFin)) s.done = true;
    }
    const geo = roll ? ramp(p) : null, th = rad(p.theta);
    const centre = r => { const u = geo.u0 + r.s; return [geo.x0 + u * Math.cos(th) + p.R * Math.sin(th), geo.H - u * Math.sin(th) + p.R * Math.cos(th)]; };

    // body meshes for a shape centred at c spinning by angle q about z
    function shapeBodies(id, shape, c, q, color, label) {
      const R = p.R, out = [], z = c[2] || 0;
      if (shape === 'hoop') out.push({ id, shape: 'torus', r: R * 0.94, tube: R * 0.06, pos: c, color, metal: 0.5, label });
      else if (shape === 'disk') out.push({ id, shape: 'sphere', r: R, scale: [1, 1, 0.16], pos: c, color, metal: 0.3, label });
      else if (shape === 'rod') out.push({ id, shape: 'box', size: [2 * R, 0.08, 0.08], pos: c, rot: [0, 0, q], color, metal: 0.4, label });
      else out.push({ id, shape: 'sphere', r: R, pos: c, color, opacity: shape === 'hollowSphere' ? 0.55 : undefined, metal: 0.3, label });
      if (shape === 'hoop' || shape === 'disk') {
        const dz = shape === 'disk' ? 0.17 * R : 0;
        out.push({ id: id + '-sp', shape: 'box', size: [1.84 * R, 0.035 * R + 0.01, 0.02], pos: [c[0], c[1], z + dz], rot: [0, 0, q], color: '#0f172a' });
        out.push({ id: id + '-sp2', shape: 'box', size: [1.84 * R, 0.035 * R + 0.01, 0.02], pos: [c[0], c[1], z + dz], rot: [0, 0, q + Math.PI / 2], color: '#0f172a' });
      }
      if (shape === 'solidSphere' || shape === 'hollowSphere') out.push({ id: id + '-st', shape: 'torus', r: R * 1.005, tube: 0.025 * R + 0.004, pos: c, rot: [-Math.PI / 2, -q, 0], color: '#0f172a' });
      out.push({ id: id + '-mk', shape: 'sphere', r: 0.05 + 0.04 * R, pos: [c[0] + R * Math.cos(q), c[1] + R * Math.sin(q), z + (shape === 'disk' ? 0.12 * R : 0)], color: '#f8fafc', emissive: '#f8fafc', glow: 0.4 });
      return out;
    }

    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) { if (s.done) return; roll ? stepRoll(dt) : stepTorque(dt); },
      measures() {
        const L = I * s.w, rot = !roll, rc = !roll;
        const KEt = 0.5 * p.M * H.v * H.v, KEr = 0.5 * betaHi * p.M * H.v * H.v;
        const ta = applied(), tn = s.w === 0 && ta <= p.tf ? 0 : ta - (s.w > 0 || ta > p.tf ? p.tf : 0);
        const aOn = s.wOff !== null ? s.wOff / p.tOn : s.t > 0 ? s.w / s.t : 0;
        const list = [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'ang', label: 'Angle turned θ', value: s.ang, unit: 'rad', ref: 200, hidden: !rot },
          { id: 'revs', label: 'Revolutions', value: s.ang / (2 * Math.PI), unit: 'rev', ref: 30, hidden: !rot },
          { id: 'w', label: 'Angular velocity ω', value: s.w, unit: 'rad/s', ref: 60, hidden: !rot },
          { id: 'alpha', label: 'Angular acceleration α', value: s.alpha, unit: 'rad/s²', ref: 20, hidden: !rot },
          { id: 'tauA', label: 'Applied torque R·F·sinφ', value: ta, unit: 'N·m', ref: 40, hidden: !rot },
          { id: 'tauNet', label: 'Net torque', value: tn, unit: 'N·m', ref: 40, hidden: !rot },
          { id: 'I', label: 'Moment of inertia', value: I, unit: 'kg·m²', ref: 10, hidden: !rc },
          { id: 'L', label: 'Angular momentum Iω', value: L, unit: 'kg·m²/s', ref: 50, hidden: !rot },
          { id: 'KErot', label: 'Rotational KE', value: 0.5 * I * s.w * s.w, unit: 'J', ref: 500, hidden: !rot },
          { id: 'alphaOn', label: 'Measured spin-up α (ω at release ÷ tOn)', value: aOn, unit: 'rad/s²', ref: 20, hidden: !rot },
          { id: 'Loff', label: 'Angular momentum at release', value: s.wOff !== null ? I * s.wOff : 0, unit: 'kg·m²/s', ref: 50, hidden: !rot },
          { id: 'beta', label: 'Shape factor β = I/(MR²)', value: roll ? betaHi : I / (p.M * p.R * p.R), unit: '', ref: 1 },
          { id: 's', label: 'Distance rolled', value: H.s, unit: 'm', ref: DIST, hidden: !roll },
          { id: 'v', label: 'Speed', value: H.v, unit: 'm/s', ref: 6, hidden: !roll },
          { id: 'a', label: 'Acceleration along incline', value: H.a, unit: 'm/s²', ref: 6, hidden: !roll },
          { id: 'wr', label: 'Spin rate ω = v/R', value: H.v / p.R, unit: 'rad/s', ref: 60, hidden: !roll },
          { id: 'KEt', label: 'Translational KE', value: KEt, unit: 'J', ref: 100, hidden: !roll },
          { id: 'KEr', label: 'Rotational KE', value: KEr, unit: 'J', ref: 100, hidden: !roll },
          { id: 'frac', label: 'Fraction of KE that is rotational', value: betaHi / (1 + betaHi), unit: '', ref: 1, hidden: !roll },
          { id: 'tFin', label: 'Finish time (highlighted shape)', value: H.tFin, unit: 's', ref: 4, hidden: !roll },
        ];
        for (const r of racers) list.push({ id: 't' + r.key, label: `${r.name} finish time`, value: r.tFin, unit: 's', ref: 4, hidden: !roll });
        for (const r of racers) list.push({ id: 'v' + r.key, label: `${r.name} speed`, value: r.v, unit: 'm/s', ref: 6, hidden: true });
        return list;
      },
      energy() {
        if (roll) {
          const v2 = H.v * H.v;
          return [
            { label: 'PE lost Mg·s·sinθ', value: p.M * C.g * H.s * Math.sin(th), color: '#60a5fa' },
            { label: 'KE translational', value: 0.5 * p.M * v2, color: '#fbbf24' },
            { label: 'KE rotational', value: 0.5 * betaHi * p.M * v2, color: '#c084fc' },
          ];
        }
        return [
          { label: 'Work by cord τ·θ', value: s.Wa, color: '#4ade80' },
          { label: 'Rotational KE ½Iω²', value: 0.5 * I * s.w * s.w, color: '#fbbf24' },
          { label: 'Thermal (axle friction)', value: s.Q, color: '#f87171' },
        ];
      },
      scene() {
        if (roll) {
          const bodies = [], vectors = [], W = lane(p);
          racers.forEach((r, i) => {
            const [x, y] = centre(r), z = (i - (racers.length - 1) / 2) * W, c = [x, y, z];
            const lbl = r.id === hi ? `▶ ${r.name}${r.tFin ? ` ${r.tFin.toFixed(3)} s` : ''}` : `${r.name}${r.tFin ? ` ${r.tFin.toFixed(3)} s` : ''}`;
            bodies.push(...shapeBodies(r.id, r.id, c, -r.s / p.R, r.color, lbl));
            if (r.id === hi) {
              vectors.push({ id: 'v', from: c, vec: [Math.cos(th) * r.v * 0.35, -Math.sin(th) * r.v * 0.35, 0], color: '#4ade80', label: `v = ${r.v.toFixed(2)} m/s` });
              vectors.push({ id: 'a', from: [c[0], c[1] + p.R + 0.1, z], vec: [Math.cos(th) * r.a * 0.3, -Math.sin(th) * r.a * 0.3, 0], color: '#fbbf24', label: `a = ${r.a.toFixed(2)} m/s²` });
            }
          });
          return { bodies, vectors };
        }
        const on = applied() > 0, P = [AX[0], AX[1] + p.R, 0.05], ph = rad(p.phi), dir = [-Math.sin(ph), Math.cos(ph), 0], k = 0.045;
        const bodies = shapeBodies('body', p.shape, [...AX], s.ang, '#38bdf8', `${p.M} kg · I = ${I.toFixed(3)} kg·m²`);
        bodies.push({ id: 'hub', shape: 'sphere', r: 0.07, pos: [AX[0], AX[1], 0], color: '#cbd5e1', metal: 0.8 });
        const cordEnd = on ? [P[0] + dir[0] * 1.6, P[1] + dir[1] * 1.6, P[2]] : P;
        return {
          bodies,
          lines: [{ id: 'cord', pts: [P, cordEnd], color: on ? '#fde68a' : '#475569' }],
          vectors: [
            { id: 'F', from: P, vec: on ? [dir[0] * p.F * k, dir[1] * p.F * k, 0] : [0, 0, 0], color: '#fbbf24', label: on ? `F = ${p.F} N` : '' },
            { id: 'r', from: [AX[0], AX[1], 0.05], vec: [0, p.R, 0], color: '#94a3b8', label: 'r' },
            { id: 'w', from: [AX[0] + 0.12, AX[1], 0], vec: [0, 0, Math.min(2.5, s.w * 0.08)], color: '#4ade80', label: s.w ? `ω = ${s.w.toFixed(2)} rad/s` : '' },
            { id: 'tau', from: [AX[0] - 0.12, AX[1], 0], vec: [0, 0, Math.max(-2.5, Math.min(2.5, (s.w === 0 && applied() <= p.tf ? 0 : applied() - p.tf) * 0.12))], color: '#f472b6', label: 'τnet' },
          ],
        };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'roll') {
      const b = m.beta;
      return [
        `a = g·sinθ/(1 + β) = 9.8 × sin ${p.theta}° / (1 + ${b.toFixed(3)}) = ${m.a.toFixed(3)} m/s²`,
        `t = √(2d/a) = √(2 × ${DIST} / ${m.a.toFixed(3)}) = ${Math.sqrt(2 * DIST / m.a).toFixed(3)} s`,
        `v = a·t = ${m.v.toFixed(3)} m/s;  ω = v/R = ${m.wr.toFixed(2)} rad/s`,
        `Mg·s·sinθ = ½Mv²(1 + β): ${(p.M * 9.8 * m.s * Math.sin(p.theta * Math.PI / 180)).toFixed(3)} J = ${(m.KEt + m.KEr).toFixed(3)} J`,
        `KE_rot / KE = β/(1 + β) = ${m.frac.toFixed(3)}`,
      ];
    }
    return [
      `I = β·M·R² = ${(m.I / (p.M * p.R * p.R)).toFixed(4)} × ${p.M} × ${p.R}² = ${m.I.toFixed(4)} kg·m²  (${SHAPES[p.shape]})`,
      `τ = R·F·sinφ = ${p.R} × ${p.F} × sin ${p.phi}° = ${(p.R * p.F * Math.sin(p.phi * Math.PI / 180)).toFixed(3)} N·m (while t < ${p.tOn} s)`,
      `α = τnet/I = ${m.tauNet.toFixed(3)} / ${m.I.toFixed(4)} = ${m.alpha.toFixed(3)} rad/s²`,
      `ω = ${m.w.toFixed(3)} rad/s;  L = Iω = ${m.L.toFixed(3)} kg·m²/s`,
      `KE_rot = ½Iω² = ${m.KErot.toFixed(3)} J`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'torque' && r.final.Loff > 0 && Math.abs(r.final.alphaOn - 2) <= 0.05),
    ({ runs }) => runs.some(r => r.params.mode === 'torque' && r.final.Loff > 0 && Math.abs(r.final.Loff - 10) <= 0.2),
    ({ runs }) => runs.some(r1 => runs.some(r2 => r1 !== r2 && r1.params.mode === 'roll' && r2.params.mode === 'roll' && r1.params.theta === r2.params.theta &&
      rollerOf(r1.params.shape) === rollerOf(r2.params.shape) && r1.params.M !== r2.params.M && r1.params.R !== r2.params.R &&
      r1.final.tFin > 0 && r2.final.tFin > 0 && Math.abs(r2.final.tFin / r1.final.tFin - 1) <= 0.005)),
  ],
  evaluate(p) {
    const beta = shapeFactor[rollerOf(p.shape)];
    return { vars: { beta, theta: p.theta, d: DIST }, answer: Math.sqrt(2 * DIST / rollingAccel(p.theta, beta)), unit: 's', tol: 0.02 };
  },
};
