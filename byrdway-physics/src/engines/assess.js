// Pure assessment logic (no DOM, no JSON imports) so it can be unit-tested. Documented in docs/ASSESSMENT.md.
// `ctx` = { items, units, sections } where units are [{num, sections:[{id, pathway, content}]}].
export const shuffle = (arr, seed = Date.now()) => {
  const a = arr.slice(); let s = Math.abs(Math.floor(seed)) % 2147483647 || 1;
  for (let i = a.length - 1; i > 0; i--) { s = (s * 16807) % 2147483647; const j = s % (i + 1); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
};
export const advancedUnits = units => new Set(units.filter(u => u.sections.every(s => s.pathway === 'Advanced')).map(u => u.num));

// Ability estimate after a sequence of answers: θ starts at 2, moves ±step, step = max(0.4, 0.9/√(k+1)), clamped to [1, 5].
export function abilityAfter(history) {
  let theta = 2;
  history.forEach((h, i) => { const step = Math.max(0.4, 0.9 / Math.sqrt(i + 1)); theta = Math.min(5, Math.max(1, theta + (h.ok ? step : -step))); });
  return theta;
}
// One item per unit, in `order`; the unused item of that unit whose level is nearest θ (ties → lower id).
export function nextDiagnosticItem(history, order, items) {
  if (history.length >= order.length) return null;
  const theta = abilityAfter(history), u = order[history.length], used = new Set(history.map(h => h.item.id));
  const pool = items.filter(it => it.unit === u && !used.has(it.id));
  pool.sort((a, b) => Math.abs(a.level - theta) - Math.abs(b.level - theta) || a.id.localeCompare(b.id));
  return pool[0] || null;
}
export function buildPlan(history, { units, sections }) {
  const findSection = id => sections.find(s => s.id === id);
  const byUnit = {};
  for (const h of history) (byUnit[h.item.unit] ||= []).push(h);
  const strengths = [], weakUnits = [];
  for (const [u, hs] of Object.entries(byUnit)) (hs.every(h => h.ok) ? strengths : weakUnits).push(+u);
  const recommend = [];
  for (const h of history.filter(h => !h.ok)) {
    const sec = findSection(h.item.section);
    for (const p of sec?.content?.prereqs || []) for (const m of String(p).matchAll(/(\d+\.\d+)/g)) if (findSection(m[1]) && !recommend.includes(m[1])) recommend.push(m[1]);
    if (!recommend.includes(h.item.section)) recommend.push(h.item.section);
  }
  recommend.sort((a, b) => sections.findIndex(s => s.id === a) - sections.findIndex(s => s.id === b));
  const gaps = [...new Set(history.filter(h => !h.ok && h.item.prereq).map(h => h.item.prereq))];
  strengths.sort((a, b) => a - b); weakUnits.sort((a, b) => a - b);
  return { strengths, weakUnits, weak: weakUnits.map(u => `${u}. ${units.find(x => x.num === u).title}`), recommend, gaps };
}
// Mastery level: 12 items of exactly that level, spread round-robin across units (Unit 19 enrichment only at Level 5).
export function levelItems(n, { items, units }, seed = Date.now()) {
  const adv = advancedUnits(units);
  const byUnit = {};
  for (const it of shuffle(items.filter(it => it.level === n && (n === 5 || !adv.has(it.unit))), seed)) (byUnit[it.unit] ||= []).push(it);
  const out = [], us = shuffle(Object.keys(byUnit), seed + 1);
  for (let round = 0; out.length < 12 && round < 6; round++) for (const u of us) { const it = byUnit[u][round]; if (it && out.length < 12) out.push(it); }
  return out;
}
// Finals: two items per Physics I unit (enrichment units excluded). Core: levels 1–4, no Honors items.
// Honors: levels 3–5, Honors items first, then highest level.
export function finalItems(kind, { items, units }, seed = Date.now()) {
  const adv = advancedUnits(units), out = [];
  for (const u of units.filter(u => !adv.has(u.num))) {
    const pool = items.filter(it => it.unit === u.num && (kind === 'core' ? !it.honors && it.level <= 4 : it.level >= 3));
    const pick = shuffle(pool, seed + u.num);
    if (kind === 'honors') pick.sort((a, b) => (b.honors - a.honors) || (b.level - a.level));
    out.push(...pick.slice(0, 2));
  }
  return shuffle(out, seed);
}
