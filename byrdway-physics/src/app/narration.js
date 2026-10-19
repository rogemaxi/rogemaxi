// Read-aloud narration using the browser's built-in speech synthesis. Narration is offered only when the
// device actually has a voice for the current language; otherwise the button explains that it is unavailable.
import { t, langMeta } from './i18n.js';
import { esc } from './ui.js';

export function voiceFor(langCode) {
  if (!('speechSynthesis' in window)) return null;
  const want = langMeta().speech.toLowerCase(), base = want.split('-')[0];
  const vs = speechSynthesis.getVoices();
  return vs.find(v => v.lang.toLowerCase() === want) || vs.find(v => v.lang.toLowerCase().startsWith(base)) || null;
}

export function speakButton(selector) {
  return `<button class="btn ghost small" data-speak="${esc(selector)}" aria-pressed="false">🔊 ${esc(t('read'))}</button>`;
}

export function wireNarration(root) {
  root.querySelectorAll('[data-speak]').forEach(btn => btn.onclick = () => {
    if (!('speechSynthesis' in window)) return alert(t('set.narration.none'));
    if (speechSynthesis.speaking) { speechSynthesis.cancel(); btn.setAttribute('aria-pressed', 'false'); btn.textContent = '🔊 ' + t('read'); return; }
    const v = voiceFor();
    if (!v) { btn.after(Object.assign(document.createElement('p'), { className: 'hint', textContent: t('set.narration.none') })); btn.disabled = true; return; }
    const el = document.querySelector(btn.dataset.speak);
    const text = [...el.querySelectorAll('h2, p, li, dt, dd')].filter(n => !n.closest('details:not([open])') && !n.closest('.hints')).map(n => n.innerText).join('. ');
    const u = new SpeechSynthesisUtterance(text.slice(0, 32000)); u.voice = v; u.lang = v.lang; u.rate = 0.95;
    u.onend = () => { btn.setAttribute('aria-pressed', 'false'); btn.textContent = '🔊 ' + t('read'); };
    speechSynthesis.speak(u); btn.setAttribute('aria-pressed', 'true'); btn.textContent = '⏹ ' + t('stop');
  });
}
