"""Regression tests for defects found by the first REAL owner products (v0.4.2).
Synthetic fixtures only - no owner content is stored in the repository."""
import sys, tempfile, unittest, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
from academic import verify_item, extract_source_items, CORRECT, INCORRECT, UNSUPPORTED, PARSE_ERROR
from browsertest import playwright_available, run_browser_tests, browser_checks


class AnswerKeyFormats(unittest.TestCase):
    def test_q_a_keys_in_nested_json_data(self):
        js = '''const AREAS = [{"id": "x", "testMe": {"foundation": [
            {"q": "Solve: 5x + 7 = 42", "a": "x = 7", "explain": "..."},
            {"q": "Solve: 2x + 1 = 9", "a": "x = 5", "explain": "..."}]},
            "cheatSheet": {"a": 1, "b": 2}}];'''
        items = extract_source_items('tool.html', js)
        self.assertEqual([i['question'] for i in items], ['Solve: 5x + 7 = 42', 'Solve: 2x + 1 = 9'])
        self.assertEqual([verify_item(i)['status'] for i in items], [CORRECT, INCORRECT])

    def test_proof_items_are_never_dropped(self):
        js = '{"q": "Prove that the sum of two even numbers is even.", "a": "2m + 2n = 2(m + n)"}'
        items = extract_source_items('t.html', js)
        self.assertEqual(len(items), 1, 'a real question/answer pair must reach the owner review list')
        self.assertEqual(verify_item(items[0])['status'], UNSUPPORTED)

    def test_method_phrases_are_not_mathematics(self):
        for q, a in [('Solve x² − 11x + 24 = 0 by factoring.', 'x = 3 or x = 8'),
                     ('Solve 2x² − 3x − 2 = 0 using the quadratic formula.', 'x = 2 or x = −1/2'),
                     ('Solve x² = 49 using the square root method.', 'x = ±7'),
                     ('Solve x² + 6x + 2 = 0 by completing the square.', 'x = −3 ± √7')]:
            with self.subTest(q=q):
                self.assertEqual(verify_item({'question': q, 'answer': a})['status'], CORRECT)
        self.assertEqual(verify_item({'question': 'Solve x² = 49 using the square root method.',
                                      'answer': 'x = 7'})['status'], INCORRECT, 'missing the negative root')

    def test_alternative_form_in_parentheses(self):
        self.assertEqual(verify_item({'question': 'Simplify: (3^2)^2', 'answer': '81 (or 3^4)'})['status'], CORRECT)

    def test_prose_questions_are_unsupported_not_parse_errors(self):
        for q in ('Find the slope of the line through (2, 3) and (6, 11).',
                  'Write 0.0062 in scientific notation.',
                  'Explain why adding two equations of a system keeps its solutions.'):
            self.assertEqual(verify_item({'question': q, 'answer': 'anything'})['status'], UNSUPPORTED, q)
        self.assertEqual(verify_item({'question': 'What is 9^9^9', 'answer': '1'})['status'], PARSE_ERROR,
                         'hostile input must still be reported as rejected')


class PageSizes(unittest.TestCase):
    def test_sub_point_size_differences_are_not_flagged(self):
        import pymupdf as fitz, pdftools
        with tempfile.TemporaryDirectory() as t:
            d = fitz.open()
            d.new_page(width=1254, height=706)
            d.new_page(width=1253.4, height=706)
            d.new_page(width=1254, height=706)
            d.save(Path(t) / 'a.pdf')
            _, f, _ = pdftools.inspect_pdf(Path(t) / 'a.pdf')
            self.assertNotIn('pdf.page_sizes', [x['check'] for x in f])
            d = fitz.open()
            d.new_page(width=612, height=792)
            d.new_page(width=1254, height=706)
            d.save(Path(t) / 'b.pdf')
            _, f, _ = pdftools.inspect_pdf(Path(t) / 'b.pdf')
            self.assertIn('pdf.page_sizes', [x['check'] for x in f])


SPA = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport"
content="width=device-width, initial-scale=1"><title>SPA</title></head><body><div id="app"></div><script>
function cover(){ return '<button onclick="location.hash=\\'#/home\\'">Enter</button>'; }
function home(){ return '<a href="#/area/one">One</a> <a href="#/area/two">Two</a>'; }
function area(id){ return '<h2>'+id+'</h2><button onclick="check(\\''+id+'\\')">Check</button>'; }
function check(id){ if(id==='two'){ undefinedScoreTable.total += 1; } }
function route(){ const h=location.hash||'#/cover'; const p=h.replace('#/','').split('/');
  const app=document.getElementById('app');
  app.innerHTML = p[0]==='home' ? home() : p[0]==='area' ? area(p[1]) : cover(); }
window.addEventListener('hashchange', route); window.addEventListener('DOMContentLoaded', route);
</script></body></html>"""


@unittest.skipUnless(playwright_available(), 'Chromium not installed')
class SinglePageAppCrawl(unittest.TestCase):
    def test_bug_on_an_inner_screen_is_found(self):
        with tempfile.TemporaryDirectory() as t:
            site = Path(t) / 'site'
            site.mkdir()
            (site / 'index.html').write_text(SPA, encoding='utf-8')
            r = run_browser_tests(site, 'index.html', Path(t) / 'shots', 'spa')
            self.assertGreaterEqual(len(r['routes_visited']), 4, r['routes_visited'])
            self.assertTrue(any('undefinedScoreTable' in e['message'] and '#/area/two' in e['after'] for e in r['errors']),
                            r['errors'])
            checks = {c[0]: c[3] for c in browser_checks(r)}
            self.assertFalse(checks['browser.no_js_exceptions'])
            self.assertTrue(checks['browser.all_screens_visited'])


if __name__ == '__main__':
    unittest.main()
