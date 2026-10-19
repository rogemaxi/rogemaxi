// Assembles the course: unit/section skeleton and video links come from resources.json (the owner's
// Video Link Library); instructional content comes from the per-unit authoring files u01.js … u20.js.
import resources from '../resources.json';
import u01 from './u01.js'; import u02 from './u02.js'; import u03 from './u03.js'; import u04 from './u04.js';
import u05 from './u05.js'; import u06 from './u06.js'; import u07 from './u07.js'; import u08 from './u08.js';
import u09 from './u09.js'; import u10 from './u10.js'; import u11 from './u11.js'; import u12 from './u12.js';
import u13 from './u13.js'; import u14 from './u14.js'; import u15 from './u15.js'; import u16 from './u16.js';
import u17 from './u17.js'; import u18 from './u18.js'; import u19 from './u19.js'; import u20 from './u20.js';

const AUTHORED = [u01, u02, u03, u04, u05, u06, u07, u08, u09, u10, u11, u12, u13, u14, u15, u16, u17, u18, u19, u20];

export const PARTS = [...new Set(resources.units.map(u => u.part))];

export const UNITS = resources.units.map(u => {
  const a = AUTHORED[u.num - 1] || {};
  const sections = resources.sections.filter(s => s.unit === u.num).map(s => ({
    ...s,
    title: s.topic,
    content: a.sections?.[s.id] || null,
  }));
  return { ...u, lab: a.lab ?? null, bridges: a.bridges || [], blueprint: a.blueprint || [], sections };
});

export const SECTIONS = UNITS.flatMap(u => u.sections);
export const findSection = id => SECTIONS.find(s => s.id === id);
export const findUnit = n => UNITS.find(u => u.num === Number(n));
export const sectionIndex = id => SECTIONS.findIndex(s => s.id === id);
export const RESOURCES = resources;
