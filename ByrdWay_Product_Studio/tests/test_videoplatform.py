"""Media Division: video platform brief, Blotato client (simulated server), review, approval-gated publishing."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commercial  # noqa: E402,F401  (puts the bundled ffmpeg on PATH)
import videoplatform as vp  # noqa: E402

PRODUCT = {'title': 'College Statistics Visual Guide', 'destination_url': 'https://www.teacherspayteachers.com/Product/x-1',
           'destination_label': 'Teachers Pay Teachers', 'destination_verified': True}
LINES = [{'beat': 'hook', 'voice': 'College statistics stressing you out?', 'shot': 'Lil Dr. Byrd points at camera'},
         {'beat': 'problem', 'voice': 'Z-scores, hypothesis testing, regression.', 'shot': 'formulas swirl around him'},
         {'beat': 'demo', 'voice': 'I walk you through every step, picture by picture.', 'shot': 'he flips through the guide'},
         {'beat': 'cta', 'voice': 'ByrdWay Anime Explainers. Get it on Teachers Pay Teachers.', 'shot': 'he holds up the guide'}]


class FakeBlotato:
    """Records every request; answers like the documented Blotato REST API."""
    def __init__(self, accounts=None, visual_states=('queueing', 'generating-media', 'done'), post_states=('in-progress', 'published')):
        self.calls = []
        self.accounts = accounts if accounts is not None else [
            {'id': '1', 'platform': 'facebook', 'fullname': 'Roge Byrd', 'username': 'roge.byrd'},
            {'id': '2', 'platform': 'instagram', 'fullname': 'ByrdWay', 'username': 'fractionsaremyfriends1'},
            {'id': '3', 'platform': 'tiktok', 'fullname': 'ByrdWay', 'username': 'z29experience'},
            {'id': '4', 'platform': 'youtube', 'fullname': 'ByrdWay', 'username': 'byrdway'}]
        self.vs, self.ps = list(visual_states), {}
        self.post_states = post_states
        self.n = 0

    def __call__(self, method, url, headers, body):
        js = json.loads(body) if body and method != 'PUT' else None
        self.calls.append((method, url, headers, js))
        if method == 'PUT':
            return 200, b''
        if 'blotato-api-key' not in headers:
            return 401, b'{}'
        path = url.split('/v2', 1)[1]
        if path.startswith('/users/me/accounts/1/subaccounts'):
            return 200, json.dumps({'items': [{'id': '555', 'accountId': '1', 'name': 'ByrdWay Page'}]}).encode()
        if path.startswith('/users/me/accounts'):
            return 200, json.dumps({'items': self.accounts}).encode()
        if path == '/media/uploads':
            return 201, json.dumps({'presignedUrl': 'https://upload.example/put', 'publicUrl': 'https://cdn.example/' + js['filename']}).encode()
        if path.startswith('/videos/templates'):
            return 200, json.dumps({'items': [{'id': 'x', 'inputs': {'characterImage': {'type': 'string'}}}]}).encode()
        if path == '/videos/from-templates':
            return 201, b'{"item": {"id": "vid-1", "status": "queueing"}}'
        if path.startswith('/videos/creations/'):
            st = self.vs.pop(0) if len(self.vs) > 1 else self.vs[0]
            return 200, json.dumps({'item': dict({'id': 'vid-1', 'status': st}, **({'mediaUrl': 'https://cdn.example/v.mp4'} if st == 'done' else {}))}).encode()
        if path == '/posts':
            self.n += 1
            sid = f'sub-{self.n}'
            self.ps[sid] = list(self.post_states)
            return 201, json.dumps({'postSubmissionId': sid}).encode()
        if path.startswith('/posts/'):
            sid = path.rsplit('/', 1)[1]
            st = self.ps[sid].pop(0) if len(self.ps[sid]) > 1 else self.ps[sid][0]
            return 200, json.dumps({'postSubmissionId': sid, 'status': st, 'publicUrl': f'https://social.example/{sid}' if st == 'published' else None}).encode()
        return 404, b'{"message": "not found"}'


def client(fake):
    return vp.Blotato(key='k', http=fake, sleep=lambda s: None)


class BriefTests(unittest.TestCase):
    def test_brief_ready_with_character_and_all_beats(self):
        b = vp.brief(PRODUCT, LINES, 30, 'google_flow')
        self.assertTrue(b['ready'], b['problems'])
        self.assertEqual([s['beat'] for s in b['shots']], ['hook', 'problem', 'demo', 'cta'])
        self.assertTrue(all('BYRDWAY MATHEMATICS AND SCIENCE' in s['prompt'] for s in b['shots']))
        self.assertTrue(all(s['clips_needed'] == 1 for s in b['shots']))      # 7.5 s per shot -> one 8 s Flow clip
        self.assertIn('labs.google', vp.brief_text(b))

    def test_brief_rejects_bad_length_missing_cta_unverified_destination(self):
        with self.assertRaises(ValueError):
            vp.brief(PRODUCT, LINES, 60)
        b = vp.brief(dict(PRODUCT, destination_verified=False), LINES[:3], 30)
        self.assertFalse(b['ready'])
        self.assertTrue(any('cta' in p for p in b['problems']))
        self.assertTrue(any('not verified' in p for p in b['problems']))


class BlotatoTests(unittest.TestCase):
    def test_accounts_and_facebook_pages(self):
        f = FakeBlotato()
        r = vp.platform_setup_check(client(f))
        self.assertTrue(all(r[p]['connected'] for p in vp.CHANNELS))
        self.assertEqual(r['facebook']['pages'][0]['id'], '555')
        self.assertEqual(f.calls[0][2]['blotato-api-key'], 'k')
        self.assertTrue(f.calls[0][1].startswith('https://backend.blotato.com/v2/users/me/accounts'))

    def test_missing_key_and_401(self):
        orig = vp.get_key
        vp.get_key = lambda: ''
        try:
            with self.assertRaises(vp.BlotatoError):
                vp.Blotato(http=FakeBlotato())
        finally:
            vp.get_key = orig
        bad = vp.Blotato(key='k', http=lambda *a: (401, b'{}'))
        with self.assertRaises(vp.BlotatoError) as e:
            bad.accounts()
        self.assertIn('401', str(e.exception))

    def test_generation_needs_owner_confirmation_then_polls_to_done(self):
        f = FakeBlotato()
        b = vp.brief(PRODUCT, LINES, 30)
        with self.assertRaises(vp.BlotatoError):
            vp.produce_on_blotato(client(f), b, owner_confirmed=False)
        self.assertFalse(any(c[1].endswith('/videos/from-templates') for c in f.calls))   # nothing paid was sent
        job = vp.produce_on_blotato(client(f), b, owner_confirmed=True, character_url='https://cdn.example/ldb.png')
        sent = [c for c in f.calls if c[1].endswith('/videos/from-templates')][0][3]
        self.assertEqual(sent['templateId'], vp.PLATFORMS['blotato']['templates']['character'])
        self.assertEqual(sent['inputs']['characterDescription'], 'https://cdn.example/ldb.png')
        self.assertEqual(sent['inputs']['aspectRatio'], '9:16')
        self.assertEqual([sc['narration'] for sc in sent['inputs']['scenes']], [l['voice'] for l in LINES])
        self.assertNotIn('BYRDWAY MATHEMATICS', sent['inputs']['scenes'][0]['description'])   # character comes from the image
        self.assertNotIn('prompt', sent)
        self.assertTrue(sent['render'])
        res = client(f).wait_visual(job['visual_id'])
        self.assertEqual(res, {'id': 'vid-1', 'status': 'done', 'mediaUrl': 'https://cdn.example/v.mp4'})

    def test_generation_failure_is_reported_not_retried(self):
        f = FakeBlotato(visual_states=('insufficient-credits',))
        res = client(f).wait_visual('vid-1')
        self.assertEqual(res['error'], 'insufficient-credits')
        self.assertEqual(sum(1 for c in f.calls if '/videos/from-templates' in c[1]), 0)

    def test_publish_gate_and_per_platform_bodies(self):
        f = FakeBlotato()
        c = client(f)
        with self.assertRaises(vp.BlotatoError):
            vp.publish(c, 'https://cdn.example/v.mp4', PRODUCT, ['tiktok'], {'owner': 'R', 'explicit': True, 'qa_decision': 'FAIL - back to repair'})
        with self.assertRaises(vp.BlotatoError):
            vp.publish(c, 'https://cdn.example/v.mp4', PRODUCT, ['tiktok'], {'owner': 'R', 'explicit': False, 'qa_decision': 'PASS'})
        self.assertFalse(any(c_[1].endswith('/posts') for c_ in f.calls))
        out = vp.publish(c, 'https://cdn.example/v.mp4', PRODUCT, list(vp.CHANNELS),
                         {'owner': 'Dr. Byrd', 'explicit': True, 'qa_decision': 'PASS - awaiting owner approval to publish'})
        self.assertEqual({r['platform']: r['status'] for r in out['results']}, {p: 'published' for p in vp.CHANNELS})
        bodies = {c_[3]['post']['content']['platform']: c_[3] for c_ in f.calls if c_[1].endswith('/v2/posts')}
        self.assertEqual(bodies['facebook']['post']['target'], {'targetType': 'facebook', 'pageId': '555', 'mediaType': 'reel'})
        self.assertEqual(bodies['tiktok']['post']['target']['privacyLevel'], 'PUBLIC_TO_EVERYONE')
        self.assertTrue(bodies['tiktok']['post']['target']['isAiGenerated'])
        self.assertEqual(bodies['youtube']['post']['target']['privacyStatus'], 'public')
        for p, bd in bodies.items():
            self.assertEqual(bd['post']['content']['platform'], bd['post']['target']['targetType'])
            self.assertEqual(bd['post']['content']['mediaUrls'], ['https://cdn.example/v.mp4'])
            self.assertIn(PRODUCT['destination_url'], bd['post']['content']['text'])

    def test_first_post_override_only_when_audience_caps_are_the_only_gap(self):
        f = FakeBlotato()
        ap = {'owner': 'R', 'explicit': True, 'qa_decision': 'FAIL - back to repair', 'first_post_override': True, 'data_capped_only': False}
        with self.assertRaises(vp.BlotatoError):
            vp.publish(client(f), 'https://cdn.example/v.mp4', PRODUCT, ['youtube'], ap)
        out = vp.publish(client(f), 'https://cdn.example/v.mp4', PRODUCT, ['youtube'], dict(ap, data_capped_only=True))
        self.assertEqual(out['results'][0]['status'], 'published')

    def test_unconnected_platform_and_local_upload(self):
        f = FakeBlotato(accounts=[{'id': '3', 'platform': 'tiktok', 'fullname': 'B', 'username': 'z'}])
        with tempfile.TemporaryDirectory() as d:
            mp4 = Path(d) / 'ad.mp4'
            mp4.write_bytes(b'\x00' * 10)
            out = vp.publish(client(f), str(mp4), PRODUCT, ['tiktok', 'instagram'],
                             {'owner': 'R', 'explicit': True, 'qa_decision': 'PASS'})
        self.assertEqual(out['media_url'], 'https://cdn.example/ad.mp4')
        self.assertTrue(any(c[0] == 'PUT' for c in f.calls))
        st = {r['platform']: r['status'] for r in out['results']}
        self.assertEqual(st, {'tiktok': 'published', 'instagram': 'not connected in Blotato'})


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg not installed')
class ReviewTests(unittest.TestCase):
    def test_review_watches_render_and_blocks_generic_voice_then_dub(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            mp4, voice = d / 'v.mp4', d / 'voice.wav'
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1080x1920:rate=30:duration=30',
                            '-f', 'lavfi', '-i', 'sine=frequency=220:duration=30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', '-shortest', str(mp4)], check=True)
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=180:duration=30', str(voice)], check=True)
            b = vp.brief(PRODUCT, LINES, 30)
            r = vp.review(mp4, b, root=None, ai_voice=True)
            self.assertTrue(r['score']['decision'].startswith('BLOCKED'))
            self.assertAlmostEqual(r['review']['duration_s'], 30, delta=0.3)
            out = vp.dub_with_voice(mp4, voice, d / 'dub.mp4')
            self.assertTrue(Path(out).stat().st_size > 1000)


if __name__ == '__main__':
    unittest.main()
