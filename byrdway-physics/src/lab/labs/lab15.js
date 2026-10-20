// Lab 15 — Optics Laboratory. Ray tracing in two experiments. (1) A laser ray crosses a flat boundary between
// two media: refraction from the vector form of Snell's law, Fresnel reflectance, and total internal
// reflection beyond the critical angle; the laser sweeps from 0° to the chosen angle. (2) A thin converging or
// diverging lens: principal rays from the tip of an object are traced through the lens (paraxial ray-transfer
// rule u' = u − h/f) and the image is located where the outgoing rays (or their extensions) cross.
import { deg, toDeg, criticalAngleTIR, thinLens } from '../../physics/index.js';

const SWEEP = 6, HOLD = 0.5;      // s: duration of the angle / object sweep and the hold at the end
const DO0 = 100;                  // cm: the object starts here and slides to the chosen distance
const Y0 = 1.5;                   // height of the boundary / optical axis in the scene, m (scene units)
const RAY = 9;                    // drawn ray length in refraction mode
const S = 0.1;                    // lens mode: scene units per cm
const XMAX = 25;                  // lens mode: rays are drawn to |x| ≤ 25 scene units (250 cm)
const nColor = n => `rgba(${Math.round(120 - 60 * (n - 1))},${Math.round(170 - 40 * (n - 1))},255,1)`;

// ---- refraction by the vector form of Snell's law (independent of the angle formula) ----
// incoming unit direction d, unit normal nrm pointing back into medium 1, index ratio η = n1/n2
function refractVec(d, nrm, eta) {
  const cosi = -(d[0] * nrm[0] + d[1] * nrm[1]), k = 1 - eta * eta * (1 - cosi * cosi);
  const refl = [d[0] + 2 * cosi * nrm[0], d[1] + 2 * cosi * nrm[1]];
  if (k < 0) return { refl, tir: true, cosi };
  const c = eta * cosi - Math.sqrt(k);
  return { refl, t: [eta * d[0] + c * nrm[0], eta * d[1] + c * nrm[1]], tir: false, cosi, cost: Math.sqrt(k) };
}
// unpolarised Fresnel reflectance
function fresnel(n1, n2, cosi, cost) {
  const rs = (n1 * cosi - n2 * cost) / (n1 * cosi + n2 * cost), rp = (n1 * cost - n2 * cosi) / (n1 * cost + n2 * cosi);
  return (rs * rs + rp * rp) / 2;
}
function boundary(n1, n2, th1) {
  const d = [Math.sin(deg(th1)), -Math.cos(deg(th1))];            // travelling down-right toward the boundary
  const r = refractVec(d, [0, 1], n1 / n2);
  if (r.tir) return { d, refl: r.refl, tir: true, th2: NaN, R: 1 };
  return { d, refl: r.refl, t: r.t, tir: false, th2: toDeg(Math.atan2(r.t[0], -r.t[1])), R: fresnel(n1, n2, r.cosi, r.cost) };
}

// ---- thin-lens ray trace (cm). A ray is [x, y, slope]; at the lens (x = 0) the slope changes by −h/f. ----
const fSigned = p => (p.lens === 'diverging' ? -p.f : p.f);
function traceLens(f, dObj, ho) {
  const tip = [-dObj, ho];
  const slopes = [0, -ho / dObj]; // parallel to the axis, through the centre
  if (Math.abs(dObj - f) > 1e-9) slopes.push((0 - ho) / (dObj - f)); // toward the near focal point (absent if the object sits on it)
  const rays = slopes.map(u => { const h = ho + u * dObj; return { u, h, out: u - h / f }; });
  // image: intersection of the two outgoing lines y = h + out·x (parallel ray and central ray)
  const [A, B] = rays, den = A.out - B.out;
  if (Math.abs(den) < 1e-12) return { tip, rays, di: Infinity, hi: Infinity, m: Infinity };
  const di = (B.h - A.h) / den, hi = A.h + A.out * di;
  return { tip, rays, di, hi, m: hi / ho };
}

export default {
  num: 15, unit: 14, sections: ['14.3', '14.4', '14.5', '14.6'],
  text: {
    title: 'Optics Laboratory',
    question: 'How does light bend when it crosses into a new medium, when is it trapped by total internal reflection, and where do lenses form images and how large are they?',
    params: { mode: 'Experiment', n1: 'Index of medium 1 (top) n₁', n2: 'Index of medium 2 (bottom) n₂', th1: 'Angle of incidence θ₁', lens: 'Lens type', f: 'Focal length |f|', do: 'Object distance d_o', ho: 'Object height h_o' },
    options: { refract: 'Refraction at a boundary', lens: 'Thin lens', converging: 'Converging (convex)', diverging: 'Diverging (concave)' },
    graph: ['refraction angle θ₂ vs incidence angle θ₁', 'reflected fraction vs incidence angle', '1/d_i vs 1/d_o (lens)', 'magnification vs object distance (lens)'],
    series: { th2: 'θ₂', R: 'reflected %', invDi: '1/d_i', mG: 'm' },
    measures: { t: 'Time', th1: 'Incidence angle θ₁', th2: 'Refraction angle θ₂', thc: 'Critical angle θc', R: 'Reflected fraction', T: 'Transmitted fraction', ratio: 'sin θ₁ / sin θ₂', tir: 'Total internal reflection', do: 'Object distance d_o', di: 'Image distance d_i', m: 'Magnification m', hi: 'Image height h_i', real: 'Image is real', invDo: '1/d_o', invDi: '1/d_i', mG: 'Magnification (graph, clipped at ±10)' },
    predict: {
      prompt: 'An object slides toward a converging lens (f = 10 cm), from 100 cm away to 15 cm away. What happens to its image?',
      choices: ['It moves farther from the lens and grows larger', 'It moves closer to the lens and shrinks', 'It stays in the same place but grows', 'It turns upright and virtual'],
    },
    guided: [
      'Refraction mode, n₁ = 1.00 (air), n₂ = 1.50 (glass), θ₁ = 60°. Run the sweep. Use the θ₂–θ₁ graph to show that sin θ₁ / sin θ₂ stays equal to n₂/n₁.',
      'Swap the media (n₁ = 1.50, n₂ = 1.00). Sweep to 60° and find the angle where the refracted ray disappears. Compare it with θc = sin⁻¹(n₂/n₁).',
      'Use the reflected-fraction graph: what happens to the reflected light as θ₁ approaches the critical angle? Why are optical fibres made of high-index glass?',
      'Lens mode, converging, f = 10 cm. Run with d_o = 30, 20, 15 and 8 cm. Record d_i and m. Which images are real and inverted, and which are virtual and upright?',
      'Use the 1/d_i vs 1/d_o graph from one run. Show that it is a straight line with slope −1 and read 1/f from its intercept.',
      'Switch to a diverging lens. Show that for every object distance the image is virtual, upright and smaller than the object.',
    ],
    challenges: [
      'Locate the critical angle for light leaving a denser medium: record a run with total internal reflection and a run without it, with the same media and incidence angles at most 1° apart.',
      'With a converging lens, form a real, inverted image exactly the same size as the object (m = −1.00 ± 0.02).',
      'With a diverging lens, form an upright image half as tall as the object (m = +0.50 ± 0.02).',
    ],
    evaluate: 'Before you run: an object stands {do} cm in front of a thin lens of focal length {fs} cm (negative means diverging). Calculate the image distance d_i (negative means a virtual image on the object’s side).',
    honors: {
      prompt: 'Using only the paraxial ray-transfer rule (a ray reaching the lens at height h leaves with its slope changed by −h/f), derive the thin-lens equation 1/f = 1/d_o + 1/d_i and the magnification m = −d_i/d_o by intersecting two rays from the top of the object. Check your result against a run.',
      solution: 'The ray parallel to the axis meets the lens at h = h_o and leaves with slope −h_o/f: y = h_o − h_o·x/f. The ray through the centre is undeviated: y = −h_o·x/d_o. They cross where h_o − h_o·x/f = −h_o·x/d_o, so x = d_i with 1/d_i = 1/f − 1/d_o, i.e. 1/f = 1/d_o + 1/d_i. There y = −h_o·d_i/d_o, so m = h_i/h_o = −d_i/d_o. Example: f = 10 cm, d_o = 15 cm → d_i = 30 cm, m = −2.',
    },
    assumptions: [
      'Geometric optics: light travels in straight rays within each uniform medium; wave effects (diffraction, interference) are ignored.',
      'Refraction mode: the boundary is flat and smooth, the media are non-absorbing and non-dispersive (one index for all colours). Refraction uses the vector form of Snell’s law; the reflected fraction is the Fresnel value for unpolarised light (the drawn ray brightness follows it).',
      'Lens mode: an ideal thin lens with paraxial rays (no spherical or chromatic aberration); every ray is bent at the lens plane by Δslope = −h/f. Distances are measured from the lens; d_i > 0 is a real image on the far side, d_i < 0 a virtual image on the object’s side.',
      'The run sweeps the incidence angle from 0° (or slides the object in from 100 cm) over 6 s so the graphs show the whole relationship; the final readings belong to the chosen setting.',
      'Lens-mode drawings use 1 scene unit = 10 cm; rays are drawn out to 250 cm. Ray glow and the laser are visual aids.',
    ],
  },
  params: [
    { id: 'mode', value: 'lens', options: [{ value: 'refract', label: 'Refraction at a boundary' }, { value: 'lens', label: 'Thin lens' }] },
    { id: 'n1', min: 1, max: 2.42, step: 0.01, value: 1, unit: '' },
    { id: 'n2', min: 1, max: 2.42, step: 0.01, value: 1.5, unit: '' },
    { id: 'th1', min: 0, max: 89, step: 0.5, value: 60, unit: '°' },
    { id: 'lens', value: 'converging', options: [{ value: 'converging', label: 'Converging (convex)' }, { value: 'diverging', label: 'Diverging (concave)' }] },
    { id: 'f', min: 5, max: 40, step: 1, value: 10, unit: 'cm' },
    { id: 'do', min: 5, max: 100, step: 1, value: 15, unit: 'cm' },
    { id: 'ho', min: 1, max: 10, step: 0.5, value: 4, unit: 'cm' },
  ],
  camera: { target: [0, 1.5, 0], dist: 24, free: [0.12, 0.2, 1] },
  view2d: { span: 26, cx: 0, cy: 1.5 },
  graph: {
    choices: [
      { label: 'refraction angle θ₂ vs incidence angle θ₁', x: 'th1', xLabel: 'θ₁ (°)', y: ['th2'], labels: ['th2'], yLabel: 'θ₂ (°)' },
      { label: 'reflected fraction vs incidence angle', x: 'th1', xLabel: 'θ₁ (°)', y: ['R'], labels: ['R'], yLabel: 'reflected (%)' },
      { label: '1/d_i vs 1/d_o (lens)', x: 'invDo', xLabel: '1/d_o (m⁻¹)', y: ['invDi'], labels: ['invDi'], yLabel: '1/d_i (m⁻¹)' },
      { label: 'magnification vs object distance (lens)', x: 'do', xLabel: 'd_o (cm)', y: ['mG'], labels: ['mG'], yLabel: 'm' },
    ],
  },
  recordKeys: ['th1', 'th2', 'R', 'tir', 'do', 'di', 'm', 'real'],
  decor: p => {
    const out = [{ shape: 'ground', size: 80, divisions: 40, y: -0.5 }];
    if (p.mode === 'refract') out.push(
      { shape: 'box', size: [22, 5, 3], pos: [0, Y0 + 2.5, 0], color: nColor(p.n1), opacity: 0.06 + 0.12 * (p.n1 - 1) },
      { shape: 'box', size: [22, 5, 3], pos: [0, Y0 - 2.5, 0], color: nColor(p.n2), opacity: 0.06 + 0.12 * (p.n2 - 1) },
      { shape: 'line', pts: [[-11, Y0, 1.5], [11, Y0, 1.5]], color: '#93c5fd' },
      { shape: 'line', pts: [[0, Y0 - 5, 0], [0, Y0 + 5, 0]], color: '#e2e8f0', opacity: 0.35 },
      { shape: 'label', text: `n₁ = ${p.n1.toFixed(2)}`, pos: [-8, Y0 + 4, 1.5], color: '#bfdbfe' },
      { shape: 'label', text: `n₂ = ${p.n2.toFixed(2)}`, pos: [-8, Y0 - 4, 1.5], color: '#bfdbfe' },
      { shape: 'label', text: 'normal', pos: [0, Y0 + 5.3, 0], color: '#94a3b8' },
    );
    else {
      const f = fSigned(p) * S;
      out.push(
        { shape: 'line', pts: [[-XMAX, Y0, 0], [XMAX, Y0, 0]], color: '#64748b' },
        { shape: 'cylinder', r: 1.6, h: 0.12, pos: [0, Y0, 0], rot: [0, 0, Math.PI / 2], color: p.lens === 'converging' ? '#7dd3fc' : '#c4b5fd', opacity: 0.45 },
        { shape: 'sphere', r: 0.12, pos: [-Math.abs(f), Y0, 0], color: '#fbbf24' }, { shape: 'sphere', r: 0.12, pos: [Math.abs(f), Y0, 0], color: '#fbbf24' },
        { shape: 'label', text: 'F', pos: [-Math.abs(f), Y0 - 0.6, 0], color: '#fbbf24' }, { shape: 'label', text: 'F', pos: [Math.abs(f), Y0 - 0.6, 0], color: '#fbbf24' },
        { shape: 'label', text: `${p.lens} lens, f = ${fSigned(p)} cm`, pos: [0, Y0 + 2.1, 0], color: '#e2e8f0' },
        ...[-100, -50, 50, 100, 200].map(c => ({ shape: 'label', text: `${c} cm`, pos: [c * S, Y0 - 1.1, 0], color: '#64748b' })),
      );
    }
    return out;
  },
  create(p) {
    const refr = p.mode === 'refract', f = fSigned(p);
    const s = { t: 0, done: false, events: [], u: 0 };
    const th1 = () => p.th1 * s.u;
    const dObj = () => DO0 + (p.do - DO0) * s.u;
    return {
      get t() { return s.t; }, get done() { return s.done; }, events: s.events,
      step(dt) {
        const wasTIR = refr && boundary(p.n1, p.n2, th1()).tir;
        s.t += dt; s.u = Math.min(1, s.t / SWEEP);
        if (refr && !wasTIR && boundary(p.n1, p.n2, th1()).tir) s.events.push({ type: 'spark', pos: [0, Y0, 0], strength: 0.5, speed: 0.8, color: '#f472b6', life: 0.7 });
        if (s.t >= SWEEP + HOLD - 1e-9) s.done = true;
      },
      measures() {
        const NaNs = ids => ids.map(id => ({ id, label: id, value: NaN, hidden: true }));
        if (refr) {
          const a = th1(), b = boundary(p.n1, p.n2, a), thc = criticalAngleTIR(p.n1, p.n2);
          return [
            { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
            { id: 'th1', label: 'Incidence angle θ₁', value: a, unit: '°', ref: 90 },
            { id: 'th2', label: 'Refraction angle θ₂', value: b.th2, unit: '°', ref: 90 },
            { id: 'thc', label: 'Critical angle θc', value: thc ?? NaN, unit: '°', ref: 90 },
            { id: 'R', label: 'Reflected fraction', value: 100 * b.R, unit: '%', ref: 100 },
            { id: 'T', label: 'Transmitted fraction', value: 100 * (1 - b.R), unit: '%', ref: 100 },
            { id: 'ratio', label: 'sin θ₁ / sin θ₂', value: b.tir || a === 0 ? NaN : Math.sin(deg(a)) / Math.sin(deg(b.th2)), unit: '', ref: 2.5 },
            { id: 'tir', label: 'Total internal reflection', value: b.tir ? 1 : 0, unit: '' },
            ...NaNs(['do', 'di', 'm', 'hi', 'real', 'invDo', 'invDi', 'mG']),
          ];
        }
        const d = dObj(), L = traceLens(f, d, p.ho);
        return [
          { id: 't', label: 'Time', value: s.t, unit: 's', hidden: true },
          { id: 'do', label: 'Object distance d_o', value: d, unit: 'cm', ref: 100 },
          { id: 'di', label: 'Image distance d_i', value: L.di, unit: 'cm', ref: 100 },
          { id: 'm', label: 'Magnification m', value: L.m, unit: '', ref: 5 },
          { id: 'hi', label: 'Image height h_i', value: L.hi, unit: 'cm', ref: 20 },
          { id: 'real', label: 'Image is real', value: L.di > 0 && Number.isFinite(L.di) ? 1 : 0, unit: '' },
          { id: 'invDo', label: '1/d_o', value: 100 / d, unit: 'm⁻¹', ref: 20, hidden: true },
          { id: 'invDi', label: '1/d_i', value: Number.isFinite(L.di) ? 100 / L.di : 0, unit: 'm⁻¹', ref: 20 },
          { id: 'mG', label: 'Magnification (graph)', value: Math.max(-10, Math.min(10, L.m)), unit: '', hidden: true },
          ...NaNs(['th1', 'th2', 'thc', 'R', 'T', 'ratio', 'tir']),
        ];
      },
      energy() {
        if (!refr) return [];
        const b = boundary(p.n1, p.n2, th1());
        return [{ label: 'Reflected light (per 1 J)', value: b.R, color: '#f472b6' }, { label: 'Transmitted light (per 1 J)', value: 1 - b.R, color: '#7dd3fc' }];
      },
      scene() {
        if (refr) {
          const a = th1(), b = boundary(p.n1, p.n2, a), O = [0, Y0, 0];
          const start = [-b.d[0] * RAY, Y0 - b.d[1] * RAY, 0];
          const lines = [
            { id: 'inc', pts: [start, O], color: '#f87171' },
            { id: 'refl', pts: [O, [b.refl[0] * RAY, Y0 + b.refl[1] * RAY, 0]], color: '#fb7185', opacity: Math.max(0.08, b.R) },
          ];
          if (!b.tir) lines.push({ id: 'refr', pts: [O, [b.t[0] * RAY, Y0 + b.t[1] * RAY, 0]], color: '#fca5a5', opacity: Math.max(0.15, 1 - b.R) });
          const al = Math.atan2(b.d[0], -b.d[1]); // laser body aligned with the incident ray
          const bodies = [
            { id: 'laser', shape: 'cylinder', r: 0.25, h: 1.6, pos: [start[0] - b.d[0] * 0.8, start[1] - b.d[1] * 0.8, 0], rot: [0, 0, al], color: '#334155', metal: 0.6, label: `θ₁ = ${a.toFixed(1)}°` },
            { id: 'spot', shape: 'sphere', r: 0.12, pos: O, color: '#fecaca', emissive: '#ef4444', glow: 0.8, label: b.tir ? 'total internal reflection' : `θ₂ = ${b.th2.toFixed(1)}°`, labelOffset: [1.6, -0.8, 0] },
          ];
          return { bodies, lines };
        }
        const d = dObj(), L = traceLens(f, d, p.ho), y = v => Y0 + v * S, X = v => v * S;
        const lines = [], cols = ['#fbbf24', '#4ade80', '#f472b6'];
        L.rays.forEach((r, i) => {
          const xEnd = XMAX / S;
          lines.push({ id: 'in' + i, pts: [[X(-d), y(p.ho), 0], [0, y(r.h), 0]], color: cols[i] });
          lines.push({ id: 'out' + i, pts: [[0, y(r.h), 0], [X(xEnd), y(Math.max(-300, Math.min(300, r.h + r.out * xEnd))), 0]], color: cols[i] });
          if (Number.isFinite(L.di) && L.di < 0) lines.push({ id: 'virt' + i, pts: [[0, y(r.h), 0], [X(L.di), y(L.hi), 0]], color: cols[i], opacity: 0.35 });
        });
        const vectors = [{ id: 'obj', from: [X(-d), Y0, 0], vec: [0, p.ho * S, 0], color: '#e2e8f0', label: `object ${p.ho} cm` }];
        if (Number.isFinite(L.di) && Math.abs(L.di) * S < XMAX && Math.abs(L.hi) * S < 6) vectors.push({ id: 'img', from: [X(L.di), Y0, 0], vec: [0, L.hi * S, 0], color: L.di > 0 ? '#fde047' : '#a5b4fc', label: `${L.di > 0 ? 'real' : 'virtual'} image, m = ${L.m.toFixed(2)}` });
        return { bodies: [{ id: 'objBase', shape: 'sphere', r: 0.08, pos: [X(-d), Y0, 0], color: '#e2e8f0' }], lines, vectors };
      },
    };
  },
  equations(p, model) {
    const m = Object.fromEntries(model.measures().map(x => [x.id, x.value]));
    if (p.mode === 'refract') {
      const thc = criticalAngleTIR(p.n1, p.n2);
      return [
        'n₁·sin θ₁ = n₂·sin θ₂',
        `${p.n1} × sin ${m.th1.toFixed(1)}° = ${(p.n1 * Math.sin(deg(m.th1))).toFixed(4)}${m.tir ? ' > n₂ → no refracted ray' : ` = ${p.n2} × sin ${m.th2.toFixed(2)}°`}`,
        thc == null ? 'n₁ ≤ n₂: no critical angle (total internal reflection impossible)' : `θc = sin⁻¹(n₂/n₁) = sin⁻¹(${p.n2}/${p.n1}) = ${thc.toFixed(2)}°`,
        `reflected ${m.R.toFixed(2)} %, transmitted ${m.T.toFixed(2)} % (Fresnel, unpolarised)`,
      ];
    }
    const f = fSigned(p);
    return [
      '1/f = 1/d_o + 1/d_i,   m = −d_i/d_o = h_i/h_o',
      `1/d_i = 1/${f} − 1/${m.do.toFixed(1)} = ${(1 / f - 1 / m.do).toFixed(5)} cm⁻¹ → d_i = ${Number.isFinite(m.di) ? m.di.toFixed(2) : '∞'} cm`,
      `m = −(${Number.isFinite(m.di) ? m.di.toFixed(2) : '∞'})/${m.do.toFixed(1)} = ${Number.isFinite(m.m) ? m.m.toFixed(3) : '∞'},  h_i = ${Number.isFinite(m.hi) ? m.hi.toFixed(2) : '∞'} cm`,
      m.real ? 'real, inverted image (on the far side of the lens)' : 'virtual, upright image (on the object’s side)',
    ];
  },
  challenges: [
    ({ runs }) => runs.some(a => a.params.mode === 'refract' && a.final.tir === 1 && runs.some(b => b !== a && b.params.mode === 'refract' && b.final.tir === 0 && b.params.n1 === a.params.n1 && b.params.n2 === a.params.n2 && a.final.th1 > b.final.th1 && a.final.th1 - b.final.th1 <= 1 + 1e-9)),
    ({ runs }) => runs.some(r => r.params.mode === 'lens' && r.params.lens === 'converging' && r.final.real === 1 && Math.abs(r.final.m + 1) <= 0.02 && Math.abs(r.final.do - r.params.do) < 1e-9),
    ({ runs }) => runs.some(r => r.params.mode === 'lens' && r.params.lens === 'diverging' && Math.abs(r.final.m - 0.5) <= 0.02 && Math.abs(r.final.do - r.params.do) < 1e-9),
  ],
  evaluate(p) {
    const fs = fSigned(p);
    return { vars: { do: p.do, fs }, answer: thinLens(fs, p.do).di, unit: 'cm', tol: 0.02 };
  },
};
