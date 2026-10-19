// Content-key enumeration shared by the app (i18n.js) and the Node tooling/tests. No imports.
// Keys whose string values are code, identifiers, units, or colors — never prose. Numeric values are skipped anyway.
export const SKIP = new Set(['id', 'eq', 'calc', 'calcTol', 'fn', 'color', 'trailColor', 'emissive', 'kind', 'unit', 'mode', 'pathway', 'sym', 'dims', 'src', 'shape', 'dok', 'tags', 'prereqTags', 'section', 'type']);
// Paths whose values are symbols or units even though they contain letters (formula variable tables: [symbol, meaning, unit]).
export const SKIP_PATH = /(^|\.)vars\.\d+\.(0|2)$/;
export const isText = s => typeof s === 'string' && /\p{L}{2}/u.test(s);
/**
 * Enumerate every translatable string of a content object as [key, englishText] pairs.
 * Keys are "<scope>|<path>", e.g. "5.3|guided.0.q". Numbers, ids, formula source and diagram geometry are skipped.
 */
export function contentKeys(scope, obj, path = '', out = []) {
  if (typeof obj === 'string') { if (isText(obj) && !SKIP_PATH.test(path)) out.push([`${scope}|${path}`, obj]); return out; }
  if (Array.isArray(obj)) { obj.forEach((v, i) => contentKeys(scope, v, path ? `${path}.${i}` : `${i}`, out)); return out; }
  if (obj && typeof obj === 'object') {
    for (const [k, v] of Object.entries(obj)) if (!SKIP.has(k) && typeof v !== 'function') contentKeys(scope, v, path ? `${path}.${k}` : k, out);
  }
  return out;
}
