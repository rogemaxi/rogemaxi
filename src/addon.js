/* ===== BYRDWAY MASTERY ADD-ON — engine (additive only) =====
   Hooks in AFTER the original router: the original route() runs first on every
   hashchange; this layer then renders its own routes and decorates the nav.
   No original function, data, or style is modified. */
const BWM_LANGS = [
  ['en','English','ltr'],['es','Español','ltr'],['zh','中文 (简体)','ltr'],['hi','हिन्दी','ltr'],
  ['ar','العربية','rtl'],['fr','Français','ltr'],['pt','Português','ltr'],['ru','Русский','ltr'],
  ['ht','Kreyòl Ayisyen','ltr'],['vi','Tiếng Việt','ltr'],['ko','한국어','ltr'],['ja','日本語','ltr']
];
const BWM_KEY = 'byrdway.mastery.v1';
const BWM_PASS = 0.8;

function bwmLoad(){ try{ return JSON.parse(localStorage.getItem(BWM_KEY)) || {}; }catch(e){ return {}; } }
const DB = bwmLoad();
DB.lang = DB.lang || 'en';
DB.progress = DB.progress || {};   // examKey -> {idx, answers:{qid: optionIndex}}
DB.results = DB.results || {};     // examKey -> {answers, correct, total, at}
DB.best = DB.best || {};           // examKey -> best fraction
function bwmSave(){ try{ localStorage.setItem(BWM_KEY, JSON.stringify(DB)); }catch(e){} }

function t(key, vars){
  let s = (BWM_I18N[DB.lang] && BWM_I18N[DB.lang][key]) || BWM_I18N.en[key] || key;
  if(vars) Object.keys(vars).forEach(k => { s = s.split('{'+k+'}').join(vars[k]); });
  return s;
}
function langDir(){ const l = BWM_LANGS.find(x => x[0]===DB.lang); return l ? l[2] : 'ltr'; }
function math(m){ return `<span class="bwm-math" translate="no" dir="ltr">${esc(m).replace(/\n/g,'<br>')}</span>`; }
function optHTML(o){ return o.charAt(0)==='@' ? `<span>${esc(t(o.slice(1)))}</span>` : math(o); }
function wrap(inner){ return `<div class="bwm page" lang="${DB.lang}" dir="${langDir()}">${inner}</div>`; }
function areaName(id){ return t('area_'+id); }
function pct(x){ return Math.round(x*100)+'%'; }

/* deterministic shuffle so the correct answer (authored as o[0]) is not always first */
function order(q){
  let h = 2166136261; for(const ch of q.id){ h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  const idx = q.o.map((_,i)=>i);
  for(let i=idx.length-1;i>0;i--){ h = Math.imul(h ^ (h>>>13), 1274126177); const j = Math.abs(h) % (i+1); [idx[i],idx[j]]=[idx[j],idx[i]]; }
  return idx;
}

function examDef(key){
  if(key==='diag') return {key, items:BWM_DIAGNOSTIC, title:t('card_diag_t'), base:'#/diagnostic'};
  const n = +key.replace('co','');
  const co = BWM_CHECKOUTS.find(c => c.n===n);
  if(!co) return null;
  return {key, items:co.items, title:t('co'+n+'_n'), dok:co.dok, base:'#/eoc/'+n};
}
function dokLabel(d){ return d.charAt(0)==='@' ? t(d.slice(1)) : d; }

/* ---------- Hub (also embedded at the top of the original Home dashboard) ---------- */
function langPicker(){
  const opts = BWM_LANGS.map(l => `<option value="${l[0]}" ${l[0]===DB.lang?'selected':''}>${l[1]}</option>`).join('');
  return `<div class="bwm-langrow"><label for="bwm-lang">🌐 ${esc(t('lang_label'))}</label>
    <select id="bwm-lang" class="bwm-select" translate="no" onchange="BWM.setLang(this.value)">${opts}</select>
    <span class="bwm-note">${esc(t('lang_note'))}</span></div>`;
}
function hubCards(){
  const d = DB.results.diag;
  const coDone = BWM_CHECKOUTS.filter(c => (DB.best['co'+c.n]||0) >= BWM_PASS).length;
  return `<div class="bwm-cards">
    <a class="bwm-card" href="#/diagnostic"><div class="bwm-ic">🩺</div><h3>${esc(t('card_diag_t'))}</h3><p>${esc(t('card_diag_d'))}</p>
      <div class="bwm-stat">${d ? esc(t('score'))+': '+d.correct+'/'+d.total : esc(t('not_taken'))}</div></a>
    <a class="bwm-card" href="#/plan"><div class="bwm-ic">📋</div><h3>${esc(t('card_plan_t'))}</h3><p>${esc(t('card_plan_d'))}</p></a>
    <a class="bwm-card" href="#/learn"><div class="bwm-ic">🧠</div><h3>${esc(t('card_learn_t'))}</h3><p>${esc(t('card_learn_d'))}</p></a>
    <a class="bwm-card" href="#/eoc"><div class="bwm-ic">🏁</div><h3>${esc(t('card_eoc_t'))}</h3><p>${esc(t('card_eoc_d'))}</p>
      <div class="bwm-stat">${coDone}/5 · ${esc(t('mastered'))}</div></a>
  </div>`;
}
function hubBlock(){
  return `<div class="bwm-hero" lang="${DB.lang}" dir="${langDir()}">
    <h2>${esc(t('hub_title'))}</h2><p class="bwm-sub">${esc(t('hub_sub'))}</p>
    ${langPicker()}${hubCards()}</div>`;
}
function renderHub(){
  return wrap(`${hubBlock()}<p class="bwm-note">${esc(t('lang_disclaimer'))}</p>`);
}

/* ---------- Exams: Diagnostic + EOC Checkouts ---------- */
function prog(key){ return DB.progress[key] || (DB.progress[key] = {idx:0, answers:{}}); }

function renderExam(key){
  const ex = examDef(key); if(!ex) return wrap('');
  const p = prog(key);
  const n = ex.items.length;
  p.idx = Math.min(Math.max(p.idx,0), n-1);
  const q = ex.items[p.idx];
  const done = Object.keys(p.answers).length;
  const ord = order(q);
  const letters = 'ABCD';
  const opts = ord.map((oi,k) => `<button type="button" class="bwm-opt ${p.answers[q.id]===oi?'on':''}" aria-pressed="${p.answers[q.id]===oi}" onclick="BWM.pick('${key}','${q.id}',${oi})">
      <span class="bwm-letter" translate="no">${letters[k]}</span>${optHTML(q.o[oi])}</button>`).join('');
  const dots = ex.items.map((it,i) => `<button type="button" class="bwm-dot ${p.answers[it.id]!==undefined?'done':''} ${i===p.idx?'cur':''}" onclick="BWM.go('${key}',${i})" translate="no" aria-label="${i+1}">${i+1}</button>`).join('');
  const intro = key==='diag' ? `<p class="hint">${esc(t('diag_intro'))}</p>` : `<p class="hint">${esc(t('co'+key.slice(2)+'_d'))}</p>`;
  return wrap(`<h2>${esc(ex.title)} ${ex.dok?`<span class="bwm-dok ${ex.dok.charAt(0)==='@'?'x':''}">${esc(dokLabel(ex.dok))}</span>`:''}</h2>
    ${intro}
    <div class="bwm-qhead"><span>${esc(t('q_of',{n:p.idx+1,t:n}))}</span><span>${esc(t('answered',{n:done,t:n}))}</span></div>
    <div class="bwm-progress"><i style="width:${Math.round(done/n*100)}%"></i></div>
    <div class="bwm-qcard">
      <div class="bwm-qhead"><span>${esc(areaName(q.a))}</span></div>
      <p class="bwm-stem">${esc(t(q.s))}</p>
      ${q.m?`<div class="bwm-mathbox">${math(q.m)}</div>`:''}
      <div class="bwm-opts" role="group">${opts}</div>
    </div>
    <div class="bwm-nav">
      <button type="button" class="bwm-btn ghost" ${p.idx===0?'disabled':''} onclick="BWM.go('${key}',${p.idx-1})">${esc(t('prev'))}</button>
      ${p.idx<n-1 ? `<button type="button" class="bwm-btn alt" onclick="BWM.go('${key}',${p.idx+1})">${esc(t('next'))}</button>` : ''}
      <button type="button" class="bwm-btn" onclick="BWM.finish('${key}')">${esc(t('finish'))}</button>
    </div>
    <div class="bwm-dots">${dots}</div>
    <p><a href="#/mastery">${esc(t('back_hub'))}</a></p>`);
}

function scoreExam(key, answers){
  const ex = examDef(key);
  const byArea = {};
  let correct = 0;
  ex.items.forEach(q => {
    const ok = answers[q.id] === 0;
    if(ok) correct++;
    const b = byArea[q.a] || (byArea[q.a] = {c:0, n:0});
    b.n++; if(ok) b.c++;
  });
  return {correct, total:ex.items.length, byArea};
}

function barColor(f){ return f>=0.85 ? 'var(--green)' : f>=0.7 ? 'var(--blue)' : f>=0.5 ? '#fb923c' : 'var(--red)'; }

function renderResults(key){
  const ex = examDef(key); const r = ex && DB.results[key];
  if(!r) return renderExam(key);
  const s = scoreExam(key, r.answers);
  const bars = AREAS.filter(a => s.byArea[a.id]).map(a => {
    const b = s.byArea[a.id], f = b.c/b.n;
    return `<div class="bwm-bar"><span>${esc(areaName(a.id))}</span><span class="bwm-track"><i style="width:${Math.max(f*100,2)}%;background:${barColor(f)}"></i></span><span translate="no">${b.c}/${b.n}</span></div>`;
  }).join('');
  const review = ex.items.map((q,i) => {
    const pick = r.answers[q.id];
    const st = pick===undefined ? 'na' : pick===0 ? 'ok' : 'no';
    const label = st==='ok' ? t('correct') : st==='no' ? t('incorrect') : t('unanswered');
    return `<div class="bwm-qcard bwm-review ${st}">
      <div class="bwm-qhead"><span translate="no">#${i+1}</span><span class="bwm-tag ${st}">${esc(label)}</span></div>
      <p class="bwm-stem">${esc(t(q.s))}</p>${q.m?`<div class="bwm-mathbox">${math(q.m)}</div>`:''}
      ${pick!==undefined && pick!==0 ? `<p><b>${esc(t('your_answer'))}:</b> ${optHTML(q.o[pick])}</p>`:''}
      <p><b>${esc(t('correct_answer'))}:</b> ${optHTML(q.o[0])}</p>
      <details><summary>${esc(t('solution'))}</summary><ol class="bwm-steps">${q.w.map((w,k)=>`<li><span class="bwm-sn">${k+1}</span>${math(w)}</li>`).join('')}</ol></details>
      ${st!=='ok'?`<div class="fixthis"><a href="#/learn/${q.a}">→ ${esc(t('step_learn'))}</a> · <a href="#/area/${q.a}/blueprint">→ ${esc(t('step_blueprint'))}</a></div>`:''}
    </div>`;
  }).join('');
  const f = s.correct/s.total;
  return wrap(`<h2>${esc(ex.title)} — ${esc(t('results'))} ${ex.dok?`<span class="bwm-dok ${ex.dok.charAt(0)==='@'?'x':''}">${esc(dokLabel(ex.dok))}</span>`:''}</h2>
    <div class="cs-page"><p class="bwm-score" translate="no">${s.correct}/${s.total} · ${pct(f)}</p>
      ${key!=='diag' && f>=BWM_PASS ? `<p class="bwm-done">✓ ${esc(t('mastered'))}</p>`:''}
      <h3>${esc(t('by_area'))}</h3><div class="bwm-bars">${bars}</div>
      <div style="margin-top:14px"><a class="bwm-btn" href="#/plan">${esc(t('see_plan'))}</a>
      <button type="button" class="bwm-btn ghost" onclick="BWM.retake('${key}')">${esc(t('retake'))}</button></div></div>
    <h3>${esc(t('review'))}</h3>${review}
    <p><a href="#/mastery">${esc(t('back_hub'))}</a></p>`);
}

/* ---------- Prescriptive plan: weakest → strongest ---------- */
function areaStats(){
  const agg = {};
  Object.keys(DB.results).forEach(key => {
    if(!examDef(key)) return;
    const s = scoreExam(key, DB.results[key].answers);
    Object.keys(s.byArea).forEach(id => { const g = agg[id] || (agg[id]={c:0,n:0}); g.c += s.byArea[id].c; g.n += s.byArea[id].n; });
  });
  return agg;
}
function band(f){
  if(f < 0.5) return {k:'fix', color:'var(--red)', steps:[['learn','#/learn/'],['blueprint','/blueprint'],['practice','/interactive'],['flash','/flashcards'],['test','/testme']]};
  if(f < 0.7) return {k:'build', color:'#fb923c', steps:[['blueprint','/blueprint'],['cheat','/cheatsheet'],['flash','/flashcards'],['test','/testme']]};
  if(f < 0.85) return {k:'strengthen', color:'var(--blue)', steps:[['flash','/flashcards'],['test','/testme'],['learn','#/learn/']]};
  return {k:'extend', color:'var(--green)', steps:[['honors','/honors'],['test','/testme']]};
}
function renderPlan(){
  const agg = areaStats();
  const answered = Object.values(agg).reduce((s,g)=>s+g.n,0);
  if(!answered) return wrap(`<h2>${esc(t('card_plan_t'))}</h2><div class="cs-page"><p>${esc(t('plan_none'))}</p>
    <a class="bwm-btn" href="#/diagnostic">${esc(t('start'))}: ${esc(t('card_diag_t'))}</a></div>`);
  const ranked = AREAS.filter(a => agg[a.id]).map(a => ({a, f:agg[a.id].c/agg[a.id].n, g:agg[a.id]}))
    .sort((x,y) => x.f - y.f || x.a.num - y.a.num);
  const items = ranked.map((r,i) => {
    const b = band(r.f);
    const links = b.steps.map(([s,path],k) => {
      const href = path.charAt(0)==='#' ? path + r.a.id : `#/area/${r.a.id}${path}`;
      return `<a href="${href}"><b translate="no">${k+1}</b>${esc(t('step_'+s))}</a>`;
    }).join('');
    return `<div class="bwm-plan-item" style="border-inline-start-color:${b.color}">
      <h3><span class="bwm-rank" translate="no">${i+1}</span>${esc(areaName(r.a.id))}
        <span class="bwm-band" style="background:${b.color}">${esc(t('band_'+b.k))}</span>
        <span class="bwm-note" translate="no">${r.g.c}/${r.g.n} · ${pct(r.f)}</span></h3>
      <p class="hint">${esc(t('band_'+b.k+'_d'))}</p><div class="bwm-plan-links">${links}</div></div>`;
  }).join('');
  const nextCo = BWM_CHECKOUTS.find(c => (DB.best['co'+c.n]||0) < BWM_PASS);
  return wrap(`<h2>${esc(t('card_plan_t'))}</h2>
    <p class="hint">${esc(t('plan_intro'))}</p><p class="bwm-note">${esc(t('plan_basis',{n:answered}))}</p>
    ${items}
    ${nextCo?`<div class="cs-page"><p><b>${esc(t('plan_next_checkout'))}</b> ${esc(t('co'+nextCo.n+'_n'))} <span class="bwm-dok ${nextCo.dok.charAt(0)==='@'?'x':''}">${esc(dokLabel(nextCo.dok))}</span></p>
      <a class="bwm-btn" href="#/eoc/${nextCo.n}">${esc(t('start'))}</a></div>`:''}
    <p><a href="#/mastery">${esc(t('back_hub'))}</a></p>`);
}

/* ---------- First-principles lessons ---------- */
function renderLearnIndex(){
  const tiles = AREAS.map(a => `<a class="tile" href="#/learn/${a.id}"><div class="tile-num" translate="no">${a.num}</div><div class="tile-ic">${icon(a.num)}</div><div class="tile-name">${esc(areaName(a.id))}</div></a>`).join('');
  return wrap(`<h2>${esc(t('learn_title'))}</h2><p class="hint">${esc(t('learn_pick'))}</p>${langPicker()}
    <div class="tilegrid bwm-tilegrid">${tiles}</div><p><a href="#/mastery">${esc(t('back_hub'))}</a></p>`);
}
function renderLesson(id){
  const L = BWM_LESSONS[id]; const a = findArea(id);
  if(!L || !a) return renderLearnIndex();
  const steps = L.steps.map((s,i) => `<li><span class="bwm-sn" translate="no">${i+1}</span><span class="bwm-sl">${esc(t(s[0]))}</span>${math(s[1])}</li>`).join('');
  const uid = 'bwm-try-'+id;
  return wrap(`<h2>${esc(areaName(id))} — ${esc(t('tab_learn'))}</h2>${langPicker()}
    <div class="bwm-lesson">
      <div class="cs-page"><h3>① ${esc(t('l_principle'))}</h3><p class="bwm-principle">${esc(t('L_'+id+'_p'))}</p></div>
      <div class="cs-page"><h3>② ${esc(t('l_why'))}</h3><p>${esc(t('L_'+id+'_w'))}</p></div>
      <div class="cs-page"><h3>③ ${esc(t('l_build'))}</h3><p><b>${esc(t('l_example'))}:</b></p><div class="bwm-mathbox">${math(L.ex)}</div><ol class="bwm-steps">${steps}</ol></div>
      <div class="cs-page"><h3>④ ${esc(t('l_check'))}</h3><div class="bwm-mathbox">${math(L.check)}</div></div>
      <div class="cs-page"><h3>⑤ ${esc(t('l_try'))}</h3><div class="bwm-mathbox">${math(L.tq)}</div>
        <button type="button" class="reveal-btn" onclick="var e=document.getElementById('${uid}');e.style.display=e.style.display==='none'?'block':'none'">${esc(t('l_reveal'))}</button>
        <div id="${uid}" class="ti-a" style="display:none"><p>${math(L.ta)}</p><ol class="bwm-steps">${L.tw.map((w,k)=>`<li><span class="bwm-sn" translate="no">${k+1}</span>${math(w)}</li>`).join('')}</ol></div></div>
      <div class="cs-page"><h3>⑥ ${esc(t('l_next'))}</h3><div class="bwm-plan-links">
        <a href="#/area/${id}/blueprint">${esc(t('step_blueprint'))}</a><a href="#/area/${id}/flashcards">${esc(t('step_flash'))}</a>
        <a href="#/area/${id}/testme">${esc(t('step_test'))}</a><a href="#/area/${id}/interactive">${esc(t('step_practice'))}</a></div></div>
    </div><p><a href="#/learn">← ${esc(t('learn_title'))}</a> · <a href="#/mastery">${esc(t('back_hub'))}</a></p>`);
}

/* ---------- EOC Checkouts list ---------- */
function renderEocList(){
  const rows = BWM_CHECKOUTS.map(c => {
    const best = DB.best['co'+c.n];
    const status = best===undefined ? esc(t('not_taken')) : esc(t('best',{s:pct(best)})) + (best>=BWM_PASS?` · <span class="bwm-done">✓ ${esc(t('mastered'))}</span>`:'');
    return `<div class="bwm-eoc-row"><div class="bwm-eoc-num" translate="no">${c.n}</div>
      <div><b>${esc(t('co'+c.n+'_n'))}</b><span class="bwm-dok ${c.dok.charAt(0)==='@'?'x':''}">${esc(dokLabel(c.dok))}</span>
        <div class="hint">${esc(t('co'+c.n+'_d'))}</div><div class="bwm-note">${esc(t('questions_n',{n:c.items.length}))} · ${status}</div></div>
      <a class="bwm-btn" href="#/eoc/${c.n}${DB.results['co'+c.n]&&!DB.progress['co'+c.n]?'/results':''}">${esc(DB.results['co'+c.n]&&!DB.progress['co'+c.n]?t('results'):t('start'))}</a></div>`;
  }).join('');
  return wrap(`<h2>${esc(t('eoc_title'))}</h2><p class="hint">${esc(t('eoc_intro'))}</p>${langPicker()}<div class="bwm-eoc">${rows}</div>
    <p><a href="#/mastery">${esc(t('back_hub'))}</a></p>`);
}

/* ---------- Router layer (runs after the original route()) ---------- */
function decorate(parts){
  const links = document.querySelector('#app .navlinks');
  if(links && !links.querySelector('.bwm-navlink')){
    const a = document.createElement('a');
    a.href = '#/mastery'; a.className = 'bwm-navlink'; a.textContent = t('nav_hub');
    if(['mastery','diagnostic','plan','learn','eoc'].includes(parts[0])) a.classList.add('active');
    links.insertBefore(a, links.firstChild);
  }
  const tabbar = document.querySelector('#app .area-tabbar');
  if(tabbar && parts[0]==='area' && parts[1] && !tabbar.querySelector('.bwm-tab')){
    const a = document.createElement('a');
    a.href = '#/learn/'+parts[1]; a.className = 'bwm-tab'; a.textContent = '🧠 '+t('tab_learn');
    tabbar.appendChild(a);
  }
  document.querySelectorAll('#app .cc-formula, #app .ti-diagram, #app .fc-diagram').forEach(el => el.setAttribute('translate','no'));
}

function bwmRoute(){
  const hash = location.hash || '#/cover';
  const parts = hash.replace('#/','').split('/');
  const app = document.getElementById('app');
  if(!app) return;
  let body = null;
  if(parts[0]==='mastery') body = renderHub();
  else if(parts[0]==='diagnostic') body = parts[1]==='results' ? renderResults('diag') : renderExam('diag');
  else if(parts[0]==='plan') body = renderPlan();
  else if(parts[0]==='learn') body = parts[1] ? renderLesson(parts[1]) : renderLearnIndex();
  else if(parts[0]==='eoc') body = parts[1] ? (parts[2]==='results' ? renderResults('co'+parts[1]) : renderExam('co'+parts[1])) : renderEocList();
  if(body !== null){
    app.innerHTML = navBar() + body;
  } else if(parts[0]==='home'){
    const page = app.querySelector('.page');
    if(page && !page.querySelector('.bwm-hero')) page.insertAdjacentHTML('afterbegin', hubBlock());
  }
  decorate(parts);
}

window.BWM = {
  setLang(l){ if(BWM_LANGS.some(x=>x[0]===l)){ DB.lang = l; bwmSave(); const y = window.scrollY; route(); bwmRoute(); window.scrollTo(0,y); } },
  pick(key, qid, oi){ const p = prog(key); p.answers[qid] = oi; bwmSave(); const y = window.scrollY; bwmRoute(); window.scrollTo(0,y); },
  go(key, i){ prog(key).idx = i; bwmSave(); bwmRoute(); window.scrollTo(0,0); },
  finish(key){
    const ex = examDef(key); const p = prog(key);
    const missing = ex.items.length - Object.keys(p.answers).length;
    if(missing > 0 && !window.confirm(t('confirm_unanswered',{n:missing}))) return;
    const s = scoreExam(key, p.answers);
    DB.results[key] = {answers:Object.assign({}, p.answers), correct:s.correct, total:s.total, at:Date.now()};
    DB.best[key] = Math.max(DB.best[key]||0, s.correct/s.total);
    delete DB.progress[key];
    bwmSave();
    location.hash = ex.base + '/results';
  },
  retake(key){ const ex = examDef(key); delete DB.progress[key]; bwmSave(); if(location.hash===ex.base) bwmRoute(); else location.hash = ex.base; window.scrollTo(0,0); }
};

window.addEventListener('hashchange', bwmRoute);
window.addEventListener('DOMContentLoaded', bwmRoute);
