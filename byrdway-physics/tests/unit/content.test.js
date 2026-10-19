// Curriculum integrity tests: every authored section must contain all required instructional components,
// every numeric answer must agree with an independent restatement (`calc`) evaluated over the physics library,
// and no paragraph may be duplicated across sections (guards against generic filler).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as P from '../../src/physics/index.js';
import { loadCurriculum } from './helpers.js';

const { units, sections, resources } = await loadCurriculum();
const DIAGRAMS = ['fbd', 'plot', 'vectors', 'incline', 'motion', 'wave', 'lens', 'refract', 'circuit', 'field', 'orbit', 'spring', 'pendulum', 'bars', 'flow', 'axis', 'trajectory'];
const REQUIRED = ['objectives', 'prereqs', 'intro', 'observe', 'predict', 'explain', 'vocab', 'formulas', 'units', 'example', 'guided', 'practice', 'misconceptions', 'visual', 'investigate', 'mastery', 'honors'];
const evalCalc = expr => Function('P', 'Math', `"use strict"; return (${expr});`)(P, Math);
const rel = (a, b) => (b === 0 ? Math.abs(a) : Math.abs(a - b) / Math.abs(b));

test('skeleton matches the owner’s Video Link Library (20 units, 170 sections)', () => {
  assert.equal(resources.sections.length, 170);
  assert.equal(new Set(resources.sections.map(s => s.id)).size, 170);
  assert.equal(units.length, 20);
});

const authored = Object.entries(sections);
test(`authored sections are complete (${authored.length} of 170 authored)`, () => {
  for (const [id, c] of authored) {
    assert.ok(resources.sections.some(s => s.id === id), `${id} is not a section in the library`);
    for (const k of REQUIRED) assert.ok(c[k] != null && (!Array.isArray(c[k]) || c[k].length), `${id}: missing ${k}`);
    assert.ok(c.objectives.length >= 3, `${id}: ≥3 objectives`);
    assert.ok(c.explain.length >= 3, `${id}: ≥3 explanation paragraphs`);
    assert.ok(c.vocab.length >= 3, `${id}: ≥3 vocabulary terms`);
    assert.ok(c.example.steps.length >= 3, `${id}: worked example needs ≥3 steps`);
    assert.ok(c.guided.length >= 2, `${id}: ≥2 guided items`);
    assert.ok(c.practice.length >= 3, `${id}: ≥3 independent items`);
    assert.ok(c.misconceptions.length >= 2, `${id}: ≥2 misconceptions`);
    assert.ok(c.mastery.length >= 3, `${id}: ≥3 mastery criteria`);
    assert.ok(DIAGRAMS.includes(c.visual.kind), `${id}: unknown diagram ${c.visual.kind}`);
    assert.ok(Number.isInteger(c.predict.correct) && c.predict.correct < c.predict.choices.length, `${id}: predict.correct`);
    assert.ok(c.honors.prompt && c.honors.solution, `${id}: honors prompt + solution`);
    for (const m of c.misconceptions) assert.ok(m.wrong && m.right && m.feedback, `${id}: misconception fields`);
    for (const f of c.formulas) assert.ok(f.eq && f.vars?.length && f.when, `${id}: formula fields`);
  }
});

test('every numeric answer matches its independent calc (≤1%), every MC key is valid', () => {
  let n = 0;
  for (const [id, c] of authored) {
    const items = [...c.guided, ...c.practice];
    const ids = new Set();
    for (const q of items) {
      assert.ok(q.id && !ids.has(q.id), `${id}: duplicate or missing item id ${q.id}`); ids.add(q.id);
      assert.ok(q.q && q.solution, `${id}/${q.id}: question and solution`);
      if (q.kind === 'num') {
        assert.ok(typeof q.answer === 'number' && Number.isFinite(q.answer), `${id}/${q.id}: numeric answer`);
        assert.ok(q.calc, `${id}/${q.id}: numeric items need a calc restatement`);
        const v = evalCalc(q.calc);
        assert.ok(rel(v, q.answer) <= (q.calcTol ?? 0.01), `${id}/${q.id}: stated ${q.answer} but calc gives ${v}`);
        n++;
      } else if (q.kind === 'mc') {
        assert.ok(Number.isInteger(q.correct) && q.correct >= 0 && q.correct < q.choices.length, `${id}/${q.id}: mc key`);
      } else assert.equal(q.kind, 'self', `${id}/${q.id}: kind`);
    }
    if (c.honors.calc) c.honors.calc.forEach((e, i) => { const v = evalCalc(e); assert.ok(rel(v, c.honors.answers[i]) <= 0.01, `${id} honors[${i}]: ${c.honors.answers[i]} vs ${v}`); n++; });
  }
  assert.ok(n >= authored.length * 2);
});

test('no explanation paragraph or worked example is duplicated across sections', () => {
  const seen = new Map();
  for (const [id, c] of authored) for (const p of [c.intro, c.observe, ...c.explain, c.example.problem]) {
    const k = p.trim().toLowerCase();
    assert.ok(!seen.has(k), `${id} repeats text from ${seen.get(k)}: "${p.slice(0, 60)}…"`);
    seen.set(k, id);
  }
});
