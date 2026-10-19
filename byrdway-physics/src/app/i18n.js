// Localization. English is the source language. UI strings live in data/i18n/ui/<lang>.json; lesson content
// lives in data/i18n/content/<lang>.json keyed by stable content keys (see contentKeys()). Any string that has
// no translation falls back to English, is marked lang="en" + class "untr", and is counted by the detector.
import ui_en from '../data/i18n/ui/en.json';
import ui_es from '../data/i18n/ui/es.json';
import ui_fr from '../data/i18n/ui/fr.json';
import ui_ht from '../data/i18n/ui/ht.json';
import ui_pt from '../data/i18n/ui/pt.json';
import ui_ar from '../data/i18n/ui/ar.json';
import ui_zh from '../data/i18n/ui/zh.json';
import ui_hi from '../data/i18n/ui/hi.json';
import ui_bn from '../data/i18n/ui/bn.json';
import ui_vi from '../data/i18n/ui/vi.json';
import ui_ko from '../data/i18n/ui/ko.json';
import ui_ja from '../data/i18n/ui/ja.json';
import { CONTENT_PACKS } from '../data/i18n/content/index.js';

export const LANGS = [
  { code: 'en', name: 'English', native: 'English', dir: 'ltr', speech: 'en-US' },
  { code: 'es', name: 'Spanish', native: 'Español', dir: 'ltr', speech: 'es-ES' },
  { code: 'fr', name: 'French', native: 'Français', dir: 'ltr', speech: 'fr-FR' },
  { code: 'ht', name: 'Haitian Creole', native: 'Kreyòl ayisyen', dir: 'ltr', speech: 'ht-HT' },
  { code: 'pt', name: 'Portuguese', native: 'Português', dir: 'ltr', speech: 'pt-BR' },
  { code: 'ar', name: 'Arabic', native: 'العربية', dir: 'rtl', speech: 'ar-SA' },
  { code: 'zh', name: 'Simplified Chinese', native: '简体中文', dir: 'ltr', speech: 'zh-CN' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी', dir: 'ltr', speech: 'hi-IN' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা', dir: 'ltr', speech: 'bn-IN' },
  { code: 'vi', name: 'Vietnamese', native: 'Tiếng Việt', dir: 'ltr', speech: 'vi-VN' },
  { code: 'ko', name: 'Korean', native: '한국어', dir: 'ltr', speech: 'ko-KR' },
  { code: 'ja', name: 'Japanese', native: '日本語', dir: 'ltr', speech: 'ja-JP' },
];
export const UI = { en: ui_en, es: ui_es, fr: ui_fr, ht: ui_ht, pt: ui_pt, ar: ui_ar, zh: ui_zh, hi: ui_hi, bn: ui_bn, vi: ui_vi, ko: ui_ko, ja: ui_ja };

let lang = 'en';
const missing = { ui: new Set(), content: new Set() };

export function setLang(code) {
  lang = LANGS.some(l => l.code === code) ? code : 'en';
  const meta = LANGS.find(l => l.code === lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = meta.dir;
}
export const getLang = () => lang;
export const langMeta = () => LANGS.find(l => l.code === lang);

const fill = (s, p) => (p ? s.replace(/\{(\w+)\}/g, (_, k) => (p[k] ?? `{${k}}`)) : s);

/** UI string. Always returns plain text (escape before inserting as HTML). */
export function t(key, params) {
  const v = UI[lang]?.[key];
  if (v != null) return fill(v, params);
  if (lang !== 'en') missing.ui.add(key);
  const en = UI.en[key];
  if (en == null) { missing.ui.add('!' + key); return key; }
  return fill(en, params);
}

/** Lesson content lookup: returns {text, translated}. key example: "5.3|explain.0" */
export function tcRaw(key, en) {
  if (lang === 'en') return { text: en, translated: true };
  const v = CONTENT_PACKS[lang]?.[key];
  if (v != null && v !== '') return { text: v, translated: true };
  missing.content.add(key);
  return { text: en, translated: false };
}

export const missingReport = () => ({ ui: [...missing.ui], content: [...missing.content] });

/**
 * Enumerate every translatable string of a content object as [key, englishText] pairs.
 * Keys are "<scope>|<path>", e.g. "5.3|guided.0.q". Numbers, ids and formula source are not translatable.
 */
const SKIP = new Set(['id', 'eq', 'answer', 'unit', 'tol', 'calc', 'lab', 'visual', 'type', 'pathway', 'level', 'difficulty', 'tags', 'prereqTags', 'unitNum', 'choices_raw', 'sym', 'dims', 'fn', 'num', 'correct', 'section', 'src', 'dok']);
export function contentKeys(scope, obj, path = '', out = []) {
  if (typeof obj === 'string') { if (/[A-Za-z]{2}/.test(obj)) out.push([`${scope}|${path}`, obj]); return out; }
  if (Array.isArray(obj)) { obj.forEach((v, i) => contentKeys(scope, v, path ? `${path}.${i}` : `${i}`, out)); return out; }
  if (obj && typeof obj === 'object') {
    for (const [k, v] of Object.entries(obj)) if (!SKIP.has(k) && typeof v !== 'function') contentKeys(scope, v, path ? `${path}.${k}` : k, out);
  }
  return out;
}

/** Return a deep copy of obj with all translatable strings localized; collects untranslated count. */
export function localize(scope, obj) {
  const stats = { total: 0, translated: 0 };
  const walk = (v, path) => {
    if (typeof v === 'string') {
      if (!/[A-Za-z]{2}/.test(v)) return v;
      stats.total++;
      const r = tcRaw(`${scope}|${path}`, v);
      if (r.translated) { stats.translated++; return r.text; }
      return { __untr: r.text };
    }
    if (Array.isArray(v)) return v.map((x, i) => walk(x, path ? `${path}.${i}` : `${i}`));
    if (v && typeof v === 'object') {
      const o = {};
      for (const [k, x] of Object.entries(v)) o[k] = (SKIP.has(k) || typeof x === 'function') ? x : walk(x, path ? `${path}.${k}` : k);
      return o;
    }
    return v;
  };
  const value = walk(obj, '');
  return { value, stats };
}
