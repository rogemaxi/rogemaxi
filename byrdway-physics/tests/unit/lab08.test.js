// Lab 8 (Collision Laboratory) verification: the headless glider model against hand-derived collision results,
// momentum conservation in every mode, and the KE-loss formula ½μ(1 − e²)(v₁ − v₂)².
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab08.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 30, dt = L.dt || 1 / 240, watch) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) { m.step(dt); watch?.(m); }
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });

test('Lab 8: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Collision Laboratory');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.equal(L.unit, 7); assert.ok(L.sections.includes('7.3'));
  for (const mode of ['collision', 'explosion']) {
    const p = { ...defaults(), mode }, m = L.create(p);
    assert.ok(m.scene({}).bodies.length && m.scene({}).vectors.length >= 2 && m.measures().filter(x => !x.hidden).length >= 4);
    assert.equal(m.energy().length, 4);
    assert.ok(L.decor(p).length && L.equations(p, m).length >= 3);
    const ev = L.evaluate(p); assert.ok(Number.isFinite(ev.answer));
    for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(Number.isFinite(ev.vars[k]), `evaluate var ${k}`);
    for (const c of L.graph.choices) for (const k of c.y) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
  }
});

test('Lab 8: elastic collisions match hand-derived results and conserve p and KE', () => {
  // equal masses, target at rest: velocities exchange
  const a = run({}).v;
  assert.equal(a.hit, 1); near(a.v1, 0, 0, 1e-12); near(a.v2, 0.6, 1e-12);
  // contact at gap/closing speed = (2.5 − 0.4)/0.6 = 3.5 s; the run ends when glider 2 reaches x = 9.8 m
  near(a.t, 3.5 + (9.8 - 5.5) / 0.6, 0, 1 / 240); // within one time step
  // light into heavy: m1 = 0.2, m2 = 1.0, v1 = 1.2 → v1′ = (0.2−1)/1.2 × 1.2 = −0.8, v2′ = 0.4/1.2 × 1.2 = 0.4
  const b = run({ m1: 0.2, m2: 1, v1: 1.2, v2: 0 }).v;
  near(b.v1, -0.8, 1e-12); near(b.v2, 0.4, 1e-12);
  near(b.pAfter, 0.24, 1e-12); near(b.KAfter, b.KBefore, 1e-12); near(b.KBefore, 0.144, 1e-12); near(b.eMeas, 1, 1e-12);
  // head-on with both moving: m1 = 1, v1 = 0.5; m2 = 0.5, v2 = −1 → v1′ = −0.5, v2′ = 1.0
  const c = run({ m1: 1, m2: 0.5, v1: 0.5, v2: -1 }).v;
  near(c.v1, -0.5, 1e-12); near(c.v2, 1.0, 1e-12);
});

test('Lab 8: inelastic collisions conserve momentum and lose ½μ(1 − e²)(v₁ − v₂)² of KE', () => {
  for (const [m1, m2, v1, v2, e] of [[0.5, 0.5, 0.6, 0, 0], [0.5, 0.5, 0.6, 0, 0.5], [1.2, 0.3, 0.4, -0.9, 0.35], [0.25, 1.5, 1.8, 0.2, 0.8]]) {
    const v = run({ m1, m2, v1, v2, e }).v, mu = m1 * m2 / (m1 + m2);
    near(v.pAfter, m1 * v1 + m2 * v2, 1e-12, 1e-14); near(v.p, v.pBefore, 1e-12, 1e-14);
    near(v.KBefore - v.KAfter, 0.5 * mu * (1 - e * e) * (v1 - v2) ** 2, 1e-9);
    near(v.v2 - v.v1, e * (v1 - v2), 1e-9, 1e-12);
    if (e > 0) near(v.eMeas, e, 1e-9);
  }
  // perfectly inelastic: 0.6 m/s into an equal mass → common 0.30 m/s, half the KE lost
  const s = run({ e: 0 });
  near(s.v.v1, 0.3, 1e-12); assert.equal(s.v.v1, s.v.v2);
  near(s.v.KAfter / s.v.KBefore, 0.5, 1e-12);
  const en = s.m.energy(); near(en[3].value, s.v.KBefore, 1e-12); // KE + thermal = initial KE
  // momentum is constant at every step (no external force)
  run({ m1: 1.2, m2: 0.3, v1: 0.4, v2: -0.9, e: 0.35 }, 30, undefined, m => near(m.measures().find(x => x.id === 'p').value, 1.2 * 0.4 - 0.3 * 0.9, 1e-12, 1e-14));
  // no collision when they separate
  const n = run({ v1: -0.5, v2: 0.5 }).v; assert.equal(n.hit, 0); near(n.v1, -0.5, 1e-12);
});

test('Lab 8: explosion / recoil from rest and from a moving start', () => {
  // m1 = 0.5, m2 = 1.0, at rest, 2 J: μ = 1/3, u = √12 = 3.4641 → v1′ = −2.3094, v2′ = 1.1547
  const r = run({ mode: 'explosion', m1: 0.5, m2: 1, v1: 0, Ex: 2 });
  near(r.v.v1, -2 * Math.sqrt(12) / 3, 1e-12); near(r.v.v2, Math.sqrt(12) / 3, 1e-12);
  near(r.v.pAfter, 0, 0, 1e-12); near(r.v.KAfter, 2, 1e-12);
  near(r.m.energy()[3].value, 2, 1e-12); // KE + stored = 2 J throughout
  // check by hand: 0.5·(−2.3094) + 1·1.1547 = 0 and ½·0.5·5.3333 + ½·1·1.3333 = 2
  near(0.5 * r.v.v1 + r.v.v2, 0, 0, 1e-12);
  // moving start: both at 0.4 m/s, 1 J, equal masses 0.5 kg: u = √(2/0.25) = 2.8284 → 0.4 ∓ 1.4142
  const s = run({ mode: 'explosion', m1: 0.5, m2: 0.5, v1: 0.4, Ex: 1 }).v;
  near(s.v1, 0.4 - Math.SQRT2, 1e-12); near(s.v2, 0.4 + Math.SQRT2, 1e-12); near(s.pAfter, 0.4, 1e-12);
});

test('Lab 8: evaluation key reproduces the simulation', () => {
  for (const q of [{}, { e: 0.5, m1: 1.2, m2: 0.3, v1: 0.4, v2: -0.9 }, { mode: 'explosion', m1: 0.5, m2: 1, v1: 0, Ex: 2 }, { v1: -0.5, v2: 0.5 }]) {
    near(L.evaluate({ ...defaults(), ...q }).answer, run(q).v.v1, 1e-12, 1e-12);
  }
});

test('Lab 8: challenge checkers accept correct evidence and reject wrong evidence', () => {
  const C = L.challenges;
  // 1: 0.5 × 0.6 + 0.3 × (−1.0) = 0 → stuck pair at rest
  assert.ok(C[0]({ runs: [rec({ e: 0, m1: 0.5, v1: 0.6, m2: 0.3, v2: -1 })] }));
  assert.ok(!C[0]({ runs: [rec({ e: 0 })] }));
  assert.ok(!C[0]({ runs: [rec({ e: 1, m1: 0.5, v1: 0.6, m2: 0.3, v2: -1 })] }));
  // 2: v1′ = (m1 − e m2) v1 / M = 0 when m1 = e·m2: m1 = 0.5, m2 = 1.0, e = 0.5
  assert.ok(C[1]({ runs: [rec({ m1: 0.5, m2: 1, e: 0.5 })] }));
  assert.ok(!C[1]({ runs: [rec({ m1: 0.5, m2: 0.5, e: 1 })] }));   // e must be < 1
  assert.ok(!C[1]({ runs: [rec({ m1: 0.5, m2: 1, e: 0.4 })] }));
  // 3: speed ratio m1/m2 = 2 → m1 = 1.0, m2 = 0.5
  assert.ok(C[2]({ runs: [rec({ mode: 'explosion', m1: 1, m2: 0.5, v1: 0, Ex: 1 })] }));
  assert.ok(!C[2]({ runs: [rec({ mode: 'explosion', m1: 0.5, m2: 1, v1: 0, Ex: 1 })] }));
});
