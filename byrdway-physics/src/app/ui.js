// Small DOM/HTML helpers shared by all views.
import { t } from './i18n.js';

export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// Render a localized value: a string, or {__untr: englishText} for an untranslated fallback.
export function L(v) {
  if (v && typeof v === 'object' && '__untr' in v) return `<span lang="en" class="untr">${rich(v.__untr)}</span>`;
  return rich(v);
}
// Plain text of a localized value (for attributes, speech, and comparisons).
export const P = v => (v && typeof v === 'object' && '__untr' in v ? v.__untr : String(v ?? ''));

// Escape, then apply light formatting: superscripts typed as ^2 and subscripts typed as _x are left as-is
// (authors write Unicode ² and ₓ directly); **bold** is supported.
export function rich(s) {
  let out = esc(s);
  // In right-to-left languages, isolate embedded formulas and units (runs without Arabic letters that contain
  // Latin letters or digits) so the bidirectional algorithm cannot reorder "N = 1 kg·m/s²".
  if (typeof document !== 'undefined' && document.documentElement.dir === 'rtl') {
    out = out.replace(/[^\u0600-\u06FF\u0750-\u077F،؛؟«»]+/g, run => {
      if (!/[A-Za-z0-9]/.test(run)) return run;
      const lead = run.match(/^\s*/)[0], trail = run.match(/\s*$/)[0];
      const core = run.slice(lead.length, run.length - trail.length);
      return core ? `${lead}<bdi dir="ltr">${core}</bdi>${trail}` : run;
    });
  }
  return out.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

export const tt = (key, params) => esc(t(key, params));

export function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'html') el.innerHTML = v;
    else if (v === true) el.setAttribute(k, '');
    else if (v !== false && v != null) el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) el.append(kid instanceof Node ? kid : document.createTextNode(kid));
  return el;
}

export function pathwayBadge(pw) {
  const key = { Core: 'core', Honors: 'honors', Advanced: 'advanced' }[pw] || 'core';
  return `<span class="pw pw-${key}">${tt('path.badge.' + key)}</span>`;
}

export function progressBar(frac, label) {
  const pct = Math.round(Math.max(0, Math.min(1, frac)) * 100);
  return `<div class="pbar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="${esc(label || '')}"><span style="width:${pct}%"></span></div>`;
}

// Parse a student's numeric answer: accepts 3.2e5, 3.2×10^5, 3,200 (thousands), unicode minus, commas as decimals.
export function parseNumber(raw) {
  if (raw == null) return NaN;
  let s = String(raw).trim().replace(/[−–]/g, '-').replace(/\s+/g, '');
  s = s.replace(/[×x*·]10\^\(?(-?\d+)\)?/i, 'e$1');
  // Drop a trailing unit the student typed ("12N", "3.0m/s²"), but keep an exponent like "e5".
  s = s.replace(/(\d)(?![eE][-+]?\d)[a-zA-Zµ°Ω/²³%·][^\d]*$/, '$1');
  if (/^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(s)) s = s.replace(/,/g, '');
  else if (/^-?\d+,\d+$/.test(s)) s = s.replace(',', '.');
  if (!/^-?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(s)) return NaN;
  return Number(s);
}

// Compare numeric answers with a relative tolerance (default 2%, which accepts 2–3 significant-figure rounding).
export function gradeNumber(value, answer, tol = 0.02) {
  if (!Number.isFinite(value)) return 'nan';
  const err = answer === 0 ? Math.abs(value) : Math.abs(value - answer) / Math.abs(answer);
  if (err <= tol) return 'ok';
  if (err <= tol * 2.5) return 'close';
  return 'wrong';
}

export function toast(msg) {
  const el = h('div', { class: 'toast', role: 'status' }, msg);
  document.body.append(el);
  setTimeout(() => el.classList.add('show'), 10);
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 400); }, 2600);
}

export function fmt(x, sig = 3) {
  if (!Number.isFinite(x)) return x === Infinity ? '∞' : '—';
  if (x === 0) return '0';
  const a = Math.abs(x);
  if (a >= 1e5 || a < 1e-3) {
    const [m, e] = x.toExponential(sig - 1).split('e');
    return `${m} × 10${sup(+e)}`;
  }
  return Number(x.toPrecision(sig)).toString();
}
const SUP = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' };
export const sup = n => String(n).split('').map(c => SUP[c] ?? c).join('');

export function download(name, text, type = 'text/plain') {
  const a = h('a', { href: URL.createObjectURL(new Blob([text], { type })), download: name });
  document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}

// Open external resources safely.
export const extLink = (url, label, cls = '') =>
  `<a class="${cls}" href="${esc(url)}" target="_blank" rel="noopener noreferrer external">${label}<span class="sr-only"> (opens in a new tab)</span> ↗</a>`;
