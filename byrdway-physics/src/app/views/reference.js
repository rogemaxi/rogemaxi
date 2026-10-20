// Student Reference: formulas, constants, SI units, glossary, misconceptions, standards crosswalk, safety, math,
// live translation report, and about/credits. Routes: #/reference, #/reference/<tab>.
import { t, localize, LANGS, getLang } from '../i18n.js';
import { esc, L, tt, fmt, extLink } from '../ui.js';
import { UNITS, SECTIONS, findSection, RESOURCES } from '../../data/curriculum/index.js';
import { C } from '../../physics/constants.js';
import * as R from '../../data/reference/index.js';
import { ITEMS } from '../../data/bank/index.js';
import { LABS } from '../../lab/labs/index.js';

const TABS = ['formulas', 'constants', 'si', 'glossary', 'misconceptions', 'standards', 'safety', 'math', 'translations', 'about'];
const ref = localize('ref', R.TRANSLATABLE).value;
const secLink = id => { const s = findSection(id); return s ? `<a href="#/section/${id}" title="${esc(s.title)}">${esc(id)}</a>` : esc(id); };

export function renderReference(main, tab = 'formulas') {
  if (!TABS.includes(tab)) tab = 'formulas';
  main.innerHTML = `<div class="page"><h1>${tt('ref.title')}</h1>
    <nav class="tabs" role="tablist">${TABS.map(k => `<a role="tab" aria-selected="${k === tab}" class="tab ${k === tab ? 'on' : ''}" href="#/reference/${k}">${tt('ref.' + k)}</a>`).join('')}</nav>
    <div id="refbody" class="refbody"></div></div>`;
  const body = main.querySelector('#refbody');
  ({ formulas, constants, si, glossary, misconceptions, standards, safety, math, translations, about })[tab](body);
}

function formulas(b) {
  b.innerHTML = `<p class="hint">${tt('ref.formulas.d')} <a href="#/engine/formula">${tt('engine.formula')} →</a></p>` + UNITS.map(u => {
    const rows = u.sections.filter(s => s.content).flatMap(s => { const c = localize(s.id, { f: s.content.formulas }).value; return c.f.map(f => ({ s, f })); });
    return rows.length ? `<h2>${u.num}. ${L(localize('unit.' + u.num, { x: u.title }).value.x)}</h2><div class="tablewrap"><table class="reftable"><tbody>${rows.map(({ s, f }) => `<tr><td><code>${L(f.eq)}</code></td><td>${L(f.when)}</td><td class="vars">${f.vars.map(v => `<code>${esc(v[0])}</code> ${L(v[1])} (${esc(v[2])})`).join('<br>')}</td><td>${secLink(s.id)}</td></tr>`).join('')}</tbody></table></div>` : '';
  }).join('');
}

function constants(b) {
  b.innerHTML = `<div class="tablewrap"><table class="reftable"><thead><tr><th>${tt('ref.symbol')}</th><th>${tt('ref.quantity')}</th><th>${tt('ref.value')}</th></tr></thead><tbody>
    ${Object.entries(R.CONSTANT_NAMES).map(([k, [, unit]]) => `<tr><td><code>${esc(k)}</code></td><td>${L(ref.constants[k])}</td><td>${fmt(C[k], 6)} ${esc(unit)}</td></tr>`).join('')}</tbody></table></div>
    <p class="hint">${tt('ref.constants.d')}</p>`;
}

function si(b) {
  b.innerHTML = `<h2>${tt('ref.si.base')}</h2><table class="reftable"><tbody>${R.BASE_UNITS.map((u, i) => `<tr><td>${L(ref.units.base[i][0])}</td><td>${L(ref.units.base[i][1])}</td><td><code>${esc(u[2])}</code></td></tr>`).join('')}</tbody></table>
    <h2>${tt('ref.si.derived')}</h2><table class="reftable"><tbody>${R.DERIVED_UNITS.map((u, i) => `<tr><td>${L(ref.units.derived[i][0])}</td><td>${L(ref.units.derived[i][1])}</td><td><code>${esc(u[2])}</code></td><td><code>${esc(u[3])}</code></td></tr>`).join('')}</tbody></table>
    <h2>${tt('ref.si.prefixes')}</h2><table class="reftable"><tbody>${R.PREFIXES.map(p => `<tr><td>${esc(p[0])}</td><td><code>${esc(p[1])}</code></td><td>${esc(p[2])}</td></tr>`).join('')}</tbody></table>
    <h2>${tt('ref.si.conv')}</h2><ul>${R.CONVERSIONS.map(c => `<li><bdi dir="ltr">${esc(c)}</bdi></li>`).join('')}</ul>`;
}

function glossary(b, filter = '') {
  const terms = SECTIONS.filter(s => s.content).flatMap(s => localize(s.id, { v: s.content.vocab }).value.v.map(v => ({ id: s.id, term: v[0], def: v[1] })));
  const plain = x => (x && typeof x === 'object' ? x.__untr : String(x));
  terms.sort((a, b) => plain(a.term).localeCompare(plain(b.term), getLang()));
  const q = filter.toLowerCase();
  const shown = terms.filter(x => !q || (plain(x.term) + ' ' + plain(x.def)).toLowerCase().includes(q));
  b.innerHTML = `<label class="sel">${tt('videos.filter')} <input id="gq" type="search" value="${esc(filter)}"></label><p class="hint">${tt('ref.glossary.n', { n: shown.length, total: terms.length })}</p>
    <dl class="glossary">${shown.map(x => `<dt>${L(x.term)} <span class="hint">${secLink(x.id)}</span></dt><dd>${L(x.def)}</dd>`).join('')}</dl>`;
  const inp = b.querySelector('#gq'); let tm;
  inp.oninput = () => { clearTimeout(tm); tm = setTimeout(() => { glossary(b, inp.value); const n = b.querySelector('#gq'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); }, 250); };
}

function misconceptions(b) {
  b.innerHTML = UNITS.map(u => {
    const ms = u.sections.filter(s => s.content).flatMap(s => localize(s.id, { m: s.content.misconceptions }).value.m.map(m => ({ s, m })));
    return ms.length ? `<h2>${u.num}. ${L(localize('unit.' + u.num, { x: u.title }).value.x)}</h2><ul class="mlist">${ms.map(({ s, m }) => `<li><span class="bad">✗ ${L(m.wrong)}</span><br><span class="good">✓ ${L(m.right)}</span> <span class="hint">${secLink(s.id)}</span></li>`).join('')}</ul>` : '';
  }).join('');
}

function standards(b) {
  const S = R.STANDARDS_SOURCE;
  b.innerHTML = `<div class="notice"><p>${tt('ref.std.source', { course: S.course, date: S.retrieved })} ${extLink(S.url, 'CPALMS')}</p>
    <p><strong>${tt('ref.std.verified')}</strong> ${tt('ref.std.verified.d')}</p><p><strong>${tt('ref.std.provisional')}</strong> ${tt('ref.std.provisional.d')}</p><p class="hint">${tt('ref.std.honors')}</p></div>
    <div class="tablewrap"><table class="reftable"><thead><tr><th>${tt('ref.std.code')}</th><th>${tt('ref.std.text')}</th><th>${tt('ref.std.sections')}</th><th>${tt('ref.std.status')}</th></tr></thead><tbody>
    ${R.STANDARDS.map((s, i) => `<tr><td><code>${esc(s.code)}</code></td><td>${L(ref.standards[i].text)}</td><td>${s.sections.map(secLink).join(' ')}</td><td><span class="good">${tt('ref.std.text.ok')}</span><br><span class="warn">${tt('ref.std.align.prov')}</span></td></tr>`).join('')}</tbody></table></div>
    <p class="hint">${tt('ref.std.cross')}: ${R.CROSS_COURSE.map(esc).join(' · ')}</p>`;
}

function safety(b) { b.innerHTML = ref.safety.map(g => `<div class="card"><h2>${L(g.title)}</h2><ul>${g.items.map(x => `<li>${L(x)}</li>`).join('')}</ul></div>`).join('') + `<p class="hint">${tt('ref.safety.d')}</p>`; }
function math(b) { b.innerHTML = ref.math.map(g => `<div class="card"><h2>${L(g.title)}</h2><ul>${g.items.map(x => `<li>${L(x)}</li>`).join('')}</ul></div>`).join(''); }

// Live completeness: count translated vs total strings for the current language across every content scope.
export function translationStats() {
  const groups = { lessons: [0, 0], units: [0, 0], labs: [0, 0], assessment: [0, 0], reference: [0, 0] };
  const add = (g, st) => { groups[g][0] += st.translated; groups[g][1] += st.total; };
  for (const u of UNITS) {
    add('units', localize('unit.' + u.num, { x: u.title, bridges: u.bridges, blueprint: u.blueprint }).stats);
    for (const s of u.sections) add('lessons', localize(s.id, { title: s.title, ...(s.content || {}) }).stats);
  }
  for (const l of LABS) add('labs', localize('lab.' + l.num, l.text).stats);
  for (const it of ITEMS) add('assessment', localize('bank.' + it.id, it).stats);
  add('reference', localize('ref', R.TRANSLATABLE).stats);
  return groups;
}
function translations(b) {
  const lang = LANGS.find(l => l.code === getLang());
  const g = translationStats();
  b.innerHTML = `<p>${tt('ref.tr.d', { lang: lang.native })}</p><div class="tablewrap"><table class="reftable"><thead><tr><th>${tt('ref.tr.group')}</th><th>${tt('ref.tr.done')}</th><th>%</th></tr></thead><tbody>
    ${Object.entries(g).map(([k, [d, n]]) => `<tr><td>${tt('ref.tr.' + k)}</td><td>${d} / ${n}</td><td>${n ? Math.round(100 * d / n) : 100}%</td></tr>`).join('')}</tbody></table></div>
    <p class="hint">${tt('ref.tr.note')}</p>`;
}

function about(b) {
  b.innerHTML = `<div class="card"><h2>${tt('product')}</h2><p>${tt('author')}</p><p>${tt('ref.about.d')}</p></div>
    <div class="card"><h2>${tt('ref.about.sources')}</h2><ul><li>${tt('ref.about.library', { src: RESOURCES.source, n: RESOURCES.counts.links })}</li><li>${tt('ref.about.cpalms')}</li><li>${tt('ref.about.codata')}</li><li>${tt('ref.about.three')}</li></ul></div>
    <div class="card"><h2>${tt('ref.about.honest')}</h2><ul><li>${tt('ref.about.h1')}</li><li>${tt('ref.about.h2')}</li><li>${tt('ref.about.h3')}</li><li>${tt('ref.about.h4')}</li><li>${tt('ref.about.h5')}</li></ul></div>`;
}
