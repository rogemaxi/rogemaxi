// Error Detective answer analyzer: given the correct value and a student's wrong value, test a list of
// common error transformations. Returns the matching pattern keys (UI strings "err.<key>"), most likely first.
const PATTERNS = [
  { key: 'sign', f: a => -a },
  { key: 'k1000', f: a => a * 1000 }, { key: 'k1000', f: a => a / 1000 },
  { key: 'k100', f: a => a * 100 }, { key: 'k100', f: a => a / 100 },
  { key: 'g', f: a => a * 9.8 }, { key: 'g', f: a => a / 9.8 },
  { key: 'half', f: a => a * 2 }, { key: 'half', f: a => a / 2 },
  { key: 'square', f: a => a * a }, { key: 'square', f: a => Math.sqrt(Math.abs(a)) },
  { key: 'kmh', f: a => a * 3.6 }, { key: 'kmh', f: a => a / 3.6 },
  { key: 'time60', f: a => a * 60 }, { key: 'time60', f: a => a / 60 },
  { key: 'time3600', f: a => a * 3600 }, { key: 'time3600', f: a => a / 3600 },
  { key: 'k1e6', f: a => a * 1e6 }, { key: 'k1e6', f: a => a / 1e6 },
  { key: 'k1e9', f: a => a * 1e9 }, { key: 'k1e9', f: a => a / 1e9 },
  { key: 'invert', f: a => 1 / a },
  { key: 'pi', f: a => a * Math.PI }, { key: 'pi', f: a => a / Math.PI },
  { key: 'twopi', f: a => a * 2 * Math.PI }, { key: 'twopi', f: a => a / (2 * Math.PI) },
];

export function diagnose(correct, value, { extra = [] } = {}) {
  if (!Number.isFinite(correct) || !Number.isFinite(value) || correct === 0) return [];
  const hits = [];
  for (const p of [...extra, ...PATTERNS]) {
    const cand = p.f(correct);
    if (!Number.isFinite(cand) || cand === 0) continue;
    if (Math.abs(value - cand) / Math.abs(cand) <= 0.02 && !hits.includes(p.key)) hits.push(p.key);
  }
  // sign combined with a scale error
  if (!hits.length) for (const p of PATTERNS) {
    const cand = -p.f(correct);
    if (Number.isFinite(cand) && cand !== 0 && Math.abs(value - cand) / Math.abs(cand) <= 0.02) { hits.push('sign', p.key); break; }
  }
  return hits;
}
export const ERROR_KEYS = [...new Set(PATTERNS.map(p => p.key))];
