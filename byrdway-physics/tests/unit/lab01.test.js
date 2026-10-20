// Lab 1 (Measurement Lab) verification: the simulated data set is checked against hand-computed statistics.
import L, { mulberry32, gaussian, stats, sigFigs, readings } from '../../src/lab/labs/lab01.js';
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

test('Lab 1: structure', () => structure(L));

test('Lab 1: generator is deterministic and readings sit on the instrument scale', () => {
  const a = mulberry32(42), b = mulberry32(42);
  for (let i = 0; i < 5; i++) assert.equal(a(), b());
  assert.deepEqual(readings({ obj: 'pencil', inst: 'ruler', n: 10, seed: 3 }), readings({ obj: 'pencil', inst: 'ruler', n: 10, seed: 3 }));
  assert.notDeepEqual(readings({ obj: 'pencil', inst: 'ruler', n: 10, seed: 3 }), readings({ obj: 'pencil', inst: 'ruler', n: 10, seed: 4 }));
  for (const [inst, res] of [['stick', 1], ['ruler', 0.1], ['caliper', 0.002]]) for (const x of readings({ obj: 'bolt', inst, n: 25, seed: 9 })) near(Math.round(x / res) * res, x, 0, 1e-9);
  // Box–Muller deviates: mean ≈ 0, variance ≈ 1 over many samples
  const r = mulberry32(1), zs = Array.from({ length: 20000 }, () => gaussian(r)), st = stats(zs);
  assert.ok(Math.abs(st.mean) < 0.03 && Math.abs(st.sd - 1) < 0.03);
});

test('Lab 1: statistics helpers match hand calculations', () => {
  const st = stats([1, 2, 3, 4]);
  near(st.mean, 2.5, 1e-12); near(st.sd, Math.sqrt(5 / 3), 1e-12); near(st.sem, Math.sqrt(5 / 3) / 2, 1e-12);
  assert.equal(sigFigs(17.54, 2), 4); assert.equal(sigFigs(2.426, 3), 4); assert.equal(sigFigs(18, 0), 2); assert.equal(sigFigs(0.0507, 4), 3); assert.equal(sigFigs(17.6, 1), 3);
});

test('Lab 1: live measurements agree with an independent recomputation of the run data', () => {
  for (const inst of ['stick', 'ruler', 'caliper', 'offset']) {
    const p = { obj: 'pencil', inst, n: 12, seed: 5 }, { m, v } = run(L, p);
    near(m.t, 12 * 0.4 + 0.2, 1e-6);
    const d = m.data; assert.equal(d.length, 12); assert.equal(v.k, 12);
    let sum = 0; for (const x of d) sum += x; const mean = sum / 12;
    let ss = 0; for (const x of d) ss += (x - mean) * (x - mean); const sd = Math.sqrt(ss / 11);
    near(v.mean, mean, 1e-12); near(v.sd, sd, 1e-12); near(v.sem, sd / Math.sqrt(12), 1e-12);
    const res = { stick: 1, ruler: 0.1, caliper: 0.002, offset: 0.1 }[inst];
    near(v.U, Math.max(res / 2, sd / Math.sqrt(12)), 1e-12);
    near(v.pe, Math.abs(mean - 17.5362) / 17.5362 * 100, 1e-9);
    near(v.relU, v.U / mean * 100, 1e-12);
    assert.equal(v.reading, d[11]);
  }
  // part-way through: only the trials completed so far count
  const half = run(L, { obj: 'coin', inst: 'ruler', n: 10, seed: 2 }, 2.0 + 1e-6).v;
  assert.equal(half.k, 5);
});

test('Lab 1: reported value and significant figures follow the uncertainty', () => {
  const s = run(L, { obj: 'pencil', inst: 'stick', n: 10, seed: 1 }).m;
  const c = run(L, { obj: 'coin', inst: 'caliper', n: 10, seed: 1 }).m;
  const r = run(L, { obj: 'pencil', inst: 'ruler', n: 10, seed: 1 }).m;
  assert.match(s.reported(), /^\d+\.\d ± 0\.5 cm$/); assert.equal(s.measures().find(x => x.id === 'sig').value, 3);
  assert.match(c.reported(), /^2\.42\d ± 0\.001 cm$/); assert.equal(c.measures().find(x => x.id === 'sig').value, 4);
  assert.match(r.reported(), /^17\.5\d ± 0\.05 cm$/); assert.equal(r.measures().find(x => x.id === 'sig').value, 4);
});

test('Lab 1: precision vs accuracy — the worn ruler is offset by exactly 0.3 cm with the same scatter', () => {
  for (const obj of ['pencil', 'bolt', 'coin', 'book']) {
    const g = run(L, { obj, inst: 'ruler', n: 15, seed: 7 }).v, w = run(L, { obj, inst: 'offset', n: 15, seed: 7 }).v;
    near(w.mean - g.mean, 0.3, 0, 1e-9); near(w.sd, g.sd, 0, 1e-9);
  }
  // larger samples: mean converges to the accepted value; sd to the instrument's scatter
  let pooled = [];
  for (let seed = 1; seed <= 40; seed++) pooled = pooled.concat(readings({ obj: 'bolt', inst: 'caliper', n: 25, seed }));
  const st = stats(pooled);
  near(st.mean, 4.8172, 1e-4); assert.ok(Math.abs(st.sd - 0.002) < 0.0004, `sd ${st.sd}`);
  // the prediction: caliper spread is far smaller than meter-stick spread for the pencil
  const sStick = run(L, { obj: 'pencil', inst: 'stick', n: 10, seed: 1 }).v.sd, sCal = run(L, { obj: 'pencil', inst: 'caliper', n: 10, seed: 1 }).v.sd;
  assert.ok(sCal > 0 && sCal < sStick / 20);
});

test('Lab 1: evaluation key equals the model’s reading-uncertainty measurement', () => {
  for (const obj of ['pencil', 'coin']) for (const inst of ['stick', 'caliper']) {
    const ev = L.evaluate({ obj, inst, n: 1, seed: 1 }), v = run(L, { obj, inst, n: 1, seed: 1 }).v;
    near(ev.answer, v.resPct, 1e-12);
  }
  near(L.evaluate({ obj: 'pencil', inst: 'stick' }).answer, 0.5 / 17.5362 * 100, 1e-12); // ≈ 2.85 %
});

test('Lab 1: challenge checkers accept real runs and reject wrong ones', () => {
  const R = p => rec(L, p);
  assert.ok(L.challenges[0]({ runs: [R({ obj: 'coin', inst: 'caliper', n: 10, seed: 1 })] }));
  assert.ok(!L.challenges[0]({ runs: [R({ obj: 'coin', inst: 'ruler', n: 25, seed: 1 })] }));
  assert.ok(!L.challenges[0]({ runs: [R({ obj: 'coin', inst: 'caliper', n: 5, seed: 1 })] }));
  assert.ok(L.challenges[1]({ runs: [R({ obj: 'bolt', inst: 'offset', n: 10, seed: 1 }), R({ obj: 'bolt', inst: 'ruler', n: 10, seed: 1 })] }));
  assert.ok(!L.challenges[1]({ runs: [R({ obj: 'bolt', inst: 'offset', n: 10, seed: 1 }), R({ obj: 'pencil', inst: 'ruler', n: 10, seed: 1 })] }));
  assert.ok(!L.challenges[1]({ runs: [R({ obj: 'bolt', inst: 'ruler', n: 10, seed: 2 }), R({ obj: 'bolt', inst: 'ruler', n: 10, seed: 1 })] }));
  let found = false;
  for (let seed = 1; seed <= 20 && !found; seed++) found = L.challenges[2]({ runs: [R({ obj: 'pencil', inst: 'ruler', n: 4, seed }), R({ obj: 'pencil', inst: 'ruler', n: 16, seed })] });
  assert.ok(found, 'some seed pair demonstrates averaging');
  assert.ok(!L.challenges[2]({ runs: [R({ obj: 'pencil', inst: 'ruler', n: 4, seed: 1 }), R({ obj: 'pencil', inst: 'ruler', n: 8, seed: 1 })] }));
  assert.ok(!L.challenges[2]({ runs: [R({ obj: 'pencil', inst: 'stick', n: 4, seed: 1 }), R({ obj: 'pencil', inst: 'stick', n: 16, seed: 1 })] }));
});
