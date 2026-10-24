// International and cross-cutting alignment layers. Codes and titles: sources/benchmarks/*.json (copied verbatim from
// the official documents). Lesson mappings are the author's provisional judgment, checked against lesson content
// (topics whose content is absent, e.g. Cambridge 24.3 PET scanning, are left unmapped and reported as gaps).
// Reviews: H4 (Cambridge), H5 (IB), H6 (NGSS) in docs/HUMAN_REVIEW_REGISTER.md.
import caie from '../../../sources/benchmarks/cambridge_9702.json';
import ib from '../../../sources/benchmarks/ib_dp_physics.json';
import ngss from '../../../sources/benchmarks/ngss_hs.json';

// Cambridge International AS & A Level Physics 9702 — sub-topic codes (topics 1–11 AS Level, 12–25 A Level).
export const CAIE_MAP = {
  '1.4': ['1.1', '1.2'], '1.5': ['1.3'], '1.6': ['1.1'], '1.7': ['1.1', '1.2'], '1.9': ['1.3'],
  '2.4': ['1.4'], '2.5': ['1.4'],
  '3.1': ['2.1'], '3.2': ['2.1'], '3.3': ['2.1'], '3.4': ['2.1'], '3.5': ['2.1'], '3.6': ['2.1'], '3.7': ['2.1'], '3.8': ['3.2'],
  '4.1': ['2.1'], '4.2': ['2.1'], '4.3': ['2.1'], '4.4': ['2.1'], '4.6': ['2.1'], '4.7': ['3.2'],
  '5.1': ['3.1'], '5.2': ['3.1'], '5.3': ['3.1'], '5.4': ['3.1'], '5.5': ['4.2'], '5.6': ['3.1', '4.2'], '5.7': ['3.2', '4.2'], '5.8': ['3.1'], '5.9': ['3.1'],
  '6.1': ['5.1'], '6.2': ['5.2'], '6.3': ['5.2'], '6.4': ['6.2'], '6.5': ['5.2'], '6.6': ['5.1', '5.2'], '6.7': ['5.1'], '6.8': ['5.1'], '6.9': ['6.2'],
  '7.1': ['3.1'], '7.2': ['3.1'], '7.3': ['3.3'], '7.4': ['3.3'], '7.5': ['3.3'], '7.6': ['3.3'], '7.7': ['3.3'], '7.8': ['3.3'],
  '8.1': ['12.1'], '8.2': ['12.2'], '8.3': ['12.2'], '8.4': ['12.2'], '8.5': ['13.2'], '8.6': ['13.1', '13.3'], '8.7': ['13.3'], '8.8': ['13.2', '13.3'], '8.9': ['13.4'],
  '9.1': ['12.1'], '9.3': ['4.1'], '9.4': ['4.1'],
  '10.1': ['17.1'], '10.2': ['6.1', '17.1'], '10.3': ['17.1'], '10.4': ['17.1'], '10.5': ['17.1'], '10.6': ['17.2'], '10.7': ['17.3'], '10.8': ['17.1'],
  '11.1': ['4.3'], '11.2': ['4.3'], '11.3': ['4.3'], '11.4': ['4.3'],
  '12.1': ['14.1', '14.2'], '12.2': ['16.1'], '12.3': ['14.3'], '12.4': ['14.3'], '12.6': ['15.1', '15.2', '15.3'], '12.7': ['16.2'],
  '13.1': ['7.1', '7.2'], '13.2': ['7.1'], '13.3': ['8.3'], '13.4': ['8.2'], '13.5': ['8.1'], '13.6': ['7.1'], '13.7': ['7.3'], '13.8': ['8.1'],
  '14.1': ['7.4'], '14.7': ['7.5', '8.2', '8.3', '8.4'],
  '15.1': ['9.1'], '15.3': ['18.3'], '15.4': ['18.1', '18.4'], '15.5': ['18.5'], '15.6': ['18.2', '18.5'], '15.7': ['19.1', '19.2'], '15.8': ['18.4', '18.5'],
  '16.1': ['9.1', '9.3'], '16.2': ['9.3'], '16.3': ['10.1', '10.3'], '16.4': ['10.1'], '16.5': ['10.1'], '16.6': ['10.2'], '16.7': ['9.2'], '16.8': ['10.1'], '16.9': ['19.3'],
  '17.1': ['20.1'], '17.2': ['20.3'], '17.3': ['20.4'], '17.4': ['20.4'], '17.5': ['20.5'], '17.6': ['20.5'], '17.7': ['20.5'], '17.8': ['20.2', '20.5', '21.1'], '17.9': ['20.5', '21.1'],
  '18.1': ['11.1'], '18.2': ['22.4'], '18.3': ['22.1', '22.2'], '18.4': ['22.1', '22.3'], '18.5': ['22.3'], '18.6': ['11.1'], '18.7': ['23.2'], '18.8': ['23.1'], '18.9': ['22.4', '23.1'],
  '19.6': ['25.2'], '19.8': ['25.3'],
  '20.4': ['6.1', '6.2'], '20.6': ['10.3'], '20.8': ['24.1', '24.2'],
};

// IB Diploma Programme Physics (first assessment 2025) — topic codes A.1–E.5.
export const IB_MAP = {
  '2.4': ['A.1'], '2.5': ['A.1'], '2.6': ['A.1'],
  '3.1': ['A.1'], '3.2': ['A.1'], '3.3': ['A.1'], '3.4': ['A.1'], '3.5': ['A.1'], '3.6': ['A.1'], '3.7': ['A.1', 'A.5'], '3.8': ['A.1'],
  '4.1': ['A.1'], '4.2': ['A.1'], '4.3': ['A.1'], '4.4': ['A.1'], '4.5': ['A.1'], '4.6': ['A.1'], '4.7': ['A.1'],
  '5.1': ['A.2'], '5.2': ['A.2'], '5.3': ['A.2'], '5.4': ['A.2'], '5.5': ['A.2'], '5.6': ['A.2'], '5.7': ['A.2'], '5.8': ['A.2'], '5.9': ['A.2'],
  '6.1': ['A.3'], '6.2': ['A.3'], '6.3': ['A.3'], '6.4': ['A.3'], '6.5': ['A.3'], '6.6': ['A.3'], '6.7': ['A.3'], '6.8': ['A.3'], '6.9': ['A.3'],
  '7.1': ['A.2'], '7.2': ['A.2'], '7.3': ['A.2'], '7.4': ['A.2'], '7.5': ['A.2'], '7.6': ['A.2'], '7.7': ['A.2'], '7.8': ['A.2'],
  '8.1': ['A.2'], '8.2': ['A.2'], '8.3': ['A.2'], '8.4': ['A.2'], '8.5': ['D.1'], '8.6': ['D.1'], '8.7': ['D.1'], '8.8': ['D.1'], '8.9': ['D.1'],
  '9.1': ['A.4'], '9.2': ['A.4'], '9.3': ['A.4'], '9.4': ['A.4'], '9.5': ['A.4'], '9.6': ['A.4'], '9.7': ['A.4'], '9.8': ['A.4'], '9.9': ['A.4'],
  '10.1': ['C.1'], '10.2': ['C.1'], '10.3': ['C.1'], '10.4': ['C.1'], '10.5': ['C.1'], '10.6': ['C.1'], '10.7': ['C.4'], '10.8': ['C.1'],
  '12.1': ['B.1'], '12.2': ['B.1'], '12.3': ['B.1'], '12.4': ['B.1'], '12.5': ['B.1'], '12.6': ['B.3'], '12.7': ['B.4'], '12.8': ['B.4'], '12.9': ['B.4'],
  '13.1': ['C.2'], '13.2': ['C.2'], '13.3': ['C.3'], '13.4': ['C.3'], '13.5': ['C.4'], '13.6': ['C.2'], '13.7': ['C.5'], '13.8': ['C.4'],
  '14.1': ['C.2'], '14.2': ['C.3'], '14.3': ['C.3'], '14.4': ['C.3'], '14.7': ['C.3'],
  '15.1': ['D.2'], '15.2': ['D.2'], '15.3': ['D.2'], '15.4': ['D.2'], '15.5': ['D.2'], '15.6': ['D.2'], '15.7': ['D.2'], '15.8': ['D.2'],
  '16.1': ['B.5'], '16.2': ['B.5'], '16.3': ['B.5'], '16.4': ['B.5'], '16.5': ['B.5'], '16.6': ['B.5'], '16.7': ['B.5'], '16.8': ['B.5'],
  '17.1': ['D.2'], '17.2': ['D.3'], '17.3': ['D.2'], '17.4': ['D.2'], '17.5': ['D.4'], '17.6': ['D.4'], '17.7': ['D.4'], '17.8': ['D.4'], '17.9': ['D.4'],
  '18.1': ['E.1'], '18.2': ['E.1'], '18.3': ['E.2'], '18.4': ['E.2'], '18.5': ['E.2'], '18.6': ['E.1'], '18.7': ['E.3'], '18.8': ['E.4', 'E.5'], '18.9': ['E.1', 'E.3'],
  '19.1': ['A.5'], '19.2': ['A.5'], '19.3': ['A.5'], '19.4': ['A.5'], '19.6': ['E.5'], '19.8': ['C.5'], '19.9': ['A.5'],
  '20.8': ['B.2'],   // Earth's energy balance: solar constant, albedo, Stefan–Boltzmann, greenhouse infrared absorption
};

// NGSS high-school performance expectations (three-dimensional; a lesson "supports" a PE — it does not by itself
// meet it, which also requires the science practice named in the PE).
export const NGSS_MAP = {
  '3.3': ['HS-PS2-1'], '5.3': ['HS-PS2-1'], '5.5': ['HS-PS2-1'], '5.8': ['HS-PS2-1'],
  '6.3': ['HS-PS3-2'], '6.4': ['HS-PS3-2'], '6.6': ['HS-PS3-1'], '6.7': ['HS-PS3-1'], '6.8': ['HS-PS3-3'],
  '7.2': ['HS-PS2-3'], '7.3': ['HS-PS2-2'], '7.4': ['HS-PS2-2'], '7.5': ['HS-PS2-2'], '7.6': ['HS-PS2-2'], '7.7': ['HS-PS2-2'],
  '8.5': ['HS-PS2-4'], '8.6': ['HS-PS2-4'], '8.7': ['HS-ESS1-4'], '8.8': ['HS-ESS1-4'],
  '12.1': ['HS-PS3-2'], '12.2': ['HS-PS3-2'], '12.3': ['HS-PS3-1', 'HS-PS3-4'], '12.5': ['HS-PS3-4'],
  '13.1': ['HS-PS4-1'], '13.2': ['HS-PS4-1'], '14.1': ['HS-PS4-1', 'HS-PS4-4'], '14.6': ['HS-PS4-5'], '14.7': ['HS-PS4-3'],
  '15.3': ['HS-PS2-4'], '15.4': ['HS-PS3-5'], '15.5': ['HS-PS3-2', 'HS-PS3-5'],
  '17.1': ['HS-PS3-5'], '17.3': ['HS-PS2-5'], '17.4': ['HS-PS2-5'], '17.6': ['HS-PS2-5'], '17.8': ['HS-PS3-3', 'HS-PS4-5'],
  '18.3': ['HS-PS4-4'], '18.4': ['HS-PS4-3'], '18.7': ['HS-PS1-8'], '18.8': ['HS-PS1-8', 'HS-ESS1-1'],
  '19.6': ['HS-ESS1-1', 'HS-ESS1-3'], '19.8': ['HS-ESS1-2'],
  '20.1': ['HS-ETS1-1', 'HS-ETS1-2'], '20.2': ['HS-ETS1-3'], '20.3': ['HS-ETS1-4'], '20.5': ['HS-PS3-3', 'HS-ETS1-1'], '20.6': ['HS-PS4-5'], '20.8': ['HS-PS4-4'], '20.9': ['HS-ETS1-2', 'HS-ETS1-3'],
};

const items = (src, pick) => src.items.filter(pick).map(i => ({ code: i.code, text: (i.title || i.text || '').replace(new RegExp('^' + i.code.replace('.', '\\.') + '\\s+'), ''), level: i.level || undefined }));
export const INTL = [
  { id: 'CAIE', name: 'Cambridge International AS & A Level Physics (9702)', short: 'Cambridge', group: 'International', level: `AS Level (topics 1–11) and A Level (topics 12–25); syllabus ${caie.syllabusYears || ''}`,
    source: caie.source, retrieved: caie.retrieved, items: items(caie, i => i.code.includes('.')), map: CAIE_MAP },
  { id: 'IB', name: 'IB Diploma Programme Physics (first assessment 2025)', short: 'IB DP', group: 'International', level: 'SL and HL; HL-only topics marked',
    source: ib.source, retrieved: ib.retrieved, items: items(ib, i => i.code.includes('.')), map: IB_MAP,
    note: `Concepts that permeate the course: ${Array.isArray(ib.concepts) ? ib.concepts.join(', ') : ib.concepts?.text || 'forces, energy and particles'}. The IB internal assessment (scientific investigation) is supported by the 20 labs and Unit 20 but is not itself provided.` },
  { id: 'NGSS', name: 'Next Generation Science Standards — High School (PS, ESS1, ETS1)', short: 'NGSS', group: 'United States (national)', level: 'Grades 9–12 performance expectations',
    source: ngss.source, retrieved: ngss.retrieved, items: items(ngss, () => true), map: NGSS_MAP,
    note: 'NGSS performance expectations are three-dimensional. A mapped lesson supports the disciplinary core idea; meeting the PE also requires the named science practice, which the linked labs and engines provide only in part.' },
];
