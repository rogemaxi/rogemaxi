// Lab 3 (Motion Simulator) verification: two-car kinematics vs hand-derived constant-acceleration results.
import L, { firstRoot } from '../../src/lab/labs/lab03.js';
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

test('Lab 3: structure', () => structure(L));

test('Lab 3: default catch-up problem (a = 2 m/s² from rest vs 10 m/s)', () => {
  const at5 = run(L, {}, 5).v;
  near(at5.xA, 25, 1e-9); near(at5.vA, 10, 1e-9); near(at5.xB, 50, 1e-9); near(at5.gap, 25, 1e-9); // speeds equal, gap largest
  assert.ok(!Number.isFinite(at5.tMeet));
  const { m, v } = run(L, {});
  near(v.tMeet, 10, 1e-9); near(v.xMeet, 100, 1e-9); assert.equal(v.meets, 1);
  near(m.t, 12, 1e-9); near(v.xA, 144, 1e-9); near(v.vA, 24, 1e-9); near(v.xB, 120, 1e-9);
  near(L.evaluate(defaults(L)).answer, at5.xA, 1e-9);
});

test('Lab 3: turnaround — displacement vs distance and the farthest point', () => {
  const v4 = run(L, { x0A: 0, v0A: 12, aA: -3 }, 4).v; near(v4.xA, 24, 1e-9); near(v4.vA, 0, 0, 1e-9);
  const v8 = run(L, { x0A: 0, v0A: 12, aA: -3 }, 8).v; near(v8.xA, 0, 0, 1e-9); near(v8.dA, 48, 1e-9);
  const v = run(L, { x0A: 0, v0A: 12, aA: -3 }).v;
  near(v.xA, 12 * 12 - 1.5 * 144, 1e-9); near(v.vA, -24, 1e-9); near(v.xMaxA, 24, 1e-9); near(v.dA, 24 + 96, 1e-9);
  // evaluate key reproduces the simulation at t = 5 s for an arbitrary set-up
  const p = { x0A: -12, v0A: 7.5, aA: -1.3 };
  near(L.evaluate({ ...defaults(L), ...p }).answer, run(L, p, 5).v.xA, 1e-9);
  near(L.evaluate({ ...defaults(L), ...p }).answer, -12 + 37.5 - 0.5 * 1.3 * 25, 1e-12);
});

test('Lab 3: meeting conditions — tangent, two meetings, never', () => {
  const t = run(L, { x0A: 0, v0A: 10, aA: 0, x0B: 25, v0B: 0, aB: 2 }).v; // discriminant zero
  near(t.tMeet, 5, 1e-6); near(t.xMeet, 50, 1e-6); assert.equal(t.meets, 1);
  // A at 8 m/s, B 30 m ahead with a = 1 → 30 − 8t + ½t² = 0 → t = 6 and 10 s
  const two = run(L, { x0A: 0, v0A: 8, aA: 0, x0B: 30, v0B: 0, aB: 1 }).v;
  near(two.tMeet, 6, 1e-9); near(two.xMeet, 48, 1e-9); assert.equal(two.meets, 2);
  const never = run(L, { x0A: 0, v0A: 5, aA: 0, x0B: 30, v0B: 0, aB: 1 }).v;
  assert.ok(!Number.isFinite(never.tMeet)); assert.equal(never.meets, 0);
  near(firstRoot(30, -8, 1, 0, 100), 6, 1e-12); assert.equal(firstRoot(30, -5, 1, 0, 100), null); near(firstRoot(-6, 3, 0, 0, 10), 2, 1e-12);
});

test('Lab 3: challenge checkers accept real runs and reject wrong ones', () => {
  const R = p => rec(L, p);
  assert.ok(L.challenges[0]({ runs: [R({ x0A: 0, v0A: 0, aA: 3, x0B: 0, v0B: 9, aB: 0 })] }));
  assert.ok(!L.challenges[0]({ runs: [R({})] }));
  assert.ok(L.challenges[1]({ runs: [R({ x0A: 0, v0A: 12, aA: -3 })] }));
  assert.ok(!L.challenges[1]({ runs: [R({ x0A: 0, v0A: 12, aA: -1 })] }));
  assert.ok(L.challenges[2]({ runs: [R({ x0A: 5, v0A: 20, aA: -5 })] }));
  assert.ok(!L.challenges[2]({ runs: [R({ x0A: 5, v0A: 20, aA: -4 })] }));
});
