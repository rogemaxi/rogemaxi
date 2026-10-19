// Laboratory model verification: each lab's simulation (the code that drives the 3D view) is run headless and
// compared with independent analytic results. Visual plausibility is never used as evidence.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { LABS } from '../../src/lab/labs/index.js';
import * as P from '../../src/physics/index.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const run = (lab, params, tEnd, dt = lab.dt || 1 / 240) => {
  const m = lab.create({ ...Object.fromEntries(lab.params.map(p => [p.id, p.value])), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const lab = n => LABS.find(l => l.num === n);

test('every registered lab has the required investigation structure', () => {
  for (const L of LABS) {
    const T = L.text;
    for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `lab ${L.num}: text.${k}`);
    assert.ok(T.guided.length >= 3 && T.challenges.length >= 2 && T.assumptions.length >= 3, `lab ${L.num}: counts`);
    assert.equal(T.challenges.length, L.challenges.length, `lab ${L.num}: challenge checkers`);
    assert.ok(L.params.length >= 2 && typeof L.create === 'function' && typeof L.evaluate === 'function' && typeof L.equations === 'function');
    const m = L.create(Object.fromEntries(L.params.map(p => [p.id, p.value])));
    const sc = m.scene({}); assert.ok(sc.bodies?.length || sc.lines?.length, `lab ${L.num}: scene renders something`);
    assert.ok(m.measures().length >= 3, `lab ${L.num}: live measurements`);
    const ev = L.evaluate(Object.fromEntries(L.params.map(p => [p.id, p.value])));
    assert.ok(Number.isFinite(ev.answer), `lab ${L.num}: evaluation answer is a number`);
  }
});

test('Lab 5: simulated motion matches ΣF = m·a and constant-acceleration kinematics', () => {
  const L = lab(5);
  const { v } = run(L, { m: 4, F: 20, mu: 0 }, 1.5);
  near(v.a, 5); near(v.v, 7.5); near(v.x, P.kin.x(0, 0, 5, 1.5));
  const f = run(L, { m: 5, F: 30, mu: 0.2 }, 1.0).v;
  near(f.a, (30 - 0.2 * 5 * 9.8) / 5); near(f.Fnet, 30 - 9.8); near(f.f, -9.8);
  // static friction: F below μs·N (μs = 0.25 → 12.25 N) leaves the cart at rest with f = −F
  const s = run(L, { m: 5, F: 12, mu: 0.2 }, 1.0).v;
  assert.equal(s.x, 0); assert.equal(s.v, 0); near(s.f, -12);
  // energy bookkeeping: work by F = KE + thermal
  const e = run(L, { m: 5, F: 30, mu: 0.2 }, 1.2).m.energy();
  near(e[1].value, e[0].value + e[2].value, 1e-9);
  // evaluation key agrees with the simulation
  near(L.evaluate({ m: 5, F: 30, mu: 0.2 }).answer, f.a, 1e-12);
  assert.equal(L.evaluate({ m: 5, F: 12, mu: 0.2 }).answer, 0);
});

test('Lab 5: challenge checkers accept correct evidence and reject wrong evidence', () => {
  const L = lab(5);
  const rec = (params, t = 1) => ({ params, final: run(L, params, t).v });
  assert.ok(L.challenges[0]({ params: { m: 5, F: 10, mu: 0 }, runs: [rec({ m: 5, F: 10, mu: 0 })] }));
  assert.ok(!L.challenges[0]({ params: { m: 5, F: 12, mu: 0 }, runs: [rec({ m: 5, F: 12, mu: 0 })] }));
  assert.ok(L.challenges[1]({ runs: [rec({ m: 2, F: 20, mu: 0 }), rec({ m: 4, F: 20, mu: 0 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ m: 2, F: 20, mu: 0 }), rec({ m: 3, F: 20, mu: 0 })] }));
  assert.ok(L.challenges[2]({ runs: [rec({ m: 5, F: 19.8, mu: 0.2 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ m: 5, F: 25, mu: 0.2 })] }));
});
