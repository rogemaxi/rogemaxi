// Lab 11 (Pendulum and Spring) verification: the RK4 oscillators are compared with independent analytic results.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab11.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = Infinity, dt = L.dt) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const g = 9.8;
// Exact period T = 4√(L/g)·K(sin(θ₀/2)), with K evaluated by composite Simpson quadrature (independent of the AGM code path).
const exactT = (Lm, th0deg) => {
  const k = Math.sin(th0deg * Math.PI / 360), n = 2000, h = Math.PI / 2 / n, F = u => 1 / Math.sqrt(1 - k * k * Math.sin(u) ** 2);
  let S = F(0) + F(Math.PI / 2); for (let i = 1; i < n; i++) S += (i % 2 ? 4 : 2) * F(i * h);
  return 4 * Math.sqrt(Lm / g) * S * h / 3;
};

test('Lab 11: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Pendulum and Spring Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 10); assert.ok(L.sections.includes('10.4') && L.sections.includes('10.7'));
  for (const mode of ['pendulum', 'spring']) {
    const p = { ...defaults(), mode, F0: 0.5 }, m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 3);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4);
    for (const c of L.graph.choices) for (const k of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
    for (const k of L.recordKeys) assert.ok(m.measures().some(x => x.id === k), `record key ${k}`);
    assert.ok(Array.isArray(L.decor(p)) && L.equations(p, m).length >= 3 && m.energy().length >= 3);
  }
  assert.ok(L.graph.choices.length >= 2);
  assert.ok(Number.isFinite(L.evaluate(defaults()).answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in L.evaluate(defaults()).vars, `evaluate var ${k}`);
});

test('Lab 11: pendulum period matches the exact elliptic-integral period at every amplitude', () => {
  for (const th0 of [5, 30, 60, 90, 150, 170]) {
    const { v } = run({ mode: 'pendulum', L: 1, th0, b: 0 });
    near(v.Tm, exactT(1, th0), 1e-6); near(v.Texact, exactT(1, th0), 1e-8);
    near(v.Tsmall, 2 * Math.PI * Math.sqrt(1 / g), 1e-12);
  }
  near(exactT(1, 60) / (2 * Math.PI * Math.sqrt(1 / g)), 1.07318, 1e-5);   // tabulated value for 60°
  near(run({ th0: 60 }).v.ratio, 1.07318, 1e-5);
  near(run({ th0: 3, L: 0.4 }).v.Tm, 2 * Math.PI * Math.sqrt(0.4 / g), 2e-4); // small-angle limit; L×4 → T×2
  near(run({ th0: 3, L: 1.6 }).v.Tm / run({ th0: 3, L: 0.4 }).v.Tm, 2, 1e-6);
  near(run({ th0: 40, m: 4 }).v.Tm, run({ th0: 40, m: 0.5 }).v.Tm, 1e-9);   // mass independent
});

test('Lab 11: energy conservation (undamped) and energy bookkeeping (damped, driven)', () => {
  const m = L.create({ ...defaults(), mode: 'pendulum', th0: 120, b: 0 });
  const E0 = 1 * g * 1 * (1 - Math.cos(120 * Math.PI / 180)); let worst = 0;
  while (!m.done) { m.step(L.dt); const e = m.energy(); worst = Math.max(worst, Math.abs(e[0].value + e[1].value - E0) / E0); }
  assert.ok(worst < 1e-7, `pendulum energy drift ${worst}`);
  const d = run({ mode: 'pendulum', th0: 45, b: 0.3 }).m.energy();
  near(d[0].value + d[1].value + d[2].value, g * (1 - Math.cos(Math.PI / 4)), 1e-6);
  const s = run({ mode: 'spring', b: 0.2, F0: 0.5, wd: 3, x0: 0.1 }).m.energy();          // E₀ + W_drive = KE + PE + heat
  near(0.5 * 20 * 0.01 + s[3].value, s[0].value + s[1].value + s[2].value, 1e-6);
  const u = run({ mode: 'spring', k: 50, m: 2, x0: 0.3 }).v; near(u.E, 0.5 * 50 * 0.09, 1e-7);
});

test('Lab 11: spring motion matches 2π√(m/k), the damped solution, and the steady driven amplitude', () => {
  for (const [mm, k] of [[1, 20], [2, 20], [1, 80], [0.5, 39.5]]) near(run({ mode: 'spring', m: mm, k, b: 0, F0: 0 }).v.Tm, 2 * Math.PI * Math.sqrt(mm / k), 1e-6);
  // underdamped release from x₀ at rest: x = x₀e^(−γt)(cos ω_d t + (γ/ω_d) sin ω_d t)
  const mm = 1, k = 20, b = 0.3, x0 = 0.2, gam = b / (2 * mm), wd = Math.sqrt(k / mm - gam * gam);
  for (const t of [0.5, 2.7, 7.3]) {
    const v = run({ mode: 'spring', m: mm, k, b, x0, F0: 0 }, t).v;
    near(v.x, x0 * Math.exp(-gam * t) * (Math.cos(wd * t) + gam / wd * Math.sin(wd * t)), 1e-6, 1e-9);
  }
  const dmp = run({ mode: 'spring', m: mm, k, b, x0, F0: 0 }).v;
  near(dmp.Tm, 2 * Math.PI / wd, 1e-6); near(dmp.Tsp, 2 * Math.PI / wd, 1e-12);
  // driven: after the transient (40 s ≫ 2m/b) the peak equals F₀/√((k − mω²)² + (bω)²)
  for (const w of [2, 4.45, 7]) {
    const v = run({ mode: 'spring', m: 1, k: 20, b: 0.5, F0: 0.5, wd: w, x0: 0 }).v;
    const A = 0.5 / Math.sqrt((20 - w * w) ** 2 + (0.5 * w) ** 2);
    near(v.Ass, A, 1e-12); near(v.Apeak, A, 2e-3);
    near(v.Tm, 2 * Math.PI / w, 1e-3);                                         // locks to the drive period
  }
});

test('Lab 11: evaluation key agrees with the simulation and with the series given in the question', () => {
  for (const [Lm, th0] of [[1, 60], [1.5, 20], [0.5, 90]]) {
    const ev = L.evaluate({ ...defaults(), L: Lm, th0 });
    near(ev.answer, run({ mode: 'pendulum', L: Lm, th0, b: 0 }).v.Tm, 1e-6);
    const th = th0 * Math.PI / 180, series = 2 * Math.PI * Math.sqrt(Lm / g) * (1 + th * th / 16 + 11 * th ** 4 / 3072);
    assert.ok(Math.abs(series / ev.answer - 1) < ev.tol, `series answer accepted at ${th0}°`);
    if (th0 >= 60) assert.ok(Math.abs(2 * Math.PI * Math.sqrt(Lm / g) / ev.answer - 1) > ev.tol, 'small-angle answer rejected');
  }
});

test('Lab 11: challenge checkers accept correct evidence and reject wrong evidence', () => {
  assert.ok(L.challenges[0]({ runs: [rec({ mode: 'pendulum', th0: 69, b: 0 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'pendulum', th0: 60, b: 0 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'pendulum', th0: 69, b: 0.5 })] }));
  assert.ok(L.challenges[1]({ runs: [rec({ mode: 'spring', m: 1, k: 39.5, b: 0, F0: 0 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mode: 'spring', m: 1, k: 30, b: 0, F0: 0 })] }));
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'spring', m: 1, k: 20, b: 0.2, F0: 0.5, wd: 4.45, x0: 0 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'spring', m: 1, k: 20, b: 0.2, F0: 0.5, wd: 3, x0: 0 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'spring', m: 1, k: 20, b: 0.2, F0: 0.5, wd: 4.45, x0: 0 })].map(r => ({ ...r, final: { ...r.final, Apeak: 0.3 } })) }));
});
