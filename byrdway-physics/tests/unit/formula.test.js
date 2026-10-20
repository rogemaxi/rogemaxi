// Formula Laboratory: every catalog formula must be dimensionally homogeneous, and solving for each variable
// in turn must reproduce the value that generated the data (round trip), checked against hand-picked cases.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { FORMULAS, findFormula } from '../../src/data/formulas.js';
import { solve, checkDimensions, defaultSample } from '../../src/engines/formula.js';

test(`all ${FORMULAS.length} formulas are dimensionally consistent`, () => {
  for (const f of FORMULAS) { const r = checkDimensions(f); assert.ok(r.ok, `${f.id}: ${r.reason || 'not homogeneous'}`); }
});

test('solve-for-any-variable round-trips every variable of every formula', () => {
  for (const f of FORMULAS) {
    const s = defaultSample(f);
    // make the sample consistent by solving the first variable from the others
    const [first, ...rest] = f.vars;
    s[first.s] = solve(f, first.s, Object.fromEntries(rest.map(v => [v.s, s[v.s]])))[0];
    for (const v of f.vars) {
      const known = Object.fromEntries(f.vars.filter(w => w !== v).map(w => [w.s, s[w.s]]));
      const roots = solve(f, v.s, known);
      assert.ok(roots.some(r => Math.abs(r - s[v.s]) <= 1e-6 * Math.abs(s[v.s])), `${f.id}: solving for ${v.s} gave ${roots} expected ${s[v.s]}`);
    }
  }
});

test('hand-checked cases', () => {
  const near = (a, b) => assert.ok(Math.abs(a - b) <= 1e-6 * Math.abs(b), `${a} vs ${b}`);
  near(solve(findFormula('kin3'), 'dx', { v: 0, v0: 20, a: -5 })[0], -40 / -1 * -1 * -1);   // 40 m stopping distance
  near(solve(findFormula('tpend'), 'L', { T: 2, g: 9.8 })[0], 9.8 / Math.PI ** 2);          // seconds pendulum ≈ 0.993 m
  const ang = solve(findFormula('range'), 'th', { R: 30, v0: 20, g: 9.8 }).filter(x => x > 0 && x < 90);
  assert.equal(ang.length, 2); near(ang[0] + ang[1], 90);                                   // complementary angles
  near(solve(findFormula('lens'), 'di', { f: 0.10, do: 0.30 })[0], 0.15);
  near(solve(findFormula('lens'), 'di', { f: 0.10, do: 0.05 }).find(x => x < 0), -0.10);    // virtual image
  assert.deepEqual(solve(findFormula('snell'), 't2', { n1: 1.5, t1: 60, n2: 1.0 }), []);    // total internal reflection
  near(solve(findFormula('ohm'), 'R', { V: 12, I: 0.5 })[0], 24);
});

test('the dimensional check rejects an inhomogeneous equation (guards against a vacuous test)', () => {
  const ke = findFormula('ke');
  const broken = { ...ke, id: 'broken', r: x => x.KE - 0.5 * x.m * x.v };   // ½mv has units of momentum, not energy
  assert.equal(checkDimensions(broken).ok, false);
});
