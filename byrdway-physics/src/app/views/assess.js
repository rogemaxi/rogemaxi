// Assessment and Mastery Center: adaptive readiness diagnostic + learning plan, five mastery levels (Level 4
// includes a DOK 4 performance task with a rubric), unit assessments, and the Core and Honors finals.
// Algorithms are documented in docs/ASSESSMENT.md. Scores are practice estimates, not validated test scores.
import { t, localize } from '../i18n.js';
import { esc, L, tt, pathwayBadge } from '../ui.js';
import * as store from '../store.js';
import { UNITS, SECTIONS, findSection, findUnit } from '../../data/curriculum/index.js';
import { ITEMS, TASKS } from '../../data/bank/index.js';
import { runQuiz, quizSummary } from '../quiz.js';
import { shuffle, advancedUnits, nextDiagnosticItem, buildPlan, levelItems, finalItems } from '../../engines/assess.js';
const CTX = { items: ITEMS, units: UNITS, sections: SECTIONS };

const locItem = it => ({ ...it, ...localize('bank.' + it.id, it).value, unit: it.unit, answer: it.answer, calc: it.calc, correct: it.correct, kind: it.kind });
const ADV_UNITS = advancedUnits(UNITS);
const pct = a => Math.round(100 * a.score / a.total);
const bestOf = arr => (arr?.length ? Math.max(...arr.map(pct)) + '%' : '—');

export function renderAssess(main, name, rest = []) {
  const page = document.createElement('div'); page.className = 'page'; main.innerHTML = ''; main.append(page);
  if (name === 'diagnostic') return rest[0] === 'plan' ? planView(page) : diagnostic(page);
  if (name === 'mastery') return level(page, +rest[0] || 1);
  if (name === 'final') return final(page, rest[0] === 'honors' ? 'honors' : 'core');
  if (rest[0] === 'unit') return unitTest(page, +rest[1] || 1);
  return hub(page);
}

function hub(page) {
  const st = store.get();
  page.innerHTML = `<h1>${tt('assess.title')}</h1><p class="hint">${tt('assess.note')}</p>
    <div class="card"><h2>${tt('assess.diag')}</h2><p>${tt('assess.diag.d', { n: ITEMS.length })}</p>
      <a class="btn gold" href="#/diagnostic">${st.diagnostic?.finished ? tt('assess.retake') : tt('assess.start')}</a> ${st.diagnostic?.finished ? `<a class="btn" href="#/diagnostic/plan">${tt('diag.plan')}</a>` : ''}</div>
    <div class="card"><h2>${tt('assess.levels')}</h2><div class="lvgrid">${[1, 2, 3, 4, 5].map(n => `<a class="lv" href="#/mastery/${n}"><b>L${n}</b><span>${tt('level.' + n)}</span><span class="hint">${tt('level.' + n + '.d')}</span><em>${tt('assess.best', { s: bestOf(st.mastery?.[n]?.attempts) })}</em></a>`).join('')}</div></div>
    <div class="card"><h2>${tt('assess.finals')}</h2><div class="row">
      <a class="btn gold" href="#/final/core">${tt('assess.final.core')} · ${bestOf(st.finals?.core)}</a>
      <a class="btn gold" href="#/final/honors">${tt('assess.final.honors')} · ${bestOf(st.finals?.honors)}</a></div></div>
    <div class="card"><h2>${tt('assess.unit')}</h2><div class="labchips">${UNITS.map(u => `<a class="chip" href="#/assess/unit/${u.num}">${u.num}. ${L(localize('unit.' + u.num, { x: u.title }).value.x)}</a>`).join('')}</div></div>`;
}

// ---------- adaptive diagnostic (logic in src/engines/assess.js) ----------
function diagnostic(page) {
  page.innerHTML = `<h1>${tt('diag.title')}</h1><p>${tt('diag.intro')}</p><p class="hint">${tt('assess.note')}</p><button class="btn gold" id="go">${tt('diag.begin')}</button><div id="qz"></div>`;
  page.querySelector('#go').onclick = () => {
    page.querySelector('#go').remove();
    const order = shuffle(UNITS.map(u => u.num));
    runQuiz(page.querySelector('#qz'), {
      title: t('diag.title'), total: order.length,
      next: h => { const it = nextDiagnosticItem(h, order, ITEMS); return it && locItem(it); },
      onDone: h => {
        const plan = buildPlan(h, CTX);
        store.update(s => { s.diagnostic = { finished: true, at: new Date().toISOString(), answers: h.map(x => ({ id: x.item.id, ok: x.ok, honors: !!x.item.honors, level: x.item.level, unit: x.item.unit })), plan }; });
        planView(page);
      },
    });
  };
}
function planView(page) {
  const d = store.get().diagnostic;
  if (!d?.plan) return diagnostic(page);
  const p = d.plan, n = d.answers.length, ok = d.answers.filter(a => a.ok).length;
  const link = id => { const s = findSection(id); return `<li><a href="#/section/${id}"><span class="secnum">${esc(id)}</span> ${esc(s?.title || '')}</a> ${s ? pathwayBadge(s.pathway) : ''}</li>`; };
  page.innerHTML = `<h1>${tt('diag.plan')}</h1><p>${tt('dash.diag.result', { pct: Math.round(100 * ok / n), n })}</p><p class="hint">${tt('assess.note')}</p>
    <div class="grid2"><div class="card"><h2>${tt('diag.strengths')}</h2>${p.strengths.length ? `<ul>${p.strengths.map(u => `<li>${u}. ${esc(findUnit(u).title)}</li>`).join('')}</ul>` : `<p>${tt('diag.none')}</p>`}</div>
    <div class="card"><h2>${tt('diag.weak')}</h2>${p.weak.length ? `<ul>${p.weak.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : `<p>${tt('diag.none')}</p>`}</div></div>
    <div class="card"><h2>${tt('diag.gaps')}</h2>${p.gaps.length ? `<ul>${p.gaps.map(g => `<li>${esc(g)}</li>`).join('')}</ul>` : `<p>${tt('diag.none')}</p>`}</div>
    <div class="card"><h2>${tt('diag.recommend')}</h2>${p.recommend.length ? `<ol>${p.recommend.map(link).join('')}</ol>` : `<p>${tt('diag.none')}</p>`}</div>
    <div class="card"><h2>${tt('diag.practice')}</h2><div class="labchips">${(p.weakUnits || []).map(u => `<a class="chip" href="#/engine/test/${u}">✅ ${tt('engine.test')} · ${u}</a><a class="chip" href="#/engine/flash/${u}">🗂️ ${tt('engine.flash')} · ${u}</a>`).join('') || tt('diag.none')}</div></div>
    <div class="card"><h2>${tt('diag.method')}</h2><p>${tt('diag.method.d')}</p></div>
    <a class="btn" href="#/diagnostic">${tt('assess.retake')}</a>`;
}

// ---------- mastery levels ----------
function level(page, n) {
  const items = levelItems(n, CTX);
  page.innerHTML = `<p class="crumb"><a href="#/assess">${tt('assess.title')}</a></p><h1>${tt('level.' + n)}</h1><p class="lead">${tt('level.' + n + '.d')}</p><p class="hint">${tt('assess.note')}</p><div id="qz"></div>${n === 4 ? '<div id="task"></div>' : ''}`;
  if (n === 4) performanceTask(page.querySelector('#task'));
  runQuiz(page.querySelector('#qz'), {
    title: t('level.' + n), total: items.length, next: h => (items[h.length] ? locItem(items[h.length]) : null),
    onDone: h => {
      const score = h.filter(x => x.ok).length;
      store.update(s => { ((s.mastery[n] ||= {}).attempts ||= []).push({ at: new Date().toISOString(), score, total: h.length }); });
      page.querySelector('#qz').innerHTML = quizSummary(h) + `<a class="btn gold" href="#/mastery/${n}">${tt('assess.retake')}</a> ${n < 5 ? `<a class="btn" href="#/mastery/${n + 1}">${tt('level.' + (n + 1))} →</a>` : ''}`;
    },
  });
}
function performanceTask(box, id) {
  const tasks = TASKS.filter(x => !ADV_UNITS.has(x.unit));
  const T = tasks.find(x => x.id === id) || tasks[0];
  if (!T) return;
  const c = localize('bank.' + T.id, T).value;
  const saved = store.get().mastery?.[4]?.tasks?.[T.id] || {};
  box.innerHTML = `<div class="card task"><h2>${tt('task.title')} · ${L(c.title)}</h2>
    <label class="sel">${tt('task.pick')} <select id="tsel">${tasks.map(x => `<option value="${x.id}" ${x.id === T.id ? 'selected' : ''}>${x.unit}. ${esc(x.title)}</option>`).join('')}</select></label>
    <p>${L(c.scenario)}</p>
    ${T.data ? `<div class="tablewrap"><table><thead><tr>${T.data.head.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${T.data.rows.map(r => `<tr>${r.map(x => `<td>${esc(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : ''}
    <ol>${c.tasks.map(x => `<li>${L(x)}</li>`).join('')}</ol>
    <label>${tt('task.response')}<textarea id="tresp" rows="8">${esc(saved.response || '')}</textarea></label>
    <h3>${tt('task.rubric')}</h3><p class="hint">${tt('task.rubric.d')}</p>
    <div class="tablewrap"><table class="rubric"><tbody>${c.rubric.map((r, i) => `<tr><th>${L(r[0])}</th>${[1, 2, 3, 4].map(k => `<td><label><input type="radio" name="rb${i}" value="${5 - k}" ${saved.scores?.[i] === 5 - k ? 'checked' : ''}> ${L(r[k])}</label></td>`).join('')}</tr>`).join('')}</tbody></table></div>
    <button class="btn gold" id="tsave">${tt('task.save')}</button><div class="fb" id="tfb"></div>
    <details><summary>${tt('task.exemplar')}</summary><p>${L(c.exemplar)}</p></details></div>`;
  box.querySelector('#tsel').onchange = e => performanceTask(box, e.target.value);
  box.querySelector('#tsave').onclick = () => {
    const scores = c.rubric.map((_, i) => +(box.querySelector(`input[name=rb${i}]:checked`)?.value || 0));
    store.update(s => { const m = (s.mastery[4] ||= {}); (m.tasks ||= {})[T.id] = { response: box.querySelector('#tresp').value, scores, at: new Date().toISOString() }; });
    const done = scores.filter(Boolean);
    box.querySelector('#tfb').innerHTML = done.length === scores.length ? tt('task.saved', { s: done.reduce((a, b) => a + b, 0), n: scores.length * 4 }) : tt('task.partial');
  };
}

// ---------- unit tests and finals ----------
function unitTest(page, n) {
  const u = findUnit(n), items = shuffle(ITEMS.filter(it => it.unit === n));
  page.innerHTML = `<p class="crumb"><a href="#/assess">${tt('assess.title')}</a></p><h1>${tt('assess.unit')} · ${u.num}. ${L(localize('unit.' + u.num, { x: u.title }).value.x)}</h1><div id="qz"></div>`;
  runQuiz(page.querySelector('#qz'), {
    title: `${u.num}. ${u.title}`, total: items.length, next: h => (items[h.length] ? locItem(items[h.length]) : null),
    onDone: h => {
      const weak = [...new Set(h.filter(x => !x.ok).map(x => x.item.section))];
      page.querySelector('#qz').innerHTML = quizSummary(h, weak.length ? `<p><strong>${tt('diag.recommend')}:</strong> ${weak.map(id => `<a href="#/section/${id}">${esc(id)}</a>`).join(' · ')}</p>` : '') + `<a class="btn gold" href="#/assess/unit/${n}">${tt('assess.retake')}</a>`;
    },
  });
}
function final(page, kind) {
  const items = finalItems(kind, CTX);
  page.innerHTML = `<p class="crumb"><a href="#/assess">${tt('assess.title')}</a></p><h1>${tt('assess.final.' + kind)}</h1><p class="lead">${tt('final.' + kind + '.d', { n: items.length })}</p><p class="hint">${tt('assess.note')}</p><button class="btn gold" id="go">${tt('assess.start')}</button><div id="qz"></div>`;
  page.querySelector('#go').onclick = () => {
    page.querySelector('#go').remove();
    runQuiz(page.querySelector('#qz'), {
      title: t('assess.final.' + kind), total: items.length, next: h => (items[h.length] ? locItem(items[h.length]) : null),
      onDone: h => {
        const score = h.filter(x => x.ok).length;
        store.update(s => { (s.finals[kind] ||= []).push({ at: new Date().toISOString(), score, total: h.length }); });
        const byUnit = UNITS.map(u => [u, h.filter(x => x.item.unit === u.num)]).filter(([, hs]) => hs.length);
        page.querySelector('#qz').innerHTML = quizSummary(h, `<div class="tablewrap"><table><tbody>${byUnit.map(([u, hs]) => `<tr><td>${u.num}. ${esc(u.title)}</td><td>${hs.filter(x => x.ok).length}/${hs.length}</td></tr>`).join('')}</tbody></table></div>`);
      },
    });
  };
}
