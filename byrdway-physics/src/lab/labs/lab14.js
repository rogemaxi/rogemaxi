// Lab 14 — Wave Interference Lab. A 4 m rope (μ = 0.50 kg/m) is simulated with the finite-difference wave
// equation (201 points, leapfrog). Three experiments: two pulses that pass through each other (superposition),
// a fixed–fixed string vibrating in harmonic n (standing waves), and two sources of slightly different
// frequency driving one end (beats measured at a detector in the middle).
import { stringSpeed, harmonicsString, beatFreq } from '../../physics/index.js';

const LEN = 4, N = 200, DX = LEN / N, MU = 0.5;
const DT = 1 / 480;                    // lab time step; Courant number v·dt/dx ≤ 0.83 for v ≤ 8 m/s
const SIG = 0.15;                      // pulse width (Gaussian σ), m
const X1 = 0.8, X2 = 3.2, GATE = 1.4;  // pulse start positions and the speed gate, m
const PROBE = 2;                       // centre probe / detector position, m
const X0 = -LEN / 2, Y0 = 1.2;         // drawing offset: the rope runs from x = −2 to 2 at height 1.2 m
const gauss = x => Math.exp(-x * x / (2 * SIG * SIG));

const probeX = p => (p.mode === 'standing' ? LEN / (2 * p.n) : PROBE);
const tEnd = (p, v) => p.mode === 'pulses' ? (X2 - X1 + 0.6) / v + 0.2 : p.mode === 'standing' ? 8 : 16;

export default {
  num: 14, unit: 13, sections: ['13.1', '13.2', '13.3', '13.5', '13.7', '13.8'],
  dt: DT,
  text: {
    title: 'Wave Interference Lab',
    question: 'What happens when two waves occupy the same place on a string, which frequencies make a fixed string resonate, and why do two nearly equal frequencies produce beats?',
    params: { mode: 'Experiment', F: 'Rope tension F', A1: 'Amplitude A₁ (pulse 1 / harmonic / source 1)', A2: 'Amplitude A₂ (pulse 2 / source 2)', n: 'Harmonic number n', f1: 'Source 1 frequency f₁', f2: 'Source 2 frequency f₂' },
    options: { pulses: 'Two pulses (superposition)', standing: 'Standing wave on a fixed string', beats: 'Two sources: beats' },
    graph: ['probe displacement vs time', 'rope energy vs time', 'largest displacement on the rope vs time'],
    series: { yp: 'probe', KE: 'kinetic', PE: 'elastic', E: 'total', ymax: 'max |y|' },
    measures: { t: 'Time', v: 'Wave speed √(F/μ)', yp: 'Probe displacement', ymax: 'Largest |y| on the rope', ypk: 'Peak displacement at centre', vm: 'Measured pulse speed', fm: 'Measured frequency at antinode', lam: 'Wavelength 2L/n', nodes: 'Interior nodes', fb: 'Measured beat frequency', E: 'Rope energy' },
    predict: {
      prompt: 'An upright pulse (+0.25 m) and an inverted pulse (−0.25 m) of the same shape travel toward each other on the rope. At the instant they overlap exactly at the centre, what does the rope look like there, and what happens afterwards?',
      choices: ['Flat for an instant, then both pulses continue unchanged', 'A 0.50 m bump, then both continue', 'Flat, and both pulses are destroyed', 'The pulses bounce off each other and reverse'],
    },
    guided: [
      'Pulses mode, A₁ = +0.25 m and A₂ = +0.25 m. Use slow motion. What is the peak displacement at the centre when the pulses overlap? Compare with A₁ + A₂.',
      'Now set A₂ = −0.25 m. Describe the rope at the moment of overlap and explain where the energy is at that instant (use the energy bars).',
      'Measure the pulse speed for F = 2, 8 and 32 N. Show that v = √(F/μ) with μ = 0.50 kg/m.',
      'Standing-wave mode, F = 8 N. Run harmonics n = 1 to 4. Record the measured frequency and count the nodes. Show that fₙ = n·v/(2L).',
      'Beats mode, f₁ = 2.0 Hz. Measure the beat frequency for f₂ = 2.2, 2.5 and 3.0 Hz and compare with |f₁ − f₂|.',
      'Beats mode with A₁ ≠ A₂: why does the sound (displacement) never drop to zero at the quiet moments?',
    ],
    challenges: [
      'Excite the third harmonic and make its measured frequency 1.50 Hz (±0.02 Hz) by choosing the tension.',
      'Produce a beat frequency of 0.40 Hz (±0.02 Hz) at the detector using source frequencies of at least 1 Hz.',
      'Make two pulses, each at least 0.20 m tall, cancel so completely that the centre of the rope never moves more than 1 cm during the whole run.',
    ],
    evaluate: 'Before you run: the 4.0 m rope (μ = 0.50 kg/m) is fixed at both ends under a tension of {F} N. Calculate the frequency of harmonic n = {n}.',
    honors: {
      prompt: 'Two sources of equal amplitude A and frequencies f₁ and f₂ drive the same point. Use a trigonometric identity to show that the result is a carrier wave of frequency (f₁ + f₂)/2 whose amplitude envelope repeats at |f₁ − f₂|. Then explain why the envelope’s own frequency is |f₁ − f₂|/2 but the loudness beats at |f₁ − f₂|.',
      solution: 'A sin(2πf₁t) + A sin(2πf₂t) = 2A cos(π(f₁ − f₂)t)·sin(π(f₁ + f₂)t). The carrier has frequency (f₁ + f₂)/2. The envelope 2A·cos(π(f₁ − f₂)t) has frequency |f₁ − f₂|/2, but its magnitude |2A cos(…)| peaks twice per envelope cycle, so the loud moments repeat at f_beat = |f₁ − f₂|. Example: 2.0 Hz and 2.5 Hz → carrier 2.25 Hz, beats at 0.5 Hz (loud every 2.0 s).',
    },
    assumptions: [
      'The rope is ideal: uniform linear density μ = 0.50 kg/m, perfectly flexible, under constant tension, with small transverse displacements, so it obeys the linear wave equation with v = √(F/μ). There is no damping.',
      'The wave equation is solved with a finite-difference (leapfrog) scheme on 201 points (Δx = 2 cm) with Δt = 1/480 s; its numerical dispersion is below 0.1 % for the waves used here.',
      'Pulses and beats modes: the rope ends absorb outgoing waves (a first-order non-reflecting boundary), as if the rope continued forever. Standing-wave mode: both ends are fixed (nodes) and the rope starts at rest in the exact shape of harmonic n.',
      'Beats mode: the left end is moved as A₁ sin(2πf₁t) + A₂ sin(2πf₂t); the beat frequency is measured from the times of the loud moments (envelope maxima) at the detector 2 m from the source.',
      'Displacements are drawn at true scale; colours and glowing markers are visual aids only.',
    ],
  },
  params: [
    { id: 'mode', value: 'pulses', options: [{ value: 'pulses', label: 'Two pulses (superposition)' }, { value: 'standing', label: 'Standing wave on a fixed string' }, { value: 'beats', label: 'Two sources: beats' }] },
    { id: 'F', min: 2, max: 32, step: 0.5, value: 8, unit: 'N' },
    { id: 'A1', min: 0, max: 0.3, step: 0.01, value: 0.25, unit: 'm' },
    { id: 'A2', min: -0.3, max: 0.3, step: 0.01, value: -0.25, unit: 'm' },
    { id: 'n', min: 1, max: 6, step: 1, value: 2, unit: '' },
    { id: 'f1', min: 0.5, max: 3, step: 0.05, value: 2, unit: 'Hz' },
    { id: 'f2', min: 0.5, max: 3, step: 0.05, value: 2.5, unit: 'Hz' },
  ],
  sampleEvery: 1 / 60,
  camera: { target: [0, 1.2, 0], dist: 6, free: [0.15, 0.25, 1] },
  view2d: { span: 5, cx: 0, cy: 1.2 },
  graph: {
    choices: [
      { label: 'probe displacement vs time', y: ['yp'], labels: ['yp'], yLabel: 'y (m)' },
      { label: 'rope energy vs time', y: ['KE', 'PE', 'E'], labels: ['KE', 'PE', 'E'], yLabel: 'energy (J)' },
      { label: 'largest displacement on the rope vs time', y: ['ymax'], labels: ['ymax'], yLabel: '|y| max (m)' },
    ],
  },
  recordKeys: ['v', 'ypk', 'vm', 'fm', 'nodes', 'fb'],
  decor: p => {
    const out = [{ shape: 'ground', size: 30, divisions: 30 },
      { shape: 'line', pts: [[X0, Y0, 0], [X0 + LEN, Y0, 0]], color: '#334155' },
      ...[0, 1, 2, 3, 4].map(x => ({ shape: 'label', text: `${x} m`, pos: [X0 + x, Y0 - 0.45, 0], color: '#64748b' }))];
    const post = x => ({ shape: 'box', size: [0.08, Y0 + 0.1, 0.08], pos: [x, (Y0 + 0.1) / 2, 0], color: '#475569' });
    if (p.mode === 'standing') {
      out.push(post(X0 - 0.04), post(X0 + LEN + 0.04));
      for (let k = 1; k < p.n; k++) out.push({ shape: 'label', text: 'node', pos: [X0 + k * LEN / p.n, Y0 + 0.4, 0], color: '#a5b4fc' });
    } else {
      out.push({ shape: 'label', text: 'absorbing end', pos: [X0 + LEN, Y0 + 0.5, 0], color: '#64748b' });
      if (p.mode === 'pulses') out.push({ shape: 'label', text: 'absorbing end', pos: [X0, Y0 + 0.5, 0], color: '#64748b' }, { shape: 'line', pts: [[X0 + GATE, Y0 - 0.35, 0], [X0 + GATE, Y0 - 0.3, 0]], color: '#4ade80' }, { shape: 'label', text: 'speed gate', pos: [X0 + GATE, Y0 - 0.6, 0], color: '#4ade80' });
      else out.push({ shape: 'box', size: [0.25, 0.6, 0.3], pos: [X0 - 0.15, Y0 - 0.1, 0], color: '#475569' }, { shape: 'label', text: `sources ${p.f1} Hz + ${p.f2} Hz`, pos: [X0, Y0 + 0.6, 0], color: '#fbbf24' });
    }
    return out;
  },
  create(p) {
    const v = stringSpeed(p.F, MU), r = v * DT / DX, r2 = r * r, mur = (r - 1) / (r + 1);
    const mode = p.mode, xs = Array.from({ length: N + 1 }, (_, i) => i * DX);
    let y = new Float64Array(N + 1), yp = new Float64Array(N + 1), yn = new Float64Array(N + 1);
    const k = p.n * Math.PI / LEN, w = 2 * Math.PI * harmonicsString(p.n, LEN, v);
    xs.forEach((x, i) => {
      if (mode === 'pulses') { y[i] = p.A1 * gauss(x - X1) + p.A2 * gauss(x - X2); yp[i] = p.A1 * gauss(x - X1 + v * DT) + p.A2 * gauss(x - X2 - v * DT); }
      else if (mode === 'standing') { y[i] = p.A1 * Math.sin(k * x); yp[i] = p.A1 * Math.sin(k * x) * Math.cos(w * DT); }
    });
    if (mode === 'standing') { y[0] = y[N] = yp[0] = yp[N] = 0; }
    const iP = Math.round(probeX(p) / DX), iG = Math.round(GATE / DX), iC = Math.round(PROBE / DX);
    const drive = t => p.A1 * Math.sin(2 * Math.PI * p.f1 * t) + p.A2 * Math.sin(2 * Math.PI * p.f2 * t);
    const s = { t: 0, done: false, events: [], ypk: 0, gate: [], tGate: NaN, cross: [], peaks: [], maxima: [], minSince: Infinity, hist: [] };
    const end = tEnd(p, v);
    const energy = () => { // discrete energy conserved by the leapfrog scheme
      let KE = 0, PE = 0;
      for (let i = 0; i <= N; i++) KE += 0.5 * MU * DX * ((y[i] - yp[i]) / DT) ** 2;
      for (let i = 0; i < N; i++) PE += 0.5 * p.F * ((y[i + 1] - y[i]) * (yp[i + 1] - yp[i])) / DX;
      return { KE, PE };
    };
    const peakRefine = (a, b, c, t1, h) => { const den = a - 2 * b + c; return Math.abs(den) < 1e-15 ? t1 : t1 + h * 0.5 * (a - c) / den; };
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        const h = DT; // the scheme is built for the lab's fixed time step
        for (let i = 1; i < N; i++) yn[i] = 2 * y[i] - yp[i] + r2 * (y[i + 1] - 2 * y[i] + y[i - 1]);
        const tn = s.t + h;
        if (mode === 'standing') { yn[0] = 0; yn[N] = 0; }
        else {
          yn[N] = y[N - 1] + mur * (yn[N - 1] - y[N]);
          yn[0] = mode === 'beats' ? drive(tn) : y[1] + mur * (yn[1] - y[0]);
        }
        [yp, y, yn] = [y, yn, yp];
        s.t = tn;
        // ---- measurements taken from the simulated rope ----
        const P = y[iP], Pold = yp[iP];
        if (mode === 'pulses') {
          if (Math.abs(y[iC]) > Math.abs(s.ypk)) s.ypk = y[iC];
          s.gate.push(Math.abs(y[iG])); if (s.gate.length > 3) s.gate.shift();
          if (!Number.isFinite(s.tGate) && s.gate.length === 3 && s.gate[1] > s.gate[0] && s.gate[1] >= s.gate[2] && s.gate[1] > 0.5 * p.A1 && p.A1 > 0) s.tGate = peakRefine(s.gate[0], s.gate[1], s.gate[2], s.t - h, h);
        } else if (mode === 'standing') {
          if (Pold !== 0 && Math.sign(P) !== Math.sign(Pold)) s.cross.push(s.t - h + h * Pold / (Pold - P));
        } else {
          s.hist.push([s.t, Math.abs(P)]); if (s.hist.length > 3) s.hist.shift();
          if (s.hist.length === 3 && s.hist[1][1] > s.hist[0][1] && s.hist[1][1] >= s.hist[2][1]) {
            // a carrier half-cycle peak of |y|: these trace the beat envelope
            const tp = peakRefine(s.hist[0][1], s.hist[1][1], s.hist[2][1], s.hist[1][0], h);
            s.peaks.push([tp, s.hist[1][1]]); if (s.peaks.length > 3) s.peaks.shift();
            s.minSince = Math.min(s.minSince, s.hist[1][1]);
            const q = s.peaks;
            if (q.length === 3 && q[1][1] > q[0][1] && q[1][1] >= q[2][1] && q[1][1] - s.minSince > 0.05 * (Math.abs(p.A1) + Math.abs(p.A2))) {
              // envelope maximum: parabola through three successive peaks
              const [[ta, a], [tb, b], [tc, c]] = q, den = (ta - tb) * (ta - tc) * (tb - tc);
              const A = (tc * (b - a) + tb * (a - c) + ta * (c - b)) / den, B = (tc * tc * (a - b) + tb * tb * (c - a) + ta * ta * (b - c)) / den;
              s.maxima.push(Math.abs(A) > 1e-12 ? -B / (2 * A) : tb); s.minSince = Infinity;
            }
          }
        }
        if (s.t >= end - 1e-9) s.done = true;
      },
      measures() {
        let ymax = 0; for (let i = 0; i <= N; i++) ymax = Math.max(ymax, Math.abs(y[i]));
        const { KE, PE } = energy();
        const per = s.cross.length >= 2 ? 2 * (s.cross.at(-1) - s.cross[0]) / (s.cross.length - 1) : NaN;
        const fb = s.maxima.length >= 2 ? (s.maxima.length - 1) / (s.maxima.at(-1) - s.maxima[0]) : NaN;
        const st = mode === 'standing', pu = mode === 'pulses', be = mode === 'beats';
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'v', label: 'Wave speed √(F/μ)', value: v, unit: 'm/s', ref: 8 },
          { id: 'yp', label: 'Probe displacement', value: y[iP], unit: 'm', ref: 0.6 },
          { id: 'ymax', label: 'Largest |y| on the rope', value: ymax, unit: 'm', ref: 0.6 },
          { id: 'ypk', label: 'Peak displacement at centre', value: pu ? s.ypk : NaN, unit: 'm', ref: 0.6, hidden: !pu },
          { id: 'vm', label: 'Measured pulse speed', value: pu ? (GATE - X1) / s.tGate : NaN, unit: 'm/s', ref: 8, hidden: !pu },
          { id: 'fm', label: 'Measured frequency at antinode', value: st ? 1 / per : NaN, unit: 'Hz', ref: 6, hidden: !st },
          { id: 'lam', label: 'Wavelength 2L/n', value: st ? 2 * LEN / p.n : be ? v / p.f1 : NaN, unit: 'm', ref: 8, hidden: pu },
          { id: 'nodes', label: 'Interior nodes', value: st ? p.n - 1 : NaN, unit: '', hidden: !st },
          { id: 'fb', label: 'Measured beat frequency', value: be ? fb : NaN, unit: 'Hz', ref: 2.5, hidden: !be },
          { id: 'KE', label: 'Kinetic energy', value: KE, unit: 'J', hidden: true },
          { id: 'PE', label: 'Elastic energy', value: PE, unit: 'J', hidden: true },
          { id: 'E', label: 'Rope energy', value: KE + PE, unit: 'J', ref: 1 },
        ];
      },
      energy() { const { KE, PE } = energy(); return [{ label: 'Kinetic', value: KE, color: '#fbbf24' }, { label: 'Elastic (stretch)', value: PE, color: '#7dd3fc' }, { label: 'Total on rope', value: KE + PE, color: '#e2e8f0' }]; },
      scene() {
        const pts = Array.from({ length: N + 1 }, (_, i) => [X0 + i * DX, Y0 + y[i], 0]);
        const bodies = [];
        for (let i = 0; i <= N; i += 5) bodies.push({ id: 'p' + i, shape: 'sphere', r: 0.025, pos: pts[i], color: Math.abs(y[i]) > 0.01 ? (y[i] > 0 ? '#fbbf24' : '#f472b6') : '#94a3b8' });
        bodies.push({ id: 'probe', shape: 'sphere', r: 0.05, pos: pts[iP], color: '#4ade80', emissive: '#22c55e', glow: 0.5, label: `${mode === 'beats' ? 'detector' : 'probe'} ${y[iP].toFixed(3)} m` });
        if (mode === 'beats') bodies.push({ id: 'driver', shape: 'box', size: [0.12, 0.12, 0.2], pos: [X0, Y0 + y[0], 0], color: '#fbbf24' });
        const lines = [{ id: 'rope', pts, color: '#e2e8f0' }];
        const vectors = [];
        if (mode === 'pulses' && s.t < 0.3 / v) vectors.push({ id: 'd1', from: [X0 + X1, Y0 + p.A1 + 0.1, 0], vec: [0.5, 0, 0], color: '#fbbf24', label: 'v →' }, { id: 'd2', from: [X0 + X2, Y0 + p.A2 + (p.A2 < 0 ? -0.1 : 0.1), 0], vec: [-0.5, 0, 0], color: '#f472b6', label: '← v' });
        return { bodies, lines, vectors };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value])), v = stringSpeed(p.F, MU);
    const head = `v = √(F/μ) = √(${p.F}/0.50) = ${v.toFixed(3)} m/s`;
    if (p.mode === 'standing') return [head, `fₙ = n·v/(2L) = ${p.n} × ${v.toFixed(3)} / 8 = ${harmonicsString(p.n, LEN, v).toFixed(4)} Hz`, `λₙ = 2L/n = ${(2 * LEN / p.n).toFixed(3)} m, nodes inside: n − 1 = ${p.n - 1}`, `measured f = ${Number.isFinite(m.fm) ? m.fm.toFixed(4) : '—'} Hz`];
    if (p.mode === 'beats') return [head, `f_beat = |f₁ − f₂| = |${p.f1} − ${p.f2}| = ${beatFreq(p.f1, p.f2).toFixed(3)} Hz`, `carrier f = (f₁ + f₂)/2 = ${((p.f1 + p.f2) / 2).toFixed(3)} Hz`, `measured f_beat = ${Number.isFinite(m.fb) ? m.fb.toFixed(4) : '—'} Hz`];
    return [head, 'y(x, t) = y₁(x − vt) + y₂(x + vt)  (superposition)', `overlap at the centre: A₁ + A₂ = ${p.A1} + ${p.A2} = ${(p.A1 + p.A2).toFixed(2)} m`, `measured peak at centre = ${m.ypk.toFixed(3)} m, measured speed = ${Number.isFinite(m.vm) ? m.vm.toFixed(3) : '—'} m/s`];
  },
  challenges: [
    ({ runs }) => runs.some(r => r.params.mode === 'standing' && r.params.n === 3 && Math.abs(r.final.fm - 1.5) <= 0.02),
    ({ runs }) => runs.some(r => r.params.mode === 'beats' && Math.min(r.params.f1, r.params.f2) >= 1 && Math.abs(r.final.fb - 0.4) <= 0.02),
    ({ runs }) => runs.some(r => r.params.mode === 'pulses' && Math.abs(r.params.A1) >= 0.2 && Math.abs(r.params.A2) >= 0.2 && Math.abs(r.final.ypk) <= 0.01 && r.final.ymax < 0.05),
  ],
  evaluate(p) {
    return { vars: { F: p.F, n: p.n }, answer: harmonicsString(p.n, LEN, stringSpeed(p.F, MU)), unit: 'Hz', tol: 0.01 };
  },
};
