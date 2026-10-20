// Student reference data: standards crosswalk, constants, SI units, laboratory safety, and math reference.
//
// Standards: benchmark CODES and TEXT below were copied from the CPALMS course page for Physics 1 (#2003380),
// https://www.cpalms.org/PreviewCourse/Preview/21084, retrieved 2026-10-19 → status "verified" means the code and
// wording were confirmed on that page. The ALIGNMENT (which sections teach each benchmark) is the author's mapping
// and is marked "provisional" until a Florida-certified teacher or the owner reviews it. CPALMS lists 52 standards for
// the course; the B.E.S.T. ELA Expectations (ELA.K12.EE.*) and Mathematical Thinking and Reasoning (MA.K12.MTR.*)
// standards apply across the whole course and are listed once rather than mapped section by section.
// Physics 1 Honors (#2003390) was not retrieved; Honors alignment is therefore not claimed.
export const STANDARDS_SOURCE = { course: 'Physics 1 (#2003380)', url: 'https://www.cpalms.org/PreviewCourse/Preview/21084', retrieved: '2026-10-19', total: 52 };

export const STANDARDS = [
  ['SC.912.E.5.2', 'Identify patterns in the organization and distribution of matter in the universe and the forces that determine them.', ['19.6', '19.7', '19.8']],
  ['SC.912.E.5.6', 'Develop logical connections through physical principles, including Kepler’s and Newton’s Laws about the relationships and the effects of Earth, Moon, and Sun on each other.', ['8.5', '8.6', '8.7', '8.8']],
  ['SC.912.N.1.1', 'Define a problem based on a specific body of knowledge, for example: biology, chemistry, physics, and earth/space science, and do the following: pose questions, conduct systematic observations, examine what is already known, review it in light of empirical evidence, plan investigations, use tools to gather, analyze, and interpret data, pose answers and explanations, justify them with evidence, communicate results, and evaluate the explanations of others. (abridged)', ['1.3', '1.8', '1.9', '20.2']],
  ['SC.912.N.1.2', 'Describe and explain what characterizes science and its methods.', ['1.1', '1.2']],
  ['SC.912.N.1.5', 'Describe and provide examples of how similar investigations conducted in many parts of the world result in the same outcome.', ['1.2', '20.2']],
  ['SC.912.N.1.6', 'Describe how scientific inferences are drawn from scientific observations and provide examples from the content being studied.', ['1.2', '1.8']],
  ['SC.912.N.1.7', 'Recognize the role of creativity in constructing scientific questions, methods and explanations.', ['1.2', '20.1']],
  ['SC.912.N.2.2', 'Identify which questions can be answered through science and which questions are outside the boundaries of scientific investigation, such as questions addressed by other ways of knowing, such as art, philosophy, and religion.', ['1.1']],
  ['SC.912.N.2.4', 'Explain that scientific knowledge is both durable and robust and open to change.', ['1.2', '18.1']],
  ['SC.912.N.2.5', 'Describe instances in which scientists’ varied backgrounds, talents, interests, and goals influence the inferences and explanations they make, and that competing interpretations are a strength of science.', ['18.1', '18.4']],
  ['SC.912.N.3.2', 'Describe the role consensus plays in the historical development of a theory in any one of the disciplines of science.', ['18.1']],
  ['SC.912.N.3.3', 'Explain that scientific laws are descriptions of specific relationships under given conditions in nature, but do not offer explanations for those relationships.', ['1.2', '8.5']],
  ['SC.912.N.3.4', 'Recognize that theories do not become laws, nor do laws become theories; theories are well supported explanations and laws are well supported descriptions.', ['1.2']],
  ['SC.912.N.3.5', 'Describe the function of models in science, and identify the wide range of models used in science.', ['1.2', '1.9', '20.1', '20.3']],
  ['SC.912.N.4.1', 'Explain how scientific knowledge and reasoning provide an empirically-based perspective to inform society’s decision making.', ['20.5', '20.8']],
  ['SC.912.P.8.1', 'Differentiate among the four states of matter.', ['11.1', '12.4']],
  ['SC.912.P.8.3', 'Explore the scientific theory of atoms (also known as atomic theory) by describing changes in the atomic model over time and why those changes were necessitated by experimental evidence.', ['18.1', '18.2']],
  ['SC.912.P.10.1', 'Differentiate among the various forms of energy and recognize that they can be transformed from one form to others.', ['6.1', '6.2', '6.3', '6.4', '6.7']],
  ['SC.912.P.10.2', 'Explore the Law of Conservation of Energy by differentiating among open, closed, and isolated systems and explain that the total energy in an isolated system is a conserved quantity.', ['6.6', '6.7', '12.7']],
  ['SC.912.P.10.3', 'Compare and contrast work and power qualitatively and quantitatively.', ['6.1', '6.5', '6.8']],
  ['SC.912.P.10.4', 'Describe heat as the energy transferred by convection, conduction, and radiation, and explain the connection of heat to change in temperature or states of matter.', ['12.2', '12.3', '12.4', '12.5']],
  ['SC.912.P.10.5', 'Relate temperature to the average molecular kinetic energy.', ['12.1', '12.6']],
  ['SC.912.P.10.10', 'Compare the magnitude and range of the four fundamental forces (gravitational, electromagnetic, weak nuclear, strong nuclear).', ['5.1', '18.6']],
  ['SC.912.P.10.13', 'Relate the configuration of static charges to the electric field, electric force, electric potential, and electric potential energy.', ['15.3', '15.4', '15.5', '15.6']],
  ['SC.912.P.10.14', 'Differentiate among conductors, semiconductors, and insulators.', ['15.2', '16.1']],
  ['SC.912.P.10.15', 'Investigate and explain the relationships among current, voltage, resistance, and power.', ['16.1', '16.2', '16.3', '16.4', '16.5', '16.7']],
  ['SC.912.P.10.18', 'Explore the theory of electromagnetism by comparing and contrasting the different parts of the electromagnetic spectrum in terms of wavelength, frequency, and energy, and relate them to phenomena and applications.', ['14.1', '18.3']],
  ['SC.912.P.10.20', 'Describe the measurable properties of waves and explain the relationships among them and how these properties change when the wave moves from one medium to another.', ['13.1', '13.2', '13.4', '14.3']],
  ['SC.912.P.10.21', 'Qualitatively describe the shift in frequency in sound or electromagnetic waves due to the relative motion of a source or a receiver.', ['13.7', '19.8']],
  ['SC.912.P.10.22', 'Construct ray diagrams and use thin lens and mirror equations to locate the images formed by lenses and mirrors.', ['14.2', '14.5', '14.6']],
  ['SC.912.P.12.1', 'Distinguish between scalar and vector quantities and assess which should be used to describe an event.', ['2.4', '2.5', '3.1']],
  ['SC.912.P.12.2', 'Analyze the motion of an object in terms of its position, velocity, and acceleration (with respect to a frame of reference) as functions of time.', ['2.6', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '4.1']],
  ['SC.912.P.12.3', 'Interpret and apply Newton’s three laws of motion.', ['5.1', '5.2', '5.3', '5.4', '5.5', '5.6', '5.7', '5.8']],
  ['SC.912.P.12.4', 'Describe how the gravitational force between two objects depends on their masses and the distance between them.', ['8.5', '8.6']],
  ['SC.912.P.12.5', 'Apply the law of conservation of linear momentum to interactions, such as collisions between objects.', ['7.3', '7.4', '7.5', '7.6', '7.7']],
  ['SC.912.P.12.7', 'Recognize that nothing travels faster than the speed of light in vacuum which is the same for all observers no matter how they or the light source are moving.', ['19.1', '19.2']],
  ['SC.912.P.12.9', 'Recognize that time, length, and energy depend on the frame of reference.', ['19.3', '19.4']],
].map(([code, text, sections]) => ({ code, text, sections, textStatus: 'verified', alignment: 'provisional' }));

export const CROSS_COURSE = ['MA.K12.MTR.1.1–7.1 (Mathematical Thinking and Reasoning)', 'ELA.K12.EE.1.1–6.1 (B.E.S.T. ELA Expectations)'];

export const SAFETY = [
  { title: 'Before every lab', items: ['Read the whole procedure and identify every hazard before touching equipment.', 'Wear safety goggles whenever objects are launched, springs are stretched, glass is used, or liquids are heated.', 'Tie back long hair and loose clothing; keep the bench clear of bags and drinks.', 'Know where the eyewash station, fire extinguisher, and first-aid kit are.'] },
  { title: 'Mechanics and launchers', items: ['Never aim a launcher, rubber band, or spring at a person; launch only into a cleared zone.', 'Stretch springs only within their marked range — overstretched springs can snap back.', 'Clamp tracks and ramps securely; keep feet clear of falling masses.'] },
  { title: 'Heat and fluids', items: ['Hot plates and heated water look the same as cold ones: test with the back of your hand from a distance and use tongs or heat-resistant gloves.', 'Clean up spills immediately; wet floors near electrical equipment are a shock and slip hazard.'] },
  { title: 'Electricity', items: ['Use only low-voltage sources (batteries or classroom power supplies) for student circuits — never wall outlets.', 'Build and change circuits with the power off; connect the source last.', 'A wire or resistor that gets hot means too much current: disconnect at once.', 'Never connect an ammeter directly across a battery; it is placed in series.'] },
  { title: 'Light and radiation', items: ['Never look into a laser beam or its reflection; keep beams below eye level.', 'Sealed classroom radioactive sources are handled with tongs, kept briefly, and returned; wash hands afterwards.'] },
  { title: 'After the lab', items: ['Turn off and unplug equipment, return materials, and wash your hands.', 'Report every injury or broken equipment to the teacher immediately, even if it seems minor.'] },
];

export const MATH = [
  { title: 'Algebra', items: ['Solve for a variable by undoing operations in reverse order: a = F/m ⇒ F = m·a ⇒ m = F/a.', 'Quadratic formula: x = (−b ± √(b² − 4ac)) / (2a).', 'Proportional reasoning: if y ∝ x², doubling x multiplies y by 4; if y ∝ 1/r², doubling r divides y by 4.'] },
  { title: 'Right-triangle trigonometry', items: ['sin θ = opposite/hypotenuse, cos θ = adjacent/hypotenuse, tan θ = opposite/adjacent.', 'Components: Ax = A cos θ, Ay = A sin θ (θ measured from +x).', 'Magnitude and direction: A = √(Ax² + Ay²), θ = tan⁻¹(Ay/Ax) — check the quadrant.', 'Pythagorean theorem: c² = a² + b².'] },
  { title: 'Geometry', items: ['Circle: circumference 2πr, area πr².', 'Sphere: surface area 4πr², volume (4/3)πr³.', 'Cylinder: volume πr²h.', 'Radian measure: s = rθ; 360° = 2π rad.'] },
  { title: 'Graphs', items: ['Slope = rise/run = Δy/Δx, with units of (y units)/(x units).', 'Area under a curve = Σ y·Δx, with units of (y units)·(x units).', 'A straight line through the origin means y ∝ x.'] },
  { title: 'Scientific notation and logs', items: ['(a × 10ᵐ)(b × 10ⁿ) = ab × 10ᵐ⁺ⁿ.', 'log₁₀(10ⁿ) = n; decibels: β = 10 log₁₀(I/I₀).', 'Half-life: N = N₀(½)^(t/T½).'] },
];

export const PREFIXES = [['tera', 'T', '10¹²'], ['giga', 'G', '10⁹'], ['mega', 'M', '10⁶'], ['kilo', 'k', '10³'], ['centi', 'c', '10⁻²'], ['milli', 'm', '10⁻³'], ['micro', 'µ', '10⁻⁶'], ['nano', 'n', '10⁻⁹'], ['pico', 'p', '10⁻¹²']];
export const BASE_UNITS = [['length', 'metre', 'm'], ['mass', 'kilogram', 'kg'], ['time', 'second', 's'], ['electric current', 'ampere', 'A'], ['temperature', 'kelvin', 'K'], ['amount of substance', 'mole', 'mol'], ['luminous intensity', 'candela', 'cd']];
export const DERIVED_UNITS = [['force', 'newton', 'N', 'kg·m/s²'], ['energy, work', 'joule', 'J', 'N·m = kg·m²/s²'], ['power', 'watt', 'W', 'J/s'], ['pressure', 'pascal', 'Pa', 'N/m²'], ['frequency', 'hertz', 'Hz', '1/s'], ['charge', 'coulomb', 'C', 'A·s'], ['potential difference', 'volt', 'V', 'J/C'], ['resistance', 'ohm', 'Ω', 'V/A'], ['capacitance', 'farad', 'F', 'C/V'], ['magnetic field', 'tesla', 'T', 'N/(A·m)'], ['magnetic flux', 'weber', 'Wb', 'T·m²']];
export const CONVERSIONS = ['1 km = 1000 m · 1 m = 100 cm · 1 in = 2.54 cm (exact)', '1 h = 3600 s · 1 km/h = 1/3.6 m/s · 1 mi/h = 0.447 m/s', '1 L = 10⁻³ m³ = 1000 cm³', '1 atm = 101 325 Pa · 1 kPa = 1000 Pa', 'T(K) = T(°C) + 273.15 · T(°F) = 1.8·T(°C) + 32', '1 eV = 1.602 × 10⁻¹⁹ J · 1 kWh = 3.6 × 10⁶ J', '1 cal = 4.186 J · 1 u = 931.5 MeV/c²'];

export const CONSTANT_NAMES = {
  g: ['Gravitational field strength at Earth’s surface (course value)', 'm/s²'], g0: ['Standard gravity (exact)', 'm/s²'], G: ['Gravitational constant', 'N·m²/kg²'],
  c: ['Speed of light in vacuum (exact)', 'm/s'], h: ['Planck constant (exact)', 'J·s'], hbar: ['Reduced Planck constant ħ', 'J·s'], e: ['Elementary charge (exact)', 'C'],
  me: ['Electron mass', 'kg'], mp: ['Proton mass', 'kg'], u: ['Atomic mass unit', 'kg'], k: ['Coulomb constant 1/(4πε₀)', 'N·m²/C²'], eps0: ['Permittivity of free space ε₀', 'F/m'],
  mu0: ['Permeability of free space μ₀', 'N/A²'], kB: ['Boltzmann constant (exact)', 'J/K'], NA: ['Avogadro constant (exact)', '1/mol'], R: ['Gas constant', 'J/(mol·K)'],
  sigma: ['Stefan–Boltzmann constant', 'W/(m²·K⁴)'], atm: ['Standard atmosphere (exact)', 'Pa'], Me: ['Earth mass', 'kg'], Re: ['Earth mean radius', 'm'], Ms: ['Sun mass', 'kg'],
  AU: ['Astronomical unit (exact)', 'm'], eV: ['Electronvolt (exact)', 'J'], rhoWater: ['Density of water (≈4 °C)', 'kg/m³'], vSound: ['Speed of sound in air at 20 °C', 'm/s'],
  cWater: ['Specific heat of water', 'J/(kg·K)'], LfWater: ['Latent heat of fusion of water', 'J/kg'], LvWater: ['Latent heat of vaporization of water', 'J/kg'], H0: ['Hubble constant (representative; measurements range ≈ 67–73)', 'km/s/Mpc'],
};

// Strings exposed to the translation tooling (scope "ref.<key>").
export const TRANSLATABLE = {
  standards: STANDARDS.map(s => ({ text: s.text })), safety: SAFETY, math: MATH,
  units: { base: BASE_UNITS.map(b => [b[0], b[1]]), derived: DERIVED_UNITS.map(d => [d[0], d[1]]) }, constants: Object.fromEntries(Object.entries(CONSTANT_NAMES).map(([k, v]) => [k, v[0]])),
};
