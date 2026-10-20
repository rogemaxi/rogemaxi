// One-question-at-a-time quiz runner shared by Test Me, unit tests, the adaptive diagnostic, mastery levels,
// and finals. Items are plain objects {key, kind:'num'|'mc', q, choices, correct, answer, unit, calc, tol,
// solution, distractors}; text fields may be localized values ({__untr}) and are rendered with L().
// `next(history)` returns the next item (adaptive) or null to finish; `onDone(history)` receives
// [{item, ok, value}] in order.
import { t } from './i18n.js';
import { esc, L, tt, parseNumber, gradeNumber } from './ui.js';
import { exactAnswer } from './views/section.js';
import { diagnose } from '../engines/errors.js';

export function runQuiz(root, { title, total, next, onDone, intro = '' }) {
  const history = [];
  let item = next(history);
  const show = () => {
    if (!item) return onDone(history);
    const i = history.length + 1;
    root.innerHTML = `<div class="quiz card" aria-live="polite">
      <div class="quiz-head"><h2>${esc(title)}</h2><span class="hint">${tt('assess.q', { i, n: total })}</span></div>
      ${i === 1 && intro ? `<p class="hint">${intro}</p>` : ''}
      <div class="pbar"><span style="width:${Math.round(100 * (i - 1) / total)}%"></span></div>
      <p class="qtext">${L(item.q)}</p>
      ${item.kind === 'num'
        ? `<div class="qrow"><input class="qin" id="qa" inputmode="decimal" aria-label="${tt('q.answer')}"><span class="unit">${esc(item.ansUnit ?? (typeof item.unit === 'string' ? item.unit : ''))}</span></div>`
        : `<div class="choices" role="radiogroup">${item.choices.map((c, k) => `<label class="choice"><input type="radio" name="qa" value="${k}"> <span>${L(c)}</span></label>`).join('')}</div>`}
      <div class="row"><button class="btn gold" id="qs">${tt('assess.submit')}</button></div>
      <div class="fb" id="qfb"></div>
    </div>`;
    const fb = root.querySelector('#qfb'), sub = root.querySelector('#qs');
    root.querySelector('#qa')?.focus();
    root.querySelector('#qa')?.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); sub.click(); } });
    sub.onclick = () => {
      if (sub.dataset.done) { item = next(history); return show(); }
      let ok, value, msg = '';
      if (item.kind === 'num') {
        const raw = root.querySelector('#qa').value;
        if (!raw.trim()) { fb.textContent = t('q.empty'); return; }
        value = parseNumber(raw);
        const exact = exactAnswer(item), g = gradeNumber(value, exact, item.tol ?? 0.025);
        if (g === 'nan') { fb.textContent = t('q.nan'); return; }
        ok = g === 'ok';
        if (!ok) { const d = diagnose(exact, value); if (d.length) msg = `<p class="detective">🔎 <strong>${tt('q.diagnose')}:</strong> ${d.map(k => tt('err.' + k)).join(' ')}</p>`; }
      } else {
        const sel = root.querySelector('input[name=qa]:checked');
        if (!sel) { fb.textContent = t('q.choose'); return; }
        value = +sel.value; ok = value === item.correct;
        if (!ok && item.distractors?.[value]) msg = `<p class="detective">🔎 ${L(item.distractors[value])}</p>`;
      }
      history.push({ item, ok, value });
      root.querySelectorAll('input').forEach(x => (x.disabled = true));
      fb.innerHTML = `${ok ? `<span class="good">✓ ${tt('q.correct')}</span>` : `<span class="bad">${tt('q.wrong')}</span>`}${msg}
        <details class="sol" ${ok ? '' : 'open'}><summary>${tt('q.solution')}</summary><p>${L(item.solution)}</p></details>`;
      sub.dataset.done = '1';
      sub.textContent = history.length >= total ? t('assess.finish') : t('assess.nextq');
      sub.focus();
    };
  };
  show();
}

// Score summary with a per-question review list.
export function quizSummary(history, extra = '') {
  const n = history.length, s = history.filter(h => h.ok).length, pct = n ? Math.round(100 * s / n) : 0;
  return `<div class="card"><h2>${tt('assess.score', { s, n, pct })}</h2>${extra}<p class="hint">${tt('assess.note')}</p>
    <details><summary>${tt('assess.review')}</summary><ol class="review">${history.map(h => `<li class="${h.ok ? 'good' : 'bad'}">${h.ok ? '✓' : '✗'} ${L(h.item.q)}<details class="sol"><summary>${tt('q.solution')}</summary><p>${L(h.item.solution)}</p></details></li>`).join('')}</ol></details></div>`;
}

export { shuffle } from '../engines/assess.js';
