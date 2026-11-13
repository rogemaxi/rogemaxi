"""Concept Tiles in the owner-approved ByrdWay format: build + independent design/academic QA (neutral sample content)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import byrdway_tiles as bt  # noqa: E402
import imageread  # noqa: E402


def tile(title, a, b):
    ex = lambda p, s, ans, m, t: {'problem': p, 'steps': s, 'answer': ans,
                                  'verify': {'type': 'physics', 'formula': 'd = v*t', 'given': {'v': m, 't': t}, 'find': 'd'}}
    return {'title': title, 'key': 'd = v t', 'meaning': 'Distance at constant speed is speed times time.',
            'picture': 'Each second adds the same distance.',
            'examples': [ex(f'A cart moves at {a} m/s for 2 s. How far?', [f'd = {a} × 2 = {2 * a}'], f'{2 * a} m', f'{a} m/s', '2 s'),
                         ex(f'A cart moves at {b} m/s for 3 s. How far?', [f'd = {b} × 3 = {3 * b}'], f'{3 * b} m', f'{b} m/s', '3 s')],
            'practice': {'question': f'A bike moves at {a} m/s for 4 s. How far?', 'answer': f'{4 * a} m',
                         'verify': {'type': 'physics', 'formula': 'd = v*t', 'given': {'v': f'{a} m/s', 't': '4 s'}, 'find': 'd'}},
            'misconception': {'incorrect': 'Add speed and time.', 'correct': 'Multiply speed by time.'},
            'teach_back': 'Explain why the units multiply to meters.', 'byrd_says': 'Speed times time!',
            'diagram': {'type': 'boxes', 'boxes': ['v', 'x t', 'd'], 'links': ['multiply', '']}}


TOC = [{'unit': 1, 'title': 'Sample Motion', 'tiles': [{'title': 'Constant speed', 'honors': False},
                                                        {'title': 'Distance from speed', 'honors': False}]}]


def extra(n):
    return [{'question': f'A car moves at {k} m/s for 5 s. How far?', 'answer': f'{5 * k} m',
             'verify': {'type': 'physics', 'formula': 'd = v*t', 'given': {'v': f'{k} m/s', 't': '5 s'}, 'find': 'd'}}
            for k in range(1, n + 1)]


class ByrdWayFormat(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_builds_in_the_approved_layout_and_passes_independent_qa(self):
        content = {1: {'tiles': [tile('Constant speed', 2, 3), tile('Distance from speed', 4, 5)], 'extra': extra(10)}}
        rep = bt.build_product(TOC, content, self.d / 'out.pdf', 'Sample Course')
        self.assertEqual(rep['failed'], 0, rep['failures'])
        self.assertEqual(rep['pages'], 2 + 2 + 5)
        with imageread._fitz().open(rep['pdf']) as doc:
            self.assertEqual((doc[3].rect.width, doc[3].rect.height), (792, 612))
            self.assertTrue(all('Kalam' in f[3] for f in doc[3].get_fonts() if 'Kalam' in f[3] or 'Helv' not in f[3]))
            names = {s['text'].strip() for b in doc[3].get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans']}
            for heading in ('1. Meaning and why it works', '2. Picture the reasoning', '3. Worked examples | explain each move',
                            '4. Practice and check', '5. Misconception / teach back'):
                self.assertIn(heading, names)

    def test_missing_tile_wrong_answer_and_short_practice_are_caught(self):
        bad = tile('Distance from speed', 4, 5)
        bad['examples'][0]['answer'] = '9 m'                                   # 4 m/s x 2 s = 8 m
        rep = bt.build_product(TOC, {1: {'tiles': [tile('Constant speed', 2, 3), bad], 'extra': extra(4)}},
                               self.d / 'bad.pdf', 'Sample Course')
        f = ' '.join(x[0] for x in rep['failures'])
        self.assertIn('u1.academic.tile2.example1', f)
        self.assertIn('u1.practice.twelve_problems', f)
        rep2 = bt.build_product(TOC, {1: {'tiles': [tile('Constant speed', 2, 3)], 'extra': extra(10)}}, self.d / 'm.pdf', 'S')
        self.assertIn('u1.structure.tile_count', ' '.join(x[0] for x in rep2['failures']))
        self.assertTrue(rep2['decision'].startswith('FAIL'))

    def test_conformance_detects_a_redesign(self):
        content = {1: {'tiles': [tile('Constant speed', 2, 3), tile('Distance from speed', 4, 5)], 'extra': extra(10)}}
        rep = bt.build_product(TOC, content, self.d / 'out.pdf', 'Sample Course')
        fitz = imageread._fitz()
        with fitz.open(rep['pdf']) as doc:                       # tamper: recolour one lesson card
            doc[3].draw_rect(fitz.Rect(28, 88, 388, 233), color=None, fill=(1, 1, 1))
            doc.save(self.d / 'tampered.pdf')
        res = {c[0]: c[1] for c in bt.conformance(self.d / 'tampered.pdf', [(4, 'lesson')])}
        self.assertTrue(res['design.p4.landscape_letter'])
        self.assertTrue(res['design.p4.lesson_cards_match_reference'])   # original card still present underneath ...
        with fitz.open(rep['pdf']) as doc:
            doc.delete_page(3)
            doc.insert_page(3, width=612, height=792)               # ... but a portrait page is caught
            doc.save(self.d / 'portrait.pdf')
        res = {c[0]: c[1] for c in bt.conformance(self.d / 'portrait.pdf', [(4, 'lesson')])}
        self.assertFalse(res['design.p4.landscape_letter'])
        self.assertFalse(res['design.p4.lesson_cards_match_reference'])


if __name__ == '__main__':
    unittest.main()
