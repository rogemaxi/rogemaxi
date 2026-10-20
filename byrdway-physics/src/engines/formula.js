// Formula Laboratory solver: solve a catalog formula (src/data/formulas.js) for any one variable by
// bracketing sign changes of its residual and bisecting, plus an automatic dimensional-consistency check.
const BASE = ['kg', 'm', 's', 'A', 'K', 'mol'];

function bisect(f, a, b, fa) {
  for (let i = 0; i < 200; i++) {
    const m = 0.5 * (a + b), fm = f(m);
    if (!Number.isFinite(fm)) return NaN;
    if (fm === 0 || Math.abs(b - a) <= 1e-13 * Math.max(Math.abs(m), 1e-300)) return m;
    if (Math.sign(fm) === Math.sign(fa)) { a = m; fa = fm; } else b = m;
  }
  return 0.5 * (a + b);
}

// Candidate grid: angles scan −180…180°, other quantities scan magnitudes 1e−40…1e40 (both signs unless pos).
function grid(spec) {
  if (spec.angle) return Array.from({ length: 721 }, (_, i) => -180 + i * 0.5);
  const pos = []; for (let e = -40; e <= 40; e += 0.05) pos.push(10 ** e);
  return spec.pos ? pos : [...pos.slice().reverse().map(x => -x), ...pos];
}

// Returns all distinct roots found (sorted: positive/physical first), or [] when none exists.
export function solve(formula, target, known) {
  const spec = formula.vars.find(v => v.s === target);
  const f = x => formula.r({ ...known, [target]: x });
  const xs = grid(spec), roots = [];
  let px = xs[0], pf = f(px);
  for (let i = 1; i < xs.length; i++) {
    const x = xs[i], fx = f(x);
    if (Number.isFinite(pf) && Number.isFinite(fx)) {
      if (fx === 0) roots.push(x);
      else if (Math.sign(fx) !== Math.sign(pf) && pf !== 0) {
        // reject poles: a true root makes |f| small, a pole makes it blow up
        const r = bisect(f, px, x, pf), fr = f(r);
        if (Number.isFinite(fr) && Math.abs(fr) <= 1e-6 * Math.max(Math.abs(pf), Math.abs(fx), 1e-300)) roots.push(r);
      }
    }
    px = x; pf = fx;
  }
  const uniq = [];
  for (const r of roots) if (!uniq.some(u => Math.abs(u - r) <= 1e-9 * Math.max(Math.abs(r), 1e-300))) uniq.push(r);
  return uniq.sort((a, b) => (spec.angle ? Math.abs(a) - Math.abs(b) || b - a : (b > 0) - (a > 0) || Math.abs(a) - Math.abs(b)));
}

export const dimString = dim => {
  const SUP = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' };
  const parts = BASE.map((b, i) => (dim[i] ? b + (dim[i] === 1 ? '' : String(dim[i]).split('').map(c => SUP[c]).join('')) : '')).filter(Boolean);
  return parts.length ? parts.join('·') : '1 (dimensionless)';
};

// Dimensional homogeneity test: rescale every base unit by an arbitrary factor; each variable's value scales by
// Π factorᵢ^dimᵢ. A homogeneous equation stays satisfied: re-solving for the first variable must give the scaled value.
export function checkDimensions(formula, sample = defaultSample(formula)) {
  const [first, ...rest] = formula.vars;
  const known = Object.fromEntries(rest.map(v => [v.s, sample[v.s]]));
  const base = solve(formula, first.s, known)[0];
  if (!Number.isFinite(base)) return { ok: false, reason: 'no solution at sample point' };
  const fac = [1.7, 2.3, 0.6, 3.1, 1.9, 2.7];
  const scale = d => d.reduce((p, e, i) => p * fac[i] ** e, 1);
  const knownS = Object.fromEntries(rest.map(v => [v.s, sample[v.s] * (v.angle ? 1 : scale(v.dim))]));
  const got = solve(formula, first.s, knownS).find(x => Math.abs(x / (base * scale(first.dim)) - 1) < 1e-6);
  return { ok: got != null, lhs: dimString(first.dim) };
}

export function defaultSample(formula) {
  // A sample point at which the first variable has a solution (tries rotations of a small value set).
  const vals = [2.0, 3.0, 5.0, 1.5, 4.0, 2.5];
  const [first, ...rest] = formula.vars;
  for (let rot = 0; rot < vals.length; rot++) {
    const s = {}; let k = rot;
    for (const v of formula.vars) s[v.s] = v.def ?? (v.angle ? 30 : vals[k++ % vals.length]);
    if (formula.vars.some(v => v.s === 'c') && 'v' in s) s.v = 0.6 * s.c;   // sub-light speeds
    if (solve(formula, first.s, Object.fromEntries(rest.map(v => [v.s, s[v.s]]))).length) return s;
  }
  throw new Error(`${formula.id}: no solvable sample point`);
}
