// Localization integrity: UI parity and placeholders; content packs reference real keys and preserve every
// number and placeholder of the English source (a translated physics answer must not change a value).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readJSON } from './helpers.js';
import { contentKeys } from '../../src/app/i18nkeys.js';
import { allScopes } from '../../tools/scopes.mjs';

const LANGS = ['es', 'fr', 'ht', 'pt', 'ar', 'zh', 'hi', 'bn', 'vi', 'ko', 'ja'];
const en = readJSON('src/data/i18n/ui/en.json');
const ph = s => [...String(s).matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort().join(',');
// Numbers with optional decimal part; a decimal comma is normalized to a point. Bengali/Hindi keep ASCII digits in our packs.
const numList = s => [...String(s).replace(/(\d),(\d)/g, '$1.$2').matchAll(/\d+(?:\.\d+)?/g)].map(m => m[0]);
// Every number in the English source must appear in the translation (as a multiset). Extra digits are allowed:
// CJK languages write words such as "twice" or "second law" with digits (2倍, 第 2 法則).
const missingNums = (e, v) => { const pool = numList(v); return numList(e).filter(n => { const i = pool.indexOf(n); if (i < 0) return true; pool.splice(i, 1); return false; }); };

test('every UI pack has exactly the English keys with matching placeholders', () => {
  for (const l of LANGS) {
    const d = readJSON(`src/data/i18n/ui/${l}.json`);
    const missing = Object.keys(en).filter(k => !(k in d));
    const extra = Object.keys(d).filter(k => !(k in en));
    assert.deepEqual(missing, [], `${l}: missing UI keys`);
    assert.deepEqual(extra, [], `${l}: unknown UI keys`);
    for (const k of Object.keys(en)) assert.equal(ph(d[k]), ph(en[k]), `${l}/${k}: placeholders differ`);
  }
});

const scopes = await allScopes();
const source = new Map(scopes.flatMap(s => contentKeys(s.scope, s.obj)));

test('content packs only contain current keys, keep placeholders, and preserve every number of the source', () => {
  const bad = [];
  for (const l of LANGS) {
    const pack = readJSON(`src/data/i18n/content/${l}.json`);
    for (const [k, v] of Object.entries(pack)) {
      if (!source.has(k)) { bad.push(`${l}: stale key ${k}`); continue; }
      const e = source.get(k);
      if (ph(v) !== ph(e)) bad.push(`${l}/${k}: placeholders differ`);
      const lost = missingNums(e, v); if (lost.length) bad.push(`${l}/${k}: numbers missing from translation: ${lost.join(' ')}`);
    }
  }
  assert.deepEqual(bad, []);
});

test('the Newton 2nd-law reference slice (5.3 + Lab 5) is fully translated in all 11 languages', () => {
  const slice = [...source.keys()].filter(k => k.startsWith('5.3|') || k.startsWith('lab.5|'));
  assert.ok(slice.length > 150);
  for (const l of LANGS) {
    const pack = readJSON(`src/data/i18n/content/${l}.json`);
    const missing = slice.filter(k => !pack[k]);
    assert.deepEqual(missing, [], `${l}: untranslated slice keys`);
  }
});
