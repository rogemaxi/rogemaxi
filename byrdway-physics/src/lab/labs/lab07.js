// Lab 7 — Energy Transformation Lab. A car locked to a smooth track (spring-launched roller-coaster profile or a
// half-pipe), with optional kinetic friction. Live KE / gravitational PE / spring PE / thermal bars; total conserved.
import { rk4Step, C } from '../../physics/index.js';

const BASE = 0.5;               // coaster: height of the flat run after the drop, m
const HILL_X = 15, HILL_W = 4;  // coaster hill centre and half-width, m
const DROP_W = 6;               // coaster drop from x = 0 to x = 6 m
const XEND = 26;                // coaster end of track, m
const HP_C = 12, HP_W = 6, HP_H = 6; // half-pipe centre, half-width and rim height, m
const WALL = -0.75;             // spring launcher wall (coaster), m; the spring's free end sits at x = 0
const TMAX = 20, HOLD = 1.5;

// C2-smooth profile pieces (value, 1st and 2nd derivative)
const smooth = u => (u <= 0 ? [0, 0, 0] : u >= 1 ? [1, 0, 0] : [u ** 3 * (10 - 15 * u + 6 * u * u), 30 * u * u * (1 - u) ** 2, 60 * u * (1 - u) * (1 - 2 * u)]);
const bump = u => (Math.abs(u) >= 1 ? [0, 0, 0] : [(1 - u * u) ** 3, -6 * u * (1 - u * u) ** 2, -6 * (1 - u * u) ** 2 + 24 * u * u * (1 - u * u)]);

export function profile(p) {
  if (p.track === 'halfpipe') {
    const a = HP_H / (HP_W * HP_W);
    return x => { const u = x - HP_C; return [a * u * u, 2 * a * u, 2 * a]; };
  }
  return x => {
    const [S, S1, S2] = smooth(x / DROP_W), [B, B1, B2] = bump((x - HILL_X) / HILL_W), dH = p.H - BASE, dh = p.Hh - BASE;
    return [BASE + dH * (1 - S) + dh * B, -dH * S1 / DROP_W + dh * B1 / HILL_W, -dH * S2 / (DROP_W * DROP_W) + dh * B2 / (HILL_W * HILL_W)];
  };
}
const startX = p => (p.track === 'halfpipe' ? HP_C - HP_W * Math.sqrt(p.H / HP_H) : -p.xc);
const springOn = p => p.track !== 'halfpipe';
const springPE = (p, x) => (springOn(p) && x < 0 ? 0.5 * p.k * x * x : 0);
const lowest = p => (p.track === 'halfpipe' ? 0 : BASE);

export default {
  num: 7, unit: 6, sections: ['6.2', '6.3', '6.4', '6.5', '6.6', '6.7'],
  text: {
    title: 'Energy Transformation Lab',
    question: 'As a car is launched by a spring and rolls over hills, how is its energy shared among kinetic, potential and thermal forms — and is the total conserved?',
    params: { track: 'Track', m: 'Car mass', H: 'Starting height', Hh: 'Hill height (coaster)', k: 'Spring constant k (coaster)', xc: 'Spring compression (coaster)', mu: 'Rolling-friction coefficient μ' },
    options: { coaster: 'Spring launch + drop + hill', halfpipe: 'Half-pipe (released from rest)' },
    graph: ['energies vs time (J)', 'energies vs position x (J)', 'speed v (m/s)', 'height h (m)'],
    series: { KE: 'KE', PEg: 'PE gravity', PEs: 'PE spring', Q: 'thermal', E: 'total' },
    measures: { t: 'Time', x: 'Position x', h: 'Height', v: 'Speed', KE: 'Kinetic energy', PEg: 'Gravitational PE', PEs: 'Spring PE', Q: 'Thermal energy', E: 'Total energy', N: 'Normal force', vMax: 'Maximum speed' },
    predict: {
      prompt: 'Friction is off. The car starts on a 4.0 m platform, the spring is barely compressed (about 1 J), and the hill ahead is 4.5 m tall. What will happen?',
      choices: ['It clears the hill because it speeds up on the drop', 'It stops exactly on top of the hill', 'It climbs part-way up the hill, rolls back, and returns to about its starting height', 'It stops at the bottom of the drop'],
    },
    guided: [
      'Coaster, μ = 0: run with the default settings and watch the energy bars. Which bar stays the same length the whole run?',
      'Set the hill to 3.0 m. Use the "energies vs position" graph to find where KE is largest and explain why using mgh.',
      'Change the spring compression from 0.10 m to 0.20 m (k fixed). By what factor does the spring PE change? Check with ½kx².',
      'Choose the half-pipe and release from 4 m with μ = 0, then μ = 0.05. Compare the heights reached on each swing and account for the "missing" energy.',
      'Change the car’s mass with friction off. Does the speed at the bottom change? Use ½mv² = mgh to explain.',
    ],
    challenges: [
      'Friction off, coaster with a hill taller than the platform: use the spring so the car just clears the hill — speed over the top between 0 and 1.0 m/s — and reaches the end.',
      'Half-pipe with friction on (μ > 0): choose the release height and μ so the car’s first turning point on the far side is 3.00 m high (±0.05 m).',
      'Friction off, coaster: launch the car so it reaches the end of the track at exactly 6.0 m/s (±0.1 m/s).',
    ],
    evaluate: 'Before you run (ignore friction): the {m} kg car starts at {H} m with {Es} J stored in the spring. Calculate its speed at the lowest point of the track, h = {hlow} m (g = 9.8 m/s²).',
    honors: {
      prompt: 'With friction on, the thermal energy is not just μ·mg·(distance). Explain why the normal force — and so the friction — is larger in the valleys and smaller over the hilltops, then design a half-pipe run that shows the effect.',
      solution: 'On a curved track the car needs a centripetal force: N − mg·cosφ = m·v²·κ (κ = curvature, positive in a valley). So N = m(g·cosφ + v²κ), larger than mg·cosφ in a valley and smaller over a crest. Friction μN and the thermal energy ∫μN ds therefore grow with speed. In the half-pipe (κ > 0 everywhere) a release from 6 m with μ = 0.05 loses more energy on the first swing than a release from 2 m loses in proportion, and the thermal bar grows fastest as the car passes the bottom at high speed.',
    },
    assumptions: [
      'The car is a particle locked to the rails (as on a real coaster), so it never leaves the track; the normal force may point either way and friction uses its magnitude.',
      'Friction is a constant coefficient μ times the normal force N = m(g·cosφ + v²κ), which includes the centripetal effect of the track’s curvature κ. The static coefficient is taken equal to μ. Air drag and wheel rotation are neglected.',
      'The spring (coaster only) is ideal and massless, obeys F = −kx while compressed, and does not stick to the car; the half-pipe has no spring.',
      'g = 9.8 m/s². Heights are measured from the ground. The equation of motion along the track is integrated with RK4 (dt = 1/240 s); turning points are located by bisection so the car stops exactly when static friction can hold it.',
      'The track profile is a smooth (C²) curve, so the normal force never jumps; the run ends at the end of the coaster track, after 20 s, or when the car has been at rest for 1.5 s.',
    ],
  },
  params: [
    { id: 'track', value: 'coaster', options: [{ value: 'coaster', label: 'Spring launch + drop + hill' }, { value: 'halfpipe', label: 'Half-pipe (released from rest)' }] },
    { id: 'm', min: 0.5, max: 10, step: 0.5, value: 2, unit: 'kg' },
    { id: 'H', min: 1, max: 6, step: 0.1, value: 4, unit: 'm' },
    { id: 'Hh', min: 0.5, max: 6, step: 0.1, value: 4.5, unit: 'm' },
    { id: 'k', min: 100, max: 3000, step: 50, value: 1000, unit: 'N/m' },
    { id: 'xc', min: 0.05, max: 0.5, step: 0.01, value: 0.05, unit: 'm' },
    { id: 'mu', min: 0, max: 0.3, step: 0.01, value: 0, unit: '' },
  ],
  camera: { target: [12.5, 2.6, 0], dist: 25, free: [0.12, 0.25, 1], followId: 'car' },
  view2d: { span: 30, cx: 12.5, cy: 3 },
  graph: {
    choices: [
      { label: 'energies vs time (J)', y: ['KE', 'PEg', 'PEs', 'Q', 'E'], labels: ['KE', 'PEg', 'PEs', 'Q', 'E'], yLabel: 'E (J)' },
      { label: 'energies vs position x (J)', x: 'x', xLabel: 'x (m)', y: ['KE', 'PEg', 'PEs', 'Q', 'E'], labels: ['KE', 'PEg', 'PEs', 'Q', 'E'], yLabel: 'E (J)' },
      { label: 'speed v (m/s)', y: ['v'], labels: ['v'], yLabel: 'v (m/s)' },
      { label: 'height h (m)', y: ['h'], labels: ['h'], yLabel: 'h (m)' },
    ],
  },
  recordKeys: ['vMax', 'v', 'h', 'Q', 'E'],
  decor: p => {
    const h = profile(p), hp = p.track === 'halfpipe';
    const x0 = hp ? HP_C - HP_W : WALL, x1 = hp ? HP_C + HP_W : XEND + 1;
    const n = 160, pts = z => Array.from({ length: n + 1 }, (_, i) => { const x = x0 + (x1 - x0) * i / n; return [x, h(x)[0], z]; });
    const items = [
      { shape: 'ground', size: 80 },
      { shape: 'line', pts: pts(0.35), color: '#94a3b8' },
      { shape: 'line', pts: pts(-0.35), color: '#94a3b8' },
    ];
    for (let x = Math.ceil(x0); x <= x1; x += hp ? 1 : 2) { const y = h(x)[0]; if (y > 0.12) items.push({ shape: 'box', size: [0.08, y - 0.05, 0.08], pos: [x, (y - 0.05) / 2, -0.35], color: '#334155' }, { shape: 'box', size: [0.08, y - 0.05, 0.08], pos: [x, (y - 0.05) / 2, 0.35], color: '#334155' }); }
    if (!hp) {
      items.push({ shape: 'box', size: [0.15, 1, 1.0], pos: [WALL - 0.08, p.H + 0.45, 0], color: '#64748b' });
      items.push({ shape: 'label', text: `hill ${p.Hh} m`, pos: [HILL_X, p.Hh + 0.9, 0], color: '#94a3b8' });
      items.push({ shape: 'label', text: 'end', pos: [XEND, BASE + 0.8, 0], color: '#94a3b8' });
      items.push({ shape: 'box', size: [0.1, 0.6, 1.0], pos: [XEND + 1, BASE + 0.3, 0], color: '#f87171' });
    }
    items.push({ shape: 'label', text: `start ${p.H} m`, pos: [startX(p), p.H + 0.9, 0], color: '#94a3b8' });
    return items;
  },
  create(p) {
    const g = C.g, h = profile(p), mu = p.mu, sp = springOn(p);
    // geometry at x: slope h1 → sinφ, cosφ; curvature κ
    const geo = x => { const [y, h1, h2] = h(x), q = Math.sqrt(1 + h1 * h1); return { y, h1, q, sn: h1 / q, cs: 1 / q, kap: h2 / (q * q * q) }; };
    const drive = (x, G = geo(x)) => -g * G.sn + (sp && x < 0 ? -(p.k / p.m) * x : 0);   // tangential accel without friction
    // state: [x, v (signed speed along track, + = toward +x), Q]
    const f = ([x, v]) => {
      const G = geo(x), nPer = g * G.cs + G.kap * v * v, d = drive(x, G);
      const dir = v !== 0 ? Math.sign(v) : Math.sign(d);
      return [v / G.q, d - dir * mu * Math.abs(nPer), p.m * mu * Math.abs(nPer) * Math.abs(v)];
    };
    const holds = x => { const G = geo(x); return Math.abs(drive(x, G)) <= mu * g * G.cs + 1e-12; };
    const x0 = startX(p);
    const s = { t: 0, y: [x0, 0, 0], done: false, events: [], stuck: holds(x0), held: 0, vMax: 0, vTop: 0, clear: 0, end: 0, vEnd: 0, h1: 0, turns: 0, last: 0 };
    const E0 = p.m * g * h(x0)[0] + springPE(p, x0);
    const onTurn = () => { s.turns++; if (s.turns === 1) s.h1 = h(s.y[0])[0]; s.stuck = holds(s.y[0]); };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events, E0,
      step(dt) {
        if (s.done) return;
        if (!s.stuck) s.held = 0;
        // Integrate with RK4, splitting the step exactly (bisection) at events: a turning point (v = 0), the spring's
        // free end (x = 0, where the spring force has a kink), the hilltop and the end of the track.
        let rem = dt;
        for (let guard = 0; rem > 1e-12 && !s.done && !s.stuck && guard < 8; guard++) {
          const y0 = s.y, y1 = rk4Step(f, y0, rem), cands = [];
          if (y0[1] !== 0 && Math.sign(y1[1]) !== Math.sign(y0[1])) cands.push(['turn', y => y[1] === 0 || Math.sign(y[1]) !== Math.sign(y0[1])]);
          if (sp && (y0[0] < 0) !== (y1[0] < 0)) cands.push(['spring', y => (y[0] < 0) !== (y0[0] < 0)]);
          if (sp && y0[0] < HILL_X && y1[0] >= HILL_X) cands.push(['top', y => y[0] >= HILL_X]);
          if (sp && y1[0] >= XEND) cands.push(['end', y => y[0] >= XEND]);
          if (!cands.length) { s.y = y1; s.t += rem; rem = 0; break; }
          let best = null;
          for (const [kind, crossed] of cands) {
            let lo = 0, hi = rem;
            for (let i = 0; i < 60; i++) { const mid = (lo + hi) / 2; if (crossed(rk4Step(f, y0, mid))) hi = mid; else lo = mid; }
            if (!best || hi < best[1]) best = [kind, hi];
          }
          const [kind, tau] = best;
          s.y = rk4Step(f, y0, tau); s.t += tau; rem -= tau;
          if (kind === 'turn') { s.y[1] = 0; onTurn(); }
          else if (kind === 'spring' && s.y[0] >= 0 && p.xc > 0) s.events.push({ type: 'burst', pos: [0, p.H + 0.2, 0], strength: 0.3, speed: 0.6, color: '#7dd3fc', life: 0.5 });
          else if (kind === 'top' && s.y[1] > 0) { s.vTop = s.y[1]; s.clear = 1; }
          else if (kind === 'end') {
            s.vEnd = Math.abs(s.y[1]); s.end = 1; s.done = true;
            s.events.push({ type: 'impact', pos: [XEND + 0.9, BASE + 0.3, 0], strength: Math.min(2, s.vEnd / 5), normal: 'x' });
          }
        }
        if (s.stuck && rem > 0 && !s.done) { s.t += rem; s.held += rem; if (s.held >= HOLD - 1e-9) s.done = true; }
        const [x, v] = s.y, sp_ = Math.abs(v);
        s.vMax = Math.max(s.vMax, sp_);
        if (s.t >= TMAX - 1e-9) s.done = true;
        if (mu > 0 && sp_ > 1 && Math.random() < 0.1) s.events.push({ type: 'spark', pos: [x, h(x)[0], 0.35], strength: 0.15, speed: 0.5, color: '#fb923c', life: 0.4 });
      },
      measures() {
        const [x, v, Q] = s.y, G = geo(x), KE = 0.5 * p.m * v * v, PEg = p.m * g * G.y, PEs = springPE(p, x);
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'x', label: 'Position x', value: x, unit: 'm', ref: XEND },
          { id: 'h', label: 'Height', value: G.y, unit: 'm', ref: 6 },
          { id: 'v', label: 'Speed', value: Math.abs(v), unit: 'm/s', ref: 15 },
          { id: 'KE', label: 'Kinetic energy', value: KE, unit: 'J', ref: E0 },
          { id: 'PEg', label: 'Gravitational PE', value: PEg, unit: 'J', ref: E0 },
          { id: 'PEs', label: 'Spring PE', value: PEs, unit: 'J', ref: E0 },
          { id: 'Q', label: 'Thermal energy', value: Q, unit: 'J', ref: E0 },
          { id: 'E', label: 'Total energy', value: KE + PEg + PEs + Q, unit: 'J', ref: E0 },
          { id: 'N', label: 'Normal force', value: p.m * (g * G.cs + G.kap * v * v), unit: 'N', ref: 3 * p.m * g },
          { id: 'vMax', label: 'Maximum speed', value: s.vMax, unit: 'm/s', ref: 15 },
          { id: 'vTop', label: 'Speed over the hilltop', value: s.vTop, unit: 'm/s', hidden: true },
          { id: 'clear', label: 'Cleared the hill', value: s.clear, unit: '', hidden: true },
          { id: 'end', label: 'Reached the end', value: s.end, unit: '', hidden: true },
          { id: 'vEnd', label: 'Speed at the end', value: s.vEnd, unit: 'm/s', hidden: true },
          { id: 'h1', label: 'First turning-point height', value: s.h1, unit: 'm', hidden: true },
        ];
      },
      energy() {
        const [x, v, Q] = s.y;
        return [
          { label: 'KE', value: 0.5 * p.m * v * v, color: '#fbbf24' },
          { label: 'PE gravity', value: p.m * g * h(x)[0], color: '#7dd3fc' },
          { label: 'PE spring', value: springPE(p, x), color: '#c084fc' },
          { label: 'Thermal', value: Q, color: '#f87171' },
          { label: 'Total', value: 0.5 * p.m * v * v + p.m * g * h(x)[0] + springPE(p, x) + Q, color: '#4ade80' },
        ];
      },
      scene() {
        const [x, v] = s.y, G = geo(x), n = [-G.sn, G.cs], tn = [G.cs, G.sn], ch = 0.45;
        const c = [x + n[0] * (ch / 2 + 0.12), G.y + n[1] * (ch / 2 + 0.12), 0], ang = Math.atan(G.h1);
        const wheel = (dx, dz, id) => ({ id, shape: 'sphere', r: 0.12, pos: [x + tn[0] * dx + n[0] * 0.12, G.y + tn[1] * dx + n[1] * 0.12, dz], color: '#1e293b' });
        const bodies = [
          { id: 'car', shape: 'box', size: [0.9, ch, 0.6], pos: c, rot: [0, 0, ang], color: '#fbbf24', metal: 0.35, trail: true, trailColor: '#fde68a', label: `${Math.abs(v).toFixed(2)} m/s` },
          wheel(-0.3, 0.35, 'w1'), wheel(0.3, 0.35, 'w2'), wheel(-0.3, -0.35, 'w3'), wheel(0.3, -0.35, 'w4'),
        ];
        const lines = [];
        if (springOn(p)) {
          const xr = Math.min(0, x) - 0.45, top = p.H + 0.12 + ch / 2, pts = [];
          for (let i = 0; i <= 20; i++) { const xx = WALL + (xr - WALL) * i / 20; pts.push([xx, top + (i % 2 && i < 20 ? (i % 4 === 1 ? 0.12 : -0.12) : 0), 0]); }
          lines.push({ id: 'spring', pts, color: x < 0 ? '#c084fc' : '#64748b' });
        }
        const kv = 0.25, kf = 0.9 / (p.m * C.g), N = p.m * (C.g * G.cs + G.kap * v * v);
        return {
          bodies, lines,
          vectors: [
            { id: 'vel', from: [c[0], c[1] + 0.35, 0.45], vec: [tn[0] * v * kv, tn[1] * v * kv, 0], color: '#fbbf24', label: 'v' },
            { id: 'W', from: [c[0], c[1], -0.45], vec: [0, -p.m * C.g * kf, 0], color: '#7dd3fc', label: 'mg' },
            { id: 'N', from: [c[0], c[1], -0.45], vec: [n[0] * N * kf, n[1] * N * kf, 0], color: '#a5b4fc', label: `N = ${N.toFixed(1)} N` },
          ],
        };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    return [
      'E = KE + PEg + PEs + Q = ½mv² + mgh + ½kx² + Q',
      `KE = ½ × ${p.m} × ${m.v.toFixed(3)}² = ${m.KE.toFixed(2)} J`,
      `PEg = ${p.m} × 9.8 × ${m.h.toFixed(3)} = ${m.PEg.toFixed(2)} J;  PEs = ${m.PEs.toFixed(2)} J;  Q = ${m.Q.toFixed(2)} J`,
      `E = ${m.KE.toFixed(2)} + ${m.PEg.toFixed(2)} + ${m.PEs.toFixed(2)} + ${m.Q.toFixed(2)} = ${m.E.toFixed(2)} J  (start ${model.E0.toFixed(2)} J)`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.track === 'coaster' && r.params.mu === 0 && r.params.Hh > r.params.H && r.final.clear === 1 && r.final.end === 1 && r.final.vTop > 0 && r.final.vTop <= 1.0),
    ({ runs }) => runs.some(r => r.params.track === 'halfpipe' && r.params.mu > 0 && Math.abs(r.final.h1 - 3) <= 0.05),
    ({ runs }) => runs.some(r => r.params.track === 'coaster' && r.params.mu === 0 && r.final.end === 1 && Math.abs(r.final.vEnd - 6) <= 0.1),
  ],
  evaluate(p) {
    const Es = springOn(p) ? 0.5 * p.k * p.xc * p.xc : 0, hlow = lowest(p);
    return { vars: { m: p.m, H: p.H, Es: Math.round(Es * 1e4) / 1e4, hlow }, answer: Math.sqrt(2 * (Es + p.m * C.g * (p.H - hlow)) / p.m), unit: 'm/s', tol: 0.02 };
  },
};
