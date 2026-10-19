// End-to-end browser tests against the BUILT standalone file (dist/), opened from disk exactly as a student would.
// Usage: node tests/e2e/run.mjs [suite…]   Results are written to docs/evidence/e2e-results.json.
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'node:fs';
import { SUITES } from './suites.mjs';

const root = new URL('../../', import.meta.url);
const FILE = new URL('dist/ByrdWay_Physics_I_Honors.html', root).href;
const only = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const results = [];
let failed = 0;

for (const [name, fn] of Object.entries(SUITES)) {
  if (only.length && !only.some(o => name.startsWith(o))) continue;
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const t0 = Date.now();
  const checks = [];
  const expect = (cond, msg) => { checks.push({ ok: !!cond, msg }); if (!cond) throw new Error('assertion failed: ' + msg); };
  let status = 'pass', error = null;
  try {
    await fn({ page, ctx, FILE, expect, goto: async (hash, lang) => {
      if (lang) await page.addInitScript(l => { const k = 'byrdway-physics-v1'; const s = JSON.parse(localStorage.getItem(k) || '{"schema":1,"sections":{},"settings":{}}'); s.settings = { ...(s.settings || {}), lang: l }; localStorage.setItem(k, JSON.stringify(s)); }, lang);
      await page.goto(FILE + hash); await page.waitForTimeout(700);
    } });
    if (errors.length) throw new Error('page errors: ' + errors.join(' | '));
  } catch (e) { status = 'fail'; error = e.message; failed++; }
  results.push({ name, status, ms: Date.now() - t0, checks: checks.length, error });
  console.log(`${status === 'pass' ? 'ok  ' : 'FAIL'} ${name} (${checks.length} checks, ${Date.now() - t0} ms)${error ? '\n     ' + error : ''}`);
  await ctx.close();
}
await browser.close();
mkdirSync(new URL('docs/evidence/', root), { recursive: true });
writeFileSync(new URL('docs/evidence/e2e-results.json', root), JSON.stringify({ file: 'dist/ByrdWay_Physics_I_Honors.html', at: new Date().toISOString(), browser: 'Chromium (Playwright 1.56.1, SwiftShader WebGL)', results }, null, 1));
console.log(`\n${results.length - failed}/${results.length} suites passed`);
process.exit(failed ? 1 : 0);
