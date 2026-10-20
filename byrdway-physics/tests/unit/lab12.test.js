// Lab 12 (Fluid Dynamics) verification: the headless model is compared with hand-derived hydrostatics,
// a damped-oscillator solution for the bobbing cube, and continuity + Bernoulli for the Venturi pipe.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab12.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 60, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const g = 9.8;

test('Lab 12: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Fluid Dynamics Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 11); assert.ok(L.sections.includes('11.4') && L.sections.includes('11.6'));
  for (const mode of ['scale', 'drop', 'pipe']) {
    const p = { ...defaults(), mode }, m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 2, mode);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4, mode);
    for (const c of L.graph.choices) for (const k of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
    assert.ok(Array.isArray(L.decor(p)) && L.equations(p, m).length >= 3);
    assert.ok(Array.isArray(m.energy()));
  }
  assert.ok(L.graph.choices.length >= 2);
  const ev = L.evaluate(defaults()); assert.ok(Number.isFinite(ev.answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in ev.vars, `evaluate var ${k}`);
});

test('Lab 12: spring scale reads mg − ρ_fluid·V·g (Archimedes) and the reading while moving includes drag', () => {
  // aluminium cube a = 0.20 m in water: m = 2700·0.008 = 21.6 kg, W = 211.68 N, Fb(full) = 1000·0.008·9.8 = 78.4 N
  const { v } = run({ mode: 'scale', rhoB: 2700, rhoF: 1000, a: 0.2 });
  near(v.W, 211.68); near(v.Fb, 78.4); near(v.T, 133.28); near(v.frac, 100); assert.equal(v.v, 0);
  // during lowering, fully submerged: T = W − Fb − b·U, b = 2·0.12·√(k·m), k = ρ g a² = 392 N/m
  const b = 2 * 0.12 * Math.sqrt(392 * 21.6);
  const mid = run({ mode: 'scale', rhoB: 2700, rhoF: 1000, a: 0.2 }, 6).v; // bottom at 1.15 − 0.48 = 0.67 m: 0.33 m deep
  near(mid.d, 0.33, 1e-6); near(mid.T, 211.68 - 78.4 - b * 0.08);
  // half-entered: the buoyant force is proportional to the submerged depth
  const half = run({ mode: 'scale', rhoB: 2700, rhoF: 1000, a: 0.2 }, 0.15 / 0.08 + 0.1 / 0.08).v;
  near(half.frac, 50, 1e-6); near(half.Fb, 39.2, 1e-6);
  // denser fluid: same cube in 1400 kg/m³ → reading (2700 − 1400)·0.008·9.8 = 101.92 N
  near(run({ mode: 'scale', rhoB: 2700, rhoF: 1400, a: 0.2 }).v.T, 101.92);
  // a floating cube makes the cable go slack: reading 0 and it floats at ρb/ρf
  const fl = run({ mode: 'scale', rhoB: 600, rhoF: 1000, a: 0.2 });
  assert.equal(fl.v.T, 0); near(fl.v.frac, 60, 2e-3);
});

test('Lab 12: released cube bobs as a damped oscillator and floats at ρ_block/ρ_fluid', () => {
  // a = 0.30, ρb/ρf = 0.4: m = 10.8 kg, k = 1000·9.8·0.09 = 882 N/m, equilibrium depth 0.12 m, released at depth 0
  const m = 10.8, k = 882, b = 2 * 0.12 * Math.sqrt(k * m), w0 = Math.sqrt(k / m), gam = b / (2 * m), wd = Math.sqrt(w0 * w0 - gam * gam);
  const x = t => 0.12 * Math.exp(-gam * t) * (Math.cos(wd * t) + gam / wd * Math.sin(wd * t)); // height above equilibrium
  for (const t of [0.2, 0.35, 0.7, 1.3, 2.9]) near(run({ mode: "drop", rhoB: 400, rhoF: 1000, a: 0.3, h0: 0 }, t).v.d, 0.12 - x(t), 2e-4, 1e-6);
  const { v, m: model } = run({ mode: 'drop', rhoB: 400, rhoF: 1000, a: 0.3, h0: 0 });
  near(v.Tb, 2 * Math.PI / wd, 2e-4);   // measured period between depth maxima = damped period 0.700 s
  near(2 * Math.PI / wd, 0.7003, 1e-3);
  near(v.frac, 40, 1e-4); near(v.Fb, v.W, 1e-4); assert.ok(Math.abs(v.v) < 1e-4);
  // energy: gravitational PE released = KE + work against buoyancy + thermal
  const e = model.energy(); near(e[1].value, e[0].value + e[2].value + e[3].value, 1e-6);
  // dropped from 0.3 m above the surface (nonlinear entry): energy still balances at every stage
  for (const t of [0.2, 0.4, 0.9, 5]) { const en = run({ mode: 'drop', rhoB: 700, rhoF: 1000, a: 0.25, h0: 0.3 }, t).m.energy(); near(en[1].value, en[0].value + en[2].value + en[3].value, 1e-4); }
  // free fall before entry (bottom reaches the surface at t = √(2·0.3/9.8) = 0.247 s): at t = 0.2 s, v = −g t, d = −0.3 + ½ g t²
  const pre = run({ mode: 'drop', rhoB: 700, rhoF: 1000, a: 0.25, h0: 0.3 }, 0.2).v;
  near(pre.v, -1.96, 1e-9); near(pre.d, -0.104, 1e-9); assert.equal(pre.Fb, 0);
  // a dense cube sinks to the floor; the floor then supplies N = mg − Fb
  const sink = run({ mode: 'drop', rhoB: 2000, rhoF: 1000, a: 0.2 }).v;
  near(sink.N, (2000 - 1000) * 0.008 * g); near(sink.d, 1.0);
});

test('Lab 12: Venturi pipe obeys continuity and Bernoulli; the tracer measures v₂', () => {
  // d₂/d₁ = 0.5 → v₂ = 4 v₁ = 6 m/s; level throat: ΔP = ½·1000·(36 − 2.25) = 16.875 kPa
  const { v, m } = run({ mode: 'pipe', v1: 1.5, r: 0.5, dh: 0, rhoF: 1000 });
  near(v.v2, 6); near(v.dP, 16.875); near(v.P1, 150); near(v.P2, 133.125); near(v.Q, Math.PI * 0.09 / 4 * 1.5 * 1000);
  near(v.tN, 2 / 6, 1e-6); near(v.xp, 3.5);
  // raised throat adds ρ g Δh: 1200 kg/m³, v1 = 1, r = 0.6, Δh = 0.8 → v₂ = 2.7778, ΔP = ½·1200·(7.716 − 1) + 1200·9.8·0.8
  const r = run({ mode: 'pipe', v1: 1, r: 0.6, dh: 0.8, rhoF: 1200 }).v;
  const v2 = 1 / 0.36; near(r.v2, v2); near(r.dP, (0.5 * 1200 * (v2 * v2 - 1) + 1200 * g * 0.8) / 1000); near(r.tN, 2 / v2, 1e-6);
  // Bernoulli total for a 1 L parcel is the same everywhere along the tracer's path
  const tot = [];
  for (const t of [0.5, 1.4, 1.7, 2.2, 2.6, 3.5]) tot.push(run({ mode: 'pipe', v1: 1, r: 0.6, dh: 0.8, rhoF: 1200 }, t).m.energy()[3].value);
  for (const x of tot) near(x, tot[0], 1e-9);
  near(m.energy()[3].value, 150e3 * 1e-3 + 0.5 * 1000 * 1e-3 * 1.5 ** 2, 1e-12); // P₁V + ½ρVv₁² = 151.125 J at every point
});

test('Lab 12: evaluation key matches the simulated scale reading', () => {
  for (const p of [{ rhoB: 2700, rhoF: 1000, a: 0.2 }, { rhoB: 1500, rhoF: 1200, a: 0.35 }]) near(L.evaluate({ ...defaults(), ...p }).answer, run({ mode: 'scale', ...p }).v.T, 1e-9);
  assert.equal(L.evaluate({ ...defaults(), rhoB: 600 }).answer, 0);
});

test('Lab 12: challenge checkers accept correct evidence and reject wrong evidence', () => {
  assert.ok(L.challenges[0]({ runs: [rec({ mode: 'drop', rhoB: 600, rhoF: 1000, a: 0.3 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ mode: 'drop', rhoB: 500, rhoF: 1000, a: 0.3 })] }));
  assert.ok(L.challenges[1]({ runs: [rec({ mode: 'scale', rhoB: 2000, rhoF: 1000, a: 0.2 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mode: 'scale', rhoB: 2700, rhoF: 1000, a: 0.2 })] }));
  // ΔP = ½ρ v1² (1/r⁴ − 1) = 20 kPa with ρ = 1000, v1 = 1.5: 1/r⁴ = 18.78 → r = 0.4834 → slider r = 0.48 gives 20.5 kPa
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'pipe', v1: 1.5, r: 0.48, dh: 0, rhoF: 1000 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'pipe', v1: 1.5, r: 0.5, dh: 0, rhoF: 1000 })] }));
});
