// Every translatable content object in the app, with its localization scope and report group.
import { readFileSync, existsSync } from 'node:fs';
const root = new URL('../', import.meta.url);
const load = async p => (existsSync(new URL(p, root)) ? (await import(new URL(p, root))).default : null);

export async function allScopes() {
  const res = JSON.parse(readFileSync(new URL('src/data/resources.json', root), 'utf8'));
  const out = [];
  for (let n = 1; n <= 20; n++) {
    const u = await load(`src/data/curriculum/u${String(n).padStart(2, '0')}.js`);
    const ru = res.units.find(x => x.num === n);
    out.push({ scope: 'unit.' + n, group: 'units', obj: { x: ru.title, bridges: u.bridges || [], blueprint: u.blueprint || [] } });
    for (const s of res.sections.filter(x => x.unit === n)) {
      const c = u.sections?.[s.id];
      out.push({ scope: s.id, group: 'lessons', obj: { title: s.topic, ...(c || {}) } });
    }
  }
  const labs = await load('src/lab/labs/index.js').catch(() => null);
  const mod = await import(new URL('src/lab/labs/index.js', root));
  for (const l of mod.LABS) out.push({ scope: 'lab.' + l.num, group: 'labs', obj: l.text });
  for (const [file, scope, group] of [['src/data/bank/index.js', 'bank', 'assessment'], ['src/data/engines/index.js', 'engines', 'engines'], ['src/data/reference/index.js', 'ref', 'reference']]) {
    if (!existsSync(new URL(file, root))) continue;
    const m = await import(new URL(file, root));
    for (const [k, v] of Object.entries(m.TRANSLATABLE || {})) out.push({ scope: `${scope}.${k}`, group, obj: v });
  }
  return out;
}
