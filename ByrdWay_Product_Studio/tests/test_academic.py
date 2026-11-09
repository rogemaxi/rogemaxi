"""Milestone D: independent academic verification (algebra, geometry, calculus,
statistics, physics), unsupported-domain flags, and hostile-input rejection."""
import unittest, warnings
warnings.filterwarnings('ignore')
from academic import (verify_item, extract_arithmetic_claims, extract_source_items, repair_for_item,
                      CORRECT, INCORRECT, UNSUPPORTED, PARSE_ERROR)

PHYS_F = {'type': 'physics', 'formula': 'F = m*a', 'given': {'m': '5 kg', 'a': '9.8 m/s^2'}, 'find': 'F'}
CASES = [
    ('What is 7 × 8?', '56', None, CORRECT), ('What is 7 × 8?', '54', None, INCORRECT),
    ('Compute 3/4 + 1/8', '7/8', None, CORRECT), ('Compute 3/4 + 1/8', '0.875', None, CORRECT),
    ('Evaluate sin(30°)', '1/2', None, CORRECT), ('Evaluate √2', '1.41', None, CORRECT),
    ('Evaluate √2', '1.42', None, INCORRECT),
    ('Solve 2x + 3 = 11', 'x = 4', None, CORRECT), ('Solve 2x + 3 = 11', 'x = 5', None, INCORRECT),
    ('Solve x^2 - 5x + 6 = 0', 'x = 2 or x = 3', None, CORRECT),
    ('Solve x^2 - 5x + 6 = 0', 'x = 2', None, INCORRECT),           # missing root
    ('Find the derivative of x^3 + 2x', '3x^2 + 2', None, CORRECT),
    ('Find the derivative of x^3 + 2x', '3x^2 + 2x', None, INCORRECT),
    ('Integrate 2x dx', 'x^2 + C', None, CORRECT),
    ('Integral of x^2 from 0 to 3', '9', None, CORRECT), ('Integral of x^2 from 0 to 3', '27', None, INCORRECT),
    ('lim x->0 sin(x)/x', '1', None, CORRECT),
    ('Find the mean of 2, 4, 6, 8', '5', None, CORRECT),
    ('Find the median of 3, 1, 4, 1, 5', '3', None, CORRECT),
    ('Find the sample standard deviation of 2, 4, 4, 4, 5, 5, 7, 9', '2.14', None, CORRECT),
    ('Find the population standard deviation of 2, 4, 4, 4, 5, 5, 7, 9', '2', None, CORRECT),
    ('Find the area of a circle with radius 3', '9π', None, CORRECT),
    ('Find the area of a circle with radius 3', '28.27', None, CORRECT),
    ('Find the area of a circle with radius 3', '18.85', None, INCORRECT),   # circumference confusion
    ('Find the hypotenuse of a right triangle with legs 3 and 4', '5', None, CORRECT),
    ('Simplify (x^2 - 1)/(x - 1)', 'x + 1', None, CORRECT),
    ('Force?', '49 N', PHYS_F, CORRECT),
    ('Force?', '49 kg', PHYS_F, INCORRECT),                                  # dimension error
    ('KE?', '0.25 kJ', {'type': 'physics', 'formula': 'K = m*v^2/2', 'given': {'m': '5 kg', 'v': '10 m/s'}, 'find': 'K'}, CORRECT),
    ('Speed?', '20 m/s', {'type': 'physics', 'formula': 'v = d/t', 'given': {'d': '100 m', 't': '5 s'}, 'find': 'v'}, CORRECT),
    ('Explain photosynthesis', 'plants make sugar', None, UNSUPPORTED),
    ('What is 9^9^9', '1', None, PARSE_ERROR),                              # DoS guard
    ('Evaluate __import__("os").system("x")', '1', None, UNSUPPORTED),      # no eval
]


class TestVerifier(unittest.TestCase):
    def test_cases(self):
        for q, a, spec, expected in CASES:
            with self.subTest(q=q, a=a):
                item = {'question': q, 'answer': a}
                if spec:
                    item['verify'] = spec
                r = verify_item(item)
                self.assertEqual(r['status'], expected, r['evidence'])
                if expected == CORRECT:
                    self.assertGreaterEqual(len(r['methods']), 2, 'two independent methods required')

    def test_wrong_answer_gets_deterministic_suggestion(self):
        r = verify_item({'question': 'Solve 2x + 3 = 11', 'answer': 'x = 5'})
        self.assertEqual(r['suggested_answer'], 'x = 4')
        self.assertEqual(verify_item({'question': 'What is 7 × 8?', 'answer': r'54'})['suggested_answer'], '56')

    def test_multiple_choice_index(self):
        r = verify_item({'question': 'Which is 6×7?', 'choices': ['36', '42', '48'], 'correct': 0})
        self.assertEqual(r['status'], INCORRECT)
        self.assertEqual(r['correct_choice_index'], 1)

    def test_no_answer_is_parse_error(self):
        self.assertEqual(verify_item({'question': 'What is 2+2?', 'answer': ''})['status'], PARSE_ERROR)

    def test_extract_claims_from_text(self):
        claims = extract_arithmetic_claims('Check: 7 × 8 = 54. Also 12 + 5 = 17 and 3x = 9.')
        self.assertEqual([c['answer'] for c in claims], ['54', '17'])
        self.assertEqual(verify_item(claims[0])['status'], INCORRECT)
        self.assertEqual(verify_item(claims[1])['status'], CORRECT)

    def test_source_item_extraction_and_repair_patch(self):
        js = 'const items = [{q: "What is 7 × 8?", answer: "54"}, {q: "Solve 2x + 3 = 11", answer: "x = 4"}];'
        items = extract_source_items('quiz.js', js)
        self.assertEqual(len(items), 2)
        r = verify_item(items[0])
        patch = repair_for_item(items[0], r)
        self.assertEqual(js.count(patch['find']), 1)
        fixed = js.replace(patch['find'], patch['replace'])
        self.assertIn('answer: "56"', fixed)
        again = extract_source_items('quiz.js', fixed)
        self.assertTrue(all(verify_item(i)['status'] == CORRECT for i in again))

    def test_mcq_index_repair(self):
        js = '{question: "What is 6 × 7?", choices: ["36", "42", "48"], correct: 0}'
        it = extract_source_items('q.js', js)[0]
        p = repair_for_item(it, verify_item(it))
        self.assertIn('correct: 1', p['replace'])

    def test_html_data_attribute_items(self):
        html = '<div class="q" data-question="What is 9 + 10?" data-answer="21"></div>'
        it = extract_source_items('a.html', html)[0]
        r = verify_item(it)
        self.assertEqual(r['status'], INCORRECT)
        self.assertIn('data-answer="19"', repair_for_item(it, r)['replace'])


if __name__ == '__main__':
    unittest.main()
