// Unit 5 — Newton's Laws and Force Analysis. Original ByrdWay instructional content.
// Numeric answers are restated as `calc` expressions over the physics library and re-checked by tests/unit/content.test.js.
export default {
  num: 5,
  lab: 5,
  bridges: [
    { gap: 'Solving a = F/m for F or m', bridge: 'Write F = m·a as a triangle with F on top. Cover the quantity you want: F = m·a, m = F/a, a = F/m. Then check the unit: N ÷ kg = m/s².' },
    { gap: 'Adding vectors that point in opposite directions', bridge: 'Choose one direction as positive and give every force a sign. 30 N right and 12 N left is +30 + (−12) = +18 N, so 18 N to the right.' },
    { gap: 'Sine and cosine components on a slope', bridge: 'On an incline of angle θ, the weight component along the slope uses sin θ and the component into the slope uses cos θ. Check with θ = 0 (flat): along-slope part = 0, into-slope part = full weight.' },
  ],
  blueprint: [
    { see: 'Object at rest or moving at constant velocity', think: 'Equilibrium: ΣF = 0 in every direction', tool: 'Newton’s first law; balance forces', trap: 'Constant velocity does NOT mean no forces — it means the forces cancel.' },
    { see: 'Speeding up, slowing down, or turning', think: 'There is a net force in the direction of the acceleration', tool: 'ΣF = m·a along each axis', trap: 'The net force points along the acceleration, not necessarily along the velocity.' },
    { see: 'Two objects push or pull on each other', think: 'Third-law pair: equal size, opposite direction, different objects', tool: 'F(A on B) = −F(B on A)', trap: 'Third-law forces act on different objects, so they never cancel each other.' },
    { see: 'Object on a slope', think: 'Tilt your axes to match the slope', tool: 'Along: mg sinθ − f = m a. Perpendicular: N = mg cosθ (no other perpendicular forces)', trap: 'N = mg only on a level surface with no vertical pushes or pulls.' },
    { see: 'Strings, pulleys, or objects that move together', think: 'Same acceleration magnitude for connected parts', tool: 'One ΣF = m·a per object, or treat the system as one mass for a', trap: 'Tension is internal to the system — it cancels when you treat all masses together.' },
    { see: 'Elevator or accelerating frame', think: 'Scale reading = normal force', tool: 'N = m(g + a) with up positive', trap: 'The scale does not read your weight when the elevator accelerates.' },
  ],
  sections: {
    '5.3': {
      objectives: [
        'State Newton’s second law as ΣF = m·a and explain each term, including that ΣF is the vector sum of all forces on one object.',
        'Predict how acceleration changes when net force or mass changes, using proportional reasoning.',
        'Calculate net force, mass, or acceleration from the other two, with correct SI units and directions.',
        'Apply the second law along each axis separately for forces in two dimensions.',
      ],
      prereqs: [
        'Acceleration is the rate of change of velocity (Unit 3.3).',
        'Forces are vectors with magnitude and direction (Section 5.1).',
        'Solving a two-variable proportion such as a = F/m (Unit 2.1).',
      ],
      observe: 'Push an empty shopping cart and then a full one with the same effort. The empty cart speeds up quickly; the full cart barely gets going. Now push the full cart twice as hard. What did you change, and what happened to how quickly it sped up?',
      predict: {
        prompt: 'A cart accelerates at 2 m/s² when pushed with a net force F. You keep the same net force but triple the cart’s mass. What is the new acceleration?',
        choices: ['6 m/s²', '2 m/s²', 'About 0.67 m/s²', 'Zero — it is too heavy to move'],
        correct: 2,
        why: 'Acceleration is inversely proportional to mass when net force is fixed: a = F/m. Triple the mass → one-third the acceleration: 2 ÷ 3 ≈ 0.67 m/s². Any nonzero net force accelerates any mass; heavy objects just accelerate less.',
      },
      intro: 'Newton’s second law connects the cause of a change in motion (net force) to the change itself (acceleration). For one object, the vector sum of every force acting on it equals its mass times its acceleration: ΣF = m·a.',
      explain: [
        'Read the law in two directions. Forward: if you know all the forces, you can predict exactly how the motion will change. Backward: if you measure the acceleration, you know the net force — even if you cannot see what is pushing.',
        'Mass here is inertial mass: a measure of how strongly an object resists changes in its velocity. Double the mass and the same net force produces half the acceleration. Double the net force on the same mass and the acceleration doubles.',
        'Because force and acceleration are vectors, the law holds along every direction independently: ΣFx = m·ax and ΣFy = m·ay. Acceleration always points in the same direction as the net force — not necessarily the direction the object is moving. A car braking while moving forward has a backward net force and a backward acceleration.',
        'The law contains Newton’s first law as a special case: if ΣF = 0, then a = 0, so velocity stays constant (including staying at rest).',
        'Limits of the model: ΣF = m·a holds in inertial (non-accelerating) reference frames, for objects whose mass is constant, and at speeds far below the speed of light. Rockets losing fuel and particles near light speed need the more general form ΣF = Δp/Δt (Unit 7 and Unit 19).',
      ],
      vocab: [
        ['Net force (ΣF)', 'The vector sum of all forces acting on one object.'],
        ['Inertial mass', 'The property of an object that measures its resistance to acceleration, measured in kilograms.'],
        ['Newton (N)', 'The SI unit of force: the net force that gives a 1 kg mass an acceleration of 1 m/s². 1 N = 1 kg·m/s².'],
        ['Inertial reference frame', 'A viewpoint that is not accelerating, in which Newton’s laws hold without extra fictitious forces.'],
        ['Proportional reasoning', 'Predicting how one quantity changes when another is scaled, e.g. a ∝ F and a ∝ 1/m.'],
      ],
      formulas: [
        { eq: 'ΣF = m·a', id: 'newton2', vars: [['ΣF', 'net force', 'N'], ['m', 'mass', 'kg'], ['a', 'acceleration', 'm/s²']], when: 'Any object of constant mass, in an inertial frame, at everyday speeds.' },
        { eq: 'ΣFx = m·ax,  ΣFy = m·ay', id: 'newton2xy', vars: [['ΣFx, ΣFy', 'net force components', 'N'], ['ax, ay', 'acceleration components', 'm/s²']], when: 'Forces in two dimensions: apply the law along each axis separately.' },
      ],
      derivation: [
        'Experiments with a fixed mass show a ∝ ΣF (double the pull, double the acceleration).',
        'Experiments with a fixed net force show a ∝ 1/m (double the mass, half the acceleration).',
        'Combining both: a ∝ ΣF/m, so ΣF = k·m·a for some constant k.',
        'The newton is defined so that k = 1: 1 N is the net force that gives 1 kg an acceleration of 1 m/s². Therefore ΣF = m·a.',
      ],
      units: 'Check every answer with units: [ΣF] = N = kg·m/s². Dividing N by kg gives m/s², an acceleration; dividing N by m/s² gives kg, a mass. If your units do not reduce to the quantity you want, a step is wrong. Grams must be converted to kilograms before using the law.',
      example: {
        problem: 'A 1200 kg car is pushed by a driving force of 3600 N forward while friction and air resistance together exert 1200 N backward. Find its acceleration.',
        steps: [
          'Choose forward as positive. Identify the forces along the motion: +3600 N (drive) and −1200 N (resistance).',
          'Net force: ΣF = 3600 N + (−1200 N) = +2400 N.',
          'Apply the second law: a = ΣF/m = 2400 N ÷ 1200 kg.',
          'Units: N/kg = (kg·m/s²)/kg = m/s². ✓',
          'a = +2.0 m/s², forward. Sense check: a real car speeding up gently has an acceleration of a few m/s². ✓',
        ],
        answer: 'a = 2.0 m/s² forward',
      },
      guided: [
        { id: 'g1', kind: 'num', q: 'A net force of 45 N acts on a 9.0 kg box. What is its acceleration?', answer: 5, unit: 'm/s²', calc: 'P.accel(45, 9)', hints: ['Which form of the law gives acceleration directly?', 'a = ΣF/m. Put the numbers in with units.'], solution: 'a = ΣF/m = 45 N ÷ 9.0 kg = 5.0 m/s².' },
        { id: 'g2', kind: 'num', q: 'A 0.40 kg soccer ball accelerates at 30 m/s² during a kick. What net force does the foot exert (assume it is the only significant force)?', answer: 12, unit: 'N', calc: '0.40 * 30', hints: ['You want force, so multiply.', 'ΣF = m·a = 0.40 kg × 30 m/s².'], solution: 'ΣF = m·a = 0.40 kg × 30 m/s² = 12 N.' },
        { id: 'g3', kind: 'num', q: 'Two people pull a 50 kg sled in the same direction with 120 N and 80 N, and snow friction is 50 N. Find the sled’s acceleration.', answer: 3, unit: 'm/s²', calc: 'P.accel(120 + 80 - 50, 50)', hints: ['Add the pulls with signs: friction opposes motion.', 'ΣF = 120 + 80 − 50 = 150 N. Now divide by the mass.'], solution: 'ΣF = 120 N + 80 N − 50 N = 150 N; a = 150 N ÷ 50 kg = 3.0 m/s² in the direction of the pulls.' },
      ],
      practice: [
        { id: 'p1', kind: 'num', q: 'What net force is needed to accelerate a 1500 kg car at 2.4 m/s²?', answer: 3600, unit: 'N', calc: '1500 * 2.4', solution: 'ΣF = m·a = 1500 kg × 2.4 m/s² = 3600 N.' },
        { id: 'p2', kind: 'num', q: 'A 250 g cart is pulled by a net force of 0.75 N. What is its acceleration?', answer: 3, unit: 'm/s²', calc: 'P.accel(0.75, 0.250)', solution: 'Convert: 250 g = 0.250 kg. a = 0.75 N ÷ 0.250 kg = 3.0 m/s². (Forgetting to convert gives 0.003 m/s² — a factor of 1000 too small.)' },
        { id: 'p3', kind: 'num', q: 'A rocket sled of mass 800 kg speeds up from 0 to 60 m/s in 4.0 s. What average net force acts on it?', answer: 12000, unit: 'N', calc: '800 * (60 - 0) / 4', solution: 'a = Δv/Δt = 60 m/s ÷ 4.0 s = 15 m/s². ΣF = m·a = 800 kg × 15 m/s² = 1.2 × 10⁴ N.' },
        { id: 'p4', kind: 'mc', q: 'A hockey puck slides to the right and is slowing down. Ignoring vertical forces, which way does the net force on it point?', choices: ['To the right, in the direction of motion', 'To the left, opposite the motion', 'There is no net force because it is still moving', 'Straight down'], correct: 1, solution: 'Slowing down while moving right means the acceleration points left. The net force always points along the acceleration, so it points left (friction from the ice).' },
        { id: 'p5', kind: 'num', q: 'The same net force gives cart A an acceleration of 6.0 m/s² and cart B an acceleration of 2.0 m/s². If cart A has a mass of 1.5 kg, what is the mass of cart B?', answer: 4.5, unit: 'kg', calc: '(1.5 * 6.0) / 2.0', solution: 'Same ΣF: m_A·a_A = m_B·a_B → m_B = 1.5 kg × 6.0 / 2.0 = 4.5 kg. Proportional reasoning: one-third the acceleration means three times the mass.' },
      ],
      misconceptions: [
        { wrong: 'A moving object must have a net force pushing it forward.', right: 'Motion at constant velocity needs zero net force. A net force changes the velocity; it is not required to maintain it.', feedback: 'If you answered “forward,” ask: is the object speeding up? If not, the forward and backward forces balance.' },
        { wrong: 'Heavier objects need a force to “overcome their mass” before they can move at all.', right: 'Any nonzero net force accelerates any mass. Large masses accelerate less, but never zero.', feedback: 'Static friction can prevent motion — but that is a force, not the mass itself.' },
        { wrong: 'Acceleration points in the direction of motion.', right: 'Acceleration points in the direction of the net force. Braking produces acceleration opposite to motion.', feedback: 'Check: is the object speeding up (a along v) or slowing down (a opposite v)?' },
        { wrong: 'ΣF = m·a means the biggest force decides the acceleration.', right: 'Only the vector sum of all forces matters. Large forces that cancel produce no acceleration.', feedback: 'List every force with a sign before adding.' },
      ],
      visual: { kind: 'fbd', title: 'Free-body diagram: the car in the worked example', forces: [{ label: 'Drive 3600 N', dir: 0, mag: 3600, color: 'good' }, { label: 'Resistance 1200 N', dir: 180, mag: 1200, color: 'bad' }, { label: 'Normal', dir: 90, mag: 2400, color: 'blue' }, { label: 'Weight', dir: 270, mag: 2400, color: 'blue' }], net: 'Net 2400 N →' },
      investigate: 'In the Newton’s Force Lab, keep the net force at 20 N and record the acceleration for masses of 2, 4, 6, 8, and 10 kg. Graph a against 1/m. A straight line through the origin with slope 20 N confirms a = ΣF/m.',
      mastery: [
        'I correctly find net force by adding forces with signs before using ΣF = m·a.',
        'I can predict the effect of doubling, halving, or tripling force or mass without a calculator.',
        'I convert grams to kilograms and check that N/kg gives m/s².',
        'I can explain why acceleration points along the net force, using a braking example.',
      ],
      honors: {
        prompt: 'A 2.0 kg block is pulled across a frictionless floor by a rope at 30° above the horizontal with a tension of 10 N. (a) Find its horizontal acceleration. (b) Find the normal force. (c) At what tension would the block lift off the floor, and what would its horizontal acceleration be at that moment?',
        solution: '(a) ΣFx = 10 cos30° = 8.66 N, so ax = 8.66/2.0 = 4.33 m/s². (b) ΣFy = 0: N + 10 sin30° − (2.0)(9.8) = 0 → N = 19.6 − 5.0 = 14.6 N. (c) Lift-off when N = 0: T sin30° = 19.6 N → T = 39.2 N; then ax = 39.2 cos30°/2.0 = 17.0 m/s².',
        calc: ['10 * Math.cos(P.deg(30)) / 2', '2 * 9.8 - 10 * Math.sin(P.deg(30))', '2 * 9.8 / Math.sin(P.deg(30))'],
        answers: [4.33, 14.6, 39.2],
      },
      explainKeys: ['net force (sum of all forces)', 'acceleration is proportional to net force', 'acceleration is inversely proportional to mass', 'acceleration has the same direction as the net force'],
      explainWords: [['net', 'sum', 'total', 'all forces'], ['proportional', 'double', 'twice', 'more force'], ['mass', 'heavier', 'inverse', 'less acceleration'], ['direction', 'same way', 'points']],
    },
  },
};
