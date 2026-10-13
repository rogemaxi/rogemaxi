const {chromium}=require(process.env.PW||'/opt/node-tools/node_modules/playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto('file://'+require('path').resolve(process.argv[2]));await p.waitForTimeout(200);
const r=await p.evaluate(()=>{const I=BWM.inspect();const T=I.translations.en;const st=q=>({...q,stem:T[q.s]||q.s});
 const legacy=(()=>{const P=JSON.parse(JSON.stringify(I.progress));return null})();
 return {bank:I.bank.map(st),eoc:I.checkouts.flatMap(c=>c.items.map(st)),tok:Object.fromEntries(Object.entries(T).filter(([k])=>k.startsWith('tok_')))};});
require('fs').writeFileSync(process.argv[3],JSON.stringify(r));await b.close();})();
