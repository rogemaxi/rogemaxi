// Section lesson view: renders all 20 instructional components for one curriculum section, following
// OBSERVE → PREDICT → EXPERIMENT → MEASURE → MODEL → CALCULATE → EXPLAIN → CHALLENGE → MASTER.
import { t, localize } from '../i18n.js';
import { esc, L, P, tt, pathwayBadge, parseNumber, gradeNumber, fmt, extLink } from '../ui.js';
import { renderDiagram } from '../diagrams.js';
import * as store from '../store.js';
import { SECTIONS, findSection, findUnit, sectionIndex } from '../../data/curriculum/index.js';
import { findLab } from '../../lab/labs/index.js';
import { diagnose } from '../../engines/errors.js';
import { speakButton } from '../narration.js';
import * as PHYS from '../../physics/index.js';

// Grade against the exact value from the item's calc restatement (verified by tests to match the displayed answer),
// so a student who keeps more digits than the rounded key is not marked wrong.
const calcCache = new Map();
export function exactAnswer(q) {
  if (!q.calc) return q.answer;
  if (!calcCache.has(q.calc)) { try { calcCache.set(q.calc, Function('P', 'Math', `"use strict"; return (${q.calc});`)(PHYS, Math)); } catch { calcCache.set(q.calc, q.answer); } }
  const v = calcCache.get(q.calc);
  return Number.isFinite(v) ? v : q.answer;
}

export function sectionDone(id) { return !!store.get().sections[id]?.done; }

export function renderSection(root, id) {
  const sec = findSection(id);
  if (!sec) { root.innerHTML = `<div class="page"><p>${tt('notfound')}</p><a href="#/home">${tt('gohome')}</a></div>`; return; }
  const unit = findUnit(sec.unit);
  const prog = store.section(id);
  store.update(() => { prog.visited = true; });
  const { value: c, stats } = localize(id, { title: sec.title, ...(sec.content || {}) });
  const i = sectionIndex(id), prev = SECTIONS[i - 1], next = SECTIONS[i + 1];
  const lab = sec.content?.lab ? findLab(sec.content.lab) : (unit.lab ? findLab(unit.lab) : null);
  const raw = sec.content;
  const untr = stats.total && stats.translated < stats.total;

  if (!raw) {
    root.innerHTML = `<article class="page"><p class="crumb"><a href="#/unit/${unit.num}">${tt('unit.title', { n: unit.num })} · ${esc(unit.title)}</a></p><h1>${esc(sec.id)} ${esc(sec.title)}</h1><p class="hint">This section's lesson is being authored. Its video resources are available now.</p>${videos(sec)}</article>`;
    return;
  }

  root.innerHTML = `
  <article class="page lesson" aria-labelledby="sttl">
    <p class="crumb"><a href="#/unit/${unit.num}">${tt('unit.title', { n: unit.num })} · ${L(localize('unit.' + unit.num, { x: unit.title }).value.x)}</a></p>
    <header class="lesson-head">
      <h1 id="sttl"><span class="secnum">${esc(sec.id)}</span> ${L(c.title)}</h1>
      <div class="lesson-meta">${pathwayBadge(sec.pathway)} ${speakButton('#lessonbody')}</div>
      ${sec.pathway === 'Advanced' ? `<p class="pw-note">${tt('path.advanced.note')}</p>` : ''}
      ${untr ? `<p class="untr-note">${tt('untr.note')} (${stats.translated}/${stats.total})</p>` : ''}
      ${!untr && store.get().settings.lang !== 'en' ? `<p class="mt-note">${tt('mt.note')}</p>` : ''}
    </header>
    <nav class="flowbar" aria-label="Learning sequence">${['observe', 'predict', 'experiment', 'measure', 'model', 'calculate', 'explain', 'challenge', 'master'].map(s => `<span>${tt('feynman.step.' + s)}</span>`).join('<i>→</i>')}</nav>
    <div id="lessonbody">
    <div class="grid2">
      <section class="card"><h2>${tt('sec.objectives')}</h2><ul>${c.objectives.map(o => `<li>${L(o)}</li>`).join('')}</ul></section>
      <section class="card"><h2>${tt('sec.prereq')}</h2><ul>${c.prereqs.map(o => `<li>${L(o)}</li>`).join('')}</ul></section>
    </div>
    <section class="card observe"><h2>🔭 ${tt('sec.observe')}</h2><p class="lead">${L(c.intro)}</p><p>${L(c.observe)}</p></section>
    <section class="card predict" id="pred"><h2>🎯 ${tt('sec.predict')}</h2>
      <p>${L(c.predict.prompt)}</p>
      <div class="choices" role="radiogroup">${c.predict.choices.map((ch, k) => `<label class="choice"><input type="radio" name="spred" value="${k}" ${prog.predict === k ? 'checked' : ''}> <span>${L(ch)}</span></label>`).join('')}</div>
      <button class="btn gold" id="plock">${tt('sec.predict.lock')}</button>
      <div class="fb" id="pfb" aria-live="polite"></div>
    </section>
    <div id="afterpredict" ${prog.predict == null ? 'class="dimmed"' : ''}>
    <section class="card"><h2>🧠 ${tt('sec.explain')}</h2>${c.explain.map(p => `<p>${L(p)}</p>`).join('')}</section>
    ${raw.visual ? `<section class="card"><h2>🖼️ ${tt('sec.visual')}</h2>${renderDiagram(plainDeep(c.visual))}</section>` : ''}
    <div class="grid2">
      <section class="card"><h2>📖 ${tt('sec.vocab')}</h2><dl class="vocab">${c.vocab.map(v => `<dt>${L(v[0])}</dt><dd>${L(v[1])}</dd>`).join('')}</dl></section>
      <section class="card"><h2>∑ ${tt('sec.formulas')}</h2>${c.formulas.map((f, k) => `<div class="formula"><div class="feq">${esc(raw.formulas[k].eq)}</div><table class="fvars">${f.vars.map((v, j) => `<tr><td>${esc(raw.formulas[k].vars[j][0])}</td><td>${L(v[1])}</td><td>${esc(raw.formulas[k].vars[j][2])}</td></tr>`).join('')}</table><p class="when">${L(f.when)}</p>${raw.formulas[k].id ? `<a class="small" href="#/engine/formula/${esc(raw.formulas[k].id)}">${tt('engine.formula')} →</a>` : ''}</div>`).join('')}</section>
    </div>
    ${c.derivation ? `<section class="card"><h2>🧩 ${tt('sec.derivation')}</h2><ol>${[].concat(c.derivation).map(s => `<li>${L(s)}</li>`).join('')}</ol></section>` : ''}
    <section class="card"><h2>📏 ${tt('sec.units')}</h2><p>${L(c.units)}</p></section>
    <section class="card example"><h2>✍️ ${tt('sec.example')}</h2><p><strong>${L(c.example.problem)}</strong></p><ol class="steps">${c.example.steps.map(s => `<li>${L(s)}</li>`).join('')}</ol><p class="answer">✓ ${L(c.example.answer)}</p></section>
    <section class="card"><h2>🤝 ${tt('sec.guided')}</h2><div class="qs">${c.guided.map((q, k) => question(id, 'g', raw.guided[k], q)).join('')}</div></section>
    <section class="card"><h2>🏁 ${tt('sec.practice')}</h2><div class="qs">${c.practice.map((q, k) => question(id, 'p', raw.practice[k], q)).join('')}</div></section>
    <section class="card miscon"><h2>⚠️ ${tt('sec.misconceptions')}</h2>${c.misconceptions.map(m => `<div class="mc"><p class="wrong"><strong>${tt('sec.wrong')}:</strong> ${L(m.wrong)}</p><p class="right"><strong>${tt('sec.right')}:</strong> ${L(m.right)}</p><p class="fbk">${L(m.feedback)}</p></div>`).join('')}</section>
    <section class="card investigate"><h2>🧪 ${tt('sec.investigate')}</h2><p>${L(c.investigate)}</p>${lab ? `<a class="btn gold" href="#/lab/${lab.num}">${esc(t('sec.openlab', { lab: P(localize('lab.' + lab.num, { x: lab.text.title }).value.x) }))}</a>` : ''}</section>
    <section class="card explainback"><h2>🗣️ ${tt('sec.explainback')}</h2><p>${tt('sec.explainback.prompt')}</p>
      <textarea id="xb" rows="4" aria-label="${tt('sec.explainback')}">${esc(prog.explained || '')}</textarea>
      <button class="btn" id="xbcheck">${tt('sec.explainback.check')}</button><div id="xbfb" aria-live="polite"></div></section>
    <section class="card"><h2>🏆 ${tt('sec.mastery')}</h2><ul class="checks">${c.mastery.map(m => `<li>${L(m)}</li>`).join('')}</ul></section>
    ${c.honors ? `<details class="card honors"><summary><h2>🎓 ${tt('sec.honors')}</h2></summary><p>${L(c.honors.prompt)}</p><details><summary>${tt('q.solution')}</summary><p>${L(c.honors.solution)}</p></details></details>` : ''}
    ${videos(sec)}
    </div>
    </div>
    <div class="complete-bar"><button class="btn gold big" id="complete" ${prog.done ? 'disabled' : ''}>${prog.done ? '✓ ' + tt('sec.completed') : tt('sec.complete')}</button><span class="hint" id="cneed"></span></div>
    <nav class="pager">${prev ? `<a class="btn ghost" href="#/section/${prev.id}">← ${tt('sec.prev')}: ${esc(prev.id)}</a>` : '<span></span>'}${next ? `<a class="btn ghost" href="#/section/${next.id}">${tt('sec.next')}: ${esc(next.id)} →</a>` : ''}</nav>
  </article>`;

  const $ = s => root.querySelector(s);
  const showPred = () => { if (prog.predict != null) $('#pfb').innerHTML = `<p>✓ ${tt('sec.predict.yours')}: <strong>${L(c.predict.choices[prog.predict])}</strong></p><p class="${prog.predict === raw.predict.correct ? 'good' : 'warn'}">${prog.predict === raw.predict.correct ? tt('q.correct') : tt('q.wrong')} ${L(c.predict.why)}</p>`; };
  $('#plock').onclick = () => {
    const sel = root.querySelector('input[name=spred]:checked');
    if (!sel) { $('#pfb').innerHTML = `<span class="warn">${tt('q.choose')}</span>`; return; }
    store.update(() => { prog.predict = +sel.value; });
    $('#afterpredict').classList.remove('dimmed'); showPred(); checkComplete();
  };
  showPred();
  wireQuestions(root, id, raw, c, checkComplete);
  $('#xbcheck').onclick = () => {
    const txt = $('#xb').value; store.update(() => { prog.explained = txt; });
    const groups = (c.explainWords || []).map(g => g.map(P));
    const lower = txt.toLowerCase();
    const hit = groups.map(g => g.some(w => lower.includes(w.toLowerCase())));
    $('#xbfb').innerHTML = `<p class="hint">${tt('sec.explainback.keyideas')}:</p><ul class="checks">${(c.explainKeys || []).map((k, j) => `<li class="${hit[j] ? 'good' : 'dimtxt'}">${hit[j] ? '✓' : '○'} ${L(k)}</li>`).join('')}</ul><p class="hint">This is a keyword check to help you self-assess; it is not a grade.</p>`;
  };
  $('#complete').onclick = () => {
    if (!practiceMet(id, raw)) { $('#cneed').textContent = t('sec.complete.need'); return; }
    store.update(() => { prog.done = true; prog.doneAt = new Date().toISOString(); });
    $('#complete').disabled = true; $('#complete').textContent = '✓ ' + t('sec.completed');
  };
  function checkComplete() { if (!prog.done && practiceMet(id, raw)) $('#cneed').textContent = ''; }
}

export function practiceMet(id, raw) {
  const p = store.get().sections[id]?.practice || {};
  const items = raw.practice || [];
  const ok = items.filter(q => p['p.' + q.id]?.ok).length;
  return items.length > 0 && ok >= Math.ceil(items.length * 0.8);
}

const plainDeep = v => (Array.isArray(v) ? v.map(plainDeep) : v && typeof v === 'object' ? ('__untr' in v ? v.__untr : Object.fromEntries(Object.entries(v).map(([k, x]) => [k, plainDeep(x)]))) : v);

function question(sid, kind, raw, q) {
  const key = `${kind}.${raw.id}`;
  const st = store.get().sections[sid]?.practice?.[key];
  const done = st?.ok ? ' qdone' : '';
  let input = '';
  if (raw.kind === 'num') input = `<div class="qrow"><input class="qin" inputmode="decimal" data-q="${key}" aria-label="${tt('q.answer')}"><span class="unit">${esc(raw.unit || '')}</span><button class="btn" data-check="${key}">${tt('q.check')}</button>${q.hints?.length ? `<button class="btn ghost" data-hint="${key}">${tt('q.hint')}</button>` : ''}</div>`;
  else if (raw.kind === 'mc') input = `<div class="choices" role="radiogroup">${q.choices.map((ch, k) => `<label class="choice"><input type="radio" name="${sid}-${key}" value="${k}"> <span>${L(ch)}</span></label>`).join('')}</div><button class="btn" data-check="${key}">${tt('q.check')}</button>`;
  else input = `<p class="hint">${tt('q.selfcheck')}</p><button class="btn ghost" data-self="${key}" data-v="1">${tt('q.igotit')}</button> <button class="btn ghost" data-self="${key}" data-v="0">${tt('q.notyet')}</button>`;
  return `<div class="q${done}" data-qwrap="${key}"><p class="qtext">${L(q.q)}</p>${input}<div class="fb" data-fb="${key}" aria-live="polite">${st?.ok ? '✓ ' + tt('q.correct') : ''}</div><div class="hints" data-hints="${key}"></div><details class="sol"><summary>${tt('q.solution')}</summary><p>${L(q.solution)}</p></details></div>`;
}

export function wireQuestions(root, sid, raw, c, onChange = () => {}) {
  const all = [...(raw.guided || []).map((q, k) => ['g', q, c.guided?.[k]]), ...(raw.practice || []).map((q, k) => ['p', q, c.practice?.[k]])];
  const find = key => all.find(([kind, q]) => `${kind}.${q.id}` === key);
  const hintIdx = {};
  root.querySelectorAll('[data-check]').forEach(btn => btn.onclick = () => {
    const key = btn.dataset.check, [, q] = find(key), fb = root.querySelector(`[data-fb="${key}"]`);
    let ok = false, msg = '';
    if (q.kind === 'num') {
      const inp = root.querySelector(`[data-q="${key}"]`), v = parseNumber(inp.value);
      if (!inp.value.trim()) { fb.textContent = t('q.empty'); return; }
      const exact = exactAnswer(q);
      const g = gradeNumber(v, exact, q.tol ?? 0.025);
      if (g === 'nan') { fb.textContent = t('q.nan'); return; }
      ok = g === 'ok';
      msg = ok ? `<span class="good">✓ ${tt('q.correct')}</span>` : g === 'close' ? `<span class="warn">${tt('q.close')}</span>` : `<span class="bad">${tt('q.wrong')}</span>`;
      if (g === 'wrong') { const d = diagnose(exact, v); if (d.length) msg += `<p class="detective">🔎 <strong>${tt('q.diagnose')}:</strong> ${d.map(k => tt('err.' + k)).join(' ')}</p>`; }
    } else if (q.kind === 'mc') {
      const sel = root.querySelector(`input[name="${sid}-${key}"]:checked`);
      if (!sel) { fb.textContent = t('q.choose'); return; }
      ok = +sel.value === q.correct;
      msg = ok ? `<span class="good">✓ ${tt('q.correct')}</span>` : `<span class="bad">${tt('q.wrong')}</span>`;
    }
    record(sid, key, ok);
    fb.innerHTML = msg;
    if (ok) root.querySelector(`[data-qwrap="${key}"]`).classList.add('qdone');
    onChange();
  });
  root.querySelectorAll('[data-hint]').forEach(btn => btn.onclick = () => {
    const key = btn.dataset.hint, [, , qc] = find(key), i = hintIdx[key] = (hintIdx[key] ?? -1) + 1;
    const box = root.querySelector(`[data-hints="${key}"]`);
    box.innerHTML = (qc?.hints || []).slice(0, i + 1).map(h => `<p class="hintline">💡 ${L(h)}</p>`).join('') + (i >= (qc?.hints?.length || 0) ? `<p class="hint">${tt('q.nohint')}</p>` : '');
  });
  root.querySelectorAll('[data-self]').forEach(btn => btn.onclick = () => {
    const key = btn.dataset.self, ok = btn.dataset.v === '1'; record(sid, key, ok);
    root.querySelector(`[data-fb="${key}"]`).innerHTML = ok ? `✓ ${tt('q.correct')}` : tt('q.notyet');
    onChange();
  });
}

function record(sid, key, ok) {
  store.update(s => { const sec = (s.sections[sid] ||= { practice: {} }); const p = (sec.practice ||= {}); const r = (p[key] ||= { ok: false, tries: 0 }); r.tries++; r.ok = r.ok || ok; });
}

export function videos(sec) {
  return `<section class="card videos"><h2>🎬 ${tt('sec.videos')}</h2><p class="hint">${tt('videos.note')}</p>
  <div class="vlinks">${extLink(sec.links.khan, tt('videos.khan'), 'vbtn khan')}${extLink(sec.links.oct, tt('videos.oct'), 'vbtn oct')}${extLink(sec.links.yt, tt('videos.yt'), 'vbtn yt')}</div>
  <p class="hint small">${tt('videos.english')}</p></section>`;
}
