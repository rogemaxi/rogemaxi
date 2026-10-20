// Lab 14 (Wave Interference) verification: the finite-difference rope is compared with v = √(F/μ),
// superposition of pulses, fₙ = n·v/(2L) for a fixed string, the standing-wave energy, and f_beat = |f₁ − f₂|.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab14.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 1e9, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });

test('Lab 14: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Wave Interference Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 13); assert.ok(L.sections.includes('13.3') && L.sections.includes('13.5') && L.sections.includes('13.7'));
  for (const mode of ['pulses', 'standing', 'beats']) {
    const p = { ...defaults(), mode }, m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length > 20 && sc.lines[0].pts.length === 201, mode);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4, mode);
    for (const c of L.graph.choices) for (const k of c.y) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
    assert.ok(Array.isArray(L.decor(p)) && L.equations(p, m).length >= 3 && m.energy().length === 3);
  }
  const ev = L.evaluate(defaults()); assert.ok(Number.isFinite(ev.answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in ev.vars, `evaluate var ${k}`);
});

test('Lab 14: pulses travel at √(F/μ) and superpose (A₁ + A₂) without changing each other', () => {
  for (const [F, v] of [[2, 2], [8, 4], [32, 8]]) near(run({ F }).v.vm, v, 5e-3);           // μ = 0.5 kg/m
  const up = run({ A1: 0.25, A2: 0.25 }).v; near(up.ypk, 0.5, 2e-3);                        // constructive
  const dn = run({ A1: 0.25, A2: -0.25 }).v; assert.ok(Math.abs(dn.ypk) < 1e-9);            // centre never moves
  const mix = run({ A1: 0.2, A2: -0.1 }).v; near(mix.ypk, 0.1, 5e-3);
  // after crossing, each pulse is unchanged: at t = 1.2/v + 0.6/v (F = 8 N, v = 4) pulse 1 is centred at 2.6 m with height A₁
  const after = run({ A1: 0.25, A2: -0.15 }, 0.45);
  near(after.v.ymax, 0.25, 3e-3);
  // energy is the same before and during the overlap (none is lost when the rope is momentarily flat)
  const e0 = run({}, 0.01).v.E, eOver = run({}, 0.3).v.E;   // pulses meet at t = 1.2/4 = 0.3 s
  near(eOver, e0, 1e-3);
  const flat = run({}, 0.3).m.energy(); assert.ok(flat[0].value > 50 * Math.abs(flat[1].value)); // all kinetic at the overlap
});

test('Lab 14: a fixed string vibrates at fₙ = n·v/(2L) with conserved energy F·n²π²A²/(4L)', () => {
  for (const [F, n] of [[8, 1], [8, 2], [8, 4], [2, 3], [32, 6]]) {
    const v = Math.sqrt(F / 0.5), { v: r } = run({ mode: 'standing', F, n, A1: 0.2 });
    near(r.fm, n * v / 8, 1e-3); assert.equal(r.nodes, n - 1); near(r.lam, 8 / n, 1e-12);
  }
  const E = t => run({ mode: 'standing', F: 8, n: 3, A1: 0.25 }, t).v.E;
  const E0 = 8 * 9 * Math.PI ** 2 * 0.0625 / 16; // 2.7758 J
  near(E(0.1), E0, 1e-3); near(E(3.3), E(0.1), 1e-9); near(E(8), E(0.1), 1e-9);
  // nodes stay put: the midpoint of the n = 2 mode never moves
  const { m } = run({ mode: 'standing', F: 8, n: 2, A1: 0.25 }, 1.37);
  const mid = m.scene({}).lines[0].pts[100][1] - 1.2; assert.ok(Math.abs(mid) < 1e-12);
});

test('Lab 14: two sources produce beats at |f₁ − f₂|', () => {
  for (const [f1, f2] of [[2, 2.5], [2, 2.2], [1.5, 2.25], [3, 2.6]]) near(run({ mode: 'beats', f1, f2, A1: 0.15, A2: 0.15 }).v.fb, Math.abs(f1 - f2), 1e-2);
  near(run({ mode: 'beats', f1: 2, f2: 2.5, A1: 0.2, A2: 0.1 }).v.fb, 0.5, 1e-2);  // unequal amplitudes: same beat rate
  assert.ok(Number.isNaN(run({ mode: 'beats', f1: 2, f2: 2 }).v.fb));              // equal frequencies: no beats
});

test('Lab 14: evaluation key matches the simulated harmonic frequency', () => {
  for (const p of [{ F: 8, n: 2 }, { F: 18, n: 5 }]) near(L.evaluate({ ...defaults(), ...p }).answer, run({ mode: 'standing', ...p }).v.fm, 1e-3);
});

test('Lab 14: challenge checkers accept correct evidence and reject wrong evidence', () => {
  assert.ok(L.challenges[0]({ runs: [rec({ mode: 'standing', n: 3, F: 8 })] }));       // v = 4 → f₃ = 1.5 Hz
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'standing', n: 3, F: 10 })] }));
  assert.ok(L.challenges[1]({ runs: [rec({ mode: 'beats', f1: 2, f2: 2.4 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mode: 'beats', f1: 2, f2: 2.5 })] }));
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'pulses', A1: 0.22, A2: -0.22 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'pulses', A1: 0.22, A2: -0.25 })] }));
});
