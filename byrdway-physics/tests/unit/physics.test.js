// Scientific-accuracy tests. Expected values are computed by hand or taken from standard references,
// never from the function under test. Each block notes what is being checked: equation, units, sign,
// boundary/limit behavior, or a conservation law.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as P from '../../src/physics/index.js';

const near = (a, b, rel = 1e-6, abs = 1e-12) =>
  assert.ok(Math.abs(a - b) <= Math.max(abs, rel * Math.abs(b)), `expected ${b}, got ${a}`);

test('kinematics: constant-acceleration equations agree with each other', () => {
  // car 0→ 20 m/s at 4 m/s²: t = 5 s, Δx = 50 m (hand: v²/2a = 400/8)
  near(P.kin.v(0, 4, 5), 20);
  near(P.kin.x(0, 0, 4, 5), 50);
  near(P.kin.vFromX(0, 4, 50), 20);
  near(P.kin.dxAvg(0, 20, 5), 50);
  near(P.kin.stoppingDistance(30, 6), 75);
  near(P.kin.timeToDx(0, 4, 50), 5);
  // ball thrown up at 15 m/s returns to launch height after 2v/g
  near(P.kin.timeToDx(15, -9.8, 0) ?? 0, 0); // t = 0 is a root; first non-negative root is 0
  assert.equal(P.kin.timeToDx(5, -9.8, 10), null); // can never reach 10 m (max height 1.28 m)
  assert.throws(() => P.kin.vFromX(1, -10, 5));
});

test('free fall: drop from 20 m takes √(2h/g)', () => {
  near(P.kin.timeToDx(0, -9.8, -20), Math.sqrt(40 / 9.8));
  near(P.speedFromDrop(20), Math.sqrt(2 * 9.8 * 20));
});

test('projectiles: level-ground range, symmetry, and 45° optimum', () => {
  const p = P.projectile(20, 30);
  near(p.range, 400 * Math.sin(Math.PI / 3) / 9.8, 1e-9);      // R = v² sin2θ / g = 35.35 m
  near(p.range, P.levelRange(20, 30), 1e-9);
  near(p.tFlight, 2 * 10 / 9.8, 1e-9);                          // 2 v sinθ / g
  near(p.hMax, 100 / (2 * 9.8), 1e-9);                          // (v sinθ)² / 2g
  near(P.levelRange(20, 30), P.levelRange(20, 60), 1e-9);       // complementary angles
  assert.ok(P.levelRange(20, 45) > P.levelRange(20, 44.9));
  assert.ok(P.levelRange(20, 45) > P.levelRange(20, 45.1));
  near(p.impactSpeed, 20, 1e-9);                                // energy: lands at launch speed
  // horizontal launch from 1.25 m at 3 m/s: t = 0.505 s, x = 1.515 m
  const h = P.projectile(3, 0, 1.25);
  near(h.tFlight, Math.sqrt(2 * 1.25 / 9.8), 1e-9);
  near(h.range, 3 * Math.sqrt(2 * 1.25 / 9.8), 1e-9);
});

test('projectile with drag: k→0 recovers vacuum result; drag shortens range', () => {
  const vac = P.levelRange(30, 40);
  const r0 = P.projectileDrag(30, 40, 0, { dt: 1e-3 });
  near(r0.range, vac, 1e-4);
  const rd = P.projectileDrag(30, 40, 0.01, { dt: 1e-3 });
  assert.ok(rd.range < vac * 0.9);
});

test("Newton's second law and friction", () => {
  near(P.accel(12, 3), 4);
  assert.throws(() => P.accel(5, 0));
  // 10 kg block, F = 30 N, μs = 0.4 (fsmax = 39.2 N): stays put; friction balances exactly
  const s = P.pushedBlock(10, 30, 0.4, 0.3);
  assert.equal(s.moving, false); near(s.friction, -30);
  // F = 50 N > 39.2 N: a = (50 − 0.3·98)/10 = 2.06 m/s²
  near(P.pushedBlock(10, 50, 0.4, 0.3).a, 2.06, 1e-9);
  // sign: pushing left mirrors the result
  near(P.pushedBlock(10, -50, 0.4, 0.3).a, -2.06, 1e-9);
});

test('incline: frictionless a = g sinθ; critical angle tanθ = μs', () => {
  near(P.incline(5, 30).a, 4.9, 1e-9);
  near(P.incline(5, 30, 0, 0).N, 5 * 9.8 * Math.cos(Math.PI / 6), 1e-9);
  near(P.criticalAngle(1), 45, 1e-12);
  assert.equal(P.incline(2, 20, 0.5, 0.4).slides, false); // tan20° = 0.364 < 0.5
  const sl = P.incline(2, 40, 0.5, 0.4);                   // tan40° = 0.839 > 0.5
  near(sl.a, 9.8 * (Math.sin(P.deg(40)) - 0.4 * Math.cos(P.deg(40))), 1e-9);
  // mass independence
  near(P.incline(1, 40, 0.5, 0.4).a, P.incline(50, 40, 0.5, 0.4).a, 1e-12);
});

test('Atwood and table-hanging systems; elevator', () => {
  // 2 kg and 3 kg: a = g/5 = 1.96, T = 2·2·3·g/5 = 23.52 N
  const a = P.atwood(2, 3); near(a.a, 1.96, 1e-9); near(a.T, 23.52, 1e-9);
  near(P.atwood(4, 4).a, 0);                               // equal masses: equilibrium
  const t = P.tableHanging(3, 1, 0); near(t.a, 2.45, 1e-9); near(t.T, 1 * (9.8 - 2.45), 1e-9);
  near(P.tableHanging(3, 1, 0.5).a, 0);                    // friction 14.7 N > weight 9.8 N
  near(P.apparentWeight(60, 2), 60 * 11.8, 1e-9);
  near(P.apparentWeight(60, -9.8), 0, 1e-9, 1e-9);        // free fall: weightless
});

test('energy: work, KE, PE, conservation on a drop', () => {
  near(P.work(10, 5, 60), 25, 1e-9);
  near(P.work(10, 5, 90), 0, 1e-9, 1e-9);
  near(P.work(10, 5, 180), -50, 1e-9);
  const m = 2, h = 5, v = P.speedFromDrop(h);
  near(P.KE(m, v), P.PEg(m, h), 1e-12);
  near(P.PEs(200, 0.1), 1);
  near(P.power(600, 2), 300);
  near(P.efficiency(30, 120), 0.25);
});

test('momentum: elastic collisions conserve p and KE; inelastic conserves only p', () => {
  const [m1, v1, m2, v2] = [2, 3, 1, -1];
  const [a, b] = P.elastic1D(m1, v1, m2, v2);
  near(m1 * a + m2 * b, m1 * v1 + m2 * v2, 1e-12);
  near(P.KE(m1, a) + P.KE(m2, b), P.KE(m1, v1) + P.KE(m2, v2), 1e-12);
  // equal masses exchange velocities
  const [c, d] = P.elastic1D(1, 5, 1, 0); near(c, 0, 0, 1e-12); near(d, 5);
  const vf = P.perfectlyInelastic1D(1000, 20, 1500, 0); near(vf, 8);
  assert.ok(P.KE(2500, vf) < P.KE(1000, 20));
  // restitution limits
  const [e0a, e0b] = P.collide1D(2, 3, 1, -1, 0); near(e0a, e0b, 1e-12);
  const [e1a, e1b] = P.collide1D(2, 3, 1, -1, 1); near(e1a, a, 1e-12); near(e1b, b, 1e-12);
  near(P.recoil(0.01, 400, 4), -1);
  near(P.centerOfMass([1, 3], [0, 4]), 3);
  near(P.impulse(500, 0.02), 10);
});

test('circular motion and gravitation', () => {
  near(P.centripetalAccel(10, 5), 20);
  near(P.centripetalForce(1000, 20, 50), 8000);
  near(P.minTopSpeed(2.5), Math.sqrt(24.5));
  near(P.flatCurveMaxSpeed(0.8, 50), Math.sqrt(0.8 * 9.8 * 50));
  // g at Earth's surface ≈ 9.82 m/s² from G, Me, Re
  near(P.gField(P.C.Me, P.C.Re), 9.82, 2e-3);
  // ISS-like orbit at 400 km: v ≈ 7.67 km/s, T ≈ 92.4 min
  const r = P.C.Re + 4e5;
  near(P.orbitalSpeed(P.C.Me, r), 7670, 3e-3);
  near(P.orbitalPeriod(P.C.Me, r) / 60, 92.4, 5e-3);
  // Earth escape speed ≈ 11.2 km/s
  near(P.escapeSpeed(P.C.Me, P.C.Re), 11186, 2e-3);
  // Earth's orbital period ≈ 1 year (365.25 d) from Kepler III
  near(P.orbitalPeriod(P.C.Ms, P.C.AU) / 86400, 365.25, 2e-3);
  // escape speed is √2 × circular speed
  near(P.escapeSpeed(P.C.Me, r) / P.orbitalSpeed(P.C.Me, r), Math.SQRT2, 1e-12);
  // inverse-square: doubling r quarters force
  near(P.gravForce(1, 1, 2) / P.gravForce(1, 1, 1), 0.25, 1e-12);
});

test('rotation: inertia table, rolling race order, torque', () => {
  near(P.inertia.disk(2, 0.5), 0.25);
  near(P.inertia.rodEnd(3, 2), 4);
  near(P.inertia.rodCenter(3, 2), 1);
  // parallel axis: I_end = I_cm + m(L/2)²
  near(P.inertia.rodEnd(3, 2), P.inertia.rodCenter(3, 2) + 3 * 1, 1e-12);
  const acc = s => P.rollingAccel(30, P.shapeFactor[s]);
  assert.ok(acc('solidSphere') > acc('disk') && acc('disk') > acc('hollowSphere') && acc('hollowSphere') > acc('hoop'));
  near(acc('hoop'), 4.9 / 2, 1e-9);
  near(P.rollingSpeedFromHeight(1, 0.4), Math.sqrt(2 * 9.8 / 1.4), 1e-12);
  near(P.torque(0.3, 50), 15);
  near(P.torque(0.3, 50, 30), 7.5, 1e-9);
  near(P.rpmToRad(60), 2 * Math.PI);
});

test('oscillations: periods, exact pendulum limit, energy, damping', () => {
  near(P.springPeriod(0.5, 50), 2 * Math.PI * 0.1, 1e-12);
  near(P.pendulumPeriodSmall(1), 2.00709, 1e-5);
  // exact period → small-angle result as θ0 → 0; at 90° the ratio is 1.18034 (tabulated)
  near(P.pendulumPeriodExact(1, 0.01) / P.pendulumPeriodSmall(1), 1, 1e-8);
  near(P.pendulumPeriodExact(1, 90) / P.pendulumPeriodSmall(1), 1.180341, 1e-6);
  // SHM: ½kA² = ½m vmax²
  const m = 2, k = 8, A = 0.3, w = Math.sqrt(k / m);
  near(0.5 * k * A * A, 0.5 * m * P.shm.vMax(A, w) ** 2, 1e-12);
  // damped: b = 0 is undamped cosine
  const d0 = P.dampedOscillator(1, 4, 0); near(d0.x(1, 1.3), Math.cos(2 * 1.3), 1e-12);
  const d = P.dampedOscillator(1, 4, 0.4); assert.ok(Math.abs(d.x(1, 20)) < 0.02);
  // driven amplitude peaks near resonance
  const amp = w => P.drivenAmplitude(1, 1, 4, 0.1, w);
  assert.ok(amp(2) > amp(1.5) && amp(2) > amp(2.5));
});

test('fluids', () => {
  near(P.hydrostatic(1000, 10, P.C.atm), 101325 + 98000);
  near(P.buoyantForce(1000, 0.002), 19.6, 1e-9);
  near(P.fractionSubmerged(917, 1025), 0.8946, 1e-4);   // iceberg ≈ 89% submerged in seawater
  near(P.pascalOutput(100, 0.01, 0.5), 5000);
  near(P.continuityV2(0.02, 1.5, 0.005), 6);
  near(P.torricelli(5), Math.sqrt(98));
  // Bernoulli: same height, faster flow → lower pressure
  assert.ok(P.bernoulliP2(2e5, 1000, 2, 0, 8, 0) < 2e5);
  near(P.bernoulliP2(2e5, 1000, 2, 0, 8, 0), 2e5 - 0.5 * 1000 * 60);
});

test('thermal physics', () => {
  near(P.cToK(25), 298.15); near(P.cToF(100), 212); near(P.fToC(-40), -40);
  near(P.heat(2, 4186, 10), 83720);
  near(P.mixTemp(1, 4186, 80, 1, 4186, 20), 50);
  // ideal gas: 1 mol at 273.15 K in 22.414 L ≈ 1 atm
  near(P.idealGasP(1, 273.15, 0.022414), P.C.atm, 1e-4);
  near(P.carnotEfficiency(500, 300), 0.4);
  near(P.firstLawDU(500, 200), 300);
  // vrms of N2 at 300 K ≈ 517 m/s
  near(P.vrms(300, 0.028), 517, 2e-3);
  near(P.isothermalWork(1, 300, 1, Math.E), P.C.R * 300, 1e-12);
});

test('waves and sound', () => {
  near(P.waveSpeed(440, 0.78), 343.2, 1e-9);
  near(P.harmonicsString(1, 0.65, 286), 220, 1e-9);
  near(P.harmonicsClosedPipe(1, 0.25, 343), 343, 1e-9);
  near(P.decibels(1e-12), 0, 0, 1e-12); near(P.decibels(1), 120, 1e-12);
  near(P.intensityFromDb(60), 1e-6, 1e-9);
  near(P.beatFreq(440, 444), 4);
  // Doppler: approaching source raises pitch; f' = 400·343/(343−20)
  near(P.doppler(400, 343, 0, 20), 400 * 343 / 323, 1e-12);
  assert.ok(P.doppler(400, 343, 0, -20) < 400);
  near(P.superpose(1, 1, 0), 2); near(P.superpose(1, 1, Math.PI), 0, 0, 1e-12);
  near(P.soundSpeedAir(0), 331.3);
});

test('optics', () => {
  near(P.snell(1, 30, 1.5), P.toDeg(Math.asin(0.5 / 1.5)), 1e-12);
  assert.equal(P.snell(1.5, 60, 1), null);                     // beyond critical angle
  near(P.criticalAngleTIR(1.5, 1), 41.8103, 1e-5);
  assert.equal(P.criticalAngleTIR(1, 1.5), null);
  // converging lens f = 10 cm, object at 30 cm → image 15 cm, m = −0.5, real, inverted
  const L = P.thinLens(0.10, 0.30); near(L.di, 0.15, 1e-12); near(L.m, -0.5, 1e-12); assert.ok(L.real && !L.upright);
  // object inside f → virtual, upright, magnified
  const V = P.thinLens(0.10, 0.05); assert.ok(!V.real && V.upright); near(V.m, 2, 1e-12);
  near(P.doubleSlitY(1, 600e-9, 2, 0.2e-3), 0.006, 1e-12);
  near(P.malus(100, 60), 25, 1e-12);
  near(P.brewster(1, 1.5), 56.3099, 1e-5);
});

test('electrostatics', () => {
  // two 1 µC charges 1 m apart: 8.99e-3 N, repulsive (+)
  near(P.coulomb(1e-6, 1e-6, 1), 8.98755e-3, 1e-5);
  assert.ok(P.coulomb(1e-6, -1e-6, 1) < 0);
  // superposition: midpoint of equal charges has zero field; dipole midpoint field points + → −
  const [ex, ey] = P.fieldAt([{ q: 1e-9, x: -1, y: 0 }, { q: 1e-9, x: 1, y: 0 }], [0, 0]);
  near(ex, 0, 0, 1e-12); near(ey, 0, 0, 1e-12);
  const [dx] = P.fieldAt([{ q: 1e-9, x: -1, y: 0 }, { q: -1e-9, x: 1, y: 0 }], [0, 0]);
  near(dx, 2 * P.C.k * 1e-9, 1e-9);
  near(P.potentialAt([{ q: 1e-9, x: -1, y: 0 }, { q: -1e-9, x: 1, y: 0 }], [0, 0]), 0, 0, 1e-9);
  near(P.parallelPlateC(1, 1e-3), 8.854e-9, 1e-3);
  near(P.capEnergy(2e-6, 100), 0.01);
  near(P.chargesToElectrons(1), 6.2415e18, 1e-4);
});

test('circuits: series/parallel formulas and MNA solver agree', () => {
  near(P.seriesR(2, 3, 5), 10);
  near(P.parallelR(6, 3), 2);
  near(P.parallelR(10, 10, 10, 10), 2.5);
  // 12 V across 2 Ω + (6 Ω ∥ 3 Ω) → Req = 4 Ω, I = 3 A
  const sol = P.solveDC(3, [
    { type: 'V', a: 1, b: 0, value: 12 },
    { type: 'R', a: 1, b: 2, value: 2 },
    { type: 'R', a: 2, b: 0, value: 6 },
    { type: 'R', a: 2, b: 0, value: 3 },
  ]);
  near(sol.currents[0], 3, 1e-12);          // source delivers 3 A
  near(sol.currents[1], 3, 1e-12);
  near(sol.V[2], 6, 1e-12);
  near(sol.currents[2] + sol.currents[3], 3, 1e-12);  // Kirchhoff junction rule
  near(sol.currents[3], 2, 1e-12);
  // Kirchhoff loop rule with two sources: 10 V and 4 V opposing through 3 Ω → 2 A
  const two = P.solveDC(3, [
    { type: 'V', a: 1, b: 0, value: 10 }, { type: 'V', a: 2, b: 0, value: 4 }, { type: 'R', a: 1, b: 2, value: 3 }]);
  near(two.currents[2], 2, 1e-12);
  assert.throws(() => P.solveDC(2, [{ type: 'V', a: 1, b: 0, value: 5 }, { type: 'V', a: 1, b: 0, value: 3 }]));
  near(P.rcCharge(10, 1000, 1e-3, 1), 10 * (1 - Math.exp(-1)), 1e-12);
  near(P.rcDischarge(10, 1000, 1e-3, 1000 * 1e-3 * Math.LN2), 5, 1e-12);
  near(P.energyCostKWh(100, 10, 0.15), 0.15);
});

test('magnetism and induction', () => {
  near(P.forceOnCharge(1.6e-19, 1e6, 0.5), 8e-14, 1e-9);
  near(P.forceOnCharge(1.6e-19, 1e6, 0.5, 0), 0, 0, 1e-30);   // parallel to B: no force
  near(P.wireField(10, 0.02), 1e-4, 1e-6);
  near(P.solenoidField(1000, 0.5, 2), 4 * Math.PI * 1e-7 * 2000 * 2, 1e-6);
  near(P.faradayEMF(100, 0.02, 0.1), -20);
  near(P.motionalEMF(0.5, 0.2, 3), 0.3);
  near(P.transformerVs(120, 500, 25), 6);
  near(P.flux(0.4, 0.5, 60), 0.1, 1e-12);
  // electron in 1 mT at 1e6 m/s: r = mv/qB ≈ 5.69 mm
  near(P.cyclotronRadius(P.C.me, 1e6, P.C.e, 1e-3), 5.686e-3, 1e-3);
});

test('modern physics: photons, photoelectric, Bohr, decay, de Broglie', () => {
  near(P.photonEnergyEV(500e-9), 2.4797, 1e-4);
  near(P.photoelectricKmax(400e-9, 2.28), 3.0996 - 2.28, 1e-3);
  assert.ok(P.photoelectricKmax(700e-9, 2.28) < 0);              // red light below threshold
  near(P.thresholdWavelength(2.28) * 1e9, 543.8, 1e-3);
  near(P.bohrEnergyEV(1), -13.6057, 1e-6);
  near(P.hydrogenLineNm(3, 2), 656.1, 1e-3);                    // H-alpha (vacuum ≈ 656.3 nm; Bohr model w/o reduced mass)
  near(P.decayRemaining(800, 5730, 3 * 5730), 100, 1e-12);
  near(P.ageFromFraction(0.25, 5730), 11460, 1e-12);
  near(P.deBroglie(P.C.me, 1e6) * 1e9, 0.7274, 1e-3);
  near(P.massDefectEnergyMeV(1), 931.494, 1e-9);
  near(P.restEnergy(1), 8.98755e16, 1e-5);
});

test('relativity: γ, dilation, contraction, velocity addition, limits', () => {
  near(P.gammaBeta(0.6), 1.25, 1e-12);
  near(P.gammaBeta(0.8), 5 / 3, 1e-12);
  near(P.dilatedTime(1, 0.6 * P.C.c), 1.25, 1e-12);
  near(P.contractedLength(100, 0.8 * P.C.c), 60, 1e-12);
  near(P.velocityAdd(0.5 * P.C.c, 0.5 * P.C.c) / P.C.c, 0.8, 1e-12);
  near(P.velocityAdd(P.C.c, 0.9 * P.C.c), P.C.c, 1e-12);          // light speed is invariant
  near(P.gamma(30), 1, 1e-12);                                     // everyday speeds: classical
  near(P.relKE(1, 3e3), P.KE(1, 3e3), 1e-6);                       // low-speed limit → ½mv²
  assert.throws(() => P.gamma(P.C.c));
  near(P.schwarzschildRadius(P.C.Ms), 2954, 1e-3);
});

test('astrophysics', () => {
  near(P.wienPeakNm(5778), 501.5, 1e-3);
  near(P.hubbleVelocity(100), 7000);
  near(P.hubbleTimeGyr(70), 13.97, 2e-3);
  near(P.redshiftLowZ(660, 600), 0.1, 1e-12);
});

test('RK4 integrator: harmonic oscillator conserves energy to high precision', () => {
  let y = [1, 0]; const f = ([x, v]) => [v, -x];
  for (let i = 0; i < 6283; i++) y = P.rk4Step(f, y, 1e-3);
  near(y[0], Math.cos(6.283), 1e-8);
  near(0.5 * (y[0] ** 2 + y[1] ** 2), 0.5, 1e-10);
});
