// Lab 2 (Vector Explorer) verification: component sums and river crossings vs hand-derived values.
import L, { resultant } from '../../src/lab/labs/lab02.js';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readJSON } from './helpers.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = lab => Object.fromEntries(lab.params.map(p => [p.id, p.value]));
const run = (lab, params, tEnd = Infinity, dt = lab.dt || 1 / 240) => {
  const m = lab.create({ ...defaults(lab), ...params });
  let guard = 0;
  while (m.t < tEnd - 1e-12 && !m.done && guard++ < 1e6) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = (lab, params, tEnd) => { const p = { ...defaults(lab), ...params }; return { params: p, final: run(lab, p, tEnd).v }; };

// Same assertions as tests/unit/labs.test.js plus the lab brief's minimum counts.
function structure(L) {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4, 'counts');
  assert.equal(T.challenges.length, L.challenges.length, 'challenge checkers');
  assert.ok(T.predict.prompt && T.predict.choices.length >= 3 && T.honors.prompt && T.honors.solution);
  assert.ok(L.params.length >= 2 && typeof L.create === 'function' && typeof L.evaluate === 'function' && typeof L.equations === 'function');
  assert.ok(L.graph.choices.length >= 2 && L.camera?.target && L.camera?.dist);
  const res = readJSON('src/data/resources.json');
  assert.equal(T.title, res.labs.find(l => l.num === L.num).title.replace("'", '’'), 'owner title');
  for (const s of L.sections) assert.equal(res.sections.find(x => x.id === s)?.unit, L.unit, `section ${s} in unit ${L.unit}`);
  const p = defaults(L), m = L.create(p);
  const sc = m.scene({}); assert.ok(sc.bodies?.length || sc.lines?.length, 'scene renders something');
  const ms = m.measures(); assert.ok(ms.filter(x => !x.hidden).length >= 4, 'live measurements');
  for (const c of L.graph.choices) for (const k of [...c.y, c.x || 't']) assert.ok(ms.some(x => x.id === k), `graph key ${k}`);
  assert.ok(Array.isArray(m.energy()));
  assert.ok(L.equations(p, m, 'quant').every(e => typeof e === 'string'));
  const ev = L.evaluate(p); assert.ok(Number.isFinite(ev.answer), 'evaluation answer');
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in ev.vars, `evaluate var ${k}`);
  for (const d of L.decor ? L.decor(p) : []) assert.ok(['ground', 'stars', 'box', 'sphere', 'cylinder', 'cone', 'torus', 'plane', 'ramp', 'line', 'label'].includes(d.shape), `decor ${d.shape}`);
  for (const b of sc.bodies || []) assert.ok(['box', 'sphere', 'cylinder', 'cone', 'torus', 'plane'].includes(b.shape) && b.pos.every(Number.isFinite), `body ${b.id}`);
  for (const v of sc.vectors || []) assert.ok([...v.from, ...v.vec].every(Number.isFinite), `vector ${v.id}`);
}

test('Lab 2: structure', () => { structure(L); structure({ ...L, params: L.params.map(p => (p.id === 'mode' ? { ...p, value: 'walk' } : p)) }); });

test('Lab 2: river crossing matches the 3-4-5 hand solution', () => {
  const { v } = run(L, { mode: 'river', A: 4, thA: 90, B: 3, W: 40 });
  near(v.R, 5, 1e-12); near(v.thR, Math.atan2(4, 3) * 180 / Math.PI, 1e-9); // 53.13° from the bank
  near(v.tCross, 10, 1e-9); near(v.drift, 30, 1e-9); near(v.y, 40, 1e-12); near(v.dist, 50, 1e-9); near(v.disp, 50, 1e-9);
  // doubling the current leaves the crossing time unchanged (independent components) — the prediction
  const d = run(L, { mode: 'river', A: 4, thA: 90, B: 6, W: 40 }).v;
  near(d.tCross, 10, 1e-9); near(d.drift, 60, 1e-9);
  // heading upstream at 120° with a 2 m/s current: vx = 4cos120° + 2 = 0, vy = 4 sin 120° = 2√3
  const u = run(L, { mode: 'river', A: 4, thA: 120, B: 2, W: 40 }).v;
  near(u.drift, 0, 0, 1e-9); near(u.tCross, 40 / (2 * Math.sqrt(3)), 1e-9);
  // a boat heading downstream never crosses
  const n = run(L, { mode: 'river', A: 4, thA: 0, B: 3, W: 40 });
  assert.ok(n.m.done && !Number.isFinite(n.v.tCross));
});

test('Lab 2: walk mode adds displacements head-to-tail', () => {
  const { v } = run(L, { mode: 'walk', A: 4, thA: 0, B: 3, thB: 90, C: 0 });
  near(v.Rx, 4, 1e-12); near(v.Ry, 3, 1e-12); near(v.R, 5, 1e-12); near(v.thR, 36.8699, 1e-5);
  near(v.x, 4, 1e-9); near(v.y, 3, 1e-9); near(v.dist, 7, 1e-9); near(v.disp, 5, 1e-9); assert.equal(v.leg, 2);
  const r = resultant({ mode: 'walk', A: 10, thA: 30, B: 6, thB: 180, C: 5, thC: 270 });
  near(r.R[0], 10 * Math.sqrt(3) / 2 - 6, 1e-12); near(r.R[1], 5 - 5, 0, 1e-12);
  // equilateral triangle closes
  const t = run(L, { mode: 'walk', A: 5, thA: 0, B: 5, thB: 120, C: 5, thC: 240 }).v;
  near(t.R, 0, 0, 1e-9); near(t.disp, 0, 0, 1e-9); near(t.dist, 15, 1e-9);
  // halfway along the first leg
  const h = run(L, { mode: 'walk', A: 4, thA: 0, B: 3, thB: 90, C: 0 }, 0.75).v;
  near(h.x, 2, 1e-6); near(h.y, 0, 0, 1e-9);
  // evaluate key = simulated resultant
  near(L.evaluate({ mode: 'walk', A: 4, thA: 0, B: 3, thB: 90, C: 0, thC: 0 }).answer, 5, 1e-12);
  near(L.evaluate({ mode: 'river', A: 4, thA: 90, B: 3, thB: 77, C: 9, thC: 10 }).answer, 5, 1e-12);
});

test('Lab 2: challenge checkers accept real runs and reject wrong ones', () => {
  const R = p => rec(L, p);
  assert.ok(L.challenges[0]({ runs: [R({ mode: 'walk', A: 5, thA: 0, B: 5, thB: 120, C: 5, thC: 240 })] }));
  assert.ok(!L.challenges[0]({ runs: [R({ mode: 'walk', A: 5, thA: 0, B: 5, thB: 120, C: 4, thC: 240 })] }));
  assert.ok(L.challenges[1]({ runs: [R({ mode: 'river', A: 4, thA: 120, B: 2, W: 40 })] }));
  assert.ok(!L.challenges[1]({ runs: [R({ mode: 'river', A: 4, thA: 90, B: 2, W: 40 })] }));
  assert.ok(!L.challenges[1]({ runs: [R({ mode: 'river', A: 4, thA: 90, B: 0, W: 40 })] }));
  const a = R({ mode: 'walk', A: 6, thA: 30, B: 4, thB: 135, C: 2, thC: 270 }), b = R({ mode: 'walk', A: 4, thA: 135, B: 6, thB: 30, C: 2, thC: 270 });
  assert.ok(L.challenges[2]({ runs: [a, b] }));
  assert.ok(!L.challenges[2]({ runs: [a, R({ mode: 'walk', A: 4, thA: 130, B: 6, thB: 30, C: 2, thC: 270 })] }));
});
