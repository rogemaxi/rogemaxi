// Study-plan logic shared by the dashboard, diagnostic, and support engine.
import * as store from '../app/store.js';
import { SECTIONS } from '../data/curriculum/index.js';
import { tt, esc } from '../app/ui.js';

const inPath = (s, pw) => pw === 'advanced' || (pw === 'honors' ? s.pathway !== 'Advanced' : s.pathway === 'Core');

export function recommendedNext() {
  const st = store.get(), pw = st.settings.pathway;
  const planIds = st.diagnostic?.plan?.recommend || [];
  for (const id of planIds) if (!st.sections[id]?.done) return SECTIONS.find(s => s.id === id);
  return SECTIONS.find(s => inPath(s, pw) && !st.sections[s.id]?.done) || null;
}

// Honors readiness rule (documented in docs/ASSESSMENT.md): "ready" needs ≥ 75% on the diagnostic AND at least
// 60% correct on Honors-level diagnostic items, OR a Level 3 mastery score ≥ 80%. "building" means some evidence.
export function honorsReadiness() {
  const st = store.get(), d = st.diagnostic;
  const l3 = st.mastery?.[3]?.attempts || [];
  const l3best = l3.length ? Math.max(...l3.map(a => a.score / a.total)) : 0;
  if (l3best >= 0.8) return { state: 'ready', reason: `Level 3 best score ${Math.round(l3best * 100)}% (≥ 80%).` };
  if (!d?.finished) return { state: 'notyet', reason: l3.length ? `Level 3 best score ${Math.round(l3best * 100)}%.` : 'Take the diagnostic or a Level 3 assessment.' };
  const pct = d.answers.filter(a => a.ok).length / d.answers.length;
  const hon = d.answers.filter(a => a.honors), honPct = hon.length ? hon.filter(a => a.ok).length / hon.length : 0;
  if (pct >= 0.75 && hon.length >= 2 && honPct >= 0.6) return { state: 'ready', reason: `Diagnostic ${Math.round(pct * 100)}%, Honors items ${Math.round(honPct * 100)}%.` };
  return { state: 'building', reason: `Diagnostic ${Math.round(pct * 100)}%${hon.length ? `, Honors items ${Math.round(honPct * 100)}%` : ''}. Ready needs ≥ 75% overall and ≥ 60% on Honors items.` };
}

export function studyPlanSummary() {
  const p = store.get().diagnostic?.plan;
  if (!p) return '';
  const link = id => `<a href="#/section/${id}">${esc(id)}</a>`;
  return `<p><strong>${tt('diag.weak')}:</strong> ${p.weak.length ? p.weak.map(w => esc(w)).join(', ') : tt('diag.none')}</p><p><strong>${tt('diag.recommend')}:</strong> ${p.recommend.slice(0, 8).map(link).join(' · ') || tt('diag.none')}</p><a class="btn" href="#/diagnostic/plan">${tt('dash.plan')} →</a>`;
}
