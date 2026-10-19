// Electrostatics, circuits, magnetism, induction, atomic/nuclear/quantum, relativity, astrophysics.
import { C } from './constants.js';
import { deg } from './mechanics.js';

// ---------- Electrostatics ----------
export const coulomb = (q1, q2, r) => C.k * q1 * q2 / (r * r);           // signed: + repulsive
export const pointField = (q, r) => C.k * q / (r * r);
export const pointPotential = (q, r) => C.k * q / r;
export const pairPE = (q1, q2, r) => C.k * q1 * q2 / r;
// Field vector at point p from list of charges [{q, x, y}] in 2D.
export function fieldAt(charges, p) {
  let Ex = 0, Ey = 0;
  for (const ch of charges) {
    const dx = p[0] - ch.x, dy = p[1] - ch.y, r2 = dx * dx + dy * dy;
    if (r2 < 1e-18) continue;
    const r = Math.sqrt(r2), E = C.k * ch.q / r2;
    Ex += E * dx / r; Ey += E * dy / r;
  }
  return [Ex, Ey];
}
export const potentialAt = (charges, p) => charges.reduce((s, ch) => {
  const r = Math.hypot(p[0] - ch.x, p[1] - ch.y); return r < 1e-12 ? s : s + C.k * ch.q / r;
}, 0);
export const uniformFieldFromPlates = (V, d) => V / d;
export const capacitance = (Q, V) => Q / V;
export const parallelPlateC = (A, d, kappa = 1) => kappa * C.eps0 * A / d;
export const capEnergy = (Cap, V) => 0.5 * Cap * V * V;
export const chargesToElectrons = q => q / C.e;

// ---------- Circuits ----------
export const ohmV = (I, R) => I * R;
export const seriesR = (...R) => R.reduce((a, b) => a + b, 0);
export const parallelR = (...R) => 1 / R.reduce((a, b) => a + 1 / b, 0);
export const seriesC = (...Cs) => 1 / Cs.reduce((a, b) => a + 1 / b, 0);
export const parallelC = (...Cs) => Cs.reduce((a, b) => a + b, 0);
export const elecPower = (V, I) => V * I;
export const resistivityR = (rho, L, A) => rho * L / A;
export const energyCostKWh = (watts, hours, pricePerKWh) => watts * hours / 1000 * pricePerKWh;
export const rcCharge = (V0, R, Cap, t) => V0 * (1 - Math.exp(-t / (R * Cap)));
export const rcDischarge = (V0, R, Cap, t) => V0 * Math.exp(-t / (R * Cap));

/**
 * DC circuit solver by Modified Nodal Analysis.
 * nodes: number of nodes (node 0 = ground). elements: [{type:'R',a,b,value}|{type:'V',a,b,value}] where a V source
 * raises node a above node b by value volts. Returns node voltages and, per element, the current: a→b through a resistor, out of terminal a for a source.
 */
export function solveDC(nodes, elements) {
  const vs = elements.filter(e => e.type === 'V');
  const n = nodes - 1, size = n + vs.length;
  const A = Array.from({ length: size }, () => new Array(size).fill(0));
  const z = new Array(size).fill(0);
  const idx = node => node - 1;
  for (const e of elements) {
    if (e.type !== 'R') continue;
    if (!(e.value > 0)) throw new RangeError('resistance must be positive');
    const g = 1 / e.value, a = idx(e.a), b = idx(e.b);
    if (a >= 0) A[a][a] += g;
    if (b >= 0) A[b][b] += g;
    if (a >= 0 && b >= 0) { A[a][b] -= g; A[b][a] -= g; }
  }
  vs.forEach((e, k) => {
    const row = n + k, a = idx(e.a), b = idx(e.b);
    if (a >= 0) { A[a][row] += 1; A[row][a] += 1; }
    if (b >= 0) { A[b][row] -= 1; A[row][b] -= 1; }
    z[row] = e.value;
  });
  const x = gaussSolve(A, z);
  const V = [0, ...x.slice(0, n)];
  const currents = elements.map(e => {
    if (e.type === 'R') return (V[e.a] - V[e.b]) / e.value;
    // The MNA unknown is the current flowing from node a into the source; report the current the source delivers out of terminal a.
    return -x[n + vs.indexOf(e)];
  });
  return { V, currents };
}
function gaussSolve(A, b) {
  const n = b.length, M = A.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-14) throw new Error('circuit is singular (open loop, floating node, or shorted source)');
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c] / M[c][c];
      for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
    }
  }
  return M.map((r, i) => r[n] / r[i]);
}

// ---------- Magnetism and induction ----------
export const forceOnCharge = (q, v, B, angleDeg = 90) => Math.abs(q) * v * B * Math.sin(deg(angleDeg));
export const forceOnWire = (I, L, B, angleDeg = 90) => I * L * B * Math.sin(deg(angleDeg));
export const cyclotronRadius = (m, v, q, B) => m * v / (Math.abs(q) * B);
export const cyclotronPeriod = (m, q, B) => 2 * Math.PI * m / (Math.abs(q) * B);
export const wireField = (I, r) => C.mu0 * I / (2 * Math.PI * r);
export const loopCenterField = (I, R, N = 1) => N * C.mu0 * I / (2 * R);
export const solenoidField = (N, L, I) => C.mu0 * (N / L) * I;
export const flux = (B, A, angleDeg = 0) => B * A * Math.cos(deg(angleDeg)); // angle between B and area normal
export const faradayEMF = (N, dPhi, dt) => -N * dPhi / dt;
export const motionalEMF = (B, L, v) => B * L * v;
export const transformerVs = (Vp, Np, Ns) => Vp * Ns / Np;
export const generatorPeakEMF = (N, B, A, w) => N * B * A * w;

// ---------- Atomic, nuclear, quantum ----------
export const photonEnergy = lambda => C.h * C.c / lambda;
export const photonEnergyEV = lambda => photonEnergy(lambda) / C.eV;
export const wavelengthFromEV = E => C.h * C.c / (E * C.eV);
export const photoelectricKmax = (lambda, workFnEV) => photonEnergyEV(lambda) - workFnEV; // eV, negative = no emission
export const thresholdWavelength = workFnEV => C.h * C.c / (workFnEV * C.eV);
export const deBroglie = (m, v) => C.h / (m * v);
export const bohrEnergyEV = n => -13.6057 / (n * n);
export const hydrogenLineNm = (nUpper, nLower) => wavelengthFromEV(bohrEnergyEV(nUpper) - bohrEnergyEV(nLower)) * 1e9;
export const uncertaintyMinDp = dx => C.hbar / (2 * dx);
export const decayRemaining = (N0, halfLife, t) => N0 * 0.5 ** (t / halfLife);
export const decayConstant = halfLife => Math.LN2 / halfLife;
export const activity = (N, halfLife) => decayConstant(halfLife) * N;
export const ageFromFraction = (fraction, halfLife) => halfLife * Math.log(fraction) / Math.log(0.5);
export const restEnergy = m => m * C.c * C.c;
export const massDefectEnergyMeV = du => du * 931.494;   // atomic mass units → MeV
export const infiniteWellEnergy = (n, m, L) => n * n * C.h * C.h / (8 * m * L * L);

// ---------- Relativity ----------
export const gamma = v => { if (Math.abs(v) >= C.c) throw new RangeError('speed must be below c'); return 1 / Math.sqrt(1 - (v / C.c) ** 2); };
export const gammaBeta = beta => 1 / Math.sqrt(1 - beta * beta);
export const dilatedTime = (tProper, v) => gamma(v) * tProper;
export const contractedLength = (Lproper, v) => Lproper / gamma(v);
export const velocityAdd = (u, v) => (u + v) / (1 + u * v / (C.c * C.c));
export const relMomentum = (m, v) => gamma(v) * m * v;
export const relKE = (m, v) => (gamma(v) - 1) * m * C.c * C.c;
export const schwarzschildRadius = M => 2 * C.G * M / (C.c * C.c);
export const gravTimeDilationFactor = (M, r) => Math.sqrt(1 - schwarzschildRadius(M) / r);

// ---------- Astrophysics and cosmology ----------
export const wienPeakNm = T => 2.897771955e-3 / T * 1e9;
export const stefanLuminosity = (R, T) => 4 * Math.PI * R * R * C.sigma * T ** 4;
export const hubbleVelocity = (dMpc, H0 = C.H0) => H0 * dMpc;     // km/s
export const hubbleTimeGyr = (H0 = C.H0) => (3.0857e19 / H0) / 3.15576e16;
export const redshiftLowZ = (lambdaObs, lambdaEmit) => (lambdaObs - lambdaEmit) / lambdaEmit;
