// Curriculum alignment integrity: every mapped code exists in the official source list saved in sources/benchmarks/,
// every mapped lesson exists, and the reported coverage gaps are exactly the known, documented ones (so a silent change
// in either the mapping or the sources is caught). Alignment correctness itself requires human review (H3–H7).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { readJSON } from './helpers.js';
import { P1, P2, CM, CE } from '../../src/data/standards/ap_alignment.js';

const res = readJSON('src/data/resources.json');
const ap = readJSON('sources/benchmarks/ap_physics.json');
const intlSrc = readFileSync(new URL('../../src/data/standards/intl.js', import.meta.url), 'utf8').replace(/^import .*$/mg, '').replace(/export const INTL[\s\S]*$/, '');
const { CAIE_MAP, IB_MAP, NGSS_MAP } = await import('data:text/javascript,' + encodeURIComponent(intlSrc));
const sub = c => c.includes('.');
const layers = [
  ['AP1', P1, ap.courses.find(c => c.id === 'AP1').items.map(i => i.code), []],
  ['AP2', P2, ap.courses.find(c => c.id === 'AP2').items.map(i => i.code), []],
  ['APCM', CM, ap.courses.find(c => c.id === 'APCM').items.map(i => i.code), []],
  ['APCE', CE, ap.courses.find(c => c.id === 'APCE').items.map(i => i.code), ['8.4', '8.5', '8.6', '12.4', '13.6']],
  ['CAIE', CAIE_MAP, readJSON('sources/benchmarks/cambridge_9702.json').items.map(i => i.code).filter(sub), ['10.3', '11.2', '21.2', '24.3', '25.1']],
  ['IB', IB_MAP, readJSON('sources/benchmarks/ib_dp_physics.json').items.map(i => i.code).filter(sub), ['B.2']],
  ['NGSS', NGSS_MAP, readJSON('sources/benchmarks/ngss_hs.json').items.map(i => i.code), ['HS-PS2-6', 'HS-PS4-2', 'HS-ESS1-6']],
];

test('official source lists have the expected sizes', () => {
  assert.deepEqual(ap.courses.map(c => c.items.length), [43, 46, 41, 31]);
  assert.equal(layers[4][2].length, 76); assert.equal(layers[5][2].length, 24); assert.equal(layers[6][2].length, 26);
});

for (const [name, map, codes, knownGaps] of layers) test(`${name}: mapped codes and lessons are real; gaps are exactly the documented ones`, () => {
  for (const [id, cs] of Object.entries(map)) {
    assert.ok(res.sections.some(s => s.id === id), `${name}: lesson ${id} does not exist`);
    for (const c of cs) assert.ok(codes.includes(c), `${name}: ${id} → unknown code ${c}`);
  }
  const used = new Set(Object.values(map).flat());
  assert.deepEqual(codes.filter(c => !used.has(c)), knownGaps);
});

test('all 170 lessons are retained; the only lessons without a content-topic alignment are the documented practice/math/enrichment ones', () => {
  assert.equal(res.sections.length, 170);
  const aligned = new Set(layers.flatMap(([, m]) => Object.keys(m)));
  // 1.1–1.3, 1.8: nature of science and practices (AP science practices, IB tools/inquiry, Cambridge practical skills, NGSS SEPs);
  // 2.1–2.3: mathematical tools; 11.7 viscosity (beyond these syllabi); 19.5, 19.7: general relativity and galaxies (enrichment).
  assert.deepEqual(res.sections.filter(s => !aligned.has(s.id)).map(s => s.id), ['1.1', '1.2', '1.3', '1.8', '2.1', '2.2', '2.3', '11.7', '19.5', '19.7']);
});
