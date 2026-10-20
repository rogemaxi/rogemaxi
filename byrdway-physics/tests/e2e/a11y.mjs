// Automated accessibility audit (axe-core 4.10, WCAG 2.1 A/AA rules) of representative routes in the built file.
// Usage: node tests/e2e/a11y.mjs  → docs/evidence/a11y-results.json. Automated checks cover only part of WCAG;
// manual keyboard and screen-reader review is recorded separately in docs/ACCESSIBILITY_PERFORMANCE.md.
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
const root = new URL('../../', import.meta.url);
const FILE = new URL('dist/ByrdWay_Physics_I_Honors.html', root).href;
const AXE = readFileSync(new URL('node_modules/axe-core/axe.min.js', root), 'utf8');
const ROUTES = ['#/cover', '#/home', '#/units', '#/unit/6', '#/section/6.6', '#/section/16.5', '#/lab/5', '#/lab/8', '#/labs', '#/engines', '#/engine/flash/3', '#/engine/formula', '#/engine/tutor/12.3', '#/engine/detective', '#/assess', '#/diagnostic', '#/mastery/4', '#/reference/standards', '#/reference/glossary', '#/videos', '#/settings'];
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: { width: 1366, height: 900 } });
const out = [];
for (const lang of ['en', 'ar']) for (const r of ROUTES) {
  await p.goto(FILE + '#/cover');
  await p.evaluate(l => { const k = 'byrdway-physics-v1'; const s = JSON.parse(localStorage.getItem(k) || '{"schema":1,"sections":{},"settings":{}}'); s.settings.lang = l; localStorage.setItem(k, JSON.stringify(s)); }, lang);
  await p.goto(FILE + r); await p.reload(); await p.waitForTimeout(500);
  await p.addScriptTag({ content: AXE });
  const res = await p.evaluate(async () => (await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })).violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length, help: v.help, sample: v.nodes.slice(0, 2).map(n => n.target.join(' ')) })));
  out.push({ lang, route: r, violations: res });
  console.log(lang, r, res.length ? res.map(v => `${v.id}(${v.impact},${v.n}) ${v.sample.join(' | ')}`).join('; ') : 'clean');
}
await b.close();
writeFileSync(new URL('docs/evidence/a11y-results.json', root), JSON.stringify({ at: new Date().toISOString(), tool: 'axe-core 4.10.2', results: out }, null, 1));
