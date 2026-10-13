const {chromium}=require(process.env.PW||'/opt/node-tools/node_modules/playwright');
const F=require('path').resolve(process.argv[2]);
(async()=>{const b=await chromium.launch();
async function shot(lang,hash,file,vp,prep){const ctx=await b.newContext({viewport:vp});const p=await ctx.newPage();p.on('dialog',d=>d.accept());
 await p.goto('file://'+F);await p.evaluate(()=>{localStorage.clear();localStorage.setItem('byrdway.algebra.onboarding.v1',JSON.stringify({version:1,status:'skipped'}))});await p.reload();await p.waitForTimeout(150);
 await p.evaluate(l=>BWM.setLang(l),lang);if(prep)await prep(p);await p.evaluate(h=>location.hash=h,hash);await p.waitForTimeout(250);
 await p.screenshot({path:'tests/screenshots/'+file});await ctx.close();}
const diag=async p=>{await p.evaluate(()=>location.hash='#/diagnostic');await p.waitForTimeout(100);for(let i=0;i<20;i++){await p.click(`button.bwm-opt[onclick$=",${i%3?0:1})"]`);if(i<19)await p.click('button[onclick="BWM.advance()"]');}await p.click(`button[onclick="BWM.finish('diag')"]`);};
await shot('ar','#/home','dashboard-ar-desktop.png',{width:1280,height:900});
await shot('ja','#/diagnostic','diagnostic-ja-mobile.png',{width:390,height:844},async p=>{await p.evaluate(()=>location.hash='#/diagnostic');await p.waitForTimeout(100);for(let i=0;i<6;i++){await p.click('button.bwm-opt[onclick$=",0)"]');await p.click('button[onclick="BWM.advance()"]');}});
await shot('es','#/plan','plan-es-desktop.png',{width:1280,height:900},diag);
await shot('hi','#/area/solving-equations/cheatsheet','cheatsheet-hi-notice.png',{width:1280,height:700});
await shot('en','#/home','dashboard-en-desktop.png',{width:1280,height:900});
await b.close();})();
