// Lab 9 (Orbital Mechanics) verification: the RK4 two-body model is compared with hand-derived Kepler results.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import L from '../../src/lab/labs/lab09.js';

const near = (a, b, rel = 1e-3, abs = 1e-9) => assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);
const defaults = () => Object.fromEntries(L.params.map(p => [p.id, p.value]));
const run = (params, tEnd = Infinity, dt = L.dt) => {
  const m = L.create({ ...defaults(), ...params });
  while (m.t < tEnd - 1e-12 && !m.done) m.step(dt);
  return { m, v: Object.fromEntries(m.measures().map(x => [x.id, x.value])) };
};
const rec = params => ({ params: { ...defaults(), ...params }, final: run(params).v });
// independent constants (hand values, not imported from the physics library)
const GM = 6.674e-11 * 5.972e24, Re = 6.371e6;

test('Lab 9: investigation structure (same assertions as labs.test.js)', () => {
  const T = L.text;
  for (const k of ['title', 'question', 'predict', 'guided', 'challenges', 'evaluate', 'honors', 'assumptions']) assert.ok(T[k], `text.${k}`);
  assert.equal(T.title, 'Orbital Mechanics Lab');
  assert.ok(T.guided.length >= 4 && T.challenges.length >= 3 && T.assumptions.length >= 4);
  assert.equal(T.challenges.length, L.challenges.length);
  assert.ok(T.predict.choices.length >= 2 && T.honors.prompt && T.honors.solution);
  assert.equal(L.unit, 8); assert.ok(L.sections.includes('8.7') && L.sections.includes('8.9'));
  const m = L.create(defaults());
  const sc = m.scene({}); assert.ok(sc.bodies.length && sc.vectors.length >= 2 && sc.bodies.some(b => b.trail));
  assert.ok(m.measures().filter(x => !x.hidden).length >= 4);
  assert.ok(L.graph.choices.length >= 2);
  for (const c of L.graph.choices) for (const k of [...c.y, c.x || 't']) assert.ok(m.measures().some(x => x.id === k), `graph key ${k}`);
  assert.ok(Array.isArray(L.decor(defaults())) && L.equations(defaults(), m).length >= 3);
  assert.ok(m.energy().length === 3);
  assert.ok(Number.isFinite(L.evaluate(defaults()).answer));
  for (const k of (T.evaluate.match(/\{(\w+)\}/g) || []).map(s => s.slice(1, -1))) assert.ok(k in L.evaluate(defaults()).vars, `evaluate var ${k}`);
  for (const k of L.recordKeys) assert.ok(m.measures().some(x => x.id === k), `record key ${k}`);
});

test('Lab 9: circular launch — constant radius and speed, period = 2π√(r³/GM)', () => {
  const r = Re + 1000e3, vc = Math.sqrt(GM / r), T = 2 * Math.PI * Math.sqrt(r ** 3 / GM); // 7.354 km/s, 6298 s
  near(vc, 7353.6, 1e-4); near(T / 60, 104.97, 1e-4);
  const { v } = run({ h: 1000, f: 1, phi: 0, M: 1 });
  near(v.v0, vc / 1000, 1e-9); near(v.v, vc / 1000, 1e-6); near(v.alt, 1000, 1e-6);
  near(v.rmin, r / 1000, 1e-6); near(v.rmax, r / 1000, 1e-6);
  assert.ok(v.ecc < 1e-6); near(v.revs, 2, 1e-9);
  near(v.Tm * 60, T, 1e-6); near(v.g, GM / r ** 2, 1e-6);
  near(v.Es, -GM / (2 * r) / 1e6, 1e-8);
  // planet mass ×4 → v_c ×2 and T ÷2 at the same radius
  const v4 = run({ h: 1000, f: 1, M: 4 }).v; near(v4.v0, 2 * vc / 1000, 1e-9); near(v4.Tm, v.Tm / 2, 1e-6);
});

test('Lab 9: elliptical launch matches vis-viva, apogee r₀f²/(2−f²), and Kepler’s third law', () => {
  const r0 = Re + 1000e3, f = 1.2, ra = r0 * f * f / (2 - f * f), a = (r0 + ra) / 2; // ra = 18 954 km
  const { m, v } = run({ h: 1000, f, phi: 0 }, Infinity);
  near(v.rmin, r0 / 1000, 1e-6); near(v.rmax, ra / 1000, 1e-5); near(v.amin, a / 1000, 1e-5);
  near(v.ecc, f * f - 1, 1e-5);                                       // e = f² − 1 for a perigee launch
  near(v.Tm * 60, 2 * Math.PI * Math.sqrt(a ** 3 / GM), 1e-5); near(v.kr, 1, 1e-5); near(v.Tk, v.Tm, 1e-5);
  near(v.v, f * Math.sqrt(GM / r0) / 1000, 1e-5);                       // back at perigee after two orbits
  assert.ok(m.done && v.escaped === 0 && v.crashed === 0);
  // an angled launch: speed at apogee from angular momentum r₀v₀cosφ = r_a v_a and energy
  const g = run({ h: 2000, f: 1.1, phi: 15 }).v;
  const r2 = Re + 2000e3, v0 = 1.1 * Math.sqrt(GM / r2), E = v0 * v0 / 2 - GM / r2, h2 = r2 * v0 * Math.cos(15 * Math.PI / 180);
  const disc = Math.sqrt(GM * GM + 2 * E * h2 * h2), rp = (-GM + disc) / (2 * E), rA = (-GM - disc) / (2 * E);
  near(g.rmax, rA / 1000, 1e-4); near(g.rmin, Math.min(r2, rp) / 1000, 1e-4); near(g.Tm * 60, 2 * Math.PI * Math.sqrt((-GM / (2 * E)) ** 3 / GM), 1e-5);
});

test('Lab 9: energy is conserved by the integrator; escape at √2·v_c; low launches crash', () => {
  const m = L.create({ ...defaults(), h: 500, f: 1.3, phi: 10 });
  const E0 = m.energy()[2].value; let worst = 0;
  while (!m.done) { m.step(L.dt); worst = Math.max(worst, Math.abs(m.energy()[2].value / E0 - 1)); }
  assert.ok(worst < 1e-6, `energy drift ${worst}`);
  const e = m.energy(); near(e[0].value + e[1].value, e[2].value, 1e-12);
  const esc = run({ h: 1000, f: 1.42 }).v;
  assert.equal(esc.escaped, 1); assert.ok(esc.Es >= 0); near(esc.vesc, Math.SQRT2 * Math.sqrt(GM / (Re + 1000e3)) / 1000, 1e-9);
  assert.ok(esc.rmax > 15 * Re / 1000 - 1);
  const bound = run({ h: 1000, f: 1.40 }).v; assert.equal(bound.escaped, 0); assert.ok(bound.Es < 0);
  // perigee r₀f²/(2−f²) below the surface → impact (f = 0.9: 5017 km < 6371 km); f = 0.97 clears it
  assert.equal(run({ h: 1000, f: 0.9 }).v.crashed, 1);
  const lo = run({ h: 1000, f: 0.97 }).v; assert.equal(lo.crashed, 0); near(lo.rmin, (Re + 1000e3) * 0.9409 / 1.0591 / 1000, 1e-5);
});

test('Lab 9: evaluation key agrees with the simulation', () => {
  for (const [h, M] of [[1000, 1], [3000, 2.5]]) {
    const r = Re + h * 1000;
    near(L.evaluate({ ...defaults(), h, M }).answer, 2 * Math.PI * Math.sqrt(r ** 3 / (GM * M)) / 60, 1e-9);
    near(run({ h, M, f: 1 }).v.Tm, L.evaluate({ ...defaults(), h, M }).answer, 1e-6);
  }
});

test('Lab 9: challenge checkers accept correct evidence and reject wrong evidence', () => {
  assert.ok(L.challenges[0]({ runs: [rec({ f: 1 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ f: 1.1 })] }));
  assert.ok(!L.challenges[0]({ runs: [rec({ f: 1, h: 1000 })].map(r => ({ ...r, final: { ...r.final, Tm: 0 } })) }));
  assert.ok(L.challenges[1]({ runs: [rec({ f: 1 }), rec({ f: 1.2 })] }));             // a ratio 1.79
  assert.ok(!L.challenges[1]({ runs: [rec({ f: 1 }), rec({ f: 1.05 })] }));           // a ratio too small
  assert.ok(!L.challenges[1]({ runs: [rec({ f: 1, M: 1 }), rec({ f: 1.2, M: 2 })] })); // different planets
  assert.ok(L.challenges[2]({ runs: [rec({ f: 1.43 })] }));
  assert.ok(!L.challenges[2]({ runs: [rec({ f: 1.6 })] }));                          // escapes, but 13% above v_esc
  assert.ok(!L.challenges[2]({ runs: [rec({ f: 1.40 })] }));                         // bound
});
