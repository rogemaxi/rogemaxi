// View dispatcher and the core navigation views: cover, dashboard, units, unit hub, labs hub, lab page,
// video library, and settings. Engine, assessment, and reference views live in their own modules.
import { t, localize, LANGS } from '../i18n.js';
import { esc, L, P, tt, pathwayBadge, progressBar, extLink, download, toast } from '../ui.js';
import * as store from '../store.js';
import { UNITS, PARTS, SECTIONS, findUnit, RESOURCES } from '../../data/curriculum/index.js';
import { LABS, findLab } from '../../lab/labs/index.js';
import { mountLab, labComplete } from '../../lab/harness.js';
import { renderSection, sectionDone } from './section.js';
import { renderEngine, enginesHub } from './engines.js';
import { renderAssess } from './assess.js';
import { renderReference } from './reference.js';
import { studyPlanSummary, honorsReadiness, recommendedNext } from '../../engines/plan.js';
import { voiceFor } from '../narration.js';

export function dispatch(name, rest, main) {
  switch (name) {
    case 'home': return home(main);
    case 'units': return units(main);
    case 'unit': return unit(main, rest[0], rest[1]);
    case 'section': return renderSection(main, rest[0]);
    case 'labs': return labsHub(main);
    case 'lab': return labPage(main, rest[0]);
    case 'engines': return enginesHub(main);
    case 'engine': return renderEngine(main, rest[0], rest.slice(1));
    case 'assess': case 'diagnostic': case 'mastery': case 'final': return renderAssess(main, name, rest);
    case 'videos': return videosView(main, rest[0]);
    case 'reference': return renderReference(main, rest[0], rest[1]);
    case 'settings': return settings(main);
    default: main.innerHTML = `<div class="page"><h1>${tt('notfound')}</h1><a class="btn" href="#/home">${tt('gohome')}</a></div>`;
  }
}

export function cover() {
  return `<div class="cover">
    <canvas id="stars" aria-hidden="true"></canvas>
    <div class="cover-inner">
      <div class="atom" aria-hidden="true"><span></span><span></span><span></span><i></i></div>
      <h1>${tt('brand')}</h1>
      <h2>${tt('product')}</h2>
      <p class="tagline">${tt('tagline')}</p>
      <p class="promise">${tt('promise')}</p>
      <p class="author">${tt('author')}</p>
      <a class="cta" href="#/home">${tt('enter')} →</a>
      <div class="cover-langs" aria-label="${tt('lang.label')}">${LANGS.map(l => `<button data-lang="${l.code}" lang="${l.code}">${esc(l.native)}</button>`).join('')}</div>
    </div>
  </div>`;
}
document.addEventListener('click', e => {
  const b = e.target.closest?.('.cover-langs [data-lang]');
  if (b) { store.update(s => { s.settings.lang = b.dataset.lang; }); location.hash = '#/home'; }
});

const unitProgress = u => { const n = u.sections.length, d = u.sections.filter(s => sectionDone(s.id)).length; return { n, d, frac: n ? d / n : 0 }; };

function home(main) {
  const st = store.get(), s = st.settings;
  const done = SECTIONS.filter(x => sectionDone(x.id)).length;
  const labsDone = LABS.filter(l => labComplete(l.num)).length;
  const next = recommendedNext();
  const hr = honorsReadiness();
  const plan = studyPlanSummary();
  const finals = st.finals || {}, lv = st.mastery || {};
  const best = arr => (arr?.length ? Math.max(...arr.map(a => Math.round(100 * a.score / a.total))) + '%' : '—');
  main.innerHTML = `<div class="page dash">
    <h1>${tt('dash.title')}</h1><p class="lead">${tt('dash.welcome')}</p>
    <div class="dash-top">
      <div class="card glow next"><div class="eyebrow">${tt('dash.recommended')}</div>
        ${next ? `<h2><span class="secnum">${esc(next.id)}</span> ${L(localize(next.id, { x: next.title }).value.x)}</h2><p>${pathwayBadge(next.pathway)} ${tt('unit.title', { n: next.unit })}</p><a class="btn gold" href="#/section/${next.id}">${st.sections[next.id]?.visited ? tt('dash.continue') : tt('dash.start')} →</a>` : `<p>${tt('complete')}</p>`}
      </div>
      <div class="card"><div class="eyebrow">${tt('path.label')}</div>
        <div class="seg" role="radiogroup">${['core', 'honors', 'advanced'].map(p => `<label><input type="radio" name="pw" value="${p}" ${s.pathway === p ? 'checked' : ''}> ${tt('path.' + p)}</label>`).join('')}</div>
        <p class="hint">${s.pathway === 'advanced' ? tt('path.advanced.note') : ''}</p>
        <div class="eyebrow">${tt('dash.streak')}</div><p class="big">🔥 ${tt('dash.streak.days', { n: st.streak.days })}</p>
        <p class="hint">${store.storageOK ? tt('dash.saved') : tt('dash.notsaved')}</p>
      </div>
      <div class="card"><div class="eyebrow">${tt('dash.diag')}</div>
        ${st.diagnostic?.finished ? `<p>${tt('dash.diag.result', { pct: Math.round(100 * st.diagnostic.answers.filter(a => a.ok).length / st.diagnostic.answers.length), n: st.diagnostic.answers.length })}</p><a class="btn" href="#/diagnostic/plan">${tt('dash.plan')}</a>` : `<p>${tt('dash.diag.none')}</p><a class="btn gold" href="#/diagnostic">${tt('dash.diag.take')}</a>`}
        <div class="eyebrow">${tt('dash.honors')}</div><p><span class="hr hr-${hr.state}">${tt('honors.' + hr.state)}</span></p><p class="hint">${esc(hr.reason)}</p>
      </div>
    </div>
    <div class="stats">
      <div class="stat"><b>${done}</b><span>/ ${SECTIONS.length} ${tt('dash.sections')}</span>${progressBar(done / SECTIONS.length, t('dash.sections'))}</div>
      <div class="stat"><b>${labsDone}</b><span>/ ${LABS.length === 20 ? 20 : 20} ${tt('dash.labs')}</span>${progressBar(labsDone / 20, t('dash.labs'))}</div>
      <div class="stat"><b>${best(finals.core)}</b><span>${tt('assess.final.core')}</span></div>
      <div class="stat"><b>${best(finals.honors)}</b><span>${tt('assess.final.honors')}</span></div>
    </div>
    ${plan ? `<div class="card"><h2>${tt('dash.plan')}</h2>${plan}</div>` : ''}
    <div class="card"><h2>${tt('dash.mastery')}</h2><div class="unitbars">${UNITS.map(u => { const p = unitProgress(u); return `<a class="ubar" href="#/unit/${u.num}"><span class="un">${u.num}</span><span class="ut">${L(localize('unit.' + u.num, { x: u.title }).value.x)}</span>${progressBar(p.frac, u.title)}<span class="uc">${p.d}/${p.n}</span></a>`; }).join('')}</div></div>
    <div class="card"><h2>${tt('dash.assess')}</h2><div class="lvgrid">${[1, 2, 3, 4, 5].map(n => `<a class="lv" href="#/mastery/${n}"><b>L${n}</b><span>${tt('level.' + n)}</span><em>${best(lv[n]?.attempts)}</em></a>`).join('')}</div></div>
    <div class="card"><h2>${tt('dash.quicklabs')}</h2><div class="labchips">${LABS.map(l => `<a class="chip ${labComplete(l.num) ? 'done' : ''}" href="#/lab/${l.num}">${l.num}. ${L(localize('lab.' + l.num, { x: l.text.title }).value.x)}</a>`).join('')}</div></div>
    <div class="card"><h2>${tt('nav.settings')}</h2><p><a href="#/settings">${tt('lang.label')} · ${tt('set.graphics')} · ${tt('set.motion')} · ${tt('set.contrast')} · ${tt('set.text')}</a></p></div>
  </div>`;
  main.querySelectorAll('input[name=pw]').forEach(r => r.onchange = () => { store.update(x => { x.settings.pathway = r.value; }); home(main); });
}

function units(main) {
  main.innerHTML = `<div class="page"><h1>${tt('units.title')}</h1>${PARTS.map(part => `<h2 class="parthead">${esc(part)}</h2><div class="unitgrid">${UNITS.filter(u => u.part === part).map(u => { const p = unitProgress(u); return `<a class="utile" href="#/unit/${u.num}"><span class="unum">${u.num}</span><span class="uname">${L(localize('unit.' + u.num, { x: u.title }).value.x)}</span><span class="hint">${tt('units.sections', { n: p.n })} · ${tt('units.done', { d: p.d, n: p.n })}</span>${progressBar(p.frac, u.title)}</a>`; }).join('')}</div>`).join('')}</div>`;
}

function unit(main, n, tab) {
  const u = findUnit(n);
  if (!u) return dispatch('404', [], main);
  const lab = u.lab ? findLab(u.lab) : null;
  const pw = store.get().settings.pathway;
  main.innerHTML = `<div class="page">
    <p class="crumb"><a href="#/units">${tt('nav.units')}</a> · ${esc(u.part)}</p>
    <h1><span class="secnum">${tt('unit.title', { n: u.num })}</span> ${L(localize('unit.' + u.num, { x: u.title }).value.x)}</h1>
    <div class="unit-actions">
      <a class="btn" href="#/engine/cheat/${u.num}">⚡ ${tt('unit.cheat')}</a>
      <a class="btn" href="#/engine/blueprint/${u.num}">🧭 ${tt('unit.blueprint')}</a>
      <a class="btn" href="#/engine/flash/${u.num}">🗂️ ${tt('unit.flash')}</a>
      <a class="btn" href="#/assess/unit/${u.num}">✅ ${tt('unit.test')}</a>
      <a class="btn" href="#/engine/support/${u.num}">🌉 ${tt('unit.bridges')}</a>
      ${lab ? `<a class="btn gold" href="#/lab/${lab.num}">🧪 ${tt('unit.lab')}: ${L(localize('lab.' + lab.num, { x: lab.text.title }).value.x)}</a>` : ''}
    </div>
    <ol class="seclist">${u.sections.map(s => {
      const hide = (pw === 'core' && s.pathway !== 'Core') ? ' optional' : '';
      return `<li class="${sectionDone(s.id) ? 'done' : ''}${hide}"><a href="#/section/${s.id}"><span class="secnum">${esc(s.id)}</span> ${L(localize(s.id, { x: s.title }).value.x)}</a> ${pathwayBadge(s.pathway)} ${sectionDone(s.id) ? '<span class="good">✓</span>' : ''}</li>`;
    }).join('')}</ol>
  </div>`;
}

function labsHub(main) {
  main.innerHTML = `<div class="page"><h1>${tt('labs.title')}</h1><p class="lead">${tt('labs.sub')}</p>
  <div class="labgrid">${RESOURCES.labs.map(r => { const l = findLab(r.num); return `<a class="labtile ${labComplete(r.num) ? 'done' : ''}" href="#/lab/${r.num}"><span class="labnum">${r.num}</span><span class="labname">${l ? L(localize('lab.' + r.num, { x: l.text.title }).value.x) : esc(r.title)}</span><span class="hint">${esc(r.focus)}</span>${labComplete(r.num) ? `<span class="good">✓ ${tt('lab.complete')}</span>` : ''}</a>`; }).join('')}</div></div>`;
}

function labPage(main, n) {
  const lab = findLab(n);
  if (!lab) { const r = RESOURCES.labs.find(l => l.num === +n); main.innerHTML = `<div class="page"><h1>${r ? esc(r.title) : tt('notfound')}</h1><p class="hint">This laboratory is being built.</p></div>`; return; }
  const wrap = document.createElement('div'); wrap.className = 'page wide'; main.append(wrap);
  return mountLab(wrap, lab);
}

function videosView(main, filter = '') {
  const q = (filter || '').toLowerCase();
  const rows = RESOURCES.sections.filter(s => !q || (s.topic + ' ' + s.id + ' ' + s.keywords).toLowerCase().includes(q));
  const groups = [['Signature Labs', RESOURCES.labs.map(r => ({ id: 'Lab ' + r.num, topic: r.title, links: r.links }))], ['Orientation', RESOURCES.orientation], ['Learning Engines', RESOURCES.engines], ['Assessment', RESOURCES.assessment], ['Reference', RESOURCES.reference]];
  const linkRow = (id, title, links, pw) => `<tr><td>${esc(id)}</td><td>${esc(title)} ${pw ? pathwayBadge(pw) : ''}</td><td>${extLink(links.khan, 'Khan', 'vbtn khan')}</td><td>${extLink(links.oct, 'OCT', 'vbtn oct')}</td><td>${extLink(links.yt, 'YouTube', 'vbtn yt')}</td></tr>`;
  main.innerHTML = `<div class="page"><h1>${tt('videos.title')}</h1>
    <p class="notice">${tt('videos.note')} ${tt('videos.english')}</p>
    <p class="hint">Source: ${esc(RESOURCES.source)} (${esc(RESOURCES.built)}) · ${RESOURCES.counts.rows} rows · ${RESOURCES.counts.links} links.</p>
    <label class="sel">${tt('videos.filter')} <input id="vf" value="${esc(filter)}" type="search"></label>
    <div class="tablewrap"><table class="vtable"><thead><tr><th>#</th><th>Topic</th><th>${tt('videos.khan')}</th><th>${tt('videos.oct')}</th><th>${tt('videos.yt')}</th></tr></thead>
    <tbody>${UNITS.map(u => { const rs = rows.filter(r => r.unit === u.num); return rs.length ? `<tr class="grp"><th colspan="5">${tt('unit.title', { n: u.num })} · ${esc(u.title)}</th></tr>` + rs.map(s => linkRow(s.id, s.topic, s.links, s.pathway)).join('') : ''; }).join('')}
    ${q ? '' : groups.map(([g, items]) => `<tr class="grp"><th colspan="5">${esc(g)}</th></tr>` + items.map(r => linkRow(r.id ?? r.num, r.topic ?? r.title, r.links)).join('')).join('')}</tbody></table></div>
    <h2>${tt('videos.anchors')}</h2><ul>${RESOURCES.anchors.map(a => `<li>${extLink(a.url, esc(a.title))} — ${esc(a.use)}</li>`).join('')}</ul></div>`;
  const vf = main.querySelector('#vf'); let tm;
  vf.oninput = () => { clearTimeout(tm); tm = setTimeout(() => { history.replaceState({ noFocus: true }, '', '#/videos/' + encodeURIComponent(vf.value)); videosView(main, vf.value); const n = main.querySelector('#vf'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 250); };
}

function settings(main) {
  const s = store.get().settings;
  const v = voiceFor();
  main.innerHTML = `<div class="page narrow"><h1>${tt('set.title')}</h1>
    <div class="card form">
      <label>${tt('lang.label')} <select id="s-lang">${LANGS.map(l => `<option value="${l.code}" ${l.code === s.lang ? 'selected' : ''}>${esc(l.native)} — ${esc(l.name)}</option>`).join('')}</select></label>
      <label>${tt('path.label')} <select id="s-pw">${['core', 'honors', 'advanced'].map(p => `<option value="${p}" ${s.pathway === p ? 'selected' : ''}>${tt('path.' + p)}</option>`).join('')}</select></label>
      <label>${tt('set.graphics')} <select id="s-gfx">${['high', 'medium', 'low'].map(g => `<option value="${g}" ${s.graphics === g ? 'selected' : ''}>${tt('set.graphics.' + g)}</option>`).join('')}</select></label>
      <label>${tt('set.motion')} <select id="s-rm"><option value="system" ${s.reducedMotion == null ? 'selected' : ''}>${tt('set.motion.system')}</option><option value="on" ${s.reducedMotion === true ? 'selected' : ''}>${tt('set.motion.on')}</option><option value="off" ${s.reducedMotion === false ? 'selected' : ''}>${tt('set.motion.off')}</option></select></label>
      <label><input type="checkbox" id="s-hc" ${s.contrast === 'high' ? 'checked' : ''}> ${tt('set.contrast')}</label>
      <label>${tt('set.text')} <input type="range" id="s-fs" min="0.85" max="1.5" step="0.05" value="${s.fontScale || 1}"></label>
      <p>${tt('set.narration')}: ${v ? esc(t('set.narration.ok', { v: v.name })) : tt('set.narration.none')}</p>
    </div>
    <div class="card"><h2>${tt('set.privacy')}</h2><p>${tt('set.privacy.d')}</p>
      <div class="row"><button class="btn" id="s-exp">⬇ ${tt('set.export')}</button><label class="btn">⬆ ${tt('set.import')}<input type="file" id="s-imp" accept="application/json" hidden></label><button class="btn danger" id="s-reset">${tt('set.reset')}</button></div></div>
  </div>`;
  const $ = q => main.querySelector(q);
  const set = (fn, rerender = true) => { store.update(st => fn(st.settings)); if (rerender) window.__byrdway.route(); };
  $('#s-lang').onchange = e => set(x => { x.lang = e.target.value; });
  $('#s-pw').onchange = e => set(x => { x.pathway = e.target.value; }, false);
  $('#s-gfx').onchange = e => set(x => { x.graphics = e.target.value; }, false);
  $('#s-rm').onchange = e => set(x => { x.reducedMotion = e.target.value === 'system' ? null : e.target.value === 'on'; });
  $('#s-hc').onchange = e => set(x => { x.contrast = e.target.checked ? 'high' : 'normal'; });
  $('#s-fs').onchange = e => set(x => { x.fontScale = +e.target.value; });
  $('#s-exp').onclick = () => download('byrdway-physics-progress.json', store.exportJSON(), 'application/json');
  $('#s-imp').onchange = async e => { try { store.importJSON(await e.target.files[0].text()); toast(t('set.imported')); window.__byrdway.route(); } catch { toast(t('set.importfail')); } };
  $('#s-reset').onclick = () => { if (confirm(t('set.reset.confirm'))) { store.resetAll(); window.__byrdway.route(); } };
}
