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
