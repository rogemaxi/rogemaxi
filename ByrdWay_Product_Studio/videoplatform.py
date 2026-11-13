"""Media Division video platform + social publishing (Blotato) for Lil Dr. Byrd commercials.

The Studio does NOT generate the commercial itself. Its agents:
  * Script & Storyboard  -> production brief for a 30-45 s vertical commercial (hook / problem / demo / CTA)
                            with the Lil Dr. Byrd character sheet and the owner's approved voice lines;
  * Video Producer       -> sends the brief to the chosen VIDEO PLATFORM:
                              - Blotato (REST API, automated: AI video templates, credits on the owner's plan)
                              - Google Flow / Adobe Firefly (no public API usable from this app: the Studio exports a
                                ready-to-paste shot list; the owner renders there and imports the MP4 back)
  * Commercial Reviewer  -> downloads/imports the MP4, watches the WHOLE render (commercial.watch), scores it,
                            checks the voice against the approved Lil Dr. Byrd reference; optional dub with the
                            owner's own voice recording;
  * Social Publisher     -> after Reviewer PASS + explicit owner approval, publishes through Blotato to the
                            owner's connected Facebook / Instagram / TikTok / YouTube accounts, one submission per
                            platform, polled to 'published' or 'failed'. Nothing is ever published automatically.

Blotato API facts used here were read from help.blotato.com (REST quickstart + LLM reference, 2026-11-13):
base https://backend.blotato.com/v2, header 'blotato-api-key', GET /users/me/accounts, GET
/users/me/accounts/:id/subaccounts, POST /media/uploads -> {presignedUrl, publicUrl} (PUT raw bytes), POST /posts
{post:{accountId, content:{text, mediaUrls, platform}, target:{targetType,...}}, scheduledTime?} -> postSubmissionId,
GET /posts/:id -> status published|failed|in-progress|scheduled, GET /videos/templates, POST /videos/from-templates
{templateId, inputs, prompt, render} -> item.id, GET /videos/creations/:id -> item.status/mediaUrl/error.
Poll posts >= 10 s apart, visuals >= 15 s apart; stop on 429.
"""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'https://backend.blotato.com/v2'
KEYRING_SERVICE = 'ByrdWayStudio'
KEY_NAME = 'BLOTATO_API_KEY'

# Owner's channels (SSOIA) -> Blotato platform ids
CHANNELS = {
    'facebook': 'https://www.facebook.com/roge.byrd',
    'instagram': 'https://instagram.com/fractionsaremyfriends1',
    'tiktok': 'https://www.tiktok.com/@z29experience',
    'youtube': 'https://www.youtube.com/channel/UC-xRHrJHbxEUxS6nMOwkGMA',
}

PLATFORMS = {
    'blotato': {
        'name': 'Blotato (AI video templates + publishing)', 'mode': 'api',
        'how': 'Automated from the Studio with your Blotato API key. Generation uses Blotato credits on your plan; '
               'the Studio asks before every paid generation.',
        'templates': {'character': '/base/v2/ai-selfie-video/57f5a565-fd17-458b-be43-4a2d8ccaca75/v1',
                      'story': '/base/v2/ai-story-video/5903fe43-514d-40ee-a060-0d6628c5f8fd/v1',
                      'avatar_broll': '/base/v2/ai-avatar-broll/7c26a1cd-d5b3-42da-9c73-2413333873b3/v1'},
        'url': 'https://my.blotato.com/videos/new'},
    'google_flow': {
        'name': 'Google Flow (Veo)', 'mode': 'manual',
        'how': 'No public API this app can call. The Studio exports the shot list + character prompt; you paste each '
               'shot into Flow, use "Ingredients" with the Lil Dr. Byrd image for consistency, extend shots to 30-45 s, '
               'download the MP4 and import it here for review.',
        'url': 'https://labs.google/fx/tools/flow'},
    'adobe_firefly': {
        'name': 'Adobe Firefly (video)', 'mode': 'manual',
        'how': 'No API this app can call without an Adobe enterprise contract. The Studio exports the shot list; you '
               'generate clips in Firefly (image-to-video from the Lil Dr. Byrd image), assemble 30-45 s, export the MP4 '
               'and import it here for review.',
        'url': 'https://firefly.adobe.com'},
}

# Character sheet from the owner-approved reference image (owner message 2026-11-13). The image itself is registered
# in the Studio assets as 'lil_dr_byrd_reference' (kind 'mascot') and never stored in the public repository.
CHARACTER_ASSET_ID = 'lil_dr_byrd_reference'
CHARACTER = ('Lil Dr. Byrd: a stylized 3D animated (feature-animation style) young Black man, short dark curly hair with '
             'a clean fade, full neatly trimmed black beard, big warm brown eyes, wide confident smile; navy blue hoodie '
             'and navy joggers with a gold "B" graduation-cap crest and the gold words "BYRDWAY MATHEMATICS AND SCIENCE" '
             'on the chest and left thigh; gold drawstring tips; gold beaded bracelet on the right wrist, black watch on '
             'the left; navy-and-gold high-top sneakers with the gold B crest and "BYRDWAY" on the side. Energetic, '
             'friendly teacher energy. Keep face, outfit, colors and logos identical in every shot.')
STYLE = ('Vertical 9:16, cinematic lighting, warm gold and purple accents, shallow depth of field, smooth camera motion, '
         'no on-screen text from the generator (captions are added by the Studio), no other characters\' logos.')

MIN_S, MAX_S = 30, 45


def brief(product, lines, duration=30, platform='blotato'):
    """Production brief. product: {title, destination_url, destination_label, destination_verified}; lines: list of
    {beat: hook|problem|demo|cta, voice: exact words in the approved voice, shot: what the camera shows}."""
    if not MIN_S <= duration <= MAX_S:
        raise ValueError(f'commercial length must be {MIN_S}-{MAX_S} s')
    beats = [b['beat'] for b in lines]
    problems = []
    for need in ('hook', 'problem', 'demo', 'cta'):
        if need not in beats:
            problems.append(f'missing {need} beat')
    if not product.get('destination_verified'):
        problems.append('CTA destination not verified (open the TpT link and confirm the product name first)')
    words = sum(len(b['voice'].split()) for b in lines)
    if words / duration > 3.2:
        problems.append(f'{words} words in {duration} s is too fast (> 3.2 words/s): cut lines or lengthen')
    seg = 8 if platform == 'google_flow' else 5 if platform == 'adobe_firefly' else None
    shots, t = [], 0.0
    share = duration / max(len(lines), 1)
    for i, b in enumerate(lines):
        d = round(share, 1)
        shots.append({'n': i + 1, 't0': round(t, 1), 't1': round(t + d, 1), 'beat': b['beat'], 'voice': b['voice'],
                      'caption': b.get('caption', b['voice']),
                      'prompt': f"{CHARACTER} {b['shot']}. {STYLE}",
                      'clips_needed': (int(-(-d // seg)) if seg else 1)})
        t += d
    return {'product': product, 'duration_s': duration, 'platform': platform, 'platform_info': PLATFORMS[platform],
            'character': CHARACTER, 'character_asset': CHARACTER_ASSET_ID, 'style': STYLE, 'shots': shots,
            'voiceover_script': ' '.join(b['voice'] for b in lines),
            'voice_rule': 'Lil Dr. Byrd approved voice ONLY (owner recording or registered voice). No generic AI narration '
                          'is accepted by the Reviewer.',
            'footer': f"{product['title']} | {product.get('destination_label', 'Teachers Pay Teachers')}",
            'ready': not problems, 'problems': problems}


def brief_text(b):
    """Human-readable shot list for pasting into Google Flow / Firefly."""
    L = [f"LIL DR. BYRD COMMERCIAL - {b['product']['title']} - {b['duration_s']} s - {b['platform_info']['name']}",
         f"Open: {b['platform_info']['url']}", f"How: {b['platform_info']['how']}", '',
         'CHARACTER (paste into every shot; attach the Lil Dr. Byrd reference image):', b['character'], '',
         'STYLE:', b['style'], '']
    for s in b['shots']:
        L += [f"SHOT {s['n']}  {s['t0']}-{s['t1']} s  [{s['beat'].upper()}]  clips: {s['clips_needed']}",
              f"  Prompt: {s['prompt']}", f"  Voice (approved Lil Dr. Byrd voice): \"{s['voice']}\"",
              f"  Caption: {s['caption']}", '']
    L += [f"Footer on every frame: {b['footer']}", '', b['voice_rule']]
    if b['problems']:
        L += ['', 'NOT READY:'] + [f'  - {p}' for p in b['problems']]
    return '\n'.join(L)


# ---------------------------------------------------------------- key storage (OS secret store, never in files/logs)
def get_key():
    import os
    if os.environ.get(KEY_NAME):
        return os.environ[KEY_NAME].strip()
    try:
        import keyring
        return (keyring.get_password(KEYRING_SERVICE, KEY_NAME) or '').strip()
    except Exception:
        return ''


def store_key(key):
    try:
        import keyring
    except Exception:
        raise RuntimeError('Install keyring (Windows Credential Manager) or set the BLOTATO_API_KEY environment variable')
    keyring.set_password(KEYRING_SERVICE, KEY_NAME, key.strip())


# ---------------------------------------------------------------- Blotato REST client
class BlotatoError(RuntimeError):
    pass


class Blotato:
    def __init__(self, key=None, http=None, sleep=time.sleep, base=BASE):
        self.key = key or get_key()
        if not self.key:
            raise BlotatoError('Blotato API key not set (Revenue & Media tab -> Video platform & Blotato setup)')
        self.http = http or self._urllib
        self.sleep = sleep
        self.base = base

    def _urllib(self, method, url, headers, body):
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def call(self, method, path, body=None):
        h = {'blotato-api-key': self.key, 'Accept': 'application/json'}
        data = None
        if body is not None:
            h['Content-Type'] = 'application/json'
            data = json.dumps(body).encode()
        code, raw = self.http(method, self.base + path, h, data)
        try:
            js = json.loads(raw or b'{}')
        except ValueError:
            js = {'raw': (raw or b'')[:300].decode('utf-8', 'replace')}
        if code == 401:
            raise BlotatoError('401: Blotato rejected the API key (copy the full key, including trailing "=")')
        if code == 429:
            raise BlotatoError('429: Blotato rate limit reached - wait a minute and try again')
        if code >= 400:
            raise BlotatoError(f'{code}: {js.get("message") or js.get("error") or js}')
        return js

    # accounts
    def accounts(self, platform=None):
        return self.call('GET', '/users/me/accounts' + (f'?platform={platform}' if platform else '')).get('items', [])

    def subaccounts(self, account_id):
        return self.call('GET', f'/users/me/accounts/{account_id}/subaccounts').get('items', [])

    # media
    def upload(self, path):
        """Presigned upload of a local file; returns the public URL Blotato serves it from."""
        p = Path(path)
        r = self.call('POST', '/media/uploads', {'filename': p.name})
        code, _ = self.http('PUT', r['presignedUrl'], {'Content-Type': 'application/octet-stream'}, p.read_bytes())
        if code >= 300:
            raise BlotatoError(f'upload failed ({code})')
        return r['publicUrl']

    # visuals (paid generation)
    def template(self, template_id):
        items = self.call('GET', f'/videos/templates?id={urllib.request.quote(template_id, safe="")}'
                                 '&fields=id,name,description,inputs').get('items', [])
        return items[0] if items else None

    def create_visual(self, template_id, prompt, inputs=None, title=None, owner_confirmed=False):
        if not owner_confirmed:
            raise BlotatoError('generation uses Blotato credits: owner confirmation required')
        body = {'templateId': template_id, 'inputs': inputs or {}, 'render': True}
        if prompt:
            body['prompt'] = prompt
        if title:
            body['title'] = title
        return self.call('POST', '/videos/from-templates', body)['item']['id']

    def wait_visual(self, vid, limit_s=1200, every=15):
        waited = 0
        while True:
            it = self.call('GET', f'/videos/creations/{vid}')['item']
            if it.get('error') or it.get('status') in ('creation-from-template-failed', 'insufficient-credits'):
                return {'id': vid, 'status': it.get('status'), 'error': it.get('error') or it.get('status')}
            if it.get('status') == 'done':
                return {'id': vid, 'status': 'done', 'mediaUrl': it.get('mediaUrl')}
            if waited >= limit_s:
                return {'id': vid, 'status': it.get('status'), 'error': None, 'unfinished': True}
            self.sleep(every)
            waited += every

    # publishing
    def post(self, account_id, platform, text, media_url, target_extra=None, scheduled_time=None):
        body = {'post': {'accountId': str(account_id),
                         'content': {'text': text, 'mediaUrls': [media_url], 'platform': platform},
                         'target': dict({'targetType': platform}, **(target_extra or {}))}}
        if scheduled_time:
            body['scheduledTime'] = scheduled_time
        return self.call('POST', '/posts', body)['postSubmissionId']

    def wait_post(self, sid, limit_s=600, every=10):
        waited = 0
        while True:
            r = self.call('GET', f'/posts/{sid}')
            if r.get('status') in ('published', 'failed', 'scheduled') or waited >= limit_s:
                return {'postSubmissionId': sid, 'status': r.get('status'), 'publicUrl': r.get('publicUrl'),
                        'errorMessage': r.get('errorMessage'), 'scheduledTime': r.get('scheduledTime')}
            self.sleep(every)
            waited += every


def target_fields(platform, title, ai_generated, page_id=None):
    """Required destination fields per Blotato's platform table."""
    if platform == 'facebook':
        if not page_id:
            raise BlotatoError('Facebook needs a Page: connect one in Blotato Accounts')
        return {'pageId': str(page_id), 'mediaType': 'reel'}
    if platform == 'instagram':
        return {'mediaType': 'reel', 'shareToFeed': True}
    if platform == 'tiktok':
        return {'privacyLevel': 'PUBLIC_TO_EVERYONE', 'disabledComments': False, 'disabledDuet': False,
                'disabledStitch': False, 'isBrandedContent': False, 'isYourBrand': True, 'isAiGenerated': bool(ai_generated)}
    if platform == 'youtube':
        return {'title': title[:100], 'privacyStatus': 'public', 'shouldNotifySubscribers': True,
                'isMadeForKids': False, 'containsSyntheticMedia': bool(ai_generated)}
    raise BlotatoError(f'unsupported platform {platform}')


TIKTOK_HASHTAGS = ['#mathteacher', '#studytok', '#ByrdWay', '#teacherspayteachers']     # exactly four (owner rule)


def captions(product, platform):
    """Per-platform post text (Sales QA checks it before publishing). TikTok: caption + exactly 4 hashtags.
    YouTube: the text is the description; the title goes in the target (<= 100 characters)."""
    url = product['destination_url']
    if platform == 'tiktok':
        return f"{product['title']}: Lil Dr. Byrd makes it click. Link in bio / TpT: {url} " + ' '.join(TIKTOK_HASHTAGS)
    if platform == 'youtube':
        return (f"{product['title']}\n\nLil Dr. Byrd walks you through it step by step.\n"
                f"Get it on Teachers Pay Teachers: {url}\n\nByrdWay Mathematics & Science\n#shorts #ByrdWay")
    if platform == 'instagram':
        return f"{product['title']} - Lil Dr. Byrd explains it step by step. Get it on TpT: {url} #mathteacher #teachersofinstagram #ByrdWay"
    return f"{product['title']} - Lil Dr. Byrd explains it step by step. Get it on Teachers Pay Teachers: {url}"


def import_key_file(path):
    """First run: move a private key file (from the owner's Starter Pack) into the OS secret store, then delete it."""
    p = Path(path)
    if not p.is_file():
        return False
    key = p.read_text(encoding='utf-8').strip()
    if not key.startswith('blt_'):
        return False
    store_key(key)
    p.unlink()
    return True


# ---------------------------------------------------------------- the agent workflow
def platform_setup_check(client):
    """Connected accounts for the owner's 4 channels (+ Facebook pages)."""
    accts = client.accounts()
    out = {}
    for p in CHANNELS:
        mine = [a for a in accts if a.get('platform') == p]
        row = {'connected': bool(mine), 'accounts': [{'id': a['id'], 'name': a.get('fullname'), 'username': a.get('username')}
                                                      for a in mine]}
        if p == 'facebook' and mine:
            row['pages'] = client.subaccounts(mine[0]['id'])
        out[p] = row
    return out


def produce_on_blotato(client, b, owner_confirmed, kind='character', character_url=None):
    """Video Producer: one paid Blotato generation from the brief (after owner confirmation).
    Inputs follow the live template schema (verified 2026-11-13 on the owner's account + help.blotato.com):
    character template = scenes[{description, narration}], style, characterDescription (text OR image URL), aspectRatio."""
    if not b['ready']:
        raise BlotatoError('brief not ready: ' + '; '.join(b['problems']))
    tid = PLATFORMS['blotato']['templates'][kind]
    shot = lambda s: s['prompt'].replace(b['character'], '').replace(b['style'], '').strip(' .')
    if kind == 'character':
        inputs = {'scenes': [{'description': shot(s), 'narration': s['voice']} for s in b['shots']],
                  'style': 'cartoon', 'characterDescription': character_url or b['character'], 'aspectRatio': '9:16'}
    elif kind == 'story':
        inputs = {'scenes': [{'mediaSource': f"{b['character']} {shot(s)}", 'script': s['voice']} for s in b['shots']],
                  'aspectRatio': '9:16', 'captionPosition': 'bottom', 'animateAiImages': True}
    else:
        inputs = {}
    prompt = None if inputs else (f"{b['duration_s']}-second vertical commercial. {b['character']} "
                                  + ' '.join(f"{shot(s)} He says: \"{s['voice']}\"" for s in b['shots']))
    vid = client.create_visual(tid, prompt, inputs, title=b['product']['title'][:80], owner_confirmed=owner_confirmed)
    return {'visual_id': vid, 'template': tid, 'inputs_set': sorted(inputs)}


def download(url, dest, http=None):
    if http:
        code, raw = http('GET', url, {}, None)
    else:
        with urllib.request.urlopen(url, timeout=120) as r:
            code, raw = r.status, r.read()
    if code >= 300:
        raise BlotatoError(f'download failed ({code})')
    Path(dest).write_bytes(raw)
    return dest


def dub_with_voice(video, voice, out):
    """Replace the generator's audio with the owner's approved Lil Dr. Byrd recording (loudness -14 LUFS)."""
    import subprocess
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(video), '-i', str(voice), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-shortest',
                    '-movflags', '+faststart', str(out)], check=True)
    return out


def review(mp4, b, root=None, ai_voice=False):
    """Commercial Reviewer: watch the whole MP4, score 8 categories, voice gate. Returns the commercial.score record."""
    import commercial
    beats, n = [], len(b['shots'])
    for i, s in enumerate(b['shots']):
        w = len(s['voice'].split())
        beats.append({'t0': s['t0'], 't1': s['t1'], 'beat': 'hook' if i == 0 else 'cta' if i == n - 1 else f'p{i + 1}',
                      'caption': s['caption'], 'voice': s['voice'], 'words': w, 'words_per_s': round(w / max(s['t1'] - s['t0'], .1), 2)})
    foot = (b['product']['title'], b['product'].get('destination_label', 'Teachers Pay Teachers'))
    rev = commercial.watch(mp4, beats, foot)
    ref = commercial.approved_voice(root) if root else None
    vc = commercial.voice_consistency(mp4, ref['file']) if ref and ref.get('file') else None
    prod = dict(b['product'], demo_from_real_product=b['product'].get('demo_from_real_product', False))
    sc = commercial.score(prod, beats, rev, 'generic AI voice' if ai_voice else 'owner voice recording', voice_check=vc,
                          target_duration=min(max(rev['duration_s'], MIN_S), MAX_S), footage=True)
    if ai_voice:
        sc['decision'] = 'BLOCKED - approved Lil Dr. Byrd voice required (dub with your recording)'
    return {'review': rev, 'score': sc, 'voice_check': vc}


def publish(client, mp4_or_url, product, platforms, approval, accounts=None, ai_generated=True, scheduled_time=None,
            previous=None):
    """Social Publisher. approval must be {'owner': name, 'explicit': True, 'qa_decision': 'PASS...'}.
    One Blotato submission per platform; each outcome reported separately."""
    ok = str((approval or {}).get('qa_decision', '')).startswith('PASS') or (
        (approval or {}).get('first_post_override') and (approval or {}).get('data_capped_only'))
    if not (approval and approval.get('explicit') and ok):
        raise BlotatoError('publishing needs Reviewer PASS (or, for a first post, every non-audience check passing plus your '
                           'explicit first-post approval) and your explicit approval')
    import salesintel
    url = mp4_or_url if str(mp4_or_url).startswith('http') else client.upload(mp4_or_url)
    accounts = accounts or platform_setup_check(client)
    results = []
    done_before = {r['platform']: r for r in (previous or []) if r.get('status') in ('published', 'scheduled', 'in-progress')}
    for p in platforms:
        if p in done_before:                       # retry safety: never post the same commercial twice
            results.append(dict(done_before[p], note='already submitted earlier - not posted again'))
            continue
        row = accounts.get(p) or {}
        if not row.get('connected'):
            results.append({'platform': p, 'status': 'not connected in Blotato'})
            continue
        text = captions(product, p)
        probs = salesintel.qa_text(text)
        if probs:
            results.append({'platform': p, 'status': 'blocked by Sales QA', 'problems': probs})
            continue
        page = (row.get('pages') or [{}])[0].get('id') if p == 'facebook' else None
        try:
            sid = client.post(row['accounts'][0]['id'], p, text, url,
                              target_fields(p, product['title'], ai_generated, page), scheduled_time)
            results.append(dict(client.wait_post(sid), platform=p))
        except BlotatoError as e:
            results.append({'platform': p, 'status': 'failed', 'errorMessage': str(e)})
    return {'media_url': url, 'results': results, 'approved_by': approval.get('owner')}
