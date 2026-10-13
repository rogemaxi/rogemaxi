// Scan every translated screen for stray English words (catches mixed-language sentences).
const {chromium}=require(process.env.PW||'/opt/node-tools/node_modules/playwright');
const F=require('path').resolve(process.argv[2]);
const ALLOW=new Set('EOC DOK Blueprint Blueprints BYRDWAY ByrdWay Byrdway Khanmigo JSON Esc Escape Enter AI IA Flashcards Honors honors Kit kit'.split(' '));
// Same-spelling native words (not English): es/fr/ht "plan", fr "questions"/"Score".
const COGNATE={es:/\bplan\b/gi,fr:/\b(plan|questions?|score|correcte?)\b/gi,ht:/\bplan\b/gi};
const STOP=/\b(the|and|your|with|this|that|from|are|was|not|for|you|questions?|answers?|lesson|area|skills?|results?|correct|incorrect|step|plan|next|back|start|finish|score)\b/i;
(async()=>{const b=await chromium.launch();let bad=0;
for(const l of ['es','zh','hi','ar','fr','pt','ru','ht','vi','ko','ja']){const ctx=await b.newContext();const p=await ctx.newPage();p.on('dialog',d=>d.accept());
 await p.goto('file://'+F);await p.evaluate(()=>{localStorage.clear();localStorage.setItem('byrdway.algebra.onboarding.v1',JSON.stringify({version:1,status:'skipped'}))});await p.reload();await p.waitForTimeout(150);
 await p.evaluate(l=>BWM.setLang(l),l);await p.evaluate(()=>location.hash='#/diagnostic');await p.waitForTimeout(100);
 for(let i=0;i<20;i++){await p.click(`button.bwm-opt[onclick$=",${i%3?0:1})"]`);if(i<19)await p.click('button[onclick="BWM.advance()"]');}
 await p.click(`button[onclick="BWM.finish('diag')"]`);await p.waitForTimeout(100);
 const hits=new Map();
 for(const r of ['#/home','#/mastery','#/diagnostic/results','#/plan','#/learn','#/eoc','#/eoc/2','#/how']){await p.evaluate(r=>location.hash=r,r);await p.waitForTimeout(120);
  await p.evaluate(()=>document.querySelectorAll('details').forEach(d=>d.open=true));
  const nodes=await p.evaluate(require('./textnodes.js'));
  for(const s of nodes){const words=(s.replace(/[A-Za-z]*\([^)]*\)[^\s]*/g,' ').match(/\b[A-Za-z]{3,}\b/g)||[]).filter(w=>!ALLOW.has(w));
   const latinLang=['es','fr','pt','ht','vi'].includes(l);
   const t=COGNATE[l]?s.replace(COGNATE[l],''):s;
   if((!latinLang&&words.length)||(latinLang&&STOP.test(t)&&!/^@/.test(s)))hits.set(s.slice(0,110),r);}}
 const list=[...hits].filter(([s])=>!/^[\s\S]*\b(abs|sqrt|f|g|h|p|P|C|F)\b/.test(s)||/\b[a-z]{4,}\b/.test(s.replace(/abs|sqrt/g,'')));
 console.log(`${l}: ${list.length} node(s) with English words`);list.slice(0,8).forEach(([s,r])=>console.log('   ',r,'|',s));bad+=list.length;await ctx.close();}
await b.close();process.exit(bad?1:0);})();
