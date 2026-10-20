// Lab 7 (Energy Transformation) verification: energy conservation of the RK4 track model and agreement with
// hand-derived energy results (½kx² + mgH = ½mv² + mgh, centripetal normal force, friction losses).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L, { profile } from '../../src/lab/labs/lab07.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 25, dt = L.dt || 1 / 240, watch) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) { m.step(dt); watch?.(m); }
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const g = 9.8;

test('Lab 7: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Energy Transformation Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.equal(L.unit, 6); assert.ok(L.sections.includes('6.6'));
  for (const track of ['coaster', 'halfpipe']) {
    const p = { ...defaults(), track };
    const m = L.create(p);
    assert.ok(m.scene({}).bodies.length && m.measures().filter(x => !x.hidden).length >= 4);
    assert.equal(m.energy().length, 5);
    assert.ok(L.decor(p).length > 3 && L.equations(p, m).length >= 3);
    const ev = L.evaluate(p); assert.ok(Number.isFinite(ev.answer));
    for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in ev.vars, `evaluate var ${k}`);
    for (const c of L.graph.choices) for (const k of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
  }
});

test('Lab 7: the track profile is C² smooth (derivatives agree with finite differences)', () => {
  for (const p of [{ track: 'coaster', H: 4, Hh: 3 }, { track: 'halfpipe', H: 4 }]) {
    const h = profile(p), e = 1e-5;
    for (const x of [1.3, 4.1, 12.2, 14.6, 17.9]) {
      near(h(x)[1], (h(x + e)[0] - h(x - e)[0]) / (2 * e), 1e-5, 1e-7);
      near(h(x)[2], (h(x + e)[1] - h(x - e)[1]) / (2 * e), 1e-5, 1e-6);
    }
  }
  const h = profile({ track: 'coaster', H: 4, Hh: 3 });
  near(h(-0.3)[0], 4); near(h(9)[0], 0.5); near(h(15)[0], 3); near(h(25)[0], 0.5);
});

test('Lab 7: frictionless energy is conserved and speeds follow ½kx² + mgH = ½mv² + mgh', () => {
  // m = 2 kg, k = 1000 N/m, x = 0.20 m → Es = 20 J; H = 4 m, hill 3 m.
  const p = { track: 'coaster', m: 2, H: 4, Hh: 3, k: 1000, xc: 0.2, mu: 0 };
  const E0 = 20 + 2 * g * 4; // 98.4 J
  let maxErr = 0;
  const { v } = run(p, 25, undefined, m => { const e = m.energy(); maxErr = Math.max(maxErr, Math.abs(e[4].value - E0)); });
  assert.ok(maxErr < 1e-6 * E0, `energy drift ${maxErr}`);
  assert.equal(v.end, 1); assert.equal(v.clear, 1);
  near(v.vMax, Math.sqrt(2 * (E0 - 2 * g * 0.5) / 2), 1e-5);        // at h = 0.5 m: 9.5289 m/s
  near(v.vTop, Math.sqrt(2 * (E0 - 2 * g * 3) / 2), 1e-4);          // over the 3 m hilltop: 6.0332 m/s
  near(v.vEnd, Math.sqrt(2 * (E0 - 2 * g * 0.5) / 2), 1e-4);
  near(L.evaluate({ ...defaults(), ...p }).answer, v.vMax, 1e-5);
  // mass independence of the gravity-only speed: half-pipe from 4 m, v_bottom = √(2gH) = 8.854 m/s
  for (const m of [1, 7]) near(run({ track: 'halfpipe', m, H: 4, mu: 0 }, 3).v.vMax, Math.sqrt(2 * g * 4), 1e-5);
});

test('Lab 7: prediction scenario — car rolls back from a taller hill and returns to its start', () => {
  const { v, m } = run({}, 25); // defaults: H = 4, hill 4.5, Es = 1.25 J, μ = 0
  assert.equal(v.clear, 0); assert.equal(v.end, 0);
  // highest point reached on the hill: mgh = Es + mgH → h = 4 + 1.25/19.6 = 4.0638 m (below the 4.5 m top)
  let hMax = 0;
  run({}, 25, undefined, mm => { const x = mm.measures(); if (x[1].value > 8) hMax = Math.max(hMax, x[2].value); });
  near(hMax, 4 + 1.25 / 19.6, 1e-4);
  near(m.energy()[4].value, 1.25 + 2 * g * 4, 1e-6);
});

test('Lab 7: normal force includes the centripetal term; friction losses close the energy books', () => {
  // Half-pipe h = (1/6)u²: at the bottom κ = h'' = 1/3 m⁻¹, so N = m(g + v²/3)
  const L2 = L.create({ ...defaults(), track: 'halfpipe', m: 2, H: 4, mu: 0 });
  let best = null;
  while (L2.t < 3) { L2.step(1 / 240); const x = Object.fromEntries(L2.measures().map(q => [q.id, q.value])); if (!best || Math.abs(x.x - 12) < Math.abs(best.x - 12)) best = x; }
  near(best.N, 2 * (g + best.v * best.v / 3), 2e-3);
  near(best.N, 2 * (g + 2 * g * 4 / 3), 5e-3); // ≈ 71.9 N at v² = 2gH
  // with friction: total (KE + PE + Q) stays equal to the starting energy, and the car comes to rest
  let maxErr = 0;
  const f = run({ track: 'halfpipe', m: 2, H: 4, mu: 0.05 }, 25, undefined, m => { maxErr = Math.max(maxErr, Math.abs(m.energy()[4].value - 2 * g * 4)); });
  assert.ok(maxErr < 1e-5 * 78.4, `energy drift ${maxErr}`);
  assert.ok(f.v.Q > 0 && f.v.h1 < 4 && f.v.h1 > 3);
  // on a flat stretch the friction loss is μmg × distance: compare thermal energy on the coaster flat (x 6 → 11)
  const c = L.create({ ...defaults(), track: 'coaster', m: 2, H: 3, Hh: 0.5, k: 1000, xc: 0.2, mu: 0.05 });
  let Q6 = null, Q11 = null;
  while (!c.done) { c.step(1 / 240); const x = Object.fromEntries(c.measures().map(q => [q.id, q.value])); if (Q6 == null && x.x >= 6) Q6 = [x.x, x.Q]; if (Q11 == null && x.x >= 11) Q11 = [x.x, x.Q]; }
  near(Q11[1] - Q6[1], 0.05 * 2 * g * (Q11[0] - Q6[0]), 1e-6);
});

test('Lab 7: challenge checkers accept correct evidence and reject wrong evidence', () => {
  const C = L.challenges;
  // 1: H = 4, hill 4.5 (needs 9.8 J), k = 1050, x = 0.14 → 10.29 J → v_top = 0.70 m/s
  const r1 = rec({ k: 1050, xc: 0.14 });
  near(r1.final.vTop, Math.sqrt(2 * (10.29 - 9.8) / 2), 1e-3);
  assert.ok(C[0]({ runs: [r1] }));
  assert.ok(!C[0]({ runs: [rec({ k: 1000, xc: 0.2 })] }));            // clears too fast (2.6 m/s)
  assert.ok(!C[0]({ runs: [rec({})] }));                                // does not clear
  // 2: find a half-pipe setting whose first turning height is 3.00 ± 0.05 m by search over the sliders
  let hit = null;
  for (let H = 3.1; H <= 6 && !hit; H += 0.1) for (let mu = 0.01; mu <= 0.1 && !hit; mu += 0.01) {
    const r = rec({ track: 'halfpipe', H: +H.toFixed(1), mu: +mu.toFixed(2) }); if (Math.abs(r.final.h1 - 3) <= 0.05) hit = r;
  }
  assert.ok(hit && C[1]({ runs: [hit] }), 'a reachable half-pipe setting exists');
  assert.ok(!C[1]({ runs: [rec({ track: 'halfpipe', H: 3, mu: 0 })] }));
  assert.ok(!C[1]({ runs: [rec({ track: 'halfpipe', H: 5, mu: 0.02 })] }));
  // 3: H = 2.3, hill 0.5, k = 100, x = 0.12 → v² = 2g(1.8) + 100·0.0144/2 = 36.0 → 6.00 m/s
  const r3 = rec({ H: 2.3, Hh: 0.5, k: 100, xc: 0.12 });
  near(r3.final.vEnd, Math.sqrt(2 * g * 1.8 + 0.72), 1e-4);
  assert.ok(C[2]({ runs: [r3] }));
  assert.ok(!C[2]({ runs: [rec({ H: 3, Hh: 0.5, k: 100, xc: 0.12 })] }));
});
