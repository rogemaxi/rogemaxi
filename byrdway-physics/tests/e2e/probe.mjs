// Ad-hoc probe: load a route, report console errors, renderer kind, and save a screenshot.
import { chromium } from 'playwright';
const [,, route = '#/home', shot = 'probe.png', w = '1366', h = '900'] = process.argv;
const file = new URL('../../dist/ByrdWay_Physics_I_Honors.html', import.meta.url).href;
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: { width: +w, height: +h } });
const errs = [];
p.on('pageerror', e => errs.push('pageerror: ' + e.message));
p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
await p.goto(file + route);
await p.waitForTimeout(1200);
if (process.env.ACT) await eval(`(async()=>{${process.env.ACT}})()`);
const info = await p.evaluate(() => ({ title: document.title, h1: document.querySelector('h1')?.innerText, renderer: document.querySelector('[data-renderer]')?.dataset.renderer, len: document.body.innerText.length }));
await p.screenshot({ path: process.env.OUT + '/' + shot, fullPage: !!process.env.FULL });
console.log(JSON.stringify(info), '\nERRORS:', errs.length ? errs.join('\n') : 'none');
await b.close();
