// Lab 19 (Quantum Discovery Lab) verification: the headless model is compared with hand-derived photoelectric and
// Bohr-model results (hc/e = 6.62607015e-34 × 299792458 / 1.602176634e-19 = 1.239841984e-6 V·m).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab19.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = 60, dt = L.dt || 1 / 240) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
const HC = 1239.841984; // eV·nm, hand value

test('Lab 19: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Quantum Discovery Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 18); assert.ok(L.sections.includes('18.3') && L.sections.includes('18.2'));
  assert.ok(L.params.length >= 2 && typeof L.create === 'function' && typeof L.evaluate === 'function' && typeof L.equations === 'function');
  for (const mode of ['photo', 'hydrogen']) {
    const p = { ...defaults(), mode };
    const m = L.create(p);
    for (let i = 0; i < 480; i++) m.step(1 / 240);
    const sc = m.scene({}); assert.ok(sc.bodies.length >= 2, `${mode}: bodies`);
    assert.ok(m.measures().filter(x => !x.hidden).length >= 4, `${mode}: ≥4 visible measures`);
    assert.ok(Array.isArray(L.decor(p)) && L.decor(p).length > 3);
    assert.ok(L.equations(p, m).length >= 3);
    assert.ok(Array.isArray(m.energy()));
    for (const b of sc.bodies) assert.ok(['box', 'sphere', 'cylinder', 'cone', 'torus', 'plane'].includes(b.shape));
  }
  assert.ok(L.graph.choices.length >= 2);
  const m = L.create(defaults());
  for (const c of L.graph.choices) for (const k of c.y) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
  for (const k of L.recordKeys) assert.ok(m.measures().some(x => x.id === k), `record key ${k}`);
  assert.ok(Number.isFinite(L.evaluate(defaults()).answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in L.evaluate(defaults()).vars, `evaluate var ${k}`);
  for (const p of L.params) if (p.options) assert.ok(p.options.some(o => o.value === p.value));
});

test('Lab 19: photon energy, Kmax, stopping voltage and threshold match Einstein’s equation', () => {
  // sodium φ = 2.28 eV, λ = 300 nm: hf = 1239.842/300 = 4.132807 eV, Kmax = 1.852807 eV, λ0 = 1239.842/2.28 = 543.79 nm
  const { v } = run({ lambda: 300, phi: 2.28, I: 50, V: 0 });
  near(v.E, HC / 300, 1e-6); near(v.Kmax, HC / 300 - 2.28, 1e-6); near(v.Vstop, 1.852807, 1e-5);
  near(v.lam0, 543.791, 1e-5); near(v.f, 299792458 / 300e-9 / 1e14, 1e-9);
  // 50 % → 20 photons/s for 10 s = 200 photons, each above threshold → 200 electrons, all collected at V = 0
  assert.equal(v.Np, 200); assert.equal(v.Ne, 200); assert.equal(v.Nc, 200); near(v.rate, 20, 1e-6);
  near(L.evaluate({ lambda: 300, phi: 2.28 }).answer, v.Vstop, 1e-12);
  // zinc 4.33 eV, 200 nm: hf = 6.19921 eV, Vstop = 1.86921 V
  near(run({ lambda: 200, phi: 4.33 }).v.Vstop, HC / 200 - 4.33, 1e-6);
});

test('Lab 19: below threshold no electrons at any intensity; intensity scales the count, not Kmax', () => {
  for (const I of [25, 50, 100]) {
    const { v } = run({ lambda: 700, phi: 2.28, I });
    assert.equal(v.Ne, 0); assert.equal(v.Nc, 0); assert.equal(v.Kmax, 0); assert.ok(v.Np > 0);
  }
  assert.equal(L.evaluate({ lambda: 700, phi: 2.28 }).answer, 0);
  // just either side of λ0 = 543.79 nm
  assert.ok(run({ lambda: 540, phi: 2.28 }).v.Ne > 0);
  assert.equal(run({ lambda: 545, phi: 2.28 }).v.Ne, 0);
  const a = run({ lambda: 400, I: 25 }).v, b = run({ lambda: 400, I: 100 }).v;
  assert.equal(a.Ne, 100); assert.equal(b.Ne, 400); assert.equal(a.Kmax, b.Kmax);
});

test('Lab 19: retarding voltage — collected fraction 1 − V/Vstop, zero at and above Vstop', () => {
  // λ = 400 nm on sodium: Kmax = 3.099605 − 2.28 = 0.819605 eV
  const Vs = HC / 400 - 2.28;
  for (const V of [0.2, 0.4, 0.6]) {
    const { v } = run({ lambda: 400, phi: 2.28, I: 100, V });
    near(v.Nc / v.Ne, 1 - V / Vs, 0, 0.01); // evenly spread energies: 400 samples
  }
  assert.equal(run({ lambda: 400, I: 100, V: 0.85 }).v.Nc, 0);
  assert.ok(run({ lambda: 400, I: 100, V: 0.80 }).v.Nc > 0);
  // accelerating voltage collects everything (saturation current)
  const s = run({ lambda: 400, I: 100, V: -1 }).v; assert.equal(s.Nc, s.Ne);
});

test('Lab 19: electron flight obeys energy conservation K(x) = K0 − eV·x/d in the retarding field', () => {
  const m = L.create({ ...defaults(), lambda: 300, phi: 2.28, I: 100, V: 1.0 });
  const C0 = 1.6, GAP = 3;
  let checked = 0;
  for (let i = 0; i < 960; i++) {
    m.step(1 / 240);
    for (const e of m.electrons()) {
      if (e.tau <= 0) continue;
      near((e.v / C0) ** 2, e.K0 - 1.0 * e.x / GAP, 1e-9, 1e-9); checked++;
      // an electron that turns back never goes beyond x = d·K0/(eV)
      assert.ok(e.x <= GAP * e.K0 / 1.0 + 1e-9);
    }
  }
  assert.ok(checked > 1000);
});

test('Lab 19: hydrogen transitions give the Bohr wavelengths', () => {
  // 3 → 2: ΔE = 13.6057 (1/4 − 1/9) = 1.889681 eV → λ = 1239.842/1.889681 = 656.11 nm (Balmer Hα)
  const h = run({ mode: 'hydrogen', nU: 3, nL: 2 });
  near(h.v.dE, 1.889681, 1e-5); near(h.v.lamH, 656.11, 1e-4); assert.equal(h.v.n, 2);
  near(h.v.Eel, -13.6057 / 4, 1e-9); near(h.v.Eu - h.v.El, h.v.dE, 1e-12);
  // 2 → 1 (Lyman α): ΔE = 10.204275 eV → 121.502 nm; 4 → 2 (Hβ): 2.551069 eV → 486.01 nm
  near(run({ mode: 'hydrogen', nU: 2, nL: 1 }).v.lamH, HC / (13.6057 * 0.75), 1e-6);
  near(run({ mode: 'hydrogen', nU: 4, nL: 2 }).v.lamH, 486.01, 1e-4);
  // before the jump at t = 1 s no photon exists; upward "jump" settings emit nothing
  const early = run({ mode: 'hydrogen', nU: 3, nL: 2 }, 0.9).v; assert.equal(early.lamH, 0); assert.equal(early.n, 3);
  const none = run({ mode: 'hydrogen', nU: 3, nL: 4 }).v; assert.equal(none.lamH, 0); assert.equal(none.dE, 0);
  // energy bars: photon energy equals the level drop (J)
  const e = h.m.energy(); near(e[0].value, e[1].value, 1e-12); near(e[1].value, 1.889681 * 1.602176634e-19, 1e-5);
});

test('Lab 19: challenge checkers accept correct evidence and reject wrong evidence', () => {
  // 0: threshold bracket within 10 nm
  assert.ok(L.challenges[0]({ runs: [rec({ lambda: 540 }), rec({ lambda: 545 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ lambda: 520 }), rec({ lambda: 545 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ lambda: 540 }), rec({ lambda: 545, phi: 2.87 })] }));
  // 1: stopping voltage (Vstop = 0.8196 V at 400 nm on sodium)
  assert.ok(L.challenges[1]({ runs: [rec({ lambda: 400, V: 0.85 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ lambda: 400, V: 1.5 })] }));
  assert.ok(!L.challenges[1]({ runs: [rec({ lambda: 400, V: 0.8 })] }));
  // 2: intensity scaling
  assert.ok(L.challenges[2]({ runs: [rec({ lambda: 400, I: 25 }), rec({ lambda: 400, I: 75 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ lambda: 400, I: 25 }), rec({ lambda: 450, I: 75 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ lambda: 400, I: 50 }), rec({ lambda: 400, I: 75 })] }));
  // 3: red Balmer line
  assert.ok(L.challenges[3]({ runs: [rec({ mode: 'hydrogen', nU: 3, nL: 2 })] }));
  assert.ok(!L.challenges[3]({ runs: [rec({ mode: 'hydrogen', nU: 4, nL: 2 })] }));
});
