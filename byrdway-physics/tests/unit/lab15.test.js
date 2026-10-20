// Lab 15 (Optics) verification: the vector ray trace is compared with hand-computed Snell's-law angles,
// critical angles and Fresnel reflectance; the traced lens image with 1/f = 1/d_o + 1/d_i and m = −d_i/d_o.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab15.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 1e9, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const D = Math.PI / 180;

test('Lab 15: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Optics Laboratory');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 14); assert.ok(L.sections.includes('14.3') && L.sections.includes('14.4') && L.sections.includes('14.5'));
  for (const mode of ['refract', 'lens']) for (const lens of ['converging', 'diverging']) {
    const p = { ...defaults(), mode, lens }, m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length && sc.lines.length >= 2, mode);
    for (const ln of sc.lines) for (const pt of ln.pts) assert.ok(pt.every(Number.isFinite), `finite ray points ${mode}`);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4, mode);
    for (const c of L.graph.choices) for (const k of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
    assert.ok(Array.isArray(L.decor(p)) && L.equations(p, m).length >= 3 && Array.isArray(m.energy()));
  }
  const ev = L.evaluate(defaults()); assert.ok(Number.isFinite(ev.answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in ev.vars, `evaluate var ${k}`);
  // object exactly at the focal point: image at infinity, rays still drawable
  const fp = L.create({ ...defaults(), do: 10, f: 10 }); while (!fp.done) fp.step(1 / 240);
  assert.equal(fp.measures().find(x => x.id === 'di').value, Infinity);
  for (const ln of fp.scene({}).lines) for (const pt of ln.pts) assert.ok(pt.every(Number.isFinite));
});

test('Lab 15: refraction follows n₁ sin θ₁ = n₂ sin θ₂ with Fresnel reflectance', () => {
  // air → glass at 60°: sin θ₂ = sin 60°/1.5 = 0.57735 → θ₂ = 35.264°
  const a = run({ mode: 'refract', n1: 1, n2: 1.5, th1: 60 }).v;
  near(a.th2, 35.2644, 1e-5); near(a.ratio, 1.5, 1e-9); assert.equal(a.tir, 0); assert.ok(Number.isNaN(a.thc));
  // Fresnel at 60°: cos i = 0.5, cos t = 0.81650; rs = (0.5 − 1.22474)/(0.5 + 1.22474) = −0.42013, rp = (0.81650 − 0.75)/(0.81650 + 0.75) = 0.04245
  near(a.R, 100 * (0.42013 ** 2 + 0.04245 ** 2) / 2, 1e-3); near(a.R + a.T, 100, 1e-12);
  // normal incidence: R = ((n₁ − n₂)/(n₁ + n₂))² = 4 %
  near(run({ mode: 'refract', n1: 1, n2: 1.5, th1: 0 }).v.R, 4, 1e-9);
  // water → air: θc = sin⁻¹(1/1.33) = 48.753°; 45° refracts at sin⁻¹(1.33·sin 45°) = 70.128°, 50° is totally reflected
  const w = run({ mode: 'refract', n1: 1.33, n2: 1, th1: 45 }).v;
  near(w.thc, 48.7535, 1e-5); near(w.th2, 70.1276, 1e-5);
  const t = run({ mode: 'refract', n1: 1.33, n2: 1, th1: 50 }).v; assert.equal(t.tir, 1); assert.equal(t.R, 100); assert.ok(Number.isNaN(t.th2));
  // the sweep passes through every angle from 0: halfway through, θ₁ = 30°
  near(run({ mode: 'refract', n1: 1, n2: 1.5, th1: 60 }, 3).v.th1, 30, 1e-9);
  // diamond → air critical angle: sin⁻¹(1/2.42) = 24.41°
  near(run({ mode: 'refract', n1: 2.42, n2: 1, th1: 10 }).v.thc, 24.407, 1e-4);
});

test('Lab 15: traced lens images satisfy 1/f = 1/d_o + 1/d_i and m = −d_i/d_o', () => {
  const cases = [
    ['converging', 10, 15, 30, -2], ['converging', 10, 30, 15, -0.5], ['converging', 10, 20, 20, -1],
    ['converging', 10, 5, -10, 2], ['converging', 25, 100, 100 / 3, -1 / 3], ['diverging', 20, 20, -10, 0.5], ['diverging', 15, 45, -11.25, 0.25],
  ];
  for (const [lens, f, d, di, mag] of cases) {
    const v = run({ mode: 'lens', lens, f, do: d, ho: 4 }).v;
    near(v.di, di, 1e-9); near(v.m, mag, 1e-9); near(v.hi, 4 * mag, 1e-9);
    assert.equal(v.real, di > 0 ? 1 : 0, `${lens} ${d}`);
  }
  // the sweep: 1/d_i = 1/f − 1/d_o holds at every moment (straight line, slope −1, intercept 1/f = 10 m⁻¹)
  for (const t of [0.5, 2, 4.4]) { const v = run({ mode: 'lens', f: 10, do: 15 }, t).v; near(v.invDi, 10 - v.invDo, 1e-9); assert.ok(v.do < 100 && v.do > 15); }
});

test('Lab 15: evaluation key matches the traced image distance', () => {
  for (const p of [{}, { lens: 'diverging', f: 20, do: 35 }, { f: 12, do: 40 }]) near(L.evaluate({ ...defaults(), ...p }).answer, run({ mode: 'lens', ...p }).v.di, 1e-9);
});

test('Lab 15: challenge checkers accept correct evidence and reject wrong evidence', () => {
  // water → air, θc = 48.75°: 49° is TIR, 48.5° is not
  assert.ok(L.challenges[0]({ runs: [rec({ mode: 'refract', n1: 1.33, n2: 1, th1: 48.5 }), rec({ mode: 'refract', n1: 1.33, n2: 1, th1: 49 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'refract', n1: 1.33, n2: 1, th1: 46 }), rec({ mode: 'refract', n1: 1.33, n2: 1, th1: 50 })] }));
  assert.ok(L.challenges[1]({ runs: [rec({ mode: 'lens', lens: 'converging', f: 15, do: 30 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mode: 'lens', lens: 'converging', f: 15, do: 40 })] }));
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'lens', lens: 'diverging', f: 20, do: 20 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'lens', lens: 'diverging', f: 20, do: 40 })] }));
});
