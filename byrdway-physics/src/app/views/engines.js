// The ten learning engines. Every engine is generated from the authored curriculum (formulas, vocabulary,
// misconceptions, blueprints, bridges, practice items) or from the executable formula catalog, so nothing here
// is placeholder text. Routes: #/engines, #/engine/<key>/<arg>.
import { t, localize } from '../i18n.js';
import { esc, L, P, tt, fmt, parseNumber, toast, extLink } from '../ui.js';
import * as store from '../store.js';
import { UNITS, SECTIONS, findUnit, findSection } from '../../data/curriculum/index.js';
import { LABS, findLab } from '../../lab/labs/index.js';
import { FORMULAS, findFormula } from '../../data/formulas.js';
import { solve, checkDimensions, dimString } from '../../engines/formula.js';
import { diagnose, ERROR_KEYS } from '../../engines/errors.js';
import { exactAnswer, sectionDone } from './section.js';
import { runQuiz, quizSummary, shuffle } from '../quiz.js';

export const ENGINES = ['cheat', 'blueprint', 'flash', 'test', 'labs', 'feynman', 'support', 'tutor', 'formula', 'detective'];
const ICON = { cheat: '⚡', blueprint: '🧭', flash: '🗂️', test: '✅', labs: '🧪', feynman: '🔬', support: '🌉', tutor: '🤖', formula: '🧮', detective: '🔎' };

export function enginesHub(main) {
  main.innerHTML = `<div class="page"><h1>${tt('engines.title')}</h1>
    <div class="enggrid">${ENGINES.map(k => `<a class="engtile" href="#/engine/${k}"><span class="engicon" aria-hidden="true">${ICON[k]}</span><b>${tt('engine.' + k)}</b><span class="hint">${tt('engine.' + k + '.d')}</span></a>`).join('')}</div></div>`;
}

export function renderEngine(main, key, args = []) {
  const fn = { cheat, blueprint, flash, test, labs, feynman, support, tutor, formula, detective }[key];
  if (!fn) return enginesHub(main);
  const page = document.createElement('div'); page.className = 'page'; main.innerHTML = ''; main.append(page);
  page.insertAdjacentHTML('beforeend', `<p class="crumb"><a href="#/engines">${tt('engines.title')}</a></p><h1>${ICON[key]} ${tt('engine.' + key)}</h1><p class="lead">${tt('engine.' + key + '.d')}</p>`);
  const body = document.createElement('div'); page.append(body);
  fn(body, ...args);
}

// ---------- shared helpers ----------
const unitLoc = u => localize('unit.' + u.num, { x: u.title, bridges: u.bridges, blueprint: u.blueprint }).value;
const unitTitle = u => L(unitLoc(u).x);
const authored = u => u.sections.filter(s => s.content);
const loc = s => localize(s.id, { title: s.title, ...s.content }).value;
function unitPicker(engine, current) {
  return `<label class="sel">${tt('flash.unit')} <select data-unitpick="${engine}">${UNITS.map(u => `<option value="${u.num}" ${u.num === current ? 'selected' : ''}>${u.num}. ${esc(u.title)}</option>`).join('')}</select></label>`;
}
function wirePicker(root) {
  root.querySelectorAll('[data-unitpick]').forEach(s => s.onchange = () => { location.hash = `#/engine/${s.dataset.unitpick}/${s.value}`; });
  root.querySelectorAll('[data-secpick]').forEach(s => s.onchange = () => { location.hash = `#/engine/${s.dataset.secpick}/${s.value}`; });
}
function sectionPicker(engine, current) {
  return `<label class="sel">${tt('tutor.pick')} <select data-secpick="${engine}">${SECTIONS.filter(s => s.content).map(s => `<option value="${s.id}" ${s.id === current ? 'selected' : ''}>${esc(s.id)} ${esc(s.title)}</option>`).join('')}</select></label>`;
}
const defaultUnit = () => {
  const st = store.get(); const s = SECTIONS.find(x => st.sections[x.id]?.visited && !st.sections[x.id]?.done) || SECTIONS[0];
  return s.unit;
};

// ---------- 1. Cheat sheets ----------
function cheat(root, n = defaultUnit()) {
  const u = findUnit(n) || UNITS[0];
  const secs = authored(u).map(s => ({ s, c: loc(s) }));
  root.innerHTML = `<div class="noprint">${unitPicker('cheat', u.num)} <button class="btn" id="pr">🖨 ${tt('eng.print')}</button></div>
    <div class="cheatsheet"><h2>${tt('unit.title', { n: u.num })} · ${unitTitle(u)}</h2>
    ${secs.map(({ s, c }) => `<section class="cheat"><h3><span class="secnum">${esc(s.id)}</span> ${L(c.title)}</h3>
      ${c.formulas.map(f => `<div class="cformula"><code>${L(f.eq)}</code><span class="hint">${L(f.when)}</span>
        <table class="vars">${f.vars.map(v => `<tr><td><code>${L(v[0])}</code></td><td>${L(v[1])}</td><td>${L(v[2])}</td></tr>`).join('')}</table></div>`).join('')}
      <p class="hint"><strong>${tt('sec.units')}:</strong> ${L(c.units)}</p>
      <ul class="traps">${c.misconceptions.map(m => `<li>⚠ ${L(m.right)}</li>`).join('')}</ul></section>`).join('')}
    ${u.blueprint.length ? `<section class="cheat"><h3>${tt('eng.traps')}</h3><ul class="traps">${unitLoc(u).blueprint.map(b => `<li>⚠ ${L(b.trap)}</li>`).join('')}</ul></section>` : ''}
    ${secs.length ? '' : `<p class="hint">${tt('eng.empty')}</p>`}</div>`;
  root.querySelector('#pr').onclick = () => window.print();
  wirePicker(root);
}

// ---------- 2. Blueprints ----------
function blueprint(root, n = defaultUnit()) {
  const u = findUnit(n) || UNITS[0];
  const bp = unitLoc(u).blueprint;
  root.innerHTML = `${unitPicker('blueprint', u.num)}
    <div class="tablewrap"><table class="bp"><thead><tr><th>${tt('bp.see')}</th><th>${tt('bp.think')}</th><th>${tt('bp.tool')}</th><th>${tt('bp.trap')}</th></tr></thead>
    <tbody>${bp.map(b => `<tr><td>${L(b.see)}</td><td>${L(b.think)}</td><td><code>${L(b.tool)}</code></td><td>⚠ ${L(b.trap)}</td></tr>`).join('')}</tbody></table></div>
    ${bp.length >= 2 ? `<div class="card"><h2>${tt('bp.drill')}</h2><div id="drill"></div></div>` : `<p class="hint">${tt('eng.empty')}</p>`}`;
  wirePicker(root);
  const box = root.querySelector('#drill'); if (!box) return;
  let score = 0, tries = 0;
  const ask = () => {
    const i = Math.floor(Math.random() * bp.length), order = shuffle(bp.map((_, k) => k), Date.now() + i);
    box.innerHTML = `<p><strong>${tt('bp.see')}:</strong> ${L(bp[i].see)}</p><p>${tt('bp.which')}</p>
      <div class="choices">${order.map(k => `<button class="btn ghost choice" data-k="${k}">${L(bp[k].tool)}</button>`).join('')}</div><div class="fb" aria-live="polite"></div><p class="hint">${tt('bp.score', { s: score, n: tries })}</p>`;
    box.querySelectorAll('[data-k]').forEach(b => b.onclick = () => {
      tries++; const ok = +b.dataset.k === i; if (ok) score++;
      box.querySelector('.fb').innerHTML = `${ok ? `<span class="good">✓ ${tt('q.correct')}</span>` : `<span class="bad">${tt('q.wrong')}</span>`} ${L(bp[i].think)} — ⚠ ${L(bp[i].trap)} <button class="btn" id="again">${tt('assess.nextq')}</button>`;
      box.querySelectorAll('[data-k]').forEach(x => (x.disabled = true));
      box.querySelector('#again').onclick = ask;
    });
  };
  ask();
}

// ---------- 3. Flashcards (Leitner boxes 1–5) ----------
export function buildCards(u) {
  const cards = [];
  for (const s of authored(u)) {
    const c = loc(s), id = s.id;
    c.vocab.forEach((v, i) => cards.push({ id: `${id}:v${i}`, type: 'vocab', front: v[0], back: v[1] }));
    c.formulas.forEach((f, i) => cards.push({ id: `${id}:f${i}`, type: 'formula', front: f.when, back: f.eq }));
    c.misconceptions.forEach((m, i) => cards.push({ id: `${id}:m${i}`, type: 'trap', front: m.wrong, back: m.right }));
    cards.push({ id: `${id}:c`, type: 'concept', front: c.predict.prompt, back: c.predict.why });
    if (s.content.visual?.kind === 'plot') cards.push({ id: `${id}:g`, type: 'graph', front: c.visual.title || c.title, back: c.explain[0] });
    if (s.pathway !== 'Core') cards.push({ id: `${id}:h`, type: 'honors', front: c.honors.prompt, back: c.honors.solution });
  }
  return cards;
}
function flash(root, n = defaultUnit()) {
  const u = findUnit(n) || UNITS[0];
  const cards = buildCards(u);
  const box = id => store.get().cards[id] || 1;
  const queue = () => cards.slice().sort((a, b) => box(a.id) - box(b.id));
  let q = queue(), i = 0, flipped = false;
  const show = () => {
    if (!cards.length) { root.innerHTML = unitPicker('flash', u.num) + `<p class="hint">${tt('eng.empty')}</p>`; wirePicker(root); return; }
    const c = q[i % q.length], counts = [1, 2, 3, 4, 5].map(b => cards.filter(x => box(x.id) === b).length);
    root.innerHTML = `${unitPicker('flash', u.num)}
      <p class="hint">${tt('flash.due', { n: cards.length })} · ${counts.map((k, b) => `${tt('flash.box', { n: b + 1 })}: ${k}`).join(' · ')}</p>
      <button class="flashcard ${flipped ? 'flipped' : ''}" id="fc" aria-live="polite" aria-label="${tt('flash.flip')}">
        <span class="ftype">${tt('flash.type.' + c.type)} · ${tt('flash.box', { n: box(c.id) })}</span>
        <span class="fface">${flipped ? L(c.back) : L(c.front)}</span><span class="hint">${tt('flash.flip')}</span></button>
      <div class="row"><button class="btn" id="miss" ${flipped ? '' : 'disabled'}>↺ ${tt('flash.missed')}</button><button class="btn gold" id="knew" ${flipped ? '' : 'disabled'}>✓ ${tt('flash.knew')}</button></div>`;
    wirePicker(root);
    const fc = root.querySelector('#fc'); fc.onclick = () => { flipped = !flipped; show(); root.querySelector('#fc').focus(); };
    const rate = up => { store.update(s => { s.cards[c.id] = up ? Math.min(5, box(c.id) + 1) : 1; }); flipped = false; i++; if (i % q.length === 0) { q = queue(); i = 0; } show(); root.querySelector('#fc').focus(); };
    root.querySelector('#knew').onclick = () => rate(true);
    root.querySelector('#miss').onclick = () => rate(false);
  };
  show();
}

// ---------- 4. Test Me ----------
export function unitItems(u) {
  const out = [];
  for (const s of authored(u)) {
    const c = loc(s);
    [...s.content.guided.map((q, k) => [q, c.guided[k]]), ...s.content.practice.map((q, k) => [q, c.practice[k]])]
      .filter(([q]) => q.kind !== 'self')
      .forEach(([q, lq]) => out.push({ ...q, key: `${s.id}/${q.id}`, section: s.id, q: lq.q, choices: lq.choices, solution: lq.solution }));
  }
  return out;
}
function test(root, n = defaultUnit()) {
  const u = findUnit(n) || UNITS[0];
  const items = shuffle(unitItems(u)).slice(0, 10);
  root.innerHTML = `${unitPicker('test', u.num)}<div id="qz"></div>`;
  wirePicker(root);
  if (!items.length) { root.querySelector('#qz').innerHTML = `<p class="hint">${tt('eng.empty')}</p>`; return; }
  const qz = root.querySelector('#qz');
  runQuiz(qz, {
    title: `${t('unit.title', { n: u.num })} · ${u.title}`, total: items.length,
    next: h => items[h.length] || null,
    onDone: h => {
      const weak = [...new Set(h.filter(x => !x.ok).map(x => x.item.section))];
      qz.innerHTML = quizSummary(h, weak.length ? `<p><strong>${tt('diag.recommend')}:</strong> ${weak.map(id => `<a href="#/section/${id}">${esc(id)}</a>`).join(' · ')}</p>` : '') + `<button class="btn gold" id="again">${tt('assess.retake')}</button>`;
      qz.querySelector('#again').onclick = () => test(root, u.num);
    },
  });
}

// ---------- 5. Reality Labs ----------
function labs(root) {
  root.innerHTML = `<div class="labchips">${LABS.map(l => `<a class="chip" href="#/lab/${l.num}">${l.num}. ${L(localize('lab.' + l.num, { x: l.text.title }).value.x)}</a>`).join('')}</div>
    <p><a class="btn gold" href="#/labs">${tt('labs.title')} →</a></p>`;
}

// ---------- 6. Feynman Discovery Studio ----------
const FSTEPS = ['observe', 'predict', 'experiment', 'measure', 'model', 'calculate', 'explain', 'challenge', 'master'];
function feynman(root, id) {
  const sec = findSection(id) || SECTIONS.find(s => s.content);
  const c = loc(sec), raw = sec.content, u = findUnit(sec.unit), lab = u.lab ? findLab(u.lab) : null;
  const st = store.get().sections[sec.id]?.feynman || {};
  const save = (k, v) => store.update(s => { const x = (s.sections[sec.id] ||= { practice: {} }); (x.feynman ||= {})[k] = v; });
  const body = {
    observe: `<p class="lead">${L(c.intro)}</p><p>${L(c.observe)}</p>`,
    predict: `<p>${L(c.predict.prompt)}</p><div class="choices">${c.predict.choices.map((ch, k) => `<label class="choice"><input type="radio" name="fp" value="${k}" ${st.predict === k ? 'checked' : ''}> ${L(ch)}</label>`).join('')}</div><div class="fb" id="fpfb">${st.predict != null ? `${st.predict === raw.predict.correct ? '<span class="good">✓</span>' : '<span class="warn">≠</span>'} ${L(c.predict.why)}` : ''}</div>`,
    experiment: `<p>${L(c.investigate)}</p>${lab ? `<a class="btn gold" href="#/lab/${lab.num}">🧪 ${L(localize('lab.' + lab.num, { x: lab.text.title }).value.x)}</a>` : ''}`,
    measure: `<label>${tt('feyn.measure')}<textarea data-f="measure" rows="3">${esc(st.measure || '')}</textarea></label>`,
    model: c.formulas.map(f => `<p><code>${L(f.eq)}</code> — ${L(f.when)}</p>`).join('') + (c.derivation ? `<details><summary>${tt('formula.derive')}</summary>${[].concat(c.derivation).map(d => `<p>${L(d)}</p>`).join('')}</details>` : ''),
    calculate: `<p><strong>${L(c.example.problem)}</strong></p><ol>${c.example.steps.map(s => `<li>${L(s)}</li>`).join('')}</ol><p>→ ${L(c.example.answer)}</p>`,
    explain: `<p>${tt('feyn.explain')}</p><textarea data-f="explain" rows="5">${esc(st.explain || '')}</textarea><button class="btn" id="fx">${tt('eng.check')}</button><div class="fb" id="fxfb"></div>`,
    challenge: `<p>${L(c.honors.prompt)}</p><details><summary>${tt('q.solution')}</summary><p>${L(c.honors.solution)}</p></details>`,
    master: `<ul class="checks">${c.mastery.map((m, k) => `<li><label><input type="checkbox" data-m="${k}" ${st['m' + k] ? 'checked' : ''}> ${L(m)}</label></li>`).join('')}</ul><a class="btn" href="#/section/${sec.id}">${tt('dash.continue')} → ${esc(sec.id)}</a>`,
  };
  root.innerHTML = `${sectionPicker('feynman', sec.id)}<p class="hint">${tt('feynman.d')}</p>
    <ol class="fsteps">${FSTEPS.map((k, i) => `<li class="card fstep"><h2><span class="secnum">${i + 1}</span> ${tt('feynman.step.' + k)}</h2>${body[k]}</li>`).join('')}</ol>`;
  wirePicker(root);
  root.querySelectorAll('input[name=fp]').forEach(r => r.onchange = () => { save('predict', +r.value); feynman(root, sec.id); });
  root.querySelectorAll('textarea[data-f]').forEach(a => a.onchange = () => save(a.dataset.f, a.value));
  root.querySelectorAll('[data-m]').forEach(b => b.onchange = () => save('m' + b.dataset.m, b.checked));
  root.querySelector('#fx').onclick = () => {
    const txt = root.querySelector('textarea[data-f=explain]').value.toLowerCase(); save('explain', txt);
    const words = raw.explainWords || [], keys = c.explainKeys || [];
    const hit = words.map(ws => ws.some(w => txt.includes(String(w).toLowerCase())));
    root.querySelector('#fxfb').innerHTML = `<ul>${keys.map((k, i) => `<li class="${hit[i] ? 'good' : 'warn'}">${hit[i] ? '✓' : '○'} ${L(k)}</li>`).join('')}</ul><p class="hint">${tt('feyn.kwnote')}</p>`;
  };
}

// ---------- 7. Interactive Support ----------
function support(root, n = defaultUnit()) {
  const u = findUnit(n) || UNITS[0];
  const plan = store.get().diagnostic?.plan;
  const br = unitLoc(u).bridges;
  root.innerHTML = `${unitPicker('support', u.num)}
    <div class="card"><h2>${tt('support.bridges')}</h2>${br.length ? br.map(b => `<div class="bridge"><p><strong>${tt('support.gap')}:</strong> ${L(b.gap)}</p><p><strong>${tt('support.bridge')}:</strong> ${L(b.bridge)}</p></div>`).join('') : `<p class="hint">${tt('eng.empty')}</p>`}</div>
    <div class="card"><h2>${tt('support.remediate')}</h2>${plan ? `<p><strong>${tt('diag.gaps')}:</strong> ${plan.gaps?.length ? plan.gaps.map(esc).join(', ') : tt('diag.none')}</p><p><strong>${tt('diag.recommend')}:</strong> ${plan.recommend.map(id => `<a href="#/section/${id}">${esc(id)}</a>`).join(' · ') || tt('diag.none')}</p>` : `<p>${tt('support.none')}</p><a class="btn" href="#/diagnostic">${tt('dash.diag.take')}</a>`}</div>
    <div class="card"><h2>${tt('ref.math')}</h2><p><a href="#/reference/math">${tt('ref.math')} →</a> · <a href="#/reference/si">${tt('ref.si')} →</a></p></div>`;
  wirePicker(root);
}

// ---------- 8. Tutor (offline guided, optional school endpoint) ----------
function tutor(root, id) {
  const sec = findSection(id) || SECTIONS.find(s => s.content);
  const c = loc(sec), raw = sec.content;
  const endpoint = store.get().settings.tutorEndpoint || '';
  const g = raw.guided[0], lg = c.guided[0];
  const steps = [
    `<p><strong>${tt('sec.objectives')}:</strong></p><ul>${c.objectives.map(o => `<li>${L(o)}</li>`).join('')}</ul><p>${tt('tutor.s.goal')}</p>`,
    `<p>${tt('tutor.s.predict')}</p><p><em>${L(c.predict.prompt)}</em></p><details><summary>${tt('tutor.s.reveal')}</summary><p>${L(c.predict.why)}</p></details>`,
    `<p>${tt('tutor.s.idea')}</p><p>${L(c.explain[0])}</p><p>${tt('tutor.s.restate')}</p>`,
    `<p>${tt('tutor.s.try')}</p><p><strong>${L(lg.q)}</strong></p>${(lg.hints || []).map((h, k) => `<details><summary>${tt('q.hint')} ${k + 1}</summary><p>💡 ${L(h)}</p></details>`).join('')}
      ${g.kind === 'num' ? `<div class="qrow"><input class="qin" id="ta" inputmode="decimal"><span class="unit">${esc(g.unit || '')}</span><button class="btn" id="tc">${tt('q.check')}</button></div><div class="fb" id="tfb"></div>` : ''}<details><summary>${tt('q.solution')}</summary><p>${L(lg.solution)}</p></details>`,
    `<p>${tt('tutor.s.trap')}</p>${c.misconceptions.map(m => `<p>✗ <s>${L(m.wrong)}</s><br>✓ ${L(m.right)}<br><span class="hint">${L(m.feedback)}</span></p>`).join('')}`,
    `<p>${tt('tutor.s.check')}</p><ul>${c.mastery.map(m => `<li>${L(m)}</li>`).join('')}</ul><a class="btn gold" href="#/section/${sec.id}">${esc(sec.id)} →</a>`,
  ];
  let k = 0;
  const prompt = t('tutor.prompt.text', { id: sec.id, title: sec.title, obj: raw.objectives.join('; ') });
  root.innerHTML = `${sectionPicker('tutor', sec.id)}
    <div class="card"><h2>${tt('tutor.offline')}</h2><p class="hint">${tt('tutor.offline.d')}</p><div id="tstep"></div>
      <div class="row"><button class="btn" id="tprev">←</button><button class="btn gold" id="tnext">${tt('tutor.next')} →</button></div></div>
    <div class="card"><h2>${tt('tutor.prompt')}</h2><p class="hint">${tt('tutor.prompt.d')}</p><textarea readonly rows="6" id="tp">${esc(prompt)}</textarea><button class="btn" id="tcopy">${tt('tutor.copy')}</button></div>
    <div class="card"><h2>${tt('tutor.cloud')}</h2><p class="hint">${tt('tutor.cloud.d')}</p>
      <label>${tt('tutor.endpoint')} <input id="tep" type="url" placeholder="https://" value="${esc(endpoint)}"></label><button class="btn" id="tsave">${tt('tutor.connect')}</button>
      ${endpoint ? `<label>${tt('tutor.ask')}<textarea id="tq" rows="3"></textarea></label><button class="btn gold" id="task">${tt('tutor.ask')}</button><div class="fb" id="tans" aria-live="polite"></div>` : `<p class="hint">${tt('tutor.cloud.none')}</p>`}</div>`;
  wirePicker(root);
  const showStep = () => {
    root.querySelector('#tstep').innerHTML = `<p class="hint">${k + 1} / ${steps.length}</p>${steps[k]}`;
    root.querySelector('#tprev').disabled = k === 0; root.querySelector('#tnext').disabled = k === steps.length - 1;
    const tc = root.querySelector('#tc');
    if (tc) tc.onclick = () => {
      const v = parseNumber(root.querySelector('#ta').value), ex = exactAnswer(g), fb = root.querySelector('#tfb');
      if (!Number.isFinite(v)) { fb.textContent = t('q.nan'); return; }
      const ok = Math.abs(v - ex) <= 0.025 * Math.abs(ex || 1), d = ok ? [] : diagnose(ex, v);
      fb.innerHTML = ok ? `<span class="good">✓ ${tt('q.correct')}</span>` : `<span class="bad">${tt('q.wrong')}</span> ${d.map(x => tt('err.' + x)).join(' ') || tt('tutor.s.hintfirst')}`;
    };
  };
  root.querySelector('#tprev').onclick = () => { k--; showStep(); };
  root.querySelector('#tnext').onclick = () => { k++; showStep(); };
  showStep();
  root.querySelector('#tcopy').onclick = async () => { try { await navigator.clipboard.writeText(prompt); toast(t('tutor.copied')); } catch { root.querySelector('#tp').select(); } };
  root.querySelector('#tsave').onclick = () => {
    const v = root.querySelector('#tep').value.trim();
    if (v && !/^https:\/\//i.test(v)) { toast(t('tutor.https')); return; }
    store.update(s => { s.settings.tutorEndpoint = v; }); tutor(root, sec.id);
  };
  const ask = root.querySelector('#task');
  if (ask) ask.onclick = async () => {
    const out = root.querySelector('#tans'); out.textContent = '…';
    try {
      // The school's service receives only the question and the section context; no credentials live in this file.
      const r = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ section: sec.id, title: sec.title, objectives: raw.objectives, question: root.querySelector('#tq').value, mode: 'socratic' }) });
      if (!r.ok) throw new Error(r.status);
      const j = await r.json().catch(() => null);
      out.innerHTML = esc(j?.reply ?? j?.text ?? JSON.stringify(j));
    } catch (e) { out.innerHTML = `<span class="bad">${tt('tutor.fail')}</span>`; }
  };
}

// ---------- 9. Formula Laboratory ----------
function formula(root, id = FORMULAS[0].id, target) {
  const f = findFormula(id) || FORMULAS[0];
  target = f.vars.some(v => v.s === target) ? target : f.vars[0].s;
  const known = f.vars.filter(v => v.s !== target);
  const dims = checkDimensions(f);
  const byUnit = UNITS.map(u => [u, FORMULAS.filter(x => x.unit === u.num)]).filter(([, xs]) => xs.length);
  root.innerHTML = `<div class="card form">
    <label>${tt('formula.pick')} <select id="fsel">${byUnit.map(([u, xs]) => `<optgroup label="${u.num}. ${esc(u.title)}">${xs.map(x => `<option value="${x.id}" ${x.id === f.id ? 'selected' : ''}>${esc(x.name)} — ${esc(x.eq)}</option>`).join('')}</optgroup>`).join('')}</select></label>
    <p class="bigeq"><code>${esc(f.eq)}</code></p>
    <label>${tt('formula.solvefor')} <select id="ftar">${f.vars.map(v => `<option value="${v.s}" ${v.s === target ? 'selected' : ''}>${esc(v.name)} (${esc(v.unit === 'none' ? '—' : v.unit)})</option>`).join('')}</select></label>
    <fieldset><legend>${tt('formula.known')}</legend>${known.map(v => `<label>${esc(v.name)} <input data-v="${v.s}" inputmode="decimal" value="${v.def ?? ''}"> <span class="unit">${esc(v.unit === 'none' ? '' : v.unit)}</span></label>`).join('')}</fieldset>
    <div class="fb" id="fres" aria-live="polite"></div>
    <p class="hint">${tt('formula.units')}: ${dims.ok ? tt('formula.units.ok', { dims: dims.lhs }) : '⚠'}</p></div>
    <div class="card"><h2 id="fexh"></h2><label>${tt('eng.vary')} <select id="fx">${known.filter(v => !v.def).map(v => `<option value="${v.s}">${esc(v.name)}</option>`).join('')}</select></label><div id="fplot"></div></div>`;
  const $ = q => root.querySelector(q);
  $('#fsel').onchange = e => formula(root, e.target.value);
  $('#ftar').onchange = e => formula(root, f.id, e.target.value);
  const read = () => Object.fromEntries(known.map(v => [v.s, parseNumber(root.querySelector(`[data-v="${v.s}"]`).value)]));
  const tv = f.vars.find(v => v.s === target);
  const compute = () => {
    const k = read();
    if (Object.values(k).some(x => !Number.isFinite(x))) { $('#fres').innerHTML = `<span class="hint">${tt('formula.enter')}</span>`; $('#fplot').innerHTML = ''; return; }
    const roots = solve(f, target, k).filter(r => !tv.pos || r > 0).filter(r => !tv.angle || (r >= 0 && r <= 180)).slice(0, 2);
    $('#fres').innerHTML = roots.length ? `<strong>${tt('formula.result')}:</strong> ${roots.map(r => `${esc(tv.name)} = <b>${fmt(r, 4)}</b> ${esc(tv.unit === 'none' ? '' : tv.unit)}`).join(` ${tt('eng.or')} `)}` : `<span class="warn">${tt('formula.nosol')}</span>`;
    plot(k);
  };
  const plot = k => {
    const xs = $('#fx').value; if (!xs) return;
    const xv = f.vars.find(v => v.s === xs);
    $('#fexh').textContent = t('formula.explore', { y: tv.name, x: xv.name });
    const x0 = Math.abs(k[xs]) || 1, pts = [];
    for (let i = 0; i <= 60; i++) {
      const x = xv.angle ? i * 1.5 : x0 * (0.1 + 1.9 * i / 60);
      const r = solve(f, target, { ...k, [xs]: x }).filter(r => !tv.pos || r > 0).filter(r => !tv.angle || (r >= 0 && r <= 180))[0];
      if (Number.isFinite(r)) pts.push([x, r]);
    }
    if (pts.length < 2) { $('#fplot').innerHTML = `<p class="hint">${tt('formula.nosol')}</p>`; return; }
    const W = 460, H = 240, pad = 44, xmin = Math.min(...pts.map(p => p[0])), xmax = Math.max(...pts.map(p => p[0]));
    let ymin = Math.min(0, ...pts.map(p => p[1])), ymax = Math.max(...pts.map(p => p[1])); if (ymax === ymin) ymax = ymin + 1;
    const X = x => pad + (x - xmin) / (xmax - xmin || 1) * (W - pad - 10), Y = y => H - pad + 10 - (y - ymin) / (ymax - ymin) * (H - pad - 10);
    $('#fplot').innerHTML = `<svg class="diagram" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t('formula.explore', { y: tv.name, x: xv.name }))}">
      <line x1="${pad}" y1="${Y(ymin)}" x2="${W - 10}" y2="${Y(ymin)}" stroke="currentColor" opacity=".4"/><line x1="${pad}" y1="10" x2="${pad}" y2="${H - pad + 10}" stroke="currentColor" opacity=".4"/>
      <polyline fill="none" stroke="#fbbf24" stroke-width="2.5" points="${pts.map(p => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(' ')}"/>
      <circle cx="${X(k[xs])}" cy="${Y(solve(f, target, k).filter(r => !tv.pos || r > 0)[0] ?? ymin)}" r="5" fill="#4ade80"/>
      <text x="${W / 2}" y="${H - 6}" text-anchor="middle" font-size="12" fill="currentColor">${esc(xv.name)} (${esc(xv.unit)})</text>
      <text x="12" y="16" font-size="12" fill="currentColor">${esc(tv.name)}</text>
      <text x="${pad - 4}" y="${Y(ymax) + 4}" text-anchor="end" font-size="11" fill="currentColor">${fmt(ymax)}</text><text x="${pad - 4}" y="${Y(ymin)}" text-anchor="end" font-size="11" fill="currentColor">${fmt(ymin)}</text>
      <text x="${pad}" y="${H - pad + 24}" font-size="11" fill="currentColor">${fmt(xmin)}</text><text x="${W - 10}" y="${H - pad + 24}" text-anchor="end" font-size="11" fill="currentColor">${fmt(xmax)}</text></svg>`;
  };
  root.querySelectorAll('[data-v]').forEach(i => (i.oninput = compute));
  $('#fx').onchange = compute;
  // seed blank inputs with a consistent example so the page opens with a live result
  known.forEach((v, i) => { const el = root.querySelector(`[data-v="${v.s}"]`); if (!el.value) el.value = v.angle ? 30 : [2, 3, 5, 1.5, 4][i % 5]; });
  compute();
}

// ---------- 10. Error Detective ----------
const TRANSFORMS = { sign: a => -a, k1000: a => a * 1000, half: a => a / 2, square: a => a * a, g: a => a * 9.8, invert: a => 1 / a, kmh: a => a * 3.6, time60: a => a * 60 };
export function detectiveCases() {
  const cases = [];
  for (const u of UNITS) for (const it of unitItems(u)) {
    if (it.kind !== 'num' || !it.calc) continue;
    const ex = exactAnswer(it); if (!Number.isFinite(ex) || ex === 0 || Math.abs(ex - 1) < 0.05) continue;
    const key = Object.keys(TRANSFORMS)[cases.length % Object.keys(TRANSFORMS).length];
    const wrong = TRANSFORMS[key](ex), d = diagnose(ex, wrong);
    if (d.length === 1 && d[0] === key) cases.push({ id: it.key, item: it, wrong, key });   // unambiguous cases only
  }
  return cases;
}
function detective(root) {
  const cases = detectiveCases(), solved = store.get().detective || {};
  const pool = shuffle(cases.filter(c => !solved[c.id]).length ? cases.filter(c => !solved[c.id]) : cases);
  let i = 0;
  root.innerHTML = `<div class="card"><h2>${tt('det.cases')}</h2><p class="hint">${tt('det.cases.d', { n: Object.keys(solved).length, total: cases.length })}</p><div id="dcase"></div></div>
    <div class="card"><h2>${tt('det.analyzer')}</h2><p class="hint">${tt('det.analyzer.d')}</p>
      <div class="row"><label>${tt('det.correct')} <input id="dc" inputmode="decimal"></label><label>${tt('det.yours')} <input id="dy" inputmode="decimal"></label><button class="btn" id="dgo">${tt('eng.check')}</button></div><div class="fb" id="dout" aria-live="polite"></div></div>`;
  const show = () => {
    const c = pool[i % pool.length]; if (!c) { root.querySelector('#dcase').innerHTML = `<p class="hint">${tt('eng.empty')}</p>`; return; }
    const opts = shuffle([c.key, ...shuffle(ERROR_KEYS.filter(k => k !== c.key && k in TRANSFORMS), i).slice(0, 3)], i + 7);
    root.querySelector('#dcase').innerHTML = `<p class="hint"><a href="#/section/${c.item.section}">${esc(c.item.section)}</a></p><p class="qtext">${L(c.item.q)}</p>
      <p>${tt('det.student', { v: fmt(c.wrong, 3), u: c.item.unit || '' })}</p><p>${tt('det.what')}</p>
      <div class="choices">${opts.map(k => `<button class="btn ghost choice" data-k="${k}">${tt('err.' + k)}</button>`).join('')}</div><div class="fb" id="dfb"></div>`;
    root.querySelectorAll('[data-k]').forEach(b => b.onclick = () => {
      const ok = b.dataset.k === c.key;
      if (ok) store.update(s => { (s.detective ||= {})[c.id] = true; });
      root.querySelector('#dfb').innerHTML = `${ok ? `<span class="good">✓ ${tt('q.correct')}</span>` : `<span class="bad">${tt('q.wrong')}</span> ${tt('err.' + c.key)}`}
        <p>${tt('det.right', { v: fmt(exactAnswer(c.item), 3), u: c.item.unit || '' })}</p><details><summary>${tt('q.solution')}</summary><p>${L(c.item.solution)}</p></details><button class="btn" id="dnext">${tt('assess.nextq')}</button>`;
      root.querySelectorAll('[data-k]').forEach(x => (x.disabled = true));
      root.querySelector('#dnext').onclick = () => { i++; show(); };
    });
  };
  show();
  root.querySelector('#dgo').onclick = () => {
    const a = parseNumber(root.querySelector('#dc').value), b = parseNumber(root.querySelector('#dy').value);
    const d = diagnose(a, b);
    root.querySelector('#dout').innerHTML = !Number.isFinite(a) || !Number.isFinite(b) ? tt('q.nan')
      : Math.abs(a - b) <= 0.02 * Math.abs(a) ? `<span class="good">✓ ${tt('det.same')}</span>`
      : d.length ? d.map(k => `<p>🔎 ${tt('err.' + k)}</p>`).join('') : tt('det.none');
  };
}
