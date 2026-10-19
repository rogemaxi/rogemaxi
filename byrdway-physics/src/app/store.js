// Student progress and settings. Everything stays in this browser (localStorage); nothing is transmitted.
// If storage is blocked (private mode, policy) the app keeps working in memory and shows a warning.
const KEY = 'byrdway-physics-v1';
const SCHEMA = 1;

const defaults = () => ({
  schema: SCHEMA,
  settings: { lang: 'en', pathway: 'core', graphics: 'high', reducedMotion: null, contrast: 'normal', fontScale: 1, narration: false },
  sections: {},      // id -> { visited, done, practice: {itemId: {ok, tries}}, predict, explained }
  labs: {},          // num -> { opened, predicted, runs, challenge: {idx: true}, evaluated }
  cards: {},         // cardId -> Leitner box 1..5
  diagnostic: null,  // { finished, at, answers:[{id, ok}], ability, plan }
  mastery: {},       // level -> { attempts:[{at, score, total}] , tasks:{id:{selfScore}} }
  finals: {},        // core|honors -> attempts
  detective: {},     // caseId -> solved
  streak: { last: null, days: 0 },
  created: new Date().toISOString(),
});

let state = defaults();
export let storageOK = true;
const listeners = new Set();

export function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      state = migrate(parsed);
    }
  } catch (e) {
    storageOK = false;
  }
  touchStreak();
  return state;
}

function migrate(s) {
  const d = defaults();
  if (!s || typeof s !== 'object') return d;
  // Shallow-merge so new fields added in later versions get defaults without losing saved progress.
  const out = { ...d, ...s, settings: { ...d.settings, ...(s.settings || {}) }, schema: SCHEMA };
  return out;
}

export function save() {
  try { localStorage.setItem(KEY, JSON.stringify(state)); storageOK = true; }
  catch (e) { storageOK = false; }
  listeners.forEach(fn => fn(state));
}

export const get = () => state;
export const onChange = fn => (listeners.add(fn), () => listeners.delete(fn));

export function update(fn) { fn(state); save(); }

export function section(id) { return (state.sections[id] ||= { visited: false, done: false, practice: {} }); }
export function lab(num) { return (state.labs[num] ||= { opened: false, predicted: null, runs: 0, challenge: {}, evaluated: false }); }

function touchStreak() {
  const today = new Date().toISOString().slice(0, 10);
  const s = state.streak;
  if (s.last === today) return;
  const y = new Date(Date.now() - 864e5).toISOString().slice(0, 10);
  s.days = s.last === y ? s.days + 1 : 1;
  s.last = today;
  save();
}

export function exportJSON() { return JSON.stringify(state, null, 1); }
export function importJSON(text) {
  const parsed = JSON.parse(text);
  if (!parsed || parsed.schema == null || !parsed.sections) throw new Error('not a ByrdWay Physics progress file');
  state = migrate(parsed); save();
}
export function resetAll() { const keep = state.settings; state = defaults(); state.settings = keep; save(); }
