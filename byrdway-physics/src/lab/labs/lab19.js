// Lab 19 — Quantum Discovery Lab. Two modes on one bench:
//  • Photoelectric effect: monochromatic light (wavelength λ, intensity) falls on a metal of work function φ inside a
//    vacuum tube. Each photon of energy hf > φ ejects one electron with kinetic energy between 0 and Kmax = hf − φ;
//    a retarding voltage V between emitter and collector turns back every electron with K < eV, so the photocurrent
//    falls to zero at the stopping voltage Vstop = Kmax/e.
//  • Hydrogen spectrum: a Bohr-model electron drops from level nU to nL and emits one photon of energy
//    ΔE = E(nU) − E(nL) with En = −13.6 eV/n², i.e. λ = hc/ΔE.
import { C, photonEnergyEV, photoelectricKmax, thresholdWavelength, bohrEnergyEV, hydrogenLineNm } from '../../physics/index.js';

const GAP = 3;           // emitter → collector distance in the scene (m, schematic)
const Y0 = 1.2;          // tube axis height
const C0 = 1.6;          // scene speed (m/s) of an electron with 1 eV kinetic energy: v = C0·√(K/eV) (slowed for viewing)
const RATE = 0.4;        // photons per second reaching the emitter per 1 % intensity
const T_PHOTO = 10, T_H = 5, T_JUMP = 1; // run lengths and the moment of the hydrogen transition, s
const PHI = 0.6180339887498949;          // golden-ratio fraction: deterministic, evenly spread electron energies
const HC = C.h * C.c / C.eV * 1e9;       // hc in eV·nm (≈ 1239.84)
const rn = n => 0.13 * n * n;            // Bohr orbit radius ∝ n² (scene units, schematic)
const ATOM = [-1, Y0, 0];
const LAMP = [1.4, 3.6, 1.4];
const ladderY = E => 3 + 0.4 * E;        // energy-level diagram: y position of a level of energy E (eV)
const METALS = [
  { value: 2.10, label: 'Cesium (φ = 2.10 eV)' },
  { value: 2.30, label: 'Potassium (φ = 2.30 eV)' },
  { value: 2.28, label: 'Sodium (φ = 2.28 eV)' },
  { value: 2.87, label: 'Calcium (φ = 2.87 eV)' },
  { value: 4.33, label: 'Zinc (φ = 4.33 eV)' },
  { value: 4.70, label: 'Copper (φ = 4.70 eV)' },
  { value: 5.65, label: 'Platinum (φ = 5.65 eV)' },
];
const frac = x => x - Math.floor(x);
const seriesName = nL => ({ 1: 'Lyman (UV)', 2: 'Balmer (visible/near-UV)', 3: 'Paschen (IR)', 4: 'Brackett (IR)', 5: 'Pfund (IR)' }[nL] || '');

// Approximate display colour of a wavelength (visual only). UV is drawn violet-white, IR dark red.
export function wavelengthColor(nm) {
  if (nm < 380) return '#c4b5fd';
  if (nm > 750) return '#7f1d1d';
  let r = 0, g = 0, b = 0;
  if (nm < 440) { r = (440 - nm) / 60; b = 1; } else if (nm < 490) { g = (nm - 440) / 50; b = 1; }
  else if (nm < 510) { g = 1; b = (510 - nm) / 20; } else if (nm < 580) { r = (nm - 510) / 70; g = 1; }
  else if (nm < 645) { r = 1; g = (645 - nm) / 65; } else r = 1;
  const h = v => Math.round(255 * Math.min(1, v) ** 0.8).toString(16).padStart(2, '0');
  return '#' + h(r) + h(g) + h(b);
}

function photoNumbers(p) {
  const E = photonEnergyEV(p.lambda * 1e-9);
  const K = photoelectricKmax(p.lambda * 1e-9, p.phi);
  const Kmax = Math.max(0, K);
  return { E, Kmax, emits: K > 0, Vstop: Kmax, lam0: thresholdWavelength(p.phi) * 1e9, f: C.c / (p.lambda * 1e-9) };
}
function hNumbers(p) {
  const Eu = bohrEnergyEV(p.nU), El = bohrEnergyEV(p.nL), ok = p.nU > p.nL;
  return { Eu, El, ok, dE: ok ? Eu - El : 0, lam: ok ? hydrogenLineNm(p.nU, p.nL) : 0 };
}
// fraction of ejected electrons that reach the collector against a retarding voltage V (energies spread evenly on 0…Kmax)
const collectFraction = (V, Kmax) => (Kmax <= 0 ? 0 : V <= 0 ? 1 : Math.max(0, 1 - V / Kmax));

export default {
  num: 19, unit: 18, sections: ['18.1', '18.2', '18.3', '18.4'],
  text: {
    title: 'Quantum Discovery Lab',
    question: 'Why does the colour (frequency) of light — not its brightness — decide whether a metal releases electrons, and why does hydrogen emit only certain colours?',
    params: { mode: 'Experiment', lambda: 'Light wavelength λ', I: 'Light intensity', phi: 'Metal (work function φ)', V: 'Retarding voltage V', nU: 'Upper level nU (hydrogen)', nL: 'Lower level nL (hydrogen)' },
    options: { photo: 'Photoelectric effect', hydrogen: 'Hydrogen spectrum (Bohr model)' },
    graph: ['electrons emitted and collected', 'photocurrent (electrons/s)', 'photon, work-function and Kmax energies (eV)', 'hydrogen electron energy (eV)'],
    series: { emitted: 'emitted', collected: 'collected', photon: 'photon hf', work: 'work function φ', kmax: 'Kmax' },
    measures: {
      t: 'Time', E: 'Photon energy hf', f: 'Frequency f', phi: 'Work function φ', Kmax: 'Max kinetic energy Kmax', Vstop: 'Stopping voltage', V: 'Retarding voltage', lam0: 'Threshold wavelength λ0',
      Ne: 'Electrons emitted', Nc: 'Electrons reaching collector', rate: 'Photocurrent', Np: 'Photons absorbed',
      n: 'Electron level n', Eel: 'Electron energy En', Eu: 'Upper level energy', El: 'Lower level energy', dE: 'Emitted photon energy', lamH: 'Emitted wavelength',
    },
    predict: {
      prompt: 'Red light (700 nm) shines on sodium (φ = 2.28 eV) and no electrons come out. You turn the intensity up from 25 % to 100 %. What will happen?',
      choices: ['Electrons start to come out because the light is brighter', 'Still no electrons — each photon has too little energy', 'A few slow electrons come out', 'Electrons come out with four times the energy'],
    },
    guided: [
      'Photoelectric mode, sodium, V = 0. Start at λ = 700 nm and shorten the wavelength in 10 nm steps. Record the first wavelength that releases electrons and compare it with λ0 = hc/φ.',
      'At λ = 400 nm on sodium, run with intensity 25 %, 50 % and 100 %. Compare the electron counts and Kmax. Which one does intensity change?',
      'Keep λ = 400 nm and raise the retarding voltage in 0.2 V steps. Watch the collected count fall. Find the voltage where it reaches zero and show that eVstop = hf − φ.',
      'Repeat the stopping-voltage measurement at three wavelengths. Plot Vstop against f: the slope is h/e and the intercept on the f-axis is the threshold frequency.',
      'Hydrogen mode: run every transition that ends on nL = 2. Record the wavelengths and identify which are visible (the Balmer series).',
    ],
    challenges: [
      'Pin down a threshold: with one metal, record a run that emits electrons and a run that emits none, with wavelengths no more than 10 nm apart.',
      'Measure a stopping voltage: in a run that emits at least 20 electrons, set V so that none reach the collector but V is no more than 0.10 V above the true stopping voltage.',
      'Show that intensity changes the number but not the energy: record two emitting runs with the same λ, metal and V = 0, where one intensity is at least double the other and the electron counts scale with intensity (±10 %).',
      'Hydrogen mode: produce the red Balmer line — a run whose emitted photon has a wavelength between 640 nm and 670 nm.',
    ],
    evaluate: 'Before you run: light of wavelength {lambda} nm falls on a metal with work function φ = {phi} eV. Calculate the stopping voltage (use hc = 1240 eV·nm). Enter 0 if no electrons are emitted.',
    honors: {
      prompt: 'Using only stopping-voltage measurements on one metal at several wavelengths, determine Planck’s constant and the work function. Explain the graph you would draw and test it.',
      solution: 'Einstein: eVstop = hf − φ, so Vstop = (h/e)·f − φ/e. Measure Vstop at several λ (f = c/λ), plot Vstop against f: slope = h/e ≈ 4.14×10⁻¹⁵ V·s → h = slope × e ≈ 6.63×10⁻³⁴ J·s; the vertical intercept is −φ/e. Example on sodium: 300 nm → 1.85 V, 400 nm → 0.82 V; slope = (1.85 − 0.82)/(9.99 − 7.49)×10¹⁴ = 4.13×10⁻¹⁵ V·s, φ = hf − eV = 4.13 − 1.85 = 2.28 eV.',
    },
    assumptions: [
      'Ideal photoelectric model: every photon with hf > φ ejects exactly one electron (quantum efficiency 1); photons with hf ≤ φ eject none, regardless of intensity. Intensity sets the photon rate (0.4 photons/s per 1 % here — far below a real lamp, so individual events can be seen).',
      'Ejected electrons have kinetic energies spread evenly between 0 and Kmax = hf − φ (a deterministic, evenly spaced sequence). Real energy distributions are not exactly uniform, but the maximum Kmax and the stopping voltage are exact.',
      'An electron is counted as reaching the collector when it leaves the emitter with K > eV (energy conservation in the uniform retarding field); the slowed-down flight shown afterwards follows K(x) = K0 − eV·x/d. Real transit times are nanoseconds.',
      'Contact potentials, the collector’s own work function, space charge and thermionic emission are ignored. Work functions are typical textbook values.',
      'Hydrogen uses the Bohr model En = −13.6 eV/n²; one electron makes one downward jump at t = 1 s and emits one photon of energy ΔE. Orbit radii (∝ n²) and orbital speeds are schematic, not to scale.',
      'Photon and electron colours, the glow and plate sparks are visual only. Ultraviolet is drawn pale violet and infrared dark red because neither is visible.',
    ],
  },
  params: [
    { id: 'mode', value: 'photo', options: [{ value: 'photo', label: 'Photoelectric effect' }, { value: 'hydrogen', label: 'Hydrogen spectrum (Bohr model)' }] },
    { id: 'lambda', min: 150, max: 800, step: 5, value: 400, unit: 'nm' },
    { id: 'I', min: 0, max: 100, step: 5, value: 50, unit: '%' },
    { id: 'phi', value: 2.28, options: METALS },
    { id: 'V', min: -2, max: 6, step: 0.05, value: 0, unit: 'V' },
    { id: 'nU', min: 2, max: 6, step: 1, value: 3, unit: '' },
    { id: 'nL', min: 1, max: 5, step: 1, value: 2, unit: '' },
  ],
  camera: { target: [1.6, 1.0, 0], dist: 13, free: [0.25, 0.3, 1] },
  view2d: { span: 15, cx: 1.6, cy: 1.0 },
  graph: {
    choices: [
      { label: 'electrons emitted and collected', y: ['Ne', 'Nc'], labels: ['emitted', 'collected'], yLabel: 'electrons' },
      { label: 'photocurrent (electrons/s)', y: ['rate'], labels: ['rate'], yLabel: 'electrons/s' },
      { label: 'photon, work-function and Kmax energies (eV)', y: ['E', 'phi', 'Kmax'], labels: ['photon', 'work', 'kmax'], yLabel: 'E (eV)' },
      { label: 'hydrogen electron energy (eV)', y: ['Eel'], labels: ['Eel'], yLabel: 'En (eV)' },
    ],
  },
  recordKeys: ['E', 'Kmax', 'Vstop', 'Ne', 'Nc', 'lamH'],
  decor(p) {
    if (p.mode === 'hydrogen') {
      const out = [];
      for (let n = 1; n <= 6; n++) out.push({ shape: 'torus', r: rn(n), tube: 0.012, pos: ATOM, color: n === p.nU || n === p.nL ? '#94a3b8' : '#334155' });
      for (let n = 1; n <= 6; n++) {
        const E = bohrEnergyEV(n), y = ladderY(E);
        out.push({ shape: 'line', pts: [[4.2, y, 0], [6.4, y, 0]], color: n === p.nU || n === p.nL ? '#e2e8f0' : '#64748b' });
        if (n <= 4 || n === 6) out.push({ shape: 'label', text: n === 6 ? 'n = 5, 6 …' : `n = ${n}  ${E.toFixed(2)} eV`, pos: [7.6, y, 0] });
      }
      out.push({ shape: 'line', pts: [[4.2, ladderY(0), 0], [6.4, ladderY(0), 0]], color: '#475569', opacity: 0.6 });
      out.push({ shape: 'label', text: '0 eV (ionized)', pos: [7.6, ladderY(0) + 0.25, 0] });
      // visible spectrum strip 380–750 nm
      for (let i = 0; i < 37; i++) out.push({ shape: 'box', size: [8 / 37 + 0.01, 0.25, 0.3], pos: [-4 + (i + 0.5) * 8 / 37, -2.7, 0], color: wavelengthColor(380 + (i + 0.5) * 10) });
      out.push({ shape: 'label', text: '← UV', pos: [-4.7, -2.7, 0] }, { shape: 'label', text: 'IR →', pos: [4.7, -2.7, 0] });
      out.push({ shape: 'label', text: '380 nm', pos: [-4, -3.1, 0] }, { shape: 'label', text: '750 nm', pos: [4, -3.1, 0] });
      return out;
    }
    const metal = METALS.find(m => m.value === p.phi)?.label.split(' (')[0] || 'Metal';
    const beam = wavelengthColor(p.lambda);
    return [
      { shape: 'box', size: [7, 0.2, 3], pos: [GAP / 2, -0.95, 0], color: '#1e293b' },
      { shape: 'cylinder', r: 1.05, h: GAP + 1.2, pos: [GAP / 2, Y0, 0], rot: [0, 0, Math.PI / 2], color: '#93c5fd', opacity: 0.1 },
      { shape: 'box', size: [0.1, 1.5, 1.3], pos: [-0.05, Y0, 0], color: '#cbd5e1', metal: 0.8 },
      { shape: 'box', size: [0.1, 1.5, 1.3], pos: [GAP + 0.05, Y0, 0], color: '#64748b', metal: 0.8 },
      { shape: 'label', text: `emitter: ${metal}`, pos: [-0.3, Y0 + 1.25, 0] },
      { shape: 'label', text: 'collector', pos: [GAP + 0.3, Y0 + 1.25, 0] },
      // circuit: emitter and collector wired to an adjustable supply (box) with a meter
      { shape: 'line', pts: [[-0.1, Y0 - 0.75, 0], [-0.1, -0.5, 0], [1.0, -0.5, 0]], color: '#94a3b8' },
      { shape: 'line', pts: [[GAP + 0.1, Y0 - 0.75, 0], [GAP + 0.1, -0.5, 0], [2.0, -0.5, 0]], color: '#94a3b8' },
      { shape: 'box', size: [1, 0.5, 0.5], pos: [1.5, -0.5, 0], color: '#334155' },
      { shape: 'label', text: `supply V = ${p.V.toFixed(2)} V (${p.V >= 0 ? 'retarding' : 'accelerating'})`, pos: [1.5, -1.25, 0] },
      { shape: 'line', pts: [LAMP, [0.02, Y0, 0]], color: p.I > 0 ? beam : '#334155', opacity: 0.35 },
      { shape: 'label', text: `λ = ${p.lambda} nm`, pos: [LAMP[0], LAMP[1] + 0.7, LAMP[2]] },
    ];
  },
  create(p) {
    const ph = photoNumbers(p), hy = hNumbers(p), R = RATE * p.I;
    const hydrogen = p.mode === 'hydrogen';
    const aRet = C0 * C0 * p.V / (2 * GAP); // scene deceleration toward the emitter (negative V accelerates)
    const s = { t: 0, k: 1, Np: 0, Ne: 0, Nc: 0, done: false, events: [], electrons: [], n: p.nU, th: 0, jumped: false, tJump: null };
    const emit = (k, tk) => {
      s.Np++;
      if (!ph.emits) return;
      const K = ph.Kmax * frac(k * PHI); // ∈ (0, Kmax)
      s.Ne++;
      const reaches = p.V <= 0 || K > p.V;
      if (reaches) s.Nc++;
      if (s.electrons.length < 80) s.electrons.push({ t0: tk, K0: K, v0: C0 * Math.sqrt(K), y: Y0 + 1.1 * (frac(k * 0.7548776662) - 0.5), z: 1.0 * (frac(k * 0.5698402910) - 0.5) });
      if (k % 3 === 0) s.events.push({ type: 'spark', pos: [0.05, Y0, 0], strength: 0.15, speed: 0.4, color: '#7dd3fc', life: 0.35 });
    };
    // exact flight of an electron in the uniform field: x = v0·τ − ½·a·τ²
    const eState = e => { const tau = s.t - e.t0; return { x: e.v0 * tau - 0.5 * aRet * tau * tau, v: e.v0 - aRet * tau, tau }; };
    const omega = n => 5 / (n * n * n); // Bohr: angular speed ∝ 1/n³ (schematic scale)
    const model = {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        s.t += dt;
        if (hydrogen) {
          s.th += omega(s.n) * dt;
          if (!s.jumped && hy.ok && s.t >= T_JUMP - 1e-9) {
            s.jumped = true; s.tJump = s.t; s.n = p.nL;
            s.events.push({ type: 'burst', pos: [ATOM[0] + rn(p.nL), ATOM[1], 0], strength: 0.4, color: wavelengthColor(hy.lam), life: 0.6 });
          }
          if (s.t >= T_H - 1e-9) s.done = true;
          return;
        }
        while (R > 0 && s.k / R <= s.t + 1e-9) { emit(s.k, s.k / R); s.k++; }
        s.electrons = s.electrons.filter(e => { const st = eState(e); return st.x >= 0 && st.x <= GAP && st.tau < 20; });
        if (s.t >= T_PHOTO - 1e-9) s.done = true;
      },
      // electrons in flight (for tests and the scene): position x (scene m from the emitter), speed, start energy
      electrons() { return s.electrons.map(e => ({ ...eState(e), K0: e.K0 })); },
      measures() {
        const Eel = bohrEnergyEV(s.n);
        const after = s.jumped;
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'E', label: 'Photon energy hf', value: ph.E, unit: 'eV', ref: 8, hidden: hydrogen },
          { id: 'f', label: 'Frequency f', value: ph.f / 1e14, unit: '×10¹⁴ Hz', ref: 20, hidden: hydrogen },
          { id: 'phi', label: 'Work function φ', value: p.phi, unit: 'eV', ref: 6, hidden: hydrogen },
          { id: 'Kmax', label: 'Max kinetic energy Kmax', value: ph.Kmax, unit: 'eV', ref: 6, hidden: hydrogen },
          { id: 'Vstop', label: 'Stopping voltage', value: ph.Vstop, unit: 'V', ref: 6, hidden: hydrogen },
          { id: 'V', label: 'Retarding voltage', value: p.V, unit: 'V', hidden: true },
          { id: 'lam0', label: 'Threshold wavelength λ0', value: ph.lam0, unit: 'nm', ref: 800, hidden: hydrogen },
          { id: 'Np', label: 'Photons absorbed', value: s.Np, unit: '', hidden: true },
          { id: 'Ne', label: 'Electrons emitted', value: s.Ne, unit: '', ref: 400, hidden: hydrogen },
          { id: 'Nc', label: 'Electrons reaching collector', value: s.Nc, unit: '', ref: 400, hidden: hydrogen },
          { id: 'rate', label: 'Photocurrent', value: s.t > 0 ? s.Nc / s.t : 0, unit: 'electrons/s', ref: 40, hidden: hydrogen },
          { id: 'n', label: 'Electron level n', value: s.n, unit: '', ref: 6, hidden: !hydrogen },
          { id: 'Eel', label: 'Electron energy En', value: Eel, unit: 'eV', ref: 13.6, hidden: !hydrogen },
          { id: 'Eu', label: 'Upper level energy', value: hy.Eu, unit: 'eV', ref: 13.6, hidden: !hydrogen },
          { id: 'El', label: 'Lower level energy', value: hy.El, unit: 'eV', ref: 13.6, hidden: !hydrogen },
          { id: 'dE', label: 'Emitted photon energy', value: after ? hy.dE : 0, unit: 'eV', ref: 13.6, hidden: !hydrogen },
          { id: 'lamH', label: 'Emitted wavelength', value: after ? hy.lam : 0, unit: 'nm', ref: 2000, hidden: !hydrogen },
        ];
      },
      energy() {
        const J = x => x * C.eV;
        if (hydrogen) return s.jumped ? [{ label: 'Level drop ΔE', value: J(hy.dE), color: '#a5b4fc' }, { label: 'Photon hf', value: J(hy.dE), color: wavelengthColor(hy.lam) }] : [];
        if (p.I === 0) return [];
        return [
          { label: 'Photon hf', value: J(ph.E), color: wavelengthColor(p.lambda) },
          { label: 'Work function φ', value: J(Math.min(ph.E, p.phi)), color: '#94a3b8' },
          { label: 'Kmax', value: J(ph.Kmax), color: '#7dd3fc' },
        ];
      },
      scene() {
        if (hydrogen) {
          let r = rn(s.n);
          if (s.jumped && s.t - s.tJump < 0.25) { const k = (s.t - s.tJump) / 0.25; r = rn(p.nU) + (rn(p.nL) - rn(p.nU)) * k; }
          const ePos = [ATOM[0] + r * Math.cos(s.th), ATOM[1] + r * Math.sin(s.th), 0];
          const bodies = [
            { id: 'nuc', shape: 'sphere', r: 0.12, pos: ATOM, color: '#f87171', emissive: '#f87171', glow: 0.4, label: 'proton' },
            { id: 'el', shape: 'sphere', r: 0.09, pos: ePos, color: '#7dd3fc', emissive: '#38bdf8', glow: 0.6, label: `n = ${s.n}` },
            { id: 'lvl', shape: 'sphere', r: 0.08, pos: [5.3, ladderY(bohrEnergyEV(s.n)), 0], color: '#7dd3fc', emissive: '#38bdf8', glow: 0.6 },
          ];
          const vectors = [];
          if (s.jumped) {
            const col = wavelengthColor(hy.lam), d = 2.2 * (s.t - s.tJump), dir = [-0.6, -0.8];
            const start = [ATOM[0] + rn(p.nL), ATOM[1], 0];
            const along = Math.min(d, 3.6), pos = [start[0] + dir[0] * along, start[1] + dir[1] * along, 0];
            bodies.push({ id: 'ph', shape: 'sphere', r: 0.1, pos, color: col, emissive: col, glow: 1.2, trail: true, label: `γ  ${hy.lam.toFixed(0)} nm` });
            const lx = hy.lam < 380 ? -4.4 : hy.lam > 750 ? 4.4 : -4 + 8 * (hy.lam - 380) / 370;
            if (d >= 3.6) bodies.push({ id: 'line', shape: 'box', size: [0.06, 0.55, 0.35], pos: [lx, -2.7, 0.05], color: '#ffffff', emissive: col, glow: 1.5, label: `${hy.lam.toFixed(1)} nm` });
            vectors.push({ id: 'jump', from: [5.0, ladderY(hy.Eu), 0], vec: [0, ladderY(hy.El) - ladderY(hy.Eu), 0], color: col, label: `ΔE = ${hy.dE.toFixed(3)} eV` });
          }
          return { bodies, vectors };
        }
        const col = wavelengthColor(p.lambda);
        const bodies = [
          { id: 'lamp', shape: 'cone', r: 0.35, h: 0.6, pos: LAMP, rot: [0, 0, Math.PI * 0.75], color: '#475569', emissive: p.I > 0 ? col : null, glow: p.I / 100 },
        ];
        // photons in flight from the lamp (visual): photon k reaches the emitter at t = k/R after a 0.6 s flight
        if (R > 0) {
          const tau = 0.6, k0 = Math.max(1, Math.ceil(s.t * R - 1e-9)), k1 = Math.floor((s.t + tau) * R);
          for (let k = Math.max(k0, k1 - 30); k <= k1; k++) {
            const u = 1 - (k / R - s.t) / tau; if (u < 0 || u > 1) continue;
            const tgt = [0.06, Y0 + 1.1 * (frac(k * 0.7548776662) - 0.5), 1.0 * (frac(k * 0.5698402910) - 0.5)];
            bodies.push({ id: 'p' + (k % 40), shape: 'sphere', r: 0.06, pos: LAMP.map((a, i) => a + (tgt[i] - a) * u), color: col, emissive: col, glow: 1.4 });
          }
        }
        const vectors = [];
        let shown = 0;
        for (const e of s.electrons) {
          const st = eState(e); if (st.x < 0 || st.x > GAP) continue;
          const pos = [st.x + 0.08, e.y, e.z];
          bodies.push({ id: 'e' + (shown % 80), shape: 'sphere', r: 0.06, pos, color: '#38bdf8', emissive: '#0ea5e9', glow: 0.8 });
          if (shown++ === 0) vectors.push({ id: 've', from: pos, vec: [0.5 * st.v, 0, 0], color: '#7dd3fc', label: 'v' });
        }
        if (p.V !== 0) vectors.push({ id: 'E', from: [p.V > 0 ? GAP - 0.4 : 0.4, Y0 + 0.95, 0], vec: [(p.V > 0 ? -1 : 1) * Math.min(1.8, 0.3 * Math.abs(p.V) + 0.4), 0, 0], color: '#f472b6', label: `force on e⁻ (${p.V > 0 ? 'retarding' : 'accelerating'})` });
        return { bodies, vectors };
      },
    };
    return model;
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'hydrogen') {
      const hy = hNumbers(p);
      if (!hy.ok) return ['En = −13.6 eV / n²', `nU = ${p.nU} is not above nL = ${p.nL}: a downward jump is impossible, so no photon is emitted.`, 'Emission needs nU > nL (absorption would need the opposite).'];
      return [
        'En = −13.6 eV / n²',
        `E${p.nU} = −13.6/${p.nU * p.nU} = ${hy.Eu.toFixed(3)} eV,  E${p.nL} = −13.6/${p.nL * p.nL} = ${hy.El.toFixed(3)} eV`,
        `ΔE = E${p.nU} − E${p.nL} = ${hy.dE.toFixed(3)} eV  (${seriesName(p.nL)})`,
        `λ = hc/ΔE = ${HC.toFixed(1)} eV·nm / ${hy.dE.toFixed(3)} eV = ${hy.lam.toFixed(1)} nm`,
      ];
    }
    const ph = photoNumbers(p);
    return [
      `hf = hc/λ = ${HC.toFixed(1)} eV·nm / ${p.lambda} nm = ${ph.E.toFixed(3)} eV`,
      ph.emits ? `Kmax = hf − φ = ${ph.E.toFixed(3)} − ${p.phi} = ${ph.Kmax.toFixed(3)} eV` : `hf = ${ph.E.toFixed(3)} eV ≤ φ = ${p.phi} eV → no emission at any intensity`,
      `eVstop = Kmax → Vstop = ${ph.Vstop.toFixed(3)} V;  λ0 = hc/φ = ${ph.lam0.toFixed(1)} nm`,
      `collected/emitted = ${m.Ne ? (m.Nc / m.Ne).toFixed(3) : '—'}  (expected ${collectFraction(p.V, ph.Kmax).toFixed(3)} for V = ${p.V} V)`,
    ];
  },
  challenges: [
    ({ runs }) => runs.some(a => runs.some(b => a !== b && a.params.mode === 'photo' && b.params.mode === 'photo' && a.params.phi === b.params.phi && a.params.I > 0 && b.params.I > 0
      && a.final.Ne > 0 && b.final.Ne === 0 && Math.abs(a.params.lambda - b.params.lambda) <= 10)),
    ({ runs }) => runs.some(r => r.params.mode === 'photo' && r.final.Ne >= 20 && r.final.Nc === 0 && r.params.V >= r.final.Vstop && r.params.V - r.final.Vstop <= 0.1),
    ({ runs }) => runs.some(a => runs.some(b => a !== b && a.params.mode === 'photo' && b.params.mode === 'photo' && a.params.lambda === b.params.lambda && a.params.phi === b.params.phi
      && a.params.V === 0 && b.params.V === 0 && a.final.Ne > 0 && b.params.I >= 2 * a.params.I
      && Math.abs(b.final.Ne / a.final.Ne - b.params.I / a.params.I) <= 0.1 * (b.params.I / a.params.I) && Math.abs(b.final.Kmax - a.final.Kmax) < 1e-9)),
    ({ runs }) => runs.some(r => r.params.mode === 'hydrogen' && r.final.lamH >= 640 && r.final.lamH <= 670),
  ],
  evaluate(p) {
    return { vars: { lambda: p.lambda, phi: p.phi }, answer: Math.max(0, photoelectricKmax(p.lambda * 1e-9, p.phi)), unit: 'V', tol: 0.02 };
  },
};
