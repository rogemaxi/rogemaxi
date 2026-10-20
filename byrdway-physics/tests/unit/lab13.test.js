// Lab 13 (Thermal Energy) verification: contact heat exchange vs the exponential solution of Newton's law and
// calorimetry; the piston gas vs PV = nRT, W = nRT ln(V₂/V₁), W = PΔV and the first law with Cv = 3/2 R.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab13.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 1e6, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => { const r = run(params); return { params: { ...defaults(), ...params }, final: r.v, t: r.m.t }; };
const R = 8.314462618;

test('Lab 13: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Thermal Energy Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 12); assert.ok(L.sections.includes('12.3') && L.sections.includes('12.7'));
  for (const mode of ['contact', 'gas']) for (const proc of ['isothermal', 'isobaric', 'isochoric']) {
    const p = { ...defaults(), mode, proc }, m = L.create(p);
    const sc = m.scene({}); assert.ok(sc.bodies.length, mode);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4, mode);
    for (const c of L.graph.choices) for (const k of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
    assert.ok(Array.isArray(L.decor(p)) && L.equations(p, m).length >= 3 && m.energy().length >= 2);
  }
  const ev = L.evaluate(defaults()); assert.ok(Number.isFinite(ev.answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in ev.vars, `evaluate var ${k}`);
});

test('Lab 13: contact temperatures follow ΔT = ΔT₀·e^(−t/τ) and settle at the calorimetry temperature', () => {
  // 1 kg water (C = 4186 J/K) at 80 °C, 1 kg copper (385 J/K) at 20 °C, G = 10 W/K
  const C1 = 4186, C2 = 385, lam = 10 * (1 / C1 + 1 / C2), Teq = (C1 * 80 + C2 * 20) / (C1 + C2);
  near(Teq, 74.9464, 1e-5);
  for (const tq of [5, 20, 60, 150]) {
    const { m, v } = run({}, tq), t = m.t, dT = 60 * Math.exp(-lam * t);
    near(v.dT, dT, 1e-8); near(v.T1, Teq + dT * C2 / (C1 + C2), 1e-9); near(v.T2, Teq - dT * C1 / (C1 + C2), 1e-9);
    near(v.H, 10 * dT, 1e-8);
    near(v.Qa, v.Qb, 1e-9, 1e-6);  // energy conservation in the insulated box
  }
  const { v } = run({});
  near(v.T1, Teq, 1e-4); near(v.T2, Teq, 1e-3); near(v.tHalf, Math.LN2 / lam, 1e-6); near(v.tHalf, 24.438, 1e-4);
  // the final temperature does not depend on G; the halving time scales as 1/G
  const g2 = run({ G: 20 }).v; near(g2.T1, Teq, 1e-4); near(g2.tHalf, v.tHalf / 2, 1e-6);
  // equal water masses: exactly halfway
  near(run({ mat2: 'water' }).v.T2, 50, 1e-3); // run ends at 8τ: ΔT = 60·e⁻⁸ = 0.02 K still remains
});

test('Lab 13: piston gas obeys PV = nRT and the first law in each process', () => {
  const nRT = R * 300; // n = 1 mol, T = 300 K → 2494.34 J
  const iso = run({ mode: 'gas', proc: 'isothermal', n: 1, V1: 10, ratio: 2 }).v;
  near(iso.W, nRT * Math.log(2), 1e-6); near(iso.W, 1728.94, 1e-5); near(iso.Q, iso.W, 1e-12); near(iso.dU, 0, 1, 1e-9);
  near(iso.Pg, nRT / 0.02 / 1000, 1e-12); near(iso.V, 20, 1e-12); near(iso.Tg, 300, 1e-12);
  const bar = run({ mode: 'gas', proc: 'isobaric', n: 1, V1: 10, ratio: 2 }).v;
  near(bar.Pg, nRT / 0.01 / 1000, 1e-12); near(bar.W, nRT, 1e-9); near(bar.Tg, 600, 1e-12);
  near(bar.dU, 1.5 * nRT, 1e-12); near(bar.Q, 2.5 * nRT, 1e-9);           // Q = n·Cp·ΔT
  const cho = run({ mode: 'gas', proc: 'isochoric', n: 1, V1: 10, ratio: 2 }).v;
  assert.equal(cho.W, 0); near(cho.Q, 1.5 * nRT, 1e-12); near(cho.Pg, 2 * nRT / 0.01 / 1000, 1e-12);
  // isothermal compression: work done on the gas, heat leaves it
  const cmp = run({ mode: 'gas', proc: 'isothermal', n: 0.5, V1: 8, ratio: 0.5 }).v;
  near(cmp.W, -0.5 * nRT * Math.LN2, 1e-6); assert.ok(cmp.Q < 0);
  // halfway through an isothermal process, PV is still nRT
  const half = run({ mode: 'gas', proc: 'isothermal', n: 2, V1: 5, ratio: 3 }, 3).v;
  near(half.Pg * half.V, 2 * nRT, 1e-12);
  near(half.W, 2 * nRT * Math.log(half.V / 5), 1e-6);
});

test('Lab 13: evaluation key matches the simulated equilibrium temperature', () => {
  for (const p of [{}, { m1: 2, mat1: 'iron', T1: 95, m2: 0.5, mat2: 'water', T2: 10 }]) near(L.evaluate({ ...defaults(), ...p }).answer, run(p).v.T2, 1e-3);
});

test('Lab 13: challenge checkers accept correct evidence and reject wrong evidence', () => {
  // water 1 kg at 20 °C + aluminium 2 kg at 87 °C → (83720 + 156600)/5986 = 40.15 °C
  assert.ok(L.challenges[0]({ runs: [rec({ m1: 1, mat1: 'water', T1: 20, m2: 2, mat2: 'aluminum', T2: 87 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ m1: 1, mat1: 'water', T1: 20, m2: 2, mat2: 'aluminum', T2: 95 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ m1: 1, mat1: 'water', T1: 20, m2: 1, mat2: 'water', T2: 60 })] })); // same material
  // two 1 kg water bodies, G = 24 W/K: t½ = ln2·4186/48 = 60.45 s
  assert.ok(L.challenges[1]({ runs: [rec({ mat1: 'water', mat2: 'water', G: 24 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ mat1: 'water', mat2: 'water', G: 10 })] }));
  // n = 1.1, ratio 0.7: Q = 1.1·2494.34·ln 0.7 = −978.6 J
  assert.ok(L.challenges[2]({ runs: [rec({ mode: 'gas', proc: 'isothermal', n: 1.1, ratio: 0.7 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ mode: 'gas', proc: 'isothermal', n: 1, ratio: 0.7 })] }));
});
