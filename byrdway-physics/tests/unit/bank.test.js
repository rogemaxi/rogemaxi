// Assessment bank and assessment algorithms: every numeric answer agrees with its calc, structure and coverage
// match the specification (250 items, every Core section covered, five levels, DOK 4 tasks with rubrics), and the
// adaptive diagnostic / plan / mastery / finals selection logic behaves as documented in docs/ASSESSMENT.md.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as P from '../../src/physics/index.js';
import { ITEMS, TASKS } from '../../src/data/bank/index.js';
import { readJSON } from './helpers.js';

const resources = readJSON('src/data/resources.json');
const evalCalc = e => Function('P', 'Math', `"use strict"; return (${e});`)(P, Math);

test('bank: 250 unique items, 20 tasks, answers verified against calc', () => {
  assert.equal(ITEMS.length, 250); assert.equal(TASKS.length, 20);
  assert.equal(new Set(ITEMS.map(i => i.id)).size, 250);
  assert.equal(new Set(ITEMS.map(i => i.q.trim().toLowerCase())).size, 250, 'duplicate question text');
  for (const it of ITEMS) {
    assert.ok(it.q && it.solution && it.level >= 1 && it.level <= 5 && it.dok >= 1 && it.dok <= 3, it.id);
    assert.ok(resources.sections.some(s => s.id === it.section && s.unit === it.unit), `${it.id}: section ${it.section} not in unit ${it.unit}`);
    if (it.kind === 'num') { const v = evalCalc(it.calc); assert.ok(Math.abs(v - it.answer) <= 0.01 * Math.abs(it.answer), `${it.id}: ${it.answer} vs ${v}`); }
    else { assert.equal(it.kind, 'mc'); assert.ok(Number.isInteger(it.correct) && it.correct < it.choices.length, it.id); }
  }
});

test('bank: every Core section is assessed; every level is populated in every unit', () => {
  for (const s of resources.sections.filter(s => s.pathway === 'Core')) assert.ok(ITEMS.some(i => i.section === s.id), `no item for ${s.id}`);
  for (let u = 1; u <= 20; u++) for (let L = 1; L <= 5; L++) assert.ok(ITEMS.some(i => i.unit === u && i.level === L), `unit ${u} level ${L}`);
});

test('tasks: one DOK 4 task per unit, each with ≥ 4 rubric criteria at 4 levels', () => {
  for (let u = 1; u <= 20; u++) {
    const t = TASKS.find(x => x.unit === u); assert.ok(t, `task for unit ${u}`);
    assert.ok(t.scenario && t.tasks.length >= 3 && t.exemplar);
    assert.ok(t.rubric.length >= 4 && t.rubric.every(r => r.length === 5), `${t.id} rubric`);
  }
});

// ---- algorithms ----
import { abilityAfter, nextDiagnosticItem, buildPlan, levelItems, finalItems, advancedUnits } from '../../src/engines/assess.js';
import { loadCurriculum } from './helpers.js';
const cur = await loadCurriculum();
const UNITS = resources.units.map(u => ({ ...u, sections: resources.sections.filter(s => s.unit === u.num).map(s => ({ ...s, content: cur.sections[s.id] || null })) }));
const SECTIONS = UNITS.flatMap(u => u.sections);
const CTX = { items: ITEMS, units: UNITS, sections: SECTIONS };

test('diagnostic: 20 questions, one per unit, harder after correct answers and easier after misses', () => {
  const order = UNITS.map(u => u.num);
  const sim = answerFn => { const h = []; let it; while ((it = nextDiagnosticItem(h, order, ITEMS))) h.push({ item: it, ok: answerFn(it) }); return h; };
  const allRight = sim(() => true), allWrong = sim(() => false);
  assert.equal(allRight.length, 20); assert.deepEqual(allRight.map(h => h.item.unit), order);
  assert.equal(abilityAfter(allRight), 5); assert.equal(abilityAfter(allWrong), 1);
  const mean = h => h.slice(10).reduce((s, x) => s + x.item.level, 0) / 10;
  assert.ok(mean(allRight) >= 4.5 && mean(allWrong) <= 1.5, `levels ${mean(allRight)} / ${mean(allWrong)}`);
  // a student who knows only Level ≤ 2 material settles around levels 2–3
  const mid = sim(it => it.level <= 2); assert.ok(abilityAfter(mid) >= 1.5 && abilityAfter(mid) <= 3.5, String(abilityAfter(mid)));
});

test('plan: misses produce weak units, the missed sections and their stated prerequisites, in course order', () => {
  const order = UNITS.map(u => u.num), h = [];
  let it; while ((it = nextDiagnosticItem(h, order, ITEMS))) h.push({ item: it, ok: it.unit !== 5 && it.unit !== 8 });
  const p = buildPlan(h, CTX);
  assert.deepEqual(p.weakUnits, [5, 8]); assert.equal(p.strengths.length, 18);
  const missed = h.filter(x => !x.ok).map(x => x.item.section);
  for (const s of missed) assert.ok(p.recommend.includes(s));
  const idx = p.recommend.map(id => SECTIONS.findIndex(s => s.id === id)); assert.deepEqual(idx, [...idx].sort((a, b) => a - b));
});

test('mastery levels and finals draw the documented items', () => {
  const adv = advancedUnits(UNITS); assert.deepEqual([...adv], [19]);
  for (let n = 1; n <= 5; n++) {
    const xs = levelItems(n, CTX, 42); assert.equal(xs.length, 12); assert.ok(xs.every(x => x.level === n));
    if (n < 5) assert.ok(xs.every(x => x.unit !== 19)); assert.ok(new Set(xs.map(x => x.unit)).size >= 10, 'spread across units');
  }
  const core = finalItems('core', CTX, 7), hon = finalItems('honors', CTX, 7);
  assert.equal(core.length, 38); assert.ok(core.every(x => !x.honors && x.level <= 4 && x.unit !== 19));
  assert.equal(hon.length, 38); assert.ok(hon.every(x => x.level >= 3 && x.unit !== 19));
  assert.ok(hon.filter(x => x.honors).length >= 18, 'honors final emphasizes Honors items');
});
