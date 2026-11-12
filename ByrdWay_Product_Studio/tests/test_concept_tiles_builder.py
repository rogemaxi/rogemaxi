"""Concept Tiles construction loop: approved TOC -> build -> independent QA -> back to the builder on failure.
Neutral sample content only (no owner product content)."""
import copy, sys, tempfile, unittest, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
import concepttiles as CT

TOC_MD = "| 1 Sample Unit | Speed basics · (H) Average speed |\n"


def _tile(title, honors, d, t, ans):
    return {"title": title, "honors": honors, "key": "v = d/t",
            "meaning": "Speed is distance covered per unit time.", "picture": "A car covering equal distances each second.",
            "byrd_says": "Divide the distance by the time!",
            "diagram": {"type": "graph", "x_label": "t (s)", "y_label": "x (m)", "points": [[0, 0], [t, d]]},
            "examples": [{"problem": f"A cart goes {d} m in {t} s. Find its speed.", "steps": [f"v = {d} / {t}"], "answer": ans,
                          "verify": {"type": "physics", "formula": "v = d/t", "given": {"d": f"{d} m", "t": f"{t} s"}, "find": "v"}},
                         {"problem": "A bike goes 30 m in 6 s. Find its speed.", "steps": ["v = 30 / 6"], "answer": "5 m/s",
                          "verify": {"type": "physics", "formula": "v = d/t", "given": {"d": "30 m", "t": "6 s"}, "find": "v"}}],
            "practice": {"question": "A runner covers 100 m in 20 s. Find the speed.", "answer": "5 m/s",
                         "verify": {"type": "physics", "formula": "v = d/t", "given": {"d": "100 m", "t": "20 s"}, "find": "v"}},
            "misconception": {"incorrect": "Speed is distance times time.", "correct": "Speed is distance divided by time."},
            "teach_back": "Explain why speed has units of meters per second.",
            **({"honors_reasoning": "Average speed over a trip is total distance divided by total time."} if honors else {})}


class Builder(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        from PIL import Image
        Image.new('RGB', (60, 60), (30, 60, 140)).save(self.d / 'mascot.png')
        self.toc = CT.toc_from_blueprint_md(TOC_MD)[0]
        self.good = [_tile("Speed basics", False, 20, 4, "5 m/s"), _tile("Average speed", True, 50, 10, "5 m/s")]

    def tearDown(self):
        self.t.cleanup()

    def build(self, tiles):
        return CT.build_unit(self.toc, tiles, self.d / 'mascot.png', self.d / 'out')

    def test_correct_unit_passes_every_mandatory_check(self):
        r = self.build(self.good)
        self.assertEqual(r['decision'], 'PASS', r['failures'])
        self.assertTrue(Path(r['pdf']).exists())

    def test_wrong_answer_goes_back_to_the_builder(self):
        bad = copy.deepcopy(self.good)
        bad[0]['examples'][0]['answer'] = '6 m/s'
        r = self.build(bad)
        self.assertTrue(any(f['check'] == 'academic.tile1.example1' for f in r['failures']), r['failures'])

    def test_toc_cannot_be_changed_shortened_or_missing_honors(self):
        r = self.build(self.good[:1])
        self.assertTrue(any(f['check'] == 'structure.tile_count' for f in r['failures']))
        renamed = copy.deepcopy(self.good)
        renamed[1]['title'] = 'Something else'
        self.assertTrue(any('title' in f['check'] for f in self.build(renamed)['failures']))
        no_h = copy.deepcopy(self.good)
        del no_h[1]['honors_reasoning']
        self.assertTrue(any(f['check'].endswith('honors_section') for f in self.build(no_h)['failures']))

    def test_premium_requirements_are_mandatory(self):
        t = copy.deepcopy(self.good)
        del t[0]['diagram']
        t[0]['examples'] = t[0]['examples'][:1]
        del t[0]['byrd_says']
        names = {f['check'].split('.')[-1] for f in self.build(t)['failures']}
        self.assertTrue({'diagram', 'two_worked_examples', 'lil_dr_byrd_tip'} <= names, names)

    def test_built_pages_are_reread_by_the_inspection_checks(self):
        t = copy.deepcopy(self.good)
        t[0]['examples'][0]['steps'] = ['v = 20 / 4', '= 6']          # a wrong worked step printed on the page
        r = self.build(t)
        self.assertTrue(any(f['check'] == 'lessons.tile1.worked_steps_and_arithmetic' for f in r['failures']), r['failures'])
        t = copy.deepcopy(self.good)
        t[0]['examples'][0]['steps'] = ['v = (20 / 4']
        self.assertTrue(any(f['check'].endswith('brackets_balanced') for f in self.build(t)['failures']))


if __name__ == '__main__':
    unittest.main()
