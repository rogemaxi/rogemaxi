// Lab 20 (Relativity Explorer) verification: the headless twin-trip model is compared with hand-derived
// special-relativity results (β = 0.8 → γ = 5/3 exactly; β = 0.6 → γ = 5/4).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab20.js';
import { dilatedTime } from '../../src/physics/index.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 60, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const c = 299792458;

test('Lab 20: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Relativity Explorer');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 19); assert.ok(L.sections.includes('19.3')); assert.equal(L.advanced, true);
  const m = L.create(defaults());
  const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 1);
  for (const b of sc.bodies) assert.ok(['box', 'sphere', 'cylinder', 'cone', 'torus', 'plane'].includes(b.shape));
  assert.ok(m.measures().filter(x => !x.hidden).length >= 4);
  assert.ok(L.graph.choices.length >= 2);
  for (const ch of L.graph.choices) for (const k of [...ch.y, ch.x || 't']) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
  for (const k of L.recordKeys) assert.ok(m.measures().some(x => x.id === k), `record key ${k}`);
  assert.ok(Array.isArray(L.decor(defaults())) && L.equations(defaults(), m).length >= 3);
  assert.ok(Number.isFinite(L.evaluate(defaults()).answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in L.evaluate(defaults()).vars, `evaluate var ${k}`);
});

test('Lab 20: twin trip at 0.8c to 4 ly — Earth 10 yr, ship 6 yr, γ = 5/3', () => {
  const { v } = run({ beta: 0.8, D: 4, L0: 100 });
  near(v.g, 5 / 3, 1e-12); near(v.tE, 10, 1e-12); near(v.tS, 6, 1e-12); near(v.gap, 4, 1e-12);
  near(v.L, 60, 1e-12); near(v.Dp, 2.4, 1e-12); near(v.x, 0, 0, 1e-9);
  assert.equal(v.ticks, 12);                    // 6 yr / 0.5 yr per tick
  near(v.tickE, 0.5 * 5 / 3, 1e-12);            // one tick lasts γ·Δt0 by Earth clocks
  near(dilatedTime(v.tS * 365.25 * 86400, 0.8 * c) / (365.25 * 86400), v.tE, 1e-12);
  near(L.evaluate({ beta: 0.8, D: 4 }).answer, 6, 1e-12);
  // β = 0.6, D = 3: γ = 1.25, Earth 10 yr, ship 8 yr
  const b = run({ beta: 0.6, D: 3 }).v; near(b.tE, 10, 1e-12); near(b.tS, 8, 1e-12); near(b.g, 1.25, 1e-12);
});

test('Lab 20: mid-trip kinematics and clock rate are constant at 1/γ', () => {
  const m = L.create({ ...defaults(), beta: 0.8, D: 4 });
  let checked = 0;
  for (let i = 1; i <= 12 * 240; i++) {
    m.step(1 / 240);
    if (i % 60) continue;
    const v = Object.fromEntries(m.measures().map(x => [x.id, x.value]));
    near(v.tS, v.tE * 0.6, 1e-12, 1e-12);
    near(v.x, v.tE <= 5 ? 0.8 * v.tE : 8 - 0.8 * v.tE, 1e-9, 1e-9);   // out for 5 yr, back for 5 yr
    checked++;
  }
  assert.equal(checked, 48);
});

test('Lab 20: the light-clock photon moves at c in the Earth frame (zig-zag geometry)', () => {
  for (const beta of [0.3, 0.8, 0.95]) {
    const m = L.create({ ...defaults(), beta, D: 4 });
    const tE = 2 * 4 / beta, g = 1 / Math.sqrt(1 - beta * beta), tickE = 0.5 * g;
    // sample short intervals on the outbound leg, avoiding the instants of mirror reflection
    let checked = 0;
    for (let te = 0.013; te < 4 / beta - 0.02; te += tickE / 7) {
      const ph0 = m.photon(te), dt = 1e-4 * tickE, ph1 = m.photon(te + dt);
      const phase = ((te / g) / 0.5) % 1, phase1 = (((te + dt) / g) / 0.5) % 1;
      if (Math.abs(phase - 0.5) < 1e-3 || phase1 < phase) continue;
      near(Math.hypot(ph1.x - ph0.x, ph1.y - ph0.y) / dt, 1, 1e-9);  // ly per yr = c
      checked++;
    }
    assert.ok(checked > 3 && tE > 0);
  }
});

test('Lab 20: length contraction and energy bars', () => {
  const v = run({ beta: 0.6, L0: 200, D: 5 }).v; near(v.L, 160, 1e-12); near(v.Dp, 4, 1e-12);
  const e = run({ beta: 0.8 }).m.energy();
  near(e[0].value, c * c, 1e-12); near(e[1].value, (5 / 3 - 1) * c * c, 1e-9);
});

test('Lab 20: challenge checkers accept correct evidence and reject wrong evidence', () => {
  assert.ok(L.challenges[0]({ runs: [rec({ beta: 0.865 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ beta: 0.8 })] }));
  assert.ok(L.challenges[1]({ runs: [rec({ beta: 0.8, D: 5 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ beta: 0.8, D: 4 })] }));
  assert.ok(L.challenges[2]({ runs: [rec({ beta: 0.97, L0: 100 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ beta: 0.9, L0: 100 })] }));
  assert.ok(L.challenges[3]({ runs: [rec({ beta: 0.8, D: 5 })] }));
  assert.ok(!L.challenges[3]({ runs: [rec({ beta: 0.6, D: 4 })] }));
});
