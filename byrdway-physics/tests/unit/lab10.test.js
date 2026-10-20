// Lab 10 (Rotation and Torque) verification: the headless model is compared with hand-derived rotational results.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab10.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = Infinity, dt = L.dt) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const g = 9.8, rad = d => d * Math.PI / 180;

test('Lab 10: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Rotation and Torque Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 9); assert.ok(L.sections.includes('9.3') && L.sections.includes('9.8'));
  for (const mode of ['roll', 'torque']) for (const shape of ['hoop', 'disk', 'solidSphere', 'hollowSphere', 'rod']) {
    const p = { ...defaults(), mode, shape }, m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 2, `${mode}/${shape} scene`);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4);
    for (const c of L.graph.choices) for (const k of c.y) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
    for (const k of L.recordKeys) assert.ok(m.measures().some(x => x.id === k), `record key ${k}`);
    assert.ok(Array.isArray(L.decor(p)) && L.equations(p, m).length >= 3 && m.energy().length === 3);
    assert.ok(Number.isFinite(L.evaluate(p).answer));
  }
  assert.ok(L.graph.choices.length >= 2);
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in L.evaluate(defaults()).vars, `evaluate var ${k}`);
});

test('Lab 10: torque spin-up matches α = RF sinφ / I and L = Iω for every shape', () => {
  const M = 2, R = 0.4, F = 10, tOn = 3;
  const I = { hoop: M * R * R, disk: M * R * R / 2, solidSphere: 0.4 * M * R * R, hollowSphere: 2 / 3 * M * R * R, rod: M * (2 * R) ** 2 / 12 };
  for (const [shape, Ih] of Object.entries(I)) {
    const al = R * F / Ih;
    const mid = run({ mode: 'torque', shape, M, R, F, phi: 90, tOn, tf: 0 }, 1.5).v;
    near(mid.I, Ih, 1e-12); near(mid.alpha, al, 1e-12); near(mid.w, al * 1.5, 1e-9); near(mid.ang, 0.5 * al * 1.5 ** 2, 1e-9);
    const end = run({ mode: 'torque', shape, M, R, F, phi: 90, tOn, tf: 0 }).v;
    near(end.alphaOn, al, 1e-9); near(end.Loff, R * F * tOn, 1e-9);         // rotational impulse τΔt = ΔL
    near(end.w, al * tOn, 1e-9); assert.equal(end.alpha, 0);                 // no friction: ω constant after release
    near(end.ang, 0.5 * al * tOn ** 2 + al * tOn * (12 - tOn), 1e-9);
  }
  // φ = 30° halves the torque
  near(run({ mode: 'torque', shape: 'disk', phi: 30 }, 1).v.tauA, 0.4 * 10 * 0.5, 1e-12);
});

test('Lab 10: axle friction — spin-down at −τf/I, static hold, and work = KE + thermal', () => {
  const I = 0.16; // disk, M = 2 kg, R = 0.4 m
  const r = run({ mode: 'torque', shape: 'disk', M: 2, R: 0.4, F: 10, phi: 90, tOn: 1, tf: 0.5 });
  const wOff = (4 - 0.5) / I * 1, tStop = 1 + wOff / (0.5 / I);           // 21.875 rad/s, stops at t = 8 s
  near(r.v.Loff, I * wOff, 1e-9); assert.ok(r.m.t >= tStop - 1e-9 && r.m.t <= tStop + L.dt + 1e-9); assert.equal(r.v.w, 0); assert.ok(r.m.done);
  const thOn = 0.5 * 21.875 * 1, thOff = wOff * wOff / (2 * 0.5 / I);
  near(r.v.ang, thOn + thOff, 1e-9);
  const e = r.m.energy(); near(e[0].value, 4 * thOn, 1e-9); near(e[0].value, e[1].value + e[2].value, 1e-9); near(e[2].value, 0.5 * (thOn + thOff), 1e-9);
  const mid = run({ mode: 'torque', shape: 'disk', tOn: 1, tf: 0.5 }, 4).v; near(mid.alpha, -0.5 / I, 1e-12);
  // applied torque below the friction torque: nothing moves
  const held = run({ mode: 'torque', shape: 'disk', F: 1, R: 0.4, tf: 0.5 }).v;
  assert.equal(held.w, 0); assert.equal(held.ang, 0); assert.equal(held.Loff, 0);
});

test('Lab 10: rolling race matches a = g sinθ/(1+β), finish order, and energy split', () => {
  const th = 20, s = Math.sin(rad(th));
  const t = b => Math.sqrt(2 * 4 / (g * s / (1 + b)));
  const { m, v } = run({ mode: 'roll', theta: th, shape: 'solidSphere', M: 2, R: 0.4 });
  near(v.tHoop, t(1), 1e-12); near(v.tHollow, t(2 / 3), 1e-12); near(v.tDisk, t(0.5), 1e-12); near(v.tSolid, t(0.4), 1e-12);
  assert.ok(v.tSolid < v.tDisk && v.tDisk < v.tHollow && v.tHollow < v.tHoop);
  near(v.tSolid, 1.8280, 1e-4); near(v.tHoop, 2.1848, 1e-4);              // hand values at 20°
  near(v.v, Math.sqrt(2 * g * 4 * s / 1.4), 1e-9);                        // v = √(2gh/(1+β))
  near(v.wr, v.v / 0.4, 1e-12); near(v.frac, 0.4 / 1.4, 1e-12);
  const e = m.energy(); near(e[0].value, e[1].value + e[2].value, 1e-9); near(e[2].value / (e[1].value + e[2].value), 2 / 7, 1e-9);
  // mid-race kinematics s = ½at²
  const mid = run({ mode: 'roll', theta: 30, shape: 'hoop' }, 1).v; near(mid.s, 0.5 * g * 0.5 / 2 * 1, 1e-9);
  // mass and radius cancel
  near(run({ mode: 'roll', theta: 20, M: 9, R: 0.9, shape: 'disk' }).v.tFin, t(0.5), 1e-12);
  near(run({ mode: 'roll', shape: 'rod' }).v.tFin, t(0.5), 1e-12);        // rod highlights the disk
});

test('Lab 10: evaluation key agrees with the simulation', () => {
  for (const [shape, theta] of [['hoop', 12], ['solidSphere', 35], ['hollowSphere', 20]]) {
    const p = { ...defaults(), mode: 'roll', shape, theta };
    near(L.evaluate(p).answer, run(p).v.tFin, 1e-12);
  }
  near(L.evaluate({ ...defaults(), shape: 'hoop', theta: 30 }).answer, Math.sqrt(8 / (g * 0.5 / 2)), 1e-12);
});

test('Lab 10: challenge checkers accept correct evidence and reject wrong evidence', () => {
  // α = RF/I = 2 → disk M = 4, R = 0.5 (I = 0.5), F = 2 N
  assert.ok(L.challenges[0]({ runs: [rec({ mode: 'torque', shape: 'disk', M: 4, R: 0.5, F: 2, phi: 90, tf: 0 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'torque', shape: 'disk', M: 4, R: 0.5, F: 3, phi: 90, tf: 0 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'roll' })] }));
  // L = τ·tOn = 0.5 × 10 × 2 = 10
  assert.ok(L.challenges[1]({ runs: [rec({ mode: 'torque', R: 0.5, F: 10, phi: 90, tOn: 2, tf: 0 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mode: 'torque', R: 0.5, F: 10, phi: 90, tOn: 3, tf: 0 })] }));
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'roll', theta: 20, M: 2, R: 0.4 }), rec({ mode: 'roll', theta: 20, M: 6, R: 0.8 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'roll', theta: 20, M: 2, R: 0.4 }), rec({ mode: 'roll', theta: 25, M: 6, R: 0.8 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'roll', theta: 20, M: 2, R: 0.4 }), rec({ mode: 'roll', theta: 20, M: 2, R: 0.8 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'roll', theta: 20, M: 2, R: 0.4, shape: 'disk' }), rec({ mode: 'roll', theta: 20, M: 6, R: 0.8, shape: 'hoop' })] }));
});
