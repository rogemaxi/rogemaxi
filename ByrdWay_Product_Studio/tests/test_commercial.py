"""30-second commercial QA: timing, caption sync, glyph/truncation checks, voice standard and the release gate."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import commercial as C  # noqa: E402

PRODUCT = {'title': 'Sample Product', 'course': 'Physics', 'hook': 'One idea per tile.', 'problem': 'Students freeze at force problems.',
           'demo_lines': ['Each tile shows a worked example.', 'Then practice with an answer key.'], 'cta': 'Search ByrdWay on TpT.',
           'destination_label': 'TpT', 'destination_verified': True, 'demo_from_real_product': True, 'demo_verified': True}
GOOD_REVIEW = {'duration_s': 30.0, 'size': (1080, 1920), 'audio_stream': True, 'loudness_lufs': -14.0, 'silent_gaps_s': [],
               'longest_static_s': 0.0, 'footer_readable_ratio': 1.0, 'text_outside_safe_zone': [],
               'caption_readable_ratio': {'hook': 1.0, 'problem': 1.0, 'demo': 1.0, 'cta': 1.0}}


class Commercial(unittest.TestCase):
    def test_four_beats_cover_exactly_30_seconds(self):
        b = C.script(PRODUCT)
        self.assertEqual([x['beat'] for x in b], ['hook', 'problem', 'demo', 'cta'])
        self.assertEqual((b[0]['t0'], b[0]['t1'], b[1]['t1'], b[2]['t1'], b[3]['t1']), (0.0, 3.0, 10.0, 22.0, 30.0))
        self.assertIn('Sample Product', b[3]['caption'])

    def test_captions_follow_the_narration_sentence_by_sentence(self):
        demo = C.script(PRODUCT)[2]
        self.assertEqual(C.caption_at(demo, 10.1), 'Each tile shows a worked example.')
        self.assertEqual(C.caption_at(demo, 21.9), 'Then practice with an answer key.')

    def test_no_approved_voice_means_blocked_never_a_substitute(self):
        sc = C.score(PRODUCT, C.script(PRODUCT), dict(GOOD_REVIEW, audio_stream=False), 'NONE', voice_check=None,
                     render_info={'min_product_text_px': 56})
        self.assertTrue(sc['decision'].startswith('BLOCKED'))
        self.assertEqual(sc['scores']['audio'], 0)
        self.assertIn('NOT LOCATED', ' '.join(sc['repair_list']))
        self.assertIsNone(C.approved_voice(tempfile.mkdtemp()))
        src = Path(C.__file__).read_text(encoding='utf-8')
        self.assertNotIn('espeak', src.split('LIL DR. BYRD VOICE STANDARD')[1].split('VOICE_ASSET_ID')[1])

    def test_every_category_must_reach_nine(self):
        sc = C.score(PRODUCT, C.script(PRODUCT), GOOD_REVIEW, 'approved Lil Dr. Byrd voice recording',
                     voice_check={'match': True}, render_info={'min_product_text_px': 56})
        self.assertFalse(sc['decision'].startswith('PASS'))           # still-image visuals are capped below 9
        self.assertIn('visual', ' '.join(sc['repair_list']))
        self.assertEqual(set(sc['scores']), set(C.CATEGORIES))
        self.assertTrue(all(sc['platform_fit'].values()))

    def test_cut_off_text_missing_glyphs_and_tiny_product_text_are_caught(self):
        b = C.script(PRODUCT)
        sc = C.score(PRODUCT, b, GOOD_REVIEW, 'approved', voice_check={'match': True},
                     render_info={'truncated_text': ['Then practice'], 'missing_glyphs': ['✓'], 'min_product_text_px': 12})
        self.assertLess(sc['scores']['clarity'], 9)
        self.assertLess(sc['scores']['product_demo'], 9)
        C.MISSING.clear()
        C._check_glyphs('15 N ✓')
        self.assertIn('✓', C.MISSING)

    def test_unverified_destination_caps_the_cta(self):
        sc = C.score(dict(PRODUCT, destination_verified=False), C.script(PRODUCT), GOOD_REVIEW, 'approved',
                     voice_check={'match': True}, render_info={'min_product_text_px': 56})
        self.assertLess(sc['scores']['cta'], 9)

    def test_owner_script_is_stored_verbatim(self):
        s = C.OWNER_SCRIPTS['college_statistics_anime_explainers']
        self.assertEqual(s['hook'], 'College statistics stressing you out?')
        self.assertIn('Z-scores', s['problem'])


if __name__ == '__main__':
    unittest.main()
