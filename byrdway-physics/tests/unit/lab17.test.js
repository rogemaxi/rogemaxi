// Lab 17 (Circuit Builder) verification: the MNA-driven model is compared with hand-derived series/parallel results
// and with the exact RC charging curve.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab17.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 1e9, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => { const r = run(params); return { params: { ...defaults(), ...params }, final: r.v, t: r.m.t }; };

test('Lab 17: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const key of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[key], `text.${key}`);
  assert.equal(T.title, 'Circuit Builder');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 16); assert.ok(L.sections.includes('16.5'));
  for (const o of L.params[0].options) assert.ok(T.options[o.value]);
  for (const mode of ['series', 'parallel', 'combo', 'rc']) {
    const p = { ...defaults(), mode };
    const m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length > 10 && sc.vectors.length >= 1, mode);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4, mode);
    for (const c of L.graph.choices) for (const key of c.y) assert.ok(m.measures().some(x => x.id === key), `graph key ${key}`);
    assert.ok(L.decor(p).length > 5 && L.equations(p, m).length >= 3);
    assert.ok(Number.isFinite(L.evaluate(p).answer));
  }
  for (const key of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(key in L.evaluate(defaults()).vars, `evaluate var ${key}`);
});

test('Lab 17: series, parallel and combination circuits match Ohm’s and Kirchhoff’s laws', () => {
  const R = { V: 12, R1: 10, R2: 20, R3: 30 };
  const s = run({ ...R, mode: 'series' }).v;               // 60 Ω, 0.2 A
  near(s.Req, 60); near(s.I, 0.2); near(s.I1, 0.2); near(s.I2, 0.2); near(s.I3, 0.2);
  near(s.V1, 2); near(s.V2, 4); near(s.V3, 6); near(s.V1 + s.V2 + s.V3, 12);
  const p = run({ ...R, mode: 'parallel' }).v;             // 1.2 + 0.6 + 0.4 = 2.2 A
  near(p.I1, 1.2); near(p.I2, 0.6); near(p.I3, 0.4); near(p.I, 2.2); near(p.Req, 60 / 11);
  near(p.V1, 12); near(p.V2, 12); near(p.V3, 12); near(p.Ptot, 26.4);
  const c = run({ ...R, mode: 'combo' }).v;                // 10 + 12 = 22 Ω (honors solution)
  near(c.Req, 22); near(c.I, 12 / 22); near(c.I2, 0.32727, 1e-4); near(c.I3, 0.21818, 1e-4);
  near(c.I1, c.I2 + c.I3); near(c.V1 + c.V2, 12); near(c.V2, c.V3);
  near(c.P1 + c.P2 + c.P3, c.Ptot);
  // energy: battery work over the 5 s run equals thermal energy, = P·t
  near(c.Wbat, c.Ptot * 5, 1e-6); near(c.Eth, c.Wbat, 1e-9);
  // predict: in parallel, R3 does not affect I1
  near(run({ ...R, mode: 'parallel', R3: 40 }).v.I1, p.I1, 1e-12);
  // evaluation answer reproduces the model's battery current
  for (const mode of ['series', 'parallel', 'combo']) near(L.evaluate({ ...defaults(), ...R, mode }).answer, run({ ...R, mode }).v.I, 1e-12);
  near(L.evaluate({ ...defaults(), ...R, mode: 'rc' }).answer, 12 / 10, 1e-12);
});

test('Lab 17: RC charging follows Vc = ε(1 − e^(−t/τ)) and conserves energy', () => {
  const P = { mode: 'rc', V: 12, R1: 20, C: 100 };   // τ = 2 s
  for (const t of [0.5, 2, 4]) {
    const v = run(P, t).v;
    near(v.Vc, 12 * (1 - Math.exp(-t / 2)), 1e-6);
    near(v.I, 12 / 20 * Math.exp(-t / 2), 1e-6);
  }
  const { m, v } = run(P);
  near(m.t, 10, 1e-9); near(v.tau, 2);
  near(v.Vc, 12 * (1 - Math.exp(-5)), 1e-6);
  near(v.Wbat, v.Uc + v.Eth, 1e-6);                       // battery work = stored + thermal
  near(v.Wbat, 12 * v.Q, 1e-6);                           // W = εQ
  near(v.Uc, 0.5 * 0.1 * v.Vc ** 2, 1e-9);
});

test('Lab 17: electron animation speed is proportional to the wire current', () => {
  const sp = mode => {
    const m = L.create({ ...defaults(), mode, V: 12, R1: 10, R2: 20, R3: 30 });
    const a = m.scene({}).bodies.find(b => b.id === 'e0_1').pos;      // electron on the battery lead
    m.step(1 / 240);
    const b = m.scene({}).bodies.find(b => b.id === 'e0_1').pos;
    return Math.hypot(b[0] - a[0], b[1] - a[1]) * 240;
  };
  const s = sp('series'), c = sp('combo');
  near(c / s, (12 / 22) / 0.2, 1e-6);
  // electrons move opposite to conventional current: on the battery lead (current flows up, + terminal → top) they move down
  const m = L.create({ ...defaults(), mode: 'series' });
  const y0 = m.scene({}).bodies.find(b => b.id === 'e0_1').pos[1]; m.step(1 / 240);
  assert.ok(m.scene({}).bodies.find(b => b.id === 'e0_1').pos[1] < y0);
});

test('Lab 17: challenge checkers accept correct evidence and reject wrong evidence', () => {
  assert.ok(L.challenges[0]({ runs: [rec({ mode: 'series', V: 12, R1: 8, R2: 8, R3: 8 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'series', V: 12, R1: 10, R2: 10, R3: 10 })] }));
  assert.ok(L.challenges[1]({ runs: [rec({ mode: 'combo', R1: 10, R2: 10, R3: 10 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mode: 'series', R1: 5, R2: 5, R3: 5 })] }), 'series 15 Ω is not the combination');
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'rc', R1: 20, C: 100 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'rc', R1: 30, C: 100 })] }));
  const partial = { params: { ...defaults(), mode: 'rc', R1: 20, C: 100 }, final: run({ mode: 'rc', R1: 20, C: 100 }, 3).v };
  assert.ok(!L.challenges[2]({ runs: [partial] }), 'an unfinished charge is rejected');
});
