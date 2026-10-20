// Lab 4 (Projectile Launcher) verification: RK4 model vs closed-form projectile results and the library drag integrator.
import L from '../../src/lab/labs/lab04.js';
import { projectileDrag } from '../../src/physics/index.js';
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

test('Lab 4: structure', () => structure(L));

test('Lab 4: no-drag flight matches hand-derived closed forms', () => {
  // 20 m/s at 45° from the ground: R = v²/g = 40.816 m, H = v² sin²θ / 2g = 10.204 m, T = 2 v sinθ / g = 2.886 s
  const { v } = run(L, { v0: 20, th: 45, h0: 0, k: 0 });
  near(v.range, 400 / 9.8, 1e-6); near(v.hMax, 200 / 19.6, 1e-6); near(v.tFlight, 2 * 20 * Math.SQRT1_2 / 9.8, 1e-6);
  near(v.vImpact, 20, 1e-6); near(v.vx, 20 * Math.SQRT1_2, 1e-9);
  // horizontal launch from 20 m at 10 m/s: t = √(2h/g) = 2.0203 s, R = 20.203 m
  const h = run(L, { v0: 10, th: 0, h0: 20, k: 0 }).v;
  near(h.tFlight, Math.sqrt(40 / 9.8), 1e-6); near(h.range, 10 * Math.sqrt(40 / 9.8), 1e-6); near(h.hMax, 20, 1e-12);
  // time of flight from a height is independent of horizontal speed
  near(run(L, { v0: 20, th: 0, h0: 20, k: 0 }).v.tFlight, h.tFlight, 1e-6);
  // complementary angles give equal ranges (the prediction): R = v² sin2θ/g = 35.35 m at 30° and 60°
  const r30 = run(L, { v0: 20, th: 30, h0: 0, k: 0 }).v.range, r60 = run(L, { v0: 20, th: 60, h0: 0, k: 0 }).v.range;
  near(r30, 400 * Math.sin(Math.PI / 3) / 9.8, 1e-6); near(r60, r30, 1e-6);
  // mid-flight state equals the parabola at t = 1 s
  const mid = run(L, { v0: 20, th: 30, h0: 5, k: 0 }, 1).v;
  near(mid.x, 20 * Math.cos(Math.PI / 6), 1e-9); near(mid.y, 5 + 10 - 4.9, 1e-9); near(mid.vy, 10 - 9.8, 1e-9);
  // evaluation key equals the simulated range
  for (const p of [{ v0: 20, th: 45, h0: 0 }, { v0: 13.5, th: 22, h0: 17 }]) near(L.evaluate({ ...p, k: 0, xT: 30 }).answer, run(L, { ...p, k: 0 }).v.range, 1e-6);
});

test('Lab 4: energy is conserved without drag and dissipated with drag', () => {
  const m = L.create({ v0: 25, th: 60, h0: 10, k: 0, xT: 30 });
  for (let i = 0; i < 500 && !m.done; i++) { m.step(1 / 240); const e = m.energy(); near(e[0].value + e[1].value, e[3].value, 1e-9); assert.ok(e[2].value < 1e-9); }
  const d = L.create({ v0: 25, th: 60, h0: 10, k: 0.02, xT: 30 }); let last = 0;
  while (!d.done) { d.step(1 / 240); const lost = d.energy()[2].value; assert.ok(lost >= last - 1e-9); last = lost; }
  assert.ok(last > 0.2 * d.energy()[3].value);
});

test('Lab 4: drag flight agrees with the library projectileDrag integrator and loses range', () => {
  for (const p of [{ v0: 30, th: 40, h0: 0, k: 0.01 }, { v0: 20, th: 60, h0: 12, k: 0.03 }]) {
    const v = run(L, p).v, ref = projectileDrag(p.v0, p.th, p.k, { h0: p.h0, dt: 1e-4 });
    near(v.range, ref.range, 1e-4); near(v.tFlight, ref.tFlight, 1e-4); near(v.hMax, ref.hMax, 1e-4);
    const vac = run(L, { ...p, k: 0 }).v;
    assert.ok(v.range < vac.range && v.hMax < vac.hMax);
  }
  // with drag, the optimum angle is below 45°
  const R = th => run(L, { v0: 30, th, h0: 0, k: 0.01 }).v.range;
  assert.ok(R(40) > R(45) && R(40) > R(35)); // peak near 40°, not 45°
});

test('Lab 4: challenge checkers accept real runs and reject wrong ones', () => {
  const Rr = p => rec(L, p);
  assert.ok(L.challenges[0]({ runs: [Rr({ v0: 20, th: 45, h0: 0, k: 0, xT: 41 })] }));
  assert.ok(!L.challenges[0]({ runs: [Rr({ v0: 20, th: 45, h0: 0, k: 0, xT: 30 })] }));
  assert.ok(L.challenges[1]({ runs: [Rr({ v0: 20, th: 30, h0: 0, k: 0 }), Rr({ v0: 20, th: 60, h0: 0, k: 0 })] }));
  assert.ok(!L.challenges[1]({ runs: [Rr({ v0: 20, th: 30, h0: 0, k: 0 }), Rr({ v0: 20, th: 50, h0: 0, k: 0 })] }));
  assert.ok(!L.challenges[1]({ runs: [Rr({ v0: 20, th: 30, h0: 0, k: 0.02 }), Rr({ v0: 20, th: 60, h0: 0, k: 0.02 })] }));
  const drag = th => Rr({ v0: 30, th, h0: 0, k: 0.01 });
  assert.ok(L.challenges[2]({ runs: [drag(45), drag(40), drag(55)] }));
  assert.ok(!L.challenges[2]({ runs: [drag(45), drag(50), drag(55)] }));
  const vac = th => Rr({ v0: 30, th, h0: 0, k: 0 });
  assert.ok(!L.challenges[2]({ runs: [vac(45), vac(40), vac(35)] }));
});
