// End-to-end check in headless Chromium: original features still work, new features work.
// Run: NODE_PATH=$(npm root -g) node tools/e2e.mjs
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import path from 'node:path';
import fs from 'node:fs';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const FILE = 'file://' + path.join(ROOT, 'dist/Byrdway_Algebra_Power_Tool_PLUS_Mastery.html');
const ORIG = 'file://' + path.join(ROOT, 'original/Byrdway_Algebra_Power_Tool_ORIGINAL.html');
const SHOTS = path.join(ROOT, 'dist/screens'); fs.mkdirSync(SHOTS, { recursive: true });
const results = []; const ok = (c, m) => { const r = (c ? 'PASS ' : 'FAIL ') + m; results.push(r); console.log(r); };

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1200, height: 900 } });
ctx.setDefaultTimeout(5000);
const page = await ctx.newPage();
const errors = []; page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('dialog', d => d.accept());

// 1) Original routes render identically (compare #app HTML minus our decorations)
const origPage = await ctx.newPage();
const strip = h => h.replace(/<a href="#\/mastery" class="bwm-navlink[^"]*">[^<]*<\/a>/g, '').replace(/<a href="#\/learn\/[^"]*" class="bwm-tab">[^<]*<\/a>/g, '').replace(/ translate="no"/g, '').replace(/<div class="bwm-hero"[\s\S]*?<\/div><\/div>\s*<\/div>/, '');
for (const h of ['#/cover', '#/how', '#/backmatter', '#/area/solving-equations/cheatsheet', '#/area/quadratic-functions/blueprint', '#/area/analyzing-data/flashcards', '#/area/systems-equations/testme', '#/area/polynomials-factoring/honors', '#/area/linear-equations/interactive']) {
  await origPage.goto(ORIG + h); await page.goto(FILE + h);
  const a = await origPage.$eval('#app', e => e.innerHTML);
  const b = await page.$eval('#app', e => e.innerHTML);
  ok(strip(b) === a, `original page unchanged: ${h}`);
}
// original interactions still work
await page.goto(FILE + '#/area/solving-equations/flashcards');
await page.click('.flashcard .flip-inner');
ok(await page.$eval('.flashcard', e => e.classList.contains('flipped')), 'flashcard flip still works');
await page.goto(FILE + '#/area/solving-equations/testme');
await page.click('.reveal-btn');
ok(await page.$eval('.ti-a', e => e.style.display === 'block'), 'Test Me reveal still works');

// 2) Dashboard (home) gets the hub
await page.goto(FILE + '#/home');
ok(await page.$('.bwm-hero') !== null, 'home dashboard shows Mastery Hub');
ok(await page.$$eval('.tile', t => t.length) === 10, 'home still shows 10 area tiles');
ok((await page.$$eval('#bwm-lang option', o => o.length)) === 12, '12 languages offered');
await page.screenshot({ path: path.join(SHOTS, 'home.png'), fullPage: false });

// 3) Diagnostic: 25 questions, answer all correctly except area 1
await page.goto(FILE + '#/diagnostic');
const nQ = await page.$$eval('.bwm-dot', d => d.length);
ok(nQ === 25, `diagnostic has 25 questions (${nQ})`);
await page.screenshot({ path: path.join(SHOTS, 'diagnostic.png') });
const diag = await page.evaluate(() => 0); // placeholder
for (let i = 0; i < 25; i++) {
  // pick the option whose onclick ends with ",0)" (correct) except first 3 questions (area 1) -> wrong
  const sel = i < 3 ? '.bwm-opt:not([onclick$=",0)"])' : '.bwm-opt[onclick$=",0)"]';
  await page.click(sel);
  if (i < 24) await page.click('.bwm-nav .bwm-btn.alt');
}
await page.click('.bwm-nav .bwm-btn:not(.alt):not(.ghost)');
await page.waitForSelector('.bwm-score');
ok((await page.$eval('.bwm-score', e => e.textContent)).startsWith('22/25'), 'diagnostic scored 22/25');
await page.screenshot({ path: path.join(SHOTS, 'diag-results.png') });

// 4) Plan: weakest first
await page.goto(FILE + '#/plan');
const first = await page.$eval('.bwm-plan-item h3', e => e.textContent);
ok(/Solving Equations/.test(first), 'plan ranks weakest area (Solving Equations) first');
ok((await page.$$eval('.bwm-plan-item', e => e.length)) === 10, 'plan lists all 10 areas');
await page.screenshot({ path: path.join(SHOTS, 'plan.png') });

// 5) Lessons for every area
for (const id of ['solving-equations','linear-equations','linear-absvalue-functions','systems-equations','exponents-exponential','polynomials-factoring','quadratic-functions','solving-quadratics','working-with-functions','analyzing-data']) {
  await page.goto(FILE + '#/learn/' + id);
  ok((await page.$$eval('.bwm-lesson .cs-page', e => e.length)) === 6, `lesson renders: ${id}`);
}
await page.screenshot({ path: path.join(SHOTS, 'lesson.png') });
await page.goto(FILE + '#/area/solving-equations/cheatsheet');
ok(await page.$('.area-tabbar .bwm-tab') !== null, 'First Principles tab added to area tab bar');

// 6) Five checkouts, 15 each, perfect score -> mastery
for (let n = 1; n <= 5; n++) {
  await page.goto(FILE + '#/eoc/' + n);
  const c = await page.$$eval('.bwm-dot', d => d.length);
  ok(c === 15, `checkout ${n} has 15 questions`);
  for (let i = 0; i < c; i++) { await page.click('.bwm-opt[onclick$=",0)"]'); if (i < c - 1) await page.click('.bwm-nav .bwm-btn.alt'); }
  await page.click('.bwm-nav .bwm-btn:not(.alt):not(.ghost)');
  await page.waitForSelector('.bwm-score');
  ok((await page.$eval('.bwm-score', e => e.textContent)).startsWith('15/15'), `checkout ${n} scored 15/15`);
}
await page.goto(FILE + '#/eoc');
ok((await page.$$eval('.bwm-done', e => e.length)) === 5, 'all 5 checkouts show mastery');
await page.screenshot({ path: path.join(SHOTS, 'eoc.png') });

// 7) Every language: switch, wording changes, math identical, no errors
const langs = await page.$$eval('#bwm-lang option', o => o.map(x => x.value));
await page.goto(FILE + '#/eoc/4');
const mathEN = await page.$$eval('.bwm-math', e => e.map(x => x.textContent).join('|'));
const stemEN = await page.$eval('.bwm-stem', e => e.textContent);
for (const l of langs) {
  await page.evaluate(l => BWM.setLang(l), l);
  await page.goto(FILE + '#/eoc/4');
  const m = await page.$$eval('.bwm-math', e => e.map(x => x.textContent).join('|'));
  const s = await page.$eval('.bwm-stem', e => e.textContent);
  ok(m === mathEN, `${l}: math identical`);
  if (l !== 'en') ok(s !== stemEN, `${l}: wording translated`);
  for (const h of ['#/mastery', '#/plan', '#/learn/quadratic-functions', '#/diagnostic/results', '#/eoc/5/results']) {
    await page.goto(FILE + h);
    const raw = await page.$eval('#app', e => e.innerText);
    ok(!/\b(s|c[1-5]|d|op|L|tok|band|step|co)_[a-z0-9_-]+\b/.test(raw.replace(/f\(g|\w+_\w+\(/g,'')), `${l}${h}: no raw keys`);
  }
  if (['ar', 'zh', 'hi', 'es'].includes(l)) { await page.goto(FILE + '#/learn/solving-equations'); await page.screenshot({ path: path.join(SHOTS, `lesson-${l}.png`) }); }
}
await page.evaluate(() => BWM.setLang('en'));

// 8) Phone width: no horizontal scroll
const phone = await ctx.newPage(); await phone.setViewportSize({ width: 375, height: 800 });
for (const h of ['#/home', '#/diagnostic', '#/plan', '#/learn/solving-equations', '#/eoc', '#/eoc/2/results']) {
  await phone.goto(FILE + h);
  const over = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  ok(over <= 0, `phone ${h}: no horizontal scroll (${over})`);
}
await phone.goto(FILE + '#/eoc/2'); await phone.screenshot({ path: path.join(SHOTS, 'phone-exam.png') });

ok(errors.length === 0, 'no JS errors: ' + errors.join(' | '));
await browser.close();

const f = results.filter(r => r.startsWith('FAIL'));
console.log(`\n${results.length - f.length}/${results.length} passed`);
process.exit(f.length ? 1 : 0);
