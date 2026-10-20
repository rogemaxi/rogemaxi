// Lab 6 (Friction and Incline) verification: the headless model is compared with hand-derived incline results.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab06.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 20, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const g = 9.8, rad = d => d * Math.PI / 180, RUN = 4.35;

test('Lab 6: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Friction and Incline Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 5); assert.ok(L.sections.includes('5.7'));
  const m = L.create(defaults());
  const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 4);
  assert.ok(m.measures().filter(x => !x.hidden).length >= 4);
  assert.ok(L.graph.choices.length >= 2);
  for (const c of L.graph.choices) for (const k of c.y) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
  assert.ok(Array.isArray(L.decor(defaults())) && L.equations(defaults(), m).length >= 3);
  assert.ok(Number.isFinite(L.evaluate(defaults()).answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in L.evaluate(defaults()).vars, `evaluate var ${k}`);
});

test('Lab 6: static friction holds below θc = tan⁻¹ μs, independent of mass', () => {
  // μs = 0.40 → θc = 21.80°
  for (const m of [2, 4, 9]) {
    const { v } = run({ theta: 20, muS: 0.4, muK: 0.3, m });
    assert.equal(v.s, 0); assert.equal(v.v, 0); assert.equal(v.slide, 0);
    near(v.f, m * g * Math.sin(rad(20)));            // static friction equals mg sinθ exactly
    near(v.fsMax, 0.4 * m * g * Math.cos(rad(20)));
    assert.ok(v.f < v.fsMax);
  }
  near(run({}).v.thetaC, Math.atan(0.4) * 180 / Math.PI);
  assert.equal(run({ theta: 21.5, muS: 0.4 }).v.slide, 0);
  assert.equal(run({ theta: 22, muS: 0.4 }).v.slide, 1);
});

test('Lab 6: sliding acceleration, arrival time and energy match a = g(sinθ − μk cosθ)', () => {
  // θ = 35°, μk = 0.25: a = 9.8 (0.573576 − 0.25 × 0.819152) = 3.61413 m/s²
  const a = 9.8 * (Math.sin(rad(35)) - 0.25 * Math.cos(rad(35)));
  near(a, 3.61413, 1e-5);
  const mid = run({ theta: 35, muS: 0.5, muK: 0.25, m: 3 }, 1.0).v;
  near(mid.a, a, 1e-9); near(mid.v, a * 1.0); near(mid.s, 0.5 * a);
  const end = run({ theta: 35, muS: 0.5, muK: 0.25, m: 3 });
  assert.equal(end.v.bottom, 1); near(end.v.s, RUN);
  near(end.v.t, Math.sqrt(2 * RUN / a), 1e-9);        // exact in-step arrival time
  near(end.v.v, Math.sqrt(2 * a * RUN), 1e-9);
  // energy: KE + PE + thermal = initial PE (relative to the stop)
  const e = end.m.energy();
  near(e[3].value, 3 * g * RUN * Math.sin(rad(35)), 1e-9);
  near(e[2].value, 0.25 * 3 * g * Math.cos(rad(35)) * RUN, 1e-9);
  // frictionless check: a = g sinθ
  near(run({ theta: 30, muS: 0, muK: 0 }, 0.5).v.a, 4.9, 1e-9);
  // μk above μs is clamped to μs
  near(run({ theta: 40, muS: 0.3, muK: 0.6 }, 0.5).v.a, 9.8 * (Math.sin(rad(40)) - 0.3 * Math.cos(rad(40))), 1e-9);
});

test('Lab 6: a pushed block decelerates, stops at s = v0²/(2|a|) and then stays (tanθ < μk)', () => {
  const a = 9.8 * (Math.sin(rad(10)) - 0.4 * Math.cos(rad(10))); // −2.1590 m/s²
  const { v } = run({ theta: 10, muS: 0.5, muK: 0.4, v0: 2 });
  assert.equal(v.v, 0); assert.equal(v.slide, 0); assert.equal(v.bottom, 0);
  near(v.s, 4 / (2 * -a), 1e-9);
  near(v.f, 2 * g * Math.sin(rad(10)));
});

test('Lab 6: evaluation key reproduces the simulation', () => {
  const p = { theta: 35, muS: 0.5, muK: 0.25, m: 3 };
  near(L.evaluate({ ...defaults(), ...p }).answer, run(p, 0.5).v.a, 1e-12);
  assert.equal(L.evaluate(defaults()).answer, 0);
});

test('Lab 6: challenge checkers accept correct evidence and reject wrong evidence', () => {
  const C = L.challenges;
  // 1: 21.5° holds, 22.0° slides (θc = 21.8°)
  assert.ok(C[0]({ runs: [rec({ theta: 21.5 }), rec({ theta: 22 })] }));
  assert.ok(!C[0]({ runs: [rec({ theta: 20 }), rec({ theta: 22 })] }));       // 2° apart
  assert.ok(!C[0]({ runs: [rec({ theta: 21.5 }), rec({ theta: 22, muS: 0.38 })] })); // different μs
  // 2: tan 15° = 0.2679, μk = 0.27 → a = −0.019 m/s²
  assert.ok(C[1]({ runs: [rec({ theta: 15, muS: 0.4, muK: 0.27, v0: 2 })] }));
  assert.ok(!C[1]({ runs: [rec({ theta: 20, muS: 0.4, muK: 0.27, v0: 2 })] }));  // accelerates
  assert.ok(!C[1]({ runs: [rec({ theta: 10, muS: 0.4, muK: 0.27, v0: 1 })] }));  // stops partway
  // 3: θ = 24°, μk = 0.20 → t = 1.99 s
  const r = rec({ theta: 24, muS: 0.4, muK: 0.2 });
  near(r.final.t, Math.sqrt(2 * RUN / (9.8 * (Math.sin(rad(24)) - 0.2 * Math.cos(rad(24))))), 1e-9);
  assert.ok(C[2]({ runs: [r] }));
  assert.ok(!C[2]({ runs: [rec({ theta: 30, muS: 0.4, muK: 0.2 })] }));
});
