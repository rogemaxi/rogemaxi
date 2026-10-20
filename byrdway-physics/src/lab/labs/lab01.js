// Lab 1 — Measurement Lab. Repeated measurements of an object with instruments of different resolution.
// Each reading = accepted length + instrument bias + Gaussian reading scatter, rounded to the instrument's
// smallest division. The scatter comes from a seeded deterministic generator, so a given seed always
// reproduces the same data set.

const OBJECTS = {
  pencil: { L: 17.5362, label: 'Pencil' },
  coin: { L: 2.4257, label: 'Coin (diameter)' },
  book: { L: 21.5903, label: 'Textbook (width)' },
  bolt: { L: 4.8172, label: 'Bolt' },
};
// res = smallest division (cm), sigma = standard deviation of the reading scatter (cm), bias = systematic offset (cm)
const INSTRUMENTS = {
  stick: { res: 1, sigma: 0.3, bias: 0, label: 'Meter stick (1 cm divisions)' },
  ruler: { res: 0.1, sigma: 0.03, bias: 0, label: 'Ruler (1 mm divisions)' },
  caliper: { res: 0.002, sigma: 0.002, bias: 0, label: 'Vernier caliper (0.02 mm)' },
  offset: { res: 0.1, sigma: 0.03, bias: 0.3, label: 'Worn ruler (end worn off 3 mm)' },
};
const TRIAL = 0.4; // s of animation per trial

// mulberry32: small deterministic PRNG (uniform in [0, 1))
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
// Standard normal deviates by the Box–Muller transform.
export function gaussian(rand) {
  let u = rand(); while (u <= 1e-12) u = rand();
  const v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}
const DEC = { stick: 0, ruler: 1, caliper: 3, offset: 1 };
export const roundTo = (x, res, dec) => +(Math.round(x / res) * res).toFixed(dec);
// Significant figures of a value written with `dec` decimal places (leading zeros not significant).
export function sigFigs(value, dec) {
  const s = Math.abs(value).toFixed(dec).replace('.', '').replace(/^0+/, '');
  return s.length;
}
export function stats(xs) {
  const n = xs.length; if (!n) return { n: 0, mean: NaN, sd: NaN, sem: NaN };
  const mean = xs.reduce((a, b) => a + b, 0) / n;
  const sd = n > 1 ? Math.sqrt(xs.reduce((a, x) => a + (x - mean) ** 2, 0) / (n - 1)) : 0;
  return { n, mean, sd, sem: sd / Math.sqrt(n) };
}
// The data set a run produces (pure function of the parameters).
export function readings(p) {
  const O = OBJECTS[p.obj], I = INSTRUMENTS[p.inst], rand = mulberry32(p.seed * 7919 + 13);
  return Array.from({ length: p.n }, () => roundTo(O.L + I.bias + I.sigma * gaussian(rand), I.res, DEC[p.inst]));
}

export default {
  num: 1, unit: 1, sections: ['1.4', '1.5', '1.6', '1.7', '1.9'],
  dt: 1 / 60, sampleEvery: 0.1,
  text: {
    title: 'Measurement Lab',
    question: 'How do an instrument’s resolution and the number of repeated trials affect the precision, accuracy, and reported significant figures of a measurement?',
    params: { obj: 'Object', inst: 'Instrument', n: 'Number of trials', seed: 'Data-set seed' },
    options: {
      pencil: 'Pencil', coin: 'Coin (diameter)', book: 'Textbook (width)', bolt: 'Bolt',
      stick: 'Meter stick (1 cm divisions)', ruler: 'Ruler (1 mm divisions)', caliper: 'Vernier caliper (0.02 mm)', offset: 'Worn ruler (end worn off 3 mm)',
    },
    graph: ['readings and running mean (cm)', 'percent error (%)', 'uncertainty (cm)'],
    series: { reading: 'reading', mean: 'running mean', U: 'uncertainty U', sem: 'standard error s/√n' },
    measures: { rep: 'Reported value', resPct: 'Reading uncertainty / length', halfDiv: 'Reading uncertainty (½ division)', t: 'Time', k: 'Trial', reading: 'Latest reading', mean: 'Mean', sd: 'Standard deviation s', sem: 'Standard error s/√n', U: 'Uncertainty U', relU: 'Relative uncertainty', pe: 'Percent error', sig: 'Significant figures', accepted: 'Accepted value' },
    predict: {
      prompt: 'You will measure the pencil 10 times with the meter stick and then 10 times with the vernier caliper. How will the standard deviation of the caliper readings compare with the meter-stick readings?',
      choices: ['Much smaller', 'About the same', 'Much larger', 'Exactly zero'],
    },
    guided: [
      'Measure the pencil with the meter stick, 10 trials. Record the mean, the standard deviation, and the uncertainty U. Why is U equal to half a division here?',
      'Repeat with the ruler and then the vernier caliper (same object, same seed, 10 trials). How do U and the number of significant figures in the reported value change?',
      'Measure the bolt with the worn ruler and with the good ruler (10 trials each). Compare their standard deviations (precision) and percent errors (accuracy).',
      'With the ruler on the coin, run 4 trials and then 16 trials. Use the standard-error graph to explain why averaging more trials helps — and why it cannot remove the worn ruler’s offset.',
      'Convert your best caliper result for the coin to millimetres and to metres, keeping the same number of significant figures.',
    ],
    challenges: [
      'Make a measurement (at least 10 trials) whose percent error AND relative uncertainty are both below 0.1 %. Record the run.',
      'Show the difference between accuracy and precision: record a worn-ruler run and a good-ruler run of the same object (10 or more trials each) where the worn ruler’s percent error is at least 3× larger but its standard deviation is similar (within a factor of 2.5).',
      'Show that averaging reduces random uncertainty: record two runs with the same object and instrument (not the meter stick) where the second has at least 4× as many trials (first run ≥ 3 trials) and a smaller standard error s/√n.',
    ],
    evaluate: 'Before you run: the instrument’s smallest division is {res} cm and the object is about {L} cm long. Calculate the reading uncertainty (half the smallest division) as a percentage of the length.',
    honors: {
      prompt: 'Measure the coin’s diameter with the caliper (≥ 10 trials). Calculate its area A = πd²/4 and the uncertainty in A. Explain why the relative uncertainty in A is twice that of d.',
      solution: 'For A = πd²/4, the relative uncertainties add with the power as a factor: δA/A = 2·δd/d. Example: d = 2.426 ± 0.001 cm → A = π(2.426)²/4 = 4.622 cm², δA/A = 2 × 0.001/2.426 = 0.082 %, δA = 0.004 cm², so A = 4.622 ± 0.004 cm².',
    },
    assumptions: [
      'Each object has a single accepted (“true”) length; the object itself does not vary between trials.',
      'Random reading scatter is Gaussian with a fixed standard deviation for each instrument (meter stick 0.3 cm, ruler 0.03 cm, caliper 0.002 cm) and is generated by a seeded pseudo-random generator, so a seed always reproduces the same data.',
      'Each reading is rounded to the instrument’s smallest division (no estimating between marks). The worn ruler adds a constant +0.3 cm systematic offset; no other systematic errors are modelled.',
      'Reported uncertainty U is the larger of half the smallest division and the standard error s/√n; it is quoted to one significant figure and the mean is rounded to the same decimal place, which sets the significant figures.',
      'The caliper is treated as a long-jaw caliper able to measure every object. The sliding red marker is only a picture of the latest reading.',
    ],
  },
  params: [
    { id: 'obj', value: 'pencil', options: Object.entries(OBJECTS).map(([value, o]) => ({ value, label: o.label })) },
    { id: 'inst', value: 'stick', options: Object.entries(INSTRUMENTS).map(([value, o]) => ({ value, label: o.label })) },
    { id: 'n', min: 1, max: 25, step: 1, value: 10, unit: '' },
    { id: 'seed', min: 1, max: 99, step: 1, value: 1, unit: '' },
  ],
  camera: { target: [11, 0, 0], dist: 32, free: [0.05, 0.75, 1] },
  view2d: { plane: 'xz', span: 30, cx: 11, cy: 0 },
  graph: {
    choices: [
      { label: 'readings and running mean (cm)', x: 'k', xLabel: 'trial n', y: ['reading', 'mean'], labels: ['reading', 'mean'], yLabel: 'length (cm)' },
      { label: 'percent error (%)', x: 'k', xLabel: 'trial n', y: ['pe'], labels: ['pe'], yLabel: 'percent error (%)' },
      { label: 'uncertainty (cm)', x: 'k', xLabel: 'trial n', y: ['U', 'sem'], labels: ['U', 'sem'], yLabel: 'uncertainty (cm)' },
    ],
  },
  recordKeys: ['k', 'mean', 'sd', 'U', 'pe', 'sig'],
  decor: p => {
    const I = INSTRUMENTS[p.inst], L = OBJECTS[p.obj].L, len = Math.max(25, Math.ceil(L + 3));
    const step = p.inst === 'stick' ? 1 : 0.1, ticks = [];
    for (let i = 0; i * step <= len + 1e-9; i++) {
      const v = i * step, major = Math.abs(v - Math.round(v)) < 1e-6;
      const h = major ? 0.9 : (Math.abs(v * 2 - Math.round(v * 2)) < 1e-6 ? 0.6 : 0.35);
      const xs = v - I.bias; // the worn ruler's "0" mark sits 0.3 cm short of the true zero edge, so it reads 0.3 cm high
      ticks.push({ shape: 'line', pts: [[xs, 0.63, 2.2], [xs, 0.63, 2.2 - h]], color: '#0f172a' });
      if (major && Math.round(v) % 5 === 0) ticks.push({ shape: 'label', text: `${Math.round(v)}`, pos: [xs, 0.65, 3.0], color: '#e2e8f0' });
    }
    return [
      { shape: 'ground', size: 120, divisions: 24 },
      { shape: 'box', size: [len + 6, 0.5, 14], pos: [len / 2, 0.25, 0], color: '#3f2d1d' }, // lab bench
      { shape: 'box', size: [len + 0.6, 0.12, 2.2], pos: [len / 2 - 0.3, 0.56, 3.3 - 2.2], color: p.inst === 'caliper' ? '#cbd5e1' : '#facc15', metal: p.inst === 'caliper' ? 0.8 : 0.05 },
      ...ticks,
      { shape: 'box', size: [0.15, 0.7, 6], pos: [-0.08, 0.85, 0], color: '#64748b' }, // stop block at true zero
      { shape: 'label', text: I.label, pos: [len / 2, 0.7, 5.2], color: '#fde68a' },
    ];
  },
  create(p) {
    const O = OBJECTS[p.obj], I = INSTRUMENTS[p.inst];
    const data = readings(p);
    const s = { t: 0, k: 0, done: false, events: [] };
    const cur = () => {
      const st = stats(data.slice(0, s.k));
      const U = s.k ? Math.max(I.res / 2, st.sem) : NaN;
      const Ur = s.k ? Number(U.toPrecision(1)) : NaN, decU = s.k ? Math.max(0, -Math.floor(Math.log10(Ur) + 1e-9)) : 0;
      const rep = s.k ? +st.mean.toFixed(decU) : NaN;
      return { ...st, U, Ur, decU, rep, pe: s.k ? Math.abs(st.mean - O.L) / O.L * 100 : NaN };
    };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events, data,
      get reportedValue() { return cur().rep; },
      step(dt) {
        s.t += dt;
        while (s.k < p.n && s.t >= (s.k + 1) * TRIAL - 1e-9) {
          s.k++;
          s.events.push({ type: 'spark', pos: [data[s.k - 1], 0.9, 0], strength: 0.15, speed: 0.3, color: '#f87171', life: 0.4 });
        }
        if (s.k >= p.n && s.t >= p.n * TRIAL + 0.2 - 1e-9) s.done = true;
      },
      measures() {
        const c = cur();
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'k', label: 'Trial', value: s.k, unit: '', ref: p.n },
          { id: 'reading', label: 'Latest reading', value: s.k ? data[s.k - 1] : NaN, unit: 'cm', ref: 25 },
          { id: 'mean', label: 'Mean', value: c.mean, unit: 'cm', ref: 25 },
          { id: 'rep', label: 'Reported value', value: c.rep, unit: 'cm', ref: 25 },
          { id: 'sd', label: 'Standard deviation s', value: s.k ? c.sd : NaN, unit: 'cm', ref: 0.5 },
          { id: 'sem', label: 'Standard error s/√n', value: s.k ? c.sem : NaN, unit: 'cm', ref: 0.5, hidden: true },
          { id: 'U', label: 'Uncertainty U', value: c.U, unit: 'cm', ref: 0.5 },
          { id: 'relU', label: 'Relative uncertainty', value: s.k ? c.U / c.mean * 100 : NaN, unit: '%', ref: 20 },
          { id: 'pe', label: 'Percent error', value: c.pe, unit: '%', ref: 10 },
          { id: 'sig', label: 'Significant figures', value: s.k ? sigFigs(c.rep, c.decU) : NaN, unit: '', ref: 5 },
          { id: 'halfDiv', label: 'Reading uncertainty (½ division)', value: I.res / 2, unit: 'cm', hidden: true },
          { id: 'resPct', label: 'Reading uncertainty / length', value: (I.res / 2) / O.L * 100, unit: '%', ref: 5 },
          { id: 'accepted', label: 'Accepted value', value: O.L, unit: 'cm', hidden: true },
        ];
      },
      reported() { const c = cur(); return s.k ? `${c.rep.toFixed(c.decU)} ± ${c.Ur} cm` : '—'; },
      energy() { return []; },
      scene() {
        const L = O.L, bodies = [];
        if (p.obj === 'pencil') {
          bodies.push({ id: 'obj', shape: 'cylinder', r: 0.35, h: L - 1.6, pos: [(L - 1.6) / 2, 0.85, -0.5], rot: [0, 0, Math.PI / 2], color: '#f59e0b' });
          bodies.push({ id: 'tip', shape: 'cone', r: 0.35, h: 1.6, pos: [L - 0.8, 0.85, -0.5], rot: [0, 0, -Math.PI / 2], color: '#e7c9a0' });
        } else if (p.obj === 'coin') bodies.push({ id: 'obj', shape: 'cylinder', r: L / 2, h: 0.2, pos: [L / 2, 0.6, -1.3], color: '#d4a373', metal: 0.8 });
        else if (p.obj === 'book') bodies.push({ id: 'obj', shape: 'box', size: [L, 2.5, 8], pos: [L / 2, 1.75, -4.5], color: '#1d4ed8' });
        else {
          bodies.push({ id: 'obj', shape: 'cylinder', r: 0.4, h: L - 0.6, pos: [(L - 0.6) / 2 + 0.6, 0.9, -0.5], rot: [0, 0, Math.PI / 2], color: '#9ca3af', metal: 0.9 });
          bodies.push({ id: 'head', shape: 'box', size: [0.6, 1.3, 1.3], pos: [0.3, 0.9, -0.5], color: '#9ca3af', metal: 0.9 });
        }
        const r = s.k ? data[s.k - 1] : null;
        if (r != null) bodies.push({ id: 'mark', shape: 'box', size: [0.08, 0.4, 3.2], pos: [r - I.bias, 0.8, 1.2], color: '#ef4444', emissive: '#ef4444', glow: 0.6, label: `#${s.k}: ${r.toFixed(DEC[p.inst])} cm` });
        if (p.inst === 'caliper') bodies.push({ id: 'jaw', shape: 'box', size: [0.4, 0.5, 4], pos: [(r ?? L) + 0.2, 0.9, -0.6], color: '#cbd5e1', metal: 0.8 });
        return {
          bodies,
          vectors: [{ id: 'len', from: [0, 2.6, 0], vec: [L, 0, 0], color: '#4ade80', label: `accepted ${L} cm` }],
        };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    const I = INSTRUMENTS[p.inst], f = (x, d = 4) => (Number.isFinite(x) ? x.toFixed(d) : '—');
    return [
      `mean = Σx/n = ${f(m.mean)} cm  (n = ${m.k})`,
      `s = √[Σ(x − mean)²/(n − 1)] = ${f(m.sd)} cm;  s/√n = ${f(m.sem)} cm`,
      `U = max(½ × ${I.res}, s/√n) = ${f(m.U)} cm  →  reported ${model.reported()}`,
      `percent error = |${f(m.mean)} − ${m.accepted}| / ${m.accepted} × 100 = ${f(m.pe, 3)} %`,
      `significant figures in reported value: ${Number.isFinite(m.sig) ? m.sig : '—'}`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.final.k >= 10 && r.final.pe < 0.1 && r.final.relU < 0.1),
    ({ runs }) => runs.some(a => a.params.inst === 'offset' && a.final.k >= 10 && runs.some(b => b.params.inst === 'ruler' && b.params.obj === a.params.obj && b.final.k >= 10 &&
      a.final.pe >= 3 * b.final.pe && a.final.sd > 0 && b.final.sd > 0 && a.final.sd / b.final.sd <= 2.5 && b.final.sd / a.final.sd <= 2.5)),
    ({ runs }) => runs.some(a => a.params.inst !== 'stick' && a.final.k >= 3 && runs.some(b => b !== a && b.params.inst === a.params.inst && b.params.obj === a.params.obj &&
      b.final.k >= 4 * a.final.k && b.final.sem < a.final.sem)),
  ],
  evaluate(p) {
    const I = INSTRUMENTS[p.inst], L = OBJECTS[p.obj].L;
    return { vars: { res: I.res, L }, answer: (I.res / 2) / L * 100, unit: '%', tol: 0.02 };
  },
};
