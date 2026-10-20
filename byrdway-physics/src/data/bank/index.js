// Assessment bank: 250 original items (13 per unit for Units 1–10, 12 per unit for Units 11–20) and 20 DOK 4
// performance tasks. Numeric answers are verified against `calc` by tests/unit/bank.test.js.
import a from './b01_10.js';
import b from './b11_20.js';

// The two source files spell the answer's unit differently (`units`, or a string `unit` that shadows the unit
// number); normalize to `unit` = unit number (from the id, e.g. B14-07 → 14) and `ansUnit` = answer unit.
const norm = x => ({ ...x, unit: +x.id.slice(1, 3), ansUnit: x.units ?? (typeof x.unit === 'string' ? x.unit : ''), units: undefined });
export const ITEMS = [...a.ITEMS, ...b.ITEMS].map(norm);
export const TASKS = [...a.TASKS, ...b.TASKS];
export const TRANSLATABLE = Object.fromEntries([...ITEMS, ...TASKS].map(x => [x.id, x]));
export default { ITEMS, TASKS };
