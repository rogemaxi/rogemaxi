// Test helpers: load curriculum and JSON data without a bundler.
import { readFileSync } from 'node:fs';

export const root = new URL('../../', import.meta.url);
export const readJSON = rel => JSON.parse(readFileSync(new URL(rel, root), 'utf8'));

export async function loadCurriculum() {
  const resources = readJSON('src/data/resources.json');
  const units = [];
  const sections = {};
  for (let n = 1; n <= 20; n++) {
    const mod = (await import(new URL(`src/data/curriculum/u${String(n).padStart(2, '0')}.js`, root))).default;
    units.push(mod);
    Object.assign(sections, mod.sections || {});
  }
  return { units, sections, resources };
}
