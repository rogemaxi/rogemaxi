// Executable formula catalog for the Formula Laboratory. Each formula is written once as a residual
// r(v) = lhs − rhs; any variable can be solved for numerically (see src/engines/formula.js).
// Dimensions are exponent vectors over SI base units [kg, m, s, A, K, mol]; the dimensional check is
// automatic (rescaling the base units must leave the equation true) and is exercised in tests/unit/formula.test.js.
const D = (kg = 0, m = 0, s = 0, A = 0, K = 0, mol = 0) => [kg, m, s, A, K, mol];
const DIM = {
  none: D(), m: D(0, 1), s: D(0, 0, 1), kg: D(1), 'm/s': D(0, 1, -1), 'm/s²': D(0, 1, -2), N: D(1, 1, -2),
  J: D(1, 2, -2), W: D(1, 2, -3), Pa: D(1, -1, -2), 'kg·m/s': D(1, 1, -1), 'N·s': D(1, 1, -1), Hz: D(0, 0, -1),
  'rad/s': D(0, 0, -1), 'rad/s²': D(0, 0, -2), rad: D(), '°': D(), 'N/m': D(1, 0, -2), 'kg/m³': D(1, -3), 'm³': D(0, 3),
  'm²': D(0, 2), 'm³/s': D(0, 3, -1), K: D(0, 0, 0, 0, 1), 'J/(kg·K)': D(0, 2, -2, 0, -1), 'J/kg': D(0, 2, -2), mol: D(0, 0, 0, 0, 0, 1),
  C: D(0, 0, 1, 1), A: D(0, 0, 0, 1), V: D(1, 2, -3, -1), 'Ω': D(1, 2, -3, -2), F: D(-1, -2, 4, 2), 'N/C': D(1, 1, -3, -1),
  T: D(1, 0, -2, -1), Wb: D(1, 2, -2, -1), 'kg·m²': D(1, 2), 'N·m': D(1, 2, -2), 'kg·m²/s': D(1, 2, -1),
  'N·m²/kg²': D(-1, 3, -2), 'N·m²/C²': D(1, 3, -4, -2), 'J/(mol·K)': D(1, 2, -2, 0, -1, -1), 'J·s': D(1, 2, -1),
  'T·m/A': D(1, 1, -2, -2), 'W/m²': D(1, 0, -3),
};
const v = (s, name, unit, extra = {}) => ({ s, name, unit, dim: DIM[unit], ...extra });
const rad = d => d * Math.PI / 180;

export const FORMULAS = [
  // Motion
  { id: 'vavg', unit: 3, name: 'Average velocity', eq: 'v = Δx / Δt', vars: [v('v', 'velocity', 'm/s'), v('dx', 'displacement Δx', 'm'), v('dt', 'time interval Δt', 's', { pos: true })], r: x => x.v - x.dx / x.dt },
  { id: 'kin1', unit: 3, name: 'Velocity–time (constant a)', eq: 'v = v₀ + a·t', vars: [v('v', 'final velocity', 'm/s'), v('v0', 'initial velocity v₀', 'm/s'), v('a', 'acceleration', 'm/s²'), v('t', 'time', 's', { pos: true })], r: x => x.v - (x.v0 + x.a * x.t) },
  { id: 'kin2', unit: 3, name: 'Position–time (constant a)', eq: 'Δx = v₀·t + ½·a·t²', vars: [v('dx', 'displacement Δx', 'm'), v('v0', 'initial velocity v₀', 'm/s'), v('a', 'acceleration', 'm/s²'), v('t', 'time', 's', { pos: true })], r: x => x.dx - (x.v0 * x.t + 0.5 * x.a * x.t ** 2) },
  { id: 'kin3', unit: 3, name: 'Velocity–displacement (constant a)', eq: 'v² = v₀² + 2·a·Δx', vars: [v('v', 'final speed', 'm/s', { pos: true }), v('v0', 'initial speed v₀', 'm/s', { pos: true }), v('a', 'acceleration', 'm/s²'), v('dx', 'displacement Δx', 'm')], r: x => x.v ** 2 - (x.v0 ** 2 + 2 * x.a * x.dx) },
  { id: 'range', unit: 4, name: 'Level-ground projectile range', eq: 'R = v₀²·sin(2θ) / g', vars: [v('R', 'range', 'm', { pos: true }), v('v0', 'launch speed v₀', 'm/s', { pos: true }), v('th', 'launch angle θ', '°', { angle: true }), v('g', 'gravitational field g', 'm/s²', { pos: true, def: 9.8 })], r: x => x.R - x.v0 ** 2 * Math.sin(2 * rad(x.th)) / x.g },
  // Forces
  { id: 'n2', unit: 5, name: 'Newton’s second law', eq: 'ΣF = m·a', vars: [v('F', 'net force ΣF', 'N'), v('m', 'mass', 'kg', { pos: true }), v('a', 'acceleration', 'm/s²')], r: x => x.F - x.m * x.a },
  { id: 'weight', unit: 5, name: 'Weight', eq: 'W = m·g', vars: [v('W', 'weight', 'N', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('g', 'gravitational field g', 'm/s²', { pos: true, def: 9.8 })], r: x => x.W - x.m * x.g },
  { id: 'fric', unit: 5, name: 'Kinetic friction', eq: 'f = μk·N', vars: [v('f', 'friction force', 'N', { pos: true }), v('mu', 'coefficient μk', 'none', { pos: true }), v('N', 'normal force', 'N', { pos: true })], r: x => x.f - x.mu * x.N },
  { id: 'hooke', unit: 10, name: 'Hooke’s law (magnitude)', eq: 'F = k·x', vars: [v('F', 'spring force', 'N', { pos: true }), v('k', 'spring constant', 'N/m', { pos: true }), v('x', 'stretch or compression', 'm', { pos: true })], r: x => x.F - x.k * x.x },
  // Energy
  { id: 'work', unit: 6, name: 'Work by a constant force', eq: 'W = F·d·cos θ', vars: [v('W', 'work', 'J'), v('F', 'force', 'N', { pos: true }), v('d', 'displacement', 'm', { pos: true }), v('th', 'angle between F and d', '°', { angle: true })], r: x => x.W - x.F * x.d * Math.cos(rad(x.th)) },
  { id: 'ke', unit: 6, name: 'Kinetic energy', eq: 'KE = ½·m·v²', vars: [v('KE', 'kinetic energy', 'J', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('v', 'speed', 'm/s', { pos: true })], r: x => x.KE - 0.5 * x.m * x.v ** 2 },
  { id: 'peg', unit: 6, name: 'Gravitational potential energy', eq: 'PE = m·g·h', vars: [v('PE', 'potential energy', 'J'), v('m', 'mass', 'kg', { pos: true }), v('g', 'gravitational field g', 'm/s²', { pos: true, def: 9.8 }), v('h', 'height', 'm')], r: x => x.PE - x.m * x.g * x.h },
  { id: 'pes', unit: 6, name: 'Elastic potential energy', eq: 'PE = ½·k·x²', vars: [v('PE', 'elastic potential energy', 'J', { pos: true }), v('k', 'spring constant', 'N/m', { pos: true }), v('x', 'stretch or compression', 'm', { pos: true })], r: x => x.PE - 0.5 * x.k * x.x ** 2 },
  { id: 'power', unit: 6, name: 'Power', eq: 'P = W / t', vars: [v('P', 'power', 'W'), v('W', 'work or energy', 'J'), v('t', 'time', 's', { pos: true })], r: x => x.P - x.W / x.t },
  { id: 'powerv', unit: 6, name: 'Power from force and velocity', eq: 'P = F·v', vars: [v('P', 'power', 'W'), v('F', 'force along v', 'N'), v('v', 'speed', 'm/s', { pos: true })], r: x => x.P - x.F * x.v },
  // Momentum
  { id: 'mom', unit: 7, name: 'Momentum', eq: 'p = m·v', vars: [v('p', 'momentum', 'kg·m/s'), v('m', 'mass', 'kg', { pos: true }), v('v', 'velocity', 'm/s')], r: x => x.p - x.m * x.v },
  { id: 'imp', unit: 7, name: 'Impulse–momentum theorem', eq: 'F·Δt = m·Δv', vars: [v('F', 'average force', 'N'), v('dt', 'contact time Δt', 's', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('dv', 'change in velocity Δv', 'm/s')], r: x => x.F * x.dt - x.m * x.dv },
  { id: 'inel', unit: 7, name: 'Perfectly inelastic collision', eq: 'm₁·v₁ + m₂·v₂ = (m₁ + m₂)·v_f', vars: [v('m1', 'mass m₁', 'kg', { pos: true }), v('v1', 'velocity v₁', 'm/s'), v('m2', 'mass m₂', 'kg', { pos: true }), v('v2', 'velocity v₂', 'm/s'), v('vf', 'common final velocity', 'm/s')], r: x => x.m1 * x.v1 + x.m2 * x.v2 - (x.m1 + x.m2) * x.vf },
  // Circular motion & gravitation
  { id: 'ac', unit: 8, name: 'Centripetal acceleration', eq: 'a_c = v² / r', vars: [v('ac', 'centripetal acceleration', 'm/s²', { pos: true }), v('v', 'speed', 'm/s', { pos: true }), v('r', 'radius', 'm', { pos: true })], r: x => x.ac - x.v ** 2 / x.r },
  { id: 'fc', unit: 8, name: 'Centripetal force', eq: 'F_c = m·v² / r', vars: [v('F', 'centripetal force', 'N', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('v', 'speed', 'm/s', { pos: true }), v('r', 'radius', 'm', { pos: true })], r: x => x.F - x.m * x.v ** 2 / x.r },
  { id: 'grav', unit: 8, name: 'Universal gravitation', eq: 'F = G·m₁·m₂ / r²', vars: [v('F', 'gravitational force', 'N', { pos: true }), v('G', 'gravitational constant', 'N·m²/kg²', { pos: true, def: 6.674e-11 }), v('m1', 'mass m₁', 'kg', { pos: true }), v('m2', 'mass m₂', 'kg', { pos: true }), v('r', 'center-to-center distance', 'm', { pos: true })], r: x => x.F - x.G * x.m1 * x.m2 / x.r ** 2 },
  { id: 'orbit', unit: 8, name: 'Circular orbital speed', eq: 'v = √(G·M / r)', vars: [v('v', 'orbital speed', 'm/s', { pos: true }), v('G', 'gravitational constant', 'N·m²/kg²', { pos: true, def: 6.674e-11 }), v('M', 'central mass', 'kg', { pos: true }), v('r', 'orbital radius', 'm', { pos: true })], r: x => x.v - Math.sqrt(x.G * x.M / x.r) },
  { id: 'escape', unit: 8, name: 'Escape speed', eq: 'v_esc = √(2·G·M / r)', vars: [v('v', 'escape speed', 'm/s', { pos: true }), v('G', 'gravitational constant', 'N·m²/kg²', { pos: true, def: 6.674e-11 }), v('M', 'mass of the body', 'kg', { pos: true }), v('r', 'distance from center', 'm', { pos: true })], r: x => x.v - Math.sqrt(2 * x.G * x.M / x.r) },
  // Rotation
  { id: 'torque', unit: 9, name: 'Torque', eq: 'τ = r·F·sin θ', vars: [v('tau', 'torque τ', 'N·m'), v('r', 'lever arm distance', 'm', { pos: true }), v('F', 'force', 'N', { pos: true }), v('th', 'angle between r and F', '°', { angle: true })], r: x => x.tau - x.r * x.F * Math.sin(rad(x.th)) },
  { id: 'n2rot', unit: 9, name: 'Newton’s second law for rotation', eq: 'τ = I·α', vars: [v('tau', 'net torque τ', 'N·m'), v('I', 'moment of inertia', 'kg·m²', { pos: true }), v('al', 'angular acceleration α', 'rad/s²')], r: x => x.tau - x.I * x.al },
  { id: 'rotke', unit: 9, name: 'Rotational kinetic energy', eq: 'KE = ½·I·ω²', vars: [v('KE', 'rotational KE', 'J', { pos: true }), v('I', 'moment of inertia', 'kg·m²', { pos: true }), v('w', 'angular speed ω', 'rad/s', { pos: true })], r: x => x.KE - 0.5 * x.I * x.w ** 2 },
  { id: 'angmom', unit: 9, name: 'Angular momentum', eq: 'L = I·ω', vars: [v('L', 'angular momentum', 'kg·m²/s'), v('I', 'moment of inertia', 'kg·m²', { pos: true }), v('w', 'angular velocity ω', 'rad/s')], r: x => x.L - x.I * x.w },
  // Oscillations
  { id: 'tspring', unit: 10, name: 'Spring–mass period', eq: 'T = 2π·√(m / k)', vars: [v('T', 'period', 's', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('k', 'spring constant', 'N/m', { pos: true })], r: x => x.T - 2 * Math.PI * Math.sqrt(x.m / x.k) },
  { id: 'tpend', unit: 10, name: 'Simple pendulum period (small angles)', eq: 'T = 2π·√(L / g)', vars: [v('T', 'period', 's', { pos: true }), v('L', 'length', 'm', { pos: true }), v('g', 'gravitational field g', 'm/s²', { pos: true, def: 9.8 })], r: x => x.T - 2 * Math.PI * Math.sqrt(x.L / x.g) },
  // Fluids
  { id: 'density', unit: 11, name: 'Density', eq: 'ρ = m / V', vars: [v('rho', 'density ρ', 'kg/m³', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('V', 'volume', 'm³', { pos: true })], r: x => x.rho - x.m / x.V },
  { id: 'pressure', unit: 11, name: 'Pressure', eq: 'P = F / A', vars: [v('P', 'pressure', 'Pa', { pos: true }), v('F', 'perpendicular force', 'N', { pos: true }), v('A', 'area', 'm²', { pos: true })], r: x => x.P - x.F / x.A },
  { id: 'hydro', unit: 11, name: 'Hydrostatic (gauge) pressure', eq: 'P = ρ·g·h', vars: [v('P', 'gauge pressure', 'Pa', { pos: true }), v('rho', 'fluid density ρ', 'kg/m³', { pos: true }), v('g', 'gravitational field g', 'm/s²', { pos: true, def: 9.8 }), v('h', 'depth', 'm', { pos: true })], r: x => x.P - x.rho * x.g * x.h },
  { id: 'buoy', unit: 11, name: 'Buoyant force (Archimedes)', eq: 'F_b = ρ_fluid·g·V_sub', vars: [v('Fb', 'buoyant force', 'N', { pos: true }), v('rho', 'fluid density ρ', 'kg/m³', { pos: true }), v('g', 'gravitational field g', 'm/s²', { pos: true, def: 9.8 }), v('V', 'submerged volume', 'm³', { pos: true })], r: x => x.Fb - x.rho * x.g * x.V },
  { id: 'cont', unit: 11, name: 'Continuity equation', eq: 'A₁·v₁ = A₂·v₂', vars: [v('A1', 'area A₁', 'm²', { pos: true }), v('v1', 'speed v₁', 'm/s', { pos: true }), v('A2', 'area A₂', 'm²', { pos: true }), v('v2', 'speed v₂', 'm/s', { pos: true })], r: x => x.A1 * x.v1 - x.A2 * x.v2 },
  // Thermal
  { id: 'heat', unit: 12, name: 'Specific heat', eq: 'Q = m·c·ΔT', vars: [v('Q', 'heat', 'J'), v('m', 'mass', 'kg', { pos: true }), v('c', 'specific heat', 'J/(kg·K)', { pos: true }), v('dT', 'temperature change ΔT', 'K')], r: x => x.Q - x.m * x.c * x.dT },
  { id: 'latent', unit: 12, name: 'Latent heat', eq: 'Q = m·L', vars: [v('Q', 'heat', 'J', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('L', 'latent heat', 'J/kg', { pos: true })], r: x => x.Q - x.m * x.L },
  { id: 'gas', unit: 12, name: 'Ideal gas law', eq: 'P·V = n·R·T', vars: [v('P', 'pressure', 'Pa', { pos: true }), v('V', 'volume', 'm³', { pos: true }), v('n', 'amount', 'mol', { pos: true }), v('R', 'gas constant', 'J/(mol·K)', { pos: true, def: 8.314 }), v('T', 'absolute temperature', 'K', { pos: true })], r: x => x.P * x.V - x.n * x.R * x.T },
  // Waves & optics
  { id: 'wave', unit: 13, name: 'Wave speed', eq: 'v = f·λ', vars: [v('v', 'wave speed', 'm/s', { pos: true }), v('f', 'frequency', 'Hz', { pos: true }), v('lam', 'wavelength λ', 'm', { pos: true })], r: x => x.v - x.f * x.lam },
  { id: 'period', unit: 13, name: 'Period and frequency', eq: 'T = 1 / f', vars: [v('T', 'period', 's', { pos: true }), v('f', 'frequency', 'Hz', { pos: true })], r: x => x.T - 1 / x.f },
  { id: 'snell', unit: 14, name: 'Snell’s law', eq: 'n₁·sin θ₁ = n₂·sin θ₂', vars: [v('n1', 'index n₁', 'none', { pos: true }), v('t1', 'angle θ₁', '°', { angle: true }), v('n2', 'index n₂', 'none', { pos: true }), v('t2', 'angle θ₂', '°', { angle: true })], r: x => x.n1 * Math.sin(rad(x.t1)) - x.n2 * Math.sin(rad(x.t2)) },
  { id: 'lens', unit: 14, name: 'Thin lens / mirror equation', eq: '1/f = 1/d_o + 1/d_i', vars: [v('f', 'focal length', 'm'), v('do', 'object distance', 'm'), v('di', 'image distance', 'm')], r: x => 1 / x.f - (1 / x.do + 1 / x.di) },
  { id: 'clight', unit: 14, name: 'Speed of light in a medium', eq: 'n = c / v', vars: [v('n', 'index of refraction', 'none', { pos: true }), v('c', 'speed of light in vacuum', 'm/s', { pos: true, def: 2.998e8 }), v('v', 'speed in the medium', 'm/s', { pos: true })], r: x => x.n - x.c / x.v },
  // Electricity & magnetism
  { id: 'coulomb', unit: 15, name: 'Coulomb’s law', eq: 'F = k·q₁·q₂ / r²', vars: [v('F', 'electric force (+ repel)', 'N'), v('k', 'Coulomb constant', 'N·m²/C²', { pos: true, def: 8.988e9 }), v('q1', 'charge q₁', 'C'), v('q2', 'charge q₂', 'C'), v('r', 'separation', 'm', { pos: true })], r: x => x.F - x.k * x.q1 * x.q2 / x.r ** 2 },
  { id: 'efield', unit: 15, name: 'Electric field and force', eq: 'F = q·E', vars: [v('F', 'force', 'N'), v('q', 'charge', 'C'), v('E', 'field', 'N/C')], r: x => x.F - x.q * x.E },
  { id: 'cap', unit: 15, name: 'Capacitance', eq: 'Q = C·V', vars: [v('Q', 'charge', 'C'), v('C', 'capacitance', 'F', { pos: true }), v('V', 'voltage', 'V')], r: x => x.Q - x.C * x.V },
  { id: 'ohm', unit: 16, name: 'Ohm’s law', eq: 'V = I·R', vars: [v('V', 'voltage', 'V'), v('I', 'current', 'A'), v('R', 'resistance', 'Ω', { pos: true })], r: x => x.V - x.I * x.R },
  { id: 'epower', unit: 16, name: 'Electric power', eq: 'P = I·V', vars: [v('P', 'power', 'W'), v('I', 'current', 'A'), v('V', 'voltage', 'V')], r: x => x.P - x.I * x.V },
  { id: 'charge', unit: 16, name: 'Current', eq: 'I = Q / t', vars: [v('I', 'current', 'A'), v('Q', 'charge', 'C'), v('t', 'time', 's', { pos: true })], r: x => x.I - x.Q / x.t },
  { id: 'fmag', unit: 17, name: 'Magnetic force on a moving charge', eq: 'F = q·v·B·sin θ', vars: [v('F', 'force', 'N'), v('q', 'charge', 'C'), v('v', 'speed', 'm/s', { pos: true }), v('B', 'magnetic field', 'T', { pos: true }), v('th', 'angle between v and B', '°', { angle: true })], r: x => x.F - x.q * x.v * x.B * Math.sin(rad(x.th)) },
  { id: 'fwire', unit: 17, name: 'Magnetic force on a wire', eq: 'F = I·L·B·sin θ', vars: [v('F', 'force', 'N'), v('I', 'current', 'A'), v('L', 'wire length', 'm', { pos: true }), v('B', 'magnetic field', 'T', { pos: true }), v('th', 'angle between wire and B', '°', { angle: true })], r: x => x.F - x.I * x.L * x.B * Math.sin(rad(x.th)) },
  { id: 'bwire', unit: 17, name: 'Field of a long straight wire', eq: 'B = μ₀·I / (2π·r)', vars: [v('B', 'magnetic field', 'T', { pos: true }), v('mu0', 'permeability μ₀', 'T·m/A', { pos: true, def: 1.2566e-6 }), v('I', 'current', 'A', { pos: true }), v('r', 'distance', 'm', { pos: true })], r: x => x.B - x.mu0 * x.I / (2 * Math.PI * x.r) },
  { id: 'memf', unit: 17, name: 'Motional EMF', eq: 'ε = B·L·v', vars: [v('emf', 'EMF ε', 'V'), v('B', 'magnetic field', 'T', { pos: true }), v('L', 'rod length', 'm', { pos: true }), v('v', 'speed', 'm/s')], r: x => x.emf - x.B * x.L * x.v },
  { id: 'xfmr', unit: 17, name: 'Ideal transformer', eq: 'V_s / V_p = N_s / N_p', vars: [v('Vs', 'secondary voltage', 'V', { pos: true }), v('Vp', 'primary voltage', 'V', { pos: true }), v('Ns', 'secondary turns', 'none', { pos: true }), v('Np', 'primary turns', 'none', { pos: true })], r: x => x.Vs / x.Vp - x.Ns / x.Np },
  // Modern
  { id: 'photon', unit: 18, name: 'Photon energy', eq: 'E = h·f', vars: [v('E', 'photon energy', 'J', { pos: true }), v('h', 'Planck constant', 'J·s', { pos: true, def: 6.626e-34 }), v('f', 'frequency', 'Hz', { pos: true })], r: x => x.E - x.h * x.f },
  { id: 'debroglie', unit: 18, name: 'de Broglie wavelength', eq: 'λ = h / (m·v)', vars: [v('lam', 'wavelength λ', 'm', { pos: true }), v('h', 'Planck constant', 'J·s', { pos: true, def: 6.626e-34 }), v('m', 'mass', 'kg', { pos: true }), v('v', 'speed', 'm/s', { pos: true })], r: x => x.lam - x.h / (x.m * x.v) },
  { id: 'emc2', unit: 19, name: 'Mass–energy equivalence', eq: 'E = m·c²', vars: [v('E', 'rest energy', 'J', { pos: true }), v('m', 'mass', 'kg', { pos: true }), v('c', 'speed of light', 'm/s', { pos: true, def: 2.998e8 })], r: x => x.E - x.m * x.c ** 2 },
  { id: 'dilation', unit: 19, name: 'Time dilation', eq: 'Δt = Δt₀ / √(1 − v²/c²)', vars: [v('dt', 'dilated time Δt', 's', { pos: true }), v('dt0', 'proper time Δt₀', 's', { pos: true }), v('v', 'relative speed', 'm/s', { pos: true }), v('c', 'speed of light', 'm/s', { pos: true, def: 2.998e8 })], r: x => (x.v >= x.c ? NaN : x.dt - x.dt0 / Math.sqrt(1 - (x.v / x.c) ** 2)) },
];

export { DIM };
export const findFormula = id => FORMULAS.find(f => f.id === id);
