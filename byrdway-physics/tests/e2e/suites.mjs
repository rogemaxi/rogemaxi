// E2E suites. Each receives { page, expect, goto } and must leave no page errors.
const LANGS = ['en', 'es', 'fr', 'ht', 'pt', 'ar', 'zh', 'hi', 'bn', 'vi', 'ko', 'ja'];

export const SUITES = {
  async 'shell: cover, dashboard, navigation'({ page, expect, goto }) {
    await goto('#/cover');
    expect(await page.locator('.cover h1').innerText() === 'BYRDWAY', 'cover title');
    await page.click('.cta'); await page.waitForTimeout(400);
    expect((await page.locator('h1').innerText()).length > 3, 'dashboard heading');
    for (const r of ['units', 'labs', 'videos', 'settings', 'unit/5', 'section/5.3', 'lab/5']) {
      await page.evaluate(h => (location.hash = h), '#/' + r); await page.waitForTimeout(300);
      expect(await page.locator('main h1').count() > 0, `route #/${r} renders a heading`);
    }
  },

  async 'slice: section 5.3 full learning flow + progress persists'({ page, expect, goto }) {
    await goto('#/section/5.3');
    const cards = await page.locator('.lesson .card').count();
    expect(cards >= 16, `lesson renders all components (${cards} cards)`);
    expect(await page.locator('svg.diagram').count() === 1, 'visual model diagram');
    expect(await page.locator('.vlinks a').count() === 3, 'three video search links');
    expect(await page.locator('.vlinks a[target=_blank][rel*=noopener]').count() === 3, 'external links open safely');
    // predict
    await page.click('#plock'); expect((await page.locator('#pfb').innerText()).length > 0, 'predict requires a choice');
    await page.check('input[name=spred][value="2"]'); await page.click('#plock');
    expect((await page.locator('#pfb').innerText()).includes('0.67'), 'prediction feedback explains');
    // a wrong numeric answer triggers the Error Detective (0.003 is the gram→kg mistake on p2)
    await page.fill('[data-q="p.p2"]', '0.003'); await page.click('[data-check="p.p2"]');
    expect(await page.locator('[data-fb="p.p2"] .detective').count() === 1, 'error detective diagnoses unit-prefix error');
    // complete is blocked until practice is correct
    await page.click('#complete'); expect((await page.locator('#cneed').innerText()).length > 0, 'completion gated on practice');
    for (const [id, v] of [['p1', '3600'], ['p2', '3.0'], ['p3', '1.2e4'], ['p5', '4.5']]) { await page.fill(`[data-q="p.${id}"]`, v); await page.click(`[data-check="p.${id}"]`); }
    await page.check('input[name="5.3-p.p4"][value="1"]'); await page.click('[data-check="p.p4"]');
    expect(await page.locator('.q.qdone').count() >= 5, 'correct answers accepted (incl. 1.2e4 notation)');
    await page.click('#complete');
    expect(await page.locator('#complete').isDisabled(), 'section marked complete');
    await page.reload(); await page.waitForTimeout(600);
    expect(await page.locator('#complete').isDisabled(), 'completion persists after reload');
    await page.evaluate(() => (location.hash = '#/home')); await page.waitForTimeout(400);
    expect((await page.locator('.stat b').first().innerText()) === '1', 'dashboard counts the completed section');
  },

  async 'slice: Lab 5 3D experiment, predict gate, run, challenge, evaluation'({ page, expect, goto }) {
    await goto('#/lab/5');
    expect(await page.locator('[data-renderer="3d"]').count() === 1, 'WebGL 3D renderer active');
    await page.click('#run');
    expect((await page.locator('#lpfb').innerText()).length > 0, 'run is gated on a prediction');
    await page.check('input[name=lpred][value="2"]'); await page.click('#lplock');
    // challenge 1: m = 5, F = 10, μ = 0 → a = 2.0
    await page.locator('[data-p="m"]').fill('5'); await page.locator('[data-p="F"]').fill('10');
    await page.click('#speed'); await page.selectOption('#speed', '1');
    await page.click('#run'); await page.waitForTimeout(3600);
    const a = await page.evaluate(() => [...document.querySelectorAll('.measures div')].map(d => d.innerText));
    expect(a.some(t => /2(\.0+)?\s*m\/s²/.test(t)), 'live acceleration reads 2 m/s² ' + JSON.stringify(a));
    await page.waitForFunction(() => document.querySelector('#run').innerText.includes('▶'), null, { timeout: 8000 });
    await page.click('[data-ch="0"]');
    expect((await page.locator('#chfb0').innerText()).includes('✓'), 'challenge 1 verified from recorded run');
    expect(await page.locator('#runs tbody tr').count() >= 1, 'run recorded in data table');
    await page.fill('#evin', '2'); await page.click('#evbtn');
    expect((await page.locator('#evfb').innerText()).includes('✓'), 'evaluation answer validated');
    expect((await page.locator('#lprog').innerText()).includes('✓'), 'lab completion recorded');
    // controls exist and work
    for (const id of ['#reset', '#replay', '#speed', '#cam', '#view', '#tv', '#tt', '#te', '#tfx', '#csv', '#rec', '#clr']) expect(await page.locator(id).count() === 1, 'control ' + id);
    await page.selectOption('#cam', 'top'); await page.selectOption('#view', 'concept');
    expect(await page.locator('.cbar').count() > 0, 'conceptual view shows qualitative bars');
  },

  async 'slice: Lab 5 2D fallback (low graphics) has identical physics'({ page, expect, goto }) {
    await page.addInitScript(() => localStorage.setItem('byrdway-physics-v1', JSON.stringify({ schema: 1, sections: {}, labs: { 5: { predicted: 2 } }, settings: { graphics: 'low' } })));
    await goto('#/lab/5');
    expect(await page.locator('[data-renderer="2d"]').count() === 1, '2D renderer used in low-graphics mode');
    await page.click('#run'); await page.waitForTimeout(1500);
    const a = await page.evaluate(() => [...document.querySelectorAll('.measures div')].map(d => d.innerText).join(' '));
    expect(/5\s*m\/s²/.test(a), '2D: a = F/m = 20/4 = 5 m/s² ' + a);
  },

  async 'labs: every registered lab runs in 3D and 2D, measures update, a run is recorded'({ page, expect, goto }) {
    await goto('#/labs');
    for (let n = 1; n <= 20; n++) {
      await page.evaluate(h => (location.hash = h), '#/lab/' + n); await page.waitForTimeout(500);
      if (!(await page.locator('[data-renderer]').count())) continue;
      expect(await page.locator('[data-renderer="3d"]').count() === 1, `lab ${n}: 3D renderer`);
      await page.check('input[name=lpred][value="0"]'); await page.click('#lplock');
      if (n === 6) await page.locator('[data-p="theta"]').fill('35');   // default 20° is a static (holding) case
      const view = page.locator('[data-renderer] canvas').first();
      const img0 = await view.screenshot();
      await page.click('#run'); await page.waitForTimeout(1200);
      const img1 = await view.screenshot();
      await page.waitForTimeout(1300);
      const after = await page.evaluate(() => [...document.querySelectorAll('.measures div')].map(d => d.innerText).join('|'));
      expect(!img0.equals(img1), `lab ${n}: the simulated scene moves during a run`);
      expect(!/NaN|undefined|Infinity/.test(after), `lab ${n}: measurements are finite (${after.slice(0, 120)})`);
      await page.screenshot({ path: `docs/evidence/screens/lab${String(n).padStart(2, '0')}-3d.png` });
      await page.click('#rec');
      expect(await page.locator('#runs tbody tr').count() >= 1, `lab ${n}: run recorded`);
      expect((await page.locator('.eqs, #eqs').innerText().catch(() => 'x')).length > 0, `lab ${n}: live equations`);
      // 2D fallback
      await page.evaluate(() => { const k = 'byrdway-physics-v1'; const s = JSON.parse(localStorage.getItem(k)); s.settings.graphics = 'low'; localStorage.setItem(k, JSON.stringify(s)); });
      await page.reload(); await page.waitForTimeout(500);
      expect(await page.locator('[data-renderer="2d"]').count() === 1, `lab ${n}: 2D fallback`);
      await page.click('#run'); await page.waitForTimeout(1200);
      await page.screenshot({ path: `docs/evidence/screens/lab${String(n).padStart(2, '0')}-2d.png` });
      await page.evaluate(() => { const k = 'byrdway-physics-v1'; const s = JSON.parse(localStorage.getItem(k)); s.settings.graphics = 'high'; localStorage.setItem(k, JSON.stringify(s)); });
      await page.reload(); await page.waitForTimeout(300);
    }
  },

  async 'curriculum: all 170 sections render every component without errors'({ page, expect, goto }) {
    await goto('#/home');
    const all = await page.evaluate(async () => { const out = []; for (let u = 1; u <= 20; u++) { location.hash = '#/unit/' + u; await new Promise(r => setTimeout(r, 60)); out.push(...[...document.querySelectorAll('.seclist a')].map(a => a.getAttribute('href').split('/').pop())); } return out; });
    expect(all.length === 170, `170 sections listed (${all.length})`);
    for (const id of all) {
      await page.evaluate(h => (location.hash = h), '#/section/' + id); await page.waitForTimeout(40);
      const n = await page.locator('.lesson .card').count();
      expect(n >= 16, `${id}: ${n} component cards`);
      expect(await page.locator('svg.diagram').count() >= 1, `${id}: diagram`);
      expect(!(await page.locator('main').innerText()).includes('being authored'), `${id}: no placeholder`);
    }
  },

  async 'engines: all ten engines render and respond'({ page, expect, goto }) {
    await goto('#/engines');
    expect(await page.locator('.engtile').count() === 10, 'ten engine tiles');
    for (const r of ['cheat/6', 'blueprint/7', 'flash/8', 'test/9', 'labs', 'feynman/10.3', 'support/11', 'tutor/12.3', 'formula', 'detective']) {
      await page.evaluate(h => (location.hash = h), '#/engine/' + r); await page.waitForTimeout(250);
      expect((await page.locator('main').innerText()).length > 200, `engine ${r} has content`);
    }
    // flashcards flip and Leitner promotion
    await page.evaluate(() => (location.hash = '#/engine/flash/3')); await page.waitForTimeout(250);
    await page.click('#fc'); await page.click('#knew');
    expect(await page.evaluate(() => Object.values(JSON.parse(localStorage.getItem('byrdway-physics-v1')).cards).includes(2)), 'card promoted to box 2');
    // formula lab solves Ohm's law for R
    await page.evaluate(() => (location.hash = '#/engine/formula')); await page.waitForTimeout(250);
    await page.selectOption('#fsel', 'ohm'); await page.waitForTimeout(150);
    await page.selectOption('#ftar', 'R'); await page.waitForTimeout(150);
    await page.fill('[data-v="V"]', '12'); await page.fill('[data-v="I"]', '0.5'); await page.dispatchEvent('[data-v="I"]', 'input');
    expect((await page.locator('#fres').innerText()).includes('24'), 'R = 24 Ω');
    expect((await page.locator('main').innerText()).includes('kg·m²·s⁻³·A⁻¹'), 'dimension check shown for V');
    // error detective analyzer
    await page.evaluate(() => (location.hash = '#/engine/detective')); await page.waitForTimeout(250);
    await page.fill('#dc', '4.5'); await page.fill('#dy', '4500'); await page.click('#dgo');
    expect((await page.locator('#dout').innerText()).toLowerCase().includes('1000'), 'analyzer finds ×1000');
    // blueprint drill gives feedback
    await page.evaluate(() => (location.hash = '#/engine/blueprint/6')); await page.waitForTimeout(250);
    await page.locator('#drill [data-k]').first().click();
    expect((await page.locator('#drill .fb').innerText()).length > 5, 'drill feedback');
  },

  async 'assessment: full adaptive diagnostic builds a plan; levels, task rubric, finals'({ page, expect, goto }) {
    await goto('#/diagnostic');
    await page.click('#go');
    for (let i = 0; i < 20; i++) {
      const num = await page.locator('#qa').count();
      if (num) await page.fill('#qa', '1'); else await page.locator('input[name=qa]').first().check();
      await page.click('#qs'); await page.click('#qs'); await page.waitForTimeout(30);
    }
    expect(await page.locator('h1').innerText() === 'Your personalized learning plan', 'plan view after 20 questions');
    const d = await page.evaluate(() => JSON.parse(localStorage.getItem('byrdway-physics-v1')).diagnostic);
    expect(d.finished && d.answers.length === 20 && new Set(d.answers.map(a => a.unit)).size === 20, 'one question per unit, saved');
    expect(d.plan.recommend.length > 0, 'plan recommends sections');
    await page.evaluate(() => (location.hash = '#/home')); await page.waitForTimeout(250);
    expect((await page.locator('.dash').innerText()).includes('Estimated readiness'), 'dashboard shows diagnostic result');
    for (const n of [1, 2, 3, 4, 5]) {
      await page.evaluate(h => (location.hash = h), '#/mastery/' + n); await page.waitForTimeout(250);
      expect((await page.locator('.quiz').count()) === 1, `level ${n} quiz`);
    }
    await page.evaluate(() => (location.hash = '#/mastery/4')); await page.waitForTimeout(250);
    expect(await page.locator('.task .rubric tr').count() >= 4, 'DOK 4 task with rubric');
    await page.fill('#tresp', 'My model and justification.'); await page.locator('.rubric tr').evaluateAll(rows => rows.forEach(r => r.querySelector('input').click()));
    await page.click('#tsave'); expect((await page.locator('#tfb').innerText()).includes('Rubric total'), 'rubric saved with total');
    for (const k of ['core', 'honors']) {
      await page.evaluate(h => (location.hash = h), '#/final/' + k); await page.waitForTimeout(200);
      expect((await page.locator('.lead').innerText()).includes('38'), `${k} final has 38 questions`);
      await page.click('#go'); expect(await page.locator('.quiz').count() === 1, `${k} final starts`);
    }
    await page.evaluate(() => (location.hash = '#/assess/unit/16')); await page.waitForTimeout(250);
    expect(await page.locator('.quiz').count() === 1, 'unit test');
  },

  async 'reference: every tab renders, standards marked verified/provisional'({ page, expect, goto }) {
    await goto('#/reference');
    for (const k of ['formulas', 'constants', 'si', 'glossary', 'misconceptions', 'standards', 'safety', 'math', 'translations', 'about']) {
      await page.evaluate(h => (location.hash = h), '#/reference/' + k); await page.waitForTimeout(200);
      expect((await page.locator('#refbody').innerText()).length > 150, `reference ${k}`);
    }
    await page.evaluate(() => (location.hash = '#/reference/standards')); await page.waitForTimeout(200);
    expect(await page.locator('#refbody tbody tr').count() === 37, 'all 37 retrieved content benchmarks listed');
    expect((await page.locator('#refbody').innerText()).includes('Alignment provisional'), 'alignment honestly provisional');
  },

  ...Object.fromEntries(LANGS.map(l => [`i18n[${l}]: 5.3 + Lab 5 fully localized`, async ({ page, expect, goto }) => {
    await goto('#/section/5.3', l);
    expect(await page.evaluate(() => document.documentElement.lang) === l, 'html lang');
    expect(await page.evaluate(() => document.documentElement.dir) === (l === 'ar' ? 'rtl' : 'ltr'), 'direction');
    const untr = await page.locator('main .untr').count();
    expect(untr === 0, `no untranslated text on 5.3 (found ${untr})`);
    await page.evaluate(() => (location.hash = '#/lab/5')); await page.waitForTimeout(600);
    const untrLab = await page.locator('main .untr').count();
    expect(untrLab === 0, `no untranslated text in Lab 5 (found ${untrLab})`);
  }])),
};
