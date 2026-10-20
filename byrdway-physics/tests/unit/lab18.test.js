// Lab 18 (Magnetic Field Lab) verification: particle motion vs the cyclotron formulas, coil EMF vs the analytic
// derivative of the dipole flux, and magnetic braking vs the exact exponential solution.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L, { dipoleFlux, dipoleFluxSlope } from '../../src/lab/labs/lab18.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 1e9, dt = L.dt || 1 / 240, each) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) { m.step(dt); each?.(m); }
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const val = m => Object.fromEntries(m.measures().map(x => [x.id, x.value]));
const rec = params => { const r = run(params); return { params: { ...defaults(), ...params }, final: r.v, t: r.m.t }; };
const mu0 = 1.25663706212e-6;

test('Lab 18: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const key of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[key], `text.${key}`);
  assert.equal(T.title, 'Magnetic Field Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 17); assert.ok(L.sections.includes('17.6') && L.sections.includes('17.7'));
  for (const mode of ['particle', 'magnet', 'rails']) {
    const p = { ...defaults(), mode };
    const m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 3, mode);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4, mode);
    for (const c of L.graph.choices) for (const key of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === key), `graph key ${key}`);
    assert.ok(L.decor(p).length > 3 && L.equations(p, m).length >= 3);
  }
  const ev = L.evaluate(defaults()); assert.ok(Number.isFinite(ev.answer));
  for (const key of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(key in ev.vars, `evaluate var ${key}`);
});

test('Lab 18: particle radius and period match r = mv/(|q|B) and T = 2πm/(|q|B); KE is constant', () => {
  // q = 2 mC, m = 1 g, v = 2 m/s, B = 1 T → r = 1 m, T = π s
  const { v } = run({ mode: 'particle', q: 2, m: 1, v: 2, B: 1, theta: 90 });
  near(v.rMeas, 1, 1e-6); near(v.Tmeas, Math.PI, 1e-6); near(v.rTh, 1, 1e-12); near(v.Tth, Math.PI, 1e-12);
  near(v.KE, 0.5 * 1e-3 * 4, 1e-9); near(v.spd, 2, 1e-9);
  near(v.F, 2e-3 * 2 * 1); near(v.F, 1e-3 * 4 / 1);            // |q|vB = mv²/r
  // a closed circle: back at the start after two periods
  assert.ok(Math.hypot(v.x, v.z) < 1e-3);
  // other values: q = 3.5 mC, m = 4 g, v = 3 m/s, B = 1.2 T → r = 2.857 m, T = 5.984 s
  const w = run({ mode: 'particle', q: 3.5, m: 4, v: 3, B: 1.2, theta: 90 }).v;
  near(w.rMeas, 4e-3 * 3 / (3.5e-3 * 1.2), 1e-5); near(w.Tmeas, 2 * Math.PI * 4e-3 / (3.5e-3 * 1.2), 1e-6);
  // positive charge circles clockwise seen from above (B up): starting along +x it first moves toward +z
  const pos = run({ mode: 'particle', q: 2 }, 0.2).v; assert.ok(pos.z > 0);
  const neg = run({ mode: 'particle', q: -2 }, 0.2).v; assert.ok(neg.z < 0);
  // period independent of speed
  near(run({ mode: 'particle', v: 4 }).v.Tmeas, Math.PI, 1e-6);
});

test('Lab 18: helix uses v⊥ for the radius and v∥·T for the pitch', () => {
  const th = 60 * Math.PI / 180;
  const v = run({ mode: 'particle', q: 2, m: 1, v: 2, B: 1, theta: 60 }).v;
  near(v.rMeas, 2 * Math.sin(th) / 2, 1e-5);
  near(v.Tmeas, Math.PI, 1e-6); near(v.pitch, 2 * Math.cos(th) * Math.PI, 1e-6);
  near(v.KE, 2e-3, 1e-9);
  // field-aligned launch: no force, straight line
  const s = run({ mode: 'particle', theta: 0 }).v; assert.equal(s.F, 0); assert.ok(Math.abs(s.x) < 1e-12);
  near(L.evaluate({ ...defaults(), q: 2, v: 2, B: 1, theta: 60 }).answer, 2e-3 * 2 * 1 * Math.sin(th), 1e-12);
});

test('Lab 18: coil EMF equals −N dΦ/dt from the analytic flux derivative, with opposite pulses (Lenz)', () => {
  const N = 200, v = 2, R = 2, dt = 1 / 240;
  let maxErr = 0, sawNeg = false, sawPos = false, peak = 0;
  const each = m => {
    const s = val(m), xMid = s.pos - v * dt / 2;            // EMF is the average over the step: compare at mid-step
    const exact = -N * dipoleFluxSlope(20, 0.5, xMid) * v;
    maxErr = Math.max(maxErr, Math.abs(s.emf - exact));
    peak = Math.max(peak, Math.abs(exact));
    if (s.pos < -0.05) { assert.ok(s.emf < 0, 'approaching: flux rises, EMF negative'); sawNeg = true; }
    if (s.pos > 0.05) { assert.ok(s.emf > 0, 'leaving: flux falls, EMF positive'); sawPos = true; }
    near(s.I, s.emf / R, 1e-12);
    assert.ok(s.Fdrag >= 0, 'drag always opposes the motion');
  };
  const { v: f } = run({ mode: 'magnet', N, v, R }, 1e9, dt, each);
  assert.ok(sawNeg && sawPos);
  assert.ok(maxErr < 2e-3 * peak, `EMF error ${maxErr}`);
  // flux formula itself: one turn at the centre = μ0 m/(2a)
  near(dipoleFlux(20, 0.5, 0), mu0 * 20 / (2 * 0.5));
  near(f.Phi, N * dipoleFlux(20, 0.5, 3));
  // analytic peak at x = a/2: |dΦ/dx| = (3/2)μ0 m a² (a/2)/(5a²/4)^(5/2)
  const pk = N * v * 1.5 * mu0 * 20 * 0.25 * 0.25 / (0.3125 ** 2.5);
  near(f.emfPk, pk, 2e-3);
  // net flux change from x = −3 to +3 is zero ⇒ ∫ε dt = 0 (equal and opposite pulses)
  let area = 0; run({ mode: 'magnet', N, v, R }, 1e9, dt, m => { area += val(m).emf * dt; });
  assert.ok(Math.abs(area) < 1e-12);
});

test('Lab 18: rod on rails decays as v₀e^(−t/τ) with τ = mR/(B²L²), and KE lost = thermal energy', () => {
  const P = { mode: 'rails', v: 3, B: 1, R: 2 };            // τ = 0.4 s
  for (const tt of [0.2, 0.4, 1.0]) {
    const r = run(P, tt), s = r.v, t = r.m.t;
    near(s.spd, 3 * Math.exp(-t / 0.4), 1e-6);
    near(s.pos, 0.5 + 3 * 0.4 * (1 - Math.exp(-t / 0.4)), 1e-6);
    // ε = −ΔΦ/Δt = BL·Δx/Δt over the last step (exact x(t)), and ≈ BLv
    near(Math.abs(s.emf), 3 * 0.4 * (Math.exp(-(t - 1 / 240) / 0.4) - Math.exp(-t / 0.4)) * 240, 1e-6);
    near(Math.abs(s.emf), 1 * 1 * s.spd, 1e-2);
    near(s.Fdrag, Math.abs(s.I) * 1 * 1, 1e-12);
    near(s.KE + s.Eth, 0.5 * 0.2 * 9, 1e-6);
    assert.ok(s.emf < 0, 'flux increases ⇒ EMF negative (clockwise from above)');
  }
  const f = run(P).v;
  near(f.tHalf, 0.4 * Math.LN2, 1e-5); near(f.pos, 1.7, 1e-4); near(f.Eth, 0.9, 1e-6);
});

test('Lab 18: challenge checkers accept correct evidence and reject wrong evidence', () => {
  // 1: r = 1.5 m: q = 2, m = 1, B = 1 → v = 3 m/s
  assert.ok(L.challenges[0]({ runs: [rec({ mode: 'particle', q: 2, m: 1, B: 1, v: 3, theta: 90 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'particle', q: 2, m: 1, B: 1, v: 2, theta: 90 })] }));
  // 2: period independent of speed
  assert.ok(L.challenges[1]({ runs: [rec({ mode: 'particle', v: 1 }), rec({ mode: 'particle', v: 2.5 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mode: 'particle', v: 1, m: 1 }), rec({ mode: 'particle', v: 2.5, m: 2 })] }));
  // 3: half-speed in 1.0 s: τ ln2 = 1 → R/B² = 7.21
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'rails', B: 1, R: 7.2 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'rails', B: 1, R: 2 })] }));
  // 4: peak EMF doubles with speed
  assert.ok(L.challenges[3]({ runs: [rec({ mode: 'magnet', v: 1 }), rec({ mode: 'magnet', v: 2 })] }));
  assert.ok(!L.challenges[3]({ runs: [rec({ mode: 'magnet', v: 1 }), rec({ mode: 'magnet', v: 1.5 })] }));
});
