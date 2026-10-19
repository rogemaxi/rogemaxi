// Mechanics: kinematics, projectiles, forces, energy, momentum, circular motion, gravitation, rotation.
// All inputs and outputs are SI. Angles are in degrees unless the name ends in "Rad".
import { C } from './constants.js';

export const deg = d => d * Math.PI / 180;
export const toDeg = r => r * 180 / Math.PI;

// ---------- Vectors ----------
export const vecFromPolar = (mag, angleDeg) => [mag * Math.cos(deg(angleDeg)), mag * Math.sin(deg(angleDeg))];
export const vecMag = v => Math.hypot(...v);
export const vecAngle = v => toDeg(Math.atan2(v[1], v[0]));
export const vecAdd = (...vs) => vs.reduce((a, b) => a.map((x, i) => x + b[i]));
export const dot = (a, b) => a.reduce((s, x, i) => s + x * b[i], 0);
export const cross3 = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];

// ---------- 1D kinematics (constant acceleration) ----------
export const kin = {
  x: (x0, v0, a, t) => x0 + v0 * t + 0.5 * a * t * t,
  v: (v0, a, t) => v0 + a * t,
  vFromX: (v0, a, dx) => { const s = v0 * v0 + 2 * a * dx; if (s < 0) throw new RangeError('no real speed'); return Math.sqrt(s); },
  dxAvg: (v0, v, t) => 0.5 * (v0 + v) * t,
  // Smallest non-negative time to reach displacement dx; null if never.
  timeToDx(v0, a, dx) {
    if (a === 0) return v0 === 0 ? null : (dx / v0 >= 0 ? dx / v0 : null);
    const disc = v0 * v0 + 2 * a * dx;
    if (disc < 0) return null;
    const r = [(-v0 + Math.sqrt(disc)) / a, (-v0 - Math.sqrt(disc)) / a].filter(t => t >= -1e-12).sort((p, q) => p - q);
    return r.length ? Math.max(0, r[0]) : null;
  },
  stoppingDistance: (v0, decel) => v0 * v0 / (2 * decel),
};

// ---------- Projectiles (no air resistance, launch from height h0 above landing level) ----------
export function projectile(v0, angleDeg, h0 = 0, g = C.g) {
  const vx = v0 * Math.cos(deg(angleDeg)), vy = v0 * Math.sin(deg(angleDeg));
  const tFlight = (vy + Math.sqrt(vy * vy + 2 * g * h0)) / g;
  const tPeak = Math.max(0, vy / g);
  return {
    vx, vy, tFlight, tPeak,
    hMax: h0 + (vy > 0 ? vy * vy / (2 * g) : 0),
    range: vx * tFlight,
    pos: t => [vx * t, h0 + vy * t - 0.5 * g * t * t],
    vel: t => [vx, vy - g * t],
    impactSpeed: Math.hypot(vx, vy - g * tFlight),
  };
}
export const levelRange = (v0, angleDeg, g = C.g) => v0 * v0 * Math.sin(2 * deg(angleDeg)) / g;

// Quadratic-drag projectile, integrated with RK4. k = drag coefficient per unit mass (1/m): a = -k|v|v.
export function projectileDrag(v0, angleDeg, k, { h0 = 0, g = C.g, dt = 1e-3, tMax = 60 } = {}) {
  let s = [0, h0, v0 * Math.cos(deg(angleDeg)), v0 * Math.sin(deg(angleDeg))];
  const f = ([, , vx, vy]) => { const sp = Math.hypot(vx, vy); return [vx, vy, -k * sp * vx, -g - k * sp * vy]; };
  const path = [[0, s[0], s[1]]];
  let t = 0;
  while (t < tMax) {
    const prev = s;
    s = rk4Step(f, s, dt); t += dt;
    if (s[1] < 0) { // interpolate landing
      const fr = prev[1] / (prev[1] - s[1]);
      const xL = prev[0] + fr * (s[0] - prev[0]);
      path.push([t - dt + fr * dt, xL, 0]);
      return { range: xL, tFlight: t - dt + fr * dt, path, hMax: Math.max(...path.map(p => p[2])) };
    }
    path.push([t, s[0], s[1]]);
  }
  return { range: s[0], tFlight: t, path, hMax: Math.max(...path.map(p => p[2])) };
}

// ---------- Numerical integration ----------
export function rk4Step(f, y, h) {
  const add = (a, b, s) => a.map((x, i) => x + s * b[i]);
  const k1 = f(y), k2 = f(add(y, k1, h / 2)), k3 = f(add(y, k2, h / 2)), k4 = f(add(y, k3, h));
  return y.map((x, i) => x + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]));
}

// ---------- Forces ----------
export const weight = (m, g = C.g) => m * g;
export const accel = (Fnet, m) => { if (m <= 0) throw new RangeError('mass must be positive'); return Fnet / m; };

// Block pushed by applied force F (horizontal) on a level surface with static/kinetic friction.
export function pushedBlock(m, F, muS, muK, g = C.g) {
  const N = m * g, fsMax = muS * N;
  if (Math.abs(F) <= fsMax) return { moving: false, friction: -F, a: 0, N };
  const fk = -Math.sign(F) * muK * N;
  return { moving: true, friction: fk, a: (F + fk) / m, N };
}

// Block on an incline (angle θ), released from rest. Positive a = down the slope.
export function incline(m, thetaDeg, muS = 0, muK = 0, g = C.g) {
  const th = deg(thetaDeg);
  const Fpar = m * g * Math.sin(th), N = m * g * Math.cos(th);
  if (Fpar <= muS * N + 1e-12) return { slides: false, a: 0, N, Fpar, friction: Fpar };
  const fk = muK * N;
  return { slides: true, a: (Fpar - fk) / m, N, Fpar, friction: fk };
}
export const criticalAngle = muS => toDeg(Math.atan(muS));

// Atwood machine (ideal string and pulley): positive a = m2 descends.
export function atwood(m1, m2, g = C.g) {
  const a = (m2 - m1) * g / (m1 + m2);
  return { a, T: 2 * m1 * m2 * g / (m1 + m2) };
}
// Modified Atwood: m1 on table (kinetic friction μk), m2 hanging.
export function tableHanging(m1, m2, muK = 0, g = C.g) {
  const drive = m2 * g - muK * m1 * g;
  const a = Math.max(0, drive) / (m1 + m2);
  return { a, T: m2 * (g - a) };
}
// Apparent weight in an elevator with upward acceleration a.
export const apparentWeight = (m, aUp, g = C.g) => m * (g + aUp);

// ---------- Work, energy, power ----------
export const work = (F, d, angleDeg = 0) => F * d * Math.cos(deg(angleDeg));
export const KE = (m, v) => 0.5 * m * v * v;
export const PEg = (m, h, g = C.g) => m * g * h;
export const PEs = (k, x) => 0.5 * k * x * x;
export const power = (W, t) => W / t;
export const efficiency = (useful, input) => useful / input;
export const speedFromDrop = (h, g = C.g) => Math.sqrt(2 * g * h);

// ---------- Momentum and collisions (1D unless noted) ----------
export const momentum = (m, v) => m * v;
export const impulse = (F, dt) => F * dt;
export function elastic1D(m1, v1, m2, v2) {
  return [((m1 - m2) * v1 + 2 * m2 * v2) / (m1 + m2), ((m2 - m1) * v2 + 2 * m1 * v1) / (m1 + m2)];
}
export const perfectlyInelastic1D = (m1, v1, m2, v2) => (m1 * v1 + m2 * v2) / (m1 + m2);
// General 1D collision with coefficient of restitution e (0 = stick, 1 = elastic).
export function collide1D(m1, v1, m2, v2, e) {
  const P = m1 * v1 + m2 * v2, M = m1 + m2;
  return [(P + m2 * e * (v2 - v1)) / M, (P + m1 * e * (v1 - v2)) / M];
}
export const recoil = (mBullet, vBullet, mGun) => -mBullet * vBullet / mGun;
export const centerOfMass = (masses, xs) => masses.reduce((s, m, i) => s + m * xs[i], 0) / masses.reduce((a, b) => a + b, 0);

// ---------- Circular motion and gravitation ----------
export const centripetalAccel = (v, r) => v * v / r;
export const centripetalForce = (m, v, r) => m * v * v / r;
export const periodFromSpeed = (r, v) => 2 * Math.PI * r / v;
export const gravForce = (m1, m2, r) => C.G * m1 * m2 / (r * r);
export const gField = (M, r) => C.G * M / (r * r);
export const orbitalSpeed = (M, r) => Math.sqrt(C.G * M / r);
export const orbitalPeriod = (M, a) => 2 * Math.PI * Math.sqrt(a ** 3 / (C.G * M));
export const escapeSpeed = (M, r) => Math.sqrt(2 * C.G * M / r);
export const orbitalEnergy = (M, m, a) => -C.G * M * m / (2 * a);
export const minTopSpeed = (r, g = C.g) => Math.sqrt(g * r);              // vertical loop
export const bankAngleNoFriction = (v, r, g = C.g) => toDeg(Math.atan(v * v / (r * g)));
export const flatCurveMaxSpeed = (muS, r, g = C.g) => Math.sqrt(muS * g * r);

// ---------- Rotation ----------
export const inertia = {
  point: (m, r) => m * r * r,
  hoop: (m, r) => m * r * r,
  disk: (m, r) => 0.5 * m * r * r,
  solidSphere: (m, r) => 0.4 * m * r * r,
  hollowSphere: (m, r) => (2 / 3) * m * r * r,
  rodCenter: (m, L) => m * L * L / 12,
  rodEnd: (m, L) => m * L * L / 3,
};
// β = I/(m r²) shape factor for rolling without slipping.
export const shapeFactor = { hoop: 1, disk: 0.5, solidSphere: 0.4, hollowSphere: 2 / 3 };
export const rollingAccel = (thetaDeg, beta, g = C.g) => g * Math.sin(deg(thetaDeg)) / (1 + beta);
export const rollingSpeedFromHeight = (h, beta, g = C.g) => Math.sqrt(2 * g * h / (1 + beta));
export const torque = (r, F, angleDeg = 90) => r * F * Math.sin(deg(angleDeg));
export const rotKE = (I, w) => 0.5 * I * w * w;
export const angMomentum = (I, w) => I * w;
export const rotKin = {
  theta: (th0, w0, alpha, t) => th0 + w0 * t + 0.5 * alpha * t * t,
  omega: (w0, alpha, t) => w0 + alpha * t,
};
export const rpmToRad = rpm => rpm * 2 * Math.PI / 60;
