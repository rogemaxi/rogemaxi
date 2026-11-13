"""Exact Algebra 1 checks: each form accepts the right answer and rejects a wrong one."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import academic  # noqa: E402

CASES = [  # question, correct answer, wrong answer
    ('Solve the inequality: −3x + 7 ≤ 22', 'x ≥ −5', 'x ≤ −5'),
    ('Solve the compound inequality: −5 < 2x − 1 ≤ 9', '−2 < x ≤ 5', '−2 ≤ x ≤ 5'),
    ('Solve the absolute value inequality: |3x − 6| > 9', 'x > 5 or x < −1', 'x > 5'),
    ('Factor completely: x^2-x-12', '(x-4)(x+3)', '(x+4)(x-3)'),
    ('Factor completely: 2x^3-8x', '2x(x-2)(x+2)', '2x(x^2-4)'),
    ('Factor completely over the integers, or state that it is prime: x^2+4x+8', 'Prime over the integers.', '(x+2)(x+4)'),
    ('Multiply using FOIL: (x+6)(x-2)', 'x^2+4x-12', 'x^2-4x-12'),
    ('Solve by elimination: 3x + y = 9 and x + 2y = 8.', '(2, 3)', '(3, 2)'),
    ('Find the slope of the line through (1, 4) and (5, 12).', 'm = 2', 'm = 1/2'),
    ('Write the equation, in slope-intercept form, of the line through (4, -1) with slope 1/2.', 'y = (1/2)x - 3', 'y = (1/2)x - 1'),
    ('Find the equation of the line parallel to y = 4x + 7 that passes through (2, 5).', 'y = 4x - 3', 'y = 4x + 3'),
    ('Evaluate f(x) = 5x - 2 at x = 4.', '18', '22'),
    ('If f(x) = 2x - 5, find f(3).', 'f(3) = 1.', 'f(3) = -1.'),
    ('Find the average rate of change of f(x) = x² + 1 from x = 0 to x = 3.', '3.', '9.'),
    ('Find the vertex of y=3x²-12x+7 using h=-b/2a and k=f(h).', 'Vertex (2,-5)', 'Vertex (-2,-5)'),
    ('Find the vertex of f(x) = 3|x + 2| - 7.', '(-2, -7)', '(2, -7)'),
    ('Find the axis of symmetry for y=(x-7)(x+1).', 'x = 3', 'x = -3'),
    ('Write 0.00047 in scientific notation.', '4.7 × 10^-4', '47 × 10^-5'),
    ('Simplify fully using only positive exponents: (2x^-3y^2) / (4x^2y^-5)', 'y^7 / (2x^5)', 'x^-5 y^7 / 2'),
    ('Quiz scores for 5 students: 82, 76, 90, 88, 74. Find the mean.', '82', '80'),
    ('Find the mode and the range of: 5, 8, 5, 9, 5, 12, 8', 'Mode = 5, Range = 7', 'Mode = 8, Range = 7'),
]


class Algebra1(unittest.TestCase):
    def test_right_answers_verify_and_wrong_answers_are_caught(self):
        for q, good, bad in CASES:
            with self.subTest(q=q):
                self.assertEqual(academic.verify_item({'question': q, 'answer': good})['status'], academic.CORRECT, q)
                self.assertEqual(academic.verify_item({'question': q, 'answer': bad})['status'], academic.INCORRECT, q)

    def test_open_questions_stay_with_human_review(self):
        for q in ('Prove that a^0 = 1 for a ≠ 0 using the Quotient Rule.', 'Is the relation {(1,2), (2,4), (1,5)} a function? Justify.',
                  'Derive the quadratic formula by completing the square starting from ax² + bx + c = 0.'):
            self.assertEqual(academic.verify_item({'question': q, 'answer': 'something'})['status'], academic.UNSUPPORTED)


if __name__ == '__main__':
    unittest.main()
