// Curriculum alignment layers. ByrdWay Physics is organized by its own 20-unit sequence; each framework below is an
// optional alignment layer. Topic codes and wording come from the official documents saved in sources/benchmarks/
// (status "verified" = copied from the source). Which lesson teaches which topic is the author's provisional mapping
// and must be reviewed by a qualified teacher (docs/HUMAN_REVIEW_REGISTER.md, H3–H7).
import ap from '../../../sources/benchmarks/ap_physics.json';
import { P1, P2, CM, CE } from './ap_alignment.js';
import { STANDARDS as FL, STANDARDS_SOURCE as FLSRC } from '../reference/index.js';
import { INTL } from './intl.js';

const apCourse = (id, short, map, level) => {
  const c = ap.courses.find(x => x.id === id);
  return { id, name: c.name, short, group: 'AP (College Board, USA)', level, source: c.source, retrieved: c.retrieved, units: c.units,
    items: c.items.map(i => ({ code: i.code, text: i.text, unit: i.unit })), map };
};

const flMap = {};
for (const s of FL) for (const id of s.sections) (flMap[id] ||= []).push(s.code);

export const FRAMEWORKS = [
  apCourse('AP1', 'AP 1', P1, 'Algebra-based, first-year college level'),
  apCourse('AP2', 'AP 2', P2, 'Algebra-based, first-year college level'),
  apCourse('APCM', 'AP C: Mech', CM, 'Calculus-based, first-year college level'),
  apCourse('APCE', 'AP C: E&M', CE, 'Calculus-based, first-year college level'),
  ...INTL,
  { id: 'FL', name: 'Florida Physics 1 (#2003380)', short: 'Florida', group: 'Optional regional layer', level: 'High school (Florida)', source: FLSRC.url, retrieved: FLSRC.retrieved,
    items: FL.map(s => ({ code: s.code, text: s.text })), map: flMap },
];

export const findFramework = id => FRAMEWORKS.find(f => f.id === id);
// Codes for one lesson in every framework: [{fw, codes:[{code,text}]}]
export function lessonAlignment(sectionId) {
  return FRAMEWORKS.map(fw => ({ fw, codes: (fw.map[sectionId] || []).map(code => fw.items.find(i => i.code === code) || { code, text: '' }) })).filter(x => x.codes.length);
}
export const gaps = fw => fw.items.filter(i => !Object.values(fw.map).some(cs => cs.includes(i.code)));
