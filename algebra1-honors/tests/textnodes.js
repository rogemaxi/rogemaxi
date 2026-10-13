// shared in-page extractor: visible text nodes outside math / no-translate / declared-English regions
module.exports=`(()=>{const out=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
 while(n=w.nextNode()){const el=n.parentElement;if(!el||el.closest('[translate=no],.bwm-math,svg,select,script,style,[lang=en],.brand'))continue;
  if(!el.closest('#app,#bwm-tour-coach,#bwm-tour-invitation'))continue;const s=n.textContent.replace(/\\s+/g,' ').trim();if(s&&/[A-Za-z]{3,}/.test(s))out.push(s);}
 document.querySelectorAll('#app [aria-label],#app [title]').forEach(e=>{if(e.closest('[translate=no],[lang=en]'))return;const s=e.getAttribute('aria-label')||e.getAttribute('title');if(/[A-Za-z]{3,}/.test(s))out.push('@'+s);});
 return out;})()`;
