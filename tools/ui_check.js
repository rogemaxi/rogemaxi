// End-to-end UI check: drives the REAL running dashboard, clicks real controls, screenshots all 15 sections.
// Usage: node tools/ui_check.js http://127.0.0.1:8765/ <screenshot_dir>
// Exit code 0 only if every section renders, controls work, and the only browser error is the expected
// 403 from the deliberate order-placement refusal test.
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const base = process.argv[2] || 'http://127.0.0.1:8765/';
  const out = process.argv[3] || 'screenshots';
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 2 });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const results = {};
  const sections = ['command', 'markets', 'portfolio', 'research', 'doctrine', 'risk', 'compounding', 'decisions', 'agents',
                    'ledgers', 'brokerage', 'reports', 'approvals', 'audit', 'settings'];
  const go = async (s) => { await page.goto(base + '#' + s); await page.reload(); await page.waitForSelector('#main h2', { timeout: 20000 }); };
  try {
    await go('agents'); await page.click('text=Run due jobs now'); await page.waitForTimeout(1500); results.run_jobs = true;
    await go('reports'); await page.click('text=Generate report for week containing date'); await page.waitForSelector('text=Week of', { timeout: 15000 }); results.weekly_report = true;
    await go('research'); await page.fill('#a_h', '10'); await page.selectOption('#a_e', 'true');
    await page.click('text=Run allocation analysis'); await page.waitForSelector('text=1 · Action', { timeout: 20000 }); results.analysis = true;
    const reject = page.locator('button:has-text("Reject")');
    if (await reject.count()) { await reject.first().click(); await page.waitForTimeout(600); results.reject_click = true; }
    await go('settings'); await page.click('text=Test: attempt to place an order'); await page.waitForTimeout(600);
    results.order_refusal = (await page.textContent('#toast')).includes('never places');
    await go('approvals'); await page.click('text=Save draft'); await page.waitForTimeout(800);
    results.policy_draft_validation = (await page.content()).includes('problem(s)') || (await page.content()).includes('valid');
    for (const [i, s] of sections.entries()) {
      await go(s);
      const h = await page.textContent('#main h2');
      results['section_' + s] = h;
      await page.screenshot({ path: `${out}/${String(i + 1).padStart(2, '0')}_${s}.png` });
    }
  } catch (e) { errors.push('script: ' + e.message); }
  await browser.close();
  const unexpected = errors.filter(e => !/403 \(Forbidden\)/.test(e));
  const ok = unexpected.length === 0 && results.order_refusal && results.weekly_report && results.analysis &&
             sections.every(s => results['section_' + s]);
  fs.writeFileSync(`${out}/ui_check.json`, JSON.stringify({ ok, results, errors }, null, 2));
  console.log(JSON.stringify({ ok, unexpected, sections: sections.map(s => results['section_' + s]) }));
  process.exit(ok ? 0 : 1);
})();
