// Assessment bank: 250 original items (13 per unit for Units 1–10, 12 per unit for Units 11–20) and 20 DOK 4
// performance tasks. Numeric answers are verified against `calc` by tests/unit/bank.test.js.
import a from './b01_10.js';
import b from './b11_20.js';

// `unit` is the unit number (checked against the id, e.g. B14-07 → 14); `ansUnit` is the answer's unit.
const norm = x => { if (x.unit !== +x.id.slice(1, 3)) throw new Error(`${x.id}: unit ${x.unit}`); return { ansUnit: '', ...x }; };
export const ITEMS = [...a.ITEMS, ...b.ITEMS].map(norm);
export const TASKS = [...a.TASKS, ...b.TASKS];
export const TRANSLATABLE = Object.fromEntries([...ITEMS, ...TASKS].map(x => [x.id, x]));
export default { ITEMS, TASKS };
