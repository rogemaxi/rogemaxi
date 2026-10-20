// Lab 16 (Electric Field Explorer) verification: the headless model is compared with hand-derived Coulomb results.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab16.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 100, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => { const r = run(params); return { params: { ...defaults(), ...params }, final: r.v, t: r.m.t }; };
const k = 8.9875517923e9, uC = 1e-6;

test('Lab 16: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const key of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[key], `text.${key}`);
  assert.equal(T.title, 'Electric Field Explorer');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 15); assert.ok(L.sections.includes('15.4'));
  assert.ok(L.params.length >= 2 && typeof L.create === 'function');
  const m = L.create(defaults());
  const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 4);
  assert.ok(m.measures().filter(x => !x.hidden).length >= 4);
  assert.ok(L.graph.choices.length >= 2);
  for (const c of L.graph.choices) for (const key of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === key), `graph key ${key}`);
  assert.ok(L.decor(defaults()).some(d => d.shape === 'line' && d.pts.length > 10), 'field lines drawn');
  assert.ok(L.equations(defaults(), m).length >= 3);
  const ev = L.evaluate(defaults()); assert.ok(Number.isFinite(ev.answer));
  for (const key of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(key in ev.vars, `evaluate var ${key}`);
  for (const id of ['q1', 'q2', 'q3']) assert.ok(T.params[id]);
});

test('Lab 16: probe field and potential match k·q/r² and k·q/r (superposition by hand)', () => {
  // single charge q1 = +3 μC at (−1.5, 0); probe at (0.5, 0): r = 2 m
  const s = run({ q1: 3, q2: 0, q3: 0, x0: 0.5, y0: 0 }, 0).v;
  near(s.E0, k * 3 * uC / 4); near(s.Vp, k * 3 * uC / 2);
  // three charges, probe at (0, 0): fields from q1 and q2 along x, q3 along −y
  const q1 = 3, q2 = -2, q3 = 1;
  const t = run({ q1, q2, q3, x0: 0, y0: 0 }, 0).v;
  const Ex = k * q1 * uC / 2.25 - k * q2 * uC / 2.25, Ey = -k * q3 * uC / 4;
  near(t.E0, Math.hypot(Ex, Ey));
  near(t.Vp, k * uC * (q1 / 1.5 + q2 / 1.5 + q3 / 2));
  near(L.evaluate({ ...defaults(), q1, q2, q3, x0: 0, y0: 0 }).answer, t.Vp, 1e-12);
  // dipole midline: V = 0 exactly, field is not zero
  const d = run({ q1: 3, q2: -3, q3: 0, x0: 0, y0: 1 }, 0).v;
  assert.ok(Math.abs(d.Vp) < 1e-6); near(d.E0, 2 * k * 3 * uC / 3.25 * (1.5 / Math.sqrt(3.25)));
});

test('Lab 16: RK4 motion conserves KE + qV and matches the energy theorem', () => {
  const { m, v } = run({});
  assert.equal(v.status, 1, 'default test charge leaves the region');
  const e = m.energy();
  near(e[0].value + e[1].value, e[2].value, 1e-12);
  // ΔKE = −q·ΔV, with V at start = Vp
  near(v.KE, -0.2 * uC * (v.V - v.Vp), 1e-6);
  // single-charge radial launch: v² = 2qk Q (1/r0 − 1/rf)/m, rf = 5.5 m to the x = 4 boundary
  const r = run({ q1: 3, q2: 0, q3: 0, qt: 0.2, mt: 0.8, x0: -1, y0: 0 }).v;
  const vExact = Math.sqrt(2 * 0.2 * uC * k * 3 * uC * (1 / 0.5 - 1 / Math.abs(r.x + 1.5)) / 0.8e-3);
  near(r.v, vExact, 1e-6); near(r.x, 4, 0.01); assert.ok(Math.abs(r.y) < 1e-9);
  // early-time check: from rest, x ≈ x0 + ½at² with a = qE/m
  const e1 = run({ q1: 3, q2: 0, q3: 0, qt: 0.2, mt: 2, x0: -1, y0: 0 }, 0.01), te = e1.m.t;
  const a = 0.2 * uC * k * 3 * uC / 0.25 / 2e-3;
  near(e1.v.disp, 0.5 * a * te * te, 2e-3);
  // attraction: a negative test charge is pulled into the positive charge
  assert.equal(run({ q1: 3, q2: 0, q3: 0, qt: -0.2, x0: -0.5, y0: 0 }).v.status, 2);
});

test('Lab 16: challenge checkers accept correct evidence and reject wrong evidence', () => {
  // 1: equilibrium at the midpoint of equal charges
  assert.ok(L.challenges[0]({ runs: [rec({ q1: 3, q2: 3, q3: 0, x0: 0, y0: 0 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ q1: 3, q2: 3, q3: 0, x0: 0.5, y0: 0.5 })] }));
  // 2: V = 0 but E ≠ 0 on the dipole midline
  assert.ok(L.challenges[1]({ runs: [rec({ q1: 3, q2: -3, q3: 0, x0: 0, y0: 1 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ q1: 3, q2: 3, q3: 0, x0: 0, y0: 0 })] }), 'E = 0 and V ≠ 0 is rejected');
  // 3: escape speed 5.0 m/s
  assert.ok(L.challenges[2]({ runs: [rec({ q1: 3, q2: 0, q3: 0, qt: 0.2, mt: 0.8, x0: -1, y0: 0 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ q1: 3, q2: 0, q3: 0, qt: 0.2, mt: 2, x0: -1, y0: 0 })] }));
});
