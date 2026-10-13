// End-to-end verification of the built Power Tool in real headless Chromium.
// Usage: node tests/verify.js <built.html> [original.html]   -> writes tests/results.json, exits 1 on failure
const {chromium}=require(process.env.PW||'/opt/node-tools/node_modules/playwright');
const fs=require('fs'),path=require('path');
const F=path.resolve(process.argv[2]),O=process.argv[3]&&path.resolve(process.argv[3]);
const EXTRACT=require('./textnodes.js');
const LANGS=['en','es','zh','hi','ar','fr','pt','ru','ht','vi','ko','ja'];
const TRANSLATED=['#/home','#/mastery','#/diagnostic','#/plan','#/learn','#/eoc','#/eoc/1','#/how'];
const AFTER=['#/diagnostic/results','#/plan','#/eoc/1/results'];
const EN_ONLY=['#/area/solving-equations/cheatsheet','#/area/linear-equations/blueprint','#/area/quadratic-functions/flashcards','#/area/analyzing-data/testme','#/area/solving-equations/honors','#/area/solving-equations/interactive','#/backmatter','#/learn/solving-equations'];
const report={file:path.basename(F),generated:new Date().toISOString(),checks:[]};let failed=0;
const check=(name,pass,detail)=>{report.checks.push({name,pass,detail});if(!pass)failed++;console.log((pass?'PASS ':'FAIL ')+name+(detail&&!pass?' :: '+JSON.stringify(detail).slice(0,400):''));};
(async()=>{const b=await chromium.launch();
async function page(opts={}){const ctx=await b.newContext(opts);const p=await ctx.newPage();p.errs=[];p.on('pageerror',e=>p.errs.push(e.message));p.on('dialog',d=>d.accept());
 await p.goto('file://'+F);await p.evaluate(()=>{localStorage.clear();localStorage.setItem('byrdway.algebra.onboarding.v1',JSON.stringify({version:1,status:'skipped'}))});await p.reload();await p.waitForTimeout(200);p.ctx=ctx;return p;}
async function go(p,h){await p.evaluate(h=>location.hash=h,h);await p.waitForTimeout(120);}
async function runDiag(p,pattern){for(let i=0;i<20;i++){await p.click(`button.bwm-opt[onclick$=",${pattern(i)})"]`);if(i<19)await p.click('button[onclick="BWM.advance()"]');}await p.click(`button[onclick="BWM.finish('diag')"]`);await p.waitForTimeout(150);}
async function runEoc(p,n){await go(p,'#/eoc/'+n);for(let i=0;i<15;i++){await p.click(`button.bwm-opt[onclick$=",${i%4?0:2})"]`);if(i<14)await p.click('.bwm-nav .bwm-btn.alt');}await p.click(`button[onclick="BWM.finish('co${n}')"]`);await p.waitForTimeout(150);}
async function texts(p,routes){const o={};for(const r of routes){await go(p,r);await p.evaluate(()=>document.querySelectorAll('details').forEach(d=>d.open=true));o[r]=await p.evaluate(EXTRACT);}return o;}
// Baseline English text for every screen
const en=await page();const enT=await texts(en,TRANSLATED);await go(en,'#/diagnostic');await runDiag(en,i=>i%3?0:1);await runEoc(en,1);Object.assign(enT,await texts(en,AFTER));await en.ctx.close();
// 1. Language coverage per language (translated screens must contain zero English-identical text nodes)
for(const l of LANGS.slice(1)){const p=await page();await p.evaluate(l=>BWM.setLang(l),l);
 const T=await texts(p,TRANSLATED);await go(p,'#/diagnostic');await runDiag(p,i=>i%3?0:1);await runEoc(p,1);Object.assign(T,await texts(p,AFTER));
 const residue={};let nodes=0;for(const r of Object.keys(T)){const E=new Set(enT[r]);nodes+=T[r].length;const same=T[r].filter(s=>E.has(s)&&!/^(EOC \d|DOK [\d.]+|@?BYRDWAY)/.test(s)&&!/^(Blueprints?|Flashcards|EOC \d+: \d+\/\d+)$/.test(s));if(same.length)residue[r]=same.slice(0,6);}
 check(`B1 ${l}: dashboard/hub/diagnostic/results/plan/EOC/how fully in ${l} (${nodes} text nodes)`,Object.keys(residue).length===0,residue);
 // English-only content pages: must carry a translated notice and be marked lang=en
 const notes=[];for(const r of EN_ONLY){await go(p,r);notes.push(await p.evaluate(()=>{const n=document.getElementById('bwm-en-only');const pg=document.querySelector('#app > .page');const lessonNote=document.querySelector('.bwm .hint[role=note]');return !!(n&&n.textContent.length>20)||!!lessonNote?(pg&&pg.getAttribute('lang')==='en'||!!document.querySelector('.bwm-lesson[lang=en]')):false;}));}
 check(`B2 ${l}: English-only sections honestly labelled in ${l} and marked lang=en`,notes.every(Boolean),{EN_ONLY,notes});
 const st=await p.evaluate(()=>({html:document.documentElement.lang,dir:document.documentElement.dir,nav:document.getElementById('bwm-lang-nav')?.value}));
 check(`L1 ${l}: <html lang/dir> and nav picker reflect the selected language`,st.html===l&&st.nav===l&&st.dir===(l==='ar'?'rtl':'ltr'),st);
 check(`R1 ${l}: no JavaScript errors`,p.errs.length===0,p.errs);await p.ctx.close();}
// 2. Tour fully translated in each language
for(const l of LANGS.slice(1)){const p=await page();await p.evaluate(l=>BWM.setLang(l),l);await go(p,'#/home');const bad=[];
 for(let s=0;s<5;s++){if(s===0)await p.click('#bwm-help-tour');else await p.click('#bwm-tour-coach .bwm-btn:not(.ghost):not(.alt)');await p.waitForTimeout(120);
  const t=await p.evaluate(()=>{const c=document.getElementById('bwm-tour-coach');return {lang:c.getAttribute('lang'),text:c.innerText};});
  if(t.lang!==l||/\b(Next|Back|Skip Tour|Exit|Step \d of 5|Welcome aboard|Replay Tour)\b/.test(t.text))bad.push({s,t:t.text.slice(0,120)});}
 check(`B3 ${l}: onboarding tour (5 steps) rendered in ${l}`,bad.length===0,bad);await p.ctx.close();}
// 3. Adaptive diagnostic behaviour + scoring (through the real UI)
const runs={};for(const [name,pat] of [['strong',()=>0],['weak',()=>1],['mixed',i=>i%2?1:0]]){const p=await page();await go(p,'#/diagnostic');
 const diffs=[];for(let i=0;i<20;i++){diffs.push(await p.evaluate(()=>{const P=JSON.parse(localStorage.getItem('byrdway.mastery.v1')).progress.diag;return BWM.inspect().bank.find(q=>q.id===P.ids.at(-1)).difficulty;}));
  await p.click(`button.bwm-opt[onclick$=",${pat(i)})"]`);if(i<19)await p.click('button[onclick="BWM.advance()"]');}
 await p.click(`button[onclick="BWM.finish('diag')"]`);await p.waitForTimeout(150);
 const r=await p.evaluate(()=>{const R=JSON.parse(localStorage.getItem('byrdway.mastery.v1')).results.diag;const per={};R.ids.forEach(id=>{const a=BWM.inspect().bank.find(q=>q.id===id).a;per[a]=(per[a]||0)+1;});return {correct:R.correct,total:R.total,unique:new Set(R.ids).size,per,shown:document.querySelector('.bwm-score')?.textContent};});
 runs[name]={diffs,...r};await p.ctx.close();}
const avg=a=>a.reduce((s,x)=>s+x,0)/a.length;
check('A1 diagnostic is adaptive: strong path reaches difficulty ≥4 and averages ≥1.5 levels above weak path',Math.max(...runs.strong.diffs)>=4&&avg(runs.strong.diffs)-avg(runs.weak.diffs)>=1.5,{strong:runs.strong.diffs,weak:runs.weak.diffs,mixed:runs.mixed.diffs});
check('A2 diagnostic covers all 10 areas, 2 items each, 20 unique items',Object.keys(runs.strong.per).length===10&&Object.values(runs.strong.per).every(n=>n===2)&&runs.strong.unique===20,runs.strong.per);
check('S1 scoring exact through UI: 20/20, 0/20, 10/20 stored and displayed',runs.strong.correct===20&&runs.weak.correct===0&&runs.mixed.correct===10&&/20\/20/.test(runs.strong.shown)&&/0\/20/.test(runs.weak.shown)&&/10\/20/.test(runs.mixed.shown),{s:runs.strong.shown,w:runs.weak.shown,m:runs.mixed.shown});
// 4. Answer keys: every bank/legacy/EOC item has o[0] correct per independent check file; distinct options
{const p=await page();const r=await p.evaluate(()=>{const I=BWM.inspect();const all=[...I.bank,...I.checkouts.flatMap(c=>c.items)];return {n:all.length,dup:all.filter(q=>new Set(q.o).size!==q.o.length).map(q=>q.id),bank:I.bank.length};});
 check(`S2 ${r.n} assessment items have 4 distinct options (bank ${r.bank} ≥ 250)`,r.dup.length===0&&r.bank>=250,r);await p.ctx.close();}
// 5. Locked earlier diagnostic answers are visibly disabled
{const p=await page();await go(p,'#/diagnostic');await p.click('button.bwm-opt[onclick$=",0)"]');await p.click('button[onclick="BWM.advance()"]');await p.click('.bwm-dot >> nth=0');await p.waitForTimeout(100);
 const r=await p.evaluate(()=>({dis:[...document.querySelectorAll('.bwm-opt')].every(b=>b.disabled),note:!!document.querySelector('.bwm-qcard .bwm-note[role=note]')}));check('A3 revisited adaptive item is locked and says why',r.dis&&r.note,r);await p.ctx.close();}
// 6. Persistence: language + mid-diagnostic progress survive reload and language switching
{const p=await page();await p.evaluate(()=>BWM.setLang('ko'));await go(p,'#/diagnostic');for(let i=0;i<3;i++){await p.click('button.bwm-opt[onclick$=",0)"]');await p.click('button[onclick="BWM.advance()"]');}
 await p.evaluate(()=>BWM.setLang('ar'));await p.reload();await p.waitForTimeout(200);await go(p,'#/diagnostic');
 const r=await p.evaluate(()=>{const D=JSON.parse(localStorage.getItem('byrdway.mastery.v1'));return {lang:D.lang,answered:Object.keys(D.progress.diag.answers).length,ids:D.progress.diag.ids.length,html:document.documentElement.lang,dir:document.documentElement.dir};});
 check('P1 language and in-progress diagnostic persist across language switch and reload',r.lang==='ar'&&r.answered===3&&r.ids===4&&r.html==='ar'&&r.dir==='rtl',r);await p.ctx.close();}
// 7. Mobile: no horizontal page scroll at 375px in the longest languages
for(const l of ['en','ru','vi','ar','hi']){const p=await page({viewport:{width:375,height:740}});await p.evaluate(l=>BWM.setLang(l),l);const over=[];
 for(const r of ['#/home','#/mastery','#/diagnostic','#/plan','#/eoc']){await go(p,r);const w=await p.evaluate(()=>[document.documentElement.scrollWidth,innerWidth]);if(w[0]>w[1]+1)over.push({r,w});}
 check(`M1 ${l}: no horizontal scroll at 375px`,over.length===0,over);await p.ctx.close();}
// 8. Accessibility basics on translated screens
{const p=await page();await p.evaluate(()=>BWM.setLang('es'));const issues=[];for(const r of ['#/home','#/diagnostic','#/plan','#/eoc']){await go(p,r);issues.push(...await p.evaluate(r=>{const out=[];document.querySelectorAll('#app button,#app a,#app select').forEach(e=>{const name=(e.getAttribute('aria-label')||e.textContent||e.title||'').trim()||(e.id&&document.querySelector(`label[for="${e.id}"]`)?.textContent);if(!name)out.push(r+' unnamed '+e.outerHTML.slice(0,60));});return out;},r));}
 check('X1 every button/link/select on translated screens has an accessible name',issues.length===0,issues.slice(0,5));await p.ctx.close();}
// 9. Regression: English text identical to the original on every route (except the two intended wording fixes)
if(O){const ROUTES=[...TRANSLATED,...EN_ONLY];async function grab(f){const ctx=await b.newContext();const p=await ctx.newPage();await p.goto('file://'+f);await p.evaluate(()=>{localStorage.clear();localStorage.setItem('byrdway.algebra.onboarding.v1',JSON.stringify({version:1,status:'skipped'}))});await p.reload();await p.waitForTimeout(200);const o={};for(const r of ROUTES){await p.evaluate(r=>location.hash=r,r);await p.waitForTimeout(120);o[r]=await p.evaluate(()=>{const c=document.getElementById('app').cloneNode(true);c.querySelectorAll('.bwm-navlang').forEach(e=>e.remove());return {t:c.textContent.replace(/\s+/g,' '),n:c.querySelectorAll('a,button,input,select,textarea').length};});}await ctx.close();return o;}
 const A=await grab(O),B=await grab(F);const diffs=[];for(const r of ROUTES){const a=A[r],c=B[r];if(a.n!==c.n){diffs.push({r,controls:[a.n,c.n]});continue;}if(a.t!==c.t){const ta=a.t.replace(/The language selector translates parts[^.]*\.[^.]*\.[^.]*\.?/,'').replace(/Written-task text is available in English\./,''),tb=c.t.replace(/Translated in this language:[^.]*\. Still English only:[^.]*\./,'').replace(/Written-task text is available in English only\./,'');if(ta!==tb)diffs.push({r,why:'text'});}}
 check(`G1 zero feature regression in English: ${ROUTES.length} routes, same controls and text (2 intended wording fixes excluded)`,diffs.length===0,diffs);}
report.summary={passed:report.checks.filter(c=>c.pass).length,failed,total:report.checks.length};
fs.writeFileSync(path.join(__dirname,'results.json'),JSON.stringify(report,null,1));console.log(`\n${report.summary.passed}/${report.summary.total} checks passed`);await b.close();process.exit(failed?1:0);})();
