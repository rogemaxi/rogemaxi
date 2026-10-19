// Oscillations, fluids, thermal physics, waves, sound, optics. SI units throughout.
import { C } from './constants.js';
import { deg, toDeg } from './mechanics.js';

// ---------- Oscillations ----------
export const springPeriod = (m, k) => 2 * Math.PI * Math.sqrt(m / k);
export const pendulumPeriodSmall = (L, g = C.g) => 2 * Math.PI * Math.sqrt(L / g);
// Exact pendulum period for amplitude θ0 using the arithmetic-geometric mean: T = T0 / AGM(1, cos(θ0/2)).
export function pendulumPeriodExact(L, theta0Deg, g = C.g) {
  let a = 1, b = Math.cos(deg(theta0Deg) / 2);
  for (let i = 0; i < 30 && Math.abs(a - b) > 1e-15; i++) [a, b] = [(a + b) / 2, Math.sqrt(a * b)];
  return pendulumPeriodSmall(L, g) / a;
}
export const shm = {
  x: (A, w, t, phi = 0) => A * Math.cos(w * t + phi),
  v: (A, w, t, phi = 0) => -A * w * Math.sin(w * t + phi),
  a: (A, w, t, phi = 0) => -A * w * w * Math.cos(w * t + phi),
  vMax: (A, w) => A * w,
  aMax: (A, w) => A * w * w,
};
export const omegaFromPeriod = T => 2 * Math.PI / T;
export const hookeForce = (k, x) => -k * x;
// Damped oscillator x(t) for underdamped b < 2√(mk), released from rest at x0.
export function dampedOscillator(m, k, b) {
  const w0 = Math.sqrt(k / m), gamma = b / (2 * m);
  const wd = Math.sqrt(Math.max(0, w0 * w0 - gamma * gamma));
  return { w0, gamma, wd, underdamped: gamma < w0, x: (x0, t) => x0 * Math.exp(-gamma * t) * (Math.cos(wd * t) + (gamma / wd) * Math.sin(wd * t)) };
}
// Steady-state amplitude of driven damped oscillator (force amplitude F0, drive ω).
export const drivenAmplitude = (F0, m, k, b, w) => F0 / Math.sqrt((k - m * w * w) ** 2 + (b * w) ** 2);

// ---------- Fluids ----------
export const density = (m, V) => m / V;
export const pressure = (F, A) => F / A;
export const hydrostatic = (rho, h, P0 = 0, g = C.g) => P0 + rho * g * h;
export const buoyantForce = (rhoFluid, Vdisp, g = C.g) => rhoFluid * Vdisp * g;
export const fractionSubmerged = (rhoObj, rhoFluid) => Math.min(1, rhoObj / rhoFluid);
export const pascalOutput = (F1, A1, A2) => F1 * A2 / A1;
export const continuityV2 = (A1, v1, A2) => A1 * v1 / A2;
// Bernoulli: solve for P2 given everything else.
export const bernoulliP2 = (P1, rho, v1, h1, v2, h2, g = C.g) => P1 + 0.5 * rho * (v1 * v1 - v2 * v2) + rho * g * (h1 - h2);
export const torricelli = (h, g = C.g) => Math.sqrt(2 * g * h);
export const poiseuilleFlow = (r, dP, eta, L) => Math.PI * r ** 4 * dP / (8 * eta * L);
export const stokesTerminal = (r, rhoS, rhoF, eta, g = C.g) => 2 * r * r * (rhoS - rhoF) * g / (9 * eta);
export const reynolds = (rho, v, L, eta) => rho * v * L / eta;

// ---------- Thermal physics ----------
export const cToK = c => c + 273.15;
export const kToC = k => k - 273.15;
export const cToF = c => c * 9 / 5 + 32;
export const fToC = f => (f - 32) * 5 / 9;
export const heat = (m, c, dT) => m * c * dT;
export const latent = (m, L) => m * L;
// Two-body calorimetry, no phase change, no losses.
export const mixTemp = (m1, c1, T1, m2, c2, T2) => (m1 * c1 * T1 + m2 * c2 * T2) / (m1 * c1 + m2 * c2);
export const conduction = (kTh, A, dT, L) => kTh * A * dT / L;
export const radiation = (emis, A, T) => emis * C.sigma * A * T ** 4;
export const idealGasP = (n, T, V) => n * C.R * T / V;
export const avgKE = T => 1.5 * C.kB * T;
export const vrms = (T, molarMassKg) => Math.sqrt(3 * C.R * T / molarMassKg);
export const firstLawDU = (Q, Wby) => Q - Wby; // ΔU = Q − W (W done BY the gas)
export const isothermalWork = (n, T, V1, V2) => n * C.R * T * Math.log(V2 / V1);
export const isobaricWork = (P, V1, V2) => P * (V2 - V1);
export const carnotEfficiency = (Th, Tc) => 1 - Tc / Th;
export const entropyChangeReversibleIsothermal = (Q, T) => Q / T;
export const linearExpansion = (alpha, L0, dT) => alpha * L0 * dT;

// ---------- Waves and sound ----------
export const waveSpeed = (f, lambda) => f * lambda;
export const stringSpeed = (T, mu) => Math.sqrt(T / mu);
export const harmonicsString = (n, L, v) => n * v / (2 * L);          // fixed-fixed, n = 1,2,3...
export const harmonicsOpenPipe = (n, L, v) => n * v / (2 * L);         // open-open
export const harmonicsClosedPipe = (n, L, v) => n * v / (4 * L);       // closed-open, n odd
export const beatFreq = (f1, f2) => Math.abs(f1 - f2);
export const intensity = (P, r) => P / (4 * Math.PI * r * r);
export const decibels = I => 10 * Math.log10(I / 1e-12);
export const intensityFromDb = dB => 1e-12 * 10 ** (dB / 10);
export const soundSpeedAir = Tc => 331.3 * Math.sqrt(1 + Tc / 273.15);
// Doppler for sound: vs > 0 = source moving toward observer, vo > 0 = observer moving toward source.
export const doppler = (f, v, vo, vs) => f * (v + vo) / (v - vs);
export const superpose = (A1, A2, phaseDiffRad) => Math.sqrt(A1 * A1 + A2 * A2 + 2 * A1 * A2 * Math.cos(phaseDiffRad));

// ---------- Optics ----------
export const photonFreq = lambda => C.c / lambda;
// Snell's law: returns refraction angle in degrees, or null for total internal reflection.
export function snell(n1, theta1Deg, n2) {
  const s = n1 * Math.sin(deg(theta1Deg)) / n2;
  return Math.abs(s) > 1 ? null : toDeg(Math.asin(s));
}
export const criticalAngleTIR = (n1, n2) => (n1 <= n2 ? null : toDeg(Math.asin(n2 / n1)));
export const indexFromSpeed = v => C.c / v;
// Thin lens / spherical mirror: 1/f = 1/do + 1/di. Real image di > 0. Returns di and magnification.
export function thinLens(f, dObj) {
  if (Math.abs(dObj - f) < 1e-12) return { di: Infinity, m: Infinity, real: false };
  const di = 1 / (1 / f - 1 / dObj);
  return { di, m: -di / dObj, real: di > 0, upright: -di / dObj > 0 };
}
export const mirrorFocal = R => R / 2;
export const lensPower = f => 1 / f;
export const doubleSlitY = (m, lambda, L, d) => m * lambda * L / d;   // small-angle bright fringe position
export const gratingAngle = (m, lambda, d) => { const s = m * lambda / d; return Math.abs(s) > 1 ? null : toDeg(Math.asin(s)); };
export const singleSlitMinAngle = (m, lambda, a) => { const s = m * lambda / a; return Math.abs(s) > 1 ? null : toDeg(Math.asin(s)); };
export const malus = (I0, thetaDeg) => I0 * Math.cos(deg(thetaDeg)) ** 2;
export const brewster = (n1, n2) => toDeg(Math.atan(n2 / n1));
export const magnifierAngular = f => 0.25 / f; // near point 25 cm, image at near point variant uses 1 + 0.25/f
export const twoLensSystem = (f1, f2, sep, dObj) => {
  const a = thinLens(f1, dObj); const d2 = sep - a.di; const b = thinLens(f2, d2);
  return { di: b.di, m: a.m * b.m };
};
